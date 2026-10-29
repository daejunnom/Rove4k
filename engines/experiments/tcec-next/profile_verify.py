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
import re
import signal
import stat
import struct
import sys
import time
import types

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
LEAGUE_PROFILE_OWNER = "engines/scripts/league_resource_profiles.py"
LEAGUE_PROFILE_IDS = frozenset(("test-p16", "test-p192"))
LEAGUE_PROFILE_OWNER_PIN = {"bytes": 952, "sha256": "1b6cae7f1829fb8c798d8f394f9d2c533191632444b66f9b572b8c233b30e258"}
CLOUD_PROVIDER = "engines/experiments/strength/cloud_runtime.py"
RSS_ACCOUNTING = "smaps_rollup"
ELF_ENTRY_CLEANUP = "anonymous-memfd-v1"
SPELLING = "engines/experiments/tcec-next/profile_spelling.py"
SPELLING_SCHEMA = "rove4k.selected-spelling-experiment.v1"
SPELLING_PIN = {"bytes": 9921, "sha256": "7ec393bc9c805ee8e1e6d715f40cb9883f829e3c6b01e2f71f31701e35136ea8"}
COMPOUND = "engines/experiments/tcec-next/spelling_compound.py"
COMPOUND_SCHEMA = "rove4k.selected-spelling-compound.v1"
COMPOUND_V1_HISTORICAL_PIN = {"bytes": 5522, "sha256": "4a4f6079341998fd2d0ef1ff5fc9b35a435751131b4687ce950ef1892820754b"}
# Fresh helper identity; old helper receipts keep their separately named history.
COMPOUND_PIN = {"bytes": 9472, "sha256": "4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce"}
F_COMPOUND_SCHEMA = "rove4k.selected-spelling-compound.v2"
F_COMPOUND_VARIANT = "clock-atomic-launcher-parentheses"
F_COMPOUND_DECLARATION = {"path": COMPOUND, "selection": "compound-v2", "variant": F_COMPOUND_VARIANT}
COMPOUND_DECLARATION = {"path": COMPOUND, "selection": "compound", "variant": "clock-atomic-launcher"}
SCAN = "engines/experiments/tcec-next/profile_scan.py"
SCAN_SCHEMA = "rove4k.selected-square-scan.v1"
SCAN_DECLARATION = {"path": SCAN, "variant": "square-successor"}
SCAN_PIN = {"bytes": 10623, "sha256": "98eb3139bcbd745f08fbab2d8a738b428d4e668de2604ac3fc715de8c58b879f"}
FINAL_COMPACT = {
    "A": {"path": "engines/experiments/tcec-next/profile_a_shortnames.py",
          "variant": "shortnames-v1", "schema": "rove4k.a-shortnames.v1",
          "pin": {"bytes": 6560, "sha256": "89a147f7c7ed11ea24456c3f66404a0ddc1396a8187a3722aa8f3ac95e9282df"},
          "profiles": ("test-p4", "tcec-provisional")},
    "B": {"path": "engines/experiments/tcec-next/profile_b_w256_names.py",
          "variant": "b-search-names", "schema": "rove4k.profile-b-short-names.v1",
          "pin": {"bytes": 8395, "sha256": "2c4bdfb92a5d3237372a0875826fb4edd5ac1ce7d096404bc71aa2108c2ad78d"},
          "profiles": ("test-p4", "tcec-provisional")},
    "C": {"path": "engines/experiments/tcec-next/c_macro_compact.py",
          "variant": "unused-macro-names", "schema": "rove4k.c-macro-compact-experiment.v1",
          "pin": {"bytes": 7370, "sha256": "6f9e2f7c4f44ceb8dcade552cc6669db4cd7cf9f6031ffb7c51d6405f6d9b839"},
          "profiles": ("test-p4", "tcec-provisional")},
    "E": {"path": "engines/compact/tiny-entry-e/profile_eval_unit.py",
          "variant": "e-fixed-coeff-macros", "schema": "rove4k.e-fixed-coeff-macros.v1",
          "pin": {"bytes": 8634, "sha256": "0ce8977c9ca390974e4952c85bd2630567f9ce81b1ca7068c6f6e50540814ceb"},
          "profiles": ("test-p4", "tcec-provisional")},
    "F": {"path": "engines/compact/tiny-entry-f/profile_names_null.py",
          "variant": "names-null", "schema": "rove4k-f-final-spelling-v1",
          "pin": {"bytes": 5112, "sha256": "9c61ccb50418fccbeb7562385c10920f5926f616cf35e7034dba9b834824b836"},
          "profiles": ("test-p4", "test-p28", "tcec-provisional")},
}
EP = "engines/experiments/tcec-next/profile_ep.py"
EP_SCHEMA = "rove4k.profile-ep-source.v1"
EP_DECLARATION = {"path": EP, "variant": "legal-maker"}
EP_PIN = {"bytes": 8477, "sha256": "9e089d39ded6da656a94b96a35c6b45c7a3839d6fc42672df8ff46d5f8220a34"}
SCAN_COMPILER_VERSION = "cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
# Independent finite native admission; existing compound/control policies remain unchanged.
SCAN_IMAGES = {
    ("A", "test-p4"): (7595, "02faeb563c435c02321fc6d497f54a31de01d9093be33bff5e44206a93dfbdc6", "dc2dc95fe41fc3ecb8dde3b5ace90961fb691caba45484cb8b55f31ebdce0a9e"),
    ("A", "test-p28"): (7628, "f1d5465716752b23c31d63035bbcb94b12818a984c9afbc4ce20c0c843f82006", "4303194fb29769c10fe0800377370cd6a64e94428e9b26123caee3aab2cd29c1"),
    ("A", "tcec-provisional"): (7597, "f85fa3716aed39fe9b2ca973ac3d87650dbac95dfa9cedbaf800ada4f6375a23", "e5a644a334125a96e60f495fb24d40b00c8f7cc16a3a3dc7195494fc0a5dd4b7"),
    ("C", "test-p4"): (8199, "86b7dd0e5f206d10086d098ce82083d4d12910df91a7f1215915727327f1d42a", "16031542896ac9d28cf6e7d70f32a8eef041baff2e65bcf030edea7eae689462"),
    ("C", "test-p28"): (8232, "b3a968d2287a8418ce32b7b2f9f019c4695b55a32fd4f332eab89e16d012d2d0", "798beb0201c23da1de875be256d19626ee8a922c595c98588c5618a11d4a8544"),
    ("C", "tcec-provisional"): (8201, "ae131e49609b34eefaa54499f79f2aa738d103cbc800c1d7a70cde359106b807", "3850273327e027346316df07b94c88f7e6b7df44da8dbbffbae69d777ed7c459"),
}
F_COMPOUND_POLICY = "F-compound-clock-gcc13-v1"
F_COMPOUND_COMPILER = ["cc", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s"]
F_COMPOUND_COMPILER_VERSION = "cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
F_COMPOUND_IDENTITIES = {
    "test-p4": {"source": {"bytes": 7034, "sha256": "c89769c80c70722f2a610dbe9371edce9f4063abc15ed2fff6cdc637fec4bc6e"},
                "native": {"bytes": 18568, "sha256": "5b4e662a29f7a989c8b7a81f8a41e46a96df5c3e805f4b7b29929b6a2725ae50"}},
    "test-p28": {"source": {"bytes": 7067, "sha256": "ad730fee827851f5833e753eb55b60453ed009987211a65d4a7bc4426ca8b5f8"},
                 "native": {"bytes": 18568, "sha256": "843bbc1ea78ef68c4cde578df93218f6d36b5f3c48cfa794ba6022b75e949262"}},
    "tcec-provisional": {"source": {"bytes": 7036, "sha256": "752720efdcc97c32eb79ff4796e4a0bc4cdfe4f24790863a52b585c667c1497b"},
                         "native": {"bytes": 18568, "sha256": "e536de10e8792573548864d6267e8ce3cde76102b6134552f9dbca0d2672437b"}},
}
F_COMPOUND_V2_POLICY = "F-compound-parentheses-gcc13-v2"
F_COMPOUND_V2_IDENTITIES = {
    "test-p4": {"source": {"bytes": 7030, "sha256": "0aa062ec8440911d094a1b4eea48eceb96facfaa4ce94d654f46bfa19c83c7f0"},
                "native": {"bytes": 18568, "sha256": "5b4e662a29f7a989c8b7a81f8a41e46a96df5c3e805f4b7b29929b6a2725ae50"}},
    "test-p28": {"source": {"bytes": 7063, "sha256": "5a016f252e8efb4faf356de92397964d19e6c5e95863e063a5179864988dcdc5"},
                 "native": {"bytes": 18568, "sha256": "843bbc1ea78ef68c4cde578df93218f6d36b5f3c48cfa794ba6022b75e949262"}},
    "tcec-provisional": {"source": {"bytes": 7032, "sha256": "7701b38ad0957066d427bb085575f26b511691a6ea60e67f44835ce9359db9df"},
                         "native": {"bytes": 18568, "sha256": "e536de10e8792573548864d6267e8ce3cde76102b6134552f9dbca0d2672437b"}},
}
BEST_SPELLING = {"A": "clock-type", "B": "atomic-assignment", "C": "clock-type",
                 "E": "clock-type", "F": "atomic-assignment"}
B_LEAGUE_SPELLING = "engines/experiments/tcec-next/profile_b_league_spelling.py"
B_LEAGUE_SPELLING_SCHEMA = "rove4k.league-b-atomic.v1"
B_LEAGUE_SPELLING_PIN = {"bytes": 3925, "sha256": "e7e81ba58dbf6210fbf132a5baba3811c987fcb86728949bca0e6e2140bff1e5"}
B_LEAGUE_SPELLING_DECLARATION = {"path": B_LEAGUE_SPELLING, "selection": "league-atomic",
                                 "variant": "atomic-assignment"}
# These are opt-in measured inputs; they do not grant runtime or league admission.
LEAGUE_VARIANTS = {
    "atomic-assignment": ("engines/experiments/tcec-next/profile_acef_league_atomic.py",
        {"bytes": 4906, "sha256": "d551768ea423655cc5566430f5e185b8377321d03f9f3429fd8f18112eaaaddd"},
        "rove4k.league-acef-atomic.v1", "ACEF"),
    "square-successor": ("engines/experiments/tcec-next/profile_league_square.py",
        {"bytes": 3790, "sha256": "8b832928e53bde3c007ed7e1bf8a35290bd8785f4233ea7246d9cb1392eed1b8"},
        "rove4k.league-square-scan.v1", "AC"),
    "legal-maker": ("engines/experiments/tcec-next/league_ep.py",
        {"bytes": 4456, "sha256": "55d76f2740732672fd6abf9cc2650143525732eadf10a9a302cf652accfafc05"},
        "rove4k.league-ep-source.v1", "CE"),
    "square-atomic": ("engines/experiments/tcec-next/profile_league_compound.py",
        {"bytes": 9520, "sha256": "4a64512d3d6da772a072232c1e303da5aef609b0e606e9508893606f7e413704"},
        "rove4k.league-combined-source.v1", "AC"),
    "square-ep": ("engines/experiments/tcec-next/profile_league_compound.py",
        {"bytes": 9520, "sha256": "4a64512d3d6da772a072232c1e303da5aef609b0e606e9508893606f7e413704"},
        "rove4k.league-combined-source.v1", "C"),
    "ep-atomic": ("engines/experiments/tcec-next/profile_league_compound.py",
        {"bytes": 9520, "sha256": "4a64512d3d6da772a072232c1e303da5aef609b0e606e9508893606f7e413704"},
        "rove4k.league-combined-source.v1", "CE"),
    "square-ep-atomic": ("engines/experiments/tcec-next/profile_league_compound.py",
        {"bytes": 9520, "sha256": "4a64512d3d6da772a072232c1e303da5aef609b0e606e9508893606f7e413704"},
        "rove4k.league-combined-source.v1", "C"),
}
LEAGUE_COMBINATIONS = {
    "square-atomic": (("square", "square-successor"), ("atomic", "atomic-assignment")),
    "square-ep": (("square", "square-successor"), ("ep", "legal-maker")),
    "ep-atomic": (("ep", "legal-maker"), ("atomic", "atomic-assignment")),
    "square-ep-atomic": (("square", "square-successor"), ("ep", "legal-maker"), ("atomic", "atomic-assignment")),
}
LEAGUE_EP_SUPPORT = "engines/experiments/tcec-next/compact_ep.py"
LEAGUE_EP_SUPPORT_PIN = {"bytes": 7267, "sha256": "42963c889070f29da4dc05d08d5fc4749afb7aec36b0d00735ccc9d271215c6c"}
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
class AnonymousMemfdContract:
    """Producer-owned admission for an outer ELF which survives its memfd exec."""

    def to_record(self):
        return {"entry_cleanup": "none", "temp_strategy": "anonymous-memfd",
                "cleanup_seconds": 0, "parent_removed": False}


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
    wrapper_contract: dict | AnonymousMemfdContract
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


def source_stages(family, post, proofs, *, post_spelling=None, post_scan=None, post_ep=None, post_league=None, source_dependencies=None, post_compact=None,
                  representation=None, entry_cleanup=None, profile_id=None):
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
    if post_league is not None:
        require(type(post_league) is dict and set(post_league) == {"path", "variant"},
                "named league candidate declaration required")
        variant = post_league["variant"]
        require(type(variant) is str and variant in LEAGUE_VARIANTS,
                "unknown league candidate variant")
        relative, _, schema, families = LEAGUE_VARIANTS[variant]
        require(post_league == {"path": relative, "variant": variant} and family in families
                and profile_id in LEAGUE_PROFILE_IDS and representation == "source-jit"
                and entry_cleanup == "private-path" and post is None and post_spelling is None
                and post_scan is None and post_ep is None and source_dependencies is None,
                "league candidate requires its standalone named league source profile")
        expected.append(schema)
    if post_spelling is not None:
        best = {"path": SPELLING, "selection": "best", "variant": BEST_SPELLING[family]}
        compound = family in "ACEF" and post_spelling == COMPOUND_DECLARATION
        compound_v2 = family == "F" and post_spelling == F_COMPOUND_DECLARATION
        league_atomic = family == "B" and profile_id in LEAGUE_PROFILE_IDS and \
                        post_spelling == B_LEAGUE_SPELLING_DECLARATION
        require(post_spelling == best or compound or compound_v2 or league_atomic,
                "final spelling requires its exact reviewed winner and helper")
        require(representation == "source-jit" and entry_cleanup == "private-path",
                "final spelling requires full source-JIT/private-path")
        require((family == "B" and post == {"path": "engines/experiments/tcec-next/profile_b.py",
                                          "variant": "tcec-final-lf"}) or
                (family in "ACEF" and kind == "phase"),
                "final spelling requires selected phase-init ACEF or tcec-final-lf B")
        if compound_v2:
            require(post_scan is None and source_dependencies == {
                "path": "engines/experiments/tcec-next/profile_dependencies.py", "variant": "unused-includes"},
                "F compound-v2 requires no scan stage and final dependency cleanup")
        if league_atomic:
            require(post_scan is None and post_ep is None and source_dependencies == {
                "path": "engines/experiments/tcec-next/profile_dependencies.py", "variant": "unused-includes"},
                "B league atomic requires final dependency cleanup")
        expected.append(B_LEAGUE_SPELLING_SCHEMA if league_atomic else F_COMPOUND_SCHEMA if compound_v2
                        else COMPOUND_SCHEMA if compound else SPELLING_SCHEMA)
    if post_scan is not None:
        require(family in ("A", "C") and post_scan == SCAN_DECLARATION
                and post_spelling == COMPOUND_DECLARATION and kind == "phase"
                and representation == "source-jit" and entry_cleanup == "private-path"
                and source_dependencies == {"path": "engines/experiments/tcec-next/profile_dependencies.py",
                                            "variant": "unused-includes"},
                "valid-square stage requires A/C phase-init/compound and final dependency cleanup")
        expected.append(SCAN_SCHEMA)
    if post_ep is not None:
        require(family in ("C", "E") and post_ep == EP_DECLARATION
                and kind == "phase" and post_spelling == COMPOUND_DECLARATION
                and post_scan == (SCAN_DECLARATION if family == "C" else None)
                and representation == "source-jit" and entry_cleanup == "private-path"
                and source_dependencies == {"path": "engines/experiments/tcec-next/profile_dependencies.py",
                                            "variant": "unused-includes"},
                "EP requires selected C/E phase/compound, C square-successor and final dependency cleanup")
        expected.append(EP_SCHEMA)
    if source_dependencies is not None:
        require(source_dependencies == {
            "path": "engines/experiments/tcec-next/profile_dependencies.py",
            "variant": "unused-includes"}, "unrecognized dependency source stage")
        expected.append("rove4k.profile-dependencies.v1")
    if post_compact is not None:
        owner = FINAL_COMPACT.get(family)
        require(owner is not None and post_compact == {"path": owner["path"], "variant": owner["variant"]}
                and profile_id in owner["profiles"] and representation == "source-jit"
                and entry_cleanup == "private-path" and post_league is None
                and source_dependencies == {"path": "engines/experiments/tcec-next/profile_dependencies.py",
                                            "variant": "unused-includes"},
                "final compact stage requires its named full profile and dependency cleanup")
        if family == "A":
            require(post_scan == SCAN_DECLARATION and post_ep is None,
                    "A final compact requires the reviewed valid-square stage")
        if family == "B":
            require(post_spelling == {"path": SPELLING, "selection": "best", "variant": BEST_SPELLING["B"]}
                    and post_scan is None and post_ep is None,
                    "B final compact requires the reviewed B spelling stage")
        if family == "F":
            require(post_spelling == F_COMPOUND_DECLARATION and post_scan is None and post_ep is None,
                    "F final compact requires the reviewed compound-v2 stage")
        if family == "E":
            require(post_spelling == COMPOUND_DECLARATION and post_scan is None and post_ep == EP_DECLARATION,
                    "E final compact requires the reviewed legal-maker stage")
        if family == "C":
            require(post_spelling == COMPOUND_DECLARATION and post_scan == SCAN_DECLARATION
                    and post_ep == EP_DECLARATION,
                    "C final compact requires the reviewed scan and legal-maker stages")
        expected.append(owner["schema"])
    require([p.get("schema", p.get("stage")) for p in proofs] == expected,
            "source proof stages are missing, extra, or out of order")
    return kind


def validate_spelling_request(manifest):
    """A B compound request is an explicit duplicate of its existing best."""
    if "spelling_request" in manifest:
        request = manifest["spelling_request"]
        require(isinstance(request, dict) and request == {
            "requested": "compound", "effective": "best", "duplicate_best": True, "new_candidate_count": 0}
            and type(request.get("duplicate_best")) is bool and type(request.get("new_candidate_count")) is int
            and manifest.get("family") == "B" and manifest.get("post_spelling") == {
                "path": SPELLING, "selection": "best", "variant": "atomic-assignment"}
            and COMPOUND not in manifest.get("inputs", {})
            and all(row.get("path") != COMPOUND for row in manifest.get("source_closure", {}).get("inputs", []))
            and all(row.get("schema") not in (COMPOUND_SCHEMA, F_COMPOUND_SCHEMA) for row in manifest.get("source_proofs", [])),
            "only B's explicit compound request may normalize to its existing best")


def _reviewed_spelling_module(manifest, build, production_paths, path, identity, schema, name):
    rows = [row for row in manifest["source_closure"]["inputs"] if row.get("path") == path]
    require(path in production_paths and len(rows) == 1 and rows[0].get("role") == "tool"
            and {key: rows[0].get(key) for key in identity} == identity
            and manifest["inputs"].get(path) == identity,
            "final spelling helper production role or frozen identity differs")
    data = checked_artifact(build, "inputs/" + path, identity)
    require(source_bytes(path, identity) == data, "current reviewed spelling helper differs")
    module_path = ROOT / path
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(module_path), "exec", dont_inherit=True), module.__dict__)
    require(getattr(module, "SCHEMA", None) == schema, "reviewed source helper schema differs")
    return module


