use std::collections::HashSet;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

use super::search::Decision;
use crate::engine::*;

const MAX_NODES: usize = 40_000;
pub static BUDGET_MS: AtomicU64 = AtomicU64::new(40);
const MAX_ROWS: usize = 4;

struct Solver<'a> {
    queue: &'a [Piece],
    rows: usize,
    total: usize,
    failed: HashSet<(u64, u8, u8)>,
    nodes: usize,
    started: Instant,
    budget: Duration,
}

fn cell_count(b: &Board) -> usize {
    b.rows.iter().map(|r| r.count_ones() as usize).sum()
}

fn hold_key(h: Option<Piece>) -> u8 {
    h.map(|p| p.idx() as u8 + 1).unwrap_or(0)
}

impl<'a> Solver<'a> {
    fn dfs(&mut self, b: &Board, hold: Option<Piece>, qi: usize, depth: usize, cleared: usize) -> Option<Decision> {
        if depth == self.total {
            return None;
        }
        if self.nodes >= MAX_NODES || (self.nodes % 64 == 0 && self.started.elapsed() > self.budget) {
            return None;
        }
        let key = (b.hash(), hold_key(hold), qi as u8);
        if self.failed.contains(&key) {
            return None;
        }
        self.nodes += 1;
        let mut options: Vec<(Piece, Option<Piece>, usize, bool)> = Vec::new();
        if qi < self.queue.len() {
            options.push((self.queue[qi], hold, qi + 1, false));
            match hold {
                Some(h) if h != self.queue[qi] => options.push((h, Some(self.queue[qi]), qi + 1, true)),
                None if qi + 1 < self.queue.len() && self.queue[qi + 1] != self.queue[qi] => {
                    options.push((self.queue[qi + 1], Some(self.queue[qi]), qi + 2, true))
                }
                _ => {}
            }
        }
        for (piece, hold_after, next_qi, used_hold) in options {
            for pl in placements(b, piece) {
                let mut nb = *b;
                let l = lock(&mut nb, piece, &pl);
                let c = cleared + l.lines as usize;
                if c > self.rows || nb.height() > self.rows - c {
                    continue;
                }
                let d = Decision { use_hold: used_hold, piece, pl };
                if depth + 1 == self.total {
                    if nb.height() == 0 {
                        return Some(d);
                    }
                    continue;
                }
                if self.dfs(&nb, hold_after, next_qi, depth + 1, c).is_some() {
                    return Some(d);
                }
            }
        }
        self.failed.insert(key);
        None
    }
}

pub fn find(board: &Board, hold: Option<Piece>, queue: &[Piece]) -> Option<Decision> {
    let cells = cell_count(board);
    let height = board.height();
    if height > MAX_ROWS || cells > 10 * MAX_ROWS - 4 {
        return None;
    }
    let started = Instant::now();
    let budget = Duration::from_millis(BUDGET_MS.load(Ordering::Relaxed));
    let available = queue.len() + hold.is_some() as usize;
    for rows in height.max(1)..=MAX_ROWS {
        let area = rows * 10;
        if area < cells || (area - cells) % 4 != 0 {
            continue;
        }
        let total = (area - cells) / 4;
        if total == 0 || total > available {
            continue;
        }
        if started.elapsed() > budget {
            return None;
        }
        let mut solver = Solver { queue, rows, total, failed: HashSet::new(), nodes: 0, started, budget };
        if let Some(d) = solver.dfs(board, hold, 0, 0, 0) {
            return Some(d);
        }
    }
    None
}
