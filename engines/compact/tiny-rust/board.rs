// Independent Tiny A: the mailbox is the only board representation.
pub type Move = u32;
pub const fn from(m: Move) -> usize { (m & 127) as usize }
pub const fn to(m: Move) -> usize { ((m >> 7) & 127) as usize }
pub const fn promo(m: Move) -> i8 { ((m >> 14) & 7) as i8 }
fn mv(f: usize, t: usize, p: i8) -> Move { f as Move | (t as Move) << 7 | (p as Move) << 14 }
fn valid(s: i16) -> bool { s >= 0 && s < 128 && s & 0x88 == 0 }
fn color(p: i8) -> usize { (p < 0) as usize }
const RAYS: [i16; 8] = [1, -1, 16, -16, 17, 15, -15, -17];
const JUMPS: [i16; 8] = [33, 31, 18, 14, -14, -18, -31, -33];

pub struct Moves { pub a: [Move; 512], pub n: usize }
impl Moves {
    fn new() -> Self { Self { a: [0; 512], n: 0 } }
    fn push(&mut self, f: usize, t: usize, promotion: bool) {
        for p in if promotion { 2..6 } else { 0..1 } {
            // Admission has <=16 pieces/side, each with <=27 pseudo moves.
            assert!(self.n < 512, "admitted board exceeds move bound");
            self.a[self.n] = mv(f, t, p); self.n += 1;
        }
    }
}

#[derive(Clone, Copy)]
pub struct Board {
    pub cells: [i8; 128],
    pub side: i8,
    pub castle: u8,
    pub ep: i16,
    pub king: [u8; 2],
    pub halfmove: u16,
    pub hash: u64,
    pub context: u64,
    pub score: i32,
}

pub fn mix(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9e3779b97f4a7c15);
    x = (x ^ (x >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94d049bb133111eb);
    x ^ (x >> 31)
}
pub fn value(p: i8, square: usize) -> i32 {
    let a = p.abs() as usize;
    let rank = (square >> 4) as i32;
    let advance = if p > 0 { rank } else { 7 - rank };
    let center = 7 - (2 * (square & 7) as i32 - 7).abs() - (2 * rank - 7).abs();
    let positional = match a {
        1 => advance * 7 + center * 2, 2 => center * 9,
        3 => center * 5, 4 => advance * 2, 5 => center * 2,
        6 => -center * 3, _ => 0,
    };
    p.signum() as i32 * ([0, 100, 320, 330, 500, 900, 0][a] + positional)
}
fn piece(p: i8, square: usize) -> u64 { mix((square as i32 + (p as i32 + 6) * 128) as u64) }
fn rights(s: usize) -> u8 {
    match s { 4 => 3, 116 => 12, 0 => 2, 7 => 1, 112 => 8, 119 => 4, _ => 0 }
}

