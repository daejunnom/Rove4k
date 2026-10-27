#!/usr/bin/env python3
"""Pinned external peer intake and resource-only tiny build preparation.

Only metadata, resource patches and this build consumer live in Rove4k.
Foreign source, licenses, compiled minifiers and engine artifacts stay outside
Git. Identity/size or build reproduction never implies runtime qualification.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import partial
import hashlib
import json
import lzma
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

TOOL_SOURCE = Path(__file__).read_bytes()

SOURCE_BLOBS = {
    "ice4": {
        "Cargo.lock": "cdef359f1ba47a25c8569bb19108b1448391e98d",
        "Cargo.toml": "2d81fdccee7b11ab1a16f4b8204ba18a2f1dcb20",
        "LICENSE": "f288702d2fa16d3cdf0035b15a9fcbc552cd88e7",
        "build.rs": "1a89a07a5415817aaca016acad90317e891a0cd7",
        "launcher.sh": "9ff12a9fb80c8604992ecd71ce9046146c7597ec",
        "minifier/constant_fold.rs": "f68fdefe105035f28a189af9e3f50f9663a2c3a1",
        "minifier/decl_merger.rs": "8fe1eb14b5a6f7455bc5776e2505df34302f6d01",
        "minifier/expr_merger.rs": "af36780cdedd9c52c9456ebb61a8421b39f966f9",
        "minifier/main.rs": "b6fa4719d0a696b3100ba19f33c8758c286d64df",
        "minifier/parse.rs": "6f75a3cf777411b3d6519f79890df5df7b30b5f5",
        "minifier/parse/ast.rs": "b880550e4c261adb59b201b686657277df8b39e7",
        "minifier/parse/cpp.lalrpop": "1728f0af858e1e89b5111b3fce7242d10450b412",
        "minifier/parse/extern_types": "36706e9761f7aaa55b357059faa7cb8f2f2e1959",
        "minifier/parse/keywords": "e659bb6624e587c0a2a76c2afedab9cf7e380199",
        "minifier/parse/lexical.rs": "a092aa703eba8d67ef59f584843768346b4c643c",
        "minifier/parse/tokenize.rs": "af4328de21c835d312ac5e8db4fed909c7524335",
        "minifier/preprocess.rs": "ef9b55a1a521aa1497005e1022140b1cdd407655",
        "minifier/renamer.rs": "f144df9399c29eb1ef4091f79e31b3b4b6f0b044",
        "minifier/semantic_analysis.rs": "cc749d0bef9353448a5d83713b5d2fd431b7a130",
        "src/board.cpp": "d9aa0f8e8a3d8717b21da8562e1ef9b06135746b",
        "src/consts.cpp": "5990b8fe1d487b6e5ed30411527d8b4431288fcb",
        "src/eval.cpp": "cc64039169df153eca37a9385dace0ddc5841db2",
        "src/everything.cpp": "368f9d474b24773ed27296b953d08f0d5cc438da",
        "src/main.cpp": "73170422d2a9d02213b528235698d4098be36bf9",
        "src/search.cpp": "3b33aecbacc0d1b2d2dbdb7b52fc721c8b81e440",
        "src/tables.cpp": "169ac0afe9531978df6b6eb4300d4644ba51003c",
        "src/uci.cpp": "3a44369317a8b00f49ed562e8779dea058bc451e",
        "trainer/Cargo.toml": "e41d6f263891bde65171c4c35295eba8187f1f0c",
        "trainer/src/features.rs": "7314417b5ab1fcbce54d7b2304997c2a1f57d0ce",
        "trainer/src/lib.rs": "8cdc9d96cb2db2b2cc7b4c508c1908d8a4fba817"
    },
    "c4ke": {
        "LICENSE": "a816cbe521ac46c753c6b4edf18308bec5e95f4f",
        "launcher.sh": "8ab37e3d1ecf8937d305c4642be73eaacd435a3a",
        "minifier/eval.h": "f627e816c78e528dee01a73fa9734bbf846432cb",
        "minifier/main.cpp": "b721d7b8e30dbfb0bb9c695d48ed35877373a6b3",
        "minifier/mini.h": "68ec53e43837281fbc75b6e644816ee7554caace",
        "src/board.cpp": "bc78737f92158f95b1c8bd2204793b3c994acb51",
        "src/chess.cpp": "59377f6afd07739bff3ececa7a588a5f60bd7ff7",
        "src/eval.cpp": "e8ee08cfb46e5c4e06efb0870a5f01d654e5a63c",
        "src/main.cpp": "57a942ee5c415dbcfd1b20912f6193bdd9372791",
        "src/search.cpp": "a9cf924b1ed07ef2f2815baa0c177fb7319628d5"
    }
}

MiB = 1 << 20
RESOURCE_PROFILES = {"test-p4": (4, 24), "test-p28": (28, 26),
                     "test-p16": (16, 31), "test-p192": (192, 34)}
RESOURCE_CAPS = {"test-p4": 128 << 20, "test-p28": 512 << 20,
                 "test-p16": 16 << 30, "test-p192": 192 << 30}
CODEC_SEARCHES = {
    "compact": (16, 64, 128, 273),
    "extended": (16, 24, 32, 40, 48, 56, 64, 72, 80, 96, 112, 128, 160, 192, 224, 273),
}
OFFICIAL_WORKERS = 256
OFFICIAL_TT_BITS = 35


@dataclass(frozen=True)
class PeerSpec:
    name: str
    repository: str
    revision: str
    version: str
    tiny_name: str
    tiny_bytes: int
    tiny_sha256: str
    license: str
    resource_path: str

    @property
    def release_url(self):
        return f"https://github.com/{self.repository}/releases/download/{self.version}/{self.tiny_name}"

    @property
    def source_url(self):
        return f"https://github.com/{self.repository}/tree/{self.revision}"

    def raw_url(self, relative):
        if relative not in SOURCE_BLOBS[self.name]:
            raise ValueError("path is outside the pinned peer source closure")
        return f"https://raw.githubusercontent.com/{self.repository}/{self.revision}/{relative}"


PEERS = {
    "ice4": PeerSpec("ice4", "MinusKelvin/ice4", "2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19",
                     "v6.1", "ice4-tcec", 4087,
                     "707d994e0515473f53052998ee85d03041f17f8c23b3793d497f64b8e41b252b",
                     "GPL-3.0", "minifier/preprocess.rs"),
    "c4ke": PeerSpec("c4ke", "citrus610/c4ke", "22e318f59b3a9eed1d2b8161da832222d4a51033",
                     "v3.0", "c4ke-tcec", 4093,
                     "b5ecbcd8a189cf3296bc5ea874dd0ed612949d02744252041f2d2914776769ea",
                     "MIT", "minifier/mini.h"),
}

NATIVE_ASSETS = {
    "ice4": ("ice4-ob", 516552, "768224f9610cbaf1b0bf7155e6b709a7c9f1f5b6dd30ff56ab40e1006570739d"),
    "c4ke": ("c4ke-linux-x86-64", 115464, "b23bf6d2b5d81ac07ece923f1689ef5f682a4c2ac0f94a4e842eec7f27b65a87"),
}


def peer_spec(name):
    try:
        return PEERS[name]
    except KeyError as error:
        raise ValueError("unsupported peer; select ice4 or c4ke") from error


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def write_json(path, record):
    data = json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False).encode() + b"\n"
    path.write_bytes(data)
    return sha(data)


def external_new(path):
    if path is None or not Path(path).is_absolute():
        raise ValueError("new absolute external output directory required")
    path = Path(path).resolve()
    if path.exists():
        raise ValueError("new absolute external output directory required")
    if any((parent / ".git").exists() for parent in (path, *path.parents)):
        raise ValueError("peer inputs and artifacts must stay outside any Git checkout")
    return path


def fetch_bytes(url, max_bytes):
    # No account configuration, credentials or arbitrary user-provided URLs.
    request = urllib.request.Request(url, headers={"User-Agent": "Rove4k-peer-intake/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("public peer response exceeded its bounded input size")
    return data


def verify_blob(name, relative, data):
    expected = SOURCE_BLOBS[name].get(relative)
    if expected is None or git_blob(data) != expected:
        raise ValueError("pinned peer source differs: " + relative)


def _intake_artifact(name, out, kind, fetch):
    peer = peer_spec(name)
    out = external_new(out)
    tiny = kind == "official-tiny"
    asset, expected_bytes, expected_sha = ((peer.tiny_name, peer.tiny_bytes, peer.tiny_sha256)
                                         if tiny else NATIVE_ASSETS[name])
    url = f"https://github.com/{peer.repository}/releases/download/{peer.version}/{asset}"
    data = fetch(url, expected_bytes)
    if len(data) != expected_bytes or sha(data) != expected_sha:
        raise ValueError("official release bytes differ from the pinned asset")
    license_data = fetch(peer.raw_url("LICENSE"), MiB)
    verify_blob(name, "LICENSE", license_data)
    out.mkdir(parents=True)
    artifact = out / asset
    artifact.write_bytes(data)
    # Intake is intentionally non-executable. Runtime qualification makes a
    # separate disposable executable copy only after resource admission.
    (out / "LICENSE").write_bytes(license_data)
    record = {
        "format": 1, "peer": name, "family": name, "version": peer.version, "revision": peer.revision,
        "artifact_kind": kind, "source_url": peer.source_url, "asset_url": url,
        "license": {"id": peer.license, "path": str(out / "LICENSE"), "sha256": sha(license_data)},
        "resources": ({"workers": OFFICIAL_WORKERS, "entry_bytes": 8, "tt_bits": OFFICIAL_TT_BITS,
                       "tt_entries": 1 << OFFICIAL_TT_BITS, "tt_bytes": 8 << OFFICIAL_TT_BITS}
                      if tiny else None),
        "whole": {"path": str(artifact), "bytes": len(data), "sha256": sha(data)},
        "feature_policy": {"upstream_tiny": tiny, "nbrq_replay_qualified": False},
        "qualification": {"identity_verified": True, "size_within_4096": len(data) <= 4096,
                          "runtime_qualified": False, "league_qualified": False},
        "execution": ("not executed; official resource constants cannot be overridden by UCI options"
                      if tiny else "not executed; explicit resource options and runtime qualification required; never score fallback"),
    }
    record["source_manifest_sha256"] = sha(canonical(SOURCE_BLOBS[name]))
    digest = write_json(out / "peer.json", record)
    return {"path": str(out / "peer.json"), "sha256": digest, "record": record}


def intake_official(name, out, *, fetch=fetch_bytes):
    """Download but never execute the fixed W256 / 256-GiB official tiny."""
    return _intake_artifact(name, out, "official-tiny", fetch)


def intake_native(name, out, *, fetch=fetch_bytes):
    """Optional benchmark input, never an eligible substitute in the score league."""
    return _intake_artifact(name, out, "configurable-native", fetch)


def intake_source(name, out, *, fetch=fetch_bytes):
    """Fetch only the explicit immutable source closure, never an archive."""
    peer = peer_spec(name)
    out = external_new(out)
    out.mkdir(parents=True)
    record = {"format": 1, "peer": name, "revision": peer.revision, "source_url": peer.source_url,
              "license": peer.license, "inputs": {}, "complete": False}
    try:
        for relative in sorted(SOURCE_BLOBS[name]):
            data = fetch(peer.raw_url(relative), MiB)
            verify_blob(name, relative, data)
            path = out / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            record["inputs"][relative] = {"bytes": len(data), "sha256": sha(data), "git_blob": git_blob(data)}
        record["source_closure_sha256"] = sha(canonical(record["inputs"]))
        record["complete"] = True
    finally:
        digest = write_json(out / "source.json", record)
    return {"path": str(out / "source.json"), "sha256": digest, "record": record}


def verify_source(name, directory):
    peer = peer_spec(name)
    directory = Path(directory)
    if not directory.is_absolute() or any((parent / ".git").exists() for parent in (directory, *directory.parents)):
        raise ValueError("pinned peer source must be an absolute external input")
    result = {}
    for relative in sorted(SOURCE_BLOBS[name]):
        path = directory / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or linked peer source input: " + relative)
        data = path.read_bytes()
        verify_blob(peer.name, relative, data)
        result[relative] = data
    return result


def resource_layout(profile):
    try:
        workers, bits = RESOURCE_PROFILES[profile]
    except KeyError as error:
        raise ValueError("peer score profiles are test-p4, test-p28, test-p16 or test-p192") from error
    if profile not in RESOURCE_CAPS or 8 << bits > RESOURCE_CAPS[profile]:
        raise ValueError("peer TT extent exceeds the selected TEST profile cap")
    return {"id": profile, "purpose": "test", "workers": workers, "entry_bytes": 8,
            "tt_bits": bits, "tt_entries": 1 << bits, "tt_bytes": 8 << bits,
            "tt_shift": 64 - bits}


def exact_edits(data, changes):
    """Apply disjoint exact edits and retain a complete inverse."""
    edits = []
    for role, before, after in changes:
        if data.count(before) != 1:
            raise ValueError("resource marker must occur exactly once: " + role)
        edits.append({"role": role, "start": data.index(before), "before": before, "after": after})
    edits.sort(key=lambda value: value["start"])
    output, cursor = [], 0
    for row in edits:
        if row["start"] < cursor:
            raise ValueError("resource edits overlap")
        output.extend((data[cursor:row["start"]], row["after"]))
        cursor = row["start"] + len(row["before"])
    output.append(data[cursor:])
    candidate = b"".join(output)
    proof = {"before_sha256": sha(data), "after_sha256": sha(candidate),
             "edits": [{"role": row["role"], "start": row["start"], "before": row["before"].decode(),
                        "after": row["after"].decode()} for row in edits]}
    if restore_resources(candidate, proof) != data:
        raise ValueError("resource patch full inverse failed")
    return candidate, proof


def restore_resources(candidate, proof):
    if sha(candidate) != proof["after_sha256"]:
        raise ValueError("resource candidate differs from its proof")
    result, cursor, delta = [], 0, 0
    for row in proof["edits"]:
        before, after = row["before"].encode(), row["after"].encode()
        start = row["start"] + delta
        if candidate[start:start + len(after)] != after:
            raise ValueError("resource inverse marker differs")
        result.extend((candidate[cursor:start], before))
        cursor = start + len(after)
        delta += len(after) - len(before)
    result.append(candidate[cursor:])
    restored = b"".join(result)
    if sha(restored) != proof["before_sha256"]:
        raise ValueError("resource inverse changed protected source")
    return restored


def resource_patch(name, data, profile):
    peer, layout = peer_spec(name), resource_layout(profile)
    verify_blob(name, peer.resource_path, data)
    if name == "ice4":
        changes = [
            ("workers", b'"THREADS" if tcec => "256"', f'"THREADS" if tcec => "{layout["workers"]}"'.encode()),
            ("tt_bits", b'"DEFAULT_TT_BITS" if tcec => "35"', f'"DEFAULT_TT_BITS" if tcec => "{layout["tt_bits"]}"'.encode()),
        ]
    else:
        newline = b"\r\n" if b"\r\n" in data else b"\n"
        def block(constant, value):
            return (f'if (is_tcec && name == "{constant}") {{'.encode() + newline +
                    f'            value = "{value}";'.encode() + newline + b"        }")
        changes = [(role, block(constant, old), block(constant, layout[role]))
                   for role, constant, old in (("workers", "THREADS", 256),
                                               ("tt_bits", "TT_BITS", 35), ("tt_shift", "TT_SHIFT", 29))]
    candidate, proof = exact_edits(data, changes)
    proof.update(peer=name, revision=peer.revision, profile=profile, resources=layout,
                 scope="minifier numeric resource substitutions only; algorithm source untouched")
    return candidate, proof


def minifier_commands(name, source, output):
    peer_spec(name)
    source, output = Path(source), Path(output)
    if name == "ice4":
        target = output / "cargo-target"
        return ([["cargo", "build", "--locked", "--release", "--jobs", "1", "--package", "minifier", "--bin", "minifier",
                  "--target-dir", str(target)]], [str(target / "release" / "minifier"), "tcec"])
    return ([["g++", "-O3", "-std=c++23", str(source / "minifier" / "main.cpp"),
              "-o", str(output / "minifier")]], [str(output / "minifier"), "tcec"])


def codec_grid(source, *, search="compact"):
    """Finite replacement for upstream's 1,350-encoder exhaustive shell loop."""
    if search not in CODEC_SEARCHES:
        raise ValueError("unknown bounded peer codec search")
    candidates = []
    finders = (lzma.MF_HC3, lzma.MF_HC4, lzma.MF_BT2, lzma.MF_BT3, lzma.MF_BT4)
    for finder in finders:
        for nice in CODEC_SEARCHES[search]:
            filters = [{"id": lzma.FILTER_LZMA1, "preset": 9 | lzma.PRESET_EXTREME,
                        "lc": 2, "lp": 0, "pb": 0, "mf": finder, "nice_len": nice}]
            payload = lzma.compress(source, format=lzma.FORMAT_ALONE, filters=filters)
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=1 << 30)
            restored = decoder.decompress(payload, max_length=len(source) + 1)
            if restored != source or not decoder.eof or decoder.unused_data:
                raise ValueError("peer payload restore mismatch or extra stream")
            candidates.append({"mf": finder, "nice_len": nice, "payload": payload,
                               "payload_bytes": len(payload), "payload_sha256": sha(payload)})
    return sorted(candidates, key=lambda row: (row["payload_bytes"], row["mf"], row["nice_len"]))


