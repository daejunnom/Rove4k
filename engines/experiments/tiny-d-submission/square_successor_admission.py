"""Fresh typed admission for two closed 0x88 outer-loop openings.

A real, source-authenticated fresh NoTidAdmission is the parent. Archived cost
evidence supplies immutable data, never a reconstructed capability. This class
retains the no-libc persistent pool, atomic128 TT and complete engine logic.
"""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import ast
import json
import lzma
import math
from pathlib import Path, PurePosixPath
import sys
from types import CodeType, FunctionType, GetSetDescriptorType, ModuleType

KIND="rove4k.D-square-successor-source.v1"
PARENT_KIND="rove4k.D-no-TID-source.v1"
EXPERIMENT_KIND="rove4k.D-no-TID-square-successor-cost.v1"
SELECTOR="successor"
OPTIONS=["previous-piece","unsigned-history"]
D="engines/experiments/tiny-d-submission/"
SELF=D+"square_successor_admission.py"
PARENT_ADMISSION=D+"no_tid_admission.py"
BRIDGE=D+"square_successor_runtime.py"
CHANGE=D+"d_square_successor.py"
PROBE=D+"probe_d_square_successor.py"
COST_TEST=D+"test_d_square_successor.py"
READABLE=("tiny.h","board.c","search.c","runtime.c","start.S","image.ld")
SHIPPING=("main.c","start.S","image.ld")
UNITS=("main.c","start.S")
DRIVER=b'#include "board.c"\n#include "search.c"\n#include "runtime.c"\n'
RECEIPT={"bytes":238485,"sha256":"e5e08036e009753517639cf8c48b71b9c10af97435b3d38e92d6eb21662d5219"}
IDENTITY={
    "linked":{"bytes":7456,"sha256":"8eb2ae8f53038cf6555c294533260a1fd64f3c1d4c7d2f213e4116568c7ce401"},
    "stripped":{"bytes":7104,"sha256":"222d8cc534073f59e3bf3f7fa114302e39e9c3f0dbb33f03924a3c6d4b98f329"}}
PACKED={"bytes":5233,"sha256":"0b4fa4afee90cd8074bc93764e73e55474ae6a9e3605a879cdadb53aaa7902b4"}
PARENT_IDENTITY={
    "linked":{"bytes":7456,"sha256":"16deff54c4059f236c845191674f9b36c26139c032d23e66b53992fd11c3ebf3"},
    "stripped":{"bytes":7104,"sha256":"f0168f752eaa15bf011cbd75964ebe10bc39ca88ddd16eeed66c73e2cf59ed7b"}}
PARENT_PACKED={"bytes":5245,"sha256":"4dbe1bfbceb1c290ee45801e74fe44d7ef2148215b57d51141e1965d5e5db9fa"}
ORIGINAL_QUALIFICATION={"bytes":1537522,"sha256":"e9510a0a408321bfc6400e49df95d3cbbd9ef9a5cdc0b37ffaf44b46958d4b6f"}
ORIGINAL_STARTUP={"bytes":252355,"sha256":"0a09371a9a5eb0aac8644d18b24b2172742796f0789432d6d4771c86b2662241"}
PARENT_SOURCE={"bytes":34127,"sha256":"b68233f41e064c8c8cee25ba295bb697b93d46bfc98f3f0f6b3ea464e60f3b86"}
POLICY="TCEC-minimum-immediate-process-exit"
INPUT_CONTRACT="TCEC-valid-non-NUL-lines-at-most-32767-bytes"
FIELDS=("_valid","_record","_parent","_parent_module","_readable","_shipping","_images","_native","_linked")
_TOKEN=object()
_EXECUTING_CODE=sys._getframe().f_code


def require(value,message):
    if not value:raise ValueError(message)


def pin(data):
    require(type(data) is bytes,"actual immutable evidence bytes required")
    return {"bytes":len(data),"sha256":sha256(data).hexdigest()}


def inventory(files):
    require(type(files) is dict and all(type(n) is str for n in files),"named immutable source mapping required")
    return {n:pin(d) for n,d in sorted(files.items())}


def equal(left,right):
    return json.dumps(left,sort_keys=True)==json.dumps(right,sort_keys=True)


