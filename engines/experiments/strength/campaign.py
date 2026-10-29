#!/usr/bin/env python3
"""Explicit cloud campaign consumer; inspect is offline and never allocates.

The journal owns the launch slot before EC2 sees a request. Recovery never sends
another RunInstances request. SSM success is transport evidence, not acceptance
of chess results. The host bridge must collect checksum-verified host evidence.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import time

sys.dont_write_bytecode = True

try:
    from . import aws, budget, ledger
except ImportError:
    import aws
    import budget
    import ledger


REGION = "ap-southeast-2"
SHA = re.compile(r"[a-f0-9]{64}")
TERMINAL = frozenset(("Success", "Cancelled", "TimedOut", "Failed"))
BOOTSTRAP_RECIPE_ID = "rove4k-ubuntu22-ssm-bootstrap-v1"
AWS_CLI_VERSION = "2.38.5"
AWS_CLI_SIGNER = "FB5DB77FD5C118B80511ADA8A6310ACC4672475C"
# Public distribution-verification key, copied from the official AWS CLI guide.
# This is not a credential or a private signing key.
AWS_CLI_PUBLIC_KEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----

mQINBF2Cr7UBEADJZHcgusOJl7ENSyumXh85z0TRV0xJorM2B/JL0kHOyigQluUG
ZMLhENaG0bYatdrKP+3H91lvK050pXwnO/R7fB/FSTouki4ciIx5OuLlnJZIxSzx
PqGl0mkxImLNbGWoi6Lto0LYxqHN2iQtzlwTVmq9733zd3XfcXrZ3+LblHAgEt5G
TfNxEKJ8soPLyWmwDH6HWCnjZ/aIQRBTIQ05uVeEoYxSh6wOai7ss/KveoSNBbYz
gbdzoqI2Y8cgH2nbfgp3DSasaLZEdCSsIsK1u05CinE7k2qZ7KgKAUIcT/cR/grk
C6VwsnDU0OUCideXcQ8WeHutqvgZH1JgKDbznoIzeQHJD238GEu+eKhRHcz8/jeG
94zkcgJOz3KbZGYMiTh277Fvj9zzvZsbMBCedV1BTg3TqgvdX4bdkhf5cH+7NtWO
lrFj6UwAsGukBTAOxC0l/dnSmZhJ7Z1KmEWilro/gOrjtOxqRQutlIqG22TaqoPG
fYVN+en3Zwbt97kcgZDwqbuykNt64oZWc4XKCa3mprEGC3IbJTBFqglXmZ7l9ywG
EEUJYOlb2XrSuPWml39beWdKM8kzr1OjnlOm6+lpTRCBfo0wa9F8YZRhHPAkwKkX
XDeOGpWRj4ohOx0d2GWkyV5xyN14p2tQOCdOODmz80yUTgRpPVQUtOEhXQARAQAB
tCFBV1MgQ0xJIFRlYW0gPGF3cy1jbGlAYW1hem9uLmNvbT6JAlQEEwEIAD4CGwMF
CwkIBwIGFQoJCAsCBBYCAwECHgECF4AWIQT7Xbd/1cEYuAURraimMQrMRnJHXAUC
akV0ygUJDqP4lQAKCRCmMQrMRnJHXFHjD/9eyZLYcKuQOlLvtqSDtUBiEZf6ZZjM
i3ygYH8rJNtuToUH+HvSpe819urJCquXhDrlK6N+aqW0hCLtNABJG/vsafIgvIYJ
hSGgpgtNnQyMV1jViRWqPjbouw8OkYKBThUfT1i2Y+wn58ifs6ODBCmTexWtXspA
Si+Gt49xDOW0APmbOPnI+a4HJW6tVEo6MWS0WjzpiBayR3d1A4pt4YrPfSdDgpLo
h2SLQqlRqvvVZJaWBjhkErNFpfsBA06sDcPEOb0G8LBUbR4WOcdvhe5LubJbZuxC
AG9kNPCVeQP1ixwjgjXKysaxeQ6rv0VzIQgRp6tLVLWhy6AKDNvLjFSsmXZ1Wl08
Y/RlOHXlzLuQMRE6sR1wOdRxc9TsrNWTGiBK65cvSWOy03JeBkQQ8pesqltiyxI9
U21kkgiXtTSKNGfKK8pO27D81YANhRqPK7iTp6kuFiY2WtOg90KTMNlIT+Ff85Y2
b1rHj6Z0SrCkJujhWk3IBPic/wJgz01LEc/OAdUPlby90RJZcIBhSlWhT7mXnXIO
c0HWlNQrns2s3CTyYwZSiSlYe9ApeLwhjDo8NhbFuCAy61l6O5UsR4AfZxx/rGKv
2wFb1/RN/P4gNe6vmxZAPjR0AQcwD3tc2McimOLr/22kmPz8IH3I0X7WoSFr0Biz
E91G7bb0hOb/cA==
=knv7
-----END PGP PUBLIC KEY BLOCK-----
"""


