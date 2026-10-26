#!/usr/bin/env python3
"""Fresh finite StructuralAdmission and actual local full-P4 qualification.

--self-test is component-only. Actual C/engine work requires --execute and a
separately reviewed budget; archived JSON never restores an authority object.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import platform
import sys
import time
from types import FunctionType, ModuleType, SimpleNamespace
import unittest

sys.dont_write_bytecode=True
_EXECUTING_CODE=sys._getframe().f_code
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
D="engines/experiments/tiny-d-submission/"
SELF=D+"qualify_structural.py"
BASE=D+"qualify_square_successor.py"
NEW=(D+"structural_admission.py",D+"structural_carrier.py",SELF)
TRANSFORMS=tuple(D+"structural_"+name+".py" for name in ("board","search","runtime"))
EXTENSIONS=tuple(D+"structural_"+name+".py" for name in
    ("board_next","search_next","platform","codec","followup","checks","runtime_check"))
HARNESS=D+"structural_size.py"
# Executing helper source is LF-normalized; the historical cost harness pin is raw.
TERMINAL_OWNER_PIN={"bytes":19309,"sha256":"4723b27096973c59e98098ffbd3c69655eb29ba35c17ced3843084b78cf64f0d"}
PROPOSED_BUDGET={"source_CPU_soft":600,"source_CPU_hard":660,"source_wall":900,
    "per_command_wall":90,"child_CPU":80,"source_AS":4<<30,"runtime_wall":300}


def require(value,message):
    if not value:raise ValueError(message)


def pin(raw):return {"bytes":len(raw),"sha256":sha256(raw).hexdigest()}


def load_bytes(name,path,raw):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    exec(compile(raw,str(path),"exec",dont_inherit=True),module.__dict__)
    return module


def base_module(root=ROOT):
    path=root/BASE;raw=path.read_bytes().replace(b"\r\n",b"\n")
    require(pin(raw)=={"bytes":44427,"sha256":"b414fe1134225914a581b1bec17480959f12cd6742f2b4b7a537b3fe18f3fa08"},"reviewed parent qualifier utilities differ")
    return load_bytes("D_structural_parent_utilities",path,raw)


def runtime_handoff_limits(base,requested,inherited_cpu,inherited_as,consumed_cpu,elapsed_wall,*,infinity=-1):
    """Keep absolute cumulative CPU caps and the remaining outer wall budget."""
    require(type(consumed_cpu) in (int,float) and math.isfinite(consumed_cpu) and consumed_cpu>=0 and
            type(elapsed_wall) in (int,float) and math.isfinite(elapsed_wall) and elapsed_wall>=0,"finite elapsed budgets required")
    cpu=base.bounded_limits(*requested["CPU_seconds"],inherited_cpu,infinity=infinity)
    address=base.bounded_limits(requested["address_space_bytes"],requested["address_space_bytes"],inherited_as,infinity=infinity)[0]
    require(address==requested["address_space_bytes"],"inherited address limit cannot support actual R headroom")
    remaining=PROPOSED_BUDGET["source_wall"]-elapsed_wall
    wall=min(requested["wall_seconds"],int(remaining))
    require(wall>=60 and cpu[0]>consumed_cpu+5,"remaining cumulative budget cannot support runtime")
    return {**requested,"CPU_seconds":list(cpu),"wall_seconds":wall,"address_space_bytes":address,
        "inherited_parent_limits":{"CPU":list(inherited_cpu),"AS":list(inherited_as)},
        "cumulative_CPU_used_at_handoff":consumed_cpu,"CPU_remaining_at_handoff":cpu[0]-consumed_cpu,
        "outer_wall_elapsed_at_handoff":elapsed_wall,"outer_wall_remaining_at_handoff":remaining,"no_budget_reset":True}


def self_test():
    """No valid nonce, C callback, compression, subprocess or engine action."""
    base=base_module()
    authority_path=ROOT/NEW[0];raw=base.normalized(authority_path)
    authority=load_bytes("D_structural_pure_admission",authority_path,raw)
    carrier_path=ROOT/NEW[1];bridge_raw=base.normalized(carrier_path)
    bridge=load_bytes("D_structural_pure_carrier",carrier_path,bridge_raw)
    terminal_raw=base.normalized(ROOT/HARNESS)
    require(pin(terminal_raw)==TERMINAL_OWNER_PIN,"reviewed terminal owner source differs")
    terminal=load_bytes("D_structural_pure_terminal_owner",ROOT/HARNESS,terminal_raw)
    pair={"current":raw,"frozen":raw};bridge_pair={"current":bridge_raw,"frozen":bridge_raw}
    class PureStructuralTests(unittest.TestCase):
        def test_exact_source_and_closed_initial_selection(self):
            self.assertEqual(authority.source(authority,pair,NEW[0]),raw)
            self.assertEqual(bridge.SELECTION,authority.SELECTION)
            self.assertEqual(bridge.ROUTE,authority.ROUTE)
            self.assertEqual(authority.IDENTITY,bridge.IDENTITY)
            self.assertEqual(authority.WHOLE,bridge.WHOLE)
            self.assertEqual(authority.SELECTION["search"],["moves432","eval_bound","mate_helper_noinline","tt_bound_select"])
        def test_source_drift_rejected(self):
            with self.assertRaises(ValueError):authority.source(authority,{"current":raw+b"x","frozen":raw},NEW[0])
        def test_same_code_foreign_globals_rejected(self):
            original=authority.pin
            try:
                authority.pin=FunctionType(original.__code__,dict(original.__globals__),original.__name__)
                with self.assertRaises(ValueError):authority.source(authority,pair,NEW[0])
            finally:authority.pin=original
        def test_class_storage_descriptors_never_run(self):
            original=authority.StructuralAdmission;called=[]
            def trap(instance):called.append(True);raise RuntimeError("storage trap invoked")
            for field in ("_valid","__dict__"):
                values={n:v for n,v in original.__dict__.items() if n not in ("__dict__","__weakref__")}
                values[field]=property(trap)
                rebound=type("StructuralAdmission",(object,),values);rebound.__module__=authority.__name__
                try:
                    authority.StructuralAdmission=rebound
                    with self.assertRaises(ValueError):authority.source(authority,pair,NEW[0])
                    self.assertEqual(called,[])
                finally:authority.StructuralAdmission=original
        def test_inherited_rebound_class_rejected(self):
            original=authority.StructuralAdmission
            class Rebound(original):pass
            Rebound.__name__=Rebound.__qualname__="StructuralAdmission";Rebound.__module__=authority.__name__
            try:
                authority.StructuralAdmission=Rebound
                with self.assertRaises(ValueError):authority.source(authority,pair,NEW[0])
            finally:authority.StructuralAdmission=original
        def test_constructor_and_exact_nine_field_nonce_reject_before_path(self):
            cls=authority.StructuralAdmission
            with self.assertRaises(ValueError):cls(object(),{},None,None,{},{},{},b"",b"")
            called=[]
            class PathTrap:
                def __fspath__(self):called.append(True);raise RuntimeError("untrusted path used")
            parent_module=ModuleType("D_structural_untrusted_parent");parent_module.__file__=PathTrap()
            token=object.__new__(cls)
            object.__getattribute__(token,"__dict__").update(dict(zip(authority.FIELDS,
                (object(),"invalid JSON",None,parent_module,(),(),(),b"",b""))))
            with self.assertRaises(ValueError):cls.assert_valid(token)
            self.assertEqual(called,[])
            with self.assertRaises(ValueError):bridge.prepare_carrier(token,admission_module=authority,admission_source=pair,
                bridge_source=bridge_pair,runtime=None,packaging=None,frozen_inputs={})
            with self.assertRaises(ValueError):bridge.shipping_board(token,b"",admission_module=authority,admission_source=pair,
                minifier=None,lexical=None)
            with self.assertRaises(ValueError):bridge.render_rules(token,[],admission_module=authority,admission_source=pair,
                preprocess_board=lambda *args:called.append(True),shared=None,minifier=None,lexical=None)
            self.assertEqual(called,[])
        def test_parent_nonce_precedes_record_and_ancestor(self):
            path=ROOT/(D+"square_successor_admission.py");parent_raw=base.normalized(path)
            parent_module=load_bytes("D_structural_pure_square",path,parent_raw)
            called=[]
            class PathTrap:
                def __fspath__(self):called.append(True);raise RuntimeError("ancestor path used")
            ancestor=ModuleType("D_structural_untrusted_ancestor");ancestor.__file__=PathTrap()
            token=object.__new__(parent_module.SquareAdmission)
            object.__getattribute__(token,"__dict__").update(dict(zip(authority.FIELDS,
                (object(),"invalid JSON",None,ancestor,(),(),(),b"",b""))))
            with self.assertRaises(ValueError):authority.validate_parent(token,parent_module,{"current":parent_raw,"frozen":parent_raw})
            self.assertEqual(called,[])
        def test_json_lookalikes_and_shadowed_instances_rejected(self):
            for token in ({"kind":authority.KIND},SimpleNamespace()):
                with self.assertRaises(ValueError):bridge.prepare_carrier(token,admission_module=authority,admission_source=pair,
                    bridge_source=bridge_pair,runtime=None,packaging=None,frozen_inputs={})
            token=object.__new__(authority.StructuralAdmission);called=[]
            object.__setattr__(token,"assert_valid",lambda:called.append(True))
            with self.assertRaises(ValueError):bridge.prepare_carrier(token,admission_module=authority,admission_source=pair,
                bridge_source=bridge_pair,runtime=None,packaging=None,frozen_inputs={})
            self.assertEqual(called,[])
        def test_reviewed_cost_required_before_names_or_transform(self):
            with self.assertRaises(ValueError):authority.cost_records({"control":b"{}","full":b"{}"})
            with self.assertRaises(ValueError):authority.evidence_names({"control":{},"full":{}})
            with self.assertRaises(ValueError):authority.transform({}, {}, {})
        def test_invalid_bytes_and_new_whole_not_square_identity(self):
            with self.assertRaises(ValueError):authority.pin(bytearray(b"x"))
            self.assertEqual(authority.IDENTITY["stripped"]["bytes"],6656)
            self.assertEqual(authority.WHOLE["bytes"],4909)
            self.assertNotEqual(authority.IDENTITY["stripped"]["sha256"],"222d8cc534073f59e3bf3f7fa114302e39e9c3f0dbb33f03924a3c6d4b98f329")
        def test_startup_requires_actual_sources_without_qualifying_them(self):
            with self.assertRaises(ValueError):bridge.render_startup_fixture({})
            self.assertEqual(bridge.STARTUP_LABEL,"structural-startup-abi")
        def test_startup_receipt_exact_types_and_finite_held_window(self):
            record={"returncode":0,"pid":42,"pgid":7,"owner_pgid":7,"held_window_seconds":.05}
            encode=lambda data:json.dumps(data).encode()
            self.assertEqual(bridge.startup_receipt(encode(record)),record)
            for raw_receipt in (None,"{}",b"[]",b"null",b"{}",b"invalid JSON"):
                with self.assertRaises(ValueError):bridge.startup_receipt(raw_receipt)
            for field,values in (("returncode",(False,True,0.,"0",1)),("pid",(True,0,-1,42.,"42")),
                    ("pgid",(True,0,-1,7.,"7")),("owner_pgid",(True,0,-1,7.,"7")),
                    ("held_window_seconds",(True,False,-1.,.049,float("nan"),float("inf"),-float("inf"),10**400,".05"))):
                for value in values:
                    with self.assertRaises(ValueError):bridge.startup_receipt(encode({**record,field:value}))
        def test_startup_receipt_rejected_before_component_delegation(self):
            generated={};expected={"selector":bridge.SELECTOR,"input":{},"output":{}}
            result={"kind":bridge.STARTUP_KIND,"label":bridge.STARTUP_LABEL,"generated":generated,
                "proof":expected,"input_pins":{},"receipt_raw":b'{"returncode":false}'}
            with self.assertRaises(ValueError):bridge.validate_startup_observation(result,generated,expected,old=None,seen=set())
        def test_module_getattr_never_runs_during_source_authentication(self):
            called=[];module=ModuleType("D_structural_missing_source")
            def trap(name):called.append(name);raise RuntimeError("module attribute trap invoked")
            module.__getattr__=trap;sys.modules[module.__name__]=module
            try:
                with self.assertRaises(ValueError):authority.source(module,pair,NEW[0])
                with self.assertRaises(ValueError):bridge._source(pair,module,logical=NEW[0])
                self.assertEqual(called,[])
                del module.__dict__["__name__"]
                with self.assertRaises(ValueError):authority.source(module,pair,NEW[0])
                with self.assertRaises(ValueError):bridge._source(pair,module,logical=NEW[0])
                self.assertEqual(called,[])
            finally:sys.modules.pop("D_structural_missing_source")
        def test_archived_entire_package_bytes_and_roles(self):
            routes=("source-jit","source-jit-compressed","packed-xz-bcj",authority.ROUTE)
            products={"full/"+route:("archived-"+route).encode() for route in routes}
            record={"packages":{route:authority.pin(products["full/"+route]) for route in routes}}
            authority.archived_packages(record,products,"full")
            changed=dict(products);changed["full/"+authority.ROUTE]=b"X"+changed["full/"+authority.ROUTE][1:]
            with self.assertRaises(ValueError):authority.archived_packages(record,changed,"full")
            with self.assertRaises(ValueError):authority.archived_packages({"packages":{}},products,"full")
        def test_wrong_native_rejected_before_package_source_or_encoder(self):
            called=[];module=ModuleType("D_structural_no_encoding")
            def trap(name):called.append(name);raise RuntimeError("package source touched")
            module.__getattr__=trap
            for native in (b"",b"X"*authority.IDENTITY["stripped"]["bytes"]):
                with self.assertRaises(ValueError):bridge.package_native(native,module)
            self.assertEqual(called,[])
        def test_counted_diagnostic_projection_complete_inverse(self):
            original=b"protected-prefix\n"+bridge.COUNTED_OUTPUT+b"#if DEV\nstatic void output(const char *s){}\nprotected-suffix\n"
            readable={name:(original if name=="runtime.c" else name.encode()) for name in bridge.READABLE}
            generated,proof=bridge.diagnostic_projection(readable)
            begin=proof["edit"]["begin"];changed=generated["runtime.c"]
            self.assertEqual(changed[:begin]+changed[begin+len(bridge.TRACE_OUTPUT):],original)
            self.assertEqual(proof["gaps"],[{"begin":0,"end":begin,**bridge.pin(original[:begin])},
                {"begin":begin,"end":len(original),**bridge.pin(original[begin:])}])
            self.assertTrue(proof["complete_inverse"]);self.assertFalse(proof["shipping_source_changed"])
            for name in bridge.READABLE-{"runtime.c"}:self.assertEqual(generated[name],readable[name])
            for bad in (original+bridge.COUNTED_OUTPUT,changed,original.replace(bridge.COUNTED_OUTPUT,b"stale-counted-role\n")):
                with self.assertRaises(ValueError):bridge.diagnostic_projection({**readable,"runtime.c":bad})
        def test_archive_and_embedded_linker_paths_are_reserved(self):
            used=bridge.reserved_paths({"reserved_evidence_paths":["/archive/original","/parent/image.ld"]})
            self.assertEqual(bridge.argv_paths(["cc","-Wl,-T,/parent/image.ld","/fresh/main.c"]),{"/parent/image.ld","/fresh/main.c"})
            with self.assertRaises(ValueError):bridge.require_fresh_paths(["/archive/original"],used)
            with self.assertRaises(ValueError):bridge.require_fresh_paths(["/parent/image.ld"],used)
            with self.assertRaises(ValueError):bridge.require_fresh_paths(["/fresh","/fresh"],used)
            bridge.require_fresh_paths(["/fresh"],used)
        def test_bounded_budget_and_no_reset(self):
            self.assertEqual(base.bounded_limits(600,660,(330,360)),(330,360))
            self.assertEqual(base.bounded_limits(600,660,(-1,-1)),(600,660))
            with self.assertRaises(ValueError):base.bounded_limits(600,660,(0,0))
            self.assertEqual(PROPOSED_BUDGET["runtime_wall"],300)
            request={"CPU_seconds":[280,285],"address_space_bytes":2<<30,"wall_seconds":300}
            chosen=runtime_handoff_limits(base,request,(250,260),(4<<30,4<<30),80.,650.)
            self.assertEqual(chosen["CPU_seconds"],[250,260]);self.assertEqual(chosen["wall_seconds"],250)
            self.assertEqual(chosen["CPU_remaining_at_handoff"],170.)
            with self.assertRaises(ValueError):runtime_handoff_limits(base,request,(250,260),(4<<30,4<<30),248.,0.)
            with self.assertRaises(ValueError):runtime_handoff_limits(base,request,(600,660),(1<<30,1<<30),0.,0.)
            with self.assertRaises(ValueError):runtime_handoff_limits(base,request,(600,660),(4<<30,4<<30),0.,850.)
            with self.assertRaises(ValueError):runtime_handoff_limits(base,request,(600,660),(4<<30,4<<30),float("inf"),0.)
        def test_source_role_is_not_transferable(self):
            with self.assertRaises(ValueError):authority.source(authority,pair,D+"square_successor_admission.py")
            with self.assertRaises(ValueError):authority.source(SimpleNamespace(),pair,NEW[0])
        def test_only_three_new_sources_and_distinct_route(self):
            self.assertEqual(NEW,(D+"structural_admission.py",D+"structural_carrier.py",SELF))
            self.assertEqual(bridge.ROUTE,"packed-xz-bcj-pb0")
            self.assertEqual(authority.SELECTION["runtime"][-1],"shared-resolver")
        def test_finite_variants_keep_actual_abi_and_capacity(self):
            full=authority.variant_contract("initial-full");fast=authority.variant_contract("fast-capacity")
            self.assertEqual(full["identity"],authority.IDENTITY);self.assertEqual(full["startup_argument_count"],3)
            self.assertFalse(full["nonreturning"])
            self.assertEqual(fast["identity"]["stripped"]["bytes"],6464);self.assertEqual(fast["whole"]["bytes"],4737)
            self.assertEqual(fast["startup_argument_count"],2);self.assertTrue(fast["nonreturning"])
            self.assertEqual(fast["board_contract"]["moves"],15*27+8)
            self.assertIn("initial_material_owner",fast["board_contract"])
            self.assertEqual(fast["selection"]["search_next"],["terminal_first_late_check","root_current","capacity413"])
            for value in (None,"full","fast","tcec-provisional",{"variant":"fast-capacity"}):
                with self.assertRaises(ValueError):authority.variant_contract(value)
        def test_variant_contract_copies_and_historical_cohort_separation(self):
            first=authority.variant_contract("fast-capacity")
            first["selection"]["search_next"].append("unknown")
            self.assertNotIn("unknown",authority.variant_contract("fast-capacity")["selection"]["search_next"])
            self.assertEqual(authority.HISTORICAL_144AD["harness"]["bytes"],19718)
            self.assertEqual(authority.HARNESS_PIN["bytes"],19309)
            self.assertEqual(authority.HISTORICAL_144AD["cost"]["control"]["bytes"],56870)
            self.assertEqual(authority.COST["control"]["bytes"],60145)
            self.assertNotEqual(authority.HISTORICAL_144AD["transforms"],authority.TRANSFORMS)
        def test_fast_wrong_native_rejected_before_recipe_encoder(self):
            for native in (b"",b"X"*6464):
                with self.assertRaises(ValueError):bridge.package_native(native,None,variant="fast-capacity",
                    admission_module=authority,admission_source=pair,codec=None)
        def test_foreign_variant_equality_hooks_never_run(self):
            called=[]
            class Foreign:
                def __eq__(self,other):called.append("eq");raise RuntimeError("foreign equality invoked")
                def __ne__(self,other):called.append("ne");raise RuntimeError("foreign inequality invoked")
            value=Foreign()
            with self.assertRaises(ValueError):authority.variant_contract(value)
            with self.assertRaises(ValueError):bridge.package_native(b"",None,variant=value)
            with self.assertRaises(ValueError):bridge.render_startup_fixture({},variant=value)
            self.assertEqual(called,[])
        def test_single_known_recipe_and_honest_fixed_startup_role(self):
            contract=authority.variant_contract("fast-capacity")
            self.assertEqual(contract["route"],"packed-xz-bcj-hc3-unnamed")
            self.assertEqual(contract["header"]["bytes"],205)
            self.assertEqual(contract["codec"]["config"],{"lc":0,"lp":0,"pb":0,"mf":3,"nice_len":32,"depth":64})
            self.assertEqual(bridge.FIXED_STARTUP_LABEL,"structural-fixed-startup-abi")
            self.assertNotEqual(bridge.FIXED_STARTUP_KIND,bridge.STARTUP_KIND)
        def test_manifest_and_whole_json_never_restore_authority(self):
            with self.assertRaises(ValueError):authority.cohort_record(b'{}')
            with self.assertRaises(ValueError):authority.whole_records({"control":b'{}',"fast-capacity":b'{}'})
            self.assertEqual(len(authority.whole_evidence_names()),8)
            self.assertEqual(set(authority.COST),{"control","fast-capacity"})
        def test_terminal_body_cleanup_save_failure_identity_matrix(self):
            for body_fails in (False,True):
                for cleanup_fails in (False,True):
                    for save_fails in (False,True):
                        with self.subTest(body=body_fails,cleanup=cleanup_fails,save=save_fails):
                            report={"complete":False,"host_cleanup":{"unsettled_commands":0,"errors":[]}}
                            events=[];saved=[]
                            body_error=RuntimeError("primary body")
                            cleanup_error=OSError("secondary close")
                            save_error=OSError("secondary save")
                            class Host:
                                def close(self):
                                    events.append("close")
                                    if cleanup_fails:raise cleanup_error
                            def save():
                                events.append("save");saved.append(report["complete"])
                                if save_fails:raise save_error
                            def run():
                                primary=None
                                try:
                                    if body_fails:raise body_error
                                    report["observations_complete"]=True
                                except BaseException as error:
                                    primary=error
                                    report["failure"]={"type":type(error).__name__,"message":str(error)}
                                    raise
                                finally:terminal.finish_report(Host(),report,save,primary)
                            expected=body_error if body_fails else cleanup_error if cleanup_fails else save_error if save_fails else None
                            if expected is None:run()
                            else:
                                with self.assertRaises(BaseException) as caught:run()
                                self.assertIs(caught.exception,expected)
                            self.assertEqual(events,["close","save"])
                            self.assertEqual(report["complete"],expected is None)
                            self.assertEqual(saved,[not body_fails and not cleanup_fails])
                            self.assertEqual("failure" in report,body_fails)
                            self.assertEqual("cleanup_failure" in report,cleanup_fails)
                            self.assertEqual("save_failure" in report,save_fails)
        def test_terminal_already_closed_host_is_not_reopened(self):
            report={"complete":False,"host_cleanup":{"unsettled_commands":0,"errors":[]}};events=[]
            terminal.finish_report(None,report,lambda:events.append(report["complete"]))
            self.assertEqual(events,[True]);self.assertTrue(report["complete"])
            primary=KeyboardInterrupt("original interruption")
            def save():raise OSError("secondary receipt")
            terminal.finish_report(None,report,save,primary)
            self.assertFalse(report["complete"]);self.assertIn("save_failure",report)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PureStructuralTests)
    require(unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful(),"pure structural self-tests failed")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--execute",action="store_true",help="requires separate reviewed C/engine budget")
    parser.add_argument("--variant",choices=("initial-full","fast-capacity"))
    for name in ("experiment","storage-evidence","startup-evidence","square-evidence","structural-evidence","out"):
        parser.add_argument("--"+name,type=Path)
    args=parser.parse_args()
    paths=(args.experiment,args.storage_evidence,args.startup_evidence,args.square_evidence,args.structural_evidence,args.out)
    if args.self_test:
        require(not args.execute and args.variant is None and not any(paths),"pure test cannot request evidence/execution")
        self_test();return
    require(args.execute and args.variant is not None and all(paths),"explicit variant, separately budget-approved execution and all evidence paths required")
    require(sys.platform=="linux" and platform.machine()=="x86_64","Linux x86-64 qualifier required")
    require(all(p.is_absolute() and ".." not in p.parts for p in paths),"absolute evidence/new output paths required")
    base=base_module();out=args.out.resolve()
    require(not out.exists() and not any((p/".git").exists() for p in (out,*out.parents)),"new external output required")
    tools={n:base.normalized(ROOT/n) for n in (*base.TOOLS,*NEW,*TRANSFORMS,*EXTENSIONS,HARNESS)}
    require(compile(tools[SELF],__file__,"exec",dont_inherit=True)==_EXECUTING_CODE,"qualifier source changed since execution began")
    search=load_bytes("D_structural_discovery_search",ROOT/base.TOOLS[0],tools[base.TOOLS[0]])
    no_tid=load_bytes("D_structural_discovery_no_tid",ROOT/(D+"no_tid_admission.py"),tools[D+"no_tid_admission.py"])
    square=load_bytes("D_structural_discovery_square",ROOT/(D+"square_successor_admission.py"),tools[D+"square_successor_admission.py"])
    structural=load_bytes("D_structural_discovery",ROOT/NEW[0],tools[NEW[0]])
    inputs_tool=load_bytes("D_structural_input_names",ROOT/base.LOGICAL["source_inputs"],base.normalized(ROOT/base.LOGICAL["source_inputs"]))
    roots={k:getattr(args,k).resolve() for k in ("experiment","storage_evidence","startup_evidence","square_evidence","structural_evidence")}
    originals={k:base.safe(roots[k],"results.json") for k in ("experiment","storage_evidence","startup_evidence","square_evidence")}
    records={k:json.loads(raw) for k,raw in originals.items()}
    recipe=json.loads(base.safe(roots["experiment"],"inputs/"+inputs_tool.RECIPE));producer=inputs_tool.producer_names(recipe)
    parent_inputs={n:base.safe(roots["experiment"],"inputs/"+n) for n in search.input_names(records["experiment"],producer)}
    startup_inputs={n:base.safe(roots["startup_evidence"],"inputs/"+n) for n in no_tid.input_names(records["startup_evidence"],producer)}
    square_inputs={n:base.safe(roots["square_evidence"],"frozen/"+n) for n in square.input_names(records["square_evidence"])}
    products={n:base.safe(roots["experiment"],n) for n in search.evidence_names(records["experiment"],producer)}
    storage_products={n:base.safe(roots["storage_evidence"],n) for n in search.storage_evidence_names(records["storage_evidence"])}
    startup_products={n:base.safe(roots["startup_evidence"],n) for n in no_tid.evidence_names(records["startup_evidence"])}
    square_products={n:base.safe(roots["square_evidence"],n) for n in square.evidence_names(records["square_evidence"])}
    cohort_raw=base.safe(roots["structural_evidence"],"source-freeze.json")
    cohort=structural.cohort_record(cohort_raw)
    cohort_sources={n:base.normalized(ROOT/n) for n in cohort["files"]}
    require(structural.inventory(cohort_sources)==cohort["files"],"current LF source differs from exact committed cohort")
    cost_root=roots["structural_evidence"] / "actual-proof/profiles/test-p4"
    whole_root=roots["structural_evidence"] / "actual-proof/whole-reproduction/test-p4"
    cost_raw={name:base.safe(cost_root,name+"/result.json") for name in structural.COST}
    cost=structural.cost_records(cost_raw)
    structural_products={n:base.safe(cost_root,n) for n in structural.evidence_names(cost)}
    whole_raw={name:base.safe(whole_root,name+"/result.json") for name in structural.WHOLE_RECEIPTS}
    structural.whole_records(whole_raw)
    whole_products={n:base.safe(whole_root,n) for n in structural.whole_evidence_names()}
    support=base.runtime_support(ROOT)
    frozen=base.unified_sources(parent_inputs,startup_inputs,square_inputs,tools,support,cohort_sources)
    current={n:base.normalized(ROOT/n) for n in frozen if n.startswith("engines/")}
    require(current=={n:d for n,d in frozen.items() if n.startswith("engines/")},"current producer/support differs from retained parent inputs")
    out.mkdir()
    for n,d in frozen.items():base.write(out/"frozen",n,d)
    for folder,data in (("products",products),("storage-products",storage_products),("startup-products",startup_products),
                        ("square-products",square_products),("structural-products",structural_products),("whole-products",whole_products)):
        for n,d in data.items():base.write(out/folder,n,d)
    for name,raw in originals.items():base.write(out,name+"-results.json",raw)
    for name,raw in cost_raw.items():base.write(out,"structural-"+name+"-result.json",raw)
    for name,raw in whole_raw.items():base.write(out,"structural-whole-"+name+"-result.json",raw)
    base.write(out,"source-freeze.json",cohort_raw)
    snapshot=base.load("D_structural_frozen_qualifier",out/"frozen"/SELF)
    snapshot.run_snapshot(out,ROOT,roots,originals,records,parent_inputs,startup_inputs,square_inputs,
        products,storage_products,startup_products,square_products,cost,structural_products,frozen,current,tools,support,
        args.variant,cohort_raw,whole_raw,whole_products,cost_root,whole_root)


def run_snapshot(out,current_root,roots,originals,records,parent_inputs,startup_inputs,square_inputs,
                 products,storage_products,startup_products,square_products,cost,structural_products,frozen_sources,current,tools,support,
                 variant,cohort_raw,whole_raw,whole_products,cost_root,whole_root):
    started=time.monotonic()
    base=base_module(out/"frozen");frozen=out/"frozen"
    search=base.load("D_structural_search_admission",frozen/(D+"search_admission.py"))
    no_tid=base.load("D_structural_no_tid_admission",frozen/(D+"no_tid_admission.py"))
    square=base.load("D_structural_square_admission",frozen/(D+"square_successor_admission.py"))
    admission=base.load("D_structural_admission",frozen/NEW[0]);carrier=base.load("D_structural_carrier",frozen/NEW[1])
    require(pin(base.safe(frozen,HARNESS))==TERMINAL_OWNER_PIN,"reviewed terminal owner source differs")
    terminal=base.load("D_structural_terminal_owner",frozen/HARNESS)
    no_tid_bridge=base.load("D_structural_no_tid_runtime",frozen/(D+"no_tid_runtime.py"))
    square_bridge=base.load("D_structural_square_runtime",frozen/(D+"square_successor_runtime.py"))
    runtime=base.load("D_structural_R",frozen/base.SUPPORT[0]);shared=base.load("D_structural_rules",frozen/base.SUPPORT[1])
    base.require_support(runtime,support)
    modules={name:base.load("D_structural_"+name,frozen/path) for name,path in base.LOGICAL.items()}
    modules.update(change=base.load("D_structural_no_tid_change",frozen/(D+"no_tid_startup.py")),no_tid_runtime=no_tid_bridge,
        square_change=base.load("D_structural_square_change",frozen/(D+"d_square_successor.py")),square_runtime=square_bridge,
        structural_carrier=carrier,structural_rules=shared)
    for name,path in zip(("board","search","runtime"),TRANSFORMS):modules["structural_"+name]=base.load("D_structural_transform_"+name,frozen/path)
    for path in EXTENSIONS:
        role=Path(path).stem
        if role in ("structural_board_next","structural_search_next","structural_platform","structural_codec"):
            modules[role]=base.load("D_structural_transform_"+role,frozen/path)
    host_path="engines/experiments/tcec-scope/build.py"
    require(pin(parent_inputs[host_path])["sha256"]==modules["source"].HOST_SHA,"unchanged source command owner required")
    for name,digest in runtime.SUPPORT.items():require(pin(support[name])["sha256"]==digest,"literal runtime support differs")
    host_module=base.load("D_structural_commands",frozen/host_path)
    report={"kind":"rove4k.D-structural-P4-qualification.v1","complete":False,"commands":[],
        "frozen_sources":admission.inventory(frozen_sources),"original_receipts":{n:pin(d) for n,d in originals.items()},
        "structural_cost":deepcopy_data(admission.COST),"frozen_execution":True,"old_native_maps_changed":False,
        "old_parent_full_runtime_executed":False,"variant":variant,"source_commit":admission.COMMIT,
        "source_cohort":pin(cohort_raw),"historical_CRLF_receipts_relabelled":False,
        **{n:False for n in ("source_admitted","native_admitted","package_generation_admitted","rules_qualified",
            "fresh_full_artifact_runtime","size_qualified","physical_placement_qualified","strength_qualified","event_target_confirmed","selected")}}
    def save():(out/"qualification.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=None;closed=False;counter=0;body_error=None
    def directory(label):
        nonlocal counter
        require(type(label) is str and all(p not in ("",".","..") for p in label.split("/")),"closed callback label required")
        counter+=1;path=out/("fresh-"+str(counter)+"-"+label.replace("/","-"));path.mkdir();return path
    def run(argv,path,kind,data=None):
        output=host.run(argv,cwd=path,kind=kind,data=data);row=dict(report["commands"][-1]);search.settled(row);return output,row
    def preprocess(files,flags,members,label):
        path=directory("pp-"+label)
        for n,d in files.items():base.write(path,n,d)
        driver=b''.join(('#include "'+n+'"\n').encode() for n in members)
        main,first=run(["cc","-E","-P",*flags,"-I",str(path),"-x","c","-"],path,"fresh-structural-cpp-"+label,driver)
        entry,second=run(["cc","-E","-P","-x","assembler-with-cpp",str(path/"start.S")],path,"fresh-structural-entry-"+label)
        return {"kind":"D-search-preprocess-v1","label":label,"input_pins":admission.inventory(files),"flags":flags,
            "members":members,"driver":driver,"readable_dir":str(path),"commands":[first,second],"outputs":{"main.c":main,"start.S":entry}}
    def compile_identity(files,flags,units,label):
        path=directory("native-"+label)
        for n,d in files.items():base.write(path,n,d)
        linked_path,native_path=path/"linked",path/"native"
        _,row=run(["cc",*flags,*[str(path/n) for n in units],"-Wl,-T,"+str(path/"image.ld"),"-o",str(linked_path)],path,"fresh-structural-native-"+label.replace("/","-"))
        linked=linked_path.read_bytes();native=modules["packer"].strip_native(linked);base.write(path,"native",native)
        return {"kind":"D-search-native-compile-v1","label":label,"input_pins":admission.inventory(files),"flags":flags,"units":units,
            "source_paths":{n:str(path/n) for n in files},"linked_path":str(linked_path),"stripped_path":str(native_path),
            "linked":linked,"stripped":native,"linked_pin":pin(linked),"stripped_pin":pin(native),"command":row}
    def semantic_callback(readable,*,label,options,valid_readable,structural_proof):
        generated,driver,proof=modules["probe"].render(readable,modules["source"],modules["storage_checker"],reference_board=valid_readable["board.c"],
            prefix=True,dense=False,variant_proof=structural_proof,union_order="union-order" in options,
            previous_index="previous-piece" in options,constant_start="constant-start" in options,unsigned_history="unsigned-history" in options)
        modes=[]
        for mode in ("plain","ubsan"):
            path=directory("semantic-"+label+"-"+mode)
            for n,d in {**generated,"driver.c":driver}.items():base.write(path,n,d)
            flags=modules["probe"].compiler_flags(prefix=True,dense=False,previous_index="previous-piece" in options,unsigned_history="unsigned-history" in options,mode=mode)
            binary=path/"fixture";_,compiled=run(["cc",*flags,str(path/"driver.c"),"-o",str(binary)],path,"fresh-parent-semantic-compile-"+label+"-"+mode)
            output,executed=run([str(binary)],path,"fresh-parent-semantic-run-"+label+"-"+mode)
            modes.append({"mode":mode,"directory":str(path),"source_paths":{n:str(path/n) for n in (*generated,"driver.c")},
                "binary_path":str(binary),"binary":binary.read_bytes(),"output":output,"compile":compiled,"execute":executed})
        return {"kind":"D-search-semantic-v1","label":label,"options":list(options),"input_pins":admission.inventory(readable),
            "instrumented":generated,"driver":driver,"proof":proof,"modes":modes}
    def startup_callback(readable,label="no-tid-startup-abi"):
        component={"no-tid-startup-abi":no_tid_bridge,"square-successor-startup-abi":square_bridge,
            "structural-startup-abi":carrier,"structural-fixed-startup-abi":carrier}[label]
        if component is carrier:
            active="fast-capacity" if label==carrier.FIXED_STARTUP_LABEL else "initial-full"
            generated,proof=carrier.render_startup_fixture(readable,variant=active,admission_module=admission,admission_source=pair("structural_admission.py"))
        else:generated,proof=component.render_startup_fixture(readable)
        path=directory("startup-"+label)
        for n,d in generated.items():base.write(path,n,d)
        dialogue=proof.get("dialogue_source",no_tid_bridge.STARTUP_DIALOGUE).encode();base.write(path,"dialogue.py",dialogue)
        binary=path/"fixture";receipt=path/"dialogue.json"
        _,compiled=run(["cc",*no_tid_bridge.STARTUP_FLAGS,*[str(path/n) for n in no_tid_bridge.STARTUP_UNITS],"-Wl,-T,"+str(path/"image.ld"),"-o",str(binary)],path,"fresh-structural-startup-compile-"+label)
        output,executed=run([sys.executable,"-I","-B",str(path/"dialogue.py"),str(binary),str(receipt)],path,"fresh-structural-startup-run-"+label)
        raw=base.safe(path,"dialogue.json");child=json.loads(raw)
        kind=("D-no-TID-three-argument-startup-fixture-v1" if component is no_tid_bridge else
            carrier.FIXED_STARTUP_KIND if label==carrier.FIXED_STARTUP_LABEL else component.STARTUP_KIND)
        return {"kind":kind,"label":label,"input_pins":admission.inventory(readable),"generated":generated,"proof":proof,
            "flags":list(no_tid_bridge.STARTUP_FLAGS),"units":list(no_tid_bridge.STARTUP_UNITS),"source_paths":{n:str(path/n) for n in generated},
            "directory":str(path),"binary_path":str(binary),"binary":base.safe(path,"fixture"),"compile":compiled,"execute":executed,
            "output":output,"stdin":no_tid_bridge.STARTUP_STDIN,"dialogue":dialogue,"receipt_raw":raw,"events":child.get("events"),
            "summary":{"held_window_seconds":child.get("held_window_seconds"),"received":[e["receive"] for e in child.get("events",[]) if "receive" in e]}}
    def observations_callback(readable,*,parent,source_proof):
        rows=[]
        for spec in admission.observation_specs(readable,parent,source_proof,modules):
            path=directory("component-"+spec["component"]+"-"+spec["mode"])
            for n,d in spec["sources"].items():base.write(path,n,d)
            binary=path/"fixture";flags=spec["flags"]
            _,compiled=run(["cc",*flags,str(path/"driver.c"),"-o",str(binary)],path,"structural-component-compile-"+spec["component"]+"-"+spec["mode"])
            output,executed=run([str(binary)],path,"structural-component-run-"+spec["component"]+"-"+spec["mode"])
            rows.append({**spec,"directory":str(path),"source_paths":{n:str(path/n) for n in spec["sources"]},"binary_path":str(binary),
                "binary":binary.read_bytes(),"output":output,"compile":compiled,"execute":executed})
        return {"kind":admission.KIND+".observations","input_pins":admission.inventory(readable),"source_proof":source_proof,"components":rows}
    def preprocess_board(files,flags,label):
        path=directory("board-"+label)
        for n,d in files.items():base.write(path,n,d)
        output,row=run(["cc","-E","-P",*flags,str(path/"board.c")],path,"structural-actual-board-cpp")
        return {"kind":"D-search-board-preprocess-v1","label":label,"input_pins":admission.inventory(files),"flags":flags,"readable_dir":str(path),"output":output,"command":row}
    def pair(name):return {"current":tools[D+name],"frozen":tools[D+name]}
    try:
        import resource
        inherited_cpu=resource.getrlimit(resource.RLIMIT_CPU);inherited_as=resource.getrlimit(resource.RLIMIT_AS)
        cpu=base.bounded_limits(PROPOSED_BUDGET["source_CPU_soft"],PROPOSED_BUDGET["source_CPU_hard"],inherited_cpu,infinity=resource.RLIM_INFINITY)
        address=base.bounded_limits(PROPOSED_BUDGET["source_AS"],PROPOSED_BUDGET["source_AS"],inherited_as,infinity=resource.RLIM_INFINITY)[0]
        usage=resource.getrusage(resource.RUSAGE_SELF);spent=usage.ru_utime+usage.ru_stime
        elapsed=time.monotonic()-started;remaining=int(PROPOSED_BUDGET["source_wall"]-elapsed)
        require(cpu[0]>spent+5 and remaining>=60,"inherited remaining source budget permits no bounded work")
        host_module.LIMITS={**host_module.LIMITS,"aggregate_wall":remaining,"per_command_wall":PROPOSED_BUDGET["per_command_wall"],
            "parent_CPU":cpu[0],"parent_CPU_hard":cpu[1],"parent_AS":address,"child_CPU":min(PROPOSED_BUDGET["child_CPU"],*cpu),
            "child_AS":min(host_module.LIMITS["child_AS"],address),"nested_producer_AS":min(host_module.LIMITS["nested_producer_AS"],address),"tool_output_bytes":8<<20}
        report["proposed_budget"]=PROPOSED_BUDGET;report["source_phase_limits"]={"CPU":{"observed":list(inherited_cpu),"chosen":list(cpu)},
            "AS":{"observed":list(inherited_as),"chosen":[address,address]},"cumulative_CPU_used":spent,"outer_wall_elapsed":elapsed,
            "outer_wall_remaining":remaining,"cumulative":True,"no_budget_reset":True};save()
        host=host_module.Host(out,report,save)
        parent=search.admit_search(records["experiment"],parent_inputs,products,modules,
            current_inputs={n:current[n] for n in parent_inputs if n.startswith("engines/")},admission_source=pair("search_admission.py"),
            evidence_root=str(roots["experiment"]),preprocess=preprocess,compile_identity=compile_identity,
            storage_evidence={"raw":originals["storage_evidence"],"root":str(roots["storage_evidence"]),"products":storage_products},semantic_callback=semantic_callback)
        parent=no_tid.admit_no_tid(parent,records["startup_evidence"],startup_inputs,startup_products,modules,
            current_inputs={n:current[n] for n in startup_inputs if n.startswith("engines/")},admission_source=pair("no_tid_admission.py"),
            parent_admission_module=search,parent_admission_source=pair("search_admission.py"),bridge_source=pair("no_tid_runtime.py"),
            evidence_root=str(roots["startup_evidence"]),preprocess=preprocess,compile_identity=compile_identity,semantic_callback=semantic_callback,startup_callback=startup_callback)
        square_frozen=base.unified_sources({n:frozen_sources[n] for n in parent.input_pins},square_inputs)
        parent=square.admit_square_successor(parent,records["square_evidence"],square_frozen,square_products,modules,
            current_inputs={n:current[n] for n in square_frozen if n.startswith("engines/")},admission_source=pair("square_successor_admission.py"),
            parent_admission_module=no_tid,parent_admission_source=pair("no_tid_admission.py"),bridge_source=pair("square_successor_runtime.py"),
            evidence_root=str(roots["square_evidence"]),preprocess=preprocess,compile_identity=compile_identity,semantic_callback=semantic_callback,startup_callback=startup_callback)
        report["fresh_square_parent"]=parent.to_record();save()
        token=admission.admit_structural(parent,cost,structural_products,modules,frozen_inputs=frozen_sources,current_inputs=current,
            admission_source=pair("structural_admission.py"),parent_admission_module=square,parent_admission_source=pair("square_successor_admission.py"),
            bridge_source=pair("structural_carrier.py"),evidence_root=str(cost_root),preprocess=preprocess,
            compile_identity=compile_identity,observations_callback=observations_callback,startup_callback=startup_callback,
            variant=variant,cohort_raw=cohort_raw,whole_receipt_raw=whole_raw,whole_products=whole_products,whole_evidence_root=str(whole_root))
        named,accepted=carrier.prepare_carrier(token,admission_module=admission,admission_source=pair("structural_admission.py"),
            bridge_source=pair("structural_carrier.py"),runtime=runtime,packaging=modules["packaging"],codec=modules["structural_codec"],
            frozen_inputs={n:frozen_sources[n] for n in token.input_pins})
        build=out/"carrier";build.mkdir()
        for n,d in named.items():base.write(build,n,d)
        (build/"program").chmod(0o700)
        report.update(source_admitted=True,native_admitted=True,package_generation_admitted=True,admission=token.to_record(),carrier=admission.inventory(named),expected=accepted.expected);save()
        cases,coverage=shared.fixture_cases()
        fixture,receipt=carrier.render_rules(token,cases,admission_module=admission,admission_source=pair("structural_admission.py"),
            preprocess_board=preprocess_board,shared=shared,minifier=modules["minifier"],lexical=modules["lexical"])
        path=out/"rules";path.mkdir();base.write(path,"fixture.c",fixture)
        rule_report={**receipt,"coverage":coverage,"complete":False,"modes":[]}
        def save_rules():(path/"rules.json").write_text(json.dumps(rule_report,indent=2)+"\n")
        save_rules()
        for mode,extra in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
            binary=path/("probe-"+mode)
            _,compiled=run(["cc","-std=c11","-O1","-g0","-fno-builtin","-msse4.2","-mcx16",*extra,str(path/"fixture.c"),"-o",str(binary)],path,"structural-rules-compile-"+mode)
            output,executed=run([str(binary)],path,"structural-rules-run-"+mode)
            rule_report["modes"].append({"mode":mode,"native":pin(binary.read_bytes()),"compile":compiled,"execute":executed,**shared._compare_output(output,cases)});save_rules()
        rule_report.update(complete=True,compiled=True,executed=True,rules_qualified=True);save_rules()
        report.update(rules_qualified=True,rules=pin((path/"rules.json").read_bytes()));save()
        require(all(base.normalized(current_root/n)==d and base.safe(frozen,n)==d for n,d in frozen_sources.items() if n.startswith("engines/")),"source closure changed before full runtime")
        host.close();closed=True
        require(report.get("host_cleanup")=={"unsettled_commands":0,"errors":[]},"source commands did not settle naturally")
        limits=runtime.execution_limits(accepted,runtime.effective_available_bytes(),wall_seconds=PROPOSED_BUDGET["runtime_wall"])
        usage=resource.getrusage(resource.RUSAGE_SELF)
        limits=runtime_handoff_limits(base,limits,resource.getrlimit(resource.RLIMIT_CPU),resource.getrlimit(resource.RLIMIT_AS),
            usage.ru_utime+usage.ru_stime,time.monotonic()-started,infinity=resource.RLIM_INFINITY)
        report["runtime_limits"]=limits;save()
        observed=runtime.run_runtime(accepted,build,out/"runtime",limits)
        require(all(base.safe(frozen,n)==d for n,d in frozen_sources.items()),"frozen source tree changed")
        require(all(base.normalized(current_root/n)==d for n,d in current.items()),"current full source closure changed")
        require(all(base.safe(build,n)==d for n,d in named.items()),"actual new carrier changed")
        report.update(runtime=pin((out/"runtime/runtime.json").read_bytes()),runtime_counts=observed["counts"],
            fresh_full_artifact_runtime=observed["complete"] and observed["owned_remaining"]==0,
            size_qualified=accepted.expected["whole_bytes"]<=4096,
            physical_placement_qualified=observed["execution_host"]["test_physical_envelope_observed"],
            current_frozen_closure_unchanged=True,carrier_unchanged=True)
        require(report["rules_qualified"] and report["fresh_full_artifact_runtime"],"structural full-P4 observations incomplete")
    except BaseException as error:
        body_error=error
        report["failure"]={"type":type(error).__name__,"message":str(error)}
        raise
    finally:
        terminal.finish_report(None if closed else host,report,save,body_error)
    require(report["complete"],"structural full-P4 qualification incomplete")
    print(json.dumps({n:report[n] for n in ("complete","rules_qualified","fresh_full_artifact_runtime","size_qualified","physical_placement_qualified","selected")}),flush=True)


def deepcopy_data(value):return json.loads(json.dumps(value))


if __name__=="__main__":main()
