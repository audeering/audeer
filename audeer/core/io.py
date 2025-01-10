from __future__ import annotations

from collections.abc import Sequence
import errno
import fnmatch
import hashlib
import inspect
import io
import itertools
import os
import shutil
import sys
import tarfile
import urllib.request
import zipfile

from audeer.core.path import path as safe_path
from audeer.core.tqdm import format_display_message
from audeer.core.tqdm import progress_bar
from audeer.core.utils import to_list


def basename_wo_ext(
    path: str | bytes,
    *,
    ext: str = None,
) -> str:
    """File basename without file extension.

    Args:
        path: file or directory name
        ext: explicit extension to be removed

    Returns:
        basename of directory or file without extension

    Examples:
        >>> path = "/test/file.wav"
        >>> audeer.basename_wo_ext(path)
        'file'

    """
    path = safe_path(path)
    path = os.path.basename(path)
    if ext is not None:
        if not ext.startswith("."):
            ext = "." + ext  # 'mp3' => '.mp3'
        path = path.removesuffix(ext)
    else:
        path = os.path.splitext(path)[0]
    return path


def common_directory(
    dirs: Sequence[str],
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
        .. skip: start if(platform.system() == "Windows")

        >>> paths = [
        ...     "/home/user1/tmp/coverage/test",
        ...     "/home/user1/tmp/covert/operator",
        ...     "/home/user1/tmp/coven/members",
        ... ]
        >>> audeer.common_directory(paths)
        '/home/user1/tmp'

        .. skip: end

    """

    def all_names_equal(name):
        return all(n == name[0] for n in name[1:])

    dirs = [safe_path(path) for path in dirs]
    by_directory_levels = zip(*[p.split(sep) for p in dirs])
    return sep.join(
        x[0]
        for x in itertools.takewhile(
            all_names_equal,
            by_directory_levels,
        )
    )


def create_archive(
    root: str,
    files: str | Sequence[str] | None,
    archive: str,
    *,
    verbose: bool = False,
):
    r"""Create ZIP or TAR archive.

    If a list with ``files`` is provided,
    only those files will be included to the archive.
    In that case the files are added in the given order,
    which may have an influence on the checksum of the archive.

    If ``files`` is set to ``None``,
    all files below ``root`` will be added in sorted order.
    This includes hidden files and files from sub-folders,
    but not empty folders.

    Args:
        root: path to root folder of archive.
            Only files below ``root`` can be included
            and will be stored relative to ``root``
        files: files that will be included in the archive.
            Absolute and relative file paths are possible,
            as long as the files are below ``root``.
            If set to ``None``
            all files below ``root``
            will be added to the archive
        archive: path to archive file.
            The type of the archive
            is determined from its file extension
        verbose: if ``True`` a progress bar is shown

    Raises:
        FileNotFoundError: if ``root`` or a file in ``files`` is not found
        NotADirectoryError: if ``root`` is not a directory
        RuntimeError: if archive does not end with ``zip``,
            ``tar``, ``tar.gz``, ``tar.bz2``, ``tar.xz``
        RuntimeError: if a file in ``files`` is not below ``root``

    Examples:
        >>> file_a = audeer.touch("a.txt")
        >>> folder = os.path.dirname(file_a)
        >>> file_b = audeer.touch(folder, "b.txt")
        >>> archive = audeer.path("archive.zip")
        >>> audeer.create_archive(folder, None, archive)
        >>> audeer.extract_archive(archive, ".")
        ['a.txt', 'b.txt']
        >>> archive = audeer.path("archive.tar.gz")
        >>> audeer.create_archive(folder, ["a.txt"], archive)
        >>> audeer.extract_archive(archive, ".")
        ['a.txt']

    """
    root = safe_path(root)
    archive = safe_path(archive)
    mkdir(os.path.dirname(archive))

    if not os.path.exists(root):
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            root,
        )

    if not os.path.isdir(root):
        raise NotADirectoryError(
            errno.ENOTDIR,
            os.strerror(errno.ENOTDIR),
            root,
        )

    if files is None:
        files = list_file_names(
            root,
            basenames=True,
            recursive=True,
            hidden=True,
        )

    else:
        files_org = to_list(files)
        files = []

        for file in files_org:
            # convert to absolute path
            if not os.path.isabs(file):
                path = safe_path(root, file)
            else:
                path = safe_path(file)

            # file is below root
            if not path.startswith(root):
                raise RuntimeError(
                    f"Only files below "
                    f"'{root}' "
                    f"can be included. "
                    f"This is not the case with "
                    f"'{file}'"
                )

            # file exists
            if not os.path.exists(path):
                raise FileNotFoundError(
                    errno.ENOENT,
                    os.strerror(errno.ENOENT),
                    file,
                )

            # convert to relative path
            files.append(path[len(root) + 1 :])

    # Progress bar arguments
    desc = format_display_message(
        f"Create {os.path.basename(archive)}",
        pbar=True,
    )
    disable = not verbose

    archive_handlers = {
        "zip": lambda path: zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED),
        "tar": lambda path: tarfile.open(path, "w:"),
        "tar.gz": lambda path: tarfile.open(path, "w:gz"),
        "tar.bz2": lambda path: tarfile.open(path, "w:bz2"),
        "tar.xz": lambda path: tarfile.open(path, "w:xz"),
    }

    # Get the archive extension
    extension = next((ext for ext in archive_handlers if archive.endswith(ext)), None)
    if extension is None:
        supported = ", ".join(archive_handlers.keys())
        raise RuntimeError(
            f"Unsupported archive format. Supported formats: {supported}"
        )

    # Create and populate the archive
    with archive_handlers[extension](archive) as archive_file:
        for file in progress_bar(files, desc=desc, disable=disable):
            full_file = safe_path(root, file)
            if extension == "zip":
                archive_file.write(full_file, arcname=file)
            else:
                archive_file.add(full_file, file)


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
        >>> dst = audeer.download_url(
        ...     "https://audeering.github.io/audeer/_static/favicon.png", "."
        ... )
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
        desc=format_display_message(f"Downloading {url}", pbar=True),
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
) -> list[str]:
    r"""Extract ZIP or TAR file.

    Args:
        archive: path to ZIP or TAR file
        destination: folder where the files will be extracted.
            If the folder does not exists,
            it will be created
        keep_archive: if ``False`` delete archive file after extraction
        verbose: if ``True`` a progress bar is shown

    Returns:
        paths of extracted files relative to ``destination``
        in order they were added to the archive

    Raises:
        FileNotFoundError: if ``archive`` is not found
        IsADirectoryError: if ``archive`` is a directory
        NotADirectoryError: if ``destination`` is not a directory
        RuntimeError: if ``archive`` is not a ZIP or TAR file
        RuntimeError: if ``archive`` is malformed

    Examples:
        >>> folder = audeer.path(".")
        >>> file = audeer.touch(folder, "a.txt")
        >>> archive = audeer.path("archive.zip")
        >>> audeer.create_archive(folder, None, archive)
        >>> audeer.extract_archive(archive, ".")
        ['a.txt']
        >>> audeer.extract_archive(archive, "sub")
        ['a.txt']

    """
    archive = safe_path(archive)
    destination = safe_path(destination)

    if not os.path.exists(archive):
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            archive,
        )

    if os.path.isdir(archive):
        raise IsADirectoryError(
            errno.EISDIR,
            os.strerror(errno.EISDIR),
            archive,
        )

    if os.path.exists(destination):
        destination_created = False
    else:
        mkdir(destination)
        destination_created = True

    if not os.path.isdir(destination):
        raise NotADirectoryError(
            errno.ENOTDIR,
            os.strerror(errno.ENOTDIR),
            destination,
        )

    # Progress bar arguments
    desc = format_display_message(
        f"Extract {os.path.basename(archive)}",
        pbar=True,
    )
    disable = not verbose

    def extract_zip(archive: str) -> list:
        with zipfile.ZipFile(archive, "r") as zf:
            members = zf.infolist()
            for member in progress_bar(members, desc=desc, disable=disable):
                zf.extract(member, destination)
            return [m.filename for m in members]

    def extract_tar(archive: str) -> list:
        with tarfile.open(archive, "r") as tf:
            members = tf.getmembers()
            for member in progress_bar(members, desc=desc, disable=disable):
                # In Python 3.12 the `filter` argument was introduced,
                # and it will be set automatically in Python 3.14,
                # see
                # https://docs.python.org/3.12/library/tarfile.html#tarfile-extraction-filter
                # noqa: E501
                kwargs = {"numeric_owner": True}
                if sys.version_info >= (3, 12):  # pragma: no cover
                    kwargs = kwargs | {"filter": "tar"}
                tf.extract(member, destination, **kwargs)
            return [m.name for m in members]

    try:
        if archive.endswith("zip"):
            files = extract_zip(archive)
        elif tarfile.is_tarfile(archive):
            files = extract_tar(archive)
        else:
            raise RuntimeError(f"You can only extract ZIP and TAR files, not {archive}")
    except (EOFError, zipfile.BadZipFile, tarfile.ReadError):
        raise RuntimeError(f"Broken archive: {archive}")
    except (KeyboardInterrupt, Exception):  # pragma: no cover
        # Clean up broken extraction files
        if destination_created:
            if os.path.exists(destination):
                shutil.rmtree(destination)
        raise

    if not keep_archive:
        os.remove(archive)

    if os.name == "nt":  # pragma: no cover
        # replace '/' with '\' on Windows
        files = [file.replace("/", os.path.sep) for file in files]

    return files


def extract_archives(
    archives: Sequence[str],
    destination: str,
    *,
    keep_archive: bool = True,
    verbose: bool = False,
) -> list[str]:
    r"""Extract multiple ZIP or TAR archives at once.

    Args:
        archives: paths of ZIP or TAR files
        destination: folder where the files will be extracted.
            If the folder does not exists,
            it will be created
        keep_archive: if ``False`` delete archive files after extraction
        verbose: if ``True`` a progress bar is shown

    Returns:
        paths of extracted files relative to ``destination``
        in order they were added to the archives

    Raises:
        FileNotFoundError: if an archive is not found
        IsADirectoryError: if an archive is a directory
        NotADirectoryError: if ``destination`` is not a directory
        RuntimeError: if an archive is not a ZIP or TAR file
        RuntimeError: if an archive file is malformed

    Examples:
        >>> folder = audeer.path(".")
        >>> _ = audeer.touch(folder, "a.txt")
        >>> _ = audeer.touch(folder, "b.txt")
        >>> archive_a = audeer.path("archive.zip")
        >>> archive_b = audeer.path("archive.tar.gz")
        >>> audeer.create_archive(folder, ["a.txt"], archive_a)
        >>> audeer.create_archive(folder, ["b.txt"], archive_b)
        >>> audeer.extract_archives([archive_a, archive_b], ".")
        ['a.txt', 'b.txt']

    """
    with progress_bar(
        total=len(archives),
        disable=not verbose,
    ) as pbar:
        member_names = []
        for archive in archives:
            desc = format_display_message(
                f"Extract {os.path.basename(archive)}",
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
    path: str | bytes,
) -> str:
    """File extension.

    Args:
        path: path to file

    Returns:
        extension of file without "."

    Examples:
        >>> path = "/test/file.wav"
        >>> audeer.file_extension(path)
        'wav'

    """
    path = safe_path(path)
    return os.path.splitext(path)[-1][1:]


def list_dir_names(
    path: str | bytes,
    *,
    basenames: bool = False,
    recursive: bool = False,
    hidden: bool = True,
) -> list[str]:
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
        .. skip: start if(platform.system() == "Windows")

        >>> path = audeer.path("path")
        >>> _ = mkdir(path, "a", ".b", "c")
        >>> audeer.list_dir_names(path, basenames=True)
        ['a']
        >>> audeer.list_dir_names(path, basenames=True, recursive=True)
        ['a', 'a/.b', 'a/.b/c']
        >>> audeer.list_dir_names(path, basenames=True, recursive=True, hidden=False)
        ['a']

        .. skip: end

    """
    path = safe_path(path)

    def helper(p: str, paths: list[str]):
        ps = [os.path.join(p, x) for x in os.listdir(p)]
        ps = [x for x in ps if os.path.isdir(x)]
        if not hidden:
            ps = [x for x in ps if not os.path.basename(x).startswith(".")]
        paths.extend(ps)
        if len(ps) > 0 and recursive:
            for p in ps:
                helper(p, paths)

    paths = []
    helper(path, paths)
    if basenames:
        paths = [p[len(path) + 1 :] for p in paths]

    return sorted(paths)


def list_file_names(
    path: str | bytes,
    *,
    filetype: str = "",
    basenames: bool = False,
    recursive: bool = False,
    hidden: bool = False,
) -> list[str]:
    """List of file names inferred from provided path.

    Args:
        path: path to directory,
            or path to directory plus file matching pattern,
            e.g. ``'dir/file.txt'``.
            If ``recursive`` is ``True``
            returns all files named ``file.txt``
            from all sub-folders.
            Besides the filename ``*``, ``?``, ``[seq]``,
            and ``[!seq]`` can be used as pattern,
            compare :mod:`fnmatch`
        filetype: optional consider only this filetype
        basenames: if ``True`` return relative path in respect to ``path``
        recursive: if ``True`` includes subdirectories
        hidden: if ``True`` includes files starting with a dot (``.``)

    Returns:
        alphabetically sorted list of path(s) to file(s)

    Raises:
        NotADirectoryError: if ``path`` is a directory or file
            that does not exist,
            or ``path`` is a pattern
            and ``os.dirname(path)`` does not exist

    Examples:
        .. skip: start if(platform.system() == "Windows")

        >>> dir_path = audeer.mkdir("path")
        >>> _ = audeer.touch(dir_path, "file.wav")
        >>> _ = audeer.touch(dir_path, "album.wav")
        >>> _ = audeer.touch(dir_path, ".lock")
        >>> sub_dir_path = audeer.mkdir(dir_path, "sub")
        >>> _ = audeer.touch(sub_dir_path, "file.ogg")
        >>> _ = audeer.touch(sub_dir_path, ".lock")
        >>> audeer.list_file_names(dir_path, basenames=True)
        ['album.wav', 'file.wav']
        >>> audeer.list_file_names(dir_path, basenames=True, hidden=True)
        ['.lock', 'album.wav', 'file.wav']
        >>> audeer.list_file_names(dir_path, basenames=True, recursive=True)
        ['album.wav', 'file.wav', 'sub/file.ogg']
        >>> audeer.list_file_names(dir_path, basenames=True, recursive=True, hidden=True)
        ['.lock', 'album.wav', 'file.wav', 'sub/.lock', 'sub/file.ogg']
        >>> audeer.list_file_names(
        ...     os.path.join(dir_path, "f*"), basenames=True, recursive=True
        ... )
        ['file.wav', 'sub/file.ogg']
        >>> audeer.list_file_names(
        ...     os.path.join(dir_path, "[fa]*"), basenames=True, recursive=True
        ... )
        ['album.wav', 'file.wav', 'sub/file.ogg']
        >>> audeer.list_file_names(
        ...     os.path.join(dir_path, "[!f]*"), basenames=True, recursive=True
        ... )
        ['album.wav']
        >>> audeer.list_file_names(dir_path, filetype="ogg", basenames=True, recursive=True)
        ['sub/file.ogg']

        .. skip: end

    """  # noqa: E501
    path = safe_path(path)

    if os.path.isdir(path):
        pattern = None
        folder = path

    elif os.path.exists(path) and not recursive:
        if not hidden and os.path.basename(path).startswith("."):
            return []
        if basenames:
            path = os.path.basename(path)
        return [path]

    else:
        pattern = os.path.basename(path)
        folder = os.path.dirname(path)

        if not os.path.isdir(folder):
            raise NotADirectoryError(folder)

    def helper(p: str, paths: list[str]):
        ps = [os.path.join(p, x) for x in os.listdir(p)]
        folders = [x for x in ps if os.path.isdir(x)]
        files = [x for x in ps if os.path.isfile(x)]
        if pattern:
            files = [
                file
                for file in files
                if fnmatch.fnmatch(os.path.basename(file), f"{pattern}")
            ]
        if filetype:
            files = [
                file
                for file in files
                if fnmatch.fnmatch(os.path.basename(file), f"*{filetype}")
            ]
        paths.extend(files)
        if len(folders) > 0 and recursive:
            for p in folders:
                helper(p, paths)

    paths = []
    helper(folder, paths)

    def is_pattern(pattern):
        return "*" in pattern or "?" in pattern or ("[" in pattern and "]" in pattern)

    # if we have no match,
    # raise an error unless
    # 1. path is a folder (i.e. pattern is None)
    # 2. or we have a valid pattern
    if len(paths) == 0 and pattern is not None and not is_pattern(pattern):
        raise NotADirectoryError(path)

    if not hidden:
        paths = [p for p in paths if not os.path.basename(p).startswith(".")]

    if basenames:
        paths = [p[len(folder) + 1 :] for p in paths]

    return sorted(paths)


def mkdir(
    path: str | bytes,
    *paths: Sequence[str | bytes],
    mode: int = 0o777,
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
        *paths: additional arguments
            to be joined with ``path``
            by :func:`os.path.join`
        mode: set permissions of created folders

    Returns:
        absolute path to the created directory

    Examples:
        >>> path = audeer.mkdir("path1", "path2", "path3")
        >>> os.path.basename(path)
        'path3'

    """
    path = safe_path(path, *paths)
    if path:
        os.makedirs(path, mode=mode, exist_ok=True)
    return path


def md5(
    path: str,
    chunk_size: int = 8192,
) -> str:
    r"""Calculate MD5 checksum of file or folder.

    If ``path`` is a folder,
    the checksum is calculated
    from all files in the folder
    (including hidden files).
    The checksum also encodes
    the (relative) file names,
    so that renaming files
    results in a different checksum.
    However,
    the calculation is independent of
    file separator of the operation systems.
    Empty folders are ignored.

    Args:
        path: path to file or folder
        chunk_size: chunk size in number of bytes

    Returns:
        checksum

    Raises:
        FileNotFoundError: if ``path`` does not exist

    Examples:
        >>> path = audeer.touch("file.txt")
        >>> audeer.md5(path)
        'd41d8cd98f00b204e9800998ecf8427e'
        >>> audeer.md5(os.path.dirname(path))
        '3d8e577bddb17db339eae0b3d9bcf180'

    """
    path = safe_path(path)
    hasher = hashlib.md5()

    if not os.path.exists(path):
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            path,
        )

    if not os.path.isdir(path):
        with open(path, "rb") as fp:
            for chunk in md5_read_chunk(fp, chunk_size):
                hasher.update(chunk)

    else:
        files = list_file_names(
            path,
            recursive=True,
            hidden=True,
            basenames=True,
        )

        for file in files:
            # encode file name that renaming of files
            # produces different checksum
            hasher.update(file.replace(os.path.sep, "/").encode())
            with open(safe_path(path, file), "rb") as fp:
                for chunk in md5_read_chunk(fp, chunk_size):
                    hasher.update(chunk)

    return hasher.hexdigest()


def md5_read_chunk(
    fp: io.IOBase,
    chunk_size: int = 8192,
):
    while True:
        data = fp.read(chunk_size)
        if not data:
            break
        yield data


def move(
    src_path,
    dst_path,
):
    """Move a file or folder independent of operating system.

    As :func:`os.rename` works differently
    under Unix and Windows
    and :func:`shutil.move` can be slow,
    we use :func:`os.replace`
    to move the file/folder.

    Args:
        src_path: source file/folder path
        dst_path: destination file/folder path

    Raises:
        OSError: if ``src_path`` is a file
            and ``dst_path`` is an existing folder
        OSError: if ``src_path`` is a folder
            and ``dst_path`` is an existing file
            (not raised under Windows)
        OSError: if ``dst_path`` is a non-empty folder,
            different from ``src_path``,
            and ``src_path`` is also a folder
        OSError: if ``dst_path`` is an empty folder,
            different from ``src_path``
            and ``src_path`` is also a folder
            (raised only under Windows)

    Examples:
        >>> path = audeer.mkdir("folder")
        >>> src_path = audeer.touch(path, "file1")
        >>> dst_path = os.path.join(path, "file2")
        >>> audeer.move(src_path, dst_path)
        >>> audeer.list_file_names(path, basenames=True)
        ['file2']

    """
    os.replace(src_path, dst_path)


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

    Warning:
        :func:`audeer.move_file` is deprecated,
        please use :func:`audeer.move` instead.

    Args:
        src_path: source file path
        dst_path: destination file path

    Examples:
        >>> path = audeer.mkdir("folder")
        >>> src_path = audeer.touch(path, "file1")
        >>> dst_path = os.path.join(path, "file2")
        >>> audeer.move_file(src_path, dst_path)
        >>> audeer.list_file_names(path, basenames=True)
        ['file2']

    """
    move(src_path, dst_path)


def replace_file_extension(
    path: str | bytes,
    new_extension: str,
    *,
    ext: str = None,
) -> str:
    """Replace file extension.

    If ``ext`` is ``None``
    it uses :func:`audeer.file_extension`
    to identify the current extension
    and replaces it with ``new_extension``.

    If ``ext`` is not ``None``
    but ``path`` ends on a different extension,
    the original path is returned.

    Args:
        path: path to file
        new_extension: new file extension
        ext: explicit extension to be removed

    Returns:
        path to file with a possibly new extension

    Examples:
        >>> audeer.replace_file_extension("file.txt", "rst")
        'file.rst'
        >>> audeer.replace_file_extension("file", "rst")
        'file.rst'
        >>> audeer.replace_file_extension("file.txt", "")
        'file'
        >>> audeer.replace_file_extension("file.tar.gz", "zip", ext="tar.gz")
        'file.zip'
        >>> audeer.replace_file_extension("file.zip", "rst", ext="txt")
        'file.zip'

    """
    if ext is None:
        ext = file_extension(path)

    # '.mp3' => 'mp3'
    ext = ext.removeprefix(".")
    new_extension = new_extension.removeprefix(".")

    if ext and not path.endswith(f".{ext}"):
        return path

    if not path:
        return path

    if not ext and not new_extension:
        pass
    elif not ext:
        path = f"{path}.{new_extension}"
    elif not new_extension:
        path = path[: -len(ext) - 1]
    else:
        path = f"{path[:-len(ext)]}{new_extension}"

    return path


def rmdir(
    path: str | bytes,
    *paths: Sequence[str | bytes],
    follow_symlink: bool = True,
):
    """Remove directory.

    Remove the directory
    and all its content
    if the directory exists.

    Args:
        path: absolute or relative path of directory to remove
        *paths: additional arguments
            to be joined with ``path``
            by :func:`os.path.join`
        follow_symlink: if ``True``
            and path is a symbolic link,
            the link and the folder it points to
            will be removed

    Raises:
        NotADirectoryError: if path is not a directory
        OSError: if ``follow_symlink`` is ``False``
            and ``path`` is a symbolic link

    Examples:
        >>> path = audeer.mkdir("path1")
        >>> _ = audeer.mkdir(path, "path2", "path3")
        >>> audeer.list_dir_names(path, basenames=True)
        ['path2']
        >>> audeer.rmdir(path, "path2")
        >>> audeer.list_dir_names(path)
        []

    """
    path = safe_path(path, *paths, follow_symlink=follow_symlink)
    if os.path.exists(path):
        shutil.rmtree(path)


def script_dir() -> str:
    r"""Folder in which caller of this function is located.

    When called from a file,
    it returns the directory,
    in which the file is stored.
    When called in an interactive session,
    it returns the current working directory
    of the interactive session.

    Returns:
        current directory of caller

    Examples:
        .. skip: next if(platform.system() == "Windows")

        >>> audeer.script_dir()  # location of this file
        '...audeer/core'

    """
    # Returning the script dir is usually done with
    # `os.path.dirname(os.path.realpath(__file__))`,
    # see https://stackoverflow.com/a/5137509.
    # We cannot use `__file__` here,
    # as this would always point to this file (`io.py`).
    # Instead we find the script
    # of the caller of `audeer.script_dir()`,
    # see https://stackoverflow.com/a/37792573
    caller = inspect.stack()[1].filename
    return os.path.dirname(os.path.realpath(caller))


def touch(
    path: str | bytes,
    *paths: Sequence[str | bytes],
) -> str:
    """Create an empty file.

    If the file exists already
    it's access and modification times
    are updated.

    Args:
        path: path to file
        *paths: additional arguments
            to be joined with ``path``
            by :func:`os.path.join`

    Returns:
        expanded path to file

    Examples:
        >>> path = audeer.touch("file.txt")
        >>> os.path.basename(path)
        'file.txt'

    """
    path = safe_path(path, *paths)
    if os.path.exists(path):
        os.utime(path, None)
    else:
        open(path, "a").close()
    return path
