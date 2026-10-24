//! Search policies share only completed normal results. A constrained PALS
//! clause is diagnostic; Repair searches the same first move unrestricted.
use crate::board::{Board, Move, MoveList};
use crate::search::{Control, Limits, SearchResult, Searcher, Table, INF, MATE};
use crate::pool::{Helpers, Task};
use std::io;
use std::sync::{Arc, Mutex, atomic::{AtomicU64, AtomicUsize, Ordering}};
#[cfg(test)] use std::thread;
use std::time::{Duration, Instant};

#[derive(Default)]
struct Counters {
    jobs: AtomicU64, cached: AtomicU64, proposals: AtomicU64,
    clauses: AtomicU64, repairs: AtomicU64, switches: AtomicU64,
    policies: AtomicU64, cross_group_alpha: AtomicU64,
    refutations: AtomicU64, rechecks: AtomicU64,
}
impl Counters {
    fn reset(&self) {
        for counter in [&self.jobs, &self.cached, &self.proposals, &self.clauses, &self.repairs, &self.switches, &self.policies, &self.cross_group_alpha, &self.refutations, &self.rechecks] { counter.store(0, Ordering::Relaxed); }
    }
}

fn completed(r: Option<SearchResult>) -> Option<SearchResult> { r.filter(|r| r.completed) }

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Bound { Exact, Lower, Upper }
#[derive(Clone, Copy)]
struct PalsContext<'a> { root: &'a Board, depth: u8, evaluation: u64 }
impl PalsContext<'_> {
    fn matches(self, other: Self) -> bool {
        std::ptr::eq(self.root, other.root) && self.depth == other.depth && self.evaluation == other.evaluation
    }
}
#[derive(Clone, Copy)]
struct PalsRequest<'a> {
    context: PalsContext<'a>, first: Move, reply: Move, repair: bool, alpha: i32, beta: i32,
}
#[derive(Clone, Copy)]
struct PalsResult<'a> { context: PalsContext<'a>, result: SearchResult, bound: Bound }
impl<'a> PalsResult<'a> {
    fn from_search(request: PalsRequest<'a>, result: SearchResult) -> Self {
        let bound = if result.score <= request.alpha { Bound::Upper }
            else if result.score >= request.beta { Bound::Lower } else { Bound::Exact };
        Self { context: request.context, result, bound }
    }
    fn matches(self, request: PalsRequest<'a>) -> bool {
        self.context.matches(request.context) && self.result.completed && self.result.depth == request.context.depth
            && self.result.best == request.first && (request.repair || self.result.reply == Some(request.reply))
    }
}

// A restricted reply can refute a fixed proposal claim, but is never a normal
// root result. Only the full-window same-first Repair can replace the proposal.
// The second review uses the repaired claim and the very same refuting reply.
// Persistent contradiction, incomplete work or cancellation rejects this depth.
fn review_pals<'a>(mut proposal: SearchResult, reply: Move, context: PalsContext<'a>,
                   control: &Control, counters: &Counters,
                   mut run: impl FnMut(PalsRequest<'a>) -> Option<PalsResult<'a>>) -> Option<SearchResult> {
    if !proposal.completed || proposal.depth != context.depth || !(-INF+1..INF).contains(&proposal.score) || control.cancelled() { return None; }
    let first = proposal.best;
    for review in 0..2 {
        if control.cancelled() { return None; }
        let claim = proposal.score;
        let request = PalsRequest { context, first, reply, repair: false, alpha: claim - 1, beta: claim };
        counters.jobs.fetch_add(1, Ordering::Relaxed);
        counters.clauses.fetch_add(1, Ordering::Relaxed);
        if review != 0 { counters.rechecks.fetch_add(1, Ordering::Relaxed); }
        let clause = run(request)?;
        if control.cancelled() || !clause.matches(request) { return None; }
        let refutes = matches!(clause.bound, Bound::Exact | Bound::Upper) && clause.result.score < claim;
        if !refutes { return Some(proposal); }
        counters.refutations.fetch_add(1, Ordering::Relaxed);
        if review != 0 { return None; }
        let request = PalsRequest { context, first, reply, repair: true, alpha: -INF, beta: INF };
        counters.jobs.fetch_add(1, Ordering::Relaxed);
        counters.repairs.fetch_add(1, Ordering::Relaxed);
        let repair = run(request)?;
        if control.cancelled() || !repair.matches(request) || repair.bound != Bound::Exact
            || !(-INF+1..INF).contains(&repair.result.score) { return None; }
        proposal = repair.result;
    }
    unreachable!()
}

