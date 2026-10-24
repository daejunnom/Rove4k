//! Persistent raw-clone workers. Main owns Job only after finished generation.
use crate::{board::{self,Board},os,search::{Control,Limits,Result,Table,Worker}};
use core::{cell::UnsafeCell,mem::size_of,sync::atomic::{AtomicI32,AtomicU32,Ordering}};

struct Job {board:Board,keys:[u64;4096],length:usize,frozen:[i16;1024],epoch:u64,limits:Limits,reset:bool,fallback:u32}
struct Child {tid:AtomicI32,done:AtomicU32,result:UnsafeCell<Result>,owner:*const Runtime,id:usize,stack:*mut u8}
pub struct Runtime {
    generation:AtomicU32,finished:AtomicU32,ready:AtomicU32,quit:AtomicU32,
    job:UnsafeCell<Job>,learned:UnsafeCell<[i16;1024]>,children:*mut Child,count:usize,
    table:Table,pub control:Control,
}
// The only mutable non-atomic fields have phase ownership: main before release
// generation; workers while main waits finished; each result has one writer.
unsafe impl Sync for Runtime {}

impl Runtime {
    pub fn new(count:usize,bits:usize)->&'static Self {
        assert!(count>=1&&count<=512);
        let table=Table::new(bits);let children=os::allocate(count*size_of::<Child>())as *mut Child;
        let raw=os::allocate(size_of::<Self>())as *mut Self;
        let board=Board::start();
        unsafe{raw.write(Self {generation:AtomicU32::new(0),finished:AtomicU32::new(0),ready:AtomicU32::new(0),quit:AtomicU32::new(0),
            job:UnsafeCell::new(Job{board,keys:[0;4096],length:0,frozen:[0;1024],epoch:0,limits:Limits{depth:1,nodes:0,millis:None},reset:false,fallback:0}),
            learned:UnsafeCell::new([0;1024]),children,count,table,control:Control::new()});}
        // Construct every child record before spawning any reader of Runtime.
        for id in 0..count {unsafe{children.add(id).write(Child{tid:AtomicI32::new(0),done:AtomicU32::new(0),result:UnsafeCell::new(Result::default()),owner:raw,id,stack:os::stack()});}}
        for id in 0..count {unsafe{let child=&*children.add(id);os::spawn(child.stack,&child.tid,children.add(id)as *mut u8);}}
        let runtime=unsafe{&*raw};
        loop {let n=runtime.ready.load(Ordering::Acquire);if n==count as u32{break;}os::wait(&runtime.ready,n);}
        runtime
    }
    fn child(&self,id:usize)->&Child {unsafe{&*self.children.add(id)}}
    pub fn finish(&self) {
        self.control.stop.store(true,Ordering::Relaxed);
        let wanted=self.generation.load(Ordering::Acquire);
        loop {let value=self.finished.load(Ordering::Acquire);if value==wanted{break;}os::wait(&self.finished,value);}
    }
    fn publish(&self) {
        // Wrap is safe only after the old generation drained; workers compare
        // equality and all prior per-worker done words are reset before publish.
        let next=self.generation.load(Ordering::Relaxed).wrapping_add(1);
        for id in 0..self.count {self.child(id).done.store(next.wrapping_sub(1),Ordering::Relaxed);}
        self.generation.store(next,Ordering::Release);os::wake(&self.generation);
    }
    pub fn start(&self,board:&Board,keys:&[u64],limits:Limits) {
        self.finish();assert!(!keys.is_empty()&&keys.len()<=4096);
        let job=unsafe{&mut *self.job.get()};job.board=*board;job.keys[..keys.len()].copy_from_slice(keys);job.length=keys.len();
        job.frozen=unsafe{*self.learned.get()};job.epoch=job.frozen.iter().fold(0,|h,&v|board::mix(h^v as u16 as u64));job.limits=limits;job.reset=false;
        let moves=board.legal();job.fallback=moves.a[..moves.n].first().copied().unwrap_or(0);
        self.control.reset(limits.millis,limits.nodes);self.publish();
    }
    pub fn reset(&self) {
        self.finish();self.table.clear();unsafe{(*self.learned.get()).fill(0);(*self.job.get()).reset=true;}
        #[cfg(not(tiny_shipping))]self.control.nodes.store(0,Ordering::Relaxed);self.publish();self.finish();
    }
    pub fn shutdown(&self) {
        self.finish();self.quit.store(1,Ordering::Release);
        self.generation.fetch_add(1,Ordering::Release);os::wake(&self.generation);
        for id in 0..self.count {let child=self.child(id);os::join(&child.tid);unsafe{os::release(child.stack,os::STACK_MAP);}}
    }
}

fn output(value:Result) {
    let mut bytes=*b"bestmove 00000\n";let len;
    if value.best==0 {bytes[13]=b'\n';len=14;}else{
        let (f,t)=(board::from(value.best),board::to(value.best));
        bytes[9]=b'a'+(f&7)as u8;bytes[10]=b'1'+(f>>4)as u8;bytes[11]=b'a'+(t&7)as u8;bytes[12]=b'1'+(t>>4)as u8;
        let p=board::promo(value.best)as usize;if p==0{bytes[13]=b'\n';len=14;}else{bytes[13]=b"  nbrq"[p];len=15;}
    }os::output(&bytes[..len]);
}

#[unsafe(no_mangle)]
extern "C" fn worker_entry(argument:*mut u8) {
    let child=unsafe{&*(argument as *const Child)};let runtime=unsafe{&*child.owner};
    let mut worker=Worker::new(child.id);let mut seen=0;
    runtime.ready.fetch_add(1,Ordering::Release);os::wake(&runtime.ready);
    loop {
        let generation=loop {
            let g=runtime.generation.load(Ordering::Acquire);
            if runtime.quit.load(Ordering::Acquire)!=0{return;}
            if g!=seen{break g;}os::wait(&runtime.generation,g);
        };seen=generation;
        let job=unsafe{&*runtime.job.get()};let mut result=Result::default();
        if job.reset {worker.reset();}else{
            result=worker.think(&job.board,&job.keys[..job.length],&job.frozen,job.epoch,job.limits,&runtime.table,&runtime.control);
            let legal=job.board.legal();if !legal.a[..legal.n].contains(&result.best){result.best=0;}
        }
        unsafe{child.result.get().write(result);}
        child.done.store(generation,Ordering::Release);os::wake(&child.done);
        if child.id==0 {
            for id in 1..runtime.count {let other=runtime.child(id);loop{let n=other.done.load(Ordering::Acquire);if n==generation{break;}os::wait(&other.done,n);}}
            let mut chosen=result;
            for id in 1..runtime.count {let value=unsafe{*runtime.child(id).result.get()};if value.depth>chosen.depth{chosen=value;}}
            unsafe{*runtime.learned.get()=worker.correction;}
            if !job.reset {if chosen.best==0{chosen.best=job.fallback;}output(chosen);}
            // No job/result borrow is used after this release. Physical output
            // completed before main can accept completion or reuse these fields.
            runtime.finished.store(generation,Ordering::Release);os::wake(&runtime.finished);
        }
    }
}
