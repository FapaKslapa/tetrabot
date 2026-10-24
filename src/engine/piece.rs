use std::sync::OnceLock;

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]
pub enum Piece {
    I = 0,
    O = 1,
    T = 2,
    L = 3,
    J = 4,
    S = 5,
    Z = 6,
}

impl Piece {
    pub const ALL: [Piece; 7] = [Piece::I, Piece::O, Piece::T, Piece::L, Piece::J, Piece::S, Piece::Z];

    #[inline]
    pub fn idx(self) -> usize {
        self as usize
    }

    pub fn ch(self) -> char {
        ['I', 'O', 'T', 'L', 'J', 'S', 'Z'][self as usize]
    }

    pub fn from_ch(c: char) -> Option<Piece> {
        match c.to_ascii_uppercase() {
            'I' => Some(Piece::I),
            'O' => Some(Piece::O),
            'T' => Some(Piece::T),
            'L' => Some(Piece::L),
            'J' => Some(Piece::J),
            'S' => Some(Piece::S),
            'Z' => Some(Piece::Z),
            _ => None,
        }
    }
}

type Shapes = [[[(i8, i8); 4]; 4]; 7];
static SHAPES: OnceLock<Shapes> = OnceLock::new();

fn shapes() -> &'static Shapes {
    SHAPES.get_or_init(|| {
        let base: [[(i8, i8); 4]; 7] = [
            [(0, 2), (1, 2), (2, 2), (3, 2)],
            [(1, 1), (2, 1), (1, 2), (2, 2)],
            [(0, 1), (1, 1), (2, 1), (1, 2)],
            [(0, 1), (1, 1), (2, 1), (2, 2)],
            [(0, 1), (1, 1), (2, 1), (0, 2)],
            [(0, 1), (1, 1), (1, 2), (2, 2)],
            [(0, 2), (1, 2), (1, 1), (2, 1)],
        ];
        let mut out = [[[(0i8, 0i8); 4]; 4]; 7];
        for p in 0..7 {
            let n: i8 = if p <= 1 { 4 } else { 3 };
            let mut cur = base[p];
            for r in 0..4 {
                out[p][r] = cur;
                for c in cur.iter_mut() {
                    *c = (c.1, n - 1 - c.0);
                }
            }
        }
        out
    })
}

#[inline]
pub fn cells(p: Piece, rot: u8) -> &'static [(i8, i8); 4] {
    &shapes()[p.idx()][rot as usize]
}
