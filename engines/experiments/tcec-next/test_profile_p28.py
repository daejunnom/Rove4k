"""Pure full-resource P28 geometry, trace-domain and startup deadline tests."""
import copy
import argparse
import importlib.util
import json
from pathlib import Path
import re
import signal
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p28_mechanism_tests", HERE / "check_profile_p28.py")
p28 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p28)


def resources():
    return dict(id="test-p28", workers=28, tt_bits=24, tt_entries=1 << 24,
        tt_bytes=(1 << 24) * 24, tt_entry_bytes=24, tt_mask=(1 << 24) - 1)


def source_fixture(family):
    c = p28.CONTEXT[family]
    headers = (f"#define {c['width']} 28\n#define {c['count']} ((size_t)1<<24)\n#define {c['unit']} 512\n").encode()
    body = f"{c['table']}[i].{c['key']}={c['table']}[i].{c['data']}=0;atomic_flag_clear_explicit(&{c['table']}[i].{c['lock']},memory_order_relaxed);".encode()
    return headers + b"void*callback(void*p){" + p28.init_marker(family) + body + b"}return 0;}\n"


def selected(family):
    return {"class":"rove4k-production-profile-v1", "family":family, "entry":family,
        "post_spelling":dict(p28.BEST_B if family == "B" else p28.COMPOUND),
        "post_profile":{"path":p28.NEXT + ("profile_b.py" if family == "B" else "profile_phase.py"),
                        "variant":"tcec-final-lf" if family == "B" else "phase-init"},
        "source_dependencies":dict(p28.DEPENDENCIES), "resources":resources(),
        "plan":{"representation":"source-jit", "entry_cleanup":"private-path"}}


