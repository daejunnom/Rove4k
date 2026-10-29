#!/usr/bin/env python3
"""Produce the experimental exact-192-GiB peer variant without running it.

Inputs and outputs are external to Git.  This producer validates the pinned
upstream closure and the complete inverse transform on each independent
attempt, then runs the upstream TCEC minifier and packages its output.  The
result is an experimental changed-index algorithm, not an official peer or
an admitted league player.  Input-transform and byte-reproduction evidence
does not prove that emitted code allocates or uses the claimed TT; native
source semantics, actual 192-GiB execution, and playing strength are separate.
"""
from __future__ import annotations

import argparse
import json
import lzma
import os
from functools import partial
from pathlib import Path
import re
import signal
import stat
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from . import peer_exact_runner as runner, peer_p192_exact as exact, peers
except ImportError:
    import peer_exact_runner as runner
    import peer_p192_exact as exact
    import peers


_BLOCKED = frozenset((".ssh", ".aws", ".npmrc", "node_modules", "dist", "dist-server", "build",
                      "coverage", "models", "checkpoints", ".cache", "package-lock.json",
                      "id_rsa", "id_ed25519", "id_dsa", "id_ecdsa", "inventory.json"))
_LICENSE_DISTRIBUTION = {
    "ice4": ["When conveying modified versions, retain the required notices and license and identify changes.",
             "Convey modified works under GPL-3.0; object-code conveyance requires corresponding source under its permitted terms."],
    "c4ke": ["When distributing copies or substantial portions, include the copyright and permission notices."],
}


def _emitted_clues(source):
    """Report narrow literal clues only; never infer TT execution semantics."""
    compact = re.sub(rb"\s+", b"", source.lower())
    allocation = re.findall(rb"calloc\((?:3(?:ull|ul|ll|l)?<<33|25769803776(?:ull|ul|ll|l)?),8\)", compact)
    index = re.findall(rb">>16\)\*3\)>>15", compact)
    return {"explicit_192gib_calloc_literals": len(allocation),
            "explicit_upper48_index_suffixes": len(index),
            "scope": "literal clues only; renamed, folded, or dead expressions are not resolved"}


def _safe_parts(path):
    for part in path.parts:
        lower = part.lower()
        if (lower.startswith(".env") or lower in _BLOCKED or lower == "token" or
                lower.endswith(("-token", "_token")) or lower.startswith("token.") or
                any(term in lower for term in ("credential", "service-account", "service_account",
                                                "api-key", "api_key", "ssh-key", "ssh_key", "private-key",
                                                "private_key", "password"))):
            raise ValueError("protected path is not a peer source input")


def _source_snapshot(name, source, *, pinned=True):
    """Read only pinned source members through non-symlink directory FDs."""
    source = Path(source)
    if sys.platform != "linux" or not source.is_absolute() or ".." in source.parts:
        raise ValueError("Linux and an absolute peer source directory are required")
    _safe_parts(source)
    if any((parent / ".git").exists() for parent in (source, *source.parents)):
        raise ValueError("pinned peer source must stay outside any Git checkout")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open("/", flags)
    try:
        for part in source.parts[1:]:
            child = os.open(part, flags, dir_fd=root)
            os.close(root)
            root = child
        result = {}
        for relative in sorted(peers.SOURCE_BLOBS[name]):
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("unsafe pinned peer source member")
            _safe_parts(path)
            current = os.dup(root)
            try:
                for part in path.parts[:-1]:
                    child = os.open(part, flags, dir_fd=current)
                    os.close(current)
                    current = child
                fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current)
                try:
                    info = os.fstat(fd)
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > peers.MiB:
                        raise ValueError("peer source member is not a bounded regular file")
                    with os.fdopen(fd, "rb", closefd=False) as stream:
                        data = stream.read(peers.MiB + 1)
                    if len(data) != info.st_size or len(data) > peers.MiB:
                        raise ValueError("peer source member changed or exceeded its size bound")
                    if pinned:
                        peers.verify_blob(name, relative, data)
                    result[relative] = data
                finally:
                    os.close(fd)
            finally:
                os.close(current)
        return result
    finally:
        os.close(root)


