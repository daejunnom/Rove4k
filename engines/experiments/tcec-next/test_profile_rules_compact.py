"""Compact-stage rules evidence, ordering and frozen-helper boundaries."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("test_rules_compact", HERE / "profile_rules.py")
RULES = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = RULES
spec.loader.exec_module(RULES)


class CompactRulesBoundaries(unittest.TestCase):
    def test_e_compact_follows_model_ep_and_dependency(self):
        profile = SimpleNamespace(id="test-p4")
        desc = RULES.FINAL_COMPACT["E"]
        resource = {"schema": "test-resource", "entry_cleanup": "private-path"}
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        model = {"stage": "canonical-e19-physical-binding", "source_model_id": "e19-admitted-source-baseline",
                 "table_value_offset": 0, "before": "r", "after": "R"}
        spelling = {"schema": RULES.COMPOUND_SCHEMA, "variant": RULES.COMPOUND_VARIANT}
        ep = {"schema": RULES.EP_SCHEMA}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        compact = {"schema": desc["schema"], "variant": desc["variant"], "family": "E",
                   "profile_id": profile.id, "full_inverse": True}
        stages = [resource, phase, model, spelling, ep, dependency, compact]
        def make_stage(before, after, proof, **attrs):
            return SimpleNamespace(SCHEMA=proof["schema"],
                transform_source=lambda actual, **kwargs: (after, proof) if actual == before else self.fail("stage input differs"),
                restore_source=lambda actual, supplied, **kwargs: before if (actual, supplied) == (after, proof)
                else self.fail("stage inverse differs"), **attrs)
        projection = make_stage(b"base", b"r0", resource)
        phase_module = make_stage(b"r0", b"resource", phase, VARIANTS=("phase-init",))
        model_owner = SimpleNamespace(model_id="canonical",
            bind_physical_table=lambda actual, **kwargs: (b"Resource", model))
        model_module = SimpleNamespace(Model=SimpleNamespace(load=lambda path: model_owner,
            from_physical_source=lambda actual, **kwargs: object()))
        compound = make_stage(b"Resource", b"spelling", spelling, VARIANT=RULES.COMPOUND_VARIANT)
        ep_module = make_stage(b"spelling", b"ep", ep)
        ep_helpers = {name: object() for name in ("ep", "projection", "dependencies", "edits")}
        dep_module = make_stage(b"ep", b"dependency", dependency)
        dep_module.validate_receipt = lambda *args, **kwargs: b"ep" if kwargs.get("final_compact") is True else self.fail("missing gate")
        compact_helper = make_stage(b"dependency", b"final", compact)
        modules = {"production_rules_projection": projection, "production_rules_phase_projection": phase_module,
                   "production_rules_E19_model": model_module, "production_rules_dependencies": dep_module}
        record = {"attempts": [{"directory": name, "source_proofs": stages} for name in ("first", "repeat")]}
        with patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
             patch.object(RULES, "compound_modules", return_value=(object(), compound)), \
             patch.object(RULES, "ep_modules", return_value=(ep_module, ep_helpers)), \
             patch.object(RULES, "compact_module", return_value=compact_helper), \
             patch.object(RULES, "_source_build_record", return_value=record) as source_record:
            self.assertEqual(RULES.admit_source(b"final", b"base", stages, "E", profile, build=Path("/named")), stages)
            self.assertEqual(source_record.call_args.kwargs["post_compact"],
                             {"path": desc["path"], "variant": desc["variant"]})
            with self.assertRaises(ValueError):
                RULES.admit_source(b"final", b"base", [resource, phase, model, spelling, dependency, compact],
                                   "E", profile, build=Path("/named"))

    def test_a_b_and_c_final_compact_follow_dependency(self):
        for family in ("A", "B", "C"):
            with self.subTest(family=family):
                profile = SimpleNamespace(id="test-p4")
                desc = RULES.FINAL_COMPACT[family]
                base, resource_body, post_body = b"base", b"resource", b"post"
                spelling_body, scan_body, ep_body, dependency_body, final = b"spelling", b"scan", b"ep", b"dependency", b"final"
                resource = {"schema": "test-resource", "entry_cleanup": "private-path"}
                post = {"schema": "rove4k.portable-phase-source.v1" if family in "AC" else
                        "rove4k.profile-b-source.v1", "variant": "phase-init" if family in "AC" else "tcec-final-lf"}
                spelling = {"schema": RULES.COMPOUND_SCHEMA if family in "AC" else RULES.SPELLING_SCHEMA,
                            "variant": RULES.COMPOUND_VARIANT if family in "AC" else RULES.BEST_SPELLING[family]}
                scan = {"schema": RULES.SCAN_SCHEMA, "variant": "square-successor"}
                ep = {"schema": RULES.EP_SCHEMA}
                dependency = {"schema": "rove4k.profile-dependencies.v1"}
                compact = {"schema": desc["schema"], "variant": desc["variant"], "family": family,
                           "profile_id": profile.id, "full_inverse": True}
                stages = [resource, post, spelling, *([scan] if family in "AC" else []),
                          *([ep] if family == "C" else []), dependency, compact]
                def make_stage(before, after, proof, **attrs):
                    return SimpleNamespace(SCHEMA=proof["schema"],
                        transform_source=lambda actual, **kwargs: (after, proof) if actual == before else self.fail("stage input differs"),
                        restore_source=lambda actual, supplied, **kwargs: before if (actual, supplied) == (after, proof)
                        else self.fail("stage inverse differs"), **attrs)
                projection = make_stage(base, resource_body, resource)
                post_module = make_stage(resource_body, post_body, post, VARIANTS=(post["variant"],))
                spelling_module = make_stage(post_body, spelling_body, spelling)
                if family in "AC":
                    spelling_module.VARIANT = RULES.COMPOUND_VARIANT
                scan_module = make_stage(spelling_body, scan_body, scan)
                ep_module = make_stage(scan_body, ep_body, ep)
                ep_helpers = {name: object() for name in ("ep", "projection", "dependencies", "edits")}
                before_dependency = ep_body if family == "C" else scan_body if family == "A" else spelling_body
                dependency_module = make_stage(before_dependency, dependency_body, dependency)
                dependency_module.validate_receipt = lambda *args, **kwargs: before_dependency if (
                    kwargs.get("final_compact") is True and args[3] == dependency_body) else self.fail("compact gate absent")
                compact_module = make_stage(dependency_body, final, compact)
                modules = {"production_rules_projection": projection,
                           "production_rules_phase_projection" if family in "AC" else "production_rules_B_projection": post_module,
                           "production_rules_spelling_projection": spelling_module,
                           "production_rules_dependencies": dependency_module}
                record = {"attempts": [{"directory": name, "source_proofs": stages} for name in ("first", "repeat")]}
                with patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
                     patch.object(RULES, "compound_modules", return_value=(object(), spelling_module)), \
                     patch.object(RULES, "scan_module", return_value=scan_module), \
                     patch.object(RULES, "ep_modules", return_value=(ep_module, ep_helpers)), \
                     patch.object(RULES, "compact_module", return_value=compact_module), \
                     patch.object(RULES, "_source_build_record", return_value=record) as source_record:
                    self.assertEqual(RULES.admit_source(final, base, stages, family, profile, build=Path("/named")), stages)
                    self.assertEqual(source_record.call_args.kwargs["post_compact"],
                                     {"path": desc["path"], "variant": desc["variant"]})
                    with self.assertRaises(ValueError):
                        RULES.admit_source(final, base, stages[:-2] + [compact, dependency], family, profile,
                                           build=Path("/named"))

    def test_f_compact_chain_replays_and_inverts_in_order(self):
        profile = SimpleNamespace(id="test-p4")
        descriptor = RULES.FINAL_COMPACT["F"]
        base, resource_source, phase_source = b"baseline", b"resource", b"phase"
        spelling_source, dependency_source, final = b"spell", b"dependency", b"compact"
        resource = {"schema": "test-resource", "entry_cleanup": "private-path"}
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        spelling = {"schema": RULES.F_COMPOUND_SCHEMA, "variant": RULES.F_COMPOUND_VARIANT}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        compact = {"schema": descriptor["schema"], "family": "F", "profile_id": profile.id,
                   "variant": descriptor["variant"], "full_inverse": True}
        stages = [resource, phase, spelling, dependency, compact]
        calls = []

        def stage(name, source, result, proof, *, schema=None, **attrs):
            def forward(actual, **kwargs):
                self.assertEqual(actual, source)
                calls.append(name + ":forward")
                return result, proof
            def restore(actual, supplied, **kwargs):
                self.assertEqual((actual, supplied), (result, proof))
                calls.append(name + ":inverse")
                return source
            return SimpleNamespace(SCHEMA=schema or proof["schema"], transform_source=forward,
                                   restore_source=restore, **attrs)

        projection = stage("resource", base, resource_source, resource)
        phase_module = stage("phase", resource_source, phase_source, phase, VARIANTS=("phase-init",))
        compound = stage("spelling", phase_source, spelling_source, spelling,
                         schema=RULES.COMPOUND_SCHEMA, F_SCHEMA=RULES.F_COMPOUND_SCHEMA)
        dependency_module = stage("dependency", spelling_source, dependency_source, dependency)
        def validate_receipt(*args, **kwargs):
            self.assertIs(kwargs.get("final_compact"), True)
            self.assertEqual(args[3], dependency_source)
            return spelling_source
        dependency_module.validate_receipt = validate_receipt
        compact_helper = stage("compact", dependency_source, final, compact)
        individual = object()
        modules = {"production_rules_projection": projection, "production_rules_phase_projection": phase_module,
                   "production_rules_dependencies": dependency_module}
        record = {"attempts": [{"directory": name, "source_proofs": stages} for name in ("first", "repeat")]}
        with patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
             patch.object(RULES, "compound_modules", return_value=(individual, compound)), \
             patch.object(RULES, "compact_module", return_value=compact_helper), \
             patch.object(RULES, "_source_build_record", return_value=record) as source_record:
            self.assertEqual(RULES.admit_source(final, base, stages, "F", profile, build=Path("/named")), stages)
            self.assertEqual(source_record.call_args.kwargs["post_compact"], {
                "path": descriptor["path"], "variant": descriptor["variant"]})
            self.assertEqual([name for name in calls if name.endswith(":inverse")][-5:],
                             ["compact:inverse", "dependency:inverse", "spelling:inverse", "phase:inverse", "resource:inverse"])
            bad_typed = [*stages[:-1], {**compact, "full_inverse": 1}]
            with self.assertRaisesRegex(ValueError, "canonical proof"):
                RULES.admit_source(final, base, bad_typed, "F", profile, build=Path("/named"))
            for invalid in ([resource, phase, spelling, compact, dependency],
                            [resource, phase, spelling, compact],
                            [*stages, compact],
                            [*stages[:-1], {**compact, "variant": "names-null-loops"}],
                            [*stages[:-1], {**compact, "family": "A"}]):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    RULES.admit_source(final, base, invalid, "F", profile, build=Path("/named"))

    def test_frozen_helpers_and_source_closure_are_required(self):
        for family, descriptor in RULES.FINAL_COMPACT.items():
            with self.subTest(family=family), tempfile.TemporaryDirectory(prefix="rove-rules-compact-") as temporary:
                root = Path(temporary)
                relative = descriptor["path"]
                frozen = root / "inputs" / relative
                frozen.parent.mkdir(parents=True)
                data = RULES.normalized(RULES.ROOT / relative)
                self.assertEqual(RULES.pin(data), descriptor["pin"])
                frozen.write_bytes(data)
                self.assertEqual(RULES.compact_module(root, descriptor).SCHEMA, descriptor["schema"])
                frozen.write_bytes(data + b"\n")
                with self.assertRaisesRegex(ValueError, "helper consumed bytes"):
                    RULES.compact_module(root, descriptor)

    def test_manifest_cannot_hide_or_swap_compact_helper(self):
        descriptor = RULES.FINAL_COMPACT["F"]
        declaration = {"path": descriptor["path"], "variant": descriptor["variant"]}
        with tempfile.TemporaryDirectory(prefix="rove-rules-compact-record-") as temporary:
            root = Path(temporary)
            relative = descriptor["path"]
            frozen = root / "inputs" / relative
            frozen.parent.mkdir(parents=True)
            data = RULES.normalized(RULES.ROOT / relative)
            frozen.write_bytes(data)
            (root / "control").mkdir()
            (root / "control/main.c").write_bytes(b"base")
            (root / "main.c").write_bytes(b"final")
            row = {"path": relative, "role": "tool", **RULES.pin(data)}
            record = {"format": 1, "class": "rove4k-production-profile-v1", "family": "F", "entry": "F",
                      "complete": True, "reproducible": True, "post_compact": declaration,
                      "source_proofs": [], "inputs": {relative: RULES.pin(data)},
                      "source_closure": {"inputs": [row]},
                      "plan": {"family": "F", "full": True, "representation": "source-jit", "entry_cleanup": "private-path"}}
            path = root / "build.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            kwargs = dict(family="F", stages=[], post_profile=None, main_source=b"final", baseline_source=b"base",
                          tools=(relative,), post_compact=declaration)
            RULES._source_build_record(root, **kwargs)
            for change in (lambda row: row.pop("post_compact"),
                           lambda row: row["source_closure"].update(inputs=[]),
                           lambda row: row["inputs"][relative].update(sha256="0" * 64),
                           lambda row: row["plan"].update(full=False)):
                bad = json.loads(json.dumps(record))
                change(bad)
                path.write_text(json.dumps(bad), encoding="utf-8")
                with self.assertRaises(ValueError):
                    RULES._source_build_record(root, **kwargs)
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identity differs"):
                RULES._source_build_record(root, **{**kwargs, "post_compact": None})


if __name__ == "__main__":
    unittest.main()
