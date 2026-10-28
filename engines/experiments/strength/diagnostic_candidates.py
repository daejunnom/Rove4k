"""Prepare a source-pinned pre-GO cohort without claiming league admission.

This separate format accepts unqualified TEST candidates for initialization
diagnostics. It does not validate a scored plan, compile or execute an engine,
prove source-to-native provenance, issue GO, or reserve memory. Candidate
records and the three files must be independently pinned; hashes establish
identity of bytes, not authenticity or a successful build relationship.

The candidate-set JSON has format ``rove4k-diagnostic-candidate-set-v1``, a
``profile`` and ``candidates``. Each candidate has a registry Artifact record,
``source`` and ``native`` records (absolute path, bytes, sha256), and an
``evidence`` record. Evidence can be ``file-pins-only`` (no source-contract
claim), ``rove-profile-build-v1`` with a pinned ``build`` report, or
``peer-reference-v1`` with pinned ``build`` and ``reference`` reports. The
registry JSON and opening bank each require their own externally supplied SHA.
Output uses a distinct lock format; it is never a scored league plan.
By default topology comes from this process's effective affinity and memory
nodes on the intended target host. Supply the original target cgroup identity
when the observer runs in a narrower sibling cgroup. Matching its device and
inode establishes only a point-in-time identity, not caller ownership,
exclusive access, hidden ancestor visibility or a resource reservation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys

try:
    from . import ledger, registry, run, topology
except ImportError:
    import ledger
    import registry
    import run
    import topology


def _check_path_components(value):
    path = run.protected_input(Path(value))
    blocked = {"node_modules", "dist", "dist-server", "build", "coverage", "models", "checkpoints", ".cache"}
    lowered = [part.casefold() for part in path.parts]
    if (any(part in blocked or part.startswith(".env") or part in (".aws", ".ssh", ".npmrc", "id_rsa", "id_ed25519")
            or any(word in part for word in ("credential", "service-account", "service_account", "serviceaccount",
                                             "api_key", "api-key", "access_key", "access-key", "ssh_key",
                                             "secret", "password")) or part == "token" or part.startswith("token.")
            or part.endswith("_token") or part.endswith("-token")
            for part in lowered) or path.name.casefold() in ("package-lock.json", "inventory.json") or
            path.suffix.casefold() in (".pem", ".key", ".p12", ".pfx")):
        raise ValueError("generated or protected dependency input is not permitted")
    return path


def _safe_input_path(value):
    path = _check_path_components(value)
    if (".." in path.parts or path.is_symlink() or any(parent.is_symlink() for parent in path.parents) or
            path.resolve(strict=True) != path):
        raise ValueError("diagnostic input must not traverse links or parent escapes")
    return path


def _safe_output_path(value):
    # Component checks run before external_new can inspect the filesystem.
    path = _check_path_components(value)
    if ".." in path.parts:
        raise ValueError("diagnostic output cannot traverse parent escapes")
    return run.external_new(path)


def _pinned_file(record, *, expected=None):
    if (type(record) is not dict or set(record) != {"path", "sha256", "bytes"} or
            not isinstance(record["sha256"], str) or not run.SHA.fullmatch(record["sha256"]) or
            type(record["bytes"]) is not int or not 0 < record["bytes"] <= 256 << 20):
        raise ValueError("bounded pinned file identity required")
    path = _safe_input_path(record["path"])
    if (path.is_symlink() or not path.is_file() or any(parent.is_symlink() for parent in path.parents) or
            path.resolve(strict=True) != path or path.stat().st_size != record["bytes"] or
            registry.file_sha(path) != record["sha256"] or
            expected is not None and record["sha256"] != expected):
        raise ValueError("candidate file differs from its pinned identity")
    return path


def _profile_verifier():
    path = (run.ROOT / "engines/experiments/tcec-next/profile_verify.py").resolve(strict=True)
    name = "rove_diagnostic_profile_verify_" + hashlib.sha256(str(path).encode("utf-8")).hexdigest()
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    module = sys.modules[name]
    if Path(module.__file__).resolve(strict=True) != path:
        raise ValueError("profile verifier belongs to another source checkout")
    return module


def _source_evidence(evidence, artifact, whole, source, native):
    """Replay existing generation checks when their exact pinned receipts exist."""
    if evidence == {"kind": "file-pins-only"}:
        return {"kind": "file-pins-only", "source_contract_verified": False,
                "native_reference_files_replay_verified": False}
    if type(evidence) is not dict:
        raise ValueError("explicit diagnostic source evidence required")
    kind = evidence.get("kind")
    if kind == "rove-profile-build-v1" and set(evidence) == {"kind", "build"}:
        if artifact.family not in "ABCEF":
            raise ValueError("Rove build evidence is for Rove candidates only")
        report_path = _pinned_file(evidence["build"])
        manifest, _ = run.json_input(report_path, evidence["build"]["sha256"])
        admitted = _profile_verifier().admit_c_build(manifest, report_path.parent)
        expected = admitted.expected
        if ((admitted.family, admitted.profile_id, admitted.representation, admitted.full) !=
                (artifact.family, artifact.profile, artifact.representation, True) or
                (admitted.resources["workers"], admitted.resources["tt_bytes"], admitted.resources["tt_entry_bytes"]) !=
                (artifact.workers, artifact.tt_bytes, artifact.entry_bytes) or
                (whole, source, native) != tuple(report_path.parent / x for x in
                                                (admitted.program, admitted.source, admitted.native)) or
                any(expected[prefix + "_sha256"] != digest for prefix, digest in
                    (("source", registry.file_sha(source)), ("native", artifact.native_sha256), ("whole", artifact.sha256)))):
            raise ValueError("Rove source admission differs from diagnostic candidate")
        return {"kind": kind, "receipt_sha256": evidence["build"]["sha256"],
                "source_contract_verified": True, "native_reference_files_replay_verified": True}
    if kind == "peer-reference-v1" and set(evidence) == {"kind", "build", "reference"}:
        if artifact.family not in ("ice4", "c4ke"):
            raise ValueError("peer evidence is for pinned comparison peers only")
        try:
            from . import peer_runtime
        except ImportError:
            import peer_runtime
        build_path, reference_path = _pinned_file(evidence["build"]), _pinned_file(evidence["reference"])
        reference, _ = peer_runtime.read_record(reference_path, evidence["reference"]["sha256"])
        if (reference.get("format") != "rove4k-peer-reference-v1" or reference.get("complete") is not True or
                reference.get("engines_executed") != 0 or reference.get("entry_size_compile_assertion") is not True or
                reference.get("build") != {"path": str(build_path), "sha256": evidence["build"]["sha256"]}):
            raise ValueError("peer reference does not bind the pinned build")
        peers = peer_runtime.sibling("peers")
        fixed = [reference_path.parent / "main.cpp", build_path.parent / "peer-producer.py"]
        fixed.extend(reference_path.parent / "source-closure" / relative for relative in
                     peer_runtime.SOURCE_FILES + peer_runtime.LEAGUE_SOURCE_FILES)
        for index in (1, 2):
            attempt = build_path.parent / ("attempt-" + str(index))
            fixed.extend(attempt / item for item in ("main.cpp", "resource-proof.json", peers.peer_spec(artifact.family).tiny_name))
            fixed.extend(attempt / "source" / relative for relative in peers.SOURCE_BLOBS[artifact.family])
        fixed.extend(reference_path.parent / ("reference-" + str(index)) for index in (1, 2, 3))
        for path in fixed:
            _safe_input_path(path)
        peer_runtime._verify_frozen(reference_path.parent / "source-closure", reference["source_inputs"], league_required=True)
        admitted = peer_runtime.validate_build(build_path, evidence["build"]["sha256"])
        if (admitted["peer"] != artifact.family or admitted["layout"] != reference["resources"] or
                reference["resources"]["id"] != artifact.profile or reference["resources"]["workers"] != artifact.workers or
                reference["resources"]["tt_bytes"] != artifact.tt_bytes or artifact.entry_bytes != 8 or
                whole.read_bytes() != admitted["whole"] or source.read_bytes() != admitted["source"] or
                peer_runtime.bound(reference_path.parent / "main.cpp", reference["source"]) != admitted["source"] or
                reference["source"]["sha256"] != registry.file_sha(source) or
                reference["native"]["path"] != str(reference_path.parent / "reference-1") or
                native != reference_path.parent / "reference-1"):
            raise ValueError("peer source admission differs from diagnostic candidate")
        raw_native = peer_runtime.bound(native, reference["native"])
        attempts = reference.get("native_attempts")
        if type(attempts) is not list or len(attempts) != 3:
            raise ValueError("three pinned peer native reference attempts are required")
        for index, attempt in enumerate(attempts, 1):
            expected_path = reference_path.parent / ("reference-" + str(index))
            if attempt.get("path") != str(expected_path) or peer_runtime.bound(expected_path, attempt) != raw_native:
                raise ValueError("peer native reference reproduction differs")
        elf = peer_runtime.Elf64(raw_native)
        if (reference["tt_symbol"] != admitted["tt_symbol"] or elf.dependencies() != reference["dependencies"] or
                elf.pointer_symbol(reference["tt_symbol"]) != reference["tt_symbol_value"]):
            raise ValueError("peer reference native metadata differs")
        return {"kind": kind, "build_sha256": evidence["build"]["sha256"],
                "reference_sha256": evidence["reference"]["sha256"],
                "source_contract_verified": True, "native_reference_files_replay_verified": True}
    raise ValueError("unknown or mismatched diagnostic source evidence")


def read_candidates(path, expected_sha256, profile, *, allow_single=False):
    """Check pinned candidates without granting score or runtime admission.

    Cohort preparation requires at least two candidates by default. A caller
    running exactly one functional diagnostic may explicitly allow a single
    candidate; every source, whole, native and profile check remains the same.
    """
    if type(allow_single) is not bool:
        raise ValueError("allow_single must be an explicit boolean")
    if not isinstance(expected_sha256, str) or not run.SHA.fullmatch(expected_sha256):
        raise ValueError("an independently supplied candidate registry digest is required")
    value, digest = run.json_input(_safe_input_path(path), expected_sha256)
    if (type(value) is not dict or set(value) != {"format", "profile", "candidates"} or
            value["format"] != "rove4k-diagnostic-candidate-set-v1" or value["profile"] != profile or
            profile not in ("test-p16", "test-p192") or type(value["candidates"]) is not list or
            not (1 if allow_single else 2) <= len(value["candidates"]) <= 32):
        raise ValueError("named diagnostic candidate set and TEST profile required")
    candidates, ids = [], set()
    for row in value["candidates"]:
        if type(row) is not dict or set(row) != {"artifact", "source", "native", "evidence"} or type(row["artifact"]) is not dict:
            raise ValueError("diagnostic candidate requires artifact, source, native and evidence pins")
        artifact = registry.Artifact.from_record(row["artifact"])
        if (artifact.profile != profile or artifact.purpose != "test" or not artifact.full or
                artifact.family not in ("A", "B", "C", "E", "F", "ice4", "c4ke") or
                artifact.representation not in ("source-jit", "packed-native") or artifact.id in ids):
            raise ValueError("distinct full non-D general 4K TEST candidates are required")
        # The approved P192 experiment specifies 192 GiB for each engine.
        # A legacy 8-byte peer layout rounds down to 128 GiB: it remains a
        # valid legacy artifact but must not enter this diagnostic cohort.
        if profile == "test-p192" and artifact.tt_bytes != 192 << 30:
            raise ValueError("P192 diagnostics require 192 GiB TT per engine")
        whole = _pinned_file({"path": str(artifact.path), "sha256": artifact.sha256,
                              "bytes": artifact.whole_bytes}, expected=artifact.sha256)
        source = _pinned_file(row["source"])
        native = _pinned_file(row["native"], expected=artifact.native_sha256)
        source_evidence = _source_evidence(row["evidence"], artifact, whole, source, native)
        ids.add(artifact.id)
        candidates.append({"artifact": artifact, "whole": whole, "source": dict(row["source"]),
                           "native": dict(row["native"]), "evidence": source_evidence})
    candidates.sort(key=lambda row: row["artifact"].id)
    return candidates, digest


def build_inputs(*, candidate_path, candidate_sha256, profile, bank_path, bank_sha256,
                 runner_binary, runner_receipt, output_root, stage=None, snapshot=None,
                 target_cgroup=None, wall_seconds=180):
    """Bind a full probe cohort to exact files, opening bank and observed slots."""
    output_root = _safe_output_path(output_root)
    if type(wall_seconds) not in (int, float) or not 0 < wall_seconds <= 180:
        raise ValueError("bounded pre-GO deadline required")
    if profile not in ("test-p16", "test-p192"):
        raise ValueError("P16 or P192 diagnostic profile required")
    if not isinstance(bank_sha256, str) or not run.SHA.fullmatch(bank_sha256):
        raise ValueError("an independently supplied opening bank digest is required")
    stage = stage or ("broad" if profile == "test-p16" else "high")
    if not run.stage_profile_allowed(stage, profile):
        raise ValueError("diagnostic stage and profile differ")
    rows, input_sha = read_candidates(candidate_path, candidate_sha256, profile)
    runner_binary, runner_receipt = _safe_input_path(runner_binary), _safe_input_path(runner_receipt)
    bank_path = _safe_input_path(bank_path)
    runner = run.runner_identity(runner_binary, runner_receipt)
    # Validate the path before the existing bank validator reads the PGN.
    bank_preview, _ = run.json_input(bank_path, bank_sha256)
    _safe_input_path(bank_preview["files"][stage]["path"])
    bank, actual_bank_sha, openings, opening_path = run.validate_bank(bank_path, bank_sha256, stage)
    opening_path = _safe_input_path(opening_path)
    if snapshot is not None and target_cgroup is not None:
        raise ValueError("choose one explicit topology source")
    if target_cgroup is not None:
        if (type(target_cgroup) is not dict or set(target_cgroup) != {"path", "device", "inode"} or
                type(target_cgroup["device"]) is not int or target_cgroup["device"] < 0 or
                type(target_cgroup["inode"]) is not int or target_cgroup["inode"] <= 0):
            raise ValueError("original target cgroup path, device and inode are required together")
        path = _safe_input_path(target_cgroup["path"])
        snapshot = topology.Topology.snapshot_target(path, device=target_cgroup["device"], inode=target_cgroup["inode"])
    elif snapshot is None:
        snapshot = topology.Topology.snapshot()
    slots, controller_cpus = run.league_placement(snapshot, profile)
    pairs = list(itertools.combinations(rows, 2))
    if len(slots) != (11 if profile == "test-p16" else 1) or not pairs:
        raise ValueError("complete diagnostic slot cohort required")
    entries, artifacts = [], {}
    for index, slot in enumerate(slots):
        chosen = list(pairs[index % len(pairs)])
        if (index // len(pairs)) % 2:
            chosen.reverse()
        if slot.id in artifacts:
            raise ValueError("duplicate diagnostic slot")
        engines = []
        for row in chosen:
            artifact = row["artifact"]
            engines.append({"id": artifact.id, "path": str(row["whole"]), "whole_sha256": artifact.sha256,
                            "native_sha256": artifact.native_sha256, "tt_bytes": artifact.tt_bytes})
        entries.append({"slot": slot.to_record(), "engines": engines,
                        "opening_start": index % len(openings) + 1,
                        "out": str(output_root / "jobs" / slot.id)})
        artifacts[slot.id] = [{key: engine[key] for key in ("id", "whole_sha256", "native_sha256", "tt_bytes")}
                              for engine in engines]
    manifest = {"format": "rove4k-pre-go-controller-v2", "profile": profile, "entries": entries,
                "runner": str(Path(runner_binary)), "runner_sha256": runner["sha256"],
                "opening": str(opening_path), "opening_sha256": bank["files"][stage]["sha256"],
                "topology": snapshot.to_record(), "saved_ancestor_cpus": list(snapshot.allowed_cpus),
                "wall_seconds": wall_seconds}
    lock = {"format": "rove4k-diagnostic-candidate-lock-v1", "candidate_set_sha256": input_sha,
            "profile": profile, "stage": stage, "bank_sha256": actual_bank_sha,
            "runner": runner, "controller_cpus": controller_cpus,
            "target_topology_cgroup": target_cgroup,
            "candidates": [{"artifact": row["artifact"].identity(), "source": row["source"],
                            "native": row["native"], "evidence": row["evidence"]} for row in rows],
            "source_to_native_provenance_verified": False, "runtime_native_observed": False,
            "size_or_rules_qualified": False,
            "runtime_admission": False, "scored_qualification": False}
    lock["manifest_sha256"] = hashlib.sha256(ledger.canonical(manifest)).hexdigest()
    lock["artifacts_sha256"] = hashlib.sha256(ledger.canonical(artifacts)).hexdigest()
    return {"manifest": manifest, "artifacts": artifacts, "lock": lock,
            "runtime_admission": False, "scored_qualification": False}


def write_inputs(**kwargs):
    data = build_inputs(**kwargs)
    root = Path(kwargs["output_root"])
    root.mkdir(parents=True, exist_ok=False)
    outputs = {}
    for key, name in (("manifest", "manifest.json"), ("artifacts", "artifacts.json"), ("lock", "candidate-lock.json")):
        raw = ledger.canonical(data[key])
        target = root / name
        with target.open("xb") as file:
            file.write(raw)
        outputs[key + "_path"] = str(target)
        outputs[key + "_sha256"] = hashlib.sha256(raw).hexdigest()
    return {**outputs, "runtime_admission": False, "scored_qualification": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--candidates-sha256", required=True)
    parser.add_argument("--profile", required=True, choices=("test-p16", "test-p192"))
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--bank-sha256", required=True)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--runner-receipt", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--target-cgroup", type=Path)
    parser.add_argument("--target-device", type=int)
    parser.add_argument("--target-inode", type=int)
    parser.add_argument("--wall-seconds", type=float, default=180)
    args = parser.parse_args(argv)
    target_fields = (args.target_cgroup, args.target_device, args.target_inode)
    if any(value is not None for value in target_fields) and any(value is None for value in target_fields):
        parser.error("--target-cgroup, --target-device and --target-inode are required together")
    target = None if args.target_cgroup is None else {"path": str(args.target_cgroup),
                                                      "device": args.target_device, "inode": args.target_inode}
    print(json.dumps(write_inputs(candidate_path=args.candidates, candidate_sha256=args.candidates_sha256,
          profile=args.profile, bank_path=args.bank, bank_sha256=args.bank_sha256, runner_binary=args.runner,
          runner_receipt=args.runner_receipt, output_root=args.out, target_cgroup=target, wall_seconds=args.wall_seconds),
          sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
