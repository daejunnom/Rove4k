"""Exercise the functional UCI smoke with owned, small real processes.

These toy engines are not 4K candidates, resource evidence, or scored games.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import subprocess
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import ExitStack
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest import mock

try:
    from . import functional_uci_probe as probe
except ImportError:
    import functional_uci_probe as probe

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def write_toy(script, mode="normal"):
    script.write_text(
        "#!" + sys.executable + "\n"
        "import os,sys,time\n"
        "mode=" + repr(mode) + "\nreadys=0\n"
        "for line in sys.stdin:\n"
        " command=line.strip()\n"
        " if command=='uci':\n"
        "  if mode=='eof': break\n"
        "  if mode=='unsolicited': os.write(1,b'bestmove e2e4\\nuciok\\n')\n"
        "  elif mode=='duplicate_uci': os.write(1,b'uciok\\nuciok\\n')\n"
        "  elif mode!='timeout': print('id name toy\\nuciok',flush=True)\n"
        " elif command=='isready':\n"
        "  readys+=1\n"
        "  if mode=='duplicate_ready' or (mode=='late_ready' and readys>1): os.write(1,b'readyok\\nreadyok\\n')\n"
        "  elif mode!='timeout': print('readyok',flush=True)\n"
        " elif command.startswith('go'):\n"
        "  if mode=='illegal': os.write(1,b'bestmove e2e5\\n')\n"
        "  elif mode=='duplicate': os.write(1,b'bestmove e2e4\\nbestmove d2d4\\n')\n"
        "  elif mode!='search_timeout': os.write(1,b'bestmove e2e4\\n')\n"
        " elif command=='stop' and mode=='late_duplicate': os.write(1,b'bestmove d2d4\\n')\n"
        " elif command=='quit': break\n",
        encoding="utf-8")
    script.chmod(0o700)


@unittest.skipUnless(sys.platform == "linux" and Path("/proc/self/exe").exists(),
                     "requires Linux process ownership and /proc")
class FunctionalUciProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = load("functional_test_scope", ROOT / "engines/experiments/tcec-scope/verify.py")
        cls.owner = load("functional_test_owner", ROOT / "engines/compact/tiny-entry-d/verify.py")
        cls.oracle = load("functional_test_oracle", ROOT / "engines/tests/chess_oracle.py")
        cls.native_sha = hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()
        cls.cpus = sorted(os.sched_getaffinity(0))

    def exercise(self, mode, *, sha=None, startup_seconds=2, search_seconds=2):
        with tempfile.TemporaryDirectory(prefix="rove-functional-uci-") as tmp:
            root = Path(tmp)
            script = root / "toy"
            write_toy(script, mode)
            owned = self.owner.Owned(script, root / "io", self.owner.Budget(10))
            try:
                result = probe.exercise_protocol(
                    owned, oracle=self.oracle, scope=self.scope,
                    native_sha256=sha or self.native_sha, cpus=self.cpus,
                    startup_seconds=startup_seconds, search_seconds=search_seconds)
                return result, bytes(owned.sent)
            finally:
                if not owned.exited():
                    try:
                        owned.send(b"quit\n")
                    except BrokenPipeError:
                        # An early-EOF toy can close stdin just before it exits.
                        pass
                self.scope.finish_owned(owned)
                cleanup = owned.cleanup()
                self.assertTrue(cleanup["owned_group_absent"])
                self.assertTrue(cleanup["readers_joined"])
                self.assertFalse(cleanup["forced_cleanup"])

    def test_real_toy_uci_path_legal_and_diagnostic_only(self):
        result, sent = self.exercise("normal")
        self.assertEqual(result["format"], "rove4k-functional-uci-smoke-v1")
        self.assertEqual(result["bestmove"], "e2e4")
        self.assertTrue(result["legal_bestmove"])
        self.assertTrue(result["idle_stop_sent"])
        self.assertFalse(result["stop_support_required"])
        self.assertEqual(result["startup_image"]["native_sha256"], self.native_sha)
        self.assertEqual(result["post_search_image"]["native_sha256"], self.native_sha)
        self.assertTrue(all(value is False for value in result["claims"].values()))
        self.assertIn(b"uci\n", sent)
        self.assertIn(b"isready\n", sent)
        self.assertIn(b"position startpos\n", sent)
        self.assertIn(b"go wtime 1000 btime 1000 winc 0 binc 0\n", sent)
        self.assertIn(b"stop\n", sent)

    def test_illegal_bestmove_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "illegal bestmove"):
            self.exercise("illegal")

    def test_duplicate_bestmoves_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly one bestmove|extra bestmove"):
            self.exercise("duplicate")
        with self.assertRaisesRegex(ValueError, "extra bestmove"):
            self.exercise("late_duplicate")

    def test_unsolicited_bestmove_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsolicited bestmove"):
            self.exercise("unsolicited")

    def test_duplicate_uci_acknowledgements_are_rejected(self):
        for mode in ("duplicate_uci", "duplicate_ready", "late_ready"):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, "duplicat"):
                self.exercise(mode)

    def test_stdout_eof_before_uciok_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "unexpected stdout EOF"):
            self.exercise("eof")

    def test_startup_and_search_timeouts_are_bounded(self):
        with self.assertRaises(TimeoutError):
            self.exercise("timeout", startup_seconds=.2)
        with self.assertRaisesRegex(TimeoutError, "search exceeded"):
            self.exercise("search_timeout", search_seconds=.2)

    def test_running_native_must_match_frozen_identity(self):
        with self.assertRaisesRegex(ValueError, "native image differs"):
            self.exercise("normal", sha="0" * 64)


@unittest.skipUnless(sys.platform == "linux" and Path("/proc/self/exe").exists(),
                     "requires Linux process ownership and /proc")
class FunctionalCandidateFixtureTests(unittest.TestCase):
    """Real owned toy process; candidate, placement and capacity are fixtures.

    This tests assembly and failure propagation, not actual cgroup creation,
    candidate admission, memory allocation or a P16/P192 engine.
    """
    @classmethod
    def setUpClass(cls):
        cls.scope = load("functional_candidate_scope", ROOT / "engines/experiments/tcec-scope/verify.py")
        cls.owner = load("functional_candidate_owner", ROOT / "engines/compact/tiny-entry-d/verify.py")
        cls.oracle = load("functional_candidate_oracle", ROOT / "engines/tests/chess_oracle.py")
        cls.native_sha = hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()

    def test_single_engine_consumer_explicitly_uses_single_candidate_validation(self):
        with tempfile.TemporaryDirectory(prefix="rove-functional-one-candidate-") as tmp:
            root = Path(tmp)
            source = root / "candidates.json"
            with mock.patch.object(probe.diagnostic_candidates, "read_candidates",
                                   side_effect=ValueError("sentinel candidate check")) as read:
                with self.assertRaisesRegex(ValueError, "sentinel candidate check"):
                    probe.run_candidate(candidate_path=source, candidate_sha256="a" * 64,
                        artifact_id="candidate-a", profile="test-p16", slot={}, cgroup={},
                        saved_ancestor_cpus=[], out=root / "out")
            read.assert_called_once_with(source, "a" * 64, "test-p16", allow_single=True)
            self.assertFalse((root / "out").exists())

    def run_fixture(self, root, *, oom=False, group_path="/sys/fs/cgroup/rove-functional-fixture", available=80 << 30,
                    fail_after_registration=False, saved_nodes=None):
        whole = root / "toy"
        write_toy(whole)
        source = root / "source.c"
        source.write_text("/* fixture source only */\n", encoding="utf-8")
        source_bytes = source.read_bytes()
        native = Path(sys.executable).resolve()
        artifact = SimpleNamespace(id="toy-a-p16", family="A", sha256=hashlib.sha256(whole.read_bytes()).hexdigest(),
                                   whole_bytes=whole.stat().st_size, native_sha256=self.native_sha,
                                   tt_bytes=12 << 30, workers=16)
        candidate = {"artifact": artifact, "whole": whole,
                     "source": {"path": str(source), "bytes": len(source_bytes),
                                "sha256": hashlib.sha256(source_bytes).hexdigest()},
                     "native": {"path": str(native), "bytes": native.stat().st_size, "sha256": self.native_sha},
                     "evidence": {"kind": "fixture-only", "source_contract_verified": False}}
        slot = {"id": "fixture-slot", "workers": 16, "cpus": list(range(16)),
                "physical_cores": [[0, core] for core in range(8)],
                "memory_nodes": [0], "smt": True, "policy": "default"}
        cgroup = {"path": group_path, "device": 1, "inode": 2,
                  "cpus": list(range(16)), "memory_nodes": [0], "memory_max": 16 << 30}
        observed = {"path": group_path, "cpus": list(range(16)), "memory_nodes": [0],
                    "device": 1, "inode": 2, "memory_max": 16 << 30}
        capacity = {"delegated_cgroup": {}, "host_memavailable_bytes": available,
                    "node_available_bytes": {0: available}}
        events_before = {"oom": 0, "oom_kill": 0}
        events_after = {"oom": int(oom), "oom_kill": 0}

        def fixture_launcher(path, *, whole, record, release_file, **_kwargs):
            # Placement is simulated; exec and UCI interact with a real child.
            self.launcher_saved_nodes = _kwargs["saved_nodes"]
            receipt = {"stage": "pre-exec runner; final engine observation is separate",
                       "requested_cpus": list(range(16)), "effective_cpus": list(range(16)),
                       "requested_nodes": [0], "effective_allowed_nodes": [0], "cgroup": cgroup,
                       "requested_policy": "default", "fallback": None,
                       "observed_policy": {"available": True, "request_applied": True, "mode": 0}}
            body = ("#!" + sys.executable + "\n" +
                    "import json,os,time\nfrom pathlib import Path\n" +
                    "gate=Path(" + repr(str(release_file)) + ")\n" +
                    "while not gate.exists(): time.sleep(.005)\n" +
                    "receipt=" + repr(receipt) + "\nreceipt['pid']=os.getpid()\n" +
                    "Path(" + repr(str(record)) + ").write_text(json.dumps(receipt))\n" +
                    "os.execv(" + repr(str(whole)) + ",[" + repr(str(whole)) + "])\n")
            path.write_text(body, encoding="utf-8")
            path.chmod(0o700)

        def fixture_cgroup_file(path):
            if path.name == "cgroup.procs":
                record = json.loads((root / "out" / "placement.json").read_text(encoding="utf-8"))
                return str(record["pid"]) + "\n"
            if path.name == "cgroup.events":
                return "populated 0\n"
            raise AssertionError("unexpected mocked cgroup file: " + str(path))

        with ExitStack() as patches:
            patches.enter_context(mock.patch.object(probe.diagnostic_candidates, "read_candidates", return_value=([candidate], "a" * 64)))
            patches.enter_context(mock.patch.object(probe.diagnostic_candidates, "_profile_verifier",
                return_value=SimpleNamespace(support_modules=lambda: (self.scope, self.owner, self.oracle))))
            patches.enter_context(mock.patch.object(probe.peak_probe_session, "_require_delegated_root"))
            patches.enter_context(mock.patch.object(probe.peak_capacity, "_require_empty"))
            patches.enter_context(mock.patch.object(probe.placement, "verify_cgroup_live", return_value=observed))
            topology_fixture = SimpleNamespace(
                cpus=[SimpleNamespace(id=cpu, physical=(0, cpu // 2),
                                      siblings=(cpu // 2 * 2, cpu // 2 * 2 + 1))
                      for cpu in range(16)],
                to_record=lambda: {"fixture": True})
            slot_fixture = SimpleNamespace(cpus=tuple(range(16)),
                physical_cores=tuple((0, core) for core in range(8)), to_record=lambda: slot)
            patches.enter_context(mock.patch.object(probe.topology.Topology, "snapshot_target", return_value=topology_fixture))
            patches.enter_context(mock.patch.object(probe.topology, "plan_slots", return_value=(slot_fixture,)))
            patches.enter_context(mock.patch.object(probe.memory_observation, "observe_capacity", return_value=capacity))
            patches.enter_context(mock.patch.object(probe.peak_capacity, "_finite_remaining", return_value=[available]))
            patches.enter_context(mock.patch.object(probe.memory_observation, "_file", side_effect=fixture_cgroup_file))
            patches.enter_context(mock.patch.object(probe, "_events", side_effect=[events_before, events_after]))
            patches.enter_context(mock.patch.object(probe, "_launcher", side_effect=fixture_launcher))
            if fail_after_registration:
                def interrupted_constructor(owner, launcher, directory, budget):
                    registered = owner.Owned(launcher, directory, budget)
                    self.registered_pid = registered.process.pid
                    raise RuntimeError("fixture constructor interrupted after registration")
                patches.enter_context(mock.patch.object(probe.peer_runtime, "construct_owned", side_effect=interrupted_constructor))
            return probe.run_candidate(candidate_path=root / "mock-candidates", candidate_sha256="a" * 64,
                artifact_id=artifact.id, profile="test-p16", slot=slot, cgroup=cgroup,
                saved_ancestor_cpus=list(range(16)), saved_ancestor_nodes=saved_nodes, out=root / "out")

    def test_node_envelope_validation_and_launcher_forwarding(self):
        for nodes in (None, [0], [0, 1]):
            with self.subTest(nodes=nodes), tempfile.TemporaryDirectory(prefix="rove-nodes-valid-") as tmp:
                self.assertTrue(self.run_fixture(Path(tmp), saved_nodes=nodes)["complete"])
                self.assertEqual(self.launcher_saved_nodes, nodes)
        for nodes in ([], [1], [0, 0], [0, -1], [0, True], "0", (0,)):
            with self.subTest(nodes=nodes), tempfile.TemporaryDirectory(prefix="rove-nodes-invalid-") as tmp:
                with self.assertRaisesRegex(ValueError, "original NUMA node envelope"):
                    self.run_fixture(Path(tmp), saved_nodes=nodes)
                self.assertFalse((Path(tmp) / "out").exists())

    def test_real_toy_uci_and_cleanup_with_mocked_candidate_and_cgroup(self):
        with tempfile.TemporaryDirectory(prefix="rove-functional-fixture-") as tmp:
            report = self.run_fixture(Path(tmp))
            self.assertTrue(report["complete"])
            self.assertEqual(report["uci"]["bestmove"], "e2e4")
            self.assertFalse(report["scored_game_admitted"])
            self.assertTrue(report["cgroup_populated_zero"])
            self.assertFalse(report["oom_observed"])
            self.assertFalse(report["cleanup"]["forced_cleanup"])
            self.assertTrue((Path(tmp) / "out" / "functional-runtime.json").is_file())
            self.assertFalse(self.owner.OWNED)

    def test_partial_constructor_recovers_registered_child(self):
        with tempfile.TemporaryDirectory(prefix="rove-functional-constructor-") as tmp:
            with self.assertRaises(probe.FunctionalProbeFailure) as caught:
                self.run_fixture(Path(tmp), fail_after_registration=True)
            report = caught.exception.report
            self.assertFalse(report["complete"])
            self.assertIn("constructor interrupted", report["failure"]["message"])
            self.assertEqual(len(report["recovered_constructor_handles"]), 1)
            self.assertTrue(report["recovered_constructor_handles"][0]["owned_group_absent"])
            self.assertFalse(self.owner.OWNED)
            self.assertFalse(Path(f"/proc/{self.registered_pid}").exists())

    def test_oom_is_failure_even_after_legal_bestmove(self):
        with tempfile.TemporaryDirectory(prefix="rove-functional-oom-") as tmp:
            with self.assertRaises(probe.FunctionalProbeFailure) as caught:
                self.run_fixture(Path(tmp), oom=True)
            report = caught.exception.report
            self.assertFalse(report["complete"])
            self.assertEqual(report["uci"]["bestmove"], "e2e4")
            self.assertTrue(report["oom_observed"])
            self.assertFalse(report["scored_game_admitted"])
            self.assertTrue((Path(tmp) / "out" / "functional-runtime.json").is_file())
            self.assertFalse(self.owner.OWNED)

    def test_arbitrary_cgroup_and_insufficient_capacity_are_rejected_before_launch(self):
        with tempfile.TemporaryDirectory(prefix="rove-functional-invalid-") as tmp:
            with self.assertRaisesRegex(ValueError, "visible cgroup2 descendant"):
                self.run_fixture(Path(tmp), group_path=str(Path(tmp) / "fake-cgroup"))
            self.assertFalse((Path(tmp) / "out").exists())
        with tempfile.TemporaryDirectory(prefix="rove-functional-small-") as tmp:
            with self.assertRaisesRegex(ValueError, "capacity is insufficient"):
                self.run_fixture(Path(tmp), available=1 << 30)
            self.assertFalse((Path(tmp) / "out").exists())


@unittest.skipUnless(sys.platform == "linux" and Path("/proc/self/exe").exists(),
                     "requires Linux process ownership and /proc")
class RealLauncherGuardTests(unittest.TestCase):
    """Execute the real generated launcher only through its pre-placement guards."""

    def test_direct_isolated_cli_help(self):
        completed = subprocess.run([sys.executable, "-I", "-B", str(HERE / "functional_uci_probe.py"), "--help"],
                                   capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for argument in ("--candidates", "--candidates-sha256", "--profile", "--artifact",
                         "--placement", "--placement-sha256", "--out", "--wall-seconds"):
            self.assertIn(argument, completed.stdout)
        self.assertIn("test-p16", completed.stdout)
        self.assertIn("test-p192", completed.stdout)

    def test_cli_accepts_old_and_new_exact_placement_records(self):
        with tempfile.TemporaryDirectory(prefix="rove-placement-cli-") as tmp:
            root = Path(tmp)
            plan = {"slot": {"id": "slot"}, "cgroup": {"path": "/fixture"},
                    "saved_ancestor_cpus": [0, 1]}
            argv = ["--candidates", str(root / "candidates"), "--candidates-sha256", "a" * 64,
                    "--profile", "test-p16", "--artifact", "candidate-a",
                    "--placement", str(root / "placement"), "--placement-sha256", "b" * 64,
                    "--out", str(root / "out")]
            for nodes in (None, [0, 1]):
                current = dict(plan)
                if nodes is not None:
                    current["saved_ancestor_nodes"] = nodes
                with self.subTest(nodes=nodes), \
                     mock.patch.object(probe.diagnostic_candidates, "_safe_input_path", side_effect=lambda x: x), \
                     mock.patch.object(probe.diagnostic_candidates.run, "json_input", return_value=(current, "b" * 64)) as read, \
                     mock.patch.object(probe, "run_candidate", return_value={"complete": True}) as run, \
                     redirect_stdout(io.StringIO()):
                    probe.main(argv)
                    read.assert_called_once_with(root / "placement", "b" * 64)
                    self.assertEqual(run.call_args.kwargs["saved_ancestor_nodes"], nodes)
                    self.assertEqual(run.call_args.kwargs["saved_ancestor_cpus"], [0, 1])
            for bad in ({**plan, "extra": True}, {"slot": {}, "cgroup": {}}):
                with self.subTest(bad=bad), \
                     mock.patch.object(probe.diagnostic_candidates, "_safe_input_path", side_effect=lambda x: x), \
                     mock.patch.object(probe.diagnostic_candidates.run, "json_input", return_value=(bad, "b" * 64)), \
                     mock.patch.object(probe, "run_candidate") as run:
                    with self.assertRaisesRegex(ValueError, "exact pinned single-slot"):
                        probe.main(argv)
                    run.assert_not_called()

    def test_generated_launcher_passes_node_envelope_to_placement(self):
        with tempfile.TemporaryDirectory(prefix="rove-launcher-nodes-") as tmp:
            root = Path(tmp)
            fake = root / "fixture_placement.py"
            capture = root / "placement-arguments.json"
            fake.write_text("import json\nfrom pathlib import Path\n"
                "def apply_slot(slot, **kwargs):\n"
                " Path(" + repr(str(capture)) + ").write_text(json.dumps({'slot':slot, **kwargs}))\n"
                " return {'fallback':None,'observed_policy':{'available':True,'request_applied':True,'mode':0}}\n",
                encoding="utf-8")
            target = root / "target"
            target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            target.chmod(0o700)
            launcher, owner, release = (root / name for name in ("launcher", "owner", "release"))
            with mock.patch.object(probe.placement, "__file__", str(fake)):
                probe._launcher(launcher, whole=target, whole_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                    slot={"id": "test"}, cgroup={"path": "/fixture"}, saved_cpus=[0, 1], saved_nodes=[2, 3],
                    record=root / "receipt", owner_file=owner, release_file=release, temporary=root)
            process = subprocess.Popen([str(launcher)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=True)
            try:
                fields = Path(f"/proc/{process.pid}/stat").read_text().rsplit(")", 1)[1].split()
                raw = json.dumps({"pid": process.pid, "pgid": int(fields[2]), "session": int(fields[3]),
                                  "start_ticks": int(fields[19])}).encode()
                owner.write_bytes(raw)
                release.write_text(hashlib.sha256(raw).hexdigest(), encoding="ascii")
                _, stderr = process.communicate(timeout=5)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
            self.assertEqual(process.returncode, 0, stderr.decode(errors="replace"))
            self.assertEqual(json.loads(capture.read_text()),
                {"slot": {"id": "test"}, "cgroup": {"path": "/fixture"},
                 "saved_ancestor_cpus": [0, 1], "saved_ancestor_nodes": [2, 3]})

    def run_launcher(self, root, *, matching_owner, symlink_target=False):
        target = root / "target"
        target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        target.chmod(0o700)
        whole = root / "linked-target" if symlink_target else target
        if symlink_target:
            whole.symlink_to(target)
        launcher, owner, release = (root / name for name in ("launcher", "owner", "release"))
        probe._launcher(launcher, whole=whole, whole_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                        slot={}, cgroup={}, saved_cpus=[], record=root / "placement.json",
                        owner_file=owner, release_file=release, temporary=root)
        process = subprocess.Popen([str(launcher)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        try:
            fields = Path(f"/proc/{process.pid}/stat").read_text().rsplit(")", 1)[1].split()
            identity = {"pid": process.pid if matching_owner else process.pid + 1,
                        "pgid": int(fields[2]), "session": int(fields[3]),
                        "start_ticks": int(fields[19])}
            raw = json.dumps(identity).encode("utf-8")
            owner.write_bytes(raw)
            release.write_text(hashlib.sha256(raw).hexdigest(), encoding="ascii")
            stdout, stderr = process.communicate(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse((root / "placement.json").exists())
        return stdout, stderr

    def test_real_launcher_rejects_mismatched_owner_after_loading_modules(self):
        with tempfile.TemporaryDirectory(prefix="rove-real-launcher-owner-") as tmp:
            _, stderr = self.run_launcher(Path(tmp), matching_owner=False)
            self.assertIn(b"owner identity differs", stderr)

    def test_real_launcher_rejects_symlink_candidate_before_placement(self):
        with tempfile.TemporaryDirectory(prefix="rove-real-launcher-symlink-") as tmp:
            _, stderr = self.run_launcher(Path(tmp), matching_owner=True, symlink_target=True)
            self.assertIn(b"Too many levels of symbolic links", stderr)


if __name__ == "__main__":
    unittest.main()
