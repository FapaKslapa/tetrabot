import numpy as np

from palette import is_gray

RECALIBRATE_AFTER_IDLE = 3.0
RECALIBRATE_INTERVAL = 2.0
GAME_OVER_IDLE = 0.6
MAX_START_CELLS = 8
MEMORY_TOLERANCE = 4
MEMORY_GIVE_UP = 3
PHANTOM_AFTER = 3
SETTLE_SECONDS = 0.14
SETTLE_POLL = 0.012
SETTLE = object()
MEMORY_FAR = 40
TRUST_LIMIT = 2
FAR_GIVE_UP = 5
FALLING_MAX_STACK = 12
SPAWN_CLEAN_WAIT = 0.05
REALIGN_CONFIRM = 2


BLACK = np.zeros(3)


def looks_like_garbage(cells, colors):
    rows = {}
    for r, c in cells:
        if is_gray(colors.get((r, c), BLACK)):
            return True
        rows[r] = rows.get(r, 0) + 1
    return any(n >= 8 for n in rows.values())


def missing(previews):
    return sum(p is None for p in previews)
