from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
import json
import os


def load_configuration(
    default_config_file: str,
    user_config_files: str | Sequence[str] | None = None,
    *,
    env_prefix: str | None = None,
    types: Mapping | None = None,
    validate: Callable[[dict], None] | None = None,
) -> dict:
    r"""Load configuration from files and environment variables.

    Configuration values are collected from,
    in order of increasing precedence:

    1. ``default_config_file``,
       e.g. the configuration file shipped with a package
    2. ``user_config_files``,
       applied in the given order
       (a later file overrides an earlier one)
    3. environment variables,
       if ``env_prefix`` is given

    Configuration files are deep-merged:
    nested mappings are merged key by key,
    so a section in a user file
    only overrides the keys it defines
    and keeps the remaining keys from the default.
    Any non-mapping value (including a list)
    replaces the previous value as a whole.

    Environment variables are matched
    against the upper-cased configuration keys,
    prefixed with ``env_prefix`` and an underscore,
    e.g. the key ``cache_root``
    is overridden by ``<env_prefix>_CACHE_ROOT``.
    Keys inside nested mappings are addressed
    by joining the levels with ``__``,
    e.g. ``model.device``
    is overridden by ``<env_prefix>_MODEL__DEVICE``.
    A whole nested mapping can instead be replaced
    by a single variable holding a JSON object,
    e.g. ``<env_prefix>_MODEL='{"device": "cpu"}'``;
    the object replaces the mapping as a whole
    (keys it omits are dropped)
    and may introduce keys not present in the files.
    Nested variables are applied afterwards
    and therefore take precedence,
    e.g. ``<env_prefix>_MODEL__DEVICE``
    overrides ``device`` from ``<env_prefix>_MODEL``.
    The value of an environment variable is converted
    to the type of the corresponding default value:
    ``str`` values are used as they are,
    ``int``/``float`` values are cast,
    and ``list``/``dict`` values are parsed as JSON.
    A ``bool`` value is ``True``
    for ``"1"``, ``"true"``, ``"yes"``, ``"on"``
    (case insensitive)
    and ``False`` for any other value;
    a boolean is therefore never rejected,
    whereas ``int``, ``float`` and JSON conversions
    raise a ``ValueError`` on invalid input.
    Only keys already present in the configuration files
    can be overridden by environment variables.
    Only string keys are matched;
    a non-string key (e.g. a numeric YAML key)
    is left untouched.

    A default value of ``None`` carries no type,
    so an environment variable would be kept as a string.
    Use ``types`` to declare the intended type
    for such keys,
    or to override the inferred type of any key.
    ``types`` mirrors the (possibly nested) structure
    of the configuration.

    Missing or empty configuration files are skipped.

    Reading configuration files requires ``pyyaml``,
    which is installed when depending on ``audeer[yaml]``.

    Args:
        default_config_file: path to default configuration file.
            The file does not have to exist
        user_config_files: path(s) to user configuration file(s),
            applied in the given order.
            Files do not have to exist
        env_prefix: prefix of environment variables
            used to override configuration values.
            If ``None``, environment variables are ignored
        types: mapping that declares the type
            of configuration values,
            mirroring the (possibly nested) configuration structure.
            Used to cast environment variable overrides
            for keys whose default value is ``None``,
            or to override the type inferred from the default value
        validate: callable that receives the merged configuration
            dictionary and raises an error if it is invalid.
            It is applied once,
            after files and environment variables are merged

    Returns:
        merged configuration dictionary

    Raises:
        ImportError: if ``pyyaml`` is not installed,
            and a configuration file exists
        ValueError: if a configuration file
            does not contain a mapping of key-value pairs
        ValueError: if an environment variable
            cannot be converted to the type
            of the corresponding default value
        ValueError: if a type declared in ``types``
            is not a class
        ValueError: if ``types``,
            or a ``types`` entry for a nested section,
            is not a mapping

    Examples:
        >>> import tempfile
        >>> config_file = audeer.path(tempfile.mkdtemp(), "config.yaml")
        >>> with open(config_file, "w") as file:
        ...     _ = file.write("cache_root: ~/cache\n")
        >>> audeer.load_configuration(config_file)
        {'cache_root': '~/cache'}

        A key that defaults to ``None`` has no inferred type,
        so declare it in ``types``.

        >>> import os
        >>> config_file = audeer.path(tempfile.mkdtemp(), "config.yaml")
        >>> with open(config_file, "w") as file:
        ...     _ = file.write("hosts: null\n")
        >>> os.environ["APP_HOSTS"] = '["host1", "host2"]'
        >>> audeer.load_configuration(
        ...     config_file, env_prefix="APP", types={"hosts": list}
        ... )
        {'hosts': ['host1', 'host2']}
        >>> del os.environ["APP_HOSTS"]

    """
    cfg = _load_configuration_file(default_config_file)

    if user_config_files is not None:
        if isinstance(user_config_files, str):
            user_config_files = [user_config_files]
        for user_config_file in user_config_files:
            _deep_merge(cfg, _load_configuration_file(user_config_file))

    if types is not None:
        if not isinstance(types, Mapping):
            raise ValueError(
                f"'types' must be a mapping, but is '{type(types).__name__}'."
            )
        _validate_types(cfg, types)

    if env_prefix is not None:
        _override_with_environment(cfg, f"{env_prefix}_", types or {})

    if validate is not None:
        validate(cfg)

    return cfg


