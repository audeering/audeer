import collections
from collections import UserDict
import pathlib
from types import MappingProxyType

import pytest
import yaml

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


def test_load_configuration_deep_merge_scalar_replaces_section(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cuda\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "model: none\n",
    )
    # A scalar in the user file replaces a whole default section
    assert audeer.load_configuration(default_file, user_file) == {"model": "none"}


def test_load_configuration_deep_merge_section_replaces_scalar(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model: none\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "model:\n  device: cuda\n",
    )
    # A mapping in the user file replaces a scalar default as a whole
    assert audeer.load_configuration(default_file, user_file) == {
        "model": {"device": "cuda"},
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


def test_load_configuration_missing_default_with_user_file(tmpdir):
    default_file = audeer.path(tmpdir, "missing.yaml")
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "cache_root: ~/user\n",
    )
    # A missing default file yields an empty base,
    # the user file provides the whole configuration
    assert audeer.load_configuration(default_file, user_file) == {
        "cache_root": "~/user",
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


def test_load_configuration_user_mapping(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cuda\n  lora: false\n",
    )
    # An already parsed mapping is accepted instead of a file path,
    # and is deep-merged like a file:
    # a key set only in the default file is kept
    assert audeer.load_configuration(default_file, {"model": {"device": "cpu"}}) == {
        "model": {"device": "cpu", "lora": False},
    }


def test_load_configuration_user_mapping_after_file(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "cache_root: ~/user\n",
    )
    # A sequence may mix file paths and mappings;
    # the mapping comes last and wins
    assert audeer.load_configuration(
        default_file,
        [user_file, {"cache_root": "~/mapping"}],
    ) == {"cache_root": "~/mapping"}


def test_load_configuration_user_mapping_before_file(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "cache_root: ~/user\n",
    )
    # The file comes last and wins
    assert audeer.load_configuration(
        default_file,
        [{"cache_root": "~/mapping"}, user_file],
    ) == {"cache_root": "~/user"}


def test_load_configuration_user_mapping_empty(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cuda\n  lora: false\n",
    )
    # An empty mapping keeps the default values
    assert audeer.load_configuration(default_file, {}) == {
        "model": {"device": "cuda", "lora": False},
    }


def test_load_configuration_user_mapping_adds_new_key(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cuda\n",
    )
    user_config = {"model": {"lora": True}, "tts": {"vendor": "iva-tts"}}
    # A mapping may introduce keys that are not in the default file,
    # inside a nested section and at the top level
    assert audeer.load_configuration(default_file, user_config) == {
        "model": {"device": "cuda", "lora": True},
        "tts": {"vendor": "iva-tts"},
    }


def test_load_configuration_user_mapping_list_replaced(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "hosts:\n  - a\n  - b\n",
    )
    # A list value of the mapping replaces the default list as a whole
    assert audeer.load_configuration(default_file, {"hosts": ["c"]}) == {
        "hosts": ["c"],
    }


def test_load_configuration_user_mapping_list_not_modified(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "hosts:\n  - a\n",
    )
    user_config = {"hosts": ["b"], "repositories": [{"name": "r1"}]}
    config = audeer.load_configuration(default_file, user_config)
    # Lists, and the mappings they contain, are copied as well,
    # so changing them afterwards
    # does not change the configuration
    user_config["hosts"].append("c")
    user_config["repositories"][0]["name"] = "r2"
    assert config == {"hosts": ["b"], "repositories": [{"name": "r1"}]}


def test_load_configuration_user_mapping_tuple_not_modified(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "name: default\n",
    )
    user_config = {"t": ({"k": 1},)}
    config = audeer.load_configuration(default_file, user_config)
    # A tuple, and the mappings it contains, are copied as well,
    # so mutating them afterwards does not change the configuration
    user_config["t"][0]["k"] = 2
    assert config == {"name": "default", "t": ({"k": 1},)}


def test_load_configuration_user_mapping_named_tuple_not_copied(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "name: default\n",
    )
    Point = collections.namedtuple("Point", ["x", "y"])
    point = Point(x=1, y=2)
    # A NamedTuple is a tuple subclass but its constructor does not accept
    # a single iterable, so it is treated like a set: kept as a leaf value,
    # not copied
    config = audeer.load_configuration(default_file, {"position": point})
    assert config == {"name": "default", "position": point}


def test_load_configuration_user_mapping_two_mappings(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "name: default\n",
    )
    user_config_1 = {"model": {"device": "cpu"}}
    user_config_2 = {"model": {"lora": True}}
    # Two mappings are deep-merged with each other,
    # and merging the second one
    # does not modify the first one
    config = audeer.load_configuration(default_file, [user_config_1, user_config_2])
    assert config == {
        "name": "default",
        "model": {"device": "cpu", "lora": True},
    }
    assert user_config_1 == {"model": {"device": "cpu"}}


def test_load_configuration_user_mapping_not_modified(tmpdir, monkeypatch):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "name: default\n",
    )
    # The section is present in the mapping only,
    # so it would become part of the configuration by reference,
    # if it was not copied
    user_config = {"model": {"device": "cpu", "lora": False}}
    # The mapping given by the caller is not modified,
    # not even by the environment overrides applied afterwards
    monkeypatch.setenv("PKG_MODEL__DEVICE", "mps")
    config = audeer.load_configuration(default_file, user_config, env_prefix="PKG")
    assert config == {
        "name": "default",
        "model": {"device": "mps", "lora": False},
    }
    assert user_config == {"model": {"device": "cpu", "lora": False}}

    # The returned configuration is not aliased to the mapping either
    user_config["model"]["device"] = "xpu"
    assert config["model"]["device"] == "mps"


