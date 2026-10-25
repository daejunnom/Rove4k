#!/usr/bin/env python3
"""Compare actual profile-emitted move generation with the independent oracle.

The included production source has only its entry name changed. The fixture
calls its real start/generate/make functions; it never calls the original main
or allocates/initializes a TT. This is a rules-consumer proof, not a startup,
resource, protocol, search-strength or complete chess-acceptance claim.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORACLE = "engines/tests/chess_oracle.py"
ORACLE_SHA = "aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8"
HOST = "engines/experiments/tcec-scope/build.py"
HOST_SHA = "fc916e798952cff1c915a6846e758874bc2d858b3c59dec73870b95c7e3d4828"
SCHEMA = "rove4k.production-generated-rules.v1"
SPELLING = "engines/experiments/tcec-next/profile_spelling.py"
SPELLING_SCHEMA = "rove4k.selected-spelling-experiment.v1"
SPELLING_PIN = {"bytes": 9921, "sha256": "7ec393bc9c805ee8e1e6d715f40cb9883f829e3c6b01e2f71f31701e35136ea8"}
BEST_SPELLING = {"A": "clock-type", "B": "atomic-assignment", "C": "clock-type",
                 "E": "clock-type", "F": "atomic-assignment"}

# These bindings refer to the complete baseline pins admitted by profile_source,
# not to guessed declarations in an arbitrary C file. Resource projection leaves
# these functions and Board/Move representations in the protected complement.
BINDINGS = {
    "A": dict(board="E", start="q", generate="T", make="v", four_args=False),
    "B": dict(board="za", start="k", generate="c", make="h", four_args=True),
    "C": dict(board="E", start="q", generate="T", make="v", four_args=False),
    "E": dict(board="E", start="q", generate="T", make="v", four_args=False),
    "F": dict(board="I", start="o", generate="T", make="h", four_args=True),
}


def pin(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def require(condition, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def normalized(path: Path) -> bytes:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named source")
    return data


def oracle_module():
    path = ROOT / ORACLE
    require(pin(normalized(path))["sha256"] == ORACLE_SHA,
            "independent oracle source differs")
    return load("production_rules_oracle", path)


def fixture_cases(oracle=None) -> tuple[list[dict], dict]:
    """Reach every test position by a legal prefix from the standard start."""
    oracle = oracle or oracle_module()
    cases, seen = [], set()

    def add(label, sequence, *, prefixes=True):
        moves = sequence.split() if isinstance(sequence, str) else list(sequence)
        limits = range(len(moves) + 1) if prefixes else (len(moves),)
        for length in limits:
            path = tuple(moves[:length])
            if path in seen:
                continue
            board = oracle.Board.from_fen()
            for move in path:
                board = board.play(move)
            legal = sorted(str(move) for move in board.legal_moves())
            cases.append({"label": label + "-" + str(length), "moves": list(path),
                          "legal": legal, "board": board})
            seen.add(path)

    add("open", "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6")
    add("castle-kingside", "e2e4 e7e5 g1f3 b8c6 f1c4 g8f6 e1g1 f8c5 d2d3 e8g8")
    add("castle-queenside", "d2d4 d7d5 b1c3 b8c6 c1f4 c8f5 d1d2 d8d7 e1c1 e8c8")
    add("white-ep", "e2e4 a7a6 e4e5 d7d5 e5d6")
    add("black-ep", "a2a3 e7e5 a3a4 e5e4 d2d4 e4d3")
    add("absolute-pin", "e2e4 e7e5 b1c3 f8b4 d2d3 a7a6")
    add("mate", "f2f3 e7e5 g2g4 d8h4")
    promotion = "e2e4 b8c6 g1f3 g8f6 f1d3 e7e6 a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 a6b7 h3g2".split()
    add("promotion-corridor", promotion)
    for white in "nbrq":
        for target in ("a8", "b8", "c8"):
            white_move = "b7" + target + white
            add("white-" + target + white, promotion + [white_move], prefixes=False)
            # Every black promotion is generated in the position after White's
            # quiet promotion. Replay both the quiet and capture branches too.
            if target == "b8":
                for black in "nbrq":
                    for black_target in ("g1", "h1"):
                        add("black-" + black_target + black,
                            promotion + [white_move, "g2" + black_target + black],
                            prefixes=False)

    promotions = {color + "_" + kind: set()
                  for color in ("white", "black") for kind in ("quiet", "capture")}
    castles, ep, pin_cases, mate_cases = set(), set(), [], []
    for case in cases:
        board = case["board"]
        for move in board.legal_moves():
            text = str(move)
            if move.promotion:
                kind = "capture" if board.cells[move.dst] != "." else "quiet"
                promotions[("white" if board.turn else "black") + "_" + kind].add(move.promotion)
            if text in ("e1g1", "e1c1", "e8g8", "e8c8"):
                castles.add(text)
            if (board.cells[move.src].lower() == "p" and board.cells[move.dst] == "."
                    and move.src % 8 != move.dst % 8):
                ep.add(text)
        if case["label"] == "absolute-pin-6":
            require(not any(move.startswith("c3") for move in case["legal"]),
                    "absolute-pin fixture does not pin its knight to the king")
            pin_cases.append(case["label"])
        if case["label"] == "mate-4":
            require(not case["legal"] and board.in_check(board.turn),
                    "mate fixture is not a discriminating checkmate")
            mate_cases.append(case["label"])
    require(all(values == set("nbrq") for values in promotions.values()),
            "fixtures must generate both colours' quiet/capture NBRQ")
    require(castles == {"e1g1", "e1c1", "e8g8", "e8c8"} and
            {"e5d6", "e4d3"} <= ep and pin_cases and mate_cases,
            "special-move fixture coverage is incomplete")
    coverage = {**{name: sorted(values) for name, values in promotions.items()},
                "castles": sorted(castles), "en_passant": sorted(ep),
                "absolute_pin_cases": pin_cases, "checkmate_cases": mate_cases}
    return cases, coverage


def _source_build_record(build, *, family, stages, post_profile, main_source,
                         baseline_source, tools=(), post_spelling=None):
    require(build is not None, "named post-profile/model source build root required")
    build = Path(build)
    record = json.loads(_evidence_bytes(build / "build.json", name="build.json"))
    require(record.get("format") == 1 and record.get("class") == "rove4k-production-profile-v1" and
            record.get("family") == family and record.get("entry") == family and
            record.get("complete") is True and record.get("reproducible") is True and
            record.get("post_profile") == post_profile and record.get("post_spelling") == post_spelling and
            record.get("source_proofs") == stages and
            _evidence_bytes(build / "main.c", name="main.c") == main_source and
            _evidence_bytes(build / "control/main.c", name="main.c") == baseline_source,
            family + " named frozen producer source/stages/post-profile identity differs")
    for relative in tools:
        frozen = _evidence_bytes(build / "inputs" / relative, name=Path(relative).name)
        expected = pin(frozen)
        rows = [row for row in record.get("source_closure", {}).get("inputs", [])
                if row.get("path") == relative]
        require(record.get("inputs", {}).get(relative) == expected and len(rows) == 1 and
                rows[0].get("role") == "tool" and
                {key: rows[0].get(key) for key in expected} == expected,
                family + " frozen named post-profile/model tool identity differs")
        if relative == SPELLING:
            require(expected == SPELLING_PIN and pin(normalized(ROOT / relative)) == SPELLING_PIN,
                    "reviewed final spelling helper identity differs")
    if post_spelling is not None:
        plan = record.get("plan", {})
        require(plan.get("family") == family and plan.get("full") is True and
                plan.get("representation") == "source-jit" and
                plan.get("entry_cleanup") == "private-path",
                "final spelling requires full source-JIT/private-path producer plan")
    return record


def admit_source(main_source: bytes, baseline_source: bytes, baseline_proof: dict,
                 family: str, profile, *, build=None):
    require(family in BINDINGS, "explicit A/B/C/E/F production family required")
    projection = load("production_rules_projection", HERE / "profile_source.py")
    stages = baseline_proof if isinstance(baseline_proof, list) else [baseline_proof]
    if isinstance(baseline_proof, list):
        candidates = [proof for proof in stages
                      if isinstance(proof, dict) and proof.get("schema") == projection.SCHEMA]
        require(len(candidates) == 1, "one explicit resource projection proof required")
        baseline_proof = candidates[0]
    require(isinstance(baseline_proof, dict), "resource projection proof must be a mapping")
    cleanup = baseline_proof.get("entry_cleanup")
    expected, resource = projection.transform_source(baseline_source, family=family,
                                                     profile=profile, entry_cleanup=cleanup)
    require(baseline_proof == resource,
            "actual profile resource proof/inverse does not replay from its admitted full baseline")
    b_schema, phase_schema = "rove4k.profile-b-source.v1", "rove4k.portable-phase-source.v1"
    suffix = stages[1:] if stages and stages[0] == resource else None
    require(suffix is not None and all(isinstance(stage, dict) for stage in suffix),
            "ordered resource-first proof chain required")
    has_spelling = bool(suffix) and suffix[-1].get("schema") == SPELLING_SCHEMA
    spelling_stage = suffix[-1] if has_spelling else None
    if has_spelling:
        suffix = suffix[:-1]
    has_b = bool(suffix) and suffix[0].get("schema") == b_schema
    has_phase = bool(suffix) and suffix[0].get("schema") == phase_schema
    model_stage = bool(suffix) and suffix[-1].get("stage") == "canonical-e19-physical-binding"
    if family == "B":
        require(not suffix or (len(suffix) == 1 and has_b),
                "explicit B proof chain must be resource-only or ordered resource/B")
    elif family == "E":
        require(model_stage and (len(suffix) == 1 or (len(suffix) == 2 and has_phase)),
                "explicit E proof chain must be resource/model or resource/phase/model")
    else:
        require(not suffix or (len(suffix) == 1 and has_phase),
                "explicit A/C/F proof chain must be resource-only or ordered resource/phase")
    post_profile, post_spelling, tools = None, None, []
    if has_b:
        relative = "engines/experiments/tcec-next/profile_b.py"
        post_profile = {"path": relative, "variant": suffix[0].get("variant")}
        tools.append(relative)
    if has_phase:
        require(family in "ACEF" and suffix[0].get("variant") == "phase-init",
                "explicit reviewed ACEF phase-init variant required")
        relative = "engines/experiments/tcec-next/profile_phase.py"
        post_profile = {"path": relative, "variant": "phase-init"}
        tools.append(relative)
    if model_stage:
        tools.extend(("engines/model/e19.py", "engines/model/e19.json"))
    if has_spelling:
        variant = BEST_SPELLING[family]
        require(cleanup == "private-path" and spelling_stage.get("variant") == variant and
                ((has_b and suffix[0].get("variant") == "tcec-final-lf") or
                 (family in "ACEF" and has_phase)),
                "final spelling requires selected phase-init ACEF or tcec-final-lf B and its reviewed winner")
        post_spelling = {"path": SPELLING, "selection": "best", "variant": variant}
        tools.append(SPELLING)
    if not suffix and not has_spelling and build is not None:
        control = json.loads(_evidence_bytes(Path(build) / "build.json", name="build.json"))
        require(control.get("post_profile") is None and control.get("post_spelling") is None and
                control.get("source_proofs") == stages,
                family + " control build declares an unconsumed post-profile stage")
    if suffix or has_spelling:
        _source_build_record(build, family=family, stages=stages, post_profile=post_profile,
                             main_source=main_source, baseline_source=baseline_source, tools=tools,
                             post_spelling=post_spelling)
    replayed = [resource]
    inverses = [("resource", projection, resource, baseline_source)]
    if has_b:
        current = load("production_rules_B_projection", HERE / "profile_b.py")
        variant = suffix[0]["variant"]
        require(variant in current.VARIANTS, "explicit finite B profile variant required")
        projected, proof = current.transform_source(expected, profile_id=profile.id,
            entry_cleanup=cleanup, variant=variant)
        require(suffix[0] == proof,
                "B full post-profile proof/inverse differs")
        inverses.append(("B full post-profile", current, proof, expected))
        expected = projected
        replayed.append(proof)
    if has_phase:
        current = load("production_rules_phase_projection", HERE / "profile_phase.py")
        projected, proof = current.transform_source(expected, family=family, profile_id=profile.id,
            entry_cleanup=cleanup, variant="phase-init")
        require(suffix[0] == proof,
                "ACEF full phase-init proof/inverse differs")
        inverses.append(("ACEF full phase-init", current, proof, expected))
        expected = projected
        replayed.append(proof)
    if model_stage:
        current = load("production_rules_E19_model", ROOT / "engines/model/e19.py")
        model = current.Model.load(Path(build) / "inputs/engines/model/e19.json")
        # The first canonical control used the canonical ID for its source
        # model. Recover its values from the admitted source just as for fresh
        # inputs; this old spelling is allowed only for the unchanged control.
        old_model_id = (not has_phase and suffix[-1].get("source_model_id") ==
                        model.model_id == "e-hand-quadratic-19-1")
        source_id = model.model_id if old_model_id else "e19-admitted-source-baseline"
        source_model = current.Model.from_physical_source(expected, model_id=source_id)
        projected, proof = model.bind_physical_table(expected, source_model=source_model)
        offset, before, after = proof["table_value_offset"], proof["before"].encode(), proof["after"].encode()
        require(suffix[-1] == proof and projected[offset:offset + len(after)] == after,
                "E full canonical model binding proof/inverse differs")
        require(not old_model_id or (projected == expected and proof["model_parameters_changed"] is False),
                "old E source-model ID is limited to the byte-identical canonical control")
        inverses.append(("E full canonical model binding", None, proof, expected))
        expected = projected
        replayed.append(proof)
    if has_spelling:
        current = load("production_rules_spelling_projection", ROOT / SPELLING)
        projected, proof = current.transform_source(expected, family=family,
            profile_id=profile.id, variant=post_spelling["variant"])
        require(current.SCHEMA == SPELLING_SCHEMA and spelling_stage == proof,
                "full final spelling proof/protected gaps differ")
        inverses.append(("full final spelling", current, proof, expected))
        expected = projected
        replayed.append(proof)
    require(main_source == expected,
            "actual profile source/proof does not replay from its admitted full baseline")
    # Undo the actual complete shipping body in the opposite order. In
    # particular spelling must be restored before E19's table offsets apply.
    restored = main_source
    for label, module, proof, parent in reversed(inverses):
        if module is None:
            offset, before, after = proof["table_value_offset"], proof["before"].encode(), proof["after"].encode()
            require(restored[offset:offset + len(after)] == after, label + " inverse span differs")
            restored = restored[:offset] + before + restored[offset + len(after):]
        else:
            restored = module.restore_source(restored, proof)
        require(restored == parent, label + " proof/inverse differs")
    require(b"rv_rule_" not in main_source, "rules fixture identifiers collide")
    return replayed if suffix or has_spelling else resource


def render_fixture(main_source: bytes, family: str, cases: list[dict]) -> bytes:
    return render_bound_fixture(main_source, BINDINGS[family], cases)


def render_bound_fixture(main_source: bytes, binding: dict, cases: list[dict],
                         extra_declarations: bytes = b"") -> bytes:
    """Render only; each caller must first admit its own family's source."""
    generate = binding["generate"] + "(p,rv_rule_raw"
    generate += ",0,p->s)" if binding["four_args"] else ")"
    paths = ",\n".join(json.dumps(" ".join(case["moves"]), ensure_ascii=True) for case in cases)
    driver = r'''
#undef main
static void rv_rule_text(unsigned m,char *s){
 unsigned f=m&119,t=(m>>7)&127,p=(m>>14)&7;
 s[0]='a'+(f&7);s[1]='1'+(f>>4);s[2]='a'+(t&7);s[3]='1'+(t>>4);
 if(p){if(p<2||p>5)abort();s[4]="xxnbrq"[p];s[5]=0;}else s[4]=0;
}
static int rv_rule_legal(const @BOARD@ *p,unsigned *out){
 unsigned rv_rule_raw[512];int n=@GENERATE@,k=0;
 if(n<0||n>512)abort();
 for(int i=0;i<n;i++){@BOARD@ child;if(@MAKE@(p,rv_rule_raw[i],&child))out[k++]=rv_rule_raw[i];}
 return k;
}
static void rv_rule_play(@BOARD@ *p,const char *move){
 unsigned moves[512];int n=rv_rule_legal(p,moves),found=0;@BOARD@ chosen;
 for(int i=0;i<n;i++){char text[6];rv_rule_text(moves[i],text);
  if(!strcmp(text,move)){if(!@MAKE@(p,moves[i],&chosen))abort();found++;}}
 if(found!=1)abort();*p=chosen;
}
int main(void){
 static const char *paths[]={@PATHS@};
 for(size_t row=0;row<sizeof(paths)/sizeof(*paths);row++){
  @BOARD@ board;@START@(&board);char line[4096];
  if(strlen(paths[row])>=sizeof line)abort();strcpy(line,paths[row]);
  char *save=0;for(char *move=strtok_r(line," ",&save);move;move=strtok_r(0," ",&save))rv_rule_play(&board,move);
  unsigned moves[512];int n=rv_rule_legal(&board,moves);printf("%zu",row);
  for(int i=0;i<n;i++){char text[6];rv_rule_text(moves[i],text);printf(" %s",text);}puts("");
 }
 return 0;
}
'''
    values = {"BOARD": binding["board"], "GENERATE": generate,
              "MAKE": binding["make"], "START": binding["start"], "PATHS": paths}
    for name, value in values.items():
        driver = driver.replace("@" + name + "@", value)
    require("@" not in driver, "unreplaced rules fixture binding")
    # No new system include precedes the source's feature-test macro.
    return (b"#define main rv_rule_original_main\n" + main_source +
            extra_declarations + driver.encode("ascii"))


