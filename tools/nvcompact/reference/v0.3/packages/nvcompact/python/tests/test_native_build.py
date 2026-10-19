"""Real native linking, explicit execution, and independent reproduction."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nvcompact
import nvelf
import nvnotation
import nvpack


@unittest.skipUnless(sys.platform.startswith("linux") and shutil.which("cc"),
                     "real native integration needs Linux and a C compiler")
class NativeBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nvcompact native tests ")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.executions = self.work / "actual program executions.log"

    def project(self, *, name="project", bad_variant=False):
        project = self.work / name
        shutil.copytree(ROOT.parent / "examples/native-build", project)
        main = project / "main.c"
        main.write_text('#include <stdlib.h>\n' + main.read_text().replace(
            "int main(void) {", "int main(void) {\n"
            '    const char *path = getenv("NVBUILD_EXECUTIONS");\n'
            '    if(path) { FILE *f=fopen(path,"a"); if(!f)return 70; fputs("ran\\n",f); fclose(f); }'))
        manifest = json.loads((project / "manifest.json").read_text())
        manifest["environment"] = {"NVBUILD_EXECUTIONS": str(self.executions)}
        manifest["tools"]["cc"]["executable"] = shutil.which("cc")
        manifest["tools"]["python"]["executable"] = sys.executable
        manifest["build_profiles"] = manifest["build_profiles"][:1]
        if bad_variant:
            (project / "square_mul.c").write_text(
                '#include <stdint.h>\nconst volatile unsigned char zeros[8192]={0};\n'
                'uint32_t square(uint32_t x){return x*x+zeros[x];}\n')
            (project / "square_sum.c").write_text(
                '#include <stdint.h>\nuint32_t square(uint32_t x){(void)x;return 0;}\n')
        self.save_manifest(project, manifest)
        return project, manifest

    @staticmethod
    def save_manifest(project, manifest):
        (project / "manifest.json").write_text(json.dumps(manifest))

    def invoke(self, *argv):
        return subprocess.run([sys.executable, "-B", str(ROOT / "nvcompact.py"), *map(str, argv)],
                              capture_output=True, text=True, timeout=30)

    def executed_count(self):
        return len(self.executions.read_text().splitlines()) if self.executions.exists() else 0

    def test_compile_only_preserves_linked_bytes_and_skips_compressors_and_execution(self):
        project, manifest = self.project()
        manifest["tools"]["python"]["executable"] = str(self.work / "missing checker runtime")
        manifest["max_bytes"] = 1  # A packed-submission budget must not govern plain linking.
        manifest["components"][0]["variants"][0]["notation"] = {
            "language": "c", "target": "c11-lp64", "token_contract": "no-token-observation", "compact": True}
        self.save_manifest(project, manifest)
        out = self.work / "plain linked result"
        # Instrument unused transformations, while independently checking the
        # actual ELF, its intact section table, native bytes, and executable IO.
        with contextlib.ExitStack() as stack:
            for module, name in ((nvpack, "pack_by_id"), (nvpack, "_compress"),
                                 (nvelf, "deployment_variants"), (nvnotation, "generate_variants")):
                stack.enter_context(mock.patch.object(module, name, side_effect=AssertionError("unexpected transform")))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            self.assertEqual(nvcompact.main(["build", str(project / "manifest.json"), "--out", str(out),
                                             "--max-seconds", "20"]), 0)
            repeated = self.work / "fresh reproduction"
            self.assertEqual(nvcompact.main(["reproduce", str(out / "winner.recipe.json"),
                                             "--out", str(repeated), "--max-seconds", "20"]), 0)
        self.assertEqual(self.executed_count(), 0)
        report = json.loads((out / "report.json").read_text())
        recipe = json.loads((out / "winner.recipe.json").read_text())
        replay = json.loads((repeated / "reproduction.json").read_text())
        self.assertEqual((report["status"], report["packing"], recipe["verification"]),
                         ("built", "none", "not_run"))
        self.assertEqual(report["screened_complete_files"], 0)
        self.assertEqual(replay["verification"]["status"], "not_run")
        self.assertEqual(set(recipe["tools"]), {"cc"})
        data = (out / "winner").read_bytes()
        self.assertEqual(data, (repeated / "winner").read_bytes())
        self.assertEqual(data, (out / report["winner"]["artifact"]).read_bytes())
        self.assertEqual(data[:4], b"\x7fELF")
        self.assertGreater(struct.unpack_from("<Q", data, 40)[0], 0)  # ELF64 e_shoff.
        self.assertGreater(struct.unpack_from("<H", data, 60)[0], 0)  # ELF64 e_shnum.
        sizes = [a["bytes"] for c in report["candidates"] for a in c["artifacts"] if a["status"] == "built"]
        self.assertEqual(len(data), min(sizes))
        observed = subprocess.run([str(out / "winner")], input=b"0\n1\n7\n255\n",
                                  capture_output=True, timeout=3,
                                  env={**os.environ, "NVBUILD_EXECUTIONS": str(self.executions)})
        self.assertEqual((observed.returncode, observed.stdout, observed.stderr),
                         (0, b"0\n1\n49\n65025\n", b""))
        self.assertEqual(self.executed_count(), 1)

    def test_minimal_manifest_and_later_verification_do_not_change_replay_defaults(self):
        project, manifest = self.project(name="minimal")
        minimal = dict(manifest)
        for name in ("verify", "verify_final", "baseline"):
            minimal.pop(name)
        self.save_manifest(project, minimal)
        out = self.work / "minimal result"
        result = self.invoke("build", project / "manifest.json", "--out", out)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.executed_count(), 0)
        refused = self.invoke("build", project / "manifest.json", "--out", self.work / "missing checker", "--verify")
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(self.executed_count(), 0)
        self.save_manifest(project, {**minimal, "target": 17})
        refused = self.invoke("build", project / "manifest.json", "--out", self.work / "invalid target")
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(self.executed_count(), 0)

        self.save_manifest(project, manifest)
        out = self.work / "unchecked with a declared checker"
        result = self.invoke("build", project / "manifest.json", "--out", out)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        recipe = json.loads((out / "winner.recipe.json").read_text())
        self.assertEqual(set(recipe["tools"]), {"cc"})
        checked = self.work / "explicitly checked replay"
        result = self.invoke("reproduce", out / "winner.recipe.json", "--out", checked, "--verify")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertGreater(self.executed_count(), 0)
        replay = json.loads((checked / "reproduction.json").read_text())
        self.assertEqual(replay["verification"]["checker_output"]["integer_inputs"], 256)
        self.assertIn("python", replay["verification"]["observed_tools"])
        before = self.executed_count()
        result = self.invoke("reproduce", out / "winner.recipe.json", "--out", self.work / "plain replay again")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.executed_count(), before)

    def test_verified_build_and_unverified_wrong_candidate_have_distinct_outcomes(self):
        project, _ = self.project(bad_variant=True)
        out = self.work / "unchecked wrong implementation"
        result = self.invoke("build", project / "manifest.json", "--out", out)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((out / "report.json").read_text())
        self.assertEqual(report["status"], "built")
        self.assertEqual(self.executed_count(), 0)
        rejected = self.work / "semantic failure"
        result = self.invoke("reproduce", out / "winner.recipe.json", "--out", rejected, "--verify")
        self.assertNotEqual(result.returncode, 0)
        failure = json.loads((rejected / "reproduction.json").read_text())
        self.assertEqual((failure["status"], failure["phase"]), ("failed", "verify_final"))
        self.assertFalse((rejected / "winner").exists())

        checked = self.work / "verified selection"
        result = self.invoke("build", project / "manifest.json", "--out", checked, "--verify")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((checked / "report.json").read_text())
        self.assertEqual(report["status"], "accepted")
        self.assertTrue(any(c["status"] == "failed" and c["phase"] == "verify" for c in report["candidates"]))
        before = self.executed_count()
        # Even a previously verified native recipe does not run the engine
        # again without this invocation's explicit --verify.
        repeated = self.work / "previously verified but now bytes only"
        result = self.invoke("reproduce", checked / "winner.recipe.json", "--out", repeated,
                             "--tool", "python=" + str(self.work / "unavailable checker"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.executed_count(), before)
        self.assertEqual((checked / "winner").read_bytes(), (repeated / "winner").read_bytes())


if __name__ == "__main__":
    unittest.main()
