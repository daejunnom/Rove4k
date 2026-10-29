#!/usr/bin/env python3
"""Finite, compile-only square-scan cost probe before dependency cleanup.

Fresh current full A/C P4, P28 and W256 factories are admitted by unchanged strict
R. Their last dependency projection is inverted, the finite scan is applied,
and the same frozen dependency projection runs last. External policy is review
provenance, never a module loader or production/native admission authority.
No generated program, engine, fixture, or TT initializer is executed.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = "engines/experiments/tcec-next/"
SELF = PREFIX + "check_profile_scan_cost.py"
HELPER = PREFIX + "profile_scan.py"
TEST = PREFIX + "test_profile_scan.py"
BUILDER = PREFIX + "profile_build.py"
VERIFIER = PREFIX + "profile_verify.py"
DEPENDENCIES = PREFIX + "profile_dependencies.py"
PRODUCTION = "engines/scripts/production.py"
OWNER = "engines/experiments/tcec-scope/build.py"
PACKAGE = "engines/scripts/source_package.py"
WRAPPER = PREFIX + "wrapper.py"
UNLINK = PREFIX + "self_unlink.py"
READERS = ("engines/scripts/production_input.py", "engines/scripts/source_composition.py")
ORIGINAL_PINS = {
    PREFIX + "check_profile_square_successor.py":
        (29267, "f0b324f8a6a7d01fe8dd5196819555d291e2598bdfc5fe3628fbb6be9fc443fc"),
    PREFIX + "profile_square_successor.py":
        (8018, "3f8020a27d23056f37149461ede703d96ec7ccb17e702b67de8eaf0dfc5ef462"),
}
SUPPORT = (SELF, HELPER, TEST, BUILDER, VERIFIER, DEPENDENCIES, PRODUCTION,
           OWNER, *READERS, *ORIGINAL_PINS)
TRUSTED = (BUILDER, OWNER, DEPENDENCIES, PRODUCTION, PACKAGE, WRAPPER, UNLINK)
FAMILIES = ("A", "C")
PROFILES = ("test-p4", "test-p28", "tcec-provisional")
COST_PROFILES = PROFILES
CASES = ("control", "square-successor")
POLICY_SCHEMA = "rove4k.square-scan-policy-review.v1"
STAGE_ORDER = ["resource", "phase-init", "compound", "square-successor", "dependency-cleanup"]
CLASS = "rove4k-square-scan-AC-six-profile-cost-v1"
_EXECUTING_CODE = sys._getframe().f_code


def require(value, detail):
    if not value:
        raise ValueError(detail)


def canonical(value):
    """JSON type identity, including bool/int, and no nonfinite numbers."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def equal(left, right):
    return canonical(left) == canonical(right)


