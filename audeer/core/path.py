import os
import platform
import typing


# Exclude common_directory example from doctest
# on Windows and MacOS
# (which adds /System/Volumes/Data in front in the Github runner)
# as it outputs a path in Linux syntax in the example
if platform.system() in ["Darwin", "Windows"]:  # pragma: no cover
    __doctest_skip__ = [
        "path",
        "safe_path",
    ]


def path(
    path: typing.Union[str, bytes],
    *paths: typing.Sequence[typing.Union[str, bytes]],
    follow_symlink: bool = False,
) -> str:
    """Expand and normalize to absolute path.

    It uses :func:`os.path.realpath`
    and :func:`os.path.expanduser`
    to ensure an absolute path
    without ``..`` or ``~``,
    and independent of the path separator
    of the operating system.
    If ``follow_symlink`` is ``False``,
    the faster :func:`os.path.abspath` is used
    instead of :func:`os.path.realpath`.

    Args:
        path: path to file, directory
        *paths: additional arguments
            to be joined with ``path``
            by :func:`os.path.join`
        follow_symlink: if ``True``
            symlinks are followed
            and the path of the original file
            is returned

    Returns:
        (joined and) expanded path

    Examples:
        >>> home = path("~")
        >>> folder = path("~/path/.././path")
        >>> folder[len(home) + 1 :]
        'path'
        >>> file = path("~/path/.././path", "./file.txt")
        >>> file[len(home) + 1 :]
        'path/file.txt'
        >>> file = audeer.touch("file.txt")
        >>> link = path("link.txt")
        >>> os.symlink(file, link)
        >>> os.path.basename(path(link))
        'link.txt'
        >>> os.path.basename(path(link, follow_symlink=True))
        'file.txt'

    """
    if paths:
        path = os.path.join(path, *paths)
    if path:
        path = os.path.expanduser(path)
        if follow_symlink:
            path = os.path.realpath(path)
        else:
            path = os.path.abspath(path)
        # Convert bytes to str, see https://stackoverflow.com/a/606199
        if isinstance(path, bytes):
            path = path.decode("utf-8").strip("\x00")
    return path


# Ensure function is not hidden
# by `path` argument in `safe_path()`
_path = path


def safe_path(
    path: typing.Union[str, bytes],
    *paths: typing.Sequence[typing.Union[str, bytes]],
    follow_symlink: bool = False,
) -> str:
    """Expand and normalize to absolute path.

    It uses :func:`os.path.realpath`
    and :func:`os.path.expanduser`
    to ensure an absolute path
    without ``..`` or ``~``,
    and independent of the path separator
    of the operating system.
    If ``follow_symlink`` is ``False``,
    the faster :func:`os.path.abspath` is used
    instead of :func:`os.path.realpath`.

    Warning:
        :func:`audeer.safe_path` is deprecated,
        please use :func:`audeer.path` instead.

    Args:
        path: path to file, directory
        *paths: additional arguments
            to be joined with ``path``
            by :func:`os.path.join`
        follow_symlink: if ``True``
            symlinks are followed
            and the path of the original file
            is returned

    Returns:
        (joined and) expanded path

    Examples:
        >>> home = safe_path("~")
        >>> folder = safe_path("~/path/.././path")
        >>> folder[len(home) + 1 :]
        'path'
        >>> file = safe_path("~/path/.././path", "./file.txt")
        >>> file[len(home) + 1 :]
        'path/file.txt'
        >>> file = audeer.touch("file.txt")
        >>> link = path("link.txt")
        >>> os.symlink(file, link)
        >>> os.path.basename(path(link))
        'link.txt'
        >>> os.path.basename(path(link, follow_symlink=True))
        'file.txt'

    """
    return _path(path, *paths, follow_symlink=follow_symlink)
