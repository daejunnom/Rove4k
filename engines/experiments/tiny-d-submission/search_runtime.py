"""Typed runtime carrier and actual-board rules for the selected D search form.

This consumes a fresh SearchAdmission.  It does not invoke an owner admission,
replace a native expectation, run a compiler/engine, or qualify a league player.
The local terminal policy permits zero or one legal closing search result.
It is TCEC-targeted; acceptance of that minimum contract by an event is unconfirmed.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import PurePosixPath
import sys

KIND = "rove4k.D-search-runtime-carrier.v1"
SOURCE_KIND = "rove4k.D-search-source.v1"
SELECTOR = "proved-win-combination"
OPTIONS = ["previous-piece", "unsigned-history"]
POLICY = "TCEC-minimum-immediate-process-exit"
INPUT_CONTRACT = "TCEC-valid-non-NUL-lines-at-most-32767-bytes"
SCOPE = "local TCEC-targeted minimal shutdown contract; event approval unconfirmed"
ROUTE = "packed-xz-bcj"
ADMISSION = "engines/experiments/tiny-d-submission/search_admission.py"
SELF = "engines/experiments/tiny-d-submission/search_runtime.py"
READABLE = {"tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld"}
SHIPPING = {"main.c", "start.S", "image.ld"}
_EXECUTING_CODE = sys._getframe().f_code


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
            and type(token) is admission_module.SearchAdmission,
            "exact typed D search admission required, not an owner or native map")
    token.assert_valid()
    record = token.to_record()
    require(record.get("kind") == SOURCE_KIND and record.get("selector") == SELECTOR
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
    require(profile.get("id") == "test-p4" and type(profile.get("workers")) is int and profile["workers"] == 4
            and profile.get("tt_bits") == 23 and profile.get("tt_entry_bytes") == 16
            and profile.get("tt_bytes") == 128 << 20 and profile.get("tt_cap_bytes") == 128 << 20,
            "search carrier admits only explicit P4/W4/TT23/128MiB")
    require(set(token.readable) == READABLE and set(token.shipping) == SHIPPING,
            "complete readable and shipping input sets required")
    return record


def _source(data, module, expected=None):
    require(isinstance(data, dict) and set(data) == {"current", "frozen"}
            and type(data["current"]) is bytes and data["current"] == data["frozen"],
            "current and frozen executing helper source must match")
    require(compile(data["frozen"], module.__file__, "exec", dont_inherit=True) == module._EXECUTING_CODE,
            "helper source differs from its actually executing module")
    if expected is not None:
        require(pin(data["frozen"]) == expected, "admission helper pin differs from typed evidence")
    return data["frozen"]


def prepare_carrier(token, *, admission_module, admission_source, bridge_source,
                    runtime, packaging, frozen_inputs):
    """Return named new carrier bytes and the generic runner's AdmittedBuild.

    Caller writes every returned file to one new external root before runtime.
    The admission remains independently held for rules and later revalidation.
    """
    record = _admitted(token, admission_module)
    own = _source(bridge_source, sys.modules[__name__])
    authority = _source(admission_source, admission_module, record["admission_source"])
    require(isinstance(frozen_inputs, dict) and inventory(frozen_inputs) == token.input_pins,
            "carrier frozen source closure differs from typed admission")
    for name in frozen_inputs:
        _relative(name)
    native, linked = token.native, token.linked
    require(len(native) == 7136 and len(linked) == 7488
            and record["identity"] == {"linked": pin(linked), "stripped": pin(native)},
            "selected search linked/native bytes differ from typed authority")
    whole, detail = packaging.package_native(native, "xz-bcj")
    repeated, again = packaging.package_native(native, "xz-bcj")
    rows = [row for row in token.packages if row.get("route") == ROUTE]
    require(len(rows) == 1 and whole == repeated == token.package_bytes(ROUTE) and detail == again
            and rows[0].get("whole") == pin(whole) and rows[0].get("detail") == detail
            and rows[0].get("reproduced") is True and len(whole) == 5261,
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


def shipping_board(token, board_preprocessed, *, admission_module, minifier, lexical):
    """Project actual board preprocessing using complete-TU admitted offsets."""
    _admitted(token, admission_module)
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


def render_rules(token, cases, *, admission_module, preprocess_board, shared, minifier, lexical):
    """Return an actual-board fixture after a fresh, unique owned preprocessing."""
    record = _admitted(token, admission_module)
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
    board = shipping_board(token, output, admission_module=admission_module, minifier=minifier, lexical=lexical)
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
