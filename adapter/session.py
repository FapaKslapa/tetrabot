import time
from collections import deque

import calibrate
from game_state import GameState
from ponder import Ponder
from queue_vote import QueueVote
from session_board import SessionBoard
from session_constants import (GAME_OVER_IDLE, RECALIBRATE_AFTER_IDLE, RECALIBRATE_INTERVAL, SETTLE,
                               SETTLE_POLL, SETTLE_SECONDS, missing)
from session_spawn import SessionSpawn
from stack import ascii_board, garbage_hole
from vision import Reader

class Session(SessionBoard, SessionSpawn):
    def __init__(self, settings, capture, engine, keys, controls, watch=False):
        self.settings = settings
        self.capture = capture
        self.engine = engine
        self.imperfect = None
        self.keys = keys
        if self.keys is not None:
            self.keys.probe = self.wait_fall
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
        if self.imperfect is not None:
            chosen = self.imperfect.maybe(move, full, state.b2b, state.combo, incoming)
            if chosen is not move:
                move = chosen
                if self.settings.get("trace"):
                    print("imperfect: played %s %s off the best placement" % (move.piece, self.imperfect.last), flush=True)
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
            print("piece %s hold=%d keys=%s read=%dms think=%dms%s press=%dms%s spawn=%dms %s seen=%s expected=%s incoming=%d%s" % (
                move.piece, move.use_hold, ",".join(move.keys), waited, (thought - started) * 1000,
                " (ponder)" if hit else "", (pressed - thought) * 1000,
                " (plan %dms%s)" % (self.keys.planned_ms, " " + self.keys.note if self.keys.note else "")
                if getattr(self.keys, "planned_ms", None) else "",
                (time.time() - pressed) * 1000, self.spawn_state,
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
