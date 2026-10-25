"""Pure full-resource P28 geometry, trace-domain and startup deadline tests."""
import copy
import importlib.util
from pathlib import Path
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


if __name__ == "__main__":unittest.main()
