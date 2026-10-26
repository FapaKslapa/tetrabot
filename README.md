# tetrabot

A Tetris search engine written in Rust, with a small Python front end that reads a game from the screen. It is a demonstration of how a search-based Tetris AI is put together: a rules simulator, a beam search, a screen-reading pipeline and a keyboard driver.

## Disclaimer

This project is for demonstration and educational purposes only. Automating input in online games, including TETR.IO, violates their terms of service and can get an account banned. Do not use it in public, ranked or competitive rooms, or anywhere automation is not explicitly allowed. The simulator and the engine work entirely offline and can be explored without touching any game.

## Requirements

- Rust toolchain (`cargo`)
- Python 3
- macOS: Screen Recording and Accessibility permissions for the terminal app
- Windows 10 or later: nothing extra
- Linux: an X11 session (Wayland blocks screen capture and key injection)

## Usage

```
./build.sh
./run.sh
```

On Windows use `build.bat` and `run.bat` instead. `run.sh` counts down so you can switch to the browser, then looks for the board on every connected display, calibrates itself and starts playing. Nothing is configured by hand and no screenshot is written to disk: frames only exist in memory.

Emergency stop: move the mouse to the top-left corner of the screen. Pause: top-right corner.

Options:

| Option | Meaning |
| --- | --- |
| `--watch` | Calibrate and print what is read from the screen, press nothing |
| `--dry` | Compute moves but press nothing |
| `--countdown N` | Seconds to switch to the browser (default 5) |
| `--depth N`, `--width N` | Search depth and beam width |
| `--garbage` | Read the incoming garbage meter and plan for it (off by default) |
| `--trace` | Print timing and reading details for every piece |
| `--engine beam\|cc2` | `beam` (default) uses the built-in search, `cc2` lets Cold Clear 2 choose moves |
| `--think N` | Cold Clear 2 thinking time per move in milliseconds (default 40) |
| `--keep-tree` | Keep the Cold Clear search running while keys are pressed instead of restarting it for every piece |
| `--no-ponder` | Do not think about the next piece while keys are pressed |
| `--sd` | Allow soft drop in key paths (needs SDF set to infinity) |
| `--threads N` (engine) | Beam search worker threads; set `search.threads` in the settings file (default 3) |
| `--pc-ms N` (engine) | Wall-clock budget of the perfect clear search in milliseconds (default 40) |
| `--settings FILE` | JSON file overriding keys, timing and search settings |
| `--human` | Press keys like a person: variable thinking pauses, uneven tap and gap timing, a drifting tempo, small hesitations and rotations that cancel out. Same placements, same strength |
| `--pps N` | With `--human`: target average pieces per second (for example `3.75`). Not a fixed time per piece: some pieces hesitate, add rotations or take a wrong turn and correct it, and the ordinary pieces speed up to pay for them. Often it also waits until the piece has fallen a row or two before touching it (`fall_chance`); if the room's gravity is too slow to be worth waiting for, it notices and stops. Without `--sd` (and with a finite SDF in the game) it holds soft drop until it sees the piece drop, so slow gravity is not a problem; set `"descend": false` to wait passively instead. With `--trace` each piece prints the planned press time and what it did |
| `mistake_chance` (setting) | With `--human`: about 1 piece in 20 is placed one or two columns off the best spot, only on a low stack, with nothing incoming, and only if the board stays nearly as good. Set to 0 to turn it off. Printed as `imperfect:` with `--trace` |
| `--human-seed N` | Seed for `--human`, for reproducible runs |

`--human` only changes how the chosen moves are typed, the engine is untouched. Its values can be tuned under `"human"` in the settings file (`think_median_ms`, `think_max_ms`, `tap_ms` (default: from `timing`), `gap_ms`, `fidget_chance`, `tempo_range` and so on, see `adapter/human.py`). Over a game its focus drifts between flow (slightly faster, fewer hesitations, fewer off-best placements) and slumps (the opposite), and tap lengths and gaps are skewed and correlated from one key to the next. Under pressure (tall stack or incoming garbage) none of this applies: it plays fast and straight. The average pace stays at `--pps`. Use it only in rooms where everyone knows it is a bot.

