"""Closed initial-PR21 structural admission above a real fresh Square parent.

Cost JSON is immutable comparison data. Only fresh source/compile/semantic and
startup callbacks can mint this distinct capability; historical maps stay closed.
"""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
import lzma
from pathlib import Path, PurePosixPath
import re
import sys
from types import CodeType, FunctionType, GetSetDescriptorType, ModuleType

D="engines/experiments/tiny-d-submission/"
SELF=D+"structural_admission.py"
PARENT=D+"square_successor_admission.py"
BRIDGE=D+"structural_carrier.py"
KIND="rove4k.D-structural-source.v1"
PARENT_KIND="rove4k.D-square-successor-source.v1"
SELECTOR="full"
ROUTE="packed-xz-bcj-pb0"
OPTIONS=["previous-piece","unsigned-history"]
POLICY="TCEC-minimum-immediate-process-exit"
INPUT_CONTRACT="TCEC-valid-non-NUL-lines-at-most-32767-bytes"
READABLE=("tiny.h","board.c","search.c","runtime.c","start.S","image.ld")
SHIPPING=("main.c","start.S","image.ld")
UNITS=("main.c","start.S")
SELECTION={"board":["value-fold-center","make-half","rights-packed","walk-ranges",
    "walk-castle-rights","walk-signed-piece","add-do","material-signature-loop"],
    "search":["moves432","eval_bound","mate_helper_noinline","tt_bound_select"],
    "runtime":["notation-inverse","direct-output","counted-output","number-limit",
        "keys-own","noinline-allocate","shared-resolver"]}
TRANSFORMS={
    D+"structural_board.py":{"bytes":27490,"sha256":"a20112fa0dae2267d67da61441400c64d2dedacb9e598ca8e6405dc333b6b9c0"},
    D+"structural_search.py":{"bytes":17077,"sha256":"f969737151f3539705d2301d572123029f0263c94e0aac89fb2af5c4f93a22ad"},
    D+"structural_runtime.py":{"bytes":21743,"sha256":"67138969f5abf70688cb5ed4f67d0c9d9f2e19aa7f673f5b678f63545c12a877"}}
HARNESS=D+"structural_size.py"
HARNESS_PIN={"bytes":19718,"sha256":"4d3b239caa6d3fd988d5922635e4c498295f3197c27dfa92470b4c08c08d4fa8"}
PARENT_SOURCE={"bytes":37973,"sha256":"b30e1b98343a97529bc3f3ce7bb572d24478d71f2702017cc6932415701779ee"}
COST={"control":{"bytes":56870,"sha256":"6b32df137db75fb4ee9751c56bae1792032b48ed08387bacf3a7995d23b216fb"},
      "full":{"bytes":56884,"sha256":"5510c08485b5f0a4bc7edf7989d1aa907df0bc49d8e0cbca87d1a7a04ecac728"}}
IDENTITY={"linked":{"bytes":7008,"sha256":"016a0b753b0a9c79a3dc5faacb16507cf675da5e73169230de403e37d2921295"},
          "stripped":{"bytes":6656,"sha256":"6d67cc6d64b4d3fb66afa33d78afcebff34eaa788570a06a0ad754dd6d8efbd5"}}
WHOLE={"bytes":4909,"sha256":"2de1e291393f59977393ae7a9e99754d8ec661b8c57d8c25989070ce8302205d"}
# This immutable comparison entry retains the original raw-CRLF experiment.
# Current admission consumes only the independently reproduced committed LF cohort.
HISTORICAL_144AD={"cost":deepcopy(COST),"transforms":deepcopy(TRANSFORMS),"harness":deepcopy(HARNESS_PIN),
    "identity":deepcopy(IDENTITY),"whole":deepcopy(WHOLE),"cohort":"historical raw CRLF; not current LF authority"}
TRANSFORMS={
    D+"structural_board.py":{"bytes":26842,"sha256":"c988f05cf18f5d9710204b6464ab53d4972824a59b631d7a4dafb868902e0595"},
    D+"structural_search.py":{"bytes":16838,"sha256":"2b3e874e1cc7f3f4e0902bb0f799bb6b0f78840f4404176bc1442c2657e92be1"},
    D+"structural_runtime.py":{"bytes":21364,"sha256":"000cc9cf56518574479e18672810ab95d82ab62a49de7d6f606786e14a3fb65a"}}
NEXT_TRANSFORMS={
    D+"structural_board_next.py":{"bytes":23995,"sha256":"25e65e641ef806f4c49fb2245ba53e21bc67f371ddcf71fa08c0bf90bf4fb5c3"},
    D+"structural_search_next.py":{"bytes":20395,"sha256":"8de9083fe73e2abef96382567cbdbe5b3a29892fb003ce2b903b86d4e45c9ae6"},
    D+"structural_platform.py":{"bytes":16797,"sha256":"89badb65c686d012b0c23ce2419b068d47a7a9c19865450e6eb97cd361731c5f"}}
HARNESS_PIN={"bytes":19309,"sha256":"4723b27096973c59e98098ffbd3c69655eb29ba35c17ced3843084b78cf64f0d"}
COHORT_PIN={"bytes":29894,"sha256":"2934d045eaf99ce0a4dbffa9468331a93be69825684235ee9c647e91cd3d4dc5"}
COMMIT="d954f3b8ad9c8f1de7c637d85b5327f6b131faf4"
COST={"control":{"bytes":60145,"sha256":"e04ec1b264be0bda621d13e275a782357def6044dbbefb057cb45c9491a9ddb1"},
      "fast-capacity":{"bytes":60428,"sha256":"8f02eb479b8273ff457c6ad4842d4e4ca9a64ba402c307a362fdcb98090db107"}}
WHOLE_RECEIPTS={"control":{"bytes":6423,"sha256":"6060689731c29483d86b6da78f325065ac99e2021086f794d891f38d935ef1eb"},
    "fast-capacity":{"bytes":6424,"sha256":"dc54915f1b9eebbcd590dd28e8f4f36d49c1a36fc34a53b3753715fbc5206979"}}
FAST_SELECTION={**SELECTION,"board_next":["mode-sign-sentinel","material-table","start-precomputed"],
    "search_next":["terminal_first_late_check","root_current","capacity413"],
    "platform":["fixed-worker-entry","abort-startup","nul-tokens"]}
FAST_IDENTITY={"linked":{"bytes":6816,"sha256":"548acb314429f506fe0db89ed67c607684001e0bd56bbfddeac123c00b5e66b1"},
    "stripped":{"bytes":6464,"sha256":"66f79c85ef322611b193a13ff85dd410a90779cb32c4f63dcde33f4897c0fe17"}}
