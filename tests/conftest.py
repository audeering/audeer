import os

import pytest


@pytest.fixture(scope='session', autouse=True)
def cleanup():
    yield
    # Clean up after last test
    files = [
        'favicon.png',
        'file.txt',
        os.path.join('path', 'sub', 'file'),
        os.path.join('path', 'file'),
        os.path.join('folder', 'file2'),
    ]
    folders = [
        os.path.join('path', 'sub'),
        os.path.join('path', 'a', 'b', 'c'),
        os.path.join('path', 'a', 'b'),
        os.path.join('path', 'a'),
        'path',
        'folder',
        'path1',
    ]
    for file in files:
        if os.path.exists(file):
            os.remove(file)
    for folder in folders:
        if os.path.exists(folder):
            os.rmdir(folder)
