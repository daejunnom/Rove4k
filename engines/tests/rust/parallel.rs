fn execute(board: Board, variant: u8, workers: usize, tt_bits: usize,
           limits: Limits, control: Arc<Control>, mode: u8, counters: &Counters) -> Option<SearchResult> {
    let mut engine = Engine::new(variant, workers, tt_bits, control, mode).unwrap();
    let result = engine.execute(&board, &limits);
    for (to, from) in [&counters.jobs, &counters.cached, &counters.proposals, &counters.clauses, &counters.repairs, &counters.switches, &counters.policies, &counters.cross_group_alpha, &counters.refutations, &counters.rechecks]
        .into_iter().zip([&engine.counters.jobs, &engine.counters.cached, &engine.counters.proposals, &engine.counters.clauses, &engine.counters.repairs, &engine.counters.switches, &engine.counters.policies, &engine.counters.cross_group_alpha, &engine.counters.refutations, &engine.counters.rechecks]) { to.store(from.load(Ordering::Relaxed), Ordering::Relaxed); }
    result
}

use super::*;
fn limits(depth: u8) -> Limits { Limits { depth, nodes: 0, movetime: Some(Duration::from_secs(10)) } }
#[test]
fn split_modes_complete_and_pals_caches_only_normal_proposals() {
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
    // separately to exercise an actual counterreply. A nonrefuting diagnostic
    // has no reason to Repair; the score/role tests below require this branch.
    let l = limits(3); let ctrl = Arc::new(Control::new(&l)); let c = Counters::default();
    let r = execute(Board::start(), b'A', 4, 12, l, ctrl, 3, &c).unwrap();
    assert_eq!(r.depth, 3); assert!(c.clauses.load(Ordering::Relaxed) > 0);
    assert!(c.cached.load(Ordering::Relaxed) > 0);
}

fn proposal(score: i32, first: Move, reply: Option<Move>, depth: u8) -> SearchResult {
    SearchResult { score, best: first, reply, depth, nodes: 7, completed: true }
}

#[test]
fn pals_scores_and_bounds_decide_whether_repair_is_needed() {
    let b = Board::start(); let first = b.parse_move("e2e4").unwrap();
    let reply = b.play(first).parse_move("e7e5").unwrap();
    let context = PalsContext { root: &b, depth: 4, evaluation: 19 };
    for (score, bound) in [(100, Bound::Lower), (120, Bound::Exact), (100, Bound::Upper), (50, Bound::Lower)] {
        let ctrl = Control::new(&limits(4)); let counters = Counters::default(); let mut calls = 0;
        let r = review_pals(proposal(100, first, None, 4), reply, context, &ctrl, &counters, |q| {
            calls += 1; assert!(!q.repair); assert_eq!((q.alpha, q.beta), (99, 100));
            Some(PalsResult { context: q.context, result: proposal(score, first, Some(reply), 4), bound })
        }).unwrap();
        assert_eq!(calls, 1); assert_eq!(r.score, 100); assert_eq!(r.reply, None);
        assert_eq!(counters.repairs.load(Ordering::Relaxed), 0);
        assert_eq!(counters.refutations.load(Ordering::Relaxed), 0);
    }
    // Request-relative classification matters: a fail-high lower bound is not
    // an exact value; a fail-low upper bound is sufficient to refute the claim.
    let q = PalsRequest { context, first, reply, repair: false, alpha: 99, beta: 100 };
    assert_eq!(PalsResult::from_search(q, proposal(100, first, Some(reply), 4)).bound, Bound::Lower);
    assert_eq!(PalsResult::from_search(q, proposal(99, first, Some(reply), 4)).bound, Bound::Upper);
}

#[test]
fn pals_repairs_same_first_and_reviews_same_reply_against_updated_claim() {
    let b = Board::start(); let first = b.parse_move("e2e4").unwrap();
    let reply = b.play(first).parse_move("e7e5").unwrap();
    let context = PalsContext { root: &b, depth: 4, evaluation: 21 };
    for refuting_bound in [Bound::Upper, Bound::Exact] {
        let ctrl = Control::new(&limits(4)); let counters = Counters::default(); let mut calls = 0;
        let r = review_pals(proposal(100, first, None, 4), reply, context, &ctrl, &counters, |q| {
            calls += 1; assert_eq!(q.first, first); assert_eq!(q.reply, reply);
            let (score, bound) = match calls {
                1 => { assert!(!q.repair); assert_eq!((q.alpha, q.beta), (99, 100)); (50, refuting_bound) },
                2 => { assert!(q.repair); assert_eq!((q.alpha, q.beta), (-INF, INF)); (20, Bound::Exact) },
                3 => { assert!(!q.repair); assert_eq!((q.alpha, q.beta), (19, 20)); (20, Bound::Lower) },
                _ => panic!("unbounded PALS negotiation"),
            };
            Some(PalsResult { context: q.context, result: proposal(score, first, Some(reply), 4), bound })
        }).unwrap();
        assert_eq!(calls, 3); assert_eq!(r.score, 20); assert_eq!(r.best, first);
        assert_eq!(counters.repairs.load(Ordering::Relaxed), 1);
        assert_eq!(counters.clauses.load(Ordering::Relaxed), 2);
        assert_eq!(counters.rechecks.load(Ordering::Relaxed), 1);
        assert_eq!(counters.refutations.load(Ordering::Relaxed), 1);
    }
}

