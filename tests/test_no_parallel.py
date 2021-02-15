import pytest
import re


def test_no_parallel_marker(testdir):
    testdir.makepyfile("""
        import os
        import pytest

        # Remember the PID of a process
        # which loaded the module.
        ppid = os.getpid()

        def test_parallel():
            # This test should be executed in a subprocess
            assert ppid != os.getpid()
            assert ppid == os.getppid()

        @pytest.mark.no_parallel
        def test_no_parallel():
            # And this one is in the main process
            assert ppid == os.getpid()

    """)
    result = testdir.runpytest('--workers=2')
    result.assert_outcomes(passed=2)
    assert result.ret == 0
