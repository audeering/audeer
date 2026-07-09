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


def test_load_configuration_environment_bool_false(tmpdir, monkeypatch):
    config_file = write_config(
        audeer.path(tmpdir, "default.yaml"),
        "enabled: true\n",
    )
    monkeypatch.setenv("PKG_ENABLED", "no")
    config = audeer.load_configuration(config_file, env_prefix="PKG")
    assert config == {"enabled": False}


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
