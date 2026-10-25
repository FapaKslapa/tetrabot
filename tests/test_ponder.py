import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

from bag import BagTracker
from ponder import Ponder
from queue_vote import QueueVote
from stack import best_candidate, clear_cells, extra_cells, raise_rows


class FakeEngine:
    def ask(self, **request):
        return request["queue"]


class PonderTest(unittest.TestCase):
    def test_accepts_matching_key(self):
        p = Ponder(FakeEngine())
        p.start("k", {"queue": "TOSZI"})
        self.assertEqual(p.take(lambda key: key == "k"), "TOSZI")

    def test_rejects_other_key(self):
        p = Ponder(FakeEngine())
        p.start("k", {"queue": "TOSZI"})
        self.assertIsNone(p.take(lambda key: key == "x"))
        self.assertIsNone(p.take(lambda key: True))

    def test_discard_without_work(self):
        Ponder(FakeEngine()).discard()


class CandidateTest(unittest.TestCase):
    def test_plain_match(self):
        expected = [0b11] + [0] * 19
        diff, cand, rose = best_candidate(list(expected), expected, None)
        self.assertEqual((diff, rose), (0, False))

    def test_garbage_rise_found(self):
        expected = [0b11] + [0] * 19
        screen = raise_rows(expected, 2, 4)
        diff, cand, rose = best_candidate(screen, expected, 4)
        self.assertEqual((diff, rose), (0, True))
        self.assertEqual(cand, screen)


class VoteTest(unittest.TestCase):
    def test_majority_beats_one_misread(self):
        votes = QueueVote()
        self.assertEqual(votes.observe(list("TSZLI"))[1], "S")
        votes.advance(1)
        self.assertEqual(votes.observe(list("STZLI"))[0], "S")
        votes.advance(1)
        self.assertEqual(votes.observe(list("ZLIOJ"))[0], "Z")

    def test_missing_read_keeps_memory(self):
        votes = QueueVote()
        votes.observe(list("TSZLI"))
        self.assertEqual(votes.observe(["T", None, "Z", "L", "I"])[1], "S")


class PhantomTest(unittest.TestCase):
    def test_extra_cells_cleared(self):
        reference = [0b1] + [0] * 19
        screen = [0b101] + [0] * 19
        extra = extra_cells(screen, reference)
        self.assertEqual(extra, {(0, 2)})
        self.assertEqual(clear_cells(screen, extra), reference)


class BagTest(unittest.TestCase):
    def test_remaining_after_window(self):
        bag = BagTracker()
        bag.update("TIOSZL")
        self.assertEqual(bag.remaining(), ["J"])
        bag.update("IOSZLJ")
        self.assertEqual(bag.remaining(), list("IOTLJSZ"))

    def test_hold_shift(self):
        bag = BagTracker()
        bag.update("TIOSZL")
        bag.update("OSZLJT")
        self.assertTrue(bag.valid)


if __name__ == "__main__":
    unittest.main()
