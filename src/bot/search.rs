use std::collections::HashSet;
use std::sync::atomic::{AtomicUsize, Ordering};

use super::features::{eval, reward, DEFEND_CANCEL, DEFEND_CLEAR, PANIC_CLEAR, PANIC_HEIGHT};
use super::perfect;
use super::weights::Weights;
use crate::engine::*;

pub const GARBAGE_CAP: u32 = 8;

const MIN_PER_THREAD: usize = 8;
const HEAD_FACTOR: usize = 12;

pub static THREADS: AtomicUsize = AtomicUsize::new(1);

#[derive(Clone, Copy)]
pub struct State {
    pub board: Board,
    pub hold: Option<Piece>,
    pub b2b: bool,
    pub combo: i32,
    pub pending: u32,
    pub hole: usize,
    pub bag: u8,
}

pub fn bag_mask(pieces: &[Piece]) -> u8 {
    pieces.iter().fold(0u8, |m, p| m | 1 << p.idx())
}

fn bag_pieces(mask: u8) -> Vec<Piece> {
    Piece::ALL.iter().copied().filter(|p| mask >> p.idx() & 1 == 1).collect()
}

#[derive(Clone, Copy, Debug)]
pub struct Decision {
    pub use_hold: bool,
    pub piece: Piece,
    pub pl: Placement,
}

#[derive(Clone)]
pub(super) struct Node {
    pub board: Board,
    pub hold: Option<Piece>,
    pub qi: usize,
    pub b2b: bool,
    pub combo: i32,
    pub pending: u32,
    pub acc: f32,
    pub value: f32,
    pub first: Option<Decision>,
}

pub struct Bot {
    pub w: Weights,
    pub depth: usize,
    pub width: usize,
    pub aware: bool,
    pub speculate: bool,
    pub panic: bool,
    pub perfect: bool,
    pub defend: bool,
    pub threads: usize,
}

impl Bot {
    pub fn new(w: Weights, depth: usize, width: usize) -> Bot {
        Bot { w, depth, width, aware: true, speculate: true, panic: true, perfect: true, defend: true, threads: THREADS.load(Ordering::Relaxed).max(1) }
    }

    pub fn with_awareness(mut self, aware: bool) -> Bot {
        self.aware = aware;
        self
    }

    pub fn with_modules(mut self, speculate: bool, panic: bool, perfect: bool) -> Bot {
        self.speculate = speculate;
        self.panic = panic;
        self.perfect = perfect;
        self
    }

    pub fn with_defense(mut self, defend: bool) -> Bot {
        self.defend = defend;
        self
    }

    fn expand_chunk(&self, nodes: &[Node], queue: &[Piece], hole: usize) -> Vec<Node> {
        let mut children: Vec<Node> = Vec::new();
        for n in nodes {
            if n.qi >= queue.len() {
                continue;
            }
            self.expand(n, hole, queue[n.qi], n.hold, n.qi + 1, false, &mut children);
            match n.hold {
                Some(h) => {
                    if h != queue[n.qi] {
                        self.expand(n, hole, h, Some(queue[n.qi]), n.qi + 1, true, &mut children);
                    }
                }
                None => {
                    if n.qi + 1 < queue.len() && queue[n.qi + 1] != queue[n.qi] {
                        self.expand(n, hole, queue[n.qi + 1], Some(queue[n.qi]), n.qi + 2, true, &mut children);
                    }
                }
            }
        }
        children
    }

    fn expand_layer(&self, layer: &[Node], queue: &[Piece], hole: usize) -> Vec<Node> {
        let workers = self.threads.min(layer.len() / MIN_PER_THREAD).max(1);
        if workers == 1 {
            return self.expand_chunk(layer, queue, hole);
        }
        let size = (layer.len() + workers - 1) / workers;
        std::thread::scope(|scope| {
            let handles: Vec<_> = layer
                .chunks(size)
                .map(|chunk| scope.spawn(move || self.expand_chunk(chunk, queue, hole)))
                .collect();
            let mut out: Vec<Node> = Vec::new();
            for handle in handles {
                out.extend(handle.join().unwrap());
            }
            out
        })
    }

