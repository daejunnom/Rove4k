#!/usr/bin/env python3
"""Pure ELF producer/reader checks; no factories, C, packing process or TT.

--fixture-root optionally names an already materialized origin directory with
the ten literal FAMILY/PROFILE/artifact/{main.c,build.json} files. Only those
named small source DATA files are read. Historical DATA never enters production.
"""
import argparse
from contextlib import redirect_stdout
import copy
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIXTURE_ROOT = None


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    # Source-only loading avoids even a .pyc cache probe in an exact-open pure
    # harness. It does not change the production helper or verifier bindings.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    exec(compile(data, str(path), "exec", dont_inherit=True), value.__dict__)
    return value


owner = module("test_full_elf_profile_owner", HERE / "elf_profile.py")
entry = module("test_full_elf_profile_entry", HERE / "elf_entry_mode.py")
projection = module("test_full_elf_profile_projection", HERE / "spelling_compound.py")
dependencies = module("test_full_elf_profile_dependencies", HERE / "profile_dependencies.py")
elf = module("test_full_elf_profile_codec", ROOT / "engines/scripts/elf_loader.py")
elf_dependencies = module("test_full_elf_profile_elf_dependencies", ROOT / "engines/scripts/elf_dependencies.py")


def image(length=512):
    """One inert static ELF LOAD; it is DATA and is never executed."""
    result = bytearray(length)
    result[:16] = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    struct.pack_into("<HHIQQQIHHHHHH", result, 16,
        2, 62, 1, 0x400100, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", result, 64, 1, 5, 0, 0x400000, 0, length, length, 4096)
    result[256] = 0xc3
    return bytes(result)


def packed():
    native = image()
    payload = elf._compress(native)
    # Give the outer LOAD the actual whole extent, while keeping payload last.
    prefix = bytearray(image(512)[:300])
    struct.pack_into("<QQ", prefix, 64 + 32, len(prefix) + len(payload), len(prefix) + len(payload))
    whole = bytes(prefix) + payload
    selected = dict(filter="none", output_bytes=len(whole), output_sha256=sha256(whole).hexdigest(),
        payload_bytes=len(payload), loader_and_headers_bytes=len(prefix), within_size_limit=True,
        compiler_options=["-DOUTPUT_SIZE=512", "-DBRANCH_FILTER=0"])
    other = dict(selected, filter="bcj", output_bytes=len(whole) + 1, loader_and_headers_bytes=len(prefix) + 1)
    detail = dict(format="elf64-x86_64-self-restoring", codec="rove4k-lz-runs-v1",
        input_bytes=len(native), input_sha256=sha256(native).hexdigest(), requested_filter="auto",
        filter_candidates=[selected, other], size_limit_bytes=4096, input_elf=elf._elf(native),
        runtime_external_tools=[], **{k: v for k, v in selected.items() if k != "within_size_limit"}, within_size_limit=True)
    return whole, native, detail


class PolicyTests(unittest.TestCase):
    def test_all_ten_contexts_are_full_and_finite(self):
        self.assertEqual(set(owner.CONTROL), set(entry.INPUTS))
        for family in owner.FAMILIES:
            for profile in owner.PROFILES:
                policy = owner.plan(family, profile)
                self.assertTrue(policy["full"])
                self.assertFalse(policy["runtime_qualified"])
                self.assertEqual(policy["entry_cleanup"], "none")
                self.assertEqual(policy["representation"], "self-contained-elf")
                self.assertEqual(policy["outer_commands"], 10)
                self.assertEqual(policy["native_variant"], "baseline")
                command = owner.factory_argv(family, Path("/external/owned"), profile)
                self.assertEqual(command[command.index("--representation") + 1], "source-jit")
                self.assertEqual(command[command.index("--source-dependencies") + 1], "unused-includes")
                self.assertEqual(command[command.index("--spelling-variant") + 1],
                                 "best" if family == "B" else "compound-v2" if family == "F" else "compound")
                self.assertEqual("--scan-variant" in command, family in ("A", "C"))

    def test_invalid_context_is_rejected_before_execution(self):
        for family, profile in (("D", "test-p4"), ("F8", "test-p4"), ("A", "tcec-provisional"), (True, "test-p4")):
            with self.assertRaises(ValueError):
                owner.plan(family, profile)
        with self.assertRaisesRegex(ValueError, "explicit --execute"):
            owner.produce("A", Path("/never-created"))
        with self.assertRaisesRegex(ValueError, "explicit --execute"):
            owner.produce("A", Path("/never-created"), native_variant="lean")
        with self.assertRaisesRegex(ValueError, "explicit --execute"):
            owner.runtime(Path("/never-read"), Path("/never-created"))
        with self.assertRaisesRegex(ValueError, "explicit --execute"):
            owner.rules(Path("/never-read"), Path("/never-created"))

    def test_incomplete_and_legacy_receipts_do_not_reach_filesystem(self):
        for value in ({}, {"format": 1, "class": "rove4k-production-profile-v1", "complete": True},
                      {"format": True, "class": owner.CLASS, "complete": True, "reproducible": True}):
            with self.assertRaisesRegex(ValueError, "complete fresh"):
                owner.admit_build(value, Path("/never-read"))

    def test_resource_caps_do_not_raise_inherited_hard_limits(self):
        result = owner.limit_plan((-1, -1), (-1, -1), (-1, -1))
        self.assertEqual(result, {"parent_CPU": (600, 630), "parent_AS": 4 << 30, "FSIZE": (8 << 20, 8 << 20)})
        self.assertEqual(owner.limit_plan((500, 500), (4 << 30, 4 << 30), (1024, 2048))["FSIZE"], (1024, 1024))
        for values in (((200, 400), (-1, -1), (-1, -1)), ((-1, -1), (2 << 30, 4 << 30), (-1, -1)),
                       ((True, 600), (-1, -1), (-1, -1)), ((-1, 600), (-1, -1), (-1, -1))):
            with self.assertRaises(ValueError):
                owner.limit_plan(*values)

    def test_nonterminal_or_forced_command_is_not_an_owner_receipt(self):
        row = dict(started=True, terminal=True, reaped=True, returncode=0, owned_group_absent=True,
                   forced_cleanup=False, other_group_members_before_reap=[],
                   original_identity_retained_until_other_members_absent=True)
        self.assertTrue(owner.settled([row]))
        self.assertFalse(owner.settled([]))
        for field, value in (("returncode", True), ("forced_cleanup", True), ("reaped", False),
                             ("owned_group_absent", False), ("other_group_members_before_reap", [{"pid": 1}])):
            self.assertFalse(owner.settled([{**row, field: value}]), field)

    def test_current_finite_ABI_absence_uses_its_semantic_owner(self):
        resource = {"schema": "rove4k.c-resource-projection.v1"}
        stage = {"schema": "rove4k.profile-b-source.v1", "variant": "tcec-final-lf"}
        manifest = {"source_proofs": [resource, stage], "post_profile": {
            "path": "engines/experiments/tcec-next/profile_b.py", "variant": "tcec-final-lf"}}
        self.assertIsNone(owner.validate_target_abi_absence(manifest, "B"))
        reordered = copy.deepcopy(manifest)
        reordered["source_proofs"].reverse()
        self.assertIsNone(owner.validate_target_abi_absence(reordered, "B"))
        for bad in ({**manifest, "source_proofs": [resource]},
                    {**manifest, "source_proofs": [resource, stage, dict(stage)]},
                    {**manifest, "source_proofs": [{**resource, "target_abi_probe": "wrong owner"}, stage]},
                    {**manifest, "source_proofs": [resource, {**stage, "target_abi_probe": "int main(void){return 0;}"}]},
                    {**manifest, "source_proofs": [resource, {**stage, "target_abi_probe": None}]}):
            with self.assertRaises(ValueError):
                owner.validate_target_abi_absence(bad, "B")
        self.assertIsNone(owner.validate_target_abi_absence({"source_proofs": [resource]}, "A"))
        with self.assertRaises(ValueError):
            owner.validate_target_abi_absence(manifest, "A")


class NativePolicyTests(unittest.TestCase):
    CONTROL_COMPILERS = {
        "A": ["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"],
        "B": ["cc", "-std=c11", "-Os", "-pthread", "-x", "c", "-", "-o", "x"],
        "C": ["cc", "-Os", "-mavx2", "-x", "c", "-", "-o", "x", "-s"],
        "E": ["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"],
        "F": ["cc", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s"],
    }
    LEAN_FLAGS = ["-fno-asynchronous-unwind-tables", "-fno-unwind-tables", "-Wl,--build-id=none"]

    def test_default_is_original_compiler_and_lean_is_exact_opt_in(self):
        for family, control in self.CONTROL_COMPILERS.items():
            for profile in owner.PROFILES:
                with self.subTest(family=family, profile=profile):
                    baseline = owner.plan(family, profile)
                    self.assertEqual(baseline, owner.plan(family, profile, native_variant="baseline"))
                    self.assertEqual(baseline["compiler"], control)
                    self.assertEqual(baseline["control_compiler"], control)
                    self.assertIsNot(baseline["compiler"], baseline["control_compiler"])
                    lean = owner.plan(family, profile, native_variant="lean")
                    self.assertEqual(lean["control_compiler"], control)
                    at = control.index("-x")
                    additions = [*self.LEAN_FLAGS, *(["-s"] if family == "B" else [])]
                    self.assertEqual(lean["compiler"], [*control[:at], *additions, *control[at:]])
                    self.assertEqual(lean["compiler"].count("-s"), 1)
                    self.assertEqual({key: value for key, value in lean.items() if key not in ("native_variant", "compiler")},
                                     {key: value for key, value in baseline.items() if key not in ("native_variant", "compiler")})

    def test_factory_argv_never_receives_derived_native_options(self):
        for family in owner.FAMILIES:
            for profile in owner.PROFILES:
                command = owner.factory_argv(family, Path("/external/unchanged-control"), profile)
                self.assertEqual(command[command.index("--representation") + 1], "source-jit")
                self.assertNotIn("--native-variant", command)
                self.assertNotIn("--compile-cc", command)
                for flag in [*self.LEAN_FLAGS, "-s"]:
                    self.assertNotIn(flag, command)

    def test_finite_variant_and_policy_mismatches_fail_before_source_capture(self):
        for variant in (None, True, "unwindless", "strip", "lean -ffast-math"):
            with self.assertRaisesRegex(ValueError, "finite baseline/lean"):
                owner.plan("A", native_variant=variant)
        manifest = dict(format=1, **{"class": owner.CLASS}, complete=True, reproducible=True,
            source_closure_rechecked=True, family="A", profile="test-p4", native_variant="baseline",
            policy=owner.plan("A"), actual={"source": "main.c", "native": "native/x", "program": "x"})
        variants = []
        changed = copy.deepcopy(manifest)
        changed["native_variant"] = "lean"
        variants.append(changed)
        for field in ("compiler", "control_compiler"):
            changed = copy.deepcopy(manifest)
            changed["policy"][field].append("-ffast-math")
            variants.append(changed)
        for changed in variants:
            with self.assertRaisesRegex(ValueError, "finite ELF build policy/layout"):
                owner.admit_build(changed, Path("/never-read"))

    def test_plan_CLI_is_read_only_and_produce_still_requires_execute(self):
        for variant in owner.NATIVE_VARIANTS:
            output = io.StringIO()
            with redirect_stdout(output):
                owner.main(["plan", "--entry", "B", "--native-variant", variant])
            self.assertEqual(json.loads(output.getvalue()), owner.plan("B", native_variant=variant))
            with self.assertRaisesRegex(ValueError, "explicit --execute"):
                owner.main(["produce", "--entry", "B", "--native-variant", variant, "--out", "/never-created"])


class PackedReaderTests(unittest.TestCase):
    def test_actual_payload_inverse_and_both_dependency_tables(self):
        whole, native, detail = packed()
        observed, header, payload = owner.packed_restore(whole, native, detail, elf=elf, dependency=elf_dependencies)
        self.assertEqual(header + payload, whole)
        self.assertEqual(elf._decompress(payload, len(native)), native)
        self.assertEqual(observed["native"]["input"], owner.pin(native))
        self.assertEqual(observed["outer"]["input"], owner.pin(whole))
        self.assertTrue(observed["native_policy"]["allowed"])
        self.assertTrue(observed["outer_policy"]["allowed"])

    def test_metadata_flags_cannot_replace_actual_inverse(self):
        whole, native, detail = packed()
        for field, value in (("payload_bytes", True), ("within_size_limit", 1),
                             ("runtime_external_tools", ["sh"]), ("input_sha256", "0" * 64),
                             ("filter", "external"), ("loader_and_headers_bytes", 0)):
            changed = copy.deepcopy(detail)
            changed[field] = value
            with self.assertRaises(ValueError, msg=field):
                owner.packed_restore(whole, native, changed, elf=elf, dependency=elf_dependencies)
        changed = copy.deepcopy(detail)
        changed["filter_candidates"][1]["output_bytes"] = len(whole) - 1
        changed["filter_candidates"][1]["loader_and_headers_bytes"] -= 2
        with self.assertRaises(ValueError):
            owner.packed_restore(whole, native, changed, elf=elf, dependency=elf_dependencies)
        corrupt = whole[:-1] + bytes([whole[-1] ^ 1])
        changed = copy.deepcopy(detail)
        changed["output_sha256"] = sha256(corrupt).hexdigest()
        changed["filter_candidates"][0]["output_sha256"] = changed["output_sha256"]
        with self.assertRaises((ValueError, RuntimeError)):
            owner.packed_restore(corrupt, native, changed, elf=elf, dependency=elf_dependencies)


class RealSourceTests(unittest.TestCase):
    def test_ten_actual_source_entry_and_final_dependency_relations(self):
        if FIXTURE_ROOT is None:
            self.skipTest("explicit --fixture-root not supplied; production source factories are never run")
        for family in owner.FAMILIES:
            for profile in owner.PROFILES:
                with self.subTest(family=family, profile=profile):
                    root = FIXTURE_ROOT / family / profile / "artifact"
                    source = (root / "main.c").read_bytes()
                    self.assertLess(len(source), 16384)
                    raw = (root / "build.json").read_bytes()
                    self.assertLess(len(raw), owner.MAX_FILE)
                    manifest = json.loads(raw)
                    self.assertIsNone(owner.validate_target_abi_absence(manifest, family))
                    old = manifest["source_proofs"][-1]
                    candidate, before, proof = owner.derive_source(source, old, family=family, profile_id=profile,
                        entry=entry, projection=projection, dependencies=dependencies)
                    self.assertEqual(owner.pin(candidate), owner.expected(entry.OUTPUTS[family, profile]))
                    self.assertEqual(entry.restore_source(candidate, proof["entry"], projection=projection), source)
                    self.assertEqual(dependencies.restore_source(candidate, proof["dependency"]), before)
                    self.assertEqual(projection._inverse_edits(before, proof["lifted_edits"]), dependencies.restore_source(source, old))
                    self.assertTrue(proof["canonical_cleanup_last"])
                    self.assertTrue(proof["complete_parent_inverse"])
                    self.assertEqual(candidate != before, family == "C")
                    with self.assertRaises(ValueError):
                        owner.derive_source(source + b"\n", old, family=family, profile_id=profile,
                            entry=entry, projection=projection, dependencies=dependencies)
                    tampered = copy.deepcopy(old)
                    tampered["full_inverse"] = False
                    with self.assertRaises(ValueError):
                        owner.derive_source(source, tampered, family=family, profile_id=profile,
                            entry=entry, projection=projection, dependencies=dependencies)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", type=Path)
    args, remaining = parser.parse_known_args()
    if args.fixture_root is not None:
        if not args.fixture_root.is_absolute():
            parser.error("--fixture-root must be an explicit absolute origin directory")
        FIXTURE_ROOT = args.fixture_root
    unittest.main(argv=[sys.argv[0], *remaining])