class P28Mechanism(unittest.TestCase):
    def test_reviewed_lifecycle_pin_matches_bytes_and_mutation_stops_before_admission(self):
        names=(p28.SELF,p28.VERIFIER,p28.LIFECYCLE,p28.OWNER,p28.RUNTIME)
        observed={str(p28.ROOT/name):p28.normalized(p28.ROOT/name) for name in names}
        self.assertEqual(p28.pin(observed[str(p28.ROOT/p28.LIFECYCLE)]),p28.LIFECYCLE_PIN)
        changed=dict(observed);changed[str(p28.ROOT/p28.LIFECYCLE)]+=b"changed"
        with patch.object(p28,"normalized",side_effect=lambda path:changed[str(path)]), \
                patch.object(p28,"load",side_effect=AssertionError("admission must not start")):
            with self.assertRaisesRegex(ValueError,"reviewed lifecycle"):
                p28.run_bound(Path("/never-read-p28-build"),Path("/never-created-p28-output"))

    def test_actual_unequal_floor_geometry_and_independent_owner_oracle(self):
        geo = p28.geometry(resources())
        self.assertEqual(geo["tt_bytes"],402653184)
        self.assertEqual(geo["range_entry_counts"],{"599040":20,"599552":8})
        self.assertEqual(geo["page_unit_bytes"],12288)
        counts=[0]*28
        for unit in range(32768):
            owner=((unit+1)*28-1)//32768
            counts[owner]+=1
            row=geo["ranges"][owner]
            self.assertLessEqual(row["begin"],unit*512)
            self.assertLess(unit*512,row["end"])
        self.assertEqual([i for i,n in enumerate(counts) if n==1171],[3,6,10,13,17,20,24,27])
        self.assertEqual(geo["ranges"][-1]["end"],1<<24)

    def test_p4_scaled_non_power_and_wrong_entry_geometry_rejected(self):
        for key,value in (("id","test-p4"),("workers",4),("tt_bits",22),
            ("tt_entries",28*1024),("tt_entry_bytes",16),("tt_bytes",64*1024)):
            record=resources();record[key]=value
            with self.assertRaises(ValueError):p28.geometry(record)

    def test_only_named_full_p28_selections(self):
        for family in "ABCEF":p28.bound_selection(selected(family))
        record=selected("F");record["post_spelling"]=dict(p28.F_COMPOUND_DECLARATION)
        p28.bound_selection(record)
        for family in "ABCDE":
            record=selected(family);record["post_spelling"]=dict(p28.F_COMPOUND_DECLARATION)
            with self.assertRaises(ValueError):p28.bound_selection(record)
        record=selected("B");record["spelling_request"]={"requested":"compound","effective":"best","duplicate_best":True,"new_candidate_count":0}
        p28.bound_selection(record)  # The exact optional record is separately authenticated by R.
        for family in "ACEF":
            record=selected(family);record["post_spelling"]={"path":p28.NEXT+"profile_spelling.py","selection":"best","variant":"clock-type"}
            with self.assertRaises(ValueError):p28.bound_selection(record)
        for key,value in (("post_spelling",None),("source_dependencies",None),
            ("plan",{"representation":"packed-native","entry_cleanup":"private-path"})):
            record=selected("B");record[key]=value
            with self.assertRaises(ValueError):p28.bound_selection(record)

    def test_one_diagnostic_insertion_preserves_every_original_byte(self):
        for family in "ABCEF":
            source=source_fixture(family)
            traced,proof=p28.trace_initialization(source,family)
            self.assertEqual(p28.restore_trace(traced,proof),source)
            at=proof["offset"]
            self.assertEqual(traced[:at],source[:at])
            self.assertEqual(traced[at+len(proof["inserted"]):],source[at:])
            self.assertIn(b"i>=",proof["inserted"].encode())
            self.assertFalse(proof["bounds_and_stores_changed"])
            self.assertFalse(proof["resource_constants_changed"])

    def test_duplicate_marker_scaling_and_tampered_trace_rejected(self):
        source=source_fixture("B")
        for changed in (source+source,source.replace(b"#define qW 28",b"#define qW 4"),
            source.replace(b"#define qN ((size_t)1<<24)",b"#define qN ((size_t)28672)")):
            with self.assertRaises(ValueError):p28.trace_initialization(changed,"B")
        traced,proof=p28.trace_initialization(source,"B")
        changed=copy.deepcopy(proof);changed["protected_suffix"]["sha256"]="different"
        with self.assertRaises(ValueError):p28.restore_trace(traced,changed)
        with self.assertRaises(ValueError):p28.restore_trace(traced+b"changed",proof)

    def test_full_fixture_keeps_constants_and_separates_padding_and_search(self):
        for family in "ABCEF":
            source=source_fixture(family)
            fixture,observation,proof,geo=p28.full_callback_fixture(source,family,
                {"resources":resources(),"target_type_assertions":["_Static_assert(sizeof(size_t)==8,\"64-bit\");"]})
            self.assertTrue(fixture.startswith(p28.DIAGNOSTIC_PREAMBLE))
            self.assertIn(source[:proof["offset"]],fixture)
            self.assertEqual(observation["actual_workers"],28)
            self.assertEqual(observation["actual_tt_bytes"],384*1024*1024)
            self.assertIn(b"atomic_flag_test_and_set_explicit",fixture)
            self.assertIn(b"for(size_t n=0;n<",fixture)
            self.assertNotIn(b"go wtime",fixture)
            self.assertEqual(geo["page_units"],32768)

    def test_actual_main_barrier_is_original_source_without_any_alias(self):
        for family in "ABCEF":
            source=source_fixture(family)
            rendered=p28.blocked_main(source,family,Path("/tmp/release"),Path("/tmp/arrived"))
            self.assertTrue(rendered.startswith(source))
            self.assertNotIn(b"#define rv_spawn",rendered)
            self.assertNotIn(b"#define RVW qW",rendered)
            self.assertIn((p28.CONTEXT[family]["width"]+"-1").encode(),rendered[len(source):])

    def test_startup_uses_remaining_single_deadline_without_ten_second_helper(self):
        calls=[]
        def until(predicate,budget,seconds):
            self.assertTrue(predicate(b"uciok\n"));calls.append(seconds)
        runtime=SimpleNamespace(stdout=SimpleNamespace(until=until),budget=object())
        with patch.object(p28.time,"monotonic",return_value=10):p28.wait_startup_line(runtime,b"uciok",65)
        self.assertEqual(calls,[55])
        with patch.object(p28.time,"monotonic",return_value=66):
            with self.assertRaises(ValueError):p28.wait_startup_line(runtime,b"uciok",65)


FAULT_CASES=("allocation","create","create-slot","create-bounds","held-slot","join")


