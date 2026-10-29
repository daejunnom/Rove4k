"""Evidence bytes are the same bytes parsed, hashed and queued; no score proof."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import durability
import run
import test_run


@unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "Linux no-follow evidence")
class ResultSnapshotTests(unittest.TestCase):
    def fixture(self, root):
        return test_run.ProtocolTests().make_mate(root)

    def controller(self, root):
        controller = run.StageController.__new__(run.StageController)
        controller.out = root
        controller.plan = {"campaign": "fixture"}
        controller.replicate = Mock()
        controller.outbox = Mock()
        controller.pending_results = {}
        controller.publisher = Mock(spec=[])
        return controller

    def test_parse_and_queue_keep_same_snapshot_across_path_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pgn, raw, spec = self.fixture(root)
            original_pgn, original_raw = pgn.read_bytes(), raw.read_bytes()
            read = run.evidence_snapshot
            def replace_after_read(path, maximum):
                result = read(path, maximum)
                if path == pgn:
                    pgn.write_text("substituted contents\n")
                return result
            snapshots = {}
            with patch.object(run, "evidence_snapshot", side_effect=replace_after_read):
                data = run.parse_result(pgn, raw, spec, snapshots=snapshots)
            self.assertEqual(data["pgn_sha256"], hashlib.sha256(original_pgn).hexdigest())
            self.assertEqual(data["raw_sha256"], hashlib.sha256(original_raw).hexdigest())
            data.update(pgn_object_key="fixture/pgn", raw_object_key="fixture/raw", evidence_directory="game")
            (root / "game").mkdir()
            controller = self.controller(root)
            controller.queue_result("fixture-game", 0, data, snapshots=snapshots)
            calls = controller.outbox.submit.call_args_list
            self.assertEqual(calls[0].args, ("fixture/pgn", original_pgn))
            self.assertEqual(calls[1].args, ("fixture/raw", original_raw))

    def test_resume_rejects_changed_bytes_before_result_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            game = root / "game"
            game.mkdir()
            pgn, raw, spec = self.fixture(game)
            data = run.parse_result(pgn, raw, spec)
            data.update(pgn_object_key="fixture/pgn", raw_object_key="fixture/raw", evidence_directory="game")
            pgn.write_text("changed\n")
            controller = self.controller(root)
            with self.assertRaisesRegex(ValueError, "bytes changed"):
                controller.queue_result("fixture-game", 0, data)
            controller.outbox.submit.assert_not_called()

    def test_snapshot_reaches_actual_outbox_and_verified_fake_transport(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            game = root / "game"
            game.mkdir()
            pgn, raw, spec = self.fixture(game)
            snapshots = {}
            data = run.parse_result(pgn, raw, spec, snapshots=snapshots)
            data.update(pgn_object_key="fixture/pgn", raw_object_key="fixture/raw", evidence_directory="game")
            pgn.write_bytes(b"replaced after parse")
            controller = self.controller(root)
            publisher = test_run.MemoryS3Port()
            controller.publisher = publisher
            controller.outbox = durability.DurableOutbox(root / "outbox", publisher)
            try:
                controller.queue_result("fixture-game", 0, data, snapshots=snapshots)
                tickets = controller.pending_results["fixture-game", 0]
                for ticket in (*tickets["required"], tickets["result"]):
                    ticket.result(5)
                self.assertEqual(publisher.objects["fixture/pgn"], snapshots["pgn"])
                self.assertEqual(publisher.objects["fixture/raw"], snapshots["raw"])
            finally:
                controller.outbox.close(5)

    def test_resume_accepts_verified_remote_bytes_when_local_evidence_is_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            game = root / "game"
            game.mkdir()
            pgn, raw, spec = self.fixture(game)
            snapshots = {}
            data = run.parse_result(pgn, raw, spec, snapshots=snapshots)
            data.update(pgn_object_key="fixture/pgn", raw_object_key="fixture/raw", evidence_directory="game")
            pgn.unlink()
            raw.unlink()
            controller = self.controller(root)
            controller.publisher = Mock()
            controller.publisher.read_verified.side_effect = lambda key, **kw: snapshots[key.rsplit("/", 1)[1]]
            controller.queue_result("fixture-game", 0, data)
            self.assertEqual(controller.outbox.submit.call_args_list[0].args, ("fixture/pgn", snapshots["pgn"]))
            self.assertEqual(controller.outbox.submit.call_args_list[1].args, ("fixture/raw", snapshots["raw"]))

    def test_resume_rejects_remote_bytes_with_wrong_digest_or_excess_size(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            game = root / "game"
            game.mkdir()
            pgn, raw, spec = self.fixture(game)
            data = run.parse_result(pgn, raw, spec)
            data.update(pgn_object_key="fixture/pgn", raw_object_key="fixture/raw", evidence_directory="game")
            pgn.unlink()
            raw.unlink()
            for invalid in (b"incorrect", b"x" * ((16 << 20) + 1)):
                controller = self.controller(root)
                controller.publisher = Mock()
                controller.publisher.read_verified.return_value = invalid
                with self.subTest(size=len(invalid)), self.assertRaises(ValueError):
                    controller.queue_result("fixture-game", 0, data)
                controller.outbox.submit.assert_not_called()

    def test_duplicate_or_malformed_critical_pgn_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            pgn, raw, spec = self.fixture(Path(folder))
            original = pgn.read_text()
            for extra in ('[White "attacker"]\n', '[White "attacker" ]\n', '[Result "0-1"]\n'):
                pgn.write_text(extra + original)
                with self.subTest(extra=extra), self.assertRaises(ValueError):
                    run.parse_result(pgn, raw, spec)

    def test_snapshot_rejects_size_links_and_during_read_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "file"
            path.write_bytes(b"a" * 65)
            with self.assertRaisesRegex(ValueError, "bounded"):
                run.evidence_snapshot(path, 64)
            symlink = root / "symlink"
            symlink.symlink_to(path)
            with self.assertRaises(OSError):
                run.evidence_snapshot(symlink, 100)
            parent_link = root / "linkdir"
            parent_link.symlink_to(root, target_is_directory=True)
            with self.assertRaises(OSError):
                run.evidence_snapshot(parent_link / "file", 100)
            hardlink = root / "hardlink"
            os.link(path, hardlink)
            with self.assertRaisesRegex(ValueError, "single-link"):
                run.evidence_snapshot(path, 100)
            hardlink.unlink()
            fifo = root / "fifo"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(ValueError, "regular file"):
                run.evidence_snapshot(fifo, 100)
            real_fstat = os.fstat
            count = 0
            def mutate(fd):
                nonlocal count
                count += 1
                if count == 2:
                    path.write_bytes(b"b" * 66)
                return real_fstat(fd)
            with patch.object(run.os, "fstat", side_effect=mutate), self.assertRaisesRegex(ValueError, "changed"):
                run.evidence_snapshot(path, 100)

    def test_crlf_pgn_preserves_exact_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            pgn, raw, spec = self.fixture(Path(folder))
            pgn.write_bytes(pgn.read_bytes().replace(b"\n", b"\r\n"))
            data = run.parse_result(pgn, raw, spec)
            self.assertEqual(data["pgn_sha256"], hashlib.sha256(pgn.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
