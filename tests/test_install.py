import importlib
import subprocess
import sys

import pytest

import audeer


PACKAGE = 'PyYaml'
MODULE = 'yaml'
VERSION = '5.4'


@pytest.fixture(autouse=True)
def run_around_tests():
    yield
    # uninstall audbackend
    subprocess.check_call(
        [
            sys.executable,
            '-m',
            'pip',
            'uninstall',
            '--yes',
            PACKAGE,
        ]
    )
    # remove from module cache
    remove = []
    for module in sys.modules:
        if module.startswith(MODULE):
            remove.append(module)
    for module in remove:
        sys.modules.pop(module)


@pytest.mark.parametrize(
    'version',
    [None, VERSION],
)
def test_install_package(version):

    # verify module is not installed
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(MODULE)

    # install package
    audeer.install_package(
        PACKAGE,
        version=version,
    )

    # import module and verify version
    m = importlib.import_module(MODULE)
    if version is not None:
        m.__version__ == version
