import fnmatch
import itertools
import os
import platform
import shutil
import tarfile
import typing
import urllib.request
import zipfile

from audeer.core.path import path as safe_path
from audeer.core.tqdm import (
    format_display_message,
    progress_bar,
)
from audeer.core.utils import to_list


# Exclude common_directory example from doctest
# on Windows and MacOS
# (which adds /System/Volumes/Data in front in the Github runner)
# as it outputs a path in Linux syntax in the example
if platform.system() in ['Darwin', 'Windows']:  # pragma: no cover
    __doctest_skip__ = [
        'common_directory',
        'list_dir_names',
        'list_file_names',
    ]


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

    Examples:

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

    Examples:
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


def create_archive(
        root: str,
        files: typing.Union[str, typing.Sequence[str]],
        archive: str,
        *,
        verbose: bool = False,
):
    r"""Create ZIP or TAR.GZ archive.

    Args:
        root: path to root folder of archive.
            Path names inside the archive
            will be relative to ``root``
        files: files to include in archive,
            relative to ``root``
        archive: path to archive file.
            The archive type is determined by the file extension
        verbose: if ``True`` a progress bar is shown

    Raises:
        RuntimeError: if archive does not end with ``zip`` or ``tar.gz``

    """
    archive = safe_path(archive)
    mkdir(os.path.dirname(archive))
    files = to_list(files)

    # Progress bar arguments
    desc = format_display_message(
        f'Create {os.path.basename(archive)}',
        pbar=True,
    )
    disable = not verbose

    if archive.endswith('zip'):
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in progress_bar(files, desc=desc, disable=disable):
                full_file = os.path.join(root, file)
                zf.write(full_file, arcname=file)
    elif archive.endswith('tar.gz'):
        with tarfile.open(archive, "w:gz") as tf:
            for file in progress_bar(files, desc=desc, disable=disable):
                full_file = os.path.join(root, file)
                tf.add(full_file, file)
    else:
        raise RuntimeError(
            f'You can only create a ZIP or TAR.GZ archive, '
            f'not {archive}'
        )


def download_url(
        url: str,
        destination: str,
        *,
        force_download: bool = False,
        verbose: bool = False,
) -> str:
    r"""Download URL to destination.

    Args:
        url: URL of file to download
        destination: file or folder to store file locally
        force_download: if ``True`` forces the artifact to be downloaded
            even if it exists locally already
        verbose: if ``True`` a progress bar is shown

    Returns:
        path of locally stored file

    Examples:
        >>> dst = download_url('https://audeering.github.io/audeer/_static/favicon.png', '.')
        >>> os.path.basename(dst)
        'favicon.png'

    """  # noqa: E501
    destination = safe_path(destination)
    if os.path.isdir(destination):
        destination = os.path.join(destination, os.path.basename(url))
    if os.path.exists(destination) and not force_download:
        return destination

    with progress_bar(
            disable=not verbose,
            desc=format_display_message(f'Downloading {url}', pbar=True),
    ) as pbar:

        def bar_update(block_num, block_size, total_size):
            if pbar.total is None and total_size:
                pbar.total = total_size
            pbar.update(block_size)

        urllib.request.urlretrieve(url, destination, reporthook=bar_update)

    return destination


