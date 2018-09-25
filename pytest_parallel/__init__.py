import os
import time
import math
import pytest
import _pytest
import platform
import threading
import queue as Queue
from multiprocessing import Manager, Process

__version__ = '0.0.5'


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
    workers_help = ('Set the max num of workers (aka processes) to start '
                    '(int or "auto" - one per core)')
    tests_per_worker_help = ('Set the max num of concurrent tests for each '
                             'worker (int or "auto" - split evenly)')

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


class ThreadLocalEnviron(os._Environ):
    def __init__(self, env):
        super().__init__(
            env._data,
            env.encodekey,
            env.decodekey,
            env.encodevalue,
            env.decodevalue,
            env.putenv,
            env.unsetenv
        )
        if hasattr(env, 'thread_store'):
            self.thread_store = env.thread_store
        else:
            self.thread_store = threading.local()

    def __getitem__(self, key):
        if key == 'PYTEST_CURRENT_TEST':
            if hasattr(self.thread_store, key):
                value = getattr(self.thread_store, key)
                return self.decodevalue(value)
            else:
                raise KeyError(key) from None
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        if key == 'PYTEST_CURRENT_TEST':
            value = self.encodevalue(value)
            self.putenv(self.encodekey(key), value)
            setattr(self.thread_store, key, value)
        else:
            super().__setitem__(key, value)

    def __delitem__(self, key):
        if key == 'PYTEST_CURRENT_TEST':
            self.unsetenv(self.encodekey(key))
            if hasattr(self.thread_store, key):
                delattr(self.thread_store, key)
            else:
                raise KeyError(key) from None
        else:
            super().__delitem__(key)

    def __iter__(self):
        if hasattr(self.thread_store, 'PYTEST_CURRENT_TEST'):
            yield 'PYTEST_CURRENT_TEST'
        keys = list(self._data)
        for key in keys:
            yield self.decodekey(key)

    def __len__(self):
        return len(self.thread_store.__dict__) + len(self._data)

    def copy(self):
        return type(self)(self)


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

        # prevent mangling the output
        reporter.showfspath = False

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
                    if key == "deselected":
                        # "deselected" on stats can safely ignore list values
                        res = force(lambda: setdefault(key, default))
                        res.extend = lambda iter: [
                            default.append(1) for i in range(len(iter))
                        ]
                        return res
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
                tests_per_worker = int(tests_per_worker)
                evenly_divided = math.ceil(len(session.items)/self.workers)
                tests_per_worker = min(tests_per_worker, evenly_divided)
            else:
                tests_per_worker = 1
        except ValueError:
            raise ValueError(('tests_per_worker can only be '
                              'an integer or "auto"'))

        if self.workers > 1:
            worker_noun, process_noun = ('workers', 'processes')
        else:
            worker_noun, process_noun = ('worker', 'process')

        if tests_per_worker > 1:
            test_noun, thread_noun = ('tests', 'threads')
        else:
            test_noun, thread_noun = ('test', 'thread')

        print('pytest-parallel: {} {} ({}), {} {} per worker ({})'
              .format(self.workers, worker_noun, process_noun,
                      tests_per_worker, test_noun, thread_noun))

        queue = Queue.Queue() if self.workers == 1 else self._manager.Queue()

        for i in range(len(session.items)):
            queue.put(i)

        if self.workers == 1:
            process_with_threads(queue, session, tests_per_worker)
            return True

        processes = []
        for _ in range(self.workers):
            process = Process(target=process_with_threads,
                              args=(queue, session, tests_per_worker))
            process.start()
            processes.append(process)
        [p.join() for p in processes]
        queue.join()

        return True
