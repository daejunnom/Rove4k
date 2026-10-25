"""One frozen, closed-TU D declaration cleanup; no generic dead-code claim.

Only the independently reviewed 31 spans are removed from one exact shipping
source. All remaining bytes, assembly, entry roots and support definitions are
retained. Native identity and package cost are separate driver requirements.
Importing this module performs no I/O and starts no tools.
"""
from hashlib import sha256
import re

KIND = "D-closed-TU-declaration-cleanup-v1"
INPUTS = {
    "main.c": {"bytes": 16986, "sha256": "c0dbf073d4690013f2abbd3529e78de27ac72bdc21f74daf35437fb3d64751af"},
    "start.S": {"bytes": 614, "sha256": "40ea09083dbe07feba76fba528b017f9a7dd4eecda7e857deeb874e1da1cddaa"},
    "image.ld": {"bytes": 446, "sha256": "38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b"},
}
SPANS = (
    (139,177,"__fsid_t typedef"), (177,200,"__timer_t typedef"),
    (200,223,"__caddr_t typedef"), (350,538,"max_align_t typedef"),
    (656,691,"atomic_thread_fence declaration"),
    (691,726,"atomic_signal_fence declaration"), (726,764,"W flag typedef"),
    (764,815,"atomic_flag_test_and_set declaration"),
    (815,877,"atomic_flag_test_and_set_explicit declaration"),
    (877,920,"atomic_flag_clear declaration"),
    (920,974,"atomic_flag_clear_explicit declaration"),
    (974,1007,"memcpy forward"), (1007,1032,"memset forward"),
    (1032,1070,"memcmp forward"), (1070,1092,"strlen declaration"),
    (1092,1128,"strcmp declaration"), (1128,1167,"strncmp declaration"),
    (1167,1196,"strchr declaration"), (1196,1233,"strstr declaration"),
    (1233,1273,"strtok_r declaration"), (1273,1309,"strtol declaration"),
    (1564,1588,"X forward"), (1588,1609,"gen forward"),
    (1633,1652,"dead forward"), (1652,1667,"start forward"),
    (1667,1676,"mix forward"), (1676,1695,"value forward"),
    (2096,2111,"workers extern"), (2140,2151,"position extern"),
    (2201,2225,"think forward"), (10702,10825,"uncalled memcmp body"),
)
FORWARDS = (
    b"int make(const y*,H,y*);", b"static int walk(const y*,H*,int,int);",
    b"g now(void);", b"_Noreturn void abort(void);",
    b"extern long spawn(void(*)(void*),void*,void*,int*);",
)
ROOTS = ("main", "work", "memcpy", "memset", "abort")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(isinstance(data, bytes), "immutable source bytes required")
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def pins(files):
    require(isinstance(files, dict) and all(isinstance(n, str) for n in files),
            "named immutable source mapping required")
    return {n: pin(d) for n, d in sorted(files.items())}


def _balanced(data, begin, opening, closing):
    require(data[begin:begin+1] == opening, "balanced region opening differs")
    level, quote, escaped = 0, None, False
    for i in range(begin, len(data)):
        char = data[i:i+1]
        if quote:
            if escaped:
                escaped = False
            elif char == b"\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in (b"'", b'"'):
            quote = char
        elif char == opening:
            level += 1
        elif char == closing:
            level -= 1
            if not level:
                return i+1
    raise ValueError("unterminated protected source region")


