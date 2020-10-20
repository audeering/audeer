from typing import Sequence

from tqdm import tqdm

from audeer.core.config import config


def format_display_message(
        text: str,
        pbar: bool = False
) -> str:
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

    Example:
        >>> config.TQDM_COLUMNS = 20
        >>> format_display_message('Long text that will be shorten to fit')
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
        return f'{text[:m]}...{text[len(text) - (n - m - 3):]}'


def progress_bar(
        iterable: Sequence = None,
        *,
        total: int = None,
        desc: str = None,
        disable: bool = False
) -> tqdm:
    r"""Progress bar with optional text on the right.

    Args:
        iterable: sequence to iterate through
        total: total number of iterations
        desc: text shown on the right of the progress bar
        disable: don't show the display bar

    Returns:
        progress bar object

    """
    if desc is None:
        desc = ''
    return tqdm(
        iterable=iterable,
        ncols=config.TQDM_COLUMNS,
        bar_format=config.TQDM_FORMAT,
        total=total,
        disable=disable,
        desc=format_display_message(desc, pbar=True),
        leave=config.TQDM_LEAVE,
    )
