import numpy as np

DEFAULT_PALETTE = {
    "Z": (182, 53, 62),
    "L": (182, 103, 54),
    "O": (181, 156, 54),
    "S": (134, 181, 54),
    "I": (52, 181, 133),
    "J": (87, 62, 209),
    "T": (168, 67, 159),
}

MIN_BRIGHTNESS = 80
MAX_TINT_DISTANCE = 0.03


def normalize(color):
    c = np.asarray(color, dtype=float)
    return c / max(c.max(), 1.0)


def classify(color, palette=DEFAULT_PALETTE):
    if np.max(color) < MIN_BRIGHTNESS:
        return None
    n = normalize(color)
    best, best_dist = None, 1e18
    for letter, ref in palette.items():
        d = float(((n - normalize(ref)) ** 2).sum())
        if d < best_dist:
            best, best_dist = letter, d
    return best


def vote(pixels, palette=DEFAULT_PALETTE):
    px = np.asarray(pixels, dtype=np.float32).reshape(-1, 3)
    if len(px) == 0:
        return None, 0
    n = px / np.maximum(px.max(axis=1), 1.0)[:, None]
    letters = list(palette)
    refs = np.array([normalize(palette[k]) for k in letters], dtype=np.float32)
    dist = ((n[:, None, :] - refs[None, :, :]) ** 2).sum(axis=2)
    best = dist.argmin(axis=1)
    keep = dist.min(axis=1) <= MAX_TINT_DISTANCE
    if not keep.any():
        return None, 0
    counts = np.bincount(best[keep], minlength=len(letters))
    return letters[int(counts.argmax())], int(counts.max())


def is_gray(color):
    mx = float(color.max())
    return 55 <= mx <= 215 and float(color.min()) / mx > 0.85


def is_block(color, palette, threshold):
    if is_gray(color):
        return True
    if float(color.max()) < threshold:
        return False
    n = normalize(color)
    return min(float(((n - normalize(v)) ** 2).sum()) for v in palette.values()) <= MAX_TINT_DISTANCE


def palette_mask(img, palette):
    v = img.max(axis=2).astype(np.float32)
    n = img.astype(np.float32) / np.maximum(v, 1.0)[:, :, None]
    best = np.full(v.shape, 9.0, dtype=np.float32)
    for ref in palette.values():
        c = np.asarray(ref, dtype=np.float32)
        c = c / max(float(c.max()), 1.0)
        best = np.minimum(best, ((n - c) ** 2).sum(axis=2))
    return (v >= 95) & (best <= MAX_TINT_DISTANCE)
