import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))
sys.path.insert(0, os.path.dirname(__file__))

import layout as layout_mod
from palette import DEFAULT_PALETTE
from synthetic import make_frame
from vision import Frame, Reader


class LayoutTest(unittest.TestCase):
    def check(self, **kwargs):
        img, board = make_frame(**kwargs)
        boxes = layout_mod.detect_pixels(img)
        self.assertIsNotNone(boxes)
        found = layout_mod.to_points(boxes, 1.0)
        for got, want in zip(found.board, board):
            self.assertLessEqual(abs(got - want), 3)
        reader = Reader(found, DEFAULT_PALETTE, 95)
        frame = Frame(img, 1.0, (0, 0))
        self.assertEqual(reader.previews(frame), list(kwargs.get("upcoming", "TOZLS")))
        self.assertEqual(reader.hold(frame), kwargs.get("hold", "J"))

    def test_default(self):
        self.check()

    def test_other_position(self):
        self.check(width=1300, height=900, board_x=520, board_y=40, upcoming="IJSZL", hold="O")

    def test_larger_cells(self):
        self.check(width=1400, height=1000, cell=40, board_x=500, board_y=60, upcoming="SZTIO", hold="L")

    def test_empty_hold(self):
        self.check(hold=None)

    def test_meter(self):
        for lines in (0, 1, 4, 9):
            img, _ = make_frame(meter=lines)
            boxes = layout_mod.detect_pixels(img)
            reader = Reader(layout_mod.to_points(boxes, 1.0), DEFAULT_PALETTE, 95)
            self.assertEqual(reader.incoming(Frame(img, 1.0, (0, 0))), lines)

    def test_meter_rejects_bright_background(self):
        img, _ = make_frame()
        boxes = layout_mod.detect_pixels(img)
        layout = layout_mod.to_points(boxes, 1.0)
        img[:, : layout.board[0]] = 200
        reader = Reader(layout, DEFAULT_PALETTE, 95)
        self.assertEqual(reader.incoming(Frame(img, 1.0, (0, 0))), 0)

    def test_no_board(self):
        import numpy as np
        self.assertIsNone(layout_mod.detect_pixels(np.full((600, 800, 3), 60, dtype=np.uint8)))


class BorderTest(unittest.TestCase):
    def test_coloured_frame_is_not_a_piece(self):
        img, board = make_frame(hold=None)
        boxes = layout_mod.detect_pixels(img)
        found = layout_mod.to_points(boxes, 1.0)
        x0, y0, x1, y1 = found.hold
        img[y1 - 4:y1, x0:x1] = DEFAULT_PALETTE["L"]
        img[y0:y1, x1 - 4:x1] = DEFAULT_PALETTE["L"]
        reader = Reader(found, DEFAULT_PALETTE, 95)
        self.assertIsNone(reader.hold(Frame(img, 1.0, (0, 0))))


if __name__ == "__main__":
    unittest.main()


class PanelHeaderTest(unittest.TestCase):
    def test_coloured_header_is_not_a_piece(self):
        import numpy as np
        import panel_finder
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        blob = (180.0, 130.0, 160, 60)
        img[100:160, 100:260] = (182, 103, 54)
        self.assertTrue(panel_finder.on_dark(img, blob, 61.0))
        img[:, :] = (182, 103, 54)
        img[100:160, 100:260] = (180, 100, 50)
        self.assertFalse(panel_finder.on_dark(img, blob, 61.0))
