import os

import audeer


def test_extract_archive_multithread(tmpdir):
    root = audeer.mkdir(tmpdir, "root")
    # Create a bunch of files
    files = [f"file_{i}.txt" for i in range(10)]
    for file in files:
        audeer.touch(root, file)

    archive = audeer.path(tmpdir, "archive.zip")
    audeer.create_archive(root, files, archive)

    destination = audeer.mkdir(tmpdir, "extracted")

    # Extract with num_workers=2
    extracted_files = audeer.extract_archive(
        archive,
        destination,
        num_workers=2,
    )

    assert len(extracted_files) == 10
    assert sorted(extracted_files) == sorted(files)
    for file in files:
        assert os.path.exists(os.path.join(destination, file))


def test_extract_tar_multithread(tmpdir):
    root = audeer.mkdir(tmpdir, "root")
    files = [f"file_{i}.txt" for i in range(10)]
    for file in files:
        audeer.touch(root, file)

    archive = audeer.path(tmpdir, "archive.tar")
    audeer.create_archive(root, files, archive)

    destination = audeer.mkdir(tmpdir, "extracted_tar")

    extracted_files = audeer.extract_archive(
        archive,
        destination,
        num_workers=2,
    )

    assert len(extracted_files) == 10
    assert sorted(extracted_files) == sorted(files)
    for file in files:
        assert os.path.exists(os.path.join(destination, file))


def test_extract_archives_multithread(tmpdir):
    root = audeer.mkdir(tmpdir, "root")
    files = [f"file_{i}.txt" for i in range(10)]
    for file in files:
        audeer.touch(root, file)

    archive1 = audeer.path(tmpdir, "archive1.zip")
    audeer.create_archive(root, files, archive1)
    archive2 = audeer.path(tmpdir, "archive2.zip")
    audeer.create_archive(root, files, archive2)

    destination = audeer.mkdir(tmpdir, "extracted_archives")

    extracted_files = audeer.extract_archives(
        [archive1, archive2],
        destination,
        num_workers=2,
    )

    # extract_archives returns a flat list of all extracted files
    # Since we extract to the same destination and files have same names,
    # they overwrite.
    # But the returned list should contain all of them.
    assert len(extracted_files) == 20
    assert len(set(extracted_files)) == 10  # duplicates because same filenames
