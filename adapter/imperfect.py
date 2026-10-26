import random
from dataclasses import replace

BASE = {
    "I": [(0, 2), (1, 2), (2, 2), (3, 2)],
    "O": [(1, 1), (2, 1), (1, 2), (2, 2)],
    "T": [(0, 1), (1, 1), (2, 1), (1, 2)],
    "L": [(0, 1), (1, 1), (2, 1), (2, 2)],
    "J": [(0, 1), (1, 1), (2, 1), (0, 2)],
    "S": [(0, 1), (1, 1), (1, 2), (2, 2)],
    "Z": [(0, 2), (1, 2), (1, 1), (2, 1)],
}


def shape(piece, rot):
    n = 4 if piece in "IO" else 3
    cells = BASE[piece]
    for _ in range(rot % 4):
        cells = [(y, n - 1 - x) for x, y in cells]
    return cells


def collides(rows, piece, rot, x, y):
    for dx, dy in shape(piece, rot):
        cx, cy = x + dx, y + dy
        if cx < 0 or cx >= 10 or cy < 0:
            return True
        if cy < len(rows) and (rows[cy] >> cx) & 1:
            return True
    return False


def landing(rows, piece, rot, x):
    y = 22
    if collides(rows, piece, rot, x, y):
        return None
    while not collides(rows, piece, rot, x, y - 1):
        y -= 1
    return y


def height(rows):
    return max((i + 1 for i, r in enumerate(rows) if r), default=0)


def holes(rows):
    count = 0
    for x in range(10):
        seen = False
        for y in range(len(rows) - 1, -1, -1):
            if (rows[y] >> x) & 1:
                seen = True
            elif seen:
                count += 1
    return count


class Imperfect:
    def __init__(self, engine, chance=0.05, seed=None, max_height=8):
        self.engine = engine
        self.chance = chance
        self.scale = 1.0
        self.max_height = max_height
        self.rng = random.Random(seed)
        self.last = ""

    def maybe(self, move, rows, b2b, combo, incoming):
        self.last = ""
        if (self.chance <= 0 or incoming or self.rng.random() >= self.chance * self.scale
                or height(move.after) > self.max_height or not hasattr(self.engine, "place")):
            return move
        base_holes, base_height = holes(move.after), height(move.after)
        options = [-1, 1, -2, 2]
        self.rng.shuffle(options)
        for shift in options:
            x = move.x + shift
            y = landing(rows, move.piece, move.rot, x)
            if y is None:
                continue
            cells = ",".join("%d:%d" % (x + dx, y + dy) for dx, dy in shape(move.piece, move.rot))
            alt = self.engine.place(rows, move.piece, cells, "none", b2b, combo)
            if alt is None or not alt.after or alt.lines < move.lines - 1:
                continue
            if holes(alt.after) > base_holes + 1 or height(alt.after) > base_height + 2:
                continue
            self.last = "%+d column%s" % (shift, "" if abs(shift) == 1 else "s")
            return replace(alt, use_hold=move.use_hold)
        return move
