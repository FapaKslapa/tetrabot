import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

import settings as settings_mod
from session import SETTLE, Session


def session():
    s = Session(settings_mod.load(), None, None, None, None)
    s.settings["trace"] = False
    s.state.memory = [0b0000001111] + [0] * 19
    s.state.pieces = 3
    return s


class ReconcileTest(unittest.TestCase):
    def test_extra_cells_only_are_trusted_without_settling(self):
        s = session()
        seen = [0b0000001111, 0b0000011111, 0b0000000111] + [0] * 17
        result = s.reconcile(seen, {}, False, False)
        self.assertEqual(result[0], 0b0000001111)
        self.assertEqual(s.state.trusted, 1)

    def test_missing_cells_wait_for_settle(self):
        s = session()
        seen = [0b1111000000] + [0b1111111111] * 3 + [0] * 16
        self.assertIs(s.reconcile(seen, {}, False, False), SETTLE)

    def test_trust_is_limited(self):
        s = session()
        s.state.trusted = 2
        seen = [0b0000001111, 0b0000011111, 0b0000000111] + [0] * 17
        self.assertIs(s.reconcile(seen, {}, False, False), SETTLE)


if __name__ == "__main__":
    unittest.main()


class GarbageTest(unittest.TestCase):
    def test_extra_garbage_row_is_not_an_animation(self):
        s = session()
        seen = [0b1111111011, 0b0000001111] + [0] * 18
        self.assertIs(s.reconcile(seen, {}, False, False), SETTLE)

    def test_predicted_garbage_that_never_arrived_is_dropped(self):
        s = session()
        s.state.memory = [0b1111111011, 0b0000001111] + [0] * 18
        seen = [0b0000001111] + [0] * 19
        self.assertEqual(s.reconcile(seen, {}, False, False)[0], 0b0000001111)


class UnsettledGarbageTest(unittest.TestCase):
    def test_unsettled_screen_waits_even_with_garbage(self):
        s = session()
        s.state.sees_garbage = True
        seen = [0b1111111011, 0b0111110111, 0b0000001111] + [0] * 17
        self.assertIs(s.reconcile(seen, {}, True, False), SETTLE)