FAST_WHOLE={"bytes":4737,"sha256":"f7a34bd51c186a328f7146e00d092e562eddc4217e145b6a350d6a4755fcd5f0"}
FAST_ROUTE="packed-xz-bcj-hc3-unnamed"
CODEC={"path":D+"structural_codec.py","pin":{"bytes":5425,"sha256":"09a00445ab551b4c212e9e46e506878c02101fff653a16193b782c658a4eae65"},
    "config":{"lc":0,"lp":0,"pb":0,"mf":3,"nice_len":32,"depth":64}}
VARIANTS={"initial-full":{"variant":"initial-full","selector":"full","route":ROUTE,"selection":SELECTION,
    "identity":IDENTITY,"whole":WHOLE,"header":None,"codec":None,"nonreturning":False,"startup_argument_count":3,
    "board_contract":{"bytes":176,"material_offset":28,"hash_offset":32,"mailbox_offset":48,"moves":432,"material_owner":"put"}},
    "fast-capacity":{"variant":"fast-capacity","selector":"fast-capacity","route":FAST_ROUTE,"selection":FAST_SELECTION,
    "identity":FAST_IDENTITY,"whole":FAST_WHOLE,"codec":CODEC,"nonreturning":True,"startup_argument_count":2,
    "header":{"bytes":205,"sha256":"848c6636bf51635078cddf8ca2a94eae29e2b4d33153997d36ae11f523a0d84c"},
    "board_contract":{"bytes":176,"material_offset":28,"hash_offset":32,"mailbox_offset":48,"moves":413,"material_owner":"put",
        "initial_material_owner":"guarded source-derived precomputed start"}}}
FIELDS=("_valid","_record","_parent","_parent_module","_readable","_shipping","_images","_native","_linked")
_TOKEN=object()
_EXECUTING_CODE=sys._getframe().f_code


def require(value,message):
    if not value:raise ValueError(message)


def pin(data):
    require(type(data) is bytes,"actual immutable evidence bytes required")
    return {"bytes":len(data),"sha256":sha256(data).hexdigest()}


def inventory(files):return {name:pin(data) for name,data in sorted(files.items())}


def equal(a,b):return json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)


def variant_contract(name):
    require(type(name) is str and name in VARIANTS,"explicit closed Structural variant required")
    return deepcopy(VARIANTS[name])


def cohort_record(raw):
    require(pin(raw)==COHORT_PIN,"reviewed committed LF source manifest required")
    record=json.loads(raw)
    require(record.get("source_commit")==COMMIT and record.get("source_count")==48 and
        len(record.get("files",{}))==48 and record.get("all_current_LF_matches_committed") is True and
        record.get("source_imports") is False,"exact independently exported committed LF cohort required")
    return record


def source(module,pair,logical,expected=None):
    """Authenticate source, functions and direct class storage before methods."""
    require(type(module) is ModuleType,"actual registered executing module required")
    namespace=module.__dict__
    require(type(namespace.get("__name__")) is str and sys.modules.get(namespace["__name__"]) is module,
            "actual registered executing module required")
    require(type(pair) is dict and set(pair)=={"current","frozen"} and
            type(pair["current"]) is bytes and pair["current"]==pair["frozen"],"current/frozen source differs")
    require(type(namespace.get("__file__")) is str,"actual module source path required")
    path=Path(namespace["__file__"]);parts=PurePosixPath(logical).parts
    require(path.parts[-len(parts):]==parts,"executing source occupies another role")
    raw=pair["frozen"];code=compile(raw,str(path),"exec",dont_inherit=True)
    require(namespace.get("_EXECUTING_CODE")==code,"executing module frame differs")
    if expected is not None:require(pin(raw)==expected,"reviewed executing source pin differs")
    for item in code.co_consts:
        if not isinstance(item,CodeType) or item.co_name.startswith("<"):continue
        if item.co_flags&2:
            fn=namespace.get(item.co_name)
            require(type(fn) is FunctionType and fn.__code__==item and fn.__globals__ is module.__dict__,
                    "executing source function differs")
        elif item.co_name in ("StructuralAdmission","SquareAdmission","NoTidAdmission","SearchAdmission"):
            cls=namespace.get(item.co_name)
            require(type(cls) is type and cls.__bases__==(object,) and cls.__name__==cls.__qualname__==item.co_name and
                cls.__module__==module.__name__ and
                not any(n in cls.__dict__ for n in ("__getattribute__","__getattr__","__slots__",*FIELDS)) and
                type(cls.__dict__.get("__dict__")) is GetSetDescriptorType and cls.__dict__["__dict__"].__objclass__ is cls,
                "direct typed authority storage differs")
            for method in item.co_consts:
                if isinstance(method,CodeType) and method.co_flags&2 and not method.co_name.startswith("<"):
                    fn=cls.__dict__.get(method.co_name)
                    if isinstance(fn,property):fn=fn.fget
                    require(type(fn) is FunctionType and fn.__code__==method and fn.__globals__ is module.__dict__,
                            "typed authority method differs")
    return raw


def instance_fields(token,cls):
    require(type(token) is cls,"exact typed authority required")
    data=object.__getattribute__(token,"__dict__")
    require(type(data) is dict and set(data)==set(FIELDS),"unminted or shadowed authority storage rejected")
    return data


def validate_parent(parent,module,pair):
    source(module,pair,PARENT,PARENT_SOURCE)
    require(module.KIND==PARENT_KIND and type(parent) is module.SquareAdmission,"real fresh Square parent required")
    data=instance_fields(parent,module.SquareAdmission)
    require(data["_valid"] is module._TOKEN and type(data["_record"]) is str and
            type(data["_parent_module"]) is ModuleType,"foreign Square nonce rejected before evidence or paths")
    # The genuine Square validator recursively authenticates unchanged NoTid/Search.
    require(module.SquareAdmission.assert_valid(parent) is parent,"fresh parent validation failed")
    record=module.SquareAdmission.to_record(parent)
    require(record.get("kind")==PARENT_KIND and record.get("selector")=="successor" and record.get("options")==OPTIONS and
            record.get("ownership_policy")==POLICY and record.get("input_contract")==INPUT_CONTRACT and
            record.get("last_search_output_required") is False,"Square parent scope differs")
    module.validate_profile(record["profile"])
    return record


def cost_records(raw):
    require(type(raw) is dict and set(raw)==set(COST),"exact control/full cost receipts required")
    result={}
    for name,data in raw.items():
        require(pin(data)==COST[name],"reviewed initial-144ad cost receipt differs")
        result[name]=json.loads(data)
    return result


def whole_records(raw):
    require(type(raw) is dict and set(raw)==set(WHOLE_RECEIPTS),"exact canonical LF whole receipts required")
    result={}
    for label,data in raw.items():
        require(pin(data)==WHOLE_RECEIPTS[label],"reviewed single known recipe receipt differs")
        row=json.loads(data);expected=IDENTITY if label=="control" else FAST_IDENTITY
        require(row.get("complete") is True and row.get("mode")=="single-known-recipe" and
            type(row.get("tried")) is int and row["tried"]==1 and row.get("source_cost")==COST[label] and
            row.get("native")==expected["stripped"] and row.get("host_cleanup")=={"unsettled_commands":0,"errors":[]} and
            all(row.get(n) is False for n in ("engine_executed","runtime_qualified","selected")),"settled single known recipe comparison required")
        require(row.get("tools",{}).get("structural_codec.py")==CODEC["pin"] and
            row["tools"].get("structural_size.py")==HARNESS_PIN,"whole generation source cohort differs")
        result[label]=row
    return result