def spelling_module(manifest, build, production_paths):
    """Consume the exact reviewed helper bytes, including its production role."""
    return _reviewed_spelling_module(manifest, build, production_paths, SPELLING, SPELLING_PIN,
                                    SPELLING_SCHEMA, "profile_runtime_reviewed_spelling")


def b_league_spelling_module(manifest, build, production_paths):
    return _reviewed_spelling_module(manifest, build, production_paths, B_LEAGUE_SPELLING,
                                    B_LEAGUE_SPELLING_PIN, B_LEAGUE_SPELLING_SCHEMA,
                                    "profile_runtime_reviewed_b_league_spelling")


def league_candidate_module(manifest, build, production_paths, declaration):
    """Load exact frozen candidate and support bytes under their production roles."""
    path, expected, schema, _ = LEAGUE_VARIANTS[declaration["variant"]]
    rows = [row for row in manifest["source_closure"]["inputs"] if row.get("path") == path]
    require(path in production_paths and len(rows) == 1 and rows[0].get("role") == "tool"
            and {k: rows[0].get(k) for k in expected} == expected and manifest["inputs"].get(path) == expected,
            "league candidate tool role or identity differs")
    data = checked_artifact(build, "inputs/" + path, expected)
    require(source_bytes(path, expected) == data, "current and frozen league candidate differ")
    # The square owner imports its sibling scan module by __file__, so bind its
    # location to the frozen tree after checking both frozen and live bytes.
    frozen = Path(build) / "inputs" / path
    spec = importlib.util.spec_from_file_location("profile_runtime_league_candidate", frozen)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(data, str(frozen), "exec", dont_inherit=True), module.__dict__)
    variant = declaration["variant"]
    require(module.SCHEMA == schema, "league candidate schema differs")
    if variant in LEAGUE_COMBINATIONS:
        require(module.VARIANTS == {key: tuple(name for name, _ in pairs)
                                    for key, pairs in LEAGUE_COMBINATIONS.items()}
                and module.FAMILIES == {key: LEAGUE_VARIANTS[key][3] for key in LEAGUE_COMBINATIONS},
                "league combined variants or family domains differ")
    else:
        require(module.VARIANT == variant, "league candidate variant differs")
    supports = {}
    if declaration["variant"] == "square-successor":
        _reviewed_spelling_module(manifest, build, production_paths, SCAN, SCAN_PIN,
                                  SCAN_SCHEMA, "profile_runtime_league_scan_support")
    elif declaration["variant"] == "legal-maker":
        supports["ep"] = _reviewed_spelling_module(manifest, build, production_paths,
            LEAGUE_EP_SUPPORT, LEAGUE_EP_SUPPORT_PIN, "rove4k.compact-ep-source.v1",
            "profile_runtime_league_ep_support")
        supports["projection"] = _reviewed_spelling_module(manifest, build, production_paths,
            COMPOUND, COMPOUND_PIN, COMPOUND_SCHEMA, "profile_runtime_league_ep_projection")
        require(module.SUPPORT == {
            name: {"path": relative, **identity} for name, relative, identity in (
                ("ep", LEAGUE_EP_SUPPORT, LEAGUE_EP_SUPPORT_PIN),
                ("projection", COMPOUND, COMPOUND_PIN))}, "league EP support declaration differs")
    elif variant in LEAGUE_COMBINATIONS:
        # Each component is independently authenticated and loaded from the
        # frozen tree. In particular, square then reads its frozen scan helper.
        helpers = {}
        for role, component_variant in LEAGUE_COMBINATIONS[variant]:
            component_path = LEAGUE_VARIANTS[component_variant][0]
            component, binding = league_candidate_module(manifest, build, production_paths,
                {"path": component_path, "variant": component_variant})
            helpers[role] = component
            if role == "ep":
                require(set(binding) == {"ep", "projection"}, "league combined EP roles differ")
                helpers["ep_owner"] = binding["ep"]
                helpers["projection"] = binding["projection"]
            else:
                require(not binding, "unexpected league combined component support")
        supports["helpers"] = helpers
    return module, supports


