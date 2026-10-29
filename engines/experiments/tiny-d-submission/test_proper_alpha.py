#!/usr/bin/env python3
"""A finite protected-alpha control/candidate cost experiment, not admission.

Pure discovery starts no tools. The explicit CLI freezes known receipts/source,
freshly derives the full control, then measures two native and whole builds per
case. No engine, semantic fixture, large TT, deployment or old guard is changed.
"""
import argparse
from copy import deepcopy
import json
import lzma
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
D="engines/experiments/tiny-d-submission/"
SHARED=D+"test_exact_clock_predicate.py"
SHARED_SHA="5c1c8621600cf49e0e332e904bfeb10296369e774a450fe89f99baad3d92bb89"
PARENT_SHA="e207630b4272c82e147a765d3e3c19ce8fcbfae50e13c19a7cb0f40c4fb0ee43"
CLEANUP_SHA="cc70e03f62e540fa087e3a651bfe6c80b8957f0902284bf884586002dce75fed"
FILES=("main.c","start.S","image.ld")
READABLE=("tiny.h","board.c","search.c","runtime.c","start.S","image.ld")
SELECTOR="proved-win-combination"


def load(name,path,data=None):
    path=Path(path).resolve();data=path.read_bytes() if data is None else data
    module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
    exec(compile(data,str(path),"exec"),module.__dict__);return module


def support():
    import hashlib
    data=(ROOT/SHARED).read_bytes().replace(b"\r\n",b"\n")
    if b"\r" in data or hashlib.sha256(data).hexdigest()!=SHARED_SHA:
        raise ValueError("exact bounded source/CPU driver support required")
    return load("D_proper_alpha_support",ROOT/SHARED,data)


def helper():
    return load("D_proper_alpha_helper",HERE/"proper_alpha.py")


def lexical():
    return load("D_proper_alpha_lexical",ROOT/"engines/scripts/rename_c.py")


