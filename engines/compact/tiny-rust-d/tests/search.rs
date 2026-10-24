use super::*;
use std::sync::Arc;

// Fixture-only FEN construction, never included in the shipping source.
fn fen(text:&str)->Board {
    let f:Vec<_>=text.split_whitespace().collect();assert_eq!(f.len(),6);
    let mut b=Board::empty();let rows:Vec<_>=f[0].split('/').collect();assert_eq!(rows.len(),8);
    for (r,row) in rows.iter().enumerate(){let mut file=0;for c in row.bytes(){
        if c.is_ascii_digit(){file+=(c-b'0')as usize;}else{
            let p=match c.to_ascii_lowercase(){b'p'=>1,b'n'=>2,b'b'=>3,b'r'=>4,b'q'=>5,b'k'=>6,_=>panic!("fixture piece")};
            b.cells[(7-r)*16+file]=if c.is_ascii_uppercase(){p}else{-p};file+=1;
        }
    }assert_eq!(file,8);}
    b.side=if f[1]=="w"{1}else{-1};for c in f[2].bytes(){b.castle|=match c{b'K'=>1,b'Q'=>2,b'k'=>4,b'q'=>8,b'-'=>0,_=>panic!("fixture rights")};}
    if f[3]!="-"{let q=f[3].as_bytes();b.ep=(q[1]-b'1')as i16*16+(q[0]-b'a')as i16;}
    b.halfmove=f[4].parse().unwrap();b.rebuild();b
}

fn perft(b:&Board,depth:u8)->u64 {if depth==0{return 1;}let m=b.pseudo();let mut n=0;for &m in &m.a[..m.n]{if let Some(c)=b.play(m){n+=perft(&c,depth-1);}}n}

#[test]
fn actual_board_perft_and_hce_incremental_rebuild() {
    let b=Board::start();assert_eq!(perft(&b,4),197281);
    let kiwi=fen("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1");assert_eq!(perft(&kiwi,3),97862);
    let q=fen("7k/8/8/8/8/8/1Q6/K7 w - - 0 1");let r=fen("7k/8/8/8/8/8/1R6/K7 w - - 0 1");assert!(q.score>r.score&&r.score>0);
    for b in [b,kiwi]{let m=b.legal();for &m in &m.a[..m.n]{let c=b.play(m).unwrap();let mut rebuilt=c;rebuilt.rebuild();
        assert_eq!((c.hash,c.score,c.bb,c.ep,c.king),(rebuilt.hash,rebuilt.score,rebuilt.bb,rebuilt.ep,rebuilt.king));
    }}
}

#[test]
fn legal_ep_identity_and_third_repetition_use_actual_board() {
    for (text,active) in [("7k/8/8/r4pPK/8/8/8/8 w - f6 0 1",false),("6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 2",true)]{
        let b=fen(text);let none=fen(&text.replace(" f6 "," - ").replace(" d6 "," - "));assert_eq!(b.hash!=none.hash,active);
    }
    let (mut w,t,c)=session();let mut b=Board::start();let mut keys=vec![b.hash];
    for (i,text) in ["g1f3","g8f6","f3g1","f6g8","g1f3","g8f6","f3g1","f6g8"].iter().enumerate(){
        b=b.play(b.parse(text).unwrap()).unwrap();keys.push(b.hash);w.keys[..keys.len()].copy_from_slice(&keys);w.length=keys.len();assert_eq!(w.repeated(&b),i==7);
    }
    c.reset(None,0);let result=w.think(&b,&keys,&[0;1024],0,Limits{depth:3,nodes:0,millis:None},&t,&c);assert_eq!(result.score,0);assert_eq!(result.best,0);
    b=b.play(b.parse("e2e4").unwrap()).unwrap();keys.push(b.hash);w.keys[..keys.len()].copy_from_slice(&keys);w.length=keys.len();assert!(!w.repeated(&b));assert_eq!(b.halfmove,0);
}

