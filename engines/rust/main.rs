//! Rove4k's independent Rust engine. Build-time selection removes development
//! commands and resource choices from a shipping executable.
mod board;
mod eval;
mod search;
mod parallel;
use board::{Board,Move};
use search::{Control,Limits};
use std::io::{self,BufRead};
use std::sync::{Arc,atomic::Ordering};
use std::thread::{self,JoinHandle};
use std::time::Duration;

const fn number(v:Option<&str>,default:usize)->usize {
    match v {None=>default,Some(s)=>{let b=s.as_bytes();let(mut i,mut n)=(0,0usize);while i<b.len(){if b[i]<b'0'||b[i]>b'9'{return default;}n=n.saturating_mul(10).saturating_add((b[i]-b'0')as usize);i+=1;}if i==0{default}else{n}}}
}
const fn letter(v:Option<&str>,default:u8)->u8 {match v{Some(s)if !s.is_empty()=>s.as_bytes()[0],_=>default}}
pub const DEV:bool=letter(option_env!("ROVE_DEV"),b'0')==b'1';
const VARIANT:u8=letter(option_env!("ROVE_VARIANT"),b'A');
const WORKERS:usize=number(option_env!("ROVE_WORKERS"),2);
const TT_BITS:usize=number(option_env!("ROVE_TT_BITS"),16);
const PARALLEL:u8=number(option_env!("ROVE_PARALLEL"),0)as u8;

struct Active {control:Arc<Control>,handle:JoinHandle<()>}
fn finish(active:&mut Option<Active>){if let Some(a)=active.take(){a.control.stop.store(true,Ordering::Relaxed);let _=a.handle.join();}}
fn diagnostic(s:impl std::fmt::Display){if DEV{println!("info string {s}");}}
fn read_command<R:BufRead>(input:&mut R)->io::Result<Option<Result<String,()>>>{
    let mut bytes=Vec::new();let mut oversized=false;
    loop{
        let data=input.fill_buf()?;
        if data.is_empty(){return Ok(if bytes.is_empty()&&!oversized{None}else{Some(if oversized{Err(())}else{String::from_utf8(bytes).map_err(|_|())})});}
        let end=data.iter().position(|&c|c==b'\n');let n=end.map_or(data.len(),|i|i+1);
        if !oversized{if bytes.len()+n<=32768{bytes.extend_from_slice(&data[..n]);}else{oversized=true;bytes.clear();}}
        input.consume(n);
        if end.is_some(){return Ok(Some(if oversized{Err(())}else{String::from_utf8(bytes).map_err(|_|())}));}
    }
}
fn set_position(old:&Board,words:&[&str])->Result<Board,String>{
    let(mut b,mut at)=if words.get(1)==Some(&"startpos"){(Board::start(),2)}
        else if DEV&&words.get(1)==Some(&"fen")&&words.len()>=8{(Board::from_fen(&words[2..8].join(" "))?,8)}
        else{return Err("unsupported position".into())};
    if words.get(at)==Some(&"moves"){at+=1;if words.len()-at>4096{return Err("position exceeds 4096 moves".into());}for text in &words[at..]{let m=b.parse_move(text).ok_or_else(||format!("illegal move {text}"))?;b=b.play(m);}}
    else if at!=words.len(){return Err("unexpected position suffix".into());}
    let _=old;
    Ok(b)
}
fn go_limits(board:&Board,words:&[&str])->Limits{
    let mut l=Limits{depth:64,nodes:0,movetime:None};
    let(mut white,mut black,mut wi,mut bi)=(None,None,0u64,0u64);
    let mut infinite=false;
    let mut i=1;
    while i<words.len(){
        let n=words.get(i+1).and_then(|s|s.parse::<u64>().ok());
        match words[i]{
            "wtime"=>white=n,"btime"=>black=n,"winc"=>wi=n.unwrap_or(0),"binc"=>bi=n.unwrap_or(0),
            "depth" if DEV=>{l.depth=n.unwrap_or(1).clamp(1,90)as u8;},
            "nodes" if DEV=>l.nodes=n.unwrap_or(1).max(1),
            "movetime" if DEV=>l.movetime=Some(Duration::from_millis(n.unwrap_or(1).max(1))),
            "infinite" if DEV=>{infinite=true;l.depth=90;},_=>{}
        }
        i+=if n.is_some(){2}else{1};
    }
    let remaining=if board.side>0{white}else{black};
    if l.movetime.is_none(){if let Some(t)=remaining{let inc=if board.side>0{wi}else{bi};let ms=(t/30).saturating_add(inc.saturating_mul(3)/4).min(t.saturating_sub(10)).max(1);l.movetime=Some(Duration::from_millis(ms));}
        else if !DEV || (!infinite&&l.depth==64&&l.nodes==0){l.movetime=Some(Duration::from_millis(if DEV{1000}else{1}));}}
    l
}

