"""Pure finite header contracts plus an opt-in actual-artifact checker.

Default tests use real literal header bytes, never fabricated source/native
images or patched production pins. check_actual_artifacts is called only by
an independently authorized owner with the six named actual artifact parts.
No compiler, codec, engine entry, TT or project factory is run by this module.
"""
import importlib.util
import json
from pathlib import Path
import sys
import unittest


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pure_profile_header", HERE / "profile_header.py")
header_owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(header_owner)

MINIMAL_HEADERS = {
    "B": (b'#!/bin/bash\nset -eo pipefail\nf=`mktemp`\n'
          b'tail -n+6 "$0"|xz -d|cc -Os -xc - -o"$f"\nexec "$f"\n'),
    "F": (b'#!/bin/bash\nset -eo pipefail\nf=`mktemp`\n'
          b'tail -n+6 "$0"|xz -d|cc -Os -xc - -o"$f" -s\nexec "$f"\n'),
}
MINIMAL_PINS = {
    "B": dict(bytes=91, sha256="f97594b112adc7a83d181202aa754275cef25de3333c77e9da49bb859814de27"),
    "F": dict(bytes=94, sha256="44b95bde0944d710e4bd20c4ab2a8c3d380c824bfc442f54e69901e6bb32406e"),
}


def clone(value):
    return json.loads(json.dumps(value))


def selected(family):
    return dict(family=family, representation="source-jit",
        b_variant="tcec-final-lf" if family == "B" else "control",
        phase_variant="control" if family == "B" else "phase-init",
        post_spelling=(dict(path=header_owner.NEXT + "profile_spelling.py", selection="best",
                            variant="atomic-assignment") if family == "B" else
                       dict(path=header_owner.NEXT + "spelling_compound.py", selection="compound-v2",
                            variant="clock-atomic-launcher-parentheses")),
        post_scan=None, dependencies="unused-includes", variant="minimal", post_ep=None)


