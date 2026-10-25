use super::weights::{Weights, NF};
use crate::engine::*;

pub const PANIC_HEIGHT: usize = 10;
pub const PANIC_CLEAR: f32 = 2.0;
pub const DEFEND_CANCEL: f32 = 1.0;
pub const DEFEND_CLEAR: f32 = 1.5;
const PANIC_SCALE: f32 = 0.25;

const SLOT_VALUE: [f32; 3] = [0.1, 1.5, 2.0];

fn slot_value(b: &Board, colh: &[i32; 10]) -> f32 {
    let mut best = 0.0f32;
    for x in 0..8usize {
        for left in [true, false] {
            let (side, far) = if left { (x, x + 2) } else { (x + 2, x) };
            let y = colh[side];
            if y < 1 || colh[x + 1] >= y {
                continue;
            }
            let y = y as usize;
            let wall = |r: usize| b.rows[r] >> far & 1 == 1;
            if !wall(y - 1) || wall(y) || y + 1 >= b.rows.len() || !wall(y + 1) {
                continue;
            }
            let stem = 1u16 << (x + 1);
            let body = 0b111u16 << x;
            let lines = (b.rows[y - 1] | stem == FULL) as usize + (b.rows[y] | body == FULL) as usize;
            best = best.max(SLOT_VALUE[lines]);
        }
    }
    best
}

pub fn features(b: &Board, b2b: bool, combo: i32) -> [f32; NF] {
    let top = b.height();
    let mut colh = [0i32; 10];
    let mut holes = 0i32;
    let mut hole_depth = 0i32;
    let mut row_trans = 0i32;
    for r in 0..top {
        let row = b.rows[r] as u32;
        let e = (row << 1) | 1 | (1 << 11);
        row_trans += ((e ^ (e >> 1)).count_ones() as i32) - 1;
    }
    for c in 0..10 {
        let mut seen = 0i32;
        let mut h = 0i32;
        for r in (0..top).rev() {
            if (b.rows[r] >> c) & 1 == 1 {
                if h == 0 {
                    h = r as i32 + 1;
                }
                seen += 1;
            } else if h > 0 {
                holes += 1;
                hole_depth += seen;
            }
        }
        colh[c] = h;
    }
    let maxh = *colh.iter().max().unwrap();
    let mut minc = 0;
    for c in 1..10 {
        if colh[c] < colh[minc] {
            minc = c;
        }
    }
    let mut well_depth = i32::MAX;
    if minc > 0 {
        well_depth = well_depth.min(colh[minc - 1] - colh[minc]);
    }
    if minc < 9 {
        well_depth = well_depth.min(colh[minc + 1] - colh[minc]);
    }
    let well_depth = well_depth.max(0).min(8);
    let mut bump = 0i32;
    for c in 0..9 {
        if well_depth >= 3 && (c == minc || c + 1 == minc) {
            continue;
        }
        bump += (colh[c] - colh[c + 1]).abs();
    }
    let danger = ((maxh - 12).max(0) as f32).powi(2);
    let flat = if maxh <= 4 { 1.0 } else { 0.0 };
    [
        holes as f32,
        hole_depth as f32,
        bump as f32,
        maxh as f32,
        danger,
        row_trans as f32,
        well_depth.min(6) as f32,
        if b2b { 1.0 } else { 0.0 },
        combo.min(6).max(0) as f32,
        flat,
        slot_value(b, &colh),
    ]
}

pub fn eval(w: &Weights, b: &Board, b2b: bool, combo: i32, panic: bool) -> f32 {
    let f = features(b, b2b, combo);
    let tall = panic && f[3] >= PANIC_HEIGHT as f32;
    let mut s = 0.0;
    for i in 0..NF {
        let scale = if tall && matches!(i, 7 | 8 | 9 | 10) { PANIC_SCALE } else { 1.0 };
        s += f[i] * w.f[i] * scale;
    }
    s
}

pub(super) fn reward(w: &Weights, l: &Lock, atk: u32, b2b_before: bool, b2b_after: bool, used_hold: bool) -> f32 {
    let mut r = atk as f32 * w.r[0];
    if l.lines > 0 {
        match (l.spin, l.lines) {
            (Spin::Full, 1) => r += w.r[6],
            (Spin::Full, 2) => r += w.r[7],
            (Spin::Full, _) => r += w.r[8],
            (Spin::Mini, _) => r += w.r[5],
            (Spin::None, 1) => r += w.r[1],
            (Spin::None, 2) => r += w.r[2],
            (Spin::None, 3) => r += w.r[3],
            _ => r += w.r[4],
        }
        if b2b_before && !b2b_after {
            r += w.r[10];
        }
    }
    if l.pc {
        r += w.r[9];
    }
    if used_hold {
        r += w.r[11];
    }
    r
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_double_slot() {
        let mut b = Board::new();
        b.rows[0] = FULL & !(1 << 1);
        b.rows[1] = FULL & !(1 << 1);
        b.rows[2] = FULL & !0b111;
        b.rows[3] = 1 << 2;
        assert_eq!(features(&b, false, 0)[10], 2.0);
    }

    #[test]
    fn flat_board_has_no_slot() {
        let mut b = Board::new();
        b.rows[0] = FULL;
        assert_eq!(features(&b, false, 0)[10], 0.0);
    }
}
