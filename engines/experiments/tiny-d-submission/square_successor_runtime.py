"""Typed carrier and actual new-board proofs for one Square-successor candidate.

This consumes a fresh SquareAdmission with a real fresh NoTidAdmission parent.
The independent 5233-byte carrier never invokes the parent's carrier or maps.
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
from types import CodeType, FunctionType, ModuleType, GetSetDescriptorType

KIND = "rove4k.D-square-successor-runtime-carrier.v1"
SOURCE_KIND = "rove4k.D-square-successor-source.v1"
SELECTOR = "successor"
OPTIONS = ["previous-piece", "unsigned-history"]
POLICY = "TCEC-minimum-immediate-process-exit"
INPUT_CONTRACT = "TCEC-valid-non-NUL-lines-at-most-32767-bytes"
SCOPE = "local TCEC-targeted minimal shutdown contract; event approval unconfirmed"
ROUTE = "packed-xz-bcj"
ADMISSION = "engines/experiments/tiny-d-submission/square_successor_admission.py"
SELF = "engines/experiments/tiny-d-submission/square_successor_runtime.py"
READABLE = {"tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld"}
SHIPPING = {"main.c", "start.S", "image.ld"}
IDENTITY = {"linked":{"bytes":7456,"sha256":"8eb2ae8f53038cf6555c294533260a1fd64f3c1d4c7d2f213e4116568c7ce401"},
    "stripped":{"bytes":7104,"sha256":"222d8cc534073f59e3bf3f7fa114302e39e9c3f0dbb33f03924a3c6d4b98f329"}}
WHOLE = {"bytes":5233,"sha256":"0b4fa4afee90cd8074bc93764e73e55474ae6a9e3605a879cdadb53aaa7902b4"}
_EXECUTING_CODE = sys._getframe().f_code
STORAGE_FIELDS=("_valid","_record","_parent","_parent_module","_readable","_shipping","_images","_native","_linked")
STARTUP_UNITS = ("board.c", "search.c", "runtime.c", "start.S")
STARTUP_FLAGS = ("-Os", "-std=c11", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic",
    "-fno-stack-protector", "-fno-builtin", "-fno-asynchronous-unwind-tables", "-fno-unwind-tables",
    "-fno-ident", "-fcf-protection=none", "-ffunction-sections", "-fdata-sections",
    "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack", "-flto", "-msse4.2", "-mcx16",
    "-DDEV=0", "-DD_HQ=0", "-DWORKERS=4", "-DTT_BITS=12")
STARTUP_STDIN = b"uci\nisready\nquit\n"


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


def validate_profile(profile):
    require(type(profile) is dict,"typed Square P4 profile required")
    expected={"workers":4,"control_threads":1,"os_threads":5,"tt_bits":23,"tt_entry_bytes":16,
              "tt_entries":8388608,"tt_mask":8388607,"tt_bytes":128<<20,"tt_cap_bytes":128<<20}
    require(profile.get("id")=="test-p4" and profile.get("purpose")=="test" and
            all(profile.get(k) is True for k in ("parallel_init","init_partition_requires_page_aligned_base","initialization_in_startup")) and
            profile.get("event_allocation_confirmed") is None and
            all(type(profile.get(k)) is int and profile[k]==v for k,v in expected.items()),
            "Square carrier admits only exact typed W4/TT23/128MiB parallel P4")
    return deepcopy(profile)


def _admitted(token, admission_module):
    require(getattr(admission_module, "KIND", getattr(admission_module, "SEARCH_KIND", None)) == SOURCE_KIND
            and type(token) is admission_module.SquareAdmission,
            "exact typed D search admission required, not an owner or native map")
    cls=admission_module.SquareAdmission
    require(cls.assert_valid(token) is token,"authenticated SquareAdmission validation failed")
    parent=token.parent;parent_cls=type(parent)
    require(parent_cls.assert_valid(parent) is parent and
            parent_cls.to_record(parent).get("kind") == "rove4k.D-no-TID-source.v1",
            "authenticated fresh real NoTidAdmission parent required")
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
    validate_profile(record["profile"])
    require(set(token.readable) == READABLE and set(token.shipping) == SHIPPING,
            "complete readable and shipping input sets required")
    return record


COMPONENT = "engines/experiments/tiny-d-submission/no_tid_runtime.py"
COMPONENT_PIN = {"bytes":30622,"sha256":"a878b2401201b46565605a7ece66b451b7248df5ac2721887e725f5b40b53656"}
STARTUP_KIND = "D-square-successor-three-argument-startup-fixture-v1"
STARTUP_LABEL = "square-successor-startup-abi"


def startup_component():
    """Authenticate a frozen generic mechanism component; never its carrier."""
    path=Path(__file__).resolve().parent/"no_tid_runtime.py"
    raw=path.read_bytes().replace(b"\r\n",b"\n")
    require(b"\r" not in raw and pin(raw)==COMPONENT_PIN,"frozen no-TID startup component source differs")
    spec=importlib.util.spec_from_file_location("D_square_authenticated_startup_component",path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    exec(compile(raw,str(path),"exec",dont_inherit=True),module.__dict__)
    _source({"current":raw,"frozen":raw},module,logical=COMPONENT)
    require(module.KIND=="rove4k.D-no-TID-runtime-carrier.v1" and
            tuple(module.STARTUP_FLAGS)==STARTUP_FLAGS and tuple(module.STARTUP_UNITS)==STARTUP_UNITS and
            module.STARTUP_STDIN==STARTUP_STDIN,"only the fixed no-TID startup mechanism is a component")
    return module,raw


def render_startup_fixture(readable):
    """Use actual Square six-source input with authenticated 3-argument startup."""
    require(set(readable)==READABLE and all(type(d) is bytes for d in readable.values()),
            "actual immutable Square six-file input required")
    component,authority=startup_component()
    generated,projection=component.render_startup_fixture(dict(readable))
    require(projection["input"]==inventory(readable) and projection["output"]==inventory(generated) and
            generated["board.c"]==readable["board.c"] and generated["start.S"]==readable["start.S"],
            "startup component changed the actual new Square board or entry")
    return generated,{"kind":"D-square-successor-actual-startup-fixture-projection-v1",
        "input":inventory(readable),"output":inventory(generated),"selector":SELECTOR,
        "component_path":COMPONENT,"component_authority":pin(authority),"component_projection":projection,
        "component_role":"3-argument startup mechanism only; no parent carrier/native authority",
        "actual_square_board":pin(readable["board.c"]),"flags":list(STARTUP_FLAGS),"units":list(STARTUP_UNITS),
        "full128MiB_qualified":False,"runtime_qualified":False}


def validate_startup_observation(result,generated,expected,*,old,seen):
    """Retain new Square source/proof while checking the genuine component."""
    require(type(result) is dict and result.get("kind")==STARTUP_KIND and result.get("label")==STARTUP_LABEL and
            result.get("generated")==generated and result.get("proof")==expected and
            expected.get("selector")==SELECTOR and expected.get("output")==inventory(generated),
            "new Square startup kind/source/proof differs")
    component,authority=startup_component()
    require(expected.get("component_authority")==pin(authority)==COMPONENT_PIN,
            "executing startup component authority differs")
    observation=component.validate_startup_observation(result,generated,expected["component_projection"],old=old,seen=seen)
    return {"kind":"D-square-successor-three-argument-startup-observation-v1",
        "source":inventory(generated),"new_projection":deepcopy(expected),"component_observation":observation,
        "component_authority":pin(authority),"parent_carrier_used":False,"runtime_qualified":False}





def _source(data, module, expected=None, *, logical=None):
    require(isinstance(data, dict) and set(data) == {"current", "frozen"}
            and type(data["current"]) is bytes and data["current"] == data["frozen"],
            "current and frozen executing helper source must match")
    require(type(module) is ModuleType and sys.modules.get(module.__name__) is module,
            "actual registered authority module required")
    parts=Path(module.__file__).parts
    roles=(logical,) if logical is not None else (ADMISSION,SELF,COMPONENT)
    require(all(role in (ADMISSION,SELF,COMPONENT) for role in roles) and
            any(parts[-len(PurePosixPath(role).parts):]==PurePosixPath(role).parts for role in roles),
            "authority occupies an unqualified source role")
    code=compile(data["frozen"], module.__file__, "exec", dont_inherit=True)
    require(code == module._EXECUTING_CODE,
            "helper source differs from its actually executing module")
    for item in code.co_consts:
        if not isinstance(item,CodeType) or item.co_name.startswith("<"):continue
        if item.co_flags&2:
            actual=getattr(module,item.co_name,None)
            require(type(actual) is FunctionType and actual.__code__==item and
                    actual.__globals__ is module.__dict__,"executing authority function binding differs")
        elif item.co_name in ("SearchAdmission","NoTidAdmission","SquareAdmission"):
            actual=getattr(module,item.co_name,None)
            require(type(actual) is type and actual.__module__==module.__name__ and
                    actual.__name__==item.co_name and actual.__qualname__==item.co_name and actual.__bases__==(object,) and
                    not any(name in actual.__dict__ for name in ("__getattribute__","__getattr__","__slots__",*STORAGE_FIELDS)) and
                    type(actual.__dict__.get("__dict__")) is GetSetDescriptorType and
                    actual.__dict__["__dict__"].__objclass__ is actual,
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


def reserved_paths(record):
    values=record.get("reserved_evidence_paths")
    require(type(values) is list and all(type(path) is str for path in values) and
            values==sorted(set(values)),"canonical immutable parent/archive path namespace required")
    return {_absolute(path) for path in values}


def argv_paths(arguments):
    result=set()
    for value in arguments:
        if isinstance(value,str):
            if value.startswith("-Wl,-T,"):value=value[len("-Wl,-T,"):]
            if value.startswith("/"):result.add(_absolute(value))
    return result


def require_fresh_paths(paths,used):
    require(len(paths)==len(set(paths)) and not used.intersection(paths),
            "new board preprocessing reused immutable parent/archive/source/output evidence")


def prepare_carrier(token, *, admission_module, admission_source, bridge_source,
                    runtime, packaging, frozen_inputs):
    """Return named new carrier bytes and the generic runner's AdmittedBuild.

    Caller writes every returned file to one new external root before runtime.
    The admission remains independently held for rules and later revalidation.
    """
    own = _source(bridge_source, sys.modules[__name__],logical=SELF)
    authority = _source(admission_source, admission_module,logical=ADMISSION)
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
    authority=_source(admission_source,admission_module,logical=ADMISSION)
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
    authority=_source(admission_source,admission_module,logical=ADMISSION)
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
    used = reserved_paths(record)
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
            used.update(argv_paths(command.get("command",[])))
        used.update(old.get("source_paths", {}).values())
        used.update(old.get(name) for name in ("linked_path", "stripped_path", "binary_path"))
    paths = [directory, *[directory + "/" + name for name in readable],
             *[_absolute(row.get(stream, {}).get("path")) for stream in ("stdout", "stderr")]]
    require_fresh_paths(paths,used)
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
