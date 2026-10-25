import sys


def load():
    if sys.platform == "darwin":
        from backends import mac
        return mac
    from backends import desktop
    return desktop
