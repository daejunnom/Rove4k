"""Profile the exact selected C portfolio sources without a runtime selector.

The maintained producers remain the source authority. This projection accepts
only their named complete outputs, changes resource/lifecycle consumers, and
protects the rest with a full inverse. It is not runtime qualification.
"""
from __future__ import annotations

from hashlib import sha256
from math import gcd
import re


SCHEMA = "rove4k.c-resource-projection.v1"
INPUTS = {
    "A": (7507, "9fbde80264463144b320617e3f3dd87770fb3c43c7d38dc98b09bb219cdf6ce7"),
    "B": (8299, "3e51aba62fba6c15eeb7fa731277fe2286ae65924a7dc94d59a425b8e5251e08"),
    "C": (8125, "e47c5c0541407b55cae45ae4754354d4de616c5c47671cf4e650b30b38e528ae"),
    "E": (7695, "a8ff777e4d3a4d0edc968c169732d52fd3b3a2c8d732a9b74b43c28f0799b3ac"),
    "F": (6929, "e513ef4f7e6e72b5f4a2f1d21d5dbc6932c6c4d4f6be07c240346d54d9e8ca8b"),
}
# All names are bound by the complete input pins, not inferred from arbitrary C.
CONTEXT = {
    "A": dict(st="static", integer="L", returned="J", table_type="Z", table="N",
              worker_type="M", workers="K", ident="id", depth="C", handles="qb",
              joined="qk", pending="I", worker="A", selector="x", clear="B",
              lock="zN", key="aT", data="U", count="1<<18", mask="((1u<<18)-1)",
              selector_old="M*w=K+(K[1].C>K->C);"),
    "B": dict(st="J", integer="I", returned="l", table_type="zb", table="qq",
              worker_type="zd", workers="qr", ident="i", depth="d", handles="qb",
              joined="qk", pending="qj", worker="s", selector="d", clear="B",
              lock="a", key="h", data="v", count="262144", mask="262143u",
              selector_old="zd*w=qr+(qr[1].d>qr[0].d);"),
    "C": dict(st="static", integer="int", returned="return", table_type="Z", table="qq",
              worker_type="ai", workers="qr", ident="id", depth="C", handles="qb",
              joined="qk", pending="qj", worker="A", selector="x", clear="B",
              lock="zN", key="aT", data="U", count="1<<18", mask="((1u<<18)-1)",
              selector_old="ai*w=qr+(qr[1].C>qr->C);"),
    "E": dict(st="static", integer="L", returned="J", table_type="Z", table="qq",
              worker_type="ai", workers="qr", ident="id", depth="C", handles="qb",
              joined="qk", pending="qj", worker="A", selector="x", clear="B",
              lock="zN", key="aT", data="U", count="1<<18", mask="((1u<<18)-1)",
              selector_old="ai*w=qr+(qr[1].C>qr->C);"),
    "F": dict(st="aa", integer="S", returned="H", table_type="ql", table="B",
              worker_type="X", workers="U", ident="a", depth="b", handles="t",
              joined="C", pending="A", worker="qq", selector="y", clear="qk",
              lock="zN", key="a", data="b", count="1<<18", mask="262143",
              selector_old="X*w=U+(U[1].b>U->b);"),
}


