#!/bin/bash
set -e
cd "$(dirname "$0")"
cargo build --release
if [ ! -d vendor/cold-clear-2 ]; then
  git clone --depth 1 https://github.com/MinusKelvin/cold-clear-2 vendor/cold-clear-2
fi
(cd vendor/cold-clear-2 && cargo build --release)
python3 -m venv .venv
.venv/bin/pip install --quiet -r requirements.txt
echo "Build complete. Start with: ./run.sh"
