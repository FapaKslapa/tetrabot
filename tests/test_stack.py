import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

import numpy as np

from stack import ascii_board, bit_difference, count_cells, drop_stray_gray, garbage_hole, strip_floating_top
from engine_client import parse_move


class StackTest(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(count_cells([0b101, 0b11]), 4)
        self.assertEqual(bit_difference([0b101], [0b110]), 2)

    def test_stray_gray_removed(self):
        gray = np.array([120.0, 120.0, 120.0])
        rows = [0] * 20
        colors = {}
        for c in range(10):
            if c != 4:
                rows[0] |= 1 << c
                colors[(0, c)] = gray
        for c in (2, 3, 4):
            rows[7] |= 1 << c
            colors[(7, c)] = gray
        out, kept = drop_stray_gray(rows, colors)
        self.assertEqual(out[7], 0)
        self.assertEqual(out[0], rows[0])
        self.assertEqual(len(kept), 9)

    def test_floating_top_removed(self):
        rows = [0] * 20
        rows[19] = 0b1
        self.assertEqual(strip_floating_top(rows)[19], 0)

    def test_ascii(self):
        rows = [0] * 20
        rows[0] = 1
        self.assertTrue(ascii_board(rows).splitlines()[-1].startswith("#"))

    def test_garbage_hole(self):
        gray = np.array([120.0, 120.0, 120.0])
        colors = {(0, c): gray for c in range(10) if c != 6}
        self.assertEqual(garbage_hole(colors), 6)
        self.assertIsNone(garbage_hole({}))

    def test_parse_move(self):
        line = "MOVE use_hold=1 piece=I rot=0 x=3 y=-2 spin=0 keys=L,CW after=120,5 hold=T b2b=0 combo=2 attack=1 lines=1"
        move = parse_move(line)
        self.assertTrue(move.use_hold)
        self.assertEqual(move.keys, ["L", "CW"])
        self.assertEqual(move.after, [120, 5])
        self.assertEqual(move.combo, 2)
        self.assertIsNone(parse_move("DEAD"))


if __name__ == "__main__":
    unittest.main()