def pin(data):
    require(type(data) is bytes, "actual immutable bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def valid_pin(value):
    return (type(value) is dict and set(value) == {"bytes", "sha256"}
            and type(value["bytes"]) is int and value["bytes"] >= 0
            and type(value["sha256"]) is str and len(value["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in value["sha256"]))


def table_pin(table, key):
    value = table[key]
    require(type(value) is tuple and len(value) == 2, "finite helper pin tuple required")
    result = {"bytes": value[0], "sha256": value[1]}
    require(valid_pin(result), "finite helper pin is malformed")
    return result


def normalized(path):
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named source")
    return data


def inventory(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def load_bytes(name, path, data):
    """Execute exactly captured named source bytes, never policy evidence."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def exact_keys(value, keys, detail):
    require(type(value) is dict and set(value) == set(keys), detail)


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def parse_policy(raw):
    require(type(raw) is bytes and len(raw) <= 1 << 20, "bounded policy bytes required")
    return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=no_duplicate_keys,
                      parse_constant=reject_constant)


def compiler_for(family):
    require(type(family) is str and family in FAMILIES, "finite A/C family required")
    return ["cc", "-Os", *(["-mavx2"] if family == "C" else []),
            "-x", "c", "-", "-o", "x", "-s"]


def validate_policy(policy, helper):
    exact_keys(policy, ("schema", "stage_order", "rows", "scope", "production_selected",
                        "runtime_qualified", "rules_qualified"), "exact policy keys required")
    require(policy["schema"] == POLICY_SCHEMA and equal(policy["stage_order"], STAGE_ORDER)
            and type(policy["scope"]) is str and bool(policy["scope"]),
            "reviewed finite stage order and scope required")
    for flag in ("production_selected", "runtime_qualified", "rules_qualified"):
        require(policy[flag] is False, "review policy cannot confer qualification")
    domain = [(family, profile) for profile in PROFILES for family in FAMILIES]
    require(tuple(helper.FAMILIES) == FAMILIES and tuple(helper.PROFILES) == PROFILES
            and helper.SCHEMA == "rove4k.selected-square-scan.v1"
            and helper.DECLARATION == {"path": HELPER, "variant": "square-successor"},
            "named helper finite domain/declaration differs")
    require(all(set(getattr(helper, name)) == set(domain) for name in
                ("INPUTS", "OUTPUTS", "POST_DEPENDENCY_INPUTS", "POST_DEPENDENCY_OUTPUTS")),
            "exact six helper pin rows required")
    require(type(policy["rows"]) is list and len(policy["rows"]) == 6,
            "six ordered policy rows required")
    result = {}
    for row, key in zip(policy["rows"], domain):
        exact_keys(row, ("family", "profile_id", "input", "output", "post_dependency_input",
                         "post_dependency_output", "compiler", "compiler_version", "resources",
                         "evidence"), "exact policy row keys required")
        family, profile = key
        require(type(row["family"]) is str and type(row["profile_id"]) is str
                and (row["family"], row["profile_id"]) == key, "finite policy row order differs")
        for field, name in (("input", "INPUTS"), ("output", "OUTPUTS"),
                            ("post_dependency_input", "POST_DEPENDENCY_INPUTS"),
                            ("post_dependency_output", "POST_DEPENDENCY_OUTPUTS")):
            require(valid_pin(row[field]) and equal(row[field], table_pin(getattr(helper, name), key)),
                    "policy cannot redefine finite helper " + field)
        require(equal(row["compiler"], compiler_for(family))
                and type(row["compiler_version"]) is str and bool(row["compiler_version"]),
                "policy compiler identity differs")
        require(type(row["resources"]) is dict and row["resources"].get("id") == profile,
                "policy resource profile differs")
        canonical(row["resources"])
        evidence = row["evidence"]
        exact_keys(evidence, ("manifest", "source", "context"), "exact provenance fields required")
        require(type(evidence["context"]) is str and bool(evidence["context"]),
                "literal provenance context required")
        for name in ("manifest", "source"):
            entry = evidence[name]
            exact_keys(entry, ("path", "bytes", "sha256"), "exact provenance pin required")
            require(type(entry["path"]) is str and bool(entry["path"])
                    and valid_pin({k: entry[k] for k in ("bytes", "sha256")}),
                    "bounded provenance identity required")
        require(equal({k: evidence["source"][k] for k in ("bytes", "sha256")},
                      row["post_dependency_input"]), "provenance source is not the old final input")
        result[key] = row
    return result


def common_resources(api, policy_row):
    """Bind all six rows to the immutable common profile without allocating it."""
    family, profile = policy_row["family"], policy_row["profile_id"]
    spec = api.engine_spec(family)
    expected = api.resource_profile(profile).to_record(spec.entry_bytes)
    actual = policy_row["resources"]
    require(set(actual) == set(expected) | {"ply", "max_position_plies"}
            and all(k in actual and equal(actual[k], v) for k, v in expected.items())
            and type(actual["ply"]) is int and actual["ply"] == 128
            and type(actual["max_position_plies"]) is int and actual["max_position_plies"] == 4095,
            "policy differs from immutable common resource profile")


def cpu_limits(inherited):
    require(type(inherited) is tuple and len(inherited) == 2
            and all(type(n) is int and (n == -1 or n > 0) for n in inherited),
            "positive exact inherited CPU pair required")
    before_soft, before_hard = inherited
    require(before_hard == -1 or 0 < before_soft <= before_hard,
            "inconsistent inherited CPU limits")
    hard = min([1500] + ([before_hard] if before_hard != -1 else []))
    soft = min([1200, hard] + ([before_soft] if before_soft != -1 else []))
    factory = min(600, soft, hard)
    require(factory >= 480,
            "inherited CPU cannot admit the unchanged factory's 480-second hard limit")
    return {"parent": (soft, hard), "factory_child": factory,
            "native_child": min(120, soft, hard)}


def factory_argv(family, profile, output):
    require(type(family) is str and family in FAMILIES
            and type(profile) is str and profile in COST_PROFILES,
            "finite A/C P4/P28/W256 factory required")
    return [sys.executable, "-I", "-B", str(ROOT / BUILDER), "--entry", family,
            "--profile", profile, "--representation", "source-jit",
            "--b-variant", "control", "--phase-variant", "phase-init",
            "--spelling-variant", "compound", "--source-dependencies", "unused-includes",
            "--out", str(output)]


def selected_baseline(manifest, admitted, family, profile, builder, policy_row):
    require(admitted.family == family and admitted.profile_id == profile
            and admitted.full is True and admitted.representation == "source-jit"
            and manifest.get("family") == family and manifest.get("class") == builder.CLASS
            and manifest.get("complete") is True and manifest.get("reproducible") is True
            and manifest.get("plan", {}).get("entry_cleanup") == "private-path"
            and equal(manifest.get("compile_executor"), manifest.get("compiler"))
            and manifest.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
            "fresh complete current full source-JIT/private-path baseline required")
    require(equal(manifest["resources"], policy_row["resources"])
            and equal(admitted.resources, policy_row["resources"])
            and equal(manifest["compiler"], policy_row["compiler"])
            and manifest["compile_executor_version"] == policy_row["compiler_version"],
            "actual baseline compiler/version/resources differ from reviewed policy")
    require(manifest.get("post_profile") ==
                {"path": PREFIX + "profile_phase.py", "variant": "phase-init"}
            and equal(manifest.get("post_spelling"), builder.spelling_selection(
                family, "source-jit", "control", "phase-init", "compound"))
            and manifest.get("source_dependencies") ==
                {"path": DEPENDENCIES, "variant": "unused-includes"},
            "current full compound and final dependency selection required")
    require(manifest.get("commands") and all(
        row.get("started") is True and row.get("terminal") is True and row.get("reaped") is True
        and row.get("owned_group_absent") is True and row.get("forced_cleanup") is False
        and type(row.get("returncode")) is int and row["returncode"] == 0
        for row in manifest["commands"]), "fresh factory command settlement is incomplete")


def restored_source(whole, header, source):
    require(type(whole) is bytes and whole.startswith(header) and 0 < len(header) < len(whole),
            "actual counted wrapper boundary differs")
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    require(decoder.decompress(whole[len(header):], max_length=len(source) + 1) == source
            and decoder.eof and not decoder.unused_data,
            "strict complete source payload inverse differs")


def measure(out, policy_path):
    import resource
    require(sys.platform == "linux" and platform.machine() == "x86_64",
            "Linux x86-64 cost execution required")
    require(out.is_absolute() and not out.exists() and ROOT not in (out, *out.parents)
            and not any((p / ".git").exists() for p in (out, *out.parents)),
            "new absolute output outside every Git checkout required")
    require(policy_path.is_absolute() and ROOT not in (policy_path, *policy_path.parents)
            and not any((p / ".git").exists() for p in policy_path.parents)
            and policy_path.is_file() and not policy_path.is_symlink()
            and policy_path.stat().st_size <= 1 << 20
            and not policy_path.name.startswith(".env"), "explicit bounded external policy file required")
    policy_raw = policy_path.read_bytes()
    policy = parse_policy(policy_raw)
    captured = {name: normalized(ROOT / name) for name in SUPPORT}
    require(compile(captured[SELF], str(Path(__file__)), "exec", dont_inherit=True) == _EXECUTING_CODE,
            "captured driver differs from its actually executing code")
    for name, expected in ORIGINAL_PINS.items():
        require((len(captured[name]), sha256(captured[name]).hexdigest()) == expected,
                "fixed original experiment changed: " + name)
    out.mkdir(parents=False)
    for name, data in captured.items():
        write(out / "support", name, data)
    write(out, "review-policy.json", policy_raw)
    report = {"format": 1, "class": CLASS, "complete": False, "reproducible": False,
        "commands": [], "families": [], "support": inventory(captured),
        "review_policy": {"path": str(policy_path), **pin(policy_raw), "contents": policy,
                          "evidence_paths_loaded": False, "native_admission": False},
        "cases": list(CASES), "profiles": list(COST_PROFILES), "stage_order": STAGE_ORDER,
        "engine_executed": False, "fixture_executed": False, "TT_allocated": False,
        "runtime_qualified": False, "rules_qualified": False, "strength_qualified": False,
        "physical_placement_qualified": False, "production_selected": False,
        "production_adopted": False, "cpu_affinity": sorted(os.sched_getaffinity(0)),
        "scope": "fresh six baselines, finite source inverse and compile/package costs only"}
    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True,
                                                    allow_nan=False) + "\n")
    save()
    host = None
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    try:
        limits = cpu_limits(resource.getrlimit(resource.RLIMIT_CPU))
        as_before = resource.getrlimit(resource.RLIMIT_AS)
        require(all(value == resource.RLIM_INFINITY or value >= 4 << 30 for value in as_before),
                "inherited address space cannot admit unchanged 4GiB factory")
        report["limits"] = {"inherited_CPU": list(resource.getrlimit(resource.RLIMIT_CPU)),
            "applied_CPU": limits, "inherited_AS": list(as_before),
            "parent_AS": 4 << 30, "factory_AS": 4 << 30, "native_AS": 2 << 30,
            "aggregate_wall": 2400, "per_command_wall": 600, "tool_output_bytes": 16 << 20}
        owner = load_bytes("scan_cost_owner", ROOT / OWNER, captured[OWNER])
        require(owner.EXECUTING_BUILD == captured[OWNER], "owner reread changed after capture")
        owner.LIMITS.update(aggregate_wall=2400, per_command_wall=600,
            parent_AS=4 << 30, parent_CPU=limits["parent"][0], parent_CPU_hard=limits["parent"][1],
            child_AS=4 << 30, nested_producer_AS=4 << 30, child_CPU=limits["factory_child"],
            tool_output_bytes=16 << 20)
        class Host(owner.Host):
            def settle(self, child, row, force=False):
                if row.get("kind", "").endswith("-fresh-profile"):
                    row["cooperative_termination_seconds"] = 30
                return super().settle(child, row, force)
        host = Host(out, report, save)
        helper = load_bytes("scan_cost_projection", ROOT / HELPER, captured[HELPER])
        rows = validate_policy(policy, helper)
        api = load_bytes("scan_cost_current_contracts", ROOT / PRODUCTION, captured[PRODUCTION])
        for row in rows.values():
            common_resources(api, row)
        R = load_bytes("scan_cost_current_R", ROOT / VERIFIER, captured[VERIFIER])
        builder = load_bytes("scan_cost_current_builder_policy", ROOT / BUILDER, captured[BUILDER])
        report["pure_iteration_witness"] = helper.iteration_witness()
        baselines = []
        for profile in COST_PROFILES:
            for family in FAMILIES:
                policy_row = rows[(family, profile)]
                label = family + "-" + profile
                directory = out / label
                directory.mkdir()
                baseline = directory / "fresh-profile"
                owner.LIMITS.update(child_AS=4 << 30, child_CPU=limits["factory_child"])
                host.run(factory_argv(family, profile, baseline), cwd=directory,
                         kind=label + "-fresh-profile")
                manifest_path = R.artifact_file(baseline, "build.json")
                raw = R.input_reader().read_regular(manifest_path, limit=16 << 20)
                manifest = json.loads(raw)
                admitted = R.admit_c_build(manifest, baseline)
                selected_baseline(manifest, admitted, family, profile, builder, policy_row)
                source = R.checked_artifact(baseline, admitted.source,
                                            R._field_pin(admitted.expected, "source"))
                require(equal(pin(source), policy_row["post_dependency_input"]),
                        "fresh final source differs from finite old final input")
                inputs = {}
                for name, expected in admitted.input_pins.items():
                    data = R.checked_artifact(baseline, "inputs/" + name, expected)
                    require(data == R.source_bytes(name, expected),
                            "fresh frozen input is not current: " + name)
                    inputs[name] = data
                    write(directory / "inputs", name, data)
                require(all(name in inputs for name in TRUSTED), "baseline omitted named cost support")
                require(all(inputs[name] == captured[name] for name in
                            (BUILDER, OWNER, DEPENDENCIES, PRODUCTION)),
                        "fresh selected factory differs from captured support")
                frozen = directory / "inputs"
                tag = family + "_" + profile.replace("-", "_")
                packaging = load_bytes("scan_package_" + tag, frozen / PACKAGE, inputs[PACKAGE])
                wrapper = load_bytes("scan_wrapper_" + tag, frozen / WRAPPER, inputs[WRAPPER])
                unlink = load_bytes("scan_unlink_" + tag, frozen / UNLINK, inputs[UNLINK])
                dependencies = load_bytes("scan_dependencies_" + tag, frozen / DEPENDENCIES,
                                          inputs[DEPENDENCIES])
                frozen_api = load_bytes("scan_contracts_" + tag, frozen / PRODUCTION, inputs[PRODUCTION])
                common_resources(frozen_api, policy_row)
                proofs = manifest["source_proofs"]
                require(type(proofs) is list and len(proofs) == 4
                        and proofs[-1]["schema"] == dependencies.SCHEMA,
                        "old resource/phase/compound/final-cleanup source stages required")
                old_dependency = proofs[-1]
                precleanup = dependencies.restore_source(source, old_dependency)
                require(equal(pin(precleanup), policy_row["input"]), "old precleanup source differs")
                replayed, replay_proof = dependencies.transform_source(precleanup)
                require(replayed == source and equal(replay_proof, old_dependency),
                        "frozen final dependency replay differs")
                scanned, scan_proof = helper.transform_source(precleanup, family=family, profile_id=profile)
                require(equal(pin(scanned), policy_row["output"])
                        and helper.restore_source(scanned, parse_policy(
                            json.dumps(scan_proof, allow_nan=False).encode())) == precleanup,
                        "scan precleanup pin or typed JSON inverse differs")
                candidate, dependency_proof = dependencies.transform_source(scanned)
                require(equal(pin(candidate), policy_row["post_dependency_output"])
                        and dependencies.restore_source(candidate, dependency_proof) == scanned,
                        "new final cleanup pin or inverse differs")
                assertions = proofs[0]["target_type_assertions"]
                require(type(assertions) is list and assertions
                        and all(type(value) is str and value.startswith("_Static_assert(")
                                for value in assertions), "actual resource type assertions required")
                write(directory, "projection.json",
                      (json.dumps(scan_proof, indent=2, allow_nan=False) + "\n").encode())
                row = {"family": family, "profile": profile, "complete": False,
                    "baseline_manifest": {"path": str(manifest_path), **pin(raw)},
                    "baseline_expected": admitted.expected, "inputs": inventory(inputs),
                    "resources": admitted.resources, "compiler": manifest["compiler"],
                    "compression": manifest["compression"], "projection": scan_proof,
                    "old_dependency_proof": old_dependency, "dependency_proof": dependency_proof,
                    "precleanup_input": pin(precleanup), "precleanup_output": pin(scanned),
                    "attempts": [], "stage_order": STAGE_ORDER}
                report["families"].append(row)
                baselines.append((baseline, manifest_path, raw, manifest, admitted, inputs, row))
                save()
                owner.LIMITS.update(child_AS=2 << 30, child_CPU=limits["native_child"])
                version = host.run([manifest["compiler"][0], "--version"], cwd=directory,
                    kind=label + "-actual-compiler-version").decode("utf-8", "strict").splitlines()[0]
                require(version == manifest["compile_executor_version"] == policy_row["compiler_version"],
                        "actual baseline compiler version changed")
                row["compiler_version"] = version
                for case in CASES:
                    for attempt in ("first", "repeat"):
                        before = dependencies.restore_source(source, old_dependency)
                        if case == "square-successor":
                            before, actual_proof = helper.transform_source(
                                before, family=family, profile_id=profile)
                            require(before == scanned and equal(actual_proof, scan_proof)
                                    and helper.restore_source(before, actual_proof) == precleanup,
                                    "independent precleanup scan differs")
                        actual_source, actual_dependency = dependencies.transform_source(before)
                        expected_source = source if case == "control" else candidate
                        require(actual_source == expected_source
                                and dependencies.restore_source(actual_source, actual_dependency) == before,
                                "last independent dependency cleanup differs")
                        target = directory / case / attempt
                        native_dir = target / "native"
                        native_dir.mkdir(parents=True)
                        write(target, "precleanup.c", before)
                        write(target, "main.c", actual_source)
                        prefix = f"{label}-{case}-{attempt}"
                        gate = {"changed": False, "source_equal": True, "CPP_executed": False,
                                "native_precleanup_compiled": False}
                        if before != actual_source:
                            gate = dependencies.compile_gate(before, actual_source,
                                compiler=manifest["compiler"], directory=target / "dependency-gate",
                                run=host.run, prefix=prefix)
                            gate.update(changed=True, CPP_executed=True,
                                        native_precleanup_compiled=True)
                        else:
                            require(family == "A", "only finite A has dependency no-op")
                        type_dir = target / "target-type-gate"
                        type_dir.mkdir()
                        asserted = actual_source + b"\n" + ("\n".join(assertions) + "\n").encode()
                        write(type_dir, "asserted.c", asserted)
                        host.run(manifest["compiler"], cwd=type_dir,
                                 kind=prefix + "-target-types", data=asserted)
                        host.run(manifest["compiler"], cwd=native_dir,
                                 kind=prefix + "-compile", data=actual_source)
                        native = R.input_reader().read_regular(native_dir / "x", limit=16 << 20)
                        require(R.input_reader().read_regular(type_dir / "x", limit=16 << 20) == native,
                                "type assertions changed actual shipping native bytes")
                        if gate["changed"]:
                            require(equal(gate["native"], pin(native))
                                    and R.input_reader().read_regular(
                                        target / "dependency-gate/x", limit=16 << 20) == native,
                                    "last cleanup changed actual native bytes")
                        header = wrapper.header(packaging, unlink, manifest["compiler"])
                        whole = wrapper.package(packaging, unlink, actual_source,
                                                manifest["compression"], manifest["compiler"])
                        restored_source(whole, header, actual_source)
                        before_whole = wrapper.package(packaging, unlink, before,
                                                       manifest["compression"], manifest["compiler"])
                        restored_source(before_whole, header, before)
                        require(len(whole) <= len(before_whole), "last cleanup grew complete artifact")
                        gate["whole_cost"] = {"before": len(before_whole), "after": len(whole)}
                        artifacts = {"source": actual_source, "native": native, "whole": whole,
                                     "header": header, "payload": whole[len(header):]}
                        if case == "control":
                            require(all(equal(pin(data), R._field_pin(admitted.expected, kind))
                                        for kind, data in artifacts.items()),
                                    "fresh control five artifact pins differ from strict admission")
                        for name, data in (("x", whole), ("header.sh", header),
                                           ("payload.lzma", whole[len(header):]),
                                           ("precleanup-x", before_whole)):
                            write(target, name, data)
                        (target / "x").chmod(0o700)
                        row["attempts"].append({"case": case, "attempt": attempt,
                            "directory": str(target), "artifacts": inventory(artifacts),
                            "precleanup": {"source": pin(before), "whole": pin(before_whole)},
                            "dependency_proof": actual_dependency, "dependency_gate": gate,
                            "target_type_gate": {"assertions": assertions, "source": pin(asserted),
                                                 "native": pin(native), "image_identical": True}})
                        save()
                costs = {}
                for case in CASES:
                    one, two = [item for item in row["attempts"] if item["case"] == case]
                    require(equal(one["artifacts"], two["artifacts"])
                            and equal(one["precleanup"], two["precleanup"])
                            and equal(one["dependency_proof"], two["dependency_proof"])
                            and equal(one["dependency_gate"], two["dependency_gate"])
                            and equal(one["target_type_gate"], two["target_type_gate"])
                            and all((Path(one["directory"]) / name).read_bytes() ==
                                    (Path(two["directory"]) / name).read_bytes()
                                    for name in ("main.c", "precleanup.c", "native/x", "x",
                                                 "header.sh", "payload.lzma", "precleanup-x")),
                            "independent complete compile/package gate productions differ")
                    costs[case] = one["artifacts"]
                row.update(costs=costs, delta={kind: costs["square-successor"][kind]["bytes"] -
                    costs["control"][kind]["bytes"] for kind in ("source", "native", "whole")},
                    costs_complete=True, reproducible=True, runtime_qualified=False,
                    rules_qualified=False, production_selected=False)
                save()
        for baseline, manifest_path, raw, manifest, admitted, inputs, row in baselines:
            require(R.input_reader().read_regular(manifest_path, limit=16 << 20) == raw
                    and R.admit_c_build(manifest, baseline) == admitted,
                    "complete actual baseline admission changed during cost measurement")
            require(all(R.source_bytes(name, expected) == inputs[name]
                        and R.checked_artifact(baseline, "inputs/" + name, expected) == inputs[name]
                        and (baseline.parent / "inputs" / name).read_bytes() == inputs[name]
                        for name, expected in admitted.input_pins.items()),
                    "current/frozen complete family closure changed")
            row.update(complete=True, full_baseline_admission_before_after_equal=True,
                       inputs_rechecked=True)
        require(all(normalized(ROOT / name) == data
                    and (out / "support" / name).read_bytes() == data
                    for name, data in captured.items()), "executing current/captured support changed")
        require(policy_path.read_bytes() == policy_raw
                and (out / "review-policy.json").read_bytes() == policy_raw,
                "external/captured reviewed policy changed")
        report.update(support_rechecked=True, policy_rechecked=True, reproducible=True,
            measured_whole_winners=[{"family": row["family"], "profile": row["profile"]}
                for row in report["families"] if row["delta"]["whole"] < 0])
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        save()
        raise
    finally:
        try:
            if host is not None:
                host.close()
            else:
                report["host_cleanup"] = {"not_constructed": True}
                save()
        finally:
            signal.signal(signal.SIGCHLD, previous)
    report["complete"] = True
    save()
    print(json.dumps({"class": CLASS, "complete": True,
        "deltas": [{"family": row["family"], "profile": row["profile"], **row["delta"]}
                   for row in report["families"]], "engine_executed": False,
        "fixture_executed": False, "TT_allocated": False}, allow_nan=False))


def self_test():
    """Pure source/JSON/property checks; no subprocess, compiler, or fixture."""
    import ast
    import copy
    import unittest
    helper_raw = normalized(ROOT / HELPER)
    helper = load_bytes("scan_pure_projection", ROOT / HELPER, helper_raw)
    def policy_fixture():
        rows = []
        for profile in PROFILES:
            for family in FAMILIES:
                key = (family, profile)
                source = table_pin(helper.POST_DEPENDENCY_INPUTS, key)
                rows.append({"family": family, "profile_id": profile,
                    "input": table_pin(helper.INPUTS, key), "output": table_pin(helper.OUTPUTS, key),
                    "post_dependency_input": source,
                    "post_dependency_output": table_pin(helper.POST_DEPENDENCY_OUTPUTS, key),
                    "compiler": compiler_for(family), "compiler_version": "pure compiler fixture",
                    "resources": {"id": profile}, "evidence": {
                        "manifest": {"path": "/never-read/manifest.json", **pin(b"fixture")},
                        "source": {"path": "/never-read/main.c", **source},
                        "context": "pure review provenance; paths are not read"}})
        return {"schema": POLICY_SCHEMA, "stage_order": list(STAGE_ORDER), "rows": rows,
                "scope": "pure policy fixture", "production_selected": False,
                "runtime_qualified": False, "rules_qualified": False}
    class Properties(unittest.TestCase):
        def test_python310_source_syntax(self):
            for name in (SELF, HELPER, TEST):
                ast.parse(normalized(ROOT / name).decode("utf-8"), feature_version=(3, 10))
        def test_ordered_visitation_and_bounds(self):
            witness = helper.iteration_witness()
            self.assertEqual(witness["values"], [r * 16 + f for r in range(8) for f in range(8)])
            self.assertEqual((witness["count"], witness["last"], witness["exit"],
                              witness["maximum_addition"]), (64, 119, 128, 128))
            self.assertIs(witness["compiled_C_executed"], False)
        def test_finite_public_domain_and_pin(self):
            for family, profile in (("B", "test-p4"), ("D", "test-p28"), ("E", "test-p4"),
                                    ("F", "tcec-provisional"), ("A", "unknown"), (True, "test-p4")):
                with self.assertRaises(ValueError):
                    helper.transform_source(b"unused", family=family, profile_id=profile)
            for family in FAMILIES:
                for profile in PROFILES:
                    with self.assertRaises(ValueError):
                        helper.transform_source(b"wrong exact input", family=family, profile_id=profile)
        def test_splices_preserve_bodies_and_inverse(self):
            source = b"prefix OLD1 body-with-continue; OLD2 early-return-body suffix"
            candidate, edits, gaps = helper._project(
                source, (("first", "OLD1", "NEW1"), ("second", "OLD2", "NEW2")))
            self.assertEqual(helper._inverse(candidate, json.loads(json.dumps(edits))), source)
            for gap in gaps:
                self.assertEqual(source[gap["input_begin"]:gap["input_begin"] + gap["bytes"]],
                                 candidate[gap["output_begin"]:gap["output_begin"] + gap["bytes"]])
        def test_duplicate_missing_and_overlapping_spans(self):
            for source, spans in ((b"OLD2 only", (("x", "OLD1", "NEW1"), ("y", "OLD2", "NEW2"))),
                                  (b"OLD1 OLD1 OLD2", (("x", "OLD1", "NEW1"), ("y", "OLD2", "NEW2"))),
                                  (b"ABCDE", (("x", "ABC", "a"), ("y", "BCD", "b")))):
                with self.assertRaises(ValueError):
                    helper._project(source, spans)
        def test_inverse_rejects_bool_or_bad_coordinate(self):
            candidate, edits, _ = helper._project(b"prefix OLD1 middle OLD2 suffix",
                (("r", "OLD1", "NEW1"), ("s", "OLD2", "NEW2")))
            for coordinate in (True, -1, 1000):
                wrong = copy.deepcopy(edits)
                wrong[0]["output_begin"] = coordinate
                with self.assertRaises(ValueError):
                    helper._inverse(candidate, wrong)
        def test_selected_finite_factory_arguments(self):
            for family in FAMILIES:
                for profile in COST_PROFILES:
                    command = factory_argv(family, profile, Path("/owned/fresh"))
                    self.assertEqual(command[command.index("--spelling-variant") + 1], "compound")
                    self.assertEqual(command[command.index("--profile") + 1], profile)
                    self.assertNotIn("--runtime", command)
            with self.assertRaises(ValueError):
                factory_argv("A", "unknown", Path("/owned/fresh"))
        def test_cpu_clamps_inherited_limits(self):
            for inherited in ((-1, -1), (600, 700), (480, 500), (1200, 1300)):
                result = cpu_limits(inherited)
                soft, hard = result["parent"]
                self.assertLessEqual(soft, hard)
                self.assertLessEqual(result["factory_child"], min(soft, hard, 600))
                self.assertLessEqual(result["native_child"], min(soft, hard, 120))
                for actual, before in zip((soft, hard), inherited):
                    if before != -1:
                        self.assertLessEqual(actual, before)
            with self.assertRaises(ValueError):
                cpu_limits((479, 500))
        def test_cpu_invalid_types_and_order(self):
            for inherited in ((True, 500), (0, 500), (501, 500), (-2, 500), (500,), [500, 600]):
                with self.assertRaises(ValueError):
                    cpu_limits(inherited)
        def test_codec_rejects_tail_wrong_source_and_truncation(self):
            source, header = b"test source bytes", b"counted-header\n"
            payload = lzma.compress(source, format=lzma.FORMAT_ALONE)
            restored_source(header + payload, header, source)
            for whole, expected in ((header + payload + b"tail", source),
                                    (header + payload, b"wrong source"),
                                    (header + payload[:-2], source)):
                with self.assertRaises((ValueError, lzma.LZMAError)):
                    restored_source(whole, header, expected)
        def test_typed_policy_domain_and_provenance(self):
            policy = policy_fixture()
            self.assertEqual(set(validate_policy(policy, helper)),
                             {(f, p) for p in PROFILES for f in FAMILIES})
            for field, value in (("production_selected", 0), ("runtime_qualified", True),
                                 ("stage_order", list(reversed(STAGE_ORDER))), ("extra", False)):
                wrong = copy.deepcopy(policy)
                wrong[field] = value
                with self.assertRaises(ValueError):
                    validate_policy(wrong, helper)
        def test_policy_cannot_redefine_helper_or_compiler(self):
            for field, value in (("input", {"bytes": True, "sha256": "0" * 64}),
                                 ("compiler", ["false"]), ("family", "B")):
                wrong = policy_fixture()
                wrong["rows"][0][field] = value
                with self.assertRaises(ValueError):
                    validate_policy(wrong, helper)
            wrong = policy_fixture()
            wrong["rows"].reverse()
            with self.assertRaises(ValueError):
                validate_policy(wrong, helper)
        def test_duplicate_json_and_nonfinite_numbers_fail(self):
            for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
                with self.assertRaises(ValueError):
                    parse_policy(raw)
        def test_existing_experiments_remain_fixed(self):
            for name, expected in ORIGINAL_PINS.items():
                actual = normalized(ROOT / name)
                self.assertEqual((len(actual), sha256(actual).hexdigest()), expected)
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Properties))
    require(result.wasSuccessful(), "scan compile-only cost pure self-tests failed")
    require(normalized(ROOT / HELPER) == helper_raw, "pure helper changed during self-test")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        require(args.out is None and args.policy is None,
                "pure self-test constructs no cost outputs or policy readers")
        self_test()
    else:
        require(args.out is not None and args.policy is not None,
                "one explicit new external output and policy required")
        measure(args.out, args.policy)


if __name__ == "__main__":
    main()
