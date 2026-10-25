"""Unselected D input readers with explicit, separate acceptance domains.

The one-byte reader accepts valid non-NUL UCI lines up to 32767 bytes and a
complete last command at EOF. Every store remains bounded. It does not retain
the old malformed-line rejection/drain contract. Its read syscall count and
timing differ. The cached-common-exit alternative retains the original guards
and drain behavior. Neither spelling claims native identity or qualification.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

KIND = "D-scoped-input-reader-source-v1"
ARITY_SHA = "9c294abe9c26747cbe188d0bc5c86ff450656870e213664802a4fd1dae8163fd"
MODES = {"one-byte-valid", "cached-common-exit"}
FILES = {"tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld"}
ORIGINAL = b'''static int read_line(char *s){
    static char bytes[4096];static int at,length;int n=0,bad=0;
    for(;;){
        if(at==length){long got=Dsc3(0,(long)(0),(long)(bytes),(long)(sizeof bytes));if(got==-4)continue;if(got<0)abort();at=0;length=(int)got;if(!got){s[n]=0;return n?!bad:-1;}}
        int c=(unsigned char)bytes[at++];if(c=='\\n')break;
        if(!c||n==32767)bad=1;else s[n++]=(char)c;
    }
    s[n]=0;return !bad;
}
'''
ONE_BYTE = b'''static int read_line(char *s){
    int n=0;char c;long got;
    for(;;){
        got=Dsc3(0,(long)(0),(long)(&c),(long)(1));
        if(got==-4)continue;
        if(got<=0){if(got<0)abort();break;}
        if(c=='\\n')break;
        if(n==32767){s[n]=0;return 0;}
        s[n++]=c;
    }
    s[n]=0;return got||n?1:-1;
}
'''
CACHED = ORIGINAL.replace(b"if(!got){s[n]=0;return n?!bad:-1;}", b"if(!got)break;").replace(
    b"    s[n]=0;return !bad;\n", b"    s[n]=0;return !length&&!n?-1:!bad;\n")


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def inventory(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def _admit(files, arity, owner, publication, arity_proof):
    path = Path(arity.__file__)
    if path.parts[-4:] != ("engines", "experiments", "tiny-d-submission", "syscall_arity.py"):
        raise ValueError("genuine frozen D syscall-arity module required")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in raw or pin(raw)["sha256"] != ARITY_SHA:
        raise ValueError("D syscall-arity authority differs")
    if (not isinstance(files, dict) or set(files) != FILES or
            any(not isinstance(d, bytes) or b"\r" in d for d in files.values())):
        raise ValueError("normalized complete six-file D arity source required")
    original = arity.restore(files, arity_proof, owner, publication)
    reproduced, proof = arity.transform(original, owner, publication, arity_proof["owner"],
        noinline_wake=arity_proof["noinline_wake"], immediate_exit=arity_proof["immediate_exit"])
    if reproduced != files or proof != arity_proof:
        raise ValueError("complete canonical D syscall-arity proof differs")
    if files["runtime.c"].count(ORIGINAL) != 1:
        raise ValueError("exact original arity read_line required")
    return pin(raw)


def _project(source, mode):
    if mode not in MODES or source.count(ORIGINAL) != 1:
        raise ValueError("unique known D input-reader source role required")
    after = ONE_BYTE if mode == "one-byte-valid" else CACHED
    begin = source.index(ORIGINAL); end = begin + len(ORIGINAL)
    output = source[:begin] + after + source[end:]
    return output, dict(input=pin(source), output=pin(output),
        role=mode, begin=begin, before=ORIGINAL.decode(), after=after.decode(),
        protected_gaps=[pin(source[:begin]), pin(source[end:])])


def _restore(output, record):
    if pin(output) != record["output"]:
        raise ValueError("D input-reader runtime output differs")
    begin, after = record["begin"], record["after"].encode()
    if type(begin) is not int or begin < 0 or output[begin:begin + len(after)] != after:
        raise ValueError("D input-reader inverse role differs")
    prefix, suffix = output[:begin], output[begin + len(after):]
    original = prefix + record["before"].encode() + suffix
    if pin(original) != record["input"] or [pin(prefix), pin(suffix)] != record["protected_gaps"]:
        raise ValueError("D input-reader inverse or protected complement differs")
    return original


def _proof(files, result, edit, authority, arity_proof, mode):
    valid = mode == "one-byte-valid"
    return dict(kind=KIND, mode=mode, arity_authority=authority, arity=deepcopy(arity_proof),
        input=inventory(files), output=inventory(result), source_edits={"runtime.c": edit},
        input_contract="TCEC-valid-non-NUL-lines-at-most-32767-bytes" if valid else "original-malformed-line-guards-and-drain",
        original_malformed_line_contract_retained=not valid,
        ownership_policy=arity_proof["ownership_policy"],
        last_search_output_required=arity_proof["last_search_output_required"],
        active_terminal_bestmove_count=deepcopy(arity_proof["active_terminal_bestmove_count"]),
        idle_terminal_bestmove_count=deepcopy(arity_proof["idle_terminal_bestmove_count"]),
        contracts=dict(buffer="caller has 32768 writable bytes; payload n never exceeds32767; terminator stays in range",
            complete_partial_EOF="nonempty last command is returned once, next EOF returns-1",
            partial_coalesced_reads="read boundaries do not change valid command contents or order",
            newline="LF ends one command, empty LF line succeeds, terminator replaces LF",
            interruption="EINTR retries; other negative read results use the unchanged own abort",
            malformed="NUL/oversize rejection and drain are outside this candidate acceptance domain" if valid else
                      "NUL marks bad; overflow marks bad and drains through LF; EOF return preserves original semantics",
            syscall_trace="one read per byte, including LF; no private input cache" if valid else "same4096-byte cache and read arguments",
            normal_engine="position/go/pending/publication, NBRQ, search and learners are unchanged"),
        other_sources_unchanged=True, native_identity_claimed=False, runtime_qualified=False,
        size_measured=False, selected=False)


def transform(files, arity, owner, publication, arity_proof, *, mode="one-byte-valid"):
    if not isinstance(mode, str) or mode not in MODES:
        raise ValueError("explicit known D input-reader mode required")
    authority = _admit(files, arity, owner, publication, arity_proof)
    result = dict(files); result["runtime.c"], edit = _project(files["runtime.c"], mode)
    proof = _proof(files, result, edit, authority, arity_proof, mode)
    if restore(result, proof, arity, owner, publication) != files:
        raise ValueError("complete D input-reader source inverse differs")
    return result, proof


def restore(files, proof, arity, owner, publication):
    if (proof.get("kind") != KIND or proof.get("mode") not in MODES or
            inventory(files) != proof.get("output") or set(proof.get("source_edits", {})) != {"runtime.c"}):
        raise ValueError("unknown or incomplete D input-reader proof")
    original = dict(files)
    original["runtime.c"] = _restore(files["runtime.c"], proof["source_edits"]["runtime.c"])
    authority = _admit(original, arity, owner, publication, proof["arity"])
    output, edit = _project(original["runtime.c"], proof["mode"])
    expected = dict(original); expected["runtime.c"] = output
    expected_proof = _proof(original, expected, edit, authority, proof["arity"], proof["mode"])
    if files != expected or proof != expected_proof:
        raise ValueError("D input-reader exact role/proof replay differs")
    return original
