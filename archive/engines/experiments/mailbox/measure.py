#!/usr/bin/env python3
"""Measure and execute whole source/native packages for every 2x2 cell.

The decoder, executable header, metadata and payload all count. This measures
the canonical A recipe and does not claim a 4096-byte submission or fair speed.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from generate import digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "engines" / "scripts"))
from pack import write_launchers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--strip", default="strip")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT == args.out or ROOT in args.out.parents:
        parser.error("--out must be new, absolute, outside the checkout")
    args.out.mkdir(parents=True)
    owner_path = args.out / "compiler_group.py"
    owner_path.write_bytes((ROOT / "engines/scripts/compiler_group.py").read_bytes())
    owner_spec = importlib.util.spec_from_file_location("mailbox_measure_compiler_group", owner_path)
    owner = importlib.util.module_from_spec(owner_spec)
    owner_spec.loader.exec_module(owner)
    compiler_group = owner.transform_bootstrap
    build = json.loads(args.build.read_text())
    report = {"build_sha256": digest(args.build.read_bytes()), "measurements": [], "selected": [],
              "compiler_group_sha256": digest(owner_path.read_bytes()),
              "eligible_4k": False, "scope": "complete file costs plus actual packaged runtime; no strength/speed claim"}
    for row in build["engines"]:
        if row["form"] == "dev":
            continue
        source = Path(row["cwd"])
        files = {name: (source / name).read_bytes() for name in row["generated_sha256"]}
        if any(digest(data) != row["generated_sha256"][name] for name, data in files.items()):
            raise RuntimeError("generated source changed since build evidence")
        directory = args.out / row["id"]
        directory.mkdir()
        kinds = [("source", files, row["compile"])]
        if row["form"] == "shipping":
            native = Path(row["command"][0])
            if digest(native.read_bytes()) != row["native_sha256"]:
                raise RuntimeError("native changed since build evidence")
            stripped = directory / "stripped"
            command = [args.strip, "--strip-all", "-o", str(stripped), str(native)]
            subprocess.run(command, check=True, capture_output=True, timeout=30)
            kinds.append(("native", {"x": stripped.read_bytes()}, None))
            report["measurements"].append({"id": row["id"], "format": "stripped-native-elf",
                                            "path": str(stripped), "bytes": stripped.stat().st_size,
                                            "sha256": digest(stripped.read_bytes()), "command": command})
        for kind, payload, command in kinds:
            first = write_launchers(payload, directory / kind / "first", command=command,
                                    compiler_group=compiler_group if command else None)
            second = write_launchers(payload, directory / kind / "second", command=command,
                                     compiler_group=compiler_group if command else None)
            for one, two in zip(first, second):
                data = Path(one["path"]).read_bytes()
                if data != Path(two["path"]).read_bytes():
                    raise RuntimeError("whole package reproduction differs")
                report["measurements"].append({**one, "id": row["id"], "kind": kind,
                                                "layout": row["layout"], "update": row["update"],
                                                "sha256": digest(data), "reproduced": True})
    specs = []
    for layout in ("0x88", "10x12"):
        for update in ("copy", "unmake"):
            for kind in ("source", "native"):
                candidates = [r for r in report["measurements"] if r.get("layout") == layout and
                              r.get("update") == update and r.get("kind") == kind]
                winner = min(candidates, key=lambda r: (r["bytes"], r["path"]))
                report["selected"].append(winner)
                specs.append({"id": f"A-{layout}-{update}-{kind}-minimum", "profile": "shipping",
                              "command": [winner["path"]], "expected_program_sha256": winner["sha256"],
                              "workers": build["workers"], "startup_threads": build["workers"] + 1,
                              "max_threads": build["workers"] + 1, "startup_timeout": 60})
                print(json.dumps({k: winner[k] for k in ("id", "kind", "bytes", "sha256")}), flush=True)
    manifest = args.out / "selected.json"
    manifest.write_text(json.dumps({"engines": specs}, indent=2) + "\n")
    (args.out / "measurements.json").write_text(json.dumps(report, indent=2) + "\n")
    command = [sys.executable, str(ROOT / "engines" / "tests" / "verify.py"), "--manifest", str(manifest),
               "--out", str(args.out / "verification"), "--suite", "shipping"]
    subprocess.run(command, check=True, timeout=600)
    report["verification"] = {"path": str(args.out / "verification" / "results.json"), "passed": True}
    (args.out / "measurements.json").write_text(json.dumps(report, indent=2) + "\n")
    print(str(args.out / "measurements.json"), flush=True)


if __name__ == "__main__":
    main()
