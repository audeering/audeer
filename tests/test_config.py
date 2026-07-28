import pathlib

import pytest

import audeer


def write_config(path, content):
    r"""Write ``content`` to ``path`` and return the path."""
    with open(path, "w") as fp:
        fp.write(content)
    return path


def test_load_configuration_missing_file(tmpdir):
    # Non-existing file returns empty dictionary
    config_file = audeer.path(tmpdir, "missing.yaml")
    assert audeer.load_configuration(config_file) == {}


def test_load_configuration_empty_file(tmpdir):
    # Empty file returns empty dictionary
    config_file = write_config(audeer.path(tmpdir, "empty.yaml"), "")
    assert audeer.load_configuration(config_file) == {}


def test_load_configuration_comments_only_file(tmpdir):
    # A non-empty file that only contains comments or whitespace
    # is parsed as ``None`` and returns an empty dictionary
    config_file = write_config(
        audeer.path(tmpdir, "comment.yaml"),
        "# only a comment\n",
    )
    assert audeer.load_configuration(config_file) == {}


def test_load_configuration_default(tmpdir):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    assert audeer.load_configuration(config_file) == {"cache_root": "~/cache"}


def test_load_configuration_user_file(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\nshared: /data\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "cache_root: ~/user\n",
    )
    # User file overrides default,
    # values only in default are kept
    assert audeer.load_configuration(default_file, user_file) == {
        "cache_root": "~/user",
        "shared": "/data",
    }


def test_load_configuration_deep_merge(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cuda\n  lora: false\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "model:\n  lora: true\n",
    )
    # Nested sections are deep-merged:
    # a key set only in the default section is kept,
    # instead of the whole section being replaced
    assert audeer.load_configuration(default_file, user_file) == {
        "model": {"device": "cuda", "lora": True},
    }


def test_load_configuration_deep_merge_user_adds_new_key(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cuda\n  lora: false\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "model:\n  uid: abcdefg-1.0.0\n",
    )
    assert audeer.load_configuration(default_file, user_file) == {
        "model": {"device": "cuda", "lora": False, "uid": "abcdefg-1.0.0"},
    }


def test_load_configuration_deep_merge_user_adds_new_top_level(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cuda\n  lora: false\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "tts:\n  vendor: iva-tts\n",
    )
    # A user config file may introduce a new top-level key
    assert audeer.load_configuration(default_file, user_file) == {
        "model": {"device": "cuda", "lora": False},
        "tts": {"vendor": "iva-tts"},
    }


def test_load_configuration_deep_merge_list_replaced(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "hosts:\n  - a\n  - b\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "hosts:\n  - c\n",
    )
    # A list value is replaced as a whole,
    # it is not merged element-wise
    assert audeer.load_configuration(default_file, user_file) == {
        "hosts": ["c"],
    }


def test_load_configuration_missing_user_file(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    user_file = audeer.path(tmpdir, "missing.yaml")
    # A non-existing user file is skipped,
    # the default configuration is kept
    assert audeer.load_configuration(default_file, user_file) == {
        "cache_root": "~/cache",
    }


def test_load_configuration_multiple_user_files(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    user_file_1 = write_config(
        audeer.path(tmpdir, "user1.yaml"),
        "cache_root: ~/user1\n",
    )
    user_file_2 = write_config(
        audeer.path(tmpdir, "user2.yaml"),
        "cache_root: ~/user2\n",
    )
    # A later file overrides an earlier one
    assert audeer.load_configuration(
        default_file,
        [user_file_1, user_file_2],
    ) == {"cache_root": "~/user2"}


def test_load_configuration_environment(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        (
            "name: default\n"
            "count: 1\n"
            "ratio: 1.5\n"
            "enabled: false\n"
            "repositories:\n"
            "  - name: r1\n"
            "    host: h1\n"
        ),
    )
    # No override without a prefix,
    # even if matching variables are set
    monkeypatch.setenv("PKG_NAME", "env")
    assert audeer.load_configuration(config_file)["name"] == "default"

    # Values are cast to the type of the default value
    monkeypatch.setenv("PKG_NAME", "env")
    monkeypatch.setenv("PKG_COUNT", "5")
    monkeypatch.setenv("PKG_RATIO", "2.5")
    monkeypatch.setenv("PKG_ENABLED", "true")
    monkeypatch.setenv(
        "PKG_REPOSITORIES",
        '[{"name": "r2", "host": "h2"}]',
    )
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {
        "name": "env",
        "count": 5,
        "ratio": 2.5,
        "enabled": True,
        "repositories": [{"name": "r2", "host": "h2"}],
    }


def test_load_configuration_environment_nested(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        ("model:\n  device: cuda\n  lora: false\ngeneration:\n  top_k: 20\n"),
    )
    # Nested keys are addressed with '__' between the levels,
    # and the value is cast to the type of the nested default
    monkeypatch.setenv("PKG_MODEL__DEVICE", "cpu")
    monkeypatch.setenv("PKG_MODEL__LORA", "true")
    monkeypatch.setenv("PKG_GENERATION__TOP_K", "40")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {
        "model": {"device": "cpu", "lora": True},
        "generation": {"top_k": 40},
    }


def test_load_configuration_environment_nested_unknown_key(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cuda\n",
    )
    # Only keys present in the defaults can be overridden:
    # an unknown nested key does not create a new entry
    monkeypatch.setenv("PKG_MODEL__UNKNOWN", "something")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"device": "cuda"}}


