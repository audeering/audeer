import os
import platform
import stat
import sys
import time

import pytest

import audeer


@pytest.fixture(scope="function", autouse=False)
def tree(tmpdir, request):
    r"""Create file tree."""
    files = request.param
    paths = []

    for path in files:
        if os.name == "nt":
            path = path.replace("/", os.path.sep)
        if path.endswith(os.path.sep):
            path = audeer.path(tmpdir, path)
            path = audeer.mkdir(path)
            path = path + os.path.sep
            paths.append(path)
        else:
            path = audeer.path(tmpdir, path)
            audeer.mkdir(os.path.dirname(path))
            path = audeer.touch(path)
            paths.append(path)

    yield paths


@pytest.mark.parametrize(
    "tree, root, files, archive_create, archive_extract, destination, " "expected",
    [
        (  # empty
            [],
            ".",
            [],
            "archive.zip",
            "archive.zip",
            ".",
            [],
        ),
        (
            [],
            ".",
            None,
            "archive.zip",
            "archive.zip",
            ".",
            [],
        ),
        (  # single file
            ["file.txt"],
            ".",
            "file.txt",
            "archive.zip",
            "archive.zip",
            ".",
            ["file.txt"],
        ),
        (  # archive folder does not exist
            ["file.txt"],
            ".",
            "file.txt",
            "sub/archive.zip",
            "sub/archive.zip",
            ".",
            ["file.txt"],
        ),
        (  # file in sub folder
            ["file.txt", "sub/a/b/file.txt"],
            ".",
            ["sub/a/b/file.txt", "file.txt"],
            "archive.zip",
            "archive.zip",
            ".",
            ["sub/a/b/file.txt", "file.txt"],
        ),
        (
            ["file.txt", "sub/a/b/file.txt"],
            ".",
            ["sub/a/b/file.txt"],
            "archive.zip",
            "archive.zip",
            ".",
            ["sub/a/b/file.txt"],
        ),
        (
            ["file.txt", "sub/a/b/file.txt"],
            ".",
            ["file.txt"],
            "archive.zip",
            "archive.zip",
            ".",
            ["file.txt"],
        ),
        (  # include all files
            ["file.txt", "sub/a/b/file.txt", ".hidden"],
            ".",
            None,
            "archive.zip",
            "archive.zip",
            ".",
            [".hidden", "file.txt", "sub/a/b/file.txt"],
        ),
        (  # exclude empty folder
            ["file.txt", "sub/a/b/file.txt", ".hidden", "empty/"],
            ".",
            None,
            "archive.zip",
            "archive.zip",
            ".",
            [".hidden", "file.txt", "sub/a/b/file.txt"],
        ),
        (  # tar
            ["file.txt", "sub/a/b/file.txt"],
            ".",
            ["sub/a/b/file.txt", "file.txt"],
            "archive.tar",
            "archive.tar",
            ".",
            ["sub/a/b/file.txt", "file.txt"],
        ),
        (  # tar.gz
            ["file.txt", "sub/a/b/file.txt"],
            ".",
            ["sub/a/b/file.txt", "file.txt"],
            "archive.tar.gz",
            "archive.tar.gz",
            ".",
            ["sub/a/b/file.txt", "file.txt"],
        ),
        (  # tar.bz2
            ["file.txt", "sub/a/b/file.txt"],
            ".",
            ["sub/a/b/file.txt", "file.txt"],
            "archive.tar.bz2",
            "archive.tar.bz2",
            ".",
            ["sub/a/b/file.txt", "file.txt"],
        ),
        (  # tar.xz
            ["file.txt", "sub/a/b/file.txt"],
            ".",
            ["sub/a/b/file.txt", "file.txt"],
            "archive.tar.xz",
            "archive.tar.xz",
            ".",
            ["sub/a/b/file.txt", "file.txt"],
        ),
        (  # root is sub folder
            ["sub/file.txt"],
            "./sub",
            ["file.txt"],
            "archive.zip",
            "archive.zip",
            ".",
            ["file.txt"],
        ),
        (
            ["sub/file.txt"],
            "./sub",
            None,
            "archive.zip",
            "archive.zip",
            ".",
            ["file.txt"],
        ),
        (  # destitation is sub folder
            ["file.txt"],
            ".",
            ["file.txt"],
            "archive.zip",
            "archive.zip",
            "./sub",
            ["file.txt"],
        ),
        (  # relative path with ../
            ["sub/file.txt"],
            "./sub",
            ["../sub/file.txt"],
            "archive.zip",
            "archive.zip",
            ".",
            ["file.txt"],
        ),
        pytest.param(  # root does not exit
            [],
            "./sub",
            None,
            "archive.zip",
            "archive.zip",
            ".",
            None,
            marks=pytest.mark.xfail(raises=FileNotFoundError),
        ),
        pytest.param(  # root is not a directory
            ["file.txt"],
            "file.txt",
            None,
            "archive.zip",
            "archive.zip",
            ".",
            None,
            marks=pytest.mark.xfail(raises=NotADirectoryError),
        ),
        pytest.param(  # destination is not a directory
            ["file.txt"],
            ".",
            [],
            "archive.zip",
            "archive.zip",
            "file.txt",
            [],
            marks=pytest.mark.xfail(raises=NotADirectoryError),
        ),
        pytest.param(  # archive to be extracted does not exit
            [],
            ".",
            [],
            "archive.zip",
            "bad.zip",
            ".",
            None,
            marks=pytest.mark.xfail(raises=FileNotFoundError),
        ),
        pytest.param(  # archive to be extracted is a directory
            ["sub/"],
            ".",
            [],
            "archive.zip",
            "sub",
            ".",
            None,
            marks=pytest.mark.xfail(raises=IsADirectoryError),
        ),
        pytest.param(  # file does not exit
            [],
            ".",
            ["file.txt"],
            "archive.zip",
            "archive.zip",
            ".",
            None,
            marks=pytest.mark.xfail(raises=FileNotFoundError),
        ),
        pytest.param(  # file not below root
            ["file.txt", "sub/"],
            "./sub",
            ["../file.txt"],
            "archive.zip",
            "archive.zip",
            ".",
            None,
            marks=pytest.mark.xfail(raises=RuntimeError),
        ),
        pytest.param(  # archive type not supported
            [],
            ".",
            [],
            "archive.bad",
            "archive.zip",
            ".",
            None,
            marks=pytest.mark.xfail(raises=RuntimeError),
        ),
        pytest.param(
            ["archive.bad"],
            ".",
            [],
            "archive.zip",
            "archive.bad",
            ".",
            None,
            marks=pytest.mark.xfail(raises=RuntimeError),
        ),
        pytest.param(  # invalid .rar format
            ["file.txt", "sub/a/b/file.txt"],
            ".",
            ["sub/a/b/file.txt", "file.txt"],
            "archive.rar",
            "archive.rar",
            ".",
            None,
            marks=pytest.mark.xfail(raises=RuntimeError),
        ),
        pytest.param(  # invalid .7z format
            ["file.txt", "sub/a/b/file.txt"],
            ".",
            ["sub/a/b/file.txt", "file.txt"],
            "archive.7z",
            "archive.7z",
            ".",
            None,
            marks=pytest.mark.xfail(raises=RuntimeError),
        ),
        pytest.param(  # broken archive
            ["archive.zip"],
            ".",
            [],
            "archive.tar.gz",
            "archive.zip",
            ".",
            None,
            marks=pytest.mark.xfail(raises=RuntimeError),
        ),
    ],
    indirect=["tree"],
)
def test_archives(
    tmpdir, tree, root, files, archive_create, archive_extract, destination, expected
):
    root = audeer.path(tmpdir, root)
    destination = audeer.path(tmpdir, destination)
    archive_create = audeer.path(tmpdir, archive_create)
    archive_extract = audeer.path(tmpdir, archive_extract)

    if os.name == "nt":
        if expected is not None:
            expected = [file.replace("/", os.path.sep) for file in expected]
        if isinstance(files, str):
            files = files.replace("/", os.path.sep)
        elif files is not None:
            files = [file.replace("/", os.path.sep) for file in files]

    # relative path

    audeer.create_archive(
        root,
        files,
        archive_create,
    )
    result = audeer.extract_archive(
        archive_extract,
        root,
        keep_archive=True,
    )
    assert result == expected
    for file in result:
        assert os.path.exists(audeer.path(root, file))
    assert os.path.exists(archive_extract)

    # list of archives

    result = audeer.extract_archives(
        [archive_extract, archive_extract],
        destination,
        keep_archive=True,
    )
    assert result == expected + expected
    for file in result:
        assert os.path.exists(audeer.path(root, file))
    assert os.path.exists(archive_extract)

    # absolute path

    if files is not None:
        if isinstance(files, str):
            files = audeer.path(root, files)
        else:
            files = [audeer.path(root, file) for file in files]
        audeer.create_archive(
            root,
            files,
            archive_create,
        )
        result = audeer.extract_archive(
            archive_extract,
            destination,
            keep_archive=True,
        )
        assert result == expected
        for file in result:
            assert os.path.exists(audeer.path(root, file))
        assert os.path.exists(archive_extract)

    # delete archive

    audeer.extract_archive(
        archive_extract,
        destination,
        keep_archive=False,
    )
    assert not os.path.exists(archive_extract)


