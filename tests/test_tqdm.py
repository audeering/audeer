import time

import pytest

import audeer


@pytest.mark.parametrize(
    "text",
    [
        ("Hello world"),
        (4 * "abcdefghijklmnopqrstuvwxyz"),
        (18 * "a"),  # 18 == audeer.config.TQDM_COLUMNS as returned by doctest
    ],
)
def test_format_display_message(text):
    t = audeer.format_display_message(text, pbar=False)
    assert len(t) == audeer.config.TQDM_COLUMNS - 2
    if len(text) > audeer.config.TQDM_COLUMNS:
        m = (audeer.config.TQDM_COLUMNS - 3) // 2
        assert t[m - 1 : m + 2] == "..."
    assert t.startswith(text[:2])
    t = audeer.format_display_message(text, pbar=True)
    assert len(t) == audeer.config.TQDM_DESCLEN - 2
    if len(text) > audeer.config.TQDM_DESCLEN:
        m = (audeer.config.TQDM_DESCLEN - 3) // 2
        assert t[m - 1 : m + 2] == "..."
    assert t.startswith(text[:2])


def test_progress_bar():
    assert audeer.config.TQDM_DESCLEN == 60
    assert audeer.config.TQDM_FORMAT == (
        "{percentage:3.0f}%|{bar} [{elapsed}<{remaining}] "
        "{desc:" + str(audeer.config.TQDM_DESCLEN) + "}"
    )
    pbar = audeer.progress_bar([0.1])
    for step in pbar:
        time.sleep(step)


def test_progress_bar_update():
    r"""Ensure progress bar is refreshed.

    If the progress bar has to wait for a long time
    until it would get updated,
    we enforce an update by a given time.

    """
    for _ in audeer.progress_bar(range(2), maximum_refresh_time=0.01):
        time.sleep(0.05)
