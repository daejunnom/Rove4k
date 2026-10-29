#!/usr/bin/env python3
"""Run a pinned, non-authoritative B semantic experiment on TEST-P4 only.

This diagnostic never changes producer/verifier gates, selects a submission,
executes W256, or grants event, placement or playing-strength qualification.
It executes local compiler-built experimental code and writes a receipt only
once all explicitly listed checks have actually completed successfully.
"""
from __future__ import annotations
import argparse
import hashlib
import types
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCHEMA = "rove4k.b-semantic-diagnostic.v1"
BASE = (7917, "68115067f6cadbf9fc1e3135fddc7aa54891660bf301c6e1d8b9d02fbe8552d0")
CANDIDATE = (7916, "b229f459aa3df639cb5816d0bee50f9acf93dbd5c884cb4baae062ca7949fdde")
NATIVES = {"base": "89b695055e8fbcdfd64f9cfd07e127180eb9827e4245631afd0525d2e0609e29", "candidate": "3585fbf96424adb7a0bda3410a278dbd78a1373ff5a0f726c35a6c5ca3eca630"}
RULES_SHA = "d9474e736e0a6da5cd66d0a199f5cd56f475ca4aea26f2b9eba775220a3066a6"
COMPILER_VERSION = "x86_64-linux-gnu-gcc-13 (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
COMPILER_SHA = "1b99826121ae6682a634e5efe09bd3e3df58ce58e0b28f849114ab5b89139c26"
EDITS = ((b"k=i+1;k<Z;k++", b"k=i;k<Z;k++"),
         (b"((q+(q&7))/2)", b"((q+(q&7))>>1)"))
SEARCH_IDS = (0, 10, 15, 27, 32, 38, 43, 47, 60, 61, 63, 67, 70, 104)


def pin(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact(data, expected):
    return (len(data), hashlib.sha256(data).hexdigest()) == expected


def transform(base):
    require(type(base) is bytes and exact(base, BASE), "baseline source pin differs")
    result = base
    for old, new in EDITS:
        require(result.count(old) == 1 and result.count(new) == 0, "forward anchor differs")
        result = result.replace(old, new, 1)
    require(exact(result, CANDIDATE), "candidate source pin differs")
    return result


def restore(candidate):
    require(type(candidate) is bytes and exact(candidate, CANDIDATE), "candidate source pin differs")
    result = candidate
    for old, new in reversed(EDITS):
        require(result.count(new) == 1 and result.count(old) == 0, "inverse anchor differs")
        result = result.replace(new, old, 1)
    require(exact(result, BASE) and transform(result) == candidate, "complete inverse differs")
    return result


def load_pinned_module(name, path, expected):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data and hashlib.sha256(data).hexdigest() == expected,
            name + " source pin differs")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def load_rules():
    rules = load_pinned_module("b_diagnostic_rules", HERE / "profile_rules.py", RULES_SHA)
    oracle = load_pinned_module("b_diagnostic_oracle", ROOT / rules.ORACLE, rules.ORACLE_SHA)
    return rules, oracle


def rule_fixture(rules, source, cases, *, guard=False):
    data = rules.render_fixture(source, "B", cases)
    needle = b"int main(void){\n static const char *paths[]={"
    addition = b"static unsigned long long rv_rule_perft(const za*p,int depth){if(!depth)return 1;unsigned moves[512];int n=rv_rule_legal(p,moves);unsigned long long z=0;for(int i=0;i<n;i++){za t;if(!h(p,moves[i],&t))abort();z+=rv_rule_perft(&t,depth-1);}return z;}\n"
    old = b'for(int i=0;i<n;i++){char text[6];rv_rule_text(moves[i],text);printf(" %s",text);}puts("");'
    new = b'for(int i=0;i<n;i++){char text[6];rv_rule_text(moves[i],text);printf(" %s",text);}printf(" perft2:%llu",rv_rule_perft(&board,2));puts("");'
    require(data.count(needle) == 1 and data.count(old) == 1, "rules driver anchor differs")
    data = data.replace(needle, addition + needle, 1).replace(old, new, 1)
    return guarded(data) if guard else data