@pytest.mark.parametrize(
    "path,ext,basename",
    [
        ("~/.bashrc", None, ".bashrc"),
        ("file.tar.gz", None, "file.tar"),
        ("/a/c.d/g", None, "g"),
        (b"/a/c.d/g", None, "g"),
        ("/a/c.d/g.exe", "exe", "g"),
        ("../.././README.md", ".md", "README"),
        ("folder/file.txt", None, "file"),
        ("folder/file.txt", "txt", "file"),
        (b"folder/file.txt", "txt", "file"),
    ],
)
def test_basename_wo_ext(path, ext, basename):
    b = audeer.basename_wo_ext(path, ext=ext)
    assert b == basename
    assert isinstance(b, str)


@pytest.mark.parametrize(
    "dirs,expected",
    [
        ([], ""),
        (
            [
                "/home/user/tmp/coverage/test",
                "/home/user/tmp/covert/operator",
                "/home/user/tmp/coven/members",
            ],
            "/home/user/tmp",
        ),
        (
            [
                "/home/user/tmp/coverage/test",
                "/home/user/tmp/covert/operator",
                "/home/user/tmp",
            ],
            "/home/user/tmp",
        ),
        (
            [
                "~/tmp/coverage/test",
                "~/tmp/covert/operator",
                "~/tmp/coven/members",
            ],
            f'{os.path.expanduser("~")}/tmp',
        ),
        (
            [
                "/etc/tmp/coverage/test",
                "/home/user/tmp/covert/operator",
                "/home/user/tmp/coven/members",
            ],
            "",
        ),
        (
            [
                "/home/user/tmp",
                "/home/user/tmp",
            ],
            "/home/user/tmp",
        ),
        (
            [
                "/home1/user/tmp",
                "/home2/user/tmp",
            ],
            "",
        ),
    ],
)
def test_common_directory(dirs, expected):
    common = audeer.common_directory(dirs)
    # Change paths always to Linux syntax
    _, common = os.path.splitdrive(common)
    _, expected = os.path.splitdrive(expected)
    common = common.replace("\\", "/")
    expected = expected.replace("\\", "/")
    # On MacOS we get a '/System/Volumes/Data' in front
    common = common.replace("/System/Volumes/Data", "")
    assert common == expected