def b_league_spelling_stage(helper, before, supplied, profile_id, variant):
    """Replay and invert the manifest proof with type-preserving JSON identity."""
    produced, regenerated = helper.transform_source(before, family="B", profile_id=profile_id, variant=variant)
    require(_json_equal(regenerated, supplied), "B league atomic spelling proof differs")
    require(helper.restore_source(produced, supplied) == before, "B league atomic inverse differs")
    return produced, supplied


def compound_module(manifest, build, production_paths):
    individual = spelling_module(manifest, build, production_paths)
    compound = _reviewed_spelling_module(manifest, build, production_paths, COMPOUND, COMPOUND_PIN,
                                         COMPOUND_SCHEMA, "profile_runtime_reviewed_compound")
    require(compound.HELPER == SPELLING and compound.HELPER_PIN == SPELLING_PIN,
            "compound requires its authenticated individual helper binding")
    if manifest.get("post_spelling") == F_COMPOUND_DECLARATION:
        require(compound.F_SCHEMA == F_COMPOUND_SCHEMA and compound.F_VARIANT == F_COMPOUND_VARIANT,
                "F compound-v2 helper schema or variant differs")
    return compound, individual


def scan_module(manifest, build, production_paths):
    return _reviewed_spelling_module(manifest, build, production_paths, SCAN, SCAN_PIN,
                                    SCAN_SCHEMA, "profile_runtime_reviewed_scan")


def final_compact_module(manifest, build, production_paths):
    """Load only the family-selected reviewed final source helper."""
    owner = FINAL_COMPACT.get(manifest.get("family"))
    require(owner is not None and manifest.get("post_compact") == {
        "path": owner["path"], "variant": owner["variant"]},
        "unrecognized final compact helper")
    helper = _reviewed_spelling_module(manifest, build, production_paths, owner["path"],
                                       owner["pin"], owner["schema"],
                                       "profile_runtime_reviewed_final_compact")
    require(getattr(helper, "DECLARATION", None) == manifest["post_compact"],
            "final compact helper declaration differs")
    return helper


def ep_modules(manifest, build, production_paths):
    owner = _reviewed_spelling_module(manifest, build, production_paths, EP, EP_PIN,
                                      EP_SCHEMA, "profile_runtime_reviewed_ep")
    helpers = {}
    for name, row in owner.SUPPORT.items():
        helpers[name] = _reviewed_spelling_module(manifest, build, production_paths,
            row["path"], {key: row[key] for key in ("bytes", "sha256")}, row["schema"],
            "profile_runtime_reviewed_ep_" + name)
    return owner, helpers


def scan_native_evidence(manifest, build, source, native, profile_id):
    declaration = manifest.get("post_scan")
    if manifest.get("post_ep") is not None:
        require(manifest["post_ep"] == EP_DECLARATION and "scan_native_policy" not in manifest,
                "EP has its own final native policy; original scan controls cannot be relabeled")
        return None
    if declaration is None:
        require("scan_native_policy" not in manifest, "valid-square native policy is outside its finite route")
        return None
    family = manifest["family"]
    require(declaration == SCAN_DECLARATION and (family, profile_id) in SCAN_IMAGES,
            "valid-square native policy requires a named A/C profile")
    size, source_sha, native_sha = SCAN_IMAGES[family, profile_id]
    compiler = ["cc", "-Os", *(["-mavx2"] if family == "C" else []), "-x", "c", "-", "-o", "x", "-s"]
    policy = dict(kind="AC-square-successor-gcc13-v1", family=family, profile_id=profile_id,
        post_scan=dict(SCAN_DECLARATION), compiler=compiler, compiler_version=SCAN_COMPILER_VERSION,
        source=dict(bytes=size, sha256=source_sha), native=dict(bytes=18568, sha256=native_sha))
    require(_json_equal(manifest.get("scan_native_policy"), policy)
            and manifest.get("compiler") == manifest.get("compile_executor") == compiler
            and manifest.get("compile_executor_version") == SCAN_COMPILER_VERSION
            and pin(source) == policy["source"] and pin(native) == policy["native"],
            "valid-square source/native/compiler differs from the named six-context policy")
    version, output = _compound_owned_command(manifest, build, "target-compiler-version", ["cc", "--version"], None, ())
    require(output["stdout"].decode().splitlines()[:1] == [SCAN_COMPILER_VERSION],
            "valid-square actual compiler banner differs")
    return dict(policy=policy, compiler_version_command=version)


