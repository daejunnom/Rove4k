use crate::{board::{Board, from, to}, dev, runtime::Runtime, search::{Control, Limits, Table, Worker}};
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::time::{Duration, Instant};

struct Counting;
static COUNTING: AtomicBool = AtomicBool::new(false);
static ALLOCATIONS: AtomicUsize = AtomicUsize::new(0);
unsafe impl GlobalAlloc for Counting {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if COUNTING.load(Ordering::Relaxed) { ALLOCATIONS.fetch_add(1, Ordering::Relaxed); }
        unsafe { System.alloc(layout) }
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) { unsafe { System.dealloc(pointer, layout) } }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        if COUNTING.load(Ordering::Relaxed) { ALLOCATIONS.fetch_add(1, Ordering::Relaxed); }
        unsafe { System.realloc(pointer, layout, size) }
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if COUNTING.load(Ordering::Relaxed) { ALLOCATIONS.fetch_add(1, Ordering::Relaxed); }
        unsafe { System.alloc_zeroed(layout) }
    }
}
#[global_allocator]
static ALLOCATOR: Counting = Counting;

pub(crate) fn fen(text: &str) -> Board { dev::fen(&text.split_whitespace().collect::<Vec<_>>()).expect(text) }

#[test]
fn published_perft_and_special_moves() {
    for (text, counts) in [
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", &[20,400,8902,197281][..]),
        ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", &[48,2039,97862][..]),
        ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", &[14,191,2812,43238][..]),
        ("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", &[6,264,9467][..]),
        ("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", &[44,1486,62379][..]),
        ("r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", &[46,2079,89890][..]),
    ] {
        let b = fen(text);
        for (i, &count) in counts.iter().enumerate() { assert_eq!(dev::perft(&b, i as u8 + 1), count, "{text} depth {}", i+1); }
    }
    let p = fen("1r5k/P7/8/8/8/8/8/4K3 w - - 0 1");
    for end in ["a8", "b8"] { for suffix in ["n", "b", "r", "q"] {
        let m = p.parse(&format!("a7{end}{suffix}")).unwrap();
        let child = p.play(m).unwrap();
        assert_eq!(child.cells[from(m)], 0); assert!(child.cells[to(m)] > 1);
        let mut rebuilt = child; rebuilt.rebuild(); assert_eq!(rebuilt.hash, child.hash); assert_eq!(rebuilt.score, child.score);
    }}
    let p = fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 27 19");
    let p = p.play(p.parse("e1c1").unwrap()).unwrap();
    assert_eq!((p.cells[0],p.cells[2],p.cells[3],p.castle,p.halfmove), (0,6,4,12,28));
    assert!(fen("4kr2/8/8/8/8/8/8/4K2R w K - 0 1").parse("e1g1").is_none());
    assert!(fen("1r2k3/8/8/8/8/8/8/R3K3 w Q - 0 1").parse("e1c1").is_some());
}

#[test]
fn legal_ep_identity_and_incremental_rebuild() {
    for (text, legal, uci) in [
        ("7k/8/8/r4pPK/8/8/8/8 w - f6 0 1",false,"g5f6"),
        ("6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 2",true,"e5d6"),
        ("k3r3/8/8/2PpP3/8/8/8/4K3 w - d6 0 1",true,"c5d6"),
    ] {
        let b = fen(text); let noep = fen(&text.replace(" f6 ", " - ").replace(" d6 ", " - "));
        assert_eq!(b.hash != noep.hash, legal); assert_eq!(b.parse(uci).is_some(), legal);
    }
    assert!(fen("k3r3/8/8/2PpP3/8/8/8/4K3 w - d6 0 1").parse("e5d6").is_none());
    let b = fen("6k1/8/8/3pP3/4K3/8/8/8 w - d6 0 1");
    assert!(b.in_check()); assert!(b.parse("e5d6").is_some()); assert!(b.parse("e5e6").is_none());
    for b in [Board::start(), fen("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"), b] {
        let moves = b.legal();
        for &m in &moves.a[..moves.n] {
            let child = b.play(m).unwrap(); let mut rebuilt = child; rebuilt.rebuild();
            assert_eq!((child.hash, child.score, child.ep, child.king), (rebuilt.hash, rebuilt.score, rebuilt.ep, rebuilt.king));
        }
    }
}

