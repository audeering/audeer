from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import MutableMapping
from collections.abc import Sequence
import json
import os


def load_configuration(
    default_config_file: str,
    user_configs: str | Mapping | Sequence[str | Mapping] | None = None,
    *,
    env_prefix: str | None = None,
    env_replace_sections: bool = True,
    strict: bool = False,
    types: Mapping | None = None,
    validate: Callable[[dict], None] | None = None,
    tracking: MutableMapping | None = None,
) -> dict:
    r"""Load configuration from files and environment variables.

    Configuration values are collected from,
    in order of increasing precedence:

    1. ``default_config_file``,
       e.g. the configuration file shipped with a package
    2. ``user_configs``,
       applied in the given order
       (a later entry overrides an earlier one)
    3. environment variables,
       if ``env_prefix`` is given

    Configuration files or mappings are deep-merged:
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
    Set ``env_replace_sections`` to ``False``
    to ignore such whole-section variables,
    so that only individual values can be overridden;
    with ``strict`` set to ``True``
    such a variable raises a ``ValueError`` instead.
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
    Only keys already present in the merged configuration,
    whether from a file or a mapping,
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

    Set ``strict`` to ``True``
    to check every user configuration
    against ``default_config_file``:
    a key that is not in the default configuration,
    or a value whose type does not match its default value,
    raises a ``ValueError``.
    The types follow the rules of a JSON section replacement:
    an integer is accepted for a float default,
    and a value whose default is ``None`` is not checked,
    unless its type is declared in ``types``.

    Missing or empty configuration files are skipped.

    Reading configuration files requires ``pyyaml``,
    which is installed when depending on ``audeer[yaml]``.

    Args:
        default_config_file: path to default configuration file.
            The file does not have to exist
        user_configs: path(s) to user configuration file(s),
            or already parsed mapping(s),
            applied in the given order.
            Files do not have to exist,
            and a given mapping is not modified
        env_prefix: prefix of environment variables
            used to override configuration values.
            If ``None``, environment variables are ignored
        env_replace_sections: if ``True``,
            a whole nested mapping can be replaced
            by a single environment variable holding a JSON object,
            e.g. ``<env_prefix>_MODEL='{"device": "cpu"}'``.
            If ``False``, such variables are ignored,
            or raise an error if ``strict`` is ``True``,
            and only individual values
            can be overridden by environment variables.
            Declaring a key as ``dict`` in ``types``
            is then not allowed
        strict: if ``True``,
            every user configuration may only contain keys
            of ``default_config_file``,
            with values of the same type as their default values.
            If ``env_replace_sections`` is ``False`` as well,
            an environment variable for a whole section
            raises an error instead of being ignored
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
        tracking: mutable mapping that records,
            for each configuration key,
            which layer set its effective value:
            ``f"file:{path}"`` for ``default_config_file``
            or a ``user_configs`` entry that provided a file,
            ``"mapping[<i>]"`` for the ``user_configs`` entry
            at index ``<i>`` that provided an already parsed mapping
            (indices count every entry of the sequence,
            file or mapping alike),
            or ``f"env:{name}"`` naming the exact environment variable
            (e.g. ``"env:PKG_MODEL__DEVICE"``)
            for an environment variable override.
            A whole-section JSON environment variable
            labels every key it sets;
            a more specific nested variable re-labels
            only the key it overrides.
            Entries are added to ``tracking`` in place.
            Reuse the same mapping across several calls
            to accumulate their entries.
            If ``None``,
            no tracking is performed

    Returns:
        merged configuration dictionary

    Raises:
        ImportError: if ``pyyaml`` is not installed,
            and a configuration file exists
        ValueError: if a configuration file
            does not contain a mapping of key-value pairs
        ValueError: if ``strict`` is ``True``
            and a user configuration contains a key
            that is not in ``default_config_file``,
            or a value whose type does not match its default value
        ValueError: if ``strict`` is ``True``,
            ``env_replace_sections`` is ``False``,
            and an environment variable sets a whole section
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
        ValueError: if a ``types`` entry declares ``dict``
            and ``env_replace_sections`` is ``False``
        ValueError: if ``tracking`` is not a mutable mapping

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

        ``tracking`` records which layer set each key's effective value.

        >>> config_file = audeer.path(tempfile.mkdtemp(), "config.yaml")
        >>> with open(config_file, "w") as file:
        ...     _ = file.write("model:\n  device: cpu\n  lora: false\n")
        >>> os.environ["PKG_MODEL__DEVICE"] = "cuda"
        >>> tracking = {}
        >>> audeer.load_configuration(config_file, env_prefix="PKG", tracking=tracking)
        {'model': {'device': 'cuda', 'lora': False}}
        >>> tracking
        {'model': {'device': 'env:PKG_MODEL__DEVICE', 'lora': 'file:...config.yaml'}}
        >>> del os.environ["PKG_MODEL__DEVICE"]

    """
    cfg = _load_configuration_file(default_config_file)

    if tracking is not None and not isinstance(tracking, MutableMapping):
        raise ValueError(
            f"'tracking' must be a mutable mapping, but is '{type(tracking).__name__}'."
        )

    # Tracking is a genuine structural no-op when off: ``owner`` stays
    # ``None``, so ``_deep_merge()``/``_override_with_environment()`` below
    # run exactly the same path they always did, and no tracking tree is
    # ever built.
    owner: dict | None = None
    if tracking is not None:
        owner = _label_tree(cfg, f"file:{default_config_file}")

    # Checked before the user configurations,
    # as ``strict`` reads ``types`` while it validates them
    if types is not None and not isinstance(types, Mapping):
        raise ValueError(f"'types' must be a mapping, but is '{type(types).__name__}'.")

    if user_configs is not None:
        # User configurations are checked against the default file only,
        # so a value set by an earlier user configuration
        # does not change the type a later one is checked against
        defaults = _copy_mapping(cfg) if strict else {}
        if isinstance(user_configs, (str, Mapping)):
            user_configs = [user_configs]
        for i, user_config in enumerate(user_configs):
            if isinstance(user_config, Mapping):
                update = _copy_mapping(user_config)
                source = f"user configuration at index {i}"
            else:
                update = _load_configuration_file(user_config)
                source = f"configuration file '{user_config}'"
            if strict:
                _validate_user_config(update, defaults, types or {}, source)
            if owner is None:
                _deep_merge(cfg, update)
            else:
                label = (
                    f"mapping[{i}]"
                    if isinstance(user_config, Mapping)
                    else f"file:{user_config}"
                )
                _deep_merge(cfg, update, owner, label)

    if types is not None:
        _validate_types(cfg, types, replace_sections=env_replace_sections)

    if env_prefix is not None:
        _override_with_environment(
            cfg,
            f"{env_prefix}_",
            types or {},
            owner,
            replace_sections=env_replace_sections,
            strict=strict,
        )

    if validate is not None:
        validate(cfg)

    if owner is not None:
        tracking.update(owner)

    return cfg


