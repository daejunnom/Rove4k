#!/usr/bin/env python3
"""Offline exact source seed preparation and explicit immutable S3 publication.

Transport is never native qualification, scoring, or permission to launch EC2.
Only declared files and clean pinned Git blobs enter a new external directory.
Uncertain upload recovery performs reads only and never resends a PutObject.
"""
from __future__ import annotations

import argparse
import ast
import base64
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import zipfile

# Default script and isolated entrypoints must not dirty the source checkout
# while reading the exact committed closure below.
sys.dont_write_bytecode = True
if __package__ in (None, ""):
    # Isolated Python omits the script directory from its import search path.
    # Only this source-bound sibling directory is admitted for CLI modules.
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from . import aws, ledger
except ImportError:
    import aws
    import ledger


MAX_SEED = 128 << 20
MAX_MEMBER = 32 << 20
FASTCHESS = "ebfd64cb7fac80d4822c50b07dca4fe934779d21"
SHA = re.compile(r"[a-f0-9]{64}\Z")
HOST_MODULES = ("cloud_runtime", "campaign", "aws", "aws_infrastructure", "budget", "ledger", "registry",
                "placement", "topology", "peer_runtime", "peers", "run", "wave", "collect", "durability", "fastchess", "seed")
CORE_R = ("engines/experiments/tcec-next/profile_verify.py", "engines/experiments/tcec-next/profile_compiler.py",
          "engines/experiments/tcec-next/target_runtime.py", "engines/scripts/production.py",
          "engines/scripts/production_input.py", "engines/scripts/production_source_bundle.py",
          "engines/scripts/source_composition.py", "engines/experiments/tiny-d-submission/source_inputs.py",
          "engines/experiments/tcec-next/profile_dependencies.py", "engines/common/board.c",
          "engines/common/move.c", "engines/common/protocol.c", "engines/common/search.c")
# These files are needed only by the new league profiles. Keep the legacy
# P4/P28 source closure unchanged; neither declaration authorizes a league run.
LEAGUE_HOST_MODULES = ("memory_observation", "overhead", "league_probe", "diagnostic_candidates", "peak_capacity", "peak_probe_session", "peak_ready_probe",
                       "peak_receipt", "peak_supervisor", "rove_runtime_observation", "rove_worker_observer", "rove_vma_observer", "functional_uci_probe", "functional_probe_session")
LEAGUE_CORE_R = ("engines/scripts/league_resource_profiles.py", "engines/experiments/tcec-scope/verify.py",
                 "engines/compact/tiny-entry-d/verify.py", "engines/tests/chess_oracle.py")