def _source(module,sources,logical=None):
    require(type(module) is ModuleType,"actual executing module object required")
    require(type(sources) is dict and set(sources)=={"current","frozen"} and
            type(sources["current"]) is bytes and sources["current"]==sources["frozen"],
            "current/frozen executing authority source differs")
    path=Path(module.__file__)
    if logical is not None:
        require(path.parts[-len(PurePosixPath(logical).parts):]==PurePosixPath(logical).parts,
                "authority module occupies another source role")
    code=compile(sources["frozen"],str(path),"exec",dont_inherit=True)
    require(getattr(module,"_EXECUTING_CODE",None)==code and sys.modules.get(module.__name__) is module,
            "authority must be its actual frozen executing module")
    for item in code.co_consts:
        if not isinstance(item,CodeType) or item.co_name.startswith("<"):continue
        if item.co_flags&2:
            actual=getattr(module,item.co_name,None)
            require(type(actual) is FunctionType and actual.__code__==item and actual.__globals__ is module.__dict__,
                    "executing authority function binding differs")
        elif item.co_name in ("SearchAdmission","NoTidAdmission","SquareAdmission"):
            actual=getattr(module,item.co_name,None)
            require(type(actual) is type and actual.__module__==module.__name__ and
                    actual.__name__==item.co_name and actual.__qualname__==item.co_name and
                    actual.__bases__==(object,) and "__getattribute__" not in actual.__dict__ and
                    "__getattr__" not in actual.__dict__ and not set(FIELDS).intersection(actual.__dict__) and
                    type(actual.__dict__.get("__dict__")) is GetSetDescriptorType and
                    actual.__dict__["__dict__"].__objclass__ is actual,
                    "executing typed authority class differs")
            for method in item.co_consts:
                if isinstance(method,CodeType) and method.co_flags&2 and not method.co_name.startswith("<"):
                    function=actual.__dict__.get(method.co_name)
                    if isinstance(function,property):function=function.fget
                    require(type(function) is FunctionType and function.__code__==method and function.__globals__ is module.__dict__,
                            "executing typed authority method binding differs")
    return sources["frozen"]


def _instance_fields(token,klass,names=FIELDS):
    require(type(token) is klass,"exact typed authority instance required")
    fields=object.__getattribute__(token,"__dict__")
    require(type(fields) is dict and set(fields)==set(names),"unminted or method-shadowed authority instance rejected")
    return fields


def validate_profile(profile):
    require(type(profile) is dict,"explicit Square profile mapping required")
    expected={"workers":4,"control_threads":1,"os_threads":5,"tt_bits":23,"tt_entry_bytes":16,
              "tt_entries":1<<23,"tt_mask":(1<<23)-1,"tt_bytes":128<<20,"tt_cap_bytes":128<<20}
    require(profile.get("id")=="test-p4" and profile.get("purpose")=="test" and
            all(type(profile.get(k)) is int and profile[k]==v for k,v in expected.items()) and
            all(profile.get(k) is True for k in ("parallel_init","init_partition_requires_page_aligned_base","initialization_in_startup")) and
            profile.get("event_allocation_confirmed") is None,"Square admission requires typed W4/TT23/128MiB P4 geometry")
    return deepcopy(profile)


def validate_parent(parent,module,source):
    raw=_source(module,source,PARENT_ADMISSION)
    require(pin(raw)==PARENT_SOURCE,"unchanged no-TID parent authority source required")
    require(getattr(module,"KIND",None)==PARENT_KIND and type(parent) is module.NoTidAdmission,
            "real authenticated fresh NoTidAdmission parent required")
    fields=_instance_fields(parent,module.NoTidAdmission)
    require(fields["_valid"] is module._TOKEN and type(fields["_record"]) is str and
            type(fields["_parent_module"]) is ModuleType,
            "foreign no-TID nonce or untyped parent storage rejected before reading evidence")
    # Authenticate the stored old Search class before no-TID delegates to it.
    # Neither a JSON claim nor a replaced parent method may run first.
    saved=json.loads(fields["_record"]);ancestor=fields["_parent_module"]
    require(type(ancestor.__file__) is str,"actual old Search authority source path required")
    path=Path(ancestor.__file__)
    require(path.parts[-4:]==("engines","experiments","tiny-d-submission","search_admission.py") and
            path.is_file() and path.stat().st_size<=1<<20,"bounded parent source role required")
    ancestor_raw=path.read_bytes().replace(b"\r\n",b"\n")
    require(pin(ancestor_raw)==saved.get("parent_admission_source"),"stored Search source pin differs")
    _source(ancestor,{"current":ancestor_raw,"frozen":ancestor_raw},D+"search_admission.py")
    require(module.NoTidAdmission.assert_valid(parent) is parent,"fresh no-TID typed authority failed")
    record=module.NoTidAdmission.to_record(parent)
    require(record.get("kind")==PARENT_KIND and record.get("selector")=="no-tid" and record.get("nonreturning") is False and
            record.get("options")==OPTIONS and record.get("admission_source")==pin(raw) and
            record.get("identity")==PARENT_IDENTITY=={"linked":pin(parent.linked),"stripped":pin(parent.native)} and
            pin(module.NoTidAdmission.package_bytes(parent,"packed-xz-bcj"))==PARENT_PACKED and
            record.get("ownership_policy")==POLICY and record.get("last_search_output_required") is False,
            "authenticated no-TID source/identity/ownership differs")
    validate_profile(record.get("profile"))
    require(all(record.get(k) is True for k in ("source_admitted","native_admitted","actual_search_semantics_admitted",
                "new_three_argument_startup_admitted")),"fresh parent semantics/startup authority required")
    return record


