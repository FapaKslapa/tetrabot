use super::board::Board;
use super::movement::Placement;
use super::piece::Piece;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Spin {
    None,
    Mini,
    Full,
}

pub fn classify(b: &Board, p: Piece, rot: u8, x: i32, y: i32, spin: u8) -> Spin {
    if p != Piece::T || spin == 0 {
        return Spin::None;
    }
    let c = |dx: i32, dy: i32| b.filled(x + dx, y + dy);
    let corners = [c(0, 0), c(2, 0), c(0, 2), c(2, 2)];
    let n = corners.iter().filter(|&&v| v).count();
    if n < 3 {
        return Spin::None;
    }
    let front = match rot {
        0 => [2, 3],
        1 => [1, 3],
        2 => [0, 1],
        _ => [0, 2],
    };
    let f = corners[front[0]] as u8 + corners[front[1]] as u8;
    if f == 2 || spin == 2 {
        Spin::Full
    } else {
        Spin::Mini
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Lock {
    pub lines: u32,
    pub spin: Spin,
    pub pc: bool,
}

pub fn lock(b: &mut Board, p: Piece, pl: &Placement) -> Lock {
    let spin = classify(b, p, pl.rot, pl.x as i32, pl.y as i32, pl.spin);
    b.place(p, pl.rot, pl.x as i32, pl.y as i32);
    let lines = b.clear_lines();
    let pc = lines > 0 && b.height() == 0;
    Lock { lines, spin, pc }
}

const COMBO_TABLE: [u32; 14] = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 5, 5, 5];

pub fn attack(l: &Lock, b2b_before: bool, combo_before: i32) -> (u32, bool) {
    if l.lines == 0 {
        return (0, b2b_before);
    }
    let difficult = l.lines == 4 || l.spin != Spin::None;
    let mut base: u32 = match (l.spin, l.lines) {
        (Spin::Full, 1) => 2,
        (Spin::Full, 2) => 4,
        (Spin::Full, _) => 6,
        (Spin::Mini, 1) => 0,
        (Spin::Mini, 2) => 1,
        (Spin::Mini, _) => 2,
        (Spin::None, 1) => 0,
        (Spin::None, 2) => 1,
        (Spin::None, 3) => 2,
        _ => 4,
    };
    if difficult && b2b_before {
        base += 1;
    }
    let c = combo_before.max(0) as usize;
    let atk = if base > 0 {
        ((base as f32) * (1.0 + 0.25 * c as f32)).floor() as u32
    } else {
        COMBO_TABLE[c.min(13)]
    };
    let atk = if l.pc { 10 } else { atk };
    (atk, difficult)
}
