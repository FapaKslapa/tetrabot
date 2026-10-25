import numpy as np

import imageops

DARK = 56
MIN_FILL = 0.85
MIN_CONTRAST = 0.5
SCAN_FACTOR = 4
LINE_BRIGHT = 150
LINE_SHARE = 0.6
LINE_MAX = 0.2


def split_at_lines(runs, bright, c):
    lines = [r for r in imageops.runs(bright, 1) if r[1] - r[0] <= LINE_MAX * c]
    out = []
    for a, b in runs:
        start = a
        for la, lb in lines:
            if start < la and lb < b and la - start >= 1:
                out.append((start, la))
                start = lb
        out.append((start, b))
    return [r for r in out if r[1] > r[0]]


def refine(img, x, y, w, h):
    height, width = img.shape[:2]
    c = w / 10.0
    v = img.max(axis=2)
    gx0, gx1 = int(max(0, x - 2 * c)), int(min(width, x + w + 2 * c))
    gy0, gy1 = int(max(0, y - 2 * c)), int(min(height, y + h + 2 * c))
    gap = max(2, int(0.15 * c))
    ya, yb = int(y + 0.25 * h), int(y + 0.75 * h)
    cols = (v[ya:yb, gx0:gx1] < DARK).mean(axis=0) > 0.35
    rx = imageops.runs(cols, gap)
    bright_cols = (v[ya:yb, gx0:gx1] > LINE_BRIGHT).mean(axis=0) > LINE_SHARE
    rx = split_at_lines(rx, bright_cols, c)
    if not rx:
        return x, y, w, h
    rx = [r for r in rx if r[1] + gx0 > x and r[0] + gx0 < x + w] or rx
    a, b = max(rx, key=lambda r: r[1] - r[0])
    nx, nw = gx0 + a, b - a
    xa, xb = int(nx + 0.2 * nw), int(nx + 0.8 * nw)
    rows = (v[gy0:gy1, xa:xb] < DARK).mean(axis=1) > 0.35
    ry = imageops.runs(rows, gap)
    bright_rows = (v[gy0:gy1, xa:xb] > LINE_BRIGHT).mean(axis=1) > LINE_SHARE
    ry = split_at_lines(ry, bright_rows, nw / 10.0)
    ry = [r for r in ry if r[1] + gy0 > y and r[0] + gy0 < y + h] or ry
    if not ry:
        return nx, y, nw, 2 * nw
    a, b = max(ry, key=lambda r: r[1] - r[0])
    ny, nh = gy0 + a, b - a
    if abs(nh - 2 * nw) <= 0.03 * 2 * nw:
        return nx, ny, nw, nh
    return nx, ny + nh - 2 * nw, nw, 2 * nw


def find_board(img, f=SCAN_FACTOR):
    v = img.max(axis=2).astype(np.float32)
    dark = (imageops.block_mean(v, f) < DARK).astype(np.float64)
    height, width = dark.shape
    table = imageops.integral(dark)
    candidates = []
    for w in range(16, min(width // 2, height // 2 - 2)):
        h = 2 * w
        m = max(1, int(round(w * 0.045)))
        if h + 2 * m >= height or w + 2 * m >= width:
            break
        inner = imageops.window_mean(table, w, h)
        wo, ho = w + 2 * m, h + 2 * m
        outer = imageops.window_mean(table, wo, ho)
        inner = inner[m:m + outer.shape[0], m:m + outer.shape[1]]
        ring = (outer * wo * ho - inner * w * h) / float(wo * ho - w * h)
        score = np.where(inner >= MIN_FILL, inner - ring, -1.0)
        idx = np.unravel_index(int(score.argmax()), score.shape)
        best = float(score[idx])
        if best > MIN_CONTRAST:
            candidates.append((best, w, idx[1] + m, idx[0] + m))
    if not candidates:
        return None
    widest = max(c[1] for c in candidates)
    large = [c for c in candidates if c[1] >= 0.93 * widest]
    top = max(c[0] for c in large)
    near = [c for c in large if c[0] >= top - 0.05]
    _, w, x, y = min(near, key=lambda c: c[2])
    x, y, w, h = refine(img, x * f, y * f, w * f, 2 * w * f)
    return int(x), int(y), int(w), int(h)
