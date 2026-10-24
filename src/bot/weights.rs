pub const NF: usize = 10;
pub const NR: usize = 12;

#[derive(Clone, Debug)]
pub struct Weights {
    pub f: [f32; NF],
    pub r: [f32; NR],
}

impl Weights {
    pub fn default_weights() -> Weights {
        Weights {
            f: [-9.0, -1.2, -0.9, -0.35, -0.12, -0.6, 1.2, 1.5, 0.8, 0.0],
            r: [3.0, -2.0, -0.8, 0.0, 2.0, 0.0, 2.0, 4.0, 5.0, 25.0, -3.0, -0.15],
        }
    }

    pub fn to_vec(&self) -> Vec<f32> {
        let mut v = self.f.to_vec();
        v.extend_from_slice(&self.r);
        v
    }

    pub fn from_vec(v: &[f32]) -> Weights {
        let mut w = Weights::default_weights();
        for i in 0..NF {
            w.f[i] = v[i];
        }
        for i in 0..NR {
            w.r[i] = v[NF + i];
        }
        w
    }
}
