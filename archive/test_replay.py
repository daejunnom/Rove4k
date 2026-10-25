"""The archive restores original source, never a mixture with today's tree."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from replay import export_snapshot


class SnapshotReplay(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rove4k-replay-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
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
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "snapshot")
        self.commit = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True)

    def test_original_paths_bytes_modes_and_provenance_survive_current_edits(self):
        (self.repo / "engine/source.c").write_text("changed current engine\n")
        (self.repo / "receipt.bin").unlink()
        (self.repo / "new-file").write_text("not part of the snapshot\n")
        out = self.root / "replay"
        receipt = export_snapshot(self.repo, self.commit, out)
        for name, data in self.original.items():
            self.assertEqual((out / name).read_bytes(), data)
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


if __name__ == "__main__":
    unittest.main()
