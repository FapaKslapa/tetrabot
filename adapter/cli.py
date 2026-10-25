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
    ap.add_argument("--trace", action="store_true", help="print timing and reading details for every piece")
    ap.add_argument("--engine", choices=["cc2", "beam"], default="beam",
                    help="beam: built-in beam search (default); cc2: Cold Clear 2 chooses moves")
    ap.add_argument("--think", type=int, help="Cold Clear 2 thinking time per move in milliseconds")
    ap.add_argument("--keep-tree", action="store_true", help="keep the Cold Clear search running between moves")
    ap.add_argument("--sd", action="store_true", help="allow soft drop in key paths (needs SDF = infinity)")
    ap.add_argument("--no-ponder", action="store_true", help="do not think about the next piece while keys are pressed")
    return ap.parse_args()
