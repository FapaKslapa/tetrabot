import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

from human import Human, stack_height


def move(piece="T", rows=None):
    return SimpleNamespace(piece=piece, after=rows if rows is not None else [0b1111, 0b11])


def net_rotation(codes):
    return sum({"CW": 1, "CCW": -1}.get(c, 0) for c in codes) % 4


class HumanTest(unittest.TestCase):
    def test_stack_height(self):
        self.assertEqual(stack_height([1, 1, 0, 0]), 2)
        self.assertEqual(stack_height([0, 0]), 0)

    def test_think_within_bounds(self):
        h = Human({"seed": 1})
        for _ in range(500):
            self.assertTrue(0.02 <= h.think(move()) <= 0.45)

    def test_fidget_cancels_out_and_respects_height(self):
        h = Human({"seed": 2, "fidget_chance": 1.0})
        for _ in range(100):
            self.assertEqual(net_rotation(h.fidget(move())), 0)
        self.assertEqual(h.fidget(move("O")), [])
        self.assertEqual(h.fidget(move(rows=[1] * 15)), [])

    def test_seed_is_reproducible(self):
        a, b = Human({"seed": 7}), Human({"seed": 7})
        self.assertEqual([a.think(move()) for _ in range(20)], [b.think(move()) for _ in range(20)])

    def test_default_has_no_effect_without_flag(self):
        import keys
        k = keys.Keys({"keys": {}, "timing": {"tap_ms": 20, "gap_ms": 8, "soft_drop_ms": 70}}, True)
        self.assertIsNone(k.human)


if __name__ == "__main__":
    unittest.main()


class TimingTest(unittest.TestCase):
    def test_taps_follow_settings(self):
        h = Human({"seed": 3}, {"tap_ms": 16, "gap_ms": 6})
        for _ in range(300):
            self.assertTrue(0.016 * 0.85 <= h.tap(16) <= 0.0256 * 1.25 + 1e-9)
            self.assertTrue(0.0 < h.gap() <= 0.015 * 1.15 + 1e-9)

    def test_soft_drop_stays_near_base(self):
        h = Human({"seed": 4}, {"tap_ms": 16, "gap_ms": 6})
        for _ in range(300):
            self.assertTrue(0.055 * 0.85 <= h.tap(55, True) <= 0.055 * 1.4 * 1.25 + 1e-9)


class PlanTest(unittest.TestCase):
    PRESSES = [("up", "rot", 16, True), ("z", "rot", 16, True)] + \
              [("right", "move", 16, False)] * 4 + [("up", "rot", 16, False), ("down", "soft", 55, False),
                                                    ("space", "drop", 16, False)]

    def plan(self, pps, seed=5):
        h = Human({"seed": seed, "pps": pps}, {"tap_ms": 16, "gap_ms": 6})
        return h.plan(move(), self.PRESSES)

    def test_sequential_without_pps(self):
        events, total = self.plan(None)
        downs = [e for e in events if e[2]]
        self.assertEqual(len(downs), len(self.PRESSES))
        self.assertEqual(sorted(events), events)

    def test_pps_fits_budget_and_is_faster(self):
        _, slow = self.plan(None)
        events, fast = self.plan(3.75)
        self.assertLess(fast, slow)
        self.assertLessEqual(fast, 1 / 3.75 - 0.055 + 1e-9)

    def test_same_key_never_overlaps_and_moves_do_not_mix(self):
        for seed in range(30):
            events, _ = self.plan(4.0, seed)
            held = set()
            for _, key, down in events:
                if down:
                    self.assertNotIn(key, held)
                    held.add(key)
                else:
                    held.discard(key)
                self.assertFalse({"right", "down"} <= held)

    def test_average_pace_hits_target_but_varies(self):
        import random
        import statistics
        rng = random.Random(1)
        names = {"left": "left", "right": "right", "cw": "up", "ccw": "z"}
        h = Human({"seed": 6, "pps": 3.75}, {"tap_ms": 16, "gap_ms": 6})
        cycles, notes = [], set()
        for _ in range(1500):
            presses = [("right", "move", 16, False)] * rng.choice([0, 1, 2, 3, 4]) + \
                      [("up", "rot", 16, False)] * rng.choice([0, 1, 2]) + [("space", "drop", 16, False)]
            _, total = h.plan(move(rng.choice("TSZLJIO")), presses, names, 16)
            h.settle(total)
            cycles.append(total + 0.055)
            notes.add(h.note)
        pps = 1 / statistics.mean(cycles)
        self.assertTrue(3.5 <= pps <= 4.0, pps)
        self.assertGreater(statistics.pstdev(cycles), 0.06)
        self.assertTrue({"pause", "fidget", "regret"} <= notes)

    def test_regret_cancels_out(self):
        names = {"left": "left", "right": "right", "cw": "up", "ccw": "z"}
        h = Human({"seed": 8, "pps": 3.75, "fidget_chance": 0.0, "regret_chance": 1.0}, {"tap_ms": 16, "gap_ms": 6})
        for _ in range(100):
            events, _ = h.plan(move(), [("space", "drop", 16, False)], names, 16)
            net = sum((1 if k == "right" else -1) for _, k, d in events if d and k in ("left", "right"))
            self.assertEqual(net, 0)