Cold Clear 2 needs soft drop to reach tucks and T-spins under overhangs, so for it set the soft drop factor (SDF) to infinity in the game handling settings and start with `--sd`. Without `--sd` the bot only plays placements reachable without soft drop and falls back to the next best suggestion.

With `--trace` each piece prints how the board was read (`path=quick`, `full` or `settle` with the reason for the slow path), the spawn wait outcome (`ok`, `REALIGN`, `TIMEOUT`) and how many of the last ten reads took the fast path. For the fastest reading, use the minimal graphics preset in the game and turn off the danger warning, board spin on T-spin and other screen effects.

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
    speculate.rs     expected value over the pieces the bag can still deal
    perfect.rs       perfect clear search over the known pieces
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
  system.py          mouse corners, permission checks
  backends/          key events and permissions per platform (macOS Quartz, pynput elsewhere)
  capture.py         screen grabbing
  imageops.py        integral images, runs, connected components
  board_finder.py    locates the 10x20 board
  panel_finder.py    locates the next queue and the hold box
  layout.py          layout type and pixel to screen conversion
  calibrate.py       calibration over all displays with a sanity check
  palette.py         piece colours and classification
  vision.py          reads the stack, the queue, the hold and the falling piece
  stack.py           stack clean-up helpers, garbage rise prediction
  bag.py             7-bag tracking for pieces beyond the preview
  ponder.py          thinks about the next piece while keys are pressed
  engine_client.py   talks to the Rust engine
  keys.py            sends key events
  game_state.py      per-game state
  session.py         main loop