def test_download_url(tmpdir):
    url = "https://audeering.github.io/audeer/_static/favicon.png"
    audeer.download_url(url, tmpdir)
    audeer.download_url(url, tmpdir)
    dst = audeer.download_url(url, tmpdir, force_download=True)
    assert dst == os.path.join(tmpdir, os.path.basename(url))


@pytest.mark.parametrize(
    "path,extension",
    [
        ("", ""),
        ("~/.bashrc", ""),
        ("file.tar.gz", "gz"),
        ("/a/c.d/g", ""),
        ("/a/c.d/g.exe", "exe"),
        ("../.././README.md", "md"),
        (b"../.././README.md", "md"),
        ("folder/file.txt", "txt"),
        (b"folder/file.txt", "txt"),
        ("test.WAV", "WAV"),
        ("test.WaV", "WaV"),
    ],
)
def test_file_extension(path, extension):
    ext = audeer.file_extension(path)
    assert ext == extension
    assert isinstance(ext, str)


@pytest.mark.parametrize(
    "dir_list,expected,recursive,hidden",
    [
        ([], [], False, False),
        ([], [], True, False),
        (["a", "b", "c"], ["a", "b", "c"], False, False),
        (["a", "b", "c"], ["a", "b", "c"], True, False),
        (["a"], ["a"], False, False),
        (["a"], ["a"], True, False),
        (
            ["a", os.path.join("a", "b"), os.path.join("a", "b", "c")],
            ["a", os.path.join("a", "b"), os.path.join("a", "b", "c")],
            True,
            False,
        ),
        # hidden
        (["a", ".b"], ["a"], True, False),
        (["a", ".b"], [".b", "a"], True, True),
        (
            ["a", ".b", os.path.join("a", ".b"), os.path.join("a", ".b", "c")],
            ["a"],
            True,
            False,
        ),
        (
            ["a", ".b", os.path.join("a", ".b"), os.path.join("a", ".b", "c")],
            [".b", "a", os.path.join("a", ".b"), os.path.join("a", ".b", "c")],
            True,
            True,
        ),
    ],
)
def test_list_dir_names(tmpdir, dir_list, expected, recursive, hidden):
    dir_tmp = tmpdir.mkdir("folder")
    directories = []
    for directory in dir_list:
        directory = os.path.join(str(dir_tmp), directory)
        directories.append(audeer.mkdir(directory))

    for directory in directories:
        assert os.path.isdir(directory)

    path = os.path.join(str(dir_tmp), ".")
    dirs = audeer.list_dir_names(
        path,
        basenames=False,
        recursive=recursive,
        hidden=hidden,
    )
    assert dirs == [audeer.path(dir_tmp, d) for d in expected]
    assert isinstance(dirs, list)

    # test basenames
    dirs = audeer.list_dir_names(
        path,
        basenames=True,
        recursive=recursive,
        hidden=hidden,
    )
    assert dirs == expected


def test_list_dir_names_errors(tmpdir):
    with pytest.raises(NotADirectoryError):
        file = audeer.touch(tmpdir, "file.txt")
        audeer.list_dir_names(file)
    with pytest.raises(FileNotFoundError):
        audeer.list_dir_names("not-existent")


