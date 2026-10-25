"""Pure admission, diagnostic-domain and startup-owner tests; no engine runs."""
import copy
import importlib.util
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


if __name__ == "__main__":unittest.main()
