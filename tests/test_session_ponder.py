import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "adapter"))

import settings as settings_mod
from engine_client import Engine
from session import Session

BINARY = os.path.join(ROOT, "target", "release", "tetrabot")


class FakeKeys:
    def run(self, move):
        pass


class FakeCapture:
    def grab_layout(self, layout):
        return None


class FakeReader:
    def __init__(self):
        self.shown = ["O", "S", "Z", "L", "J"]
        self.meter = 0

    def previews(self, frame):
        return list(self.shown)

    def falling(self, colors):
        return None

    def incoming(self, frame):
        return self.meter


@unittest.skipUnless(os.path.exists(BINARY), "engine binary not built")
class SessionPonderTest(unittest.TestCase):
    def test_second_move_uses_ponder(self):
        settings = settings_mod.load()
        settings["trace"] = False
        settings["timing"]["spawn_timeout_ms"] = 50
        engine = Engine(BINARY, ROOT, 4, 20, True)
        self.asks = 0
        original = engine.ask

        def counted(*args, **kwargs):
            self.asks += 1
            return original(*args, **kwargs)

        engine.ask = counted
        session = Session(settings, FakeCapture(), engine, FakeKeys(), None)
        session.reader = FakeReader()
        session.layout = object()
        state = session.state
        state.current = "T"
        stack = [0] * 20
        previews = ["O", "S", "Z", "L", "J"]
        session.play(None, {}, stack, previews)
        self.assertEqual(state.pieces, 1)
        self.assertIsNotNone(session.ponder.thread)
        stack = (state.memory + [0] * 20)[:20]
        session.reader.shown = ["S", "Z", "L", "J", "I"]
        session.play(None, {}, stack, ["S", "Z", "L", "J", "I"])
        self.assertEqual(state.pieces, 2)
        self.assertEqual(self.asks, 3)
        session.ponder.discard()
        engine.close()


    def test_ponder_hits_while_garbage_is_incoming(self):
        settings = settings_mod.load()
        settings["trace"] = False
        settings["garbage"] = True
        settings["timing"]["spawn_timeout_ms"] = 50
        engine = Engine(BINARY, ROOT, 4, 20, True)
        self.asks = 0
        original = engine.ask

        def counted(*args, **kwargs):
            self.asks += 1
            return original(*args, **kwargs)

        engine.ask = counted
        session = Session(settings, FakeCapture(), engine, FakeKeys(), None)
        session.reader = FakeReader()
        session.reader.meter = 3
        session.layout = object()
        state = session.state
        state.current = "T"
        session.play(None, {}, [0] * 20, ["O", "S", "Z", "L", "J"])
        stack = (state.memory + [0] * 20)[:20]
        session.reader.shown = ["S", "Z", "L", "J", "I"]
        session.play(None, {}, stack, ["S", "Z", "L", "J", "I"])
        self.assertEqual(state.pieces, 2)
        self.assertEqual(self.asks, 3)
        session.ponder.discard()
        engine.close()


if __name__ == "__main__":
    unittest.main()