class FallTest(unittest.TestCase):
    names = {"left": "left", "right": "right", "cw": "up", "ccw": "z"}

    def test_waits_for_fall_some_pieces_but_not_all(self):
        h = Human({"seed": 11, "pps": 3.75, "fall_chance": 0.6}, {"tap_ms": 16, "gap_ms": 6})
        falls = []
        for _ in range(400):
            h.plan(move(), [("space", "drop", 16, False)], self.names, 16)
            falls.append(h.fall)
        self.assertTrue(0.4 < sum(1 for f in falls if f) / len(falls) < 0.8)
        self.assertTrue(set(falls) <= {0, 1, 2})

    def test_no_fall_wait_on_tall_stack_or_without_pps(self):
        h = Human({"seed": 12, "pps": 3.75, "fall_chance": 1.0}, {"tap_ms": 16, "gap_ms": 6})
        h.plan(move(rows=[1] * 15), [("space", "drop", 16, False)], self.names, 16)
        self.assertEqual(h.fall, 0)
        g = Human({"seed": 12, "fall_chance": 1.0}, {"tap_ms": 16, "gap_ms": 6})
        g.plan(move(), [("space", "drop", 16, False)], self.names, 16)
        self.assertEqual(g.fall, 0)

    def test_slow_gravity_switches_waiting_off_then_retries(self):
        h = Human({"seed": 13, "pps": 3.75, "fall_chance": 1.0}, {"tap_ms": 16, "gap_ms": 6})
        h.fell(None)
        flags = []
        for _ in range(160):
            h.plan(move(), [("space", "drop", 16, False)], self.names, 16)
            flags.append(h.fall)
        self.assertEqual(flags[:149], [0] * 149)
        self.assertTrue(any(flags[149:]))
        h.fell(120.0)
        self.assertEqual(h.row_ms, 120.0)


class DescendTest(unittest.TestCase):
    def run_keys(self, descend, seen):
        import keys as keys_mod
        from types import SimpleNamespace
        events = []

        class Backend:
            def press(self, name, down):
                events.append((name, down))

        settings = {"keys": {"left": "left", "right": "right", "cw": "up", "ccw": "z", "hold": "c",
                             "hard_drop": "space", "soft_drop": "down"},
                    "timing": {"tap_ms": 16, "gap_ms": 6, "soft_drop_ms": 55}}
        human = Human({"seed": 3, "pps": 3.75, "fall_chance": 1.0, "descend": descend,
                       "fidget_chance": 0, "regret_chance": 0, "pause_chance": 0}, settings["timing"])
        k = keys_mod.Keys(settings, True, human)
        k.dry = False
        k.backend = Backend()
        k.probe = lambda rows, timeout: seen
        k.run(SimpleNamespace(piece="T", use_hold=False, keys=["R"], after=[1, 1]))
        return events, human

    def test_soft_drop_is_held_only_around_the_wait(self):
        events, _ = self.run_keys(True, 80.0)
        self.assertEqual(events[0], ("down", True))
        self.assertEqual(events[1], ("down", False))
        self.assertEqual([e for e in events[2:] if e[0] == "down"], [])
        self.assertEqual(events[-1], ("space", False))

    def test_released_even_when_nothing_seen(self):
        events, human = self.run_keys(True, None)
        self.assertEqual(events[:2], [("down", True), ("down", False)])
        self.assertGreater(human.row_ms, human.cfg["fall_max_ms"])

    def test_passive_wait_never_presses_down(self):
        events, _ = self.run_keys(False, 80.0)
        self.assertNotIn("down", [e[0] for e in events])
