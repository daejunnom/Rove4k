// Old, unmodified search module only. Never appended to tiny_shipping source.
pub fn default_budget_two()->(u64,u64,u64,bool) {
    crate::os::set_clock(0);
    let control=Control::new();
    control.reset(None,2);
    let mut worker=Worker::new(0);
    let mut accepted=0;
    for _ in 0..3 {accepted+=u64::from(worker.claim(&control).is_some());}
    let global=control.nodes.load(Ordering::Relaxed);
    assert_eq!((accepted,worker.nodes,global),(2,2,2));
    assert!(control.cancelled());
    (accepted,worker.nodes,global,control.cancelled())
}
