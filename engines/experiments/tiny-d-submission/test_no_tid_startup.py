#!/usr/bin/env python3
"""One source-owned three-case D startup cost experiment; no engine execution.

Pure discovery/--self-test starts no tools. Explicit cost mode reproduces the
canonical source and the exact e207 control before control/no-TID/no-TID-tail
compilation. New startup native identities never enter an old admission map.
"""
import argparse
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import re
import shutil
import sys
import unittest

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
D="engines/experiments/tiny-d-submission/"
SELECTOR="proved-win-combination"
PARENT_SHA="e207630b4272c82e147a765d3e3c19ce8fcbfae50e13c19a7cb0f40c4fb0ee43"
READER="engines/scripts/production_input.py"
READER_SHA="770ddab0bf142d5d39f5737b04e05c541208efd61a9bdf235d4c1e43c8f1cbc1"
FILES=("tiny.h","board.c","search.c","runtime.c","start.S","image.ld")
SHIPPING=("main.c","start.S","image.ld")
MODES=(("control",None),("no-tid",False),("no-tid-tail",True))
EXPECTED_READABLE={
 "tiny.h":{"bytes":2970,"sha256":"fac1d3f165d01e01efc7c6a2f89ee8767661e6d3aad0478febad21fa3814bf9e"},
 "board.c":{"bytes":10361,"sha256":"ecd9d567a1f6c5ee185012a70915ab63c741bbf68b7a294d1604334c59db4e62"},
 "search.c":{"bytes":5909,"sha256":"73ba9dbdf23906cff90e6098ee0903bdf38b4f95e826871042281c9894de6344"},
 "runtime.c":{"bytes":15555,"sha256":"0d80984d9bbb32969eb1c6ee76105a3742c09d7baa0a679195dde573e3aa183e"},
 "start.S":{"bytes":845,"sha256":"4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b"},
 "image.ld":{"bytes":446,"sha256":"38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b"},
}


def require(value,message):
    if not value:raise ValueError(message)


def pin(data):return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def normalized(data):
    data=data.replace(b"\r\n",b"\n")
    require(b"\r" not in data,"lone CR in named source")
    return data


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result
    spec.loader.exec_module(result);return result


def write(root,name,data):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)


def helper():return load("D_no_tid_source",HERE/"no_tid_startup.py")


def bounded_cpu_limits(requested_soft,requested_hard,current_soft,current_hard,*,infinity=-1):
    require(all(type(v) is int and (v==infinity or v>=0) for v in
            (requested_soft,requested_hard,current_soft,current_hard)),"CPU limits must be integers")
    def minimum(*items):
        finite=[v for v in items if v!=infinity]
        return min(finite) if finite else infinity
    hard=minimum(requested_hard,current_hard);soft=minimum(requested_soft,current_soft,hard)
    require(soft==infinity or soft>0,"inherited CPU limit permits no work")
    require(hard==infinity or (hard>0 and soft!=infinity and soft<=hard),"ordered positive CPU limits required")
    return soft,hard


def child_entry_rsp(initial,actions):
    """SysV entry math only; this does not execute clone or assembly."""
    require(type(initial) is int and 0<=initial<16,"mod16 stack state required")
    value=initial
    for action in actions:
        if action=="pop":value=(value+8)%16
        elif action in ("mov","jmp"):pass
        elif action=="call":value=(value-8)%16
        else:raise ValueError("unknown finite stack action")
    return value


def flags_without_tid(flags):
    require(flags==0x350f00,"exact old clone flags required")
    return flags & ~(0x100000|0x200000)


def assert_worker_id_header(before,after):
    require(before==after and before.count(b"int id,depth;")==1,
            "actual combined Worker.id/depth declaration or unchanged header differs")


