"""Bounded B/F source reuse receipts and minimal-only modeled UCI checks.

The shared verifier owns actual selected-wrapper/DEV sessions. This helper runs
only the actual shipping dispatch with the admitted A harness's fixed clock and
synthetic worker completion. Those observations are explicitly nonphysical.
Historical algorithm proof reuse requires actual archived readable/core/DEV
byte equality; missing context/PLY receipts remain missing, never implied pass.
"""

import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys


_PINS = {
    "B": {"readable": "8130f0cde0c30679c84e6ec8c5bb6967e9d9b8ed19223c3856a05126cee4fa7c",
          "source": "14b8da672881a480d85dd7a5ea3c3f746ba48b55236f2e579c17c400ff7b65c8",
          "wrapper": "58ade8a95d80e89d84bf0f638844aa8befb45feae292b20ae0839abe34e79cb6",
          "native": "95d2e80ef1675f669a2c81860de3768271e5118b5d0d5771e7af787777f59362",
          "protected": "9519c9465fa29f04fa14fe42b557c3eb6868a6e0bb3d51af4a4dad310c7198bf"},
    "F": {"readable": "ccc7a4b232cebdad7f00c5fe6b0dbff718b51c895db0c9996467679841af59a3",
          "source": "1c1ef488085da1022357ca1ae1ddd29c53039c3dc5557653f714c8d291117709",
          "wrapper": "5b61c8cc14a21de3c8ac446439d4d90ebb8ea909e9e3d3d0161c692fb2ab6082",
          "native": "71b9b39ceb59024fce3fdc87b1a4c22d38af5ef88e89a5f841e96e4ca8ecdb4b",
          "protected": "6f9570b01a84bf873f7113f88acef43cfad37ba190946c003ffe6e205ed4b4d4"},
}
_TRANSFORM_SHA256 = "1f6782447ae303784278a198f3e846400d8481f2199d658cb6f8551be4a3d220"
_A_VERIFIER = Path("/home/stemxstudio/rove4k-tiny-uci-min-verify-20261020/recipe/verify.py")
_A_VERIFIER_SHA256 = "1e95b0a4e40c0584ca772b7545b73fcf758a0a82828f8dc9ba724ab812be0ddb"
_B_CORE = Path("/home/stemxstudio/rove4k-tiny-b-contract-v7/results.json")
_B_CORE_SHA256 = "4b898ac93399e9d6ee5e4525078efed9669818b5f4c1586edf5d88d7e905e800"
_F_CORE = Path("/home/stemxstudio/rove4k-tiny-f-final-proof-v3-20261020/results.json")
_F_CORE_SHA256 = "62b04e0c5eddaf6d1adcf25b18315dfad43437d20efb6fd0d06b37cde600e173"

