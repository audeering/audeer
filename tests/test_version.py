import operator
import pytest

import audeer


@pytest.mark.parametrize(
    'v1, v2, wanted',
    [
        ('1.5.1', '1.5.2b2', -1),
        ('161', '3.10a', 1),
        ('8.02', '8.02', 0),
        ('3.4j', '1996.07.12', -1),
        ('3.2.pl0', '3.1.1.6', 1),
        ('2g6', '11g', -1),
        ('0.960923', '2.2beta29', -1),
        ('1.13++', '5.5.kw', -1),
    ]
)
def test_version(v1, v2, wanted):

    v1 = audeer.Version(v1)

    result = v1._cmp(audeer.Version(v2))
    assert result == wanted

    result = v1._cmp(v2)
    assert result == wanted

    result = v1._cmp(object())
    assert result == NotImplemented

    assert v1.__repr__() == f"Version ('{str(v1)}')"


@pytest.mark.parametrize(
    'v1, v2, operator, expected',
    [
        ('1.5.1', '1.5.2b2', operator.eq, False),
        ('1.5.1', '1.5.2b2', operator.lt, True),
        ('1.5.1', '1.5.2b2', operator.le, True),
        ('1.5.1', '1.5.2b2', operator.gt, False),
        ('1.5.1', '1.5.2b2', operator.ge, False),
        ('1.5.1', '1.5.1', operator.eq, True),
        ('1.5.1', '1.5.1', operator.le, True),
        ('1.5.1', '1.5.1', operator.ge, True),
        ('161', '3.10a', operator.gt, True),
        ('8.02', '8.02', operator.eq, True),
        ('3.4j', '1996.07.12', operator.lt, True),
        ('3.2.pl0', '3.1.1.6', operator.gt, True),
        ('2g6', '11g', operator.lt, True),
        ('0.960923', '2.2beta29', operator.lt, True),
        ('1.13++', '5.5.kw', operator.lt, True),
    ]
)
def test_version_eq(v1, v2, operator, expected):
    result = operator(audeer.Version(v1), audeer.Version(v2))
    assert result == expected
