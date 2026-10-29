"""Experimental exact producer reinspection; no peer or large TT runs."""
import ast
import hashlib
import json
import lzma
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import peer_exact_proposal as proposal, peer_p192_exact as exact
    from . import peer_p192_exact_build as build, registry, seed
    from .test_peer_p192_exact import sources, c4ke_structural_sources, c4ke_phalanx_extra_sources
except ImportError:
    import peer_exact_proposal as proposal
    import peer_p192_exact as exact
    import peer_p192_exact_build as build
    import registry
    import seed
    from test_peer_p192_exact import sources, c4ke_structural_sources, c4ke_phalanx_extra_sources


class LegacySeedTests(unittest.TestCase):
    def test_lazy_proposal_api_adds_no_named_seed_dependencies(self):
        raw = Path(registry.__file__).read_text(encoding="utf-8")
        tree = ast.parse(raw)
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == "inspect_exact_peer_proposal")
        lines = raw.splitlines(keepends=True)
        old = "".join(lines[:function.lineno - 1] + lines[function.end_lineno:])
        source_name = "engines/experiments/strength/registry.py"
        for league_required in (False, True):
            self.assertEqual(seed.named_python_dependencies(raw, source_name=source_name,
                                                            league_required=league_required),
                             seed.named_python_dependencies(old, source_name=source_name,
                                                            league_required=league_required))


