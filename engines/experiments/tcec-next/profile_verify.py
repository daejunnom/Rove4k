#!/usr/bin/env python3
"""Qualify an explicitly generated C resource profile on the current host.

Build reproduction, actual runtime observations, size eligibility and event
hardware confirmation remain separate. The host gate runs before creating an
output directory or starting a wrapper; it never probes capacity by allocating
a large TT. Historical literal verifier admissions are not modified.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import signal
import stat
import struct
import sys
import time

try:
    import resource
except ImportError:  # The pure admission tests also run on Windows.
    resource = None

sys.dont_write_bytecode = True
_EXECUTING_CODE = sys._getframe().f_code
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CLASS = "rove4k-production-profile-v1"
SUPPORT = {
    "engines/experiments/tcec-scope/verify.py":
        "b39321386f4ff2520ec7f7185178e01d9b9a005965c0840929d848d87c92fb48",
    "engines/compact/tiny-entry-d/verify.py":
        "18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae",
    "engines/tests/chess_oracle.py":
        "aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8",
}
_CONSTRUCTING = False
_DEFERRED = None
_TARGET_HELPER = None
_INPUT_HELPER = None
_CLOUD_PROVIDER = None
INPUT_READER = "engines/scripts/production_input.py"
CLOUD_PROVIDER = "engines/experiments/strength/cloud_runtime.py"
RSS_ACCOUNTING = "smaps_rollup"
SPELLING = "engines/experiments/tcec-next/profile_spelling.py"
SPELLING_SCHEMA = "rove4k.selected-spelling-experiment.v1"
SPELLING_PIN = {"bytes": 9921, "sha256": "7ec393bc9c805ee8e1e6d715f40cb9883f829e3c6b01e2f71f31701e35136ea8"}
BEST_SPELLING = {"A": "clock-type", "B": "atomic-assignment", "C": "clock-type",
                 "E": "clock-type", "F": "atomic-assignment"}
TARGET_SUPPORT = ("engines/experiments/tcec-next/target_runtime.py",
                  "engines/experiments/tcec-next/profile_compiler.py")


def require(value, detail):
    if not value:
        raise ValueError(detail)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def executing_source(data):
    require(compile(data, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "qualifier source changed after this process compiled its executing module")
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def contracts():
    return load("profile_runtime_contracts", ROOT / "engines/scripts/production.py")


def input_reader():
    """One shared reader for the new artifact/target admission boundaries."""
    global _INPUT_HELPER
    if _INPUT_HELPER is None:
        _INPUT_HELPER = sys.modules.get("rove4k_production_input")
        if _INPUT_HELPER is None:
            _INPUT_HELPER = load("rove4k_production_input", ROOT / INPUT_READER)
        require(Path(_INPUT_HELPER.__file__).resolve() == ROOT / INPUT_READER,
                "shared input reader came from another source path")
        _INPUT_HELPER = _INPUT_HELPER.cached_module()
    return _INPUT_HELPER


def _json_equal(left, right):
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def runtime_feature_required(qualifier_source, name, literal):
    """Derive a new observation contract from its frozen qualifier source."""
    declarations = []
    for node in ast.parse(qualifier_source).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                and target.id == name for target in node.targets):
            require(isinstance(node.value, ast.Constant), "frozen runtime feature declaration must be literal")
            declarations.append(node.value.value)
    require(declarations in ([], [literal]), "frozen runtime feature declaration differs")
    return bool(declarations)


def runtime_reader_required(qualifier_source):
    return runtime_feature_required(qualifier_source, "INPUT_READER", INPUT_READER)


def artifact_file(root, name):
    """Resolve only regular, unlinked-to-other-input files inside this build."""
    root = Path(root).resolve(strict=True)
    path = Path(name)
    path = path if path.is_absolute() else root / path
    for component in (path, *path.parents):
        if component == root:
            break
        require(not component.is_symlink(), "artifact cannot follow a symlink")
    path = path.resolve(strict=True)
    require(path.is_relative_to(root) and path.is_file(), "artifact escaped its build")
    require(path.stat().st_nlink == 1, "artifact cannot be a hard-linked input")
    return path


def checked_artifact(root, name, expected):
    path = artifact_file(root, name)
    require(type(expected.get("bytes")) is int and 0 <= expected["bytes"] <= 16 << 20,
            "artifact byte extent is not admitted")
    data = input_reader().read_regular(path, limit=expected["bytes"])
    require(len(data) == expected["bytes"], "artifact size differs: " + str(name))
    require(pin(data) == expected, "artifact identity differs: " + str(name))
    return data


def _field_pin(record, prefix):
    return {key: record[prefix + "_" + key] for key in ("bytes", "sha256")}


def source_bytes(relative, expected=None):
    # This checks path names before reading. A manifest cannot request secrets,
    # heavy trees or an arbitrary filesystem path through source provenance.
    api = contracts()
    logical = api._logical_path(relative)
    require(logical.startswith("engines/"), "verifier input must be an engine source")
    path = artifact_file(ROOT, logical)
    data = input_reader().read_regular(path, limit=16 << 20).replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in verifier source")
    if expected is not None:
        require(pin(data) == expected, "current source differs from frozen input: " + relative)
    return data


def support_modules():
    for path, digest in SUPPORT.items():
        require(pin(source_bytes(path))["sha256"] == digest, "frozen runtime helper changed: " + path)
    scope = load("profile_runtime_scope", ROOT / "engines/experiments/tcec-scope/verify.py")
    owner = load("profile_runtime_owner", ROOT / "engines/compact/tiny-entry-d/verify.py")
    oracle = load("profile_runtime_oracle", ROOT / "engines/tests/chess_oracle.py")
    return scope, owner, oracle


def restore_payload(payload, maximum):
    require(0 <= maximum <= 4 << 20, "restoration extent exceeds the profile source domain")
    decoder = lzma.LZMADecompressor()
    value = decoder.decompress(payload, max_length=maximum + 1)
    require(len(value) <= maximum and decoder.eof and not decoder.unused_data,
            "payload must be one bounded, complete stream")
    return value


@dataclass(frozen=True)
class AdmittedBuild:
    family: str
    profile_id: str
    representation: str
    program: str
    source: str | None
    native: str
    expected: dict
    resources: dict
    runtime_policy: dict
    wrapper_contract: dict
    input_pins: dict
    source_contract: dict
    full: bool = True


def target_module():
    global _TARGET_HELPER
    if _TARGET_HELPER is None:
        _TARGET_HELPER = load("profile_validated_target_reference", HERE / "target_runtime.py")
    return _TARGET_HELPER


def cloud_bridge_available():
    """Probe executable feature APIs before a controller can launch a host."""
    helper = target_module()
    if (not all(callable(getattr(helper, name, None)) for name in
                ("sealed_source_binding", "compiler_receipt_binding", "_compiler_module")) or
            not all(isinstance(getattr(helper, name, None), type) for name in
                    ("ValidatedSourceEvidence", "ValidatedCompilerEvidence"))):
        return False
    compiler = helper._compiler_module()
    mode = getattr(compiler, "program_provenance_enabled", None)
    return (getattr(compiler, "SCHEMA", None) == "rove4k.profile-compiler.v1" and callable(mode)
            and mode(True, False, system=True) is True and mode(False, False, system=True) is False)


def cloud_runtime_supported(provider):
    """Register only the compiled canonical EC2 provider from this source tree."""
    global _CLOUD_PROVIDER
    if not isinstance(provider, type(sys)) or not getattr(provider, "__file__", None):
        return False
    if (Path(provider.__file__).resolve() != ROOT / CLOUD_PROVIDER or
            sys.modules.get("rove4k_cloud_runtime") is not provider or
            getattr(provider, "CANONICAL_MODULE", None) != "rove4k_cloud_runtime"):
        return False
    data = source_bytes(CLOUD_PROVIDER)
    require(compile(data, provider.__file__, "exec", dont_inherit=True) == provider._EXECUTING_CODE,
            "cloud provider source changed after its module was compiled")
    require(provider.canonical_provider() is provider,
            "cloud provider canonical module identity differs")
    if not cloud_bridge_available():
        return False
    _CLOUD_PROVIDER = provider
    return True


def cloud_provider():
    require(_CLOUD_PROVIDER is not None and cloud_runtime_supported(_CLOUD_PROVIDER),
            "canonical EC2 cloud provider has not been registered")
    return _CLOUD_PROVIDER


def reference_kind(reference):
    if type(reference) is target_module().TargetRuntimeReference:
        return "ci"
    if _CLOUD_PROVIDER is not None and type(reference) is cloud_provider().CloudRuntimeReference:
        return "cloud"
    raise ValueError("runtime image requires a validated TargetRuntimeReference or canonical CloudRuntimeReference, not a native map")


def cloud_source_binding(admitted, build, *, source_bundle, source_seal, source_origin,
                         seed_root, member_map, restored_layout):
    provider = cloud_provider()
    require(type(restored_layout) is provider.OriginalLayout,
            "cloud source requires a validated canonical OriginalLayout")
    restored_layout.revalidate()
    return target_module().sealed_source_binding(admitted, Path(build), verify=sys.modules[__name__],
        source_bundle=Path(source_bundle), source_seal=Path(source_seal), source_origin=source_origin,
        seed_root=Path(seed_root), member_map=member_map, restored_layout=restored_layout.to_record())


def cloud_compiler_binding(admitted, build, compiler_receipt, *, source_binding):
    helper = target_module()
    require(type(source_binding) is helper.ValidatedSourceEvidence,
            "cloud compiler requires validated source evidence, not a source map")
    source_binding.assert_admission(admitted, Path(build))
    source_binding.revalidate(verify=sys.modules[__name__])
    result = helper.compiler_receipt_binding(admitted, Path(build), Path(compiler_receipt),
        verify=sys.modules[__name__], source_binding=source_binding)
    require(type(result) is helper.ValidatedCompilerEvidence,
            "cloud compiler authority must retain its validated evidence type")
    record = result.to_record()
    require(set(record) == {"native_path", "native", "compiler_context", "compiler_inputs", "evidence"},
            "cloud compiler authority record differs")
    return record


def cloud_rules_receipt(admitted, build, rules_path, *, source_binding):
    helper = target_module()
    require(type(source_binding) is helper.ValidatedSourceEvidence,
            "cloud rules require validated source evidence, not a source map")
    source_binding.assert_admission(admitted, Path(build))
    source_binding.revalidate(verify=sys.modules[__name__])
    original = source_binding.member_bytes(Path(rules_path))
    rules_receipt(admitted, Path(build), Path(rules_path))
    require(source_binding.member_bytes(Path(rules_path)) == original,
            "sealed cloud rules changed during source-bound validation")
    source_binding.revalidate(verify=sys.modules[__name__])
    return Path(rules_path)


def reference_support_pins(reference):
    record = reference.to_record()
    if reference_kind(reference) == "ci":
        return {TARGET_SUPPORT[0]: record["reference_validator"]["sha256"],
                TARGET_SUPPORT[1]: record["compiler_tools"][TARGET_SUPPORT[1]]["sha256"]}
    provider = cloud_provider()
    evidence = record["compiler_evidence"]
    source = reference.source_evidence
    require(type(source) is target_module().ValidatedSourceEvidence
            and source.to_record() == record["source_binding"],
            "cloud runtime support lost its exact typed source evidence")
    sources = {**source.source_provenance_tools, **evidence["compiler_tools"]}
    validator = evidence["reference_validator"]
    sources[validator["path"]] = {key: validator[key] for key in ("bytes", "sha256")}
    for name in provider.HOST_SOURCE_FILES:
        require(name.startswith("engines/experiments/strength/"), "cloud support escaped its source domain")
        sources[name] = pin(source_bytes(name))
    return {name: value["sha256"] for name, value in sources.items()}


def runtime_image(admitted, build, reference=None):
    """Select an image expectation without modifying the source build map."""
    if reference is None:
        expected = _field_pin(admitted.expected, "native")
        return expected, checked_artifact(build, admitted.native, expected)
    kind = reference_kind(reference)
    record = reference.to_record()
    require(admitted.representation == "source-jit" and reference.family == admitted.family
            and reference.profile == admitted.profile_id and record.get("runtime_eligible") is True
            and record.get("factory_replayed_on_target") is False
            and _json_equal(record.get("original_build_expected_contract"), admitted.expected)
            and record.get("source_build") == {"path": str(Path(build)),
                **pin(artifact_file(build, "build.json").read_bytes())},
            "validated target reference belongs to another source build/profile")
    reference.assert_admission(admitted, build)
    if kind == "cloud":
        source = reference.source_evidence
        require(type(source) is target_module().ValidatedSourceEvidence,
                "cloud runtime lost its typed source admission")
        source.assert_admission(admitted, Path(build))
        require(source.to_record() == record["source_binding"],
                "cloud runtime source record differs from its typed evidence")
    path = Path(reference.native_path)
    expected = reference.native_pin
    return expected, checked_artifact(path.parent, path.name, expected)


def revalidate_target(reference):
    if reference is not None:
        if reference_kind(reference) == "cloud":
            reference.revalidate(verify=sys.modules[__name__])
        else:
            helper = target_module()
            reference.revalidate(verify=sys.modules[__name__], expected_ci=helper.CIContext.from_environment())


def source_stages(family, post, proofs, *, post_spelling=None, source_dependencies=None,
                  representation=None, entry_cleanup=None):
    """Declare the complete finite stage grammar before loading a helper."""
    require(family in ("A", "B", "C", "E", "F") and isinstance(proofs, list)
            and all(isinstance(p, dict) for p in proofs),
            "explicit C family and ordered source proofs required")
    expected = ["rove4k.c-resource-projection.v1"]
    kind = None
    if post is not None:
        require(isinstance(post, dict) and set(post) == {"path", "variant"},
                "unrecognized post-resource source stage")
        if family == "B":
            require(post["path"] == "engines/experiments/tcec-next/profile_b.py"
                    and isinstance(post["variant"], str) and bool(post["variant"]),
                    "B requires its explicit finite post-resource helper")
            kind = "B"
            expected.append("rove4k.profile-b-source.v1")
        else:
            require(family in "ACEF" and post == {
                "path": "engines/experiments/tcec-next/profile_phase.py", "variant": "phase-init"},
                "A/C/E/F post-resource stage requires the named phase-init helper")
            kind = "phase"
            expected.append("rove4k.portable-phase-source.v1")
    if family == "E":
        expected.append("canonical-e19-physical-binding")
    if post_spelling is not None:
        require(post_spelling == {"path": SPELLING, "selection": "best", "variant": BEST_SPELLING[family]},
                "final spelling requires its exact reviewed winner and helper")
        require(representation == "source-jit" and entry_cleanup == "private-path",
                "final spelling requires full source-JIT/private-path")
        require((family == "B" and post == {"path": "engines/experiments/tcec-next/profile_b.py",
                                          "variant": "tcec-final-lf"}) or
                (family in "ACEF" and kind == "phase"),
                "final spelling requires selected phase-init ACEF or tcec-final-lf B")
        expected.append(SPELLING_SCHEMA)
    if source_dependencies is not None:
        require(source_dependencies == {
            "path": "engines/experiments/tcec-next/profile_dependencies.py",
            "variant": "unused-includes"}, "unrecognized dependency source stage")
        expected.append("rove4k.profile-dependencies.v1")
    require([p.get("schema", p.get("stage")) for p in proofs] == expected,
            "source proof stages are missing, extra, or out of order")
    return kind


def spelling_module(manifest, build, production_paths):
    """Consume the exact reviewed helper bytes, including its production role."""
    rows = [row for row in manifest["source_closure"]["inputs"] if row.get("path") == SPELLING]
    require(SPELLING in production_paths and len(rows) == 1 and rows[0].get("role") == "tool"
            and {key: rows[0].get(key) for key in SPELLING_PIN} == SPELLING_PIN
            and manifest["inputs"].get(SPELLING) == SPELLING_PIN,
            "final spelling helper production role or frozen identity differs")
    data = checked_artifact(build, "inputs/" + SPELLING, SPELLING_PIN)
    require(source_bytes(SPELLING, SPELLING_PIN) == data, "current reviewed spelling helper differs")
    path = ROOT / SPELLING
    name = "profile_runtime_reviewed_spelling"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec", dont_inherit=True), module.__dict__)
    require(module.SCHEMA == SPELLING_SCHEMA, "reviewed spelling schema differs")
    return module


def inverse_source_stages(source, inverses):
    """Undo the actual shipping body, including E19 offsets, in reverse order."""
    restored = source
    for module, proof, parent in reversed(inverses):
        if module is None:
            offset, before, after = proof["table_value_offset"], proof["before"].encode(), proof["after"].encode()
            require(restored[offset:offset + len(after)] == after, "E19 inverse span differs")
            restored = restored[:offset] + before + restored[offset + len(after):]
        else:
            restored = module.restore_source(restored, proof)
        require(restored == parent, "complete reverse-order source stage inverse differs")
    return restored


def dependency_evidence(manifest, build, declaration, proof, before, after):
    """Expose the already verified final-stage native and stdin evidence."""
    attempts, commands = [], []
    selected = set()
    for attempt in manifest["attempts"]:
        directory = attempt["directory"]
        attempts.append({"directory": directory, "dependency_gate": attempt.get("dependency_gate"),
                         "native": _field_pin(attempt, "native")})
        selected.add(directory + "-compile")
        if before != after:
            selected.update(directory + "-dependencies-" + label for label in ("before", "after", "native"))
    for row in manifest["commands"]:
        if row["kind"] not in selected:
            continue
        if row["kind"].endswith("-compile"):
            require(row["command"] == manifest.get("compile_executor", manifest["compiler"]),
                    "shipping dependency compiler argv differs")
        data = after if row["kind"].endswith(("-after", "-compile")) else before
        name = Path(row["stdout"]["path"]).with_suffix(".stdin").name
        checked_artifact(build, name, pin(data))
        commands.append({**row, "stdin": {"name": name, **pin(data)}})
    require(len(commands) == len(selected) and {row["kind"] for row in commands} == selected,
            "dependency compiler stdin evidence is incomplete")
    return {"declaration": declaration, "proof": proof, "attempts": attempts, "compiler_commands": commands}


def _resource_record(record, family):
    api = contracts()
    spec = api.engine_spec(family)
    profile = api.resource_profile(record["id"])
    expected = profile.to_record(spec.entry_bytes)
    require(all(record.get(k) == value for k, value in expected.items()),
            "resource record differs from the selected immutable profile")
    return profile, spec


def _check_command_set(manifest):
    require(manifest.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
            "producer commands have not settled")
    rows = manifest.get("commands", ())
    require(rows and all(row.get("returncode") == 0 and row.get("terminal") is True
                        and row.get("reaped") is True and row.get("owned_group_absent") is True
                        and row.get("forced_cleanup") is False for row in rows),
            "producer command failed, was forced, or is not terminal")


def admit_c_build(manifest, build):
    require(manifest.get("format") == 1 and manifest.get("class") == CLASS,
            "explicit new C production-profile build required")
    require(manifest.get("complete") is True and manifest.get("reproducible") is True,
            "new profile generation/reproduction is incomplete")
    family = manifest["family"]
    require(family in "ABCEF" and manifest["entry"] == family, "invalid C profile family")
    profile, spec = _resource_record(manifest["resources"], family)
    api = contracts()
    plan = manifest["plan"]
    representation = plan["representation"]
    actual_plan = api.ArtifactPlan(spec, profile, representation, plan["entry_cleanup"], full=True)
    require(_json_equal(plan, actual_plan.to_record()), "artifact plan/full policy differs")
    require(manifest["actual"] == {"source": "main.c", "native": "native/x", "program": "x"},
            "unrecognized profile artifact layout")
    _check_command_set(manifest)
    expected = manifest["expected_contract"]
    source = checked_artifact(build, "main.c", _field_pin(expected, "source"))
    native = checked_artifact(build, "native/x", _field_pin(expected, "native"))
    whole = checked_artifact(build, "x", _field_pin(expected, "whole"))
    header = checked_artifact(build, "header.sh", _field_pin(expected, "header"))
    payload = checked_artifact(build, "payload.lzma", _field_pin(expected, "payload"))
    require(whole == header + payload, "whole/header/payload are not the same artifact")
    attempts = manifest.get("attempts", ())
    require(len(attempts) == 2, "two fresh profile attempts required")
    for row, directory in zip(attempts, ("first", "repeat")):
        require(row["directory"] == directory and all(row.get(k) == v for k, v in expected.items()),
                "profile attempt disagrees with the selected artifact")
        for name, prefix in (("main.c", "source"), ("native/x", "native"), ("x", "whole")):
            checked_artifact(build, directory + "/" + name, _field_pin(expected, prefix))
        require(row["source_proofs"] == manifest["source_proofs"]
                and row["target_type_gate"]["image_identical"] is True,
                "profile source/target type reproduction differs")
    inputs = manifest["inputs"]
    require(inputs, "profile input closure is empty")
    closure_record = manifest["source_closure"]
    require(closure_record.get("family") == family
            and closure_record.get("admission") == "expected-pins-verified", "source closure was not pinned")
    production_paths = {row["path"] for row in closure_record["inputs"]}
    require(len(production_paths) == len(closure_record["inputs"])
            and all(row.get("role") in ("engine", "tool") for row in closure_record["inputs"]),
            "production closure has duplicate or non-production roles")
    api.SourceClosure.validate(spec,
        engine_inputs=[row["path"] for row in closure_record["inputs"] if row["role"] == "engine"],
        tool_inputs=[row["path"] for row in closure_record["inputs"] if row["role"] == "tool"], submission=True)
    proof_only = set(SUPPORT) | {"engines/scripts/verify_shell.py", "engines/tests/verify.py",
        "engines/compact/tiny-entry-f/verify.py",
        "engines/experiments/tcec-next/profile_verify.py", "engines/experiments/tcec-next/profile_rules.py"}
    require(production_paths <= set(inputs) and set(inputs) - production_paths <= proof_only,
            "unclassified input outside the explicit production/proof closure")
    for relative, value in inputs.items():
        # Proof tools describe this particular build receipt; they never enter
        # the emitted source. A later verifier revision gets its own runtime
        # snapshot instead of being falsely treated as a production change.
        api._logical_path(relative)
        data = checked_artifact(build, "inputs/" + relative, value)
        if relative in production_paths:
            require(source_bytes(relative, value) == data, "current production input differs")
    for row in closure_record["inputs"]:
        require(inputs[row["path"]] == {"bytes": row["bytes"], "sha256": row["sha256"]},
                "source closure role and frozen identity disagree")
    projection = load("profile_runtime_projection", ROOT / "engines/experiments/tcec-next/profile_source.py")
    control = manifest["control"]
    base = checked_artifact(build, "control/main.c", control["source"])
    control_raw = checked_artifact(build, "control/build.json", control["report"])
    control_manifest = json.loads(control_raw)
    require(control_manifest["complete"] is True and control_manifest["reproducible"] is True,
            "fresh source control is incomplete")
    _check_command_set(control_manifest)
    produced, proof = projection.transform_source(base, family=family, profile=profile,
                                                entry_cleanup=plan["entry_cleanup"])
    require(proof == manifest["source_proofs"][0], "resource projection proof differs")
    require(projection.restore_source(produced, proof) == base, "profile inverse differs")
    inverses = [(projection, proof, base)]
    post = manifest.get("post_profile")
    post_spelling = manifest.get("post_spelling")
    dependency_declaration = manifest.get("source_dependencies")
    post_kind = source_stages(family, post, manifest["source_proofs"], post_spelling=post_spelling,
        source_dependencies=dependency_declaration, representation=representation, entry_cleanup=plan["entry_cleanup"])
    next_stage = 1
    if post is not None:
        path = post["path"]
        require(path in production_paths, "post-resource helper is outside the production tool closure")
        helper = load("profile_runtime_post_projection", ROOT / path)
        require(post["variant"] in helper.VARIANTS, "variant is outside the explicit finite transform set")
        before_post = produced
        options = dict(profile_id=profile.id, entry_cleanup=plan["entry_cleanup"], variant=post["variant"])
        if post_kind == "phase":
            options["family"] = family
        produced, post_proof = helper.transform_source(produced, **options)
        require(post_proof == manifest["source_proofs"][next_stage]
                and helper.restore_source(produced, post_proof) == before_post,
                "post-resource projection or complete inverse differs")
        inverses.append((helper, post_proof, before_post))
        next_stage += 1
        abi_probe = post_proof.get("target_abi_probe")
        if abi_probe is not None:
            require(isinstance(abi_probe, str) and abi_probe.strip() and "\0" not in abi_probe,
                    "B ABI probe is not standalone C text")
            for attempt in attempts:
                gate = attempt.get("target_abi_gate", {})
                require(gate.get("directory") == "target-abi-gate" and gate.get("compile_only") is True
                        and gate.get("production_source_modified") is False
                        and gate.get("source") == pin(abi_probe.encode()), "B ABI assertions were not compiled separately")
                directory = attempt["directory"] + "/target-abi-gate/"
                checked_artifact(build, directory + "probe.c", gate["source"])
                checked_artifact(build, directory + "x", gate["object"])
                commands = [row for row in manifest["commands"] if row.get("kind") == attempt["directory"] + "-target-abi"]
                require(len(commands) == 1 and commands[0].get("command") ==
                        [*manifest.get("compile_executor", manifest["compiler"]), "-c"],
                        "B ABI assertion command differs from the actual native compiler")
    if family == "E":
        module = load("profile_runtime_e19", ROOT / "engines/model/e19.py")
        model = module.Model.load()
        source_model = module.Model.from_physical_source(produced, model_id="e19-admitted-source-baseline")
        before_model = produced
        produced, model_proof = model.bind_physical_table(produced, source_model=source_model)
        require(model_proof == manifest["source_proofs"][next_stage],
                "actual final E19 consumer differs")
        inverses.append((None, model_proof, before_model))
        next_stage += 1
    if post_spelling is not None:
        helper = spelling_module(manifest, build, production_paths)
        before_spelling = produced
        produced, spelling_proof = helper.transform_source(produced, family=family,
            profile_id=profile.id, variant=post_spelling["variant"])
        require(spelling_proof == manifest["source_proofs"][next_stage],
                "full final spelling proof/protected gaps differ")
        inverses.append((helper, spelling_proof, before_spelling))
        next_stage += 1
    before_dependencies = produced
    dependencies = None
    if dependency_declaration is not None:
        path = dependency_declaration["path"]
        rows = [row for row in closure_record["inputs"] if row["path"] == path]
        require(path in production_paths and len(rows) == 1 and rows[0]["role"] == "tool",
                "dependency helper is outside the production tool closure")
        helper = load("profile_runtime_dependencies", ROOT / path)
        produced, dependency_proof = helper.transform_source(produced)
        require(dependency_proof == manifest["source_proofs"][next_stage],
                "final dependency projection differs")
        require(helper.validate_receipt(build, manifest, dependency_proof, produced,
                                        checked=checked_artifact) == before_dependencies,
                "dependency compiler receipt does not bind its original source")
        inverses.append((helper, dependency_proof, before_dependencies))
        dependencies = dependency_evidence(manifest, build, dependency_declaration, dependency_proof,
                                           before_dependencies, produced)
        next_stage += 1
    require(next_stage == len(manifest["source_proofs"]), "an admitted source stage was not consumed")
    require(produced == source, "full source projection chain does not reproduce the actual consumer")
    require(inverse_source_stages(source, inverses) == base,
            "complete final consumer inverse differs from its fresh control")
    if representation == "source-jit":
        require(restore_payload(payload, len(source)) == source, "source package inverse differs")
        package = load("profile_runtime_package", ROOT / "engines/scripts/source_package.py")
        wrapper = load("profile_runtime_wrapper", ROOT / "engines/experiments/tcec-next/wrapper.py")
        unlink = load("profile_runtime_unlink", ROOT / "engines/experiments/tcec-next/self_unlink.py")
        require(wrapper.header(package, unlink, manifest["compiler"]) == header,
                "source-JIT command/dependency boundary differs")
        require(wrapper.contract(package, unlink, manifest["compiler"]) == manifest["wrapper_contract"],
                "source-JIT file ownership contract differs")
        if before_dependencies != source:
            before_whole = wrapper.package(package, unlink, before_dependencies,
                                           manifest["compression"], manifest["compiler"])
            require(wrapper.package(package, unlink, source, manifest["compression"], manifest["compiler"])
                    == whole and len(whole) <= len(before_whole),
                    "dependency cleanup did not preserve or reduce the actual complete artifact")
            require(all(row["dependency_gate"]["whole_cost"] ==
                        {"before": len(before_whole), "after": len(whole)} for row in attempts),
                    "dependency whole cost receipt differs from regenerated packaging")
    elif representation == "packed-native":
        require(restore_payload(payload, len(native)) == native, "native package inverse differs")
    else:
        raise ValueError("ELF runtime class requires its own restored-image admission; not yet qualified")
    policy = manifest["runtime_policy"]
    workers = profile.workers
    require(policy["mode"] == "per-go" and policy["variant"] == "async"
            and policy["input_during_GO"] == "asynchronous"
            and policy["startup_threads"] == policy["between_GO_threads"] == 1
            and policy["active_threads"] == workers + 1
            and policy["initialization_threads"] == workers + 1
            and policy["initialization_join_before_uci"] is True,
            "actual profile runtime topology is not admitted")
    require(manifest["resources"]["ply"] == 128
            and manifest["resources"]["max_position_plies"] == 4095,
            "profile chess-state bounds differ")
    return AdmittedBuild(family, profile.id, representation, "x", "main.c", "native/x", expected,
                         manifest["resources"], policy, manifest["wrapper_contract"], inputs,
                         {"kind": "exact-resource-projection", "proof": proof, "post_profile": post,
                          **({"post_spelling": post_spelling} if post_spelling is not None else {}),
                          **({"source_dependencies": dependencies} if dependencies is not None else {}),
                          "full_rules_generation": "pending-actual-emitted-consumer-fixture"})


def admit_d_build(manifest, build, candidate_name):
    """Admit D's separate kernel-loaded general class, not an old own-loader."""
    require(manifest.get("format") == "rove4k-D-general-source-v1" and manifest.get("family") == "D",
            "explicit new D general source build required")
    require(manifest.get("complete") is True and manifest.get("native_reproduced") is True,
            "D generation/native reproduction is incomplete")
    require(manifest.get("frozen_execution") is True,
            "D producer did not consume its frozen source/tool snapshot")
    profile, _ = _resource_record(manifest["resource"], "D")
    _check_command_set(manifest)
    require(type(manifest.get("equivalent_edits")) is bool, "D transform policy must be explicit")
    inputs = manifest.get("inputs", {})
    require(inputs and all(name in inputs for name in (
        "engines/experiments/tiny-d-submission/build.py",
        "engines/experiments/tiny-d-submission/source.py",
        "engines/experiments/tiny-d-submission/packaging.py",
        "engines/scripts/production.py")), "D production tool closure is incomplete")
    for relative, value in inputs.items():
        data = source_bytes(relative, value)
        checked_artifact(build, "inputs/" + relative, pin(data))
    producer = load("profile_runtime_d_source", ROOT / "engines/experiments/tiny-d-submission/source.py")
    files, proof = producer.prepare(profile, equivalent_edits=manifest["equivalent_edits"])
    mode = manifest.get("storage", "none")
    require(mode in ("none", "prefix", "dense", "prefix-dense")
            and manifest.get("source_reduced", False) is False, "unadmitted D storage/source reduction policy")
    if mode != "none":
        path = "engines/experiments/tiny-d-submission/storage.py"
        require(path in inputs, "D storage transform is outside the frozen production closure")
        helper = load("profile_runtime_d_storage", ROOT / path)
        before_storage = files
        files, storage_proof = helper.transform(files, prefix="prefix" in mode, dense="dense" in mode)
        require(helper.restore(files, storage_proof) == before_storage, "D storage full inverse differs")
        proof["storage"] = storage_proof
    require(_json_equal(proof, manifest["proof"]), "D current source transformation proof differs")
    for name, data in files.items():
        observed = checked_artifact(build, "generated-readable/" + name, pin(data))
        require(observed == data, "D actual generated source differs")
    candidates = [row for row in manifest["candidates"] if Path(row["path"]).name == candidate_name]
    require(len(candidates) == 1, "select one explicitly named D representation")
    candidate = candidates[0]
    require(candidate["representation"] in ("source-jit", "packed-native")
            and candidate.get("package_reproduced") is True, "D whole reproduction is incomplete")
    expected_whole = {key: candidate[key] for key in ("bytes", "sha256")}
    require(candidate["package_rebuilds"] == [expected_whole, expected_whole],
            "D complete-file repetitions differ")
    program = artifact_file(build, candidate["path"])
    whole = checked_artifact(build, program, expected_whole)
    native_row = candidate["native"]
    native_pin = {key: native_row[key] for key in ("bytes", "sha256")}
    native_path = artifact_file(build, native_row["path"])
    native = checked_artifact(build, native_path, native_pin)
    native_attempts = manifest["source_jit_native_rebuilds"] if candidate["representation"] == "source-jit" else manifest["native_rebuilds"]
    require(len(native_attempts) == 2, "D requires two actual native repetitions")
    for row in native_attempts:
        require({key: row[key] for key in native_pin} == native_pin, "D native repetition differs")
        checked_artifact(build, row["path"], native_pin)
    boundary = candidate["header_bytes"]
    require(type(boundary) is int and 0 < boundary < len(whole)
            and candidate["payload_bytes"] == len(whole) - boundary, "D header/payload extent differs")
    payload = whole[boundary:]
    restored = restore_payload(payload, candidate.get("source_bundle_bytes", len(native)))
    packaging = load("profile_runtime_d_packaging", ROOT / "engines/experiments/tiny-d-submission/packaging.py")
    if candidate["representation"] == "packed-native":
        require(restored == native, "D complete kernel ELF restoration differs")
        regenerated, detail = packaging.package_native(native, candidate["codec"])
    else:
        bundle = json.loads(restored)
        require(bundle["flags"] == manifest["flags"] and bundle["units"] == manifest["units"],
                "D JIT compiler flags/units differ")
        shipping = {}
        require(set(bundle["files"]) == set(manifest["shipping_inputs"]), "D JIT source bundle differs")
        for name, value in manifest["shipping_inputs"].items():
            require(Path(name).name == name, "D shipping source name is not local")
            data = checked_artifact(build, "shipping-inputs/" + name, value)
            require(bundle["files"][name].encode() == data, "D JIT input differs from reproduced compiler input")
            shipping[name] = data
        regenerated, detail = packaging.package_source(shipping, manifest["flags"], manifest["units"])
    require(regenerated == whole and detail["header_bytes"] == boundary,
            "D approved dependency/cleanup bootstrap differs")
    workers = profile.workers
    policy = {"mode": "persistent", "variant": "raw-clone", "startup_threads": workers + 1,
              "between_GO_threads": workers + 1, "active_threads": workers + 1,
              "input_during_GO": "asynchronous", "initialization_join_before_uci": True}
    resources = {**manifest["resource"], "ply": 128, "max_position_plies": 4095}
    expected = {**{"native_" + k: v for k, v in native_pin.items()},
                **{"whole_" + k: v for k, v in expected_whole.items()},
                "header_bytes": boundary, "payload_bytes": len(payload)}
    wrapper = {"entry_cleanup": "loader-owned-fd", "temp_strategy": candidate["cleanup"],
               "cleanup_seconds": 0, "parent_removed": candidate["representation"] == "source-jit"}
    return AdmittedBuild("D", profile.id, candidate["representation"], str(program.relative_to(build)), None,
                         str(native_path.relative_to(build)), expected, resources, policy, wrapper, inputs,
                         {"kind": "source-owned-D-kernel-image", "proof": proof,
                          "full_rules_generation": "pending-actual-emitted-consumer-fixture"})


