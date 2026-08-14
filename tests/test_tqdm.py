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
    assert audeer.config.TQDM_BAR == "╸"
    assert audeer.config.TQDM_COLOUR == "green"
    assert audeer.config.TQDM_BG_COLOUR == "black"
    assert audeer.config.TQDM_DESCLEN == 60
    assert audeer.config.TQDM_FORMAT == (
        "{percentage:3.0f}% {bar} {elapsed}<{remaining} "
        "{desc:" + str(audeer.config.TQDM_DESCLEN) + "}"
    )
    pbar = audeer.progress_bar([0.1])
    for step in pbar:
        time.sleep(step)


def test_ansi_colour():
    """Test _ansi_colour with hex colours and invalid input."""
    from audeer.core.tqdm import _ansi_colour

    # Hex colour
    assert _ansi_colour("#ff8000") == "\033[38;2;255;128;0m"
    # Invalid/unknown colour returns empty string
    assert _ansi_colour("nonexistent") == ""
    assert _ansi_colour(123) == ""


def test_progress_bar_no_bg_colour():
    """Cover the else branch when TQDM_BG_COLOUR is None."""
    original_bg = audeer.config.TQDM_BG_COLOUR
    original_bar = audeer.config.TQDM_BAR
    original_colour = audeer.config.TQDM_COLOUR
    try:
        # Both TQDM_BAR and TQDM_COLOUR set, but no BG colour
        audeer.config.TQDM_BG_COLOUR = None
        audeer.config.TQDM_BAR = "="
        audeer.config.TQDM_COLOUR = "green"
        pbar = audeer.progress_bar([0], disable=True)
        for _ in pbar:
            pass

        # Only TQDM_COLOUR is None (no colour kwarg passed)
        audeer.config.TQDM_COLOUR = None
        audeer.config.TQDM_BAR = "="
        pbar = audeer.progress_bar([0], disable=True)
        for _ in pbar:
            pass

        # Both None
        audeer.config.TQDM_BAR = None
        pbar = audeer.progress_bar([0], disable=True)
        for _ in pbar:
            pass
    finally:
        audeer.config.TQDM_BG_COLOUR = original_bg
        audeer.config.TQDM_BAR = original_bar
        audeer.config.TQDM_COLOUR = original_colour


def test_progress_bar_update():
    r"""Ensure progress bar is refreshed.

    If the progress bar has to wait for a long time
    until it would get updated,
    we enforce an update by a given time.

    """
    for _ in audeer.progress_bar(range(2), maximum_refresh_time=0.01):
        time.sleep(0.05)
