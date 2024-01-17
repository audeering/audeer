import importlib
import subprocess
import sys

import pytest

import audeer


PACKAGE = "PyYaml"
MODULE = "yaml"


def uninstall():
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "uninstall",
            "--yes",
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


@pytest.fixture(autouse=True)
def run_around_tests():
    yield
    uninstall()


def test():
    # verify module is not installed
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(MODULE)

    # version not found
    with pytest.raises(subprocess.CalledProcessError):
        audeer.install_package(
            PACKAGE,
            version="999.0.0",
        )

    # install package
    audeer.install_package(
        PACKAGE,
        version="<=5.3",
    )

    # installed version satisfies requested version
    audeer.install_package(
        PACKAGE,
        version=">=5.3",
    )
    audeer.install_package(
        PACKAGE,
        version=">5.2",
    )
    audeer.install_package(
        PACKAGE,
        version="<=6.0",
    )
    audeer.install_package(
        PACKAGE,
        version="  <   5.4  ",  # whitespace will be ignored
    )
    audeer.install_package(
        PACKAGE,
        version=None,
    )

    # installed version does not satisfied requested version
    with pytest.raises(RuntimeError):
        audeer.install_package(
            PACKAGE,
            version=">=5.4",
        )
    with pytest.raises(RuntimeError):
        audeer.install_package(
            PACKAGE,
            version=">5.3",
        )
    with pytest.raises(RuntimeError):
        audeer.install_package(
            PACKAGE,
            version="<=5.2",
        )
    with pytest.raises(RuntimeError):
        audeer.install_package(
            PACKAGE,
            version="<5.3",
        )