def whole_evidence_names():
    return tuple(label+"/"+name for label in COST for name in ("default-1","default-2","best-unnamed","repeat-unnamed"))


def validate_wholes(records,products,stored):
    require(set(products)==set(whole_evidence_names()),"exact complete whole-generation products required")
    for label,row in records.items():
        native=stored[label]["native"]
        require([r.get("native_generation") for r in row["default_runs"]]==[1,2] and
            [r.get("native_generation") for r in row["single_runs"]]==[1,2],"two native-coupled whole generations required")
        for role,names in (("default_runs",("default-1","default-2")),("single_runs",("best-unnamed","repeat-unnamed"))):
            for observed,name in zip(row[role],names):
                whole=products[label+"/"+name];extent=observed["header_bytes"];inverse=observed["inverse"]
                require(pin(whole)=={k:observed[k] for k in ("bytes","sha256")} and 0<extent<len(whole) and
                    pin(whole[:extent])==inverse["header"] and pin(whole[extent:])==inverse["payload"],"archived entire header/payload differs")
                decoder=lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
                decoded=decoder.decompress(whole[extent:],max_length=len(native)+1)
                require(decoder.eof and not decoder.unused_data and decoder.check==lzma.CHECK_CRC64 and decoded==native and
                    inverse.get("strict_EOF") is True and inverse.get("trailing_bytes")==0 and
                    inverse.get("complete_native_inverse") is True and inverse.get("decoded")==pin(native),"archived strict complete native inverse differs")
                if role=="single_runs":
                    require(extent==205 and inverse["header"]==VARIANTS["fast-capacity"]["header"] and
                        observed.get("config")==CODEC["config"] and observed.get("unnamed_memfd") is True and
                        observed.get("dict_size")==8192,"single HC3 unnamed recipe differs")
            require(products[label+"/"+names[0]]==products[label+"/"+names[1]],"entire whole-generation repeats differ")


def evidence_names(records):
    """Finite pinned archived products; JSON names never discover arbitrary files."""
    require(type(records) is dict and set(records)==set(COST),"two reviewed cost cases required")
    names=set()
    for label in COST:
        row=records[label]
        require(pin((json.dumps(row,indent=2)+"\n").encode())==COST[label],"exact cost data required before names")
        names.update(label+"/generated-readable/"+n for n in READABLE)
        names.update(label+"/shipping-inputs/"+n for n in SHIPPING)
        for directory in ("gate-baseline","gate-typedefs","gate-batch-alpha","native","repeat"):
            names.update(label+"/"+directory+"/"+n for n in (*SHIPPING,"linked","native"))
        names.update(label+"/"+route for route in ("source-jit","source-jit-compressed","packed-xz-bcj",ROUTE))
        for i,command in enumerate(row["commands"],1):
            for stream in ("stdout","stderr"):
                names.add(label+"/tool-"+str(i)+"-"+command["kind"]+"."+stream)
            if command["kind"]=="cpp":names.add(label+"/tool-"+str(i)+"-cpp.stdin")
    return tuple(sorted(names))


def transform(parent_files,modules,frozen,variant="initial-full"):
    require(set(parent_files)==set(READABLE),"complete fresh Square readable cohort required")
    contract=variant_contract(variant)
    output=dict(parent_files);stages=[]
    roles=("board","search","runtime")+(("board_next","search_next","platform") if variant=="fast-capacity" else ())
    for role in roles:
        logical=D+"structural_"+role+".py";module=modules["structural_"+role]
        raw=frozen[logical];expected={**TRANSFORMS,**NEXT_TRANSFORMS}[logical]
        require(b"\r" not in raw and pin(raw)==expected,"reviewed canonical LF structural transform differs")
        require(type(module) is ModuleType,"actual structural module required")
        namespace=module.__dict__
        require(type(namespace.get("__name__")) is str and sys.modules.get(namespace["__name__"]) is module and
                type(namespace.get("__file__")) is str,"actual structural module required")
        path=Path(namespace["__file__"])
        require(path.parts[-4:]==("engines","experiments","tiny-d-submission","structural_"+role+".py") and
                path.read_bytes().replace(b"\r\n",b"\n")==raw,"structural executing source differs")
        for item in compile(raw,str(path),"exec",dont_inherit=True).co_consts:
            if isinstance(item,CodeType) and item.co_flags&2 and not item.co_name.startswith("<"):
                fn=namespace.get(item.co_name)
                require(type(fn) is FunctionType and fn.__code__==item and fn.__globals__ is module.__dict__,
                        "structural function binding differs")
        selected=contract["selection"][role]
        if role!="platform":
            best=tuple(selected[:-1]) if role=="search_next" else tuple(selected)
            require(namespace.get("BEST")==best,"closed reviewed selection differs")
        else:require(set(selected)<=set(namespace.get("OPTIONS",{})),"reviewed platform selection absent")
        before=inventory(output);output=module.apply(dict(output),tuple(selected))
        require(set(output)==set(READABLE) and all(type(d) is bytes for d in output.values()),"structural output cohort differs")
        stages.append({"role":role,"selection":list(selected),"source":pin(raw),"input":before,"output":inventory(output)})
    require(output["image.ld"]==parent_files["image.ld"] and
        (variant=="fast-capacity" or output["start.S"]==parent_files["start.S"]),"unreviewed startup ASM/linker change")
    require(("#define MOVES "+str(contract["board_contract"]["moves"])).encode() in output["tiny.h"] and
            b"unsigned material; uint64_t h,r; int8_t b[128];" in output["tiny.h"],"selected capacity/layout absent")
    return output,{"kind":KIND+".source-composition","variant":variant,"parent":inventory(parent_files),"stages":stages,"output":inventory(output)}


def archived_packages(row,products,label):
    require(set(row["packages"])=={"source-jit","source-jit-compressed","packed-xz-bcj",ROUTE},"exact archived package roles required")
    for route,detail in row["packages"].items():
        require(pin(products[label+"/"+route])=={k:detail[k] for k in ("bytes","sha256")},"archived complete package bytes differ")