#[test]
fn strict_fen_admission_and_material_draws() {
    for text in [
        "8/8/8/8/8/8/8/8 w - - 0 1", "7k/8/8/8/8/8/8/K7 w - a4 0 1",
        "4k3/8/8/8/8/8/8/4K3 w KQ - 0 1", "r2k3r/8/8/8/8/8/8/4K3 b kq - 0 1",
        "4k3/8/8/8/8/8/8/R3K2r w K - 0 1", "7k/8/8/4P3/8/8/8/K7 w - d6 0 1",
        "7k/8/3N4/3pP3/8/8/8/K7 w - d6 0 1", "7k/8/8/8/4p3/8/8/K7 b - d3 0 1",
        "7k/8/8/8/8/8/8/K7 x - - 0 1", "7k/8/8/8/8/8/8/K7 w -- - 0 1",
        "7k/8/8/8/8/8/8/K7 w - - -1 1", "7k/8/8/8/8/8/8/K7 w - - 0 0",
        "7k/8/8/8/8/8/8/K6P w - - 0 1", "4k3/8/8/8/8/NNNNNNNN/NNNNNNNN/4K3 w - - 0 1",
        "7k/8/8/8/8/8/8/K7 w - - 65536 1", "8/8/8/8/8/8/4k3/4K3 w - - 0 1",
    ] { assert!(dev::fen(&text.split_whitespace().collect::<Vec<_>>()).is_none(), "admitted {text}"); }
    for (text, expected) in [
        ("7k/8/8/8/8/8/8/K7 w - - 0 1",true),
        ("7k/8/8/8/8/8/8/KN6 w - - 0 1",true),
        ("7k/8/8/8/8/8/5b2/K1B5 w - - 0 1",true),
        ("7k/8/8/8/8/8/8/KNN5 w - - 0 1",false),
        ("7k/8/8/8/8/8/8/KNB5 w - - 0 1",false),
        ("7k/8/8/8/8/8/4b3/K1B5 w - - 0 1",false),
    ] { assert_eq!(fen(text).dead(), expected, "{text}"); }
    let mate=fen("7k/6Q1/6K1/8/8/8/8/8 b - - 100 80");
    assert!(!dev::drawn(&mate,&[mate.hash]),"mate takes precedence over the fifty-move counter");
    let dead=fen("7k/8/8/8/8/8/8/K7 w - - 0 1");
    assert!(dev::drawn(&dead,&[dead.hash]),"dead material is a rule draw");
    // Development FEN accepts structural analysis positions, as the existing
    // engines do. The inactive king can already be checked in such a fixture.
    let queen=fen("7k/8/8/8/8/8/1Q6/K7 w - - 0 1");
    let rook=fen("7k/8/8/8/8/8/1R6/K7 w - - 0 1");
    assert!(queen.score>rook.score&&rook.score>0);
}

#[test]
fn repetition_third_occurrence_and_irreversible_reset() {
    let mut b = Board::start(); let mut keys = vec![b.hash];
    for (i, text) in ["g1f3","g8f6","f3g1","f6g8","g1f3","g8f6","f3g1","f6g8"].iter().enumerate() {
        b = b.play(b.parse(text).unwrap()).unwrap(); keys.push(b.hash);
        assert_eq!(dev::repeated(&b, &keys), i == 7);
    }
    assert_eq!(b.halfmove, 8);
    b = b.play(b.parse("e2e4").unwrap()).unwrap(); keys.push(b.hash);
    assert_eq!(b.halfmove,0); assert!(!dev::repeated(&b, &keys));
}

