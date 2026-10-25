import time

from collections import deque

import numpy as np

import calibrate
from game_state import GameState
from palette import is_gray
from ponder import Ponder
from queue_vote import QueueVote
from stack import (ascii_board, best_candidate, clear_cells, count_cells, count_gray, drop_stray_gray,
                   drop_specks, extra_cells, garbage_hole, strip_active, strip_floating_top)
from vision import Reader

RECALIBRATE_AFTER_IDLE = 3.0
RECALIBRATE_INTERVAL = 2.0
GAME_OVER_IDLE = 0.6
MAX_START_CELLS = 8
MEMORY_TOLERANCE = 4
MEMORY_GIVE_UP = 3
PHANTOM_AFTER = 3
SETTLE_SECONDS = 0.14
SETTLE_POLL = 0.012
SETTLE = object()
MEMORY_FAR = 40
TRUST_LIMIT = 2
FAR_GIVE_UP = 5
FALLING_MAX_STACK = 12
SPAWN_CLEAN_WAIT = 0.05
REALIGN_CONFIRM = 2


BLACK = np.zeros(3)


def looks_like_garbage(cells, colors):
    rows = {}
    for r, c in cells:
        if is_gray(colors.get((r, c), BLACK)):
            return True
        rows[r] = rows.get(r, 0) + 1
    return any(n >= 8 for n in rows.values())


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
        self.last_seen = []
        self.finished = deque(maxlen=11)
        self.carry = None
        self.carry_clean = True
        self.path = "quick"
        self.settle_note = ""
        self.spawn_state = "ok"
        self.paths = deque(maxlen=10)
        self.timeouts = 0
        self.ponder = Ponder(engine) if engine is not None and getattr(engine, "supports_ponder", False) \
            and settings["search"].get("ponder") else None

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
        if self.carry is not None:
            frame, previews = self.carry
            self.carry = None
        else:
            frame = self.capture.grab_layout(self.layout)
            previews = self.reader.previews(frame)
            self.carry_clean = True
        if missing(previews) > 1:
            self.on_idle()
            return
        self.idle_since = None
        self.path = "quick"
        self.settle_note = ""
        quick = self.quick_board(frame)
        if quick is not None:
            self.play(frame, quick[0], quick[1], previews)
            return
        self.path = "full"
        frame, rows, colors, previews = self.stable_read(frame, previews)
        self.carry_clean = True
        if missing(previews) > 1:
            return
        state = self.state
        self.sync_current(colors)
        if state.current is None and not self.attach(frame, rows, colors, previews):
            return
        board = self.board_rows(rows, colors, False)
        if board is SETTLE:
            self.path = "settle"
            deadline = time.time() + SETTLE_SECONDS
            while board is SETTLE and time.time() < deadline:
                time.sleep(SETTLE_POLL)
                frame = self.capture.grab_layout(self.layout)
                rows, colors = self.reader.board(frame)
                board = self.board_rows(rows, colors, False)
            if board is SETTLE:
                frame = self.capture.grab_layout(self.layout)
                previews = self.reader.previews(frame)
                if missing(previews) > 1:
                    return
                frame, rows, colors, previews = self.stable_read(frame, previews)
                board = self.board_rows(rows, colors, True)
        if board is not None:
            self.play(frame, colors, board, previews)

    def sync_current(self, colors):
        state = self.state
        if state.current is None:
            return
        height = max((i + 1 for i, row in enumerate(state.memory) if row), default=0)
        if height > FALLING_MAX_STACK:
            return
        seen = self.reader.falling(colors)
        if seen is None or seen == state.current:
            return
        if self.settings.get("trace"):
            print("current piece corrected: %s -> %s" % (state.current, seen), flush=True)
        state.current = seen
        state.votes = QueueVote()
        state.bag.valid = False

    def quick_board(self, frame):
        state = self.state
        if state.current is None or state.pieces == 0 or not state.memory:
            return None
        rows, colors = self.reader.board(frame)
        self.sync_current(colors)
        board = self.board_rows(rows, colors, False, quick=True)
        if board is None or board is SETTLE:
            return None
        return colors, board

    def restart(self):
        if self.ponder:
            self.ponder.discard()
        self.state.reset()
        self.engine.new_game()

    def on_idle(self):
        now = time.time()
        state = self.state
        if self.idle_since is None:
            self.idle_since = now
        else:
            idle = now - self.idle_since
            if idle > GAME_OVER_IDLE and (state.current is not None or state.pieces):
                self.restart()
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

    def stable_read(self, frame, previews):
        current = self.state.current
        rows, colors = self.reader.board(frame)
        a = (frame, rows, colors, previews)
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
            state.hold = self.reader.hold(frame) if count_cells(rows) else None
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
            state.bag.valid = False
            self.engine.mid_game()
            state.hold = self.reader.hold(frame)
            state.join_prev = None
            state.join_notice = False
            return True
        state.join_prev = previews
        time.sleep(0.01)
        return False

    def board_rows(self, rows, colors, settled, quick=False):
        state = self.state
        rows, colors = drop_stray_gray(rows, colors)
        stack = strip_floating_top(strip_active(rows, colors, state.current))
        gray = count_gray(colors) > 0
        if gray and state.pieces > 0:
            state.sees_garbage = True
        if state.pieces > 0 and state.memory:
            stack = self.reconcile(stack, colors, gray, settled)
            if stack is SETTLE:
                return SETTLE
        if state.pieces > 0 and count_cells(state.memory) >= 12 and count_cells(stack) <= 4:
            if quick:
                return None
            self.restart()
            return None
        return stack

    def reconcile(self, stack, colors, gray, settled):
        state = self.state
        expected = (state.memory + [0] * 20)[:20]
        raw = drop_specks(stack)
        stack = clear_cells(raw, state.phantoms)
        diff, candidate, rose = best_candidate(stack, expected, garbage_hole(colors), settled)
        if diff <= MEMORY_TOLERANCE:
            state.bad_streak = 0
            state.trusted = 0
            self.track_phantoms(raw, candidate)
            return candidate
        lost = extra_cells(candidate, stack)
        added = extra_cells(stack, candidate)
        if not lost and diff <= MEMORY_FAR and state.trusted < TRUST_LIMIT and not looks_like_garbage(added, colors):
            state.trusted += 1
            self.trace_diff(diff, rose, lost, added, "animation")
            return candidate
        if not settled:
            if not self.settle_note:
                self.settle_note = "diff=%d lost=%s added=%s" % (diff, sorted(lost)[:4], sorted(added)[:4])
            return SETTLE
        self.trace_diff(diff, rose, lost, added, "mismatch")
        if gray and state.sees_garbage:
            return stack
        state.bad_streak += 1
        if state.bad_streak < (MEMORY_GIVE_UP if diff <= MEMORY_FAR else FAR_GIVE_UP):
            return expected
        return stack

    def trace_diff(self, diff, rose, lost, added, kind):
        if not self.settings.get("trace"):
            return
        print("screen %s: %d cells%s missing=%s extra=%s" % (
            kind, diff, " (garbage rise)" if rose else "", sorted(lost)[:8], sorted(added)[:8]), flush=True)

    def track_phantoms(self, raw, candidate):
        state = self.state
        counts = {cell: state.phantom_counts.get(cell, 0) + 1 for cell in extra_cells(raw, candidate)}
        state.phantom_counts = counts
        state.phantoms = {cell for cell, n in counts.items() if n >= PHANTOM_AFTER}

    def bag_after(self, queue):
        if len(queue) != 6:
            return None
        self.state.bag.update(queue)
        remaining = self.state.bag.remaining()
        return "".join(remaining) if remaining else None

    def pondered(self, stack, queue, incoming, hole):
        if self.ponder is None:
            return None
        state = self.state
        rows = tuple(stack[:20])
        hole = hole if incoming else None

        def accepts(key):
            kept_rows, hold, ahead, b2b, combo, kept_incoming, kept_hole = key
            return (kept_incoming == incoming and kept_hole == hole and kept_rows == rows and hold == state.hold
                    and queue.startswith(ahead) and b2b == state.b2b and combo == state.combo)

        return self.ponder.take(accepts)

    def start_ponder(self, move, hold_after, next_piece, rest, bag, incoming, hole):
        if self.ponder is None or not next_piece or not all(rest):
            return
        ahead = next_piece + "".join(rest)
        if len(ahead) < 5:
            return
        incoming = max(0, incoming - move.attack)
        hole = hole if incoming else None
        key = (tuple((move.after + [0] * 20)[:20]), hold_after, ahead, move.b2b, move.combo, incoming, hole)
        request = dict(rows=list(move.after), hold=hold_after, queue=ahead, b2b=move.b2b, combo=move.combo,
                       incoming=incoming, hole=hole, bag=bag)
        self.ponder.start(key, request)

    def play(self, frame, colors, stack, previews):
        state = self.state
        previews = state.votes.observe(previews, guard=not self.carry_clean)
        full = stack[:20] + [state.memory[i] if i < len(state.memory) else 0 for i in range(20, 40)]
        queue = state.current + "".join(p or "" for p in previews)
        incoming, hole = 0, None
        if self.settings.get("garbage"):
            incoming, hole = self.reader.incoming(frame), garbage_hole(colors)
        bag = self.bag_after(queue)
        started = time.time()
        waited = (started - self.finished[-1]) * 1000 if self.finished else 0
        move = self.pondered(stack, queue, incoming, hole)
        hit = move is not None
        if move is None:
            move = self.engine.ask(full, state.hold, queue, state.b2b, state.combo, incoming, hole, bag)
        thought = time.time()
        if move is None:
            self.on_dead()
            return
        if move.use_hold and state.hold is None:
            hold_after, next_piece, consumed = state.current, previews[1], 2
        elif move.use_hold:
            hold_after, next_piece, consumed = state.current, previews[0], 1
        else:
            hold_after, next_piece, consumed = state.hold, previews[0], 1
        state.votes.advance(consumed)
        self.start_ponder(move, hold_after, next_piece, previews[consumed:], bag, incoming, hole)
        self.keys.run(move)
        pressed = time.time()
        state.pieces += 1
        state.hold = hold_after
        state.b2b = move.b2b
        state.combo = move.combo
        state.memory = move.after
        landed = self.wait_for_spawn(previews[consumed:], previews, consumed)
        if not landed:
            shifted = self.resync(previews, consumed)
            if shifted != consumed:
                consumed = shifted
                next_piece = previews[consumed - 1]
                state.votes = QueueVote()
        self.finished.append(time.time())
        self.paths.append(self.path)
        if self.spawn_state == "TIMEOUT":
            self.timeouts += 1
        if self.settings.get("trace"):
            note = " path=%s%s" % (self.path, " (%s)" % self.settle_note if self.settle_note else "")
            print("piece %s hold=%d keys=%s read=%dms think=%dms%s press=%dms spawn=%dms %s seen=%s expected=%s incoming=%d%s" % (
                move.piece, move.use_hold, ",".join(move.keys), waited, (thought - started) * 1000,
                " (ponder)" if hit else "", (pressed - thought) * 1000, (time.time() - pressed) * 1000, self.spawn_state,
                "".join(p or "?" for p in self.last_seen), "".join(p or "?" for p in previews[consumed:]), incoming,
                note if self.path != "quick" else ""), flush=True)
        state.current = next_piece
        if self.settings.get("trace") and len(self.finished) == 11 and state.pieces % 10 == 0:
            quick = sum(1 for p in self.paths if p == "quick")
            print("speed: %.2f pieces/s over the last 10 | quick reads %d/10 | spawn timeouts so far %d" % (
                10.0 / (self.finished[-1] - self.finished[0]), quick, self.timeouts), flush=True)

    def on_dead(self):
        self.dead_notices += 1
        if self.dead_notices <= 3:
            print("The engine sees no valid move for this board.")
        if self.ponder:
            self.ponder.discard()
        self.state.memory = []
        self.state.pieces = 0
        self.state.votes = QueueVote()
        self.engine.new_game()
        time.sleep(0.4)

    def resync(self, before, consumed):
        seen = self.last_seen
        if len(seen) < 5 or None in seen[:3]:
            return consumed
        for shift in (1, 2):
            if before[shift:shift + 3] == seen[:3] and shift != consumed:
                print("Queue advanced by %d, not %d: realigning." % (shift, consumed), flush=True)
                return shift
        return consumed

    def shifted_elsewhere(self, before, seen, consumed):
        if before is None or None in seen[:3]:
            return False
        return any(before[shift:shift + 3] == seen[:3] for shift in (1, 2) if shift != consumed)

    def wait_for_spawn(self, expected, before=None, consumed=1):
        deadline = time.time() + self.settings["timing"]["spawn_timeout_ms"] / 1000.0
        tolerance = 1 if len(expected) >= 4 else 0
        fallback, fallback_until, realign = None, 0.0, 0
        self.spawn_state = "ok"
        while time.time() < deadline:
            frame = self.capture.grab_layout(self.layout)
            seen = self.reader.previews(frame)
            self.last_seen = seen
            hits = sum(1 for x, y in zip(seen, expected) if x == y)
            now = time.time()
            if seen[0] == expected[0] and hits >= len(expected) - tolerance:
                if hits == len(expected):
                    self.carry, self.carry_clean = (frame, seen), True
                    return True
                if fallback is None:
                    fallback_until = now + SPAWN_CLEAN_WAIT
                fallback = (frame, seen)
                if now >= fallback_until:
                    break
            elif self.shifted_elsewhere(before, seen, consumed):
                realign += 1
                if realign >= REALIGN_CONFIRM:
                    self.spawn_state = "REALIGN"
                    return False
            else:
                realign = 0
            time.sleep(0.004)
        if fallback is not None:
            self.carry, self.carry_clean = fallback, False
            return True
        self.spawn_state = "TIMEOUT"
        return False
