#!/usr/bin/env python3
"""Pure cleanup regressions; explicit cost mode generates only a control/cleanup pair.

Unittest discovery starts no tools. Cost mode freezes and replays the actual
current source closure before two fresh native/package observations per case.
No engine is executed and no old producer/admission is modified.
"""
import argparse
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import random
import re
import sys
import unittest

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
D="engines/experiments/tiny-d-submission/"
FILES=("tiny.h","board.c","search.c","runtime.c","start.S","image.ld")
SELECTOR="proved-win-combination"
READER="engines/scripts/production_input.py"
READER_SHA="770ddab0bf142d5d39f5737b04e05c541208efd61a9bdf235d4c1e43c8f1cbc1"
SDK=Path("/home/stemxstudio/rove4k-gcc11-jammy-sdk-20261025-v2")
SDK_AUDIT_SHA="15bab1eba07ad230e72733efca3b4a3f0122b603b39db1167908f76575bc09c4"
SDK_WRAPPER_SHA="6a75516c661192d307949f95f7518b18ca8d9a627b900d956c0acb53cf78821e"

def pin(data):return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
def normalized(data):
    data=data.replace(b"\r\n",b"\n")
    if b"\r" in data:raise ValueError("lone CR in named source")
    return data


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module);return module


def require(value,message):
    if not value:raise ValueError(message)


def write(root,name,data):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)


CLEANUP=load("D_closed_TU_pure",HERE/"closed_tu_cleanup.py")


