use super::weights_io::weights_or_default;
use crate::bot::*;
use crate::cli::arg;
use crate::sim::*;

pub fn tune(args: &[String]) {
    let iters: usize = arg(args, "--iters", "40").parse().unwrap();
    let games: u64 = arg(args, "--games", "16").parse().unwrap();
    let depth: usize = arg(args, "--tdepth", "3").parse().unwrap();
    let width: usize = arg(args, "--twidth", "14").parse().unwrap();
    let mut best = weights_or_default().to_vec();
    let seed: u64 = arg(args, "--seed", "19088743").parse().unwrap();
    let out = arg(args, "--out", "weights.txt");
    let accept: f32 = arg(args, "--accept", "0.58").parse().unwrap();
    let survival: f32 = arg(args, "--survival", "0").parse().unwrap();
    let stress_games = (games / 2).max(6);
    let mut rng = Rng(seed | 1);
    let fitness = |cand: &Vec<f32>, base: &Vec<f32>, seed0: u64| -> f32 {
        let a = Bot::new(Weights::from_vec(cand), depth, width);
        let b = Bot::new(Weights::from_vec(base), depth, width);
        let mut s = 0.0;
        for i in 0..games {
            s += play_match(&a, &b, seed0 + i, 400);
            s += 1.0 - play_match(&b, &a, seed0 + i, 400);
        }
        let versus = s / (2.0 * games as f32);
        if survival <= 0.0 {
            return versus;
        }
        let stress = survival_score(&a, &b, seed0 + 5000, stress_games, 300);
        (1.0 - survival) * versus + survival * stress
    };
    for it in 0..iters {
        let mut cand = best.clone();
        for v in cand.iter_mut() {
            if rng.f() < 0.4 {
                let scale = v.abs().max(0.5) * 0.3;
                *v += (rng.f() - 0.5) * 2.0 * scale;
            }
        }
        let f = fitness(&cand, &best, 1000 + it as u64 * 97);
        println!("iter {} fitness vs best: {:.2}", it, f);
        if f > accept {
            best = cand;
            println!("  accepted new weights");
            let s: Vec<String> = best.iter().map(|x| format!("{:.4}", x)).collect();
            std::fs::write(&out, s.join(" ")).ok();
        }
    }
}