def _deep_merge(base: dict, update: dict) -> None:
    r"""Recursively merge ``update`` into ``base`` in place.

    Nested mappings are merged key by key,
    so a key present only in ``base``
    is kept when ``update`` provides the same section.
    Any non-mapping value (including lists)
    replaces the corresponding value in ``base``.

    Args:
        base: dictionary to merge into
        update: dictionary whose values take precedence

    """
    for key, value in update.items():
        if (
            key in base
            and isinstance(base[key], Mapping)
            and isinstance(value, Mapping)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _load_configuration_file(config_file: str) -> dict:
    r"""Read a single configuration file.

    Args:
        config_file: path to a YAML configuration file.
            The file does not have to exist

    Returns:
        configuration dictionary,
        empty if the file is missing or empty

    """
    # Skip missing or empty files
    if not os.path.exists(config_file) or os.path.getsize(config_file) == 0:
        return {}

    # Import lazily as ``pyyaml`` is an optional dependency
    try:
        import yaml
    except ImportError:  # pragma: no cover
        raise ImportError(
            "Reading configuration files requires 'pyyaml'. "
            "Install it with: uv pip install audeer[yaml]"
        )

    with open(config_file) as cf:
        cfg = yaml.load(cf, Loader=yaml.SafeLoader)

    # A file with only comments or whitespace also yields ``None``
    if cfg is None:
        return {}
    if not isinstance(cfg, Mapping):
        raise ValueError(
            f"The configuration file '{config_file}' "
            f"must contain a mapping of key-value pairs, "
            f"but contains a '{type(cfg).__name__}'."
        )
    return dict(cfg)


def _validate_types(cfg: Mapping, types: Mapping) -> None:
    r"""Validate declared ``types`` against the configuration structure.

    Checks, independent of which environment variables are set, that a declared
    leaf type is a class and a declared section type is a mapping. Only entries
    that mirror the configuration are considered.

    Args:
        cfg: configuration dictionary
        types: declared types mirroring ``cfg``

    Raises:
        ValueError: if a declared section type is not a mapping
        ValueError: if a declared leaf type is not a class

    """
    for key, value in cfg.items():
        # An explicit ``None`` entry is a malformed declaration,
        # only an absent key means "no type declared"
        if key not in types:
            continue
        declared = types[key]
        if isinstance(value, Mapping):
            if not isinstance(declared, Mapping):
                raise ValueError(
                    f"The 'types' entry for the nested section '{key}' "
                    f"must be a mapping, but is '{type(declared).__name__}'."
                )
            _validate_types(value, declared)
        elif not isinstance(declared, type):
            raise ValueError(
                f"The 'types' entry for '{key}' is not a type: {declared!r}."
            )


def _override_with_environment(
    cfg: dict,
    env_prefix: str,
    types: Mapping,
) -> None:
    r"""Override configuration values with environment variables in place.

    Nested mappings are traversed recursively.
    The environment variable name of a nested key
    joins the levels with ``__``,
    e.g. ``model.device`` with prefix ``PKG``
    is overridden by ``PKG_MODEL__DEVICE``.

    Args:
        cfg: configuration dictionary, modified in place
        env_prefix: name prefix accumulated so far,
            including the trailing separator
            (``PKG_`` at the top level, ``PKG_MODEL__`` below)
        types: declared types mirroring ``cfg``,
            used to cast values whose default is ``None``

    """
    for key, default_value in cfg.items():
        # Environment variables can only address string keys;
        # non-string keys (e.g. integers) are left untouched.
        if not isinstance(key, str):
            continue
        name = f"{env_prefix}{key.upper()}"
        key_type = types.get(key)
        if isinstance(default_value, Mapping):
            # A whole-section variable (e.g. PKG_MODEL) replaces the mapping
            # as a JSON object; nested variables (e.g. PKG_MODEL__DEVICE) are
            # applied afterwards and therefore take precedence.
            nested_types = dict(key_type or {})
            if name in os.environ:
                # The JSON replacement loses the default types, so remember
                # the original leaf types and reuse them when casting the
                # nested overrides below (an explicit ``types`` entry wins).
                for nested_key, nested_default in default_value.items():
                    if not isinstance(nested_default, Mapping):
                        nested_types.setdefault(nested_key, type(nested_default))
                cfg[key] = _parse_environment_value(
                    name,
                    os.environ[name],
                    default_value,
                    dict,
                )
            _override_with_environment(cfg[key], f"{name}__", nested_types)
        elif name in os.environ:
            cfg[key] = _parse_environment_value(
                name,
                os.environ[name],
                default_value,
                key_type,
            )


def _parse_environment_value(
    name: str,
    value: str,
    default_value: object,
    target_type: type | None = None,
) -> object:
    r"""Convert an environment variable to the wanted type.

    The target type is ``target_type`` if given,
    otherwise the type of ``default_value``.
    A ``None`` default without a declared type
    leaves the value unchanged as a string.
    """
    if target_type is None:
        target_type = type(default_value)
    try:
        # ``bool`` has to be checked before ``int``,
        # as ``bool`` is a subclass of ``int``.
        # A boolean never fails conversion:
        # any value other than the truthy ones becomes ``False``
        if issubclass(target_type, bool):
            return value.lower() in ("1", "true", "yes", "on")
        if issubclass(target_type, int):
            return int(value)
        if issubclass(target_type, float):
            return float(value)
        # ``json.JSONDecodeError`` is a subclass of ``ValueError``
        if issubclass(target_type, (list, dict)):
            parsed = json.loads(value)
            # ``json.loads`` accepts any JSON value,
            # so a scalar like ``"123"`` parses without
            # being the requested ``list``/``dict``.
            if not isinstance(parsed, target_type):
                raise ValueError
            return parsed
    except ValueError as ex:
        raise ValueError(
            f"The environment variable '{name}={value}' "
            f"could not be converted to the type "
            f"'{target_type.__name__}' "
            f"of the corresponding configuration value."
        ) from ex
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
