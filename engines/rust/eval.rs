//! Independent HCE (B/C) and frozen integer feature model (E).
//!
//! C's fixed x86-64 profile enables AVX2 and calls the vector dot product
//! directly. `simd_available` is for development diagnostics, not its hot path.
use crate::board::{Board, Move};
use std::sync::OnceLock;

#[path = "../model/frozen.rs"]
mod frozen;

const VALUE: [i32; 7] = [0, 100, 320, 330, 500, 900, 20000];
const HCE: [i16; 32] = [
    100, 320, 335, 505, 950, 1, 8, 5, 1, 1, -5, 4, -12, -10, 24, 12,
    9, 2, 15, 8, 3, 6, 10, 12, 0, 0, 0, 0, 0, 0, 0, 0,
];
const KNIGHT: [i32; 8] = [33, 31, 18, 14, -14, -18, -31, -33];
const RAYS: [i32; 8] = [-17, -15, 15, 17, -16, -1, 1, 16];
static MODEL: OnceLock<[i16; 21]> = OnceLock::new();

/// C+E is a separate build candidate; the baseline C HCE remains available.
pub const CROSS_MODEL: bool = match option_env!("ROVE_MODEL") {
    Some(value) => value.as_bytes().len() == 1 && value.as_bytes()[0] == b'1',
    None => false,
};

pub fn init_model() {
    MODEL.get_or_init(frozen::model_weights);
}

fn at(b: &Board, q: i32) -> i8 {
    if q & 0x88 == 0 { b.cells[q as usize] } else { 0 }
}

fn center(q: usize) -> i16 {
    7 - (((2 * (q & 7) as i32 - 7).abs()
        + (2 * (q >> 4) as i32 - 7).abs()) / 2) as i16
}

fn near(a: usize, b: usize) -> bool {
    (a as i32 / 16 - b as i32 / 16).abs() <= 1
        && (a as i32 % 16 - b as i32 % 16).abs() <= 1
}

/// The first 16 features are the canonical frozen E schema, white minus black.
/// The remaining HCE terms add passed pawns, mobility, open rooks, king cover,
/// king pressure, pawn chains, seventh-rank rooks and phase-scaled king activity.
fn model_features(b: &Board) -> [i16; 32] {
    let mut x = [0i16; 32];
    let mut files = [[0i16; 8]; 2];
    let mut bishops = [0i16; 2];
    for q in 0..128 {
        if q & 0x88 != 0 { continue; }
        let p = b.cells[q];
        if p == 0 { continue; }
        let s = p.signum() as i16;
        let c = usize::from(p < 0);
        let t = p.unsigned_abs() as usize;
        if t <= 5 { x[t - 1] += s; }
        x[4 + t] += s * center(q);
        if t == 1 {
            files[c][q & 7] += 1;
            let r = if c == 0 { q >> 4 } else { 7 - (q >> 4) };
            x[11] += s * (r as i16 - 1);
        }
        if t == 3 { bishops[c] += 1; }
    }
    for c in 0..2 {
        let s = if c == 0 { 1 } else { -1 };
        x[14] += s * i16::from(bishops[c] >= 2);
        for f in 0..8 {
            let n = files[c][f];
            x[12] += s * (n - 1).max(0);
            if (f == 0 || files[c][f - 1] == 0)
                && (f == 7 || files[c][f + 1] == 0) {
                x[13] += s * n;
            }
        }
    }
    x[15] = b.side as i16;
    x
}

