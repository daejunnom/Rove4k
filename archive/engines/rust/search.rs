//! Independent Rust search. Completed bounds are published only after an entire
//! node returns; cancellation and excluded searches never publish normal bounds.
use crate::board::{Board, Move, MoveList};
use crate::eval;
use std::sync::{Arc, atomic::{AtomicBool, AtomicU64, Ordering, fence}};
use std::time::{Duration, Instant};
#[cfg(rove_f_single)]
use std::{cell::UnsafeCell, sync::atomic::AtomicU8};

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
    #[cfg(test)] deepest:AtomicU64,
}

#[cfg(test)]
#[path = "../tests/rust/search.rs"]
mod tests;
#[cfg(test)]
#[path = "../tests/rust/f_tt.rs"]
mod f_tt_tests;
impl Control {
    pub fn new(limits: &Limits) -> Self {
        let result = Self { stop: AtomicBool::new(false), nodes: AtomicU64::new(0), origin: Instant::now(), deadline_ns: AtomicU64::new(0), node_limit: AtomicU64::new(0), conflicts: AtomicU64::new(0), probes:AtomicU64::new(0), singular:AtomicU64::new(0), see_calls:AtomicU64::new(0), tt_hits:AtomicU64::new(0), #[cfg(test)] trace:std::sync::Mutex::new(Vec::new()),#[cfg(test)] deepest:AtomicU64::new(0) };
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
        #[cfg(test)] self.deepest.store(0,Ordering::Relaxed);
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
#[cfg(not(rove_f_single))]
struct Slot { sequence: AtomicU64, key: AtomicU64, data: AtomicU64 }
#[cfg(rove_f_single)]
#[repr(C)]
struct Slot { key: UnsafeCell<u64>, data: UnsafeCell<[u8;7]>, lock: AtomicU8 }
// Every access to either UnsafeCell is inside the same exclusive byte lock.
// Readers never inspect payload before acquiring it, so lock reuse has no ABA
// or sequence-wrap condition. Contention is a miss or a skipped replacement.
#[cfg(rove_f_single)]
unsafe impl Sync for Slot {}
#[cfg(rove_f_single)]
const _: () = assert!(std::mem::size_of::<Slot>() == 16);
pub struct Table { slots: Vec<Slot>, mask: usize }
fn encode_move(m: Move) -> u64 { m.from as u64 | ((m.to as u64) << 7) | ((m.promo.unsigned_abs() as u64) << 14) }
fn decode_move(m: u64) -> Move { Move { from: (m & 127) as u8, to: ((m >> 7) & 127) as u8, promo: ((m >> 14) & 7) as i8 } }
fn store_score(v: i32, ply: usize) -> i32 { if v > MATE - 128 { v + ply as i32 } else if v < -MATE + 128 { v - ply as i32 } else { v } }
fn load_score(v: i32, ply: usize) -> i32 { if v > MATE - 128 { v - ply as i32 } else if v < -MATE + 128 { v + ply as i32 } else { v } }
#[cfg(not(rove_f_single))]
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

#[cfg(rove_f_single)]
impl Slot {
    fn acquire(&self)->bool { self.lock.compare_exchange(0,1,Ordering::Acquire,Ordering::Relaxed).is_ok() }
    fn release(&self) { self.lock.store(0,Ordering::Release); }
}
#[cfg(rove_f_single)]
impl Table {
    pub fn new(bits:usize)->Self {
        assert!((8..=26).contains(&bits),"TT allocation exponent must be 8..26");
        let size=1usize<<bits;
        Self{slots:(0..size).map(|_|Slot{key:UnsafeCell::new(0),data:UnsafeCell::new([0;7]),lock:AtomicU8::new(0)}).collect(),mask:size-1}
    }
    pub fn clear(&self) {
        for s in &self.slots {if s.acquire(){unsafe{*s.data.get()=[0;7];}s.release();}}
    }
    fn get(&self,key:u64,ply:usize)->Option<Entry> {
        let s=&self.slots[key as usize&self.mask];if !s.acquire(){return None;}
        let (k,bytes)=unsafe{(*s.key.get(),*s.data.get())};s.release();
        let mut d=0u64;for(i,b)in bytes.into_iter().enumerate(){d|=(b as u64)<<(i*8);}
        if k!=key||d&(1<<42)==0{return None;}
        let bound=(d>>40)&3;let score=load_score(((d>>24)as u16 as i16)as i32,ply);
        Some(Entry{key:k,mv:decode_move(d),depth:((d>>17)&127)as u8,
            lower:if bound==1||bound==2{score}else{-INF},upper:if bound==1||bound==3{score}else{INF}})
    }
    fn put(&self,e:Entry,ply:usize,control:&Control)->bool {
        if e.lower>e.upper{control.conflicts.fetch_add(1,Ordering::Relaxed);return false;}
        let (bound,score)=if e.lower==e.upper{(1,e.lower)}else if e.lower>-INF{(2,e.lower)}else if e.upper<INF{(3,e.upper)}else{(0,0)};
        let d=(1u64<<42)|encode_move(e.mv)|((e.depth as u64)<<17)|((store_score(score,ply)as i16 as u16 as u64)<<24)|(bound<<40);
        let s=&self.slots[e.key as usize&self.mask];if !s.acquire(){return true;}
        unsafe{*s.key.get()=e.key;for(i,b)in(&mut*s.data.get()).iter_mut().enumerate(){*b=(d>>(i*8))as u8;}}
        s.release();true
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
    #[cfg(test)] pub repair_first: Option<Move>,
}
impl Searcher {
    pub fn new(table: Arc<Table>, control: Arc<Control>, variant: u8, worker: usize) -> Self {
        let _=variant;
        Self { table, control, #[cfg(test)] variant, worker, history: vec![0;32768], continuation: vec![0;4096], capture_history: vec![0;7*7*128],
            correction: std::array::from_fn(|_| vec![0;2048]), frozen: std::array::from_fn(|_| vec![0;2048]), epoch: 0,
            pv: (0..=PLY_LIMIT).map(|_| Vec::with_capacity(PLY_LIMIT)).collect(), reply_hint: None, hint_ply: 1, root_choice: Move::default(),
            #[cfg(test)] repair_first: None }
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
        if self.reply_hint == Some(m) && ply == self.hint_ply { return 21_000_000; }
        if m == tt { return 20_000_000; }
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
        #[cfg(test)] self.control.deepest.fetch_max(ply as u64,Ordering::Relaxed);
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
        #[cfg(test)] self.control.deepest.fetch_max(ply as u64,Ordering::Relaxed);
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
        // Repair must investigate its challenger rather than return the normal
        // proposal's cached bound. Its descendants retain ordinary TT reuse.
        let repair = self.reply_hint.is_some() && ply == self.hint_ply;
        if let Some(e) = entry { if !repair && (e.depth >= depth && (self.variant() != b'F' || e.depth == depth)) && moves.contains(&e.mv) {
            let score = if e.lower == e.upper { Some(e.lower) } else if e.lower >= beta { Some(e.lower) } else if e.upper <= alpha {Some(e.upper)} else {None};
            if let Some(score) = score { self.control.tt_hits.fetch_add(1,Ordering::Relaxed); self.pv[ply].push(e.mv); if ply == 0 {self.root_choice=e.mv;} return Ok(score); }
        }}
        let static_eval = self.evaluation(b);
        moves.sort_unstable_by_key(|&m| std::cmp::Reverse(self.order(b,m,tt_move,previous,ply)));
        if self.control.cancelled(){return Err(());}
        let mut best = -INF;
        let mut best_move = Move::default();
        let mut searched = 0usize;
        let mut quiets = MoveList::new();
        for m in moves {
            if excluded == Some(m) { continue; }
            #[cfg(test)] { if repair && searched == 0 { self.repair_first = Some(m); } }
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
        #[cfg(test)] { self.repair_first = None; }
        self.reply_hint=hint;
        self.hint_ply=1;
        let score=if Self::draw(b) {
            self.pv[1].clear();
            self.tick().map(|()|0)
        } else {self.negamax(&b.play(m),depth.saturating_sub(1),-beta,-alpha,1,m,None,false).map(|v|-v)};
        self.reply_hint=None;
        Some(SearchResult {score:score.ok()?,best:m,reply:self.pv[1].first().copied(),depth,nodes:self.control.nodes.load(Ordering::Relaxed),completed:true})
    }
    pub fn search_clause(&mut self,b:&Board,first:Move,reply:Move,depth:u8,alpha:i32,beta:i32)->Option<SearchResult> {
        if !b.legal().contains(&first) {return None;}
        let child=b.play(first);
        if !child.legal().contains(&reply) {return None;}
        // This is a constrained diagnostic. No bound for the unrestricted first
        // move is stored, nor may this score be accepted as its complete result.
        // A game already drawn at the root or after first cannot be resumed by
        // a forced pawn move/capture resetting its clock or repetition suffix.
        // Requested moves are still checked and echoed, including on draws.
        let score=if Self::draw(b)||Self::draw(&child) {self.tick().ok()?;0}
            else {self.negamax(&child.play(reply),depth.saturating_sub(2),alpha,beta,2,reply,None,true).ok()?};
        Some(SearchResult {score,best:first,reply:Some(reply),depth,nodes:self.control.nodes.load(Ordering::Relaxed),completed:true})
    }
}
