//! External std qualification image. This is never a shipping engine source.
#![allow(dead_code)]
#[path = "../board.rs"] mod board;
use board::{Board, Move, from, to, promo};
use std::fmt::Write as FormatWrite;
use std::io::{self, BufRead, Write};

pub const HQ: bool = cfg!(board_test_hq);

fn square(text: &[u8]) -> Option<usize> {
    if text.len() != 2 || !(b'a'..=b'h').contains(&text[0]) || !(b'1'..=b'8').contains(&text[1]) { return None; }
    Some((text[1] - b'1') as usize * 16 + (text[0] - b'a') as usize)
}
fn fen(text: &str) -> Option<Board> {
    let f: Vec<_> = text.split_whitespace().collect();
    if f.len() != 6 { return None; }
    let ranks: Vec<_> = f[0].split('/').collect();
    if ranks.len() != 8 { return None; }
    let mut b = Board::empty(); let mut kings = [0; 2]; let mut counts = [0; 2];
    for (row, data) in ranks.iter().enumerate() {
        let mut file = 0;
        for c in data.bytes() {
            if (b'1'..=b'8').contains(&c) { file += (c - b'0') as usize; }
            else {
                let p = match c.to_ascii_lowercase() { b'p' => 1, b'n' => 2, b'b' => 3, b'r' => 4, b'q' => 5, b'k' => 6, _ => return None };
                if file >= 8 || p == 1 && (row == 0 || row == 7) { return None; }
                let side = usize::from(c.is_ascii_lowercase());
                kings[side] += usize::from(p == 6); counts[side] += 1;
                b.cells[(7 - row) * 16 + file] = if side == 0 { p } else { -p }; file += 1;
            }
            if file > 8 { return None; }
        }
        if file != 8 { return None; }
    }
    if kings != [1, 1] || counts.iter().any(|&n| n > 16) { return None; }
    b.side = match f[1] { "w" => 1, "b" => -1, _ => return None };
    if f[2] != "-" {
        for c in f[2].bytes() {
            let mask = match c { b'K' => 1, b'Q' => 2, b'k' => 4, b'q' => 8, _ => return None };
            if b.castle & mask != 0 { return None; } b.castle |= mask;
        }
    }
    b.ep = if f[3] == "-" { -1 } else { square(f[3].as_bytes())? as i16 };
    b.halfmove = f[4].parse().ok()?;
    if f[5].parse::<u32>().ok()? == 0 { return None; }
    b.rebuild(); Some(b)
}
fn text(m: Move) -> String {
    let mut s = String::new();
    for q in [from(m), to(m)] { s.push((b'a' + (q & 7) as u8) as char); s.push((b'1' + (q >> 4) as u8) as char); }
    if promo(m) != 0 { s.push(b"  nbrq"[promo(m) as usize] as char); } s
}
fn state(b: &Board, output: &mut String, attacks: bool) {
    let mut cells = String::new();
    for q in 0..64 {
        let p = b.cells[q / 8 * 16 + q % 8]; let c = b".pnbrqk"[p.unsigned_abs() as usize];
        cells.push(if p > 0 { c.to_ascii_uppercase() as char } else { c as char });
    }
    let mut rebuilt = *b; rebuilt.rebuild();
    let coherent = b.cells == rebuilt.cells && b.side == rebuilt.side && b.castle == rebuilt.castle
        && b.ep == rebuilt.ep && b.halfmove == rebuilt.halfmove && b.king == rebuilt.king
        && b.hash == rebuilt.hash && b.score == rebuilt.score && b.bb == rebuilt.bb;
    write!(output,"{{\"cells\":\"{cells}\",\"side\":{},\"castle\":{},\"ep\":{},\"halfmove\":{},\"king\":{:?},\"hash\":\"{:016x}\",\"context\":\"{:016x}\",\"score\":{},\"bb\":{:?},\"check\":{},\"dead\":{},\"rebuild_coherent\":{}",
        b.side,b.castle,b.ep,b.halfmove,b.king,b.hash,b.context,b.score,b.bb,b.in_check(),b.dead(),coherent).unwrap();
    if attacks {
        let mut scalar = [0u64; 2]; let mut hq = [0u64; 2];
        for q in 0..64 {
            let sq = (q / 8 * 16 + q % 8) as u8;
            for (i, side) in [1, -1].iter().copied().enumerate() {
                scalar[i] |= u64::from(b.attacked_scalar(sq, side)) << q;
                hq[i] |= u64::from(b.attacked_hq(sq, side)) << q;
            }
        }
        write!(output,",\"attacked_scalar\":[\"{:016x}\",\"{:016x}\"],\"attacked_hq\":[\"{:016x}\",\"{:016x}\"]",scalar[0],scalar[1],hq[0],hq[1]).unwrap();
    }
    output.push('}');
}
fn perft(b: &Board, depth: u32) -> u64 {
    if depth == 0 { return 1; }
    let moves = b.pseudo(); let mut n = 0;
    for &m in &moves.a[..moves.n] { if let Some(child) = b.play(m) { n += perft(&child, depth - 1); } }
    n
}
// Independent 64-coordinate rays; no 0x88 offsets or HQ formula are reused.
fn ray(square: u8, occupancy: u64, diagonal: bool) -> u64 {
    let x = (square & 7) as i32; let y = (square >> 4) as i32; let mut result = 0;
    let dirs = if diagonal { [(1,1),(-1,1),(1,-1),(-1,-1)] } else { [(1,0),(-1,0),(0,1),(0,-1)] };
    for (dx,dy) in dirs {
        let (mut nx,mut ny) = (x + dx,y + dy);
        while (0..8).contains(&nx) && (0..8).contains(&ny) {
            let p = 1u64 << (ny * 8 + nx); result |= p;
            if occupancy & p != 0 { break; } nx += dx; ny += dy;
        }
    }
    result
}
fn next(seed: &mut u64) -> u64 { *seed ^= *seed << 13; *seed ^= *seed >> 7; *seed ^= *seed << 17; *seed }
fn hq_check(mut seed: u64, count: usize) -> u64 {
    let mut tested = 0;
    for q in 0..64 {
        let sq = (q / 8 * 16 + q % 8) as u8; let source = 1u64 << q;
        for diagonal in [false,true] {
            for i in 0..count + 68 {
                let occupancy = match i { 0 => 0, 1 => u64::MAX, 2 => 0xaa55aa55aa55aa55, 3 => 0xff818181818181ff, 4..=67 => 1u64 << (i-4), _ => next(&mut seed) };
                for occupied in [occupancy & !source,occupancy | source] {
                    assert_eq!(board::hq_attacks(sq,occupied,diagonal),ray(sq,occupied,diagonal),"HQ square={sq} occupancy={occupied:016x} diagonal={diagonal}"); tested += 1;
                }
            }
        }
    }
    tested
}
fn main() {
    let stdin = io::stdin(); let mut out = io::BufWriter::new(io::stdout().lock());
    for line in stdin.lock().lines() {
        let line = line.unwrap(); let f: Vec<_> = line.split('\t').collect(); let mut output = String::new();
        match f[0] {
            "hq" => { let n = hq_check(f[1].parse().unwrap(),f[2].parse().unwrap()); write!(output,"{{\"kind\":\"hq\",\"cases\":{n}}}").unwrap(); }
            "perft" => { let b = fen(f[2]).unwrap(); let n = perft(&b,f[3].parse().unwrap()); write!(output,"{{\"kind\":\"perft\",\"id\":\"{}\",\"nodes\":{n}}}",f[1]).unwrap(); }
            "probe" => {
                let mut b = fen(f[2]).unwrap(); let mut keys = vec![b.hash];
                if f.len() > 3 { for name in f[3].split_whitespace() { b = b.play(b.parse(name).unwrap()).unwrap(); keys.push(b.hash); } }
                write!(output,"{{\"kind\":\"probe\",\"id\":\"{}\",\"repetition\":{},\"position\":",f[1],keys.iter().filter(|&&key|key==b.hash).count()).unwrap();
                state(&b,&mut output,true); output.push_str(",\"legal\":[");
                let moves = b.legal(); let mut legal: Vec<_> = moves.a[..moves.n].iter().map(|&m|(text(m),m)).collect(); legal.sort();
                for (i,(name,m)) in legal.iter().enumerate() {
                    if i != 0 { output.push(','); } write!(output,"{{\"move\":\"{name}\",\"capture\":{},\"state\":",b.capture(*m)).unwrap();
                    state(&b.play(*m).unwrap(),&mut output,false); output.push('}');
                }
                output.push_str("]}");
            }
            _ => panic!("unknown development driver command"),
        }
        writeln!(out,"{output}").unwrap(); out.flush().unwrap();
    }
}
