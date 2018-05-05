import os
import time
import math
import pytest
import _pytest
import platform
import threading
import collections
import queue as Queue
from multiprocessing import Manager, Process


def parse_config(config, name):
    return getattr(config.option, name, config.getini(name))


def force(fn):
    while True:
        try:
            return fn()
        except ConnectionRefusedError:
            time.sleep(.1)
            continue


def pytest_addoption(parser):
    workers_help = 'Set the max num of workers (aka processes) to start (int or "auto" - one per core)'
    tests_per_worker_help = 'Set the max num of concurrent tests for each worker (int or "auto" - split evenly)'

    group = parser.getgroup('pytest-parallel')
    group.addoption(
        '--workers',
        dest='workers',
        help=workers_help
    )
    group.addoption(
        '--tests-per-worker',
        dest='tests_per_worker',
        help=tests_per_worker_help
    )

    parser.addini('workers', workers_help)
    parser.addini('tests_per_worker', tests_per_worker_help)


def run_test(session, item, nextitem):
    item.ihook.pytest_runtest_protocol(item=item, nextitem=nextitem)
    if session.shouldstop:
        raise session.Interrupted(session.shouldstop)


def process_with_threads(queue, session, tests_per_worker):
    threads = []
    for _ in range(tests_per_worker):
        thread = ThreadWorker(queue, session)
        thread.start()
        threads.append(thread)
    [t.join() for t in threads]


class ThreadWorker(threading.Thread):
    def __init__(self, queue, session):
        threading.Thread.__init__(self)
        self.queue = queue
        self.session = session
 
    def run(self):
        while True:
            try:
                index = self.queue.get_nowait()
            except Queue.Empty:
                break
            except ConnectionRefusedError:
                time.sleep(.1)
                continue
            item = self.session.items[index]
            run_test(self.session, item, None)
            try:
                self.queue.task_done()
            except ConnectionRefusedError:
                pass


@pytest.mark.trylast
def pytest_configure(config):
    workers = parse_config(config, 'workers')
    tests_per_worker = parse_config(config, 'tests_per_worker')
    if not config.option.collectonly and (workers or tests_per_worker):
        config.pluginmanager.register(ParallelRunner(config), 'parallelrunner')


class ThreadLocalEnviron(collections.MutableMapping):
    def __init__(self, *args, **kwargs):
        self.dict_store = {}
        self.thread_store = threading.local()
        self.update(dict(*args, **kwargs))

    def __getitem__(self, key):
        if key == 'PYTEST_CURRENT_TEST':
            return getattr(self.thread_store, key, None)
        return self.dict_store[key]

    def __setitem__(self, key, value):
        if key == 'PYTEST_CURRENT_TEST':
            setattr(self.thread_store, key, value)
        else:
            self.dict_store[key] = value

    def __delitem__(self, key):
        if key == 'PYTEST_CURRENT_TEST':
            delattr(self.thread_store, self.__keytransform__(key))
        else:
            del self.dict_store[self.__keytransform__(key)]

    def __iter__(self):
        tmp = {}
        tmp.update(self.dict_store)
        tmp.update(self.thread_store.__dict__)
        return iter(tmp)

    def __len__(self):
        return len(self.thread_store.__dict__) + len(self.dict_store)

    def __keytransform__(self, key):
        return key


class ThreadLocalSetupState(threading.local, _pytest.runner.SetupState):
    def __init__(self):
        super(ThreadLocalSetupState, self).__init__()


class ThreadLocalFixtureDef(threading.local, _pytest.fixtures.FixtureDef):
    def __init__(self, *args, **kwargs):
        super(ThreadLocalFixtureDef, self).__init__(*args, **kwargs)


class ParallelRunner(object):
    def __init__(self, config):
        self._manager = Manager()
        reporter = config.pluginmanager.getplugin('terminalreporter')
        reporter.showfspath = False # prevent mangling the output

        # get the number of workers
        workers = parse_config(config, 'workers')
        try:
            if workers == 'auto':
                workers = os.cpu_count() or 1
            elif workers:
                workers = int(workers)
            else:
                workers = 1
            if workers > 1 and platform.system() == 'Windows':
                workers = 1
                print('INFO: pytest-parallel forces 1 worker on Windows')
        except ValueError:
            raise ValueError('workers can only be an integer or "auto"')
        
        self.workers = workers

        if self.workers > 1:
            # ensure stats are process-safe
            reporter.stats = self._manager.dict()
            setdefault = reporter.stats.setdefault
            def setdefault_proxy(key, default=None):
                if isinstance(default, list) and len(default) == 0:
                    default = force(lambda: self._manager.list())
                    return force(lambda: setdefault(key, default))
            reporter.stats.setdefault = setdefault_proxy


    @pytest.mark.tryfirst
    def pytest_sessionstart(self, session):
        # make the session threadsafe
        _pytest.runner.SetupState = ThreadLocalSetupState
        
        # ensure that the fixtures (specifically finalizers) are threadsafe
        _pytest.fixtures.FixtureDef = ThreadLocalFixtureDef

        # make the environment threadsafe
        os.environ = ThreadLocalEnviron(os.environ)


    def pytest_runtestloop(self, session):
        # get the number of tests per worker
        tests_per_worker = parse_config(session.config, 'tests_per_worker')
        try:
            if tests_per_worker == 'auto':
                tests_per_worker = 50
            if tests_per_worker:
                tests_per_worker = min(int(tests_per_worker), math.ceil(len(session.items)/self.workers))
            else:
                tests_per_worker = 1
        except ValueError:
            raise ValueError('tests_per_worker can only be an integer or "auto"')

        worker_noun = 'workers' if self.workers > 1 else 'worker'
        test_noun = 'tests' if tests_per_worker > 1 else 'test'
        print('pytest-parallel: {} {} (processes), {} {} per worker (threads)'
            .format(self.workers, worker_noun, tests_per_worker, test_noun))

        queue = Queue.Queue() if self.workers == 1 else self._manager.Queue()

        for i in range(len(session.items)):
            queue.put(i)
        
        if self.workers == 1:
            process_with_threads(queue, session, tests_per_worker)
            return True

        processes = []
        for _ in range(self.workers):
            process = Process(target=process_with_threads, args=(queue, session, tests_per_worker))
            process.start()
            processes.append(process)
        [p.join() for p in processes]
        queue.join()

        return True
