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
        def test_sync():
            time.sleep(.1)
            assert 1 == 1
    """)
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_sanity_async_double(testdir):
    testdir.makepyfile("""
        import time
        def test_sync_1():
            time.sleep(.1)
            assert 1 == 1

        def test_sync_2():
            time.sleep(.1)
            assert 2 == 2
    """)
    result = testdir.runpytest()
    result.assert_outcomes(passed=2)
