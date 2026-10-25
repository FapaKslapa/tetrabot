import os
import sys

import mss

_state = {}


def _load():
    if not _state:
        if sys.platform.startswith("win"):
            import ctypes
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        from pynput import keyboard, mouse
        _state["keys"] = keyboard
        _state["keyboard"] = keyboard.Controller()
        _state["mouse"] = mouse.Controller()
    return _state


def _key(name):
    keyboard = _load()["keys"]
    special = getattr(keyboard.Key, name, None)
    return special if special is not None else keyboard.KeyCode.from_char(name)


def press(name, down):
    controller = _load()["keyboard"]
    if down:
        controller.press(_key(name))
    else:
        controller.release(_key(name))


def mouse_position():
    return _load()["mouse"].position


def screen_width():
    with mss.mss() as sct:
        return sct.monitors[1]["width"]


def check_permissions(need_keys):
    if sys.platform.startswith("linux"):
        if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
            print("Wayland sessions block screen capture and key injection.")
            print("Log in with an X11 session and run again.")
            return False
        if not os.environ.get("DISPLAY"):
            print("No DISPLAY found: run this inside a graphical X11 session.")
            return False
    try:
        _load()
    except Exception as error:
        print("Could not start keyboard and mouse control: %s" % error)
        return False
    return True