def _stored(records,products,parent,baseline,modules,old,root):
    require(set(products)==set(evidence_names(records)),"exact archived product scope required")
    results={};legacy=parent.identifier_composition["legacy"];flags=parent.to_record()["flags"]
    for label in COST:
        row=records[label];directory=root+"/"+label
        require(row.get("complete") is True and row.get("profile")=="test-p4" and row.get("workers")==4 and
            row.get("flags")==flags and row.get("host_cleanup")=={"unsettled_commands":0,"errors":[]} and
            all(row.get(n) is False for n in ("engine_executed","runtime_qualified","selected")) and
            row.get("harness")==HARNESS_PIN,"settled initial P4 cost data required")
        kinds=["compiler","cpp","assembly-cpp","reduce-baseline","reduce-typedefs","reduce-batch-alpha","native","native-repeat"]
        require([r.get("kind") for r in row["commands"]]==kinds,"exact eight archived cost command roles required")
        for i,command in enumerate(row["commands"],1):
            old.settled(command)
            for stream in ("stdout","stderr"):
                name="tool-"+str(i)+"-"+command["kind"]+"."+stream
                require(command[stream]["path"]==directory+"/"+name and
                        {k:command[stream][k] for k in ("bytes","sha256")}==pin(products[label+"/"+name]),"archived raw pipe differs")
        files={n:products[label+"/generated-readable/"+n] for n in READABLE}
        require(inventory(files)==row["input"],"archived readable input differs")
        cpp=row["commands"][1];assembly=row["commands"][2];rawdir=directory+"/generated-readable"
        driver=b'#include "board.c"\n#include "search.c"\n#include "runtime.c"\n'
        require(cpp["command"]==["cc","-E","-P",*flags,"-I",rawdir,"-x","c","-"] and
                assembly["command"]==["cc","-E","-P","-x","assembler-with-cpp",rawdir+"/start.S"] and
                cpp["cwd"]==assembly["cwd"]==rawdir and products[label+"/tool-2-cpp.stdin"]==driver,"archived CPP source/argv differs")
        emitted={"main.c":modules["minifier"].compact_source(products[label+"/tool-2-cpp.stdout"],"c"),
                 "start.S":products[label+"/tool-3-assembly-cpp.stdout"],"image.ld":files["image.ld"]}
        require(not set(legacy.values()).intersection(modules["lexical"]._ANY_WORD.findall(emitted["main.c"].decode())),"legacy capture")
        mapped={"main.c":emitted["main.c"]}
        for before,after in legacy.items():mapped=modules["lexical"]._replace(mapped,before,after)
        emitted.update(mapped)
        def compiled(contents,sub,command):
            path=directory+"/"+sub
            require(command["cwd"]==path and command["command"]==["cc",*flags,path+"/main.c",path+"/start.S",
                    "-Wl,-T,"+path+"/image.ld","-o",path+"/linked"] and
                    all(products[label+"/"+sub+"/"+n]==d for n,d in contents.items()),"archived source/compile argv differs")
            linked=products[label+"/"+sub+"/linked"];native=products[label+"/"+sub+"/native"]
            require(modules["packer"].strip_native(linked)==native,"archived full native inverse differs")
            modules["builder"].kernel_geometry(modules["packer"],native,4)
            return linked,native
        def digest(contents,trial):
            command=row["commands"][3+("baseline","typedefs","batch-alpha").index(trial)]
            return pin(compiled({**emitted,**contents},"gate-"+trial,command)[0])["sha256"]
        reduced,reduction=modules["reducer"].reduce_sources({"main.c":emitted["main.c"]},digest,modules["lexical"],
            reserve=modules["lexical"]._ANY_WORD.findall((emitted["start.S"]+emitted["image.ld"]).decode()))
        emitted.update(reduced)
        require(equal(reduction,row["reduction"]) and inventory(emitted)==row["shipping"] and
                all(products[label+"/shipping-inputs/"+n]==d for n,d in emitted.items()),"archived reducer/shipping differs")
        images=[compiled(emitted,sub,row["commands"][6+i]) for i,sub in enumerate(("native","repeat"))]
        require(images[0]==images[1] and row["native_runs"]==[{"linked":pin(a),"native":pin(b)} for a,b in images],"archived repeated image differs")
        archived_packages(row,products,label)
        if label=="control":require(files==baseline,"cost control must equal initial full derived from genuine fresh Square")
        expected=IDENTITY if label=="control" else FAST_IDENTITY
        require({"linked":pin(images[0][0]),"stripped":pin(images[0][1])}==expected,"reviewed canonical LF native identity differs")
        results[label]={"readable":files,"shipping":emitted,"linked":images[0][0],"native":images[0][1],"reduction":reduction}
    require(pin(products["control/"+ROUTE])==WHOLE,"initial full PB0 complete package differs")
    return results


def nul_resolver_probe(before,after,runtime):
    """Reuse the finite helper driver with actual NUL function bodies/signatures."""
    names=("scan","word","number","amount","text","resolve_move","parse_apply","first")
    units=[]
    for files,prefix,nul in ((before,"ref_",False),(after,"new_",True)):
        text=files["runtime.c"].decode()
        code="\n".join(runtime._function(text,name) for name in names if
            re.search(r"^static [^{\n]*\b"+name+r"\([^{}\n]*\)\s*\{",text,re.M))+"\n"
        go=runtime._function(text,"go");begin=go.index("    char *cursor=s;" if nul else "    const char *cursor=s;")
        end=go.index("#if DEV\n    if(!infinite)",begin)
        code+=("static void parse_clock(char *s,int side,uint64_t out[3]){uint64_t clock=0,inc=0,budget=0;"
            "int present=0;position.s=side;\n"+go[begin:end]+"out[0]=clock;out[1]=inc;out[2]=present;}\n")
        for name in (*names,"parse_clock"):
            code=re.sub(r"\b"+name+r"\b",prefix+name,code)
        if nul:code="typedef char *new_Span;\n"+re.sub(r"\bSpan\b","new_Span",code)
        units.append(code)
    main=runtime._PROBE_MAIN
    for old,new in (("new_number(t)","new_number((char *)s)"),
        ("new_parse_apply(&in,t,&b)","new_parse_apply(&in,(char *)s,&b)"),
        ("uint64_t a[3],b[3];","uint64_t a[3],b[3];char copy[32768];"),
        ("new_parse_clock(s,side,b);","strcpy(copy,s);new_parse_clock(copy,side,b);")):
        main=runtime._replace_exact(main,old,new)
    extra=r'''
 char owned[]="a2a3 b2b3";char *cursor=owned;Board input={1,0},child;
 legal=1;pool_count=-1;listed=MOVE(16,32,0);
 if(!new_parse_apply(&input,new_scan(&cursor),&child)||child.witness!=listed)return 7;
 listed=MOVE(17,33,0);
 if(!new_parse_apply(&input,new_scan(&cursor),&child)||child.witness!=listed||*new_scan(&cursor))return 8;
 char boundary[32768];memset(boundary,' ',32767);boundary[32767]=0;
 memcpy(boundary,"wtime 30000 winc 20 ",19);check_clock(boundary);
 memset(boundary,'x',32767);boundary[32767]=0;check_move(boundary);check_num(boundary);
'''
    marker=' printf("{\\"numeric_cases\\"'
    require(main.count(marker)==1,"finite helper summary boundary differs")
    main=main.replace(marker,extra+marker,1)
    return (runtime._PROBE_PREFIX+"\n".join(units)+main).encode()