class ProperAlphaProperties(unittest.TestCase):
    def test_GNU_attributes_are_finite_and_reference_attributes_rejected(self):
        alpha=helper()
        rows=alpha.attribute_inventory(b"static __attribute__((noinline)) void f(void){}")
        self.assertEqual(rows[0]["source"],"__attribute__((noinline))")
        self.assertFalse(rows[0]["reference_arguments"])
        for data in (b"",b"__attribute__((cleanup(cleanupFoo))) int x;",
                     b"__attribute__((alias(\"target\"))) int x;",
                     b"__attribute__((section(\".code\"))) int x;",
                     b"__attribute__((noinline)) __attribute__((noinline)) int x;"):
            with self.assertRaises(ValueError):alpha.attribute_inventory(data)

    def test_protected_alpha_inverse_preserves_attributes_ASM_and_exports(self):
        alpha,lex=helper(),lexical()
        files={"main.c":b'''__attribute__((noinline)) static int functionLong(int argumentLong){
const char*opaqueLong="argumentLong asmSymbol";return argumentLong+!!opaqueLong;}
int main(void){return functionLong(0);}''',
               "start.S":b".global _start\ncall main\n", "image.ld":b"ENTRY(_start)\n"}
        expected={n:(len(d),alpha.pin(d)["sha256"]) for n,d in files.items()}
        with patch.dict(alpha.INPUTS,expected,clear=True):
            candidate,proof=alpha.transform(files,lex)
            self.assertEqual(alpha.restore(candidate,json.loads(json.dumps(proof)),lex),files)
            self.assertNotIn("noinline",proof["renames"])
            self.assertNotIn("argumentLong",proof["renames"])
            self.assertNotIn("main",proof["renames"])
            self.assertIn("functionLong",proof["renames"])
            self.assertIn(b"__attribute__((noinline))",candidate["main.c"])
            damaged=deepcopy(proof);damaged["compiler_attributes_unchanged"]=1
            with self.assertRaises(ValueError):alpha.restore(candidate,damaged,lex)
            damaged=deepcopy(proof);damaged["renames"]["noinline"]="ce"
            with self.assertRaises(ValueError):alpha.restore(candidate,damaged,lex)

    def test_projection_rejects_tampering_of_every_complement(self):
        alpha=helper();data=b"longName+x+longName;"
        output,proof=alpha._project(data,[(0,8,"longName"),(11,19,"longName")],{"longName":"q"})
        self.assertEqual(alpha._restore(output,proof),data)
        for i in range(len(proof["gaps"])):
            damaged=deepcopy(proof);damaged["gaps"][i]["sha256"]="0"*64
            with self.assertRaises(ValueError):alpha._restore(output,damaged)
        damaged=deepcopy(proof);damaged["edits"][0]["target"]=True
        with self.assertRaises(ValueError):alpha._restore(output,damaged)

    def test_exact_production_input_required(self):
        alpha,lex=helper(),lexical()
        with self.assertRaises(ValueError):alpha.transform({n:b"x" for n in FILES},lex)
        with self.assertRaises(ValueError):alpha.restore({}, {"kind":"unknown"},lex)
        self.assertFalse(alpha.same({"accepted":True},{"accepted":1}))

    def test_shared_CPU_owner_never_raises_child_hard_limit(self):
        shared=support()
        self.assertEqual(shared.child_cpu_limit(20,30),20)
        self.assertEqual(shared.bounded_cpu_limits(300,330,150,180),(150,180))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--report",type=Path)
    parser.add_argument("--cleanup-report",type=Path)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args();shared=support()
    if args.self_test:
        shared.require(args.report is None and args.cleanup_report is None and args.out is None,
                       "pure tests cannot also request external work")
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProperAlphaProperties))
        if not result.wasSuccessful():raise SystemExit(1)
        return
    shared.require(sys.platform=="linux" and args.report and args.cleanup_report and args.out
        and all(p.is_absolute() for p in (args.report,args.cleanup_report,args.out)),
        "explicit known Linux receipts and fresh absolute external output required")
    out=args.out.resolve();parent_root=args.report.resolve().parent;cleanup_root=args.cleanup_report.resolve().parent
    shared.require(not out.exists() and not any((p/".git").exists() for p in (out,*out.parents)),"new external output required")
    reader_data=shared.normalized((ROOT/shared.READER).read_bytes())
    shared.require(shared.pin(reader_data)["sha256"]==shared.READER_SHA,"bounded reader identity differs")
    reader=load("D_proper_alpha_initial_reader",ROOT/shared.READER,reader_data)
    parent_raw=reader.read_regular(args.report,limit=4<<20)
    cleanup_raw=reader.read_regular(args.cleanup_report,limit=4<<20)
    shared.require(shared.pin(parent_raw)["sha256"]==PARENT_SHA and shared.pin(cleanup_raw)["sha256"]==CLEANUP_SHA,
                   "exact original structural and cleanup receipts required")
    parent,cleanup=json.loads(parent_raw),json.loads(cleanup_raw)
    shared.require(parent.get("kind")=="D-structural-search-source-semantic-cost-v1"
        and parent.get("complete") is True and parent.get("frozen_execution") is True
        and parent.get("host_cleanup")=={"unsettled_commands":0,"errors":[]}
        and cleanup.get("kind")=="D-closed-TU-cleanup-native-identity-cost-v1"
        and all(cleanup.get(k) is True for k in ("complete","source_reproduced","native_reproduced"))
        and cleanup.get("parent_receipt")==shared.pin(parent_raw)
        and cleanup.get("host_cleanup")=={"unsettled_commands":0,"errors":[]},"complete original parent evidence required")
    shared.require(set(parent["inputs"])==set(cleanup["inputs"]),"original full source closure differs")
    inputs={}
    for name,want in parent["inputs"].items():
        shared.require(name=="selection/build.json" or name.startswith("engines/") and ".." not in Path(name).parts,
                       "named engine source input required")
        data=reader.read_regular(parent_root/"inputs"/name,limit=4<<20)
        shared.require(shared.pin(data)==want==cleanup["inputs"][name],"original frozen source differs")
        if name.startswith("engines/"):
            shared.require(shared.normalized(reader.read_regular(ROOT/name,limit=4<<20))==data,"current/frozen source differs: "+name)
        inputs[name]=data
    for name in (D+"proper_alpha.py",D+"test_proper_alpha.py",SHARED,D+"closed_tu_cleanup.py",shared.READER):
        shared.require(name not in inputs,"new finite source/tool closure overlaps parent")
        inputs[name]=shared.normalized(reader.read_regular(ROOT/name,limit=4<<20))
    shared.require(shared.pin(inputs[D+"closed_tu_cleanup.py"])==cleanup["tools"][D+"closed_tu_cleanup.py"],"old cleanup helper differs")
    choices=[v for v in parent["variants"] if v.get("name")==SELECTOR]
    shared.require(len(choices)==1 and choices[0].get("options")==["previous-piece","unsigned-history"],"full structural selector differs")
    selected=choices[0];products={}
    for category,names,pins in (("generated-readable",READABLE,selected["source"]),("shipping-inputs",FILES,selected["shipping"])):
        for name in names:
            logical=SELECTOR+"/"+category+"/"+name;data=reader.read_regular(parent_root/logical,limit=1<<20)
            shared.require(shared.pin(data)==pins[name],"actual original source product differs")
            products[logical]=data
    shared.require([c["name"] for c in cleanup["cases"]]==["control","cleanup"],"finite prior cleanup pair differs")
    for name,want in cleanup["cases"][1]["shipping"].items():
        data=reader.read_regular(cleanup_root/"cleanup/shipping-inputs"/name,limit=1<<20)
        shared.require(shared.pin(data)==want,"actual prior cleaned source differs")
        products["cleanup/"+name]=data
    out.mkdir()
    for name,data in inputs.items():shared.write(out/"inputs",name,data)
    for name,data in products.items():shared.write(out/"parent-products",name,data)
    shared.write(out,"parent-receipt.json",parent_raw);shared.write(out,"cleanup-receipt.json",cleanup_raw)
    frozen=load("D_proper_alpha_frozen",out/"inputs"/(D+"test_proper_alpha.py"))
    frozen.run_snapshot(out,ROOT,parent,cleanup,inputs,products)


