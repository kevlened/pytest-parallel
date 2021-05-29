import os
import py
import sys
import time
import math
import pytest
import _pytest
import platform
import threading
import multiprocessing
from tblib import pickling_support
from multiprocessing import Manager, Process

# In Python 3.8 and later, the default on macOS is spawn.
# We force forking behavior at the expense of safety.
#
# "On macOS, the spawn start method is now the default. The fork start method should be
#  considered unsafe as it can lead to crashes of the subprocess. See bpo-33725."
#
# https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
if sys.platform.startswith('darwin'):
    multiprocessing.set_start_method('fork')

__version__ = '0.1.0'


def parse_config(config, name):
    return getattr(config.option, name, config.getini(name))


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


def process_with_threads(config, queue, session, tests_per_worker, errors):
    # This function will be called from subprocesses, forked from the main
    # pytest process. First thing we need to do is to change config's value
    # so we know we are running as a worker.
    config.parallel_worker = True

    threads = []
    for _ in range(tests_per_worker):
        thread = ThreadWorker(queue, session, errors)
        thread.start()
        threads.append(thread)
    [t.join() for t in threads]


class ThreadWorker(threading.Thread):
    def __init__(self, queue, session, errors):
        threading.Thread.__init__(self)
        self.queue = queue
        self.session = session
        self.errors = errors

    def run(self):
        pickling_support.install()
        while True:
            try:
                index = self.queue.get()
                if index == 'stop':
                    self.queue.task_done()
                    break
            except ConnectionRefusedError:
                time.sleep(.1)
                continue
            item = self.session.items[index]
            try:
                run_test(self.session, item, None)
            except BaseException:
                import pickle
                import sys

                self.errors.put((self.name, pickle.dumps(sys.exc_info())))
            finally:
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
        if sys.version_info >= (3, 9):
            super().__init__(
                env._data,
                env.encodekey,
                env.decodekey,
                env.encodevalue,
                env.decodevalue,
            )
            self.putenv = os.putenv
            self.unsetenv = os.unsetenv
        else:
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
        self._config = config
        self._manager = Manager()
        self._log = py.log.Producer('pytest-parallel')

        reporter = config.pluginmanager.getplugin('terminalreporter')

        # prevent mangling the output
        reporter.showfspath = False
        reporter._show_progress_info = False

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

    @pytest.mark.tryfirst
    def pytest_sessionstart(self, session):
        # make the session threadsafe
        _pytest.runner.SetupState = ThreadLocalSetupState

        # ensure that the fixtures (specifically finalizers) are threadsafe
        _pytest.fixtures.FixtureDef = ThreadLocalFixtureDef

        # make the environment threadsafe
        os.environ = ThreadLocalEnviron(os.environ)

    def pytest_runtestloop(self, session):
        if (
            session.testsfailed
            and not session.config.option.continue_on_collection_errors
        ):
            raise session.Interrupted(
                "%d error%s during collection"
                % (session.testsfailed, "s" if session.testsfailed != 1 else "")
            )

        if session.config.option.collectonly:
            return True

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

        queue_cls = self._manager.Queue
        queue = queue_cls()
        errors = queue_cls()

        # Reports about tests will be gathered from workerss
        # using this queue. Workers will push reports to the queue,
        # and a separate thread will rerun pytest_runtest_logreport
        # for them.
        # This way, report generators like JUnitXML will work as expected.
        self.responses_queue = queue_cls()

        for i in range(len(session.items)):
            queue.put(i)

        # Now we need to put stopping sentinels, so that worker
        # processes will know, there is time to finish the work.
        for i in range(self.workers * tests_per_worker):
            queue.put('stop')

        responses_processor = threading.Thread(
            target=self.process_responses,
            args=(self.responses_queue,),
        )
        responses_processor.daemon = True
        responses_processor.start()

        def wait_for_responses_processor():
            self.responses_queue.put(('quit', {}))
            responses_processor.join()

        processes = []

        # Current process is not a worker.
        # This flag will be changed after the worker's fork.
        self._config.parallel_worker = False

        args = (self._config, queue, session, tests_per_worker, errors)
        for _ in range(self.workers):
            process = Process(target=process_with_threads, args=args)
            process.start()
            processes.append(process)

        [p.join() for p in processes]

        queue.join()
        wait_for_responses_processor()

        if not errors.empty():
            import six
            import pickle

            thread_name, errinfo = errors.get()
            err = pickle.loads(errinfo)
            err[1].__traceback__ = err[2]

            exc = RuntimeError(
                "pytest-parallel got {} errors, raising the first from {}."
                .format(errors.qsize() + 1, thread_name)
            )

            six.raise_from(exc, err[1])

        return True

    def send_response(self, event_name, **arguments):
        self.responses_queue.put((event_name, arguments))

    def pytest_runtest_logreport(self, report):
        # We want workers to report to it's master.
        # Without this "if", master will try to report to itself.
        if self._config.parallel_worker:
            data = self._config.hook.pytest_report_to_serializable(
                config=self._config, report=report
            )
            self.send_response('testreport', report=data)

    def on_testreport(self, report):
        report = self._config.hook.pytest_report_from_serializable(
            config=self._config, data=report
        )
        self._config.hook.pytest_runtest_logreport(report=report)

    def process_responses(self, queue):
        while True:
            try:
                event_name, kwargs = queue.get()
                if event_name == 'quit':
                    break
            except ConnectionRefusedError:
                time.sleep(.1)
                continue

            callback_name = 'on_' + event_name
            try:
                callback = getattr(self, callback_name)
                callback(**kwargs)
            except BaseException:
                self._log('Exception during calling callback', callback_name)
            finally:
                try:
                    queue.task_done()
                except ConnectionRefusedError:
                    pass