class BootstrapRunner:
    """Own and reap each bootstrap process group before admitting host work."""
    def __init__(self, root, deadline, *, clock=None):
        import time
        from pathlib import Path
        self.root, self.deadline = Path(root), deadline
        self.clock = clock or time.time
        self.commands = []

    @staticmethod
    def identity(pid):
        from pathlib import Path
        raw = (Path("/proc") / str(pid) / "stat").read_text()
        fields = raw[raw.rfind(")") + 2:].split()
        return {"pid": pid, "pgid": int(fields[2]), "sid": int(fields[3]), "start_ticks": int(fields[19])}

    @classmethod
    def members(cls, owner):
        from pathlib import Path
        found = []
        for path in Path("/proc").iterdir():
            if not path.name.isdigit():
                continue
            try:
                row = cls.identity(int(path.name))
            except (FileNotFoundError, ProcessLookupError):
                continue
            if row["pgid"] == owner["pgid"] and row["sid"] == owner["sid"]:
                found.append(row)
        return found

    def run(self, argv, maximum_seconds, *, env=None, cwd=None):
        import hashlib, os, signal, subprocess, time
        limit = min(maximum_seconds, self.deadline - self.clock())
        if limit <= 0:
            raise TimeoutError("bootstrap deadline is due")
        number = len(self.commands)
        out, err = self.root / (str(number) + ".stdout"), self.root / (str(number) + ".stderr")
        record = {"argv": list(argv), "started_at": self.clock(), "forced_cleanup": False,
                  "reaped": False, "group_absent": False}
        self.commands.append(record)
        with out.open("xb") as stdout, err.open("xb") as stderr:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                       cwd=cwd, env=env, start_new_session=True)
            owner = self.identity(process.pid)
            record.update(owner)
            if owner["pgid"] != process.pid or owner["sid"] != process.pid:
                raise RuntimeError("bootstrap child did not own its new session")
            try:
                process.wait(timeout=limit)
            except BaseException:
                record["forced_cleanup"] = True
                os.killpg(owner["pgid"], signal.SIGTERM)
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(owner["pgid"], signal.SIGKILL)
                    process.wait(timeout=3)
            record["reaped"] = process.poll() is not None
            record["returncode"] = process.returncode
            members = self.members(owner)
            if members:
                record["forced_cleanup"] = True
                # Do not signal a recycled session leader.
                try:
                    current = self.identity(owner["pid"])
                except (FileNotFoundError, ProcessLookupError):
                    current = None
                if current is None or current == owner:
                    os.killpg(owner["pgid"], signal.SIGKILL)
                end = time.monotonic() + 3
                while members and time.monotonic() < end:
                    time.sleep(0.02)
                    members = self.members(owner)
            record["group_absent"] = not members
            record["terminal"] = record["reaped"] and record["group_absent"]
            record["finished_at"] = self.clock()
            for name, path in (("stdout", out), ("stderr", err)):
                raw = path.read_bytes()
                record[name] = {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        if record["returncode"] != 0 or not record["reaped"] or not record["group_absent"] or record["forced_cleanup"]:
            raise RuntimeError("bootstrap command failed or retained descendants")
        return record


def install_bootstrap(root, recipe, permit, plan, *, runner_factory=None, clock=None):
    """Install only the fixed signed recipe on this already-owned instance."""
    import hashlib, json, os, pathlib, shutil, time
    clock = clock or time.time
    root = pathlib.Path(root)
    started = clock()
    deadline = min(started + recipe["maximum_seconds"], permit["expires_at"], plan["deadline_epoch"] - 30)
    if deadline <= started:
        raise TimeoutError("bootstrap cannot start after its permit/deadline")
    work = root / "bootstrap"
    work.mkdir()
    runner = (runner_factory or BootstrapRunner)(work, deadline, clock=clock)
    env = os.environ.copy()
    env.update(DEBIAN_FRONTEND="noninteractive", NEEDRESTART_MODE="l", AWS_CONFIG_FILE=os.devnull,
               AWS_SHARED_CREDENTIALS_FILE=os.devnull, AWS_PAGER="", AWS_CLI_AUTO_PROMPT="off")
    for name in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AWS_WEB_IDENTITY_TOKEN_FILE"):
        env.pop(name, None)
    receipt = {"format": "rove4k-bootstrap-receipt-v1", "recipe_id": recipe["id"],
        "recipe_sha256": recipe["sha256"], "started_at": started, "deadline_epoch": deadline,
        "commands": runner.commands, "complete": False}
    try:
        sources = work / "ubuntu.list"
        sources.write_text(recipe["apt_sources"])
        receipt["apt_sources_sha256"] = hashlib.sha256(sources.read_bytes()).hexdigest()
        (work / "empty-preferences").write_text("")
        apt = ["/usr/bin/apt-get", "-o", "Dir::Etc::sourcelist=" + str(sources),
            "-o", "Dir::Etc::sourceparts=-", "-o", "Dir::Etc::preferences=" + str(work / "empty-preferences"),
            "-o", "Dir::Etc::preferencesparts=-", "-o", "Acquire::Retries=0", "-o", "Acquire::http::Timeout=30",
            "-o", "Acquire::https::Timeout=30", "-o", "DPkg::Lock::Timeout=30",
            "-o", "Acquire::AllowInsecureRepositories=false", "-o", "Acquire::AllowDowngradeToInsecureRepositories=false",
            "-o", "APT::Get::AllowUnauthenticated=false", "-o", "Acquire::AllowWeakRepositories=false",
            "-o", "Acquire::Check-Valid-Until=true", "-o", "Acquire::Check-Date=true"]
        runner.run([*apt, "update", "--error-on=any"], 120, env=env)
        runner.run([*apt, "install", "--yes", "--no-install-recommends", "--no-remove", *recipe["apt_packages"]], 360, env=env)
        runner.run(["/usr/bin/dpkg-query", "-W", "-f=${binary:Package}=${Version}\\n", *recipe["apt_packages"]], 10, env=env)
        key = work / "aws-cli-public.asc"
        key.write_text(recipe["aws_cli_public_key"])
        gnupg = work / "gnupg"
        gnupg.mkdir(mode=0o700)
        runner.run(["/usr/bin/gpg", "--homedir", str(gnupg), "--batch", "--import", str(key)], 20, env=env)
        archive, signature = work / "awscliv2.zip", work / "awscliv2.zip.sig"
        for url, target in ((recipe["aws_cli_url"], archive), (recipe["aws_cli_url"] + ".sig", signature)):
            runner.run(["/usr/bin/curl", "--fail", "--silent", "--show-error", "--proto", "=https", "--tlsv1.2",
                        "--connect-timeout", "10", "--max-time", "120", "--max-filesize",
                        str((128 << 20) if target == archive else (1 << 20)), "--output", str(target), url], 125, env=env)
        if archive.stat().st_size > 128 << 20 or signature.stat().st_size > 1 << 20:
            raise ValueError("AWS CLI distribution exceeds bounded download")
        verification = runner.run(["/usr/bin/gpg", "--homedir", str(gnupg), "--batch", "--status-fd=1",
                                   "--verify", str(signature), str(archive)], 20, env=env)
        status = pathlib.Path(verification["stdout"]["path"]).read_text()
        valid = [line.split()[2] for line in status.splitlines() if line.startswith("[GNUPG:] VALIDSIG ")]
        if valid != [recipe["aws_cli_signer_fingerprint"]]:
            raise ValueError("AWS CLI signature is not from the exact pinned publisher key")
        receipt["aws_cli_archive"] = {"url": recipe["aws_cli_url"], "version": recipe["aws_cli_version"],
            "bytes": archive.stat().st_size, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "signature_sha256": hashlib.sha256(signature.read_bytes()).hexdigest(),
            "signer_fingerprint": valid[0]}
        runner.run(["/usr/bin/unzip", "-q", str(archive), "-d", str(work / "distribution")], 30, env=env)
        owned_bin = root / "bin"
        owned_bin.mkdir()
        runner.run([str(work / "distribution" / "aws" / "install"), "--install-dir", str(root / "aws-cli"),
                    "--bin-dir", str(owned_bin)], 60, env=env)
        for name, target in (("cc", "/usr/bin/gcc-11"), ("gcc", "/usr/bin/gcc-11"),
                             ("c++", "/usr/bin/g++-12"), ("g++", "/usr/bin/g++-12")):
            (owned_bin / name).symlink_to(target)
        env["PATH"] = str(owned_bin) + ":/usr/bin:/bin:/snap/bin"
        tools = {}
        for name in ("python3", "aws", "cc", "gcc", "c++", "g++", "git", "make", "xz", "systemd-run"):
            path = shutil.which(name, path=env["PATH"])
            if path is None:
                raise ValueError("installed bootstrap tool is absent: " + name)
            actual = pathlib.Path(path).resolve(strict=True)
            raw = actual.read_bytes()
            row = runner.run([path, "--version"], 10, env=env)
            version = pathlib.Path(row["stdout"]["path"]).read_text(errors="replace")[:4096]
            tools[name] = {"path": path, "resolved_path": str(actual), "bytes": len(raw),
                           "sha256": hashlib.sha256(raw).hexdigest(), "version": version}
        if not tools["aws"]["version"].startswith("aws-cli/" + recipe["aws_cli_version"] + " "):
            raise ValueError("installed AWS CLI version differs from signed recipe")
        receipt["tools"] = tools
        receipt["complete"] = True
        return env
    finally:
        receipt["finished_at"] = clock()
        path = work / "receipt.json"
        with path.open("xb") as output:
            output.write(json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
            output.flush(); os.fsync(output.fileno())


def bootstrap_recipe():
    value = {"format": "rove4k-bootstrap-recipe-v1", "id": BOOTSTRAP_RECIPE_ID,
        "maximum_seconds": 600, "aws_cli_version": AWS_CLI_VERSION,
        "aws_cli_signer_fingerprint": AWS_CLI_SIGNER, "aws_cli_public_key": AWS_CLI_PUBLIC_KEY,
        "aws_cli_url": "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-" + AWS_CLI_VERSION + ".zip",
        "apt_packages": ["python3", "build-essential", "gcc-11", "g++-12", "git", "xz-utils", "ca-certificates",
                         "curl", "unzip", "gnupg", "groff", "less"],
        "apt_suites": ["jammy", "jammy-updates", "jammy-security"],
        "apt_sources": "".join("deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] " +
            ("http://security.ubuntu.com/ubuntu " if suite == "jammy-security" else "http://archive.ubuntu.com/ubuntu ") +
            suite + " main universe\n" for suite in ("jammy", "jammy-updates", "jammy-security")),
        "installer_source_sha256": hashlib.sha256(inspect.getsource(install_bootstrap).encode()).hexdigest(),
        "process_owner_source_sha256": hashlib.sha256(inspect.getsource(BootstrapRunner).encode()).hexdigest()}
    return {**value, "sha256": ledger.digest(value)}


BOOTSTRAP_RECIPE_SHA256 = bootstrap_recipe()["sha256"]


def object_dict(value):
    value = asdict(value) if is_dataclass(value) else value
    if not isinstance(value, dict):
        raise ValueError("an explicit JSON object is required")
    return json.loads(ledger.canonical(value))


def seed_descriptor(value, plan):
    value = object_dict(value)
    if (set(value) != {"bucket", "key", "version_id", "sha256", "bytes"}
            or value["bucket"] != plan.artifact_bucket
            or not isinstance(value["key"], str)
            or not value["key"].startswith(plan.campaign_id + "/")
            or any(part in ("", ".", "..") for part in value["key"].split("/"))
            or not isinstance(value["version_id"], str) or value["version_id"] in ("", "null")
            or not isinstance(value["sha256"], str) or not SHA.fullmatch(value["sha256"])
            or type(value["bytes"]) is not int or not 0 < value["bytes"] <= 128 << 20):
        raise ValueError("versioned, bounded campaign seed identity required")
    return value


def validate_permit(value, plan, seed, manifest_sha, now):
    """Bind explicit execution approval; live authority is checked separately."""
    value, now = object_dict(value), budget.timestamp(now)
    if not isinstance(manifest_sha, str) or not SHA.fullmatch(manifest_sha):
        raise ValueError("sealed seed manifest SHA-256 required")
    expected = {"format": "rove4k-campaign-permit-v1", "campaign_id": plan.campaign_id,
                "plan_sha256": aws.digest(plan.as_dict()), "seed_sha256": seed["sha256"],
                "seed_manifest_sha256": manifest_sha, "deadline_epoch": plan.deadline_epoch}
    if any(value.get(name) != item for name, item in expected.items()):
        raise ValueError("execution permit differs from the exact plan/seed/deadline")
    issued, expires = budget.timestamp(value["issued_at"]), budget.timestamp(value["expires_at"])
    if not issued <= now < expires <= issued + 900 or expires > plan.deadline_epoch:
        raise ValueError("execution permit is stale, future-dated, or excessively long")
    if not SHA.fullmatch(value.get("deployment_receipt_sha256", "")):
        raise ValueError("reviewed deployment receipt identity required")
    host = value.get("host", {})
    root = PurePosixPath(host.get("root", ""))
    allowed = PurePosixPath("/opt/rove4k") / (plan.campaign_id + "-" + plan.owner_nonce[:12])
    job_id = ledger.valid_id(host.get("host_job_id"))
    cgroup = PurePosixPath(host.get("cgroup_root", ""))
    if (root != allowed or cgroup != PurePosixPath("/sys/fs/cgroup/system.slice") / ("rove4k-" + job_id + ".service")):
        raise ValueError("explicit owned host and delegated cgroup paths required")
    if value.get("runtime_bridge") != "rove4k_cloud_runtime":
        raise ValueError("canonical cloud runtime provider required")
    if value.get("bootstrap") != {"recipe_id": BOOTSTRAP_RECIPE_ID, "recipe_sha256": BOOTSTRAP_RECIPE_SHA256}:
        raise ValueError("fixed reviewed same-instance Ubuntu bootstrap recipe required")
    return value


def sealed_json(path, expected_sha=None, *, maximum=4 << 20):
    """Read only an explicit non-secret regular input, with bounded bytes."""
    path = Path(path)
    if not path.is_absolute() or any(any(token in part.lower() for token in
            (".env", "credential", "inventory", "service-account", "api_key", ".aws", ".ssh"))
            for part in path.parts):
        raise ValueError("absolute non-secret JSON input required")
    if any(item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction())
           for item in (path, *path.parents)):
        raise ValueError("input cannot follow links")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
        raise ValueError("bounded regular JSON input required")
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
    if identity(before) != identity(after) or len(raw) != before.st_size:
        raise ValueError("sealed JSON input changed during reading")
    if expected_sha is not None and (not SHA.fullmatch(expected_sha)
            or hashlib.sha256(raw).hexdigest() != expected_sha):
        raise ValueError("input byte identity differs")
    return object_dict(json.loads(raw)), hashlib.sha256(raw).hexdigest()


class CloudRuntimeBridge:
    """The real cloud module must implement both ends before launch is possible."""
    def __init__(self):
        name = (__package__ + ".cloud_runtime") if __package__ else "cloud_runtime"
        module = sys.modules.get("rove4k_cloud_runtime") or importlib.import_module(name)
        module = module.canonical_provider()
        self.validator = getattr(module, "validate_controller_inputs", None)
        self.collector = getattr(module, "collect_host_result", None)
        if not callable(self.validator) or not callable(self.collector):
            raise RuntimeError("cloud runtime controller validation/result bridge is unavailable")

    def validate(self, **inputs):
        return self.validator(**inputs)

    def collect(self, **inputs):
        return self.collector(**inputs)


class SSMCommands:
    """Reuse the bounded AWS transport; no second credential provider chain."""
    def __init__(self, client):
        self.client = client

    def ready(self, instance_id):
        response = self.client.call("ssm", "describe-instance-information", {
            "Filters": [{"Key": "InstanceIds", "Values": [instance_id]}]})
        rows = response.get("InstanceInformationList", [])
        if not isinstance(rows, list) or len(rows) > 1 or response.get("NextToken"):
            raise ValueError("SSM readiness response is ambiguous")
        if not rows:
            return {"instance_id": instance_id, "ready": False, "ping_status": "NotObserved"}
        row = rows[0]
        if (row.get("InstanceId") != instance_id or row.get("PlatformType") != "Linux"
                or not isinstance(row.get("AgentVersion"), str) or not 0 < len(row["AgentVersion"]) <= 128):
            raise ValueError("SSM readiness identity/platform/agent differs")
        if row.get("PingStatus") not in ("Online", "ConnectionLost", "Inactive"):
            raise ValueError("unknown SSM managed-node ping state")
        return {"instance_id": instance_id, "ready": row["PingStatus"] == "Online",
                "ping_status": row["PingStatus"], "agent_version": row["AgentVersion"], "platform_type": "Linux"}

    def send(self, plan, instance_id, command, job_id, seconds):
        if type(seconds) is not int or not 30 <= seconds <= 43200:
            raise ValueError("bounded SSM execution interval required")
        result = self.client.call("ssm", "send-command", {"InstanceIds": [instance_id], "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": [command], "executionTimeout": [str(seconds)]},
            "TimeoutSeconds": 60, "MaxConcurrency": "1", "MaxErrors": "0",
            "Comment": "rove4k:" + job_id, "OutputS3BucketName": plan.artifact_bucket,
            "OutputS3KeyPrefix": plan.campaign_id + "/ssm/" + job_id})
        row = result.get("Command", {})
        command_id = row.get("CommandId", "")
        if not re.fullmatch(r"[a-f0-9-]{36}", command_id) or row.get("InstanceIds") != [instance_id]:
            raise ValueError("SSM response has no exact command/instance binding")
        return command_id

    def observe(self, command_id, instance_id):
        try:
            row = self.client.call("ssm", "get-command-invocation", {"CommandId": command_id, "InstanceId": instance_id})
        except aws.AwsError as error:
            if error.code != "InvocationDoesNotExist":
                raise
            return {"command_id": command_id, "instance_id": instance_id, "status": "NotObserved"}
        if row.get("CommandId") != command_id or row.get("InstanceId") != instance_id:
            raise ValueError("SSM invocation identity changed")
        status = row.get("Status")
        if status not in TERMINAL | {"Pending", "InProgress", "Delayed", "Cancelling"}:
            raise ValueError("unknown SSM invocation state")
        # stdout/stderr can contain arbitrary program data; persist only their
        # hashes here, with complete output retained in the campaign S3 prefix.
        return {"command_id": command_id, "instance_id": instance_id, "status": status,
                "response_code": row.get("ResponseCode"),
                "stdout_sha256": hashlib.sha256(row.get("StandardOutputContent", "").encode()).hexdigest(),
                "stderr_sha256": hashlib.sha256(row.get("StandardErrorContent", "").encode()).hexdigest()}

    def cancel(self, command_id, instance_id):
        self.client.call("ssm", "cancel-command", {"CommandId": command_id, "InstanceIds": [instance_id]})


