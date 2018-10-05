import pytest


@pytest.mark.parametrize('cli_args', [
  [],
  ['--workers=2'],
  ['--tests-per-worker=2']
])
def test_normal(testdir, cli_args):
    testdir.makepyfile("""
        def test_0():
            assert 1 == 2

        def test_1():
            assert True == False
    """)
    result = testdir.runpytest(*cli_args)
    result.assert_outcomes(failed=2)
    assert result.ret == 1
