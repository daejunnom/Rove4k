#!/usr/bin/env python3
"""Two exact-clock cases; explicit cost CLI owns finite external work.

Discovery and --self-test start no tools. Cost mode freezes the known complete
source closure, derives both actual compiler inputs and measures whole files
twice. Only if a route improves does it run generated frontend/key fixtures.
No full engine, large TT, old admission or selected producer is modified.
"""
import argparse
import ast
from copy import deepcopy
import hashlib
import json
import lzma
from pathlib import Path
import re
import sys
import types
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
READER = "engines/scripts/production_input.py"
READER_SHA = "770ddab0bf142d5d39f5737b04e05c541208efd61a9bdf235d4c1e43c8f1cbc1"
PARENT_SHA = "e207630b4272c82e147a765d3e3c19ce8fcbfae50e13c19a7cb0f40c4fb0ee43"
CLEANUP_SHA = "cc70e03f62e540fa087e3a651bfe6c80b8957f0902284bf884586002dce75fed"
SELECTOR = "proved-win-combination"
FILES = ("main.c", "start.S", "image.ld")
READABLE = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")
EXTRA = (D+"exact_clock_predicate.py", D+"test_exact_clock_predicate.py",
         D+"closed_tu_cleanup.py", D+"test_frontend_compact.py", READER)


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def normalized(data):
    data = data.replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named source")
    return data


def load(name, path, data=None):
    """Execute the captured bytes; do not reopen after an identity check."""
    path = Path(path).resolve()
    data = path.read_bytes() if data is None else data
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def write(root, name, data):
    path = root/name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def helper():
    return load("D_exact_clock_pure", HERE/"exact_clock_predicate.py")


def bounded_cpu_limits(requested_soft, requested_hard, current_soft, current_hard, *, infinity=-1):
    values = (requested_soft, requested_hard, current_soft, current_hard)
    require(all(type(v) is int and (v == infinity or v >= 0) for v in values),
            "nonnegative CPU limits or explicit infinity required")
    def minimum(*items):
        finite = [v for v in items if v != infinity]
        return min(finite) if finite else infinity
    hard = minimum(requested_hard, current_hard)
    soft = minimum(requested_soft, current_soft, hard)
    require(soft == infinity or soft > 0, "inherited CPU soft limit permits no work")
    require(hard == infinity or hard > 0 and soft != infinity and soft <= hard,
            "positive ordered effective CPU limits required")
    return soft, hard


def child_cpu_limit(effective_soft, effective_hard, *, requested=40, infinity=-1):
    soft, _ = bounded_cpu_limits(requested,requested,effective_soft,effective_hard,infinity=infinity)
    return soft


def rename(data, names, lexical):
    for old, new in names.items():
        data = lexical._replace({"main.c": data}, old, new)["main.c"]
    return data


def compiler_cleanup(files, control, cleanup, clock):
    """Extend the exact old prefix cleanup only across this later clock edit."""
    require(set(files) == set(control) == set(FILES), "complete actual compiler input required")
    require(files["start.S"] == control["start.S"] and files["image.ld"] == control["image.ld"],
            "clock class changed entry/linker")
    expected, clock_proof = clock._project(control["main.c"], clock.old_expression("o"), clock.predicate("o"))
    require(files["main.c"] == expected, "fresh whole TU differs beyond exact clock expression")
    cleaned_control, control_proof = cleanup.transform(control)
    clock_at = clock_proof["begin"]
    require(max(end for _, end, _ in cleanup.SPANS) <= clock_at,
            "clock edit overlaps old closed-TU declaration prefix")
    for begin, end, _ in cleanup.SPANS:
        require(files["main.c"][begin:end] == control["main.c"][begin:end],
                "clock class changed an old cleanup declaration")
    output, edits = cleanup._project(files["main.c"], cleanup.SPANS)
    require(cleanup._restore(output, edits) == files["main.c"], "new cleanup complete inverse differs")
    cleaned = {**files, "main.c": output}
    protected = cleanup.retention(files)
    require(cleanup.retention(cleaned) == protected and protected == cleanup.retention(control),
            "clock class changed a protected root/ASM/assertion or forward")
    return cleaned, dict(kind="D-exact-clock-after-closed-prefix-cleanup-v1",
        control_cleanup=control_proof, clock_on_complete_TU=clock_proof,
        new_cleanup=edits, retained=protected, old_cleanup_helper_changed=False,
        original_prefix_spans_retained=True, new_native_identity_claimed=False,
        original_cleaned_control=cleanup.pins(cleaned_control), output=cleanup.pins(cleaned))


