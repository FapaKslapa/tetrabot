import os
import sys
import tempfile
import unittest
import zlib
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapter"))

from debug_dump import Dumper, png_bytes


class DumpTest(unittest.TestCase):
    def test_png_round_trip(self):
        img = np.random.RandomState(1).randint(0, 255, (5, 7, 3)).astype(np.uint8)
        data = png_bytes(img)
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        start = data.index(b"IDAT")
        size = int.from_bytes(data[start - 4:start], "big")
        raw = zlib.decompress(data[start + 4:start + 4 + size])
        rows = [np.frombuffer(raw[y * 22 + 1:(y + 1) * 22], dtype=np.uint8).reshape(7, 3) for y in range(5)]
        self.assertTrue((np.stack(rows) == img).all())

    def test_dumper_stops_at_its_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            dumper = Dumper(tmp, 2)
            frame = SimpleNamespace(img=np.zeros((4, 4, 3), dtype=np.uint8))
            for _ in range(5):
                dumper.save(frame, "x", "note")
            self.assertEqual(len([f for f in os.listdir(tmp) if f.endswith(".png")]), 2)
            self.assertIsNone(dumper.save(None, "x"))


if __name__ == "__main__":
    unittest.main()
