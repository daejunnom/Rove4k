#!/usr/bin/env python3
"""Build the complete C A 2x2, pinning every canonical input before mutation."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from generate import INPUTS, digest, generate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "engines" / "scripts"))
from minify import compact_source
from specialize import specialize_c
from pack import write_launchers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT / "engines" / "c")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--tt-bits", type=int, default=16)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--no-pack", action="store_true")
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or args.out == ROOT or ROOT in args.out.parents:
        parser.error("--out must be new, absolute, and outside the checkout")
    if not 1 <= args.workers <= 512 or not 8 <= args.tt_bits <= 28:
        parser.error("workers must be 1..512 and TT bits 8..28")
    inputs = {name: (args.source_root / name).read_bytes() for name in INPUTS}
    # Capture all input bytes once. Each cell uses these exact same immutable
    # bytes even if an owner subsequently edits the shared checkout.
    args.out.mkdir(parents=True)
    pinned = args.out / "canonical-input"
    pinned.mkdir()
    for name, data in inputs.items():
        (pinned / name).write_bytes(data)
    records = []
    flags = ["-std=c11", "-Os", "-pthread", "-DROVE_VARIANT=1", "-DROVE_PARALLEL=0",
             f"-DROVE_WORKERS={args.workers}", f"-DROVE_TT_BITS={args.tt_bits}"]
    if args.sanitize:
        flags += ["-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    source_names = ("board.c", "search.c", "main.c")
    for layout in ("0x88", "10x12"):
        for update in ("copy", "unmake"):
            cell = args.out / (layout + "-" + update)
            cell.mkdir()
            files = generate(inputs, layout, update)
            recipe = [args.cc, *flags, "-DROVE_DEV=0", *source_names, "-o", "x"]
            specialized, observations = specialize_c(files, cell / "preprocess", recipe, os.environ.copy())
            compact = {name: compact_source(data, "c") for name, data in specialized.items()}
            for form, selected, dev in (("dev", files, 1), ("shipping", files, 0), ("compact", compact, 0)):
                directory = cell / form
                directory.mkdir()
                for name, data in selected.items():
                    (directory / name).write_bytes(data)
                command = [args.cc, *flags, f"-DROVE_DEV={dev}", *source_names, "-o", "x"]
                subprocess.run(command, cwd=directory, check=True, timeout=180)
                binary = directory / "x"
                subprocess.run(command[:-1] + ["x.second"], cwd=directory, check=True, timeout=180)
                if binary.read_bytes() != (directory / "x.second").read_bytes():
                    raise RuntimeError("native reproduction differs: " + str(directory))
                entry = {"id": f"A-{layout}-{update}-{form}", "layout": layout, "update": update,
                         "profile": "dev" if dev else "shipping", "form": form,
                         "command": [str(binary)], "cwd": str(directory),
                         "workers": args.workers, "startup_threads": args.workers + 1,
                         "native_bytes": binary.stat().st_size, "native_sha256": digest(binary.read_bytes()),
                         "source_bytes": sum(map(len, selected.values())),
                         "generated_sha256": {name: digest(data) for name, data in selected.items()},
                         "compile": command, "native_reproduced": True}
                if not dev and not args.no_pack and not args.sanitize:
                    launchers = write_launchers(selected, directory / "packed", command=recipe)
                    again = write_launchers(selected, directory / "repeated", command=recipe)
                    for first, second in zip(launchers, again):
                        if Path(first["path"]).read_bytes() != Path(second["path"]).read_bytes():
                            raise RuntimeError("complete launcher reproduction differs")
                        first["reproduced"] = True
                    entry["launchers"] = launchers
                records.append(entry)
                print(json.dumps({key: entry[key] for key in ("id", "native_bytes", "source_bytes")}), flush=True)
    report = {"candidate": "canonical A mailbox/update 2x2", "eligible_4k": False,
              "timing_fairness": "no throughput claim; host shared with other verification",
              "input_sha256": {name: digest(data) for name, data in inputs.items()},
              "generator_sha256": digest((HERE / "generate.py").read_bytes()),
              "compiler": subprocess.check_output([args.cc, "--version"], text=True).splitlines()[0],
              "workers": args.workers, "tt_bits": args.tt_bits,
              "engines": records}
    (args.out / "build.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
