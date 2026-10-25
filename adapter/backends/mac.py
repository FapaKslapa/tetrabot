import Quartz
from ApplicationServices import AXIsProcessTrusted

KEYCODES = {"left": 123, "right": 124, "down": 125, "up": 126, "space": 49,
            "z": 6, "x": 7, "c": 8, "a": 0, "shift": 56}


def press(name, down):
    event = Quartz.CGEventCreateKeyboardEvent(None, KEYCODES[name], down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def mouse_position():
    loc = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    return loc.x, loc.y


def screen_width():
    return Quartz.CGDisplayBounds(Quartz.CGMainDisplayID()).size.width


def check_permissions(need_keys):
    ok = True
    try:
        capture_ok = bool(Quartz.CGPreflightScreenCaptureAccess())
    except Exception:
        capture_ok = True
    if not capture_ok:
        print("Screen Recording permission is missing for this terminal app.")
        print("System Settings > Privacy & Security > Screen Recording")
        ok = False
    if need_keys and not bool(AXIsProcessTrusted()):
        print("Accessibility permission is missing for this terminal app.")
        print("System Settings > Privacy & Security > Accessibility")
        ok = False
    if not ok:
        print("Enable it, quit the terminal with Cmd+Q, reopen it and run again.")
    return ok
