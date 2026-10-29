#!/usr/bin/env python3
"""Fresh source, rules and P4 runtime qualification for one explicit D search class.

The 5261-byte immediate-exit candidate is independent of the final-wait owner
class. Original experiment evidence remains immutable. This driver freezes its
entire consumer closure before invoking callbacks or the shipping artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
_EXECUTING_CODE = sys._getframe().f_code
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
TOOLS = (D + "search_admission.py", D + "search_runtime.py", D + "qualify_search.py")
SUPPORT = ("engines/experiments/tcec-next/profile_verify.py",
    "engines/experiments/tcec-next/profile_rules.py", "engines/experiments/tcec-scope/verify.py",
    "engines/compact/tiny-entry-d/verify.py", "engines/tests/chess_oracle.py",
    "engines/scripts/production.py", "engines/scripts/production_input.py")
LOGICAL = dict(source=D+"source.py", builder=D+"build.py", storage=D+"storage.py",
    publication=D+"publication.py", owner=D+"process_owner.py", startup=D+"test_startup.py",
    checker=D+"test_process_owner.py", packaging=D+"packaging.py", bootstrap=D+"compressed_bootstrap.py",
    reducer=D+"reduce.py", arity=D+"syscall_arity.py", valid=D+"valid_input.py",
    runtime_checker=D+"test_runtime_scaffold.py", search=D+"search_compact.py",
    probe=D+"probe_search_compact.py", storage_checker=D+"check_storage.py", source_inputs=D+"source_inputs.py",
    lexical="engines/scripts/rename_c.py", minifier="engines/scripts/minify.py",
    packer="engines/compact/tiny-entry-d/packer.py")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def normalized(path):
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named search qualifier source")
    return data


def safe(root, name, *, maximum=16 << 20):
    relative = Path(name)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.parts,
            "explicit relative search evidence required")
    path = Path(root) / relative
    require(not any(part.is_symlink() for part in (path, *path.parents)), "search evidence cannot follow links")
    require(path.is_file() and path.stat().st_nlink == 1 and path.stat().st_size <= maximum,
            "bounded ordinary search evidence required")
    data = path.read_bytes()
    require(len(data) <= maximum, "search evidence changed beyond its byte bound")
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_bytes(name, path, data):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists(), "search qualifier will not overwrite evidence")
    path.write_bytes(data)


def runtime_support(root):
    return {name: normalized(root / name) for name in SUPPORT}


def require_support(runtime, support):
    expected = set(runtime.SUPPORT) | {SUPPORT[0], SUPPORT[1], "engines/scripts/production.py", runtime.INPUT_READER}
    require(set(support) == expected, "complete frozen search runtime/rules support required")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--storage-evidence", type=Path, required=True)
    parser.add_argument("--selector", choices=("proved-win-combination",), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 search qualifier required")
    require(all(path.is_absolute() and ".." not in path.parts for path in
                (args.out, args.experiment, args.storage_evidence)), "absolute original evidence and new output required")
    out, experiment, storage_root = args.out.resolve(), args.experiment.resolve(), args.storage_evidence.resolve()
    require(not out.exists() and not any((parent / ".git").exists() for parent in (out, *out.parents)),
            "new external search output required")
    tools = {name: normalized(ROOT / name) for name in TOOLS}
    require(compile(tools[D+"qualify_search.py"], __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "search qualifier source changed after execution began")
    admission = load_bytes("D_search_discovery", ROOT / (D+"search_admission.py"), tools[D+"search_admission.py"])
    source_inputs = load_bytes("D_search_input_names", ROOT / LOGICAL["source_inputs"], normalized(ROOT / LOGICAL["source_inputs"]))
    original = safe(experiment, "results.json")
    record = json.loads(original)
    recipe = json.loads(safe(experiment, "inputs/" + source_inputs.RECIPE))
    producer = source_inputs.producer_names(recipe)
    inputs = {name: safe(experiment, "inputs/" + name) for name in admission.input_names(record, producer)}
    products = {name: safe(experiment, name) for name in admission.evidence_names(record, producer)}
    current = {name: normalized(ROOT / name) for name in inputs if name.startswith("engines/")}
    require(all(current[name] == inputs[name] for name in current), "current search producer differs from frozen inputs")
    storage_raw = safe(storage_root, "results.json")
    storage_record = json.loads(storage_raw)
    storage_products = {name: safe(storage_root, name) for name in admission.storage_evidence_names(storage_record)}
    support = runtime_support(ROOT)
    out.mkdir()
    for name, data in inputs.items():
        write(out / "evidence", name, data)
    for name, data in products.items():
        write(out / "products", name, data)
    for name, data in storage_products.items():
        write(out / "storage-products", name, data)
    for name, data in tools.items():
        write(out / "tools", name, data)
    for name, data in support.items():
        write(out / "support", name, data)
    write(out, "original-results.json", original)
    write(out, "storage-results.json", storage_raw)
    frozen = load("D_search_frozen_qualifier", out / "tools" / (D+"qualify_search.py"))
    frozen.run_snapshot(out, experiment, storage_root, ROOT, record, original, inputs, products,
        current, tools, support, storage_raw, storage_products, args.selector)


def run_snapshot(out, experiment, storage_root, current_root, record, original, inputs, products,
                 current, tools, support, storage_raw, storage_products, selector):
    admission = load("D_search_frozen_admission", out / "tools" / (D+"search_admission.py"))
    bridge = load("D_search_frozen_runtime", out / "tools" / (D+"search_runtime.py"))
    runtime = load("D_search_frozen_R", out / "support" / SUPPORT[0])
    shared = load("D_search_frozen_rules", out / "support" / SUPPORT[1])
    require_support(runtime, support)
    modules = {name: load("D_search_qual_" + name, out / "evidence" / path) for name, path in LOGICAL.items()}
    host_path = "engines/experiments/tcec-scope/build.py"
    require(pin(inputs[host_path])["sha256"] == modules["source"].HOST_SHA, "bounded search command owner differs")
    for name, digest in runtime.SUPPORT.items():
        require(pin(support[name])["sha256"] == digest, "literal runtime support differs")
    host_module = load("D_search_qual_commands", out / "evidence" / host_path)
    host_module.LIMITS = {**host_module.LIMITS, "aggregate_wall": 900, "per_command_wall": 45,
                         "parent_AS": 4 << 30, "parent_CPU": 480, "parent_CPU_hard": 600, "child_CPU": 40}
    report = {"kind": "rove4k.D-structural-search-P4-qualification.v1", "complete": False, "commands": [],
        "selector": selector, "original_experiment": pin(original), "storage_evidence": pin(storage_raw),
        "inputs": admission.inventory(inputs), "current_inputs": admission.inventory(current),
        "tools": admission.inventory(tools), "runtime_support": admission.inventory(support),
        "frozen_execution": True, "old_D_admission_used": False, "owner_final_wait_authority_used": False,
        "source_admitted": False, "native_admitted": False, "package_generation_admitted": False,
        "rules_qualified": False, "fresh_full_artifact_runtime": False, "physical_placement_qualified": False,
        "size_qualified": False, "strength_qualified": False, "real_target_allocation": False, "selected": False,
        "shutdown_scope": "local TCEC-targeted minimal shutdown contract; event approval unconfirmed",
        "event_target_confirmed": False}
    def save():
        (out / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    host = host_module.Host(out, report, save)
    host_closed, counter = False, 0
    def run(command, *, cwd, kind, data=None):
        output = host.run(command, cwd=cwd, kind=kind, data=data)
        row = dict(report["commands"][-1])
        admission._settled(row)
        return output, row
    def directory(label):
        nonlocal counter
        require(isinstance(label, str) and label and all(part not in ("", ".", "..") for part in label.split("/")),
                "finite internal callback label required")
        counter += 1
        path = out / ("fresh-" + str(counter) + "-" + label.replace("/", "-"))
        path.mkdir()
        return path
    def preprocess(files, flags, members, label):
        path = directory("pp-" + label)
        for name, data in files.items():
            write(path, name, data)
        driver = b''.join(('#include "' + name + '"\n').encode() for name in members)
        main, first = run(["cc", "-E", "-P", *flags, "-I", str(path), "-x", "c", "-"],
            cwd=path, kind="independent-search-preprocess-" + label, data=driver)
        entry, second = run(["cc", "-E", "-P", "-x", "assembler-with-cpp", str(path / "start.S")],
            cwd=path, kind="independent-search-entry-" + label)
        return {"kind": "D-search-preprocess-v1", "label": label, "input_pins": admission.inventory(files),
            "flags": list(flags), "members": list(members), "driver": driver, "readable_dir": str(path),
            "commands": [first, second], "outputs": {"main.c": main, "start.S": entry}}
    def compile_identity(files, flags, units, label):
        path = directory("native-" + label)
        for name, data in files.items():
            write(path, name, data)
        linked_path, native_path = path / "linked", path / "native"
        _, row = run(["cc", *flags, *[str(path / name) for name in units],
            "-Wl,-T," + str(path / "image.ld"), "-o", str(linked_path)],
            cwd=path, kind="independent-search-compile-" + label.replace("/", "-"))
        linked = linked_path.read_bytes()
        native = modules["packer"].strip_native(linked)
        write(path, "native", native)
        return {"kind": "D-search-native-compile-v1", "label": label, "input_pins": admission.inventory(files),
            "flags": list(flags), "units": list(units), "source_paths": {name: str(path / name) for name in files},
            "linked_path": str(linked_path), "stripped_path": str(native_path), "linked": linked, "stripped": native,
            "linked_pin": pin(linked), "stripped_pin": pin(native), "command": row}
    def semantic_callback(readable, *, label, options, valid_readable, structural_proof):
        generated, driver, proof = modules["probe"].render(readable, modules["source"], modules["storage_checker"],
            reference_board=valid_readable["board.c"], prefix=True, dense=False, variant_proof=structural_proof,
            union_order="union-order" in options, previous_index="previous-piece" in options,
            constant_start="constant-start" in options, unsigned_history="unsigned-history" in options)
        modes = []
        for mode in ("plain", "ubsan"):
            path = directory("semantic-" + label + "-" + mode)
            for name, data in generated.items():
                write(path, name, data)
            write(path, "driver.c", driver)
            program = path / "fixture"
            flags = modules["probe"].compiler_flags(prefix=True, dense=False,
                previous_index="previous-piece" in options, unsigned_history="unsigned-history" in options, mode=mode)
            _, compile_row = run(["cc", *flags, str(path / "driver.c"), "-o", str(program)],
                cwd=path, kind="fresh-search-semantic-compile-" + label + "-" + mode)
            output, execute_row = run([str(program)], cwd=path, kind="fresh-search-semantic-run-" + label + "-" + mode)
            modes.append({"mode": mode, "directory": str(path),
                "source_paths": {name: str(path / name) for name in (*generated, "driver.c")},
                "binary_path": str(program), "binary": program.read_bytes(), "output": output,
                "compile": compile_row, "execute": execute_row})
        return {"kind": "D-search-semantic-v1", "label": label, "options": list(options),
            "input_pins": admission.inventory(readable), "instrumented": generated,
            "driver": driver, "proof": proof, "modes": modes}
    def preprocess_board(files, flags, label):
        path = directory("board-" + label)
        for name, data in files.items():
            write(path, name, data)
        output, row = run(["cc", "-E", "-P", *flags, str(path / "board.c")],
            cwd=path, kind="independent-search-actual-board")
        return {"kind": "D-search-board-preprocess-v1", "label": label,
            "input_pins": admission.inventory(files), "flags": list(flags),
            "readable_dir": str(path), "output": output, "command": row}
    try:
        token = admission.admit_search(record, inputs, products, modules, current_inputs=current,
            admission_source={"current": tools[D+"search_admission.py"], "frozen": tools[D+"search_admission.py"]},
            evidence_root=str(experiment), preprocess=preprocess, compile_identity=compile_identity,
            storage_evidence={"raw": storage_raw, "root": str(storage_root), "products": storage_products},
            semantic_callback=semantic_callback)
        require(token.to_record()["selector"] == selector, "explicit search selector differs")
        named, accepted = bridge.prepare_carrier(token, admission_module=admission,
            admission_source={"current": tools[D+"search_admission.py"], "frozen": tools[D+"search_admission.py"]},
            bridge_source={"current": tools[D+"search_runtime.py"], "frozen": tools[D+"search_runtime.py"]},
            runtime=runtime, packaging=modules["packaging"], frozen_inputs=inputs)
        carrier = out / "carrier"
        carrier.mkdir()
        for name, data in named.items():
            write(carrier, name, data)
        (carrier / "program").chmod(0o700)
        report.update(source_admitted=True, native_admitted=True, package_generation_admitted=True,
            admission=token.to_record(), carrier=admission.inventory(named), expected=accepted.expected,
            resources=accepted.resources, source_contract=accepted.source_contract)
        save()
        cases, coverage = shared.fixture_cases()
        fixture, receipt = bridge.render_rules(token, cases, admission_module=admission,
            preprocess_board=preprocess_board, shared=shared, minifier=modules["minifier"], lexical=modules["lexical"])
        rules = out / "rules"
        rules.mkdir()
        write(rules, "fixture.c", fixture)
        rules_report = {**receipt, "coverage": coverage, "complete": False, "modes": []}
        def save_rules():
            (rules / "rules.json").write_text(json.dumps(rules_report, indent=2) + "\n")
        save_rules()
        for mode, extra in (("plain", []), ("ubsan", ["-fsanitize=undefined", "-fno-sanitize-recover=all"])):
            program = rules / ("probe-" + mode)
            _, compiled = run(["cc", "-std=c11", "-O1", "-g0", "-fno-builtin", "-msse4.2", "-mcx16",
                *extra, str(rules / "fixture.c"), "-o", str(program)], cwd=rules, kind="actual-search-rules-compile-" + mode)
            output, executed = run([str(program)], cwd=rules, kind="actual-search-rules-run-" + mode)
            rules_report["modes"].append({"mode": mode, "native": pin(program.read_bytes()),
                "compile": compiled, "execute": executed, **shared._compare_output(output, cases)})
            save_rules()
        rules_report.update(complete=True, compiled=True, executed=True, rules_qualified=True)
        save_rules()
        report.update(rules_qualified=True, rules=pin((rules / "rules.json").read_bytes()))
        host.close()
        host_closed = True
        require(report.get("host_cleanup") == {"unsettled_commands": 0, "errors": []}, "fresh search tools not settled")
        limits = runtime.execution_limits(accepted, runtime.effective_available_bytes(), wall_seconds=300)
        report["runtime_limits"] = limits
        save()
        observed = runtime.run_runtime(accepted, carrier, out / "runtime", limits)
        report.update(runtime=pin((out / "runtime/runtime.json").read_bytes()), runtime_counts=observed["counts"],
            fresh_full_artifact_runtime=observed["complete"] and observed["owned_remaining"] == 0,
            size_qualified=accepted.expected["whole_bytes"] <= 4096,
            physical_placement_qualified=observed["execution_host"]["test_physical_envelope_observed"],
            input_domain="TCEC-valid-non-NUL-lines-at-most-32767-bytes",
            ownership_policy="TCEC-minimum-immediate-process-exit", last_search_output_required=False)
        require(all(normalized(current_root / name) == data for name, data in current.items()),
                "current producer changed during search qualification")
        require(all(normalized(current_root / name) == data for name, data in {**tools, **support}.items()),
                "search admission/bridge/runtime source changed during qualification")
        require(all(safe(carrier, name) == data for name, data in named.items()), "search carrier changed during execution")
        report.update(current_frozen_closure_unchanged=True, carrier_unchanged=True)
        report["complete"] = report["fresh_full_artifact_runtime"] and report["rules_qualified"]
        save()
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        save()
        raise
    finally:
        if not host_closed:
            try:
                host.close()
            except BaseException as error:
                report["cleanup_failure"] = {"type": type(error).__name__, "message": str(error)}
                report["complete"] = False
                save()
                raise
        save()
    require(report["complete"], "fresh search qualification did not complete")
    print(json.dumps({key: report[key] for key in ("complete", "source_admitted", "native_admitted",
        "package_generation_admitted", "rules_qualified", "fresh_full_artifact_runtime", "size_qualified",
        "physical_placement_qualified", "selected")}), flush=True)


if __name__ == "__main__":
    main()
