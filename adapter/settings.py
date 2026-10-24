import copy
import json

from palette import DEFAULT_PALETTE

DEFAULTS = {
    "palette": DEFAULT_PALETTE,
    "fill_threshold": 95,
    "keys": {
        "left": "left", "right": "right", "cw": "up", "ccw": "z",
        "hold": "c", "hard_drop": "space", "soft_drop": "down",
    },
    "timing": {"tap_ms": 20, "gap_ms": 8, "soft_drop_ms": 70, "spawn_timeout_ms": 1500},
    "search": {"depth": 6, "width": 120, "nosd": True},
}


def merge(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merge(base[key], value)
        else:
            base[key] = value
    return base


def load(path=None):
    settings = copy.deepcopy(DEFAULTS)
    if path:
        with open(path) as f:
            merge(settings, json.load(f))
    return settings
