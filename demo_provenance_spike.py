"""Tier-0 provenance spike demo.

Run with: uv run python demo.py   (from the audeer-provenance-spike checkout)

Exercises ALL layers at once:
  1. default config file
  2. user config file
  3. user config mapping
  4. scalar env override of a nested key      (PKG_MODEL__DEVICE)
  5. whole-section JSON env override          (PKG_FEATURES)
     ...with one nested key inside that section overridden afterwards too
     (PKG_FEATURES__RETRIES), to test the "JSON-replace-then-nested-
     override" interaction specifically.
"""

import json
import os
import tempfile

import yaml

import audeer
from audeer.core.config import _owner_of
from audeer.core.config import _resolve_provenance_spike  # noqa: F401 (used indirectly)


tmp = tempfile.mkdtemp()

default_file = audeer.path(tmp, "default.yaml")
with open(default_file, "w") as f:
    yaml.safe_dump(
        {
            "cache_root": "~/cache",
            "model": {
                "device": "cpu",
                "lora": False,
            },
            "features": {
                "enabled": True,
                "retries": 3,
                "timeout": 10,
            },
            "untouched": "default-only",
        },
        f,
    )

user_file = audeer.path(tmp, "user.yaml")
with open(user_file, "w") as f:
    yaml.safe_dump(
        {
            "model": {
                "lora": True,  # user file wins over default here
            },
        },
        f,
    )

user_mapping = {
    "cache_root": "/from/mapping",  # mapping wins over default here
}

# Env layer:
#  - PKG_MODEL__DEVICE: scalar override of a nested key -> should win over
#    everything for model.device
#  - PKG_FEATURES: whole-section JSON replace -> should become the owner of
#    features.enabled and features.timeout (features.retries is NOT in the
#    JSON payload... wait, JSON replace REPLACES the whole section, so
#    "timeout" would actually be DROPPED unless included. Let's include all
#    three keys in the JSON so the section is a full replacement, and then
#    override just "retries" afterwards via a more specific nested var.)
os.environ["PKG_MODEL__DEVICE"] = "cuda"
os.environ["PKG_FEATURES"] = json.dumps(
    {"enabled": False, "retries": 99, "timeout": 20}
)
os.environ["PKG_FEATURES__RETRIES"] = "7"

try:
    cfg, owner = audeer.load_configuration(
        default_file,
        [user_file, user_mapping],
        env_prefix="PKG",
        _provenance_spike=True,
    )
finally:
    del os.environ["PKG_MODEL__DEVICE"]
    del os.environ["PKG_FEATURES"]
    del os.environ["PKG_FEATURES__RETRIES"]

print("=== final cfg ===")
print(json.dumps(cfg, indent=2))

print()
print("=== owner tree (raw) ===")
print(json.dumps(owner, indent=2))

print()
print("=== per-key provenance verdicts ===")

checks = [
    # (path, expected label substring, human explanation of the expectation)
    (
        ("cache_root",),
        "mapping[1]",
        "user mapping is the last file/mapping layer to touch cache_root "
        "(default sets it, mapping overrides it; no env var for it)",
    ),
    (
        ("model", "lora"),
        "file:",
        "user file sets model.lora=True over the default's False; "
        "no env var touches model.lora",
    ),
    (
        ("model", "device"),
        "env:PKG_MODEL__DEVICE",
        "scalar env var overrides model.device, which beats every file/"
        "mapping layer (default only, in this case)",
    ),
    (
        ("features", "enabled"),
        "env:PKG_FEATURES",
        "whole-section JSON replace sets features.enabled=False; no "
        "more specific var overrides just 'enabled', so the section "
        "variable itself is the owner",
    ),
    (
        ("features", "timeout"),
        "env:PKG_FEATURES",
        "same section replace also owns features.timeout=20 (the default's 10 is gone)",
    ),
    (
        ("features", "retries"),
        "env:PKG_FEATURES__RETRIES",
        "PKG_FEATURES set retries=99 as part of the whole-section "
        "replace, but PKG_FEATURES__RETRIES is applied afterwards and "
        "overrides just this one leaf to 7 -- the resolver must not "
        "attribute retries to PKG_FEATURES anymore",
    ),
    (
        ("untouched",),
        "default:",
        "nothing overrides this key at any layer",
    ),
]

all_correct = True
for path, expected_substr, explanation in checks:
    label = _owner_of(owner, path)
    ok = label is not None and expected_substr in label
    all_correct = all_correct and ok
    verdict = "CORRECT" if ok else "WRONG !!"
    print(f"{'.'.join(path):30s} -> {label!r:35s} [{verdict}]  {explanation}")

print()
print("ALL CHECKS CORRECT" if all_correct else "SOME CHECKS FAILED")

print()
print("=== sanity: manually re-derive expected final cfg ===")
expected = {
    "cache_root": "/from/mapping",
    "model": {"device": "cuda", "lora": True},
    "features": {"enabled": False, "retries": 7, "timeout": 20},
    "untouched": "default-only",
}
print("matches expected:", cfg == expected)
