use std::sync::atomic::{AtomicBool, Ordering};

use super::board::Board;
use super::kicks::rotate;
use super::piece::Piece;

pub static NO_SD: AtomicBool = AtomicBool::new(false);

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Active {
    pub x: i8,
    pub y: i8,
    pub rot: u8,
    pub spin: u8,
}

pub const SPAWN: Active = Active { x: 3, y: 19, rot: 0, spin: 0 };

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Key {
    Left,
    Right,
    Cw,
    Ccw,
    SoftDrop,
}

impl Key {
    fn from_u8(v: u8) -> Key {
        match v {
            0 => Key::Left,
            1 => Key::Right,
            2 => Key::Cw,
            3 => Key::Ccw,
            _ => Key::SoftDrop,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Key::Left => "L",
            Key::Right => "R",
            Key::Cw => "CW",
            Key::Ccw => "CCW",
            Key::SoftDrop => "SD",
        }
    }
}

#[inline]
pub fn drop_dist(b: &Board, p: Piece, a: Active) -> i32 {
    let mut d = 0;
    while !b.collides(p, a.rot, a.x as i32, a.y as i32 - d - 1) {
        d += 1;
    }
    d
}

const NX: usize = 13;
const NY: usize = 26;
const NS: usize = NX * NY * 12;

#[inline]
fn sidx(a: Active) -> usize {
    ((((a.x as i32 + 2) as usize) * NY + (a.y as i32 + 2) as usize) * 4 + a.rot as usize) * 3 + a.spin as usize
}

fn sdec(i: usize) -> Active {
    let spin = (i % 3) as u8;
    let r = i / 3;
    let rot = (r % 4) as u8;
    let r = r / 4;
    let y = (r % NY) as i32 - 2;
    let x = (r / NY) as i32 - 2;
    Active { x: x as i8, y: y as i8, rot, spin }
}

#[derive(Clone, Copy, Debug)]
pub struct Placement {
    pub rot: u8,
    pub x: i8,
    pub y: i8,
    pub spin: u8,
    pub src: u16,
}

fn explore(b: &Board, p: Piece, keep: bool) -> (Vec<Placement>, Vec<(u16, u8)>) {
    let mut out: Vec<Placement> = Vec::with_capacity(48);
    if b.collides(p, SPAWN.rot, SPAWN.x as i32, SPAWN.y as i32) {
        return (out, Vec::new());
    }
    let mut seen = [false; NS];
    let mut placed = [false; NS];
    let mut parent: Vec<(u16, u8)> = if keep { vec![(u16::MAX, 0); NS] } else { Vec::new() };
    let mut queue: Vec<u16> = Vec::with_capacity(512);
    let s0 = sidx(SPAWN);
    seen[s0] = true;
    queue.push(s0 as u16);
    let mut head = 0;
    while head < queue.len() {
        let si = queue[head] as usize;
        head += 1;
        let a = sdec(si);
        let d = drop_dist(b, p, a);
        let fa = Active { x: a.x, y: a.y - d as i8, rot: a.rot, spin: if d > 0 { 0 } else { a.spin } };
        let fi = sidx(fa);
        if !placed[fi] {
            placed[fi] = true;
            out.push(Placement { rot: fa.rot, x: fa.x, y: fa.y, spin: fa.spin, src: si as u16 });
        }
        let mut cand: [(Option<Active>, u8); 5] = [(None, 0); 5];
        if !b.collides(p, a.rot, a.x as i32 - 1, a.y as i32) {
            cand[0] = (Some(Active { x: a.x - 1, y: a.y, rot: a.rot, spin: 0 }), 0);
        }
        if !b.collides(p, a.rot, a.x as i32 + 1, a.y as i32) {
            cand[1] = (Some(Active { x: a.x + 1, y: a.y, rot: a.rot, spin: 0 }), 1);
        }
        cand[2] = (rotate(b, p, a, true), 2);
        cand[3] = (rotate(b, p, a, false), 3);
        if d > 0 && !NO_SD.load(Ordering::Relaxed) {
            cand[4] = (Some(Active { x: a.x, y: a.y - d as i8, rot: a.rot, spin: 0 }), 4);
        }
        for (na, k) in cand.iter() {
            if let Some(na) = na {
                let ni = sidx(*na);
                if !seen[ni] {
                    seen[ni] = true;
                    queue.push(ni as u16);
                    if keep {
                        parent[ni] = (si as u16, *k);
                    }
                }
            }
        }
    }
    (out, parent)
}

pub fn placements(b: &Board, p: Piece) -> Vec<Placement> {
    explore(b, p, false).0
}

pub fn find_path(b: &Board, p: Piece, target: &Placement) -> Option<Vec<Key>> {
    let (pls, parent) = explore(b, p, true);
    let t = pls
        .iter()
        .find(|q| q.rot == target.rot && q.x == target.x && q.y == target.y && q.spin == target.spin)?;
    let mut keys = Vec::new();
    let mut cur = t.src as usize;
    let s0 = sidx(SPAWN);
    while cur != s0 {
        let (prev, k) = parent[cur];
        if prev == u16::MAX {
            return None;
        }
        keys.push(Key::from_u8(k));
        cur = prev as usize;
    }
    keys.reverse();
    Some(keys)
}

pub fn simulate_keys(b: &Board, p: Piece, keys: &[Key]) -> Active {
    let mut a = SPAWN;
    for k in keys {
        match k {
            Key::Left => {
                if !b.collides(p, a.rot, a.x as i32 - 1, a.y as i32) {
                    a.x -= 1;
                    a.spin = 0;
                }
            }
            Key::Right => {
                if !b.collides(p, a.rot, a.x as i32 + 1, a.y as i32) {
                    a.x += 1;
                    a.spin = 0;
                }
            }
            Key::Cw => {
                if let Some(n) = rotate(b, p, a, true) {
                    a = n;
                }
            }
            Key::Ccw => {
                if let Some(n) = rotate(b, p, a, false) {
                    a = n;
                }
            }
            Key::SoftDrop => {
                let d = drop_dist(b, p, a);
                if d > 0 {
                    a.y -= d as i8;
                    a.spin = 0;
                }
            }
        }
    }
    let d = drop_dist(b, p, a);
    if d > 0 {
        a.y -= d as i8;
        a.spin = 0;
    }
    a
}
