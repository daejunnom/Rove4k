"""Pure D full-P28 mechanism contracts; no compiler, engine or TT allocation."""
from copy import deepcopy
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


CHECK = load("D_P28_pure_checker", HERE / "check_profile_p28.py")
SOURCE = load("D_P28_pure_source", HERE / "source.py")
PROFILE = SOURCE.production().resource_profile("test-p28")
STARTUP = load("D_P28_pure_startup", HERE / "test_startup.py")
STORAGE = load("D_P28_pure_storage", HERE / "storage.py")
INPUTS = load("D_P28_pure_names", HERE / "source_inputs.py")


def manifest():
    return dict(format="rove4k-D-general-source-v1", family="D", storage="prefix", source_reduced=False,
        equivalent_edits=True, complete=True, frozen_execution=True, native_reproduced=True,
        resource=PROFILE.to_record(16))


def terminal(kind="compile-full-entry-positive", code=0):
    return dict(kind=kind, returncode=code, started=True, terminal=True, reaped=True,
        owned_group_absent=True, original_identity_retained_until_other_members_absent=True,
        forced_cleanup=False, other_group_members_before_reap=[])


class CounterClock:
    def __init__(self, now=100):
        self.now = now

    def __call__(self):
        return self.now


class FakeReader:
    def __init__(self, data=b""):
        self.data = data
        self.done, self.error = True, None
        self.thread = types.SimpleNamespace(join=lambda timeout: None, is_alive=lambda: False)
        self.calls = []

    def bytes(self):
        return self.data

    def until(self, predicate, budget, seconds=10):
        self.calls.append(seconds)
        if not predicate(self.data):
            raise ValueError("missing test output")


