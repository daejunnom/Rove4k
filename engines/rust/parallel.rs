//! Search policies share only completed normal results. A constrained PALS
//! clause is diagnostic; Repair searches the same first move unrestricted.
use crate::board::{Board, Move};
use crate::search::{Control, Limits, SearchResult, Searcher, Table, INF, MATE};
use std::sync::{Arc, Mutex, atomic::{AtomicU64, AtomicUsize, Ordering}};
use std::thread;
use std::time::{Duration, Instant};

#[derive(Default)]
struct Counters {
    jobs: AtomicU64, cached: AtomicU64, proposals: AtomicU64,
    clauses: AtomicU64, repairs: AtomicU64, switches: AtomicU64,
    policies: AtomicU64, cross_group_alpha: AtomicU64,
}

fn completed(r: Option<SearchResult>) -> Option<SearchResult> { r.filter(|r| r.completed) }

// A full iteration owns its root result. Even with shared TT, worker-local
// histories and correction states need not have the same evaluation epoch.
fn loose_depth(b: &Board, searchers: &mut [Searcher], depth: u8, guess: i32) -> Option<SearchResult> {
    thread::scope(|scope| {
        let (leader, helpers) = searchers.split_first_mut().unwrap();
        leader.begin_depth();
        for s in helpers.iter_mut() { s.share_evaluation(leader); }
        let handles: Vec<_> = helpers.iter_mut().map(|s| scope.spawn(move || completed(s.iteration_frozen(b, depth, guess)))).collect();
        let mut best = completed(leader.iteration_frozen(b, depth, guess));
        // Deterministic worker priority, not an optimistic score comparison
        // across worker-local correction epochs.
        for h in handles { if let Ok(r) = h.join() { if best.is_none() { best = r; } } }
        best
    })
}

struct Root<'a> {
    board: &'a Board, moves: Vec<Move>, depth: u8,
    queue: AtomicUsize, alpha: AtomicU64,
    // The cache contains exact normal results for this board, depth and frozen
    // evaluation only. It never contains a restricted clause score.
    cache: Option<SearchResult>, best: Mutex<(SearchResult, usize)>,
    finished: AtomicUsize, control: &'a Control, counters: &'a Counters,
}
impl Root<'_> {
    fn work(&self, s: &mut Searcher, group: usize, mut i: usize) {
        while !self.control.cancelled() {
            let Some(&m) = self.moves.get(i) else { break; };
            // Score and producing group are one atomic publication. Thus the
            // observed cross-group bound counter cannot pair different writes.
            let bound = self.alpha.load(Ordering::Acquire);
            let alpha = bound as u32 as i32;
            let cached = self.cache.filter(|r| r.best == m);
            let result = if let Some(r) = cached {
                self.counters.cached.fetch_add(1, Ordering::Relaxed);
                Some(r)
            } else {
                if (bound >> 32) as usize != group { self.counters.cross_group_alpha.fetch_add(1, Ordering::Relaxed); }
                self.counters.jobs.fetch_add(1, Ordering::Relaxed);
                completed(s.search_move(self.board, m, self.depth, alpha, INF))
            };
            let Some(r) = result else { i = self.queue.fetch_add(1, Ordering::Relaxed); continue; };
            // With beta=INF, an uncached score above the original alpha is
            // exact; fail-low is an upper bound and cannot replace an exact
            // incumbent. Only a completed unrestricted result raises alpha.
            if cached.is_some() || r.score > alpha {
                let mut best = self.best.lock().unwrap();
                if r.score > best.0.score { *best = (r, group); }
                self.alpha.store(((best.1 as u64) << 32) | best.0.score as u32 as u64, Ordering::Release);
            }
            self.finished.fetch_add(1, Ordering::Relaxed);
            i = self.queue.fetch_add(1, Ordering::Relaxed);
        }
    }
}

