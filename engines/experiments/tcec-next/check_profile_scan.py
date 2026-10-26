#!/usr/bin/env python3
"""Bind the selected A/C square scan to existing P4/P28 startup mechanisms.

Only orchestration is new. Reviewed diagnostic renderers and process owners
remain unchanged. P4 reduces diagnostic TT size only; P28 checks the full real
384 MiB table. Each profile separately runs an unaliased original-main barrier.
No shipping image, NUMA placement, strength or W256 runtime is qualified here.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NEXT = "engines/experiments/tcec-next/"
SELF = NEXT + "check_profile_scan.py"
SCHEMA = "rove4k-bound-scan-mechanism-v1"
VERIFIER = NEXT + "profile_verify.py"
LIFECYCLE = NEXT + "check_profile_compound.py"
P28 = NEXT + "check_profile_p28.py"
PHASE_CHECK = NEXT + "check_profile_phase.py"
PHASE = NEXT + "profile_phase.py"
SOURCE = NEXT + "profile_source.py"
SPELLING = NEXT + "profile_spelling.py"
COMPOUND = NEXT + "spelling_compound.py"
SCAN = NEXT + "profile_scan.py"
COMMON = "engines/scripts/production.py"
OWNER = "engines/experiments/tcec-scope/build.py"
RUNTIME = "engines/compact/tiny-entry-d/verify.py"
FIXED_INPUTS = {
    LIFECYCLE: dict(bytes=20823, sha256="1f3b9fc6ccd3796a8bbffd8c9ebd81db1a9fb5f38eb9752ec23f40d432b68168"),
    P28: dict(bytes=29400, sha256="b71da77276bea6e3461eb59ebd1f818bd830a17f4c4cefb32aabd3b1d267a79e"),
    PHASE_CHECK: dict(bytes=30905, sha256="a0c0c0ff25dd2b935f281789e7842b2bf199f3167f80df27ac1ff3550c8f4c37"),
    SPELLING: dict(bytes=9921, sha256="7ec393bc9c805ee8e1e6d715f40cb9883f829e3c6b01e2f71f31701e35136ea8"),
    COMPOUND: dict(bytes=9472, sha256="4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce"),
    SCAN: dict(bytes=10623, sha256="98eb3139bcbd745f08fbab2d8a738b428d4e668de2604ac3fc715de8c58b879f"),
}
COMPOUND_DECLARATION = dict(path=COMPOUND, selection="compound", variant="clock-atomic-launcher")
SCAN_DECLARATION = dict(path=SCAN, variant="square-successor")
DEPENDENCIES = dict(path=NEXT + "profile_dependencies.py", variant="unused-includes")
STAGES = ("rove4k.c-resource-projection.v1", "rove4k.portable-phase-source.v1",
          "rove4k.selected-spelling-compound.v1", "rove4k.selected-square-scan.v1",
          "rove4k.profile-dependencies.v1")
PROFILES = {"test-p4": (4, 22), "test-p28": (28, 24)}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def normalized(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named scan mechanism input")
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def bound_selection(manifest):
    """Reject foreign routes before any output, allocation or compiler starts."""
    family, resources = manifest.get("family"), manifest.get("resources", {})
    profile = resources.get("id") if type(resources) is dict else None
    require(manifest.get("class") == "rove4k-production-profile-v1" and family in ("A", "C")
        and manifest.get("entry") == family and profile in PROFILES
        and manifest.get("post_profile") == dict(path=PHASE, variant="phase-init")
        and manifest.get("post_spelling") == COMPOUND_DECLARATION
        and manifest.get("post_scan") == SCAN_DECLARATION
        and manifest.get("source_dependencies") == DEPENDENCIES
        and manifest.get("plan", {}).get("representation") == "source-jit"
        and manifest.get("plan", {}).get("entry_cleanup") == "private-path",
        "scan mechanisms require named A/C compound/scan/dependencies TEST source-JIT")
    workers, bits = PROFILES[profile]
    expected = dict(workers=workers, tt_bits=bits, tt_entries=1 << bits,
        tt_bytes=(1 << bits) * 24, tt_entry_bytes=24, tt_mask=(1 << bits) - 1)
    require(all(type(resources.get(key)) is type(value) and resources[key] == value
                for key, value in expected.items()), "exact scan mechanism worker/TT resources required")
    proofs = manifest.get("source_proofs")
    require(type(proofs) is list and all(type(row) is dict for row in proofs)
        and [row.get("schema") for row in proofs] == list(STAGES),
        "scan mechanism requires exactly resource/phase/compound/scan/dependencies in order")
    require(proofs[0].get("family") == family
        and all(row.get("family") == family and row.get("profile_id") == profile for row in proofs[1:4])
        and proofs[1].get("variant") == "phase-init"
        and proofs[2].get("variant") == "clock-atomic-launcher"
        and proofs[3].get("variant") == "square-successor",
        "scan mechanism source-proof family/profile/variant differs")
    helper = manifest.get("inputs", {}).get(SCAN)
    require(type(helper) is dict and type(helper.get("bytes")) is int and helper == FIXED_INPUTS[SCAN],
        "reviewed scan helper production identity differs")
    return profile


def checked_support(observed):
    for name, identity in FIXED_INPUTS.items():
        require(name in observed and pin(observed[name]) == identity,
                "reviewed scan mechanism helper differs: " + name)


def prepare_fixture(source, manifest, lifecycle, phase_check, phase, p28):
    """The final shipping bytes remain the diagnostic source authority."""
    profile = bound_selection(manifest)
    family, proofs = manifest["family"], manifest["source_proofs"]
    if profile == "test-p4":
        prefix, alias = lifecycle.diagnostic_alias(source, proofs[2])
        fixture, observation = phase_check.scaled_fixture(prefix, proofs[0], phase.CONTEXT[family])
        return dict(fixture=fixture, observation=observation, prefix=prefix, alias=alias)
    fixture, observation, trace, geometry = p28.full_callback_fixture(source, family, proofs[0])
    return dict(fixture=fixture, observation=observation, trace=trace, geometry=geometry)


def run_bound(build, out):
    names = (SELF, VERIFIER, LIFECYCLE, P28, PHASE_CHECK, PHASE, SOURCE,
             SPELLING, COMPOUND, SCAN, COMMON, OWNER, RUNTIME)
    observed = {name: normalized(ROOT / name) for name in names}
    checked_support(observed)
    verifier = load("scan_current_admission", ROOT / VERIFIER)
    manifest_raw = verifier.artifact_file(build, "build.json").read_bytes()
    manifest = json.loads(manifest_raw)
    profile = bound_selection(manifest)
    admitted = verifier.admit_c_build(manifest, build)
    require(admitted.family == manifest["family"] and admitted.profile_id == profile and admitted.full
        and admitted.representation == "source-jit" and admitted.source == "main.c" and admitted.native == "native/x"
        and manifest["compile_executor"] == manifest["compiler"], "admitted full scan source/JIT compiler differs")
    proof_raw = verifier.artifact_file(build, "source-proof.json").read_bytes()
    require(json.loads(proof_raw) == manifest["source_proofs"], "scan raw source proof differs from the admitted manifest")
    shipping = {role: verifier.checked_artifact(build, path,
        {key: admitted.expected[role + "_" + key] for key in ("bytes", "sha256")})
        for role, path in (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program))}
    require(pin(observed[RUNTIME])["sha256"] == verifier.SUPPORT[RUNTIME], "reviewed process owner differs")
    for name in (PHASE, SPELLING, COMPOUND, SCAN):
        require(pin(observed[name]) == manifest["inputs"][name], "admitted scan tool differs: " + name)
    limits = verifier.execution_limits(admitted, verifier.effective_available_bytes())
    for name, data in observed.items():
        require(normalized(ROOT / name) == data, "scan support changed during admission: " + name)
    out.mkdir()
    for name, data in observed.items():
        target = out / "inputs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    frozen = out / "inputs"
    owner = load("scan_frozen_host", frozen / OWNER)
    runtime_module = load("scan_frozen_runtime", frozen / RUNTIME)
    lifecycle = load("scan_frozen_lifecycle", frozen / LIFECYCLE)
    phase_check = load("scan_frozen_phase_check", frozen / PHASE_CHECK)
    phase = load("scan_frozen_phase", frozen / PHASE)
    p28 = load("scan_frozen_p28", frozen / P28)
    require(not runtime_module.OWNED, "new scan runtime namespace is not empty")
    source = shipping["source"]
    prepared = prepare_fixture(source, manifest, lifecycle, phase_check, phase, p28)
    resource_proof = manifest["source_proofs"][0]
    require(resource_proof["resources"] == {key: admitted.resources[key] for key in resource_proof["resources"]},
            "actual scan mechanism resource proof differs")
    report = dict(format=1, **{"class": SCHEMA}, mode="source-bound", complete=False, source_bound=False,
        entry=admitted.family, profile=profile, representation=admitted.representation,
        selected_post_profile=manifest["post_profile"], selected_post_spelling=manifest["post_spelling"],
        selected_post_scan=manifest["post_scan"], source_dependencies=manifest["source_dependencies"],
        build=dict(path=str(build), **pin(manifest_raw)),
        actual={role: dict(path=path, **pin(shipping[role])) for role, path in
            (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program))},
        resources=admitted.resources, source_closure=manifest["source_closure"], source_contract=admitted.source_contract,
        admitted_input_pins=admitted.input_pins, source_proofs=pin(proof_raw),
        support_inputs={name: pin(data) for name, data in observed.items()}, host_admission=limits["admission"],
        observed_affinity=sorted(os.sched_getaffinity(0)), commands=[], mechanisms=[], startup_barriers=[],
        production_adopted=False, runtime_qualified=False, rules_eligibility="unproven", placement_qualified=False,
        timing_claimed=False, NUMA_qualified=False, shipping_binary_executed=False, W256_executed=False,
        large_submission_tt_executed=False, derived_other_resource_profiles=False,
        scope="final admitted A/C square-scan source; inherited profile-specific diagnostic and separate alias-free main barrier")
    if profile == "test-p4":
        report["diagnostic_alias"] = prepared["alias"]

    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    cpu = limits["CPU_seconds"][0]
    owner.LIMITS.update(aggregate_wall=360, per_command_wall=120, parent_AS=limits["address_space_bytes"],
        child_AS=limits["address_space_bytes"], parent_CPU=cpu + 30, parent_CPU_hard=cpu + 60, child_CPU=cpu)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    host = owner.Host(out, report, save)
    closed = False
    try:
        stem = "selected-W4-scaled-callback" if profile == "test-p4" else "selected-W28-full-callback"
        directory = out / stem
        directory.mkdir()
        fixture, expected = prepared["fixture"], prepared["observation"]
        (directory / "fixture.c").write_bytes(fixture)
        if profile == "test-p4":
            (directory / "diagnostic-prefix.c").write_bytes(prepared["prefix"])
        else:
            (directory / "trace-proof.json").write_text(json.dumps(prepared["trace"], indent=2) + "\n")
        compiler = manifest["compiler"]
        link_flags = p28.LINK_FLAGS if profile == "test-p28" else ("-Wl,--wrap=pthread_create",)
        host.run([*compiler, *link_flags], cwd=directory, kind=stem + "-compile", data=fixture)
        raw = host.run([directory / "x"], cwd=directory, kind=stem + "-execute")
        if profile == "test-p4":
            lines = raw.decode("ascii").splitlines()
            require(len(lines) == 3 and lines[:2] == ["bestmove g1f3", "bestmove b1c3"]
                and json.loads(lines[2]) == expected, "actual scan P4 callback/selector mechanism differs")
            report["mechanisms"].append(dict(profile=profile, variant="clock-atomic-launcher",
                shipping_source=pin(source), diagnostic_prefix_source=pin(prepared["prefix"]), fixture_source=pin(fixture),
                native=pin((directory / "x").read_bytes()), observation=expected, output=pin(raw), selector_results=lines[:2],
                fixture_tt_entries=1 << phase_check.FIXTURE_BITS, shipping_worker_count_unchanged=True,
                shipping_tt_executed=False, shipping_binary_executed=False, search_executed=False))
        else:
            require(raw == (json.dumps(expected, separators=(",", ":")) + "\n").encode(),
                    "actual scan P28 key/data/flag/page-owner callback audit differs")
            report["mechanisms"].append(dict(name="full-W28-TT24-initialization", profile=profile,
                shipping_source=pin(source), fixture_source=pin(fixture), native=pin((directory / "x").read_bytes()),
                output=pin(raw), observation=expected, trace_proof=prepared["trace"], geometry=prepared["geometry"],
                diagnostic_preamble=dict(text=p28.DIAGNOSTIC_PREAMBLE.decode(), **pin(p28.DIAGNOSTIC_PREAMBLE)),
                resource_constants_changed=False, padding_checked=False, search_executed=False,
                poisoning_changes_first_touch=True, NUMA_claimed=False, production_startup_timing_claimed=False))
        save()
        if profile == "test-p4":
            barrier = lifecycle.actual_barrier(host, owner, runtime_module, phase_check,
                out / "selected-W4-last-initializer", source, phase.CONTEXT[admitted.family], compiler, report)
            report["startup_barriers"].append(dict(variant="clock-atomic-launcher", shipping_source=pin(source), **barrier))
        else:
            report["startup_barriers"].append(p28.actual_barrier(host, runtime_module, lifecycle,
                out / "selected-W28-last-initializer", source, admitted.family, compiler, report))
        require(verifier.artifact_file(build, "build.json").read_bytes() == manifest_raw
            and verifier.admit_c_build(manifest, build) == admitted, "actual scan source admission changed")
        require(verifier.artifact_file(build, "source-proof.json").read_bytes() == proof_raw,
                "scan raw source proof changed during its mechanisms")
        for role, path in (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program)):
            require(verifier.checked_artifact(build, path, pin(shipping[role])) == shipping[role], "actual scan artifact changed")
        for name, data in observed.items():
            require(normalized(ROOT / name) == data, "scan support changed during execution: " + name)
        lifecycle.drain_owned(runtime_module, host, report)
        host.close()
        closed = True
        require(report["host_cleanup"] == dict(unsettled_commands=0, errors=[]), "scan owned commands are unsettled")
        report.update(complete=True, source_bound=True)
        save()
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    finally:
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, set(host.handled))
        try:
            try:
                lifecycle.drain_owned(runtime_module, host, report)
            finally:
                if not closed:
                    host.close()
                save()
        finally:
            signal.signal(signal.SIGCHLD, previous)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps(dict(entry=admitted.family, profile=profile, complete=True, source_bound=True,
        actual_workers=PROFILES[profile][0], legal_GO_cycles=2, placement_qualified=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or not args.out.is_absolute() or out.exists()
        or ROOT in (out, *out.parents) or any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("Linux x86-64 and a new absolute external output required")
    if not args.build.is_absolute() or not args.build.is_dir():
        parser.error("existing absolute selected scan build required")
    run_bound(args.build.resolve(), out)


if __name__ == "__main__":
    main()