def native_dependencies(native):
    """Inspect actual ELF program/dynamic tables, without executing readelf."""
    require(len(native) >= 64 and native[:6] == b"\x7fELF\x02\x01", "Linux ELF64 little-endian native required")
    values = struct.unpack_from("<16sHHIQQQIHHHHHH", native)
    require(values[1] in (2, 3) and values[2] == 62 and values[3] == 1,
            "x86-64 executable/shared native required")
    phoff, phsize, phcount = values[5], values[9], values[10]
    require(phsize == 56 and 0 < phcount <= 64 and phoff + phsize * phcount <= len(native),
            "native program header extent differs")
    headers = [struct.unpack_from("<IIQQQQQQ", native, phoff + phsize * i) for i in range(phcount)]
    require(any(kind == 1 and flags & 1 and vaddr <= values[4] < vaddr + filesz
                for kind, flags, _, vaddr, _, filesz, _, _ in headers),
            "native entry is outside executable file-backed bytes")
    require(sum(kind == 0x6474E551 for kind, *_ in headers) == 1,
            "native requires an explicit non-executable stack declaration")
    interpreter, needed, tags = None, [], {}
    for kind, flags, offset, address, _, file_size, memory_size, _ in headers:
        require(offset + file_size <= len(native) and file_size <= memory_size,
                "native segment exceeds file or memory extent")
        if kind == 1:
            require(not (flags & 2 and flags & 1), "native has a writable executable segment")
        if kind == 0x6474E551:
            require(not flags & 1, "native process stack is executable")
        if kind == 3:
            raw = native[offset:offset + file_size]
            require(raw.endswith(b"\0") and b"\0" not in raw[:-1], "invalid native interpreter")
            interpreter = raw[:-1].decode("ascii")
        if kind == 2:
            require(file_size % 16 == 0, "invalid native dynamic table")
            for at in range(offset, offset + file_size, 16):
                tag, value = struct.unpack_from("<qQ", native, at)
                if tag == 0:
                    break
                if tag == 1:
                    needed.append(value)
                else:
                    require(tag not in (15, 29), "native cannot use an implicit RPATH/RUNPATH dependency")
                    tags[tag] = value
    names = []
    if needed:
        require(5 in tags and 10 in tags, "native dependency string table is absent")
        address, size = tags[5], tags[10]
        found = [offset + address - vaddr for kind, _, offset, vaddr, _, file_size, _, _ in headers
                 if kind == 1 and vaddr <= address and address + size <= vaddr + file_size]
        require(len(found) == 1 and size <= 1 << 20, "native dependency string table escaped loaded bytes")
        table = native[found[0]:found[0] + size]
        for index in needed:
            require(index < len(table) and b"\0" in table[index:], "invalid native dependency name")
            names.append(table[index:].split(b"\0", 1)[0].decode("ascii"))
    permitted = {"libc.so.6", "libpthread.so.0", "libm.so.6", "libdl.so.2", "libgcc_s.so.1", "libstdc++.so.6"}
    require(set(names) <= permitted, "native has a dependency outside the qualified system-library set")
    require(interpreter in (None, "/lib64/ld-linux-x86-64.so.2", "/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"),
            "native interpreter is outside the qualified Linux system set")
    return {"ELF64_x86_64": True, "interpreter": interpreter, "DT_NEEDED": names,
            "writable_executable_segment": False, "executable_stack": False,
            "scope": "actual native program/dynamic tables; wrapper dependency separately reproduced"}