def input_names(record):
    require(type(record) is dict and pin((json.dumps(record,indent=2)+"\n").encode())==RECEIPT,
            "exact reviewed Square receipt required before input discovery")
    names=record.get("captured_sources")
    require(type(names) is dict and len(names)==11 and {CHANGE,PROBE,COST_TEST}<=set(names) and
            all(type(n) is str and n.startswith("engines/") and ".." not in PurePosixPath(n).parts for n in names),
            "exact bounded Square source/tool closure required")
    return tuple(sorted(names))


def evidence_names(record):
    input_names(record)
    require([c.get("name") for c in record.get("cases",[])]==["control",SELECTOR],"exact two Square cases required")
    names=set()
    for row in record["commands"]:
        for stream in ("stdout","stderr"):names.add(Path(row[stream]["path"]).name)
        if row["kind"].endswith("-single-preprocess"):
            names.add(Path(row["stdout"]["path"]).with_suffix(".stdin").name)
    for case in record["cases"]:
        label=case["name"]
        names.update(label+"/generated-readable/"+n for n in READABLE)
        names.update(label+"/shipping-inputs/"+n for n in SHIPPING)
        for sub in ("gate-baseline","gate-typedefs","gate-batch-alpha","native-0","native-1"):
            names.update(label+"/"+sub+"/"+n for n in (*SHIPPING,"linked","native"))
        names.update(label+"/"+route+"-"+str(i) for route in ("source-jit","source-jit-compressed","packed-xz-bcj") for i in range(2))
    return tuple(sorted(names))


def used_paths(*values):
    result=set()
    def walk(value):
        if type(value) is dict:
            for item in value.values():walk(item)
        elif type(value) in (list,tuple):
            for item in value:walk(item)
        elif type(value) is str:
            path=value[len("-Wl,-T,"):] if value.startswith("-Wl,-T,") else value
            if path.startswith("/"):result.add(str(PurePosixPath(path)))
    for value in values:walk(value)
    return result


@dataclass(frozen=True,init=False)
class SquareAdmission:
    """Fresh opaque authority; JSON and old native classes cannot mint it."""
    def __init__(self,nonce,record,parent,parent_module,readable,shipping,images,native,linked):
        require(nonce is _TOKEN,"SquareAdmission requires fresh explicit square-successor admission")
        for name,value in (("_valid",_TOKEN),("_record",json.dumps(record,sort_keys=True)),
            ("_parent",parent),("_parent_module",parent_module),("_readable",tuple(sorted(readable.items()))),
            ("_shipping",tuple(sorted(shipping.items()))),("_images",tuple(sorted(images.items()))),
            ("_native",native),("_linked",linked)):
            object.__setattr__(self,name,value)

    def assert_valid(self):
        fields=_instance_fields(self,SquareAdmission)
        require(fields["_valid"] is _TOKEN and type(fields["_parent_module"]) is ModuleType,
                "foreign constructor nonce or parent module rejected")
        path=Path(self._parent_module.__file__)
        require(path.is_file() and path.stat().st_size<=1<<20,"bounded no-TID parent authority source required")
        parent_raw=path.read_bytes().replace(b"\r\n",b"\n")
        parent_record=validate_parent(self._parent,self._parent_module,{"current":parent_raw,"frozen":parent_raw})
        record=SquareAdmission.to_record(self);validate_profile(record.get("profile"))
        require(record.get("kind")==KIND and record.get("selector")==SELECTOR and record.get("nonreturning") is False and
                record.get("options")==OPTIONS and record.get("identity")==IDENTITY=={"linked":pin(self._linked),"stripped":pin(self._native)} and
                pin(SquareAdmission.package_bytes(self,"packed-xz-bcj"))==PACKED,"new Square native/package authority differs")
        require(record.get("ownership_policy")==POLICY and record.get("last_search_output_required") is False and
                record.get("input_contract")==INPUT_CONTRACT and record.get("kernel_tid_handshake") is False and
                all(record.get(k) is True for k in ("source_admitted","native_admitted","package_generation_admitted",
                    "actual_search_semantics_admitted","new_three_argument_startup_admitted")) and
                all(record.get(k) is False for k in ("fresh_full_artifact_runtime","rules_qualified","physical_placement_qualified",
                    "size_qualified","strength_qualified","event_target_confirmed","selected")) and
                equal(record.get("parent_admission"),parent_record),
                "typed Square parent/policy/readiness differs")
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


