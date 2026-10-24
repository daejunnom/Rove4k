#!/usr/bin/env python3
"""Admit exact first-cost gains, then run each frozen selected verifier once.

Original cost artifacts and all 35 original control inputs remain immutable.
An explicitly derived execution recipe changes five representation pins and
narrows historical reuse to the unchanged complete native image. There is no
separate producer compilation, preprocessing, recompression, or broad engine
test matrix. Each selected wrapper still performs its normal fixed compilation
when the original verifier launches it for a session.
"""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
_PINS_SHA256 = "8d6b03d5a0e273721c8b97e186d04757d27487ec02cc9d22e325c96a452dfc7c"
_PINS_RAW = (HERE / "runtime-pins.json").read_bytes()
if hashlib.sha256(_PINS_RAW).hexdigest() != _PINS_SHA256:
    raise ValueError("literal runtime-pins.json SHA-256 mismatch")
_EXPECTED_CHANGE_KEYS = frozenset(("source_bytes", "source_sha256", "whole_bytes", "whole_sha256", "bootstrap_sha256"))
_ARTIFACT_KEYS = {"main.c": "source", "native/x": "native", "x": "whole", "bootstrap.py": "bootstrap"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(document):
    return (json.dumps(document, indent=2) + "\n").encode("utf-8")


def exact(root, relative, pin):
    """Read only one named, in-root, nonsymlink file and check its raw bytes."""
    root = Path(root).resolve()
    relative = Path(relative)
    require(not relative.is_absolute() and ".." not in relative.parts, "unsafe pinned relative path")
    path = root / relative
    require(root in path.resolve().parents, "pinned input escaped its root")
    require(not any(p.is_symlink() for p in (path, *path.parents) if p != root and root in p.parents),
            "symlink in pinned input path")
    data = path.read_bytes()
    require(sha(data) == pin["sha256"] and ("bytes" not in pin or len(data) == pin["bytes"]),
            "pinned raw input differs: " + str(path))
    return data


def _summary_matches(row, artifacts):
    for relative, kind in _ARTIFACT_KEYS.items():
        expected = artifacts[relative]
        require(row[kind + "_sha256"] == expected["sha256"], "cost artifact SHA differs: " + kind)
        if kind != "bootstrap":
            require(row[kind + "_bytes"] == expected["bytes"], "cost artifact length differs: " + kind)


def admit(build):
    """Pure admission: read fixed inputs, return admitted bytes, never execute.

    Both this experiment's owned control closure and the actual cost producer's
    frozen closure must match the same 35 literal pins. No live canonical entry
    is consulted. Returned bytes are copied only after every family is admitted.
    """
    build = Path(build).resolve()
    pins = json.loads(_PINS_RAW)
    require(pins["format"] == 1 and len(pins["control_inputs"]) == 35, "unsupported runtime pin closure")
    require(set(pins["families"]) == {"B", "C", "E"}, "runtime family set differs")
    cost_raw = exact(build, "results.json", pins["cost_receipt"])
    cost = json.loads(cost_raw)
    require(cost["complete"] is True and cost["engine_runs"] == 0, "cost receipt did not complete without runtime")
    require(cost["source_checkpoint"] == pins["source_checkpoint"], "cost source checkpoint differs")
    require(cost["producer_inputs"] == pins["producer_inputs"] and cost["control_inputs"] == pins["control_inputs"],
            "cost producer/control manifest differs")
    require(set(cost["families"]) == set(pins["families"]), "cost family set differs")
    producer = {}
    for relative, pin in pins["producer_inputs"].items():
        own = exact(HERE, relative, pin)
        frozen = exact(build / "recipe", relative, pin)
        require(own == frozen, "owned/frozen producer bytes differ")
        producer[relative] = own
    require(set(producer) == {"recipe.json", "build.py", "policy.py", "policy.json"}, "producer closure differs")
    recipe = json.loads(producer["recipe.json"])
    require(recipe["control_file_count"] == 35 and recipe["live_canonical_dependencies"] is False,
            "producer is not a closed control recipe")
    require({name: {key: value[key] for key in ("bytes", "sha256")}
             for name, value in recipe["control_files"].items()} == pins["control_inputs"],
            "cost recipe control pins differ")
    controls = {}
    for relative, pin in pins["control_inputs"].items():
        own = exact(HERE / "control", relative, pin)
        frozen = exact(build / "recipe", relative, pin)
        require(own == frozen, "owned/frozen control bytes differ")
        controls[relative] = own
    families = {}
    for family in ("B", "C", "E"):
        fixed, row = pins["families"][family], cost["families"][family]
        expected = fixed["original_expected"]
        original = json.loads(controls[fixed["entry"] + "/recipe.json"])
        require(original["family"] == family and original["expected"] == expected,
                "original recipe expected values differ")
        require(recipe["control_expected"][family] == expected, "producer old expected values differ")
        require(original["compiler"] == fixed["compiler"], "original compiler arguments differ")
        require(row["status"] == fixed["status"] == "gain_native_exact_runtime_pending"
                and row["native_identity_required"] is True, "family is not an authorized exact-native gain")
        control = row["control"]
        require(control["complete"] is True and control["independent_attempts"] == 2,
                "original control lacks two actual reproductions")
        require(control["build_json_sha256"] == fixed["control_build_sha256"], "control build receipt pin differs")
        control_raw = exact(build, "control-" + family + "/build.json", {"sha256": fixed["control_build_sha256"]})
        control_build = json.loads(control_raw)
        require(control_build["complete"] is True and len(control_build["attempts"]) == 2,
                "actual control build did not complete twice")
        for key in ("source_sha256", "native_sha256", "whole_sha256", "whole_bytes", "dev_source_sha256", "dev_native_sha256"):
            require(control[key] == expected[key], "cost original identity differs: " + key)
        for number, attempt in enumerate(control_build["attempts"], 1):
            require(attempt["attempt"] == number, "control attempt numbering differs")
            for kind in ("source", "native", "whole", "bootstrap"):
                require(attempt[kind + "_sha256"] == expected[kind + "_sha256"], "control attempt identity differs")
            require(attempt["dev"]["source_sha256"] == expected["dev_source_sha256"]
                    and attempt["dev"]["native_sha256"] == expected["dev_native_sha256"]
                    and attempt["dev"]["exact_qualified_control_bytes"] is True, "unchanged DEV proof differs")
        gate = row["header_gate"]
        require(gate["pass"] is True and gate["fresh_alias_capture"] == []
                and gate["strict_full_preprocessed_alpha_inverse_bytes_equal"] is True
                and gate["expanded_control_sha256"] == gate["expanded_inverse_sha256"]
                and gate["numeric_inverse_replacements"] == 0 and gate["final_macro_definitions_equal"] is True
                and gate["resource_macro_values"] == {"WORKERS": "2", "TT_BITS": "18", "PLY": "128"},
                "actual header/PP identity gate did not pass")
        candidate = row["candidate"]
        require(candidate["independent_attempts"] == 2 and len(candidate["attempts"]) == 2
                and candidate["full_native_exact"] is True and candidate["complete_file_reproduced"] is True,
                "candidate lacks two actual full reproductions")
        _summary_matches(candidate, fixed["artifacts"])
        require(candidate["native_sha256"] == expected["native_sha256"]
                and candidate["native_bytes"] == expected["native_bytes"], "complete original native identity differs")
        require(candidate["whole_saved_bytes"] == fixed["whole_saved_bytes"] > 0
                and candidate["source_saved_bytes"] == fixed["source_saved_bytes"] > 0
                and expected["whole_bytes"] - candidate["whole_bytes"] == fixed["whole_saved_bytes"],
                "candidate has no pinned complete-file gain")
        artifacts, attempts = {}, []
        for number, attempt in enumerate(candidate["attempts"], 1):
            require(attempt["attempt"] == number and attempt["compiler"] == fixed["compiler"],
                    "candidate attempt recipe differs")
            _summary_matches(attempt, fixed["artifacts"])
            current = {relative: exact(build / ("candidate-" + family) / ("attempt-" + str(number)), relative, pin)
                       for relative, pin in fixed["artifacts"].items()}
            if number == 1:
                artifacts = current
            else:
                require(current == artifacts, "two actual candidate attempts differ byte-for-byte")
            attempts.append(current)
        for relative, pin in fixed["artifacts"].items():
            require(exact(build / ("candidate-" + family), relative, pin) == artifacts[relative],
                    "selected candidate differs from both admitted attempts")
        families[family] = {"fixed": fixed, "original": original, "artifacts": artifacts,
                            "attempts": attempts, "cost_candidate": candidate}
    return {"pins": pins, "cost": cost, "cost_raw": cost_raw, "producer": producer,
            "controls": controls, "families": families}


def execution_recipe(original_raw, fixed, cost_sha):
    """Make an explicit runtime-only config; preserve all other expected pins."""
    original = json.loads(original_raw)
    require(original["expected"] == fixed["original_expected"], "execution original expected pins differ")
    require(set(fixed["expected_changes"]) == _EXPECTED_CHANGE_KEYS, "execution config must change exactly five expected keys")
    configured = deepcopy(original)
    changes = {key: {"original": original["expected"][key], "execution": value}
               for key, value in fixed["expected_changes"].items()}
    require(all(x["original"] != x["execution"] for x in changes.values()), "execution expected changes must be explicit")
    configured["expected"].update(fixed["expected_changes"])
    require({key for key in original["expected"] if original["expected"][key] != configured["expected"][key]}
            == _EXPECTED_CHANGE_KEYS, "execution expected values changed outside representation pins")
    configured["qualified_receipt"] = {
        "scope": "Historical core reuse only, justified by the exact complete original shipping native SHA-256. Nested old metadata is provenance, not fresh source/wrapper/runtime qualification.",
        "unchanged_full_native_sha256": original["expected"]["native_sha256"],
        "first_cost_receipt_sha256": cost_sha,
        "source_representation_and_wrapper_changed": True,
        "original_qualified_receipt_metadata": deepcopy(original["qualified_receipt"]),
        "fresh_runtime_scope": "Exactly two selected sessions, quit and EOF; results recorded separately."}
    require({key: value for key, value in configured.items() if key not in ("expected", "qualified_receipt")}
            == {key: value for key, value in original.items() if key not in ("expected", "qualified_receipt")},
            "execution recipe changed outside explicit expected/provenance fields")
    result = encoded(configured)
    return result, {"scope": "explicit runtime verification configuration; original recipe is preserved separately",
                    "original_recipe_sha256": sha(original_raw), "execution_recipe_sha256": sha(result),
                    "expected_changes": changes, "all_other_expected_values_preserved": True,
                    "original_expected": original["expected"], "execution_expected": configured["expected"],
                    "qualified_receipt": configured["qualified_receipt"]}


def write_file(root, relative, data, executable=False):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    if executable:
        target.chmod(0o755)
    require(target.read_bytes() == data, "output copy differs: " + str(target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    if (not args.build.is_absolute() or not args.out.is_absolute() or out.exists()
            or build == out or build in out.parents or HERE == out or HERE in out.parents
            or any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("existing absolute cost root and new absolute output outside cost/source/Git are required")
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        parser.error("selected physical verification requires Linux x86-64")
    admitted = admit(build)
    pins = admitted["pins"]
    out.mkdir(parents=True)
    report = {"complete": False, "scope": "Exact first-cost gains; original native/core identity reused, fresh selected restoration/quit/EOF only.",
              "cost_receipt_sha256": pins["cost_receipt"]["sha256"], "runtime_pins_sha256": _PINS_SHA256,
              "families": {}, "fresh_sessions": 0, "broad_core_games_benchmarks_run": False}

    def save():
        (out / "results.json").write_bytes(encoded(report))

    save()
    try:
        write_file(out, "cost-results.json", admitted["cost_raw"])
        write_file(out, "verification-producer/runtime-pins.json", _PINS_RAW)
        own_verifier = Path(__file__).read_bytes()
        write_file(out, "verification-producer/verify.py", own_verifier)
        report["verifier_sha256"] = sha(own_verifier)
        for relative, data in admitted["producer"].items():
            write_file(out / "cost-producer", relative, data)
        execution = out / "execution-recipe"
        for relative, data in admitted["controls"].items():
            write_file(out / "control-inputs", relative, data)
            write_file(execution, relative, data)
        report["control_inputs"] = pins["control_inputs"]
        configured_outputs = {}
        for family in ("B", "C", "E"):
            selected = admitted["families"][family]
            fixed, original = selected["fixed"], selected["original"]
            relative = fixed["entry"] + "/recipe.json"
            configured, config_proof = execution_recipe(admitted["controls"][relative], fixed, pins["cost_receipt"]["sha256"])
            write_file(execution, relative, configured)
            configured_outputs[relative] = {"bytes": len(configured), "sha256": sha(configured)}
            destination = out / ("admitted-" + family)
            for name, data in selected["artifacts"].items():
                write_file(destination, name, data, name in ("x", "native/x"))
            for number, attempt in enumerate(selected["attempts"], 1):
                for name, data in attempt.items():
                    write_file(destination / ("attempt-" + str(number)), name, data, name in ("x", "native/x"))
            derived = {"complete": True,
                       "scope": "Derived admission of two actual first-cost producer attempts; no producer regeneration/compilation was performed for admission. Later selected wrapper sessions perform their normal fixed compilation.",
                       "cost_receipt_sha256": pins["cost_receipt"]["sha256"],
                       "source_native_whole_reproduction_proof": "two actual producer attempts, exact byte copies admitted against literal pins",
                       "attempts": selected["cost_candidate"]["attempts"], "artifacts": fixed["artifacts"],
                       "native_exact_original": True, "whole_saved_bytes": fixed["whole_saved_bytes"],
                       "DEV": "not transformed or executed here; unchanged control DEV is separate cost proof",
                       "runtime_execution_config": config_proof}
            write_file(destination, "build.json", encoded(derived))
            report["families"][family] = {"status": "admitted_runtime_pending", "admitted_build": str(destination),
                                          "derived_build_sha256": sha(encoded(derived)), "execution_config": config_proof}
        save()
        # Verify the exact original helper/verifier bytes before invoking any
        # family. Only the three declared recipe configurations may differ.
        for relative, pin in pins["control_inputs"].items():
            if not any(relative == row["fixed"]["entry"] + "/recipe.json" for row in admitted["families"].values()):
                exact(execution, relative, pin)
        for family in ("B", "C", "E"):
            fixed = admitted["families"][family]["fixed"]
            row = report["families"][family]
            destination, runtime_out = out / ("admitted-" + family), out / ("runtime-" + family)
            command = ["python3", "-B", str(execution / fixed["entry"] / "verify.py"),
                       "--build", str(destination), "--out", str(runtime_out)]
            row.update(status="runtime_started", command=command, original_verifier_invocations=1)
            save()
            # The original verifier owns its bounded Engine sessions and cleanup.
            # The outer managed command owns this invocation; there is no retry,
            # independent engine launch, or verifier-only forced timeout here.
            process = subprocess.run(command, cwd=out, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            write_file(out, "runtime-" + family + ".stdout", process.stdout)
            write_file(out, "runtime-" + family + ".stderr", process.stderr)
            row["returncode"] = process.returncode
            require(process.returncode == 0, "frozen selected verifier failed: " + family)
            runtime_raw = (runtime_out / "runtime.json").read_bytes()
            runtime = json.loads(runtime_raw)
            require(runtime["complete"] is True and len(runtime["fresh_sessions"]) == 2, "selected runtime did not complete exactly twice")
            require(runtime["whole_sha256"] == fixed["artifacts"]["x"]["sha256"]
                    and runtime["native_sha256"] == fixed["artifacts"]["native/x"]["sha256"], "runtime artifact binding differs")
            require(runtime["helpers"] == {name: pins["control_inputs"][name]["sha256"]
                                            for name in ("engines/tests/verify.py", "engines/tests/chess_oracle.py")},
                    "runtime helper binding differs")
            require([session["termination"] for session in runtime["fresh_sessions"]] == ["quit", "EOF"], "runtime session scope differs")
            for session in runtime["fresh_sessions"]:
                require(session["returncode"] == 0 and session["process_absent"] is True
                        and session["readers_finished"] is True and session["exactly_one_closing_bestmove"] is True
                        and session["stderr"] == [] and session["image"]["image_sha256"] == fixed["artifacts"]["native/x"]["sha256"]
                        and len(session["image"]["startup_tids"]) == 3
                        and session["activity"]["cancellation_causality"] == "unproven", "selected physical exit/image proof differs")
            for name, pin in fixed["artifacts"].items():
                exact(destination, name, pin)
            row.update(status="selected_runtime_pass", runtime_sha256=sha(runtime_raw), fresh_sessions=2,
                       cancellation_causality="unproven")
            report["fresh_sessions"] += 2
            save()
        # Re-admit immutable original cost/owned inputs after the six sessions.
        admit(build)
        for relative, pin in pins["control_inputs"].items():
            exact(out / "control-inputs", relative, pin)
            exact(execution, relative, configured_outputs.get(relative, pin))
        report.update(complete=True, original_cost_and_owned_inputs_unchanged=True,
                      execution_recipe_inputs_unchanged_after_runtime=True)
        save()
        print(json.dumps({"complete": True, "out": str(out), "families": 3, "fresh_sessions": 6,
                          "results_sha256": sha((out / "results.json").read_bytes())}), flush=True)
    except BaseException as error:
        report["error"] = repr(error)
        save()
        raise


if __name__ == "__main__":
    main()
