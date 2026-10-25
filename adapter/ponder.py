import threading


class Ponder:
    def __init__(self, engine):
        self.engine = engine
        self.thread = None
        self.key = None
        self.result = None

    def start(self, key, request):
        self.discard()
        self.key = key
        self.result = None
        self.thread = threading.Thread(target=self.work, args=(request,), daemon=True)
        self.thread.start()

    def work(self, request):
        self.result = self.engine.ask(**request)

    def take(self, accepts):
        if self.thread is None:
            return None
        self.thread.join()
        self.thread = None
        key, result = self.key, self.result
        self.key, self.result = None, None
        return result if accepts(key) else None

    def discard(self):
        self.take(lambda key: False)