def test_load_configuration_environment_deeply_nested(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "a:\n  b:\n    c: default\n",
    )
    # The nested delimiter is a fixed '__' at every level below the top,
    # so overrides also reach three levels deep
    monkeypatch.setenv("PKG_A__B__C", "deep")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"a": {"b": {"c": "deep"}}}


def test_load_configuration_environment_non_string_keys(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "status:\n  200: ok\n",
    )
    # Non-string keys (e.g. numeric YAML keys) cannot be addressed by an
    # environment variable and must not crash when env_prefix is set
    monkeypatch.setenv("PKG_OTHER", "x")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"status": {200: "ok"}}


def test_load_configuration_environment_partial_override(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n  lora: false\n",
    )
    # Only one nested key is overridden; the other stays as in the file
    monkeypatch.setenv("PKG_MODEL__DEVICE", "cuda")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"device": "cuda", "lora": False}}


def test_load_configuration_environment_whole_dict_preserves_type(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  count: 1\n",
    )
    # After a whole-dict replace, a nested override still casts to the
    # original default's type (int)
    monkeypatch.setenv("PKG_MODEL", '{"count": 5}')
    monkeypatch.setenv("PKG_MODEL__COUNT", "2")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"count": 2}}
    assert isinstance(config["model"]["count"], int)


@pytest.mark.parametrize(
    "content, value, match",
    [
        (  # str value where the default is int
            "model:\n  count: 1\n",
            '{"count": "one"}',
            "has type 'int'",
        ),
        (  # same, in a deeper nesting level
            "model:\n  b:\n    c: 1\n",
            '{"b": {"c": "bad"}}',
            "has type 'int'",
        ),
        (  # a nested section replaced by a scalar
            "model:\n  b:\n    c: 1\n",
            '{"b": 5}',
            "is a mapping",
        ),
        (  # int value where the default is bool
            "model:\n  lora: false\n",
            '{"lora": 1}',
            "has type 'bool'",
        ),
        (  # bool value where the default is int
            "model:\n  count: 1\n",
            '{"count": true}',
            "has type 'int'",
        ),
    ],
)
def test_load_configuration_environment_whole_dict_wrong_value_type(
    tmpdir, monkeypatch, content, value, match
):
    config_file = write_config(audeer.path(tmpdir, "default.yaml"), content)
    # A JSON object must match the types of the default values it replaces
    monkeypatch.setenv("PKG_MODEL", value)
    with pytest.raises(ValueError, match=match):
        audeer.load_configuration(config_file, env_prefix="PKG")


def test_load_configuration_environment_whole_dict_nested_preserves_type(
    tmpdir, monkeypatch
):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "a:\n  b:\n    c: 1\n",
    )
    # A nested override on top of a whole-dict replace
    # keeps the original default's type also in deeper levels
    monkeypatch.setenv("PKG_A", '{"b": {"c": 3}}')
    monkeypatch.setenv("PKG_A__B__C", "2")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"a": {"b": {"c": 2}}}
    assert isinstance(config["a"]["b"]["c"], int)


def test_load_configuration_environment_whole_dict_float_promotion(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  ratio: 1.5\n",
    )
    # A JSON int is accepted for a float default and promoted
    monkeypatch.setenv("PKG_MODEL", '{"ratio": 2}')
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"ratio": 2.0}}
    assert isinstance(config["model"]["ratio"], float)


