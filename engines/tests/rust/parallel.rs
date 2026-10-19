fn execute(board: Board, variant: u8, workers: usize, tt_bits: usize,
           limits: Limits, control: Arc<Control>, mode: u8, counters: &Counters) -> Option<SearchResult> {
    let mut engine = Engine::new(variant, workers, tt_bits, control, mode).unwrap();
    let result = engine.execute(&board, &limits);
    for (to, from) in [&counters.jobs, &counters.cached, &counters.proposals, &counters.clauses, &counters.repairs, &counters.switches, &counters.policies, &counters.cross_group_alpha]
        .into_iter().zip([&engine.counters.jobs, &engine.counters.cached, &engine.counters.proposals, &engine.counters.clauses, &engine.counters.repairs, &engine.counters.switches, &engine.counters.policies, &engine.counters.cross_group_alpha]) { to.store(from.load(Ordering::Relaxed), Ordering::Relaxed); }
    result
}

use super::*;
fn limits(depth: u8) -> Limits { Limits { depth, nodes: 0, movetime: Some(Duration::from_secs(10)) } }
#[test]
fn split_modes_complete_and_pals_reuses_normal_repair() {
    // A unique mate avoids equal-score ordering differences among workers.
    let b = Board::from_fen("7k/8/5KQ1/8/8/8/8/8 w - - 0 1").unwrap();
    let winning = b.parse_move("g6g7").unwrap();
    for mode in 0..=4 {
        let l = limits(3); let ctrl = Arc::new(Control::new(&l)); let c = Counters::default();
        let r = execute(b.clone(), b'A', 4, 12, l, ctrl, mode, &c).unwrap();
        assert!(r.completed); assert_eq!(r.depth, 3); assert_eq!(r.best, winning, "mode {mode}");
        if mode == 3 { assert!(c.cached.load(Ordering::Relaxed) > 0); }
        if mode == 4 { assert!(c.switches.load(Ordering::Relaxed) > 0); }
    }
    // A mate proposal has no legal opponent reply. Use a nonterminal root
    // separately to exercise an actual counterreply and normal Repair.
    let l = limits(3); let ctrl = Arc::new(Control::new(&l)); let c = Counters::default();
    let r = execute(Board::start(), b'A', 4, 12, l, ctrl, 3, &c).unwrap();
    assert_eq!(r.depth, 3); assert!(c.clauses.load(Ordering::Relaxed) > 0);
    assert_eq!(c.repairs.load(Ordering::Relaxed), c.clauses.load(Ordering::Relaxed));
    assert!(c.cached.load(Ordering::Relaxed) > 0);
}
#[test]
fn original_node_budget_and_completed_depth_survive_cancellation() {
    for mode in 0..=4 {
        let l = Limits { depth: 40, nodes: 300, movetime: Some(Duration::from_secs(5)) };
        let ctrl = Arc::new(Control::new(&l)); let c = Counters::default();
        let r = execute(Board::start(), b'A', 4, 12, l, ctrl.clone(), mode, &c);
        assert!(ctrl.cancelled()); assert!(ctrl.nodes.load(Ordering::Relaxed) <= 300);
        if let Some(r) = r { assert!(r.completed); assert!(Board::start().legal().contains(&r.best)); }
        let after = ctrl.nodes.load(Ordering::Relaxed);
        thread::sleep(Duration::from_millis(5));
        assert_eq!(after, ctrl.nodes.load(Ordering::Relaxed), "helper outlived run");
    }
}
#[test]
fn group_policy_has_cross_group_completed_bounds() {
    let l = limits(2); let ctrl = Arc::new(Control::new(&l)); let c = Counters::default();
    let r = execute(Board::start(), b'A', 8, 12, l, ctrl, 2, &c).unwrap();
    assert_eq!(r.depth, 2); assert!(c.jobs.load(Ordering::Relaxed) >= 40);
    assert!(c.cross_group_alpha.load(Ordering::Relaxed) > 0);
    assert_eq!(group_count(b'A', 2, 512, 8), 1);
}
#[test]
fn hybrid_uses_observed_instability_and_time_cost() {
    let mut a = SearchResult { score: 0, best: Move { from: 1, to: 2, promo: 0 }, reply: None, depth: 2, nodes: 1, completed: true };
    let b = a; a.score = 100;
    let ctrl = Control::new(&limits(3));
    assert_eq!(policy(4, Some(a), Some(b), Duration::from_millis(1), &ctrl), 3);
    assert_eq!(policy(4, Some(b), Some(b), Duration::from_millis(1), &ctrl), 2);
    let tight = Control::new(&Limits { depth: 3, nodes: 0, movetime: Some(Duration::from_millis(1)) });
    assert_eq!(policy(4, Some(a), Some(b), Duration::from_millis(2), &tight), 0);
}
#[test]
fn f_retains_whole_root_mtd_convergence() {
    let l = limits(2); let ctrl = Arc::new(Control::new(&l)); let c = Counters::default();
    let r = execute(Board::start(), b'F', 2, 12, l, ctrl.clone(), 3, &c).unwrap();
    assert_eq!(r.depth, 2); assert_eq!(c.policies.load(Ordering::Relaxed), 1);
    assert_eq!(ctrl.conflicts.load(Ordering::Relaxed), 0);
}
