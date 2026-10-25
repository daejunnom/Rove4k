#!/usr/bin/env python3
"""Generate scalar D profiles and both general-4K representations from source.

Build/size observations are not runtime qualification. In particular, compiling
the W256/TT34 target never allocates its TT. Use the separate verifier for real
execution after host admission. Outputs must be new and outside every checkout.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def normalized(path):
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in named producer input")
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def native_flags(profile, optimize="s"):
    if optimize not in ("s", "2", "z"):
        raise ValueError("finite D compiler optimization required")
    return ["-O" + optimize, "-std=c11", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic",
            "-fno-stack-protector", "-fno-builtin", "-fno-asynchronous-unwind-tables",
            "-fno-unwind-tables", "-fno-ident", "-fcf-protection=none", "-ffunction-sections",
            "-fdata-sections", "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack", "-flto",
            "-msse4.2", "-mcx16", "-DDEV=0", "-DD_HQ=0",
            f"-DWORKERS={profile.workers}", f"-DTT_BITS={profile.layout(16).bits}"]


def kernel_geometry(packer, native, workers):
    """The new source-owned dynamic-TT kernel class; no legacy guard change."""
    geometry = packer.elf(native)
    if len(geometry["segments"]) != 3:
        raise ValueError("three kernel program headers required")
    rx, rw, stack = geometry["segments"]
    base, page = 0x400000, 4096
    if (rx["type"] != 1 or rx["flags"] != 5 or rx["offset"] != 0 or
            rx["vaddr"] != base or rx["paddr"] != base or rx["align"] != page or
            not 232 < rx["filesz"] <= len(native) or rx["memsz"] != rx["filesz"] or
            not base + 232 <= geometry["entry"] < base + rx["filesz"]):
        raise ValueError("kernel RX/header/entry extent differs")
    end = base + (rx["memsz"] + page - 1) // page * page
    if (rw["type"] != 1 or rw["flags"] != 6 or rw["offset"] != 0 or rw["filesz"] != 0 or
            rw["vaddr"] != end or rw["paddr"] != end or rw["align"] != page or
            not 0 < rw["memsz"] < workers * (128 << 10) + (1 << 20)):
        raise ValueError("kernel dynamic-TT private BSS extent differs")
    if (stack["type"] != 0x6474E551 or stack["flags"] != 6 or
            any(stack[k] != 0 for k in ("offset", "vaddr", "paddr", "filesz", "memsz"))):
        raise ValueError("nonexecuting kernel stack header differs")
    return geometry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("test-p4", "test-p28", "tcec-provisional"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--control", action="store_true", help="omit previously qualified REP/byte/reply/dead-score edits; keep resource correctness")
    parser.add_argument("--rename-trials", type=int, default=32, help="bounded complete-native-identity identifier trials")
    parser.add_argument("--source-shape", choices=("single", "split"), default="single")
    parser.add_argument("--optimize", choices=("s", "2", "z"), default="s")
    parser.add_argument("--storage", choices=("none", "prefix", "dense", "prefix-dense"), default="none")
    parser.add_argument("--source-reduce", action="store_true", help="gate unused scalar typedef pruning and batch alpha renaming by complete native identity")
    args = parser.parse_args()
    out = args.out.resolve()
    if (not args.out.is_absolute() or out.exists() or
            any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("new absolute output outside every Git checkout required")
    if sys.platform != "linux" or platform.machine() != "x86_64":
        parser.error("Linux x86-64 required")
    if not 0 <= args.rename_trials <= 64:
        parser.error("rename trials must be between zero and 64")
    names = tuple("engines/compact/tiny-entry-d/native/" + n for n in
                  ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")) + (
        "engines/compact/tiny-entry-d/recipe.json", "engines/compact/tiny-entry-d/shipping_fused_ray.py",
        "engines/compact/tiny-entry-d/packer.py", "engines/experiments/tcec-scope/build.py",
        "engines/scripts/production.py", "engines/scripts/minify.py", "engines/scripts/rename_c.py",
        "engines/experiments/tiny-d-submission/source.py", "engines/experiments/tiny-d-submission/build.py",
        "engines/experiments/tiny-d-submission/packaging.py")
    recipe = json.loads(normalized(ROOT / "engines/compact/tiny-entry-d/recipe.json"))
    names += tuple(recipe["shared_source_sha256"]) + tuple(recipe["helper_sha256"])
    if args.storage != "none":
        names += ("engines/experiments/tiny-d-submission/storage.py",)
    if args.source_reduce:
        names += ("engines/experiments/tiny-d-submission/reduce.py",)
    frozen = {name: normalized(ROOT / name) for name in names}
    # Every generator/module below, including the executing build logic, is
    # loaded from this snapshot. Concurrent workspace edits cannot substitute
    # new pins for source bytes already consumed by a prior module instance.
    out.mkdir()
    for name, data in frozen.items():
        path = out / "inputs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    executing = load("tiny_d_frozen_build", out / "inputs/engines/experiments/tiny-d-submission/build.py")
    executing.build_snapshot(args, out, frozen, ROOT)


def build_snapshot(args, out, frozen, working_root):
    source = load("tiny_d_submission_source", HERE / "source.py")
    packaging = load("tiny_d_submission_packaging", HERE / "packaging.py")
    api = source.production()
    profile = api.resource_profile(args.profile)
    files, proof = source.prepare(profile, equivalent_edits=not args.control)
    if args.storage != "none":
        storage = load("tiny_d_submission_storage", HERE / "storage.py")
        files, storage_proof = storage.transform(files, prefix="prefix" in args.storage, dense="dense" in args.storage)
        proof["storage"] = storage_proof
    # Pin the existing command owner instead of duplicating its PID/group logic.
    host_path = ROOT / source.HOST
    if source.pin(source.normalized(host_path))["sha256"] != source.HOST_SHA:
        raise ValueError("bounded command owner differs")
    tools = load("tiny_d_submission_host", host_path)
    tools.LIMITS = {**tools.LIMITS, "aggregate_wall": 600, "per_command_wall": 90,
                    "parent_CPU": 240, "parent_CPU_hard": 270, "child_CPU": 60}
    minifier = load("tiny_d_submission_minifier", ROOT / "engines/scripts/minify.py")
    renamer = load("tiny_d_submission_renamer", ROOT / "engines/scripts/rename_c.py")
    packer = load("tiny_d_submission_elf", source.CANONICAL / "packer.py")
    report = dict(format="rove4k-D-general-source-v1", family="D", complete=False,
                  resource=profile.to_record(16), proof=proof, commands=[],
                  runtime_qualified=False, selected=False,
                  equivalent_edits=not args.control,
                  storage=args.storage,
                  source_reduced=args.source_reduce,
                  scope="source generation, repeated native/whole reproduction and general size only",
                  source_root="engines/compact/tiny-entry-d/native", candidates=[])
    report["inputs"] = {name: source.pin(data) for name, data in frozen.items()}
    report["frozen_execution"] = True
    def save():
        (out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    flags = native_flags(profile, args.optimize)
    report["flags"] = flags
    save()
    host = tools.Host(out, report, save)
    try:
        original = out / "generated-readable"
        original.mkdir()
        for name, data in files.items():
            (original / name).write_bytes(data)
        report["compiler"] = host.run(["cc", "--version"], cwd=out, kind="compiler-version").decode().splitlines()[0]
        emitted = {}
        units = source.UNITS
        # Remove DEV/HQ code before it becomes a compressed source payload.
        if args.source_shape == "single":
            aggregate = b''.join(('#include "' + name + '"\n').encode() for name in source.UNITS if name.endswith('.c'))
            data = host.run(["cc", "-E", "-P", *flags, "-I", str(original), "-x", "c", "-"],
                            cwd=out, kind="preprocess-single-TU", data=aggregate)
            emitted["main.c"] = minifier.compact_source(data, "c")
            units = ("main.c", "start.S")
            report["single_TU"] = dict(members=[n for n in source.UNITS if n.endswith('.c')],
                                       driver=source.pin(aggregate), preprocessed=source.pin(data))
        for name in source.UNITS:
            if name.endswith(".c"):
                if args.source_shape == "single":
                    continue
                data = host.run(["cc", "-E", "-P", *flags, str(original / name)],
                                cwd=out, kind="preprocess-" + name)
                emitted[name] = minifier.compact_source(data, "c")
            else:
                emitted[name] = host.run(["cc", "-E", "-P", "-x", "assembler-with-cpp", str(original / name)],
                                         cwd=out, kind="preprocess-entry")
        emitted["image.ld"] = files["image.ld"]
        prepared = out / "shipping-inputs"
        prepared.mkdir()
        if args.rename_trials or args.source_reduce:
            gate = out / "identifier-gate"
            gate.mkdir()
            def compile_digest(c_files, trial):
                combined = {**emitted, **c_files}
                for name, data in combined.items():
                    (gate / name).write_bytes(data)
                host.run(["cc", *flags, *[str(gate / n) for n in units],
                          "-Wl,-T," + str(gate / "image.ld"), "-o", str(gate / "linked")],
                         cwd=gate, kind="identifier-native-" + str(trial))
                return source.pin(packer.strip_native((gate / "linked").read_bytes()))["sha256"]
            if args.source_reduce:
                reducer = load("tiny_d_submission_reducer", HERE / "reduce.py")
                reduced, reduction_proof = reducer.reduce_sources(
                    {name: data for name, data in emitted.items() if name.endswith('.c')},
                    compile_digest, renamer,
                    reserve=renamer._ANY_WORD.findall((emitted["start.S"] + emitted["image.ld"]).decode()))
                emitted.update(reduced)
                report["source_reduction"] = reduction_proof
            if args.rename_trials:
                renamed, rename_proof = renamer.compact_identifiers(
                    {name: data for name, data in emitted.items() if name.endswith('.c')},
                    compile_digest, max_trials=args.rename_trials)
                emitted.update(renamed)
                report["identifier_native_gate"] = rename_proof
        report["shipping_inputs"] = {name: source.pin(data) for name, data in emitted.items()}
        report["units"] = list(units)
        for name, data in emitted.items():
            (prepared / name).write_bytes(data)
        native_rows = []
        for index in range(2):
            directory = out / ("attempt-" + str(index))
            directory.mkdir()
            command = ["cc", *flags, *[str(prepared / name) for name in units],
                       "-Wl,-T," + str(prepared / "image.ld"), "-o", str(directory / "linked")]
            host.run(command, cwd=directory, kind="compile-native-" + str(index))
            native = packer.strip_native((directory / "linked").read_bytes())
            geometry = kernel_geometry(packer, native, profile.workers)
            (directory / "native").write_bytes(native)
            (directory / "native").chmod(0o755)
            native_rows.append(dict(path=str(directory / "native"), **source.pin(native), geometry=geometry))
            linked = (directory / "linked").read_bytes()
            report.setdefault("source_jit_native_rebuilds", []).append(
                dict(path=str(directory / "linked"), **source.pin(linked), geometry=kernel_geometry(packer, linked, profile.workers)))
        if (out / "attempt-0/native").read_bytes() != (out / "attempt-1/native").read_bytes():
            raise ValueError("native reproduction differs")
        report["native"] = native_rows[0]
        report["native_rebuilds"] = native_rows
        report["native_reproduced"] = True
        for gate_name in ("source_reduction", "identifier_native_gate"):
            if (gate_name in report and
                    report[gate_name]["final_native_sha256"] != native_rows[0]["sha256"]):
                raise ValueError("final repeated native differs from " + gate_name)
        if (out / "attempt-0/linked").read_bytes() != (out / "attempt-1/linked").read_bytes():
            raise ValueError("source-JIT native reproduction differs")
        report["source_jit_native"] = report["source_jit_native_rebuilds"][0]
        for kind in ("alone", "xz", "xz-bcj"):
            whole, detail = packaging.package_native(native, kind)
            repeated, _ = packaging.package_native(native, kind)
            if whole != repeated:
                raise ValueError("native package reproduction differs")
            path = out / ("D-packed-" + kind)
            path.write_bytes(whole)
            path.chmod(0o755)
            plan = api.ArtifactPlan(api.engine_spec("D"), profile, "packed-native", "none")
            report["candidates"].append(dict(path=str(path), representation="packed-native", native=native_rows[0],
                package_reproduced=True, package_rebuilds=[source.pin(whole), source.pin(repeated)], **detail,
                **source.pin(whole), size_decision=plan.size_decision(len(whole), "general4k")))
        whole, detail = packaging.package_source(emitted, flags, units)
        repeated, _ = packaging.package_source(emitted, flags, units)
        if whole != repeated:
            raise ValueError("source package reproduction differs")
        path = out / "D-source-jit"
        path.write_bytes(whole)
        path.chmod(0o755)
        plan = api.ArtifactPlan(api.engine_spec("D"), profile, "source-jit", "none")
        report["candidates"].append(dict(path=str(path), representation="source-jit", native=report["source_jit_native"],
            package_reproduced=True, package_rebuilds=[source.pin(whole), source.pin(repeated)], **detail,
            **source.pin(whole), size_decision=plan.size_decision(len(whole), "general4k")))
        report["minimum_measured"] = min(report["candidates"], key=lambda row: row["bytes"])
        report["complete"] = True
        print(json.dumps(dict(profile=args.profile, native=len(native),
                              whole=report["minimum_measured"]["bytes"], runtime_qualified=False)), flush=True)
    except BaseException as error:
        report["complete"] = False
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        try:
            host.close()
        except BaseException as error:
            report["complete"] = False
            report["cleanup_failure"] = dict(type=type(error).__name__, message=str(error))
            raise
        finally:
            cleanup = report.get("host_cleanup", {})
            if cleanup.get("unsettled_commands") or cleanup.get("errors"):
                report["complete"] = False
            try:
                report["working_closure_unchanged"] = all(normalized(working_root / name) == data for name, data in frozen.items())
            except (OSError, ValueError) as error:
                report["working_closure_unchanged"] = False
                report["working_closure_observation_error"] = dict(type=type(error).__name__, message=str(error))
            save()


if __name__ == "__main__":
    main()
