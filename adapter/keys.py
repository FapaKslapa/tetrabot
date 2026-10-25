import time

import backends

KEY_ACTIONS = {"L": "left", "R": "right", "CW": "cw", "CCW": "ccw", "SD": "soft_drop"}


class Keys:
    def __init__(self, settings, dry):
        self.keys = settings["keys"]
        self.timing = settings["timing"]
        self.dry = dry
        self.backend = None if dry else backends.load()

    def post(self, name, down):
        self.backend.press(name, down)

    def tap(self, name, hold_ms=None):
        if self.dry:
            return
        self.post(name, True)
        time.sleep((hold_ms or self.timing["tap_ms"]) / 1000.0)
        self.post(name, False)
        time.sleep(self.timing["gap_ms"] / 1000.0)

    def run(self, move):
        if move.use_hold:
            self.tap(self.keys["hold"])
        for code in move.keys:
            action = KEY_ACTIONS.get(code)
            if action == "soft_drop":
                self.tap(self.keys[action], self.timing["soft_drop_ms"])
            elif action:
                self.tap(self.keys[action])
        self.tap(self.keys["hard_drop"])