def test_load_configuration_user_mapping_environment(tmpdir, monkeypatch):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "name: default\n",
    )
    user_config = {"count": 1, "model": {"device": "cpu"}}
    # A key introduced by the mapping can be overridden
    # by an environment variable,
    # also with the nested '__' form,
    # and is cast to the type of the mapping's value
    monkeypatch.setenv("PKG_COUNT", "5")
    monkeypatch.setenv("PKG_MODEL__DEVICE", "cuda")
    config = audeer.load_configuration(default_file, user_config, env_prefix="PKG")
    assert config == {
        "name": "default",
        "count": 5,
        "model": {"device": "cuda"},
    }
    assert isinstance(config["count"], int)


def test_load_configuration_user_mapping_environment_json(tmpdir, monkeypatch):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "name: default\n",
    )
    user_config = {"model": {"device": "cpu"}}
    # A section introduced by the mapping
    # can be replaced by a JSON environment variable,
    # and the values of the mapping provide the types for it
    monkeypatch.setenv("PKG_MODEL", '{"device": "cuda"}')
    config = audeer.load_configuration(default_file, user_config, env_prefix="PKG")
    assert config == {"name": "default", "model": {"device": "cuda"}}
    monkeypatch.setenv("PKG_MODEL", '{"device": 5}')
    with pytest.raises(ValueError, match="has type 'str'"):
        audeer.load_configuration(default_file, user_config, env_prefix="PKG")


def test_load_configuration_user_mapping_types(tmpdir, monkeypatch):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "name: default\n",
    )
    user_config = {"timeout": None}
    # ``types`` is validated after merging,
    # so it may declare a key that only the mapping introduced
    monkeypatch.setenv("PKG_TIMEOUT", "2.5")
    config = audeer.load_configuration(
        default_file,
        user_config,
        env_prefix="PKG",
        types={"timeout": float},
    )
    assert config == {"name": "default", "timeout": 2.5}


def test_load_configuration_user_mapping_immutable(tmpdir, monkeypatch):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "name: default\n",
    )
    user_config = MappingProxyType(
        {"model": MappingProxyType({"device": "cpu", "lora": False})},
    )
    # Any mapping is accepted, not only a dictionary.
    # It is copied into plain dictionaries,
    # so a nested section can still be overridden
    # by an environment variable
    monkeypatch.setenv("PKG_MODEL__DEVICE", "cuda")
    config = audeer.load_configuration(default_file, user_config, env_prefix="PKG")
    assert config == {
        "name": "default",
        "model": {"device": "cuda", "lora": False},
    }


