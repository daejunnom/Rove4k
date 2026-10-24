use super::*;
fn session(variant:u8,nodes:u64)->Searcher {
    let limits=Limits{depth:6,nodes,movetime:None};
    Searcher::new(Arc::new(Table::new(10)),Arc::new(Control::new(&limits)),variant,0)
}
#[test]
fn isolated_exclusion_does_not_touch_normal_bounds_or_learning() {
    let b=Board::start();let first=b.parse_move("e2e4").unwrap();
    let mut s=session(b'B',0);s.begin_depth();let key=s.key(&b);
    assert!(s.table.put(Entry{key,mv:first,depth:50,lower:12345,upper:12345},0,&s.control));
    let history=s.history.clone();let continuation=s.continuation.clone();let correction=s.correction.clone();
    let before=b.fen();
    let score=s.negamax(&b,1,-INF,INF,0,Move::default(),Some(first),true).unwrap();
    assert!(score.abs()<1000,"excluded probe must not consume normal exact TT value");
    assert_eq!(s.table.get(key,0).unwrap().lower,12345);
    assert_eq!(s.history,history);assert_eq!(s.continuation,continuation);assert_eq!(s.correction,correction);assert_eq!(b.fen(),before);
}
#[test]
fn mtd_converges_with_stable_evaluation_and_monotone_bounds() {
    let b=Board::from_fen("4k3/8/8/3p4/4P3/8/4K3/8 w - - 0 1").unwrap();
    for depth in 1..=3 {
        let mut f=session(b'F',0);let mut p=session(b'A',0);
        let expected=p.iteration(&b,depth,0).unwrap();let actual=f.iteration(&b,depth,157).unwrap();
        assert_eq!(actual.score,expected.score);
        let trace=f.control.trace.lock().unwrap();assert!(!trace.is_empty());
        let(mut low,mut high)=(-INF,INF);
        for &(d,l,h,epoch) in trace.iter(){assert_eq!(d,depth);assert!(l>=low&&h<=high&&l<=h);assert_eq!(epoch,0);low=l;high=h;}
        assert_eq!(low,high);assert_eq!(low,actual.score);assert_eq!(f.control.conflicts.load(Ordering::Relaxed),0);
    }
}
#[test]
fn unfinished_depth_has_no_completed_result() {
    let b=Board::start();let mut s=session(b'F',160);
    let completed=s.iteration(&b,1,0).unwrap();assert!(completed.completed);
    let unfinished=s.iteration(&b,8,completed.score);assert!(unfinished.is_none());
    assert!(b.legal().contains(&completed.best));assert!(s.control.nodes.load(Ordering::Relaxed)<=160);
}
#[test]
fn concurrent_tt_reads_never_accept_mixed_record() {
    let table=Arc::new(Table::new(8));let c=session(b'F',0).control;
    std::thread::scope(|scope|{for worker in 0..4 {let table=table.clone();let c=c.clone();scope.spawn(move||{
        for i in 0..2000u64 {let key=(i*17+worker)%512;let v=(key as i32)%1500;let mv=Move{from:(key&7)as u8,to:16+(key&7)as u8,promo:0};
            assert!(table.put(Entry{key,mv,depth:3,lower:v,upper:v},0,&c));
            if let Some(e)=table.get(key,0){assert_eq!(e.key,key);assert_eq!(e.lower,v);assert_eq!(e.upper,v);assert_eq!(e.mv,mv);}
        }
    });}});
}
#[test]
#[cfg(not(rove_f_single))]
fn interval_merge_retains_its_lower_bound_move_witness() {
    let s=session(b'F',0);let good=Move{from:4,to:20,promo:0};let upper_hint=Move{from:3,to:19,promo:0};
    assert!(s.table.put(Entry{key:77,mv:good,depth:4,lower:120,upper:INF},0,&s.control));
    assert!(s.table.put(Entry{key:77,mv:upper_hint,depth:4,lower:-INF,upper:120},0,&s.control));
    let e=s.table.get(77,0).unwrap();assert_eq!((e.lower,e.upper),(120,120));assert_eq!(e.mv,good);
}
#[test]
fn b_normal_search_executes_eligible_same_ply_singular_probe() {
    let b=Board::from_fen("4k3/8/8/3q4/8/8/4K3/3Q4 w - - 0 1").unwrap();
    let mut s=session(b'B',12000);let _=s.iteration(&b,3,0).unwrap();
    let key=s.key(&b);assert!(s.table.get(key,0).is_some());
    // Keep the exact same frozen evaluation as the completed TT result.
    // This is the normal recursive search, not the exclusion test helper.
    let _=s.negamax(&b,6,-INF,INF,0,Move::default(),None,false);
    assert!(s.control.singular.load(Ordering::Relaxed)>0);
    assert!(s.control.see_calls.load(Ordering::Relaxed)>0);
}
#[test]
fn b_cancelled_ordering_cannot_publish_a_normal_tt_bound(){
    let b=Board::from_fen("4k3/8/8/3q4/8/8/4K3/3Q4 w - - 0 1").unwrap();let mut s=session(b'B',1);s.begin_depth();
    assert!(s.negamax(&b,1,-INF,INF,0,Move::default(),None,false).is_err());
    assert!(s.table.get(s.key(&b),0).is_none());assert_eq!(s.control.nodes.load(Ordering::Relaxed),1);
    assert!(s.control.stop.load(Ordering::Relaxed));
}
#[test]
fn converged_root_move_witness_achieves_the_completed_score() {
    let b=Board::from_fen("4k3/8/2r5/3p4/4P3/8/4K3/3R4 w - - 0 1").unwrap();
    let mut s=session(b'F',0);let result=s.iteration(&b,3,900).unwrap();
    let mut exact=session(b'F',0);exact.begin_depth();
    let moves=b.legal();let scores:Vec<_>=moves.iter().map(|&m|exact.search_move(&b,m,3,-INF,INF).unwrap().score).collect();
    assert_eq!(result.score,*scores.iter().max().unwrap());
    assert_eq!(result.score,scores[moves.iter().position(|&m|m==result.best).unwrap()]);
}
#[test]
fn control_reset_reuses_storage_and_handles_large_clock_values() {
    let c=Control::new(&Limits{depth:2,nodes:1,movetime:Some(Duration::ZERO)});
    assert!(c.cancelled());c.probes.store(9,Ordering::Relaxed);c.nodes.store(1,Ordering::Relaxed);
    c.reset(&Limits{depth:3,nodes:100,movetime:None});
    assert!(!c.cancelled());assert!(c.deadline().is_none());assert_eq!(c.probes.load(Ordering::Relaxed),0);assert_eq!(c.nodes.load(Ordering::Relaxed),0);
    c.reset(&Limits{depth:3,nodes:0,movetime:Some(Duration::from_millis(u64::MAX))});
    assert!(c.deadline().is_some());assert!(!c.cancelled());
}
#[test]
fn terminal_reuse_cannot_publish_a_previous_root_move() {
    let mut s=session(b'A',0);let first=s.iteration(&Board::start(),1,0).unwrap();assert_ne!(first.best,Move::default());
    for(fen,score)in [
        ("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1",-MATE),
        ("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",0),
        ("4k3/8/8/8/8/8/4K3/R7 w - - 100 1",0),
    ]{let terminal=Board::from_fen(fen).unwrap();let r=s.iteration(&terminal,1,0).unwrap();assert_eq!(r.score,score);assert_eq!(r.best,Move::default());assert!(r.reply.is_none());}
}
#[test]
fn fixed_storage_reaches_the_ply_limit_on_the_actual_one_mib_worker_stack(){
    std::thread::Builder::new().stack_size(1024*1024).spawn(||{
        let limits=Limits{depth:96,nodes:0,movetime:None};let control=Arc::new(Control::new(&limits));
        let mut s=Searcher::new(Arc::new(Table::new(18)),control.clone(),b'B',0);s.begin_depth();
        let root=Board::start();let mut b=root;let mut hints=Vec::new();
        for ply in 0..96{
            let moves=b.legal();
            let m=moves.iter().copied().filter(|&m|{let c=b.play(m);!c.repeated()&&c.halfmove<100&&!c.insufficient()&&!c.legal().is_empty()})
                .min_by_key(|&m|{let pawn=b.cells[m.from as usize].unsigned_abs()==1;((b.halfmove>30&&!pawn)as u64)<<63|mix(encode_move(m)^ply)}).unwrap();
            let key=s.key(&b);assert!(s.table.put(Entry{key,mv:m,depth:0,lower:-INF,upper:INF},ply as usize,&control));
            hints.push((key,m));b=b.play(m);
        }
        for&(key,m)in&hints{assert_eq!(s.table.get(key,0).unwrap().mv,m,"TT ordering fixture collision");}
        control.reset(&Limits{depth:96,nodes:97,movetime:Some(Duration::from_secs(5))});
        assert!(s.negamax(&root,96,-INF,INF,0,Move::default(),None,false).is_err());
        assert_eq!(control.deepest.load(Ordering::Relaxed),96);assert_eq!(control.nodes.load(Ordering::Relaxed),97);
    }).unwrap().join().unwrap();
}