def ep_native_evidence(manifest, build, source, native, profile_id, owner):
    if manifest.get("post_ep") is None:
        require("ep_native_policy" not in manifest, "EP native policy is outside its finite route")
        return None
    require(owner is not None and owner.SCHEMA == EP_SCHEMA
            and manifest["post_ep"] == EP_DECLARATION,
            "reviewed EP source owner and explicit declaration required")
    policy = owner.native_policy(manifest["family"], profile_id, source, manifest["compiler"],
        manifest.get("compile_executor", manifest["compiler"]), manifest.get("compile_executor_version"))
    require(_json_equal(manifest.get("ep_native_policy"), policy) and pin(native) == policy["native"],
            "EP source/native/compiler differs from its named measured profile policy")
    version, output = _compound_owned_command(manifest, build, "target-compiler-version", ["cc", "--version"], None, ())
    require(output["stdout"].decode().splitlines()[:1] == [owner.COMPILER_VERSION],
            "EP actual compiler banner differs")
    return dict(policy=policy, compiler_version_command=version)


def _compound_owned_command(manifest, build, kind, command, data, suffix):
    matches = [(index, row) for index, row in enumerate(manifest["commands"], 1) if row.get("kind") == kind]
    require(len(matches) == 1, "compound compiler command is missing or duplicated")
    index, row = matches[0]
    require(row.get("command") == command and type(row.get("returncode")) is int and row["returncode"] == 0
            and all(row.get(key) is True for key in ("started", "terminal", "reaped", "owned_group_absent",
                "original_identity_retained_until_other_members_absent"))
            and row.get("forced_cleanup") is False and row.get("other_group_members_before_reap") == []
            and type(row.get("pid")) is int and row["pid"] > 0 and row.get("pgid") == row["pid"],
            "compound compiler command did not settle naturally with its original identity")
    cwd = PurePosixPath(row.get("cwd", ""))
    require(cwd.is_absolute() and ".." not in cwd.parts and str(cwd) == row.get("cwd")
            and (not suffix or tuple(cwd.parts[-len(suffix):]) == tuple(suffix)), "compound compiler cwd differs")
    original_root = cwd
    for _ in suffix:
        original_root = original_root.parent
    pipes, outputs = {}, {}
    for stream in ("stdout", "stderr"):
        name = "tool-" + str(index) + "-" + kind + "." + stream
        expected = row.get(stream, {})
        require(expected.get("path") == str(original_root / name), "compound compiler pipe path differs")
        identity = {key: expected.get(key) for key in ("bytes", "sha256")}
        outputs[stream] = checked_artifact(build, name, identity)
        pipes[stream] = {"name": name, **identity}
    stdin = None
    if data is not None:
        name = "tool-" + str(index) + "-" + kind + ".stdin"
        require(checked_artifact(build, name, pin(data)) == data, "compound compiler stdin differs")
        stdin = {"name": name, **pin(data)}
    return {"row": row, "stdin": stdin, "pipes": pipes}, outputs


def final_compact_evidence(manifest, build, before, final, native):
    """Bind both original-source compiler gates to the actual final image."""
    compiler = manifest.get("compile_executor", manifest["compiler"])
    require(type(before) is bytes and type(final) is bytes and type(native) is bytes and type(compiler) is list,
            "actual pre-compact source, final source, native bytes and compiler required")
    observed = []
    for attempt in manifest["attempts"]:
        directory = attempt["directory"]
        gate = {"directory": "final-compact-control", "source": pin(before),
                "native": pin(native), "image_identical": True}
        require(_json_equal(attempt.get("final_compact_gate"), gate),
                "final compact control gate differs")
        require(checked_artifact(build, directory + "/final-compact-control/x", pin(native)) == native,
                "final compact control native differs from the final image")
        command, _ = _compound_owned_command(manifest, build, directory + "-final-compact-control",
            list(compiler), before, (directory, "final-compact-control"))
        require(checked_artifact(build, directory + "/native/x", pin(native)) == native,
                "final compact shipping native differs")
        shipping, _ = _compound_owned_command(manifest, build, directory + "-compile",
            list(compiler), final, (directory, "native"))
        observed.append({"directory": directory, "gate": gate, "command": command,
                         "shipping_command": shipping})
    require([row["directory"] for row in observed] == ["first", "repeat"],
            "two final compact control attempts required")
    return {"scope": "owned pre-compact compiler inputs and final native byte equality",
            "attempts": observed}


def compound_native_evidence(manifest, build, source, native, resource_proof, profile_id, ep_owner=None,
                             *, policy_source=None):
    """Bind new compound codegen to actual appended assertions and owned stdin."""
    declaration = manifest.get("post_spelling")
    selected = declaration in (COMPOUND_DECLARATION, F_COMPOUND_DECLARATION)
    reviewed_source = source if policy_source is None else policy_source
    scan_evidence = scan_native_evidence(manifest, build, reviewed_source, native, profile_id)
    ep_evidence = ep_native_evidence(manifest, build, reviewed_source, native, profile_id, ep_owner)
    if not selected:
        require("native_policy" not in manifest, "named compound native policy is outside its finite route")
        return None
    family = manifest["family"]
    require(family in "ACEF" and (declaration != F_COMPOUND_DECLARATION or family == "F"),
            "compound native evidence requires A/C/E/F; compound-v2 requires F")
    compiler = manifest.get("compile_executor", manifest["compiler"])
    policy = None
    if family == "F":
        identities_by_profile, kind = ((F_COMPOUND_V2_IDENTITIES, F_COMPOUND_V2_POLICY)
            if declaration == F_COMPOUND_DECLARATION else (F_COMPOUND_IDENTITIES, F_COMPOUND_POLICY))
        require(profile_id in identities_by_profile, "unknown F compound profile")
        identities = identities_by_profile[profile_id]
        policy = {"kind": kind, "family": "F", "profile_id": profile_id,
                  "post_spelling": dict(declaration), "compiler": list(F_COMPOUND_COMPILER),
                  "compiler_version": F_COMPOUND_COMPILER_VERSION, **identities}
        require(_json_equal(manifest.get("native_policy"), policy) and manifest["compiler"] == compiler == F_COMPOUND_COMPILER
                and manifest.get("compile_executor_version") == F_COMPOUND_COMPILER_VERSION
                and pin(reviewed_source) == identities["source"] and pin(native) == identities["native"],
                "F compound requires its named GCC13 source/native policy without compiler substitution")
        version, output = _compound_owned_command(manifest, build, "target-compiler-version", ["cc", "--version"], None, ())
        require(output["stdout"].decode().splitlines()[:1] == [F_COMPOUND_COMPILER_VERSION],
                "F compound actual compiler banner differs")
    else:
        require("native_policy" not in manifest, "only F compound may declare the named native policy")
        version = None
    assertions = resource_proof["target_type_assertions"]
    require(isinstance(assertions, list) and assertions and all(isinstance(value, str) for value in assertions),
            "compound target assertions must come from the admitted resource projection")
    asserted = source + b"\n" + ("\n".join(assertions) + "\n").encode()
    attempts = manifest["attempts"]
    require([attempt.get("directory") for attempt in attempts] == ["first", "repeat"],
            "two compound target assertion attempts required")
    observed = []
    for attempt in attempts:
        directory = attempt["directory"]
        gate = {"assertions": assertions, "source": pin(asserted), "native": pin(native), "image_identical": True}
        if family == "F":
            gate.update(directory="target-type-gate", source_file="asserted.c", policy=policy["kind"])
        require(_json_equal(attempt.get("target_type_gate"), gate) and attempt["target_type_gate"].get("image_identical") is True,
                "compound target-type assertion record differs")
        prefix = directory + "/target-type-gate/"
        require(checked_artifact(build, prefix + "asserted.c", pin(asserted)) == asserted
                and checked_artifact(build, prefix + "x", pin(native)) == native
                and checked_artifact(build, directory + "/native/x", pin(native)) == native,
                "compound appended assertions changed the actual shipping native")
        asserted_command, _ = _compound_owned_command(manifest, build, directory + "-target-types", list(compiler),
                                                     asserted, (directory, "target-type-gate"))
        shipping_command, _ = _compound_owned_command(manifest, build, directory + "-compile", list(compiler),
                                                     source, (directory, "native"))
        observed.append({"directory": directory, "target_type_gate": gate,
                         "asserted_command": asserted_command, "shipping_command": shipping_command})
    return {"declaration": dict(declaration), "source": pin(source), "native": pin(native),
            "native_policy": policy, "compiler_version_command": version, "attempts": observed,
            **({"scan_native_evidence": scan_evidence} if scan_evidence is not None else {}),
            **({"ep_native_evidence": ep_evidence} if ep_evidence is not None else {})}


