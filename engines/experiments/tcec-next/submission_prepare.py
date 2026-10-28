#!/usr/bin/env python3
"""Prepare a selected full W256 source-JIT deliverable from its real producer.

Run profile_build.py with selected_arguments() first. This consumer repeats the
existing strict admission, which may replay packaging, and copies exact artifacts.
It starts no new producer/compiler, launches no workers, allocates no TT and grants
no runtime/event qualification.
The ELF producer owns ELF preparation and deferred_size decisions separately.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import platform
import stat
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SELF = "engines/experiments/tcec-next/submission_prepare.py"
BUILDER = "engines/experiments/tcec-next/profile_build.py"
VERIFIER = "engines/experiments/tcec-next/profile_verify.py"
CONTRACTS = "engines/scripts/production.py"
PROFILE = "tcec-provisional"
REPRESENTATION = "source-jit"
MAX_FILE = 8 << 20


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def equal(left, right):
    options = dict(sort_keys=True, separators=(",", ":"), allow_nan=False)
    return json.dumps(left, **options) == json.dumps(right, **options)


def selection(family, *, ep_variant="control"):
    require(type(family) is str and family in tuple("ABCEF"), "one full non-D C family required")
    require(type(ep_variant) is str and ep_variant in ("control", "legal-maker")
            and (ep_variant == "control" or family in ("C", "E")),
            "explicit C/E legal-maker or control EP selection required")
    result = dict(b_variant="tcec-final-lf" if family == "B" else "control",
                phase_variant="control" if family == "B" else "phase-init",
                spelling_variant="best" if family == "B" else "compound-v2" if family == "F" else "compound",
                scan_variant="square-successor" if family in "AC" else "control",
                source_dependencies="unused-includes")
    if ep_variant != "control":
        result["ep_variant"] = ep_variant
    if family in "ABF" or (family in "CE" and ep_variant == "legal-maker"):
        result["final_compact"] = "selected"
    return result


def selected_arguments(family, *, ep_variant="control"):
    """Existing producer arguments; the caller supplies its new external --out."""
    result = ["--entry", family, "--profile", PROFILE, "--representation", REPRESENTATION]
    for name, value in selection(family, ep_variant=ep_variant).items():
        result.extend(("--" + name.replace("_", "-"), value))
    return result


def validate_selection(record, family, builder, *, ep_variant="control"):
    chosen = selection(family, ep_variant=ep_variant)
    require(record.get("family") == record.get("entry") == family,
            "producer family differs from the explicit submission entry")
    resources = record.get("resources", {})
    plan = record.get("plan", {})
    require(resources.get("id") == PROFILE and type(resources.get("workers")) is int
            and resources["workers"] == 256 and plan.get("representation") == REPRESENTATION
            and plan.get("entry_cleanup") == "private-path" and plan.get("full") is True,
            "full W256 source-JIT/private-path producer required")
    post = dict(path=builder.B_PROFILE, variant=chosen["b_variant"]) if family == "B" else dict(
        path=builder.PHASE, variant=chosen["phase_variant"])
    spelling = builder.spelling_selection(family, REPRESENTATION, chosen["b_variant"],
                                          chosen["phase_variant"], chosen["spelling_variant"])
    scan = builder.scan_selection(family, REPRESENTATION, chosen["phase_variant"], spelling,
                                  chosen["source_dependencies"], chosen["scan_variant"])
    require(equal(record.get("post_profile"), post)
            and equal(record.get("post_spelling"), spelling)
            and equal(record.get("post_scan"), scan)
            and equal(record.get("source_dependencies"), dict(path=builder.DEPENDENCIES, variant="unused-includes"))
            and record.get("spelling_request") is None,
            "submission must use the maintained explicit source stages and final include cleanup")
    post_ep = dict(path=builder.EP, variant="legal-maker") if ep_variant != "control" else None
    require(equal(record.get("post_ep"), post_ep)
            and (ep_variant != "control" or "ep_native_policy" not in record),
            "submission EP differs from the explicit selected recipe")
    compact = builder.FINAL_COMPACTS.get(family) if chosen.get("final_compact") == "selected" else None
    compact_declaration = ({"path": compact["path"], "variant": compact["variant"]} if compact else None)
    require(equal(record.get("post_compact"), compact_declaration),
            "submission final compaction differs from the explicit selected recipe")
    require(equal(record.get("compiler"), record.get("compile_executor")),
            "submission preparation uses its original producer compiler")


def size_decisions(family, whole_bytes, contracts):
    selection(family)
    plan = contracts.ArtifactPlan(contracts.engine_spec(family), contracts.resource_profile(PROFILE),
                                 REPRESENTATION, "private-path", full=True)
    return {division: plan.size_decision(whole_bytes, division) for division in ("general4k", "elf4k")}


def external_path(path, *, existing):
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "explicit absolute artifact path required")
    require(not any(part.lower().startswith(".env") or part.lower() in (".aws", ".ssh", "inventory.json")
                    or any(word in part.lower() for word in ("credential", "service-account", "service_account", "api_key", "ssh_key"))
                    for part in path.parts), "protected path is not a submission artifact")
    require(not any(component.is_symlink() for component in (path, *path.parents)), "artifact path cannot follow links")
    require(not any((component / ".git").exists() for component in (path, *path.parents)),
            "submission artifacts must remain outside every checkout")
    require(path.is_dir() if existing else not os.path.lexists(path), "existing build or new output directory required")
    return path


def load(relative, name):
    require(relative in (BUILDER, VERIFIER), "only the canonical producer/verifier modules may be loaded")
    path = ROOT / relative
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and metadata.st_size <= 1 << 20,
            "bounded ordinary canonical Python tool required")
    before = path.read_bytes().replace(b"\r\n", b"\n")
    require(len(before) <= 1 << 20 and b"\r" not in before and not path.is_symlink(), "bounded canonical Python tool required")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    require(path.read_bytes().replace(b"\r\n", b"\n") == before, "canonical tool changed while loading")
    return module


def write_at(directory, name, data, *, executable=False):
    require(type(data) is bytes and len(data) <= MAX_FILE and type(name) is str
            and Path(name).name == name and name not in (".", "..") and "\\" not in name,
            "one bounded named deliverable required")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(name, flags, 0o700 if executable else 0o600, dir_fd=directory)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def prepare_submission(build, out, *, family, ep_variant="control", execute=False):
    require(execute is True, "submission preparation is inactive without --execute")
    selection(family, ep_variant=ep_variant)
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 artifact consumer required")
    build, out = external_path(build, existing=True), external_path(out, existing=False)
    require(not out.is_relative_to(build) and not build.is_relative_to(out), "producer and output roots must be disjoint")
    verify = load(VERIFIER, "rove_submission_prepare_verify")
    builder = load(BUILDER, "rove_submission_prepare_builder")
    contracts = verify.contracts()
    reader = verify.input_reader()
    sources = {name: reader.read_regular(ROOT / name, limit=1 << 20).replace(b"\r\n", b"\n")
               for name in (SELF, BUILDER, VERIFIER, CONTRACTS)}
    manifest_raw = reader.read_regular(verify.artifact_file(build, "build.json"), limit=MAX_FILE)
    manifest = json.loads(manifest_raw)
    admitted = verify.admit_c_build(manifest, build)
    validate_selection(manifest, family, builder, ep_variant=ep_variant)
    require(admitted.family == family and admitted.profile_id == PROFILE and admitted.full
            and admitted.representation == REPRESENTATION, "strict full submission admission differs")
    require(equal(manifest.get("host_cleanup"), dict(unsettled_commands=0, errors=[])),
            "producer commands have not settled cleanly")
    proof_raw = reader.read_regular(verify.artifact_file(build, "source-proof.json"), limit=MAX_FILE)
    require(equal(json.loads(proof_raw), manifest["source_proofs"]), "raw source proof differs from the admitted producer")
    identities = admitted.expected
    artifact = lambda name, role: verify.checked_artifact(build, name, {
        key: identities[role + "_" + key] for key in ("bytes", "sha256")})
    files = {"Rove4k-" + family: artifact(admitted.program, "whole"), "main.c": artifact(admitted.source, "source"),
             "native.elf": artifact(admitted.native, "native"), "producer-build.json": manifest_raw,
             "source-proof.json": proof_raw}
    dependencies = verify.native_dependencies(files["native.elf"])
    record = dict(format="rove4k-submission-prepared-v1", prepared=False, family=family, profile=PROFILE,
        representation=REPRESENTATION, full=True, source_build=str(build), producer_manifest=pin(manifest_raw),
        resources=admitted.resources, source_closure=manifest["source_closure"], dependencies=dependencies,
        compiler=manifest["compiler"], wrapper_contract=admitted.wrapper_contract,
        source_selection=selection(family, ep_variant=ep_variant), size=size_decisions(family, len(files["Rove4k-" + family]), contracts),
        consumer_sources={name: pin(data) for name, data in sources.items()}, files={},
        compile_package_only=True, runtime_qualified=False, general_candidate_ready=False,
        general_submission_ready=False, elf_qualified=False, event_target_confirmed=False,
        league_admitted=False, strength_qualified=False, release_qualified=False,
        workers_started=0, TT_allocated=False,
        scope="strict source/type/native/package preparation only; no W256 runtime, event or playing-strength qualification")
    parent = reader.open_directory(out.parent)
    directory = None
    try:
        os.mkdir(out.name, 0o700, dir_fd=parent)
        directory = os.open(out.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), dir_fd=parent)
        try:
            for name, data in files.items():
                write_at(directory, name, data, executable=name.startswith("Rove4k-") or name == "native.elf")
                record["files"][name] = pin(data)
            require(reader.read_regular(verify.artifact_file(build, "build.json"), limit=MAX_FILE) == manifest_raw
                    and verify.admit_c_build(manifest, build) == admitted, "producer admission changed during export")
            for name, original in sources.items():
                require(reader.read_regular(ROOT / name, limit=1 << 20).replace(b"\r\n", b"\n") == original,
                        "canonical consumer source changed during preparation")
            reader.same_directory(out.parent, parent)
            reader.same_directory(out, directory)
            record["prepared"] = True
        except BaseException as error:
            record["failure"] = dict(type=type(error).__name__, message=str(error))
            try:
                write_at(directory, "submission.json", (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
            except BaseException as write_error:
                raise error from write_error
            raise
        write_at(directory, "submission.json", (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
    finally:
        if directory is not None:
            os.close(directory)
        os.close(parent)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", choices=tuple("ABCEF"), required=True)
    parser.add_argument("--ep-variant", choices=("control", "legal-maker"), default="control",
                        help="optional C/E EP recipe; the default preserves the maintained source selection")
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required before admission or output creation")
    result = prepare_submission(args.build, args.out, family=args.entry, ep_variant=args.ep_variant, execute=True)
    print(json.dumps(dict(prepared=result["prepared"], family=args.entry, profile=PROFILE, size=result["size"],
                          runtime_qualified=False, event_target_confirmed=False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
