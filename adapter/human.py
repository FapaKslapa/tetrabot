import math
import random
import time

from human_config import FIDGETS, HUMAN_DEFAULTS, STAGES, stack_height
from human_schedule import build_schedule


class Human:
    def __init__(self, config=None, timing=None):
        self.cfg = dict(HUMAN_DEFAULTS)
        if config:
            self.cfg.update({k: v for k, v in config.items() if k in HUMAN_DEFAULTS})
        timing = timing or {"tap_ms": 20, "gap_ms": 8}
        if not self.cfg["tap_ms"]:
            self.cfg["tap_ms"] = [timing["tap_ms"], timing["tap_ms"] * 1.6]
        if not self.cfg["gap_ms"]:
            self.cfg["gap_ms"] = [timing["gap_ms"], timing["gap_ms"] * 2.5]
        self.rng = random.Random(self.cfg["seed"])
        self.tempo = 1.0
        self.bank = 0.0
        self.note = ""
        self.fall = 0
        self.row_ms = None
        self.skipped = 0
        self.pressure = 0
        self.last_plan = None

    def urgent(self, move):
        return self.pressure > 0 or stack_height(move.after) >= self.cfg["urgent_height"]

    def drift(self):
        low, high = self.cfg["tempo_range"]
        self.tempo = min(high, max(low, self.tempo + self.rng.uniform(-0.04, 0.04)))

    def between(self, bounds):
        low, high = bounds
        return self.rng.uniform(low, high) * self.tempo / 1000.0

    def think(self, move):
        self.drift()
        cfg = self.cfg
        ms = cfg["think_median_ms"] * math.exp(self.rng.gauss(0, cfg["think_sigma"]))
        if self.urgent(move):
            ms *= 0.7
        else:
            ms *= 1 + cfg["height_factor"] * stack_height(move.after) / 20.0
            ms *= 1 + cfg["key_factor"] * min(len(getattr(move, "keys", ())), 8)
            if self.rng.random() < cfg["long_think_chance"]:
                ms += self.rng.uniform(*cfg["long_think_extra_ms"])
        ms = min(cfg["think_max_ms"], max(cfg["think_min_ms"], ms * self.tempo))
        return ms / 1000.0

    def opening(self):
        now = time.time()
        fresh = self.last_plan is None or now - self.last_plan > self.cfg["opening_idle_s"]
        self.last_plan = now
        return self.between(self.cfg["opening_ms"]) if fresh else 0.0

    def tap(self, base_ms, soft=False):
        if soft:
            return base_ms * self.rng.uniform(0.9, 1.4) * self.tempo / 1000.0
        return self.between(self.cfg["tap_ms"])

    def gap(self):
        return self.between(self.cfg["gap_ms"])

    def hesitation(self):
        if self.rng.random() < self.cfg["hesitate_chance"]:
            return self.between(self.cfg["hesitate_ms"])
        return 0.0

    def confirm(self):
        return self.between(self.cfg["confirm_ms"])

    def fidget(self, move):
        if move.piece == "O" or self.rng.random() >= self.cfg["fidget_chance"]:
            return []
        if stack_height(move.after) > self.cfg["fidget_max_height"]:
            return []
        return list(self.rng.choice(FIDGETS))

    def extras(self, move, names, base_ms):
        cfg = self.cfg
        if stack_height(move.after) > cfg["fidget_max_height"] or self.urgent(move):
            return [], ""
        roll = self.rng.random()
        if roll < cfg["fidget_chance"] and move.piece != "O":
            rename = {"CW": names["cw"], "CCW": names["ccw"]}
            return [(rename[c], "rot", base_ms, True, 0.0) for c in self.rng.choice(FIDGETS)], "fidget"
        if roll < cfg["fidget_chance"] + cfg["regret_chance"]:
            way, back = self.rng.choice([("left", "right"), ("right", "left")])
            count = self.rng.choice([1, 2, 2, 3])
            out = [(names[way], "move", base_ms, True, 0.0)] * count
            pause = self.between(cfg["regret_pause_ms"])
            out += [(names[back], "move", base_ms, True, pause if i == 0 else 0.0) for i in range(count)]
            return out, "regret"
        return [], ""

    def plan(self, move, presses, names=None, base_ms=20):
        cfg = self.cfg
        think = self.think(move)
        notes = []
        urgent = self.urgent(move)
        think += self.opening()
        if cfg["pps"] and not urgent and self.rng.random() < cfg["pause_chance"]:
            think += self.between(cfg["pause_ms"])
            notes.append("pause")
        self.fall = 0
        if (cfg["pps"] and not urgent and stack_height(move.after) <= cfg["fidget_max_height"] and self.fall_possible()
                and self.rng.random() < cfg["fall_chance"]):
            self.fall = 2 if self.rng.random() < 0.3 else 1
            notes.append("fall")
        extra, note = self.extras(move, names, base_ms) if names else ([], "")
        if note:
            notes.append(note)
        self.note = "+".join(notes)
        presses = list(presses)
        hold = [p for p in presses if p[1] == "hold"]
        presses = hold + extra + [p for p in presses if p[1] != "hold"]
        items = []
        for press in presses:
            key, kind, base, flag = press[:4]
            more = press[4] if len(press) > 4 else 0.0
            items.append({"key": key, "kind": kind, "extra": flag,
                          "down": self.tap(base, kind == "soft"), "gap": self.gap(),
                          "pre": more + (self.confirm() if kind == "drop" else 0.0 if urgent else self.hesitation())})
        budget = None
        if cfg["pps"]:
            base_budget = max(0.05, 1.0 / cfg["pps"] - cfg["pace_overhead_ms"] / 1000.0)
            nominal = base_budget * min(1.6, max(0.6, math.exp(self.rng.gauss(0, cfg["budget_sigma"]))))
            if [n for n in notes if n != "fall"]:
                budget = max(nominal, base_budget) * 2.5
            else:
                budget = min(1.6 * base_budget, max(0.55 * base_budget, nominal + 0.9 * self.bank))
        best = None
        for scale, overlap, shrink in STAGES:
            best = self.build(think, items, scale, overlap, shrink)
            if budget is None or best[1] <= budget:
                break
        return best

    def fall_possible(self):
        if self.row_ms is None or self.row_ms <= self.cfg["fall_max_ms"]:
            return True
        self.skipped += 1
        if self.skipped >= 150:
            self.row_ms, self.skipped = None, 0
        return False

    def fell(self, elapsed_ms):
        if elapsed_ms is None:
            self.row_ms = self.cfg["fall_max_ms"] * 2.0
        elif self.row_ms is None or self.row_ms > self.cfg["fall_max_ms"]:
            self.row_ms = elapsed_ms
        else:
            self.row_ms = 0.7 * self.row_ms + 0.3 * elapsed_ms
        self.skipped = 0

    def settle(self, actual):
        if self.cfg["pps"]:
            target = max(0.05, 1.0 / self.cfg["pps"] - self.cfg["pace_overhead_ms"] / 1000.0)
            self.bank = min(0.3, max(-0.5, self.bank + 0.93 * target - actual))

    def build(self, think, items, scale, overlap, shrink):
        return build_schedule(self.cfg, think, items, scale, overlap, shrink)