@pytest.mark.parametrize(
    "files,path,filetype,expected,recursive,hidden",
    [
        # empty
        ([], ".", "", [], False, False),
        ([], ".", "", [], True, False),
        ([], ".", "wav", [], False, False),
        ([], ".", "wav", [], True, False),
        # file
        (
            ["file.txt"],
            "file.txt",
            "",
            ["file.txt"],
            False,
            False,
        ),
        pytest.param(
            [os.path.join("sub", "file.txt")],
            "file.txt",
            "",
            [],
            False,
            False,
            marks=pytest.mark.xfail(raises=NotADirectoryError),
        ),
        (
            [os.path.join("sub", "file.txt")],
            "file.txt",
            "",
            [os.path.join("sub", "file.txt")],
            True,
            False,
        ),
        pytest.param(
            [],
            "file",
            "",
            None,
            False,
            False,
            marks=pytest.mark.xfail(raises=NotADirectoryError),
        ),
        (
            [
                "t1.wav",
                "t2.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "t2.wav"),
            ],
            "t1.wav",
            "",
            [os.path.join("sub", "t1.wav"), "t1.wav"],
            True,
            False,
        ),
        # folder
        (
            ["t3.ogg", "t2.wav", "t1.wav"],
            ".",
            "",
            ["t1.wav", "t2.wav", "t3.ogg"],
            False,
            False,
        ),
        (
            [
                "t3.ogg",
                "t2.wav",
                "t1.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "t1.ogg"),
            ],
            ".",
            "",
            ["t1.wav", "t2.wav", "t3.ogg"],
            False,
            False,
        ),
        (
            [
                "t3.ogg",
                "t2.wav",
                "t1.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "sub", "t1.ogg"),
            ],
            ".",
            "",
            [
                os.path.join("sub", "sub", "t1.ogg"),
                os.path.join("sub", "t1.wav"),
                "t1.wav",
                "t2.wav",
                "t3.ogg",
            ],
            True,
            False,
        ),
        pytest.param(
            [],
            "does-not-exist",
            "",
            None,
            False,
            False,
            marks=pytest.mark.xfail(raises=NotADirectoryError),
        ),
        pytest.param(
            [],
            os.path.join("does", "not", "exist"),
            "",
            None,
            False,
            False,
            marks=pytest.mark.xfail(raises=NotADirectoryError),
        ),
        # filetype
        (
            [
                "t3.ogg",
                "t2.wav",
                "t1.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "sub", "t1.ogg"),
            ],
            ".",
            "ogg",
            ["t3.ogg"],
            False,
            False,
        ),
        (
            [
                "t3.ogg",
                "t2.wav",
                "t1.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "sub", "t1.ogg"),
            ],
            ".",
            "ogg",
            [
                os.path.join("sub", "sub", "t1.ogg"),
                "t3.ogg",
            ],
            True,
            False,
        ),
        (
            [
                "t1.wav",
                os.path.join("sub", "t1.wav"),
            ],
            "t1.wav",
            "",
            ["t1.wav"],
            False,
            False,
        ),
        # pattern
        (
            [
                "t1.wav",
                "t2.ogg",
                "s3.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "t2.ogg"),
                os.path.join("sub", "s3.wav"),
            ],
            "t*",
            "",
            [
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "t2.ogg"),
                "t1.wav",
                "t2.ogg",
            ],
            True,
            False,
        ),
        (
            [
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "t2.ogg"),
                os.path.join("sub", "s3.wav"),
            ],
            "t*",
            "",
            [
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "t2.ogg"),
            ],
            True,
            False,
        ),
        (
            [
                "t1.wav",
                "t2.ogg",
                "s3.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "t2.ogg"),
                os.path.join("sub", "s3.wav"),
            ],
            "x*",
            "",
            [],
            True,
            False,
        ),
        (
            [
                "t1.wav",
                "t2.wav",
                "s1.wav",
                "s2.wav",
            ],
            "t?.wav",
            "",
            ["t1.wav", "t2.wav"],
            False,
            False,
        ),
        (
            [
                "t1.wav",
                "t2.wav",
                "s1.wav",
                "s2.wav",
            ],
            "[ts]1.wav",
            "",
            ["s1.wav", "t1.wav"],
            False,
            False,
        ),
        (
            [
                "t1.wav",
                "t2.wav",
                "s1.wav",
                "s.wav",
            ],
            "[ts]?.wav",
            "",
            ["s1.wav", "t1.wav", "t2.wav"],
            False,
            False,
        ),
        (
            [
                "t1.wav",
                "t2.wav",
                "s1.wav",
                "s.wav",
                "x.wav",
            ],
            "[ts]*.wav",
            "",
            ["s.wav", "s1.wav", "t1.wav", "t2.wav"],
            False,
            False,
        ),
        (
            [],
            "file*",
            "",
            [],
            False,
            False,
        ),
        (
            [],
            "?ile",
            "",
            [],
            False,
            False,
        ),
        pytest.param(
            [],
            os.path.join("does", "not", "exist", "file*"),
            "",
            None,
            False,
            False,
            marks=pytest.mark.xfail(raises=NotADirectoryError),
        ),
        pytest.param(
            [],
            os.path.join("not!a[pattern"),
            "",
            None,
            False,
            False,
            marks=pytest.mark.xfail(raises=NotADirectoryError),
        ),
        # pattern + filetype
        (
            [
                "t1.wav",
                "t2.ogg",
                "s3.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", "t2.ogg"),
                os.path.join("sub", "s3.wav"),
            ],
            "t*",
            "ogg",
            [os.path.join("sub", "t2.ogg"), "t2.ogg"],
            True,
            False,
        ),
        # hidden
        (
            [".file.txt"],
            ".file.txt",
            "",
            [],
            False,
            False,
        ),
        (
            [".file.txt"],
            ".file.txt",
            "",
            [".file.txt"],
            False,
            True,
        ),
        (
            [os.path.join("sub", ".file.txt")],
            ".file.txt",
            "",
            [],
            True,
            False,
        ),
        (
            [os.path.join("sub", ".file.txt")],
            ".file.txt",
            "",
            [os.path.join("sub", ".file.txt")],
            True,
            True,
        ),
        (
            [
                "t1.wav",
                ".t2.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", ".t2.wav"),
            ],
            "",
            "",
            [
                "t1.wav",
            ],
            False,
            False,
        ),
        (
            [
                "t1.wav",
                ".t2.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", ".t2.wav"),
            ],
            "",
            "",
            [
                os.path.join("sub", "t1.wav"),
                "t1.wav",
            ],
            True,
            False,
        ),
        (
            [
                "t1.wav",
                ".t2.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", ".t2.wav"),
            ],
            "",
            "",
            [
                ".t2.wav",
                "t1.wav",
            ],
            False,
            True,
        ),
        (
            [
                "t1.wav",
                ".t2.wav",
                os.path.join("sub", "t1.wav"),
                os.path.join("sub", ".t2.wav"),
            ],
            "",
            "",
            [
                ".t2.wav",
                os.path.join("sub", ".t2.wav"),
                os.path.join("sub", "t1.wav"),
                "t1.wav",
            ],
            True,
            True,
        ),
    ],
)
def test_list_file_names(tmpdir, files, path, filetype, expected, recursive, hidden):
    dir_tmp = tmpdir.mkdir("folder")
    dir_tmp.mkdir("subfolder")
    path = os.path.join(str(dir_tmp), path)
    for file in files:
        # Create the files
        file_tmp = dir_tmp.join(file)
        audeer.mkdir(os.path.dirname(file_tmp))
        file_tmp.write("")
    f = audeer.list_file_names(
        path,
        filetype=filetype,
        basenames=False,
        recursive=recursive,
        hidden=hidden,
    )
    # test full path
    assert f == [audeer.path(dir_tmp, f) for f in expected]
    assert isinstance(f, list)
    # test basenames
    f = audeer.list_file_names(
        path,
        filetype=filetype,
        basenames=True,
        recursive=recursive,
        hidden=hidden,
    )
    assert f == expected


