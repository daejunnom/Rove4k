"""Targeted runner regressions for selection, cache identity and evidence.

The linker fixture deliberately has non-additive whole-file costs. It copies a
real host ELF and appends unobserved padding, so the runner must execute/check
the complete artifact without assuming that shortest component objects win.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "nvcompact.py"
sys.path.insert(0, str(ROOT))
import nvcompact


FIXTURE = r'''
import pathlib
import subprocess
import sys

mode, *args = sys.argv[1:]
if mode == "object":
    output, slot, variant, length = args
    content = (slot + ":" + variant + "\n").encode()
    pathlib.Path(output).write_bytes(content + b"." * int(length))
elif mode == "link":
    output, base, *objects = args
    markers = [pathlib.Path(p).read_bytes().split(b"\n", 1)[0] for p in objects]
    if [m.split(b":", 1)[0] for m in markers] != [b"left", b"right"]:
        raise SystemExit("component cache substituted another slot's object")
    large_pair = all(m.endswith(b":large") for m in markers)
    pathlib.Path(output).write_bytes(pathlib.Path(base).read_bytes() +
                                    (b"." * (0 if large_pair else 2048)))
elif mode == "verify":
    completed = subprocess.run([args[0]], input=b"", capture_output=True, timeout=3)
    if completed.returncode != 0 or completed.stdout or completed.stderr:
        raise SystemExit("whole artifact violated the fixture contract")
else:
    raise SystemExit("unknown fixture action")
'''


@unittest.skipUnless(sys.platform.startswith("linux"), "ELF execution fixture targets Linux")
class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nvcompact runner ")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def make_project(self, *, colliding_names=False):
        compiler = shutil.which("cc")
        if not compiler:
            self.skipTest("the real native fixture requires the host C compiler")
        project = self.work / "project with spaces"
        project.mkdir()
        (project / "base.c").write_text("int main(void) { return 0; }\n")
        subprocess.run([compiler, str(project / "base.c"), "-o", str(project / "base")],
                       check=True, capture_output=True, timeout=10)
        (project / "fixture.py").write_text(textwrap.dedent(FIXTURE))
        identifiers = (("a-b", "c"), ("a", "b-c")) if colliding_names else \
            (("first", "small"), ("second", "small"))
        components = []
        for (component_id, small_id), slot in zip(identifiers, ("left", "right")):
            variants = []
            for variant_id, marker, length in ((small_id, "small", 1), ("large", "large", 256)):
                variants.append({
                    "id": variant_id, "language": "test fixture bytes",
                    "sources": ["fixture.py"],
                    "commands": [["{python}", "{source}", "object", "{object}",
                                  slot, marker, str(length)]],
                })
            components.append({"id": component_id, "contract": "one typed fixture slot",
                               "variants": variants})
        order = [c["id"] for c in components]
        manifest = {
            "project_root": ".", "target": "x86_64-linux-gnu",
            "inputs": ["base", "fixture.py"],
            "tools": {"python": {"executable": sys.executable}},
            "components": components,
            "build_profiles": [{"id": "default", "variables": {}}],
            "link_profiles": [{"id": "fixture", "common": [],
                               "argv": ["{python}", "{root}/fixture.py", "link",
                                        "{binary}", "{root}/base", "{objects}"]}],
            "verify": ["{python}", "{root}/fixture.py", "verify", "{binary}"],
            "baseline": {"build": "default", "link": "fixture", "order": order,
                         "variants": {identifier: small for identifier, small in identifiers}},
            "codecs": [],
        }
        path = project / "portfolio.json"
        path.write_text(json.dumps(manifest))
        return path, manifest

    def invoke(self, *argv):
        return subprocess.run([sys.executable, str(RUNNER), *map(str, argv)],
                              capture_output=True, text=True, timeout=30)

    def test_complete_file_selection_reproduction_and_input_integrity(self):
        manifest, _ = self.make_project()
        out = self.work / "chosen results"
        result = self.invoke("run", manifest, "--out", out, "--jobs", 2,
                             "--max-seconds", 20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((out / "report.json").read_text())
        recipe = json.loads((out / "winner.recipe.json").read_text())
        self.assertEqual(set(recipe["selection"]["variants"].values()), {"large"})
        accepted = [row for row in report["candidates"]
                    if row["id"] == report["winner"]["candidate"]][0]
        baseline_objects = report["candidates"][0]["objects"]
        self.assertGreater(sum(o["bytes"] for o in accepted["objects"]),
                           sum(o["bytes"] for o in baseline_objects))
        self.assertLess(report["winner"]["bytes"], report["baseline"]["bytes"])
        repeated = self.work / "repeated elsewhere"
        result = self.invoke("reproduce", out / "winner.recipe.json", "--out", repeated)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((out / "winner").read_bytes(), (repeated / "winner").read_bytes())

        before = (out / "winner").read_bytes()
        refused = self.invoke("run", manifest, "--out", out)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual((out / "winner").read_bytes(), before)
        with (out / "snapshot" / "fixture.py").open("a") as stream:
            stream.write("\n# declared source changed after selection\n")
        refused = self.invoke("reproduce", out / "winner.recipe.json",
                              "--out", self.work / "must not accept changed input")
        self.assertNotEqual(refused.returncode, 0)

    def test_distinct_component_variant_pairs_do_not_alias_cache_entries(self):
        manifest, _ = self.make_project(colliding_names=True)
        out = self.work / "collision results"
        result = self.invoke("run", manifest, "--out", out, "--jobs", 2,
                             "--max-seconds", 20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((out / "report.json").read_text())
        self.assertEqual(report["status"], "accepted")

    def test_candidate_limit_does_not_materialize_the_full_cross_product(self):
        # Two variants in 30 roles imply 2**30 combinations. Only one is asked
        # for. Bound this test process's memory so an eager-product regression
        # fails cleanly rather than consuming the user's machine.
        child = textwrap.dedent('''
            import pathlib, resource, sys, tempfile
            sys.path.insert(0, sys.argv[1])
            import nvcompact
            resource.setrlimit(resource.RLIMIT_AS, (256 << 20, 256 << 20))
            m = {"target": "x86_64-linux-gnu", "tools": {},
                 "components": [{"id": "c" + str(i), "contract": "pure scalar",
                                 "variants": [{"id": "a"}, {"id": "b"}]}
                                for i in range(30)],
                 "build_profiles": [{"id": "b"}],
                 "link_profiles": [{"id": "l"}], "verify": ["unused"]}
            a = type("Options", (), {"max_seconds": 10.0, "command_seconds": 2.0,
                    "max_log_bytes": 1024, "tool": [], "max_candidates": 1,
                    "profile": None, "link_profile": None})()
            with tempfile.TemporaryDirectory() as directory:
                path = pathlib.Path(directory)
                campaign = nvcompact.Campaign(m, path, path, a)
                total, choices = campaign.candidates()
                assert total == 2**30 and len(choices) == 1, (total, len(choices))
        ''')
        result = subprocess.run([sys.executable, "-c", child, str(ROOT)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_timeout_and_excess_output_are_failures(self):
        env = {"PATH": os.environ.get("PATH", ""), "LANG": "C"}
        for name, code, timeout, cap, reason in (
                ("timeout", "import time; time.sleep(5)", 0.1, 1024, "timeout"),
                ("output", "import os; os.write(1, b'x' * 8192)", 2.0, 128, "log_limit")):
            with self.subTest(name=name):
                with self.assertRaises(nvcompact.RunError) as raised:
                    nvcompact.execute([sys.executable, "-c", code], cwd=self.work,
                                      env=env, log=self.work / name, timeout=timeout,
                                      max_log_bytes=cap, phase="fixture")
                self.assertEqual(raised.exception.detail["reason"], reason)

    def test_notation_overlay_locks_only_complete_identical_objects(self):
        compiler = shutil.which("cc")
        if not compiler:
            self.skipTest("notation integration requires the host C compiler")
        project = self.work / "notation project"
        (project / "src" / "local").mkdir(parents=True)
        files = {
            "src/calc.c": '#include "local/value.h"\nint answer(void) { return 0x0000002a + OFFSET; }\n',
            "src/local/value.h": "#define OFFSET 5\n",
            "src/main.c": "int answer(void); int main(void){return answer()==47?0:1;}\n",
            "src/path.c": 'const char *where(void){return __FILE__;} int value=0x00000001;\n',
            "src/lines.c": '/* original location is observable */\nint value=0x00000001;\n_Static_assert(__LINE__==3,"location");\n',
            "check.py": "import subprocess,sys\nsubprocess.run([sys.argv[1]],check=True,timeout=3)\n",
        }
        for name, content in files.items():
            (project / name).write_text(content)
        notation = {"language": "c", "target": "c11-lp64", "token_contract": "no-token-observation",
                    "compact": True, "max_variants": 3}
        commands = [["{cc}", "-std=c11", "-Os", "-frandom-seed={unit_id}",
                     "-c", "{source}", "-o", "{object}"]]
        manifest = {
            "project_root": ".", "target": "x86_64-linux-gnu", "inputs": list(files),
            "tools": {"cc": {"executable": compiler}, "python": {"executable": sys.executable}},
            "components": [{"id": "kernel", "contract": "answer returns 47 without effects",
                            "variants": [{"id": "c", "sources": ["./src/calc.c"],
                                          "commands": commands, "notation": notation}]}],
            "build_profiles": [{"id": "default"}],
            "link_profiles": [{"id": "hosted", "common": [{"id": "main", "sources": ["src/main.c"], "commands": commands}],
                               "argv": ["{cc}", "{objects}", "-Wl,--build-id=none", "-o", "{binary}"]}],
            "verify": ["{python}", "{root}/check.py", "{binary}"], "codecs": [],
            "baseline": {"build": "default", "link": "hosted", "order": ["kernel"], "variants": {"kernel": "c"}},
        }
        path = project / "manifest.json"
        path.write_text(json.dumps(manifest))
        out = self.work / "notation run"
        completed = self.invoke("run", path, "--out", out, "--max-seconds", 20)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads((out / "report.json").read_text())
        objects = report["candidates"][0]["objects"]
        audited = next(obj for obj in objects if "notation" in obj)
        self.assertGreater(audited["notation"]["source_bytes_saved"], 0)
        self.assertEqual(audited["notation"]["selected"]["status"], "object_byte_identical")
        selected_root = out / audited["notation"]["selected"]["overlay"]
        original_obj = out / "objects/default/variant/kernel/c/unit.o"
        self.assertEqual(original_obj.read_bytes(), (selected_root.parent / "build/unit.o").read_bytes())
        self.assertIn("nvnotation.py", report["runtime"]["source_sha256"])
        repeated = self.work / "notation repeated"
        completed = self.invoke("reproduce", out / "winner.recipe.json", "--out", repeated)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual((out / "winner").read_bytes(), (repeated / "winner").read_bytes())

        # Deliberately violated non-observation contracts demonstrate why the
        # complete-object boundary and compile failures must remain real gates.
        probe_out = self.work / "notation negative cases"
        probe_out.mkdir()
        args = SimpleNamespace(max_seconds=20, command_seconds=5, max_log_bytes=1 << 20, tool=[])
        campaign = nvcompact.Campaign(manifest, out / "snapshot", probe_out, args)
        path_unit = campaign.unit("default", ("probe", "path"),
                                  {"sources": ["src/path.c"], "commands": commands, "notation": notation})
        rows = path_unit["notation"]["candidates"]
        self.assertTrue(any(r["status"] == "rejected_object_difference" for r in rows))
        self.assertEqual(path_unit["notation"]["selected"]["id"], "raw")
        line_unit = campaign.unit("default", ("probe", "lines"),
                                  {"sources": ["src/lines.c"], "commands": commands, "notation": notation})
        self.assertTrue(any(r["status"] == "failed" and r.get("phase") == "notation_compile"
                            for r in line_unit["notation"]["candidates"]))
        self.assertTrue(line_unit["path"].is_file())
        for name, content in files.items():
            self.assertEqual((project / name).read_text(), content)
            self.assertEqual((out / "snapshot" / name).read_text(), content)


if __name__ == "__main__":
    unittest.main()
