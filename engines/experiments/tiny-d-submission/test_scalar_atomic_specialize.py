#!/usr/bin/env python3
"""Finite typed-int atomic experiment; explicit CLI owns all external work.

Discovery and --self-test start no tools. Cost mode freezes the known cleanup
closure, replays its canonical source/compiler/package experiment, then compares
exact atomic forms, a bounded pthread publication fixture, actual PVS residues
and the actual board prefix. This is no full engine or target-runtime approval.
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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
READER = "engines/scripts/production_input.py"
PARENT_SHA = "cc70e03f62e540fa087e3a651bfe6c80b8957f0902284bf884586002dce75fed"
READER_SHA = "770ddab0bf142d5d39f5737b04e05c541208efd61a9bdf235d4c1e43c8f1cbc1"
EXTRA = (D + "scalar_atomic_specialize.py", D + "test_scalar_atomic_specialize.py",
         "engines/experiments/tcec-next/profile_rules.py", "engines/tests/chess_oracle.py")
FILES = ("main.c", "start.S", "image.ld")
READABLE = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def normalized(data):
    data = data.replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named source")
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def specialize():
    return load("D_scalar_atomic_helper", HERE / "scalar_atomic_specialize.py")


def bounded_cpu_limits(requested_soft, requested_hard, current_soft, current_hard, *, infinity=-1):
    """A nested owner may tighten, but never raise, either existing CPU limit."""
    values=(requested_soft,requested_hard,current_soft,current_hard)
    require(all(type(value) is int and (value==infinity or value>=0) for value in values),
            "finite nonnegative CPU limits or the explicit infinity sentinel required")
    def minimum(*items):
        finite=[value for value in items if value!=infinity]
        return min(finite) if finite else infinity
    hard=minimum(requested_hard,current_hard)
    soft=minimum(requested_soft,current_soft,hard)
    require(soft==infinity or soft>0,"inherited CPU soft limit permits no further work")
    require(hard==infinity or (hard>0 and soft!=infinity and soft<=hard),
            "positive ordered effective CPU limits required")
    return soft,hard


def splice(data, edits):
    """Fixture-only finite splices, with an independently complete inverse."""
    parts, proof, at, target = [], [], 0, 0
    for begin, end, before, after, role in edits:
        require(type(begin) is int and type(end) is int and at <= begin < end <= len(data),
                "ordered fixture splice bounds required")
        require(data[begin:end] == before and isinstance(after, bytes), "exact fixture splice differs")
        gap = data[at:begin]
        parts.extend((gap, after)); target += len(gap)
        proof.append(dict(begin=begin, end=end, target=target, before=before.decode(),
                          after=after.decode(), role=role, gap=pin(gap)))
        target += len(after); at = end
    parts.append(data[at:]); output = b"".join(parts)
    record = dict(input=pin(data), output=pin(output), edits=proof, tail=pin(data[at:]))
    require(unsplice(output, record) == data, "complete fixture splice inverse differs")
    return output, record


def unsplice(output, proof):
    require(pin(output) == proof["output"], "fixture output pin differs")
    parts, at, original_at = [], 0, 0
    for row in proof["edits"]:
        target, after, before = row["target"], row["after"].encode(), row["before"].encode()
        require(type(target) is int and at <= target <= len(output) and
                output[target:target+len(after)] == after, "fixture inverse replacement differs")
        gap = output[at:target]
        require(pin(gap) == row["gap"] and row["begin"] == original_at + len(gap) and
                row["end"] == row["begin"] + len(before), "fixture inverse complement differs")
        parts.extend((gap, before)); at = target + len(after); original_at = row["end"]
    require(pin(output[at:]) == proof["tail"], "fixture inverse tail differs")
    parts.append(output[at:]); original = b"".join(parts)
    require(pin(original) == proof["input"], "fixture inverse input differs")
    return original


def hooked(expression, row):
    """Observe operand evaluation without changing the returned operand values."""
    operands = [("pointer", row["pointer"], "pointer_once")]
    if row["value"] is not None:
        operands.append(("value", row["value"], "value_once"))
    operands.append(("order", row["order"], "order_once"))
    data = expression
    for role, value, observer in operands:
        before = ("(" + value + ")").encode()
        require(data.count(before) == 1, "unique actual atomic " + role + " operand required")
        data = data.replace(before, ("(" + observer + "(" + value + "))").encode())
    return data


ATOMIC_HEADER = r'''#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <sched.h>
#include <limits.h>
typedef _Atomic int U;
static U T,epoch,P;
enum {l=memory_order_relaxed,L=memory_order_acquire,G=memory_order_release};
_Static_assert(sizeof(U)==4&&sizeof(int)==4&&_Alignof(U)==_Alignof(int),"int atomic layout");
_Static_assert(ATOMIC_INT_LOCK_FREE==2&&__atomic_always_lock_free(4,0),"lock-free int");
_Static_assert(__builtin_types_compatible_p(__typeof__(T),U),"atomic storage retained");
_Static_assert(l==0&&L==2&&G==3&&memory_order_acq_rel==4&&memory_order_seq_cst==5,"orders");
static unsigned pointers,values,orders,last_order;
static U *pointer_once(U *p){pointers++;return p;}
static int value_once(int v){values++;return v;}
static int order_once(int v){orders++;last_order=(unsigned)v;return v;}
static void broken(const char *s){fprintf(stderr,"BROKEN %s\n",s);exit(3);}
'''


def render_atomic_probe(proof, *, candidate):
    rows = proof["edits"]
    require(len(rows) == 12 and sum(r["operation"] == "load" for r in rows) == 5 and
            sum(r["operation"] == "store" for r in rows) == 7, "actual twelve-form inventory required")
    functions, checks = [], []
    for index, row in enumerate(rows):
        expression = row["after" if candidate else "before"].encode()
        observed = hooked(expression, row)
        is_load = row["operation"] == "load"
        result = "int" if is_load else "void"
        prefix = "return " if is_load else ""
        for suffix, data in (("", expression), ("_hook", observed)):
            functions.append((f"__attribute__((noinline,noclone)) static {result} op{index}{suffix}(void){{{prefix}__extension__ ").encode() + data + b";}\n")
        target = row["pointer"][1:]
        if is_load:
            checks.append(f'''for(unsigned k=0;k<sizeof samples/sizeof*samples;k++){{
__atomic_store_n((int*)&{target},samples[k],0);if(op{index}()!=samples[k])broken("load{index}");direct++;}}
__atomic_store_n((int*)&{target},17,0);pointers=values=orders=0;
if(op{index}_hook()!=17)broken("hookload{index}");
''')
        else:
            checks.append(f'''__atomic_store_n((int*)&{target},-19,0);op{index}();
if(__atomic_load_n((int*)&{target},0)!=({row['value']}))broken("store{index}");direct++;
pointers=values=orders=0;op{index}_hook();
''')
        checks.append(f'''if(pointers!=1||values!={int(not is_load)}||orders!=1||last_order!={row['order_value']})broken("once{index}");hook_count++;
''')
    # These are the actual shipping operation roles, not synthetic memory orders.
    body = r'''
enum {W=4,ROUNDS=64};
static int startup[W],work_values[W],job,published;
static void *worker(void *arg){
 int id=(int)(uintptr_t)arg,seen=0;startup[id]=id+101;
 __atomic_fetch_sub((&P),(1),(G));
 for(int round=1;round<=ROUNDS;round++){
  int current;while((current=op5())==seen)sched_yield();seen=current;
  if(job!=current)broken("release-acquire publication");
  work_values[id]=job*17+id;
  if(__atomic_fetch_sub((&P),(1),(memory_order_acq_rel))==2){
   for(int i=0;i<W;i++)if(work_values[i]!=current*17+i)broken("pending release sequence");
   published=current;op6();
  }
 }
 return 0;
}
static void pool(void){
 pthread_t threads[W];op11();
 for(int i=0;i<W;i++)if(pthread_create(&threads[i],0,worker,(void*)(uintptr_t)i))broken("pthread_create");
 while(op8())sched_yield();
 for(int i=0;i<W;i++)if(startup[i]!=i+101)broken("startup first-touch witness");
 for(int round=1;round<=ROUNDS;round++){
  job=round;op10();__atomic_fetch_add((&epoch),(1),(G));
  while(op8())sched_yield();if(published!=round)broken("complete publication");
 }
 for(int i=0;i<W;i++)if(pthread_join(threads[i],0))broken("pthread_join");
}
int main(void){
 unsigned direct=0,hook_count=0;static const int samples[]={INT_MIN,-1,0,17,INT_MAX};
@CHECKS@
 __atomic_store_n((int*)&T,0,0);__atomic_store_n((int*)&epoch,0,0);__atomic_store_n((int*)&P,0,0);
 pool();printf("ATOMIC forms=12 direct=%u hooks=%u workers=4 epochs=64 residues=256\n",direct,hook_count);
 return direct==32&&hook_count==12?0:4;
}
'''.replace("@CHECKS@", "".join(checks)).encode()
    data = ATOMIC_HEADER.encode() + b"".join(functions) + body
    return data, dict(kind="D-actual-twelve-int-atomic-fixture-v1", candidate=candidate,
        driver=pin(data), exact_forms=[pin(r["after" if candidate else "before"].encode()) for r in rows],
        eval_once="separate operand hooks return identical values; dynamic order instrumentation is not a hardware-order proof",
        persistent_pool="4 pthread workers,64 finite epochs; actual release/acquire/pending roles; no raw-clone engine",
        isolated_libc_fixture=True, full_engine=False, target_qualification=False)


def pvs_bridge(files, atomic_proof):
    """Five actual search roles only; no generic atomic/source rewriter."""
    data = files["search.c"]
    expected = [r for r in atomic_proof["edits"] if r["pointer"] == "&T"][:5]
    require([r["operation"] for r in expected] == ["load", "store", "store", "load", "load"],
            "exact shipping search atomic role order differs")
    needles = {"load": b"atomic_load_explicit(&stopped,memory_order_relaxed)",
               "store": b"atomic_store(&stopped,1)"}
    inactive=b"do{if(n>=limit){atomic_store(&stopped,1);return 0;}}"
    require(data.count(inactive)==1 and data.count(needles["load"]) == 3 and
            data.count(needles["store"]) == 3,"five active and one DEV-only search atomic sites required")
    inactive_at=data.index(inactive)+inactive.index(needles["store"])
    located = []
    for operation, needle in needles.items():
        located.extend((m.start(), m.end(), operation, needle) for m in re.finditer(re.escape(needle), data)
                       if m.start()!=inactive_at)
    located.sort(); edits = []
    for (begin, end, operation, needle), row in zip(located, expected):
        require(operation == row["operation"], "shipping/readable search role correspondence differs")
        after = row["after"].replace("&T", "&stopped")
        after = re.sub(r"\bl\b", "memory_order_relaxed", after).encode()
        edits.append((begin, end, needle, after, "actual-search-"+operation))
    output, proof = splice(data, edits)
    transformed = {**files, "search.c": output}
    bridge = dict(kind="D-fixture-only-five-search-atomic-role-bridge-v1",
        input={n:pin(d) for n,d in files.items()},output={n:pin(d) for n,d in transformed.items()},
        options=["previous-piece", "unsigned-history"],splices=proof,
        actual_shipping_roles=expected,normalization={"T":"stopped","l":"memory_order_relaxed"},
        inactive_DEV_only_store_retained=pin(inactive),fixture_only=True,shipping_source_changed=False)
    return transformed, bridge


def disassembly_summary(data):
    """Diagnostic only; classify actual objdump instruction text and bytes."""
    instructions=[];functions={};current=None
    for line in data.decode("ascii").splitlines():
        label=re.match(r"^\s*[0-9a-f]+ <([^>]+)>:$",line)
        if label:
            current=label[1];functions.setdefault(current,[]);continue
        fields=line.split("\t")
        if len(fields)<3 or not re.match(r"\s*[0-9a-f]+:$",fields[0]):continue
        codes=fields[1].strip().split();text=fields[2].strip()
        if not codes or not all(re.fullmatch("[0-9a-f]{2}",x) for x in codes) or not text:continue
        item=dict(bytes="".join(codes),instruction=text);instructions.append(item)
        if current is not None:functions[current].append(item)
    require(instructions,"actual objdump instruction rows required")
    def counts(rows):
        return dict(instructions=len(rows),mov=sum(re.match(r"mov\w*\s",q["instruction"]) is not None for q in rows),
            xchg=sum(re.match(r"xchg\s",q["instruction"]) is not None for q in rows),
            lock=sum(q["instruction"].startswith("lock ") for q in rows),
            cmpxchg16b=sum("cmpxchg16b" in q["instruction"] for q in rows))
    return dict(output=pin(data),all=counts(instructions),instructions=instructions,
                isolated_actual_forms={name:counts(rows) for name,rows in functions.items()
                                       if re.fullmatch(r"op\d+",name)},
                scope="diagnostic instruction classification; no semantic or target-runtime admission")


class ScalarAtomicProperties(unittest.TestCase):
    def test_nested_cpu_limits_never_raise_soft_or_hard(self):
        self.assertEqual(bounded_cpu_limits(400,450,330,360),(330,360))
        self.assertEqual(bounded_cpu_limits(100,200,330,360),(100,200))
        self.assertEqual(bounded_cpu_limits(400,200,330,360),(200,200))
        for current_soft,current_hard in ((1,2),(330,360),(360,360)):
            soft,hard=bounded_cpu_limits(400,450,current_soft,current_hard)
            self.assertLessEqual(soft,current_soft)
            self.assertLessEqual(hard,current_hard)
            self.assertLessEqual(soft,hard)
        with self.assertRaises(ValueError):bounded_cpu_limits(400,450,0,0)

    def test_nested_cpu_limits_handle_explicit_infinity(self):
        self.assertEqual(bounded_cpu_limits(400,450,-1,-1),(400,450))
        self.assertEqual(bounded_cpu_limits(400,450,330,-1),(330,450))
        self.assertEqual(bounded_cpu_limits(400,450,-1,360),(360,360))
        self.assertEqual(bounded_cpu_limits(-1,-1,-1,-1),(-1,-1))
        self.assertEqual(bounded_cpu_limits(400,450,999,999,infinity=999),(400,450))
        for values in ((400,450,-2,360),(400.0,450,330,360),(400,450,True,360)):
            with self.assertRaises(ValueError):bounded_cpu_limits(*values)

    def test_inverse_preserves_every_gap_and_rejects_tampering(self):
        data=b"prefixFIRSTmiddleSECONDtail";output,proof=splice(data,[(6,11,b"FIRST",b"x","first"),(17,23,b"SECOND",b"zz","second")])
        self.assertEqual(unsplice(output,proof),data)
        for changed in (output+b"x",b"!"+output[1:]):
            with self.assertRaises(ValueError):unsplice(changed,proof)
        bad=deepcopy(proof);bad["edits"][1]["target"]+=1
        with self.assertRaises(ValueError):unsplice(output,bad)

    def test_hooked_operands_have_one_explicit_observer_each(self):
        helper=specialize()
        for _,_,operation,pointer,value,order in helper.OPS:
            row=dict(pointer=pointer,value=value,order=order)
            for form in helper.expressions(operation,pointer,value,order):
                result=hooked(form,row)
                self.assertEqual(result.count(b"pointer_once("),1)
                self.assertEqual(result.count(b"order_once("),1)
                self.assertEqual(result.count(b"value_once("),int(value is not None))

    def test_exact_inventory_and_new_class_no_identity_waiver(self):
        helper=specialize()
        self.assertEqual(len(helper.OPS),12)
        self.assertEqual(sum(r[2]=="load" for r in helper.OPS),5)
        self.assertEqual(sum(r[2]=="store" and r[5]=="5" for r in helper.OPS),2)
        self.assertEqual(len(helper.FETCHES),3)
        for bad in ({},{n:b"x" for n in helper.INPUTS}):
            with self.assertRaises(ValueError):helper.transform(bad)
        with self.assertRaises(ValueError):helper.restore({},dict(kind="old-native-map"))

    def test_all_twelve_replacements_preserve_extension_token_boundary(self):
        helper=specialize()
        for _,_,operation,pointer,value,order in helper.OPS:
            _,after=helper.expressions(operation,pointer,value,order)
            self.assertTrue(after.startswith(b"(") and after.endswith(b")"))
            # Shipping templates immediately follow this keyword without a gap.
            tokens=re.findall(rb"[A-Za-z_][A-Za-z_0-9]*|[^\s]",b"__extension__"+after)
            self.assertEqual(tokens[:2],[b"__extension__",b"("])
            self.assertEqual(sum(t==b"__extension__" for t in tokens),1)
            self.assertFalse(any(t.startswith(b"__extension____atomic") for t in tokens))

    def test_pvs_bridge_rejects_missing_or_extra_roles(self):
        with self.assertRaises(ValueError):pvs_bridge({"search.c":b""},{"edits":[]})

    def test_disassembly_counts_only_instruction_rows(self):
        result=disassembly_summary(b"0000000000400000 <op1>:\n  400000:\t87 05 12 00 00 00 \txchg DWORD PTR [rip+0x12],eax\n  400006:\tf0 0f c7 0f \tlock cmpxchg16b OWORD PTR [rdi]\n")
        self.assertEqual(result["all"]["instructions"],2)
        self.assertEqual(result["all"]["xchg"],1)
        self.assertEqual(result["all"]["lock"],1)
        self.assertEqual(result["isolated_actual_forms"]["op1"]["cmpxchg16b"],1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--report",type=Path)
    parser.add_argument("--report-sha256")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if args.self_test:
        require(args.report is None and args.out is None and args.report_sha256 is None,
                "pure self-test cannot also request external work")
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ScalarAtomicProperties))
        if not result.wasSuccessful():raise SystemExit(1)
        return
    require(sys.platform=="linux" and args.report and args.out and args.report.is_absolute() and
            args.out.is_absolute() and args.report_sha256==PARENT_SHA,"explicit known cleanup receipt/new Linux output required")
    out=args.out.resolve();parent=args.report.resolve().parent
    require(not out.exists() and not any((p/".git").exists() for p in (out,*out.parents)),"new external output required")
    reader_bytes=normalized((ROOT/READER).read_bytes());require(pin(reader_bytes)["sha256"]==READER_SHA,"bounded reader differs")
    reader=load("D_scalar_initial_reader",ROOT/READER)
    raw=reader.read_regular(args.report,limit=4<<20);require(pin(raw)["sha256"]==PARENT_SHA,"cleanup receipt differs")
    record=json.loads(raw)
    require(record.get("kind")=="D-closed-TU-cleanup-native-identity-cost-v1" and
            all(record.get(k) is True for k in ("complete","source_reproduced","native_reproduced")) and
            record.get("selected") is False and record.get("host_cleanup")=={"unsettled_commands":0,"errors":[]},
            "complete unselected cleanup source/native control required")
    inputs={}
    for name,want in {**record["inputs"],**record["tools"]}.items():
        data=reader.read_regular(parent/"inputs"/name,limit=4<<20)
        require(pin(data)==want,"parent frozen source/tool differs: "+name)
        if name.startswith("engines/"):
            require(normalized(reader.read_regular(ROOT/name,limit=4<<20))==data,"current/frozen source differs: "+name)
        inputs[name]=data
    for name in EXTRA:
        require(name not in inputs,"new explicit fixture/tool closure overlaps parent")
        inputs[name]=normalized(reader.read_regular(ROOT/name,limit=4<<20))
    original=reader.read_regular(parent/"parent-receipt.json",limit=4<<20)
    require(pin(original)==record["parent_receipt"],"canonical structural parent receipt differs")
    structural=json.loads(original);selector=record["selector"]
    names=[selector+"/generated-readable/"+n for n in READABLE]
    names += [selector+"/shipping-inputs/"+n for n in FILES]
    names += [selector+"/native-"+str(i)+"/"+n for i in range(2) for n in ("linked","native")]
    names += [selector+"/packed-xz-bcj",selector+"/source-jit-compressed","target/audit.json","target/compiler-wrapper"]
    products={n:reader.read_regular(parent/"parent-products"/n,limit=4<<20) for n in names}
    require(record.get("SDK11") and all(len(c.get("SDK11",[]))==2 for c in record["cases"]),"paired audited SDK11 parent required")
    for c in record["cases"]:
        for n,want in c["shipping"].items():
            data=reader.read_regular(parent/c["name"]/"shipping-inputs"/n,limit=1<<20)
            require(pin(data)==want,"actual parent cleanup source differs")
    out.mkdir()
    for n,d in inputs.items():write(out/"inputs",n,d)
    for n,d in products.items():write(out/"parent-products",n,d)
    write(out,"parent-receipt.json",raw);write(out,"structural-receipt.json",original)
    frozen=load("D_scalar_frozen_driver",out/"inputs"/(D+"test_scalar_atomic_specialize.py"))
    frozen.run_experiment(out,ROOT,record,structural,original,inputs,products)


def run_experiment(out,origin,parent,structural,structural_raw,inputs,products):
    scalar=specialize();reader=load("D_scalar_reader",ROOT/READER)
    old=load("D_scalar_cleanup_replay",HERE/"test_closed_tu_cleanup.py")
    oldinputs={n:inputs[n] for n in parent["inputs"]};oldtools={n:inputs[n] for n in parent["tools"]}
    replay=out/"canonical-replay";replay.mkdir()
    old.run_experiment(replay,origin,structural,structural_raw,oldinputs,products,oldtools,parent["SDK11"])
    replay_raw=(replay/"results.json").read_bytes();replayed=json.loads(replay_raw)
    require(replayed.get("complete") and replayed.get("cleanup_proof")==parent["cleanup_proof"] and
            replayed.get("host_cleanup")=={"unsettled_commands":0,"errors":[]},"fresh full cleanup replay failed")
    for actual,want in zip(replayed["cases"],parent["cases"]):
        require(actual["name"]==want["name"] and actual["shipping"]==want["shipping"] and
                actual["packages"]==want["packages"],"fresh cleanup source/package replay differs")
    source=load("D_scalar_source",HERE/"source.py");builder=load("D_scalar_builder",HERE/"build.py")
    startup=load("D_scalar_startup",HERE/"test_startup.py")
    packer=load("D_scalar_packer",source.CANONICAL/"packer.py")
    packaging=load("D_scalar_packaging",HERE/"packaging.py")
    compressed=load("D_scalar_compressed",HERE/"compressed_bootstrap.py")
    hostmod=load("D_scalar_commands",ROOT/source.HOST)
    require(pin(inputs[source.HOST])["sha256"]==source.HOST_SHA,"original command owner differs")
    report=dict(kind="D-typed-scalar-atomic-semantic-native-cost-v1",complete=False,frozen_execution=True,
        parent_receipt=pin((out/"parent-receipt.json").read_bytes()),source_replay_receipt=pin(replay_raw),
        source_replay_path=str(replay/"results.json"),inputs={n:pin(d) for n,d in inputs.items()},commands=[],
        cases=[],semantic=[],source_reproduced=True,semantic_qualified=False,full_typed_admission=False,
        rules_qualified=False,runtime_qualified=False,engine_executed=False,selected=False,
        target11_runtime_qualified=False,old_native_map_changed=False,production_packaging_changed=False,
        scope="fresh source, isolated atomics, actual PVS/order/prior/learner and board rules; finite native/package cost only")
    save=lambda:(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=None
    def run(command,*,cwd,kind,data=None):
        result=host.run(command,cwd=cwd,kind=kind,data=data)
        startup.require_execution(report["commands"][-1],0);return result
    try:
        import resource
        current_cpu=resource.getrlimit(resource.RLIMIT_CPU)
        effective_cpu=bounded_cpu_limits(400,450,*current_cpu,infinity=resource.RLIM_INFINITY)
        report["parent_CPU_limits"]=dict(requested=[400,450],observed=list(current_cpu),
            effective=list(effective_cpu),infinity=resource.RLIM_INFINITY,
            policy="neither current soft nor current hard may be raised by the nested owner")
        hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":600,"per_command_wall":75,
                        "parent_CPU":effective_cpu[0],"parent_CPU_hard":effective_cpu[1],
                        "child_CPU":60,"tool_output_bytes":8<<20}
        report["host_construction_complete"]=False;save()
        host=hostmod.Host(out,report,save)
        report["host_construction_complete"]=True;save()
        compiler_path=Path(shutil.which("cc") or "").resolve()
        objdump_path=Path(shutil.which("objdump") or "").resolve()
        require(compiler_path.is_file() and objdump_path.is_file(),"installed compiler and objdump required")
        report["tools_observed"]={}
        for label,path in (("GCC13",compiler_path),("SDK11",Path(parent["SDK11"]["compiler"])),("objdump",objdump_path)):
            version=run([str(path),"--version"],cwd=out,kind=label+"-version").decode().splitlines()[0]
            report["tools_observed"][label]=dict(path=str(path),version=version,
                executable=pin(reader.read_regular(path,limit=8<<20)))
        control={n:(replay/"cleanup/shipping-inputs"/n).read_bytes() for n in FILES}
        candidate,proof=scalar.transform(control)
        require(scalar.restore(candidate,json.loads(json.dumps(proof)))==control,"typed full inverse differs")
        report["scalar_proof"]=proof
        variants=(("control",control),("scalar",candidate))
        for name,files in variants:
            for n,d in files.items():write(out/name/"shipping-inputs",n,d)
        # Exact twelve forms + finite persistent-pool publication, before native costs.
        atomic_reference=None
        for name,_ in variants:
            driver,fixtureproof=render_atomic_probe(proof,candidate=name=="scalar")
            for mode,extra in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
                directory=out/name/("atomic-"+mode);write(directory,"driver.c",driver)
                binary=directory/"x"
                run(["cc","-std=c11","-O2","-g0","-pthread",*extra,str(directory/"driver.c"),"-o",str(binary)],
                    cwd=directory,kind=name+"-atomic-compile-"+mode)
                output=run([str(binary)],cwd=directory,kind=name+"-atomic-run-"+mode)
                require(output==b"ATOMIC forms=12 direct=32 hooks=12 workers=4 epochs=64 residues=256\n",
                        "exact atomic/persistent-pool observations incomplete")
                if atomic_reference is None:atomic_reference=output
                require(output==atomic_reference,"atomic observations differ")
                report["semantic"].append(dict(kind="atomic",name=name,mode=mode,proof=fixtureproof,
                    output=pin(output),binary=pin(binary.read_bytes()),equal=True));save()
                if mode=="plain":
                    dump=run([str(objdump_path),"-d","-Mintel",str(binary)],cwd=directory,kind=name+"-atomic-disassembly")
                    write(directory,"objdump.txt",dump)
                    report["semantic"][-1]["disassembly"]=disassembly_summary(dump)
                    save()
        # Fresh actual PVS/order/previous-piece/learner/cancellation fixture.
        search=load("D_scalar_search_probe",HERE/"probe_search_compact.py")
        storage=load("D_scalar_storage_fixture",HERE/"check_storage.py")
        selected=next(v for v in structural["variants"] if v["name"]==parent["selector"])
        readable={n:products[parent["selector"]+"/generated-readable/"+n] for n in READABLE}
        bridged,bridgeproof=pvs_bridge(readable,proof);report["PVS_bridge"]=bridgeproof
        pvs_reference=None
        for name,files,sourceproof in (("control",readable,selected["proof"]),("scalar",bridged,bridgeproof)):
            observed,driver,fixtureproof=search.render(files,source,storage,reference_board=readable["board.c"],
                variant_proof=sourceproof,prefix=True,dense=False,previous_index=True,unsigned_history=True)
            for mode in ("plain","ubsan"):
                directory=out/name/("pvs-"+mode)
                for n in ("tiny.h","board.c","search.c"):write(directory,n,observed[n])
                write(directory,"driver.c",driver);binary=directory/"x"
                run(["cc",*search.compiler_flags(prefix=True,dense=False,previous_index=True,unsigned_history=True,mode=mode),
                     str(directory/"driver.c"),"-o",str(binary)],cwd=directory,kind=name+"-pvs-compile-"+mode)
                output=run([str(binary)],cwd=directory,kind=name+"-pvs-run-"+mode)
                semantic,summary=search.verify_output(output)
                if pvs_reference is None:pvs_reference=semantic
                require(semantic==pvs_reference,"actual specialized PVS/order/prior/learner residues differ")
                report["semantic"].append(dict(kind="PVS",name=name,mode=mode,proof=fixtureproof,
                    output=pin(output),summary=summary,binary=pin(binary.read_bytes()),equal=True));save()
        # Exact final-TU board prefix; no search/runtime or giant table allocated.
        shared=load("D_scalar_rules",ROOT/"engines/experiments/tcec-next/profile_rules.py")
        cases,coverage=shared.fixture_cases();report["rules_coverage"]=coverage
        prefixes=[]
        for _,files in variants:
            matches=list(re.finditer(rb"\bstatic g probe\(",files["main.c"]))
            require(len(matches)==1,"actual board/search boundary differs")
            prefixes.append(files["main.c"][:matches[0].start()])
        require(prefixes[0]==prefixes[1],"typed specialization changed actual board prefix")
        declarations=(b"\ntypedef F size_t;extern int printf(const char*,...);extern int puts(const char*);"
            b"extern char*strcpy(char*,const char*);extern F strlen(const char*);"
            b"extern int strcmp(const char*,const char*);extern char*strtok_r(char*,const char*,char**);\n")
        driver=shared.render_bound_fixture(prefixes[0],dict(board="y",start="start",generate="gen",make="make",four_args=False),cases,declarations)
        report["rules_binding"]=dict(prefix=pin(prefixes[0]),same_both_sources=True,fixture=pin(driver),
            explicit_fixture_libc_declarations=pin(declarations),cases=len(cases),actual_runtime=False)
        for mode,extra in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
            directory=out/("rules-"+mode);write(directory,"driver.c",driver);binary=directory/"x"
            run(["cc","-std=c11","-O1","-g0","-fno-builtin","-msse4.2","-mcx16",*extra,
                 str(directory/"driver.c"),"-o",str(binary)],cwd=directory,kind="rules-compile-"+mode)
            output=run([str(binary)],cwd=directory,kind="rules-run-"+mode)
            summary=shared._compare_output(output,cases)
            require(summary["cases"]==105 and summary["legal_moves_compared"]==2858,"actual board oracle coverage differs")
            report["semantic"].append(dict(kind="rules",mode=mode,summary=summary,binary=pin(binary.read_bytes())));save()
        report["semantic_qualified"]=True
        flags=parent["compiler_flags"];units=parent["units"];profile=source.production().resource_profile("test-p4")
        report.update(compiler_flags=flags,units=units,resource=profile.to_record(16),SDK11=parent["SDK11"])
        for name,files in variants:
            directory=out/name;row=dict(name=name,shipping={n:pin(d) for n,d in files.items()},native=[],SDK11=[],packages=[])
            for compiler,label,bucket in (("cc","GCC13",row["native"]),(parent["SDK11"]["compiler"],"SDK11",row["SDK11"])):
                repetitions=[]
                for index in range(2):
                    attempt=directory/(label+"-"+str(index));attempt.mkdir()
                    run([compiler,*flags,*[str(directory/"shipping-inputs"/n) for n in units],
                         "-Wl,-T,"+str(directory/"shipping-inputs/image.ld"),"-o",str(attempt/"linked")],
                        cwd=attempt,kind=name+"-"+label+"-native-"+str(index))
                    linked=(attempt/"linked").read_bytes();native=packer.strip_native(linked);write(attempt,"native",native)
                    builder.kernel_geometry(packer,linked,profile.workers);builder.kernel_geometry(packer,native,profile.workers)
                    identity=dict(linked=pin(linked),stripped=pin(native));repetitions.append(identity)
                    bucket.append(dict(**identity,command=report["commands"][-1]))
                require(repetitions[0]==repetitions[1],"two fresh same-class native images differ")
                if name=="control":
                    oldrow=parent["cases"][1]["native_rebuilds" if label=="GCC13" else "SDK11"][0]
                    require(repetitions[0]=={k:oldrow[k] for k in ("linked","stripped")},"actual cleanup control native differs")
                dump=run([str(objdump_path),"-d","-Mintel",str(directory/(label+"-0")/"linked")],cwd=directory,
                         kind=name+"-"+label+"-shipping-disassembly")
                write(directory,label+"-objdump.txt",dump)
                row.setdefault("disassembly",{})[label]=disassembly_summary(dump)
            native=(directory/"GCC13-0/native").read_bytes()
            for route in ("source-jit","source-jit-compressed","packed-xz-bcj"):
                repetitions=[]
                for index in range(2):
                    if route=="source-jit":whole,detail=packaging.package_source(files,flags,units)
                    elif route=="source-jit-compressed":whole,detail=compressed.package_source(files,flags,units,packaging)
                    else:whole,detail=packaging.package_native(native,"xz-bcj")
                    decoded=lzma.decompress(whole[detail["header_bytes"]:])
                    if route=="packed-xz-bcj":require(decoded==native,"entire new native package inverse differs")
                    else:
                        bundle=json.loads(decoded) if route=="source-jit" else ast.literal_eval(ast.parse(decoded).body[1].value)
                        require(bundle==dict(files={n:d.decode() for n,d in sorted(files.items())},flags=flags,units=units),
                                "new whole exact source bundle inverse differs")
                    write(directory,route+"-"+str(index),whole);repetitions.append(dict(whole=pin(whole),package=detail))
                require(repetitions[0]==repetitions[1],"two fresh whole packages differ")
                if name=="control":
                    previous=next(p for p in parent["cases"][1]["packages"] if p["route"]==route)
                    require(repetitions[0]["whole"]==previous["whole"],"cleanup control whole differs")
                row["packages"].append(dict(route=route,**repetitions[0],reproduced=True,actual_whole_inverse=True))
            report["cases"].append(row);save()
        a,b=report["cases"]
        report["whole_savings"]={x["route"]:x["whole"]["bytes"]-y["whole"]["bytes"] for x,y in zip(a["packages"],b["packages"])}
        report["new_codegen"]={label:a[bucket][0]["linked"]!=b[bucket][0]["linked"] for label,bucket in (("GCC13","native"),("SDK11","SDK11"))}
        report["instruction_differences"]={label:dict(
            control=a["disassembly"][label]["all"],candidate=b["disassembly"][label]["all"],
            identical_instruction_rows=a["disassembly"][label]["instructions"]==b["disassembly"][label]["instructions"],
            function_names_unavailable_in_stripped_shipping=True,
            isolated_form_classification="see atomic plain fixture non-inlined op0..op11; hooks excluded")
            for label in ("GCC13","SDK11")}
        report["source_current_after"]={n:pin(normalized(reader.read_regular(origin/n,limit=4<<20))) for n in inputs if n.startswith("engines/")}
        require(report["source_current_after"]=={n:pin(d) for n,d in inputs.items() if n.startswith("engines/")},"source changed during typed experiment")
        for path,key in ((parent["SDK11"]["compiler"],"wrapper"),(parent["SDK11"]["audit_path"],"audit")):
            require(pin(reader.read_regular(Path(path),limit=1<<20))==parent["SDK11"][key],"known SDK11 audit/wrapper changed")
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
                         semantic_qualified=report["semantic_qualified"],engine_executed=False)),flush=True)


if __name__ == "__main__":
    main()
