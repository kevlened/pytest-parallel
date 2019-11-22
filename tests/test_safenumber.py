import multiprocessing as mp

from pytest_parallel import SafeNumber


def test_SafeNumber():
    manager = mp.Manager()

    nr = SafeNumber(manager)
    assert isinstance(nr, SafeNumber)
    assert not nr
    assert nr == 0

    assert nr + 1 == 1
    nr += 1
    assert isinstance(nr, SafeNumber)
    assert nr == 1
    assert nr >= 1
    assert nr <= 1
    assert nr
    assert repr(nr) == '1'
    assert str(nr) == '1'