def _packages(shipping,flags,native,declared,products,modules,*,label):
    routes=("source-jit","source-jit-compressed","packed-xz-bcj")
    require([(r.get("route"),r.get("repeat")) for r in declared]==[(r,i) for r in routes for i in range(2)],
            "exact three routes each twice required")
    rows,images=[],{}
    for route in routes:
        captured=[]
        for repeat in range(2):
            if route=="source-jit":whole,detail=modules["packaging"].package_source(shipping,flags,UNITS)
            elif route=="source-jit-compressed":whole,detail=modules["bootstrap"].package_source(shipping,flags,UNITS,modules["packaging"])
            else:whole,detail=modules["packaging"].package_native(native,"xz-bcj")
            stored=next(r for r in declared if r["route"]==route and r["repeat"]==repeat)
            require(pin(whole)==stored.get("whole") and equal(detail,stored.get("detail")) and
                    whole==products[label+"/"+route+"-"+str(repeat)] and
                    type(stored.get("bootstrap_plus_payload_bytes")) is int and stored["bootstrap_plus_payload_bytes"]==len(whole),
                    "entire Square package/header/payload count differs")
            boundary=detail.get("header_bytes")
            require(type(boundary) is int and 0<boundary<len(whole),"typed whole package boundary required")
            decoder=lzma.LZMADecompressor();decoded=decoder.decompress(whole[boundary:],max_length=4<<20)
            require(decoder.eof and not decoder.unused_data,"strict package EOF/trailing data differs")
            if route=="packed-xz-bcj":require(decoded==native,"complete kernel ELF inverse differs")
            else:
                bundle=json.loads(decoded) if route=="source-jit" else ast.literal_eval(ast.parse(decoded).body[1].value)
                require(bundle=={"files":{n:d.decode() for n,d in sorted(shipping.items())},"flags":list(flags),"units":list(UNITS)},
                        "whole source/flags/units inverse differs")
            inverse={"header":pin(whole[:boundary]),"payload":pin(whole[boundary:]),"decoded":pin(decoded),
                     "strict_EOF":True,"trailing_bytes":0,"complete_input_inverse":True}
            require(equal(inverse,stored.get("inverse")),"archived exact whole inverse observation differs")
            captured.append((whole,detail))
        require(captured[0]==captured[1],"two fresh entire packages differ")
        images[route]=captured[0][0]
        rows.append({"route":route,"whole":pin(images[route]),"detail":deepcopy(captured[0][1]),"reproduced":True,
                     "boundaries":{"header":pin(images[route][:boundary]),"payload":pin(images[route][boundary:])}})
    return rows,images


