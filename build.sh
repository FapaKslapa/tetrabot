#!/bin/bash
set -e
cd "$(dirname "$0")"
cargo build --release
python3 -m venv .venv
.venv/bin/pip install --quiet -r requirements.txt
echo "Build complete. Start with: ./run.sh"
