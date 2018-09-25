import pytest


def test_help(testdir):
    result = testdir.runpytest(
        '--help',
    )
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'pytest-parallel:',
        '*--workers=WORKERS*',
        '*--tests-per-worker=TESTS_PER_WORKER*',

        '*workers (string)*',
        '*tests_per_worker (string)*',
    ])


def test_sanity_sync_single(testdir):
    testdir.makepyfile("""
        def test_sync():
            assert 1 == 1
    """)
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_sanity_sync_double(testdir):
    testdir.makepyfile("""
        def test_sync_1():
            assert 1 == 1

        def test_sync_2():
            assert 2 == 2
    """)
    result = testdir.runpytest()
    result.assert_outcomes(passed=2)


def test_sanity_async_single(testdir):
    testdir.makepyfile("""
        import time
        def test_async():
            time.sleep(.1)
            assert 1 == 1
    """)
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_sanity_async_double(testdir):
    testdir.makepyfile("""
        import time
        def test_async_1():
            time.sleep(.1)
            assert 1 == 1

        def test_async_2():
            time.sleep(.1)
            assert 2 == 2
    """)
    result = testdir.runpytest()
    result.assert_outcomes(passed=2)


@pytest.mark.parametrize('cli_args', [
  [],
  ['--workers=2'],
  ['--tests-per-worker=2']
])
def test_environ_shim(testdir, cli_args):
    testdir.makepyfile("""
        import os

        def test_0():
            expected = set([
                '_MutableMapping__marker', '__abstractmethods__', '__class__',
                '__contains__', '__delattr__', '__delitem__', '__dict__',
                '__dir__', '__doc__', '__eq__', '__format__', '__ge__',
                '__getattribute__', '__getitem__', '__gt__', '__hash__',
                '__init__', '__init_subclass__', '__iter__', '__le__',
                '__len__', '__lt__', '__module__', '__ne__', '__new__',
                '__reduce__', '__reduce_ex__', '__repr__', '__reversed__',
                '__setattr__', '__setitem__', '__sizeof__', '__slots__',
                '__str__', '__subclasshook__', '__weakref__', '_data',
                'clear', 'copy', 'decodekey', 'decodevalue', 'encodekey',
                'encodevalue', 'get', 'items', 'keys', 'pop', 'popitem',
                'putenv', 'setdefault', 'unsetenv', 'update', 'values'
            ])
            environ_keys = dir(os.environ)
            assert list(set(expected) - set(environ_keys)) == []
            assert list(os.environ.keys()) == list(os.environ.copy().keys())

            for key, value in os.environ.items():
                assert isinstance(key, str)
                assert isinstance(value, str)
    """)
    result = testdir.runpytest(*cli_args)
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize('cli_args', [
  [],
  ['--workers=2'],
  ['--tests-per-worker=2']
])
def test_skip_markers(testdir, cli_args):
    testdir.makepyfile("""
        import pytest

        def test_1():
            assert 1 == 1

        @pytest.mark.skip(reason="because")
        def test_2():
            assert 2 == 2
    """)
    result = testdir.runpytest(*cli_args)
    result.assert_outcomes(passed=1, skipped=1)


@pytest.mark.parametrize('cli_args', [
  [],
  ['--workers=2'],
  ['--tests-per-worker=2']
])
def test_skipif_markers(testdir, cli_args):
    testdir.makepyfile("""
        import pytest

        def test_1():
            assert 1 == 1

        @pytest.mark.skipif(True, reason="because")
        def test_2():
            assert 2 == 2

        @pytest.mark.skipif(
            "config.getoption('workers') or not config.getoption('workers')",
            reason="because"
        )
        def test_3():
            assert 3 == 3
    """)
    result = testdir.runpytest(*cli_args)
    result.assert_outcomes(passed=1, skipped=2)


@pytest.mark.parametrize('cli_args', [
  [],
  ['--workers=2'],
  ['--tests-per-worker=2']
])
def test_parametrize_markers(testdir, cli_args):
    testdir.makepyfile("""
        import pytest

        @pytest.mark.parametrize('num', [
            1,
            2
        ])
        def test_1(num):
            assert num == num
    """)
    result = testdir.runpytest(*cli_args)
    result.assert_outcomes(passed=2)


@pytest.mark.parametrize('cli_args', [
  ['-s'],
#   ['--workers=2'],
  ['-s', '--tests-per-worker=2']
])
def test_tryfirst_markers(testdir, cli_args):
    testdir.makepyfile("""
        import pytest
        from six import print_

        def test_1():
            print_('first')

        @pytest.mark.tryfirst
        def test_2():
            print_('second')
    """)
    result = testdir.runpytest(*cli_args)
    result.stdout.fnmatch_lines([
        '*second',
        '*first'
    ])
    result.assert_outcomes(passed=2)


@pytest.mark.parametrize('cli_args', [
  ['-s'],
#   ['-s', '--workers=2'],
  ['-s', '--tests-per-worker=2']
])
def test_trylast_markers(testdir, cli_args):
    testdir.makepyfile("""
        import pytest
        from six import print_

        @pytest.mark.trylast
        def test_1():
            print_('first')

        def test_2():
            print_('second')
    """)
    result = testdir.runpytest(*cli_args)
    result.stdout.fnmatch_lines([
        '*first',
        '*second'
    ])
    result.assert_outcomes(passed=2)


@pytest.mark.parametrize('cli_args', [
  ['-m marked'],
  ['-m marked', '--workers=2'],
  ['-m marked', '--tests-per-worker=2']
])
def test_custom_markers(testdir, cli_args):
    testdir.makepyfile("""
        import pytest

        def test_1():
            assert 1 == 1

        @pytest.mark.marked
        def test_2():
            assert 2 == 2
    """)
    result = testdir.runpytest(*cli_args)
    result.assert_outcomes(passed=1, skipped=0)
