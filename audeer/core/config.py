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
    _provenance_spike: bool = False,
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

    Missing or empty configuration files are skipped.

    Reading configuration files requires ``pyyaml``,
    which is installed when depending on ``audeer[yaml]``.

    Args:
        default_config_file: path to default configuration file.
            The file does not have to exist
        user_config_files: path(s) to user configuration file(s),
            or an already parsed mapping,
            applied in the given order
            (a mapping may also appear as part of the sequence).
            Files do not have to exist,
            and a given mapping is not modified
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

    # --- provenance spike: begin ---
    # Tier 0 raw-chunk collection. Chunk 0 needs an explicit copy because
    # ``cfg`` (built from the default file) keeps being mutated in place by
    # later ``_deep_merge`` calls into its nested dicts; chunks 1..N can just
    # keep the exact dict object handed to ``_deep_merge``, since
    # ``_deep_merge`` never mutates its ``update`` argument, only ``base``.
    _spike_chunks: list[tuple[str, dict]] | None = None
    _spike_env_applications: list[tuple[str, str, object]] | None = None
    if _provenance_spike:
        _spike_chunks = [(f"default:{default_config_file}", _copy_mapping(cfg))]
        _spike_env_applications = []
    # --- provenance spike: end ---

    if user_config_files is not None:
        if isinstance(user_config_files, (str, Mapping)):
            user_config_files = [user_config_files]
        for _spike_i, user_config_file in enumerate(user_config_files):
            if isinstance(user_config_file, Mapping):
                update = _copy_mapping(user_config_file)
                _deep_merge(cfg, update)
                if _provenance_spike:
                    _spike_chunks.append((f"mapping[{_spike_i}]", update))
            else:
                update = _load_configuration_file(user_config_file)
                _deep_merge(cfg, update)
                if _provenance_spike:
                    _spike_chunks.append((f"file:{user_config_file}", update))

    if types is not None:
        if not isinstance(types, Mapping):
            raise ValueError(
                f"'types' must be a mapping, but is '{type(types).__name__}'."
            )
        _validate_types(cfg, types)

    if env_prefix is not None:
        _override_with_environment(
            cfg,
            f"{env_prefix}_",
            types or {},
            env_applications=_spike_env_applications,
        )

    if validate is not None:
        validate(cfg)

    # --- provenance spike: begin ---
    if _provenance_spike:
        owner = _resolve_provenance_spike(
            _spike_chunks,
            _spike_env_applications,
            f"{env_prefix}_" if env_prefix is not None else "",
        )
        return cfg, owner
    # --- provenance spike: end ---

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
    env_applications: list[tuple[str, str, object]] | None = None,
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
                # --- provenance spike ---
                if env_applications is not None:
                    env_applications.append(("section", name, parsed))
            _override_with_environment(
                cfg[key], f"{name}__", key_type or {}, env_applications
            )
        elif name in os.environ:
            cfg[key] = _parse_environment_value(
                name,
                os.environ[name],
                default_value,
                key_type,
            )
            # --- provenance spike ---
            if env_applications is not None:
                env_applications.append(("scalar", name, cfg[key]))
            if isinstance(cfg[key], Mapping):
                # A mapping introduced via a declared ``dict`` type
                # behaves like a section, so nested variables
                # are applied on top of it as well
                _override_with_environment(cfg[key], f"{name}__", {}, env_applications)


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


# =====================================================================
# Provenance spike (Tier 0): everything below this line is throwaway
# spike code, never intended to ship. It answers one question: can the
# per-key "who set the effective value" answer be *derived after the
# fact* from raw, unresolved per-layer chunks (Dynaconf-style), rather
# than recorded at each write site (pydantic-settings-style)?
# =====================================================================


def _merge_with_owner(merged: dict, owner: dict, update: dict, label: str) -> None:
    r"""Replicate ``_deep_merge`` precedence while also tracking ownership.

    Mirrors ``_deep_merge`` exactly: when a key exists in both ``merged``
    and ``update`` as a mapping, we recurse (so the owner tree grows a
    nested dict). Otherwise the whole value at that key is replaced
    wholesale by ``update``, so the whole subtree becomes owned by
    ``label`` -- even if it is itself a nested mapping several levels
    deep, because ``_deep_merge`` would have replaced it as one unit too.

    Args:
        merged: scratch dict replicating the real ``cfg`` merge so far
        owner: parallel dict, same shape as ``merged``, whose leaves are
            either a chunk label (a whole subtree owned by that chunk)
            or a nested dict (a section merged key-by-key from multiple
            chunks)
        update: the next raw chunk to merge in
        label: the chunk's label

    """
    for key, value in update.items():
        if (
            key in merged
            and isinstance(merged[key], Mapping)
            and isinstance(value, Mapping)
        ):
            if not isinstance(owner.get(key), dict):
                owner[key] = {}
            _merge_with_owner(merged[key], owner[key], value, label)
        else:
            merged[key] = _copy_value(value)
            owner[key] = label