#[test]
fn recursive_board_and_search_allocate_only_at_startup() {
    let board = Board::start(); let table = Table::new(12); let control = Control::new();
    let mut worker = Worker::new(0); let frozen = [0;1024];
    control.reset(None,0);
    ALLOCATIONS.store(0,Ordering::Relaxed); COUNTING.store(true,Ordering::SeqCst);
    let count = dev::perft(&board,4);
    let result = worker.think(&board,&[board.hash],&frozen,0,Limits{depth:3,nodes:0,millis:None},&table,&control);
    COUNTING.store(false,Ordering::SeqCst);
    assert_eq!(count,197281); assert_eq!(result.depth,3); assert_ne!(result.best,0);
    assert_eq!(ALLOCATIONS.load(Ordering::Relaxed),0,"recursive board/search allocated after startup");
}

#[test]
fn runtime_frozen_correction_is_handed_over_only_to_the_next_go() {
    let mut runtime = Runtime::new(1,12).unwrap(); let b=Board::start(); let keys=[b.hash];
    runtime.start(&b,&keys,Limits{depth:3,nodes:0,millis:None});
    let until=Instant::now()+Duration::from_secs(5);
    while runtime.stats().0.depth<3 { assert!(Instant::now()<until,"first depth did not drain"); std::thread::sleep(Duration::from_millis(1)); }
    runtime.finish();
    let (first_frozen,learned)=runtime.snapshots();
    assert_eq!(first_frozen,[0;1024]); assert!(learned.iter().any(|&v|v!=0));
    let first_epoch=runtime.epoch(); let first_uses=runtime.statistics().uses;
    runtime.start(&b,&keys,Limits{depth:1,nodes:0,millis:None});
    let until=Instant::now()+Duration::from_secs(5);
    while runtime.stats().0.depth!=1 { assert!(Instant::now()<until,"second depth did not drain"); std::thread::sleep(Duration::from_millis(1)); }
    runtime.finish(); assert!(runtime.statistics().uses>first_uses,"next GO actually evaluated with its frozen snapshot");
    let (next_frozen,_)=runtime.snapshots(); assert_eq!(next_frozen,learned); assert_ne!(runtime.epoch(),first_epoch);
    runtime.reset(); assert_eq!(runtime.snapshots().1,[0;1024]);
}

#[test]
fn invalid_present_moving_clock_is_bounded_and_explicit_infinite_wins() {
    for side in [1,-1] {
        let mut b=Board::start();b.side=side;b.rebuild();
        let moving=if side>0 {"wtime"} else {"btime"};
        let other=if side>0 {"btime"} else {"wtime"};
        for value in ["garbage","-1","18446744073709551616","0"] {
            let command=format!("go {moving} {value} {other} 300000");
            let words:Vec<_>=command.split_whitespace().collect();
            assert_eq!(crate::limits(&b,&words).millis,Some(1),"side {side}: {command}");
        }
        let command=format!("go {other} 300000 {moving}");
        assert_eq!(crate::limits(&b,&command.split_whitespace().collect::<Vec<_>>()).millis,Some(1));
        let command=format!("go {moving} garbage infinite");
        assert_eq!(crate::limits(&b,&command.split_whitespace().collect::<Vec<_>>()).millis,None);
        let command=format!("go infinite {moving}");
        assert_eq!(crate::limits(&b,&command.split_whitespace().collect::<Vec<_>>()).millis,None);
        let command=format!("go {moving} 3000 {other} garbage");
        assert_eq!(crate::limits(&b,&command.split_whitespace().collect::<Vec<_>>()).millis,Some(100));
        let command=format!("go {moving} 3000 {moving} garbage");
        assert_eq!(crate::limits(&b,&command.split_whitespace().collect::<Vec<_>>()).millis,Some(1));
        let command=format!("go {moving} garbage {moving} 3000");
        assert_eq!(crate::limits(&b,&command.split_whitespace().collect::<Vec<_>>()).millis,Some(100));
    }
}
