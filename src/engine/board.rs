use super::piece::{cells, Piece};

pub const W: i32 = 10;
pub const H: usize = 40;
pub const FULL: u16 = (1 << 10) - 1;

#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Board {
    pub rows: [u16; H],
}

impl Board {
    pub fn new() -> Board {
        Board { rows: [0; H] }
    }

    #[inline]
    pub fn filled(&self, x: i32, y: i32) -> bool {
        if x < 0 || x >= W || y < 0 {
            return true;
        }
        if y >= H as i32 {
            return false;
        }
        (self.rows[y as usize] >> x) & 1 == 1
    }

    #[inline]
    pub fn collides(&self, p: Piece, rot: u8, x: i32, y: i32) -> bool {
        for &(dx, dy) in cells(p, rot) {
            if self.filled(x + dx as i32, y + dy as i32) {
                return true;
            }
        }
        false
    }

    pub fn place(&mut self, p: Piece, rot: u8, x: i32, y: i32) {
        for &(dx, dy) in cells(p, rot) {
            let cx = x + dx as i32;
            let cy = y + dy as i32;
            if cx >= 0 && cx < W && cy >= 0 && (cy as usize) < H {
                self.rows[cy as usize] |= 1 << cx;
            }
        }
    }

    pub fn clear_lines(&mut self) -> u32 {
        let mut w = 0;
        let mut cleared = 0;
        for r in 0..H {
            if self.rows[r] == FULL {
                cleared += 1;
            } else {
                self.rows[w] = self.rows[r];
                w += 1;
            }
        }
        for r in w..H {
            self.rows[r] = 0;
        }
        cleared
    }

    pub fn height(&self) -> usize {
        for r in (0..H).rev() {
            if self.rows[r] != 0 {
                return r + 1;
            }
        }
        0
    }

    pub fn add_garbage(&mut self, n: usize, hole: usize) {
        if n == 0 {
            return;
        }
        for r in (n..H).rev() {
            self.rows[r] = self.rows[r - n];
        }
        for r in 0..n.min(H) {
            self.rows[r] = FULL & !(1u16 << hole);
        }
    }

    pub fn hash(&self) -> u64 {
        let mut h: u64 = 0xcbf29ce484222325;
        let top = self.height();
        for r in 0..top {
            h ^= self.rows[r] as u64;
            h = h.wrapping_mul(0x100000001b3);
            h ^= h >> 29;
        }
        h
    }
}