def inverse_source_stages(source, inverses):
    """Undo the actual shipping body, including E19 offsets, in reverse order."""
    restored = source
    for stage in reversed(inverses):
        require(len(stage) in (3, 4), "explicit source inverse stage required")
        module, proof, parent = stage[:3]
        binding = stage[3] if len(stage) == 4 else {}
        if len(stage) == 4:
            compound_binding = (isinstance(binding, dict) and set(binding) == {"spelling"}
                    and module is not None and module.SCHEMA == COMPOUND_SCHEMA
                    and (proof.get("schema") == COMPOUND_SCHEMA or
                         proof.get("schema") == F_COMPOUND_SCHEMA and
                         getattr(module, "F_SCHEMA", None) == F_COMPOUND_SCHEMA)
                    and binding["spelling"].SCHEMA == SPELLING_SCHEMA)
            ep_binding = (isinstance(binding, dict) and set(binding) == {"ep", "projection", "dependencies", "edits"}
                          and module is not None and module.SCHEMA == EP_SCHEMA and proof.get("schema") == EP_SCHEMA)
            league_ep_binding = (isinstance(binding, dict) and set(binding) == {"ep", "projection"}
                                 and module is not None and module.SCHEMA == "rove4k.league-ep-source.v1"
                                 and proof.get("schema") == module.SCHEMA
                                 and binding["ep"].SCHEMA == "rove4k.compact-ep-source.v1"
                                 and binding["projection"].SCHEMA == COMPOUND_SCHEMA)
            league_combined_binding = (isinstance(binding, dict) and set(binding) == {"helpers"}
                                       and module is not None and module.SCHEMA == "rove4k.league-combined-source.v1"
                                       and proof.get("schema") == module.SCHEMA
                                       and type(proof.get("variant")) is str
                                       and proof.get("variant") in LEAGUE_COMBINATIONS
                                       and type(binding["helpers"]) is dict)
            require(compound_binding or ep_binding or league_ep_binding or league_combined_binding,
                    "source inverse requires its explicit authenticated helper binding")
        if module is None:
            offset, before, after = proof["table_value_offset"], proof["before"].encode(), proof["after"].encode()
            require(restored[offset:offset + len(after)] == after, "E19 inverse span differs")
            restored = restored[:offset] + before + restored[offset + len(after):]
        else:
            restored = module.restore_source(restored, proof, **binding)
        require(restored == parent, "complete reverse-order source stage inverse differs")
    return restored


def dependency_evidence(manifest, build, declaration, proof, before, after, *, shipping_source=None):
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
        data = ((after if shipping_source is None else shipping_source) if row["kind"].endswith("-compile")
                else after if row["kind"].endswith("-after") else before)
        name = Path(row["stdout"]["path"]).with_suffix(".stdin").name
        checked_artifact(build, name, pin(data))
        commands.append({**row, "stdin": {"name": name, **pin(data)}})
    require(len(commands) == len(selected) and {row["kind"] for row in commands} == selected,
            "dependency compiler stdin evidence is incomplete")
    return {"declaration": declaration, "proof": proof, "attempts": attempts, "compiler_commands": commands}


def profile_resource(profile_id, *, input_pins=None, build=None, source_closure=None):
    """Resolve the two league profiles only from their frozen production owner."""
    api = contracts()
    if profile_id not in LEAGUE_PROFILE_IDS:
        return api.resource_profile(profile_id)
    require(isinstance(input_pins, dict) and LEAGUE_PROFILE_OWNER in input_pins,
            "league resource owner is missing from the admitted input closure")
    expected = input_pins[LEAGUE_PROFILE_OWNER]
    require(expected == LEAGUE_PROFILE_OWNER_PIN, "league resource owner pin differs from reviewed source")
    data = source_bytes(LEAGUE_PROFILE_OWNER, expected)
    if build is not None:
        require(checked_artifact(build, "inputs/" + LEAGUE_PROFILE_OWNER, expected) == data,
                "frozen league resource owner differs from current reviewed source")
        require(isinstance(source_closure, dict), "league resource source closure is missing")
        rows = [row for row in source_closure.get("inputs", ())
                if row.get("path") == LEAGUE_PROFILE_OWNER]
        require(len(rows) == 1 and rows[0].get("role") == "tool"
                and {key: rows[0].get(key) for key in ("bytes", "sha256")} == expected,
                "league resource owner is not a pinned production tool")
    module = types.ModuleType("profile_runtime_league_resources")
    module.__file__ = str(ROOT / LEAGUE_PROFILE_OWNER)
    exec(compile(data, module.__file__, "exec", dont_inherit=True), module.__dict__)
    require(source_bytes(LEAGUE_PROFILE_OWNER, expected) == data,
            "league resource owner changed while loading")
    return module.resource_profile(api, profile_id)


def _resource_record(record, family, *, input_pins=None, build=None, source_closure=None):
    api = contracts()
    spec = api.engine_spec(family)
    profile = profile_resource(record["id"], input_pins=input_pins, build=build,
                               source_closure=source_closure)
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