def terminal_search_driver(driver,files,board,*,only=False):
    """Observe actual terminal/cancellation paths without altering normalized rows."""
    call=(b"fixture_worker.current=0;int score=search(&fixture_worker,&position,2,-MATE,MATE,ply,6);" if
        b"Move best,current;" in files["tiny.h"] else
        b"Move best=0;int score=search(&fixture_worker,&position,2,-MATE,MATE,ply,6,&best);")
    helper=b'''
static void check_terminal_search(void){
    for(int kind=0;kind<3;kind++)for(int half=0;half<=100;half+=100)for(int edge=0;edge<2;edge++){
        int ply=edge?PLY-1:0;if(!kind&&!half&&!edge)continue;
        Board position={0};
        if(!kind)start(&position);
        else{
            position.s=-1;position.e=-1;
            put(&position,119,-6);put(&position,kind==1?85:86,6);put(&position,kind==1?102:101,5);
            position.h^=state(&position);position.r=position.h;
        }
        position.half=half;
        Move list[MOVES];Board child;int count=gen(&position,list),legal=0;
        for(int i=0;i<count;i++)legal+=!!make(&position,list[i],&child);
        if((!kind&&!legal)||(kind&&legal)||(kind==1&&!attacked(&position,position.k[1],1))||
           (kind==2&&attacked(&position,position.k[1],1))){puts("BROKEN_TERMINAL_POSITION");abort();}
        for(int cancel=0;cancel<2;cancel++){
            memset(&fixture_worker,0,sizeof fixture_worker);memset(table,0,((size_t)1<<TT_BITS)*sizeof *table);
            fixture_worker.best=MOVE(16,32,0);fixture_worker.depth=7;
            game_length=1;game_keys[0]=position.h;expected_prior[ply]=6;
            test_claims=test_narrow=test_research=0;test_cancel_at=cancel?1:0;
            path_digest=UINT64_C(1469598103934665603);atomic_store(&stopped,0);
            TERMINAL_CALL
            int expected=cancel?0:kind==1?-MATE+ply:0;
            int expected_stopped=cancel||(!kind&&!half&&edge);
            if(score!=expected||atomic_load(&stopped)!=expected_stopped||fixture_worker.best!=MOVE(16,32,0)||fixture_worker.depth!=7){
                puts("BROKEN_TERMINAL_SEARCH");abort();
            }
        }
    }
}
'''.replace(b"TERMINAL_CALL",call)
    require(driver.count(b"int main(void){")==1,"actual terminal fixture main differs")
    if only:
        original=board.function(driver,b"int main(")
        replacement=b'int main(void){table=calloc((size_t)1<<TT_BITS,sizeof *table);if(!table)return 2;check_terminal_search();free(table);puts("STRUCTURAL_TERMINALS_OK");return 0;}'
        driver=driver.replace(original,replacement,1)
    else:
        marker=b"    free(table);return total_research?0:6;"
        require(driver.count(marker)==1,"actual PVS terminal check insertion boundary differs")
        driver=driver.replace(marker,b"    check_terminal_search();\n"+marker,1)
    return driver.replace(b"int main(void){",helper+b"\nint main(void){",1)


def observation_specs(readable,parent,proof,modules):
    """Closed component renderers; callback-produced C cannot choose its proof."""
    reference=parent.readable
    variant=proof["variant"];contract=variant_contract(variant)
    control=dict(reference)
    for role in ("board","search","runtime"):
        control=modules["structural_"+role].apply(control,tuple(SELECTION[role]))
    require(inventory(control)==proof["stages"][2]["output"],"actual initial full component control differs")
    probe=modules["probe"];board=modules["structural_board"];runtime=modules["structural_runtime"]
    projection={"kind":KIND+".semantic-source-projection","output":inventory(readable),"options":list(OPTIONS),"structural":proof}
    generated,driver,_=probe.render(readable,modules["source"],modules["storage_checker"],
        reference_board=reference["board.c"],variant_proof=projection,prefix=True,dense=False,
        union_order=False,previous_index=True,constant_start=False,unsigned_history=True)
    if variant=="fast-capacity":
        next_search=modules["structural_search_next"]
        driver=next_search.adapt_root_observer(driver,readable)
        dependencies=next_search.runtime_dependencies(readable)
        require(dependencies and driver.count(b'#include "search.c"')==1,"actual terminal resolver fixture boundary differs")
        driver=driver.replace(b'#include "search.c"',dependencies+b'\n#include "search.c"',1)
    driver=terminal_search_driver(driver,readable,board)
    control_generated=control_driver=None
    if variant=="fast-capacity":
        control_projection={"kind":KIND+".terminal-control","output":inventory(control),"options":list(OPTIONS)}
        control_generated,control_driver,_=probe.render(control,modules["source"],modules["storage_checker"],
            reference_board=reference["board.c"],variant_proof=control_projection,prefix=True,dense=False,
            union_order=False,previous_index=True,constant_start=False,unsigned_history=True)
        control_driver=terminal_search_driver(control_driver,control,board,only=True)
    cases,_=modules["structural_rules"].fixture_cases()
    lifecycle=board.render_lifecycle_probe(reference["board.c"],[" ".join(c["moves"]) for c in cases])
    helper=(modules["structural_platform"].render_token_probe(reference,readable) if variant=="fast-capacity" else
            runtime.render_helper_probe(reference,readable))
    values=[]
    signatures=(b"uint64_t mix(",b"int value(",b"static uint64_t piece(",b"static uint64_t state(",
        b"static unsigned material_piece(",b"static void put(",b"void start(")
    for name,files in (("reference",control),("actual",readable)):
        body=b"\n".join(board.function(files["board.c"],signature) for signature in signatures)
        for spelling in ("mix","value","piece","state","material_piece","put","start"):
            body=modules["lexical"]._replace({"driver.c":body},spelling,name+"_"+spelling)["driver.c"]
        values.append(body)
    mate=board.function(readable["search.c"],b"static __attribute__((noinline)) int mate_score(")
    require(b"#if MATE-PLY-1<=32*910\n" in readable["search.c"],"selected guarded evaluation clamp absent")
    scalar=(b'#include <stdio.h>\n#include <limits.h>\n#include "tiny.h"\n'+b"\n".join(values)+b"\n"+mate+b'''
static int reference_mate(int s,int p){if(s>MATE-PLY)s+=p;if(s< -MATE+PLY)s-=p;return s;}
int main(void){
    _Static_assert(MOVES==432,"selected pseudo move capacity");
    _Static_assert(sizeof(Board)==176 && offsetof(Board,material)==28 && offsetof(Board,h)==32 && offsetof(Board,b)==48,"selected Board layout");
    if(MATE-PLY-1<=32*910)return 1;
    Board before,after;reference_start(&before);actual_start(&after);
    if(before.s!=after.s||before.c!=after.c||before.e!=after.e||before.half!=after.half||before.v!=after.v||
       before.k[0]!=after.k[0]||before.k[1]!=after.k[1]||before.material!=after.material||before.h!=after.h||before.r!=after.r)return 4;
    for(int q=0;q<128;q++)if(before.b[q]!=after.b[q])return 5;
    for(int v=-6;v<=6;v++)if(v)for(int q=0;q<128;q++)if(!(q&0x88)){
        int a=actual_value(v,q);if(a!=reference_value(v,q)||a>910||a< -910)return 2;
        if(actual_material_piece(v,q)!=reference_material_piece(v,q))return 6;
    }
    const int scores[]={INT16_MIN,-MATE,-MATE+PLY-1,-MATE+PLY,-MATE+PLY+1,-1,0,1,MATE-PLY-1,MATE-PLY,MATE-PLY+1,MATE,INT16_MAX};
    const int plies[]={0,1,PLY-1};
    for(unsigned i=0;i<sizeof(scores)/sizeof(*scores);i++)for(unsigned p=0;p<sizeof(plies)/sizeof(*plies);p++)
        for(int direction=-1;direction<=1;direction+=2)if(mate_score(scores[i],direction*plies[p])!=reference_mate(scores[i],direction*plies[p]))return 3;
    puts("STRUCTURAL_SCALAR_OK");return 0;
}
''')
    scalar=scalar.replace(b"MOVES==432",("MOVES=="+str(contract["board_contract"]["moves"])).encode())
    result=[]
    components=("pvs","board-control","board-lifecycle","scalar-boundaries","protocol-helpers")+(("nul-resolver","terminal-search-control") if variant=="fast-capacity" else ())
    for component in components:
        for mode in (("ubsan",) if component in ("protocol-helpers","nul-resolver") else ("plain","ubsan")):
            sanitizers=["-fsanitize=undefined","-fno-sanitize-recover=all"] if mode=="ubsan" else []
            flags=["-std=c11","-O2","-g0","-fno-builtin","-msse4.2","-mcx16","-DDEV=0","-DD_HQ=0","-DWORKERS=4","-DTT_BITS=12"]
            if component=="pvs":
                files={**generated,"driver.c":driver}
                flags=probe.compiler_flags(prefix=True,dense=False,previous_index=True,unsigned_history=True,mode=mode)
            elif component=="terminal-search-control":
                files={**control_generated,"driver.c":control_driver}
                flags=probe.compiler_flags(prefix=True,dense=False,previous_index=True,unsigned_history=True,mode=mode)
            elif component.startswith("board-"):
                files={**(reference if component=="board-control" else readable),"driver.c":lifecycle}
                if component=="board-lifecycle":flags.append("-DCHECK_MATERIAL")
                flags+=sanitizers
            elif component=="scalar-boundaries":files={"tiny.h":readable["tiny.h"],"driver.c":scalar};flags+=sanitizers
            else:
                files={"driver.c":nul_resolver_probe(control,readable,runtime) if component=="nul-resolver" else helper}
                flags=["-std=c11","-O1",*sanitizers]
            result.append({"component":component,"mode":mode,"sources":files,"flags":flags})
    return result