def fault_source(case):
    """Actual shared wrappers with deterministic real-call stubs; no TT/thread."""
    prefix=b'''#define _POSIX_C_SOURCE 200809L
#include<stdio.h>
#include<stdlib.h>
#include<stdint.h>
#include<stdatomic.h>
#include<pthread.h>
#include<errno.h>
#define RVW 28
typedef struct{size_t id;}M;
static int qh;
static void*A(void*p){return p;}
void*__real_aligned_alloc(size_t alignment,size_t size){(void)alignment;(void)size;errno=ENOMEM;return 0;}
int __real_pthread_join(pthread_t thread,void**result){(void)thread;(void)result;errno=EDOM;return EINVAL;}
int __real_pthread_create(pthread_t*t,const pthread_attr_t*a,void*(*fn)(void*),void*p){(void)t;(void)a;(void)fn;(void)p;errno=EIO;return EAGAIN;}
'''
    if case=="held-slot":
        prefix+=p28.blocked_main(b"","A",Path("/fixed/release"),Path("/fixed/arrived"))
    else:prefix+=p28.FAILURE_DIAGNOSTICS+p28.callback_launcher("A")
    bodies={
        "allocation":"errno=0;void*p=__wrap_aligned_alloc(4096,402653184);if(p||errno!=ENOMEM)return 77;return 2;",
        "create":"M worker={0};pthread_t thread;errno=0;int rc=__wrap_pthread_create(&thread,0,A,&worker);if(rc!=EAGAIN||errno!=EIO||atomic_load(rv28_claimed))return 77;return 2;",
        "create-slot":"M worker={0};pthread_t thread;atomic_store(rv28_claimed,1);errno=EDOM;int rc=__wrap_pthread_create(&thread,0,A,&worker);if(rc!=22||errno!=EDOM)return 77;return 2;",
        "create-bounds":"M worker={RVW};pthread_t thread;errno=EIO;int rc=__wrap_pthread_create(&thread,0,A,&worker);if(rc!=21||errno!=EIO)return 77;return 2;",
        "held-slot":"M worker={RVW-1};pthread_t thread;atomic_store(&rv28_held_claimed,1);errno=EDOM;int rc=__wrap_pthread_create(&thread,0,A,&worker);if(rc!=25||errno!=EDOM)return 77;return 2;",
        "join":"errno=0;int rc=__wrap_pthread_join((pthread_t)0,0);if(rc!=EINVAL||errno!=EDOM)return 77;return 2;"}
    return prefix+("int main(void){"+bodies[case]+"}\n").encode()


