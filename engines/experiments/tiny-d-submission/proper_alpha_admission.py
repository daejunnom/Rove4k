"""Fresh typed admission and TT-free board binding for one D alpha class.

This module performs no I/O and starts no process. A live SearchAdmission is
mandatory. Callbacks supply newly owned compiler observations; saved JSON and
the prior cost experiment cannot manufacture authority. Runtime qualification
remains the responsibility of the unchanged production verifier.
"""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import ast
import json
import lzma
from pathlib import PurePosixPath
import re
import sys

D = "engines/experiments/tiny-d-submission/"
SELF = D + "proper_alpha_admission.py"
PARENT = D + "search_admission.py"
BRIDGE = D + "search_runtime.py"
ALPHA = D + "proper_alpha.py"
CLEANUP = D + "closed_tu_cleanup.py"
RUNTIME = "engines/experiments/tcec-next/profile_verify.py"
RULES = "engines/experiments/tcec-next/profile_rules.py"
REQUIRED_EXTRA = (SELF, PARENT, BRIDGE, ALPHA, CLEANUP, D + "qualify_proper_alpha.py",
    D + "qualify_search.py", RUNTIME, RULES, "engines/experiments/tcec-scope/verify.py",
    "engines/compact/tiny-entry-d/verify.py", "engines/tests/chess_oracle.py",
    "engines/scripts/production.py", "engines/scripts/production_input.py")
KIND = "rove4k.D-proper-alpha-source.v1"
PARENT_KIND = "rove4k.D-search-source.v1"
ROUTES = ("source-jit", "source-jit-compressed")
HELPER_PINS = {
    ALPHA: {"bytes": 7187, "sha256": "b35c26d46bf28e26089f5ed091491384b2496068ed34f9bc3540fe204ad2446b"},
    CLEANUP: {"bytes": 8330, "sha256": "9e98c0e023dc6d033be539af3e2341f13cd79307dfe0ff343deff72aaf6dd25e"},
    PARENT: {"bytes": 53743, "sha256": "287947522e4d13f57ee9acb59791af666074812d935f47dbb633fc91086e319c"},
    BRIDGE: {"bytes": 16880, "sha256": "5f54e0fb9be88d0a9e84e5903b35a49d98329c91cc0dff13f34c9572b3896213"},
}
MAIN = {"bytes": 14137, "sha256": "4cbee770fd702f3deeb32429d54bf03bf3b75c4da0a21e0c93a798c11c5e71ea"}
IDENTITY = {
    "linked": {"bytes": 7488, "sha256": "87c9f93a87a5d53aaa094a0019952cafbbf8da2ff83c382dee1f1c927d91f00f"},
    "stripped": {"bytes": 7136, "sha256": "448eeb52aa59e7eaaf7830940be18f5618129d55732d8855e0c8bcb13368f565"},
}
WHOLE = {
    "source-jit": {"bytes": 6467, "sha256": "76da7353276f84b1e7e1d5bf76360af0c1cc6f40f585f35d49e9490336d4df30"},
    "source-jit-compressed": {"bytes": 6327, "sha256": "008b7765a26d109fab8beafe38f527565764e12dbcb3edad4d2962b78a8e74b7"},
}
MODULES = {"alpha": ALPHA, "cleanup": CLEANUP, "lexical": "engines/scripts/rename_c.py",
    "packaging": D + "packaging.py", "bootstrap": D + "compressed_bootstrap.py",
    "packer": "engines/compact/tiny-entry-d/packer.py", "builder": D + "build.py"}
_TOKEN = object()
_EXECUTING_CODE = sys._getframe().f_code


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "immutable evidence bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def inventory(files):
    require(type(files) is dict and all(type(n) is str for n in files), "explicit source mapping required")
    return {n: pin(b) for n, b in sorted(files.items())}


