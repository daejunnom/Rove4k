#!/usr/bin/env python3
"""Bind focused startup mechanisms to one admitted final compound TEST-P4.

The old phase/B diagnostic helpers retain their reviewed bytes. Only a named
fixture alias, appended AFTER the entire shipping body, adapts the old scaled
renderer. The actual W4 last-initializer barrier receives unaliased shipping C.
This is functional evidence; it makes no placement, timing or strength claim.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import platform
import re
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NEXT = "engines/experiments/tcec-next/"
SELF = NEXT + "check_profile_compound.py"
SCHEMA = "rove4k-bound-compound-mechanism-v1"
PHASE_CHECK = NEXT + "check_profile_phase.py"
PHASE = NEXT + "profile_phase.py"
SOURCE = NEXT + "profile_source.py"
COMPOUND = NEXT + "spelling_compound.py"
SPELLING = NEXT + "profile_spelling.py"
COMMON = "engines/scripts/production.py"
VERIFIER = NEXT + "profile_verify.py"
OWNER = "engines/experiments/tcec-scope/build.py"
RUNTIME = "engines/compact/tiny-entry-d/verify.py"
PHASE_CHECK_SHA = "a0c0c0ff25dd2b935f281789e7842b2bf199f3167f80df27ac1ff3550c8f4c37"
COMPOUND_PIN = dict(bytes=9472, sha256="4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce")
SPELLING_PIN = dict(bytes=9921, sha256="7ec393bc9c805ee8e1e6d715f40cb9883f829e3c6b01e2f71f31701e35136ea8")
DECLARATION = dict(path=COMPOUND, selection="compound", variant="clock-atomic-launcher")
F_COMPOUND_DECLARATION = dict(path=COMPOUND, selection="compound-v2", variant="clock-atomic-launcher-parentheses")
DEPENDENCIES = dict(path=NEXT + "profile_dependencies.py", variant="unused-includes")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def normalized(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named diagnostic source")
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def bound_selection(manifest):
    require(manifest.get("class") == "rove4k-production-profile-v1" and
        manifest.get("family") in tuple("ACEF") and manifest.get("entry") == manifest.get("family") and
        manifest.get("resources", {}).get("id") == "test-p4" and
        manifest.get("post_profile") == dict(path=PHASE, variant="phase-init") and
        (manifest.get("post_spelling") == DECLARATION or
         manifest.get("family") == "F" and manifest.get("post_spelling") == F_COMPOUND_DECLARATION) and
        manifest.get("source_dependencies") == DEPENDENCIES and
        manifest.get("plan", {}).get("representation") == "source-jit" and
        manifest.get("plan", {}).get("entry_cleanup") == "private-path",
        "compound mechanisms require final A/C/E/F TEST-P4 phase-init/compound/dependencies source-JIT")


def selected_compound_proof(manifest):
    """Select the admitted compound stage even when a later scan precedes cleanup."""
    stages = [proof for proof in manifest["source_proofs"] if proof.get("schema") in
        ("rove4k.selected-spelling-compound.v1", "rove4k.selected-spelling-compound.v2")]
    require(len(stages) == 1 and stages[0].get("variant") == manifest["post_spelling"]["variant"],
            "one admitted selected compound source stage required")
    return stages[0]


def diagnostic_alias(source, proof):
    """Derive one finite alias from the already admitted final shipping proof."""
    if proof.get("schema") == "rove4k.selected-spelling-compound.v2":
        base = proof.get("base")
        require(type(source) is bytes and proof.get("variant") == F_COMPOUND_DECLARATION["variant"] and
            proof.get("family") == "F" and proof.get("profile_id") == "test-p4" and
            proof.get("output") == pin(source) and isinstance(base, dict) and
            base.get("family") == "F" and base.get("profile_id") == "test-p4" and
            base.get("input") == proof.get("input"), "named admitted F-v2 shipping/base proof required")
        proof = base
    require(type(source) is bytes and proof.get("schema") == "rove4k.selected-spelling-compound.v1" and
        proof.get("variant") == "clock-atomic-launcher" and proof.get("family") in tuple("ACEF") and
        proof.get("profile_id") == "test-p4" and proof.get("helper") == dict(path=SPELLING, **SPELLING_PIN) and
        proof.get("components") == ["clock-type", "atomic-assignment", "launcher-short"],
        "named admitted compound launcher proof required")
    replacement = "J" if proof["family"] == "F" else "rv"
    individual = [r.get("proof") for r in proof.get("individual", []) if r.get("variant") == "launcher-short"]
    require(len(individual) == 1 and isinstance(individual[0], dict), "one launcher component required")
    component = individual[0]
    require(component.get("schema") == "rove4k.selected-spelling-experiment.v1" and
        component.get("variant") == "launcher-short" and component.get("family") == proof["family"] and
        component.get("profile_id") == "test-p4" and component.get("input") == proof.get("input"),
        "launcher component identity differs")
    rows = component.get("edits", [])
    union = [r for r in proof.get("edits", []) if r.get("component") == "launcher-short"]
    require(len(rows) == len(union) == 3 and all(r.get("before") == "rv_spawn" and
        r.get("after") == replacement and r.get("role") == "private-launcher-name" for r in rows) and
        [{k:r.get(k) for k in ("input_begin", "before", "after", "role")} for r in rows] ==
        [{k:r.get(k) for k in ("input_begin", "before", "after", "role")} for r in union],
        "launcher alias differs from the finite admitted component")
    require(b"rv_spawn" not in source and len(re.findall(rb"\b" + replacement.encode() + rb"\b", source)) == 3,
        "shipping launcher references differ from the admitted replacement")
    alias = ("\n#define rv_spawn " + replacement + "\n").encode()
    prefix = source + alias
    return prefix, dict(macro="rv_spawn", replacement=replacement, text=alias.decode(),
        shipping_source=pin(source), diagnostic_prefix=pin(prefix), launcher_component=component)


def construct_owned(runtime_module, path, directory, budget, handled):
    """Defer constructor interruptions without blocking inherited child signals."""
    # Owned itself masks TERM until its handle/readers are registered. Defer the
    # other host interrupts as Python flags, leaving the child's mask unchanged.
    deferred = [sig for sig in handled if sig != signal.SIGTERM]
    previous = {sig: signal.getsignal(sig) for sig in deferred}
    pending = []

    def defer(sig, frame):
        pending.append((sig, frame))

    for sig in deferred:
        signal.signal(sig, defer)
    try:
        result = runtime_module.Owned(path, directory, budget)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    if pending:
        sig, frame = pending[0]
        handler = previous[sig]
        if callable(handler):
            handler(sig, frame)
        raise TimeoutError("deferred compound startup signal " + str(sig))
    return result


def actual_barrier(host, owner, runtime_module, phase_check, directory, source, context, compiler, report):
    directory.mkdir()
    gate, arrived = directory / "release", directory / "last-initializer-arrived"
    fixture = phase_check.blocked_main(source, context, gate, arrived)
    require(fixture.startswith(source) and b"#define rv_spawn" not in fixture,
            "actual barrier must retain the alias-free shipping body")
    (directory / "fixture.c").write_bytes(fixture)
    host.run([*compiler, "-Wl,--wrap=pthread_create"], cwd=directory,
             kind=directory.name + "-compile", data=fixture)
    disposable = directory / "disposable-native"
    shutil.copyfile(directory / "x", disposable)
    disposable.chmod(0o700)
    runtime = None
    try:
        budget = runtime_module.Budget(25)
        runtime = construct_owned(runtime_module, disposable, directory / "runtime", budget, host.handled)
        runtime.send(b"uci\nisready\n")
        deadline = time.monotonic() + budget.left(5)
        while disposable.exists() or not arrived.exists():
            require(time.monotonic() < deadline and not runtime.exited(), "last initializer did not reach its gate")
            time.sleep(.005)
        time.sleep(.1)
        require(not runtime.exited() and runtime.stdout.bytes() == b"", "UCI escaped the actual startup barrier")
        gate.write_bytes(b"release\n")
        runtime.wait_line(b"uciok")
        runtime.wait_line(b"readyok")
        legal = {bytes((file,)) + b"2" + bytes((file,)) + rank
                 for file in range(ord("a"), ord("h") + 1) for rank in (b"3", b"4")}
        legal.update((b"b1a3", b"b1c3", b"g1f3", b"g1h3"))
        for count in (1, 2):
            runtime.send(b"position startpos\ngo wtime 30 btime 30 winc 0 binc 0\n")
            runtime.wait_best(count)
            runtime.send(b"isready\n")
            runtime.wait_line(b"readyok", count + 1)
            moves = [r[9:] for r in runtime.stdout.bytes().splitlines() if r.startswith(b"bestmove ")]
            require(len(moves) == count and all(move in legal for move in moves), "compound search result differs")
        runtime.send(b"position startpos\nisready\n")
        runtime.wait_line(b"readyok", 4)
        runtime.send(b"quit\n")
        physical = runtime.finish()
        cleanup = runtime.cleanup()
        require(not cleanup["forced_cleanup"] and not cleanup["errors"], "actual compound barrier forced cleanup")
        output = runtime.stdout.bytes()
        moves = [r[9:] for r in output.splitlines() if r.startswith(b"bestmove ")]
        require(len(moves) == 2 and all(move in legal for move in moves), "late duplicate/illegal compound result")
        (directory / "runtime.stdout").write_bytes(output)
        return dict(fixture_source=pin(fixture), native=pin((directory / "x").read_bytes()),
            actual_resource_profile="test-p4", actual_workers=4, actual_tt_entries=1 << 22,
            last_initializer_delayed=True, gate_arrival_observed=True, no_uci_before_release=True,
            uci_ready_after_release=True, private_copy_removed=not disposable.exists(), legal_search_relaunches=2,
            post_GO2_join_observed=True, output=pin(output), physical=physical, cleanup=cleanup,
            shipping_identity_claimed=False, diagnostic_alias_applied=False)
    finally:
        if runtime is not None:
            row = dict(directory=str(runtime.directory), pid=runtime.process.pid)
            try:
                row["cleanup"] = runtime.cleanup()
            except BaseException as error:
                row.update(cleanup=runtime.cleaned, error=dict(type=type(error).__name__, message=str(error)))
                raise
            finally:
                report.setdefault("barrier_runtime_cleanup", []).append(row)


def drain_owned(runtime_module, host, report):
    """Retain registered process identities through cleanup, before handler restore."""
    inherited = signal.pthread_sigmask(signal.SIG_BLOCK, set(host.handled))
    try:
        rows = []
        errors = list(report.get("runtime_cleanup", {}).get("errors", []))
        for owned in list(runtime_module.OWNED):
            try:
                rows.append(owned.cleanup())
            except BaseException as error:
                errors.append(str(error))
        prior = report.get("runtime_cleanup", {}).get("drained", [])
        report["runtime_cleanup"] = dict(remaining_owned=len(runtime_module.OWNED), drained=prior + rows, errors=errors)
        require(not runtime_module.OWNED and not errors, "compound mechanism left owned runtime groups")
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, inherited)


def run_bound(build, out):
    names = (SELF, PHASE_CHECK, PHASE, SOURCE, COMPOUND, SPELLING, COMMON, VERIFIER, OWNER, RUNTIME)
    observed = {name: normalized(ROOT / name) for name in names}
    require(pin(observed[PHASE_CHECK])["sha256"] == PHASE_CHECK_SHA and
        pin(observed[COMPOUND]) == COMPOUND_PIN and pin(observed[SPELLING]) == SPELLING_PIN,
        "reviewed compound/individual/phase diagnostic helper identity differs")
    verifier = load("compound_bound_admission", ROOT / VERIFIER)
    manifest_raw = verifier.artifact_file(build, "build.json").read_bytes()
    manifest = json.loads(manifest_raw)
    bound_selection(manifest)
    admitted = verifier.admit_c_build(manifest, build)
    require(admitted.family == manifest["family"] and admitted.profile_id == "test-p4" and admitted.full and
        admitted.representation == "source-jit" and admitted.source == "main.c" and admitted.native == "native/x" and
        manifest["compile_executor"] == manifest["compiler"], "actual compound source/JIT compiler differs")
    shipping = {role: verifier.checked_artifact(build, path,
        {key: admitted.expected[role + "_" + key] for key in ("bytes", "sha256")})
        for role, path in (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program))}
    for name, data in observed.items():
        require(normalized(ROOT / name) == data, "compound support changed during admission: " + name)
    owner = load("compound_bound_owner", ROOT / OWNER)
    require(pin(observed[PHASE]) == manifest["inputs"][PHASE] and
        pin(observed[COMPOUND]) == manifest["inputs"][COMPOUND] and
        pin(observed[SPELLING]) == manifest["inputs"][SPELLING] and
        pin(observed[RUNTIME])["sha256"] == verifier.SUPPORT[RUNTIME], "compound admitted support differs")
    out.mkdir()
    frozen = out / "inputs"
    for name, data in observed.items():
        target = frozen / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    phase_check = load("compound_frozen_phase_check", frozen / PHASE_CHECK)
    phase = load("compound_frozen_phase", frozen / PHASE)
    runtime_module = load("compound_frozen_runtime", frozen / RUNTIME)
    require(not runtime_module.OWNED, "new compound runtime namespace is not empty")
    source = shipping["source"]
    resource_proof = manifest["source_proofs"][0]
    compound_proof = selected_compound_proof(manifest)
    prefix, alias = diagnostic_alias(source, compound_proof)
    require(resource_proof["family"] == admitted.family and resource_proof["resources"]["workers"] == 4 and
        resource_proof["resources"] == {key: admitted.resources[key] for key in resource_proof["resources"]},
        "actual compound resource proof differs")
    report = dict(format=1, **{"class": SCHEMA}, mode="source-bound", complete=False, source_bound=False,
        entry=admitted.family, profile=admitted.profile_id, representation=admitted.representation,
        selected_post_profile=manifest["post_profile"], selected_post_spelling=manifest["post_spelling"],
        source_dependencies=manifest["source_dependencies"], build=dict(path=str(build), **pin(manifest_raw)),
        actual={role: dict(path=path, **pin(shipping[role])) for role, path in
            (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program))},
        resources=admitted.resources, source_closure=manifest["source_closure"], admitted_input_pins=admitted.input_pins,
        source_contract=admitted.source_contract, support_inputs={name: pin(data) for name, data in observed.items()},
        diagnostic_alias=alias, commands=[], mechanisms=[], startup_barriers=[], production_adopted=False,
        runtime_qualified=False, rules_eligibility="unproven", shipping_binary_executed=False,
        large_submission_tt_executed=False, derived_other_resource_profiles=False, timing_claimed=False,
        scope="admitted final compound source; named diagnostic alias for scaled callbacks; alias-free actual W4 barrier")

    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    owner.LIMITS.update(aggregate_wall=300, per_command_wall=60, parent_AS=2 << 30, child_AS=2 << 30,
        parent_CPU=120, parent_CPU_hard=150, child_CPU=45)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    host = owner.Host(out, report, save)
    closed = False
    try:
        context = phase.CONTEXT[admitted.family]
        directory = out / "selected-W4-scaled-callback"
        directory.mkdir()
        fixture, expected = phase_check.scaled_fixture(prefix, resource_proof, context)
        (directory / "diagnostic-prefix.c").write_bytes(prefix)
        (directory / "fixture.c").write_bytes(fixture)
        compiler = manifest["compiler"]
        host.run([*compiler, "-Wl,--wrap=pthread_create"], cwd=directory,
                 kind="selected-W4-scaled-callback-compile", data=fixture)
        raw = host.run([directory / "x"], cwd=directory, kind="selected-W4-scaled-callback-execute")
        lines = raw.decode("ascii").splitlines()
        require(len(lines) == 3 and lines[:2] == ["bestmove g1f3", "bestmove b1c3"] and
            json.loads(lines[2]) == expected, "actual compound callback/selector mechanism differs")
        report["mechanisms"].append(dict(profile="test-p4", variant=manifest["post_spelling"]["variant"],
            shipping_source=pin(source), diagnostic_prefix_source=pin(prefix), fixture_source=pin(fixture),
            native=pin((directory / "x").read_bytes()), observation=expected, output=pin(raw), selector_results=lines[:2],
            fixture_tt_entries=1 << phase_check.FIXTURE_BITS, shipping_worker_count_unchanged=True,
            shipping_tt_executed=False, shipping_binary_executed=False, search_executed=False))
        save()
        barrier = actual_barrier(host, owner, runtime_module, phase_check, out / "selected-W4-last-initializer",
            source, context, compiler, report)
        report["startup_barriers"].append(dict(variant=manifest["post_spelling"]["variant"], shipping_source=pin(source), **barrier))
        require(verifier.artifact_file(build, "build.json").read_bytes() == manifest_raw and
            verifier.admit_c_build(manifest, build) == admitted, "actual compound build/admission changed")
        for role, path in (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program)):
            require(verifier.checked_artifact(build, path, pin(shipping[role])) == shipping[role],
                    "actual compound artifact changed")
        for name, data in observed.items():
            require(normalized(ROOT / name) == data, "compound support changed during execution: " + name)
        drain_owned(runtime_module, host, report)
        host.close()
        closed = True
        require(report["host_cleanup"] == dict(unsettled_commands=0, errors=[]), "compound commands did not settle")
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
                drain_owned(runtime_module, host, report)
            finally:
                if not closed:
                    host.close()
                save()
        finally:
            signal.signal(signal.SIGCHLD, previous)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps(dict(entry=admitted.family, profile=admitted.profile_id, complete=True, source_bound=True,
        mechanisms=1, startup_barriers=1, actual_short_GO_cycles=2, production_adopted=False, runtime_qualified=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or not args.out.is_absolute() or out.exists() or
        ROOT in (out, *out.parents) or any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("Linux x86-64 and a new absolute external output required")
    if not args.build.is_absolute() or not args.build.is_dir():
        parser.error("existing absolute compound production build required")
    run_bound(args.build.resolve(), out)


if __name__ == "__main__":
    main()
