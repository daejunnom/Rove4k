"""Separate scalar D ownership class: final wait, then own exit_group entry.

The main thread still requests stopped=1 and acquires pending==0 before a
normal quit/EOF return. Only idle-worker shutdown/join is removed. The pinned
standalone entry invokes Linux exit_group(231), covering its CLONE_THREAD
workers (TGID), not the external command owner's process group (PGID).

This pure source candidate is not baseline wiring, native identity, measured
size, or runtime qualification. Its caller must use the genuine, unmodified
frozen publication module as admission authority and qualify natural exits.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

KIND = "D-final-wait-own-exit-group-v1"
ADMISSION_SHA = "9958da259d9b622f7ff2559f248bf4e5c70ab0cb69f0c5b13af1d829e115c10f"
COHORTS = {family + "-" + mode for family in ("resource", "equivalent")
           for mode in ("none", "prefix", "dense", "prefix-dense")}
ENTRY_SHA = "4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b"
ENTRY = b"    call main\n    mov %eax,%edi\n    mov $231,%eax\n    syscall\n    ud2\n"
CLONE = b"    mov $0x350f00,%edi\n    mov $56,%eax\n    syscall\n"
GLOBAL = b"static atomic_int epoch,pending,quitting,ids[WORKERS];"
POLL = b"        if(atomic_load_explicit(&quitting,memory_order_relaxed))return;\n"
SHUTDOWN = (b"    atomic_store_explicit(&quitting,1,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake(&epoch);\n"
    b"    for(int i=0;i<created;i++){int id;while((id=atomic_load_explicit(ids+i,memory_order_acquire)))futex_wait(ids+i,id,0);}\n")
FINAL_WAIT = b"    }\n    wait();\nshutdown:\n"
RETURN = b"    return status;\n}\n"
WAIT = (b"static void wait(void){\n"
    b"    atomic_store_explicit(&stopped,1,memory_order_relaxed);\n"
    b"    int count;while((count=atomic_load_explicit(&pending,memory_order_acquire)))futex_wait(&pending,count,1);\n}\n")
WRITE = b'static void output(const char *s){size_t n=0;while(s[n])n++;while(n){long z=CALL(1,1,s,n,0,0,0);if(z==-4)continue;if(z<=0)abort();s+=z;n-=(size_t)z;}}'
ROLES = {
    "stop-before-pending-acquire": WAIT,
    "complete-raw-write-or-own-abort": WRITE,
    "result-before-pending-zero-release": b"result();atomic_store_explicit(&pending,0,memory_order_release);wake(&pending);",
    "ordinary-main-final-wait": FINAL_WAIT,
    "startup-failure-skips-pending-wait": b"    if(status)goto shutdown;\n    wait();\n    for(;;){",
    "startup-arrival-release": b"    atomic_fetch_sub_explicit(&pending,1,memory_order_release);wake(&pending);",
    "last-worker-output-reservation": b"if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==2){",
    "position-reuse-fence": b'if(word(command,"position")){wait();set_position((char *)cursor);}',
    "EOF-break": b"int valid=read_line(line);if(valid<0)break;if(!valid)continue;",
    "quit-break": b'else if(word(command,"quit"))break;',
    "clone-TID-storage-ABI": b"spawn(work,workers+created,stack+1048576+4096,(int *)(ids+created))<0",
}


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def inventory(files):
    return {name:pin(data) for name,data in sorted(files.items())}


def _admit(files, admission, publication_proof):
    path = Path(admission.__file__)
    if path.parts[-4:] != ("engines", "experiments", "tiny-d-submission", "publication.py"):
        raise ValueError("frozen publication authority required")
    authority = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in authority or pin(authority)["sha256"] != ADMISSION_SHA or set(admission.INPUTS) != COHORTS:
        raise ValueError("process-owner publication authority differs")
    if (not isinstance(files, dict) or not files or
            any(not isinstance(n,str) or not isinstance(d,bytes) or b"\r" in d for n,d in files.items())):
        raise ValueError("normalized complete D source mapping required")
    base = files if publication_proof is None else admission.restore(files, publication_proof)
    if publication_proof is not None:
        expected_files,expected_proof = admission.transform(base)
        if expected_files != files or expected_proof != publication_proof:
            raise ValueError("complete canonical publication proof required")
    actual = {name:pin(data)["sha256"] for name,data in base.items()}
    cohort = next((name for name,expected in admission.INPUTS.items() if actual == expected), None)
    if cohort is None:
        raise ValueError("exact complete D process-owner cohort required")
    if (pin(files["start.S"])["sha256"] != ENTRY_SHA or files["start.S"].count(ENTRY) != 1 or
            files["start.S"].count(CLONE) != 1 or files["image.ld"].count(b"ENTRY(_start)") != 1):
        raise ValueError("own exit_group entry or CLONE_THREAD contract differs")
    runtime = files["runtime.c"]
    if not runtime.endswith(FINAL_WAIT + SHUTDOWN + RETURN):
        raise ValueError("original final wait/shutdown/return boundary differs")
    for role,body in ROLES.items():
        if runtime.count(body) != 1:
            raise ValueError("retained process-owner role differs: " + role)
    return cohort, pin(authority)


def _project(source):
    roles = (("remove-only-quitting-state", GLOBAL, b"static atomic_int epoch,pending,ids[WORKERS];"),
             ("remove-idle-worker-quitting-poll", POLL, b""),
             ("entry-owns-thread-group-termination", SHUTDOWN, b""))
    rows = []
    for role,before,after in roles:
        if source.count(before) != 1:
            raise ValueError("unique process-owner source role required: " + role)
        rows.append((source.index(before),role,before,after))
    parts,edits,gaps,cursor,target = [],[],[],0,0
    for begin,role,before,after in sorted(rows):
        if begin < cursor:
            raise ValueError("overlapping process-owner roles")
        gap = source[cursor:begin]; parts.extend((gap,after)); gaps.append(pin(gap)); target += len(gap)
        edits.append(dict(role=role,source=begin,target=target,before=before.decode(),after=after.decode()))
        cursor = begin + len(before); target += len(after)
    parts.append(source[cursor:]); gaps.append(pin(source[cursor:])); output = b"".join(parts)
    proof = dict(input=pin(source),output=pin(output),edits=edits,protected_gaps=gaps)
    if _restore(output,proof) != source:
        raise ValueError("process-owner full runtime inverse differs")
    if b"quitting" in output or not output.endswith(FINAL_WAIT + RETURN):
        raise ValueError("process-owner final wait/return or quitting removal differs")
    return output,proof


def _restore(output, proof):
    if pin(output) != proof["output"]:
        raise ValueError("process-owner runtime output differs")
    parts,gaps,cursor = [],[],0
    for row in proof["edits"]:
        begin,after = row["target"],row["after"].encode()
        if begin < cursor or output[begin:begin+len(after)] != after:
            raise ValueError("process-owner inverse role differs")
        gap = output[cursor:begin]; parts.extend((gap,row["before"].encode())); gaps.append(pin(gap))
        cursor = begin + len(after)
    parts.append(output[cursor:]); gaps.append(pin(output[cursor:])); original = b"".join(parts)
    if pin(original) != proof["input"] or gaps != proof["protected_gaps"]:
        raise ValueError("process-owner inverse or protected complement differs")
    return original


def _retained(before, after):
    records = {}
    for role,body in ROLES.items():
        if before.count(body) != 1 or after.count(body) != 1:
            raise ValueError("process-owner retained role missing: " + role)
        records[role] = dict(source=before.index(body),target=after.index(body),**pin(body))
    result_begin = b"static void result(void){\n"; result_end = b"static void work(void *p){\n"
    if before.count(result_begin) != 1 or before.count(result_end) != 1:
        raise ValueError("one complete result function required")
    start,end = before.index(result_begin),before.index(result_end)
    complete = before[start:end]
    if after.count(complete) != 1:
        raise ValueError("complete bestmove result writer changed")
    records["entire-result-before-release"] = dict(source=start,target=after.index(complete),**pin(complete))
    return records


def _proof(files, result, edit, cohort, authority, publication_proof):
    return dict(kind=KIND,cohort=cohort,admission=authority,publication=deepcopy(publication_proof),
        input=inventory(files),output=inventory(result),source_edits={"runtime.c":edit},
        retained_runtime_roles=_retained(files["runtime.c"],result["runtime.c"]),
        entry=dict(source=pin(files["start.S"]),main_return_to_exit_group=pin(ENTRY),
            clone_thread_flags=pin(CLONE),clone_mask=0x350f00,entry_symbol="_start",
            linker=pin(files["image.ld"]),linker_entry_role=pin(b"ENTRY(_start)"),syscall=231),
        scope="separate standalone Linux x86-64 scalar D DEV0 ownership class",
        contracts=dict(normal_quit_EOF="unchanged final wait requests stopped=1 before pending acquire loop",
            output="last result completes raw writes before pending=0 release; main acquires zero before return",
            natural_exit="main status returns to pinned _start; syscall231 ends all CLONE_THREAD members",
            startup_failure="status2 bypasses pending wait; entry terminates any already-created workers",
            owner="exit_group covers engine TGID, not external command-owner PGID",
            clone_ABI="ids[] storage, parent-set/child-clear TID and all clone flags retained"),
        active_atomic_inventory_DEV0=dict(load=5,store=7,fetch_sub=2,fetch_add=1,total=15),
        external_termination_counts_as_success=False,board_search_changed=False,
        initialization_position_go_pending_output_changed=False,
        native_identity_claimed=False,runtime_qualified=False,size_measured=False,selected=False)


def transform(files, admission, publication_proof=None):
    cohort,authority = _admit(files,admission,publication_proof)
    result = dict(files); result["runtime.c"],edit = _project(files["runtime.c"])
    proof = _proof(files,result,edit,cohort,authority,publication_proof)
    if restore(result,proof,admission) != files:
        raise ValueError("complete process-owner source inverse differs")
    return result,proof


def restore(files, proof, admission):
    if proof.get("kind") != KIND or proof.get("cohort") not in COHORTS:
        raise ValueError("unknown process-owner proof")
    if inventory(files) != proof["output"] or set(proof["source_edits"]) != {"runtime.c"}:
        raise ValueError("complete process-owner output cohort differs")
    original = dict(files); original["runtime.c"] = _restore(files["runtime.c"],proof["source_edits"]["runtime.c"])
    cohort,authority = _admit(original,admission,proof["publication"])
    runtime,expected = _project(original["runtime.c"])
    expected_files = dict(original); expected_files["runtime.c"] = runtime
    expected_proof = _proof(original,expected_files,expected,cohort,authority,proof["publication"])
    if files != expected_files or proof != expected_proof:
        raise ValueError("process-owner exact roles or entry contract differs")
    return original
