"""Guarded, study-only C/Rust Zobrist alignment; no canonical files are edited.

Apply this overlay before any other transformation of ``rust/board.rs``. Inputs
are a mapping of runtime-relative names to UTF-8 str or bytes, as used by the
build recipe. The returned mapping preserves each value's type and all other
files. The pinned complete board digest deliberately rejects an unreviewed
source revision, rather than silently producing a partially matched study.

``precompute=True`` (the default) gives the matched study a single fixed Rust
table, built by const evaluation, so piece and metadata operations use lookups
like C. The 1561 u64 values occupy 12488 initialized data bytes before native
compression. C instead fills zero-initialized static arrays in board_init at
runtime. This intentional rodata/BSS and startup difference remains part of the
source/native/data/startup cost; it is not language-cost equivalence. Set
``precompute=False`` only for an explicitly labeled on-demand hash experiment.

``Board.study_pawn_key`` is maintained by the existing Rust incremental board
operations. ``study_context_key`` matches C's reversible-history fold only at
nonterminal halfmove clocks (<100); both engines adjudicate >=100 before a TT
lookup. It rejects direct use outside that domain. This preserves Rust's fixed
101-key suffix instead of changing its independent rules/runtime machinery.
"""

from __future__ import annotations

import hashlib
from typing import Mapping, TypeVar

PINNED_BASE = "de5676dcbc498d77477c66064aca926633c851ff"
BOARD_SHA256 = "1e48a2780dac8d401045528e6e942bb616a68c330ae283b24ab789234e4df59d"
MASK64 = (1 << 64) - 1
SEED = 0x726F7665346B
GAMMA = 0x9E3779B97F4A7C15
PIECE_SLOTS = 12 * 128
RIGHTS_SLOT = PIECE_SLOTS
EP_SLOT = RIGHTS_SLOT + 16
TURN_SLOT = EP_SLOT + 8
Source = TypeVar("Source", str, bytes)


def reference_slot(index: int) -> int:
    """C's zero-based board_init slot, for independent fixture consumers."""
    if not 0 <= index <= TURN_SLOT:
        raise ValueError("Zobrist slot must be in 0..1560")
    value = (SEED + (index + 1) * GAMMA) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return value ^ (value >> 31)


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"matched hash overlay: {label} expected once, found {count}")
    return source.replace(old, new, 1)


