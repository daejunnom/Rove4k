#!/usr/bin/env python3
"""Explicit, unselected P4 D-owner source/rules/runtime qualification.

Fresh source admission and original owned callbacks precede a new carrier.
Actual shipped-board rules and generic runtime observations remain separately
recorded. This never invokes the old D admission or qualification registry.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
BRIDGE_SHA = "2f55825ecc5c69c11ba77d7918791831b272dbd49f9e8020e2940b88ef9e410f"
SUPPORT = ("engines/experiments/tcec-next/profile_verify.py",
    "engines/experiments/tcec-next/profile_rules.py",
    "engines/experiments/tcec-scope/verify.py",
    "engines/compact/tiny-entry-d/verify.py", "engines/tests/chess_oracle.py",
    "engines/scripts/production.py")
LOGICAL = dict(source=D+"source.py", builder=D+"build.py", storage=D+"storage.py",
    publication=D+"publication.py", owner=D+"process_owner.py", startup=D+"test_startup.py",
    checker=D+"test_process_owner.py", reducer=D+"reduce.py", packaging=D+"packaging.py",
    lexical="engines/scripts/rename_c.py", minifier="engines/scripts/minify.py",
    packer="engines/compact/tiny-entry-d/packer.py")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def normalized(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named qualification source")
    return data


def safe(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and ".." not in relative.parts,
        "bounded qualification evidence name required")
    path = root / relative
    for part in (path, *path.parents):
        if part == root:
            break
        require(not part.is_symlink(), "qualification evidence cannot follow links")
    require(path.is_file() and path.stat().st_nlink == 1,
        "qualification evidence must be a regular non-hard-linked file")
    return path.read_bytes()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out, experiment = args.out.resolve(), args.experiment.resolve()
    require(sys.platform == "linux" and platform.machine() == "x86_64" and
        args.out.is_absolute() and args.experiment.is_absolute() and
        not out.exists() and not any((p / ".git").exists() for p in (out, *out.parents)),
        "new absolute external output and absolute owner experiment on Linux x86-64 required")
    tool_names = (D+"owner_admission.py", D+"owner_runtime.py", D+"qualify_owner.py")
    tools = {name: normalized(ROOT/name) for name in tool_names}
    require(pin(tools[D+"owner_runtime.py"])["sha256"] == BRIDGE_SHA,
        "frozen reviewed owner runtime bridge differs")
    discovery = load("D_owner_qualification_input_grammar", ROOT/(D+"owner_admission.py"))
    original = safe(experiment, "results.json")
    record = json.loads(original)
    inputs = {name: safe(experiment, "inputs/"+name) for name in discovery.input_names(record)}
    products = {name: safe(experiment, name) for name in discovery.evidence_names(record)}
    current = {name: normalized(ROOT/name) for name in inputs if name.startswith("engines/")}
    require(all(current[name] == inputs[name] for name in current),
        "current producer differs from owner experiment before qualification")
    support = {name: normalized(ROOT/name) for name in SUPPORT}
    out.mkdir()
    for name, data in {**inputs, **{"products/"+n:d for n,d in products.items()}}.items():
        write(out/"evidence", name, data)
    for name, data in tools.items():
        write(out/"tools", name, data)
    for name, data in support.items():
        write(out/"support", name, data)
    write(out, "original-results.json", original)
    frozen = load("D_owner_qualification_frozen", out/"tools"/(D+"qualify_owner.py"))
    frozen.run_snapshot(out, experiment, ROOT, record, original, inputs, products,
        current, tools, support)


def run_snapshot(out, experiment, current_root, record, original, inputs, products,
                 current, tools, support):
    admission = load("D_owner_qualification_admission", out/"tools"/(D+"owner_admission.py"))
    bridge = load("D_owner_qualification_bridge", out/"tools"/(D+"owner_runtime.py"))
    runtime = load("D_owner_qualification_runtime", out/"support"/SUPPORT[0])
    shared = load("D_owner_qualification_rules", out/"support"/SUPPORT[1])
    logical = dict(LOGICAL)
    if admission.BOOTSTRAP in inputs:
        logical["bootstrap"] = admission.BOOTSTRAP
    modules = {name:load("D_owner_qual_"+name, out/"evidence"/path)
        for name, path in logical.items()}
    host_name = "engines/experiments/tcec-scope/build.py"
    require(pin(inputs[host_name])["sha256"] == modules["source"].HOST_SHA,
        "original command owner differs")
    for name, digest in runtime.SUPPORT.items():
        require(pin(support[name])["sha256"] == digest, "original runtime support differs: "+name)
    hostmod = load("D_owner_qualification_commands", out/"evidence"/host_name)
    hostmod.LIMITS = {**hostmod.LIMITS, "aggregate_wall": 300,
        "per_command_wall": 40, "parent_CPU": 480, "parent_CPU_hard": 600,
        "child_CPU": 25}
    report = {"kind": "rove4k.D-process-owner-P4-qualification.v1", "complete": False,
        "commands": [], "original_experiment": pin(original),
        "inputs": admission.inventory(inputs), "current_inputs": admission.inventory(current),
        "tools": admission.inventory(tools), "runtime_support": admission.inventory(support),
        "frozen_execution": True, "old_D_admission_used": False,
        "source_admitted": False, "native_admitted": False,
        "package_generation_admitted": False, "rules_qualified": False,
        "fresh_full_artifact_runtime": False, "physical_placement_qualified": False,
        "size_qualified": False, "real_target_allocation": False,
        "strength_qualified": False, "selected": False}
    def save():
        (out/"qualification.json").write_text(json.dumps(report, indent=2)+"\n")
    save()
    host = hostmod.Host(out, report, save)
    host_closed = False
    counter = 0
    def run(command, *, cwd, kind, data=None):
        output = host.run(command, cwd=cwd, kind=kind, data=data)
        row = dict(report["commands"][-1])
        admission._settled(row, 0)
        return output, row
    def preprocess(files, flags, members, label):
        nonlocal counter
        counter += 1
        directory = out/("fresh-pp-"+str(counter)+"-"+label)
        directory.mkdir()
        for name, data in files.items():
            write(directory, name, data)
        driver = b''.join(('#include "'+name+'"\n').encode() for name in members)
        main, row = run(["cc", "-E", "-P", *flags, "-I", str(directory), "-x", "c", "-"],
            cwd=directory, kind="independent-preprocess-single-"+label, data=driver)
        entry, entry_row = run(["cc", "-E", "-P", "-x", "assembler-with-cpp", str(directory/"start.S")],
            cwd=directory, kind="independent-preprocess-entry-"+label)
        return {"kind":"D-owner-preprocess-v1", "label":label,
            "input_pins":admission.inventory(files), "flags":flags, "members":members,
            "driver":driver, "readable_dir":str(directory), "commands":[row, entry_row],
            "outputs":{"main.c":main, "start.S":entry}}
    def compile_identity(files, flags, units, label):
        nonlocal counter
        counter += 1
        directory = out/("fresh-native-"+str(counter)+"-"+label.replace("/", "-"))
        directory.mkdir()
        for name, data in files.items():
            write(directory, name, data)
        linked_path, native_path = directory/"linked", directory/"native"
        _, row = run(["cc", *flags, *[str(directory/name) for name in units],
            "-Wl,-T,"+str(directory/"image.ld"), "-o", str(linked_path)],
            cwd=directory, kind="independent-compile-"+label.replace("/", "-"))
        linked = linked_path.read_bytes()
        native = modules["packer"].strip_native(linked)
        native_path.write_bytes(native)
        return {"kind":"D-owner-native-compile-v1", "label":label,
            "input_pins":admission.inventory(files), "flags":flags, "units":units,
            "source_paths":{n:str(directory/n) for n in files},
            "linked_path":str(linked_path), "stripped_path":str(native_path),
            "linked":linked, "stripped":native, "linked_pin":pin(linked),
            "stripped_pin":pin(native), "command":row}
    def preprocess_board(files, flags, label):
        nonlocal counter
        counter += 1
        directory = out/("fresh-board-"+str(counter))
        directory.mkdir()
        for name, data in files.items():
            write(directory, name, data)
        output, row = run(["cc", "-E", "-P", *flags, str(directory/"board.c")],
            cwd=directory, kind="independent-preprocess-actual-owner-board")
        return {"kind":"D-owner-board-preprocess-v1", "label":label,
            "input_pins":admission.inventory(files), "flags":flags,
            "readable_dir":str(directory), "output":output, "command":row}
    try:
        named, admitted, replay = bridge.prepare_carrier(record, inputs, products, modules,
            admission=admission, current_inputs=current,
            admission_source={"current":tools[D+"owner_admission.py"], "frozen":tools[D+"owner_admission.py"]},
            bridge_source={"current":tools[D+"owner_runtime.py"], "frozen":tools[D+"owner_runtime.py"]},
            evidence_root=str(experiment), preprocess=preprocess,
            compile_identity=compile_identity, route="native-xz-bcj", runtime=runtime)
        carrier = out/"carrier"
        carrier.mkdir()
        for name, data in named.items():
            write(carrier, name, data)
        (carrier/"program").chmod(0o700)
        report.update(source_admitted=True, native_admitted=True,
            package_generation_admitted=True, carrier=admission.inventory(named),
            expected=admitted.expected, source_contract=admitted.source_contract,
            resources=admitted.resources, fresh_commands=replay["fresh_commands"],
            scaled_contract=replay["scaled_contract"])
        save()
        cases, coverage = shared.fixture_cases()
        fixture, receipt = bridge.render_rules(replay, cases,
            preprocess_board=preprocess_board, admission=admission, shared=shared,
            minifier=modules["minifier"], lexical=modules["lexical"])
        rules = out/"rules"
        rules.mkdir()
        (rules/"fixture.c").write_bytes(fixture)
        rules_report = {**receipt, "coverage":coverage, "complete":False, "modes":[]}
        def save_rules():
            (rules/"rules.json").write_text(json.dumps(rules_report, indent=2)+"\n")
        save_rules()
        for mode, extra in (("plain", []), ("ubsan", ["-fsanitize=undefined", "-fno-sanitize-recover=all"])):
            program = rules/("probe-"+mode)
            run(["cc", "-std=c11", "-O1", "-g0", "-fno-builtin", "-msse4.2", "-mcx16",
                *extra, str(rules/"fixture.c"), "-o", str(program)],
                cwd=rules, kind="actual-owner-rules-compile-"+mode)
            output, _ = run([str(program)], cwd=rules, kind="actual-owner-rules-execute-"+mode)
            rules_report["modes"].append({"mode":mode, "native":pin(program.read_bytes()),
                **shared._compare_output(output, cases)})
            save_rules()
        rules_report.update(complete=True, compiled=True, executed=True, rules_qualified=True)
        save_rules()
        report.update(rules_qualified=True, rules=pin((rules/"rules.json").read_bytes()))
        for row in report["commands"]:
            admission._settled(row, 0)
        host.close()
        host_closed = True
        require(report.get("host_cleanup") == {"unsettled_commands":0, "errors":[]},
            "source/rules owned commands not fully settled before runtime")
        limits = runtime.execution_limits(admitted, runtime.effective_available_bytes(), wall_seconds=300)
        report["runtime_limits"] = limits
        save()
        observed = runtime.run_runtime(admitted, carrier, out/"runtime", limits)
        report["equivalent_output_contract"] = bridge.require_equivalent_terminal_output(observed)
        report["fresh_full_artifact_runtime"] = True
        report["runtime"] = pin((out/"runtime/runtime.json").read_bytes())
        report["physical_placement_qualified"] = observed["execution_host"]["test_physical_envelope_observed"]
        report["size_qualified"] = admitted.expected["whole_bytes"] <= 4096
        for name, data in {**current, **tools, **support}.items():
            require(normalized(current_root/name) == data, "qualification source changed during execution: "+name)
        for name, data in named.items():
            require(safe(carrier, name) == data, "carrier changed during execution: "+name)
        report.update(current_frozen_closure_unchanged=True, carrier_unchanged=True, complete=True)
    except BaseException as error:
        report["complete"] = False
        report["failure"] = {"type":type(error).__name__, "message":str(error)}
        raise
    finally:
        try:
            if not host_closed:
                host.close()
        except BaseException as error:
            report["complete"] = False
            report["cleanup_failure"] = {"type":type(error).__name__, "message":str(error)}
            raise
        finally:
            if report.get("host_cleanup", {}).get("errors") or report.get("host_cleanup", {}).get("unsettled_commands"):
                report["complete"] = False
            save()
    require(report["complete"], "owner qualification incomplete")
    print(json.dumps({k:report[k] for k in ("complete", "source_admitted", "native_admitted",
        "package_generation_admitted", "rules_qualified", "fresh_full_artifact_runtime",
        "physical_placement_qualified", "size_qualified", "selected")}), flush=True)


if __name__ == "__main__":
    main()