fn report(r: SearchResult) {
    if crate::DEV {
        let score = if r.score.abs() >= MATE - 128 { format!("mate {}", r.score.signum() * ((MATE - r.score.abs() + 1) / 2)) }
            else { format!("cp {}", r.score) };
        let pv = if r.best == Move::default() { String::new() } else {
            format!(" pv {}{}", r.best.uci(), r.reply.map_or_else(String::new, |m| format!(" {}", m.uci())))
        };
        println!("info depth {} score {} nodes {}{}", r.depth, score, r.nodes, pv);
    }
}

#[derive(Clone, Copy)]
enum Kind { Reset, Loose, Split }
struct Depth {
    kind: Kind, board: Board, moves: MoveList, depth: u8, guess: i32,
    frozen: [[i16; 2048]; 3], epoch: u64, workers: usize, groups: usize, first_job: usize,
    queue: AtomicUsize, alpha: AtomicU64,
    // The cache contains exact normal results for this board, depth and frozen
    // evaluation only. It never contains a restricted clause score.
    cache: Option<SearchResult>, best: Mutex<(SearchResult, usize)>,
    finished: AtomicUsize, control: Arc<Control>, counters: Arc<Counters>,
}
impl Depth {
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
                completed(s.search_move(&self.board, m, self.depth, alpha, INF))
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
impl Task for Depth {
    fn work(&self, searcher: &mut Searcher, worker: usize) -> Option<SearchResult> {
        if matches!(self.kind, Kind::Reset) { searcher.reset_learning(); return None; }
        searcher.use_frozen(&self.frozen, self.epoch);
        #[cfg(test)] let loose=matches!(self.kind,Kind::Loose);
        #[cfg(not(test))] let loose=if crate::VARIANT==b'F'||crate::PARALLEL==0{true}else if crate::PARALLEL==4{matches!(self.kind,Kind::Loose)}else{false};
        if loose {completed(searcher.iteration_frozen(&self.board,self.depth,self.guess))}
        else {self.work(searcher,worker*self.groups/self.workers,self.first_job+worker);None}
    }
}

#[inline(always)]
fn policy(mode: u8, previous: Option<SearchResult>, older: Option<SearchResult>,
          last_cost: Duration, control: &Control) -> u8 {
    if mode != 4 { return mode; }
    let (Some(a), Some(b)) = (previous, older) else { return if previous.is_none() { 1 } else { 2 }; };
    let unstable = a.best != b.best || (a.score - b.score).abs() >= 64;
    let tight = control.deadline().is_some_and(|d| d.saturating_duration_since(Instant::now()) <= last_cost.saturating_mul(2));
    // Expensive unstable iterations warrant a same-first Repair. Stable work
    // uses group locality; very little remaining time uses a whole-root race.
    if tight { 0 } else if unstable && last_cost >= Duration::from_micros(50) { 3 } else { 2 }
}

#[inline(always)]
fn group_count(variant: u8, mode: u8, workers: usize, tt_bits: usize) -> usize {
    if variant == b'F' || mode != 2 && mode != 4 { return 1; }
    // Table's smallest supported allocation is 2^8 slots. Tiny development
    // budgets use fewer groups rather than multiplying that allocation.
    workers.div_ceil(4).min(1usize << tt_bits.clamp(8, 26).saturating_sub(8))
}

pub struct Engine {
    leader: Searcher, helpers: Helpers<Depth>, tables: Vec<Arc<Table>>, control: Arc<Control>,
    workers: usize, mode: u8, effective: u8, groups: usize, counters: Arc<Counters>,
}
impl Engine {
    pub fn new(variant: u8, workers: usize, tt_bits: usize, control: Arc<Control>, mode: u8) -> io::Result<Self> {
        #[cfg(not(test))] let (variant,mode)={let _=(variant,mode);(crate::VARIANT,crate::PARALLEL)};
        assert!((1..=512).contains(&workers));
        assert!(mode <= 4);
        assert!((8..=26).contains(&tt_bits), "ROVE_TT_BITS must be 8..26");
        let effective = if variant == b'F' { 0 } else { mode };
        let groups = group_count(variant, effective, workers, tt_bits);
    // The exponent is a total TT allocation budget. Group-local tables divide
    // it rather than each silently allocating the entire requested memory.
        let group_shift = if groups == 1 { 0 } else { usize::BITS as usize - (groups - 1).leading_zeros() as usize };
        let tables: Vec<_> = (0..groups).map(|_| Arc::new(Table::new(tt_bits.saturating_sub(group_shift)))).collect();
        let leader = Searcher::new(tables[0].clone(), control.clone(), variant, 0);
        let searchers = (1..workers).map(|i| Searcher::new(tables[i * groups / workers].clone(), control.clone(), variant, i)).collect();
        let counters = Arc::new(Counters::default());
        let board = Board::start();
        let empty = SearchResult { score: -INF, best: Move::default(), reply: None, depth: 0, nodes: 0, completed: false };
        let helpers = Helpers::new(Depth { kind: Kind::Reset, board, moves: MoveList::new(), depth: 0, guess: 0,
            frozen: [[0; 2048]; 3], epoch: 0, workers, groups, first_job: 0,
            queue: AtomicUsize::new(0), alpha: AtomicU64::new(0), cache: None,
            best: Mutex::new((empty, 0)), finished: AtomicUsize::new(0), control: control.clone(), counters: counters.clone() }, searchers)?;
        Ok(Self { leader, helpers, tables, control, workers, mode, effective, groups, counters })
    }
    pub fn reset(&mut self) {
        self.helpers.wait();
        for table in &self.tables { table.clear(); }
        self.leader.reset_learning();
        self.helpers.prepare(|task| task.kind = Kind::Reset);
        self.helpers.begin();
        self.helpers.wait();
        self.counters.reset();
    }
    fn prepare_depth(&mut self, board: &Board, depth: u8) {
        self.leader.begin_depth();
        self.helpers.prepare(|task| {
            task.board.reuse_from(board); task.depth = depth;
            task.epoch = self.leader.freeze_to(&mut task.frozen);
        });
    }
    fn loose_depth(&mut self, board: &Board, depth: u8, guess: i32) -> Option<SearchResult> {
        self.prepare_depth(board, depth);
        self.helpers.prepare(|task| { task.kind = Kind::Loose; task.guess = guess; });
        self.helpers.begin();
        let leader = completed(self.leader.iteration_frozen(board, depth, guess));
        let helper = self.helpers.first_result();
        // Stable worker priority: never compare scores from different searches.
        leader.or(helper)
    }
    fn split_depth(&mut self, board: &Board, depth: u8, previous: Option<SearchResult>, pals: bool) -> Option<SearchResult> {
        #[cfg(not(test))] let pals=if crate::PARALLEL==4{pals}else{crate::PARALLEL==3};
        self.prepare_depth(board, depth);
        self.helpers.prepare(|task| {
            task.moves.clear(); task.moves.extend(board.legal());
            if let Some(old) = previous { if let Some(i) = task.moves.iter().position(|&m| m == old.best) { task.moves.swap(0, i); } }
        });
        let first = self.helpers.task(|task| task.moves.first().copied())?;
        self.counters.jobs.fetch_add(1, Ordering::Relaxed);
        let mut proposal = completed(self.leader.search_move(board, first, depth, -INF, INF))?;
        let mut cache = None;
        if pals && depth >= 2 {
            self.counters.proposals.fetch_add(1, Ordering::Relaxed);
            let replies = board.play(first).legal();
            let reply = replies.iter().copied().find(|m| Some(*m) != proposal.reply).or_else(|| replies.first().copied());
            if let Some(reply) = reply {
                let evaluation = self.helpers.task(|task| task.epoch);
                let context = PalsContext { root: board, depth, evaluation };
                proposal = review_pals(proposal, reply, context, &self.control, &self.counters, |request| {
                    let result = if request.repair {
                        self.leader.search_move_hint(board, request.first, Some(request.reply), depth, request.alpha, request.beta)
                    } else {
                        self.leader.search_clause(board, request.first, request.reply, depth, request.alpha, request.beta)
                    }?;
                    Some(PalsResult::from_search(request, result))
                })?;
            }
            // The queue may reuse the normal proposal or a feedback-accepted
            // unrestricted Repair, never a restricted diagnostic result.
            cache = Some(proposal);
        }
        self.helpers.prepare(|task| {
            task.kind = Kind::Split; task.cache = cache; task.first_job = usize::from(cache.is_none());
            task.queue.store(task.first_job + self.workers, Ordering::Relaxed);
            task.alpha.store(proposal.score as u32 as u64, Ordering::Relaxed);
            *task.best.get_mut().unwrap() = (proposal, 0);
            task.finished.store(1, Ordering::Relaxed);
        });
        self.helpers.begin();
        self.helpers.task(|task| task.work(&mut self.leader, 0, task.first_job));
        self.helpers.wait();
        self.helpers.task(|task| {
            if task.control.cancelled() || task.finished.load(Ordering::Relaxed) != task.moves.len() + usize::from(task.cache.is_some()) { return None; }
            let mut result = task.best.lock().unwrap().0;
            result.nodes = self.control.nodes.load(Ordering::Relaxed);
            Some(result)
        })
    }
    pub fn execute(&mut self, board: &Board, limits: &Limits) -> Option<SearchResult> {
        self.counters.reset();
    if board.legal().is_empty() || board.halfmove >= 100 || board.repeated() || board.insufficient() {
        let result = completed(self.leader.iteration(board, 1, 0));
        if let Some(r) = result { report(r); }
        return result;
    }
    let (mut best, mut older, mut last_cost, mut last_policy) = (None, None, Duration::ZERO, 255);
    let mut parity_guess=[0;2];
    for depth in 1..=limits.depth.max(1) {
        if self.control.cancelled() { break; }
        #[cfg(test)] let selected=policy(self.effective,best,older,last_cost,&self.control);
        #[cfg(not(test))] let selected=if crate::VARIANT==b'F'{0}else{policy(crate::PARALLEL,best,older,last_cost,&self.control)};
        if last_policy != 255 && selected != last_policy { self.counters.switches.fetch_add(1, Ordering::Relaxed); }
        self.counters.policies.fetch_or(1 << selected, Ordering::Relaxed);
        last_policy = selected;
        let start = Instant::now();
        let previous=best.map_or(0,|r:SearchResult|r.score);
        let guess=if crate::VARIANT==b'F'&&crate::number(option_env!("ROVE_F_PARITY"),0)==1&&depth>2 {parity_guess[(depth&1)as usize]}else{previous};
        if crate::DEV&&crate::VARIANT==b'F'{println!("info string f seed depth {depth} guess {guess}");}
        let r = if selected == 0 { self.loose_depth(board, depth, guess) }
            else { self.split_depth(board, depth, best, selected == 3) };
        last_cost = start.elapsed();
        let Some(r) = r else { break; };
        parity_guess[(depth&1)as usize]=r.score;
        older = best;
        best = Some(r);
        report(r);
    }
        let counters = &self.counters;
    if crate::DEV { println!("info string parallel mode {} effective {} workers {} groups {} root_jobs {} cache_hits {} proposals {} clauses {} repairs {} policy_switches {} policies {} cross_group_alpha {} refutations {} rechecks {}",
        self.mode, self.effective, self.workers, self.groups,
        counters.jobs.load(Ordering::Relaxed), counters.cached.load(Ordering::Relaxed),
        counters.proposals.load(Ordering::Relaxed), counters.clauses.load(Ordering::Relaxed),
        counters.repairs.load(Ordering::Relaxed), counters.switches.load(Ordering::Relaxed),
        counters.policies.load(Ordering::Relaxed), counters.cross_group_alpha.load(Ordering::Relaxed),
        counters.refutations.load(Ordering::Relaxed), counters.rechecks.load(Ordering::Relaxed)); }
        best
    }
}

#[cfg(test)]
#[path = "../tests/rust/parallel.rs"]
mod tests;