def _copy_mapping(mapping: Mapping) -> dict:
    r"""Copy a mapping into plain dictionaries.

    Nested mappings, and plain lists and tuples, are copied as well,
    so merging and environment overrides
    cannot modify the mapping given by the user.
    Values of other container types,
    e.g. a ``set`` or a ``NamedTuple``,
    are not copied and remain shared with the given mapping:
    a ``NamedTuple`` is a ``tuple`` subclass
    whose constructor does not accept a single iterable,
    so it is kept as a leaf value like a set is.
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
    if type(value) in (list, tuple):
        return type(value)(_copy_value(item) for item in value)
    return value


def _label_tree(mapping: Mapping, label: str) -> dict:
    r"""Build a tracking tree that attributes every key to ``label``.

    Mirrors the (possibly nested) structure of ``mapping``,
    replacing every leaf value with ``label``.
    Used both for the initial tracking tree
    (every key starts out attributed to the default file)
    and to expand a single label into a per-leaf tree,
    e.g. when a whole configuration section
    is replaced by a JSON environment variable
    and a more specific, nested variable
    later overrides one of its keys.

    Args:
        mapping: mapping whose structure is mirrored
        label: label assigned to every leaf

    Returns:
        tracking tree, the same shape as ``mapping``,
        with ``label`` at every leaf

    """
    return {
        key: _label_tree(value, label) if isinstance(value, Mapping) else label
        for key, value in mapping.items()
    }


def _deep_merge(
    base: dict,
    update: Mapping,
    owner: dict | None = None,
    label: str | None = None,
) -> None:
    r"""Recursively merge ``update`` into ``base`` in place.

    Nested mappings are merged key by key,
    so a key present only in ``base``
    is kept when ``update`` provides the same section.
    Any non-mapping value (including lists)
    replaces the corresponding value in ``base``.

    When ``owner`` is given,
    it is updated in place like ``base``.

    Args:
        base: dictionary to merge into
        update: dictionary whose values take precedence
        owner: owner tracking dictionary to merge into
        label: label attributed to keys set or replaced by ``update``.
            Every key ``update`` touches in this call gets the same
            ``label``, since they all come from the same source.
            Required when ``owner`` is given

    """
    for key, value in update.items():
        if (
            key in base
            and isinstance(base[key], Mapping)
            and isinstance(value, Mapping)
        ):
            if owner is None:
                _deep_merge(base[key], value)
            else:
                # ``base[key]`` is a mapping, so ``owner[key]`` is
                # already a matching nested dict: either from the
                # initial tracking tree, or set by an earlier iteration
                # of this same loop
                _deep_merge(base[key], value, owner[key], label)
        else:
            base[key] = value
            if owner is not None:
                owner[key] = (
                    _label_tree(value, label) if isinstance(value, Mapping) else label
                )


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


def _validate_types(
    cfg: Mapping,
    types: Mapping,
    *,
    replace_sections: bool = True,
) -> None:
    r"""Validate declared ``types`` against the configuration structure.

    Checks, independent of which environment variables are set, that a declared
    leaf type is a class and a declared section type is a mapping. Only entries
    that mirror the configuration are considered.

    Args:
        cfg: configuration dictionary
        types: declared types mirroring ``cfg``
        replace_sections: if ``False``,
            declaring a leaf as ``dict`` is rejected

    Raises:
        ValueError: if a declared section type is not a mapping
        ValueError: if a declared leaf type is not a class
        ValueError: if a declared leaf type is ``dict``
            and ``replace_sections`` is ``False``

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
            _validate_types(value, declared, replace_sections=replace_sections)
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
        elif not replace_sections and declared is dict:
            # A value declared as ``dict`` is replaced as a whole,
            # just like a section, which is disabled
            raise ValueError(
                f"The 'types' entry for '{key}' declares 'dict', "
                f"which has no effect with 'env_replace_sections=False'."
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
        target = _target_type(declared, default_value)
        if target is None:
            continue
        if not _matches_type(json_value, target):
            raise ValueError(
                f"The environment variable '{name}={value}' "
                f"sets '{key_path}' to a value of type "
                f"'{type(json_value).__name__}', "
                f"but the corresponding configuration value "
                f"has type '{target.__name__}'."
            )
        if target is float:
            parsed[key] = float(json_value)


def _target_type(declared: object, default_value: object) -> type | None:
    r"""Type a value is checked against.

    Args:
        declared: entry of ``types`` for the value, if any
        default_value: default value

    Returns:
        the declared type,
        otherwise the type of ``default_value``,
        or ``None`` if neither gives a type

    """
    if isinstance(declared, type):
        return declared
    if default_value is not None:
        return type(default_value)
    return None


def _matches_type(value: object, target: type) -> bool:
    r"""Check if a value matches the type of a configuration value.

    ``bool`` and ``int`` do not match each other,
    although ``bool`` is a subclass of ``int``,
    and an integer matches a ``float``.

    Args:
        value: value to check
        target: wanted type

    Returns:
        ``True`` if ``value`` matches ``target``

    """
    if target is bool:
        return isinstance(value, bool)
    if target is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if target is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, target)


