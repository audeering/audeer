from collections.abc import Sequence
import threading
import time

from tqdm import tqdm

from audeer.core.config import config


_ANSI_COLOURS = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "dark_grey": 90,
    "dark_gray": 90,
    "bright_red": 91,
    "bright_green": 92,
    "bright_yellow": 93,
    "bright_blue": 94,
    "bright_magenta": 95,
    "bright_cyan": 96,
    "bright_white": 97,
}
_ANSI_RESET = "\033[0m"

# Placeholder characters used internally for the bar.
# These are replaced with coloured bar characters in _ColouredTqdm.
_PLACEHOLDER_FULL = "\u2588"  # █ (full block)
_PLACEHOLDER_EMPTY = "\u2800"  # ⠀ (braille pattern blank)


def _ansi_colour(colour):
    """Convert a colour name or hex string to an ANSI escape code."""
    if colour in _ANSI_COLOURS:
        return f"\033[{_ANSI_COLOURS[colour]}m"
    if isinstance(colour, str) and colour.startswith("#") and len(colour) == 7:
        r = int(colour[1:3], 16)
        g = int(colour[3:5], 16)
        b = int(colour[5:7], 16)
        return f"\033[38;2;{r};{g};{b}m"
    return ""


class _ColouredTqdm(tqdm):
    """Tqdm subclass with dual-coloured bar."""

    _bar_char = "\u2588"
    _fc = ""
    _uc = ""

    def __str__(self):
        s = super().__str__()
        filled = s.count(_PLACEHOLDER_FULL)
        unfilled = s.count(_PLACEHOLDER_EMPTY)
        bc = self._bar_char
        colored = f"{self._fc}{bc * filled}{self._uc}{bc * unfilled}{_ANSI_RESET}"
        start = s.find(_PLACEHOLDER_FULL) if filled else s.find(_PLACEHOLDER_EMPTY)
        if start >= 0:
            end = (
                max(
                    s.rfind(_PLACEHOLDER_FULL),
                    s.rfind(_PLACEHOLDER_EMPTY),
                )
                + 1
            )
            s = s[:start] + colored + s[end:]
        return s


def format_display_message(text: str, pbar: bool = False) -> str:
    """Ensure a fixed length of text printed to screen.

    The length of the text message is the same as the overall
    progress bar length as given by :attr:`audeer.config.TQDM_COLUMNS`.

    Args:
        text: text to be displayed
        pbar: if a progress bar is displayed as well.
            This will shorten the text to the given progress bar
            description length :attr:`audeer.config.TQDM_DESCLEN`

    Returns:
        formatted text message

    Examples:
        >>> audeer.config.TQDM_COLUMNS = 20
        >>> audeer.format_display_message("Long text that will be shorten to fit")
        'Long te...n to fit'

    """
    if not text:
        return text
    if pbar:
        n = config.TQDM_DESCLEN - 2
    else:
        n = config.TQDM_COLUMNS - 2
    if len(text) == n:
        return text
    elif len(text) < n:
        return text.ljust(n)
    else:
        m = (n - 3) // 2
        return f"{text[:m]}...{text[len(text) - (n - m - 3) :]}"


def progress_bar(
    iterable: Sequence = None,
    *,
    total: int = None,
    desc: str = None,
    disable: bool = False,
    maximum_refresh_time: float = None,
) -> tqdm:
    r"""Progress bar with optional text on the right.

    If you want to show a constant description text
    during presenting the progress bar,
    you can use it similar to:

    .. code-block:: python

        for file in progress_bar(files, desc="Copying"):
            copy(file)

    When the text should be updated as well,
    you have to explicitly do that in each step:

    .. code-block:: python

        with progress_bar(files) as pbar:
            for file in pbar:
                desc = format_display_message(
                    f"Copying {file}",
                    pbar=True,
                )
                pbar.set_description_str(desc)
                pbar.refresh()
                copy(file)
                pbar.update()

    Args:
        iterable: sequence to iterate through
        total: total number of iterations
        desc: text shown on the right of the progress bar
        disable: don't show the display bar
        maximum_refresh_time: refresh the progress bar
            at least every ``maximum_refresh_time`` seconds,
            using another thread.
            If ``None``,
            no refreshing is enforced

    Returns:
        progress bar object

    """
    if desc is None:
        desc = ""
    kwargs = dict(
        iterable=iterable,
        maximum_refresh_time=maximum_refresh_time,
        ncols=config.TQDM_COLUMNS,
        bar_format=config.TQDM_FORMAT,
        total=total,
        disable=disable,
        desc=format_display_message(desc, pbar=True),
        leave=config.TQDM_LEAVE,
        smoothing=0,
    )
    if config.TQDM_COLOUR is not None and config.TQDM_BG_COLOUR is not None:
        # Dual-colour mode: use placeholder ascii chars
        # that get replaced with coloured bar chars in _ColouredTqdm
        kwargs["ascii"] = f"{_PLACEHOLDER_EMPTY}{_PLACEHOLDER_FULL}"
        kwargs["cls"] = _ColouredTqdm
        kwargs["cls"]._bar_char = config.TQDM_BAR or _PLACEHOLDER_FULL
        kwargs["cls"]._fc = _ansi_colour(config.TQDM_COLOUR)
        kwargs["cls"]._uc = _ansi_colour(config.TQDM_BG_COLOUR)
    else:
        if config.TQDM_BAR is not None:
            kwargs["ascii"] = config.TQDM_BAR
        if config.TQDM_COLOUR is not None:
            kwargs["colour"] = config.TQDM_COLOUR
    return tqdm_wrapper(**kwargs)


def tqdm_wrapper(
    iterable: Sequence,
    maximum_refresh_time: float,
    *args,
    cls: type = tqdm,
    **kwargs,
) -> tqdm:
    r"""Tqdm progress bar wrapper to enforce update once a second.

    When using tqdm with large time durations
    between single steps of the iteration,
    it will not automatically update the elapsed time,
    but needs to be forced,
    see https://github.com/tqdm/tqdm/issues/861#issuecomment-2197893883.

    Args:
        iterable: sequence to iterate through
        maximum_refresh_time: refresh the progress bar
            at least every ``maximum_refresh_time`` seconds,
            using another thread.
            If ``None``,
            no refreshing is enforced
        args: arguments passed on to ``tqdm``
        cls: tqdm class to instantiate
        kwargs: keyword arguments passed on to ``tqdm``

    Returns:
        progress bar object

    """
    pbar = cls(iterable, *args, **kwargs)

    def refresh():
        while not pbar.disable:
            time.sleep(maximum_refresh_time)
            pbar.refresh()

    if maximum_refresh_time is not None:
        thread = threading.Thread(target=refresh, daemon=True)
        thread.start()

    return pbar
