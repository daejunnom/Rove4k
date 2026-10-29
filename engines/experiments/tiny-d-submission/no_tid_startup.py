"""Two frozen-source clone startup candidates, separate from production.

The persistent worker's logical id, guard page, stack and TT/publication
barriers remain intact. Kernel TID publication/clear-on-exit is unused in
this exact process-owner class. The optional tail has an explicit never-
returning worker contract and preserves the SysV callback entry alignment.
No import-time I/O, command execution, native waiver or selection occurs.
"""
from hashlib import sha256
import re

KINDS = ("D-no-TID-clone-startup-v1", "D-no-TID-nonreturning-callback-startup-v1")
INPUTS = {
    "tiny.h": {"bytes":2970,"sha256":"fac1d3f165d01e01efc7c6a2f89ee8767661e6d3aad0478febad21fa3814bf9e"},
    "board.c": {"bytes":10361,"sha256":"ecd9d567a1f6c5ee185012a70915ab63c741bbf68b7a294d1604334c59db4e62"},
    "search.c": {"bytes":5909,"sha256":"73ba9dbdf23906cff90e6098ee0903bdf38b4f95e826871042281c9894de6344"},
    "runtime.c": {"bytes":15555,"sha256":"0d80984d9bbb32969eb1c6ee76105a3742c09d7baa0a679195dde573e3aa183e"},
    "start.S": {"bytes":845,"sha256":"4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b"},
    "image.ld": {"bytes":446,"sha256":"38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b"},
}
PROTOTYPE = b"extern long spawn(void (*)(void *),void *,void *,int *);"
PROTOTYPE3 = b"extern long spawn(void (*)(void *),void *,void *);"
SPAWN_CALL = b"spawn(work,workers+created,stack+1048576+4096,(int *)(ids+created))"
SPAWN_CALL3 = b"spawn(work,workers+created,stack+1048576+4096)"
COMMENT = b"""/* long spawn(void (*fn)(void *), void *arg, void *stack_top, int *tid);
 * CLONE_PARENT_SETTID publishes tid before the parent returns. The kernel
 * clears it and performs a shared futex wake on thread exit. No TLS is used. */"""
COMMENT3 = b"""/* long spawn(void (*fn)(void *), void *arg, void *stack_top);
 * No kernel TID/TLS argument is requested. A returning callback exits the
 * thread. Only the fixed persistent work callback is passed by this class. */"""
COMMENT_TAIL = b"""/* long spawn(void (*fn)(void *), void *arg, void *stack_top);
 * Only the fixed _Noreturn work callback is passed. Its unused return slot
 * preserves SysV entry RSP modulo16=8. No kernel TID/TLS argument is used. */"""
UNUSED_REGISTERS = b"    mov %rcx,%rdx\n    mov %rcx,%r10\n    xor %r8d,%r8d\n"
CALLBACK = b"""    pop %rax
    pop %rdi
    call *%rax
    xor %edi,%edi
    mov $60,%eax
    syscall
    ud2
"""
TAIL = b"""    pop %rax
    mov (%rsp),%rdi
    jmp *%rax
"""


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(isinstance(data, bytes), "immutable actual source bytes required")
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def pins(files):
    require(isinstance(files, dict) and all(isinstance(n,str) for n in files),
            "complete named source mapping required")
    return {n:pin(d) for n,d in sorted(files.items())}


def _project(data, roles):
    located=[]
    for role,before,after in roles:
        require(data.count(before)==1,"unique exact startup source role required: "+role)
        located.append((data.index(before),role,before,after))
    parts,edits,gaps=[],[],[];at=target=0
    for begin,role,before,after in sorted(located):
        require(begin>=at,"nonoverlapping startup roles required")
        gap=data[at:begin];parts.extend((gap,after));gaps.append(pin(gap));target+=len(gap)
        edits.append(dict(role=role,begin=begin,target=target,before=before.decode(),after=after.decode()))
        at=begin+len(before);target+=len(after)
    parts.append(data[at:]);gaps.append(pin(data[at:]));output=b"".join(parts)
    proof=dict(input=pin(data),output=pin(output),edits=edits,gaps=gaps)
    require(_restore(output,proof)==data,"full startup source inverse differs")
    return output,proof


def _restore(output,proof):
    require(pin(output)==proof["output"],"startup output pin differs")
    parts,gaps=[],[];at=original_at=0
    for row in proof["edits"]:
        target=row["target"];before=row["before"].encode();after=row["after"].encode()
        require(type(target) is int and at<=target<=len(output) and output[target:target+len(after)]==after,
                "startup inverse target differs")
        gap=output[at:target]
        require(row["begin"]==original_at+len(gap),"startup inverse original offset differs")
        parts.extend((gap,before));gaps.append(pin(gap))
        at=target+len(after);original_at=row["begin"]+len(before)
    parts.append(output[at:]);gaps.append(pin(output[at:]));data=b"".join(parts)
    require(pin(data)==proof["input"] and gaps==proof["gaps"],"startup inverse/complement differs")
    return data


def worker_body(data):
    """Exact fixed callback body, independent of its declaration attribute."""
    names=(b"static void work(void *p){",b"static _Noreturn void work(void *p){")
    matches=[(data.index(n),n) for n in names if data.count(n)==1]
    require(len(matches)==1,"unique fixed work definition required")
    begin,name=matches[0];opening=begin+len(name)-1
    level,quote,escaped=0,None,False
    for index in range(opening,len(data)):
        char=data[index:index+1]
        if quote:
            if escaped:escaped=False
            elif char==b"\\":escaped=True
            elif char==quote:quote=None
        elif char in (b"'",b'"'):quote=char
        elif char==b"{":level+=1
        elif char==b"}":
            level-=1
            if not level:return data[opening:index+1]
    raise ValueError("unterminated work callback")


