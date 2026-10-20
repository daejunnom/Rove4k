#!/usr/bin/env python3
"""Bind the blocked per-thread signal runtime to frozen scalar/HQ TinyD costs.

Compare complete files under matching GCC/ABI/resource flags. A smaller Board
or worker is reported independently from complete ELF size. This study does
not infer NPS, strength, or a final adoption from representation alone.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
LAYOUT = '''#include "tiny.h"
#include <stdio.h>
int main(void){printf("{\\"Board\\":%zu,\\"Worker\\":%zu,\\"Entry\\":%zu,\\"atomic_flag\\":%zu,\\"atomic_int\\":%zu}\\n",sizeof(Board),sizeof(Worker),sizeof(Entry),sizeof(atomic_flag),sizeof(atomic_int));}
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flags(record):
    return sorted(arg for arg in record["compile"] if arg.startswith("-") and arg != "-o" and not arg.startswith("-Wl,-T,"))


def layout(directory, build, out):
    frozen = directory / "sources"
    source = out / "layout.c"
    source.write_text(LAYOUT)
    command = [build["engines"][0]["compile"][0], "-std=c11", "-DDEV=0", "-DWORKERS=2", "-DTT_BITS=18",
               "-I", str(frozen), str(source), "-o", str(out / "layout")]
    subprocess.run(command, check=True, timeout=30)
    observed = json.loads(subprocess.check_output([str(out / "layout")], text=True, timeout=5))
    return {"sizes": observed, "compile": command, "source_sha256": sha(source)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--control", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.is_absolute():
        args.out = args.out.resolve()
    if not args.out.is_absolute() or args.out.exists() or HERE.parents[2] in args.out.parents:
        parser.error("--out must be a new absolute external directory")
    args.out.mkdir(parents=True)
    builds = [json.loads(path.read_text()) for path in (args.control, args.build)]
    if builds[0]["compiler"] != builds[1]["compiler"]:
        raise ValueError("control compiler identity differs")
    report = {"control_manifest_sha256": sha(args.control), "experiment_manifest_sha256": sha(args.build),
              "compiler": builds[0]["compiler"], "frozen_inputs": [], "forms": [],
              "isolated_language_or_nps_comparison": False, "adopted_for_size": False}
    layouts = []
    for label, path, build in zip(("control", "experiment"), (args.control, args.build), builds):
        frozen = args.out / label
        frozen.mkdir()
        shutil.copy2(path, frozen / "build.json")
        shutil.copytree(path.parent / "sources", frozen / "sources")
        for name, expected in build["source_sha256"].items():
            if sha(frozen / "sources" / name) != expected:
                raise RuntimeError("frozen source hash differs")
        layouts.append(layout(frozen, build, frozen))
        report["frozen_inputs"].append({"label": label, "source_sha256": build["source_sha256"], "layout": layouts[-1]})
        for record in build["engines"]:
            program = Path(record["command"][0])
            if sha(program) != record["native_sha256"]:
                raise RuntimeError("native hash differs")
            shutil.copy2(program, frozen / (record["id"]+".elf"))
            for launcher in record["launchers"]:
                program = Path(launcher["path"])
                if sha(program) != launcher["sha256"]:
                    raise RuntimeError("whole ELF hash differs")
                shutil.copy2(program, frozen / (record["id"]+"-self.elf"))
    for mode in ("scalar", "hq"):
        records = [next(record for record in build["engines"] if record["id"].endswith(mode+"-shipping")) for build in builds]
        if flags(records[0]) != flags(records[1]):
            raise ValueError("code generation/resource flags differ")
        values = []
        for record in records:
            value = {"id": record["id"], "native_bytes": record["native_bytes"], "native_sha256": record["native_sha256"],
                     "self_elf_bytes": min((p["bytes"] for p in record["launchers"]), default=None)}
            if record.get("source_launchers"):
                value["general_source_package_bytes"] = min(p["bytes"] for p in record["source_launchers"])
            values.append(value)
        report["forms"].append({"backend": mode, "matching_flags": flags(records[0]), "control": values[0], "experiment": values[1],
                                "native_delta_bytes": values[1]["native_bytes"]-values[0]["native_bytes"],
                                "self_elf_delta_bytes": values[1]["self_elf_bytes"]-values[0]["self_elf_bytes"]})
    report["layout_delta_bytes"] = {key: layouts[1]["sizes"][key]-layouts[0]["sizes"][key] for key in layouts[0]["sizes"]}
    report["qualification"] = "Only runtime notification architecture differs from the frozen board/search/HQ/ABI controls. Full tests establish correctness separately; no NPS or hardware-scaling claim follows from complete-file size."
    (args.out / "results.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"native_deltas": [r["native_delta_bytes"] for r in report["forms"]], "layout_delta_bytes": report["layout_delta_bytes"]}))


if __name__ == "__main__":
    main()