def test_load_configuration_user_mapping_shared_file(tmpdir, monkeypatch):
    default_file_a = write_config(
        audeer.path(tmpdir, "default_a.yaml"),
        "cache_root: ~/cache-a\ntimeout: null\n",
    )
    default_file_b = write_config(
        audeer.path(tmpdir, "default_b.yaml"),
        "cache_root: ~/cache-b\n",
    )
    shared_file = write_config(
        audeer.path(tmpdir, "shared.yaml"),
        "lib-a:\n  cache_root: ~/shared-a\nlib-b:\n  cache_root: ~/shared-b\n",
    )
    with open(shared_file) as fp:
        data = yaml.load(fp, Loader=yaml.SafeLoader)
    # An application parses a shared configuration file itself
    # and hands each section to the package that owns it,
    # every package keeping its own defaults, prefix and types
    monkeypatch.setenv("LIB_A_TIMEOUT", "2.5")
    monkeypatch.setenv("LIB_B_CACHE_ROOT", "~/env-b")
    config_a = audeer.load_configuration(
        default_file_a,
        data["lib-a"],
        env_prefix="LIB_A",
        types={"timeout": float},
    )
    config_b = audeer.load_configuration(
        default_file_b,
        data["lib-b"],
        env_prefix="LIB_B",
    )
    assert config_a == {"cache_root": "~/shared-a", "timeout": 2.5}
    assert config_b == {"cache_root": "~/env-b"}
    assert data == {
        "lib-a": {"cache_root": "~/shared-a"},
        "lib-b": {"cache_root": "~/shared-b"},
    }


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


def test_load_configuration_environment_whole_dict_null_for_typed_default(
    tmpdir, monkeypatch
):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n",
    )
    # JSON null does not match the str type of the default
    monkeypatch.setenv("PKG_MODEL", '{"device": null}')
    with pytest.raises(ValueError, match="has type 'str'"):
        audeer.load_configuration(config_file, env_prefix="PKG")


def test_load_configuration_environment_whole_dict_null_for_none_default(
    tmpdir, monkeypatch
):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: null\n",
    )
    # A None default accepts any JSON value, including null
    monkeypatch.setenv("PKG_MODEL", '{"device": null}')
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"device": None}}


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


def test_load_configuration_environment_whole_dict_introduced_section_then_nested(
    tmpdir, monkeypatch
):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n",
    )
    # A section introduced by the JSON object behaves like any section:
    # nested variables are applied on top of it
    monkeypatch.setenv("PKG_MODEL", '{"device": "cuda", "sub": {"a": 1}}')
    monkeypatch.setenv("PKG_MODEL__SUB__A", "2")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"model": {"device": "cuda", "sub": {"a": 2}}}


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


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("Yes", True),
        ("on", True),
        ("0", False),
        ("off", False),
        ("false", False),
        ("", False),
        ("no", False),
    ],
)
def test_load_configuration_environment_bool_values(
    tmpdir, monkeypatch, value, expected
):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        f"enabled: {str(not expected).lower()}\n",
    )
    # The truthy values are matched case insensitively,
    # any other value becomes False
    monkeypatch.setenv("PKG_ENABLED", value)
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"enabled": expected}


def test_load_configuration_environment_empty_string(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "name: default\ncount: 1\n",
    )
    # An empty string is a legal value for a str default
    monkeypatch.setenv("PKG_NAME", "")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"name": "", "count": 1}

    # But it cannot be cast to an int default
    monkeypatch.setenv("PKG_COUNT", "")
    with pytest.raises(ValueError, match="could not be converted to the type"):
        audeer.load_configuration(config_file, env_prefix="PKG")


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


def test_load_configuration_environment_types_none_default_list(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "hosts: null\n",
    )
    monkeypatch.setenv("PKG_HOSTS", '["host1", "host2"]')
    # A declared ``list`` type parses the value as JSON
    config = audeer.load_configuration(
        config_file,
        env_prefix="PKG",
        types={"hosts": list},
    )
    assert config == {"hosts": ["host1", "host2"]}


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


