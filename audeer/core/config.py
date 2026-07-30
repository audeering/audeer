from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
import json
import os


def load_configuration(
    default_config_file: str,
    user_config_files: str | Mapping | Sequence[str | Mapping] | None = None,
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
       (a later entry overrides an earlier one)
    3. environment variables,
       if ``env_prefix`` is given

    Configuration files are deep-merged:
    nested mappings are merged key by key,
    so a section in a user file
    only overrides the keys it defines
    and keeps the remaining keys from the default.
    Any non-mapping value (including a list)
    replaces the previous value as a whole.

    A user configuration
    may also be given as an already parsed mapping
    instead of a file path,
    e.g. a single section
    of a configuration file
    that the application has parsed itself
    and that is shared by several packages.
    It is deep-merged in the same way as a file,
    and the given mapping is not modified.

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
    Each value of the object must match the type
    of the default value it replaces
    (an integer is accepted for a float default),
    otherwise a ``ValueError`` is raised;
    introduced keys and keys whose default is ``None``
    keep their JSON type.
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
    A default value of any other type
    (e.g. a date parsed from YAML)
    cannot be overridden
    and raises a ``ValueError`` as well.
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
    of the configuration;
    an entry that does not match a configuration key
    raises a ``ValueError``.

    Missing or empty configuration files are skipped.

    Reading configuration files requires ``pyyaml``,
    which is installed when depending on ``audeer[yaml]``.

    Args:
        default_config_file: path to default configuration file.
            The file does not have to exist
        user_config_files: path(s) to user configuration file(s),
            applied in the given order.
            Files do not have to exist.
            An already parsed mapping
            can be given instead of a file path,
            also as part of the sequence.
            It is not modified
        env_prefix: prefix of environment variables
            used to override configuration values.
            If ``None``, environment variables are ignored
        types: mapping that declares the type
            of configuration values,
            mirroring the (possibly nested) configuration structure.
            Used to cast environment variable overrides
            for keys whose default value is ``None``,
            or to override the type inferred from the default value.
            Supported types are
            ``bool``, ``int``, ``float``, ``str``, ``list``, ``dict``
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
            of the corresponding default value,
            or that type is not supported
        ValueError: if a type declared in ``types``
            is not a class,
            or not one of the supported types
        ValueError: if ``types``,
            or a ``types`` entry for a nested section,
            is not a mapping
        ValueError: if a ``types`` entry
            does not match any configuration key

    Examples:
        >>> import tempfile
        >>> config_file = audeer.path(tempfile.mkdtemp(), "config.yaml")
        >>> with open(config_file, "w") as file:
        ...     _ = file.write("cache_root: ~/cache\n")
        >>> audeer.load_configuration(config_file)
        {'cache_root': '~/cache'}

        A user configuration can also be given
        as an already parsed mapping.

        >>> config_file = audeer.path(tempfile.mkdtemp(), "config.yaml")
        >>> with open(config_file, "w") as file:
        ...     _ = file.write("model:\n  device: cpu\n  lora: false\n")
        >>> audeer.load_configuration(config_file, {"model": {"device": "cuda"}})
        {'model': {'device': 'cuda', 'lora': False}}

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
        if isinstance(user_config_files, (str, Mapping)):
            user_config_files = [user_config_files]
        for user_config_file in user_config_files:
            if isinstance(user_config_file, Mapping):
                _deep_merge(cfg, _copy_mapping(user_config_file))
            else:
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


def _copy_mapping(mapping: Mapping) -> dict:
    r"""Copy a mapping into plain dictionaries.

    Nested mappings, lists, and tuples are copied as well,
    so merging and environment overrides
    cannot modify the mapping given by the user.
    Values of other container types,
    e.g. a ``set``,
    are not copied and remain shared with the given mapping.
    This is not a concern for configuration values
    parsed from JSON or YAML,
    which never produce such types.

    Args:
        mapping: mapping to copy

    Returns:
        copy of ``mapping``, using ``dict`` at every level

    """
    return {key: _copy_value(value) for key, value in mapping.items()}


def _copy_value(value: object) -> object:
    r"""Copy a configuration value, see :func:`_copy_mapping`."""
    if isinstance(value, Mapping):
        return _copy_mapping(value)
    if isinstance(value, (list, tuple)):
        return type(value)(_copy_value(item) for item in value)
    return value


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
    # Reject entries without a matching configuration key
    # to catch misspellings
    for key in types:
        if key not in cfg:
            raise ValueError(
                f"The 'types' entry '{key}' does not match any configuration key."
            )
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
        elif isinstance(declared, Mapping):
            raise ValueError(
                f"The 'types' entry for '{key}' declares a nested section, "
                f"but the corresponding configuration value is not a mapping."
            )
        elif not isinstance(declared, type):
            raise ValueError(
                f"The 'types' entry for '{key}' is not a type: {declared!r}."
            )
        elif declared not in (bool, int, float, str, list, dict):
            # Anything else would silently fall through
            # to keeping the environment variable a string
            raise ValueError(
                f"The 'types' entry for '{key}' "
                f"is not a supported type: '{declared.__name__}'. "
                f"Supported types are "
                f"'bool', 'int', 'float', 'str', 'list', 'dict'."
            )


def _validate_json_replacement(
    name: str,
    value: str,
    parsed: dict,
    defaults: Mapping,
    types: Mapping,
    path: str = "",
) -> None:
    r"""Validate a JSON section replacement against the default values.

    Each value of the parsed JSON object
    must match the type of the default value it replaces,
    mirroring the conversion rules for scalar environment variables.
    An integer is promoted in place
    where the default value is a float.
    Values without a default (introduced keys)
    or with a ``None`` default keep their JSON type,
    unless a type is declared in ``types``.

    Args:
        name: name of the environment variable
        value: raw string value of the environment variable
        parsed: JSON object parsed from ``value``, modified in place
        defaults: section of the configuration the object replaces
        types: declared types mirroring ``defaults``
        path: dotted key path accumulated so far

    Raises:
        ValueError: if a value does not match
            the type of the corresponding default value

    """
    for key, json_value in parsed.items():
        key_path = f"{path}{key}"
        declared = types.get(key)
        default_value = defaults.get(key)
        if isinstance(default_value, Mapping):
            if not isinstance(json_value, dict):
                raise ValueError(
                    f"The environment variable '{name}={value}' "
                    f"sets '{key_path}' to a value of type "
                    f"'{type(json_value).__name__}', "
                    f"but the corresponding configuration value "
                    f"is a mapping."
                )
            _validate_json_replacement(
                name,
                value,
                json_value,
                default_value,
                declared if isinstance(declared, Mapping) else {},
                f"{key_path}.",
            )
            continue
        if isinstance(declared, type):
            target = declared
        elif default_value is not None:
            target = type(default_value)
        else:
            continue
        if target is bool:
            valid = isinstance(json_value, bool)
        elif target is int:
            valid = isinstance(json_value, int) and not isinstance(json_value, bool)
        elif target is float:
            valid = isinstance(json_value, (int, float)) and not isinstance(
                json_value, bool
            )
            if valid:
                parsed[key] = float(json_value)
        else:
            valid = isinstance(json_value, target)
        if not valid:
            raise ValueError(
                f"The environment variable '{name}={value}' "
                f"sets '{key_path}' to a value of type "
                f"'{type(json_value).__name__}', "
                f"but the corresponding configuration value "
                f"has type '{target.__name__}'."
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
            if name in os.environ:
                parsed = _parse_environment_value(
                    name,
                    os.environ[name],
                    default_value,
                    dict,
                )
                # The validation guarantees that the replaced values keep
                # the types of the defaults, so nested overrides applied
                # below still cast to the original types
                _validate_json_replacement(
                    name,
                    os.environ[name],
                    parsed,
                    default_value,
                    key_type or {},
                )
                cfg[key] = parsed
            _override_with_environment(cfg[key], f"{name}__", key_type or {})
        elif name in os.environ:
            cfg[key] = _parse_environment_value(
                name,
                os.environ[name],
                default_value,
                key_type,
            )
            if isinstance(cfg[key], Mapping):
                # A mapping introduced via a declared ``dict`` type
                # behaves like a section, so nested variables
                # are applied on top of it as well
                _override_with_environment(cfg[key], f"{name}__", {})


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
    Any other target type outside the supported set
    raises a ``ValueError``.
    """
    if target_type is None:
        target_type = type(default_value)
    try:
        # A boolean never fails conversion:
        # any value other than the truthy ones becomes ``False``
        if target_type is bool:
            return value.lower() in ("1", "true", "yes", "on")
        if target_type is int:
            return int(value)
        if target_type is float:
            return float(value)
        # ``json.JSONDecodeError`` is a subclass of ``ValueError``
        if target_type in (list, dict):
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
    # A ``None`` default carries no type information,
    # so the value is kept as a string (see ``types``)
    if target_type in (str, type(None)):
        return value
    # E.g. a datetime.date default parsed from YAML;
    # silently keeping the value a string would hide the error
    raise ValueError(
        f"The environment variable '{name}={value}' "
        f"cannot override the corresponding configuration value: "
        f"its type '{target_type.__name__}' is not supported. "
        f"Supported types are "
        f"'bool', 'int', 'float', 'str', 'list', 'dict'."
    )


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
