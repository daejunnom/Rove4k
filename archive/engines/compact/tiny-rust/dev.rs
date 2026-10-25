//! Development admission and diagnostics. This file is absent from shipping.
use crate::board::{Board, uci};
use crate::runtime::Runtime;
use crate::search::Limits;

fn decimal(text: &str) -> Option<u64> {
    if text.is_empty() || !text.bytes().all(|b| b.is_ascii_digit()) { return None; }
    text.parse().ok()
}

/// Check FEN structure, inventory, rights and EP before the trusted board core.
/// Analysis positions need not be reachable from the orthodox initial position.
pub fn fen(fields: &[&str]) -> Option<Board> {
    if fields.len() != 6 { return None; }
    let mut b = Board::empty();
    let rows: Vec<_> = fields[0].split('/').collect();
    if rows.len() != 8 { return None; }
    let mut counts = [[0usize; 7]; 2];
    for (row, text) in rows.iter().enumerate() {
        let mut file = 0usize;
        for c in text.bytes() {
            if (b'1'..=b'8').contains(&c) { file += (c - b'0') as usize; }
            else {
                if file >= 8 { return None; }
                let piece = match c.to_ascii_lowercase() {
                    b'p' => 1, b'n' => 2, b'b' => 3, b'r' => 4, b'q' => 5, b'k' => 6,
                    _ => return None,
                };
                if piece == 1 && (row == 0 || row == 7) { return None; }
                let side = c.is_ascii_lowercase() as usize;
                counts[side][piece] += 1;
                b.cells[(7 - row) * 16 + file] = if side == 0 { piece as i8 } else { -(piece as i8) };
                file += 1;
            }
            if file > 8 { return None; }
        }
        if file != 8 { return None; }
    }
    for pieces in counts {
        if pieces[6] != 1 || pieces[1] > 8 || pieces.iter().sum::<usize>() > 16 { return None; }
        let promotions = pieces[2].saturating_sub(2) + pieces[3].saturating_sub(2)
            + pieces[4].saturating_sub(2) + pieces[5].saturating_sub(1);
        if promotions > 8 - pieces[1] { return None; }
    }
    b.side = match fields[1] { "w" => 1, "b" => -1, _ => return None };
    if fields[2] != "-" {
        if fields[2].is_empty() { return None; }
        for c in fields[2].bytes() {
            let (right, king, rook, side) = match c {
                b'K' => (1, 4, 7, 1), b'Q' => (2, 4, 0, 1),
                b'k' => (4, 116, 119, -1), b'q' => (8, 116, 112, -1),
                _ => return None,
            };
            if b.castle & right != 0 || b.cells[king] != side * 6 || b.cells[rook] != side * 4 { return None; }
            b.castle |= right;
        }
    }
    if fields[3] != "-" {
        let ep = fields[3].as_bytes();
        if ep.len() != 2 || !(b'a'..=b'h').contains(&ep[0])
            || ep[1] != if b.side > 0 { b'6' } else { b'3' } { return None; }
        let square = (ep[1] - b'1') as i16 * 16 + (ep[0] - b'a') as i16;
        if b.cells[square as usize] != 0 || b.cells[(square - b.side as i16 * 16) as usize] != -b.side
            || b.cells[(square + b.side as i16 * 16) as usize] != 0 { return None; }
        b.ep = square;
    }
    b.halfmove = decimal(fields[4])?.try_into().ok()?;
    if decimal(fields[5])? == 0 { return None; }
    b.rebuild();
    let (white, black) = (b.king[0] as i16, b.king[1] as i16);
    if ((white & 7) - (black & 7)).abs() <= 1 && ((white >> 4) - (black >> 4)).abs() <= 1 { return None; }
    Some(b)
}

pub fn perft(b: &Board, depth: u8) -> u64 {
    if depth == 0 { return 1; }
    let moves = b.pseudo();
    let mut total = 0;
    for &m in &moves.a[..moves.n] {
        if let Some(child) = b.play(m) { total += perft(&child, depth - 1); }
    }
    total
}

pub fn repeated(b: &Board, keys: &[u64]) -> bool {
    keys.iter().rev().take(b.halfmove as usize + 1).filter(|&&key| key == b.hash).count() >= 3
}

pub fn drawn(b: &Board, keys: &[u64]) -> bool {
    let legal = b.legal();
    if legal.n == 0 { !b.in_check() }
    else { b.halfmove >= 100 || repeated(b, keys) || b.dead() }
}

pub fn limits(words: &[&str], limits: &mut Limits) -> bool {
    let mut infinite = false;
    for i in 1..words.len() {
        let value = words.get(i + 1).and_then(|text| decimal(text));
        match words[i] {
            "depth" => limits.depth = value.unwrap_or(1).clamp(1, (crate::search::PLY - 2) as u64) as u8,
            "nodes" => limits.nodes = value.unwrap_or(1).max(1),
            "movetime" => limits.millis = Some(value.unwrap_or(0)),
            "infinite" => infinite = true,
            _ => (),
        }
    }
    infinite
}

pub fn command(words: &[&str], b: &Board, keys: &[u64], runtime: &mut Runtime) -> bool {
    match words.first().copied().unwrap_or("") {
        "perft" => {
            let depth = words.get(1).and_then(|text| decimal(text)).unwrap_or(0).min(6) as u8;
            println!("perft {depth} {}", perft(b, depth));
        }
        "legal" => {
            let moves = b.legal();
            print!("legal");
            for &m in &moves.a[..moves.n] { print!(" {}", uci(m)); }
            println!();
        }
        "state" => {
            let mut copy = *b; copy.rebuild();
            let invariant = copy.hash == b.hash && copy.score == b.score && copy.ep == b.ep && copy.king == b.king;
            let eval = (b.score * b.side as i32).clamp(-20000, 20000);
            let draw = drawn(b, keys);
            println!("state {{\"hash\":{},\"halfmove\":{},\"eval\":{},\"draw\":{},\"dead\":{},\"invariant\":{}}}",
                     b.hash, b.halfmove, eval, draw, b.dead(), invariant);
        }
        "eval" => println!("eval {}", (b.score * b.side as i32).clamp(-20000, 20000)),
        "stats" => {
            let (result, nodes) = runtime.stats();
            let stats = runtime.statistics();
            println!("stats {{\"nodes\":{nodes},\"workers\":{},\"total_threads\":{},\"completed_depth\":{},\"epoch\":{},\"pvs\":{},\"qs\":{},\"hits\":{},\"history\":{},\"continuation\":{},\"correction\":{},\"eval_uses\":{},\"aborts\":{}}}",
                     runtime.workers(), runtime.workers() + 1, result.depth, runtime.epoch(),
                     stats.pvs, stats.qs, stats.hits, stats.history, stats.continuation,
                     stats.correction, stats.uses, stats.aborts);
        }
        _ => return false,
    }
    true
}
