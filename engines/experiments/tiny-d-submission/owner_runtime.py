"""Explicit bridge from fresh D-owner admission to the generic runtime runner.

This is a source-only API, not an old D admission fallback or CLI. Its caller
owns frozen modules, unique compiler callbacks, carrier writes and the later
runtime/rules processes. A stored successful JSON receipt is not accepted in
place of replay_owner. Nothing here runs an engine or allocates a TT.
"""
from copy import deepcopy
import hashlib
import json
import sys

KIND = "rove4k.D-process-owner-runtime-carrier.v1"
ROUTES = {"native-xz-bcj": "packed", "source-jit": "source-jit"}
_EXECUTING_CODE = sys._getframe().f_code


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(isinstance(data, bytes), "carrier evidence must be actual bytes")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _json(data):
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()


def prepare_carrier(record, frozen_inputs, products, modules, *, admission,
                    current_inputs, admission_source, evidence_root,
                    preprocess, compile_identity, route, runtime, bridge_source):
    """Freshly admit, then return (named carrier bytes, AdmittedBuild, replay).

    The third result contains actual readable/shipping bytes for a separately
    owned actual-board fixture. The caller must write *all* named bytes into
    one new external directory before run_runtime(admitted, carrier, ...).
    No target-native reference or old qualification_record is constructed.
    """
    require(route in ROUTES, "explicit owner packed/plain-C-source route required")
    require(set(bridge_source) == {"current", "frozen"} and
        bridge_source["current"] == bridge_source["frozen"] and
        compile(bridge_source["frozen"], __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
        "owner bridge must execute its current frozen source")
    require(admission.OWNER_KIND == "rove4k.D-process-owner-source.v1",
            "explicit D owner source admission module required")
    replay = admission.replay_owner(record, frozen_inputs, products, modules,
        current_inputs=current_inputs, admission_source=admission_source,
        evidence_root=evidence_root, preprocess=preprocess,
        compile_identity=compile_identity)
    require(replay.get("kind") == admission.OWNER_KIND and
        all(replay.get(k) is True for k in ("source_admitted", "native_admitted",
            "package_generation_admitted", "ready_for_fresh_full_P4")) and
        replay.get("ownership_policy") == "final-wait-equivalent-output" and
        replay.get("last_search_output_required") is True and
        all(replay.get(k) is False for k in ("fresh_full_artifact_runtime",
            "rules_qualified", "physical_placement_qualified", "size_qualified",
            "whole_artifact_qualified", "selected")),
        "fresh generation-only equivalent-output owner admission required")
    profile = replay["profile"]
    require(profile["id"] == "test-p4" and profile["workers"] == 4 and
        profile["tt_bits"] == 23 and profile["tt_bytes"] == 128 << 20,
        "carrier only admits actual P4/W4/128MiB, never TT34")
    source = replay["shipping"]
    linked = products["owner/attempt-0/linked"]
    native = products["owner/attempt-0/native"]
    require({"linked": pin(linked), "stripped": pin(native)} == replay["identity"],
            "admitted owner native bytes differ")
    packaging = modules["packaging"]
    if route == "native-xz-bcj":
        whole, detail = packaging.package_native(native, "xz-bcj")
        repeated, again = packaging.package_native(native, "xz-bcj")
        image = native
    else:
        whole, detail = packaging.package_source(source, replay["flags"], replay["units"])
        repeated, again = packaging.package_source(source, replay["flags"], replay["units"])
        image = linked
    declared = next(p for p in replay["packages"] if p["route"] == route)
    require(whole == repeated == products["owner/" + route] and detail == again and
        pin(whole) == declared["whole"] and declared.get("generation_admitted") is True,
        "actual owner carrier package differs from two fresh reproductions")
    boundary = detail["header_bytes"]
    require(pin(whole[:boundary]) == declared["boundaries"]["header"] and
        pin(whole[boundary:]) == declared["boundaries"]["payload"],
        "owner carrier counted bootstrap/payload differs")
    expected = {**{"native_" + k: v for k, v in pin(image).items()},
        **{"whole_" + k: v for k, v in pin(whole).items()},
        "header_bytes": boundary, "payload_bytes": len(whole) - boundary}
    policy = {"mode": "persistent", "variant": "raw-clone",
        "startup_threads": 5, "between_GO_threads": 5, "active_threads": 5,
        "input_during_GO": "asynchronous", "initialization_join_before_uci": True}
    wrapper = {"entry_cleanup": "loader-owned-fd", "temp_strategy": detail["cleanup"],
        "cleanup_seconds": 0, "parent_removed": route == "source-jit"}
    inputs = deepcopy(replay["current_frozen_closure"])
    inputs["engines/experiments/tiny-d-submission/owner_admission.py"] = replay["admission_source"]
    inputs["engines/experiments/tiny-d-submission/owner_runtime.py"] = pin(bridge_source["frozen"])
    contract = {"kind": KIND, "owner_admission_kind": replay["kind"],
        "ownership_policy": replay["ownership_policy"],
        "last_search_output_required": True, "production_proof": replay["production_proof"],
        "owner_proof": replay["owner_proof"],
        "identifier_composition": replay["identifier_composition"],
        "actual_rules_generation": "pending-separate-shipping-board-fixture"}
    manifest = {"kind": KIND, "family": "D", "profile": deepcopy(profile),
        "route": route, "representation": ROUTES[route], "expected": expected,
        "original_experiment_canonical_record": pin(_json(record)),
        "source_contract": contract, "input_pins": inputs,
        "native_identity": deepcopy(replay["identity"]),
        "readable_inputs": {n: pin(d) for n, d in replay["readable"].items()},
        "shipping_inputs": {n: pin(d) for n, d in source.items()},
        "fresh_replay_commands": deepcopy(replay["fresh_commands"]),
        "source_native_package_admitted": True,
        "fresh_full_artifact_runtime": False, "rules_qualified": False,
        "physical_placement_qualified": False, "size_qualified": False,
        "selected": False}
    files = {"program": whole, "native/image": image,
        **{"generated-readable/" + n: d for n, d in replay["readable"].items()},
        **{"shipping-inputs/" + n: d for n, d in source.items()},
        **{"inputs/" + n: d for n, d in frozen_inputs.items()},
        "inputs/engines/experiments/tiny-d-submission/owner_admission.py": admission_source["frozen"],
        "inputs/engines/experiments/tiny-d-submission/owner_runtime.py": bridge_source["frozen"],
        "original-experiment-canonical.json": _json(record),
        "build.json": _json(manifest)}
    admitted = runtime.AdmittedBuild("D", "test-p4", ROUTES[route], "program",
        "shipping-inputs/main.c", "native/image", expected,
        {**profile, "ply": 128, "max_position_plies": 4095}, policy, wrapper,
        inputs, contract)
    return files, admitted, replay


def shipping_board(replay, board_preprocessed, *, minifier, lexical):
    """Project fresh standalone-board preprocessing to its actual shipped prefix.

    Complete-TU typedef deletion offsets and alpha names were independently
    admitted by replay_owner. Apply only deletions lying inside this board
    prefix; do not rerun dead-type analysis on a smaller translation unit.
    """
    require(replay.get("kind") == "rove4k.D-process-owner-source.v1" and
        replay.get("source_admitted") is True and isinstance(board_preprocessed, bytes),
        "fresh owner replay and actual board preprocessing required")
    composition = replay["identifier_composition"]
    board = minifier.compact_source(board_preprocessed, "c").rstrip(b"\n")
    for old, new in composition["legacy"].items():
        board = lexical._replace({"main.c": board}, old, new)["main.c"]
    for rounds in composition["scalar_typedef_rounds"]:
        for step in rounds:
            removals = step.get("main.c", {}).get("removed", [])
            parts, offset = [], 0
            for removal in removals:
                begin, end = removal["begin"], removal["end"]
                require(type(begin) is int and type(end) is int and offset <= begin < end,
                        "admitted scalar deletion interval differs")
                if begin >= len(board):
                    continue
                require(end <= len(board) and board[begin:end] == removal["declaration"].encode(),
                        "complete-TU scalar deletion cuts or differs inside board prefix")
                parts.append(board[offset:begin]); offset = end
            parts.append(board[offset:]); board = b"".join(parts)
    alpha = composition["accepted_alpha"]
    text, parts, offset = board.decode(), [], 0
    for begin, end, token in lexical._identifier_spans(text):
        if token in alpha:
            parts.extend((text[offset:begin], alpha[token])); offset = end
    parts.append(text[offset:]); board = "".join(parts).encode()
    require(board.endswith(b"}") and replay["shipping"]["main.c"].startswith(board),
            "actual independently preprocessed board is not the complete shipping prefix")
    return board


def render_rules(replay, cases, *, preprocess_board, admission, shared,
                 minifier, lexical):
    """Freshly preprocess the admitted board and render; do not compile a probe.

    preprocess_board(readable, flags, label) is an owned callback returning
    kind D-owner-board-preprocess-v1, label, input_pins, flags, readable_dir,
    output bytes and its original settled command. Its new directory contains
    all six exact readable inputs, so the quoted tiny.h resolves locally.
    """
    label = "owner-actual-board"
    readable, flags = replay["readable"], replay["flags"]
    receipt = preprocess_board(dict(readable), list(flags), label)
    require(isinstance(receipt, dict) and
        receipt.get("kind") == "D-owner-board-preprocess-v1" and receipt.get("label") == label and
        receipt.get("input_pins") == {n: pin(d) for n, d in sorted(readable.items())} and
        receipt.get("flags") == list(flags),
        "fresh actual-board sources/flags/role differ")
    directory = admission._absolute(receipt.get("readable_dir"))
    row = receipt.get("command", {})
    admission._settled(row, 0)
    require(row.get("command") == ["cc", "-E", "-P", *flags, directory + "/board.c"] and
        row.get("cwd") == directory,
        "fresh actual-board original command differs")
    used = set()
    for previous in replay["fresh_commands"]:
        rows = previous.get("commands", [previous.get("command", {})])
        for command in rows:
            used.add(command.get("cwd"))
            used.update(command.get(s, {}).get("path") for s in ("stdout", "stderr"))
        used.update(previous.get("source_paths", {}).values())
        used.update(previous.get(k) for k in ("linked_path", "stripped_path"))
    paths = [directory, *[directory + "/" + n for n in readable],
        *[admission._absolute(row.get(s, {}).get("path")) for s in ("stdout", "stderr")]]
    require(len(set(paths)) == len(paths) and not used.intersection(paths),
        "actual-board preprocessing reused earlier source/output paths")
    board_preprocessed = receipt.get("output")
    require(isinstance(board_preprocessed, bytes) and
        {k: row.get("stdout", {}).get(k) for k in ("bytes", "sha256")} == pin(board_preprocessed),
        "fresh actual-board stdout differs")
    board = shipping_board(replay, board_preprocessed, minifier=minifier, lexical=lexical)
    renames = replay["identifier_composition"]["composed"]
    require(not set(renames).intersection({"memcpy", "memset", "abort"}),
        "actual-board memory/abort boundary must retain its protected spelling")
    # The complete-TU reducer renames three unused header declarations. They
    # are not calls in the shipping board. Supply original libc declarations
    # for the appended fixture driver, without mapping its calls to aliases.
    counts = {}
    for _, _, token in lexical._identifier_spans(board.decode()):
        counts[token] = counts.get(token, 0) + 1
    for name in ("strlen", "strcmp", "strtok_r"):
        alias = renames.get(name, name)
        require(counts.get(alias) == 1,
            "fixture-only string declaration acquired an actual-board consumer")
    size = renames.get("size_t", "size_t")
    declarations = b"\n"
    if size != "size_t":
        declarations += ("typedef " + size + " size_t;\n").encode()
    declarations += (b"extern size_t strlen(const char *);extern int strcmp(const char *,const char *);"
        b"extern char *strtok_r(char *,const char *,char **);"
        b"extern int printf(const char *,...);extern int puts(const char *);"
        b"extern char *strcpy(char *,const char *);\n")
    fixture = shared.render_bound_fixture(board, {
        "board": renames.get("Board", "Board"), "start": renames.get("start", "start"),
        "generate": renames.get("gen", "gen"), "make": renames.get("make", "make"),
        "four_args": False}, cases, declarations)
    return fixture, {"kind": KIND + ".actual-board-fixture",
        "fresh_preprocess": {"label": label, "input_pins": receipt["input_pins"],
            "flags": list(flags), "command": deepcopy(row), "output": pin(board_preprocessed)},
        "shipping_main": pin(replay["shipping"]["main.c"]),
        "shipping_board_prefix": pin(board), "fixture": pin(fixture),
        "fixture_only_original_libc_strings": ["strlen", "strcmp", "strtok_r"],
        "shipping_string_alias_declarations_only": True,
        "TT_allocated": False, "native_entry_called": False,
        "compiled": False, "executed": False, "rules_qualified": False}


def require_equivalent_terminal_output(runtime_record):
    """Additional owner contract after generic runtime accepts 0-or-1 replies.

    The generic runner intentionally accepts zero terminal replies for other
    TCEC classes. This owner class retains final wait and requires one complete
    legal reply for each of its two actually active terminal sessions.
    """
    require(runtime_record.get("complete") is True and
        runtime_record.get("source_contract", {}).get("kind") == KIND and
        runtime_record["source_contract"].get("last_search_output_required") is True,
        "complete explicit equivalent-output owner runtime required")
    rows = runtime_record.get("sessions", [])
    require([r.get("termination") for r in rows] ==
        ["idle-quit", "idle-EOF", "active-quit", "active-EOF"],
        "exact four owner runtime sessions required")
    for row in rows[2:]:
        require(row.get("complete") is True and len(row.get("GO", [])) == 1 and
            row["GO"][0].get("label") == "active-terminal" and
            len(row["GO"][0].get("bestmoves", [])) == 1,
            "final-wait owner lost its active terminal complete legal reply")
    return {"ownership_policy": "final-wait-equivalent-output",
        "active_terminal_complete_legal_replies": 2,
        "generic_runtime_completed": True, "rules_qualified": False,
        "physical_placement_qualified": False, "size_qualified": False,
        "selected": False}