#[test]
fn recursive_actual_board_and_search_have_zero_allocator_calls() {
    let b=Board::start();let (mut w,t,c)=session();let f=[0;1024];
    crate::ALLOCATIONS.store(0,Ordering::Relaxed);crate::COUNTING.store(true,Ordering::SeqCst);
    let n=perft(&b,4);let r=w.think(&b,&[b.hash],&f,0,Limits{depth:3,nodes:0,millis:None},&t,&c);
    crate::COUNTING.store(false,Ordering::SeqCst);
    assert_eq!(n,197281);assert_eq!(r.depth,3);assert_eq!(crate::ALLOCATIONS.load(Ordering::Relaxed),0);
}

// RAW_DEEP_BEGIN
// This hook is std-free and can be appended inside the production search module
// in a separate raw-OS qualification image. It does not modify the module prefix.
pub fn qualification_deep_path(w:&mut Worker,t:&Table,c:&Control)->u64 {
    let root=Board::start();let mut b=root;let mut history=[0u64;PLY];history[0]=b.hash;
    let mut hints_key=[0u64;PLY];let mut hints_move=[0u32;PLY];let mut buckets=[0usize;PLY];buckets[0]=w.key(&b)as usize&t.mask;
    for ply in 0..PLY-1{
        let moves=b.legal();let mut selected=None;let mut priority=u64::MAX;
        for &m in &moves.a[..moves.n]{let child=b.play(m).unwrap();let begin=(ply+1).saturating_sub(child.halfmove as usize);
            let repeated=history[begin..=ply].iter().filter(|&&k|k==child.hash).count()>=2;let bucket=w.key(&child)as usize&t.mask;
            if child.halfmove>=100||repeated||child.dead()||child.legal().n==0||buckets[..=ply].contains(&bucket){continue;}
            let pawn=b.cells[from(m)].abs()==1;let rank=((b.halfmove>30&&!pawn)as u64)<<63|mix(m as u64^ply as u64);
            if selected.is_none()||rank<priority{selected=Some((m,child));priority=rank;}
        }
        let (m,child)=selected.expect("deterministic nonterminal max-ply path");let key=w.key(&b);
        t.put(key,Entry{mv:m,score:MATE-2,depth:0,bound:3},ply);hints_key[ply]=key;hints_move[ply]=m;buckets[ply+1]=w.key(&child)as usize&t.mask;
        b=child;history[ply+1]=b.hash;
    }
    for p in 0..PLY-1{assert_eq!(t.get(hints_key[p],0).unwrap().mv,hints_move[p]);}
    w.keys[0]=root.hash;w.length=1;w.nodes=0;w.choice=0;c.reset(None,256);
    let result=w.search(&root,200,-MATE,MATE,0,0,t,c);
    assert!(result.is_none()&&c.cancelled());assert_eq!(w.nodes,PLY as u64);assert_eq!(c.nodes.load(Ordering::Relaxed),PLY as u64);
    for p in 0..PLY-1{let e=t.get(hints_key[p],0).unwrap();assert_eq!((e.mv,e.depth,e.bound),(hints_move[p],0,3));}
    PLY as u64
}
// RAW_DEEP_END

pub fn standalone_probe()->(u64,u64,i32,u32,u64) {
    std::thread::Builder::new().stack_size(1024*1024).spawn(||{
        let mut w=Worker::new(0);let t=Table::new(18);let c=Control::new();
        crate::ALLOCATIONS.store(0,Ordering::Relaxed);crate::COUNTING.store(true,Ordering::SeqCst);
        let deepest=qualification_deep_path(&mut w,&t,&c);
        crate::COUNTING.store(false,Ordering::SeqCst);let alloc=crate::ALLOCATIONS.load(Ordering::Relaxed);
        assert_eq!(alloc,0);w.reset();t.clear();c.reset(None,0);let b=Board::start();
        let r=w.think(&b,&[b.hash],&[0;1024],0,Limits{depth:3,nodes:0,millis:None},&t,&c);
        assert_eq!(r.depth,3);assert!(b.legal().a[..b.legal().n].contains(&r.best));
        (deepest,alloc as u64,r.score,r.best,r.nodes)
    }).unwrap().join().unwrap()
}

#[test]
fn actual_one_mib_worker_stack_reaches_ply127_without_allocation_or_partial_tt() {
    let (nodes,alloc,score,best,search_nodes)=standalone_probe();assert_eq!((nodes,alloc),(128,0));
    println!("deep nodes={nodes} allocations={alloc}; depth3 score={score} best={best} nodes={search_nodes}");
}

