use super::board::Board;
use super::movement::Active;
use super::piece::Piece;

type K5 = [(i8, i8); 5];

fn kicks(p: Piece, from: u8, to: u8) -> &'static K5 {
    const JLSTZ: [K5; 8] = [
        [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
        [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
        [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
        [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
        [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
        [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
        [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
        [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    ];
    const IK: [K5; 8] = [
        [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
        [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
        [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
        [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
        [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
        [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
        [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
        [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
    ];
    let i = match (from, to) {
        (0, 1) => 0,
        (1, 0) => 1,
        (1, 2) => 2,
        (2, 1) => 3,
        (2, 3) => 4,
        (3, 2) => 5,
        (3, 0) => 6,
        _ => 7,
    };
    if p == Piece::I {
        &IK[i]
    } else {
        &JLSTZ[i]
    }
}

pub fn rotate(b: &Board, p: Piece, a: Active, cw: bool) -> Option<Active> {
    if p == Piece::O {
        return None;
    }
    let to = if cw { (a.rot + 1) % 4 } else { (a.rot + 3) % 4 };
    for (i, &(kx, ky)) in kicks(p, a.rot, to).iter().enumerate() {
        let nx = a.x as i32 + kx as i32;
        let ny = a.y as i32 + ky as i32;
        if !b.collides(p, to, nx, ny) {
            return Some(Active { x: nx as i8, y: ny as i8, rot: to, spin: if i == 4 { 2 } else { 1 } });
        }
    }
    None
}
