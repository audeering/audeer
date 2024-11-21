# This code comes from
# https://github.com/python/cpython/blob/20a1c8ee4bcb1c421b7cca1f3f5d6ad7ce30a9c9/Lib/distutils/tests/test_version.py
# and is licensed under
# https://github.com/python/cpython/blob/20a1c8ee4bcb1c421b7cca1f3f5d6ad7ce30a9c9/LICENSE

import re


class Version:
    """Abstract base class for version numbering classes."""

    def __repr__(self):
        r"""Python code to recreate instance."""
        return f"{self.__class__.__name__} ('{str(self)}')"

    def __eq__(self, other):
        r"""Check if version equals another version."""
        c = self._cmp(other)
        return c == 0

    def __lt__(self, other):
        r"""Check if version is less than another version."""
        c = self._cmp(other)
        return c < 0

    def __le__(self, other):
        r"""Check if version is less or equal another version."""
        c = self._cmp(other)
        return c <= 0

    def __gt__(self, other):
        r"""Check if version is greater than another version."""
        c = self._cmp(other)
        return c > 0

    def __ge__(self, other):
        r"""Check if version is greater or equal another version."""
        c = self._cmp(other)
        return c >= 0


# Interface for version-number classes -- must be implemented
# by the following classes (the concrete ones -- Version should
# be treated as an abstract class).
#    __init__ (string) - create and take same action as 'parse'
#                        (string parameter is optional)
#    parse (string)    - convert a string representation to whatever
#                        internal representation is appropriate for
#                        this style of version numbering
#    __str__ (self)    - convert back to a string; should be very similar
#                        (if not identical to) the string supplied to parse
#    __repr__ (self)   - generate Python code to recreate
#                        the instance
#    _cmp (self, other) - compare two version numbers ('other' may
#                        be an unparsed version string, or another
#                        instance of your version class)


class StrictVersion(Version):
    """Version numbering for anal retentives and software idealists.

    This implementation was originally part of :mod:`distutils`
    as ``version.StrictVersion``.

    A version number consists of two
    or three dot-separated numeric components,
    with an optional "pre-release" tag on the end.
    The pre-release tag consists of the letter 'a' or 'b'
    followed by a number.
    If the numeric components of two version numbers are equal,
    then one with a pre-release tag
    will always be deemed earlier (lesser)
    than one without.

    The following are valid version numbers
    (shown in the order
    that would be obtained
    by sorting according to the supplied cmp function):
    ``'0.4'``,
    ``'0.4.1'``,
    ``'0.5a1'``,
    ``'0.5b3'``,
    ``'0.5'``,
    ``'0.9.6'``,
    ``'1.0'``,
    ``'1.0.4a3'``,
    ``'1.0.4b1'``,
    ``'1.0.4'``.

    The following are examples of invalid version numbers:
    ``'1'``,
    ``'2.7.2.2'``,
    ``'1.3.a4'``,
    ``'1.3pl1'``,
    ``'1.3c4'``.

    Args:
        version: version string

    Raises:
        ValueError: if ``version`` does not match
            the ``StrictVersion.version_re`` pattern

    Examples:
        >>> v1 = audeer.StrictVersion("1.17.2a1")
        >>> v1
        StrictVersion ('1.17.2a1')
        >>> v1.version
        (1, 17, 2)
        >>> v1.prerelease
        ('a', 1)
        >>> v2 = audeer.StrictVersion("1.17.2")
        >>> v1 < v2
        True

    """

    version_re = re.compile(
        r"^(\d+) \. (\d+) (\. (\d+))? ([ab](\d+))?$", re.VERBOSE | re.ASCII
    )
    """Version regexp pattern.

    The regexp pattern is used to split the version
    into
    *major*,
    *minor*,
    *patch*,
    *prerelease*,
    *prerelease number*
    when parsing it.

    """

    def __init__(self, version=None):
        self.version = None
        r"Parsed version."
        self.prerelease = None
        r"Parsed prerelease part of version."

        if version:
            self.parse(version)

    def parse(self, version):
        r"""Parse a version string.

        When called this updates the stored version
        under ``self.version``.

        Args:
            version: version string

        """
        match = self.version_re.match(version)
        if not match:
            raise ValueError(f"invalid version number '{version}'")

        (major, minor, patch, prerelease, prerelease_num) = match.group(1, 2, 4, 5, 6)

        if patch:
            self.version = tuple(map(int, [major, minor, patch]))
        else:
            self.version = tuple(map(int, [major, minor])) + (0,)

        if prerelease:
            self.prerelease = (prerelease[0], int(prerelease_num))
        else:
            self.prerelease = None

    def __str__(self):
        r"""String representation of version."""
        if self.version[2] == 0:
            vstring = ".".join(map(str, self.version[0:2]))
        else:
            vstring = ".".join(map(str, self.version))

        if self.prerelease:
            vstring = vstring + self.prerelease[0] + str(self.prerelease[1])

        return vstring

    def _cmp(self, other):
        if isinstance(other, str):
            other = StrictVersion(other)
        elif not isinstance(other, StrictVersion):
            return NotImplemented

        if self.version != other.version:
            # numeric versions don't match
            # prerelease stuff doesn't matter
            if self.version < other.version:
                return -1
            else:
                return 1

        # have to compare prerelease
        # case 1: neither has prerelease; they're equal
        # case 2: self has prerelease, other doesn't; other is greater
        # case 3: self doesn't have prerelease, other does: self is greater
        # case 4: both have prerelease: must compare them!

        if not self.prerelease and not other.prerelease:
            return 0
        elif self.prerelease and not other.prerelease:
            return -1
        elif not self.prerelease and other.prerelease:
            return 1
        elif self.prerelease and other.prerelease:
            if self.prerelease == other.prerelease:
                return 0
            elif self.prerelease < other.prerelease:
                return -1
            else:
                return 1


