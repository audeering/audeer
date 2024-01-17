import pytest

import audeer


@pytest.fixture(autouse=True)
def docdir(doctest_namespace, request):
    # make sure audeer is imported
    doctest_namespace["audeer"] = audeer
    # set temporal working directory in docstring examples
    tmpdir = request.getfixturevalue("tmpdir")
    with tmpdir.as_cwd():
        yield