fn main(){
    assert!((b'A'..=b'F').contains(&VARIANT),"ROVE_VARIANT must be A..F");
    assert!((1..=512).contains(&WORKERS),"ROVE_WORKERS must be 1..512");
    assert!(PARALLEL<=4,"ROVE_PARALLEL must be 0..4");
    eval::init_model();
    let mut board=Board::start();
    let mut active:Option<Active>=None;
    let mut last_control:Option<Arc<Control>>=None;
    let stdin=io::stdin();let mut input=stdin.lock();
    loop{
        let line=match read_command(&mut input){Ok(Some(Ok(line)))=>line,Ok(Some(Err(())))=>{diagnostic("command exceeds input bound or is not UTF-8");continue;},_=>break};
        let w:Vec<_>=line.split_whitespace().collect();
        let Some(&cmd)=w.first()else{continue};
        match cmd{
            "uci"=>{println!("id name Rove4k {} Rust",VARIANT as char);println!("id author Rove4k");println!("uciok");},
            "isready"=>println!("readyok"),
            "position"=>{finish(&mut active);match set_position(&board,&w){Ok(b)=>board=b,Err(e)=>diagnostic(e)}},
            "ucinewgame"=>{finish(&mut active);last_control=None;},
            "stop"=>finish(&mut active),
            "quit"=>{finish(&mut active);break;},
            "go"=>{
                finish(&mut active);
                let limits=go_limits(&board,&w);
                let control=Arc::new(Control::new(&limits));
                last_control=Some(control.clone());
                let(c,b)=(control.clone(),board.clone());
                let fallback=b.legal().first().copied();
                let handle=thread::spawn(move||{
                    let result=parallel::run(b,VARIANT,WORKERS,TT_BITS,limits,c,PARALLEL);
                    let chosen=result.filter(|r|r.completed).map(|r|r.best).filter(|m|*m!=Move::default()).or(fallback);
                    println!("bestmove {}",chosen.map_or_else(||"0000".into(),Move::uci));
                });
                active=Some(Active{control,handle});
            },
            "perft" if DEV=>{finish(&mut active);if let Some(d)=w.get(1).and_then(|s|s.parse::<u32>().ok()){if d<=7{println!("perft {d} {}",board.perft(d));}}},
            "legal" if DEV=>println!("legal {}",board.legal().into_iter().map(Move::uci).collect::<Vec<_>>().join(" ")),
            "fen"|"d"|"board" if DEV=>println!("fen {}",board.fen()),
            "hash" if DEV=>println!("hash {}",board.hash),
            "eval" if DEV=>println!("eval {}",eval::evaluate(&board,VARIANT)),
            "see" if DEV=>{if let Some(m)=w.get(1).and_then(|s|board.parse_move(s)){println!("see {}",board.see(m));}},
            "simd" if DEV=>{let scalar=eval::scalar(&board);if eval::simd_available(){println!("simd scalar {scalar} vector {}",eval::evaluate(&board,b'C'));}else{println!("simd unavailable scalar {scalar}");}},
            "state" if DEV=>{
                let mut rebuilt=board.clone();rebuilt.rebuild();
                println!("{{\"hash\":{},\"halfmove\":{},\"eval\":{},\"draw\":{},\"invariant\":{},\"fen\":\"{}\"}}",board.hash,board.halfmove,eval::evaluate(&board,VARIANT),board.halfmove>=100||board.repeated()||board.insufficient(),board.hash==rebuilt.hash&&board.bb==rebuilt.bb&&board.evalwhite()==rebuilt.evalwhite(),board.fen());
            },
            "stats" if DEV=>{if let Some(c)=&last_control{println!("{{\"nodes\":{},\"f_probes\":{},\"singular\":{},\"see_calls\":{},\"tt_hits\":{},\"bound_conflicts\":{},\"search_workers\":{},\"total_threads\":{}}}",c.nodes.load(Ordering::Relaxed),c.probes.load(Ordering::Relaxed),c.singular.load(Ordering::Relaxed),c.see_calls.load(Ordering::Relaxed),c.tt_hits.load(Ordering::Relaxed),c.conflicts.load(Ordering::Relaxed),WORKERS,WORKERS+1);}},
            _=>{}
        }
    }
    finish(&mut active);
}