def bootstrap_command(handoff, permit, manifest, *, systemd_run="/usr/bin/systemd-run"):
    """Install the fixed signed tools, then import only a sealed source ZIP."""
    source_tree = manifest.get("source_tree", "")
    if (not isinstance(source_tree, str) or not source_tree or "\\" in source_tree
            or PurePosixPath(source_tree).is_absolute()
            or any(part in ("", ".", "..") for part in source_tree.split("/"))):
        raise ValueError("sealed source_tree namespace required")
    if not isinstance(systemd_run, str) or not PurePosixPath(systemd_run).is_absolute():
        raise ValueError("absolute systemd-run executable required")
    ledger.valid_id(handoff.get("host_job_id"))
    payload = base64.b64encode(ledger.canonical({"handoff": handoff, "permit": permit,
                                               "recipe": bootstrap_recipe()})).decode()
    # The inline loader verifies paths/types/lengths before extraction and
    # verifies *all* archive members before importing any campaign source.
    script = '''import base64,hashlib,json,os,pathlib,re,stat,subprocess,sys,zipfile
d=json.loads(base64.b64decode(PAYLOAD)); h=d['handoff']; p=d['permit']; s=h['seed']
enc=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def seed_expansion_limit(value):
 if not isinstance(value,dict): raise ValueError('explicit source profile lists required')
 seen=set(); rove=set()
 for kind,families in (('rove',tuple('ABCDEF')),('peers',('ice4','c4ke'))):
  rows=value.get(kind)
  if not isinstance(rows,list): raise ValueError('explicit source profile lists required')
  for row in rows:
   if not isinstance(row,dict) or not isinstance(row.get('family'),str) or not isinstance(row.get('profile'),str) or row['family'] not in families or row['profile'] not in ('test-p4','test-p28'): raise ValueError('invalid source family/profile')
   identity=row['family'],row['profile']
   if identity in seen: raise ValueError('duplicate seed family/profile')
   seen.add(identity)
   if kind=='rove': rove.add(identity)
 if not seen: raise ValueError('seed contains no explicit TEST source inputs')
 joint={(family,profile) for family in 'ABCDEF' for profile in ('test-p4','test-p28')}
 return 268435456 if rove==joint else 134217728
root=pathlib.Path(h['root'])
assert not any(p.is_symlink() for p in (root,*root.parents)), 'bootstrap root must not follow links'
root.mkdir(parents=True,exist_ok=False)
archive=root/'seed.zip'
env=install_bootstrap(root,d['recipe'],p,h['aws_plan'])
remaining=min(120,p['expires_at']-__import__('time').time(),h['aws_plan']['deadline_epoch']-30-__import__('time').time())
assert remaining>0, 'bootstrap permit/deadline expired before seed transfer'
subprocess.run(['aws','--region',h['aws_plan']['region'],'--no-cli-pager','s3api','get-object','--bucket',s['bucket'],'--key',s['key'],'--version-id',s['version_id'],str(archive)],env=env,check=True,timeout=remaining,stdout=subprocess.DEVNULL)
assert archive.stat().st_size==s['bytes'] and hashlib.sha256(archive.read_bytes()).hexdigest()==s['sha256'], 'seed archive identity differs'
out=root/'seed'
with zipfile.ZipFile(archive) as z:
 infos=z.infolist(); names=[i.filename for i in infos]; assert len(names)==len(set(names)) and len(names)<=20000, 'duplicate/excessive ZIP namespace'
 manifest_info=z.getinfo('seed.json'); assert 0<=manifest_info.file_size<=4194304 and not manifest_info.flag_bits&1, 'seed manifest exceeds bounded read'
 with z.open(manifest_info) as f: raw=f.read(4194305)
 assert len(raw)==manifest_info.file_size and len(raw)<=4194304 and hashlib.sha256(raw).hexdigest()==h['seed_manifest_sha256'], 'seed manifest identity differs'
 m=json.loads(raw); assert isinstance(m,dict) and m.get('format')=='rove4k-cloud-seed-v1' and raw==enc(m)+b'\\n', 'seed manifest must be canonical JSON plus one LF'
 expanded_limit=seed_expansion_limit(m)
 members=m.get('members'); assert isinstance(members,dict) and members and len(members)<20000, 'explicit bounded member map required'
 declared_total=len(raw)
 blocked={'.git','.aws','.ssh','node_modules','dist','dist-server','coverage','models','checkpoints','.cache','inventory.json','package-lock.json'}
 for n,v in members.items():
  assert isinstance(n,str) and n and n!='seed.json' and '\\\\' not in n and ':' not in n and '\\0' not in n and not pathlib.PurePosixPath(n).is_absolute() and all(x not in ('','.','..') for x in n.split('/')), 'unsafe manifest member path'
  assert not any(x.casefold() in blocked or x.casefold().startswith('.env') or re.search(r'credential|service[-_ ]?account|api[-_ ]?key|ssh[-_ ]?key|^id_(rsa|ed25519)$',x,re.I) for x in n.split('/')), 'protected manifest member path'
  assert isinstance(v,dict) and set(v)=={'bytes','sha256','mode'} and type(v['bytes']) is int and 0<=v['bytes']<=33554432 and isinstance(v['sha256'],str) and re.fullmatch('[0-9a-f]{64}',v['sha256']) and type(v['mode']) is int and v['mode'] in (384,448), 'bounded manifest member descriptor required'
  declared_total+=v['bytes']
 assert declared_total<=expanded_limit, 'declared seed expansion exceeds bound'
 namespace=set(members)|{'seed.json'}
 assert not any(str(parent) in namespace for n in members for parent in pathlib.PurePosixPath(n).parents if str(parent)!='.'), 'seed file/directory namespace collision'
 assert set(names)==set(members)|{'seed.json'}, 'seed members differ'
 assert all(0<=i.file_size<=33554432 and not i.flag_bits&1 for i in infos) and sum(i.file_size for i in infos)<=expanded_limit, 'ZIP expansion/encryption unsupported'
 for i in infos:
  assert __import__('time').time()<min(p['expires_at'],h['aws_plan']['deadline_epoch']-30), 'bootstrap deadline during extraction'
  n=i.filename; q=pathlib.PurePosixPath(n); mode=i.external_attr>>16
  assert n and not q.is_absolute() and '\\\\' not in n and ':' not in n and all(x not in ('','.','..') for x in n.split('/')) and not i.is_dir(), 'unsafe ZIP path'
  assert stat.S_IFMT(mode) in (0,stat.S_IFREG), 'ZIP member must be a regular file'
  if n=='seed.json': continue
  assert i.file_size==members[n]['bytes'], 'ZIP metadata differs'
 for i in infos:
  if i.filename=='seed.json': continue
  assert __import__('time').time()<min(p['expires_at'],h['aws_plan']['deadline_epoch']-30), 'bootstrap deadline during payload verification'
  data=z.read(i); assert hashlib.sha256(data).hexdigest()==members[i.filename]['sha256'], 'ZIP member bytes differ'
 out.mkdir()
 for n,v in members.items():
  target=out/n; target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f: f.write(z.read(n))
  target.chmod(v['mode'])
 (out/'seed.json').write_bytes(raw)
handoff=root/'handoff.json'; approval=root/'permit.json'
handoff.write_bytes(enc(h)); approval.write_bytes(enc(p))
entry=out/SOURCE_TREE/'engines/experiments/strength/cloud_runtime.py'
assert entry.is_file(), 'sealed cloud runtime is absent'
assert __import__('time').time()<min(p['expires_at'],h['aws_plan']['deadline_epoch']-30), 'bootstrap deadline before host start'
os.execv(SYSTEMD_RUN,[SYSTEMD_RUN,'--unit=rove4k-'+h['host_job_id']+'.service','--property=Delegate=yes','--property=Type=exec','--wait','--pipe','--setenv=PATH='+env['PATH'],'--setenv=AWS_CONFIG_FILE=/dev/null','--setenv=AWS_SHARED_CREDENTIALS_FILE=/dev/null','--collect',sys.executable,'-I',str(entry),'host','--handoff',str(handoff),'--handoff-sha256',hashlib.sha256(enc(h)).hexdigest(),'--permit',str(approval),'--permit-sha256',hashlib.sha256(enc(p)).hexdigest()])
'''.replace("PAYLOAD", repr(payload)).replace("SOURCE_TREE", repr(source_tree)).replace("SYSTEMD_RUN", repr(systemd_run))
    script = inspect.getsource(BootstrapRunner) + "\n" + inspect.getsource(install_bootstrap) + "\n" + script
    return "set -eu\nexec python3 -I - <<'ROVE_CLOUD_BOOTSTRAP'\n" + script + "ROVE_CLOUD_BOOTSTRAP\n"