#[test]
fn pals_unresolved_contradiction_or_nonexact_repair_rejects_depth() {
    let b = Board::start(); let first = b.parse_move("e2e4").unwrap();
    let reply = b.play(first).parse_move("e7e5").unwrap();
    let context = PalsContext { root: &b, depth: 4, evaluation: 22 };
    for repair_bound in [Bound::Exact, Bound::Lower, Bound::Upper] {
        let ctrl = Control::new(&limits(4)); let counters = Counters::default(); let mut calls = 0;
        let r = review_pals(proposal(100, first, None, 4), reply, context, &ctrl, &counters, |q| {
            calls += 1;
            let (score, bound) = if q.repair { (40, repair_bound) } else { (30, Bound::Upper) };
            Some(PalsResult { context: q.context, result: proposal(score, first, Some(reply), 4), bound })
        });
        assert!(r.is_none());
        assert_eq!(calls, if repair_bound == Bound::Exact { 3 } else { 2 });
        assert_eq!(counters.repairs.load(Ordering::Relaxed), 1);
    }
}

#[test]
fn pals_incomplete_mismatched_or_cancelled_results_are_never_proposals() {
    let b = Board::start(); let other = b.clone(); let first = b.parse_move("e2e4").unwrap();
    let reply = b.play(first).parse_move("e7e5").unwrap();
    let context = PalsContext { root: &b, depth: 4, evaluation: 23 };
    // Exercise every phase, rather than accepting a partial Repair on failure.
    for fail_at in 1..=3 {
        for failure in 0..9 {
            let l = Limits { depth: 4, nodes: 999, movetime: Some(Duration::from_secs(10)) };
            let ctrl = Control::new(&l); let deadline = ctrl.deadline(); let counters = Counters::default(); let mut calls = 0;
            let r = review_pals(proposal(100, first, None, 4), reply, context, &ctrl, &counters, |q| {
                calls += 1;
                let score = if calls == 1 { 50 } else if q.repair { 40 } else { 40 };
                let mut r = PalsResult::from_search(q, proposal(score, first, Some(reply), 4));
                if calls == fail_at { match failure {
                    0 => return None,
                    1 => r.result.completed = false,
                    2 => r.result.best = Move::default(),
                    3 => r.result.depth -= 1,
                    4 => r.context.evaluation += 1,
                    5 => r.context.depth -= 1,
                    6 => r.context.root = &other,
                    7 => { if !q.repair { r.result.reply = None; } else { r.bound = Bound::Lower; } },
                    _ => ctrl.stop.store(true, Ordering::Relaxed),
                }}
                Some(r)
            });
            assert!(r.is_none(), "phase {fail_at} failure {failure}"); assert_eq!(calls, fail_at);
            assert_eq!(ctrl.deadline(), deadline); assert_eq!(ctrl.node_limit.load(Ordering::Relaxed), 999);
            assert_eq!(ctrl.nodes.load(Ordering::Relaxed), 0, "review must not reset or grant nodes");
        }
    }
    let ctrl = Control::new(&limits(4)); ctrl.stop.store(true, Ordering::Relaxed);
    assert!(review_pals(proposal(100, first, None, 4), reply, context, &ctrl, &Counters::default(), |_| panic!("cancelled review ran")).is_none());
    for score in [-INF, INF, i32::MIN, i32::MAX] {
        let ctrl = Control::new(&limits(4));
        assert!(review_pals(proposal(score, first, None, 4), reply, context, &ctrl, &Counters::default(), |_| panic!("sentinel claim ran")).is_none());
    }
}