def retained(files):
    data=files["runtime.c"];body=worker_body(data)
    require(body.count(b"for(;;){")==1 and re.search(rb"\b(return|break|goto)\b",body) is None,
            "fixed work callback must have no normal return path")
    required=(b"workers[created].id=created;",
        b"char *stack=allocate(1048576+4096);if(!stack){status=2;break;}",
        b"if(Dsc3(10,(long)(stack),(long)(4096),(long)(0))||",
        b"<0){status=2;break;}",b"if(status)goto shutdown;",
        b"table=allocate(((size_t)1<<TT_BITS)*sizeof *table);if(!table)return 2;",
        b"atomic_store_explicit(&pending,WORKERS,memory_order_relaxed);",
        b"shutdown:\n    return status;")
    for text in required:require(data.count(text)==1,"required stack/guard/publication/error path differs")
    entry=files["start.S"].split(b"/* long spawn",1)[0]
    require(entry.count(b"call main")==1 and entry.count(b"mov $231,%eax")==1,
            "process-owner _start entry/exit_group differs")
    return dict(worker_body=pin(body),entry_start=pin(entry),
        required_runtime_roles=[pin(s) for s in required],
        unchanged_units={n:pin(files[n]) for n in ("tiny.h","board.c","search.c","image.ld")})


def transform(files, *, nonreturning=False):
    require(type(nonreturning) is bool,"explicit callback contract boolean required")
    require(pins(files)==INPUTS,"exact e207 proved-win source required")
    original_retained=retained(files)
    require(len(re.findall(rb"\bids\b",files["runtime.c"]))==2,
            "ids must have only its declaration and fourth spawn argument as C consumers")
    runtime_roles=[("drop-unused-kernel-TID-storage",b"static atomic_int epoch,pending,ids[WORKERS];",b"static atomic_int epoch,pending;"),
        ("three-argument-spawn-prototype",PROTOTYPE,PROTOTYPE3),
        ("three-argument-fixed-work-call",SPAWN_CALL,SPAWN_CALL3)]
    entry_roles=[("explicit-no-TID-callback-contract",COMMENT,COMMENT_TAIL if nonreturning else COMMENT3),
        ("unused-conditional-kernel-arguments",UNUSED_REGISTERS,b""),
        ("drop-PARENT_SETTID-and-CHILD_CLEARTID",b"mov $0x350f00,%edi",b"mov $0x50f00,%edi")]
    if nonreturning:
        runtime_roles.append(("explicit-never-returning-fixed-work",b"static void work(void *p){",b"static _Noreturn void work(void *p){"))
        entry_roles.append(("ABI-aligned-never-returning-callback-tail",CALLBACK,TAIL))
    result=dict(files);edits={}
    result["runtime.c"],edits["runtime.c"]=_project(files["runtime.c"],runtime_roles)
    result["start.S"],edits["start.S"]=_project(files["start.S"],entry_roles)
    require(retained(result)==original_retained,"worker/entry/guard/stack/search/TT retention differs")
    require(re.search(rb"\bids\b",result["runtime.c"]) is None and
            result["runtime.c"].count(PROTOTYPE3)==1 and result["runtime.c"].count(SPAWN_CALL3)==1,
            "stale TID storage/prototype/call consumer remains")
    mask=0x50f00
    require(mask==0x350f00 & ~(0x100000|0x200000) and mask&0x10000 and
            not mask&(0x1000|0x80000|0x1000000|0x100000|0x200000),
            "clone sharing/ignored-argument flag contract differs")
    proof=dict(kind=KINDS[int(nonreturning)],nonreturning=nonreturning,input=pins(files),output=pins(result),
        source_edits=edits,retained=original_retained,
        clone_flags=dict(before=0x350f00,after=mask,removed=["CLONE_PARENT_SETTID","CLONE_CHILD_CLEARTID"],
            kept=["CLONE_VM","CLONE_FS","CLONE_FILES","CLONE_SIGHAND","CLONE_THREAD","CLONE_SYSVSEM"],
            ignored_arguments=["parent_tid (PARENT_SETTID/PIDFD absent)","child_tid (CHILD_SETTID/CLEARTID absent)","tls (SETTLS absent)"]),
        logical_Worker_id_preserved=True,guard_page_preserved=True,stack_bytes=1048576,
        callback_contract="fixed work never returns" if nonreturning else "callback return retains SYS_exit fallback",
        callback_entry_stack_mod16=8,tail_unused_return_slot_bytes=8 if nonreturning else 0,
        full_engine_executed=False,runtime_qualified=False,old_native_map_changed=False,selected=False)
    require(all(_restore(result[n],edit)==files[n] for n,edit in edits.items()),"complete source inverse differs")
    return result,proof


def restore(files,proof):
    require(type(proof.get("nonreturning")) is bool and
            proof.get("kind")==KINDS[int(proof["nonreturning"])] and pins(files)==proof["output"],
            "new startup class/output proof differs")
    original=dict(files)
    require(set(proof["source_edits"])=={"runtime.c","start.S"},"closed startup edit set required")
    for name,edit in proof["source_edits"].items():original[name]=_restore(files[name],edit)
    regenerated,expected=transform(original,nonreturning=proof["nonreturning"])
    require(regenerated==files and expected==proof,"canonical startup roles/full inverse differ")
    return original
