#!/usr/bin/env python3
"""Finite cost comparison after fresh full A/B/C TEST-P4 factories.

This measures only control and the named valid-square successor projection.
Every baseline is freshly generated and admitted by current strict R before
its support is imported. Neither candidate execution nor runtime admission is
performed. The small C visitation program is a separate diagnostic fixture.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = "engines/experiments/tcec-next/"
SELF = PREFIX + "check_profile_square_successor.py"
HELPER = PREFIX + "profile_square_successor.py"
BUILDER = PREFIX + "profile_build.py"
VERIFIER = PREFIX + "profile_verify.py"
OWNER = "engines/experiments/tcec-scope/build.py"
PACKAGE = "engines/scripts/source_package.py"
WRAPPER = PREFIX + "wrapper.py"
UNLINK = PREFIX + "self_unlink.py"
READERS = ("engines/scripts/production_input.py", "engines/scripts/source_composition.py")
SUPPORT = (SELF, HELPER, BUILDER, VERIFIER, OWNER, *READERS)
TRUSTED = (BUILDER, OWNER, PACKAGE, WRAPPER, UNLINK)
CLASS = "rove4k-square-successor-ABC-P4-cost-v1"
_EXECUTING_CODE = sys._getframe().f_code


def require(value, detail):
    if not value:
        raise ValueError(detail)


def pin(data):
    require(type(data) is bytes, "actual immutable bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def normalized(path):
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named source")
    return data


def inventory(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def load_bytes(name, path, data):
    """Execute the bytes already captured, never a second source read."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def cpu_limits(inherited):
    require(type(inherited) is tuple and len(inherited) == 2
            and all(type(n) is int and (n == -1 or n > 0) for n in inherited),
            "positive exact inherited CPU pair required")
    before_soft, before_hard = inherited
    require(before_hard == -1 or 0 < before_soft <= before_hard,
            "inconsistent inherited CPU limits")
    hard = min([1200] + ([before_hard] if before_hard != -1 else []))
    soft = min([900, hard] + ([before_soft] if before_soft != -1 else []))
    factory = min(600, soft, hard)
    require(factory >= 480,
            "inherited CPU cannot admit the unchanged factory's 480-second hard limit")
    return {"parent": (soft, hard), "factory_child": factory,
            "native_child": min(120, soft, hard)}


def factory_argv(family, output):
    require(family in ("A", "B", "C"), "explicit A/B/C family required")
    b, phase, spelling = (("tcec-final-lf", "control", "best") if family == "B"
                          else ("control", "phase-init", "compound"))
    return [sys.executable, "-I", "-B", str(ROOT / BUILDER), "--entry", family,
            "--profile", "test-p4", "--representation", "source-jit",
            "--b-variant", b, "--phase-variant", phase,
            "--spelling-variant", spelling, "--source-dependencies", "unused-includes",
            "--out", str(output)]


def selected_baseline(manifest, admitted, family, builder):
    require(admitted.family == family and admitted.profile_id == "test-p4"
            and admitted.full is True and admitted.representation == "source-jit"
            and manifest.get("family") == family and manifest.get("class") == builder.CLASS
            and manifest.get("complete") is True and manifest.get("reproducible") is True
            and manifest.get("plan", {}).get("entry_cleanup") == "private-path"
            and manifest.get("compile_executor") == manifest.get("compiler")
            and manifest.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
            "fresh complete current full source-JIT/private-path baseline required")
    resources = manifest["resources"]
    require(resources.get("id") == "test-p4"
            and type(resources.get("workers")) is int and resources["workers"] == 4
            and type(resources.get("tt_bits")) is int and resources["tt_bits"] == 22
            and type(resources.get("tt_entry_bytes")) is int and resources["tt_entry_bytes"] == 24
            and resources.get("tt_bytes") == 96 << 20,
            "actual fixed P4 resource domain differs")
    b, phase, spelling = (("tcec-final-lf", "control", "best") if family == "B"
                          else ("control", "phase-init", "compound"))
    post = ({"path": PREFIX + "profile_b.py", "variant": b} if family == "B"
            else {"path": PREFIX + "profile_phase.py", "variant": phase})
    require(manifest.get("post_profile") == post
            and manifest.get("post_spelling") == builder.spelling_selection(
                family, "source-jit", b, phase, spelling)
            and manifest.get("source_dependencies") ==
                {"path": PREFIX + "profile_dependencies.py", "variant": "unused-includes"},
            "current compound A/C or best B final dependency selection required")
    require(manifest.get("commands") and all(
        row.get("started") is True and row.get("terminal") is True and row.get("reaped") is True
        and row.get("owned_group_absent") is True and row.get("forced_cleanup") is False
        and type(row.get("returncode")) is int and row["returncode"] == 0
        for row in manifest["commands"]), "fresh factory command settlement is incomplete")