def must_reject(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError("altered header recipe/artifact unexpectedly admitted")


def check_actual_artifacts(source, native, control_header, header, payload, whole, *, family, profile_id,
                           expanded=None, context=None, host="ubuntu24-gcc13-glibc239", observation_native=None):
    """Exercise the complete pure owner against caller-supplied actual bytes.

    This is not I/O admission: the caller authenticates named file/command
    provenance first. The optional CPP/context check requires both values;
    a target observation supplies its separate native as observation_native.
    Every negative mutation changes real input or metadata, never the policy.
    """
    owner = header_owner
    compiler = list(owner.BUILD_COMPILERS[family])
    policy = owner.compiler_policy(family, profile_id, source, compiler, compiler, owner.BUILD_VERSION)
    actual = dict(source=source, native=native, control_header=control_header, header=header,
                  payload=payload, whole=whole)
    control_whole, proof = owner.check_artifacts(policy, **actual)
    if control_whole != control_header + payload or whole != header + payload:
        raise AssertionError("actual same-payload package relation differs")
    if proof["whole_delta"] != (-18 if family == "B" else -9):
        raise AssertionError("actual independent header cost differs")
    if proof["runtime_qualified"] or proof["selected"]:
        raise AssertionError("pure artifact checker acquired runtime/selection authority")
    candidate, inverse = owner.transform_header(control_header, family=family, profile_id=profile_id)
    if candidate != header or owner.restore_header(header, inverse) != control_header:
        raise AssertionError("actual header replay/inverse differs")
    for key in actual:
        altered = dict(actual)
        altered[key] += b" "
        must_reject(lambda altered=altered: owner.check_artifacts(policy, **altered))
    for key, value in (("compiler", policy["wrapper_compiler"]),
                       ("compile_executor", policy["wrapper_compiler"]),
                       ("wrapper_compiler", policy["compiler"]),
                       ("compiler_version", "cc (unmeasured) 13.3.0"),
                       ("runtime_qualified", True), ("selected", True)):
        altered = clone(policy)
        altered[key] = value
        must_reject(lambda altered=altered: owner.check_artifacts(altered, **actual))
    for executor, version in ((policy["wrapper_compiler"], owner.BUILD_VERSION),
                              (compiler, "cc (unmeasured) 13.3.0")):
        must_reject(lambda executor=executor, version=version: owner.compiler_policy(
            family, profile_id, source, compiler, executor, version))
    observation = None
    if expanded is not None or context is not None or observation_native is not None:
        if expanded is None or context is None:
            raise AssertionError("actual CPP and context must be supplied together")
        if host != "ubuntu24-gcc13-glibc239" and observation_native is None:
            raise AssertionError("a target observation requires its separate actual native")
        observed_native = native if observation_native is None else observation_native
        observation = owner.check_compiler_observation(policy, source=source, expanded=expanded,
            native=observed_native, host=host, context=context)
        must_reject(lambda: owner.check_compiler_observation(policy, source=source, expanded=expanded + b" ",
            native=observed_native, host=host, context=context))
        changed = clone(context)
        changed["libc"] = "unmeasured"
        must_reject(lambda: owner.check_compiler_observation(policy, source=source, expanded=expanded,
            native=observed_native, host=host, context=changed))
    return dict(family=family, profile_id=profile_id, artifact_proof=proof, observation=observation,
                compiler_executed=False, payload_decoded=False, runtime_qualified=False, selected=False)


class HeaderContracts(unittest.TestCase):
    def test_exact_full_selection_and_controls(self):
        for family in ("B", "F"):
            kwargs = selected(family)
            self.assertEqual(header_owner.selection(**kwargs), header_owner.DECLARATION)
            kwargs["variant"] = "control"
            self.assertIsNone(header_owner.selection(**kwargs))
        kwargs = selected("B")
        kwargs.update(family="D", representation="self-contained-elf", variant="control")
        self.assertIsNone(header_owner.selection(**kwargs))

    def test_source_jit_and_recipe_boundaries(self):
        for family in ("B", "F"):
            base = selected(family)
            for key, value in (("family", "D"), ("representation", "self-contained-elf"),
                               ("representation", "packed-native"), ("b_variant", "unknown"),
                               ("phase_variant", "unknown"), ("post_spelling", None),
                               ("post_scan", {}), ("post_ep", {}),
                               ("dependencies", "control"), ("variant", "unknown")):
                with self.subTest(family=family, field=key, value=value):
                    changed = dict(base)
                    changed[key] = value
                    with self.assertRaises(ValueError):
                        header_owner.selection(**changed)

    def test_actual_literal_header_projection_and_inverse(self):
        for family in ("B", "F"):
            for profile in header_owner.PROFILES:
                with self.subTest(family=family, profile=profile):
                    control = header_owner.HEADERS[family]
                    result, proof = header_owner.transform_header(control, family=family, profile_id=profile)
                    self.assertEqual(result, MINIMAL_HEADERS[family])
                    self.assertEqual(header_owner.pin(result), MINIMAL_PINS[family])
                    self.assertEqual(header_owner.restore_header(result, proof), control)
                    self.assertEqual(result.splitlines()[:3], control.splitlines()[:3])
                    self.assertEqual(result.splitlines()[4:], control.splitlines()[4:])
                    self.assertEqual(len(result.splitlines()), 5)
                    self.assertFalse(proof["build_compiler_changed"])
                    self.assertFalse(proof["runtime_qualified"])

    def test_header_and_proof_mutations_fail_closed(self):
        for family in ("B", "F"):
            control = header_owner.HEADERS[family]
            output, proof = header_owner.transform_header(control, family=family, profile_id="test-p4")
            for changed in (control + b"\n", control.replace(b"set -eo pipefail", b"set -e"),
                            control.replace(b"tail -n+6", b"tail -n+5"),
                            control.replace(b"mktemp", b"mktemp -u"),
                            control.replace(b'exec "$f"', b'exec "$f" "$@"'),
                            control.replace(b"\n", b"\r\n")):
                with self.assertRaises(ValueError):
                    header_owner.transform_header(changed, family=family, profile_id="test-p4")
            with self.assertRaises(ValueError):
                header_owner.restore_header(output + b" ", proof)
            for key, value in (("wrapper_compiler", proof["compiler"]), ("full_inverse", False),
                               ("deleted", []), ("runtime_qualified", True),
                               ("selected", True), ("untrusted_waiver", True)):
                changed = clone(proof)
                changed[key] = value
                with self.assertRaises(ValueError):
                    header_owner.restore_header(output, changed)

    def test_policy_keeps_build_and_wrapper_compiler_roles_separate(self):
        minimal_sizes = {"B": (4053, 4063, 4054), "F": (3578, 3593, 3580)}
        for family in ("B", "F"):
            for profile, size in zip(header_owner.PROFILES, minimal_sizes[family]):
                policy = header_owner.expected_policy(family, profile)
                self.assertEqual(policy["compiler"], policy["compile_executor"])
                self.assertEqual(policy["compiler"].count("-pthread"), 1)
                self.assertNotIn("-pthread", policy["wrapper_compiler"])
                if family == "B":
                    self.assertIn("-std=c11", policy["compiler"])
                    self.assertNotIn("-std=c11", policy["wrapper_compiler"])
                self.assertEqual(policy["minimal"]["whole"]["bytes"], size)
                self.assertEqual(policy["original"]["payload"], policy["minimal"]["payload"])
                producer = policy["compatibility"]["ubuntu24-gcc13-glibc239"]
                target = policy["compatibility"]["ubuntu22-gcc11-glibc235"]
                self.assertEqual(policy["source"], producer["source"])
                self.assertEqual(policy["source"], target["source"])
                self.assertEqual(policy["native"], producer["native"])
                self.assertNotEqual(policy["native"], target["native"])
                self.assertNotEqual(producer["CPP"], target["CPP"])
                self.assertFalse(policy["evidence"]["cross_host_native_identity_claimed"])
                self.assertTrue(policy["requires_actual_runtime_image"])
                self.assertFalse(policy["runtime_qualified"])
                policy["compatibility"]["ubuntu22-gcc11-glibc235"]["context"]["libc"] = "mutated"
                self.assertEqual(header_owner.expected_policy(family, profile)["compatibility"]
                                 ["ubuntu22-gcc11-glibc235"]["context"]["libc"], "2.35")

    def test_finite_policy_and_unauthenticated_artifacts_rejected(self):
        for family, profile in (("A", "test-p4"), ("D", "test-p4"), ("F", "unknown"), (True, "test-p4")):
            with self.assertRaises(ValueError):
                header_owner.expected_policy(family, profile)
        for family in ("B", "F"):
            policy = header_owner.expected_policy(family, "test-p4")
            with self.assertRaises(ValueError):
                header_owner.compiler_policy(family, "test-p4", b"", policy["compiler"],
                                             policy["compiler"], header_owner.BUILD_VERSION)
            for key, value in (("wrapper_compiler", policy["compiler"]), ("runtime_qualified", True),
                               ("selected", True), ("untrusted_waiver", True)):
                changed = clone(policy)
                changed[key] = value
                with self.assertRaises(ValueError):
                    header_owner.check_artifacts(changed, source=b"", native=b"", control_header=b"",
                                                 header=b"", payload=b"", whole=b"")
            with self.assertRaises(ValueError):
                header_owner.check_compiler_observation(policy, source=b"", expanded=b"", native=b"",
                                                        host="gcc-any", context={})


if __name__ == "__main__":
    unittest.main()