def guarded(data):
    for marker in (b"J D o(I q){", b"J void M(za*p,I q,I v){"):
        require(data.count(marker) == 1, "coordinate guard anchor differs")
        data = data.replace(marker, marker + b"if(q<0||q>=128||(q&136))abort();", 1)
    return data


def search_fixture(rules, source, cases, *, guard=False):
    data = rules.render_fixture(source, "B", cases)
    marker = b"int main(void){\n static const char *paths[]={"
    require(data.count(marker) == 1, "search driver anchor differs")
    paths = ",".join(json.dumps(" ".join(cases[i]["moves"])) for i in SEARCH_IDS)
    driver = r'''
static const char *paths[]={@PATHS@};
int main(void){
 qq=aligned_alloc(4096,qN*sizeof(*qq));if(!qq)abort();
 for(int row=0;row<sizeof(paths)/sizeof(*paths);row++){
  za p;k(&p);qh=1;qg[0]=p.h;char line[4096];strcpy(line,paths[row]);char *save=0;
  for(char *mv=strtok_r(line," ",&save);mv;mv=strtok_r(0," ",&save)){rv_rule_play(&p,mv);qg[qh++]=p.h;}
  for(int depth=3;depth<=4;depth++){
   memset(qq,0,qN*sizeof(*qq));for(size_t j=0;j<qN;j++)atomic_flag_clear_explicit(&qq[j].a,memory_order_relaxed);
   zd w={0};atomic_store(&qp,0);qc=~(D)0;N best=0;I score=P(&w,&p,depth,-30000,30000,0,6,&best,0,1);
   if(atomic_load(&qp))abort();char text[6];T(best,text);printf("%d %d %d %s %llu",row,depth,score,text,(unsigned long long)w.n);
   za q=p;for(int ply=0;ply<depth;ply++){D key=q.h^b(q.r+(unsigned)q.n);N next=K(key,0)&131071;za child;if(!next||!h(&q,next,&child))break;T(next,text);printf(" %s",text);q=child;}puts("");fflush(stdout);
  }
 }
 free(qq);return 0;
}
'''.replace("@PATHS@", paths).encode("ascii")
    data = data[:data.index(marker)] + driver
    return guarded(data) if guard else data


def validate_rules(data, cases, rules):
    rows = data.decode("ascii").splitlines()
    require(len(rows) == len(cases) == 105, "rules row count differs")
    perft, stripped = 0, []
    for index, row in enumerate(rows):
        fields = row.split()
        require(len(fields) >= 2 and fields[0] == str(index) and fields[-1].startswith("perft2:"), "rules row differs")
        value = fields[-1][len("perft2:"):]
        require(value.isdecimal(), "perft count invalid")
        perft += int(value)
        stripped.append(" ".join(fields[:-1]))
    result = rules._compare_output(("\n".join(stripped) + "\n").encode(), cases)
    require(result["legal_moves_compared"] == 2858 and perft == 90483, "rules/perft total differs")
    return {"cases": 105, "legal_moves": 2858, "perft2_total": perft}


def execute(argv, cwd, *, data=None, timeout=120):
    result = subprocess.run(argv, cwd=cwd, input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=timeout, check=False)
    record = {"argv": argv, "exit_code": result.returncode, "stdout": pin(result.stdout),
              "stderr": pin(result.stderr), "stdin": pin(data) if data is not None else None}
    require(result.returncode == 0, "command failed: " + repr(argv))
    return result.stdout, record


def validate_native(name, binary):
    require(name in NATIVES and pin(binary)["sha256"] == NATIVES[name],
            "native pin differs: " + name)
    return pin(binary)


