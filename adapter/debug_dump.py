import os
import struct
import time
import zlib

import numpy as np

DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "debug")
MAX_DUMPS = 8


def chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def png_bytes(img):
    img = np.ascontiguousarray(img[:, :, :3], dtype=np.uint8)
    height, width = img.shape[:2]
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")


class Dumper:
    def __init__(self, directory=DEBUG_DIR, limit=MAX_DUMPS):
        self.directory = directory
        self.limit = limit
        self.count = 0

    def save(self, frame, tag, text=""):
        if self.count >= self.limit or frame is None:
            return None
        os.makedirs(self.directory, exist_ok=True)
        stamp = time.strftime("%H%M%S")
        base = os.path.join(self.directory, "%s-%s-%d" % (stamp, tag, self.count))
        with open(base + ".png", "wb") as handle:
            handle.write(png_bytes(frame.img))
        with open(base + ".txt", "w") as handle:
            handle.write(text)
        self.count += 1
        return base
