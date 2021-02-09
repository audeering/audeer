import os
import subprocess
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
        assert issubclass(w[-1].category, UserWarning)
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
        assert issubclass(w[-1].category, UserWarning)
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
        assert issubclass(w[-1].category, UserWarning)
        assert expected_message == str(w[-1].message)


def test_deprecated_default_value():

    @audeer.deprecated_default_value(
        argument='foo',
        new_default_value='bar',
        change_in_version='1.0.0',
    )
    def function_with_deprecated_default_value(*, foo='foo'):
        return foo

    expected_message = (
        "The default of 'foo' will change from "
        "'foo' to 'bar' "
        "with version 1.0.0."
    )
    default_value = 'foo'
    with pytest.warns(None):
        # no warning if we set value
        function_with_deprecated_default_value(foo='foo')
        function_with_deprecated_default_value(foo='bar')
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Raise warning
        assert function_with_deprecated_default_value() == default_value
        assert issubclass(w[-1].category, UserWarning)
        assert expected_message == str(w[-1].message)


def test_deprecated_keyword_argument():

    @audeer.deprecated_keyword_argument(
        deprecated_argument='foo',
        new_argument='bar',
        removal_version='1.0.0',
        mapping=lambda x: 2 * x,
    )
    def function_with_deprecated_keyword_argument(*, bar):
        return bar

    expected_message = (
        "'foo' argument is deprecated "
        "and will be removed with version 1.0.0."
        " Use 'bar' instead."
    )
    value = 1
    assert function_with_deprecated_keyword_argument(bar=value) == value
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Raise warning
        r = function_with_deprecated_keyword_argument(foo=value)
        assert issubclass(w[-1].category, UserWarning)
        assert expected_message == str(w[-1].message)
        assert r == 2 * value

    @audeer.deprecated_keyword_argument(
        deprecated_argument='foo',
        removal_version='1.0.0',
    )
    def function_with_deprecated_keyword_argument(**kwargs):
        return 1

    expected_message = (
        "'foo' argument is deprecated "
        "and will be removed with version 1.0.0."
    )
    assert function_with_deprecated_keyword_argument() == 1
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Raise warning
        r = function_with_deprecated_keyword_argument(foo=2)
        assert issubclass(w[-1].category, UserWarning)
        assert expected_message == str(w[-1].message)
        assert r == 1

    @audeer.deprecated_keyword_argument(
        deprecated_argument='foo',
        new_argument='bar',
        removal_version='1.0.0',
    )
    class class_with_deprecated_keyword_argument(object):

        def __init__(self, *, bar):
            self.bar = bar

    expected_message = (
        "'foo' argument is deprecated "
        "and will be removed with version 1.0.0."
        " Use 'bar' instead."
    )
    value = 1
    assert class_with_deprecated_keyword_argument(bar=value).bar == value
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Raise warning
        r = class_with_deprecated_keyword_argument(foo=value)
        assert issubclass(w[-1].category, UserWarning)
        assert expected_message == str(w[-1].message)
        assert r.bar == value


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


def test_git_repo_tags():
    git = ['git', 'tag']
    expected_tags = subprocess.check_output(git)
    expected_tags = expected_tags.decode().strip().split('\n')
    tags = audeer.git_repo_tags()
    assert tags == expected_tags
    tags = audeer.git_repo_tags(v=True)
    expected_tags = [
        f'v{t}' if not t.startswith('v') else t for t in expected_tags
    ]
    assert tags == expected_tags
    tags = audeer.git_repo_tags(v=False)
    expected_tags = [
        t[1:] if t.startswith('v') else t for t in expected_tags
    ]
    assert tags == expected_tags


def test_git_repo_version():
    git = ['git', 'describe', '--tags', '--always']
    expected_version = subprocess.check_output(git)
    expected_version = expected_version.decode().strip()
    version = audeer.git_repo_version(v=True)
    if not expected_version.startswith('v'):
        expected_version = f'v{expected_version}'
    assert version == expected_version
    version = audeer.git_repo_version(v=False)
    assert version == expected_version[1:]


