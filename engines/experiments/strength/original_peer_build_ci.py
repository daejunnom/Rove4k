"""Create a bounded, non-authorizing JSON receipt for an original peer build.

Source and native files stay outside the checkout.  The receipt identifies
observed bytes; it is not CI provenance authentication or runtime admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from . import original_peer_build as original, peer_exact_runner as runner, peers
except ImportError:
    import original_peer_build as original
    import peer_exact_runner as runner
    import peers

_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){0,3}\Z")
_ANCHOR_SCOPE = ("runner-owned duplicates passed to the original child; "
                 "descendant FD survival and crash-safe settlement unproved")
_QUALIFICATION = {
    "source_blob_identity_checked": True, "compiler_authenticated": False,
    "source_to_native_proven": False, "tt_abi_verified": False,
    "allocation_observed": False, "runtime_qualified": False,
    "league_qualified": False, "scored_game_admitted": False,
}


def _digest(value, pattern):
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ValueError("invalid digest")
    return value


def _positive(value, maximum):
    if type(value) is not int or not 0 < value <= maximum:
        raise ValueError("invalid positive size")
    return value


def verify_intake(peer, source):
    """Recheck the pinned intake using no-follow reads for every component."""
    source = original._outside_checkout(source)
    root = runner._open_directory(source)
    try:
        raw = original._read_regular(root, "source.json", 1 << 20)
    finally:
        os.close(root)

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate intake field")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("non-finite intake value")

    manifest = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    if (type(manifest) is not dict or manifest.get("complete") is not True or
            manifest.get("peer") != peer or manifest.get("revision") != peers.peer_spec(peer).revision or
            type(manifest.get("inputs")) is not dict or
            set(manifest["inputs"]) != set(peers.SOURCE_BLOBS[peer])):
        raise ValueError("source intake incomplete")
    checked = {}
    for relative in sorted(peers.SOURCE_BLOBS[peer]):
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("invalid source member")
        member = original._protected_path(source / path)
        directory = runner._open_directory(member.parent)
        try:
            data = original._read_regular(directory, path.name, peers.MiB)
        finally:
            os.close(directory)
        peers.verify_blob(peer, relative, data)
        checked[relative] = {"bytes": len(data), "sha256": peers.sha(data), "git_blob": peers.git_blob(data)}
    if (peers.canonical(manifest["inputs"]) != peers.canonical(checked) or
            manifest.get("source_closure_sha256") != peers.sha(peers.canonical(checked))):
        raise ValueError("source intake does not match pinned files")
    return source


def receipt(record, *, peer, profile, repo, checkout_sha, event_sha,
            head_sha, event_name, workflow_ref, run_id, run_attempt, cpu, compiler_cli_version):
    """Allowlist result fields; never return raw paths, argv, logs, or bytes."""
    if (type(record) is not dict or peer not in ("ice4", "c4ke") or
            profile not in ("test-p16", "test-p192") or type(repo) is not str or
            _REPO.fullmatch(repo) is None or type(compiler_cli_version) is not str or
            _VERSION.fullmatch(compiler_cli_version) is None):
        raise ValueError("invalid build identity")
    _digest(checkout_sha, _HEX40)
    _digest(event_sha, _HEX40)
    if checkout_sha != event_sha:
        raise ValueError("checkout differs from event revision")
    if head_sha is not None:
        _digest(head_sha, _HEX40)
    if (event_name not in ("pull_request", "workflow_dispatch") or
            (event_name == "pull_request" and head_sha is None) or
            (event_name == "workflow_dispatch" and head_sha is not None) or
            type(workflow_ref) is not str or not 0 < len(workflow_ref) <= 512 or
            not workflow_ref.startswith(repo + "/.github/workflows/original-peer-build-trial.yml@") or
            any(ord(character) < 33 or ord(character) > 126 for character in workflow_ref)):
        raise ValueError("workflow event identity differs")
    _positive(run_id, (1 << 63) - 1)
    _positive(run_attempt, (1 << 31) - 1)
    if type(cpu) is not int or cpu < 0:
        raise ValueError("invalid selected CPU")
    if (record.get("format") != "rove4k-original-peer-build-v1" or
            record.get("purpose") != "test-only" or record.get("peer") != peer or
            record.get("profile") != profile or record.get("revision") != peers.peer_spec(peer).revision or
            record.get("complete") is not True or record.get("same_host_native_reproduced") is not True or
            record.get("source_modified_by_builder") is not False or
            record.get("concurrent_source_mutation_excluded") is not False or
            record.get("uci_setup_performed") is not False or
            type(record.get("engines_executed")) is not int or record["engines_executed"] != 0):
        raise ValueError("build record does not prove the bounded build scope")
    qualification = record.get("qualification")
    if type(qualification) is not dict or set(qualification) != set(_QUALIFICATION):
        raise ValueError("qualification differs")
    if any(qualification[key] is not expected for key, expected in _QUALIFICATION.items()):
        raise ValueError("qualification is not diagnostic only")
    requested = record.get("requested_uci")
    expected_uci = original._PROFILES[profile]
    if (type(requested) is not dict or set(requested) != set(expected_uci) or
            any(type(requested[key]) is not int or requested[key] != expected_uci[key]
                for key in expected_uci)):
        raise ValueError("requested UCI plan differs")

    source = record.get("source")
    if type(source) is not dict or set(source) != set(original.source_names(peer)):
        raise ValueError("original source closure differs")
    source_pins = {}
    for name in original.source_names(peer):
        item = source[name]
        if type(item) is not dict or set(item) != {"bytes", "sha256", "git_blob"}:
            raise ValueError("invalid source pin")
        size = _positive(item["bytes"], original.MAX_SOURCE_BYTES)
        sha = _digest(item["sha256"], _HEX64)
        blob = _digest(item["git_blob"], _HEX40)
        if blob != peers.SOURCE_BLOBS[peer][name]:
            raise ValueError("upstream blob pin differs")
        source_pins[name] = {"bytes": size, "sha256": sha, "git_blob": blob}
    closure = _digest(record.get("source_closure_sha256"), _HEX64)
    if closure != peers.sha(peers.canonical(source_pins)):
        raise ValueError("source closure digest differs")

    compiler = record.get("compiler")
    if (type(compiler) is not dict or compiler.get("flags") != list(original._FLAGS[peer]) or
            compiler.get("home_policy") != "/dev/null"):
        raise ValueError("compiler options differ")
    compiler_pin = {"bytes": _positive(compiler.get("bytes"), original.MAX_COMPILER_BYTES),
                    "sha256": _digest(compiler.get("sha256"), _HEX64),
                    "flags": list(original._FLAGS[peer]), "home_policy": "/dev/null",
                    "cli_version_unverified": compiler_cli_version}

    attempts = record.get("attempts")
    if type(attempts) is not list or len(attempts) != 2:
        raise ValueError("two build attempts required")
    summaries = []
    for index, item in enumerate(attempts, 1):
        if type(item) is not dict or item.get("name") != f"peer-native-{index}":
            raise ValueError("build attempt differs")
        command = item.get("command")
        if (type(command) is not dict or type(command.get("exit_code")) is not int or
                command["exit_code"] != 0 or command.get("leader_reaped") is not True or
                command.get("group_absent") is not True or
                command.get("forced_cleanup") is not False or command.get("anchor_home") != "/dev/null" or
                command.get("fd_anchor_scope") != _ANCHOR_SCOPE or
                command.get("original_group_empty_observed_before_reap") is not True or
                command.get("physical_group_settlement_proven") is not False):
            raise ValueError("owned command observation differs")
        summaries.append({"bytes": _positive(item.get("bytes"), original.MAX_NATIVE_BYTES),
                          "sha256": _digest(item.get("sha256"), _HEX64),
                          "exit_code": 0, "leader_reaped": True,
                          "group_absent_observed": True,
                          "physical_group_settlement_proven": False})
    if (summaries[0]["bytes"], summaries[0]["sha256"]) != (summaries[1]["bytes"], summaries[1]["sha256"]):
        raise ValueError("native outputs differ")
    return {
        "format": "rove4k-original-peer-build-ci-receipt-v1", "purpose": "build-only",
        "ci": {"repository": repo, "checkout_sha": checkout_sha, "event_sha": event_sha,
               "pull_request_head_sha": head_sha, "event_name": event_name, "workflow_ref": workflow_ref,
               "run_id": run_id, "run_attempt": run_attempt},
        "peer": peer, "profile_label": profile, "revision": record["revision"],
        "requested_uci_plan": dict(expected_uci), "uci_settings_observed": False,
        "source": source_pins, "source_closure_sha256": closure, "compiler": compiler_pin,
        "cpu": cpu, "native_attempts": summaries, "same_host_native_reproduced": True,
        "infrastructure_limits": {"source_bytes_per_file": original.MAX_SOURCE_BYTES,
                                  "native_bytes_per_file": original.MAX_NATIVE_BYTES,
                                  "compiler_bytes": original.MAX_COMPILER_BYTES,
                                  "compiler_wall_seconds_per_attempt": 600,
                                  "compiler_address_space_bytes_per_process": 2 << 30,
                                  "compiler_combined_output_bytes": 2 << 20,
                                  "tcec_size_limit_applied": False},
        "engines_executed": 0, "qualification": dict(_QUALIFICATION),
        "ci_origin_authenticated": False, "physical_group_settlement_proven": False,
        "scope": "identity and same-runner build only; no runtime or scored-game admission",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--peer", required=True, choices=("ice4", "c4ke"))
    parser.add_argument("--profile", required=True, choices=("test-p16", "test-p192"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--compiler-cli-version", required=True)
    args = parser.parse_args()
    if not hasattr(os, "sched_getaffinity"):
        raise ValueError("Linux affinity required")
    cpus = sorted(os.sched_getaffinity(0))
    if not cpus:
        raise ValueError("no allowed CPU")
    source = verify_intake(args.peer, args.source)
    built = original.build(args.peer, args.profile, source, args.out, cpu=cpus[0], timeout=600)
    result = receipt(built["record"], peer=args.peer, profile=args.profile,
                     repo=os.environ["GITHUB_REPOSITORY"], checkout_sha=os.environ["CHECKOUT_SHA"],
                     event_sha=os.environ["GITHUB_SHA"], head_sha=os.environ.get("PR_HEAD_SHA") or None,
                     event_name=os.environ["GITHUB_EVENT_NAME"], workflow_ref=os.environ["GITHUB_WORKFLOW_REF"],
                     run_id=int(os.environ["GITHUB_RUN_ID"]), run_attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]),
                     cpu=cpus[0], compiler_cli_version=args.compiler_cli_version)
    raw = peers.canonical(result) + b"\n"
    # A fresh caller-specified receipt outside the checkout is required.
    path = original._outside_checkout(args.receipt)
    parent = runner._open_directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        output = os.fdopen(fd, "wb")
        fd = None
        with output:
            output.write(raw)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)
    return 0


if __name__ == "__main__":
    # Source/compiler diagnostics may contain external source: do not print them.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:
        print("Original peer build-only verification failed.", file=sys.stderr)
        raise SystemExit(1)
