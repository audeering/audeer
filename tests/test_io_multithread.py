import os
from unittest import mock
import zipfile

import pytest

import audeer


@pytest.fixture
def archive_files():
    """List of files to create in test archives."""
    return [f"file_{i}.txt" for i in range(10)]


@pytest.fixture
def zip_archive(tmpdir, archive_files):
    """Create a zip archive with test files."""
    root = audeer.mkdir(tmpdir, "root_zip")
    for file in archive_files:
        audeer.touch(root, file)
    archive = audeer.path(tmpdir, "archive.zip")
    audeer.create_archive(root, archive_files, archive)
    return archive, archive_files


@pytest.fixture
def tar_archive(tmpdir, archive_files):
    """Create a tar archive with test files."""
    root = audeer.mkdir(tmpdir, "root_tar")
    for file in archive_files:
        audeer.touch(root, file)
    archive = audeer.path(tmpdir, "archive.tar")
    audeer.create_archive(root, archive_files, archive)
    return archive, archive_files


@pytest.fixture
def empty_zip_archive(tmpdir):
    """Create an empty zip archive."""
    root = audeer.mkdir(tmpdir, "root_empty_zip")
    archive = audeer.path(tmpdir, "empty.zip")
    audeer.create_archive(root, [], archive)
    return archive


@pytest.fixture
def empty_tar_archive(tmpdir):
    """Create an empty tar archive."""
    root = audeer.mkdir(tmpdir, "root_empty_tar")
    archive = audeer.path(tmpdir, "empty.tar")
    audeer.create_archive(root, [], archive)
    return archive


@pytest.mark.parametrize("num_workers", [1, 2, 4])
def test_extract_zip_multithread(tmpdir, zip_archive, num_workers):
    archive, expected_files = zip_archive
    destination = audeer.mkdir(tmpdir, f"extracted_zip_{num_workers}")

    extracted_files = audeer.extract_archive(
        archive,
        destination,
        num_workers=num_workers,
    )

    assert len(extracted_files) == len(expected_files)
    assert extracted_files == expected_files
    extracted_paths = [os.path.join(destination, f) for f in expected_files]
    assert all(os.path.exists(p) for p in extracted_paths)


@pytest.mark.parametrize("num_workers", [1, 2, 4])
def test_extract_tar_multithread(tmpdir, tar_archive, num_workers):
    archive, expected_files = tar_archive
    destination = audeer.mkdir(tmpdir, f"extracted_tar_{num_workers}")

    extracted_files = audeer.extract_archive(
        archive,
        destination,
        num_workers=num_workers,
    )

    assert len(extracted_files) == len(expected_files)
    assert extracted_files == expected_files
    extracted_paths = [os.path.join(destination, f) for f in expected_files]
    assert all(os.path.exists(p) for p in extracted_paths)


@pytest.mark.parametrize("num_workers", [1, 2])
def test_extract_empty_zip_archive(tmpdir, empty_zip_archive, num_workers):
    destination = audeer.mkdir(tmpdir, f"extracted_empty_zip_{num_workers}")

    extracted_files = audeer.extract_archive(
        empty_zip_archive,
        destination,
        num_workers=num_workers,
    )

    assert extracted_files == []


@pytest.mark.parametrize("num_workers", [1, 2])
def test_extract_empty_tar_archive(tmpdir, empty_tar_archive, num_workers):
    destination = audeer.mkdir(tmpdir, f"extracted_empty_tar_{num_workers}")

    extracted_files = audeer.extract_archive(
        empty_tar_archive,
        destination,
        num_workers=num_workers,
    )

    assert extracted_files == []


def test_extract_archives_multithread(tmpdir, archive_files):
    root = audeer.mkdir(tmpdir, "root_multi")
    for file in archive_files:
        audeer.touch(root, file)

    archive1 = audeer.path(tmpdir, "archive1.zip")
    audeer.create_archive(root, archive_files, archive1)
    archive2 = audeer.path(tmpdir, "archive2.zip")
    audeer.create_archive(root, archive_files, archive2)

    destination = audeer.mkdir(tmpdir, "extracted_archives")

    extracted_files = audeer.extract_archives(
        [archive1, archive2],
        destination,
        num_workers=2,
    )

    # extract_archives returns a flat list of all extracted files
    # Since we extract to the same destination and files have same names,
    # they overwrite. But the returned list should contain all of them.
    assert len(extracted_files) == 20
    assert len(set(extracted_files)) == 10  # duplicates because same filenames


@pytest.mark.parametrize("num_workers", [0, -1, -10])
def test_extract_archive_invalid_num_workers(tmpdir, zip_archive, num_workers):
    archive, _ = zip_archive
    destination = audeer.mkdir(tmpdir, f"extracted_invalid_{num_workers}")

    with pytest.raises(ValueError, match="num_workers must be at least 1"):
        audeer.extract_archive(
            archive,
            destination,
            num_workers=num_workers,
        )


def test_extract_archive_preserves_order(tmpdir):
    """Test that extraction preserves original file order."""
    root = audeer.mkdir(tmpdir, "root_order")
    # Create files with names that would sort differently alphabetically
    files = ["z_first.txt", "a_second.txt", "m_third.txt"]
    for file in files:
        audeer.touch(root, file)

    archive = audeer.path(tmpdir, "order_test.zip")
    audeer.create_archive(root, files, archive)

    destination = audeer.mkdir(tmpdir, "extracted_order")

    extracted_files = audeer.extract_archive(
        archive,
        destination,
        num_workers=2,
    )

    # Files should be returned in the order they were added to the archive
    assert extracted_files == files


def test_extract_archive_member_not_found(tmpdir, zip_archive):
    """Test that KeyError from missing member is converted to RuntimeError."""
    archive, _ = zip_archive
    destination = audeer.mkdir(tmpdir, "extracted_missing")

    def mock_getinfo(self, name):
        raise KeyError(name)

    with mock.patch.object(zipfile.ZipFile, "getinfo", mock_getinfo):
        with pytest.raises(RuntimeError, match="Member not found in archive"):
            audeer.extract_archive(
                archive,
                destination,
                num_workers=2,
            )
