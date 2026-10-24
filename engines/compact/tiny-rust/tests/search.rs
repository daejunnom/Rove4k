use super::*;
use crate::contracts::fen;
use std::sync::Arc;

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
    assert_eq!(completed.depth,1);assert!(b.parse(&crate::board::uci(completed.best)).is_some());
    t.clear();c.reset(None,100);w.reset();
    let partial=w.think(&b,&[b.hash],&f,0,Limits{depth:30,nodes:100,millis:None},&t,&c);
    assert!(c.cancelled());assert_eq!(c.nodes.load(Ordering::Relaxed),100);assert!(partial.depth>0&&partial.depth<30);
    assert!(b.parse(&crate::board::uci(partial.best)).is_some());
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
fn actual_max_ply_aborts_with_no_score_or_tt_bound() {
    std::thread::Builder::new().stack_size(1024*1024).spawn(|| {
        let mut w=Worker::new(0);let t=Table::new(18);let c=Control::new();
        let root=Board::start();let mut b=root;let mut history=vec![b.hash];let mut hints=Vec::new();
        let mut buckets=vec![(w.key(&b) as usize)&t.mask];
        for ply in 0..PLY-1 {
            let moves=b.legal();
            let (m,child)=moves.a[..moves.n].iter().filter_map(|&m| {
                let child=b.play(m).unwrap();
                let repeated=history.iter().rev().take(child.halfmove as usize).filter(|&&key|key==child.hash).count()>=2;
                let bucket=w.key(&child) as usize&t.mask;
                if child.halfmove>=100||repeated||child.dead()||child.legal().n==0||buckets.contains(&bucket) {None}
                else {Some((m,child))}
            }).min_by_key(|&(m,_)| {
                let pawn=b.cells[from(m)].abs()==1;
                ((b.halfmove>30&&!pawn) as u64)<<63|mix(m as u64^ply as u64)
            }).expect("deterministic legal max-ply path");
            let key=w.key(&b);t.put(key,Entry{mv:m,score:MATE-2,depth:0,bound:3},ply);
            hints.push((key,m));buckets.push(w.key(&child) as usize&t.mask);
            b=child;history.push(b.hash);
        }
        for &(key,m) in &hints {assert_eq!(t.get(key,0).unwrap().mv,m,"ordering fixture collided");}
        prepare(&mut w,&root);c.reset(None,256);
        assert!(w.search(&root,200,-MATE,MATE,0,0,&t,&c).is_none());assert!(c.cancelled());
        assert_eq!(w.stats.aborts,1);assert_eq!(w.nodes,PLY as u64);assert_eq!(c.nodes.load(Ordering::Relaxed),PLY as u64);
        for &(key,m) in &hints {let e=t.get(key,0).unwrap();assert_eq!((e.mv,e.depth,e.bound),(m,0,3),"partial normal bound replaced ordering hint");}
        println!("max-ply actual recursion: {} nodes on 1048576-byte worker stack",w.nodes);
    }).unwrap().join().unwrap();
}
