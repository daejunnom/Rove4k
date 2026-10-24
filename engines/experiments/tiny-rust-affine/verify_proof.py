#!/usr/bin/env python3
"""Precompile source/domain proof for the one Rust affine-HCE experiment.

Only Python integer arithmetic and explicit source reads are used. No Rust,
compiler, engine, subprocess, or native image is executed. This is a proof on
production consumers' valid 0x88 squares, not arbitrary usize square inputs.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
FILES = ("main.rs", "board.rs", "search.rs", "runtime.rs", "os.rs", "link.ld", "build.py")
ORIGINAL_BOARD_SHA256 = "f27472ea055b67e61cdd82a3d7747feced50c899bef72365ffdc940043dedef3"

# Independent transcription of the original match and material values. These
# literals are deliberately not imported from producer.py or its Rust template.
BASE = (0, 100, 320, 330, 500, 900, 0)
CENTER = (0, 2, 9, 5, 0, 2, -3)
ADVANCE = (0, 7, 0, 0, 2, 0, 0)
PACKED_EXPECTED = (3072, 119908, 12608, 8522, 36340, 6020, 0)

ORIGINAL_VALUE = """pub fn value(p: i8, square: usize) -> i32 {
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
}"""

# The candidate's permitted token stream is independent of producer/template
# constants. In particular, conversion to i32 MUST precede subtraction of 3.
CANDIDATE_VALUE = """static HCE_COEFFICIENTS: [u32; 7] =
    [3072, 119908, 12608, 8522, 36340, 6020, 0];
pub fn value(p: i8, square: usize) -> i32 {
    let a = p.abs() as usize;
    let rank = (square >> 4) as i32;
    let advance = if p > 0 { rank } else { 7 - rank };
    let center = 7 - (2 * (square & 7) as i32 - 7).abs() - (2 * rank - 7).abs();
    let w = HCE_COEFFICIENTS[a];
    let positional = (w >> 14) as i32 * advance + (((w >> 10) & 15) as i32 - 3) * center;
    p.signum() as i32 * ((w & 1023) as i32 + positional)
}"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def tokens(text):
    # No strings or nested comments occur in either permitted value body.
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    return re.findall(r"[A-Za-z_][A-Za-z_0-9]*|[0-9]+|>>|<<|->|=>|[^\s]", text)


def witness(source, fragment, label):
    source_tokens, fragment_tokens = tokens(source), tokens(fragment)
    size = len(fragment_tokens)
    require(any(source_tokens[i:i + size] == fragment_tokens
                for i in range(len(source_tokens) - size + 1)),
            "source admission witness missing: " + label)


def value_span(source):
    signature = "pub fn value(p: i8, square: usize) -> i32 {"
    require(source.count(signature) == 1, "expected one exact value signature")
    start = source.index(signature)
    at, depth = start + len(signature), 1
    while depth and at < len(source):
        depth += (source[at] == "{") - (source[at] == "}")
        at += 1
    require(depth == 0, "unterminated value function")
    return start, at


def verify_delta(original, candidate):
    start, end = value_span(original)
    require(tokens(original[start:end]) == tokens(ORIGINAL_VALUE),
            "original value differs from independent original formula")
    prefix, suffix = original[:start], original[end:]
    require(candidate.startswith(prefix) and candidate.endswith(suffix),
            "candidate changed text outside original value replacement")
    replacement_end = len(candidate) - len(suffix) if suffix else len(candidate)
    replacement = candidate[len(prefix):replacement_end]
    require(tokens(replacement) == tokens(CANDIDATE_VALUE),
            "candidate is not exactly the permitted static7u32/value token delta")
    require("unsafe" not in tokens(replacement), "unsafe candidate value")
    return {
        "original_value_sha256": sha(original[start:end].encode()),
        "replacement_sha256": sha(replacement.encode()),
        "outside_replacement_bytes_identical": True,
        "permitted_replacement_tokens_exact": True,
        "signature_rank_advance_center_abs_signum_retained": True,
        "safe_static_7_u32_index_retained": True,
        "signed_conversion_before_center_bias_subtraction": True,
    }


def original_value(p, square):
    """Literal original match, not the proposed coefficient expression."""
    kind = abs(p)
    rank = square >> 4
    advance = rank if p > 0 else 7 - rank
    center = 7 - abs(2 * (square & 7) - 7) - abs(2 * rank - 7)
    if kind == 1:
        positional = advance * 7 + center * 2
    elif kind == 2:
        positional = center * 9
    elif kind == 3:
        positional = center * 5
    elif kind == 4:
        positional = advance * 2
    elif kind == 5:
        positional = center * 2
    elif kind == 6:
        positional = -center * 3
    else:
        positional = 0
    return ((p > 0) - (p < 0)) * (BASE[kind] + positional)


def packed_value(p, square):
    word = PACKED_EXPECTED[abs(p)]
    rank = square >> 4
    advance = rank if p > 0 else 7 - rank
    center = 7 - abs(2 * (square & 7) - 7) - abs(2 * rank - 7)
    positional = (word >> 14) * advance + (((word >> 10) & 15) - 3) * center
    return ((p > 0) - (p < 0)) * ((word & 1023) + positional)


