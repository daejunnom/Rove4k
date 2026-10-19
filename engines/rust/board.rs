// Independent chess rules: 0x88 move geometry, incremental piece bitboards.
use std::mem::MaybeUninit;
use std::ops::{Deref,DerefMut};
pub const VALUE: [i32; 7] = [0, 100, 320, 330, 500, 900, 20000];
const KNIGHT: [i16; 8] = [33, 31, 18, 14, -14, -18, -31, -33];
const KING: [i16; 8] = [1, -1, 16, -16, 17, 15, -15, -17];
const HQ:bool=match option_env!("ROVE_HQ"){
    Some(v)if v.as_bytes().len()==1=>v.as_bytes()[0]==b'1',
    _=>match option_env!("ROVE_VARIANT"){Some(v)=>v.as_bytes().len()==1&&v.as_bytes()[0]==b'D',None=>false},
};

#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
pub struct Move { pub from: u8, pub to: u8, pub promo: i8 }
impl Move {
    pub fn uci(self) -> String {
        let mut s = format!("{}{}", square_name(self.from), square_name(self.to));
        if self.promo != 0 { s.push(b"  nbrqk"[self.promo as usize] as char); }
        s
    }
}

pub const MOVE_CAPACITY:usize=512;
/// At most sixteen admitted pieces per side, each with at most 27 pseudo
/// destinations. Four promotion choices give a pawn at most 12 destinations.
#[derive(Clone,Copy)]
pub struct MoveList {moves:[MaybeUninit<Move>;MOVE_CAPACITY],len:usize}
impl MoveList{
    pub fn new()->Self{Self{moves:[MaybeUninit::uninit();MOVE_CAPACITY],len:0}}
    pub fn clear(&mut self){self.len=0;}
    pub fn try_push(&mut self,m:Move)->Result<(),&'static str>{if self.len==MOVE_CAPACITY{return Err("move capacity exceeded");}self.moves[self.len].write(m);self.len+=1;Ok(())}
    pub fn push(&mut self,m:Move){self.try_push(m).expect("admitted board exceeds move bound");}
    pub fn extend(&mut self,moves:impl IntoIterator<Item=Move>){for m in moves{self.push(m);}}
    pub fn retain(&mut self,mut keep:impl FnMut(&Move)->bool){let mut n=0;for i in 0..self.len{let m=self[i];if keep(&m){self.moves[n].write(m);n+=1;}}self.len=n;}
}
impl Deref for MoveList{type Target=[Move];fn deref(&self)->&[Move]{
    // Insertion initializes a slot before publishing len. Only that prefix is exposed.
    unsafe{std::slice::from_raw_parts(self.moves.as_ptr().cast(),self.len)}
}}
impl DerefMut for MoveList{fn deref_mut(&mut self)->&mut[Move]{unsafe{std::slice::from_raw_parts_mut(self.moves.as_mut_ptr().cast(),self.len)}}}
pub struct IntoMoves {moves:MoveList,at:usize}
impl Iterator for IntoMoves{type Item=Move;fn next(&mut self)->Option<Move>{if self.at==self.moves.len{None}else{let m=self.moves[self.at];self.at+=1;Some(m)}}fn size_hint(&self)->(usize,Option<usize>){let n=self.moves.len-self.at;(n,Some(n))}}
impl ExactSizeIterator for IntoMoves{}
impl IntoIterator for MoveList{type Item=Move;type IntoIter=IntoMoves;fn into_iter(self)->IntoMoves{IntoMoves{moves:self,at:0}}}
impl<'a> IntoIterator for &'a MoveList{type Item=&'a Move;type IntoIter=std::slice::Iter<'a,Move>;fn into_iter(self)->Self::IntoIter{self.iter()}}

/// Exact repetition suffix before halfmove 100. At a later replay position the
/// older keys cannot affect this engine's terminal draw decision. Mate precedes it.
#[derive(Clone,Copy,Debug)]
pub struct History {keys:[u64;101],len:u8}
impl History{
    fn new()->Self{Self{keys:[0;101],len:0}}
    pub fn clear(&mut self){self.len=0;}
    pub fn push(&mut self,key:u64){if self.len==101{self.keys.copy_within(1..101,0);self.len=100;}self.keys[self.len as usize]=key;self.len+=1;}
}
impl Deref for History{type Target=[u64];fn deref(&self)->&[u64]{&self.keys[..self.len as usize]}}