def test_load_configuration_environment_whole_dict_none_default(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: null\n",
    )
    # A None default carries no type, so any JSON value is accepted
    monkeypatch.setenv("PKG_MODEL", '{"device": "cuda"}')
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"device": "cuda"}}


def test_load_configuration_environment_whole_dict_declared_type(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  count: null\n",
    )
    # A ``types`` declaration is also enforced inside a JSON object
    monkeypatch.setenv("PKG_MODEL", '{"count": "5"}')
    with pytest.raises(ValueError, match="has type 'int'"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types={"model": {"count": int}},
        )


def test_load_configuration_environment_whole_dict_replace(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n  lora: false\n",
    )
    # A whole-section variable replaces the mapping as a JSON object,
    # so a key it omits (``lora``) is dropped
    monkeypatch.setenv("PKG_MODEL", '{"device": "cuda"}')
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"device": "cuda"}}


def test_load_configuration_environment_whole_dict_introduces_key(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n",
    )
    # A whole-dict replace may introduce a key not present in the file
    monkeypatch.setenv("PKG_MODEL", '{"device": "cuda", "batch": 8}')
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"device": "cuda", "batch": 8}}


def test_load_configuration_environment_whole_dict_then_nested(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n  lora: false\n",
    )
    # The whole-section variable is applied first,
    # then the nested variable on top (higher precedence)
    monkeypatch.setenv("PKG_MODEL", '{"device": "cuda"}')
    monkeypatch.setenv("PKG_MODEL__DEVICE", "mps")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"device": "mps"}}


@pytest.mark.parametrize(
    "value",
    [
        "5",  # valid JSON, but a scalar and not a mapping
        "[1, 2]",  # valid JSON, but an array and not a mapping
        "{not valid json",  # invalid JSON
    ],
)
def test_load_configuration_environment_whole_dict_invalid(tmpdir, monkeypatch, value):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n",
    )
    # A whole-section variable must be a valid JSON object
    monkeypatch.setenv("PKG_MODEL", value)
    with pytest.raises(ValueError, match="could not be converted to the type"):
        audeer.load_configuration(config_file, env_prefix="PKG")


def test_load_configuration_environment_whole_dict_nested_omitted_key(
    tmpdir, monkeypatch
):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n  lora: false\n",
    )
    # The whole-dict value omits ``lora``; a nested variable for that
    # now-removed key has no effect
    monkeypatch.setenv("PKG_MODEL", '{"device": "cuda"}')
    monkeypatch.setenv("PKG_MODEL__LORA", "true")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"device": "cuda"}}


def test_load_configuration_environment_declared_dict_then_nested(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model: null\n",
    )
    # A None default declared as ``dict`` accepts a JSON object,
    # and nested variables are applied on top of it afterwards,
    # like for any other section
    monkeypatch.setenv("PKG_MODEL", '{"device": "cpu", "batch": 8}')
    monkeypatch.setenv("PKG_MODEL__DEVICE", "cuda")
    config = audeer.load_configuration(
        config_file,
        env_prefix="PKG",
        types={"model": dict},
    )
    assert config == {"model": {"device": "cuda", "batch": 8}}
    assert isinstance(config["model"]["batch"], int)


def test_load_configuration_environment_bool_false(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "enabled: true\n",
    )
    monkeypatch.setenv("PKG_ENABLED", "no")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"enabled": False}


def test_load_configuration_environment_types_none_default(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "timeout: null\n",
    )
    monkeypatch.setenv("PKG_TIMEOUT", "2.5")
    # A None default carries no type,
    # so ``types`` declares the target type for the cast
    config = audeer.load_configuration(
        config_file,
        env_prefix="PKG",
        types={"timeout": float},
    )
    assert config == {"timeout": 2.5}
    assert isinstance(config["timeout"], float)


def test_load_configuration_environment_types_override_default(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        'timeout: "1"\n',
    )
    monkeypatch.setenv("PKG_TIMEOUT", "2")
    # ``types`` overrides the type inferred from the (str) default value
    config = audeer.load_configuration(
        config_file,
        env_prefix="PKG",
        types={"timeout": int},
    )
    assert config == {"timeout": 2}
    assert isinstance(config["timeout"], int)


