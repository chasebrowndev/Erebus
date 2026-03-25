"""
config_loader.py — Erebus config loader.

Reads ~/.config/erebus/config.toml and deep-merges it over DEFAULTS.
Falls back to DEFAULTS silently if the file doesn't exist or has errors.

Usage:
    from config_loader import load_config
    config = load_config()  # always returns a fully-populated dict
"""

import os
import sys
import copy

# tomllib is stdlib in Python 3.11+; fall back to the backport for older versions
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from defaults import DEFAULTS

CONFIG_PATH = os.path.expanduser("~/.config/erebus/config.toml")


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge `override` into a copy of `base`.
    Keys in `override` win; nested dicts are merged, not replaced.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    """
    Load and return the resolved config.

    Priority (highest to lowest):
      1. User's ~/.config/erebus/config.toml
      2. DEFAULTS (defaults.py)

    Always returns a complete dict — never raises.
    """
    if tomllib is None:
        print("[erebus] WARNING: tomllib not available. Using defaults only.", file=sys.stderr)
        return copy.deepcopy(DEFAULTS)

    if not os.path.exists(CONFIG_PATH):
        print(f"[erebus] No config found at {CONFIG_PATH}. Using defaults.", file=sys.stderr)
        return copy.deepcopy(DEFAULTS)

    try:
        with open(CONFIG_PATH, "rb") as f:
            user_config = tomllib.load(f)
        merged = _deep_merge(DEFAULTS, user_config)
        print(f"[erebus] Config loaded from {CONFIG_PATH}", file=sys.stderr)
        return merged
    except Exception as e:
        print(f"[erebus] Config parse error: {e}. Using defaults.", file=sys.stderr)
        return copy.deepcopy(DEFAULTS)
