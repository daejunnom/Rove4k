"""Independent replay admission for the finite D process-owner v2 candidate.

No subprocess, engine, filesystem mutation or R fallback lives here. Callers
supply named evidence bytes, genuine frozen D modules, and freshly owned
preprocess/compile callbacks. Every fresh compile needs unique output paths;
recorded reducer hashes alone are insufficient (old scratch images were
overwritten). Generation/package, scaled semantics, fresh artifact runtime,
rules, placement and size are deliberately separate admission dimensions.

``preprocess(readable, flags, members, label)`` returns outputs/main.c+start.S,
input_pins, flags, members, driver bytes, readable_dir, and two original Host
command rows. ``compile_identity(shipping, flags, units, label)`` returns
linked/stripped bytes and pins, input_pins, flags, units, source_paths,
linked_path/stripped_path, and the original Host command row. The callbacks
own the real I/O. Their rows must retain original PID/PGID and complete normal
settlement; source buffers, argv and paths are checked against each request.
"""
from collections import Counter
from copy import deepcopy
from pathlib import PurePosixPath
import hashlib
import json
import lzma
import re

OWNER_KIND = "rove4k.D-process-owner-source.v1"
EXPERIMENT_KIND = "D-process-owner-experimental-source-cost-runtime-v1"
NATIVE = ("tiny.h","board.c","search.c","runtime.c","start.S","image.ld")
UNITS = ("main.c","start.S")
MEMBERS = ("board.c","search.c","runtime.c")
BASELINE = dict(linked=dict(bytes=7792,sha256="e5d54f2f9b918316efcb171631cf4745bf97f7dfacfb55faff6a5ee9aa71128f"),
    stripped=dict(bytes=7440,sha256="e06bce0d9998fa14cb85f135d3c5f54f9972d3dea533cede1f44ed28618e3337"))
OWNER = dict(linked=dict(bytes=7712,sha256="c80f6c4d3b7af14a96f47326c843abbabd7626a54c879ed21a376eca22d7eeca"),
    stripped=dict(bytes=7360,sha256="cfa7b5d045d5f1e6e2232942e38d79cd8b8812e9e3ed7702fb4df50ab71296f4"))
PRODUCER = tuple("engines/compact/tiny-entry-d/native/"+n for n in NATIVE)+(
    "engines/compact/tiny-entry-d/recipe.json","engines/compact/tiny-entry-d/shipping_fused_ray.py",
    "engines/compact/tiny-entry-d/packer.py","engines/experiments/tcec-scope/build.py",
    "engines/scripts/production.py","engines/scripts/minify.py","engines/scripts/rename_c.py",
    "engines/experiments/tiny-d-submission/source.py","engines/experiments/tiny-d-submission/build.py",
    "engines/experiments/tiny-d-submission/packaging.py","engines/experiments/tiny-d-submission/storage.py")
EXTRA = tuple("engines/experiments/tiny-d-submission/"+n for n in
    ("reduce.py","publication.py","process_owner.py","test_startup.py","test_process_owner.py"))
BOOTSTRAP = "engines/experiments/tiny-d-submission/compressed_bootstrap.py"
RUNTIME = (
    ("w4-startup",4,0,"startup"),("w28-startup",28,0,"startup"),("w256-startup",256,0,"startup"),
    ("w256-go",256,0,"go"),("w4-spawn-fail",4,2,"spawn-two"),("w4-omit-clear",4,7,"omit-clear"),
    ("w4-zero-spawn",4,2,"spawn-zero"),("w4-active-quit",4,0,"active-quit"),
    ("w4-active-eof",4,0,"active-eof"),("w4-drop-wait-negative",4,13,"drop-wait-negative"))


def require(value,message):
    if not value:raise ValueError(message)


def pin(data):
    require(isinstance(data,bytes),"evidence must be actual bytes")
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def inventory(files):
    return {n:pin(d) for n,d in sorted(files.items())}


def equal(left,right):
    return json.dumps(left,sort_keys=True,separators=(",",":"))==json.dumps(right,sort_keys=True,separators=(",",":"))


def _absolute(value):
    require(isinstance(value,str) and PurePosixPath(value).is_absolute() and
        ".." not in PurePosixPath(value).parts and str(PurePosixPath(value))==value,"canonical absolute Linux evidence path required")
    return value


def _settled(row,expected):
    require(type(expected) is int and type(row.get("returncode")) is int and row["returncode"]==expected,
        "typed command expected status differs")
    require(all(row.get(k) is True for k in ("started","terminal","reaped","owned_group_absent",
        "original_identity_retained_until_other_members_absent")) and row.get("forced_cleanup") is False and
        row.get("other_group_members_before_reap")==[],"original owned command did not settle naturally")
    require(type(row.get("pid")) is int and row["pid"]>0 and row.get("pgid")==row["pid"],
        "precise original owned PID/PGID required")