def restored_source(whole, header, source):
    require(type(whole) is bytes and whole.startswith(header) and 0 < len(header) < len(whole),
            "actual counted wrapper boundary differs")
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    require(decoder.decompress(whole[len(header):], max_length=len(source) + 1) == source
            and decoder.eof and not decoder.unused_data,
            "strict complete source payload inverse differs")


def visitation_fixture(helper):
    """Compile-only observer source; never includes a shipping entry or TT."""
    body = """
 if(n>=64)return -11;
 out->pre[n++]=VALUE;
 if(VALUE+9>out->maximum)out->maximum=VALUE+9;
 if(mode&&(VALUE&3)==1)continue;
 out->post[m++]=VALUE;
 if(VALUE==stop){out->count=n;out->post_count=m;out->early=1;return n;}
"""
    definitions, old_names, new_names = [], [], []
    for family in helper.FAMILIES:
        for index, (_, before, after) in enumerate(helper.SPANS[family]):
            import re
            old_var = re.search(r"(?:for|X)\((?:L|I|int) ([qo])=", before)
            new_var = re.search(r"(?:for|X)\((?:L|I|int) ([qo])=", after)
            require(old_var is not None and new_var is not None
                    and old_var[1] == new_var[1], "finite witness control variable differs")
            for variant, opening, names in (("old", before, old_names), ("new", after, new_names)):
                name = f"scan_{family}_{index}_{variant}"
                names.append(name)
                definitions.append("static int " + name + "(struct observation*out,int mode,int stop){"
                    "int n=0,m=0;" + opening + body.replace("VALUE", old_var[1]) +
                    "}out->count=n;out->post_count=m;return n;}")
    pairs = len(old_names)
    require(pairs == 5 and len(new_names) == pairs, "five finite loop pairs required")
    reference = ("static int reference(struct observation*out,int mode,int stop){int n=0,m=0;"
                 "for(int rank=0;rank<8;rank++)for(int file=0;file<8;file++){int v=rank*16+file;"
                 + body.replace("VALUE", "v") + "}out->count=n;out->post_count=m;return n;}")
    text = """#include <stdio.h>
#include <string.h>
#define L int
#define I int
#define X for
#define W if
_Static_assert(sizeof(int)==4,"named Linux int32 witness");
struct observation{int pre[64],post[64],count,post_count,early,maximum;};
""" + "\n".join(definitions) + "\n" + reference + "\n"
    text += "static int(*old_scan[])(struct observation*,int,int)={" + ",".join(old_names) + "};\n"
    text += "static int(*new_scan[])(struct observation*,int,int)={" + ",".join(new_names) + "};\n"
    text += """int main(void){
 int observations=0;
 for(int mode=0;mode<2;mode++)for(int stop=-1;stop<=128;stop++){
  struct observation expected;memset(&expected,0,sizeof expected);
  int er=reference(&expected,mode,stop);
  for(unsigned pair=0;pair<sizeof old_scan/sizeof*old_scan;pair++){
   struct observation before,after;memset(&before,0,sizeof before);memset(&after,0,sizeof after);
   int a=old_scan[pair](&before,mode,stop),b=new_scan[pair](&after,mode,stop);
   if(a<0||b<0||a!=b||a!=er||memcmp(&before,&after,sizeof before)||
      memcmp(&after,&expected,sizeof after))return 20;
   observations++;
  }
 }
 int q=0,maximum=0,count=0,last=-1;
 for(;q<128;q=q+9&~8){last=q;count++;if(q+9>maximum)maximum=q+9;}
 if(count!=64||last!=119||q!=128||maximum!=128)return 21;
 printf("square-successor-visitation-ok %d 64 119 128\\n",observations);
 return observations==1300?0:22;
}
"""
    return text.encode("ascii"), {"loop_pairs": pairs, "continue_modes": 2,
        "stop_values": 130, "observations": 1300,
        "expected_stdout": "square-successor-visitation-ok 1300 64 119 128\n",
        "shipping_entry_called": False, "TT_allocated": False,
        "scope": "exact loop-opening visitation, continue and early-return diagnostic; source bodies protected separately"}


