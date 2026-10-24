import time

import calibrate
from game_state import GameState
from stack import (ascii_board, bit_difference, count_cells, count_gray,
                   garbage_hole, strip_active, strip_floating_top)
from vision import Reader

RECALIBRATE_AFTER_IDLE = 3.0
RECALIBRATE_INTERVAL = 2.0
GAME_OVER_IDLE = 0.6
MAX_START_CELLS = 8
MEMORY_TOLERANCE = 4
MEMORY_GIVE_UP = 5
MEMORY_FAR = 40


def missing(previews):
    return sum(p is None for p in previews)


class Session:
    def __init__(self, settings, capture, engine, keys, controls, watch=False):
        self.settings = settings
        self.capture = capture
        self.engine = engine
        self.keys = keys
        self.controls = controls
        self.watch = watch
        self.layout = None
        self.reader = None
        self.state = GameState()
        self.idle_since = None
        self.last_recalibration = 0.0
        self.dead_notices = 0

    def use_layout(self, layout):
        self.layout = layout
        self.reader = Reader(layout, self.settings["palette"], self.settings["fill_threshold"])

    def find_layout(self):
        return calibrate.find_layout(self.capture, self.settings["palette"], self.settings["fill_threshold"])

    def signal(self):
        return self.controls.poll() if self.controls else None

    def wait_for_layout(self):
        print("Looking for the game board. Open a game and keep the board visible.")
        attempts = 0
        while True:
            if self.signal() == "stop":
                return False
            found = self.find_layout()
            if found:
                self.use_layout(found)
                print("Calibrated: board %s, next %s, hold %s" % (found.board, found.next, found.hold or "-"))
                return True
            attempts += 1
            if attempts % 20 == 0:
                print("  still looking...")
            time.sleep(0.4)

    def run(self):
        if not self.wait_for_layout():
            return
        if self.watch:
            return self.show()
        print("Running. Stop: mouse in the top-left corner. Pause: top-right corner.")
        while True:
            signal = self.signal()
            if signal == "stop":
                break
            if signal == "pause":
                time.sleep(0.1)
                continue
            self.step()

    def show(self):
        while True:
            frame = self.capture.grab_layout(self.layout)
            rows, colors = self.reader.board(frame)
            previews = self.reader.previews(frame)
            print("\033[2J\033[H" + ascii_board(rows))
            print("\nnext:", " ".join(p or "?" for p in previews), "| top piece:", self.reader.active(colors) or "?",
                  "| incoming:", self.reader.incoming(frame), "| garbage hole:", garbage_hole(colors))
            time.sleep(0.1)

    def step(self):
        frame = self.capture.grab_layout(self.layout)
        previews = self.reader.previews(frame)
        if missing(previews) > 1:
            self.on_idle()
            return
        self.idle_since = None
        frame, rows, colors, previews = self.stable_read()
        if missing(previews) > 1:
            return
        state = self.state
        if state.current is None and not self.attach(frame, rows, colors, previews):
            return
        board = self.board_rows(rows, colors)
        if board is not None:
            self.play(frame, colors, board, previews)

    def on_idle(self):
        now = time.time()
        state = self.state
        if self.idle_since is None:
            self.idle_since = now
        else:
            idle = now - self.idle_since
            if idle > GAME_OVER_IDLE and (state.current is not None or state.pieces):
                state.reset()
                print("Game over, waiting for the next one...")
            if idle > RECALIBRATE_AFTER_IDLE and now - self.last_recalibration > RECALIBRATE_INTERVAL:
                self.last_recalibration = now
                found = self.find_layout()
                if found and found != self.layout:
                    self.use_layout(found)
                    print("Recalibrated: board %s" % (found.board,))
        time.sleep(0.05)

    def read_once(self):
        frame = self.capture.grab_layout(self.layout)
        rows, colors = self.reader.board(frame)
        return frame, rows, colors, self.reader.previews(frame)

    def stable_read(self):
        current = self.state.current
        a = self.read_once()
        for _ in range(4):
            time.sleep(0.012)
            b = self.read_once()
            if strip_active(a[1], a[2], current) == strip_active(b[1], b[2], current) and a[3] == b[3]:
                return b
            a = b
        return a

    def attach(self, frame, rows, colors, previews):
        state = self.state
        if count_cells(rows) <= MAX_START_CELLS:
            state.current = self.reader.active(colors)
            state.hold = self.reader.hold(frame)
            if state.current is None:
                time.sleep(0.01)
                return False
            return True
        if not state.join_notice:
            print("Game already running: waiting for the next piece to join...")
            state.join_notice = True
        joined = state.join_prev
        if joined is not None and previews[:4] == joined[1:5] and joined[0]:
            state.current = joined[0]
            state.hold = self.reader.hold(frame)
            state.join_prev = None
            state.join_notice = False
            return True
        state.join_prev = previews
        time.sleep(0.01)
        return False

    def board_rows(self, rows, colors):
        state = self.state
        stack = strip_floating_top(strip_active(rows, colors, state.current))
        if count_gray(colors) > 0 and state.pieces > 0:
            state.sees_garbage = True
        if not state.sees_garbage and state.pieces > 0:
            expected = (state.memory + [0] * 20)[:20]
            diff = bit_difference(stack, expected)
            if diff <= MEMORY_TOLERANCE:
                stack, state.bad_streak = expected, 0
            else:
                state.bad_streak += 1
                if state.bad_streak < MEMORY_GIVE_UP or diff > MEMORY_FAR:
                    stack = expected
        if state.pieces > 0 and count_cells(state.memory) >= 12 and count_cells(stack) <= 4:
            state.reset()
            return None
        return stack

    def play(self, frame, colors, stack, previews):
        state = self.state
        full = stack[:20] + [state.memory[i] if i < len(state.memory) else 0 for i in range(20, 40)]
        queue = state.current + "".join(p or "" for p in previews)
        move = self.engine.ask(full, state.hold, queue, state.b2b, state.combo,
                               self.reader.incoming(frame), garbage_hole(colors))
        if move is None:
            self.on_dead()
            return
        self.keys.run(move)
        state.pieces += 1
        if move.use_hold and state.hold is None:
            state.hold, next_piece, consumed = state.current, previews[1], 2
        elif move.use_hold:
            state.hold, next_piece, consumed = state.current, previews[0], 1
        else:
            next_piece, consumed = previews[0], 1
        state.b2b = move.b2b
        state.combo = move.combo
        state.memory = move.after
        self.wait_for_spawn(previews[consumed:])
        state.current = next_piece

    def on_dead(self):
        self.dead_notices += 1
        if self.dead_notices <= 3:
            print("The engine sees no valid move for this board.")
        self.state.memory = []
        self.state.pieces = 0
        time.sleep(0.4)

    def wait_for_spawn(self, expected):
        deadline = time.time() + self.settings["timing"]["spawn_timeout_ms"] / 1000.0
        tolerance = 1 if len(expected) >= 4 else 0
        while time.time() < deadline:
            seen = self.reader.previews(self.capture.grab_layout(self.layout))
            hits = sum(1 for x, y in zip(seen, expected) if x == y)
            if hits >= len(expected) - tolerance and seen[0] == expected[0]:
                return
            time.sleep(0.004)