def input_names(record):
    """Exact finite input closure; return names without reading arbitrary paths."""
    require(record.get("kind")==EXPERIMENT_KIND and record.get("complete") is True and
        record.get("frozen_execution") is True and record.get("ownership_class")=="D-final-wait-own-exit-group-v1",
        "explicit completed D owner experiment required")
    require(all(record.get(k) is False for k in ("baseline_wired","old_native_R_guard_used","real_target_allocation",
        "locality_proof","strength_claim","per_worker_search_work_proof",
        "runtime_qualified","whole_artifact_qualified","selected")),"owner experiment qualification scope differs")
    names={"selection/build.json",*PRODUCER,*EXTRA}
    names.update("selection/generated-readable/"+n for n in NATIVE)
    names.update("selection/shipping-inputs/"+n for n in ("main.c","start.S","image.ld"))
    if BOOTSTRAP in record.get("inputs",{}):names.add(BOOTSTRAP)
    require(isinstance(record.get("inputs"),dict) and set(record["inputs"])==names,"owner exact named input closure differs")
    return tuple(sorted(names))


def command_scopes(record):
    """Assign statuses by exact typed command role, never blanket nonzero allow."""
    input_names(record)
    specs=[("compiler-version",0,"generation/compiler")]
    for label in ("baseline","owner"):
        specs += [("preprocess-single-"+label,0,"generation/preprocess"),("preprocess-entry-"+label,0,"generation/preprocess")]
        specs += [(label+"-source-gate-"+stage,0,"generation/reducer-linked-gate") for stage in ("baseline","typedefs","batch-alpha")]
        specs += [(label+"-native-repeat-"+str(i),0,"generation/native-repeat") for i in range(2)]
    for name,workers,status,mode in RUNTIME:
        specs += [("compile-"+name,0,"scaled/compile"),("execute-"+name,status,"scaled/"+mode)]
    rows=record.get("commands")
    require(isinstance(rows,list) and len(rows)==len(specs),"owner typed command scope count differs")
    result=[]
    for index,(row,(kind,status,scope)) in enumerate(zip(rows,specs)):
        require(row.get("kind")==kind and type(row.get("expected_returncode")) is int and
            row["expected_returncode"]==status,"owner typed command role/status differs")
        _settled(row,status)
        require(isinstance(row.get("command"),list) and all(isinstance(x,str) for x in row["command"]),"original command argv required")
        result.append(dict(index=index,kind=kind,scope=scope,expected_returncode=status,
            identity=dict(pid=row["pid"],pgid=row["pgid"]),record=pin(json.dumps(row,sort_keys=True).encode())))
    require(record.get("host_cleanup")==dict(unsettled_commands=0,errors=[]),"owner experiment cleanup differs")
    return result


def evidence_names(record):
    """Bounded relative product names for a caller's safe evidence reader."""
    scopes=command_scopes(record);names=set()
    for label in ("baseline","owner"):
        names.update(label+"/generated-readable/"+n for n in NATIVE)
        names.update(label+"/shipping-inputs/"+n for n in ("main.c","start.S","image.ld"))
        names.update(label+"/attempt-"+str(i)+"/"+n for i in range(2) for n in ("linked","native"))
        names.update(label+"/"+n for n in ("native-alone","native-xz","native-xz-bcj","source-jit"))
        if BOOTSTRAP in record["inputs"]:names.add(label+"/source-jit-compressed")
    for row in scopes:
        stem="tool-"+str(row["index"]+1)+"-"+row["kind"]
        names.update((stem+".stdout",stem+".stderr"))
        if row["kind"].startswith("preprocess-single-"):names.add(stem+".stdin")
    for name,workers,status,mode in RUNTIME:
        names.add(name+"/x");names.update(name+"/"+n for n in NATIVE)
        if mode in ("go","active-quit","active-eof","drop-wait-negative"):
            names.update((name+"/dialogue.py",name+"/dialogue.json"))
        else:
            index=next(s["index"] for s in scopes if s["kind"]=="execute-"+name)
            names.add("tool-"+str(index+1)+"-execute-"+name+".stdin")
    return tuple(sorted(names))