def arithmetic_proof():
    derived = tuple(base | ((center + 3) << 10) | (advance << 14)
                    for base, center, advance in zip(BASE, CENTER, ADVANCE))
    require(derived == PACKED_EXPECTED, "independent packed literals disagree")
    decoded = []
    for kind, word in enumerate(PACKED_EXPECTED):
        require(0 <= BASE[kind] < 1024 and 0 <= CENTER[kind] + 3 < 16
                and 0 <= ADVANCE[kind] < 8, "overlapping packed field")
        row = (word & 1023, ((word >> 10) & 15) - 3, word >> 14)
        require(row == (BASE[kind], CENTER[kind], ADVANCE[kind]),
                "decoded coefficients disagree")
        decoded.append({"kind": kind, "word": word, "base": row[0],
                        "center": row[1], "advance": row[2]})
    squares = tuple(square for square in range(128) if square & 0x88 == 0)
    require(len(squares) == 64, "incorrect 0x88 domain")
    rows = []
    for p in range(-6, 7):
        for square in squares:
            original, candidate = original_value(p, square), packed_value(p, square)
            require(original == candidate, f"value mismatch: p={p}, square={square}")
            rank, file = square >> 4, square & 7
            advance = rank if p > 0 else 7 - rank
            center = 7 - abs(2 * file - 7) - abs(2 * rank - 7)
            # Absolute term bound <= 900+9*7+7*7=1012; each multiplication,
            # addition and final sign product is representable as Rust i32.
            require(0 <= advance <= 7 and -7 <= center <= 5,
                    "consumer square arithmetic domain differs")
            require(abs(BASE[abs(p)]) + abs(CENTER[abs(p)] * center)
                    + abs(ADVANCE[abs(p)] * advance) <= 1012,
                    "i32 intermediate range proof failed")
            rows.append([p, square, original])
    require(len(rows) == 832, "enumeration incomplete")
    invalid = [p for p in range(-127, 128) if abs(p) >= 7]
    require(len(invalid) == 242 and all(abs(p) >= len(PACKED_EXPECTED) for p in invalid),
            "invalid signed-piece safe-index rejection proof failed")
    return {
        "independent_original_match_and_material_literals": True,
        "packing_formula": "base | ((center + 3) << 10) | (advance << 14)",
        "decoded_coefficients": decoded,
        "piece_domain": [-6, 6], "valid_0x88_squares": list(squares),
        "compared_pairs": len(rows), "zero_pairs": 64,
        "both_colour_promotion_kind_pairs": 512,
        "both_colour_ep_pawn_pairs": 128,
        "both_colour_nonzero_capture_piece_pairs": 768,
        "results_sha256": sha(json.dumps(rows, separators=(",", ":")).encode()),
        "all_equal": True, "i32_intermediate_absolute_bound": 1012,
        "invalid_piece_source_argument": {
            "values_minus127_to127_rejected_by_safe_length7_index": len(invalid),
            "minus128": "p.abs() is retained exactly; checked/release abs behavior is unchanged, not simulated here",
            "no_mask_no_unchecked_access_no_invalid_piece_admission": True,
        },
        "excluded_domain": "No equivalence or panic-order claim for arbitrary usize squares outside admitted valid 0x88 consumers",
    }


