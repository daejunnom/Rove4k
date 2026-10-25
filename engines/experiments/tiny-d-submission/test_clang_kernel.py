#!/usr/bin/env python3
"""Bounded two-recipe Clang18 static-native experiment; no default adoption."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OWN=("build.py","storage.py","publication.py","process_owner.py","syscall_arity.py",
     "test_startup.py","test_process_owner.py","test_runtime_scaffold.py","packaging.py","clang_kernel.py","test_clang_kernel.py")


def pin(data):return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def normalized(path):
    data=Path(path).read_bytes().replace(b"\r\n",b"\n")
    if b"\r" in data:raise ValueError("lone CR in named Clang input")
    return data


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module


def snapshot_inputs():
    source_inputs=load("D_clang_source_inputs",HERE/"source_inputs.py")
    recipe_data=normalized(ROOT/source_inputs.RECIPE)
    recipe=json.loads(recipe_data)
    names=source_inputs.source_names(recipe)+(
        source_inputs.SELF,
        "engines/compact/tiny-entry-d/packer.py","engines/experiments/tcec-scope/build.py"
        )+tuple("engines/experiments/tiny-d-submission/"+n for n in OWN)
    inputs={n:normalized(ROOT/n) for n in names}
    inputs[source_inputs.RECIPE]=recipe_data
    return inputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if (sys.platform!="linux" or platform.machine()!="x86_64" or not args.out.is_absolute() or out.exists()
            or any((p/".git").exists() for p in (out,*out.parents))):
        parser.error("Linux x86-64 and new external output required")
    inputs=snapshot_inputs()
    out.mkdir()
    for n,d in inputs.items():
        path=out/"inputs"/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(d)
    executing=load("D_clang_frozen",out/"inputs/engines/experiments/tiny-d-submission/test_clang_kernel.py")
    executing.run_snapshot(out,inputs,ROOT)


def run_snapshot(out,inputs,current_root):
    mods={n:load("D_clang_"+n,HERE/(n+".py")) for n in
        ("source","build","storage","publication","process_owner","syscall_arity","test_startup",
         "test_process_owner","test_runtime_scaffold","packaging","clang_kernel")}
    source,builder,recipe,startup=mods["source"],mods["build"],mods["clang_kernel"],mods["test_startup"]
    hostmod=load("D_clang_host",ROOT/source.HOST)
    if pin(normalized(ROOT/source.HOST))["sha256"]!=source.HOST_SHA:raise ValueError("command owner differs")
    packer=load("D_clang_elf",source.CANONICAL/"packer.py")
    hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":240,"per_command_wall":35,"parent_CPU":150,"parent_CPU_hard":170,"child_CPU":20}
    compiler=Path("/usr/bin/clang-18");linker=Path("/usr/bin/ld")
    report=dict(kind=recipe.KIND,complete=False,frozen_execution=True,commands=[],variants=[],
        inputs={n:pin(d) for n,d in inputs.items()},compiler_path=str(compiler),compiler_image=pin(compiler.read_bytes()),
        linker_path=str(linker),linker_image=pin(linker.read_bytes()),LTO=False,
        gcc_control=dict(native_bytes=7248,native_sha256="449926a3abb7d671b031d1a2e0ffa6d18338cba683a4c4d309c655adc282948b",whole_bytes=5329,
                         scope="prior GCC13 source-owned arity-wake-immediate measured control; not Clang identity authority"),
        full_P4_runtime_qualified=False,rules_qualified=False,target22_qualified=False,selected=False,real_target_allocation=False)
    def save():(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=hostmod.Host(out,report,save)
    def run(command,*,cwd,kind,data=None):
        value=host.run(command,cwd=cwd,kind=kind,data=data);startup.require_execution(report["commands"][-1],0);return value
    try:
        report["compiler_version"]=run([str(compiler),"--version"],cwd=out,kind="clang-version").decode().splitlines()[0]
        if "clang version 18." not in report["compiler_version"]:raise ValueError("Clang18 required")
        report["linker_version"]=run([str(linker),"--version"],cwd=out,kind="linker-version").decode().splitlines()[0]
        api=source.production();profile=api.resource_profile("test-p4")
        files,proof=recipe.prepared(source,mods["storage"],startup,mods["process_owner"],mods["publication"],mods["syscall_arity"],profile)
        report["source_proof"]=proof
        shipping=out/"generated-readable";shipping.mkdir()
        for n,d in files.items():(shipping/n).write_bytes(d)
        (shipping/"main.c").write_bytes(recipe.DRIVER)
        for opt in recipe.OPTS:
            label="clang-O"+opt;directory=out/label;directory.mkdir();flags=recipe.flags(profile,opt);images=[];observations=[]
            trace=run([str(compiler),"-###",*flags,str(shipping/"main.c"),str(shipping/"start.S"),"-Wl,-T,"+str(shipping/"image.ld"),"-o",str(directory/"trace-only")],cwd=shipping,kind=label+"-driver-trace")
            for index in range(2):
                attempt=directory/("attempt-"+str(index));attempt.mkdir();program=attempt/"linked"
                run([str(compiler),*flags,str(shipping/"main.c"),str(shipping/"start.S"),"-Wl,-T,"+str(shipping/"image.ld"),"-o",str(program)],cwd=shipping,kind=label+"-native-"+str(index))
                linked=program.read_bytes();native=packer.strip_native(linked);(attempt/"native").write_bytes(native)
                observations.append(dict(linked=pin(linked),native=pin(native),elf_type=recipe.kernel_type(native),
                    linked_geometry=builder.kernel_geometry(packer,linked,profile.workers),native_geometry=builder.kernel_geometry(packer,native,profile.workers)))
                images.append((linked,native))
            if images[0]!=images[1]:raise ValueError("Clang actual native double reproduction differs")
            packages=[]
            for codec in ("alone","xz","xz-bcj"):
                whole,detail=mods["packaging"].package_native(images[0][1],codec)
                repeated,_=mods["packaging"].package_native(images[1][1],codec)
                if whole!=repeated:raise ValueError("Clang whole double reproduction differs")
                target=directory/("packed-"+codec);target.write_bytes(whole);target.chmod(0o700)
                packages.append(dict(codec=codec,whole=pin(whole),detail=detail,whole_reproduced=True))
            report["variants"].append(dict(name=label,flags=flags,units=list(recipe.UNITS),native_reproduced=True,
                native_observations=observations,packages=packages,source_inputs={n:pin(d) for n,d in files.items()},
                compiler_recipe_changed=True,old_native_hash_guard_used=False))
            save()
        best=min((p["whole"]["bytes"],v["name"],p["codec"]) for v in report["variants"] for p in v["packages"])
        report["best"]=dict(whole_bytes=best[0],variant=best[1],codec=best[2],delta_vs_control=best[0]-5329)
        report["cost_improved"]=best[0]<5329
        report["semantic_controls_deferred"]=not report["cost_improved"]
        report["stop_reason"]="concrete whole loss" if not report["cost_improved"] else "cost win requires separate actual rules/scaled-mechanism qualification"
        report["current_inputs_unchanged"]={n:normalized(current_root/n)==d for n,d in inputs.items()}
        if not all(report["current_inputs_unchanged"].values()):raise ValueError("producer changed during finite cohort")
        for row in report["commands"]:startup.require_execution(row,0)
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
    print(json.dumps(dict(complete=report["complete"],best=report["best"],cost_improved=report["cost_improved"],selected=False)),flush=True)


if __name__=="__main__":main()
