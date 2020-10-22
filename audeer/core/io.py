from glob import glob
import itertools
import os
import shutil
import tarfile
import typing
import zipfile

from audeer.core.tqdm import (
    format_display_message,
    progress_bar,
)


def basename_wo_ext(
        path: typing.Union[str, bytes],
        *,
        ext: str = None
) -> str:
    """File basename without file extension.

    Args:
        path: file or directory name
        ext: explicit extension to be removed

    Returns:
        basename of directory or file without extension

    Example:

        >>> path = '/test/file.wav'
        >>> basename_wo_ext(path)
        'file'

    """
    path = safe_path(path)
    path = os.path.basename(path)
    if ext is not None:
        if not ext.startswith('.'):
            ext = '.' + ext  # 'mp3' => '.mp3'
        if path.endswith(ext):
            path = path[:-len(ext)]
    else:
        path = os.path.splitext(path)[0]
    return path


def common_directory(
    dirs: typing.Sequence[str],
    *,
    sep: str = os.path.sep,
) -> str:
    r"""Find common directory path.

    Args:
        dirs: list of directories
        sep: path separator

    Returns:
        part of the directory tree that is common to all the directories

    Example:
        >>> paths = [
        ...     '/home/user1/tmp/coverage/test',
        ...     '/home/user1/tmp/covert/operator',
        ...     '/home/user1/tmp/coven/members',
        ... ]
        >>> common_directory(paths)
        '/home/user1/tmp'

    """
    def all_names_equal(name):
        return all(n == name[0] for n in name[1:])

    dirs = [safe_path(path) for path in dirs]
    by_directory_levels = zip(*[p.split(sep) for p in dirs])
    return sep.join(x[0] for x in itertools.takewhile(
        all_names_equal, by_directory_levels,
    ))


def extract_archive(
        archive: str,
        destination: str,
        *,
        keep_archive: bool = True,
        verbose: bool = False,
):
    r"""Extract a ZIP or TAR.GZ file.

    Args:
        archive: path to ZIP or TAR.GZ file
        destination: folder where the content should be stored.
            Will be created if it doesn't exist
        keep_archive: if ``False`` delete archive file after extraction
        verbose: if ``True`` a progress bar is shown

    Raises:
        RuntimeError: if the provided archive is not a ZIP or TAR.GZ file
        RuntimeError: if the archive file is malformed

    """
    destination = safe_path(destination)
    if os.path.exists(destination):
        destination_created = False
    else:
        mkdir(destination)
        destination_created = True

    # Progress bar arguments
    desc = format_display_message(
        f'Extract {os.path.basename(archive)}',
        pbar=True,
    )
    disable = not verbose

    try:
        if archive.endswith('zip'):
            with zipfile.ZipFile(archive, 'r') as zf:
                members = zf.infolist()
                with progress_bar(
                    total=len(members),
                    desc=desc,
                    disable=disable,
                ) as pbar:
                    for member in members:
                        zf.extract(member, destination)
                        pbar.update()
        elif archive.endswith('tar.gz'):
            with tarfile.open(archive, 'r') as tf:
                members = tf.getmembers()
                with progress_bar(
                    total=len(members),
                    desc=desc,
                    disable=disable,
                ) as pbar:
                    for member in members:
                        tf.extract(member, destination, numeric_owner=True)
                        pbar.update()
        else:
            raise RuntimeError(
                f'You can only extract ZIP and TAR.GZ files, '
                f'not {archive}'
            )
    except (EOFError, zipfile.BadZipFile, tarfile.ReadError):
        raise RuntimeError(f'Broken archive: {archive}')
    except (KeyboardInterrupt, Exception):  # pragma: nocover
        # Clean up broken extraction files
        if destination_created:
            if os.path.exists(destination):
                shutil.rmtree(destination)
        raise

    if not keep_archive:
        os.remove(archive)


def extract_archives(
        archives: typing.Sequence[str],
        destination: str,
        *,
        keep_archive: bool = True,
        verbose: bool = False,
):
    r"""Extract ZIP or TAR.GZ archives.

    Args:
        archives: paths of ZIP or TAR.GZ files
        destination: folder where the content should be stored.
            Will be created if it doesn't exist
        keep_archive: if ``False`` delete archive files after extraction
        verbose: if ``True`` a progress bar is shown

    """
    with progress_bar(
        total=len(archives),
        disable=not verbose,
    ) as pbar:
        for archive in archives:
            desc = format_display_message(
                f'Extract {os.path.basename(archive)}',
                pbar=True,
            )
            pbar.set_description_str(desc)
            pbar.refresh()
            extract_archive(
                archive,
                destination,
                keep_archive=keep_archive,
                verbose=False,
            )
            pbar.update()


def file_extension(
        path: typing.Union[str, bytes]
) -> str:
    """File extension.

    Args:
        path: path to file

    Returns:
        extension of file without "."

    Example:
        >>> path = '/test/file.wav'
        >>> file_extension(path)
        'wav'

    """
    path = safe_path(path)
    return os.path.splitext(path)[-1][1:]


def list_file_names(
        path: typing.Union[str, bytes],
        *,
        filetype: str = ''
) -> typing.List:
    """List of file names inferred from provided path.

    Args:
        path: path to file, directory or pattern
        filetype: optional consider only this filetype

    Returns:
        list of path(s) to file(s)

    Example:
        >>> path = mkdir('path1')
        >>> open(os.path.join(path, 'file1'), 'a').close()
        >>> [os.path.basename(p) for p in list_file_names(path)]
        ['file1']

    """
    path = safe_path(path)
    if os.path.isfile(path):
        search_pattern = path
    else:
        if os.path.isdir(path):
            # Ensure / at the end
            path = os.path.join(path, '')
        search_pattern = f'{path}*{filetype}'
    # Get list of files matching search pattern
    file_names = sorted(glob(search_pattern))
    return [f for f in file_names if not os.path.isdir(f)]


def mkdir(
        path: typing.Union[str, bytes],
        *,
        mode: int = 0o777
) -> str:
    """Create directory.

    Create a directory at the provided path
    and return the absolute path to the generated directory.
    If parent directories are missing,
    they are created as well.
    If the directory exists already,
    only its absolute path is returned.

    On some systems, mode is ignored.
    Where it is used, the current umask value is first masked out.
    If bits other than the last 9
    (i.e. the last 3 digits of the octal representation of the mode)
    are set,
    their meaning is platform-dependent.
    On some platforms, they are ignored
    and you should call :func:`os.chmod`
    explicitly to set them.

    Args:
        path: absolute or relative path of directory to create
        mode: set permissions of created folders

    Returns:
        absolute path to the created directory

    Example:
        >>> p = mkdir('path1/path2/path3')
        >>> os.path.basename(p)
        'path3'

    """
    path = safe_path(path)
    if path:
        os.makedirs(path, mode=mode, exist_ok=True)
    return path


def safe_path(
        path: typing.Union[str, bytes]
) -> str:
    """Ensure the path is absolute and doesn't include `..` or `~`.

    Args:
        path: path to file, directory

    Returns:
        expanded path

    Example:
        >>> home = safe_path('~')
        >>> path = safe_path('~/path/.././path')
        >>> path[len(home):]
        '/path'

    """
    if path:
        path = os.path.realpath(os.path.expanduser(path))
        # Convert bytes to str, see https://stackoverflow.com/a/606199
        if type(path) == bytes:
            path = path.decode('utf-8').strip('\x00')
    return path