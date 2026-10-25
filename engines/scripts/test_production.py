"""Production boundaries and resource mechanisms; no engine or TT allocation."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).with_name("production.py")
_spec = importlib.util.spec_from_file_location("rove_production_contract", SCRIPT)
production = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = production
_spec.loader.exec_module(production)


class ResourceContracts(unittest.TestCase):
    def test_target_and_test_resources_remain_distinct(self):
        # Actual current production ABCEF entry24; D entry16. Generic DEV is
        # intentionally not the authority for these object layouts.
        expected = {
            ("test-p4", 24): (4, 22, 96 << 20),
            ("test-p28", 24): (28, 24, 384 << 20),
            ("tcec-provisional", 24): (256, 33, 192 << 30),
            ("test-p4", 16): (4, 23, 128 << 20),
            ("test-p28", 16): (28, 25, 512 << 20),
            ("tcec-provisional", 16): (256, 34, 256 << 30),
        }
        for (name, entry), (workers, bits, size) in expected.items():
            with self.subTest(name=name, entry=entry):
                profile = production.resource_profile(name)
                layout = profile.layout(entry)
                self.assertEqual((profile.workers, layout.bits, layout.bytes), (workers, bits, size))
                self.assertLessEqual(layout.bytes, profile.tt_cap_bytes)
                self.assertGreater(layout.bytes * 2, profile.tt_cap_bytes)
        target = production.resource_profile("tcec-provisional")
        self.assertEqual(target.os_threads, 257)
        self.assertEqual(target.minimum_counter_bits, 9)
        self.assertFalse(target.to_record(24)["event_allocation_confirmed"])
        self.assertTrue(target.to_record(24)["init_partition_requires_page_aligned_base"])

    def test_64bit_indexes_and_target_width_rejection(self):
        profile = production.resource_profile("tcec-provisional")
        self.assertEqual(profile.layout(24).mask, 0x1FFFFFFFF)
        self.assertEqual(profile.layout(16).mask, 0x3FFFFFFFF)
        for entry in (16, 24):
            with self.subTest(entry=entry), self.assertRaisesRegex(ValueError, "address/object width"):
                profile.layout(entry, address_bits=32)
        with self.assertRaises(ValueError):
            profile.layout(True)
        with self.assertRaises(ValueError):
            production.TTLayout(24, 0, True, 24, 0)
        with self.assertRaises(ValueError):
            production.ResourceProfile("too-large", "test", 1, 1 << 63).layout(16)

    def test_registered_profiles_and_registries_are_immutable(self):
        profile = production.resource_profile("test-p4")
        with self.assertRaises(FrozenInstanceError):
            profile.workers = 1
        with self.assertRaises(TypeError):
            production.PROFILES["test-p4"] = profile
        with self.assertRaisesRegex(ValueError, "cannot be redefined"):
            production.ResourceProfile("test-p4", "test", 1, 128 << 20)
        with self.assertRaises(ValueError):
            production.engine_spec("rust")
        with self.assertRaises(ValueError):
            production.resource_profile("target512")

    def test_init_ranges_cover_w28_and_w256_without_page_sharing(self):
        for name in production.PROFILES:
            profile = production.resource_profile(name)
            for entry in (16, 24):
                with self.subTest(profile=name, entry=entry):
                    layout = profile.layout(entry)
                    ranges = profile.init_ranges(layout, base_address=0x100000)
                    self.assertEqual(len(ranges), profile.workers)
                    self.assertEqual(ranges[0].begin, 0)
                    self.assertEqual(ranges[-1].end, layout.entries)
                    self.assertEqual(sum(row.entries for row in ranges), layout.entries)
                    self.assertTrue(all(a.end == b.begin for a, b in zip(ranges, ranges[1:])))
                    self.assertTrue(all(row.begin <= row.end for row in ranges))
                    self.assertTrue(all(row.begin * entry % 4096 == 0 for row in ranges))
                    if entry == 24:
                        self.assertTrue(all(row.begin % 512 == 0 for row in ranges))
                    with self.assertRaisesRegex(ValueError, "TT base is not aligned"):
                        profile.init_ranges(layout, base_address=0x100010)

    def test_tiny_fixture_partition_has_explicit_empty_workers(self):
        fixture = production.ResourceProfile("mechanism", "test", 256, 16 * 8)
        layout = fixture.layout(16)
        rows = fixture.init_ranges(layout)
        self.assertEqual(rows[0].begin, 0)
        self.assertEqual(rows[-1].end, 8)
        self.assertEqual(sum(row.entries for row in rows), 8)
        self.assertEqual(sum(row.entries != 0 for row in rows), 1)

    def test_execution_gate_rejects_before_allocator_is_called(self):
        profile = production.resource_profile("tcec-provisional")
        layout = profile.layout(24)
        admission = production.host_admission(profile, layout, 15 << 30,
                                               other_peak_bytes=2 << 30)
        self.assertFalse(admission.admitted)
        self.assertIn("before allocation", admission.reason)
        with self.assertRaisesRegex(ValueError, "insufficient effective headroom"):
            admission.require()
        self.assertTrue(production.require_host_capacity(profile, layout, 320 << 30,
                                                        other_peak_bytes=2 << 30).admitted)
        with self.assertRaisesRegex(ValueError, "does not match"):
            production.host_admission(profile, production.TTLayout(24, 18, 1 << 18,
                                                                  24 << 18, (1 << 18) - 1), 15 << 30)


class ClosureContracts(unittest.TestCase):
    def _closure(self, family="A", **kwargs):
        spec = production.engine_spec(family)
        return production.SourceClosure.validate(spec, engine_inputs=spec.required_source_inputs, **kwargs)

    def test_canonical_model_and_core_cannot_be_omitted(self):
        e = production.engine_spec("E")
        for incomplete in ((e.source_inputs[0],), (e.source_inputs[1],)):
            with self.subTest(incomplete=incomplete), self.assertRaisesRegex(ValueError, "required model"):
                production.SourceClosure.validate(e, engine_inputs=incomplete)
        d = production.engine_spec("D")
        minimal = production.SourceClosure.validate(d, engine_inputs=d.required_source_inputs)
        self.assertNotIn("engines/compact/tiny-entry-d/native/hq.c", minimal.engine_inputs)
        production.SourceClosure.validate(d, engine_inputs=d.source_inputs)

    def test_cross_family_and_reference_core_are_rejected(self):
        a = production.engine_spec("A")
        for alien in ("engines/compact/tiny-entry-b/engine.c", "engines/c/main.c"):
            with self.subTest(alien=alien), self.assertRaisesRegex(ValueError, "this family's"):
                production.SourceClosure.validate(a, engine_inputs=(*a.source_inputs, alien))
        for tool in ("engines/compact/tiny-entry-b/shipping_core.py",
                     "engines/scripts/test_production.py", "engines/experiments/tcec-next/check_b_exchange.py"):
            with self.subTest(tool=tool), self.assertRaisesRegex(ValueError, "production helpers"):
                self._closure(tool_inputs=(tool,))

    def test_shared_helpers_and_packaging_are_explicit(self):
        closure = self._closure("B", tool_inputs=(
            "engines/compact/tiny-entry-b/bootstrap.py.in",
            "engines/compact/tiny-entry-b/launcher.sh",
            "engines/compact/tiny-entry-a/shipping_condition_bce.py",
            "engines/scripts/source_package.py"))
        self.assertEqual(len(closure.tool_inputs), 4)
        a = production.engine_spec("A")
        closure = production.SourceClosure.validate(
            a, engine_inputs=(*a.source_inputs, *production.COMMON_RUNTIME_INPUTS))
        self.assertIn("engines/scripts/elf-loader/loader.c", closure.engine_inputs)
        with self.assertRaisesRegex(ValueError, "production helpers"):
            self._closure(tool_inputs=("engines/scripts/elf-loader/loader.c",))

    def test_common_c_is_required_engine_source_and_cannot_hide_as_a_tool(self):
        for family in "ABCDEF":
            spec = production.engine_spec(family)
            shared = production.SHARED_ENGINE_INPUTS[family]
            closure = self._closure(family)
            self.assertTrue(set(shared).issubset(closure.engine_inputs))
            with self.assertRaisesRegex(ValueError, "required model"):
                production.SourceClosure.validate(spec, engine_inputs=tuple(
                    path for path in spec.required_source_inputs if path not in shared))
            with self.assertRaisesRegex(ValueError, "production helpers"):
                self._closure(family, tool_inputs=("engines/common/other.c",))
        d = production.engine_spec("D")
        with self.assertRaisesRegex(ValueError, "this family's"):
            production.SourceClosure.validate(d, engine_inputs=(*d.source_inputs, "engines/common/protocol.c"))

    def test_test_closure_is_distinct_and_protected_names_never_read(self):
        diagnostic = ("engines/tests/chess_oracle.py",)
        with self.assertRaisesRegex(ValueError, "cannot include test"):
            self._closure(test_inputs=diagnostic)
        closure = self._closure(test_inputs=diagnostic, submission=False)
        self.assertEqual(closure.test_inputs, diagnostic)
        for path in ("engines/experiments/.ENV", "engines/experiments/.ENV.local",
                     "engines/experiments/.CACHE/foo.py", "engines/experiments/id_rsa",
                     "engines/experiments/secret.pem", "engines/experiments/serviceaccount.json",
                     "engines/tests/../inventory.json"):
            with self.subTest(path=path), patch.object(Path, "read_bytes") as read:
                with self.assertRaises(ValueError):
                    self._closure(test_inputs=(path,), submission=False)
                read.assert_not_called()

    def test_source_pin_snapshot_distinguishes_observation_from_admission(self):
        closure = self._closure()
        logical = closure.engine_inputs[0]
        with tempfile.TemporaryDirectory(prefix="rove-source-closure-") as temporary:
            root = Path(temporary)
            path = root / logical
            raw = b"int main(void){return 0;}\r\n"
            for name in closure.engine_inputs:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            observed = production.snapshot_closure(root, closure)
            self.assertEqual(observed.admission, "observed-only")
            self.assertEqual(observed.inputs[0].raw_bytes, len(raw))
            expected = {name: sha256(raw.replace(b"\r\n", b"\n")).hexdigest() for name in closure.engine_inputs}
            verified = production.snapshot_closure(root, closure, expected=expected)
            self.assertEqual(verified.admission, "expected-pins-verified")
            with self.assertRaisesRegex(ValueError, "exactly cover"):
                production.snapshot_closure(root, closure, expected={})
            path.write_bytes(b"int main(void){return 1;}\n")
            with self.assertRaisesRegex(ValueError, "pin differs"):
                production.snapshot_closure(root, closure, expected=expected)

    def test_manual_closure_cannot_bypass_admission(self):
        manual = production.SourceClosure("A", ("engines/compact/tiny-entry-b/engine.c",), ())
        with tempfile.TemporaryDirectory(prefix="rove-manual-closure-") as temporary:
            with patch.object(Path, "read_bytes") as read:
                with self.assertRaisesRegex(ValueError, "this family's"):
                    production.snapshot_closure(Path(temporary), manual)
                read.assert_not_called()

    def test_symlink_is_rejected_before_source_read(self):
        closure = self._closure()
        with tempfile.TemporaryDirectory(prefix="rove-link-closure-") as temporary:
            root = Path(temporary)
            path = root / closure.engine_inputs[0]
            path.parent.mkdir(parents=True)
            target = root / "normal-source.c"
            target.write_text("int main(void){return 0;}\n", encoding="utf-8")
            try:
                path.symlink_to(target)
            except OSError as error:
                self.skipTest("host cannot create a symlink: " + str(error))
            with patch.object(Path, "read_bytes") as read:
                with self.assertRaisesRegex(ValueError, "cannot follow links"):
                    production.snapshot_closure(root, closure)
                read.assert_not_called()


class ArtifactContracts(unittest.TestCase):
    def test_division_and_representation_are_independent(self):
        args = (production.engine_spec("C"), production.resource_profile("tcec-provisional"))
        elf = production.ArtifactPlan(*args, "self-contained-elf", "none")
        for division in ("general4k", "elf4k"):
            decision = elf.size_decision(4096, division)
            self.assertEqual(decision["status"], "within_limit")
            self.assertFalse(decision["qualified"])
        self.assertEqual(elf.size_decision(4097, "general4k")["status"], "blocked_size")
        self.assertEqual(elf.size_decision(4097, "elf4k")["status"], "deferred_size")
        source = production.ArtifactPlan(*args, "source-jit", "private-path")
        self.assertEqual(source.size_decision(3800, "elf4k")["status"], "not_applicable")
        self.assertNotEqual(source.id, production.ArtifactPlan(
            args[0], production.resource_profile("test-p4"), "source-jit", "private-path").id)
        with self.assertRaisesRegex(ValueError, "cannot unlink"):
            production.ArtifactPlan(*args, "self-contained-elf", "private-path")


if __name__ == "__main__":
    unittest.main()
