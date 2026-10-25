PIECES = "IOTLJSZ"


class BagTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.sequence = []
        self.last = None
        self.valid = True

    def update(self, queue_text):
        if self.last is None:
            self.sequence = list(queue_text)
        else:
            shift = next((k for k in (1, 2) if self.last[k:] == queue_text[:len(self.last) - k]), None)
            if shift is None:
                self.valid = False
            else:
                self.sequence += list(queue_text[len(queue_text) - shift:])
        self.last = queue_text

    def remaining(self):
        if not self.valid:
            return None
        n = len(self.sequence)
        drawn = self.sequence[n - n % 7:]
        if len(set(drawn)) != len(drawn):
            self.valid = False
            return None
        return [p for p in PIECES if p not in drawn]