def _fill_owner_from_merged(
    owner_dict: dict, merged_value: Mapping, label: str
) -> None:
    r"""Expand a coarse "whole subtree owned by ``label``" marker.

    Needed when a later, more specific override (env only) needs to
    carve a single leaf out of a subtree that a previous chunk replaced
    wholesale. Without this expansion step, descending into that subtree
    to set just one leaf would silently destroy the ownership
    information for its siblings.

    Args:
        owner_dict: dict to populate, mirroring ``merged_value``'s shape
        merged_value: the actual (already resolved) subtree
        label: the label every leaf/section of ``merged_value`` currently
            has, before the more specific override is applied

    """
    for key, value in merged_value.items():
        if isinstance(value, Mapping):
            child: dict = {}
            _fill_owner_from_merged(child, value, label)
            owner_dict[key] = child
        else:
            owner_dict[key] = label


def _set_owner_and_value(
    owner_node: dict,
    merged_node: dict,
    path: tuple[str, ...],
    label: str,
    value: object,
) -> None:
    r"""Apply one environment-variable application to ``owner``/``merged``.

    Handles both env application kinds (whole-section JSON replace, and
    scalar leaf override) with the *same* logic: descend to the parent
    of the target path, then wholesale-replace the final key -- exactly
    mirroring what ``_override_with_environment`` actually does to
    ``cfg`` at that point (a single ``cfg[key] = ...`` assignment).

    The only non-trivial bit is descending through a key that is
    currently a coarse label (e.g. a previous whole-section JSON
    replace) rather than a nested owner dict: that label must first be
    expanded via :func:`_fill_owner_from_merged` so the sibling leaves
    keep their correct provenance.

    Args:
        owner_node: owner dict at the current recursion level
        merged_node: merged dict at the current recursion level,
            mirroring ``owner_node``'s shape
        path: remaining key path to the target leaf/section
        label: label to assign at the end of ``path``
        value: the resolved value to write into ``merged_node`` (so it
            stays in sync for any later, deeper expansion)

    """
    key = path[0]
    if len(path) == 1:
        owner_node[key] = label
        merged_node[key] = value
        return
    if not isinstance(owner_node.get(key), dict):
        expanded: dict = {}
        _fill_owner_from_merged(expanded, merged_node[key], owner_node.get(key))
        owner_node[key] = expanded
    _set_owner_and_value(owner_node[key], merged_node[key], path[1:], label, value)


def _env_name_to_path(name: str, env_prefix: str) -> tuple[str, ...]:
    r"""Reverse ``name = f"{env_prefix}{key.upper()}"`` back to a key path.

    This duplicates the *forward* naming convention from
    ``_override_with_environment`` in reverse, including its nesting
    rule (each level joined by ``__``). It is fragile in exactly the
    way that duplication usually is: if a single, non-nested key
    happens to contain a literal double underscore in its name (e.g. a
    YAML key ``foo__bar``), this reversal cannot tell that apart from a
    section ``foo`` with child ``bar`` -- both produce the environment
    variable name ``..._FOO__BAR``. ``_override_with_environment`` never
    has this ambiguity because it always walks ``cfg`` structurally
    from the top and *constructs* the name; it never has to invert it.

    Args:
        name: full environment variable name, as it appears in
            ``os.environ``
        env_prefix: top-level prefix (including trailing underscore)
            that ``load_configuration`` originally passed to
            ``_override_with_environment``

    Returns:
        key path, e.g. ``("model", "device")``

    """
    remainder = name[len(env_prefix) :]
    return tuple(segment.lower() for segment in remainder.split("__"))


def _resolve_provenance_spike(
    chunks: list[tuple[str, dict]],
    env_applications: list[tuple[str, str, object]],
    env_prefix: str,
) -> dict:
    r"""Derive per-key provenance from raw Tier-0 chunks (after the fact).

    First replays the file/mapping chunks through :func:`_merge_with_owner`
    (replicating ``_deep_merge``'s precedence), then replays the
    environment applications *in the order they were recorded* -- which
    already matches real precedence, since ``_override_with_environment``
    records a whole-section JSON replace before its own nested overrides
    are applied.

    Args:
        chunks: ``(label, raw_chunk_dict)`` pairs, in increasing
            precedence order (default file first)
        env_applications: ``(kind, var_name, value)`` triples, in the
            order they were actually applied
        env_prefix: top-level environment-variable prefix, including
            trailing underscore (``""`` if no ``env_prefix`` was given)

    Returns:
        owner tree, same shape as the final ``cfg``, whose leaves are
        chunk labels (``"default:...''``, ``"file:...''``,
        ``"mapping[i]"``, or ``"env:VAR_NAME"``)

    """
    merged: dict = {}
    owner: dict = {}
    for label, chunk in chunks:
        _merge_with_owner(merged, owner, chunk, label)
    for kind, name, value in env_applications:
        path = _env_name_to_path(name, env_prefix)
        _set_owner_and_value(owner, merged, path, f"env:{name}", value)
    return owner


def _owner_of(owner: dict, path: tuple[str, ...]) -> str | None:
    r"""Look up the provenance label for a leaf key path.

    Stops early if a coarser node along ``path`` is already a plain
    label rather than a nested dict: that means the whole subtree,
    including our leaf, was set wholesale by that one chunk/variable.

    Args:
        owner: owner tree returned by :func:`_resolve_provenance_spike`
        path: key path to look up, e.g. ``("model", "device")``

    Returns:
        the label, or ``None`` if ``path`` does not exist in ``owner``

    """
    node = owner
    for segment in path:
        if not isinstance(node, dict) or segment not in node:
            return None
        node = node[segment]
    return node if isinstance(node, str) else None


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