def _validate_user_config(
    update: dict,
    defaults: Mapping,
    types: Mapping,
    source: str,
    path: str = "",
) -> None:
    r"""Validate a user configuration against the default configuration.

    Every key must exist in ``defaults``,
    a section must stay a section,
    and every value must match the type of its default value,
    see :func:`_matches_type`.
    An integer is promoted in place
    where the default value is a float.
    A value with a ``None`` default is not checked,
    unless a type is declared in ``types``.

    Args:
        update: user configuration, modified in place
        defaults: corresponding section of the default configuration
        types: declared types mirroring ``defaults``
        source: description of the user configuration
            used in error messages
        path: dotted key path accumulated so far

    Raises:
        ValueError: if a key is not in ``defaults``,
            or a value does not match the type of its default value

    """
    for key, value in update.items():
        key_path = f"{path}{key}"
        if key not in defaults:
            raise ValueError(
                f"The {source} contains the key '{key_path}', "
                f"which is not in the default configuration."
            )
        default_value = defaults[key]
        declared = types.get(key)
        if isinstance(default_value, Mapping):
            if not isinstance(value, Mapping):
                raise ValueError(
                    f"The {source} sets '{key_path}' to a value of type "
                    f"'{type(value).__name__}', "
                    f"but the default value is a mapping."
                )
            _validate_user_config(
                value,
                default_value,
                declared if isinstance(declared, Mapping) else {},
                source,
                f"{key_path}.",
            )
            continue
        target = _target_type(declared, default_value)
        if target is None:
            continue
        if not _matches_type(value, target):
            raise ValueError(
                f"The {source} sets '{key_path}' to a value of type "
                f"'{type(value).__name__}', "
                f"but the default value has type '{target.__name__}'."
            )
        if target is float:
            update[key] = float(value)


