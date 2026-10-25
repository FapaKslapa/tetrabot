use std::collections::VecDeque;

use super::rng::Rng;
use crate::bot::*;
use crate::engine::*;

const VIEW: usize = 6;

pub struct Game {
    pub st: State,
    pub queue: VecDeque<Piece>,
    pub pending: u32,
    pub hole: usize,
    pub sent: u32,
    pub pieces: u32,
    pub popped: usize,
    pub dead: bool,
    pub rng: Rng,
    pub stats: [u32; 8],
}

impl Game {
    pub fn new(seed: u64) -> Game {
        let mut g = Game {
            st: State { board: Board::new(), hold: None, b2b: false, combo: 0, pending: 0, hole: 0, bag: 0 },
            queue: VecDeque::new(),
            pending: 0,
            hole: 0,
            sent: 0,
            pieces: 0,
            popped: 0,
            dead: false,
            stats: [0; 8],
            rng: Rng(seed.wrapping_mul(0x9E3779B97F4A7C15) | 1),
        };
        g.refill();
        g
    }

    fn refill(&mut self) {
        while self.queue.len() < 14 {
            let mut bag = Piece::ALL.to_vec();
            for i in (1..7).rev() {
                let j = self.rng.below(i as u64 + 1) as usize;
                bag.swap(i, j);
            }
            self.queue.extend(bag);
        }
    }

    pub fn decide(&mut self, bot: &Bot) -> Option<Decision> {
        self.st.pending = self.pending;
        self.st.hole = self.hole;
        let q = self.view();
        self.st.bag = self.bag_after_view();
        bot.choose(&self.st, &q)
    }

    fn bag_after_view(&self) -> u8 {
        let next = self.popped + VIEW;
        let start = next / 7 * 7;
        let seen: Vec<Piece> = (0..VIEW).filter(|i| self.popped + i >= start).map(|i| self.queue[i]).collect();
        bag_mask(&Piece::ALL) & !bag_mask(&seen)
    }

    pub fn view(&self) -> Vec<Piece> {
        self.queue.iter().take(VIEW).copied().collect()
    }

    pub fn apply(&mut self, d: &Decision) -> u32 {
        self.popped += if d.use_hold && self.st.hold.is_none() { 2 } else { 1 };
        if d.use_hold {
            let cur = self.queue.pop_front().unwrap();
            match self.st.hold {
                Some(h) => {
                    debug_assert!(h == d.piece);
                    self.st.hold = Some(cur);
                }
                None => {
                    self.st.hold = Some(cur);
                    let nxt = self.queue.pop_front().unwrap();
                    debug_assert!(nxt == d.piece);
                }
            }
        } else {
            self.queue.pop_front();
        }
        let l = lock(&mut self.st.board, d.piece, &d.pl);
        let (atk, b2b) = attack(&l, self.st.b2b, self.st.combo);
        self.stats[l.lines.min(4) as usize] += 1;
        if l.spin == Spin::Full {
            self.stats[5] += 1;
        }
        if l.spin == Spin::Mini {
            self.stats[6] += 1;
        }
        if l.pc {
            self.stats[7] += 1;
        }
        self.st.b2b = b2b;
        self.st.combo = if l.lines > 0 { self.st.combo + 1 } else { 0 };
        self.pieces += 1;
        self.refill();
        let mut out = atk;
        if out > 0 {
            let c = out.min(self.pending);
            self.pending -= c;
            out -= c;
        }
        if l.lines == 0 && self.pending > 0 {
            let n = self.pending.min(GARBAGE_CAP);
            self.pending -= n;
            if self.rng.f() > 0.7 {
                self.hole = self.rng.below(10) as usize;
            }
            self.st.board.add_garbage(n as usize, self.hole);
        }
        self.sent += out;
        let next = self.queue[0];
        if self.st.board.collides(next, 0, SPAWN.x as i32, SPAWN.y as i32) {
            self.dead = true;
        }
        out
    }
}
