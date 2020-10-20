import os
import warnings

import pytest

import audeer


def test_deprecated():

    @audeer.deprecated(removal_version='1.0.0', alternative='audeer.mkdir')
    def deprecated_function():
        pass

    expected_message = (
        'deprecated_function is deprecated '
        'and will be removed with version 1.0.0.'
        ' Use audeer.mkdir instead.'
    )
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Raise warning
        deprecated_function()
        assert issubclass(w[-1].category, DeprecationWarning)
        assert expected_message == str(w[-1].message)

    @audeer.deprecated(removal_version='2.0.0')
    def deprecated_function():
        pass

    expected_message = (
        'deprecated_function is deprecated '
        'and will be removed with version 2.0.0.'
    )
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Raise warning
        deprecated_function()
        assert issubclass(w[-1].category, DeprecationWarning)
        assert expected_message == str(w[-1].message)

    @audeer.deprecated(removal_version='2.0.0')
    class DeprecatedClass():
        pass

    expected_message = (
        'DeprecatedClass is deprecated '
        'and will be removed with version 2.0.0.'
    )
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Raise warning
        DeprecatedClass()
        assert issubclass(w[-1].category, DeprecationWarning)
        assert expected_message == str(w[-1].message)


@pytest.mark.parametrize('nested_list,expected_list', [
    ([1, 2, 3, [4], [], [[[[[[[[[5]]]]]]]]]], [1, 2, 3, 4, 5]),
    ([[1, 2], 3], [1, 2, 3]),
    ([1, 2, 3], [1, 2, 3]),
])
def test_flatten_list(nested_list, expected_list):
    flattened_list = audeer.flatten_list(nested_list)
    assert flattened_list == expected_list


def test_freeze_requirements(tmpdir):
    path = str(tmpdir.mkdir('tmp'))
    outfile = os.path.join(path, 'requirements.txt.lock')
    audeer.freeze_requirements(outfile)
    with open(outfile) as f:
        requirements = f.readlines()
    # Remove whitespace and \n
    requirements = [r.strip() for r in requirements]
    assert any(['pytest' in r for r in requirements])
    assert any(['audeer' in r for r in requirements])
    with pytest.raises(RuntimeError, match=r'Freezing Python packages failed'):
        outfile = os.path.join(path, 'tmp2/requirements.txt.lock')
        audeer.freeze_requirements(outfile)


def power(a: int = 0, *, b: int = 1):
    return a ** b


@pytest.mark.parametrize(
    'multiprocessing',
    [
        True, False,
    ]
)
@pytest.mark.parametrize(
    'num_workers',
    [
        1, 3, None,
    ]
)
@pytest.mark.parametrize(
    'task_fun, params',
    [
        (power, [([], {})]),
        (power, [([1], {})]),
        (power, [([1], {'b': 2})]),
        (power, [([], {'a': 1, 'b': 2})]),
        (power, [([x], {'b': x}) for x in range(5)]),
    ]
)
def test_run_tasks(multiprocessing, num_workers, task_fun, params):
    expected = [
        task_fun(*param[0], **param[1]) for param in params
    ]
    results = audeer.run_tasks(
        task_fun,
        params,
        num_workers=num_workers,
        multiprocessing=multiprocessing,
    )
    assert expected == results


@pytest.mark.parametrize('func,params,expected_output', [
    (
        lambda x, n: x ** n,
        [(2, n) for n in range(7)],
        [1, 2, 4, 8, 16, 32, 64],
    ),
    (3, None, [None]),
    (lambda x: x, ['hello'], ['hello']),
    (lambda x: x, ['hello', 1, print], ['hello', 1, print]),
])
def test_run_worker_threads(func, params, expected_output):
    num_workers = [None, 1, 2, 4, 5, 100]
    for n in num_workers:
        output = audeer.run_worker_threads(func, params, num_workers=n)
        assert output == expected_output


@pytest.mark.parametrize(
    'input,expected_output',
    [
        (1, [1]),
        ('abc', ['abc']),
        (['abc', 1], ['abc', 1]),
        ((1, 2, 3), [1, 2, 3]),
        (len, [len]),
        ({1: 'a', 2: 'b'}, [1, 2]),
        ([], []),
        ('', ['']),
        (None, [None]),
    ],
)
def test_to_list(input, expected_output):
    assert audeer.to_list(input) == expected_output


@pytest.mark.parametrize(
    'from_string',
    [
        None,
        'example_string',
    ]
)
def test_uid(from_string):
    uid = audeer.uid(from_string=from_string)
    assert len(uid) == 36
    for pos in [8, 13, 18, 23]:
        assert uid[pos] == '-'
    uid2 = audeer.uid(from_string=from_string)
    if from_string is not None:
        assert uid == uid2
    else:
        assert uid != uid2
