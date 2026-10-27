#!/usr/bin/env python3
"""Compare a league combination against its actual same-run constituents.

Producer source/rules receipts and byte identity are checked before comparison.
The separately scheduled Ubuntu 22 compiler/rules job is not implied here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("league_compound_compare_single", HERE / "league_candidate_compare.py")
single = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = single
spec.loader.exec_module(single)

COMPOUND_PATH = "engines/experiments/tcec-next/profile_league_compound.py"
COMPOUND_SCHEMA = "rove4k.league-combined-source.v1"
VARIANTS = {
    "square-atomic": ("square", "atomic"),
    "square-ep": ("square", "ep"),
    "ep-atomic": ("ep", "atomic"),
    "square-ep-atomic": ("square", "ep", "atomic"),
}
FAMILIES = {"square-atomic": "AC", "square-ep": "C", "ep-atomic": "CE", "square-ep-atomic": "C"}
SINGLES = {"square": "square-successor", "ep": "legal-maker", "atomic": "atomic-assignment"}
PAIRS = ("square-atomic", "square-ep", "ep-atomic")


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def named(rows, expected, label):
    require(type(rows) is list and all(type(row) in (tuple, list) and len(row) == 2 for row in rows),
            label + " must be named path pairs")
    result = {}
    for key, path in rows:
        require(type(key) is str and key in expected and key not in result, label + " identity differs")
        result[key] = Path(path)
    require(set(result) == set(expected), label + " is incomplete")
    return result


def checked(control, candidate, *, family, profile, variant):
    # The single-candidate admission checks bind same-run producer/rules
    # receipts, resource projection, compiler identity, full file and proof.
    single.HELPERS[variant] = COMPOUND_PATH
    roots, records, sources = single.checked_pair(control, candidate, family=family, profile=profile, variant=variant)
    proof = records[1]["source_proofs"][-1]
    require(proof.get("schema") == COMPOUND_SCHEMA and proof.get("family") == family
            and proof.get("profile_id") == profile and proof.get("variant") == variant,
            "combined proof identity differs")
    components = proof.get("components")
    require(type(components) is list and all(type(row) is dict and set(row) == {"component", "proof"}
            for row in components) and tuple(row["component"] for row in components) == VARIANTS[variant],
            "combined component order or shape differs")
    return roots, records, sources, proof


def checked_comparison(control, candidate, *, family, profile, variant, singles, pairs):
    require(type(family) is str and len(family) == 1 and type(variant) is str and variant in VARIANTS
            and family in FAMILIES[variant] and profile in ("test-p16", "test-p192"),
            "explicit combination family and profile required")
    needed = tuple(SINGLES[name] for name in VARIANTS[variant])
    single_paths = named(singles, needed, "single candidates")
    pair_paths = named(pairs, PAIRS if variant == "square-ep-atomic" else (), "pair candidates")
    c_roots, c_records, c_sources, c_proof = checked(control, candidate, family=family, profile=profile, variant=variant)
    roots = {"control": c_roots[0], variant: c_roots[1]}
    records = {"control": c_records[0], variant: c_records[1]}
    sources = {"control": c_sources[0], variant: c_sources[1]}
    single_proofs = {}
    for name in needed:
        p_roots, p_records, p_sources = single.checked_pair(control, single_paths[name],
            family=family, profile=profile, variant=name)
        require(p_sources[0] == c_sources[0], "single candidate control source differs")
        roots[name], records[name], sources[name] = p_roots[1], p_records[1], p_sources[1]
        single_proofs[name] = p_records[1]["source_proofs"][-1]

    def verify_components(proof, requested):
        for row in proof["components"]:
            name = SINGLES[row["component"]]
            require(name in requested and canonical(row["proof"]) == canonical(single_proofs[name]),
                    "combination constituent proof differs from actual single candidate: " + name)

    verify_components(c_proof, needed)
    for name, path in pair_paths.items():
        p_roots, p_records, p_sources, proof = checked(control, path, family=family, profile=profile, variant=name)
        require(p_sources[0] == c_sources[0], "pair candidate control source differs")
        verify_components(proof, tuple(SINGLES[component] for component in VARIANTS[name]))
        roots[name], records[name], sources[name] = p_roots[1], p_records[1], p_sources[1]
    return roots, records, sources


def compare(control, candidate, *, family, profile, variant, singles, pairs):
    roots, records, sources = checked_comparison(control, candidate, family=family, profile=profile,
                                                   variant=variant, singles=singles, pairs=pairs)
    all_roots = tuple(roots.values())
    package = single.load_shared("league_combined_compare_package", single.PACKAGE, all_roots)
    wrapper = single.load_shared("league_combined_compare_wrapper", single.WRAPPER, all_roots)
    unlink = single.load_shared("league_combined_compare_unlink", single.UNLINK, all_roots)
    whole = {name: (root / "build/x").read_bytes() for name, root in roots.items()}
    replay = {name: wrapper.package(package, unlink, source, records["control"]["compression"],
                                    records["control"]["compiler"]) for name, source in sources.items()}
    comparisons = {}
    for name in roots:
        if name == variant:
            continue
        comparisons[name] = {"actual_candidate_minus_reference_bytes": len(whole[variant]) - len(whole[name]),
                             "same_host_candidate_minus_reference_bytes": len(replay[variant]) - len(replay[name])}
    return {"family": family, "profile": profile, "variant": variant,
            "actual_files": {name: single.pin(data) for name, data in whole.items()},
            "same_host_files": {name: single.pin(data) for name, data in replay.items()},
            "same_host_matches_original": {name: replay[name] == whole[name] for name in roots},
            "versus": comparisons, "candidate_at_most_4096": len(whole[variant]) <= 4096,
            "constituent_proofs_match": True, "producer_source_and_rules_passed": True,
            "comparison_scope": "same-run producer evidence; independent Ubuntu 22 compiler and rules run separately",
            "production_selected": False, "runtime_qualified": False,
            "physical_placement_qualified": False, "playing_strength_qualified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--single", nargs=2, action="append", default=[])
    parser.add_argument("--pair", nargs=2, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.control, args.candidate, family=args.family, profile=args.profile,
                     variant=args.variant, singles=args.single, pairs=args.pair)
    with args.out.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, sort_keys=True)
        output.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
