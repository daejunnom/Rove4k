// Independent chess rules: 0x88 move geometry, incremental piece bitboards.
pub const VALUE: [i32; 7] = [0, 100, 320, 330, 500, 900, 20000];
const KNIGHT: [i16; 8] = [33, 31, 18, 14, -14, -18, -31, -33];
const KING: [i16; 8] = [1, -1, 16, -16, 17, 15, -15, -17];

#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
pub struct Move { pub from: u8, pub to: u8, pub promo: i8 }
impl Move {
    pub fn uci(self) -> String {
        let mut s = format!("{}{}", square_name(self.from), square_name(self.to));
        if self.promo != 0 { s.push(b"  nbrqk"[self.promo as usize] as char); }
        s
    }
}

#[derive(Clone, Debug)]
pub struct Board {
    pub cells: [i8; 128],
    pub side: i8,
    pub castle: u8,
    pub ep: i16,
    pub halfmove: u16,
    pub fullmove: u16,
    pub hash: u64,
    pub hist: Vec<u64>,
    pub bb: [[u64; 7]; 2],
    pub king: [u8; 2],
    score: i32,
}

fn color(p: i8) -> usize { (p < 0) as usize }
fn valid(s: i16) -> bool { s >= 0 && s < 128 && s & 0x88 == 0 }
fn bit(s: u8) -> u64 { 1 << ((s >> 4) * 8 + (s & 7)) }
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
    let b = s.as_bytes();
    if b.len() == 2 && (b'a'..=b'h').contains(&b[0]) && (b'1'..=b'8').contains(&b[1]) {
        Some((b[1] - b'1') * 16 + b[0] - b'a')
    } else { None }
}