def effective_available_bytes(proc=Path("/proc"), cgroup_root=Path("/sys/fs/cgroup")):
    fields = dict(line.split(":", 1) for line in (proc / "meminfo").read_text().splitlines() if ":" in line)
    require("MemAvailable" in fields, "host does not report available physical memory")
    available = int(fields["MemAvailable"].split()[0]) * 1024
    limits = []
    for line in (proc / "self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            relative = PurePosixPath(line[3:].lstrip("/"))
            require(".." not in relative.parts, "invalid effective cgroup path")
            directory = cgroup_root.joinpath(*relative.parts)
            while True:
                maximum, current = directory / "memory.max", directory / "memory.current"
                if maximum.is_file() and current.is_file():
                    value = maximum.read_text().strip()
                    if value != "max":
                        limits.append(max(0, int(value) - int(current.read_text().strip())))
                if directory == cgroup_root:
                    break
                directory = directory.parent
        elif "memory" in line.split(":", 2)[1].split(","):
            relative = PurePosixPath(line.split(":", 2)[2].lstrip("/"))
            require(".." not in relative.parts, "invalid effective memory cgroup path")
            base = cgroup_root / "memory"
            directory = base.joinpath(*relative.parts)
            observed = False
            while True:
                maximum, current = directory / "memory.limit_in_bytes", directory / "memory.usage_in_bytes"
                if maximum.is_file() and current.is_file():
                    observed = True
                    limits.append(max(0, int(maximum.read_text().strip()) - int(current.read_text().strip())))
                if directory == base:
                    break
                directory = directory.parent
            require(observed, "cannot establish the effective cgroup-v1 memory budget")
    return min([available, *limits])


def execution_host(admitted):
    cpus = sorted(os.sched_getaffinity(0))
    topology = []
    for cpu in cpus:
        directory = Path("/sys/devices/system/cpu") / ("cpu" + str(cpu)) / "topology"
        topology.append({"cpu": cpu,
                         "socket": int((directory / "physical_package_id").read_text()),
                         "core": int((directory / "core_id").read_text())})
    physical = {(row["socket"], row["core"]) for row in topology}
    required = {"test-p4": 4, "test-p28": 28}.get(admitted.profile_id)
    one_sibling = len(cpus) == len(physical)
    placement = required is not None and len(physical) == required and one_sibling
    return {"affinity": cpus, "topology": topology, "physical_cores_exposed": len(physical),
            "one_sibling_per_physical_core": one_sibling,
            "test_physical_envelope_observed": placement,
            "scored_cloud_slot_confirmed": False,
            "role": "local functional observation; placement and target league preflight are separate",
            "oversubscribed_by_search_workers": admitted.resources["workers"] > len(cpus)}


def execution_limits(admitted, available_bytes, *, wall_seconds=600):
    api = contracts()
    profile = api.resource_profile(admitted.profile_id)
    layout = profile.layout(admitted.resources["tt_entry_bytes"])
    other = max(768 * api.MiB, profile.workers * 16 * api.MiB)
    capacity = api.host_admission(profile, layout, available_bytes,
                                 other_peak_bytes=other, reserve_bytes=256 * api.MiB)
    capacity.require()
    require(type(wall_seconds) is int and 60 <= wall_seconds <= 1200, "finite runtime wall bound required")
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)
    active_cpus = max(1, min(cpus, profile.os_threads))
    # RLIMIT_CPU counts every search thread. A constant 590s would terminate a
    # legitimate W256 GO long before its wall-clock budget on a large host.
    # Each owned session has its own 140s wall budget, within the outer alarm.
    cpu_seconds = max(180, min(140, wall_seconds - 10) * active_cpus)
    return {"admission": capacity.to_record(), "address_space_bytes": max(2 * api.GiB, layout.bytes + other),
            "CPU_seconds": [cpu_seconds, cpu_seconds + max(5, active_cpus * 2)],
            "CPU_budget_effective_cpus": active_cpus, "per_session_wall_seconds": 140,
            "wall_seconds": wall_seconds,
            "output_bytes_per_pipe": 1 << 20, "startup_seconds": 60}


