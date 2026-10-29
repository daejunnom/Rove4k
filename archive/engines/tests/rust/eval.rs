use super::*;

fn board(fen: &str) -> Board { Board::from_fen(fen).unwrap() }
// Deliberately outside legal chess inventory: numerical overflow stress
// builds a synthetic board directly, without weakening FEN admission.
fn dense_numeric_board()->Board{
    let mut b=board("8/8/8/8/3k4/8/8/K7 w - - 0 1");
    for q in 0..128{if q&0x88==0&&b.cells[q]==0{b.cells[q]=5;}}
    b.rebuild();b
}

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
    let promoted = dense_numeric_board();
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
        board("7k/P7/8/8/8/8/8/K7 w - - 0 1")] {
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
    let dense=dense_numeric_board();assert_eq!(model_simd(&dense),model(&dense));
    assert_eq!(evaluate(&dense,b'C'),if CROSS_MODEL{model(&dense)}else{scalar(&dense)});
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