def test_list_file_names_symlinks(tmpdir):
    # symlinks in folder
    folder = audeer.mkdir(tmpdir, "folder")
    file = audeer.touch(folder, "file.txt")
    link = audeer.path(folder, "link.txt")
    os.symlink(file, link)
    files = audeer.list_file_names(folder, basenames=True)
    assert files == ["file.txt", "link.txt"]
    os.remove(link)
    # symlinks to sub-folders
    sub_folder = audeer.mkdir(folder, "sub-folder")
    audeer.touch(sub_folder, "file2.txt")
    link = audeer.path(folder, "link")
    os.symlink(sub_folder, link)
    files = audeer.list_file_names(folder, basenames=True)
    assert files == ["file.txt"]
    files = audeer.list_file_names(folder, basenames=True, recursive=True)
    assert files == [
        "file.txt",
        os.path.join("link", "file2.txt"),
        os.path.join("sub-folder", "file2.txt"),
    ]


def test_md5_errors():
    with pytest.raises(FileNotFoundError):
        audeer.md5("does/not/exist")


@pytest.mark.parametrize(
    "file, content, expected",
    [
        (  # empty file
            "file.txt",
            None,
            "d41d8cd98f00b204e9800998ecf8427e",
        ),
        (  # different content
            "file.txt",
            "hello world",
            "5eb63bbbe01eeed093cb22bb8f5acdc3",
        ),
        (
            "file.txt",
            "Hello World",
            "b10a8db164e0754105b7a99be72e3fe5",
        ),
        (  # different filename
            "file.TXT",
            "Hello World",
            "b10a8db164e0754105b7a99be72e3fe5",
        ),
    ],
)
def test_md5_file(tmpdir, file, content, expected):
    path = audeer.path(tmpdir, file)
    with open(path, "w") as fp:
        if content is not None:
            fp.write(content)

    assert audeer.md5(path) == expected


@pytest.mark.parametrize(
    "tree, content, expected",
    [
        (  # empty folder
            [],
            None,
            "d41d8cd98f00b204e9800998ecf8427e",
        ),
        (  # folder with different content
            ["f"],
            None,
            "8fa14cdd754f91cc6554c9e71929cce7",
        ),
        (
            ["sub/f"],
            None,
            "1af042d5a4ec129583f6093f98f64118",
        ),
        (
            ["f", "sub/f"],
            None,
            "b540f38948f445622adc657a757f4b0d",
        ),
        (
            ["f", "sub/g"],
            None,
            "305107efbb15f9334d22ae4fbeec4de6",
        ),
        (
            ["f", "sub/g"],
            "hello world",
            "47829eb8ef287d0d72e0fed9b96d258d",
        ),
        (
            ["f", "sub/g"],
            "Hello World",
            "442d96d7c43bb18f247888408e5d6977",
        ),
        (  # with empty sub folder
            ["f", "sub/g", "sub/"],
            None,
            "305107efbb15f9334d22ae4fbeec4de6",
        ),
        (  # with hidden file
            ["f", "sub/g", ".hidden"],
            None,
            "97490b233a7717aec19023e28443a1bf",
        ),
        (  # umlaute
            ["ä", "ö", "ü", "ß"],
            None,
            "622165ad36122984c6b2c7ba466aa262",
        ),
    ],
    indirect=["tree"],
)
def test_md5_folder(tmpdir, tree, content, expected):
    if content is not None:
        for path in tree:
            with open(path, "w") as fp:
                fp.write(content)

    assert audeer.md5(tmpdir) == expected


def test_md5_symbolic_link(tmpdir):
    # Link to a file
    file = audeer.touch(tmpdir, "file.txt")
    link = audeer.path(tmpdir, "link.txt")
    os.symlink(file, link)
    assert audeer.md5(file) == audeer.md5(link)
    os.remove(file)
    os.remove(link)
    # Link to a folder
    folder = audeer.mkdir(tmpdir, "folder")
    file = audeer.touch(folder, "file.txt")
    link = audeer.path(tmpdir, "link")
    os.symlink(folder, link)
    assert audeer.md5(folder) == audeer.md5(link)
    os.remove(link)
    # Link to file in folder
    md5_single_file = audeer.md5(folder)
    link = audeer.path(folder, "link.txt")
    os.symlink(file, link)
    md5_link = audeer.md5(folder)
    os.remove(link)
    audeer.touch(folder, "link.txt")
    md5_file = audeer.md5(folder)
    assert md5_link == md5_file
    assert md5_file != md5_single_file


