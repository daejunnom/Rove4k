#[test]
fn fixed_move_storage_rejects_overflow_without_truncation(){
    let mut moves=MoveList::new();for i in 0..MOVE_CAPACITY{moves.try_push(Move{from:(i%128)as u8,to:(i%64)as u8,promo:0}).unwrap();}
    assert_eq!(moves.len(),MOVE_CAPACITY);assert!(moves.try_push(Move::default()).is_err());assert_eq!(moves.len(),MOVE_CAPACITY);
    moves.retain(|m|m.to%2!=0);assert_eq!(moves.len(),256);
    assert!(moves.into_iter().all(|m|m.to%2!=0));
    assert!(!std::mem::needs_drop::<Board>());assert!(!std::mem::needs_drop::<MoveList>());
    assert!(Board::from_fen("4k3/8/8/8/8/NNNNNNNN/NNNNNNNN/4K3 w - - 0 1").is_err());
    assert!(Board::from_fen("7k/8/8/8/8/P7/PPPPPPPP/K7 w - - 0 1").is_err());
    let b=Board::start();let fen=Board::from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1").unwrap();
    assert_eq!(b.hash,fen.hash);assert_eq!(b.bb,fen.bb);assert_eq!(b.evalwhite(),fen.evalwhite());assert_eq!(b.fen(),fen.fen());
    for text in ["€a1","éa1","e2e4q","a0a1","e2e4extra"]{assert!(b.parse_move(text).is_none());}
}
#[test]
fn bounded_history_preserves_draw_and_irreversible_replay_semantics(){
    let mut h=History::new();for key in 0..301{h.push(key);}assert_eq!(h.len(),101);assert_eq!(h[0],200);assert_eq!(h[100],300);
    let mut b=Board::start();for _ in 0..100{for text in ["g1f3","g8f6","f3g1","f6g8"]{let m=b.parse_move(text).unwrap();b=b.play(m);}}
    assert_eq!(b.halfmove,400);assert_eq!(b.hist.len(),101);assert!(b.repeated());assert!(b.halfmove>=100);
    let m=b.parse_move("e2e4").unwrap();b=b.play(m);assert_eq!(b.halfmove,0);assert_eq!(b.hist.len(),1);assert!(!b.repeated());
}
#[test]
fn exchange_abort_is_not_a_zero_exchange_result(){
    let b=Board::from_fen("4k3/8/8/3q4/8/8/4K3/3Q4 w - - 0 1").unwrap();let m=b.parse_move("d1d5").unwrap();
    let visits=std::cell::Cell::new(0);
    let abort=||{visits.set(visits.get()+1);visits.get()>=2};
    assert_eq!(b.see_with_abort(m,&abort),None);assert_eq!(visits.get(),2);
    assert!(b.see(m)>0);assert_eq!(b.fen(),"4k3/8/8/3q4/8/8/4K3/3Q4 w - - 0 1");
}
#[test]
fn hyperbola_matches_independent_rays_on_random_occupancies(){
    fn ray(square:u8,occupancy:u64,diagonal:bool)->u64{
        let mut attacks=0;
        for &d in if diagonal{&[15,17,-15,-17][..]}else{&[1,-1,16,-16][..]}{
            let mut next=square as i16+d;
            while valid(next){let target=bit(next as u8);attacks|=target;if occupancy&target!=0{break;}next+=d;}
        }
        attacks
    }
    let mut seed=0x397bace871d2046f;
    for _ in 0..2048{seed=mix(seed);for n in 0..64{let square=(n/8)*16+n%8;
        for diagonal in [false,true]{for occupancy in [seed,seed&!bit(square),seed|bit(square)]{
            assert_eq!(hq_attacks(square,occupancy,diagonal),ray(square,occupancy,diagonal),"sq {square} occ {occupancy:x}");
        }}
    }}
    for fen in ["r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1","4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"]{
        let b=Board::from_fen(fen).unwrap();for n in 0..64{let square=(n/8)*16+n%8;for side in [-1,1]{assert_eq!(b.attackers_hq(square,side),b.attackers_scalar(square,side));}}
    }
}
use super::*;
fn b(s: &str) -> Board { Board::from_fen(s).unwrap() }
#[test] fn initial_and_kiwipete_perft() {
    let start = Board::start(); assert_eq!(start.perft(1), 20); assert_eq!(start.perft(2), 400); assert_eq!(start.perft(3), 8902); assert_eq!(start.perft(4), 197281);
    let kiwi = b("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1");
    assert_eq!(kiwi.perft(1), 48); assert_eq!(kiwi.perft(2), 2039); assert_eq!(kiwi.perft(3), 97862);
}
#[test] fn ep_identity_and_discovered_check() {
    let f = "7k/8/8/r4pPK/8/8/8/8 w - f6 0 1";
    let pos = b(f); assert!(pos.parse_move("g5f6").is_none());
    assert_eq!(pos.hash, b(&f.replace(" f6 ", " - ")).hash);
    let f = "6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 2";
    let pos = b(f); assert_eq!(pos.perft(1), 7); assert!(pos.parse_move("e5d6").is_some());
    assert_ne!(pos.hash, b(&f.replace(" d6 ", " - ")).hash);
    let pos = b("k3r3/8/8/2PpP3/8/8/8/4K3 w - d6 0 1");
    assert!(pos.parse_move("c5d6").is_some()); assert!(pos.parse_move("e5d6").is_none()); assert_eq!(pos.perft(1), 8);
    assert_ne!(pos.hash, b(&pos.fen().replace(" d6 ", " - ")).hash);
    let pos = b("6k1/8/8/3pP3/4K3/8/8/8 w - d6 0 1");
    assert!(pos.in_check()); assert!(pos.parse_move("e5d6").is_some()); assert!(pos.parse_move("e5e6").is_none());
}
#[test] fn promotions_castling_and_incremental_state() {
    let p = b("1r6/P6k/8/8/8/8/8/7K w - - 0 1"); assert_eq!(p.perft(1), 11);
    for suffix in ["q", "r", "b", "n"] { assert!(p.parse_move(&format!("a7b8{}", suffix)).is_some()); }
    let mut p = b("4k3/8/8/8/8/8/8/4K3 w - - 0 1"); p.castle = 3; p.rebuild();
    assert!(p.parse_move("e1g1").is_none()); assert!(p.parse_move("e1c1").is_none());
    let p = b("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 27 19");
    let p = p.play(p.parse_move("e1c1").unwrap());
    assert_eq!(p.cells[3], 4); assert_eq!(p.cells[0], 0); assert_eq!(p.castle, 12); assert_eq!(p.halfmove, 28); assert_eq!(p.fullmove, 19);
    let mut q = p.clone(); q.rebuild(); assert_eq!(p.hash, q.hash); assert_eq!(p.bb, q.bb); assert_eq!(p.score, q.score);
    assert_eq!(b(&p.fen()).fen(), p.fen());
    let p = b("4kr2/8/8/8/8/8/8/4K2R w K - 0 1"); assert!(p.parse_move("e1g1").is_none());
    let p = b("1r2k3/8/8/8/8/8/8/R3K3 w Q - 0 1"); assert!(p.parse_move("e1c1").is_some());
    let p = b("4r3/8/8/8/8/3k4/4R3/4K3 b - - 0 1"); assert!(p.parse_move("d3c2").is_none());
    for p in [Board::start(), b("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1")] {
        for m in p.legal() {
            let q = p.play(m); let mut rebuilt = q.clone(); rebuilt.rebuild();
            assert_eq!(q.hash, rebuilt.hash); assert_eq!(q.bb, rebuilt.bb); assert_eq!(q.score, rebuilt.score);
        }
    }
}
#[test] fn repetition_and_clocks() {
    let mut p = Board::start();
    for (i, uci) in ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"].iter().enumerate() {
        p = p.play(p.parse_move(uci).unwrap()); assert_eq!(p.repeated(), i == 7);
        let q = b(&p.fen()); assert_eq!(p.hash, q.hash); assert_eq!(p.bb, q.bb); assert_eq!(p.score, q.score);
    }
    assert_eq!(p.halfmove, 8); assert_eq!(p.fullmove, 5);
    p = p.play(p.parse_move("e2e4").unwrap()); assert_eq!(p.halfmove, 0); assert_eq!(p.ep, 36);
}
#[test] fn see_handles_pins_king_safety_ep_and_promotion() {
    let p = b("4k3/4n3/5p2/8/8/2B5/8/K3R3 w - - 0 1");
    assert_eq!(p.see(p.parse_move("c3f6").unwrap()), 100); // e7 knight is pinned.
    let p = b("8/8/4k3/3p4/2P5/8/8/K2R4 w - - 0 1");
    assert_eq!(p.see(p.parse_move("c4d5").unwrap()), 100); // King cannot take a rook-protected pawn.
    let p = b("6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 2"); assert_eq!(p.see(p.parse_move("e5d6").unwrap()), 100);
    let p = b("7k/P7/8/8/8/8/8/K7 w - - 0 1"); assert_eq!(p.see(p.parse_move("a7a8q").unwrap()), 800);
}
#[test] fn terminal_rules_and_fen_validation() {
    let mate = b("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"); assert!(mate.in_check()); assert!(mate.legal().is_empty());
    let stale = b("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"); assert!(!stale.in_check()); assert!(stale.legal().is_empty());
    assert!(b("7k/8/8/8/8/8/8/K7 w - - 0 1").insufficient());
    assert!(Board::from_fen("8/8/8/8/8/8/8/8 w - - 0 1").is_err());
    assert!(Board::from_fen("7k/8/8/8/8/8/8/K7 w - a4 0 1").is_err());
    for fen in [
        "4k3/8/8/8/8/8/8/4K3 w KQ - 0 1", // Missing castling rooks.
        "r2k3r/8/8/8/8/8/8/4K3 b kq - 0 1", // King moved.
        "4k3/8/8/8/8/8/8/R3K2r w K - 0 1", // Wrong-color rook.
        "7k/8/8/4P3/8/8/8/K7 w - d6 0 1", // Missing EP victim.
        "7k/8/3N4/3pP3/8/8/8/K7 w - d6 0 1", // Occupied EP destination.
        "7k/8/8/8/3Pp3/3n4/8/K7 b - d3 0 1", // Black EP destination occupied.
        "7k/8/8/8/4p3/8/8/K7 b - d3 0 1", // Black EP victim missing.
    ] { assert!(Board::from_fen(fen).is_err(), "{}", fen); }
}
