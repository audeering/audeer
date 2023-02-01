import pytest


@pytest.fixture(autouse=True)
def docdir(request):
    # set temporal working directory in docstring examples
    tmpdir = request.getfixturevalue('tmpdir')
    with tmpdir.as_cwd():
        yield
