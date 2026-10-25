use std::io::{self, BufRead, Write};

use super::weights_io::weights_or_default;
use crate::bot::*;
use crate::engine::*;

fn parse_rows(s: &str) -> Board {
    let mut b = Board::new();
    for (i, t) in s.split(',').enumerate() {
        if i >= H {
            break;
        }
        b.rows[i] = t.trim().parse::<u16>().unwrap_or(0) & FULL;
    }
    b
}

fn rows_str(b: &Board) -> String {
    let top = b.height().max(1);
    b.rows[..top].iter().map(|r| r.to_string()).collect::<Vec<_>>().join(",")
}

fn parse_request(line: &str) -> (State, Vec<Piece>) {
    let mut st = State { board: Board::new(), hold: None, b2b: false, combo: 0, pending: 0, hole: 4, bag: 0 };
    let mut queue: Vec<Piece> = Vec::new();
    for tok in line.split_whitespace() {
        if let Some((k, v)) = tok.split_once('=') {
            match k {
                "rows" => st.board = parse_rows(v),
                "hold" => st.hold = v.chars().next().and_then(Piece::from_ch),
                "queue" => queue = v.chars().filter_map(Piece::from_ch).collect(),
                "b2b" => st.b2b = v == "1",
                "combo" => st.combo = v.parse().unwrap_or(0),
                "incoming" => st.pending = v.parse().unwrap_or(0),
                "bag" => st.bag = bag_mask(&v.chars().filter_map(Piece::from_ch).collect::<Vec<_>>()),
                "hole" => st.hole = v.parse::<usize>().unwrap_or(4).min(9),
                _ => {}
            }
        }
    }
    (st, queue)
}

fn parse_cells(s: &str) -> Vec<(i32, i32)> {
    s.split(',')
        .filter_map(|t| {
            let (x, y) = t.split_once(':')?;
            Some((x.parse().ok()?, y.parse().ok()?))
        })
        .collect()
}

fn find_placement(b: &Board, piece: Piece, wanted: &[(i32, i32)], spin: &str) -> Option<Placement> {
    let want: Spin = match spin {
        "full" => Spin::Full,
        "mini" => Spin::Mini,
        _ => Spin::None,
    };
    let mut fallback = None;
    for pl in placements(b, piece) {
        let mut cs: Vec<(i32, i32)> = cells(piece, pl.rot)
            .iter()
            .map(|&(dx, dy)| (pl.x as i32 + dx as i32, pl.y as i32 + dy as i32))
            .collect();
        let mut w = wanted.to_vec();
        cs.sort();
        w.sort();
        if cs != w {
            continue;
        }
        if classify(b, piece, pl.rot, pl.x as i32, pl.y as i32, pl.spin) == want {
            return Some(pl);
        }
        fallback.get_or_insert(pl);
    }
    fallback
}

fn parse_place(line: &str) -> Option<(State, Piece, Vec<(i32, i32)>, String)> {
    let (st, _) = parse_request(line);
    let mut piece = None;
    let mut cs = Vec::new();
    let mut spin = String::from("none");
    for tok in line.split_whitespace() {
        if let Some((k, v)) = tok.split_once('=') {
            match k {
                "piece" => piece = v.chars().next().and_then(Piece::from_ch),
                "cells" => cs = parse_cells(v),
                "spin" => spin = v.to_string(),
                _ => {}
            }
        }
    }
    Some((st, piece?, cs, spin))
}

fn format_move(st: &State, queue: &[Piece], d: &Decision) -> String {
    let keys = find_path(&st.board, d.piece, &d.pl).unwrap_or_default();
    let mut nb = st.board;
    let l = lock(&mut nb, d.piece, &d.pl);
    let (atk, b2b) = attack(&l, st.b2b, st.combo);
    let combo = if l.lines > 0 { st.combo + 1 } else { 0 };
    let hold_after = if d.use_hold { Some(queue[0]) } else { st.hold };
    let ks = keys.iter().map(|k| k.name()).collect::<Vec<_>>().join(",");
    format!(
        "MOVE use_hold={} piece={} rot={} x={} y={} spin={} keys={} after={} hold={} b2b={} combo={} attack={} lines={}",
        d.use_hold as u8,
        d.piece.ch(),
        d.pl.rot,
        d.pl.x,
        d.pl.y,
        d.pl.spin,
        if ks.is_empty() { "-".to_string() } else { ks },
        rows_str(&nb),
        hold_after.map(|p| p.ch()).unwrap_or('-'),
        b2b as u8,
        combo,
        atk,
        l.lines
    )
}

pub fn serve(depth: usize, width: usize) {
    let bot = Bot::new(weights_or_default(), depth, width);
    let stdin = io::stdin();
    let mut out = io::stdout();
    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        if line.contains("cells=") {
            let reply = match parse_place(&line) {
                Some((st, piece, cs, spin)) => match find_placement(&st.board, piece, &cs, &spin) {
                    Some(pl) => format_move(&st, &[piece], &Decision { use_hold: false, piece, pl }),
                    None => "ERR placement".to_string(),
                },
                None => "ERR request".to_string(),
            };
            writeln!(out, "{}", reply).ok();
            out.flush().ok();
            continue;
        }
        let (st, queue) = parse_request(&line);
        if queue.is_empty() {
            writeln!(out, "ERR queue").ok();
            out.flush().ok();
            continue;
        }
        match bot.choose(&st, &queue) {
            None => writeln!(out, "DEAD").ok(),
            Some(d) => writeln!(out, "{}", format_move(&st, &queue, &d)).ok(),
        };
        out.flush().ok();
    }
}