def _stored(record,products,parent,modules,old,root):
    input_names(record)
    require(record.get("kind")==EXPERIMENT_KIND and record.get("complete") is True and record.get("frozen_execution") is True and
            record.get("original_qualification")==ORIGINAL_QUALIFICATION and record.get("original_startup_cost")==ORIGINAL_STARTUP and
            record.get("no_proper_alpha_combination") is True and
            record.get("host_cleanup")=={"unsettled_commands":0,"errors":[]},"reviewed bounded Square generation receipt required")
    require(all(record.get(k) is False for k in ("engine_executed","target_TT_allocated","capability_deserialized","full_typed_admission",
                "runtime_qualified","rules_qualified","size_qualified","strength_qualified","physical_placement_qualified",
                "event_target_confirmed","selected","production_adopted","old_maps_changed")),"cost is not full runtime authority")
    kinds=["compiler-version"]
    for label in ("control",SELECTOR):
        kinds += [label+"-single-preprocess",label+"-entry-preprocess"]
        kinds += [label+"-source-reduction-gate-"+trial for trial in ("baseline","typedefs","batch-alpha")]
        kinds += [label+"-native-repeat-"+str(i) for i in range(2)]
    require([r.get("kind") for r in record.get("commands",[])]==kinds and set(products)==set(evidence_names(record)),
            "exact archived command/product scope required")
    rows={r["kind"]:r for r in record["commands"]}
    for i,row in enumerate(record["commands"],1):old.settled(row);old._streams(row,products,root,i)
    flags=parent.to_record()["flags"]
    require(record.get("compiler_flags")==flags and record.get("units")==list(UNITS) and
            record.get("resource")=={"profile":"test-p4","workers":4,"tt_bits":23,"tt_entry_bytes":16,"tt_bytes":128<<20} and
            record.get("input_sources")==inventory(parent.readable),"archived P4 source/compiler/resource differs")
    change=modules["square_change"];legacy=parent.identifier_composition["legacy"];results={}
    for case in record["cases"]:
        label=case["name"]
        readable,proof=(parent.readable,None) if label=="control" else change.transform(parent.readable)
        require(inventory(readable)==case["readable"] and equal(proof,case.get("source_stage")) and
                all(products[label+"/generated-readable/"+n]==d for n,d in readable.items()),"archived six-source projection differs")
        if proof is not None:
            require(change.restore(readable,json.loads(json.dumps(proof)))==parent.readable and equal(proof,record["source_stage"]),
                    "complete two-opening inverse differs")
        rawdir=root+"/"+label+"/generated-readable"
        cpprow=rows[label+"-single-preprocess"];entryrow=rows[label+"-entry-preprocess"]
        require(cpprow["command"]==["cc","-E","-P",*flags,"-I",rawdir,"-x","c","-"] and
                entryrow["command"]==["cc","-E","-P","-x","assembler-with-cpp",rawdir+"/start.S"] and
                cpprow["cwd"]==entryrow["cwd"]==rawdir and equal(case["preprocess"]["commands"],[cpprow,entryrow]),
                "archived exact preprocessing argv differs")
        driver=case["preprocess"]["driver"];drivername=Path(cpprow["stdout"]["path"]).with_suffix(".stdin").name
        require(driver=={"path":root+"/"+drivername,**pin(DRIVER)} and products[drivername]==DRIVER,"actual saved CPP driver differs")
        cpp=products[Path(cpprow["stdout"]["path"]).name];entry=products[Path(entryrow["stdout"]["path"]).name]
        emitted={"main.c":modules["minifier"].compact_source(cpp,"c"),"start.S":entry,"image.ld":readable["image.ld"]}
        require(case["preprocess"]["C"]==pin(cpp) and case["preprocess"]["assembly"]==pin(entry) and
                case["preprocess"]["minified"]==inventory(emitted),"archived CPP/minifier output differs")
        require(not set(legacy.values()).intersection(modules["lexical"]._ANY_WORD.findall(emitted["main.c"].decode())),"legacy identifier capture")
        mapped={"main.c":emitted["main.c"]}
        for before,after in legacy.items():mapped=modules["lexical"]._replace(mapped,before,after)
        restored=dict(mapped)
        for before,after in reversed(tuple(legacy.items())):restored=modules["lexical"]._replace(restored,after,before)
        require(restored=={"main.c":emitted["main.c"]},"full legacy token inverse differs")
        emitted.update(mapped)
        require(case["legacy"]=={"mapping":legacy,"full_inverse":True,"emitted":inventory(emitted)},"archived legacy source differs")
        def compile_row(files,row,sub):
            directory=root+"/"+label+"/"+sub
            command=row["command"]
            require(row["input"]==inventory(files) and row["input_paths"]=={n:directory+"/"+n for n in files} and
                    row["linked_path"]==directory+"/linked" and row["native_path"]==directory+"/native" and
                    command["cwd"]==directory and command["command"]==["cc",*flags,*[directory+"/"+n for n in UNITS],
                        "-Wl,-T,"+directory+"/image.ld","-o",directory+"/linked"] and
                    all(products[label+"/"+sub+"/"+n]==d for n,d in files.items()),"archived actual compile source/argv differs")
            linked=products[label+"/"+sub+"/linked"];native=products[label+"/"+sub+"/native"]
            require(row["linked"]==pin(linked) and row["native"]==pin(native) and modules["packer"].strip_native(linked)==native,
                    "archived full linked/native inverse differs")
            require(equal(row["linked_geometry"],modules["builder"].kernel_geometry(modules["packer"],linked,4)) and
                    equal(row["native_geometry"],modules["builder"].kernel_geometry(modules["packer"],native,4)),"complete kernel geometry differs")
            return linked,native
        gate_index=0
        def digest(c_files,trial):
            nonlocal gate_index
            row=case["reducer_native"][gate_index];gate_index+=1
            require(equal(row["command"],rows[label+"-source-reduction-gate-"+trial]),"archived reduction command lineage differs")
            linked,_=compile_row({**emitted,**c_files},row,"gate-"+trial)
            return pin(linked)["sha256"]
        reduced,reduction=modules["reducer"].reduce_sources({"main.c":emitted["main.c"]},digest,modules["lexical"],
            reserve=modules["lexical"]._ANY_WORD.findall((entry+emitted["image.ld"]).decode()))
        require(gate_index==3 and len(case["reducer_native"])==3 and equal(reduction,case["reduction"]),"archived full reducer replay differs")
        emitted.update(reduced)
        require(inventory(emitted)==case["shipping"] and all(products[label+"/shipping-inputs/"+n]==d for n,d in emitted.items()),
                "archived actual final shipping input differs")
        captured=[]
        require(len(case["native"])==2,"exact two archived native captures required")
        for i,row in enumerate(case["native"]):
            require(equal(row["command"],rows[label+"-native-repeat-"+str(i)]),"native original lineage differs")
            captured.append(compile_row(emitted,row,"native-"+str(i)))
        require(captured[0]==captured[1],"two archived native outputs differ")
        packages,images=_packages(emitted,flags,captured[0][1],case["packages"],products,modules,label=label)
        results[label]={"readable":readable,"proof":proof,"shipping":emitted,"reduction":reduction,
            "linked":captured[0][0],"native":captured[0][1],"packages":packages,"images":images}
    control=results["control"]
    require(control["readable"]==parent.readable and control["shipping"]==parent.shipping and control["linked"]==parent.linked and
            control["native"]==parent.native and control["images"]["packed-xz-bcj"]==parent.package_bytes("packed-xz-bcj"),
            "fresh actual NoTid parent differs from cost control")
    require({"linked":pin(results[SELECTOR]["linked"]),"stripped":pin(results[SELECTOR]["native"])}==IDENTITY and
            pin(results[SELECTOR]["images"]["packed-xz-bcj"])==PACKED,"new exact Square identity differs")
    return results[SELECTOR]