impl Board {
    pub fn start() -> Self { Self::from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1").unwrap() }
    pub fn from_fen(fen: &str) -> Result<Self, String> {
        let f: Vec<_> = fen.split_whitespace().collect();
        if f.len() != 6 { return Err("FEN needs six fields".into()); }
        let mut b = Self { cells: [0; 128], side: 1, castle: 0, ep: -1, halfmove: 0,
            fullmove: 1, hash: 0, hist: Vec::new(), bb: [[0; 7]; 2], king: [0; 2], score: 0 };
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
        for (mask, king, rook, side) in [(1, 4, 7, 1), (2, 4, 0, 1), (4, 116, 119, -1), (8, 116, 112, -1)] {
            if b.castle & mask != 0 && (b.cells[king] != 6 * side || b.cells[rook] != 4 * side) {
                return Err("Castling right requires original king and rook squares".into());
            }
        }
        b.rebuild();
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
                let mut b = self.clone();
                b.put(from as u8, 0); b.put(cap as u8, 0); b.put(self.ep as u8, self.side);
                if !b.attacked(b.king[color(self.side)], -self.side) { return true; }
            }
        }
        false
    }
    // Returns a bitboard of all attackers, including pinned geometric attackers.
    pub fn attackers(&self, sq: u8, by: i8) -> u64 {
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
        let mut b = self.clone(); b.hash ^= b.meta_hash();
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
        if self.side < 0 { b.fullmove = b.fullmove.saturating_add(1); }
        b.side = -b.side; b.hash ^= b.meta_hash(); b.hist.push(b.hash); b
    }
    fn push(moves: &mut Vec<Move>, from: u8, to: u8, promote: bool) {
        if promote { for promo in [5, 4, 3, 2] { moves.push(Move { from, to, promo }); } }
        else { moves.push(Move { from, to, promo: 0 }); }
    }
    fn pseudo(&self) -> Vec<Move> {
        let mut moves = Vec::with_capacity(64);
        for from in 0..128u8 {
            if from & 0x88 != 0 { continue; }
            let p = self.cells[from as usize]; if p * self.side <= 0 { continue; }
            if p.abs() == 1 {
                let d = 16 * self.side as i16; let to = from as i16 + d;
                let promote = to >> 4 == if self.side > 0 { 7 } else { 0 };
                if valid(to) && self.cells[to as usize] == 0 {
                    Self::push(&mut moves, from, to as u8, promote);
                    let two = to + d;
                    if from >> 4 == if self.side > 0 { 1 } else { 6 } && self.cells[two as usize] == 0 { Self::push(&mut moves, from, two as u8, false); }
                }
                for to in [to - 1, to + 1] {
                    if !valid(to) { continue; }
                    let t = self.cells[to as usize];
                    if t * self.side < 0 && t.abs() != 6 || to == self.ep && t == 0 && self.cells[(to - d) as usize] == -self.side {
                        Self::push(&mut moves, from, to as u8, promote);
                    }
                }
            } else {
                let dirs: &[i16] = match p.abs() { 2 => &KNIGHT, 3 => &KING[4..], 4 => &KING[..4], _ => &KING };
                for &d in dirs {
                    let mut to = from as i16 + d;
                    while valid(to) {
                        let t = self.cells[to as usize];
                        if t * self.side > 0 || t.abs() == 6 { break; }
                        Self::push(&mut moves, from, to as u8, false);
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
                            Self::push(&mut moves, from, (from as i16 + steps[1]) as u8, false);
                        }
                    }
                }
            }
        }
        moves
    }
    pub fn legal(&self) -> Vec<Move> {
        self.pseudo().into_iter().filter(|&m| {
            let b = self.play(m); !b.attacked(b.king[color(self.side)], -self.side)
        }).collect()
    }
    pub fn parse_move(&self, text: &str) -> Option<Move> {
        self.legal().into_iter().find(|m| m.uci() == text)
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
        let gain = VALUE[self.captured(m).abs() as usize]
            + if m.promo != 0 { VALUE[m.promo as usize] - VALUE[1] } else { 0 };
        gain - self.play(m).exchange(m.to)
    }
    fn exchange(&self, target: u8) -> i32 {
        let mut attackers = self.attackers(target, self.side); let mut best = 0;
        while attackers != 0 {
            let n = attackers.trailing_zeros() as u8; attackers &= attackers - 1;
            let from = (n >> 3) * 16 + (n & 7);
            let promote = self.cells[from as usize].abs() == 1 && (target >> 4 == 0 || target >> 4 == 7);
            for promo in if promote { &[5, 4, 3, 2][..] } else { &[0][..] } {
                let m = Move { from, to: target, promo: *promo }; let b = self.play(m);
                if !b.attacked(b.king[color(self.side)], -self.side) {
                    let gain = VALUE[self.cells[target as usize].abs() as usize]
                        + if *promo != 0 { VALUE[*promo as usize] - VALUE[1] } else { 0 };
                    best = best.max(gain - b.exchange(target));
                }
            }
        }
        best
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
mod tests {
    use super::*;
    fn b(s: &str) -> Board { Board::from_fen(s).unwrap() }
    #[test] fn initial_and_kiwipete_perft() {
        let start = Board::start(); assert_eq!(start.perft(1), 20); assert_eq!(start.perft(2), 400); assert_eq!(start.perft(3), 8902); assert_eq!(start.perft(4), 197281);
        let kiwi = b("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1");
        assert_eq!(kiwi.perft(1), 48); assert_eq!(kiwi.perft(2), 2039); assert_eq!(kiwi.perft(3), 97862);
    }
    #[test] fn ep_identity_and_discovered_check() {
        let f = "7k/8/8/r4pPK/8/8/8/8 w - f6 0 1";
        let pos = b(f); assert!(pos.parse_move("g5f6").is_none());
        assert_eq!(pos.hash, b(&f.replace(" f6 ", " - ")).hash);
        let f = "6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 2";
        let pos = b(f); assert_eq!(pos.perft(1), 7); assert!(pos.parse_move("e5d6").is_some());
        assert_ne!(pos.hash, b(&f.replace(" d6 ", " - ")).hash);
        let pos = b("k3r3/8/8/2PpP3/8/8/8/4K3 w - d6 0 1");
        assert!(pos.parse_move("c5d6").is_some()); assert!(pos.parse_move("e5d6").is_none()); assert_eq!(pos.perft(1), 8);
        assert_ne!(pos.hash, b(&pos.fen().replace(" d6 ", " - ")).hash);
        let pos = b("6k1/8/8/3pP3/4K3/8/8/8 w - d6 0 1");
        assert!(pos.in_check()); assert!(pos.parse_move("e5d6").is_some()); assert!(pos.parse_move("e5e6").is_none());
    }
    #[test] fn promotions_castling_and_incremental_state() {
        let p = b("1r6/P6k/8/8/8/8/8/7K w - - 0 1"); assert_eq!(p.perft(1), 11);
        for suffix in ["q", "r", "b", "n"] { assert!(p.parse_move(&format!("a7b8{}", suffix)).is_some()); }
        let mut p = b("4k3/8/8/8/8/8/8/4K3 w - - 0 1"); p.castle = 3; p.rebuild();
        assert!(p.parse_move("e1g1").is_none()); assert!(p.parse_move("e1c1").is_none());
        let p = b("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 27 19");
        let p = p.play(p.parse_move("e1c1").unwrap());
        assert_eq!(p.cells[3], 4); assert_eq!(p.cells[0], 0); assert_eq!(p.castle, 12); assert_eq!(p.halfmove, 28); assert_eq!(p.fullmove, 19);
        let mut q = p.clone(); q.rebuild(); assert_eq!(p.hash, q.hash); assert_eq!(p.bb, q.bb); assert_eq!(p.score, q.score);
        assert_eq!(b(&p.fen()).fen(), p.fen());
        let p = b("4kr2/8/8/8/8/8/8/4K2R w K - 0 1"); assert!(p.parse_move("e1g1").is_none());
        let p = b("1r2k3/8/8/8/8/8/8/R3K3 w Q - 0 1"); assert!(p.parse_move("e1c1").is_some());
        let p = b("4r3/8/8/8/8/3k4/4R3/4K3 b - - 0 1"); assert!(p.parse_move("d3c2").is_none());
        for p in [Board::start(), b("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1")] {
            for m in p.legal() {
                let q = p.play(m); let mut rebuilt = q.clone(); rebuilt.rebuild();
                assert_eq!(q.hash, rebuilt.hash); assert_eq!(q.bb, rebuilt.bb); assert_eq!(q.score, rebuilt.score);
            }
        }
    }
    #[test] fn repetition_and_clocks() {
        let mut p = Board::start();
        for (i, uci) in ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"].iter().enumerate() {
            p = p.play(p.parse_move(uci).unwrap()); assert_eq!(p.repeated(), i == 7);
            let q = b(&p.fen()); assert_eq!(p.hash, q.hash); assert_eq!(p.bb, q.bb); assert_eq!(p.score, q.score);
        }
        assert_eq!(p.halfmove, 8); assert_eq!(p.fullmove, 5);
        p = p.play(p.parse_move("e2e4").unwrap()); assert_eq!(p.halfmove, 0); assert_eq!(p.ep, 36);
    }
    #[test] fn see_handles_pins_king_safety_ep_and_promotion() {
        let p = b("4k3/4n3/5p2/8/8/2B5/8/K3R3 w - - 0 1");
        assert_eq!(p.see(p.parse_move("c3f6").unwrap()), 100); // e7 knight is pinned.
        let p = b("8/8/4k3/3p4/2P5/8/8/K2R4 w - - 0 1");
        assert_eq!(p.see(p.parse_move("c4d5").unwrap()), 100); // King cannot take a rook-protected pawn.
        let p = b("6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 2"); assert_eq!(p.see(p.parse_move("e5d6").unwrap()), 100);
        let p = b("7k/P7/8/8/8/8/8/K7 w - - 0 1"); assert_eq!(p.see(p.parse_move("a7a8q").unwrap()), 800);
    }
    #[test] fn terminal_rules_and_fen_validation() {
        let mate = b("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"); assert!(mate.in_check()); assert!(mate.legal().is_empty());
        let stale = b("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"); assert!(!stale.in_check()); assert!(stale.legal().is_empty());
        assert!(b("7k/8/8/8/8/8/8/K7 w - - 0 1").insufficient());
        assert!(Board::from_fen("8/8/8/8/8/8/8/8 w - - 0 1").is_err());
        assert!(Board::from_fen("7k/8/8/8/8/8/8/K7 w - a4 0 1").is_err());
        for fen in [
            "4k3/8/8/8/8/8/8/4K3 w KQ - 0 1", // Missing castling rooks.
            "r2k3r/8/8/8/8/8/8/4K3 b kq - 0 1", // King moved.
            "4k3/8/8/8/8/8/8/R3K2r w K - 0 1", // Wrong-color rook.
            "7k/8/8/4P3/8/8/8/K7 w - d6 0 1", // Missing EP victim.
            "7k/8/3N4/3pP3/8/8/8/K7 w - d6 0 1", // Occupied EP destination.
            "7k/8/8/8/3Pp3/3n4/8/K7 b - d3 0 1", // Black EP destination occupied.
            "7k/8/8/8/4p3/8/8/K7 b - d3 0 1", // Black EP victim missing.
        ] { assert!(Board::from_fen(fen).is_err(), "{}", fen); }
    }
}
