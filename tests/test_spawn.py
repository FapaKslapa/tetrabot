import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

import settings as settings_mod
from palette import DEFAULT_PALETTE
from queue_vote import QueueVote
from session import Session
from vision import Reader


class Script:
    def __init__(self, frames):
        self.frames = list(frames)
        self.last = self.frames[-1]

    def next(self):
        return self.frames.pop(0) if self.frames else self.last


class ScriptedCapture:
    def __init__(self, script):
        self.script = script

    def grab_layout(self, layout):
        return self.script.next()


class ScriptedReader:
    def previews(self, frame):
        return list(frame)


def session_with(frames, timeout_ms=300):
    settings = settings_mod.load()
    settings["trace"] = False
    settings["timing"]["spawn_timeout_ms"] = timeout_ms
    s = Session(settings, ScriptedCapture(Script(frames)), None, None, None)
    s.reader = ScriptedReader()
    s.layout = object()
    return s


class SpawnTest(unittest.TestCase):
    def test_clean_frame_is_accepted_at_once(self):
        s = session_with([list("ISTZL")])
        self.assertTrue(s.wait_for_spawn(list("ISTZ"), list("OISTZ"), 1))
        self.assertTrue(s.carry_clean)

    def test_stale_slot_waits_for_a_clean_frame(self):
        s = session_with([list("ISTSL"), list("ISTZL")])
        self.assertTrue(s.wait_for_spawn(list("ISTZ"), list("OISTZ"), 1))
        self.assertTrue(s.carry_clean)
        self.assertEqual(s.carry[1], list("ISTZL"))

    def test_persistent_stale_slot_is_accepted_but_marked_dirty(self):
        s = session_with([list("ISTSL")])
        started = time.time()
        self.assertTrue(s.wait_for_spawn(list("ISTZ"), list("OISTZ"), 1))
        self.assertFalse(s.carry_clean)
        self.assertLess(time.time() - started, 0.25)

    def test_wrong_vote_realigns_without_waiting_for_the_timeout(self):
        s = session_with([list("ISTZL")], timeout_ms=1500)
        started = time.time()
        landed = s.wait_for_spawn(list("JIST"), list("OJISTZ"), 1)
        self.assertFalse(landed)
        self.assertEqual(s.spawn_state, "REALIGN")
        self.assertLess(time.time() - started, 0.3)

    def test_nothing_matching_times_out(self):
        s = session_with([list("JJJJJ")], timeout_ms=60)
        self.assertFalse(s.wait_for_spawn(list("ISTZ"), list("OISTZ"), 1))
        self.assertEqual(s.spawn_state, "TIMEOUT")

    def test_old_queue_is_not_a_spawn(self):
        s = session_with([list("OISTZ")], timeout_ms=60)
        self.assertFalse(s.wait_for_spawn(list("ISTZ"), list("OISTZ"), 1))
        self.assertEqual(s.spawn_state, "TIMEOUT")


class FallingReader:
    def __init__(self, piece):
        self.piece = piece

    def falling(self, colors):
        return self.piece


class SyncTest(unittest.TestCase):
    def make(self, current, seen):
        s = session_with([list("OISTZ")])
        s.reader = FallingReader(seen)
        s.state.current = current
        s.state.votes.observe(list("OISTZ"))
        return s

    def test_wrong_current_is_replaced_by_the_falling_piece(self):
        s = self.make("J", "T")
        s.sync_current({})
        self.assertEqual(s.state.current, "T")
        self.assertEqual(s.state.votes.slots, [])
        self.assertFalse(s.state.bag.valid)

    def test_tall_stack_is_never_mistaken_for_the_falling_piece(self):
        s = self.make("J", "T")
        s.state.memory = [0b1111111011] * 15 + [0] * 25
        s.sync_current({})
        self.assertEqual(s.state.current, "J")
        self.assertEqual(len(s.state.votes.slots), 5)

    def test_matching_or_unreadable_piece_changes_nothing(self):
        for seen in ("J", None):
            s = self.make("J", seen)
            s.sync_current({})
            self.assertEqual(s.state.current, "J")
            self.assertEqual(len(s.state.votes.slots), 5)


def cells(letter, positions):
    return {pos: tuple(DEFAULT_PALETTE[letter]) for pos in positions}


class FallingTest(unittest.TestCase):
    def reader(self):
        return Reader(None, DEFAULT_PALETTE, 95)

    def test_piece_at_the_top_is_read(self):
        colors = cells("T", [(19, 4), (18, 3), (18, 4), (18, 5)])
        colors.update(cells("S", [(0, 1), (0, 2), (1, 2), (1, 3)]))
        self.assertEqual(self.reader().falling(colors), "T")

    def test_low_cells_are_not_a_falling_piece(self):
        colors = cells("T", [(9, 4), (8, 3), (8, 4), (8, 5)])
        self.assertIsNone(self.reader().falling(colors))

    def test_scattered_top_cells_are_rejected(self):
        colors = cells("I", [(19, 0), (19, 9), (18, 0), (18, 9)])
        self.assertIsNone(self.reader().falling(colors))

    def test_mixed_colours_are_rejected(self):
        colors = cells("T", [(19, 4), (18, 4)])
        colors.update(cells("S", [(18, 3)]))
        colors.update(cells("Z", [(18, 5)]))
        self.assertIsNone(self.reader().falling(colors))


class VoteGuardTest(unittest.TestCase):
    def test_guarded_read_does_not_override_the_majority(self):
        votes = QueueVote()
        votes.observe(list("TSZLI"))
        votes.observe(list("TSZLI"))
        self.assertEqual(votes.observe(list("TSSLI"), guard=True)[2], "Z")
        self.assertEqual(votes.slots[2]["counts"], {"Z": 2})

    def test_guard_still_fills_empty_slots(self):
        votes = QueueVote()
        self.assertEqual(votes.observe(list("TSZLI"), guard=True), list("TSZLI"))


if __name__ == "__main__":
    unittest.main()
