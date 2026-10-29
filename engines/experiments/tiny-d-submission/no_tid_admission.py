"""Fresh typed admission for the fixed no-TID D startup, never an old waiver.

An unchanged, authenticated SearchAdmission is the parent authority. This
module admits only the reviewed three-argument, returning-callback startup;
the optional never-returning tail is outside this class. Native and package
authority is obtained from fresh owned captures before a runtime carrier can
be minted. This module never launches commands or reads ambient credentials.
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
from types import CodeType, FunctionType, ModuleType

KIND = "rove4k.D-no-TID-source.v1"
PARENT_KIND = "rove4k.D-search-source.v1"
EXPERIMENT_KIND = "D-no-TID-startup-three-case-source-cost-v1"
SELECTOR = "no-tid"
OPTIONS = ["previous-piece", "unsigned-history"]
D = "engines/experiments/tiny-d-submission/"
SELF = D+"no_tid_admission.py"
PARENT_ADMISSION = D+"search_admission.py"
BRIDGE = D+"no_tid_runtime.py"
CHANGE = D+"no_tid_startup.py"
COST_DRIVER = D+"test_no_tid_startup.py"
READER = "engines/scripts/production_input.py"
COMPOSER = "engines/scripts/source_composition.py"
READABLE = ("tiny.h","board.c","search.c","runtime.c","start.S","image.ld")
SHIPPING = ("main.c","start.S","image.ld")
UNITS = ("main.c","start.S")
RECEIPT = {"bytes":252355,"sha256":"0a09371a9a5eb0aac8644d18b24b2172742796f0789432d6d4771c86b2662241"}
IDENTITY = {
    "linked":{"bytes":7456,"sha256":"16deff54c4059f236c845191674f9b36c26139c032d23e66b53992fd11c3ebf3"},
    "stripped":{"bytes":7104,"sha256":"f0168f752eaa15bf011cbd75964ebe10bc39ca88ddd16eeed66c73e2cf59ed7b"},
}
PACKED = {"bytes":5245,"sha256":"4dbe1bfbceb1c290ee45801e74fe44d7ef2148215b57d51141e1965d5e5db9fa"}
PARENT_IDENTITY = {
    "linked":{"bytes":7488,"sha256":"87c9f93a87a5d53aaa094a0019952cafbbf8da2ff83c382dee1f1c927d91f00f"},
    "stripped":{"bytes":7136,"sha256":"448eeb52aa59e7eaaf7830940be18f5618129d55732d8855e0c8bcb13368f565"},
}
PARENT_PACKED = {"bytes":5261,"sha256":"01b36b58e190694f36ee052f0f299f96618cc72f430ed178b12fe37af58448dd"}
POLICY = "TCEC-minimum-immediate-process-exit"
INPUT_CONTRACT = "TCEC-valid-non-NUL-lines-at-most-32767-bytes"
_TOKEN = object()
_EXECUTING_CODE = sys._getframe().f_code


def require(value,message):
    if not value:raise ValueError(message)


def pin(data):
    require(type(data) is bytes,"actual immutable evidence bytes required")
    return {"bytes":len(data),"sha256":sha256(data).hexdigest()}


def inventory(files):
    require(isinstance(files,dict) and all(type(n) is str for n in files),"named immutable input mapping required")
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
    require(getattr(module,"_EXECUTING_CODE",None)==code and
            sys.modules.get(module.__name__) is module,"authority must be its actual frozen executing module")
    # Also reject a module whose exported function/class bindings were replaced
    # after its frame was captured. This is not a substitute for input bytes.
    for item in code.co_consts:
        if not isinstance(item,CodeType) or item.co_name.startswith("<"):continue
        if item.co_flags&2:
            actual=getattr(module,item.co_name,None)
            require(type(actual) is FunctionType and actual.__code__==item and actual.__globals__ is module.__dict__,
                    "executing authority function binding differs")
        elif item.co_name in ("SearchAdmission","NoTidAdmission"):
            actual=getattr(module,item.co_name,None)
            require(type(actual) is type and actual.__module__==module.__name__ and
                    actual.__name__==item.co_name and actual.__qualname__==item.co_name and
                    actual.__bases__==(object,) and "__getattribute__" not in actual.__dict__ and
                    "__getattr__" not in actual.__dict__,"executing typed authority class differs")
            for method in item.co_consts:
                if isinstance(method,CodeType) and method.co_flags&2 and not method.co_name.startswith("<"):
                    function=actual.__dict__.get(method.co_name)
                    if isinstance(function,property):function=function.fget
                    require(type(function) is FunctionType and function.__code__==method and function.__globals__ is module.__dict__,
                            "executing typed authority method binding differs")
    return sources["frozen"]


def _instance_fields(token,klass,names):
    require(type(token) is klass,"exact typed authority instance required")
    fields=object.__getattribute__(token,"__dict__")
    require(type(fields) is dict and set(fields)==set(names),"unminted or method-shadowed authority instance rejected")
    return fields


def validate_profile(profile):
    require(type(profile) is dict,"explicit no-TID profile mapping required")
    expected={"workers":4,"control_threads":1,"os_threads":5,"tt_bits":23,"tt_entry_bytes":16,
              "tt_entries":1<<23,"tt_mask":(1<<23)-1,"tt_bytes":128<<20,"tt_cap_bytes":128<<20}
    require(profile.get("id")=="test-p4" and profile.get("purpose")=="test" and
            all(type(profile.get(k)) is int and profile[k]==v for k,v in expected.items()) and
            all(profile.get(k) is True for k in ("parallel_init","init_partition_requires_page_aligned_base","initialization_in_startup")) and
            profile.get("event_allocation_confirmed") is None,
            "no-TID admission requires typed W4/TT23/128MiB P4 geometry")
    return deepcopy(profile)


def validate_parent(parent,module,source):
    raw=_source(module,source,PARENT_ADMISSION)
    require(getattr(module,"KIND",None)==PARENT_KIND and type(parent) is module.SearchAdmission,
            "real authenticated old SearchAdmission parent required")
    _instance_fields(parent,module.SearchAdmission,("_record","_readable","_shipping","_images","_native","_linked","_valid"))
    require(module.SearchAdmission.assert_valid(parent) is parent,"parent typed authority failed")
    record=module.SearchAdmission.to_record(parent)
    require(record.get("kind")==PARENT_KIND and record.get("selector")=="proved-win-combination" and
            record.get("options")==OPTIONS and record.get("admission_source")==pin(raw) and
            record.get("identity")==PARENT_IDENTITY=={"linked":pin(parent.linked),"stripped":pin(parent.native)} and
            pin(parent.package_bytes("packed-xz-bcj"))==PARENT_PACKED and
            record.get("ownership_policy")==POLICY and record.get("last_search_output_required") is False,
            "old authenticated parent source/identity/ownership differs")
    validate_profile(record.get("profile"))
    require(record.get("source_admitted") is True and record.get("native_admitted") is True and
            record.get("actual_search_semantics_admitted") is True,"fresh parent semantic authority required")
    return record


def input_names(record,producer):
    require(type(record) is dict and type(record.get("inputs")) is dict and type(record.get("tools")) is dict,
            "named startup input/tool closure required")
    base=set(producer)|{D+n+".py" for n in (
        "reduce","publication","process_owner","test_startup","test_process_owner",
        "compressed_bootstrap","syscall_arity","test_runtime_scaffold","valid_input",
        "search_compact","test_search_compact","probe_search_compact","check_storage","source_inputs")}|{"selection/build.json"}
    require(set(record["inputs"])==base and set(record["tools"])=={CHANGE,COST_DRIVER,READER} and
            COMPOSER in base and READER not in base,"exact recipe-derived no-TID closure required")
    return tuple(sorted(base|set(record["tools"])))


def evidence_names(record):
    names=set()
    for row in record["commands"]:
        for stream in ("stdout","stderr"):names.add(Path(row[stream]["path"]).name)
    for case in record["cases"]:
        label=case["name"]
        names.update(label+"/generated-readable/"+n for n in READABLE)
        names.update(label+"/shipping-inputs/"+n for n in SHIPPING)
        names.update(label+"/native-"+str(i)+"/"+n for i in range(2) for n in ("linked","native"))
        for i in range(3):
            names.update(label+"/gate-"+str(i)+"/"+n for n in (*SHIPPING,"linked"))
        names.update(label+"/"+route+"-"+str(i) for route in
            ("source-jit","source-jit-compressed","packed-xz-bcj") for i in range(2))
    return tuple(sorted(names))


def used_paths(*values):
    """Reserve all earlier source/output/pipe namespaces before fresh work."""
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
class NoTidAdmission:
    """Opaque fresh authority; a JSON record or old parent cannot mint this."""
    def __init__(self,nonce,record,parent,parent_module,readable,shipping,images,native,linked):
        require(nonce is _TOKEN,"NoTidAdmission requires fresh explicit no-TID admission")
        for name,value in (("_valid",_TOKEN),("_record",json.dumps(record,sort_keys=True)),
            ("_parent",parent),("_parent_module",parent_module),("_readable",tuple(sorted(readable.items()))),
            ("_shipping",tuple(sorted(shipping.items()))),("_images",tuple(sorted(images.items()))),
            ("_native",native),("_linked",linked)):
            object.__setattr__(self,name,value)

    def assert_valid(self):
        _instance_fields(self,NoTidAdmission,("_valid","_record","_parent","_parent_module","_readable","_shipping","_images","_native","_linked"))
        require(self._valid is _TOKEN and type(self._parent_module) is ModuleType,
                "foreign no-TID constructor nonce or parent module rejected")
        _instance_fields(self._parent,self._parent_module.SearchAdmission,("_record","_readable","_shipping","_images","_native","_linked","_valid"))
        require(type(self) is NoTidAdmission and self._valid is _TOKEN and
                type(self._parent) is self._parent_module.SearchAdmission and
                self._parent_module.SearchAdmission.assert_valid(self._parent) is self._parent,
                "exact authenticated no-TID token and fresh typed parent required")
        record=NoTidAdmission.to_record(self);validate_profile(record.get("profile"))
        require(record.get("kind")==KIND and record.get("selector")==SELECTOR and
                record.get("nonreturning") is False and record.get("options")==OPTIONS and
                record.get("identity")==IDENTITY=={"linked":pin(self._linked),"stripped":pin(self._native)} and
                pin(NoTidAdmission.package_bytes(self,"packed-xz-bcj"))==PACKED,
                "new no-TID source/native/package authority differs")
        require(record.get("ownership_policy")==POLICY and record.get("last_search_output_required") is False and
                record.get("input_contract")==INPUT_CONTRACT and record.get("kernel_tid_handshake") is False and
                all(record.get(k) is True for k in ("source_admitted","native_admitted","package_generation_admitted",
                    "actual_search_semantics_admitted","new_three_argument_startup_admitted")) and
                all(record.get(k) is False for k in ("fresh_full_artifact_runtime","rules_qualified",
                    "physical_placement_qualified","size_qualified","strength_qualified","event_target_confirmed","selected")) and
                equal(record.get("parent_admission"),self._parent_module.SearchAdmission.to_record(self._parent)),
                "new typed authority policy/parent/readiness differs")
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


def validate_startup(result,readable,bridge,old,seen):
    """Strict NEW three-argument mechanism result; no four-argument wrapper."""
    generated,expected=bridge.render_startup_fixture(dict(readable))
    require(type(result) is dict and result.get("kind")=="D-no-TID-three-argument-startup-fixture-v1" and
            result.get("label")=="no-tid-startup-abi" and result.get("input_pins")==inventory(readable) and
            result.get("generated")==generated and equal(result.get("proof"),expected),
            "new three-argument startup fixture input/projection differs")
    require(type(result.get("receipt_raw")) is bytes,"actual startup child receipt bytes required")
    child=json.loads(result["receipt_raw"])
    require(type(child) is dict and type(child.get("returncode")) is int and child["returncode"]==0 and
            all(type(child.get(k)) is int and child[k]>0 for k in ("pid","pgid","owner_pgid")) and
            type(child.get("held_window_seconds")) in (int,float) and
            math.isfinite(child["held_window_seconds"]) and child["held_window_seconds"]>=.05,
            "typed finite startup child identity/status/held observation required")
    return bridge.validate_startup_observation(result,generated,expected,old=old,seen=seen)


def _packages(shipping,flags,native,declared,products,modules,*,label):
    routes=("source-jit","source-jit-compressed","packed-xz-bcj")
    require([r.get("route") for r in declared]==list(routes),"exact three no-TID package routes required")
    rows,images=[],{}
    for route,stored in zip(routes,declared):
        if route=="source-jit":
            whole,detail=modules["packaging"].package_source(shipping,flags,UNITS)
            repeated,again=modules["packaging"].package_source(shipping,flags,UNITS)
        elif route=="source-jit-compressed":
            whole,detail=modules["bootstrap"].package_source(shipping,flags,UNITS,modules["packaging"])
            repeated,again=modules["bootstrap"].package_source(shipping,flags,UNITS,modules["packaging"])
        else:
            whole,detail=modules["packaging"].package_native(native,"xz-bcj")
            repeated,again=modules["packaging"].package_native(native,"xz-bcj")
        require(whole==repeated and equal(detail,again) and stored.get("reproduced") is True and
                stored.get("actual_whole_inverse") is True and pin(whole)==stored.get("whole") and
                equal(detail,stored.get("package")),"fresh no-TID whole/package repetition differs")
        for repeat in range(2):
            require(products[label+"/"+route+"-"+str(repeat)]==whole,"actual stored whole file differs")
        boundary=detail.get("header_bytes")
        require(type(boundary) is int and 0<boundary<len(whole),"typed complete package boundary required")
        decoder=lzma.LZMADecompressor();decoded=decoder.decompress(whole[boundary:],max_length=4<<20)
        require(decoder.eof and not decoder.unused_data,"strict complete package EOF/trailing-data contract differs")
        if route=="packed-xz-bcj":require(decoded==native,"whole native ELF inverse differs")
        else:
            bundle=json.loads(decoded) if route=="source-jit" else ast.literal_eval(ast.parse(decoded).body[1].value)
            require(bundle=={"files":{n:d.decode() for n,d in sorted(shipping.items())},
                    "flags":list(flags),"units":list(UNITS)},"whole source/flags/unit inverse differs")
        images[route]=whole
        rows.append({"route":route,"whole":pin(whole),"detail":deepcopy(detail),"reproduced":True,
                     "boundaries":{"header":pin(whole[:boundary]),"payload":pin(whole[boundary:])}})
    return rows,images


def _stored(record,products,parent,modules,old,root):
    """Authenticate the complete archived three-case evidence without rerunning tail."""
    require(pin((json.dumps(record,indent=2)+"\n").encode())==RECEIPT and record.get("kind")==EXPERIMENT_KIND and
            record.get("complete") is True and record.get("frozen_execution") is True and
            record.get("selected") is False and record.get("host_cleanup")=={"unsettled_commands":0,"errors":[]},
            "exact reviewed no-TID generation receipt required")
    require([c.get("name") for c in record.get("cases",[])]==["control","no-tid","no-tid-tail"] and
            [c.get("nonreturning") for c in record["cases"]]==[None,False,True],"exact bounded startup cases required")
    require(all(record.get(k) is False for k in ("full_typed_admission","rules_qualified","runtime_qualified",
        "engine_executed","raw_clone_fixture_executed","old_admission_changed","production_packaging_changed","SDK11_requested")),
        "generation receipt must not claim old/native/runtime approval")
    kinds=["compiler-version"]
    for label in ("control","no-tid","no-tid-tail"):
        kinds += [label+"-single-preprocess",label+"-entry-preprocess"]
        kinds += [label+"-source-reduction-gate-"+trial for trial in ("baseline","typedefs","batch-alpha")]
        kinds += [label+"-native-repeat-"+str(i) for i in range(2)]
    require([r.get("kind") for r in record.get("commands",[])]==kinds,"exact owned no-TID command scope required")
    require(set(products)==set(evidence_names(record)),"exact bounded no-TID products/streams required")
    rows={r["kind"]:r for r in record["commands"]}
    for i,row in enumerate(record["commands"],1):old.settled(row);old._streams(row,products,root,i)
    flags=parent.to_record()["flags"]
    require(record.get("compiler_flags")==flags and record.get("units")==list(UNITS) and
            equal(record.get("resource"),parent.to_record()["profile"]),"archived P4 compiler/resource recipe differs")
    change=modules["change"];results={}
    legacy=parent.identifier_composition["legacy"]
    for case in record["cases"]:
        label=case["name"]
        if label=="control":readable,proof=parent.readable,None
        else:readable,proof=change.transform(parent.readable,nonreturning=case["nonreturning"])
        require(inventory(readable)==case["source"] and equal(proof,case.get("source_stage")) and
                all(products[label+"/generated-readable/"+n]==d for n,d in readable.items()),
                "archived no-TID six-file source projection differs")
        if proof is not None:require(change.restore(readable,json.loads(json.dumps(proof)))==parent.readable,"source inverse differs")
        rawdir=root+"/"+label+"/generated-readable"
        cpprow=rows[label+"-single-preprocess"];entryrow=rows[label+"-entry-preprocess"]
        require(cpprow["command"]==["cc","-E","-P",*flags,"-I",rawdir,"-x","c","-"] and
                entryrow["command"]==["cc","-E","-P","-x","assembler-with-cpp",rawdir+"/start.S"] and
                cpprow["cwd"]==entryrow["cwd"]==rawdir,"archived preprocessing argv differs")
        cpp=products[Path(cpprow["stdout"]["path"]).name];entry=products[Path(entryrow["stdout"]["path"]).name]
        emitted={"main.c":modules["minifier"].compact_source(cpp,"c"),"start.S":entry,"image.ld":readable["image.ld"]}
        require(not set(legacy.values()).intersection(modules["lexical"]._ANY_WORD.findall(emitted["main.c"].decode())),"legacy capture")
        mapped={"main.c":emitted["main.c"]}
        for before,after in legacy.items():mapped=modules["lexical"]._replace(mapped,before,after)
        emitted.update(mapped);gate_index=0
        def digest(c_files,trial):
            nonlocal gate_index
            number=gate_index;gate_index+=1;combined={**emitted,**c_files}
            directory=root+"/"+label+"/gate-"+str(number);row=rows[label+"-source-reduction-gate-"+trial]
            require(row["cwd"]==directory and row["command"]==["cc",*flags,*[directory+"/"+n for n in UNITS],
                    "-Wl,-T,"+directory+"/image.ld","-o",directory+"/linked"] and
                    all(products[label+"/gate-"+str(number)+"/"+n]==d for n,d in combined.items()),
                    "archived reduction input/owned argv differs")
            return pin(products[label+"/gate-"+str(number)+"/linked"])["sha256"]
        reduced,reduction=modules["reducer"].reduce_sources({"main.c":emitted["main.c"]},digest,modules["lexical"],
            reserve=modules["lexical"]._ANY_WORD.findall((entry+emitted["image.ld"]).decode()))
        require(gate_index==3 and equal(reduction,case["reduction"]),"archived complete reduction replay differs")
        emitted.update(reduced)
        require(inventory(emitted)==case["shipping"] and all(products[label+"/shipping-inputs/"+n]==d for n,d in emitted.items()),
                "archived final shipping sources differ")
        images=[]
        for i in range(2):
            directory=root+"/"+label+"/native-"+str(i);row=rows[label+"-native-repeat-"+str(i)]
            src=root+"/"+label+"/shipping-inputs"
            require(row["cwd"]==directory and row["command"]==["cc",*flags,*[src+"/"+n for n in UNITS],
                    "-Wl,-T,"+src+"/image.ld","-o",directory+"/linked"] and equal(row,case["native"][i]["command"]),
                    "archived original native command differs")
            linked=products[label+"/native-"+str(i)+"/linked"];native=products[label+"/native-"+str(i)+"/native"]
            require(case["native"][i]["linked"]==pin(linked) and case["native"][i]["stripped"]==pin(native) and
                    modules["packer"].strip_native(linked)==native,"archived entire linked/native bytes differ")
            modules["builder"].kernel_geometry(modules["packer"],linked,4)
            modules["builder"].kernel_geometry(modules["packer"],native,4);images.append((linked,native))
        require(images[0]==images[1],"archived native repetitions differ")
        packages,package_images=_packages(emitted,flags,images[0][1],case["packages"],products,modules,label=label)
        results[label]={"readable":readable,"proof":proof,"shipping":emitted,"reduction":reduction,
            "linked":images[0][0],"native":images[0][1],"packages":packages,"images":package_images}
    require(results["control"]["readable"]==parent.readable and results["control"]["shipping"]==parent.shipping and
            results["control"]["linked"]==parent.linked and results["control"]["native"]==parent.native and
            results["control"]["images"]["packed-xz-bcj"]==parent.package_bytes("packed-xz-bcj"),
            "authenticated parent differs from no-TID experiment control")
    return results[SELECTOR]


def _semantic(readable,proof,parent,modules,callback,old,seen):
    projection={"kind":KIND+".semantic-source-projection","output":inventory(readable),"options":list(OPTIONS),
                "startup_transform":deepcopy(proof)}
    generated,driver,expected=modules["probe"].render(readable,modules["source"],modules["storage_checker"],
        reference_board=parent.readable["board.c"],variant_proof=projection,prefix=True,dense=False,
        union_order=False,previous_index=True,constant_start=False,unsigned_history=True)
    result=callback(dict(readable),label=SELECTOR,options=tuple(OPTIONS),valid_readable=parent.readable,structural_proof=projection)
    require(type(result) is dict and result.get("kind")=="D-search-semantic-v1" and result.get("label")==SELECTOR and
            result.get("options")==OPTIONS and result.get("input_pins")==inventory(readable) and
            result.get("instrumented")==generated and result.get("driver")==driver and equal(result.get("proof"),expected),
            "fresh actual no-TID search semantics consumed another source")
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
                row["binary"] and pin(normalized)==parent.to_record()["semantic_observations"],
                "fresh no-TID search/order/prior/learner observations differ from fresh parent")
        if baseline is None:baseline=normalized
        require(normalized==baseline,"plain/UBSan semantics differ")
        commands.append({"mode":mode,"input_pins":inventory(inputs),"driver":pin(driver),"binary":pin(row["binary"]),
            "output":pin(output),"normalized":pin(normalized),"summary":summary,"commands":[deepcopy(compiled),deepcopy(executed)]})
    return {"source_projection":projection,"observations":pin(baseline),"modes":commands}


def admit_no_tid(parent,record,frozen_inputs,products,modules,*,current_inputs,admission_source,
                 parent_admission_module,parent_admission_source,bridge_source,evidence_root,
                 preprocess,compile_identity,semantic_callback,startup_callback):
    """Fresh replay; archived success booleans never replace owned captures."""
    require(all(callable(fn) for fn in (preprocess,compile_identity,semantic_callback,startup_callback)),
            "fresh CPP/native/semantic/new-startup callbacks are mandatory")
    old=parent_admission_module;parent_record=validate_parent(parent,old,parent_admission_source)
    own=_source(sys.modules[__name__],admission_source,SELF)
    bridge=modules["no_tid_runtime"];bridge_raw=_source(bridge,bridge_source,BRIDGE)
    modules=old._modules(modules);change=modules["change"]
    producer=modules["source_inputs"].producer_names(json.loads(frozen_inputs[modules["source_inputs"].RECIPE]))
    require(set(frozen_inputs)==set(input_names(record,producer)) and inventory(frozen_inputs)=={**record["inputs"],**record["tools"]},
            "complete frozen no-TID source/tool bytes differ")
    names={n for n in frozen_inputs if n.startswith("engines/")}
    require(set(current_inputs)==names and current_inputs=={n:frozen_inputs[n] for n in names} and
            inventory(current_inputs)==record.get("source_current_after"),"current/frozen no-TID source closure differs")
    require(parent.input_pins==record["inputs"],"no-TID parent producer closure differs")
    old._module_inputs(modules,{n:frozen_inputs[n] for n in parent.input_pins})
    helper_path=Path(change.__file__)
    require(helper_path.parts[-4:]==("engines","experiments","tiny-d-submission","no_tid_startup.py") and
            helper_path.read_bytes().replace(b"\r\n",b"\n")==frozen_inputs[CHANGE] and
            change.INPUTS==inventory(parent.readable),"executing exact no-TID helper source/input differs")
    old._function_inputs(change,frozen_inputs[CHANGE],helper_path)
    root=old.absolute(evidence_root);stored=_stored(record,products,parent,modules,old,root)
    readable,proof=change.transform(parent.readable,nonreturning=False)
    require(readable==stored["readable"] and equal(proof,stored["proof"]) and change.restore(readable,proof)==parent.readable,
            "fresh no-TID source/inverse/complement differs")
    require(all(readable[n]==parent.readable[n] for n in ("tiny.h","board.c","search.c","image.ld")),
            "startup-only class changed engine logic")
    flags=parent_record["flags"]
    seen=used_paths(parent_record,record["commands"],[root+"/"+name for name in products])
    fresh=[]
    outputs,receipt=old.fresh_preprocess(preprocess(dict(readable),list(flags),list(old.MEMBERS),"no-tid"),readable,flags,"no-tid",seen)
    fresh.append(receipt)
    emitted={"main.c":modules["minifier"].compact_source(outputs["main.c"],"c"),"start.S":outputs["start.S"],"image.ld":readable["image.ld"]}
    legacy=parent.identifier_composition["legacy"]
    require(not set(legacy.values()).intersection(modules["lexical"]._ANY_WORD.findall(emitted["main.c"].decode())),"fresh legacy capture")
    mapped={"main.c":emitted["main.c"]}
    for before,after in legacy.items():mapped=modules["lexical"]._replace(mapped,before,after)
    emitted.update(mapped)
    def digest(c_files,trial):
        files={**emitted,**c_files};label="no-tid/reduction/"+trial
        linked,native,entry=old.fresh_compile(compile_identity(files,list(flags),list(UNITS),label),files,flags,UNITS,label,modules,seen)
        fresh.append(entry);return pin(linked)["sha256"]
    reduced,reduction=modules["reducer"].reduce_sources({"main.c":emitted["main.c"]},digest,modules["lexical"],
        reserve=modules["lexical"]._ANY_WORD.findall((emitted["start.S"]+emitted["image.ld"]).decode()))
    emitted.update(reduced)
    require(equal(reduction,stored["reduction"]) and emitted==stored["shipping"],"fresh no-TID CPP/full reducer/shipping differs")
    images=[]
    for i in range(2):
        label="no-tid/native-repeat/"+str(i)
        linked,native,entry=old.fresh_compile(compile_identity(dict(emitted),list(flags),list(UNITS),label),emitted,flags,UNITS,label,modules,seen)
        require(linked==stored["linked"] and native==stored["native"] and
                {"linked":pin(linked),"stripped":pin(native)}==IDENTITY,"fresh new-class full native capture differs")
        fresh.append(entry);images.append((linked,native))
    require(images[0]==images[1],"two fresh new-class images differ")
    declared=next(c["packages"] for c in record["cases"] if c["name"]==SELECTOR)
    packages,whole=_packages(emitted,flags,images[0][1],declared,products,modules,label=SELECTOR)
    require(pin(whole["packed-xz-bcj"])==PACKED,"fresh complete 5245-byte counted package differs")
    semantics=_semantic(readable,proof,parent,modules,semantic_callback,old,seen)
    fresh.extend({"kind":KIND+".fresh-semantic",**deepcopy(mode)} for mode in semantics["modes"])
    startup=validate_startup(startup_callback(dict(readable),label="no-tid-startup-abi"),readable,bridge,old,seen)
    fresh.append({"kind":KIND+".fresh-startup",**deepcopy(startup),"input_pins":deepcopy(startup["source"]),
                  "commands":[deepcopy(startup["compile"]),deepcopy(startup["execute"])]})
    input_pins=inventory(frozen_inputs)
    input_pins.update({SELF:pin(own),PARENT_ADMISSION:pin(parent_admission_source["frozen"]),BRIDGE:pin(bridge_raw)})
    record_out={"kind":KIND,"family":"D","selector":SELECTOR,"nonreturning":False,"options":list(OPTIONS),
        "profile":validate_profile(parent_record["profile"]),"flags":list(flags),"units":list(UNITS),
        "identity":deepcopy(IDENTITY),"packages":packages,"input_pins":input_pins,"admission_source":pin(own),
        "startup_fixture_authority":pin(bridge_raw),"parent_admission_source":pin(parent_admission_source["frozen"]),
        "parent_admission":deepcopy(parent_record),"parent_admission_record":pin((json.dumps(parent_record,sort_keys=True,indent=2)+"\n").encode()),
        "source_proof":proof,"original_experiment":deepcopy(RECEIPT),"identifier_composition":old._composition(legacy,reduction),
        "fresh_commands":[*deepcopy(parent_record["fresh_commands"]),*fresh],
        "semantic_observations":semantics,"startup_mechanism":startup,
        "ownership_policy":POLICY,"last_search_output_required":False,"input_contract":INPUT_CONTRACT,
        "kernel_tid_handshake":False,"callback_contract":"fixed work; returning callback SYS_exit fallback retained",
        "source_admitted":True,"native_admitted":True,"package_generation_admitted":True,
        "actual_search_semantics_admitted":True,"new_three_argument_startup_admitted":True,
        "fresh_full_artifact_runtime":False,"rules_qualified":False,"physical_placement_qualified":False,
        "size_qualified":False,"strength_qualified":False,"event_target_confirmed":False,"selected":False,
        "scope":"local no-TID persistent raw-clone P4 class; actual full runtime still required"}
    return NoTidAdmission(_TOKEN,record_out,parent,old,readable,emitted,whole,images[0][1],images[0][0]).assert_valid()