def merge_host_rows(journal, handoff, rows):
    """Validate the entire original chain before appending any returned event."""
    if not isinstance(rows, list) or len(rows) < len(journal.rows):
        raise ValueError("host journal omitted the original controller prefix")
    branch = handoff["journal"]
    if (branch["rows"] != len(journal.rows) or branch["last_sha256"] != journal.last
            or rows[:len(journal.rows)] != journal.rows):
        raise ValueError("host journal/controller handoff branch differs")
    previous = "0" * 64
    for sequence, original in enumerate(rows):
        row = object_dict(original)
        required = {"format", "seq", "event", "time_utc", "campaign", "pair", "game", "attempt",
                    "data", "previous_sha256", "sha256"}
        if (set(row) != required or type(row.get("seq")) is not int
                or not isinstance(row.get("event"), str) or not 0 < len(row["event"]) <= 80
                or not isinstance(row.get("data"), dict) or len(ledger.canonical(row)) + 1 > 1 << 20):
            raise ValueError("returned host event is not appendable without changing its identity")
        for key in ("pair", "game"):
            if row[key] is not None:
                ledger.valid_id(row[key])
        if row["attempt"] is not None and (type(row["attempt"]) is not int or row["attempt"] < 0):
            raise ValueError("returned host event attempt differs")
        claimed = row.pop("sha256", None)
        if (row.get("format") != "rove4k-campaign-v1" or row.get("campaign") != journal.campaign
                or row.get("seq") != sequence or row.get("previous_sha256") != previous
                or ledger.digest(row) != claimed):
            raise ValueError("returned host journal chain differs")
        previous = claimed
    budget.CampaignBudget.replay(journal.campaign, rows)
    for original in rows[len(journal.rows):]:
        written = journal.append(original["event"], original["data"], pair=original["pair"],
            game=original["game"], attempt=original["attempt"], time_utc=original["time_utc"])
        if written != original:
            raise ValueError("host event could not retain its original physical journal identity")


