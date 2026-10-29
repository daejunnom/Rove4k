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
    from . import peer_ice_structural as ice
    from . import peer_c4ke_edit_structural as edit
    from . import peer_c4ke_slider_loop as slider, peer_c4ke_startpos_loop as startpos
    from . import peer_c4ke_quiet_history as quiet
    from . import peer_c4ke_move_emission as emission, peer_c4ke_phalanx as phalanx
    from . import peer_c4ke_ep_hash as ep
    from .test_peer_p192_exact import sources, share_sources, slot_ray_sources, c4ke_structural_sources, c4ke_phalanx_extra_sources
except ImportError:
    import peer_p192_exact as exact
    import peer_p192_exact_build as build
    import peer_ice_structural as ice
    import peer_c4ke_edit_structural as edit
    import peer_c4ke_slider_loop as slider
    import peer_c4ke_startpos_loop as startpos
    import peer_c4ke_quiet_history as quiet
    import peer_c4ke_move_emission as emission
    import peer_c4ke_phalanx as phalanx
    import peer_c4ke_ep_hash as ep
    from test_peer_p192_exact import sources, share_sources, slot_ray_sources, c4ke_structural_sources, c4ke_phalanx_extra_sources


class ExactProducerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rove4k-peer-exact-producer-")
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)

    def fixture(self, name, *, share=False, slot_ray=False):
        original = {**(slot_ray_sources() if slot_ray else share_sources() if share else sources(name)),
                    "launcher.sh": b'#!/bin/sh\ntail -n +5 "$0"\n# synthetic\n# end\n',
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

    def fake_runner(self, name, original, *, mutate=None, changed_output=False, variant="baseline"):
        outputs = []
        def run(command, snapshot, *, sandbox_home):
            command = list(command)
            self.assertTrue(Path(sandbox_home).is_dir())
            self.assertEqual(Path(sandbox_home).parent, Path(snapshot).parent)
            if command[-1] == "tcec":
                selected = {path: original[path] for path in exact.source_closure(name, variant=variant)}
                transformed, proof = exact.transform(name, selected, variant=variant)
                self.assertEqual(exact.restore(name, transformed, proof, variant=variant), selected)
                for relative, data in original.items():
                    self.assertEqual((Path(snapshot) / relative).read_bytes(), transformed.get(relative, data))
                outputs.append(1)
                if mutate:
                    mutate(Path(snapshot), len(outputs))
                suffix = str(len(outputs)).encode() if changed_output else b"stable"
                return b"#include <stdint.h>\n/* synthetic " + suffix + b" */\n", b"", {"fixture": "emit"}
            return b"fixture version\n", b"", {"fixture": "tool"}
        return run, outputs

    def test_c4ke_shared_source_and_trimmed_launcher_are_independent_variants(self):
        name = "c4ke"
        source, original = self.fixture(name, share=True)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            run, _ = self.fake_runner(name, original, variant="share-v1")
            result = build.build(name, source, self.root / "share-original", run=run, variant="share-v1")
            run, _ = self.fake_runner(name, original, variant="share-v1")
            trimmed = build.build(name, source, self.root / "share-trimmed", run=run,
                                  variant="share-v1", launcher_variant="gnu-tail-v1")
        first, second = result["record"], trimmed["record"]
        self.assertEqual(first["source_variant"], "share-v1")
        self.assertEqual(second["launcher_variant"], "gnu-tail-v1")
        self.assertEqual(second["whole"]["bytes"], first["whole"]["bytes"] - 3)
        self.assertFalse(second["qualification"]["runtime_qualified"])

    def test_c4ke_structural_variants_run_through_producer(self):
        name = "c4ke"
        source, original = self.fixture(name, slot_ray=True)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            for variant in ("slot-v1", "ray-v1", "slot-ray-v1"):
                with self.subTest(variant=variant):
                    run, attempts = self.fake_runner(name, original, variant=variant)
                    record = build.build(name, source, self.root / variant, run=run,
                                         variant=variant, launcher_variant="gnu-tail-v1")["record"]
                    self.assertEqual(len(attempts), 2)
                    self.assertEqual(record["source_variant"], variant)
                    self.assertEqual(record["resources"]["tt_bytes"], 192 << 30)
                    self.assertFalse(record["qualification"]["runtime_qualified"])
                    self.assertFalse(record["qualification"]["league_qualified"])

    def test_ice_structural_variants_run_through_producer(self):
        name = "ice4"
        original = sources(name)
        for path, edits in ice.edit_specs("castle-zobrist-v1").items():
            original[path] = original.get(path, b"synthetic context\n") + b"\n".join(e[1] for e in edits)
        original.update({"launcher.sh": b'#!/bin/sh\ntail -n +5 "$0"\n# synthetic\n# end\n',
                         "LICENSE": b"synthetic license\n", "other.txt": b"unchanged fixture\n"})
        source = self.root / "ice-upstream"
        source.mkdir()
        for relative, data in original.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            for variant in ice.VARIANTS:
                with self.subTest(variant=variant):
                    run, attempts = self.fake_runner(name, original, variant=variant)
                    record = build.build(name, source, self.root / variant, run=run,
                                         variant=variant, launcher_variant="gnu-tail-v1")["record"]
                    self.assertEqual(len(attempts), 2)
                    self.assertEqual(record["source_variant"], variant)
                    self.assertEqual(record["resources"]["tt_bytes"], 192 << 30)
                    self.assertIn("ice_structural_transform", record["producer_inputs"])
                    self.assertFalse(record["qualification"]["runtime_qualified"])
                    self.assertFalse(record["qualification"]["league_qualified"])

    def test_c4ke_castle_variants_run_through_producer(self):
        name = "c4ke"
        original = {**c4ke_structural_sources(),
                    "launcher.sh": b'#!/bin/sh\ntail -n +5 "$0"\n# synthetic\n# end\n',
                    "LICENSE": b"synthetic license\n", "other.txt": b"unchanged fixture\n"}
        source = self.root / "c4ke-castle-upstream"
        source.mkdir()
        for relative, data in original.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            for variant in ("castle-or-v1", "ray-castle-or-v1"):
                with self.subTest(variant=variant):
                    run, attempts = self.fake_runner(name, original, variant=variant)
                    record = build.build(name, source, self.root / variant, run=run,
                                         variant=variant, launcher_variant="gnu-tail-v1")["record"]
                    self.assertEqual(len(attempts), 2)
                    self.assertEqual(record["source_variant"], variant)
                    self.assertEqual(record["resources"]["tt_bytes"], 192 << 30)
                    self.assertIn("c4ke_structural_transform", record["producer_inputs"])
                    self.assertFalse(record["qualification"]["runtime_qualified"])
                    self.assertFalse(record["qualification"]["league_qualified"])

    def test_c4ke_edit_variants_run_through_producer(self):
        name = "c4ke"
        structural = c4ke_structural_sources()
        structural["src/board.cpp"] += edit._EDIT_BEFORE
        original = {**structural,
                    "launcher.sh": b'#!/bin/sh\ntail -n +5 "$0"\n# synthetic\n# end\n',
                    "LICENSE": b"synthetic license\n", "other.txt": b"unchanged fixture\n"}
        source = self.root / "c4ke-edit-upstream"
        source.mkdir()
        for relative, data in original.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            for variant in ("edit-loop-v1", "edit-castle-or-v1", "edit-castle-alloc24-v1"):
                with self.subTest(variant=variant):
                    run, attempts = self.fake_runner(name, original, variant=variant)
                    record = build.build(name, source, self.root / variant, run=run,
                                         variant=variant, launcher_variant="gnu-tail-v1")["record"]
                    self.assertEqual(len(attempts), 2)
                    self.assertEqual(record["source_variant"], variant)
                    self.assertEqual(record["resources"]["tt_bytes"], 192 << 30)
                    self.assertIn("c4ke_edit_structural_transform", record["producer_inputs"])
                    if variant in ("edit-castle-or-v1", "edit-castle-alloc24-v1"):
                        self.assertIn("c4ke_structural_transform", record["producer_inputs"])
                    self.assertFalse(record["qualification"]["runtime_qualified"])
                    self.assertFalse(record["qualification"]["league_qualified"])

    def test_literal_search_reaches_producer_receipt(self):
        name = "c4ke"
        source, original = self.fixture(name)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        real_compress = lzma.compress
        def small_fixture(data, *, format, filters):
            return real_compress(data, format=format, filters=[dict(filters[0], dict_size=65536)])
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}), \
             patch.object(exact.peers.lzma, "compress", side_effect=small_fixture):
            run, attempts = self.fake_runner(name, original)
            record = build.build(name, source, self.root / "literal-out", run=run,
                                 codec_search="literal-v1")["record"]
        self.assertEqual(len(attempts), 2)
        self.assertEqual(record["codec_search"]["name"], "literal-v1")
        self.assertEqual(record["codec_search"]["literal_contexts"], (0, 1, 3, 4))
        for attempt in record["attempts"]:
            self.assertIn(attempt["selected_codec"]["lc"], (0, 1, 3, 4))
        self.assertFalse(record["qualification"]["runtime_qualified"])

    def test_c4ke_loop_compositions_run_through_producer(self):
        name = "c4ke"
        structural = c4ke_structural_sources()
        structural["src/board.cpp"] += edit._EDIT_BEFORE + slider.BEFORE + startpos.PRECONDITION + startpos.BEFORE
        structural["src/chess.cpp"] += b"\r\n".join(startpos.CONSTANTS) + b"\r\n#define BISHOP 2\r\n#define ROOK 3\r\n#define QUEEN 4\r\n"
        structural["src/eval.cpp"] += startpos.LAYOUT
        original = {**structural,
                    "launcher.sh": b'#!/bin/sh\ntail -n +5 "$0"\n# synthetic\n# end\n',
                    "LICENSE": b"synthetic license\n", "other.txt": b"unchanged fixture\n"}
        source = self.root / "c4ke-loop-upstream"
        source.mkdir()
        for relative, data in original.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            for variant in ("edit-castle-slider-v1", "edit-castle-startpos-v1"):
                with self.subTest(variant=variant):
                    run, attempts = self.fake_runner(name, original, variant=variant)
                    record = build.build(name, source, self.root / variant, run=run,
                                         variant=variant, launcher_variant="gnu-tail-v1")["record"]
                    self.assertEqual(len(attempts), 2)
                    self.assertEqual(record["source_variant"], variant)
                    self.assertEqual(record["resources"]["tt_bytes"], 192 << 30)
                    self.assertIn("c4ke_loop_transform", record["producer_inputs"])
                    self.assertFalse(record["qualification"]["runtime_qualified"])
                    self.assertFalse(record["qualification"]["league_qualified"])

    def test_c4ke_quiet_composition_runs_through_producer(self):
        name = "c4ke"
        structural = c4ke_structural_sources()
        structural["src/board.cpp"] += edit._EDIT_BEFORE
        structural["src/search.cpp"] += quiet._SEARCH + quiet._BONUS_BEFORE + quiet._PENALTY_BEFORE
        original = {**structural,
                    "launcher.sh": b'#!/bin/sh\ntail -n +5 "$0"\n# synthetic\n# end\n',
                    "LICENSE": b"synthetic license\n", "other.txt": b"unchanged fixture\n"}
        source = self.root / "c4ke-quiet-upstream"
        source.mkdir()
        for relative, data in original.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        variant = "edit-castle-quiet-v1"
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}):
            run, attempts = self.fake_runner(name, original, variant=variant)
            record = build.build(name, source, self.root / variant, run=run,
                                 variant=variant, launcher_variant="gnu-tail-v1")["record"]
        self.assertEqual(len(attempts), 2)
        self.assertEqual(record["source_variant"], variant)
        self.assertEqual(record["resources"]["tt_bytes"], 192 << 30)
        for key in ("c4ke_quiet_transform", "c4ke_edit_structural_transform", "c4ke_structural_transform"):
            self.assertIn(key, record["producer_inputs"])
        self.assertFalse(record["qualification"]["runtime_qualified"])
        self.assertFalse(record["qualification"]["league_qualified"])

    def test_c4ke_emission_and_phalanx_compositions_run_through_producer(self):
        name = "c4ke"
        structural = c4ke_structural_sources()
        context = phalanx._START + b"\r\nsynthetic pawn context\r\n" + phalanx._BEFORE
        structural["src/board.cpp"] += edit._EDIT_BEFORE + emission.PAWN_BEFORE + emission.PIECE_BEFORE
        structural["src/board.cpp"] += b"\r\n".join(emission.PAWN_CALLS) + context
        structural["src/chess.cpp"] += b"\r\n".join(emission.CONSTANTS) + b"\r\n#define LSB countr_zero\r\n"
        original = {**structural,
                    "launcher.sh": b'#!/bin/sh\ntail -n +5 "$0"\n# synthetic\n# end\n',
                    "LICENSE": b"synthetic license\n", "other.txt": b"unchanged fixture\n"}
        source = self.root / "c4ke-candidate-upstream"
        source.mkdir()
        for relative, data in original.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}), \
             patch.object(phalanx, "_CONTEXT_SHA256", exact.peers.sha(context)):
            for variant in ("edit-castle-emission-v1", "edit-castle-phalanx-v1"):
                with self.subTest(variant=variant):
                    run, attempts = self.fake_runner(name, original, variant=variant)
                    record = build.build(name, source, self.root / variant, run=run,
                                         variant=variant, launcher_variant="gnu-tail-v1")["record"]
                    self.assertEqual(len(attempts), 2)
                    self.assertEqual(record["source_variant"], variant)
                    self.assertEqual(record["resources"]["tt_bytes"], 192 << 30)
                    for key in ("c4ke_candidate_transform", "c4ke_edit_structural_transform", "c4ke_structural_transform"):
                        self.assertIn(key, record["producer_inputs"])
                    self.assertFalse(record["qualification"]["runtime_qualified"])
                    self.assertFalse(record["qualification"]["league_qualified"])

    def test_c4ke_phalanx_extra_compositions_run_through_producer(self):
        name = "c4ke"
        structural, hashes = c4ke_phalanx_extra_sources()
        original = {**structural,
                    "launcher.sh": b'#!/bin/sh\ntail -n +5 "$0"\n# synthetic\n# end\n',
                    "LICENSE": b"synthetic license\n", "other.txt": b"unchanged fixture\n"}
        source = self.root / "c4ke-phalanx-extra-upstream"
        source.mkdir()
        for relative, data in original.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        with patch.dict(exact.peers.SOURCE_BLOBS, {name: blobs}), \
             patch.object(phalanx, "_CONTEXT_SHA256", hashes["phalanx_context"]), \
             patch.object(ep, "_EDIT_SHA", hashes["ep_edit"]), patch.object(ep, "_MAKE_SHA", hashes["ep_make"]):
            for variant in ("edit-castle-phalanx-attack-pawns-v1", "edit-castle-phalanx-ep-hash-v1", "edit-castle-phalanx-pop-lsb-v1"):
                with self.subTest(variant=variant):
                    run, attempts = self.fake_runner(name, original, variant=variant)
                    record = build.build(name, source, self.root / variant, run=run,
                                         variant=variant, launcher_variant="gnu-tail-v1")["record"]
                    self.assertEqual(len(attempts), 2)
                    self.assertEqual(record["source_variant"], variant)
                    self.assertEqual(record["resources"]["tt_bytes"], 192 << 30)
                    for key in ("c4ke_candidate_transform", "c4ke_extra_transform", "c4ke_edit_structural_transform", "c4ke_structural_transform"):
                        self.assertIn(key, record["producer_inputs"])
                    self.assertFalse(record["qualification"]["runtime_qualified"])
                    self.assertFalse(record["qualification"]["league_qualified"])

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