def require_profile_proof_closure(manifest, production_paths):
    """Validate the mandatory legacy source-proof inventory before reading it.

    This is the original producer contract, including its shared verifier
    helper paths. A future transport policy needs its own explicit admission;
    removing a pin and its file is not a valid projection of this contract.
    """
    inputs = manifest.get("inputs")
    require(isinstance(inputs, dict) and inputs, "profile input closure is empty")
    require(isinstance(production_paths, set) and production_paths <= set(inputs),
            "production closure omitted from profile inputs")
    proof_only = set(SUPPORT) | {"engines/scripts/verify_shell.py", "engines/tests/verify.py",
        "engines/compact/tiny-entry-f/verify.py",
        "engines/experiments/tcec-next/profile_verify.py", "engines/experiments/tcec-next/profile_rules.py"}
    extras = set(inputs) - production_paths
    require(extras <= proof_only, "unclassified input outside the explicit production/proof closure")
    require(_json_equal(manifest.get("proof_inputs"), {name: inputs[name] for name in extras}),
            "profile proof inventory differs from frozen inputs")
    family = manifest.get("family")
    require(family in tuple("ABCEF"), "profile proof inventory requires a C family")
    # The producer always froze the shared support helpers. Its own profile
    # verifier was historically optional, so do not require it retroactively.
    required = set(SUPPORT)
    if manifest.get("plan", {}).get("representation") == "source-jit":
        required.add("engines/scripts/verify_shell.py")
    if family == "F":
        required |= {"engines/compact/tiny-entry-f/verify.py", "engines/tests/verify.py"}
    require(required <= extras, "mandatory profile proof helper is absent from frozen proof inventory")
    for name in required:
        value = inputs[name]
        require(isinstance(value, dict) and set(value) == {"bytes", "sha256"}
                and type(value["bytes"]) is int and 0 < value["bytes"] <= 16 << 20
                and isinstance(value["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", value["sha256"]),
                "mandatory profile proof helper identity is malformed: " + name)


def require_profile_control_closure(manifest, control_manifest):
    """Retain the exact input identities recorded by the maintained control."""
    inputs, control = manifest.get("inputs"), control_manifest.get("inputs")
    require(isinstance(inputs, dict) and isinstance(control, dict) and control
            and all(name in inputs and _json_equal(inputs[name], value) for name, value in control.items()),
            "maintained control input is absent or differs from profile")
    control_closure = control_manifest.get("control_source_closure")
    require(isinstance(control_closure, dict) and control_closure
            and _json_equal(manifest.get("control_source_closure"), control_closure)
            and all(name in inputs and _json_equal(inputs[name], value) for name, value in control_closure.items()),
            "maintained control source closure is absent or differs from profile")


def admit_c_build(manifest, build):
    require(manifest.get("format") == 1 and manifest.get("class") == CLASS,
            "explicit new C production-profile build required")
    require(manifest.get("complete") is True and manifest.get("reproducible") is True,
            "new profile generation/reproduction is incomplete")
    family = manifest["family"]
    require(family in "ABCEF" and manifest["entry"] == family, "invalid C profile family")
    validate_spelling_request(manifest)
    profile, spec = _resource_record(manifest["resources"], family, input_pins=manifest.get("inputs"),
                                     build=build, source_closure=manifest.get("source_closure"))
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
    require_profile_proof_closure(manifest, production_paths)
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
    require_profile_control_closure(manifest, control_manifest)
    _check_command_set(control_manifest)
    produced, proof = projection.transform_source(base, family=family, profile=profile,
                                                entry_cleanup=plan["entry_cleanup"])
    require(proof == manifest["source_proofs"][0], "resource projection proof differs")
    require(projection.restore_source(produced, proof) == base, "profile inverse differs")
    inverses = [(projection, proof, base)]
    post = manifest.get("post_profile")
    post_spelling = manifest.get("post_spelling")
    post_scan = manifest.get("post_scan")
    post_ep = manifest.get("post_ep")
    post_league = manifest.get("post_league")
    post_compact = manifest.get("post_compact")
    dependency_declaration = manifest.get("source_dependencies")
    post_kind = source_stages(family, post, manifest["source_proofs"], post_spelling=post_spelling,
        post_scan=post_scan, post_ep=post_ep, post_league=post_league, source_dependencies=dependency_declaration,
        post_compact=post_compact, representation=representation,
        entry_cleanup=plan["entry_cleanup"], profile_id=profile.id)
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
    if post_league is not None:
        helper, binding = league_candidate_module(manifest, build, production_paths, post_league)
        before_league = produced
        options = dict(family=family, profile_id=profile.id, **binding)
        if post_league["variant"] == "atomic-assignment" or post_league["variant"] in LEAGUE_COMBINATIONS:
            options["variant"] = post_league["variant"]
        produced, league_proof = helper.transform_source(produced, **options)
        supplied = manifest["source_proofs"][next_stage]
        require(_json_equal(league_proof, supplied)
                and helper.restore_source(produced, supplied, **binding) == before_league,
                "league source proof or complete inverse differs")
        inverses.append((helper, supplied, before_league, binding) if binding
                        else (helper, supplied, before_league))
        next_stage += 1
    if post_spelling is not None:
        if post_spelling in (COMPOUND_DECLARATION, F_COMPOUND_DECLARATION):
            helper, individual = compound_module(manifest, build, production_paths)
            spelling_options = {"spelling": individual}
            if post_spelling == F_COMPOUND_DECLARATION:
                spelling_options["variant"] = F_COMPOUND_VARIANT
        elif post_spelling == B_LEAGUE_SPELLING_DECLARATION:
            helper = b_league_spelling_module(manifest, build, production_paths)
            spelling_options = {"variant": post_spelling["variant"]}
        else:
            helper = spelling_module(manifest, build, production_paths)
            spelling_options = {"variant": post_spelling["variant"]}
        before_spelling = produced
        if post_spelling == B_LEAGUE_SPELLING_DECLARATION:
            produced, spelling_proof = b_league_spelling_stage(helper, produced,
                manifest["source_proofs"][next_stage], profile.id, spelling_options["variant"])
        else:
            produced, spelling_proof = helper.transform_source(produced, family=family,
                profile_id=profile.id, **spelling_options)
            require((_json_equal(spelling_proof, manifest["source_proofs"][next_stage])
                     if post_spelling == F_COMPOUND_DECLARATION else spelling_proof == manifest["source_proofs"][next_stage]),
                    "full final spelling proof/protected gaps differ")
        if post_spelling in (COMPOUND_DECLARATION, F_COMPOUND_DECLARATION):
            inverses.append((helper, spelling_proof, before_spelling, {"spelling": individual}))
        else:
            inverses.append((helper, spelling_proof, before_spelling))
        next_stage += 1
    if post_scan is not None:
        helper = scan_module(manifest, build, production_paths)
        before_scan = produced
        produced, scan_proof = helper.transform_source(produced, family=family, profile_id=profile.id)
        require(_json_equal(scan_proof, manifest["source_proofs"][next_stage])
                and helper.restore_source(produced, manifest["source_proofs"][next_stage]) == before_scan,
                "full valid-square proof/protected gaps or inverse differs")
        inverses.append((helper, scan_proof, before_scan))
        next_stage += 1
    ep_owner = None
    if post_ep is not None:
        ep_owner, ep_helpers = ep_modules(manifest, build, production_paths)
        before_ep = produced
        produced, ep_proof = ep_owner.transform_source(produced, family=family,
            profile_id=profile.id, **ep_helpers)
        supplied = manifest["source_proofs"][next_stage]
        require(_json_equal(ep_proof, supplied)
                and ep_owner.restore_source(produced, supplied, **ep_helpers) == before_ep,
                "full EP source/protected gaps/cleanup-lift inverse differs")
        inverses.append((ep_owner, supplied, before_ep, ep_helpers))
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
                                        checked=checked_artifact,
                                        **({"final_compact": True} if post_compact is not None else {})) == before_dependencies,
                "dependency compiler receipt does not bind its original source")
        inverses.append((helper, dependency_proof, before_dependencies))
        dependencies = dependency_evidence(manifest, build, dependency_declaration, dependency_proof,
                                           before_dependencies, produced,
                                           shipping_source=source if post_compact is not None else None)
        next_stage += 1
    after_dependencies = produced
    compact_evidence = None
    if post_compact is not None:
        helper = final_compact_module(manifest, build, production_paths)
        before_compact = produced
        produced, compact_proof = helper.transform_source(produced, family=family, profile_id=profile.id)
        supplied = manifest["source_proofs"][next_stage]
        require(_json_equal(compact_proof, supplied)
                and helper.restore_source(produced, supplied) == before_compact,
                "final compact source proof or complete inverse differs")
        inverses.append((helper, supplied, before_compact))
        compact_evidence = final_compact_evidence(manifest, build, before_compact, produced, native)
        next_stage += 1
    require(next_stage == len(manifest["source_proofs"]), "an admitted source stage was not consumed")
    require(produced == source, "full source projection chain does not reproduce the actual consumer")
    require(inverse_source_stages(source, inverses) == base,
            "complete final consumer inverse differs from its fresh control")
    compound_evidence = compound_native_evidence(manifest, build, source, native, proof, profile.id, ep_owner,
        policy_source=after_dependencies if post_compact is not None else None)
    if representation == "source-jit":
        require(restore_payload(payload, len(source)) == source, "source package inverse differs")
        package = load("profile_runtime_package", ROOT / "engines/scripts/source_package.py")
        wrapper = load("profile_runtime_wrapper", ROOT / "engines/experiments/tcec-next/wrapper.py")
        unlink = load("profile_runtime_unlink", ROOT / "engines/experiments/tcec-next/self_unlink.py")
        require(wrapper.header(package, unlink, manifest["compiler"]) == header,
                "source-JIT command/dependency boundary differs")
        require(wrapper.contract(package, unlink, manifest["compiler"]) == manifest["wrapper_contract"],
                "source-JIT file ownership contract differs")
        if before_dependencies != after_dependencies:
            before_whole = wrapper.package(package, unlink, before_dependencies,
                                           manifest["compression"], manifest["compiler"])
            dependency_whole = wrapper.package(package, unlink, after_dependencies,
                                               manifest["compression"], manifest["compiler"])
            require(len(dependency_whole) <= len(before_whole),
                    "dependency cleanup did not preserve or reduce the actual complete artifact")
            if post_compact is None:
                require(dependency_whole == whole,
                        "dependency output did not reproduce the complete artifact")
            require(all(row["dependency_gate"]["whole_cost"] ==
                        {"before": len(before_whole), "after": len(dependency_whole)} for row in attempts),
                    "dependency whole cost receipt differs from regenerated packaging")
        if post_compact is not None:
            pre_compact_whole = wrapper.package(package, unlink, after_dependencies,
                                                manifest["compression"], manifest["compiler"])
            require(wrapper.package(package, unlink, source, manifest["compression"], manifest["compiler"])
                    == whole and len(whole) < len(pre_compact_whole),
                    "final compact did not reproduce and reduce the complete artifact")
            cost = {"before": len(pre_compact_whole), "after": len(whole)}
            require(all(_json_equal(row.get("final_compact_cost"), cost) for row in attempts),
                    "final compact complete artifact cost differs between attempts")
            compact_evidence["whole_cost"] = cost
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
                          **({"post_scan": post_scan} if post_scan is not None else {}),
                          **({"post_ep": post_ep} if post_ep is not None else {}),
                          **({"post_compact": post_compact, "final_compact_evidence": compact_evidence}
                             if post_compact is not None else {}),
                          **({"post_league": post_league} if post_league is not None else {}),
                          **({"spelling_request": manifest["spelling_request"]}
                             if "spelling_request" in manifest else {}),
                          **({"compound_native_evidence": compound_evidence}
                             if compound_evidence is not None else {}),
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
    """Best-effort memory observation, never an execution admission gate."""
    try:
        return _effective_available_bytes(proc, cgroup_root)
    except (OSError, ValueError, IndexError, UnicodeError):
        return None


def _effective_available_bytes(proc, cgroup_root):
    fields = dict(line.split(":", 1) for line in (proc / "meminfo").read_text().splitlines() if ":" in line)
    require("MemAvailable" in fields, "host does not report available physical memory")
    available = int(fields["MemAvailable"].split()[0]) * 1024
    require(0 <= available < 1 << 63, "available memory observation is outside its range")
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


def _parse_linux_cpu_list(value):
    """Parse a sysfs CPU list without silently accepting malformed evidence."""
    result = set()
    for item in value.strip().split(","):
        fields = item.split("-")
        require(len(fields) in (1, 2) and all(field.isdecimal() for field in fields),
                "invalid sysfs CPU list")
        first, last = int(fields[0]), int(fields[-1])
        require(first <= last and last < 1 << 20, "invalid sysfs CPU range")
        group = set(range(first, last + 1))
        require(result.isdisjoint(group), "overlapping sysfs CPU list")
        result.update(group)
    return sorted(result)


def _shared_test_topology(profile_id, cpus, topology, online_cpu_count):
    """Report an observed host shape, never scored placement or policy proof."""
    wanted = {"test-p16": (16, 8), "test-p192": (192, 96)}
    require(profile_id in wanted, "not a shared SMT test profile")
    logical, physical = wanted[profile_id]
    rows = {row["cpu"]: row for row in topology}
    valid_cpus = (len(cpus) == len(set(cpus)) == logical and len(rows) == len(topology) == logical
                  and set(rows) == set(cpus))
    groups = {}
    nodes = set()
    if valid_cpus:
        for cpu in cpus:
            row = rows[cpu]
            node = row.get("node")
            if type(node) is not int or node < 0:
                valid_cpus = False
                break
            nodes.add(node)
            groups.setdefault((row["socket"], row["core"]), []).append(cpu)
    complete_pairs = valid_cpus and len(groups) == physical and all(
        len(members) == 2 and len({rows[cpu]["node"] for cpu in members}) == 1
        and all(rows[cpu].get("siblings") == sorted(members) for cpu in members)
        for members in groups.values())
    node_shape = len(nodes) == 1 if profile_id == "test-p16" else bool(nodes)
    return {"profile": profile_id, "observed_logical_cpus": len(cpus),
            "observed_physical_groups": len(groups), "observed_nodes": sorted(nodes),
            "complete_smt_sibling_pairs": bool(complete_pairs),
            "profile_cpu_node_shape_observed": bool(complete_pairs and node_shape),
            "online_cpu_count": online_cpu_count,
            "all_online_cpus_in_affinity": type(online_cpu_count) is int and online_cpu_count == len(cpus),
            "worker_affinity_observed": False, "memory_policy_observed": False,
            "tt_page_placement_observed": False, "scored_placement_confirmed": False}


