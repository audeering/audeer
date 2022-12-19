import os
import platform
import typing


# Exclude common_directory example from doctest
# on Windows and MacOS
# (which adds /System/Volumes/Data in front in the Github runner)
# as it outputs a path in Linux syntax in the example
if platform.system() in ['Darwin', 'Windows']:  # pragma: no cover
    __doctest_skip__ = [
        'path',
        'safe_path',
    ]


def path(
        path: typing.Union[str, bytes],
        *paths: typing.Sequence[typing.Union[str, bytes]],
) -> str:
    """Expand and normalize to absolute path.

    It uses :func:`os.path.realpath`
    and :func:`os.path.expanduser`
    to ensure an absolute path
    without ``..`` or ``~``,
    and independent of the path separator
    of the operating system.

    Args:
        path: path to file, directory
        *paths: additional arguments
            to be joined with ``path``
            by :func:`os.path.join`

    Returns:
        (joined and) expanded path

    Examples:
        >>> home = path('~')
        >>> folder = path('~/path/.././path')
        >>> folder[len(home) + 1:]
        'path'
        >>> file = path('~/path/.././path', './file.txt')
        >>> file[len(home) + 1:]
        'path/file.txt'

    """
    if paths:
        path = os.path.join(path, *paths)
    if path:
        path = os.path.realpath(os.path.expanduser(path))
        # Convert bytes to str, see https://stackoverflow.com/a/606199
        if type(path) == bytes:
            path = path.decode('utf-8').strip('\x00')
    return path


# Ensure function is not hidden
# by `path` argument in `safe_path()`
_path = path


def safe_path(
        path: typing.Union[str, bytes],
        *paths: typing.Sequence[typing.Union[str, bytes]],
) -> str:
    """Expand and normalize to absolute path.

    It uses :func:`os.path.realpath`
    and :func:`os.path.expanduser`
    to ensure an absolute path
    without ``..`` or ``~``,
    and independent of the path separator
    of the operating system.

    Warning:
        :func:`audeer.safe_path` is deprecated,
        please use :func:`audeer.path` instead.

    Args:
        path: path to file, directory
        *paths: additional arguments
            to be joined with ``path``
            by :func:`os.path.join`

    Returns:
        (joined and) expanded path

    Examples:
        >>> home = safe_path('~')
        >>> folder = safe_path('~/path/.././path')
        >>> folder[len(home) + 1:]
        'path'
        >>> file = safe_path('~/path/.././path', './file.txt')
        >>> file[len(home) + 1:]
        'path/file.txt'

    """
    return _path(path, *paths)
