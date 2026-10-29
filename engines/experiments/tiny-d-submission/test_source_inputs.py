"""Frozen D source-generation regression checks; no engines or qualifiers run."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


INPUTS = load("D_snapshot_input_contract", HERE / "source_inputs.py")
SOURCE = load("D_snapshot_live_source", HERE / "source.py")


def write_snapshot(root, contents):
    for name, data in contents.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


class DSourceInputs(unittest.TestCase):
    def test_actual_asm_and_clang_frozen_source_preparation(self):
        profile = SOURCE.production().resource_profile("test-p4")
        original, original_proof = SOURCE.prepare(profile)
        for consumer in ("asm_jit", "test_clang_kernel"):
            with self.subTest(consumer=consumer), tempfile.TemporaryDirectory() as directory:
                reader = load("D_snapshot_reader_" + consumer, HERE / (consumer + ".py"))
                contents = reader.snapshot_inputs()
                root = Path(directory)
                write_snapshot(root, contents)
                source = load("D_snapshot_source_" + consumer, root / (INPUTS.D + "source.py"))
                prepared, proof = source.prepare(profile)
                self.assertEqual((prepared, proof), (original, original_proof))
                raw = contents[INPUTS.ENTRY + "native/board.c"]
                self.assertIn(b"rove-common/", raw)
                self.assertNotIn(b"rove-common/", prepared["board.c"])
                self.assertEqual(proof["input_sources"][INPUTS.ENTRY + "native/board.c"], SOURCE.pin(raw))
                recipe = json.loads(contents[INPUTS.RECIPE])
                self.assertEqual(proof["composition"]["assembled_board"]["sha256"],
                                 recipe["assembled_source_sha256"]["native/board.c"])
                self.assertTrue(set(recipe["shared_source_sha256"]) <= contents.keys())
                self.assertIn(INPUTS.COMPOSER, contents)
                self.assertIn(INPUTS.SELF, contents)
                storage = load("D_snapshot_storage_" + consumer, root / (INPUTS.D + "storage.py"))
                if consumer == "asm_jit":
                    files, _ = storage.transform(prepared, prefix=True, dense=False)
                    directives = load("D_snapshot_directives", root / (INPUTS.D + "directives.py"))
                    self.assertEqual({name: SOURCE.pin(data)["sha256"] for name, data in files.items()},
                                     directives.PREPARED)
                else:
                    modules = {name: load("D_snapshot_clang_" + name, root / (INPUTS.D + name + ".py"))
                               for name in ("clang_kernel", "test_startup", "process_owner", "publication", "syscall_arity")}
                    files, receipt = modules["clang_kernel"].prepared(source, storage, modules["test_startup"],
                        modules["process_owner"], modules["publication"], modules["syscall_arity"], profile)
                    self.assertNotIn(b"rove-common/", files["board.c"])
                    self.assertFalse(receipt["runtime_qualified"])
                    self.assertFalse(receipt["selected"])

    def test_frozen_composition_bytes_and_assembled_digest_still_gate(self):
        reader = load("D_snapshot_bad_reader", HERE / "asm_jit.py")
        contents = reader.snapshot_inputs()
        recipe = json.loads(contents[INPUTS.RECIPE])
        shared = next(iter(recipe["shared_source_sha256"]))
        mutations = (
            (shared, None, ValueError, "shared source must be a regular file"),
            (shared, contents[shared] + b"\n", ValueError, "shared source input differs"),
            (INPUTS.COMPOSER, contents[INPUTS.COMPOSER] + b"\n", ValueError, "composition helper differs"),
            (INPUTS.RECIPE, json.dumps({**recipe, "assembled_source_sha256": {"native/board.c": "0" * 64}}).encode(),
             ValueError, "assembled canonical source differs"),
        )
        for name, data, error, message in mutations:
            with self.subTest(name=name, message=message), tempfile.TemporaryDirectory() as directory:
                damaged = dict(contents)
                if data is None:
                    del damaged[name]
                else:
                    damaged[name] = data
                root = Path(directory)
                write_snapshot(root, damaged)
                source = load("D_snapshot_rejected_source", root / (INPUTS.D + "source.py"))
                with self.assertRaisesRegex(error, message):
                    source.prepare(source.production().resource_profile("test-p4"))

    def test_recipe_closure_matches_control_and_remains_exact_for_owner(self):
        recipe = json.loads((ROOT / INPUTS.RECIPE).read_bytes())
        producer = INPUTS.producer_names(recipe)
        startup = load("D_snapshot_startup_inputs", HERE / "test_startup.py")
        self.assertEqual(set(producer), set(startup.PRODUCER_INPUTS + startup.composition_inputs() + (startup.STORAGE_INPUT,)))
        admission = load("D_snapshot_owner_inputs", HERE / "owner_admission.py")
        names = {"selection/build.json", *producer, *admission.EXTRA}
        names.update("selection/generated-readable/" + name for name in INPUTS.NATIVE)
        names.update("selection/shipping-inputs/" + name for name in ("main.c", "start.S", "image.ld"))
        record = dict(kind=admission.EXPERIMENT_KIND, complete=True, frozen_execution=True,
            ownership_class="D-final-wait-own-exit-group-v1", inputs={name: {} for name in names},
            **{key: False for key in ("baseline_wired", "old_native_R_guard_used", "real_target_allocation",
                "locality_proof", "strength_claim", "per_worker_search_work_proof", "runtime_qualified",
                "whole_artifact_qualified", "selected")})
        self.assertEqual(set(admission.input_names(record, producer)), names)
        for missing in (INPUTS.COMPOSER, *recipe["shared_source_sha256"], INPUTS.SELF):
            damaged = deepcopy(record)
            del damaged["inputs"][missing]
            with self.assertRaisesRegex(ValueError, "exact named input closure differs"):
                admission.input_names(damaged, producer)
        for field, old, new in (
            ("shared_source_sha256", next(iter(recipe["shared_source_sha256"])), "archive/engines/common/board.c"),
            ("helper_sha256", INPUTS.COMPOSER, "engines/scripts/other.py"),
        ):
            damaged = deepcopy(recipe)
            damaged[field][new] = damaged[field].pop(old)
            with self.assertRaises(ValueError):
                INPUTS.producer_names(damaged)


if __name__ == "__main__":
    unittest.main()
