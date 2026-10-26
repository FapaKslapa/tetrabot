import os
import sys
import time

import settings as settings_mod
import system
from capture import Capture
from cli import parse_args
from cold_clear import ColdClear
from engine_client import Engine
from human import Human
from imperfect import Imperfect
from keys import Keys
from session import Session

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = ".exe" if sys.platform.startswith("win") else ""
BINARY = os.path.join(ROOT, "target", "release", "tetrabot" + EXE)
COLD_CLEAR = os.path.join(ROOT, "vendor", "cold-clear-2", "target", "release", "cold-clear-2" + EXE)


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
    if args.think:
        settings["search"]["think_ms"] = args.think
    if args.no_ponder:
        settings["search"]["ponder"] = False
    settings["garbage"] = args.garbage
    settings["trace"] = args.trace
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
        engine = Engine(BINARY, ROOT, search["depth"], search["width"], search.get("nosd", True) and not args.sd,
                        search.get("threads", 1))
        if args.engine == "cc2":
            if os.path.exists(COLD_CLEAR):
                engine = ColdClear(COLD_CLEAR, ROOT, engine, search["think_ms"], args.keep_tree, args.garbage)
                if not args.sd:
                    print("Cold Clear plays best with --sd and SDF set to infinity in the game handling settings.")
            else:
                print("Cold Clear 2 is not built, using the built-in search. Run the build script to get it.")
    controls = system.Controls() if live else None
    human = None
    if args.human:
        if args.human_seed is not None:
            settings["human"]["seed"] = args.human_seed
        if args.pps:
            settings["human"]["pps"] = args.pps
        if settings["human"].get("descend") is None:
            settings["human"]["descend"] = not args.sd
        human = Human(settings["human"], settings["timing"])
        print("Human mode on: same moves, human-like timing%s." % (", soft drop to let pieces fall" if human.cfg["descend"] else ""))
    session = Session(settings, capture, engine, Keys(settings, not live, human), controls, args.watch)
    if human is not None and engine is not None:
        session.imperfect = Imperfect(getattr(engine, "engine", engine), settings["human"].get("mistake_chance", 0.05),
                                      settings["human"].get("seed"))
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
