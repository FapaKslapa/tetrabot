import glob
import os
import subprocess
import sys
import time

REPO_URL = os.environ.get("REPO_URL", "https://github.com/FapaKslapa/tetris_bot")
HOURS = float(os.environ.get("HOURS", "3"))
PROCS = int(os.environ.get("PROCS", str(os.cpu_count() or 2)))
GAMES = os.environ.get("GAMES", "40")
TUNE_DEPTH = os.environ.get("TUNE_DEPTH", "4")
TUNE_WIDTH = os.environ.get("TUNE_WIDTH", "30")
ACCEPT = os.environ.get("ACCEPT", "0.58")
CHECK_GAMES = os.environ.get("CHECK_GAMES", "40")
SRC = os.environ.get("SRC", os.environ.get("ZIP_PATH", ""))
BASE = "/kaggle/working" if os.path.isdir("/kaggle/working") else "/content" if os.path.isdir("/content") else os.getcwd()
WORK = os.environ.get("WORK", os.path.join(BASE, "tetris_bot"))


def run(cmd, **kwargs):
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=True, **kwargs)


def install_rust():
    if subprocess.run("command -v cargo", shell=True, capture_output=True).returncode == 0:
        return
    run("curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal")
    os.environ["PATH"] += os.pathsep + os.path.expanduser("~/.cargo/bin")


def fetch_project():
    if os.path.isdir(WORK):
        return
    if SRC and os.path.isdir(SRC):
        run(["cp", "-r", SRC, WORK])
        return
    if SRC:
        run(["unzip", "-q", SRC, "-d", WORK])
        return
    run(["git", "clone", "--depth", "1", REPO_URL, WORK])


def build():
    run("cargo build --release", cwd=WORK)
    return os.path.join(WORK, "target", "release", "tetrabot")


def start_tuning(binary, outdir):
    os.makedirs(outdir, exist_ok=True)
    procs = []
    for i in range(PROCS):
        out = os.path.join(outdir, "weights_%d.txt" % i)
        log = open(os.path.join(outdir, "log_%d.txt" % i), "w")
        cmd = [binary, "tune", "--iters", "100000", "--games", GAMES, "--tdepth", TUNE_DEPTH,
               "--twidth", TUNE_WIDTH, "--accept", ACCEPT, "--seed", str(1000 + 7919 * i), "--out", out]
        procs.append(subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=outdir))
    return procs


def score(binary, candidate, outdir):
    baseline = os.path.join(outdir, "baseline.txt")
    if not os.path.exists(baseline):
        run([binary, "defaults"], cwd=outdir, stdout=open(baseline, "w"))
    workdir = os.path.join(outdir, "check")
    os.makedirs(workdir, exist_ok=True)
    run(["cp", candidate, os.path.join(workdir, "weights.txt")])
    result = subprocess.run([binary, "versus", "--games", CHECK_GAMES, "--other", baseline,
                             "--depth", "6", "--width", "120"], cwd=workdir, capture_output=True, text=True)
    return float(result.stdout.split()[2])


def main():
    install_rust()
    fetch_project()
    binary = build()
    outdir = os.path.join(WORK, "tuning")
    procs = start_tuning(binary, outdir)
    deadline = time.time() + HOURS * 3600
    try:
        while time.time() < deadline and any(p.poll() is None for p in procs):
            time.sleep(60)
            done = sum(len(open(f).read().split("\n")) for f in glob.glob(os.path.join(outdir, "log_*.txt")))
            print("elapsed %.1f min, log lines %d" % ((time.time() - deadline) / 60 + HOURS * 60, done), flush=True)
    finally:
        for p in procs:
            p.terminate()
    candidates = sorted(glob.glob(os.path.join(outdir, "weights_*.txt")))
    if not candidates:
        print("No candidate was accepted; keep the default weights.")
        return
    results = [(score(binary, c, outdir), c) for c in candidates]
    for wins, path in results:
        print("%s: %.1f wins of %s against the default weights" % (path, wins, CHECK_GAMES))
    best = max(results)
    final = os.path.join(WORK, "best_weights.txt")
    run(["cp", best[1], final])
    print("Best candidate copied to", final, "with", best[0], "wins of", CHECK_GAMES)


if __name__ == "__main__":
    sys.exit(main())