def test_load_configuration_tracking_omitted(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    # Without ``tracking``, the return value is the plain configuration
    # dictionary, exactly as before the feature existed
    config = audeer.load_configuration(default_file)
    assert config == {"cache_root": "~/cache"}
    assert type(config) is dict


def test_load_configuration_tracking_none(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    # ``tracking=None`` is explicitly the same as omitting it:
    # a structural no-op, not "compute it and throw it away"
    config = audeer.load_configuration(default_file, tracking=None)
    assert config == {"cache_root": "~/cache"}
    assert type(config) is dict


def test_load_configuration_tracking_not_a_mutable_mapping(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    # ``tracking`` must be a mutable mapping, like ``types`` must be a mapping
    with pytest.raises(ValueError, match="must be a mutable mapping"):
        audeer.load_configuration(default_file, tracking="not-a-mapping")


def test_load_configuration_tracking_user_dict(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    # A ``MutableMapping`` that is not a ``dict`` subclass is accepted too
    tracking = UserDict()
    config = audeer.load_configuration(default_file, tracking=tracking)
    assert config == {"cache_root": "~/cache"}
    assert dict(tracking) == {"cache_root": f"file:{default_file}"}


def test_load_configuration_tracking_default_only_key(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    tracking = {}
    config = audeer.load_configuration(default_file, tracking=tracking)
    # A key that no later layer touches is attributed to the default file
    assert config == {"cache_root": "~/cache"}
    assert tracking == {"cache_root": f"file:{default_file}"}


def test_load_configuration_tracking_user_file(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\nshared: /data\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "cache_root: ~/user\n",
    )
    tracking = {}
    config = audeer.load_configuration(default_file, user_file, tracking=tracking)
    # A user config file is labeled by its own path,
    # the untouched key stays attributed to the default file's path
    assert config == {"cache_root": "~/user", "shared": "/data"}
    assert tracking == {
        "cache_root": f"file:{user_file}",
        "shared": f"file:{default_file}",
    }


def test_load_configuration_tracking_user_mapping(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cuda\n  lora: false\n",
    )
    tracking = {}
    config = audeer.load_configuration(
        default_file,
        {"model": {"device": "cpu"}},
        tracking=tracking,
    )
    # A mapping in ``user_configs`` is labeled by its index in the
    # (normalized) sequence; deep-merged keys keep their own attribution
    assert config == {"model": {"device": "cpu", "lora": False}}
    assert tracking == {
        "model": {"device": "mapping[0]", "lora": f"file:{default_file}"},
    }


def test_load_configuration_tracking_user_configs_mixed_sequence(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "cache_root: ~/user\n",
    )
    tracking = {}
    config = audeer.load_configuration(
        default_file,
        [user_file, {"cache_root": "~/mapping"}],
        tracking=tracking,
    )
    # The mapping's index reflects its position in the sequence,
    # not the count of mapping entries alone
    assert config == {"cache_root": "~/mapping"}
    assert tracking == {"cache_root": "mapping[1]"}


def test_load_configuration_tracking_environment_scalar(tmpdir, monkeypatch):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n  lora: false\n",
    )
    monkeypatch.setenv("PKG_MODEL__DEVICE", "cuda")
    tracking = {}
    config = audeer.load_configuration(
        default_file, env_prefix="PKG", tracking=tracking
    )
    # A scalar environment override is labeled by the exact variable name
    assert config == {"model": {"device": "cuda", "lora": False}}
    assert tracking == {
        "model": {"device": "env:PKG_MODEL__DEVICE", "lora": f"file:{default_file}"},
    }


def test_load_configuration_tracking_environment_whole_dict(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n  lora: false\n",
    )
    monkeypatch.setenv("PKG_MODEL", '{"device": "cuda", "lora": true}')
    tracking = {}
    config = audeer.load_configuration(config_file, env_prefix="PKG", tracking=tracking)
    # A whole-section JSON replace attributes every leaf it sets
    # to the one variable that replaced the section
    assert config == {"model": {"device": "cuda", "lora": True}}
    assert tracking == {
        "model": {"device": "env:PKG_MODEL", "lora": "env:PKG_MODEL"},
    }


def test_load_configuration_tracking_environment_whole_dict_then_nested(
    tmpdir, monkeypatch
):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n  lora: false\n",
    )
    # The whole-section variable sets both keys, then a more specific
    # nested variable overrides just "device" afterwards
    monkeypatch.setenv("PKG_MODEL", '{"device": "cuda", "lora": true}')
    monkeypatch.setenv("PKG_MODEL__DEVICE", "mps")
    tracking = {}
    config = audeer.load_configuration(config_file, env_prefix="PKG", tracking=tracking)
    assert config == {"model": {"device": "mps", "lora": True}}
    # "device" is re-attributed to the more specific variable,
    # "lora" (untouched by it) stays attributed to the section variable
    assert tracking == {
        "model": {"device": "env:PKG_MODEL__DEVICE", "lora": "env:PKG_MODEL"},
    }


def test_load_configuration_tracking_accumulates_across_calls(tmpdir, monkeypatch):
    default_file_a = write_config(
        audeer.path(tmpdir, "default_a.yaml"),
        "cache_root: ~/cache-a\ntimeout: null\n",
    )
    default_file_b = write_config(
        audeer.path(tmpdir, "default_b.yaml"),
        "pool_size: 4\n",
    )
    monkeypatch.setenv("LIB_A_TIMEOUT", "2.5")
    monkeypatch.setenv("LIB_B_POOL_SIZE", "8")
    tracking = {}
    # Two independent calls sharing the same ``tracking`` dict:
    # like ``dict.update()``, entries from both calls are kept,
    # the second call does not wipe out the first
    config_a = audeer.load_configuration(
        default_file_a,
        env_prefix="LIB_A",
        types={"timeout": float},
        tracking=tracking,
    )
    config_b = audeer.load_configuration(
        default_file_b,
        env_prefix="LIB_B",
        tracking=tracking,
    )
    assert config_a == {"cache_root": "~/cache-a", "timeout": 2.5}
    assert config_b == {"pool_size": 8}
    assert tracking == {
        "cache_root": f"file:{default_file_a}",
        "timeout": "env:LIB_A_TIMEOUT",
        "pool_size": "env:LIB_B_POOL_SIZE",
    }


def test_load_configuration_tracking_types_none_default_environment(
    tmpdir, monkeypatch
):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "timeout: null\n",
    )
    monkeypatch.setenv("PKG_TIMEOUT", "2.5")
    tracking = {}
    # A key declared in ``types`` because its default is ``None``
    # is still attributed to the environment variable that overrides it
    config = audeer.load_configuration(
        default_file,
        env_prefix="PKG",
        types={"timeout": float},
        tracking=tracking,
    )
    assert config == {"timeout": 2.5}
    assert tracking == {"timeout": "env:PKG_TIMEOUT"}


def test_load_configuration_tracking_environment_declared_dict_then_nested(
    tmpdir, monkeypatch
):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model: null\n",
    )
    # A None default declared as ``dict`` is introduced by one variable,
    # then refined by a nested one, exactly like without tracking;
    # both are attributed to the variable that actually set them
    monkeypatch.setenv("PKG_MODEL", '{"device": "cpu", "batch": 8}')
    monkeypatch.setenv("PKG_MODEL__DEVICE", "cuda")
    tracking = {}
    config = audeer.load_configuration(
        config_file,
        env_prefix="PKG",
        types={"model": dict},
        tracking=tracking,
    )
    assert config == {"model": {"device": "cuda", "batch": 8}}
    assert tracking == {
        "model": {"device": "env:PKG_MODEL__DEVICE", "batch": "env:PKG_MODEL"},
    }


def test_load_configuration_tracking_does_not_affect_cfg(tmpdir, monkeypatch):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cpu\n  lora: false\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "model:\n  lora: true\n",
    )
    monkeypatch.setenv("PKG_MODEL__DEVICE", "cuda")
    # The exact same call, once with tracking, once without,
    # must produce an identical configuration:
    # ``tracking`` is a pure side channel
    config_without = audeer.load_configuration(
        default_file, user_file, env_prefix="PKG"
    )
    config_with = audeer.load_configuration(
        default_file, user_file, env_prefix="PKG", tracking={}
    )
    assert config_without == config_with


