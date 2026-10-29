#!/usr/bin/env python3
"""Boundary/fault checks for peer qualification; mocks never qualify a player."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("tested_peer_runtime", HERE / "peer_runtime.py")
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)
peers = runtime.sibling("peers")
topology = runtime.sibling("topology")


def elf_fixture(*, symbol_size=8, dependency=b"libc.so.6", symbol_name=b"table"):
    """A separate ELF writer supplies known symbol and dynamic-table offsets."""
    data = bytearray(176)
    data[:16] = b"\x7fELF\x02\x01\x01" + bytes(9)
    def append(value):
        start = len(data)
        data.extend(value)
        return start, len(value)
    interpreter = append(b"/lib64/ld-linux-x86-64.so.2\0")
    strings = append(b"\0" + symbol_name + b"\0")
    symbols = append(bytes(24) + struct.pack("<IBBHQQ", 1, 0x11, 0, 1, 0x200, symbol_size))
    dynamic_strings = append(b"\0" + dependency + b"\0")
    dynamic = append(struct.pack("<qQqQ", 1, 1, 0, 0))
    data.extend(bytes((-len(data)) % 8))
    section_start = len(data)
    def section(kind, extent, link=0, stride=0):
        return struct.pack("<IIQQQQIIQQ", 0, kind, 0, 0, extent[0], extent[1], link, 0, 1, stride)
    data.extend(bytes(64))
    data.extend(section(3, strings))
    data.extend(section(2, symbols, 1, 24))
    data.extend(section(3, dynamic_strings))
    data.extend(section(6, dynamic, 3, 16))
    struct.pack_into("<HHIQQQIHHHHHH", data, 16, 3, 62, 1, 0, 64, section_start, 0, 64, 56, 2, 64, 5, 0)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 6, 0, 0, 0, len(data), 8192, 4096)
    struct.pack_into("<IIQQQQQQ", data, 120, 3, 4, interpreter[0], interpreter[0], 0, interpreter[1], interpreter[1], 1)
    return bytes(data)


class PeerRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "linux", "isolated Linux peer diagnostic CLI")
    def test_controlled_cli_can_import_owner_in_isolated_mode(self):
        with tempfile.TemporaryDirectory(prefix="peer-cli-") as tmp:
            root = Path(tmp).resolve()
            command = [sys.executable, "-I", "-B", str(HERE / "peer_runtime.py"), "qualify-controlled",
                "--root", str(root / "cgroup"), "--campaign", "test", "--candidates", str(root / "missing.json"),
                "--candidates-sha256", "a" * 64, "--profile", "test-p16", "--artifact-id", "peer-one",
                "--reference", str(root / "reference.json"), "--manifest-sha", "b" * 64, "--out", str(root / "out")]
            result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b"ModuleNotFoundError", result.stderr)
            self.assertIn(b"missing.json", result.stderr)

    def test_controlled_peer_binds_reference_and_never_grants_score(self):
        import diagnostic_candidates
        import functional_probe_session

        artifact = SimpleNamespace(id="peer-one", family="ice4", profile="test-p16", tt_bytes=16 << 30,
                                   sha256="a" * 64, native_sha256="b" * 64)
        slot = {"id": "slot-000", "cpus": [0, 1], "memory_nodes": [0], "workers": 16, "policy": "default"}
        owner = object.__new__(functional_probe_session.OwnedFunctionalProbe)
        owner.slot = SimpleNamespace(to_record=lambda: slot)
        owner.cgroup = {"path": "/sys/fs/cgroup/test/slot-000"}
        owner.saved_ancestor_cpus, owner.saved_ancestor_nodes = [0, 1], [0]
        owner.close, owner._attempted, owner._running = Mock(return_value=[]), False, False
        evidence = {"kind": "peer-reference-v1", "reference_sha256": "c" * 64}
        result = {"qualified": False, "admission": None,
                  "record": {"complete": False, "controlled_diagnostic": {"authorizes_go": False}}}
        arguments = dict(root=Path("/sys/fs/cgroup/test"), campaign="test-campaign",
            candidate_path=Path("/tmp/candidates.json"), candidate_sha256="d" * 64, profile="test-p16",
            artifact_id="peer-one", reference=Path("/tmp/reference.json"), reference_sha="c" * 64,
            out=Path("/tmp/peer-result"), wall_seconds=180)
        with patch.object(diagnostic_candidates, "read_candidates", return_value=([{"artifact": artifact, "evidence": evidence}], "d" * 64)), \
             patch.object(functional_probe_session.OwnedFunctionalProbe, "create", return_value=owner) as create, \
             patch.object(runtime, "qualify_peer", return_value=result) as qualify:
            self.assertEqual(runtime.qualify_peer_controlled(**arguments), result)
            create.assert_called_once()
            self.assertEqual(qualify.call_args.kwargs["reference_sha"], "c" * 64)
            self.assertIs(qualify.call_args.kwargs["_controlled"].owner, owner)
            self.assertTrue(owner._attempted)
            self.assertFalse(owner._running)
            owner.close.assert_called_once()

        with patch.object(diagnostic_candidates, "read_candidates", return_value=([{"artifact": artifact, "evidence": evidence}], "d" * 64)), \
             patch.object(functional_probe_session.OwnedFunctionalProbe, "create") as create:
            with self.assertRaisesRegex(ValueError, "matching source-bound"):
                runtime.qualify_peer_controlled(**{**arguments, "reference_sha": "e" * 64})
            create.assert_not_called()

        artifact.profile, artifact.tt_bytes = "test-p192", 128 << 30
        with patch.object(diagnostic_candidates, "read_candidates", return_value=([{"artifact": artifact, "evidence": evidence}], "d" * 64)), \
             patch.object(functional_probe_session.OwnedFunctionalProbe, "create") as create:
            with self.assertRaisesRegex(ValueError, "192 GiB TT"):
                runtime.qualify_peer_controlled(**{**arguments, "profile": "test-p192"})
            create.assert_not_called()

    def test_controlled_peer_failure_retains_cleanup_context(self):
        import diagnostic_candidates
        import functional_probe_session
        artifact = SimpleNamespace(id="peer-one", family="c4ke", profile="test-p16", tt_bytes=16 << 30,
                                   sha256="a" * 64, native_sha256="b" * 64)
        owner = object.__new__(functional_probe_session.OwnedFunctionalProbe)
        owner.slot = SimpleNamespace(to_record=lambda: {"cpus": [0], "memory_nodes": [0]})
        owner.cgroup = {"path": "/sys/fs/cgroup/test/slot-000"}
        owner.saved_ancestor_cpus, owner.saved_ancestor_nodes = [0], [0]
        owner.manager = SimpleNamespace(created=[])
        owner.close, owner._attempted, owner._running = Mock(return_value=[{"error": "group populated"}]), False, False
        evidence = {"kind": "peer-reference-v1", "reference_sha256": "c" * 64}
        with patch.object(diagnostic_candidates, "read_candidates", return_value=([{"artifact": artifact, "evidence": evidence}], "d" * 64)), \
             patch.object(functional_probe_session.OwnedFunctionalProbe, "create", return_value=owner), \
             patch.object(runtime, "qualify_peer", side_effect=ValueError("qualification failed")):
            with self.assertRaises(functional_probe_session.FunctionalCleanupFailure) as caught:
                runtime.qualify_peer_controlled(root=Path("/sys/fs/cgroup/test"), campaign="test",
                    candidate_path=Path("/tmp/candidates.json"), candidate_sha256="d" * 64,
                    profile="test-p16", artifact_id="peer-one", reference=Path("/tmp/reference.json"),
                    reference_sha="c" * 64, out=Path("/tmp/peer-result"))
            self.assertIs(caught.exception.owner, owner)
            self.assertIsInstance(caught.exception.original, ValueError)
            self.assertFalse(owner._running)

    def test_controlled_owner_signal_waits_for_cleanup(self):
        import diagnostic_candidates
        import functional_probe_session
        artifact = SimpleNamespace(id="peer-one", family="ice4", profile="test-p16", tt_bytes=16 << 30,
                                   sha256="a" * 64, native_sha256="b" * 64)
        evidence = {"kind": "peer-reference-v1", "reference_sha256": "c" * 64}
        arguments = dict(root=Path("/sys/fs/cgroup/test"), campaign="test",
            candidate_path=Path("/tmp/candidates.json"), candidate_sha256="d" * 64,
            profile="test-p16", artifact_id="peer-one", reference=Path("/tmp/reference.json"),
            reference_sha="c" * 64, out=Path("/tmp/peer-result"))
        for phase in ("create", "cleanup"):
            owner = object.__new__(functional_probe_session.OwnedFunctionalProbe)
            owner.slot = SimpleNamespace(to_record=lambda: {"cpus": [0], "memory_nodes": [0]})
            owner.cgroup = {"path": "/sys/fs/cgroup/test/slot-000"}
            owner.saved_ancestor_cpus, owner.saved_ancestor_nodes = [0], [0]
            owner._attempted, owner._running = False, False
            def create(**kwargs):
                if phase == "create":
                    runtime.bounded_signal(signal.SIGTERM, None)
                return owner
            def close():
                if phase == "cleanup":
                    runtime.bounded_signal(signal.SIGTERM, None)
                return []
            owner.close = Mock(side_effect=close)
            result = {"qualified": False, "admission": None,
                      "record": {"complete": False, "controlled_diagnostic": {"authorizes_go": False}}}
            with self.subTest(phase=phase), \
                 patch.object(diagnostic_candidates, "read_candidates", return_value=([{"artifact": artifact, "evidence": evidence}], "d" * 64)), \
                 patch.object(functional_probe_session.OwnedFunctionalProbe, "create", side_effect=create), \
                 patch.object(runtime, "qualify_peer", return_value=result) as qualify:
                with self.assertRaises(KeyboardInterrupt):
                    runtime.qualify_peer_controlled(**arguments)
                owner.close.assert_called_once()
                self.assertFalse(owner._running)
                if phase == "create":
                    qualify.assert_not_called()

    def test_controlled_peer_preflight_keeps_ownership_and_treats_free_memory_as_telemetry(self):
        import functional_probe_session
        import memory_observation
        import peak_capacity
        import peak_probe_session
        import placement
        group_path = Path("/sys/fs/cgroup/owned/campaign/slot-000")
        group = {"path": str(group_path), "device": 7, "inode": 42, "memory_max": 20 << 30,
                 "cpus": [0, 1], "memory_nodes": [0]}
        manager = object.__new__(placement.CgroupSlots)
        manager._root_fd, manager._parent_fd, manager._closed = 10, 11, False
        manager.parent, manager.created = group_path.parent, [(group_path, 7, 42)]
        manager._check_anchored_parent = Mock()
        owner = object.__new__(functional_probe_session.OwnedFunctionalProbe)
        owner.slot = SimpleNamespace(to_record=lambda: {"id": "slot-000", "cpus": [0, 1], "memory_nodes": [0]})
        owner.cgroup, owner.manager = group, manager
        owner.saved_ancestor_cpus, owner.saved_ancestor_nodes = [0, 1], [0]
        artifact = SimpleNamespace(sha256="a" * 64)
        context = runtime._ControlledPeer(owner, artifact, "b" * 64, "c" * 64)
        capacity = {"host_memavailable_bytes": 20 << 30, "delegated_cgroup": {},
                    "node_available_bytes": {0: 20 << 30}}
        with patch.object(peak_probe_session, "_require_delegated_root"), \
             patch.object(placement, "verify_cgroup_live", return_value=group), \
             patch.object(peak_capacity, "_require_empty") as fresh, \
             patch.object(runtime, "_controlled_peer_quiescent", return_value=0), \
             patch.object(peak_capacity, "_finite_remaining", return_value=[20 << 30]), \
             patch.object(memory_observation, "observe_capacity", return_value=capacity):
            observed = runtime._controlled_peer_preflight(context, {"workers": 16, "tt_bytes": 16 << 30})
            self.assertGreater(observed["required_bytes"], 16 << 30)
            self.assertIn("not a physical reservation", observed["scope"])
            manager._check_anchored_parent.assert_called_once()
            runtime._controlled_peer_preflight(context, {"workers": 16, "tt_bytes": 16 << 30})
            fresh.assert_called_once()
            manager.created = [(group_path, 7, 43)]
            with self.assertRaisesRegex(ValueError, "original anchored"):
                runtime._controlled_peer_preflight(context, {"workers": 16, "tt_bytes": 16 << 30})
            manager.created = [(group_path, 7, 42)]
            capacity["node_available_bytes"] = {0: 1}
            capacity["host_memavailable_bytes"] = 0
            observed = runtime._controlled_peer_preflight(context, {"workers": 16, "tt_bytes": 16 << 30})
            self.assertFalse(observed["current_availability_enforced"])
            self.assertEqual(observed["capacity"]["node_available_bytes"], {0: 1})
            group["memory_max"] = 16 << 30
            with self.assertRaisesRegex(ValueError, "cgroup memory limit is insufficient"):
                runtime._controlled_peer_preflight(context, {"workers": 16, "tt_bytes": 16 << 30})

    def test_controlled_peer_source_closure_detects_live_and_snapshot_changes(self):
        with tempfile.TemporaryDirectory(prefix="peer-source-") as tmp:
            base = Path(tmp).resolve()
            source, frozen = base / "source", base / "frozen"
            paths = runtime.SOURCE_FILES + runtime.LEAGUE_SOURCE_FILES + runtime.CONTROLLED_SOURCE_FILES
            # The controlled functional path imports these transitively: run
            # owns ledger/collection, while peak_probe_session loads the peak
            # supervisor, receipt and wave modules.  The profile verifier and
            # shared input reader are loaded dynamically by the UCI probe.
            transitive = tuple("engines/experiments/strength/" + module + ".py" for module in (
                "budget", "collect", "durability", "fastchess", "ledger", "overhead",
                "peak_ready_probe", "peak_supervisor", "wave", "peak_receipt")) + (
                "engines/experiments/tcec-next/profile_verify.py",
                "engines/scripts/production_input.py",
            )
            for relative in transitive + tuple("engines/experiments/strength/" + module for module in
                                               ("rove_b_tt_observe.py", "rove_vma_observer.py")):
                self.assertIn(relative, paths)
            self.assertEqual(len(paths), len(set(paths)))
            pins = {}
            for relative in paths:
                raw = (runtime.ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
                for root in (source, frozen):
                    destination = root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(raw)
                pins[relative] = {"bytes": len(raw), "sha256": runtime.sha(raw)}
            context = SimpleNamespace(source_pins=pins, frozen=frozen)
            with patch.object(runtime, "ROOT", source):
                runtime._check_controlled_sources(context)
                # Earlier controlled receipts lacking a new dependency stay
                # historical and cannot be reinterpreted as the fuller set.
                for relative in transitive:
                    missing = dict(pins)
                    missing.pop(relative)
                    with self.subTest(missing=relative), self.assertRaisesRegex(ValueError, "source closure is incomplete"):
                        runtime._check_controlled_sources(SimpleNamespace(source_pins=missing, frozen=frozen))
                extra = dict(pins)
                extra["engines/experiments/strength/unexpected.py"] = {"bytes": 1, "sha256": "0" * 64}
                with self.assertRaisesRegex(ValueError, "source closure is incomplete"):
                    runtime._check_controlled_sources(SimpleNamespace(source_pins=extra, frozen=frozen))
                for relative in transitive:
                    for changed_root, original_root in ((source, frozen), (frozen, source)):
                        changed = changed_root / relative
                        changed.write_bytes(changed.read_bytes() + b"\n# changed\n")
                        with self.subTest(module=relative, changed=str(changed_root)), self.assertRaisesRegex(ValueError, "source closure changed"):
                            runtime._check_controlled_sources(context)
                        shutil.copyfile(original_root / relative, changed)
                runtime._check_controlled_sources(context)
                changed = source / runtime.CONTROLLED_SOURCE_FILES[0]
                changed.write_bytes(changed.read_bytes() + b"\n# changed\n")
                with self.assertRaisesRegex(ValueError, "source closure changed"):
                    runtime._check_controlled_sources(context)
                shutil.copyfile(frozen / runtime.CONTROLLED_SOURCE_FILES[0], changed)
                runtime._check_controlled_sources(context)
                for module in ("rove_b_tt_observe.py", "rove_vma_observer.py"):
                    relative = "engines/experiments/strength/" + module
                    changed = frozen / relative
                    changed.write_bytes(changed.read_bytes() + b"\n# changed\n")
                    with self.subTest(module=module), self.assertRaisesRegex(ValueError, "source closure changed"):
                        runtime._check_controlled_sources(context)
                    shutil.copyfile(source / relative, changed)
                    runtime._check_controlled_sources(context)
                changed = frozen / runtime.CONTROLLED_SOURCE_FILES[1]
                changed.write_bytes(changed.read_bytes() + b"\n# changed\n")
                with self.assertRaisesRegex(ValueError, "source closure changed"):
                    runtime._check_controlled_sources(context)

    @unittest.skipUnless(sys.platform == "linux", "Linux controlled memfd execution")
    def test_controlled_launcher_executes_verified_bytes_after_replacement(self):
        helper = runtime.load("controlled_peer_fixture_owner", runtime.ROOT / "engines/compact/tiny-entry-d/verify.py")
        with tempfile.TemporaryDirectory(prefix="controlled-peer-") as tmp:
            root = Path(tmp).resolve()
            work = root / "work"
            work.mkdir()
            frozen = root / "frozen"
            source_dir = frozen / "engines/experiments/strength"
            source_dir.mkdir(parents=True)
            whole = root / "fixture"
            original = (b'#!/bin/sh\n[ "$(head -n 1 "$0")" = "#!/bin/sh" ] || exit 33\n'
                        b'printf "original-ready\\n"\nread answer\n')
            whole.write_bytes(original)
            whole.chmod(0o700)
            replacement = b"#!/usr/bin/python3\nprint('wrong-image',flush=True)\n"
            (source_dir / "placement.py").write_text(
                "from pathlib import Path\n"
                "def apply_slot(slot, **kwargs):\n"
                " assert kwargs['saved_ancestor_nodes']==[2]\n"
                " Path(" + repr(str(whole)) + ").write_bytes(" + repr(replacement) + ")\n"
                " return {'effective_cpus':[0], 'observed_policy': {'mode':0}}\n")
            (source_dir / "topology.py").write_text("value = 1\n")
            slot = root / "slot.json"
            slot.write_text(json.dumps({"cpus": [0], "memory_nodes": [2]}))
            owner_file, release = root / "owner.json", root / "release"
            launcher, receipt = root / "launch", root / "placement.json"
            controlled = {"cgroup": {"path": "/sys/fs/cgroup/fake/slot-000"},
                          "slot": {"cpus": [0], "memory_nodes": [2]},
                          "saved_cpus": [0], "saved_nodes": [2], "whole_sha256": runtime.sha(original),
                          "source_pins": {"engines/experiments/strength/" + name + ".py":
                              {"sha256": runtime.sha((source_dir / (name + ".py")).read_bytes())}
                              for name in ("topology", "placement")}}
            runtime._write_launcher(launcher, whole, work, slot, receipt, frozen, owner_file, release,
                                    runtime_budget={"address_space_bytes": 4 << 30, "cpu_seconds": [180, 185]},
                                    controlled=controlled)
            compile(launcher.read_bytes(), str(launcher), "exec")
            owned = None
            try:
                owned = helper.Owned(launcher, root / "raw", helper.Budget(8))
                owner_bytes = (json.dumps(runtime.process_identity(owned.process.pid)) + "\n").encode()
                runtime.durable_new(owner_file, owner_bytes)
                runtime.durable_new(release, (runtime.sha(owner_bytes) + "\n").encode())
                owned.wait_line(b"original-ready")
                self.assertEqual(whole.read_bytes(), replacement)
                self.assertNotIn(b"wrong-image", owned.stdout.bytes())
                owned.send(b"quit\n")
                runtime._finish_peer(owned)
            finally:
                if owned is not None:
                    cleanup = owned.cleanup()
                    self.assertTrue(cleanup["owned_group_absent"] and cleanup["readers_joined"])
                self.assertFalse(helper.OWNED)

    @unittest.skipUnless(sys.platform == "linux", "Linux controlled source verification")
    def test_controlled_launcher_rejects_placement_source_change_before_exec(self):
        helper = runtime.load("controlled_changed_source_owner", runtime.ROOT / "engines/compact/tiny-entry-d/verify.py")
        with tempfile.TemporaryDirectory(prefix="controlled-peer-source-") as tmp:
            root = Path(tmp).resolve()
            work, frozen = root / "work", root / "frozen"
            work.mkdir()
            source_dir = frozen / "engines/experiments/strength"
            source_dir.mkdir(parents=True)
            for name in ("topology", "placement"):
                (source_dir / (name + ".py")).write_text("value = 1\n")
            pins = {"engines/experiments/strength/" + name + ".py":
                    {"sha256": runtime.sha((source_dir / (name + ".py")).read_bytes())}
                    for name in ("topology", "placement")}
            whole, marker = root / "fixture", root / "executed"
            whole.write_text("#!/usr/bin/python3\nfrom pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
            whole.chmod(0o700)
            slot, owner_file, release = root / "slot.json", root / "owner.json", root / "release"
            slot.write_text("{}")
            launcher = root / "launch"
            runtime._write_launcher(launcher, whole, work, slot, root / "placement.json", frozen, owner_file, release,
                runtime_budget={"address_space_bytes": 4 << 30, "cpu_seconds": [180, 185]},
                controlled={"cgroup": {"path": "/sys/fs/cgroup/fake/slot-000"}, "saved_cpus": [0],
                            "saved_nodes": [0], "slot": {}, "whole_sha256": runtime.sha(whole.read_bytes()), "source_pins": pins})
            (source_dir / "placement.py").write_text("raise RuntimeError('changed')\n")
            owned = None
            try:
                owned = helper.Owned(launcher, root / "raw", helper.Budget(8))
                deadline = time.monotonic() + 6
                while not owned.exited() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(owned.exited())
                self.assertFalse(marker.exists())
                self.assertFalse((root / "placement.json").exists())
            finally:
                if owned is not None:
                    cleanup = owned.cleanup()
                    self.assertTrue(cleanup["owned_group_absent"] and cleanup["readers_joined"])
                    self.assertIn(b"controlled placement source changed", owned.stderr.bytes())
                self.assertFalse(helper.OWNED)

    @unittest.skipUnless(sys.platform == "linux", "Linux controlled slot binding")
    def test_controlled_launcher_rejects_slot_policy_change_before_exec(self):
        helper = runtime.load("controlled_changed_slot_owner", runtime.ROOT / "engines/compact/tiny-entry-d/verify.py")
        with tempfile.TemporaryDirectory(prefix="controlled-peer-slot-") as tmp:
            root = Path(tmp).resolve()
            work, frozen = root / "work", root / "frozen"
            work.mkdir()
            source_dir = frozen / "engines/experiments/strength"
            source_dir.mkdir(parents=True)
            (source_dir / "topology.py").write_text("value=1\n")
            (source_dir / "placement.py").write_text("def apply_slot(slot,**kwargs): return {}\n")
            pins = {"engines/experiments/strength/" + name + ".py":
                    {"sha256": runtime.sha((source_dir / (name + ".py")).read_bytes())}
                    for name in ("topology", "placement")}
            whole, marker = root / "fixture", root / "executed"
            whole.write_text("#!/usr/bin/python3\nfrom pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
            whole.chmod(0o700)
            slot, owner_file, release = root / "slot.json", root / "owner.json", root / "release"
            expected = {"cpus": [0], "memory_nodes": [0], "policy": "default"}
            slot.write_text(json.dumps({**expected, "policy": "inherit"}))
            launcher = root / "launch"
            runtime._write_launcher(launcher, whole, work, slot, root / "placement.json", frozen, owner_file, release,
                runtime_budget={"address_space_bytes": 4 << 30, "cpu_seconds": [180, 185]},
                controlled={"cgroup": {"path": "/sys/fs/cgroup/fake/slot-000"}, "saved_cpus": [0],
                            "saved_nodes": [0], "slot": expected, "whole_sha256": runtime.sha(whole.read_bytes()),
                            "source_pins": pins})
            owned = None
            try:
                owned = helper.Owned(launcher, root / "raw", helper.Budget(8))
                owner_bytes = (json.dumps(runtime.process_identity(owned.process.pid)) + "\n").encode()
                runtime.durable_new(owner_file, owner_bytes)
                runtime.durable_new(release, (runtime.sha(owner_bytes) + "\n").encode())
                deadline = time.monotonic() + 6
                while not owned.exited() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(owned.exited())
                self.assertFalse(marker.exists())
                self.assertFalse((root / "placement.json").exists())
            finally:
                if owned is not None:
                    cleanup = owned.cleanup()
                    self.assertTrue(cleanup["owned_group_absent"] and cleanup["readers_joined"])
                    self.assertIn(b"controlled slot changed", owned.stderr.bytes())
                self.assertFalse(helper.OWNED)

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("xz") and shutil.which("cc"),
                         "Linux, xz and C compiler required")
    def test_controlled_launcher_runs_self_reading_compiled_source_stream(self):
        pack = runtime.load("peer_controlled_stream_fixture", runtime.ROOT / "engines/compact/tiny-a/pack_stream.py")
        source = b'#include <stdio.h>\nint main(void){puts("peer-source-stream-ok");return 0;}\n'
        whole, _ = pack.make_stream(source, ["cc", "-x", "c", "-o", "x", "-"],
                                    compiler_group=lambda script: (script, {"fixture": True}))
        helper = runtime.load("controlled_stream_owner", runtime.ROOT / "engines/compact/tiny-entry-d/verify.py")
        with tempfile.TemporaryDirectory(prefix="controlled-peer-stream-") as tmp:
            root = Path(tmp).resolve()
            work, frozen = root / "work", root / "frozen"
            work.mkdir()
            source_dir = frozen / "engines/experiments/strength"
            source_dir.mkdir(parents=True)
            target = root / "fixture"
            target.write_bytes(whole)
            target.chmod(0o700)
            (source_dir / "topology.py").write_text("value = 1\n")
            (source_dir / "placement.py").write_text(
                "from pathlib import Path\ndef apply_slot(slot, **kwargs):\n"
                " Path(" + repr(str(target)) + ").write_text('#!/bin/sh\\nexit 97\\n')\n"
                " return {'effective_cpus':[0]}\n")
            pins = {"engines/experiments/strength/" + name + ".py":
                    {"sha256": runtime.sha((source_dir / (name + ".py")).read_bytes())}
                    for name in ("topology", "placement")}
            slot, owner_file, release = root / "slot.json", root / "owner.json", root / "release"
            slot.write_text("{}")
            launcher = root / "launch"
            runtime._write_launcher(launcher, target, work, slot, root / "placement.json", frozen, owner_file, release,
                runtime_budget={"address_space_bytes": 4 << 30, "cpu_seconds": [180, 185]},
                controlled={"cgroup": {"path": "/sys/fs/cgroup/fake/slot-000"}, "saved_cpus": [0],
                            "saved_nodes": [0], "slot": {}, "whole_sha256": runtime.sha(whole), "source_pins": pins})
            owned = None
            try:
                owned = helper.Owned(launcher, root / "raw", helper.Budget(20))
                owner_bytes = (json.dumps(runtime.process_identity(owned.process.pid)) + "\n").encode()
                runtime.durable_new(owner_file, owner_bytes)
                runtime.durable_new(release, (runtime.sha(owner_bytes) + "\n").encode())
                owned.wait_line(b"peer-source-stream-ok")
                observed = runtime._finish_peer(owned)
                self.assertEqual(observed["returncode"], 0)
                self.assertNotEqual(runtime.sha(target.read_bytes()), runtime.sha(whole))
            finally:
                if owned is not None:
                    cleanup = owned.cleanup()
                    self.assertTrue(cleanup["owned_group_absent"] and cleanup["readers_joined"])
                self.assertFalse(helper.OWNED)

    def test_frozen_source_closure_lazily_binds_league_profile_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            legacy = base / "legacy"
            league = base / "league"
            old_pins = runtime._freeze(legacy)
            new_pins = runtime._freeze(league, league_required=True)
            # Controlled-only additions must not alter the legacy reference
            # closure nor retroactively qualify a stored snapshot.
            self.assertEqual(set(old_pins), set(runtime.SOURCE_FILES))
            self.assertEqual(set(new_pins), set(runtime.SOURCE_FILES + runtime.LEAGUE_SOURCE_FILES))
            owner = runtime.LEAGUE_SOURCE_FILES[0]
            self.assertNotIn(owner, old_pins)
            self.assertIn(owner, new_pins)
            runtime._verify_frozen(legacy / "source-closure", old_pins)
            runtime._verify_frozen(league / "source-closure", new_pins, league_required=True)
            frozen_registry = runtime.sibling("registry", league / "source-closure")
            self.assertEqual(Path(frozen_registry.production.__file__),
                             league / "source-closure" / "engines/scripts/production.py")
            whole = base / "fixture"
            whole.write_bytes(b"synthetic input")
            legacy_registry = runtime.sibling("registry", legacy / "source-closure")
            self.assertEqual(Path(legacy_registry.production.__file__),
                             legacy / "source-closure" / "engines/scripts/production.py")
            legacy_artifact = legacy_registry.Artifact("ice4-p4", "ice4", whole, "test", "test-p4", 4,
                128 << 20, 8, "source-jit", True, runtime.sha(whole.read_bytes()), whole.stat().st_size, "b" * 64)
            legacy_artifact.verify_bytes()
            artifact = frozen_registry.Artifact("ice4-p16", "ice4", whole, "test", "test-p16", 16,
                16 << 30, 8, "source-jit", True, runtime.sha(whole.read_bytes()), whole.stat().st_size, "b" * 64)
            artifact.verify_bytes()
            with self.assertRaisesRegex(ValueError, "source closure"):
                runtime._verify_frozen(legacy / "source-closure", old_pins, league_required=True)
            copied = league / "source-closure" / owner
            copied.write_bytes(copied.read_bytes() + b"\n# altered\n")
            with self.assertRaisesRegex(ValueError, "bound input bytes changed"):
                runtime._verify_frozen(league / "source-closure", new_pins, league_required=True)

    def test_elf_reads_actual_object_and_dependencies(self):
        elf = runtime.Elf64(elf_fixture())
        self.assertEqual(elf.pointer_symbol("table"), 0x200)
        self.assertEqual(elf.dependencies()["needed"], ["libc.so.6"])
        with self.assertRaisesRegex(ValueError, "pointer size"):
            runtime.Elf64(elf_fixture(symbol_size=4)).pointer_symbol("table")
        with self.assertRaisesRegex(ValueError, "unique"):
            elf.pointer_symbol("different")
        with self.assertRaisesRegex(ValueError, "undeclared"):
            runtime.Elf64(elf_fixture(dependency=b"libforeign.so.1")).dependencies()
        for broken in (b"notelf", elf_fixture()[:-20], elf_fixture()[:100]):
            with self.assertRaises(ValueError):
                runtime.Elf64(broken)

    @unittest.skipUnless(sys.platform == "linux", "Linux proc/device mapping ABI")
    def test_actual_pointer_and_complete_private_mapping_required(self):
        elf = runtime.Elf64(elf_fixture())
        rows = [dict(start=0x100000, end=0x102000, permissions="rw-p", offset=0, device="08:01", inode=42, path="/tmp/native"),
                dict(start=0x500000, end=0x502000, permissions="rw-p", offset=0, device="00:00", inode=0, path="")]
        with patch.object(runtime, "mappings", return_value=rows), \
             patch.object(Path, "stat", return_value=SimpleNamespace(st_ino=42, st_dev=os.makedev(8, 1))), \
             patch.object(os, "open", return_value=99), patch.object(os, "close"), \
             patch.object(os, "pread", return_value=(0x500010).to_bytes(8, "little")) as read:
            observed = runtime.runtime_tt(123, elf, "table", 4096)
            self.assertEqual(observed["pointer"], 0x500010)
            self.assertEqual(read.call_args.args, (99, 8, 0x100200))
            rows[1]["end"] = 0x500800
            with self.assertRaisesRegex(ValueError, "smaller"):
                runtime.runtime_tt(123, elf, "table", 4096)
            rows[1]["end"], rows[1]["permissions"] = 0x502000, "rw-s"
            with self.assertRaisesRegex(ValueError, "private"):
                runtime.runtime_tt(123, elf, "table", 4096)

    def test_resource_allocation_is_extracted_not_assumed_from_a_name(self):
        layout = peers.resource_layout("test-p4")
        for source, expected in ((b"auto renamed=(atomic<Entry>*)calloc(1ull<<24,8);", "renamed"),
                                 (b"Entry*Other=(Entry*)calloc(1ull<<24,8);", "Other")):
            self.assertEqual(runtime.tt_declaration(source, layout), expected)
        for source in (b"Entry*G=(Entry*)calloc(1ull<<35,8);", b"Entry*G=(Entry*)calloc(1ull<<24,16);",
                       b"Entry*G=(Entry*)calloc(1ull<<24,8); auto H=calloc(1,8);", b"G=new Entry[1<<24];"):
            with self.assertRaises(ValueError):
                runtime.tt_declaration(source, layout)

    def test_actual_worker_array_and_construction_bounds_are_both_checked(self):
        ice = b"thread c[4];for(thread&f:c)f=thread([d](){work();});"
        cake = b"jthread i[4];for(a t=0;t<4;t++)i[t]=jthread([=]{work();});"
        self.assertEqual(runtime.worker_declaration("ice4", ice, 4)["workers"], 4)
        self.assertEqual(runtime.worker_declaration("c4ke", cake, 4)["workers"], 4)
        for peer, source in (("ice4", ice.replace(b"[4]", b"[256]")),
                             ("c4ke", cake.replace(b"t<4", b"t<256")),
                             ("c4ke", cake.replace(b"[4]", b"[256]"))):
            with self.assertRaisesRegex(ValueError, "TEST profile"):
                runtime.worker_declaration(peer, source, 4)

    def test_bestmove_and_optional_ponder_are_independently_legal(self):
        oracle = runtime.load("peer_reply_oracle", runtime.ROOT / "engines/tests/chess_oracle.py")
        board = oracle.Board.from_fen()
        self.assertEqual(runtime.checked_best(b"bestmove e2e4", board), "e2e4")
        self.assertEqual(runtime.checked_best(b"bestmove e2e4 ponder e7e5", board), "e2e4")
        for line in (b"bestmove e2e5", b"bestmove e2e4 junk e7e5", b"bestmove e2e4 ponder a7a1", b"bestmove e2e4 extra"):
            with self.assertRaises(ValueError):
                runtime.checked_best(line, board)

    @unittest.skipUnless(sys.platform == "linux", "Linux production scope helper")
    def test_shared_promotion_fixture_interface_keeps_all_nbrq_cases(self):
        oracle = runtime.load("peer_fixture_oracle", runtime.ROOT / "engines/tests/chess_oracle.py")
        scope = runtime.load("peer_fixture_scope", runtime.ROOT / "engines/experiments/tcec-scope/verify.py")
        rows = scope.promotion_fixtures(oracle)
        self.assertEqual({label for label, moves, board in rows},
                         {"white-n", "white-b", "white-r", "white-q", "black-n", "black-b", "black-r"})
        for label, moves, board in rows:
            replayed = runtime._replay(oracle, moves)
            self.assertEqual({str(move) for move in replayed.legal_moves()}, {str(move) for move in board.legal_moves()})
            self.assertTrue(replayed.in_check(replayed.turn), label)

    def test_test_slot_requires_actual_distinct_physical_cores(self):
        host = topology.Topology(tuple(topology.Cpu(i, 0, i % 4, 0, (i % 4, i % 4 + 4)) for i in range(8)),
                                 tuple(range(8)), (0,), {"0": [10]}, "test")
        slot = {"cpus": [0, 1, 2, 3], "memory_nodes": [0], "workers": 4, "smt": False}
        self.assertTrue(runtime.validate_slot(host, slot, peers.resource_layout("test-p4"))["qualified"])
        actual_slot = topology.Slot("slot-000", (0, 1, 2, 3), tuple((0, core) for core in range(4)),
                                    (0,), 4, False).to_record()
        self.assertTrue(runtime.validate_slot(host, actual_slot, peers.resource_layout("test-p4"))["qualified"])
        slot.update(cpus=[0, 4, 1, 5], smt=True)
        with self.assertRaisesRegex(ValueError, "physical TEST"):
            runtime.validate_slot(host, slot, peers.resource_layout("test-p4"))
        functional = runtime.validate_slot(host, slot, peers.resource_layout("test-p4"), allow_functional=True)
        self.assertFalse(functional["qualified"])
        self.assertEqual(functional["physical_cores"], 2)
        slot["cpus"] = [0, 9]
        with self.assertRaisesRegex(ValueError, "outside"):
            runtime.validate_slot(host, slot, peers.resource_layout("test-p4"), allow_functional=True)

    def test_smt_profile_geometry_remains_diagnostic_until_runtime_is_bound(self):
        cpus = tuple(topology.Cpu(logical, core // 48, core, core // 48,
                                  (core, core + 96))
                     for core in range(96) for logical in (core, core + 96))
        host = topology.Topology(cpus, tuple(cpu.id for cpu in cpus), (0, 1),
                                 {"0": [10, 20], "1": [20, 10]}, "fixture")
        slot16 = {"cpus": [v for core in range(8) for v in (core, core + 96)],
                  "memory_nodes": [0], "workers": 16, "smt": True}
        layout16 = {"id": "test-p16", "workers": 16}
        with self.assertRaisesRegex(ValueError, "diagnostic only"):
            runtime.validate_slot(host, slot16, layout16)
        observed = runtime.validate_slot(host, slot16, layout16, allow_functional=True)
        self.assertEqual((observed["physical_cores"], observed["logical_cpus"]), (8, 16))
        self.assertEqual(observed["memory_nodes"], [0])
        self.assertFalse(observed["qualified"])

        slot192 = {"cpus": list(host.allowed_cpus), "memory_nodes": [0, 1],
                   "workers": 192, "smt": True}
        layout192 = {"id": "test-p192", "workers": 192}
        result = runtime.validate_slot(host, slot192, layout192, allow_functional=True)
        self.assertEqual((result["physical_cores"], result["logical_cpus"]), (96, 192))
        self.assertFalse(result["qualified"])

        # Same counts and physical cores are not enough if the observed
        # sibling declaration is inconsistent with the selected pair.
        broken = list(cpus)
        broken[0] = topology.Cpu(0, 0, 0, 0, (0,))
        bad_host = topology.Topology(tuple(broken), host.allowed_cpus, host.allowed_nodes,
                                     host.distances, host.kernel)
        with self.assertRaisesRegex(ValueError, "symmetric observed sibling"):
            runtime.validate_slot(bad_host, slot16, layout16, allow_functional=True)

        mixed = {**slot16, "cpus": [v for core in (*range(4), *range(48, 52))
                                     for v in (core, core + 96)], "memory_nodes": [0, 1]}
        with self.assertRaisesRegex(ValueError, "one actual NUMA node"):
            runtime.validate_slot(host, mixed, layout16, allow_functional=True)

        extra = topology.Cpu(999, 2, 999, 2, (999,))
        wider = topology.Topology((*host.cpus, extra), (*host.allowed_cpus, 999),
                                  (0, 1, 2), host.distances, host.kernel)
        with self.assertRaisesRegex(ValueError, "entire allowed CPU envelope"):
            runtime.validate_slot(wider, slot192, layout192, allow_functional=True)

    def test_new_smt_profiles_reject_before_peer_process_launch(self):
        with tempfile.TemporaryDirectory(prefix="rove-peer-smt-reject-") as directory:
            reference = Path(directory).resolve() / "reference.json"
            out = Path(directory).resolve() / "out"
            for profile, workers in (("test-p16", 16), ("test-p192", 192)):
                with self.subTest(profile=profile):
                    layout = {"id": profile, "workers": workers}
                    ref = {"format": "rove4k-peer-reference-v1", "complete": True,
                           "engines_executed": 0, "peer": "ice4", "resources": layout,
                           "build": {"path": "unused", "sha256": "unused"}, "source_inputs": []}
                    admitted = {"peer": "ice4", "layout": layout}
                    with patch.object(runtime.sys, "platform", "linux"), \
                            patch.dict(runtime.os.environ, {"LD_PRELOAD": "", "LD_AUDIT": "", "LD_LIBRARY_PATH": ""}), \
                            patch.object(runtime, "read_record", return_value=(ref, "digest")), \
                            patch.object(runtime, "_verify_frozen") as verify, \
                            patch.object(runtime, "validate_build", return_value=admitted) as build, \
                            patch.object(runtime, "construct_owned") as launch:
                        with self.assertRaisesRegex(ValueError, "explicit functional-only opt-in"):
                            runtime.qualify_peer(reference, out, {}, allow_functional=False)
                        with self.assertRaisesRegex(ValueError, "controlled cgroup ownership and source identity"):
                            runtime.qualify_peer(reference, out, {}, allow_functional=True)
                        verify.assert_not_called()
                        build.assert_not_called()
                        launch.assert_not_called()
                        self.assertFalse(out.exists())

    def test_large_peer_budget_records_available_memory_and_enforces_inherited_limits(self):
        layout = {"id": "test-p16", "workers": 16, "tt_bytes": 16 << 30}
        cpus = list(range(16))
        required = (17 << 30)
        available = {"effective_available_bytes": required}
        parents = {"address_space": [-1, -1], "cpu": [-1, -1]}
        result = runtime.peer_runtime_budget(layout, cpus=cpus, wall_seconds=180,
                                             availability=available, parent_limits=parents)
        self.assertEqual(result["required_available_bytes"], required)
        self.assertEqual(result["address_space_bytes"], (16 << 30) + (768 << 20))
        self.assertEqual(result["cpu_seconds"], [2240, 2272])
        with self.assertRaisesRegex(ValueError, "finite resource profile"):
            runtime.peer_runtime_budget({**layout, "tt_bytes": (16 << 30) + 1}, cpus=cpus,
                wall_seconds=180, availability=available, parent_limits=parents)
        exact = {"address_space": [result["address_space_bytes"]] * 2,
                 "cpu": [result["cpu_seconds"][1]] * 2}
        self.assertEqual(runtime.peer_runtime_budget(layout, cpus=cpus, wall_seconds=180,
            availability=available, parent_limits=exact)["cpu_seconds"], [2240, 2272])
        for observed in (required - 1, 0, -1, None):
            record = {"effective_available_bytes": observed}
            result_low = runtime.peer_runtime_budget(layout, cpus=cpus, wall_seconds=180,
                availability=record, parent_limits=parents)
            self.assertEqual(result_low["availability"], record)
            self.assertFalse(result_low["current_availability_enforced"])
        for field, index in (("cpu", 0), ("cpu", 1), ("address_space", 0), ("address_space", 1)):
            changed = {name: list(pair) for name, pair in exact.items()}
            changed[field][index] -= 1
            with self.subTest(field=field, index=index), self.assertRaisesRegex(ValueError, "inherited"):
                runtime.peer_runtime_budget(layout, cpus=cpus, wall_seconds=180,
                                            availability=available, parent_limits=changed)
        for bad_cpus in (cpus[:-1], [0] * 16, cpus[:-1] + [True]):
            with self.subTest(cpus=bad_cpus), self.assertRaisesRegex(ValueError, "logical CPU envelope"):
                runtime.peer_runtime_budget(layout, cpus=bad_cpus, wall_seconds=180,
                                            availability=available, parent_limits=parents)
        big = {"id": "test-p192", "workers": 192, "tt_bytes": 192 << 30}
        observed = runtime.peer_runtime_budget(big, cpus=list(range(192)), wall_seconds=180,
            availability={"effective_available_bytes": (192 << 30) + (3328 << 20)}, parent_limits=parents)
        self.assertEqual(observed["required_available_bytes"], (192 << 30) + (3328 << 20))
        self.assertEqual(observed["cpu_seconds"], [26880, 27264])

    def test_p192_peer_budget_requires_exact_192g_and_enforces_each_limit(self):
        layout = {"id": "test-p192", "workers": 192, "tt_bytes": 192 << 30}
        cpus = list(range(192))
        required = (192 << 30) + (3328 << 20)
        address_space = (192 << 30) + (3072 << 20)
        availability = {"effective_available_bytes": required}
        exact = {"address_space": [address_space, address_space], "cpu": [27264, 27264]}
        result = runtime.peer_runtime_budget(layout, cpus=cpus, wall_seconds=180,
                                            availability=availability, parent_limits=exact)
        self.assertEqual(result["tt_bytes"], 192 << 30)
        self.assertEqual(result["required_available_bytes"], required)
        self.assertEqual(result["address_space_bytes"], address_space)
        self.assertEqual(result["cpu_seconds"], [26880, 27264])
        for invalid_workers in (191, 192.0, True):
            with self.subTest(workers=invalid_workers), self.assertRaisesRegex(ValueError, "unsupported large peer runtime profile"):
                runtime.peer_runtime_budget({**layout, "workers": invalid_workers}, cpus=cpus,
                                            wall_seconds=180, availability=availability, parent_limits=exact)
        for size in (128 << 30, (192 << 30) - 1, (192 << 30) + 1, True):
            with self.subTest(tt_bytes=size), self.assertRaisesRegex(ValueError, "finite resource profile"):
                runtime.peer_runtime_budget({**layout, "tt_bytes": size}, cpus=cpus,
                    wall_seconds=180, availability=availability, parent_limits=exact)
        result_low = runtime.peer_runtime_budget(layout, cpus=cpus, wall_seconds=180,
            availability={"effective_available_bytes": 0}, parent_limits=exact)
        self.assertFalse(result_low["current_availability_enforced"])
        for field, index in (("cpu", 0), ("cpu", 1), ("address_space", 0), ("address_space", 1)):
            changed = {name: list(pair) for name, pair in exact.items()}
            changed[field][index] -= 1
            with self.subTest(field=field, index=index), self.assertRaisesRegex(ValueError, "inherited"):
                runtime.peer_runtime_budget(layout, cpus=cpus, wall_seconds=180,
                                            availability=availability, parent_limits=changed)
        for bad_cpus in (cpus[:-1], [0] * 192, cpus[1:] + [False]):
            with self.subTest(cpus=bad_cpus), self.assertRaisesRegex(ValueError, "logical CPU envelope"):
                runtime.peer_runtime_budget(layout, cpus=bad_cpus, wall_seconds=180,
                                            availability=availability, parent_limits=exact)
        for invalid_wall in (59, 601, True):
            with self.subTest(wall_seconds=invalid_wall), self.assertRaisesRegex(ValueError, "bounded peer wall time"):
                runtime.peer_runtime_budget(layout, cpus=cpus, wall_seconds=invalid_wall,
                                            availability=availability, parent_limits=exact)

    def test_child_rechecks_inherited_limits_without_raising_them(self):
        resource = SimpleNamespace(RLIM_INFINITY=-1, getrlimit=Mock(return_value=(400, 500)),
                                   setrlimit=Mock())
        self.assertEqual(runtime.checked_child_limit(resource, 7, 200, 300), [400, 500])
        resource.setrlimit.assert_called_once_with(7, (200, 300))
        for inherited in ((299, 500), (400, 299)):
            resource.getrlimit.return_value = inherited
            resource.setrlimit.reset_mock()
            with self.assertRaisesRegex(ValueError, "inherited child limit"):
                runtime.checked_child_limit(resource, 7, 200, 300)
            resource.setrlimit.assert_not_called()

    def test_peer_availability_observes_all_cgroup_ancestors(self):
        with tempfile.TemporaryDirectory(prefix="rove-peer-available-") as directory:
            root = Path(directory)
            proc, cgroup = root / "proc", root / "cgroup"
            (proc / "self").mkdir(parents=True)
            (proc / "meminfo").write_text("MemAvailable: 2000 kB\n")
            (proc / "self" / "cgroup").write_text("0::/a/b\n")
            (cgroup / "a" / "b").mkdir(parents=True)
            for relative, maximum, current in (("a", "1500000", "300000"),
                                                ("a/b", "1000000", "300000")):
                (cgroup / relative / "memory.max").write_text(maximum)
                (cgroup / relative / "memory.current").write_text(current)
            result = runtime.effective_available_bytes(proc, cgroup)
            self.assertEqual(result["host_available_bytes"], 2000 * 1024)
            self.assertEqual(result["effective_available_bytes"], 700000)
            (proc / "meminfo").write_text("MemAvailable: 0 kB\n")
            (cgroup / "a" / "b" / "memory.current").write_text("1000001")
            exhausted = runtime.effective_available_bytes(proc, cgroup)
            self.assertEqual(exhausted["host_available_bytes"], 0)
            self.assertEqual(exhausted["effective_available_bytes"], -1)
            (proc / "self" / "cgroup").write_text("0::/\n")
            with self.assertRaisesRegex(ValueError, "root-only cgroup namespace"):
                runtime.effective_available_bytes(proc, cgroup)
            (cgroup / "memory.max").write_text("max")
            (cgroup / "memory.current").write_text("0")
            with self.assertRaisesRegex(ValueError, "root-only cgroup namespace"):
                runtime.effective_available_bytes(proc, cgroup)
            (cgroup / "memory.max").unlink()
            (cgroup / "memory.current").unlink()
            (proc / "self" / "cgroup").write_text("0::/a/b\n")
            (cgroup / "a" / "memory.max").unlink()
            with self.assertRaisesRegex(ValueError, "ancestor memory limit or usage"):
                runtime.effective_available_bytes(proc, cgroup)
            (cgroup / "a" / "memory.max").write_text("1500000")
            (cgroup / "a" / "memory.current").write_text("bad")
            with self.assertRaisesRegex(ValueError, "invalid current cgroup"):
                runtime.effective_available_bytes(proc, cgroup)

    @unittest.skipUnless(sys.platform == "linux", "Linux resource limits")
    def test_peer_budget_refresh_records_low_or_unavailable_memory_without_blocking(self):
        layout = {"id": "test-p16", "workers": 16, "tt_bytes": 16 << 30}
        enough = {"effective_available_bytes": 17 << 30}
        reduced = {"effective_available_bytes": (17 << 30) - 1}
        with patch.object(runtime, "effective_available_bytes", side_effect=[enough, reduced, ValueError("unavailable")]) as available, \
                patch("resource.getrlimit", return_value=(-1, -1)) as limits:
            first = runtime.observed_peer_runtime_budget(layout, cpus=list(range(16)), wall_seconds=180)
            self.assertEqual(first["required_available_bytes"], 17 << 30)
            second = runtime.observed_peer_runtime_budget(layout, cpus=list(range(16)), wall_seconds=180)
            third = runtime.observed_peer_runtime_budget(layout, cpus=list(range(16)), wall_seconds=180)
            self.assertEqual(second["availability"], reduced)
            self.assertFalse(second["current_availability_enforced"])
            self.assertEqual(third["availability"]["status"], "unavailable")
        self.assertEqual(available.call_count, 3)
        self.assertEqual(limits.call_count, 6)

    def test_worker_and_tt_numa_evidence_are_identity_bound_and_scoped(self):
        with tempfile.TemporaryDirectory(prefix="rove-peer-evidence-") as directory:
            proc = Path(directory)
            task = proc / "123" / "task" / "7"
            task.mkdir(parents=True)
            fields = ["0"] * 20
            fields[0], fields[11], fields[12], fields[19] = "S", "12", "3", "80"
            (task / "stat").write_text("7 (worker name) " + " ".join(fields))
            with patch.object(runtime.os, "sched_getaffinity", return_value={10, 11}):
                worker = runtime._worker_evidence(123, 7, proc=proc)
            self.assertEqual(worker, {"tid": 7, "start_ticks": 80, "cpus": [10, 11],
                                      "cpu_ticks_first": 15, "cpu_ticks_last": 15})

            (proc / "123" / "numa_maps").write_text(
                "100 default anon=8 N0=3 N1=5 kernelpagesize_kB=4\n"
                "900 default anon=1 N0=1 kernelpagesize_kB=4\n")
            owner = {"pid": 123, "pgid": 123, "session": 123, "start_ticks": 10}
            mapping = {"pointer": 0x110, "mappings": [{"start": 0x100, "end": 0x200}]}
            with patch.object(runtime, "process_identity", return_value=owner), \
                    patch.object(runtime, "runtime_tt", return_value=mapping):
                result = runtime._tt_numa_after_search(123, None, "tt", 64, owner, 0x110, proc=proc)
            self.assertEqual(result["observed_page_nodes"], [0, 1])
            self.assertTrue(result["all_mapping_starts_observed"])
            self.assertEqual(result["tt_overlapping_vmas"][0]["node_pages"], {0: 3, 1: 5})
            self.assertIn("may include non-TT pages", result["scope"])
            with patch.object(runtime, "process_identity", return_value={**owner, "start_ticks": 11}):
                with self.assertRaisesRegex(ValueError, "owner changed"):
                    runtime._tt_numa_after_search(123, None, "tt", 64, owner, 0x110, proc=proc)

    def test_official_native_and_missing_producer_cannot_reach_execution(self):
        with tempfile.TemporaryDirectory(prefix="rove-peer-reject-") as directory:
            receipt = Path(directory) / "peer.json"
            value = {"peer": "ice4", "revision": peers.peer_spec("ice4").revision,
                     "resources": peers.resource_layout("test-p4"), "artifact_kind": "official-tiny"}
            for kind in ("official-tiny", "configurable-native"):
                value["artifact_kind"] = kind
                receipt.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, "only pinned resource-only"):
                    runtime.validate_build(receipt)
            value.update(artifact_kind="resource-tiny", complete=True, reproducible=True, attempts=[{}, {}],
                         feature_policy={"upstream_tiny": True, "generated_promotions": ["q"], "nbrq_replay_qualified": False})
            receipt.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "frozen producer"):
                runtime.validate_build(receipt)

    def test_protected_inputs_are_refused_before_read(self):
        with patch.object(Path, "read_bytes", side_effect=AssertionError("must not read")):
            for name in (".env", ".env.production", "credentials.json", "inventory.json", "service-account.json", "id_rsa", "api_key.txt"):
                with self.assertRaisesRegex(ValueError, "non-source or secret"):
                    runtime.ordinary(Path(tempfile.gettempdir()) / name)

    def test_constructor_interruption_retains_registered_owner(self):
        marker = SimpleNamespace(registered=False)
        class Helper:
            @staticmethod
            def Owned(*args):
                marker.registered = True
                runtime.bounded_signal(signal.SIGINT, None)
                return marker
        try:
            with self.assertRaises(KeyboardInterrupt):
                runtime.construct_owned(Helper, None, None, None)
            self.assertTrue(marker.registered)
            self.assertFalse(runtime.CONSTRUCTING_OWNED)
        finally:
            runtime.DEFERRED_SIGNAL = None

    def test_signal_handlers_restore_after_failure(self):
        before = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
        @runtime.owned_signals
        def cancelled():
            raise RuntimeError("fault")
        with self.assertRaisesRegex(RuntimeError, "fault"):
            cancelled()
        self.assertEqual(before, {number: signal.getsignal(number) for number in before})

    @unittest.skipUnless(sys.platform == "linux", "Linux build process observation")
    def test_exact_build_stdin_and_original_process_settlement(self):
        with tempfile.TemporaryDirectory(prefix="rove-peer-stdin-") as directory:
            source = b"exact source <stdin>\n\0\xff"
            work = Path(directory) / "work"
            work.mkdir()
            allowed = os.sched_getaffinity(0)
            cpu = 5 if 5 in allowed else min(allowed)
            stdout, stderr, record = peers.bounded_run([sys.executable, "-c", "import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())"],
                work, cpu=cpu, timeout=5, input_bytes=source)
            self.assertEqual(stdout, source)
            self.assertEqual(stderr, b"")
            self.assertEqual(record["stdin"], {"bytes": len(source), "sha256": runtime.sha(source)})
            self.assertTrue(record["leader_reaped"] and record["group_absent"])
            self.assertFalse(record["forced_cleanup"])

    @unittest.skipUnless(sys.platform == "linux", "Linux original-owner settlement")
    def test_delayed_child_keeps_original_leader_unreaped_until_group_settles(self):
        self._lifecycle_fixture(.2, False)

    @unittest.skipUnless(sys.platform == "linux", "Linux physical fault cleanup")
    def test_delayed_child_timeout_is_failure_and_kills_only_owned_group(self):
        self._lifecycle_fixture(3, True)

    @unittest.skipUnless(sys.platform == "linux", "Linux durable pre-exec gate")
    def test_no_fixture_exec_before_durable_original_owner_release(self):
        helper = runtime.load("peer_gate_owner", runtime.ROOT / "engines/compact/tiny-entry-d/verify.py")
        host = topology.Topology.snapshot()
        cpu = next(row for row in host.cpus if row.id == (5 if 5 in host.allowed_cpus else min(host.allowed_cpus)))
        with tempfile.TemporaryDirectory(prefix="rove-peer-gate-") as directory:
            directory = Path(directory)
            temporary = directory / "tmp"
            temporary.mkdir()
            marker, whole = directory / "executed", directory / "fixture"
            whole.write_text("#!/usr/bin/python3\nfrom pathlib import Path\n"
                "Path(" + repr(str(marker)) + ").write_text('executed')\nprint('ready',flush=True)\ninput()\n")
            whole.chmod(0o700)
            slot, owner_path, release = directory / "slot.json", directory / "owner.json", directory / "release"
            slot.write_text(json.dumps({"cpus": [cpu.id], "memory_nodes": [cpu.node], "workers": 1, "smt": False, "policy": "inherit"}))
            launch = directory / "launch"
            runtime._write_launcher(launch, whole, temporary, slot, directory / "placement.json", runtime.ROOT, owner_path, release)
            compile(launch.read_bytes(), str(launch), "exec")
            owned = None
            try:
                owned = helper.Owned(launch, directory / "raw", helper.Budget(5))
                time.sleep(.05)
                self.assertFalse(marker.exists())
                owner_bytes = (json.dumps(runtime.process_identity(owned.process.pid)) + "\n").encode()
                runtime.durable_new(owner_path, owner_bytes)
                runtime.durable_new(release, (runtime.sha(owner_bytes) + "\n").encode())
                owned.wait_line(b"ready")
                self.assertTrue(marker.exists())
                owned.send(b"quit\n")
                runtime._finish_peer(owned)
            finally:
                if owned is not None:
                    cleanup = owned.cleanup()
                    self.assertTrue(cleanup["owned_group_absent"] and cleanup["readers_joined"])
                    self.assertFalse(cleanup["forced_cleanup"])
                self.assertFalse(helper.OWNED)

    @unittest.skipUnless(sys.platform == "linux", "Linux actual ELF pointer observation")
    def test_real_allocating_fixture_matches_symbol_pointer_and_private_extent(self):
        # A chess-free helper proves PIE/symbol/proc handling independently of
        # the mock ELF writer. It allocates 8MiB and never produces admission.
        helper = runtime.load("peer_tt_owner", runtime.ROOT / "engines/compact/tiny-entry-d/verify.py")
        with tempfile.TemporaryDirectory(prefix="rove-peer-elf-") as directory:
            directory = Path(directory)
            work = directory / "work"
            work.mkdir()
            native = work / "fixture"
            source = (b"#include <cstdlib>\n#include <cstdio>\n"
                      b"void*table=calloc(1ull<<20,8);int main(){puts(\"ready\");fflush(stdout);getchar();}\n")
            allowed = os.sched_getaffinity(0)
            peers.bounded_run(["g++", "-O2", "-xc++", "-o" + str(native), "-"], work,
                              cpu=5 if 5 in allowed else min(allowed), timeout=15, input_bytes=source)
            elf = runtime.Elf64(native.read_bytes())
            owned = None
            try:
                owned = helper.Owned(native, directory / "raw", helper.Budget(5))
                owned.wait_line(b"ready")
                observed = runtime.runtime_tt(owned.process.pid, elf, "table", 8 << 20)
                self.assertEqual(observed["tt_bytes"], 8 << 20)
                self.assertTrue(observed["mapping_extent_verified"])
                self.assertGreater(observed["pointer"], 0)
                owned.send(b"q\n")
                runtime._finish_peer(owned)
            finally:
                if owned is not None:
                    cleanup = owned.cleanup()
                    self.assertTrue(cleanup["owned_group_absent"] and cleanup["readers_joined"])
                    self.assertFalse(cleanup["forced_cleanup"])
                self.assertFalse(helper.OWNED)

    def _lifecycle_fixture(self, child_delay, timeout):
        helper = runtime.load("peer_fixture_owner", runtime.ROOT / "engines/compact/tiny-entry-d/verify.py")
        with tempfile.TemporaryDirectory(prefix="rove-peer-lifecycle-") as directory:
            directory = Path(directory)
            script = directory / "fixture"
            script.write_text("#!/usr/bin/python3\nimport os,sys,time\n"
                "child=os.fork()\nif child==0:\n time.sleep(" + str(child_delay) + ");os._exit(0)\n"
                "sys.stdout.write('ready\\n');sys.stdout.flush()\n"
                "sys.stderr.write('fixture compiler diagnostic\\n');sys.stderr.flush()\n"
                "sys.stdin.readline();os._exit(0)\n")
            script.chmod(0o700)
            owned = None
            try:
                owned = helper.Owned(script, directory / "raw", helper.Budget(5))
                owned.wait_line(b"ready")
                owned.send(b"quit\n")
                if timeout:
                    with self.assertRaisesRegex(ValueError, "did not physically settle"):
                        runtime._finish_peer(owned, seconds=.1)
                    self.assertFalse(owned.reaped)
                else:
                    observed = runtime._finish_peer(owned)
                    self.assertTrue(observed["leader_exited_with_other_members"])
                    self.assertTrue(observed["original_identity_retained_until_other_members_absent"])
                    self.assertGreater(observed["stderr_bytes"], 0)
            finally:
                if owned is not None:
                    cleanup = owned.cleanup()
                    self.assertTrue(cleanup["owned_group_absent"] and cleanup["readers_joined"])
                    self.assertEqual(cleanup["forced_cleanup"], timeout)
                self.assertFalse(helper.OWNED)


if __name__ == "__main__":
    unittest.main()
