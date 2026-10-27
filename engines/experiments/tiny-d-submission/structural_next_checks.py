"""Bounded hosted observations for measured BSS D structural candidates.

This consumes actual source/native/package identities from structural_next's
portfolio.  It observes source semantics with the existing independent board
oracle and actual-search fixture.  It does not issue production admission,
execute the packaged raw-clone runtime, or qualify resources/strength.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MAX_CASES = 12


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read(path, maximum=16 << 20):
    path = Path(path)
    if (not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents))
            or not path.is_file() or path.stat().st_size > maximum):
        raise ValueError("bounded regular absolute observation input required: " + str(path))
    return path.read_bytes()


def case_name(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("simple measured case name required")
    return name


def select_cases(portfolio):
    """Baseline first; each improved source cohort once, smallest first."""
    rows = portfolio.get("cases", [])
    by_name = {case_name(row["name"]): row for row in rows}
    if len(by_name) != len(rows) or "baseline" not in by_name:
        raise ValueError("unique measured baseline/case names required")
    baseline = by_name["baseline"]
    ordered = sorted(rows, key=lambda row: (row["package"]["bytes"], row["name"]))
    chosen, seen, reused, omitted = [baseline], {json.dumps(baseline["source"], sort_keys=True): "baseline"}, [], []
    for row in ordered:
        if row["name"] == "baseline" or row["package"]["bytes"] >= baseline["package"]["bytes"]:
            continue
        identity = json.dumps(row["source"], sort_keys=True)
        if identity in seen:
            reused.append({"name": row["name"], "same_source_as": seen[identity],
                           "scope": "source semantics only; compiler/native/runtime not reused"})
        elif len(chosen) < MAX_CASES:
            chosen.append(row)
            seen[identity] = row["name"]
        else:
            omitted.append({"name": row["name"], "reason": "finite source observation case budget"})
    return chosen, reused, omitted


def board_prefix(case, cost, modules, host):
    """Reproduce the complete board prefix of the actual reduced shipping TU."""
    raw = case / "generated-readable"
    cpp = host.run(["cc", "-E", "-P", *cost["flags"], str(raw / "board.c")],
                   cwd=raw, kind=case.name + "-actual-board-cpp")
    board = modules["minifier"].compact_source(cpp, "c").rstrip(b"\n")
    names = dict(modules["probe_d_square_successor"].LEGACY)
    for before, after in names.items():
        board = modules["lexical"]._replace({"main.c": board}, before, after)["main.c"]
    for stage in cost["reduction"]["stages"]:
        if stage["status"] != "accepted":
            continue
        if stage["kind"] == "unused-scalar-typedefs":
            for edits in stage["rounds"]:
                pieces, cursor = [], 0
                for edit in edits.get("main.c", {}).get("removed", []):
                    first, last = edit["begin"], edit["end"]
                    if first >= len(board):
                        continue
                    if first < cursor or last > len(board) or board[first:last] != edit["declaration"].encode():
                        raise ValueError("actual board typedef reduction differs")
                    pieces.append(board[cursor:first])
                    cursor = last
                pieces.append(board[cursor:])
                board = b"".join(pieces)
        elif stage["kind"] == "batch-alpha":
            mapping, text, pieces, cursor = stage["renames"], board.decode(), [], 0
            for first, last, token in modules["lexical"]._identifier_spans(text):
                if token in mapping:
                    pieces.extend((text[cursor:first], mapping[token]))
                    cursor = last
            pieces.append(text[cursor:])
            board = "".join(pieces).encode()
            names = {key: mapping.get(value, value) for key, value in names.items()}
            names.update({key: value for key, value in mapping.items() if key not in names})
        else:
            raise ValueError("unknown accepted shipping source reduction")
    if not read(case / "shipping-inputs/main.c").startswith(board) or not board.endswith(b"}"):
        raise ValueError("observed board is not the complete actual shipping prefix")
    return board, names


def resolver_probe(original, changed, board_tools, cases):
    """Compare the actual old/new runtime resolver using actual candidate Board."""
    function = board_tools.function

    def implementation(source, prefix):
        sections = [function(source, start) for start in
                    (b"static void text(", b"static int word(", b"static Move resolve_move(")]
        text = b"\n".join(sections).decode()
        for name in ("text", "word", "resolve_move"):
            text = re.sub(r"\b" + name + r"\b", prefix + name, text)
        return text.encode()

    paths = ",\n".join(json.dumps(" ".join(case["moves"])) for case in cases).encode()
    return (b'#include <stdio.h>\n#include <string.h>\n#include "board.c"\ntypedef char *Span;\n' +
            implementation(original, "before_") + b"\n" + implementation(changed, "after_") +
            rb'''
static unsigned observations;
static int same_board(const Board *a,const Board *b){
    return a->s==b->s&&a->c==b->c&&a->e==b->e&&a->k[0]==b->k[0]&&a->k[1]==b->k[1]&&
        a->half==b->half&&a->v==b->v&&a->material==b->material&&a->h==b->h&&a->r==b->r&&
        !memcmp(a->b,b->b,sizeof a->b);
}
static void compare(const Board *p,char *token){
    Board a,b,before=*p;memset(&a,0xA5,sizeof a);memset(&b,0xA5,sizeof b);
    Move x=before_resolve_move(p,token,&a),y=after_resolve_move(p,token,&b);observations++;
    if(x!=y||(x&&!same_board(&a,&b))||!same_board(p,&before)){
        fprintf(stderr,"resolver mismatch case=%u token=%s\n",observations,token?token:"<first>");abort();
    }
}
static const char *paths[]={''' + paths + rb'''};
int main(void){
    static char token[32768];
    const char *bad[]={"","a","a1","a1a","a1a1","0000","a0a1","i1a1","a1i1","a1a9",
        "A1a1","a1A1","e2e4n","e2e4q","a7a8k","a7a8p","a7a8Q","e2e4 ","e2e4x","e2e4qq"};
    for(unsigned row=0;row<sizeof paths/sizeof *paths;row++){
        Board p;start(&p);char line[4096],*save=0;strcpy(line,paths[row]);
        for(char *move=strtok_r(line," ",&save);move;move=strtok_r(0," ",&save)){
            Board child;if(!before_resolve_move(&p,move,&child))abort();p=child;
        }
        compare(&p,0);
        Move moves[MOVES];int n=gen(&p,moves);
        for(int i=0;i<n;i++){
            before_text(moves[i],token);compare(&p,token);size_t length=strlen(token);
            for(size_t cut=0;cut<length;cut++){
                char saved=token[cut];token[cut]=0;compare(&p,token);token[cut]=saved;
            }
            for(const char *suffix="nbrqkQx";*suffix;suffix++){
                token[length]=*suffix;token[length+1]=0;compare(&p,token);
            }
        }
        for(unsigned i=0;i<sizeof bad/sizeof *bad;i++){strcpy(token,bad[i]);compare(&p,token);}
        for(unsigned byte=1;byte<256;byte++){
            token[0]='a';token[1]='1';token[2]='a';token[3]=(char)byte;token[4]=0;compare(&p,token);
        }
    }
    Board p;start(&p);memset(token,'a',sizeof token-1);token[sizeof token-1]=0;compare(&p,token);
    printf("actual-runtime-resolver observations=%u\n",observations);return 0;
}
''')


def run(portfolio_path, out):
    h = load("D_next_checks_cost", HERE / "structural_size.py")
    portfolio_bytes = read(portfolio_path / "portfolio.json")
    portfolio = json.loads(portfolio_bytes)
    h.require_settled_cost(portfolio)
    if portfolio.get("format") != "rove4k-D-bss-structural-next-v1":
        raise ValueError("measured structural-next portfolio required")
    snapshot = portfolio_path / "inputs"
    for relative, identity in portfolio["inputs"].items():
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("relative captured source input required")
        frozen = read(snapshot / relative, 1 << 20)
        if h.pin(frozen) != identity or read(ROOT / relative, 1 << 20).replace(b"\r\n", b"\n") != frozen:
            raise ValueError("measured/captured/current input differs: " + relative)
    generator = load("D_next_checks_frozen_generator", snapshot / "engines/experiments/tiny-d-submission/structural_next.py")
    _, _, _, _, _, baseline_files, _, _, changes = generator.prepare(snapshot)
    chosen, reused, omitted = select_cases(portfolio)
    modules = h.modules()
    rules = load("D_next_checks_rules", ROOT / "engines/experiments/tcec-next/profile_rules.py")
    storage = load("D_next_checks_storage", HERE / "check_storage.py")
    probe = load("D_next_checks_search", HERE / "probe_search_compact.py")
    search = changes["search"]
    dependencies = load("D_next_checks_search_runtime", HERE / "structural_search_next.py")
    board_tools = load("D_next_checks_board_lifecycle", HERE / "structural_board.py")
    reference_board = h.load_baseline()["board.c"]
    cases, coverage = rules.fixture_cases()
    report = {"format": "rove4k-D-bss-structural-next-observations-v1", "complete": False,
              "portfolio": h.pin(portfolio_bytes), "coverage": coverage, "commands": [],
              "cases": [], "candidate_failures": [], "source_reuse": reused, "omitted": omitted,
              "measured_minimum": portfolio["minimum_measured"],
              "limits": {"max_source_cases": MAX_CASES, "fixture_TT_bits": 12},
              "runtime_qualified": False, "selected": False,
              "scope": "actual shipping Board prefix, bounded state/search and actual parser/resolver C",
              "not_proven": ["packaged raw-clone runtime and BSS startup", "many-worker resource/NUMA behavior",
                             "exhaustive chess correctness", "strength or tournament admission"],
              "verifier_inputs": {str(Path(tool.__file__).relative_to(ROOT)): h.pin(read(Path(tool.__file__)))
                                  for tool in (h, rules, storage, probe, dependencies, board_tools, *modules.values())}}
    report["verifier_inputs"][str(Path(__file__).relative_to(ROOT))] = h.pin(read(Path(__file__)))

    def save():
        (out / "checks.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    hostmod = modules["host"]
    hostmod.LIMITS = {**hostmod.LIMITS, "aggregate_wall": 600, "per_command_wall": 60,
                     "child_CPU": 55, "parent_CPU": 1200, "parent_CPU_hard": 1260,
                     "tool_output_bytes": 8 << 20}
    host, body_error = None, None
    search_control = lifecycle_control = None
    try:
        host = hostmod.Host(out, report, save)
        parser_source = changes["runtime"].parser_probe(baseline_files["runtime.c"].decode()).encode()
        parser_path, parser_binary = out / "runtime-parser.c", out / "runtime-parser"
        parser_path.write_bytes(parser_source)
        host.run(["cc", "-std=c11", "-O1", "-fsanitize=undefined", "-fno-sanitize-recover=all",
                  str(parser_path), "-o", str(parser_binary)], cwd=out, kind="actual-parser-compile-ubsan")
        output = host.run([str(parser_binary)], cwd=out, kind="actual-parser-run-ubsan")
        if report["commands"][-1]["stderr"]["bytes"]:
            raise ValueError("parser sanitizer emitted diagnostics")
        report["parser"] = {"source": h.pin(parser_source), "binary": h.pin(read(parser_binary)),
                            "output": h.pin(output), "summary": output.decode().strip(), "sanitizer": "undefined"}
        (out / "runtime-parser.stdout").write_bytes(output)
        save()
        for row in chosen:
            name, selectors = row["name"], tuple(row["selectors"])
            case, directory = portfolio_path / name, out / name
            directory.mkdir()
            result = {"name": name, "selectors": list(selectors), "complete": False,
                      "whole_bytes": row["package"]["bytes"], "rules": [], "search": [], "board_lifecycle": []}
            report["cases"].append(result)
            save()
            try:
                cost_bytes = read(case / "result.json")
                cost = json.loads(cost_bytes)
                h.require_settled_cost(cost)
                files = {filename: read(case / "generated-readable" / filename, 1 << 20) for filename in h.FILES}
                if (h.inventory(files) != row["source"] or cost["input"] != row["source"] or
                        generator.project(baseline_files, selectors, changes) != files):
                    raise ValueError("measured candidate source/projection differs")
                if h.pin(read(case / "native/native")) != cost["native_runs"][0]["native"]:
                    raise ValueError("measured candidate native bytes differ")
                package = {key: row["package"][key] for key in ("bytes", "sha256")}
                if h.pin(read(case / "packed-xz-bcj-pb0")) != package:
                    raise ValueError("measured candidate package bytes differ")
                for filename, identity in cost["shipping"].items():
                    if h.pin(read(case / "shipping-inputs" / filename)) != identity:
                        raise ValueError("measured candidate shipping source differs")
                result.update(cost_report=h.pin(cost_bytes), source=h.inventory(files))
                actual_board, names = board_prefix(case, cost, modules, host)
                size = names.get("size_t", "size_t")
                declarations = (("\ntypedef " + size + " size_t;\n").encode() if size != "size_t" else b"\n")
                declarations += (b"extern size_t strlen(const char *);extern int strcmp(const char *,const char *);"
                    b"extern char *strtok_r(char *,const char *,char **);extern int printf(const char *,...);"
                    b"extern int puts(const char *);extern char *strcpy(char *,const char *);\n")
                fixture = rules.render_bound_fixture(actual_board, {
                    "board": names.get("Board", "Board"), "start": names.get("start", "start"),
                    "generate": names.get("gen", "gen"), "make": names.get("make", "make"), "four_args": False},
                    cases, declarations)
                (directory / "rules.c").write_bytes(fixture)
                result["actual_shipping_board_prefix"] = h.pin(actual_board)
                result["rules_fixture"] = h.pin(fixture)
                generated, driver, proof = search.render_probe(files, modules["source"], storage, probe,
                    reference_board=reference_board,
                    names=tuple(value.split("/", 1)[1] for value in selectors if value.startswith("search/")))
                runtime_dependencies = dependencies.runtime_dependencies(files)
                if runtime_dependencies:
                    marker = b'#include "search.c"'
                    if driver.count(marker) != 1:
                        raise ValueError("unique actual search include required")
                    driver = driver.replace(marker, runtime_dependencies + b"\n" + marker, 1)
                testdir = directory / "actual-search"
                testdir.mkdir()
                for filename, data in generated.items():
                    (testdir / filename).write_bytes(data)
                (testdir / "driver.c").write_bytes(driver)
                result.update(search_fixture=proof, actual_search_driver=h.pin(driver),
                              runtime_search_dependencies=h.pin(runtime_dependencies))
                lifecycle = board_tools.render_lifecycle_probe(reference_board, [" ".join(case["moves"]) for case in cases])
                (directory / "board-lifecycle.c").write_bytes(lifecycle)
                raw = case / "generated-readable"
                for mode, flags in (("plain", []), ("ubsan", ["-fsanitize=undefined", "-fno-sanitize-recover=all"])):
                    binary = directory / ("rules-" + mode)
                    host.run(["cc", "-std=c11", "-O1", *flags, str(directory / "rules.c"), "-o", str(binary)],
                             cwd=directory, kind=name + "-rules-compile-" + mode)
                    observed = host.run([str(binary)], cwd=directory, kind=name + "-rules-run-" + mode)
                    (directory / ("rules-" + mode + ".stdout")).write_bytes(observed)
                    result["rules"].append({"mode": mode, "binary": h.pin(read(binary)), **rules._compare_output(observed, cases)})
                    binary = testdir / ("search-" + mode)
                    host.run(["cc", "-std=c11", "-O2", "-msse4.2", "-mcx16", "-DDEV=0", "-DD_HQ=0", "-DWORKERS=4",
                              "-DTT_BITS=12", "-DCASE_PREFIX=1", "-DCASE_DENSE=0", "-DCASE_UNSIGNED_HISTORY=1", *flags,
                              str(testdir / "driver.c"), "-o", str(binary)], cwd=testdir, kind=name + "-search-compile-" + mode)
                    observed = host.run([str(binary)], cwd=testdir, kind=name + "-search-run-" + mode)
                    normalized, details = probe.verify_output(observed)
                    if search_control is None:
                        search_control = normalized
                    if normalized != search_control:
                        raise ValueError("actual search observations differ from BSS baseline")
                    (directory / ("search-" + mode + ".stdout")).write_bytes(observed)
                    (directory / ("search-" + mode + ".normalized")).write_bytes(normalized)
                    result["search"].append({"mode": mode, "binary": h.pin(read(binary)), **details, "equal_to_baseline": True})
                    binary = directory / ("board-" + mode)
                    host.run(["cc", "-std=c11", "-O2", "-DDEV=0", "-DD_HQ=0", "-DTT_BITS=23", "-DCHECK_MATERIAL", *flags,
                              "-I", str(raw), str(directory / "board-lifecycle.c"), "-o", str(binary)],
                             cwd=directory, kind=name + "-board-compile-" + mode)
                    observed = host.run([str(binary)], cwd=directory, kind=name + "-board-run-" + mode)
                    if lifecycle_control is None:
                        lifecycle_control = observed
                    if observed != lifecycle_control:
                        raise ValueError("actual board lifecycle/state differs from BSS baseline")
                    (directory / ("board-" + mode + ".stdout")).write_bytes(observed)
                    result["board_lifecycle"].append({"mode": mode, "binary": h.pin(read(binary)),
                        "output": h.pin(observed), "summary": observed.decode().strip(), "equal_to_baseline": True})
                    save()
                resolver = resolver_probe(baseline_files["runtime.c"], files["runtime.c"], board_tools, cases)
                resolver_path, binary = directory / "runtime-resolver.c", directory / "runtime-resolver"
                resolver_path.write_bytes(resolver)
                host.run(["cc", "-std=c11", "-O1", "-DDEV=0", "-DD_HQ=0", "-DTT_BITS=23",
                          "-fsanitize=undefined", "-fno-sanitize-recover=all", "-I", str(raw), str(resolver_path), "-o", str(binary)],
                         cwd=directory, kind=name + "-resolver-compile-ubsan")
                observed = host.run([str(binary)], cwd=directory, kind=name + "-resolver-run-ubsan")
                if report["commands"][-1]["stderr"]["bytes"]:
                    raise ValueError("resolver sanitizer emitted diagnostics")
                (directory / "runtime-resolver.stdout").write_bytes(observed)
                result["resolver"] = {"source": h.pin(resolver), "binary": h.pin(read(binary)), "output": h.pin(observed),
                                      "summary": observed.decode().strip(), "sanitizer": "undefined"}
                result["complete"] = True
                save()
            except (TimeoutError, MemoryError):
                raise
            except Exception as error:
                result["failure"] = {"type": type(error).__name__, "message": str(error)}
                report["candidate_failures"].append({"name": name, **result["failure"]})
                save()
                if name == "baseline":
                    raise
        passing = [row for row in report["cases"] if row["complete"]]
        report["smallest_passing_source"] = min(passing, key=lambda row: row["whole_bytes"])["name"]
        if report["candidate_failures"]:
            raise ValueError("one or more measured candidates failed source observations; see per-case failures")
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        h.finish_report(host, report, save, body_error)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("hosted compiler/probe execution is inactive without --execute")
    if not args.portfolio.is_absolute() or not args.out.is_absolute():
        parser.error("absolute portfolio and output paths required")
    portfolio, out = args.portfolio.resolve(), args.out.resolve()
    if out.exists() or any((p / ".git").exists() for p in (out, *out.parents)):
        parser.error("new output outside every Git checkout required")
    out.mkdir(parents=True)
    report = run(portfolio, out)
    print(json.dumps({"complete": report["complete"], "measured_minimum": report["measured_minimum"],
        "smallest_passing_source": report["smallest_passing_source"],
        "cases": [{"name": row["name"], "complete": row["complete"], "whole_bytes": row["whole_bytes"]}
                  for row in report["cases"]]}), flush=True)


if __name__ == "__main__":
    main()
