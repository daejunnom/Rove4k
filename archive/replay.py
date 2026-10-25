#!/usr/bin/env python3
"""Export the preserved engine snapshot at its original repository paths.

This reads local Git objects only. It does not build or execute the exported
engines, fetch missing history, or adopt historical measurements.
"""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def git(repo, *args, **kwargs):
    environment = kwargs.pop("env", None)
    environment = dict(os.environ if environment is None else environment)
    # The declared object IDs, not replacement refs or promisor remotes, own
    # the replay. The empty protocol allow-list fails closed on older Git builds
    # that do not understand GIT_NO_LAZY_FETCH; no transport may fill a gap.
    environment.update(GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
                       GIT_ALLOW_PROTOCOL="")
    result = subprocess.run(["git", "-C", str(repo), *args], stderr=subprocess.PIPE,
                            check=False, env=environment, **kwargs)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip())
    return result


def export_snapshot(repo, commit, destination):
    """Materialize exact tracked blobs and modes, independent of today's tree."""
    repo, destination = Path(repo).resolve(), Path(destination)
    if not destination.is_absolute():
        raise ValueError("a new absolute output outside Git checkouts is required")
    if destination.exists() or destination.is_symlink():
        raise ValueError("output already exists; preserve earlier replay evidence")
    destination = destination.resolve()
    if (destination == repo or repo in destination.parents or
            any((path / ".git").exists() for path in (destination, *destination.parents))):
        raise ValueError("replay output must be outside Git checkouts")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("an exact source commit object is required")
    resolved = git(repo, "rev-parse", "--verify", commit + "^{commit}",
                   stdout=subprocess.PIPE).stdout.decode().strip()
    if resolved != commit:
        raise ValueError("source object is not the declared commit")
    raw_tree = git(repo, "ls-tree", "-r", "-z", commit, stdout=subprocess.PIPE).stdout
    entries = []
    for raw in raw_tree.split(b"\0"):
        if not raw:
            continue
        info, raw_name = raw.split(b"\t", 1)
        mode, kind, oid = info.decode().split()
        name = PurePosixPath(raw_name.decode())
        if (kind != "blob" or mode not in ("100644", "100755") or name.is_absolute()
                or any(part in ("..", ".git") for part in name.parts)
                or str(name) == "archive-replay.json"):
            raise ValueError("unsupported source tree entry: " + str(name))
        entries.append((str(name), mode, oid))

    # Read objects, not `git archive`: export-subst/export-ignore attributes must
    # not alter or omit any historical source byte. No mutable worktree is read.
    with tempfile.TemporaryFile() as blobs:
        git(repo, "cat-file", "--batch", input="".join(oid + "\n" for _, _, oid in entries).encode(),
            stdout=blobs)
        blobs.seek(0)
        contents = []
        for name, mode, oid in entries:
            header = blobs.readline().decode().split()
            if len(header) != 3 or header[:2] != [oid, "blob"]:
                raise ValueError("source blob is not available locally: " + name)
            size = int(header[2])
            offset = blobs.tell()
            blobs.seek(size, os.SEEK_CUR)
            if blobs.read(1) != b"\n":
                raise ValueError("incomplete Git blob for " + name)
            contents.append((name, mode, offset, size))
        # Reject a missing local object before creating any replay evidence.
        destination.mkdir(parents=True)
        byte_count = 0
        for name, mode, offset, size in contents:
            blobs.seek(offset)
            data = blobs.read(size)
            if len(data) != size:
                raise ValueError("incomplete Git blob for " + name)
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(0o755 if mode == "100755" else 0o644)
            byte_count += len(data)
    receipt = {"source_commit": commit, "tracked_files": len(entries), "tracked_bytes": byte_count,
               "materialization": "original paths, exact Git blobs and executable modes",
               "builds_or_engines_executed": False}
    (destination / "archive-replay.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    snapshot = json.loads((HERE / "engines/snapshot.json").read_text())
    try:
        receipt = export_snapshot(ROOT, snapshot["source_commit"], args.out)
    except (OSError, ValueError) as error:
        parser.error(str(error) + "; the declared source commit must be available locally")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
