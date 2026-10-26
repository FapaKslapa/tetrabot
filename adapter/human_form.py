class Form:
    def __init__(self, rng, cfg):
        self.rng = rng
        self.cfg = cfg
        self.value = 0.0
        self.touch = 0.0

    def step(self):
        self.value = min(1.0, max(-1.0, 0.97 * self.value + self.rng.gauss(0, 0.12)))

    def step_touch(self):
        self.touch = 0.7 * self.touch + self.rng.gauss(0, 0.09)
        return self.touch

    def pace(self):
        return 1.0 - self.cfg["form_tempo"] * self.value

    def chance_scale(self):
        return min(1.6, max(0.4, 1.0 - self.cfg["form_chance"] * self.value))

    def mistake_scale(self):
        return min(1.6, max(0.4, 1.0 - self.cfg["form_mistakes"] * self.value))
