def test_concurrent_fixture(testdir):
    testdir.makepyfile("""
        import pytest
        import time
        from six import print_

        @pytest.fixture
        def driver(request):
            fn_name = request.function.__name__
            if fn_name == 'test_1':
                time.sleep(.05)
            print_('before sleep', fn_name)
            time.sleep(.1)
            print_('after sleep', fn_name)
            def after():
                print_('after test', fn_name)
            request.addfinalizer(after)

        def test_0(driver):
            print_('inside test_0')
            time.sleep(.2)

        def test_1(driver):
            print_('inside test_1')
    """)
    result = testdir.runpytest_subprocess(
      '-s',
      '--tests-per-worker=2'
    )
    result.stdout.fnmatch_lines([
        'pytest-parallel: 1 worker (process), 2 tests per worker (threads)',
        '*before sleep test_0',
        '*before sleep test_1',
        '*after sleep test_0',
        '*inside test_0',
        '*after sleep test_1',
        '*inside test_1',
        '*after test test_1',
        '*after test test_0'
    ])
    result.assert_outcomes(passed=2)
    assert result.ret == 0