def test_mkdir(tmpdir):
    # New dir
    path = str(tmpdir.mkdir("folder1"))
    p = audeer.mkdir(path)
    assert os.path.isdir(p) is True
    assert p == path
    # Existing dir
    p = audeer.mkdir(path)
    assert os.path.isdir(p) is True
    assert p == path
    # Existing dir with content
    dir_tmp = tmpdir.mkdir("folder2")
    f = dir_tmp.join("file.txt")
    f.write("")
    path = str(dir_tmp)
    p = audeer.mkdir(path)
    assert os.path.isdir(p) is True
    assert p == path
    # Relative path
    path = str(tmpdir.mkdir("folder3"))
    current_path = os.getcwd()
    os.chdir(path)
    p = audeer.mkdir("folder4")
    os.chdir(current_path)
    assert os.path.isdir(p) is True
    assert p == os.path.join(path, "folder4")
    # Subdirectories
    os.chdir(path)
    p = audeer.mkdir("folder5", "folder6")
    os.chdir(current_path)
    assert os.path.isdir(p) is True
    assert p == os.path.join(path, "folder5", "folder6")
    # Path in bytes
    path = str(tmpdir.mkdir("folder7"))
    path = bytes(path, "utf8")
    p = audeer.mkdir(path)
    assert os.path.isdir(p) is True
    assert p == path.decode("utf8")
    # Empty dir
    path = ""
    p = audeer.mkdir(path)
    assert p == path
    # Mode, see https://stackoverflow.com/a/705088
    # Default mode
    os.umask(0)
    p = audeer.mkdir(tmpdir, "folder8", "sub-folder")
    mode = stat.S_IMODE(os.stat(p).st_mode)
    expected_mode = int("777", 8)
    assert mode == expected_mode
    # Non-default modes
    # Under Windows, changing permissions does not work,
    # there we always expect 777
    os.umask(0)
    p = audeer.mkdir(tmpdir, "folder9", "sub-folder", mode=0o775)
    expected_mode = "775"
    if platform.system() == "Windows":
        expected_mode = "777"
    mode = stat.S_IMODE(os.stat(p).st_mode)
    assert mode == int(expected_mode, 8)
    assert mode != int("755", 8)
    os.umask(0)
    p = audeer.mkdir(tmpdir, "folder10", "sub-folder", mode=0o755)
    expected_mode = "755"
    if platform.system() == "Windows":
        expected_mode = "777"
    mode = stat.S_IMODE(os.stat(p).st_mode)
    assert mode == int(expected_mode, 8)
    assert mode != int("775", 8)


