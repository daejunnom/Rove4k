//! Independent Rust search. Completed bounds are published only after an entire
//! node returns; cancellation and excluded searches never publish normal bounds.
use crate::board::{Board, Move};
use crate::eval;
use std::sync::{Arc, atomic::{AtomicBool, AtomicU64, Ordering, fence}};
use std::time::{Duration, Instant};

pub const INF: i32 = 31000;
pub const MATE: i32 = 30000;
const PLY_LIMIT: usize = 96;

#[derive(Clone)]
pub struct Limits { pub depth: u8, pub nodes: u64, pub movetime: Option<Duration> }
pub struct Control {
    pub stop: AtomicBool,
    pub nodes: AtomicU64,
    origin: Instant,
    deadline_ns: AtomicU64,
    pub node_limit: AtomicU64,
    pub conflicts: AtomicU64,
    pub probes: AtomicU64,
    pub singular: AtomicU64,
    pub see_calls: AtomicU64,
    pub tt_hits: AtomicU64,
    #[cfg(test)] trace: std::sync::Mutex<Vec<(u8,i32,i32,i32)>>,
}

#[cfg(test)]
mod tests {
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
}
impl Control {
    pub fn new(limits: &Limits) -> Self {
        let result = Self { stop: AtomicBool::new(false), nodes: AtomicU64::new(0), origin: Instant::now(), deadline_ns: AtomicU64::new(0), node_limit: AtomicU64::new(0), conflicts: AtomicU64::new(0), probes:AtomicU64::new(0), singular:AtomicU64::new(0), see_calls:AtomicU64::new(0), tt_hits:AtomicU64::new(0), #[cfg(test)] trace:std::sync::Mutex::new(Vec::new()) };
        result.reset(limits);
        result
    }
    /// The caller has physically stopped every worker before resetting a search.
    /// One allocation and monotonic clock origin serve the whole process lifetime.
    pub fn reset(&self, limits: &Limits) {
        self.stop.store(false, Ordering::Relaxed);
        self.nodes.store(0, Ordering::Relaxed);
        self.node_limit.store(limits.nodes, Ordering::Relaxed);
        let deadline = limits.movetime.map_or(0, |d| (self.origin.elapsed().saturating_add(d).as_nanos().min(u64::MAX as u128) as u64).max(1));
        self.deadline_ns.store(deadline, Ordering::Relaxed);
        for value in [&self.conflicts, &self.probes, &self.singular, &self.see_calls, &self.tt_hits] { value.store(0, Ordering::Relaxed); }
        #[cfg(test)] self.trace.lock().unwrap().clear();
    }
    pub fn deadline(&self) -> Option<Instant> {
        let ns = self.deadline_ns.load(Ordering::Relaxed);
        if ns == 0 { None } else { self.origin.checked_add(Duration::from_nanos(ns)) }
    }
    pub fn cancelled(&self) -> bool {
        if self.stop.load(Ordering::Relaxed) { return true; }
        let limit = self.node_limit.load(Ordering::Relaxed);
        let cancelled = (limit != 0 && self.nodes.load(Ordering::Relaxed) >= limit)
            || self.deadline().is_some_and(|d| Instant::now() >= d);
        if cancelled { self.stop.store(true, Ordering::Relaxed); }
        cancelled
    }
}

#[derive(Clone, Copy, Debug)]
pub struct SearchResult {
    pub score: i32, pub best: Move, pub reply: Option<Move>, pub depth: u8,
    pub nodes: u64, pub completed: bool,
}
#[derive(Clone, Copy)]
struct Entry { key: u64, mv: Move, depth: u8, lower: i32, upper: i32 }
struct Slot { sequence: AtomicU64, key: AtomicU64, data: AtomicU64 }
pub struct Table { slots: Vec<Slot>, mask: usize }
fn encode_move(m: Move) -> u64 { m.from as u64 | ((m.to as u64) << 7) | ((m.promo.unsigned_abs() as u64) << 14) }
fn decode_move(m: u64) -> Move { Move { from: (m & 127) as u8, to: ((m >> 7) & 127) as u8, promo: ((m >> 14) & 7) as i8 } }
fn store_score(v: i32, ply: usize) -> i32 { if v > MATE - 128 { v + ply as i32 } else if v < -MATE + 128 { v - ply as i32 } else { v } }
fn load_score(v: i32, ply: usize) -> i32 { if v > MATE - 128 { v - ply as i32 } else if v < -MATE + 128 { v + ply as i32 } else { v } }
impl Table {
    pub fn new(bits: usize) -> Self {
        assert!((8..=26).contains(&bits), "TT allocation exponent must be 8..26");
        let size = 1usize << bits;
        Self { slots: (0..size).map(|_| Slot { sequence: AtomicU64::new(0), key: AtomicU64::new(0), data: AtomicU64::new(0) }).collect(), mask: size - 1 }
    }
    pub fn clear(&self) {
        // Session reset is called after physical worker completion. The same
        // sequence protocol also keeps an accidental concurrent reader safe.
        for s in &self.slots {
            let seq=s.sequence.load(Ordering::Relaxed);
            if seq&1==0&&s.sequence.compare_exchange(seq,seq.wrapping_add(1),Ordering::Acquire,Ordering::Relaxed).is_ok(){s.data.store(0,Ordering::Relaxed);s.sequence.store(seq.wrapping_add(2),Ordering::Release);}
        }
    }
    fn get(&self, key: u64, ply: usize) -> Option<Entry> {
        let s = &self.slots[key as usize & self.mask];
        let a = s.sequence.load(Ordering::Acquire);
        if a & 1 != 0 { return None; }
        let k = s.key.load(Ordering::Relaxed);
        let d = s.data.load(Ordering::Relaxed);
        fence(Ordering::Acquire);
        if s.sequence.load(Ordering::Relaxed) != a || d >> 63 == 0 || k != key { return None; }
        Some(Entry { key: k, mv: decode_move(d), depth: ((d >> 17) & 127) as u8,
            lower: load_score(((d >> 24) as u16 as i16) as i32, ply), upper: load_score(((d >> 40) as u16 as i16) as i32, ply) })
    }
    fn put(&self, mut e: Entry, ply: usize, control: &Control) -> bool {
        let s = &self.slots[e.key as usize & self.mask];
        let seq = s.sequence.load(Ordering::Relaxed);
        if seq & 1 != 0 || s.sequence.compare_exchange(seq, seq.wrapping_add(1), Ordering::Acquire, Ordering::Relaxed).is_err() { return true; }
        let old = s.data.load(Ordering::Relaxed);
        if old >> 63 != 0 && s.key.load(Ordering::Relaxed) == e.key && ((old >> 17) & 127) as u8 == e.depth {
            let old_lower=load_score(((old >> 24) as u16 as i16) as i32, ply);
            // The move witnesses the lower bound. An upper-only probe cannot
            // replace that witness when its bound closes an existing interval.
            if old_lower>=e.lower && old_lower>-INF {e.mv=decode_move(old);}
            e.lower = e.lower.max(old_lower);
            e.upper = e.upper.min(load_score(((old >> 40) as u16 as i16) as i32, ply));
        }
        let consistent = e.lower <= e.upper;
        if consistent {
            let data = (1u64 << 63) | encode_move(e.mv) | ((e.depth as u64) << 17)
                | ((store_score(e.lower, ply) as i16 as u16 as u64) << 24)
                | ((store_score(e.upper, ply) as i16 as u16 as u64) << 40);
            s.key.store(e.key, Ordering::Relaxed);
            s.data.store(data, Ordering::Relaxed);
        } else { control.conflicts.fetch_add(1, Ordering::Relaxed); }
        s.sequence.store(seq.wrapping_add(2), Ordering::Release);
        consistent
    }
}

fn mix(mut x: u64) -> u64 { x ^= x >> 30; x = x.wrapping_mul(0xbf58476d1ce4e5b9); x ^= x >> 27; x = x.wrapping_mul(0x94d049bb133111eb); x ^ (x >> 31) }
fn move_index(m: Move) -> usize { m.from as usize * 128 + m.to as usize }
fn history_update(value: &mut i16, bonus: i32) { let v = *value as i32; *value = (v + bonus - v * bonus.abs() / 16384).clamp(-16384, 16384) as i16; }

pub struct Searcher {
    table: Arc<Table>, control: Arc<Control>, #[cfg(test)] variant: u8, worker: usize,
    history: Vec<i16>, continuation: Vec<i16>, capture_history: Vec<i16>,
    correction: [Vec<i16>; 3], frozen: [Vec<i16>; 3], epoch: u64,
    pv: Vec<Vec<Move>>, reply_hint: Option<Move>, hint_ply: usize,
    pub root_choice: Move,
}
impl Searcher {
    pub fn new(table: Arc<Table>, control: Arc<Control>, variant: u8, worker: usize) -> Self {
        let _=variant;
        Self { table, control, #[cfg(test)] variant, worker, history: vec![0;32768], continuation: vec![0;4096], capture_history: vec![0;7*7*128],
            correction: std::array::from_fn(|_| vec![0;2048]), frozen: std::array::from_fn(|_| vec![0;2048]), epoch: 0,
            pv: (0..=PLY_LIMIT).map(|_| Vec::with_capacity(PLY_LIMIT)).collect(), reply_hint: None, hint_ply: 1, root_choice: Move::default() }
    }
    #[inline(always)]
    fn variant(&self)->u8{
        #[cfg(test)] {self.variant}
        #[cfg(not(test))] {crate::VARIANT}
    }
    pub fn reset_learning(&mut self){
        self.history.fill(0);self.continuation.fill(0);self.capture_history.fill(0);
        for c in &mut self.correction{c.fill(0);}for c in &mut self.frozen{c.fill(0);}
        for line in &mut self.pv{line.clear();}self.epoch=0;self.reply_hint=None;self.root_choice=Move::default();
    }
    fn set_pv(&mut self,ply:usize,m:Move){let(parent,child)=self.pv.split_at_mut(ply+1);let line=&mut parent[ply];line.clear();line.push(m);line.extend_from_slice(&child[0]);}
    pub fn eval_epoch(&self) -> u64 { self.epoch }
    pub fn share_evaluation(&mut self, source:&Self) { self.frozen.clone_from(&source.frozen);self.epoch=source.epoch; }
    pub fn freeze_to(&self,output:&mut [[i16;2048];3])->u64{for(i,c)in output.iter_mut().enumerate(){c.copy_from_slice(&self.frozen[i]);}self.epoch}
    pub fn use_frozen(&mut self,input:&[[i16;2048];3],epoch:u64){for(i,c)in input.iter().enumerate(){self.frozen[i].copy_from_slice(c);}self.epoch=epoch;}
    pub fn begin_depth(&mut self) {
        if self.variant() == b'F' { self.epoch = 0; return; }
        self.frozen.clone_from(&self.correction);
        self.epoch = self.frozen.iter().flatten().fold(0, |h, &v| mix(h ^ v as u16 as u64));
    }
    fn correction_indices(b: &Board) -> [usize;3] {
        let mut keys = [0u64;3];
        for sq in 0..128 { if sq & 0x88 == 0 {
            let p = b.cells[sq]; if p == 0 { continue; }
            let v = mix(sq as u64 ^ ((p as i64 as u64).wrapping_mul(197)));
            keys[if p.unsigned_abs() == 1 {0} else {2}] ^= v;
            keys[1] = keys[1].wrapping_add(mix(p as i64 as u64));
        }}
        keys.map(|k| k as usize & 2047)
    }
    fn evaluation(&self, b: &Board) -> i32 {
        let correction = if self.variant() == b'F' { 0 } else { Self::correction_indices(b).iter().enumerate().map(|(i,&k)| self.frozen[i][k] as i32).sum::<i32>() / 128 };
        (eval::evaluate(b, self.variant()) + correction).clamp(-MATE + 256, MATE - 256)
    }
    fn key(&self, b: &Board) -> u64 {
        // Draw history is part of the search context. Position-only keys are not
        // sufficient for exact bound reuse near repetition or the fifty-move rule.
        let mut key = mix(b.hash ^ self.epoch ^ ((b.halfmove as u64) << 48));
        let n = (b.halfmove as usize + 1).min(b.hist.len());
        for &h in &b.hist[b.hist.len()-n..] { key = mix(key ^ h); }
        key
    }
    fn tick(&self) -> Result<(), ()> {
        if self.control.cancelled() { return Err(()); }
        let limit = self.control.node_limit.load(Ordering::Relaxed);
        if limit==0 {self.control.nodes.fetch_add(1, Ordering::Relaxed);}
        else if self.control.nodes.fetch_update(Ordering::Relaxed,Ordering::Relaxed,|n|if n<limit{Some(n+1)}else{None}).is_err(){self.control.stop.store(true,Ordering::Relaxed);return Err(());}
        Ok(())
    }
    fn draw(b: &Board) -> bool { b.halfmove >= 100 || b.repeated() || b.insufficient() }
    fn order(&self, b: &Board, m: Move, tt: Move, previous: Move, ply: usize) -> i32 {
        if m == tt { return 20_000_000; }
        if self.reply_hint == Some(m) && ply == self.hint_ply { return 19_000_000; }
        let capture = b.is_capture(m);
        let mut v = if capture {
            let victim = b.captured(m).unsigned_abs() as usize;
            let piece = b.cells[m.from as usize].unsigned_abs() as usize;
            // On cancellation this key is immaterial: both sorting callers
            // propagate Err before searching a move or publishing any bound.
            let see = if self.variant() == b'B' { self.control.see_calls.fetch_add(1,Ordering::Relaxed); b.see_with_abort(m,&||self.control.cancelled()).unwrap_or(0) } else { [0,100,320,330,500,900,20000][victim] - piece as i32 };
            1_000_000 + see * 64 + self.capture_history[(piece*7+victim)*128+m.to as usize] as i32
        } else {
            self.history[(b.side < 0) as usize*16384+move_index(m)] as i32
                + self.continuation[(move_index(previous).wrapping_mul(13)^move_index(m)) & 4095] as i32
        };
        if m.promo != 0 { v += 800_000 + m.promo as i32 * 100; }
        if self.variant() == b'E'||self.variant()==b'C'&&eval::CROSS_MODEL { v += eval::order(b,m); }
        // Search diversity changes equal-score ordering only.
        v * 8 + ((mix(encode_move(m) ^ self.worker as u64) & 7) as i32)
    }
    fn qsearch(&mut self, b: &Board, mut alpha: i32, beta: i32, ply: usize, previous: Move, isolated: bool) -> Result<i32, ()> {
        self.tick()?;
        if ply >= PLY_LIMIT { return Err(()); }
        self.pv[ply].clear();
        let check = b.in_check();
        let mut moves = b.legal();
        // Terminal game rules precede draw counters (checkmate on move 100 wins).
        if moves.is_empty() { return Ok(if check { -MATE + ply as i32 } else { 0 }); }
        if Self::draw(b) { return Ok(0); }
        let mut best = -INF;
        if !check {
            best = self.evaluation(b);
            if best >= beta { return Ok(best); }
            alpha = alpha.max(best);
            moves.retain(|&m| b.is_capture(m) || m.promo != 0);
        }
        moves.sort_unstable_by_key(|&m| std::cmp::Reverse(self.order(b,m,Move::default(),previous,ply)));
        if self.control.cancelled(){return Err(());}
        for m in moves {
            // Legal evasions are never filtered by SEE.
            if !check && self.variant() == b'B' && m.promo == 0 && b.see_with_abort(m,&||self.control.cancelled()).ok_or(())? < 0 { continue; }
            let score = -self.qsearch(&b.play(m),-beta,-alpha,ply+1,m,isolated)?;
            if score > best { best = score; self.set_pv(ply,m); }
            alpha = alpha.max(score);
            if alpha >= beta { break; }
        }
        Ok(best)
    }
    fn negamax(&mut self, b: &Board, depth: u8, mut alpha: i32, mut beta: i32, ply: usize, previous: Move, excluded: Option<Move>, isolated: bool) -> Result<i32, ()> {
        if depth == 0 { return self.qsearch(b,alpha,beta,ply,previous,isolated); }
        self.tick()?;
        if ply >= PLY_LIMIT { return Err(()); }
        self.pv[ply].clear();
        let check = b.in_check();
        let mut moves = b.legal();
        if moves.is_empty() { return Ok(if check {-MATE + ply as i32} else {0}); }
        if Self::draw(b) { return Ok(0); }
        if ply > 0 { alpha = alpha.max(-MATE + ply as i32); beta = beta.min(MATE - ply as i32 - 1); if alpha >= beta {return Ok(alpha);} }
        let original_alpha = alpha;
        let key = self.key(b);
        let entry = if isolated { None } else { self.table.get(key,ply) };
        let tt_move = entry.map_or(Move::default(),|e| e.mv);
        if let Some(e) = entry { if (e.depth >= depth && (self.variant() != b'F' || e.depth == depth)) && moves.contains(&e.mv) {
            let score = if e.lower == e.upper { Some(e.lower) } else if e.lower >= beta { Some(e.lower) } else if e.upper <= alpha {Some(e.upper)} else {None};
            if let Some(score) = score { self.control.tt_hits.fetch_add(1,Ordering::Relaxed); self.pv[ply].push(e.mv); if ply == 0 {self.root_choice=e.mv;} return Ok(score); }
        }}
        let static_eval = self.evaluation(b);
        moves.sort_unstable_by_key(|&m| std::cmp::Reverse(self.order(b,m,tt_move,previous,ply)));
        if self.control.cancelled(){return Err(());}
        let mut best = -INF;
        let mut best_move = Move::default();
        let mut searched = 0usize;
        let mut quiets = Vec::new();
        for m in moves {
            if excluded == Some(m) { continue; }
            let quiet = !b.is_capture(m) && m.promo == 0;
            let mut extension = 0;
            if self.variant() == b'B' && !isolated && excluded.is_none() && depth >= 6 && m == tt_move {
                if let Some(e) = entry { if e.depth >= depth.saturating_sub(3) && e.lower > -MATE+128 && e.lower < MATE-128 && e.lower > -INF {
                    let threshold = e.lower - 2*depth as i32;
                    self.control.singular.fetch_add(1,Ordering::Relaxed);
                    // The excluded search retains the same state and ply. Its
                    // complete subtree is isolated from normal TT and histories.
                    let alternative = self.negamax(b,depth/2,threshold-1,threshold,ply,previous,Some(m),true)?;
                    self.pv[ply].clear();
                    if alternative < threshold { extension = 1; }
                }}
            }
            let child = b.play(m);
            let full_depth = depth.saturating_sub(1).saturating_add(extension);
            let mut score;
            if searched == 0 {
                score = -self.negamax(&child,full_depth,-beta,-alpha,ply+1,m,None,isolated)?;
            } else {
                // MTD(f) uses full-depth alpha-beta at every probe. Ordering may
                // evolve, while the searched value and evaluation stay fixed.
                let reduction = if self.variant() != b'F' && !check && quiet && depth >= 3 && searched >= 4 && !child.in_check() { 1 + (depth >= 8 && searched >= 12) as u8 } else {0};
                score = -self.negamax(&child,full_depth.saturating_sub(reduction),-alpha-1,-alpha,ply+1,m,None,isolated)?;
                if reduction > 0 && score > alpha { score = -self.negamax(&child,full_depth,-alpha-1,-alpha,ply+1,m,None,isolated)?; }
                if score > alpha && score < beta { score = -self.negamax(&child,full_depth,-beta,-alpha,ply+1,m,None,isolated)?; }
            }
            searched += 1;
            if score > best { best=score; best_move=m; self.set_pv(ply,m); if ply==0 {self.root_choice=m;} }
            alpha=alpha.max(score);
            if alpha >= beta {
                if !isolated {
                    let bonus=(depth as i32*depth as i32*32).min(2048);
                    if quiet {
                        history_update(&mut self.history[(b.side<0) as usize*16384+move_index(m)],bonus);
                        history_update(&mut self.continuation[(move_index(previous).wrapping_mul(13)^move_index(m))&4095],bonus);
                        for q in quiets { history_update(&mut self.history[(b.side<0) as usize*16384+move_index(q)],-bonus/2); }
                    } else {
                        let p=b.cells[m.from as usize].unsigned_abs() as usize;
                        let v=b.captured(m).unsigned_abs() as usize;
                        history_update(&mut self.capture_history[(p*7+v)*128+m.to as usize],bonus);
                    }
                }
                break;
            }
            if quiet {quiets.push(m);}
        }
        if searched == 0 { return Ok(-INF); }
        if !isolated {
            let lower=if best>original_alpha {best} else {-INF};
            let upper=if best<beta {best} else {INF};
            if !self.table.put(Entry {key,mv:best_move,depth,lower,upper},ply,&self.control) && self.variant()==b'F' {self.control.stop.store(true,Ordering::Relaxed);return Err(());}
            if self.variant()!=b'F' && !check && depth>=2 && !b.is_capture(best_move) && best_move.promo==0 && best.abs()<MATE-128
                && ((best>original_alpha && best<beta) || (best>=beta && best>static_eval) || (best<=original_alpha && best<static_eval)) {
                let target=((best-static_eval)*32).clamp(-2048,2048);
                for (i,k) in Self::correction_indices(b).into_iter().enumerate() {history_update(&mut self.correction[i][k],target*depth as i32/8);}
            }
        }
        Ok(best)
    }
    pub fn iteration(&mut self, b: &Board, depth: u8, guess: i32) -> Option<SearchResult> {
        self.begin_depth();
        self.iteration_frozen(b,depth,guess)
    }
    /// One immutable evaluation meaning is shared by all workers for a depth.
    pub fn iteration_frozen(&mut self,b:&Board,depth:u8,guess:i32)->Option<SearchResult>{
        self.root_choice=Move::default();self.reply_hint=None;
        let mut lower_witness=None;
        let score = if self.variant() == b'F' {
            let(mut lower,mut upper,mut value)=(-INF,INF,guess.clamp(-INF+1,INF-1));
            while lower<upper {
                self.control.probes.fetch_add(1,Ordering::Relaxed);
                let beta=if value==lower {value+1} else {value};
                value=self.negamax(b,depth,beta-1,beta,0,Move::default(),None,false).ok()?;
                if value<beta {upper=value;} else {lower=value;lower_witness=self.pv[0].first().copied().or(lower_witness);}
                #[cfg(test)] self.control.trace.lock().unwrap().push((depth,lower,upper,self.epoch as i32));
                if lower>upper {self.control.conflicts.fetch_add(1,Ordering::Relaxed);self.control.stop.store(true,Ordering::Relaxed);return None;}
            }
            value
        } else {self.negamax(b,depth,-INF,INF,0,Move::default(),None,false).ok()?};
        let last_move=self.pv[0].first().copied().unwrap_or(self.root_choice);
        let best=if self.variant()==b'F'{lower_witness.unwrap_or(last_move)}else{last_move};
        Some(SearchResult {score,best,reply:if best==last_move{self.pv[0].get(1).copied()}else{None},depth,nodes:self.control.nodes.load(Ordering::Relaxed),completed:true})
    }
    pub fn search_move(&mut self,b:&Board,m:Move,depth:u8,alpha:i32,beta:i32)->Option<SearchResult> {
        self.search_move_hint(b,m,None,depth,alpha,beta)
    }
    pub fn search_move_hint(&mut self,b:&Board,m:Move,hint:Option<Move>,depth:u8,alpha:i32,beta:i32)->Option<SearchResult> {
        if !b.legal().contains(&m) {return None;}
        self.reply_hint=hint;
        self.hint_ply=1;
        let score=self.negamax(&b.play(m),depth.saturating_sub(1),-beta,-alpha,1,m,None,false).map(|v|-v);
        self.reply_hint=None;
        Some(SearchResult {score:score.ok()?,best:m,reply:self.pv[1].first().copied(),depth,nodes:self.control.nodes.load(Ordering::Relaxed),completed:true})
    }
    pub fn search_clause(&mut self,b:&Board,first:Move,reply:Move,depth:u8,alpha:i32,beta:i32)->Option<SearchResult> {
        if !b.legal().contains(&first) {return None;}
        let child=b.play(first);
        if !child.legal().contains(&reply) {return None;}
        // This is a constrained diagnostic. No bound for the unrestricted first
        // move is stored, nor may this score be accepted as its complete result.
        let score=self.negamax(&child.play(reply),depth.saturating_sub(2),alpha,beta,2,reply,None,true).ok()?;
        Some(SearchResult {score,best:first,reply:Some(reply),depth,nodes:self.control.nodes.load(Ordering::Relaxed),completed:true})
    }
}
