"""Finite, reversible TCEC input specialization for maintained full C profiles.

This is a final source stage, after an admitted canonical/compact build and any
ownership stage.  It is deliberately not a C optimizer or a source-admission
mechanism: the caller must pin its complete input.  Only the two exact functions
below may change.  Existing development and standalone shipping paths keep their
transactional parser.

Valid input is NUL-free startpos UCI, with legal coordinate moves (all N/B/R/Q
promotions), at most 4096 historical positions and the unchanged line-reader
limit.  Clock values are ASCII unsigned decimals in [0, INT64_MAX]; omitted own
time still has the distinct UINT64_MAX sentinel.  Clock key ordering, repetition,
side selection, finite bare-go budget and overflow-safe budget cap do not change.

The owning command handler must finish the preceding GO before position writes.
Malformed positions may now leave a partial root/history, and malformed numeric
tokens no longer have the old zero-on-error semantics.  Their bounded handling
must remain memory-safe.  No in-place make-move assumption is introduced: parse
still writes a separate temporary Board.  Unsupported commands and long-line
draining are outside these protected edits and remain the caller's responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re


SCHEMA = "rove4k.tcec-c-input.v1"
B_TCEC_COMPILER = ("cc", "-std=c11", "-Os", "-pthread", "-x", "c", "-", "-o", "x")
B_COMPILER_PROOF = {
    "input_bytes": 9744,
    "input_sha256": "4b3412e3dddbe4cc9b40172be66d577aa998dc65e4ffa5876827f6b92654c5a8",
    "cpp_bytes": 88582,
    "cpp_sha256": "880cf9820a0be42c42525fb9bc881c3368735f48817400444fabf6ca639e58d0",
    "native_bytes": 26080,
    "native_sha256": "59eea719b15f84ef83dcdc1918e1037c234578df417a537f7997fa3593648e28",
    "receipt_sha256": "318d1ff30ba7e01b5a5d4bea64419933b98b150e1cea348f17e9674d443a4db6",
    "removed": ("-DWORKERS=2", "-DTT_BITS=18", "-DDEV=0"),
    "scope": "independent original-source CPP/native identity; new source needs native validation",
}


@dataclass(frozen=True)
class _Spec:
    storage: str
    board: str
    integer: str
    word: str
    ret: str
    position: str
    number: str
    token: str
    start: str
    parse: str
    root: str
    cursor: str
    history: str = "4096"
    digit: str = "(unsigned)(*s-'0')>9"


_SPECS = {
    "A": _Spec("static", "E", "L", "W", "J", "z", "y", "nt", "q", "i", "F", "B", "HISTORY"),
    "B": _Spec("static", "za", "I", "D", "return", "R", "G", "nt", "k", "H", "ql", "d"),
    "C": _Spec("static", "E", "int", "W", "return", "z", "y", "nt", "q", "i", "ql", "B"),
    "E": _Spec("static", "E", "L", "W", "J", "z", "y", "nt", "q", "i", "ql", "B"),
    "F2": _Spec("aa", "I", "S", "W", "H", "z", "qm", "w", "o", "qb", "Z", "d", digit="*s-48u>9"),
    "F8": _Spec("static", "I", "S", "W", "H", "z", "qm", "w", "o", "qb", "Z", "d", digit="*s-48u>9"),
}


def _regions(family: str) -> tuple[tuple[str, bytes, bytes], ...]:
    try:
        s = _SPECS[family]
    except KeyError as exc:
        raise ValueError(f"unsupported full C family: {family}") from exc
    d, token, r = s.cursor, s.token, s.root
    old_position = (
        f'{s.storage} void {s.position}(void){{{s.board} b,c;{s.word} a[{s.history}];'
        f'{s.integer} n=1;char*{d}={token}();if(!{d}||strcmp({d},"startpos")){s.ret};'
        f'{s.start}(&b);a[0]=b.h;{d}={token}();if({d}){{if(strcmp({d},"moves")){s.ret};'
        f'while(({d}={token}())){{if(n=={s.history}||!{s.parse}(&b,{d},&c)){s.ret};'
        f'b=c;a[n++]=b.h;}}}}{r}=b;qh=n;memcpy(qg,a,n*sizeof*a);}}'
    )
    # A legal startpos record's optional next token is exactly "moves".  Drop it
    # once, then consume all moves.  A missing token is safe (the tokenizer's
    # exhausted-state NULL result is never passed to parse).
    new_position = (
        f'{s.storage} void {s.position}(void){{{s.board} c;char*{d}={token}();'
        f'if(!{d}||strcmp({d},"startpos")){s.ret};{s.start}(&{r});'
        f'qg[0]={r}.h;qh=1;{token}();while(({d}={token}())){{'
        f'if(qh=={s.history}||!{s.parse}(&{r},{d},&c)){s.ret};'
        f'{r}=c;qg[qh++]={r}.h;}}}}'
    )
    old_number = (
        f'{s.storage} {s.word} {s.number}(const char*s){{char*e;if(!s||{s.digit}){s.ret} 0;'
        f'{s.word} n=strtoull(s,&e,10);{s.ret}*e||n>>63?0:n;}}'
    )
    # This is a function, not a macro: number(token()) must evaluate token once.
    new_number = f'{s.storage} {s.word} {s.number}(const char*s){{{s.ret} s?strtoull(s,0,10):0;}}'
    return tuple((name, old.encode("ascii"), new.encode("ascii")) for name, old, new in (
        ("position", old_position, new_position), ("number", old_number, new_number)
    ))


def _digest(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _patch(source: bytes, changes: tuple[tuple[str, bytes, bytes], ...]) -> tuple[bytes, list, list]:
    located = []
    for name, old, new in changes:
        if source.count(old) != 1:
            raise ValueError(f"{name}: expected exactly one admitted function")
        located.append((source.index(old), name, old, new))
    located.sort()
    chunks, edits, gaps = [], [], []
    consumed = emitted = 0
    for begin, name, old, new in located:
        if begin < consumed:
            raise ValueError("overlapping admitted functions")
        gap = source[consumed:begin]
        chunks.extend((gap, new))
        gaps.append({"input_begin": consumed, "output_begin": emitted, **_digest(gap)})
        emitted += len(gap)
        edits.append({
            "role": name, "input_begin": begin, "output_begin": emitted,
            "before": _digest(old), "after": _digest(new),
        })
        consumed, emitted = begin + len(old), emitted + len(new)
    gap = source[consumed:]
    chunks.append(gap)
    gaps.append({"input_begin": consumed, "output_begin": emitted, **_digest(gap)})
    return b"".join(chunks), edits, gaps


def transform_source(source: bytes, *, family: str, mode: str = "valid-tcec") -> tuple[bytes, dict]:
    """Transform only admitted position/number functions and prove full inverse.

    The caller pins full source identity and proves the prior-GO drain.  The
    optional single-role modes are finite experiments, not fallback parsers.
    """
    if not isinstance(source, bytes):
        raise TypeError("source must be bytes")
    if mode not in ("valid-tcec", "position", "number"):
        raise ValueError(f"unsupported input specialization: {mode}")
    changes = tuple(row for row in _regions(family) if mode == "valid-tcec" or row[0] == mode)
    result, edits, gaps = _patch(source, changes)
    restored, _, _ = _patch(result, tuple((name, new, old) for name, old, new in changes))
    if restored != source:
        raise ValueError("input specialization full inverse failed")
    proof = {
        "schema": SCHEMA, "family": family, "mode": mode,
        "input": _digest(source), "output": _digest(result),
        "edits": edits, "protected_spans": gaps, "inverse_exact": True,
        "contract": {
            "position": "legal startpos replay including castling, EP and N/B/R/Q; <=4096 positions",
            "numbers": "ASCII unsigned decimal <=INT64_MAX; own-clock sentinel UINT64_MAX retained",
            "ownership": "caller drains prior GO before direct root/history mutation",
            "scope_change": "malformed-position rollback and malformed-number zero recovery removed",
            "unchanged": "line reader, tokenization, clock keys/order/side, history/search/gen/parse",
        },
    }
    return result, proof


def restore_source(candidate: bytes, proof: dict) -> bytes:
    """Restore exact original bytes; reject altered proof identities or candidate."""
    if proof.get("schema") != SCHEMA or _digest(candidate) != proof.get("output"):
        raise ValueError("input specialization output identity mismatch")
    family, mode = proof.get("family"), proof.get("mode")
    if mode not in ("valid-tcec", "position", "number"):
        raise ValueError("input specialization mode mismatch")
    changes = tuple(row for row in _regions(family) if mode == "valid-tcec" or row[0] == mode)
    original, _, _ = _patch(candidate, tuple((name, new, old) for name, old, new in changes))
    if _digest(original) != proof.get("input"):
        raise ValueError("input specialization input identity mismatch")
    projected, expected = transform_source(original, family=family, mode=mode)
    if projected != candidate or expected != proof:
        raise ValueError("input specialization protected-span proof mismatch")
    return original


def compiler_for(source: bytes, *, family: str, original: tuple[str, ...] | list[str]) -> tuple[tuple[str, ...], dict]:
    """Select the independently proved B argv reduction, with a fresh token gate.

    Other families retain their admitted compiler verbatim.  For B, new source
    still needs its own native/semantic check; the old native hash is no claim
    about a transformed source's executable.
    """
    original = tuple(original)
    if family != "B":
        return original, {"changed": False}
    full = ("cc", "-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18", "-DDEV=0", "-x", "c", "-", "-o", "x")
    if original not in (full, B_TCEC_COMPILER):
        raise ValueError("B compiler differs from admitted full/short argv")
    if re.search(rb"\b(?:WORKERS|TT_BITS|DEV)\b", source):
        raise ValueError("B source still contains a removed definition's token")
    return B_TCEC_COMPILER, {
        "changed": original != B_TCEC_COMPILER,
        "tokens_absent": ["WORKERS", "TT_BITS", "DEV"],
        "input": _digest(source), "baseline_identity_proof": dict(B_COMPILER_PROOF),
        "new_source_native_validation_required": True,
    }
