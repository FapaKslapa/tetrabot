import numpy as np


def block_mean(a, f):
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    return a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def integral(a):
    s = np.zeros((a.shape[0] + 1, a.shape[1] + 1), dtype=np.float64)
    s[1:, 1:] = a.cumsum(0).cumsum(1)
    return s


def window_mean(s, w, h):
    return (s[h:, w:] - s[:-h, w:] - s[h:, :-w] + s[:-h, :-w]) / float(w * h)


def runs(flags, min_gap):
    out = []
    start = None
    last = None
    for i, on in enumerate(list(flags) + [False]):
        if on:
            if start is None:
                start = i
            last = i
        elif start is not None and i - last > min_gap:
            out.append([start, last + 1])
            start = None
    return out


def components(mask):
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        stack = [(y0, x0)]
        seen[y0, x0] = True
        bx0 = bx1 = x0
        by0 = by1 = y0
        area = 0
        while stack:
            y, x = stack.pop()
            area += 1
            bx0, bx1 = min(bx0, x), max(bx1, x)
            by0, by1 = min(by0, y), max(by1, y)
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        out.append((bx0, by0, bx1 + 1, by1 + 1, area))
    return out