_B_CONTEXT = r'''
#define main original_protocol_main
#include "engine.c"
#undef main
#include <assert.h>
static void proof_reset(void){
    clear();memset(workers,0,sizeof workers);start(&position);
    game_length=1;game_keys[0]=position.h;deadline=UINT64_MAX;limit=0;
    atomic_store(&searched,0);atomic_store(&stopped,0);
}
static void proof_position(const char *s,int depth){
    assert(fen(&position,s));game_keys[0]=position.h;game_length=1;
    workers[0].best=0;max_depth=depth;atomic_store(&stopped,0);think(workers,&position);
}
int main(void){
    table=calloc((size_t)1<<TT_BITS,sizeof *table);assert(table);proof_reset();
#if PLY==4
    max_depth=2;think(workers,&position);
    assert(atomic_load(&stopped)&&workers[0].depth==1&&workers[0].best&&workers[0].ply_aborts>0);
    Board child;assert(make(&position,workers[0].best,&child));
    printf("{\"passed\":true,\"completed_depth\":%d,\"ply_aborts\":%llu,\"legal_witness\":true}\n",
           workers[0].depth,(unsigned long long)workers[0].ply_aborts);
#else
    proof_position("7k/8/8/8/8/8/1Q6/K7 w - - 99 1",3);
    assert(!atomic_load(&stopped)&&workers[0].depth==3);int first_score=workers[0].score;
    uint64_t board_key=position.h,tt_key=position.h^mix(position.r+(unsigned)position.half);
    /* No TT clear between the two halfmove contexts. */
    proof_position("7k/8/8/8/8/8/1Q6/K7 w - - 0 1",3);
    assert(!atomic_load(&stopped)&&workers[0].depth==3&&position.h==board_key);
    assert((position.h^mix(position.r+(unsigned)position.half))!=tt_key);
    int second_score=workers[0].score;assert(first_score==0&&second_score>0);
    uint64_t before=workers[0].corr_updates;
    proof_position("6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 1",1);
    assert(!atomic_load(&stopped)&&workers[0].depth==1);
    Move expected=parse(&position,"e5d6");assert(expected&&workers[0].best==expected);
    assert(workers[0].corr_updates==before);
    printf("{\"passed\":true,\"retained_TT_halfmove_scores\":[%d,%d],\"board_key_equal\":true,\"TT_context_key_distinct\":true,\"ep_move\":\"e5d6\",\"correction_updates_before\":%llu,\"correction_updates_after\":%llu}\n",
           first_score,second_score,(unsigned long long)before,(unsigned long long)workers[0].corr_updates);
#endif
    free(table);return 0;
}
'''


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _require(value, message):
    if not value:
        raise ValueError(message)


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def verify(family, family_build, out):
    """Verify one cost-build ``build.json``; preserve all proof output outside Git."""
    _require(family in _PINS, "only B/F are owned by this proof helper")
    family_build, out = Path(family_build).resolve(), Path(out)
    _require(out.is_absolute(), "absolute proof output required")
    out = out.resolve()
    _require(not out.exists() and not any((p / ".git").exists() for p in (out, *out.parents)),
             "new proof output outside Git required")
    out.mkdir(parents=True)
    frozen = out / "frozen"
    frozen.mkdir()
    report = {"complete": False, "family": family, "scope": "source-bound historical algorithm reuse and minimal-only modeled UCI policy",
              "actual_wrapper_sessions": 0, "physical_completion_claim": False,
              "shared_checker_modified": False, "inputs": {}}

    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    def freeze(name, data):
        relative = PurePosixPath(name)
        _require(not relative.is_absolute() and ".." not in relative.parts and "\\" not in name, "unsafe proof input name")
        target = frozen.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        report["inputs"][name] = _sha(data)
        return data

    def pinned(name, path, expected):
        data = Path(path).read_bytes()
        _require(_sha(data) == expected, "proof input drift: " + str(path))
        return freeze(name, data)

    save()
    try:
        raw_build = freeze("family-build.json", family_build.read_bytes())
        build = json.loads(raw_build)
        _require(build["complete"] and build["family"] == family, "incomplete or different family build")
        records = {entry["id"]: entry for entry in build["engines"]}
        _require(set(records) == {"baseline", "minimal"} and len(build["engines"]) == 2, "unexpected cost forms")
        source_recipe = family_build.parent.parent / "recipe"
        transform_data = pinned("transform.py", source_recipe / "transform.py", _TRANSFORM_SHA256)
        _require(build["tooling_sha256"]["transform.py"] == _sha(transform_data), "cost build transform provenance differs")
        transform = _module("tiny_uci_bf_proof_transform_" + family, frozen / "transform.py")
        archived, dev_sources, dev_images = {}, {}, {}
        for name, entry in records.items():
            readable = pinned(name + "/combined.c", entry["readable"], entry["readable_sha256"])
            archived[name] = readable
            for key, path in (("source", entry["source"]), ("native", entry["native"]), ("whole", entry["command"][0])):
                pinned(name + "/" + key, path, entry[key + "_sha256"])
            dev_sources[name] = pinned(name + "/dev.c", Path(entry["dev"]).parent / "main.c", entry["dev_source_sha256"])
            dev_images[name] = pinned(name + "/dev.elf", entry["dev"], entry["dev_native_sha256"])
        _require(_sha(archived["baseline"]) == _PINS[family]["readable"], "unqualified baseline readable")
        for key, field in (("source", "source_sha256"), ("wrapper", "whole_sha256"), ("native", "native_sha256")):
            _require(records["baseline"][field] == _PINS[family][key], "unqualified baseline identity class: " + key)
        transformed, policy = transform.transform(archived["baseline"], family)
        _require(transformed == archived["minimal"], "archived minimal differs from the one declared policy")
        protected = transform.protected_bytes(archived["baseline"])
        _require(protected == transform.protected_bytes(archived["minimal"]) and
                 _sha(protected) == _PINS[family]["protected"] == build["policy"]["protected_sha256"],
                 "actual non-go/main core/global bytes changed")
        _require(dev_sources["baseline"] == dev_sources["minimal"] and dev_images["baseline"] == dev_images["minimal"],
                 "actual DEV source/native changed")
        freeze("protected.c", protected)
        report["actual_source_binding"] = {"family_build_sha256": _sha(raw_build),
            "baseline_readable_sha256": _sha(archived["baseline"]), "minimal_readable_sha256": _sha(archived["minimal"]),
            "protected_bytes": len(protected), "protected_sha256": _sha(protected),
            "all_actual_bytes_outside_go_main_identical": True,
            "actual_DEV_source_sha256": _sha(dev_sources["minimal"]),
            "actual_DEV_native_sha256": _sha(dev_images["minimal"]), "DEV_source_native_identical": True}

        if family == "B":
            raw_receipt = pinned("algorithm/B-contract.json", _B_CORE, _B_CORE_SHA256)
            receipt = json.loads(raw_receipt)
            _require(receipt["passed"] and receipt["source_sha256"] == _PINS[family]["readable"] and
                     {item["id"] for item in receipt["forms"]} == {"optimized", "asan"} and
                     all(item["returncode"] == 0 for item in receipt["forms"]), "B actual-core receipt is incomplete or belongs elsewhere")
            contract_path = source_recipe / "family-B/source-recipe/engines/compact/tiny-b/contract.c"
            contract = pinned("algorithm/B-contract-tail.c", contract_path, receipt["contract_sha256"])
            actual_unit = (_B_CORE.parent / "contract.c").read_bytes()
            _require(actual_unit == b"#define main tiny_b_protocol_main\n" + archived["baseline"] + b"\n#undef main\n" + contract,
                     "B contract unit did not contain the admitted actual readable source")
            freeze("algorithm/B-compiled-unit.c", actual_unit)
            report["historical_algorithm_reuse"] = {"receipt_sha256": _sha(raw_receipt),
                "receipt_path": str(_B_CORE), "actual_compiled_unit_sha256": _sha(actual_unit),
                "scope": "incremental bitboards/shared attackers, exact SEE complete/incomplete controls, singular positive/negative probes and learning suppression",
                "optimized_and_sanitized_passed": True,
                "reuse_basis": "receipt binds the exact baseline readable; every byte outside go/main and the actual DEV source/native are unchanged",
                "not_reused": ["old shipping stop/newgame/infinite lifecycle policy", "performance", "playing strength", "many-core scaling"],
                "missing": ["separate B retained-TT halfmove/EP context receipt", "separate B PLY=4 retained-witness receipt"]}
        else:
            raw_receipt = pinned("algorithm/F-qualification.json", _F_CORE, _F_CORE_SHA256)
            receipt = json.loads(raw_receipt)
            _require(receipt["passed"] and receipt["dev_source_sha256"] == _PINS[family]["readable"] and
                     {item["label"] for item in receipt["contracts"]} == {"optimized", "sanitized", "ply-cap"} and
                     all(item["result"]["passed"] for item in receipt["contracts"]), "F actual-core receipt is incomplete or belongs elsewhere")
            historical_readable = pinned("algorithm/F-original-dev.c", _F_CORE.parent / "frozen/dev/main.c", _PINS[family]["readable"])
            _require(historical_readable == archived["baseline"], "F contracts compiled a different readable core")
            for name, expected in receipt["test_inputs"].items():
                pinned("algorithm/F-test-inputs/" + name, _F_CORE.parent / "frozen" / name, expected)
            report["historical_algorithm_reuse"] = {"receipt_sha256": _sha(raw_receipt), "receipt_path": str(_F_CORE),
                "scope": "exact-horizon TT positive/negative/root/QS controls, ordering-only correction, coherent contention, retained-depth cancellation and 36 full-depth MTD(f) state cases",
                "contracts": receipt["contracts"], "PLY4_completed_legal_witness": next(item["result"] for item in receipt["contracts"] if item["label"] == "ply-cap"),
                "reuse_basis": "actual frozen contract DEV source equals baseline readable; every byte outside go/main and actual DEV source/native are unchanged",
                "not_reused": ["old shipping stop/newgame/infinite lifecycle policy", "performance", "playing strength", "many-core scaling"],
                "missing": []}

        pinned("A-policy-verifier.py", _A_VERIFIER, _A_VERIFIER_SHA256)
        harness_module = _module("tiny_uci_bf_actual_harness_" + family, frozen / "A-policy-verifier.py")
        units = out / "units"
        units.mkdir()
        (units / "engine.c").write_bytes(archived["minimal"])
        (units / "harness.c").write_text(harness_module.HARNESS)
        compile_command = ["cc", "-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18", "-DDEV=0", "harness.c", "-o", "harness"]
        report["instrumented"] = {"source_sha256": _sha(archived["minimal"]),
            "harness_sha256": _sha(harness_module.HARNESS.encode()),
            "scope": "actual minimal go/main/wait/clear with no-thread completion and fixed-clock environmental stubs",
            "physical_completion_claim": False, "cases": []}
        report["instrumented"]["compile"] = harness_module.bounded(compile_command, units, timeout=90)
        report["instrumented"]["program_sha256"] = _sha((units / "harness").read_bytes())
        for scenario in ("ignored", "position", "quit", "eof"):
            case = harness_module.bounded([str(units / "harness"), "1", scenario], units, timeout=5)
            case["observation"] = json.loads(case["stderr"])
            if scenario == "ignored":
                _require(case["stdout"] == "uciok\nreadyok\n", "minimal shipping output differs")
            report["instrumented"]["cases"].append(case)
        cases = [("", 1000, False), ("infinite", 1000, False),
                 ("wtime 0 btime 9223372036854775807", 1, False),
                 ("wtime 3000 winc 1000", 600, False),
                 ("wtime 400000000 winc 86400000", 78133333, False),
                 ("wtime 400000000 winc 9223372036854775807", 78133333, False),
                 ("wtime 648000000 winc 86400000", 86400000, False),
                 ("wtime 9223372036854775807 winc 0", 86400000, False),
                 ("btime 0", 1000, False),
                 ("wtime 9223372036854775807 btime 0 winc 999", 1, True),
                 ("btime 3000 binc 20 winc 999", 115, True)]
        for fields, budget, black in cases:
            case = harness_module.bounded([str(units / "harness"), "1", "budget", fields,
                                          str(harness_module.T0 + budget), str(int(black))], units, timeout=5)
            case["expected_budget_ms"] = budget
            case["observation"] = json.loads(case["stderr"])
            report["instrumented"]["cases"].append(case)
        _require(len(report["instrumented"]["cases"]) == 15, "bounded case inventory changed")
        report["modeled_policy_checks_passed"] = True
        if family == "B":
            core = out / "B-context-PLY"
            core.mkdir()
            (core / "engine.c").write_bytes(archived["minimal"])
            (core / "fixture.c").write_text(_B_CONTEXT)
            results = []
            for label, ply in (("context-EP", 128), ("PLY4", 4)):
                command = ["cc", "-std=c11", "-O2", "-pthread", "-DWORKERS=2", "-DTT_BITS=18", "-DDEV=1",
                           "-DPLY=" + str(ply), "fixture.c", "-o", label]
                compiled = harness_module.bounded(command, core, timeout=90)
                result = harness_module.bounded([str(core / label)], core, timeout=15)
                observation = json.loads(result["stdout"])
                _require(observation["passed"], "B fresh context/PLY observation failed")
                results.append({"id": label, "compile": compiled, "program_sha256": _sha((core / label).read_bytes()),
                                "execution": result, "observation": observation})
            report["fresh_B_context_PLY"] = {"source_sha256": _sha(archived["minimal"]),
                "fixture_sha256": _sha(_B_CONTEXT.encode()), "scope": "actual selected readable DEV core; optimized retained-TT halfmove/EP eligibility and PLY4 legal-witness abortion",
                "new_runtime_dispatch_claim": False, "cases": results}
            report["historical_algorithm_reuse"]["missing"] = []
        report["remaining_algorithm_evidence"] = report["historical_algorithm_reuse"]["missing"]
        report["complete"] = not report["remaining_algorithm_evidence"]
        save()
        return report
    except Exception as error:
        report["failure"] = repr(error)
        save()
        raise
