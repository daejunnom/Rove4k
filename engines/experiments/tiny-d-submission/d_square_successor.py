"""One closed D source projection for ordered 0x88 square successors.

Only the dead-material loop and the scalar walk square-loop opening change.
This module performs no I/O and makes no native, rules, runtime or size claim.
"""
from hashlib import sha256
import json
import re


KIND = "D-closed-0x88-square-successor-v1"
INPUTS = {
    "tiny.h": (2970, "fac1d3f165d01e01efc7c6a2f89ee8767661e6d3aad0478febad21fa3814bf9e"),
    "board.c": (10361, "ecd9d567a1f6c5ee185012a70915ab63c741bbf68b7a294d1604334c59db4e62"),
    "search.c": (5909, "73ba9dbdf23906cff90e6098ee0903bdf38b4f95e826871042281c9894de6344"),
    "runtime.c": (15515, "4ed5d28d3bdec003dc556ce3265150ab680af511481c22839c86e1cd05e9c81e"),
    "start.S": (778, "c2de2a81692227a1b02d2bc7633fc23f7416074f2b020c406ee464b0980ab28d"),
    "image.ld": (446, "38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b"),
}
INPUTS = {name: {"bytes": size, "sha256": digest} for name, (size, digest) in INPUTS.items()}
DEAD_BEFORE = b"for(int q=0;q<128;q++)if(!(q&0x88)){"
DEAD_AFTER = b"for(int q=0;q<128;q=q+9&~8){"
WALK_BEFORE = b"    for(int from=0;from<128;from++){\n        if(from&0x88){from+=7;continue;}\n"
WALK_AFTER = b"    for(int from=0;from<128;from=from+9&~8){\n"
SPANS = (
    (1334, 1370, DEAD_BEFORE, DEAD_AFTER, "dead-onboard-square-loop"),
    (6302, 6380, WALK_BEFORE, WALK_AFTER, "scalar-walk-onboard-square-loop"),
)
_WORD = re.compile(rb"[A-Za-z_][A-Za-z_0-9]*")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "immutable bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def inventory(files):
    require(type(files) is dict and all(type(n) is str for n in files), "explicit named source mapping required")
    return {name: pin(data) for name, data in sorted(files.items())}


def _json(value):
    def check(item):
        if type(item) is dict:
            require(all(type(key) is str for key in item), "proof keys must be strings")
            for child in item.values():
                check(child)
        elif type(item) is list:
            for child in item:
                check(child)
        else:
            require(type(item) in (str, int, bool, type(None)), "canonical proof value type required")
    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _same(left, right):
    return _json(left) == _json(right)


def _mask(data):
    """Preserve offsets while hiding quoted literals and C comments."""
    require(type(data) is bytes and b"\0" not in data, "non-NUL source bytes required")
    result = bytearray(data)
    at = 0
    while at < len(data):
        begin = at
        if data[at:at + 2] == b"//":
            end = data.find(b"\n", at + 2)
            at = len(data) if end < 0 else end
        elif data[at:at + 2] == b"/*":
            end = data.find(b"*/", at + 2)
            require(end >= 0, "unterminated source comment")
            at = end + 2
        elif data[at] in (34, 39):
            quote = data[at]
            at += 1
            while at < len(data) and data[at] != quote:
                require(data[at] not in (10, 13), "unspliced newline in source literal")
                if data[at] == 92:
                    at += 1
                    require(at < len(data) and data[at] not in (10, 13), "unsupported source literal splice")
                at += 1
            require(at < len(data), "unterminated source literal")
            at += 1
        else:
            at += 1
            continue
        for index in range(begin, at):
            if result[index] not in (10, 13):
                result[index] = 32
    return bytes(result)


def _block_end(masked, opening):
    require(type(opening) is int and 0 <= opening < len(masked) and masked[opening:opening + 1] == b"{",
            "exact block opening required")
    depth = 0
    for at in range(opening, len(masked)):
        if masked[at] == 123:
            depth += 1
        elif masked[at] == 125:
            depth -= 1
            if depth == 0:
                return at + 1
    raise ValueError("unclosed source block")


