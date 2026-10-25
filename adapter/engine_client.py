import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class Move:
    piece: str
    use_hold: bool
    keys: List[str]
    after: List[int]
    b2b: int
    combo: int
    attack: int
    lines: int


def parse_move(line):
    parts = line.strip().split()
    if not parts or parts[0] != "MOVE":
        return None
    kv = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
    keys = [] if kv.get("keys", "-") == "-" else kv["keys"].split(",")
    after = [int(x) for x in kv["after"].split(",") if x != ""]
    return Move(kv["piece"], kv["use_hold"] == "1", keys, after,
                int(kv["b2b"]), int(kv["combo"]), int(kv["attack"]), int(kv["lines"]))


class Engine:
    supports_ponder = True

    def __init__(self, binary, root, depth, width, no_soft_drop, threads=1):
        cmd = [binary, "serve", "--depth", str(depth), "--width", str(width)]
        if no_soft_drop:
            cmd.append("--nosd")
        if threads > 1:
            cmd += ["--threads", str(threads)]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, bufsize=1, cwd=root)

    def ask(self, rows, hold, queue, b2b, combo, incoming=0, hole=None, bag=None):
        request = "rows=%s hold=%s queue=%s b2b=%s combo=%d incoming=%d" % (
            ",".join(str(r) for r in rows), hold or "-", queue, b2b, combo, incoming)
        if hole is not None:
            request += " hole=%d" % hole
        if bag:
            request += " bag=%s" % bag
        request += "\n"
        self.proc.stdin.write(request)
        self.proc.stdin.flush()
        return parse_move(self.proc.stdout.readline())

    def place(self, rows, piece, cells, spin, b2b, combo):
        request = "rows=%s piece=%s cells=%s spin=%s b2b=%s combo=%d\n" % (
            ",".join(str(r) for r in rows), piece, cells, spin, b2b, combo)
        self.proc.stdin.write(request)
        self.proc.stdin.flush()
        return parse_move(self.proc.stdout.readline())

    def new_game(self):
        pass

    def mid_game(self):
        pass

    def close(self):
        self.proc.terminate()