def validate_observations(result,readable,parent,proof,modules,old,seen):
    """Admission requires fresh actual component commands, never passed JSON."""
    require(type(result) is dict and result.get("kind")==KIND+".observations" and
            result.get("input_pins")==inventory(readable) and equal(result.get("source_proof"),proof),"actual structural observation source differs")
    rows=result.get("components")
    specs=observation_specs(readable,parent,proof,modules)
    required=[(s["component"],s["mode"]) for s in specs]
    require(type(rows) is list and [(r.get("component"),r.get("mode")) for r in rows]==required,"exact fresh component modes required")
    output={}
    for row,spec in zip(rows,specs):
        require(row.get("sources")==spec["sources"] and row.get("flags")==spec["flags"],"fresh component fixture/flags differ from actual renderer")
        paths=row["source_paths"];directory=old.absolute(row["directory"]);binary=old.absolute(row["binary_path"])
        require(type(row.get("sources")) is dict and paths=={n:directory+"/"+n for n in row["sources"]},"actual component source paths differ")
        compiled,executed=row["compile"],row["execute"]
        old._fresh_paths(compiled,[directory,*paths.values(),binary],seen);old._fresh_paths(executed,[],seen)
        require(compiled["cwd"]==executed["cwd"]==directory and compiled["command"]==["cc",*row["flags"],paths["driver.c"],"-o",binary] and
                executed["command"]==[binary] and pin(row["output"])=={k:executed["stdout"][k] for k in ("bytes","sha256")} and
                type(row.get("binary")) is bytes and row["binary"] and executed["stderr"]["bytes"]==0,"actual component command/output differs")
        key=(row["component"],row["mode"])
        output[key]=modules["probe"].verify_output(row["output"])[0] if row["component"]=="pvs" else row["output"]
    require(pin(output["pvs","plain"])==parent.to_record()["semantic_observations"]["observations"] and
            output["pvs","plain"]==output["pvs","ubsan"],"fresh actual PVS differs from fresh Square parent")
    for name in ("board-control","board-lifecycle","scalar-boundaries"):
        require(output[name,"plain"]==output[name,"ubsan"],"plain/UBSan structural component differs")
    require(output["board-control","plain"]==output["board-lifecycle","plain"]==b"positions=418878 checksum=8dd4cbfc86c94b6b\n", "fresh Board lifecycle differs from actual fresh Square control")
    require(output["scalar-boundaries","plain"]==b"STRUCTURAL_SCALAR_OK\n","structural scalar boundary coverage absent")
    if proof["variant"]=="fast-capacity":
        helper=re.fullmatch(rb"numeric=([0-9]+) tokens=([0-9]+) clocks=([0-9]+)\n",output["protocol-helpers","ubsan"])
        require(helper is not None and all(int(n)>0 for n in helper.groups()),"actual NUL token/number/clock coverage absent")
        resolver=json.loads(output["nul-resolver","ubsan"])
        require(type(resolver) is dict and resolver.get("all_equal") is True and
            all(type(resolver.get(n)) is int and resolver[n]>0 for n in
                ("numeric_cases","clock_cases","notation_cases","first_cases")),"actual NUL resolver/order/boundary coverage absent")
        require(output["terminal-search-control","plain"]==output["terminal-search-control","ubsan"]==b"STRUCTURAL_TERMINALS_OK\n",
            "fresh full control terminal search/cancellation observations differ")
    else:
        helper=json.loads(output["protocol-helpers","ubsan"])
        require(type(helper) is dict and helper.get("all_equal") is True and all(type(helper.get(n)) is int and helper[n]>0 for n in
            ("numeric_cases","clock_cases","notation_cases","first_cases")),"structural boundary/helper coverage absent")
    # Keep immutable source/output/command witnesses, not callback assertions.
    return {"source_proof":deepcopy(proof),"pvs":pin(output["pvs","plain"]),
        "terminal_search":{"actual_candidate":True,"actual_full_control":proof["variant"]=="fast-capacity",
            "positions":"legal, checkmate, stalemate; half0/100; ply0/127; ordinary nonterminal root excluded",
            "cases_per_implementation":11,"first_claim_cancellation_cases_per_implementation":11,
            "search_best_and_depth_fields_preserved":True,
            "cancellation_scope":"direct actual search first claim; not think/publication loop"},"components":[{
        "component":r["component"],"mode":r["mode"],"source":inventory(r["sources"]),"binary":pin(r["binary"]),
        "output":pin(r["output"]),"normalized":pin(output[r["component"],r["mode"]]),
        "flags":list(r["flags"]),"commands":[deepcopy(r["compile"]),deepcopy(r["execute"])]} for r in rows]}