LEAGUE_PROFILES = ("test-p16", "test-p192")
# Exact declarations whose values are used only by league profile branches.
# This is scanner metadata, not a blanket exemption for the owning file.
LEAGUE_DEPENDENCY_DECLARATIONS = {
    "engines/experiments/strength/seed.py": ("LEAGUE_CORE_R", ("engines/scripts/league_resource_profiles.py", "engines/experiments/tcec-scope/verify.py", "engines/compact/tiny-entry-d/verify.py", "engines/tests/chess_oracle.py")),
    "engines/experiments/strength/cloud_runtime.py": ("LEAGUE_HOST_SOURCE_FILES", ("engines/experiments/strength/memory_observation.py", "engines/experiments/strength/overhead.py", "engines/experiments/strength/league_probe.py", "engines/experiments/strength/diagnostic_candidates.py", "engines/experiments/strength/peak_capacity.py", "engines/experiments/strength/peak_probe_session.py", "engines/experiments/strength/peak_ready_probe.py", "engines/experiments/strength/peak_receipt.py", "engines/experiments/strength/peak_supervisor.py", "engines/experiments/strength/rove_runtime_observation.py", "engines/experiments/strength/rove_worker_observer.py", "engines/experiments/strength/rove_vma_observer.py", "engines/experiments/strength/functional_uci_probe.py", "engines/experiments/strength/functional_probe_session.py", "engines/scripts/league_resource_profiles.py", "engines/experiments/tcec-scope/verify.py", "engines/compact/tiny-entry-d/verify.py", "engines/tests/chess_oracle.py")),
    "engines/experiments/strength/registry.py": ("LEAGUE_PROFILE_OWNER", "engines/scripts/league_resource_profiles.py"),
    "engines/experiments/strength/peer_runtime.py": ("LEAGUE_SOURCE_FILES", ("engines/scripts/league_resource_profiles.py",)),
    "engines/experiments/tcec-next/profile_verify.py": ("LEAGUE_PROFILE_OWNER", "engines/scripts/league_resource_profiles.py"),
    "engines/experiments/tcec-next/profile_rules.py": ("LEAGUE_OWNER", "engines/scripts/league_resource_profiles.py"),
    "engines/experiments/tcec-next/profile_build.py": ("LEAGUE_PROFILES", "engines/scripts/league_resource_profiles.py"),
}
# These are precise AST-value fingerprints of reviewed opt-in candidate
# inventories. Some values contain symbol references, so literal_eval cannot
# validate them. For legacy seeds only, exclude the five exact declarations;
# identical paths occurring anywhere else in the owner remain dependencies.
LEAGUE_EXPERIMENT_DECLARATIONS = {
    "engines/experiments/tcec-next/profile_build.py": (
        ("LEAGUE_EXPERIMENTS", "960fcf7bdb7322badfd4d011b92b87a2d15c47012bd8a4a748797121d314bf41"),
        ("LEAGUE_SUPPORT", "1cd9a170bceceae29d2062120715a84d06834fbb67e311d4c69e2687ab628a3b")),
    "engines/experiments/tcec-next/profile_rules.py": (
        ("LEAGUE_CANDIDATES", "ca3e65ce314eae6d8e76869bbf49aff748121777980286526c4707c2078667fc"),),
    "engines/experiments/tcec-next/profile_verify.py": (
        ("LEAGUE_VARIANTS", "49def85c55f44339b3aa8e6cec621003bf259ca20403d28c3e0fd7e5c2e1ac66"),
        ("LEAGUE_EP_SUPPORT", "91d711b05ed2030ac4c49210c5de89c26abe54072ec8be25468bd46204c4acdd")),
}
LEAGUE_CAMPAIGN_CI = "engines/experiments/strength/campaign_ci.py"


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def named_python_dependencies(raw, *, source_name, league_required=True):
    """Collect named paths, excluding only structurally identified metadata.

    The legacy exception applies to specific reviewed lazy declarations, not
    every occurrence of a path in the file that owns such a declaration.
    """
    tree = ast.parse(raw)
    metadata_nodes = set()
    if source_name == "engines/experiments/strength/seed.py":
        declarations = [node for node in tree.body if isinstance(node, ast.Assign)
                        and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                        and node.targets[0].id == "LEAGUE_DEPENDENCY_DECLARATIONS"]
        require(len(declarations) == 1
                and ast.literal_eval(declarations[0].value) == LEAGUE_DEPENDENCY_DECLARATIONS,
                "seed owner inventory metadata differs")
        metadata_nodes = {id(node) for node in ast.walk(declarations[0].value)}
        experiments = [node for node in tree.body if isinstance(node, ast.Assign)
                       and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id == "LEAGUE_EXPERIMENT_DECLARATIONS"]
        require(len(experiments) == 1
                and ast.literal_eval(experiments[0].value) == LEAGUE_EXPERIMENT_DECLARATIONS,
                "seed experiment inventory metadata differs")
        metadata_nodes.update(id(node) for node in ast.walk(experiments[0].value))
        campaign = [node for node in tree.body if isinstance(node, ast.Assign)
                    and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "LEAGUE_CAMPAIGN_CI"]
        require(len(campaign) == 1 and ast.literal_eval(campaign[0].value) == LEAGUE_CAMPAIGN_CI,
                "seed campaign metadata differs")
        metadata_nodes.update(id(node) for node in ast.walk(campaign[0].value))
    if not league_required and source_name in LEAGUE_DEPENDENCY_DECLARATIONS:
        symbol, expected = LEAGUE_DEPENDENCY_DECLARATIONS[source_name]
        declarations = [node for node in tree.body if isinstance(node, ast.Assign)
                        and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                        and node.targets[0].id == symbol]
        if declarations:
            require(len(declarations) == 1 and ast.literal_eval(declarations[0].value) == expected,
                    "league dependency declaration differs")
            metadata_nodes.update(id(node) for node in ast.walk(declarations[0].value))
    if not league_required and source_name in LEAGUE_EXPERIMENT_DECLARATIONS:
        for symbol, expected_hash in LEAGUE_EXPERIMENT_DECLARATIONS[source_name]:
            declarations = [node for node in tree.body if isinstance(node, ast.Assign)
                            and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                            and node.targets[0].id == symbol]
            if declarations:
                require(len(declarations) == 1 and hashlib.sha256(
                    ast.dump(declarations[0].value).encode("utf-8")).hexdigest() == expected_hash,
                    "league experiment dependency declaration differs")
                metadata_nodes.update(id(node) for node in ast.walk(declarations[0].value))
    if not league_required and source_name == LEAGUE_CAMPAIGN_CI:
        # bind_materializer_source binds league paths only under this exact
        # feature condition. Match the complete statements, so an additional
        # use of the same path remains visible to the closure check.
        test = ast.dump(ast.parse("league <= set(values)", mode="eval").body)
        templates = (
            'require(values["LEAGUE_HOST_MODULES"] == ("memory_observation",) and '
            'values["LEAGUE_CORE_R"] == ("engines/scripts/league_resource_profiles.py",), '
            '"committed league materializer source closure differs")',
            'require(values["LEAGUE_HOST_MODULES"] in (("memory_observation",), '
            '("memory_observation", "overhead", "league_probe", "diagnostic_candidates", "peak_capacity", "peak_probe_session", "peak_ready_probe", '
            '"peak_receipt", "peak_supervisor"), '
            '("memory_observation", "overhead", "league_probe", "diagnostic_candidates", "peak_capacity", "peak_probe_session", "peak_ready_probe", '
            '"peak_receipt", "peak_supervisor", "rove_runtime_observation", "rove_worker_observer", "rove_vma_observer")) and '
            'values["LEAGUE_CORE_R"] == ("engines/scripts/league_resource_profiles.py",), '
            '"committed league materializer source closure differs")',
            'names += ("engines/experiments/strength/memory_observation.py", '
            '"engines/scripts/league_resource_profiles.py")',
            'require(values["LEAGUE_HOST_MODULES"] in (("memory_observation",), '
            '("memory_observation", "overhead", "league_probe", "diagnostic_candidates", "peak_capacity", "peak_probe_session", "peak_ready_probe", '
            '"peak_receipt", "peak_supervisor")) and '
            'values["LEAGUE_CORE_R"] == ("engines/scripts/league_resource_profiles.py",), '
            '"committed league materializer source closure differs")',
        )
        expected = {ast.dump(ast.parse(value).body[0]) for value in templates}
        for function in tree.body:
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)) and function.name == "bind_materializer_source":
                for branch in function.body:
                    if isinstance(branch, ast.If) and ast.dump(branch.test) == test:
                        for statement in branch.body:
                            if (ast.dump(statement) in expected or hashlib.sha256(ast.dump(statement).encode("utf-8")).hexdigest()
                                    == "b5025cf1c17efb69f2577490e22395341bf23413bc0128227246e81fd735487f"):
                                metadata_nodes.update(id(node) for node in ast.walk(statement))
    return tuple(node.value for node in ast.walk(tree)
                 if id(node) not in metadata_nodes and isinstance(node, ast.Constant)
                 and isinstance(node.value, str) and node.value.startswith("engines/")
                 and node.value.endswith(".py"))


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def member(value):
    require(isinstance(value, str) and value and "\\" not in value and ":" not in value and "\0" not in value,
            "normalized explicit seed member required")
    parts = value.split("/")
    require(not PurePosixPath(value).is_absolute() and all(part not in ("", ".", "..") for part in parts),
            "seed member escaped its relative namespace")
    blocked = {".git", ".aws", ".ssh", "node_modules", "dist", "dist-server", "coverage", "models",
               "checkpoints", ".cache", "inventory.json", "package-lock.json"}
    require(not any(part.casefold() in blocked or part.casefold().startswith(".env") or
                    re.search(r"credential|service[-_ ]?account|api[-_ ]?key|ssh[-_ ]?key|^id_(rsa|ed25519)$", part, re.I)
                    for part in parts), "protected or heavy input cannot enter a source seed")
    return value


def ordinary(path, *, limit=MAX_MEMBER):
    path = Path(path)
    require(path.is_absolute(), "absolute explicit input required")
    for part in path.parts[1:]:
        member(part)
    require(not any(item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction())
                    for item in (path, *path.parents)), "input must not follow links")
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit,
            "bounded ordinary single-link input required")
    raw = path.read_bytes()
    after = path.stat()
    stamp = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
    require(stamp(before) == stamp(after) and len(raw) == before.st_size, "input changed during collection")
    return raw


