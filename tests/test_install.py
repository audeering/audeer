import importlib
import subprocess
import sys

import pytest

import audeer


PACKAGE = 'audbackend'
MODULE = 'audbackend'


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
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # remove from module cache
    remove = []
    for module in sys.modules:
        if module.startswith(MODULE):
            remove.append(module)
    for module in remove:
        sys.modules.pop(module)


def test_install_package():

    # verify module is not installed
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(MODULE)

    # version not found
    with pytest.raises(subprocess.CalledProcessError):
        audeer.install_package(
            PACKAGE,
            version='999.0.0',
        )

    # install package
    audeer.install_package(
        PACKAGE,
        version='0.3.6',
    )

    # installed version satisfies requiested version
    audeer.install_package(
        PACKAGE,
        version='>=0.3.6',
    )
    audeer.install_package(
        PACKAGE,
        version='>0.3.5',
    )
    audeer.install_package(
        PACKAGE,
        version='<=0.3.6',
    )
    audeer.install_package(
        PACKAGE,
        version='<0.3.7',
    )
    audeer.install_package(
        PACKAGE,
        version=None,
    )

    # installed version does not satisfied requested version
    with pytest.raises(RuntimeError):
        audeer.install_package(
            PACKAGE,
            version='>=0.3.7',
        )
    with pytest.raises(RuntimeError):
        audeer.install_package(
            PACKAGE,
            version='>0.3.6',
        )
    with pytest.raises(RuntimeError):
        audeer.install_package(
            PACKAGE,
            version='<=0.3.5',
        )
    with pytest.raises(RuntimeError):
        audeer.install_package(
            PACKAGE,
            version='<0.3.6',
        )

    # invalid version string
    with pytest.raises(ValueError):
        audeer.install_package(
            PACKAGE,
            version='<=0.3.8,>0.3.5',
        )
