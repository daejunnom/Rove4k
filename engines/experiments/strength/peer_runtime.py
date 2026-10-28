#!/usr/bin/env python3
"""Source-bound qualification of external peers' full resource-only tiny files.

Reference compilation and engine execution are separate actions. Official
W256/256GiB files and oversize/resource-unproven files cannot reach execution.
The driver observes the actual native image, TT allocation and worker CPUs;
source size, a package manifest, or an oversubscribed smoke test cannot admit a
player. Peer queen-only generation is explicit; N/B/R/Q *input* replay is tested.
"""
from __future__ import annotations

import argparse
from functools import wraps
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import struct
import sys
import threading
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
SOURCE_FILES = (
    "engines/experiments/strength/peer_runtime.py",
    "engines/experiments/strength/peers.py",
    "engines/experiments/strength/registry.py",
    "engines/experiments/strength/placement.py",
    "engines/experiments/strength/topology.py",
    "engines/scripts/production.py",
    "engines/compact/tiny-entry-d/verify.py",
    "engines/experiments/tcec-scope/verify.py",
    "engines/tests/chess_oracle.py",
)
LEAGUE_SOURCE_FILES = ("engines/scripts/league_resource_profiles.py",)
CONTROLLED_SOURCE_FILES = tuple("engines/experiments/strength/" + name + ".py" for name in (
    "functional_probe_session", "functional_uci_probe", "diagnostic_candidates",
    "peak_capacity", "peak_probe_session", "memory_observation", "run",
    "rove_b_tt_observe", "rove_vma_observer", "rove_b_static_tt",
    "budget", "collect", "durability", "fastchess", "ledger", "overhead",
    "peak_ready_probe", "peak_supervisor", "peak_receipt", "wave")) + (
        "engines/experiments/tcec-next/profile_verify.py",
        "engines/scripts/production_input.py",
    )
HELPER_PINS = {
    "engines/compact/tiny-entry-d/verify.py": "18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae",
    "engines/tests/chess_oracle.py": "aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8",
}
DEPENDENCIES = frozenset(("libstdc++.so.6", "libm.so.6", "libgcc_s.so.1", "libc.so.6",
                          "libpthread.so.0", "librt.so.1", "libatomic.so.1"))
CONSTRUCTING_OWNED = False
DEFERRED_SIGNAL = None


def require(value, message):
    if not value:
        raise ValueError(message)


def bounded_signal(signum, frame):
    global DEFERRED_SIGNAL
    if CONSTRUCTING_OWNED:
        DEFERRED_SIGNAL = signum
        return
    raise KeyboardInterrupt("peer preparation/qualification signal " + str(signum))


def owned_signals(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        global DEFERRED_SIGNAL
        require(threading.current_thread() is threading.main_thread(), "owned process execution requires main-thread signal ownership")
        DEFERRED_SIGNAL = None
        previous = {number: signal.signal(number, bounded_signal) for number in (signal.SIGINT, signal.SIGTERM)}
        try:
            return function(*args, **kwargs)
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
    return wrapped


def construct_owned(helper, launcher, directory, budget):
    global CONSTRUCTING_OWNED
    CONSTRUCTING_OWNED = True
    try:
        owned = helper.Owned(launcher, directory, budget)
    finally:
        CONSTRUCTING_OWNED = False
    if DEFERRED_SIGNAL is not None:
        # The helper has already registered the original process and readers;
        # outer cleanup also sees it when construction never returns a handle.
        raise KeyboardInterrupt("peer constructor signal " + str(DEFERRED_SIGNAL))
    return owned


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def sibling(name, root=ROOT):
    path = root / "engines/experiments/strength" / (name + ".py")
    return load("peer_runtime_" + name + "_" + sha(str(root).encode())[:12], path)


def ordinary(path, *, maximum=8 << 20):
    path = Path(path)
    forbidden = {"inventory.json", "package-lock.json", "node_modules", "dist", "dist-server", "build",
                 "coverage", "models", "checkpoints", ".cache", ".ssh"}
    require(not any(part in forbidden or part.startswith(".env") or re.search(
        r"(?:credential|service[-_ ]?account|api[-_ ]?key|^id_(?:rsa|dsa|ecdsa|ed25519)$)", part, re.I) for part in path.parts),
        "non-source or secret-like path is not an admitted qualification input")
    require(path.is_absolute() and not path.is_symlink() and path.is_file(), "absolute ordinary input required")
    require(path.stat().st_size <= maximum, "input exceeds explicit byte bound")
    return path.read_bytes()


def bound(path, expected):
    data = ordinary(path)
    require(len(data) == expected["bytes"] and sha(data) == expected["sha256"], "bound input bytes changed: " + str(path))
    return data


def read_record(path, expected_sha=None):
    data = ordinary(path)
    if expected_sha is not None:
        require(sha(data) == expected_sha, "manifest SHA-256 differs")
    return json.loads(data), sha(data)


def durable_new(path, data):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def process_identity(pid):
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return {"pid": pid, "pgid": int(fields[2]), "session": int(fields[3]), "start_ticks": int(fields[19])}


def _freeze(out, *, league_required=False, controlled_required=False):
    pins = {}
    for relative in SOURCE_FILES + (LEAGUE_SOURCE_FILES if league_required else ()) + (CONTROLLED_SOURCE_FILES if controlled_required else ()):
        data = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
        require(relative not in HELPER_PINS or sha(data) == HELPER_PINS[relative], "owned helper changed: " + relative)
        destination = out / "source-closure" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        pins[relative] = {"bytes": len(data), "sha256": sha(data)}
    return pins


def _verify_frozen(directory, pins, *, league_required=False):
    expected = SOURCE_FILES + (LEAGUE_SOURCE_FILES if league_required else ())
    require(set(pins) == set(expected), "qualification source closure is incomplete")
    for relative, pin in pins.items():
        bound(directory / relative, pin)
        require(relative not in HELPER_PINS or pin["sha256"] == HELPER_PINS[relative], "qualification helper pin differs")


def tt_declaration(source, layout):
    """Identify the single emitted allocation; never guess a renamed TT symbol."""
    require(source.count(b"calloc(") == 1, "peer must have one identifiable TT allocation")
    rows = re.findall(rb"([A-Za-z_]\w*)\s*=\s*\([^;()]+\*\)calloc\(1ull<<(\d+),(\d+)\)", source)
    require(len(rows) == 1, "resource-only TT declaration cannot be identified")
    name, bits, stride = rows[0]
    require(int(bits) == layout["tt_bits"] and int(stride) == layout["entry_bytes"], "emitted TT allocation differs from TEST profile")
    return name.decode("ascii")


def worker_declaration(peer, source, workers):
    """Admit the pinned minifiers' actual array and construction bounds."""
    if peer == "ice4":
        rows = re.findall(rb"thread\s+(\w+)\[(\d+)\];for\(thread&(\w+):\1\)\3=thread\(", source)
        require(len(rows) == 1 and int(rows[0][1]) == workers, "emitted ice4 worker construction differs from TEST profile")
    else:
        require(peer == "c4ke", "unknown peer")
        rows = re.findall(rb"jthread\s+(\w+)\[(\d+)\];for\(\w+\s+(\w+)=0;\3<(\d+);\3\+\+\)\1\[\3\]=jthread\(", source)
        require(len(rows) == 1 and int(rows[0][1]) == int(rows[0][3]) == workers,
                "emitted c4ke array/worker construction differs from TEST profile")
    return {"workers": workers, "array_symbol": rows[0][0].decode("ascii"), "construction_bound_verified": True}


def compile_argv(peer, output):
    # These are the compiler argv in each pinned four-line launcher. Feeding
    # stdin also preserves <stdin> in ELF STT_FILE; compiling a filename does not.
    if peer == "ice4":
        return ["c++", "-O3", "-pthread", "-xc++", "-o" + str(output), "-"]
    require(peer == "c4ke", "unknown peer")
    return ["g++", "-O3", "-std=c++23", "-pthread", "-march=native", "-xc++", "-o" + str(output), "-"]


def validate_build(path, expected_sha=None):
    peers = sibling("peers")
    path = Path(path)
    require(path.is_absolute() and not any((parent / ".git").exists() for parent in path.parents),
            "peer build receipt must be external to Git")
    record, digest = read_record(path, expected_sha)
    name, profile = record.get("peer"), record.get("resources", {}).get("id")
    peer, layout = peers.peer_spec(name), peers.resource_layout(profile)
    require(record.get("artifact_kind") == "resource-tiny" and record.get("revision") == peer.revision,
            "only pinned resource-only TEST peers are executable")
    require(record.get("resources") == layout and record.get("complete") is True and record.get("reproducible") is True,
            "two completed source/whole build attempts required")
    require(record.get("feature_policy") == {"upstream_tiny": True, "generated_promotions": ["q"], "nbrq_replay_qualified": False},
            "full upstream tiny feature policy differs")
    require(len(record.get("attempts", [])) == 2, "two independent build attempts required")
    producer = record.get("producer")
    require(isinstance(producer, dict), "build lacks frozen producer source; rebuild rather than invent provenance")
    require(producer.get("path") == str(path.parent / "peer-producer.py"), "producer path is outside bound build output")
    bound(producer["path"], producer)
    sources, wholes, observed = [], [], []
    for index, row in enumerate(record["attempts"], 1):
        attempt = Path(path).parent / ("attempt-" + str(index))
        require(row["whole"]["path"] == str(attempt / peer.tiny_name), "whole path is outside bound build attempt")
        source = bound(attempt / "main.cpp", row["source"])
        whole = bound(row["whole"]["path"], row["whole"])
        original = {}
        proof, _ = read_record(attempt / "resource-proof.json")
        require(sha(peers.canonical(proof)) == row["resource_proof_sha256"], "resource proof differs")
        for relative in sorted(peers.SOURCE_BLOBS[name]):
            data = ordinary(attempt / "source" / relative)
            if relative == peer.resource_path:
                data = peers.restore_resources(data, proof)
            peers.verify_blob(name, relative, data)
            original[relative] = data
        changed, expected_proof = peers.resource_patch(name, original[peer.resource_path], profile)
        require(proof == expected_proof and ordinary(attempt / "source" / peer.resource_path) == changed,
                "resource proof permits something beyond exact W/TT substitutions")
        header = original["launcher.sh"]
        require(whole.startswith(header) and row["header"] == {"bytes": len(header), "sha256": sha(header)},
                "whole file must use exact pinned launcher")
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=1 << 30)
        decoded = decoder.decompress(whole[len(header):], max_length=len(source) + 1)
        require(decoded == source and decoder.eof and not decoder.unused_data, "whole source inverse has extra/truncated/changed data")
        require(len(row.get("commands", [])) == 3 and all(command.get("exit_code") == 0
                and command.get("leader_reaped") is True and command.get("group_absent") is True
                and command.get("forced_cleanup") is False for command in row["commands"]), "producer command settlement evidence is incomplete")
        require(row["commands"][-1]["stdout_sha256"] == sha(source), "minifier stdout does not bind actual source")
        sources.append(source)
        wholes.append(whole)
        observed.append({"attempt": index, "source_inputs": len(original), "resource_proof_sha256": sha(peers.canonical(proof))})
    require(sources[0] == sources[1] and wholes[0] == wholes[1], "independent build outputs differ")
    require(record["whole"] == record["attempts"][0]["whole"], "selected whole is not the reproduced first attempt")
    require(len(wholes[0]) <= 4096, "blocked_size: complete resource-tiny file exceeds 4096 bytes")
    symbol = tt_declaration(sources[0], layout)
    worker_source = worker_declaration(name, sources[0], layout["workers"])
    return {"record": record, "manifest_sha256": digest, "peer": name, "layout": layout,
            "source": sources[0], "whole": wholes[0], "tt_symbol": symbol, "worker_source": worker_source,
            "input_observations": observed}


