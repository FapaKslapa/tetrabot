import time

KEYCODES = {"left": 123, "right": 124, "down": 125, "up": 126, "space": 49,
            "z": 6, "x": 7, "c": 8, "a": 0, "shift": 56}

KEY_ACTIONS = {"L": "left", "R": "right", "CW": "cw", "CCW": "ccw", "SD": "soft_drop"}


class Keys:
    def __init__(self, settings, dry):
        self.keys = settings["keys"]
        self.timing = settings["timing"]
        self.dry = dry
        self.quartz = None
        if not dry:
            import Quartz
            self.quartz = Quartz

    def post(self, name, down):
        event = self.quartz.CGEventCreateKeyboardEvent(None, KEYCODES[name], down)
        self.quartz.CGEventPost(self.quartz.kCGHIDEventTap, event)

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
