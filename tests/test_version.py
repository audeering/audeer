import operator

import pytest

import audeer


@pytest.mark.parametrize(
    "v1, v2, wanted",
    [
        ("1.5.1", "1.5.2b2", -1),
        ("161", "3.10a", 1),
        ("8.02", "8.02", 0),
        ("3.4j", "1996.07.12", -1),
        ("3.2.pl0", "3.1.1.6", 1),
        ("2g6", "11g", -1),
        ("0.960923", "2.2beta29", -1),
        ("1.13++", "5.5.kw", -1),
    ],
)
def test_loose_version(v1, v2, wanted):
    # This test is replicating the original tests from
    # https://github.com/python/cpython/blob/20a1c8ee4bcb1c421b7cca1f3f5d6ad7ce30a9c9/Lib/distutils/tests/test_version.py

    v1 = audeer.LooseVersion(v1)

    result = v1._cmp(audeer.LooseVersion(v2))
    assert result == wanted

    result = v1._cmp(v2)
    assert result == wanted

    result = v1._cmp(object())
    assert result == NotImplemented

    assert v1.__repr__() == f"LooseVersion ('{str(v1)}')"


@pytest.mark.parametrize(
    "v1, v2, operator, expected",
    [
        ("1.5.1", "1.5.2b2", operator.eq, False),
        ("1.5.1", "1.5.2b2", operator.lt, True),
        ("1.5.1", "1.5.2b2", operator.le, True),
        ("1.5.1", "1.5.2b2", operator.gt, False),
        ("1.5.1", "1.5.2b2", operator.ge, False),
        ("1.5.1", "1.5.1", operator.eq, True),
        ("1.5.1", "1.5.1", operator.le, True),
        ("1.5.1", "1.5.1", operator.ge, True),
        ("161", "3.10a", operator.gt, True),
        ("8.02", "8.02", operator.eq, True),
        ("3.4j", "1996.07.12", operator.lt, True),
        ("3.2.pl0", "3.1.1.6", operator.gt, True),
        ("2g6", "11g", operator.lt, True),
        ("0.960923", "2.2beta29", operator.lt, True),
        ("1.13++", "5.5.kw", operator.lt, True),
    ],
)
def test_loose_version_operator(v1, v2, operator, expected):
    v1 = audeer.LooseVersion(v1)
    v2 = audeer.LooseVersion(v2)
    result = operator(v1, v2)
    assert result == expected


@pytest.mark.parametrize(
    "v1, v2, wanted",
    [
        ("1.5.1", "1.5.2b2", -1),
        pytest.param(
            "161",
            "3.10a",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        ("8.02", "8.02", 0),
        pytest.param(
            "3.4j",
            "1996.07.12",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            "3.2.pl0",
            "3.1.1.6",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            "2g6",
            "11g",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        ("0.9", "2.2", -1),
        ("1.2.1", "1.2", 1),
        ("1.1", "1.2.2", -1),
        ("1.2", "1.1", 1),
        ("1.2.1", "1.2.2", -1),
        ("1.2.2", "1.2", 1),
        ("1.2", "1.2.2", -1),
        ("0.4.0", "0.4", 0),
        pytest.param(
            "1.13++",
            "5.5.kw",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ],
)
def test_strict_version(v1, v2, wanted):
    # This test is replicating the original tests from
    # https://github.com/python/cpython/blob/20a1c8ee4bcb1c421b7cca1f3f5d6ad7ce30a9c9/Lib/distutils/tests/test_version.py

    v1 = audeer.StrictVersion(v1)

    result = v1._cmp(audeer.StrictVersion(v2))
    assert result == wanted

    result = v1._cmp(v2)
    assert result == wanted

    result = v1._cmp(object())
    assert result == NotImplemented

    assert v1.__repr__() == f"StrictVersion ('{str(v1)}')"


@pytest.mark.parametrize(
    "v1, v2, operator, expected",
    [
        ("1.5.1", "1.5.2b2", operator.eq, False),
        ("1.5.1", "1.5.2b2", operator.lt, True),
        ("1.5.1", "1.5.2b2", operator.le, True),
        ("1.5.1", "1.5.2b2", operator.gt, False),
        ("1.5.1", "1.5.2b2", operator.ge, False),
        ("1.5.1", "1.5.2b2", operator.ge, False),
        ("1.5.1a1", "1.5.1", operator.lt, True),
        ("1.5.1a1", "1.5.1a2", operator.lt, True),
        ("1.5.1a2", "1.5.1a1", operator.gt, True),
        ("1.5.1a1", "1.5.1a1", operator.eq, True),
        ("1.5.1", "1.5.1b2", operator.gt, True),
        ("1.5.1", "1.5.1", operator.le, True),
        ("1.5.1", "1.5.1", operator.ge, True),
        ("8.02", "8.02", operator.eq, True),
        ("0.9", "2.2", operator.lt, True),
        ("1.2.1", "1.2", operator.gt, True),
        ("1.1", "1.2.2", operator.lt, True),
        ("1.2", "1.1", operator.gt, True),
        ("1.2.1", "1.2.2", operator.lt, True),
        ("1.2.2", "1.2", operator.gt, True),
        ("1.2", "1.2.2", operator.lt, True),
        ("0.4.0", "0.4", operator.eq, True),
    ],
)
def test_strict_version_operator(v1, v2, operator, expected):
    v1 = audeer.StrictVersion(v1)
    v2 = audeer.StrictVersion(v2)
    result = operator(v1, v2)
    assert result == expected