def assert_actual_candidate(control,output,proof,source,*,nonreturning):
    require(source.restore(output,json.loads(json.dumps(proof)))==control,"complete startup source inverse differs")
    require(all(output[n]==control[n] for n in ("board.c","search.c","image.ld")),
            "startup change touched board/search/linker logic")
    require(b"ids" not in re.findall(rb"[A-Za-z_][A-Za-z_0-9]*",output["tiny.h"]+output["runtime.c"]+output["start.S"]),
            "obsolete TID identifier remains")
    assert_worker_id_header(control["tiny.h"],output["tiny.h"])
    assembly=output["start.S"]
    require(b"0x50f00" in assembly and b"0x350f00" not in assembly,"clone flag specialization differs")
    require(b".global _start" in assembly and b".global spawn" in assembly and b"call main" in assembly,
            "entry/spawn root lost")
    if nonreturning:
        compact=re.sub(rb"\s+",b"",assembly)
        require(b"pop%rax;mov(%rsp),%rdi;jmp*%rax" in compact or
                b"pop%raxmov(%rsp),%rdijmp*%rax" in compact,"single-pop nonreturning tail required")
        require(child_entry_rsp(0,("pop","mov","jmp"))==8,"nonreturning worker ABI entry alignment differs")
    # Negative proofs/output must not be admitted under the new class either.
    damaged=deepcopy(proof);damaged["kind"]="old-selected-D-native-map"
    try:source.restore(output,damaged)
    except (ValueError,KeyError,TypeError):pass
    else:raise ValueError("old-kind startup inverse accepted")
    broken={**output,"runtime.c":output["runtime.c"]+b"\nextern int ids[4];\n"}
    try:source.restore(broken,proof)
    except (ValueError,KeyError,TypeError):pass
    else:raise ValueError("stale-TID output accepted")
    stale={**output,"tiny.h":output["tiny.h"]+b"\nextern long spawn(void(*)(void*),void*,void*,int*);\n"}
    try:source.restore(stale,proof)
    except (ValueError,KeyError,TypeError):pass
    else:raise ValueError("stale four-argument prototype accepted")
    return dict(full_serialized_inverse=True,board_search_linker_unchanged=True,
        obsolete_tid_absent=True,worker_id_retained=True,negative_old_kind=True,
        negative_stale_tid=True,negative_stale_spawn_prototype=True,nonreturning=nonreturning,
        expected_child_rsp_mod16=8,raw_clone_executed=False)