def _fresh_compile(result,files,flags,units,label,modules,seen):
    require(isinstance(result,dict) and result.get("kind")=="D-owner-native-compile-v1" and result.get("label")==label,
        "typed fresh owner compilation result required")
    require(equal(result.get("input_pins"),inventory(files)) and result.get("flags")==list(flags) and
        result.get("units")==list(units),"fresh compile frozen inputs/flags/units differ")
    paths=result.get("source_paths",{})
    require(set(paths)==set(files),"fresh compile exact source paths required")
    for name,path in paths.items():
        _absolute(path);require(PurePosixPath(path).name==name,"fresh compile source basename differs")
    linked_path=_absolute(result.get("linked_path"));native_path=_absolute(result.get("stripped_path"))
    all_paths=[*paths.values(),linked_path,native_path]
    require(len(set(all_paths))==len(all_paths) and not any(p in seen for p in all_paths),
        "fresh compile source/output path reused or overwritten")
    seen.update(all_paths)
    row=result.get("command",{});_settled(row,0)
    streams=[_absolute(row.get(stream,{}).get("path")) for stream in ("stdout","stderr")]
    require(len(set(streams))==len(streams) and not any(path in seen for path in streams),"fresh compile tool streams reused or overwritten")
    seen.update(streams)
    require(row["command"]==["cc",*flags,*[paths[n] for n in units],"-Wl,-T,"+paths["image.ld"],"-o",linked_path],
        "fresh full-linked compiler argv differs")
    linked,native=result.get("linked"),result.get("stripped")
    require(result.get("linked_pin")==pin(linked) and result.get("stripped_pin")==pin(native) and
        modules["packer"].strip_native(linked)==native,"fresh linked/stripped actual bytes or pins differ")
    geometry=modules["builder"].kernel_geometry(modules["packer"],linked,4)
    native_geometry=modules["builder"].kernel_geometry(modules["packer"],native,4)
    return linked,native,dict(label=label,input_pins=inventory(files),flags=list(flags),units=list(units),
        linked=pin(linked),stripped=pin(native),linked_path=linked_path,stripped_path=native_path,
        command=deepcopy(row),geometry=geometry,native_geometry=native_geometry)


def _fresh_preprocess(result,files,flags,label,seen):
    require(isinstance(result,dict) and result.get("kind")=="D-owner-preprocess-v1" and result.get("label")==label,
        "typed fresh owner preprocessing result required")
    driver=b''.join(('#include "'+name+'"\n').encode() for name in MEMBERS)
    require(result.get("input_pins")==inventory(files) and result.get("flags")==list(flags) and
        result.get("members")==list(MEMBERS) and result.get("driver")==driver,
        "fresh preprocess frozen sources/flags/member order differs")
    directory=_absolute(result.get("readable_dir"));rows=result.get("commands")
    require(isinstance(rows,list) and len(rows)==2,"two exact preprocessing commands required")
    for row in rows:_settled(row,0)
    require(rows[0]["command"]==["cc","-E","-P",*flags,"-I",directory,"-x","c","-"] and
        rows[1]["command"]==["cc","-E","-P","-x","assembler-with-cpp",directory+"/start.S"] and
        all(row.get("cwd")==directory for row in rows),
        "fresh source/entry preprocessing argv differs")
    outputs=result.get("outputs",{})
    require(set(outputs)=={"main.c","start.S"},"actual fresh C/S preprocessing bytes required")
    paths=[directory,*[directory+"/"+n for n in files]]
    for name,row in zip(("main.c","start.S"),rows):
        require({k:row.get("stdout",{}).get(k) for k in ("bytes","sha256")}==pin(outputs[name]),
            "fresh preprocessing stdout identity differs")
        paths.extend(_absolute(row.get(stream,{}).get("path")) for stream in ("stdout","stderr"))
    require(len(set(paths))==len(paths) and not any(p in seen for p in paths),"fresh preprocessing source/output path reused or overwritten")
    seen.update(paths)
    return outputs,dict(label=label,input_pins=inventory(files),flags=list(flags),members=list(MEMBERS),
        driver=pin(driver),commands=deepcopy(rows),outputs=inventory(outputs))


def _check_tool_bytes(record,products,root):
    rows=record["commands"]
    for index,row in enumerate(rows):
        stem="tool-"+str(index+1)+"-"+row["kind"]
        for stream in ("stdout","stderr"):
            name=stem+"."+stream
            require(row.get(stream)==dict(path=root+"/"+name,**pin(products[name])),"typed stored command output bytes differ")
    require(rows[0]["command"]==["cc","--version"] and rows[0]["cwd"]==root,"stored compiler identity command differs")