def run_host_handoff(handoff_path, handoff_sha256, permit_path, permit_sha256):
    """EC2-side CLI boundary; the source was materialized by the sealed loader."""
    handoff, _ = sealed_json(handoff_path, handoff_sha256)
    permit, _ = sealed_json(permit_path, permit_sha256)
    if handoff.get("format") != "rove4k-cloud-handoff-v1":
        raise ValueError("explicit cloud handoff required")
    plan = aws.AWSPlan.from_dict(handoff["aws_plan"])
    if plan.region != REGION or plan.project_region != REGION or handoff.get("campaign_id") != plan.campaign_id:
        raise ValueError("host handoff requires the original fixed Sydney campaign")
    seed = seed_descriptor(handoff["seed"], plan)
    permit = validate_permit(permit, plan, seed, handoff["seed_manifest_sha256"], time.time())
    for key in ("root", "cgroup_root", "host_job_id"):
        if handoff.get(key) != permit["host"].get(key):
            raise ValueError("host handoff and execution permit differ")
    root = Path(handoff["root"])
    if (not root.is_dir() or any(item.is_symlink() for item in (root, *root.parents))
            or Path(handoff_path).parent != root or Path(permit_path).parent != root):
        raise ValueError("bootstrap-owned host directory required")
    name = (__package__ + ".cloud_runtime") if __package__ else "cloud_runtime"
    runtime = sys.modules.get("rove4k_cloud_runtime") or importlib.import_module(name)
    runtime = runtime.canonical_provider()
    consumer = getattr(runtime, "run_host_session", None)
    if not callable(consumer):
        raise RuntimeError("actual EC2 host session bridge is unavailable")
    manifest = runtime.load_seed_manifest(root / "seed" / "seed.json", handoff["seed_manifest_sha256"])
    runtime.revalidate_seed(manifest, root / "seed")
    source = root / "seed" / manifest["source_tree"] / "engines" / "experiments" / "strength" / "campaign.py"
    if Path(__file__).resolve() != source.resolve():
        raise ValueError("host consumer was not imported from the sealed source tree")
    client = aws.AWSCLI(plan.region)
    publisher = aws.S3Evidence(client, plan, root)
    branch = handoff["journal"]
    if (type(branch.get("bytes")) is not int or not 0 < branch["bytes"] <= 128 << 20
            or type(branch.get("rows")) is not int or branch["rows"] < 1
            or not SHA.fullmatch(branch.get("last_sha256", ""))):
        raise ValueError("bounded exact journal handoff required")
    raw = publisher.read_verified(branch["object_key"], expected_sha=branch["sha256"], max_bytes=branch["bytes"])
    if len(raw) != branch["bytes"]:
        raise ValueError("host journal handoff size differs")
    journal_path = root / "host.jsonl"
    with journal_path.open("xb") as output:
        output.write(raw); output.flush(); os.fsync(output.fileno())
    rows = ledger.read_journal(journal_path, plan.campaign_id)
    if len(rows) != branch["rows"] or rows[-1]["sha256"] != branch["last_sha256"]:
        raise ValueError("host journal branch identity differs")
    state = budget.CampaignBudget.replay(plan.campaign_id, rows)
    aws.verify_owned_lease(client, plan, state, time.time(), caller_kind="instance")
    return consumer(handoff, permit, client, publisher, journal_path=journal_path)


