import os
import platform
import stat
import tarfile
import time
import zipfile

import pytest

import audeer


def test_archives(tmpdir):

    # Create tmp files to put in archives
    filenames = ['file1', 'file2']
    dir_tmp = tmpdir.mkdir('content')
    for filename in filenames:
        f = dir_tmp.join(f'{filename}.txt')
        f.write('')
    path = str(dir_tmp)
    src_path = audeer.mkdir(path)
    # Create destination folder
    dir_tmp = tmpdir.mkdir('destination')
    destination = str(dir_tmp)
    os.rmdir(destination)  # make sure destination does not exists
    # Create folder holding archive files
    archive_dir_tmp = tmpdir.mkdir('archives')
    archive_folder = audeer.mkdir(str(archive_dir_tmp))

    # Create archives
    zip_files = []
    tar_files = []
    for filename in filenames:

        src_file = f'{filename}.txt'

        zip_file = os.path.join(archive_folder, f'{filename}.zip')
        audeer.create_archive(src_path, src_file, zip_file)
        zip_files.append(zip_file)

        tar_file = os.path.join(archive_folder, f'{filename}.tar.gz')
        audeer.create_archive(src_path, src_file, tar_file)
        tar_files.append(tar_file)

    with pytest.raises(RuntimeError):
        audeer.create_archive(src_path, src_file, f'{filename}.7z')

    # Extract archives
    members = audeer.extract_archives(zip_files, destination)
    for filename, member in zip(filenames, members):
        target_file = os.path.join(destination, f'{filename}.txt')
        assert os.path.exists(target_file)
        assert os.path.basename(target_file) == member
        os.remove(target_file)

    members = audeer.extract_archives(tar_files, destination)
    for filename, member in zip(filenames, members):
        target_file = os.path.join(destination, f'{filename}.txt')
        assert os.path.exists(target_file)
        assert os.path.basename(target_file) == member
        os.remove(target_file)

    with pytest.raises(RuntimeError):
        audeer.extract_archive(os.path.join(src_path, src_file), destination)

    audeer.extract_archive(tar_files[0], destination, keep_archive=False)
    assert not os.path.exists(tar_files[0])
    assert os.path.exists(tar_files[1])

    # Create broken archives
    for ext in ['zip', 'tar.gz']:
        f = archive_dir_tmp.join(f'broken.{ext}')
        f.write('')
        archive_file = os.path.join(archive_folder, f'broken.{ext}')
        if ext == 'zip':
            with pytest.raises(RuntimeError):
                audeer.extract_archive(
                    archive_file,
                    destination,
                    keep_archive=False,
                )
        elif ext == 'tar.gz':
            with pytest.raises(RuntimeError):
                audeer.extract_archive(
                    archive_file,
                    destination,
                    keep_archive=False,
                )

        # File should still be there if extraction failed
        assert os.path.exists(zip_file)


@pytest.mark.parametrize('path,ext,basename', [
    ('~/.bashrc', None, '.bashrc'),
    ('file.tar.gz', None, 'file.tar'),
    ('/a/c.d/g', None, 'g'),
    (b'/a/c.d/g', None, 'g'),
    ('/a/c.d/g.exe', 'exe', 'g'),
    ('../.././README.md', '.md', 'README'),
    ('folder/file.txt', None, 'file'),
    ('folder/file.txt', 'txt', 'file'),
    (b'folder/file.txt', 'txt', 'file'),
])
def test_basename_wo_ext(path, ext, basename):
    b = audeer.basename_wo_ext(path, ext=ext)
    assert b == basename
    assert type(b) is str


@pytest.mark.parametrize('dirs,expected', [
    ([], ''),
    (
        [
            '/home/user/tmp/coverage/test',
            '/home/user/tmp/covert/operator',
            '/home/user/tmp/coven/members',
        ], '/home/user/tmp',
    ),
    (
        [
            '/home/user/tmp/coverage/test',
            '/home/user/tmp/covert/operator',
            '/home/user/tmp',
        ], '/home/user/tmp',
    ),
    (
        [
            '~/tmp/coverage/test',
            '~/tmp/covert/operator',
            '~/tmp/coven/members',
        ], f'{os.path.expanduser("~")}/tmp',
    ),
    (
        [
            '/etc/tmp/coverage/test',
            '/home/user/tmp/covert/operator',
            '/home/user/tmp/coven/members',
        ], '',
    ),
    (
        [
            '/home/user/tmp',
            '/home/user/tmp',
        ], '/home/user/tmp',
    ),
    (
        [
            '/home1/user/tmp',
            '/home2/user/tmp',
        ], '',
    ),
])
def test_common_directory(dirs, expected):
    common = audeer.common_directory(dirs)
    # Change paths always to Linux syntax
    _, common = os.path.splitdrive(common)
    _, expected = os.path.splitdrive(expected)
    common = common.replace('\\', '/')
    expected = expected.replace('\\', '/')
    # On MacOS we get a '/System/Volumes/Data' in front
    common = common.replace('/System/Volumes/Data', '')
    assert common == expected