def c_faults(out):
    p28.require(sys.platform=="linux" and out.is_absolute() and not out.exists()
        and p28.ROOT not in (out,*out.parents) and not any((parent/".git").exists() for parent in (out,*out.parents)),
        "new absolute external Linux fault output required")
    owner=p28.load("p28_fault_owned_host",p28.ROOT/p28.OWNER);out.mkdir()
    report=dict(complete=False,commands=[],cases=[],engine_executed=False,TT_allocated=False,
        source=p28.pin(Path(__file__).read_bytes().replace(b"\r\n",b"\n")),renderer=p28.pin(p28.normalized(p28.HERE/"check_profile_p28.py")))
    def save():(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    owner.LIMITS.update(aggregate_wall=120,per_command_wall=20,parent_AS=4<<30,child_AS=2<<30,
        parent_CPU=60,parent_CPU_hard=90,child_CPU=10)
    previous=signal.signal(signal.SIGCHLD,signal.SIG_DFL);host=owner.Host(out,report,save)
    try:
        expected={"allocation":("aligned_alloc",0,12),"create":("pthread_create",11,5),
                  "create-slot":("create-slot",22,33),"create-bounds":("create-precondition",21,5),
                  "held-slot":("held-slot",25,33),"join":("pthread_join",22,33)}
        p28.require(tuple(expected)==FAULT_CASES,"explicit six diagnostic fault cases required")
        for case,(stage,code,error) in expected.items():
            directory=out/case;directory.mkdir();source=fault_source(case);(directory/"fault.c").write_bytes(source)
            host.run(["cc","-std=c11","-Os","-x","c","-","-o","x"],cwd=directory,kind=case+"-compile",data=source)
            try:host.run([directory/"x"],cwd=directory,kind=case+"-fault")
            except ValueError:
                row=report["commands"][-1]
                p28.require(row.get("returncode")==2 and row.get("forced_cleanup") is False
                    and all(row.get(k) is True for k in ("terminal","reaped","owned_group_absent")),"original fault return2/ownership changed")
            else:raise ValueError("injected failure relabelled as native success")
            stderr=Path(row["stderr"]["path"]).read_bytes();text=stderr.decode()
            p28.require(Path(row["stdout"]["path"]).read_bytes()==b"" and len(stderr)<50000
                and p28.pin(stderr)=={k:row["stderr"][k] for k in ("bytes","sha256")},"raw fault streams differ")
            p28.require(text.splitlines()[0].startswith(f"RV28_FAILURE stage={stage} rc={code} errno={error} ")
                and "RV28_LIMIT name=AS available=1 soft=2147483648 hard=2147483648" in text
                and "RV28_LIMIT name=STACK available=" in text and "RV28_LIMIT name=NPROC available=" in text,
                "fault rc/errno/limits not preserved")
            files=re.findall(rb"RV28_FILE path=([^ ]+) available=([01]) errno=([0-9]+)",stderr)
            p28.require([r[0].decode() for r in files]==["/proc/self/status","/proc/self/limits","/proc/self/cgroup",
                "/sys/fs/cgroup/pids.current","/sys/fs/cgroup/pids.max"],"fault read outside fixed kernel counter list")
            report["cases"].append(dict(case=case,source=p28.pin(source),native=p28.pin((directory/"x").read_bytes()),
                original_returncode=2,expected_failure_observed=True,stderr=row["stderr"],stdout=row["stdout"],
                errno_preserved=True,returned_error_preserved=True,kernel_files=[dict(path=p.decode(),available=a==b"1",errno=int(e)) for p,a,e in files]))
            save()
        report["complete"]=True
    finally:host.close();save();signal.signal(signal.SIGCHLD,previous)
    print(json.dumps(dict(complete=True,cases=len(expected),native_returncodes=[2]*len(expected),host_cleanup=report["host_cleanup"])))


class P28FailureObservability(unittest.TestCase):
    def test_shared_renderers_preserve_prefix_and_cover_each_return2_source(self):
        self.assertEqual(p28.LINK_FLAGS,("-Wl,--wrap=pthread_create","-Wl,--wrap=pthread_join","-Wl,--wrap=aligned_alloc"))
        for family in "ABCEF":
            source=source_fixture(family)
            fixture,_,trace,_=p28.full_callback_fixture(source,family,{"resources":resources(),"target_type_assertions":["_Static_assert(sizeof(void*)==8,\"ptr\");"]})
            self.assertEqual(p28.restore_trace(p28.trace_initialization(source,family)[0],trace),source)
            self.assertEqual(fixture.count(p28.FAILURE_DIAGNOSTICS),1)
            self.assertIn(p28.callback_launcher(family),fixture)
            blocked=p28.blocked_main(source,family,Path("/fixed/release"),Path("/fixed/arrived"))
            self.assertTrue(blocked.startswith(source));self.assertEqual(blocked.count(p28.FAILURE_DIAGNOSTICS),1)
            for stage in (b'"aligned_alloc"',b'"pthread_create"',b'"pthread_join"'):
                self.assertIn(stage,fixture);self.assertIn(stage,blocked)
        self.assertIn(b"errno=saved_errno;",p28.FAILURE_DIAGNOSTICS);self.assertIn(b"total<8192",p28.FAILURE_DIAGNOSTICS)

    def test_fault_sources_use_shared_callback_and_do_not_allocate_TT(self):
        for case in FAULT_CASES:
            source=fault_source(case);self.assertIn(p28.FAILURE_DIAGNOSTICS,source)
            wrapper=(p28.blocked_main(b"","A",Path("/fixed/release"),Path("/fixed/arrived"))
                     if case=="held-slot" else p28.callback_launcher("A"))
            self.assertIn(wrapper,source);self.assertIn(b"return 2;",source)
            self.assertNotIn(b"N=aligned_alloc",source)

    def test_diagnostic_slots_keep_default_attributes_and_real_failure_rollback(self):
        for family in "ABCEF":
            callback=p28.callback_launcher(family)
            held=p28.blocked_main(b"",family,Path("/fixed/release"),Path("/fixed/arrived"))
            for text in (callback,held):
                self.assertNotIn(b"malloc(",text);self.assertNotIn(b"free(",text)
                self.assertNotIn(b"pthread_attr_set",text)
            self.assertIn(b"__real_pthread_create(t,a,rv28_observe,v)",callback)
            self.assertLess(callback.index(b"n>="),callback.index(b"rv28_slots+n"))
            self.assertIn(b'"create-slot",22,errno',callback)
            self.assertIn(b"atomic_store_explicit(rv28_claimed+n,0,memory_order_release)",callback)
            self.assertIn(b"__real_pthread_create(t,a,rv28_wait,&rv28_held_slot)",held)
            self.assertIn(b'"held-slot",25,errno',held)
            self.assertIn(b"atomic_store_explicit(&rv28_held_claimed,0,memory_order_release)",held)


if __name__=="__main__":
    if "--c-faults" in sys.argv:
        parser=argparse.ArgumentParser();parser.add_argument("--c-faults",action="store_true");parser.add_argument("--out",type=Path,required=True)
        args=parser.parse_args();c_faults(args.out)
    else:unittest.main()