#[derive(Clone, Copy, Debug)]
pub struct Board {
    pub cells: [i8; 128],
    pub side: i8,
    pub castle: u8,
    pub ep: i16,
    pub halfmove: u16,
    pub fullmove: u16,
    pub hash: u64,
    pub hist: History,
    pub bb: [[u64; 7]; 2],
    pub king: [u8; 2],
    score: i32,
}

fn color(p: i8) -> usize { (p < 0) as usize }
fn valid(s: i16) -> bool { s >= 0 && s < 128 && s & 0x88 == 0 }
fn bit(s: u8) -> u64 { 1 << ((s >> 4) * 8 + (s & 7)) }
fn hq_line(piece:u64,occupancy:u64,mask:u64)->u64{
    let line=(occupancy|piece)&mask;
    (line.wrapping_sub(piece.wrapping_mul(2))
        ^ line.reverse_bits().wrapping_sub(piece.reverse_bits().wrapping_mul(2)).reverse_bits())&mask
}
/// Hyperbola Quintessence returns reachable squares through the first blocker.
/// Occupancy need not contain the source square (castling attack queries don't).
pub fn hq_attacks(square:u8,occupancy:u64,diagonal:bool)->u64{
    let rank=(square>>4)as i32;let file=(square&7)as i32;let piece=bit(square);
    let (a,b)=if diagonal{
        let d=rank-file;let e=rank+file-7;
        (if d>=0{0x8040201008040201u64.wrapping_shl((d*8)as u32)}else{0x8040201008040201u64.wrapping_shr((-d*8)as u32)},
         if e>=0{0x0102040810204080u64.wrapping_shl((e*8)as u32)}else{0x0102040810204080u64.wrapping_shr((-e*8)as u32)})
    }else{(0xffu64<<(rank*8),0x0101010101010101u64<<file)};
    hq_line(piece,occupancy,a)|hq_line(piece,occupancy,b)
}
fn mix(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9e3779b97f4a7c15);
    x = (x ^ (x >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94d049bb133111eb);
    x ^ (x >> 31)
}
fn piece_hash(s: u8, p: i8) -> u64 { mix(1 + s as u64 * 12 + (p.abs() - 1) as u64 + color(p) as u64 * 6) }
fn piece_score(s: u8, p: i8) -> i32 {
    let rank = if p > 0 { s >> 4 } else { 7 - (s >> 4) } as i32;
    let center = 6 - (2 * (s & 7) as i32 - 7).abs() - (2 * rank - 7).abs();
    let positional = match p.abs() {
        1 => 6 * rank + center,
        2 => 4 * center,
        3 => 2 * center,
        4 => rank,
        _ => 0,
    };
    p.signum() as i32 * (if p.abs() == 6 { 0 } else { VALUE[p.abs() as usize] } + positional)
}
pub fn square_name(s: u8) -> String { format!("{}{}", (b'a' + (s & 7)) as char, (b'1' + (s >> 4)) as char) }
pub fn square(s: &str) -> Option<u8> {
    square_bytes(s.as_bytes())
}
fn square_bytes(b:&[u8])->Option<u8>{
    if b.len() == 2 && (b'a'..=b'h').contains(&b[0]) && (b'1'..=b'8').contains(&b[1]) {
        Some((b[1] - b'1') * 16 + b[0] - b'a')
    } else { None }
}

