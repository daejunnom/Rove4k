"""A declared single-TU source layout, without redundant module declarations.

The readable C files retain their independently compilable API. A source package
is one translation unit: definitions can precede callers instead of carrying
both declarations and definitions. This operates only on this owned fixed API;
unexpected source shapes fail closed instead of guessing at arbitrary C syntax.
"""
import re


def stitch(sources, selected, lean=False):
    # Git may check these owned text inputs out with CRLF. Hashing remains over
    # their original bytes in build.py; assembly uses one explicit LF spelling.
    text = {name: data.decode().replace("\r\n", "\n") for name, data in sources.items()}
    normalization = {"newline_normalization": "CRLF_to_LF",
                     "normalized_inputs": [name for name, data in sources.items() if b"\r\n" in data]}
    header = text["tiny.h"]
    board, search, runtime = (text[name].replace('#include "tiny.h"', "") for name in selected[1:])
    if not lean:
        return (header + "\n" + "\n".join((board, search, runtime))).encode(), {"layout": "declared-modules", **normalization}
    globals_pattern = r"(?ms)^Entry \*table;\n.*?^Board position;\n"
    matches = list(re.finditer(globals_pattern, runtime))
    if len(matches) != 1:
        raise ValueError("expected exactly one declared runtime global block")
    globals_block = matches[0].group()
    runtime = runtime[:matches[0].start()] + runtime[matches[0].end():]
    now_pattern = r"(?m)^uint64_t now\(void\)\{[^\n]+\}\n"
    matches = list(re.finditer(now_pattern, runtime))
    if len(matches) != 1:
        raise ValueError("expected exactly one declared monotonic clock definition")
    clock = matches[0].group()
    runtime = runtime[:matches[0].start()] + runtime[matches[0].end():]
    header, externs = re.subn(r"(?m)^extern [^\n]+;\n", "", header)
    header, prototypes = re.subn(r"(?m)^(?:int|void|uint64_t) \w+\([^\n]*\);\n", "", header)
    if externs != 10 or prototypes != 11:
        raise ValueError(f"fixed API declaration count changed: {externs} externs, {prototypes} prototypes")
    result = header + "\n" + globals_block + clock + board + "\n" + search + "\n" + runtime
    return result.encode(), {"layout": "definitions-before-callers", **normalization, "removed_externs": externs,
                             "removed_prototypes": prototypes, "moved_clock_bytes": len(clock),
                             "moved_global_bytes": len(globals_block)}


def strip_dev_counters(source):
    """Remove exactly this candidate's known no-op DEV instrumentation.

    Input is the lexically compacted shipping specialization. The two standalone
    if statements exist solely for their diagnostic increments. Every other
    increment is inside a real production block, so its surrounding control flow
    remains. Build acceptance additionally requires full native byte identity
    with the unmodified shipping input; this is not an arbitrary C optimizer.
    """
    text = source.decode()
    text, definitions = re.subn(r"(?m)^#define COUNT\(w,f\) \(\(void\)0\)\n", "", text)
    for statement in ("if(bound)COUNT(w,hits);", "if(depth<=0)COUNT(w,qs);"):
        if text.count(statement) != 1:
            raise ValueError("fixed diagnostic-only conditional changed")
        text = text.replace(statement, "")
    names = ("ply_aborts", "pvs", "corr_uses", "hist_updates", "cont_updates", "corr_updates")
    for name in names:
        call = "COUNT(w," + name + ");"
        if text.count(call) != 1:
            raise ValueError("fixed diagnostic call changed: " + name)
        text = text.replace(call, "")
    if definitions != 1 or "COUNT(" in text:
        raise ValueError("unexpected remaining diagnostic macro")
    return text.encode(), {"removed_noop_counter_calls": 8, "required_native_byte_identity": True}
