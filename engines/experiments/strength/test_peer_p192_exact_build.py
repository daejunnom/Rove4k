"""Exact P192 peer producer contract with synthetic inputs; no engines run."""
from __future__ import annotations

import json
import lzma
import os
from pathlib import Path
from functools import partial
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import peer_p192_exact as exact, peer_p192_exact_build as build
    from .test_peer_p192_exact import sources
except ImportError:
    import peer_p192_exact as exact
    import peer_p192_exact_build as build
    from test_peer_p192_exact import sources


class ExactProducerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rove4k-peer-exact-producer-")
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)

    def fixture(self, name):
        original = {**sources(name), "launcher.sh": b"#!/bin/sh\n# synthetic wrapper\n",
                    "LICENSE": b"synthetic license\n", "other.txt": b"unchanged fixture\n"}
        root = self.root / (name + "-upstream")
        root.mkdir()
        for relative, data in original.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return root, original

    def test_literal_clues_never_become_a_semantic_claim(self):
        raw = b"p=calloc(3ULL << 33, 8); a[((h >> 16) * 3) >> 15];"
        clues = build._emitted_clues(raw)
        self.assertEqual(clues["explicit_192gib_calloc_literals"], 1)
        self.assertEqual(clues["explicit_upper48_index_suffixes"], 1)
        self.assertIn("not resolved", clues["scope"])
        absent = build._emitted_clues(b"p=calloc(1ULL << 34, 8); a[h >> 30];")
        self.assertEqual(absent["explicit_192gib_calloc_literals"], 0)
        self.assertEqual(absent["explicit_upper48_index_suffixes"], 0)

    def fake_runner(self, name, original, *, mutate=None, changed_output=False):
        outputs = []
        def run(command, snapshot, *, sandbox_home):
            command = list(command)
            self.assertTrue(Path(sandbox_home).is_dir())
            self.assertEqual(Path(sandbox_home).parent, Path(snapshot).parent)
            if command[-1] == "tcec":
                selected = {path: original[path] for path in set(exact._EDITS[name]) |
                            {exact.peers.peer_spec(name).resource_path}}
                transformed, proof = exact.transform(name, selected)
                self.assertEqual(exact.restore(name, transformed, proof), selected)
                for relative, data in original.items():
                    self.assertEqual((Path(snapshot) / relative).read_bytes(), transformed.get(relative, data))
                outputs.append(1)
                if mutate:
                    mutate(Path(snapshot), len(outputs))
                suffix = str(len(outputs)).encode() if changed_output else b"stable"
                return b"#include <stdint.h>\n/* synthetic " + suffix + b" */\n", b"", {"fixture": "emit"}
            return b"fixture version\n", b"", {"fixture": "tool"}
        return run, outputs

    def test_both_peers_produce_two_matching_full_streams_without_qualification(self):
        for name in ("ice4", "c4ke"):
            with self.subTest(peer=name):
                source, original = self.fixture(name)
                blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
                with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
                    run, outputs = self.fake_runner(name, original)
                    result = build.build(name, source, self.root / (name + "-out"), run=run)
                self.assertEqual(len(outputs), 2)
                record = result["record"]
                self.assertTrue(record["complete"] and record["reproducible"])
                self.assertEqual(record["profile"], exact.PROFILE)
                self.assertEqual(record["resources"]["tt_entries"], 3 << 33)
                self.assertEqual(record["resources"]["tt_bytes"], 192 << 30)
                self.assertTrue(record["algorithm_changed"])
                self.assertEqual(record["license"]["spdx"], "GPL-3.0" if name == "ice4" else "MIT")
                self.assertEqual(record["license"]["sha256"], exact.peers.sha(original["LICENSE"]))
                self.assertTrue(record["license"]["distribution_conditions_summary"])
                self.assertIn("upstream license text controls", record["license"]["scope"])
                self.assertFalse(record["qualification"]["emitted_tt_semantics_verified"])
                self.assertFalse(record["qualification"]["runtime_qualified"])
                self.assertFalse(record["qualification"]["league_qualified"])
                self.assertFalse(record["executing_code_identity_verified"])
                self.assertEqual(record["qualification"]["size_within_4096"], record["whole"]["bytes"] <= 4096)
                first, second = record["attempts"]
                whole = Path(first["whole"]["path"]).read_bytes()
                self.assertEqual(whole, Path(second["whole"]["path"]).read_bytes())
                self.assertEqual(len(whole), first["whole"]["bytes"])
                self.assertEqual(lzma.decompress(whole[len(original["launcher.sh"]):], format=lzma.FORMAT_ALONE),
                                 (Path(first["whole"]["path"]).parent / "main.cpp").read_bytes())
                self.assertEqual(first["transform_proof_sha256"], second["transform_proof_sha256"])

    def test_minifier_mutation_and_changed_output_fail_closed_with_receipt(self):
        name = "ice4"
        source, original = self.fixture(name)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        def mutate(snapshot, attempt):
            if attempt == 1:
                (snapshot / "other.txt").write_bytes(b"changed")
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            run, _ = self.fake_runner(name, original, mutate=mutate)
            output = self.root / "mutated"
            with self.assertRaisesRegex(ValueError, "protected peer input"):
                build.build(name, source, output, run=run)
            failed = json.loads((output / "peer-exact.json").read_text(encoding="utf-8"))
            self.assertFalse(failed["complete"])
            self.assertFalse(failed["qualification"]["league_qualified"])
            run, _ = self.fake_runner(name, original, changed_output=True)
            output = self.root / "nonreproducible"
            with self.assertRaisesRegex(ValueError, "reproduction differs"):
                build.build(name, source, output, run=run)
            failed = json.loads((output / "peer-exact.json").read_text(encoding="utf-8"))
            self.assertEqual(len(failed["attempts"]), 2)
            self.assertFalse(failed["complete"])

    def test_original_source_mutation_between_attempts_is_rejected(self):
        name = "c4ke"
        source, original = self.fixture(name)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        def mutate(_snapshot, attempt):
            if attempt == 1:
                (source / "other.txt").write_bytes(b"changed")
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            run, _ = self.fake_runner(name, original, mutate=mutate)
            output = self.root / "source-changed"
            with self.assertRaisesRegex(ValueError, "pinned peer source differs"):
                build.build(name, source, output, run=run)
            failed = json.loads((output / "peer-exact.json").read_text(encoding="utf-8"))
            self.assertEqual(len(failed["attempts"]), 1)
            self.assertFalse(failed["complete"])

    def test_minifier_cannot_modify_retained_proofs_or_previous_attempt(self):
        name = "ice4"
        source, original = self.fixture(name)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            def first(snapshot, attempt):
                if attempt == 1:
                    (snapshot.parent / "transform-proof.json").write_text("{}", encoding="utf-8")
            run, _ = self.fake_runner(name, original, mutate=first)
            output = self.root / "proof-changed"
            with self.assertRaisesRegex(ValueError, "modified the retained transform proof"):
                build.build(name, source, output, run=run)
            self.assertFalse(json.loads((output / "peer-exact.json").read_text())["complete"])
            def second(snapshot, attempt):
                if attempt == 2:
                    (snapshot.parent.parent / "attempt-1" / "transform-proof.json").write_text("{}", encoding="utf-8")
            run, _ = self.fake_runner(name, original, mutate=second)
            output = self.root / "previous-proof-changed"
            with self.assertRaisesRegex(ValueError, "retained attempt evidence changed"):
                build.build(name, source, output, run=run)
            self.assertFalse(json.loads((output / "peer-exact.json").read_text())["complete"])
            def previous_snapshot(snapshot, attempt):
                if attempt == 2:
                    (snapshot.parent.parent / "attempt-1" / "source" / "src" / "board.cpp").write_bytes(b"altered")
            run, _ = self.fake_runner(name, original, mutate=previous_snapshot)
            output = self.root / "previous-source-changed"
            with self.assertRaisesRegex(ValueError, "retained attempt input changed"):
                build.build(name, source, output, run=run)
            self.assertFalse(json.loads((output / "peer-exact.json").read_text())["complete"])

    def test_protected_or_symlinked_sources_are_not_read(self):
        name = "ice4"
        source, original = self.fixture(name)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            protected = self.root / "credentials" / "source"
            with self.assertRaisesRegex(ValueError, "protected path"):
                build.build(name, protected, self.root / "protected-out")
            linked = self.root / "linked-source"
            linked.symlink_to(source, target_is_directory=True)
            with self.assertRaises(OSError):
                build.build(name, linked, self.root / "linked-out")
            outside = self.root / "outside"
            outside.mkdir()
            for item in (source / "src").iterdir():
                item.rename(outside / item.name)
            (source / "src").rmdir()
            (source / "src").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(OSError):
                build.build(name, source, self.root / "nested-linked-out")
        self.assertFalse((self.root / "protected-out").exists())
        self.assertFalse((self.root / "linked-out").exists())
        self.assertFalse((self.root / "nested-linked-out").exists())

    def test_output_cannot_be_nested_in_the_source(self):
        name = "ice4"
        source, original = self.fixture(name)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            with self.assertRaisesRegex(ValueError, "separate directories"):
                build.build(name, source, source / "out")
            protected_parent = self.root / "credentials"
            protected_parent.mkdir()
            alias = self.root / "alias"
            alias.symlink_to(protected_parent, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "protected path"):
                build.build(name, source, alias / "out")
        self.assertFalse((source / "out").exists())
        self.assertFalse((protected_parent / "out").exists())

    def test_minifier_cannot_replace_output_or_next_attempt_with_symlink(self):
        name = "ice4"
        source, original = self.fixture(name)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        target = self.root / "sentinel.txt"
        target.write_bytes(b"unchanged")
        outside = self.root / "outside"
        outside.mkdir()
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            def replace_file(snapshot, attempt):
                if attempt == 1:
                    (snapshot.parent / "main.cpp").symlink_to(target)
            run, _ = self.fake_runner(name, original, mutate=replace_file)
            output = self.root / "link-output"
            with self.assertRaises(FileExistsError):
                build.build(name, source, output, run=run)
            self.assertEqual(target.read_bytes(), b"unchanged")
            def replace_directory(snapshot, attempt):
                if attempt == 1:
                    (snapshot.parent.parent / "attempt-2").symlink_to(outside, target_is_directory=True)
            run, _ = self.fake_runner(name, original, mutate=replace_directory)
            output = self.root / "link-attempt"
            with self.assertRaises(FileExistsError):
                build.build(name, source, output, run=run)
            self.assertFalse((outside / "source").exists())

    @unittest.skipUnless(sys.platform == "linux" and hasattr(os, "sched_getaffinity"), "Linux owned subprocess required")
    def test_real_bounded_toy_processes_connect_to_producer(self):
        name = "ice4"
        source, original = self.fixture(name)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        def commands(_name, _snapshot, _attempt):
            return ([[sys.executable, "-c", "pass"]],
                    [sys.executable, "-c", "print('#include <stdint.h>\\n/* toy */')"])
        cpu = min(os.sched_getaffinity(0))
        owned_run = partial(build.runner.run, cpu=cpu, timeout=15, memory_bytes=512 << 20)
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}), patch.object(exact.peers, "minifier_commands", commands):
            result = build.build(name, source, self.root / "actual-toy", run=owned_run)
        self.assertTrue(result["record"]["complete"])
        self.assertFalse(result["record"]["qualification"]["league_qualified"])
        for attempt in result["record"]["attempts"]:
            self.assertTrue(all(row["leader_reaped"] and row["group_absent"] for row in attempt["commands"]))


if __name__ == "__main__":
    unittest.main()
