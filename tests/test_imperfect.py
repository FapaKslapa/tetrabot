import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

from engine_client import Move
from imperfect import Imperfect, collides, holes, height, landing, shape


def lock(rows, piece, rot, x, y):
    rows = list(rows) + [0] * 6
    for dx, dy in shape(piece, rot):
        rows[y + dy] |= 1 << (x + dx)
    kept = [r for r in rows if r != 1023]
    return kept + [0] * (len(rows) - len(kept))


def trim(rows):
    top = height(rows)
    return rows[:max(top, 1)]


class FakeEngine:
    def place(self, rows, piece, cells, spin, b2b, combo):
        pts = [tuple(int(v) for v in c.split(":")) for c in cells.split(",")]
        for rot in range(4):
            for x in range(-3, 10):
                for y in range(-3, 30):
                    if sorted((x + dx, y + dy) for dx, dy in shape(piece, rot)) == sorted(pts):
                        after = trim(lock(rows, piece, rot, x, y))
                        return Move(piece, False, ["R"], after, 0, 0, 0, 0, rot, x, y)
        return None


def best_move(rows, piece, rot, x):
    y = landing(rows, piece, rot, x)
    after = trim(lock(rows, piece, rot, x, y))
    return Move(piece, True, ["R"], after, 0, 0, 0, 0, rot, x, y)


class ShapeTest(unittest.TestCase):
    def test_shapes_match_engine_table(self):
        self.assertEqual(sorted(shape("O", 0)), sorted([(1, 1), (2, 1), (1, 2), (2, 2)]))
        self.assertEqual(sorted(shape("I", 1)), [(2, 0), (2, 1), (2, 2), (2, 3)])
        self.assertEqual(sorted(shape("T", 1)), sorted([(1, 0), (1, 1), (1, 2), (2, 1)]))

    def test_landing_on_empty_and_stacked_board(self):
        self.assertEqual(landing([0] * 40, "O", 0, 3), -1)
        self.assertEqual(landing([0b1111111110] + [0] * 39, "O", 0, 3), 0)
        self.assertEqual(landing([0b0000011000] + [0] * 39, "O", 0, 3), 0)

    def test_holes_and_height(self):
        self.assertEqual(holes([0b0000000001, 0, 0b0000000001]), 1)
        self.assertEqual(height([1, 1, 0, 0]), 2)


class ImperfectTest(unittest.TestCase):
    def setUp(self):
        self.rows = [0b0001111111, 0b0000001111] + [0] * 38

    def test_never_changes_move_when_chance_zero_or_incoming(self):
        move = best_move(self.rows, "O", 0, 7)
        imp = Imperfect(FakeEngine(), 0.0, 1)
        self.assertIs(imp.maybe(move, self.rows, 0, 0, 0), move)
        imp = Imperfect(FakeEngine(), 1.0, 1)
        self.assertIs(imp.maybe(move, self.rows, 0, 0, 3), move)

    def test_alternative_is_near_valid_and_keeps_hold_flag(self):
        changed = 0
        for seed in range(60):
            move = best_move(self.rows, "O", 0, 7)
            imp = Imperfect(FakeEngine(), 1.0, seed)
            chosen = imp.maybe(move, self.rows, 0, 0, 0)
            if chosen is move:
                continue
            changed += 1
            self.assertTrue(chosen.use_hold)
            self.assertIn(abs(chosen.x - move.x), (1, 2))
            self.assertEqual(chosen.rot, move.rot)
            self.assertLessEqual(holes(chosen.after), holes(move.after) + 1)
            self.assertLessEqual(height(chosen.after), height(move.after) + 2)
            self.assertFalse(collides(self.rows, chosen.piece, chosen.rot, chosen.x, chosen.y))
        self.assertGreater(changed, 30)

    def test_tall_stack_is_left_alone(self):
        tall = [0b0111111111] * 12
        move = best_move(tall, "O", 0, 3)
        self.assertIs(Imperfect(FakeEngine(), 1.0, 1).maybe(move, tall, 0, 0, 0), move)

    def test_rate_follows_chance(self):
        imp = Imperfect(FakeEngine(), 0.05, 5)
        changed = 0
        for _ in range(2000):
            move = best_move(self.rows, "O", 0, 7)
            if imp.maybe(move, self.rows, 0, 0, 0) is not move:
                changed += 1
        self.assertTrue(40 <= changed <= 160, changed)


if __name__ == "__main__":
    unittest.main()
