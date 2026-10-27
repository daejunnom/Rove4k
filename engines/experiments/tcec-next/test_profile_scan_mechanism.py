"""Pure scan mechanism route, fixed helper and diagnostic-domain checks."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("scan_mechanism_tests", HERE / "check_profile_scan.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def selected(family="A", profile="test-p4", *, ep=False):
    workers, bits = adapter.PROFILES[profile]
    resources = dict(id=profile, workers=workers, tt_bits=bits, tt_entries=1 << bits,
        tt_bytes=(1 << bits) * 24, tt_entry_bytes=24, tt_mask=(1 << bits) - 1)
    proofs = [dict(schema=name) for name in adapter.STAGES]
    proofs[0].update(family=family, resources=resources, target_type_assertions=["_Static_assert(sizeof(size_t)==8,\"64bit\");"])
    for proof, variant in zip(proofs[1:4], ("phase-init", "clock-atomic-launcher", "square-successor")):
        proof.update(family=family, profile_id=profile, variant=variant)
    rows = [dict(input_begin=at, before="rv_spawn", after="rv", role="private-launcher-name") for at in (10, 20, 30)]
    parent = dict(bytes=100, sha256="fixture-parent")
    component = dict(schema="rove4k.selected-spelling-experiment.v1", variant="launcher-short",
        family=family, profile_id=profile, input=parent, edits=rows)
    proofs[2].update(helper=dict(path=adapter.SPELLING, **adapter.FIXED_INPUTS[adapter.SPELLING]),
        components=["clock-type", "atomic-assignment", "launcher-short"], input=parent,
        individual=[dict(variant="launcher-short", proof=component)],
        edits=[dict(**row, component="launcher-short") for row in rows])
    record = {"class":"rove4k-production-profile-v1", "family":family, "entry":family,
        "post_profile":{"path":adapter.PHASE,"variant":"phase-init"},
        "post_spelling":dict(adapter.COMPOUND_DECLARATION), "post_scan":dict(adapter.SCAN_DECLARATION),
        "source_dependencies":dict(adapter.DEPENDENCIES), "resources":resources,
        "source_proofs":proofs, "inputs":{adapter.SCAN:dict(adapter.FIXED_INPUTS[adapter.SCAN])},
        "plan":{"representation":"source-jit","entry_cleanup":"private-path"}}
    if ep:
        record["post_ep"] = {"path":"engines/experiments/tcec-next/profile_ep.py", "variant":"legal-maker"}
        proofs.insert(4, dict(schema="rove4k.profile-ep-source.v1", family=family,
                              profile_id=profile, variant="legal-maker"))
    return record


class ScanMechanism(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lifecycle = adapter.load("scan_tests_lifecycle", adapter.ROOT / adapter.LIFECYCLE)
        cls.phase_check = adapter.load("scan_tests_phase_check", adapter.ROOT / adapter.PHASE_CHECK)
        cls.phase = adapter.load("scan_tests_phase", adapter.ROOT / adapter.PHASE)
        cls.p28 = adapter.load("scan_tests_p28", adapter.ROOT / adapter.P28)

    def test_only_ac_p4_p28_exact_selected_route(self):
        for family in "AC":
            for profile in adapter.PROFILES:
                self.assertEqual(adapter.bound_selection(selected(family, profile)), profile)
        good = selected()
        for key,value in (("family","B"),("entry","C"),("post_scan",None),
            ("post_spelling",None),("source_dependencies",None),
            ("post_profile",{"path":adapter.PHASE,"variant":"phase"}),
            ("plan",{"representation":"packed-native","entry_cleanup":"private-path"})):
            record=copy.deepcopy(good);record[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):adapter.bound_selection(record)

    def test_missing_duplicate_foreign_or_reordered_stage_rejected(self):
        good=selected();cases=[]
        record=copy.deepcopy(good);record["source_proofs"].pop(3);cases.append(record)
        record=copy.deepcopy(good);record["source_proofs"].insert(3,record["source_proofs"][3]);cases.append(record)
        record=copy.deepcopy(good);record["source_proofs"][3]["schema"]="foreign";cases.append(record)
        record=copy.deepcopy(good);record["source_proofs"][2:4]=record["source_proofs"][2:4][::-1];cases.append(record)
        for record in cases:
            with self.assertRaisesRegex(ValueError,"in order"):adapter.bound_selection(record)

    def test_C_EP_requires_exact_optional_declaration_and_ordered_proof(self):
        for profile in adapter.PROFILES:
            self.assertEqual(adapter.bound_selection(selected("C", profile, ep=True)), profile)
        mutations = (
            lambda row: row.update(post_ep=None),
            lambda row: row["post_ep"].update(path="foreign.py"),
            lambda row: row["post_ep"].update(variant="control"),
            lambda row: row["post_ep"].update(extra=True),
            lambda row: row["source_proofs"].pop(4),
            lambda row: row["source_proofs"].insert(4, copy.deepcopy(row["source_proofs"][4])),
            lambda row: row["source_proofs"][4].update(schema="foreign"),
            lambda row: row["source_proofs"][4].update(family="A"),
            lambda row: row["source_proofs"][4].update(profile_id="test-p28"),
            lambda row: row["source_proofs"][4].update(variant="foreign"),
            lambda row: row["source_proofs"].__setitem__(slice(3, 5), row["source_proofs"][3:5][::-1]),
            lambda row: row["source_proofs"].__setitem__(slice(4, 6), row["source_proofs"][4:6][::-1]),
        )
        for mutate in mutations:
            record = selected("C", ep=True)
            mutate(record)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                adapter.bound_selection(record)
        for record in (selected("A", ep=True), selected("E", ep=True)):
            with self.assertRaises(ValueError):
                adapter.bound_selection(record)
        declared_without_proof = selected("C")
        declared_without_proof["post_ep"] = {"path":"engines/experiments/tcec-next/profile_ep.py", "variant":"legal-maker"}
        with self.assertRaises(ValueError):
            adapter.bound_selection(declared_without_proof)

    def test_C_EP_fixture_forwards_supplied_final_source_to_existing_renderers(self):
        # These mocks test the source/owner join, not C semantics or admission.
        source = b"supplied-final-EP-source"
        prefix, alias = b"existing-diagnostic-prefix", {"fixture":"existing-launcher-alias"}
        context = {"fixture":"C-context"}
        observation = {"fixture":"existing-observation"}
        for profile in adapter.PROFILES:
            record = selected("C", profile, ep=True)
            lifecycle = SimpleNamespace(diagnostic_alias=Mock(return_value=(prefix, alias)))
            phase_check = SimpleNamespace(scaled_fixture=Mock(return_value=(b"p4-fixture", observation)))
            phase = SimpleNamespace(CONTEXT={"C":context})
            p28 = SimpleNamespace(full_callback_fixture=Mock(
                return_value=(b"p28-fixture", observation, {"trace":True}, {"geometry":True})))
            prepared = adapter.prepare_fixture(source, record, lifecycle, phase_check, phase, p28)
            if profile == "test-p4":
                lifecycle.diagnostic_alias.assert_called_once_with(source, record["source_proofs"][2])
                phase_check.scaled_fixture.assert_called_once_with(prefix, record["source_proofs"][0], context)
                p28.full_callback_fixture.assert_not_called()
                self.assertEqual((prepared["fixture"], prepared["prefix"], prepared["alias"]),
                                 (b"p4-fixture", prefix, alias))
            else:
                p28.full_callback_fixture.assert_called_once_with(source, "C", record["source_proofs"][0])
                lifecycle.diagnostic_alias.assert_not_called()
                phase_check.scaled_fixture.assert_not_called()
                self.assertEqual(prepared["fixture"], b"p28-fixture")
            self.assertEqual(prepared["observation"], observation)

    def test_wrong_stage_family_profile_or_variant_rejected(self):
        for stage,key,value in ((0,"family","C"),(1,"family","C"),(2,"profile_id","test-p28"),
            (3,"family","C"),(3,"profile_id","tcec-provisional"),(3,"variant","foreign")):
            record=selected();record["source_proofs"][stage][key]=value
            with self.subTest(stage=stage,key=key),self.assertRaisesRegex(ValueError,"family/profile/variant"):
                adapter.bound_selection(record)

    def test_resources_are_typed_and_never_relabelled_or_scaled(self):
        for profile in adapter.PROFILES:
            for key,value in (("id","tcec-provisional"),("workers",28 if profile=="test-p4" else 4),
                ("tt_entries",28*1024),("tt_bytes",64*1024),("tt_bits",24 if profile=="test-p4" else 22),
                ("tt_entry_bytes",16),("workers",float(adapter.PROFILES[profile][0])),("tt_mask",True)):
                record=selected(profile=profile);record["resources"][key]=value
                with self.subTest(profile=profile,key=key),self.assertRaises(ValueError):adapter.bound_selection(record)

    def test_scan_declaration_and_production_helper_pin_are_exact(self):
        for mutate in (lambda x:x["post_scan"].update(variant="other"),
            lambda x:x["post_scan"].update(path="foreign.py"),
            lambda x:x["inputs"][adapter.SCAN].update(sha256="changed"),
            lambda x:x["inputs"][adapter.SCAN].update(bytes=float(adapter.FIXED_INPUTS[adapter.SCAN]["bytes"])),
            lambda x:x["inputs"].pop(adapter.SCAN)):
            record=selected();mutate(record)
            with self.assertRaises(ValueError):adapter.bound_selection(record)

    def test_fixed_reviewed_helpers_match_current_bytes_and_mutation_fails(self):
        observed={name:adapter.normalized(adapter.ROOT/name) for name in adapter.FIXED_INPUTS}
        adapter.checked_support(observed)
        for name in adapter.FIXED_INPUTS:
            changed=dict(observed);changed[name]+=b"changed"
            with self.subTest(name=name),self.assertRaises(ValueError):adapter.checked_support(changed)

    def test_p4_reuses_frozen_renderers_and_compound_index_before_scan(self):
        source=b"#define RVW 4\n#define RVN ((size_t)1<<22)\nvoid rv(void){}void x(void){rv();rv();}\n"
        record=selected()
        prepared=adapter.prepare_fixture(source,record,self.lifecycle,self.phase_check,self.phase,self.p28)
        prefix,alias=self.lifecycle.diagnostic_alias(source,record["source_proofs"][2])
        expected=self.phase_check.scaled_fixture(prefix,record["source_proofs"][0],self.phase.CONTEXT["A"])
        self.assertEqual((prepared["fixture"],prepared["observation"]),expected)
        self.assertEqual(prepared["prefix"],source+b"\n#define rv_spawn rv\n")
        self.assertEqual(prepared["alias"],alias)
        self.assertIn(b"#define RVW 4\n",prepared["fixture"])
        self.assertIn(b"#define RVN ((size_t)1<<18)\n",prepared["fixture"])
        self.assertEqual(prepared["observation"]["entries"],1<<18)
        self.assertEqual(record["source_proofs"][-2]["schema"],"rove4k.selected-square-scan.v1")

    def test_p28_reuses_full_floor_renderer_without_resource_reduction_or_alias(self):
        for family in "AC":
            c=self.p28.CONTEXT[family]
            source=(f"#define {c['width']} 28\n#define {c['count']} ((size_t)1<<24)\n#define {c['unit']} 512\n"
                +"void*worker(void*p){").encode()+self.p28.init_marker(family)+b"}return 0;}\n"
            record=selected(family,"test-p28")
            prepared=adapter.prepare_fixture(source,record,self.lifecycle,self.phase_check,self.phase,self.p28)
            expected=self.p28.full_callback_fixture(source,family,record["source_proofs"][0])
            self.assertEqual((prepared["fixture"],prepared["observation"],prepared["trace"],prepared["geometry"]),expected)
            self.assertEqual(prepared["geometry"]["range_entry_counts"],{"599040":20,"599552":8})
            self.assertEqual(prepared["observation"]["actual_tt_bytes"],384<<20)
            self.assertNotIn("prefix",prepared)
            self.assertNotIn(b"#define rv_spawn",prepared["fixture"])
            self.assertIn(self.p28.FAILURE_DIAGNOSTICS,prepared["fixture"])
            self.assertEqual(self.p28.LINK_FLAGS,("-Wl,--wrap=pthread_create","-Wl,--wrap=pthread_join","-Wl,--wrap=aligned_alloc"))
            self.assertEqual(self.p28.restore_trace(
                self.p28.trace_initialization(source,family)[0],prepared["trace"]),source)


if __name__ == "__main__":unittest.main()
