#!/usr/bin/env python3
"""Pure filter regressions, or an explicit four-case generation-only cost job.

Import/unittest discovery never generates artifacts or starts tools. Cost mode
requires an explicit pinned parent receipt and a new external output root.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import random
import re
import shutil
import shlex
import struct
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
D="engines/experiments/tiny-d-submission/"
FILES=("tiny.h","board.c","search.c","runtime.c","start.S","image.ld")
MODES=("control","jcc","rip","union")
SELECTOR="proved-win-combination"
READER="engines/scripts/production_input.py"
READER_SHA="770ddab0bf142d5d39f5737b04e05c541208efd61a9bdf235d4c1e43c8f1cbc1"


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


FILTER=load("D_operand_pure",HERE/"native_operand_filter.py")


def bootstrap_inverse(whole,metadata):
    """Execute exactly the shipping inverse prefix, stopping before memfd/exec."""
    header=whole[:metadata["header_bytes"]].decode()
    require(header.startswith("#!/bin/sh\n"),"self-contained shell bootstrap required")
    words=shlex.split(header[len("#!/bin/sh\n"):])
    require(len(words)==5 and words[:3]==["exec","python3","-c"] and words[4]=="$0",
        "fixed self-contained bootstrap argv differs")
    code=words[3];anchor="\nf=os.memfd_create("
    require(code.count(anchor)==1,"unique pre-memfd inverse boundary required")
    namespace={}
    def bounded_open(name,mode):
        require(name=="<counted-whole>" and mode=="rb","bootstrap attempted an unexpected read")
        return io.BytesIO(whole)
    namespace["open"]=bounded_open
    with patch.object(sys,"argv",["case","<counted-whole>"]):
        exec(compile(code.split(anchor,1)[0],"<exact-shipping-inverse-prefix>","exec"),namespace)
    require(isinstance(namespace.get("b"),(bytes,bytearray)),"shipping inverse produced no native bytes")
    return bytes(namespace["b"])


class NativeOperandProperties(unittest.TestCase):
    def test_arbitrary_data_and_truncated_jcc_round_trip(self):
        rng=random.Random(0xD4)
        for length in (*range(80),127,255,1024,4096):
            raw=bytes(rng.randrange(256) for _ in range(length))
            for suffix in (b"",b"\x0f\x80",b"\x0f\x8f\xff\xff\xff"):
                original=raw+suffix
                self.assertEqual(FILTER.restore(FILTER.normalize(original,"jcc",()),"jcc",()),original)

    def test_jcc_markers_skip_operands_and_wrap_modulo_32(self):
        for opcode in range(0x80,0x90):
            for displacement in (0,1,0x7fffffff,0x80000000,0xfffffff9,0xffffffff,0x800f800f):
                original=b"ABC"+bytes((15,opcode))+struct.pack("<I",displacement)+b"Z"
                filtered=FILTER.normalize(original,"jcc",())
                self.assertEqual(filtered[3:5],original[3:5])
                self.assertEqual(int.from_bytes(filtered[5:9],"little"),(displacement+9)&0xffffffff)
                self.assertEqual(FILTER.restore(filtered,"jcc",()),original)
        nested=bytes.fromhex("0f 80 0f 8f 00 00 0f 81 ff ff ff ff")
        self.assertEqual(FILTER.restore(FILTER.normalize(nested,"jcc",()),"jcc",()),nested)

    def test_rip_map_bounds_overlap_and_union_arbitrary_round_trip(self):
        rng=random.Random(0x128)
        raw=bytes(rng.randrange(256) for _ in range(160))
        offsets=(4,30,64,112)
        for mode in ("rip","union"):
            self.assertEqual(FILTER.restore(FILTER.normalize(raw,mode,offsets),mode,offsets),raw)
        for bad in ((4,6),(30,4),(-1,),(157,),(4,4)):
            with self.assertRaises(ValueError):FILTER.normalize(raw,"rip",bad)

    def test_map_codec_is_canonical_and_bounded(self):
        offsets=(4,25,255,1024)
        blob=FILTER.encode_map(offsets)
        self.assertEqual(FILTER.decode_map(blob,2048),offsets)
        for bad in (blob[:-1],blob+b"x",b"\xff\xff",b"\x01\x00\xff\xff"):
            with self.assertRaises(ValueError):FILTER.decode_map(bad,2048)

    def test_binutils_map_binds_rx_bytes_and_excludes_trailing_immediate(self):
        native=bytearray(512);native[:16]=b"\x7fELF\x02\x01\x01"+bytes(9)
        struct.pack_into("<HHIQQQIHHHHHH",native,16,2,62,1,0x400100,64,0,0,64,56,1,0,0,0)
        struct.pack_into("<IIQQQQQQ",native,64,1,5,0,0x400000,0x400000,512,512,4096)
        native[256:263]=bytes.fromhex("48 8b 05 04 00 00 00")
        native[272:282]=bytes.fromhex("c7 05 04 00 00 00 04 00 00 00")
        dump=("400100: 48 8b 05 04 00 00 00 mov rax,QWORD PTR [rip+0x4] # 40010b\n"
              "400110: c7 05 04 00 00 00 04 00 00 00 mov DWORD PTR [rip+0x4],0x4 # 40011e\n")
        offsets,proof=FILTER.decode_rip_map(bytes(native),dump)
        self.assertEqual(offsets,(259,))
        self.assertEqual(len(proof["excluded"]),1)
        self.assertIn("immediate",proof["excluded"][0]["reason"])
        damaged=bytearray(native);damaged[259]^=1
        with self.assertRaisesRegex(ValueError,"bytes differ"):
            FILTER.decode_rip_map(bytes(damaged),dump)
        with self.assertRaisesRegex(ValueError,"overlapping"):
            FILTER.decode_rip_map(bytes(native),dump+"400104: 00 nop\n")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--report",type=Path)
    parser.add_argument("--report-sha256")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if args.self_test:
        require(args.report is None and args.out is None and args.report_sha256 is None,"pure test cannot also request cost")
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeOperandProperties))
        if not result.wasSuccessful():raise SystemExit(1)
        return
    require(sys.platform=="linux" and args.report and args.out and args.report.is_absolute() and args.out.is_absolute(),
        "explicit absolute Linux report/output or --self-test required")
    require(re.fullmatch("[0-9a-f]{64}",args.report_sha256 or "") is not None,"explicit parent receipt SHA-256 required")
    out=args.out.resolve();parent=args.report.resolve().parent
    require(not out.exists() and not any((p/".git").exists() for p in (out,*out.parents)),"new external output required")
    reader_raw=normalized((ROOT/READER).read_bytes())
    require(pin(reader_raw)["sha256"]==READER_SHA,"current bounded source reader differs")
    reader=load("D_operand_initial_reader",ROOT/READER)
    raw=reader.read_regular(args.report,limit=4<<20)
    require(pin(raw)["sha256"]==args.report_sha256,"parent receipt identity differs")
    record=json.loads(raw)
    require(record.get("kind")=="D-structural-search-source-semantic-cost-v1" and
        all(record.get(k) is True for k in ("complete","frozen_execution")) and
        record.get("selected") is False and record.get("host_cleanup")=={"unsettled_commands":0,"errors":[]},
        "complete unselected generation-only parent required")
    names_module=load("D_operand_source_names",ROOT/(D+"source_inputs.py"))
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
    tools={n:normalized(reader.read_regular(ROOT/n,limit=1<<20)) for n in
           (D+"native_operand_filter.py",D+"test_native_operand_filter.py",READER)}
    out.mkdir()
    for name,data in inputs.items():write(out/"inputs",name,data)
    for name,data in products.items():write(out/"parent-products",name,data)
    for name,data in tools.items():write(out/"inputs",name,data)
    write(out,"parent-receipt.json",raw)
    frozen=load("D_operand_frozen_driver",out/"inputs"/(D+"test_native_operand_filter.py"))
    frozen.run_experiment(out,ROOT,record,raw,inputs,products,tools)


def run_experiment(out,origin,parent,parent_raw,inputs,products,tools):
    mods={n:load("D_operand_"+n,HERE/(n+".py")) for n in (
        "source","build","storage","test_startup","publication","process_owner","syscall_arity",
        "valid_input","search_compact","reduce","packaging")}
    source,builder,startup=mods["source"],mods["build"],mods["test_startup"]
    lexical=load("D_operand_lexical",ROOT/"engines/scripts/rename_c.py")
    minifier=load("D_operand_minify",ROOT/"engines/scripts/minify.py")
    packer=load("D_operand_elf",source.CANONICAL/"packer.py")
    reader=load("D_operand_frozen_reader",ROOT/READER)
    hostmod=load("D_operand_commands",ROOT/source.HOST)
    require(pin(normalized(reader.read_regular(ROOT/source.HOST,limit=1<<20)))["sha256"]==source.HOST_SHA,"original command owner differs")
    hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":300,"per_command_wall":40,"parent_CPU":150,"parent_CPU_hard":180,"child_CPU":25,"tool_output_bytes":4<<20}
    report=dict(kind="D-native-operand-four-case-cost-v1",complete=False,commands=[],
        parent_receipt=pin(parent_raw),selector=SELECTOR,inputs={n:pin(d) for n,d in inputs.items()},
        tools={n:pin(d) for n,d in tools.items()},cases=[],source_reproduced=False,native_reproduced=False,
        full_typed_admission=False,rules_qualified=False,runtime_qualified=False,engine_executed=False,
        selected=False,production_packaging_changed=False,threshold_bytes=100)
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
        objdump=Path(shutil.which("objdump")).resolve(strict=True)
        report["decoder"]={"path":str(objdump),"program":pin(reader.read_regular(objdump,limit=16<<20)),
            "version":run([str(objdump),"--version"],cwd=out,kind="decoder-version").decode().splitlines()[0]}
        disassembly=run([str(objdump),"-d","-Mintel","--insn-width=16",str(out/"native-0/linked")],cwd=out,kind="decode-fresh-linked-instructions")
        write(out,"disassembly.txt",disassembly)
        offsets,map_proof=FILTER.decode_rip_map(native,disassembly)
        report.update(decoded=pin(disassembly),rip_map=map_proof,rip_offsets=list(offsets))
        baseline=None
        for mode in MODES:
            case_offsets=offsets if mode in ("rip","union") else ()
            first,detail=FILTER.package(native,mode,case_offsets,mods["packaging"])
            second,again=FILTER.package(native,mode,case_offsets,mods["packaging"])
            require(first==second and detail==again,"double whole package differs")
            require(FILTER.restore_package(first,detail,mods["packaging"])==native,"exact complete ELF restoration differs")
            require(FILTER.restore_package(second,again,mods["packaging"])==native,"second complete ELF restoration differs")
            require(bootstrap_inverse(first,detail)==native and bootstrap_inverse(second,again)==native,
                "actual self-contained inverse prefix did not restore the entire original ELF")
            if mode=="control":
                require(first==products[SELECTOR+"/packed-xz-bcj"],"actual complete control bootstrap/package differs")
                baseline=len(first)
            write(out,"case-"+mode,first)
            saving=baseline-len(first)
            report["cases"].append(dict(mode=mode,whole=pin(first),package=detail,reproduced=True,
                exact_ELF_restoration=True,actual_bootstrap_inverse_checked=True,memfd_or_engine_executed=False,
                net_saving_bytes=saving,retained=mode!="control" and saving>=100))
            save()
        report["source_current_after"]={n:pin(normalized(reader.read_regular(origin/n,limit=4<<20)))
            for n in {**inputs,**tools} if n.startswith("engines/")}
        require(report["source_current_after"]=={n:pin(d) for n,d in {**inputs,**tools}.items() if n.startswith("engines/")},"source changed during finite experiment")
        require(len(report["cases"])==4,"finite four-case portfolio incomplete")
        report["complete"]=True
    except BaseException as error:
        report["failure"]=dict(type=type(error).__name__,message=str(error));raise
    finally:
        try:host.close()
        except BaseException as error:
            report["complete"]=False;report["cleanup_failure"]=dict(type=type(error).__name__,message=str(error));raise
        finally:
            if report.get("host_cleanup",{}).get("errors") or report.get("host_cleanup",{}).get("unsettled_commands"):report["complete"]=False
            save()
    print(json.dumps(dict(complete=report["complete"],cases=len(report["cases"]),retained=[r["mode"] for r in report["cases"] if r["retained"]],engine_executed=False)),flush=True)


if __name__=="__main__":main()
