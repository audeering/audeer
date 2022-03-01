import os

import pytest


@pytest.fixture(scope='session', autouse=True)
def cleanup():
    yield
    # Clean up after last test
    files = [
        'favicon.png',
        'file.txt',
        os.path.join('path', 'file'),
        os.path.join('path1', 'file1'),
        os.path.join('folder', 'file2'),
    ]
    folders = ['folder', 'path', 'path1']
    for file in files:
        if os.path.exists(file):
            os.remove(file)
    for folder in folders:
        if os.path.exists(folder):
            os.rmdir(folder)
