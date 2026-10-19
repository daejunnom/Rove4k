"""Small execution fixtures for explicit resource plans; never start lab engines."""
from __future__ import annotations

import contextlib
import fcntl
import io
import json
import os
from pathlib import Path
import resource
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nvresource
import nvuci
from test_uci import CHESS, ENGINE


MIB = 1 << 20


def specification(root, source="raise SystemExit('unexpected engine execution')\n", **settings):
    artifact = root / "fixture with spaces.py"
    artifact.write_text(source)
    value = {"format": nvresource.SPEC_FORMAT, "name": "small owned fixture",
             "artifact": artifact.name, "command": [sys.executable, "{artifact}"],
             "budget": {"required_memory_bytes": 96 * MIB, "reserve_memory_bytes": 16 * MIB,
                        "address_space_bytes": 256 * MIB, "cpu_seconds_per_process": 3,
                        "wall_seconds": 8, "file_bytes": MIB, "output_bytes_per_session": 262144},
             "uci": {"preserve_engine_options": True, "quick": True,
                     "startup_seconds": 1, "ready_seconds": .5, "search_seconds": .5,
                     "quit_seconds": .5, "cleanup_seconds": .2}}
    value["uci"].update(settings)
    if CHESS:
        value["uci"]["oracle_path"] = str(Path(CHESS.__file__).parent.parent)
    path = root / "spec.json"
    path.write_text(json.dumps(value))
    return path, artifact


def saved_plan(spec, path):
    value = nvresource.create_plan(spec)
    path.write_text(json.dumps(value))
    return value


class ResourcePlanningTests(unittest.TestCase):
    def test_plan_and_missing_opt_in_cannot_launch_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec, artifact = specification(root)
            original = artifact.read_bytes()
            with patch("subprocess.Popen", side_effect=AssertionError("planning spawned a process")):
                plan = saved_plan(spec, root / "plan.json")
                self.assertEqual(plan["status"], "planned")
                self.assertFalse(plan["engine_started"])
                with self.assertRaisesRegex(ValueError, "--start"):
                    nvresource.execute_plan(root / "plan.json", root / "run")
            self.assertFalse((root / "run").exists())
            self.assertEqual(artifact.read_bytes(), original)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(nvresource.main(["plan", str(spec), "--output", str(root / "cli-plan.json")]), 0)
            self.assertEqual(json.loads((root / "cli-plan.json").read_text())["status"], "planned")

    def test_memory_shortfall_and_changed_inputs_block_before_process_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec, artifact = specification(root)
            value = json.loads(spec.read_text())
            value["budget"].update(required_memory_bytes=1 << 60, address_space_bytes=1 << 61)
            spec.write_text(json.dumps(value))
            plan = saved_plan(spec, root / "huge-plan.json")
            self.assertEqual(plan["preflight_at_plan"]["status"], "blocked")
            with patch("subprocess.Popen", side_effect=AssertionError("insufficient resources launched an engine")):
                result = nvresource.execute_plan(root / "huge-plan.json", root / "blocked", start=True)
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["engine_started"])
            self.assertIsNone(result["uci"])
            spec, artifact = specification(root)
            saved_plan(spec, root / "old-plan.json")
            artifact.write_text("# changed input\n")
            with patch("subprocess.Popen", side_effect=AssertionError("changed input launched an engine")):
                result = nvresource.execute_plan(root / "old-plan.json", root / "changed", start=True)
            self.assertEqual(result["status"], "blocked")
            self.assertTrue(result["changed_inputs_before"])

    def test_changed_budget_and_existing_output_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec, _ = specification(root)
            plan = saved_plan(spec, root / "plan.json")
            plan["budget"]["address_space_bytes"] = -1
            plan["plan_sha256"] = nvresource._digest({key: value for key, value in plan.items() if key != "plan_sha256"})
            (root / "plan.json").write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, "address_space_bytes"):
                nvresource.execute_plan(root / "plan.json", root / "invalid", start=True)
            self.assertFalse((root / "invalid").exists())
            saved_plan(spec, root / "valid.json")
            (root / "existing").mkdir()
            keep = root / "existing/keep"
            keep.write_text("existing evidence")
            with self.assertRaises(FileExistsError):
                nvresource.execute_plan(root / "valid.json", root / "existing", start=True)
            self.assertEqual(keep.read_text(), "existing evidence")

    def test_cgroup_ancestry_is_combined_with_physical_available_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc, group = root / "proc", root / "cgroup"
            (proc / "self").mkdir(parents=True)
            (group / "job").mkdir(parents=True)
            (proc / "meminfo").write_text("MemTotal: 1024000 kB\nMemAvailable: 800000 kB\n")
            (proc / "self/stat").write_text(str(os.getpid() + 100000) + " fixture\n")
            (proc / "self/cgroup").write_text("0::/job\n")
            (proc / "self/mountinfo").write_text("1 0 0:0 / " + str(group) + " rw - cgroup2 cgroup rw\n")
            for where, maximum, usage, inactive in ((group, 400 * MIB, 350 * MIB, 10 * MIB),
                                                   (group / "job", 300 * MIB, 100 * MIB, 20 * MIB)):
                (where / "memory.max").write_text(str(maximum))
                (where / "memory.current").write_text(str(usage))
                (where / "memory.stat").write_text("file " + str(inactive) + "\ninactive_file " + str(inactive) + "\n")
            facts = nvresource.probe_resources(proc)
            self.assertFalse(facts["errors"])
            self.assertEqual(facts["estimated_available_memory_bytes"], 60 * MIB)
            self.assertFalse(facts["proc_pid_namespace_matches"])
            self.assertEqual(next(item for item in facts["cgroup_v2"] if item["path"] == str(group))["raw_headroom_bytes"], 50 * MIB)