def test_download_url(tmpdir):
    url = 'https://audeering.github.io/audeer/_static/favicon.png'
    audeer.download_url(url, tmpdir)
    audeer.download_url(url, tmpdir)
    dst = audeer.download_url(url, tmpdir, force_download=True)
    assert dst == os.path.join(tmpdir, os.path.basename(url))


@pytest.mark.parametrize('path,extension', [
    ('', ''),
    ('~/.bashrc', ''),
    ('file.tar.gz', 'gz'),
    ('/a/c.d/g', ''),
    ('/a/c.d/g.exe', 'exe'),
    ('../.././README.md', 'md'),
    (b'../.././README.md', 'md'),
    ('folder/file.txt', 'txt'),
    (b'folder/file.txt', 'txt'),
    ('test.WAV', 'WAV'),
    ('test.WaV', 'WaV'),
])
def test_file_extension(path, extension):
    ext = audeer.file_extension(path)
    assert ext == extension
    assert type(ext) is str


@pytest.mark.parametrize(
    'dir_list,expected,recursive,hidden',
    [
        ([], [], False, False),
        ([], [], True, False),
        (['a', 'b', 'c'], ['a', 'b', 'c'], False, False),
        (['a', 'b', 'c'], ['a', 'b', 'c'], True, False),
        (['a'], ['a'], False, False),
        (['a'], ['a'], True, False),
        (
            ['a', os.path.join('a', 'b'), os.path.join('a', 'b', 'c')],
            ['a', os.path.join('a', 'b'), os.path.join('a', 'b', 'c')],
            True,
            False,
        ),
        # hidden
        (['a', '.b'], ['a'], True, False),
        (['a', '.b'], ['.b', 'a'], True, True),
        (
            ['a', '.b', os.path.join('a', '.b'), os.path.join('a', '.b', 'c')],
            ['a'],
            True,
            False,
        ),
        (
            ['a', '.b', os.path.join('a', '.b'), os.path.join('a', '.b', 'c')],
            ['.b', 'a', os.path.join('a', '.b'), os.path.join('a', '.b', 'c')],
            True,
            True,
        ),
    ],
)
def test_list_dir_names(tmpdir, dir_list, expected, recursive, hidden):

    dir_tmp = tmpdir.mkdir('folder')
    directories = []
    for directory in dir_list:
        directory = os.path.join(str(dir_tmp), directory)
        directories.append(audeer.mkdir(directory))

    for directory in directories:
        assert os.path.isdir(directory)

    path = os.path.join(str(dir_tmp), '.')
    dirs = audeer.list_dir_names(
        path,
        basenames=False,
        recursive=recursive,
        hidden=hidden,
    )
    assert dirs == [audeer.path(dir_tmp, d) for d in expected]
    assert type(dirs) is list

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
        file = audeer.touch(audeer.path(tmpdir, 'file.txt'))
        audeer.list_dir_names(file)
    with pytest.raises(FileNotFoundError):
        audeer.list_dir_names('not-existent')