def apply(files: Mapping[str, Source], *, precompute: bool = True) -> tuple[dict[str, Source], list[str]]:
    """Return copied sources and change descriptions; fail closed on drift."""
    if not isinstance(precompute, bool):
        raise TypeError("matched hash overlay precompute must be bool")
    name = "rust/board.rs"
    if name not in files:
        raise ValueError(f"matched hash overlay: missing {name}")
    raw = files[name]
    if not isinstance(raw, (str, bytes)):
        raise TypeError("matched hash overlay source values must be str or bytes")
    source = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    source = source.replace("\r\n", "\n")
    actual = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if actual != BOARD_SHA256:
        raise ValueError(
            f"matched hash overlay: unknown rust/board.rs {actual}; "
            f"expected {BOARD_SHA256} from {PINNED_BASE}; apply hash first"
        )

    if precompute:
        hash_source = (
            "// C initializes these values in BSS at startup; Rust const evaluation\n"
            "// keeps the same per-node table lookup while using initialized rodata.\n"
            "const fn study_zobrist_table() -> [u64; 1561] {\n"
            "    let mut table = [0u64; 1561];\n"
            "    let mut state = 0x726f7665346bu64;\n"
            "    let mut index = 0;\n"
            "    while index < table.len() {\n"
            "        state = state.wrapping_add(0x9e3779b97f4a7c15);\n"
            "        let mut value = state;\n"
            "        value = (value ^ (value >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);\n"
            "        value = (value ^ (value >> 27)).wrapping_mul(0x94d049bb133111eb);\n"
            "        table[index] = value ^ (value >> 31);\n"
            "        index += 1;\n"
            "    }\n"
            "    table\n"
            "}\n"
            "static STUDY_ZOBRIST: [u64; 1561] = study_zobrist_table();\n"
            "fn study_zobrist(index: u64) -> u64 { STUDY_ZOBRIST[index as usize] }\n"
        )
        hash_label = "C indexed SplitMix piece keys; precomputed Rust table lookup (12488 initialized bytes)"
    else:
        hash_source = (
            "fn study_zobrist(index: u64) -> u64 {\n"
            "    mix(0x726f7665346bu64.wrapping_add(index.wrapping_mul(0x9e3779b97f4a7c15)))\n"
            "}\n"
        )
        hash_label = "C indexed SplitMix piece keys; on-demand Rust calculation experiment"

    replacements = [
        (
            "    pub hash: u64,\n    pub hist: History,",
            "    pub hash: u64,\n    pub study_pawn_key: u64,\n    pub hist: History,",
            "incremental pawn key field",
        ),
        (
            "fn piece_hash(s: u8, p: i8) -> u64 { mix(1 + s as u64 * 12 + (p.abs() - 1) as u64 + color(p) as u64 * 6) }",
            "// Matched study: C board_init consumes 12*128 piece slots, then metadata.\n"
            + hash_source +
            "fn piece_hash(s: u8, p: i8) -> u64 {\n"
            "    let piece = if p > 0 { p as i16 - 1 } else { 5 - p as i16 };\n"
            "    study_zobrist(piece as u64 * 128 + s as u64)\n"
            "}",
            hash_label,
        ),
        (
            "fullmove:1,hash:0,hist:History::new()",
            "fullmove:1,hash:0,study_pawn_key:0,hist:History::new()",
            "empty board pawn key initialization",
        ),
        (
            "        self.bb = [[0; 7]; 2]; self.hash = 0; self.score = 0;",
            "        self.bb = [[0; 7]; 2]; self.hash = 0; self.study_pawn_key = 0; self.score = 0;",
            "rebuild pawn key initialization",
        ),
        (
            "                self.hash ^= piece_hash(s, p); self.score += piece_score(s, p);",
            "                let key = piece_hash(s, p); self.hash ^= key;\n"
            "                if p.abs() == 1 { self.study_pawn_key ^= key; }\n"
            "                self.score += piece_score(s, p);",
            "rebuild pawn key update",
        ),
        (
            "            self.hash ^= piece_hash(s, old); self.score -= piece_score(s, old);",
            "            let key = piece_hash(s, old); self.hash ^= key;\n"
            "            if old.abs() == 1 { self.study_pawn_key ^= key; }\n"
            "            self.score -= piece_score(s, old);",
            "put old pawn key update",
        ),
        (
            "            self.hash ^= piece_hash(s, p); self.score += piece_score(s, p);",
            "            let key = piece_hash(s, p); self.hash ^= key;\n"
            "            if p.abs() == 1 { self.study_pawn_key ^= key; }\n"
            "            self.score += piece_score(s, p);",
            "put new pawn key update",
        ),
        (
            "    fn meta_hash(&self) -> u64 {\n"
            "        mix(2000 + self.castle as u64) ^ if self.side < 0 { mix(2100) } else { 0 }\n"
            "            ^ if self.legal_ep() { mix(2200 + (self.ep & 7) as u64) } else { 0 }\n"
            "    }",
            "    fn meta_hash(&self) -> u64 {\n"
            "        study_zobrist(1536 + self.castle as u64)\n"
            "            ^ if self.side < 0 { study_zobrist(1560) } else { 0 }\n"
            "            ^ if self.legal_ep() { study_zobrist(1552 + (self.ep & 7) as u64) } else { 0 }\n"
            "    }\n"
            "    /// C context_key, after the caller's terminal/draw adjudication.\n"
            "    pub fn study_context_key(&self) -> u64 {\n"
            "        assert!(self.halfmove < 100, \"study context is defined only before the fifty-move terminal\");\n"
            "        let mut key = self.hash ^ (self.halfmove as u64).wrapping_mul(0xd6e8feb86659fd93);\n"
            "        let count = (self.halfmove as usize + 1).min(self.hist.len());\n"
            "        for &previous in &self.hist[self.hist.len() - count..] {\n"
            "            key = key.rotate_left(17) ^ previous;\n"
            "        }\n"
            "        key\n"
            "    }",
            "C metadata and reversible-history context",
        ),
    ]
    changes = []
    for old, new, label in replacements:
        source = _replace_once(source, old, new, label)
        changes.append(f"{name}: {label}")
    result = dict(files)
    result[name] = source.encode("utf-8") if isinstance(raw, bytes) else source
    return result, changes