def execution_host(admitted):
    cpus = sorted(os.sched_getaffinity(0))
    topology = []
    for cpu in cpus:
        directory = Path("/sys/devices/system/cpu") / ("cpu" + str(cpu)) / "topology"
        row = {"cpu": cpu, "socket": int((directory / "physical_package_id").read_text()),
               "core": int((directory / "core_id").read_text())}
        if admitted.profile_id in ("test-p16", "test-p192"):
            cpu_directory = directory.parent
            nodes = [int(path.name[4:]) for path in cpu_directory.glob("node[0-9]*")
                     if path.name[4:].isdecimal()]
            row["node"] = nodes[0] if len(nodes) == 1 else None
            try:
                row["siblings"] = _parse_linux_cpu_list((directory / "thread_siblings_list").read_text())
            except (OSError, ValueError):
                row["siblings"] = None
        topology.append(row)
    physical = {(row["socket"], row["core"]) for row in topology}
    required = {"test-p4": 4, "test-p28": 28}.get(admitted.profile_id)
    one_sibling = len(cpus) == len(physical)
    placement = required is not None and len(physical) == required and one_sibling
    result = {"affinity": cpus, "topology": topology, "physical_cores_exposed": len(physical),
            "one_sibling_per_physical_core": one_sibling,
            "test_physical_envelope_observed": placement,
            "scored_cloud_slot_confirmed": False,
            "role": "local functional observation; placement and target league preflight are separate",
            "oversubscribed_by_search_workers": admitted.resources["workers"] > len(cpus)}
    if admitted.profile_id in ("test-p16", "test-p192"):
        result["shared_smt_diagnostic"] = _shared_test_topology(
            admitted.profile_id, cpus, topology, os.cpu_count())
        result["worker_and_main_threads_exceed_affinity"] = admitted.resources["workers"] + 1 > len(cpus)
    return result


def execution_limits(admitted, available_bytes, *, wall_seconds=600):
    api = contracts()
    profile = profile_resource(admitted.profile_id, input_pins=admitted.input_pins)
    layout = profile.layout(admitted.resources["tt_entry_bytes"])
    other = max(768 * api.MiB, profile.workers * 16 * api.MiB)
    require(available_bytes is None or type(available_bytes) is int and -(1 << 63) <= available_bytes < 1 << 63,
            "available memory observation must be an integer or unknown")
    capacity = api.host_admission(profile, layout, available_bytes,
                                 other_peak_bytes=other, reserve_bytes=256 * api.MiB)
    capacity.require()
    capacity_record = capacity.to_record()
    # Neither the value nor an inability to observe it authorizes allocation,
    # resource qualification, or a scored run.
    capacity_record["availability_observed"] = available_bytes is not None
    capacity_record["availability_complete"] = None
    capacity_record["availability_scope"] = (
        "provided snapshot; effective collector clamps cgroup headroom at zero; "
        "some cgroup ancestors or controllers may be unobserved; "
        "not a capacity reservation or allocation result")
    require(type(wall_seconds) is int and 60 <= wall_seconds <= 1200, "finite runtime wall bound required")
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)
    active_cpus = max(1, min(cpus, profile.os_threads))
    # RLIMIT_CPU counts every search thread. A constant 590s would terminate a
    # legitimate W256 GO long before its wall-clock budget on a large host.
    # Each owned session has its own 140s wall budget, within the outer alarm.
    cpu_seconds = max(180, min(140, wall_seconds - 10) * active_cpus)
    return {"admission": capacity_record, "address_space_bytes": max(2 * api.GiB, layout.bytes + other),
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


def _runtime_wrapper(admitted):
    contract = admitted.wrapper_contract
    if type(contract) is AnonymousMemfdContract:
        require(type(admitted) is AdmittedBuild and admitted.representation == "self-contained-elf",
                "anonymous memfd cleanup requires a typed self-contained ELF admission")
        return contract.to_record()
    require(isinstance(contract, dict) and admitted.representation != "self-contained-elf"
            and contract.get("entry_cleanup") != "none",
            "anonymous memfd cleanup requires its producer-owned typed contract")
    return contract


def _stat_record(value):
    return {"device": value.st_dev, "inode": value.st_ino, "mode": value.st_mode,
            "links": value.st_nlink, "bytes": value.st_size,
            "mtime_ns": value.st_mtime_ns, "ctime_ns": value.st_ctime_ns}


def _validate_submitted_file(record, admitted, original=None):
    require(isinstance(record, dict) and set(record) == {"program", "whole", "stat"}
            and record["program"] == admitted.program
            and record["whole"] == _field_pin(admitted.expected, "whole"),
            "submitted ELF whole identity differs")
    stamp = record["stat"]
    require(isinstance(stamp, dict) and set(stamp) ==
            {"device", "inode", "mode", "links", "bytes", "mtime_ns", "ctime_ns"}
            and all(type(value) is int for value in stamp.values())
            and stamp["device"] >= 0 and stamp["inode"] > 0
            and stat.S_ISREG(stamp["mode"]) and stamp["links"] == 1
            and stamp["bytes"] == record["whole"]["bytes"],
            "submitted ELF must remain the original regular single-link file")
    require(original is None or record == original, "submitted ELF was replaced or changed")
    return record


def _submitted_file(admitted, build, original=None):
    """Read only the admitted program, retaining its namespace and inode identity."""
    expected = _field_pin(admitted.expected, "whole")
    require(type(expected["bytes"]) is int and 0 < expected["bytes"] <= 16 << 20,
            "submitted ELF byte extent is not admitted")
    path = artifact_file(build, admitted.program)
    before = _stat_record(path.stat())
    data = input_reader().read_regular(path, limit=expected["bytes"])
    require(pin(data) == expected and before == _stat_record(artifact_file(build, admitted.program).stat()),
            "submitted ELF changed during whole-file observation")
    return _validate_submitted_file({"program": admitted.program, "whole": pin(data), "stat": before},
                                    admitted, original)


def _anonymous_image(pid, snapshot, expected):
    """Observe the live original process and its actual anonymous native image."""
    require(type(expected.get("bytes")) is int and 0 < expected["bytes"] <= 16 << 20,
            "anonymous native byte extent is not admitted")
    proc = Path("/proc") / str(pid)
    before = _process_identity(_proc_bytes(proc / "stat", 16384), pid)
    executable = proc / "exe"
    link = str(executable.readlink())
    descriptor = os.open(executable, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0))
    try:
        stamp = _stat_record(os.fstat(descriptor))
        require(stat.S_ISREG(stamp["mode"]) and stamp["links"] == 0
                and stamp["bytes"] == expected["bytes"], "restored image is not an anonymous regular native")
        chunks, count = [], 0
        while count <= expected["bytes"]:
            value = os.read(descriptor, min(65536, expected["bytes"] + 1 - count))
            if not value:
                break
            chunks.append(value)
            count += len(value)
        native = pin(b"".join(chunks))
        require(native == expected and stamp == _stat_record(os.fstat(descriptor))
                and stamp == _stat_record(executable.stat()) and str(executable.readlink()) == link,
                "actual anonymous native image changed or differs")
    finally:
        os.close(descriptor)
    after = _process_identity(_proc_bytes(proc / "stat", 16384), pid)
    record = {"exe": link, "path": link.removesuffix(" (deleted)"), "stat": stamp,
              "native": native, "before": before, "after": after}
    _validate_anonymous_image(record, snapshot, expected, pid)
    return record


def _validate_anonymous_image(record, snapshot, expected, pid):
    require(isinstance(record, dict) and set(record) == {"exe", "path", "stat", "native", "before", "after"},
            "anonymous executable observation is incomplete")
    link, stamp = record["exe"], record["stat"]
    require(isinstance(link, str) and link.startswith("/memfd:") and link.endswith(" (deleted)")
            and record["path"] == link.removesuffix(" (deleted)")
            and snapshot.get("exe") == link and snapshot.get("path") == record["path"]
            and snapshot.get("path_exists") is False and record["native"] == expected
            and snapshot.get("native_sha256") == expected["sha256"],
            "restored executable must be the admitted deleted anonymous memfd")
    require(isinstance(stamp, dict) and set(stamp) ==
            {"device", "inode", "mode", "links", "bytes", "mtime_ns", "ctime_ns"}
            and all(type(value) is int for value in stamp.values())
            and stamp["device"] >= 0 and stamp["inode"] > 0 and stat.S_ISREG(stamp["mode"])
            and stamp["links"] == 0 and stamp["bytes"] == expected["bytes"],
            "restored image is not an anonymous regular native")
    before, after = record["before"], record["after"]
    require(all(isinstance(value, dict) and type(value.get("pid")) is int and value["pid"] == pid
                and type(value.get("start_ticks")) is int and value["start_ticks"] > 0
                and value.get("state") in ("R", "S", "D", "T", "t", "I", "W", "P")
                for value in (before, after)) and before["start_ticks"] == after["start_ticks"],
            "anonymous observation lost the live original process identity")


