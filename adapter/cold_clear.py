import json
import queue
import subprocess
import threading
import time

from bag import BagTracker
from stack import MAX_RISE, raise_rows

BASE = {
    "I": [(-1, 0), (0, 0), (1, 0), (2, 0)],
    "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T": [(-1, 0), (0, 0), (1, 0), (0, 1)],
    "L": [(-1, 0), (0, 0), (1, 0), (1, 1)],
    "J": [(-1, 0), (0, 0), (1, 0), (-1, 1)],
    "S": [(-1, 0), (0, 0), (0, 1), (1, 1)],
    "Z": [(-1, 1), (0, 1), (0, 0), (1, 0)],
}
TURNS = {
    "north": lambda x, y: (x, y),
    "east": lambda x, y: (y, -x),
    "south": lambda x, y: (-x, -y),
    "west": lambda x, y: (-y, x),
}


def tbp_cells(location):
    turn = TURNS[location["orientation"]]
    return [(location["x"] + dx, location["y"] + dy)
            for dx, dy in (turn(*cell) for cell in BASE[location["type"]])]


def tbp_board(rows):
    return [[("G" if (rows[y] >> x) & 1 else None) for x in range(10)] for y in range(40)]


class ColdClear:
    def __init__(self, binary, root, engine, think_ms=60, keep_tree=False, garbage=False, config=None):
        self.engine = engine
        self.keep = keep_tree
        self.garbage = garbage
        self.expected = None
        self.think = think_ms / 1000.0
        self.bag = BagTracker()
        self.inbox = queue.Queue()
        self.proc = subprocess.Popen([binary] + ((["--config", config]) if config else []), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, bufsize=1, cwd=root)
        threading.Thread(target=self.read_loop, daemon=True).start()

    def read_loop(self):
        for line in self.proc.stdout:
            try:
                self.inbox.put(json.loads(line))
            except ValueError:
                continue

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def new_game(self):
        self.bag.reset()
        self.expected = None

    def mid_game(self):
        self.bag.valid = False
        self.expected = None

    def continues(self, rows, hold, queue_text, b2b, combo):
        if not self.keep or self.expected is None:
            return False
        want_rows, want_hold, known, want_b2b, want_combo = self.expected
        return (list(rows) == want_rows and hold == want_hold and b2b == want_b2b
                and combo == want_combo and queue_text[:len(known)] == known)

    def begin(self, rows, hold, queue_text, b2b, combo):
        start = {"type": "start", "hold": hold, "queue": list(queue_text), "combo": int(combo),
                 "back_to_back": bool(b2b), "board": tbp_board(rows)}
        remaining = self.bag.remaining()
        if remaining is not None:
            start["randomizer"] = {"type": "seven_bag", "bag_state": remaining}
        self.send({"type": "stop"})
        self.send(start)
        time.sleep(self.think)

    def suggestion(self, timeout):
        deadline = time.time() + timeout
        while time.time() < deadline:
            while not self.inbox.empty():
                self.inbox.get_nowait()
            self.send({"type": "suggest"})
            end = time.time() + 0.25
            while time.time() < end:
                try:
                    message = self.inbox.get(timeout=0.05)
                except queue.Empty:
                    continue
                if message.get("type") == "suggestion":
                    return message["moves"]
        return None

    def ask(self, rows, hold, queue_text, b2b, combo, incoming=0, hole=None, bag=None):
        self.bag.update(queue_text)
        lift = min(int(incoming), MAX_RISE) if self.garbage else 0
        move = self.plan(rows, hold, queue_text, b2b, combo, lift, hole or 0) if lift else None
        if move is None:
            move = self.plan(rows, hold, queue_text, b2b, combo, 0, 0)
        return move

    def plan(self, rows, hold, queue_text, b2b, combo, lift, hole):
        if lift:
            self.expected = None
            self.begin(raise_rows(rows, lift, hole), hold, queue_text, b2b, combo)
        elif self.continues(rows, hold, queue_text, b2b, combo):
            for piece in queue_text[len(self.expected[2]):]:
                self.send({"type": "new_piece", "piece": piece})
        else:
            self.begin(rows, hold, queue_text, b2b, combo)
        self.expected = None
        moves = self.suggestion(2.0 if not lift else 0.6)
        for best in moves or []:
            location = tbp_cells(best["location"])
            if any(y - lift < 0 for _, y in location):
                continue
            piece = best["location"]["type"]
            cells = ",".join("%d:%d" % (x, y - lift) for x, y in location)
            move = self.engine.place(rows, piece, cells, best.get("spin", "none"), b2b, combo)
            if move is None:
                continue
            move.use_hold = piece != queue_text[0]
            if self.keep and not lift:
                self.advance(best, move, hold, queue_text)
            return move
        return None

    def advance(self, best, move, hold, queue_text):
        self.send({"type": "play", "move": best})
        consumed = 2 if move.use_hold and hold is None else 1
        new_hold = queue_text[0] if move.use_hold else hold
        self.expected = ((move.after + [0] * 40)[:40], new_hold, queue_text[consumed:], move.b2b, move.combo)

    def close(self):
        self.proc.terminate()
        self.engine.close()
