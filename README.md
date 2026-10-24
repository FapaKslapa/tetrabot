# tetrabot

A Tetris search engine written in Rust, with a small Python front end that reads a game from the screen. It is a demonstration of how a search-based Tetris AI is put together: a rules simulator, a beam search, a screen-reading pipeline and a keyboard driver.

## Disclaimer

This project is for demonstration and educational purposes only. Automating input in online games, including TETR.IO, violates their terms of service and can get an account banned. Do not use it in public, ranked or competitive rooms, or anywhere automation is not explicitly allowed. The simulator and the engine work entirely offline and can be explored without touching any game.

## Requirements

- macOS (screen capture and key events use Quartz)
- Rust toolchain (`cargo`)
- Python 3
- Screen Recording and Accessibility permissions for the terminal app

## Usage

```
./build.sh
./run.sh
```

`run.sh` counts down so you can switch to the browser, then looks for the board on every connected display, calibrates itself and starts playing. Nothing is configured by hand and no screenshot is written to disk: frames only exist in memory.

Emergency stop: move the mouse to the top-left corner of the screen. Pause: top-right corner.

Options:

| Option | Meaning |
| --- | --- |
| `--watch` | Calibrate and print what is read from the screen, press nothing |
| `--dry` | Compute moves but press nothing |
| `--countdown N` | Seconds to switch to the browser (default 5) |
| `--depth N`, `--width N` | Search depth and beam width |
| `--sd` | Allow soft drop in key paths (needs SDF set to infinity) |
| `--settings FILE` | JSON file overriding keys, timing and search settings |

Default key bindings are the arrow keys, `z` for counter-clockwise rotation, `c` for hold and space for hard drop.

## Layout of the code

```
src/
  main.rs            command dispatch
  cli.rs             argument helpers
  engine/            rules and move generation
    piece.rs         piece shapes and rotations
    board.rs         bitboard, collision, line clears, garbage
    kicks.rs         SRS wall kicks and rotation
    movement.rs      reachable placements, key paths, key replay
    scoring.rs       T-spin detection, attack table, combo, back-to-back
  bot/               search
    weights.rs       tunable weights
    features.rs      board features, evaluation and move rewards
    search.rs        beam search with hold and the preview queue
  sim/               self-play simulator
    rng.rs           small xorshift generator
    game.rs          one game with a 7-bag and garbage
    matches.rs       bot versus bot, solo runs
  commands/          CLI commands
    protocol.rs      line protocol used by the Python front end
    bench.rs         solo, versus and check commands
    tune.rs          random-search weight tuning
    weights_io.rs    weight file loading

adapter/
  main.py            entry point
  cli.py             command line options
  settings.py        defaults for keys, timing and search
  system.py          permissions, mouse corners
  capture.py         screen grabbing
  imageops.py        integral images, runs, connected components
  board_finder.py    locates the 10x20 board
  panel_finder.py    locates the next queue and the hold box
  layout.py          layout type and pixel to screen conversion
  calibrate.py       calibration over all displays with a sanity check
  palette.py         piece colours and classification
  vision.py          reads the stack, the queue, the hold and the falling piece
  stack.py           stack clean-up helpers
  engine_client.py   talks to the Rust engine
  keys.py            sends key events
  game_state.py      per-game state
  session.py         main loop
tests/               unit tests on synthetic frames
```

## How the engine works

Board: ten columns, forty rows, one `u16` per row. Collision, placement and line clearing are bit operations.

Move generation: for a piece, a breadth-first search explores every state `(x, y, rotation, spin flag)` reachable from the spawn position using left, right, clockwise, counter-clockwise and optionally soft drop. Rotation uses the SRS kick tables. Every state that can hard drop gives a placement, and the search remembers the parent of each state so the exact key sequence for any placement can be recovered.

Scoring: a T piece that rotated into a spot with at least three occupied corners counts as a T-spin, full or mini depending on the front corners and the kick used. The attack table covers clears, T-spins, back-to-back, combo and perfect clears.

Search: a beam search over the current piece plus the preview queue. At each layer it expands every placement of the current piece and, when allowed, of the held piece (or of the next piece if hold is empty). Each node accumulates a reward for lines sent and clear type, and is ranked by that reward plus a static evaluation. Duplicate boards are merged by hash and only the best `width` nodes continue for `depth` layers.

Evaluation features: holes, depth of holes, bumpiness, maximum height, a danger term for tall stacks, row transitions, well depth, back-to-back and combo state. The weights live in `bot/weights.rs`; `tune` improves them by random search with self-play.

Garbage awareness: `incoming` is the number of pending garbage lines read from the meter next to the board, and `hole` is the column of the gray rows already on the stack. During search, attack cancels pending lines first; the rest rises (at most 8 rows) after any placement that clears nothing, so the bot prefers clearing lines and keeping the stack low when garbage is on the way. `versus --blind-other` disables this for the opponent to measure its effect; `tune` accepts `--seed` and `--out`.

Line protocol: the front end writes one line per decision to the engine and reads one line back.

```
rows=<u16 rows from bottom, comma separated> hold=<piece or -> queue=<current piece followed by previews> b2b=<0|1> combo=<n> [incoming=<n>] [hole=<column>]
MOVE use_hold=<0|1> piece=<P> rot=<r> x=<x> y=<y> spin=<s> keys=<L,R,CW,CCW,SD or -> after=<rows> hold=<piece or -> b2b=<0|1> combo=<n> attack=<n> lines=<n>
```

The engine answers `DEAD` when no placement exists.

Engine commands:

```
target/release/tetrabot solo --pieces 300      attack per piece in solo runs
target/release/tetrabot check                  verify that key paths reach the chosen placement
target/release/tetrabot versus --other w.txt   match against another weight file
target/release/tetrabot tune                   tune weights, writes weights.txt
```

## How the front end works

Calibration: the screen is searched for the board without fixed coordinates. A scan over window sizes with a 1:2 aspect ratio finds the large dark rectangle that stands out most from its surroundings, using an integral image, and its edges are refined from dark runs. Cell size follows from the board width. Pieces in the queue are located as colour blobs about one tetromino in size, stacked in a column to the right of the board, and a fit over their positions gives the slot pitch. The hold box is found the same way on the left. A layout is accepted only if at least four queue pieces can be read from it. If the queue becomes unreadable for a few seconds, for example after the window moved, calibration runs again.

Reading: each board cell is sampled and counted as filled when its tint matches a piece colour or a neutral gray. Queue slots and the hold box are classified by the average tint of their bright pixels. The falling piece is the four highest cells and is removed from the stack before the engine is asked for a move.

Loop: wait for the queue to become readable, attach to the current piece (at the start of a game, or by waiting for the queue to shift if a game is already running), ask the engine, replay the key sequence, then wait until the queue has advanced. Between moves the front end keeps its own copy of the board and compares it with what it sees, so transient on-screen effects do not corrupt the state. When gray cells appear, the screen becomes the source of truth.

## Tests

```
python3 -m unittest discover -s tests
cargo build --release && target/release/tetrabot check
```

The Python tests build synthetic frames and check board, queue and hold detection at several positions and sizes.