impl Board {
    pub fn reuse_from(&mut self,source:&Self){*self=*source;}
    fn empty()->Self{Self{cells:[0;128],side:1,castle:0,ep:-1,halfmove:0,fullmove:1,hash:0,hist:History::new(),bb:[[0;7];2],king:[0;2],score:0}}
    pub fn start()->Self{
        let mut b=Self::empty();let back=[4,2,3,5,6,3,2,4];b.castle=15;
        for f in 0..8{b.cells[f]=back[f];b.cells[16+f]=1;b.cells[96+f]=-1;b.cells[112+f]=-back[f];}
        b.rebuild();b.hist.push(b.hash);b
    }
    pub fn from_fen(fen: &str) -> Result<Self, String> {
        let f: Vec<_> = fen.split_whitespace().collect();
        if f.len() != 6 { return Err("FEN needs six fields".into()); }
        let mut b = Self::empty();
        let ranks: Vec<_> = f[0].split('/').collect();
        if ranks.len() != 8 { return Err("FEN needs eight ranks".into()); }
        for (r, row) in ranks.iter().enumerate() {
            let mut file = 0usize;
            for ch in row.chars() {
                if ('1'..='8').contains(&ch) { file += ch as usize - '0' as usize; }
                else {
                    let p = match ch.to_ascii_lowercase() { 'p' => 1, 'n' => 2, 'b' => 3, 'r' => 4, 'q' => 5, 'k' => 6, _ => return Err("Invalid FEN piece".into()) };
                    if file >= 8 || p == 1 && (r == 0 || r == 7) { return Err("Invalid FEN placement".into()); }
                    b.cells[(7 - r) * 16 + file] = if ch.is_ascii_uppercase() { p } else { -p };
                    file += 1;
                }
                if file > 8 { return Err("FEN rank too long".into()); }
            }
            if file != 8 { return Err("FEN rank too short".into()); }
        }
        b.side = match f[1] { "w" => 1, "b" => -1, _ => return Err("Invalid FEN side".into()) };
        if f[2] != "-" {
            for c in f[2].chars() {
                let mask = match c { 'K' => 1, 'Q' => 2, 'k' => 4, 'q' => 8, _ => return Err("Invalid castling rights".into()) };
                if b.castle & mask != 0 { return Err("Duplicate castling rights".into()); }
                b.castle |= mask;
            }
        }
        if f[3] != "-" {
            b.ep = square(f[3]).ok_or("Invalid en passant square")? as i16;
            if b.ep >> 4 != if b.side > 0 { 5 } else { 2 } { return Err("Invalid en passant rank".into()); }
            if b.cells[b.ep as usize] != 0 || b.cells[(b.ep - 16 * b.side as i16) as usize] != -b.side {
                return Err("Invalid en passant occupancy".into());
            }
        }
        b.halfmove = f[4].parse().map_err(|_| "Invalid halfmove counter")?;
        b.fullmove = f[5].parse().map_err(|_| "Invalid fullmove counter")?;
        if b.fullmove == 0 { return Err("Fullmove counter starts at one".into()); }
        for p in [6, -6] { if b.cells.iter().filter(|&&x| x == p).count() != 1 { return Err("FEN needs one king per side".into()); } }
        for side in [-1,1]{if b.cells.iter().filter(|&&p|p*side>0).count()>16||b.cells.iter().filter(|&&p|p==side).count()>8{return Err("FEN exceeds chess piece inventory".into());}}
        for (mask, king, rook, side) in [(1, 4, 7, 1), (2, 4, 0, 1), (4, 116, 119, -1), (8, 116, 112, -1)] {
            if b.castle & mask != 0 && (b.cells[king] != 6 * side || b.cells[rook] != 4 * side) {
                return Err("Castling right requires original king and rook squares".into());
            }
        }
        b.rebuild();
        b.pseudo().map_err(str::to_owned)?;
        b.hist.push(b.hash);
        Ok(b)
    }
    pub fn rebuild(&mut self) {
        self.bb = [[0; 7]; 2]; self.hash = 0; self.score = 0;
        for s in 0..128u8 {
            if s & 0x88 != 0 { continue; }
            let p = self.cells[s as usize];
            if p != 0 {
                self.bb[color(p)][p.abs() as usize] |= bit(s);
                if p.abs() == 6 { self.king[color(p)] = s; }
                self.hash ^= piece_hash(s, p); self.score += piece_score(s, p);
            }
        }
        self.hash ^= self.meta_hash();
    }
    fn put(&mut self, s: u8, p: i8) {
        let old = self.cells[s as usize];
        if old != 0 {
            self.bb[color(old)][old.abs() as usize] ^= bit(s);
            self.hash ^= piece_hash(s, old); self.score -= piece_score(s, old);
        }
        self.cells[s as usize] = p;
        if p != 0 {
            self.bb[color(p)][p.abs() as usize] |= bit(s);
            if p.abs() == 6 { self.king[color(p)] = s; }
            self.hash ^= piece_hash(s, p); self.score += piece_score(s, p);
        }
    }
    fn meta_hash(&self) -> u64 {
        mix(2000 + self.castle as u64) ^ if self.side < 0 { mix(2100) } else { 0 }
            ^ if self.legal_ep() { mix(2200 + (self.ep & 7) as u64) } else { 0 }
    }
    // FIDE position identity counts an EP square only if a legal EP move exists.
    fn legal_ep(&self) -> bool {
        if !valid(self.ep) || self.cells[self.ep as usize] != 0 { return false; }
        let d = 16 * self.side as i16;
        let cap = self.ep - d;
        if !valid(cap) || self.cells[cap as usize] != -self.side { return false; }
        for from in [cap - 1, cap + 1] {
            if valid(from) && self.cells[from as usize] == self.side {
                let mut b = *self;
                b.put(from as u8, 0); b.put(cap as u8, 0); b.put(self.ep as u8, self.side);
                if !b.attacked(b.king[color(self.side)], -self.side) { return true; }
            }
        }
        false
    }
    fn leapers(&self,sq:u8,by:i8)->u64{
        let side = color(by); let mut result = 0; let mut mask = 0;
        for d in [15, 17] {
            let s = sq as i16 - by as i16 * d;
            if valid(s) { mask |= bit(s as u8); }
        }
        result |= mask & self.bb[side][1]; mask = 0;
        for d in KNIGHT { let s = sq as i16 + d; if valid(s) { mask |= bit(s as u8); } }
        result |= mask & self.bb[side][2]; mask = 0;
        for d in KING { let s = sq as i16 + d; if valid(s) { mask |= bit(s as u8); } }
        result |= mask & self.bb[side][6];
        result
    }
    // Returns geometric attackers, including pinned pieces (FIDE king safety).
    pub fn attackers(&self,sq:u8,by:i8)->u64{
        if HQ{self.attackers_hq(sq,by)}else{self.attackers_scalar(sq,by)}
    }
    pub fn attackers_hq(&self,sq:u8,by:i8)->u64{
        let side=color(by);let occupancy=self.bb.iter().flatten().fold(0,|all,&pieces|all|pieces);
        self.leapers(sq,by)
            |hq_attacks(sq,occupancy,true)&(self.bb[side][3]|self.bb[side][5])
            |hq_attacks(sq,occupancy,false)&(self.bb[side][4]|self.bb[side][5])
    }
    pub fn attackers_scalar(&self,sq:u8,by:i8)->u64{
        let side=color(by);let mut result=self.leapers(sq,by);
        for d in KING {
            let mut s = sq as i16 + d;
            while valid(s) {
                let p = self.cells[s as usize];
                if p != 0 {
                    let sliders = self.bb[side][5] | self.bb[side][if d.abs() == 1 || d.abs() == 16 { 4 } else { 3 }];
                    result |= bit(s as u8) & sliders;
                    break;
                }
                s += d;
            }
        }
        result
    }
    pub fn attacked(&self, sq: u8, by: i8) -> bool { self.attackers(sq, by) != 0 }
    pub fn in_check(&self) -> bool { self.attacked(self.king[color(self.side)], -self.side) }
    pub fn captured(&self, m: Move) -> i8 {
        if self.cells[m.from as usize].abs() == 1 && m.to as i16 == self.ep && self.cells[m.to as usize] == 0 && (m.from & 7) != (m.to & 7) { -self.side }
        else { self.cells[m.to as usize] }
    }
    pub fn is_capture(&self, m: Move) -> bool { self.captured(m) != 0 }
    pub fn play(&self, m: Move) -> Self {
        let mut b = *self; b.hash ^= b.meta_hash();
        let p = self.cells[m.from as usize]; let captured = self.captured(m);
        b.put(m.from, 0);
        if p.abs() == 1 && m.to as i16 == self.ep && captured != self.cells[m.to as usize] { b.put((m.to as i16 - 16 * self.side as i16) as u8, 0); }
        b.put(m.to, if m.promo == 0 { p } else { self.side * m.promo });
        if p.abs() == 6 {
            b.castle &= if p > 0 { !3 } else { !12 };
            if (m.to as i16 - m.from as i16).abs() == 2 {
                let (from, to) = if m.to > m.from { (m.from + 3, m.from + 1) } else { (m.from - 4, m.from - 1) };
                let rook = b.cells[from as usize]; b.put(from, 0); b.put(to, rook);
            }
        }
        for s in [m.from, m.to] { b.castle &= match s { 0 => !2, 7 => !1, 112 => !8, 119 => !4, _ => 255 }; }
        b.ep = if p.abs() == 1 && (m.to as i16 - m.from as i16).abs() == 32 { (m.to as i16 + m.from as i16) / 2 } else { -1 };
        b.halfmove = if p.abs() == 1 || captured != 0 { 0 } else { b.halfmove.saturating_add(1) };
        if b.halfmove == 0 { b.hist.clear(); }
        if self.side < 0 { b.fullmove = b.fullmove.saturating_add(1); }
        b.side = -b.side; b.hash ^= b.meta_hash(); b.hist.push(b.hash); b
    }
    fn push(moves: &mut MoveList, from: u8, to: u8, promote: bool)->Result<(),&'static str> {
        if promote { for promo in [5, 4, 3, 2] { moves.try_push(Move { from, to, promo })?; } }
        else { moves.try_push(Move { from, to, promo: 0 })?; }
        Ok(())
    }
    fn pseudo(&self) -> Result<MoveList,&'static str> {
        let mut moves = MoveList::new();
        for from in 0..128u8 {
            if from & 0x88 != 0 { continue; }
            let p = self.cells[from as usize]; if p * self.side <= 0 { continue; }
            if p.abs() == 1 {
                let d = 16 * self.side as i16; let to = from as i16 + d;
                let promote = to >> 4 == if self.side > 0 { 7 } else { 0 };
                if valid(to) && self.cells[to as usize] == 0 {
                    Self::push(&mut moves, from, to as u8, promote)?;
                    let two = to + d;
                    if from >> 4 == if self.side > 0 { 1 } else { 6 } && self.cells[two as usize] == 0 { Self::push(&mut moves, from, two as u8, false)?; }
                }
                for to in [to - 1, to + 1] {
                    if !valid(to) { continue; }
                    let t = self.cells[to as usize];
                    if t * self.side < 0 && t.abs() != 6 || to == self.ep && t == 0 && self.cells[(to - d) as usize] == -self.side {
                        Self::push(&mut moves, from, to as u8, promote)?;
                    }
                }
            } else {
                let dirs: &[i16] = match p.abs() { 2 => &KNIGHT, 3 => &KING[4..], 4 => &KING[..4], _ => &KING };
                for &d in dirs {
                    let mut to = from as i16 + d;
                    while valid(to) {
                        let t = self.cells[to as usize];
                        if t * self.side > 0 || t.abs() == 6 { break; }
                        Self::push(&mut moves, from, to as u8, false)?;
                        if t != 0 || p.abs() == 2 || p.abs() == 6 { break; }
                        to += d;
                    }
                }
                if p.abs() == 6 && from == if self.side > 0 { 4 } else { 116 } && !self.in_check() {
                    let shift = if self.side > 0 { 0 } else { 2 };
                    for (right, rook, steps) in [(1, from + 3, [1, 2, 0]), (2, from - 4, [-1, -2, -3])] {
                        if self.castle & (right << shift) == 0 || self.cells[rook as usize] != 4 * self.side { continue; }
                        if steps.iter().filter(|&&s| s != 0).all(|&s| self.cells[(from as i16 + s) as usize] == 0)
                            && !self.attacked((from as i16 + steps[0]) as u8, -self.side)
                            && !self.attacked((from as i16 + steps[1]) as u8, -self.side) {
                            Self::push(&mut moves, from, (from as i16 + steps[1]) as u8, false)?;
                        }
                    }
                }
            }
        }
        Ok(moves)
    }
    pub fn legal(&self) -> MoveList {
        let mut moves=self.pseudo().expect("admitted board exceeds move bound");
        moves.retain(|&m|{let b=self.play(m);!b.attacked(b.king[color(self.side)],-self.side)});
        moves
    }
    pub fn parse_move(&self, text: &str) -> Option<Move> {
        let b=text.as_bytes();if b.len()!=4&&b.len()!=5{return None;}
        let m=Move{from:square_bytes(&b[..2])?,to:square_bytes(&b[2..4])?,promo:if b.len()==4{0}else{match b[4]{b'n'=>2,b'b'=>3,b'r'=>4,b'q'=>5,_=>return None}}};
        self.legal().contains(&m).then_some(m)
    }
    pub fn perft(&self, depth: u32) -> u64 {
        if depth == 0 { 1 } else { self.legal().into_iter().map(|m| self.play(m).perft(depth - 1)).sum() }
    }
    pub fn evalwhite(&self) -> i32 { self.score }
    pub fn repeated(&self) -> bool {
        self.hist.iter().rev().take(self.halfmove as usize + 1).filter(|&&h| h == self.hash).count() >= 3
    }
    pub fn insufficient(&self) -> bool {
        if self.bb.iter().any(|s| s[1] | s[4] | s[5] != 0) { return false; }
        let knights = (self.bb[0][2] | self.bb[1][2]).count_ones();
        let bishops = self.bb[0][3] | self.bb[1][3];
        if knights + bishops.count_ones() <= 1 { return true; }
        if knights != 0 { return false; }
        let dark = 0xaa55aa55aa55aa55u64;
        bishops & dark == 0 || bishops & !dark == 0
    }
    // Exact optional-capture minimax on one square. Legal move filtering handles
    // pinned recapturers, king captures, promotions and EP occupancy correctly.
    pub fn see(&self, m: Move) -> i32 {
        self.see_with_abort(m,&||false).unwrap()
    }
    pub fn see_with_abort(&self,m:Move,abort:&impl Fn()->bool)->Option<i32>{
        if abort(){return None;}
        let gain = VALUE[self.captured(m).abs() as usize]
            + if m.promo != 0 { VALUE[m.promo as usize] - VALUE[1] } else { 0 };
        Some(gain-self.play(m).exchange(m.to,abort)?)
    }
    fn exchange(&self, target: u8,abort:&impl Fn()->bool) -> Option<i32> {
        if abort(){return None;}
        let mut attackers = self.attackers(target, self.side); let mut best = 0;
        while attackers != 0 {
            let n = attackers.trailing_zeros() as u8; attackers &= attackers - 1;
            let from = (n >> 3) * 16 + (n & 7);
            let promote = self.cells[from as usize].abs() == 1 && (target >> 4 == 0 || target >> 4 == 7);
            for promo in if promote { &[5, 4, 3, 2][..] } else { &[0][..] } {
                if abort(){return None;}
                let m = Move { from, to: target, promo: *promo }; let b = self.play(m);
                if !b.attacked(b.king[color(self.side)], -self.side) {
                    let gain = VALUE[self.cells[target as usize].abs() as usize]
                        + if *promo != 0 { VALUE[*promo as usize] - VALUE[1] } else { 0 };
                    best = best.max(gain - b.exchange(target,abort)?);
                }
            }
        }
        Some(best)
    }
    pub fn fen(&self) -> String {
        let mut s = String::new();
        for r in (0..8).rev() {
            let mut empty = 0;
            for f in 0..8 {
                let p = self.cells[r * 16 + f];
                if p == 0 { empty += 1; }
                else {
                    if empty != 0 { s.push((b'0' + empty) as char); empty = 0; }
                    let c = b" pnbrqk"[p.abs() as usize] as char;
                    s.push(if p > 0 { c.to_ascii_uppercase() } else { c });
                }
            }
            if empty != 0 { s.push((b'0' + empty) as char); }
            if r != 0 { s.push('/'); }
        }
        s.push_str(if self.side > 0 { " w " } else { " b " });
        if self.castle == 0 { s.push('-'); } else { for (c, m) in [('K', 1), ('Q', 2), ('k', 4), ('q', 8)] { if self.castle & m != 0 { s.push(c); } } }
        format!("{} {} {} {}", s, if self.ep < 0 { "-".into() } else { square_name(self.ep as u8) }, self.halfmove, self.fullmove)
    }
}

#[cfg(test)]
#[path = "../tests/rust/board.rs"]
mod tests;