def test_load_configuration_tracking_untouched_on_error(tmpdir, monkeypatch):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\ntimeout: null\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "cache_root: ~/user\n",
    )
    monkeypatch.setenv("PKG_TIMEOUT", "not-a-number")
    tracking = {"preexisting": "sentinel"}
    # By the time the environment override raises, the internal tracking
    # tree already holds real entries built from the default file and
    # ``user_file``. None of that leaks into the caller's ``tracking``
    # mapping: it is only ever updated once, as the very last step, after
    # every other step succeeded
    with pytest.raises(ValueError, match="could not be converted"):
        audeer.load_configuration(
            default_file,
            user_file,
            env_prefix="PKG",
            types={"timeout": float},
            tracking=tracking,
        )
    assert tracking == {"preexisting": "sentinel"}


def test_load_configuration_tracking_key_overridden_by_every_layer(tmpdir, monkeypatch):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\nshared: /data\ntimeout: 1\n",
    )
    user_file = write_config(
        audeer.path(tmpdir, "user.yaml"),
        "shared: /user-data\ntimeout: 2\n",
    )
    monkeypatch.setenv("PKG_TIMEOUT", "3")
    tracking = {}
    config = audeer.load_configuration(
        default_file, user_file, env_prefix="PKG", tracking=tracking
    )
    # "cache_root" is set only by the default file, "shared" is overridden
    # once (by the user file), and "timeout" is overridden by every layer
    # in turn: tracking must show the outermost layer that actually
    # touched each key, not an intermediate one
    assert config == {"cache_root": "~/cache", "shared": "/user-data", "timeout": 3}
    assert tracking == {
        "cache_root": f"file:{default_file}",
        "shared": f"file:{user_file}",
        "timeout": "env:PKG_TIMEOUT",
    }


