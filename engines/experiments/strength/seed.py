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
          "engines/scripts/production_input.py", "engines/scripts/production_source_bundle.py")


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


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


def checked_input(value, *, limit=MAX_MEMBER):
    require(isinstance(value, dict) and set(value) == {"path", "bytes", "sha256"}, "explicit path/byte/SHA input required")
    require(type(value["bytes"]) is int and 0 <= value["bytes"] <= limit and SHA.fullmatch(str(value["sha256"])),
            "bounded exact input identity required")
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
    for item in (path, *path.parents):
        require(not item.is_symlink() and not (hasattr(item, "is_junction") and item.is_junction())
                and not (item / ".git").exists(), "staging must stay outside Git and links")
    member(path.name)
    return path


def git(checkout, *arguments, limit=MAX_SEED):
    env = os.environ.copy()
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0",
               GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-c",
        "core.hooksPath=" + os.devnull, "--literal-pathspecs", "-C", str(checkout), *arguments],
        capture_output=True, env=env, timeout=30,
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


def checkout_files(value, origin):
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
    exact_names(root, prefixes, set(blobs))
    result = {}
    for name, blob in sorted(blobs.items()):
        raw = git(root, "cat-file", "blob", blob, limit=MAX_MEMBER)
        result[name] = (raw, modes[name])
    required = {"engines/experiments/strength/" + name + ".py" for name in HOST_MODULES}
    if origin.get("rove_required", True):
        required.update(CORE_R)
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
        for node in ast.walk(ast.parse(raw)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                target = node.value
                if target.startswith("engines/") and target.endswith(".py"):
                    member(target)
                    require(target in selected, "named production Python dependency omitted: " + target)
    require(not git(root, "status", "--porcelain=v1", "--untracked-files=no"), "source checkout changed during collection")
    require(git(root, "rev-parse", "HEAD").decode().strip() == commit, "source commit changed during collection")
    return result


def archive_members(raw):
    require(len(raw) <= MAX_SEED, "source ZIP exceeds transport bound")
    result = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        total = 0
        for info in archive.infolist():
            name = member(info.filename)
            mode = info.external_attr >> 16
            require(not info.is_dir() and not info.flag_bits & 1 and stat.S_IFMT(mode) in (0, stat.S_IFREG),
                    "source ZIP contains a link/directory/encrypted member")
            total += info.file_size
            require(name not in result and info.file_size <= MAX_MEMBER and total <= MAX_SEED,
                    "source ZIP has duplicate or excessive members")
            result[name] = (archive.read(info), 0o700 if mode & 0o111 else 0o600)
    require(result, "source ZIP is empty")
    return result


def origin_check(value):
    require(isinstance(value, dict) and set(value) == {"repository", "head_sha", "run_id", "run_attempt"},
            "exact source CI origin required")
    require(re.fullmatch(r"[\w.-]+/[\w.-]+", str(value["repository"])) and
            re.fullmatch(r"[a-f0-9]{40}(?:[a-f0-9]{24})?", str(value["head_sha"])) and
            all(re.fullmatch(r"[1-9][0-9]*", str(value[key])) for key in ("run_id", "run_attempt")),
            "invalid or ambiguous CI origin")
    return json.loads(ledger.canonical(value))


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


def prepare(config, out):
    require(isinstance(config, dict) and config.get("format") == "rove4k-seed-prepare-v1", "explicit seed prepare configuration required")
    origin = origin_check(config["source_origin"])
    target = new_external(out)
    source_tree = member(config.get("source_tree", "source"))
    content = {}

    def add(name, raw, mode=0o600):
        name = member(name)
        require(name != "seed.json" and name not in content and mode in (0o600, 0o700), "duplicate seed member or invalid mode")
        require(len(raw) <= MAX_MEMBER and len(content) < 20000, "seed member/count exceeds bound")
        content[name] = (raw, mode)
        require(sum(len(value[0]) for value in content.values()) <= MAX_SEED, "expanded seed exceeds bound")

    for name, (raw, mode) in checkout_files(config["checkout"], origin).items():
        add(source_tree + "/" + name, raw, mode)
    inputs = config.get("inputs", {})
    require(isinstance(inputs, dict), "explicit external input map required")
    for name, descriptor in sorted(inputs.items()):
        add(name, checked_input(descriptor, limit=MAX_MEMBER))
    rove = config.get("rove", [])
    require(isinstance(rove, list), "explicit Rove selection required")
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
        metadata_name = member(selected["artifact_metadata"])
        require(metadata_name in content, "downloaded CI artifact metadata is absent")
        metadata = json.loads(content[metadata_name][0])
        run = metadata.get("workflow_run", {})
        require(type(metadata.get("id")) is int and metadata["id"] > 0 and str(run.get("id")) == str(origin["run_id"])
                and run.get("head_sha") == origin["head_sha"], "downloaded artifact metadata differs from sealed origin")
    manifest = {"format": "rove4k-cloud-seed-v1", "source_origin": origin, "source_tree": source_tree,
        **{key: config[key] for key in ("rove", "peers", "runner", "bank", "bank_pgns")},
        "members": {name: {**pin(raw), "mode": mode} for name, (raw, mode) in sorted(content.items())}}
    roots = config.get("original_layout", {}).get("roots", [])
    require(isinstance(roots, list), "explicit original layout roots required")
    manifest["original_layout"] = {"format": "rove4k-original-layout-plan-v1", "roots": []}
    for row in roots:
        require(isinstance(row, dict) and set(row) == {"original_root", "seed_prefix"}, "original roots must name exact paths/prefixes")
        prefix = member(row["seed_prefix"])
        files = {name[len(prefix) + 1:]: pin(raw) for name, (raw, _) in content.items() if name.startswith(prefix + "/")}
        manifest["original_layout"]["roots"].append({**row, "files": files})
    consumer = runtime()
    consumer.validate_seed_manifest(manifest)
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
    # Original command streams and rule evidence keep their exact absolute
    # paths. Check every pinned temporary-path file reference without rewriting.
    def original_member(path):
        matched = [row for row in mappings if path.startswith(row["original_root"] + "/")]
        require(len(matched) == 1, "original evidence path has no unique explicit transport root")
        row = matched[0]
        return row["seed_prefix"] + path[len(row["original_root"]):]

    def closure(value):
        if isinstance(value, dict):
            path = value.get("path")
            if isinstance(path, str) and path.startswith("/home/runner/work/_temp/") and {"bytes", "sha256"} <= set(value):
                logical = original_member(path)
                require(logical in content and pin(content[logical][0]) == {key: value[key] for key in ("bytes", "sha256")},
                        "original rule/tool evidence omitted or changed a pinned file")
            for item in value.values():
                closure(item)
        elif isinstance(value, list):
            for item in value:
                closure(item)
    for row in mappings:
        for name, (raw, _) in content.items():
            if name.startswith(row["seed_prefix"] + "/") and name.endswith(".json"):
                closure(json.loads(raw))
    for selected in manifest["peers"]:
        peer_originals(selected, content, source_tree)
    validate_runner(config, content, source_tree, config["checkout"]["path"])
    raw_manifest = ledger.canonical(manifest)
    require(sum(len(value[0]) for value in content.values()) + len(raw_manifest) <= MAX_SEED,
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
    with archive_path.open("rb") as source:
        os.fsync(source.fileno())
    archive_pin = pin(ordinary(archive_path, limit=MAX_SEED))
    receipt = {"format": "rove4k-seed-prepare-receipt-v1", "source_origin": origin,
        "seed_manifest": {"path": str(target / "seed.json"), **pin(raw_manifest)},
        "archive": {"path": str(archive_path), **archive_pin}, "members": len(content),
        "native_qualified": False, "engine_executed": False, "aws_calls_performed": False}
    write_new(target / "prepare-receipt.json", ledger.canonical(receipt))
    return receipt


def inspect_archive(raw):
    files = archive_members(raw)
    require("seed.json" in files, "archive omitted canonical seed.json")
    manifest = json.loads(files["seed.json"][0])
    consumer = runtime()
    consumer.validate_seed_manifest(manifest)
    consumer.original_layout_plan(manifest)
    require(set(files) == set(manifest["members"]) | {"seed.json"}, "archive has an unlisted/missing member")
    for name, expected in manifest["members"].items():
        value, mode = files[name]
        require({**pin(value), "mode": mode} == expected, "archive member differs from canonical manifest")
    require(files["seed.json"][0] == ledger.canonical(manifest), "seed.json is not canonical JSON bytes")
    return {"manifest_sha256": pin(files["seed.json"][0])["sha256"], "members": len(manifest["members"])}


def upload_identity(plan, archive, key):
    require(plan.region == plan.project_region == "ap-southeast-2", "seed publication requires explicit selected Sydney region")
    raw = ordinary(archive, limit=MAX_SEED)
    inspect_archive(raw)
    identity = pin(raw)
    require(key == plan.campaign_id + "/seed/" + identity["sha256"] + ".zip", "content-addressed campaign seed key required")
    return {"bucket": plan.artifact_bucket, "key": key, **identity}


def reconcile(client, plan, archive, key):
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
    require(isinstance(version, str) and version not in ("", "null"), "actual immutable non-null S3 VersionId is required")
    descriptor = {**identity, "version_id": version}
    runtime().SeedObject(**descriptor)
    return {"state": "verified", "seed": descriptor, "verified": True, "upload_performed": False}


def publish(client, plan, archive, key, journal):
    identity = upload_identity(plan, archive, key)
    require(journal.campaign == plan.campaign_id, "upload journal belongs to another campaign")
    previous = [row for row in journal.rows if row["event"] == "seed.upload_requested" and row["data"].get("key") == key]
    if previous:
        require(all(row["data"] == identity for row in previous), "prior upload intent differs; preserve its original bytes")
        return reconcile(client, plan, archive, key)  # An uncertain outcome is never a resend permit.
    observed = reconcile(client, plan, archive, key)
    if observed["state"] == "verified":
        return observed
    aws.require_paid_account_plan(client, plan.account_id, __import__('time').time())
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
                  "engines/experiments/tcec-scope", "engines/compact/tiny-entry-d", "engines/model"]},
        "source_tree": "source", "inputs": {"origin/A/source-bundle.zip": identity,
        "origin/A/source-seal.json": identity, "origin/A/artifact.json": identity, "origin/rules/A.json": identity,
        "runner/fastchess.bundle": identity, "runner/patch.diff": identity, "runner/LICENSE": identity,
        "bank/bank.json": identity, "bank/broad.pgn": identity, "bank/high.pgn": identity},
        "rove": [{"family": "A", "profile": "test-p4", "build": "origin/A/artifact",
            "source_bundle": "origin/A/source-bundle.zip", "source_seal": "origin/A/source-seal.json",
            "artifact_metadata": "origin/A/artifact.json", "rules": "origin/rules/A.json"}], "peers": [],
        "runner": {"checkout": "external/fastchess", "revision": FASTCHESS, "transport": "external-git-bundle",
            "bundle": "runner/fastchess.bundle", "patch": "runner/patch.diff", "license": "runner/LICENSE"},
        "bank": "bank/bank.json", "bank_pgns": {"broad": "bank/broad.pgn", "high": "bank/high.pgn"},
        "original_layout": {"roots": [{"original_root": "/home/runner/work/_temp/EXACT-SEALED-OUTPUT", "seed_prefix": "origin/A"},
                                       {"original_root": "/home/runner/work/_temp/EXACT-RULES-ROOT", "seed_prefix": "origin/rules"}]}}


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
        item.add_argument("--key", required=True)
    args = parser.parse_args(argv)
    if args.action == "example":
        result = example()
    elif args.action == "prepare":
        result = prepare(json.loads(ordinary(args.config)), args.out)
    else:
        new_external(args.out)
        plan = aws.AWSPlan.from_dict(json.loads(ordinary(args.aws_plan)))
        client = aws.AWSCLI(plan.region)
        if args.action == "reconcile":
            result = reconcile(client, plan, args.archive, args.key)
        else:
            with ledger.Journal(args.journal, plan.campaign_id) as journal:
                result = publish(client, plan, args.archive, args.key, journal)
        write_new(args.out, ledger.canonical(result))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