def input_descriptor(value, *, limit=MAX_MEMBER):
    require(isinstance(value, dict) and set(value) == {"path", "bytes", "sha256"}, "explicit path/byte/SHA input required")
    require(isinstance(value["path"], (str, Path)) and Path(value["path"]).is_absolute()
            and type(value["bytes"]) is int and 0 <= value["bytes"] <= limit
            and isinstance(value["sha256"], str) and SHA.fullmatch(value["sha256"]),
            "bounded exact input identity required")
    return value


def checked_input(value, *, limit=MAX_MEMBER):
    input_descriptor(value, limit=limit)
    raw = ordinary(value["path"], limit=limit)
    require(pin(raw) == {key: value[key] for key in ("bytes", "sha256")}, "downloaded input differs from its declared pin")
    return raw


def write_new(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(raw); output.flush(); os.fsync(output.fileno())
    return pin(raw)


def new_external(path):
    path = Path(path)
    require(path.is_absolute() and not path.exists(), "new absolute external staging directory required")
    for part in path.parts[1:]:
        member(part)
    for item in (path, *path.parents):
        require(not item.is_symlink() and not (hasattr(item, "is_junction") and item.is_junction())
                and not (item / ".git").exists(), "staging must stay outside Git and links")
    member(path.name)
    return path


def git(checkout, *arguments, limit=MAX_SEED, input_bytes=None):
    env = os.environ.copy()
    for name in list(env):
        if name.startswith("GIT_"):
            del env[name]
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0",
               GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
               GIT_ALLOW_PROTOCOL="")
    result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-c",
        "core.hooksPath=" + os.devnull, "-c", "protocol.allow=never", "--literal-pathspecs", "-C", str(checkout), *arguments],
        capture_output=True, input=input_bytes, env=env, timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    require(result.returncode == 0 and len(result.stdout) <= limit, "local pinned Git operation failed or exceeded its bound")
    return result.stdout


def exact_names(root, prefixes, tracked):
    """Metadata-only allowlist scan; never descend into blocked directories."""
    seen = set()
    pending = [root / prefix for prefix in prefixes]
    visited = set()
    while pending:
        path = pending.pop()
        relative = path.relative_to(root).as_posix()
        member(relative)
        require(not path.is_symlink() and not (hasattr(path, "is_junction") and path.is_junction()),
                "selected source namespace contains a link")
        if path.is_dir():
            if relative in visited:
                continue
            visited.add(relative)
            pending.extend(path.iterdir())
        else:
            require(path.is_file() and relative in tracked, "selected source root contains an unlisted file")
            seen.add(relative)
        require(len(seen) + len(pending) + len(visited) <= 40000, "selected source namespace exceeds its bound")
    require(seen == tracked, "selected committed source namespace is missing a file")


def checkout_files(value, origin, *, byte_budget=None, member_budget=None, league_required=False):
    require(type(league_required) is bool, "explicit league closure selection required")
    require(isinstance(value, dict) and set(value) == {"path", "commit", "paths"}, "explicit clean checkout/commit/paths required")
    root = Path(value["path"])
    require(root.is_absolute() and root.is_dir() and not root.is_symlink(), "ordinary explicit source checkout required")
    commit = value["commit"]
    require(commit == origin["head_sha"] and re.fullmatch(r"[a-f0-9]{40}(?:[a-f0-9]{24})?", commit),
            "source checkout differs from the sealed CI commit")
    require(git(root, "rev-parse", "HEAD").decode().strip() == commit, "checkout HEAD is not the selected exact commit")
    require(not git(root, "status", "--porcelain=v1", "--untracked-files=no"), "dirty tracked checkout cannot be a source seed")
    prefixes = value["paths"]
    require(isinstance(prefixes, list) and prefixes and len(prefixes) == len(set(prefixes)), "explicit source path selection required")
    prefixes = [member(name) for name in prefixes]
    records = git(root, "ls-files", "--stage", "-z", "--", *prefixes).split(b"\0")
    blobs, modes = {}, {}
    for record in filter(None, records):
        meta, raw_name = record.split(b"\t", 1)
        mode, blob, stage = meta.decode().split()
        name = member(raw_name.decode())
        require(mode in ("100644", "100755") and stage == "0", "symlink/submodule/conflict cannot enter source seed")
        require(name not in blobs, "ambiguous selected source member")
        blobs[name] = blob
        modes[name] = 0o700 if mode == "100755" else 0o600
    require(blobs, "selected source checkout is empty")
    if member_budget is not None:
        require(len(blobs) <= member_budget, "source metadata exceeds remaining seed member count")
    if byte_budget is not None:
        identities = list(blobs.values())
        rows = git(root, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                   input_bytes=("\n".join(identities) + "\n").encode()).decode().splitlines()
        require(len(rows) == len(identities), "source object size metadata is incomplete")
        sizes = []
        for expected, row in zip(identities, rows):
            fields = row.split()
            require(len(fields) == 3 and fields[:2] == [expected, "blob"] and fields[2].isdigit(),
                    "source object metadata differs from its selected Git blob")
            size = int(fields[2])
            require(size <= MAX_MEMBER, "source object metadata exceeds the per-member bound")
            sizes.append(size)
        require(sum(sizes) <= byte_budget, "source metadata exceeds remaining expanded seed bound")
    exact_names(root, prefixes, set(blobs))
    result = {}
    for name, blob in sorted(blobs.items()):
        raw = git(root, "cat-file", "blob", blob, limit=MAX_MEMBER)
        result[name] = (raw, modes[name])
    required = {"engines/experiments/strength/" + name + ".py" for name in HOST_MODULES}
    if origin.get("rove_required", True):
        required.update(CORE_R)
    if league_required:
        required.update("engines/experiments/strength/" + name + ".py" for name in LEAGUE_HOST_MODULES)
        required.update(LEAGUE_CORE_R)
    require(required <= set(result), "source seed omitted the host/R production code closure")
    own = "engines/experiments/strength/seed.py"
    require(result[own][0].replace(b"\r\n", b"\n") == ordinary(Path(__file__).absolute()).replace(b"\r\n", b"\n"),
            "selected committed seed producer differs from this executing tool")
    # Discover the newly factored input reader from the actual selected sources.
    for path, constant in ((CORE_R[0], "INPUT_READER"), (CORE_R[1], "INPUT_PATH")):
        if path not in result:
            continue
        assignments = {node.targets[0].id: node.value.value for node in ast.walk(ast.parse(result[path][0]))
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)}
        require(constant in assignments and member(assignments[constant]) in result,
                "selected qualifier/compiler input helper is absent")
    # Require named repository Python dependencies; this is a closure check,
    # not a module import or a scan of unrelated generated trees.
    selected = set(result)
    for name, (raw, _) in list(result.items()):
        if not name.endswith(".py"):
            continue
        for target in named_python_dependencies(raw, source_name=name, league_required=league_required):
            member(target)
            require(target in selected, "named production Python dependency omitted: " + target)
    require(not git(root, "status", "--porcelain=v1", "--untracked-files=no"), "source checkout changed during collection")
    require(git(root, "rev-parse", "HEAD").decode().strip() == commit, "source commit changed during collection")
    return result