def _index_reads(body, name, origin):
    """A closed-source guard against index writes, shadows and address escape."""
    code = _mask(body)
    require(type(name) is bytes and re.fullmatch(rb"[A-Za-z_][A-Za-z_0-9]*", name), "index identifier required")
    matches = list(re.finditer(rb"\b" + name + rb"\b", code))
    require(matches, "retained body must read its square index")
    for match in matches:
        before, after = code[:match.start()].rstrip(), code[match.end():].lstrip()
        require(not before.endswith((b"++", b"--", b"&")) and not after.startswith((b"++", b"--")),
                "square index write or address escape")
        require(re.match(rb"(?:<<|>>|[+*/%&|^-])?=(?!=)", after) is None,
                "square index assignment in retained body")
        require(re.search(rb"\b(?:int|long|short|char|unsigned|signed)\s+$", before) is None,
                "square index shadow in retained body")
    require(re.search(rb"\b(?:goto|setjmp|longjmp)\b", code) is None, "unsupported nonlocal retained control")
    return [origin + match.start() for match in matches]


def _controls(body, origin):
    code = _mask(body)
    return {word: [origin + match.start() for match in re.finditer(rb"\b" + word.encode() + rb"\b", code)]
            for word in ("continue", "break", "return")}


def _region(data, begin, end):
    require(type(begin) is int and type(end) is int and 0 <= begin < end <= len(data), "ordered source region required")
    return {"begin": begin, "end": end, **pin(data[begin:end])}


def _scope(data):
    masked = _mask(data)
    require(data.count(DEAD_BEFORE) == 1 and data.count(WALK_BEFORE) == 2, "exact dead/dual-walk opening cohort required")
    require(data.find(WALK_BEFORE) == 4657, "HQ/DEV walk opening differs")
    for begin, end, before, _, _ in SPANS:
        require(data[begin:end] == before and masked[begin:end] == before, "target opening bytes or lexical role differ")
    require(data[1287:1312] == b"int dead(const Board *p){", "dead function boundary differs")
    require(data[4529:4545] == b"#if D_HQ || DEV\n" and data[6225:6231] == b"#else\n"
            and data[7562:7569] == b"#endif\n" and data[7879:7887] == b"#if DEV\n", "scalar/HQ/DEV branch boundary differs")
    dead_end = _block_end(masked, 1369)
    walk_open = 6302 + WALK_BEFORE.index(b"{")
    walk_end = _block_end(masked, walk_open)
    require(dead_end == 1621 and walk_end == 7545, "retained loop extent differs")
    dead, walk = data[1370:dead_end], data[6380:walk_end]
    dead_controls, walk_controls = _controls(dead, 1370), _controls(walk, 6380)
    require({key: len(value) for key, value in dead_controls.items()} == {"continue": 0, "break": 0, "return": 4},
            "dead retained control inventory differs")
    require(walk_controls == {"continue": [6429], "break": [7054, 7162], "return": [6980]},
            "scalar retained control inventory differs")
    ray = masked.find(b"for(int to=from+step;!(to&0x88);to+=step){", 6380)
    require(ray >= 0, "nested destination-ray loop differs")
    ray_open = masked.find(b"{", ray)
    ray_end = _block_end(masked, ray_open)
    require(all(ray_open < at < ray_end for at in walk_controls["break"] + walk_controls["return"])
            and walk_controls["continue"][0] < ray, "retained control targets differ")
    require(data[7550:7559] == b"return n;", "scalar final return boundary differs")
    return {
        "dead": {"body_and_close": _region(data, 1370, dead_end),
                 "index_reads": _index_reads(dead, b"q", 1370), "controls": dead_controls,
                 "index_writes_or_address_escape": False, "early_return_order_preserved": True},
        "scalar_walk": {"body_and_close": _region(data, 6380, walk_end),
                        "index_reads": _index_reads(walk, b"from", 6380), "controls": walk_controls,
                        "index_writes_or_address_escape": False,
                        "continue_target": "outer square loop update",
                        "break_target": "unchanged nested destination-ray loop",
                        "return_target": "unchanged walk function", "ray_loop": _region(data, ray, ray_end)},
        "HQ_DEV_branch_unchanged": _region(data, 4529, 6231),
        "scalar_signature_unchanged": _region(data, 6231, 6302),
        "later_DEV_block_unchanged": _region(data, 7879, len(data)),
        "all_128_entry_DEV_validation_retained": True,
    }


