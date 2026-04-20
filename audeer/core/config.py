class config:
    """Get/set defaults for :mod:`audeer`.

    For example, when you want to change the default number of columns
    for the progress bar::

        import audeer

        audeer.config.TQDM_COLUMNS = 50

    """

    TQDM_BAR = "╸"
    """Character used for the progress bar.

    Used for both filled and unfilled portions
    when :attr:`TQDM_BG_COLOUR` is set,
    providing a uv-style dashed progress bar.
    Set to ``None`` to use the default ``tqdm`` bar characters.
    """

    TQDM_BG_COLOUR = "black"
    """Colour for the unfilled portion of the progress bar.

    When set together with :attr:`TQDM_COLOUR`,
    enables a dual-coloured progress bar.
    Supports named colours
    (e.g. ``'green'``, ``'cyan'``, ``'dark_grey'``)
    and hex colours (e.g. ``'#808080'``).
    Set to ``None`` to disable.
    """

    TQDM_COLOUR = "green"
    """Colour for the filled portion of the progress bar.

    Supports named colours
    (e.g. ``'green'``, ``'cyan'``, ``'dark_grey'``)
    and hex colours (e.g. ``'#00ff00'``).
    Set to ``None`` to disable colouring.
    """

    TQDM_DESCLEN = 60
    """Length of progress bar description."""

    TQDM_FORMAT = (
        "{percentage:3.0f}% {bar} {elapsed}<{remaining} "
        "{desc:" + str(TQDM_DESCLEN) + "}"
    )
    """Format of progress bars."""

    TQDM_COLUMNS = 100
    """Number of columns of progress bars."""

    TQDM_LEAVE = False
    """Leave progress bar on screen after finishing."""