@unittest.skipUnless(sys.platform == "linux", "Linux no-follow source snapshots required")
class CandidateProposalTests(unittest.TestCase):
    def test_phalanx_extra_producer_tools_are_exact_and_pinned(self):
        original, hashes = c4ke_phalanx_extra_sources()
        original.update({"launcher.sh": b'#!/bin/sh\ntail -n +5 "$0"\n# synthetic\n# end\n',
                         "LICENSE": b"synthetic license\n", "other.txt": b"fixture\n"})
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        phalanx, ep = exact.peer_c4ke_phalanx, exact.peer_c4ke_ep_hash
        real_compress = lzma.compress

        def tiny_compress(data, *, format, filters):
            return real_compress(data, format=format, filters=[dict(filters[0], dict_size=65536)])

        def fake(command, snapshot, *, sandbox_home):
            if command[-1] == "tcec":
                return b"#include <stdint.h>\n/* fixture: no TT */\n", b"", {"fixture": "emit"}
            return b"fixture version\n", b"", {"fixture": "tool"}

        with tempfile.TemporaryDirectory(prefix="rove-peer-extra-proposal-") as directory, \
             patch.dict(exact.peers.SOURCE_BLOBS, {"c4ke": blobs}), \
             patch.object(phalanx, "_CONTEXT_SHA256", hashes["phalanx_context"]), \
             patch.object(ep, "_EDIT_SHA", hashes["ep_edit"]), patch.object(ep, "_MAKE_SHA", hashes["ep_make"]), \
             patch.object(exact.peers.lzma, "compress", side_effect=tiny_compress):
            root = Path(directory).resolve()
            source = root / "source"
            source.mkdir()
            for path, raw in original.items():
                target = source / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            variants = ("edit-castle-phalanx-attack-pawns-v1", "edit-castle-phalanx-ep-hash-v1",
                        "edit-castle-phalanx-pop-lsb-v1")
            for variant in variants:
                with self.subTest(variant=variant):
                    produced = build.build("c4ke", source, root / variant, run=fake, variant=variant,
                                           launcher_variant="gnu-tail-v1")
                    receipt = Path(produced["path"])
                    record = json.loads(receipt.read_bytes())
                    result = registry.inspect_exact_peer_proposal(receipt, produced["sha256"])
                    self.assertTrue(result["source_snapshot_inverse_verified"])
                    self.assertFalse(result["eligible_for_diagnostic"])
                    self.assertFalse(result["eligible_for_scored_league"])
                    self.assertEqual(set(record["producer_inputs"]), {
                        "producer", "transform", "peer_base", "command_runner", "launcher_transform",
                        "c4ke_structural_transform", "c4ke_edit_structural_transform",
                        "c4ke_candidate_transform", "c4ke_extra_transform"})
                    original_receipt = receipt.read_bytes()
                    for operation in ("missing", "extra"):
                        changed = json.loads(original_receipt)
                        if operation == "missing":
                            del changed["producer_inputs"]["c4ke_extra_transform"]
                        else:
                            changed["producer_inputs"]["unexpected"] = changed["producer_inputs"]["producer"]
                        modified = json.dumps(changed).encode()
                        receipt.write_bytes(modified)
                        with self.assertRaisesRegex(ValueError, "producer tool set differs"):
                            registry.inspect_exact_peer_proposal(receipt, hashlib.sha256(modified).hexdigest())
                    receipt.write_bytes(original_receipt)
                    snapshot = receipt.parent / "c4ke_extra_transform.py"
                    raw = snapshot.read_bytes()
                    snapshot.write_bytes(raw + b"# tampered\n")
                    with self.assertRaises(ValueError):
                        registry.inspect_exact_peer_proposal(receipt, produced["sha256"])
                    snapshot.write_bytes(raw)
                    # A self-consistent descriptor for the wrong module must also fail.
                    wrong = Path(phalanx.__file__).read_bytes()
                    snapshot.write_bytes(wrong)
                    changed = json.loads(receipt.read_bytes())
                    changed["producer_inputs"]["c4ke_extra_transform"] = {
                        "bytes": len(wrong), "sha256": hashlib.sha256(wrong).hexdigest()}
                    modified = json.dumps(changed).encode()
                    receipt.write_bytes(modified)
                    with self.assertRaisesRegex(ValueError, "producer snapshot differs"):
                        registry.inspect_exact_peer_proposal(receipt, hashlib.sha256(modified).hexdigest())

    def test_emission_and_phalanx_producer_tools_are_exact_and_pinned(self):
        emission = exact.peer_c4ke_move_emission
        phalanx = exact.peer_c4ke_phalanx
        edit = exact.peer_c4ke_edit_structural
        original = c4ke_structural_sources()
        context = phalanx._START + b"\r\nsynthetic pawn context\r\n" + phalanx._BEFORE
        original["src/board.cpp"] += edit._EDIT_BEFORE + emission.PAWN_BEFORE + emission.PIECE_BEFORE
        original["src/board.cpp"] += b"\r\n".join(emission.PAWN_CALLS) + context
        original["src/chess.cpp"] += b"\r\n".join(emission.CONSTANTS) + b"\r\n#define LSB countr_zero\r\n"
        original.update({"launcher.sh": b'#!/bin/sh\ntail -n +5 "$0"\n# synthetic\n# end\n',
                         "LICENSE": b"synthetic license\n", "other.txt": b"fixture\n"})
        blobs = {path: exact.peers.git_blob(data) for path, data in original.items()}
        def fake(command, snapshot, *, sandbox_home):
            if command[-1] == "tcec":
                return b"#include <stdint.h>\n/* fixture: no TT */\n", b"", {"fixture": "emit"}
            return b"fixture version\n", b"", {"fixture": "tool"}
        with tempfile.TemporaryDirectory(prefix="rove-peer-candidate-proposal-") as directory, \
             patch.dict(exact.peers.SOURCE_BLOBS, {"c4ke": blobs}), \
             patch.object(phalanx, "_CONTEXT_SHA256", exact.peers.sha(context)):
            root = Path(directory).resolve()
            source = root / "source"
            source.mkdir()
            for path, raw in original.items():
                target = source / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            for variant in ("edit-castle-emission-v1", "edit-castle-phalanx-v1"):
                with self.subTest(variant=variant):
                    produced = build.build("c4ke", source, root / variant, run=fake, variant=variant,
                                           launcher_variant="gnu-tail-v1")
                    receipt = Path(produced["path"])
                    result = registry.inspect_exact_peer_proposal(receipt, produced["sha256"])
                    self.assertFalse(result["eligible_for_diagnostic"])
                    self.assertFalse(result["emitted_tt_semantics_verified"])
                    record = json.loads(receipt.read_bytes())
                    original_receipt = receipt.read_bytes()
                    tools = record["producer_inputs"]
                    expected = {"producer", "transform", "peer_base", "command_runner", "launcher_transform",
                                "c4ke_structural_transform", "c4ke_edit_structural_transform",
                                "c4ke_candidate_transform"}
                    self.assertEqual(set(tools), expected)
                    for key in ("c4ke_structural_transform", "c4ke_edit_structural_transform",
                                "c4ke_candidate_transform"):
                        snapshot = receipt.parent / (key + ".py")
                        raw = snapshot.read_bytes()
                        snapshot.write_bytes(raw + b"# tampered\n")
                        with self.assertRaises(ValueError):
                            registry.inspect_exact_peer_proposal(receipt, produced["sha256"])
                        snapshot.write_bytes(raw)
                    for operation in ("missing", "extra", "wrong_candidate"):
                        changed = json.loads(receipt.read_bytes())
                        candidate = receipt.parent / "c4ke_candidate_transform.py"
                        candidate_raw = candidate.read_bytes()
                        if operation == "missing":
                            del changed["producer_inputs"]["c4ke_candidate_transform"]
                        elif operation == "extra":
                            changed["producer_inputs"]["unexpected"] = changed["producer_inputs"]["producer"]
                        else:
                            wrong = phalanx if variant == "edit-castle-emission-v1" else emission
                            data = Path(wrong.__file__).read_bytes()
                            candidate.write_bytes(data)
                            changed["producer_inputs"]["c4ke_candidate_transform"] = {
                                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                        modified = json.dumps(changed).encode()
                        receipt.write_bytes(modified)
                        with self.assertRaises(ValueError):
                            registry.inspect_exact_peer_proposal(receipt, hashlib.sha256(modified).hexdigest())
                        candidate.write_bytes(candidate_raw)
                        receipt.write_bytes(original_receipt)


@unittest.skipUnless(sys.platform == "linux", "Linux no-follow source snapshots required")
class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rove-peer-proposal-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.peer = "c4ke"
        self.original = {**sources(self.peer), "launcher.sh": b"#!/bin/sh\ntail -n +5 \"$0\"\n# synthetic\n# end\n",
                         "LICENSE": b"synthetic license\n", "other.txt": b"unchanged fixture\n"}
        source = self.root / "upstream"
        source.mkdir()
        for relative, data in self.original.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.blobs = {name: exact.peers.git_blob(data) for name, data in self.original.items()}
        self.blob_patch = patch.dict(exact.peers.SOURCE_BLOBS, {self.peer: self.blobs})
        self.blob_patch.start()
        self.addCleanup(self.blob_patch.stop)

        def fake(command, snapshot, *, sandbox_home):
            if command[-1] == "tcec":
                return b"#include <stdint.h>\n/* fixture: no TT */\n", b"", {"fixture": "emit"}
            return b"fixture version\n", b"", {"fixture": "tool"}

        result = build.build(self.peer, source, self.root / "output", run=fake)
        self.record = Path(result["path"])
        self.digest = result["sha256"]

    def inspect(self):
        return registry.inspect_exact_peer_proposal(self.record, self.digest)

    def test_actual_producer_files_replayed_without_admission(self):
        result = self.inspect()
        self.assertEqual(result["layout"], "peer-p192-exact-3x2p33-v1")
        self.assertEqual(result["resources"]["tt_entries"], 3 << 33)
        self.assertEqual(result["resources"]["tt_bytes"], 192 << 30)
        self.assertTrue(result["source_snapshot_inverse_verified"])
        self.assertTrue(result["retained_source_whole_consistent"])
        for field in ("minifier_execution_replayed", "emitted_tt_semantics_verified", "native_reference_verified",
                      "eligible_for_diagnostic", "eligible_for_scored_league"):
            self.assertIs(result[field], False)
        # The minifier fixture emitted no TT at all. A producer success flag or
        # exact byte count therefore cannot qualify it for an Artifact.
        with self.assertRaises((KeyError, TypeError, ValueError)):
            registry.Artifact.from_record(result)

    def test_receipt_or_snapshot_replacement_rejected(self):
        for relative in ("attempt-1/main.cpp", "attempt-2/transform-proof.json",
                         "attempt-1/source/src/board.cpp", "transform.py"):
            with self.subTest(relative=relative):
                path = self.record.parent / relative
                old = path.read_bytes()
                path.write_bytes(old + b"changed")
                with self.assertRaises(ValueError):
                    self.inspect()
                path.write_bytes(old)
        with self.assertRaisesRegex(ValueError, "receipt identity"):
            registry.inspect_exact_peer_proposal(self.record, "0" * 64)

    def test_fabricated_resource_or_semantics_claim_rejected(self):
        original = self.record.read_bytes()
        for mutate in (lambda r: r["resources"].update(tt_entries=1 << 34),
                       lambda r: r["resources"].update(tt_entries=float(3 << 33)),
                       lambda r: r["qualification"].update(emitted_tt_semantics_verified=True),
                       lambda r: r["attempts"].pop()):
            with self.subTest(mutation=mutate):
                record = json.loads(original)
                mutate(record)
                self.record.write_text(json.dumps(record), encoding="utf-8")
                self.digest = hashlib.sha256(self.record.read_bytes()).hexdigest()
                with self.assertRaises(ValueError):
                    self.inspect()
        self.record.write_bytes(original)

    def test_exact_layout_does_not_replace_legacy_artifact_contract(self):
        record = {"id": "peer", "family": "c4ke", "path": self.record.parent / "attempt-1" / "c4ke",
                  "purpose": "test", "profile": "test-p192", "workers": 192,
                  "tt_bytes": 192 << 30, "entry_bytes": 8, "representation": "source-jit",
                  "full": True, "sha256": "a" * 64, "whole_bytes": 1, "native_sha256": "b" * 64}
        with self.assertRaisesRegex(ValueError, "TT extent"):
            registry.Artifact(**record)

    def test_hostile_lzma_dictionary_is_rejected(self):
        record = json.loads(self.record.read_bytes())
        row = record["attempts"][0]
        whole_path = Path(row["whole"]["path"])
        whole = bytearray(whole_path.read_bytes())
        offset = row["header"]["bytes"]
        whole[offset + 1:offset + 5] = b"\xff\xff\xff\x7f"
        whole_path.write_bytes(whole)
        row["whole"]["sha256"] = hashlib.sha256(whole).hexdigest()
        self.record.write_text(json.dumps(record), encoding="utf-8")
        self.digest = hashlib.sha256(self.record.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "invalid retained source stream"):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