def test_load_configuration_environment_types_nested(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "audio:\n  activity_preroll_s: null\n",
    )
    monkeypatch.setenv("PKG_AUDIO__ACTIVITY_PREROLL_S", "0.5")
    # ``types`` mirrors the nested structure of the configuration
    config = audeer.load_configuration(
        config_file,
        env_prefix="PKG",
        types={"audio": {"activity_preroll_s": float}},
    )
    assert config == {"audio": {"activity_preroll_s": 0.5}}


def test_load_configuration_environment_types_invalid_value(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "audio:\n  activity_preroll_s: null\n",
    )
    # A value that cannot be cast to the declared type raises
    monkeypatch.setenv("PKG_AUDIO__ACTIVITY_PREROLL_S", "not-a-float")
    with pytest.raises(ValueError, match="could not be converted to the type"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types={"audio": {"activity_preroll_s": float}},
        )


def test_load_configuration_environment_types_json_wrong_type(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "hosts: []\n",
    )
    # A valid JSON list is accepted
    monkeypatch.setenv("PKG_HOSTS", '["a", "b"]')
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config["hosts"] == ["a", "b"]
    # A JSON scalar parses, but is not a list,
    # so it must raise instead of silently returning the wrong type
    monkeypatch.setenv("PKG_HOSTS", "123")
    with pytest.raises(ValueError, match="could not be converted to the type"):
        audeer.load_configuration(config_file, env_prefix="PKG")


def test_load_configuration_types_not_a_mapping(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "timeout: null\n",
    )
    monkeypatch.setenv("PKG_TIMEOUT", "2.5")
    # ``types`` itself must be a mapping
    with pytest.raises(ValueError, match="must be a mapping"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types=["timeout"],
        )


@pytest.mark.parametrize("section_type", [float, dict])
def test_load_configuration_types_section_not_a_mapping(
    tmpdir, monkeypatch, section_type
):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "audio:\n  activity_preroll_s: null\n",
    )
    monkeypatch.setenv("PKG_AUDIO__ACTIVITY_PREROLL_S", "0.5")
    # A ``types`` entry for a nested section must itself be a mapping;
    # a bare type such as ``float`` or ``dict`` is rejected,
    # otherwise the misconfiguration would be silently ignored
    with pytest.raises(ValueError, match="must be a mapping"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types={"audio": section_type},
        )


def test_load_configuration_types_section_for_scalar_value(tmpdir):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model: null\n",
    )
    # A nested ``types`` section requires
    # a matching mapping in the configuration;
    # the error names the mismatch instead of dumping a repr
    with pytest.raises(ValueError, match="declares a nested section"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types={"model": {"device": str}},
        )


def test_load_configuration_types_ignores_unlisted_keys(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "name: default\ntimeout: null\n",
    )
    # A config key without a ``types`` entry is left untouched
    monkeypatch.setenv("PKG_TIMEOUT", "2.5")
    config = audeer.load_configuration(
        config_file,
        env_prefix="PKG",
        types={"timeout": float},
    )
    assert config == {"name": "default", "timeout": 2.5}


def test_load_configuration_types_not_a_type_without_env(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "timeout: null\n",
    )
    # A malformed declared type is rejected up front,
    # even when the matching environment variable is not set
    monkeypatch.delenv("PKG_TIMEOUT", raising=False)
    with pytest.raises(ValueError, match="is not a type"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types={"timeout": "float"},
        )


def test_load_configuration_environment_types_not_a_type(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "timeout: null\n",
    )
    monkeypatch.setenv("PKG_TIMEOUT", "2.5")
    # A declared type that is not a class
    # raises a clear error instead of a TypeError from issubclass()
    with pytest.raises(ValueError, match="is not a type"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types={"timeout": "float"},
        )


@pytest.mark.parametrize("env_set", [True, False])
def test_load_configuration_types_unsupported(tmpdir, monkeypatch, env_set):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "path: null\n",
    )
    if env_set:
        monkeypatch.setenv("PKG_PATH", "file.txt")
    else:
        monkeypatch.delenv("PKG_PATH", raising=False)
    # A declared type outside the supported set is rejected up front
    # instead of silently keeping the value a string
    with pytest.raises(ValueError, match="is not a supported type"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types={"path": pathlib.Path},
        )


