"""Actual Rust module-boundary fixtures for the guarded single-source merger."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAMES = ("main.rs", "board.rs", "search.rs", "runtime.rs")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def compile_fixture(rustc, files, merged, folder, *, succeeds=True):
    outputs = []
    records = []
    for label in ("modules", "merged"):
        local = folder / label
        local.mkdir(parents=True)
        selected = files if label == "modules" else {"main.rs": merged}
        for name, data in selected.items():
            (local / name).write_bytes(data)
        executable = local / ("native.exe" if os.name == "nt" else "native")
        command = [rustc, str(local / "main.rs"), "--edition=2024", "--crate-name", "r4_merge_fixture", "-o", str(executable)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        evidence = {"command": command, "returncode": result.returncode,
                    "stdout": result.stdout, "stderr": result.stderr}
        save(local / "compile.json", evidence)
        records.append(evidence)
        if succeeds:
            assert result.returncode == 0, f"{label} compile failed: {result.stderr}"
            execution = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5)
            save(local / "run.json", {"returncode": execution.returncode, "stdout": execution.stdout, "stderr": execution.stderr})
            assert execution.returncode == 0
            outputs.append(execution.stdout)
        else:
            assert result.returncode != 0 and "E0603" in result.stderr, "private module function became accessible"
    if succeeds:
        assert outputs[0] == outputs[1], (outputs[0], outputs[1])
    return {"passed": True, "source_hashes": {name: sha(data) for name, data in files.items()},
            "merged_sha256": sha(merged), "outputs": outputs, "compilations": records}


MODULES = {
    "main.rs": b'''mod board; mod search; mod runtime;
fn main(){let b=board::Board::new();println!("{}|{}",search::evaluate(&b),runtime::run());}
''',
    "board.rs": b'''pub struct Board{value:i32}
impl Board{pub fn new()->Self{Self{value:hidden()}}pub(crate)fn score(&self)->i32{self.value}}
fn hidden()->i32{7}
''',
    "search.rs": b'''use crate::board::Board;
pub fn evaluate(b:&Board)->i32{b.score()+hidden()}fn hidden()->i32{11}
''',
    "runtime.rs": b'''use super::{board,search};
pub fn run()->i32{search::evaluate(&board::Board::new())+hidden()}fn hidden()->i32{13}
''',
}

LITERALS = {
    "main.rs": b'''mod board;mod search;mod runtime;
fn main(){let text=r###"mod board; /* { \" } */"###;println!("{}|{}|{}",board::value(),search::text(text),runtime::value());}
''',
    "board.rs": b'''/* mod search; /* nested comment */ mod runtime; */
pub fn value()->i32{let mut n=0;for i in 0..=3{n+=i;}n}
''',
    "search.rs": b'''pub fn text<'a>(s:&'a str)->&'a str{s}
''',
    "runtime.rs": b'''pub fn value()->u32{let a='\\'';let b=b'/';a as u32+b as u32}
''',
}


def resource_contract(merger, out):
    stable=load("r4_resource_stable_sources",ROOT/"engines/compact/tiny-rust/build.py")
    raw={name:(ROOT/"engines/compact/tiny-rust"/name).read_bytes() for name in NAMES}
    pruned,_=stable.specialize(raw,development=False)
    original,_=merger.merge(pruned)
    resources=load("r4_resource_contract",HERE/"resources.py")
    actual,metadata=resources.embody(original,workers=2,tt_bits=18)
    assert resources.embody(original,workers=2,tt_bits=18)==(actual,metadata)
    before=merger.SYNTAX.tokenize(original.decode())
    after=merger.SYNTAX.tokenize(actual.decode())
    # Independently reconstruct exactly the three admitted root edits. Whole
    # module bodies are skipped rather than inspected by feature-name counts.
    roots=[];i=0
    while i<len(before):
        roots.append(i)
        i=merger.SYNTAX.matching(before,i)+1 if before[i] in ('(','[','{') else i+1
    edits=[]
    for i in roots:
        if before[i:i+3]==['const','fn','number']:
            end=i+3
            while before[end]!='{':
                end=merger.SYNTAX.matching(before,end)+1 if before[end] in ('(','[') else end+1
            edits.append((i,merger.SYNTAX.matching(before,end)+1,[]))
        for name,value in (('WORKERS','2'),('TT_BITS','18')):
            if before[i:i+5]==['const',name,':','usize','=']:
                end=i+5
                while before[end]!=';':
                    end=merger.SYNTAX.matching(before,end)+1 if before[end] in ('(','[','{') else end+1
                edits.append((i+5,end,[value]))
    assert len(edits)==3
    expected=[];cursor=0
    for start,end,replacement in sorted(edits):
        expected.extend(before[cursor:start]);expected.extend(replacement);cursor=end
    expected.extend(before[cursor:])
    assert after==expected,"resource producer changed tokens beyond the three independent root edits"
    assert before.count('number')==3 and after.count('number')==0
    assert metadata['input_sha256']==sha(original) and metadata['output_sha256']==sha(actual)
    rejected=[]
    for label,kwargs in (('workers1',{'workers':1}),('workers3',{'workers':3}),('tt17',{'tt_bits':17}),
                         ('tt19',{'tt_bits':19}),('bool-worker',{'workers':True}),('string-worker',{'workers':'2'}),
                         ('bool-tt',{'tt_bits':True}),('float-tt',{'tt_bits':18.0})):
        try:resources.embody(original,**kwargs)
        except (ValueError,TypeError):rejected.append(label)
        else:raise AssertionError('unsupported resource profile admitted: '+label)
    for label,source in (('source-drift',original+b' '),('mutable-bytearray',bytearray(original)),('source-text',original.decode())):
        try:resources.embody(source)
        except (ValueError,TypeError):rejected.append(label)
        else:raise AssertionError('unbound resource source admitted: '+label)
    import builtins
    old_open=builtins.open;old_read=Path.read_bytes;old_write=Path.write_bytes;old_os_open=os.open
    def forbidden(*args,**kwargs):raise AssertionError('producer call attempted filesystem I/O')
    try:
        builtins.open=forbidden;Path.read_bytes=forbidden;Path.write_bytes=forbidden;os.open=forbidden
        pure=resources.embody(original)
    finally:
        builtins.open=old_open;Path.read_bytes=old_read;Path.write_bytes=old_write;os.open=old_os_open
    assert pure==(actual,metadata)
    (out/'resource-embodied.rs').write_bytes(actual)
    return {'passed':True,'source_input_sha256':sha(original),'source_output_sha256':sha(actual),
            'independent_exact_root_edits':True,'no_filesystem_IO_during_call':True,
            'rejected':rejected,'metadata':metadata}


def main():
    raise SystemExit("Rust A is retired; this historical merge/resource test CLI is disabled.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rustc", default=os.environ.get("RUSTC", "rustc"))
    parser.add_argument("--resources-only",action="store_true",help="Python-only exact fixed-resource and rejection checks; reuses prior unchanged merge compiler evidence")
    args = parser.parse_args()
    out = args.out.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error("--out must be outside the checkout")
    out.mkdir(parents=True, exist_ok=False)
    rustc = shutil.which(args.rustc)
    if rustc is None and not args.resources_only:
        parser.error("Rust compiler unavailable")
    merger = load("r4_stream_merge_tests", HERE / "merge.py")
    report = {"passed": False, "scope": "guarded source merge, module privacy and exact fixture executions",
              "checks": {}, "rustc": rustc}
    try:
        if args.resources_only:
            report['scope']='Python-only fixed-resource token boundary and fail-closed profile/source contracts'
            report['checks']['resources']=resource_contract(merger,out)
            report['passed']=True
            print(out/'report.json')
            return
        for label, files in (("privacy-scopes", MODULES), ("lexical-boundaries", LITERALS)):
            before = dict(files)
            merged, metadata = merger.merge_unbound(files)
            assert files == before, "merger mutated source inputs"
            assert merger.merge_unbound(files) == (merged, metadata), "non-deterministic merge"
            report["checks"][label] = compile_fixture(rustc, files, merged, out / label)
        private = dict(MODULES)
        private["main.rs"] = b"mod board;mod search;mod runtime;fn main(){board::hidden();}\n"
        merged, _ = merger.merge_unbound(private)
        report["checks"]["privacy-rejection"] = compile_fixture(rustc, private, merged, out / "private", succeeds=False)
        rejected = []
        for label, source in (
            ("missing-module", b"mod board;mod search;fn main(){}"),
            ("duplicate-module", b"mod board;mod board;mod search;mod runtime;fn main(){}"),
            ("unexpected-module", b"mod board;mod search;mod runtime;mod extra;fn main(){}"),
            ("attributed-module", b"#[allow(dead_code)] mod board;mod search;mod runtime;fn main(){}"),
            ("inline-collision", b"mod board{}mod search;mod runtime;fn main(){}"),
            ("include-macro", b'mod board;mod search;mod runtime;fn main(){include!("elsewhere.rs");}'),
            ("location-macro", b'mod board;mod search;mod runtime;fn main(){println!("{}",file!());}'),
            ("cfg-attribute", b'mod board;mod search;mod runtime;#[cfg(test)]fn f(){}fn main(){}'),
            ("macro-definition", b'mod board;mod search;mod runtime;macro_rules! x{()=>{}}fn main(){}'),
            ("extern-crate", b'mod board;mod search;mod runtime;extern crate anything;fn main(){}'),
            ("unbalanced", b'mod board;mod search;mod runtime;fn main(){'),
        ):
            files = dict(MODULES, **{"main.rs": source})
            try:
                merger.merge_unbound(files)
            except (ValueError, TypeError):
                rejected.append(label)
            else:
                raise AssertionError(f"unsafe source shape accepted: {label}")
        for label, files in (("missing-input", {}), ("extra-input", dict(MODULES, **{"dev.rs": b""})),
                             ("non-byte-input", dict(MODULES, **{"board.rs": "text"}))):
            try:
                merger.merge_unbound(files)
            except (ValueError, TypeError):
                rejected.append(label)
            else:
                raise AssertionError(f"bad input accepted: {label}")
        producer = load("r4_stable_rust_source_tests", ROOT / "engines/compact/tiny-rust/build.py")
        raw = {name: (ROOT / "engines/compact/tiny-rust" / name).read_bytes() for name in NAMES}
        production, _ = producer.specialize(raw, development=False)
        frozen = dict(production)
        single, metadata = merger.merge(production)
        assert production == frozen and merger.merge(production) == (single, metadata)
        (out / "merged-production.rs").write_bytes(single)
        changed = dict(production)
        changed["board.rs"] += b" "
        try:
            merger.merge(changed)
        except ValueError:
            rejected.append("production-source-drift")
        else:
            raise AssertionError("changed bound production source accepted")
        report["checks"]["binding"] = {"passed": True, "inputs": {name: sha(data) for name, data in production.items()},
                                            "merged_sha256": sha(single), "metadata": metadata}
        report["checks"]["guards"] = {"passed": True, "rejected": rejected}
        report["passed"] = True
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        save(out / "report.json", report)
    print(out / "report.json")


if __name__ == "__main__":
    main()
