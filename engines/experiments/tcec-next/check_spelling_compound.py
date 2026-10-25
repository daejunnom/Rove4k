#!/usr/bin/env python3
"""Measure one finite, unselected compound against a fresh admitted best build.

Cost mode independently compiles and packages twice, without running an engine
or allocating its TT. B is the already selected atomic-only duplicate and is
recorded without a new compilation, encoding or counted candidate.
"""
from __future__ import annotations
import argparse
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


def require(value, message):
    if not value:
        raise ValueError(message)


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
    trusted = (SPELLING, BUILDER, PACKAGE, WRAPPER, UNLINK, OWNER)
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
    post = selected_route(manifest, admitted, builder)
    best = R.checked_artifact(build, admitted.source, R._field_pin(admitted.expected, "source"))
    last = manifest["source_proofs"][-1]
    require(last.get("schema") == spelling.SCHEMA and last.get("variant") == post["variant"]
            and last.get("family") == admitted.family and last.get("profile_id") == admitted.profile_id,
            "last admitted stage must be the exact selected individual spelling")
    parent = spelling.restore_source(best, last)
    candidate, proof = compound.transform_source(parent, family=admitted.family,
        profile_id=admitted.profile_id, spelling=spelling)
    require(compound.restore_source(candidate, proof, spelling=spelling) == parent,
            "compound complete inverse differs")
    parent_chain = manifest["source_proofs"][:-1]
    require(parent_chain, "selected parent proof chain required")
    if admitted.family == "E":
        require(parent_chain[-1].get("stage") == "canonical-e19-physical-binding"
                and parent_chain[-1].get("result_sha256") == owner.sha(parent),
                "E19 parent proof does not end at restored parent")
    else:
        require(parent_chain[-1].get("output") == owner.pin(parent),
                "selected parent proof chain does not end at restored parent")
    duplicate = admitted.family == "B"
    require(proof["duplicate_best"] == duplicate and (not duplicate or candidate == best),
            "B atomic-only compound must duplicate actual production best")
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
    (out / "parent.c").write_bytes(parent)
    proof_raw = (json.dumps(parent_chain + [proof], indent=2) + "\n").encode()
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
        compiler=manifest["compiler"], compression=manifest["compression"], resources=admitted.resources,
        wrapper_contract=admitted.wrapper_contract, parent=owner.pin(parent), compound_proof=proof,
        source_proof=owner.pin(proof_raw), scope="one finite original-coordinate union; cost only against actual admitted best")
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
                delta_vs_actual_best=dict(source=0, native=0, whole=0), measured_new_candidate=False)
        else:
            owner.LIMITS.update(aggregate_wall=600, per_command_wall=120, parent_AS=4 << 30,
                parent_CPU=240, parent_CPU_hard=300, child_AS=2 << 30, child_CPU=120)
            host = owner.Host(out, report, save)
            version = host.run([manifest["compiler"][0], "--version"], cwd=out,
                kind="actual-compiler-version").decode("utf-8", "strict").splitlines()[0]
            require(version == manifest["compile_executor_version"], "actual best compiler version changed")
            report["compiler_version"] = version
            for attempt in ("first", "repeat"):
                source, repeated = compound.transform_source(parent, family=admitted.family,
                    profile_id=admitted.profile_id, spelling=spelling)
                require(source == candidate and repeated == proof
                        and compound.restore_source(source, repeated, spelling=spelling) == parent,
                        "independent compound reproduction differs")
                directory = out / attempt
                native_dir = directory / "native"
                native_dir.mkdir(parents=True)
                (directory / "main.c").write_bytes(source)
                (directory / "source-proof.json").write_bytes(proof_raw)
                host.run(manifest["compiler"], cwd=native_dir, kind=attempt + "-compile", data=source)
                native = (native_dir / "x").read_bytes()
                header = wrapper.header(package, unlink, manifest["compiler"])
                whole = wrapper.package(package, unlink, source, manifest["compression"], manifest["compiler"])
                require(whole.startswith(header), "compound wrapper boundary differs")
                payload = whole[len(header):]
                decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                require(decoder.decompress(payload, max_length=len(source) + 1) == source
                        and decoder.eof and not decoder.unused_data, "strict compound source restoration differs")
                for name, data in (("x", whole), ("header.sh", header), ("payload.lzma", payload)):
                    (directory / name).write_bytes(data)
                (directory / "x").chmod(0o700)
                row = dict(attempt=attempt, **{key: owner.pin(data) for key, data in
                    (("source", source), ("native", native), ("whole", whole),
                     ("header", header), ("payload", payload), ("proof", proof_raw))})
                report["attempts"].append(row)
                save()
            first, repeat = report["attempts"]
            require({k: v for k, v in first.items() if k != "attempt"}
                    == {k: v for k, v in repeat.items() if k != "attempt"},
                    "independent compound native/package production differs")
            report.update(reproducible=True, measured_new_candidate=True,
                costs={key: first[key] for key in ("source", "native", "whole")},
                delta_vs_actual_best={key: first[key]["bytes"] - admitted.expected[key + "_bytes"]
                                      for key in ("source", "native", "whole")})
        require(normalized(ROOT / VERIFIER) == verifier_raw
                and all(normalized(ROOT / name) == data for name, data in current.items())
                and R.input_reader().read_regular(manifest_path, limit=16 << 20) == manifest_raw,
                "executing support or original build receipt changed")
        for name in trusted:
            require(R.checked_artifact(build, "inputs/" + name, admitted.input_pins[name]) == frozen[name]
                    and R.source_bytes(name, admitted.input_pins[name]) == frozen[name],
                    "named compound support changed during cost measurement")
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
    """Eight pure tests; no admission, compiler, encoder or engine is called."""
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