fn features(b: &Board) -> [i16; 32] {
    let mut x = model_features(b);
    let pawns = [b.bb[0][1], b.bb[1][1]];
    let kings = [b.king[0] as usize, b.king[1] as usize];
    let phase = b.bb.iter().map(|s|
        s[2].count_ones() + s[3].count_ones() + 2 * s[4].count_ones() + 4 * s[5].count_ones()
    ).sum::<u32>().min(24) as i16;
    for q in 0..128 {
        if q & 0x88 != 0 { continue; }
        let p = b.cells[q];
        if p == 0 { continue; }
        let s = p.signum() as i16;
        let c = usize::from(p < 0);
        let t = p.unsigned_abs();
        let f = q & 7;
        let r = q >> 4;
        let relative = if c == 0 { r } else { 7 - r };
        if t == 1 {
            let file_mask = 0x0101_0101_0101_0101u64 << f;
            let adjacent = file_mask | (file_mask << 1 & !0x0101_0101_0101_0101)
                | (file_mask >> 1 & !0x8080_8080_8080_8080);
            let forward = if c == 0 {
                if r == 7 { 0 } else { u64::MAX << ((r + 1) * 8) }
            } else if r == 0 { 0 } else { (1u64 << (r * 8)) - 1 };
            if pawns[1 - c] & adjacent & forward == 0 {
                x[16] += s * (relative * relative) as i16;
            }
            let back = q as i32 - 16 * s as i32;
            x[21] += s * i16::from(at(b, back - 1) == p || at(b, back + 1) == p);
            for d in [-1, 1] {
                let dst = q as i32 + 16 * s as i32 + d;
                if dst & 0x88 == 0 && near(dst as usize, kings[1 - c]) {
                    x[20] += s;
                }
            }
            continue;
        }
        if t == 4 {
            if pawns[c] & (0x0101_0101_0101_0101u64 << f) == 0 { x[18] += s; }
            if relative == 6 { x[22] += s; }
        }
        if t == 6 {
            x[23] += s * center(q) * (24 - phase) / 24;
            for d in [-1, 0, 1] {
                let dst = q as i32 + 16 * s as i32 + d;
                x[19] += s * i16::from(at(b, dst) == s as i8);
            }
            continue;
        }
        let directions: &[i32] = match t {
            2 => &KNIGHT,
            3 => &RAYS[..4],
            4 => &RAYS[4..],
            _ => &RAYS,
        };
        for d in directions {
            let mut dst = q as i32 + d;
            while dst & 0x88 == 0 {
                let target = b.cells[dst as usize];
                if target != 0 && target.signum() == p.signum() { break; }
                x[17] += s;
                if near(dst as usize, kings[1 - c]) { x[20] += s; }
                if t == 2 || target != 0 { break; }
                dst += d;
            }
        }
    }
    x
}

fn scalar_dot(x: &[i16], w: &[i16]) -> i32 {
    x.iter().zip(w).map(|(&a, &b)| a as i32 * b as i32).sum()
}

fn score(white: i32, side: i8) -> i32 {
    (white * side as i32).clamp(-20000, 20000)
}

pub fn scalar(b: &Board) -> i32 {
    score(scalar_dot(&features(b), &HCE), b.side)
}

#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
unsafe fn vector_dot<const N: usize>(x: &[i16; N], weights: &[i16; N]) -> i32 {
    use std::arch::x86_64::*;
    let mut v = _mm256_setzero_si256();
    // The only instantiations are exactly 16 canonical model or 32 HCE lanes.
    for i in (0..N).step_by(16) {
        // Each unaligned load reads exactly 16 initialized i16 lanes.
        let a = unsafe { _mm256_loadu_si256(x.as_ptr().add(i).cast()) };
        let b = unsafe { _mm256_loadu_si256(weights.as_ptr().add(i).cast()) };
        v = _mm256_add_epi32(v, _mm256_madd_epi16(a, b));
    }
    let mut lanes = [0i32; 8];
    unsafe { _mm256_storeu_si256(lanes.as_mut_ptr().cast(), v) };
    lanes.iter().sum()
}

pub fn simd_available() -> bool {
    #[cfg(target_arch = "x86_64")]
    { std::is_x86_feature_detected!("avx2") }
    #[cfg(not(target_arch = "x86_64"))]
    { false }
}

pub fn model(b: &Board) -> i32 {
    let w = MODEL.get_or_init(frozen::model_weights);
    score(scalar_dot(&model_features(b)[..16], &w[..16]), b.side)
}

/// Fixed AVX2 model profile. No CPUID branch is emitted in the search path.
pub fn model_simd(b: &Board) -> i32 {
    #[cfg(target_arch = "x86_64")]
    {
        let x = model_features(b);
        let w = MODEL.get_or_init(frozen::model_weights);
        let features: &[i16; 16] = x[..16].try_into().unwrap();
        let weights: &[i16; 16] = w[..16].try_into().unwrap();
        score(unsafe { vector_dot(features, weights) }, b.side)
    }
    #[cfg(not(target_arch = "x86_64"))]
    { panic!("candidate C+E requires x86-64 AVX2") }
}

/// Frozen E ordering uses victim value, attacker cost only on captures,
/// promotion gain, center change and relative pawn advance, in that order.
pub fn order(b: &Board, m: Move) -> i32 {
    let w = MODEL.get_or_init(frozen::model_weights);
    let p = b.cells[m.from as usize].unsigned_abs() as usize;
    let target = b.cells[m.to as usize].unsigned_abs() as usize;
    let capture = target != 0 || (p == 1 && (m.from & 7) != (m.to & 7));
    // Canonical model material is its decoded P/N/B/R/Q coefficients; king=0.
    // HCE's VALUE[6] is a search sentinel, not a model ordering coefficient.
    let value = |piece: usize| if (1..=5).contains(&piece) { w[piece - 1] as i32 } else { 0 };
    let victim = if target != 0 { value(target) } else if capture { value(1) } else { 0 };
    let promo = m.promo.unsigned_abs() as usize;
    let values = [
        victim,
        if capture { value(p) } else { 0 },
        if promo != 0 { value(promo) - value(1) } else { 0 },
        (center(m.to as usize) - center(m.from as usize)) as i32,
        if p == 1 { ((m.to >> 4) as i32 - (m.from >> 4) as i32) * b.side as i32 } else { 0 },
    ];
    values.iter().zip(&w[16..]).map(|(&a, &k)| a * k as i32).sum()
}

