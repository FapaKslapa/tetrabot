use crate::bot::{Weights, NF, NR};

pub fn load_weights(path: &str) -> Option<Weights> {
    let s = std::fs::read_to_string(path).ok()?;
    let v: Vec<f32> = s.split_whitespace().filter_map(|t| t.parse().ok()).collect();
    if v.len() == NF + NR {
        Some(Weights::from_vec(&v))
    } else {
        None
    }
}

pub fn weights_or_default() -> Weights {
    for p in ["weights.txt", "../weights.txt"] {
        if let Some(w) = load_weights(p) {
            return w;
        }
    }
    Weights::default_weights()
}