@pytest.mark.parametrize(
    'version, is_semantic',
    [
        (
            '1.0.0',
            True,
        ),
        (
            'v1.0.0',
            True,
        ),
        (
            '4.0.0-20200206.095534-3',
            True,
        ),
        (
            'v1.0.1-1-gdf29c4a',
            True,
        ),
        (
            '1',
            False,
        ),
        (
            'v1',
            False,
        ),
        (
            'v1.3-r3',
            False,
        ),
        (
            'v1.3.3-r3',
            True,
        ),
        (
            'a.b.c',
            False,
        ),
        (
            'va.b.c',
            False,
        ),
        (
            '1.2.a',
            False,
        ),
        (
            'v1.3.3.3-r3',
            False,
        ),
        (
            '1.0.0+20130313144700',
            True,
        ),
        (
            '1.0.0-alpha+001',
            True,
        ),
    ]
)
def test_is_semantic_version(version, is_semantic):
    assert audeer.is_semantic_version(version) == is_semantic


@pytest.mark.parametrize(
    'uid, expected',
    [
        (audeer.uid(), True),
        (audeer.uid(from_string='from string'), True),
        (None, False),
        (1234, False),
        ('', False),
        ('some random string', False),
        (audeer.uid()[:-1], False),
    ]
)
def test_is_uid(uid, expected):
    assert audeer.is_uid(uid) == expected


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
        with pytest.warns(UserWarning):
            output = audeer.run_worker_threads(func, params, num_workers=n)
        assert output == expected_output


@pytest.mark.parametrize(
    'versions, expected_versions',
    [
        (
            ['1.0.0', '3.0.0', '1.10.1', '1.2.0', '1.0.1'],
            ['1.0.0', '1.0.1', '1.2.0', '1.10.1', '3.0.0'],
        ),
        (
            [
                '1.0.0-SNAPSHOT',
                '4.0.0-20200206.095424-2',
                '1.0.0',
                '2.0.0-20200131.102442-1',
                '3.0.0',
                '3.1.0',
                '4.0.0-20200206.095316-1',
                '3.2.0',
                '2.0.0-20200131.102728-2',
                '3.3.0',
                '3.4.0',
                '4.0.0-20200206.095534-3',
                '4.0.0',
            ],
            [
                '1.0.0',
                '1.0.0-SNAPSHOT',
                '2.0.0-20200131.102442-1',
                '2.0.0-20200131.102728-2',
                '3.0.0',
                '3.1.0',
                '3.2.0',
                '3.3.0',
                '3.4.0',
                '4.0.0',
                '4.0.0-20200206.095316-1',
                '4.0.0-20200206.095424-2',
                '4.0.0-20200206.095534-3',
            ],
        ),
        (
            ['v1.0.0', 'v1.0.1', 'v1.0.1-1-gdf29c4a'],
            ['v1.0.0', 'v1.0.1', 'v1.0.1-1-gdf29c4a'],
        ),
        # From https://github.com/postmarketOS/pmbootstrap/issues/342
        (
            ['22.7.3-r1.3', '22.7.3-r1'],
            ['22.7.3-r1', '22.7.3-r1.3'],
        ),
        (
            ['1.0.0', '1.1.1+1', '1.2.1', '1.2.0'],
            ['1.0.0', '1.1.1+1', '1.2.0', '1.2.1'],
        ),
    ]
)
def test_sort_versions(versions, expected_versions):
    sorted_versions = audeer.sort_versions(versions)
    assert sorted_versions == expected_versions


@pytest.mark.parametrize(
    'versions, error_message',
    [
        (
            ['1'],
            (
                "All version numbers have to be semantic versions, "
                "following 'X.Y.Z', "
                "where X, Y, Z are integers. "
                "But your version is: '1'."
            ),
        ),
    ]
)
def test_sort_versions_errors(versions, error_message):
    with pytest.raises(ValueError, match=error_message):
        audeer.sort_versions(versions)


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