def retention(files):
    """Record the actual untouched C root bodies, assertions and inline ASM."""
    data = files["main.c"]
    bodies = {}
    for name in ROOTS:
        pattern = rb"\b" + name.encode() + rb"\([^;{}]*\)\s*\{"
        matches = list(re.finditer(pattern, data))
        require(len(matches) == 1, "unique protected definition required: " + name)
        row = matches[0]
        end = _balanced(data, row.end()-1, b"{", b"}")
        bodies[name] = pin(data[row.start():end])
    forwards = {}
    for text in FORWARDS:
        require(data.count(text) == 1, "necessary forward declaration differs")
        forwards[text.decode()] = pin(text)
    regions = {}
    for token in (b"__asm__", b"_Static_assert"):
        rows = []
        for match in re.finditer(rb"\b" + token + rb"\b", data):
            start = data.find(b"(", match.end())
            require(start >= 0, "protected expression opening absent")
            end = _balanced(data, start, b"(", b")")
            rows.append(pin(data[match.start():end]))
        require(rows, "protected ASM/assertion category absent")
        regions[token.decode()] = rows
    require(files["start.S"].count(b"call main") == 1 and
            files["start.S"].count(b"call *%rax") == 1 and
            files["start.S"].count(b".global _start") == 1 and
            files["start.S"].count(b".global spawn") == 1,
            "entry/indirect-worker ASM roots differ")
    return dict(definitions=bodies, necessary_forwards=forwards, regions=regions,
                assembler=pin(files["start.S"]), linker=pin(files["image.ld"]),
                roots=["_start", "main", "spawn", "address-taken work"],
                compiler_support=["memcpy", "memset", "_Noreturn abort"])


def _project(data, spans):
    """Remove sorted exact spans and retain every gap for a complete inverse."""
    parts, edits, gaps = [], [], []
    at, target = 0, 0
    require(isinstance(spans, (tuple, list)), "finite span sequence required")
    for begin, end, role in spans:
        require(type(begin) is int and type(end) is int and
                at <= begin < end <= len(data) and isinstance(role, str),
                "sorted nonoverlapping in-bounds cleanup spans required")
        gap = data[at:begin]
        parts.append(gap); gaps.append(pin(gap)); target += len(gap)
        edits.append(dict(begin=begin, end=end, target=target, role=role,
                          before=data[begin:end].decode("ascii")))
        at = end
    parts.append(data[at:]); gaps.append(pin(data[at:]))
    output = b"".join(parts)
    return output, dict(input=pin(data), output=pin(output), edits=edits, gaps=gaps)


def _restore(output, proof):
    require(pin(output) == proof["output"], "cleanup output pin differs")
    parts, gaps = [], []
    at, original_at = 0, 0
    for row in proof["edits"]:
        target = row["target"]
        require(type(target) is int and at <= target <= len(output),
                "cleanup inverse target differs")
        gap = output[at:target]
        before = row["before"].encode("ascii")
        require(row["begin"] == original_at + len(gap) and
                row["end"] == row["begin"] + len(before) and before,
                "cleanup inverse source offsets differ")
        parts.extend((gap, before)); gaps.append(pin(gap))
        original_at = row["end"]; at = target
    parts.append(output[at:]); gaps.append(pin(output[at:]))
    original = b"".join(parts)
    require(pin(original) == proof["input"] and gaps == proof["gaps"],
            "cleanup inverse or protected complement differs")
    return original


def transform(files):
    require(pins(files) == INPUTS, "exact frozen c0dbf073 D shipping source required")
    protected = retention(files)
    output, edit = _project(files["main.c"], SPANS)
    require(len(SPANS) == 31 and len(files["main.c"])-len(output) == 1205,
            "reviewed 31-span cleanup geometry differs")
    result = {**files, "main.c": output}
    require(retention(result) == protected, "ASM/root/support/assert retention differs")
    proof = dict(kind=KIND, input=pins(files), output=pins(result), edit=edit,
                 removed_items=31, removed_raw_bytes=1205, retained=protected,
                 scope="one frozen combined C TU; declarations and one uncalled body only",
                 native_identity_required=True, runtime_qualified=False, selected=False)
    require(_restore(output, edit) == files["main.c"], "complete cleanup inverse differs")
    return result, proof


def restore(files, proof):
    require(proof.get("kind") == KIND and pins(files) == proof["output"],
            "closed-TU cleanup proof/output differs")
    original = {**files, "main.c": _restore(files["main.c"], proof["edit"])}
    regenerated, expected = transform(original)
    require(regenerated == files and expected == proof,
            "closed-TU reviewed spans or full proof replay differs")
    return original