def _semantic(readable,proof,parent,modules,callback,old,seen):
    projection={"kind":KIND+".semantic-source-projection","output":inventory(readable),"options":list(OPTIONS),
                "square_transform":deepcopy(proof)}
    generated,driver,expected=modules["probe"].render(readable,modules["source"],modules["storage_checker"],
        reference_board=parent.readable["board.c"],variant_proof=projection,prefix=True,dense=False,
        union_order=False,previous_index=True,constant_start=False,unsigned_history=True)
    result=callback(dict(readable),label=SELECTOR,options=tuple(OPTIONS),valid_readable=parent.readable,structural_proof=projection)
    require(type(result) is dict and result.get("kind")=="D-search-semantic-v1" and result.get("label")==SELECTOR and
            result.get("options")==OPTIONS and result.get("input_pins")==inventory(readable) and
            result.get("instrumented")==generated and result.get("driver")==driver and equal(result.get("proof"),expected),
            "fresh actual Square search semantics consumed another source")
    require([r.get("mode") for r in result.get("modes",[])]==["plain","ubsan"],"fresh actual plain/UBSan semantics required")
    commands=[];baseline=None
    for mode,row in zip(("plain","ubsan"),result["modes"]):
        directory=old.absolute(row.get("directory"));paths=row.get("source_paths",{});inputs={**generated,"driver.c":driver}
        binary=old.absolute(row.get("binary_path"));compiled=row.get("compile",{});executed=row.get("execute",{})
        require(paths=={n:directory+"/"+n for n in inputs} and compiled.get("cwd")==executed.get("cwd")==directory,
                "fresh semantic source/binary ownership differs")
        old._fresh_paths(compiled,[directory,*paths.values(),binary],seen);old._fresh_paths(executed,[],seen)
        flags=modules["probe"].compiler_flags(prefix=True,dense=False,previous_index=True,unsigned_history=True,mode=mode)
        require(compiled.get("command")==["cc",*flags,paths["driver.c"],"-o",binary] and executed.get("command")==[binary],
                "fresh actual semantic argv differs")
        output=row.get("output");normalized,summary=modules["probe"].verify_output(output)
        require(pin(output)=={k:executed["stdout"][k] for k in ("bytes","sha256")} and type(row.get("binary")) is bytes and
                row["binary"] and pin(normalized)==parent.to_record()["semantic_observations"]["observations"],
                "fresh Square order/prior/learner/PVS observations differ from fresh parent")
        if baseline is None:baseline=normalized
        require(normalized==baseline,"plain/UBSan actual Square semantics differ")
        commands.append({"mode":mode,"input_pins":inventory(inputs),"driver":pin(driver),"binary":pin(row["binary"]),
            "output":pin(output),"normalized":pin(normalized),"summary":summary,"commands":[deepcopy(compiled),deepcopy(executed)]})
    return {"source_projection":projection,"observations":pin(baseline),"modes":commands}