def test_load_configuration_types_subclass(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "value: null\n",
    )
    monkeypatch.setenv("PKG_VALUE", "1")

    # A subclass of a supported type is rejected,
    # as the cast would return the base type anyway
    class CustomInt(int):
        pass

    with pytest.raises(ValueError, match="is not a supported type"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types={"value": CustomInt},
        )


@pytest.mark.parametrize(
    "content, types",
    [
        (  # misspelled top-level entry
            "timeout: null\n",
            {"tiemout": float},  # codespell:ignore tiemout
        ),
        (  # misspelled entry inside a nested section
            "connection:\n  timeout: null\n",
            {"connection": {"tiemout": float}},  # codespell:ignore tiemout
        ),
    ],
)
def test_load_configuration_types_unknown_key(tmpdir, content, types):
    config_file = write_config(audeer.path(tmpdir, "default.yaml"), content)
    # A ``types`` entry that does not match a configuration key
    # is rejected to catch misspellings,
    # also when no environment variable is set
    with pytest.raises(ValueError, match="does not match any configuration key"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types=types,
        )


def test_load_configuration_types_unknown_key_json_introduced(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "connection:\n  timeout: null\n",
    )
    # A ``types`` entry for a key that would only enter
    # the configuration via a JSON environment variable
    # is rejected as well
    monkeypatch.setenv(
        "PKG_CONNECTION",
        '{"tiemout": 2}',  # codespell:ignore tiemout
    )
    with pytest.raises(ValueError, match="does not match any configuration key"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types={"connection": {"tiemout": float}},  # codespell:ignore tiemout
        )


@pytest.mark.parametrize(
    "content, name, value",
    [
        (  # YAML parses this default as datetime.date
            "release: 2026-01-01\n",
            "PKG_RELEASE",
            "2027-05-05",
        ),
        (  # YAML parses this default as datetime.datetime
            "start: 2026-01-01 10:00:00\n",
            "PKG_START",
            "2027-01-01 10:00:00",
        ),
    ],
)
def test_load_configuration_environment_unsupported_default_type(
    tmpdir, monkeypatch, content, name, value
):
    config_file = write_config(audeer.path(tmpdir, "default.yaml"), content)
    # A default value of an unsupported type cannot be overridden;
    # silently degrading it to a string would hide the error
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match="is not supported"):
        audeer.load_configuration(config_file, env_prefix="PKG")


def test_load_configuration_environment_none_default_untyped(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "timeout: null\n",
    )
    # A None default carries no type,
    # so without a ``types`` declaration
    # the environment variable is kept as a string
    monkeypatch.setenv("PKG_TIMEOUT", "2.5")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"timeout": "2.5"}


def test_load_configuration_environment_types_none_declared(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "timeout: null\n",
    )
    monkeypatch.setenv("PKG_TIMEOUT", "2.5")
    # An explicit ``None`` entry is a malformed declaration,
    # not the same as leaving the key out of ``types``
    with pytest.raises(ValueError, match="is not a type: None"):
        audeer.load_configuration(
            config_file,
            env_prefix="PKG",
            types={"timeout": None},
        )


def test_load_configuration_non_mapping(tmpdir):
    # A file that does not contain a mapping raises an error
    config_file = write_config(
        audeer.path(tmpdir, "list.yaml"),
        "- a\n- b\n",
    )
    with pytest.raises(ValueError, match="must contain a mapping"):
        audeer.load_configuration(config_file)


@pytest.mark.parametrize(
    "content, name, value",
    [
        ("count: 1\n", "PKG_COUNT", "not-an-int"),
        ("ratio: 1.5\n", "PKG_RATIO", "not-a-float"),
        ("items:\n  - a\n", "PKG_ITEMS", "not-json"),
    ],
)
def test_load_configuration_environment_invalid(
    tmpdir,
    monkeypatch,
    content,
    name,
    value,
):
    config_file = write_config(audeer.path(tmpdir, "default.yaml"), content)
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match="could not be converted to the type"):
        audeer.load_configuration(config_file, env_prefix="PKG")


def test_load_configuration_validate(tmpdir):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )

    calls = []

    def validate(config):
        calls.append(config)
        if "repositories" not in config:
            raise ValueError("Missing repositories.")

    with pytest.raises(ValueError, match="Missing repositories."):
        audeer.load_configuration(config_file, validate=validate)

    # validate() received the merged configuration
    assert calls == [{"cache_root": "~/cache"}]