def _validate_anonymous_cleanup(cleanup, snapshot, admitted, original, native, pid):
    require(type(admitted.wrapper_contract) is AnonymousMemfdContract,
            "anonymous cleanup requires its typed admission")
    _runtime_wrapper(admitted)
    require(isinstance(cleanup, dict) and set(cleanup) ==
            {"entry_cleanup", "temp_strategy", "observed_while_alive", "wall_from_launch", "executable", "submitted_file"}
            and cleanup["entry_cleanup"] == "none" and cleanup["temp_strategy"] == "anonymous-memfd"
            and cleanup["observed_while_alive"] is True
            and type(cleanup["wall_from_launch"]) in (int, float) and 0 <= cleanup["wall_from_launch"] <= 60,
            "anonymous cleanup observation cannot claim submitted path removal")
    _validate_submitted_file(original, admitted)
    _validate_submitted_file(cleanup["submitted_file"], admitted, original)
    _validate_anonymous_image(cleanup["executable"], snapshot, native, pid)


def _clean_live(scope, owned, snapshot, contract, started, *, admitted=None, build=None,
                submitted=None, native=None):
    if type(contract) is AnonymousMemfdContract:
        require(admitted is not None and contract is admitted.wrapper_contract,
                "anonymous cleanup lost its admitted contract")
        _runtime_wrapper(admitted)
        executable = _anonymous_image(owned.process.pid, snapshot, native)
        outer = _submitted_file(admitted, build, submitted)
        require(not owned.exited(), "anonymous cleanup was not observed while engine remained alive")
        result = {"entry_cleanup": "none", "temp_strategy": "anonymous-memfd",
                  "observed_while_alive": True, "wall_from_launch": time.monotonic() - started,
                  "executable": executable, "submitted_file": outer}
        _validate_anonymous_cleanup(result, snapshot, admitted, submitted, native, owned.process.pid)
        return result
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


def require_runtime_launch_allowed(admitted):
    """Keep large shared profiles out of the legacy owned-runtime launcher.

    Its availability snapshot and per-process rlimits neither reserve the
    cohort's memory nor prove the complete cgroup ancestry or ownership.
    Source admission, compilation, rule checks, and revalidation of existing
    receipts remain available; a separate verified owner must supply a new
    execution path before either shared profile can actually be started.
    """
    require(admitted.profile_id not in ("test-p16", "test-p192"),
            "P16/P192 runtime launch requires a verified cohort resource owner")


def run_runtime(admitted, build, out, limits, *, target_reference=None):
    require_runtime_launch_allowed(admitted)
    global _CONSTRUCTING, _DEFERRED
    scope, owner, oracle = support_modules()
    own_path = "engines/experiments/tcec-next/profile_verify.py"
    own_source = executing_source(source_bytes(own_path))
    wrapper_contract = _runtime_wrapper(admitted)
    anonymous = type(admitted.wrapper_contract) is AnonymousMemfdContract
    submitted = _submitted_file(admitted, build) if anonymous else None
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
    if anonymous:
        report["wrapper_contract"] = wrapper_contract
        report["submitted_file_before_launch"] = submitted
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
                if anonymous:
                    _submitted_file(admitted, build, submitted)
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
                    admitted.wrapper_contract, started, admitted=admitted, build=build,
                    submitted=submitted, native=image_pin)
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
        if anonymous:
            report["submitted_file_after_groups"] = _submitted_file(admitted, build, submitted)
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
        profile=profile_resource(admitted.profile_id, input_pins=admitted.input_pins), main_source=main_source,
        source_proof=source_proof, baseline_source=baseline, build=build)


def submission_size_within_limit(whole_bytes):
    require(type(whole_bytes) is int and whole_bytes > 0, "positive complete-file size required")
    return whole_bytes <= 4096


def require_qualification_scope(admitted, scope):
    require(scope in ("general4k", "league-test"), "unknown qualification scope")
    if scope == "league-test":
        require(profile_resource(admitted.profile_id, input_pins=admitted.input_pins).purpose == "test",
                "league-test scope requires a TEST profile")


QUALIFICATION_CHECKS = ("reproduction", "size", "startup", "dependencies", "cleanup", "protocol",
                        "legal_moves", "resources", "lifecycle", "placement")


def qualification_policy(scope, purpose, checks):
    """Keep legacy 4K qualification distinct from an explicit league TEST record.

    Size is always an observed 4 KiB comparison; only a TEST-only record may
    omit it from that record's required checks. Neither scope grants score or
    submission approval by itself.
    """
    require(scope in ("general4k", "league-test"), "unknown qualification scope")
    require(scope != "league-test" or purpose == "test", "league-test scope requires a TEST profile")
    require(type(checks) is dict and type(checks.get("size")) is bool,
            "qualification requires an actual submission-size observation")
    require(set(checks) == set(QUALIFICATION_CHECKS)
            and all(type(value) is bool for value in checks.values()),
            "qualification checks must contain every explicit boolean condition")
    return [name for name, passed in checks.items()
            if passed is not True and (scope != "league-test" or name != "size")]


def scoped_qualification_record(result, scope):
    """Label a freshly assembled report without widening the v1 contract."""
    require(scope in ("general4k", "league-test"), "unknown qualification scope")
    if scope == "general4k":
        return result
    artifact, checks = result["artifact"], result["checks"]
    require(artifact["purpose"] == "test", "league-test scope requires a TEST profile")
    size = submission_size_within_limit(artifact["whole_bytes"])
    require(type(checks.get("size")) is bool and checks["size"] is size,
            "recorded submission size differs from the complete file")
    failures = qualification_policy(scope, artifact["purpose"], checks)
    require(result["failures"] == failures and result["complete"] is (not failures)
            and result["test_qualified"] is (not failures)
            and result["release_qualified"] is False and result["event_target_confirmed"] is False,
            "league-test report status differs from bound checks")
    result.update(format="rove4k-qualification-v2", division="league-test",
                  qualification_scope="league-test",
                  submission_size_within_4096=size, score_authorized=False)
    result["scope"] = ("bound full runtime and actual generated rules for league TEST only; "
                       "submission size is observed separately and score authorization remains separate")
    return result


def qualification_record(admitted, build, runtime_path, *, rules_path=None, artifact_id=None,
                         target_reference=None, qualification_scope="general4k"):
    """Bind measured evidence for registry intake; missing placement stays failed.

    This is an adapter for an already admitted artifact and an owned runtime
    receipt. It performs no engine execution and does not grant event approval.
    The immutable runtime support and raw pipe outputs are checked again.
    """
    require_qualification_scope(admitted, qualification_scope)
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
    wrapper_contract = _runtime_wrapper(admitted)
    anonymous = type(admitted.wrapper_contract) is AnonymousMemfdContract
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
    anonymous_supported = runtime_feature_required(frozen_qualifier, "ELF_ENTRY_CLEANUP", ELF_ENTRY_CLEANUP)
    submitted = None
    if anonymous:
        require(anonymous_supported and exact_rss and observed.get("wrapper_contract") == wrapper_contract,
                "frozen runtime qualifier did not observe the typed anonymous cleanup contract")
        submitted = _validate_submitted_file(observed.get("submitted_file_before_launch"), admitted)
        _validate_submitted_file(observed.get("submitted_file_after_groups"), admitted, submitted)
        _submitted_file(admitted, build, submitted)
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
        if anonymous:
            _validate_anonymous_cleanup(row["normal_temporary_cleanup"], snapshot, admitted,
                                        submitted, image_pin, row["pid"])
            executable = row["normal_temporary_cleanup"]["executable"]
            require(executable["before"]["start_ticks"] ==
                    row["startup_resident_accounting"]["before"]["start_ticks"],
                    "anonymous image and resident accounting observed different process identities")
        else:
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
    if anonymous:
        _submitted_file(admitted, build, submitted)
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
    checks = {"reproduction": True, "size": submission_size_within_limit(admitted.expected["whole_bytes"]),
              "startup": True, "dependencies": dependencies, "cleanup": True, "protocol": True,
              "legal_moves": rules is not None and rules.get("nbrq_generation") is True,
              "resources": True, "lifecycle": True, "placement": placement}
    profile = profile_resource(admitted.profile_id, input_pins=admitted.input_pins)
    failures = qualification_policy(qualification_scope, profile.purpose, checks)
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
    result = {"format": "rove4k-qualification-v1", "division": "general4k", "artifact": identity,
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
    return scoped_qualification_record(result, qualification_scope)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", help="explicit D candidate filename; omit for ABCEF")
    parser.add_argument("--rules", type=Path, help="actual source-bound rules.json; no replay-to-generation inference")
    parser.add_argument("--qualification-scope", choices=("general4k", "league-test"), default="general4k",
                        help="league-test omits the 4 KiB size gate only for TEST profiles; default retains v1")
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
    # Refuse TEST-only semantics for a submission profile before any target
    # compiler, resource scan, engine process, TT allocation, or output.
    require_qualification_scope(admitted, args.qualification_scope)
    # Existing receipts may still be revalidated. A new launch must be
    # rejected before optional target-runtime checks can start subprocesses.
    if args.runtime is None:
        require_runtime_launch_allowed(admitted)
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
                                             target_reference=reference,
                                             **({"qualification_scope": "league-test"}
                                                if args.qualification_scope == "league-test" else {}))
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
                                         target_reference=reference,
                                         **({"qualification_scope": "league-test"}
                                            if args.qualification_scope == "league-test" else {}))
    if reference is not None:
        (out / "target-runtime.json").write_text(json.dumps(reference.to_record(), indent=2) + "\n")
    (out / "qualification.json").write_text(json.dumps(qualification, indent=2) + "\n")
    print(json.dumps({"complete": report["complete"], "family": admitted.family,
                      "profile": admitted.profile_id, "whole_bytes": admitted.expected["whole_bytes"],
                      **report["counts"], "event_target_confirmed": False}), flush=True)


if __name__ == "__main__":
    main()