    fn select(&self, children: &[Node]) -> Vec<Node> {
        let mut order: Vec<(f32, u32)> = children.iter().enumerate().map(|(i, c)| (c.value, i as u32)).collect();
        let rank = |a: &(f32, u32), b: &(f32, u32)| b.0.partial_cmp(&a.0).unwrap().then(a.1.cmp(&b.1));
        let head = (self.width * HEAD_FACTOR).min(order.len());
        if head < order.len() {
            order.select_nth_unstable_by(head - 1, rank);
        }
        order[..head].sort_unstable_by(rank);
        let mut seen: HashSet<u64> = HashSet::new();
        let mut next: Vec<Node> = Vec::with_capacity(self.width);
        let mut visit = |i: u32, next: &mut Vec<Node>| -> bool {
            let c = &children[i as usize];
            let hk = c.board.hash()
                ^ ((c.hold.map(|p| p.idx() as u64 + 1).unwrap_or(0)) << 56)
                ^ ((c.b2b as u64) << 60)
                ^ ((c.combo.min(15) as u64) << 52)
                ^ ((c.pending.min(15) as u64) << 44)
                ^ ((c.qi as u64) << 48);
            if seen.insert(hk) {
                next.push(c.clone());
            }
            next.len() >= self.width
        };
        for &(_, i) in &order[..head] {
            if visit(i, &mut next) {
                return next;
            }
        }
        if head < order.len() {
            order[head..].sort_unstable_by(rank);
            for &(_, i) in &order[head..] {
                if visit(i, &mut next) {
                    break;
                }
            }
        }
        next
    }

    pub fn choose(&self, st: &State, queue: &[Piece]) -> Option<Decision> {
        let mut queue = queue.to_vec();
        let mut bag = if self.speculate { st.bag } else { 0 };
        if bag.count_ones() == 1 {
            queue.extend(bag_pieces(bag));
            bag = 0;
        }
        if self.perfect {
            if let Some(d) = perfect::find(&st.board, st.hold, &queue) {
                return Some(d);
            }
        }
        let mut exhausted = false;
        let mut layer = vec![Node {
            board: st.board,
            hold: st.hold,
            qi: 0,
            b2b: st.b2b,
            combo: st.combo,
            pending: if self.aware { st.pending } else { 0 },
            acc: 0.0,
            value: 0.0,
            first: None,
        }];
        let mut best: Option<Decision> = None;
        for _d in 0..self.depth {
            let children = self.expand_layer(&layer, &queue, st.hole);
            if children.is_empty() {
                exhausted = true;
                break;
            }
            let next = self.select(&children);
            best = next[0].first;
            layer = next;
        }
        if exhausted && bag != 0 {
            return self.speculate_leaf(&layer, st.hole, &bag_pieces(bag)).or(best);
        }
        best
    }

    pub(super) fn expand(
        &self,
        n: &Node,
        hole: usize,
        piece: Piece,
        hold_after: Option<Piece>,
        qi: usize,
        used_hold: bool,
        out: &mut Vec<Node>,
    ) {
        let tall = n.board.height() >= PANIC_HEIGHT;
        for pl in placements(&n.board, piece) {
            let mut nb = n.board;
            let l = lock(&mut nb, piece, &pl);
            let (atk, b2b_after) = attack(&l, n.b2b, n.combo);
            let combo_after = if l.lines > 0 { n.combo + 1 } else { 0 };
            let cancelled = atk.min(n.pending);
            let mut pending = n.pending - cancelled;
            if l.lines == 0 && pending > 0 {
                let rise = pending.min(GARBAGE_CAP);
                nb.add_garbage(rise as usize, hole);
                pending -= rise;
            }
            let mut acc = n.acc + reward(&self.w, &l, atk, n.b2b, b2b_after, used_hold);
            if self.defend && n.pending > 0 {
                acc += cancelled as f32 * DEFEND_CANCEL + if l.lines > 0 { DEFEND_CLEAR } else { 0.0 };
            }
            if self.panic && tall {
                acc += l.lines as f32 * PANIC_CLEAR;
            }
            let value = acc + eval(&self.w, &nb, b2b_after, combo_after, self.panic);
            let first = n.first.or(Some(Decision { use_hold: used_hold, piece, pl }));
            out.push(Node { board: nb, hold: hold_after, qi, b2b: b2b_after, combo: combo_after, pending, acc, value, first });
        }
    }
}
