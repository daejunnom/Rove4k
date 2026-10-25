#!/usr/bin/env python3
"""Boundary/fault checks for peer qualification; mocks never qualify a player."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import struct
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

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
        slot.update(cpus=[0, 4, 1, 5], smt=True)
        with self.assertRaisesRegex(ValueError, "physical TEST"):
            runtime.validate_slot(host, slot, peers.resource_layout("test-p4"))
        functional = runtime.validate_slot(host, slot, peers.resource_layout("test-p4"), allow_functional=True)
        self.assertFalse(functional["qualified"])
        self.assertEqual(functional["physical_cores"], 2)
        slot["cpus"] = [0, 9]
        with self.assertRaisesRegex(ValueError, "outside"):
            runtime.validate_slot(host, slot, peers.resource_layout("test-p4"), allow_functional=True)

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