class ClosedTUProperties(unittest.TestCase):
    def test_complete_inverse_and_every_protected_gap(self):
        rng=random.Random(0xD31)
        for length in range(20,300,7):
            data=bytes(rng.randrange(32,127) for _ in range(length))
            spans=((1,3,"a"),(3,5,"adjacent"),(length-5,length-1,"tail"))
            output,proof=CLEANUP._project(data,spans)
            self.assertEqual(CLEANUP._restore(output,proof),data)
            self.assertEqual(len(data)-len(output),8)
            damaged=bytearray(output);damaged[0]^=1
            with self.assertRaises(ValueError):CLEANUP._restore(bytes(damaged),proof)
            changed=deepcopy(proof);changed["edits"][1]["target"]+=1
            with self.assertRaises(ValueError):CLEANUP._restore(output,changed)
            changed=deepcopy(proof);changed["gaps"][0]["sha256"]="0"*64
            with self.assertRaises(ValueError):CLEANUP._restore(output,changed)

    def test_overlapping_reordered_and_out_of_bounds_spans_rejected(self):
        for rows in (((1,4,"a"),(3,5,"b")),((4,6,"a"),(1,2,"b")),((-1,2,"a"),),((1,50,"a"),),((2,2,"a"),)):
            with self.assertRaises(ValueError):CLEANUP._project(b"0123456789",rows)

    def test_frozen_cohort_and_full_inverse_proof_are_required(self):
        for files in ({},{"main.c":b"int main(void){return 0;}"},{n:b"x" for n in CLEANUP.INPUTS}):
            with self.assertRaises(ValueError):CLEANUP.transform(files)
        with self.assertRaises(ValueError):CLEANUP.restore({}, {"kind":"unknown"})
        self.assertEqual(len(CLEANUP.SPANS),31)
        self.assertEqual(sum(b-a for a,b,_ in CLEANUP.SPANS),1205)
        self.assertEqual({name for name in CLEANUP.ROOTS},{"main","work","memcpy","memset","abort"})
        self.assertTrue(all(name not in {"make forward","walk forward","now forward"} for _,_,name in CLEANUP.SPANS))

    def test_balanced_retention_handles_quoted_delimiters_and_escapes(self):
        data=b'{const char*s="}\\\"{";if(1){x();}}trailing'
        end=CLEANUP._balanced(data,0,b"{",b"}")
        self.assertEqual(data[end:],b"trailing")
        with self.assertRaises(ValueError):CLEANUP._balanced(b'{"}",',0,b"{",b"}")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--report",type=Path)
    parser.add_argument("--report-sha256")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if args.self_test:
        require(args.report is None and args.out is None and args.report_sha256 is None,"pure test cannot also request cost")
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ClosedTUProperties))
        if not result.wasSuccessful():raise SystemExit(1)
        return
    require(sys.platform=="linux" and args.report and args.out and args.report.is_absolute() and args.out.is_absolute(),
        "explicit absolute Linux report/output or --self-test required")
    require(re.fullmatch("[0-9a-f]{64}",args.report_sha256 or "") is not None,"explicit parent receipt SHA-256 required")
    out=args.out.resolve();parent=args.report.resolve().parent
    require(not out.exists() and not any((p/".git").exists() for p in (out,*out.parents)),"new external output required")
    reader_raw=normalized((ROOT/READER).read_bytes())
    require(pin(reader_raw)["sha256"]==READER_SHA,"current bounded source reader differs")
    reader=load("D_closed_TU_initial_reader",ROOT/READER)
    raw=reader.read_regular(args.report,limit=4<<20)
    require(pin(raw)["sha256"]==args.report_sha256,"parent receipt identity differs")
    record=json.loads(raw)
    require(record.get("kind")=="D-structural-search-source-semantic-cost-v1" and
        all(record.get(k) is True for k in ("complete","frozen_execution")) and
        record.get("selected") is False and record.get("host_cleanup")=={"unsettled_commands":0,"errors":[]},
        "complete unselected generation-only parent required")
    names_module=load("D_closed_TU_source_names",ROOT/(D+"source_inputs.py"))
    recipe=json.loads(reader.read_regular(ROOT/names_module.RECIPE,limit=1<<20))
    names=set(names_module.producer_names(recipe))|{D+n for n in (
        "reduce.py","publication.py","process_owner.py","test_startup.py","test_process_owner.py",
        "compressed_bootstrap.py","syscall_arity.py","test_runtime_scaffold.py","valid_input.py",
        "search_compact.py","test_search_compact.py","probe_search_compact.py","check_storage.py","source_inputs.py")}|{"selection/build.json"}
    require(set(record["inputs"])==names,"exact parent frozen source closure required")
    inputs={}
    for name in sorted(names):
        data=reader.read_regular(parent/"inputs"/name,limit=4<<20)
        require(pin(data)==record["inputs"][name],"parent source pin differs: "+name)
        if name.startswith("engines/"):
            require(normalized(reader.read_regular(ROOT/name,limit=4<<20))==data,"parent/current source differs: "+name)
        inputs[name]=data
    require(record.get("source_current_after")=={n:pin(d) for n,d in inputs.items() if n.startswith("engines/")},
        "parent current/frozen source recheck differs")
    selected=[v for v in record["variants"] if v.get("name")==SELECTOR]
    require(len(selected)==1 and selected[0].get("options")==["previous-piece","unsigned-history"],"explicit proved-win selector required")
    variant=selected[0];products={}
    for name in FILES:
        logical=SELECTOR+"/generated-readable/"+name
        data=reader.read_regular(parent/logical,limit=1<<20)
        require(pin(data)==variant["source"][name],"parent readable source differs")
        products[logical]=data
    for name in ("main.c","start.S","image.ld"):
        logical=SELECTOR+"/shipping-inputs/"+name;data=reader.read_regular(parent/logical,limit=1<<20)
        require(pin(data)==variant["shipping"][name],"parent shipping source differs")
        products[logical]=data
    require(len(variant["native"])==2 and variant["native"][0]==variant["native"][1],"parent double native identity differs")
    for index in range(2):
        for file,key in (("linked","linked"),("native","stripped")):
            logical=SELECTOR+"/native-"+str(index)+"/"+file;data=reader.read_regular(parent/logical,limit=1<<20)
            require(pin(data)==variant["native"][index][key],"parent observed native differs")
            products[logical]=data
    package=next(p for p in variant["packages"] if p["route"]=="packed-xz-bcj")
    data=reader.read_regular(parent/SELECTOR/"packed-xz-bcj",limit=1<<20)
    require(pin(data)==package["whole"],"parent control package differs")
    products[SELECTOR+"/packed-xz-bcj"]=data
    source_package=next(p for p in variant["packages"] if p["route"]=="source-jit-compressed")
    data=reader.read_regular(parent/SELECTOR/"source-jit-compressed",limit=1<<20)
    require(pin(data)==source_package["whole"],"parent source-JIT package differs")
    products[SELECTOR+"/source-jit-compressed"]=data
    sdk={}
    if (SDK/"bin/gcc-11").is_file():
        audit=reader.read_regular(SDK/"audit-v2.json",limit=1<<20)
        wrapper=reader.read_regular(SDK/"bin/gcc-11",limit=1<<20)
        require(pin(audit)["sha256"]==SDK_AUDIT_SHA and pin(wrapper)["sha256"]==SDK_WRAPPER_SHA,
            "known audited SDK11 compiler/audit differs")
        sdk={"compiler":str(SDK/"bin/gcc-11"),"audit_path":str(SDK/"audit-v2.json"),
             "audit":pin(audit),"wrapper":pin(wrapper)}
        products["target/audit.json"]=audit;products["target/compiler-wrapper"]=wrapper
    tools={n:normalized(reader.read_regular(ROOT/n,limit=1<<20)) for n in
           (D+"closed_tu_cleanup.py",D+"test_closed_tu_cleanup.py",READER)}
    out.mkdir()
    for name,data in inputs.items():write(out/"inputs",name,data)
    for name,data in products.items():write(out/"parent-products",name,data)
    for name,data in tools.items():write(out/"inputs",name,data)
    write(out,"parent-receipt.json",raw)
    frozen=load("D_closed_TU_frozen_driver",out/"inputs"/(D+"test_closed_tu_cleanup.py"))
    frozen.run_experiment(out,ROOT,record,raw,inputs,products,tools,sdk)