def consumer_proof(sources, fixture_sources):
    board, main, search = (sources[name].decode() for name in ("board.rs", "main.rs", "search.rs"))
    fragments = (
        (board, "let back = [4, 2, 3, 5, 6, 3, 2, 4];", "start piece alphabet"),
        (board, "if s & 0x88 == 0 && p != 0 {", "rebuild square domain"),
        (board, "self.hash ^= piece(p, s); self.score += value(p, s);", "rebuild score"),
        (board, "self.score -= value(old, s);", "put removal score"),
        (board, "self.score += value(p, s);", "put insertion score"),
        (board, "if (f | t) & 0x88 != 0 { return None; }", "play square rejection"),
        (board, "if !(2..=5).contains(&promotion) { return None; } p = s * promotion;", "promotion alphabet"),
        (board, "if p == 0 && self.cells[from(m)].abs() == 1 && to(m) as i16 == self.ep { -self.side } else { p }", "captured EP pawn"),
        (board, "b.put(f, 0); b.put(t, p);", "play piece transport"),
        (board, "b.put(rook, 0); b.put(transit, s * 4);", "castle rook alphabet"),
        (board, "if valid(q) && self.cells[q as usize] == self.side {", "canonical EP source square"),
        (board, "t.put(q as usize, 0); t.put(cap as usize, 0); t.put(self.ep as usize, self.side);", "canonical EP piece alphabet"),
        (main, "if words.get(1)!=Some(&\"startpos\"){return None;}", "shipping position admission"),
        (main, "b=b.play(b.parse(text)?)?;", "shipping moves admitted by parse/play"),
        (search, "value(b.captured(m),to(m)).abs()*16-value(b.cells[from(m)],from(m)).abs()", "capture-order value consumers"),
    )
    for source, fragment, label in fragments:
        witness(source, fragment, label)
    board_fixture = fixture_sources["tests/board.rs"].decode()
    witness(board_fixture, "b'p' => 1, b'n' => 2, b'b' => 3, b'r' => 4, b'q' => 5, b'k' => 6, _ => return None", "external FEN piece rejection")
    witness(board_fixture, "if file >= 8 || p == 1 && (row == 0 || row == 7) { return None; }", "external FEN file and pawn admission")
    witness(board_fixture, "if file != 8 { return None; }", "external FEN rank admission")
    witness(board_fixture, "if kings != [1, 1] || counts.iter().any(|&n| n > 16) { return None; }", "external FEN king/count admission")
    return {
        "source_fragment_witnesses": [label for _, _, label in fragments],
        "all_witnesses_present": True,
        "production_induction": "start uses only 0,+/-1..6 on valid 0x88 squares; play transports admitted pieces, introduces only 0, same-colour pawn, rook4, or validated promotion2..5; canonical EP uses admitted valid squares and same-colour pawn",
        "incremental_consumer": "put subtracts and adds identical per-piece/square values; rebuild sums the same values",
        "capture_order_consumer": "pseudo-generated valid source/target squares and captured piece +/-1..6, including EP +/-1, have identical value().abs() ordering contributions",
        "zero_consumer": "both formulas return zero for p=0 on every admitted square",
        "fixture_fen_validation_witnesses_retained": True,
        "admission_unchanged_basis": "all original board bytes outside value are identical; all six other production files are byte-identical; fixture sources are read and hashed, never transformed",
        "proof_boundary": "Source admission argument plus exhaustive scalar arithmetic; not Rust execution, chess legality requalification, or universal invalid-square equivalence",
    }


def prove(source_dir, report):
    source_bytes = {name: (source_dir / name).read_bytes() for name in FILES}
    fixture_bytes = {name: (source_dir / name).read_bytes()
                     for name in ("tests/board.rs", "tests/search.rs")}
    report["source_sha256"] = {name: sha(data) for name, data in source_bytes.items()}
    report["fixture_source_sha256"] = {name: sha(data) for name, data in fixture_bytes.items()}
    require(sha(source_bytes["board.rs"]) == ORIGINAL_BOARD_SHA256,
            "original qualified board SHA-256 differs")
    producer_path = HERE / "producer.py"
    template_path = HERE / "value.rs.in"
    report["experiment_input_sha256"] = {
        "producer.py": sha(producer_path.read_bytes()),
        "value.rs.in": sha(template_path.read_bytes()),
        "verify_proof.py": sha(Path(__file__).read_bytes()),
    }
    # Execute only the reviewed pure producer's in-memory source transform.
    # Avoid creating __pycache__ or other generated files in the checkout.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("tiny_rust_affine_proof_producer", producer_path)
    require(spec is not None and spec.loader is not None, "producer import unavailable")
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    original = source_bytes["board.rs"].decode()
    candidate = producer.transform(original)
    require(isinstance(candidate, str), "producer.transform must return str")
    produced, metadata = producer.produce(source_bytes)
    require(set(produced) == set(source_bytes), "producer changed source file set")
    require(all(isinstance(data, bytes) for data in produced.values()), "producer files must remain bytes")
    require(produced["board.rs"] == candidate.encode(), "produce/transform board differs")
    require(all(produced[name] == data for name, data in source_bytes.items() if name != "board.rs"),
            "producer changed a file other than board.rs")
    report["candidate_source_sha256"] = {name: sha(data) for name, data in produced.items()}
    report["producer_metadata"] = metadata
    report["source_delta"] = verify_delta(original, candidate)
    report["source_delta"]["other_six_production_files_byte_identical"] = True
    report["arithmetic"] = arithmetic_proof()
    report["consumer_admission"] = consumer_proof(source_bytes, fixture_bytes)
    report["passed"] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path,
                        help="new absolute external JSON report path")
    args = parser.parse_args()
    if not args.source_dir.is_absolute() or not args.out.is_absolute():
        parser.error("--source-dir and --out must be absolute")
    source_dir, output = args.source_dir.resolve(), args.out.resolve()
    if not source_dir.is_dir() or output.exists():
        parser.error("existing source directory and new output file required")
    # The runner executes a frozen copy outside the checkout. Discover actual
    # Git ancestors instead of interpreting that copy's parent as a repository.
    checkouts = {parent for anchor in (source_dir, HERE)
                 for parent in (anchor, *anchor.parents) if (parent / ".git").exists()}
    if any(output == root or root in output.parents for root in checkouts) or output.suffix.lower() != ".json":
        parser.error("--out must be a new external .json file outside the checkout")
    report = {
        "scope": "PRECOMPILE independent arithmetic and exact source-delta proof",
        "source_dir": str(source_dir), "passed": False,
        "rust_compiler_or_engine_executed": False,
        "no_native_size_reproducibility_runtime_strength_or_4k_claim": True,
    }
    try:
        prove(source_dir, report)
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"report": str(output), "passed": report["passed"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
