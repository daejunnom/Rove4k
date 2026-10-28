"""Pure static-report JSON and type checks; ELF symbol lookup is a fixture."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rove_b_static_tt as subject


class StaticJsonTest(unittest.TestCase):
    def setUp(self):
        self.source = (b"#define qN ((size_t)1<<29)\nzb*qq;"
                       b"qq=aligned_alloc(4096,qN*sizeof*qq);qq+(a&(qN-1))")
        self.native = b"synthetic native, ELF lookup is mocked"
        self.options = dict(profile="test-p16", source=self.source, native=self.native,
                            manifest={"compiler": subject.COMMAND},
                            compiler_sha="a" * 64, linker_sha="b" * 64)
        self.report = {
            "schema": "rove4k.b-static-candidate.v1", "family": "B", "profile": "test-p16",
            "source": {"bytes": len(self.source), "sha256": hashlib.sha256(self.source).hexdigest()},
            "native": {"bytes": len(self.native), "sha256": hashlib.sha256(self.native).hexdigest()},
            "compiler_sha256": "a" * 64, "linker_sha256": "b" * 64,
            "compiler_command": subject.COMMAND, "source_recompiled_native_identical": True,
            "entry_bytes_compile_assertion": 24, "candidate_symbol": "qq",
            "candidate_symbol_value": 4096, "candidate_tt_bytes": 24 << 29,
            "source_allocation_alignment": 4096, "engine_executed": False,
            "live_pointer_observed": False, "tt_semantics_proven": False,
            "physical_placement_qualified": False, "runtime_qualified": False,
            "playing_strength_qualified": False,
        }
        self.elf = mock.patch.object(subject.peer_runtime, "Elf64", return_value=object())
        self.symbol = mock.patch.object(subject.rove_b_tt_observe, "_symbol_value", return_value=4096)
        self.elf.start()
        self.symbol.start()
        self.addCleanup(self.elf.stop)
        self.addCleanup(self.symbol.stop)

    def encode(self, report=None):
        return json.dumps(self.report if report is None else report).encode()

    def test_valid_report_has_no_runtime_or_producer_qualification(self):
        result = subject.validate_report_bytes(self.encode(), **self.options)
        self.assertEqual((result["symbol"], result["elf_symbol_offset"]), ("qq", 4096))
        self.assertFalse(result["producer_authenticated"])
        self.assertFalse(result["tt_semantics_proven"])
        self.assertFalse(result["compiler_replay_independently_verified"])

    def test_rejects_duplicate_top_level_and_nested_keys(self):
        raw = self.encode()
        cases = (raw[:-1] + b',"runtime_qualified":false}',
                 raw.replace(b'"source": {', b'"source": {"bytes":0,', 1))
        for value in cases:
            with self.subTest(raw=value), self.assertRaisesRegex(ValueError, "duplicate"):
                subject.validate_report_bytes(value, **self.options)

    def test_rejects_nonfinite_values(self):
        for literal in (b"NaN", b"Infinity", b"-Infinity"):
            with self.subTest(literal=literal), self.assertRaisesRegex(ValueError, "non-finite"):
                subject.validate_report_bytes(b'{"value":' + literal + b'}', **self.options)

    def test_rejects_boolean_integer_substitution_and_wrong_types(self):
        for field, value in (("engine_executed", 0),
                             ("source_recompiled_native_identical", 1),
                             ("candidate_symbol_value", True),
                             ("entry_bytes_compile_assertion", "24")):
            changed = dict(self.report, **{field: value})
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "differs"):
                subject.validate_report_bytes(self.encode(changed), **self.options)

    def test_requires_bounded_exact_bytes(self):
        for raw in ("{}", bytearray(b"{}"), b" " * ((1 << 20) + 1)):
            with self.subTest(kind=type(raw)), self.assertRaisesRegex(ValueError, "bounded"):
                subject.validate_report_bytes(raw, **self.options)


if __name__ == "__main__":
    unittest.main()
