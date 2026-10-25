"""Profile qualifier admission and host-budget boundaries; no engine required."""
from __future__ import annotations

import importlib.util
import json
import lzma
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PATH = Path(__file__).with_name("profile_verify.py")
SPEC = importlib.util.spec_from_file_location("profile_verify_tests_target", PATH)
VERIFY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VERIFY
SPEC.loader.exec_module(VERIFY)


def admitted(profile_id="test-p4", family="A"):
    api = VERIFY.contracts()
    profile, engine = api.resource_profile(profile_id), api.engine_spec(family)
    return VERIFY.AdmittedBuild(family, profile_id, "source-jit", "x", "main.c", "native/x", {},
                                profile.to_record(engine.entry_bytes), {}, {}, {}, {})


class ProfileRuntimeAdmission(unittest.TestCase):
    def test_target_image_is_separate_from_the_original_producer_expectation(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory(prefix="rove4k-target-image-") as temporary:
            root = Path(temporary)
            (root / "native").mkdir()
            (root / "native/x").write_bytes(b"original compiler image")
            (root / "target").mkdir()
            target = root / "target/x"
            target.write_bytes(b"independent target image")
            (root / "build.json").write_bytes(b"{}")
            old = {"native_" + k: v for k, v in VERIFY.pin((root / "native/x").read_bytes()).items()}
            accepted = replace(admitted(), expected=dict(old))
            expected_target = VERIFY.pin(target.read_bytes())
            class Reference:
                family, profile, native_path = "A", "test-p4", target
                native_pin = expected_target
                def assert_admission(self, value, build):
                    VERIFY.require(value.program == "x", "reference execution object differs")
                def to_record(self):
                    return {"runtime_eligible": True, "factory_replayed_on_target": False,
                            "original_build_expected_contract": dict(old),
                            "source_build": {"path": str(root), **VERIFY.pin(b"{}")}}
            self.assertEqual(VERIFY.runtime_image(accepted, root),
                             (VERIFY.pin((root / "native/x").read_bytes()), b"original compiler image"))
            with patch.object(VERIFY, "target_module", return_value=types.SimpleNamespace(TargetRuntimeReference=Reference)):
                self.assertEqual(VERIFY.runtime_image(accepted, root, Reference()),
                                 (expected_target, b"independent target image"))
                with self.assertRaisesRegex(ValueError, "validated TargetRuntimeReference"):
                    VERIFY.runtime_image(accepted, root, {"native_pin": expected_target})
                with self.assertRaisesRegex(ValueError, "execution object differs"):
                    VERIFY.runtime_image(replace(accepted, program="unadmitted-program"), root, Reference())
            self.assertEqual(accepted.expected, old)

    def test_reference_for_another_profile_cannot_choose_a_runtime_image(self):
        from dataclasses import replace
        class Reference:
            family, profile = "A", "test-p28"
            def to_record(self):
                return {"runtime_eligible": True, "factory_replayed_on_target": False}
        with patch.object(VERIFY, "target_module", return_value=types.SimpleNamespace(TargetRuntimeReference=Reference)):
            with self.assertRaisesRegex(ValueError, "another source build/profile"):
                VERIFY.runtime_image(replace(admitted(), expected={}), Path("not-read"), Reference())

    def test_phase_and_model_proofs_have_exact_order_and_named_helper(self):
        resource = {"schema": "rove4k.c-resource-projection.v1"}
        phase = {"schema": "rove4k.portable-phase-source.v1"}
        model = {"stage": "canonical-e19-physical-binding"}
        post = {"path": "engines/experiments/tcec-next/profile_phase.py", "variant": "phase-init"}
        self.assertEqual(VERIFY.source_stages("E", post, [resource, phase, model]), "phase")
        self.assertEqual(VERIFY.source_stages("A", post, [resource, phase]), "phase")
        self.assertIsNone(VERIFY.source_stages("E", None, [resource, model]))
        for family, declaration, proofs in (
            ("E", post, [resource, model, phase]), ("E", post, [resource, phase]),
            ("A", None, [resource, phase]), ("B", post, [resource, phase]),
            ("A", {**post, "path": "engines/other.py"}, [resource, phase]),
            ("A", {**post, "variant": "phase"}, [resource, phase]),
            ("", None, [resource]), ("AC", None, [resource]),
        ):
            with self.subTest(family=family, post=declaration, proofs=proofs), self.assertRaises(ValueError):
                VERIFY.source_stages(family, declaration, proofs)

    def test_runtime_snapshot_matches_the_code_that_this_process_actually_compiled(self):
        source = PATH.read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(VERIFY.executing_source(source), source)
        altered = source.replace(b'CLASS = "rove4k-production-profile-v1"',
                                 b'CLASS = "different-program"', 1)
        self.assertNotEqual(altered, source)
        with self.assertRaisesRegex(ValueError, "compiled its executing module"):
            VERIFY.executing_source(altered)

    def test_large_submission_is_rejected_by_real_headroom_before_execution(self):
        record = admitted("tcec-provisional")
        with self.assertRaisesRegex(ValueError, "insufficient effective headroom before allocation"):
            VERIFY.execution_limits(record, 16 << 30)
        # A successful arithmetic admission is not execution or qualification.
        limits = VERIFY.execution_limits(record, 512 << 30)
        self.assertEqual(limits["admission"]["tt_bytes"], 192 << 30)
        self.assertGreater(limits["address_space_bytes"], 192 << 30)
        self.assertNotIn("qualified", limits)

    def test_generic_tt_or_mislabeled_workers_do_not_match_production(self):
        api = VERIFY.contracts()
        record = api.resource_profile("test-p4").to_record(16)
        with self.assertRaisesRegex(ValueError, "selected immutable profile"):
            VERIFY._resource_record(record, "A")
        record = api.resource_profile("test-p4").to_record(24)
        record["workers"] = 2
        with self.assertRaisesRegex(ValueError, "selected immutable profile"):
            VERIFY._resource_record(record, "A")

    def test_small_test_budget_is_finite_and_does_not_use_large_submission_limit(self):
        limits = VERIFY.execution_limits(admitted(), 4 << 30, wall_seconds=300)
        self.assertEqual(limits["address_space_bytes"], 2 << 30)
        self.assertEqual(limits["wall_seconds"], 300)
        self.assertEqual(limits["output_bytes_per_pipe"], 1 << 20)
        self.assertEqual(limits["startup_seconds"], 60)
        with self.assertRaisesRegex(ValueError, "finite runtime wall bound"):
            VERIFY.execution_limits(admitted(), 4 << 30, wall_seconds=0)

    def test_payload_must_have_exact_bounded_single_stream(self):
        source = b"int main(void){return 0;}\n"
        encoded = lzma.compress(source, format=lzma.FORMAT_ALONE)
        self.assertEqual(VERIFY.restore_payload(encoded, len(source)), source)
        for corrupt in (encoded + b"unused", encoded[:-1]):
            with self.subTest(case=corrupt[-8:]), self.assertRaisesRegex(ValueError, "one bounded"):
                VERIFY.restore_payload(corrupt, len(source))
        with self.assertRaisesRegex(ValueError, "one bounded"):
            VERIFY.restore_payload(encoded, len(source) - 1)

    def test_legacy_or_incomplete_build_cannot_enter_new_profile_runtime(self):
        with self.assertRaisesRegex(ValueError, "explicit new C production-profile"):
            VERIFY.admit_c_build({"format": 1, "class": "tcec-full-C-v1"}, Path("not-read"))
        with self.assertRaisesRegex(ValueError, "generation/reproduction is incomplete"):
            VERIFY.admit_c_build({"format": 1, "class": VERIFY.CLASS,
                                  "complete": True, "reproducible": False}, Path("not-read"))

    def test_build_complete_flag_is_not_an_owned_runtime_receipt(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-profile-receipt-") as temporary:
            root = Path(temporary)
            receipt = root / "runtime.json"
            receipt.write_text('{"format": "rove4k-production-profile-v1", "complete": true}')
            with self.assertRaisesRegex(ValueError, "owned runtime has not completed cleanly"):
                VERIFY.qualification_record(admitted(), root, receipt)

    def test_completed_runtime_cannot_be_rebound_to_another_artifact(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-profile-binding-") as temporary:
            root = Path(temporary)
            receipt = root / "runtime.json"
            (root / "build.json").write_bytes(b"{}")
            record = {"format": "rove4k-profile-runtime-v1", "complete": True,
                      "owned_remaining": 0, "final_owned_cleanup": [], "family": "B",
                      "profile": "test-p4", "representation": "source-jit"}
            receipt.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "runtime artifact class differs"):
                VERIFY.qualification_record(admitted(), root, receipt)
            record.update(family="A", build_sha256="0" * 64)
            receipt.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "whole/native/source/resource identity"):
                VERIFY.qualification_record(admitted(), root, receipt)

    def test_effective_headroom_includes_each_cgroup_v2_ancestor(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-profile-budget-") as temporary:
            root = Path(temporary)
            proc, cgroups = root / "proc", root / "cgroups"
            (proc / "self").mkdir(parents=True)
            (proc / "meminfo").write_text("MemAvailable: 16777216 kB\n")
            (proc / "self/cgroup").write_text("0::/slice/job\n")
            (cgroups / "slice/job").mkdir(parents=True)
            (cgroups / "memory.max").write_text("max\n")
            (cgroups / "memory.current").write_text("0\n")
            (cgroups / "slice/memory.max").write_text(str(1 << 30))
            (cgroups / "slice/memory.current").write_text(str(256 << 20))
            (cgroups / "slice/job/memory.max").write_text(str(512 << 20))
            (cgroups / "slice/job/memory.current").write_text(str(64 << 20))
            self.assertEqual(VERIFY.effective_available_bytes(proc, cgroups), 448 << 20)
            (cgroups / "slice/job/memory.current").write_text(str(1 << 30))
            self.assertEqual(VERIFY.effective_available_bytes(proc, cgroups), 0)

    def test_effective_headroom_includes_cgroup_v1_memory_controller(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-profile-budget-v1-") as temporary:
            root = Path(temporary)
            proc, cgroups = root / "proc", root / "cgroups"
            (proc / "self").mkdir(parents=True)
            (proc / "meminfo").write_text("MemAvailable: 16777216 kB\n")
            (proc / "self/cgroup").write_text("7:cpu,cpuacct:/job\n8:memory:/job\n")
            memory = cgroups / "memory"
            (memory / "job").mkdir(parents=True)
            (memory / "memory.limit_in_bytes").write_text(str(2 << 30))
            (memory / "memory.usage_in_bytes").write_text(str(256 << 20))
            (memory / "job/memory.limit_in_bytes").write_text(str(1 << 30))
            (memory / "job/memory.usage_in_bytes").write_text(str(512 << 20))
            self.assertEqual(VERIFY.effective_available_bytes(proc, cgroups), 512 << 20)

    def test_cpu_budget_covers_all_observed_workers_without_unbounded_wall(self):
        with patch.object(VERIFY.os, "sched_getaffinity", return_value=set(range(256)), create=True):
            large = VERIFY.execution_limits(admitted("tcec-provisional"), 512 << 30)
            small = VERIFY.execution_limits(admitted(), 4 << 30)
        self.assertEqual(large["CPU_budget_effective_cpus"], 256)
        self.assertGreater(large["CPU_seconds"][0], 256 * 60)
        self.assertEqual(small["CPU_budget_effective_cpus"], 5)
        self.assertEqual(large["wall_seconds"], small["wall_seconds"])
        self.assertGreater(large["CPU_seconds"][1], large["CPU_seconds"][0])

    def test_native_dependency_gate_checks_executable_entry_and_stack(self):
        def native(load_flags=5, stack_flags=6, entry=0x4000C8):
            identity = b"\x7fELF\x02\x01\x01" + b"\0" * 9
            header = struct.pack("<16sHHIQQQIHHHHHH", identity, 2, 62, 1, entry,
                                 64, 0, 0, 64, 56, 2, 0, 0, 0)
            load = struct.pack("<IIQQQQQQ", 1, load_flags, 0, 0x400000, 0,
                               201, 201, 4096)
            stack = struct.pack("<IIQQQQQQ", 0x6474E551, stack_flags, 0, 0, 0,
                                0, 0, 16)
            return (header + load + stack).ljust(200, b"\0") + b"\xc3"
        record = VERIFY.native_dependencies(native())
        self.assertEqual(record["DT_NEEDED"], [])
        self.assertIsNone(record["interpreter"])
        self.assertFalse(record["executable_stack"])
        for image in (native(load_flags=7), native(stack_flags=7),
                      native(entry=0x500000), native()[:64]):
            with self.subTest(image=image[-8:]), self.assertRaises(ValueError):
                VERIFY.native_dependencies(image)

    def test_artifact_path_cannot_escape_build_or_follow_symlink(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-profile-files-") as temporary:
            root = Path(temporary)
            build = root / "build"
            build.mkdir()
            inside, outside = build / "x", root / "other-source.txt"
            inside.write_bytes(b"own")
            outside.write_bytes(b"outside")
            self.assertEqual(VERIFY.checked_artifact(build, "x", VERIFY.pin(b"own")), b"own")
            with self.assertRaisesRegex(ValueError, "escaped its build"):
                VERIFY.artifact_file(build, outside)
            link = build / "linked"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                return
            with self.assertRaisesRegex(ValueError, "cannot follow a symlink"):
                VERIFY.artifact_file(build, link)


if __name__ == "__main__":
    unittest.main()