def validate_startup(result,readable,bridge,old,seen):
    generated,expected=bridge.render_startup_fixture(dict(readable))
    require(type(result) is dict and result.get("kind")=="D-square-successor-three-argument-startup-fixture-v1" and
            result.get("label")=="square-successor-startup-abi" and result.get("input_pins")==inventory(readable) and
            result.get("generated")==generated and equal(result.get("proof"),expected),
            "new Square actual three-argument startup source/projection differs")
    require(type(result.get("receipt_raw")) is bytes,"actual startup child receipt bytes required")
    child=json.loads(result["receipt_raw"])
    require(type(child) is dict and type(child.get("returncode")) is int and child["returncode"]==0 and
            all(type(child.get(k)) is int and child[k]>0 for k in ("pid","pgid","owner_pgid")) and
            type(child.get("held_window_seconds")) in (int,float) and math.isfinite(child["held_window_seconds"]) and
            child["held_window_seconds"]>=.05,"typed finite actual startup child/status/held observation required")
    observation=bridge.validate_startup_observation(result,generated,expected,old=old,seen=seen)
    component=observation["component_observation"]
    require(component.get("spawn_argument_count")==3 and component.get("worker_count")==4 and
            component.get("TT_bytes")==65536 and observation.get("parent_carrier_used") is False,
            "new square mechanism must consume actual three-argument source without old carrier")
    return {**observation,"compile":deepcopy(component["compile"]),"execute":deepcopy(component["execute"])}


