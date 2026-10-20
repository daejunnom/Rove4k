#!/usr/bin/env python3
"""Matched moving-side-positive 0x88 source architecture experiment.

No source or helper outside this folder is changed. Inputs/helpers are frozen in
the new external output before processing; native and complete-file generation
are independently repeated. The prior qualified 5283-byte artifact is a separate
control, not an additive saving claimed for these matched readable modules.
"""
import argparse
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--tt-bits", type=int, default=18)
    parser.add_argument("--forms", default="baseline,oriented")
    parser.add_argument("--no-pack", action="store_true")
    parser.add_argument("--argv-form", choices=("list", "split"), default="split",
                        help="fixed compiler-argv representation; default is the selected encoding recipe's string split")
    parser.add_argument("--selected-control", type=Path)
    parser.add_argument("--selected-control-sha256")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT in args.out.parents:
        parser.error("new absolute external output required")
    if not 1 <= args.workers <= 512 or not 8 <= args.tt_bits <= 28:
        parser.error("invalid fixed resource profile")
    if not args.no_pack and (args.workers, args.tt_bits) != (2, 18):
        parser.error("the frozen encoding recipe is fixed to workers=2, TT bits=18; use --no-pack for other DEV profiles")
    names = args.forms.split(",")
    if not names or len(names) != len(set(names)) or set(names) - {"baseline", "oriented"}:
        parser.error("unknown or repeated architecture form")
    if bool(args.selected_control) != bool(args.selected_control_sha256):
        parser.error("selected control path and digest required together")
    args.out.mkdir(parents=True)
    frozen = args.out / "frozen"
    frozen.mkdir()
    helpers = {"stitch.py": ROOT / "engines/compact/tiny-a/stitch.py",
               "pack_stream.py": ROOT / "engines/compact/tiny-a/pack_stream.py",
               "minify.py": ROOT / "engines/scripts/minify.py",
               "specialize.py": ROOT / "engines/scripts/specialize.py",
               "rename_c.py": ROOT / "engines/scripts/rename_c.py",
               "encoding_campaign.py": ROOT / "engines/experiments/tiny-encoding/campaign.py",
               "build.py": Path(__file__)}
    for name, path in helpers.items():
        (frozen / name).write_bytes(path.read_bytes())
    stitch = module("sentinel_frozen_stitch", frozen / "stitch.py")
    minify = module("sentinel_frozen_minify", frozen / "minify.py")
    specialize = module("sentinel_frozen_specialize", frozen / "specialize.py")
    pack = module("sentinel_frozen_stream", frozen / "pack_stream.py")
    lexer = module("sentinel_frozen_lexer", frozen / "rename_c.py")
    encoding = module("sentinel_frozen_encoding", frozen / "encoding_campaign.py")
    canonical_bootstrap = pack.bootstrap
    inputs = {}
    for form in ("baseline", "oriented"):
        directory = frozen / form
        directory.mkdir()
        mapping = {"tiny.h": "tiny.h", "board.c": "board-generated.c.in" if form == "baseline" else "board.c",
                   "search.c": "search.c", "main.c": "main.c"}
        source_root = ROOT / "engines/compact/tiny-a" if form == "baseline" else HERE
        inputs[form] = {}
        for name, original in mapping.items():
            data = (source_root / original).read_bytes()
            (directory / name).write_bytes(data)
            inputs[form][name] = data
    control = None
    if args.selected_control:
        data = args.selected_control.read_bytes()
        if sha(data) != args.selected_control_sha256:
            raise ValueError("selected historical control changed")
        (frozen / "qualified-selected-control").write_bytes(data)
        control = {"path": str(args.selected_control), "bytes": len(data), "sha256": sha(data),
                   "scope": "separate previously qualified selected recipe; matched source architecture controls below"}
    records = []
    flags = ["-std=c11", "-Os", "-pthread", f"-DWORKERS={args.workers}", f"-DTT_BITS={args.tt_bits}"]
    for name in names:
        directory = args.out / name
        directory.mkdir()
        source_map = inputs[name]
        combined, layout = stitch.stitch(source_map, ("tiny.h", "board.c", "search.c", "main.c"), True)
        (directory / "assembled.c").write_bytes(combined)
        compile_flags = flags
        preprocess_command = ["cc", *compile_flags, "-DDEV=0", "main.c", "-o", "x"]
        specialized, observations = specialize.specialize_c({"main.c": combined}, directory / "preprocess",
                                                              preprocess_command, os.environ.copy())
        compact = minify.compact_source(specialized["main.c"], "c")
        compact, counters = stitch.strip_dev_counters(compact)
        native_records = []
        reference_shipping = None
        for source_form, data, dev in (("dev", combined, 1), ("original", combined, 0), ("compact", compact, 0)):
            target = directory / source_form
            target.mkdir()
            (target / "main.c").write_bytes(data)
            command = ["cc", *compile_flags, f"-DDEV={dev}", "main.c", "-o", "x"]
            subprocess.run(command, cwd=target, check=True, timeout=60)
            image = (target / "x").read_bytes()
            subprocess.run(command, cwd=target, check=True, timeout=60)
            if image != (target / "x").read_bytes():
                raise ValueError("independent complete native reproduction failed")
            if source_form == "original":
                reference_shipping = image
            if source_form == "compact" and image != reference_shipping:
                raise ValueError("shipping specialization/noop removal changed actual native bytes")
            native_records.append({"id": name + "-" + source_form, "profile": "dev" if dev else "shipping",
                                   "source_sha256": sha(data), "source_bytes": len(data), "command": [str(target / "x")],
                                   "cwd": str(target), "compile": command, "workers": args.workers,
                                   "startup_threads": args.workers + 1, "native_bytes": len(image),
                                   "expected_program_sha256": sha(image), "native_reproduced": True})
        entry = {"name": name, "absolute_canonical_FIDE_hash": True, "source_layout": layout,
                 "board_representation": "signed-absolute-0x88" if name == "baseline" else "signed-moving-side-relative-0x88",
                 "search_policy": "absolute-coordinate history/ties and signed-colour continuation" if name == "baseline" else "relative-coordinate history/ties and previous/current piece-kind continuation",
                 "inputs_sha256": {key: sha(value) for key, value in source_map.items()},
                 "preprocessor": observations, "counter_recipe": counters, "natives": native_records}
        if not args.no_pack:
            encoded, resources = encoding.profile_literals(compact, lexer)
            encoded, spellings = encoding.manual_functions(encoded, lexer, True)
            command = ["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"]
            target = directory / "encoded"
            target.mkdir()
            (target / "main.c").write_bytes(encoded)
            baseline_stdin = ["cc", *compile_flags, "-DDEV=0", "-x", "c", "-", "-o", "x", "-s"]
            subprocess.run(baseline_stdin, input=compact, cwd=target, check=True, timeout=60)
            reference = (target / "x").read_bytes()
            for _ in range(2):
                subprocess.run(command, input=encoded, cwd=target, check=True, timeout=60)
                if (target / "x").read_bytes() != reference:
                    raise ValueError("fixed resources/spellings/flags changed stripped native class")
            script, kind = canonical_bootstrap(encoded, command)
            if args.argv_form == "split":
                script = encoding.replace_argument(script, "subprocess", "Popen", repr(" ".join(command)) + ".split()")
            assert encoding.value(encoding.argument(script, "p", "communicate")) == encoded
            assert encoding.value(encoding.argument(script, "subprocess", "Popen")) == command
            (target / "bootstrap.py").write_bytes(script)
            pack.bootstrap = lambda _source, _command, selected=script: (selected, "fixed-argv-" + args.argv_form)
            artifacts = []
            for codec in ("xz", "gzip", "bzip2"):
                whole, metadata = pack.make_stream(encoded, command, codec)
                repeated, _ = pack.make_stream(encoded, command, codec)
                if whole != repeated:
                    raise ValueError("complete source launcher reproduction failed")
                path = target / codec / "x"
                path.parent.mkdir()
                path.write_bytes(whole)
                path.chmod(0o755)
                metadata.update(path=str(path), reproduced=True)
                artifacts.append(metadata)
            pack.bootstrap = canonical_bootstrap
            # Exactly the selected lossless lc2/pb0 recipe, with the same
            # decoded bootstrap and full shell prefix. No parameter search.
            baseline = (target / "xz/x").read_bytes()
            offset = baseline.index(b"\xfd7zXZ\0")
            decoded = lzma.decompress(baseline[offset:])
            payload = lzma.compress(decoded, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64,
                                    filters=[{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME,
                                              "lc": 2, "lp": 0, "pb": 0}])
            assert lzma.decompress(payload) == decoded
            path = target / "xz-selected/x"
            path.parent.mkdir()
            whole = baseline[:offset] + payload
            path.write_bytes(whole)
            path.chmod(0o755)
            repeated = baseline[:offset] + lzma.compress(decoded, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64,
                                    filters=[{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME,
                                              "lc": 2, "lp": 0, "pb": 0}])
            assert whole == repeated
            artifacts.append({"codec": "xz-lc2-lp0-pb0", "bytes": len(whole), "sha256": sha(whole),
                              "path": str(path), "launcher_bytes": offset, "payload_bytes": len(payload),
                              "decoded_sha256": sha(decoded), "reproduced": True})
            chosen = min(artifacts, key=lambda item: item["bytes"])
            entry["encoding"] = {"source_bytes": len(encoded), "source_sha256": sha(encoded), "resources": resources,
                                 "manual_function_spellings": spellings, "compiler": command,
                                 "compiler_argv_representation": args.argv_form, "bootstrap_sha256": sha(script),
                                 "stripped_native_sha256": sha(reference), "stripped_native_bytes": len(reference),
                                 "artifacts": artifacts, "selected": chosen}
        records.append(entry)
        print(json.dumps({"name": name, "shipping_source_bytes": len(compact),
                          "selected_complete_bytes": entry.get("encoding", {}).get("selected", {}).get("bytes")}), flush=True)
    engines = [native for record in records for native in record["natives"]]
    for record in records:
        if "encoding" in record:
            artifact = record["encoding"]["selected"]
            engines.append({"id": record["name"] + "-selected", "profile": "shipping", "command": [artifact["path"]],
                            "cwd": str(Path(artifact["path"]).parent), "workers": args.workers,
                            "startup_threads": args.workers + 1, "startup_timeout": 60,
                            "expected_program_sha256": artifact["sha256"]})
    report = {"scope": "independent oriented architecture experiment; no canonical promotion or 4K acceptance",
              "workers": args.workers, "tt_bits": args.tt_bits, "selected_historical_control": control,
              "helpers_sha256": {name: sha((frozen / name).read_bytes()) for name in helpers},
              "compiler": subprocess.check_output(["cc", "--version"], text=True).splitlines()[0],
              "records": records, "engines": engines}
    (args.out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.out / "validation-manifest.json").write_text(json.dumps({"engines": engines}, indent=2) + "\n")


if __name__ == "__main__":
    main()