class NoTidProperties(unittest.TestCase):
    def test_actual_worker_id_combined_declarator_is_preserved(self):
        actual=b"typedef struct{int id,depth; Move best;}Worker;"
        assert_worker_id_header(actual,actual)
        invented=b"typedef struct{int id;int depth; Move best;}Worker;"
        for before,after in ((invented,invented),(actual,invented),(actual,actual+b"changed")):
            with self.assertRaises(ValueError):assert_worker_id_header(before,after)

    def test_exact_flag_delta_retains_every_non_tid_bit(self):
        old,new=0x350f00,flags_without_tid(0x350f00)
        self.assertEqual(new,0x50f00)
        self.assertEqual(old^new,0x100000|0x200000)
        for bit in (0x100,0x200,0x400,0x800,0x10000,0x40000):self.assertTrue(new&bit)
        self.assertFalse(new&0x80000)  # CLONE_SETTLS absent before/after.
        with self.assertRaises(ValueError):flags_without_tid(0x350e00)

    def test_tail_entry_alignment_requires_one_pop_and_no_call(self):
        self.assertEqual(child_entry_rsp(0,("pop","pop","call")),8)
        self.assertEqual(child_entry_rsp(0,("pop","mov","jmp")),8)
        self.assertEqual(child_entry_rsp(0,("pop","pop","jmp")),0)
        with self.assertRaises(ValueError):child_entry_rsp(0,("unknown",))

    def test_actual_callback_templates_preserve_entry_stack_math(self):
        source=helper()
        self.assertEqual(source.CALLBACK.count(b"pop "),2)
        self.assertEqual(source.CALLBACK.count(b"call *%rax"),1)
        self.assertEqual(source.TAIL.count(b"pop "),1)
        self.assertIn(b"mov (%rsp),%rdi",source.TAIL)
        self.assertIn(b"jmp *%rax",source.TAIL)
        self.assertNotIn(b"call",source.TAIL)
        self.assertNotIn(b"ret",source.TAIL)
        self.assertEqual(source.UNUSED_REGISTERS,
            b"    mov %rcx,%rdx\n    mov %rcx,%r10\n    xor %r8d,%r8d\n")

    def test_new_spawn_signature_and_fixed_call_drop_only_tid_argument(self):
        source=helper()
        self.assertEqual(source.PROTOTYPE.replace(b",int *",b""),source.PROTOTYPE3)
        self.assertEqual(source.SPAWN_CALL.replace(b",(int *)(ids+created)",b""),source.SPAWN_CALL3)
        self.assertNotIn(b"ids",source.SPAWN_CALL3)
        self.assertNotIn(b"int *",source.PROTOTYPE3)

    def test_startup_splice_inverse_and_protected_complement(self):
        source=helper()
        original=b"root FIRST gap SECOND tail"
        output,proof=source._project(original,[("drop",b"FIRST",b""),("replace",b"SECOND",b"Z")])
        self.assertEqual(source._restore(output,json.loads(json.dumps(proof))),original)
        for damaged in (b"!"+output[1:],output+b"x"):
            with self.assertRaises(ValueError):source._restore(damaged,proof)
        altered=deepcopy(proof);altered["edits"][1]["target"]+=1
        with self.assertRaises(ValueError):source._restore(output,altered)
        altered=deepcopy(proof);altered["gaps"][0]["sha256"]="0"*64
        with self.assertRaises(ValueError):source._restore(output,altered)
        for roles in ([("absent",b"MISSING",b"")],[("a",b"FIRST",b""),("overlap",b"FIRST gap",b"")]):
            with self.assertRaises(ValueError):source._project(original,roles)

    def test_no_nested_cpu_limit_raise(self):
        self.assertEqual(bounded_cpu_limits(300,330,150,180),(150,180))
        self.assertEqual(bounded_cpu_limits(300,330,-1,-1),(300,330))
        self.assertEqual(bounded_cpu_limits(300,330,200,-1),(200,330))
        with self.assertRaises(ValueError):bounded_cpu_limits(300,330,0,0)

    def test_exact_input_domain_and_wrong_proof_rejected(self):
        source=helper()
        self.assertEqual(source.INPUTS,EXPECTED_READABLE)
        for invalid in ({},{n:b"x" for n in FILES}):
            with self.assertRaises(ValueError):source.transform(invalid)
        with self.assertRaises((ValueError,KeyError,TypeError)):source.restore({},dict(kind="old-native-map"))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--report",type=Path)
    parser.add_argument("--report-sha256")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if args.self_test:
        require(args.report is None and args.out is None and args.report_sha256 is None,
                "pure test cannot also request cost")
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NoTidProperties))
        if not result.wasSuccessful():raise SystemExit(1)
        return
    require(sys.platform=="linux" and args.report and args.out and args.report.is_absolute() and
            args.out.is_absolute() and args.report_sha256==PARENT_SHA,"known pinned e207 report/new absolute Linux output required")
    out=args.out.resolve();parent=args.report.resolve().parent
    require(not out.exists() and not any((p/".git").exists() for p in (out,*out.parents)),"new output outside Git required")
    reader_raw=normalized((ROOT/READER).read_bytes())
    require(pin(reader_raw)["sha256"]==READER_SHA,"bounded reader source differs")
    reader=load("D_no_tid_initial_reader",ROOT/READER)
    raw=reader.read_regular(args.report,limit=4<<20)
    require(pin(raw)["sha256"]==PARENT_SHA,"exact structural parent receipt differs")
    record=json.loads(raw)
    require(record.get("kind")=="D-structural-search-source-semantic-cost-v1" and
            all(record.get(k) is True for k in ("complete","frozen_execution")) and
            record.get("selected") is False and record.get("host_cleanup")=={"unsettled_commands":0,"errors":[]},
            "complete unselected structural parent required")
    names_module=load("D_no_tid_names",ROOT/(D+"source_inputs.py"))
    recipe=json.loads(reader.read_regular(ROOT/names_module.RECIPE,limit=1<<20))
    names=set(names_module.producer_names(recipe))|{D+n for n in (
        "reduce.py","publication.py","process_owner.py","test_startup.py","test_process_owner.py",
        "compressed_bootstrap.py","syscall_arity.py","test_runtime_scaffold.py","valid_input.py",
        "search_compact.py","test_search_compact.py","probe_search_compact.py","check_storage.py","source_inputs.py")}|{"selection/build.json"}
    require(set(record["inputs"])==names,"exact recipe-derived parent source closure required")
    inputs={}
    for name in sorted(names):
        data=reader.read_regular(parent/"inputs"/name,limit=4<<20)
        require(pin(data)==record["inputs"][name],"frozen parent source differs: "+name)
        if name.startswith("engines/"):
            require(normalized(reader.read_regular(ROOT/name,limit=4<<20))==data,"current/frozen source differs: "+name)
        inputs[name]=data
    require(record["source_current_after"]=={n:pin(d) for n,d in inputs.items() if n.startswith("engines/")},
            "parent final source check differs")
    variants=[v for v in record["variants"] if v.get("name")==SELECTOR]
    require(len(variants)==1 and variants[0].get("options")==["previous-piece","unsigned-history"],"exact structural selector required")
    variant=variants[0];products={}
    require(variant["source"]==EXPECTED_READABLE,"exact no-TID input source class required")
    for name in FILES:
        logical=SELECTOR+"/generated-readable/"+name;data=reader.read_regular(parent/logical,limit=1<<20)
        require(pin(data)==variant["source"][name],"actual parent readable source differs")
        products[logical]=data
    for name in SHIPPING:
        logical=SELECTOR+"/shipping-inputs/"+name;data=reader.read_regular(parent/logical,limit=1<<20)
        require(pin(data)==variant["shipping"][name],"actual parent shipping source differs")
        products[logical]=data
    require(len(variant["native"])==2 and variant["native"][0]==variant["native"][1],"double parent native identities required")
    for index in range(2):
        for file,key in (("linked","linked"),("native","stripped")):
            logical=SELECTOR+"/native-"+str(index)+"/"+file;data=reader.read_regular(parent/logical,limit=1<<20)
            require(pin(data)==variant["native"][index][key],"actual parent native differs")
            products[logical]=data
    for route in ("packed-xz-bcj","source-jit-compressed"):
        package=next(p for p in variant["packages"] if p["route"]==route)
        data=reader.read_regular(parent/SELECTOR/route,limit=1<<20)
        require(pin(data)==package["whole"],"actual parent whole package differs")
        products[SELECTOR+"/"+route]=data
    tools={n:normalized(reader.read_regular(ROOT/n,limit=1<<20)) for n in
           (D+"no_tid_startup.py",D+"test_no_tid_startup.py",READER)}
    out.mkdir()
    for n,d in {**inputs,**tools}.items():write(out/"inputs",n,d)
    for n,d in products.items():write(out/"parent-products",n,d)
    write(out,"parent-receipt.json",raw)
    frozen=load("D_no_tid_frozen_driver",out/"inputs"/(D+"test_no_tid_startup.py"))
    frozen.run_experiment(out,ROOT,record,raw,inputs,products,tools)