@dataclass(frozen=True,init=False)
class StructuralAdmission:
    def __init__(self,nonce,record,parent,parent_module,readable,shipping,images,native,linked):
        require(nonce is _TOKEN,"StructuralAdmission requires fresh explicit upper admission")
        for name,value in (("_valid",_TOKEN),("_record",json.dumps(record,sort_keys=True)),("_parent",parent),
            ("_parent_module",parent_module),("_readable",tuple(sorted(readable.items()))),
            ("_shipping",tuple(sorted(shipping.items()))),("_images",tuple(sorted(images.items()))),("_native",native),("_linked",linked)):
            object.__setattr__(self,name,value)

    def assert_valid(self):
        data=instance_fields(self,StructuralAdmission)
        require(data["_valid"] is _TOKEN and type(data["_parent_module"]) is ModuleType,"foreign structural nonce rejected before evidence/path")
        module=data["_parent_module"];require(type(module.__file__) is str,"actual Square source path required")
        path=Path(module.__file__);require(path.is_file() and path.stat().st_size<=1<<20,"bounded Square source required")
        raw=path.read_bytes().replace(b"\r\n",b"\n");parent_record=validate_parent(data["_parent"],module,{"current":raw,"frozen":raw})
        record=StructuralAdmission.to_record(self);module.validate_profile(record.get("profile"))
        contract=variant_contract(record.get("variant"))
        require(record.get("kind")==KIND and record.get("selector")==contract["selector"] and record.get("selected_route")==contract["route"] and
            record.get("structural_selection")==contract["selection"] and record.get("options")==OPTIONS and
            record.get("identity")==contract["identity"]=={"linked":pin(data["_linked"]),"stripped":pin(data["_native"])} and
            pin(StructuralAdmission.package_bytes(self,contract["route"]))==contract["whole"] and
            record.get("source_cohort")==COHORT_PIN and record.get("source_commit")==COMMIT and
            equal(record.get("parent_admission"),parent_record),"new structural identity/parent/cohort differs")
        require(record.get("ownership_policy")==POLICY and record.get("input_contract")==INPUT_CONTRACT and
            record.get("last_search_output_required") is False and record.get("nonreturning") is contract["nonreturning"] and
            record.get("board_contract")==contract["board_contract"] and
            record.get("new_three_argument_startup_admitted") is (contract["startup_argument_count"]==3) and
            record.get("new_fixed_entry_startup_admitted") is (contract["startup_argument_count"]==2) and
            all(record.get(k) is True for k in ("source_admitted","native_admitted","package_generation_admitted",
                "actual_search_semantics_admitted","actual_startup_mechanism_admitted")) and
            all(record.get(k) is False for k in ("fresh_full_artifact_runtime","rules_qualified","physical_placement_qualified",
                "size_qualified","strength_qualified","event_target_confirmed","selected")),"structural generation scope differs")
        return self

    def to_record(self):return json.loads(self._record)
    @property
    def parent(self):return self._parent
    @property
    def readable(self):return dict(self._readable)
    @property
    def shipping(self):return dict(self._shipping)
    @property
    def native(self):return self._native
    @property
    def linked(self):return self._linked
    @property
    def packages(self):return self.to_record()["packages"]
    @property
    def input_pins(self):return self.to_record()["input_pins"]
    @property
    def identifier_composition(self):return self.to_record()["identifier_composition"]
    @property
    def fresh_commands(self):return self.to_record()["fresh_commands"]
    def package_bytes(self,route):return dict(self._images)[route]