KEY_FIXTURE = r'''
static int actual_clock_key(Span token){
 if(!token.n)return 0;
 return @EXPRESSION@;
}
static int expected_clock_key(const char *s,unsigned n){
 static const char *const names[]={"wtime","btime","winc","binc"};
 for(unsigned k=0;k<4;k++)if(strlen(names[k])==n&&!memcmp(s,names[k],n))return 1;
 return 0;
}
static void exact_key_checks(void){
 static const char *const names[]={"wtime","btime","winc","binc"};
 long page=sysconf(_SC_PAGESIZE);if(page<=0)fail("pagesize");
 char *map=mmap(0,(size_t)page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 if(map==MAP_FAILED||mprotect(map+page,(size_t)page,PROT_NONE))fail("key-guard");
 unsigned checked=0;
 for(unsigned n=0;n<=6;n++)for(unsigned base=0;base<4;base++){
  char *tail=map+page-n;unsigned length=(unsigned)strlen(names[base]);
  for(unsigned i=0;i<n;i++)tail[i]=i<length?names[base][i]:'#';
  Span token={tail,n};
  if(actual_clock_key(token)!=expected_clock_key(tail,n))fail("key-length");checked++;
  for(unsigned i=0;i<n;i++){
   char old=tail[i];
   for(unsigned value=0;value<256;value++){
    tail[i]=(char)value;
    if(actual_clock_key(token)!=expected_clock_key(tail,n))fail("key-mutation");checked++;
   }
   tail[i]=old;
  }
 }
 if(munmap(map,(size_t)page*2))fail("key-unmap");
 if(checked!=21532)fail("key-count");
 printf("CLOCKKEY cases=%u guard=none-after-span lengths=0..6 bytes=0..255\n",checked);
}
static void extra_go_checks(void){
 static const char *const cases[]={
  "wtimeX 50 wtime 30","btimeX 50 btime 30","win 50 wtime 60","bin 50 btime 60",
  "wincX 200 wtime 90","bincX 200 btime 90","Wtime 50 wtime 30","Binc 50 btime 30",
  "wtime 30 wtimes 90 winc 3","btime 30 btimes 90 binc 3","wtime btime winc 4 wtime 30",
  "binc wtime btime 30","wtime 0000000000000000030 winc 0003",
  "btime 9223372036854775807 binc 9223372036854775807",
  "wtime 9223372036854775808 winc 9223372036854775808","wtime\00130\002winc\0033"
 };
 unsigned checked=0;
 for(int black=0;black<2;black++){
  char setup[64];strcpy(setup,black?"startpos moves e2e4":"startpos");set_position(setup);
  for(unsigned c=0;c<sizeof cases/sizeof *cases;c++){
   char args[1024],oracle_args[1024];strcpy(args,cases[c]);strcpy(oracle_args,cases[c]);
   /* The original scanner's ASCII<=32 separators exceed sscanf whitespace. */
   for(char *p=oracle_args;*p;p++)if((unsigned char)*p<=32)*p=' ';
   uint64_t before=global_position_hash();
   uint64_t expected=reference_deadline(oracle_args,position.s);
   atomic_store_explicit(&pending,0,memory_order_relaxed);
   atomic_store_explicit(&stopped,1,memory_order_relaxed);
   int old_epoch=atomic_load_explicit(&epoch,memory_order_relaxed);go(args);
   if(deadline!=expected||atomic_load_explicit(&pending,memory_order_relaxed)!=WORKERS+1||
      atomic_load_explicit(&stopped,memory_order_relaxed)!=0||
      atomic_load_explicit(&epoch,memory_order_relaxed)!=old_epoch+1||
      before!=global_position_hash())fail("extra-go-publication");
   Board next;if(!fallback||!make(&position,fallback,&next))fail("extra-go-fallback");
   printf("EXTRAGO side=%d case=%u deadline=%" PRIu64 " fallback=%u state=%016" PRIx64 "\n",
          position.s,c,deadline,fallback,before);
   atomic_store_explicit(&pending,0,memory_order_relaxed);checked++;
  }
 }
 if(checked!=32)fail("extra-go-count");
 puts("EXTRAGO cases=32 exact-key/deadline/publication/fallback");
}
'''