def admit_square_successor(parent,record,frozen_inputs,products,modules,*,current_inputs,admission_source,
                          parent_admission_module,parent_admission_source,bridge_source,evidence_root,
                          preprocess,compile_identity,semantic_callback,startup_callback):
    """Fresh source/native/package authority; never restore JSON capabilities."""
    require(all(callable(fn) for fn in (preprocess,compile_identity,semantic_callback,startup_callback)),
            "fresh CPP/native/semantic/new-startup callbacks are mandatory")
    parent_record=validate_parent(parent,parent_admission_module,parent_admission_source)
    own=_source(sys.modules[__name__],admission_source,SELF)
    bridge=modules["square_runtime"];bridge_raw=_source(bridge,bridge_source,BRIDGE)
    old=object.__getattribute__(parent,"_parent_module")
    modules=old._modules(modules);change=modules["square_change"]
    require(set(frozen_inputs)==set(parent.input_pins)|set(input_names(record)) and
            inventory({n:frozen_inputs[n] for n in parent.input_pins})==parent.input_pins and
            inventory({n:frozen_inputs[n] for n in input_names(record)})==record["captured_sources"],
            "exact parent plus Square captured source closure required")
    engine_names={n for n in frozen_inputs if n.startswith("engines/")}
    require(set(current_inputs)==engine_names and current_inputs=={n:frozen_inputs[n] for n in engine_names},
            "current/frozen complete Square producer/helper closure differs")
    require(frozen_inputs[PARENT_ADMISSION]==parent_admission_source["frozen"],"actual parent authority source absent from closure")
    old._module_inputs(modules,{n:frozen_inputs[n] for n in parent.input_pins})
    path=Path(change.__file__)
    require(type(change) is ModuleType and sys.modules.get(change.__name__) is change and
            path.parts[-4:]==("engines","experiments","tiny-d-submission","d_square_successor.py") and
            path.read_bytes().replace(b"\r\n",b"\n")==frozen_inputs[CHANGE] and
            change.INPUTS==inventory(parent.readable),"actual executing exact Square helper/input differs")
    old._function_inputs(change,frozen_inputs[CHANGE],path)
    for item in compile(frozen_inputs[CHANGE],str(path),"exec",dont_inherit=True).co_consts:
        if isinstance(item,CodeType) and item.co_flags&2 and not item.co_name.startswith("<"):
            require(getattr(change,item.co_name).__globals__ is change.__dict__,"Square helper function globals differ")
    root=old.absolute(evidence_root);stored=_stored(record,products,parent,modules,old,root)
    readable,proof=change.transform(parent.readable)
    require(readable==stored["readable"] and equal(proof,stored["proof"]) and
            change.restore(readable,json.loads(json.dumps(proof)))==parent.readable and
            all(readable[n]==parent.readable[n] for n in READABLE if n!="board.c"),
            "two-opening complete source/inverse/protected engine bodies differ")
    flags=parent_record["flags"]
    seen=used_paths(parent_record,record,[root+"/"+name for name in products]);reserved=sorted(seen);fresh=[]
    outputs,entry=old.fresh_preprocess(preprocess(dict(readable),list(flags),list(old.MEMBERS),"square-successor"),
        readable,flags,"square-successor",seen)
    fresh.append(entry)
    emitted={"main.c":modules["minifier"].compact_source(outputs["main.c"],"c"),"start.S":outputs["start.S"],"image.ld":readable["image.ld"]}
    legacy=parent.identifier_composition["legacy"]
    require(not set(legacy.values()).intersection(modules["lexical"]._ANY_WORD.findall(emitted["main.c"].decode())),"fresh legacy capture")
    mapped={"main.c":emitted["main.c"]}
    for before,after in legacy.items():mapped=modules["lexical"]._replace(mapped,before,after)
    emitted.update(mapped)
    def digest(c_files,trial):
        files={**emitted,**c_files};label="square-successor/reduction/"+trial
        linked,native,entry=old.fresh_compile(compile_identity(files,list(flags),list(UNITS),label),files,flags,UNITS,label,modules,seen)
        fresh.append(entry);return pin(linked)["sha256"]
    reduced,reduction=modules["reducer"].reduce_sources({"main.c":emitted["main.c"]},digest,modules["lexical"],
        reserve=modules["lexical"]._ANY_WORD.findall((emitted["start.S"]+emitted["image.ld"]).decode()))
    emitted.update(reduced)
    require(equal(reduction,stored["reduction"]) and emitted==stored["shipping"],"fresh Square CPP/reducer/shipping differs")
    captures=[]
    for i in range(2):
        label="square-successor/native-repeat/"+str(i)
        linked,native,entry=old.fresh_compile(compile_identity(dict(emitted),list(flags),list(UNITS),label),emitted,flags,UNITS,label,modules,seen)
        require(linked==stored["linked"] and native==stored["native"] and
                {"linked":pin(linked),"stripped":pin(native)}==IDENTITY,"fresh new Square entire native capture differs")
        fresh.append(entry);captures.append((linked,native))
    require(captures[0]==captures[1],"two fresh entire new Square images differ")
    declared=next(c["packages"] for c in record["cases"] if c["name"]==SELECTOR)
    packages,images=_packages(emitted,flags,captures[0][1],declared,products,modules,label=SELECTOR)
    require(pin(images["packed-xz-bcj"])==PACKED,"fresh entire 5233-byte counted package differs")
    semantics=_semantic(readable,proof,parent,modules,semantic_callback,old,seen)
    fresh.extend({"kind":KIND+".fresh-semantic",**deepcopy(mode)} for mode in semantics["modes"])
    startup=validate_startup(startup_callback(dict(readable),label="square-successor-startup-abi"),readable,bridge,old,seen)
    fresh.append({"kind":KIND+".fresh-startup",**deepcopy(startup),"input_pins":deepcopy(startup["source"]),
                  "commands":[deepcopy(startup["compile"]),deepcopy(startup["execute"])]})
    input_pins=inventory(frozen_inputs)
    input_pins.update({SELF:pin(own),PARENT_ADMISSION:pin(parent_admission_source["frozen"]),BRIDGE:pin(bridge_raw)})
    record_out={"kind":KIND,"family":"D","selector":SELECTOR,"nonreturning":False,"options":list(OPTIONS),
        "profile":validate_profile(parent_record["profile"]),"flags":list(flags),"units":list(UNITS),"identity":deepcopy(IDENTITY),
        "packages":packages,"input_pins":input_pins,"admission_source":pin(own),"startup_fixture_authority":pin(bridge_raw),
        "parent_admission_source":pin(parent_admission_source["frozen"]),"parent_admission":deepcopy(parent_record),
        "parent_admission_record":pin((json.dumps(parent_record,sort_keys=True,indent=2)+"\n").encode()),
        "source_proof":proof,"original_experiment":deepcopy(RECEIPT),"identifier_composition":old._composition(legacy,reduction),
        "reserved_evidence_paths":reserved,
        "fresh_commands":[*deepcopy(parent_record["fresh_commands"]),*fresh],"semantic_observations":semantics,"startup_mechanism":startup,
        "ownership_policy":POLICY,"last_search_output_required":False,"input_contract":INPUT_CONTRACT,"kernel_tid_handshake":False,
        "callback_contract":"fixed work; returning callback SYS_exit fallback retained","source_admitted":True,"native_admitted":True,
        "package_generation_admitted":True,"actual_search_semantics_admitted":True,"new_three_argument_startup_admitted":True,
        "fresh_full_artifact_runtime":False,"rules_qualified":False,"physical_placement_qualified":False,"size_qualified":False,
        "strength_qualified":False,"event_target_confirmed":False,"selected":False,
        "scope":"two scalar 0x88 outer openings on fresh actual no-TID P4 class; full runtime still required"}
    return SquareAdmission(_TOKEN,record_out,parent,parent_admission_module,readable,emitted,images,captures[0][1],captures[0][0]).assert_valid()
