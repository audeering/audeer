from doctest import ELLIPSIS
import os

import pytest
import sybil
from sybil.parsers.rest import DocTestParser
from sybil.parsers.rest import SkipParser


# Collect doctests
pytest_collect_file = sybil.Sybil(
    parsers=[DocTestParser(optionflags=ELLIPSIS), SkipParser()],
    patterns=["*.py"],
    fixtures=["run_in_tmpdir"],
).pytest()


@pytest.fixture(scope="function")
def run_in_tmpdir(tmpdir_factory):
    """Move to a persistent tmpdir for execution of a whole file."""
    tmpdir = tmpdir_factory.mktemp("tmp")
    current_dir = os.getcwd()
    os.chdir(tmpdir)

    yield

    os.chdir(current_dir)
