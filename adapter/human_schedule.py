from human_config import MOVE_KINDS


def build_schedule(cfg, think, items, scale, overlap, shrink):
    min_gap = cfg["min_gap_ms"] / 1000.0
    events, held, prev, prev_up = [], [], None, think * scale
    for it in items:
        down = cfg["min_tap_ms"] / 1000.0 if shrink else it["down"]
        if prev is None:
            start = think * scale + it["pre"] * scale
        elif overlap:
            start = max(held[-1][0] + 0.004, prev_up - cfg["overlap_ratio"] * prev["_down"]) + it["pre"] * scale
        else:
            start = prev_up + max(min_gap, prev["gap"] * scale) + it["pre"] * scale
        for began, up, other in held:
            clash = other["key"] == it["key"] or (other["kind"] in MOVE_KINDS and it["kind"] in MOVE_KINDS)
            if clash and up + (min_gap if other["key"] == it["key"] else 0.0) > start:
                start = up + (min_gap if other["key"] == it["key"] else 0.0)
        it["_down"] = down
        events.append((start, it["key"], True))
        events.append((start + down, it["key"], False))
        held.append((start, start + down, it))
        prev, prev_up = it, max(prev_up, start + down)
    events.sort(key=lambda e: e[0])
    return events, prev_up
