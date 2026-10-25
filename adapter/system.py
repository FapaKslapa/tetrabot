import sys

import backends


class Controls:
    def __init__(self):
        self.backend = backends.load()
        self.width = self.backend.screen_width()

    def poll(self):
        x, y = self.backend.mouse_position()
        if x <= 3 and y <= 3:
            return "stop"
        if x >= self.width - 4 and y <= 3:
            return "pause"
        return None


def check_permissions(need_keys):
    return backends.load().check_permissions(need_keys)


if __name__ == "__main__":
    sys.exit(0 if check_permissions(True) else 1)