fn split_depth(b: &Board, searchers: &mut [Searcher], depth: u8,
               previous: Option<SearchResult>, pals: bool, control: &Control,
               counters: &Counters, groups: usize) -> Option<SearchResult> {
    let workers = searchers.len();
    let (leader, helpers) = searchers.split_first_mut().unwrap();
    // Each depth has one frozen evaluation meaning, while every worker keeps
    // its own histories and pending correction updates across depths.
    leader.begin_depth();
    for s in helpers.iter_mut() { s.share_evaluation(leader); }
    let mut moves = b.legal();
    if let Some(old) = previous { if let Some(i) = moves.iter().position(|&m| m == old.best) { moves.swap(0, i); } }
    let first = *moves.first()?;
    counters.jobs.fetch_add(1, Ordering::Relaxed);
    let mut proposal = completed(leader.search_move(b, first, depth, -INF, INF))?;
    let mut cache = None;
    if pals && depth >= 2 {
        counters.proposals.fetch_add(1, Ordering::Relaxed);
        let replies = b.play(first).legal();
        // Prefer an alternative to the completed principal reply. This is a
        // question to investigate, never a proof about the unrestricted move.
        let reply = replies.iter().copied().find(|m| Some(*m) != proposal.reply).or_else(|| replies.first().copied());
        if let Some(reply) = reply {
            if completed(leader.search_clause(b, first, reply, depth, -INF, INF)).is_some() {
                counters.clauses.fetch_add(1, Ordering::Relaxed);
                counters.jobs.fetch_add(1, Ordering::Relaxed);
                proposal = completed(leader.search_move_hint(b, first, Some(reply), depth, -INF, INF))?;
                counters.repairs.fetch_add(1, Ordering::Relaxed);
            } else { return None; }
        }
        // Reassigning this move to the ordinary queue consumes a compatible
        // completed result, not the clause. The depth/epoch is fixed above.
        cache = Some(proposal);
    }
    let first_job = usize::from(cache.is_none());
    let root = Root { board: b, moves, depth,
        // Enroll one initial queue job per worker before any thread can drain
        // the remaining queue. Thereafter every job is claimed dynamically.
        queue: AtomicUsize::new(first_job + workers),
        alpha: AtomicU64::new(proposal.score as u32 as u64), cache,
        best: Mutex::new((proposal, 0)), finished: AtomicUsize::new(1), control, counters };
    thread::scope(|scope| {
        let handles: Vec<_> = helpers.iter_mut().enumerate().map(|(i, s)| { let root = &root;
            scope.spawn(move || root.work(s, (i + 1) * groups / workers, first_job + i + 1)) }).collect();
        root.work(leader, 0, first_job);
        // No state or table may be reused until every helper has physically
        // returned, even after the original control marks the work cancelled.
        for h in handles { h.join().expect("root search worker panicked"); }
    });
    let expected = root.moves.len() + usize::from(root.cache.is_some());
    if root.finished.load(Ordering::Relaxed) != expected { return None; }
    let mut r = root.best.lock().unwrap().0;
    r.nodes = control.nodes.load(Ordering::Relaxed);
    Some(r)
}

fn policy(mode: u8, previous: Option<SearchResult>, older: Option<SearchResult>,
          last_cost: Duration, control: &Control) -> u8 {
    if mode != 4 { return mode; }
    let (Some(a), Some(b)) = (previous, older) else { return if previous.is_none() { 1 } else { 2 }; };
    let unstable = a.best != b.best || (a.score - b.score).abs() >= 64;
    let tight = control.deadline.is_some_and(|d| d.saturating_duration_since(Instant::now()) <= last_cost.saturating_mul(2));
    // Expensive unstable iterations warrant a same-first Repair. Stable work
    // uses group locality; very little remaining time uses a whole-root race.
    if tight { 0 } else if unstable && last_cost >= Duration::from_micros(50) { 3 } else { 2 }
}

