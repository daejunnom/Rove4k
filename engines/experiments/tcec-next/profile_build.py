#!/usr/bin/env python3
"""Regenerate one full C engine for a named test or submission profile.

Every run freshly invokes the maintained, pinned tracked-source producer.
There is no historical source/binary input, runtime family selector, implicit
reduced feature policy, or automatic selected-recipe update. Building a large
TT profile only compiles/packages it; no engine is executed by this command.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import shutil
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SELF = "engines/experiments/tcec-next/profile_build.py"
CLASS = "rove4k-production-profile-v1"
BASELINE = "engines/experiments/tcec-next/build.py"
COMMON = "engines/scripts/production.py"
SOURCE = "engines/experiments/tcec-next/profile_source.py"
VERIFIER = "engines/experiments/tcec-next/profile_verify.py"
PACKAGE = "engines/scripts/source_package.py"
WRAPPER = "engines/experiments/tcec-next/wrapper.py"
UNLINK = "engines/experiments/tcec-next/self_unlink.py"
ELF = "engines/scripts/elf_loader.py"
B_PROFILE = "engines/experiments/tcec-next/profile_b.py"
PHASE = "engines/experiments/tcec-next/profile_phase.py"
DEPENDENCIES = "engines/experiments/tcec-next/profile_dependencies.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def normalized(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in named source input: " + str(path))
    return data


def _tool_path(path, family):
    """The payload producer and its old receipt verifier are separate roles."""
    if path in (VERIFIER, "engines/experiments/tcec-next/profile_rules.py"):
        return False
    name = Path(path).name
    return ((path.endswith(".py") and not path.startswith("engines/tests/") and
             not name.startswith(("test", "check", "verify", "fresh"))) or
            name == "recipe.json" or path == "engines/model/e19.json" or
            path in (f"engines/compact/tiny-entry-{family.lower()}/bootstrap.py.in",
                     f"engines/compact/tiny-entry-{family.lower()}/launcher.sh"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", choices=tuple("ABCEF"), required=True)
    parser.add_argument("--profile", choices=("test-p4", "test-p28", "tcec-provisional"), required=True)
    parser.add_argument("--representation", choices=("source-jit", "packed-native", "self-contained-elf"),
                        default="source-jit")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compile-cc", help="final native/type-gate compiler only; runtime wrapper still uses admitted cc argv")
    parser.add_argument("--b-variant", default="control",
                        help="explicit reviewed B post-profile projection; default preserves the control")
    parser.add_argument("--phase-variant", choices=("control", "phase-init"), default="control",
                        help="explicit measured A/C/E/F lifecycle projection; default preserves the control")
    parser.add_argument("--source-dependencies", choices=("control", "unused-includes"),
                        default="unused-includes",
                        help="reviewed final include cleanup with expanded-input/native/whole-cost gates")
    args = parser.parse_args()
    if args.b_variant != "control" and args.entry != "B":
        parser.error("--b-variant applies only to the independently owned B engine")
    if args.phase_variant != "control" and args.entry not in "ACEF":
        parser.error("--phase-variant applies only to A/C/E/F")
    out = args.out.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or
            not args.out.is_absolute() or out.exists() or
            ROOT in (out, *out.parents) or any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("Linux x86-64 and a new absolute output outside every Git checkout are required")
    source_bytes = normalized(ROOT / SOURCE)
    common_bytes = normalized(ROOT / COMMON)
    executing = normalized(Path(__file__))
    production = load("profile_build_contracts", ROOT / COMMON)
    projection = load("profile_build_projection", ROOT / SOURCE)
    spec, profile = production.engine_spec(args.entry), production.resource_profile(args.profile)
    cleanup = "none" if args.representation == "self-contained-elf" else "private-path"
    plan = production.ArtifactPlan(spec, profile, args.representation, cleanup)
    old = load("profile_build_owner", ROOT / "engines/experiments/tcec-scope/build.py")
    resources = {**profile.to_record(spec.entry_bytes), "ply": 128, "max_position_plies": 4095}
    runtime = old.runtime_policy("per-go", "async", profile.workers)
    runtime.update(initialization_threads=profile.os_threads,
                   initialization_join_before_uci=True, entry_cleanup=cleanup)
    report = dict(format=1, **{"class": CLASS}, entry=args.entry, family=args.entry,
        complete=False, reproducible=False, plan=plan.to_record(), resources=resources,
        runtime_policy=runtime, commands=[], attempts=[], source_proofs=[],
        qualification=dict(selection="new-profile-measurement", runtime=False,
                           rules_eligibility="unproven", game_strength="unproven"),
        authority="fresh maintained tracked-source producer then bound profile projection",
        execution_policy="compile/package only; engine and TT are never executed or allocated here")
    out.mkdir()

    def save():
        (out / "build.json").write_text(json.dumps(report, indent=2) + "\n")

    class Host(old.Host):
        def settle(self, child, row, force=False):
            if row.get("kind") == "fresh-profile-control":
                row["cooperative_termination_seconds"] = 30
            return super().settle(child, row, force)

    old.LIMITS.update(aggregate_wall=1800, per_command_wall=600, parent_AS=4 << 30,
                      child_AS=4 << 30, parent_CPU=300, parent_CPU_hard=480, child_CPU=420)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    host = Host(out, report, save)
    try:
        # This nested builder independently freezes and verifies its complete
        # tracked closure; no caller-supplied control artifact is accepted.
        host.run([sys.executable, "-I", "-B", ROOT / BASELINE, "--entry", args.entry,
                  "--measure", "--out", out / "control"], cwd=out, kind="fresh-profile-control")
        control_raw = (out / "control/build.json").read_bytes()
        control = json.loads(control_raw)
        old.require(control["complete"] and control["reproducible"] and
                    control["host_cleanup"] == {"unsettled_commands": 0, "errors": []} and
                    all(c["returncode"] == 0 and c["terminal"] and c["reaped"] and
                        c["owned_group_absent"] and not c["forced_cleanup"] for c in control["commands"]),
                    "fresh maintained control incomplete or unsettled")
        base = (out / "control/main.c").read_bytes()
        old.require((len(base), old.sha(base)) == projection.INPUTS[args.entry],
                    "fresh maintained profile input differs")
        old.require(normalized(ROOT / SOURCE) == source_bytes and
                    normalized(ROOT / COMMON) == common_bytes and normalized(Path(__file__)) == executing,
                    "executing profile producer changed before input freeze")
        names = set(control["control_source_closure"]) | set(control["inputs"])
        names.update((SELF, COMMON, SOURCE, PACKAGE, WRAPPER, UNLINK))
        if args.entry == "E":
            names.update(("engines/model/e19.py", "engines/model/e19.json"))
        if args.b_variant != "control":
            names.add(B_PROFILE)
        if args.phase_variant != "control":
            names.add(PHASE)
        if args.source_dependencies != "control":
            names.add(DEPENDENCIES)
        if args.representation in ("packed-native", "self-contained-elf"):
            names.add(ELF)
        if args.representation == "self-contained-elf":
            names.update((ELF, "engines/scripts/elf-loader/loader.c", "engines/scripts/elf-loader/loader.ld"))
        # The new runtime verifier is a proof dependency, never payload code.
        if (ROOT / VERIFIER).is_file():
            names.add(VERIFIER)
        inputs = {}
        for name in sorted(names):
            data = normalized(ROOT / name)
            expected = control["control_source_closure"].get(name, control["inputs"].get(name))
            old.require(expected is None or old.pin(data) == expected,
                        "tracked baseline input changed after regeneration: " + name)
            target = out / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            inputs[name] = old.pin(data)
        tools = tuple(name for name in sorted(names) if _tool_path(name, args.entry))
        engine_inputs = list(spec.source_inputs)
        if args.representation == "self-contained-elf":
            engine_inputs.extend(("engines/scripts/elf-loader/loader.c", "engines/scripts/elf-loader/loader.ld"))
        tools = tuple(name for name in tools if name not in engine_inputs)
        closure = production.SourceClosure.validate(spec, engine_inputs=tuple(engine_inputs),
                                                    tool_inputs=tools, submission=True)
        snapshot = production.snapshot_closure(ROOT, closure,
            expected={name: inputs[name]["sha256"] for name in (*closure.engine_inputs, *closure.tool_inputs)})
        producer_paths = set((*closure.engine_inputs, *closure.tool_inputs, *closure.test_inputs))
        report.update(inputs=inputs, source_closure=snapshot.to_record(),
            proof_inputs={name: pin for name, pin in inputs.items() if name not in producer_paths},
            control_source_closure=control["control_source_closure"],
            control=dict(source=old.pin(base), report=old.pin(control_raw),
                         expected_contract=control["expected_contract"], path="control"),
            selected_verifier=dict(path=VERIFIER, command=[sys.executable, "-I", "-B",
                str(ROOT / VERIFIER), "--build", str(out), "--out", "<new external output>"]))
        own = out / "inputs"
        projection = load("profile_frozen_projection", own / SOURCE)
        frozen_production = load("profile_frozen_contracts", own / COMMON)
        profile = frozen_production.resource_profile(args.profile)
        packaging = load("profile_frozen_package", own / PACKAGE)
        wrapper = load("profile_frozen_wrapper", own / WRAPPER)
        unlink = load("profile_frozen_unlink", own / UNLINK)
        compiler, compression = control["compiler"], control["compression"]
        compile_executor = list(compiler)
        if args.compile_cc:
            compile_executor[0] = args.compile_cc
        report.update(compiler=compiler, compile_executor=compile_executor, compression=compression)
        report["post_profile"] = (dict(path=B_PROFILE, variant=args.b_variant)
            if args.b_variant != "control" else dict(path=PHASE, variant=args.phase_variant)
            if args.phase_variant != "control" else None)
        dependencies = (load("profile_frozen_dependencies", own / DEPENDENCIES)
                        if args.source_dependencies != "control" else None)
        report["source_dependencies"] = dict(dependencies.DECLARATION) if dependencies else None
        if args.representation == "source-jit":
            report["wrapper_contract"] = wrapper.contract(packaging, unlink, compiler)
        elif args.representation == "packed-native":
            report["wrapper_contract"] = dict(policy="private-file-native-delayed-directory-cleanup",
                argv0="wrapper-owned private absolute executable path", entry_cleanup=cleanup,
                cleanup_child=True, runtime_qualified=False)
        else:
            report["wrapper_contract"] = dict(policy="self-contained-memfd-loader", entry_cleanup="none",
                temporary_pathname=False, outer_preserved=True, runtime_qualified=False)
        old.LIMITS["child_AS"] = 2 << 30
        old.LIMITS["child_CPU"] = 120
        report["compile_executor_version"] = host.run([compile_executor[0], "--version"], cwd=out,
            kind="target-compiler-version").decode("utf-8", "strict").splitlines()[0]
        header_name, payload_name = (("header.bin", "payload.bin")
            if args.representation == "self-contained-elf" else ("header.sh", "payload.lzma"))
        report["package_parts"] = dict(header=header_name, payload=payload_name,
            codec="rove4k-lz-runs-v1" if args.representation == "self-contained-elf" else "lzma-alone")
        for attempt in ("first", "repeat"):
            directory = out / attempt
            native_dir = directory / "native"
            native_dir.mkdir(parents=True)
            source, proof = projection.transform_source(base, family=args.entry, profile=profile,
                                                        entry_cleanup=cleanup)
            old.require(projection.restore_source(source, proof) == base,
                        "profile projection inverse differs")
            proofs = [proof]
            abi_probe = None
            if args.b_variant != "control":
                b_profile = load("profile_frozen_B_projection", own / B_PROFILE)
                parent_source = source
                source, b_proof = b_profile.transform_source(source, profile_id=profile.id,
                    entry_cleanup=cleanup, variant=args.b_variant)
                old.require(b_profile.restore_source(source, b_proof) == parent_source,
                            "B post-profile inverse differs")
                proofs.append(b_proof)
                abi_probe = b_proof.get("target_abi_probe")
                old.require(abi_probe is None or
                            (isinstance(abi_probe, str) and abi_probe.strip() and "\0" not in abi_probe),
                            "B target ABI probe must be nonempty standalone C text")
            if args.phase_variant != "control":
                phase = load("profile_frozen_phase_projection", own / PHASE)
                parent_source = source
                source, phase_proof = phase.transform_source(source, family=args.entry,
                    profile_id=profile.id, entry_cleanup=cleanup, variant=args.phase_variant)
                old.require(phase.restore_source(source, phase_proof) == parent_source,
                            "portable phase post-profile inverse differs")
                proofs.append(phase_proof)
            if args.entry == "E":
                model_module = load("profile_e19_canonical", own / "engines/model/e19.py")
                model = model_module.Model.load(own / "engines/model/e19.json")
                source_model = model_module.Model.from_physical_source(source,
                    model_id="e19-admitted-source-baseline")
                source, model_proof = model.bind_physical_table(source, source_model=source_model)
                proofs.append(model_proof)
                report["model"] = dict(id=model.model_id, coefficient_sha256=model.coefficient_sha256(),
                    bounds=model.bounds(), source_coefficient_sha256=source_model.coefficient_sha256(),
                    model_parameters_changed=model.coefficients != source_model.coefficients,
                    optimizer_executed_by_builder=False)
            dependency_gate = None
            before_dependencies = source
            if dependencies:
                source, dependency_proof = dependencies.transform_source(source)
                proofs.append(dependency_proof)
                if source != before_dependencies:
                    dependency_gate = dependencies.compile_gate(before_dependencies, source,
                        compiler=compile_executor, directory=directory / "dependency-gate",
                        run=host.run, prefix=attempt)
            (directory / "main.c").write_bytes(source)
            gate = directory / "target-type-gate"
            gate.mkdir()
            asserted = source + b"\n" + ("\n".join(proof["target_type_assertions"]) + "\n").encode()
            host.run(compile_executor, cwd=gate, kind=attempt + "-target-types", data=asserted)
            host.run(compile_executor, cwd=native_dir, kind=attempt + "-compile", data=source)
            native = (native_dir / "x").read_bytes()
            old.require((gate / "x").read_bytes() == native,
                        "target type assertions changed the shipping native image")
            if dependency_gate is not None:
                old.require(dependency_gate["native"] == old.pin(native) and
                            (directory / "dependency-gate/x").read_bytes() == native,
                            "include removal changed the native image")
            abi_gate = None
            if abi_probe is not None:
                # ABI assertions are a separate translation unit. In particular,
                # feature macros and system headers never prefix shipping C.
                abi_directory = directory / "target-abi-gate"
                abi_directory.mkdir()
                probe_bytes = abi_probe.encode("utf-8")
                (abi_directory / "probe.c").write_bytes(probe_bytes)
                host.run([*compile_executor, "-c"], cwd=abi_directory,
                         kind=attempt + "-target-abi", data=probe_bytes)
                abi_gate = dict(directory="target-abi-gate", source=old.pin(probe_bytes),
                    object=old.pin((abi_directory / "x").read_bytes()), compile_only=True,
                    production_source_modified=False)
            loader = None
            if args.representation == "source-jit":
                header = wrapper.header(packaging, unlink, compiler)
                whole = wrapper.package(packaging, unlink, source, compression, compiler)
                payload = whole[len(header):]
                decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                old.require(decoder.decompress(payload, max_length=len(source) + 1) == source and
                            decoder.eof and not decoder.unused_data, "strict source restoration differs")
            elif args.representation == "packed-native":
                elf = load("profile_native_elf_admission", own / ELF)
                whole = packaging.package_shell(native, compression, kind="native", elf_admission=elf._elf)
                header = packaging.shell_header(kind="native")
                payload = whole[len(header):]
                decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                old.require(decoder.decompress(payload, max_length=len(native) + 1) == native and
                            decoder.eof and not decoder.unused_data, "strict native restoration differs")
            else:
                raw = host.run([sys.executable, "-I", "-B", own / ELF, native_dir / "x",
                                directory / "x", "--timeout", "120", "--cc", compile_executor[0]], cwd=directory,
                               kind=attempt + "-self-contained-loader")
                loader = json.loads(raw)
                whole = (directory / "x").read_bytes()
                boundary = loader["loader_and_headers_bytes"]
                header, payload = whole[:boundary], whole[boundary:]
                old.require(len(payload) == loader["payload_bytes"] and
                            loader["input_sha256"] == old.sha(native), "loader/native identity differs")
                elf = load("profile_elf_restore_check", own / ELF)
                restored = elf._decompress(payload, len(native))
                if loader["filter"] == "bcj":
                    restored = elf._bcj(restored, inverse=True)
                old.require(restored == native, "actual self-contained payload restoration differs")
                loader["actual_output_payload_restores_native"] = True
            old.require(whole.startswith(header), "package header differs")
            if dependency_gate is not None:
                before_whole = (wrapper.package(packaging, unlink, before_dependencies, compression, compiler)
                                if args.representation == "source-jit" else whole)
                old.require(len(whole) <= len(before_whole), "include removal grew the complete artifact")
                dependency_gate["whole_cost"] = dict(before=len(before_whole), after=len(whole))
            for name, data in (("main.c", source), ("x", whole), (header_name, header),
                               (payload_name, payload)):
                (directory / name).write_bytes(data)
            (directory / "x").chmod(0o700)
            (directory / "source-proof.json").write_text(json.dumps(proofs, indent=2) + "\n")
            actual = {kind + "_" + key: value for kind, data in
                      (("source", source), ("native", native), ("whole", whole),
                       ("header", header), ("payload", payload)) for key, value in old.pin(data).items()}
            report["attempts"].append(dict(directory=attempt, **actual, source_proofs=proofs,
                target_type_gate=dict(assertions=proof["target_type_assertions"],
                    source=old.pin(asserted), native=old.pin(native), image_identical=True), loader=loader,
                dependency_gate=dependency_gate))
            if abi_gate is not None:
                report["attempts"][-1]["target_abi_gate"] = abi_gate
            if dependencies:
                def checked(root, name, expected):
                    data = (root / name).read_bytes()
                    old.require(old.pin(data) == expected, "dependency evidence identity differs: " + name)
                    return data
                dependencies.validate_receipt(out, report, dependency_proof, source, checked=checked)
            save()
        a, b = report["attempts"]
        # Loader command metadata contains its own output path; byte identity,
        # proof and target types are the reproducibility contract.
        same = lambda row: {k: v for k, v in row.items() if k not in ("directory", "loader")}
        old.require(same(a) == same(b), "independent profile reproduction differs")
        report["expected_contract"] = {key: value for key, value in a.items()
            if key not in ("directory", "source_proofs", "target_type_gate", "target_abi_gate", "loader", "dependency_gate")}
        report["source_proofs"] = a["source_proofs"]
        report["actual"] = dict(source="main.c", native="native/x", program="x")
        for name in ("main.c", "native/x", "x", header_name, payload_name, "source-proof.json"):
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(out / "first" / name, target)
        (out / "x").chmod(0o700)
        report["qualification"]["divisions"] = [plan.size_decision(len((out / "x").read_bytes()), division)
                                                for division in ("general4k", "elf4k")]
        report.update(complete=True, reproducible=True)
        save()
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    finally:
        try:
            host.close()
        finally:
            signal.signal(signal.SIGCHLD, previous)
    print(json.dumps(dict(entry=args.entry, profile=args.profile, representation=args.representation,
                          whole=report["expected_contract"]["whole_bytes"], complete=True)))


if __name__ == "__main__":
    main()
