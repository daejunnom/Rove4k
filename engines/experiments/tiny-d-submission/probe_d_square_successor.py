#!/usr/bin/env python3
"""Finite full-P4 D square-successor cost comparison; never run an engine.

Only a pinned, already qualified no-TID six-source carrier is an input. Saved
JSON supplies checked provenance, never a restored admission capability. Both
cases replay the same CPP, literal legacy map and original reducer, then build
two complete linked images and regenerate all three maintained whole routes.
The new source stage is not a production policy or a runtime admission.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import stat
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
SELF = D + "probe_d_square_successor.py"
NEW = (D + "d_square_successor.py", SELF, D + "test_d_square_successor.py")
QUALIFICATION = Path("/home/stemxstudio/rove4k-D-no-tid-P4-20261026-v1")
QUALIFICATION_PIN = (1537522, "e9510a0a408321bfc6400e49df95d3cbbd9ef9a5cdc0b37ffaf44b46958d4b6f")
STARTUP_PIN = (252355, "0a09371a9a5eb0aac8644d18b24b2172742796f0789432d6d4771c86b2662241")
TOOLS = {
    "host": ("engines/experiments/tcec-scope/build.py", 34364, "5fa10c6f8f032be374bf3a86bbe6ca558076630a2cc3170b41890f691688f563"),
    "package": (D + "packaging.py", 3184, "928b7f2ea76787994a4d47f516395583af5cba0bfe840d54fc5321056558faa6"),
    "bootstrap": (D + "compressed_bootstrap.py", 8029, "d9d167990a58e8d3505dea54251a0a5e2754344c1f21e955d7cc505d63a60839"),
    "packer": ("engines/compact/tiny-entry-d/packer.py", 9528, "af95c8fd8a38f999bb846f024e13689d417e28c0ce0ec830f8a200b4cef3fd7e"),
    "builder": (D + "build.py", 16475, "1e51803539f0038e7e729431b9f73bbc325f735d512cde24a70c9a66e9754a41"),
    "reducer": (D + "reduce.py", 5294, "9394a7e11e8d23be6189ee8d3e1b17d1a7f1e86c127147394dbf04ca25d59f17"),
    "minifier": ("engines/scripts/minify.py", 6624, "eb5eeca57b8f0f7225e639c8ee9e13fd1d5a5f159e58c38d66e0dea3b0433c3b"),
    "lexical": ("engines/scripts/rename_c.py", 12574, "9d7d09e2787cfda21701384be94ed00d588165574da5d8aacdf731fcb317cbe5"),
}
FLAGS = ["-Os", "-std=c11", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic",
    "-fno-stack-protector", "-fno-builtin", "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables", "-fno-ident", "-fcf-protection=none", "-ffunction-sections",
    "-fdata-sections", "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack", "-flto",
    "-msse4.2", "-mcx16", "-DDEV=0", "-DD_HQ=0", "-DWORKERS=4", "-DTT_BITS=23"]
UNITS = ["main.c", "start.S"]
DRIVER = b'#include "board.c"\n#include "search.c"\n#include "runtime.c"\n'
LEGACY = {"Board":"y", "Move":"H", "Worker":"Z", "alpha":"V", "atomic_flag":"W",
    "atomic_int":"U", "attacked":"X", "best":"M", "bestmove":"ad", "budget":"aa",
    "created":"Y", "cursor":"A", "depth":"C", "evaluation":"O", "from":"B",
    "game_length":"N", "memory_order":"R", "memory_order_acquire":"L",
    "memory_order_relaxed":"l", "memory_order_release":"G", "moves":"J", "pending":"P",
    "position":"Q", "promotion":"K", "score":"E", "size_t":"F", "stopped":"T",
    "system_call":"I", "target":"ab", "token":"o", "uint64_t":"g", "workers":"ac"}
SHIPPING = {"main.c":(16960,"c7a18c4b9536263a90dc2a69678276202ba19ccfa03fc3b837d30aad671df65e"),
    "start.S":(559,"4205000a4c0993ad014ee7e25122e2d27e1e4e14b619da34365db1d1cc9aedde"),
    "image.ld":(446,"38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b")}
IDENTITY = {"linked":(7456,"16deff54c4059f236c845191674f9b36c26139c032d23e66b53992fd11c3ebf3"),
    "native":(7104,"f0168f752eaa15bf011cbd75964ebe10bc39ca88ddd16eeed66c73e2cf59ed7b")}
WHOLE = {"source-jit":(7114,"f1e3e1209a696b9eb88ca99c8be24d9ff18bf925d0ef4aab3eb4f03d69cd9714"),
    "source-jit-compressed":(6972,"fd66ce2266288121d5a85a69d32daa5d488fb7abc5523b8bf8eac0c456c662e8"),
    "packed-xz-bcj":(5245,"4dbe1bfbceb1c290ee45801e74fe44d7ef2148215b57d51141e1965d5e5db9fa")}
COMPILER = Path("/usr/bin/x86_64-linux-gnu-gcc-13")
COMPILER_PIN = (1023032,"1b99826121ae6682a634e5efe09bd3e3df58ce58e0b28f849114ab5b89139c26")
BANNER = "cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
_EXECUTING_CODE = sys._getframe().f_code


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "immutable byte evidence required")
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def expected(pair):
    return dict(bytes=pair[0], sha256=pair[1])


def inventory(files):
    return {name:pin(data) for name,data in sorted(files.items())}


def normalized(path):
    data = read(path).replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in explicit source input")
    return data


def read(path, maximum=2 << 20):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and
        stat.S_ISREG(path.lstat().st_mode) and path.stat().st_size <= maximum,
        "explicit bounded regular source/evidence file required")
    return path.read_bytes()


def write(root, name, data):
    require(type(name) is str and name and not name.startswith("/") and
        all(p not in ("", ".", "..") for p in name.split("/")) and "\\" not in name,
        "new relative output role required")
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
    return path


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def strict_decode(data):
    decoder = lzma.LZMADecompressor()
    decoded = decoder.decompress(data)
    require(decoder.eof and decoder.unused_data == b"", "whole payload EOF/trailing bytes differ")
    return decoded


def inverse(whole, detail, route, files, flags, native, package):
    count = detail["header_bytes"]
    header, payload = whole[:count], whole[count:]
    decoded = strict_decode(payload)
    wanted = dict(files={n:d.decode() for n,d in sorted(files.items())}, flags=flags, units=UNITS)
    if route == "packed-xz-bcj":
        require(decoded == native, "complete native inverse differs")
        code = package.NATIVE_CODE
    elif route == "source-jit":
        require(json.loads(decoded) == wanted, "complete source bundle inverse differs")
        code = package.SOURCE_CODE
    else:
        tree = ast.parse(decoded)
        require(len(tree.body) == 4 and isinstance(tree.body[1], ast.Assign) and
            len(tree.body[1].targets) == 1 and isinstance(tree.body[1].targets[0], ast.Name) and
            tree.body[1].targets[0].id == "b" and ast.literal_eval(tree.body[1].value) == wanted,
            "compressed compiler literal inverse differs")
        code = 'import lzma,sys\nexec(lzma.decompress(open(sys.argv[1],"rb").read()[PAYLOAD_OFFSET:]))'
    again, wanted_header = package.envelope(code, payload)
    require(again == whole and wanted_header == header and count + len(payload) == len(whole),
        "actual header/offset/payload/whole boundary differs")
    return dict(header=pin(header), payload=pin(payload), decoded=pin(decoded),
        strict_EOF=True, trailing_bytes=0, complete_input_inverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, default=QUALIFICATION)
    args = parser.parse_args()
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 tools required")
    require(args.qualification == QUALIFICATION and QUALIFICATION.resolve() == QUALIFICATION,
        "one literal qualified no-TID input root required")
    out = args.out
    require(out.is_absolute() and out.resolve() == out and not out.exists() and out.parent.is_dir() and
        not any((p / ".git").exists() for p in (out, *out.parents)) and
        QUALIFICATION not in out.parents and out not in QUALIFICATION.parents,
        "new output outside every checkout and archived input required")
    raw_qualification = read(QUALIFICATION / "qualification.json")
    raw_startup = read(QUALIFICATION / "startup-results.json")
    require(pin(raw_qualification) == expected(QUALIFICATION_PIN) and
        pin(raw_startup) == expected(STARTUP_PIN), "literal original evidence pins differ")
    qualified, startup = json.loads(raw_qualification), json.loads(raw_startup)
    provenance = qualified["admission"]
    require(qualified.get("complete") is True and qualified.get("selector") == "no-tid" and
        provenance["flags"] == FLAGS and provenance["units"] == UNITS and
        provenance["identifier_composition"]["legacy"] == LEGACY,
        "qualified original source/flags/units/legacy provenance differs")
    old_cases = [c for c in startup["cases"] if c["name"] == "no-tid"]
    require(len(old_cases) == 1, "one archived no-TID case required")
    original = {n:read(QUALIFICATION / "carrier/generated-readable" / n)
        for n in ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")}
    old_shipping = {n:read(QUALIFICATION / "carrier/shipping-inputs" / n) for n in SHIPPING}
    old_images = {"linked":read(QUALIFICATION / "carrier/native/linked"),
        "native":read(QUALIFICATION / "carrier/native/image")}
    old_packed = read(QUALIFICATION / "carrier/program")
    require(inventory(old_shipping) == {n:expected(p) for n,p in SHIPPING.items()} and
        inventory(old_images) == {n:expected(p) for n,p in IDENTITY.items()} and
        pin(old_packed) == expected(WHOLE["packed-xz-bcj"]), "actual archived carrier bytes differ")
    frozen, origins = {}, {}
    for _, (name, size, digest) in TOOLS.items():
        archived = read(QUALIFICATION / "frozen" / name)
        current = normalized(REPO / name)
        require(archived == current and pin(archived) == expected((size,digest)) and
            qualified["inputs"][name] == pin(archived), "pinned qualified/current tool differs: " + name)
        frozen[name] = archived
        origins[name] = dict(qualified_path=str(QUALIFICATION / "frozen" / name),
            current_path=str(REPO / name), normalized_current_equal=True)
    for name in NEW:
        frozen[name] = normalized(REPO / name)
        origins[name] = dict(current_path=str(REPO / name), new_cost_only_source=True)
    require(compile(frozen[SELF], __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
        "captured driver differs from actually executing module")
    require(Path(shutil.which("cc") or "").resolve() == COMPILER and
        pin(read(COMPILER)) == expected(COMPILER_PIN), "actual cc binary identity differs")
    out.mkdir()
    for name, data in frozen.items():
        write(out / "frozen", name, data)
    write(out, "inputs/qualification.json", raw_qualification)
    write(out, "inputs/startup-results.json", raw_startup)
    for name,data in original.items():write(out, "inputs/generated-readable/" + name, data)
    for name,data in old_shipping.items():write(out, "inputs/shipping-inputs/" + name, data)
    for name,data in old_images.items():write(out, "inputs/original-" + name, data)
    write(out, "inputs/original-packed-xz-bcj", old_packed)
    modules = {role:load("D_successor_frozen_" + role, out / "frozen" / value[0])
        for role,value in TOOLS.items()}
    change = load("D_successor_frozen_change", out / "frozen" / NEW[0])
    require(inventory(original) == change.INPUTS, "exact current no-TID six-source input required")
    candidate, proof = change.transform(original)
    require(change.restore(candidate, json.loads(json.dumps(proof))) == original,
        "two-opening whole-source inverse differs")
    report = dict(kind="rove4k.D-no-TID-square-successor-cost.v1", complete=False,
        scope="two exact scalar outer openings; finite control/candidate whole cost only",
        commands=[], cases=[], original_qualification=pin(raw_qualification),
        original_startup_cost=pin(raw_startup), original_root=str(QUALIFICATION),
        input_sources=inventory(original), captured_sources=inventory(frozen), source_origins=origins,
        compiler=dict(path=str(COMPILER), **expected(COMPILER_PIN)), compiler_flags=FLAGS, units=UNITS,
        resource=dict(profile="test-p4", workers=4, tt_bits=23, tt_entry_bytes=16, tt_bytes=128 << 20),
        native_input_model="complete preprocessed/minified C plus exact CPP assembly and linker file",
        stripped_model="canonical strip_native retains PT_LOAD bytes and clears section metadata",
        payload_model="three unchanged maintained envelopes; full bootstrap+payload count",
        source_stage=proof, frozen_execution=True, engine_executed=False, target_TT_allocated=False,
        capability_deserialized=False, full_typed_admission=False, runtime_qualified=False,
        rules_qualified=False, size_qualified=False, strength_qualified=False,
        physical_placement_qualified=False, event_target_confirmed=False, selected=False,
        production_adopted=False, old_maps_changed=False, no_proper_alpha_combination=True)
    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    owner = modules["host"]
    inherited = resource.getrlimit(resource.RLIMIT_CPU)
    require(all(v == resource.RLIM_INFINITY or v >= 240 for v in inherited),
        "fresh parent CPU limit must permit the bounded cost owner")
    owner.LIMITS = {**owner.LIMITS, "aggregate_wall":300, "per_command_wall":45,
        "parent_CPU":180, "parent_CPU_hard":210, "child_CPU":30, "tool_output_bytes":4 << 20}
    host = None
    try:
        host = owner.Host(out, report, save)
        def run(command, path, kind, *, data=None, diagnostics=False):
            output = host.run(command, cwd=path, kind=kind, data=data)
            row = report["commands"][-1]
            errors = Path(row["stderr"]["path"]).read_bytes()
            require(diagnostics or not errors, "accepted source/compiler diagnostics: " + kind)
            return output, row
        version, _ = run(["cc", "--version"], out, "compiler-version")
        require(version.decode().splitlines()[0] == BANNER, "actual compiler version differs")
        report["compiler"]["banner"] = BANNER
        for label, readable, stage in (("control", original, None), ("successor", candidate, proof)):
            base = out / label
            base.mkdir()
            raw = base / "generated-readable"
            raw.mkdir()
            for name,data in readable.items():write(raw, name, data)
            row = dict(name=label, readable=inventory(readable), source_stage=stage, native=[], packages=[])
            report["cases"].append(row)
            cpp, cpp_command = run(["cc", "-E", "-P", *FLAGS, "-I", str(raw), "-x", "c", "-"],
                raw, label + "-single-preprocess", data=DRIVER)
            entry, entry_command = run(["cc", "-E", "-P", "-x", "assembler-with-cpp", str(raw / "start.S")],
                raw, label + "-entry-preprocess")
            emitted = {"main.c":modules["minifier"].compact_source(cpp, "c"),
                "start.S":entry, "image.ld":readable["image.ld"]}
            cpp_stdin = Path(cpp_command["stdout"]["path"]).with_suffix(".stdin")
            require(read(cpp_stdin) == DRIVER, "actual CPP driver stdin differs")
            row["preprocess"] = dict(driver=dict(path=str(cpp_stdin), **pin(DRIVER)), C=pin(cpp), assembly=pin(entry),
                commands=[cpp_command, entry_command], minified=inventory(emitted))
            require(not set(LEGACY.values()).intersection(modules["lexical"]._ANY_WORD.findall(emitted["main.c"].decode())),
                "legacy rename would capture an existing identifier")
            mapped = {"main.c":emitted["main.c"]}
            for before,after in LEGACY.items():mapped = modules["lexical"]._replace(mapped, before, after)
            restored = dict(mapped)
            for before,after in reversed(tuple(LEGACY.items())):
                restored = modules["lexical"]._replace(restored, after, before)
            require(restored == {"main.c":emitted["main.c"]}, "complete legacy token inverse differs")
            emitted.update(mapped)
            row["legacy"] = dict(mapping=LEGACY, full_inverse=True, emitted=inventory(emitted))
            gate_names = []
            def compile_files(files, directory, kind, *, allow_diagnostics=False):
                directory.mkdir()
                for name,data in files.items():write(directory, name, data)
                _, command = run(["cc", *FLAGS, *[str(directory / n) for n in UNITS],
                    "-Wl,-T," + str(directory / "image.ld"), "-o", str(directory / "linked")],
                    directory, kind, diagnostics=allow_diagnostics)
                require({n:read(directory / n) for n in files} == files, "actual native input changed during compilation")
                linked = read(directory / "linked")
                native = modules["packer"].strip_native(linked)
                write(directory, "native", native)
                record = dict(input=inventory(files), input_paths={n:str(directory/n) for n in files},
                    linked_path=str(directory / "linked"), native_path=str(directory / "native"),
                    linked=pin(linked), native=pin(native), command=command,
                    linked_geometry=modules["builder"].kernel_geometry(modules["packer"], linked, 4),
                    native_geometry=modules["builder"].kernel_geometry(modules["packer"], native, 4))
                return linked, native, record
            def digest(c_files, trial):
                require(trial in ("baseline", "typedefs", "batch-alpha") and trial not in gate_names,
                    "original reducer exceeded its finite three gates")
                gate_names.append(trial)
                linked, _, gate = compile_files({**emitted, **c_files}, base / ("gate-" + trial),
                    label + "-source-reduction-gate-" + trial, allow_diagnostics=trial == "batch-alpha")
                row.setdefault("reducer_native", []).append(gate)
                return pin(linked)["sha256"]
            reduced, reduction = modules["reducer"].reduce_sources({"main.c":emitted["main.c"]}, digest,
                modules["lexical"], reserve=modules["lexical"]._ANY_WORD.findall((entry + emitted["image.ld"]).decode()))
            require(gate_names == ["baseline", "typedefs", "batch-alpha"], "original three reducer gates not reproduced")
            for gate in row["reducer_native"]:
                if gate["command"]["stderr"]["bytes"]:
                    require(gate["command"]["kind"].endswith("batch-alpha") and
                        reduction["stages"][-1]["status"] == "rejected-native-differs",
                        "diagnostic source must not enter accepted shipping")
                    errors = Path(gate["command"]["stderr"]["path"]).read_bytes()
                    warnings = [s for s in errors.splitlines() if b"warning:" in s]
                    require(warnings and b"error:" not in errors and all(re.search(
                        rb": warning: '[A-Za-z][A-Za-z_0-9]*' attribute directive ignored \[-Wattributes\]$", s)
                        for s in warnings), "unexpected diagnostics in rejected legacy batch")
            emitted.update(reduced)
            row["reduction"] = reduction
            row["shipping"] = inventory(emitted)
            ship = base / "shipping-inputs"
            ship.mkdir()
            for name,data in emitted.items():write(ship, name, data)
            if label == "control":
                require(emitted == old_shipping and reduction == old_cases[0]["reduction"],
                    "original production-path control shipping/reducer differs")
            images = []
            for index in range(2):
                linked, native, record = compile_files(emitted, base / ("native-" + str(index)),
                    label + "-native-repeat-" + str(index))
                require(pin(linked)["sha256"] == reduction["final_native_sha256"],
                    "final native differs from original reducer identity gate")
                row["native"].append(record)
                images.append((linked,native))
            require(images[0] == images[1], "complete linked/native first-repeat differs")
            if label == "control":require(dict(zip(("linked","native"), images[0])) == old_images,
                "actual complete original control linked/native not reproduced")
            for route in WHOLE:
                packages = []
                for index in range(2):
                    if route == "packed-xz-bcj":whole, detail = modules["package"].package_native(images[0][1], "xz-bcj")
                    elif route == "source-jit":whole, detail = modules["package"].package_source(emitted, FLAGS, UNITS)
                    else:whole, detail = modules["bootstrap"].package_source(emitted, FLAGS, UNITS, modules["package"])
                    boundary = inverse(whole, detail, route, emitted, FLAGS, images[0][1], modules["package"])
                    path = write(base, route + "-" + str(index), whole)
                    packages.append((whole,detail,boundary))
                    row["packages"].append(dict(route=route, repeat=index, path=str(path), whole=pin(whole),
                        detail=detail, inverse=boundary, bootstrap_plus_payload_bytes=len(whole)))
                require(packages[0] == packages[1], "whole/detail/inverse first-repeat differs")
                if label == "control":require(pin(packages[0][0]) == expected(WHOLE[route]),
                    "original whole control hash not reproduced: " + route)
            require({n:read(raw/n) for n in readable} == readable and
                {n:read(ship/n) for n in emitted} == emitted, "case source changed after cost generation")
            save()
        require(len(report["commands"]) == 15, "exact finite 15-command cost scope differs")
        report["whole_delta"] = {route:report["cases"][1]["packages"][2*i]["whole"]["bytes"]-WHOLE[route][0]
            for i,route in enumerate(WHOLE)}
        report["all_routes_loss_or_equal"] = all(v >= 0 for v in report["whole_delta"].values())
        report["current_sources_unchanged"] = {n:pin(normalized(REPO/n)) for n in frozen}
        require(report["current_sources_unchanged"] == inventory(frozen), "captured/current helper/tool closure changed")
        require(read(QUALIFICATION/"qualification.json") == raw_qualification and
            read(QUALIFICATION/"startup-results.json") == raw_startup and
            {n:read(QUALIFICATION/"carrier/generated-readable"/n) for n in original} == original,
            "original archived source/evidence changed")
        report["complete"] = True
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        report["complete"] = False
        raise
    finally:
        if host is not None:
            try:
                host.close()
            except BaseException as error:
                report["complete"] = False
                report["cleanup_failure"] = dict(type=type(error).__name__, message=str(error))
                raise
        else:
            report["host_cleanup"] = dict(unsettled_commands=0, errors=[], host_not_started=True)
        save()
    print(json.dumps(dict(complete=report["complete"], whole_delta=report["whole_delta"],
        commands=len(report["commands"]), engine_executed=False, selected=False)))


if __name__ == "__main__":
    main()
