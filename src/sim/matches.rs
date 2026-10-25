use super::game::Game;
use crate::bot::*;

pub fn play_match(a: &Bot, b: &Bot, seed: u64, max_pieces: u32) -> f32 {
    let mut ga = Game::new(seed);
    let mut gb = Game::new(seed ^ 0xABCDEF);
    for _ in 0..max_pieces {
        for who in 0..2 {
            let (me, other, bot) = if who == 0 { (&mut ga, &mut gb, a) } else { (&mut gb, &mut ga, b) };
            match me.decide(bot) {
                Some(d) => {
                    let out = me.apply(&d);
                    other.pending += out;
                }
                None => me.dead = true,
            }
            if me.dead {
                return if who == 0 { 0.0 } else { 1.0 };
            }
        }
    }
    match ga.sent.cmp(&gb.sent) {
        std::cmp::Ordering::Greater => 1.0,
        std::cmp::Ordering::Less => 0.0,
        _ => 0.5,
    }
}

pub fn solo(bot: &Bot, seed: u64, pieces: u32, garbage_every: u32, burst: u32) -> (f32, bool, u32, [u32; 8]) {
    let mut g = Game::new(seed);
    for i in 0..pieces {
        match g.decide(bot) {
            Some(d) => {
                g.apply(&d);
            }
            None => return (g.sent as f32 / (g.pieces.max(1)) as f32, false, g.pieces, g.stats),
        }
        if g.dead {
            return (g.sent as f32 / (g.pieces.max(1)) as f32, false, g.pieces, g.stats);
        }
        if garbage_every > 0 && i % garbage_every == garbage_every - 1 {
            g.pending += if burst > 1 { 1 + g.rng.below(burst as u64) as u32 } else { 1 };
        }
    }
    (g.sent as f32 / pieces as f32, true, pieces, g.stats)
}

const STRESS_EVERY: u32 = 4;
const STRESS_BURST: u32 = 8;

pub fn survival_score(a: &Bot, b: &Bot, seed0: u64, games: u64, pieces: u32) -> f32 {
    let mut total = 0.0;
    for i in 0..games {
        let (attack_a, _, lived_a, _) = solo(a, seed0 + i, pieces, STRESS_EVERY, STRESS_BURST);
        let (attack_b, _, lived_b, _) = solo(b, seed0 + i, pieces, STRESS_EVERY, STRESS_BURST);
        total += match lived_a.cmp(&lived_b) {
            std::cmp::Ordering::Greater => 1.0,
            std::cmp::Ordering::Less => 0.0,
            std::cmp::Ordering::Equal if attack_a > attack_b => 1.0,
            std::cmp::Ordering::Equal if attack_a < attack_b => 0.0,
            std::cmp::Ordering::Equal => 0.5,
        };
    }
    total / games as f32
}