def _compare_output(data: bytes, cases: list[dict]) -> dict:
    rows = data.decode("ascii").splitlines()
    require(len(rows) == len(cases), "rules probe output case count differs")
    total = 0
    for index, (line, case) in enumerate(zip(rows, cases)):
        fields = line.split()
        require(fields and fields[0] == str(index), "rules probe row identity differs")
        moves = fields[1:]
        require(len(moves) == len(set(moves)), "duplicate generated legal move: " + case["label"])
        require(sorted(moves) == case["legal"], "actual generated legal move set differs: " + case["label"])
        total += len(moves)
    return {"cases": len(cases), "legal_moves_compared": total,
            "stdout": pin(data), "legal_sets_equal": True}


def verify_generated_rules(main_source: bytes, baseline_proof: dict, family: str,
                           profile, *, baseline_source: bytes, out: Path,
                           run_command, compiler: str = "cc", build=None) -> dict:
    """Use a caller-owned bounded runner with signature (argv,cwd=,kind=)."""
    proof = admit_source(main_source, baseline_source, baseline_proof, family, profile, build=build)
    out = Path(out)
    require(out.is_absolute() and not out.exists() and
            not any((p / ".git").exists() for p in (out, *out.parents)),
            "new absolute rules output outside every checkout required")
    require(callable(run_command), "an owned bounded command runner is required")
    cases, coverage = fixture_cases()
    fixture = render_fixture(main_source, family, cases)
    out.mkdir(parents=True)
    (out / "fixture.c").write_bytes(fixture)
    (out / "cases.json").write_text(json.dumps(
        [{k: value for k, value in case.items() if k != "board"} for case in cases],
        indent=2) + "\n")
    report = {"format": SCHEMA, "family": family, "profile": profile.to_record(24),
              "source": pin(main_source), "baseline": pin(baseline_source),
              "source_proof": pin(json.dumps(proof, sort_keys=True).encode()),
              "fixture": pin(fixture), "oracle": {"path": ORACLE, "sha256": ORACLE_SHA},
              "verifier_inputs": {relative: pin(normalized(path)) for relative, path in (
                  ("engines/experiments/tcec-next/profile_rules.py", Path(__file__)),
                  ("engines/experiments/tcec-next/profile_source.py", HERE / "profile_source.py"),
                  ("engines/scripts/production.py", ROOT / "engines/scripts/production.py"))},
              "coverage": coverage, "complete": False, "modes": [],
              "scope": "actual emitted start/generate/make legal sets at standard-start-derived positions",
              "not_proven": ["exhaustive chess correctness", "startup and real parallel TT initialization",
                             "search, protocol, resource or tournament qualification", "playing strength"],
              "TT_allocated": False, "original_entry_called": False}
    if isinstance(proof, list):
        report["build"] = pin(_evidence_bytes(Path(build) / "build.json", name="build.json"))
    def save():
        (out / "rules.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    try:
        for mode, flags in (("plain", []), ("ubsan", ["-fsanitize=undefined", "-fno-sanitize-recover=all"])):
            program = out / ("probe-" + mode)
            command = [compiler, "-std=c11", "-O1", "-pthread", "-g0", *flags,
                       str(out / "fixture.c"), "-o", str(program)]
            run_command(command, cwd=out, kind="rules-compile-" + mode)
            observed = run_command([str(program)], cwd=out, kind="rules-execute-" + mode)
            report["modes"].append({"mode": mode, "native": pin(program.read_bytes()),
                                    **_compare_output(observed, cases)})
            save()
        report["complete"] = True
        return report
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        save()


def _evidence_bytes(path: Path, *, name: str | None = None) -> bytes:
    path = Path(path)
    require(path.is_absolute() and (name is None or path.name == name) and
            not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(),
            "explicit regular rules evidence file required")
    return path.read_bytes()


def _legacy_model_report(report, proof, family, main_source):
    """Metadata compatibility only, after full source/stage admission."""
    return bool(family == "E" and isinstance(proof, list) and len(proof) == 2 and
        "build" not in report and proof[1].get("stage") == "canonical-e19-physical-binding" and
        proof[1].get("model_parameters_changed") is False and proof[1].get("full_inverse") is True and
        proof[1].get("consumer_code_changed") is False and proof[1].get("change_kind") == "model-input-binding" and
        proof[1].get("source_sha256") == proof[1].get("result_sha256") == pin(main_source)["sha256"] and
        report.get("source_proof") == pin(json.dumps(proof[0], sort_keys=True).encode()))


def validate_rules_receipt(report_path: Path, *, family: str, profile,
                           main_source: bytes, source_proof, baseline_source=None,
                           build=None, commands_path=None, compiler="cc") -> dict:
    """Revalidate stored C probes and oracle output without launching a process.

    ABCEF requires the fresh producer's baseline bytes. D requires its build
    root so the fresh own-source derivation and stored preprocessor outputs can
    be checked. A changed verifier metadata hash is never retroactively stamped
    on an old report: current source, complete C fixture and cases must reproduce.
    The result is a rules-consumer receipt, not tournament qualification.
    """
    report_path = Path(report_path)
    report_bytes = _evidence_bytes(report_path, name="rules.json")
    report = json.loads(report_bytes)
    require(family in (*BINDINGS, "D") and report.get("family") == family and
            report.get("complete") is True and "failure" not in report and
            report.get("TT_allocated") is False,
            "completed matching-family TT-free rules evidence required")
    expected_schema = "rove4k.D-generated-rules.v1" if family == "D" else SCHEMA
    require(report.get("format") == expected_schema and
            report.get("profile") == profile.to_record(16 if family == "D" else 24) and
            report.get("oracle") == {"path": ORACLE, "sha256": ORACLE_SHA} and
            report.get("native_entry_called" if family == "D" else "original_entry_called") is False,
            "rules receipt resource/oracle/entry boundary differs")
    require(pin(normalized(ROOT / HOST))["sha256"] == HOST_SHA,
            "bounded rules command owner differs")
    probe = report_path.parent
    command_path = Path(commands_path) if commands_path is not None else probe.parent / "commands.json"
    command_bytes = _evidence_bytes(command_path, name="commands.json")
    commands = json.loads(command_bytes)
    require(commands.get("format") == expected_schema + ".commands" and
            commands.get("complete") is True and "failure" not in commands and
            commands.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
            "terminal owned rules commands and clean host closure required")
    prefix = "D-" if family == "D" else ""
    kinds = (["D-rules-preprocess-actual-single-TU", "D-rules-preprocess-actual-board"]
             if family == "D" else []) + [prefix + "rules-" + action + "-" + mode
                for mode in ("plain", "ubsan") for action in ("compile", "execute")]
    rows = commands.get("commands")
    require(isinstance(rows, list) and [row.get("kind") for row in rows] == kinds,
            "exact complete rules command sequence required")
    outputs = {}
    for index, row in enumerate(rows, 1):
        require(row.get("started") is True and row.get("terminal") is True and
                row.get("reaped") is True and row.get("owned_group_absent") is True and
                row.get("original_identity_retained_until_other_members_absent") is True and
                row.get("forced_cleanup") is False and
                row.get("other_group_members_before_reap") == [] and
                type(row.get("returncode")) is int and row["returncode"] == 0 and
                type(row.get("pid")) is int and row["pid"] > 0 and row.get("pgid") == row["pid"] and
                row.get("child_limits") == {"AS": 2147483648, "CPU": 40} and
                0 <= row.get("elapsed_diagnostic_seconds", -1) <= 45 and
                row.get("cwd") == str(probe),
                "rules process identity, bounds, terminal state or group cleanup differs")
        for stream in ("stdout", "stderr"):
            expected_path = command_path.parent / ("tool-" + str(index) + "-" + row["kind"] + "." + stream)
            observed = row.get(stream, {})
            require(observed.get("path") == str(expected_path), "unexpected rules output path")
            data = _evidence_bytes(expected_path)
            require(pin(data) == {key: observed.get(key) for key in ("bytes", "sha256")},
                    "rules command stream identity differs")
            if stream == "stdout":
                outputs[row["kind"]] = data
            else:
                require(data == b"", "rules compiler/probe diagnostics must be empty")
    cases, coverage = fixture_cases()
    require(report.get("coverage") == coverage, "rules coverage differs from the independent fixture")
    expected_cases = [{key: value for key, value in case.items() if key != "board"} for case in cases]
    case_bytes = _evidence_bytes(probe / "cases.json", name="cases.json")
    require(json.loads(case_bytes) == expected_cases, "stored rule cases differ")
    if family == "D":
        require(build is not None, "D source-owned build root required")
        driver = load("production_D_rules_receipt", ROOT / "engines/experiments/tiny-d-submission/profile_rules.py")
        fixture = driver.receipt_fixture(report, profile=profile, main_source=main_source,
            source_proof=source_proof, build=Path(build), cases=cases, commands=rows, outputs=outputs,
            probe=probe, compiler=compiler)
    else:
        require(isinstance(baseline_source, bytes), "fresh producer baseline bytes required")
        proof = admit_source(main_source, baseline_source, source_proof, family, profile, build=build)
        full_pin = pin(json.dumps(proof, sort_keys=True).encode())
        # Historical E controls recorded P0 only. Accept that exact old pin
        # solely after the complete current/frozen E-model chain above replayed
        # and proved a byte-identical binding. Fresh reports always bind all stages.
        legacy_model = _legacy_model_report(report, proof, family, main_source)
        require(report.get("source") == pin(main_source) and
                report.get("baseline") == pin(baseline_source) and
                (report.get("source_proof") == full_pin or legacy_model),
                "rules source, baseline or full resource proof identity differs")
        if isinstance(proof, list) and not legacy_model:
            require(report.get("build") == pin(_evidence_bytes(Path(build) / "build.json", name="build.json")),
                    "post-profile/model rules receipt build identity differs")
        fixture = render_fixture(main_source, family, cases)
    require(report.get("fixture") == pin(fixture) and
            _evidence_bytes(probe / "fixture.c", name="fixture.c") == fixture,
            "actual rules fixture does not match the current renderer and source")
    modes = report.get("modes")
    require(isinstance(modes, list) and [mode.get("mode") for mode in modes] == ["plain", "ubsan"],
            "both ordinary and UBSan actual-source rules probes required")
    for mode in modes:
        name = mode["mode"]
        native = probe / ("probe-" + name)
        require(mode.get("native") == pin(_evidence_bytes(native)), "actual rules probe binary differs")
        sanitizers = [] if name == "plain" else ["-fsanitize=undefined", "-fno-sanitize-recover=all"]
        if family == "D":
            flags = ["-std=c11", "-O1", "-g0", "-fno-builtin", "-msse4.2", "-mcx16"]
        else:
            flags = ["-std=c11", "-O1", "-pthread", "-g0"]
        compile_row = rows[kinds.index(prefix + "rules-compile-" + name)]
        execute_row = rows[kinds.index(prefix + "rules-execute-" + name)]
        require(compile_row.get("command") == [compiler, *flags, *sanitizers, str(probe / "fixture.c"), "-o", str(native)] and
                execute_row.get("command") == [str(native)], "actual rules compiler/executable command differs")
        comparison = _compare_output(outputs[prefix + "rules-execute-" + name], cases)
        require(comparison == {key: mode.get(key) for key in comparison} and
                comparison["cases"] == 105 and comparison["legal_moves_compared"] == 2858,
                "actual oracle/output counts or legal sets differ")
    return {"nbrq_generation": True, "family": family, "cases": len(cases),
            "legal_moves_compared": modes[0]["legal_moves_compared"], "modes": ["plain", "ubsan"],
            "coverage": coverage, "runtime_qualified": False,
            "scope": report["scope"], "current_renderer_matches": True,
            "evidence": {"rules_report": {"path": str(report_path), **pin(report_bytes)},
                         "commands": {"path": str(command_path), **pin(command_bytes)},
                         "source": pin(main_source), "fixture": pin(fixture), "cases": pin(case_bytes),
                         "oracle": {"path": ORACLE, "sha256": ORACLE_SHA},
                         "probes": {mode["mode"]: mode["native"] for mode in modes},
                         "stdout": modes[0]["stdout"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--family", choices=tuple(BINDINGS), required=True)
    parser.add_argument("--profile", choices=("test-p4", "test-p28", "tcec-provisional"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--build", type=Path, help="named post-profile/model frozen source artifact root")
    args = parser.parse_args()
    require(sys.platform == "linux", "Linux bounded rules fixture host required")
    for path, names in ((args.source, ("main.c",)), (args.baseline, ("main.c",)),
                        (args.proof, ("source-proof.json", "proof.json"))):
        require(path.name in names and path.is_absolute(), "explicit named source/proof file required")
        require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(),
                "rules fixture inputs must not follow filesystem links")
    production = load("production_rules_contract", ROOT / "engines/scripts/production.py")
    profile = production.resource_profile(args.profile)
    source, baseline = args.source.read_bytes(), args.baseline.read_bytes()
    proof = json.loads(args.proof.read_text())
    admit_source(source, baseline, proof, args.family, profile, build=args.build)
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and
            not any((p / ".git").exists() for p in (out, *out.parents)),
            "new absolute output outside every checkout required")
    host_path = ROOT / HOST
    require(pin(normalized(host_path))["sha256"] == HOST_SHA, "bounded command owner differs")
    owner = load("production_rules_command_owner", host_path)
    owner.LIMITS = {**owner.LIMITS, "aggregate_wall": 180, "per_command_wall": 45,
                    "parent_CPU": 100, "parent_CPU_hard": 120, "child_CPU": 40}
    out.mkdir()
    record = {"format": SCHEMA + ".commands", "complete": False, "commands": []}
    def save():
        (out / "commands.json").write_text(json.dumps(record, indent=2) + "\n")
    save()
    host = owner.Host(out, record, save)
    try:
        result = verify_generated_rules(source, proof, args.family, profile,
            baseline_source=baseline, out=out / "probe", run_command=host.run, compiler=args.cc, build=args.build)
        record["complete"] = result["complete"]
    except BaseException as error:
        record["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        host.close()
        save()
    print(json.dumps({"complete": True, "family": args.family,
                      "cases": result["modes"][0]["cases"], "coverage": result["coverage"]}), flush=True)


if __name__ == "__main__":
    main()
