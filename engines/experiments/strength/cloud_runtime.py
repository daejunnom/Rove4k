#!/usr/bin/env python3
"""EC2 consumer of an immutable, *unqualified* source seed.

The seed is transport, never league admission.  The source CI identity and the
EC2 consumer are different authorities.  In particular this module never sets
GitHub environment variables and never replaces a producer native expectation.
The only runtime-image authority is the validated CloudRuntimeReference below.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import importlib.util
import importlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import sys
import time
import types
import urllib.request
import zipfile

sys.dont_write_bytecode = True
_EXECUTING_CODE = sys._getframe().f_code

if not __package__:
    # A profile verifier may load the canonical provider by absolute file path.
    # Give only its known sibling directory a package, without widening sys.path
    # or depending on the caller's cwd/import search order.
    _package_name = "rove4k_cloud_strength"
    _package_path = str(Path(__file__).resolve().parent)
    _package = sys.modules.get(_package_name)
    if _package is None:
        _package = types.ModuleType(_package_name)
        _package.__path__ = [_package_path]
        sys.modules[_package_name] = _package
    if list(_package.__path__) != [_package_path]:
        raise ValueError("cloud sibling package belongs to another source tree")
    _SIBLING_PACKAGE = _package_name
else:
    _SIBLING_PACKAGE = __package__

aws, budget, collect, ledger, registry, run, topology = (
    importlib.import_module(_SIBLING_PACKAGE + "." + name)
    for name in ("aws", "budget", "collect", "ledger", "registry", "run", "topology"))

CANONICAL_MODULE = "rove4k_cloud_runtime"
CANONICAL_AMI = "ami-0af9110f0ec0820e2"
CANONICAL_OWNER = "099720109477"
# Both a direct CLI and profile_verify's loader must use this exact module.
if __name__ == "__main__":
    sys.modules[CANONICAL_MODULE] = sys.modules[__name__]
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_SEED = 128 << 20
MAX_SEED_MANIFEST = 4 << 20
JOINT_EXPANDED_SEED = 256 << 20
MAX_MEMBER = 32 << 20
MAX_SEED_MEMBERS = 20000  # Includes seed.json, not just payload members.
ORIGINAL_LAYOUT_BASE = PurePosixPath("/home/runner/work/_temp")
_VALIDATED = object()
COMPILER_ENV = ("GCC_EXEC_PREFIX", "COMPILER_PATH", "LIBRARY_PATH", "CPATH",
                "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "OBJC_INCLUDE_PATH",
                "LD_PRELOAD", "LD_AUDIT", "LD_LIBRARY_PATH")
HOST_SOURCE_FILES = tuple("engines/experiments/strength/" + name + ".py" for name in
    ("cloud_runtime", "campaign", "aws", "budget", "ledger", "registry", "placement", "topology",
     "peer_runtime", "peers", "run", "wave", "collect", "durability", "fastchess", "seed")) + (
        "engines/scripts/production_input.py", "engines/scripts/source_composition.py",
        "engines/experiments/tcec-next/profile_dependencies.py",
        "engines/experiments/tiny-d-submission/source_inputs.py",
        "engines/common/board.c", "engines/common/move.c", "engines/common/protocol.c", "engines/common/search.c")


def require(value, detail):
    if not value:
        raise ValueError(detail)


def pin(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def member(name):
    require(isinstance(name, str) and name and "\\" not in name and ":" not in name and "\0" not in name,
            "normalized logical seed member required")
    parts = name.split("/")
    require(not PurePosixPath(name).is_absolute() and all(p not in ("", ".", "..") for p in parts),
            "seed member escaped its relative namespace")
    blocked = {".git", ".aws", ".ssh", "node_modules", "dist", "dist-server", "coverage",
               "models", "checkpoints", ".cache", "inventory.json", "package-lock.json"}
    require(not any(p.casefold() in blocked or p.casefold().startswith(".env") or
                    re.search(r"credential|service[-_ ]?account|api[-_ ]?key|ssh[-_ ]?key|^id_(rsa|ed25519)$", p, re.I)
                    for p in parts), "protected input cannot be transported in a seed")
    return name


def ordinary(path, *, limit=MAX_MEMBER):
    path = Path(path)
    require(path.is_absolute(), "absolute explicit input required")
    for component in path.parts[1:]:
        member(component)
    require(not any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
                    for p in (path, *path.parents)), "evidence must not follow links")
    if os.name == "posix" and hasattr(os, "O_NOFOLLOW"):
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
        directory = os.open(path.anchor, flags | os.O_DIRECTORY)
        descriptor = None
        try:
            for part in path.parts[1:-1]:
                child = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
                os.close(directory)
                directory = child
            descriptor = os.open(path.name, flags, dir_fd=directory)
            before = os.fstat(descriptor)
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit,
                    "bounded ordinary single-link evidence required")
            chunks, count = [], 0
            while count <= before.st_size:
                chunk = os.read(descriptor, min(65536, before.st_size + 1 - count))
                if not chunk:
                    break
                chunks.append(chunk)
                count += len(chunk)
            stamp = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            require(count == before.st_size and stamp(before) == stamp(os.fstat(descriptor)) ==
                    stamp(os.stat(path.name, dir_fd=directory, follow_symlinks=False)), "evidence inode changed during read")
            current = os.open(path.parent, flags | os.O_DIRECTORY)
            try:
                require((os.fstat(current).st_dev, os.fstat(current).st_ino) ==
                        (os.fstat(directory).st_dev, os.fstat(directory).st_ino), "evidence parent changed during read")
            finally:
                os.close(current)
            return b"".join(chunks)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(directory)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit,
            "bounded ordinary single-link evidence required")
    data = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) and
            len(data) == before.st_size, "evidence changed during read")
    return data


def new_external(path):
    path = Path(path)
    member(path.name)
    require(path.is_absolute() and not path.exists() and not any(p.is_symlink() or
            (p / ".git").exists() for p in (path, *path.parents)), "new absolute output outside Git required")
    return path


def write_new(path, data, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    path.chmod(mode)
    return pin(data)


def json_new(path, value):
    return write_new(path, ledger.canonical(value) + b"\n")


def checked_json(path, expected_sha=None):
    raw = ordinary(path)
    require(expected_sha is None or (isinstance(expected_sha, str) and SHA.fullmatch(expected_sha)
                                    and pin(raw)["sha256"] == expected_sha), "JSON input identity differs")
    return json.loads(raw)


@dataclass(frozen=True)
class SeedObject:
    bucket: str
    key: str
    version_id: str
    sha256: str
    bytes: int

    def __post_init__(self):
        require(isinstance(self.bucket, str) and re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", self.bucket),
                "explicit seed bucket required")
        member(self.key)
        require(isinstance(self.version_id, str) and self.version_id not in ("", "null") and
                len(self.version_id) <= 1024, "immutable S3 VersionId required")
        require(isinstance(self.sha256, str) and SHA.fullmatch(self.sha256) and
                type(self.bytes) is int and 0 < self.bytes <= MAX_SEED, "bounded seed object pin required")


def fetch_seed(seed, s3, out):
    """One explicit version GET, not prefix discovery or credential discovery."""
    require(type(seed) is SeedObject, "typed seed object required")
    out = new_external(out)
    response = s3.get_object(Bucket=seed.bucket, Key=seed.key, VersionId=seed.version_id)
    body = response["Body"]
    try:
        require(response.get("VersionId") == seed.version_id and response.get("ContentLength") == seed.bytes,
                "S3 seed version/length differs")
        data = body.read(seed.bytes + 1)
    finally:
        body.close()
    require(pin(data) == {"bytes": seed.bytes, "sha256": seed.sha256}, "S3 seed body identity differs")
    write_new(out, data)
    return out


def seed_expansion_limit(value):
    """Only the complete A--F/P4+P28 source cohort gets a larger expansion."""
    require(isinstance(value, dict), "seed selection must be an object")
    selected, rove = set(), set()
    for kind in ("rove", "peers"):
        rows = value.get(kind)
        require(isinstance(rows, list), "explicit Rove and peer source lists required")
        for row in rows:
            require(isinstance(row, dict) and isinstance(row.get("family"), str)
                    and isinstance(row.get("profile"), str)
                    and row["family"] in (tuple("ABCDEF") if kind == "rove" else ("ice4", "c4ke"))
                    and row["profile"] in ("test-p4", "test-p28"),
                    "source seed admits only named full TEST inputs")
            identity = row["family"], row["profile"]
            require(identity not in selected, "duplicate seed family/profile")
            selected.add(identity)
            if kind == "rove":
                rove.add(identity)
    require(selected, "seed contains no explicit TEST source inputs")
    joint = {(family, profile) for family in "ABCDEF" for profile in ("test-p4", "test-p28")}
    return JOINT_EXPANDED_SEED if rove == joint else MAX_SEED


def validate_seed_manifest(value):
    require(isinstance(value, dict) and value.get("format") == "rove4k-cloud-seed-v1",
            "explicit prequalification seed required")
    require(not any(key in value for key in ("qualified", "complete", "registry", "native_map", "scoring")),
            "seed transport cannot claim runtime qualification")
    capacity = seed_expansion_limit(value)
    origin = value.get("source_origin", {})
    require(isinstance(origin, dict) and set(origin) == {"repository", "head_sha", "run_id", "run_attempt"} and
            isinstance(origin["repository"], str) and re.fullmatch(r"[\w.-]+/[\w.-]+", origin["repository"]) and
            re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", str(origin["head_sha"])) and
            all(re.fullmatch(r"[1-9][0-9]*", str(origin[k])) for k in ("run_id", "run_attempt")),
            "sealed source origin must name its actual CI repository/head/run/attempt")
    members = value.get("members")
    require(isinstance(members, dict) and members and len(members) < MAX_SEED_MEMBERS,
            "explicit bounded member map including seed.json required")
    total = 0
    for name, expected in members.items():
        member(name)
        require(name != "seed.json" and not name.startswith("seed.json/") and isinstance(expected, dict) and
                set(expected) == {"bytes", "sha256", "mode"} and type(expected["bytes"]) is int and
                0 <= expected["bytes"] <= MAX_MEMBER and isinstance(expected["sha256"], str) and
                SHA.fullmatch(expected["sha256"]) and type(expected["mode"]) is int and
                expected["mode"] in (0o600, 0o700), "bounded seed member pin/mode required")
        total += expected["bytes"]
    raw = ledger.canonical(value) + b"\n"
    require(len(raw) <= MAX_SEED_MANIFEST, "seed manifest exceeds its bounded JSON size")
    require(total + len(raw) <= capacity, "uncompressed seed including manifest exceeds expansion bound")
    for prefix in members:
        require(not any(parent in members for parent in (str(p) for p in PurePosixPath(prefix).parents)
                        if parent != "."), "seed file/directory namespace collision")
    tree = member(value.get("source_tree"))
    require(tree + "/engines/experiments/strength/cloud_runtime.py" in members,
            "seed must carry the exact host consumer source tree")
    for kind in ("rove", "peers"):
        for row in value[kind]:
            if kind == "rove":
                root = member(row.get("build"))
                require(root + "/build.json" in members, "Rove source build omitted manifest")
                for key in ("source_bundle", "source_seal", "rules"):
                    require(member(row.get(key)) in members, "Rove input omitted " + key)
            else:
                prefix = member(row.get("source"))
                require(any(name.startswith(prefix + "/") for name in members), "peer original source is empty")
    require(member(value.get("bank")) in members and isinstance(value.get("runner"), dict),
            "seed requires its frozen opening bank and runner source declaration")
    pgns = value.get("bank_pgns", {})
    require(isinstance(pgns, dict) and {"broad", "high"} <= set(pgns) and
            set(pgns) <= {"broad", "high", "update1", "update2"} and
            all(member(name) in members for name in pgns.values()), "explicit stage PGN transport members required")
    runner = value["runner"]
    require(runner.get("revision") == "ebfd64cb7fac80d4822c50b07dca4fe934779d21" and
            member(runner.get("checkout")) and runner.get("transport") == "external-git-bundle" and
            member(runner.get("bundle")) in members, "pinned external Fastchess Git bundle required")
    return json.loads(json.dumps(value))


def load_seed_manifest(path, expected_sha=None):
    raw = ordinary(path, limit=MAX_SEED_MANIFEST)
    require(expected_sha is None or (isinstance(expected_sha, str) and SHA.fullmatch(expected_sha)
                                    and pin(raw)["sha256"] == expected_sha), "JSON input identity differs")
    manifest = validate_seed_manifest(json.loads(raw))
    require(raw == ledger.canonical(manifest) + b"\n", "seed manifest must use its exact canonical encoding")
    return manifest


def original_layout_plan(seed):
    """Validate explicit transport correspondence, never infer an old path."""
    value = seed.get("original_layout", {"format": "rove4k-original-layout-plan-v1", "roots": []})
    require(isinstance(value, dict) and set(value) == {"format", "roots"} and
            value["format"] == "rove4k-original-layout-plan-v1" and isinstance(value["roots"], list),
            "explicit original-layout roots required")
    rows, roots, prefixes = [], [], []
    for row in value["roots"]:
        require(isinstance(row, dict) and set(row) == {"original_root", "seed_prefix", "files"},
                "original restore root requires its exact prefix and file pins")
        raw_root = row["original_root"]
        require(isinstance(raw_root, str) and "\\" not in raw_root and ":" not in raw_root and
                "\0" not in raw_root, "original restore root must be a normalized POSIX path")
        root = PurePosixPath(raw_root)
        require(str(root) == raw_root and root.is_relative_to(ORIGINAL_LAYOUT_BASE) and root != ORIGINAL_LAYOUT_BASE and
                all(part not in ("", ".", "..") for part in root.parts[1:]),
                "original restore root escaped the owned CI temporary namespace")
        member(str(root.relative_to(ORIGINAL_LAYOUT_BASE)))
        prefix = member(row["seed_prefix"])
        require(not any(root == old or root in old.parents or old in root.parents for old in roots) and
                not any(prefix == old or prefix.startswith(old + "/") or old.startswith(prefix + "/") for old in prefixes),
                "original restore roots/prefixes overlap")
        files = row["files"]
        require(isinstance(files, dict) and files, "original restore root has no explicit artifact members")
        for relative, expected in files.items():
            logical = prefix + "/" + member(relative)
            require(logical in seed["members"] and expected ==
                    {key: seed["members"][logical][key] for key in ("bytes", "sha256")},
                    "original layout pin differs from its exact seed member")
        require(set(files) == {name[len(prefix) + 1:] for name in seed["members"] if name.startswith(prefix + "/")},
                "original layout must preserve the complete explicitly selected seed prefix")
        rows.append({"original_root": raw_root, "seed_prefix": prefix, "files": files})
        roots.append(root)
        prefixes.append(prefix)
    return rows


@dataclass(frozen=True, init=False)
class OriginalLayout:
    """Actual copy-only restore, not source admission or a rewritten receipt."""
    _record: str
    _manifest: str

    def __init__(self, token, record, manifest):
        require(token is _VALIDATED, "original layout must be restored and verified before use")
        object.__setattr__(self, "_record", json.dumps(record, sort_keys=True))
        object.__setattr__(self, "_manifest", json.dumps(manifest, sort_keys=True))

    def to_record(self):
        return json.loads(self._record)

    def execution_path(self, logical_member):
        member(logical_member)
        record = self.to_record()
        for row in record["roots"]:
            prefix = row["seed_prefix"]
            if logical_member == prefix:
                return Path(row["original_root"])
            if logical_member.startswith(prefix + "/"):
                return Path(row["original_root"]) / logical_member[len(prefix) + 1:]
        return Path(record["seed_root"]) / logical_member

    def assert_member(self, path):
        path = Path(path)
        require(path.is_absolute(), "explicit absolute original-layout member required")
        record, manifest = self.to_record(), json.loads(self._manifest)
        candidates = []
        seed_root = Path(record["seed_root"])
        if path.is_relative_to(seed_root):
            candidates.append(str(path.relative_to(seed_root)).replace(os.sep, "/"))
        for row in record["roots"]:
            root = Path(row["original_root"])
            if path.is_relative_to(root):
                candidates.append(row["seed_prefix"] + "/" + str(path.relative_to(root)).replace(os.sep, "/"))
        require(len(candidates) == 1 and candidates[0] in manifest["members"],
                "path has no exact original-layout seed correspondence")
        logical = candidates[0]
        expected = {key: manifest["members"][logical][key] for key in ("bytes", "sha256")}
        require(pin(ordinary(path)) == pin(ordinary(seed_root / logical)) == expected,
                "original-layout member changed from its sealed seed bytes")
        return logical

    def member_bytes(self, path):
        logical = self.assert_member(path)
        data = ordinary(Path(path))
        expected = json.loads(self._manifest)["members"][logical]
        require(pin(data) == {key: expected[key] for key in ("bytes", "sha256")},
                "original-layout member changed after its correspondence check")
        return data

    def revalidate(self):
        record, manifest = self.to_record(), json.loads(self._manifest)
        root = Path(record["seed_root"])
        revalidate_seed(manifest, root)
        require(pin(ordinary(root / "seed.json", limit=MAX_SEED_MANIFEST)) == record["seed_manifest"],
                "original-layout seed identity changed")
        for row in record["roots"]:
            destination = Path(row["original_root"])
            current = destination.stat()
            require(not destination.is_symlink() and (current.st_dev, current.st_ino) == (row["device"], row["inode"]),
                    "original restore root identity changed")
            files = set(row["files"])
            directories = {str(parent) for name in files for parent in PurePosixPath(name).parents if str(parent) != "."}
            pending = [destination]
            seen = set()
            while pending:
                directory = pending.pop()
                for path in directory.iterdir():
                    relative = str(path.relative_to(destination)).replace(os.sep, "/")
                    require(not path.is_symlink(), "original restore tree unexpectedly contains a link")
                    if path.is_dir():
                        require(relative in directories, "original restore tree has an unknown directory")
                        pending.append(path)
                    else:
                        require(relative in files, "original restore tree has an unknown file")
                        logical = self.assert_member(path)
                        require(stat.S_IMODE(path.stat().st_mode) == manifest["members"][logical]["mode"],
                                "original restored file mode changed")
                        seen.add(relative)
            require(seen == files, "original restore tree omitted a sealed member")
        return self


def restore_original_layout(seed, seed_root):
    """Copy exact declared members to new CI-owned paths; never merge/delete."""
    require(sys.platform == "linux", "original CI layout restoration requires Linux")
    revalidate_seed(seed, seed_root)
    plan = original_layout_plan(seed)
    require(not seed.get("rove") or plan, "Rove cloud seed omitted its exact original-layout restore map")
    for selected in seed.get("rove", []):
        seal = checked_json(Path(seed_root) / selected["source_seal"])
        require(seal.get("format") == "rove4k.source-bundle-seal.v1" and
                seal.get("ci_context") == seed["source_origin"] and
                seal.get("producer") == {"ID": "ubuntu", "VERSION_ID": "24.04"} and
                seal.get("bundle") == pin(ordinary(Path(seed_root) / selected["source_bundle"], limit=MAX_SEED)),
                "original-layout declaration does not bind the sealed source origin/bundle")
        profiles = [entry for entry in seal.get("profiles", []) if
                    (entry.get("family"), entry.get("profile")) == (selected["family"], selected["profile"])]
        mappings = [row for row in plan if selected["build"] == row["seed_prefix"] or
                    selected["build"].startswith(row["seed_prefix"] + "/")]
        require(len(profiles) == len(mappings) == 1, "Rove build has no unique sealed original-root mapping")
        mapping = mappings[0]
        relative = selected["build"][len(mapping["seed_prefix"]):].lstrip("/")
        execution = Path(mapping["original_root"]) / relative
        require(str(execution) == profiles[0].get("build_root"),
                "restored execution build differs from the exact sealed original build root")
    for row in plan:
        destination = Path(row["original_root"])
        require(not destination.exists() and not any(path.is_symlink() for path in (destination, *destination.parents)) and
                not any((path / ".git").exists() for path in (destination, *destination.parents)),
                "original restore destination already exists, is linked, or belongs to an unknown checkout")
    restored = []
    for row in plan:
        destination = Path(row["original_root"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.mkdir(mode=0o700)
        current = destination.stat()
        for relative, expected in sorted(row["files"].items()):
            logical = row["seed_prefix"] + "/" + relative
            data = ordinary(Path(seed_root) / logical)
            require(pin(data) == expected, "seed member changed before original-layout copy")
            write_new(destination / relative, data, seed["members"][logical]["mode"])
        restored.append({**row, "device": current.st_dev, "inode": current.st_ino})
    token = OriginalLayout(_VALIDATED, {"format": "rove4k-original-layout-v1", "seed_root": str(Path(seed_root)),
        "seed_manifest": pin(ordinary(Path(seed_root) / "seed.json", limit=MAX_SEED_MANIFEST)), "roots": restored,
        "scope": "exact transport correspondence; not source/runtime qualification"}, seed)
    return token.revalidate()


def seed_archive_manifest(archive, *, expected_manifest_sha256=None):
    """Inspect only the bounded manifest before any other ZIP member is read.

    The caller owns an already-open ZipFile and separately bounds its wire
    bytes.  Every entry's name/type/size and the derived aggregate expansion
    limit are checked before the returned entries may be read or written.
    """
    require(type(archive) is zipfile.ZipFile and archive.fp is not None,
            "an already-open standard seed ZipFile is required")
    require(expected_manifest_sha256 is None or
            (isinstance(expected_manifest_sha256, str) and SHA.fullmatch(expected_manifest_sha256)),
            "controller-pinned seed manifest SHA required")
    infos = archive.infolist()
    require(0 < len(infos) <= MAX_SEED_MEMBERS, "seed archive member count exceeds bound")
    names, total = {}, 0
    for info in infos:
        name = member(info.filename)
        mode = info.external_attr >> 16
        require(name not in names and not info.is_dir() and not info.flag_bits & 1 and
                stat.S_IFMT(mode) in (0, stat.S_IFREG) and type(info.file_size) is int and
                0 <= info.file_size <= (MAX_SEED_MANIFEST if name == "seed.json" else MAX_MEMBER),
                "seed has duplicate/link/directory/encrypted/excessive member")
        total += info.file_size
        names[name] = info
    require(total <= JOINT_EXPANDED_SEED, "seed expansion exceeds bound")
    require("seed.json" in names, "seed archive omitted its bounded manifest")
    with archive.open(names["seed.json"], "r") as source:
        raw = source.read(MAX_SEED_MANIFEST + 1)
    require(len(raw) == names["seed.json"].file_size and len(raw) <= MAX_SEED_MANIFEST,
            "seed manifest size differs from bounded ZIP metadata")
    require(expected_manifest_sha256 is None or pin(raw)["sha256"] == expected_manifest_sha256,
            "seed manifest differs from controller pin")
    manifest = validate_seed_manifest(json.loads(raw))
    require(raw == ledger.canonical(manifest) + b"\n", "seed manifest must use its exact canonical encoding")
    require(total <= seed_expansion_limit(manifest), "seed expansion exceeds selected cohort bound")
    require(set(names) == {"seed.json", *manifest["members"]},
            "seed archive differs from exact member allowlist")
    require(all(names[name].file_size == expected["bytes"] for name, expected in manifest["members"].items()),
            "seed member changed: archive member differs in length from manifest")
    return manifest, raw, infos


def materialize_seed_archive(path, out, *, expected_manifest_sha256):
    """Extract exactly the allowlist after validating *all* names and bytes.

    No extractall, destination layout rewrite, receipt patching or code execution.
    The root is new; partial failures are retained, never recursively removed.
    """
    data = ordinary(path, limit=MAX_SEED)
    require(isinstance(expected_manifest_sha256, str) and SHA.fullmatch(expected_manifest_sha256),
            "controller-pinned seed manifest SHA required")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest, raw, infos = seed_archive_manifest(archive, expected_manifest_sha256=expected_manifest_sha256)
        files = {"seed.json": raw}
        for info in infos:
            if info.filename == "seed.json":
                continue
            with archive.open(info, "r") as source:
                body = source.read(MAX_MEMBER + 1)
            expected = manifest["members"][info.filename]
            require(pin(body) == {k: expected[k] for k in ("bytes", "sha256")},
                    "seed member changed: " + info.filename)
            files[info.filename] = body
    out = new_external(out)
    out.mkdir(parents=True, mode=0o700)
    for name, body in files.items():
        write_new(out / name, body, 0o600 if name == "seed.json" else manifest["members"][name]["mode"])
    return manifest


def revalidate_seed(manifest, root):
    validate_seed_manifest(manifest)
    require(ordinary(Path(root) / "seed.json", limit=MAX_SEED_MANIFEST) == ledger.canonical(manifest) + b"\n",
            "materialized seed manifest changed")
    for name, expected in manifest["members"].items():
        require(pin(ordinary(Path(root) / name)) == {k: expected[k] for k in ("bytes", "sha256")},
                "materialized seed changed: " + name)


def validate_host_source(manifest, source_root=ROOT):
    """Bind the transported host controller to the reviewed executing checkout."""
    for name in HOST_SOURCE_FILES:
        expected = manifest["members"].get(manifest["source_tree"] + "/" + name)
        require(expected is not None, "seed omitted host execution source: " + name)
        data = ordinary(Path(source_root) / name).replace(b"\r\n", b"\n")
        require(pin(data) == {key: expected[key] for key in ("bytes", "sha256")},
                "transported host execution source differs from reviewed controller: " + name)
    own_source = ordinary(Path(__file__).resolve()).replace(b"\r\n", b"\n")
    require(compile(own_source, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "cloud validator changed after its executing module was compiled")


def load_module(name, path):
    existing = sys.modules.get(name)
    if existing is not None:
        require(Path(existing.__file__).resolve() == Path(path).resolve(), "canonical provider module path collision")
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    try:
        spec.loader.exec_module(result)
    except BaseException:
        del sys.modules[name]
        raise
    return result


def canonical_provider():
    current = sys.modules.get(CANONICAL_MODULE)
    if current is None:
        sys.modules[CANONICAL_MODULE] = sys.modules[__name__]
        current = sys.modules[__name__]
    require(Path(current.__file__).resolve() == Path(__file__).resolve(), "canonical cloud provider source differs")
    return current


def bootstrap_module():
    module = importlib.import_module(_SIBLING_PACKAGE + ".campaign")
    require(Path(module.__file__).resolve() == HERE / "campaign.py", "bootstrap recipe module belongs to another source tree")
    return module


def instance_document(opener=None):
    """IMDSv2 non-secret identity document only; never role credentials."""
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({})).open
    endpoint = "http://169.254.169.254/latest/"
    request = urllib.request.Request(endpoint + "api/token", method="PUT",
                                     headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"})
    with opener(request, timeout=3) as response:
        token = response.read(4097)
    require(0 < len(token) <= 4096, "bounded IMDSv2 token required")
    request = urllib.request.Request(endpoint + "dynamic/instance-identity/document",
                                     headers={"X-aws-ec2-metadata-token": token.decode("ascii")})
    with opener(request, timeout=3) as response:
        raw = response.read(16385)
    require(len(raw) <= 16384, "bounded instance identity document required")
    return json.loads(raw)


@dataclass(frozen=True, init=False)
class CloudConsumer:
    _record: str
    _inputs: tuple

    def __init__(self, token, record, inputs):
        require(token is _VALIDATED, "EC2 consumer must pass live ownership and host checks")
        object.__setattr__(self, "_record", json.dumps(record, sort_keys=True))
        object.__setattr__(self, "_inputs", inputs)

    def to_record(self):
        return json.loads(self._record)

    def revalidate(self):
        client, plan, state, root, clock, metadata = self._inputs
        fresh = observe_consumer(client, plan, state, root, clock=clock, metadata=metadata,
                                 _original_topology=self.to_record()["topology"])
        require(fresh.to_record() == self.to_record(), "EC2 consumer identity/topology/source changed")
        return fresh


def observe_consumer(client, plan, state, source_root, *, clock=time.time, metadata=instance_document,
                     _original_topology=None):
    require(plan.region == "ap-southeast-2" and plan.project_region == plan.region,
            "campaign cloud consumer is restricted to the selected Sydney region")
    require(sys.platform == "linux" and platform.machine() == "x86_64" and
            not any(os.environ.get(name) for name in COMPILER_ENV), "unredirected Linux x86-64 host required")
    lease = aws.verify_owned_lease(client, plan, state, clock(), caller_kind="instance")
    document = metadata()
    require(document.get("instanceId") == lease["instance_id"] and document.get("accountId") == plan.account_id and
            document.get("region") == plan.region and document.get("imageId") == plan.ami_id and
            document.get("instanceType") == aws.INSTANCE_TYPE, "actual IMDS identity differs from owned lease/AMI/SKU")
    observed = topology.Topology.snapshot()
    if _original_topology is not None:
        # Qualification narrows the calling thread to its actual TEST slot.
        # Retain only the previously observed host envelope; never set a wider
        # affinity or accept a caller-supplied replacement native/topology map.
        original = topology.Topology.from_record(_original_topology)
        require(set(observed.allowed_cpus) <= set(original.allowed_cpus) and
                observed.allowed_nodes == original.allowed_nodes and observed.kernel == original.kernel,
                "current qualification escaped its original host envelope")
        current = {cpu.id: cpu for cpu in observed.cpus}
        require(all(current[cpu.id] == cpu for cpu in original.cpus if cpu.id in current),
                "observed physical CPU topology changed")
        online = topology.parse_list(Path("/sys/devices/system/cpu/online").read_text())
        require(set(original.allowed_cpus) <= online, "original host CPU went offline")
        for cpu in original.cpus:
            directory = Path(f"/sys/devices/system/cpu/cpu{cpu.id}/topology")
            require(int((directory / "physical_package_id").read_text()) == cpu.socket and
                    int((directory / "core_id").read_text()) == cpu.core and
                    topology.parse_list((directory / "thread_siblings_list").read_text()) == set(cpu.siblings),
                    "original host topology changed during qualification")
        observed = original
    require(len(observed.allowed_cpus) == 192 and len({cpu.physical for cpu in observed.cpus}) == 96,
            "m6a.48xlarge full 192 logical / 96 physical host envelope required")
    compiler = load_module("rove_cloud_profile_compiler", Path(source_root) / "engines/experiments/tcec-next/profile_compiler.py")
    import shutil
    cc = shutil.which("cc")
    require(cc is not None, "source-JIT cc is absent")
    context = compiler.system_descriptor(Path(cc).resolve())
    record = {"format": "rove4k-ec2-consumer-v1", "instance_id": lease["instance_id"],
              "account_id": plan.account_id, "region": plan.region, "ami_id": plan.ami_id,
              "instance_type": aws.INSTANCE_TYPE, "owner_nonce": plan.owner_nonce,
              "launch_token": plan.launch_token, "plan_sha256": aws.digest(plan.as_dict()),
              "ownership_sha256": lease["ownership_sha256"], "caller": lease["caller"],
              "identity_document": document, "topology": observed.to_record(), "compiler_context": context}
    return CloudConsumer(_VALIDATED, record, (client, plan, state, Path(source_root), clock, metadata))


def admission_snapshot(admitted):
    require(is_dataclass(admitted), "immutable production admission dataclass required")
    return json.dumps(asdict(admitted), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, init=False)
class CloudRuntimeReference:
    family: str
    profile: str
    native_path: Path
    _record: str
    _inputs: tuple
    _admission: str
    _admission_type: type
    _build: str
    _source_evidence: object

    def __init__(self, token, admitted, build, native_path, record, inputs, *, source_evidence=None):
        require(token is _VALIDATED, "cloud reference must pass sealed source/compiler/live EC2 validation")
        for key, value in (("family", admitted.family), ("profile", admitted.profile_id),
                           ("native_path", Path(native_path)), ("_record", json.dumps(record, sort_keys=True)),
                           ("_inputs", inputs), ("_admission", admission_snapshot(admitted)),
                           ("_admission_type", type(admitted)), ("_build", str(Path(build))),
                           ("_source_evidence", source_evidence)):
            object.__setattr__(self, key, value)

    @property
    def native_pin(self):
        return self.to_record()["native"]

    @property
    def compiler_context(self):
        return self.to_record()["compiler_context"]

    @property
    def source_evidence(self):
        """The immutable validated token; its JSON record is not authority."""
        return self._source_evidence

    def to_record(self):
        return json.loads(self._record)

    def assert_admission(self, admitted, build):
        require(type(admitted) is self._admission_type and admission_snapshot(admitted) == self._admission and
                str(Path(build)) == self._build and Path(build).resolve() == Path(build),
                "cloud reference admission/build differs; producer native map is immutable")

    def revalidate(self, *, verify):
        admitted, build, receipt, manifest, root, row, consumer, restored_layout = self._inputs
        self.assert_admission(admitted, build)
        current = validate_cloud_runtime(admitted, build, receipt, seed=manifest, root=root,
                                         row=row, consumer=consumer, verify=verify, restored_layout=restored_layout)
        require(current.to_record() == self.to_record(), "cloud reference changed before/post runtime")
        return current


def require_rove_bridge(verify):
    required = ("cloud_source_binding", "cloud_compiler_binding", "cloud_rules_receipt", "cloud_runtime_supported")
    missing = [name for name in required if not callable(getattr(verify, name, None))]
    require(not missing, "missing production R cloud bridge: " + ", ".join(missing))
    require(verify.cloud_runtime_supported(canonical_provider()) is True,
            "production R consumer has not registered the canonical CloudRuntimeReference type")


def validate_cloud_runtime(admitted, build, compiler_receipt, *, seed, root, row, consumer, verify, restored_layout):
    """Issue authority only after both real source and compile validators pass.

    R owns the pure validators. They must replay all original source admission,
    owned compiler pipes, dependency/type gates, and before/post toolchain pins.
    Missing validators stop before any runtime, never use a passed fixture flag.
    """
    require(type(consumer) is CloudConsumer, "validated live CloudConsumer required")
    require(type(restored_layout) is OriginalLayout, "actual typed original-layout restoration required")
    require_rove_bridge(verify)
    consumer.revalidate()
    revalidate_seed(seed, root)
    restored_layout.revalidate()
    require(row in seed["rove"] and admitted.family == row["family"] and admitted.profile_id == row["profile"] and
            Path(build) == restored_layout.execution_path(row["build"]) and admitted.representation == "source-jit",
            "cloud runtime requires the selected sealed source-JIT TEST build")
    original = json.loads(json.dumps(admitted.expected))
    binding = verify.cloud_source_binding(admitted, Path(build), source_bundle=Path(root) / row["source_bundle"],
        source_seal=Path(root) / row["source_seal"], source_origin=seed["source_origin"],
        seed_root=Path(root), restored_layout=restored_layout,
        member_map={name: {k: p[k] for k in ("bytes", "sha256")} for name, p in seed["members"].items()})
    compiled = verify.cloud_compiler_binding(admitted, Path(build), Path(compiler_receipt),
                                            source_binding=binding)
    require(set(compiled) == {"native_path", "native", "compiler_context", "compiler_inputs", "evidence"},
            "cloud compiler validator returned an incomplete authority binding")
    require(compiled["compiler_context"] == consumer.to_record()["compiler_context"] and
            compiled["native"] == pin(ordinary(Path(compiled["native_path"]))) and compiled["compiler_inputs"],
            "cloud native/toolchain differs from actual EC2 compiler")
    require(admitted.expected == original, "cloud validation modified producer native expectation")
    record = {"format": "rove4k-cloud-runtime-reference-v1", "runtime_eligible": True,
              "factory_replayed_on_target": False, "source_origin": seed["source_origin"],
              "seed_manifest": pin(ordinary(Path(root) / "seed.json", limit=MAX_SEED_MANIFEST)),
              "source_binding": binding.to_record(),
              "consumer": consumer.to_record(), "source_build": {"path": str(build), **pin(ordinary(Path(build) / "build.json"))},
              "original_build_expected_contract": original, "native": compiled["native"],
              "compiler_context": compiled["compiler_context"], "compiler_inputs": compiled["compiler_inputs"],
              "compiler_evidence": compiled["evidence"], "family": admitted.family, "profile": admitted.profile_id,
              "scope": "EC2 source-JIT runtime image reference; not runtime qualification or score admission"}
    return CloudRuntimeReference(_VALIDATED, admitted, build, compiled["native_path"], record,
                                 (admitted, Path(build), Path(compiler_receipt), seed, Path(root), row, consumer, restored_layout),
                                 source_evidence=binding)


@contextmanager
def qualification_slot(slot):
    original = os.sched_getaffinity(0)
    require(set(slot.cpus) <= original and len(slot.cpus) == slot.workers, "qualification cannot widen original affinity")
    try:
        os.sched_setaffinity(0, slot.cpus)
        require(os.sched_getaffinity(0) == set(slot.cpus), "actual qualification affinity differs")
        yield
    finally:
        os.sched_setaffinity(0, original)
        require(os.sched_getaffinity(0) == original, "qualification did not restore original host affinity")


def prepare_rove(row, *, seed, root, out, consumer, slot, execute_command, restored_layout):
    source = Path(root) / seed["source_tree"]
    verify = load_module("rove_cloud_profile_verify", source / "engines/experiments/tcec-next/profile_verify.py")
    require_rove_bridge(verify)  # Fail before compiler/engine when authority is absent.
    require(type(restored_layout) is OriginalLayout, "Rove execution requires its original owned layout")
    restored_layout.revalidate()
    build = restored_layout.execution_path(row["build"])
    manifest = checked_json(build / "build.json")
    if row["family"] == "D":
        require(row.get("candidate"), "D requires explicit selected candidate")
        admitted = verify.admit_d_build(manifest, build, row["candidate"])
    else:
        admitted = verify.admit_c_build(manifest, build)
    require(admitted.full and admitted.expected["whole_bytes"] <= 4096,
            "blocked_size/full: source seed does not authorize native fallback")
    out = new_external(out)
    out.mkdir(parents=True)
    compiler_out = out / "compiler"
    execute_command([sys.executable, "-I", str(source / "engines/experiments/tcec-next/profile_compiler.py"),
                     "--build", str(build), "--compiler", consumer.to_record()["compiler_context"]["driver"]["path"],
                     "--ubuntu22-system", "--program-provenance", "--out", str(compiler_out)], out, slot.cpus[0])
    reference = validate_cloud_runtime(admitted, build, compiler_out / "compiler.json", seed=seed,
        root=root, row=row, consumer=consumer, verify=verify, restored_layout=restored_layout)
    rules = verify.cloud_rules_receipt(admitted, build, restored_layout.execution_path(row["rules"]),
                                       source_binding=reference.source_evidence)
    with qualification_slot(slot):
        limits = verify.execution_limits(admitted, verify.effective_available_bytes())
        verify.run_runtime(admitted, build, out / "runtime", limits, target_reference=reference)
        proof = verify.qualification_record(admitted, build, out / "runtime/runtime.json",
            rules_path=Path(rules), target_reference=reference)
    receipt = out / "qualification.json"
    proof_pin = json_new(receipt, proof)
    artifact = registry.Artifact.from_record({**proof["artifact"], "path": str(build / admitted.program)})
    registry.admit_to_test_league(artifact, receipt, proof_pin["sha256"])
    json_new(out / "cloud-reference.json", reference.to_record())
    return {"artifact": {**artifact.identity(), "path": str(artifact.path)},
            "receipt": str(receipt), "receipt_sha256": proof_pin["sha256"]}


def prepare_peer(row, *, seed, root, out, slot):
    source = Path(root) / seed["source_tree"]
    peers = load_module("rove_cloud_peers", source / "engines/experiments/strength/peers.py")
    runtime = load_module("rove_cloud_peer_runtime", source / "engines/experiments/strength/peer_runtime.py")
    out = new_external(out)
    out.mkdir(parents=True)
    # Fresh target producer receipts retain their real target absolute paths;
    # original source files are verified by the upstream literal blob pins.
    built = peers.build_resource_tiny(row["family"], Path(root) / row["source"], out / "peer-build", row["profile"],
        run=lambda argv, cwd, **kw: peers.bounded_run(argv, cwd, cpu=slot.cpus[0], **kw))
    build = Path(built["path"])
    require(build.exists(), "peer producer did not emit its real build manifest")
    reference = runtime.prepare_reference(build, out / "reference", cpu=slot.cpus[0])
    qualified = runtime.qualify_peer(Path(reference["path"]), out / "runtime", slot.to_record(), reference_sha=reference["sha256"])
    artifact = checked_json(Path(qualified["artifact"]))
    registry.admit_to_test_league(registry.Artifact.from_record(artifact), Path(qualified["path"]), qualified["sha256"])
    return {"artifact": artifact, "receipt": qualified["path"], "receipt_sha256": qualified["sha256"]}


def prepare_registry(seed, root, out, consumer, profile, *, execute_command, restored_layout,
                     rove_driver=prepare_rove, peer_driver=prepare_peer):
    require(type(consumer) is CloudConsumer and profile in ("test-p4", "test-p28"), "actual consumer/named TEST profile required")
    consumer.revalidate()
    revalidate_seed(seed, root)
    observed = topology.Topology.from_record(consumer.to_record()["topology"])
    physical = 4 if profile == "test-p4" else 28
    slot = topology.plan_slots(observed, physical, physical, reserve_physical=8, max_slots=1)[0]
    out = new_external(out)
    out.mkdir(parents=True)
    players, rejected = [], []
    for kind, driver in (("rove", rove_driver), ("peers", peer_driver)):
        for row in seed.get(kind, []):
            if row["profile"] != profile:
                continue
            kwargs = dict(seed=seed, root=root, out=out / (row["family"] + "-" + profile), slot=slot)
            if kind == "rove":
                kwargs.update(consumer=consumer, execute_command=execute_command, restored_layout=restored_layout)
            try:
                result = driver(row, **kwargs)
                registry.admit_to_test_league(registry.Artifact.from_record(result["artifact"]),
                    Path(result["receipt"]), result["receipt_sha256"])
                players.append(result)
            except ValueError as error:
                # An explicitly ineligible source remains rejected; it does not
                # turn into a configurable/native fallback or a passed flag.
                rejected.append({"family": row["family"], "profile": profile, "reason": str(error)})
    value = {"format": "rove4k-league-registry-v1", "players": players,
             "source_origin": seed["source_origin"], "consumer": consumer.to_record(), "rejected": rejected}
    json_new(out / "registry.json", value)
    return out / "registry.json"


def archive_files(publisher, campaign, files):
    """Only explicit allowlisted files, acknowledged by content before return."""
    receipts = []
    for logical, path in sorted(files.items()):
        member(logical)
        data = ordinary(Path(path), limit=MAX_SEED)
        expected = pin(data)
        key = campaign + "/archive/" + expected["sha256"] + "/" + logical
        result = publisher.publish(Path(path), key)
        require(result.get("verified") is True and result.get("sha256") == expected["sha256"] and
                result.get("object_key") == key, "archive object did not receive exact remote acknowledgement")
        receipts.append({"logical": logical, **expected, "remote": result})
    return receipts


def validate_controller_inputs(*, plan, seed, manifest, manifest_sha256, permit, client, now):
    """Read actual image/template/function identities before an explicit launch.

    The permit pins the reviewed deployment and the same-instance bootstrap
    recipe. Canonical's image metadata does not claim installed build tools.
    SSM performs that recipe on the one admitted Spot instance, then the host
    independently records and checks the actual toolchain before any engine.
    """
    manifest = validate_seed_manifest(manifest)
    require(not manifest.get("rove") or original_layout_plan(manifest),
            "Rove source seed has no original-layout restoration plan")
    validate_host_source(manifest)
    seed = SeedObject(**seed)
    require(plan.region == plan.project_region == "ap-southeast-2" and
            seed.bucket == plan.artifact_bucket and seed.key.startswith(plan.campaign_id + "/"),
            "seed and selected workload region differ from campaign")
    source = ROOT / "engines/experiments/tcec-next/profile_verify.py"
    verify = load_module("rove_cloud_controller_profile_verify", source)
    if manifest.get("rove"):
        require_rove_bridge(verify)
    reviewed = permit.get("reviewed_deployment")
    bootstrap = permit.get("bootstrap")
    require(isinstance(reviewed, dict) and isinstance(bootstrap, dict),
            "missing reviewed deployment and same-instance bootstrap recipe")
    require(ledger.digest({"deployment": reviewed, "bootstrap": bootstrap}) == permit["deployment_receipt_sha256"],
            "reviewed deployment/image receipt differs from explicit permit")
    campaign_module = bootstrap_module()
    recipe_function = getattr(campaign_module, "bootstrap_recipe", None)
    require(callable(recipe_function), "actual bounded same-instance bootstrap recipe is missing")
    recipe = recipe_function()
    require(bootstrap == {"recipe_id": recipe["id"], "recipe_sha256": recipe["sha256"]},
            "execution permit does not bind the reviewed same-instance bootstrap recipe")
    infrastructure = load_module("rove_cloud_infrastructure", HERE / "aws_infrastructure.py")
    template_options = ({"account_readiness": plan.account_readiness.as_dict()}
                        if plan.account_readiness is not None else {})
    expected_template = infrastructure.template(project_region=plan.region, **template_options)
    require(reviewed.get("template_sha256") == ledger.digest(expected_template) and
            reviewed.get("watchdog_source_sha256") == pin(infrastructure.WATCHDOG_SOURCE.encode())["sha256"],
            "deployment receipt does not bind reviewed template and actual watchdog source")
    aws.verify_caller(client, plan)
    aws.verify_watchdog(client, plan, now)
    template = client.call("cloudformation", "get-template", {"StackName": plan.watchdog_stack, "TemplateStage": "Original"})
    body = template.get("TemplateBody")
    body = json.loads(body) if isinstance(body, str) else body
    require(body == expected_template, "deployed original CloudFormation template differs from reviewed source")
    function = client.call("lambda", "get-function-configuration", {"FunctionName": plan.watchdog_arn})
    require(function.get("FunctionArn") == plan.watchdog_arn and function.get("State") == "Active" and
            function.get("LastUpdateStatus") == "Successful" and
            function.get("CodeSha256") == reviewed.get("function_code_sha256") and
            function.get("RevisionId") == reviewed.get("function_revision_id") and
            bool(reviewed.get("function_code_sha256")) and bool(reviewed.get("function_revision_id")),
            "live watchdog code/revision differs from reviewed deployment receipt")
    images = client.call("ec2", "describe-images", {"ImageIds": [plan.ami_id]}).get("Images", [])
    require(len(images) == 1, "exact bootstrap AMI is unavailable")
    image = images[0]
    require(image.get("ImageId") == plan.ami_id == CANONICAL_AMI and
            image.get("OwnerId") == CANONICAL_OWNER and
            re.fullmatch(r"ubuntu/images/hvm-ssd/ubuntu-jammy-22\.04-amd64-server-[0-9]{8}", image.get("Name", "")) and
            image.get("State") == "available" and image.get("Architecture") == "x86_64" and
            image.get("RootDeviceType") == "ebs", "live image differs from fixed Canonical Ubuntu22 baseline")
    return {"verified": True, "plan_sha256": aws.digest(plan.as_dict()), "seed_sha256": seed.sha256,
            "seed_manifest_sha256": manifest_sha256, "deployment_receipt_sha256": permit["deployment_receipt_sha256"],
            "ami_id": plan.ami_id}


def verify_host_tools(permit, root):
    """Consume actual same-instance bootstrap output, then rehash live tools."""
    import shutil
    receipt = checked_json(Path(root) / "bootstrap/receipt.json")
    campaign_module = bootstrap_module()
    recipe = campaign_module.bootstrap_recipe()
    require(receipt.get("format") == "rove4k-bootstrap-receipt-v1" and receipt.get("complete") is True and
            receipt.get("recipe_id") == recipe["id"] and receipt.get("recipe_sha256") == recipe["sha256"] and
            permit["bootstrap"] == {"recipe_id": recipe["id"], "recipe_sha256": recipe["sha256"]},
            "actual bootstrap receipt differs from reviewed recipe/permit")
    started, finished = budget.timestamp(receipt["started_at"]), budget.timestamp(receipt["finished_at"])
    require(started <= finished <= budget.timestamp(receipt["deadline_epoch"]) and finished - started <= recipe["maximum_seconds"],
            "actual bootstrap exceeded its bounded same-instance interval")
    commands = receipt.get("commands", [])
    require(isinstance(commands, list) and commands, "bootstrap has no actual command evidence")
    for command in commands:
        require(command.get("returncode") == 0 and command.get("reaped") is True and
                command.get("group_absent") is True and command.get("terminal") is True and command.get("forced_cleanup") is False and
                type(command.get("pid")) is int and command["pid"] == command.get("pgid") == command.get("sid") and
                type(command.get("start_ticks")) is int and command["start_ticks"] > 0 and
                isinstance(command.get("argv"), list) and command["argv"] and
                all(isinstance(item, str) for item in command["argv"]),
                "bootstrap command did not naturally settle its original group")
        for stream in ("stdout", "stderr"):
            expected = command.get(stream, {})
            path = Path(expected.get("path", "."))
            require(path.is_absolute() and path.is_relative_to(Path(root) / "bootstrap") and
                    pin(ordinary(path)) == {key: expected[key] for key in ("bytes", "sha256")},
                    "bootstrap actual command pipe differs")
    archive = receipt.get("aws_cli_archive", {})
    require(archive.get("url") == recipe["aws_cli_url"] and archive.get("version") == recipe["aws_cli_version"] and
            archive.get("signer_fingerprint") == recipe["aws_cli_signer_fingerprint"] and
            SHA.fullmatch(str(archive.get("sha256"))) and SHA.fullmatch(str(archive.get("signature_sha256"))),
            "bootstrap did not bind the official pinned signed CLI archive")
    base = Path(root) / "bootstrap"
    sources = ordinary(base / "ubuntu.list")
    require(sources == recipe["apt_sources"].encode() and pin(sources)["sha256"] == receipt.get("apt_sources_sha256") and
            ordinary(base / "aws-cli-public.asc") == recipe["aws_cli_public_key"].encode(),
            "actual signed APT sources or pinned CLI public key changed")
    for filename, expected in (("awscliv2.zip", {"bytes": archive["bytes"], "sha256": archive["sha256"]}),
                               ("awscliv2.zip.sig", None)):
        actual = pin(ordinary(base / filename, limit=MAX_SEED))
        require(actual == expected if expected is not None else actual["sha256"] == archive["signature_sha256"],
                "downloaded signed CLI distribution changed")
    imports = [c for c in commands if c["argv"] == ["/usr/bin/gpg", "--homedir", str(base / "gnupg"),
                "--batch", "--import", str(base / "aws-cli-public.asc")]]
    signatures = [c for c in commands if c["argv"] == ["/usr/bin/gpg", "--homedir", str(base / "gnupg"),
                "--batch", "--status-fd=1", "--verify", str(base / "awscliv2.zip.sig"), str(base / "awscliv2.zip")]]
    require(len(imports) == len(signatures) == 1 and commands.index(imports[0]) < commands.index(signatures[0]),
            "actual pinned-key import and CLI verification commands are missing")
    status = ordinary(Path(signatures[0]["stdout"]["path"])).decode()
    valid = [line.split()[2] for line in status.splitlines() if line.startswith("[GNUPG:] VALIDSIG ")]
    require(valid == [recipe["aws_cli_signer_fingerprint"]], "actual CLI signature output differs from pinned publisher")
    apt_commands = [c["argv"] for c in commands if c["argv"] and c["argv"][0] == "/usr/bin/apt-get"]
    require(len(apt_commands) == 2 and apt_commands[0][-2:] == ["update", "--error-on=any"] and
            apt_commands[1][-(len(recipe["apt_packages"]) + 4):] ==
                ["install", "--yes", "--no-install-recommends", "--no-remove", *recipe["apt_packages"]] and
            all("Dir::Etc::sourcelist=" + str(base / "ubuntu.list") in argv and
                "Dir::Etc::sourceparts=-" in argv and "Acquire::AllowInsecureRepositories=false" in argv for argv in apt_commands),
            "actual bootstrap did not use the fixed signed APT source/package recipe")
    tools = receipt.get("tools", {})
    require({"python3", "aws", "cc", "c++", "git", "make", "xz", "systemd-run"} <= set(tools),
            "actual bootstrap omitted required executable observations")
    for name, expected in tools.items():
        path = Path(expected["resolved_path"])
        resolved = path.resolve(strict=True)
        require(resolved.is_file() and resolved.is_absolute() and resolved.stat().st_size <= MAX_SEED,
                "bootstrapped executable is absent: " + name)
        # Installed tool hard links/symlinks are permitted; evidence files are
        # still single-link ordinary files. No SDK credentials are inspected.
        require(pin(resolved.read_bytes()) == {key: expected[key] for key in ("bytes", "sha256")},
                "actual executable changed since bootstrap: " + name)
        if name not in ("ssm-agent",):
            actual = shutil.which(name)
            require(actual is not None and Path(actual).resolve() == resolved,
                    "PATH redirects an image bootstrap tool: " + name)
    return receipt


def delegate_controller(cgroup_root):
    """Use only the systemd-delegated service root, never a global ancestor."""
    path = Path(cgroup_root)
    require(path.is_absolute() and path != Path("/sys/fs/cgroup") and not path.is_symlink() and path.is_dir(),
            "actual dedicated cgroup root required")
    rows = Path("/proc/self/cgroup").read_text().splitlines()
    require(len(rows) == 1 and rows[0].startswith("0::/") and
            Path("/sys/fs/cgroup") / rows[0][3:].lstrip("/") == path,
            "host process is not in its handed-off systemd delegated unit")
    require({"cpuset", "memory"} <= set((path / "cgroup.controllers").read_text().split()),
            "systemd did not delegate required cgroup2 controllers")
    leaf = path / "controller"
    leaf.mkdir()
    (leaf / "cgroup.procs").write_text(str(os.getpid()))
    require(str(os.getpid()) in (leaf / "cgroup.procs").read_text().split() and
            not (path / "cgroup.procs").read_text().strip(), "delegated service root retains unowned tasks")
    (path / "cgroup.subtree_control").write_text("+cpuset +memory")
    return {"path": str(path), "device": path.stat().st_dev, "inode": path.stat().st_ino,
            "controller_leaf": str(leaf), "controller_pid": os.getpid()}


def rebase_bank(seed, root, out):
    """Preserve original bank bytes and derive a checked logical-path consumer."""
    source_path = Path(root) / seed["bank"]
    original = checked_json(source_path)
    value = json.loads(json.dumps(original))
    mapping = {}
    for stage, expected in original.get("files", {}).items():
        logical = seed["bank_pgns"].get(stage)
        require(logical is not None, "bank omitted explicit PGN member for " + stage)
        path = Path(root) / logical
        require(pin(ordinary(path)) == {key: expected[key] for key in ("bytes", "sha256")},
                "transported PGN differs from frozen original bank")
        mapping[stage] = {"original_path": expected["path"], "logical_member": logical, "path": str(path)}
        value["files"][stage]["path"] = str(path)
    require({"broad", "high"} <= set(mapping), "actual broad and high opening bank required")
    value["transport"] = {"original_bank": {"logical_member": seed["bank"], **pin(ordinary(source_path))},
                          "pgn_member_map": mapping, "moves_changed": False}
    json_new(out, value)
    return Path(out)


def local_build_command(argv, cwd, cpu):
    peers = importlib.import_module(_SIBLING_PACKAGE + ".peers")
    stdout, _stderr, _record = peers.bounded_run(argv, cwd, cpu=cpu, timeout=600, output_bytes=8 << 20)
    return stdout


def prepare_runner(seed, root, out, *, cpu, execute_command=local_build_command):
    """Rebuild the pinned patched runner from a transported Git object bundle."""
    fastchess = importlib.import_module(_SIBLING_PACKAGE + ".fastchess")
    out = new_external(out)
    out.mkdir(parents=True)
    checkout = out / "checkout"
    bundle = Path(root) / seed["runner"]["bundle"]
    execute_command(["git", "-c", "core.hooksPath=/dev/null", "clone", "--no-hardlinks", str(bundle), str(checkout)], out, cpu)
    execute_command(["git", "-c", "core.hooksPath=/dev/null", "checkout", "--detach", fastchess.PIN], checkout, cpu)
    head = execute_command(["git", "rev-parse", "HEAD"], checkout, cpu).decode().strip()
    require(head == fastchess.PIN, "transported runner bundle does not contain the exact pinned revision")
    originals = {name: ordinary(checkout / name) for name in fastchess.PINS}
    changed = fastchess.patched_sources(originals)
    patch = fastchess.make_patch(originals, changed)
    require(patch == ordinary(fastchess.PATCH), "runner patch differs from reviewed source")
    for name, data in changed.items():
        target = checkout / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    preparation = {"complete": True, "upstream_url": fastchess.URL, "upstream_commit": head,
                   "patch_sha256": fastchess.sha(patch), "source_inputs": fastchess.PINS,
                   "patched_sources": {name: fastchess.sha(data) for name, data in changed.items()},
                   "transport": {"logical_member": seed["runner"]["bundle"], **pin(ordinary(bundle))}}
    json_new(checkout / "rove-preparation.json", preparation)
    fastchess.build(checkout, out / "build", cpu=cpu)
    run.runner_identity(out / "build/fastchess", out / "build/build.json")
    return out / "build/fastchess", out / "build/build.json"


def owned_output_files(root, prefix):
    """Enumerate only a directory this host preparation just created and owns."""
    root = Path(root)
    require(root.is_absolute() and root.is_dir() and not root.is_symlink(), "owned output directory required")
    files, pending = {}, [root]
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir()):
            relative = str(path.relative_to(root)).replace(os.sep, "/")
            member(relative)
            require(not path.is_symlink(), "owned output unexpectedly contains a link")
            if path.is_dir():
                pending.append(path)
            elif path.is_file():
                files[member(prefix + "/" + relative)] = path
            else:
                raise ValueError("owned output unexpectedly contains a special file")
            require(len(files) + len(pending) <= 100000, "owned output archive exceeded explicit file bound")
    return files


def bootstrap_evidence_files(root):
    """Retain named receipt/pipes; never scan a package tree or GPG socket home."""
    base = Path(root) / "bootstrap"
    receipt_path = base / "receipt.json"
    if not receipt_path.exists():
        return {}
    receipt = checked_json(receipt_path)
    result = {"bootstrap/receipt.json": receipt_path}
    for filename in ("ubuntu.list", "aws-cli-public.asc", "awscliv2.zip", "awscliv2.zip.sig"):
        path = base / filename
        if path.exists():
            result["bootstrap/" + filename] = path
    for index, command in enumerate(receipt.get("commands", [])):
        for stream in ("stdout", "stderr"):
            path = Path(command.get(stream, {}).get("path", "."))
            require(path.is_absolute() and path.is_relative_to(base), "bootstrap pipe escaped owned directory")
            result[f"bootstrap/command-{index:03d}.{stream}"] = path
    return result


def run_host_session(handoff, permit, client, publisher, *, journal_path=None, clock=time.time,
                     execute_command=local_build_command, registry_builder=prepare_registry,
                     runner_builder=prepare_runner, stage_factory=run.StageController):
    """Actual host path: source transport -> qualification -> frozen P4/P28.

    Lifecycle termination remains the external controller's responsibility.
    Every outcome, including a failed qualification, preserves its host journal
    and allowlisted evidence before publishing an immutable terminal descriptor.
    """
    plan = aws.AWSPlan.from_dict(handoff["aws_plan"])
    require(handoff.get("format") == "rove4k-cloud-handoff-v1" and handoff.get("campaign_id") == plan.campaign_id,
            "host handoff campaign differs")
    root = Path(handoff["root"])
    seed_root = root / "seed"
    seed = load_seed_manifest(seed_root / "seed.json", handoff["seed_manifest_sha256"])
    revalidate_seed(seed, seed_root)
    seed_object = SeedObject(**handoff["seed"])
    require(pin(ordinary(root / "seed.zip", limit=MAX_SEED)) == {"bytes": seed_object.bytes, "sha256": seed_object.sha256},
            "host archive differs from controller immutable seed")
    require(seed["source_origin"] == permit.get("source_origin", seed["source_origin"]), "permit source origin differs")
    if journal_path is None:
        journal_data = publisher.read_verified(handoff["journal"]["object_key"],
            expected_sha=handoff["journal"]["sha256"], max_bytes=32 << 20)
        journal_path = root / "host.jsonl"
        write_new(journal_path, journal_data)
    else:
        journal_path = Path(journal_path)
        require(journal_path == root / "host.jsonl", "host journal is outside its exact handoff root")
        journal_data = ordinary(journal_path, limit=32 << 20)
    require(pin(journal_data) == {key: handoff["journal"][key] for key in ("bytes", "sha256")},
            "handoff journal length/hash differs")
    original_rows = ledger.read_journal(journal_path, plan.campaign_id)
    require(len(original_rows) == handoff["journal"]["rows"] and original_rows and
            original_rows[-1]["sha256"] == handoff["journal"]["last_sha256"], "handoff journal branch differs")
    outputs = root / "host-output"
    outputs.mkdir()
    stages, archives, failure = [], [], None
    with ledger.Journal(journal_path, plan.campaign_id) as journal:
        try:
            bootstrap_receipt = verify_host_tools(permit, root)
            json_new(outputs / "bootstrap.json", bootstrap_receipt)
            delegation = delegate_controller(handoff["cgroup_root"])
            json_new(outputs / "delegation.json", delegation)
            state = budget.CampaignBudget.replay(plan.campaign_id, journal.rows)
            consumer = observe_consumer(client, plan, state, seed_root / seed["source_tree"], clock=clock)
            json_new(outputs / "consumer.json", consumer.to_record())
            restored_layout = restore_original_layout(seed, seed_root)
            json_new(outputs / "original-layout.json", restored_layout.to_record())
            bank_path = rebase_bank(seed, seed_root, outputs / "bank.json")
            runner, runner_receipt = runner_builder(seed, seed_root, outputs / "runner", cpu=consumer.to_record()["topology"]["allowed_cpus"][0],
                                                    execute_command=execute_command)
            # Archive source transport before games. A scored frozen bundle is
            # created only after actual host-specific registry admission.
            archives += archive_files(publisher, plan.campaign_id,
                {"seed/seed.json": seed_root / "seed.json", "seed/source-seed.zip": root / "seed.zip"})
            broad_plan = None
            for profile, stage in (("test-p4", "broad"), ("test-p28", "high")):
                state = budget.CampaignBudget.replay(plan.campaign_id, journal.rows)
                aws.verify_owned_lease(client, plan, state, clock(), caller_kind="instance")
                registry_path = registry_builder(seed, seed_root, outputs / ("qualify-" + profile), consumer, profile,
                    execute_command=execute_command, restored_layout=restored_layout)
                archives += archive_files(publisher, plan.campaign_id,
                    owned_output_files(registry_path.parent, "qualification/" + profile))
                frozen = outputs / ("plan-" + stage)
                extra = {} if stage == "broad" else {"broad_plan": broad_plan, "broad_journal": journal_path}
                run.freeze_plan(plan.campaign_id, profile, registry_path, bank_path, registry.file_sha(bank_path),
                    runner, runner_receipt, frozen, stage=stage,
                    snapshot=topology.Topology.from_record(consumer.to_record()["topology"]), **extra)
                archives += archive_files(publisher, plan.campaign_id, owned_output_files(frozen, "frozen/" + stage))
                state = budget.CampaignBudget.replay(plan.campaign_id, journal.rows)
                driver = stage_factory(frozen / "plan.json", outputs / ("run-" + stage), journal, publisher, state,
                    lease_verifier=lambda current: aws.verify_owned_lease(client, plan, current, clock(), caller_kind="instance"))
                report = driver.execute(Path(handoff["cgroup_root"]))
                stages.append({"stage": stage, "profile": profile, "report": report})
                summary_out = outputs / ("summary-" + stage)
                collect.write_summary(report["summary"], summary_out)
                archives += archive_files(publisher, plan.campaign_id, owned_output_files(summary_out, "summary/" + stage))
                archives += archive_files(publisher, plan.campaign_id, owned_output_files(outputs / ("run-" + stage), "run/" + stage))
                require(report.get("complete") is True, "stage retained incomplete pairs/cleanup; high stage cannot begin")
                broad_plan = frozen / "plan.json" if stage == "broad" else broad_plan
            require(verify_host_tools(permit, root) == bootstrap_receipt,
                    "installed bootstrap tools changed before/post host session")
        except BaseException as error:
            failure = {"type": type(error).__name__, "message": str(error)}
            journal.append("campaign.host_error", failure)
        finally:
            # Failed inputs stay local and are allowlisted for retention. The
            # runner checkout's Git database is neither traversed nor uploaded.
            files = {"host/consumer.json": outputs / "consumer.json", "host/delegation.json": outputs / "delegation.json",
                     "host/bootstrap.json": outputs / "bootstrap.json", "host/original-layout.json": outputs / "original-layout.json"}
            files = {key: path for key, path in files.items() if path.exists()}
            if files:
                archives += archive_files(publisher, plan.campaign_id, files)
            archives += archive_files(publisher, plan.campaign_id, bootstrap_evidence_files(root))
            already = {(item["logical"], item["sha256"]) for item in archives}
            for name in ("qualify-test-p4", "qualify-test-p28", "plan-broad", "plan-high", "run-broad", "run-high",
                         "summary-broad", "summary-high", "runner/build"):
                owned = outputs / name
                if owned.is_dir():
                    retained = owned_output_files(owned, "retained/" + name)
                    retained = {logical: path for logical, path in retained.items()
                                if (logical, pin(ordinary(path, limit=MAX_SEED))["sha256"]) not in already}
                    archives += archive_files(publisher, plan.campaign_id, retained)
            journal.append("campaign.host_terminal", {"complete": failure is None, "stages": len(stages), "failure": failure})
    raw = ordinary(journal_path, limit=32 << 20)
    journal_pin = pin(raw)
    journal_key = plan.campaign_id + "/host/" + handoff["host_job_id"] + "/journal-" + journal_pin["sha256"] + ".jsonl"
    journal_ack = publisher.publish(journal_path, journal_key)
    require(journal_ack.get("verified") is True and journal_ack.get("sha256") == journal_pin["sha256"],
            "host terminal journal is not remotely acknowledged")
    rows = ledger.read_journal(journal_path, plan.campaign_id)
    terminal = {"format": "rove4k-cloud-terminal-v1", "campaign_id": plan.campaign_id,
                "host_job_id": handoff["host_job_id"], "handoff_sha256": ledger.digest(handoff),
                "seed_sha256": seed_object.sha256, "source_origin": seed["source_origin"],
                "complete": failure is None and len(stages) == 2 and all(r["report"]["complete"] for r in stages),
                "failure": failure, "stages": stages, "archives": archives,
                "journal": {"object_key": journal_key, **journal_pin, "last_sha256": rows[-1]["sha256"], "rows": len(rows)},
                "termination_observed": False, "scope": "TEST P4/P28 full 4KiB cohort; no TCEC W256 strength claim"}
    path = root / "terminal.json"
    terminal_pin = json_new(path, terminal)
    ack = publisher.publish(path, plan.campaign_id + "/host/" + handoff["host_job_id"] + "/terminal.json")
    require(ack.get("verified") is True and ack.get("sha256") == terminal_pin["sha256"],
            "host terminal descriptor is not remotely acknowledged")
    return terminal


def collect_host_result(*, plan, handoff, publisher):
    """Read independently verified terminal objects, then validate the original chain."""
    key = plan.campaign_id + "/host/" + handoff["host_job_id"] + "/terminal.json"
    raw = publisher.read_verified(key, max_bytes=32 << 20)
    terminal = json.loads(raw)
    require(terminal.get("format") == "rove4k-cloud-terminal-v1" and terminal.get("campaign_id") == plan.campaign_id and
            terminal.get("host_job_id") == handoff["host_job_id"] and
            terminal.get("handoff_sha256") == ledger.digest(handoff) and terminal.get("seed_sha256") == handoff["seed"]["sha256"],
            "remote terminal does not belong to the exact handoff")
    descriptor = terminal["journal"]
    journal_raw = publisher.read_verified(descriptor["object_key"], expected_sha=descriptor["sha256"], max_bytes=32 << 20)
    require(pin(journal_raw) == {key: descriptor[key] for key in ("bytes", "sha256")}, "terminal journal bytes differ")
    path = publisher.root / ("collected-host-" + descriptor["sha256"] + ".jsonl")
    if path.exists():
        require(ordinary(path, limit=32 << 20) == journal_raw, "previous collected journal differs")
    else:
        write_new(path, journal_raw)
    rows = ledger.read_journal(path, plan.campaign_id)
    prefix = handoff["journal"]
    require(len(rows) == descriptor["rows"] and rows and rows[-1]["sha256"] == descriptor["last_sha256"] and
            len(rows) >= prefix["rows"] > 0 and rows[prefix["rows"] - 1]["sha256"] == prefix["last_sha256"],
            "terminal journal changed its original handoff branch")
    for archived in terminal.get("archives", []):
        remote = archived["remote"]
        require(remote.get("verified") is True and remote.get("sha256") == archived["sha256"], "terminal archive lacks acknowledgement")
        publisher.read_verified(remote["object_key"], expected_sha=archived["sha256"], max_bytes=MAX_SEED)
    return {"terminal": terminal, "rows": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    inspect = actions.add_parser("inspect", help="validate a seed without API calls, engines, or imports from it")
    inspect.add_argument("--manifest", type=Path, required=True)
    inspect.add_argument("--manifest-sha256", required=True)
    unpack = actions.add_parser("materialize", help="verify an explicit local archive, without executing its code")
    unpack.add_argument("--archive", type=Path, required=True)
    unpack.add_argument("--manifest-sha256", required=True)
    unpack.add_argument("--out", type=Path, required=True)
    host = actions.add_parser("host", help="explicit EC2 host consumer; requires a controller handoff and execution permit")
    for key in ("handoff", "permit"):
        host.add_argument("--" + key, type=Path, required=True)
        host.add_argument("--" + key + "-sha256", required=True)
    args = parser.parse_args(argv)
    if args.action == "inspect":
        seed = load_seed_manifest(args.manifest, args.manifest_sha256)
        result = {"source_origin": seed["source_origin"], "members": len(seed["members"]),
                  "qualification": False, "engine_execution_performed": False, "aws_calls_performed": False}
    elif args.action == "materialize":
        seed = materialize_seed_archive(args.archive, args.out, expected_manifest_sha256=args.manifest_sha256)
        result = {"root": str(args.out), "qualification": False, "members": len(seed["members"])}
    else:
        # The campaign module validates and consumes the permit and the original
        # handoff journal. Never import or execute arbitrary seed code first.
        campaign = bootstrap_module()
        require(callable(getattr(campaign, "run_host_handoff", None)),
                "missing production campaign.run_host_handoff consumer")
        result = campaign.run_host_handoff(args.handoff, args.handoff_sha256, args.permit, args.permit_sha256)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


canonical_provider()
if __name__ == "__main__":
    raise SystemExit(main())
