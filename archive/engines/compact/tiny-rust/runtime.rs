//! Fixed startup workers; a GO owns its position until every worker drains.
use crate::{board::{self, Board}, search::{Control, Limits, Result, Table, Worker}};
use std::{io::{self, Write}, sync::{Arc, Condvar, Mutex, RwLock, atomic::Ordering}, thread};
#[cfg(tiny_dev)]use std::thread::JoinHandle;

fn empty() -> Result { Result {best:0, #[cfg(tiny_dev)]score:0, depth:0, #[cfg(tiny_dev)]nodes:0} }
struct Job {
    board:Board, keys:[u64;4096], length:usize, frozen:[i16;1024], epoch:u64, limits:Limits,
}
struct State {
    epoch:u64, ready:usize, pending:usize, #[cfg(tiny_dev)]quit:bool, #[cfg(tiny_dev)]reset:bool,
    results:Vec<Result>, learned:[i16;1024], fallback:u32, #[cfg(tiny_dev)]last:Result,
    #[cfg(tiny_dev)]
    stats:Vec<crate::search::Stats>,
}
struct Shared {state:Mutex<State>, job:RwLock<Job>, wake:Condvar, done:Condvar}
pub struct Runtime {
    shared:Arc<Shared>, table:Arc<Table>, pub control:Arc<Control>, #[cfg(tiny_dev)]handles:Vec<JoinHandle<()>>,
}

fn output(result:Result, #[cfg(tiny_dev)]nodes:u64) {
    let mut name=[b'0';5];
    let length=if result.best==0 {4} else {
        let (f,t)=(board::from(result.best),board::to(result.best));
        name[0]=b'a'+(f&7)as u8; name[1]=b'1'+(f>>4)as u8;
        name[2]=b'a'+(t&7)as u8; name[3]=b'1'+(t>>4)as u8;
        let p=board::promo(result.best) as usize;
        if p==0 {4} else {name[4]=b"  nbrq"[p];5}
    };
    let text=std::str::from_utf8(&name[..length]).unwrap();
    let mut out=io::stdout().lock();
    #[cfg(tiny_dev)]
    {
        use crate::search::{MATE,PLY};
        if result.score.abs()>=MATE-PLY as i32 {
            let mate=if result.score>0 {(MATE-result.score+1)/2} else {-(MATE+result.score+1)/2};
            write!(out,"info depth {} score mate {} nodes {}",result.depth,mate,nodes).unwrap();
        } else {write!(out,"info depth {} score cp {} nodes {}",result.depth,result.score,nodes).unwrap();}
        if result.best!=0 {write!(out," pv {text}").unwrap();}
        writeln!(out).unwrap();
    }
    writeln!(out,"bestmove {text}").unwrap(); out.flush().unwrap();
}

impl Runtime {
    pub fn new(count:usize,bits:usize)->io::Result<Self> {
        let board=Board::start();
        let shared=Arc::new(Shared {
            state:Mutex::new(State {epoch:0,ready:0,pending:0,#[cfg(tiny_dev)]quit:false,#[cfg(tiny_dev)]reset:false,results:vec![empty();count],learned:[0;1024],fallback:0,#[cfg(tiny_dev)]last:empty(),
                #[cfg(tiny_dev)]stats:vec![crate::search::Stats::default();count]}),
            job:RwLock::new(Job {board,keys:[0;4096],length:0,frozen:[0;1024],epoch:0,limits:Limits {depth:1,#[cfg(tiny_dev)]nodes:0,millis:None}}),
            wake:Condvar::new(),done:Condvar::new(),
        });
        let runtime=Self {shared,table:Arc::new(Table::new(bits)),control:Arc::new(Control::new()),#[cfg(tiny_dev)]handles:Vec::with_capacity(count)};
        #[cfg(tiny_dev)]let mut runtime=runtime;
        // Initialize stdout before any search can emit a result.
        io::stdout().lock().flush()?;
        for id in 0..count {
            let (shared,table,control)=(runtime.shared.clone(),runtime.table.clone(),runtime.control.clone());
            let _handle=thread::Builder::new().stack_size(1024*1024).spawn(move || {
                std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                    let mut worker=Worker::new(id);
                    let mut seen=0;
                    let mut state=shared.state.lock().unwrap();
                    state.ready+=1; shared.done.notify_one();
                    loop {
                        while state.epoch==seen {#[cfg(tiny_dev)]{if state.quit {break;}}state=shared.wake.wait(state).unwrap();}
                        #[cfg(tiny_dev)]{if state.quit {break;}}
                        seen=state.epoch; #[cfg(tiny_dev)]let reset=state.reset; drop(state);
                        let result=(|| {
                            #[cfg(tiny_dev)]{if reset {worker.reset();return empty();}}
                            let job=shared.job.read().unwrap();
                            let mut result=worker.think(&job.board,&job.keys[..job.length],&job.frozen,job.epoch,job.limits,&table,&control);
                            let legal=job.board.legal();
                            if !legal.a[..legal.n].contains(&result.best) {result.best=0;}
                            result
                        })();
                        state=shared.state.lock().unwrap();
                        state.results[id]=result;
                        #[cfg(tiny_dev)]
                        {state.stats[id]=worker.stats;}
                        if id==0 {state.learned=worker.correction;}
                        state.pending-=1;
                        if state.pending==0 {
                            #[cfg(tiny_dev)]{if reset {shared.done.notify_one();continue;}}
                                let mut chosen=state.results[0];
                                for value in &state.results[1..] {if value.depth>chosen.depth {chosen=*value;}}
                                if chosen.best==0 {chosen.best=state.fallback;}
                                #[cfg(tiny_dev)]{state.last=chosen;output(chosen,control.nodes.load(Ordering::Relaxed));}
                                #[cfg(not(tiny_dev))]{output(chosen);}
                            shared.done.notify_one();
                        }
                    }
                })).unwrap_or_else(|_|std::process::abort());
            })?;
            #[cfg(tiny_dev)]{runtime.handles.push(_handle);}
        }
        let mut state=runtime.shared.state.lock().unwrap();
        while state.ready<count {state=runtime.shared.done.wait(state).unwrap();}
        drop(state); Ok(runtime)
    }
    pub fn finish(&self) {
        self.control.stop.store(true,Ordering::Relaxed);
        let mut state=self.shared.state.lock().unwrap();
        while state.pending!=0 {state=self.shared.done.wait(state).unwrap();}
    }
    pub fn start(&mut self,board:&Board,keys:&[u64],limits:Limits) {
        self.finish();
        let mut state=self.shared.state.lock().unwrap();
        {
            let mut job=self.shared.job.write().unwrap();
            job.board=*board; job.keys[..keys.len()].copy_from_slice(keys); job.length=keys.len();
            job.frozen=state.learned;
            job.epoch=job.frozen.iter().fold(0,|h,&v|board::mix(h^v as u16 as u64));
            job.limits=limits;
        }
        let legal=board.legal(); state.fallback=legal.a[..legal.n].first().copied().unwrap_or(0);
        state.results.fill(empty()); #[cfg(tiny_dev)]{state.reset=false;self.control.reset(limits.millis,limits.nodes);}
        #[cfg(not(tiny_dev))]{self.control.reset(limits.millis);}
        state.pending=state.results.len(); state.epoch=state.epoch.wrapping_add(1); self.shared.wake.notify_all();
    }
    #[cfg(tiny_dev)]
    pub fn reset(&mut self) {
        self.finish(); self.table.clear();
        self.control.nodes.store(0,Ordering::Relaxed);
        let mut state=self.shared.state.lock().unwrap();
        state.learned.fill(0); state.last=empty(); state.reset=true;
        state.pending=state.results.len(); state.epoch=state.epoch.wrapping_add(1); self.shared.wake.notify_all();
        while state.pending!=0 {state=self.shared.done.wait(state).unwrap();}
    }
    #[cfg(tiny_dev)]
    pub fn stats(&self)->(Result,u64) {(self.shared.state.lock().unwrap().last,self.control.nodes.load(Ordering::Relaxed))}
    #[cfg(tiny_dev)]
    pub fn workers(&self)->usize {self.handles.len()}
    #[cfg(tiny_dev)]
    pub fn epoch(&self)->u64 {self.shared.job.read().unwrap().epoch}
    #[cfg(test)]
    pub fn snapshots(&self)->([i16;1024],[i16;1024]) {
        let state=self.shared.state.lock().unwrap();
        (self.shared.job.read().unwrap().frozen,state.learned)
    }
    #[cfg(tiny_dev)]
    pub fn statistics(&self)->crate::search::Stats {
        let mut total=crate::search::Stats::default();
        for s in &self.shared.state.lock().unwrap().stats {
            total.pvs+=s.pvs;total.qs+=s.qs;total.hits+=s.hits;total.history+=s.history;
            total.continuation+=s.continuation;total.correction+=s.correction;total.uses+=s.uses;total.aborts+=s.aborts;
        }
        total
    }
}
#[cfg(tiny_dev)]
impl Drop for Runtime {
    fn drop(&mut self) {
        self.finish(); self.shared.state.lock().unwrap().quit=true; self.shared.wake.notify_all();
        for handle in self.handles.drain(..) {handle.join().expect("search worker panicked");}
    }
}