fn group_count(variant: u8, mode: u8, workers: usize, tt_bits: usize) -> usize {
    if variant == b'F' || mode != 2 && mode != 4 { return 1; }
    // Table's smallest supported allocation is 2^8 slots. Tiny development
    // budgets use fewer groups rather than multiplying that allocation.
    workers.div_ceil(4).min(1usize << tt_bits.clamp(8, 24).saturating_sub(8))
}

fn execute(board: Board, variant: u8, workers: usize, tt_bits: usize,
           limits: Limits, ctrl: Arc<Control>, mode: u8, counters: &Counters) -> Option<SearchResult> {
    assert!((1..=512).contains(&workers));
    assert!(mode <= 4);
    let effective = if variant == b'F' { 0 } else { mode };
    let groups = group_count(variant, effective, workers, tt_bits);
    // The exponent is a total TT allocation budget. Group-local tables divide
    // it rather than each silently allocating the entire requested memory.
    let group_shift = if groups == 1 { 0 } else { usize::BITS as usize - (groups - 1).leading_zeros() as usize };
    let tables: Vec<_> = (0..groups).map(|_| Arc::new(Table::new(tt_bits.saturating_sub(group_shift)))).collect();
    let mut searchers: Vec<_> = (0..workers).map(|i| Searcher::new(tables[i * groups / workers].clone(), ctrl.clone(), variant, i)).collect();
    if board.legal().is_empty() || board.halfmove >= 100 || board.repeated() || board.insufficient() {
        return completed(searchers[0].iteration(&board, 1, 0));
    }
    let (mut best, mut older, mut last_cost, mut last_policy) = (None, None, Duration::ZERO, 255);
    for depth in 1..=limits.depth.max(1) {
        if ctrl.cancelled() { break; }
        let selected = policy(effective, best, older, last_cost, &ctrl);
        if last_policy != 255 && selected != last_policy { counters.switches.fetch_add(1, Ordering::Relaxed); }
        counters.policies.fetch_or(1 << selected, Ordering::Relaxed);
        last_policy = selected;
        let start = Instant::now();
        let r = if selected == 0 { loose_depth(&board, &mut searchers, depth, best.map_or(0, |r: SearchResult| r.score)) }
            else { split_depth(&board, &mut searchers, depth, best, selected == 3, &ctrl, counters, groups) };
        last_cost = start.elapsed();
        let Some(r) = r else { break; };
        older = best;
        best = Some(r);
        let score = if r.score.abs() >= MATE - 128 { format!("mate {}", r.score.signum() * ((MATE - r.score.abs() + 1) / 2)) }
            else { format!("cp {}", r.score) };
        if crate::DEV { println!("info depth {} score {} nodes {} pv {}{}", r.depth, score,
            r.nodes, r.best.uci(), r.reply.map_or_else(String::new, |m| format!(" {}", m.uci()))); }
    }
    best
}

pub fn run(board: Board, variant: u8, workers: usize, tt_bits: usize,
           limits: Limits, ctrl: Arc<Control>, mode: u8) -> Option<SearchResult> {
    let counters = Counters::default();
    let result = execute(board, variant, workers, tt_bits, limits, ctrl, mode, &counters);
    if crate::DEV { println!("info string parallel mode {} effective {} workers {} groups {} root_jobs {} cache_hits {} proposals {} clauses {} repairs {} policy_switches {} policies {} cross_group_alpha {}",
        mode, if variant == b'F' { 0 } else { mode }, workers,
        group_count(variant, mode, workers, tt_bits),
        counters.jobs.load(Ordering::Relaxed), counters.cached.load(Ordering::Relaxed),
        counters.proposals.load(Ordering::Relaxed), counters.clauses.load(Ordering::Relaxed),
        counters.repairs.load(Ordering::Relaxed), counters.switches.load(Ordering::Relaxed),
        counters.policies.load(Ordering::Relaxed), counters.cross_group_alpha.load(Ordering::Relaxed)); }
    result
}

#[cfg(test)]
mod tests {
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
}
