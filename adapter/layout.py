from dataclasses import dataclass
from typing import Optional, Tuple

import board_finder
import panel_finder
from palette import DEFAULT_PALETTE

Box = Tuple[int, int, int, int]


@dataclass(frozen=True)
class Layout:
    board: Box
    next: Box
    hold: Optional[Box]

    def boxes(self):
        return [b for b in (self.board, self.next, self.hold) if b]

    def region(self, margin=4):
        boxes = self.boxes()
        x0 = min(b[0] for b in boxes) - margin
        y0 = min(b[1] for b in boxes) - margin
        x1 = max(b[2] for b in boxes) + margin
        y1 = max(b[3] for b in boxes) + margin
        return x0, y0, x1 - x0, y1 - y0


def detect_pixels(img, palette=DEFAULT_PALETTE):
    found = board_finder.find_board(img)
    if found is None:
        return None
    x, y, w, h = found
    next_box, hold_box = panel_finder.find_panels(img, found, palette)
    if next_box is None:
        return None
    return {"board": [x, y, x + w, y + h], "next": next_box, "hold": hold_box}


def to_points(boxes, scale, left=0, top=0):
    def convert(box):
        if box is None:
            return None
        return tuple(int(round(v)) for v in (
            box[0] / scale + left, box[1] / scale + top,
            box[2] / scale + left, box[3] / scale + top))
    return Layout(convert(boxes["board"]), convert(boxes["next"]), convert(boxes["hold"]))
