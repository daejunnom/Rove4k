#!/usr/bin/env python3
"""Measure one finite, unselected compound against a fresh admitted best build.

Cost mode produces each final native/package independently twice. A real final
dependency edit adds CPP and pre-dependency native gates per attempt. No engine
or TT is executed. B is the already selected atomic-only duplicate and is
recorded without a new compilation, encoding or counted candidate.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = "engines/experiments/tcec-next/"
SELF = PREFIX + "check_spelling_compound.py"
COMPOUND = PREFIX + "spelling_compound.py"
SPELLING = PREFIX + "profile_spelling.py"
BUILDER = PREFIX + "profile_build.py"
VERIFIER = PREFIX + "profile_verify.py"
PACKAGE = "engines/scripts/source_package.py"
WRAPPER = PREFIX + "wrapper.py"
UNLINK = PREFIX + "self_unlink.py"
OWNER = "engines/experiments/tcec-scope/build.py"
DEPENDENCIES = PREFIX + "profile_dependencies.py"


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def normalized(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named source")
    return data


def selected_route(manifest, admitted, builder):
    require(admitted.full is True and admitted.family in ("A", "B", "C", "E", "F")
            and admitted.representation == "source-jit"
            and manifest["plan"]["entry_cleanup"] == "private-path"
            and manifest["compile_executor"] == manifest["compiler"],
            "full source-JIT/private-path build with its actual JIT compiler required")
    post = manifest.get("post_profile")
    expected_post = (dict(path=PREFIX + "profile_b.py", variant="tcec-final-lf")
        if admitted.family == "B" else dict(path=PREFIX + "profile_phase.py", variant="phase-init"))
    require(post == expected_post, "current selected pre-spelling stage required")
    b, phase = (("tcec-final-lf", "control") if admitted.family == "B" else ("control", "phase-init"))
    expected = builder.spelling_selection(admitted.family, "source-jit", b, phase, "best")
    require(manifest.get("post_spelling") == expected,
            "exact production best spelling selection required")
    return expected


def restore_selected_parent(best, proofs, *, family, profile_id, post,
                            declaration, spelling, dependencies):
    """Peel the exact final dependency stage before the pinned spelling."""
    require(family in ("A", "B", "C", "E", "F") and
            profile_id in ("test-p4", "test-p28", "tcec-provisional"),
            "one named full C family/resource profile required")
    prefix = ["rove4k.c-resource-projection.v1",
              "rove4k.profile-b-source.v1" if family == "B" else "rove4k.portable-phase-source.v1"]
    if family == "E":
        prefix.append("canonical-e19-physical-binding")
    require(declaration == dependencies.DECLARATION and isinstance(proofs, list)
            and all(isinstance(p, dict) for p in proofs)
            and [p.get("schema", p.get("stage")) for p in proofs] ==
                prefix + [spelling.SCHEMA, dependencies.SCHEMA],
            "exact selected parent, spelling and one final dependency stage required")
    dependency_proof, spelling_proof = proofs[-1], proofs[-2]
    before_dependencies = dependencies.restore_source(best, dependency_proof)
    require(dependencies.transform_source(before_dependencies) == (best, dependency_proof),
            "baseline final dependency candidate does not replay canonically")
    require(spelling_proof.get("variant") == post["variant"]
            and spelling_proof.get("family") == family
            and spelling_proof.get("profile_id") == profile_id,
            "penultimate stage must be the exact selected individual spelling")
    parent = spelling.restore_source(before_dependencies, spelling_proof)
    parent_chain = proofs[:-2]
    boundary = parent_chain[-1]
    require((boundary.get("stage") == "canonical-e19-physical-binding"
             and boundary.get("result_sha256") == pin(parent)["sha256"]) if family == "E"
            else boundary.get("output") == pin(parent),
            "restored parent does not end at its phase/B/E19 proof boundary")
    return parent, parent_chain, before_dependencies, dependency_proof


def compose_final(parent, *, family, profile_id, compound, spelling, dependencies):
    """Compose on the original domain, then append a fresh final dependency proof."""
    before, proof = compound.transform_source(parent, family=family,
        profile_id=profile_id, spelling=spelling)
    final, dependency_proof = dependencies.transform_source(before)
    require(dependencies.restore_source(final, dependency_proof) == before
            and dependencies.transform_source(before) == (final, dependency_proof)
            and compound.restore_source(before, proof, spelling=spelling) == parent,
            "compound/dependency full inverse or canonical final stage differs")
    return before, final, proof, dependency_proof


def require_duplicate_best(before, final, dependency_proof, *,
                           best_before, best_final, baseline_dependency_proof, proof):
    require(proof["duplicate_best"] is True and proof["new_candidate_count"] == 0
            and before == best_before and final == best_final
            and dependency_proof == baseline_dependency_proof,
            "B compound must duplicate actual best before and after dependencies")


def measure(build, out):
    # The current authority is called before any archived module is imported.
    verifier_raw = normalized(ROOT / VERIFIER)
    R = load("compound_current_admission", ROOT / VERIFIER)
    manifest_path = R.artifact_file(build, "build.json")
    manifest_raw = R.input_reader().read_regular(manifest_path, limit=16 << 20)
    manifest = json.loads(manifest_raw)
    admitted = R.admit_c_build(manifest, build)
    current = {name: normalized(ROOT / name) for name in (SELF, COMPOUND, VERIFIER)}
    require(current[VERIFIER] == verifier_raw, "current admission helper changed")
    compound = load("compound_current_transform", ROOT / COMPOUND)
    trusted = (SPELLING, BUILDER, PACKAGE, WRAPPER, UNLINK, OWNER, DEPENDENCIES)
    frozen = {}
    for name in trusted:
        require(name in admitted.input_pins, "named compound support is outside admitted build inputs")
        frozen[name] = R.checked_artifact(build, "inputs/" + name, admitted.input_pins[name])
        require(frozen[name] == R.source_bytes(name, admitted.input_pins[name]),
                "archived compound support is not current trusted source")
    require(R.pin(frozen[SPELLING]) == compound.HELPER_PIN, "individual spelling helper identity differs")
    # Freeze the admitted input closure before importing its authenticated code.
    out.mkdir()
    for name, expected in admitted.input_pins.items():
        data = R.checked_artifact(build, "inputs/" + name, expected)
        target = out / "inputs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for name, data in current.items():
        target = out / "support" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    own = out / "inputs"
    spelling = load("compound_frozen_individual", own / SPELLING)
    builder = load("compound_frozen_builder_policy", own / BUILDER)
    owner = load("compound_frozen_owner", own / OWNER)
    wrapper = load("compound_frozen_wrapper", own / WRAPPER)
    package = load("compound_frozen_package", own / PACKAGE)
    unlink = load("compound_frozen_unlink", own / UNLINK)
    dependencies = load("compound_frozen_dependencies", own / DEPENDENCIES)
    post = selected_route(manifest, admitted, builder)
    best = R.checked_artifact(build, admitted.source, R._field_pin(admitted.expected, "source"))
    parent, parent_chain, best_before, baseline_dependencies = restore_selected_parent(
        best, manifest["source_proofs"], family=admitted.family, profile_id=admitted.profile_id,
        post=post, declaration=manifest.get("source_dependencies"), spelling=spelling,
        dependencies=dependencies)
    candidate_before, candidate, proof, dependency_proof = compose_final(parent,
        family=admitted.family, profile_id=admitted.profile_id, compound=compound,
        spelling=spelling, dependencies=dependencies)
    duplicate = admitted.family == "B"
    require(proof["duplicate_best"] == duplicate, "compound family duplicate policy differs")
    if duplicate:
        require_duplicate_best(candidate_before, candidate, dependency_proof,
            best_before=best_before, best_final=best, baseline_dependency_proof=baseline_dependencies,
            proof=proof)
    baseline = out / "baseline"
    baseline.mkdir()
    (baseline / "build.json").write_bytes(manifest_raw)
    baseline_artifacts = {}
    for name, key in (("main.c", "source"), ("native/x", "native"), ("x", "whole"),
                      ("header.sh", "header"), ("payload.lzma", "payload")):
        data = R.checked_artifact(build, name, R._field_pin(admitted.expected, key))
        target = baseline / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        baseline_artifacts[name] = owner.pin(data)
    baseline_proof = R.input_reader().read_regular(R.artifact_file(build, "source-proof.json"), limit=16 << 20)
    require(json.loads(baseline_proof) == manifest["source_proofs"], "baseline proof file differs")
    (baseline / "source-proof.json").write_bytes(baseline_proof)
    (baseline / "before-dependencies.c").write_bytes(best_before)
    (out / "parent.c").write_bytes(parent)
    (out / "before-dependencies.c").write_bytes(candidate_before)
    proof_raw = (json.dumps(parent_chain + [proof, dependency_proof], indent=2) + "\n").encode()
    (out / "source-proof.json").write_bytes(proof_raw)
    report = dict(format=1, **{"class": "rove4k-spelling-compound-experiment-v1"},
        family=admitted.family, profile=admitted.profile_id, variant=compound.VARIANT,
        complete=False, reproducible=False, duplicate_best=duplicate,
        new_candidate_count=proof["new_candidate_count"], components=proof["components"],
        production_selected=False, production_adopted=False, runtime_qualified=False, rules_qualified=False,
        qualification=dict(selection="unselected-compound-experiment", runtime=False,
                           rules_eligibility="unproven", game_strength="unproven"),
        engine_executed=False, TT_allocated=False, compressor_sweep=False, commands=[], attempts=[],
        source_build=dict(path=str(build), manifest=owner.pin(manifest_raw), actual_best=admitted.expected,
                          artifacts=baseline_artifacts, source_proof=owner.pin(baseline_proof)),
        inputs=admitted.input_pins, support={name: owner.pin(data) for name, data in current.items()},
        compiler=manifest["compiler"], compile_executor=manifest["compiler"],
        compression=manifest["compression"], resources=admitted.resources,
        source_dependencies=dict(dependencies.DECLARATION), dependency_proof=dependency_proof,
        wrapper_contract=admitted.wrapper_contract, parent=owner.pin(parent), compound_proof=proof,
        before_dependencies=owner.pin(candidate_before), source_proof=owner.pin(proof_raw),
        scope="one original-coordinate union followed by final dependencies; cost against actual final admitted best")
    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    host = None
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    try:
        if duplicate:
            (out / "main.c").write_bytes(candidate)
            report.update(reproducible=True, costs=dict(source=owner.pin(candidate),
                native=R._field_pin(admitted.expected, "native"), whole=R._field_pin(admitted.expected, "whole")),
                delta_vs_actual_best=dict(source=0, native=0, whole=0), measured_new_candidate=False,
                baseline_dependency_evidence_reused=True, native_compilations=0, package_productions=0)
        else:
            owner.LIMITS.update(aggregate_wall=600, per_command_wall=120, parent_AS=4 << 30,
                parent_CPU=240, parent_CPU_hard=300, child_AS=2 << 30, child_CPU=120)
            host = owner.Host(out, report, save)
            version = host.run([manifest["compiler"][0], "--version"], cwd=out,
                kind="actual-compiler-version").decode("utf-8", "strict").splitlines()[0]
            require(version == manifest["compile_executor_version"], "actual best compiler version changed")
            report["compiler_version"] = version
            for attempt in ("first", "repeat"):
                before, source, repeated, repeated_dependencies = compose_final(parent,
                    family=admitted.family, profile_id=admitted.profile_id, compound=compound,
                    spelling=spelling, dependencies=dependencies)
                require(before == candidate_before and source == candidate and repeated == proof
                        and repeated_dependencies == dependency_proof,
                        "independent compound reproduction differs")
                directory = out / attempt
                native_dir = directory / "native"
                native_dir.mkdir(parents=True)
                (directory / "main.c").write_bytes(source)
                (directory / "before-dependencies.c").write_bytes(before)
                (directory / "source-proof.json").write_bytes(proof_raw)
                dependency_gate = None
                if before != source:
                    dependency_gate = dependencies.compile_gate(before, source,
                        compiler=manifest["compiler"], directory=directory / "dependency-gate",
                        run=host.run, prefix=attempt)
                host.run(manifest["compiler"], cwd=native_dir, kind=attempt + "-compile", data=source)
                native = (native_dir / "x").read_bytes()
                if dependency_gate is not None:
                    require(dependency_gate["native"] == owner.pin(native)
                            and (directory / "dependency-gate/x").read_bytes() == native,
                            "final dependency cleanup changed compound native image")
                header = wrapper.header(package, unlink, manifest["compiler"])
                whole = wrapper.package(package, unlink, source, manifest["compression"], manifest["compiler"])
                require(whole.startswith(header), "compound wrapper boundary differs")
                before_whole = (wrapper.package(package, unlink, before,
                    manifest["compression"], manifest["compiler"]) if before != source else whole)
                require(len(whole) <= len(before_whole), "final dependency cleanup grew whole compound")
                require(before_whole.startswith(header), "pre-dependency compound wrapper differs")
                before_decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                require(before_decoder.decompress(before_whole[len(header):], max_length=len(before) + 1) == before
                        and before_decoder.eof and not before_decoder.unused_data,
                        "strict pre-dependency compound restoration differs")
                if dependency_gate is not None:
                    dependency_gate["whole_cost"] = dict(before=len(before_whole), after=len(whole))
                payload = whole[len(header):]
                decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                require(decoder.decompress(payload, max_length=len(source) + 1) == source
                        and decoder.eof and not decoder.unused_data, "strict compound source restoration differs")
                for name, data in (("x", whole), ("header.sh", header), ("payload.lzma", payload)):
                    (directory / name).write_bytes(data)
                (directory / "before-dependencies.x").write_bytes(before_whole)
                (directory / "x").chmod(0o700)
                row = dict(attempt=attempt, directory=attempt, dependency_gate=dependency_gate,
                    native_bytes=len(native), native_sha256=owner.sha(native), whole_bytes=len(whole),
                    native_compilations=2 if dependency_gate is not None else 1,
                    preprocessor_invocations=2 if dependency_gate is not None else 0,
                    package_productions=2 if before != source else 1,
                    pre_dependency_package_reused=before == source,
                    pre_dependency_whole=owner.pin(before_whole), **{key: owner.pin(data) for key, data in
                    (("source", source), ("native", native), ("whole", whole),
                     ("header", header), ("payload", payload), ("proof", proof_raw))})
                report["attempts"].append(row)
                dependencies.validate_receipt(out, report, dependency_proof, source,
                                               checked=R.checked_artifact)
                save()
            first, repeat = report["attempts"]
            require({k: v for k, v in first.items() if k not in ("attempt", "directory")}
                    == {k: v for k, v in repeat.items() if k not in ("attempt", "directory")},
                    "independent compound native/package production differs")
            report.update(reproducible=True, measured_new_candidate=True,
                costs={key: first[key] for key in ("source", "native", "whole")},
                delta_vs_actual_best={key: first[key]["bytes"] - admitted.expected[key + "_bytes"]
                                      for key in ("source", "native", "whole")})
            report["native_compilations"] = sum(row["native_compilations"] for row in report["attempts"])
            report["package_productions"] = sum(row["package_productions"] for row in report["attempts"])
        require(normalized(ROOT / VERIFIER) == verifier_raw
                and all(normalized(ROOT / name) == data for name, data in current.items())
                and R.input_reader().read_regular(manifest_path, limit=16 << 20) == manifest_raw,
                "executing support or original build receipt changed")
        for name in trusted:
            require(R.checked_artifact(build, "inputs/" + name, admitted.input_pins[name]) == frozen[name]
                    and R.source_bytes(name, admitted.input_pins[name]) == frozen[name],
                    "named compound support changed during cost measurement")
        # Recheck the complete original baseline, including its stored CPP and
        # compiler stdin evidence, rather than merely its unchanged manifest.
        require(R.admit_c_build(manifest, build) == admitted,
                "actual parent admission changed during compound measurement")
        report["source_build"]["full_admission_before_after_equal"] = True
        report["source_build"]["admission_recipe_replay_is_not_new_compound_packaging"] = True
        report["inputs_rechecked"] = True
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    finally:
        try:
            if host is not None:
                host.close()
            else:
                report["host_cleanup"] = dict(unsettled_commands=0, errors=[])
                save()
        finally:
            signal.signal(signal.SIGCHLD, previous)
    report["complete"] = True
    save()
    print(json.dumps(dict(family=admitted.family, profile=admitted.profile_id,
        complete=True, duplicate_best=duplicate, new_candidate_count=proof["new_candidate_count"],
        delta_vs_actual_best=report["delta_vs_actual_best"])))


def self_test():
    """Pure composition/seam tests; no admission, compiler, codec or engine is called."""
    import copy
    from hashlib import sha256
    from types import SimpleNamespace
    import unittest
    compound = load("compound_pure_selftest", ROOT / COMPOUND)
    source = b"abcdefghijklmno"
    plans = {"clock-type": (2, "c", "CCC"), "atomic-assignment": (8, "ij", "I"),
             "launcher-short": (12, "m", "M")}
    helper = SimpleNamespace(SCHEMA="rove4k.selected-spelling-experiment.v1",
        INPUTS={(family, "test-p4"): (len(source), sha256(source).hexdigest()) for family in "ABCEF"},
        available=lambda family: compound.components(family))
    def transform(data, *, family, profile_id, variant):
        at, before, after = plans[variant]
        result = data[:at] + after.encode() + data[at + len(before):]
        return result, dict(variant=variant, input=compound.pin(data), output=compound.pin(result),
            edits=[dict(input_begin=at, output_begin=at, before=before, after=after, role=variant)])
    helper.transform_source = transform
    def restore(data, proof):
        row = proof["edits"][0]
        result = data[:row["output_begin"]] + row["before"].encode() + data[row["output_begin"] + len(row["after"]):]
        require(compound.pin(result) == proof["input"], "synthetic inverse differs")
        return result
    helper.restore_source = restore
    def make(family="A"):
        return compound.transform_source(source, family=family, profile_id="test-p4", spelling=helper)

    dependencies = load("compound_pure_dependencies", ROOT / DEPENDENCIES)
    def dependency_case(family="C", with_include=True):
        parent = (dependencies.DIRECTIVE if with_include else b"") + source
        offset = len(parent) - len(source)
        own = SimpleNamespace(SCHEMA=helper.SCHEMA,
            INPUTS={(f, "test-p4"): (len(parent), sha256(parent).hexdigest()) for f in "ABCEF"},
            available=lambda f: compound.components(f))
        def own_transform(data, *, family, profile_id, variant):
            at, before, after = plans[variant]
            at += offset
            require(data[at:at + len(before)] == before.encode(), "synthetic original span differs")
            result = data[:at] + after.encode() + data[at + len(before):]
            return result, dict(schema=own.SCHEMA, family=family, profile_id=profile_id,
                variant=variant, input=compound.pin(data), output=compound.pin(result),
                edits=[dict(input_begin=at, output_begin=at, before=before, after=after, role=variant)])
        own.transform_source = own_transform
        def own_restore(data, proof):
            require(compound.pin(data) == proof["output"], "synthetic selected output differs")
            return restore(data, proof)
        own.restore_source = own_restore
        variant = "atomic-assignment" if family in "BF" else "clock-type"
        selected, spelling_proof = own_transform(parent, family=family, profile_id="test-p4", variant=variant)
        best, dependency_proof = dependencies.transform_source(selected)
        chain = [dict(schema="rove4k.c-resource-projection.v1"),
            dict(schema="rove4k.profile-b-source.v1" if family == "B" else "rove4k.portable-phase-source.v1",
                 output=compound.pin(parent))]
        if family == "E":
            chain.append(dict(stage="canonical-e19-physical-binding", result_sha256=sha256(parent).hexdigest()))
        return dict(family=family, parent=parent, helper=own, best=best, before=selected,
                    post=dict(variant=variant), proofs=chain + [spelling_proof, dependency_proof])

    def peel(case, *, proofs=None, best=None, declaration=None):
        return restore_selected_parent(case["best"] if best is None else best,
            case["proofs"] if proofs is None else proofs, family=case["family"], profile_id="test-p4",
            post=case["post"], declaration=dependencies.DECLARATION if declaration is None else declaration,
            spelling=case["helper"], dependencies=dependencies)
    class Pure(unittest.TestCase):
        def test_original_coordinate_union(self):
            result, proof = make()
            self.assertEqual(result, b"abCCCdefghIklMno")
            self.assertEqual([r["input_begin"] for r in proof["edits"]], [2, 8, 12])
            self.assertEqual(compound.restore_source(result, proof, spelling=helper), source)
        def test_all_family_components(self):
            for family in "ACEF":
                self.assertEqual(make(family)[1]["components"], list(compound.COMPONENTS))
        def test_b_duplicate_not_counted(self):
            result, proof = make("B")
            self.assertEqual(result, transform(source, family="B", profile_id="test-p4", variant="atomic-assignment")[0])
            self.assertTrue(proof["duplicate_best"])
            self.assertEqual(proof["new_candidate_count"], 0)
        def test_overlap_rejected(self):
            rows = [dict(input_begin=2, before="cd", after="X", role="x", component="x"),
                    dict(input_begin=3, before="d", after="Y", role="y", component="y")]
            with self.assertRaises(ValueError): compound._splice(source, rows)
        def test_nonpinned_parent_rejected(self):
            with self.assertRaises(ValueError): compound.transform_source(source + b"x", family="A", profile_id="test-p4", spelling=helper)
        def test_unknown_domain_rejected(self):
            for family, profile in (("D", "test-p4"), ("A", "unknown")):
                with self.assertRaises(ValueError): compound.transform_source(source, family=family, profile_id=profile, spelling=helper)
        def test_candidate_tamper_rejected(self):
            result, proof = make()
            with self.assertRaises(ValueError): compound.restore_source(result + b"x", proof, spelling=helper)
        def test_proof_gaps_and_individuals_replayed(self):
            result, proof = make()
            for field in ("protected_gaps", "individual"):
                changed = copy.deepcopy(proof)
                changed[field] = []
                with self.assertRaises(ValueError): compound.restore_source(result, changed, spelling=helper)
        def test_dependency_seam_restores_before_spelling_and_replays_after_compound(self):
            for family, include in (("C", True), ("E", True), ("E", False), ("A", False), ("F", False)):
                with self.subTest(family=family, include=include):
                    case = dependency_case(family, include)
                    parent, chain, before, old_dependencies = peel(case)
                    self.assertEqual(parent, case["parent"])
                    self.assertEqual(before, case["before"])
                    self.assertEqual(chain, case["proofs"][:-2])
                    pre, final, proof, new_dependencies = compose_final(parent, family=family,
                        profile_id="test-p4", compound=compound, spelling=case["helper"], dependencies=dependencies)
                    self.assertEqual(dependencies.restore_source(final, new_dependencies), pre)
                    self.assertEqual(compound.restore_source(pre, proof, spelling=case["helper"]), parent)
                    self.assertNotIn(dependencies.DIRECTIVE, final)
                    self.assertEqual(bool(old_dependencies["spans"]), include)
        def test_dependency_seam_rejects_missing_duplicate_order_declaration_and_tamper(self):
            case = dependency_case()
            chain = case["proofs"]
            wrong_order = chain[:-2] + [chain[-1], chain[-2]]
            altered = copy.deepcopy(chain)
            altered[-1]["output"]["sha256"] = "0" * 64
            wrong_spelling = copy.deepcopy(chain)
            wrong_spelling[-2]["variant"] = "atomic-assignment"
            for proofs in (chain[:-1], chain + [chain[-1]], wrong_order, altered, wrong_spelling):
                with self.subTest(proofs=proofs), self.assertRaises(ValueError):
                    peel(case, proofs=proofs)
            with self.assertRaises(ValueError):
                peel(case, declaration={**dependencies.DECLARATION, "variant": "control"})
            # A hash-consistent identity proof over an input that still contains
            # the reviewed include is not the canonical final transformation.
            identity = copy.deepcopy(chain[-1])
            identity.update(input=compound.pin(case["before"]), output=compound.pin(case["before"]), spans=[])
            with self.assertRaisesRegex(ValueError, "canonically"):
                peel(case, proofs=chain[:-1] + [identity], best=case["before"])
        def test_b_duplicate_compares_before_after_and_exact_dependency_proof(self):
            for include in (False, True):
                with self.subTest(include=include):
                    case = dependency_case("B", include)
                    parent, _, before_best, baseline_dependency = peel(case)
                    before, final, proof, dependency = compose_final(parent, family="B", profile_id="test-p4",
                        compound=compound, spelling=case["helper"], dependencies=dependencies)
                    require_duplicate_best(before, final, dependency, best_before=before_best,
                        best_final=case["best"], baseline_dependency_proof=baseline_dependency, proof=proof)
                    self.assertEqual(proof["new_candidate_count"], 0)
                    for pre, result, changed in ((before + b"x", final, dependency),
                        (before, final + b"x", dependency), (before, final, {**dependency, "extra": True})):
                        with self.assertRaises(ValueError):
                            require_duplicate_best(pre, result, changed, best_before=before_best,
                                best_final=case["best"], baseline_dependency_proof=baseline_dependency, proof=proof)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Pure))
    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        require(args.build is None and args.out is None, "self-test accepts no build/output")
        raise SystemExit(self_test())
    require(args.build is not None and args.out is not None, "--build and --out are required")
    build, out = args.build.resolve(), args.out.resolve()
    require(sys.platform == "linux" and platform.machine() == "x86_64"
            and args.build.is_absolute() and args.out.is_absolute() and build.is_dir()
            and not out.exists() and ROOT not in (out, *out.parents)
            and build not in (out, *out.parents)
            and not any((p / ".git").exists() for p in (out, *out.parents)),
            "existing absolute build and new external Linux x86-64 output required")
    measure(build, out)


if __name__ == "__main__":
    main()