pub fn evaluate(b: &Board, variant: u8) -> i32 {
    match variant {
        b'E' => model(b),
        b'A' | b'D' | b'F' => score(b.evalwhite(), b.side),
        b'C' if CROSS_MODEL => model_simd(b),
        b'C' => {
            #[cfg(target_arch = "x86_64")]
            // The fixed C shipping profile requires AVX2. Development callers
            // must use simd_available before selecting C on an unknown CPU.
            { score(unsafe { vector_dot(&features(b), &HCE) }, b.side) }
            #[cfg(not(target_arch = "x86_64"))]
            { panic!("candidate C requires x86-64 AVX2") }
        }
        _ => scalar(b),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn board(fen: &str) -> Board { Board::from_fen(fen).unwrap() }

    #[test]
    fn frozen_model_hand_calculated_positions() {
        let start = Board::start();
        assert_eq!(model(&start), 10);
        let mut black = start.clone(); black.side = -1;
        assert_eq!(model(&black), 10);
        let p = board("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1");
        // Pawn100 + center18 + advance12 - isolation8 + tempo10.
        assert_eq!(model(&p), 132);
        let mut p = p; p.side = -1;
        assert_eq!(model(&p), -112);
        let promoted = board("QQQQQQQQ/QQQQQQQQ/QQQQQQQQ/QQQQQQQQ/QQQkQQQQ/QQQQQQQQ/QQQQQQQQ/KQQQQQQQ w - - 0 1");
        assert_eq!(model(&promoted), 20000);
        assert_ne!(model(&start), scalar(&start));
    }

    #[test]
    fn model_order_uses_ep_and_promotion_features() {
        let ep = board("6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 2");
        let capture = ep.parse_move("e5d6").unwrap();
        assert_eq!(order(&ep, capture), 1502);
        let promotion = board("7k/P7/8/8/8/8/8/K7 w - - 0 1");
        assert_eq!(order(&promotion, promotion.parse_move("a7a8q").unwrap()), 9602);
        assert!(order(&promotion, promotion.parse_move("a7a8q").unwrap())
            > order(&promotion, promotion.parse_move("a7a8n").unwrap()));
        let king = board("7k/8/8/8/8/8/3p4/4K3 w - - 0 1");
        assert_eq!(order(&king, king.parse_move("e1d2").unwrap()), 1602);
    }

    #[test]
    fn evaluation_preserves_color_and_rank_symmetry() {
        let original = board("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1");
        let mut mirror = original.clone();
        for q in 0..128 {
            if q & 0x88 == 0 { mirror.cells[q ^ 112] = -original.cells[q]; }
        }
        mirror.side = -original.side; mirror.castle = 0; mirror.ep = -1;
        mirror.rebuild();
        assert_eq!(model(&original), model(&mirror));
        assert_eq!(scalar(&original), scalar(&mirror));
    }

    #[test]
    fn avx2_matches_scalar_on_played_positions_and_extremes() {
        if !simd_available() {
            eprintln!("AVX2 comparison not run: development CPU has no AVX2");
            return;
        }
        let mut seed = 13u64;
        for mut b in [Board::start(),
            board("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
            board("6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 2"),
            board("7k/P7/8/8/8/8/8/K7 w - - 0 1"),
            board("QQQQQQQQ/QQQQQQQQ/QQQQQQQQ/QQQQQQQQ/QQQkQQQQ/QQQQQQQQ/QQQQQQQQ/KQQQQQQQ w - - 0 1")] {
            for _ in 0..64 {
                assert_eq!(model_simd(&b), model(&b), "{}", b.fen());
                let expected = if CROSS_MODEL { model(&b) } else { scalar(&b) };
                assert_eq!(evaluate(&b, b'C'), expected, "{}", b.fen());
                let moves = b.legal();
                if moves.is_empty() { break; }
                seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                b = b.play(moves[seed as usize % moves.len()]);
            }
        }
    }

    #[test]
    fn incremental_candidates_use_rebuild_equivalent_score() {
        let mut b = Board::start();
        let mut seed = 23u64;
        for _ in 0..128 {
            let mut rebuilt = b.clone(); rebuilt.rebuild();
            assert_eq!(b.evalwhite(), rebuilt.evalwhite());
            for variant in [b'A', b'D', b'F'] {
                assert_eq!(evaluate(&b, variant), score(b.evalwhite(), b.side));
            }
            let moves = b.legal();
            if moves.is_empty() { break; }
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            b = b.play(moves[seed as usize % moves.len()]);
        }
    }
}
