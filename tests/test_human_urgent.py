import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

from human import Human

NAMES = {"left": "a", "right": "d", "cw": "w", "ccw": "q"}
PRESSES = [("d", "move", 20, False), ("w", "rot", 20, False), ("x", "drop", 20, False)]


def move(height=2, keys=("R", "CW")):
    return SimpleNamespace(piece="T", after=[1] * height, keys=list(keys))


def settled(**cfg):
    h = Human(dict({"seed": 5, "pps": 3.5, "opening_idle_s": 0.0}, **cfg))
    h.last_plan = 0.0
    return h


class UrgentTest(unittest.TestCase):
    def test_pressure_or_tall_stack_is_urgent(self):
        h = settled()
        self.assertFalse(h.urgent(move(5)))
        self.assertTrue(h.urgent(move(12)))
        h.pressure = 2
        self.assertTrue(h.urgent(move(1)))

    def test_urgent_plans_have_no_extras_or_pauses(self):
        h = settled(pause_chance=1.0, fidget_chance=1.0, hesitate_chance=1.0, fall_chance=1.0)
        h.pressure = 3
        for _ in range(100):
            h.last_plan = 1e12
            h.plan(move(), PRESSES, NAMES, 20)
            self.assertEqual(h.note, "")
            self.assertEqual(h.fall, 0)

    def test_calm_plans_can_have_extras(self):
        h = settled(pause_chance=1.0)
        h.last_plan = 1e12
        h.plan(move(), PRESSES, NAMES, 20)
        self.assertIn("pause", h.note)

    def test_urgent_thinks_faster(self):
        calm, hurried = settled(), settled()
        hurried.pressure = 1
        a = sum(calm.think(move(9)) for _ in range(300))
        b = sum(hurried.think(move(9)) for _ in range(300))
        self.assertLess(b, a)

    def test_complex_moves_take_longer(self):
        h1, h2 = settled(), settled()
        short = sum(h1.think(move(keys=())) for _ in range(300))
        long = sum(h2.think(move(keys=("R",) * 6)) for _ in range(300))
        self.assertGreater(long, short)

    def test_opening_beat_only_after_idle(self):
        h = Human({"seed": 1, "opening_idle_s": 4.0})
        self.assertGreater(h.opening(), 0.0)
        self.assertEqual(h.opening(), 0.0)


if __name__ == "__main__":
    unittest.main()
