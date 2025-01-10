from collections.abc import Sequence
import threading
import time

from tqdm import tqdm

from audeer.core.config import config


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
        return f"{text[:m]}...{text[len(text) - (n - m - 3):]}"


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
    return tqdm_wrapper(
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


def tqdm_wrapper(
    iterable: Sequence,
    maximum_refresh_time: float,
    *args,
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
        kwargs: keyword arguments passed on to ``tqdm``

    Returns:
        progress bar object

    """
    pbar = tqdm(iterable, *args, **kwargs)

    def refresh():
        while not pbar.disable:
            time.sleep(maximum_refresh_time)
            pbar.refresh()

    if maximum_refresh_time is not None:
        thread = threading.Thread(target=refresh, daemon=True)
        thread.start()

    return pbar
