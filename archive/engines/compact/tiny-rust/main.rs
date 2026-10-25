//! Independent Rust Tiny A, with fixed startup resources and minimal shipping UCI.
mod board;
mod search;
mod runtime;
#[cfg(tiny_dev)]
mod dev;
#[cfg(test)]
#[path="tests/contracts.rs"]
mod contracts;
use board::Board;
use search::Limits;
use std::io::{self,BufRead,Write};

const fn number(value:Option<&str>,default:usize)->usize {
    match value {Some(text)=>{let b=text.as_bytes();let(mut i,mut n)=(0,0usize);while i<b.len(){if b[i]<b'0'||b[i]>b'9'{return 0;}n=n.saturating_mul(10).saturating_add((b[i]-b'0')as usize);i+=1;}if i==0 {0} else {n}},None=>default}
}
const WORKERS:usize=number(option_env!("ROVE_WORKERS"),2);
const TT_BITS:usize=number(option_env!("ROVE_TT_BITS"),16);

// The fixed buffer survives rejected lines; oversized input is drained to LF.
fn read<R:BufRead>(input:&mut R,bytes:&mut Vec<u8>)->io::Result<Option<bool>> {
    bytes.clear(); let mut bad=false;
    loop {
        let data=input.fill_buf()?;
        if data.is_empty() {return Ok(if bytes.is_empty()&&!bad {None} else {Some(!bad)});}
        let end=data.iter().position(|&c|c==b'\n'); let n=end.map_or(data.len(),|i|i+1);
        if !bad {if bytes.len()+n<=32768 {bytes.extend_from_slice(&data[..n]);} else {bad=true;bytes.clear();}}
        input.consume(n);
        if end.is_some() {return Ok(Some(!bad));}
    }
}
fn position(words:&[&str])->Option<(Board,[u64;4096],usize)> {
    let (board,at)=if words.get(1)==Some(&"startpos") {(Board::start(),2)} else {
        #[cfg(tiny_dev)]
        {
            if words.get(1)==Some(&"fen") && words.len()>=8 {
                return replay(dev::fen(&words[2..8])?,words,8);
            }
        }
        return None;
    };
    replay(board,words,at)
}
fn replay(mut board:Board,words:&[&str],mut at:usize)->Option<(Board,[u64;4096],usize)> {
    let mut keys=[0;4096]; keys[0]=board.hash; let mut length=1;
    if words.get(at)==Some(&"moves") {at+=1;} else if at!=words.len() {return None;}
    for text in &words[at..] {
        if length==keys.len() {return None;}
        board=board.play(board.parse(text)?)?; keys[length]=board.hash; length+=1;
    }
    Some((board,keys,length))
}
#[cfg(tiny_dev)]
fn limits(board:&Board,words:&[&str])->Limits {
    let mut limits=Limits {depth:(search::PLY-2)as u8,nodes:0,millis:None};
    let(mut clock,mut inc,mut infinite)=(None,0u64,false);
    let mut i=1;
    while i<words.len() {
        if words[i]=="infinite" {infinite=true;}
        let value=words.get(i+1).and_then(|v|v.parse::<u64>().ok());
        match words[i] {
            "wtime" if board.side>0=>clock=Some(value.unwrap_or(0)),"btime" if board.side<0=>clock=Some(value.unwrap_or(0)),
            "winc" if board.side>0=>inc=value.unwrap_or(0),"binc" if board.side<0=>inc=value.unwrap_or(0),_=>{}
        }
        i+=if value.is_some() {2} else {1};
    }
    #[cfg(tiny_dev)]
    {infinite|=dev::limits(words,&mut limits);}
    if infinite {limits.millis=None;} else if limits.millis.is_none() {
        if let Some(t)=clock {limits.millis=Some((t/30).saturating_add(inc.min(86400000)*3/4).min(t/5).clamp(1,86400000));}
    }
    limits
}
#[cfg(not(tiny_dev))]
fn limits(board:&Board,words:&[&str])->Limits {
    let(mut clock,mut inc)=(None,0u64);
    let mut i=1;
    while i<words.len() {
        let value=words.get(i+1).and_then(|v|v.parse::<u64>().ok());
        match words[i] {
            "wtime" if board.side>0=>clock=Some(value.unwrap_or(0)),"btime" if board.side<0=>clock=Some(value.unwrap_or(0)),
            "winc" if board.side>0=>inc=value.unwrap_or(0),"binc" if board.side<0=>inc=value.unwrap_or(0),_=>{}
        }
        i+=if value.is_some() {2} else {1};
    }
    let millis=clock.map_or(1000,|t|(t/30).saturating_add(inc.min(86400000)*3/4).min(t/5).clamp(1,86400000));
    Limits{depth:(search::PLY-2)as u8,millis:Some(millis)}
}
fn main() {
    assert!((1..=512).contains(&WORKERS) && (8..=26).contains(&TT_BITS));
    let mut board=Board::start(); let mut keys=[0;4096]; keys[0]=board.hash; let mut length=1;
    let mut bytes=Vec::with_capacity(32768);
    let mut runtime=runtime::Runtime::new(WORKERS,TT_BITS).expect("fixed worker startup failed");
    let stdin=io::stdin(); let mut input=stdin.lock();
    while let Ok(Some(valid))=read(&mut input,&mut bytes) {
        if !valid || bytes.contains(&0) {continue;}
        let Ok(line)=std::str::from_utf8(&bytes) else {continue};
        let mut tokens=["";16384]; let mut count=0;
        for word in line.split_whitespace() {tokens[count]=word;count+=1;}
        let words=&tokens[..count]; let Some(&command)=words.first() else {continue};
        match command {
            "uci"=>{#[cfg(tiny_dev)]{println!("id name Rove4k Tiny A Rust\nuciok");}#[cfg(not(tiny_dev))]{println!("uciok");}},
            "isready"=>println!("readyok"),
            #[cfg(tiny_dev)]
            "stop"=>runtime.finish(),
            #[cfg(tiny_dev)]
            "ucinewgame"=>runtime.reset(),
            "position"=>{runtime.finish();if let Some((b,k,n))=position(words) {board=b;keys=k;length=n;}},
            "go"=>runtime.start(&board,&keys[..length],limits(&board,words)),
            "quit"=>break,
            _=>{
                #[cfg(tiny_dev)]
                {runtime.finish();dev::command(words,&board,&keys[..length],&mut runtime);}
            }
        }
        io::stdout().flush().unwrap();
    }
    #[cfg(tiny_dev)]{runtime.finish();}
    #[cfg(not(tiny_dev))]{std::process::exit(0);}
}
