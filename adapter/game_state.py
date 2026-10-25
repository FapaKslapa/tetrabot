from bag import BagTracker
from queue_vote import QueueVote


class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.current = None
        self.hold = None
        self.b2b = 0
        self.combo = 0
        self.memory = []
        self.pieces = 0
        self.bad_streak = 0
        self.trusted = 0
        self.join_prev = None
        self.join_notice = False
        self.sees_garbage = False
        self.bag = BagTracker()
        self.diff = None
        self.rose = False
        self.votes = QueueVote()
        self.phantom_counts = {}
        self.phantoms = set()