#[test]
fn pals_real_repair_investigates_challenger_before_reusing_normal_tt() {
    let b = Board::start(); let l = limits(3); let ctrl = Arc::new(Control::new(&l));
    let mut engine = Engine::new(b'A', 1, 16, ctrl.clone(), 3).unwrap();
    let first = engine.execute(&b, &l).unwrap(); assert_eq!(first.depth, 3);
    // A deeper ordinary result is an eligible shallow TT shortcut. Repair must
    // bypass it at the reply node and put the actual challenger before TT move.
    let first_move = first.best;
    let normal = engine.leader.search_move(&b, first_move, 2, -INF, INF).unwrap();
    let reply = b.play(first_move).legal().into_iter().find(|m| Some(*m) != normal.reply).unwrap();
    let before = ctrl.nodes.load(Ordering::Relaxed);
    let cached = engine.leader.search_move(&b, first_move, 2, -INF, INF).unwrap();
    assert_eq!(cached.score, normal.score);
    assert_eq!(ctrl.nodes.load(Ordering::Relaxed) - before, 1, "positive TT cutoff control");
    let before = ctrl.nodes.load(Ordering::Relaxed);
    let repaired = engine.leader.search_move_hint(&b, first_move, Some(reply), 2, -INF, INF).unwrap();
    assert_eq!(engine.leader.repair_first, Some(reply));
    assert!(ctrl.nodes.load(Ordering::Relaxed) - before > 1, "Repair returned cached proposal");
    assert!(repaired.completed); assert_eq!(repaired.best, first_move);
    drop(engine);
    ctrl.reset(&l);
    let mut engine = Engine::new(b'A', 1, 16, ctrl.clone(), 3).unwrap();
    assert_eq!(engine.execute(&b, &l).unwrap().depth, 3);
    // Original Control is reset only between separate GO sessions by its owner.
    // A retained-TT session must repair that shallow proposal, not repeat the
    // old TT shortcut and manufacture an unresolved contradiction.
    ctrl.reset(&l);
    let second = engine.execute(&b, &l).unwrap();
    assert!(second.completed); assert_eq!(second.depth, 3); assert!(b.legal().contains(&second.best));
    assert_eq!(engine.counters.repairs.load(Ordering::Relaxed), 1);
    assert_eq!(engine.counters.rechecks.load(Ordering::Relaxed), 1);
    assert_eq!(engine.counters.refutations.load(Ordering::Relaxed), 1);
    assert_eq!(engine.counters.cached.load(Ordering::Relaxed), 2);
}

#[test]
fn pals_restricted_reply_preserves_draw_before_irreversible_reply() {
    let clock = Board::from_fen("7k/p7/8/8/8/8/8/R6K w - - 99 1").unwrap();
    let mut repetition = Board::start();
    for text in ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1"] {
        repetition = repetition.play(repetition.parse_move(text).unwrap());
    }
    assert!(!repetition.repeated());
    for (board, first_text, reply_text) in [(clock, "h1g1", "a7a6"), (repetition, "f6g8", "a2a3")] {
        let first = board.parse_move(first_text).unwrap(); let child = board.play(first);
        assert!(child.halfmove >= 100 || child.repeated());
        let reply = child.parse_move(reply_text).unwrap(); let after = child.play(reply);
        assert_eq!(after.halfmove, 0); assert!(!after.repeated());
        let l = limits(2); let ctrl = Arc::new(Control::new(&l));
        let mut engine = Engine::new(b'A', 1, 12, ctrl.clone(), 3).unwrap();
        let raw = engine.leader.iteration(&after, 1, 0).unwrap();
        assert_ne!(raw.score, 0, "post-reply position must distinguish skipped terminal draw");
        let normal = engine.leader.search_move(&board, first, 2, -INF, INF).unwrap();
        assert_eq!(normal.score, 0);
        let clause = engine.leader.search_clause(&board, first, reply, 2, -INF, INF).unwrap();
        assert!(clause.completed); assert_eq!(clause.score, 0); assert_eq!(clause.best, first); assert_eq!(clause.reply, Some(reply));
        assert!(engine.leader.search_clause(&board, first, Move::default(), 2, -INF, INF).is_none());
        ctrl.stop.store(true, Ordering::Relaxed);
        assert!(engine.leader.search_clause(&board, first, reply, 2, -INF, INF).is_none());
    }
    // The same rule applies to an already-drawn root even if the first move
    // itself resets the halfmove clock before the requested reply is played.
    let board = Board::from_fen("7k/p7/8/8/8/8/8/R6K w - - 100 1").unwrap();
    let first = board.parse_move("a1a7").unwrap(); let child = board.play(first);
    assert_eq!(child.halfmove, 0); let reply = child.parse_move("h8g8").unwrap();
    let l = limits(2); let ctrl = Arc::new(Control::new(&l));
    let mut engine = Engine::new(b'A', 1, 12, ctrl, 3).unwrap();
    assert_ne!(engine.leader.iteration(&child.play(reply), 1, 0).unwrap().score, 0);
    assert_eq!(engine.leader.search_move(&board, first, 2, -INF, INF).unwrap().score, 0);
    let clause = engine.leader.search_clause(&board, first, reply, 2, -INF, INF).unwrap();
    assert_eq!(clause.score, 0); assert_eq!(clause.reply, Some(reply));
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