def bounded_run(command, cwd, *, timeout=600, cpu=5, memory_bytes=2 << 30, output_bytes=2 << 20,
                input_bytes=None):
    """Own one build-only process group; never run the produced engine."""
    if sys.platform != "linux":
        raise ValueError("peer minifier builds require Linux")
    import resource
    if not command or not all(isinstance(item, str) and item for item in command):
        raise ValueError("structured command argv required")
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 5))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 << 20, 64 << 20))
        os.sched_setaffinity(0, {cpu})
    started = time.monotonic()
    if input_bytes is not None and not isinstance(input_bytes, bytes):
        raise ValueError("build stdin must be exact source bytes")
    proc = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=True, preexec_fn=limits)
    forced = False
    interrupted_error = None
    try:
        stdout, stderr = proc.communicate(input=input_bytes, timeout=timeout)
    except subprocess.TimeoutExpired:
        forced = True
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
    except BaseException as error:
        forced = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
        interrupted_error = error
    # Compiler children must not survive a successfully exited leader either.
    remaining = False
    try:
        os.killpg(proc.pid, 0)
        remaining = True
    except ProcessLookupError:
        pass
    if remaining:
        forced = True
        os.killpg(proc.pid, signal.SIGKILL)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                remaining = False
                break
            time.sleep(0.02)
    record = {"argv": command, "cwd": str(cwd), "exit_code": proc.returncode,
              "elapsed_seconds": time.monotonic() - started, "leader_reaped": proc.poll() is not None,
              "forced_cleanup": forced, "group_absent": not remaining,
              "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr)}
    if input_bytes is not None:
        record["stdin"] = {"bytes": len(input_bytes), "sha256": sha(input_bytes)}
    logs = Path(cwd).parent / "command-logs"
    logs.mkdir(exist_ok=True)
    key = str(time.monotonic_ns())
    for label, data in (("stdout", stdout), ("stderr", stderr)):
        path = logs / (key + "." + label)
        path.write_bytes(data[:output_bytes])
        record[label] = {"path": str(path), "bytes": len(data), "truncated": len(data) > output_bytes}
    write_json(logs / (key + ".json"), record)
    if interrupted_error is not None:
        raise interrupted_error
    if len(stdout) > output_bytes or len(stderr) > output_bytes:
        raise RuntimeError("peer build exceeded output bound: " + json.dumps(record, sort_keys=True))
    if forced or proc.returncode:
        raise RuntimeError("peer minifier command failed: " + json.dumps(record, sort_keys=True))
    return stdout, stderr, record


def build_resource_tiny(name, source, out, profile, *, run=bounded_run, codec_search="compact"):
    """Rebuild two resource-only minifier/package attempts, without executing engines."""
    peer, layout = peer_spec(name), resource_layout(profile)
    if codec_search not in CODEC_SEARCHES:
        raise ValueError("unknown bounded peer codec search")
    original = verify_source(name, source)
    out = external_new(out)
    out.mkdir(parents=True)
    (out / "peer-producer.py").write_bytes(TOOL_SOURCE)
    record = {"format": 1, "peer": name, "family": name, "version": peer.version, "revision": peer.revision,
              "artifact_kind": "resource-tiny", "resources": layout, "source_url": peer.source_url,
              "producer": {"path": str(out / "peer-producer.py"), "bytes": len(TOOL_SOURCE), "sha256": sha(TOOL_SOURCE)},
              "codec_search": {"name": codec_search, "nice_lengths": CODEC_SEARCHES[codec_search]},
              "license": peer.license, "attempts": [], "complete": False,
              "qualification": {"runtime_qualified": False, "league_qualified": False}}
    try:
        for index in (1, 2):
            attempt = out / f"attempt-{index}"
            src = attempt / "source"
            src.mkdir(parents=True)
            for relative, data in original.items():
                path = src / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            changed, proof = resource_patch(name, original[peer.resource_path], profile)
            (src / peer.resource_path).write_bytes(changed)
            write_json(attempt / "resource-proof.json", proof)
            compile_commands, emit_command = minifier_commands(name, src, attempt)
            commands = []
            version, version_errors, version_record = run([compile_commands[0][0], "--version"], src)
            commands.append(version_record)
            (attempt / "compiler.version").write_bytes(version)
            (attempt / "compiler-version.stderr").write_bytes(version_errors)
            for number, command in enumerate(compile_commands):
                stdout, stderr, command_record = run(command, src)
                commands.append(command_record)
                (attempt / f"compile-{number}.stdout").write_bytes(stdout)
                (attempt / f"compile-{number}.stderr").write_bytes(stderr)
            minified, stderr, command_record = run(emit_command, src)
            commands.append(command_record)
            if not minified.startswith(b"#include") or len(minified) > MiB:
                raise ValueError("minifier did not emit an admitted source stream")
            (attempt / "main.cpp").write_bytes(minified)
            (attempt / "minifier.stderr").write_bytes(stderr)
            for relative, data in original.items():
                expected = changed if relative == peer.resource_path else data
                if (src / relative).read_bytes() != expected:
                    raise ValueError("minifier modified a protected peer input: " + relative)
            grid = codec_grid(minified, search=codec_search)
            selected = grid[0]
            whole = original["launcher.sh"] + selected["payload"]
            path = attempt / peer.tiny_name
            path.write_bytes(whole)
            row = {"source": {"bytes": len(minified), "sha256": sha(minified)},
                   "whole": {"path": str(path), "bytes": len(whole), "sha256": sha(whole)},
                   "header": {"bytes": len(original["launcher.sh"]), "sha256": sha(original["launcher.sh"])},
                   "selected_codec": {key: value for key, value in selected.items() if key != "payload"},
                   "compiler_version_sha256": sha(version),
                   "codec_trials": len(grid), "resource_proof_sha256": sha(canonical(proof)), "commands": commands}
            record["attempts"].append(row)
        first, second = record["attempts"]
        if first["source"] != second["source"] or first["whole"]["sha256"] != second["whole"]["sha256"]:
            raise ValueError("resource peer source/whole reproduction differs")
        record.update(complete=True, reproducible=True, whole=first["whole"],
                      feature_policy={"upstream_tiny": True, "generated_promotions": ["q"],
                                      "nbrq_replay_qualified": False})
        record["qualification"].update(size_within_4096=first["whole"]["bytes"] <= 4096,
                                       identity_verified=True, source_resource_patch_verified=True)
    except BaseException as error:
        record["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        digest = write_json(out / "peer.json", record)
    return {"path": str(out / "peer.json"), "sha256": digest, "record": record}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("official", "native", "source", "plan", "build"))
    parser.add_argument("--peer", choices=tuple(PEERS), required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--profile", choices=tuple(RESOURCE_PROFILES), default="test-p4")
    parser.add_argument("--cpu", type=int, default=5, help="owned CPU for bounded build commands")
    parser.add_argument("--wall-seconds", type=int, default=600)
    parser.add_argument("--codec-search", choices=tuple(CODEC_SEARCHES), default="compact")
    args = parser.parse_args()
    if args.out is None:
        parser.error("all actions require --out (plan records the intended path without creating it)")
    if args.wall_seconds <= 0 or args.cpu < 0:
        parser.error("positive wall bound and nonnegative owned CPU required")
    if args.action == "plan":
        if args.source is None or args.out is None:
            parser.error("plan requires --source and --out")
        result = {"peer": args.peer, "resources": resource_layout(args.profile),
                  "commands": minifier_commands(args.peer, args.source, args.out),
                  "engines_executed": False, "runtime_qualified": False}
    elif args.action == "official":
        result = intake_official(args.peer, args.out)
    elif args.action == "native":
        result = intake_native(args.peer, args.out)
    elif args.action == "source":
        result = intake_source(args.peer, args.out)
    else:
        if args.source is None:
            parser.error("build requires --source")
        result = build_resource_tiny(args.peer, args.source, args.out, args.profile,
                                     run=partial(bounded_run, cpu=args.cpu, timeout=args.wall_seconds),
                                     codec_search=args.codec_search)
    print(json.dumps({key: value for key, value in result.items() if key != "record"}, sort_keys=True))


if __name__ == "__main__":
    if hasattr(signal, "SIGTERM"):
        def interrupted(signum, frame):
            raise KeyboardInterrupt("peer preparation cancelled")
        signal.signal(signal.SIGTERM, interrupted)
    main()