def extract_archive(
        archive: str,
        destination: str,
        *,
        keep_archive: bool = True,
        verbose: bool = False,
) -> typing.List[str]:
    r"""Extract a ZIP or TAR.GZ file.

    Args:
        archive: path to ZIP or TAR.GZ file
        destination: folder where the content should be stored.
            Will be created if it doesn't exist
        keep_archive: if ``False`` delete archive file after extraction
        verbose: if ``True`` a progress bar is shown

    Returns:
        member filenames of archive

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
                for member in progress_bar(
                    members,
                    desc=desc,
                    disable=disable,
                ):
                    zf.extract(member, destination)
                member_names = [m.filename for m in members]
        elif archive.endswith('tar.gz'):
            with tarfile.open(archive, 'r') as tf:
                members = tf.getmembers()
                for member in progress_bar(
                    members,
                    desc=desc,
                    disable=disable,
                ):
                    tf.extract(member, destination, numeric_owner=True)
                member_names = [m.name for m in members]
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

    return member_names


def extract_archives(
        archives: typing.Sequence[str],
        destination: str,
        *,
        keep_archive: bool = True,
        verbose: bool = False,
) -> typing.List[str]:
    r"""Extract ZIP or TAR.GZ archives.

    Args:
        archives: paths of ZIP or TAR.GZ files
        destination: folder where the content should be stored.
            Will be created if it doesn't exist
        keep_archive: if ``False`` delete archive files after extraction
        verbose: if ``True`` a progress bar is shown

    Returns:
        combined member filenames of archives

    """
    with progress_bar(
        total=len(archives),
        disable=not verbose,
    ) as pbar:
        member_names = []
        for archive in archives:
            desc = format_display_message(
                f'Extract {os.path.basename(archive)}',
                pbar=True,
            )
            pbar.set_description_str(desc)
            pbar.refresh()
            member_names += extract_archive(
                archive,
                destination,
                keep_archive=keep_archive,
                verbose=False,
            )
            pbar.update()

    return member_names


def file_extension(
        path: typing.Union[str, bytes]
) -> str:
    """File extension.

    Args:
        path: path to file

    Returns:
        extension of file without "."

    Examples:
        >>> path = '/test/file.wav'
        >>> file_extension(path)
        'wav'

    """
    path = safe_path(path)
    return os.path.splitext(path)[-1][1:]


def list_dir_names(
        path: typing.Union[str, bytes],
        *,
        basenames: bool = False,
        recursive: bool = False,
        hidden: bool = True,
) -> typing.List[str]:
    """List of folder names located inside provided path.

    Args:
        path: path to directory
        basenames: if ``True`` return relative path in respect to ``path``
        recursive: if ``True`` includes subdirectories
        hidden: if ``True`` includes directories starting with a dot (``.``)

    Returns:
        list of paths to directories

    Raises:
        NotADirectoryError: if path is not a directory
        FileNotFoundError: if path does not exists

    Examples:
        >>> _ = mkdir('path/a/.b/c')
        >>> list_dir_names(
        ...     'path',
        ...     basenames=True,
        ... )
        ['a']
        >>> list_dir_names(
        ...     'path',
        ...     basenames=True,
        ...     recursive=True,
        ... )
        ['a', 'a/.b', 'a/.b/c']
        >>> list_dir_names(
        ...     'path',
        ...     basenames=True,
        ...     recursive=True,
        ...     hidden=False,
        ... )
        ['a']

    """
    path = safe_path(path)

    def helper(p: str, paths: typing.List[str]):
        ps = [os.path.join(p, x) for x in os.listdir(p)]
        ps = [x for x in ps if os.path.isdir(x)]
        if not hidden:
            ps = [x for x in ps if not os.path.basename(x).startswith('.')]
        paths.extend(ps)
        if len(ps) > 0 and recursive:
            for p in ps:
                helper(p, paths)

    paths = []
    helper(path, paths)
    if basenames:
        paths = [p[len(path) + 1:] for p in paths]

    return sorted(paths)


def list_file_names(
        path: typing.Union[str, bytes],
        *,
        filetype: str = '',
        basenames: bool = False,
        recursive: bool = False,
        hidden: bool = False,
) -> typing.List[str]:
    """List of file names inferred from provided path.

    Args:
        path: path to file, directory or pattern
        filetype: optional consider only this filetype
        basenames: if ``True`` return relative path in respect to ``path``
        recursive: if ``True`` includes subdirectories
        hidden: if ``True`` includes files starting with a dot (``.``)

    Returns:
        list of path(s) to file(s)

    Examples:
        >>> dir_path = mkdir('path')
        >>> _ = touch(os.path.join(dir_path, 'file.wav'))
        >>> _ = touch(os.path.join(dir_path, '.lock'))
        >>> sub_dir_path = mkdir(os.path.join('path', 'sub'))
        >>> _ = touch(os.path.join(sub_dir_path, 'file.ogg'))
        >>> _ = touch(os.path.join(sub_dir_path, '.lock'))
        >>> list_file_names(
        ...     dir_path,
        ...     basenames=True,
        ... )
        ['file.wav']
        >>> list_file_names(
        ...     dir_path,
        ...     basenames=True,
        ...     hidden=True,
        ... )
        ['.lock', 'file.wav']
        >>> list_file_names(
        ...     dir_path,
        ...     basenames=True,
        ...     recursive=True,
        ... )
        ['file.wav', 'sub/file.ogg']
        >>> list_file_names(
        ...     dir_path,
        ...     basenames=True,
        ...     recursive=True,
        ...     hidden=True,
        ... )
        ['.lock', 'file.wav', 'sub/.lock', 'sub/file.ogg']
        >>> list_file_names(
        ...     os.path.join(dir_path, 'f*'),
        ...     basenames=True,
        ...     recursive=True,
        ...     hidden=True,
        ... )
        ['file.wav', 'sub/file.ogg']
        >>> list_file_names(
        ...     os.path.join(dir_path, 'f*'),
        ...     filetype='ogg',
        ...     basenames=True,
        ...     recursive=True,
        ...     hidden=True,
        ... )
        ['sub/file.ogg']

    """
    path = safe_path(path)
    if not os.path.isdir(path):
        pattern = os.path.basename(path)
        path = os.path.dirname(path)
    else:
        pattern = None

    def helper(p: str, paths: typing.List[str]):
        ps = [os.path.join(p, x) for x in os.listdir(p)]
        folders = [x for x in ps if os.path.isdir(x)]
        files = [x for x in ps if os.path.isfile(x)]
        if pattern:
            files = [
                file for file in files
                if fnmatch.fnmatch(os.path.basename(file), f'{pattern}')
            ]
        if filetype:
            files = [
                file for file in files
                if fnmatch.fnmatch(os.path.basename(file), f'*{filetype}')
            ]
        if not hidden:
            files = [
                file for file in files
                if not os.path.basename(file).startswith('.')
            ]
        paths.extend(files)
        if len(folders) > 0 and recursive:
            for p in folders:
                helper(p, paths)

    paths = []
    helper(path, paths)
    if basenames:
        paths = [p[len(path) + 1:] for p in paths]

    return sorted(paths)


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

    Examples:
        >>> p = mkdir('path1/path2/path3')
        >>> os.path.basename(p)
        'path3'

    """
    path = safe_path(path)
    if path:
        os.makedirs(path, mode=mode, exist_ok=True)
    return path