def render_frontend(original_driver, clock, *, candidate):
    expression = clock.predicate("token") if candidate else clock.old_expression("token")
    driver = b"#define _GNU_SOURCE\n#include <sys/mman.h>\n#include <unistd.h>\n"+original_driver
    marker = b"int main(void){\n static const struct{const char *s;int id;}ids[]="
    require(driver.count(marker) == 1, "original frontend main marker differs")
    fixture = KEY_FIXTURE.replace("@EXPRESSION@", expression.decode()).encode()
    driver = driver.replace(marker, fixture+b"\n"+marker, 1)
    call = b" position_checks();promotion_checks();clock_checks();puts("
    require(driver.count(call) == 1, "original frontend invocation differs")
    driver = driver.replace(call, b" exact_key_checks();extra_go_checks();"+call, 1)
    return driver, dict(kind="D-exact-clock-frontend-key-fixture-v1", candidate=candidate,
        original_driver=pin(original_driver), driver=pin(driver), expression=pin(expression),
        original_clock_cases=64, extra_go_cases=32, key_checks=21532,
        memory_boundary="each Span ends at a PROT_NONE page; length0 pointer starts in that page",
        libc_fixture=True, full_engine=False)


class ExactClockProperties(unittest.TestCase):
    def test_single_edit_inverse_and_protected_complement(self):
        clock = helper()
        for name in ("token", "o"):
            source = b"prefix\n"+clock.old_expression(name)+b";suffix\n"
            result, proof = clock._project(source, clock.old_expression(name), clock.predicate(name))
            self.assertEqual(clock._restore(result, json.loads(json.dumps(proof))), source)
            for field in ("input", "output"):
                damaged = deepcopy(proof);damaged[field]["sha256"] = "0"*64
                with self.assertRaises(ValueError):clock._restore(result, damaged)
            damaged = deepcopy(proof);damaged["gaps"][1]["bytes"] += 1
            with self.assertRaises(ValueError):clock._restore(result, damaged)
            damaged = bytearray(result);damaged[0] ^= 1
            with self.assertRaises(ValueError):clock._restore(bytes(damaged), proof)

    def test_only_finite_exact_names_and_source_classes(self):
        clock = helper()
        for name in ("t", "token;abort()", "", None):
            with self.assertRaises(ValueError):clock.predicate(name)
            with self.assertRaises(ValueError):clock.old_expression(name)
        for readable, shipping in (({}, {}), ({n:b"x" for n in READABLE}, {n:b"x" for n in FILES})):
            with self.assertRaises(ValueError):clock.transform(readable, shipping)
        with self.assertRaises(ValueError):clock.restore({}, {}, {"kind":"unknown"})
        self.assertFalse(clock.same({"x":True}, {"x":1}))

    def test_predicate_byte_reads_have_exact_length_guards(self):
        clock = helper()
        text = clock.predicate("token").decode()
        self.assertLess(text.index("token.n==5"), text.index("token.p[4]"))
        self.assertLess(text.index("token.n==4"), text.rindex("token.p[3]"))
        self.assertNotIn("uint32", text)
        self.assertNotIn("strcmp", text)
        self.assertEqual(text.count("token.p[0]"), 2)

    def test_projection_requires_unique_nonempty_span(self):
        clock = helper()
        for data, before, after in ((b"abc",b"x",b"y"),(b"aa",b"a",b"b"),
                                     (b"abc",b"",b"b"),(b"abc",b"a",b"a")):
            with self.assertRaises(ValueError):clock._project(data,before,after)
        with self.assertRaises(ValueError):clock._restore(b"x", {"output":pin(b"x"),"begin":True,"after":"x"})

    def test_cpu_limits_never_raise_inherited_soft_or_hard(self):
        self.assertEqual(bounded_cpu_limits(300,330,150,180),(150,180))
        self.assertEqual(bounded_cpu_limits(300,330,330,360),(300,330))
        self.assertEqual(bounded_cpu_limits(300,330,-1,-1),(300,330))
        self.assertEqual(bounded_cpu_limits(300,330,-1,200),(200,200))
        with self.assertRaises(ValueError):bounded_cpu_limits(300,330,0,0)

    def test_child_cpu_limit_never_raises_the_effective_parent_pair(self):
        self.assertEqual(child_cpu_limit(20,30),20)
        self.assertEqual(child_cpu_limit(300,330),40)
        self.assertEqual(child_cpu_limit(-1,-1),40)
        self.assertEqual(child_cpu_limit(15,-1),15)
        with self.assertRaises(ValueError):child_cpu_limit(0,0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--cleanup-report", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.self_test:
        require(args.report is None and args.cleanup_report is None and args.out is None,
                "pure test cannot also request external cost work")
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExactClockProperties))
        if not result.wasSuccessful():raise SystemExit(1)
        return
    require(sys.platform == "linux" and args.report and args.cleanup_report and args.out
            and all(p.is_absolute() for p in (args.report,args.cleanup_report,args.out)),
            "explicit known Linux parent receipts and new absolute output required")
    out, parent_root = args.out.resolve(), args.report.resolve().parent
    cleanup_root = args.cleanup_report.resolve().parent
    require(not out.exists() and not any((p/".git").exists() for p in (out,*out.parents)),
            "new external output required")
    reader_bytes = normalized((ROOT/READER).read_bytes())
    require(pin(reader_bytes)["sha256"] == READER_SHA, "bounded reader identity differs")
    reader = load("D_exact_clock_initial_reader", ROOT/READER, reader_bytes)
    parent_raw = reader.read_regular(args.report,limit=4<<20)
    cleanup_raw = reader.read_regular(args.cleanup_report,limit=4<<20)
    require(pin(parent_raw)["sha256"] == PARENT_SHA and pin(cleanup_raw)["sha256"] == CLEANUP_SHA,
            "exact completed structural and cleanup receipts required")
    parent, cleanup_parent = json.loads(parent_raw), json.loads(cleanup_raw)
    require(parent.get("kind") == "D-structural-search-source-semantic-cost-v1"
            and parent.get("complete") is True and parent.get("frozen_execution") is True
            and parent.get("host_cleanup") == {"unsettled_commands":0,"errors":[]}
            and parent.get("selected") is False, "complete unselected structural source required")
    require(cleanup_parent.get("kind") == "D-closed-TU-cleanup-native-identity-cost-v1"
            and all(cleanup_parent.get(k) is True for k in ("complete","source_reproduced","native_reproduced"))
            and cleanup_parent.get("parent_receipt") == pin(parent_raw)
            and cleanup_parent.get("host_cleanup") == {"unsettled_commands":0,"errors":[]},
            "complete exact cleanup parent required")
    inputs = {}
    require(set(parent["inputs"]) == set(cleanup_parent["inputs"]), "complete source closure differs")
    for name, want in parent["inputs"].items():
        require(name == "selection/build.json" or name.startswith("engines/") and ".." not in Path(name).parts,
                "named engine source closure required")
        data = reader.read_regular(parent_root/"inputs"/name,limit=4<<20)
        require(pin(data) == want == cleanup_parent["inputs"][name], "parent frozen source differs: "+name)
        if name.startswith("engines/"):
            require(normalized(reader.read_regular(ROOT/name,limit=4<<20)) == data,
                    "current/frozen source differs: "+name)
        inputs[name] = data
    for name in EXTRA:
        require(name not in inputs, "new exact fixture/tool closure overlaps original")
        inputs[name] = normalized(reader.read_regular(ROOT/name,limit=4<<20))
    require(pin(inputs[D+"closed_tu_cleanup.py"]) == cleanup_parent["tools"][D+"closed_tu_cleanup.py"],
            "old cleanup helper differs")
    choices = [v for v in parent["variants"] if v.get("name") == SELECTOR]
    require(len(choices) == 1 and choices[0].get("options") == ["previous-piece","unsigned-history"],
            "exact full search combination required")
    selected = choices[0]
    products = {}
    for kind, names, pins in (("generated-readable",READABLE,selected["source"]),
                               ("shipping-inputs",FILES,selected["shipping"])):
        for name in names:
            logical = SELECTOR+"/"+kind+"/"+name
            data = reader.read_regular(parent_root/logical,limit=1<<20)
            require(pin(data) == pins[name], "actual original source product differs")
            products[logical] = data
    require([c["name"] for c in cleanup_parent["cases"]] == ["control","cleanup"],
            "finite closed-TU parent cases differ")
    for name,want in cleanup_parent["cases"][1]["shipping"].items():
        data = reader.read_regular(cleanup_root/"cleanup/shipping-inputs"/name,limit=1<<20)
        require(pin(data) == want, "actual cleaned compiler source differs")
        products["cleanup/"+name] = data
    sdk = cleanup_parent["SDK11"]
    for name, key in (("compiler","wrapper"),("audit_path","audit")):
        data = reader.read_regular(Path(sdk[name]),limit=1<<20)
        require(pin(data) == sdk[key], "known audited SDK11 source differs")
        products["target/"+key] = data
    out.mkdir()
    for name,data in inputs.items():write(out/"inputs",name,data)
    for name,data in products.items():write(out/"parent-products",name,data)
    write(out,"parent-receipt.json",parent_raw);write(out,"cleanup-receipt.json",cleanup_raw)
    frozen = load("D_exact_clock_frozen",out/"inputs"/(D+"test_exact_clock_predicate.py"))
    frozen.run_snapshot(out,ROOT,parent,cleanup_parent,inputs,products)