def run_experiment(out,origin,parent,parent_raw,inputs,products,tools,sdk):
    mods={n:load("D_closed_TU_"+n,HERE/(n+".py")) for n in (
        "source","build","storage","test_startup","publication","process_owner","syscall_arity",
        "valid_input","search_compact","reduce","packaging","compressed_bootstrap")}
    source,builder,startup=mods["source"],mods["build"],mods["test_startup"]
    lexical=load("D_closed_TU_lexical",ROOT/"engines/scripts/rename_c.py")
    minifier=load("D_closed_TU_minify",ROOT/"engines/scripts/minify.py")
    packer=load("D_closed_TU_elf",source.CANONICAL/"packer.py")
    reader=load("D_closed_TU_frozen_reader",ROOT/READER)
    hostmod=load("D_closed_TU_commands",ROOT/source.HOST)
    require(pin(normalized(reader.read_regular(ROOT/source.HOST,limit=1<<20)))["sha256"]==source.HOST_SHA,"original command owner differs")
    hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":600,"per_command_wall":40,"parent_CPU":330,"parent_CPU_hard":360,"child_CPU":25,"tool_output_bytes":4<<20}
    report=dict(kind="D-closed-TU-cleanup-native-identity-cost-v1",complete=False,commands=[],
        parent_receipt=pin(parent_raw),selector=SELECTOR,inputs={n:pin(d) for n,d in inputs.items()},
        tools={n:pin(d) for n,d in tools.items()},cases=[],source_reproduced=False,native_reproduced=False,
        full_typed_admission=False,rules_qualified=False,runtime_qualified=False,engine_executed=False,
        selected=False,production_packaging_changed=False,threshold_bytes=100,
        SDK11=sdk, target11_runtime_qualified=False)
    save=lambda:(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=hostmod.Host(out,report,save)
    def run(command,*,cwd,kind,data=None):
        result=host.run(command,cwd=cwd,kind=kind,data=data)
        startup.require_execution(report["commands"][-1],0);return result
    try:
        report["compiler"]=run(["cc","--version"],cwd=out,kind="compiler-version").decode().splitlines()[0]
        profile=source.production().resource_profile("test-p4")
        require(profile.to_record(16)==parent["resource"],"parent resource profile differs")
        base,proof=startup.prepared(source,profile,True,mods["storage"],"prefix")
        require(startup.json_equal(proof,parent["production_proof"]),"complete prepared source proof differs")
        base,proof=mods["process_owner"].transform(base,mods["publication"])
        require(proof==parent["owner_proof"],"owner proof differs")
        base,proof=mods["syscall_arity"].transform(base,mods["process_owner"],mods["publication"],proof,noinline_wake=True,immediate_exit=True)
        require(proof==parent["arity_proof"],"arity proof differs")
        base,proof=mods["valid_input"].transform(base,mods["syscall_arity"],mods["process_owner"],mods["publication"],proof)
        require(proof==parent["valid_proof"],"valid-input proof differs")
        base,proof=mods["search_compact"].transform(base,mods["valid_input"],mods["syscall_arity"],mods["process_owner"],mods["publication"],proof,options=("previous-piece","unsigned-history"))
        variant=next(v for v in parent["variants"] if v["name"]==SELECTOR)
        require(proof==variant["proof"] and all(base[n]==products[SELECTOR+"/generated-readable/"+n] for n in FILES),"complete best source derivation differs")
        flags=builder.native_flags(profile);units=("main.c","start.S")
        require(flags==variant["flags"] and list(units)==variant["units"],"exact compiler recipe differs")
        readable=out/"generated-readable";readable.mkdir()
        for n,d in base.items():write(readable,n,d)
        cpp=run(["cc","-E","-P",*flags,"-I",str(readable),"-x","c","-"],cwd=readable,kind="fresh-single-preprocess",
            data=b''.join(('#include "'+n+'"\n').encode() for n in source.UNITS if n.endswith('.c')))
        entry=run(["cc","-E","-P","-x","assembler-with-cpp",str(readable/"start.S")],cwd=readable,kind="fresh-entry-preprocess")
        emitted={"main.c":minifier.compact_source(cpp,"c"),"start.S":entry,"image.ld":base["image.ld"]}
        renames=variant["legacy_renames"]
        selected=json.loads(inputs["selection/build.json"])
        require(renames==selected["identifier_native_gate"]["accepted_renames"],"selected legacy source map differs")
        require(not set(renames.values()).intersection(lexical._ANY_WORD.findall(emitted["main.c"].decode())),"legacy identifier capture")
        mapped={"main.c":emitted["main.c"]}
        for old,new in renames.items():mapped=lexical._replace(mapped,old,new)
        emitted.update(mapped);trial_index=0
        def digest(c_files,label):
            nonlocal trial_index
            directory=out/("gate-"+str(trial_index));trial_index+=1;directory.mkdir()
            for n,d in {**emitted,**c_files}.items():write(directory,n,d)
            run(["cc",*flags,*[str(directory/n) for n in units],"-Wl,-T,"+str(directory/"image.ld"),"-o",str(directory/"linked")],cwd=directory,kind="fresh-native-source-gate-"+str(label))
            return pin((directory/"linked").read_bytes())["sha256"]
        reduced,reduction=mods["reduce"].reduce_sources({"main.c":emitted["main.c"]},digest,lexical,
            reserve=lexical._ANY_WORD.findall((entry+emitted["image.ld"]).decode()))
        require(reduction==variant["reduction"],"full source reduction replay differs")
        emitted.update(reduced)
        require(all(emitted[n]==products[SELECTOR+"/shipping-inputs/"+n] for n in emitted),"actual final shipping source differs")
        report["source_reproduced"]=True
        shipping=out/"shipping-inputs";shipping.mkdir()
        for n,d in emitted.items():write(shipping,n,d)
        images=[]
        for index in range(2):
            directory=out/("native-"+str(index));directory.mkdir()
            run(["cc",*flags,*[str(shipping/n) for n in units],"-Wl,-T,"+str(shipping/"image.ld"),"-o",str(directory/"linked")],cwd=directory,kind="fresh-native-repeat-"+str(index))
            linked=(directory/"linked").read_bytes();native=packer.strip_native(linked);write(directory,"native",native)
            require(linked==products[SELECTOR+"/native-"+str(index)+"/linked"] and native==products[SELECTOR+"/native-"+str(index)+"/native"],"entire observed parent native identity differs")
            builder.kernel_geometry(packer,linked,profile.workers);builder.kernel_geometry(packer,native,profile.workers);images.append(native)
        require(images[0]==images[1],"double native differs");native=images[0]
        report.update(native=pin(native),native_reproduced=True,compiler_flags=flags,units=list(units))

        cleaned,cleanup_proof=CLEANUP.transform(emitted)
        require(CLEANUP.restore(cleaned,cleanup_proof)==emitted,"complete cleanup inverse differs")
        require(CLEANUP.restore(cleaned,json.loads(json.dumps(cleanup_proof)))==emitted,
                "serialized cleanup proof inverse differs")
        report["cleanup_proof"]=cleanup_proof
        report["scope"]="frozen source replay, native identity and repeated package cost only"
        report["target11_scope"]="known audited Jammy11.4 SDK on Noble host; compilation only"
        target_control=None
        for name,files in (("control",emitted),("cleanup",cleaned)):
            directory=out/name;directory.mkdir()
            for n,d in files.items():write(directory/"shipping-inputs",n,d)
            observed=[]
            if name=="control":
                observed=[dict(linked=variant["native"][i]["linked"],
                    stripped=variant["native"][i]["stripped"],
                    command=next(c for c in report["commands"] if c["kind"]=="fresh-native-repeat-"+str(i)))
                    for i in range(2)]
            else:
                for index in range(2):
                    attempt=directory/("native-"+str(index));attempt.mkdir()
                    run(["cc",*flags,*[str(directory/"shipping-inputs"/n) for n in units],
                        "-Wl,-T,"+str(directory/"shipping-inputs/image.ld"),"-o",str(attempt/"linked")],
                        cwd=attempt,kind="cleanup-native-repeat-"+str(index))
                    linked=(attempt/"linked").read_bytes();restored=packer.strip_native(linked)
                    write(attempt,"native",restored)
                    require(linked==products[SELECTOR+"/native-"+str(index)+"/linked"] and
                            restored==native,"cleanup must preserve the entire GCC13 linked/stripped image")
                    builder.kernel_geometry(packer,linked,profile.workers)
                    builder.kernel_geometry(packer,restored,profile.workers)
                    observed.append(dict(linked=pin(linked),stripped=pin(restored),command=report["commands"][-1]))
            row=dict(name=name,shipping={n:pin(d) for n,d in files.items()},
                native_rebuilds=observed,native_identity=True,packages=[],SDK11=[])
            if sdk:
                if name=="control":
                    report["target11_compiler"]=run([sdk["compiler"],"--version"],cwd=out,
                        kind="target11-version").decode().splitlines()[0]
                for index in range(2):
                    attempt=directory/("target11-"+str(index));attempt.mkdir()
                    run([sdk["compiler"],*flags,*[str(directory/"shipping-inputs"/n) for n in units],
                        "-Wl,-T,"+str(directory/"shipping-inputs/image.ld"),"-o",str(attempt/"linked")],
                        cwd=attempt,kind="target11-"+name+"-repeat-"+str(index))
                    linked=(attempt/"linked").read_bytes();restored=packer.strip_native(linked)
                    write(attempt,"native",restored)
                    builder.kernel_geometry(packer,linked,profile.workers)
                    builder.kernel_geometry(packer,restored,profile.workers)
                    identity=dict(linked=pin(linked),stripped=pin(restored))
                    if target_control is None:target_control=identity
                    require(identity==target_control,"SDK11 control/cleanup complete native identity differs")
                    row["SDK11"].append(dict(**identity,command=report["commands"][-1]))
            for route in ("source-jit","source-jit-compressed","packed-xz-bcj"):
                repetitions=[]
                for index in range(2):
                    if route=="source-jit":whole,detail=mods["packaging"].package_source(files,flags,units)
                    elif route=="source-jit-compressed":
                        whole,detail=mods["compressed_bootstrap"].package_source(files,flags,units,mods["packaging"])
                    else:whole,detail=mods["packaging"].package_native(native,"xz-bcj")
                    decoded=lzma.decompress(whole[detail["header_bytes"]:])
                    if route=="packed-xz-bcj":require(decoded==native,"entire packaged ELF inverse differs")
                    else:
                        bundle=json.loads(decoded) if route=="source-jit" else ast.literal_eval(ast.parse(decoded).body[1].value)
                        require(bundle==dict(files={n:d.decode() for n,d in sorted(files.items())},
                            flags=flags,units=list(units)),"actual whole source bundle inverse differs")
                    repetitions.append(dict(whole=pin(whole),package=detail))
                    write(directory,route+"-"+str(index),whole)
                    if name=="control" and route in ("source-jit-compressed","packed-xz-bcj"):
                        require(whole==products[SELECTOR+"/"+route],"strict parent control whole differs")
                require(repetitions[0]==repetitions[1],"double whole source package differs")
                row["packages"].append(dict(route=route,**repetitions[0],reproduced=True,
                    actual_whole_inverse=True,engine_executed=False))
            report["cases"].append(row);save()
        control,candidate=report["cases"]
        report["whole_savings"]={a["route"]:a["whole"]["bytes"]-b["whole"]["bytes"]
            for a,b in zip(control["packages"],candidate["packages"])}
        report["source_current_after"]={n:pin(normalized(reader.read_regular(origin/n,limit=4<<20)))
            for n in {**inputs,**tools} if n.startswith("engines/")}
        require(report["source_current_after"]=={n:pin(d) for n,d in {**inputs,**tools}.items() if n.startswith("engines/")},
            "source changed during finite cleanup experiment")
        if sdk:
            require(pin(reader.read_regular(Path(sdk["compiler"]),limit=1<<20))==sdk["wrapper"] and
                    pin(reader.read_regular(Path(sdk["audit_path"]),limit=1<<20))==sdk["audit"],
                    "known audited SDK wrapper/audit changed during compile-only job")
        require(len(report["cases"])==2,"finite control/cleanup pair incomplete")
        report["complete"]=True
    except BaseException as error:
        report["failure"]=dict(type=type(error).__name__,message=str(error));raise
    finally:
        try:host.close()
        except BaseException as error:
            report["complete"]=False;report["cleanup_failure"]=dict(type=type(error).__name__,message=str(error));raise
        finally:
            if report.get("host_cleanup",{}).get("errors") or report.get("host_cleanup",{}).get("unsettled_commands"):
                report["complete"]=False
            save()
    print(json.dumps(dict(complete=report["complete"],cases=len(report["cases"]),
        source_raw_saving=1205,whole_savings=report["whole_savings"],engine_executed=False)),flush=True)


if __name__=="__main__":main()
