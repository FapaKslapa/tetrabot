import sys


def _quartz():
    import Quartz
    return Quartz


def accessibility_allowed():
    try:
        from ApplicationServices import AXIsProcessTrusted
        return bool(AXIsProcessTrusted())
    except Exception:
        return True


def screen_capture_allowed():
    try:
        return bool(_quartz().CGPreflightScreenCaptureAccess())
    except Exception:
        return True


def mouse_position():
    q = _quartz()
    loc = q.CGEventGetLocation(q.CGEventCreate(None))
    return loc.x, loc.y


def main_display_width():
    q = _quartz()
    return q.CGDisplayBounds(q.CGMainDisplayID()).size.width


class Controls:
    def __init__(self):
        self.width = main_display_width()

    def poll(self):
        x, y = mouse_position()
        if x <= 3 and y <= 3:
            return "stop"
        if x >= self.width - 4 and y <= 3:
            return "pause"
        return None


def check_permissions(need_keys):
    ok = True
    if not screen_capture_allowed():
        print("Screen Recording permission is missing for this terminal app.")
        print("System Settings > Privacy & Security > Screen Recording")
        ok = False
    if need_keys and not accessibility_allowed():
        print("Accessibility permission is missing for this terminal app.")
        print("System Settings > Privacy & Security > Accessibility")
        ok = False
    if not ok:
        print("Enable it, quit the terminal with Cmd+Q, reopen it and run again.")
    return ok


if __name__ == "__main__":
    sys.exit(0 if check_permissions(True) else 1)