@unittest.skipUnless(CHESS, "install chess==1.11.2 or set NVUCI_ORACLE_PATH")
class ResourceExecutionTests(unittest.TestCase):
    def test_invocation_argv_zero_is_preserved_and_retargeted_symlink_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            alias = root / "nvcompact-argv0-fixture"
            alias.symlink_to(sys.executable)
            source = "from pathlib import Path\nassert Path('/proc/self/cmdline').read_bytes().split(b'\\0')[0] == %r\n" % alias.name.encode()
            source += "ORACLE = %r\nMODE = 'normal'\n" % str(Path(CHESS.__file__).parent.parent) + ENGINE
            spec, _ = specification(root, source)
            value = json.loads(spec.read_text())
            value["command"][0] = alias.name
            spec.write_text(json.dumps(value))
            with patch.dict(os.environ, {"PATH": str(root) + os.pathsep + os.environ.get("PATH", "")}):
                saved_plan(spec, root / "plan.json")
                result = nvresource.execute_plan(root / "plan.json", root / "run", start=True)
                self.assertEqual(result["status"], "pass", result)
                self.assertFalse(result["changed_inputs_after"])
                alternate = root / "different-executable"
                shutil.copyfile(sys.executable, alternate)
                alternate.chmod(0o700)
                alias.unlink()
                alias.symlink_to(alternate)
                with patch("subprocess.Popen", side_effect=AssertionError("retargeted executable was launched")):
                    blocked = nvresource.execute_plan(root / "plan.json", root / "blocked", start=True)
                self.assertEqual(blocked["status"], "blocked")
                self.assertTrue(blocked["changed_inputs_before"])
                self.assertFalse(blocked["engine_started"])

    def test_interruption_before_verifier_returns_does_not_claim_no_engine_started(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec, _ = specification(root)
            plan = saved_plan(spec, root / "plan.json")
            self.assertEqual(plan["preflight_at_plan"]["status"], "ready", plan["preflight_at_plan"])
            with patch.object(nvuci, "verify_engine", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    nvresource.execute_plan(root / "plan.json", root / "run", start=True)
            result = json.loads((root / "run/result.json").read_text())
            self.assertEqual(result["status"], "interrupted")
            self.assertIsNone(result["engine_started"])
            self.assertTrue(result["environment_unchanged"])

    def test_small_uci_fixture_preserves_options_inputs_parent_environment_and_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = "import resource\nassert resource.getrlimit(resource.RLIMIT_AS)==(%d,%d)\nassert resource.getrlimit(resource.RLIMIT_CPU)==(3,3)\n" % (256 * MIB, 256 * MIB)
            source = prefix + "ORACLE = %r\nMODE = 'normal'\n" % str(Path(CHESS.__file__).parent.parent) + ENGINE
            spec, artifact = specification(root, source)
            plan = saved_plan(spec, root / "plan.json")
            self.assertEqual(plan["preflight_at_plan"]["status"], "ready", plan["preflight_at_plan"])
            environment = dict(os.environ)
            limits = {name: resource.getrlimit(getattr(resource, name)) for name in nvresource._limits(plan["budget"])}
            before = artifact.read_bytes()
            result = nvresource.execute_plan(root / "plan.json", root / "run", start=True)
            self.assertEqual(result["status"], "pass", result)
            self.assertTrue(result["engine_started"])
            self.assertTrue(result["environment_unchanged"])
            self.assertEqual(dict(os.environ), environment)
            self.assertEqual(artifact.read_bytes(), before)
            self.assertFalse(result["changed_inputs_after"])
            for name, value in limits.items():
                self.assertEqual(resource.getrlimit(getattr(resource, name)), value)
            changes = result["uci"]["handshakes"][0]["configured_options"]
            self.assertTrue(changes)
            self.assertTrue(all(item["status"] == "preserved" for item in changes))
            sent = [item["text"] for session in result["uci"]["sessions"] for item in session["transcript"] if item["direction"] == "send"]
            self.assertFalse(any(line.startswith("setoption") for line in sent))

    def test_timeout_releases_owned_child_and_grandchild_locks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = root / "helper.py"
            stop = root / "stop"
            helper.write_text("""import fcntl,pathlib,subprocess,sys,time
root=pathlib.Path(sys.argv[2])
with (root/(sys.argv[1]+'.lock')).open('w') as held:
 fcntl.flock(held,fcntl.LOCK_EX)
 held.write('held');held.flush()
 if sys.argv[1]=='child': subprocess.Popen([sys.executable,__file__,'grandchild',str(root)])
 deadline=time.monotonic()+15
 while not (root/'stop').exists() and time.monotonic()<deadline: time.sleep(.02)
""")
            source = "import subprocess,sys,time\nsubprocess.Popen([sys.executable,%r,'child',%r])\ntime.sleep(15)\n" % (str(helper), str(root))
            spec, _ = specification(root, source, startup_seconds=.5)
            saved_plan(spec, root / "plan.json")
            try:
                started = time.monotonic()
                result = nvresource.execute_plan(root / "plan.json", root / "run", start=True)
                self.assertIn(result["status"], ("fail", "incomplete"))
                self.assertLess(time.monotonic() - started, 5)
                self.assertTrue(result["uci"]["sessions"][0]["cleanup"]["forced_cleanup"])
                for name in ("child", "grandchild"):
                    path = root / (name + ".lock")
                    self.assertEqual(path.read_text(), "held")
                    deadline = time.monotonic() + 1
                    with path.open("r+") as held:
                        while True:
                            try:
                                fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
                                break
                            except BlockingIOError:
                                if time.monotonic() >= deadline:
                                    self.fail("owned " + name + " remained live after timeout cleanup")
                                time.sleep(.01)
            finally:
                stop.touch()

    def test_artifact_mutation_is_a_failure_without_automatic_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = "with open(__file__,'a') as stream:stream.write('\\n# mutated by fixture\\n')\n"
            source += "ORACLE = %r\nMODE = 'normal'\n" % str(Path(CHESS.__file__).parent.parent) + ENGINE
            spec, artifact = specification(root, source)
            saved_plan(spec, root / "plan.json")
            result = nvresource.execute_plan(root / "plan.json", root / "run", start=True)
            self.assertEqual(result["status"], "fail")
            self.assertTrue(result["changed_inputs_after"])
            self.assertTrue(artifact.read_text().endswith("# mutated by fixture\n"))


if __name__ == "__main__":
    unittest.main()
