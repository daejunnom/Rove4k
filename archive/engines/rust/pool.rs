//! Fixed startup workers. Command/depth epochs are barriers, not thread lifetimes.
use crate::board::{Board, Move};
use crate::parallel::Engine;
use crate::search::{Control, Limits, SearchResult, Searcher};
use std::io;
use std::sync::{Arc, Condvar, Mutex, RwLock, atomic::Ordering};
use std::thread::{self, JoinHandle};

pub trait Task: Send + Sync + 'static {
    fn work(&self, searcher: &mut Searcher, worker: usize) -> Option<SearchResult>;
}

struct WorkersState {
    epoch: u64, ready: usize, pending: usize, shutdown: bool,
    results: Vec<Option<SearchResult>>,
}
struct WorkersShared<T> {
    state: Mutex<WorkersState>, wake: Condvar, done: Condvar, task: RwLock<T>,
}
pub struct Helpers<T: Task> {
    shared: Arc<WorkersShared<T>>, handles: Vec<JoinHandle<()>>,
}
impl<T: Task> Helpers<T> {
    pub fn new(task: T, searchers: Vec<Searcher>) -> io::Result<Self> {
        let count = searchers.len();
        let shared = Arc::new(WorkersShared { state: Mutex::new(WorkersState {
            epoch: 0, ready: 0, pending: 0, shutdown: false, results: vec![None; count],
        }), wake: Condvar::new(), done: Condvar::new(), task: RwLock::new(task) });
        let mut result = Self { shared, handles: Vec::with_capacity(count) };
        for (i, mut searcher) in searchers.into_iter().enumerate() {
            let shared = result.shared.clone();
            let handle = thread::Builder::new().name(format!("rove-search-{}", i + 1)).stack_size(1024 * 1024).spawn(move || {
                let mut epoch = 0;
                let mut state = shared.state.lock().unwrap();
                state.ready += 1;
                shared.done.notify_one();
                loop {
                    while !state.shutdown && state.epoch == epoch { state = shared.wake.wait(state).unwrap(); }
                    if state.shutdown { break; }
                    epoch = state.epoch;
                    drop(state);
                    // A failed search worker cannot leave an apparently healthy
                    // coordinator waiting forever or silently reduce the profile.
                    let value = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| shared.task.read().unwrap().work(&mut searcher, i + 1)))
                        .unwrap_or_else(|_| std::process::abort());
                    state = shared.state.lock().unwrap();
                    state.results[i] = value;
                    state.pending -= 1;
                    if state.pending == 0 { shared.done.notify_one(); }
                }
            });
            match handle { Ok(handle) => result.handles.push(handle), Err(error) => return Err(error) }
        }
        let mut state = result.shared.state.lock().unwrap();
        while state.ready != count { state = result.shared.done.wait(state).unwrap(); }
        drop(state);
        Ok(result)
    }
    /// There is no live reader from the previous depth when this is called.
    pub fn prepare(&mut self, prepare: impl FnOnce(&mut T)) {
        self.wait();
        prepare(&mut self.shared.task.write().unwrap());
    }
    pub fn begin(&self) {
        let mut state = self.shared.state.lock().unwrap();
        assert_eq!(state.pending, 0);
        state.results.fill(None);
        state.pending = self.handles.len();
        state.epoch = state.epoch.wrapping_add(1);
        self.shared.wake.notify_all();
    }
    pub fn task<R>(&self, work: impl FnOnce(&T) -> R) -> R { work(&self.shared.task.read().unwrap()) }
    pub fn wait(&self) {
        let mut state = self.shared.state.lock().unwrap();
        while state.pending != 0 { state = self.shared.done.wait(state).unwrap(); }
    }
    pub fn first_result(&self) -> Option<SearchResult> {
        self.wait();
        self.shared.state.lock().unwrap().results.iter().copied().flatten().next()
    }
}
impl<T: Task> Drop for Helpers<T> {
    fn drop(&mut self) {
        // All normal callers drain the barrier before shutdown. A partially
        // constructed pool has no submitted tasks and uses the same join path.
        self.wait();
        self.shared.state.lock().unwrap().shutdown = true;
        self.shared.wake.notify_all();
        for handle in self.handles.drain(..) { handle.join().expect("search helper panicked"); }
    }
}

