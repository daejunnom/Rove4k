#!/usr/bin/env python3
"""Compare same-run P16/P192 control and opt-in league candidates.

This records the actual entire file and a same-host repack of both sources.
It is not engine execution, runtime admission, or evidence of playing strength.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HELPERS = {
    "square-successor": "engines/experiments/tcec-next/profile_league_square.py",
    "legal-maker": "engines/experiments/tcec-next/league_ep.py",
    "atomic-assignment": "engines/experiments/tcec-next/profile_acef_league_atomic.py",
}
PACKAGE = "engines/scripts/source_package.py"
WRAPPER = "engines/experiments/tcec-next/wrapper.py"
UNLINK = "engines/experiments/tcec-next/self_unlink.py"


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def pin(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read_json(path):
    return json.loads(path.read_bytes())


def checked_pair(control, candidate, *, family, profile, variant):
    require(family in "ACEF" and len(family) == 1 and profile in ("test-p16", "test-p192")
            and variant in HELPERS, "explicit league comparison identity required")
    roots = (Path(control), Path(candidate))
    records = [read_json(root / "build/build.json") for root in roots]
    audits = [read_json(root / "artifact-audit.json") for root in roots]
    for i, (root, record, audit) in enumerate(zip(roots, records, audits)):
        require(record.get("family") == family and record.get("resources", {}).get("id") == profile
                and record.get("complete") is True and record.get("reproducible") is True,
                "actual producer identity or completion differs")
        require((audit.get("family"), audit.get("profile"), audit.get("variant")) ==
                (family, profile, "control" if i == 0 else variant), "audit identity differs")
        whole = (root / "build/x").read_bytes()
        require(audit.get("parts", {}).get("x") == pin(whole)
                and audit.get("actual_whole_bytes") == len(whole), "actual whole file differs from audit")
        admission = read_json(root / "admission.json")
        require(admission.get("strict_source_admission") is True and
                (admission.get("family"), admission.get("profile"), admission.get("variant")) ==
                (family, profile, "control" if i == 0 else variant), "strict source admission identity differs")
        rules = read_json(root / "rules/probe/rules.json")
        commands = read_json(root / "rules/commands.json")
        rows = commands.get("commands", [])
        source = (root / "build/main.c").read_bytes()
        require(rules.get("complete") is True and rules.get("family") == family
                and rules.get("profile", {}).get("id") == profile and rules.get("source") == pin(source)
                and commands.get("complete") is True
                and commands.get("host_cleanup") == {"unsettled_commands": 0, "errors": []}
                and [row.get("kind") for row in rows] == ["rules-compile-plain", "rules-execute-plain",
                    "rules-compile-ubsan", "rules-execute-ubsan"]
                and all(row.get("returncode") == 0 and row.get("terminal") is True
                    and row.get("reaped") is True and row.get("owned_group_absent") is True
                    and row.get("forced_cleanup") is False for row in rows),
                "actual source-bound rules are incomplete")
    require(records[0].get("post_league") is None and records[1].get("post_league") ==
            {"path": HELPERS[variant], "variant": variant}, "candidate selection declaration differs")
    for key in ("compiler", "compile_executor", "compile_executor_version", "compression"):
        require(records[0].get(key) == records[1].get(key), "producer compiler or compression differs: " + key)
    for path in ("resource-projection.c", "build/control/main.c", "build/header.sh",
                 "compiler-sha256.txt", "linker-sha256.txt"):
        require((roots[0] / path).read_bytes() == (roots[1] / path).read_bytes(),
                "producer parent, wrapper or tool identity differs: " + path)
    sources = [(root / "build/main.c").read_bytes() for root in roots]
    proof = records[1].get("source_proofs", [])[-1]
    require(proof.get("input") == pin(sources[0]) and proof.get("output") == pin(sources[1])
            and proof.get("variant") == variant and proof.get("full_inverse") is True,
            "candidate stage does not bind the actual control and candidate sources")
    return roots, records, sources


def load_shared(name, relative, roots):
    live_path = Path(relative).resolve()
    raw = live_path.read_bytes()
    require(all((root / "build/inputs" / relative).read_bytes() == raw for root in roots),
            "same-host packaging input differs from a frozen producer: " + relative)
    spec = importlib.util.spec_from_file_location(name, live_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def compare(control, candidate, *, family, profile, variant):
    roots, records, sources = checked_pair(control, candidate, family=family, profile=profile, variant=variant)
    package = load_shared("league_compare_package", PACKAGE, roots)
    wrapper = load_shared("league_compare_wrapper", WRAPPER, roots)
    unlink = load_shared("league_compare_unlink", UNLINK, roots)
    whole = [(root / "build/x").read_bytes() for root in roots]
    replay = [wrapper.package(package, unlink, source, records[0]["compression"], records[0]["compiler"])
              for source in sources]
    return {"family": family, "profile": profile, "variant": variant,
            "actual_control": pin(whole[0]), "actual_candidate": pin(whole[1]),
            "actual_candidate_minus_control_bytes": len(whole[1]) - len(whole[0]),
            "same_host_control": pin(replay[0]), "same_host_candidate": pin(replay[1]),
            "same_host_candidate_minus_control_bytes": len(replay[1]) - len(replay[0]),
            "same_host_matches_original": [replay[i] == whole[i] for i in range(2)],
            "candidate_at_most_4096": len(whole[1]) <= 4096,
            "producer_source_and_rules_passed": True,
            "comparison_scope": "same-run producer evidence; independent Ubuntu 22 compiler and rules run separately",
            "production_selected": False,
            "runtime_qualified": False, "physical_placement_qualified": False,
            "playing_strength_qualified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.control, args.candidate, family=args.family,
                     profile=args.profile, variant=args.variant)
    with args.out.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, sort_keys=True)
        output.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