class P28Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files, cls.proof = STARTUP.prepared(SOURCE, PROFILE, True, STORAGE, "prefix")

    def test_actual_floor_partition_has_all_pages_and_remainder(self):
        result = CHECK.bound_selection(manifest())
        self.assertEqual(result["tt_bytes"], 512 << 20)
        self.assertEqual(result["pages"], 131072)
        self.assertEqual(result["page_counts"], {"4681": 24, "4682": 4})
        self.assertEqual([r["worker"] for r in result["ranges"] if
            (r["end"] - r["begin"]) // 256 == 4682], [6, 13, 20, 27])
        self.assertEqual(sum(r["end"] - r["begin"] for r in result["ranges"]), 1 << 25)
        self.assertTrue(all(a["end"] == b["begin"] for a, b in zip(result["ranges"], result["ranges"][1:])))

    def test_profile_guard_rejects_each_different_class_and_numeric_type(self):
        for key, value in (("format", "rove4k.D-search-source.v1"), ("family", "A"), ("storage", "none"),
                ("source_reduced", True), ("equivalent_edits", False), ("complete", 1),
                ("frozen_execution", False), ("native_reproduced", False)):
            bad = manifest()
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                CHECK.bound_selection(bad)
        for key in ("workers", "tt_bits", "tt_entries", "tt_bytes", "tt_entry_bytes", "tt_mask"):
            for value in (float(manifest()["resource"][key]), True, manifest()["resource"][key] + 1):
                bad = manifest()
                bad["resource"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    CHECK.bound_selection(bad)

    def test_actual_source_binding_requires_all_units_exact_full_proof(self):
        data = manifest()
        data["proof"] = self.proof
        self.assertEqual(CHECK.source_binding(self.files, self.proof, data, dict(self.files)),
                         {n: CHECK.pin(d) for n, d in sorted(self.files.items())})
        for changed in (dict(self.files, **{"runtime.c": self.files["runtime.c"] + b"\n"}),
                        {n: d for n, d in self.files.items() if n != "start.S"}):
            with self.assertRaises(ValueError):
                CHECK.source_binding(changed, self.proof, data, self.files)
        bad = deepcopy(data)
        bad["proof"]["source_edits"]["runtime.c"]["gaps"][0]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            CHECK.source_binding(self.files, self.proof, bad, self.files)

    def test_full_poison_preserves_actual_bounds_and_all_nonruntime_units(self):
        result, proof = CHECK.poison_fixture(self.files, SOURCE)
        self.assertEqual(SOURCE.restore(result["runtime.c"], proof["runtime"]), self.files["runtime.c"])
        self.assertEqual({n:d for n,d in result.items() if n != "runtime.c"},
                         {n:d for n,d in self.files.items() if n != "runtime.c"})
        for text in (b"size_t begin=pages*(unsigned)w->id/WORKERS*256;",
                     b"size_t end=pages*((unsigned)w->id+1)/WORKERS*256;",
                     b"memset(table+begin,0,(end-begin)*sizeof *table);",
                     b"if(table[e].key||table[e].data)", b"((p+1)*WORKERS-1)"):
            self.assertIn(text, result["runtime.c"])
        self.assertEqual(result["runtime.c"].count(b"memset(table,165,"), 1)
        self.assertFalse(proof["production_floor_bounds_changed"])
        self.assertFalse(proof["production_clear_changed"])

    def test_fault_controls_remove_only_the_named_production_effect(self):
        positive, _ = CHECK.poison_fixture(self.files, SOURCE)
        omitted, omit_proof = CHECK.poison_fixture(self.files, SOURCE, negative="omit-clear")
        owner, owner_proof = CHECK.poison_fixture(self.files, SOURCE, negative="omit-page-owner")
        clear = b"memset(table+begin,0,(end-begin)*sizeof *table);"
        self.assertNotIn(clear, omitted["runtime.c"])
        self.assertIn(clear, owner["runtime.c"])
        self.assertIn(b"p<end/256;p++)if(p)if(atomic_exchange_explicit", owner["runtime.c"])
        self.assertNotIn(b"p<end/256;p++)if(p)", positive["runtime.c"])
        for files, proof in ((omitted, omit_proof), (owner, owner_proof)):
            self.assertEqual(SOURCE.restore(files["runtime.c"], proof["runtime"]), self.files["runtime.c"])
        self.assertTrue(omit_proof["production_clear_changed"])
        self.assertFalse(owner_proof["production_clear_changed"])
        with self.assertRaises(ValueError):
            CHECK.poison_fixture(self.files, SOURCE, negative="unknown")
        wrong = dict(self.files, **{"runtime.c": self.files["runtime.c"].replace(clear, b"not-the-clear")})
        with self.assertRaises(ValueError):
            CHECK.poison_fixture(wrong, SOURCE)

    def test_wrapper_is_distinct_syscall_tu_and_preserves_spawn_arguments(self):
        with tempfile.TemporaryDirectory() as root:
            paths = {name: Path(root).resolve() / name for name in ("arrived", "release", "joined", "exit_release")}
            extra = CHECK.startup_wrapper(paths)
            self.assertIn(b"return __real_spawn(rv28_trampoline,rv28_contexts+n,stack,tid)", extra)
            self.assertIn(b"rv28_contexts[n]=(rv28_context){fn,arg,n}", extra)
            self.assertIn(b"c->fn(c->arg);if(atomic_fetch_add_explicit(rv28_returned+c->id,1,memory_order_release))abort()", extra)
            self.assertIn(b"rv28_entered[WORKERS],rv28_returned[WORKERS]", extra)
            self.assertIn(b"atomic_fetch_add_explicit(rv28_entered+c->id,1,memory_order_acq_rel))abort()", extra)
            self.assertIn(b"c->arg!=workers+c->id", extra)
            self.assertIn(b"arg!=workers+n", extra)
            self.assertIn(b"!fn||!stack||!tid", extra)
            self.assertIn(b"(uintptr_t)stack%16||(uintptr_t)tid%_Alignof(atomic_int)", extra)
            self.assertIn(b"for(unsigned i=0;i<WORKERS;i++)if(atomic_load_explicit(rv28_entered+i,memory_order_acquire)!=1||", extra)
            self.assertIn(b"atomic_load_explicit(rv28_returned+i,memory_order_acquire)!=1)abort()", extra)
            self.assertIn(b"int status=__real_main()", extra)
            self.assertIn(b"if(status||atomic_load_explicit(&rv28_called,memory_order_acquire)!=WORKERS", extra)
            self.assertNotIn(b"#define main", extra)
            self.assertNotIn(b"pthread", extra)
            self.assertNotIn(b"printf", extra)
            self.assertNotIn(b"read(", extra)
            self.assertIn(b"static void rv28_marker", extra)
            self.assertIn(b"if(z==-4)continue;if(z<=0||z>n)abort();s+=z;n-=z", extra)
            self.assertIn(b"while(fd==-4)", extra)
            self.assertIn(b"if(fd>=0){rv28_close(fd);return;}", extra)
            self.assertNotIn(b"@arrived@", extra)
            self.assertTrue(all(data == self.files[name] for name, data in self.files.items()))
            bad = dict(paths, release=paths["arrived"])
            with self.assertRaises(ValueError):
                CHECK.startup_wrapper(bad)
            with self.assertRaises(ValueError):
                CHECK.startup_wrapper({name: Path(name) for name in paths})

    def test_freeze_names_before_producer_consumption_and_reject_artifact_drift(self):
        recipe = json.loads(CHECK.normalized(ROOT / CHECK.RECIPE))
        names = INPUTS.producer_names(recipe)
        frozen = {name: CHECK.normalized(ROOT / name) for name in names}
        data = manifest()
        data["inputs"] = {name: CHECK.pin(raw) for name, raw in frozen.items()}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            build = root / "selected"
            build.mkdir()
            CHECK._write(build / "inputs", frozen)
            CHECK._write(build / "generated-readable", self.files)
            (build / "build.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            with patch.object(SOURCE, "prepare", side_effect=AssertionError("producer must not run during freeze")):
                actual = CHECK.freeze_inputs(build, root / "positive")
            self.assertTrue(set(names) <= actual.keys())
            self.assertTrue({CHECK.STARTUP, CHECK.SELF, CHECK.SOURCE_INPUTS, CHECK.VERIFIER,
                CHECK.READER, CHECK.ORACLE, CHECK.RUNTIME, CHECK.SCOPE} <= actual.keys())
            self.assertEqual(actual["selection/generated-readable/runtime.c"], self.files["runtime.c"])
            (build / "inputs" / names[0]).write_bytes(frozen[names[0]] + b"\n")
            with self.assertRaisesRegex(ValueError, "current/frozen producer differs"):
                CHECK.freeze_inputs(build, root / "tampered-artifact")
            data["inputs"]["unlisted.py"] = CHECK.pin(b"not consumed")
            (build / "build.json").write_text(json.dumps(data) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "recipe-derived producer closure"):
                CHECK.freeze_inputs(build, root / "unlisted-input")

    def test_one_deadline_consumes_launch_hold_and_later_work(self):
        clock = CounterClock()
        deadline = CHECK.Deadline(clock=clock)
        self.assertEqual(deadline.left(), 60)
        clock.now += 15
        self.assertEqual(deadline.left(), 45)
        self.assertEqual(deadline.left(5), 5)
        clock.now += 44
        self.assertEqual(deadline.left(), 1)
        clock.now += 1
        with self.assertRaises(TimeoutError):
            deadline.left()
        for seconds in (10, 60.0, True):
            with self.assertRaises(ValueError):
                CHECK.Deadline(seconds=seconds)
        for value in (float("nan"), float("inf"), -1, 0):
            with self.assertRaises(ValueError):
                CHECK.Deadline(clock=clock).left(value)

    def test_mechanism_cpu_is_short_and_cannot_raise_inherited_hard(self):
        limited = CHECK.mechanism_limits((240, 300))
        self.assertEqual((limited["parent_CPU"], limited["parent_CPU_hard"], limited["child_CPU"]), (300, 300, 60))
        self.assertEqual(limited["per_command_wall"], 60)
        unlimited = CHECK.mechanism_limits((-1, -1))
        self.assertEqual((unlimited["parent_CPU"], unlimited["parent_CPU_hard"], unlimited["child_CPU"]), (480, 540, 60))
        self.assertEqual(CHECK.mechanism_limits((60, 60))["child_CPU"], 60)
        for inherited in ((59, 59), (1, 30), (400, 300), (-1, 300), (60.0, 300), (60, True)):
            with self.subTest(inherited=inherited), self.assertRaises(ValueError):
                CHECK.mechanism_limits(inherited)

    def test_launch_records_low_or_missing_available_memory_without_gating(self):
        verifier = types.SimpleNamespace(
            execution_limits=lambda actual, available, wall_seconds: {
                "admission": {"admitted": True}, "identity": (actual, available, wall_seconds)})
        for available in (None, 0, (4 << 30) - 1, 4 << 30):
            with self.subTest(available=available):
                verifier.effective_available_bytes = lambda: available
                result = CHECK.launch_capacity(verifier, "admitted")
                self.assertEqual(result["identity"], ("admitted", available, 60))
                self.assertEqual(result["launch_headroom"], {
                    "effective_available_bytes": available, "used_for_admission": False})

    def test_executed_checker_source_cannot_be_replaced_before_freeze(self):
        raw = CHECK.normalized(HERE / "check_profile_p28.py")
        self.assertEqual(CHECK.executing_source(raw), CHECK.pin(raw))
        changed = raw.replace(b"STARTUP_SECONDS = 60", b"STARTUP_SECONDS = 61")
        self.assertNotEqual(changed, raw)
        with self.assertRaisesRegex(ValueError, "executing code"):
            CHECK.executing_source(changed)
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            fake = temp / "root" / CHECK.SELF
            fake.parent.mkdir(parents=True)
            fake.write_bytes(changed)
            early = {CHECK.SOURCE_INPUTS: b"# pure fixture\n", CHECK.RECIPE: b"{}\n", CHECK.VERIFIER: b"# verifier\n"}
            CHECK._write(temp / "root", early)
            build = temp / "selection"
            build.mkdir()
            (build / "build.json").write_text(json.dumps(manifest()), encoding="utf-8")
            with patch.object(CHECK, "ROOT", temp / "root"), patch.object(CHECK, "load") as loaded:
                with self.assertRaisesRegex(ValueError, "executing code"):
                    CHECK.freeze_inputs(build, temp / "not-created")
                loaded.assert_not_called()
                self.assertFalse((temp / "not-created").exists())

    def test_startup_waits_pass_remaining_deadline_not_reader_default10(self):
        clock = CounterClock()
        deadline = CHECK.Deadline(clock=clock)
        clock.now += 21
        reader = FakeReader(b"uciok\nreadyok\nbestmove e2e4\n")
        fake = types.SimpleNamespace(stdout=reader)
        CHECK._line(fake, b"readyok", 1, deadline)
        CHECK._best(fake, 1, deadline)
        self.assertEqual(reader.calls, [39, 39])

    def test_command_exit_lifetime_and_exact_seven_roles_are_required(self):
        rows = []
        for name, code in CHECK.CASES:
            rows.extend((terminal("compile-" + name), terminal("execute-" + name, code)))
        rows.append(terminal("compile-unpoisoned-startup"))
        CHECK.command_contract(rows)
        for key, value in (("returncode", 0), ("forced_cleanup", True), ("terminal", False),
                ("reaped", False), ("owned_group_absent", False),
                ("original_identity_retained_until_other_members_absent", False),
                ("other_group_members_before_reap", [{"pid": 3}])):
            bad = deepcopy(rows)
            bad[3][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                CHECK.command_contract(bad)
        for changed in (rows[:-1], rows + [terminal()], list(reversed(rows))):
            with self.assertRaises(ValueError):
                CHECK.command_contract(changed)
        with self.assertRaises(ValueError):
            CHECK.require_execution(terminal(code=2), 2)

    def test_natural_exit_retains_original_handle_until_group_settles(self):
        clock = CounterClock()
        deadline = CHECK.Deadline(clock=clock)
        events = []
        groups = iter(([{"pid": 2}], [], []))
        owned = types.SimpleNamespace(exited=lambda: True, group_others=lambda: next(groups),
            stdout=FakeReader(b"uciok\n"), stderr=FakeReader(), reaped=False, finished=False,
            process=types.SimpleNamespace(returncode=0, wait=lambda timeout: events.append("reap")))
        def sleep(seconds):
            events.append("wait-other-members")
            clock.now += seconds
        with patch.object(CHECK.time, "sleep", sleep):
            result = CHECK.natural_finish(owned, deadline)
        self.assertEqual(events, ["wait-other-members", "reap"])
        self.assertTrue(owned.reaped and owned.finished)
        self.assertTrue(result["original_identity_retained_until_other_members_absent"])
        self.assertTrue(result["stdout_eof"] and result["stderr_eof"])
        deadline = CHECK.Deadline(clock=clock)
        fake = types.SimpleNamespace(exited=lambda: True, group_others=lambda: [{"pid": 2}])
        with patch.object(CHECK.time, "sleep", lambda seconds: setattr(clock, "now", clock.now + 61)):
            with self.assertRaises(TimeoutError):
                CHECK.natural_finish(fake, deadline)

    def test_joined_task_poll_allows_transient_tids_but_keeps_same_deadline(self):
        clock = CounterClock()
        deadline = CHECK.Deadline(clock=clock)
        snapshots = iter(({n: {} for n in range(101, 130)}, {101: {}, 102: {}}, {101: {}}, {101: {}}))
        scope = types.SimpleNamespace(task_snapshot=lambda pid: next(snapshots))
        owned = types.SimpleNamespace(process=types.SimpleNamespace(pid=101), exited=lambda: False)
        sleeps = []
        def sleep(seconds):
            sleeps.append(seconds)
            clock.now += seconds
        with patch.object(CHECK.time, "sleep", sleep):
            result = CHECK.joined_tasks(scope, owned, deadline)
        self.assertEqual(result, {101: {}})
        self.assertEqual(len(sleeps), 2)
        self.assertAlmostEqual(deadline.left(), 59.99)
        stuck = types.SimpleNamespace(task_snapshot=lambda pid: {101: {}, 102: {}})
        with patch.object(CHECK.time, "sleep", lambda seconds: setattr(clock, "now", clock.now + 61)):
            with self.assertRaises(TimeoutError):
                CHECK.joined_tasks(stuck, owned, deadline)

    def test_no_old_wait_finish_monkeypatch_or_resource_downgrade(self):
        raw = (HERE / "check_profile_p28.py").read_text(encoding="utf-8")
        tree = ast.parse(raw, feature_version=(3, 10))
        runtime = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "startup_runtime")
        called = [n.func.attr for n in ast.walk(runtime) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertNotIn("wait_line", called)
        self.assertNotIn("wait_best", called)
        self.assertNotIn("finish", called)
        self.assertNotIn("TT_BITS=12", raw)
        self.assertNotIn("Budget(10)", raw)
        self.assertEqual(CHECK.STARTUP_SECONDS, 60)

    def test_literal_support_is_finite_not_dynamic_or_duplicate(self):
        self.assertEqual(CHECK.literal(b"SUPPORT={'a':'b'}\n", "SUPPORT"), {"a": "b"})
        for raw in (b"SUPPORT = factory()\n", b"SUPPORT={}\nSUPPORT={}\n", b"OTHER={}\n"):
            with self.assertRaises((ValueError, TypeError)):
                CHECK.literal(raw, "SUPPORT")

    def test_json_evidence_contains_pins_and_never_fixture_raw_bytes(self):
        _, proof = CHECK.poison_fixture(self.files, SOURCE)
        encoded = json.dumps(proof)
        self.assertIn("full_inverse", encoded)
        self.assertNotIn("bytearray", encoded)
        bad = deepcopy(self.proof)
        bad["resource"]["workers"] = 28.0
        self.assertFalse(CHECK.json_equal(bad, self.proof))


if __name__ == "__main__":
    unittest.main()
