"""Fresh admission of the finite D previous-piece/positive-history candidate.

This module starts no process and writes no artifact. Its callbacks return
actual newly owned preprocessing, full-linked compilation and semantic probe
results. The token does not admit a runtime, board rules, placement or size.
The upstream owner projection is provenance, not this candidate's policy:
this class permits immediate process exit on quit/EOF and valid input only.
"""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
import lzma
from pathlib import Path, PurePosixPath
import re
import sys
from types import CodeType, FunctionType

KIND = "rove4k.D-search-source.v1"
EXPERIMENT_KIND = "D-structural-search-source-semantic-cost-v1"
SELECTOR = "proved-win-combination"
OPTIONS = ("previous-piece", "unsigned-history")
D = "engines/experiments/tiny-d-submission/"
NATIVE = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")
UNITS = ("main.c", "start.S")
MEMBERS = ("board.c", "search.c", "runtime.c")
PLANS = ("control", "union-order", "previous-piece", "constant-start", "unsigned-history", SELECTOR)
EXTRA = tuple(D + name + ".py" for name in (
    "reduce", "publication", "process_owner", "test_startup", "test_process_owner",
    "compressed_bootstrap", "syscall_arity", "test_runtime_scaffold", "valid_input",
    "search_compact", "test_search_compact", "probe_search_compact", "check_storage", "source_inputs"))
IDENTITY = {"linked": {"bytes": 7488, "sha256": "87c9f93a87a5d53aaa094a0019952cafbbf8da2ff83c382dee1f1c927d91f00f"},
            "stripped": {"bytes": 7136, "sha256": "448eeb52aa59e7eaaf7830940be18f5618129d55732d8855e0c8bcb13368f565"}}
CONTROL = {"linked": {"bytes": 7520, "sha256": "d5e88f33cb83d5ec167c295fdf93e161f3863e83c3ff0c18fda34776e1db6c2b"},
           "stripped": {"bytes": 7168, "sha256": "8eb3ecf8b17d2a0b3485a713cb5bdd896e3ff34b6c32453e2469f07debbaacec"}}
