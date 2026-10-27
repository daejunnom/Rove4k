#!/usr/bin/env python3
"""Pure cancellation recipe/identity/receipt checks; never invoke its driver."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("test_elf_cancel_source", HERE / "elf_profile_cancel.py")
cancel = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cancel
exec(compile((HERE / "elf_profile_cancel.py").read_bytes().replace(b"\r\n", b"\n"),
             str(HERE / "elf_profile_cancel.py"), "exec", dont_inherit=True), cancel.__dict__)


def chain():
    return [dict(pid=100 + i, ppid=99 + i, pgid=100 + i if i < 5 else 104,
                 session=100 + i if i < 5 else 104, state="S", start_ticks=1234 + i) for i in range(6)]


def receipts():
    return [dict(format=1, **{"class": kind}, complete=False,
        host_cleanup={"unsettled_commands": 0, "errors": []}, commands=[dict(kind=kind_name,
            started=True, terminal=True, reaped=True, owned_group_absent=True, forced_cleanup=True,
            other_group_members_before_reap=[], original_identity_retained_until_other_members_absent=True,
            returncode=-15, pid=101 + index, pgid=101 + index)])
        for index, (_, kind, kind_name) in enumerate(cancel.RECEIPTS)]


class CancelTests(unittest.TestCase):
    def test_execute_guard_precedes_any_output_or_capture(self):
        with self.assertRaisesRegex(ValueError, "explicit --execute"):
            cancel.run(Path("/never-created"))
        self.assertEqual(cancel.plan()["modes"], ["term", "ignore-term"])
        self.assertFalse(cancel.plan()["production_grace_changed"])
        self.assertFalse(cancel.plan()["native_or_ELF_qualified"])

    def test_wrapper_is_finite_python_source_without_shell_or_payload(self):
        for mode in cancel.MODES:
            source = cancel.wrapper_source("/usr/bin/python3", "/usr/bin/cc", "/owned/ready.json", mode)
            self.assertTrue(source.startswith(b"#!/usr/bin/python3\n"))
            self.assertIn(b"os.execv(compiler, [compiler, *args])", source)
            self.assertIn(b"stdin_consumed=False", source)
            self.assertIn(b"signal.SIG_IGN", source)
            self.assertNotIn(b"subprocess", source)
            self.assertNotIn(b"shell=", source)
            self.assertNotIn(b"@", source)
        for values in (("python", "/cc", "/ready", "term"), ("/python", "/cc", "/ready", "other"),
                       ("/python with spaces", "/cc", "/ready", "term"), ("/python", "/cc\n", "/ready", "term")):
            with self.assertRaises(ValueError):
                cancel.wrapper_source(*values)

    def test_exact_six_node_non_F8_chain(self):
        values = chain()
        ready = {key: values[-1][key] for key in ("pid", "ppid", "pgid", "start_ticks")}
        self.assertEqual(cancel.validate_chain(values, 100, ready), values)
        for field, value in (("ppid", 1), ("pgid", 105), ("session", 105), ("state", "Z"), ("start_ticks", True)):
            bad = copy.deepcopy(values)
            bad[-1][field] = value
            with self.assertRaises(ValueError, msg=field):
                cancel.validate_chain(bad, 100, ready)
        with self.assertRaises(ValueError):
            cancel.validate_chain(values[:-1], 100, ready)
        with self.assertRaises(ValueError):
            cancel.validate_chain(values, 100, {**ready, "start_ticks": 999})

    def test_proc_stat_does_not_parse_command_line_or_environment(self):
        fields = [b"S", b"12", b"13", b"14", *([b"0"] * 15), b"456"]
        parsed = cancel.parse_stat(b"15 (name with ) spaces) " + b" ".join(fields), 15)
        self.assertEqual(parsed, dict(pid=15, state="S", ppid=12, pgid=13, session=14, start_ticks=456))
        for data, pid in ((b"15 (x) S", 15), (b"16 (x) " + b" ".join(fields), 15), (b"invalid", 15)):
            with self.assertRaises(ValueError):
                cancel.parse_stat(data, pid)

    def test_actual_failed_owner_receipts_are_required(self):
        records = receipts()
        self.assertTrue(cancel.validate_receipts(records))
        for field, value in (("complete", True), ("format", True), ("host_cleanup", {"unsettled_commands": 1, "errors": []})):
            bad = copy.deepcopy(records)
            bad[1][field] = value
            with self.assertRaises(ValueError, msg=field):
                cancel.validate_receipts(bad)
        for field, value in (("returncode", 0), ("returncode", True), ("reaped", False),
                             ("forced_cleanup", False), ("owned_group_absent", False),
                             ("other_group_members_before_reap", [{"pid": 999}])):
            bad = copy.deepcopy(records)
            bad[-1]["commands"][0][field] = value
            with self.assertRaises(ValueError, msg=field):
                cancel.validate_receipts(bad)
        with self.assertRaises(ValueError):
            cancel.validate_receipts(records[:-1])


if __name__ == "__main__":
    unittest.main()
