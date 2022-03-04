import os

import pytest

import audeer


@pytest.mark.parametrize('path', [
    ('~/.someconfigrc'),
    ('file.tar.gz'),
    ('/a/c.d/g'),
    ('/a/c.d/g.exe'),
    ('../.././README.md'),
    ('folder/file.txt'),
    (b'folder/file.txt'),
    (''),
])
def test_path(path):
    if path:
        expected_path = os.path.abspath(os.path.expanduser(path))
    else:
        expected_path = ''
    if type(expected_path) == bytes:
        expected_path = expected_path.decode('utf8')
    path = audeer.path(path)
    assert path == expected_path
    assert type(path) is str
    path = audeer.safe_path(path)
    assert path == expected_path
    assert type(path) is str


@pytest.mark.parametrize(
    'path, paths',
    [
        ('/a/b', ['file.tar.gz']),
        ('/a', ['b', 'file.tar.gz']),
        ('/a/c.d/g', ['../f']),
        ('', ''),
    ]
)
def test_path_join(path, paths):
    expected_path = os.path.join(path, *paths)
    if expected_path:
        expected_path = os.path.abspath(os.path.expanduser(expected_path))
    else:
        expected_path = ''
    path = audeer.path(path, *paths)
    assert path == expected_path
    assert type(path) is str


def test_path_symlinks(tmpdir):
    filename = 'file.txt'
    linkname = 'link.txt'
    dir_tmp = tmpdir.mkdir('folder')
    f = dir_tmp.join(filename)
    f.write('')
    folder = audeer.mkdir(str(dir_tmp))
    file = os.path.join(folder, filename)
    link = os.path.join(folder, linkname)
    os.symlink(file, link)
    expected_path = os.path.realpath(os.path.expanduser(link))
    path = audeer.path(link)
    _, path = os.path.splitdrive(path)
    _, expected_path = os.path.splitdrive(expected_path)
    assert path == expected_path
    assert type(path) is str