def move_file(
        src_path,
        dst_path,
):
    """Move a file independent of operating system.

    As :func:`os.rename` works differently
    under Unix and Windows
    and :func:`shutil.move` can be slow,
    we use :func:`os.replace`
    to move the file.

    Args:
        scr_path: source file path
        dst_path: destination file path

    Examples:
        >>> path = mkdir('folder')
        >>> src_path = touch(os.path.join(path, 'file1'))
        >>> dst_path = os.path.join(path, 'file2')
        >>> move_file(src_path, dst_path)
        >>> list_file_names(path, basenames=True)
        ['file2']

    """
    os.replace(src_path, dst_path)


def replace_file_extension(
        path: typing.Union[str, bytes],
        new_extension: str,
        *,
        ext: str = None,
) -> str:
    """Replace file extension.

    If ``ext`` is ``None``
    it uses :func:`audeer.file_extension`
    to identify the current extension
    and replaces it with ``new_extension``.

    Args:
        path: path to file
        new_extension: new file extension
            without leading ``.``
        ext: explicit extension to be removed

    Returns:
        path to file with new extension

    Examples:
        >>> path = 'file.txt'
        >>> replace_file_extension(path, 'rst')
        'file.rst'
        >>> replace_file_extension('file.tar.gz', 'zip', ext='tar.gz')
        'file.zip'

    """
    if ext is None:
        ext = file_extension(path)
    elif ext.startswith('.'):
        ext = ext[1:]  # '.mp3' => 'mp3'
    return f'{path[:-len(ext)]}{new_extension}'


def rmdir(
        path: typing.Union[str, bytes],
):
    """Remove directory.

    Remove the directory
    and all its content
    if the directory exists.

    Args:
        path: absolute or relative path of directory to remove

    Raises:
        NotADirectoryError: if path is not a directory

    Examples:
        >>> mkdir('path1/path2/path3')  # doctest: +SKIP
        >>> rmdir('path1/path2')
        >>> list_dir_names('path1')
        []

    """
    path = safe_path(path)
    if os.path.exists(path):
        shutil.rmtree(path)


def touch(
        path: typing.Union[str, bytes]
) -> str:
    """Create an empty file.

    If the file exists already
    it's access and modification times
    are updated.

    Args:
        path: path to file

    Returns:
        expanded path to file

    Examples:
        >>> path = touch('file.txt')
        >>> os.path.basename(path)
        'file.txt'

    """
    path = safe_path(path)
    if os.path.exists(path):
        os.utime(path, None)
    else:
        open(path, 'a').close()
    return path