def test_load_configuration_tracking_merge_into_freshly_introduced_section(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    tracking = {}
    config = audeer.load_configuration(
        default_file,
        [{"tts": {"vendor": "iva-tts"}}, {"tts": {"region": "eu"}}],
        tracking=tracking,
    )
    # The default file has no "tts" section at all: the first mapping
    # entry introduces it fresh, and the second entry deep-merges an
    # additional key into that same section. At that point owner["tts"]
    # was set by the first entry's iteration, not by the initial tracking
    # tree built from the default file
    assert config == {
        "cache_root": "~/cache",
        "tts": {"vendor": "iva-tts", "region": "eu"},
    }
    assert tracking == {
        "cache_root": f"file:{default_file}",
        "tts": {"vendor": "mapping[0]", "region": "mapping[1]"},
    }


def test_load_configuration_tracking_section_collapsed_to_scalar(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  device: cuda\n  lora: false\n",
    )
    tracking = {}
    config = audeer.load_configuration(
        default_file,
        {"model": "none"},
        tracking=tracking,
    )
    # A scalar in a later layer replaces a whole default section wholesale:
    # the previously nested per-leaf attribution ("device", "lora") must
    # collapse into a single flat label for "model", not leave stale
    # nested entries behind
    assert config == {"model": "none"}
    assert tracking == {"model": "mapping[0]"}


def test_load_configuration_tracking_three_levels_deep(tmpdir, monkeypatch):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "model:\n  gpu:\n    device: cuda\n    memory: 8\n",
    )
    monkeypatch.setenv("PKG_MODEL__GPU__DEVICE", "mps")
    tracking = {}
    config = audeer.load_configuration(
        default_file, env_prefix="PKG", tracking=tracking
    )
    # Every existing nested test stops at one level (e.g. "model.device").
    # This checks the recursion through _label_tree(), _deep_merge(), and
    # _override_with_environment() actually holds three levels deep: the
    # overridden leaf is attributed to its variable, the untouched sibling
    # at the same depth keeps its "file:" label
    assert config == {"model": {"gpu": {"device": "mps", "memory": 8}}}
    assert tracking == {
        "model": {
            "gpu": {
                "device": "env:PKG_MODEL__GPU__DEVICE",
                "memory": f"file:{default_file}",
            },
        },
    }


def test_load_configuration_tracking_multiple_mapping_entries(tmpdir):
    default_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "cache_root: ~/cache\n",
    )
    tracking = {}
    config = audeer.load_configuration(
        default_file,
        [{"a": 1}, {"b": 2}, {"c": 3}],
        tracking=tracking,
    )
    # Three mapping-only entries, no file mixed in: each index must be
    # counted by sequence position, not just "some mapping touched it"
    assert config == {"cache_root": "~/cache", "a": 1, "b": 2, "c": 3}
    assert tracking == {
        "cache_root": f"file:{default_file}",
        "a": "mapping[0]",
        "b": "mapping[1]",
        "c": "mapping[2]",
    }


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


def test_load_configuration_validate_passes_with_environment(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "count: 1\n",
    )
    monkeypatch.setenv("PKG_COUNT", "5")
    calls = []

    def validate(config):
        # Snapshot: load_configuration() mutates and returns this very object
        calls.append(dict(config))

    config = audeer.load_configuration(
        config_file,
        env_prefix="PKG",
        validate=validate,
    )
    # validate() received the configuration
    # after environment variables were applied,
    # and the configuration is returned unchanged
    assert calls == [{"count": 5}]
    assert config == {"count": 5}
