import pytest
import re


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
    assert result.ret == 0


def test_sanity_sync_double(testdir):
    testdir.makepyfile("""
        def test_sync_1():
            assert 1 == 1

        def test_sync_2():
            assert 2 == 2
    """)
    result = testdir.runpytest()
    result.assert_outcomes(passed=2)
    assert result.ret == 0


def test_sanity_async_single(testdir):
    testdir.makepyfile("""
        import time
        def test_async():
            time.sleep(.1)
            assert 1 == 1
    """)
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)
    assert result.ret == 0


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
    assert result.ret == 0


@pytest.mark.parametrize('cli_args', [
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
    assert result.ret == 0


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
    assert result.ret == 0


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
    assert result.ret == 0


@pytest.mark.parametrize('cli_args', [
  [],
  ['--workers=2'],
  ['--tests-per-worker=2']
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
    result = testdir.runpytest('-m marked', *cli_args)
    result.assert_outcomes(passed=1, skipped=0)
    assert result.ret == 0


@pytest.mark.parametrize('cli_args', [
  [],
  ['--workers=2'],
  ['--tests-per-worker=2']
])
def test_multiple_failures(testdir, cli_args):
    testdir.makepyfile("""
        def test_0():
            assert 1 == 2

        def test_1():
            assert True == False

        def test_2():
            assert 1 == 2

        def test_3():
            assert True == False
    """)
    result = testdir.runpytest(*cli_args)
    result.assert_outcomes(failed=4)
    assert result.ret == 1


@pytest.mark.parametrize('cli_args', [
  [],
  ['--workers=2'],
  ['--tests-per-worker=2']
])
def test_pytest_html(testdir, cli_args):
    report = testdir.tmpdir.join('report.html')
    testdir.makepyfile("""
        def test_1():
            assert 1 == 1

        def test_2():
            assert 1 == 2
    """)
    result = testdir.runpytest('--html=' + str(report), *cli_args)
    result.assert_outcomes(passed=1, failed=1)
    assert result.ret == 1
    with open(str(report)) as f:
        html = str(f.read())
        assert re.search('2 tests ran', html) is not None
        assert re.search('1 passed', html) is not None
        assert re.search('1 failed', html) is not None
        assert re.search('passed results-table-row', html) is not None
        assert re.search('failed results-table-row', html) is not None


@pytest.mark.parametrize('cli_args', [
  [],
  ['--workers=2'],
  ['--tests-per-worker=2']
])
def test_collection_error(testdir, cli_args):
    testdir.makepyfile(first_file_test="""
        def test_1():
            assert 1 == 1
    """, second_file_test="""
        raise Exception('Failed to load test file')
    """)
    result = testdir.runpytest(*cli_args)
    result.assert_outcomes(error=1)
    # Expect error code 2 (Interrupted), which is returned on collection error.
    assert result.ret == 2


@pytest.mark.parametrize('cli_args', [
  [],
  ['--workers=2'],
  ['--tests-per-worker=2']
])
def test_collection_collectonly(testdir, cli_args):
    testdir.makepyfile("def test(): pass")
    result = testdir.runpytest("--collect-only", *cli_args)
    result.stdout.fnmatch_lines([
        "collected 1 item",
        "<Module test_collection_collectonly.py>",
        "  <Function test>",
        "*= no tests ran in *",
    ])
    result.assert_outcomes()
    assert result.ret == 0