def _stored_generation_vectors(record,products,root,flags):
    index=1;driver=b''.join(('#include "'+name+'"\n').encode() for name in MEMBERS)
    for label in ("baseline","owner"):
        directory=root+"/"+label;readable=directory+"/generated-readable"
        row=record["commands"][index]
        require(row["command"]==["cc","-E","-P",*flags,"-I",readable,"-x","c","-"] and row["cwd"]==directory and
            products["tool-"+str(index+1)+"-"+row["kind"]+".stdin"]==driver,"stored exact single-TU preprocessing boundary differs")
        index+=1;row=record["commands"][index]
        require(row["command"]==["cc","-E","-P","-x","assembler-with-cpp",readable+"/start.S"] and
            row["cwd"]==directory,"stored entry preprocessing boundary differs")
        index+=1
        for stage in ("baseline","typedefs","batch-alpha"):
            row=record["commands"][index];gate=directory+"/identity-gate"
            require(row["command"]==["cc",*flags,gate+"/main.c",gate+"/start.S","-Wl,-T,"+gate+"/image.ld","-o",gate+"/linked"] and
                row["cwd"]==gate,"stored reducer command boundary differs")
            index+=1
        for repeat in range(2):
            row=record["commands"][index];shipping=directory+"/shipping-inputs";attempt=directory+"/attempt-"+str(repeat)
            require(row["command"]==["cc",*flags,shipping+"/main.c",shipping+"/start.S","-Wl,-T,"+shipping+"/image.ld","-o",attempt+"/linked"] and
                row["cwd"]==attempt,"stored independent native command boundary differs")
            index+=1


def _strict_payload(whole,header_bytes,expected):
    require(type(header_bytes) is int and 0<header_bytes<len(whole) and whole.startswith(b"#!/bin/sh\nexec python3 -c "),
        "complete counted D bootstrap header required")
    decoder=lzma.LZMADecompressor()
    restored=decoder.decompress(whole[header_bytes:])
    require(decoder.eof and not decoder.unused_data and restored==expected,"strict whole wrapper payload boundary differs")
    return dict(header=pin(whole[:header_bytes]),payload=pin(whole[header_bytes:]),restored=pin(restored))


def _packages(label,files,flags,units,native,declared,products,modules,compressed):
    packaging=modules["packaging"];result=[]
    routes=["native-alone","native-xz","native-xz-bcj","source-jit"]+(["source-jit-compressed"] if compressed else [])
    require(isinstance(declared,list) and [r.get("route") for r in declared]==routes,"exact finite owner package routes required")
    bundle=dict(files={n:files[n].decode() for n in sorted(files)},flags=list(flags),units=list(units))
    for route,row in zip(routes,declared):
        if route.startswith("native-"):
            codec=route[len("native-"):];whole,detail=packaging.package_native(native,codec)
            repeated,again=packaging.package_native(native,codec);restored=native
        elif route=="source-jit":
            whole,detail=packaging.package_source(files,flags,units)
            repeated,again=packaging.package_source(files,flags,units)
            restored=json.dumps(bundle,separators=(",",":"),ensure_ascii=True).encode()
        else:
            bootstrap=modules["bootstrap"]
            whole,detail=bootstrap.package_source(files,flags,units,packaging)
            repeated,again=bootstrap.package_source(files,flags,units,packaging)
            suffix=bootstrap.ANCHOR+packaging.SOURCE_CODE.split(bootstrap.ANCHOR,1)[1]
            restored=(bootstrap.IMPORTS+"b="+json.dumps(bundle,separators=(",",":"),ensure_ascii=True)+"\n"+suffix).encode()
            require(detail.get("runtime_qualified") is False and detail.get("selected") is False,
                "compressed bootstrap remains cost-only")
        require(whole==repeated==products[label+"/"+route] and equal(detail,again) and row.get("whole")==pin(whole) and
            equal(row.get("package"),detail) and row.get("package_reproduced") is True,"independent whole package reproduction differs")
        boundaries=_strict_payload(whole,detail["header_bytes"],restored)
        result.append(dict(route=route,whole=pin(whole),boundaries=boundaries,cost_only=route=="source-jit-compressed",
            generation_admitted=True,runtime_qualified=False))
    return result


def _role_composition(legacy,reduction):
    alpha={}
    for stage in reduction["stages"]:
        if stage["kind"]=="batch-alpha" and stage["status"]=="accepted":alpha=stage["renames"]
    names=set(legacy)|set(alpha);composed={name:alpha.get(legacy.get(name,name),legacy.get(name,name)) for name in names}
    roles={name:composed.get(name,name) for name in ("Board","Worker","Move","start","gen","make","attacked","value",
        "dead","mix","think","main","spawn","memcpy","memset","memcmp","abort","game_keys","game_length")}
    return dict(legacy=deepcopy(legacy),accepted_alpha=deepcopy(alpha),composed=composed,roles=roles,
        scalar_typedef_rounds=[deepcopy(s["rounds"]) for s in reduction["stages"] if s["kind"]=="unused-scalar-typedefs" and s["status"]=="accepted"],
        stage_order=["legacy-control-identifiers","accepted-unused-scalar-typedefs","accepted-batch-alpha"])


