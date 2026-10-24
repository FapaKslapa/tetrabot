import numpy as np

import imageops
from palette import DEFAULT_PALETTE, palette_mask

SLOT_CELLS = 3.0
NEXT_SLOTS = 5
PANEL_HALF_WIDTH = 0.77


def piece_blobs(img, x0, x1, y0, y1, c, palette, f=3):
    height, width = img.shape[:2]
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(width, int(x1)), min(height, int(y1))
    if x1 - x0 < c or y1 - y0 < c:
        return []
    mask = palette_mask(img[y0:y1, x0:x1], palette).astype(np.float32)
    coarse = imageops.block_mean(mask, f) >= 0.5
    blobs = []
    for bx0, by0, bx1, by1, area in imageops.components(coarse):
        w, h = (bx1 - bx0) * f, (by1 - by0) * f
        if not (0.7 * c <= min(w, h) <= 2.3 * c and 1.7 * c <= max(w, h) <= 4.4 * c):
            continue
        if area * f * f < 0.35 * w * h:
            continue
        blobs.append((x0 + (bx0 + bx1) * f / 2.0, y0 + (by0 + by1) * f / 2.0, w, h))
    return blobs


def pick_column(blobs, c):
    best = []
    for b in blobs:
        group = [o for o in blobs if abs(o[0] - b[0]) <= 0.7 * c]
        if len(group) > len(best):
            best = group
    return sorted(best, key=lambda t: t[1])


def fit_slots(column, board_top, c):
    ys = [b[1] for b in column]
    pitch0 = SLOT_CELLS * c
    k0 = max(0, int(round((ys[0] - board_top - 2.2 * c) / pitch0)))
    ks = [k0]
    for a, b in zip(ys, ys[1:]):
        ks.append(ks[-1] + max(1, int(round((b - a) / pitch0))))
    keep = [(k, y) for k, y in zip(ks, ys) if k < NEXT_SLOTS]
    if len(keep) >= 2:
        k = np.array([t[0] for t in keep], dtype=float)
        y = np.array([t[1] for t in keep], dtype=float)
        pitch, y0 = np.polyfit(k, y, 1)
        if not (0.85 * pitch0 <= pitch <= 1.2 * pitch0):
            pitch = pitch0
            y0 = float(np.median(y - k * pitch))
    else:
        pitch = pitch0
        y0 = keep[0][1] - keep[0][0] * pitch
    return float(y0), float(pitch)


def find_next(img, board, palette):
    bx, by, bw, _ = board
    c = bw / 10.0
    blobs = piece_blobs(img, bx + bw, bx + bw + 8 * c, by - 2 * c, by + 18 * c, c, palette)
    column = pick_column(blobs, c)
    if len(column) < 2:
        return None, None
    cx = float(np.median([b[0] for b in column]))
    y0, pitch = fit_slots(column, by, c)
    half = PANEL_HALF_WIDTH * pitch
    top = y0 - pitch / 2
    return [cx - half, top, cx + half, top + NEXT_SLOTS * pitch], pitch


def find_dark_run(img, x0, x1, y0, y1, c):
    height, width = img.shape[:2]
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(width, int(x1)), min(height, int(y1))
    if x1 <= x0 or y1 <= y0:
        return None
    v = img[y0:y1, x0:x1].max(axis=2)
    dark_cols = (v < 70).mean(axis=0) >= 0.85
    found = [r for r in imageops.runs(dark_cols, 2) if r[1] - r[0] >= 3 * c]
    if not found:
        return None
    a, b = found[-1]
    if b - a > 5.2 * c:
        a = b - 5.2 * c
    return [x0 + a, y0, x0 + b, y1]


def find_hold(img, board, next_box, pitch, palette):
    bx, by, bw, _ = board
    c = bw / 10.0
    if next_box is not None:
        ya, yb = next_box[1], next_box[1] + pitch
    else:
        pitch = SLOT_CELLS * c
        ya, yb = by + 0.3 * c, by + 3.5 * c
    blobs = piece_blobs(img, bx - 9 * c, bx, ya - 0.5 * c, yb + 0.5 * c, c, palette)
    if blobs:
        hx = max(blobs, key=lambda t: t[2] * t[3])[0]
        half = PANEL_HALF_WIDTH * pitch
        return [hx - half, ya, hx + half, yb]
    return find_dark_run(img, bx - 9 * c, bx, ya, yb, c)


def find_panels(img, board, palette=DEFAULT_PALETTE):
    next_box, pitch = find_next(img, board, palette)
    return next_box, find_hold(img, board, next_box, pitch, palette)