@pytest.mark.parametrize(
    'files,path,filetype,expected,recursive,hidden',
    [
        # empty
        ([], '.', '', [], False, False),
        ([], '.', '', [], True, False),
        ([], '.', 'wav', [], False, False),
        ([], '.', 'wav', [], True, False),
        # folder
        (
            ['t3.ogg', 't2.wav', 't1.wav'],
            '.',
            '',
            ['t1.wav', 't2.wav', 't3.ogg'],
            False,
            False,
        ),
        (
            [
                't3.ogg',
                't2.wav',
                't1.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', 't1.ogg'),
            ],
            '.',
            '',
            ['t1.wav', 't2.wav', 't3.ogg'],
            False,
            False,
        ),
        (
            [
                't3.ogg',
                't2.wav',
                't1.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', 'sub', 't1.ogg'),
            ],
            '.',
            '',
            [
                os.path.join('sub', 'sub', 't1.ogg'),
                os.path.join('sub', 't1.wav'),
                't1.wav',
                't2.wav',
                't3.ogg',
            ],
            True,
            False,
        ),
        # filetype
        (
            [
                't3.ogg',
                't2.wav',
                't1.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', 'sub', 't1.ogg'),
            ],
            '.',
            'ogg',
            ['t3.ogg'],
            False,
            False,
        ),
        (
            [
                't3.ogg',
                't2.wav',
                't1.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', 'sub', 't1.ogg'),
            ],
            '.',
            'ogg',
            [
                os.path.join('sub', 'sub', 't1.ogg'),
                't3.ogg',
            ],
            True,
            False,
        ),
        (
            [
                't1.wav',
                os.path.join('sub', 't1.wav'),
            ],
            't1.wav',
            '',
            ['t1.wav'],
            False,
            False,
        ),
        # pattern
        (
            [
                't1.wav',
                't2.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', 't2.wav'),
            ],
            't1.wav',
            '',
            [os.path.join('sub', 't1.wav'), 't1.wav'],
            True,
            False,
        ),
        (
            [
                't1.wav',
                't2.ogg',
                's3.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', 't2.ogg'),
                os.path.join('sub', 's3.wav'),
            ],
            't*',
            '',
            [
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', 't2.ogg'),
                't1.wav',
                't2.ogg'
            ],
            True,
            False,
        ),
        # pattern + filetype
        (
            [
                't1.wav',
                't2.ogg',
                's3.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', 't2.ogg'),
                os.path.join('sub', 's3.wav'),
            ],
            't*',
            'ogg',
            [
                os.path.join('sub', 't2.ogg'),
                't2.ogg'
            ],
            True,
            False,
        ),
        # hidden
        (
            [
                't1.wav',
                '.t2.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', '.t2.wav'),
            ],
            '',
            '',
            [
                't1.wav',
            ],
            False,
            False,
        ),
        (
            [
                't1.wav',
                '.t2.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', '.t2.wav'),
            ],
            '',
            '',
            [
                os.path.join('sub', 't1.wav'),
                't1.wav',
            ],
            True,
            False,
        ),
        (
            [
                't1.wav',
                '.t2.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', '.t2.wav'),
            ],
            '',
            '',
            [
                '.t2.wav',
                't1.wav',
            ],
            False,
            True,
        ),
        (
            [
                't1.wav',
                '.t2.wav',
                os.path.join('sub', 't1.wav'),
                os.path.join('sub', '.t2.wav'),
            ],
            '',
            '',
            [
                '.t2.wav',
                os.path.join('sub', '.t2.wav'),
                os.path.join('sub', 't1.wav'),
                't1.wav',
            ],
            True,
            True,
        ),
    ],
)
def test_list_file_names(tmpdir, files, path, filetype, expected,
                         recursive, hidden):
    dir_tmp = tmpdir.mkdir('folder')
    dir_tmp.mkdir('subfolder')
    path = os.path.join(str(dir_tmp), path)
    for file in files:
        # Create the files
        file_tmp = dir_tmp.join(file)
        audeer.mkdir(os.path.dirname(file_tmp))
        file_tmp.write('')
    f = audeer.list_file_names(
        path,
        filetype=filetype,
        basenames=False,
        recursive=recursive,
        hidden=hidden,
    )
    # test full path
    assert f == [audeer.path(dir_tmp, f) for f in expected]
    assert type(f) is list
    # test basenames
    f = audeer.list_file_names(
        path,
        filetype=filetype,
        basenames=True,
        recursive=recursive,
        hidden=hidden,
    )
    assert f == expected