def archive_members(raw, *, expanded_limit=None):
    require(len(raw) <= MAX_SEED, "source ZIP exceeds transport bound")
    expanded_limit = MAX_SEED if expanded_limit is None else expanded_limit
    require(type(expanded_limit) is int and 0 < expanded_limit <= runtime().JOINT_EXPANDED_SEED,
            "bounded source ZIP expansion limit required")
    result = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        require(len(infos) <= runtime().MAX_SEED_MEMBERS,
                "source ZIP exceeds the total member count bound")
        total, seen = 0, set()
        for info in infos:
            name = member(info.filename)
            mode = info.external_attr >> 16
            require(not info.is_dir() and not info.flag_bits & 1 and stat.S_IFMT(mode) in (0, stat.S_IFREG),
                    "source ZIP contains a link/directory/encrypted member")
            total += info.file_size
            require(name not in seen and info.file_size <= MAX_MEMBER and total <= expanded_limit,
                    "source ZIP has duplicate or excessive members")
            seen.add(name)
        for info in infos:
            name, mode = info.filename, info.external_attr >> 16
            result[name] = (archive.read(info), 0o700 if mode & 0o111 else 0o600)
    require(result, "source ZIP is empty")
    return result


def dependency_evidence(content, build, record, *, original_build=None):
    """Preserve final dependency evidence bytes; never run or certify a compiler."""
    if record.get("source_dependencies") is None:
        return
    require(record["source_dependencies"] == {"path": "engines/experiments/tcec-next/profile_dependencies.py",
            "variant": "unused-includes"}, "unknown final dependency source declaration")

    def checked(relative, expected):
        logical = build + "/" + member(relative)
        require(logical in content and pin(content[logical][0]) == expected,
                "final dependency evidence is missing or changed: " + relative)
        return content[logical][0]

    def proofs(value):
        if isinstance(value, dict):
            name = value.get("path")
            if isinstance(name, str) and {"bytes", "sha256"} <= set(value):
                if original_build is not None and name.startswith(original_build + "/"):
                    checked(name[len(original_build) + 1:], {key: value[key] for key in ("bytes", "sha256")})
                elif not PurePosixPath(name).is_absolute():
                    relative = member(name)
                    if relative.startswith("engines/") and build + "/" + relative not in content:
                        relative = "inputs/" + relative
                    checked(relative, {key: value[key] for key in ("bytes", "sha256")})
            for item in value.values():
                proofs(item)
        elif isinstance(value, list):
            for item in value:
                proofs(item)
    proofs(record)

    attempts = record.get("attempts")
    require(isinstance(attempts, list) and attempts, "final dependency attempt evidence is absent")
    for attempt in attempts:
        gate = attempt.get("dependency_gate")
        if gate is None:
            continue  # Identity transforms have no compiler gate to transport.
        require(isinstance(gate, dict), "dependency gate must be an exact evidence object")
        directory = member(attempt["directory"])
        gate_root = directory + "/dependency-gate/"
        before = checked(gate_root + "before.c", gate["input"])
        after = checked(gate_root + "after.c", gate["output"])
        expanded = [checked(gate_root + label + ".i", gate["expanded"]) for label in ("before", "after")]
        require(expanded[0] == expanded[1], "full dependency expanded input bytes differ")
        native = {key: attempt["native_" + key] for key in ("bytes", "sha256")}
        require(gate.get("native") == native and checked(gate_root + "x", native) ==
                checked(directory + "/native/x", native), "full dependency native bytes differ")
        for label, stdin in (("before", before), ("after", after), ("native", before), ("shipping", after)):
            kind = directory + ("-compile" if label == "shipping" else "-dependencies-" + label)
            rows = [row for row in record.get("commands", []) if row.get("kind") == kind]
            require(len(rows) == 1, "final dependency command evidence is ambiguous or absent")
            row = rows[0]
            stdout_name = PurePosixPath(row["stdout"]["path"]).name
            stdin_name = str(PurePosixPath(stdout_name).with_suffix(".stdin"))
            checked(stdin_name, pin(stdin))
            for stream in ("stdout", "stderr"):
                observed = row[stream]
                basename = PurePosixPath(observed["path"]).name
                require(basename.startswith("tool-") and basename.endswith("." + stream),
                        "final dependency stream has no owned basename")
                checked(basename, {key: observed[key] for key in ("bytes", "sha256")})


def origin_check(value):
    require(isinstance(value, dict) and set(value) == {"repository", "head_sha", "run_id", "run_attempt"},
            "exact source CI origin required")
    require(re.fullmatch(r"[\w.-]+/[\w.-]+", str(value["repository"])) and
            re.fullmatch(r"[a-f0-9]{40}(?:[a-f0-9]{24})?", str(value["head_sha"])) and
            all(re.fullmatch(r"[1-9][0-9]*", str(value[key])) for key in ("run_id", "run_attempt")),
            "invalid or ambiguous CI origin")
    return json.loads(ledger.canonical(value))


def workflow_binding(config, content, origin, api_head):
    """Bind local clean Git objects and pinned originals using the common worker."""
    proof = config.get("workflow_provenance")
    if proof is None:
        require(api_head == origin["head_sha"], "unequal API/checkout heads require explicit PR provenance")
        return {"kind": "artifact-head-equality", "api_head_sha": api_head,
                "checkout_sha": origin["head_sha"], "inputs": {}}
    consumer = runtime()
    checkout = config["checkout"]["path"]
    require(config["checkout"]["commit"] == origin["head_sha"]
            and git(checkout, "rev-parse", "HEAD").decode().strip() == origin["head_sha"]
            and not git(checkout, "status", "--porcelain=v1", "--untracked-files=no"),
            "workflow provenance requires the exact clean execution checkout")
    raw = git(checkout, "cat-file", "commit", origin["head_sha"])
    tree, _parents = consumer.git_commit_fields(raw, origin["head_sha"])
    tree_raw = git(checkout, "cat-file", "tree", tree)
    def read(name):
        require(name in content, "pinned workflow provenance input is absent: " + name)
        return content[name][0]
    return consumer.bind_workflow_provenance(origin, api_head, proof, read,
                                             execution_commit=raw, execution_tree=tree_raw)


