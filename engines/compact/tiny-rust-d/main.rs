#![no_std]
#![no_main]
//! ASCII streaming input candidate; all non-ASCII or NUL lines are rejected.
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

fn whitespace(b:u8)->bool {b==b' '||(9..=13).contains(&b)}
#[derive(Clone,Copy)]
struct Words<'a> {bytes:&'a[u8]}
impl<'a> Iterator for Words<'a> {
    type Item=&'a[u8];
    fn next(&mut self)->Option<Self::Item> {
        let mut at=0;
        while at<self.bytes.len()&&whitespace(self.bytes[at]) {at+=1;}
        let start=at;
        while at<self.bytes.len()&&!whitespace(self.bytes[at]) {at+=1;}
        let word=&self.bytes[start..at];self.bytes=&self.bytes[at..];
        if word.is_empty(){None}else{Some(word)}
    }
}
fn unsigned(bytes:&[u8])->Option<u64> {
    let bytes=if bytes.first()==Some(&b'+'){&bytes[1..]}else{bytes};
    if bytes.is_empty(){return None;}
    let mut value=0u64;
    for &b in bytes {
        let digit=b.wrapping_sub(b'0');if digit>9{return None;}
        value=value.checked_mul(10)?.checked_add(digit as u64)?;
    }
    Some(value)
}
fn position(mut words:Words<'_>)->Option<(Board,[u64;4096],usize)> {
    if words.next()!=Some(b"startpos".as_slice()){return None;}
    if let Some(word)=words.next(){if word!=b"moves"{return None;}}
    let mut b=Board::start();let mut keys=[0;4096];keys[0]=b.hash;let mut length=1;
    for text in words {if length==keys.len(){return None;}b=b.play(b.parse_bytes(text)?)?;keys[length]=b.hash;length+=1;}
    Some((b,keys,length))
}
fn limits(board:&Board,mut words:Words<'_>)->Limits {
    let mut result=Limits{depth:(search::PLY-2)as u8,nodes:0,millis:None};
    let(mut clock,mut inc,mut infinite)=(None,0u64,false);
    while let Some(word)=words.next() {
        if word==b"infinite"{infinite=true;}
        let value=words.clone().next().and_then(unsigned);
        match word {b"wtime" if board.side>0=>clock=Some(value.unwrap_or(0)),b"btime" if board.side<0=>clock=Some(value.unwrap_or(0)),
            b"winc" if board.side>0=>inc=value.unwrap_or(0),b"binc" if board.side<0=>inc=value.unwrap_or(0),_=>{}}
        if value.is_some(){words.next();}
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
        let Some(n)=valid else{continue};let line=&bytes[..n];
        if line.iter().any(|&b|b==0||!b.is_ascii()){continue;}
        // A line of <=32768 bytes has <=16384 nonempty ASCII tokens.
        let mut words=Words{bytes:line};let Some(command)=words.next()else{continue};
        match command {
            b"uci"=>os::output(b"id name Rove4k Tiny D Rust\nuciok\n"),b"isready"=>os::output(b"readyok\n"),
            b"stop"=>runtime.finish(),b"ucinewgame"=>runtime.reset(),
            b"position"=>{runtime.finish();if let Some((b,k,n))=position(words){board=b;keys=k;length=n;}},
            b"go"=>runtime.start(&board,&keys[..length],limits(&board,words)),b"quit"=>break,_=>{},
        }
    }
    runtime.shutdown();os::fatal(0)
}
