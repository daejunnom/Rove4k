#!/usr/bin/env python3
"""Prepare strict combined-source bootstrap/argv artifacts, without encoding."""

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

COMPOSE_SHA = "b7750a084d5389ec5aa3ed579185639a58ba73ce0d297815b71a897310f7c076"
WHOLE_SHA = "430089b211c0f7888ea7a5c6ee8b3bc3940332c65103591f4dc480750b36a6e1"
GATE_SHA = "6347ebba4845b73d28155ac7b8d0df447d37c21ece9a8d1b87feede5189336f6"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composed", required=True, type=Path)
    parser.add_argument("--gate", required=True, type=Path)
    parser.add_argument("--static-whole", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    composed, gate, whole, out = args.composed.resolve(), args.gate.resolve(), args.static_whole.resolve(), args.out.resolve()
    compose_raw, gate_raw, whole_raw = [(folder / name).read_bytes() for folder, name in
        ((composed, "compose.json"), (gate, "gate.json"), (whole, "whole.json"))]
    if (identity(compose_raw)["sha256"] != COMPOSE_SHA or identity(whole_raw)["sha256"] != WHOLE_SHA
            or identity(gate_raw)["sha256"] != GATE_SHA):
        raise ValueError("fixed composition/original-static-whole receipt changed")
    proposal, gate_report, old_whole = json.loads(compose_raw), json.loads(gate_raw), json.loads(whole_raw)
    if (not proposal["complete"] or not gate_report["complete"] or not old_whole["complete"]
            or gate_report["composition_receipt_sha256"] != COMPOSE_SHA
            or not all(row["full_native_equal"] for row in gate_report["families"].values())):
        raise ValueError("complete full-native gate required")
    if not args.out.is_absolute() or out.exists() or any((p / ".git").exists() for p in (out, *out.parents)):
        raise ValueError("new absolute external output required")
    out.mkdir(parents=True)
    reader = module(Path(__file__).with_name("whole.py"), "private_combined_literal_reader")
    report = {"complete": False, "scope": __doc__, "composition_receipt_sha256": COMPOSE_SHA,
        "gate_receipt": identity(gate_raw), "static_whole_receipt_sha256": WHOLE_SHA,
        "families": {}, "codec_calls": 0, "native_compiles": 0, "engine_executions": 0,
        "combined_original_codec_cost_measured_here": False}
    for family, row in proposal["families"].items():
        source = (composed / family / "candidate.c").read_bytes()
        if identity(source) != row["combined_source"] or gate_report["families"][family]["source"] != identity(source):
            raise ValueError("exact combined-source gate binding changed")
        directory = out / family
        directory.mkdir()
        packaging = {}
        for name in ("bootstrap.py.in", "launcher.sh", "pack_stream.py"):
            raw = (whole / family / name).read_bytes()
            relative = next(key for key in old_whole["families"][family]["packaging_inputs"] if key.endswith("/" + name))
            if identity(raw) != old_whole["families"][family]["packaging_inputs"][relative]:
                raise ValueError("original packaging source changed")
            packaging[name] = raw
        literal = module(whole / family / "pack_stream.py", "private_combined_literal_" + family).source_literal
        expression, literal_kind = literal(source)
        template = packaging["bootstrap.py.in"]
        if template.count(b"__ROVE_SOURCE_LITERAL__") != 1 or len(packaging["launcher.sh"]) != 75:
            raise ValueError("fixed original prefix/template shape changed")
        script = template.replace(b"__ROVE_SOURCE_LITERAL__", expression.encode())
        tree = ast.parse(script)
        popens = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess" and node.func.attr == "Popen"]
        if len(popens) != 1 or ast.literal_eval(popens[0].args[0]) != row["compiler"] or reader.source_argument(tree) != source:
            raise ValueError("strict source/compiler argv restoration differs")
        (directory / "bootstrap.py").write_bytes(script)
        (directory / "launcher.sh").write_bytes(packaging["launcher.sh"])
        (directory / "compiler.json").write_bytes((json.dumps(row["compiler"]) + "\n").encode())
        report["families"][family] = {"source_path": str(composed / family / "candidate.c"), "source": identity(source),
            "bootstrap_path": str(directory / "bootstrap.py"), "bootstrap": identity(script),
            "prefix_path": str(directory / "launcher.sh"), "prefix": identity(packaging["launcher.sh"]),
            "compiler": row["compiler"], "literal_kind": literal_kind, "strict_source_and_argv_restored": True,
            "native": gate_report["families"][family]["native"], "full_static_native_equal": True,
            "static_only_original_whole": old_whole["families"][family]["whole"],
            "static_only_original_whole_path": str(whole / family / "x"),
            "combined_original_codec_whole": "unmeasured; codec owner will measure actual combined input"}
    report["complete"] = True
    raw = (json.dumps(report, indent=2) + "\n").encode()
    (out / "bootstrap.json").write_bytes(raw)
    print(json.dumps({"receipt": identity(raw), "families": report["families"]}), flush=True)


if __name__ == "__main__":
    main()
