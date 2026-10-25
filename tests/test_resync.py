import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

import settings as settings_mod
from session import FAR_GIVE_UP, SETTLE, Session
from stack import best_candidate, drop_specks

FULL = (1 << 10) - 1


def hole_row(hole):
    return FULL & ~(1 << hole)


def session(memory):
    s = Session(settings_mod.load(), None, None, None, None)
    s.settings["trace"] = False
    s.state.memory = list(memory)
    s.state.pieces = 3
    return s


class SeenRiseTest(unittest.TestCase):
    def test_rows_with_different_holes_are_found_without_a_hole(self):
        expected = [0b0000001111, 0b0000000111] + [0] * 18
        garbage = [hole_row(2), hole_row(7), hole_row(4)]
        screen = (garbage + expected)[:20]
        diff, cand, rose = best_candidate(screen, expected, None, True)
        self.assertEqual((diff, rose), (0, True))
        self.assertEqual(cand, screen)

    def test_not_used_before_the_screen_settles(self):
        expected = [0b0000001111] + [0] * 19
        screen = ([hole_row(2), hole_row(7)] + expected)[:20]
        diff, cand, rose = best_candidate(screen, expected, None, False)
        self.assertFalse(rose)

    def test_plain_stack_is_not_mistaken_for_garbage(self):
        expected = [hole_row(3), 0b0000001111] + [0] * 18
        screen = list(expected)
        diff, cand, rose = best_candidate(screen, expected, None, True)
        self.assertEqual((diff, rose), (0, False))


class ReconcileResyncTest(unittest.TestCase):
    def test_multi_hole_garbage_is_adopted_when_settled(self):
        memory = [0b0000001111, 0b0000000111] + [0] * 18
        s = session(memory)
        screen = ([hole_row(1), hole_row(8), hole_row(5), hole_row(0)] + memory)[:20]
        result = s.reconcile(screen, {}, False, True)
        self.assertEqual(result, screen)

    def test_unrelated_board_is_adopted_after_repeated_settled_reads(self):
        s = session([0b0000001111] + [0] * 19)
        screen = [0b0101010101, 0b1010101010] * 8 + [0] * 4
        for _ in range(FAR_GIVE_UP - 1):
            self.assertNotEqual(s.reconcile(screen, {}, False, True), screen)
        self.assertEqual(s.reconcile(screen, {}, False, True), screen)


class SpeckTest(unittest.TestCase):
    def test_floating_specks_high_on_the_board_are_removed(self):
        rows = [0b0000001111] + [0] * 19
        rows[13] = 1 << 5
        rows[15] = 1 << 6
        rows[16] = (1 << 3) | (1 << 4)
        rows[17] = 1 << 6
        self.assertEqual(drop_specks(rows), [0b0000001111] + [0] * 19)

    def test_connected_stack_is_kept(self):
        rows = [0b1111111111] * 10 + [0b0000000011, 0b0000000001, 0, 0] + [0] * 6
        self.assertEqual(drop_specks(rows), rows)

    def test_low_specks_are_kept(self):
        rows = [0b0000001111, 0, 0b0000100000] + [0] * 17
        self.assertEqual(drop_specks(rows), rows)

    def test_four_cell_group_is_kept(self):
        rows = [0] * 20
        rows[15] = 0b0000001100
        rows[16] = 0b0000001100
        self.assertEqual(drop_specks(rows), rows)


if __name__ == "__main__":
    unittest.main()