def run_snapshot(out, origin, parent, cleanup_parent, inputs, products):
    mods = {n:load("D_exact_clock_"+n,HERE/(n+".py")) for n in (
        "source","build","test_startup","storage","publication","process_owner",
        "syscall_arity","valid_input","search_compact","reduce","packaging",
        "compressed_bootstrap","closed_tu_cleanup","test_frontend_compact")}
    clock = helper()
    source,builder,startup = mods["source"],mods["build"],mods["test_startup"]
    lexical = load("D_exact_clock_lexical",ROOT/"engines/scripts/rename_c.py")
    minifier = load("D_exact_clock_minify",ROOT/"engines/scripts/minify.py")
    packer = load("D_exact_clock_packer",source.CANONICAL/"packer.py")
    reader = load("D_exact_clock_reader",ROOT/READER)
    hostmod = load("D_exact_clock_owner",ROOT/source.HOST)
    require(pin(inputs[source.HOST])["sha256"] == source.HOST_SHA, "original command owner differs")
    report = dict(kind="D-exact-clock-native-package-frontend-v1",complete=False,frozen_execution=True,
        parent_receipt=pin((out/"parent-receipt.json").read_bytes()),
        cleanup_receipt=pin((out/"cleanup-receipt.json").read_bytes()),
        inputs={n:pin(d) for n,d in inputs.items()},commands=[],cases=[],frontend_semantics=[],
        source_reproduced=False,semantic_qualified=False,full_typed_admission=False,
        rules_qualified=False,runtime_qualified=False,engine_executed=False,selected=False,
        target11_runtime_qualified=False,old_native_map_changed=False,
        production_packaging_changed=False,profile="test-p4",
        scope="two exact clock cases, same full chess/search/learners; finite compile/package and isolated frontend only")
    save = lambda:(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    host = None;save()
    def run(command, *, cwd, kind, data=None):
        result = host.run(command,cwd=cwd,kind=kind,data=data)
        startup.require_execution(report["commands"][-1],0)
        return result
    try:
        import resource
        observed_cpu = resource.getrlimit(resource.RLIMIT_CPU)
        effective_cpu = bounded_cpu_limits(300,330,*observed_cpu,infinity=resource.RLIM_INFINITY)
        child_cpu = child_cpu_limit(*effective_cpu,infinity=resource.RLIM_INFINITY)
        report["parent_CPU_limits"] = dict(requested=[300,330],observed=list(observed_cpu),effective=list(effective_cpu),
            child_requested=40,child_effective=child_cpu,
            policy="cap inherited parent pair and child limit; never reset accumulated CPU")
        hostmod.LIMITS = {**hostmod.LIMITS,"aggregate_wall":600,"per_command_wall":60,
            "parent_CPU":effective_cpu[0],"parent_CPU_hard":effective_cpu[1],"child_CPU":child_cpu,"tool_output_bytes":4<<20}
        host = hostmod.Host(out,report,save)
        sdk = cleanup_parent["SDK11"]
        report["compiler"] = run(["cc","--version"],cwd=out,kind="GCC13-version").decode().splitlines()[0]
        report["SDK11"] = {**sdk,"version":run([sdk["compiler"],"--version"],cwd=out,kind="SDK11-version").decode().splitlines()[0],
            "scope":"audited Jammy11.4 SDK on Noble; compile-only, not target runtime"}
        profile = source.production().resource_profile("test-p4")
        require(profile.to_record(16) == parent["resource"], "parent actual resource differs")
        base, proof = startup.prepared(source,profile,True,mods["storage"],"prefix")
        require(startup.json_equal(proof,parent["production_proof"]), "complete prepared source proof differs")
        base, proof = mods["process_owner"].transform(base,mods["publication"])
        require(clock.same(proof,parent["owner_proof"]), "complete owner proof differs")
        base, proof = mods["syscall_arity"].transform(base,mods["process_owner"],mods["publication"],proof,
            noinline_wake=True,immediate_exit=True)
        require(clock.same(proof,parent["arity_proof"]), "complete arity proof differs")
        base, proof = mods["valid_input"].transform(base,mods["syscall_arity"],mods["process_owner"],mods["publication"],proof)
        require(clock.same(proof,parent["valid_proof"]), "complete valid-input proof differs")
        base, proof = mods["search_compact"].transform(base,mods["valid_input"],mods["syscall_arity"],
            mods["process_owner"],mods["publication"],proof,options=("previous-piece","unsigned-history"))
        selected = next(v for v in parent["variants"] if v["name"] == SELECTOR)
        require(clock.same(proof,selected["proof"]) and all(base[n] == products[SELECTOR+"/generated-readable/"+n] for n in READABLE),
                "full structural six-file projection differs")
        original_full = {n:products[SELECTOR+"/shipping-inputs/"+n] for n in FILES}
        control, cleanup_proof = mods["closed_tu_cleanup"].transform(original_full)
        require(clock.same(cleanup_proof,cleanup_parent["cleanup_proof"])
            and all(control[n] == products["cleanup/"+n] for n in FILES), "complete old cleanup source/proof differs")
        candidate_readable, candidate, clock_proof = clock.transform(base,control)
        require(clock.restore(candidate_readable,candidate,json.loads(json.dumps(clock_proof))) == (base,control),
                "new six-file/compiler-input full inverse differs")
        report.update(production_proof=parent["production_proof"],structural_proof=proof,
            cleanup_proof=cleanup_proof,clock_proof=clock_proof,resource=profile.to_record(16))
        flags, units = builder.native_flags(profile), ["main.c","start.S"]
        require(flags == selected["flags"] == cleanup_parent["compiler_flags"]
                and units == selected["units"] == cleanup_parent["units"], "exact compiler flags/units differ")
        report.update(compiler_flags=flags,units=units)
        stages = selected["reduction"]["stages"]
        require(len(stages) == 2 and stages[0]["kind"] == "unused-scalar-typedefs" and stages[0]["status"] == "accepted"
                and stages[1]["kind"] == "batch-alpha" and stages[1]["status"] == "rejected-native-differs",
                "frozen accepted typedef-only spelling path differs")
        for name, readable, shipping in (("control",base,control),("exact-clock",candidate_readable,candidate)):
            directory = out/name
            for n,d in readable.items():write(directory/"generated-readable",n,d)
            for n,d in shipping.items():write(directory/"shipping-inputs",n,d)
            raw = directory/"generated-readable"
            cpp = run(["cc","-E","-P",*flags,"-I",str(raw),"-x","c","-"],cwd=raw,kind=name+"-fresh-preprocess",
                data=b''.join(('#include "'+n+'"\n').encode() for n in source.UNITS if n.endswith('.c')))
            entry = run(["cc","-E","-P","-x","assembler-with-cpp",str(raw/"start.S")],cwd=raw,kind=name+"-fresh-entry")
            mapped = rename(minifier.compact_source(cpp,"c"),selected["legacy_renames"],lexical)
            pruned, rounds = mods["reduce"].prune_typedefs({"main.c":mapped},lexical)
            require([r["main.c"]["removed"] for r in rounds] == [r["main.c"]["removed"] for r in stages[0]["rounds"]],
                    "exact old unused typedef prefix changed")
            full = {"main.c":pruned["main.c"],"start.S":entry,"image.ld":readable["image.ld"]}
            if name == "control":
                require(full == original_full and rounds == stages[0]["rounds"], "fresh actual control preprocessing differs")
                fresh_cleaned, bridge = mods["closed_tu_cleanup"].transform(full)
            else:
                fresh_cleaned, bridge = compiler_cleanup(full,original_full,mods["closed_tu_cleanup"],clock)
            require(fresh_cleaned == shipping, "fresh generated source does not reach exact shipping class")
            row = dict(name=name,source={n:pin(d) for n,d in readable.items()},shipping={n:pin(d) for n,d in shipping.items()},
                fresh_cpp=pin(cpp),fresh_entry=pin(entry),typedef_rounds=rounds,cleanup_bridge=bridge,
                native=[],SDK11=[],packages=[])
            for compiler,label,bucket in (("cc","GCC13",row["native"]),(sdk["compiler"],"SDK11",row["SDK11"])):
                observations = []
                for index in range(2):
                    attempt = directory/(label+"-"+str(index));attempt.mkdir()
                    run([compiler,*flags,*[str(directory/"shipping-inputs"/n) for n in units],
                         "-Wl,-T,"+str(directory/"shipping-inputs/image.ld"),"-o",str(attempt/"linked")],
                        cwd=attempt,kind=name+"-"+label+"-native-"+str(index))
                    linked = (attempt/"linked").read_bytes();native = packer.strip_native(linked)
                    write(attempt,"native",native)
                    geometry = dict(linked=builder.kernel_geometry(packer,linked,profile.workers),
                                    native=builder.kernel_geometry(packer,native,profile.workers))
                    identity = dict(linked=pin(linked),stripped=pin(native));observations.append((linked,native))
                    bucket.append(dict(**identity,geometry=geometry,command=report["commands"][-1]))
                require(observations[0] == observations[1], "two fresh same-class native images differ")
                if name == "control":
                    old = cleanup_parent["cases"][1]["native_rebuilds" if label == "GCC13" else "SDK11"][0]
                    require({k:bucket[0][k] for k in ("linked","stripped")} == {k:old[k] for k in ("linked","stripped")},
                            "fresh unchanged control native differs")
            native = (directory/"GCC13-0/native").read_bytes()
            for route in ("source-jit","source-jit-compressed","packed-xz-bcj"):
                repetitions = []
                for index in range(2):
                    if route == "source-jit":whole, detail = mods["packaging"].package_source(shipping,flags,units)
                    elif route == "source-jit-compressed":whole, detail = mods["compressed_bootstrap"].package_source(shipping,flags,units,mods["packaging"])
                    else:whole, detail = mods["packaging"].package_native(native,"xz-bcj")
                    decoder = lzma.LZMADecompressor();decoded = decoder.decompress(whole[detail["header_bytes"]:])
                    require(decoder.eof and not decoder.unused_data, "whole payload is incomplete or has trailing data")
                    if route == "packed-xz-bcj":require(decoded == native, "entire kernel native inverse differs")
                    else:
                        bundle = json.loads(decoded) if route == "source-jit" else ast.literal_eval(ast.parse(decoded).body[1].value)
                        require(bundle == dict(files={n:d.decode() for n,d in sorted(shipping.items())},flags=flags,units=units),
                                "entire actual source bundle inverse differs")
                    write(directory,route+"-"+str(index),whole)
                    repetitions.append(dict(whole=pin(whole),package=detail))
                require(repetitions[0] == repetitions[1], "two complete whole packages differ")
                if name == "control":
                    old = next(p for p in cleanup_parent["cases"][1]["packages"] if p["route"] == route)
                    require(repetitions[0]["whole"] == old["whole"], "fresh unchanged control whole differs")
                row["packages"].append(dict(route=route,**repetitions[0],reproduced=True,actual_whole_inverse=True))
            report["cases"].append(row);save()
        report["source_reproduced"] = True
        a,b = report["cases"]
        report["whole_savings"] = {x["route"]:x["whole"]["bytes"]-y["whole"]["bytes"] for x,y in zip(a["packages"],b["packages"])}
        report["any_whole_improvement"] = any(v > 0 for v in report["whole_savings"].values())
        save()
        if report["any_whole_improvement"]:
            reference = None
            original_driver = mods["test_frontend_compact"].FRONTEND_DRIVER
            now_old = b"uint64_t now(void){long t[2];if(Dsc2(228,(long)(1),(long)(t)))abort();return (uint64_t)t[0]*1000+(uint64_t)t[1]/1000000;}"
            for name,readable,is_candidate in (("control",base,False),("exact-clock",candidate_readable,True)):
                fixture_files = dict(readable)
                fixture_files["runtime.c"], now_proof = source.project(readable["runtime.c"],[(
                    "fixture-only-constant-monotonic-clock",now_old,b"uint64_t now(void){return UINT64_C(1000000);}")])
                driver, fixture_proof = render_frontend(original_driver,clock,candidate=is_candidate)
                for mode,extra in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
                    directory = out/name/("frontend-"+mode)
                    for n,d in fixture_files.items():write(directory,n,d)
                    write(directory,"driver.c",driver);binary = directory/"x"
                    run(["cc","-std=c11","-O2","-g0","-fno-builtin","-ffunction-sections","-fdata-sections",
                         "-Wl,--gc-sections","-msse4.2","-mcx16","-DDEV=0","-DD_HQ=0","-DWORKERS=4","-DTT_BITS=12",
                         "-DFRONTEND_CSTRING=0",*extra,str(directory/"driver.c"),"-o",str(binary)],
                        cwd=directory,kind=name+"-frontend-compile-"+mode)
                    output = run([str(binary)],cwd=directory,kind=name+"-frontend-run-"+mode)
                    lines = output.splitlines()
                    require(lines and lines[0].startswith(b"ABI ")
                        and lines[-1] == b"TOTAL commands=23 positions=18 promotions=16 clock_cases=64"
                        and b"CLOCKKEY cases=21532 guard=none-after-span lengths=0..6 bytes=0..255" in lines
                        and b"EXTRAGO cases=32 exact-key/deadline/publication/fallback" in lines,
                        "actual generated frontend/key/clock controls incomplete")
                    normalized_output = b"\n".join(lines[1:])+b"\n"
                    if reference is None:reference = normalized_output
                    require(normalized_output == reference, "actual frontend state/key/deadline/publication observations differ")
                    report["frontend_semantics"].append(dict(name=name,mode=mode,fixture=fixture_proof,
                        original_readable=clock.inventory(readable),constant_clock=now_proof,
                        output=pin(output),normalized=pin(normalized_output),binary=pin(binary.read_bytes()),equal=True));save()
            report["semantic_qualified"] = True
        else:
            report["semantic_not_run_reason"] = "all three complete routes tied or lost; finite two-case portfolio stopped"
        report["source_current_after"] = {n:pin(normalized(reader.read_regular(origin/n,limit=4<<20)))
                                          for n in inputs if n.startswith("engines/")}
        require(report["source_current_after"] == {n:pin(d) for n,d in inputs.items() if n.startswith("engines/")},
                "current/frozen source changed during experiment")
        for path,key in ((sdk["compiler"],"wrapper"),(sdk["audit_path"],"audit")):
            require(pin(reader.read_regular(Path(path),limit=1<<20)) == sdk[key], "audited SDK11 wrapper/audit changed")
        for command in report["commands"]:startup.require_execution(command,0)
        report["complete"] = True
    except BaseException as error:
        report["complete"] = False
        report["failure"] = dict(type=type(error).__name__,message=str(error));raise
    finally:
        try:
            if host is not None:host.close()
        except BaseException as error:
            report["complete"] = False
            report["cleanup_failure"] = dict(type=type(error).__name__,message=str(error));raise
        finally:
            if report.get("host_cleanup",{}).get("unsettled_commands") or report.get("host_cleanup",{}).get("errors"):
                report["complete"] = False
            save()
    print(json.dumps(dict(complete=report["complete"],cases=len(report["cases"]),whole_savings=report["whole_savings"],
        semantic_qualified=report["semantic_qualified"],engine_executed=False)),flush=True)


if __name__ == "__main__":
    main()