def _read_proof(path):
    """Read the retained proof through non-symlink directories and file."""
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("absolute retained proof required")
    _safe_parts(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open("/", flags)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, flags, dir_fd=root)
            os.close(root)
            root = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=root)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > peers.MiB:
                raise ValueError("retained transform proof is not a bounded regular file")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(peers.MiB + 1)
            if len(data) != info.st_size or len(data) > peers.MiB:
                raise ValueError("retained transform proof changed or exceeded its size bound")
            return data
        finally:
            os.close(fd)
    finally:
        os.close(root)


def _write_new(path, data):
    """Create a new output without traversing or overwriting a symlink."""
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or type(data) is not bytes:
        raise ValueError("absolute owned output and immutable bytes required")
    _safe_parts(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open("/", flags)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, flags, dir_fd=root)
            os.close(root)
            root = child
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
    finally:
        os.close(root)


def _mkdir_new(path):
    """Create exactly one new directory under non-symlink parents."""
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("absolute owned directory required")
    _safe_parts(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open("/", flags)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, flags, dir_fd=root)
            os.close(root)
            root = child
        os.mkdir(path.name, mode=0o700, dir_fd=root)
    finally:
        os.close(root)


def build(name, source, out, *, run=runner.run, codec_search="compact", variant="baseline",
          launcher_variant="upstream"):
    """Build two independent exact-profile snapshots and compare whole bytes.

    ``run`` accepts the structured command, source cwd, and private home. It
    permits a simulated producer in tests but does not change receipt claims.
    The default bounded runner does not inherit credentials or write logs.
    No engine program is executed by this function.
    """
    peer = peers.peer_spec(name)
    if codec_search not in peers.CODEC_SEARCHES:
        raise ValueError("unknown bounded peer codec search")
    c4ke_variants = ("share-v1", "slot-v1", "ray-v1", "slot-ray-v1", "castle-or-v1", "ray-castle-or-v1",
                     "edit-loop-v1", "edit-castle-or-v1", "edit-castle-alloc24-v1",
                     "edit-castle-slider-v1", "edit-castle-startpos-v1", "edit-castle-quiet-v1",
                     "edit-castle-emission-v1", "edit-castle-phalanx-v1",
                     "edit-castle-phalanx-attack-pawns-v1", "edit-castle-phalanx-ep-hash-v1", "edit-castle-phalanx-pop-lsb-v1")
    ice_variants = ("castle-v1", "zobrist-v1", "castle-zobrist-v1")
    if not (variant == "baseline" or (name == "c4ke" and variant in c4ke_variants) or
            (name == "ice4" and variant in ice_variants)):
        raise ValueError("unsupported peer source variant")
    if launcher_variant not in ("upstream", "gnu-tail-v1"):
        raise ValueError("unsupported launcher variant")
    original = _source_snapshot(name, source)
    source = Path(source)
    if out is None or not Path(out).is_absolute() or ".." in Path(out).parts:
        raise ValueError("new absolute external output directory required")
    _safe_parts(Path(out))
    out = peers.external_new(out)
    _safe_parts(out)
    if out == source or out.is_relative_to(source) or source.is_relative_to(out):
        raise ValueError("output and pinned peer source must be separate directories")
    _mkdir_new(out)
    own = Path(__file__).resolve(strict=True).read_bytes()
    tool_paths = {"producer": own, "transform": Path(exact.__file__).resolve(strict=True).read_bytes(),
                  "peer_base": Path(peers.__file__).resolve(strict=True).read_bytes(),
                  "command_runner": Path(runner.__file__).resolve(strict=True).read_bytes()}
    if variant in ice_variants:
        try:
            from . import peer_ice_structural as ice
        except ImportError:
            import peer_ice_structural as ice
        tool_paths["ice_structural_transform"] = Path(ice.__file__).resolve(strict=True).read_bytes()
    if variant in ("castle-or-v1", "ray-castle-or-v1", "edit-castle-or-v1", "edit-castle-alloc24-v1",
                   "edit-castle-slider-v1", "edit-castle-startpos-v1", "edit-castle-quiet-v1",
                   "edit-castle-emission-v1", "edit-castle-phalanx-v1",
                   "edit-castle-phalanx-attack-pawns-v1", "edit-castle-phalanx-ep-hash-v1", "edit-castle-phalanx-pop-lsb-v1"):
        try:
            from . import peer_c4ke_structural as c4ke
        except ImportError:
            import peer_c4ke_structural as c4ke
        tool_paths["c4ke_structural_transform"] = Path(c4ke.__file__).resolve(strict=True).read_bytes()
    if variant in ("edit-loop-v1", "edit-castle-or-v1", "edit-castle-alloc24-v1",
                   "edit-castle-slider-v1", "edit-castle-startpos-v1", "edit-castle-quiet-v1",
                   "edit-castle-emission-v1", "edit-castle-phalanx-v1",
                   "edit-castle-phalanx-attack-pawns-v1", "edit-castle-phalanx-ep-hash-v1", "edit-castle-phalanx-pop-lsb-v1"):
        try:
            from . import peer_c4ke_edit_structural as edit
        except ImportError:
            import peer_c4ke_edit_structural as edit
        tool_paths["c4ke_edit_structural_transform"] = Path(edit.__file__).resolve(strict=True).read_bytes()
    if variant in ("edit-castle-slider-v1", "edit-castle-startpos-v1"):
        try:
            from . import peer_c4ke_slider_loop as slider, peer_c4ke_startpos_loop as startpos
        except ImportError:
            import peer_c4ke_slider_loop as slider
            import peer_c4ke_startpos_loop as startpos
        module = slider if variant == "edit-castle-slider-v1" else startpos
        tool_paths["c4ke_loop_transform"] = Path(module.__file__).resolve(strict=True).read_bytes()
    if variant == "edit-castle-quiet-v1":
        try:
            from . import peer_c4ke_quiet_history as quiet
        except ImportError:
            import peer_c4ke_quiet_history as quiet
        tool_paths["c4ke_quiet_transform"] = Path(quiet.__file__).resolve(strict=True).read_bytes()
    if variant in ("edit-castle-emission-v1", "edit-castle-phalanx-v1",
                   "edit-castle-phalanx-attack-pawns-v1", "edit-castle-phalanx-ep-hash-v1", "edit-castle-phalanx-pop-lsb-v1"):
        try:
            from . import peer_c4ke_move_emission as emission, peer_c4ke_phalanx as phalanx
        except ImportError:
            import peer_c4ke_move_emission as emission
            import peer_c4ke_phalanx as phalanx
        module = emission if variant == "edit-castle-emission-v1" else phalanx
        tool_paths["c4ke_candidate_transform"] = Path(module.__file__).resolve(strict=True).read_bytes()
    if variant in ("edit-castle-phalanx-attack-pawns-v1", "edit-castle-phalanx-ep-hash-v1", "edit-castle-phalanx-pop-lsb-v1"):
        try:
            from . import peer_c4ke_attack_pawns as attack, peer_c4ke_ep_hash as ep, peer_c4ke_pop_lsb as pop
        except ImportError:
            import peer_c4ke_attack_pawns as attack
            import peer_c4ke_ep_hash as ep
            import peer_c4ke_pop_lsb as pop
        module = {"edit-castle-phalanx-attack-pawns-v1": attack,
                  "edit-castle-phalanx-ep-hash-v1": ep,
                  "edit-castle-phalanx-pop-lsb-v1": pop}[variant]
        tool_paths["c4ke_extra_transform"] = Path(module.__file__).resolve(strict=True).read_bytes()
    if launcher_variant == "gnu-tail-v1":
        try:
            from . import peer_launcher_trim as trim
        except ImportError:
            import peer_launcher_trim as trim
        tool_paths["launcher_transform"] = Path(trim.__file__).resolve(strict=True).read_bytes()
        launcher, launcher_proof = trim.transform_launcher(name, original["launcher.sh"])
        if trim.restore_launcher(name, launcher, launcher_proof) != original["launcher.sh"]:
            raise ValueError("launcher inverse differs")
    else:
        launcher, launcher_proof = original["launcher.sh"], None
    for key, value in tool_paths.items():
        _write_new(out / (key + ".py"), value)
    tools = {key: {"bytes": len(value), "sha256": peers.sha(value)} for key, value in tool_paths.items()}
    record = {
        "format": "rove4k-peer-p192-exact-producer-v1", "profile": exact.PROFILE,
        "artifact_kind": "experimental-p192-exact", "peer": name, "family": name,
        "version": peer.version, "repository": peer.repository, "revision": peer.revision,
        "source_url": peer.source_url,
        "license": {"spdx": peer.license, "source_url": peer.raw_url("LICENSE"),
                    "git_blob": peers.git_blob(original["LICENSE"]),
                    "sha256": peers.sha(original["LICENSE"]),
                    "distribution_conditions_summary": _LICENSE_DISTRIBUTION[name],
                    "scope": "brief distribution summary; the pinned upstream license text controls"},
        "resources": {"workers": exact.WORKERS, "entry_bytes": 8,
                      "tt_entries": exact.ENTRIES, "tt_bytes": exact.TT_BYTES,
                      "index": "upper48-times3-shift15"},
        "algorithm_changed": True, "producer_inputs": tools,
        "upstream_blob_manifest_sha256": peers.sha(peers.canonical(peers.SOURCE_BLOBS[name])),
        "codec_search": {"name": codec_search, "nice_lengths": peers.CODEC_SEARCHES[codec_search]},
        "attempts": [], "complete": False, "reproducible": False,
        "qualification": {"emitted_tt_semantics_verified": False, "runtime_qualified": False,
                          "league_qualified": False},
        "candidate_status": "not-admitted; emitted TT semantics and runtime remain unverified",
        "executing_code_identity_verified": False,
        "scope": "experimental source and package reproduction; no engine execution or score admission",
    }
    if variant != "baseline":
        record["source_variant"] = variant
    if codec_search in peers.LITERAL_SEARCH_LC:
        record["codec_search"]["literal_contexts"] = peers.LITERAL_SEARCH_LC[codec_search]
    if launcher_variant != "upstream":
        record["launcher_variant"] = launcher_variant
        record["launcher_transform"] = launcher_proof
    try:
        closure = exact.source_closure(name, variant=variant)
        selected_original = {path: original[path] for path in closure}
        for number in (1, 2):
            # Re-check all source identities before each snapshot.  Source is
            # untrusted input and can change after initial collection.
            current = _source_snapshot(name, source)
            if current != original:
                raise ValueError("pinned upstream source changed between attempts")
            transformed, proof = exact.transform(name, selected_original, variant=variant)
            if exact.restore(name, transformed, proof, variant=variant) != selected_original:
                raise ValueError("exact transform did not fully restore pinned upstream")
            attempt = out / ("attempt-" + str(number))
            snapshot = attempt / "source"
            _mkdir_new(attempt)
            _mkdir_new(snapshot)
            sandbox_home = attempt / "home"
            _mkdir_new(sandbox_home)
            directories = set()
            for relative in original:
                parent = Path(relative).parent
                while parent != Path("."):
                    directories.add(parent)
                    parent = parent.parent
            for directory in sorted(directories, key=lambda path: (len(path.parts), str(path))):
                _mkdir_new(snapshot / directory)
            for relative, data in original.items():
                path = snapshot / relative
                _write_new(path, transformed.get(relative, data))
            proof_bytes = json.dumps(proof, sort_keys=True, indent=2, ensure_ascii=False).encode() + b"\n"
            _write_new(attempt / "transform-proof.json", proof_bytes)
            proof_sha = peers.sha(proof_bytes)
            proof_bytes = _read_proof(attempt / "transform-proof.json")
            if peers.sha(proof_bytes) != proof_sha:
                raise ValueError("retained transform proof differs before minifier")
            compile_commands, emit_command = peers.minifier_commands(name, snapshot, attempt)
            version, version_errors, version_record = run([compile_commands[0][0], "--version"], snapshot,
                                                           sandbox_home=sandbox_home)
            _write_new(attempt / "compiler.version", version)
            _write_new(attempt / "compiler-version.stderr", version_errors)
            commands = [version_record]
            for index, command in enumerate(compile_commands):
                stdout, stderr, command_record = run(command, snapshot, sandbox_home=sandbox_home)
                commands.append(command_record)
                _write_new(attempt / ("compile-" + str(index) + ".stdout"), stdout)
                _write_new(attempt / ("compile-" + str(index) + ".stderr"), stderr)
            minified, stderr, command_record = run(emit_command, snapshot, sandbox_home=sandbox_home)
            commands.append(command_record)
            if not isinstance(minified, bytes) or not minified.startswith(b"#include") or len(minified) > peers.MiB:
                raise ValueError("minifier did not emit a bounded source stream")
            _write_new(attempt / "main.cpp", minified)
            _write_new(attempt / "minifier.stderr", stderr)
            actual_snapshot = _source_snapshot(name, snapshot, pinned=False)
            changed_after = {}
            for relative, data in original.items():
                expected = transformed.get(relative, data)
                if actual_snapshot[relative] != expected:
                    raise ValueError("minifier modified a protected peer input: " + relative)
                if relative in transformed:
                    changed_after[relative] = expected
            if exact.restore(name, changed_after, proof, variant=variant) != selected_original:
                raise ValueError("post-minifier exact transform inverse differs")
            if _read_proof(attempt / "transform-proof.json") != proof_bytes:
                raise ValueError("minifier modified the retained transform proof")
            grid = peers.codec_grid(minified, search=codec_search)
            selected = grid[0]
            if lzma.decompress(selected["payload"], format=lzma.FORMAT_ALONE) != minified:
                raise ValueError("selected compressed stream differs from emitted source")
            if launcher_proof is not None and trim.restore_launcher(name, launcher, launcher_proof) != original["launcher.sh"]:
                raise ValueError("launcher inverse changed during production")
            whole = launcher + selected["payload"]
            target = attempt / peer.tiny_name
            _write_new(target, whole)
            row = {"source": {"bytes": len(minified), "sha256": peers.sha(minified)},
                   "whole": {"path": str(target), "bytes": len(whole), "sha256": peers.sha(whole)},
                   "header": {"bytes": len(launcher), "sha256": peers.sha(launcher)},
                   "transform_proof_sha256": proof_sha, "source_inverse_verified": True,
                   "selected_codec": {key: value for key, value in selected.items() if key != "payload"},
                   "codec_trials": len(grid), "compiler_version_sha256": peers.sha(version),
                   "emitted_literal_clues": _emitted_clues(minified),
                   "commands": commands}
            record["attempts"].append(row)
        first, second = record["attempts"]
        for number, row in enumerate(record["attempts"], 1):
            base = out / ("attempt-" + str(number))
            if (peers.sha(_read_proof(base / "transform-proof.json")) != row["transform_proof_sha256"] or
                    peers.sha(_read_proof(base / "main.cpp")) != row["source"]["sha256"] or
                    peers.sha(_read_proof(Path(row["whole"]["path"]))) != row["whole"]["sha256"]):
                raise ValueError("retained attempt evidence changed after minifier")
            retained = _source_snapshot(name, base / "source", pinned=False)
            if any(retained[path] != transformed.get(path, data) for path, data in original.items()):
                raise ValueError("retained attempt input changed after minifier")
            if exact.restore(name, {path: retained[path] for path in transformed}, proof, variant=variant) != selected_original:
                raise ValueError("retained attempt inverse differs")
        for key, value in tool_paths.items():
            if _read_proof(out / (key + ".py")) != value:
                raise ValueError("retained producer source snapshot changed after minifier")
        if (_read_proof(out / "attempt-1" / "main.cpp") != _read_proof(out / "attempt-2" / "main.cpp") or
                _read_proof(Path(first["whole"]["path"])) != _read_proof(Path(second["whole"]["path"])) or
                first["source"] != second["source"] or first["whole"]["bytes"] != second["whole"]["bytes"] or
                first["whole"]["sha256"] != second["whole"]["sha256"] or
                first["transform_proof_sha256"] != second["transform_proof_sha256"] or
                first["compiler_version_sha256"] != second["compiler_version_sha256"]):
            raise ValueError("independent peer output or transform reproduction differs")
        record.update(complete=True, reproducible=True, whole=first["whole"])
        record["qualification"].update(size_within_4096=first["whole"]["bytes"] <= 4096,
                                       input_transform_inverse_verified=True)
    except BaseException as error:
        record["failure"] = {"type": type(error).__name__, "message": str(error)}
        if isinstance(error, runner.BuildCommandFailure):
            record["failure"]["command"] = error.record
        raise
    finally:
        record_bytes = json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False).encode() + b"\n"
        _write_new(out / "peer-exact.json", record_bytes)
        digest = peers.sha(record_bytes)
    return {"path": str(out / "peer-exact.json"), "sha256": digest, "record": record}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--peer", choices=("ice4", "c4ke"), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--codec-search", choices=tuple(peers.CODEC_SEARCHES), default="compact")
    parser.add_argument("--source-variant", choices=("baseline", "share-v1", "slot-v1", "ray-v1", "slot-ray-v1",
                                                     "castle-or-v1", "ray-castle-or-v1", "edit-loop-v1", "edit-castle-or-v1", "edit-castle-alloc24-v1",
                                                     "edit-castle-slider-v1", "edit-castle-startpos-v1", "edit-castle-quiet-v1",
                                                     "edit-castle-emission-v1", "edit-castle-phalanx-v1",
                                                     "edit-castle-phalanx-attack-pawns-v1", "edit-castle-phalanx-ep-hash-v1", "edit-castle-phalanx-pop-lsb-v1",
                                                     "castle-v1", "zobrist-v1", "castle-zobrist-v1"), default="baseline")
    parser.add_argument("--launcher-variant", choices=("upstream", "gnu-tail-v1"), default="upstream")
    parser.add_argument("--cpu", type=int, default=None)
    parser.add_argument("--rustup-home", type=Path, default=None,
                        help="absolute existing Rustup toolchain directory for the ice4 minifier")
    parser.add_argument("--wall-seconds", type=int, default=600)
    args = parser.parse_args()
    if args.wall_seconds <= 0:
        parser.error("positive wall bound required")
    available = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else []
    cpu = args.cpu if args.cpu is not None else (available[0] if available else None)
    if cpu is None or cpu < 0 or (available and cpu not in available):
        parser.error("an allowed CPU is required")
    result = build(args.peer, args.source, args.out,
                   run=partial(runner.run, cpu=cpu, timeout=args.wall_seconds, rustup_home=args.rustup_home),
                   codec_search=args.codec_search, variant=args.source_variant,
                   launcher_variant=args.launcher_variant)
    print(json.dumps({key: value for key, value in result.items() if key != "record"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    def _interrupted(signum, frame):
        raise KeyboardInterrupt("peer exact producer cancelled")
    signal.signal(signal.SIGTERM, _interrupted)
    sys.exit(main())