def measure(out):
    import resource
    require(sys.platform == "linux" and platform.machine() == "x86_64",
            "Linux x86-64 cost execution required")
    require(out.is_absolute() and not out.exists() and ROOT not in (out, *out.parents)
            and not any((p / ".git").exists() for p in (out, *out.parents)),
            "new absolute output outside every Git checkout required")
    captured = {name: normalized(ROOT / name) for name in SUPPORT}
    require(compile(captured[SELF], str(Path(__file__)), "exec", dont_inherit=True) == _EXECUTING_CODE,
            "captured driver differs from its actually executing code")
    out.mkdir(parents=False)
    for name, data in captured.items():
        write(out / "support", name, data)
    report = {"format": 1, "class": CLASS, "complete": False, "reproducible": False,
        "commands": [], "families": [], "support": inventory(captured),
        "cases": ["control", "square-successor"], "profiles": ["test-p4"],
        "engine_executed": False, "TT_allocated": False, "runtime_qualified": False,
        "rules_qualified": False, "physical_placement_qualified": False,
        "production_selected": False, "production_adopted": False,
        "cpu_affinity": sorted(os.sched_getaffinity(0)),
        "scope": "fresh factories and actual native/whole cost only; no shipping engine execution"}
    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    save()
    owner = helper = R = builder = host = None
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    try:
        limits = cpu_limits(resource.getrlimit(resource.RLIMIT_CPU))
        as_before = resource.getrlimit(resource.RLIMIT_AS)
        require(all(value == resource.RLIM_INFINITY or value >= 4 << 30 for value in as_before),
                "inherited address space cannot admit unchanged 4GiB factory")
        report["limits"] = {"inherited_CPU": list(resource.getrlimit(resource.RLIMIT_CPU)),
            "applied_CPU": limits, "inherited_AS": list(as_before),
            "parent_AS": 4 << 30, "factory_AS": 4 << 30, "native_AS": 2 << 30,
            "aggregate_wall": 1800, "per_command_wall": 600, "tool_output_bytes": 16 << 20}
        owner = load_bytes("square_owner", ROOT / OWNER, captured[OWNER])
        require(owner.EXECUTING_BUILD == captured[OWNER], "owner reread changed after capture")
        owner.LIMITS.update(aggregate_wall=1800, per_command_wall=600,
            parent_AS=4 << 30, parent_CPU=limits["parent"][0], parent_CPU_hard=limits["parent"][1],
            child_AS=4 << 30, nested_producer_AS=4 << 30, child_CPU=limits["factory_child"],
            tool_output_bytes=16 << 20)
        class Host(owner.Host):
            def settle(self, child, row, force=False):
                if row.get("kind", "").endswith("-fresh-profile"):
                    row["cooperative_termination_seconds"] = 30
                return super().settle(child, row, force)
        host = Host(out, report, save)
        helper = load_bytes("square_projection", ROOT / HELPER, captured[HELPER])
        R = load_bytes("square_current_R", ROOT / VERIFIER, captured[VERIFIER])
        builder = load_bytes("square_current_builder_policy", ROOT / BUILDER, captured[BUILDER])
        report["pure_iteration_witness"] = helper.iteration_witness()
        baselines = []
        for family in helper.FAMILIES:
            directory = out / family
            directory.mkdir()
            baseline = directory / "fresh-profile"
            owner.LIMITS.update(child_AS=4 << 30, child_CPU=limits["factory_child"])
            host.run(factory_argv(family, baseline), cwd=directory, kind=family + "-fresh-profile")
            manifest_path = R.artifact_file(baseline, "build.json")
            raw = R.input_reader().read_regular(manifest_path, limit=16 << 20)
            manifest = json.loads(raw)
            admitted = R.admit_c_build(manifest, baseline)
            selected_baseline(manifest, admitted, family, builder)
            source = R.checked_artifact(baseline, admitted.source, R._field_pin(admitted.expected, "source"))
            require((len(source), sha256(source).hexdigest()) == helper.INPUTS[(family, "test-p4")],
                    "fresh actual selected source differs from the finite projection input")
            inputs = {}
            for name, expected in admitted.input_pins.items():
                data = R.checked_artifact(baseline, "inputs/" + name, expected)
                require(data == R.source_bytes(name, expected), "fresh frozen input is not current: " + name)
                inputs[name] = data
                write(directory / "inputs", name, data)
            require(all(name in inputs for name in TRUSTED), "fresh baseline omitted named cost support")
            require(inputs[BUILDER] == captured[BUILDER] and inputs[OWNER] == captured[OWNER],
                    "fresh factory or compiler owner differs from captured current tools")
            frozen = directory / "inputs"
            packaging = load_bytes("square_package_" + family, frozen / PACKAGE, inputs[PACKAGE])
            wrapper = load_bytes("square_wrapper_" + family, frozen / WRAPPER, inputs[WRAPPER])
            unlink = load_bytes("square_unlink_" + family, frozen / UNLINK, inputs[UNLINK])
            candidate, proof = helper.transform_source(source, family=family, profile_id="test-p4")
            require(helper.restore_source(candidate, json.loads(json.dumps(proof))) == source,
                    "new projection JSON roundtrip/full inverse differs")
            write(directory, "projection.json", (json.dumps(proof, indent=2) + "\n").encode())
            row = {"family": family, "profile": "test-p4", "complete": False,
                "baseline_manifest": {"path": str(manifest_path), **pin(raw)},
                "baseline_expected": admitted.expected, "inputs": inventory(inputs),
                "resources": admitted.resources, "compiler": manifest["compiler"],
                "compression": manifest["compression"], "projection": proof, "attempts": []}
            report["families"].append(row)
            baselines.append((baseline, manifest_path, raw, manifest, admitted, inputs, row))
            save()
            owner.LIMITS.update(child_AS=2 << 30, child_CPU=limits["native_child"])
            version = host.run([manifest["compiler"][0], "--version"], cwd=directory,
                               kind=family + "-actual-compiler-version").decode("utf-8", "strict").splitlines()[0]
            require(version == manifest["compile_executor_version"], "actual baseline compiler version changed")
            row["compiler_version"] = version
            for case in ("control", "square-successor"):
                for attempt in ("first", "repeat"):
                    actual_source, actual_proof = (source, None) if case == "control" else helper.transform_source(
                        source, family=family, profile_id="test-p4")
                    if case != "control":
                        require(actual_source == candidate and actual_proof == proof
                                and helper.restore_source(actual_source, actual_proof) == source,
                                "independent square projection differs")
                    target = directory / case / attempt
                    native_dir = target / "native"
                    native_dir.mkdir(parents=True)
                    write(target, "main.c", actual_source)
                    host.run(manifest["compiler"], cwd=native_dir,
                             kind=f"{family}-{case}-{attempt}-compile", data=actual_source)
                    native = R.input_reader().read_regular(native_dir / "x", limit=16 << 20)
                    header = wrapper.header(packaging, unlink, manifest["compiler"])
                    whole = wrapper.package(packaging, unlink, actual_source,
                                            manifest["compression"], manifest["compiler"])
                    restored_source(whole, header, actual_source)
                    artifacts = {"source": actual_source, "native": native, "whole": whole,
                                 "header": header, "payload": whole[len(header):]}
                    if case == "control":
                        require(all(pin(data) == R._field_pin(admitted.expected, kind)
                                    for kind, data in artifacts.items()),
                                "fresh control cost bytes differ from its strict baseline admission")
                    for name, data in (("x", whole), ("header.sh", header),
                                       ("payload.lzma", whole[len(header):])):
                        write(target, name, data)
                    (target / "x").chmod(0o700)
                    row["attempts"].append({"case": case, "attempt": attempt,
                        "directory": str(target), "artifacts": inventory(artifacts)})
                    save()
            costs = {}
            for case in ("control", "square-successor"):
                one, two = [item for item in row["attempts"] if item["case"] == case]
                require(one["artifacts"] == two["artifacts"] and all(
                    (Path(one["directory"]) / name).read_bytes() == (Path(two["directory"]) / name).read_bytes()
                    for name in ("main.c", "native/x", "x", "header.sh", "payload.lzma")),
                    "independent complete cost productions differ")
                costs[case] = one["artifacts"]
            row.update(costs=costs, delta={kind: costs["square-successor"][kind]["bytes"] -
                costs["control"][kind]["bytes"] for kind in ("source", "native", "whole")})
            row.update(costs_complete=True, reproducible=True,
                       runtime_qualified=False, rules_qualified=False)
            save()
        fixture, witness = visitation_fixture(helper)
        fixture_dir = out / "visitation"
        fixture_dir.mkdir()
        write(fixture_dir, "fixture.c", fixture)
        witness.update(source=pin(fixture), compiled_C_executed=False, modes=[])
        report["compiled_visitation_witness"] = witness
        for mode, flags in (("plain", []), ("ubsan", ["-fsanitize=undefined", "-fno-sanitize-recover=undefined"])):
            command = ["cc", "-std=c11", "-O1", "-x", "c", "-", "-o", mode, *flags]
            host.run(command, cwd=fixture_dir, kind="visitation-" + mode + "-compile", data=fixture)
            output = host.run([str(fixture_dir / mode)], cwd=fixture_dir,
                              kind="visitation-" + mode + "-execute")
            require(output == witness["expected_stdout"].encode("ascii")
                    and report["commands"][-1]["stderr"]["bytes"] == 0,
                    "actual C visitation or UBSan diagnostic differs")
            witness["modes"].append({"mode": mode, "compiler": command,
                "native": pin((fixture_dir / mode).read_bytes()), "stdout": pin(output)})
            save()
        witness["compiled_C_executed"] = True
        for baseline, manifest_path, raw, manifest, admitted, inputs, row in baselines:
            require(R.input_reader().read_regular(manifest_path, limit=16 << 20) == raw
                    and R.admit_c_build(manifest, baseline) == admitted,
                    "complete actual baseline admission changed during cost measurement")
            require(all(R.source_bytes(name, expected) == inputs[name]
                        and R.checked_artifact(baseline, "inputs/" + name, expected) == inputs[name]
                        for name, expected in admitted.input_pins.items()),
                    "current/frozen full family input closure changed")
            row.update(complete=True, full_baseline_admission_before_after_equal=True,
                       inputs_rechecked=True)
        require(all(normalized(ROOT / name) == data for name, data in captured.items()),
                "executing named current support changed")
        report.update(support_rechecked=True, reproducible=True,
            measured_whole_winners=[row["family"] for row in report["families"] if row["delta"]["whole"] < 0])
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        save()
        raise
    finally:
        try:
            if host is not None:
                host.close()
            else:
                report["host_cleanup"] = {"not_constructed": True}
                save()
        finally:
            signal.signal(signal.SIGCHLD, previous)
    report["complete"] = True
    save()
    print(json.dumps({"class": CLASS, "complete": True,
        "deltas": {row["family"]: row["delta"] for row in report["families"]},
        "actual_C_visitation": True, "engine_executed": False}))


