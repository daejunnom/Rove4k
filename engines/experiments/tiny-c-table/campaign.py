#!/usr/bin/env python3
"""Bounded startup/readonly PSQT full-file experiment over frozen TinyC6059."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-c-build", type=Path, required=True)
    parser.add_argument("--control-a-build", type=Path, required=True)
    parser.add_argument("--control-a-artifact", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT == args.out or ROOT in args.out.parents:
        parser.error("--out must be new, absolute and outside the checkout")
    args.out.mkdir(parents=True)
    c_data, a_data = args.control_c_build.read_bytes(), args.control_a_build.read_bytes()
    c_control, a_control = json.loads(c_data), json.loads(a_data)
    if c_control["features"]["variant"] != "C" or c_control["selected"]["bytes"] != 6059:
        raise ValueError("the declared 6059-byte TinyC control is required")
    expected_a_sha = "3a33e40a202ad7319c7b8198fd99e42e7813b54bd0be64dd50e9c23f971bfb76"
    a_artifact = args.control_a_artifact.read_bytes()
    if len(a_artifact) != 5671 or sha(a_artifact) != expected_a_sha:
        raise ValueError("the exact independently qualified 5671-byte TinyA control is required")
    c_artifact = Path(c_control["selected"]["path"]).read_bytes()
    if len(c_artifact) != 6059 or sha(c_artifact) != c_control["selected"]["sha256"]:
        raise ValueError("TinyC control artifact changed")
    compiler = subprocess.check_output(["cc", "--version"], text=True).splitlines()[0]
    if compiler != c_control["compiler"] or compiler != a_control["compiler"]:
        raise ValueError("control and candidate compiler identities differ")
    core_map = {"tiny.h": "tiny.h", "board-generated.c.in": "board.c", "search.c": "search.c", "main.c": "main.c"}
    frozen = args.out / "frozen"
    runtime_inputs = {}
    for name, expected in c_control["input_sha256"].items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name:
            raise ValueError("invalid control recipe source path")
        data = (args.control_c_build.parent / "recipe" / name).read_bytes()
        if sha(data) != expected:
            raise ValueError("control recipe input changed: " + name)
        destination = frozen / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        runtime_inputs[name] = expected
    for a_name, core_name in core_map.items():
        c_name = "engines/compact/tiny-ce/core/" + core_name
        if a_control["source_sha256"][a_name] != runtime_inputs[c_name]:
            raise ValueError("TinyA/TinyC core identity differs")
    extra_inputs = {}
    for path in (HERE / "campaign.py", HERE / "generate.py", HERE / "table-eval.c.in", HERE / "table_contract.c",
                 HERE / "qualify.py", HERE / "test_generate.py", ROOT / "engines/compact/tiny-ce/check.py",
                 ROOT / "engines/compact/tiny-ce/restoration.py", ROOT / "engines/compact/tiny-ce/blackbox.py",
                 ROOT / "engines/tests/verify.py", ROOT / "engines/tests/chess_oracle.py"):
        name = str(path.relative_to(ROOT))
        data = path.read_bytes()
        dest = frozen / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        extra_inputs[name] = sha(data)
    controls = args.out / "controls"
    controls.mkdir()
    for name, data in (("C-build.json", c_data), ("A-build.json", a_data), ("C-6059", c_artifact), ("A-5671", a_artifact)):
        (controls / name).write_bytes(data)
    producer = frozen / "engines/experiments/tiny-c-table"
    generator = load("tiny_c_table_frozen_generate", producer / "generate.py")
    report = {"scope": "two actual AVX2 table representations; no canonical promotion or 4KiB eligibility",
              "compiler": compiler, "controls": {"A": {"bytes": 5671, "sha256": sha(a_artifact), "build_sha256": sha(a_data)},
                                                 "C": {"bytes": 6059, "sha256": sha(c_artifact), "build_sha256": sha(c_data)}},
              "control_core_identical": True, "runtime_input_sha256": runtime_inputs,
              "experiment_validation_input_sha256": extra_inputs, "candidates": [], "complete": False}
    try:
        for representation in generator.REPRESENTATIONS:
            candidate = args.out / representation
            recipe = candidate / "producer"
            shutil.copytree(frozen, recipe)
            evaluator, table = generator.produce((producer / "table-eval.c.in").read_bytes(), representation)
            evaluator_path = recipe / "engines/compact/tiny-ce/c-eval.c.in"
            evaluator_path.write_bytes(evaluator)
            table["evaluator_sha256"] = sha(evaluator)
            table["template_sha256"] = extra_inputs["engines/experiments/tiny-c-table/table-eval.c.in"]
            build_path = candidate / "build"
            command = [sys.executable, "-I", "-B", str(recipe / "engines/compact/tiny-ce/build.py"), "--variant", "C", "--out", str(build_path)]
            subprocess.run(command, check=True, timeout=180)
            build = json.loads((build_path / "build.json").read_bytes())
            sizes = {}
            for engine in build["engines"]:
                if "native_bytes" in engine:
                    sizes[engine["id"]] = {key: engine[key] for key in ("native_bytes", "native_sha256", "source_bytes", "source_sha256")}
            binary = build_path / "original/x"
            sections = subprocess.check_output(["size", "-A", str(binary)], text=True)
            (candidate / "native-sections.txt").write_text(sections)
            entry = {"representation": representation, "table": table, "build": str(build_path / "build.json"),
                     "build_sha256": sha((build_path / "build.json").read_bytes()), "build_command": command,
                     "sizes": sizes, "selected": build["selected"], "selected_native": build["selected_native"],
                     "delta_complete_source_vs_C6059": build["selected"]["bytes"] - 6059,
                     "delta_complete_source_vs_A5671": build["selected"]["bytes"] - 5671,
                     "native_sections": sections, "native_reproduced": True, "complete_wrappers_reproduced": True,
                     "runtime_qualified": False}
            report["candidates"].append(entry)
            (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        report["complete"] = True
        report["source_cost_winner"] = min(report["candidates"], key=lambda item: item["selected"]["bytes"])["representation"]
    finally:
        (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"complete": True, "candidates": [{"representation": item["representation"], "bytes": item["selected"]["bytes"],
                     "delta_vs_C6059": item["delta_complete_source_vs_C6059"]} for item in report["candidates"]]}))


if __name__ == "__main__":
    main()
