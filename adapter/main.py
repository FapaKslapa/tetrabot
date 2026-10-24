import os
import sys
import time

import settings as settings_mod
import system
from capture import Capture
from cli import parse_args
from engine_client import Engine
from keys import Keys
from session import Session

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARY = os.path.join(ROOT, "target", "release", "tetrabot")


def countdown(seconds):
    for i in range(seconds, 0, -1):
        print("Switch to the browser: %d..." % i, flush=True)
        time.sleep(1)


def main():
    args = parse_args()
    settings = settings_mod.load(args.settings)
    if args.depth:
        settings["search"]["depth"] = args.depth
    if args.width:
        settings["search"]["width"] = args.width
    settings["garbage"] = args.garbage
    if not args.watch and not os.path.exists(BINARY):
        print("Engine binary not found. Run ./build.sh first.")
        return 1
    live = not args.watch and not args.dry
    if not system.check_permissions(live):
        return 1
    capture = Capture()
    countdown(args.countdown)
    engine = None
    if not args.watch:
        search = settings["search"]
        engine = Engine(BINARY, ROOT, search["depth"], search["width"], search.get("nosd", True) and not args.sd)
    controls = system.Controls() if live else None
    session = Session(settings, capture, engine, Keys(settings, not live), controls, args.watch)
    try:
        session.run()
    except KeyboardInterrupt:
        pass
    finally:
        if engine:
            engine.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
