// Appended fixture only. The old/new production search prefix stays exact.
use super::*;

pub type DepthWitness=(u32,i32,u8,u64,u64,[i16;1024]);

pub fn depth_two()->DepthWitness {
    crate::os::set_clock(0);
    let mut worker=Worker::new(0);
    let table=Table::new(18);
    let control=Control::new();
    control.reset(None,0);
    let board=Board::start();
    let frozen=[0;1024];
    let result=worker.think(&board,&[board.hash],&frozen,0,
        Limits{depth:2,nodes:0,millis:None},&table,&control);
    assert_eq!(result.depth,2);
    assert!(board.legal().a[..board.legal().n].contains(&result.best));
    assert_eq!(result.nodes,worker.nodes);
    assert_eq!(worker.frozen,frozen);
    assert!(!control.cancelled());
    (result.best,result.score,result.depth,result.nodes,worker.nodes,worker.correction)
}

pub fn three_claims_with_budget_two()->(u64,u64,bool) {
    crate::os::set_clock(0);
    let control=Control::new();
    control.reset(None,2);
    let mut worker=Worker::new(0);
    let mut accepted=0;
    for _ in 0..3 {accepted+=u64::from(worker.claim(&control).is_some());}
    (accepted,worker.nodes,control.cancelled())
}

pub fn pre_stopped()->(u64,u64,bool) {
    crate::os::set_clock(0);
    let control=Control::new();
    control.reset(Some(1),2);
    crate::os::set_clock(2);
    control.stop.store(true,Ordering::Relaxed);
    let mut worker=Worker::new(0);
    let before=crate::os::clock_reads();
    assert!(worker.claim(&control).is_none());
    let reads=crate::os::clock_reads()-before;
    assert_eq!(worker.nodes,0);
    assert_eq!(reads,0,"stop must precede even an expired deadline read");
    assert!(control.cancelled());
    (worker.nodes,reads,control.cancelled())
}

pub fn deadline_boundary()->(u64,u64,u64,bool) {
    crate::os::set_clock(0);
    let control=Control::new();
    control.reset(Some(10),2);
    assert_eq!(control.deadline_ms.load(Ordering::Relaxed),10);
    let mut worker=Worker::new(0);
    let before=crate::os::clock_reads();
    crate::os::set_clock(9);
    assert!(worker.claim(&control).is_some());
    assert_eq!(worker.nodes,1);
    assert_eq!(crate::os::clock_reads()-before,1);
    crate::os::set_clock(10);
    for _ in 1..256 {assert!(worker.claim(&control).is_some());}
    assert_eq!(worker.nodes,256);
    let before_boundary=crate::os::clock_reads()-before;
    assert_eq!(before_boundary,1,"claims at local counts 1..255 must not read time");
    assert!(!control.cancelled());
    assert!(worker.claim(&control).is_none());
    let after_boundary=crate::os::clock_reads()-before;
    assert_eq!(worker.nodes,256,"expired claim must not increment local count");
    assert_eq!(after_boundary,2);
    assert!(control.cancelled());
    (worker.nodes,before_boundary,after_boundary,control.cancelled())
}