class Elf64:
    """Bounded ELF64 little-endian metadata reader; no external binary execution."""
    def __init__(self, data):
        self.data = data
        require(data[:7] == b"\x7fELF\x02\x01\x01" and len(data) >= 64, "native must be ELF64 little-endian")
        fields = self.unpack("HHIQQQIHHHHHH", 16)
        self.kind, machine, version, _, phoff, shoff, _, _, phsize, phnum, shsize, shnum, _ = fields
        require(self.kind in (2, 3) and machine == 62 and version == 1 and phsize == 56 and shsize == 64,
                "unsupported ELF ABI or header geometry")
        require(0 < phnum <= 256 and 0 < shnum <= 4096, "ELF table count exceeds bound")
        self.programs = [self.unpack("IIQQQQQQ", phoff + index * phsize) for index in range(phnum)]
        self.sections = [self.unpack("IIQQQQIIQQ", shoff + index * shsize) for index in range(shnum)]

    def unpack(self, form, offset):
        size = struct.calcsize("<" + form)
        require(type(offset) is int and 0 <= offset <= len(self.data) - size, "ELF table is out of bounds")
        return struct.unpack_from("<" + form, self.data, offset)

    def segment(self, offset, length):
        require(0 <= offset <= len(self.data) and 0 <= length <= len(self.data) - offset, "ELF segment is out of bounds")
        return self.data[offset:offset + length]

    @staticmethod
    def string(data, offset):
        require(0 <= offset < len(data), "ELF string index out of bounds")
        end = data.find(b"\0", offset)
        require(end >= 0, "unterminated ELF string")
        return data[offset:end].decode("ascii")

    def pointer_symbol(self, name):
        matches = []
        for section in self.sections:
            if section[1] != 2:
                continue
            offset, length, link, stride = section[4], section[5], section[6], section[9]
            require(stride == 24 and length % stride == 0 and link < len(self.sections), "invalid ELF symbol table")
            strings = self.segment(self.sections[link][4], self.sections[link][5])
            for index in range(length // stride):
                symbol = self.unpack("IBBHQQ", offset + index * stride)
                if self.string(strings, symbol[0]) == name and symbol[1] & 15 == 1 and symbol[3] != 0:
                    require(symbol[5] == 8, "actual TT pointer symbol does not have pointer size")
                    matches.append(symbol[4])
        require(len(matches) == 1, "actual TT pointer has no unique ELF object symbol")
        return matches[0]

    def dependencies(self):
        needed, interpreter = [], []
        for program in self.programs:
            if program[0] == 3:
                interpreter.append(self.segment(program[2], program[5]).rstrip(b"\0").decode("ascii"))
        for section in self.sections:
            if section[1] != 6:
                continue
            require(section[9] == 16 and section[5] % 16 == 0 and section[6] < len(self.sections), "invalid ELF dynamic table")
            strings = self.segment(self.sections[section[6]][4], self.sections[section[6]][5])
            for offset in range(section[4], section[4] + section[5], 16):
                tag, value = self.unpack("qQ", offset)
                if tag == 1:
                    needed.append(self.string(strings, value))
        require(len(interpreter) == 1 and interpreter[0] in ("/lib64/ld-linux-x86-64.so.2", "/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"),
                "unexpected native interpreter")
        require(needed and len(needed) == len(set(needed)) and set(needed) <= DEPENDENCIES, "undeclared native dependency")
        return {"interpreter": interpreter[0], "needed": needed}


@owned_signals
def prepare_reference(build, out, *, manifest_sha=None, cpu=5, timeout=600):
    """Compile exact payload stdin twice, without executing a produced engine."""
    require(sys.platform == "linux", "reference compilation requires Linux")
    peers = sibling("peers")
    admitted = validate_build(build, manifest_sha)
    out = peers.external_new(out)
    out.mkdir(parents=True)
    record = {"format": "rove4k-peer-reference-v1", "complete": False,
              "build": {"path": str(build), "sha256": admitted["manifest_sha256"]},
              "peer": admitted["peer"], "resources": admitted["layout"], "tt_symbol": admitted["tt_symbol"],
              "worker_source": admitted["worker_source"],
              "input_observations": admitted["input_observations"], "commands": [], "engines_executed": 0}
    try:
        record["source_inputs"] = _freeze(out, league_required=admitted["layout"]["id"] in ("test-p16", "test-p192"))
        (out / "main.cpp").write_bytes(admitted["source"])
        record["source"] = {"bytes": len(admitted["source"]), "sha256": sha(admitted["source"])}
        compiler = compile_argv(admitted["peer"], out / "unused")[0]
        version, _, command = peers.bounded_run([compiler, "--version"], out, cpu=cpu, timeout=timeout)
        record["commands"].append(command)
        (out / "compiler.version").write_bytes(version)
        record["compiler"] = {"command": compiler, "path": shutil.which(compiler), "version_sha256": sha(version)}
        natives = []
        for index in (1, 2, 3):
            target = out / ("reference-" + str(index))
            source = admitted["source"]
            if index == 3:
                source += ("\nstatic_assert(sizeof(*" + admitted["tt_symbol"] + ") == 8);\n").encode()
            _, _, command = peers.bounded_run(compile_argv(admitted["peer"], target), out, cpu=cpu,
                                               timeout=timeout, input_bytes=source)
            record["commands"].append(command)
            native = ordinary(target)
            natives.append(native)
            record.setdefault("native_attempts", []).append({"path": str(target), "bytes": len(native), "sha256": sha(native),
                                                             "layout_assertion": index == 3})
        require(natives[0] == natives[1], "two exact native reference compilations differ")
        require(natives[0] == natives[2], "inert entry-size assertion changed emitted native image")
        elf = Elf64(natives[0])
        record.update(complete=True, native=record["native_attempts"][0], tt_symbol_value=elf.pointer_symbol(admitted["tt_symbol"]),
                      entry_size_compile_assertion=True, dependencies=elf.dependencies())
    except BaseException as error:
        record["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        digest = peers.write_json(out / "reference.json", record)
    return {"path": str(out / "reference.json"), "sha256": digest, "record": record}


def mappings(pid):
    result = []
    for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        first, last = (int(value, 16) for value in fields[0].split("-"))
        result.append({"start": first, "end": last, "permissions": fields[1], "offset": int(fields[2], 16),
                       "device": fields[3], "inode": int(fields[4]), "path": fields[5] if len(fields) > 5 else ""})
    return result


def runtime_tt(pid, elf, symbol, tt_bytes):
    """Read the actual pointer in the admitted image and verify its RW extent."""
    image_stat = Path(f"/proc/{pid}/exe").stat()
    rows = mappings(pid)
    image_rows = [row for row in rows if row["inode"] == image_stat.st_ino
                  and tuple(int(part, 16) for part in row["device"].split(":")) == (os.major(image_stat.st_dev), os.minor(image_stat.st_dev))]
    loads = [program for program in elf.programs if program[0] == 1 and program[2] == 0]
    require(len(loads) == 1, "native has no unique zero-offset load segment")
    bases = {row["start"] - loads[0][3] for row in image_rows if row["offset"] == 0}
    require(len(bases) == 1, "actual PIE image load bias is ambiguous")
    bias = next(iter(bases))
    address = bias + elf.pointer_symbol(symbol)
    require(any(program[0] == 1 and bias + program[3] <= address and address + 8 <= bias + program[3] + program[6]
                for program in elf.programs) and any(row["start"] <= address and address + 8 <= row["end"]
                and "r" in row["permissions"] for row in rows),
            "TT pointer symbol is outside actual readable engine load segments")
    descriptor = os.open(f"/proc/{pid}/mem", os.O_RDONLY)
    try:
        value = os.pread(descriptor, 8, address)
    finally:
        os.close(descriptor)
    require(len(value) == 8, "actual TT pointer read was incomplete")
    pointer = int.from_bytes(value, "little")
    require(pointer > 0 and pointer + tt_bytes < 1 << 63, "actual TT pointer/range is invalid")
    coverage = pointer
    mapped = []
    for row in rows:
        if row["end"] <= coverage or row["start"] > coverage:
            continue
        require("rw" == row["permissions"][:2] and row["permissions"][3] == "p", "TT allocation is not private readable writable memory")
        mapped.append(row)
        coverage = min(pointer + tt_bytes, row["end"])
        if coverage == pointer + tt_bytes:
            break
    require(coverage == pointer + tt_bytes, "actual TT virtual mapping is smaller than the declared allocation")
    return {"pointer_symbol_address": address, "pointer": pointer, "tt_bytes": tt_bytes, "entry_bytes": 8,
            "mapping_extent_verified": True, "mappings": mapped,
            "scope": "actual calloc pointer and virtual allocation; not resident/touched bytes or peak memory"}


def validate_slot(topology, slot, layout, *, allow_functional=False):
    cpus = slot.get("cpus")
    require(isinstance(cpus, (list, tuple)) and cpus and len(cpus) == len(set(cpus)) and all(type(cpu) is int for cpu in cpus),
            "explicit unique actual CPU IDs required")
    by_id = {cpu.id: cpu for cpu in topology.cpus}
    require(set(cpus) <= set(topology.allowed_cpus) and set(cpus) <= set(by_id), "slot is outside actual allowed topology")
    actual = [by_id[cpu] for cpu in cpus]
    physical = {cpu.physical for cpu in actual}
    nodes = {cpu.node for cpu in actual}
    require(set(slot.get("memory_nodes", [])) == nodes and nodes <= set(topology.allowed_nodes), "slot memory nodes differ from actual CPU nodes")
    require(slot.get("workers") == layout["workers"] and slot.get("policy", "inherit") in ("inherit", "default", "interleave"), "slot resource/policy mismatch")
    profile = layout.get("id")
    if profile in ("test-p16", "test-p192"):
        expected_cores, expected_workers = {"test-p16": (8, 16), "test-p192": (96, 192)}[profile]
        require(layout["workers"] == expected_workers and len(cpus) == expected_workers
                and len(physical) == expected_cores and slot.get("smt") is True,
                "SMT TEST geometry does not match the named profile")
        require(profile != "test-p16" or len(nodes) == 1,
                "P16 requires one actual NUMA node")
        require(profile != "test-p192" or set(cpus) == set(topology.allowed_cpus),
                "P192 must cover the entire allowed CPU envelope")
        # Require exactly the observed pair on each physical core, with a
        # symmetric sysfs sibling declaration. Counts alone cannot establish
        # that the same core's two hardware threads were selected.
        for core in physical:
            siblings = [cpu for cpu in actual if cpu.physical == core]
            ids = {cpu.id for cpu in siblings}
            require(len(siblings) == 2 and all(set(cpu.siblings) == ids for cpu in siblings),
                    "SMT TEST slot requires complete symmetric observed sibling pairs")
        # Geometry alone does not establish actual large-resource runtime,
        # cgroup memory, task policy, or scored controller placement.
        qualified = False
        require(allow_functional, "SMT TEST geometry is diagnostic only until runtime and placement evidence is available")
    else:
        qualified = len(cpus) == len(physical) == layout["workers"] and slot.get("smt") is False
        require(qualified or allow_functional, "actual one-sibling physical TEST placement is unavailable; explicit functional scope required")
    if "physical_cores" in slot:
        require({tuple(row) for row in slot["physical_cores"]} == physical, "declared physical cores differ from sysfs")
    return {"physical_cores": len(physical), "logical_cpus": len(cpus), "cpu_ids": sorted(cpus),
            "memory_nodes": sorted(nodes), "one_sibling_per_core": len(cpus) == len(physical), "qualified": qualified,
            "scope": ("SMT geometry only; runtime and scored placement are not qualified"
                      if profile in ("test-p16", "test-p192") else
                      "physical TEST placement only; no W256 strength or scaling evidence")}


def effective_available_bytes(proc=Path("/proc"), cgroup_root=Path("/sys/fs/cgroup")):
    """Conservative current host/cgroup availability, not a reservation."""
    rows = dict(line.split(":", 1) for line in (proc / "meminfo").read_text().splitlines() if ":" in line)
    match = re.fullmatch(r"\s*(\d+)\s+kB\s*", rows.get("MemAvailable", ""))
    require(match is not None, "host MemAvailable is unavailable or malformed")
    host = int(match[1]) * 1024
    limits, found = [], False
    for line in (proc / "self/cgroup").read_text().splitlines():
        fields = line.split(":", 2)
        require(len(fields) == 3, "invalid cgroup membership")
        if fields[0:2] == ["0", ""]:
            base, names = cgroup_root, ("memory.max", "memory.current")
        elif "memory" in fields[1].split(","):
            base, names = cgroup_root / "memory", ("memory.limit_in_bytes", "memory.usage_in_bytes")
        else:
            continue
        relative = PurePosixPath(fields[2].lstrip("/"))
        require(".." not in relative.parts, "invalid effective cgroup path")
        require(fields[0:2] != ["0", ""] or relative.parts,
                "root-only cgroup namespace cannot prove effective ancestor memory limits")
        directory, read_any = base.joinpath(*relative.parts), False
        while True:
            maximum, current = directory / names[0], directory / names[1]
            maximum_exists, current_exists = maximum.is_file(), current.is_file()
            # cgroup-v2 root has no memory.max/current. We can omit it only
            # after observing at least one non-root level; a root-only view
            # cannot prove whether a namespace hides a constrained ancestor.
            if directory == base and fields[0:2] == ["0", ""] and not maximum_exists and not current_exists:
                break
            require(maximum_exists and current_exists,
                    "effective cgroup ancestor memory limit or usage is unavailable")
            if maximum_exists and current_exists:
                read_any = True
                maximum_value, current_value = maximum.read_text().strip(), current.read_text().strip()
                require(current_value.isdecimal(), "invalid current cgroup memory usage")
                require(maximum_value == "max" or maximum_value.isdecimal(), "invalid cgroup memory limit")
                if maximum_value != "max":
                    limits.append(int(maximum_value) - int(current_value))
            if directory == base:
                break
            directory = directory.parent
        require(read_any, "effective cgroup memory limit is unavailable")
        found = True
    require(found, "effective cgroup memory controller is unavailable")
    return {"host_available_bytes": host, "cgroup_remaining_bytes": limits,
            "effective_available_bytes": min([host, *limits]),
            "scope": "point-in-time visible cgroup ancestry; hidden namespace ancestors and memory reservation are not proven"}


def peer_runtime_budget(layout, *, cpus, wall_seconds, availability, parent_limits):
    """Build a bounded large-profile child budget without raising inherited limits."""
    profile, workers, tt_bytes = layout.get("id"), layout.get("workers"), layout.get("tt_bytes")
    require(profile in ("test-p16", "test-p192") and type(workers) is int
            and workers == {"test-p16": 16, "test-p192": 192}[profile],
            "unsupported large peer runtime profile")
    require(type(tt_bytes) is int and tt_bytes == {"test-p16": 16 << 30, "test-p192": 192 << 30}[profile],
            "peer TT extent differs from its finite resource profile")
    require(type(wall_seconds) is int and 60 <= wall_seconds <= 600, "bounded peer wall time required")
    require(isinstance(cpus, (list, tuple)) and len(cpus) == workers and len(set(cpus)) == workers
            and all(type(cpu) is int and cpu >= 0 for cpu in cpus), "exact actual logical CPU envelope required")
    require(isinstance(availability, dict), "memory observation record required")
    other = max(768 << 20, workers * (16 << 20))
    required, address_space = tt_bytes + other + (256 << 20), max(4 << 30, tt_bytes + other)
    active_cpus = len(cpus)
    cpu_soft = max(180, min(140, wall_seconds - 10) * active_cpus)
    cpu_hard = cpu_soft + max(5, 2 * active_cpus)
    for name, needed in (("address_space", address_space), ("cpu", cpu_hard)):
        pair = parent_limits.get(name)
        require(isinstance(pair, (tuple, list)) and len(pair) == 2 and
                all(type(value) is int and (value == -1 or value >= needed) for value in pair),
                "peer " + name + " budget exceeds inherited soft or hard limit")
    return {"profile": profile, "workers": workers, "tt_bytes": tt_bytes,
            "required_available_bytes": required, "other_peak_bytes": other,
            "address_space_bytes": address_space, "cpu_seconds": [cpu_soft, cpu_hard],
            "effective_cpus": active_cpus, "wall_seconds": wall_seconds,
            "parent_limits": parent_limits, "availability": availability,
            "current_availability_enforced": False,
            "scope": "single peer host/cgroup preflight; no reservation or scored game admission"}


def observed_peer_runtime_budget(layout, *, cpus, wall_seconds):
    """Refresh memory and inherited limits immediately before each owned launch."""
    import resource
    limits = {"address_space": list(resource.getrlimit(resource.RLIMIT_AS)),
              "cpu": list(resource.getrlimit(resource.RLIMIT_CPU))}
    try:
        availability = effective_available_bytes()
    except (OSError, ValueError) as error:
        availability = {"status": "unavailable", "error": str(error),
                        "scope": "memory telemetry is not a start gate"}
    return peer_runtime_budget(layout, cpus=cpus, wall_seconds=wall_seconds,
                               availability=availability, parent_limits=limits)


def checked_child_limit(resource, kind, soft, hard):
    """Read inherited limits again in the child, then only narrow them."""
    require(type(soft) is int and type(hard) is int and 0 < soft <= hard,
            "invalid child resource limit")
    before = resource.getrlimit(kind)
    require(len(before) == 2 and all(type(value) is int and
            (value == resource.RLIM_INFINITY or value >= hard) for value in before),
            "inherited child limit is below admitted budget")
    resource.setrlimit(kind, (soft, hard))
    return list(before)


def _write_controlled_launcher(path, whole, temporary, slot, placement_record, frozen_root, owner_record, release,
                               runtime_budget, controlled):
    """Load pinned placement bytes and execute a sealed peer snapshot."""
    require(runtime_budget is not None, "controlled peer needs preflight resource limits")
    pins = controlled["source_pins"]
    modules = [(name, str(frozen_root / ("engines/experiments/strength/" + name + ".py")),
                pins["engines/experiments/strength/" + name + ".py"]["sha256"])
               for name in ("topology", "placement")]
    source = "#!/usr/bin/python3 -I\n" + "\n".join((
        "import fcntl,hashlib,json,os,resource,stat,sys,time,types", "from pathlib import Path",
        "sys.dont_write_bytecode=True",
        "def read_safe(path,limit):",
        " p=Path(path)",
        " if not p.is_absolute() or '..' in p.parts: raise RuntimeError('unsafe controlled input')",
        " d=os.open(p.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)",
        " try:",
        "  for part in p.parts[1:-1]:",
        "   n=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=d);os.close(d);d=n",
        "  f=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=d)",
        "  try:",
        "   s=os.fstat(f)",
        "   if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size<0 or s.st_size>limit: raise RuntimeError('controlled input extent differs')",
        "   chunks=[];left=s.st_size",
        "   while left:",
        "    chunk=os.read(f,min(left,65536))",
        "    if not chunk: raise RuntimeError('short controlled input')",
        "    chunks.append(chunk);left-=len(chunk)",
        "   t=os.fstat(f);current=os.stat(p.name,dir_fd=d,follow_symlinks=False)",
        "   if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns) or (s.st_dev,s.st_ino)!=(current.st_dev,current.st_ino): raise RuntimeError('controlled input changed')",
        "   return b''.join(chunks)",
        "  finally: os.close(f)", " finally: os.close(d)",
        "for name,path,digest in " + repr(modules) + ":",
        " raw=read_safe(path,1<<20)",
        " if hashlib.sha256(raw).hexdigest()!=digest: raise RuntimeError('controlled placement source changed')",
        " mod=types.ModuleType(name);mod.__file__=path;sys.modules[name]=mod;exec(compile(raw,path,'exec'),mod.__dict__)",
        "placement=sys.modules['placement']",
        "release=Path(" + repr(str(release)) + ")", "deadline=time.monotonic()+30",
        "while not release.exists():",
        " if os.getppid()!=" + str(os.getpid()) + " or time.monotonic()>deadline: raise RuntimeError('owner gate not released')",
        " time.sleep(.01)",
        "owner_bytes=read_safe(" + repr(str(owner_record)) + ",65536);owner=json.loads(owner_bytes)",
        "if hashlib.sha256(owner_bytes).hexdigest()!=read_safe(release,128).decode('ascii').strip() or owner['pid']!=os.getpid(): raise RuntimeError('owner gate identity differs')",
        "fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()",
        "if [owner['pgid'],owner['session'],owner['start_ticks']]!=[int(fields[2]),int(fields[3]),int(fields[19])]: raise RuntimeError('original owner process differs')",
        "def lower(kind,soft,hard):",
        " before=resource.getrlimit(kind)",
        " if not 0<soft<=hard or any(v!=resource.RLIM_INFINITY and v<hard for v in before): raise RuntimeError('inherited limit below admitted budget')",
        " resource.setrlimit(kind,(soft,hard));return list(before)",
        "as_before=lower(resource.RLIMIT_AS," + str(runtime_budget["address_space_bytes"]) + "," + str(runtime_budget["address_space_bytes"]) + ")",
        "cpu_before=lower(resource.RLIMIT_CPU," + str(runtime_budget["cpu_seconds"][0]) + "," + str(runtime_budget["cpu_seconds"][1]) + ")",
        "before=resource.getrlimit(resource.RLIMIT_FSIZE);value=min([64<<20]+[v for v in before if v!=resource.RLIM_INFINITY]);resource.setrlimit(resource.RLIMIT_FSIZE,(value,value))",
        "target=Path(" + repr(str(whole)) + ");data=read_safe(target,256<<20)",
        "if hashlib.sha256(data).hexdigest()!=" + repr(controlled["whole_sha256"]) + ": raise RuntimeError('peer candidate changed')",
        "image=os.memfd_create('rove4k-peer-whole',os.MFD_ALLOW_SEALING);os.fchmod(image,0o700);view=memoryview(data)",
        "while view:", " written=os.write(image,view)", " if written<=0: raise RuntimeError('short peer snapshot')", " view=view[written:]",
        "seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL;fcntl.fcntl(image,fcntl.F_ADD_SEALS,seals)",
        "if fcntl.fcntl(image,fcntl.F_GET_SEALS)&seals!=seals: raise RuntimeError('peer snapshot not sealed')",
        "os.set_inheritable(image,True)",
        "slot=json.loads(read_safe(" + repr(str(slot)) + ",65536))",
        "if slot!=" + repr(controlled["slot"]) + ": raise RuntimeError('controlled slot changed')",
        "record=placement.apply_slot(slot,cgroup=" + repr(controlled["cgroup"]) +
            ",saved_ancestor_cpus=" + repr(controlled["saved_cpus"]) +
            ",saved_ancestor_nodes=" + repr(controlled["saved_nodes"]) + ")",
        "record['runtime_limits']={'address_space':list(resource.getrlimit(resource.RLIMIT_AS)),'cpu':list(resource.getrlimit(resource.RLIMIT_CPU))};record['child_inherited_limits']={'address_space':as_before,'cpu':cpu_before}",
        "p=Path(" + repr(str(placement_record)) + ")",
        "with p.open('x') as stream:", " stream.write(json.dumps(record,sort_keys=True)+'\\n');stream.flush();os.fsync(stream.fileno())",
        "os.environ['TMPDIR']=" + repr(str(temporary)), "os.execve(image,[" + repr(str(whole)) + "],os.environ)", "",
    ))
    path.write_text(source)
    path.chmod(0o700)


def _write_launcher(path, whole, temporary, slot, placement_record, frozen_root, owner_record, release, *, runtime_budget=None, controlled=None):
    if controlled is not None:
        return _write_controlled_launcher(path, whole, temporary, slot, placement_record, frozen_root,
                                          owner_record, release, runtime_budget, controlled)
    source = "#!/usr/bin/python3 -I\n" + "\n".join((
        "import hashlib,json,os,resource,sys,time", "from pathlib import Path",
        "release=Path(" + repr(str(release)) + ")", "deadline=time.monotonic()+30",
        "while not release.exists():",
        " if os.getppid()!=" + str(os.getpid()) + " or time.monotonic()>deadline: raise RuntimeError('owner gate not released')",
        " time.sleep(.01)",
        "owner_bytes=Path(" + repr(str(owner_record)) + ").read_bytes()",
        "owner=json.loads(owner_bytes)",
        "if hashlib.sha256(owner_bytes).hexdigest()!=release.read_text().strip() or owner['pid']!=os.getpid(): raise RuntimeError('owner gate identity differs')",
        "fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()",
        "if [owner['pgid'],owner['session'],owner['start_ticks']]!=[int(fields[2]),int(fields[3]),int(fields[19])]: raise RuntimeError('original owner process differs')",
        "sys.path.insert(0," + repr(str(frozen_root / "engines/experiments/strength")) + ")",
        "import placement", "def cap(kind,ceiling):",
        " value=min([ceiling]+[v for v in resource.getrlimit(kind) if v!=resource.RLIM_INFINITY])",
        " resource.setrlimit(kind,(value,value))",
        ("pass" if runtime_budget is None else "import peer_runtime as budget_runtime"),
        ("cap(resource.RLIMIT_AS,4<<30)" if runtime_budget is None else
         "as_before=budget_runtime.checked_child_limit(resource,resource.RLIMIT_AS," + str(runtime_budget["address_space_bytes"]) + "," + str(runtime_budget["address_space_bytes"]) + ")"),
        ("cap(resource.RLIMIT_CPU,180)" if runtime_budget is None else
         "cpu_before=budget_runtime.checked_child_limit(resource,resource.RLIMIT_CPU," + str(runtime_budget["cpu_seconds"][0]) + "," + str(runtime_budget["cpu_seconds"][1]) + ")"),
        "cap(resource.RLIMIT_FSIZE,64<<20)",
        "slot=json.loads(Path(" + repr(str(slot)) + ").read_text())",
        "record=placement.apply_slot(slot)",
        ("pass" if runtime_budget is None else
         "record['runtime_limits']={'address_space':list(resource.getrlimit(resource.RLIMIT_AS)),'cpu':list(resource.getrlimit(resource.RLIMIT_CPU))};record['child_inherited_limits']={'address_space':as_before,'cpu':cpu_before}"),
        "p=Path(" + repr(str(placement_record)) + ")",
        "with p.open('x') as stream:", " stream.write(json.dumps(record,sort_keys=True)+'\\n');stream.flush();os.fsync(stream.fileno())",
        "os.environ['TMPDIR']=" + repr(str(temporary)), "os.execv(" + repr(str(whole)) + ",[" + repr(str(whole)) + "])", "",
    ))
    path.write_text(source)
    path.chmod(0o700)


def _finish_peer(owned, seconds=20):
    # Permit upstream compiler diagnostics on stderr. Keep the original
    # unreaped leader until its delayed cleanup child has physically settled.
    deadline = time.monotonic() + owned.budget.left(seconds)
    others_seen, exited_with_others = set(), False
    while True:
        exited, others = owned.exited(), owned.group_others()
        others_seen.update(row["pid"] for row in others)
        exited_with_others |= exited and bool(others)
        if exited and not others:
            break
        require(time.monotonic() < deadline, "peer or delayed cleanup child did not physically settle")
        time.sleep(.01)
    owned.pre_reap_other_members = owned.group_others()
    owned.process.wait(timeout=owned.budget.left(3))
    owned.reaped = True
    for reader in (owned.stdout, owned.stderr):
        reader.thread.join(timeout=owned.budget.left(3))
        require(not reader.thread.is_alive() and reader.done and not reader.error, "peer output reader did not join")
    require(owned.process.returncode == 0, "peer exited unsuccessfully")
    owned.finished = True
    return {"returncode": 0, "readers_joined": True, "reaped": True, "forced_cleanup": False,
            "original_identity_retained_until_other_members_absent": True,
            "other_members_observed": sorted(others_seen), "leader_exited_with_other_members": exited_with_others,
            "stderr_bytes": len(owned.stderr.bytes()), "stderr_sha256": sha(owned.stderr.bytes())}


def _best_lines(owned):
    return [line for line in owned.stdout.bytes().splitlines() if line.startswith(b"bestmove ")]


def _replay(oracle, moves):
    board = oracle.Board.from_fen()
    for move in moves:
        board = board.play(move)
    return board


def checked_best(line, board):
    fields = line.split()
    require(len(fields) in (2, 4) and fields[0] == b"bestmove", "malformed bestmove line")
    move = fields[1].decode("ascii")
    require(move in {str(value) for value in board.legal_moves()}, "peer emitted an illegal bestmove after full startpos replay")
    if len(fields) == 4:
        require(fields[2] == b"ponder" and fields[3].decode("ascii") in {str(value) for value in board.play(move).legal_moves()},
                "malformed or illegal optional ponder move")
    return move


def _worker_evidence(pid, tid, *, proc=Path("/proc")):
    """Bind a worker mask and CPU ticks to the same Linux task identity."""
    stat = proc / str(pid) / "task" / str(tid) / "stat"
    before = stat.read_text().rsplit(")", 1)[1].split()
    affinity = sorted(os.sched_getaffinity(tid))
    after = stat.read_text().rsplit(")", 1)[1].split()
    require(len(before) > 19 and len(after) > 19 and before[19] == after[19],
            "worker identity changed during affinity observation")
    first, last = int(before[11]) + int(before[12]), int(after[11]) + int(after[12])
    require(last >= first, "worker CPU ticks went backwards")
    return {"tid": tid, "start_ticks": int(after[19]), "cpus": affinity,
            "cpu_ticks_first": first, "cpu_ticks_last": last}


def _search(owned, scope, oracle, moves, label, *, workers=None, cpus=(), capture_smt=False):
    board = _replay(oracle, moves)
    legal = {str(move) for move in board.legal_moves()}
    require(legal, "qualification fixture must have legal replies")
    previous = len(_best_lines(owned))
    owned.send(("position startpos" + (" moves " + " ".join(moves) if moves else "") + "\n").encode())
    clock = 60000 if workers is not None else 1000
    before = scope.task_snapshot(owned.process.pid)
    owned.send(f"go wtime {clock} btime {clock} winc 0 binc 0\n".encode())
    allowance = 35 if workers is not None else 5
    started = time.monotonic()
    deadline = started + owned.budget.left(allowance)
    samples, positive, all_workers, worker_observations = [], set(), set(), {}
    while len(_best_lines(owned)) == previous:
        require(time.monotonic() < deadline and not owned.exited(), "peer clocked search exceeded actual deadline")
        current = scope.task_snapshot(owned.process.pid)
        active = {tid: value for tid, value in current.items() if tid != owned.process.pid}
        if workers is not None:
            all_workers.update(active)
            require(len(active) <= workers and len(all_workers) <= workers, "peer created more workers than TEST profile")
            for tid, row in active.items():
                try:
                    actual_cpus = set(os.sched_getaffinity(tid))
                except ProcessLookupError:
                    continue
                require(actual_cpus == set(cpus), "worker escaped inherited CPU slot")
                if capture_smt:
                    try:
                        evidence = _worker_evidence(owned.process.pid, tid)
                    except (FileNotFoundError, ProcessLookupError):
                        continue
                    require(evidence["cpus"] == sorted(cpus), "worker affinity changed during evidence capture")
                    previous_evidence = worker_observations.get(tid)
                    if previous_evidence is not None:
                        require(previous_evidence["start_ticks"] == evidence["start_ticks"],
                                "worker TID was reused during one search")
                        require(evidence["cpu_ticks_first"] >= previous_evidence["cpu_ticks_last"],
                                "worker CPU ticks regressed between observations")
                        previous_evidence["cpu_ticks_last"] = evidence["cpu_ticks_last"]
                    else:
                        worker_observations[tid] = evidence
                if row["cpu_ticks"] > before.get(tid, {}).get("cpu_ticks", 0):
                    positive.add(tid)
            if len(samples) < 256:
                samples.append({"elapsed_seconds": time.monotonic() - started, "tasks": current})
        time.sleep(.02)
    lines = _best_lines(owned)
    require(len(lines) == previous + 1, "clocked search emitted duplicate bestmove")
    move = checked_best(lines[-1], board)
    ready_count = owned.stdout.bytes().splitlines().count(b"readyok") + 1
    owned.send(b"isready\n")
    owned.wait_line(b"readyok", ready_count)
    require(owned.stdout.bytes().splitlines().count(b"readyok") == ready_count, "duplicate readyok response")
    require(len(_best_lines(owned)) == previous + 1, "late duplicate bestmove after ready")
    if workers is not None:
        require(len(all_workers) == workers and len(positive) == workers, "not every declared worker used positive actual CPU")
    result = {"label": label, "moves": moves, "bestmove": move, "legal_reply_count": len(legal), "clock_ms": clock,
              "worker_ids": sorted(all_workers), "positive_cpu_worker_ids": sorted(positive), "samples": samples}
    if capture_smt:
        result["worker_affinity_evidence"] = [worker_observations[tid] for tid in sorted(worker_observations)]
        result["worker_affinity_evidence_complete"] = set(worker_observations) == all_workers and all(
            row["cpu_ticks_last"] > row["cpu_ticks_first"] for row in worker_observations.values())
    return result


def _observe_image(owned, scope, native, elf, symbol, layout, tmpdir, *, wait_cleanup=True):
    deadline = time.monotonic() + owned.budget.left(10)
    while True:
        snapshot = scope.image_snapshot(owned.process.pid, native["sha256"])
        require(not owned.exited(), "peer exited while checking live cleanup")
        require(Path(snapshot["path"]).parent == tmpdir, "JIT compiler escaped owned temporary directory")
        if not snapshot["path_exists"] or not wait_cleanup:
            break
        require(time.monotonic() < deadline, "peer JIT temporary image was not unlinked while live")
        time.sleep(.025)
    if not snapshot["path_exists"]:
        require(not list(tmpdir.iterdir()), "peer left unexpected temporary files while alive")
    snapshot["tt"] = runtime_tt(owned.process.pid, elf, symbol, layout["tt_bytes"])
    return snapshot


def _tt_numa_after_search(pid, elf, symbol, tt_bytes, expected_owner, original_pointer, *, proc=Path("/proc")):
    """Observe VMAs overlapping TT after GO; these may also contain other data."""
    require(process_identity(pid) == expected_owner, "engine owner changed before NUMA observation")
    tt = runtime_tt(pid, elf, symbol, tt_bytes)
    require(tt["pointer"] == original_pointer, "TT pointer changed before NUMA observation")
    starts = {row["start"] for row in tt["mappings"]}
    rows = []
    for line in (proc / str(pid) / "numa_maps").read_text().splitlines():
        fields = line.split()
        if not fields or not re.fullmatch(r"[0-9a-fA-F]+", fields[0]):
            continue
        start = int(fields[0], 16)
        if start in starts:
            pages = {int(node): int(count) for node, count in re.findall(r"\bN(\d+)=(\d+)", line)}
            rows.append({"mapping_start": start, "node_pages": pages, "raw": line})
    require(process_identity(pid) == expected_owner, "engine owner changed during NUMA observation")
    return {"owner": expected_owner, "tt_pointer": tt["pointer"], "tt_bytes": tt_bytes,
            "tt_mappings": tt["mappings"], "tt_overlapping_vmas": rows,
            "matching_vma_starts": sorted(row["mapping_start"] for row in rows),
            "observed_page_nodes": sorted({node for row in rows for node in row["node_pages"]}),
            "all_mapping_starts_observed": {row["mapping_start"] for row in rows} == starts,
            "scope": "after GO, VMAs overlapping TT; may include non-TT pages; no remote-access or NUMA efficiency claim"}


def _dependencies_live(pid, needed):
    expected = {name.split(".so", 1)[0] for name in needed}
    rows = []
    for row in mappings(pid):
        path = row["path"].removesuffix(" (deleted)")
        if "x" not in row["permissions"] or not path.startswith("/"):
            continue
        if path.startswith("/tmp/rove4k-peer-"):
            continue
        name = Path(path).name
        require(name.startswith("ld-linux-") or name.split(".so", 1)[0] in expected, "unexpected executable dependency mapping")
        resolved = Path(path).resolve(strict=True)
        require(str(resolved).startswith(("/usr/lib/", "/lib/", "/lib64/")), "dependency is outside system runtime directories")
        rows.append({"path": str(resolved), "sha256": sha(resolved.read_bytes())})
    require(rows, "actual executable system dependencies not observed")
    return rows


_CONTROLLED_PEER_TOKEN = object()


class _ControlledPeer:
    """One manager-owned diagnostic group, never scored authority."""

    def __init__(self, owner, artifact, reference_sha, candidate_sha256):
        try:
            from . import functional_probe_session
        except ImportError:
            import functional_probe_session
        require(type(owner) is functional_probe_session.OwnedFunctionalProbe,
                "the original owned functional probe is required")
        self.token = _CONTROLLED_PEER_TOKEN
        self.owner, self.artifact = owner, artifact
        self.reference_sha, self.candidate_sha256 = reference_sha, candidate_sha256
        self.slot = json.loads(json.dumps(owner.slot.to_record()))
        self.cgroup = json.loads(json.dumps(owner.cgroup))
        self.launch_record = {"cgroup": self.cgroup,
                              "slot": self.slot,
                              "saved_cpus": list(owner.saved_ancestor_cpus),
                              "saved_nodes": list(owner.saved_ancestor_nodes),
                              "whole_sha256": artifact.sha256}
        self.fresh_checked = False


def _controlled_peer_events(context):
    try:
        from . import functional_uci_probe
    except ImportError:
        import functional_uci_probe
    return functional_uci_probe._events(Path(context.cgroup["path"]))


def _check_controlled_sources(context):
    """Detect changed source bytes, without claiming loaded code attestation."""
    require(isinstance(getattr(context, "source_pins", None), dict) and
            set(context.source_pins) == set(SOURCE_FILES + LEAGUE_SOURCE_FILES + CONTROLLED_SOURCE_FILES),
            "controlled peer source closure is incomplete")
    for relative, pin in context.source_pins.items():
        current = ordinary(ROOT / relative).replace(b"\r\n", b"\n")
        frozen = ordinary(context.frozen / relative).replace(b"\r\n", b"\n")
        require(len(current) == len(frozen) == pin["bytes"] and
                sha(current) == sha(frozen) == pin["sha256"],
                "controlled peer source closure changed: " + relative)


def _controlled_peer_quiescent(context):
    """An owned leaf may retain accounting, but must contain no live tasks."""
    try:
        from . import placement, memory_observation
    except ImportError:
        import placement, memory_observation
    placement.verify_cgroup_live(context.cgroup)
    path = Path(context.cgroup["path"])
    events = memory_observation._file(path / "cgroup.events")
    procs = memory_observation._file(path / "cgroup.procs")
    current = memory_observation._file(path / "memory.current").strip()
    require(events.splitlines().count("populated 0") == 1 and not procs.strip() and current.isdecimal(),
            "controlled peer original cgroup is not quiescent")
    return int(current)


def _controlled_peer_preflight(context, layout):
    """Re-read the actual owned leaf before each peer launch; no reservation."""
    try:
        from . import placement, peak_capacity, peak_probe_session, memory_observation
    except ImportError:
        import placement, peak_capacity, peak_probe_session, memory_observation
    group_path = Path(context.cgroup["path"])
    require(group_path.is_absolute() and group_path.is_relative_to(Path("/sys/fs/cgroup")) and
            group_path != Path("/sys/fs/cgroup"), "controlled peer requires a visible cgroup2 leaf")
    manager = context.owner.manager
    require(type(manager) is placement.CgroupSlots and manager._root_fd is not None and
            manager._parent_fd is not None and not manager._closed and
            (group_path, context.cgroup["device"], context.cgroup["inode"]) in manager.created and
            group_path.parent == manager.parent,
            "controlled peer lost its original anchored cgroup owner")
    manager._check_anchored_parent()
    peak_probe_session._require_delegated_root(group_path)
    group = placement.verify_cgroup_live(context.cgroup)
    require(group["cpus"] == context.slot["cpus"] and group["memory_nodes"] == context.slot["memory_nodes"],
            "controlled peer cgroup masks changed")
    if not context.fresh_checked:
        peak_capacity._require_empty(group_path)
        context.fresh_checked = True
    current = _controlled_peer_quiescent(context)
    workers = layout["workers"]
    required = layout["tt_bytes"] + max(768 << 20, workers * (16 << 20)) + (256 << 20)
    require(group["memory_max"] >= required, "controlled peer cgroup memory limit is insufficient")
    capacity = memory_observation.observe_capacity([context.slot], group_path, mask_scope="delegated-only")
    return {"required_bytes": required, "retained_cgroup_bytes": current, "capacity": capacity,
            "current_availability_enforced": False,
            "scope": "point-in-time visible capacity, not a physical reservation or score admission"}


@owned_signals
def qualify_peer_controlled(*, root, campaign, candidate_path, candidate_sha256, profile,
                            artifact_id, reference, reference_sha, out, wall_seconds=180):
    """Run the full peer lifecycle under a fresh owned group, without league admission.

    The existing diagnostic manager owns and removes its original cgroup. Its
    point-in-time checks do not reserve RAM, authenticate the host, exclude
    hidden ancestors or establish recovery after supervisor failure.
    """
    try:
        from . import diagnostic_candidates, functional_probe_session
    except ImportError:
        import diagnostic_candidates, functional_probe_session
    rows, digest = diagnostic_candidates.read_candidates(candidate_path, candidate_sha256, profile,
                                                           allow_single=True)
    selected = [row for row in rows if row["artifact"].id == artifact_id]
    require(len(selected) == 1 and digest == candidate_sha256 and
            selected[0]["artifact"].family in ("ice4", "c4ke") and
            selected[0]["evidence"].get("kind") == "peer-reference-v1" and
            selected[0]["evidence"].get("reference_sha256") == reference_sha,
            "controlled peer requires one matching source-bound peer reference")
    require(profile != "test-p192" or selected[0]["artifact"].tt_bytes == 192 << 30,
            "P192 peer diagnostic requires the requested 192 GiB TT, not the current 128 GiB peer layout")
    global CONSTRUCTING_OWNED, DEFERRED_SIGNAL
    CONSTRUCTING_OWNED = True
    try:
        owner = functional_probe_session.OwnedFunctionalProbe.create(
            root=root, campaign=campaign, candidate_path=candidate_path, candidate_sha256=candidate_sha256,
            profile=profile, artifact_id=artifact_id, out=out, wall_seconds=wall_seconds)
        result, original = None, None
        try:
            CONSTRUCTING_OWNED = False
            if DEFERRED_SIGNAL is not None:
                pending, DEFERRED_SIGNAL = DEFERRED_SIGNAL, None
                raise KeyboardInterrupt("controlled peer owner signal " + str(pending))
            context = _ControlledPeer(owner, selected[0]["artifact"], reference_sha, candidate_sha256)
            owner._attempted = owner._running = True
            result = qualify_peer(reference, out, context.slot, reference_sha=reference_sha,
                                  allow_functional=True, wall_seconds=wall_seconds, _controlled=context)
            require(isinstance(result, dict) and result.get("qualified") is False and
                    result.get("admission") is None and isinstance(result.get("record"), dict) and
                    result["record"].get("complete") is False and
                    result["record"].get("controlled_diagnostic", {}).get("authorizes_go") is False,
                    "controlled diagnostic cannot grant league admission")
        except BaseException as error:
            original = error
        finally:
            CONSTRUCTING_OWNED = True
            try:
                owner._running = False
                try:
                    errors = owner.close()
                except BaseException as cleanup:
                    errors = [{"error": str(cleanup)}]
            finally:
                CONSTRUCTING_OWNED = False
    finally:
        CONSTRUCTING_OWNED = False
    if DEFERRED_SIGNAL is not None and original is None:
        pending, DEFERRED_SIGNAL = DEFERRED_SIGNAL, None
        original = KeyboardInterrupt("controlled peer cleanup signal " + str(pending))
    if errors:
        raise functional_probe_session.FunctionalCleanupFailure(
            "controlled peer cgroup cleanup requires attention", errors=errors, owner=owner,
            original=original) from original
    if original is not None:
        raise original
    return result


@owned_signals
def qualify_peer(reference, out, slot, *, reference_sha=None, allow_functional=False, wall_seconds=180,
                 _controlled=None):
    require(sys.platform == "linux", "peer execution requires Linux")
    require(not any(os.environ.get(name) for name in ("LD_PRELOAD", "LD_AUDIT", "LD_LIBRARY_PATH")),
            "qualification requires the declared system loader without external interposition")
    peers = sibling("peers")
    reference = Path(reference)
    require(reference.is_absolute() and not any((parent / ".git").exists() for parent in reference.parents),
            "peer reference must be external to Git")
    ref, ref_sha = read_record(reference, reference_sha)
    require(ref.get("format") == "rove4k-peer-reference-v1" and ref.get("complete") is True and ref.get("engines_executed") == 0,
            "completed engine-free reference preparation required")
    reference_frozen = Path(reference).parent / "source-closure"
    large_profile = ref["resources"]["id"] in ("test-p16", "test-p192")
    require(not large_profile or allow_functional,
            "SMT TEST runtime requires explicit functional-only opt-in; scored placement remains unqualified")
    # Large profiles require the owner that binds the cgroup, source and slot.
    # This identity check does not reserve memory or inspect current free RAM.
    require(not large_profile or (isinstance(_controlled, _ControlledPeer) and
                                   _controlled.token is _CONTROLLED_PEER_TOKEN),
            "SMT peer launch requires controlled cgroup ownership and source identity")
    _verify_frozen(reference_frozen, ref["source_inputs"], league_required=large_profile)
    admitted = validate_build(ref["build"]["path"], ref["build"]["sha256"])
    require(admitted["peer"] == ref["peer"] and admitted["layout"] == ref["resources"], "reference resource identity differs")
    if large_profile:
        require(ref["resources"]["id"] != "test-p192" or ref["resources"]["tt_bytes"] == 192 << 30,
                "P192 peer diagnostic requires the requested 192 GiB TT")
        require(_controlled.reference_sha == ref_sha and
                _controlled.artifact.family == admitted["peer"] and
                _controlled.artifact.profile == ref["resources"]["id"] and
                _controlled.artifact.tt_bytes == ref["resources"]["tt_bytes"] and
                _controlled.artifact.sha256 == admitted["record"]["whole"]["sha256"] and
                _controlled.artifact.native_sha256 == ref["native"]["sha256"] and
                json.loads(json.dumps(slot)) == _controlled.slot,
                "controlled peer source, resource or slot differs from the owned candidate")
    require(ref["native"]["path"] == str(reference.parent / "reference-1"), "native reference path is outside bound output")
    native = bound(ref["native"]["path"], ref["native"])
    require(ref["entry_size_compile_assertion"] is True and len(ref["native_attempts"]) == 3,
            "two actual native reproductions and inert entry assertion required")
    for index, attempt in enumerate(ref["native_attempts"], 1):
        require(attempt["path"] == str(reference.parent / ("reference-" + str(index))), "native attempt path is outside bound output")
        require(bound(attempt["path"], attempt) == native, "native reproduction changed")
    elf = Elf64(native)
    require(elf.dependencies() == ref["dependencies"] and elf.pointer_symbol(ref["tt_symbol"]) == ref["tt_symbol_value"],
            "ELF reference metadata differs")
    require(ref["tt_symbol"] == admitted["tt_symbol"] and bound(Path(reference).parent / "main.cpp", ref["source"]) == admitted["source"],
            "exact native stdin source differs from decoded whole payload")
    topology_module = sibling("topology")
    topology = topology_module.Topology.snapshot()
    placement = validate_slot(topology, slot, ref["resources"], allow_functional=allow_functional)
    runtime_budget = None
    if large_profile:
        runtime_budget = observed_peer_runtime_budget(ref["resources"], cpus=slot["cpus"], wall_seconds=wall_seconds)
    out = peers.external_new(out)
    out.mkdir(parents=True)
    runtime_inputs = _freeze(out, league_required=large_profile, controlled_required=large_profile)
    frozen = out / "source-closure"
    if large_profile:
        _controlled.source_pins, _controlled.frozen = runtime_inputs, frozen
        _controlled.launch_record["source_pins"] = runtime_inputs
        _check_controlled_sources(_controlled)
    registry = sibling("registry", frozen)
    record = admitted["record"]
    artifact = registry.Artifact(id=f'{ref["peer"]}-{ref["resources"]["id"]}-{record["whole"]["sha256"][:8]}-{ref["native"]["sha256"][:8]}',
        family=ref["peer"], path=Path(record["whole"]["path"]), purpose="test", profile=ref["resources"]["id"],
        workers=ref["resources"]["workers"], tt_bytes=ref["resources"]["tt_bytes"], entry_bytes=8,
        representation="source-jit", full=True, sha256=record["whole"]["sha256"], whole_bytes=record["whole"]["bytes"],
        native_sha256=ref["native"]["sha256"])
    artifact.verify_bytes()
    artifact_record = {**artifact.identity(), "path": str(artifact.path)}
    peers.write_json(out / "artifact.json", artifact_record)
    report = {"format": "rove4k-qualification-v1", "division": "general4k", "complete": False,
              "artifact": artifact.identity(), "reference": {"path": str(reference), "sha256": ref_sha},
              "checks": {name: False for name in registry.CHECKS}, "observations": {}, "failures": [], "sessions": [],
              "source_inputs": runtime_inputs, "reference_source_inputs": ref["source_inputs"],
              "topology": topology.to_record(), "placement": placement, "runtime_budget": runtime_budget,
              "execution_context": {"host_only_functional_validation": True, "scored_envelope": False,
                  "controller_reserve_validated": False,
                  "unused_physical_cores_in_allowed_topology": len({cpu.physical for cpu in topology.cpus}) - placement["physical_cores"]},
              "scope": "host-bound full TEST peer functional/resource qualification; no controller reserve, scored envelope, W256/256GiB, strength or scaling claim"}
    if large_profile:
        report["slot"] = slot
        report["controlled_diagnostic"] = {"cgroup": _controlled.cgroup,
            "candidate_set_sha256": _controlled.candidate_sha256,
            "physical_memory_reserved": False, "hidden_ancestors_excluded": False,
            "restart_ownership_proven": False, "loaded_code_identity_proven": False,
            "authorizes_go": False}
    report["checks"].update(reproduction=True, size=True)
    owned_helper = load("peer_owned_helper", frozen / "engines/compact/tiny-entry-d/verify.py")
    scope = load("peer_scope_helper", frozen / "engines/experiments/tcec-scope/verify.py")
    oracle = load("peer_independent_oracle", frozen / "engines/tests/chess_oracle.py")
    budget = owned_helper.Budget(wall_seconds)
    slot_path = out / "slot.json"
    peers.write_json(slot_path, slot)
    temporary = []
    try:
        for label in ("cold", "warm", "active-quit", "active-eof"):
            session = {"label": label, "searches": []}
            report["sessions"].append(session)
            session_budget = (observed_peer_runtime_budget(ref["resources"], cpus=slot["cpus"], wall_seconds=wall_seconds)
                              if large_profile else None)
            if large_profile:
                _check_controlled_sources(_controlled)
                session["controlled_preflight"] = _controlled_peer_preflight(_controlled, ref["resources"])
                session["memory_events_before"] = _controlled_peer_events(_controlled)
                session["runtime_budget"] = session_budget
            directory = out / label
            directory.mkdir()
            tmpdir = Path("/tmp") / ("rove4k-peer-" + sha(str(out).encode())[:16] + "-" + label)
            require(not tmpdir.exists() and not tmpdir.is_symlink(), "owned temporary namespace already exists")
            tmpdir.mkdir(mode=0o700)
            identity = tmpdir.stat()
            temporary.append((tmpdir, identity.st_dev, identity.st_ino))
            whole = directory / "whole"
            whole.write_bytes(admitted["whole"])
            whole.chmod(0o700)
            launcher = directory / "launch"
            placement_record = directory / "placement.json"
            owner_record, release = directory / "owner.json", directory / "owner-release"
            _write_launcher(launcher, whole, tmpdir, slot_path, placement_record, frozen, owner_record, release,
                            runtime_budget=session_budget,
                            controlled=_controlled.launch_record if large_profile else None)
            owned = None
            try:
                started = time.monotonic()
                owned = construct_owned(owned_helper, launcher, directory, budget)
                session["owner"] = {**process_identity(owned.process.pid), "whole_sha256": artifact.sha256,
                                    "runtime_native_sha256": artifact.native_sha256, "role": "peer-qualification"}
                require(session["owner"]["pgid"] == session["owner"]["session"] == owned.process.pid,
                        "owned peer does not have an original isolated process group/session")
                owner_bytes = (json.dumps(session["owner"], sort_keys=True) + "\n").encode()
                durable_new(owner_record, owner_bytes)
                durable_new(release, (sha(owner_bytes) + "\n").encode())
                owned.send(b"uci\n")
                owned.stdout.until(lambda data: b"uciok" in data.splitlines(), budget, seconds=60)
                owned.send(b"isready\n")
                owned.wait_line(b"readyok")
                require(owned.stdout.bytes().splitlines().count(b"uciok") == 1
                        and owned.stdout.bytes().splitlines().count(b"readyok") == 1 and not _best_lines(owned),
                        "duplicate startup protocol response or unsolicited bestmove")
                session["image"] = _observe_image(owned, scope, ref["native"], elf, ref["tt_symbol"], ref["resources"], tmpdir,
                                                   wait_cleanup=label in ("cold", "warm"))
                session["startup_ms"] = (time.monotonic() - started) * 1000
                require(session["startup_ms"] <= 60000, "aggregate complete startup exceeds 60 seconds")
                preexec, _ = read_record(placement_record)
                require(preexec["effective_cpus"] == sorted(slot["cpus"]), "pre-exec placement did not take effect")
                if large_profile:
                    require(preexec.get("requested_policy") == slot["policy"] and
                            preexec.get("requested_nodes") == sorted(slot["memory_nodes"]),
                            "pre-exec slot policy or nodes changed")
                if session_budget is not None:
                    expected_limits = {"address_space": [session_budget["address_space_bytes"]] * 2,
                                       "cpu": session_budget["cpu_seconds"]}
                    require(preexec.get("runtime_limits") == expected_limits,
                            "actual peer pre-exec limits differ from admitted resource budget")
                if slot.get("policy", "inherit") != "inherit":
                    policy = preexec["observed_policy"]
                    require(preexec["fallback"] is None and policy.get("available") is True
                            and policy.get("mode") == {"default": 0, "interleave": 3}[slot["policy"]]
                            and (slot["policy"] == "default" or set(policy.get("nodes", [])) == set(slot["memory_nodes"])),
                            "explicit task-memory policy could not actually be applied/observed")
                require(set(os.sched_getaffinity(owned.process.pid)) == set(slot["cpus"]), "actual engine CPU mask differs")
                session["preexec_placement"] = preexec
                session["startup_group_other_members"] = owned.group_others()
                session["dependencies"] = _dependencies_live(owned.process.pid, ref["dependencies"]["needed"])
                session["numa_maps_observation"] = Path(f"/proc/{owned.process.pid}/numa_maps").read_text()
                session["multi_node_validated"] = False
                if label == "cold":
                    owned.send(b"ucinewgame\n")
                    session["searches"].append(_search(owned, scope, oracle, [], "white-startpos",
                        workers=artifact.workers, cpus=slot["cpus"], capture_smt=large_profile))
                    if large_profile:
                        session["post_go_tt_numa"] = _tt_numa_after_search(
                            owned.process.pid, elf, ref["tt_symbol"], ref["resources"]["tt_bytes"],
                            {key: session["owner"][key] for key in ("pid", "pgid", "session", "start_ticks")},
                            session["image"]["tt"]["pointer"])
                    session["searches"].append(_search(owned, scope, oracle, ["e2e4"], "black-startpos"))
                    for fixture, moves, _board in scope.promotion_fixtures(oracle):
                        session["searches"].append(_search(owned, scope, oracle, moves, fixture))
                    before_idle = scope.task_snapshot(owned.process.pid)
                    time.sleep(min(.1, budget.left(.1)))
                    after_idle = scope.task_snapshot(owned.process.pid)
                    require(set(after_idle) == {owned.process.pid} and set(before_idle) == {owned.process.pid}, "peer has active idle workers")
                    require(after_idle[owned.process.pid]["cpu_ticks"] - before_idle[owned.process.pid]["cpu_ticks"] <= 1,
                            "peer consumed search CPU without GO")
                    session["idle"] = {"before": before_idle, "after": after_idle}
                elif label == "warm":
                    session["searches"].append(_search(owned, scope, oracle, [], "warm-white"))
                else:
                    owned.send(b"position startpos moves e2e4\ngo wtime 1000 btime 1000 winc 0 binc 0\n")
                    time.sleep(min(.025, budget.left(.025)))
                if label == "active-eof":
                    owned.close_input()
                else:
                    owned.send(b"quit\n")
                session["finish"] = _finish_peer(owned)
                if label.startswith("active-"):
                    board = _replay(oracle, ["e2e4"])
                    lines = _best_lines(owned)
                    require(len(lines) <= 1, "closing GO emitted duplicate bestmove")
                    for line in lines:
                        checked_best(line, board)
                    session["closing_bestmove_count"] = len(lines)
            finally:
                if owned is not None:
                    session["cleanup"] = owned.cleanup()
                    require(session["cleanup"]["owned_group_absent"] and session["cleanup"]["readers_joined"]
                            and not session["cleanup"]["errors"], "peer cleanup did not physically settle")
                if large_profile:
                    after = _controlled_peer_events(_controlled)
                    session["memory_events_after"] = after
                    require(all(after[name] == session["memory_events_before"][name]
                                for name in ("oom", "oom_kill")), "peer cgroup observed an OOM event")
                    _controlled_peer_quiescent(_controlled)
                    _check_controlled_sources(_controlled)
        observations = report["observations"]
        observations.update(startup_ms=max(row["startup_ms"] for row in report["sessions"]), workers=artifact.workers,
            positive_cpu_workers=len(report["sessions"][0]["searches"][0]["positive_cpu_worker_ids"]),
            tt_bytes=artifact.tt_bytes, runtime_native_sha256=artifact.native_sha256,
            temporary_cleanup_while_live=all(not row["image"]["path_exists"] for row in report["sessions"][:2]),
            nbrq_replay=True, promotion_generation_policy="queen-only", physical_cores=placement["physical_cores"],
            logical_cpus=placement["logical_cpus"], multi_node_validated=False,
            compiler=ref["compiler"], native_reference_host_scope="must regenerate and requalify for a different compiler/CPU host")
        if large_profile:
            report["shared_smt_evidence"] = registry.smt_runtime_evidence(report, artifact)
        require(any(row["finish"]["leader_exited_with_other_members"] for row in report["sessions"] if row["label"].startswith("active-")),
                "actual delayed cleanup child settlement after leader exit was not observed")
        report["checks"].update({name: True for name in registry.CHECKS})
        report["checks"]["placement"] = placement["qualified"]
        report["checks"]["resources"] = placement["qualified"]
        if not placement["qualified"]:
            report["failures"].append({"scope": "placement", "message": "functional-only run lacks named physical TEST slot"})
    except BaseException as error:
        report["failures"].append({"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        for remaining in list(owned_helper.OWNED):
            try:
                result = remaining.cleanup()
                report.setdefault("recovered_constructor_handles", []).append(result)
            except BaseException as error:
                report["failures"].append({"scope": "cleanup", "message": str(error)})
        for path, device, inode in temporary:
            try:
                actual = path.stat()
                require(not path.is_symlink() and (actual.st_dev, actual.st_ino) == (device, inode), "temporary directory identity changed")
                path.rmdir()  # Only the exact empty directory owned by this run.
            except (OSError, ValueError) as error:
                report["failures"].append({"scope": "cleanup", "path": str(path), "message": str(error)})
                report["checks"]["cleanup"] = False
        if large_profile:
            report["functional_runtime_complete"] = (not any(row.get("scope") != "placement" for row in report["failures"])
                and all(value is True for name, value in report["checks"].items() if name not in ("placement", "resources")))
        report["complete"] = not report["failures"] and all(report["checks"].values())
        digest = peers.write_json(out / "qualification.json", report)
    admission = registry.admit_to_test_league(artifact, out / "qualification.json", digest) if report["complete"] else None
    return {"path": str(out / "qualification.json"), "sha256": digest, "artifact": str(out / "artifact.json"),
            "qualified": report["complete"], "admission": admission, "record": report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "qualify", "qualify-controlled"))
    parser.add_argument("--build", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--manifest-sha")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--slot", type=Path)
    parser.add_argument("--cpu", type=int, default=5)
    parser.add_argument("--wall-seconds", type=int, default=180)
    parser.add_argument("--allow-functional", action="store_true")
    parser.add_argument("--root", type=Path, help="original delegated cgroup2 root for a controlled diagnostic")
    parser.add_argument("--campaign")
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--candidates-sha256")
    parser.add_argument("--profile", choices=("test-p16", "test-p192"))
    parser.add_argument("--artifact-id")
    args = parser.parse_args()
    require(0 <= args.cpu and 0 < args.wall_seconds <= 600, "bounded CPU/wall configuration required")
    if args.action == "prepare":
        require(args.build is not None, "prepare requires --build")
        result = prepare_reference(args.build, args.out, manifest_sha=args.manifest_sha, cpu=args.cpu, timeout=args.wall_seconds)
    elif args.action == "qualify":
        require(args.reference is not None and args.slot is not None, "qualify requires --reference and --slot")
        slot, _ = read_record(args.slot)
        result = qualify_peer(args.reference, args.out, slot, reference_sha=args.manifest_sha,
                              allow_functional=args.allow_functional, wall_seconds=args.wall_seconds)
    else:
        require(args.reference is not None and args.manifest_sha is not None and args.root is not None and
                args.campaign is not None and args.candidates is not None and args.candidates_sha256 is not None and
                args.profile is not None and args.artifact_id is not None,
                "controlled peer qualification requires pinned candidate and reference plus an owned cgroup root")
        result = qualify_peer_controlled(root=args.root, campaign=args.campaign,
            candidate_path=args.candidates, candidate_sha256=args.candidates_sha256,
            profile=args.profile, artifact_id=args.artifact_id, reference=args.reference,
            reference_sha=args.manifest_sha, out=args.out, wall_seconds=args.wall_seconds)
    print(json.dumps({key: value for key, value in result.items() if key != "record"}, sort_keys=True))


if __name__ == "__main__":
    main()