def _scaled_contract(record,frozen_inputs,products,modules,root,owned):
    source,owner,publication,startup,storage,builder,checker=(modules[n] for n in
        ("source","owner","publication","startup","storage","builder","checker"))
    api=source.production();cases=record.get("runtime_cases")
    require(record.get("ownership_contract_passed") is True and isinstance(cases,list) and len(cases)==len(RUNTIME),
        "complete typed stored scaled ownership matrix required")
    commands={row["kind"]:row for row in record["commands"]};result=[]
    expected_source=inventory(owned);legal={f"{f}2{f}{r}" for f in "abcdefgh" for r in "34"}|{"b1a3","b1c3","g1f3","g1h3"}
    for case,(name,workers,status,mode) in zip(cases,RUNTIME):
        require(case.get("name")==name and type(case.get("expected_returncode")) is int and case["expected_returncode"]==status and
            case.get("workers")==workers and case.get("tt_bits")==12 and case.get("tt_bytes")==16<<12 and
            all(case.get(k) is True for k in ("passed","owner_source_equal","natural_termination")) and
            case.get("external_termination_used") is False and case.get("source_before_instrumentation")==expected_source,
            "typed scaled source/profile/status differs")
        profile=api.ResourceProfile(name,"test",workers,16<<12)
        raw,proof=startup.prepared(source,profile,True,storage,"prefix")
        variant,owner_proof=owner.transform(raw,publication)
        require(inventory(variant)==expected_source and owner.restore(variant,owner_proof,publication)==raw and
            equal(proof,case.get("production")) and equal(owner_proof,case.get("owner")),"scaled exact source/owner inverse differs")
        instrumented,instrumentation=startup.instrument(variant,fail=mode=="spawn-two",omit_clear=mode=="omit-clear",go=mode=="go")
        extra=None
        if mode=="spawn-zero":
            instrumented["runtime.c"],extra=source.project(instrumented["runtime.c"],[("fail-before-first-real-spawn",
                b"char *stack=allocate(1048576+4096);if(!stack){status=2;break;}",
                b'if(created==0){output("TEST_OWNER_ZERO_SPAWN_FAILURE\\n");status=2;break;}char *stack=allocate(1048576+4096);if(!stack){status=2;break;}')])
        active=mode in ("active-quit","active-eof","drop-wait-negative")
        negative=mode=="drop-wait-negative"
        if active:instrumented,extra=checker.active_instrument(instrumented,source,owner,drop_wait=negative)
        require(equal(instrumentation,case.get("instrumentation")) and equal(extra,case.get("extra_instrumentation")) and
            case.get("test_only_held_real_claim") is active and case.get("negative_final_wait_deleted") is negative and
            all(products[name+"/"+n]==d for n,d in instrumented.items()),"actual scaled test-only source/projection differs")
        directory=root+"/"+name;flags=builder.native_flags(profile)
        compile_row=commands["compile-"+name];execute_row=commands["execute-"+name]
        require(case.get("flags")==flags and compile_row["cwd"]==directory and
            compile_row["command"]==["cc",*flags,*[directory+"/"+n for n in source.UNITS],"-Wl,-T,"+directory+"/image.ld","-o",directory+"/x"],
            "scaled compiler exact source/flags boundary differs")
        require(case.get("binary")==pin(products[name+"/x"]),"scaled actual native image differs")
        builder.kernel_geometry(modules["packer"],products[name+"/x"],workers)
        require(execute_row["cwd"]==directory,"scaled runtime command directory differs")
        index=record["commands"].index(execute_row)+1
        output=products["tool-"+str(index)+"-execute-"+name+".stdout"]
        require(case.get("output")==output.decode(),"scaled output bytes differ")
        dialogue=None
        if active or mode=="go":
            driver=checker.ACTIVE if active else startup.DIALOGUE
            require(products[name+"/dialogue.py"]==driver.encode(),"actual scaled driver source differs")
            argv=execute_row["command"]
            expected=["-I","-B",directory+"/dialogue.py",directory+"/x",directory+"/dialogue.json"]
            if active:expected += ["eof" if mode=="active-eof" else "quit"]+(["negative"] if negative else [])
            require(len(argv)==len(expected)+1 and _absolute(argv[0])==argv[0] and PurePosixPath(argv[0]).name=="python3" and
                argv[1:]==expected,"scaled exact Python dialogue argv differs")
            dialogue=json.loads(products[name+"/dialogue.json"])
            require(equal(dialogue,case.get("dialogue")) and all(dialogue.get(k) is True for k in
                ("complete","engine_started","engine_reaped","inherits_owner_group")) and dialogue.get("forced_cleanup") is False and
                type(dialogue.get("returncode")) is int and dialogue["returncode"]==0 and
                type(dialogue.get("pid")) is int and dialogue["pid"]>0 and dialogue["pid"]!=execute_row["pid"] and
                dialogue.get("pgid")==dialogue.get("owner_pgid")==execute_row["pgid"],"scaled natural engine/TGID owner evidence differs")
            received="".join(e["receive"] for e in dialogue.get("events",[]) if "receive" in e)
            sends=[e["send"] for e in dialogue.get("events",[]) if "send" in e]
            expected_sends=["uci\n","position startpos\ngo wtime 3600000 btime 3600000\n"] if active else [
                "uci\n","position startpos\ngo wtime 100 btime 100\n","isready\n","quit\n"]
            if active and mode!="active-eof":expected_sends.append("quit\n")
            require(received==output.decode() and sends==expected_sends,"scaled actual interrupt/dialogue ordering differs")
            lines=output.decode().splitlines(keepends=True)
            require(len(lines)==(3 if negative else 5 if active else 6),"finite scaled dialogue line count differs")
            if active:
                events=[dict(send=expected_sends[0]),dict(receive=lines[0]),dict(receive=lines[1]),
                    dict(send=expected_sends[1]),dict(receive=lines[2])]
                if mode!="active-eof":events.append(dict(send="quit\n"))
                if not negative:events.extend((dict(receive=lines[3]),dict(receive=lines[4])))
            else:
                events=[dict(send=expected_sends[0]),dict(receive=lines[0]),dict(receive=lines[1]),
                    dict(send=expected_sends[1]),dict(receive=lines[2]),dict(receive=lines[3]),dict(receive=lines[4]),
                    dict(send="isready\n"),dict(receive=lines[5]),dict(send="quit\n")]
            require(dialogue.get("events")==events,"scaled exact send/receive interleaving differs")
        else:
            require(case.get("dialogue") is None and execute_row["command"]==[directory+"/x"] and
                products["tool-"+str(index)+"-execute-"+name+".stdin"]==b"uci\nisready\nquit\n",
                "scaled direct runtime stdin/argv differs")
        if negative:
            require(dialogue.get("negative") is True and dialogue.get("negative_detected") is True and
                dialogue.get("interrupted_after_real_claim") is True and
                output==b"TEST_INITIALIZED\nuciok\nTEST_OWNER_SEARCH_ENTERED\n",
                "dropped wait negative requires natural zero with missing complete result")
        elif active:
            lines=output.splitlines()
            require(dialogue.get("negative") is False and dialogue.get("interrupted_after_real_claim") is True and
                len(lines)==5 and lines[:4]==[b"TEST_INITIALIZED",b"uciok",b"TEST_OWNER_SEARCH_ENTERED",b"TEST_OWNER_ACTIVE_PENDING"] and
                lines[4].startswith(b"bestmove ") and lines[4][9:].decode() in legal and dialogue.get("bestmove")==lines[4].decode(),
                "active quit/EOF must retain final wait and complete legal result")
        elif mode=="go":
            lines=output.splitlines()
            require(len(lines)==6 and lines[:4]==[b"TEST_INITIALIZED",b"uciok",b"TEST_PENDING_257",b"TEST_FINISHED_256"] and
                lines[5]==b"readyok" and lines[4].startswith(b"bestmove ") and lines[4][9:].decode() in legal and
                dialogue.get("bestmove")==lines[4].decode(),"stored W256 GO/pending/result differs")
        elif mode in ("spawn-zero","spawn-two","omit-clear"):
            expected={"spawn-zero":b"TEST_OWNER_ZERO_SPAWN_FAILURE\n","spawn-two":b"TEST_INJECTED_SPAWN_FAILURE\n",
                      "omit-clear":b"TEST_POISON_REMAINS\n"}[mode]
            require(output==expected,"typed negative exact failure marker differs")
        else:
            require(output==b"TEST_INITIALIZED\nuciok\nreadyok\n","stored startup exact protocol differs")
        result.append(dict(name=name,scope="scaled/"+mode,workers=workers,tt_bits=12,tt_bytes=16<<12,
            expected_returncode=status,source_bound=True,natural_group_exit=True,output=pin(output),
            driver=pin(products[name+"/dialogue.py"]) if dialogue is not None else None))
    return dict(stored_contract_verified=True,cases=result,fresh_full_artifact_runtime=False,
        real_target_allocation=False,locality_proof=False,strength_claim=False)


