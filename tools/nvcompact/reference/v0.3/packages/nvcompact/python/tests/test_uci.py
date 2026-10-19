"""Protocol behavior tests; not source-shape or text-presence assertions."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nvuci


ORACLE = os.environ.get("NVUCI_ORACLE_PATH", "/tmp/nvcompact-uci-deps")
try:
    CHESS = nvuci._oracle(ORACLE if Path(ORACLE).is_dir() else None)
except ValueError:
    CHESS = None


ENGINE = r'''
import json, os, subprocess, sys, tempfile
sys.path.insert(0, ORACLE)
import chess
board = chess.Board()
searching = False
mode = MODE
child = None
def answer():
    if mode == 'illegal':
        print('bestmove e2e5', flush=True)
        return
    moves = sorted(move.uci() for move in board.legal_moves)
    print('bestmove ' + (moves[0] if moves else '0000'), flush=True)
    if mode == 'duplicate':
        print('bestmove ' + (moves[0] if moves else '0000'), flush=True)
for raw in sys.stdin:
    words = raw.split()
    if not words:
        continue
    if words[0] == 'uci':
        if mode in ('cleaner', 'dirty', 'crash-cleanup'):
            descriptor, path = tempfile.mkstemp()
            os.close(descriptor)
            if mode == 'cleaner':
                child = subprocess.Popen([sys.executable, '-c',
                    'import os,sys,time; time.sleep(.25); os.unlink(sys.argv[1])', path])
        if mode == 'flood':
            os.write(2, b'x' * 100000)
        if mode != 'minimal':
            print('id name deterministic protocol fixture')
            print('id author NVCompact tests')
            print('option name Threads type spin default 2 min 1 max 8')
            print('option name Hash type spin default 16 min 1 max 128')
            print('option name OwnBook type check default true')
        print('uciok', flush=True)
    elif words[0] == 'isready':
        print('readyok', flush=True)
    elif words[0] == 'position':
        if words[1] == 'startpos':
            board = chess.Board()
            suffix = words[2:]
        else:
            board = chess.Board(' '.join(words[2:8]))
            suffix = words[8:]
        if suffix:
            for move in suffix[1:]:
                board.push_uci(move)
    elif words[0] == 'go':
        if mode in ('crash-helper', 'crash-cleanup'):
            cleanup = 'import os,sys,time; time.sleep(.4); os.unlink(sys.argv[1])' if mode == 'crash-cleanup' else 'import time; time.sleep(.4)'
            child = subprocess.Popen([sys.executable, '-c', cleanup] + ([path] if mode == 'crash-cleanup' else []))
            os._exit(11)
        if 'infinite' in words:
            searching = True
        else:
            answer()
    elif words[0] == 'stop' and searching:
        searching = False
        answer()
    elif words[0] == 'quit':
        if mode == 'child':
            child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'])
        break
'''


@unittest.skipUnless(CHESS, "install chess==1.11.2 or set NVUCI_ORACLE_PATH")
class UciTests(unittest.TestCase):
    def run_engine(self, mode, **settings):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "fixture.py"
            source.write_text("ORACLE = %r\nMODE = %r\n" % (str(Path(CHESS.__file__).parent.parent), mode) + ENGINE)
            defaults = dict(oracle_path=str(Path(CHESS.__file__).parent.parent),
                            ready_seconds=1, search_seconds=1, stop_seconds=1,
                            quit_seconds=1, cleanup_seconds=.1, max_seconds=20)
            defaults.update(settings)
            config = nvuci.Config(**defaults)
            return nvuci.verify_engine([str(Path(sys.executable).resolve()), str(source)], config)

    def test_minimal_tcec_subset_does_not_require_optional_id(self):
        report = self.run_engine("minimal")
        self.assertEqual(report["verdict"], "pass", report)
        self.assertEqual(report["extended_uci_verdict"], "not_run")
        self.assertEqual(len(report["observations"]), 6)
        self.assertTrue(all(item["legal"] for item in report["observations"]))
        self.assertFalse(report["sessions"][0]["cleanup"]["forced_cleanup"])

    def test_full_uci_fen_controls_and_async_lifetime(self):
        report = self.run_engine("normal", profile="uci")
        self.assertEqual(report["verdict"], "pass", report)
        by_id = {case["id"]: case for case in report["cases"]}
        self.assertEqual(by_id["fen_checkmate"]["detail"]["bestmove"], "0000")
        self.assertEqual(by_id["fen_stalemate"]["detail"]["bestmove"], "0000")
        self.assertEqual(by_id["ready_and_stop_during_infinite"]["status"], "pass")
        changes = report["handshakes"][0]["configured_options"]
        self.assertIn({"name": "OwnBook", "value": "false", "status": "sent"}, changes)

    def test_extension_failure_is_preserved_without_failing_tcec(self):
        report = self.run_engine("minimal", extensions=True)
        self.assertEqual(report["verdict"], "pass", report)
        self.assertEqual(report["extended_uci_verdict"], "fail")
        self.assertTrue(any(item["case"] == "go_depth" for item in report["observations"]))

    def test_illegal_and_duplicate_bestmoves_fail(self):
        for mode in ("illegal", "duplicate"):
            with self.subTest(mode=mode):
                report = self.run_engine(mode, quick=True)
                self.assertEqual(report["verdict"], "fail", report)
                self.assertTrue(any(case["status"] == "fail" for case in report["cases"]))

    def test_combined_output_cap_and_child_lifetime(self):
        report = self.run_engine("flood", max_output_bytes=8192, quick=True)
        self.assertEqual(report["verdict"], "fail")
        self.assertTrue(any(case.get("kind") == "output_limit" for case in report["cases"]))
        report = self.run_engine("child", quick=True)
        self.assertEqual(report["verdict"], "fail")
        self.assertTrue(any(case.get("kind") == "cleanup" for case in report["cases"]))
        self.assertTrue(report["sessions"][0]["cleanup"]["forced_cleanup"])

    def test_bestmove_contract_handles_null_promotion_and_ponder(self):
        for line in ("bestmove (none)", "bestmove 0000", "bestmove e2e2", "bestmove e2e4 ponder e7e4", "bestmove e2e4 ponder e7e7", "bestmove e2e4 garbage"):
            with self.subTest(line=line), self.assertRaises(nvuci.ProbeError):
                nvuci.validate_bestmove(line, CHESS.Board(), CHESS)
        self.assertEqual(nvuci.validate_bestmove("bestmove e2e4 ponder e7e5", CHESS.Board(), CHESS)["ponder"], "e7e5")
        board = CHESS.Board("8/P7/8/8/8/6k1/8/4K3 w - - 0 1")
        self.assertTrue(nvuci.validate_bestmove("bestmove a7a8n", board, CHESS)["legal"])

    def test_finite_cleanup_grace_and_tmpdir_leftover_evidence(self):
        report = self.run_engine("cleaner", quick=True, cleanup_seconds=1)
        self.assertEqual(report["verdict"], "pass", report)
        self.assertTrue(report["sessions"][0]["cleanup"]["process_group_exists_immediately_after_quit"])
        self.assertGreater(report["sessions"][0]["cleanup"]["cleanup_wait_ms"], 20)
        self.assertFalse(report["sessions"][0]["working_directory_leftovers"])
        report = self.run_engine("dirty", quick=True)
        self.assertEqual(report["verdict"], "fail")
        self.assertTrue(report["sessions"][0]["working_directory_leftovers"])

    def test_crash_is_detected_before_inherited_helper_pipe_eof(self):
        report = self.run_engine("crash-helper", quick=True, search_seconds=.15)
        self.assertEqual(report["verdict"], "fail", report)
        failure = next(item for item in report["cases"] if item["status"] == "fail")
        self.assertEqual(failure["kind"], "exit")

    def test_forced_abort_does_not_blame_engine_for_interrupted_cleanup(self):
        report = self.run_engine("crash-cleanup", quick=True, search_seconds=.15)
        self.assertEqual(report["verdict"], "fail", report)
        self.assertTrue(any(item.get("kind") == "exit" and item["status"] == "fail" for item in report["cases"]))
        observations = [item for item in report["cases"] if item.get("kind") == "cleanup_observation"]
        self.assertTrue(observations)
        self.assertTrue(all(item["status"] == "incomplete" and item["harness_interrupted_cleanup"] for item in observations))

    def test_differential_never_turns_inherited_failure_into_pass(self):
        baseline = {"verdict": "fail", "cases": [{"id": "x", "status": "fail", "kind": "protocol"}],
                    "observations": [{"case": "clock", "mode": "clock", "budget": 2000,
                                      "position": "position startpos", "bestmove": "e2e4"}]}
        candidate = json.loads(json.dumps(baseline))
        candidate["observations"][0]["bestmove"] = "d2d4"
        report = nvuci.compare_results(baseline, candidate)
        self.assertEqual(report["candidate_strict_verdict"], "fail")
        self.assertEqual(report["exact_fixed_budget_observations"]["status"], "not_requested")
        self.assertTrue(report["inherited_observed_failures"])
        for source in (baseline, candidate):
            source["observations"][0].update(case="depth", mode="depth", budget=3)
        report = nvuci.compare_results(baseline, candidate, deterministic_mode="depth")
        self.assertEqual(report["exact_fixed_budget_observations"]["status"], "mismatch")
        self.assertEqual(nvuci.acceptance_verdict({"verdict": "pass", "comparison": report}), "fail")
        empty = nvuci.compare_results({}, {}, deterministic_mode="nodes")
        self.assertEqual(nvuci.acceptance_verdict({"verdict": "pass", "comparison": empty}), "incomplete")


if __name__ == "__main__":
    unittest.main()