fn session() -> (Worker, Table, Control) {
    let control=Control::new(); control.reset(None,0);
    (Worker::new(0),Table::new(12),control)
}
fn prepare(w:&mut Worker,b:&Board) {w.keys[0]=b.hash;w.length=1;w.nodes=0;w.choice=0;}

#[test]
fn full_key_publication_and_mate_distance_survive_colliding_writes() {
    let t=Table::new(8);
    t.put(1,Entry{mv:17,score:123,depth:7,bound:1},0);
    assert_eq!(t.get(1,0).unwrap().score,123);
    t.put(257,Entry{mv:18,score:-456,depth:4,bound:2},0);
    assert!(t.get(1,0).is_none()); assert_eq!(t.get(257,0).unwrap().score,-456);
    t.put(13,Entry{mv:19,score:MATE-10,depth:8,bound:1},7);
    assert_eq!(t.get(13,3).unwrap().score,MATE-6);
    t.put(14,Entry{mv:20,score:-MATE+10,depth:8,bound:1},7);
    assert_eq!(t.get(14,3).unwrap().score,-MATE+6);
    let t=Arc::new(t);
    std::thread::scope(|scope| {for worker in 0..4u64 {let t=t.clone();scope.spawn(move||{
        for i in 0..4000u64 {
            let key=(i*29+worker)%1024;let score=(key as i32)%1500-700;let mv=key as u32+1;
            t.put(key,Entry{mv,score,depth:3,bound:1},0);
            if let Some(e)=t.get(key,0) {assert_eq!((e.mv,e.score,e.depth,e.bound),(mv,score,3,1));}
        }
    });}});
}

#[test]
fn tt_context_includes_ordered_history_clock_and_frozen_epoch() {
    let (mut w,_,_)=session();
    let mut a=Board::start();for text in ["g1f3","g8f6","f3g1","f6g8"] {a=a.play(a.parse(text).unwrap()).unwrap();}
    let mut b=Board::start();for text in ["b1c3","b8c6","c3b1","c6b8"] {b=b.play(b.parse(text).unwrap()).unwrap();}
    assert_eq!(a.hash,b.hash);assert_eq!(a.halfmove,b.halfmove);assert_ne!(a.context,b.context);assert_ne!(w.key(&a),w.key(&b));
    let before=w.key(&a);a.halfmove+=1;assert_ne!(before,w.key(&a));a.halfmove-=1;
    w.epoch=1;assert_ne!(before,w.key(&a));
    let raw=a.score*a.side as i32;w.frozen[a.hash as usize&1023]=640;assert_eq!(w.evaluation(&a),raw+10);
    w.correction[a.hash as usize&1023]=9000;assert_eq!(w.evaluation(&a),raw+10,"learning must not mutate the active frozen evaluation");
    assert_eq!(w.stats.uses,2);
}

#[test]
fn actual_tt_cutoff_requires_legal_witness_and_sufficient_depth() {
    let (mut w,t,c)=session();let b=Board::start();prepare(&mut w,&b);let mv=b.parse("e2e4").unwrap();
    t.put(w.key(&b),Entry{mv,score:317,depth:5,bound:1},1);
    assert_eq!(w.search(&b,2,-MATE,MATE,1,0,&t,&c),Some(317));assert_eq!(w.nodes,1);
    c.reset(None,0);prepare(&mut w,&b);t.put(w.key(&b),Entry{mv:1,score:12345,depth:5,bound:1},1);
    let score=w.search(&b,1,-MATE,MATE,1,0,&t,&c).unwrap();assert!(score.abs()<1000,"illegal move must not witness TT cutoff");
}