def _signal(signum, frame):
    global _DEFERRED
    if _CONSTRUCTING:
        _DEFERRED = signum
        return
    raise TimeoutError("profile verifier signal " + str(signum))


def _rss_bytes(snapshot):
    value = snapshot["memory_snapshot_not_peak"]["VmRSS"].split()
    require(len(value) == 2 and value[1] == "kB", "unrecognized RSS unit")
    return int(value[0]) * 1024


def _proc_bytes(path, maximum):
    """Read a bounded proc pseudo-file; its reported st_size is normally zero."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0))
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), "ordinary proc observation required")
        chunks, count = [], 0
        while count <= maximum:
            value = os.read(descriptor, min(65536, maximum + 1 - count))
            if not value:
                break
            chunks.append(value)
            count += len(value)
        require(count <= maximum, "proc observation exceeds its byte bound")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _process_identity(raw, pid):
    prefix, fields = raw.decode("ascii").rsplit(")", 1)
    require(prefix.startswith(str(pid) + " (") and len(fields.split()) >= 20,
            "proc stat identity differs")
    fields = fields.split()
    start = int(fields[19])
    require(start > 0 and fields[0] in ("R", "S", "D", "T", "t", "I", "W", "P"),
            "startup process is no longer live")
    return {"pid": pid, "start_ticks": start, "state": fields[0]}


def rollup_rss_bytes(raw):
    rows = [line.split() for line in raw.decode("ascii").splitlines() if line.startswith("Rss:")]
    require(len(rows) == 1 and len(rows[0]) == 3 and rows[0][2] == "kB"
            and rows[0][1].isdecimal(), "one exact smaps_rollup Rss in kB required")
    value = int(rows[0][1]) * 1024
    require(0 <= value < 1 << 63, "smaps_rollup Rss extent differs")
    return value


def resident_accounting(pid, *, proc=Path("/proc")):
    """One exact resident-page walk per startup, retaining the original PID."""
    require(type(pid) is int and pid > 0, "owned process PID required")
    root = proc / str(pid)
    before = _process_identity(_proc_bytes(root / "stat", 16384), pid)
    raw = _proc_bytes(root / "smaps_rollup", 1 << 20)
    after = _process_identity(_proc_bytes(root / "stat", 16384), pid)
    require(before["start_ticks"] == after["start_ticks"], "process identity changed during resident accounting")
    return {"source": RSS_ACCOUNTING, "before": before, "after": after,
            "Rss_bytes": rollup_rss_bytes(raw), "raw": raw.decode("ascii"), "raw_pin": pin(raw)}


def startup_residency(row, snapshot, tt_bytes, *, exact_required):
    """Keep the threshold, using exact page accounting for new observations."""
    approximate = _rss_bytes(snapshot)
    if exact_required:
        account = row.get("startup_resident_accounting")
        require(isinstance(account, dict) and account.get("source") == RSS_ACCOUNTING
                and row.get("startup_RSS_source") == RSS_ACCOUNTING,
                "exact startup smaps_rollup accounting is unavailable")
        raw = account.get("raw", "").encode("ascii")
        require(len(raw) <= 1 << 20 and pin(raw) == account.get("raw_pin"),
                "exact resident observation bytes differ")
        resident = rollup_rss_bytes(raw)
        before, after = account.get("before", {}), account.get("after", {})
        require(type(before.get("start_ticks")) is int and before["start_ticks"] > 0
                and type(after.get("start_ticks")) is int
                and before.get("start_ticks") == after.get("start_ticks")
                and type(row.get("pid")) is int and type(before.get("pid")) is int
                and type(after.get("pid")) is int and before.get("pid") == after.get("pid") == row["pid"]
                and before.get("state") in ("R", "S", "D", "T", "t", "I", "W", "P")
                and after.get("state") in ("R", "S", "D", "T", "t", "I", "W", "P")
                and type(account.get("Rss_bytes")) is int and account["Rss_bytes"] == resident
                and row.get("startup_VmRSS_bytes_not_peak") == approximate,
                "resident accounting identity/value or approximate telemetry differs")
    else:
        require("startup_resident_accounting" not in row and "startup_RSS_source" not in row,
                "historical qualifier did not record exact resident accounting")
        resident = approximate
    require(row.get("startup_RSS_bytes_not_peak") == resident and resident >= tt_bytes - 8192,
            "full startup TT writes were not reflected in resident pages")
    return resident


def _clean_live(scope, owned, snapshot, contract, started):
    if contract.get("entry_cleanup") == "loader-owned-fd":
        executable = Path("/proc") / str(owned.process.pid) / "exe"
        require(executable.stat().st_nlink == 0 and snapshot["exe"].endswith(" (deleted)"),
                "loader did not remove its executable pathname before entry")
        path = Path(snapshot["path"])
        if not snapshot["path"].startswith("/memfd:"):
            require(not path.exists() and not path.parent.exists(), "source-JIT private directory remains")
        require(not owned.exited(), "cleanup was not observed while engine remained alive")
        return {"entry_cleanup": "loader-owned-fd", "path_absent": True,
                "observed_while_alive": True, "wall_from_launch": time.monotonic() - started}
    return scope.normal_cleanup(owned, snapshot, contract, started)


def _profile_session(scope):
    class ProfileSession(scope.Session):
        def observe_workers(self, before, started, maximum):
            leader = self.owned.process.pid
            baseline = {tid: row["cpu_ticks"] for tid, row in before.items()}
            positive, observed, samples, peak = set(), set(before), [], len(before)
            deadline = started + self.owned.budget.left(maximum)
            while True:
                after = scope.task_snapshot(leader)
                require(len(after) <= self.policy["active_threads"], "search exceeded declared OS threads")
                peak = max(peak, len(after))
                observed.update(after)
                for tid, row in after.items():
                    if tid != leader and row["cpu_ticks"] > baseline.get(tid, 0):
                        positive.add(tid)
                if len(samples) < (64 if self.workers >= 64 else 200):
                    samples.append({"at": time.monotonic() - started, "tasks": after})
                if len(positive) >= self.workers and peak == self.policy["active_threads"]:
                    break
                require(sum(line.startswith(b"bestmove ") for line in self.owned.stdout.bytes().splitlines())
                        < self.count, "search completed before every worker showed positive CPU")
                require(time.monotonic() < deadline, "not every declared worker showed positive CPU")
                time.sleep(.005)
            return {"positive_CPU_participant_TIDs": sorted(positive), "all_observed_TIDs": sorted(observed),
                    "peak_threads": peak, "all_workers_positive_CPU": True, "samples": samples,
                    "before_tasks": before, "last_tasks": after,
                    "simultaneously_running_state_required": False}
    return ProfileSession


def run_runtime(admitted, build, out, limits, *, target_reference=None):
    global _CONSTRUCTING, _DEFERRED
    scope, owner, oracle = support_modules()
    own_path = "engines/experiments/tcec-next/profile_verify.py"
    own_source = executing_source(source_bytes(own_path))
    revalidate_target(target_reference)
    image_pin, image = runtime_image(admitted, build, target_reference)
    reference_record = target_reference.to_record() if target_reference is not None else None
    Session = _profile_session(scope)
    fixtures = scope.promotion_fixtures(oracle)
    manifest = {"resources": admitted.resources, "runtime_policy": admitted.runtime_policy}
    report = {"format": "rove4k-profile-runtime-v1", "family": admitted.family,
              "profile": admitted.profile_id, "representation": admitted.representation,
              "complete": False, "resources": admitted.resources, "limits": limits,
              "expected_contract": admitted.expected, "source_contract": admitted.source_contract,
              "runtime_native_contract": image_pin,
              "target_runtime_reference": reference_record,
              "event_target_confirmed": False,
              "own_source_matches_executed_module": True,
              "build_sha256": pin(artifact_file(build, "build.json").read_bytes())["sha256"],
              "source_closure": admitted.input_pins,
              "execution_host": execution_host(admitted),
              "dependencies": native_dependencies(image),
              "ISA": owner.execution_profile(),
              "sessions": [], "counts": {"GO": 0, "legal_bestmoves": 0},
              "not_proven": ["event-specific compiler/allocation acceptance", "playing strength or scaling",
                             "actual multi-node NUMA behavior", "exact retained learner values from minimum UCI",
                             "exhaustive NBRQ generation from replay alone"]}
    out.mkdir()
    support_inputs = dict(SUPPORT)
    support_inputs[own_path] = pin(own_source)["sha256"]
    support_inputs[INPUT_READER] = pin(input_reader().source_identity())["sha256"]
    report["runtime_support"] = support_inputs
    reference_support = {}
    if reference_record is not None:
        reference_support = reference_support_pins(target_reference)
        report["target_reference_support"] = reference_support
    for relative, digest in {**support_inputs, **reference_support}.items():
        data = source_bytes(relative)
        require(pin(data)["sha256"] == digest, "runtime support changed before execution")
        target = out / "inputs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    def save():
        (out / "runtime.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    resource.setrlimit(resource.RLIMIT_AS, (limits["address_space_bytes"],) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, tuple(limits["CPU_seconds"]))
    handlers = {sig: signal.signal(sig, _signal) for sig in
                (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)}
    signal.alarm(limits["wall_seconds"])
    try:
        for eof, active in ((False, False), (True, False), (False, True), (True, True)):
            label = ("active-" if active else "idle-") + ("EOF" if eof else "quit")
            directory = out / label
            directory.mkdir()
            row = {"termination": label, "complete": False, "GO": []}
            report["sessions"].append(row)
            started = time.monotonic()
            owned = None
            try:
                _CONSTRUCTING = True
                try:
                    owned = owner.Owned(artifact_file(build, admitted.program), directory, owner.Budget(140))
                finally:
                    _CONSTRUCTING = False
                if _DEFERRED is not None:
                    pending, _DEFERRED = _DEFERRED, None
                    _signal(pending, None)
                row["pid"] = owned.process.pid
                original_stdin = os.fstat(owned.process.stdin.fileno())
                owned.send(b"uci\nisready\n")
                owned.stdout.until(lambda data: b"uciok" in data.splitlines() and b"readyok" in data.splitlines(),
                                   owned.budget, seconds=60)
                row["startup_wall_seconds"] = time.monotonic() - started
                require(row["startup_wall_seconds"] <= 60, "combined startup exceeded 60 seconds")
                snapshot = scope.image_snapshot(owned.process.pid, image_pin["sha256"])
                require(len(snapshot["tasks"]) == admitted.runtime_policy["startup_threads"],
                        "startup search-worker lifetime differs")
                actual_stdin = os.stat(Path("/proc") / str(owned.process.pid) / "fd/0")
                require((original_stdin.st_dev, original_stdin.st_ino) == (actual_stdin.st_dev, actual_stdin.st_ino),
                        "restoration replaced or consumed the original UCI input pipe")
                row["startup"] = snapshot
                row["original_UCI_stdin_pipe_preserved"] = True
                row["startup_VmRSS_bytes_not_peak"] = _rss_bytes(snapshot)
                row["startup_resident_accounting"] = resident_accounting(owned.process.pid)
                row["startup_RSS_source"] = RSS_ACCOUNTING
                row["startup_RSS_bytes_not_peak"] = row["startup_resident_accounting"]["Rss_bytes"]
                startup_residency(row, snapshot, admitted.resources["tt_bytes"], exact_required=True)
                row["normal_temporary_cleanup"] = _clean_live(scope, owned, snapshot,
                                                               admitted.wrapper_contract, started)
                session = Session(owned, oracle, manifest, row, report)
                require(not any(line.startswith(b"option name ") for line in owned.stdout.bytes().splitlines()),
                        "fixed submission profile exposed a configurable UCI option")
                owned.send(b"setoption name Threads value 1\nsetoption name Hash value 1\n"
                           b"ponderhit\ndebug on\ndebug off\nregister later\nucinewgame\nstop\n")
                session.ready()
                require(not session.moves(), "an idle optional command started an unsolicited search")
                row["optional_UCI_commands"] = {"idle_commands_tolerated": True,
                    "fixed_resource_mutation_ignored": True, "unsolicited_bestmove": False,
                    "declared_workers_checked_during_following_GO": admitted.resources["workers"]}
                if active:
                    board = session.position()
                    session.count = 1
                    report["counts"]["GO"] += 1
                    before = scope.task_snapshot(owned.process.pid)
                    searched = time.monotonic()
                    owned.send(b"go wtime 60000 btime 0 winc 4000 binc 0\n")
                    activity = session.observe_workers(before, searched, 8)
                    require(not session.moves(), "terminal request followed a completed search")
                    if eof:
                        owned.close_input()
                    else:
                        owned.send(b"quit\n")
                    row["settled"] = scope.finish_owned(owned)
                    closing = session.moves()
                    require(len(closing) <= 1 and all(move in {str(m) for m in board.legal_moves()}
                                                    for move in closing), "invalid active-terminal result")
                    report["counts"]["legal_bestmoves"] += len(closing)
                    row["GO"].append({"label": "active-terminal", "activity": activity,
                                      "bestmoves": closing, "bestmove_required": False})
                else:
                    board = session.position()
                    session.go(board, b"go wtime 0 btime 3600000 winc 0 binc 8000\n", "white-own-zero", maximum=3)
                    board = session.position(["e2e4"])
                    session.go(board, b"go wtime 3600000 btime 0 winc 8000 binc 0\n", "black-own-zero", maximum=3)
                    board = session.position()
                    session.go(board, b"go\n", "bare-finite-go", maximum=5, minimum=.5)
                    session.queued_positions()
                    owned.send(b"stop\nucinewgame\n")
                    session.ready()
                    board = session.position()
                    session.go(board, b"go wtime 60000 btime 0 winc 4000 binc 0\n", "white-workers",
                               maximum=10, minimum=.8, observe=True)
                    board = session.position(["e2e4"])
                    session.go(board, b"go wtime 0 btime 60000 winc 0 binc 4000\n", "black-workers",
                               maximum=10, minimum=.8, observe=True)
                    if not eof:
                        for promotion, moves, board in fixtures:
                            session.position(moves)
                            session.go(board, b"go wtime 0 btime 0\n", "promotion-replay-" + promotion, maximum=3)
                        moves = "g1f3 g8f6 f3g1 f6g8".split() * 256
                        board = session.position(moves)
                        require(board.halfmove == 1024, "long replay did not reach its halfmove contract")
                        session.go(board, b"go wtime 0 btime 0\n", "long-repetition-fifty-replay", maximum=3)
                        row["long_position"] = {"plies": len(moves), "oracle_halfmove": board.halfmove,
                                                "draw_score_exposed": False}
                    results = session.moves()
                    if eof:
                        owned.close_input()
                    else:
                        owned.send(b"quit\n")
                    row["settled"] = scope.finish_owned(owned)
                    require(session.moves() == results, "terminal EOF changed the result count")
                row["cleanup"] = owned.cleanup()
                require(row["cleanup"]["owned_group_absent"] and row["cleanup"]["readers_joined"]
                        and not row["cleanup"]["forced_cleanup"] and not row["cleanup"]["errors"],
                        "runtime group/readers required forced or failed cleanup")
                row.update(complete=True, wall_seconds=time.monotonic() - started,
                           stdout_sha256=pin(owned.stdout.bytes())["sha256"],
                           stderr_sha256=pin(owned.stderr.bytes())["sha256"])
                save()
            finally:
                if owned is not None:
                    cleanup = owned.cleanup()
                    if not row["complete"]:
                        row["failed_session_cleanup"] = cleanup
        revalidate_target(target_reference)
        if target_reference is not None:
            report["target_context_before_post_unchanged"] = True
        report["complete"] = True
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        report["final_owned_cleanup"] = [item.cleanup() for item in tuple(owner.OWNED)]
        report["owned_remaining"] = len(owner.OWNED)
        if report["final_owned_cleanup"] or report["owned_remaining"]:
            report["complete"] = False
            report["cleanup_failure"] = "an owned lifetime remained after the four naturally settled sessions"
        save()
        signal.alarm(0)
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
    return report


def rules_receipt(admitted, build, rules_path):
    """Replay the same source-bound actual rules receipt for either consumer."""
    helper = load("profile_runtime_rules_receipt", HERE / "profile_rules.py")
    manifest = json.loads(input_reader().read_regular(artifact_file(build, "build.json"), limit=8 << 20))
    if admitted.family == "D":
        main_source = checked_artifact(build, "shipping-inputs/main.c", manifest["shipping_inputs"]["main.c"])
        baseline, source_proof = None, manifest["proof"]
    else:
        main_source = checked_artifact(build, admitted.source, _field_pin(admitted.expected, "source"))
        baseline = input_reader().read_regular(artifact_file(build, "control/main.c"), limit=16 << 20)
        source_proof = manifest["source_proofs"]
    return helper.validate_rules_receipt(rules_path, family=admitted.family,
        profile=contracts().resource_profile(admitted.profile_id), main_source=main_source,
        source_proof=source_proof, baseline_source=baseline, build=build)


def qualification_record(admitted, build, runtime_path, *, rules_path=None, artifact_id=None,
                         target_reference=None):
    """Bind measured evidence for registry intake; missing placement stays failed.

    This is an adapter for an already admitted artifact and an owned runtime
    receipt. It performs no engine execution and does not grant event approval.
    The immutable runtime support and raw pipe outputs are checked again.
    """
    build, runtime_path = Path(build), Path(runtime_path)
    runtime_root = runtime_path.parent
    runtime_path = artifact_file(runtime_root, runtime_path.name)
    require(runtime_path.stat().st_size <= 64 << 20, "runtime receipt exceeds bounded input")
    raw = runtime_path.read_bytes()
    observed = json.loads(raw)
    require(observed.get("format") == "rove4k-profile-runtime-v1" and observed.get("complete") is True
            and observed.get("owned_remaining") == 0 and not observed.get("final_owned_cleanup")
            and "failure" not in observed, "owned runtime has not completed cleanly")
    require((observed.get("family"), observed.get("profile"), observed.get("representation")) ==
            (admitted.family, admitted.profile_id, admitted.representation), "runtime artifact class differs")
    require(observed.get("build_sha256") == pin(artifact_file(build, "build.json").read_bytes())["sha256"]
            and _json_equal(observed.get("expected_contract"), admitted.expected)
            and _json_equal(observed.get("source_closure"), admitted.input_pins)
            and _json_equal(observed.get("resources"), admitted.resources),
            "runtime does not bind the admitted whole/native/source/resource identity")
    revalidate_target(target_reference)
    image_pin, image = runtime_image(admitted, build, target_reference)
    reference_record = target_reference.to_record() if target_reference is not None else None
    require(observed.get("target_runtime_reference") == reference_record,
            "target runtime evidence requires the same explicit validated compiler reference")
    require(observed.get("runtime_native_contract", _field_pin(admitted.expected, "native")) == image_pin,
            "runtime native expectation differs from its admitted image authority")
    if target_reference is not None:
        require(observed.get("target_context_before_post_unchanged") is True,
                "target compiler/source context was not revalidated after execution")
    support = observed.get("runtime_support", {})
    own = "engines/experiments/tcec-next/profile_verify.py"
    require(set(support) in (set(SUPPORT) | {own}, set(SUPPORT) | {own, INPUT_READER})
            and all(support[name] == digest for name, digest in SUPPORT.items()),
            "runtime support contract differs")
    frozen_qualifier = None
    for name, digest in support.items():
        contracts()._logical_path(name)
        data = artifact_file(runtime_root, "inputs/" + name).read_bytes()
        require(pin(data)["sha256"] == digest, "frozen runtime support differs: " + name)
        if name == own:
            frozen_qualifier = data
    # Historical receipts retain their old qualifier source. A new qualifier
    # cannot omit the helper it actually executed from its support closure.
    require((INPUT_READER in support) == runtime_reader_required(frozen_qualifier),
            "runtime input reader support is missing or inconsistent with its frozen qualifier")
    exact_rss = runtime_feature_required(frozen_qualifier, "RSS_ACCOUNTING", RSS_ACCOUNTING)
    reference_support = observed.get("target_reference_support", {})
    if reference_record is not None:
        expected_support = reference_support_pins(target_reference)
        require(reference_support == expected_support, "target reference support closure differs")
        for name, digest in reference_support.items():
            require(pin(artifact_file(runtime_root, "inputs/" + name).read_bytes())["sha256"] == digest,
                    "frozen target reference support differs")
    else:
        require(not reference_support, "default runtime cannot inherit a target support map")
    scope, _, oracle = support_modules()
    promotions = {"promotion-replay-" + label: board for label, _, board in scope.promotion_fixtures(oracle)}
    base_labels = ["white-own-zero", "black-own-zero", "bare-finite-go", "white-workers", "black-workers"]
    rows = observed.get("sessions", [])
    require([row.get("termination") for row in rows] == ["idle-quit", "idle-EOF", "active-quit", "active-EOF"],
            "runtime lifecycle coverage differs")
    startup, worker_counts, actual_bestmoves, requested = [], [], 0, 0
    for row in rows:
        label = row["termination"]
        require(row.get("complete") is True and row.get("original_UCI_stdin_pipe_preserved") is True,
                "runtime session or original UCI pipe is incomplete")
        settled, cleanup = row["settled"], row["cleanup"]
        require(settled.get("returncode") == 0 and settled.get("readers_joined") is True
                and settled.get("stdout_eof") is True and settled.get("stderr_eof") is True
                and settled.get("forced_cleanup") is False and settled.get("reaped") is True
                and settled.get("pre_reap_other_members") == []
                and settled.get("original_identity_retained_until_other_members_absent") is True
                and cleanup.get("owned_group_absent") is True and cleanup.get("readers_joined") is True
                and cleanup.get("forced_cleanup") is False and cleanup.get("errors") == [],
                "runtime original group/readers did not settle naturally")
        pipes = {}
        for pipe in ("stdout", "stderr"):
            path = artifact_file(runtime_root, label + "/" + pipe + ".bin")
            require(path.stat().st_size <= 1 << 20, "runtime pipe exceeded bounded output")
            pipes[pipe] = path.read_bytes()
            require(pin(pipes[pipe])["sha256"] == row[pipe + "_sha256"], "runtime pipe identity differs")
        require(not pipes["stderr"], "runtime engine wrote stderr")
        snapshot = row["startup"]
        require(snapshot["native_sha256"] == image_pin["sha256"]
                and len(snapshot["tasks"]) == admitted.runtime_policy["startup_threads"],
                "runtime actual image/startup threads/resident TT differs")
        startup_residency(row, snapshot, admitted.resources["tt_bytes"], exact_required=exact_rss)
        seconds = row["startup_wall_seconds"]
        require(type(seconds) in (int, float) and 0 <= seconds <= 60, "runtime startup exceeds 60 seconds")
        startup.append(seconds * 1000)
        require(row["normal_temporary_cleanup"].get("path_absent") is True,
                "live usable startup cleanup is absent")
        active = label.startswith("active-")
        expected_labels = (["active-terminal"] if active else base_labels +
                           (list(promotions) + ["long-repetition-fifty-replay"] if label == "idle-quit" else []))
        require([go["label"] for go in row["GO"]] == expected_labels, "runtime protocol coverage differs")
        wanted = []
        for go in row["GO"]:
            requested += 1
            go_label = go["label"]
            board = promotions.get(go_label)
            if board is None:
                board = oracle.Board.from_fen()
                if go_label in ("black-own-zero", "black-workers"):
                    board = board.play("e2e4")
            if go_label == "white-workers":
                queued = row["queued_GO_positions"]["bestmoves"]
                require(len(queued) == 2 and queued[0] in {str(m) for m in oracle.Board.from_fen().legal_moves()}
                        and queued[1] in {str(m) for m in oracle.Board.from_fen().play("e2e4").legal_moves()},
                        "queued positions did not preserve their independent legal moves")
                wanted.extend(queued)
                requested += 2
            moves = go["bestmoves"] if active else [go["bestmove"]]
            require((not active or len(moves) <= 1) and
                    all(move in {str(m) for m in board.legal_moves()} for move in moves),
                    "runtime result is not legal under the independent oracle")
            wanted.extend(moves)
            if "activity" in go:
                activity = go["activity"]
                count = len(set(activity["positive_CPU_participant_TIDs"]))
                require(count == admitted.resources["workers"] and activity["all_workers_positive_CPU"] is True
                        and activity["peak_threads"] == admitted.runtime_policy["active_threads"],
                        "runtime did not observe every declared search worker doing CPU work")
                worker_counts.append(count)
                if not active:
                    require(activity["active_GO_isready"]["response_before_bestmove"] is True,
                            "active search did not consume isready")
            if not active:
                require(len(go["between_GO_tasks"]) == admitted.runtime_policy["between_GO_threads"],
                        "between-search worker lifetime differs")
        found = []
        for line in pipes["stdout"].splitlines():
            if line.startswith(b"bestmove "):
                fields = line.split()
                require(len(fields) == 2, "malformed bestmove in raw runtime pipe")
                found.append(fields[1].decode("ascii"))
        require(found == wanted, "raw runtime results differ from the checked protocol transitions")
        actual_bestmoves += len(found)
    require(len(worker_counts) == 6 and observed["counts"] ==
            {"GO": requested, "legal_bestmoves": actual_bestmoves}, "runtime observation count differs")
    require(rows[0]["long_position"]["plies"] == 1024 and
            rows[0]["long_position"]["oracle_halfmove"] == 1024, "long replay was not observed")
    actual_dependencies = native_dependencies(image)
    dependencies = _json_equal(observed.get("dependencies"), actual_dependencies)
    isa = observed.get("ISA", {})
    dependencies = dependencies and isa.get("sse4_2_all_available") is True and isa.get("cx16_all_available") is True
    rules = None
    if rules_path is not None:
        rules = rules_receipt(admitted, build, rules_path)
    host = observed.get("execution_host", {})
    physical, logical = host.get("physical_cores_exposed"), len(host.get("affinity", []))
    needed = {"test-p4": 4, "test-p28": 28}.get(admitted.profile_id)
    placement = needed is not None and physical == needed and logical == needed and \
                host.get("one_sibling_per_physical_core") is True and host.get("test_physical_envelope_observed") is True
    checks = {"reproduction": True, "size": admitted.expected["whole_bytes"] <= 4096,
              "startup": True, "dependencies": dependencies, "cleanup": True, "protocol": True,
              "legal_moves": rules is not None and rules.get("nbrq_generation") is True,
              "resources": True, "lifecycle": True, "placement": placement}
    failures = [name for name, passed in checks.items() if passed is not True]
    profile = contracts().resource_profile(admitted.profile_id)
    identity = {"id": artifact_id or ("rove-" + admitted.family.lower() + "-" + admitted.profile_id + "-" +
                 admitted.representation + "-" + admitted.expected["whole_sha256"][:12]),
                "family": admitted.family, "purpose": profile.purpose, "profile": profile.id,
                "workers": profile.workers, "tt_bytes": admitted.resources["tt_bytes"],
                "entry_bytes": admitted.resources["tt_entry_bytes"], "representation": admitted.representation,
                "full": admitted.full, **{key: admitted.expected["whole_" + key] for key in ("bytes", "sha256")},
                "native_sha256": image_pin["sha256"]}
    if target_reference is not None and artifact_id is None:
        identity["id"] += "-t11-" + image_pin["sha256"][:8]
    identity["whole_bytes"] = identity.pop("bytes")
    return {"format": "rove4k-qualification-v1", "division": "general4k", "artifact": identity,
            "artifact_path": str(artifact_file(build, admitted.program)), "complete": not failures,
            "functional_runtime_complete": True, "test_qualified": not failures and profile.purpose == "test",
            "release_qualified": False, "event_target_confirmed": False,
            "target_compiler_bound": target_reference is not None,
            "target_runtime_reference": reference_record,
            "checks": checks, "failures": failures,
            "observations": {"startup_ms": max(startup), "workers": profile.workers,
                "positive_cpu_workers": min(worker_counts), "tt_bytes": admitted.resources["tt_bytes"],
                "runtime_native_sha256": image_pin["sha256"],
                "temporary_cleanup_while_live": True, "nbrq_replay": True,
                "nbrq_generation": rules is not None and rules.get("nbrq_generation") is True,
                "physical_cores": physical, "logical_cpus": logical,
                "scored_cloud_slot_confirmed": host.get("scored_cloud_slot_confirmed", False)},
            "evidence": {"runtime": {"path": str(runtime_path), **pin(raw)},
                         "runtime_support": support, "rules": rules},
            "scope": "bound full runtime and actual generated rules; named physical TEST placement separately required"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", help="explicit D candidate filename; omit for ABCEF")
    parser.add_argument("--rules", type=Path, help="actual source-bound rules.json; no replay-to-generation inference")
    parser.add_argument("--runtime", type=Path,
                        help="revalidate an existing owned runtime.json without launching an engine")
    parser.add_argument("--target-compiler-receipt", type=Path,
                        help="optional actual system-Ubuntu22/GCC11 compiler.json; SDK evidence is ineligible")
    parser.add_argument("--source-bundle", type=Path, help="exact same-CI source-bundle.zip for target mode")
    parser.add_argument("--source-seal", type=Path, help="matching source-seal.json for target mode")
    parser.add_argument("--target-reference", type=Path,
                        help="optional saved target-runtime.json, revalidated from the complete authority chain")
    args = parser.parse_args()
    target_inputs = (args.target_compiler_receipt, args.source_bundle, args.source_seal)
    require(not any(target_inputs) or all(target_inputs),
            "target mode requires compiler receipt, source bundle and source seal together")
    require(args.target_reference is None or all(target_inputs),
            "a saved target reference requires all original authority inputs")
    require(sys.platform == "linux" and resource is not None, "Linux /proc runtime target required")
    build, out = args.build.resolve(), args.out.resolve()
    require(args.build.is_absolute() and args.out.is_absolute() and not out.exists()
            and ROOT not in (out, *out.parents)
            and not any((p / ".git").exists() for p in (out, *out.parents)),
            "absolute build and new output outside every checkout required")
    if args.rules is not None:
        require(args.rules.is_absolute() and args.rules.name == "rules.json",
                "an existing absolute rules.json is required before execution")
        path = artifact_file(args.rules.parent, args.rules.name)
        require(path.stat().st_size <= 16 << 20, "rules receipt exceeds bounded input")
    manifest_path = artifact_file(build, "build.json")
    require(manifest_path.stat().st_size <= 8 << 20, "profile manifest exceeds bounded input")
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get("format") == "rove4k-D-general-source-v1":
        require(args.candidate, "D runtime requires an explicit --candidate filename")
        admitted = admit_d_build(manifest, build, args.candidate)
    else:
        require(args.candidate is None, "C source-profile has one explicit selected artifact")
        admitted = admit_c_build(manifest, build)
    reference = None
    if all(target_inputs):
        helper = target_module()
        options = dict(verify=sys.modules[__name__], source_bundle=args.source_bundle,
                       source_seal=args.source_seal, expected_ci=helper.CIContext.from_environment())
        if args.target_reference is not None:
            reference = helper.load_reference(args.target_reference, admitted, build,
                                               args.target_compiler_receipt, **options)
        else:
            reference = helper.validate_target_runtime(admitted, build, args.target_compiler_receipt, **options)
    if args.runtime is not None:
        require(args.runtime.is_absolute() and args.runtime.name == "runtime.json",
                "an existing absolute runtime.json is required for read-only revalidation")
        qualification = qualification_record(admitted, build, args.runtime, rules_path=args.rules,
                                             target_reference=reference)
        out.mkdir()
        if reference is not None:
            (out / "target-runtime.json").write_text(json.dumps(reference.to_record(), indent=2) + "\n")
        (out / "qualification.json").write_text(json.dumps(qualification, indent=2) + "\n")
        print(json.dumps({"complete": qualification["complete"],
                          "functional_runtime_complete": qualification["functional_runtime_complete"],
                          "engine_executed_by_this_command": False,
                          "failures": qualification["failures"], "family": admitted.family,
                          "profile": admitted.profile_id}), flush=True)
        return
    # No output, process or TT allocation precedes this gate.
    limits = execution_limits(admitted, effective_available_bytes())
    report = run_runtime(admitted, build, out, limits, target_reference=reference)
    qualification = qualification_record(admitted, build, out / "runtime.json", rules_path=args.rules,
                                         target_reference=reference)
    if reference is not None:
        (out / "target-runtime.json").write_text(json.dumps(reference.to_record(), indent=2) + "\n")
    (out / "qualification.json").write_text(json.dumps(qualification, indent=2) + "\n")
    print(json.dumps({"complete": report["complete"], "family": admitted.family,
                      "profile": admitted.profile_id, "whole_bytes": admitted.expected["whole_bytes"],
                      **report["counts"], "event_target_confirmed": False}), flush=True)


if __name__ == "__main__":
    main()
