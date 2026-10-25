#!/usr/bin/env python3
"""Compose exact qualified protocol-D natives with unchanged dedicated fixed v3.

This driver owns only composition/admission/provenance. Decoder, codec, linker
script, native source and compiler flags are frozen inputs and remain unchanged.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
EXPECTED_REPORT="17d7e72ecb66440d84e96dcb2f7051873e2efcb3ee2d31df3c0fab4ecee52275"
EXPECTED_OLD_REPORT="e49edad36b00c8f21d07e15e4d567e9f017a8a26ad1de846ff67ba9457d0f5e0"
EXPECTED_TRANSFORM="459516acd435f4f78bcc32f35e8250b0b98fea58744795dbff1bbca3f6be6993"
V3_RECIPE={"build.py":"fe43b4c59a571b125812bc805dc90cf1d9f37289519b8d4ecfa959dbad2a5241",
    "loader.c":"8a6a9cb93ae484400056852c5bc406be1cc15dc7b8df6b0a57e6d6330a2e4094",
    "image.ld":"93934099212b944b20c2f7840ee87e4817311c4f87fddbb2b3f91db28776cf99",
    "codec.py":"17165d1cb16eaba8916833741bfa229d196c3ad07ca391c14b94288a3cdc0866",
    "test_runtime.py":"43c02d5b89afa3cf56d39dbab1e1e8f429c1b24d64b48ebb1d45ab51a577403d"}
DEDICATED={"scalar-shipping":(7665,"790864a3dc2632e040ef0ad639d541e1c384512211a04fc82388698491a694fe"),
    "hq-shipping":(7918,"f5db18be38d5807b4dca47b8316ca94763f37947520d365706f2ccefce8511ac")}
ADMITTED={
    "scalar-shipping":(8476,"ba2d42473ca25a944b85da18f74f32eae18e68112010948a0e7c2dc0c69a7c5c",8763,0x401f89),
    "hq-shipping":(8864,"09917666d5862c4f17ed77e33453000f608a7d83aa47f16f8726a063ec5f31ce",9081,0x4020c6),
}


def sha(data):return hashlib.sha256(data).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)


def admit(data,form,base):
    size,expected,_,entry=ADMITTED[form]
    if len(data)!=size or sha(data)!=expected:raise ValueError("unknown protocol-D image: "+form)
    parsed=base.elf(data)
    segments=[
        {"type":1,"flags":5,"offset":0,"vaddr":0x400000,"paddr":0x400000,"filesz":size,"memsz":size,"align":4096},
        {"type":1,"flags":6,"offset":0,"vaddr":0x403000,"paddr":0x403000,"filesz":0,"memsz":175092,"align":4096},
        {"type":0x6474e551,"flags":6,"offset":0,"vaddr":0,"paddr":0,"filesz":0,"memsz":0,"align":8},
    ]
    if parsed["entry"]!=entry or parsed["segments"]!=segments or any(parsed[key] for key in ("section_offset","section_size","section_count","section_names")):
        raise ValueError("unadmitted protocol-D ELF layout")
    return {**parsed,"image_base":0x400000,"image_size":size,"image_pages":0x3000,
            "bss_base":0x403000,"bss_size":175092,"bss_pages":0x2b000,
            "guard_base":0x3ff000,"reserve_size":0x30000,"upper_guard":0x42e000}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-root",type=Path,required=True)
    parser.add_argument("--loader-root",type=Path,required=True)
    parser.add_argument("--protocol-index",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/".git").exists() for p in (out,*out.parents)):
        parser.error("--out must be new, absolute and outside Git")
    protocol=args.protocol_root.resolve(strict=True);loader=args.loader_root.resolve(strict=True)
    campaign_data=(protocol/"results.json").read_bytes()
    if sha(campaign_data)!=EXPECTED_REPORT:raise ValueError("unknown qualified protocol campaign")
    campaign=json.loads(campaign_data)
    index_data=args.protocol_index.read_bytes();index=json.loads(index_data.decode("utf-8-sig"))
    if index["reports"]["campaign"]!=EXPECTED_REPORT or not index["all_runtime_native_identities_match"]:
        raise ValueError("protocol qualification index mismatch")
    old_data=(protocol/"recipe/d-build.json").read_bytes()
    if sha(old_data)!=EXPECTED_OLD_REPORT:raise ValueError("unexpected original D source lineage")
    old=json.loads(old_data)
    selected={r["id"].removeprefix("tiny-D-"):r for r in campaign["D"] if r["form"]=="protocol" and r["profile"]=="shipping"}
    baseline={r["id"].removeprefix("tiny-D-"):r for r in campaign["D"] if r["form"]=="baseline" and r["profile"]=="shipping"}
    if set(selected)!=set(ADMITTED) or set(baseline)!=set(ADMITTED):raise ValueError("unexpected protocol candidate set")
    out.mkdir(parents=True)
    report={"schema":1,"complete":False,"scope":"exact protocol-D plus unchanged dedicated v3 fixed decoder; no additive size inference",
            "protocol_campaign_sha256":sha(campaign_data),"original_D_build_sha256":sha(old_data),"engines":[],"negative_decoder_controls":[],
            "runtime_validation":"pending","rules_eligibility":"unproven; actual whole file must be <=4096"}
    try:
        write(out/"inputs/protocol-results.json",campaign_data)
        write(out/"inputs/protocol-qualification-index.json",index_data)
        write(out/"inputs/original-D-build.json",old_data)
        write(out/"recipe/build.py",Path(__file__).read_bytes())
        for name in ("build.py","loader.c","image.ld","codec.py","test_runtime.py"):
            data=(loader/"recipe"/name).read_bytes();write(out/"loader-recipe"/name,data)
            if sha(data)!=V3_RECIPE[name]:raise ValueError("unqualified dedicated v3 recipe: "+name)
        frozen_loader=json.loads((loader/"build.json").read_text())
        write(out/"inputs/dedicated-v3-build.json",(loader/"build.json").read_bytes())
        for name,expected in frozen_loader["recipe_sha256"].items():
            if sha((out/"loader-recipe"/name).read_bytes())!=expected:raise ValueError("dedicated v3 recipe drift: "+name)
        base=module("compose_v3_builder",out/"loader-recipe/build.py")
        codecs=module("compose_v3_codec",out/"loader-recipe/codec.py")
        report["tools"]={"compiler_version":base.run(["cc","--version"])["stdout"],"python":sys.version}
        for name in ("transform.py","span.c.in","position.c.in","go-loop.c.in"):
            write(out/"protocol-recipe"/name,(protocol/"recipe"/name).read_bytes())
        if sha((out/"protocol-recipe/transform.py").read_bytes())!=EXPECTED_TRANSFORM:raise ValueError("protocol transformer drift")
        transformer=module("compose_protocol_transform",out/"protocol-recipe/transform.py")
        frozen_original={}
        for name,expected in old["source_sha256"].items():
            data=(protocol/"recipe/D"/name).read_bytes()
            if sha(data)!=expected:raise ValueError("original frozen D source drift: "+name)
            frozen_original[name]=data;write(out/"original-native-recipe"/name,data)
        native_builder=module("compose_native_builder",out/"original-native-recipe/build.py")
        transformed,policy=transformer.transform(frozen_original["runtime.c"],family="D")
        source_hashes=selected["scalar-shipping"]["source_sha256"]
        if source_hashes!=selected["hq-shipping"]["source_sha256"]:raise ValueError("protocol sources differ across modes")
        for name,expected in source_hashes.items():
            data=(protocol/"D-protocol/sources"/name).read_bytes()
            if sha(data)!=expected:raise ValueError("qualified protocol source drift: "+name)
            expected_data=transformed if name=="runtime.c" else frozen_original[name]
            if data!=expected_data:raise ValueError("unqualified source transformation: "+name)
            write(out/"protocol-native-sources"/name,data)
        report["lineage"]={"only_changed_native_source":"runtime.c","frozen_transform_reproduced":True,"policy":policy,
                           "source_sha256":source_hashes,"all_other_native_sources_identical":True}
        for form,record in selected.items():
            native=Path(record["command"][0]).read_bytes()
            original=Path(baseline[form]["command"][0]).read_bytes()
            if sha(native)!=ADMITTED[form][1] or sha(native)!=record["native_sha256"]:raise ValueError("protocol native drift")
            generic=Path(record["packing"]["output"]).read_bytes()
            if len(generic)!=ADMITTED[form][2] or sha(generic)!=record["packing"]["output_sha256"]:raise ValueError("protocol generic control drift")
            old_layout=base.admit(original,form)
            layout=admit(native,form,base)
            rejection={"v3_builder_sha256":sha((out/"loader-recipe/build.py").read_bytes()),"input_sha256":sha(native)}
            try:base.admit(native,form)
            except ValueError as error:rejection.update({"admitted":False,"exception":"ValueError","cause":str(error)})
            else:raise ValueError("unchanged v3 unexpectedly admitted new input")
            changed={key:{"old":old_layout[key],"new":layout[key]} for key in layout if old_layout[key]!=layout[key]}
            base_dir=out/form;base_dir.mkdir()
            write(base_dir/"qualified-native-control",native);write(base_dir/"qualified-generic-control",generic)
            write(base_dir/"original-native-control",original)
            previous=next(e for e in frozen_loader["engines"] if e["id"]==form)
            previous_fixed=next(c for c in previous["candidates"] if c["codec"]=="fixed")
            previous_bytes=Path(previous_fixed["path"]).read_bytes()
            if len(previous_bytes)!=DEDICATED[form][0] or sha(previous_bytes)!=DEDICATED[form][1] or sha(previous_bytes)!=previous_fixed["sha256"]:
                raise ValueError("dedicated independent control drift")
            write(base_dir/"separate-dedicated-control",previous_bytes)
            def normalized(command,root):return [arg.replace(str(root),"SOURCES") for arg in command[:-1]]
            if normalized(record["compile"],protocol/"D-protocol/sources")!=normalized(baseline[form]["compile"],protocol/"D-baseline/sources"):
                raise ValueError("native compiler flags changed from qualified control")
            rebuilds=[]
            for attempt in ("native-first","native-repeat"):
                destination=base_dir/attempt;destination.mkdir()
                command=[arg.replace(str(protocol/"D-protocol/sources"),str(out/"protocol-native-sources")) for arg in record["compile"][:-1]]+[str(destination/"linked")]
                log=base.run(command)
                rebuilt=native_builder.strip_sections((destination/"linked").read_bytes())
                if rebuilt!=native:raise ValueError("qualified protocol native did not independently reproduce")
                write(destination/"x",rebuilt);(destination/"x").chmod(0o755)
                write(destination/"compile.json",(json.dumps(log,indent=2)+"\n").encode())
                rebuilds.append({"path":str(destination/"x"),"sha256":sha(rebuilt),"compile":log})
            payload=codecs.fixed_compress(codecs.bcj(native))
            if codecs.bcj(codecs.fixed_decompress(payload,len(native)),inverse=True)!=native:raise ValueError("combined decoded RX differs")
            candidate=base.compile_loader(base_dir/"fixed",out/"loader-recipe",payload,layout,"fixed","cc")
            repeat_payload=codecs.fixed_compress(codecs.bcj(bytes(rebuilt)))
            repeat=base.compile_loader(base_dir/"fixed-repeat",out/"loader-recipe",repeat_payload,layout,"fixed","cc")
            if candidate["sha256"]!=repeat["sha256"]:raise ValueError("combined whole file did not reproduce")
            candidate.update({"codec":"fixed","reproduction":repeat,"within4096":candidate["bytes"]<=4096,
                              "audit":base.compile_loader(base_dir/"fixed-audit",out/"loader-recipe",payload,layout,"fixed","cc",checkpoint=True)})
            report["engines"].append({"id":form,"input_sha256":sha(native),"input_bytes":len(native),"layout":layout,"old_v3_admission":rejection,
                "reviewed_layout_changes":changed,"native_rebuilds":rebuilds,"generic_control_bytes":len(generic),"generic_control_sha256":sha(generic),
                "separate_dedicated_control_bytes":len(previous_bytes),"separate_dedicated_control_sha256":sha(previous_bytes),"candidates":[candidate]})
            write(out/"build.json",(json.dumps(report,indent=2)+"\n").encode())
        report["frozen_recipe_sha256"]={str(p.relative_to(out)):sha(p.read_bytes()) for folder in ("recipe","loader-recipe","protocol-recipe","original-native-recipe","protocol-native-sources") for p in sorted((out/folder).rglob("*")) if p.is_file()}
        report["complete"]=True
    except Exception as error:
        report["failure"]=repr(error);raise
    finally:write(out/"build.json",(json.dumps(report,indent=2)+"\n").encode())
    print(json.dumps({"out":str(out),"forms":[{"mode":e["id"],"native":e["input_bytes"],"generic":e["generic_control_bytes"],
        "separate_dedicated":e["separate_dedicated_control_bytes"],"combined":e["candidates"][0]["bytes"],"payload":e["candidates"][0]["payload_bytes"]} for e in report["engines"]]},indent=2))


if __name__=="__main__":main()
