#!/usr/bin/env python3
"""Focused frozen independent owner admission replay; no engine execution.

The only child tools are fresh GCC preprocessing/compilation commands. Each
native trial retains unique sources, linked output and stripped image. Old
scaled runtime evidence receives explicit typed validation, never a blanket
nonzero-command exemption. Full artifact runtime/rules remain pending.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module


def safe(root,name):
    relative=Path(name)
    if relative.is_absolute() or ".." in relative.parts:raise ValueError("bounded evidence name required")
    path=root/relative
    for part in (path,*path.parents):
        if part==root:break
        if part.is_symlink():raise ValueError("linked evidence input rejected")
    return path.read_bytes()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment",type=Path,required=True);parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--pure",action="store_true",help="stored typed/source/scaled checks only; no compiler or encoder")
    args=parser.parse_args();out=args.out.resolve();experiment=args.experiment.resolve()
    if (sys.platform!="linux" or platform.machine()!="x86_64" or not args.out.is_absolute() or not args.experiment.is_absolute()
            or out.exists() or any((p/".git").exists() for p in (out,*out.parents))):
        parser.error("absolute experiment and new external output on Linux x86-64 required")
    raw={n:(HERE/n).read_bytes().replace(b"\r\n",b"\n") for n in ("owner_admission.py","test_owner_admission.py","source_inputs.py")}
    out.mkdir();(out/"tools").mkdir()
    for name,data in raw.items():(out/"tools"/name).write_bytes(data)
    frozen=load("D_owner_admission_focused_frozen",out/"tools/test_owner_admission.py")
    frozen.run_snapshot(out,experiment,ROOT,raw,args.pure)


def run_snapshot(out,experiment,current_root,raw,pure):
    admission=load("D_owner_admission_under_test",out/"tools/owner_admission.py")
    source_inputs=load("D_owner_admission_source_inputs",out/"tools/source_inputs.py")
    original=safe(experiment,"results.json");record=json.loads(original)
    recipe=json.loads(safe(experiment,"inputs/"+source_inputs.RECIPE))
    producer=source_inputs.producer_names(recipe)
    inputs={n:safe(experiment,"inputs/"+n) for n in admission.input_names(record,producer)}
    products={n:safe(experiment,n) for n in admission.evidence_names(record,producer)}
    current={n:safe(current_root,n).replace(b"\r\n",b"\n") for n in inputs if n.startswith("engines/")}
    for name,data in {**inputs,**{"products/"+n:d for n,d in products.items()}}.items():
        path=out/"evidence"/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    (out/"original-results.json").write_bytes(original)
    for n,d in current.items():
        path=out/"current"/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(d)
    modules={}
    logical=dict(source="engines/experiments/tiny-d-submission/source.py",builder="engines/experiments/tiny-d-submission/build.py",
        storage="engines/experiments/tiny-d-submission/storage.py",publication="engines/experiments/tiny-d-submission/publication.py",
        owner="engines/experiments/tiny-d-submission/process_owner.py",startup="engines/experiments/tiny-d-submission/test_startup.py",
        checker="engines/experiments/tiny-d-submission/test_process_owner.py",reducer="engines/experiments/tiny-d-submission/reduce.py",
        packaging="engines/experiments/tiny-d-submission/packaging.py",lexical="engines/scripts/rename_c.py",
        minifier="engines/scripts/minify.py",packer="engines/compact/tiny-entry-d/packer.py",
        source_inputs=source_inputs.SELF)
    if admission.BOOTSTRAP in inputs:logical["bootstrap"]=admission.BOOTSTRAP
    for name,path in logical.items():modules[name]=load("D_independent_owner_"+name,out/"evidence"/path)
    host_name="engines/experiments/tcec-scope/build.py"
    if admission.pin(inputs[host_name])["sha256"]!=modules["source"].HOST_SHA:raise ValueError("original command owner differs")
    hostmod=load("D_independent_owner_commands",out/"evidence"/host_name)
    hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":240,"per_command_wall":35,"parent_CPU":120,"parent_CPU_hard":140,"child_CPU":20}
    report=dict(kind="D-process-owner-independent-admission-probe-v1",complete=False,commands=[],frozen_execution=True,
        original_experiment=admission.pin(original),tools={n:admission.pin(d) for n,d in raw.items()},
        source_inputs=admission.inventory(inputs),current_inputs=admission.inventory(current),
        products=admission.inventory(products),full_engines_executed=False,fresh_full_artifact_runtime=False,rules_qualified=False)
    def save():(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=hostmod.Host(out,report,save);counter=0
    def run(command,*,cwd,kind,data=None):
        result=host.run(command,cwd=cwd,kind=kind,data=data)
        return result,dict(report["commands"][-1])
    def preprocess(files,flags,members,label):
        nonlocal counter
        counter+=1;directory=out/("fresh-pp-"+str(counter)+"-"+label);directory.mkdir()
        readable=directory/"readable";readable.mkdir()
        for n,d in files.items():(readable/n).write_bytes(d)
        driver=b''.join(('#include "'+n+'"\n').encode() for n in members)
        main,row=run(["cc","-E","-P",*flags,"-I",str(readable),"-x","c","-"],cwd=readable,
            kind="independent-preprocess-single-"+label,data=driver)
        entry,entry_row=run(["cc","-E","-P","-x","assembler-with-cpp",str(readable/"start.S")],cwd=readable,
            kind="independent-preprocess-entry-"+label)
        return dict(kind="D-owner-preprocess-v1",label=label,input_pins=admission.inventory(files),flags=flags,members=members,
            driver=driver,readable_dir=str(readable),commands=[row,entry_row],outputs={"main.c":main,"start.S":entry})
    def compile_identity(files,flags,units,label):
        nonlocal counter
        counter+=1;directory=out/("fresh-native-"+str(counter)+"-"+label.replace("/","-"));directory.mkdir()
        for n,d in files.items():(directory/n).write_bytes(d)
        linked_path=directory/"linked";native_path=directory/"native"
        _,row=run(["cc",*flags,*[str(directory/n) for n in units],"-Wl,-T,"+str(directory/"image.ld"),"-o",str(linked_path)],
            cwd=directory,kind="independent-compile-"+label.replace("/","-"))
        linked=linked_path.read_bytes();native=modules["packer"].strip_native(linked);native_path.write_bytes(native)
        return dict(kind="D-owner-native-compile-v1",label=label,input_pins=admission.inventory(files),flags=flags,units=units,
            source_paths={n:str(directory/n) for n in files},linked_path=str(linked_path),stripped_path=str(native_path),
            linked=linked,stripped=native,linked_pin=admission.pin(linked),stripped_pin=admission.pin(native),command=row)
    try:
        for index in (0,3,15):
            bad=json.loads(json.dumps(record));bad["commands"][index]["returncode"]=2;bad["commands"][index]["expected_returncode"]=2
            try:admission.command_scopes(bad,producer)
            except ValueError:pass
            else:raise ValueError("blanket nonzero command exemption was admitted")
        report["typed_nonzero_mutations_rejected"]=True
        unit_profile=modules["source"].production().resource_profile("test-p4")
        unit_base,unit_proof=modules["startup"].prepared(modules["source"],unit_profile,True,modules["storage"],"prefix")
        unit_owned,unit_owner_proof=modules["owner"].transform(unit_base,modules["publication"])
        unit_flags=modules["builder"].native_flags(unit_profile)
        pp=[dict(r) for r in record["commands"] if r["kind"] in ("preprocess-single-baseline","preprocess-entry-baseline")]
        directory=str(experiment/"baseline/generated-readable")
        outputs={name:products["tool-"+str(record["commands"].index(row)+1)+"-"+row["kind"]+".stdout"]
                 for name,row in zip(("main.c","start.S"),pp)}
        pp_result=dict(kind="D-owner-preprocess-v1",label="unit",input_pins=admission.inventory(unit_base),flags=unit_flags,
            members=list(admission.MEMBERS),driver=b''.join(('#include "'+n+'"\n').encode() for n in admission.MEMBERS),
            readable_dir=directory,commands=pp,outputs=outputs)
        try:admission._fresh_preprocess(pp_result,unit_base,unit_flags,"unit",set())
        except ValueError as error:
            if str(error)!="fresh source/entry preprocessing argv differs":raise
        else:raise ValueError("ambient quoted-include cwd admitted")
        for row in pp:row["cwd"]=directory
        try:admission._fresh_preprocess(pp_result,unit_base,unit_flags,"unit",{directory})
        except ValueError as error:
            if str(error)!="fresh preprocessing source/output path reused or overwritten":raise
        else:raise ValueError("reused preprocessing namespace admitted")
        report["fresh_pp_ambient_cwd_and_reuse_rejected"]=True
        if pure:
            if admission.inventory(inputs)!=record["inputs"] or set(current)!={n for n in inputs if n.startswith("engines/")} or any(
                    current[n]!=inputs[n] for n in current):raise ValueError("pure current/frozen closure differs")
            admission._check_tool_bytes(record,products,str(experiment))
            profile=modules["source"].production().resource_profile("test-p4")
            baseline,proof=modules["startup"].prepared(modules["source"],profile,True,modules["storage"],"prefix")
            owned,owner_proof=modules["owner"].transform(baseline,modules["publication"])
            if not admission.equal(proof,record["production_proof"]) or not admission.equal(owner_proof,record["owner_proof"]):
                raise ValueError("pure complete source/owner proof differs")
            admission._stored_generation_vectors(record,products,str(experiment),modules["builder"].native_flags(profile))
            scaled=admission._scaled_contract(record,inputs,products,modules,str(experiment),owned)
            result=dict(kind=admission.OWNER_KIND,pure_preflight=True,source_admitted=False,native_admitted=False,
                package_generation_admitted=False,scaled_contract=scaled,fresh_full_artifact_runtime=False,
                rules_qualified=False,selected=False)
        else:
            result=admission.replay_owner(record,inputs,products,modules,current_inputs=current,
                admission_source=dict(current=raw["owner_admission.py"],frozen=(out/"tools/owner_admission.py").read_bytes()),
                evidence_root=str(experiment),preprocess=preprocess,compile_identity=compile_identity)
            result["readable"]=admission.inventory(result["readable"]);result["shipping"]=admission.inventory(result["shipping"])
        report["admission"]=result
        bad=json.loads(json.dumps(record));bad_products=dict(products)
        active=next(c for c in bad["runtime_cases"] if c["name"]=="w4-active-quit")
        events=active["dialogue"]["events"];events[4],events[5]=events[5],events[4]
        bad_products["w4-active-quit/dialogue.json"]=json.dumps(active["dialogue"]).encode()
        try:admission._scaled_contract(bad,inputs,bad_products,modules,str(experiment),unit_owned)
        except ValueError as error:
            if str(error)!="scaled exact send/receive interleaving differs":raise
        else:raise ValueError("reordered active interrupt evidence admitted")
        report["active_event_interleaving_mutation_rejected"]=True
        for row in report["commands"]:admission._settled(row,0)
        report["complete"]=True
    except BaseException as error:
        report["complete"]=False;report["failure"]=dict(type=type(error).__name__,message=str(error));raise
    finally:
        try:host.close()
        except BaseException as error:
            report["complete"]=False;report["cleanup_failure"]=dict(type=type(error).__name__,message=str(error));raise
        finally:
            cleanup=report.get("host_cleanup",{})
            if cleanup.get("errors") or cleanup.get("unsettled_commands"):report["complete"]=False
            save()
    if not report["complete"]:raise ValueError("independent admission cleanup incomplete")
    print(json.dumps(dict(complete=True,kind=result["kind"],source_admitted=result["source_admitted"],native_admitted=result["native_admitted"],
        package_generation_admitted=result["package_generation_admitted"],scaled_cases=len(result["scaled_contract"]["cases"]),
        fresh_full_artifact_runtime=False,rules_qualified=False)),flush=True)


if __name__=="__main__":main()