def run_experiment(out,origin,parent,parent_raw,inputs,products,tools):
    mods={n:load("D_no_tid_"+n,HERE/(n+".py")) for n in (
        "source","build","storage","test_startup","publication","process_owner","syscall_arity",
        "valid_input","search_compact","reduce","packaging","compressed_bootstrap")}
    source,builder,startup=mods["source"],mods["build"],mods["test_startup"]
    change=helper();lexical=load("D_no_tid_rename",ROOT/"engines/scripts/rename_c.py")
    minifier=load("D_no_tid_minify",ROOT/"engines/scripts/minify.py")
    packer=load("D_no_tid_packer",source.CANONICAL/"packer.py")
    reader=load("D_no_tid_reader",ROOT/READER)
    hostmod=load("D_no_tid_commands",ROOT/source.HOST)
    require(pin(inputs[source.HOST])["sha256"]==source.HOST_SHA,"original command-owner source differs")
    report=dict(kind="D-no-TID-startup-three-case-source-cost-v1",complete=False,frozen_execution=True,
        parent_receipt=pin(parent_raw),selector=SELECTOR,inputs={n:pin(d) for n,d in inputs.items()},
        tools={n:pin(d) for n,d in tools.items()},commands=[],cases=[],source_reproduced=False,
        control_native_reproduced=False,control_whole_reproduced=False,full_typed_admission=False,
        rules_qualified=False,runtime_qualified=False,engine_executed=False,raw_clone_fixture_executed=False,
        selected=False,old_admission_changed=False,production_packaging_changed=False,
        SDK11_requested=False,scope="fresh canonical and exact control replay; 3 startup source/native/package costs only")
    save=lambda:(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=None
    def run(command,*,cwd,kind,data=None):
        result=host.run(command,cwd=cwd,kind=kind,data=data)
        startup.require_execution(report["commands"][-1],0);return result
    try:
        import resource
        observed=resource.getrlimit(resource.RLIMIT_CPU)
        effective=bounded_cpu_limits(300,330,*observed,infinity=resource.RLIM_INFINITY)
        report["parent_CPU_limits"]=dict(requested=[300,330],observed=list(observed),effective=list(effective),
            infinity=resource.RLIM_INFINITY,cumulative=True,no_budget_reset=True)
        hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":600,"per_command_wall":45,"parent_CPU":effective[0],
                       "parent_CPU_hard":effective[1],"child_CPU":30,"tool_output_bytes":4<<20}
        report["host_construction_complete"]=False;save()
        host=hostmod.Host(out,report,save);report["host_construction_complete"]=True;save()
        compiler=Path(shutil.which("cc") or "").resolve();require(compiler.is_file(),"installed cc required")
        version=run([str(compiler),"--version"],cwd=out,kind="compiler-version").decode().splitlines()[0]
        report["compiler"]=dict(path=str(compiler),version=version,executable=pin(reader.read_regular(compiler,limit=8<<20)))
        profile=source.production().resource_profile("test-p4")
        require(profile.to_record(16)==parent["resource"],"parent resource geometry differs")
        base,proof=startup.prepared(source,profile,True,mods["storage"],"prefix")
        require(startup.json_equal(proof,parent["production_proof"]),"full canonical preparation proof differs")
        base,proof=mods["process_owner"].transform(base,mods["publication"])
        require(proof==parent["owner_proof"],"full owner source proof differs")
        base,proof=mods["syscall_arity"].transform(base,mods["process_owner"],mods["publication"],proof,noinline_wake=True,immediate_exit=True)
        require(proof==parent["arity_proof"],"full syscall-arity source proof differs")
        base,proof=mods["valid_input"].transform(base,mods["syscall_arity"],mods["process_owner"],mods["publication"],proof)
        require(proof==parent["valid_proof"],"full valid-input source proof differs")
        base,proof=mods["search_compact"].transform(base,mods["valid_input"],mods["syscall_arity"],mods["process_owner"],mods["publication"],proof,
                                                    options=("previous-piece","unsigned-history"))
        selected=next(v for v in parent["variants"] if v["name"]==SELECTOR)
        require(proof==selected["proof"] and {n:pin(d) for n,d in base.items()}==EXPECTED_READABLE and
                all(base[n]==products[SELECTOR+"/generated-readable/"+n] for n in FILES),
                "actual six-file structural source derivation differs")
        report.update(source_reproduced=True,resource=profile.to_record(16),source_proof=proof)
        flags=builder.native_flags(profile);units=("main.c","start.S")
        require(flags==selected["flags"] and list(units)==selected["units"],"actual compiler flags/units differ")
        report.update(compiler_flags=flags,units=list(units))
        renames=selected["legacy_renames"]
        require(renames==json.loads(inputs["selection/build.json"])["identifier_native_gate"]["accepted_renames"],
                "legacy32 source identifier map differs")
        for name,tail in MODES:
            if tail is None:readable,stage,pure=base,None,None
            else:
                readable,stage=change.transform(base,nonreturning=tail)
                pure=assert_actual_candidate(base,readable,stage,change,nonreturning=tail)
            directory=out/name;rawdir=directory/"generated-readable";rawdir.mkdir(parents=True)
            for n,d in readable.items():write(rawdir,n,d)
            cpp=run(["cc","-E","-P",*flags,"-I",str(rawdir),"-x","c","-"],cwd=rawdir,kind=name+"-single-preprocess",
                data=b''.join(('#include "'+n+'"\n').encode() for n in source.UNITS if n.endswith('.c')))
            entry=run(["cc","-E","-P","-x","assembler-with-cpp",str(rawdir/"start.S")],cwd=rawdir,kind=name+"-entry-preprocess")
            emitted={"main.c":minifier.compact_source(cpp,"c"),"start.S":entry,"image.ld":readable["image.ld"]}
            require(not set(renames.values()).intersection(lexical._ANY_WORD.findall(emitted["main.c"].decode())),
                    "legacy identifier capture")
            mapped={"main.c":emitted["main.c"]}
            for old,new in renames.items():mapped=lexical._replace(mapped,old,new)
            emitted.update(mapped);gate_index=0
            def digest(c_files,trial):
                nonlocal gate_index
                gate=directory/("gate-"+str(gate_index));gate_index+=1;gate.mkdir()
                for n,d in {**emitted,**c_files}.items():write(gate,n,d)
                run(["cc",*flags,*[str(gate/n) for n in units],"-Wl,-T,"+str(gate/"image.ld"),"-o",str(gate/"linked")],
                    cwd=gate,kind=name+"-source-reduction-gate-"+str(trial))
                return pin((gate/"linked").read_bytes())["sha256"]
            reduced,reduction=mods["reduce"].reduce_sources({"main.c":emitted["main.c"]},digest,lexical,
                reserve=lexical._ANY_WORD.findall((entry+emitted["image.ld"]).decode()))
            emitted.update(reduced)
            if name=="control":
                require(reduction==selected["reduction"] and all(emitted[n]==products[SELECTOR+"/shipping-inputs/"+n] for n in SHIPPING),
                        "full control reducer/final shipping source replay differs")
            shipping=directory/"shipping-inputs";shipping.mkdir()
            for n,d in emitted.items():write(shipping,n,d)
            row=dict(name=name,nonreturning=tail,source={n:pin(d) for n,d in readable.items()},source_stage=stage,
                pure_actual_source_checks=pure,reduction=reduction,shipping={n:pin(d) for n,d in emitted.items()},
                native=[],packages=[],selected=False,engine_executed=False)
            images=[]
            for index in range(2):
                attempt=directory/("native-"+str(index));attempt.mkdir()
                run(["cc",*flags,*[str(shipping/n) for n in units],"-Wl,-T,"+str(shipping/"image.ld"),"-o",str(attempt/"linked")],
                    cwd=attempt,kind=name+"-native-repeat-"+str(index))
                linked=(attempt/"linked").read_bytes();native=packer.strip_native(linked);write(attempt,"native",native)
                builder.kernel_geometry(packer,linked,profile.workers);builder.kernel_geometry(packer,native,profile.workers)
                identity=dict(linked=pin(linked),stripped=pin(native));row["native"].append(dict(**identity,command=report["commands"][-1]))
                if name=="control":
                    require(linked==products[SELECTOR+"/native-"+str(index)+"/linked"] and
                            native==products[SELECTOR+"/native-"+str(index)+"/native"],"entire control native replay differs")
                images.append((linked,native))
            require(images[0]==images[1],"double same-source entire native differs")
            if name=="control":report["control_native_reproduced"]=True
            for route in ("source-jit","source-jit-compressed","packed-xz-bcj"):
                repetitions=[]
                for index in range(2):
                    if route=="source-jit":whole,detail=mods["packaging"].package_source(emitted,flags,units)
                    elif route=="source-jit-compressed":whole,detail=mods["compressed_bootstrap"].package_source(emitted,flags,units,mods["packaging"])
                    else:whole,detail=mods["packaging"].package_native(images[0][1],"xz-bcj")
                    decoded=lzma.decompress(whole[detail["header_bytes"]:])
                    if route=="packed-xz-bcj":require(decoded==images[0][1],"entire counted ELF inverse differs")
                    else:
                        bundle=json.loads(decoded) if route=="source-jit" else ast.literal_eval(ast.parse(decoded).body[1].value)
                        require(bundle==dict(files={n:d.decode() for n,d in sorted(emitted.items())},flags=flags,units=list(units)),
                                "entire counted source/flags/units inverse differs")
                    write(directory,route+"-"+str(index),whole);repetitions.append(dict(whole=pin(whole),package=detail))
                    if name=="control" and route in ("source-jit-compressed","packed-xz-bcj"):
                        require(whole==products[SELECTOR+"/"+route],"exact control whole replay differs")
                require(repetitions[0]==repetitions[1],"two entire counted packages differ")
                row["packages"].append(dict(route=route,**repetitions[0],reproduced=True,actual_whole_inverse=True))
            if name=="control":
                require({p["route"]:p["whole"]["bytes"] for p in row["packages"]}==
                        {"source-jit":7147,"source-jit-compressed":7004,"packed-xz-bcj":5261},"known control costs differ")
                report["control_whole_reproduced"]=True
            report["cases"].append(row);save()
        require(len(report["cases"])==3,"finite three-case portfolio incomplete")
        control=report["cases"][0]
        report["whole_savings"]={row["name"]:{a["route"]:a["whole"]["bytes"]-b["whole"]["bytes"]
            for a,b in zip(control["packages"],row["packages"])} for row in report["cases"][1:]}
        report["native_changes"]={row["name"]:row["native"][0]["linked"]!=control["native"][0]["linked"] for row in report["cases"][1:]}
        report["source_current_after"]={n:pin(normalized(reader.read_regular(origin/n,limit=4<<20)))
            for n in {**inputs,**tools} if n.startswith("engines/")}
        require(report["source_current_after"]=={n:pin(d) for n,d in {**inputs,**tools}.items() if n.startswith("engines/")},
                "executed source/tool closure changed during cost job")
        report["complete"]=True
    except BaseException as error:
        report["failure"]=dict(type=type(error).__name__,message=str(error));raise
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
                         engine_executed=False)),flush=True)


if __name__=="__main__":main()