# The rules according to Greg Stein:
# 1) a version number has 1 or more numbers separated by a period or by
#    sequences of letters. If only periods, then these are compared
#    left-to-right to determine an ordering.
# 2) sequences of letters are part of the tuple for comparison and are
#    compared lexicographically
# 3) recognize the numeric components may have leading zeroes
#
# The LooseVersion class below implements these rules: a version number
# string is split up into a tuple of integer and string components, and
# comparison is a simple tuple comparison.  This means that version
# numbers behave in a predictable and obvious way, but a way that might
# not necessarily be how people *want* version numbers to behave.  There
# wouldn't be a problem if people could stick to purely numeric version
# numbers: just split on period and compare the numbers as tuples.
# However, people insist on putting letters into their version numbers;
# the most common purpose seems to be:
#   - indicating a "pre-release" version
#     ('alpha', 'beta', 'a', 'b', 'pre', 'p')
#   - indicating a post-release patch ('p', 'pl', 'patch')
# but of course this can't cover all version number schemes, and there's
# no way to know what a programmer means without asking him.
#
# The problem is what to do with letters (and other non-numeric
# characters) in a version number.  The current implementation does the
# obvious and predictable thing: keep them as strings and compare
# lexically within a tuple comparison.  This has the desired effect if
# an appended letter sequence implies something "post-release":
# eg. "0.99" < "0.99pl14" < "1.0", and "5.001" < "5.001m" < "5.002".
#
# However, if letters in a version number imply a pre-release version,
# the "obvious" thing isn't correct.  Eg. you would expect that
# "1.5.1" < "1.5.2a2" < "1.5.2", but under the tuple/lexical comparison
# implemented here, this just isn't so.


class LooseVersion(Version):
    r"""Version numbering for anarchists and software realists.

    This implementation was originally part of :mod:`distutils`
    as ``version.LooseVersion``.

    A version number consists of a series of numbers,
    separated by either periods or strings of letters.
    When comparing version numbers,
    the numeric components will be compared numerically,
    and the alphabetic components lexically.
    The following are all valid version numbers,
    in no particular order:
    ``'1.5.1``,
    ``'1.5.2b2``,
    ``'161'``,
    ``'3.10a'``,
    ``'8.02'``,
    ``'3.4j'``,
    ``'1996.07.12'``,
    ``'3.2.pl0'``,
    ``'3.1.1.6'``,
    ``'2g6'``,
    ``'11g'``,
    ``'0.960923'``,
    ``'2.2beta29'``,
    ``'1.13++'``,
    ``'5.5.kw'``,
    ``'2.0b1pl0'``.

    Args:
        version: version string

    Examples:
        >>> v1 = audeer.LooseVersion("1.17.2")
        >>> v1
        LooseVersion ('1.17.2')
        >>> v1.version
        [1, 17, 2]
        >>> v2 = audeer.LooseVersion("1.17.2-3-g70b71bd")
        >>> v1 < v2
        True

    """

    version_re = re.compile(r"(\d+ | [a-z]+ | \.)", re.VERBOSE)
    """Version regexp pattern.

    The regexp pattern is used to split the version
    into single components
    when parsing it.

    """

    def __init__(self, version=None):
        self.version = None
        r"Parsed version."

        if version:
            self.parse(version)

    def __eq__(self, other):  # noqa: D105 (inherited)
        c = self._cmp(other)
        return c == 0

    def __lt__(self, other):  # noqa: D105 (inherited)
        c = self._cmp(other)
        return c < 0

    def __le__(self, other):  # noqa: D105 (inherited)
        c = self._cmp(other)
        return c <= 0

    def __gt__(self, other):  # noqa: D105 (inherited)
        c = self._cmp(other)
        return c > 0

    def __ge__(self, other):  # noqa: D105 (inherited)
        c = self._cmp(other)
        return c >= 0

    def __str__(self):
        r"""String representation of version."""
        return self.vstring

    def parse(self, version):
        r"""Parse a version string.

        When called this updates the stored version
        under ``self.version``.

        Args:
            version: version string

        """
        # I've given up on thinking I can reconstruct the version string
        # from the parsed tuple -- so I just store the string here for
        # use by __str__
        self.vstring = version
        components = [x for x in self.version_re.split(version) if x and x != "."]
        for i, obj in enumerate(components):
            try:
                components[i] = int(obj)
            except ValueError:
                pass

        self.version = components

    def _cmp(self, other):
        if isinstance(other, str):
            other = LooseVersion(other)
        elif not isinstance(other, LooseVersion):
            return NotImplemented

        if self.version == other.version:
            return 0
        if self.version < other.version:
            return -1
        if self.version > other.version:
            return 1
