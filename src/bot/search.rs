use std::collections::HashSet;

use super::features::{eval, reward};
use super::weights::Weights;
use crate::engine::*;

pub const GARBAGE_CAP: u32 = 8;

#[derive(Clone, Copy)]
pub struct State {
    pub board: Board,
    pub hold: Option<Piece>,
    pub b2b: bool,
    pub combo: i32,
    pub pending: u32,
    pub hole: usize,
}

#[derive(Clone, Copy, Debug)]
pub struct Decision {
    pub use_hold: bool,
    pub piece: Piece,
    pub pl: Placement,
}

#[derive(Clone)]
struct Node {
    board: Board,
    hold: Option<Piece>,
    qi: usize,
    b2b: bool,
    combo: i32,
    pending: u32,
    acc: f32,
    value: f32,
    first: Option<Decision>,
}

pub struct Bot {
    pub w: Weights,
    pub depth: usize,
    pub width: usize,
    pub aware: bool,
}

impl Bot {
    pub fn new(w: Weights, depth: usize, width: usize) -> Bot {
        Bot { w, depth, width, aware: true }
    }

    pub fn with_awareness(mut self, aware: bool) -> Bot {
        self.aware = aware;
        self
    }

    pub fn choose(&self, st: &State, queue: &[Piece]) -> Option<Decision> {
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
            let mut children: Vec<Node> = Vec::new();
            for n in &layer {
                if n.qi >= queue.len() {
                    continue;
                }
                self.expand(n, st.hole, queue[n.qi], n.hold, n.qi + 1, false, &mut children);
                match n.hold {
                    Some(h) => {
                        if h != queue[n.qi] {
                            self.expand(n, st.hole, h, Some(queue[n.qi]), n.qi + 1, true, &mut children);
                        }
                    }
                    None => {
                        if n.qi + 1 < queue.len() && queue[n.qi + 1] != queue[n.qi] {
                            self.expand(n, st.hole, queue[n.qi + 1], Some(queue[n.qi]), n.qi + 2, true, &mut children);
                        }
                    }
                }
            }
            if children.is_empty() {
                break;
            }
            children.sort_by(|a, b| b.value.partial_cmp(&a.value).unwrap());
            let mut seen: HashSet<u64> = HashSet::new();
            let mut next: Vec<Node> = Vec::with_capacity(self.width);
            for c in children {
                let hk = c.board.hash()
                    ^ ((c.hold.map(|p| p.idx() as u64 + 1).unwrap_or(0)) << 56)
                    ^ ((c.b2b as u64) << 60)
                    ^ ((c.combo.min(15) as u64) << 52)
                    ^ ((c.pending.min(15) as u64) << 44)
                    ^ ((c.qi as u64) << 48);
                if seen.insert(hk) {
                    next.push(c);
                    if next.len() >= self.width {
                        break;
                    }
                }
            }
            best = next[0].first;
            layer = next;
        }
        best
    }

    fn expand(
        &self,
        n: &Node,
        hole: usize,
        piece: Piece,
        hold_after: Option<Piece>,
        qi: usize,
        used_hold: bool,
        out: &mut Vec<Node>,
    ) {
        for pl in placements(&n.board, piece) {
            let mut nb = n.board;
            let l = lock(&mut nb, piece, &pl);
            let (atk, b2b_after) = attack(&l, n.b2b, n.combo);
            let combo_after = if l.lines > 0 { n.combo + 1 } else { 0 };
            let mut pending = n.pending - atk.min(n.pending);
            if l.lines == 0 && pending > 0 {
                let rise = pending.min(GARBAGE_CAP);
                nb.add_garbage(rise as usize, hole);
                pending -= rise;
            }
            let acc = n.acc + reward(&self.w, &l, atk, n.b2b, b2b_after, used_hold);
            let value = acc + eval(&self.w, &nb, b2b_after, combo_after);
            let first = n.first.or(Some(Decision { use_hold: used_hold, piece, pl }));
            out.push(Node { board: nb, hold: hold_after, qi, b2b: b2b_after, combo: combo_after, pending, acc, value, first });
        }
    }
}