impl Board {
    pub fn empty() -> Self {
        Self { cells: [0; 128], side: 1, castle: 0, ep: -1, king: [0; 2],
            halfmove: 0, hash: 0, context: 0, score: 0 }
    }
    pub fn start() -> Self {
        let mut b = Self::empty(); b.castle = 15;
        let back = [4, 2, 3, 5, 6, 3, 2, 4];
        for f in 0..8 {
            b.cells[f] = back[f]; b.cells[f + 16] = 1;
            b.cells[f + 96] = -1; b.cells[f + 112] = -back[f];
        }
        b.rebuild(); b
    }
    pub fn rebuild(&mut self) {
        self.hash = 0; self.score = 0; self.king = [0; 2];
        for s in 0..128 {
            let p = self.cells[s];
            if s & 0x88 == 0 && p != 0 {
                self.hash ^= piece(p, s); self.score += value(p, s);
                if p.abs() == 6 { self.king[color(p)] = s as u8; }
            }
        }
        self.canonical_ep(); self.hash ^= self.state(); self.context = self.hash;
    }
    fn put(&mut self, s: usize, p: i8) {
        let old = self.cells[s];
        if old != 0 { self.hash ^= piece(old, s); self.score -= value(old, s); }
        self.cells[s] = p;
        if p != 0 {
            self.hash ^= piece(p, s); self.score += value(p, s);
            if p.abs() == 6 { self.king[color(p)] = s as u8; }
        }
    }
    fn state(&self) -> u64 {
        mix(2048 + self.castle as u64) ^ if self.side < 0 { mix(2064) } else { 0 }
            ^ if self.ep < 0 { 0 } else { mix(2065 + (self.ep & 7) as u64) }
    }
    pub fn attacked(&self, square: u8, side: i8) -> bool {
        let sq = square as i16;
        for d in [-1, 1] {
            let q = sq - side as i16 * 16 + d;
            if valid(q) && self.cells[q as usize] == side { return true; }
        }
        for d in JUMPS {
            let q = sq + d;
            if valid(q) && self.cells[q as usize] == side * 2 { return true; }
        }
        for (i, d) in RAYS.iter().enumerate() {
            let mut q = sq + d; let mut adjacent = true;
            while valid(q) {
                let p = self.cells[q as usize];
                if p != 0 {
                    if p * side > 0 && (p.abs() == 5 || p.abs() == if i < 4 { 4 } else { 3 }
                        || adjacent && p.abs() == 6) { return true; }
                    break;
                }
                q += d; adjacent = false;
            }
        }
        false
    }
    pub fn in_check(&self) -> bool { self.attacked(self.king[color(self.side)], -self.side) }
    // Only a legal EP capture contributes to FIDE position identity.
    fn canonical_ep(&mut self) {
        if valid(self.ep) && self.ep >> 4 == if self.side > 0 { 5 } else { 2 }
            && self.cells[self.ep as usize] == 0 {
            let cap = self.ep - self.side as i16 * 16;
            if self.cells[cap as usize] == -self.side {
                for q in [cap - 1, cap + 1] {
                    if valid(q) && self.cells[q as usize] == self.side {
                        let mut t = *self;
                        t.cells[q as usize] = 0; t.cells[cap as usize] = 0;
                        t.cells[self.ep as usize] = self.side;
                        if !t.in_check() { return; }
                    }
                }
            }
        }
        self.ep = -1;
    }
    pub fn captured(&self, m: Move) -> i8 {
        let p = self.cells[to(m)];
        if p == 0 && self.cells[from(m)].abs() == 1 && to(m) as i16 == self.ep { -self.side }
        else { p }
    }
    pub fn capture(&self, m: Move) -> bool { self.captured(m) != 0 }
    // Geometry belongs to pseudo(). Public text is matched against that list.
    pub fn play(&self, m: Move) -> Option<Self> {
        let f = from(m); let t = to(m); let promotion = promo(m); let s = self.side;
        if (f | t) & 0x88 != 0 { return None; }
        let mut p = self.cells[f]; let target = self.cells[t];
        if p * s <= 0 || target * s > 0 || target.abs() == 6 { return None; }
        let mut b = *self; b.hash ^= self.state(); b.ep = -1;
        b.halfmove = self.halfmove.saturating_add(1);
        if p.abs() == 1 {
            b.halfmove = 0;
            if t as i16 == self.ep && target == 0 {
                let cap = t as i16 - s as i16 * 16;
                if !valid(cap) || self.cells[cap as usize] != -s { return None; }
                b.put(cap as usize, 0);
            }
            if (t as i16 - f as i16).abs() == 32 { b.ep = f as i16 + s as i16 * 16; }
            if t >> 4 == 0 || t >> 4 == 7 {
                if !(2..=5).contains(&promotion) { return None; }
                p = s * promotion;
            } else if promotion != 0 { return None; }
        } else if promotion != 0 { return None; }
        if target != 0 { b.halfmove = 0; }
        if p.abs() == 6 {
            b.castle &= if s > 0 { !3 } else { !12 };
            if (t as i16 - f as i16).abs() == 2 {
                let home = if s > 0 { 4 } else { 116 };
                if f != home { return None; }
                let shift = if s > 0 { 0 } else { 2 };
                let (rook, transit, right) = if t > f { (f + 3, f + 1, 1) } else { (f - 4, f - 1, 2) };
                if self.castle & (right << shift) == 0 || self.cells[rook] != s * 4
                    || self.in_check() || self.attacked(transit as u8, -s) { return None; }
                b.put(rook, 0); b.put(transit, s * 4);
            }
        }
        b.put(f, 0); b.put(t, p); b.castle &= !(rights(f) | rights(t)); b.side = -s;
        if b.attacked(b.king[color(s)], -s) { return None; }
        b.canonical_ep(); b.hash ^= b.state();
        b.context = if b.halfmove == 0 { b.hash } else { mix(self.context ^ b.hash) };
        Some(b)
    }
    pub fn pseudo(&self) -> Moves {
        let mut moves = Moves::new(); let s = self.side;
        for f in 0..128 {
            if f & 0x88 != 0 { continue; }
            let p = self.cells[f]; let a = p.abs();
            if p * s <= 0 { continue; }
            if a == 1 {
                let t = f as i16 + s as i16 * 16;
                if valid(t) && self.cells[t as usize] == 0 {
                    let promotion = t >> 4 == 0 || t >> 4 == 7;
                    moves.push(f, t as usize, promotion);
                    if f >> 4 == if s > 0 { 1 } else { 6 }
                        && self.cells[(t + s as i16 * 16) as usize] == 0 {
                        moves.push(f, (t + s as i16 * 16) as usize, false);
                    }
                }
                for t in [t - 1, t + 1] {
                    if valid(t) {
                        let target = self.cells[t as usize];
                        if target * s < 0 && target.abs() != 6 || t == self.ep {
                            moves.push(f, t as usize, t >> 4 == 0 || t >> 4 == 7);
                        }
                    }
                }
            } else {
                let dirs: &[i16] = if a == 2 { &JUMPS } else if a == 3 { &RAYS[4..] }
                    else if a == 4 { &RAYS[..4] } else { &RAYS };
                for &d in dirs {
                    let mut t = f as i16 + d;
                    while valid(t) {
                        let target = self.cells[t as usize];
                        if target * s > 0 || target.abs() == 6 { break; }
                        moves.push(f, t as usize, false);
                        if target != 0 || a == 2 || a == 6 { break; }
                        t += d;
                    }
                }
                let home = if s > 0 { 4 } else { 116 };
                if a == 6 && f == home && !self.in_check() {
                    let shift = if s > 0 { 0 } else { 2 };
                    for (right, rook, d) in [(1, home + 3, 1i16), (2, home - 4, -1)] {
                        if self.castle & (right << shift) != 0 && self.cells[rook] == s * 4
                            && self.cells[(home as i16 + d) as usize] == 0
                            && self.cells[(home as i16 + d * 2) as usize] == 0
                            && (d > 0 || self.cells[home - 3] == 0)
                            && !self.attacked((home as i16 + d) as u8, -s) {
                            moves.push(f, (home as i16 + d * 2) as usize, false);
                        }
                    }
                }
            }
        }
        moves
    }
    pub fn legal(&self) -> Moves {
        let mut moves = self.pseudo(); let mut n = 0;
        for i in 0..moves.n {
            if self.play(moves.a[i]).is_some() { moves.a[n] = moves.a[i]; n += 1; }
        }
        moves.n = n; moves
    }
    pub fn parse(&self, text: &str) -> Option<Move> {
        let b = text.as_bytes();
        if b.len() != 4 && b.len() != 5 { return None; }
        for i in [0, 2] {
            if !(b'a'..=b'h').contains(&b[i]) || !(b'1'..=b'8').contains(&b[i + 1]) { return None; }
        }
        let p = if b.len() == 4 { 0 } else {
            match b[4] { b'n' => 2, b'b' => 3, b'r' => 4, b'q' => 5, _ => return None }
        };
        let m = mv((b[1] - b'1') as usize * 16 + (b[0] - b'a') as usize,
            (b[3] - b'1') as usize * 16 + (b[2] - b'a') as usize, p);
        let moves = self.pseudo();
        (moves.a[..moves.n].contains(&m) && self.play(m).is_some()).then_some(m)
    }
    pub fn dead(&self) -> bool {
        let mut minors = 0; let mut knights = 0; let mut colors = 0;
        for q in 0..128 {
            if q & 0x88 != 0 { continue; }
            match self.cells[q].abs() {
                2 => { minors += 1; knights += 1; }
                3 => { minors += 1; colors |= 1 << ((q + (q >> 4)) & 1); }
                1 | 4 | 5 => return false, _ => (),
            }
        }
        minors < 2 || knights == 0 && colors != 3
    }
}

pub fn uci(m: Move) -> String {
    if m == 0 { return "0000".into(); }
    let mut s = String::with_capacity(5);
    for q in [from(m), to(m)] {
        s.push((b'a' + (q & 7) as u8) as char); s.push((b'1' + (q >> 4) as u8) as char);
    }
    if promo(m) != 0 { s.push(b"  nbrq"[promo(m) as usize] as char); }
    s
}