def run_snapshot(out,origin,parent,cleanup_parent,inputs,products):
    shared=support();alpha=helper();require,pin,write=shared.require,shared.pin,shared.write
    mods={n:load("D_proper_alpha_"+n,HERE/(n+".py")) for n in (
        "source","build","test_startup","storage","publication","process_owner","syscall_arity",
        "valid_input","search_compact","reduce","packaging","compressed_bootstrap","closed_tu_cleanup")}
    source,builder,startup=mods["source"],mods["build"],mods["test_startup"]
    lex=lexical();minifier=load("D_proper_alpha_minify",ROOT/"engines/scripts/minify.py")
    packer=load("D_proper_alpha_packer",source.CANONICAL/"packer.py")
    reader=load("D_proper_alpha_reader",ROOT/shared.READER)
    require(pin(inputs[source.HOST])["sha256"]==source.HOST_SHA,"verified identical command-owner module differs")
    hostmod=load("D_proper_alpha_owner",ROOT/source.HOST,inputs[source.HOST])
    report=dict(kind="D-protected-alpha-native-whole-cost-v1",complete=False,frozen_execution=True,
        parent_receipt=pin((out/"parent-receipt.json").read_bytes()),cleanup_receipt=pin((out/"cleanup-receipt.json").read_bytes()),
        inputs={n:pin(d) for n,d in inputs.items()},commands=[],cases=[],source_reproduced=False,
        semantic_qualified=False,full_typed_admission=False,rules_qualified=False,runtime_qualified=False,
        engine_executed=False,selected=False,target11_runtime_qualified=False,SDK11_compiled=False,
        old_native_map_changed=False,production_packaging_changed=False,
        owner_module=dict(path=source.HOST,pin=pin(inputs[source.HOST]),current_equals_original_frozen=True),
        scope="two proper-alpha source cases; fresh native/whole cost only, no old byte-identity waiver")
    save=lambda:(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    host=None;save()
    def run(command,*,cwd,kind,data=None):
        output=host.run(command,cwd=cwd,kind=kind,data=data)
        row=report["commands"][-1];startup.require_execution(row,0)
        stderr=reader.read_regular(Path(row["stderr"]["path"]),limit=4<<20)
        require(pin(stderr)=={k:row["stderr"][k] for k in ("bytes","sha256")},"original compiler stderr identity differs")
        require(not stderr,"compiler diagnostics reject this finite class, including unknown/ignored attributes")
        return output
    try:
        import resource
        inherited=resource.getrlimit(resource.RLIMIT_CPU)
        effective=shared.bounded_cpu_limits(240,270,*inherited,infinity=resource.RLIM_INFINITY)
        child=shared.child_cpu_limit(*effective,infinity=resource.RLIM_INFINITY)
        report["CPU_limits"]=dict(inherited=list(inherited),effective_parent=list(effective),child=child)
        hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":480,"per_command_wall":60,
            "parent_CPU":effective[0],"parent_CPU_hard":effective[1],"child_CPU":child,"tool_output_bytes":4<<20}
        host=hostmod.Host(out,report,save)
        report["compiler"]=run(["cc","--version"],cwd=out,kind="compiler-version").decode().splitlines()[0]
        profile=source.production().resource_profile("test-p4")
        require(profile.to_record(16)==parent["resource"],"actual parent profile differs")
        base,proof=startup.prepared(source,profile,True,mods["storage"],"prefix")
        require(startup.json_equal(proof,parent["production_proof"]),"complete production proof differs")
        base,proof=mods["process_owner"].transform(base,mods["publication"])
        require(alpha.same(proof,parent["owner_proof"]),"complete owner proof differs")
        base,proof=mods["syscall_arity"].transform(base,mods["process_owner"],mods["publication"],proof,noinline_wake=True,immediate_exit=True)
        require(alpha.same(proof,parent["arity_proof"]),"complete arity proof differs")
        base,proof=mods["valid_input"].transform(base,mods["syscall_arity"],mods["process_owner"],mods["publication"],proof)
        require(alpha.same(proof,parent["valid_proof"]),"complete valid-line proof differs")
        base,proof=mods["search_compact"].transform(base,mods["valid_input"],mods["syscall_arity"],mods["process_owner"],mods["publication"],proof,
            options=("previous-piece","unsigned-history"))
        selected=next(v for v in parent["variants"] if v["name"]==SELECTOR)
        require(alpha.same(proof,selected["proof"]) and all(base[n]==products[SELECTOR+"/generated-readable/"+n] for n in READABLE),
                "actual complete six-file source derivation differs")
        flags=builder.native_flags(profile);units=["main.c","start.S"]
        require(flags==selected["flags"]==cleanup_parent["compiler_flags"] and units==selected["units"]==cleanup_parent["units"],
                "actual flags/units differ")
        raw=out/"generated-readable"
        for n,d in base.items():write(raw,n,d)
        cpp=run(["cc","-E","-P",*flags,"-I",str(raw),"-x","c","-"],cwd=raw,kind="fresh-control-preprocess",
            data=b''.join(('#include "'+n+'"\n').encode() for n in source.UNITS if n.endswith('.c')))
        entry=run(["cc","-E","-P","-x","assembler-with-cpp",str(raw/"start.S")],cwd=raw,kind="fresh-control-entry")
        mapped=shared.rename(minifier.compact_source(cpp,"c"),selected["legacy_renames"],lex)
        pruned,rounds=mods["reduce"].prune_typedefs({"main.c":mapped},lex)
        stages=selected["reduction"]["stages"]
        require(len(stages)==2 and stages[0]["status"]=="accepted" and stages[0]["kind"]=="unused-scalar-typedefs"
            and stages[1]["status"]=="rejected-native-differs" and stages[1]["kind"]=="batch-alpha"
            and rounds==stages[0]["rounds"],"original accepted spelling stage differs")
        full={"main.c":pruned["main.c"],"start.S":entry,"image.ld":base["image.ld"]}
        require(all(full[n]==products[SELECTOR+"/shipping-inputs/"+n] for n in FILES),"fresh original full compiler source differs")
        control,cleanup_proof=mods["closed_tu_cleanup"].transform(full)
        require(alpha.same(cleanup_proof,cleanup_parent["cleanup_proof"])
                and all(control[n]==products["cleanup/"+n] for n in FILES),"same complete 31-span cleanup differs")
        candidate,alpha_proof=alpha.transform(control,lex)
        require(alpha.restore(candidate,json.loads(json.dumps(alpha_proof)),lex)==control,"new protected alpha full inverse differs")
        # Both cases start after the exact same cleanup. Inverse alpha FIRST
        # restores that cleaned compiler input, then the old cleanup restores
        # the complete fresh original TU, without editing old span metadata.
        require(mods["closed_tu_cleanup"].restore(alpha.restore(candidate,alpha_proof,lex),cleanup_proof)==full,
                "alpha-to-cleanup-to-original full inverse differs")
        report.update(production_proof=parent["production_proof"],structural_proof=proof,
            readable={n:pin(d) for n,d in base.items()},fresh_cpp=pin(cpp),fresh_entry=pin(entry),
            typedef_rounds=rounds,cleanup_proof=cleanup_proof,alpha_proof=alpha_proof,
            compiler_flags=flags,units=units,resource=profile.to_record(16),source_reproduced=True,
            family_applicability=alpha_proof["family_applicability"])
        for name,files in (("control",control),("proper-alpha",candidate)):
            directory=out/name
            for n,d in files.items():write(directory/"shipping-inputs",n,d)
            row=dict(name=name,shipping={n:pin(d) for n,d in files.items()},native=[],packages=[])
            images=[]
            for index in range(2):
                attempt=directory/("native-"+str(index));attempt.mkdir()
                run(["cc",*flags,*[str(directory/"shipping-inputs"/n) for n in units],
                     "-Wl,-T,"+str(directory/"shipping-inputs/image.ld"),"-o",str(attempt/"linked")],
                    cwd=attempt,kind=name+"-native-"+str(index))
                linked=(attempt/"linked").read_bytes();native=packer.strip_native(linked);write(attempt,"native",native)
                geometries=dict(linked=builder.kernel_geometry(packer,linked,profile.workers),
                                native=builder.kernel_geometry(packer,native,profile.workers))
                images.append((linked,native));row["native"].append(dict(linked=pin(linked),stripped=pin(native),geometry=geometries,
                    command=report["commands"][-1]))
            require(images[0]==images[1],"two complete fresh native builds differ")
            if name=="control":
                old=cleanup_parent["cases"][1]["native_rebuilds"][0]
                require({k:row["native"][0][k] for k in ("linked","stripped")}=={k:old[k] for k in ("linked","stripped")},
                        "actual unchanged control native differs")
            for route in ("source-jit","source-jit-compressed","packed-xz-bcj"):
                repetitions=[]
                for index in range(2):
                    if route=="source-jit":whole,detail=mods["packaging"].package_source(files,flags,units)
                    elif route=="source-jit-compressed":whole,detail=mods["compressed_bootstrap"].package_source(files,flags,units,mods["packaging"])
                    else:whole,detail=mods["packaging"].package_native(images[0][1],"xz-bcj")
                    decoder=lzma.LZMADecompressor();decoded=decoder.decompress(whole[detail["header_bytes"]:])
                    require(decoder.eof and not decoder.unused_data,"complete payload EOF/no-tail inverse required")
                    if route=="packed-xz-bcj":require(decoded==images[0][1],"whole native inverse differs")
                    else:
                        if route=="source-jit":bundle=json.loads(decoded)
                        else:
                            import ast
                            bundle=ast.literal_eval(ast.parse(decoded).body[1].value)
                        require(bundle==dict(files={n:d.decode() for n,d in sorted(files.items())},flags=flags,units=units),
                                "complete canonical source bundle inverse differs")
                    write(directory,route+"-"+str(index),whole);repetitions.append(dict(whole=pin(whole),package=detail))
                require(repetitions[0]==repetitions[1],"two whole package constructions differ")
                if name=="control":
                    old=next(p for p in cleanup_parent["cases"][1]["packages"] if p["route"]==route)
                    require(repetitions[0]["whole"]==old["whole"],"fresh unchanged control whole differs")
                row["packages"].append(dict(route=route,**repetitions[0],reproduced=True,actual_whole_inverse=True))
            report["cases"].append(row);save()
        a,b=report["cases"]
        report["whole_savings"]={x["route"]:x["whole"]["bytes"]-y["whole"]["bytes"] for x,y in zip(a["packages"],b["packages"])}
        report["any_whole_improvement"]=any(v>0 for v in report["whole_savings"].values())
        report["new_machinecode"]=a["native"][0]["linked"]!=b["native"][0]["linked"]
        report["semantic_not_run_reason"]="new source class requires separately authorized semantics/type/runtime admission; no old map waiver"
        report["source_current_after"]={n:pin(shared.normalized(reader.read_regular(origin/n,limit=4<<20)))
                                        for n in inputs if n.startswith("engines/")}
        require(report["source_current_after"]=={n:pin(d) for n,d in inputs.items() if n.startswith("engines/")},
                "current/frozen source changed during experiment")
        for command in report["commands"]:startup.require_execution(command,0)
        report["complete"]=True
    except BaseException as error:
        report["complete"]=False;report["failure"]=dict(type=type(error).__name__,message=str(error));raise
    finally:
        try:
            if host is not None:host.close()
        except BaseException as error:
            report["complete"]=False;report["cleanup_failure"]=dict(type=type(error).__name__,message=str(error));raise
        finally:
            if report.get("host_cleanup",{}).get("errors") or report.get("host_cleanup",{}).get("unsettled_commands"):
                report["complete"]=False
            save()
    print(json.dumps(dict(complete=report["complete"],cases=len(report["cases"]),whole_savings=report["whole_savings"],
        semantic_qualified=False,engine_executed=False,selected=False)),flush=True)


if __name__=="__main__":main()
