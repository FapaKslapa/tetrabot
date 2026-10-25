class QueueVote:
    def __init__(self):
        self.slots = []

    def advance(self, count):
        self.slots = self.slots[count:]

    @staticmethod
    def leader(slot):
        counts = slot["counts"]
        return max(counts, key=lambda p: (counts[p], p == slot["last"])) if counts else None

    def observe(self, previews, guard=False):
        while len(self.slots) < len(previews):
            self.slots.append({"counts": {}, "last": None})
        voted = []
        for slot, piece in zip(self.slots, previews):
            if piece:
                leader = self.leader(slot)
                if not (guard and leader is not None and leader != piece):
                    slot["counts"][piece] = slot["counts"].get(piece, 0) + 1
                    slot["last"] = piece
            voted.append(self.leader(slot))
        return voted