def runtime():
    import importlib
    name = (__package__ + ".cloud_runtime") if __package__ else "cloud_runtime"
    module = sys.modules.get("rove4k_cloud_runtime") or importlib.import_module(name)
    return module.canonical_provider()


def peer_originals(selected, content, source_tree):
    """Reuse the selected producer's literal source-blob policy without imports."""
    policy = ast.parse(content[source_tree + "/engines/experiments/strength/peers.py"][0])
    assignments = {node.targets[0].id: node.value for node in policy.body if isinstance(node, ast.Assign)
                   and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)}
    blobs = ast.literal_eval(assignments["SOURCE_BLOBS"])
    peers = assignments["PEERS"]
    require(isinstance(peers, ast.Dict), "selected peer policy is not a literal pinned map")
    declarations = {}
    for key, call in zip(peers.keys, peers.values):
        require(isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "PeerSpec",
                "selected peer declaration is unsupported")
        args = [ast.literal_eval(value) for value in call.args]
        declarations[ast.literal_eval(key)] = args
    family, prefix = selected["family"], member(selected["source"])
    require(family in blobs and family in declarations, "unknown external peer")
    args = declarations[family]
    require(selected.get("repository") == args[1] and selected.get("revision") == args[2]
            and selected.get("license") == prefix + "/LICENSE", "peer repository/revision/license differs from pinned policy")
    actual = {name[len(prefix) + 1:]: raw for name, (raw, _) in content.items() if name.startswith(prefix + "/")}
    require(set(actual) == set(blobs[family]), "peer prefix must contain its exact original source closure only")
    for name, raw in actual.items():
        git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        require(git_blob == blobs[family][name], "external peer source/license differs from pinned Git blob: " + name)


def validate_runner(config, content, source_tree, checkout):
    runner = config["runner"]
    require(runner["revision"] == FASTCHESS and runner.get("patch") in content and runner.get("license") in content,
            "pinned runner requires original license and tracked source-only patch")
    original_patch = source_tree + "/engines/experiments/strength/patches/fastchess-rove.patch"
    require(original_patch in content and content[runner["patch"]][0] == content[original_patch][0],
            "declared runner patch differs from selected committed source")
    descriptor = config["inputs"].get(runner["bundle"])
    require(descriptor is not None, "runner Git bundle must be an exact downloaded external input")
    path = Path(descriptor["path"])
    git(checkout, "bundle", "verify", str(path))
    heads = git(checkout, "bundle", "list-heads", str(path)).decode().splitlines()
    require(any(line.split(" ", 1)[0] == FASTCHESS for line in heads), "runner bundle does not advertise the exact pinned revision")


def original_references(content, mappings, source_builds, origin):
    """Check file pins and the target reference's explicit build-directory pin.

    A target-runtime reference names the original build *directory*, while its
    byte/SHA pair identifies build.json.  Only that named record contract and
    an already selected sealed source build may use this correspondence.
    """
    def original_member(path):
        matched = [row for row in mappings if path.startswith(row["original_root"] + "/")]
        require(len(matched) == 1, "original evidence path has no unique explicit transport root")
        row = matched[0]
        return row["seed_prefix"] + path[len(row["original_root"]):]

    roots = set()
    for key, selected in source_builds.items():
        require(isinstance(key, tuple) and len(key) == 2 and all(type(item) is str for item in key)
                and set(selected) == {"path", "member"} and type(selected["path"]) is str
                and selected["path"] not in roots, "selected source build identity is ambiguous")
        roots.add(selected["path"])
        logical = member(selected["member"])
        require(logical == original_member(selected["path"] + "/build.json") and logical in content,
                "selected source build omitted its exact build.json")

    counts = {"file_references": 0, "source_build_references": 0}

    def expected_pin(value):
        require(type(value.get("bytes")) is int and 0 <= value["bytes"] <= MAX_MEMBER
                and type(value.get("sha256")) is str and SHA.fullmatch(value["sha256"]),
                "original evidence requires an exact typed file pin")
        return {key: value[key] for key in ("bytes", "sha256")}

    def closure(value):
        if isinstance(value, dict):
            reference = value.get("format") == "rove4k.target-runtime-reference.v1"
            if reference:
                require(type(value.get("family")) is str and type(value.get("profile")) is str
                        and (value["family"], value["profile"]) in source_builds
                        and value.get("ci_context") == origin
                        and value.get("consumer_scope") == "github-actions-ubuntu22-system"
                        and value.get("representation") == "source-jit" and value.get("full") is True
                        and value.get("runtime_eligible") is True
                        and value.get("runtime_executed") is False and value.get("runtime_qualified") is False
                        and value.get("event_target_confirmed") is False
                        and value.get("factory_replayed_on_target") is False,
                        "target reference differs from its selected sealed source identity")
                selected = source_builds[(value["family"], value["profile"])]
                build = value.get("source_build")
                require(isinstance(build, dict) and set(build) == {"path", "bytes", "sha256"}
                        and build["path"] == selected["path"],
                        "target reference source_build differs from its exact sealed build directory")
                require(pin(content[selected["member"]][0]) == expected_pin(build),
                        "target reference source_build differs from its exact build.json pin")
                counts["source_build_references"] += 1
            path = value.get("path")
            if isinstance(path, str) and path.startswith("/home/runner/work/_temp/") and {"bytes", "sha256"} <= set(value):
                logical = original_member(path)
                require(logical in content and pin(content[logical][0]) == expected_pin(value),
                        "original rule/tool evidence omitted or changed a pinned file")
                counts["file_references"] += 1
            for key, item in value.items():
                if not (reference and key == "source_build"):
                    closure(item)
        elif isinstance(value, list):
            for item in value:
                closure(item)

    for row in mappings:
        for name, (raw, _) in content.items():
            if name.startswith(row["seed_prefix"] + "/") and name.endswith(".json"):
                closure(json.loads(raw))
    return counts


