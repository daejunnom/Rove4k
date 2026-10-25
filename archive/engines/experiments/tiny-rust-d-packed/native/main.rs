#![no_std]
#![no_main]
//! Independent Rust D: raw Linux startup and persistent guarded worker stacks.
mod board;
mod os;
mod search;
mod runtime;
use board::Board;
use search::Limits;

const fn number(value:Option<&str>,default:usize)->usize {
    match value {Some(text)=>{let b=text.as_bytes();let(mut i,mut n)=(0,0usize);while i<b.len(){if b[i]<b'0'||b[i]>b'9'{return 0;}n=n.saturating_mul(10).saturating_add((b[i]-b'0')as usize);i+=1;}if i==0{0}else{n}},None=>default}
}
const WORKERS:usize=number(option_env!("ROVE_WORKERS"),2);
const TT_BITS:usize=number(option_env!("ROVE_TT_BITS"),18);
pub const HQ:bool=number(option_env!("ROVE_HQ"),1)==1;
const _:()=assert!(WORKERS>=1&&WORKERS<=512&&TT_BITS>=8&&TT_BITS<=26);
const _:()=assert!(number(option_env!("ROVE_HQ"),1)<=1);

#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! {os::fatal(134)}

struct Input {bytes:[u8;4096],at:usize,end:usize}
impl Input {
    fn line(&mut self,out:&mut[u8;32768])->Option<Option<usize>> {
        let(mut n,mut valid)=(0,true);
        loop {
            if self.at==self.end {
                let count=os::read(&mut self.bytes);if count<0{os::fatal(121);}
                if count==0{return if n==0&&valid{None}else{Some(if valid{Some(n)}else{None})};}
                self.at=0;self.end=count as usize;
            }
            let b=self.bytes[self.at];self.at+=1;
            if valid {if n==out.len(){valid=false;}else{out[n]=b;n+=1;}}
            if b==b'\n'{return Some(if valid{Some(n)}else{None});}
        }
    }
}
fn position(words:&[&str])->Option<(Board,[u64;4096],usize)> {
    if words.get(1)!=Some(&"startpos"){return None;}
    let mut b=Board::start();let mut keys=[0;4096];keys[0]=b.hash;let mut length=1;let mut at=2;
    if words.get(at)==Some(&"moves"){at+=1;}else if words.len()!=at{return None;}
    for text in &words[at..] {if length==keys.len(){return None;}b=b.play(b.parse(text)?)?;keys[length]=b.hash;length+=1;}
    Some((b,keys,length))
}
fn limits(board:&Board,words:&[&str])->Limits {
    let mut result=Limits{depth:(search::PLY-2)as u8,nodes:0,millis:None};
    let(mut clock,mut inc,mut infinite)=(None,0u64,false);let mut i=1;
    while i<words.len() {
        if words[i]=="infinite"{infinite=true;}
        let value=words.get(i+1).and_then(|s|s.parse::<u64>().ok());
        match words[i] {"wtime" if board.side>0=>clock=Some(value.unwrap_or(0)),"btime" if board.side<0=>clock=Some(value.unwrap_or(0)),
            "winc" if board.side>0=>inc=value.unwrap_or(0),"binc" if board.side<0=>inc=value.unwrap_or(0),_=>{}}
        i+=if value.is_some(){2}else{1};
    }
    if !infinite{if let Some(t)=clock{result.millis=Some((t/30).saturating_add(inc.min(86400000)*3/4).min(t/5).clamp(1,86400000));}}
    result
}
#[unsafe(no_mangle)]
extern "C" fn engine_main()->! {
    let runtime=runtime::Runtime::new(WORKERS,TT_BITS);
    let mut board=Board::start();let mut keys=[0;4096];keys[0]=board.hash;let mut length=1;
    let mut input=Input{bytes:[0;4096],at:0,end:0};let mut bytes=[0;32768];
    while let Some(valid)=input.line(&mut bytes) {
        let Some(n)=valid else{continue};if bytes[..n].contains(&0){continue;}
        let Ok(line)=core::str::from_utf8(&bytes[..n])else{continue};let mut tokens=["";16384];let mut count=0;
        for word in line.split_whitespace(){if count==tokens.len(){count=0;break;}tokens[count]=word;count+=1;}
        let words=&tokens[..count];let Some(&command)=words.first()else{continue};
        match command {
            "uci"=>os::output(b"id name Rove4k Tiny D Rust\nuciok\n"),"isready"=>os::output(b"readyok\n"),
            "stop"=>runtime.finish(),"ucinewgame"=>runtime.reset(),
            "position"=>{runtime.finish();if let Some((b,k,n))=position(words){board=b;keys=k;length=n;}},
            "go"=>runtime.start(&board,&keys[..length],limits(&board,words)),"quit"=>break,_=>{},
        }
    }
    runtime.shutdown();os::fatal(0)
}