@pytest.mark.parametrize(
    "src_path, dst_path",
    [
        (
            "path1",
            "path1",
        ),
        (
            "path1",
            "path2",
        ),
    ],
)
def test_move(tmpdir, src_path, dst_path):
    system = platform.system()
    tmp_dir = audeer.mkdir(tmpdir, "folder")

    # src: file
    # dst: new file
    audeer.touch(tmp_dir, src_path)
    audeer.move(
        os.path.join(tmp_dir, src_path),
        os.path.join(tmp_dir, dst_path),
    )
    if src_path != dst_path:
        assert not os.path.exists(os.path.join(tmp_dir, src_path))
    assert os.path.exists(os.path.join(tmp_dir, dst_path))

    # src: file
    # dst: existing file
    audeer.rmdir(tmp_dir)
    audeer.mkdir(tmp_dir)
    audeer.touch(tmp_dir, src_path)
    audeer.touch(tmp_dir, dst_path)
    audeer.move(
        os.path.join(tmp_dir, src_path),
        os.path.join(tmp_dir, dst_path),
    )
    if src_path != dst_path:
        assert not os.path.exists(os.path.join(tmp_dir, src_path))
    assert os.path.exists(os.path.join(tmp_dir, dst_path))

    # src: folder
    # dst: new folder
    audeer.rmdir(tmp_dir)
    audeer.mkdir(tmp_dir, src_path)
    audeer.touch(tmp_dir, src_path, "file.txt")
    audeer.move(
        os.path.join(tmp_dir, src_path),
        os.path.join(tmp_dir, dst_path),
    )
    if src_path != dst_path:
        assert not os.path.exists(os.path.join(tmp_dir, src_path))
    assert os.path.exists(os.path.join(tmp_dir, dst_path))
    assert os.path.exists(os.path.join(tmp_dir, dst_path, "file.txt"))
    assert os.path.isdir(os.path.join(tmp_dir, dst_path))

    # src: non-empty folder
    # dst: existing non-empty folder
    audeer.rmdir(tmp_dir)
    audeer.mkdir(tmp_dir, src_path)
    audeer.touch(tmp_dir, src_path, "file.txt")
    if src_path != dst_path:
        audeer.mkdir(tmp_dir, dst_path)
        audeer.touch(tmp_dir, dst_path, "file.txt")
    if src_path != dst_path:
        if system == "Windows":
            error_msg = "Access is denied"
        else:
            error_msg = "Directory not empty"
        with pytest.raises(OSError, match=error_msg):
            audeer.move(
                os.path.join(tmp_dir, src_path),
                os.path.join(tmp_dir, dst_path),
            )

        # src: non-empty folder
        # dst: existing empty folder
        os.remove(os.path.join(tmp_dir, dst_path, "file.txt"))
        if system == "Windows":
            # Only under Windows
            # we get an error
            # if destination is an empty folder
            with pytest.raises(OSError, match="Access is denied"):
                audeer.move(
                    os.path.join(tmp_dir, src_path),
                    os.path.join(tmp_dir, dst_path),
                )
        else:
            audeer.move(
                os.path.join(tmp_dir, src_path),
                os.path.join(tmp_dir, dst_path),
            )

            if src_path != dst_path:
                assert not os.path.exists(os.path.join(tmp_dir, src_path))
            assert os.path.exists(os.path.join(tmp_dir, dst_path))
            assert os.path.exists(os.path.join(tmp_dir, dst_path, "file.txt"))
            assert os.path.isdir(os.path.join(tmp_dir, dst_path))

    # src: non-empty folder
    # dst: identical to src
    if src_path == dst_path:
        audeer.move(
            os.path.join(tmp_dir, src_path),
            os.path.join(tmp_dir, dst_path),
        )

        if src_path != dst_path:
            assert not os.path.exists(os.path.join(tmp_dir, src_path))
        assert os.path.exists(os.path.join(tmp_dir, dst_path))
        assert os.path.exists(os.path.join(tmp_dir, dst_path, "file.txt"))
        assert os.path.isdir(os.path.join(tmp_dir, dst_path))

    # src: empty folder
    # dst: existing non-empty folder
    audeer.rmdir(tmp_dir)
    audeer.mkdir(tmp_dir, src_path)
    if src_path != dst_path:
        audeer.mkdir(tmp_dir, dst_path)
        audeer.touch(tmp_dir, dst_path, "file.txt")
    if src_path != dst_path:
        if system == "Windows":
            error_msg = "Access is denied"
        else:
            error_msg = "Directory not empty"
        with pytest.raises(OSError, match=error_msg):
            audeer.move(
                os.path.join(tmp_dir, src_path),
                os.path.join(tmp_dir, dst_path),
            )

        # src: empty folder
        # dst: existing empty folder
        os.remove(os.path.join(tmp_dir, dst_path, "file.txt"))
        if system == "Windows":
            # Only under Windows
            # we get an error
            # if destination is an empty folder
            with pytest.raises(OSError, match="Access is denied"):
                audeer.move(
                    os.path.join(tmp_dir, src_path),
                    os.path.join(tmp_dir, dst_path),
                )
        else:
            audeer.move(
                os.path.join(tmp_dir, src_path),
                os.path.join(tmp_dir, dst_path),
            )

            if src_path != dst_path:
                assert not os.path.exists(os.path.join(tmp_dir, src_path))
            assert os.path.exists(os.path.join(tmp_dir, dst_path))
            assert not os.path.exists(os.path.join(tmp_dir, dst_path, "file.txt"))
            assert os.path.isdir(os.path.join(tmp_dir, dst_path))

    # src: empty folder
    # dst: identical to src
    if src_path == dst_path:
        audeer.move(
            os.path.join(tmp_dir, src_path),
            os.path.join(tmp_dir, dst_path),
        )

        if src_path != dst_path:
            assert not os.path.exists(os.path.join(tmp_dir, src_path))
        assert os.path.exists(os.path.join(tmp_dir, dst_path))
        assert not os.path.exists(os.path.join(tmp_dir, dst_path, "file.txt"))
        assert os.path.isdir(os.path.join(tmp_dir, dst_path))

    if src_path != dst_path:
        # src: file
        # dst: non-empty folder
        audeer.rmdir(tmp_dir)
        audeer.mkdir(tmp_dir)
        audeer.touch(tmp_dir, src_path)
        audeer.mkdir(tmp_dir, dst_path)
        audeer.touch(tmp_dir, dst_path, "file.txt")
        if system == "Windows":
            error_msg = "Access is denied"
        else:
            error_msg = "Is a directory"
        with pytest.raises(OSError, match=error_msg):
            audeer.move(
                os.path.join(tmp_dir, src_path),
                os.path.join(tmp_dir, dst_path),
            )

        # src: file
        # dst: empty folder
        os.remove(os.path.join(tmp_dir, dst_path, "file.txt"))
        with pytest.raises(OSError, match=error_msg):
            audeer.move(
                os.path.join(tmp_dir, src_path),
                os.path.join(tmp_dir, dst_path),
            )

        # src: non-empty folder
        # dst: file
        audeer.rmdir(tmp_dir)
        audeer.mkdir(tmp_dir)
        audeer.mkdir(tmp_dir, src_path)
        audeer.touch(tmp_dir, src_path, "file.txt")
        audeer.touch(tmp_dir, dst_path)
        if system != "Windows":
            error_msg = "Not a directory"
            with pytest.raises(OSError, match=error_msg):
                audeer.move(
                    os.path.join(tmp_dir, src_path),
                    os.path.join(tmp_dir, dst_path),
                )
        else:
            audeer.move(
                os.path.join(tmp_dir, src_path),
                os.path.join(tmp_dir, dst_path),
            )
            assert not os.path.exists(os.path.join(tmp_dir, src_path))
            assert os.path.exists(os.path.join(tmp_dir, dst_path))
            assert os.path.exists(os.path.join(tmp_dir, dst_path, "file.txt"))
            assert os.path.isdir(os.path.join(tmp_dir, dst_path))

        # src: empty folder
        # dst: file
        audeer.rmdir(tmp_dir)
        audeer.mkdir(tmp_dir, src_path)
        audeer.touch(tmp_dir, dst_path)
        if system != "Windows":
            error_msg = "Not a directory"
            with pytest.raises(OSError, match=error_msg):
                audeer.move(
                    os.path.join(tmp_dir, src_path),
                    os.path.join(tmp_dir, dst_path),
                )
        else:
            audeer.move(
                os.path.join(tmp_dir, src_path),
                os.path.join(tmp_dir, dst_path),
            )
            assert not os.path.exists(os.path.join(tmp_dir, src_path))
            assert os.path.exists(os.path.join(tmp_dir, dst_path))
            assert not os.path.exists(os.path.join(tmp_dir, dst_path, "file.txt"))
            assert os.path.isdir(os.path.join(tmp_dir, dst_path))


