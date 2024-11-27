import sybil
from sybil.parsers.rest import DocTestParser
from sybil.parsers.rest import PythonCodeBlockParser


pytest_collect_file = sybil.Sybil(
    parsers=[DocTestParser(), PythonCodeBlockParser()],
    pattern="*.rst",
).pytest()
