import os
import statistics
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

from human import Human


def move(height=3):
    return SimpleNamespace(piece="T", after=[1] * height, keys=["R", "CW"])


class FormTest(unittest.TestCase):
    def test_form_wanders_in_both_directions_and_stays_bounded(self):
        h = Human({"seed": 11})
        values = []
        for _ in range(2000):
            h.think(move())
            values.append(h.form.value)
        self.assertTrue(all(-1.0 <= v <= 1.0 for v in values))
        self.assertGreater(max(values), 0.3)
        self.assertLess(min(values), -0.3)

    def test_form_changes_slowly(self):
        h = Human({"seed": 12})
        last = 0.0
        for _ in range(500):
            h.think(move())
            self.assertLess(abs(h.form.value - last), 0.6)
            last = h.form.value

    def test_slump_is_slower_and_flow_is_faster(self):
        h = Human({"seed": 2})
        h.form.value = 1.0
        flow = h.pace()
        h.form.value = -1.0
        self.assertLess(flow, h.pace())

    def test_slump_raises_mistake_chance_and_flow_lowers_it(self):
        h = Human({"seed": 3})
        h.form.value = -1.0
        slump = h.mistake_scale()
        h.form.value = 1.0
        self.assertGreater(slump, 1.0)
        self.assertLess(h.mistake_scale(), 1.0)

    def test_pressure_ignores_form(self):
        h = Human({"seed": 4})
        h.form.value = -1.0
        h.pressure = 2
        h.think(move())
        self.assertEqual(h.mistake_scale(), 1.0)
        self.assertEqual(h.scale(), 1.0)

    def test_tap_durations_vary_and_are_not_uniform(self):
        h = Human({"seed": 5}, {"tap_ms": 16, "gap_ms": 6})
        taps = [h.tap(16) for _ in range(500)]
        self.assertGreater(statistics.pstdev(taps), 0.001)
        self.assertGreater(len({round(t, 5) for t in taps}), 100)

    def test_taps_are_correlated_between_neighbours(self):
        h = Human({"seed": 6}, {"tap_ms": 16, "gap_ms": 6})
        taps = [h.tap(16) for _ in range(2000)]
        mean = statistics.fmean(taps)
        num = sum((a - mean) * (b - mean) for a, b in zip(taps, taps[1:]))
        den = sum((a - mean) ** 2 for a in taps)
        self.assertGreater(num / den, 0.05)


if __name__ == "__main__":
    unittest.main()
