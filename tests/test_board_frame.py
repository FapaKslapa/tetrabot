import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

import board_finder
import imageops
import panel_finder
from palette import DEFAULT_PALETTE


def framed_screen():
    img = np.full((760, 760, 3), 190, dtype=np.uint8)
    img[100:580, 100:130] = 8
    img[100:586, 130:136] = 255
    img[100:580, 136:376] = 8
    img[100:586, 376:382] = 255
    img[100:580, 382:760] = 8
    img[580:586, 100:382] = 255
    img[592:620, 136:376] = 8
    return img


class FramedBoardTest(unittest.TestCase):
    def test_meter_strip_and_nameplate_are_not_part_of_the_board(self):
        x, y, w, h = board_finder.find_board(framed_screen())
        self.assertLessEqual(abs(x - 136), 4)
        self.assertLessEqual(abs(w - 240), 4)
        self.assertLessEqual(abs(y + h - 580), 5)

    def test_run_touching_the_end_is_closed(self):
        self.assertEqual(imageops.runs([False, True, True, True], 3), [[1, 4]])

    def test_missing_hold_box_falls_back_to_the_board_side(self):
        img = framed_screen()
        board = (136, 100, 240, 480)
        next_box = [400, 110, 500, 560]
        box = panel_finder.find_hold(img, board, next_box, 90.0, DEFAULT_PALETTE)
        self.assertIsNotNone(box)
        self.assertLess(box[2], board[0])


if __name__ == "__main__":
    unittest.main()
