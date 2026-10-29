#!/usr/bin/env python3
"""Fresh Search/NoTid parent authority, Square source/rules and P4 runtime.

The 5233-byte candidate has fresh authenticated Search and NoTid parents and
two ordered scalar 0x88 square-successor openings. Original evidence is immutable.
All producers, consumers, rules and R support execute from one frozen tree.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import inspect
import unittest
from types import FunctionType, ModuleType, SimpleNamespace

sys.dont_write_bytecode = True
_EXECUTING_CODE = sys._getframe().f_code
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
TOOLS = (D+"search_admission.py",D+"no_tid_admission.py",D+"no_tid_runtime.py",
         D+"square_successor_admission.py",D+"square_successor_runtime.py",D+"qualify_square_successor.py")
SUPPORT = ("engines/experiments/tcec-next/profile_verify.py",
    "engines/experiments/tcec-next/profile_rules.py", "engines/experiments/tcec-scope/verify.py",
    "engines/compact/tiny-entry-d/verify.py", "engines/tests/chess_oracle.py",
    "engines/scripts/production.py", "engines/scripts/production_input.py", "engines/scripts/source_composition.py")
LOGICAL = dict(source=D+"source.py", builder=D+"build.py", storage=D+"storage.py",
    publication=D+"publication.py", owner=D+"process_owner.py", startup=D+"test_startup.py",
    checker=D+"test_process_owner.py", packaging=D+"packaging.py", bootstrap=D+"compressed_bootstrap.py",
    reducer=D+"reduce.py", arity=D+"syscall_arity.py", valid=D+"valid_input.py",
    runtime_checker=D+"test_runtime_scaffold.py", search=D+"search_compact.py",
    probe=D+"probe_search_compact.py", storage_checker=D+"check_storage.py", source_inputs=D+"source_inputs.py",
    lexical="engines/scripts/rename_c.py", minifier="engines/scripts/minify.py",
    packer="engines/compact/tiny-entry-d/packer.py")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def normalized(path):
    path=Path(path)
    data = safe(path.parent,path.name).replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named search qualifier source")
    return data


def safe(root, name, *, maximum=16 << 20):
    require(isinstance(name,str) and "\\" not in name and ":" not in name and "\0" not in name,
            "normalized relative no-TID evidence name required")
    relative = Path(name)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.parts,
            "explicit relative search evidence required")
    blocked={".git",".ssh",".aws","node_modules","dist","dist-server","coverage","models",
             "checkpoints",".cache","inventory.json","package-lock.json"}
    require(not any(p.casefold() in blocked or p.casefold()==".env" or p.casefold().startswith(".env.")
                    for p in relative.parts),"protected file is not a no-TID evidence input")
    path = Path(root) / relative
    require(not any(part.is_symlink() for part in (path, *path.parents)), "search evidence cannot follow links")
    require(path.is_file() and path.stat().st_nlink == 1 and path.stat().st_size <= maximum,
            "bounded ordinary search evidence required")
    data = path.read_bytes()
    require(len(data) <= maximum, "search evidence changed beyond its byte bound")
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_bytes(name, path, data):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def write(root, name, data):
    require(isinstance(name,str) and "\\" not in name and ":" not in name and "\0" not in name and
            not Path(name).is_absolute() and all(p not in ("",".","..") for p in name.split("/")),
            "normalized relative frozen output name required")
    path = root / name
    require(not any(part.is_symlink() for part in (path,*path.parents)),"frozen output cannot follow links")
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists(), "search qualifier will not overwrite evidence")
    path.write_bytes(data)


def runtime_support(root):
    return {name: normalized(root / name) for name in SUPPORT}


def require_support(runtime, support):
    expected = set(runtime.SUPPORT) | {SUPPORT[0], SUPPORT[1], "engines/scripts/production.py", runtime.INPUT_READER,
        "engines/scripts/source_composition.py"}
    require(set(support) == expected, "complete frozen search runtime/rules support required")


def bounded_limits(soft,hard,current,*,infinity=-1):
    require(all(type(x) is int and (x==infinity or x>=0) for x in (soft,hard,*current)),"integer inherited limits required")
    def minimum(*values):
        finite=[v for v in values if v!=infinity]
        return min(finite) if finite else infinity
    chosen_hard=minimum(hard,current[1]);chosen_soft=minimum(soft,current[0],chosen_hard)
    require(chosen_soft==infinity or chosen_soft>0,"inherited soft limit permits no further work")
    require(chosen_hard==infinity or (chosen_hard>0 and chosen_soft!=infinity and chosen_soft<=chosen_hard),
            "positive ordered inherited limits required")
    return chosen_soft,chosen_hard


def unified_sources(*groups):
    result={}
    for group in groups:
        for name,data in group.items():
            require(name not in result or result[name]==data,"frozen source role has conflicting bytes: "+name)
            result[name]=data
    return result


def run_self_tests():
    """Component rejection tests only; no nonce mint, callback, encoder or tool."""
    runtime_path=ROOT/(D+"square_successor_runtime.py")
    authority_path=ROOT/(D+"square_successor_admission.py")
    runtime_raw=normalized(runtime_path);authority_raw=normalized(authority_path)
    runtime=load_bytes("D_square_pure_runtime",runtime_path,runtime_raw)
    authority=load_bytes("D_square_pure_authority",authority_path,authority_raw)
    authority_source={"current":authority_raw,"frozen":authority_raw}
    runtime_source={"current":runtime_raw,"frozen":runtime_raw}
    class PureSquareQualification(unittest.TestCase):
        def test_genuine_source_component_is_not_an_admission(self):
            self.assertEqual(runtime._source(runtime_source,runtime),runtime_raw)
            self.assertEqual(runtime._source(authority_source,authority),authority_raw)
            self.assertEqual(authority.KIND,"rove4k.D-square-successor-source.v1")
            self.assertEqual(authority.SELECTOR,"successor")

        def test_source_drift_and_foreign_module_rejected(self):
            with self.assertRaises(ValueError):runtime._source({"current":runtime_raw+b"x","frozen":runtime_raw},runtime)
            with self.assertRaises(ValueError):runtime._source(authority_source,SimpleNamespace())

        def test_same_code_foreign_globals_rejected(self):
            original=authority.require
            try:
                authority.require=FunctionType(original.__code__,dict(original.__globals__),original.__name__)
                with self.assertRaises(ValueError):runtime._source(authority_source,authority)
            finally:authority.require=original

        def test_rebound_inherited_canonical_class_rejected(self):
            original=authority.SquareAdmission
            class Rebound(original):pass
            Rebound.__name__=Rebound.__qualname__="SquareAdmission"
            Rebound.__module__=authority.__name__
            try:
                authority.SquareAdmission=Rebound
                with self.assertRaises(ValueError):runtime._source(authority_source,authority)
            finally:authority.SquareAdmission=original

        def test_injected_private_or_instance_dict_descriptor_is_never_called(self):
            original=authority.SquareAdmission;called=[]
            def trap(instance):called.append(True);raise RuntimeError("storage descriptor invoked")
            for field in ("_valid","__dict__"):
                attributes={n:v for n,v in original.__dict__.items() if n not in ("__dict__","__weakref__")}
                attributes[field]=property(trap)
                rebound=type("SquareAdmission",(object,),attributes)
                rebound.__module__=authority.__name__;rebound.__qualname__="SquareAdmission"
                try:
                    authority.SquareAdmission=rebound
                    with self.assertRaises(ValueError):runtime._source(authority_source,authority)
                    self.assertEqual(called,[])
                finally:authority.SquareAdmission=original

        def test_exact_nine_field_foreign_parent_nonce_precedes_ancestor_path(self):
            parent_path=ROOT/(D+"no_tid_admission.py");parent_raw=normalized(parent_path)
            parent_module=load_bytes("D_square_pure_parent_NoTid",parent_path,parent_raw)
            called=[]
            class PathLikeTrap:
                def __fspath__(self):called.append("path");raise RuntimeError("ancestor path read")
            ancestor=ModuleType("D_square_untrusted_ancestor")
            def missing(name):called.append("ancestor-attribute");return PathLikeTrap()
            ancestor.__getattr__=missing
            invalid=object.__new__(parent_module.NoTidAdmission)
            object.__getattribute__(invalid,"__dict__").update({
                "_valid":object(),"_record":"{}","_parent":None,"_parent_module":ancestor,
                "_readable":(),"_shipping":(),"_images":(),"_native":b"","_linked":b""})
            with self.assertRaises(ValueError):authority.validate_parent(invalid,parent_module,
                {"current":parent_raw,"frozen":parent_raw})
            self.assertEqual(called,[])

        def test_all_public_paths_authenticate_before_token_methods(self):
            called=[]
            class Trap:
                def assert_valid(self):called.append("assert_valid");raise RuntimeError("untrusted token invoked")
                def to_record(self):called.append("to_record");raise RuntimeError("untrusted record invoked")
            fake=ModuleType("D_square_untrusted_authority");sys.modules[fake.__name__]=fake
            fake.__file__=str(authority_path);fake.KIND=authority.KIND
            fake._EXECUTING_CODE=compile(authority_raw,str(authority_path),"exec",dont_inherit=True)
            fake.SquareAdmission=Trap;token=Trap()
            calls=(lambda:runtime.prepare_carrier(token,admission_module=fake,admission_source=authority_source,
                bridge_source=runtime_source,runtime=None,packaging=None,frozen_inputs={}),
                lambda:runtime.shipping_board(token,b"",admission_module=fake,admission_source=authority_source,
                    minifier=None,lexical=None),
                lambda:runtime.render_rules(token,[],admission_module=fake,admission_source=authority_source,
                    preprocess_board=None,shared=None,minifier=None,lexical=None))
            try:
                for call in calls:
                    with self.assertRaises(ValueError):call()
                self.assertEqual(called,[])
            finally:sys.modules.pop(fake.__name__,None)

        def test_invalid_nonce_and_instance_shadow_never_mint(self):
            cls=authority.SquareAdmission
            self.assertEqual(len(inspect.signature(cls).parameters),9)
            with self.assertRaises(ValueError):cls(object(),{},None,None,{},{},{},b"",b"")
            invalid=object.__new__(cls);called=[]
            def poison():called.append(True);raise RuntimeError("instance shadow invoked")
            object.__setattr__(invalid,"assert_valid",poison)
            object.__setattr__(invalid,"to_record",poison)
            with self.assertRaises((ValueError,AttributeError)):
                runtime.prepare_carrier(invalid,admission_module=authority,admission_source=authority_source,
                    bridge_source=runtime_source,runtime=None,packaging=None,frozen_inputs={})
            self.assertEqual(called,[])

        def test_exact_nine_field_foreign_square_nonce_precedes_parent_path(self):
            called=[]
            class PathLikeTrap:
                def __fspath__(self):called.append("path");raise RuntimeError("parent path read")
            parent_module=ModuleType("D_square_untrusted_parent")
            parent_module.__file__=PathLikeTrap()
            class ParentTrap:
                def assert_valid(self):called.append("parent-assert");raise RuntimeError("parent invoked")
                def to_record(self):called.append("parent-record");raise RuntimeError("parent record invoked")
            invalid=object.__new__(authority.SquareAdmission)
            object.__getattribute__(invalid,"__dict__").update({
                "_valid":object(),"_record":"malformed JSON must not be read","_parent":ParentTrap(),
                "_parent_module":parent_module,"_readable":(),"_shipping":(),"_images":(),
                "_native":b"","_linked":b""})
            with self.assertRaises(ValueError):authority.SquareAdmission.assert_valid(invalid)
            calls=(lambda:runtime.prepare_carrier(invalid,admission_module=authority,admission_source=authority_source,
                    bridge_source=runtime_source,runtime=None,packaging=None,frozen_inputs={}),
                lambda:runtime.shipping_board(invalid,b"",admission_module=authority,admission_source=authority_source,
                    minifier=None,lexical=None),
                lambda:runtime.render_rules(invalid,[],admission_module=authority,admission_source=authority_source,
                    preprocess_board=None,shared=None,minifier=None,lexical=None))
            for call in calls:
                with self.assertRaises(ValueError):call()
            self.assertEqual(called,[])

        def test_json_and_lookalike_are_not_tokens(self):
            for token in ({"kind":authority.KIND},SimpleNamespace()):
                with self.assertRaises(ValueError):runtime.prepare_carrier(token,admission_module=authority,
                    admission_source=authority_source,bridge_source=runtime_source,runtime=None,packaging=None,frozen_inputs={})

        def test_typed_profile_component_rejects_bool_geometry(self):
            expected={"id":"test-p4","purpose":"test","workers":4,"control_threads":1,"os_threads":5,"tt_bits":23,
                "tt_entry_bytes":16,"tt_entries":8388608,"tt_mask":8388607,"tt_bytes":128<<20,
                "tt_cap_bytes":128<<20,"parallel_init":True,"init_partition_requires_page_aligned_base":True,
                "initialization_in_startup":True,"event_allocation_confirmed":None}
            self.assertEqual(runtime.validate_profile(expected),expected)
            for name,value in expected.items():
                if type(value) is int:
                    changed={**expected,name:True}
                    with self.assertRaises(ValueError):runtime.validate_profile(changed)
            for changes in ({"parallel_init":1},{"workers":28},{"tt_bits":34},{"tt_bytes":256<<30},
                            {"event_allocation_confirmed":True},{"initialization_in_startup":1}):
                with self.assertRaises(ValueError):runtime.validate_profile({**expected,**changes})

        def test_same_native_length_is_not_old_identity(self):
            component,raw=runtime.startup_component()
            self.assertEqual(pin(raw),runtime.COMPONENT_PIN)
            self.assertEqual(runtime.IDENTITY["stripped"]["bytes"],component.IDENTITY["stripped"]["bytes"])
            self.assertNotEqual(runtime.IDENTITY,component.IDENTITY)
            self.assertEqual(runtime.IDENTITY["stripped"]["sha256"],"222d8cc534073f59e3bf3f7fa114302e39e9c3f0dbb33f03924a3c6d4b98f329")
            self.assertEqual(runtime.WHOLE["bytes"],5233)
            self.assertNotEqual(runtime.WHOLE,component.WHOLE)

        def test_startup_component_rejects_non_actual_or_stale_input(self):
            with self.assertRaises(ValueError):runtime.render_startup_fixture({})
            with self.assertRaises(ValueError):runtime.render_startup_fixture({n:b"stale ids and four arguments" for n in runtime.READABLE})
            self.assertEqual(runtime.STARTUP_LABEL,"square-successor-startup-abi")

        def test_frozen_source_conflict_and_cpu_limits(self):
            self.assertEqual(unified_sources({"a":b"x"},{"a":b"x","b":b"y"}),{"a":b"x","b":b"y"})
            with self.assertRaises(ValueError):unified_sources({"a":b"x"},{"a":b"z"})
            self.assertEqual(bounded_limits(480,600,(330,360)),(330,360))
            self.assertEqual(bounded_limits(480,600,(-1,-1)),(480,600))
            with self.assertRaises(ValueError):bounded_limits(480,600,(0,0))

        def test_reserved_archive_and_embedded_linker_paths_cannot_be_reused(self):
            archives=["/archive/cpp/main.c","/archive/semantic/driver.c","/archive/startup/runtime.c"]
            used=runtime.reserved_paths({"reserved_evidence_paths":archives})
            used.update(runtime.argv_paths(["cc","-Wl,-T,/archive/native/image.ld","/archive/native/main.c","-o","/archive/native/linked"]))
            self.assertIn("/archive/native/image.ld",used)
            for reused in (*archives,"/archive/native/image.ld","/archive/native/linked"):
                with self.assertRaises(ValueError):runtime.require_fresh_paths(["/new/board.c",reused],used)
            runtime.require_fresh_paths(["/new/board.c","/new/stdout"],used)
            with self.assertRaises(ValueError):runtime.reserved_paths({"reserved_evidence_paths":archives[::-1]})

        def test_required_reader_composer_support_and_safe_names(self):
            support_runtime=SimpleNamespace(SUPPORT={n:"component-only" for n in SUPPORT[2:5]},INPUT_READER="engines/scripts/production_input.py")
            complete={n:b"component-only" for n in SUPPORT};require_support(support_runtime,complete)
            for name in ("engines/scripts/production_input.py","engines/scripts/source_composition.py"):
                with self.assertRaises(ValueError):require_support(support_runtime,{n:d for n,d in complete.items() if n!=name})
            for name in (".env","../escape",".ssh/key","node_modules/x","inventory.json"):
                with self.assertRaises(ValueError):safe(ROOT,name)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PureSquareQualification))
    if not result.wasSuccessful():raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--experiment", type=Path)
    parser.add_argument("--storage-evidence", type=Path)
    parser.add_argument("--startup-evidence", type=Path)
    parser.add_argument("--square-evidence",type=Path)
    parser.add_argument("--selector", choices=("successor",))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.self_test:
        require(not any((args.experiment,args.storage_evidence,args.startup_evidence,args.square_evidence,args.selector,args.out)),
                "pure self-test cannot request evidence or runtime work")
        run_self_tests();return
    require(all((args.experiment,args.storage_evidence,args.startup_evidence,args.square_evidence,args.selector,args.out)),
            "all explicit evidence paths, successor selector and new output required")
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 search qualifier required")
    require(all(path.is_absolute() and ".." not in path.parts for path in
                (args.out,args.experiment,args.storage_evidence,args.startup_evidence,args.square_evidence)), "absolute original evidence and new output required")
    out, experiment, storage_root = args.out.resolve(), args.experiment.resolve(), args.storage_evidence.resolve()
    startup_root=args.startup_evidence.resolve()
    square_root=args.square_evidence.resolve()
    require(not out.exists() and not any((parent / ".git").exists() for parent in (out, *out.parents)),
            "new external search output required")
    tools = {name: normalized(ROOT / name) for name in TOOLS}
    require(compile(tools[D+"qualify_square_successor.py"], __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "search qualifier source changed after execution began")
    admission = load_bytes("D_search_discovery", ROOT / (D+"search_admission.py"), tools[D+"search_admission.py"])
    new_admission=load_bytes("D_no_tid_discovery",ROOT/(D+"no_tid_admission.py"),tools[D+"no_tid_admission.py"])
    square_admission=load_bytes("D_square_discovery",ROOT/(D+"square_successor_admission.py"),tools[D+"square_successor_admission.py"])
    source_inputs = load_bytes("D_search_input_names", ROOT / LOGICAL["source_inputs"], normalized(ROOT / LOGICAL["source_inputs"]))
    original = safe(experiment, "results.json")
    record = json.loads(original)
    recipe = json.loads(safe(experiment, "inputs/" + source_inputs.RECIPE))
    producer = source_inputs.producer_names(recipe)
    inputs = {name: safe(experiment, "inputs/" + name) for name in admission.input_names(record, producer)}
    products = {name: safe(experiment, name) for name in admission.evidence_names(record, producer)}
    current = {name: normalized(ROOT / name) for name in inputs if name.startswith("engines/")}
    require(all(current[name] == inputs[name] for name in current), "current search producer differs from frozen inputs")
    storage_raw = safe(storage_root, "results.json")
    storage_record = json.loads(storage_raw)
    storage_products = {name: safe(storage_root, name) for name in admission.storage_evidence_names(storage_record)}
    startup_raw=safe(startup_root,"results.json");startup_record=json.loads(startup_raw)
    require(pin(startup_raw)==new_admission.RECEIPT,"exact approved no-TID cost evidence required")
    startup_inputs={name:safe(startup_root,"inputs/"+name) for name in new_admission.input_names(startup_record,producer)}
    startup_products={name:safe(startup_root,name) for name in new_admission.evidence_names(startup_record)}
    startup_current={name:normalized(ROOT/name) for name in startup_inputs if name.startswith("engines/")}
    require(all(startup_current[n]==startup_inputs[n] for n in startup_current),"current no-TID producer/tools differ from cost evidence")
    support = runtime_support(ROOT)
    square_raw=safe(square_root,"results.json");square_record=json.loads(square_raw)
    require(pin(square_raw)==square_admission.RECEIPT,"exact approved Square cost evidence required")
    square_inputs={name:safe(square_root,"frozen/"+name) for name in square_admission.input_names(square_record)}
    square_products={name:safe(square_root,name) for name in square_admission.evidence_names(square_record)}
    square_current={name:normalized(ROOT/name) for name in square_inputs}
    require(square_current==square_inputs,"current Square cost/helper closure differs")
    frozen_sources=unified_sources(inputs,startup_inputs,square_inputs,tools,support)
    out.mkdir()
    for name,data in frozen_sources.items():write(out/"frozen",name,data)
    for name, data in products.items():
        write(out / "products", name, data)
    for name, data in storage_products.items():
        write(out / "storage-products", name, data)
    for name,data in startup_products.items():write(out/"startup-products",name,data)
    for name,data in square_products.items():write(out/"square-products",name,data)
    write(out, "original-results.json", original)
    write(out, "storage-results.json", storage_raw)
    write(out,"startup-results.json",startup_raw)
    write(out,"square-results.json",square_raw)
    frozen = load("D_no_tid_frozen_qualifier", out / "frozen" / (D+"qualify_square_successor.py"))
    frozen.run_snapshot(out, experiment, storage_root, ROOT, record, original, inputs, products,
        current, tools, support, storage_raw, storage_products, args.selector,
        startup_root,startup_record,startup_raw,startup_inputs,startup_products,startup_current,frozen_sources,
        square_root,square_record,square_raw,square_inputs,square_products,square_current)


def run_snapshot(out, experiment, storage_root, current_root, record, original, inputs, products,
                 current, tools, support, storage_raw, storage_products, selector,
                 startup_root,startup_record,startup_raw,startup_inputs,startup_products,startup_current,frozen_sources,
                 square_root,square_record,square_raw,square_inputs,square_products,square_current):
    frozen=out/"frozen"
    admission = load("D_no_tid_parent_admission", frozen / (D+"search_admission.py"))
    new_admission=load("D_no_tid_frozen_admission",frozen/(D+"no_tid_admission.py"))
    parent_bridge = load("D_no_tid_frozen_runtime", frozen / (D+"no_tid_runtime.py"))
    square_admission=load("D_square_frozen_admission",frozen/(D+"square_successor_admission.py"))
    bridge=load("D_square_frozen_runtime",frozen/(D+"square_successor_runtime.py"))
    runtime = load("D_no_tid_frozen_R", frozen / SUPPORT[0])
    shared = load("D_no_tid_frozen_rules", frozen / SUPPORT[1])
    require_support(runtime, support)
    modules = {name: load("D_no_tid_qual_" + name, frozen / path) for name, path in LOGICAL.items()}
    modules["change"]=load("D_no_tid_change",frozen/(D+"no_tid_startup.py"))
    modules["no_tid_runtime"]=parent_bridge
    modules["square_change"]=load("D_square_change",frozen/(D+"d_square_successor.py"))
    modules["square_runtime"]=bridge
    host_path = "engines/experiments/tcec-scope/build.py"
    require(pin(inputs[host_path])["sha256"] == modules["source"].HOST_SHA, "bounded search command owner differs")
    for name, digest in runtime.SUPPORT.items():
        require(pin(support[name])["sha256"] == digest, "literal runtime support differs")
    host_module = load("D_no_tid_qual_commands", frozen / host_path)
    report = {"kind": "rove4k.D-square-successor-P4-qualification.v1", "complete": False, "commands": [],
        "selector": selector, "original_experiment": pin(original), "storage_evidence": pin(storage_raw),
        "inputs": admission.inventory(inputs), "current_inputs": admission.inventory(current),
        "tools": admission.inventory(tools), "runtime_support": admission.inventory(support),
        "startup_evidence":pin(startup_raw),"startup_inputs":admission.inventory(startup_inputs),
        "square_evidence":pin(square_raw),"square_inputs":admission.inventory(square_inputs),
        "frozen_sources":admission.inventory(frozen_sources),
        "frozen_execution": True, "old_D_native_map_used": False, "authenticated_SearchAdmission_parent_used": True,
        "owner_final_wait_authority_used": False,
        "source_admitted": False, "native_admitted": False, "package_generation_admitted": False,
        "rules_qualified": False, "fresh_full_artifact_runtime": False, "physical_placement_qualified": False,
        "size_qualified": False, "strength_qualified": False, "real_target_allocation": False, "selected": False,
        "shutdown_scope": "local TCEC-targeted minimal shutdown contract; event approval unconfirmed",
        "event_target_confirmed": False}
    def save():
        (out / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    host = None
    host_closed, counter = False, 0
    def run(command, *, cwd, kind, data=None):
        output = host.run(command, cwd=cwd, kind=kind, data=data)
        row = dict(report["commands"][-1])
        admission._settled(row)
        return output, row
    def directory(label):
        nonlocal counter
        require(isinstance(label, str) and label and all(part not in ("", ".", "..") for part in label.split("/")),
                "finite internal callback label required")
        counter += 1
        path = out / ("fresh-" + str(counter) + "-" + label.replace("/", "-"))
        path.mkdir()
        return path
    def preprocess(files, flags, members, label):
        path = directory("pp-" + label)
        for name, data in files.items():
            write(path, name, data)
        driver = b''.join(('#include "' + name + '"\n').encode() for name in members)
        main, first = run(["cc", "-E", "-P", *flags, "-I", str(path), "-x", "c", "-"],
            cwd=path, kind="independent-search-preprocess-" + label, data=driver)
        entry, second = run(["cc", "-E", "-P", "-x", "assembler-with-cpp", str(path / "start.S")],
            cwd=path, kind="independent-search-entry-" + label)
        return {"kind": "D-search-preprocess-v1", "label": label, "input_pins": admission.inventory(files),
            "flags": list(flags), "members": list(members), "driver": driver, "readable_dir": str(path),
            "commands": [first, second], "outputs": {"main.c": main, "start.S": entry}}
    def compile_identity(files, flags, units, label):
        path = directory("native-" + label)
        for name, data in files.items():
            write(path, name, data)
        linked_path, native_path = path / "linked", path / "native"
        _, row = run(["cc", *flags, *[str(path / name) for name in units],
            "-Wl,-T," + str(path / "image.ld"), "-o", str(linked_path)],
            cwd=path, kind="independent-search-compile-" + label.replace("/", "-"))
        linked = linked_path.read_bytes()
        native = modules["packer"].strip_native(linked)
        write(path, "native", native)
        return {"kind": "D-search-native-compile-v1", "label": label, "input_pins": admission.inventory(files),
            "flags": list(flags), "units": list(units), "source_paths": {name: str(path / name) for name in files},
            "linked_path": str(linked_path), "stripped_path": str(native_path), "linked": linked, "stripped": native,
            "linked_pin": pin(linked), "stripped_pin": pin(native), "command": row}
    def semantic_callback(readable, *, label, options, valid_readable, structural_proof):
        generated, driver, proof = modules["probe"].render(readable, modules["source"], modules["storage_checker"],
            reference_board=valid_readable["board.c"], prefix=True, dense=False, variant_proof=structural_proof,
            union_order="union-order" in options, previous_index="previous-piece" in options,
            constant_start="constant-start" in options, unsigned_history="unsigned-history" in options)
        modes = []
        for mode in ("plain", "ubsan"):
            path = directory("semantic-" + label + "-" + mode)
            for name, data in generated.items():
                write(path, name, data)
            write(path, "driver.c", driver)
            program = path / "fixture"
            flags = modules["probe"].compiler_flags(prefix=True, dense=False,
                previous_index="previous-piece" in options, unsigned_history="unsigned-history" in options, mode=mode)
            _, compile_row = run(["cc", *flags, str(path / "driver.c"), "-o", str(program)],
                cwd=path, kind="fresh-search-semantic-compile-" + label + "-" + mode)
            output, execute_row = run([str(program)], cwd=path, kind="fresh-search-semantic-run-" + label + "-" + mode)
            modes.append({"mode": mode, "directory": str(path),
                "source_paths": {name: str(path / name) for name in (*generated, "driver.c")},
                "binary_path": str(program), "binary": program.read_bytes(), "output": output,
                "compile": compile_row, "execute": execute_row})
        return {"kind": "D-search-semantic-v1", "label": label, "options": list(options),
            "input_pins": admission.inventory(readable), "instrumented": generated,
            "driver": driver, "proof": proof, "modes": modes}
    def preprocess_board(files, flags, label):
        path = directory("board-" + label)
        for name, data in files.items():
            write(path, name, data)
        output, row = run(["cc", "-E", "-P", *flags, str(path / "board.c")],
            cwd=path, kind="independent-search-actual-board")
        return {"kind": "D-search-board-preprocess-v1", "label": label,
            "input_pins": admission.inventory(files), "flags": list(flags),
            "readable_dir": str(path), "output": output, "command": row}
    def startup_callback(readable, label="no-tid-startup-abi"):
        component=parent_bridge if label=="no-tid-startup-abi" else bridge
        require(label in ("no-tid-startup-abi","square-successor-startup-abi"),"named startup mechanism route required")
        generated,proof=component.render_startup_fixture(readable)
        path=directory("startup-"+label)
        for name,data in generated.items():write(path,name,data)
        dialogue=parent_bridge.STARTUP_DIALOGUE.encode();write(path,"dialogue.py",dialogue)
        program=path/"fixture";receipt=path/"dialogue.json"
        _,compiled=run(["cc",*parent_bridge.STARTUP_FLAGS,*[str(path/n) for n in parent_bridge.STARTUP_UNITS],
            "-Wl,-T,"+str(path/"image.ld"),"-o",str(program)],cwd=path,kind="fresh-no-TID-startup-compile")
        output,executed=run([sys.executable,"-I","-B",str(path/"dialogue.py"),str(program),str(receipt)],
            cwd=path,kind="fresh-no-TID-startup-execute")
        receipt_raw=safe(path,"dialogue.json");observation=json.loads(receipt_raw)
        return {"kind":"D-no-TID-three-argument-startup-fixture-v1" if component is parent_bridge else bridge.STARTUP_KIND,"label":label,
            "input_pins":admission.inventory(readable),"generated":generated,"proof":proof,
            "flags":list(parent_bridge.STARTUP_FLAGS),"units":list(parent_bridge.STARTUP_UNITS),
            "source_paths":{n:str(path/n) for n in generated},"directory":str(path),
            "binary_path":str(program),"binary":safe(path,"fixture"),"compile":compiled,"execute":executed,
            "output":output,"stdin":parent_bridge.STARTUP_STDIN,"dialogue":dialogue,
            "receipt_raw":receipt_raw,"events":observation.get("events"),
            "summary":{"held_window_seconds":observation.get("held_window_seconds"),
                "received":[e["receive"] for e in observation.get("events",[]) if "receive" in e]}}
    try:
        import resource
        inherited_cpu=resource.getrlimit(resource.RLIMIT_CPU)
        inherited_as=resource.getrlimit(resource.RLIMIT_AS)
        chosen_cpu=bounded_limits(480,600,inherited_cpu,infinity=resource.RLIM_INFINITY)
        chosen_as=bounded_limits(4<<30,4<<30,inherited_as,infinity=resource.RLIM_INFINITY)
        # Host sets one equal AS pair. Use the stricter chosen soft for both.
        address_cap=chosen_as[0]
        report["source_phase_limits"]={"CPU":{"observed":list(inherited_cpu),"chosen":list(chosen_cpu)},
            "AS":{"observed":list(inherited_as),"chosen":[address_cap,address_cap]},
            "cumulative":True,"no_budget_reset":True}
        host_module.LIMITS={**host_module.LIMITS,"aggregate_wall":900,"per_command_wall":45,
            "parent_AS":address_cap,"parent_CPU":chosen_cpu[0],"parent_CPU_hard":chosen_cpu[1],"child_CPU":40}
        report["host_construction_complete"]=False;save()
        host=host_module.Host(out,report,save)
        report["host_construction_complete"]=True;save()
        parent_token = admission.admit_search(record, inputs, products, modules, current_inputs=current,
            admission_source={"current": tools[D+"search_admission.py"], "frozen": tools[D+"search_admission.py"]},
            evidence_root=str(experiment), preprocess=preprocess, compile_identity=compile_identity,
            storage_evidence={"raw": storage_raw, "root": str(storage_root), "products": storage_products},
            semantic_callback=semantic_callback)
        report["parent_admission"]=parent_token.to_record();save()
        no_tid_token=new_admission.admit_no_tid(parent_token,startup_record,startup_inputs,startup_products,modules,
            current_inputs=startup_current,
            admission_source={"current":tools[D+"no_tid_admission.py"],"frozen":tools[D+"no_tid_admission.py"]},
            parent_admission_module=admission,
            parent_admission_source={"current":tools[D+"search_admission.py"],"frozen":tools[D+"search_admission.py"]},
            bridge_source={"current":tools[D+"no_tid_runtime.py"],"frozen":tools[D+"no_tid_runtime.py"]},
            evidence_root=str(startup_root),preprocess=preprocess,compile_identity=compile_identity,
            semantic_callback=semantic_callback,startup_callback=startup_callback)
        report["no_tid_parent_admission"]=no_tid_token.to_record();save()
        square_frozen=unified_sources({name:frozen_sources[name] for name in no_tid_token.input_pins},square_inputs)
        square_actual={name:normalized(current_root/name) for name in square_frozen if name.startswith("engines/")}
        require(square_actual=={name:data for name,data in square_frozen.items() if name.startswith("engines/")},
                "current Square parent/helper source differs")
        token=square_admission.admit_square_successor(no_tid_token,square_record,square_frozen,square_products,modules,
            current_inputs=square_actual,
            admission_source={"current":tools[D+"square_successor_admission.py"],"frozen":tools[D+"square_successor_admission.py"]},
            parent_admission_module=new_admission,
            parent_admission_source={"current":tools[D+"no_tid_admission.py"],"frozen":tools[D+"no_tid_admission.py"]},
            bridge_source={"current":tools[D+"square_successor_runtime.py"],"frozen":tools[D+"square_successor_runtime.py"]},
            evidence_root=str(square_root),preprocess=preprocess,compile_identity=compile_identity,
            semantic_callback=semantic_callback,startup_callback=startup_callback)
        require(token.to_record()["selector"] == selector and token.parent is no_tid_token,"explicit Square selector/parent differs")
        carrier_inputs={name:frozen_sources[name] for name in token.input_pins}
        named, accepted = bridge.prepare_carrier(token, admission_module=square_admission,
            admission_source={"current": tools[D+"square_successor_admission.py"], "frozen": tools[D+"square_successor_admission.py"]},
            bridge_source={"current": tools[D+"square_successor_runtime.py"], "frozen": tools[D+"square_successor_runtime.py"]},
            runtime=runtime, packaging=modules["packaging"], frozen_inputs=carrier_inputs)
        carrier = out / "carrier"
        carrier.mkdir()
        for name, data in named.items():
            write(carrier, name, data)
        (carrier / "program").chmod(0o700)
        report.update(source_admitted=True, native_admitted=True, package_generation_admitted=True,
            admission=token.to_record(), carrier=admission.inventory(named), expected=accepted.expected,
            resources=accepted.resources, source_contract=accepted.source_contract)
        save()
        cases, coverage = shared.fixture_cases()
        fixture, receipt = bridge.render_rules(token, cases, admission_module=square_admission,
            admission_source={"current":tools[D+"square_successor_admission.py"],"frozen":tools[D+"square_successor_admission.py"]},
            preprocess_board=preprocess_board, shared=shared, minifier=modules["minifier"], lexical=modules["lexical"])
        rules = out / "rules"
        rules.mkdir()
        write(rules, "fixture.c", fixture)
        rules_report = {**receipt, "coverage": coverage, "complete": False, "modes": []}
        def save_rules():
            (rules / "rules.json").write_text(json.dumps(rules_report, indent=2) + "\n")
        save_rules()
        for mode, extra in (("plain", []), ("ubsan", ["-fsanitize=undefined", "-fno-sanitize-recover=all"])):
            program = rules / ("probe-" + mode)
            _, compiled = run(["cc", "-std=c11", "-O1", "-g0", "-fno-builtin", "-msse4.2", "-mcx16",
                *extra, str(rules / "fixture.c"), "-o", str(program)], cwd=rules, kind="actual-search-rules-compile-" + mode)
            output, executed = run([str(program)], cwd=rules, kind="actual-search-rules-run-" + mode)
            rules_report["modes"].append({"mode": mode, "native": pin(program.read_bytes()),
                "compile": compiled, "execute": executed, **shared._compare_output(output, cases)})
            save_rules()
        rules_report.update(complete=True, compiled=True, executed=True, rules_qualified=True)
        save_rules()
        report.update(rules_qualified=True, rules=pin((rules / "rules.json").read_bytes()))
        require(all(normalized(current_root/name)==data for name,data in frozen_sources.items() if name.startswith("engines/")),
                "source/consumer/support closure changed before full runtime")
        require(all(safe(frozen,name)==data for name,data in frozen_sources.items()),"executing frozen source closure changed")
        host.close()
        host_closed = True
        require(report.get("host_cleanup") == {"unsettled_commands": 0, "errors": []}, "fresh search tools not settled")
        limits = runtime.execution_limits(accepted, runtime.effective_available_bytes(), wall_seconds=300)
        report["runtime_limits"] = limits
        save()
        observed = runtime.run_runtime(accepted, carrier, out / "runtime", limits)
        report.update(runtime=pin((out / "runtime/runtime.json").read_bytes()), runtime_counts=observed["counts"],
            fresh_full_artifact_runtime=observed["complete"] and observed["owned_remaining"] == 0,
            size_qualified=accepted.expected["whole_bytes"] <= 4096,
            physical_placement_qualified=observed["execution_host"]["test_physical_envelope_observed"],
            input_domain="TCEC-valid-non-NUL-lines-at-most-32767-bytes",
            ownership_policy="TCEC-minimum-immediate-process-exit", last_search_output_required=False)
        require(all(normalized(current_root / name) == data for name, data in current.items()),
                "current producer changed during search qualification")
        require(all(normalized(current_root / name) == data for name, data in {**tools, **support}.items()),
                "search admission/bridge/runtime source changed during qualification")
        require(all(normalized(current_root/name)==data for name,data in startup_current.items()),
                "no-TID startup producer/tools changed during qualification")
        require(all(normalized(current_root/name)==data for name,data in square_current.items()),
                "Square helper/cost-source closure changed during qualification")
        require(all(safe(frozen,name)==data for name,data in frozen_sources.items()),"frozen source tree changed during qualification")
        require(all(safe(carrier, name) == data for name, data in named.items()), "search carrier changed during execution")
        report.update(current_frozen_closure_unchanged=True, carrier_unchanged=True)
        report["complete"] = report["fresh_full_artifact_runtime"] and report["rules_qualified"]
        save()
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        save()
        raise
    finally:
        if not host_closed and host is not None:
            try:
                host.close()
            except BaseException as error:
                report["cleanup_failure"] = {"type": type(error).__name__, "message": str(error)}
                report["complete"] = False
                save()
                raise
        save()
    require(report["complete"], "fresh search qualification did not complete")
    print(json.dumps({key: report[key] for key in ("complete", "source_admitted", "native_admitted",
        "package_generation_admitted", "rules_qualified", "fresh_full_artifact_runtime", "size_qualified",
        "physical_placement_qualified", "selected")}), flush=True)


if __name__ == "__main__":
    main()