def replay_owner(record,frozen_inputs,products,modules,*,current_inputs,admission_source,
                 evidence_root,preprocess,compile_identity):
    """Return explicit generation-only owner admission after independent gates.

    ``products`` uses exactly evidence_names(record)'s root-relative names.
    ``current_inputs`` covers the engine/tool logical names from input_names.
    ``admission_source`` holds equal current/frozen bytes for this new helper;
    its caller freezes and loads the same helper, outside the old experiment.
    """
    names=input_names(record);scopes=command_scopes(record);root=_absolute(evidence_root)
    require(set(frozen_inputs)==set(names) and inventory(frozen_inputs)==record["inputs"],"frozen owner input bytes differ")
    logical={n for n in names if n.startswith("engines/")}
    require(set(current_inputs)==logical and inventory(current_inputs)=={n:record["inputs"][n] for n in sorted(logical)} and
        all(current_inputs[n]==frozen_inputs[n] for n in logical),"current/frozen owner source closure differs")
    require(set(admission_source)=={"current","frozen"} and admission_source["current"]==admission_source["frozen"],
        "new owner admission helper must be frozen and current")
    admission_pin=pin(admission_source["frozen"])
    require(set(products)==set(evidence_names(record)),"exact bounded owner evidence products required")
    _check_tool_bytes(record,products,root)
    source,builder,storage,owner,publication=(modules[n] for n in ("source","builder","storage","owner","publication"))
    startup,lexical,reducer,minifier,packer=(modules[n] for n in ("startup","lexical","reducer","minifier","packer"))
    selected=json.loads(frozen_inputs["selection/build.json"])
    require(record.get("selected_control_manifest")==pin(frozen_inputs["selection/build.json"]),"declared selected control manifest differs")
    require(all(selected.get(k) is True for k in ("complete","frozen_execution","native_reproduced")) and
        selected.get("family")=="D" and selected.get("source_reduced") is False and selected.get("equivalent_edits") is True and
        selected.get("storage")=="prefix" and set(selected.get("inputs",{}))==set(PRODUCER),"exact unreduced prefix v8 control required")
    require({n:record["inputs"][n] for n in PRODUCER}==selected["inputs"],"selected control producer pins differ")
    profile=source.production().resource_profile("test-p4");flags=builder.native_flags(profile)
    require(equal(selected.get("resource"),profile.to_record(16)) and selected.get("flags")==flags and
        selected.get("units")==list(UNITS) and equal(record.get("resource"),profile.to_record(16)),"exact P4 source/flag/resource contract required")
    baseline,production_proof=startup.prepared(source,profile,True,storage,"prefix")
    require(equal(production_proof,selected["proof"]) and equal(production_proof,record.get("production_proof")) and
        baseline=={n:frozen_inputs["selection/generated-readable/"+n] for n in NATIVE},"independent complete control source replay differs")
    owned,owner_proof=owner.transform(baseline,publication)
    require(owner.restore(owned,owner_proof,publication)==baseline and equal(owner_proof,record.get("owner_proof")) and
        inventory(baseline)==record.get("baseline_source") and inventory(owned)==record.get("owner_source"),"independent owner chain/inverse/entry roles differ")
    _stored_generation_vectors(record,products,root,flags)
    require([v.get("name") for v in record.get("variants",[])]==["baseline","owner"],"exact control/owner variant pair required")
    seen=set();replayed=[];fresh=[];compressed=BOOTSTRAP in frozen_inputs
    for label,readable,variant in zip(("baseline","owner"),(baseline,owned),record["variants"]):
        require(variant.get("flags")==flags and variant.get("units")==list(UNITS),"declared variant flags/units differ")
        require(inventory(readable)==variant.get("source") and all(products[label+"/generated-readable/"+n]==d for n,d in readable.items()),
            "actual variant readable source differs")
        cpp,pp_receipt=_fresh_preprocess(preprocess(dict(readable),list(flags),list(MEMBERS),label),readable,flags,label,seen)
        fresh.append(pp_receipt)
        index=next(s["index"] for s in scopes if s["kind"]=="preprocess-single-"+label)
        entry_index=next(s["index"] for s in scopes if s["kind"]=="preprocess-entry-"+label)
        require(cpp["main.c"]==products["tool-"+str(index+1)+"-preprocess-single-"+label+".stdout"] and
            cpp["start.S"]==products["tool-"+str(entry_index+1)+"-preprocess-entry-"+label+".stdout"] and
            pin(cpp["main.c"])==variant.get("preprocessed"),"fresh and original complete preprocessing differ")
        emitted={"main.c":minifier.compact_source(cpp["main.c"],"c"),"start.S":cpp["start.S"],"image.ld":readable["image.ld"]}
        require(inventory(emitted)==variant.get("raw_pre_identifier_source"),"raw pre-identifier bytes differ")
        legacy=selected.get("identifier_native_gate",{});renames=legacy.get("accepted_renames",{})
        require(isinstance(renames,dict) and len(set(renames.values()))==len(renames) and all(
            isinstance(a,str) and isinstance(b,str) and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*",a) and
            re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*",b) for a,b in renames.items()),"finite injective original identifier map required")
        require(not set(renames.values()).intersection(lexical._ANY_WORD.findall(emitted["main.c"].decode())),"original identifier map captures a spelling")
        if label=="baseline":require({"main.c":pin(emitted["main.c"])}==legacy.get("before"),"raw control before-stage pin differs")
        mapped={"main.c":emitted["main.c"]}
        for old,new in renames.items():mapped=lexical._replace(mapped,old,new)
        emitted.update(mapped)
        if label=="baseline":
            require(inventory(emitted)==selected.get("shipping_inputs") and
                emitted=={n:frozen_inputs["selection/shipping-inputs/"+n] for n in emitted} and
                {"main.c":pin(emitted["main.c"])}==legacy.get("after"),"actual complete v8 shipping replay differs")
        require(variant.get("legacy_identifier_map_capture_free") is True and variant.get("selected_shipping_replayed") is (label=="baseline") and
            equal(variant.get("legacy_control_identifier_map"),renames),"declared legacy stage differs")
        observations=[]
        def digest(c_files,trial):
            combined={**emitted,**c_files};tag=label+"/reducer/"+str(trial)
            linked,native,receipt=_fresh_compile(compile_identity(dict(combined),list(flags),list(UNITS),tag),combined,flags,UNITS,tag,modules,seen)
            fresh.append(receipt);observations.append(dict(trial=trial,linked=pin(linked),stripped=pin(native),inputs=inventory(combined)))
            return pin(linked)["sha256"]
        reduced,reduction=reducer.reduce_sources({"main.c":emitted["main.c"]},digest,lexical,
            reserve=lexical._ANY_WORD.findall((emitted["start.S"]+emitted["image.ld"]).decode()))
        require(equal(reduction,variant.get("source_reduction")) and equal(observations,variant.get("reduction_observations")) and
            variant.get("reduction_digest_scope")=="complete linked ELF","all independent reducer byte/native stages must replay")
        emitted.update(reduced)
        require(inventory(emitted)==variant.get("shipping_inputs") and all(products[label+"/shipping-inputs/"+n]==d for n,d in emitted.items()),
            "actual final owner/control shipping bytes differ")
        linked_images=[];native_images=[]
        for repeat in range(2):
            tag=label+"/native-repeat/"+str(repeat)
            linked,native,receipt=_fresh_compile(compile_identity(dict(emitted),list(flags),list(UNITS),tag),emitted,flags,UNITS,tag,modules,seen)
            fresh.append(receipt);linked_images.append(linked);native_images.append(native)
            old=variant["native_rebuilds"][repeat]
            require(linked==products[label+"/attempt-"+str(repeat)+"/linked"] and native==products[label+"/attempt-"+str(repeat)+"/native"] and
                old==dict(linked=pin(linked),stripped=pin(native),linked_geometry=receipt["geometry"],native_geometry=receipt["native_geometry"]),
                "actual repeated linked/native identity or geometry differs")
        identity=dict(linked=pin(linked_images[0]),stripped=pin(native_images[0]))
        expected=BASELINE if label=="baseline" else OWNER
        require(linked_images[0]==linked_images[1] and native_images[0]==native_images[1] and identity==expected==variant.get("identity") and
            variant.get("native_reproduced") is True and variant.get("identity_is_selected_v8") is (label=="baseline") and
            variant.get("experimental_owner_class") is (label=="owner"),"separate typed owner/native registry differs")
        packages=_packages(label,emitted,flags,UNITS,native_images[0],variant["packages"],products,modules,compressed)
        replayed.append(dict(name=label,readable=readable,shipping=emitted,identity=identity,packages=packages,
            identifier_composition=_role_composition(renames,reduction)))
    scaled=_scaled_contract(record,frozen_inputs,products,modules,root,owned)
    old_cost={p["route"]:p["whole"]["bytes"] for p in replayed[0]["packages"]}
    savings={p["route"]:old_cost[p["route"]]-p["whole"]["bytes"] for p in replayed[1]["packages"]}
    require(savings==record.get("whole_savings") and any(n>0 for n in savings.values()) and record.get("cost_improved") is True,
        "actual route savings/conditional runtime scope differs")
    return dict(kind=OWNER_KIND,family="D",ownership_class="D-final-wait-own-exit-group-v1",
        ownership_policy="final-wait-equivalent-output",last_search_output_required=True,
        profile=profile.to_record(16),admission_source=admission_pin,
        source_admitted=True,native_admitted=True,package_generation_admitted=True,
        current_frozen_closure=inventory(current_inputs),selected_control=pin(frozen_inputs["selection/build.json"]),
        readable=owned,shipping=replayed[1]["shipping"],flags=list(flags),units=list(UNITS),
        production_proof=production_proof,owner_proof=owner_proof,identity=deepcopy(OWNER),
        identifier_composition=replayed[1]["identifier_composition"],packages=replayed[1]["packages"],
        whole_savings=savings,typed_original_scopes=scopes,fresh_commands=fresh,scaled_contract=scaled,
        ready_for_fresh_full_P4=True,fresh_full_artifact_runtime=False,rules_qualified=False,
        physical_placement_qualified=False,size_qualified=False,whole_artifact_qualified=False,selected=False)