class CampaignController:
    def __init__(self, plan, journal, client, publisher, ssm, bridge, *, seed,
                 manifest, manifest_sha256, clock=time.time, monotonic=time.monotonic, sleep=time.sleep,
                 poll_seconds=5, cleanup_seconds=240):
        if plan.region != REGION or plan.project_region != REGION:
            raise ValueError("this campaign requires explicitly bound Sydney workload resources")
        if journal.campaign != plan.campaign_id:
            raise ValueError("campaign journal and AWS plan differ")
        if (type(poll_seconds) not in (int, float) or not math.isfinite(poll_seconds) or not 0 < poll_seconds <= 30
                or type(cleanup_seconds) not in (int, float) or not math.isfinite(cleanup_seconds)
                or not 0 < cleanup_seconds <= 240):
            raise ValueError("finite polling and termination observation budgets required")
        self.plan, self.journal, self.client = plan, journal, client
        self.publisher, self.ssm, self.bridge = publisher, ssm, bridge
        self.seed, self.manifest = seed_descriptor(seed, plan), object_dict(manifest)
        self.manifest_sha256 = manifest_sha256
        self.clock, self.monotonic, self.sleep = clock, monotonic, sleep
        self.poll_seconds, self.cleanup_seconds = poll_seconds, cleanup_seconds
        self.state = budget.CampaignBudget.replay(plan.campaign_id, journal.rows)
        if any(row["event"] == "campaign.host_history_unresolved" for row in journal.rows):
            raise ValueError("unresolved original host history must be recovered before another campaign run")
        self.host_owns_journal = False
        self.control_receipts = []

    def control(self, event, data):
        """After handoff, the host owns the journal branch until it is merged.

        SSM request receipts remain fsynced independently. A crashed controller
        cannot mistake missing command acknowledgement for permission to resend.
        """
        value = {"event": event, "data": data, "observed_at": self.clock(),
                 "campaign_id": self.plan.campaign_id, "launch_token": self.plan.launch_token}
        raw = ledger.canonical(value)
        path = self.publisher.root / ("controller-" + ledger.digest(value) + ".json")
        with path.open("xb") as output:
            output.write(raw); output.flush(); os.fsync(output.fileno())
        self.control_receipts.append(value)
        return value

    def append(self, event, data):
        text = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat().replace("+00:00", "Z")
        at = budget.timestamp(text)
        candidate = self.state.apply(event, data, at)
        row = self.journal.append(event, data, time_utc=text)
        self.state = candidate
        return row

    def inspect(self):
        return {"campaign_id": self.plan.campaign_id, "plan_sha256": aws.digest(self.plan.as_dict()),
                "seed": self.seed, "seed_manifest_sha256": self.manifest_sha256,
                "budget": self.state.as_dict(self.clock()), "aws_calls_performed": False,
                "paid_launch_performed": False}

    def _bind(self, result):
        instance_id = result.get("instance_id")
        if instance_id is not None:
            self.append("budget.instance_bound", {"launch_token": self.plan.launch_token,
                        "instance_id": instance_id})
        return instance_id

    def _recover(self):
        result = aws.recover_launch(self.client, self.plan)
        self.append("campaign.launch_recovered", result)
        return self._bind(result)

    def _journal_snapshot(self):
        raw = self.journal.path.read_bytes()
        fingerprint = hashlib.sha256(raw).hexdigest()
        target = self.publisher.root / ("controller-journal-" + fingerprint + ".jsonl")
        if target.exists():
            if target.is_symlink() or target.read_bytes() != raw:
                raise ValueError("immutable journal snapshot changed")
        else:
            with target.open("xb") as output:
                output.write(raw); output.flush(); os.fsync(output.fileno())
        key = self.plan.campaign_id + "/controller-journals/" + fingerprint + ".jsonl"
        acknowledgement = self.publisher.publish(target, key)
        if (acknowledgement.get("verified") is not True or acknowledgement.get("sha256") != fingerprint
                or acknowledgement.get("bytes") != len(raw) or acknowledgement.get("object_key") != key):
            raise ValueError("journal handoff lacks a verified exact remote acknowledgement")
        self.control("campaign.journal_published", acknowledgement)
        return {"object_key": key, "sha256": fingerprint, "bytes": len(raw),
                "last_sha256": self.journal.last, "rows": len(self.journal.rows)}

    def _archive_controller(self):
        """Archive exact final local bytes after cleanup; no success from a queue."""
        journal = self._journal_snapshot()
        receipts = []
        for value in self.control_receipts:
            path = self.publisher.root / ("controller-" + ledger.digest(value) + ".json")
            key = self.plan.campaign_id + "/controller-receipts/" + path.name
            ack = self.publisher.publish(path, key)
            if ack.get("verified") is not True or ack.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
                raise ValueError("controller receipt lacks exact remote acknowledgement")
            receipts.append(ack)
        return {"journal": journal, "receipts": receipts, "verified": True}

    def _await_running(self, instance_id, startup_deadline):
        while self.clock() < startup_deadline:
            observation = aws.observe_termination(self.client, self.plan, instance_id)
            state = observation["state"]
            if state == "running":
                return aws.verify_owned_lease(self.client, self.plan, self.state, self.clock())
            if state in ("terminated", "stopped", "stopping", "shutting-down"):
                raise RuntimeError("owned instance cannot run the campaign: " + state)
            self.sleep(self.poll_seconds)
        raise TimeoutError("instance initialization exceeded the remaining campaign window")

    def _await_ssm(self, instance_id, startup_deadline):
        while self.clock() < startup_deadline:
            observation = self.ssm.ready(instance_id)
            if observation["ready"]:
                self.append("campaign.ssm_ready", observation)
                return observation
            self.sleep(min(self.poll_seconds, max(0, startup_deadline - self.clock())))
        raise TimeoutError("SSM registration exceeded the bounded startup window")

    def _cleanup(self, instance_id, command_id=None):
        errors, closed = [], None
        if command_id is not None:
            try:
                self.ssm.cancel(command_id, instance_id)
                self.control("campaign.ssm_cancel_requested", {"command_id": command_id, "instance_id": instance_id})
            except Exception as error:
                errors.append("SSM cancel: " + type(error).__name__)
        try:
            if self.host_owns_journal:
                self.control("budget.terminate_requested", {"launch_token": self.plan.launch_token, "instance_id": instance_id})
            else:
                self.append("budget.terminate_requested", {"launch_token": self.plan.launch_token, "instance_id": instance_id})
        except Exception as error:
            errors.append("termination journal: " + type(error).__name__)
        try:
            aws.terminate(self.client, self.plan, instance_id)
        except Exception as error:
            errors.append("termination request: " + type(error).__name__)
        end = self.monotonic() + self.cleanup_seconds
        while self.monotonic() < end:
            try:
                observation = aws.observe_termination(self.client, self.plan, instance_id)
                if observation.get("observed") is True and observation.get("state") == "terminated":
                    # Physical termination ends the host's ability to append.
                    # Missing host history remains explicit; it is never scored
                    # or erased by the following controller cleanup events.
                    if self.host_owns_journal:
                        self.host_owns_journal = False
                        self.append("campaign.host_history_unresolved", {"instance_id": instance_id})
                    for receipt in self.control_receipts:
                        self.append("campaign.control_receipt", receipt)
                    self.control_receipts.clear()
                    reference = "journal:" + self.append("campaign.termination_observed", observation)["sha256"]
                    self.append("budget.instance_observed", {"launch_token": self.plan.launch_token,
                        "instance_id": instance_id, "state": "terminated", "evidence": reference})
                    closed = aws.close_ownership(self.client, self.plan, instance_id, self.clock(), reference)
                    self.append("campaign.ownership_closed", closed)
                    break
            except Exception as error:
                errors.append("termination observation: " + type(error).__name__)
                break
            self.sleep(min(self.poll_seconds, max(0, end - self.monotonic())))
        return {"instance_id": instance_id, "termination_observed": closed is not None,
                "ownership_closed": closed is not None, "errors": errors,
                "independent_watchdog_required": closed is None}

    def terminate_owned(self):
        """Crash/cancel cleanup needs original ownership, not a fresh game permit."""
        active = self.state.active_instances
        if len(active) != 1 or active[0].launch_token != self.plan.launch_token:
            raise ValueError("the original unresolved campaign slot is required for termination")
        self.host_owns_journal = any(row["event"] == "campaign.ssm_requested" for row in self.journal.rows)
        recovered = aws.recover_launch(self.client, self.plan)  # Never calls RunInstances.
        instance_id = recovered.get("instance_id")
        if self.host_owns_journal:
            if instance_id is not None and instance_id != active[0].instance_id:
                raise ValueError("recovered host identity differs from its original budget binding")
            self.control("campaign.cleanup_recovered", recovered)
        else:
            self.append("campaign.cleanup_recovered", recovered)
            if instance_id is not None:
                self._bind(recovered)
        cleanup = self._cleanup(instance_id) if instance_id is not None else {
            "termination_observed": False, "unresolved_launch": True, "independent_watchdog_required": True}
        if self.host_owns_journal:
            self.control("campaign.cleanup_settled", cleanup)
        else:
            self.append("campaign.cleanup_settled", cleanup)
        archive = self._archive_controller()
        return {"campaign_id": self.plan.campaign_id, "cleanup": cleanup, "controller_archive": archive,
                "complete": cleanup.get("ownership_closed") is True, "paid_launch_request_sent": False,
                "budget": self.state.as_dict(self.clock())}

    def execute(self, permit, advisor):
        permit = validate_permit(permit, self.plan, self.seed, self.manifest_sha256, self.clock())
        # Authority/bootstrap checks must be real consumers. Missing bridges or
        # serialized 'passed' fixtures cannot satisfy this call.
        evidence = self.bridge.validate(plan=self.plan, seed=self.seed, manifest=self.manifest,
            manifest_sha256=self.manifest_sha256, permit=permit, client=self.client, now=self.clock())
        expected = {"verified": True, "plan_sha256": aws.digest(self.plan.as_dict()),
                    "seed_sha256": self.seed["sha256"], "seed_manifest_sha256": self.manifest_sha256,
                    "deployment_receipt_sha256": permit["deployment_receipt_sha256"],
                    "ami_id": self.plan.ami_id}
        if not isinstance(evidence, dict) or any(evidence.get(k) != v for k, v in expected.items()):
            raise ValueError("live deployment/bootstrap authority is not verified for this campaign")
        prior = [item for item in self.state.instances if item.launch_token == self.plan.launch_token]
        if prior and not prior[0].active:
            raise ValueError("original launch token is terminal; no relaunch permitted")
        if not self.state.admit(self.clock(), 0).allowed:
            raise ValueError("campaign budget is draining")
        instance_id, command_id, outcome, failure = None, None, None, None
        cleanup = {"termination_observed": False, "unresolved_launch": False}
        try:
            if prior:
                instance_id = self._recover()  # Read only; never issue RunInstances again.
            else:
                receipt = aws.preflight(self.client, self.plan, advisor, self.clock())
                if receipt.get("allowed") is not True:
                    raise ValueError("fresh AWS admission denied: " + "; ".join(receipt.get("blockers", [])))
                validate_permit(permit, self.plan, self.seed, self.manifest_sha256, self.clock())
                self.append("campaign.preflight", receipt)
                self.append("budget.launch_requested", {"launch_token": self.plan.launch_token,
                            "max_hourly_usd": self.plan.max_hourly_usd})
                try:
                    instance_id = self._bind(aws.launch(self.client, self.plan, self.state, receipt, self.clock()))
                except Exception:
                    # Persist failure before observation, but preserve the
                    # original exception if recovery itself is unavailable.
                    self.append("campaign.launch_uncertain", {"launch_token": self.plan.launch_token})
                    instance_id = self._recover()
                    raise
            if instance_id is None:
                raise RuntimeError("original launch remains unresolved; no replacement request is permitted")
            startup_deadline = min(self.clock() + 180, permit["expires_at"] - 30,
                self.plan.deadline_epoch - 60, self.state.deadline(self.clock()) - 60)
            self._await_running(instance_id, startup_deadline)
            self._await_ssm(instance_id, startup_deadline)
            validate_permit(permit, self.plan, self.seed, self.manifest_sha256, self.clock())
            previous_ssm = [row for row in self.journal.rows if row["event"] == "campaign.ssm_requested"]
            marker = self.publisher.root / ("controller-handoff-" + self.plan.launch_token + ".json")
            if previous_ssm or marker.exists():
                raise RuntimeError("prior host command may have run; reconcile host evidence before another command")
            self.append("campaign.ssm_requested", {"instance_id": instance_id,
                        "host_job_id": permit["host"]["host_job_id"]})
            journal = self._journal_snapshot()
            host = permit["host"]
            handoff = {"format": "rove4k-cloud-handoff-v1", "campaign_id": self.plan.campaign_id,
                "aws_plan": self.plan.as_dict(), "journal": journal, "seed": self.seed,
                "seed_manifest_sha256": self.manifest_sha256, **host}
            command = bootstrap_command(handoff, permit, self.manifest)
            seconds = int(min(self.plan.deadline_epoch, self.state.deadline(self.clock())) - self.clock() - 30)
            if seconds < 30:
                raise TimeoutError("no bounded host execution interval remains")
            request_receipt = {"instance_id": instance_id, "host_job_id": host["host_job_id"],
                "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
                "handoff_sha256": ledger.digest(handoff), "permit_sha256": ledger.digest(permit)}
            with marker.open("xb") as output:
                output.write(ledger.canonical(request_receipt)); output.flush(); os.fsync(output.fileno())
            self.host_owns_journal = True
            self.control("campaign.ssm_send_started", request_receipt)
            command_id = self.ssm.send(self.plan, instance_id, command, host["host_job_id"], seconds)
            self.control("campaign.ssm_bound", {"command_id": command_id, "instance_id": instance_id})
            while self.clock() + 30 < min(self.plan.deadline_epoch, self.state.deadline(self.clock())):
                observation = self.ssm.observe(command_id, instance_id)
                if observation["status"] in TERMINAL:
                    self.control("campaign.ssm_terminal", observation)
                    if observation["status"] != "Success" or observation.get("response_code") != 0:
                        raise RuntimeError("host command failed: " + observation["status"])
                    collected = self.bridge.collect(plan=self.plan, handoff=handoff, publisher=self.publisher)
                    if not isinstance(collected, dict) or not isinstance(collected.get("terminal"), dict):
                        raise ValueError("host results have not been remotely verified")
                    outcome = collected["terminal"]
                    merge_host_rows(self.journal, handoff, collected.get("rows"))
                    # The collector imports original host journal rows (same
                    # chain prefix), never re-dates pair events on receipt.
                    self.state = budget.CampaignBudget.replay(self.plan.campaign_id, self.journal.rows)
                    self.host_owns_journal = False
                    for receipt in self.control_receipts:
                        self.append("campaign.control_receipt", receipt)
                    self.control_receipts.clear()
                    remote_journal = outcome.get("journal", {})
                    if not isinstance(remote_journal, dict):
                        raise ValueError("terminal journal descriptor differs")
                    summary = {"host_job_id": host["host_job_id"], "complete": outcome.get("complete"),
                        "terminal_sha256": ledger.digest(outcome),
                        "journal": {key: remote_journal[key] for key in
                                    ("object_key", "sha256", "bytes", "last_sha256", "rows") if key in remote_journal},
                        "stagecount": len(outcome.get("stages", [])),
                        "failure_sha256": ledger.digest(outcome.get("failure"))}
                    if len(ledger.canonical(summary)) > 16 << 10:
                        raise ValueError("terminal identity summary exceeds its bound")
                    self.append("campaign.host_collected", summary)
                    if outcome.get("complete") is not True:
                        raise RuntimeError("host session retained incomplete qualification/results")
                    break
                self.sleep(self.poll_seconds)
            else:
                raise TimeoutError("campaign drained before host completion")
        except BaseException as error:
            failure = error
        finally:
            if instance_id is not None:
                cleanup = self._cleanup(instance_id, command_id)
            elif any(item.launch_token == self.plan.launch_token for item in self.state.active_instances):
                cleanup = {"termination_observed": False, "unresolved_launch": True,
                           "independent_watchdog_required": True}
            settlement = {"cleanup": cleanup, "failure_type": type(failure).__name__ if failure else None}
            if self.host_owns_journal:
                self.control("campaign.controller_settled", settlement)
            else:
                self.append("campaign.controller_settled", settlement)
        archive = None
        try:
            archive = self._archive_controller()
        except Exception as error:
            if failure is None:
                failure = error
        report = {"campaign_id": self.plan.campaign_id, "complete": failure is None and cleanup.get("ownership_closed") is True,
                  "outcome": outcome, "cleanup": cleanup, "failure_type": type(failure).__name__ if failure else None,
                  "budget": self.state.as_dict(self.clock()), "controller_archive": archive}
        if isinstance(failure, (KeyboardInterrupt, SystemExit)):
            raise failure
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("inspect", "execute", "terminate"), default="inspect")
    parser.add_argument("--aws-plan", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--seed-manifest", type=Path, required=True)
    parser.add_argument("--seed-manifest-sha256", required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--permit", type=Path)
    parser.add_argument("--permit-sha256")
    args = parser.parse_args(argv)
    try:
        plan = aws.AWSPlan.from_dict(sealed_json(args.aws_plan)[0])
        seed = sealed_json(args.seed)[0]
        manifest, _ = sealed_json(args.seed_manifest, args.seed_manifest_sha256)
        if args.action == "inspect":
            rows = ledger.read_journal(args.journal, plan.campaign_id) if args.journal.exists() else []
            result = {"plan": plan.as_dict(), "seed": seed_descriptor(seed, plan),
                      "seed_manifest_sha256": args.seed_manifest_sha256,
                      "budget": budget.CampaignBudget.replay(plan.campaign_id, rows).as_dict(time.time()),
                      "aws_calls_performed": False, "paid_launch_performed": False}
        else:
            if args.action == "execute" and (args.permit is None or args.permit_sha256 is None):
                raise ValueError("explicit sealed fresh execution permit required")
            permit = sealed_json(args.permit, args.permit_sha256)[0] if args.action == "execute" else None
            # Resolve the actual bridge before any client/authentication or paid action.
            bridge = CloudRuntimeBridge() if args.action == "execute" else None
            client = aws.AWSCLI(plan.region)
            args.out.mkdir(parents=True, exist_ok=True)
            publisher = aws.S3Evidence(client, plan, args.out)
            ssm = SSMCommands(client)
            with ledger.Journal(args.journal, plan.campaign_id) as journal:
                controller = CampaignController(plan, journal, client, publisher, ssm, bridge,
                    seed=seed, manifest=manifest, manifest_sha256=args.seed_manifest_sha256)
                result = (controller.terminate_owned() if args.action == "terminate" else
                          controller.execute(permit, aws.fetch_advisor(plan.region)))
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0 if args.action == "inspect" or result["complete"] else 2
    except Exception as error:
        print(json.dumps({"complete": False, "error_type": type(error).__name__,
                          "error": str(error)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