def prepare(config, out):
    require(isinstance(config, dict) and config.get("format") == "rove4k-seed-prepare-v1", "explicit seed prepare configuration required")
    origin = origin_check(config["source_origin"])
    consumer = runtime()
    expanded_limit = consumer.seed_expansion_limit(config)
    target = new_external(out)
    source_tree = member(config.get("source_tree", "source"))
    content = {}
    inputs = config.get("inputs", {})
    require(isinstance(inputs, dict) and len(inputs) < consumer.MAX_SEED_MEMBERS,
            "explicit bounded external input map required")
    reserved = 0
    for name, descriptor in inputs.items():
        require(member(name) != "seed.json", "seed.json is reserved for the canonical manifest")
        reserved += input_descriptor(descriptor)["bytes"]
    require(reserved <= expanded_limit, "external input metadata exceeds expanded seed bound")

    def add(name, raw, mode=0o600):
        name = member(name)
        require(name != "seed.json" and name not in content and mode in (0o600, 0o700), "duplicate seed member or invalid mode")
        require(len(raw) <= MAX_MEMBER and len(content) < consumer.MAX_SEED_MEMBERS - 1,
                "seed member/count exceeds bound including seed.json")
        content[name] = (raw, mode)
        require(sum(len(value[0]) for value in content.values()) <= expanded_limit, "expanded seed exceeds bound")

    league_required = any(row["profile"] in LEAGUE_PROFILES
                          for kind in ("rove", "peers") for row in config[kind])
    for name, (raw, mode) in checkout_files(config["checkout"], origin,
            byte_budget=expanded_limit - reserved,
            member_budget=consumer.MAX_SEED_MEMBERS - 1 - len(inputs),
            league_required=league_required).items():
        add(source_tree + "/" + name, raw, mode)
    for name, descriptor in sorted(inputs.items()):
        add(name, checked_input(descriptor, limit=MAX_MEMBER))
    rove = config.get("rove", [])
    require(isinstance(rove, list), "explicit Rove selection required")
    workflow, artifact_pins, source_builds = None, {}, {}
    for selected in rove:
        bundle_name, seal_name = member(selected["source_bundle"]), member(selected["source_seal"])
        require(bundle_name in content and seal_name in content and PurePosixPath(bundle_name).name == "source-bundle.zip"
                and PurePosixPath(seal_name).name == "source-seal.json", "raw named source bundle/seal input is absent")
        bundle, seal = content[bundle_name][0], json.loads(content[seal_name][0])
        require(seal.get("format") == "rove4k.source-bundle-seal.v1" and seal.get("ci_context") == origin
                and seal.get("producer") == {"ID": "ubuntu", "VERSION_ID": "24.04"} and seal.get("bundle_format") == "zip"
                and seal.get("bundle") == pin(bundle), "raw source bundle differs from its exact CI seal")
        files = archive_members(bundle)
        require(seal.get("members") == {name: pin(raw) for name, (raw, _) in sorted(files.items())},
                "raw ZIP member map differs from source seal")
        matches = [entry for entry in seal.get("profiles", []) if (entry.get("family"), entry.get("profile")) ==
                   (selected["family"], selected["profile"])]
        require(len(matches) == 1, "selected Rove source profile is ambiguous")
        entry = matches[0]
        require(entry.get("full") is True and entry.get("representation") == "source-jit",
                "seed accepts only the sealed full source-JIT Rove profile")
        prefix = member(entry["archive_prefix"])
        layout = seal.get("restore_layout", {})
        require(set(layout) == {"runner_temp_root", "output_root", "builds"}
                and layout["runner_temp_root"] == "/home/runner/work/_temp"
                and layout["builds"] == {prefix: entry["build_root"]}
                and entry["build_root"] == layout["output_root"] + "/" + prefix,
                "source seal original restore metadata differs from its profile")
        build = member(selected["build"])
        require(build.endswith("/" + prefix), "transport build must retain its sealed archive prefix")
        destination = build[:-len(prefix) - 1]
        for name, (raw, mode) in files.items():
            require(name.startswith(prefix + "/"), "source bundle contains an unselected profile namespace")
            logical = destination + "/" + name
            if logical in content:
                require(content[logical] == (raw, mode), "explicit raw build input differs from sealed ZIP")
            else:
                add(logical, raw, mode)
        require(build + "/build.json" in content, "sealed build omitted its manifest")
        require(entry.get("input_manifest") == pin(content[build + "/build.json"][0]), "sealed build.json pin differs")
        key = (selected["family"], selected["profile"])
        require(key not in source_builds, "selected source build family/profile is ambiguous")
        source_builds[key] = {"path": entry["build_root"], "member": build + "/build.json"}
        dependency_evidence(content, build, json.loads(content[build + "/build.json"][0]), original_build=entry["build_root"])
        metadata_name = member(selected["artifact_metadata"])
        require(metadata_name in content, "downloaded CI artifact metadata is absent")
        metadata = json.loads(content[metadata_name][0])
        require(isinstance(metadata, dict) and isinstance(metadata.get("workflow_run"), dict),
                "downloaded artifact metadata must contain its workflow object")
        run = metadata.get("workflow_run", {})
        require(type(metadata.get("id")) is int and metadata["id"] > 0 and str(run.get("id")) == str(origin["run_id"])
                and isinstance(run.get("head_sha"), str), "downloaded artifact metadata differs from sealed origin")
        bound = workflow_binding(config, content, origin, run["head_sha"])
        require(workflow is None or workflow == bound, "artifacts disagree on the verified workflow execution")
        workflow = bound
        if bound.get("repository_id") is not None:
            require(run.get("repository_id") == bound["repository_id"], "artifact repository differs from verified workflow")
        if bound["kind"] in ("pull-request-merge", "execution-base-ancestor-v1"):
            require(run.get("head_repository_id") == bound["head_repository_id"]
                    and run.get("head_branch") == bound["head_branch"], "artifact PR repository/ref differs from workflow")
        artifact_pins[metadata_name] = pin(content[metadata_name][0])
    manifest = {"format": "rove4k-cloud-seed-v1", "source_origin": origin, "source_tree": source_tree,
        **{key: config[key] for key in ("rove", "peers", "runner", "bank", "bank_pgns")},
        "members": {name: {**pin(raw), "mode": mode} for name, (raw, mode) in sorted(content.items())}}
    if workflow is not None:
        manifest["workflow_provenance"] = {**workflow, "artifact_metadata": artifact_pins}
    roots = config.get("original_layout", {}).get("roots", [])
    require(isinstance(roots, list), "explicit original layout roots required")
    manifest["original_layout"] = {"format": "rove4k-original-layout-plan-v1", "roots": []}
    for row in roots:
        require(isinstance(row, dict) and set(row) == {"original_root", "seed_prefix"}, "original roots must name exact paths/prefixes")
        prefix = member(row["seed_prefix"])
        files = {name[len(prefix) + 1:]: pin(raw) for name, (raw, _) in content.items() if name.startswith(prefix + "/")}
        manifest["original_layout"]["roots"].append({**row, "files": files})
    consumer.validate_seed_manifest(manifest)
    consumer.validate_workflow_provenance(manifest, lambda name: content[name][0])
    mappings = consumer.original_layout_plan(manifest)
    for selected in rove:
        seal = json.loads(content[selected["source_seal"]][0])
        entry = next(row for row in seal["profiles"] if (row["family"], row["profile"]) == (selected["family"], selected["profile"]))
        matching = [row for row in mappings if selected["build"].startswith(row["seed_prefix"] + "/")]
        require(len(matching) == 1, "Rove build has no unique original-root mapping")
        row = matching[0]
        original = PurePosixPath(row["original_root"]) / selected["build"][len(row["seed_prefix"]) + 1:]
        require(str(original) == entry["build_root"], "original sealed build_root differs from transport mapping")
        require(any(selected["rules"].startswith(item["seed_prefix"] + "/") for item in mappings),
                "raw rules evidence has no explicit original-layout mapping")
        rules_name = member(selected["rules"])
        require(PurePosixPath(rules_name).name == "rules.json", "raw rules receipt must retain its original filename")
        probe = PurePosixPath(rules_name).parent
        required_rules = (str(probe / "cases.json"), str(probe / "fixture.c"), str(probe.parent / "commands.json"))
        require(all(name in content for name in required_rules), "raw rules command/fixture/case closure is incomplete")
        report = json.loads(content[rules_name][0])
        require(report.get("family") == selected["family"] and report.get("complete") is True,
                "rules report is incomplete or belongs to a different family")
        tools = report.get("verifier_inputs", {})
        require(isinstance(tools, dict) and tools, "raw rules verifier tool closure is absent")
        for path, expected in tools.items():
            logical = source_tree + "/" + member(path)
            require(logical in content and pin(content[logical][0].replace(b"\r\n", b"\n")) == expected,
                    "rules tool bytes differ from the selected CI checkout")
    original_references(content, mappings, source_builds, origin)
    for selected in manifest["peers"]:
        peer_originals(selected, content, source_tree)
    validate_runner(config, content, source_tree, config["checkout"]["path"])
    raw_manifest = ledger.canonical(manifest) + b"\n"
    require(len(raw_manifest) <= consumer.MAX_SEED_MANIFEST, "seed manifest exceeds its 4 MiB bound")
    require(sum(len(value[0]) for value in content.values()) + len(raw_manifest) <= expanded_limit,
            "seed including its manifest exceeds expansion bound")
    target.mkdir(parents=True)
    write_new(target / "seed.json", raw_manifest)
    archive_path = target / "seed.zip"
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, (raw, mode) in sorted({**content, "seed.json": (raw_manifest, 0o600)}.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system, info.external_attr = 3, (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    with archive_path.open("r+b") as source:
        os.fsync(source.fileno())
    archive_pin = pin(ordinary(archive_path, limit=MAX_SEED))
    receipt = {"format": "rove4k-seed-prepare-receipt-v1", "source_origin": origin,
        "workflow_provenance": manifest.get("workflow_provenance"),
        "seed_manifest": {"path": str(target / "seed.json"), **pin(raw_manifest)},
        "archive": {"path": str(archive_path), **archive_pin}, "members": len(content),
        "native_qualified": False, "engine_executed": False, "aws_calls_performed": False}
    write_new(target / "prepare-receipt.json", ledger.canonical(receipt))
    return receipt


def inspect_archive(raw):
    require(isinstance(raw, bytes) and len(raw) <= MAX_SEED, "seed ZIP exceeds its wire bound")
    consumer = runtime()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        manifest, _raw_manifest, _infos = consumer.seed_archive_manifest(archive)
    files = archive_members(raw, expanded_limit=consumer.seed_expansion_limit(manifest))
    consumer.original_layout_plan(manifest)
    require(set(files) == set(manifest["members"]) | {"seed.json"}, "archive has an unlisted/missing member")
    for name, expected in manifest["members"].items():
        value, mode = files[name]
        require({**pin(value), "mode": mode} == expected, "archive member differs from canonical manifest")
    require(files["seed.json"][0] == ledger.canonical(manifest) + b"\n", "seed.json is not canonical JSON with one LF")
    consumer.validate_workflow_provenance(manifest, lambda name: files[name][0])
    return {"manifest_sha256": pin(files["seed.json"][0])["sha256"], "members": len(manifest["members"])}


def upload_identity(plan, archive, key):
    require(plan.region == plan.project_region == "ap-southeast-2", "seed publication requires explicit selected Sydney region")
    require(not any((parent / ".git").exists() for parent in (Path(archive), *Path(archive).parents)),
            "seed upload archive must remain outside Git")
    require(re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", plan.artifact_bucket), "explicit valid seed bucket required")
    raw = ordinary(archive, limit=MAX_SEED)
    inspect_archive(raw)
    identity = pin(raw)
    require(key == plan.campaign_id + "/seed/" + identity["sha256"] + ".zip", "content-addressed campaign seed key required")
    return {"bucket": plan.artifact_bucket, "key": key, **identity}


def reconcile(client, plan, archive, key, *, expected_version=None):
    identity = upload_identity(plan, archive, key)
    aws.verify_caller(client, plan)
    try:
        head = client.call("s3api", "head-object", {"Bucket": identity["bucket"], "Key": key, "ChecksumMode": "ENABLED"})
    except aws.AwsError as error:
        if error.code in ("NoSuchKey", "NotFound", "404"):
            return {"state": "not_observed", "identity": identity, "upload_performed": False}
        raise
    checksum = base64.b64encode(bytes.fromhex(identity["sha256"])).decode()
    require(head.get("ContentLength") == identity["bytes"] and head.get("Metadata", {}).get("sha256") == identity["sha256"]
            and head.get("ChecksumSHA256") == checksum, "current seed object conflicts with the immutable local bytes")
    version = head.get("VersionId")
    require(isinstance(version, str) and version not in ("", "null") and len(version) <= 1024,
            "actual immutable non-null S3 VersionId is required")
    require(expected_version is None or version == expected_version, "confirmed seed VersionId changed; do not rebind it")
    descriptor = {**identity, "version_id": version}
    return {"state": "verified", "seed": descriptor, "verified": True, "upload_performed": False}


def confirmed_version(rows, identity):
    versions = set()
    for row in rows:
        if row["event"] != "seed.upload_confirmed" or row["data"].get("key") != identity["key"]:
            continue
        value = row["data"]
        require({key: value.get(key) for key in identity} == identity, "confirmed seed identity differs from current archive")
        version = value.get("version_id")
        require(isinstance(version, str) and version not in ("", "null"), "journal has no exact confirmed VersionId")
        versions.add(version)
    require(len(versions) <= 1, "journal has conflicting confirmed seed versions")
    return next(iter(versions), None)


def publish(client, plan, archive, key, journal):
    identity = upload_identity(plan, archive, key)
    require(journal.campaign == plan.campaign_id, "upload journal belongs to another campaign")
    previous = [row for row in journal.rows if row["event"] == "seed.upload_requested" and row["data"].get("key") == key]
    version = confirmed_version(journal.rows, identity)
    if previous:
        require(all(row["data"] == identity for row in previous), "prior upload intent differs; preserve its original bytes")
        result = reconcile(client, plan, archive, key, expected_version=version)  # Never resend an uncertain request.
        if result["state"] == "verified" and version is None:
            journal.append("seed.upload_confirmed", result["seed"])
        return result
    observed = reconcile(client, plan, archive, key, expected_version=version)
    if observed["state"] == "verified":
        if version is None:
            journal.append("seed.upload_confirmed", observed["seed"])
        return observed
    if version is not None:
        return observed  # A missing current object cannot authorize replacing a confirmed version.
    aws.require_account_readiness(client, plan, __import__('time').time())
    journal.append("seed.upload_requested", identity)  # fsync before the first PutObject.
    publisher = aws.S3Evidence(client, plan, Path(archive).parent)
    try:
        acknowledgement = publisher.publish(Path(archive), key)
        require(acknowledgement.get("verified") is True, "seed upload is not remotely acknowledged")
        result = reconcile(client, plan, archive, key)
        require(result["state"] == "verified", "seed upload remains unobserved")
    except Exception:
        journal.append("seed.upload_uncertain", identity)
        raise
    journal.append("seed.upload_confirmed", result["seed"])
    return {**result, "upload_performed": True}


def example():
    identity = {"path": "/absolute/download/file", "bytes": 1, "sha256": "0" * 64}
    return {"format": "rove4k-seed-prepare-v1", "source_origin": {"repository": "daejunnom/Rove4k", "head_sha": "0" * 40,
        "run_id": "1", "run_attempt": "1"}, "checkout": {"path": "/absolute/clean-checkout", "commit": "0" * 40,
        "paths": ["engines/experiments/strength", "engines/experiments/tcec-next", "engines/scripts", "engines/tests",
                  "engines/experiments/tcec-scope", "engines/experiments/tiny-d-submission", "engines/common",
                  "engines/compact/tiny-entry-d", "engines/model"]},
        "source_tree": "source", "inputs": {"origin/A/source-bundle.zip": identity,
        "origin/A/source-seal.json": identity, "metadata/A-artifact.json": identity,
        "metadata/workflow-run.json": identity, "metadata/pull-request.json": identity,
        "metadata/execution-commit.json": identity,
        "origin/rules/A/probe/rules.json": identity, "origin/rules/A/probe/cases.json": identity,
        "origin/rules/A/probe/fixture.c": identity, "origin/rules/A/commands.json": identity,
        "runner/fastchess.bundle": identity, "runner/LICENSE": identity,
        "bank/bank.json": identity, "bank/broad.pgn": identity, "bank/high.pgn": identity},
        "rove": [{"family": "A", "profile": "test-p4", "build": "origin/A/artifact",
            "source_bundle": "origin/A/source-bundle.zip", "source_seal": "origin/A/source-seal.json",
            "artifact_metadata": "metadata/A-artifact.json", "rules": "origin/rules/A/probe/rules.json"}], "peers": [],
        "workflow_provenance": {"run": "metadata/workflow-run.json", "pull_request": "metadata/pull-request.json",
                                "commit": "metadata/execution-commit.json"},
        "runner": {"checkout": "external/fastchess", "revision": FASTCHESS, "transport": "external-git-bundle",
            "bundle": "runner/fastchess.bundle", "patch": "source/engines/experiments/strength/patches/fastchess-rove.patch", "license": "runner/LICENSE"},
        "bank": "bank/bank.json", "bank_pgns": {"broad": "bank/broad.pgn", "high": "bank/high.pgn"},
        "original_layout": {"roots": [{"original_root": "/home/runner/work/_temp/EXACT-SEALED-OUTPUT", "seed_prefix": "origin/A"},
                                       {"original_root": "/home/runner/work/_temp/EXACT-RULES-ROOT", "seed_prefix": "origin/rules/A"}]}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("example", help="print a placeholder configuration; never execute or infer input origins")
    prep = actions.add_parser("prepare", help="offline exact seed ZIP creation in a new external staging directory")
    prep.add_argument("--config", type=Path, required=True); prep.add_argument("--out", type=Path, required=True)
    for action in ("publish", "reconcile"):
        item = actions.add_parser(action)
        for key in ("aws-plan", "archive", "journal", "out"):
            item.add_argument("--" + key, type=Path, required=True)
        item.add_argument("--seed-out", type=Path, required=True,
                          help="new external exact SeedObject descriptor; created only after verified API observation")
        item.add_argument("--key", required=True)
    args = parser.parse_args(argv)
    if args.action == "example":
        result = example()
    elif args.action == "prepare":
        result = prepare(json.loads(ordinary(args.config)), args.out)
    else:
        new_external(args.out)
        new_external(args.seed_out)
        require(args.out.resolve() != args.seed_out.resolve(), "report and seed descriptor destinations must differ")
        plan = aws.AWSPlan.from_dict(json.loads(ordinary(args.aws_plan)))
        client = aws.AWSCLI(plan.region)
        if args.action == "reconcile":
            identity = upload_identity(plan, args.archive, args.key)
            rows = ledger.read_journal(args.journal, plan.campaign_id)
            result = reconcile(client, plan, args.archive, args.key, expected_version=confirmed_version(rows, identity))
        else:
            with ledger.Journal(args.journal, plan.campaign_id) as journal:
                result = publish(client, plan, args.archive, args.key, journal)
        if result.get("state") == "verified":
            descriptor = result["seed"]
            require(set(descriptor) == {"bucket", "key", "version_id", "sha256", "bytes"},
                    "verified seed result is not an exact consumer descriptor")
            write_new(args.seed_out, ledger.canonical(descriptor))
            result = {**result, "seed_descriptor_path": str(args.seed_out)}
        write_new(args.out, ledger.canonical(result))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 2 if args.action in ("publish", "reconcile") and result.get("state") != "verified" else 0


if __name__ == "__main__":
    raise SystemExit(main())