def _override_with_environment(
    cfg: dict,
    env_prefix: str,
    types: Mapping,
    owner: dict | None = None,
    *,
    replace_sections: bool = True,
    strict: bool = False,
) -> None:
    r"""Override configuration values with environment variables in place.

    Nested mappings are traversed recursively.
    The environment variable name of a nested key
    joins the levels with ``__``,
    e.g. ``model.device`` with prefix ``PKG``
    is overridden by ``PKG_MODEL__DEVICE``.

    When ``owner`` is given,
    it is updated in place to mirror ``cfg``:
    a key overridden by an environment variable
    is attributed to that variable's exact name.
    A whole-section JSON replacement
    attributes every one of its leaves
    to the section variable;
    a more specific, nested variable
    applied afterwards then re-attributes
    only the one leaf it overrides.

    Args:
        cfg: configuration dictionary, modified in place
        env_prefix: name prefix accumulated so far,
            including the trailing separator
            (``PKG_`` at the top level, ``PKG_MODEL__`` below)
        types: declared types mirroring ``cfg``,
            used to cast values whose default is ``None``
        owner: owner tracking dictionary, updated in place when given
        replace_sections: if ``False``,
            whole-section variables (e.g. ``PKG_MODEL``) are ignored
        strict: if ``True`` and ``replace_sections`` is ``False``,
            a whole-section variable raises an error

    Raises:
        ValueError: if ``strict`` is ``True``,
            ``replace_sections`` is ``False``,
            and a whole-section variable is set

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
            if not replace_sections and strict and name in os.environ:
                example = next(
                    (
                        f"{name}__{k.upper()}"
                        for k in default_value
                        if isinstance(k, str)
                    ),
                    None,
                )
                hint = f", e.g. '{example}'" if example else ""
                raise ValueError(
                    f"The environment variable '{name}' sets a whole section, "
                    f"which is not allowed with 'env_replace_sections=False'. "
                    f"Set single values instead{hint}."
                )
            if replace_sections and name in os.environ:
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
                if owner is not None:
                    owner[key] = _label_tree(parsed, f"env:{name}")
            _override_with_environment(
                cfg[key],
                f"{name}__",
                key_type or {},
                owner[key] if owner is not None else None,
                replace_sections=replace_sections,
                strict=strict,
            )
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
                if owner is not None:
                    owner[key] = _label_tree(cfg[key], f"env:{name}")
                _override_with_environment(
                    cfg[key],
                    f"{name}__",
                    {},
                    owner[key] if owner is not None else None,
                    replace_sections=replace_sections,
                    strict=strict,
                )
            elif owner is not None:
                owner[key] = f"env:{name}"


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
