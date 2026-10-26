#!/usr/bin/env python3
"""Manual CI transport for an immutable seed's existing campaign controller.

This module is deliberately not a controller, publisher, or authentication
provider. A standard pinned Actions OIDC step supplies temporary environment
credentials. All campaign authority is loaded from the materialized seed.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys
import time
import urllib.request

sys.dont_write_bytecode = True
REPOSITORY = "daejunnom/Rove4k"
ACCOUNT = "292341339363"
REGION = "ap-southeast-2"
ACTION = "e1253824e5c10ff9df46874f81ed3ec929e19cfd"
WORKFLOW_SHA256 = "66b152c3360f05c3b9ab0321adf0be01ab1a15c65692ce20beb746cc3760d639"
JOB_NAME = "Rove4k AWS evaluation"
OIDC_STEP = "Configure AWS controller OIDC"
DURATION = 21600
RESERVE = 900
SHA = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
MAX_REQUEST = 4 << 20
MAX_SEED = 128 << 20


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def document(raw):
    def unique(pairs):
        value = dict(pairs)
        require(len(value) == len(pairs), "duplicate JSON field")
        return value
    return json.loads(raw, object_pairs_hook=unique)


def logical(value):
    require(isinstance(value, str) and value and not PurePosixPath(value).is_absolute()
            and not any(c in value for c in ("\\", "\0", ":"))
            and all(part not in ("", ".", "..") for part in value.split("/")), "unsafe logical object/member name")
    blocked = {".git", ".aws", ".ssh", "node_modules", "dist", "dist-server", "coverage", "models", "checkpoints", ".cache", "inventory.json", "package-lock.json"}
    require(not any(part.casefold() in blocked or part.casefold().startswith(".env")
            or re.search(r"credential|service[-_ ]?account|api[-_ ]?key|ssh[-_ ]?key|^id_(rsa|ed25519)$", part, re.I)
            for part in value.split("/")), "protected logical input")
    return value


def ordinary(path, maximum=MAX_REQUEST):
    path = Path(path)
    require(path.is_absolute() and not any(item.is_symlink() for item in (path, *path.parents)), "absolute regular input required")
    require(not any(part.casefold().startswith(".env") or re.search(r"credential|service[-_ ]?account|api[-_ ]?key|^id_(rsa|ed25519)$", part, re.I)
                    for part in path.parts), "protected input cannot be read")
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= maximum, "bounded ordinary input required")
    raw = path.read_bytes()
    after = path.stat()
    stamp = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    require(stamp(before) == stamp(after) and len(raw) == before.st_size, "input changed while reading")
    return raw


def write_new(path, raw):
    path = Path(path)
    require(path.is_absolute() and not any(item.is_symlink() for item in (path, *path.parents)), "owned ordinary output required")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    path.chmod(0o600)
    return {"path": str(path), **pin(raw)}


def read_pinned(path, expected, maximum=MAX_REQUEST):
    raw = ordinary(path, maximum)
    require(pin(raw) == {key: expected[key] for key in ("bytes", "sha256")}, "input pin differs")
    return document(raw)


def parse_request(value, *, campaign_id, role_arn, bucket):
    fields = {"format", "aws_plan", "seed", "seed_manifest_sha256", "source_origin",
              "workflow_provenance", "reviewed_deployment", "bootstrap", "journal"}
    require(isinstance(value, dict) and set(value) == fields and value["format"] == "rove4k-campaign-ci-v1", "exact campaign CI request required")
    require(re.fullmatch(r"[a-z][a-z0-9-]{2,39}", campaign_id or ""), "invalid campaign ID")
    require(isinstance(role_arn, str) and re.fullmatch(r"arn:aws:iam::" + ACCOUNT + r":role/[A-Za-z0-9+=,.@_/-]+", role_arn), "controller role must belong to the fixed account")
    plan = value["aws_plan"]
    require(isinstance(plan, dict) and plan.get("campaign_id") == campaign_id
            and plan.get("account_id") == ACCOUNT and plan.get("region") == plan.get("project_region") == REGION
            and plan.get("controller_role_arn") == role_arn and plan.get("artifact_bucket") == bucket,
            "request campaign/account/region/role/bucket differs")
    require(type(plan.get("deadline_epoch")) is int and plan["deadline_epoch"] > 0, "integer immutable deadline required")
    seed = value["seed"]
    require(isinstance(seed, dict) and set(seed) == {"bucket", "key", "version_id", "sha256", "bytes"}, "exact immutable seed descriptor required")
    require(seed["bucket"] == bucket and logical(seed["key"]).startswith(campaign_id + "/")
            and isinstance(seed["version_id"], str) and seed["version_id"] not in ("", "null")
            and len(seed["version_id"]) <= 1024 and isinstance(seed["sha256"], str) and SHA.fullmatch(seed["sha256"])
            and type(seed["bytes"]) is int and 0 < seed["bytes"] <= MAX_SEED, "versioned bounded campaign seed required")
    require(isinstance(value["seed_manifest_sha256"], str) and SHA.fullmatch(value["seed_manifest_sha256"]), "manifest SHA required")
    origin = value["source_origin"]
    require(isinstance(origin, dict) and set(origin) == {"repository", "head_sha", "run_id", "run_attempt"}
            and origin["repository"] == REPOSITORY and isinstance(origin["head_sha"], str) and COMMIT.fullmatch(origin["head_sha"])
            and all(re.fullmatch(r"[1-9][0-9]*", str(origin[key])) for key in ("run_id", "run_attempt")), "exact original source CI identity required")
    provenance = value["workflow_provenance"]
    require(isinstance(provenance, dict) and set(provenance) in ({"run", "commit"}, {"run", "commit", "pull_request"},
            {"run", "commit", "pull_request", "execution_base_proof"})
            and all(isinstance(name, str) for name in provenance.values()) and len(set(provenance.values())) == len(provenance),
            "distinct original provenance member roles required")
    for name in provenance.values():
        logical(name)
    reviewed = value["reviewed_deployment"]
    require(isinstance(reviewed, dict) and set(reviewed) == {"template_sha256", "watchdog_source_sha256", "function_code_sha256", "function_revision_id"}
            and all(isinstance(reviewed[key], str) and SHA.fullmatch(reviewed[key]) for key in ("template_sha256", "watchdog_source_sha256"))
            and isinstance(reviewed["function_code_sha256"], str) and re.fullmatch(r"[A-Za-z0-9+/]{43}=", reviewed["function_code_sha256"])
            and isinstance(reviewed["function_revision_id"], str) and 0 < len(reviewed["function_revision_id"]) <= 128,
            "reviewed deployment pins required; passing flags are not evidence")
    bootstrap = value["bootstrap"]
    require(isinstance(bootstrap, dict) and set(bootstrap) == {"recipe_id", "recipe_sha256"}
            and bootstrap["recipe_id"] == "rove4k-ubuntu22-ssm-bootstrap-v1"
            and isinstance(bootstrap["recipe_sha256"], str) and SHA.fullmatch(bootstrap["recipe_sha256"]), "frozen bootstrap pin required")
    journal = value["journal"]
    if journal is not None:
        require(isinstance(journal, dict) and set(journal) == {"object_key", "sha256", "bytes", "rows", "last_sha256"}
                and logical(journal["object_key"]).startswith(campaign_id + "/")
                and all(isinstance(journal[key], str) and SHA.fullmatch(journal[key]) for key in ("sha256", "last_sha256"))
                and type(journal["bytes"]) is int and 0 < journal["bytes"] <= 32 << 20
                and type(journal["rows"]) is int and journal["rows"] > 0, "explicit complete original journal pin required")
    return value


def epoch(value):
    require(isinstance(value, str) and value.endswith("Z"), "actual UTC API timestamp required")
    result = datetime.fromisoformat(value[:-1] + "+00:00").timestamp()
    require(result > 0, "positive API timestamp required")
    return result


def bind_context(run, jobs, env, now):
    require(type(now) in (int, float) and math.isfinite(now) and now > 0, "finite local observation clock required")
    require(env.get("GITHUB_ACTIONS") == "true" and env.get("GITHUB_REPOSITORY") == REPOSITORY
            and env.get("GITHUB_EVENT_NAME") == "workflow_dispatch", "real manual repository workflow required")
    run_id, attempt, sha = (env.get(name, "") for name in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA"))
    require(all(re.fullmatch(r"[1-9][0-9]*", value) for value in (run_id, attempt)) and COMMIT.fullmatch(sha), "actual workflow identity required")
    workflow_ref = env.get("GITHUB_WORKFLOW_REF", "")
    require(workflow_ref.startswith(REPOSITORY + "/.github/workflows/aws-evaluation.yml@refs/"), "unexpected workflow ref")
    require(isinstance(run, dict) and str(run.get("id")) == run_id and str(run.get("run_attempt")) == attempt
            and run.get("repository", {}).get("full_name") == REPOSITORY and run.get("event") == "workflow_dispatch"
            and run.get("head_sha") == sha and run.get("status") == "in_progress"
            and run.get("path", "").split("@", 1)[0] == ".github/workflows/aws-evaluation.yml", "current run API identity differs")
    require(isinstance(jobs, dict) and type(jobs.get("total_count")) is int and jobs["total_count"] == len(jobs.get("jobs", [])) <= 100, "complete bounded jobs API required")
    matches = [job for job in jobs["jobs"] if job.get("name") == JOB_NAME]
    require(len(matches) == 1, "one actual evaluation job required")
    job = matches[0]
    require(job.get("status") == "in_progress" and str(job.get("run_id")) == run_id
            and ("run_attempt" not in job or str(job["run_attempt"]) == attempt), "current job identity/status differs")
    require(isinstance(job.get("steps"), list), "actual job step list required")
    steps = [step for step in job.get("steps", []) if step.get("name") == OIDC_STEP]
    require(len(steps) == 1 and steps[0].get("status") == "completed" and steps[0].get("conclusion") == "success", "pinned OIDC step has not completed successfully")
    started, job_started, oidc_started, oidc_completed = map(epoch, (run.get("run_started_at"), job.get("started_at"), steps[0].get("started_at"), steps[0].get("completed_at")))
    require(0 < started <= job_started <= oidc_started <= oidc_completed <= now, "API clocks are future, negative, or out of order")
    safe = min(started, job_started, oidc_started) + DURATION
    require(now < safe - RESERVE, "no job/credential cleanup reserve remains")
    return {"format": "rove4k-campaign-ci-context-v1", "repository": REPOSITORY, "run_id": run_id,
            "run_attempt": attempt, "workflow_sha": sha, "workflow_ref": workflow_ref,
            "run_started_at_epoch": started, "job_started_at_epoch": job_started,
            "oidc_step_started_at_epoch": oidc_started, "oidc_action": ACTION, "requested_session_seconds": DURATION,
            "actual_STS_expiration": None, "actual_STS_expiration_observed": False,
            "conservatively_safe_use_until": safe, "campaign_deadline_limit": safe - RESERVE}


def validate_window(request, context, now):
    require(type(now) in (int, float) and math.isfinite(now) and now > 0, "finite local observation clock required")
    deadline = request["aws_plan"]["deadline_epoch"]
    require(type(deadline) is int and now < deadline <= context["campaign_deadline_limit"], "immutable campaign deadline exceeds the safe job/credential window or expired")
    return {"deadline_epoch": deadline, "campaign_deadline_limit": context["campaign_deadline_limit"],
            "cleanup_reserve_seconds": context["conservatively_safe_use_until"] - deadline,
            "actual_STS_expiration": None, "actual_STS_expiration_observed": False}


def github_get(path):
    token = os.environ.get("GH_TOKEN", "")
    require(token, "workflow read token required")
    request = urllib.request.Request("https://api.github.com" + path, headers={"Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Rove4k-campaign-ci"})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read((8 << 20) + 1)
    require(len(raw) <= 8 << 20, "GitHub observation exceeds bound")
    return raw, document(raw)


def aws_call(service, operation, request, *, outfile=None):
    argv = ["aws", "--region", REGION, "--no-cli-pager", "--no-paginate", service, operation,
            "--cli-input-json", canonical(request).decode(), "--output", "json"]
    if outfile is not None:
        require(not Path(outfile).exists(), "download destination already exists")
        argv.append(str(outfile))
    env = os.environ.copy()
    env.update(AWS_CONFIG_FILE=os.devnull, AWS_SHARED_CREDENTIALS_FILE=os.devnull, AWS_MAX_ATTEMPTS="1", AWS_PAGER="")
    for key in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AWS_WEB_IDENTITY_TOKEN_FILE"):
        env.pop(key, None)
    result = subprocess.run(argv, capture_output=True, timeout=60, env=env)
    require(result.returncode == 0, "AWS transport failed: " + service + "." + operation)
    require(len(result.stdout) <= MAX_REQUEST, "AWS response exceeds bound")
    return document(result.stdout)


def fetch_version(descriptor, path, maximum):
    require(type(descriptor["bytes"]) is int and 0 < descriptor["bytes"] <= maximum, "bounded version download required")
    request = {"Bucket": descriptor["bucket"], "Key": logical(descriptor["key"]), "VersionId": descriptor["version_id"]}
    head = aws_call("s3api", "head-object", request)
    require(head.get("VersionId") == descriptor["version_id"] and head.get("ContentLength") == descriptor["bytes"], "version HEAD differs")
    result = aws_call("s3api", "get-object", request, outfile=path)
    require(result.get("VersionId") == descriptor["version_id"] and result.get("ContentLength") == descriptor["bytes"], "version GET differs")
    raw = ordinary(path, maximum)
    require(pin(raw) == {key: descriptor[key] for key in ("bytes", "sha256")}, "downloaded immutable object differs")
    return raw


def stage_request(args):
    root = Path(args.out)
    require(root.is_absolute() and not root.exists() and not any(item.is_symlink() for item in (root, *root.parents))
            and not any((parent / ".git").exists() for parent in root.parents), "new external CI root required")
    require(SHA.fullmatch(args.sha256 or "") and args.version_id not in ("", "null") and len(args.version_id) <= 1024
            and re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", args.bucket or "")
            and logical(args.key).startswith(args.campaign_id + "/seed/"), "pinned campaign seed/request namespace required")
    require(args.bucket == os.environ.get("EXPECTED_BUCKET", args.bucket), "request bucket differs from reviewed environment")
    root.mkdir(parents=True, mode=0o700)
    reports = root / "reports"
    reports.mkdir()
    outputs = os.environ.get("GITHUB_OUTPUT")
    require(outputs, "actual workflow output channel required")
    with Path(outputs).open("a", encoding="utf-8") as target:
        target.write("report_path=" + str(reports) + "\n")
    run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    require(all(re.fullmatch(r"[1-9][0-9]*", value) for value in (run_id, attempt)), "actual run identity required")
    prefix = "/repos/" + REPOSITORY + "/actions/runs/" + run_id + "/attempts/" + attempt
    raw_run, run = github_get(prefix)
    raw_jobs, jobs = github_get(prefix + "/jobs?per_page=100")
    write_new(reports / "workflow-run.original.json", raw_run)
    write_new(reports / "workflow-jobs.original.json", raw_jobs)
    context = bind_context(run, jobs, os.environ, time.time())
    own_checkout = Path(__file__).resolve().parents[3]
    require(git(own_checkout, "rev-parse", "HEAD").decode().strip() == context["workflow_sha"]
            and os.environ.get("GITHUB_WORKFLOW_SHA") == context["workflow_sha"]
            and not git(own_checkout, "status", "--porcelain=v1", "--untracked-files=no"), "orchestration checkout/workflow SHA differs from the actual job")
    require(git(own_checkout, "show", context["workflow_sha"] + ":engines/experiments/strength/campaign_ci.py").replace(b"\r\n", b"\n")
            == ordinary(Path(__file__).resolve()).replace(b"\r\n", b"\n"), "executing orchestration helper differs from its actual workflow commit")
    workflow = git(own_checkout, "show", context["workflow_sha"] + ":.github/workflows/aws-evaluation.yml")
    require(hashlib.sha256(workflow.replace(b"\r\n", b"\n")).hexdigest() == WORKFLOW_SHA256,
            "actual workflow differs from the reviewed direct 21600-second OIDC definition")
    context_pin = write_new(reports / "context.json", canonical(context) + b"\n")
    descriptor = {"bucket": args.bucket, "key": args.key, "version_id": args.version_id, "sha256": args.sha256, "bytes": args.bytes}
    request_path = reports / "request.original.json"
    raw = fetch_version(descriptor, request_path, MAX_REQUEST)
    role = os.environ.get("EXPECTED_ROLE_ARN", "")
    request = parse_request(document(raw), campaign_id=args.campaign_id, role_arn=role, bucket=args.bucket)
    require(request["aws_plan"]["deadline_epoch"] <= context["campaign_deadline_limit"], "immutable campaign deadline exceeds the safe job window")
    value = {"format": "rove4k-campaign-ci-stage-v1", "root": str(root), "request": {"path": str(request_path), **pin(raw)},
             "request_object": descriptor, "context": context_pin, "role_arn": role, "bucket": args.bucket}
    path = root / "stage.json"
    write_new(path, canonical(value) + b"\n")
    with Path(outputs).open("a", encoding="utf-8") as target:
        target.write("source_sha=" + request["source_origin"]["head_sha"] + "\nstage_path=" + str(path) + "\n")


def load_stage(path):
    path = Path(path)
    value = document(ordinary(path))
    require(value.get("format") == "rove4k-campaign-ci-stage-v1" and Path(value["root"]) == path.parent, "owned stage identity differs")
    request = read_pinned(value["request"]["path"], value["request"])
    context = read_pinned(value["context"]["path"], value["context"])
    parse_request(request, campaign_id=request["aws_plan"]["campaign_id"], role_arn=value["role_arn"], bucket=value["bucket"])
    return value, request, context


def git(origin, *arguments, limit=4 << 20, input_bytes=None):
    require(type(limit) is int and 0 < limit <= 32 << 20, "invalid original source Git read bound")
    env = os.environ.copy()
    for name in list(env):
        if name.upper().startswith("GIT_"):
            del env[name]
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0",
               GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
               GIT_ALLOW_PROTOCOL="")
    result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-c",
        "core.hooksPath=" + os.devnull, "-c", "protocol.allow=never", "--literal-pathspecs", "-C", str(origin), *arguments],
        capture_output=True, input=input_bytes, env=env, timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    require(result.returncode == 0 and len(result.stdout) <= limit, "original source Git observation failed or exceeded its bound")
    return result.stdout


def bind_materializer_source(origin, expected_head, *, out=None):
    """Bind the checkout before its data-only archive consumer can execute."""
    origin = Path(origin)
    require(origin.is_absolute() and origin.is_dir() and not any(item.is_symlink() for item in (origin, *origin.parents)),
            "ordinary original Git checkout required")
    require(git(origin, "rev-parse", "HEAD").decode().strip() == expected_head
            and not git(origin, "status", "--porcelain=v1", "--untracked-files=normal"), "exact clean original CI checkout required")
    # Read only the committed source's literal production closure. No checkout
    # module or attacker-selected archive code is imported to obtain this list.
    declaration = git(origin, "show", expected_head + ":engines/experiments/strength/seed.py", limit=32 << 20)
    values = {}
    for node in ast.parse(declaration).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("HOST_MODULES", "CORE_R"):
                    require(target.id not in values, "duplicate committed materializer source closure")
                    values[target.id] = ast.literal_eval(node.value)
    require(set(values) == {"HOST_MODULES", "CORE_R"}
            and all(type(value) is tuple and 0 < len(value) <= 128 for value in values.values()),
            "static committed materializer source closure required")
    modules, core = values["HOST_MODULES"], values["CORE_R"]
    require(all(isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in modules)
            and {"cloud_runtime", "aws", "budget", "collect", "ledger", "registry", "run", "topology",
                 "durability", "fastchess", "placement", "seed"} <= set(modules)
            and "engines/scripts/production.py" in core, "committed materializer import closure is incomplete")
    names = tuple("engines/experiments/strength/" + name + ".py" for name in modules) + tuple(logical(name) for name in core)
    require(len(set(names)) == len(names), "duplicate committed materializer source member")
    records = git(origin, "ls-tree", "-r", "-z", expected_head, "--", *sorted(names)).split(b"\0")
    tracked = {}
    for record in filter(None, records):
        meta, name = record.split(b"\t", 1)
        mode, kind, blob = meta.decode().split()
        name = logical(name.decode())
        require(kind == "blob" and mode in ("100644", "100755") and name not in tracked,
                "materializer closure must contain regular committed source blobs")
        tracked[name] = (blob, mode)
    require(set(tracked) == set(names), "committed materializer source closure is missing")
    sources = {}
    for name, (blob, mode) in tracked.items():
        size = git(origin, "cat-file", "-s", blob).decode().strip()
        require(size.isdigit() and int(size) <= 32 << 20, "committed materializer source exceeded its bound")
        committed = git(origin, "cat-file", "blob", blob, limit=32 << 20)
        path = origin / name
        require(ordinary(path, 32 << 20) == committed
                and bool(stat.S_IMODE(path.stat().st_mode) & 0o111) == (mode == "100755"),
                "original materializer source bytes/mode differ from the committed Git blob")
        sources[name] = committed
    require(git(origin, "rev-parse", "HEAD").decode().strip() == expected_head
            and not git(origin, "status", "--porcelain=v1", "--untracked-files=normal"), "original materializer source changed during binding")
    proof = {"source_files": len(names), "source_commit": expected_head}
    if out is not None:
        out = Path(out)
        require(out.is_absolute() and not any(item.is_symlink() for item in (out, *out.parents)),
                "owned materializer namespace required")
        out.mkdir()  # A fresh namespace has no ignored bytecode, packages or extensions.
        for name, raw in sources.items():
            write_new(out / name, raw)
        proof["root"] = str(out)
        proof["members"] = {name: {**pin(raw), "mode": 0o600} for name, raw in sources.items()}
        proof["materializer_path"] = str(out / "engines/experiments/strength/cloud_runtime.py")
    return proof


def process_identity(pid):
    try:
        fields = Path("/proc", str(pid), "stat").read_text().rsplit(")", 1)[1].split()
        return {"pid": pid, "pgid": int(fields[2]), "session": int(fields[3]),
                "start_ticks": int(fields[19]), "state": fields[0]}
    except FileNotFoundError:
        return None


def process_members(owner):
    current = process_identity(owner["pid"])
    require(current is not None and all(current[key] == owner[key] for key in ("pid", "pgid", "session", "start_ticks")),
            "original controller process identity is unavailable")
    result = []
    for directory in Path("/proc").iterdir():
        if directory.name.isdigit():
            item = process_identity(int(directory.name))
            if item is not None and item["pid"] != owner["pid"] and item["state"] != "Z" and item["session"] == owner["session"]:
                require(item["pgid"] == owner["pgid"], "controller child escaped its owned process group")
                result.append(item)
    return result


def signal_controller(owner, number):
    process_members(owner)  # Retain the unreaped original leader until settlement.
    os.killpg(owner["pgid"], number)


def run_request(args):
    stage, request, context = load_stage(args.stage)
    root, origin = Path(stage["root"]), Path(args.origin)
    if args.mode != "terminate":
        validate_window(request, context, time.time())
    materializer = root / "materializer"
    materializer_proof = bind_materializer_source(origin, request["source_origin"]["head_sha"], out=materializer)
    write_new(root / "reports/materializer-source.json", canonical({**materializer_proof, "source_origin": request["source_origin"]}) + b"\n")
    archive, seed_root = root / "reports/seed-transfer.zip", root / "seed"
    fetch_version(request["seed"], archive, MAX_SEED)
    subprocess.run([sys.executable, "-I", "-B", str(materializer / "engines/experiments/strength/cloud_runtime.py"),
        "materialize", "--archive", str(archive), "--manifest-sha256", request["seed_manifest_sha256"], "--out", str(seed_root)], check=True, timeout=300)
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "_execute", "--stage", str(args.stage), "--origin", str(origin), "--mode", args.mode]
    run_owned(command, root, context, "controller")


def run_owned(command, root, context, prefix, *, maximum_seconds=None):
    interrupted = [False]
    previous = {}
    def interrupt(signum, frame):
        interrupted[0] = True
    for number in (signal.SIGINT, signal.SIGTERM):
        previous[number] = signal.signal(number, interrupt)
    try:
        return _run_owned(command, root, context, prefix, interrupted, maximum_seconds=maximum_seconds)
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def _run_owned(command, root, context, prefix, interrupted, *, maximum_seconds=None):
    read_gate, write_gate = os.pipe()
    command = [*command, "--gate-fd", str(read_gate)]
    child = None
    try:
        with (root / ("reports/" + prefix + ".stdout")).open("xb") as stdout, (root / ("reports/" + prefix + ".stderr")).open("xb") as stderr:
            child = subprocess.Popen(command, start_new_session=True, pass_fds=(read_gate,), stdout=stdout, stderr=stderr)
        owner = process_identity(child.pid)
        require(owner is not None and owner["pgid"] == owner["session"] == child.pid, "dedicated controller session was not observed")
        write_new(root / ("reports/" + prefix + "-process.json"), canonical(owner) + b"\n")
        require(not interrupted[0], "controller cancelled before owner gate release")
        os.write(write_gate, b"G")
    except BaseException:
        # The child is blocked before importing a frozen module or making an
        # API call. Keep its original Popen handle unreaped until stopped.
        if child is not None:
            child.kill()
            child.wait(timeout=5)
        raise
    finally:
        os.close(read_gate)
        os.close(write_gate)
    try:
        def exited():
            return os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
        stop = time.monotonic() + maximum_seconds if maximum_seconds is not None else float("inf")
        reserve = 305 if prefix == "cleanup" else 600
        while not exited() and not interrupted[0] and time.monotonic() < stop and time.time() < context["conservatively_safe_use_until"] - reserve:
            time.sleep(1)
        forced = not exited() or bool(process_members(owner))
        if forced:
            signal_controller(owner, signal.SIGINT)
            until = min(time.monotonic() + 240, time.monotonic() + max(1, context["conservatively_safe_use_until"] - 305 - time.time()))
            while (not exited() or process_members(owner)) and time.monotonic() < until:
                time.sleep(.1)
            if not exited() or process_members(owner):
                signal_controller(owner, signal.SIGTERM)
                until = time.monotonic() + 5
                while (not exited() or process_members(owner)) and time.monotonic() < until:
                    time.sleep(.1)
            if not exited() or process_members(owner):
                signal_controller(owner, signal.SIGKILL)
                until = time.monotonic() + 5
                while (not exited() or process_members(owner)) and time.monotonic() < until:
                    time.sleep(.1)
        require(exited() and not process_members(owner), "controller process group remains unsettled")
        child.wait(timeout=1)
        write_new(root / ("reports/" + prefix + "-settled.json"), canonical({"owner": owner, "returncode": child.returncode,
            "group_absent_before_leader_reap": True, "forced": forced}) + b"\n")
        require(child.returncode == 0 and not interrupted[0] and not forced, "frozen controller retained a failure, descendant, or interruption")
    finally:
        if child.returncode is None:
            write_new(root / ("reports/" + prefix + "-unsettled.json"), canonical({"owner": owner, "physical_settlement_unproven": True}) + b"\n")


def bind_source_tree(seed_root, manifest, origin, expected_head):
    seed_root, origin = Path(seed_root), Path(origin)
    require(origin.is_absolute() and origin.is_dir() and not any(item.is_symlink() for item in (origin, *origin.parents)),
            "ordinary original Git checkout required")
    require(git(origin, "rev-parse", "HEAD").decode().strip() == expected_head
            and not git(origin, "status", "--porcelain=v1", "--untracked-files=normal"), "exact clean original source checkout required")
    prefix = logical(manifest["source_tree"]) + "/"
    selected = {logical(name[len(prefix):]): expected for name, expected in manifest["members"].items() if name.startswith(prefix)}
    require(selected, "transported source namespace is empty")
    records = git(origin, "ls-files", "--stage", "-z", "--", *sorted(selected)).split(b"\0")
    tracked = {}
    for record in filter(None, records):
        meta, name = record.split(b"\t", 1)
        mode, blob, stage = meta.decode().split()
        name = logical(name.decode())
        require(stage == "0" and mode in ("100644", "100755") and name not in tracked, "source mode/stage/link is not a regular committed blob")
        tracked[name] = (blob, 0o700 if mode == "100755" else 0o600)
    require(set(tracked) == set(selected), "transported source path set differs from the exact tracked selection")
    source_root = seed_root / prefix[:-1]
    require(source_root.is_dir() and not any(item.is_symlink() for item in (source_root, *source_root.parents)), "ordinary transported source root required")
    expected_dirs = {str(parent) for name in selected for parent in PurePosixPath(name).parents if str(parent) != "."}
    actual = set()
    for directory, subdirs, files in os.walk(source_root, followlinks=False):
        relative = Path(directory).relative_to(source_root)
        for name in subdirs:
            child = Path(directory) / name
            key = child.relative_to(source_root).as_posix()
            require(key in expected_dirs and not child.is_symlink(), "unlisted/protected source directory cannot be traversed")
        for name in files:
            key = (relative / name).as_posix()
            require(key in selected, "unlisted source member cannot be imported")
            actual.add(key)
    require(actual == set(selected), "materialized source path set is incomplete")
    for name, expected in selected.items():
        blob, mode = tracked[name]
        size = git(origin, "cat-file", "-s", blob).decode().strip()
        require(size.isdigit() and int(size) == expected["bytes"] <= 32 << 20, "committed source size differs from the transported descriptor")
        committed = git(origin, "cat-file", "blob", blob, limit=32 << 20)
        raw = ordinary(source_root / name, 32 << 20)
        require(raw == committed and pin(raw) == {key: expected[key] for key in ("bytes", "sha256")}
                and expected["mode"] == mode and stat.S_IMODE((source_root / name).stat().st_mode) == mode,
                "transported source bytes/mode differ from the original committed Git blob")
    require(git(origin, "rev-parse", "HEAD").decode().strip() == expected_head
            and not git(origin, "status", "--porcelain=v1", "--untracked-files=normal"), "original source changed during binding")
    return {"source_files": len(selected), "source_commit": expected_head, "policy": "exact raw Git blobs and declared modes; LF is never used to hide a byte mismatch"}


def load_frozen(seed_root, manifest_sha256, *, origin=None, expected_source_origin=None):
    seed_root = Path(seed_root)
    raw = ordinary(seed_root / "seed.json")
    require(hashlib.sha256(raw).hexdigest() == manifest_sha256, "materialized manifest pin differs")
    manifest = document(raw)
    require(origin is not None and expected_source_origin is not None and manifest["source_origin"] == expected_source_origin,
            "explicit original source identity required before frozen import")
    bind_source_tree(seed_root, manifest, origin, expected_source_origin["head_sha"])
    source = seed_root / logical(manifest["source_tree"])
    for name, expected in manifest["members"].items():
        require(pin(ordinary(seed_root / logical(name), 32 << 20)) == {key: expected[key] for key in ("bytes", "sha256")}, "materialized member changed before frozen import")
    path = source / "engines/experiments/strength/cloud_runtime.py"
    require("rove4k_cloud_runtime" not in sys.modules, "execution process already imported a cloud authority")
    spec = importlib.util.spec_from_file_location("rove4k_cloud_runtime", path)
    cloud = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cloud
    spec.loader.exec_module(cloud)
    cloud.revalidate_seed(manifest, seed_root)
    cloud.validate_host_source(manifest)
    return cloud, manifest


def frozen_inputs(stage_path, origin):
    stage, request, context = load_stage(stage_path)
    root = Path(stage["root"])
    cloud, manifest = load_frozen(root / "seed", request["seed_manifest_sha256"], origin=origin, expected_source_origin=request["source_origin"])
    require(manifest["source_origin"] == request["source_origin"], "seed original CI provenance differs")
    source = importlib.import_module(cloud._SIBLING_PACKAGE + ".seed")
    require(Path(source.__file__).resolve() == (cloud.ROOT / "engines/experiments/strength/seed.py").resolve(), "original seed validator imported another tree")
    members = {name: (ordinary(root / "seed" / name, 32 << 20), expected["mode"]) for name, expected in manifest["members"].items()}
    provenance = manifest.get("workflow_provenance", {})
    bound = source.workflow_binding({"workflow_provenance": request["workflow_provenance"],
        "checkout": {"path": str(origin), "commit": request["source_origin"]["head_sha"]}}, members,
        request["source_origin"], provenance.get("api_head_sha"))
    require(bound == {key: value for key, value in provenance.items() if key != "artifact_metadata"}, "original run/PR/Git binding differs")
    infrastructure = cloud.load_module("rove_ci_infrastructure", cloud.HERE / "aws_infrastructure.py")
    template = infrastructure.template(project_region=REGION)
    require(template["Resources"]["ControllerRole"]["Properties"].get("MaxSessionDuration") == DURATION,
            "frozen seed requires the reviewed 21600-second IaC cohort")
    plan = cloud.aws.AWSPlan.from_dict(request["aws_plan"])
    client = cloud.aws.AWSCLI(plan.region)
    identity = cloud.aws.verify_caller(client, plan)
    session = "rove4k-" + context["run_id"] + "-" + context["run_attempt"]
    require(identity["caller_arn"] == "arn:aws:sts::" + ACCOUNT + ":assumed-role/" + plan.controller_role_arn.rsplit("/", 1)[-1] + "/" + session,
            "actual controller session differs from this workflow")
    return stage, request, context, cloud, manifest, plan, client


def verify_campaign_history(cloud, client, plan, publisher, request, journal):
    response = client.call("dynamodb", "query", {"TableName": plan.ownership_table, "ConsistentRead": True,
        "KeyConditionExpression": "campaign_id = :campaign", "ExpressionAttributeValues": {":campaign": {"S": plan.campaign_id}}})
    require(not response.get("LastEvaluatedKey") and isinstance(response.get("Items", []), list), "complete bounded campaign ownership history required")
    records = response.get("Items", [])
    remote_keys = publisher.list_keys(plan.campaign_id + "/controller-journals/")
    if not journal.rows:
        require(not records and not remote_keys,
                "remote campaign history cannot use a fresh/reset journal")
    for key in remote_keys:
        match = re.fullmatch(re.escape(plan.campaign_id) + r"/controller-journals/([0-9a-f]{64})\.jsonl", key)
        require(match is not None, "unrecognized remote controller history object")
        raw = publisher.read_verified(key, expected_sha=match[1], max_bytes=32 << 20)
        archive = journal.path.parent / "remote-controller-history" / (match[1] + ".jsonl")
        if archive.exists():
            require(ordinary(archive, 32 << 20) == raw, "preserved controller history changed")
        else:
            write_new(archive, raw)
        rows = cloud.ledger.read_journal(archive, plan.campaign_id)
        require(len(rows) <= len(journal.rows) and rows == journal.rows[:len(rows)],
                "supplied journal omits newer or conflicting remote controller history")
    tokens = {row["record_id"]["S"][7:] for row in records if row.get("record_id", {}).get("S", "").startswith("launch#")}
    state = cloud.budget.CampaignBudget.replay(plan.campaign_id, journal.rows)
    require(tokens == {item.launch_token for item in state.instances}, "original journal omits remote launch history")


def verify_inactive_ownership(cloud, client, plan, journal):
    state = cloud.budget.CampaignBudget.replay(plan.campaign_id, journal.rows)
    for instance in state.instances:
        if instance.active:
            continue
        intent = cloud.aws.get_record(client, plan, "launch#" + instance.launch_token)
        closed = cloud.aws.get_record(client, plan, "closed#" + instance.launch_token)
        require(isinstance(intent, dict) and isinstance(closed, dict) and closed.get("terminal_state") == "terminated"
                and closed.get("instance_id") == instance.instance_id
                and all(closed.get(key) == value for key, value in intent.items()),
                "local inactivity has no matching durable remote ownership closure")


def execute_frozen(args):
    require(getattr(args, "gate_fd", None) is not None or args.mode == "terminate", "owned controller release gate required")
    if getattr(args, "gate_fd", None) is not None:
        try:
            require(os.read(args.gate_fd, 1) == b"G", "controller owner gate was not released")
        finally:
            os.close(args.gate_fd)
    stage, request, context, cloud, manifest, plan, client = frozen_inputs(args.stage, Path(args.origin))
    root = Path(stage["root"])
    if args.mode != "terminate":
        validate_window(request, context, time.time())
    campaign, ledger = cloud.bootstrap_module(), cloud.ledger
    outputs = root / "reports/evidence"
    outputs.mkdir(parents=True, exist_ok=True)
    publisher = cloud.aws.S3Evidence(client, plan, outputs)
    journal_path = root / "reports/campaign.jsonl"
    if not journal_path.exists():
        if request["journal"] is not None:
            descriptor = request["journal"]
            raw = publisher.read_verified(descriptor["object_key"], expected_sha=descriptor["sha256"], max_bytes=descriptor["bytes"])
            write_new(journal_path, raw)
            rows = ledger.read_journal(journal_path, plan.campaign_id)
            require(len(rows) == descriptor["rows"] and rows[-1]["sha256"] == descriptor["last_sha256"], "original complete journal differs")
        else:
            write_new(journal_path, b"")
    with ledger.Journal(journal_path, plan.campaign_id) as journal:
        if args.mode in ("execute", "terminate"):
            verify_campaign_history(cloud, client, plan, publisher, request, journal)
        if args.mode == "execute":
            require(not any(row["event"] == "campaign.ssm_requested" for row in journal.rows), "prior host handoff cannot be automatically relaunched")
            write_new(root / "execution-started.json", canonical({"campaign_id": plan.campaign_id, "request_sha256": stage["request"]["sha256"]}) + b"\n")
        if args.mode == "terminate" and not cloud.budget.CampaignBudget.replay(plan.campaign_id, journal.rows).active_instances:
            try:
                verify_inactive_ownership(cloud, client, plan, journal)
            except Exception as error:
                write_new(root / "reports/terminate-result.json", canonical({"complete": False, "cleanup_required": True,
                    "ownership_closed": False, "failure_type": type(error).__name__}) + b"\n")
                raise
            write_new(root / "reports/terminate-result.json", canonical({"cleanup_required": False, "paid_launch_request_sent": False}) + b"\n")
            return
        controller = campaign.CampaignController(plan, journal, client, publisher, campaign.SSMCommands(client),
            campaign.CloudRuntimeBridge() if args.mode == "execute" else None,
            seed=request["seed"], manifest=manifest, manifest_sha256=request["seed_manifest_sha256"])
        if args.mode == "inspect":
            result = controller.inspect()
        elif args.mode == "preflight":
            result = cloud.aws.preflight(client, plan, cloud.aws.fetch_advisor(REGION), time.time())
        elif args.mode == "terminate":
            if not controller.state.active_instances:
                result = {"cleanup_required": False, "paid_launch_request_sent": False}
            else:
                result = controller.terminate_owned()
        else:
            recipe = campaign.bootstrap_recipe()
            require(request["bootstrap"] == {"recipe_id": recipe["id"], "recipe_sha256": recipe["sha256"]}, "reviewed frozen bootstrap differs")
            now = time.time()
            job_id = "ci-" + context["run_id"] + "-" + context["run_attempt"]
            permit = {"format": "rove4k-campaign-permit-v1", "campaign_id": plan.campaign_id,
                "plan_sha256": cloud.aws.digest(plan.as_dict()), "seed_sha256": request["seed"]["sha256"],
                "seed_manifest_sha256": request["seed_manifest_sha256"], "deadline_epoch": plan.deadline_epoch,
                "issued_at": now, "expires_at": min(now + 900, plan.deadline_epoch),
                "reviewed_deployment": request["reviewed_deployment"], "bootstrap": request["bootstrap"],
                "deployment_receipt_sha256": ledger.digest({"deployment": request["reviewed_deployment"], "bootstrap": request["bootstrap"]}),
                "runtime_bridge": "rove4k_cloud_runtime", "source_origin": request["source_origin"],
                "host": {"host_job_id": job_id, "root": "/opt/rove4k/" + plan.campaign_id + "-" + plan.owner_nonce[:12],
                         "cgroup_root": "/sys/fs/cgroup/system.slice/rove4k-" + job_id + ".service"}}
            write_new(root / "reports/permit.json", canonical(permit) + b"\n")
            result = controller.execute(permit, cloud.aws.fetch_advisor(REGION))
        write_new(root / "reports" / (args.mode + "-result.json"), canonical(result) + b"\n")
        if args.mode == "preflight":
            require(result.get("allowed") is True, "fresh preflight denied")
        elif args.mode in ("execute", "terminate"):
            require(result.get("complete") is True or result.get("cleanup_required") is False,
                    "campaign retained incomplete results or ownership")


def cleanup_request(args):
    stage, request, context = load_stage(args.stage)
    root = Path(stage["root"])
    if not (root / "execution-started.json").exists():
        return
    ownership = root / "reports/controller-process.json"
    if ownership.exists():
        owner = document(ordinary(ownership))
        current = process_identity(owner["pid"])
        require(current is None or current["start_ticks"] != owner["start_ticks"], "original controller is still live; no second cleanup owner")
        require((root / "reports/controller-settled.json").is_file(), "original controller group settlement is unproven")
    require(time.time() < context["conservatively_safe_use_until"] - 30, "cleanup credential window expired; independent watchdog remains authoritative")
    run_owned([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "_execute", "--stage", str(args.stage),
               "--origin", str(args.origin), "--mode", "terminate"], root, context, "cleanup", maximum_seconds=300)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("stage")
    for name in ("campaign-id", "bucket", "key", "version-id", "sha256"):
        stage.add_argument("--" + name, required=True)
    stage.add_argument("--bytes", type=int, required=True)
    stage.add_argument("--out", type=Path, required=True)
    for name in ("run", "cleanup", "_execute"):
        command = commands.add_parser(name)
        command.add_argument("--stage", type=Path, required=True)
        command.add_argument("--origin", type=Path, required=True)
        if name != "cleanup":
            command.add_argument("--mode", choices=("inspect", "preflight", "execute", "terminate"), required=True)
        if name == "_execute":
            command.add_argument("--gate-fd", type=int)
    args = parser.parse_args(argv)
    try:
        {"stage": stage_request, "run": run_request, "cleanup": cleanup_request, "_execute": execute_frozen}[args.command](args)
        return 0
    except Exception as error:
        # Auth, CLI and HTTP diagnostics may contain sensitive values. Report a
        # stable classification, never the raw response or exception text.
        result = {"complete": False, "error_type": type(error).__name__, "operation": args.command}
        if type(error) is ValueError:
            result["message"] = str(error)
        print(json.dumps(result))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
