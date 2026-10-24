import argparse


def parse_args():
    ap = argparse.ArgumentParser(description="Screen-reading front end for the tetrabot engine")
    ap.add_argument("--watch", action="store_true", help="show what is read from the screen, press nothing")
    ap.add_argument("--dry", action="store_true", help="compute moves but press nothing")
    ap.add_argument("--countdown", type=int, default=5, help="seconds to switch to the browser")
    ap.add_argument("--depth", type=int, help="search depth in pieces")
    ap.add_argument("--width", type=int, help="beam width")
    ap.add_argument("--settings", help="JSON file overriding keys, timing and search settings")
    ap.add_argument("--garbage", action="store_true", help="read the incoming garbage meter and plan for it")
    ap.add_argument("--sd", action="store_true", help="allow soft drop in key paths (needs SDF = infinity)")
    return ap.parse_args()
