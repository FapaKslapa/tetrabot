use super::weights_io::{load_weights, weights_or_default};
use crate::bot::*;
use crate::cli::{arg, flag};
use crate::engine::*;
use crate::sim::*;

pub fn run_solo(args: &[String], depth: usize, width: usize) {
    let n: u32 = arg(args, "--pieces", "500").parse().unwrap();
    let g: u32 = arg(args, "--garbage-every", "0").parse().unwrap();
    let bot = Bot::new(weights_or_default(), depth, width);
    let t = std::time::Instant::now();
    let mut tot = 0.0;
    let games = 5;
    for s in 0..games {
        let (app, alive, p, st) = solo(&bot, 100 + s, n, g);
        println!(
            "seed {}: attack/piece {:.2}, survived: {}, pieces: {} | lines 1:{} 2:{} 3:{} 4:{} tspin:{} mini:{} pc:{}",
            s, app, alive, p, st[1], st[2], st[3], st[4], st[5], st[6], st[7]
        );
        tot += app;
    }
    println!(
        "mean attack/piece {:.2}, {:.1} ms/move",
        tot / games as f32,
        t.elapsed().as_secs_f64() * 1000.0 / (games as f64 * n as f64)
    );
}

pub fn run_versus(args: &[String], depth: usize, width: usize) {
    let n: u64 = arg(args, "--games", "20").parse().unwrap();
    let a = Bot::new(weights_or_default(), depth, width);
    let bw = load_weights(&arg(args, "--other", "")).unwrap_or_else(Weights::default_weights);
    let b = Bot::new(bw, depth, width).with_awareness(!flag(args, "--blind-other"));
    let mut s = 0.0;
    for i in 0..n {
        s += play_match(&a, &b, 7 + i, 600);
    }
    println!("A wins {:.1} of {}", s, n);
}

pub fn run_check() {
    let bot = Bot::new(weights_or_default(), 4, 30);
    let mut bad = 0;
    let mut tot = 0;
    let mut tspins = 0;
    for seed in 0..6u64 {
        let mut g = Game::new(seed + 50);
        for i in 0..250 {
            let d = match g.decide(&bot) {
                Some(d) => d,
                None => break,
            };
            tot += 1;
            match find_path(&g.st.board, d.piece, &d.pl) {
                None => bad += 1,
                Some(k) => {
                    let a = simulate_keys(&g.st.board, d.piece, &k);
                    if a.x != d.pl.x || a.y != d.pl.y || a.rot != d.pl.rot {
                        bad += 1;
                    }
                }
            }
            let mut b2 = g.st.board;
            let l = lock(&mut b2, d.piece, &d.pl);
            if l.spin == Spin::Full {
                tspins += 1;
            }
            g.apply(&d);
            if i % 5 == 4 {
                g.pending += 1;
            }
            if g.dead {
                break;
            }
        }
    }
    println!("moves: {}, wrong paths: {}, full t-spins: {}", tot, bad, tspins);
}
