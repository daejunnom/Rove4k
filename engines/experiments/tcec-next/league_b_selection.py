#!/usr/bin/env python3
"""Explicit experimental B source-JIT recipe for the two league profiles.

This only selects a candidate.  Source admission, actual target execution,
placement and scored-league admission are separate requirements.
"""
import argparse
import json
from pathlib import Path


WORKERS = {"test-p16": 16, "test-p192": 192}
POST_PROFILE = {"path": "engines/experiments/tcec-next/profile_b.py", "variant": "tcec-final-lf"}
POST_SPELLING = {"path": "engines/experiments/tcec-next/profile_b_league_spelling.py",
                 "selection": "league-atomic", "variant": "atomic-assignment"}
DEPENDENCIES = {"path": "engines/experiments/tcec-next/profile_dependencies.py", "variant": "unused-includes"}


def arguments(profile):
    if type(profile) is not str or profile not in WORKERS:
        raise ValueError("explicit B P16 or P192 profile required")
    return ["--entry", "B", "--profile", profile, "--representation", "source-jit",
            "--b-variant", "tcec-final-lf", "--phase-variant", "control",
            "--spelling-variant", "league-atomic", "--scan-variant", "control",
            "--ep-variant", "control", "--source-dependencies", "unused-includes"]


def check_manifest(record, profile):
    arguments(profile)
    if not isinstance(record, dict):
        raise ValueError("candidate producer manifest required")
    resources, plan = record.get("resources"), record.get("plan")
    if not isinstance(resources, dict) or not isinstance(plan, dict):
        raise ValueError("candidate resource and plan records required")
    if (record.get("entry") != "B" or record.get("family") != "B"
            or resources.get("id") != profile or type(resources.get("workers")) is not int
            or resources["workers"] != WORKERS[profile]
            or plan.get("representation") != "source-jit" or plan.get("entry_cleanup") != "private-path"
            or plan.get("full") is not True or record.get("complete") is not True
            or record.get("reproducible") is not True
            or record.get("post_profile") != POST_PROFILE or record.get("post_spelling") != POST_SPELLING
            or record.get("source_dependencies") != DEPENDENCIES
            or record.get("post_scan") is not None or record.get("post_ep") is not None
            or record.get("spelling_request") is not None):
        raise ValueError("producer manifest differs from the B league candidate recipe")
    return {"family": "B", "profile": profile, "selection": "league-atomic",
            "candidate_only": True, "runtime_qualified": False, "league_admitted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=tuple(WORKERS), required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--emit-arguments", action="store_true")
    group.add_argument("--check-manifest", type=Path)
    args = parser.parse_args()
    if args.emit_arguments:
        print("\n".join(arguments(args.profile)))
    else:
        print(json.dumps(check_manifest(json.loads(args.check_manifest.read_text()), args.profile), sort_keys=True))


if __name__ == "__main__":
    main()
