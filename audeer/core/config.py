from collections.abc import Sequence
import json
import os


def load_configuration(
    default_config_file: str,
    user_config_files: str | Sequence[str] = None,
    *,
    env_prefix: str = None,
    validate: callable = None,
) -> dict:
    r"""Load configuration from files and environment variables.

    Configuration values are collected from,
    in order of increasing precedence:

    1. ``default_config_file``,
       the configuration file shipped with a package
    2. ``user_config_files``,
       applied in the given order
       (a later file overrides an earlier one)
    3. environment variables,
       if ``env_prefix`` is given

    Environment variables are matched
    against the upper-cased configuration keys,
    prefixed with ``env_prefix`` and an underscore,
    e.g. the key ``cache_root``
    is overridden by ``<env_prefix>_CACHE_ROOT``.
    The value of an environment variable is converted
    to the type of the corresponding default value:
    ``str`` values are used as they are,
    ``bool``/``int``/``float`` values are cast,
    and ``list``/``dict`` values are parsed as JSON.
    Only keys already present in the configuration files
    can be overridden by environment variables.

    Missing or empty configuration files are skipped.

    Reading configuration files requires ``pyyaml``,
    which is installed with ``pip install audeer[yaml]``.

    Args:
        default_config_file: path to the configuration file
            shipped with a package.
            The file does not have to exist
        user_config_files: path(s) to user configuration file(s),
            applied in the given order.
            Files do not have to exist
        env_prefix: prefix of environment variables
            used to override configuration values.
            If ``None``, environment variables are ignored
        validate: callable that receives the merged configuration
            dictionary and raises an error if it is invalid.
            It is applied once,
            after files and environment variables are merged

    Returns:
        merged configuration dictionary

    Raises:
        ImportError: if ``pyyaml`` is not installed,
            and a configuration file exists

    Examples:
        >>> import tempfile
        >>> config_file = audeer.path(tempfile.mkdtemp(), "config.yaml")
        >>> _ = open(config_file, "w").write("cache_root: ~/cache\n")
        >>> audeer.load_configuration(config_file)
        {'cache_root': '~/cache'}

    """
    config = _load_configuration_file(default_config_file)

    if user_config_files is not None:
        if isinstance(user_config_files, str):
            user_config_files = [user_config_files]
        for user_config_file in user_config_files:
            config.update(_load_configuration_file(user_config_file))

    if env_prefix is not None:
        _override_with_environment(config, env_prefix)

    if validate is not None:
        validate(config)

    return config


def _load_configuration_file(config_file: str) -> dict:
    r"""Read a single configuration file.

    Args:
        config_file: path to a YAML configuration file.
            The file does not have to exist

    Returns:
        configuration dictionary,
        empty if the file is missing or empty

    """
    if not os.path.exists(config_file):
        return {}

    # ``pyyaml`` is an optional dependency (``audeer[yaml]``),
    # imported lazily so that audeer's base install stays dependency-light
    try:
        import yaml
    except ImportError:  # pragma: no cover
        raise ImportError(
            "Reading configuration files requires 'pyyaml'. "
            "Install it with: pip install audeer[yaml]"
        )

    with open(config_file) as cf:
        config = yaml.load(cf, Loader=yaml.SafeLoader)

    return config or {}


def _override_with_environment(
    config: dict,
    env_prefix: str,
) -> None:
    r"""Override configuration values with environment variables in place."""
    for key, default_value in config.items():
        name = f"{env_prefix}_{key.upper()}"
        if name in os.environ:
            config[key] = _parse_environment_value(
                os.environ[name],
                default_value,
            )


def _parse_environment_value(value: str, default_value: object) -> object:
    r"""Convert an environment variable to the type of the default value."""
    # ``bool`` has to be checked before ``int``
    if isinstance(default_value, bool):
        return value.lower() in ("1", "true", "yes", "on")
    if isinstance(default_value, int):
        return int(value)
    if isinstance(default_value, float):
        return float(value)
    if isinstance(default_value, (list, dict)):
        return json.loads(value)
    return value


class config:
    """Get/set defaults for :mod:`audeer`.

    For example, when you want to change the default number of columns
    for the progress bar::

        import audeer

        audeer.config.TQDM_COLUMNS = 50

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
