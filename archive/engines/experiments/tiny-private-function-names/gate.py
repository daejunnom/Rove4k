#!/usr/bin/env python3
"""One full-native gate per fixed static-plus-locals source; no packaging."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

COMPOSE_SHA = "b7750a084d5389ec5aa3ed579185639a58ba73ce0d297815b71a897310f7c076"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composed", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    composed, out = args.composed.resolve(), args.out.resolve()
    raw = (composed / "compose.json").read_bytes()
    if identity(raw)["sha256"] != COMPOSE_SHA or not args.out.is_absolute() or out.exists():
        raise ValueError("exact fixed composition receipt and new absolute output required")
    proposal = json.loads(raw)
    if not proposal["complete"] or any((p / ".git").exists() for p in (out, *out.parents)):
        raise ValueError("complete source proposal and external output required")
    out.mkdir(parents=True)
    report = {"complete": False, "scope": __doc__, "composition_receipt_sha256": COMPOSE_SHA,
              "families": {}, "native_compiles": 0, "codec_calls": 0, "engine_executions": 0,
              "static_only_class_is_separate": "Static-only metadata differs from maintained full native; this gate allows NO byte difference from static-only native"}
    def save():
        (out / "gate.json").write_bytes((json.dumps(report, indent=2) + "\n").encode())
    save()
    try:
        for family, row in proposal["families"].items():
            source = (composed / family / "candidate.c").read_bytes()
            baseline = Path(row["static_native_path"]).read_bytes()
            if identity(source) != row["combined_source"] or identity(baseline) != row["static_native"]:
                raise ValueError("fixed combined source/static-only native changed")
            directory = out / family
            directory.mkdir()
            compiled = subprocess.run(row["compiler"], input=source, cwd=directory,
                                      capture_output=True, timeout=90)
            report["native_compiles"] += 1
            (directory / "compiler.stdout").write_bytes(compiled.stdout)
            (directory / "compiler.stderr").write_bytes(compiled.stderr)
            if compiled.returncode:
                raise ValueError("combined native compile failed")
            candidate = (directory / "x").read_bytes()
            report["families"][family] = {"source": identity(source), "native": identity(candidate),
                "static_native": identity(baseline), "full_native_equal": candidate == baseline,
                "compiler": row["compiler"], "native_path": str(directory / "x")}
            save()
            if candidate != baseline:
                raise ValueError("full-native byte identity gate rejected: " + family)
            print(json.dumps({"family": family, "full_native_equal": True, "native": identity(candidate)}), flush=True)
        report["complete"] = True
        save()
    except Exception as error:
        report["error"] = repr(error)
        save()
        raise


if __name__ == "__main__":
    main()
