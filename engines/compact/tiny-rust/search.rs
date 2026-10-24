//! Independent compact A: fixed storage, one PVS/QS routine and coherent TT.
use crate::board::{Board,Move,from,to,promo,mix,value};
use std::sync::atomic::{AtomicBool,AtomicU64,Ordering};
use std::time::Instant;
pub const PLY:usize=128;
pub const MATE:i32=30000;
#[derive(Clone,Copy)]pub struct Limits{pub depth:u8,#[cfg(tiny_dev)]pub nodes:u64,pub millis:Option<u64>}
#[derive(Clone,Copy,Default,Debug)]pub struct Result{pub best:Move,#[cfg(tiny_dev)]pub score:i32,pub depth:u8,#[cfg(tiny_dev)]pub nodes:u64}
pub struct Control{pub stop:AtomicBool,#[cfg(tiny_dev)]pub nodes:AtomicU64,#[cfg(tiny_dev)]pub node_limit:AtomicU64,pub deadline_ms:AtomicU64,pub origin:Instant}
impl Control{
 pub fn new()->Self{Self{stop:AtomicBool::new(true),#[cfg(tiny_dev)]nodes:AtomicU64::new(0),#[cfg(tiny_dev)]node_limit:AtomicU64::new(0),deadline_ms:AtomicU64::new(u64::MAX),origin:Instant::now()}}
 pub fn now(&self)->u64{self.origin.elapsed().as_millis().min(u64::MAX as u128)as u64}
 #[cfg(not(tiny_dev))]
 pub fn reset(&self,millis:Option<u64>){self.deadline_ms.store(millis.map_or(u64::MAX,|n|self.now().saturating_add(n.max(1))),Ordering::Relaxed);self.stop.store(false,Ordering::Relaxed);}
 #[cfg(tiny_dev)]
 pub fn reset(&self,millis:Option<u64>,nodes:u64){self.nodes.store(0,Ordering::Relaxed);self.node_limit.store(nodes,Ordering::Relaxed);self.deadline_ms.store(millis.map_or(u64::MAX,|n|self.now().saturating_add(n.max(1))),Ordering::Relaxed);self.stop.store(false,Ordering::Relaxed);}
 pub fn cancelled(&self)->bool{self.stop.load(Ordering::Relaxed)}
}
struct Slot{lock:AtomicBool,key:AtomicU64,data:AtomicU64}
pub struct Table{slots:Vec<Slot>,mask:usize}
#[derive(Clone,Copy,Debug)]pub struct Entry{pub mv:Move,pub score:i32,pub depth:u8,pub bound:u8}
impl Table{
 pub fn new(bits:usize)->Self{assert!((8..=26).contains(&bits));let n=1usize<<bits;Self{slots:(0..n).map(|_|Slot{lock:AtomicBool::new(false),key:AtomicU64::new(0),data:AtomicU64::new(0)}).collect(),mask:n-1}}
 // Every payload read/write holds the same nonblocking exclusive slot lock.
 fn slot(&self,key:u64)->Option<&Slot>{let s=&self.slots[key as usize&self.mask];s.lock.compare_exchange(false,true,Ordering::Acquire,Ordering::Relaxed).ok().map(|_|s)}
 #[cfg(tiny_dev)]
 pub fn clear(&self){for s in &self.slots{if s.lock.compare_exchange(false,true,Ordering::Acquire,Ordering::Relaxed).is_ok(){s.data.store(0,Ordering::Relaxed);s.lock.store(false,Ordering::Release);}}}
 pub fn get(&self,key:u64,ply:usize)->Option<Entry>{let s=self.slot(key)?;let k=s.key.load(Ordering::Relaxed);let d=s.data.load(Ordering::Relaxed);s.lock.store(false,Ordering::Release);let bound=((d>>41)&3)as u8;if k!=key||bound==0{return None;}let mut score=((d>>17)as u16 as i16)as i32;if score>MATE-PLY as i32{score-=ply as i32;}if score< -MATE+PLY as i32{score+=ply as i32;}Some(Entry{mv:(d&131071)as Move,score,depth:(d>>33)as u8,bound})}
 pub fn put(&self,key:u64,mut e:Entry,ply:usize){if e.score>MATE-PLY as i32{e.score+=ply as i32;}if e.score< -MATE+PLY as i32{e.score-=ply as i32;}let Some(s)=self.slot(key)else{return};let data=e.mv as u64|((e.score as i16 as u16 as u64)<<17)|((e.depth as u64)<<33)|((e.bound as u64)<<41);s.key.store(key,Ordering::Relaxed);s.data.store(data,Ordering::Relaxed);s.lock.store(false,Ordering::Release);}
}
#[cfg(tiny_dev)]#[derive(Default,Clone,Copy)]pub struct Stats{pub pvs:u64,pub qs:u64,pub hits:u64,pub history:u64,pub continuation:u64,pub correction:u64,pub uses:u64,pub aborts:u64}
pub struct Worker{
 pub id:usize,pub nodes:u64,pub correction:[i16;1024],pub frozen:[i16;1024],
 history:[i16;16384],continuation:[i16;169],keys:[u64;4096+PLY],length:usize,epoch:u64,choice:Move,
 #[cfg(tiny_dev)]pub stats:Stats,
}
fn learn(cell:&mut i16,bonus:i32){let old=*cell as i32;*cell=(old+bonus-old*bonus.abs()/16384).clamp(-16384,16384)as i16;}
impl Worker{
 pub fn new(id:usize)->Self{Self{id,nodes:0,correction:[0;1024],frozen:[0;1024],history:[0;16384],continuation:[0;169],keys:[0;4096+PLY],length:0,epoch:0,choice:0,#[cfg(tiny_dev)]stats:Stats::default()}}
 #[cfg(tiny_dev)]
 pub fn reset(&mut self){self.correction.fill(0);self.frozen.fill(0);self.history.fill(0);self.continuation.fill(0);self.nodes=0;self.length=0;self.epoch=0;self.choice=0;#[cfg(tiny_dev)]{self.stats=Stats::default();}}
 fn key(&self,b:&Board)->u64{mix(b.hash^b.context.rotate_left(17)^((b.halfmove as u64)<<48)^self.epoch)}
 fn evaluation(&mut self,b:&Board)->i32{#[cfg(tiny_dev)]{self.stats.uses+=1;}(b.side as i32*b.score+self.frozen[b.hash as usize&1023]as i32/64).clamp(-MATE+PLY as i32+1,MATE-PLY as i32-1)}
 fn claim(&mut self,c:&Control)->Option<()>{
  if c.cancelled(){return None;}
  if self.nodes&255==0&&c.now()>=c.deadline_ms.load(Ordering::Relaxed){c.stop.store(true,Ordering::Relaxed);return None;}
  #[cfg(tiny_dev)]{
   let limit=c.node_limit.load(Ordering::Relaxed);
   if limit==0{c.nodes.fetch_add(1,Ordering::Relaxed);}else if c.nodes.fetch_update(Ordering::Relaxed,Ordering::Relaxed,|n|if n<limit{Some(n+1)}else{None}).is_err(){c.stop.store(true,Ordering::Relaxed);return None;}
  }
  self.nodes+=1;Some(())
 }
 fn repeated(&self,b:&Board)->bool{let begin=self.length.saturating_sub(b.halfmove as usize+1);let mut found=0;let mut i=self.length as isize-3;while i>=begin as isize{if self.keys[i as usize]==b.hash{found+=1;}i-=2;}found>=2}
 fn search(&mut self,b:&Board,depth:i32,mut alpha:i32,beta:i32,ply:usize,previous:Move,t:&Table,c:&Control)->Option<i32>{
  self.claim(c)?;
  let check=b.in_check();let draw=b.halfmove>=100||self.repeated(b)||b.dead();let mut moves=b.pseudo();
  if draw||ply==PLY-1{for &m in &moves.a[..moves.n]{if b.play(m).is_some(){if !draw{#[cfg(tiny_dev)]{self.stats.aborts+=1;}c.stop.store(true,Ordering::Relaxed);return None;}return Some(0);}}return Some(if check{-MATE+ply as i32}else{0});}
  let key=self.key(b);let entry=t.get(key,ply);let tt=entry.map_or(0,|e|e.mv);
  if let Some(e)=entry{#[cfg(tiny_dev)]{self.stats.hits+=1;}if ply>0&&e.depth as i32>=depth.max(0)&&e.mv!=0&&moves.a[..moves.n].contains(&e.mv)&&b.play(e.mv).is_some()&&(e.bound==1||e.bound==2&&e.score>=beta||e.bound==3&&e.score<=alpha){return Some(e.score);}}
  let evaluation=self.evaluation(b);let quiet=depth<=0&&!check;let old=alpha;let mut best=if quiet{evaluation}else{-MATE};let mut bestmove=0;let mut legal=0;
  #[cfg(tiny_dev)]{if depth<=0{self.stats.qs+=1;}}
  if quiet{alpha=alpha.max(best);}
  let prior=if previous==0{6}else{(b.cells[to(previous)]+6)as usize};let mut scores=[0i32;512];
  for(i,&m)in moves.a[..moves.n].iter().enumerate(){let pi=(b.cells[from(m)]+6)as usize;scores[i]=if m==tt{1000000}else if b.capture(m){500000+value(b.captured(m),to(m)).abs()*16-value(b.cells[from(m)],from(m)).abs()}else{self.history[from(m)*128+to(m)]as i32+self.continuation[prior*13+pi]as i32+((m as usize*37+self.id*19)%17)as i32};if promo(m)!=0{scores[i]+=400000+promo(m)as i32*1000;}}
  for i in 0..moves.n{
   let mut j=i;for k in i+1..moves.n{if scores[k]>scores[j]{j=k;}}moves.a.swap(i,j);scores.swap(i,j);let m=moves.a[i];let Some(child)=b.play(m)else{continue};legal+=1;
   let tactical=b.capture(m)||promo(m)!=0;if quiet&&(!tactical||alpha>=beta){continue;}
   self.keys[self.length]=child.hash;self.length+=1;
   let result=if legal==1||depth<=0{self.search(&child,depth-1,-beta,-alpha,ply+1,m,t,c).map(|v|-v)}else{
    #[cfg(tiny_dev)]{self.stats.pvs+=1;}
    let reduce=depth>=4&&legal>=4&&!tactical&&!check&&!child.in_check();
    let mut score=self.search(&child,depth-1-i32::from(reduce),-alpha-1,-alpha,ply+1,m,t,c).map(|v|-v);
    if reduce&&score.is_some_and(|v|v>alpha){score=self.search(&child,depth-1,-alpha-1,-alpha,ply+1,m,t,c).map(|v|-v);}
    if score.is_some_and(|v|v>alpha&&v<beta){score=self.search(&child,depth-1,-beta,-alpha,ply+1,m,t,c).map(|v|-v);}score
   };
   self.length-=1;let score=result?;if c.cancelled(){return None;}
   if score>best{best=score;bestmove=m;if ply==0{self.choice=m;}}
   alpha=alpha.max(score);
   if alpha>=beta{if depth>0&&!tactical{let bonus=(depth*depth*16).min(2048);learn(&mut self.history[from(m)*128+to(m)],bonus);learn(&mut self.continuation[prior*13+(b.cells[from(m)]+6)as usize],bonus);#[cfg(tiny_dev)]{self.stats.history+=1;self.stats.continuation+=1;}}break;}
  }
  if legal==0{return Some(if check{-MATE+ply as i32}else{0});}
  if c.cancelled(){return None;}
  let bound=if best<=old{3}else if best>=beta{2}else{1};
  if depth>0&&bound==1&&!check&&bestmove!=0&&!b.capture(bestmove)&&promo(bestmove)==0&&best.abs()<MATE-PLY as i32{let error=(best-b.side as i32*b.score).clamp(-256,256);let cell=&mut self.correction[b.hash as usize&1023];*cell=(*cell as i32+error-*cell as i32/64).clamp(-16384,16384)as i16;#[cfg(tiny_dev)]{self.stats.correction+=1;}}
  t.put(key,Entry{mv:bestmove,score:best,depth:depth.max(0)as u8,bound},ply);Some(best)
 }
 pub fn think(&mut self,b:&Board,keys:&[u64],frozen:&[i16;1024],epoch:u64,limits:Limits,t:&Table,c:&Control)->Result{
  assert!(!keys.is_empty()&&keys.len()<=4096&&keys.last()==Some(&b.hash));self.keys[..keys.len()].copy_from_slice(keys);self.length=keys.len();self.frozen.copy_from_slice(frozen);self.epoch=epoch;self.nodes=0;let mut result=Result::default();
  for depth in 1..=limits.depth.clamp(1,(PLY-2)as u8){self.choice=0;let Some(_score)=self.search(b,depth as i32,-MATE,MATE,0,0,t,c)else{break};if c.cancelled(){break;}result=Result{best:self.choice,#[cfg(tiny_dev)]score:_score,depth,#[cfg(tiny_dev)]nodes:self.nodes};}
  result
 }
}
#[cfg(test)]#[path="tests/search.rs"]mod tests;