tests/               unit tests on synthetic frames
```

## Cold Clear 2

[Cold Clear 2](https://github.com/MinusKelvin/cold-clear-2) by MinusKelvin is a Tetris bot licensed under MIT or Apache-2.0. The build script clones it into `vendor/` and compiles it; its sources are not part of this repository. It speaks the Tetris Bot Protocol over stdin and stdout. For every piece the front end sends the board read from the screen, the queue, the hold piece, combo, back-to-back state and the 7-bag state it tracked, waits for the thinking time, and asks for a suggestion. The suggested placement is turned into a set of cells, and the built-in engine finds the key sequence that reaches exactly those cells. Played alone, with the same piece sequences, Cold Clear 2 produced about 0.72 attack per piece at 40 ms against about 0.59 for the built-in search. In simulated versus games with garbage the built-in search, which plans for incoming lines, won most matches, so it stays the default; start with `--engine cc2` to compare. `--garbage` makes Cold Clear plan as if the pending lines had already risen.

## How the engine works

Board: ten columns, forty rows, one `u16` per row. Collision, placement and line clearing are bit operations.

Move generation: for a piece, a breadth-first search explores every state `(x, y, rotation, spin flag)` reachable from the spawn position using left, right, clockwise, counter-clockwise and optionally soft drop. Rotation uses the SRS kick tables. Every state that can hard drop gives a placement, and the search remembers the parent of each state so the exact key sequence for any placement can be recovered.

Scoring: a T piece that rotated into a spot with at least three occupied corners counts as a T-spin, full or mini depending on the front corners and the kick used. The attack table covers clears, T-spins, back-to-back, combo and perfect clears.

Search: a beam search over the current piece plus the preview queue. At each layer it expands every placement of the current piece and, when allowed, of the held piece (or of the next piece if hold is empty). Each node accumulates a reward for lines sent and clear type, and is ranked by that reward plus a static evaluation. Duplicate boards are merged by hash and only the best `width` nodes continue for `depth` layers.

Evaluation features: holes, depth of holes, bumpiness, maximum height, a danger term for tall stacks, row transitions, well depth, back-to-back and combo state. The weights live in `bot/weights.rs`; `tune` improves them by random search with self-play.

Garbage awareness is only used when the front end is started with `--garbage`; otherwise it sends `incoming=0`. `incoming` is the number of pending garbage lines read from the meter next to the board, and `hole` is the column of the gray rows already on the stack. During search, attack cancels pending lines first; the rest rises (at most 8 rows) after any placement that clears nothing, so the bot prefers clearing lines and keeping the stack low when garbage is on the way. `versus --blind-other` disables this for the opponent to measure its effect; `tune` accepts `--seed`, `--out` and `--survival F`, the share (0 to 1) of the fitness taken from surviving bursts of garbage in solo games instead of head-to-head wins; `scripts/remote_tune.py` passes it from the `SURVIVAL` environment variable (default 0.4).

Bag knowledge: the front end tracks the 7-bag from the first queue it sees and sends `bag=<letters>`, the pieces the piece after the queue can still be. One letter extends the queue exactly; several letters are averaged over in a final speculative layer. Perfect clear search runs before the beam when the stack is at most four rows: a depth-first search over the known pieces and hold, memoised on the board, looks for a placement sequence that empties the board. When the stack reaches ten rows the evaluation switches to a survival mode that scales down combo, back-to-back and T-slot bonuses and adds a bonus per cleared line. `versus --other-off speculate|panic|perfect` disables one of these for the opponent.

Line protocol: the front end writes one line per decision to the engine and reads one line back.

```
rows=<u16 rows from bottom, comma separated> hold=<piece or -> queue=<current piece followed by previews> b2b=<0|1> combo=<n> [incoming=<n>] [hole=<column>] [bag=<letters>]
MOVE use_hold=<0|1> piece=<P> rot=<r> x=<x> y=<y> spin=<s> keys=<L,R,CW,CCW,SD or -> after=<rows> hold=<piece or -> b2b=<0|1> combo=<n> attack=<n> lines=<n>
```

The engine answers `DEAD` when no placement exists.

Engine commands:

```
target/release/tetrabot solo --pieces 300      attack per piece in solo runs
target/release/tetrabot check                  verify that key paths reach the chosen placement
target/release/tetrabot versus --a old.txt --other new.txt --games 100   match between two weight files, games run in parallel (--jobs N), with a win rate and a 95% margin; --seed-offset N runs new games on top of an earlier batch
target/release/tetrabot tune                   tune weights, writes weights.txt
```

## How the front end works

Calibration: the screen is searched for the board without fixed coordinates. A scan over window sizes with a 1:2 aspect ratio finds the large dark rectangle that stands out most from its surroundings, using an integral image, and its edges are refined from dark runs. The board edges are cut at thin white border lines, so the garbage meter strip and the name plate next to the board are not mistaken for board. Cell size follows from the board width. Pieces in the queue are located as colour blobs about one tetromino in size, stacked in a column to the right of the board, and a fit over their positions gives the slot pitch. The hold box is found the same way on the left, with a position derived from the board when the box is empty or greyed out. A layout is accepted only if at least four queue pieces can be read from it. If the queue becomes unreadable for a few seconds, for example after the window moved, calibration runs again.

Reading: each board cell is sampled and counted as filled when its tint matches a piece colour or a neutral gray. Queue slots and the hold box are classified by the average tint of their bright pixels. The falling piece is the four highest cells and is removed from the stack before the engine is asked for a move.

Loop: wait for the queue to become readable, attach to the current piece (at the start of a game, or by waiting for the queue to shift if a game is already running), ask the engine, replay the key sequence, then wait until the queue has advanced. Between moves the front end keeps its own copy of the board and compares it with what it sees, so transient on-screen effects do not corrupt the state. The copy is also compared against the board with one to eight garbage rows raised below it, so incoming lines are recognised without trusting the raw screen. A gray cell only counts when its row is almost completely gray. While the keys of one piece are pressed, the engine already works on the next position, predicting the garbage meter after the move; if the screen matches the prediction the answer is used, otherwise the engine is asked again. Garbage rows are recognised from the settled screen itself, whatever their holes are, so Expert Mode blocks with different holes do not desynchronise the stored board; if the screen keeps disagreeing with the stored board it is adopted after a few settled reads. Isolated groups of up to three cells high on the board are treated as on-screen text and ignored. The current piece is cross-checked against the falling piece on the screen, and the queue wait accepts the first clean frame so a stale preview slot cannot cause a long stall.

## Tests

```
python3 -m unittest discover -s tests
cargo build --release && target/release/tetrabot check
```

The Python tests build synthetic frames and check board, queue and hold detection at several positions and sizes.
