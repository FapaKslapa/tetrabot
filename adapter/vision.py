from typing import NamedTuple, Tuple

import numpy as np

from palette import classify, is_block, vote

BRIGHT = 110
MIN_PIECE_PIXELS = 20
METER_LEFT = 0.80
METER_RIGHT = 0.30
METER_ON = 60
METER_OFF = 40
METER_MAX = 15


class Frame(NamedTuple):
    img: np.ndarray
    scale: float
    origin: Tuple[float, float]


def sample(frame, x, y, r=2):
    px, py = int(x * frame.scale), int(y * frame.scale)
    rr = max(1, int(r * frame.scale))
    patch = frame.img[max(0, py - rr): py + rr + 1, max(0, px - rr): px + rr + 1].reshape(-1, 3)
    if len(patch) == 0:
        return np.zeros(3)
    return patch.mean(axis=0)


def sample_wide(frame, x, y, half_w, half_h):
    s = frame.scale
    px0, px1 = int((x - half_w) * s), int((x + half_w) * s) + 1
    py0, py1 = int((y - half_h) * s), int((y + half_h) * s) + 1
    patch = frame.img[max(0, py0):max(1, py1), max(0, px0):max(1, px1)].reshape(-1, 3).astype(float)
    if len(patch) == 0:
        return np.zeros((1, 3))
    return patch


def crop(frame, box):
    x0, y0, x1, y1 = box
    ox, oy = frame.origin
    s = frame.scale
    ys, ye = int((y0 - oy) * s), int((y1 - oy) * s)
    xs, xe = int((x0 - ox) * s), int((x1 - ox) * s)
    return frame.img[max(0, ys):ye, max(0, xs):xe]


class Reader:
    def __init__(self, layout, palette, threshold):
        self.layout = layout
        self.palette = palette
        self.threshold = threshold

    def board(self, frame, rows=20):
        bx0, by0, bx1, by1 = self.layout.board
        cw = (bx1 - bx0) / 10.0
        ch = (by1 - by0) / 20.0
        out = [0] * rows
        colors = {}
        for r in range(rows):
            y = by1 - (r + 0.5) * ch - frame.origin[1]
            for c in range(10):
                x = bx0 + (c + 0.5) * cw - frame.origin[0]
                color = sample(frame, x, y)
                if is_block(color, self.palette, self.threshold):
                    out[r] |= 1 << c
                    colors[(r, c)] = color
        return out, colors

    def piece_in(self, region, scale):
        pixels = region.reshape(-1, 3).astype(float)
        if len(pixels) == 0:
            return None
        bright = pixels[pixels.max(axis=1) >= BRIGHT]
        if len(bright) < MIN_PIECE_PIXELS * scale * scale:
            return None
        letter, count = vote(bright, self.palette)
        if count < MIN_PIECE_PIXELS * scale * scale:
            return None
        return letter

    def previews(self, frame):
        x0, y0, x1, y1 = self.layout.next
        slot = (y1 - y0) / 5.0
        return [self.piece_in(crop(frame, (x0, y0 + i * slot, x1, y0 + (i + 1) * slot)), frame.scale)
                for i in range(5)]

    def hold(self, frame):
        if not self.layout.hold:
            return None
        return self.piece_in(crop(frame, self.layout.hold), frame.scale)

    def active(self, colors):
        cells = sorted(colors.items(), key=lambda kv: -kv[0][0])[:4]
        if len(cells) < 4:
            return None
        votes = [classify(v, self.palette) for _, v in cells]
        best = max(set(votes), key=votes.count)
        return best if votes.count(best) >= 3 else None

    def meter_levels(self, frame):
        bx0, by0, bx1, by1 = self.layout.board
        c = (bx1 - bx0) / 10.0
        ch = (by1 - by0) / 20.0
        x = bx0 - (METER_LEFT + METER_RIGHT) / 2.0 * c - frame.origin[0]
        half = max(1.0, (METER_LEFT - METER_RIGHT) / 2.0 * c * 0.6)
        levels = []
        for r in range(20):
            y = by1 - (r + 0.5) * ch - frame.origin[1]
            levels.append(float(sample_wide(frame, x, y, half, ch * 0.3).max(axis=1).mean()))
        return levels

    def incoming(self, frame):
        levels = self.meter_levels(frame)
        filled = 0
        while filled < METER_MAX and levels[filled] >= METER_ON:
            filled += 1
        if filled >= METER_MAX or any(v >= METER_OFF for v in levels[filled + 1:]):
            return 0
        return filled