def _witness():
    dead = [value for value in range(128) if not value & 0x88]
    walk, value = [], 0
    while value < 128:
        if value & 0x88:
            value += 7
        else:
            walk.append(value)
        value += 1
    require(value == 128, "old scalar terminal differs")
    successor, steps, value = [], [], 0
    while value < 128:
        require(0 <= value <= 119 and not value & 0x88 and len(successor) < 64, "successor escaped finite int domain")
        successor.append(value)
        next_value = (value + 9) & ~8
        steps.append([value, next_value])
        require(value < next_value <= 128, "successor is not strictly increasing")
        value = next_value
    require(dead == walk == successor and len(successor) == 64 and value == 128, "meaningful square order differs")
    return {"old_dead_visits": dead, "old_scalar_walk_visits": walk, "successor_visits": successor,
            "successor_steps": steps, "visits": 64, "exit": 128, "largest_addition": max(v + 9 for v in successor),
            "step_expression": "index=((index+9)&~8)", "padding_mask": 8,
            "continue_reaches_same_next_meaningful_square": True, "same_order": True,
            "int_addition_overflow": False, "terminal_bit_7_retained": True}


def _project(data):
    pieces, edits, gaps, at, target = [], [], [], 0, 0
    for begin, end, before, after, role in SPANS:
        require(at <= begin < end <= len(data) and data[begin:end] == before, "closed edit interval differs")
        gap = data[at:begin]
        pieces.extend((gap, after)); gaps.append(pin(gap)); target += len(gap)
        edits.append({"begin": begin, "end": end, "target": target, "role": role,
                      "before": before.decode("ascii"), "after": after.decode("ascii")})
        target += len(after); at = end
    pieces.append(data[at:]); gaps.append(pin(data[at:]))
    return b"".join(pieces), {"edits": edits, "protected_gaps": gaps}


def _inverse(data):
    parts, at, shift = [], 0, 0
    for begin, end, before, after, _ in SPANS:
        target = begin + shift
        require(at <= target and data[target:target + len(after)] == after, "successor inverse edit differs")
        parts.extend((data[at:target], before)); at = target + len(after)
        shift += len(after) - (end - begin)
    parts.append(data[at:])
    return b"".join(parts)


def transform(files):
    require(inventory(files) == INPUTS,
            "exact six-file no-TID D input cohort required")
    board = files["board.c"]
    scope, witness = _scope(board), _witness()
    projected, edit = _project(board)
    require(_inverse(projected) == board, "complete square-successor inverse differs")
    output = dict(files, **{"board.c": projected})
    proof = {"kind": KIND, "input": inventory(files), "output": inventory(output), "projection": edit,
             "scope": scope, "witness": witness, "full_inverse": True,
             "unchanged_files": sorted(set(files) - {"board.c"}),
             "source_contract": "same ordered meaningful square entries; retained body bytes and control targets",
             "native_identity_claimed": False, "semantics_qualified": False, "rules_qualified": False,
             "runtime_qualified": False, "size_qualified": False, "selected": False}
    return output, proof


def restore(files, proof):
    require(type(files) is dict and set(files) == set(INPUTS), "exact six output file roles required")
    require(type(proof) is dict and _same(proof.get("output"), inventory(files)), "square-successor output or proof differs")
    original = dict(files, **{"board.c": _inverse(files["board.c"])})
    expected, canonical = transform(original)
    require(expected == files and _same(canonical, proof), "canonical square-successor proof/complement differs")
    return original
