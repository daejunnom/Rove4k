"""Separate D syscall-arity and terminal ownership source candidates.

Only the arguments consumed by each Linux x86-64 syscall are populated. This
changes the syscall register trace and compiler output; it makes no native-byte
identity, runtime, size or target-qualification claim. The optional immediate
terminal policy belongs to a separate TCEC-minimum contract and does not claim
the final-search-output equivalence of the parent process-owner class.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re

KIND = "D-explicit-syscall-arity-source-v1"
OWNER_SHA = "e8951daa552e01dca79214f4bc06780f2eeed8542cad4f48ab97e1ca4be359f2"
FILES = {"tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld"}
ORIGINAL = b'''static long system_call(long n,long a,long b,long c,long d,long e,long f){
    register long r10 __asm__("r10")=d,r8 __asm__("r8")=e,r9 __asm__("r9")=f;
    long result;
    __asm__ volatile("syscall":"=a"(result):"a"(n),"D"(a),"S"(b),"d"(c),"r"(r10),"r"(r8),"r"(r9):"rcx","r11","memory");
    return result;
}
#define CALL(n,a,b,c,d,e,f) system_call(n,(long)(a),(long)(b),(long)(c),(long)(d),(long)(e),(long)(f))
'''
HELPERS = b'''static long Dsc1(long n,long a){long z;__asm__ volatile("syscall":"=a"(z):"a"(n),"D"(a):"rcx","r11","memory");return z;}
static long Dsc2(long n,long a,long b){long z;__asm__ volatile("syscall":"=a"(z):"a"(n),"D"(a),"S"(b):"rcx","r11","memory");return z;}
static long Dsc3(long n,long a,long b,long c){long z;__asm__ volatile("syscall":"=a"(z):"a"(n),"D"(a),"S"(b),"d"(c):"rcx","r11","memory");return z;}
static long Dsc4(long n,long a,long b,long c,long d){register long r10 __asm__("r10")=d;long z;__asm__ volatile("syscall":"=a"(z):"a"(n),"D"(a),"S"(b),"d"(c),"r"(r10):"rcx","r11","memory");return z;}
static long Dsc6(long n,long a,long b,long c,long d,long e,long f){register long r10 __asm__("r10")=d,r8 __asm__("r8")=e,r9 __asm__("r9")=f;long z;__asm__ volatile("syscall":"=a"(z):"a"(n),"D"(a),"S"(b),"d"(c),"r"(r10),"r"(r8),"r"(r9):"rcx","r11","memory");return z;}
'''
CALLS = (
    ("exit-group-one-argument", b"CALL(231,2,0,0,0,0,0)", 1, ("231", "2")),
    ("anonymous-map-six-arguments", b"CALL(9,0,n,3,0x22,-1,0)", 6, ("9", "0", "n", "3", "0x22", "-1", "0")),
    ("futex-wait-including-null-timeout", b"CALL(202,address,private?128:0,value,0,0,0)", 4, ("202", "address", "private?128:0", "value", "0")),
    ("futex-wake-three-arguments", b"CALL(202,address,129,INT_MAX,0,0,0)", 3, ("202", "address", "129", "INT_MAX")),
    ("monotonic-clock-two-arguments", b"CALL(228,1,t,0,0,0,0)", 2, ("228", "1", "t")),
    ("complete-write-three-arguments", b"CALL(1,1,s,n,0,0,0)", 3, ("1", "1", "s", "n")),
    ("buffered-read-three-arguments", b"CALL(0,0,bytes,sizeof bytes,0,0,0)", 3, ("0", "0", "bytes", "sizeof bytes")),
    ("stack-guard-three-arguments", b"CALL(10,stack,4096,0,0,0,0)", 3, ("10", "stack", "4096", "0")),
)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def inventory(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def _owner(files, owner, publication, owner_proof):
    path = Path(owner.__file__)
    if path.parts[-4:] != ("engines", "experiments", "tiny-d-submission", "process_owner.py"):
        raise ValueError("genuine frozen D owner module required")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in raw or pin(raw)["sha256"] != OWNER_SHA:
        raise ValueError("D owner module identity differs")
    if (not isinstance(files, dict) or set(files) != FILES or
            any(not isinstance(d, bytes) or b"\r" in d for d in files.values())):
        raise ValueError("normalized complete six-file D owner source required")
    original = owner.restore(files, owner_proof, publication)
    reproduced, proof = owner.transform(original, publication, owner_proof["publication"])
    if reproduced != files or proof != owner_proof:
        raise ValueError("complete canonical D owner proof differs")
    if any(re.search(rb"\b" + name + rb"\b", data) for data in files.values()
           for name in (b"Dsc1", b"Dsc2", b"Dsc3", b"Dsc4", b"Dsc6")):
        raise ValueError("syscall helper identifier capture")
    return pin(raw)


def _roles(*, noinline_wake, immediate_exit, owner):
    roles = [("replace-seven-register-wrapper", ORIGINAL, HELPERS)]
    for role, old, arity, arguments in CALLS:
        new = ("Dsc" + str(arity) + "(" + arguments[0] + "," +
               ",".join("(long)(" + arg + ")" for arg in arguments[1:]) + ")").encode()
        roles.append((role, old, new))
    if noinline_wake:
        roles.append(("centralize-futex-wake-call", b"static void wake(atomic_int *address){",
                      b"static __attribute__((noinline)) void wake(atomic_int *address){"))
    if immediate_exit:
        roles.append(("TCEC-terminal-loop-returns-directly-to-exit-group", owner.FINAL_WAIT,
                      b"    }\nshutdown:\n"))
    return roles


def _project(source, roles):
    edits = []
    for role, before, after in roles:
        if source.count(before) != 1:
            raise ValueError("unique D arity role required: " + role)
        edits.append((source.index(before), role, before, after))
    result, records, gaps, cursor, target = [], [], [], 0, 0
    for begin, role, before, after in sorted(edits):
        if begin < cursor:
            raise ValueError("overlapping D arity source roles")
        gap = source[cursor:begin]
        result.extend((gap, after)); gaps.append(pin(gap)); target += len(gap)
        records.append(dict(role=role, source=begin, target=target,
                            before=before.decode(), after=after.decode()))
        cursor = begin + len(before); target += len(after)
    result.append(source[cursor:]); gaps.append(pin(source[cursor:]))
    output = b"".join(result)
    if b"CALL(" in output or b"system_call(" in output:
        raise ValueError("unclassified legacy D syscall call remains")
    return output, dict(input=pin(source), output=pin(output), edits=records, protected_gaps=gaps)


def _restore(output, record):
    if pin(output) != record["output"]:
        raise ValueError("D arity source output differs")
    parts, gaps, cursor = [], [], 0
    for row in record["edits"]:
        begin, after = row["target"], row["after"].encode()
        if begin < cursor or output[begin:begin + len(after)] != after:
            raise ValueError("D arity inverse role differs")
        gap = output[cursor:begin]
        parts.extend((gap, row["before"].encode())); gaps.append(pin(gap))
        cursor = begin + len(after)
    parts.append(output[cursor:]); gaps.append(pin(output[cursor:]))
    original = b"".join(parts)
    if pin(original) != record["input"] or gaps != record["protected_gaps"]:
        raise ValueError("D arity inverse or protected complement differs")
    return original


def _proof(files, result, edit, authority, owner_proof, noinline_wake, immediate_exit):
    return dict(kind=KIND, owner_authority=authority, owner=deepcopy(owner_proof),
        input=inventory(files), output=inventory(result), source_edits={"runtime.c": edit},
        noinline_wake=noinline_wake, immediate_exit=immediate_exit,
        ownership_policy="TCEC-minimum-immediate-process-exit" if immediate_exit else "final-wait-equivalent-output",
        last_search_output_required=not immediate_exit,
        active_terminal_bestmove_count=[0, 1] if immediate_exit else [1],
        idle_terminal_bestmove_count=[0],
        contracts=dict(syscall_abi="Linux x86-64 required arguments, return value, rcx/r11/memory clobbers retained",
            futex_wait="fourth argument r10 remains explicit NULL timeout; private/shared selector unchanged",
            allocation="six mmap arguments, anonymous private flags and error check retained",
            output="complete write loop, EINTR retry and abort path retained",
            terminal="pinned _start syscall231 terminates engine TGID naturally",
            normal_position_go="all startup/reuse/pending/output publication fences retained",
            trace="unused syscall register values may differ",
            final_search="0 or 1 complete legal bestmove; no final wait on terminal quit/EOF" if immediate_exit else
                         "main stops and waits pending acquire before returning; result completes first"),
        board_search_learners_changed=False, source_authority_changed=False,
        native_identity_claimed=False, runtime_qualified=False, size_measured=False,
        external_termination_counts_as_success=False, selected=False)


def transform(files, owner, publication, owner_proof, *, noinline_wake=False, immediate_exit=False):
    if type(noinline_wake) is not bool or type(immediate_exit) is not bool:
        raise ValueError("explicit boolean D arity candidate options required")
    authority = _owner(files, owner, publication, owner_proof)
    result = dict(files)
    result["runtime.c"], edit = _project(files["runtime.c"], _roles(
        noinline_wake=noinline_wake, immediate_exit=immediate_exit, owner=owner))
    proof = _proof(files, result, edit, authority, owner_proof, noinline_wake, immediate_exit)
    if restore(result, proof, owner, publication) != files:
        raise ValueError("complete D arity source inverse differs")
    return result, proof


def restore(files, proof, owner, publication):
    if proof.get("kind") != KIND or inventory(files) != proof.get("output") or set(proof.get("source_edits", {})) != {"runtime.c"}:
        raise ValueError("unknown or incomplete D arity proof")
    options = {name: proof[name] for name in ("noinline_wake", "immediate_exit")}
    if any(type(value) is not bool for value in options.values()):
        raise ValueError("nonboolean D arity proof options")
    original = dict(files)
    original["runtime.c"] = _restore(files["runtime.c"], proof["source_edits"]["runtime.c"])
    authority = _owner(original, owner, publication, proof["owner"])
    output, edit = _project(original["runtime.c"], _roles(owner=owner, **options))
    expected = dict(original); expected["runtime.c"] = output
    expected_proof = _proof(original, expected, edit, authority, proof["owner"], **options)
    if files != expected or proof != expected_proof:
        raise ValueError("D arity exact canonical role/proof replay differs")
    return original