def validate_search(data):
    rows = data.decode("ascii").splitlines()
    require(len(rows) == len(SEARCH_IDS)*2, "search row count differs")
    for row, line in enumerate(rows):
        fields = line.split()
        require(len(fields) >= 5 and fields[0] == str(row//2) and
                fields[1] == str(3+row%2) and fields[2].lstrip("-").isdigit()
                and fields[4].isdigit(), "search row differs")


def run(base, cc="cc"):
    candidate = transform(base)
    require(restore(candidate) == base, "inverse differs")
    compiler = shutil.which(cc)
    require(compiler is not None, "compiler not found")
    compiler = str(Path(compiler).resolve(strict=True))
    compiler_pin = pin(Path(compiler).read_bytes())
    require(compiler_pin["sha256"] == COMPILER_SHA, "compiler executable pin differs")
    cc = compiler
    rules, oracle = load_rules()
    cases, _ = rules.fixture_cases(oracle=oracle)
    require(len(cases) == 105, "fixture count differs")
    with tempfile.TemporaryDirectory(prefix="rove-b-semantic-") as temp:
        cwd = Path(temp)
        version, version_cmd = execute([cc, "--version"], cwd)
        require(version.decode().splitlines()[0] == COMPILER_VERSION, "compiler version differs")
        commands, images, sources = [version_cmd], {}, {"base": base, "candidate": candidate}
        for name, source in sources.items():
            _, command = execute([cc,"-std=c11","-Os","-pthread","-xc","-","-o","x"], cwd, data=source)
            binary = (cwd / "x").read_bytes()
            images[name] = validate_native(name, binary)
            command.update(role=name+"-native-compile", image=pin(binary))
            commands.append(command)
        require(images["base"] != images["candidate"], "native difference unexpectedly absent")
        outputs = {}
        for name, source in sources.items():
            for mode in ("plain", "ubsan", "guard-ubsan"):
                fixture = rule_fixture(rules, source, cases, guard=mode == "guard-ubsan")
                flags = [] if mode == "plain" else ["-fsanitize=undefined", "-fno-sanitize-recover=all"]
                _, command = execute([cc,"-std=c11","-O1","-pthread","-g0",*flags,"-xc","-","-o","x"], cwd, data=fixture)
                command.update(role=name+"-"+mode+"-rules-compile", image=pin((cwd / "x").read_bytes()))
                commands.append(command)
                out, command = execute(["./x"], cwd)
                command.update(role=name+"-"+mode+"-rules", image=pin((cwd / "x").read_bytes()))
                commands.append(command)
                validate_rules(out, cases, rules)
                outputs[name+"-"+mode] = out
        require(len(set(outputs.values())) == 1, "rules/perft outputs differ")
        searches = {}
        for name, source in sources.items():
            for guard in (False, True):
                fixture = search_fixture(rules, source, cases, guard=guard)
                _, command = execute([cc,"-std=c11","-Os","-pthread","-xc","-","-o","x"], cwd, data=fixture)
                label = name+("-guard" if guard else "-plain")
                command.update(role=label+"-search-compile", image=pin((cwd / "x").read_bytes()))
                commands.append(command)
                out, command = execute(["./x"], cwd, timeout=300)
                command.update(role=label+"-search", image=pin((cwd / "x").read_bytes()))
                commands.append(command)
                validate_search(out)
                searches[label] = out
        require(len(set(searches.values())) == 1, "fixed-depth search outputs differ")
        return {"schema": SCHEMA, "experimental": True, "submission_admitted": False,
                "event_qualified": False, "runtime_target_qualified": False,
                "strength_proven": False, "w256_executed": False,
                "scope": "Unsigned local P4 diagnostic only; 105 rules/perft cases and selected direct single-worker depths 3 and 4; PV reconstructed from TT",
                "receipt_authenticated": False, "compiler": {"resolved_path": compiler, "image": compiler_pin, "version": COMPILER_VERSION},
                "baseline_source": pin(base), "candidate_source": pin(candidate),
                "native": images, "native_identical": False, "rules_renderer_sha256": RULES_SHA,
                "oracle_sha256": rules.ORACLE_SHA,
                "inverse_exact": True, "rules": validate_rules(outputs["base-plain"], cases, rules),
                "rule_output": pin(outputs["base-plain"]), "search_case_indices": list(SEARCH_IDS),
                "search_output": pin(searches["base-plain"]), "pv_kind": "tt_reconstructed_pv", "commands": commands}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    require(not args.output.resolve().is_relative_to(ROOT.resolve()), "output must be outside repository")
    require(not args.output.exists(), "output already exists")
    receipt = run(args.baseline.read_bytes(), args.cc)
    with args.output.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(receipt, out, sort_keys=True, indent=2)
        out.write("\n")


if __name__ == "__main__":
    main()
