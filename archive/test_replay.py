"""The archive restores original source, never a mixture with today's tree."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from replay import export_snapshot


class SnapshotReplay(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rove4k-replay-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        # Fixtures own their configuration and objects; never inherit a user's
        # signing, newline, hooks, repository overrides or transport settings.
        environment = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                           GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL="file",
                           GIT_NO_LAZY_FETCH="0")
        for name in tuple(environment):
            if (name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                         "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                         "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT",
                         "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE")
                    or name.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))):
                environment.pop(name)
        isolate = patch.dict(os.environ, environment, clear=True)
        isolate.start()
        self.addCleanup(isolate.stop)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "--object-format=sha1")
        self.git("config", "core.autocrlf", "false")
        self.original = {"engine/source.c": b"int main(void){return 0;}\r\n",
                         "receipt.bin": bytes(range(256)),
                         "producer.py": b"#!/usr/bin/env python3\n# $Format:%H$\n",
                         ".gitattributes": b"producer.py export-subst\nreceipt.bin export-ignore\n"}
        for name, data in self.original.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (self.repo / "producer.py").chmod(0o755)
        self.git("add", ".")
        # Git retains executable modes even where the filesystem cannot.
        self.git("update-index", "--chmod=+x", "producer.py")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "snapshot")
        self.commit = self.git("rev-parse", "HEAD").strip()

    def git(self, *args, **kwargs):
        return subprocess.check_output(["git", "-C", str(self.repo), *args],
                                       text=True, stderr=subprocess.PIPE, **kwargs)

    def missing_promisor_object(self, oid):
        """Remove one loose object only from this newly owned fixture repo."""
        remote = self.root / "local-promisor.git"
        subprocess.run(["git", "clone", "--bare", "--no-hardlinks", str(self.repo), str(remote)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.git("remote", "add", "origin", remote.as_uri())
        self.git("config", "remote.origin.promisor", "true")
        self.git("config", "remote.origin.partialclonefilter", "blob:none")
        for name in ("uploadpack.allowFilter", "uploadpack.allowAnySHA1InWant"):
            subprocess.run(["git", "-C", str(remote), "config", name, "true"], check=True)
        object_path = self.repo / ".git" / "objects" / oid[:2] / oid[2:]
        self.assertTrue(object_path.resolve().is_relative_to(self.repo / ".git" / "objects"))
        self.assertTrue(object_path.is_file())
        self.assertFalse(object_path.is_symlink())
        self.assertEqual(object_path.stat().st_nlink, 1)
        object_path.chmod(0o600)
        object_path.unlink()
        return object_path

    def assert_missing_promisor_is_local_only(self, oid):
        object_path = self.missing_promisor_object(oid)
        trace = self.root / "guarded-trace.json"
        out = self.root / "missing-object-replay"
        # Deliberately permissive caller settings must not override the
        # exporter's local-only contract. The only fixture remote is local.
        with patch.dict(os.environ, GIT_TRACE2_EVENT=str(trace), GIT_ALLOW_PROTOCOL="file",
                        GIT_NO_LAZY_FETCH="0", GIT_NO_REPLACE_OBJECTS=""):
            with self.assertRaises(ValueError):
                export_snapshot(self.repo, self.commit, out)
        events = [json.loads(line) for line in trace.read_text().splitlines()]
        self.assertFalse(any(row.get("event") == "child_start" and "fetch" in row.get("argv", [])
                             for row in events))
        self.assertFalse(object_path.exists())
        self.assertFalse(out.exists())
        # Positive control: this really is a missing promisor object, not an
        # inert config fixture. Unguarded Git restores it from the local remote.
        control_trace = self.root / "control-trace.json"
        with patch.dict(os.environ, GIT_TRACE2_EVENT=str(control_trace)):
            subprocess.run(["git", "-C", str(self.repo), "cat-file", "-p", oid], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        control = [json.loads(line) for line in control_trace.read_text().splitlines()]
        self.assertTrue(any(row.get("event") == "child_start" and "fetch" in row.get("argv", [])
                            for row in control))

    def test_original_paths_bytes_modes_and_provenance_survive_current_edits(self):
        (self.repo / "engine/source.c").write_text("changed current engine\n")
        (self.repo / "receipt.bin").unlink()
        (self.repo / "new-file").write_text("not part of the snapshot\n")
        out = self.root / "replay"
        receipt = export_snapshot(self.repo, self.commit, out)
        for name, data in self.original.items():
            self.assertEqual((out / name).read_bytes(), data)
        if os.name != "nt":
            self.assertTrue((out / "producer.py").stat().st_mode & 0o111)
            self.assertFalse((out / "engine/source.c").stat().st_mode & 0o111)
        self.assertFalse((out / ".git").exists())
        self.assertFalse((out / "new-file").exists())
        self.assertEqual(json.loads((out / "archive-replay.json").read_text()), receipt)
        self.assertEqual(receipt["source_commit"], self.commit)
        self.assertEqual(receipt["tracked_bytes"], sum(map(len, self.original.values())))
        self.assertFalse(receipt["builds_or_engines_executed"])

    def test_preserves_existing_evidence_and_refuses_checkout_output(self):
        out = self.root / "existing"
        out.mkdir()
        marker = out / "failed-attempt"
        marker.write_bytes(b"keep this evidence")
        with self.assertRaisesRegex(ValueError, "already exists"):
            export_snapshot(self.repo, self.commit, out)
        self.assertEqual(marker.read_bytes(), b"keep this evidence")
        with self.assertRaisesRegex(ValueError, "outside Git"):
            export_snapshot(self.repo, self.commit, self.repo / "generated")
        self.assertFalse((self.repo / "generated").exists())
        with self.assertRaisesRegex(ValueError, "absolute"):
            export_snapshot(self.repo, self.commit, Path("relative-output"))

    def test_unavailable_commit_fails_before_output_creation(self):
        out = self.root / "missing-history"
        with self.assertRaises(ValueError):
            export_snapshot(self.repo, "0" * 40, out)
        self.assertFalse(out.exists())

    def test_replacement_commit_cannot_change_declared_snapshot(self):
        (self.repo / "engine/source.c").write_text("replacement commit source\n")
        (self.repo / "replacement-only").write_text("not declared source\n")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", "replacement")
        replacement = self.git("rev-parse", "HEAD").strip()
        self.git("replace", self.commit, replacement)
        self.assertEqual(self.git("show", self.commit + ":engine/source.c"),
                         "replacement commit source\n")
        out = self.root / "original-commit-replay"
        receipt = export_snapshot(self.repo, self.commit, out)
        for name, data in self.original.items():
            self.assertEqual((out / name).read_bytes(), data)
        self.assertFalse((out / "replacement-only").exists())
        self.assertEqual(receipt["source_commit"], self.commit)

    def test_replacement_blob_cannot_change_declared_bytes(self):
        original = self.git("rev-parse", self.commit + ":receipt.bin").strip()
        replacement = self.git("hash-object", "-w", "--stdin", input="replacement blob\n").strip()
        self.git("replace", original, replacement)
        self.assertEqual(self.git("cat-file", "-p", original), "replacement blob\n")
        out = self.root / "original-blob-replay"
        export_snapshot(self.repo, self.commit, out)
        self.assertEqual((out / "receipt.bin").read_bytes(), self.original["receipt.bin"])

    def test_missing_promisor_commit_does_not_fetch(self):
        self.assert_missing_promisor_is_local_only(self.commit)

    def test_missing_promisor_tree_does_not_fetch(self):
        tree = self.git("rev-parse", self.commit + "^{tree}").strip()
        self.assert_missing_promisor_is_local_only(tree)

    def test_missing_promisor_blob_does_not_fetch(self):
        blob = self.git("rev-parse", self.commit + ":receipt.bin").strip()
        self.assert_missing_promisor_is_local_only(blob)


if __name__ == "__main__":
    unittest.main()
