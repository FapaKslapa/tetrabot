HUMAN_DEFAULTS = {
    "think_median_ms": 70,
    "think_sigma": 0.45,
    "think_min_ms": 20,
    "think_max_ms": 450,
    "long_think_chance": 0.03,
    "long_think_extra_ms": [150, 350],
    "height_factor": 0.6,
    "tap_ms": None,
    "gap_ms": None,
    "hesitate_chance": 0.04,
    "hesitate_ms": [30, 100],
    "confirm_ms": [8, 50],
    "fidget_chance": 0.08,
    "fidget_max_height": 12,
    "tempo_range": [0.9, 1.15],
    "pps": None,
    "pause_chance": 0.10,
    "pause_ms": [150, 400],
    "regret_chance": 0.07,
    "regret_pause_ms": [90, 220],
    "fall_chance": 0.6,
    "fall_max_ms": 450,
    "descend": None,
    "budget_sigma": 0.35,
    "pace_overhead_ms": 55,
    "min_tap_ms": 17,
    "min_gap_ms": 5,
    "overlap_ratio": 0.5,
    "mistake_chance": 0.05,
    "urgent_height": 10,
    "form_tempo": 0.08,
    "form_chance": 0.5,
    "form_mistakes": 0.6,
    "key_factor": 0.04,
    "opening_ms": [180, 350],
    "opening_idle_s": 4.0,
    "seed": None,
}

STAGES = [(1.0, False, False), (1.0, True, False), (0.5, True, False), (0.25, True, False),
          (0.0, True, False), (0.0, True, True)]
MOVE_KINDS = ("move", "soft")

FIDGETS = (["CW", "CCW"], ["CCW", "CW"], ["CW", "CW", "CW", "CW"], ["CCW", "CCW", "CCW", "CCW"])


def stack_height(rows):
    height = 0
    for i, row in enumerate(rows):
        if row:
            height = i + 1
    return height
