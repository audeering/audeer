class config:
    """Get/set defaults for :mod:`audeer`.

    For example, when you want to change the default number of columns
    for the progress bar::

        import audeer

        audeer.config.TQDM_COLUMNS = 50

    """

    TQDM_BAR = "─╸━"
    """Characters used for the progress bar.

    The first character is used for the unfilled portion,
    the last for the filled portion,
    and any characters in between for fractional fills.
    Set to ``None`` to use the default ``tqdm`` bar characters.
    """

    TQDM_COLOUR = "green"
    """Colour of the progress bar.

    Any colour string supported by ``tqdm``,
    e.g. ``'green'``, ``'cyan'``, ``'#00ff00'``.
    Set to ``None`` to disable colouring.
    """

    TQDM_DESCLEN = 60
    """Length of progress bar description."""

    TQDM_FORMAT = (
        "{percentage:3.0f}%|{bar} [{elapsed}<{remaining}] "
        "{desc:" + str(TQDM_DESCLEN) + "}"
    )
    """Format of progress bars."""

    TQDM_COLUMNS = 100
    """Number of columns of progress bars."""

    TQDM_LEAVE = False
    """Leave progress bar on screen after finishing."""