PACKED = {"bytes": 5261, "sha256": "01b36b58e190694f36ee052f0f299f96618cc72f430ed178b12fe37af58448dd"}
RECEIPT = {"bytes": 1316547, "sha256": "e207630b4272c82e147a765d3e3c19ce8fcbfae50e13c19a7cb0f40c4fb0ee43"}
STORAGE_RECEIPT = {"bytes": 114928, "sha256": "3023184711864d78d3f1d6df790b973e78c5158e47bb373cfff61ca9f721d491"}
_TOKEN = object()
_EXECUTING_CODE = sys._getframe().f_code


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "actual evidence bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def inventory(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def executing_source(data):
    require(compile(data, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "search admission source differs from its executing module")
    return data


def equal(left, right):
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def absolute(value):
    require(isinstance(value, str) and PurePosixPath(value).is_absolute() and
            ".." not in PurePosixPath(value).parts and str(PurePosixPath(value)) == value,
            "canonical absolute Linux evidence path required")
    return value


def settled(row):
    require(isinstance(row, dict) and type(row.get("returncode")) is int and row["returncode"] == 0
            and all(row.get(key) is True for key in ("started", "terminal", "reaped", "owned_group_absent",
                "original_identity_retained_until_other_members_absent"))
            and row.get("forced_cleanup") is False and row.get("other_group_members_before_reap") == []
            and type(row.get("pid")) is int and row["pid"] > 0 and row.get("pgid") == row["pid"],
            "original owned search command did not settle naturally")


_absolute = absolute
_settled = settled


def input_names(record, producer):
    require(record.get("kind") == EXPERIMENT_KIND and record.get("complete") is True
            and record.get("frozen_execution") is True, "explicit completed structural search experiment required")
    require(all(record.get(key) is False for key in ("selected", "old_admission_changed", "runtime_qualified",
        "rules_qualified", "real_target_allocation", "locality_proof", "strength_claim")),
        "search experiment must remain unqualified and unselected")
    names = {"selection/build.json", *producer, *EXTRA}
    require(set(record.get("inputs", {})) == names, "exact recipe-derived search input closure differs")
    return tuple(sorted(names))


def command_scopes(record, producer):
    input_names(record, producer)
    kinds = ["compiler-version"]
    for label in PLANS:
        kinds += [label + "-semantic-" + action + "-" + mode
                  for mode in ("plain", "ubsan") for action in ("compile", "run")]
        kinds += [label + "-preprocess", label + "-entry"]
        kinds += [label + "-source-gate-" + stage for stage in ("baseline", "typedefs", "batch-alpha")]
        kinds += [label + "-native-" + str(index) for index in range(2)]
        kinds += [label + "-fixture-" + action + "-" + mode
                  for mode in ("valid", "quit", "eof") for action in ("compile", "run")]
    rows = record.get("commands")
    require(isinstance(rows, list) and [row.get("kind") for row in rows] == kinds,
            "exact derived search command role/order differs")
    for row in rows:
        settled(row)
        require(isinstance(row.get("command"), list) and all(isinstance(v, str) for v in row["command"]),
                "original search command argv/status differs")
    require(record.get("host_cleanup") == {"unsettled_commands": 0, "errors": []}, "search command owner not settled")
    return tuple(kinds)


def evidence_names(record, producer):
    kinds = command_scopes(record, producer)
    names = set()
    for index, kind in enumerate(kinds, 1):
        names.update("tool-" + str(index) + "-" + kind + "." + stream for stream in ("stdout", "stderr"))
        if kind.endswith("-preprocess"):
            names.add("tool-" + str(index) + "-" + kind + ".stdin")
    for label in PLANS:
        names.update(label + "/generated-readable/" + name for name in NATIVE)
        names.update(label + "/shipping-inputs/" + name for name in ("main.c", "start.S", "image.ld"))
        names.update(label + "/gate-" + str(index) + "/" + name
                     for index in range(3) for name in ("main.c", "start.S", "image.ld", "linked"))
        names.update(label + "/native-" + str(index) + "/" + name for index in range(2) for name in ("linked", "native"))
        names.update(label + "/" + route for route in ("packed-alone", "packed-xz", "packed-xz-bcj", "source-jit-compressed"))
        names.update(label + "/semantic-" + mode + "/" + name for mode in ("plain", "ubsan")
                     for name in ("tiny.h", "board.c", "search.c", "driver.c", "x"))
        names.update(label + "/fixture-" + mode + "/" + name for mode in ("valid", "quit", "eof")
                     for name in (*NATIVE, "x", "dialogue.py", "dialogue.json"))
    return tuple(sorted(names))


def storage_evidence_names(record):
    require(pin((json.dumps(record, indent=2) + "\n").encode()) == STORAGE_RECEIPT,
            "approved storage receipt required before evidence name discovery")
    names = {"frozen-inputs/" + name for name in record.get("inputs", {})}
    names.update("prepared/" + name for name in NATIVE)
    for case in record.get("cases", []):
        name = case.get("name")
        require(isinstance(name, str) and re.fullmatch(r"(?:plain|ubsan)-prefix-[01]-dense-[01]", name),
                "finite storage case name required")
        names.update(name + "/" + member for member in ("tiny.h", "board.c", "search.c", "driver.c", "fixture"))
    for index, row in enumerate(record.get("commands", []), 1):
        names.update("tool-" + str(index) + "-" + row["kind"] + "." + stream for stream in ("stdout", "stderr"))
    return tuple(sorted(names))


def _streams(row, products, root, index):
    for stream in ("stdout", "stderr"):
        entry = row.get(stream, {})
        name = "tool-" + str(index) + "-" + row["kind"] + "." + stream
        require(entry.get("path") == root + "/" + name and pin(products[name]) ==
                {key: entry.get(key) for key in ("bytes", "sha256")}, "owned search command raw pipe differs")


def _fresh_paths(row, paths, seen):
    settled(row)
    candidates = [absolute(value) for value in paths]
    candidates += [absolute(row.get(stream, {}).get("path")) for stream in ("stdout", "stderr")]
    require(len(set(candidates)) == len(candidates) and not seen.intersection(candidates),
            "fresh search source/output/pipe path was reused")
    seen.update(candidates)


def fresh_preprocess(result, files, flags, label, seen):
    driver = b"".join(('#include "' + name + '"\n').encode() for name in MEMBERS)
    require(isinstance(result, dict) and result.get("kind") == "D-search-preprocess-v1"
        and result.get("label") == label and result.get("input_pins") == inventory(files)
        and result.get("flags") == list(flags) and result.get("members") == list(MEMBERS)
        and result.get("driver") == driver, "typed fresh search preprocess inputs differ")
    directory = absolute(result.get("readable_dir")); rows = result.get("commands")
    require(isinstance(rows, list) and len(rows) == 2, "two fresh preprocessing commands required")
    require(rows[0].get("command") == ["cc", "-E", "-P", *flags, "-I", directory, "-x", "c", "-"]
        and rows[1].get("command") == ["cc", "-E", "-P", "-x", "assembler-with-cpp", directory + "/start.S"]
        and all(row.get("cwd") == directory for row in rows), "fresh preprocessing argv differs")
    outputs = result.get("outputs", {})
    require(set(outputs) == {"main.c", "start.S"}, "fresh main and entry bytes required")
    for index, (name, row) in enumerate(zip(("main.c", "start.S"), rows)):
        _fresh_paths(row, ([directory, *[directory + "/" + n for n in files]] if index == 0 else []), seen)
        require(pin(outputs[name]) == {key: row["stdout"].get(key) for key in ("bytes", "sha256")},
                "fresh preprocessing output differs from original pipe")
    return outputs, {"kind": "D-search-preprocess-v1", "label": label,
        "input_pins": inventory(files), "flags": list(flags), "members": list(MEMBERS),
        "driver": pin(driver), "readable_dir": directory, "commands": deepcopy(rows),
        "outputs": inventory(outputs)}


def fresh_compile(result, files, flags, units, label, modules, seen):
    require(isinstance(result, dict) and result.get("kind") == "D-search-native-compile-v1"
        and result.get("label") == label and result.get("input_pins") == inventory(files)
        and result.get("flags") == list(flags) and result.get("units") == list(units),
        "typed fresh search compile inputs differ")
    paths = result.get("source_paths", {})
    require(set(paths) == set(files) and all(PurePosixPath(absolute(value)).name == name for name, value in paths.items()),
            "exact fresh compiler source paths required")
    linked_path, native_path = absolute(result.get("linked_path")), absolute(result.get("stripped_path"))
    row = result.get("command", {})
    _fresh_paths(row, [*paths.values(), linked_path, native_path], seen)
    require(all(str(PurePosixPath(value).parent) == row.get("cwd") for value in paths.values())
        and str(PurePosixPath(linked_path).parent) == row.get("cwd")
        and row.get("command") == ["cc", *flags, *[paths[name] for name in units],
        "-Wl,-T," + paths["image.ld"], "-o", linked_path], "fresh full-linked compiler argv differs")
    linked, native = result.get("linked"), result.get("stripped")
    require(result.get("linked_pin") == pin(linked) and result.get("stripped_pin") == pin(native)
            and modules["packer"].strip_native(linked) == native, "fresh full-linked/stripped bytes differ")
    return linked, native, {"label": label, "input_pins": inventory(files), "flags": list(flags), "units": list(units),
        "source_paths": deepcopy(paths), "linked_path": linked_path, "stripped_path": native_path,
        "linked": pin(linked), "stripped": pin(native), "command": deepcopy(row),
        "geometry": modules["builder"].kernel_geometry(modules["packer"], linked, 4),
        "native_geometry": modules["builder"].kernel_geometry(modules["packer"], native, 4)}


def _composition(legacy, reduction):
    alpha = {}
    for stage in reduction["stages"]:
        if stage["kind"] == "batch-alpha" and stage["status"] == "accepted":
            alpha = stage["renames"]
    composed = {name: alpha.get(legacy.get(name, name), legacy.get(name, name)) for name in set(legacy) | set(alpha)}
    return {"legacy": deepcopy(legacy), "accepted_alpha": deepcopy(alpha), "composed": composed,
        "scalar_typedef_rounds": [deepcopy(stage["rounds"]) for stage in reduction["stages"]
            if stage["kind"] == "unused-scalar-typedefs" and stage["status"] == "accepted"],
        "stage_order": ["legacy-control-identifiers", "accepted-unused-scalar-typedefs", "accepted-batch-alpha"]}


def _packages(label, shipping, flags, native, declared, products, modules):
    routes = ("packed-alone", "packed-xz", "packed-xz-bcj", "source-jit-compressed")
    require([row.get("route") for row in declared] == list(routes), "exact finite search package routes required")
    result, images = [], {}
    for route, old in zip(routes, declared):
        if route.startswith("packed-"):
            whole, detail = modules["packaging"].package_native(native, route[len("packed-"):])
            repeated, again = modules["packaging"].package_native(native, route[len("packed-"):])
            restored = native
        else:
            whole, detail = modules["bootstrap"].package_source(shipping, flags, UNITS, modules["packaging"])
            repeated, again = modules["bootstrap"].package_source(shipping, flags, UNITS, modules["packaging"])
            bundle = {"files": {name: shipping[name].decode() for name in sorted(shipping)}, "flags": list(flags), "units": list(UNITS)}
            bootstrap = modules["bootstrap"]; packaging = modules["packaging"]
            suffix = bootstrap.ANCHOR + packaging.SOURCE_CODE.split(bootstrap.ANCHOR, 1)[1]
            restored = (bootstrap.IMPORTS + "b=" + json.dumps(bundle, separators=(",", ":"), ensure_ascii=True) + "\n" + suffix).encode()
        require(whole == repeated == products[label + "/" + route] and detail == again
            and pin(whole) == old.get("whole") and equal(detail, old.get("detail")) and old.get("reproduced") is True,
            "fresh whole search package differs")
        boundary = detail["header_bytes"]
        require(type(boundary) is int and 0 < boundary < len(whole), "complete package boundary required")
        decoder = lzma.LZMADecompressor()
        decoded = decoder.decompress(whole[boundary:], max_length=len(restored) + 1)
        require(decoded == restored and decoder.eof and not decoder.unused_data, "strict whole search payload inverse differs")
        images[route] = whole
        result.append({**deepcopy(old), "boundaries": {"header": pin(whole[:boundary]), "payload": pin(whole[boundary:])}})
    return result, images


@dataclass(frozen=True, init=False)
class SearchAdmission:
    """An immutable generation/semantic token; a JSON map cannot construct it."""
    _record: str
    _readable: tuple
    _shipping: tuple
    _images: tuple
    _native: bytes
    _linked: bytes
    _valid: object

    def __init__(self, token, record, readable, shipping, images, native, linked):
        require(token is _TOKEN, "SearchAdmission requires fresh explicit search admission")
        for name, value in (("_record", json.dumps(record, sort_keys=True)), ("_readable", tuple(sorted(readable.items()))),
            ("_shipping", tuple(sorted(shipping.items()))), ("_images", tuple(sorted(images.items()))),
            ("_native", native), ("_linked", linked), ("_valid", _TOKEN)):
            object.__setattr__(self, name, value)

    def assert_valid(self):
        require(type(self) is SearchAdmission and self._valid is _TOKEN and
            self.to_record().get("kind") == KIND and self.to_record().get("selector") == SELECTOR
            and {"linked": pin(self._linked), "stripped": pin(self._native)} == IDENTITY,
            "exact fresh SearchAdmission token required")
        return self

    def to_record(self):
        return json.loads(self._record)

    @property
    def readable(self): return dict(self._readable)
    @property
    def shipping(self): return dict(self._shipping)
    @property
    def native(self): return self._native
    @property
    def linked(self): return self._linked
    @property
    def packages(self): return self.to_record()["packages"]
    @property
    def input_pins(self): return self.to_record()["input_pins"]
    @property
    def identifier_composition(self): return self.to_record()["identifier_composition"]
    @property
    def fresh_commands(self): return self.to_record()["fresh_commands"]
    def package_bytes(self, route): return dict(self._images)[route]
    def replay_dict(self):
        return {**self.to_record(), "readable": self.readable, "shipping": self.shipping}


def _modules(modules):
    aliases = {"builder": "build", "startup": "test_startup", "owner": "process_owner",
        "arity": "syscall_arity", "valid": "valid_input", "search": "search_compact",
        "probe": "probe_search_compact", "storage_checker": "check_storage", "reducer": "reduce",
        "checker": "test_process_owner", "runtime_checker": "test_runtime_scaffold", "bootstrap": "compressed_bootstrap"}
    result = dict(modules)
    for name, alternative in aliases.items():
        if name not in result and alternative in result:
            result[name] = result[alternative]
    required = {"source", "builder", "startup", "owner", "arity", "valid", "search", "probe",
        "storage_checker", "reducer", "checker", "runtime_checker", "bootstrap", "lexical", "minifier",
        "packer", "packaging", "storage", "publication", "source_inputs"}
    require(required <= set(result), "complete named search source/probe modules required")
    return result


def _module_inputs(modules, frozen):
    names = {name: D + filename + ".py" for name, filename in (
        ("source", "source"), ("builder", "build"), ("startup", "test_startup"), ("owner", "process_owner"),
        ("arity", "syscall_arity"), ("valid", "valid_input"), ("search", "search_compact"),
        ("probe", "probe_search_compact"), ("storage_checker", "check_storage"), ("reducer", "reduce"),
        ("checker", "test_process_owner"), ("runtime_checker", "test_runtime_scaffold"), ("bootstrap", "compressed_bootstrap"),
        ("packaging", "packaging"), ("storage", "storage"), ("publication", "publication"), ("source_inputs", "source_inputs"))}
    names.update(lexical="engines/scripts/rename_c.py", minifier="engines/scripts/minify.py",
                 packer="engines/compact/tiny-entry-d/packer.py")
    for name, logical in names.items():
        module = modules[name]; path = Path(module.__file__)
        require(path.parts[-len(PurePosixPath(logical).parts):] == PurePosixPath(logical).parts,
                "named frozen search module belongs to another source role")
        require(path.is_file() and path.stat().st_size <= 16 << 20, "bounded named frozen module required")
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        require(raw == frozen[logical], "executing search module source differs from frozen bytes")
        _function_inputs(module, raw, path)


def _function_inputs(module, raw, path):
    code = compile(raw, str(path), "exec", dont_inherit=True)
    # Top-level function bodies have CO_NEWLOCALS. Class bodies do not, and
    # comprehensions/lambdas have synthetic names rather than module bindings.
    for function in (value for value in code.co_consts if isinstance(value, CodeType)
            and value.co_flags & 2 and not value.co_name.startswith("<")):
        actual = getattr(module, function.co_name, None)
        require(type(actual) is FunctionType and actual.__code__ == function,
                "search source function differs from its compiled frozen module")


def _storage(evidence, frozen, modules):
    require(isinstance(evidence, dict) and set(evidence) == {"raw", "root", "products"}
            and pin(evidence["raw"]) == STORAGE_RECEIPT, "approved actual storage receipt bytes required")
    record = json.loads(evidence["raw"]); root = absolute(evidence["root"]); products = evidence["products"]
    require(set(products) == set(storage_evidence_names(record)), "exact storage evidence products required")
    require(record.get("kind") == "D-actual-C-search-storage-contract-v3" and record.get("complete") is True
            and record.get("frozen_execution") is True and record.get("actual_functions_equal") is True
            and all(record.get(key) is False for key in ("actual_runtime", "actual_target_allocation", "strength_claim"))
            and record.get("host_cleanup") == {"unsettled_commands": 0, "errors": []}, "storage evidence scope differs")
    api = modules["source"].production()
    profile = api.ResourceProfile("storage-fixture-tt12-w256", "test", 256, 16 << 12)
    files, source_proof = modules["source"].prepare(profile)
    require(equal(record["resource"], profile.to_record(16)) and equal(record["source"], source_proof)
            and inventory(files) == record["prepared"], "actual storage prepared source differs")
    expected_inputs = set(modules["source_inputs"].source_names(json.loads(frozen[modules["source_inputs"].RECIPE]))) | {
        D + "source_inputs.py", D + "storage.py", D + "check_storage.py", "engines/experiments/tcec-scope/build.py"}
    require(set(record["inputs"]) == expected_inputs, "storage exact recipe/helper input closure differs")
    for name, expected in record["inputs"].items():
        require(name in frozen and pin(frozen[name]) == expected and products["frozen-inputs/" + name] == frozen[name],
                "storage/search frozen source authority differs")
    require(all(products["prepared/" + name] == data for name, data in files.items()), "storage prepared bytes differ")
    cases = [(mode, prefix, dense) for mode in ("plain", "ubsan")
             for prefix, dense in ((False, False), (True, False), (False, True), (True, True))]
    require(len(record["cases"]) == len(cases) and len(record["commands"]) == 2 * len(cases), "complete storage matrix required")
    baseline = None
    for index, (case, (mode, prefix, dense)) in enumerate(zip(record["cases"], cases)):
        name = mode + "-prefix-" + str(int(prefix)) + "-dense-" + str(int(dense)); directory = root + "/" + name
        projected, proof = modules["storage"].transform(files, prefix=prefix, dense=dense)
        require(modules["storage"].restore(projected, proof) == files, "storage full inverse differs")
        generated, observation = modules["storage_checker"].instrument(modules["source"], projected)
        require(case["name"] == name and case["mode"] == mode and case["prefix"] is prefix and case["dense"] is dense
                and equal(case["projection"], proof) and equal(case["instrumentation"], observation), "actual storage fixture proof differs")
        for member in ("tiny.h", "board.c", "search.c"):
            require(products[name + "/" + member] == generated[member], "storage actual instrumented input differs")
        require(products[name + "/driver.c"] == modules["storage_checker"].DRIVER.encode(), "storage driver bytes differ")
        flags = ["-std=c11", "-O2", "-g0", "-msse4.2", "-mcx16", "-DDEV=0", "-DD_HQ=0",
            "-DWORKERS=256", "-DTT_BITS=12", "-DPLY=128", "-DCASE_PREFIX=" + str(int(prefix)), "-DCASE_DENSE=" + str(int(dense))]
        if mode == "ubsan": flags += ["-fsanitize=undefined", "-fno-sanitize-recover=undefined"]
        require(case["flags"] == flags and pin(products[name + "/fixture"]) == case["binary"], "storage compiler input/native differs")
        for offset, action in enumerate(("compile", "execute")):
            row = record["commands"][index * 2 + offset]; settled(row)
            require(row["kind"] == action + "-" + name and row["cwd"] == directory and row["command"] ==
                (["cc", *flags, directory + "/driver.c", "-o", directory + "/fixture"] if action == "compile" else [directory + "/fixture"]),
                "storage exact owned compiler/execution argv differs")
            _streams(row, products, root, index * 2 + offset + 1)
            require(not products[Path(row["stderr"]["path"]).name], "actual storage fixture diagnostic differs")
        output = products[Path(record["commands"][index * 2 + 1]["stdout"]["path"]).name]
        lines = output.splitlines(); require(lines and lines[0].startswith(b"ABI ") and lines[-1].startswith(b"TOTAL "), "storage observations incomplete")
        normalized = b"\n".join(lines[1:]) + b"\n"
        if baseline is None: baseline = normalized
        require(normalized == baseline and pin(normalized) == case["observations"] and pin(output) == case["output"]
                and lines[0].decode() == case["worker_abi"] and lines[-1].decode() == case["totals"], "actual storage observations differ")
    return {"receipt": STORAGE_RECEIPT, "prepared": inventory(files), "cases": len(cases), "observations": pin(baseline),
            "actual_target_allocation": False, "runtime_qualified": False}


def semantic_observation(fresh, archived, archived_binary, normalized, summary):
    """Bind two actual fixture images without asserting cross-directory identity.

    UBSan embeds source paths. The immutable archived image keeps its old pin;
    a freshly owned compile gets its own observed pin and must reproduce the
    exact raw/normalized observations. Shipping native identity is separate.
    """
    output, binary = fresh.get("output"), fresh.get("binary")
    require(pin(archived_binary) == archived.get("binary"), "archived actual semantic binary differs")
    require(pin(output) == {key: fresh.get("execute", {}).get("stdout", {}).get(key)
                for key in ("bytes", "sha256")}
        and pin(output) == archived.get("output") and pin(normalized) == archived.get("normalized")
        and equal(summary, archived.get("summary")), "fresh semantic bytes/coverage differs")
    require(binary and type(binary) is bytes, "fresh actual semantic binary bytes required")
    return {"binary": pin(binary), "archived_binary": pin(archived_binary),
            "binary_matches_archived": binary == archived_binary,
            "output": pin(output), "normalized": pin(normalized), "summary": deepcopy(summary)}


def _semantic(label, readable, proof, valid, stored, products, rows, root, modules, callback, seen):
    options = () if label == "control" else OPTIONS
    generated, driver, expected = modules["probe"].render(readable, modules["source"], modules["storage_checker"],
        reference_board=valid["board.c"], variant_proof=proof, prefix=True, dense=False,
        union_order=False, previous_index=bool(options), constant_start=False, unsigned_history=bool(options))
    require(equal(expected, stored["semantic_proof"]), "actual selected search semantic fixture proof differs")
    result = callback(dict(readable), label=label, options=tuple(options), valid_readable=dict(valid), structural_proof=deepcopy(proof))
    require(isinstance(result, dict) and result.get("kind") == "D-search-semantic-v1" and result.get("label") == label
        and result.get("options") == list(options) and result.get("input_pins") == inventory(readable)
        and result.get("instrumented") == generated and result.get("driver") == driver
        and equal(result.get("proof"), expected), "fresh semantic callback consumed another source/fixture")
    require([mode.get("mode") for mode in result.get("modes", [])] == ["plain", "ubsan"], "fresh plain and UBSan semantic probes required")
    outputs, commands = [], []
    for fresh, old, mode in zip(result["modes"], stored["semantic"], ("plain", "ubsan")):
        directory = absolute(fresh.get("directory")); paths = fresh.get("source_paths", {})
        inputs = {name: generated[name] for name in NATIVE}; inputs["driver.c"] = driver
        require(paths == {name: directory + "/" + name for name in inputs}, "fresh semantic fixture source paths differ")
        binary = absolute(fresh.get("binary_path")); compile_row, execute_row = fresh.get("compile", {}), fresh.get("execute", {})
        _fresh_paths(compile_row, [directory, *paths.values(), binary], seen); _fresh_paths(execute_row, [], seen)
        flags = modules["probe"].compiler_flags(prefix=True, dense=False, previous_index=bool(options), unsigned_history=bool(options), mode=mode)
        require(compile_row.get("cwd") == execute_row.get("cwd") == directory
            and compile_row.get("command") == ["cc", *flags, paths["driver.c"], "-o", binary]
            and execute_row.get("command") == [binary], "fresh semantic original compile/run argv differs")
        output = fresh.get("output"); normalized, summary = modules["probe"].verify_output(output)
        observation = semantic_observation(fresh, old, products[label + "/semantic-" + mode + "/x"], normalized, summary)
        for member, data in inputs.items():
            if member not in ("tiny.h", "board.c", "search.c", "driver.c"):
                continue
            require(products[label + "/semantic-" + mode + "/" + member] == data, "stored actual semantic source differs")
        original = rows[label + "-semantic-run-" + mode]
        require(products[Path(original["stdout"]["path"]).name] == output, "stored actual semantic raw output differs")
        outputs.append(normalized)
        commands.append({"kind": "D-search-semantic-v1", "label": label, "mode": mode, "input_pins": inventory(inputs),
            "driver": pin(driver), "directory": directory, "source_paths": deepcopy(paths), "binary_path": binary,
            **observation, "commands": [deepcopy(compile_row), deepcopy(execute_row)]})
    require(outputs[0] == outputs[1], "fresh plain/UBSan actual search observations differ")
    return outputs[0], commands


def _stored_matrix(record, products, rows, root, valid, valid_proof, selected, flags, modules):
    """Consume the finite original source/semantic/terminal matrix, not flags."""
    baseline_observations = None
    runtime_cases = record.get("runtime_cases", [])
    require([case.get("name") for case in runtime_cases] == [label + "-" + mode for label in PLANS
        for mode in ("valid", "quit", "eof")], "complete original valid/quit/EOF matrix required")
    raw_dialogue = modules["runtime_checker"].DIALOGUE
    witness = '  history=b"g1f3 g8f6 f3g1 f6g8 "*256\n'
    require(raw_dialogue.count(witness) == 1, "original valid dialogue extension boundary differs")
    extension = '  send(b"isready"+b" "*32760+b"\\n");until(b"readyok");record["max_line_payload_bytes"]=32767;save()\n'
    dialogue_source = raw_dialogue.replace(witness, extension + witness).encode()
    small = modules["source"].production().ResourceProfile("search-scaled-runtime", "test", 4, 16 << 12)
    small_flags = modules["builder"].native_flags(small)
    for label, old in zip(PLANS, record["variants"]):
        options = () if label == "control" else OPTIONS if label == SELECTOR else (label,)
        readable, proof = (valid, None) if not options else modules["search"].transform(valid, modules["valid"],
            modules["arity"], modules["owner"], modules["publication"], valid_proof, options=options)
        require(old["name"] == label and old["source"] == inventory(readable) and equal(old["proof"], proof)
                and old["options"] == list(options) and old["flags"] == flags and old["units"] == list(UNITS)
                and old["last_search_output_required"] is False and old["input_domain"] == "TCEC-valid-lines",
                "stored structural variant source/flags/policy differs")
        require(all(products[label + "/generated-readable/" + name] == data for name, data in readable.items()),
                "stored structural readable bytes differ")
        generated, driver, semantic_proof = modules["probe"].render(readable, modules["source"], modules["storage_checker"],
            reference_board=valid["board.c"], variant_proof=proof, prefix=True, dense=False,
            union_order="union-order" in options, previous_index="previous-piece" in options,
            constant_start="constant-start" in options, unsigned_history="unsigned-history" in options)
        require(equal(semantic_proof, old["semantic_proof"]) and [row["mode"] for row in old["semantic"]] == ["plain", "ubsan"],
                "stored actual semantic fixture proof differs")
        for semantic in old["semantic"]:
            mode = semantic["mode"]; directory = root + "/" + label + "/semantic-" + mode
            for name in ("tiny.h", "board.c", "search.c"):
                require(products[label + "/semantic-" + mode + "/" + name] == generated[name], "stored semantic body differs")
            require(products[label + "/semantic-" + mode + "/driver.c"] == driver
                and pin(products[label + "/semantic-" + mode + "/x"]) == semantic["binary"], "stored semantic driver/native differs")
            compile_row, execute = rows[label + "-semantic-compile-" + mode], rows[label + "-semantic-run-" + mode]
            probe_flags = modules["probe"].compiler_flags(prefix=True, dense=False,
                previous_index="previous-piece" in options, unsigned_history="unsigned-history" in options, mode=mode)
            require(compile_row["command"] == ["cc", *probe_flags, directory + "/driver.c", "-o", directory + "/x"]
                and compile_row["cwd"] == execute["cwd"] == directory and execute["command"] == [directory + "/x"],
                "stored actual semantic compile/run argv differs")
            output = products[Path(execute["stdout"]["path"]).name]
            normalized, summary = modules["probe"].verify_output(output)
            if baseline_observations is None: baseline_observations = normalized
            require(normalized == baseline_observations and pin(normalized) == semantic["normalized"]
                and pin(output) == semantic["output"] and equal(summary, semantic["summary"])
                and not products[Path(execute["stderr"]["path"]).name], "stored actual search observations differ")
        pp, entry = rows[label + "-preprocess"], rows[label + "-entry"]
        readable_root = root + "/" + label + "/generated-readable"
        require(pp["command"] == ["cc", "-E", "-P", *flags, "-I", readable_root, "-x", "c", "-"]
            and entry["command"] == ["cc", "-E", "-P", "-x", "assembler-with-cpp", readable_root + "/start.S"]
            and pp["cwd"] == entry["cwd"] == readable_root, "stored preprocessing argv differs")
        driver_input = b"".join(('#include "' + name + '"\n').encode() for name in MEMBERS)
        require(products[Path(pp["stdout"]["path"]).with_suffix(".stdin").name] == driver_input,
                "stored preprocessing exact stdin differs")
        cpp = products[Path(pp["stdout"]["path"]).name]
        emitted = {"main.c": modules["minifier"].compact_source(cpp, "c"),
            "start.S": products[Path(entry["stdout"]["path"]).name], "image.ld": readable["image.ld"]}
        renames = selected["identifier_native_gate"]["accepted_renames"]
        require(old["legacy_renames"] == renames and not set(renames.values()).intersection(
            modules["lexical"]._ANY_WORD.findall(emitted["main.c"].decode())), "stored legacy identifier capture differs")
        for before, after in renames.items():
            emitted["main.c"] = modules["lexical"]._replace({"main.c": emitted["main.c"]}, before, after)["main.c"]
        gate_index = 0
        def stored_digest(c_files, trial):
            nonlocal gate_index
            prefix = label + "/gate-" + str(gate_index) + "/"; gate_index += 1
            files = {**emitted, **c_files}; directory = root + "/" + prefix.rstrip("/")
            require(all(products[prefix + name] == data for name, data in files.items()), "stored reducer exact trial source differs")
            row = rows[label + "-source-gate-" + str(trial)]
            require(row["cwd"] == directory and row["command"] == ["cc", *flags,
                *[directory + "/" + name for name in UNITS], "-Wl,-T," + directory + "/image.ld", "-o", directory + "/linked"],
                "stored full-linked reducer argv differs")
            return pin(products[prefix + "linked"])["sha256"]
        reduced, reduction = modules["reducer"].reduce_sources({"main.c": emitted["main.c"]}, stored_digest, modules["lexical"],
            reserve=modules["lexical"]._ANY_WORD.findall((emitted["start.S"] + emitted["image.ld"]).decode()))
        require(gate_index == 3 and equal(reduction, old["reduction"]), "complete stored reducer stages differ")
        emitted.update(reduced)
        shipping = {name: products[label + "/shipping-inputs/" + name] for name in ("main.c", "start.S", "image.ld")}
        require(shipping == emitted, "stored shipping source composition differs")
        require(inventory(shipping) == old["shipping"], "stored complete shipping inputs differ")
        for index, native in enumerate(old["native"]):
            linked_bytes = products[label + "/native-" + str(index) + "/linked"]
            native_bytes = products[label + "/native-" + str(index) + "/native"]
            require(pin(linked_bytes) == native["linked"] and pin(native_bytes) == native["stripped"]
                and modules["packer"].strip_native(linked_bytes) == native_bytes
                and modules["builder"].kernel_geometry(modules["packer"], linked_bytes, 4) == native["linked_geometry"]
                and modules["builder"].kernel_geometry(modules["packer"], native_bytes, 4) == native["native_geometry"],
                "stored full native image/geometry differs")
            directory = root + "/" + label + "/native-" + str(index)
            shipping_root = root + "/" + label + "/shipping-inputs"
            row = rows[label + "-native-" + str(index)]
            require(row["cwd"] == directory and row["command"] == ["cc", *flags,
                *[shipping_root + "/" + name for name in UNITS], "-Wl,-T," + shipping_root + "/image.ld", "-o", directory + "/linked"],
                "stored final native argv differs")
        _packages(label, shipping, flags, products[label + "/native-0/native"], old["packages"], products, modules)
        for mode in ("valid", "quit", "eof"):
            case = next(case for case in runtime_cases if case["name"] == label + "-" + mode)
            files, instrumentation = (readable, None) if mode == "valid" else modules["checker"].active_instrument(readable,
                modules["source"], modules["owner"])
            prefix = label + "/fixture-" + mode + "/"; directory = root + "/" + prefix.rstrip("/")
            require(case["workers"] == 4 and case["tt_bits"] == 12 and case["mode"] == mode
                and case["last_search_output_required"] is False and case["source_before"] == inventory(readable)
                and equal(case["instrumentation"], instrumentation) and all(products[prefix + name] == data for name, data in files.items())
                and products[prefix + "dialogue.py"] == dialogue_source
                and pin(products[prefix + "x"]) == case["binary"], "stored scoped runtime source/instrumentation differs")
            compile_row, execute = rows[label + "-fixture-compile-" + mode], rows[label + "-fixture-run-" + mode]
            require(compile_row["command"] == ["cc", *small_flags, *[directory + "/" + name for name in modules["source"].UNITS],
                "-Wl,-T," + directory + "/image.ld", "-o", directory + "/x"] and compile_row["cwd"] == execute["cwd"] == directory
                and len(execute["command"]) == 8 and execute["command"][1:] == ["-I", "-B", directory + "/dialogue.py",
                    directory + "/x", directory + "/dialogue.json", mode, "1"], "stored scoped runtime argv differs")
            dialogue = json.loads(products[prefix + "dialogue.json"])
            require(equal(dialogue, case["dialogue"]) and all(dialogue.get(key) is True for key in
                ("complete", "engine_started", "engine_reaped", "inherits_owner_group"))
                and dialogue.get("forced_cleanup") is False and dialogue.get("returncode") == 0
                and dialogue.get("pgid") == dialogue.get("owner_pgid") == execute["pgid"],
                "stored scoped runtime did not settle its original group")
            if mode == "valid":
                require(dialogue.get("max_line_payload_bytes") == 32767 and dialogue.get("history_plies") == 1024,
                        "stored valid input bounds/replay coverage differs")
            else:
                require(dialogue.get("interrupted_after_real_claim") is True, "stored active terminal case never entered search")
    return pin(baseline_observations)


def admit_search(record, frozen_inputs, products, modules, *, current_inputs, admission_source,
                 evidence_root, preprocess, compile_identity, storage_evidence, semantic_callback=None):
    """Freshly replay the exact finite selector and return an immutable token.

    ``semantic_callback`` is mandatory: it compiles and runs control/selected
    actual-search fixtures in plain and UBSan modes through original owners.
    A saved success flag is never a substitute for these fresh observations.
    """
    require(callable(preprocess) and callable(compile_identity) and callable(semantic_callback),
            "fresh preprocessing/full-linked/semantic callbacks are required")
    require(pin((json.dumps(record, indent=2) + "\n").encode()) == RECEIPT,
            "explicit reviewed structural search receipt identity differs")
    modules = _modules(modules); root = absolute(evidence_root)
    recipe = json.loads(frozen_inputs[modules["source_inputs"].RECIPE])
    producer = modules["source_inputs"].producer_names(recipe)
    require(set(frozen_inputs) == set(input_names(record, producer)) and inventory(frozen_inputs) == record["inputs"],
            "frozen search input bytes differ")
    logical = {name for name in frozen_inputs if name.startswith("engines/")}
    require(set(current_inputs) == logical and all(current_inputs[name] == frozen_inputs[name] for name in logical)
        and inventory(current_inputs) == record["source_current_after"], "current/frozen search source closure differs")
    require(set(admission_source) == {"current", "frozen"} and admission_source["current"] == admission_source["frozen"]
        and compile(admission_source["frozen"], __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
        "search admission must consume its current frozen executing source")
    require(set(products) == set(evidence_names(record, producer)), "exact bounded search evidence products required")
    _module_inputs(modules, frozen_inputs)
    rows = {row["kind"]: row for row in record["commands"]}
    for index, row in enumerate(record["commands"], 1): _streams(row, products, root, index)
    require(rows["compiler-version"]["command"] == ["cc", "--version"] and rows["compiler-version"]["cwd"] == root
        and products["tool-1-compiler-version.stdout"].decode().splitlines()[0] == record["compiler"], "stored actual compiler identity differs")
    source, startup, builder = modules["source"], modules["startup"], modules["builder"]
    profile = source.production().resource_profile("test-p4"); flags = builder.native_flags(profile)
    selected = json.loads(frozen_inputs["selection/build.json"])
    require(equal(record["resource"], profile.to_record(16)) and selected.get("resource") == profile.to_record(16)
        and selected.get("storage") == "prefix" and selected.get("source_reduced") is False
        and selected.get("equivalent_edits") is True and set(selected.get("inputs", {})) == set(producer)
        and selected["inputs"] == {name: pin(frozen_inputs[name]) for name in producer}
        and all(selected.get(key) is True for key in ("complete", "frozen_execution", "native_reproduced")),
        "exact complete prefix control/resource/producer required")
    baseline, production = startup.prepared(source, profile, True, modules["storage"], "prefix")
    require(equal(production, record["production_proof"]) and equal(production, selected["proof"]), "complete production projection differs")
    owned, owner_proof = modules["owner"].transform(baseline, modules["publication"])
    require(modules["owner"].restore(owned, owner_proof, modules["publication"]) == baseline
        and equal(owner_proof, record["owner_proof"]), "upstream owner full inverse differs")
    arity, arity_proof = modules["arity"].transform(owned, modules["owner"], modules["publication"], owner_proof,
        noinline_wake=True, immediate_exit=True)
    require(modules["arity"].restore(arity, arity_proof, modules["owner"], modules["publication"]) == owned
        and equal(arity_proof, record["arity_proof"]) and arity_proof.get("last_search_output_required") is False,
        "explicit immediate-exit syscall-arity inverse differs")
    valid, valid_proof = modules["valid"].transform(arity, modules["arity"], modules["owner"], modules["publication"],
        arity_proof, mode="one-byte-valid")
    require(modules["valid"].restore(valid, valid_proof, modules["arity"], modules["owner"], modules["publication"]) == arity
        and equal(valid_proof, record["valid_proof"]) and valid_proof.get("last_search_output_required") is False,
        "explicit one-byte valid input full inverse differs")
    candidate, proof = modules["search"].transform(valid, modules["valid"], modules["arity"], modules["owner"],
        modules["publication"], valid_proof, options=OPTIONS)
    require(modules["search"].restore(candidate, proof, modules["valid"], modules["arity"], modules["owner"],
        modules["publication"]) == valid, "complete structural search inverse differs")
    storage = _storage(storage_evidence, frozen_inputs, modules)
    variants = record["variants"]
    require([row["name"] for row in variants] == list(PLANS) and record["proved_one_factor_wins"] == list(OPTIONS), "exact finite selector matrix differs")
    stored_semantics = _stored_matrix(record, products, rows, root, valid, valid_proof, selected, flags, modules)
    seen, fresh, semantic_outputs, generated = set(), [], [], {}
    for label, readable, structural, expected_identity in (("control", valid, None, CONTROL), (SELECTOR, candidate, proof, IDENTITY)):
        old = next(row for row in variants if row["name"] == label)
        require(old["options"] == ([] if label == "control" else list(OPTIONS)) and old["source"] == inventory(readable)
            and equal(old["proof"], structural) and old["last_search_output_required"] is False
            and old["input_domain"] == "TCEC-valid-lines" and old["flags"] == flags and old["units"] == list(UNITS),
            "selected structural source/policy/flags differs")
        require(all(products[label + "/generated-readable/" + name] == data for name, data in readable.items()), "actual selected readable source differs")
        normalized, observations = _semantic(label, readable, structural, valid, old, products, rows, root, modules, semantic_callback, seen)
        semantic_outputs.append(normalized); fresh.extend(observations)
        cpp, pp = fresh_preprocess(preprocess(dict(readable), list(flags), list(MEMBERS), label), readable, flags, label, seen)
        fresh.append(pp)
        require(cpp["main.c"] == products[Path(rows[label + "-preprocess"]["stdout"]["path"]).name]
            and cpp["start.S"] == products[Path(rows[label + "-entry"]["stdout"]["path"]).name], "fresh/stored complete preprocessing differs")
        driver = b"".join(('#include "' + name + '"\n').encode() for name in MEMBERS)
        require(products[Path(rows[label + "-preprocess"]["stdout"]["path"]).with_suffix(".stdin").name] == driver,
                "stored preprocessing stdin differs")
        emitted = {"main.c": modules["minifier"].compact_source(cpp["main.c"], "c"), "start.S": cpp["start.S"], "image.ld": readable["image.ld"]}
        renames = selected["identifier_native_gate"]["accepted_renames"]
        require(old["legacy_renames"] == renames and len(set(renames.values())) == len(renames)
            and all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", value) for pair in renames.items() for value in pair)
            and not set(renames.values()).intersection(modules["lexical"]._ANY_WORD.findall(emitted["main.c"].decode())),
            "legacy identifier map captures an actual spelling")
        for before, after in renames.items():
            emitted["main.c"] = modules["lexical"]._replace({"main.c": emitted["main.c"]}, before, after)["main.c"]
        trials = []
        def digest(c_files, trial):
            files = {**emitted, **c_files}; tag = label + "/reducer/" + str(trial)
            linked, native, receipt = fresh_compile(compile_identity(dict(files), list(flags), list(UNITS), tag), files, flags, UNITS, tag, modules, seen)
            fresh.append(receipt); trials.append((trial, linked, files)); return pin(linked)["sha256"]
        reduced, reduction = modules["reducer"].reduce_sources({"main.c": emitted["main.c"]}, digest, modules["lexical"],
            reserve=modules["lexical"]._ANY_WORD.findall((emitted["start.S"] + emitted["image.ld"]).decode()))
        require(equal(reduction, old["reduction"]) and [str(trial) for trial, _, _ in trials] == ["baseline", "typedefs", "batch-alpha"],
                "every fresh full-linked reducer gate must replay")
        for index, (trial, linked, files) in enumerate(trials):
            require(products[label + "/gate-" + str(index) + "/linked"] == linked
                and all(products[label + "/gate-" + str(index) + "/" + name] == data for name, data in files.items()),
                "stored reducer trial inputs/full-linked bytes differ")
        emitted.update(reduced)
        require(inventory(emitted) == old["shipping"] and all(products[label + "/shipping-inputs/" + name] == data for name, data in emitted.items()),
                "actual final search shipping source differs")
        images = []
        for repeat in range(2):
            tag = label + "/native-repeat/" + str(repeat)
            linked, native, receipt = fresh_compile(compile_identity(dict(emitted), list(flags), list(UNITS), tag), emitted, flags, UNITS, tag, modules, seen)
            fresh.append(receipt); images.append((linked, native))
            require(old["native"][repeat] == {"linked": pin(linked), "stripped": pin(native), "linked_geometry": receipt["geometry"], "native_geometry": receipt["native_geometry"]}
                and products[label + "/native-" + str(repeat) + "/linked"] == linked
                and products[label + "/native-" + str(repeat) + "/native"] == native,
                "fresh final native/repetition/geometry differs")
        require(images[0] == images[1] and {"linked": pin(images[0][0]), "stripped": pin(images[0][1])} == expected_identity,
                "explicit structural class native identity differs")
        packages, package_images = _packages(label, emitted, flags, images[0][1], old["packages"], products, modules)
        generated[label] = {"readable": readable, "shipping": emitted, "linked": images[0][0], "native": images[0][1],
            "packages": packages, "package_images": package_images, "composition": _composition(renames, reduction)}
    require(semantic_outputs[0] == semantic_outputs[1], "control/candidate actual search/order/learner observations differ")
    result = generated[SELECTOR]
    require(pin(result["package_images"]["packed-xz-bcj"]) == PACKED, "reviewed5261 complete package differs")
    record_out = {"kind": KIND, "family": "D", "selector": SELECTOR, "options": list(OPTIONS),
        "ownership_policy": "TCEC-minimum-immediate-process-exit", "last_search_output_required": False,
        "scope": "local TCEC-targeted minimal shutdown contract; event approval unconfirmed",
        "event_target_confirmed": False,
        "input_contract": "TCEC-valid-non-NUL-lines-at-most-32767-bytes", "profile": profile.to_record(16),
        "flags": list(flags), "units": list(UNITS), "identity": deepcopy(IDENTITY), "packages": result["packages"],
        "input_pins": inventory(frozen_inputs), "admission_source": pin(admission_source["frozen"]),
        "source_admitted": True, "native_admitted": True, "package_generation_admitted": True,
        "actual_search_semantics_admitted": True, "source_proof": proof, "production_proof": production,
        "owner_proof": owner_proof, "arity_proof": arity_proof, "valid_proof": valid_proof,
        "identifier_composition": result["composition"], "fresh_commands": fresh, "storage_evidence": storage,
        "semantic_observations": pin(semantic_outputs[0]), "stored_semantic_observations": stored_semantics, "original_experiment": RECEIPT,
        "ready_for_fresh_full_P4": True, "fresh_full_artifact_runtime": False, "rules_qualified": False,
        "physical_placement_qualified": False, "size_qualified": False, "whole_artifact_qualified": False, "selected": False}
    return SearchAdmission(_TOKEN, record_out, result["readable"], result["shipping"], result["package_images"], result["native"], result["linked"])
