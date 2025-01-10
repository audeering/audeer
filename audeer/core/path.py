from __future__ import annotations

from collections.abc import Sequence
import os


def path(
    path: str | bytes,
    *paths: Sequence[str | bytes],
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
        .. skip: start if(platform.system() == "Windows")

        >>> home = audeer.path("~")
        >>> folder = audeer.path("~/path/.././path")
        >>> folder[len(home) + 1 :]
        'path'
        >>> file = audeer.path("~/path/.././path", "./file.txt")
        >>> file[len(home) + 1 :]
        'path/file.txt'
        >>> file = audeer.touch("file.txt")
        >>> link = audeer.path("link.txt")
        >>> os.symlink(file, link)
        >>> os.path.basename(audeer.path(link))
        'link.txt'
        >>> os.path.basename(audeer.path(link, follow_symlink=True))
        'file.txt'

        .. skip: end

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
    path: str | bytes,
    *paths: Sequence[str | bytes],
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
        .. skip: start if(platform.system() == "Windows")

        >>> home = audeer.safe_path("~")
        >>> folder = audeer.safe_path("~/path/.././path")
        >>> folder[len(home) + 1 :]
        'path'
        >>> file = audeer.safe_path("~/path/.././path", "./file.txt")
        >>> file[len(home) + 1 :]
        'path/file.txt'
        >>> file = audeer.touch("file.txt")
        >>> link = audeer.path("link.txt")
        >>> os.symlink(file, link)
        >>> os.path.basename(audeer.path(link))
        'link.txt'
        >>> os.path.basename(audeer.path(link, follow_symlink=True))
        'file.txt'

        .. skip: end

    """
    return _path(path, *paths, follow_symlink=follow_symlink)