enum Request { Search(Limits), Reset }
struct State { request: Option<Request>, active: bool, ready: bool, shutdown: bool }
struct Shared { state: Mutex<State>, wake: Condvar, done: Condvar, board: RwLock<Board> }

/// One coordinator is itself search worker zero. There are exactly N search
/// threads plus the caller's stdin thread; no extra supervisor is introduced.
pub struct Runtime {
    shared: Arc<Shared>, control: Arc<Control>, handle: Option<JoinHandle<()>>,
}
impl Runtime {
    pub fn new(variant: u8, workers: usize, tt_bits: usize, mode: u8) -> io::Result<Self> {
        let limits = Limits { depth: 1, nodes: 0, movetime: None };
        let control = Arc::new(Control::new(&limits));
        // TT, history, PV storage and every helper are ready before the stdin
        // command loop. A spawn/allocation failure fails startup explicitly.
        let mut engine = Engine::new(variant, workers, tt_bits, control.clone(), mode)?;
        let board = Board::start();
        let shared = Arc::new(Shared { state: Mutex::new(State { request: None, active: false, ready: false, shutdown: false }),
            wake: Condvar::new(), done: Condvar::new(), board: RwLock::new(board) });
        let worker_shared = shared.clone();
        let handle = thread::Builder::new().name("rove-search-0".into()).stack_size(1024 * 1024).spawn(move || {
            let mut state = worker_shared.state.lock().unwrap();
            state.ready = true;
            worker_shared.done.notify_one();
            loop {
                while !state.shutdown && state.request.is_none() { state = worker_shared.wake.wait(state).unwrap(); }
                if state.shutdown { break; }
                let request = state.request.take().unwrap();
                drop(state);
                // Panic cannot be mistaken for a completed/cancelled search.
                std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| match request {
                    Request::Search(limits) => {
                        let board = worker_shared.board.read().unwrap();
                        let legal = board.legal();
                        let fallback = legal.first().copied();
                        let result = engine.execute(&board, &limits);
                        let chosen = result.filter(|r| r.completed).map(|r| r.best).filter(|m| *m != Move::default() && legal.contains(m)).or(fallback);
                        println!("bestmove {}", chosen.map_or_else(|| "0000".into(), Move::uci));
                    },
                    Request::Reset => engine.reset(),
                })).unwrap_or_else(|_| std::process::abort());
                state = worker_shared.state.lock().unwrap();
                state.active = false;
                worker_shared.done.notify_one();
            }
        })?;
        let mut state = shared.state.lock().unwrap();
        while !state.ready { state = shared.done.wait(state).unwrap(); }
        drop(state);
        Ok(Self { shared, control, handle: Some(handle) })
    }
    pub fn control(&self) -> Arc<Control> { self.control.clone() }
    pub fn finish(&self) {
        self.control.stop.store(true, Ordering::Relaxed);
        self.wait();
    }
    pub fn wait(&self) {
        let mut state = self.shared.state.lock().unwrap();
        while state.active { state = self.shared.done.wait(state).unwrap(); }
    }
    pub fn start(&mut self, board: &Board, limits: Limits) {
        self.finish();
        self.shared.board.write().unwrap().reuse_from(board);
        self.control.reset(&limits);
        let mut state = self.shared.state.lock().unwrap();
        state.active = true;
        state.request = Some(Request::Search(limits));
        self.shared.wake.notify_one();
    }
    pub fn reset(&mut self) {
        self.finish();
        {
            let mut state = self.shared.state.lock().unwrap();
            state.active = true;
            state.request = Some(Request::Reset);
            self.shared.wake.notify_one();
        }
        self.wait();
    }
}
impl Drop for Runtime {
    fn drop(&mut self) {
        self.finish();
        self.shared.state.lock().unwrap().shutdown = true;
        self.shared.wake.notify_one();
        if let Some(handle) = self.handle.take() { handle.join().expect("search coordinator panicked"); }
    }
}
