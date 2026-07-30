"""Tier-0 provenance spike demo.

Run with: uv run python demo_provenance_spike.py
(from the audeer-provenance-spike checkout)

Section 1 exercises ALL layers at once, via the agreed ``tracking=`` keyword
(see https://github.com/audeering/audeer/issues/197):
  1. default config file
  2. user config file
  3. user config mapping
  4. scalar env override of a nested key      (PKG_MODEL__DEVICE)
  5. whole-section JSON env override          (PKG_FEATURES)
     ...with one nested key inside that section overridden afterwards too
     (PKG_FEATURES__RETRIES), to test the "JSON-replace-then-nested-
     override" interaction specifically.

Section 2 demonstrates the two properties that make ``tracking`` behave like
``scipy.io.loadmat(..., mdict=...)``, the explicit precedent the reviewer
cited on the issue:
  - passing the SAME dict to two independent ``load_configuration()`` calls
    accumulates entries from both, rather than the second call wiping out
    the first;
  - omitting ``tracking`` (or passing ``None``) keeps the return value a
    plain ``cfg`` dict, never a tuple -- exactly as it is today.
"""

import json
import os
import tempfile

import yaml

import audeer
from audeer.core.config import _owner_of


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

owner_tree: dict = {}
try:
    cfg = audeer.load_configuration(
        default_file,
        [user_file, user_mapping],
        env_prefix="PKG",
        tracking=owner_tree,
    )
finally:
    del os.environ["PKG_MODEL__DEVICE"]
    del os.environ["PKG_FEATURES"]
    del os.environ["PKG_FEATURES__RETRIES"]

print("=== final cfg (a plain dict, same as without `tracking`) ===")
print(json.dumps(cfg, indent=2))

print()
print("=== owner tree, collected into the caller-supplied `tracking` dict ===")
print(json.dumps(owner_tree, indent=2))

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
    label = _owner_of(owner_tree, path)
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


# =====================================================================
# Section 2: `tracking` behaves like `scipy.io.loadmat(..., mdict=...)`
# =====================================================================

print()
print("=" * 72)
print(
    "=== accumulation: the SAME `tracking` dict reused across TWO "
    "independent load_configuration() calls ==="
)
print("=" * 72)

# Mirrors tests/test_config.py::test_load_configuration_user_mapping_shared_file:
# two "packages", each with its own default file and env prefix, called
# independently -- except here we deliberately pass the *same* `tracking`
# dict to both calls, instead of a fresh one each time.
lib_a_default = audeer.path(tmp, "lib_a_default.yaml")
with open(lib_a_default, "w") as f:
    yaml.safe_dump({"cache_root": "~/cache-a", "timeout": 5}, f)

lib_b_default = audeer.path(tmp, "lib_b_default.yaml")
with open(lib_b_default, "w") as f:
    yaml.safe_dump({"pool_size": 4, "retries": 1}, f)

os.environ["LIB_A_TIMEOUT"] = "9"
os.environ["LIB_B_POOL_SIZE"] = "8"

shared_tracking: dict = {}
try:
    cfg_a = audeer.load_configuration(
        lib_a_default,
        env_prefix="LIB_A",
        tracking=shared_tracking,
    )
    cfg_b = audeer.load_configuration(
        lib_b_default,
        env_prefix="LIB_B",
        tracking=shared_tracking,
    )
finally:
    del os.environ["LIB_A_TIMEOUT"]
    del os.environ["LIB_B_POOL_SIZE"]

print()
print("cfg_a:", cfg_a)
print("cfg_b:", cfg_b)
print()
print("shared `tracking` dict after BOTH calls:")
print(json.dumps(shared_tracking, indent=2))

expected_keys = {"cache_root", "timeout", "pool_size", "retries"}
accumulated = expected_keys.issubset(shared_tracking.keys())
print()
print(
    "entries from BOTH calls present (accumulation, not "
    "overwriting-from-scratch): " + ("CORRECT" if accumulated else "WRONG !!")
)

print()
print("=" * 72)
print("=== tracking=None (or omitted): return value is a plain dict ===")
print("=" * 72)

# No `tracking=` at all -- this is the path every existing caller takes.
cfg_plain = audeer.load_configuration(lib_a_default, env_prefix="LIB_A")
print()
print("cfg_plain:", cfg_plain)
print("type(cfg_plain).__name__:", type(cfg_plain).__name__)
print(
    "is a plain dict, not a tuple: "
    + str(isinstance(cfg_plain, dict) and not isinstance(cfg_plain, tuple))
)

# Same call, but explicit `tracking=None`, to show it is truly a no-op:
# identical return value, no bookkeeping performed.
cfg_explicit_none = audeer.load_configuration(
    lib_a_default, env_prefix="LIB_A", tracking=None
)
print()
print(
    "tracking=None explicitly gives the same plain dict: "
    + str(cfg_explicit_none == cfg_plain)
)
