import time

from session_constants import REALIGN_CONFIRM, SPAWN_CLEAN_WAIT


class SessionSpawn:
    def wait_fall(self, rows, timeout):
        start, last, dropped = time.time(), None, 0
        while time.time() - start < timeout:
            frame = self.capture.grab_layout(self.layout)
            _, colors = self.reader.board(frame)
            cells = sorted(colors.items(), key=lambda kv: -kv[0][0])[:4]
            if len(cells) == 4:
                seen = tuple(sorted(rc for rc, _ in cells))
                if last is not None and seen != last and sum(r for r, _ in seen) < sum(r for r, _ in last):
                    dropped += 1
                    if dropped >= rows:
                        return (time.time() - start) * 1000.0
                last = seen
            time.sleep(0.006)
        return None

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
