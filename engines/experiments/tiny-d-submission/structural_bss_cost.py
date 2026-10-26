"""One nonselected BSS-TT cost cohort: strict P4 control, BSS P4, TT33 layout.

Only compiler and fixed-recipe packaging are executed. Generated native/JIT
programs are never invoked. No production, typed, runtime or size admission is
created. The caller must bound all setup/work/cleanup to 600+30 seconds.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import platform
import stat
import struct
import sys
from types import CodeType, FunctionType, ModuleType

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
SELF = D+"structural_bss_cost.py"
CORE = D+"build_structural.py"
BSS = D+"bss_tt_runtime.py"
CORE_PIN = (40699, "66cbd6172081852fb3d153052bea4de4846e2007dd5f6ec568eeb698eeaca39d")
BSS_PIN = (8297, "e9f2eeea0025bc1bd3ec021505ce663d3f0c24440adeab6edcae20dda0d83a92")
FORMAT = "rove4k-D-structural-bss-cost-v1"
FILE_BYTES = 8 << 20
WORK_SECONDS = 600
CLEANUP_SECONDS = 30
_EXECUTING_CODE = sys._getframe().f_code


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _expected(pair):
    return {"bytes": pair[0], "sha256": pair[1]}


def _normalized(path):
    before = Path(path).lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= 1 << 20,
            "bounded regular source required")
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    after = Path(path).lstat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and b"\r" not in data,
            "source changed or contains lone CR")
    return data


def _authenticate(module, raw, constants):
    require(type(module) is ModuleType and sys.modules.get(module.__name__) is module,
            "registered actual cost/helper module required")
    require(type(raw) is bytes and b"\r" not in raw and _normalized(module.__file__) == raw,
            "executing cost/helper source differs")
    code = compile(raw, module.__file__, "exec", dont_inherit=True)
    if module.__name__ == __name__:
        require(code == _EXECUTING_CODE, "executing controller frame differs")
    for item in code.co_consts:
        if isinstance(item, CodeType) and item.co_flags & 2 and not item.co_name.startswith("<"):
            function = module.__dict__.get(item.co_name)
            require(type(function) is FunctionType and function.__code__ == item and
                    function.__globals__ is module.__dict__, "executing cost/helper function differs")
    reference = {"__name__": "D_bss_cost_frozen_reference", "__file__": module.__file__}
    exec(code, reference)
    require(all(type(module.__dict__.get(name)) is type(reference[name]) and
                module.__dict__[name] == reference[name] for name in constants), "frozen cost/helper constants differ")


def _self(raw):
    _authenticate(sys.modules[__name__], raw,
        ("HERE", "ROOT", "D", "SELF", "CORE", "BSS", "CORE_PIN", "BSS_PIN", "FORMAT",
         "FILE_BYTES", "WORK_SECONDS", "CLEANUP_SECONDS"))


def _load(name, path, raw):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def _core(root):
    raw = _normalized(Path(root) / CORE)
    require(pin(raw) == _expected(CORE_PIN), "reviewed shared generation core differs")
    module = _load("D_bss_cost_generation_core", Path(root) / CORE, raw)
    module.authenticate_generation_source(raw)
    return module


def capture_inputs(root=ROOT):
    _self(_normalized(__file__))
    core = _core(root)
    baseline = core.capture_inputs(root)
    helper = _normalized(Path(root) / BSS)
    require(pin(helper) == _expected(BSS_PIN), "reviewed BSS source prototype differs")
    result = {**baseline, BSS: helper, SELF: _normalized(__file__)}
    validate_inputs(result, core)
    return result


def validate_inputs(inputs, core):
    require(type(inputs) is dict and set(inputs) == set(core.REVIEWED_INPUTS) | {core.SELF, BSS, SELF},
            "exact forty baseline plus BSS/controller source closure required")
    _self(inputs[SELF])
    require(pin(inputs[CORE]) == _expected(CORE_PIN) and pin(inputs[BSS]) == _expected(BSS_PIN),
            "fixed generation core/BSS source differs")
    baseline = {name: inputs[name] for name in (*core.REVIEWED_INPUTS, core.SELF)}
    core.validate_inputs(baseline)
    require(len(baseline) == 40 and len(inputs) == 42, "fixed cost source count differs")
    return baseline


def _bss(root, raw):
    require(pin(raw) == _expected(BSS_PIN), "reviewed BSS source required")
    module = _load("D_bss_cost_source_projection", Path(root) / BSS, raw)
    _authenticate(module, raw, ("SCHEMA", "INPUT", "TT_SYMBOL", "TT_INPUT_SECTION", "TT_OUTPUT_SECTION"))
    return module


def _apply_bss(helper, files, owner, bits):
    projected, proof = helper.transform(files, owner, tt_bits=bits)
    require(helper.restore(projected, proof, owner) == files, "BSS complete inverse differs")
    replay, replay_proof = helper.transform(dict(files), owner, tt_bits=bits)
    require(replay == projected and replay_proof == proof and proof["tt_bits"] == bits and
            proof["tt_bytes"] == (1 << bits)*16, "canonical BSS replay/profile differs")
    return projected, proof


def _file_limit():
    import resource
    inherited = resource.getrlimit(resource.RLIMIT_FSIZE)
    finite = [value for value in inherited if value != resource.RLIM_INFINITY]
    chosen = min([FILE_BYTES, *finite])
    require(chosen > 0, "inherited file-size limit prevents cost generation")
    resource.setrlimit(resource.RLIMIT_FSIZE, (chosen, chosen))
    actual = resource.getrlimit(resource.RLIMIT_FSIZE)
    require(actual == (chosen, chosen) and chosen <= FILE_BYTES, "cost file-size cap was not applied")
    return {"inherited": list(inherited), "applied": list(actual)}


def layout_data(linked, modules, baseline, core, *, tt_bits):
    """Read bounded ELF/NOBITS DATA; never map or execute the declared extent."""
    _self(_normalized(__file__))
    core.validate_inputs(baseline)
    core.validate_modules(modules, baseline)
    require(type(tt_bits) is int and tt_bits in (23, 33) and type(linked) is bytes and
            64 <= len(linked) <= core.MAX_ELF_BYTES, "bounded named BSS ELF data required")
    geometry = modules["packer"].elf(linked)
    count, size, offset, names_index = (geometry[k] for k in ("section_count", "section_size", "section_offset", "section_names"))
    require(size == 64 and 1 <= count <= 128 and 0 < names_index < count and
            64 <= offset and offset+count*size <= len(linked), "bounded linked section table required")
    rows = [struct.unpack_from("<IIQQQQIIQQ", linked, offset+i*size) for i in range(count)]
    names = rows[names_index]
    require(names[1] == 3 and names[4]+names[5] <= len(linked), "bounded section-name string table required")
    strings = linked[names[4]:names[4]+names[5]]
    sections = []
    for row in rows:
        require(row[0] < len(strings), "section-name offset differs")
        end = strings.find(b"\0", row[0])
        require(end >= 0, "unterminated section name")
        name = strings[row[0]:end].decode("ascii")
        if row[1] != 8:
            require(row[4]+row[5] <= len(linked), "file-backed section exceeds actual file")
        sections.append({"name": name, "type": row[1], "flags": row[2], "address": row[3],
                         "offset": row[4], "size": row[5], "alignment": row[8]})
    matches = [row for row in sections if row["name"] == ".kernel_tt"]
    require(len(matches) == 1, "one explicit kernel TT output section required")
    table = matches[0]
    expected_bytes = (1 << tt_bits)*16
    require(table["type"] == 8 and table["flags"] == 3 and table["size"] == expected_bytes and
            table["address"] < 0x80000000 and table["address"] % 4096 == 0 and table["alignment"] >= 4096,
            "kernel TT NOBITS/profile/alignment/base differs")
    other = [row for row in sections if row["flags"] & 2 and row is not table and row["name"] != ".kernel_tt"]
    require(all(row["address"]+row["size"] <= table["address"] for row in other), "allocated small section follows the TT")
    segments = geometry["segments"]
    require(len(segments) == 3 and [row["type"] for row in segments] == [1, 1, 0x6474E551] and
            [row["flags"] for row in segments] == [5, 6, 6], "fixed RX/RW/NX-stack program headers required")
    memory = segments[1]
    require(memory["vaddr"]+memory["filesz"] <= table["address"] and
            memory["vaddr"]+memory["memsz"] == table["address"]+expected_bytes and
            memory["offset"]+memory["filesz"] <= len(linked), "TT is not the final zero-file RW extent")
    return {"kind": "ELF-layout-data-only", "tt_bits": tt_bits, "logical_tt_bytes": expected_bytes,
            "linked": core.pin(linked), "kernel_tt": table, "other_allocated_sections": other,
            "program_headers": segments,
            "symbol_binding": "successful fixed linker ASSERT; no stripped symbol-table claim",
            "scope": "NOBITS/NOLOAD layout inspection only; no ELF loading, kernel-zero or runtime observation"}


def _save(out, report):
    (out / "cost.json").write_text(json.dumps(report, indent=2)+"\n")


def run_snapshot(out, snapshot, current_root, inputs):
    _self(inputs[SELF])
    core = _core(snapshot)
    baseline = validate_inputs(inputs, core)
    modules = core.load_modules(snapshot, baseline)
    helper = _bss(snapshot, inputs[BSS])
    files, source_proof = core.prepare_sources(modules, baseline)
    resource = modules["source"].production().resource_profile(core.PROFILE)
    flags = modules["build"].native_flags(resource, "s")
    report = {"format": FORMAT, "family": "D", "complete": False, "inputs": core.inventory(inputs),
              "baseline_resource": resource.to_record(16), "baseline_source_proof": source_proof,
              "commands": [], "cases": [], "work_wall_seconds": WORK_SECONDS, "cleanup_reserve_seconds": CLEANUP_SECONDS,
              "scope": "one control + one BSS P4 cost + one W256/TT33 compile/layout; no generated program execution or admission"}
    save = lambda: _save(out, report)
    save()
    host, body_error = None, None
    try:
        report["file_size_limit"] = _file_limit()
        save()
        host = core.open_generation_host(out, report, save, modules, baseline, wall_seconds=WORK_SECONDS)
        report["generation_owner_limits"] = dict(modules["host"].LIMITS)
        # The unchanged strict production gates run to completion before BSS.
        directory = out / "control"
        directory.mkdir()
        control = core.generate_fixed_p4(files, flags, directory, modules, baseline, host)
        report["cases"].append({"name": "control-fast-p4", "source": core.inventory(files), **control["record"]})
        save()
        canonical, repeated_proof = core.prepare_sources(modules, baseline)
        require(canonical == files and repeated_proof == source_proof, "fresh canonical control replay differs")
        projected, proof = _apply_bss(helper, canonical, modules["source"], 23)
        directory = out / "bss-p4"
        directory.mkdir()
        generated = core.emit_native_generation(projected, flags, directory, modules, baseline, host)
        packed = core.package_native_generation(generated, modules, baseline)
        layout = layout_data(generated["images"][0][0], modules, baseline, core, tt_bits=23)
        report["cases"].append({"name": "bss-p4", "source": core.inventory(projected), "source_proof": proof,
                               "generation": generated["record"], "package": packed["row"], "layout": layout})
        save()
        # This is one explicit compile-only profile, not a production resource.
        canonical, repeated_proof = core.prepare_sources(modules, baseline)
        require(canonical == files and repeated_proof == source_proof, "fresh TT33 canonical replay differs")
        projected, proof = _apply_bss(helper, canonical, modules["source"], 33)
        flags33 = ["-DWORKERS=256" if flag == "-DWORKERS=4" else "-DTT_BITS=33" if flag == "-DTT_BITS=23" else flag for flag in flags]
        require(flags.count("-DWORKERS=4") == flags.count("-DTT_BITS=23") == 1 and
                flags33.count("-DWORKERS=256") == flags33.count("-DTT_BITS=33") == 1,
                "exact W256/TT33 compile-only flags required")
        directory = out / "bss-w256-tt33-layout"
        directory.mkdir()
        generated = core.emit_native_generation(projected, flags33, directory, modules, baseline, host)
        layout = layout_data(generated["images"][0][0], modules, baseline, core, tt_bits=33)
        require(layout["logical_tt_bytes"] == 137438953472, "TT33 exact logical size differs")
        report["cases"].append({"name": "bss-w256-tt33-layout-only", "source": core.inventory(projected),
                               "source_proof": proof, "generation": generated["record"], "layout": layout})
        require([row["name"] for row in report["cases"]] ==
                ["control-fast-p4", "bss-p4", "bss-w256-tt33-layout-only"], "exact finite cost cohort required")
        require(all(row["command"][0] == "cc" for row in report["commands"]), "cost cohort invoked a generated program")
        require({n: core.normalized(Path(current_root)/n) for n in inputs} == inputs and
                {n: core.normalized(Path(snapshot)/n) for n in inputs} == inputs, "cost source closure changed")
        _authenticate(helper, inputs[BSS], ("SCHEMA", "INPUT", "TT_SYMBOL", "TT_INPUT_SECTION", "TT_OUTPUT_SECTION"))
        core.validate_modules(modules, baseline)
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        modules["terminal"].finish_report(host, report, save, body_error)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--tt33-layout", action="store_true", help="explicitly include the one W256/TT33 compiler-only layout case")
    args = parser.parse_args(argv)
    require(args.execute, "cost generation is inactive without --execute")
    require(args.tt33_layout, "this exact cost cohort requires explicit --tt33-layout")
    _self(_normalized(__file__))
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 cost controller required")
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p / ".git").exists() for p in (out, *out.parents)),
            "new absolute cost output outside every checkout required")
    inputs = capture_inputs()
    out.mkdir(parents=True)
    snapshot = out / "inputs"
    for name, data in inputs.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    require(capture_inputs() == inputs, "cost source changed during snapshot")
    executing = _load("D_frozen_structural_bss_cost", snapshot/SELF, inputs[SELF])
    result = executing.run_snapshot(out, snapshot, ROOT, inputs)
    print(json.dumps({"format": result["format"], "complete": result["complete"],
        "cases": [row["name"] for row in result["cases"]], "scope": result["scope"]}), flush=True)


if __name__ == "__main__":
    main()
