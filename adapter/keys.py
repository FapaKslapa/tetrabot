import time

import backends

KEY_ACTIONS = {"L": "left", "R": "right", "CW": "cw", "CCW": "ccw", "SD": "soft_drop"}


class Keys:
    def __init__(self, settings, dry, human=None):
        self.keys = settings["keys"]
        self.timing = settings["timing"]
        self.dry = dry
        self.human = human
        self.planned_ms = None
        self.probe = None
        self.note = ""
        self.pressure = 0
        self.backend = None if dry else backends.load()

    def post(self, name, down):
        self.backend.press(name, down)

    def tap(self, name, hold_ms=None):
        if self.dry:
            return
        base = hold_ms or self.timing["tap_ms"]
        down = base / 1000.0
        gap = self.timing["gap_ms"] / 1000.0
        self.post(name, True)
        time.sleep(down)
        self.post(name, False)
        time.sleep(gap)

    def pause(self, seconds):
        if seconds > 0 and not self.dry:
            time.sleep(seconds)

    def run_human(self, move):
        human = self.human
        human.pressure = self.pressure
        presses = []
        if move.use_hold:
            presses.append((self.keys["hold"], "hold", self.timing["tap_ms"], False))
        for code in move.keys:
            action = KEY_ACTIONS.get(code)
            if action == "soft_drop":
                presses.append((self.keys[action], "soft", self.timing["soft_drop_ms"], False))
            elif action in ("cw", "ccw"):
                presses.append((self.keys[action], "rot", self.timing["tap_ms"], False))
            elif action:
                presses.append((self.keys[action], "move", self.timing["tap_ms"], False))
        presses.append((self.keys["hard_drop"], "drop", self.timing["tap_ms"], False))
        names = {name: self.keys[name] for name in ("left", "right", "cw", "ccw")}
        events, total = human.plan(move, presses, names, self.timing["tap_ms"])
        self.planned_ms = total * 1000.0
        self.note = human.note
        if self.dry:
            human.settle(total)
            return
        began = time.perf_counter()
        if human.fall and self.probe:
            if human.cfg["descend"]:
                key = self.keys["soft_drop"]
                self.post(key, True)
                try:
                    seen = self.probe(human.fall, min(human.cfg["fall_max_ms"], 300) / 1000.0)
                finally:
                    self.post(key, False)
                time.sleep(0.012)
            else:
                seen = self.probe(human.fall, human.cfg["fall_max_ms"] / 1000.0)
            human.fell(seen)
            self.note += " no-drop-seen" if seen is None else " fell-in-%dms" % seen
        start = time.perf_counter()
        for moment, key, down in events:
            wait = start + moment - time.perf_counter()
            if wait > 0.002:
                time.sleep(wait - 0.0015)
            while time.perf_counter() < start + moment:
                pass
            self.post(key, down)
        human.settle(time.perf_counter() - began)

    def run(self, move):
        if self.human:
            return self.run_human(move)
        if move.use_hold:
            self.tap(self.keys["hold"])
        for code in move.keys:
            action = KEY_ACTIONS.get(code)
            if action == "soft_drop":
                self.tap(self.keys[action], self.timing["soft_drop_ms"])
            elif action:
                self.tap(self.keys[action])
        self.tap(self.keys["hard_drop"])