@pytest.mark.parametrize(
    "src_file, dst_file",
    [
        (
            "file1",
            "file1",
        ),
        (
            "file1",
            "file2",
        ),
    ],
)
def test_move_file(tmpdir, src_file, dst_file):
    tmp_path = audeer.mkdir(tmpdir, "folder")

    src_path = audeer.touch(tmp_path, src_file)
    dst_path = os.path.join(tmp_path, dst_file)

    audeer.move_file(src_path, dst_path)

    if src_file != dst_file:
        assert not os.path.exists(src_path)
    assert os.path.exists(dst_path)


@pytest.mark.parametrize(
    "path, new_extension, ext, expected_path",
    [
        ("", "", None, ""),
        ("", "txt", None, ""),
        ("", "", "rst", ""),
        ("", "txt", "rst", ""),
        ("file", "", None, "file"),
        ("file", "txt", None, "file.txt"),
        ("file.txt", "wav", None, "file.wav"),
        ("test/file.txt", "wav", None, "test/file.wav"),
        ("a/b/../file.txt", "wav", None, "a/b/../file.wav"),
        ("file.txt", "wav", "txt", "file.wav"),
        ("file.txt", "wav", ".txt", "file.wav"),
        ("file.txt", ".wav", "txt", "file.wav"),
        ("file.txt", ".wav", ".txt", "file.wav"),
        ("file.a.b", "wav", "a.b", "file.wav"),
        ("file.a.b", "wav", ".a.b", "file.wav"),
        ("file", "wav", "ext", "file"),
        ("file.txt", "wav", "ext", "file.txt"),
        ("file.txt", "wav", "t", "file.txt"),
    ],
)
def test_replace_file_extension(path, new_extension, ext, expected_path):
    new_path = audeer.replace_file_extension(path, new_extension, ext=ext)
    assert new_path == expected_path


def test_rmdir(tmpdir):
    # Non existing dir
    audeer.rmdir("non-esitent")
    # Folder with file content
    dir_tmp = tmpdir.mkdir("folder")
    f = dir_tmp.join("file.txt")
    f.write("")
    path = str(dir_tmp)
    p = audeer.mkdir(path)
    with pytest.raises(NotADirectoryError):
        audeer.rmdir(os.path.join(p, "file.txt"))
    audeer.rmdir(p)
    assert not os.path.exists(p)
    # Folder with folder content
    p = audeer.mkdir(tmpdir, "folder", "sub-folder")
    audeer.rmdir(tmpdir, "folder")
    assert not os.path.exists(p)
    assert not os.path.exists(os.path.dirname(p))
    # Relative path
    path = str(tmpdir.mkdir("folder"))
    current_path = os.getcwd()
    os.chdir(os.path.dirname(path))
    assert os.path.exists(path)
    audeer.rmdir("folder")
    assert not os.path.exists(path)
    os.chdir(current_path)
    # Symbolic link
    path = audeer.mkdir(tmpdir, "folder")
    link = os.path.join(tmpdir, "link")
    os.symlink(path, link)
    # Error message is broken
    # for newer version of Python 3.12
    # under MacOS and Linux
    python_version = (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )
    if python_version >= (3, 12, 4) and platform.system() != "Windows":
        error_msg = "None"
    else:
        error_msg = "symbolic link"
    with pytest.raises(OSError, match=error_msg):
        audeer.rmdir(link, follow_symlink=False)
    assert os.path.exists(link)
    assert os.path.exists(path)
    audeer.rmdir(link, follow_symlink=True)
    assert not os.path.exists(link)
    assert not os.path.exists(path)


def test_script_dir(tmpdir):
    r"""Test estimation of current directory of caller.

    See https://stackoverflow.com/a/5137509.

    Args:
        tmpdir: tmpdir fixture

    """
    expected_script_dir = os.path.dirname(os.path.realpath(__file__))
    assert audeer.script_dir() == expected_script_dir
    current_dir = os.getcwd()
    os.chdir(tmpdir)
    assert audeer.script_dir() == expected_script_dir
    os.chdir(current_dir)


def test_touch(tmpdir):
    path = audeer.mkdir(tmpdir, "folder1")
    path = os.path.join(path, "file")
    assert not os.path.exists(path)
    audeer.touch(path)
    assert os.path.exists(path)
    stat = os.stat(path)
    time.sleep(0.1)
    audeer.touch(path)
    assert os.path.exists(path)
    new_stat = os.stat(path)
    assert stat.st_atime < new_stat.st_atime
    assert stat.st_mtime < new_stat.st_mtime