def self_test():
    import copy
    import unittest
    helper_raw = normalized(ROOT / HELPER)
    helper = load_bytes("square_pure_projection", ROOT / HELPER, helper_raw)
    class Properties(unittest.TestCase):
        def test_python310_source_syntax(self):
            import ast
            for name in (SELF, HELPER):
                ast.parse(normalized(ROOT / name).decode("utf-8"), feature_version=(3, 10))
        def test_rank_file_order_and_bounds(self):
            witness = helper.iteration_witness()
            self.assertEqual(witness["values"], [r * 16 + f for r in range(8) for f in range(8)])
            self.assertEqual((witness["count"], witness["last"], witness["exit"], witness["maximum_addition"]),
                             (64, 119, 128, 128))
            self.assertIs(witness["compiled_C_executed"], False)
        def test_finite_public_domain_and_actual_source_pin(self):
            for family, profile in (("D", "test-p4"), ("E", "test-p4"), ("F", "test-p4"),
                                    ("A", "test-p28"), ("A", "tcec-provisional"), (True, "test-p4")):
                with self.assertRaisesRegex(ValueError, "finite"):
                    helper.transform_source(b"unused", family=family, profile_id=profile)
            with self.assertRaisesRegex(ValueError, "exact pin"):
                helper.transform_source(b"not the admitted current source", family="A")
        def test_two_splices_keep_body_and_complete_inverse(self):
            specifications = (("first", "OLD1", "NEW1"), ("second", "OLD2", "NEW2"))
            source = b"prefix OLD1 body-with-continue; OLD2 early-return-body suffix"
            candidate, edits, gaps = helper._project(source, specifications)
            self.assertEqual(helper._inverse(candidate, json.loads(json.dumps(edits))), source)
            for gap in gaps:
                self.assertEqual(source[gap["input_begin"]:gap["input_begin"] + gap["bytes"]],
                                 candidate[gap["output_begin"]:gap["output_begin"] + gap["bytes"]])
        def test_missing_duplicate_and_overlap_spans_fail(self):
            for source, spans in ((b"none", (("x", "OLD", "NEW"),)),
                                  (b"OLD OLD", (("x", "OLD", "NEW"),)),
                                  (b"ABCDE", (("x", "ABC", "a"), ("y", "BCD", "b")))):
                with self.assertRaises(ValueError):
                    helper._project(source, spans)
        def test_inverse_rejects_boolean_or_changed_coordinate(self):
            candidate, edits, _ = helper._project(b"prefix OLD suffix", (("r", "OLD", "NEW"),))
            for coordinate in (True, -1, 1000):
                wrong = copy.deepcopy(edits)
                wrong[0]["output_begin"] = coordinate
                with self.assertRaises(ValueError):
                    helper._inverse(candidate, wrong)
        def test_selected_factory_arguments(self):
            for family, selection in (("A", "compound"), ("B", "best"), ("C", "compound")):
                command = factory_argv(family, Path("/owned/fresh-" + family))
                self.assertEqual(command[command.index("--spelling-variant") + 1], selection)
                self.assertEqual(command[command.index("--profile") + 1], "test-p4")
                self.assertNotIn("--runtime", command)
        def test_cpu_never_raises_inherited_limits(self):
            for inherited in ((-1, -1), (600, 700), (480, 500), (1000, 1100)):
                result = cpu_limits(inherited)
                soft, hard = result["parent"]
                self.assertLessEqual(soft, hard)
                self.assertLessEqual(result["factory_child"], soft)
                self.assertLessEqual(result["factory_child"], hard)
                self.assertLessEqual(result["native_child"], min(soft, hard, 120))
                if inherited[0] != -1:
                    self.assertLessEqual(soft, inherited[0])
                if inherited[1] != -1:
                    self.assertLessEqual(hard, inherited[1])
            with self.assertRaisesRegex(ValueError, "480"):
                cpu_limits((479, 500))
        def test_cpu_invalid_types_and_order_fail(self):
            for inherited in ((True, 500), (0, 500), (501, 500), (-2, 500), (500,), [500, 600]):
                with self.assertRaises(ValueError):
                    cpu_limits(inherited)
        def test_strict_lzma_rejects_tail_wrong_source_and_truncation(self):
            source, header = b"test source bytes", b"counted-header\n"
            payload = lzma.compress(source, format=lzma.FORMAT_ALONE)
            restored_source(header + payload, header, source)
            for whole, expected in ((header + payload + b"tail", source),
                                    (header + payload, b"wrong source"),
                                    (header + payload[:-2], source)):
                with self.assertRaises((ValueError, lzma.LZMAError)):
                    restored_source(whole, header, expected)
        def test_fixture_contains_exact_controls_and_no_shipping_entry(self):
            fixture, description = visitation_fixture(helper)
            self.assertEqual(description["observations"], 1300)
            self.assertIs(description["TT_allocated"], False)
            self.assertEqual(fixture.count(b"int main(void)"), 1)
            self.assertNotIn(b"pthread_create", fixture)
            for family in helper.FAMILIES:
                for _, before, after in helper.SPANS[family]:
                    self.assertIn(before.encode(), fixture)
                    self.assertIn(after.encode(), fixture)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Properties)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    require(result.wasSuccessful(), "square successor pure self-tests failed")
    require(normalized(ROOT / HELPER) == helper_raw, "pure helper changed during self-test")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        require(args.out is None, "self-test does not construct cost outputs")
        self_test()
    else:
        require(args.out is not None, "one explicit new external output required")
        measure(args.out)


if __name__ == "__main__":
    main()
