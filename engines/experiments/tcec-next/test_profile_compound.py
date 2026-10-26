"""Pure admission, diagnostic-domain and startup-owner tests; no engine runs."""
import copy
import importlib.util
import json
from pathlib import Path
import signal
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("compound_mechanism_tests", HERE / "check_profile_compound.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def fixture(family="A"):
    replacement = "J" if family == "F" else "rv"
    rows = [dict(input_begin=at, before="rv_spawn", after=replacement, role="private-launcher-name")
            for at in (10, 20, 30)]
    parent = dict(bytes=100, sha256="fixture-parent")
    component = dict(schema="rove4k.selected-spelling-experiment.v1", variant="launcher-short",
        family=family, profile_id="test-p4", input=parent, edits=rows)
    proof = dict(schema="rove4k.selected-spelling-compound.v1", variant="clock-atomic-launcher",
        family=family, profile_id="test-p4", helper=dict(path=adapter.SPELLING, **adapter.SPELLING_PIN),
        components=["clock-type", "atomic-assignment", "launcher-short"], input=parent,
        individual=[dict(variant="launcher-short", proof=component)],
        edits=[dict(**row, component="launcher-short") for row in rows])
    source = f"void {replacement}(void){{}}void x(void){{{replacement}();{replacement}();}}\n".encode()
    return source, proof


class CompoundMechanism(unittest.TestCase):
    def test_alias_is_after_complete_shipping_body(self):
        for family in "ACEF":
            source, proof = fixture(family)
            prefix, record = adapter.diagnostic_alias(source, proof)
            replacement = "J" if family == "F" else "rv"
            self.assertEqual(prefix, source + f"\n#define rv_spawn {replacement}\n".encode())
            self.assertEqual(record["shipping_source"], adapter.pin(source))
            self.assertEqual(record["diagnostic_prefix"], adapter.pin(prefix))
            self.assertNotIn(b"#define", source)

    def test_wrong_alias_duplicate_component_and_changed_helper_rejected(self):
        source, proof = fixture()
        cases = []
        changed = copy.deepcopy(proof); changed["individual"][0]["proof"]["edits"][0]["after"] = "J"; cases.append(changed)
        changed = copy.deepcopy(proof); changed["individual"].append(changed["individual"][0]); cases.append(changed)
        changed = copy.deepcopy(proof); changed["helper"]["sha256"] = "changed"; cases.append(changed)
        changed = copy.deepcopy(proof); changed["edits"][0]["input_begin"] += 1; cases.append(changed)
        for changed in cases:
            with self.assertRaises(ValueError):adapter.diagnostic_alias(source, changed)

    def test_shipping_launcher_collision_or_unconverted_name_rejected(self):
        source, proof = fixture()
        for changed in (source + b"int rv;\n", source + b"void rv_spawn(void);\n"):
            with self.assertRaises(ValueError):adapter.diagnostic_alias(changed, proof)

    def test_selection_requires_actual_compound_p4_and_dependencies(self):
        record = {"class":"rove4k-production-profile-v1", "family":"A", "entry":"A",
            "resources":{"id":"test-p4"}, "post_profile":{"path":adapter.PHASE,"variant":"phase-init"},
            "post_spelling":dict(adapter.DECLARATION), "source_dependencies":dict(adapter.DEPENDENCIES),
            "plan":{"representation":"source-jit","entry_cleanup":"private-path"}}
        adapter.bound_selection(record)
        for key,value in (("family","B"),("resources",{"id":"test-p28"}),
            ("post_spelling",None),("source_dependencies",None),
            ("plan",{"representation":"packed-native","entry_cleanup":"private-path"})):
            changed=copy.deepcopy(record);changed[key]=value
            with self.assertRaises(ValueError):adapter.bound_selection(changed)

    def test_f_v2_alias_uses_base_metadata_and_final_shipping_source(self):
        source, base = fixture("F")
        base["output"] = dict(bytes=len(source)+4, sha256="different-v1-base")
        proof = dict(schema="rove4k.selected-spelling-compound.v2",
            variant=adapter.F_COMPOUND_DECLARATION["variant"], family="F", profile_id="test-p4",
            input=base["input"], output=adapter.pin(source), base=base)
        prefix, record = adapter.diagnostic_alias(source, proof)
        self.assertEqual(prefix,source+b"\n#define rv_spawn J\n")
        self.assertEqual(record["shipping_source"],adapter.pin(source))
        self.assertNotEqual(record["shipping_source"],base["output"])
        self.assertEqual(record["launcher_component"],base["individual"][0]["proof"])
        for section,key,value in (((),"family","A"),((),"profile_id","test-p28"),
            ((),"output",base["output"]),(("base",),"family","A"),
            (("base",),"profile_id","test-p28"),(("base",),"variant","other")):
            changed=copy.deepcopy(proof);target=changed
            for name in section:target=target[name]
            target[key]=value
            with self.assertRaises(ValueError):adapter.diagnostic_alias(source,changed)

    def test_unique_selected_compound_stage_survives_later_ac_scan_and_cleanup(self):
        for family in "ACF":
            _, base = fixture(family)
            proof = base if family != "F" else dict(schema="rove4k.selected-spelling-compound.v2",
                variant=adapter.F_COMPOUND_DECLARATION["variant"],family="F",profile_id="test-p4",base=base)
            record = dict(post_spelling=dict(adapter.F_COMPOUND_DECLARATION if family == "F" else adapter.DECLARATION),
                source_proofs=[dict(schema="rove4k.c-resource-projection.v1"),
                    dict(schema="rove4k.portable-phase-source.v1"),proof])
            if family in "AC":record["source_proofs"].append(dict(schema="rove4k.selected-square-scan.v1"))
            record["source_proofs"].append(dict(schema="rove4k.profile-dependencies.v1"))
            self.assertIs(adapter.selected_compound_proof(record),proof)
            for stages in ([p for p in record["source_proofs"] if p is not proof],
                           [*record["source_proofs"],copy.deepcopy(proof)]):
                changed=copy.deepcopy(record);changed["source_proofs"]=stages
                with self.assertRaises(ValueError):adapter.selected_compound_proof(changed)
            changed=copy.deepcopy(record);changed["post_spelling"]["variant"]="foreign"
            with self.assertRaises(ValueError):adapter.selected_compound_proof(changed)

    def test_only_f_can_select_compound_v2_mechanism(self):
        record = {"class":"rove4k-production-profile-v1", "family":"F", "entry":"F",
            "resources":{"id":"test-p4"}, "post_profile":{"path":adapter.PHASE,"variant":"phase-init"},
            "post_spelling":dict(adapter.F_COMPOUND_DECLARATION), "source_dependencies":dict(adapter.DEPENDENCIES),
            "plan":{"representation":"source-jit","entry_cleanup":"private-path"}}
        adapter.bound_selection(record)
        for family in "ABCDE":
            changed=copy.deepcopy(record);changed["family"]=changed["entry"]=family
            with self.assertRaises(ValueError):adapter.bound_selection(changed)

    def test_constructor_defers_nonterm_signal_without_changing_child_mask(self):
        handlers = {}
        owned = set()
        def interrupted(sig, frame):raise TimeoutError("saved host interrupt")
        handled = (signal.SIGTERM, signal.SIGINT)
        handlers[signal.SIGINT] = interrupted
        def set_handler(sig, handler):
            previous=handlers[sig];handlers[sig]=handler;return previous
        marker=object()
        def construct(*args):
            owned.add(marker)
            handlers[signal.SIGINT](signal.SIGINT,None)
            return marker
        runtime=SimpleNamespace(Owned=construct,OWNED=owned)
        with patch.object(adapter.signal,"getsignal",side_effect=lambda sig:handlers[sig]), \
                patch.object(adapter.signal,"signal",side_effect=set_handler), \
                patch.object(adapter.signal,"pthread_sigmask",create=True) as mask:
            with self.assertRaisesRegex(TimeoutError,"saved host"):
                adapter.construct_owned(runtime,None,None,None,handled)
            mask.assert_not_called()
        self.assertEqual(owned,{marker})
        self.assertIs(handlers[signal.SIGINT],interrupted)

    def test_outer_drain_cleans_registered_interrupted_construction(self):
        runtime=SimpleNamespace(OWNED=set())
        class Owned:
            def cleanup(self):runtime.OWNED.remove(self);return {"owned_group_absent":True}
        runtime.OWNED.add(Owned())
        report={}
        with patch.object(adapter.signal,"pthread_sigmask",return_value=set(),create=True), \
                patch.object(adapter.signal,"SIG_BLOCK",0,create=True), \
                patch.object(adapter.signal,"SIG_SETMASK",2,create=True):
            adapter.drain_owned(runtime,SimpleNamespace(handled=(signal.SIGTERM,)),report)
        self.assertFalse(runtime.OWNED)
        self.assertEqual(report["runtime_cleanup"],{"remaining_owned":0,
            "drained":[{"owned_group_absent":True}],"errors":[]})

    def test_later_empty_drain_cannot_erase_prior_cleanup_error(self):
        report={"runtime_cleanup":{"remaining_owned":0,"drained":[],"errors":["retained failure"]}}
        with patch.object(adapter.signal,"pthread_sigmask",return_value=set(),create=True), \
                patch.object(adapter.signal,"SIG_BLOCK",0,create=True), \
                patch.object(adapter.signal,"SIG_SETMASK",2,create=True):
            with self.assertRaisesRegex(ValueError,"left owned"):
                adapter.drain_owned(SimpleNamespace(OWNED=set()),SimpleNamespace(handled=()),report)
        self.assertEqual(report["runtime_cleanup"]["errors"],["retained failure"])


compound_spec = importlib.util.spec_from_file_location("compound_source_tests", HERE / "spelling_compound.py")
compound = importlib.util.module_from_spec(compound_spec)
compound_spec.loader.exec_module(compound)


def spelling_fixture():
    """Independent single-edit components let the composition contract be isolated."""
    source = (b"CLOCK U;ATOMIC V;LAUNCH H;for(S q=0;q<128;q=(q+9)&~8){body;}"
              b"for(S j=0;j<128;j=(j+9)&~8){other;}")
    edits = {"clock-type": ("CLOCK", "C"), "atomic-assignment": ("ATOMIC", "A"),
             "launcher-short": ("LAUNCH", "J")}
    def transform(parent, *, family, profile_id, variant):
        before, after = edits[variant]
        at = parent.index(before.encode())
        candidate = parent[:at] + after.encode() + parent[at + len(before):]
        row = dict(input_begin=at, output_begin=at, before=before, after=after, role=variant)
        return candidate, dict(schema="rove4k.selected-spelling-experiment.v1", variant=variant,
            family=family, profile_id=profile_id, input=compound.pin(parent),
            output=compound.pin(candidate), edits=[row])
    def restore(candidate, proof):
        row = proof["edits"][0]
        at, before, after = row["output_begin"], row["before"].encode(), row["after"].encode()
        if compound.pin(candidate) != proof["output"] or candidate[at:at + len(after)] != after:
            raise ValueError("fixture component differs")
        return candidate[:at] + before + candidate[at + len(after):]
    spelling = SimpleNamespace(SCHEMA="rove4k.selected-spelling-experiment.v1",
        INPUTS={(family, profile): (len(source), compound.pin(source)["sha256"])
                for family in "ABCEF" for profile in compound.PROFILES},
        available=lambda family: tuple(edits), transform_source=transform, restore_source=restore)
    return source, spelling


class CompoundSource(unittest.TestCase):
    def setUp(self):
        self.source, self.spelling = spelling_fixture()
        self.base = (b"C U;A V;J H;for(S q=0;q<128;q=(q+9)&~8){body;}"
                     b"for(S j=0;j<128;j=(j+9)&~8){other;}")
        self.candidate = (b"C U;A V;J H;for(S q=0;q<128;q=q+9&~8){body;}"
                          b"for(S j=0;j<128;j=j+9&~8){other;}")
        def tuples(data):return {p: (len(data), compound.pin(data)["sha256"]) for p in compound.PROFILES}
        self.bases = patch.object(compound, "F_BASES", tuples(self.base))
        self.outputs = patch.object(compound, "F_OUTPUTS", tuples(self.candidate))
        self.bases.start();self.outputs.start()
        self.addCleanup(self.bases.stop);self.addCleanup(self.outputs.stop)

    def transform(self, profile="test-p4", variant=None, family="F"):
        return compound.transform_source(self.source, family=family, profile_id=profile,
            spelling=self.spelling, **({} if variant is None else {"variant":variant}))

    def test_v1_default_explicit_variant_and_inverse_remain_equal(self):
        for family in "ABCEF":
            for profile in compound.PROFILES:
                default, proof = self.transform(profile, family=family)
                self.assertEqual((default, proof), self.transform(profile, compound.VARIANT, family))
                self.assertEqual(proof["schema"], compound.SCHEMA)
                self.assertNotIn("base", proof)
                self.assertEqual(compound.restore_source(default, proof, spelling=self.spelling), self.source)
        self.assertEqual(self.transform()[0], self.base)

    def test_f_v2_is_ordered_v1_then_exact_two_parentheses_and_full_inverse(self):
        for profile in compound.PROFILES:
            candidate, proof = self.transform(profile, compound.F_VARIANT)
            self.assertEqual(candidate, self.candidate)
            self.assertEqual(proof["base"], self.transform(profile)[1])
            self.assertEqual(proof["schema"], compound.F_SCHEMA)
            self.assertEqual(len(proof["edits"]), 2)
            self.assertEqual(len(proof["protected_gaps"]), 3)
            self.assertEqual(proof["input"], compound.pin(self.source))
            self.assertEqual(proof["base"]["output"], compound.pin(self.base))
            self.assertEqual(compound.restore_source(candidate, json.loads(json.dumps(proof)),
                spelling=self.spelling), self.source)
            self.assertFalse(proof["resources_changed"] or proof["features_removed"] or proof["production_selected"])

    def test_v2_rejects_non_f_unknown_variant_and_profile(self):
        for family in "ABCDE":
            with self.assertRaisesRegex(ValueError,"F-only"):
                self.transform(variant=compound.F_VARIANT, family=family)
        with self.assertRaisesRegex(ValueError,"named compound"):
            self.transform(variant="unknown")
        with self.assertRaisesRegex(ValueError,"F-only"):
            self.transform("unknown", compound.F_VARIANT)

    def test_v2_exact_base_and_final_policy_are_both_required(self):
        for field in ("F_BASES", "F_OUTPUTS"):
            changed = dict(getattr(compound,field));changed["test-p4"]=(1,"wrong")
            with patch.object(compound,field,changed), self.assertRaisesRegex(ValueError,"exact finite F"):
                self.transform(variant=compound.F_VARIANT)
        self.assertEqual(self.transform()[0],self.base)

    def test_v2_rejects_modified_outer_base_proofs_gaps_and_resources(self):
        candidate, proof = self.transform(variant=compound.F_VARIANT)
        cases = []
        for section in ((),("base",)):
            for key,value in (("family","A"),("profile_id","test-p28"),
                ("resources_changed",True),("features_removed",True),("production_selected",True)):
                changed=copy.deepcopy(proof);target=changed
                for name in section:target=target[name]
                target[key]=value;cases.append(changed)
            changed=copy.deepcopy(proof);target=changed
            for name in section:target=target[name]
            target["protected_gaps"][0]["sha256"]="wrong";cases.append(changed)
            changed=copy.deepcopy(proof);target=changed
            for name in section:target=target[name]
            target["edits"][0]["output_begin"]+=1;cases.append(changed)
        changed=copy.deepcopy(proof);changed["base"]["schema"]=compound.F_SCHEMA;cases.append(changed)
        changed=copy.deepcopy(proof);changed["full_inverse"]=1;cases.append(changed)
        changed=copy.deepcopy(proof);changed["base"]["full_inverse"]=1;cases.append(changed)
        changed=copy.deepcopy(proof);changed["base"]["new_candidate_count"]=True;cases.append(changed)
        changed=copy.deepcopy(proof);changed["output"]["bytes"]=float(len(candidate));cases.append(changed)
        for changed in cases:
            with self.assertRaises(ValueError):compound.restore_source(candidate,changed,spelling=self.spelling)
        with self.assertRaises(ValueError):compound.restore_source(candidate+b"!",proof,spelling=self.spelling)

    def test_v1_proof_cannot_be_relabelled_v2(self):
        base, proof = self.transform()
        proof["schema"]=compound.F_SCHEMA;proof["variant"]=compound.F_VARIANT
        with self.assertRaises(ValueError):compound.restore_source(base,proof,spelling=self.spelling)


if __name__ == "__main__":unittest.main()