def equal(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(right, sort_keys=True, separators=(",", ":"))


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def relative(name):
    require(type(name) is str and name and not name.startswith("/") and
        not any(c in name for c in ("\\", ":", "\0")), "normalized relative source name required")
    parts = name.split("/")
    denied = {".git", ".ssh", ".aws", "node_modules", "dist", "dist-server", "build", "coverage",
        "models", "checkpoints", ".cache", "inventory.json", "package-lock.json", "credentials"}
    require(all(p not in ("", ".", "..") and p.casefold() not in denied and
        not p.casefold().startswith(".env") for p in parts), "protected or escaping source name")
    return name


def absolute(value):
    require(type(value) is str and value.startswith("/") and value != "/" and
        str(PurePosixPath(value)) == value and ".." not in PurePosixPath(value).parts and
        not any(c in value for c in ("\\", ":", "\0")), "canonical absolute Linux path required")
    return value


def source_pair(pair, module, *, expected=None, executing=False, verifier=None):
    require(type(pair) is dict and set(pair) == {"current", "frozen"} and
        type(pair["current"]) is bytes and pair["current"] == pair["frozen"],
        "current/frozen helper source pair differs")
    raw = pair["frozen"]
    if expected is not None:
        require(pin(raw) == expected, "named helper source identity differs")
    if executing:
        require(compile(raw, module.__file__, "exec", dont_inherit=True) == module._EXECUTING_CODE,
            "source differs from actually executing admission module")
    else:
        require(callable(verifier), "function-source verifier required")
        verifier(module, raw, module.__file__)
    return raw


def parent_record(parent, module):
    require(getattr(module, "KIND", None) == PARENT_KIND and
        type(parent) is getattr(module, "SearchAdmission", None), "live exact SearchAdmission required")
    parent.assert_valid()
    record = parent.to_record()
    require(record.get("kind") == PARENT_KIND and record.get("selector") == "proved-win-combination"
        and record.get("options") == ["previous-piece", "unsigned-history"]
        and record.get("ownership_policy") == "TCEC-minimum-immediate-process-exit"
        and record.get("last_search_output_required") is False
        and record.get("input_contract") == "TCEC-valid-non-NUL-lines-at-most-32767-bytes",
        "parent search/source/terminal policy differs")
    require(all(record.get(k) is True for k in ("source_admitted", "native_admitted",
        "package_generation_admitted", "actual_search_semantics_admitted")) and
        all(record.get(k) is False for k in ("fresh_full_artifact_runtime", "rules_qualified",
        "physical_placement_qualified", "size_qualified", "selected")), "fresh generation-only parent authority required")
    require(record.get("identity") == IDENTITY and pin(parent.linked) == IDENTITY["linked"]
        and pin(parent.native) == IDENTITY["stripped"], "exact parent linked and stripped images required")
    profile = record.get("profile", {})
    require(profile.get("id") == "test-p4" and type(profile.get("workers")) is int and profile["workers"] == 4
        and type(profile.get("tt_bits")) is int and profile["tt_bits"] == 23
        and profile.get("tt_bytes") == 128 << 20 and profile.get("tt_entry_bytes") == 16,
        "only full P4/W4/TT23/128MiB parent supported")
    return record


def command_paths(value):
    """Collect original paths, including linker paths embedded in argv."""
    found = set()
    def visit(item):
        if type(item) is str:
            if item.startswith("/"):
                found.add(absolute(item))
            elif item.startswith("-Wl,-T,/"):
                found.add(absolute(item[len("-Wl,-T,"):]))
        elif isinstance(item, dict):
            for child in item.values():
                visit(child)
        elif isinstance(item, (tuple, list)):
            for child in item:
                visit(child)
    visit(value)
    return found


def reservations(record, reserved_paths):
    require(isinstance(reserved_paths, (tuple, list, set, frozenset)) and reserved_paths,
        "explicit full archived-artifact reservations required")
    return {absolute(p) for p in reserved_paths} | command_paths(record.get("fresh_commands", []))


def claim_paths(paths, seen):
    require(isinstance(paths, (tuple, list)) and paths, "fresh callback path roles required")
    paths = [absolute(p) for p in paths]
    require(len(paths) == len(set(paths)), "fresh callback reused an input/output/pipe path")
    require(not any(p == old or PurePosixPath(p).is_relative_to(PurePosixPath(old)) or
        PurePosixPath(old).is_relative_to(PurePosixPath(p))
        for p in paths for old in seen), "fresh callback aliases an archived or previously used path")
    seen.update(paths)


def full_source_closure(parent, frozen_inputs, current_inputs):
    require(type(frozen_inputs) is dict and set(frozen_inputs) == set(parent.input_pins) | set(REQUIRED_EXTRA),
        "exact parent plus alpha/runtime consumer source closure required")
    for n in frozen_inputs:
        relative(n)
    require({n: pin(frozen_inputs[n]) for n in parent.input_pins} == parent.input_pins,
        "parent frozen source bytes differ")
    engine_names = {n for n in frozen_inputs if n.startswith("engines/")}
    require(type(current_inputs) is dict and set(current_inputs) == engine_names and
        all(current_inputs[n] == frozen_inputs[n] for n in engine_names), "current/frozen expanded source closure differs")
    return inventory(frozen_inputs)


def package_inverse(whole, detail, files, flags, units, route):
    require(route in ROUTES and type(whole) is bytes and type(detail) is dict,
        "one declared source package route required")
    boundary = detail.get("header_bytes")
    require(type(boundary) is int and 0 < boundary < len(whole) and
        whole.startswith(b"#!/bin/sh\nexec python3 -c "), "counted source bootstrap boundary differs")
    decoder = lzma.LZMADecompressor()
    decoded = decoder.decompress(whole[boundary:], max_length=1 << 20)
    require(decoder.eof and not decoder.unused_data, "whole source payload lacks exact EOF or has trailing data")
    if route == "source-jit":
        bundle = json.loads(decoded)
        require(detail.get("cleanup") == "all filesystem inputs and native removed before fdexec",
            "ordinary source bootstrap cleanup differs")
    else:
        tree = ast.parse(decoded)
        require(len(tree.body) >= 2 and isinstance(tree.body[1], ast.Assign), "compressed source bundle literal absent")
        bundle = ast.literal_eval(tree.body[1].value)
        require(detail.get("kind") == "D-compressed-source-bootstrap-v1" and
            detail.get("cleanup") == "original all-paths-removed-before-fdexec suffix unchanged",
            "compressed source bootstrap cleanup differs")
    require(bundle == {"files": {n: b.decode() for n, b in sorted(files.items())},
        "flags": list(flags), "units": list(units)}, "complete source/flags/units inverse differs")
    return {"header": pin(whole[:boundary]), "payload": pin(whole[boundary:]), "decoded": pin(decoded)}


@dataclass(frozen=True, init=False)
class AlphaAdmission:
    _record: str
    _parent: object
    _parent_module: object
    _shipping: tuple
    _images: tuple
    _frozen: tuple
    _cleanup_module: object
    _valid: object

    def __init__(self, key, record, parent, parent_module, shipping, images, frozen_inputs, cleanup_module):
        require(key is _TOKEN, "AlphaAdmission requires fresh typed alpha admission")
        for name, value in (("_record", json.dumps(record, sort_keys=True)), ("_parent", parent),
            ("_parent_module", parent_module), ("_shipping", tuple(sorted(shipping.items()))),
            ("_images", tuple(sorted(images.items()))), ("_frozen", tuple(sorted(frozen_inputs.items()))),
            ("_cleanup_module", cleanup_module), ("_valid", _TOKEN)):
            object.__setattr__(self, name, value)

    def assert_valid(self):
        require(type(self) is AlphaAdmission and self._valid is _TOKEN, "exact private AlphaAdmission required")
        parent_record(self._parent, self._parent_module)
        record = self.to_record()
        require(record.get("kind") == KIND and inventory(self.shipping) == record.get("shipping_inputs")
            and pin(self.shipping["main.c"]) == MAIN and record.get("identity") == IDENTITY
            and all(pin(self.package_bytes(route)) == WHOLE[route] for route in ROUTES),
            "alpha token source/native/package identity differs")
        return self

    def to_record(self): return json.loads(self._record)
    @property
    def parent(self): return self._parent
    @property
    def readable(self): return self._parent.readable
    @property
    def linked(self): return self._parent.linked
    @property
    def native(self): return self._parent.native
    @property
    def shipping(self): return dict(self._shipping)
    @property
    def input_pins(self): return self.to_record()["input_pins"]
    @property
    def fresh_commands(self): return self.to_record()["fresh_commands"]
    @property
    def packages(self): return self.to_record()["packages"]
    def package_bytes(self, route):
        require(route in ROUTES, "foreign alpha source-package route")
        return dict(self._images)[route]


def admit_alpha(parent, *, parent_module, parent_source, admission_source, helper_sources,
                frozen_inputs, current_inputs, modules, compile_identity, reserved_paths):
    record = parent_record(parent, parent_module)
    require(callable(compile_identity), "fresh full-linked compiler callback required")
    input_pins = full_source_closure(parent, frozen_inputs, current_inputs)
    parent_bytes = source_pair(parent_source, parent_module, expected=HELPER_PINS[PARENT], executing=True)
    require(pin(parent_bytes) == record["admission_source"] and frozen_inputs[PARENT] == parent_bytes,
        "parent admission source binding differs")
    own = source_pair(admission_source, sys.modules[__name__], executing=True)
    require(frozen_inputs[SELF] == own, "expanded closure omitted executing alpha admission")
    require(type(helper_sources) is dict and set(helper_sources) == {ALPHA, CLEANUP}
        and type(modules) is dict and set(modules) == set(MODULES), "complete named alpha modules/source roles required")
    for alias, logical in MODULES.items():
        raw = frozen_inputs[logical]
        if logical in helper_sources:
            require(source_pair(helper_sources[logical], modules[alias], expected=HELPER_PINS[logical],
                verifier=parent_module._function_inputs) == raw, "frozen helper binding differs")
        else:
            parent_module._function_inputs(modules[alias], raw, modules[alias].__file__)
    clean, cleanup_proof = modules["cleanup"].transform(parent.shipping)
    shipping, alpha_proof = modules["alpha"].transform(clean, modules["lexical"])
    restored = modules["alpha"].restore(shipping, deepcopy(alpha_proof), modules["lexical"])
    require(restored == clean and modules["cleanup"].restore(restored, deepcopy(cleanup_proof)) == parent.shipping
        and pin(shipping["main.c"]) == MAIN, "complete fresh cleanup/alpha class or inverse differs")
    seen = reservations(record, reserved_paths)
    observations = []
    for index in range(2):
        label = "proper-alpha/native-repeat/" + str(index)
        result = compile_identity(dict(shipping), list(record["flags"]), list(record["units"]), label)
        require(type(result) is dict, "typed new compiler observation required")
        row = result.get("command", {})
        paths = [row.get("cwd"), *result.get("source_paths", {}).values(), result.get("linked_path"),
            result.get("stripped_path"), *[row.get(s, {}).get("path") for s in ("stdout", "stderr")]]
        next_seen = set(seen)
        claim_paths(paths, next_seen)
        linked, native, observation = parent_module.fresh_compile(result, shipping, record["flags"],
            record["units"], label, modules, set(seen))
        streams = result.get("streams", {})
        require(type(streams) is dict and set(streams) == {"stdout", "stderr"} and
            all(pin(streams[s]) == {k: row[s].get(k) for k in ("bytes", "sha256")} for s in streams)
            and streams["stderr"] == b"", "actual new compiler diagnostics/stream pins differ")
        require(linked == parent.linked and native == parent.native and
            {"linked": pin(linked), "stripped": pin(native)} == IDENTITY,
            "new actual alpha linked/native images differ from live parent")
        seen = next_seen
        observations.append(observation)
    images, packages = {}, []
    for route in ROUTES:
        generated = []
        for _ in range(2):
            if route == "source-jit":
                whole, detail = modules["packaging"].package_source(shipping, record["flags"], record["units"])
            else:
                whole, detail = modules["bootstrap"].package_source(shipping, record["flags"],
                    record["units"], modules["packaging"])
            inverse = package_inverse(whole, detail, shipping, record["flags"], record["units"], route)
            require(pin(whole) == WHOLE[route], "finite alpha whole-package identity differs")
            generated.append((whole, detail, inverse))
        require(generated[0] == generated[1], "two actual alpha source-package constructions differ")
        whole, detail, inverse = generated[0]
        images[route] = whole
        packages.append({"route": route, "whole": pin(whole), "detail": detail, "inverse": inverse, "reproduced": True})
    out = {"kind": KIND, "family": "D", "selector": "proper-alpha", "parent_kind": PARENT_KIND,
        "profile": deepcopy(record["profile"]), "flags": deepcopy(record["flags"]), "units": deepcopy(record["units"]),
        "ownership_policy": record["ownership_policy"], "last_search_output_required": False,
        "input_contract": record["input_contract"], "parent_admission": record,
        "parent_admission_source": pin(parent_bytes), "admission_source": pin(own), "input_pins": input_pins,
        "shipping_inputs": inventory(shipping), "readable_inputs": inventory(parent.readable),
        "cleanup_proof": cleanup_proof, "alpha_proof": alpha_proof, "identity": deepcopy(IDENTITY),
        "packages": packages, "fresh_commands": parent.fresh_commands + observations,
        "reserved_paths": sorted(seen), "source_admitted": True, "native_admitted": True,
        "package_generation_admitted": True, "parent_search_semantics_freshly_admitted": True,
        "new_semantic_fixture_executed": False, "fresh_full_artifact_runtime": False, "rules_qualified": False,
        "physical_placement_qualified": False, "size_qualified": False, "selected": False,
        "event_target_confirmed": False, "scope": "local TCEC-targeted minimal shutdown contract; event approval unconfirmed"}
    return AlphaAdmission(_TOKEN, out, parent, parent_module, shipping, images, frozen_inputs, modules["cleanup"])


def runtime_expected(linked, whole, header_bytes):
    """Source-JIT executes the complete linked image, not the stripped packet."""
    require(type(header_bytes) is int and 0 < header_bytes < len(whole), "counted bootstrap boundary required")
    return {**{"native_" + k: v for k, v in pin(linked).items()},
        **{"whole_" + k: v for k, v in pin(whole).items()},
        "header_bytes": header_bytes, "payload_bytes": len(whole) - header_bytes}


def carrier(token, route, *, runtime, frozen_inputs):
    require(type(token) is AlphaAdmission, "typed alpha admission required for runtime carrier")
    token.assert_valid()
    require(route in ROUTES, "foreign alpha runtime route")
    record = token.to_record()
    require(inventory(frozen_inputs) == token.input_pins, "runtime carrier source closure differs")
    require(runtime.executing_source(frozen_inputs[RUNTIME]) == frozen_inputs[RUNTIME], "executing R source differs")
    whole = token.package_bytes(route)
    package = next(p for p in token.packages if p["route"] == route)
    expected = runtime_expected(token.linked, whole, package["detail"]["header_bytes"])
    contract = {"kind": KIND + ".runtime", "admission": record, "route": route,
        "ownership_policy": record["ownership_policy"], "last_search_output_required": False,
        "input_contract": record["input_contract"], "event_target_confirmed": False,
        "actual_rules_generation": "pending-fresh-cleaned-alpha-board-fixture", "shutdown_scope": record["scope"]}
    wrapper = {"entry_cleanup": "loader-owned-fd", "temp_strategy": "fdexec-unlinked-source-build",
        "cleanup_seconds": 0, "parent_removed": True}
    policy = {"mode": "persistent", "variant": "raw-clone", "startup_threads": 5,
        "between_GO_threads": 5, "active_threads": 5, "input_during_GO": "asynchronous",
        "initialization_join_before_uci": True}
    manifest = {"kind": KIND + ".runtime", "family": "D", "profile": record["profile"],
        "representation": "source-jit", "route": route, "expected": expected,
        "native_identity": record["identity"], "source_contract": contract, "input_pins": token.input_pins,
        "shipping_inputs": inventory(token.shipping), "readable_inputs": inventory(token.readable),
        "fresh_replay_commands": token.fresh_commands, "source_native_package_admitted": True,
        "fresh_full_artifact_runtime": False, "rules_qualified": False, "physical_placement_qualified": False,
        "size_qualified": False, "selected": False, "event_target_confirmed": False}
    files = {"program": whole, "native/image": token.linked, "native/stripped": token.native,
        **{"generated-readable/" + n: b for n, b in token.readable.items()},
        **{"shipping-inputs/" + n: b for n, b in token.shipping.items()},
        **{"inputs/" + relative(n): b for n, b in frozen_inputs.items()},
        "source-admission.json": json_bytes(record), "build.json": json_bytes(manifest)}
    admitted = runtime.AdmittedBuild("D", "test-p4", "source-jit", "program", "shipping-inputs/main.c",
        "native/image", expected, {**record["profile"], "ply": 128, "max_position_plies": 4095},
        policy, wrapper, token.input_pins, contract)
    return files, admitted


def compose_identifiers(parent_map, alpha_map):
    require(type(parent_map) is dict and type(alpha_map) is dict, "complete admitted identifier maps required")
    return {n: alpha_map.get(parent_map.get(n, n), parent_map.get(n, n)) for n in set(parent_map) | set(alpha_map)}


def project_board_prefix(board, shipping, cleanup, alpha_map, lexical):
    """Use complete admitted offsets and the full admitted map, never remap."""
    require(type(board) is bytes and board.endswith(b"}"), "complete actual parent board prefix required")
    spans = []
    for begin, end, role in cleanup.SPANS:
        if begin < len(board):
            require(end <= len(board), "closed-TU cleanup cuts an actual board prefix")
            spans.append((begin, end, role))
    cleaned, proof = cleanup._project(board, spans)
    require(cleanup._restore(cleaned, proof) == board, "actual board cleanup inverse differs")
    text = cleaned.decode("ascii")
    pieces, at = [], 0
    for begin, end, name in lexical._identifier_spans(text):
        if name in alpha_map:
            pieces.extend((text[at:begin], alpha_map[name])); at = end
    pieces.append(text[at:])
    result = "".join(pieces).encode("ascii")
    require(result.endswith(b"}") and shipping["main.c"].startswith(result),
        "fresh cleaned/alpha board is not the admitted shipping prefix")
    return result, {"parent_board": pin(board), "cleanup": proof, "alpha_map": deepcopy(alpha_map), "board": pin(result)}


_FIXTURE_LOCALS = set("m s f t p out n k i child move moves found chosen text paths row board line save".split())
_FIXTURE_EXTERNAL = {"main", "abort", "strlen", "strcmp", "strcpy", "strtok_r", "printf", "puts", "size_t"}


def namespace_fixture(driver, board, binding, lexical):
    bound = {binding[k] for k in ("board", "start", "generate", "make")}
    require(all(type(n) is str and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", n) for n in bound)
        and not bound.intersection(_FIXTURE_LOCALS | _FIXTURE_EXTERNAL), "admitted rule binding captures fixture identifiers")
    board_words = set(lexical._ANY_WORD.findall(board.decode()))
    pieces, at, mapping = [], 0, {}
    for begin, end, name in lexical._identifier_spans(driver.decode()):
        prefix = driver[:begin].rstrip()
        if prefix.endswith(b".") or prefix.endswith(b"->"):
            continue
        if name in lexical._KEYWORDS or name in bound or name in _FIXTURE_EXTERNAL:
            continue
        if name.startswith("rv_rule_"):
            new = "rv_alpha_rule_" + name[len("rv_rule_"):]
        else:
            require(name in _FIXTURE_LOCALS, "unreviewed rules fixture identifier")
            new = "rv_alpha_rule_var_" + name
        require(new not in board_words, "rules fixture namespace collides with admitted board")
        mapping[name] = new
        pieces.extend((driver[at:begin], new.encode())); at = end
    pieces.append(driver[at:])
    return b"".join(pieces), mapping


def render_rules(token, cases, *, parent_module, search_runtime, preprocess_board, shared, minifier, lexical):
    require(type(token) is AlphaAdmission, "typed alpha admission required for actual rules")
    token.assert_valid()
    require(parent_module is token._parent_module and callable(preprocess_board), "exact live parent and fresh board callback required")
    record = token.to_record(); parent = token.parent
    sources = dict(token._frozen)
    frozen = record["input_pins"]
    require(frozen[BRIDGE] == HELPER_PINS[BRIDGE], "original search-runtime bridge source differs")
    require(getattr(search_runtime, "KIND", None) == "rove4k.D-search-runtime-carrier.v1", "named parent board bridge required")
    require(compile(sources[BRIDGE], search_runtime.__file__, "exec", dont_inherit=True) == search_runtime._EXECUTING_CODE,
        "actual search-runtime bridge differs from admitted frozen source")
    for module, logical in ((shared, RULES), (minifier, "engines/scripts/minify.py"),
                            (lexical, "engines/scripts/rename_c.py")):
        parent_module._function_inputs(module, sources[logical], module.__file__)
    flags, label = record["flags"], "proper-alpha-actual-board"
    result = preprocess_board(dict(token.readable), list(flags), label)
    require(type(result) is dict and result.get("kind") == "D-search-board-preprocess-v1" and
        result.get("label") == label and result.get("input_pins") == inventory(token.readable)
        and result.get("flags") == flags, "fresh actual-board input/role differs")
    directory = absolute(result.get("readable_dir")); row = result.get("command", {})
    parent_module.settled(row)
    require(row.get("command") == ["cc", "-E", "-P", *flags, directory + "/board.c"] and
        row.get("cwd") == directory, "fresh actual-board compiler argv differs")
    seen = set(record["reserved_paths"])
    claim_paths([directory, *[directory + "/" + n for n in token.readable],
        *[row.get(s, {}).get("path") for s in ("stdout", "stderr")]], seen)
    output = result.get("output"); streams = result.get("streams", {})
    require(type(output) is bytes and type(streams) is dict and set(streams) == {"stdout", "stderr"}
        and streams["stdout"] == output and streams["stderr"] == b"" and
        all(pin(streams[s]) == {k: row[s].get(k) for k in ("bytes", "sha256")} for s in streams),
        "fresh actual-board original streams or diagnostics differ")
    # The already source-authenticated bridge consumes the live parent token.
    parent_board = search_runtime.shipping_board(parent, output, admission_module=parent_module,
        minifier=minifier, lexical=lexical)
    cleanup_module = token._cleanup_module
    board, projection = project_board_prefix(parent_board, token.shipping, cleanup_module,
        record["alpha_proof"]["renames"], lexical)
    composed = compose_identifiers(parent.identifier_composition["composed"], record["alpha_proof"]["renames"])
    name = lambda n: composed.get(n, n)
    binding = {"board": name("Board"), "start": name("start"), "generate": name("gen"), "make": name("make"), "four_args": False}
    counts = {}
    for _, _, n in lexical._identifier_spans(board.decode()): counts[n] = counts.get(n, 0) + 1
    require(all(counts.get(name(n), 0) == 0 for n in ("strlen", "strcmp", "strtok_r", "printf", "puts", "strcpy")),
        "fixture libc declaration captures a real board identifier")
    size, move, entry = name("size_t"), name("Move"), name("Entry")
    declarations = (("\ntypedef " + size + " size_t;\n").encode() if size != "size_t" else b"\n")
    declarations += (b"extern size_t strlen(const char *);extern int strcmp(const char *,const char *);"
        b"extern char *strtok_r(char *,const char *,char **);extern int printf(const char *,...);"
        b"extern int puts(const char *);extern char *strcpy(char *,const char *);\n")
    assertions = (f'_Static_assert(sizeof({size})==8&&sizeof({move})==4,"alpha ABI scalar");\n'
        f'_Static_assert(sizeof({binding["board"]})==176&&__builtin_offsetof({binding["board"]},{name("h")})==32'
        f'&&__builtin_offsetof({binding["board"]},{name("b")})==48,"alpha ABI board");\n'
        f'_Static_assert(sizeof({entry})==16&&_Alignof({entry})==16,"alpha ABI TT");\n').encode()
    declarations += assertions
    raw = shared.render_bound_fixture(board, binding, cases, declarations)
    old_prefix = b"#define main rv_rule_original_main\n"
    require(raw.startswith(old_prefix + board + declarations), "shared rules template source/declaration boundary differs")
    driver, namespace = namespace_fixture(raw[len(old_prefix)+len(board)+len(declarations):], board, binding, lexical)
    require(b"rv_alpha_rule_original_main" not in board, "rules original-main namespace collides")
    fixture = b"#define main rv_alpha_rule_original_main\n" + board + declarations + driver
    return fixture, {"kind": KIND + ".actual-board-fixture", "source_admission": pin(json_bytes(record)),
        "fresh_preprocess": {"label": label, "input_pins": result["input_pins"], "flags": flags,
            "command": deepcopy(row), "output": pin(output)}, "shipping_main": pin(token.shipping["main.c"]),
        "shipping_board_prefix": pin(board), "projection": projection, "binding": binding,
        "namespace": namespace, "ABI_assertions": pin(assertions), "fixture": pin(fixture),
        "TT_allocated": False, "native_entry_called": False, "compiled": False, "executed": False,
        "rules_qualified": False, "last_search_output_required": False, "input_contract": record["input_contract"],
        "shutdown_scope": record["scope"], "event_target_confirmed": False}
