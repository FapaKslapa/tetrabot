import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

from cold_clear import BagTracker, tbp_cells


class ColdClearTest(unittest.TestCase):
    def test_cells_north(self):
        cells = tbp_cells({"type": "T", "orientation": "north", "x": 4, "y": 0})
        self.assertEqual(sorted(cells), [(3, 0), (4, 0), (4, 1), (5, 0)])

    def test_cells_east_points_right(self):
        cells = tbp_cells({"type": "T", "orientation": "east", "x": 4, "y": 5})
        self.assertIn((5, 5), cells)
        self.assertEqual(len(set(cells)), 4)

    def test_vertical_i(self):
        cells = tbp_cells({"type": "I", "orientation": "east", "x": 5, "y": 10})
        self.assertEqual(sorted(x for x, _ in cells), [5, 5, 5, 5])

    def test_bag_after_start(self):
        tracker = BagTracker()
        tracker.update("TOILJS")
        self.assertEqual(tracker.remaining(), ["Z"])

    def test_bag_after_shift(self):
        tracker = BagTracker()
        tracker.update("TOILJS")
        tracker.update("OILJSZ")
        self.assertEqual(tracker.remaining(), ["I", "O", "T", "L", "J", "S", "Z"])

    def test_bag_after_hold_shift(self):
        tracker = BagTracker()
        tracker.update("TOILJS")
        tracker.update("ILJSZT")
        self.assertEqual(tracker.remaining(), ["I", "O", "L", "J", "S", "Z"])

    def test_bag_invalid_on_jump(self):
        tracker = BagTracker()
        tracker.update("TOILJS")
        tracker.update("ZZZZZZ")
        self.assertIsNone(tracker.remaining())


if __name__ == "__main__":
    unittest.main()
