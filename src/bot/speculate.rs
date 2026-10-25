use super::search::{Bot, Decision, Node};
use crate::engine::*;

const SPEC_NODES: usize = 48;
const DEAD_VALUE: f32 = -1.0e4;

impl Bot {
    pub(super) fn speculate_leaf(&self, layer: &[Node], hole: usize, pieces: &[Piece]) -> Option<Decision> {
        let mut best_value = f32::NEG_INFINITY;
        let mut pick = None;
        let mut scratch: Vec<Node> = Vec::new();
        for n in layer.iter().take(SPEC_NODES) {
            let mut sum = 0.0;
            for &p in pieces {
                scratch.clear();
                self.expand(n, hole, p, n.hold, n.qi, false, &mut scratch);
                if let Some(h) = n.hold {
                    if h != p {
                        self.expand(n, hole, h, Some(p), n.qi, true, &mut scratch);
                    }
                }
                sum += scratch.iter().map(|c| c.value).fold(DEAD_VALUE, f32::max);
            }
            let v = sum / pieces.len() as f32;
            if v > best_value {
                best_value = v;
                pick = n.first;
            }
        }
        pick
    }
}
