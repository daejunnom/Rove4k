"""Typed carrier, actual startup mechanism and rules for one no-TID candidate.

This consumes a fresh SearchAdmission.  It does not invoke an owner admission,
replace a native expectation, run a compiler/engine, or qualify a league player.
The local terminal policy permits zero or one legal closing search result.
It is TCEC-targeted; acceptance of that minimum contract by an event is unconfirmed.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import importlib.util
import re
import sys
from types import CodeType, FunctionType, ModuleType

KIND = "rove4k.D-no-TID-runtime-carrier.v1"
SOURCE_KIND = "rove4k.D-no-TID-source.v1"
SELECTOR = "no-tid"
OPTIONS = ["previous-piece", "unsigned-history"]
POLICY = "TCEC-minimum-immediate-process-exit"
INPUT_CONTRACT = "TCEC-valid-non-NUL-lines-at-most-32767-bytes"
SCOPE = "local TCEC-targeted minimal shutdown contract; event approval unconfirmed"
ROUTE = "packed-xz-bcj"
ADMISSION = "engines/experiments/tiny-d-submission/no_tid_admission.py"
SELF = "engines/experiments/tiny-d-submission/no_tid_runtime.py"
READABLE = {"tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld"}
SHIPPING = {"main.c", "start.S", "image.ld"}
IDENTITY = {"linked":{"bytes":7456,"sha256":"16deff54c4059f236c845191674f9b36c26139c032d23e66b53992fd11c3ebf3"},
    "stripped":{"bytes":7104,"sha256":"f0168f752eaa15bf011cbd75964ebe10bc39ca88ddd16eeed66c73e2cf59ed7b"}}
WHOLE = {"bytes":5245,"sha256":"4dbe1bfbceb1c290ee45801e74fe44d7ef2148215b57d51141e1965d5e5db9fa"}
_EXECUTING_CODE = sys._getframe().f_code
STARTUP_LABEL = "no-tid-startup-abi"
STARTUP_UNITS = ("board.c", "search.c", "runtime.c", "start.S")
STARTUP_FLAGS = ("-Os", "-std=c11", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic",
    "-fno-stack-protector", "-fno-builtin", "-fno-asynchronous-unwind-tables", "-fno-unwind-tables",
    "-fno-ident", "-fcf-protection=none", "-ffunction-sections", "-fdata-sections",
    "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack", "-flto", "-msse4.2", "-mcx16",
    "-DDEV=0", "-DD_HQ=0", "-DWORKERS=4", "-DTT_BITS=12")
STARTUP_STDIN = b"uci\nisready\nquit\n"
STARTUP_WRAPPER = b'''static atomic_uint test_spawn3_calls;
extern long fixture_actual_spawn3(void (*)(void *),void *,void *) __asm__("spawn");
static long fixture_spawn3(void (*fn)(void *),void *arg,void *stack){
    Worker *w=arg;unsigned n=atomic_fetch_add_explicit(&test_spawn3_calls,1,memory_order_relaxed);
    if(n>=WORKERS||w->id!=(int)n||((unsigned long)stack&15))abort();
    return fixture_actual_spawn3(fn,arg,stack);
}'''
STARTUP_HOLD = b'''    if(w->id==WORKERS-1){
        struct {long seconds,nanoseconds;} delay={0,200000000};
        output("TEST_LAST_HELD\\n");
        if(Dsc2(35,(long)&delay,0))abort();
        output("TEST_LAST_RELEASED\\n");
    }
'''
STARTUP_DIALOGUE = r'''import json,os,select,subprocess,sys,time
from pathlib import Path
receipt=Path(sys.argv[2]);record=dict(complete=False,events=[],engine_started=False,engine_reaped=False,forced_cleanup=False)
child=None;buffer=b"";deadline=time.monotonic()+20
def save():receipt.write_text(json.dumps(record,indent=2)+"\n")
def emit(data):
 while data:
  n=os.write(1,data);data=data[n:]
def send(data):
 child.stdin.write(data);child.stdin.flush();record["events"].append({"send":data.decode()});save()
def line_until(wanted):
 global buffer
 while True:
  if b"\n" in buffer:
   line,buffer=buffer.split(b"\n",1);line+=b"\n";emit(line)
   record["events"].append({"receive":line.decode()});save()
   if line==wanted:return
   if wanted==b"TEST_LAST_HELD\n" and line==b"uciok\n":raise ValueError("uci before held worker")
   continue
  left=deadline-time.monotonic()
  if left<=0:raise TimeoutError("bounded three-argument startup fixture")
  if select.select([child.stdout],[],[],min(left,.1))[0]:
   data=os.read(child.stdout.fileno(),4096)
   if not data:raise ValueError("startup EOF before expected marker")
   buffer+=data
   if len(buffer)>65536:raise ValueError("startup output bound")
save()
try:
 child=subprocess.Popen([sys.argv[1]],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=None,bufsize=0)
 record.update(engine_started=True,pid=child.pid,pgid=os.getpgid(child.pid),owner_pgid=os.getpgrp(),inherits_owner_group=os.getpgid(child.pid)==os.getpgrp())
 if not record["inherits_owner_group"]:raise ValueError("fixture left original owner group")
 send(b"uci\n");line_until(b"TEST_LAST_HELD\n")
 if buffer:raise ValueError("output arrived before held observation window")
 start=time.monotonic()
 if select.select([child.stdout],[],[],.05)[0]:raise ValueError("premature output while last worker held")
 record["held_window_seconds"]=time.monotonic()-start
 record["no_uci_during_held_window"]=True;save()
 line_until(b"TEST_LAST_RELEASED\n");line_until(b"TEST_INITIALIZED\n");line_until(b"uciok\n")
 send(b"isready\n");line_until(b"readyok\n")
 send(b"quit\n");child.stdin.close();child.stdin=None
 code=child.wait(timeout=5);record.update(engine_reaped=True,returncode=code)
 trailing=buffer+child.stdout.read()
 if trailing:emit(trailing);raise ValueError("unexpected trailing fixture output")
 if code:raise ValueError("startup returned "+str(code))
 record["complete"]=True
except BaseException as error:
 record["failure"]={"type":type(error).__name__,"message":str(error)};raise
finally:
 if child is not None:
  if child.poll() is None:
   record["forced_cleanup"]=True;child.terminate()
   try:child.wait(timeout=2)
   except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)
  record.update(engine_reaped=child.returncode is not None,returncode=child.returncode)
 save()
'''


def require(value, detail):
    if not value:
        raise ValueError(detail)


def pin(data):
    require(type(data) is bytes, "actual immutable bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def inventory(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def _json(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def _relative(name):
    require(isinstance(name, str) and name and "\\" not in name and ":" not in name and "\0" not in name,
            "one normalized carrier input name required")
    parts = name.split("/")
    require(not name.startswith("/") and all(p not in ("", ".", "..") for p in parts),
            "carrier input escaped its relative namespace")
    protected = {".git", ".ssh", ".aws", "node_modules", "dist", "dist-server", "coverage",
                 "models", "checkpoints", ".cache", "inventory.json", "package-lock.json"}
    require(not any(p.casefold() in protected or p.casefold() == ".env" or p.casefold().startswith(".env.")
                    for p in parts), "protected input is not a carrier source")
    return name


def _absolute(path):
    require(isinstance(path, str) and path.startswith("/") and path != "/" and
            str(PurePosixPath(path)) == path and ".." not in PurePosixPath(path).parts and
            not any(c in path for c in ("\\", ":", "\0")), "normalized absolute evidence path required")
    return path


def _settled(row):
    require(isinstance(row, dict) and type(row.get("returncode")) is int and row["returncode"] == 0
            and all(row.get(key) is True for key in ("started", "terminal", "reaped", "owned_group_absent",
                "original_identity_retained_until_other_members_absent"))
            and row.get("forced_cleanup") is False and row.get("other_group_members_before_reap") == []
            and type(row.get("pid")) is int and row["pid"] > 0 and row.get("pgid") == row["pid"],
            "original actual-board command did not settle naturally")


def _admitted(token, admission_module):
    require(getattr(admission_module, "KIND", getattr(admission_module, "SEARCH_KIND", None)) == SOURCE_KIND
            and type(token) is admission_module.NoTidAdmission,
            "exact typed D search admission required, not an owner or native map")
    cls=admission_module.NoTidAdmission
    require(cls.assert_valid(token) is token,"authenticated NoTidAdmission validation failed")
    parent=token.parent;parent_cls=type(parent)
    require(parent_cls.assert_valid(parent) is parent and
            parent_cls.to_record(parent).get("kind") == "rove4k.D-search-source.v1",
            "authenticated unchanged real SearchAdmission parent required")
    record = cls.to_record(token)
    require(record.get("kind") == SOURCE_KIND and record.get("selector") == SELECTOR
            and record.get("nonreturning") is False
            and record.get("options") == OPTIONS and record.get("ownership_policy") == POLICY
            and record.get("last_search_output_required") is False
            and record.get("input_contract") == INPUT_CONTRACT,
            "selected search source or terminal/input contract differs")
    require(all(record.get(key) is True for key in
                ("source_admitted", "native_admitted", "package_generation_admitted"))
            and all(record.get(key) is False for key in
                ("fresh_full_artifact_runtime", "rules_qualified", "physical_placement_qualified",
                 "size_qualified", "selected")), "search carrier requires generation-only authority")
    profile = record["profile"]
    expected_profile={"workers":4,"control_threads":1,"os_threads":5,"tt_bits":23,"tt_entry_bytes":16,
                      "tt_entries":8388608,"tt_mask":8388607,"tt_bytes":128<<20,"tt_cap_bytes":128<<20}
    require(profile.get("id") == "test-p4" and profile.get("parallel_init") is True and
            all(type(profile.get(k)) is int and profile[k]==v for k,v in expected_profile.items()),
            "search carrier admits only explicit P4/W4/TT23/128MiB")
    require(set(token.readable) == READABLE and set(token.shipping) == SHIPPING,
            "complete readable and shipping input sets required")
    return record


def render_startup_fixture(readable):
    """Actual no-TID runtime + exact 3-argument ASM, scaled poison/held probe."""
    require(set(readable)==READABLE and all(type(d) is bytes for d in readable.values()),
            "complete immutable no-TID readable source required")
    prototype=b"extern long spawn(void (*)(void *),void *,void *);"
    call=b"spawn(work,workers+created,stack+1048576+4096)"
    require(readable["runtime.c"].count(prototype)==1 and readable["runtime.c"].count(call)==1 and
            re.search(rb"\bids\b",readable["runtime.c"]) is None and
            b"static void work(void *p){" in readable["runtime.c"] and
            b"0x50f00" in readable["start.S"] and b"call *%rax" in readable["start.S"] and
            b"mov $60,%eax" in readable["start.S"],"only actual returning 3-argument startup is supported")
    here=Path(__file__).resolve().parent
    path=here/"test_startup.py";authority=path.read_bytes().replace(b"\r\n",b"\n")
    spec=importlib.util.spec_from_file_location("D_no_tid_generic_poison",path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    exec(compile(authority,str(path),"exec",dont_inherit=True),module.__dict__)
    generated,poison=module.instrument(dict(readable),go=False)
    roles=[("actual-three-argument-wrapper",prototype,STARTUP_WRAPPER),
        ("actual-three-argument-call",call,b"fixture_spawn3(work,workers+created,stack+1048576+4096)"),
        ("hold-last-real-worker-before-first-touch",b"    for(size_t p=begin/256;",STARTUP_HOLD+b"    for(size_t p=begin/256;"),
        ("check-all-three-argument-transports",b'    output("TEST_INITIALIZED\\n");',
         b'    if(atomic_load_explicit(&test_spawn3_calls,memory_order_relaxed)!=4)abort();\n'
         b'    output("TEST_SPAWN3_4\\nTEST_INITIALIZED\\n");')]
    projection_path=here/"source.py"
    spec=importlib.util.spec_from_file_location("D_no_tid_fixture_projection",projection_path)
    projection=importlib.util.module_from_spec(spec);sys.modules[spec.name]=projection
    spec.loader.exec_module(projection)
    generated["runtime.c"],extra=projection.project(generated["runtime.c"],roles)
    require(generated["start.S"]==readable["start.S"] and
            all(generated[n]==readable[n] for n in ("tiny.h","board.c","search.c","image.ld")),
            "fixture changed actual ASM or search/board units")
    return generated,{"kind":"D-no-TID-actual-startup-fixture-projection-v1","input":inventory(readable),
        "output":inventory(generated),"generic_poison_source":pin(authority),"generic_poison_projection":poison,
        "new_three_argument_projection":extra,"start_S_unchanged":True,"spawn_argument_count":3,
        "worker_count":4,"TT_bits":12,"TT_bytes":65536,"poison_byte":165,"held_last_worker":3,
        "logical_Worker_id_transport_checked":True,"stack_alignment_checked":16,
        "flags":list(STARTUP_FLAGS),"units":list(STARTUP_UNITS),"stdin":pin(STARTUP_STDIN),
        "dialogue":pin(STARTUP_DIALOGUE.encode()),"scope":"scaled actual startup mechanism; not full128MiB/runtime qualification"}


def validate_startup_observation(result,generated,expected,*,old,seen):
    """Bind actual mechanism observations to new source, paths and owner rows."""
    directory=_absolute(result.get("directory"));binary=_absolute(result.get("binary_path"))
    paths=result.get("source_paths",{})
    require(result.get("flags")==list(STARTUP_FLAGS) and result.get("units")==list(STARTUP_UNITS) and
            paths=={n:directory+"/"+n for n in generated} and binary==directory+"/fixture",
            "new three-argument fixture flags/units/source paths differ")
    compiled,executed=result.get("compile",{}),result.get("execute",{})
    old._fresh_paths(compiled,[directory,*paths.values(),binary],seen)
    require(compiled.get("command")==["cc",*STARTUP_FLAGS,*[directory+"/"+n for n in STARTUP_UNITS],
            "-Wl,-T,"+directory+"/image.ld","-o",binary] and compiled.get("cwd")==directory,
            "actual three-argument original compiler argv differs")
    require(type(result.get("binary")) is bytes and result["binary"].startswith(b"\x7fELF"),
            "actual no-libc startup fixture binary required")
    dialogue,receipt=directory+"/dialogue.py",directory+"/dialogue.json"
    old._fresh_paths(executed,[dialogue,receipt],seen)
    require(executed.get("command")==[sys.executable,"-I","-B",dialogue,binary,receipt] and
            executed.get("cwd")==directory and result.get("dialogue")==STARTUP_DIALOGUE.encode() and
            result.get("stdin")==STARTUP_STDIN,"actual startup dialogue argv/input differs")
    output=result.get("output");raw=result.get("receipt_raw")
    require(type(output) is bytes and type(raw) is bytes and
            {k:executed["stdout"].get(k) for k in ("bytes","sha256")}==pin(output),
            "startup observation differs from original owner pipe")
    record=json.loads(raw)
    require(record.get("complete") is True and record.get("engine_started") is True and
            record.get("engine_reaped") is True and record.get("forced_cleanup") is False and
            record.get("returncode")==0 and record.get("inherits_owner_group") is True and
            record.get("owner_pgid")==executed.get("pgid") and record.get("pgid")==executed.get("pgid") and
            type(record.get("pid")) is int and record["pid"]>0,
            "three-argument fixture child did not settle naturally in its owned group")
    require(type(record.get("held_window_seconds")) in (int,float) and record["held_window_seconds"]>=.05 and
            record.get("no_uci_during_held_window") is True,"actual held-last-arrival observation missing")
    events=record.get("events",[])
    require(result.get("events")==events and b"".join(e["send"].encode() for e in events if "send" in e)==STARTUP_STDIN and
            b"".join(e["receive"].encode() for e in events if "receive" in e)==output,
            "startup actual event/input/output streams differ")
    lines=output.splitlines();markers=[b"TEST_LAST_HELD",b"TEST_LAST_RELEASED",b"TEST_SPAWN3_4",b"TEST_INITIALIZED",b"uciok",b"readyok"]
    require(all(lines.count(m)==1 for m in markers) and [lines.index(m) for m in markers]==sorted(lines.index(m) for m in markers),
            "three-argument count/first-touch/held/UCI marker ordering differs")
    return {"kind":"D-no-TID-three-argument-startup-observation-v1","source":inventory(generated),
        "projection":deepcopy(expected),"compile":deepcopy(compiled),"execute":deepcopy(executed),
        "binary":pin(result["binary"]),"output":pin(output),"receipt":pin(raw),
        "worker_count":4,"spawn_argument_count":3,"TT_bits":12,"TT_bytes":65536,
        "held_window_seconds":record["held_window_seconds"],"natural_cleanup":True,
        "full128MiB_qualified":False,"runtime_qualified":False}


def _source(data, module, expected=None):
    require(isinstance(data, dict) and set(data) == {"current", "frozen"}
            and type(data["current"]) is bytes and data["current"] == data["frozen"],
            "current and frozen executing helper source must match")
    require(type(module) is ModuleType and sys.modules.get(module.__name__) is module,
            "actual registered authority module required")
    code=compile(data["frozen"], module.__file__, "exec", dont_inherit=True)
    require(code == module._EXECUTING_CODE,
            "helper source differs from its actually executing module")
    for item in code.co_consts:
        if not isinstance(item,CodeType) or item.co_name.startswith("<"):continue
        if item.co_flags&2:
            actual=getattr(module,item.co_name,None)
            require(type(actual) is FunctionType and actual.__code__==item and
                    actual.__globals__ is module.__dict__,"executing authority function binding differs")
        elif item.co_name in ("SearchAdmission","NoTidAdmission"):
            actual=getattr(module,item.co_name,None)
            require(type(actual) is type and actual.__module__==module.__name__ and
                    actual.__name__==item.co_name and actual.__bases__==(object,),
                    "direct object-only typed authority class binding differs")
            for method in item.co_consts:
                if isinstance(method,CodeType) and method.co_flags&2 and not method.co_name.startswith("<"):
                    function=actual.__dict__.get(method.co_name)
                    if isinstance(function,property):function=function.fget
                    require(type(function) is FunctionType and function.__code__==method and
                            function.__globals__ is module.__dict__,"typed authority method binding differs")
    if expected is not None:
        require(pin(data["frozen"]) == expected, "admission helper pin differs from typed evidence")
    return data["frozen"]


def prepare_carrier(token, *, admission_module, admission_source, bridge_source,
                    runtime, packaging, frozen_inputs):
    """Return named new carrier bytes and the generic runner's AdmittedBuild.

    Caller writes every returned file to one new external root before runtime.
    The admission remains independently held for rules and later revalidation.
    """
    own = _source(bridge_source, sys.modules[__name__])
    authority = _source(admission_source, admission_module)
    record = _admitted(token, admission_module)
    require(pin(authority)==record["admission_source"] and pin(own)==record["startup_fixture_authority"],
            "captured admission/actual startup renderer authority source differs")
    require(isinstance(frozen_inputs, dict) and inventory(frozen_inputs) == token.input_pins,
            "carrier frozen source closure differs from typed admission")
    for name in frozen_inputs:
        _relative(name)
    native, linked = token.native, token.linked
    require(record["identity"] == IDENTITY == {"linked": pin(linked), "stripped": pin(native)},
            "selected search linked/native bytes differ from typed authority")
    whole, detail = packaging.package_native(native, "xz-bcj")
    repeated, again = packaging.package_native(native, "xz-bcj")
    rows = [row for row in token.packages if row.get("route") == ROUTE]
    require(len(rows) == 1 and whole == repeated == token.package_bytes(ROUTE) and detail == again
            and rows[0].get("whole") == pin(whole) and rows[0].get("detail") == detail
            and rows[0].get("reproduced") is True and pin(whole) == WHOLE,
            "fresh selected whole package does not match two reproductions")
    import lzma
    boundary = detail["header_bytes"]
    require(type(boundary) is int and 0 < boundary < len(whole)
            and whole.startswith(b"#!/bin/sh\nexec python3 -c ") and detail.get("codec") == "xz-bcj"
            and detail.get("cleanup") == "memfd-CLOEXEC",
            "counted packed-native bootstrap/cleanup contract differs")
    decoder = lzma.LZMADecompressor()
    restored = decoder.decompress(whole[boundary:], max_length=len(native) + 1)
    require(decoder.eof and not decoder.unused_data and restored == native,
            "strict counted packed-native header/payload inverse differs")
    expected = {**{"native_" + key: value for key, value in pin(native).items()},
                **{"whole_" + key: value for key, value in pin(whole).items()},
                "header_bytes": boundary, "payload_bytes": len(whole) - boundary}
    inputs = deepcopy(token.input_pins)
    inputs[ADMISSION], inputs[SELF] = pin(authority), pin(own)
    contract = {"kind": KIND, "search_admission_kind": SOURCE_KIND, "selector": SELECTOR,
                "options": list(OPTIONS), "ownership_policy": POLICY,
                "last_search_output_required": False, "input_contract": INPUT_CONTRACT,
                "shutdown_scope": SCOPE, "event_target_confirmed": False,
                "admission": record, "identifier_composition": token.identifier_composition,
                "actual_rules_generation": "pending-fresh-shipping-board-fixture"}
    manifest = {"kind": KIND, "family": "D", "profile": deepcopy(record["profile"]),
                "route": ROUTE, "representation": "packed", "expected": expected,
                "native_identity": deepcopy(record["identity"]), "source_contract": contract,
                "input_pins": inputs, "readable_inputs": inventory(token.readable),
                "shipping_inputs": inventory(token.shipping), "fresh_replay_commands": token.fresh_commands,
                "source_native_package_admitted": True, "fresh_full_artifact_runtime": False,
                "rules_qualified": False, "physical_placement_qualified": False,
                "size_qualified": False, "selected": False,
                "shutdown_scope": SCOPE, "event_target_confirmed": False}
    files = {"program": whole, "native/image": native, "native/linked": linked,
             **{"generated-readable/" + name: data for name, data in token.readable.items()},
             **{"shipping-inputs/" + name: data for name, data in token.shipping.items()},
             **{"inputs/" + name: data for name, data in frozen_inputs.items()},
             "inputs/" + ADMISSION: authority, "inputs/" + SELF: own,
             "source-admission.json": _json(record), "build.json": _json(manifest)}
    policy = {"mode": "persistent", "variant": "raw-clone", "startup_threads": 5,
              "between_GO_threads": 5, "active_threads": 5, "input_during_GO": "asynchronous",
              "initialization_join_before_uci": True}
    wrapper = {"entry_cleanup": "loader-owned-fd", "temp_strategy": "memfd-CLOEXEC",
               "cleanup_seconds": 0, "parent_removed": False}
    admitted = runtime.AdmittedBuild("D", "test-p4", "packed", "program", "shipping-inputs/main.c",
        "native/image", expected, {**record["profile"], "ply": 128, "max_position_plies": 4095},
        policy, wrapper, inputs, contract)
    return files, admitted


def shipping_board(token, board_preprocessed, *, admission_module, admission_source, minifier, lexical):
    """Project actual board preprocessing using complete-TU admitted offsets."""
    authority=_source(admission_source,admission_module)
    record=_admitted(token, admission_module)
    require(pin(authority)==record["admission_source"],"actual no-TID board authority differs")
    require(type(board_preprocessed) is bytes, "actual board preprocessing bytes required")
    composition = token.identifier_composition
    board = minifier.compact_source(board_preprocessed, "c").rstrip(b"\n")
    for old, new in composition["legacy"].items():
        board = lexical._replace({"main.c": board}, old, new)["main.c"]
    for rounds in composition["scalar_typedef_rounds"]:
        for step in rounds:
            pieces, offset = [], 0
            for removal in step.get("main.c", {}).get("removed", []):
                begin, end = removal["begin"], removal["end"]
                require(type(begin) is int and type(end) is int and offset <= begin < end,
                        "admitted scalar deletion interval differs")
                if begin >= len(board):
                    continue
                require(end <= len(board) and board[begin:end] == removal["declaration"].encode(),
                        "full-TU deletion cuts or differs inside the actual board prefix")
                pieces.append(board[offset:begin]); offset = end
            pieces.append(board[offset:]); board = b"".join(pieces)
    text, pieces, offset = board.decode(), [], 0
    for begin, end, token_name in lexical._identifier_spans(text):
        if token_name in composition["accepted_alpha"]:
            pieces.extend((text[offset:begin], composition["accepted_alpha"][token_name])); offset = end
    pieces.append(text[offset:]); board = "".join(pieces).encode()
    require(board.endswith(b"}") and token.shipping["main.c"].startswith(board),
            "fresh actual board is not the complete admitted shipping prefix")
    return board


def render_rules(token, cases, *, admission_module, admission_source, preprocess_board, shared, minifier, lexical):
    """Return an actual-board fixture after a fresh, unique owned preprocessing."""
    authority=_source(admission_source,admission_module)
    record = _admitted(token, admission_module)
    require(pin(authority)==record["admission_source"],"actual no-TID rules authority differs")
    readable, flags, label = token.readable, record["flags"], "search-actual-board"
    receipt = preprocess_board(dict(readable), list(flags), label)
    require(isinstance(receipt, dict) and receipt.get("kind") == "D-search-board-preprocess-v1"
            and receipt.get("label") == label and receipt.get("input_pins") == inventory(readable)
            and receipt.get("flags") == list(flags), "fresh search board input/role differs")
    directory = _absolute(receipt.get("readable_dir"))
    row = receipt.get("command", {}); _settled(row)
    require(row.get("command") == ["cc", "-E", "-P", *flags, directory + "/board.c"]
            and row.get("cwd") == directory, "fresh actual-board original argv differs")
    used = set()
    for old in token.fresh_commands:
        for command in old.get("commands", [old.get("command", {})]):
            old_directory = command.get("cwd")
            used.add(old_directory)
            used.update(command.get(stream, {}).get("path") for stream in ("stdout", "stderr"))
            # Semantic and preprocessing receipts retain exact input names and
            # original argv even when they do not repeat source_paths.  Cover
            # those consumed files and the executable path as well as pipes.
            if isinstance(old_directory, str):
                used.update(old_directory + "/" + _relative(name) for name in old.get("input_pins", {}))
            used.update(value for value in command.get("command", [])
                        if isinstance(value, str) and value.startswith("/"))
        used.update(old.get("source_paths", {}).values())
        used.update(old.get(name) for name in ("linked_path", "stripped_path", "binary_path"))
    paths = [directory, *[directory + "/" + name for name in readable],
             *[_absolute(row.get(stream, {}).get("path")) for stream in ("stdout", "stderr")]]
    require(len(paths) == len(set(paths)) and not used.intersection(paths),
            "actual board preprocessing reused an earlier source/output path")
    output = receipt.get("output")
    require(type(output) is bytes and {key: row["stdout"].get(key) for key in ("bytes", "sha256")} == pin(output),
            "fresh actual-board stdout differs")
    board = shipping_board(token, output, admission_module=admission_module,admission_source=admission_source,
        minifier=minifier, lexical=lexical)
    renames = token.identifier_composition["composed"]
    require(not set(renames).intersection({"memcpy", "memset", "abort"}),
            "shipping board memory/abort boundary must preserve original names")
    counts = {}
    for _, _, name in lexical._identifier_spans(board.decode()):
        counts[name] = counts.get(name, 0) + 1
    for name in ("strlen", "strcmp", "strtok_r"):
        require(counts.get(renames.get(name, name)) == 1,
                "fixture-only string declaration acquired an actual board consumer")
    size = renames.get("size_t", "size_t")
    declarations = b"\n" + (("typedef " + size + " size_t;\n").encode() if size != "size_t" else b"")
    declarations += (b"extern size_t strlen(const char *);extern int strcmp(const char *,const char *);"
        b"extern char *strtok_r(char *,const char *,char **);extern int printf(const char *,...);"
        b"extern int puts(const char *);extern char *strcpy(char *,const char *);\n")
    fixture = shared.render_bound_fixture(board, {"board": renames.get("Board", "Board"),
        "start": renames.get("start", "start"), "generate": renames.get("gen", "gen"),
        "make": renames.get("make", "make"), "four_args": False}, cases, declarations)
    return fixture, {"kind": KIND + ".actual-board-fixture", "source_admission": pin(_json(record)),
        "fresh_preprocess": {"label": label, "input_pins": receipt["input_pins"], "flags": list(flags),
            "command": deepcopy(row), "output": pin(output)}, "shipping_main": pin(token.shipping["main.c"]),
        "shipping_board_prefix": pin(board), "fixture": pin(fixture), "TT_allocated": False,
        "native_entry_called": False, "compiled": False, "executed": False, "rules_qualified": False,
        "input_contract": INPUT_CONTRACT, "last_search_output_required": False,
        "shutdown_scope": SCOPE, "event_target_confirmed": False}