#[test]
fn terminal_mate_precedes_fifty_move_draw_in_normal_and_qs_search() {
    let (mut w,t,c)=session();
    for depth in [0,3] {for (text,expected) in [
        ("7k/6Q1/6K1/8/8/8/8/8 b - - 100 80",-MATE),
        ("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",0),
        ("4k3/8/8/8/8/8/4K3/R7 w - - 100 1",0),
    ] {let b=fen(text);prepare(&mut w,&b);c.reset(None,0);assert_eq!(w.search(&b,depth,-MATE,MATE,0,0,&t,&c),Some(expected));}}
    let b=fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1");prepare(&mut w,&b);c.reset(None,0);
    assert_eq!(w.search(&b,0,-20000,-19000,0,0,&t,&c),Some(0),"stand pat cannot turn stalemate into a material score");
    let b=fen("4k3/8/8/8/8/8/4r3/4K3 w - - 0 1");assert!(b.in_check());prepare(&mut w,&b);c.reset(None,0);
    assert!(w.search(&b,0,-MATE,MATE,0,0,&t,&c).is_some());assert!(w.nodes>1,"QS must search legal quiet check evasions");
}

#[test]
fn node_abort_does_not_publish_an_unfinished_root_or_replace_last_completion() {
    let (mut w,t,c)=session();let b=Board::start();let f=[0;1024];
    let completed=w.think(&b,&[b.hash],&f,0,Limits{depth:1,nodes:0,millis:None},&t,&c);
    assert_eq!(completed.depth,1);assert!(b.legal().a[..b.legal().n].contains(&completed.best));
    t.clear();c.reset(None,100);w.reset();
    let partial=w.think(&b,&[b.hash],&f,0,Limits{depth:30,nodes:100,millis:None},&t,&c);
    assert!(c.cancelled());assert_eq!(c.nodes.load(Ordering::Relaxed),100);assert!(partial.depth>0&&partial.depth<30);
    assert!(b.legal().a[..b.legal().n].contains(&partial.best));
    let e=t.get(w.key(&b),0).expect("completed shallow root remains");assert_eq!(e.depth,partial.depth);
    t.clear();c.reset(None,1);prepare(&mut w,&b);
    assert!(w.search(&b,3,-MATE,MATE,0,0,&t,&c).is_none());assert!(t.get(w.key(&b),0).is_none());
    assert_eq!(c.nodes.load(Ordering::Relaxed),1);
}

#[test]
fn actual_search_updates_history_continuation_and_deferred_correction() {
    let (mut w,t,c)=session();let b=Board::start();let f=[0;1024];
    let result=w.think(&b,&[b.hash],&f,0,Limits{depth:4,nodes:0,millis:None},&t,&c);
    assert_eq!(result.depth,4);assert!(w.stats.pvs>0&&w.stats.qs>0&&w.stats.uses>0);
    assert!(w.stats.history>0&&w.stats.continuation>0&&w.stats.correction>0);
    assert!(w.history.iter().any(|&v|v!=0));assert!(w.continuation.iter().any(|&v|v!=0));assert!(w.correction.iter().any(|&v|v!=0));
    assert_eq!(w.frozen,f,"active GO evaluation remains frozen while learning");
}

#[test]
fn completed_mate_move_attains_score_and_terminal_reuse_has_no_stale_witness() {
    let (mut w,t,c)=session();let f=[0;1024];let start=Board::start();
    let initial=w.think(&start,&[start.hash],&f,0,Limits{depth:1,nodes:0,millis:None},&t,&c);assert_ne!(initial.best,0);
    let b=fen("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1");c.reset(None,0);
    let result=w.think(&b,&[b.hash],&f,0,Limits{depth:3,nodes:0,millis:None},&t,&c);
    assert_eq!(result.depth,3);assert_eq!(result.score,MATE-1);
    assert!(b.legal().a[..b.legal().n].contains(&result.best));let child=b.play(result.best).unwrap();assert!(child.in_check()&&child.legal().n==0);
    let entry=t.get(w.key(&b),0).unwrap();assert_eq!((entry.mv,entry.score,entry.bound),(result.best,result.score,1));
    for (text,score) in [("7k/6Q1/6K1/8/8/8/8/8 b - - 100 80",-MATE),
                        ("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",0),
                        ("4k3/8/8/8/8/8/4K3/R7 w - - 100 1",0)]{
        let b=fen(text);c.reset(None,0);let result=w.think(&b,&[b.hash],&f,0,Limits{depth:2,nodes:0,millis:None},&t,&c);
        assert_eq!((result.score,result.best,result.depth),(score,0,2));
    }
}