def pin(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def require(value, message: str) -> None:
    if not value:
        raise ValueError(message)


def transform_source(source: bytes, *, family: str, profile,
                     entry_cleanup: str = "private-path") -> tuple[bytes, dict]:
    """Consume a validated ResourceProfile; never allocate or execute its TT."""
    require(type(source) is bytes and family in INPUTS and
            (len(source), sha256(source).hexdigest()) == INPUTS[family],
            "exact selected full C portfolio source required")
    require(entry_cleanup in ("private-path", "none"), "explicit entry cleanup policy required")
    layout = profile.layout(24)
    require(profile.parallel_init and profile.control_threads == 1 and 1 <= profile.workers <= 512 and
            18 <= layout.bits <= 34, "unsupported fixed production resource domain")
    c = CONTEXT[family]
    text = source.decode("ascii")
    names = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", text))
    require(not ({"RVW", "RVN", "RVU", "rv_n", "rv_i", "rv_e"} & names),
            "profile identifiers collide with the admitted source")
    unit = 4096 // gcd(4096, layout.entry_bytes)
    require(layout.entries % unit == 0, "profile TT must contain complete base-page units")
    definitions = (f"#define RVW {profile.workers}\n"
                   f"#define RVN ((size_t)1<<{layout.bits})\n"
                   f"#define RVU {unit}\n")
    edits = [("resource constants", 0, "", definitions)]

    def change(role: str, before: str, after: str) -> None:
        require(text.count(before) == 1, "one exact resource consumer required: " + role)
        edits.append((role, text.index(before), before, after))

    wt, ws, ident, depth = (c[name] for name in ("worker_type", "workers", "ident", "depth"))
    tt, handles, integer = (c[name] for name in ("table", "handles", "integer"))
    change("worker storage", f"{wt} {ws}[2];", f"{wt} {ws}[RVW];")
    change("join handles", f"pthread_t {handles}[2];", f"pthread_t {handles}[RVW];")
    change("TT mask", f"{tt}+(a&{c['mask']})", f"{tt}+(a&(RVN-1))")
    change("TT allocation", f"{tt}=calloc({c['count']},sizeof*{tt});",
           f"{tt}=aligned_alloc(4096,RVN*sizeof*{tt});")
    index_type = "Y" if family == "F" else "size_t"
    old_end = "262144" if family == "B" else "(1<<18)"
    old_clear = (f"{c['st']} void {c['clear']}(void){{for({index_type} i=0;i<{old_end};i++)"
                 f"atomic_flag_clear(&{tt}[i].{c['lock']});}}")
    new_clear = (f"{c['st']} void*{c['clear']}(void*p){{{wt}*w=p;size_t rv_n=w->{ident},"
                 "rv_i=(RVN/RVU*rv_n/RVW)*RVU,rv_e=(RVN/RVU*(rv_n+1)/RVW)*RVU;"
                 f"for(;rv_i<rv_e;rv_i++){{{tt}[rv_i].{c['key']}={tt}[rv_i].{c['data']}=0;"
                 f"atomic_flag_clear_explicit(&{tt}[rv_i].{c['lock']},memory_order_relaxed);}}"
                 f"{c['returned']} 0;}}")
    change("parallel page-owned TT initialization", old_clear, new_clear)
    startup = (f"for({integer} n=0;n<RVW;n++){{{ws}[n].{ident}=n;"
               f"if(pthread_create({handles}+n,0,{c['clear']},{ws}+n))exit(2);}}"
               f"for({integer} n=0;n<RVW;n++)if(pthread_join({handles}[n],0))exit(2);")
    change("initialization join before UCI", c["clear"] + "();", startup)
    new_selector = (f"{wt}*w={ws};for({integer} n=1;n<RVW;n++)"
                    f"if({ws}[n].{depth}>w->{depth})w={ws}+n;")
    change("all-worker completed-depth selector", c["selector_old"], new_selector)
    null = "NULL" if family == "F" else "0"
    old_launch = (f"{c['pending']}={c['joined']}=2;for({integer} n=0;n<2;n++)"
                  f"{{{ws}[n].{ident}=n;{ws}[n].{depth}=0;"
                  f"if(pthread_create({handles}+n,{null},{c['worker']},{ws}+n))exit(2);}}")
    new_launch = old_launch.replace("=2;", "=RVW;", 1).replace("n<2;", "n<RVW;", 1)
    change("GO publication and launch count", old_launch, new_launch)
    if entry_cleanup == "none":
        expression = (rf"{re.escape(integer)} main\({re.escape(integer)} [A-Za-z_][A-Za-z_0-9]*,"
                      rf"char\*\*[A-Za-z_][A-Za-z_0-9]*\)\{{if\(remove\(\*"
                      rf"[A-Za-z_][A-Za-z_0-9]*\)\){re.escape(c['returned'])} 2;")
        entries = list(re.finditer(expression, text))
        require(len(entries) == 1, "one packaging-owned unlink entry required")
        change("loader-owned entry without pathname unlink", entries[0].group(), integer + " main(void){")
    ordered = sorted(edits, key=lambda row: (row[1], len(row[2])))
    result = source
    end = 0
    for role, begin, before, _ in ordered:
        require(begin >= end, "overlapping resource projection: " + role)
        end = begin + len(before)
    for role, begin, before, after in reversed(ordered):
        result = result[:begin] + after.encode("ascii") + result[begin + len(before):]
    spans, gaps = [], []
    old_at = new_at = delta = 0
    for role, begin, before, after in ordered:
        start = begin + delta
        gap = source[old_at:begin]
        require(gap == result[new_at:start], "resource protected complement differs")
        gaps.append(dict(old_start=old_at, new_start=new_at, **pin(gap)))
        spans.append(dict(role=role, old_start=begin, new_start=start, old=before, new=after))
        old_at, new_at = begin + len(before), start + len(after)
        delta += len(after) - len(before)
    require(source[old_at:] == result[new_at:], "resource protected suffix differs")
    gaps.append(dict(old_start=old_at, new_start=new_at, **pin(source[old_at:])))
    assertions = ["_Static_assert(sizeof(size_t)==8,\"64-bit resource arithmetic\");",
                  f"_Static_assert(sizeof({c['table_type']})==24,\"production TT entry\");",
                  f"_Static_assert(sizeof({ws}[0].{ident})>=4 && sizeof({c['joined']})>=4,\"worker count width\");"]
    proof = dict(schema=SCHEMA, family=family, input=pin(source), output=pin(result),
                 resources=profile.to_record(24), entry_cleanup=entry_cleanup,
                 spans=spans, protected_gaps=gaps, full_inverse=True,
                 target_type_assertions=assertions,
                 initialization=dict(allocator="C11 aligned_alloc", alignment_bytes=4096,
                     unit_entries=unit, fields="key=0,data=0,atomic_flag_clear_explicit relaxed",
                     partition="(entries/unit * worker_id / workers) * unit",
                     ranges=[dict(worker=r.worker, begin=r.begin, end=r.end)
                             for r in profile.init_ranges(layout)],
                     completion="main joins every initializer before board setup/UCI; GO count remains zero",
                     ordering="exclusive stores; pthread_join then later pthread_create publishes initialization",
                     learner_lifetime="unchanged process-lifetime storage; only worker id assigned at startup",
                     page_scope="4KiB base-page boundaries; no THP or NUMA-locality claim"),
                 selector="strict completed-depth greater across all workers; lowest id wins ties",
                 ownership=dict(game="existing immutable game prefix and position",
                     search="existing per-GO generation/deadline/publication",
                     worker="existing persistent record and learners; private recursive path",
                     tt="main allocation; worker-owned initialization ranges; shared search locks unchanged",
                     runtime="main-owned join handles reused only after initialization joins"),
                 runtime_qualified=False)
    require(restore_source(result, proof) == source, "resource full inverse differs")
    return result, proof


def restore_source(candidate: bytes, proof: dict) -> bytes:
    require(type(candidate) is bytes and proof.get("schema") == SCHEMA and
            pin(candidate) == proof.get("output"), "profile output identity differs")
    result = candidate
    for span in reversed(proof["spans"]):
        at, before, after = span["new_start"], span["old"].encode(), span["new"].encode()
        require(result[at:at + len(after)] == after, "profile inverse span differs")
        result = result[:at] + before + result[at + len(after):]
    require(pin(result) == proof.get("input"), "profile restored input identity differs")
    return result