def test_mkdir(tmpdir):
    # New dir
    path = str(tmpdir.mkdir('folder1'))
    p = audeer.mkdir(path)
    assert os.path.isdir(p) is True
    assert p == path
    # Existing dir
    p = audeer.mkdir(path)
    assert os.path.isdir(p) is True
    assert p == path
    # Existing dir with content
    dir_tmp = tmpdir.mkdir('folder2')
    f = dir_tmp.join('file.txt')
    f.write('')
    path = str(dir_tmp)
    p = audeer.mkdir(path)
    assert os.path.isdir(p) is True
    assert p == path
    # Relative path
    path = str(tmpdir.mkdir('folder3'))
    current_path = os.getcwd()
    os.chdir(path)
    p = audeer.mkdir('folder4')
    os.chdir(current_path)
    assert os.path.isdir(p) is True
    assert p == os.path.join(path, 'folder4')
    # Subdirectories
    os.chdir(path)
    p = audeer.mkdir('folder5/folder6')
    os.chdir(current_path)
    assert os.path.isdir(p) is True
    assert p == os.path.join(path, 'folder5', 'folder6')
    # Path in bytes
    path = str(tmpdir.mkdir('folder7'))
    path = bytes(path, 'utf8')
    p = audeer.mkdir(path)
    assert os.path.isdir(p) is True
    assert p == path.decode('utf8')
    # Empty dir
    path = ''
    p = audeer.mkdir(path)
    assert p == path
    # Mode, see https://stackoverflow.com/a/705088
    # Default mode
    path = os.path.join(str(tmpdir.mkdir('folder8')), 'sub-folder')
    os.umask(0)
    p = audeer.mkdir(path)
    mode = stat.S_IMODE(os.stat(p).st_mode)
    expected_mode = int('777', 8)
    assert mode == expected_mode
    # Non-default modes
    # Under Windows, changing permissions does not work,
    # there we always expect 777
    path = os.path.join(str(tmpdir.mkdir('folder9')), 'sub-folder')
    os.umask(0)
    p = audeer.mkdir(path, mode=0o775)
    expected_mode = '775'
    if platform.system() == 'Windows':
        expected_mode = '777'
    mode = stat.S_IMODE(os.stat(p).st_mode)
    assert mode == int(expected_mode, 8)
    assert mode != int('755', 8)
    path = os.path.join(str(tmpdir.mkdir('folder10')), 'sub-folder')
    os.umask(0)
    p = audeer.mkdir(path, mode=0o755)
    expected_mode = '755'
    if platform.system() == 'Windows':
        expected_mode = '777'
    mode = stat.S_IMODE(os.stat(p).st_mode)
    assert mode == int(expected_mode, 8)
    assert mode != int('775', 8)


@pytest.mark.parametrize(
    'src_file, dst_file',
    [
        (
            'file1',
            'file1',
        ),
        (
            'file1',
            'file2',
        ),
    ]
)
def test_move_file(tmpdir, src_file, dst_file):

    tmp_path = str(tmpdir.mkdir('folder'))
    tmp_path = audeer.mkdir(tmp_path)

    src_path = audeer.touch(os.path.join(tmp_path, src_file))
    dst_path = os.path.join(tmp_path, dst_file)

    audeer.move_file(src_path, dst_path)

    if src_file != dst_file:
        assert not os.path.exists(src_path)
    assert os.path.exists(dst_path)


@pytest.mark.parametrize(
    'path, new_extension, ext, expected_path',
    [
        ('file.txt', 'wav', None, 'file.wav'),
        ('test/file.txt', 'wav', None, 'test/file.wav'),
        ('a/b/../file.txt', 'wav', None, 'a/b/../file.wav'),
        ('file.txt', 'wav', 'txt', 'file.wav'),
        ('file.txt', 'wav', '.txt', 'file.wav'),
        ('file.txt', 'wav', 't', 'file.txwav'),
        ('file.a.b', 'wav', 'a.b', 'file.wav'),
        ('file.a.b', 'wav', '.a.b', 'file.wav'),
    ]
)
def test_replace_file_extension(path, new_extension, ext, expected_path):
    new_path = audeer.replace_file_extension(path, new_extension, ext=ext)
    assert new_path == expected_path


def test_rmdir(tmpdir):
    # Non existing dir
    audeer.rmdir('non-esitent')
    # Folder with file content
    dir_tmp = tmpdir.mkdir('folder')
    f = dir_tmp.join('file.txt')
    f.write('')
    path = str(dir_tmp)
    p = audeer.mkdir(path)
    with pytest.raises(NotADirectoryError):
        audeer.rmdir(os.path.join(p, 'file.txt'))
    audeer.rmdir(p)
    assert not os.path.exists(p)
    # Folder with folder content
    path = str(tmpdir.mkdir('folder'))
    p = audeer.mkdir(os.path.join(path, 'sub-folder'))
    audeer.rmdir(os.path.dirname(p))
    assert not os.path.exists(p)
    assert not os.path.exists(os.path.dirname(p))
    # Relative path
    path = str(tmpdir.mkdir('folder'))
    current_path = os.getcwd()
    os.chdir(os.path.dirname(path))
    assert os.path.exists(path)
    audeer.rmdir('folder')
    assert not os.path.exists(path)
    os.chdir(current_path)


def test_touch(tmpdir):
    path = str(tmpdir.mkdir('folder1'))
    path = audeer.mkdir(path)
    path = os.path.join(path, 'file')
    assert not os.path.exists(path)
    audeer.touch(path)
    assert os.path.exists(path)
    stat = os.stat(path)
    time.sleep(.1)
    audeer.touch(path)
    assert os.path.exists(path)
    new_stat = os.stat(path)
    assert stat.st_atime < new_stat.st_atime
    assert stat.st_mtime < new_stat.st_mtime