def admit_structural(parent,records,products,modules,*,frozen_inputs,current_inputs,admission_source,
                     parent_admission_module,parent_admission_source,bridge_source,evidence_root,
                     preprocess,compile_identity,observations_callback,startup_callback,variant="initial-full",
                     cohort_raw=None,whole_receipt_raw=None,whole_products=None,whole_evidence_root=None):
    require(all(callable(f) for f in (preprocess,compile_identity,observations_callback,startup_callback)),"fresh structural callbacks required")
    parent_record=validate_parent(parent,parent_admission_module,parent_admission_source)
    contract=variant_contract(variant);cohort=cohort_record(cohort_raw)
    own=source(sys.modules[__name__],admission_source,SELF)
    bridge=modules["structural_carrier"];bridge_raw=source(bridge,bridge_source,BRIDGE)
    require(set(parent.input_pins)|set(cohort["files"])<=set(frozen_inputs) and
        inventory({n:frozen_inputs[n] for n in parent.input_pins})==parent.input_pins and
        inventory({n:frozen_inputs[n] for n in cohort["files"]})==cohort["files"] and
        all(b"\r" not in frozen_inputs[n] for n in cohort["files"]) and
        frozen_inputs[PARENT]==parent_admission_source["frozen"] and pin(frozen_inputs[HARNESS])==HARNESS_PIN,
        "exact parent/current committed LF source join required; mixed cohorts rejected")
    require(current_inputs=={n:d for n,d in frozen_inputs.items() if n.startswith("engines/")},"current/frozen upper source closure differs")
    old=object.__getattribute__(parent.parent,"_parent_module")
    old._module_inputs(modules,{n:frozen_inputs[n] for n in parent.input_pins})
    baseline,baseline_proof=transform(parent.readable,modules,frozen_inputs,"initial-full")
    readable,proof=transform(parent.readable,modules,frozen_inputs,variant)
    root=old.absolute(evidence_root);stored=_stored(records,products,parent,baseline,modules,old,root)
    selected="control" if variant=="initial-full" else "fast-capacity"
    require(readable==stored[selected]["readable"],"fresh ordered transform differs from audited readable bytes")
    recipes=whole_records(whole_receipt_raw);validate_wholes(recipes,whole_products,stored)
    whole_root=old.absolute(whole_evidence_root)
    archived=[root+"/"+n for n in products]+[whole_root+"/"+n for n in whole_products]
    seen=parent_admission_module.used_paths(parent_record,[records,recipes],archived);reserved=sorted(seen);fresh=[];stages=[]
    flags=parent_record["flags"]
    legacy=parent.identifier_composition["legacy"]
    def replay_stage(stage_variant,files,case):
        stage_contract=variant_contract(stage_variant);begin=len(fresh);label="structural-"+stage_variant
        outputs,entry=old.fresh_preprocess(preprocess(dict(files),list(flags),list(old.MEMBERS),label),files,flags,label,seen)
        fresh.append(entry)
        emitted={"main.c":modules["minifier"].compact_source(outputs["main.c"],"c"),"start.S":outputs["start.S"],"image.ld":files["image.ld"]}
        mapped={"main.c":emitted["main.c"]}
        require(not set(legacy.values()).intersection(modules["lexical"]._ANY_WORD.findall(emitted["main.c"].decode())),"fresh legacy capture")
        for before,after in legacy.items():mapped=modules["lexical"]._replace(mapped,before,after)
        emitted.update(mapped)
        def digest(contents,trial):
            inputs={**emitted,**contents};tag=label+"/reduction/"+trial
            linked,native,entry=old.fresh_compile(compile_identity(inputs,list(flags),list(UNITS),tag),inputs,flags,UNITS,tag,modules,seen)
            fresh.append(entry);return pin(linked)["sha256"]
        reduced,reduction=modules["reducer"].reduce_sources({"main.c":emitted["main.c"]},digest,modules["lexical"],
            reserve=modules["lexical"]._ANY_WORD.findall((emitted["start.S"]+emitted["image.ld"]).decode()))
        emitted.update(reduced)
        require(emitted==stored[case]["shipping"] and equal(reduction,stored[case]["reduction"]),"fresh stage reducer/shipping differs")
        images=[]
        for i in range(2):
            tag=label+"/native-repeat/"+str(i)
            linked,native,entry=old.fresh_compile(compile_identity(dict(emitted),list(flags),list(UNITS),tag),emitted,flags,UNITS,tag,modules,seen)
            require((linked,native)==(stored[case]["linked"],stored[case]["native"]),"fresh complete stage native differs")
            images.append((linked,native));fresh.append(entry)
        require(images[0]==images[1],"fresh native repetitions differ")
        packages=[bridge.package_native(images[0][1],modules["packaging"],variant=stage_variant,
            admission_module=sys.modules[__name__],admission_source=admission_source,codec=modules["structural_codec"]) for _ in range(2)]
        whole,detail=packages[0]
        archived_whole=products["control/"+ROUTE] if case=="control" else whole_products[case+"/best-unnamed"]
        declared=records[case]["packages"][ROUTE] if case=="control" else {
            k:v for k,v in recipes[case]["single_runs"][0].items() if k not in ("native_generation","inverse")}
        require(packages[0]==packages[1] and pin(whole)==stage_contract["whole"] and whole==archived_whole and
            equal({**pin(whole),**detail},declared),"two fresh entire selected stage packages differ")
        stages.append({"variant":stage_variant,"readable":inventory(files),"shipping":inventory(emitted),"identity":deepcopy(stage_contract["identity"]),
            "route":stage_contract["route"],"whole":pin(whole),"whole_repeats":2,"commands":deepcopy(fresh[begin:])})
        return emitted,images[0],whole,detail,reduction
    initial=replay_stage("initial-full",baseline,"control")
    emitted,image,whole,detail,reduction=initial if variant=="initial-full" else replay_stage(variant,readable,selected)
    observations=validate_observations(observations_callback(dict(readable),parent=parent,source_proof=proof),readable,parent,proof,modules,old,seen)
    startup_label="structural-startup-abi" if contract["startup_argument_count"]==3 else "structural-fixed-startup-abi"
    startup=startup_callback(dict(readable),label=startup_label)
    generated,expected=bridge.render_startup_fixture(dict(readable),variant=variant,
        admission_module=sys.modules[__name__],admission_source=admission_source)
    require(startup.get("input_pins")==inventory(readable),"actual structural startup input differs")
    startup_observed=bridge.validate_startup_observation(startup,generated,expected,old=old,seen=seen)
    for row in observations["components"]:fresh.append({"kind":KIND+".fresh-component",**deepcopy(row)})
    fresh.append({"kind":KIND+".fresh-startup","input_pins":deepcopy(startup_observed["source"]),
        "commands":[deepcopy(startup_observed["compile"]),deepcopy(startup_observed["execute"])]})
    inputs=inventory(frozen_inputs);inputs.update({SELF:pin(own),BRIDGE:pin(bridge_raw)})
    record={"kind":KIND,"family":"D","variant":variant,"selector":contract["selector"],"selected_route":contract["route"],"structural_selection":deepcopy(contract["selection"]),
        "options":list(OPTIONS),"nonreturning":contract["nonreturning"],"profile":deepcopy(parent_record["profile"]),"flags":list(flags),"units":list(UNITS),
        "identity":deepcopy(contract["identity"]),"packages":[{"route":contract["route"],"whole":pin(whole),"detail":detail,"reproduced":True,"whole_repeats":2}],
        "input_pins":inputs,"admission_source":pin(own),"startup_fixture_authority":pin(bridge_raw),"parent_admission_source":PARENT_SOURCE,
        "parent_admission":deepcopy(parent_record),"source_proof":proof,"initial_full_source_proof":baseline_proof,"stage_replays":stages,
        "source_cohort":deepcopy(COHORT_PIN),"source_commit":COMMIT,"original_experiment":deepcopy(COST),"whole_experiment":deepcopy(WHOLE_RECEIPTS),
        "identifier_composition":old._composition(legacy,reduction),"reserved_evidence_paths":reserved,
        "fresh_commands":[*deepcopy(parent_record["fresh_commands"]),*fresh],"semantic_observations":observations,"startup_mechanism":startup_observed,
        "board_contract":deepcopy(contract["board_contract"]),
        "ownership_policy":POLICY,"input_contract":INPUT_CONTRACT,"last_search_output_required":False,"kernel_tid_handshake":False,
        **{k:True for k in ("source_admitted","native_admitted","package_generation_admitted","actual_search_semantics_admitted","actual_startup_mechanism_admitted")},
        "new_three_argument_startup_admitted":contract["startup_argument_count"]==3,
        "new_fixed_entry_startup_admitted":contract["startup_argument_count"]==2,
        **{k:False for k in ("fresh_full_artifact_runtime","rules_qualified","physical_placement_qualified","size_qualified","strength_qualified","event_target_confirmed","selected")},
        "scope":"closed committed LF structural P4 variant; fresh full carrier runtime still required"}
    return StructuralAdmission(_TOKEN,record,parent,parent_admission_module,readable,emitted,{contract["route"]:whole},image[1],image[0]).assert_valid()
