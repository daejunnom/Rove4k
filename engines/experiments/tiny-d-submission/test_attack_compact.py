#!/usr/bin/env python3
"""One target-centric attack candidate: fresh source/rules/search/native cost.

The old selected image and its admission remain unchanged. Each candidate is
fresh own-source generation; changes to ignored syscall registers and terminal
output ownership are named semantic classes, never old-byte equivalence.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FILES = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")
EXPECTED = {"linked": dict(bytes=7488, sha256="87c9f93a87a5d53aaa094a0019952cafbbf8da2ff83c382dee1f1c927d91f00f"),
            "stripped": dict(bytes=7136, sha256="448eeb52aa59e7eaaf7830940be18f5618129d55732d8855e0c8bcb13368f565")}


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def normalized(path):
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in named input")
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def shipping_board(preprocessed,emitted,legacy,reduction,minifier,lexical):
    """Replay complete-TU accepted lexical stages on its actual Board prefix."""
    board=minifier.compact_source(preprocessed,"c").rstrip(b"\n")
    for old,new in legacy.items():board=lexical._replace({"main.c":board},old,new)["main.c"]
    alpha={}
    for stage in reduction["stages"]:
        if stage["status"]!="accepted":continue
        if stage["kind"]=="unused-scalar-typedefs":
            for round in stage["rounds"]:
                parts,at=[],0
                for row in round.get("main.c",{}).get("removed",[]):
                    a,b=row["begin"],row["end"]
                    if a>=len(board):continue
                    if a<at or b>len(board) or board[a:b]!=row["declaration"].encode():
                        raise ValueError("whole-TU typedef cut differs in Board prefix")
                    parts.append(board[at:a]);at=b
                parts.append(board[at:]);board=b"".join(parts)
        elif stage["kind"]=="batch-alpha":alpha=stage["renames"]
        else:raise ValueError("unknown accepted source stage")
    text,parts,at=board.decode(),[],0
    for a,b,token in lexical._identifier_spans(text):
        if token in alpha:parts.extend((text[at:a],alpha[token]));at=b
    parts.append(text[at:]);board="".join(parts).encode()
    if not board.endswith(b"}") or not emitted["main.c"].startswith(board):
        raise ValueError("fresh Board is not complete actual shipping prefix")
    names={n:alpha.get(legacy.get(n,n),legacy.get(n,n)) for n in ("Board","start","gen","make","size_t")}
    size=names["size_t"]
    declarations=("\ntypedef "+size+" size_t;\n").encode() if size!="size_t" else b"\n"
    declarations += (b"extern size_t strlen(const char *);extern int strcmp(const char *,const char *);"
        b"extern char *strtok_r(char *,const char *,char **);extern int printf(const char *,...);"
        b"extern int puts(const char *);extern char *strcpy(char *,const char *);\n")
    binding=dict(board=names["Board"],start=names["start"],generate=names["gen"],make=names["make"],four_args=False)
    return board,binding,declarations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out, selected = args.out.resolve(), args.build.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or not args.out.is_absolute()
            or not args.build.is_absolute() or out.exists() or any((p/".git").exists() for p in (out,*out.parents))):
        parser.error("new external output and absolute selected build on Linux x86-64 required")
    control = json.loads((selected/"build.json").read_bytes())
    source_inputs=load("D_recipe_snapshot_names",HERE/"source_inputs.py")
    producer=set(source_inputs.producer_names(json.loads(normalized(ROOT/source_inputs.RECIPE))))
    if (control.get("storage") != "prefix" or control.get("source_reduced") is not False or
            control.get("family")!="D" or control.get("equivalent_edits") is not True or
            any(control.get(key) is not True for key in ("complete","frozen_execution","native_reproduced")) or
            set(control.get("inputs",{}))!=producer or control.get("units")!=["main.c","start.S"]):
        raise ValueError("unreduced prefix control required")
    inputs = {name:normalized(ROOT/name) for name in control["inputs"]}
    for name,data in inputs.items():
        if pin(data) != control["inputs"][name] or (selected/"inputs"/name).read_bytes() != data:
            raise ValueError("current/selected exact producer differs: "+name)
    for name in ("reduce.py", "publication.py", "process_owner.py", "test_startup.py", "test_process_owner.py",
                 "compressed_bootstrap.py", "syscall_arity.py", "test_runtime_scaffold.py", "valid_input.py",
                 "search_compact.py", "probe_search_compact.py", "check_storage.py", "source_inputs.py", "attack_compact.py", "test_attack_compact.py"):
        logical = "engines/experiments/tiny-d-submission/"+name
        inputs[logical] = normalized(ROOT/logical)
    inputs["selection/build.json"] = (selected/"build.json").read_bytes()
    for name in ("engines/experiments/tcec-next/profile_rules.py","engines/tests/chess_oracle.py"):
        inputs[name]=normalized(ROOT/name)
    out.mkdir()
    for name,data in inputs.items():
        path=out/"inputs"/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    frozen=load("d_attack_frozen",out/"inputs/engines/experiments/tiny-d-submission/test_attack_compact.py")
    frozen.run_snapshot(out,inputs,ROOT)


def run_snapshot(out,inputs,origin):
    mods={n:load("d_scaffold_"+n,HERE/(n+".py")) for n in
          ("source","build","storage","publication","process_owner","test_startup","test_process_owner",
           "packaging","compressed_bootstrap","reduce","syscall_arity","valid_input","test_runtime_scaffold",
           "search_compact","check_storage","probe_search_compact","attack_compact")}
    rules_tool=load("d_attack_actual_rules",ROOT/"engines/experiments/tcec-next/profile_rules.py")
    source, builder, startup = mods["source"],mods["build"],mods["test_startup"]
    original_dialogue=mods["test_runtime_scaffold"].DIALOGUE
    witness='  history=b"g1f3 g8f6 f3g1 f6g8 "*256\n'
    if original_dialogue.count(witness)!=1:raise ValueError("frozen valid dialogue extension boundary differs")
    extension='  send(b"isready"+b" "*32760+b"\\n");until(b"readyok");record["max_line_payload_bytes"]=32767;save()\n'
    DIALOGUE=original_dialogue.replace(witness,extension+witness)
    lexical=load("d_scaffold_lexical",ROOT/"engines/scripts/rename_c.py")
    minifier=load("d_scaffold_minify",ROOT/"engines/scripts/minify.py")
    packer=load("d_scaffold_packer",source.CANONICAL/"packer.py")
    hostmod=load("d_scaffold_commands",ROOT/source.HOST)
    if pin(normalized(ROOT/source.HOST))["sha256"] != source.HOST_SHA:
        raise ValueError("original command owner differs")
    hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":900,"per_command_wall":90,"parent_CPU":500,"parent_CPU_hard":540,"child_CPU":75,"tool_output_bytes":8<<20}
    report=dict(kind="D-target-centric-attack-source-rules-search-cost-v1",complete=False,frozen_execution=True,
        inputs={n:pin(d) for n,d in inputs.items()},commands=[],variants=[],runtime_cases=[],
        selected=False,old_admission_changed=False,runtime_qualified=False,rules_qualified=False,
        real_target_allocation=False,locality_proof=False,strength_claim=False)
    def save():(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=hostmod.Host(out,report,save)
    def run(command,*,cwd,kind,data=None):
        result=host.run(command,cwd=cwd,kind=kind,data=data)
        startup.require_execution(report["commands"][-1],0)
        return result
    try:
        report["compiler"]=run(["cc","--version"],cwd=out,kind="compiler-version").decode().splitlines()[0]
        api=source.production();profile=api.resource_profile("test-p4")
        baseline,production=startup.prepared(source,profile,True,mods["storage"],"prefix")
        owned,ownerproof=mods["process_owner"].transform(baseline,mods["publication"])
        if mods["process_owner"].restore(owned,ownerproof,mods["publication"])!=baseline:
            raise ValueError("owner full source inverse differs")
        report.update(resource=profile.to_record(16),production_proof=production,owner_proof=ownerproof)
        selected=json.loads(inputs["selection/build.json"])
        renames=selected["identifier_native_gate"]["accepted_renames"]
        aritybase,arityproof=mods["syscall_arity"].transform(owned,mods["process_owner"],mods["publication"],ownerproof,noinline_wake=True,immediate_exit=True)
        report["arity_proof"]=arityproof
        validbase,validproof=mods["valid_input"].transform(aritybase,mods["syscall_arity"],mods["process_owner"],mods["publication"],arityproof,mode="one-byte-valid")
        report["valid_proof"]=validproof
        structural,structural_proof=mods["search_compact"].transform(validbase,mods["valid_input"],mods["syscall_arity"],
            mods["process_owner"],mods["publication"],validproof,options=("previous-piece","unsigned-history"))
        report["structural_proof"]=structural_proof
        plans=(("control",False),("target-centric",True))
        semantic_baseline=None
        cases,coverage=rules_tool.fixture_cases()
        for label,candidate in plans:
            options=("previous-piece","unsigned-history")
            immediate=True
            readable,proof=(structural,structural_proof) if not candidate else mods["attack_compact"].transform(structural,
                mods["search_compact"],mods["valid_input"],mods["syscall_arity"],mods["process_owner"],mods["publication"],structural_proof)
            if candidate and mods["attack_compact"].restore(readable,proof,mods["search_compact"],mods["valid_input"],
                    mods["syscall_arity"],mods["process_owner"],mods["publication"])!=structural:
                raise ValueError("attack complete source inverse differs")
            directory=out/label;directory.mkdir();raw=directory/"generated-readable";raw.mkdir()
            for name,data in readable.items():(raw/name).write_bytes(data)
            semantic=[]
            instrumented,driver,semantic_proof=mods["probe_search_compact"].render(readable,source,mods["check_storage"],
                reference_board=validbase["board.c"],prefix=True,dense=False,variant_proof=proof,union_order="union-order" in options,
                previous_index="previous-piece" in options,constant_start="constant-start" in options,
                unsigned_history="unsigned-history" in options)
            for mode,extra in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
                fixture=directory/("semantic-"+mode);fixture.mkdir()
                for name in ("tiny.h","board.c","search.c"):(fixture/name).write_bytes(instrumented[name])
                (fixture/"driver.c").write_bytes(driver);binary=fixture/"x"
                probe_flags=mods["probe_search_compact"].compiler_flags(prefix=True,dense=False,
                    previous_index="previous-piece" in options,unsigned_history="unsigned-history" in options,mode=mode)
                run(["cc",*probe_flags,
                    str(fixture/"driver.c"),"-o",str(binary)],cwd=fixture,kind=label+"-semantic-compile-"+mode)
                output=run([str(binary)],cwd=fixture,kind=label+"-semantic-run-"+mode)
                semantic_bytes,summary=mods["probe_search_compact"].verify_output(output)
                if semantic_baseline is None:semantic_baseline=semantic_bytes
                if semantic_bytes!=semantic_baseline:raise ValueError("actual structural search/order/learner observations differ: "+label)
                semantic.append(dict(mode=mode,output=pin(output),normalized=pin(semantic_bytes),summary=summary,binary=pin(binary.read_bytes())))
            flags=builder.native_flags(profile);units=("main.c","start.S")
            cpp=run(["cc","-E","-P",*flags,"-I",str(raw),"-x","c","-"],cwd=raw,kind=label+"-preprocess",
                data=b''.join(('#include "'+n+'"\n').encode() for n in source.UNITS if n.endswith('.c')))
            walk_sites=len(re.findall(rb"\bwalk\s*\(",cpp))
            if walk_sites!=(3 if candidate else 4):raise ValueError("exact scalar gen-only callgraph differs")
            entry=run(["cc","-E","-P","-x","assembler-with-cpp",str(raw/"start.S")],cwd=raw,kind=label+"-entry")
            emitted={"main.c":minifier.compact_source(cpp,"c"),"start.S":entry,"image.ld":readable["image.ld"]}
            words=set(lexical._ANY_WORD.findall(emitted["main.c"].decode()))
            if any(new in words for new in renames.values()):raise ValueError("legacy aliases capture fresh identifiers")
            mapped={"main.c":emitted["main.c"]}
            for old,new in renames.items():mapped=lexical._replace(mapped,old,new)
            emitted.update(mapped);gate_index=0
            def compile_gate(files,trial):
                nonlocal gate_index
                gate=directory/("gate-"+str(gate_index));gate_index+=1;gate.mkdir()
                for name,data in {**emitted,**files}.items():(gate/name).write_bytes(data)
                run(["cc",*flags,*[str(gate/n) for n in units],"-Wl,-T,"+str(gate/"image.ld"),"-o",str(gate/"linked")],cwd=gate,kind=label+"-source-gate-"+str(trial))
                return pin((gate/"linked").read_bytes())["sha256"]
            reduced,reduction=mods["reduce"].reduce_sources({"main.c":emitted["main.c"]},compile_gate,lexical,
                reserve=lexical._ANY_WORD.findall((entry+emitted["image.ld"]).decode()))
            emitted.update(reduced);shipping=directory/"shipping-inputs";shipping.mkdir()
            for name,data in emitted.items():(shipping/name).write_bytes(data)
            observations=[];images=[]
            for index in range(2):
                attempt=directory/("native-"+str(index));attempt.mkdir()
                run(["cc",*flags,*[str(shipping/n) for n in units],"-Wl,-T,"+str(shipping/"image.ld"),"-o",str(attempt/"linked")],cwd=attempt,kind=label+"-native-"+str(index))
                linked=(attempt/"linked").read_bytes();native=packer.strip_native(linked)
                (attempt/"native").write_bytes(native);images.append((linked,native))
                observations.append(dict(linked=pin(linked),stripped=pin(native),
                    linked_geometry=builder.kernel_geometry(packer,linked,profile.workers),
                    native_geometry=builder.kernel_geometry(packer,native,profile.workers)))
            if images[0]!=images[1] or observations[0]["linked"]["sha256"]!=reduction["final_native_sha256"]:
                raise ValueError("actual native double reproduction/source gate differs")
            identity={k:observations[0][k] for k in EXPECTED}
            if not candidate and identity!=EXPECTED:raise ValueError("current structural control native differs")
            board_cpp=run(["cc","-E","-P",*flags,str(raw/"board.c")],cwd=raw,kind=label+"-actual-board-preprocess")
            actual_board,binding,declarations=shipping_board(board_cpp,emitted,renames,reduction,minifier,lexical)
            rule_fixture=rules_tool.render_bound_fixture(actual_board,binding,cases,declarations)
            rule_results=[]
            for mode,extra in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
                rules_dir=directory/("rules-"+mode);rules_dir.mkdir();(rules_dir/"fixture.c").write_bytes(rule_fixture)
                binary=rules_dir/"x"
                run(["cc","-std=c11","-O1","-g0","-fno-builtin","-msse4.2","-mcx16",*extra,
                    str(rules_dir/"fixture.c"),"-o",str(binary)],cwd=rules_dir,kind=label+"-rules-compile-"+mode)
                observed=run([str(binary)],cwd=rules_dir,kind=label+"-rules-run-"+mode)
                rule_results.append(dict(mode=mode,binary=pin(binary.read_bytes()),**rules_tool._compare_output(observed,cases)))
            packages=[]
            for codec in ("alone","xz","xz-bcj"):
                whole,detail=mods["packaging"].package_native(images[0][1],codec)
                repeated,_=mods["packaging"].package_native(images[0][1],codec)
                if whole!=repeated:raise ValueError("whole repeat differs")
                path=directory/("packed-"+codec);path.write_bytes(whole);path.chmod(0o700)
                packages.append(dict(route="packed-"+codec,whole=pin(whole),detail=detail,reproduced=True))
                if not candidate and codec=="xz-bcj" and len(whole)!=5261:raise ValueError("control whole cost differs")
            whole,detail=mods["compressed_bootstrap"].package_source(emitted,flags,units,mods["packaging"])
            repeated,_=mods["compressed_bootstrap"].package_source(emitted,flags,units,mods["packaging"])
            if whole!=repeated:raise ValueError("compressed source double reproduction differs")
            (directory/"source-jit-compressed").write_bytes(whole)
            packages.append(dict(route="source-jit-compressed",whole=pin(whole),detail=detail,reproduced=True))
            report["variants"].append(dict(name=label,source={n:pin(d) for n,d in readable.items()},proof=proof,
                flags=flags,units=list(units),shipping={n:pin(d) for n,d in emitted.items()},
                legacy_renames=renames,reduction=reduction,native=observations,packages=packages,
                last_search_output_required=False,input_domain="TCEC-valid-lines",options=list(options),
                semantic_proof=semantic_proof,semantic=semantic,semantic_equal=True,
                rules=dict(preprocessed=pin(board_cpp),shipping_board_prefix=pin(actual_board),fixture=pin(rule_fixture),
                    binding=binding,coverage=coverage,modes=rule_results,actual_shipping_prefix=True),
                scalar_walk_sites=walk_sites))
            cost=next(x["whole"]["bytes"] for x in packages if x["route"]=="packed-xz-bcj")
            if candidate:report["whole_improved"]=cost<5261
            save()
            small=api.ResourceProfile(label,"test",4,16<<12)
            smallflags=builder.native_flags(small)
            for mode in ("valid","quit","eof"):
                fixture=directory/("fixture-"+mode);fixture.mkdir();testfiles=dict(readable);instrumentation=None
                if mode!="valid":testfiles,instrumentation=mods["test_process_owner"].active_instrument(testfiles,source,mods["process_owner"])
                for name,data in testfiles.items():(fixture/name).write_bytes(data)
                binary=fixture/"x"
                run(["cc",*smallflags,*[str(fixture/n) for n in source.UNITS],"-Wl,-T,"+str(fixture/"image.ld"),"-o",str(binary)],cwd=fixture,kind=label+"-fixture-compile-"+mode)
                driver=fixture/"dialogue.py";driver.write_text(DIALOGUE);receipt=fixture/"dialogue.json"
                run([sys.executable,"-I","-B",str(driver),str(binary),str(receipt),mode,str(int(immediate))],cwd=fixture,kind=label+"-fixture-run-"+mode)
                dialogue=json.loads(receipt.read_text())
                if not dialogue.get("complete") or not dialogue.get("engine_reaped") or dialogue.get("forced_cleanup") or dialogue.get("returncode")!=0:
                    raise ValueError("finite actual-runtime contract failed")
                report["runtime_cases"].append(dict(name=label+"-"+mode,mode=mode,workers=4,tt_bits=12,
                    source_before={n:pin(d) for n,d in readable.items()},instrumentation=instrumentation,
                    binary=pin(binary.read_bytes()),dialogue=dialogue,last_search_output_required=not immediate))
                save()
        if len(report["runtime_cases"])!=3*len(plans):raise ValueError("finite runtime matrix incomplete")
        for row in report["commands"]:startup.require_execution(row,0)
        report["source_current_after"]={name:pin(normalized(origin/name)) for name in inputs if name.startswith("engines/")}
        if any(report["source_current_after"][name]!=pin(data) for name,data in inputs.items() if name.startswith("engines/")):
            raise ValueError("frozen/current producer changed during experiment")
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
    print(json.dumps(dict(complete=report["complete"],variants=len(report["variants"]),runtime_cases=len(report["runtime_cases"]),selected=False)),flush=True)


if __name__=="__main__":main()
