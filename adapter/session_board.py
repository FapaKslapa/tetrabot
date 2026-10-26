import time

from queue_vote import QueueVote
from session_constants import (FALLING_MAX_STACK, FAR_GIVE_UP, MAX_START_CELLS, MEMORY_FAR, MEMORY_GIVE_UP,
                               MEMORY_TOLERANCE, PHANTOM_AFTER, SETTLE, TRUST_LIMIT, looks_like_garbage)
from stack import (best_candidate, clear_cells, count_cells, count_gray, drop_specks, drop_stray_gray, extra_cells,
                   garbage_hole, strip_active, strip_floating_top)


class SessionBoard:
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
