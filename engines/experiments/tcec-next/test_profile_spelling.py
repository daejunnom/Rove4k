"""Focused non-executing admission tests for the explicit production option."""
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

build=load("spelling_policy_build",HERE/"profile_build.py")
spelling=load("spelling_policy_helper",HERE/"profile_spelling.py")

class SpellingPolicy(unittest.TestCase):
    def test_scan_default_preserves_controls_and_explicit_domain(self):
        args=build.argument_parser().parse_args(["--entry","A","--profile","test-p4","--out","/new"])
        self.assertEqual(args.scan_variant,"control")
        self.assertIsNone(build.scan_selection("F","packed-native","control",None,"control","control"))
        for family in "AC":
            self.assertEqual(build.scan_selection(family,"source-jit","phase-init",build.COMPOUND_DECLARATION,
                "unused-includes","square-successor"),build.SCAN_DECLARATION)
        for family,representation,phase,spelling,dependencies in (
            ("B","source-jit","phase-init",build.COMPOUND_DECLARATION,"unused-includes"),
            ("A","packed-native","phase-init",build.COMPOUND_DECLARATION,"unused-includes"),
            ("C","source-jit","control",build.COMPOUND_DECLARATION,"unused-includes"),
            ("A","source-jit","phase-init",None,"unused-includes"),
            ("C","source-jit","phase-init",build.COMPOUND_DECLARATION,"control")):
            with self.assertRaises(ValueError):
                build.scan_selection(family,representation,phase,spelling,dependencies,"square-successor")

    def test_scan_policy_has_exact_six_contexts_without_changing_old_maps(self):
        scan=load("spelling_policy_scan",HERE/"profile_scan.py")
        self.assertEqual(set(build.SCAN_IMAGES),set(scan.POST_DEPENDENCY_OUTPUTS))
        for key,row in build.SCAN_IMAGES.items():
            self.assertEqual(row[:2],scan.POST_DEPENDENCY_OUTPUTS[key])
        for family in "AC":
            compiler=["cc","-Os",*(["-mavx2"] if family=="C" else []),"-x","c","-","-o","x","-s"]
            with self.assertRaisesRegex(ValueError,"final source"):
                build.scan_native_policy(family,"test-p4",build.SCAN_DECLARATION,b"wrong",compiler,compiler,build.SCAN_COMPILER_VERSION)
            with self.assertRaisesRegex(ValueError,"six-context"):
                build.scan_native_policy(family,"test-p4",build.SCAN_DECLARATION,b"wrong",compiler,["gcc-11",*compiler[1:]],build.SCAN_COMPILER_VERSION)
        self.assertIsNone(build.scan_native_policy("F","test-p4",None,b"",[],[],""))

    def test_merged_cli_keeps_independent_defaults(self):
        parsed=build.argument_parser().parse_args(["--entry","C","--profile","test-p4","--out","/example/new"])
        self.assertEqual(parsed.spelling_variant,"control")
        self.assertEqual(parsed.source_dependencies,"unused-includes")

    def test_merged_cli_allows_explicit_control_and_best_together(self):
        parsed=build.argument_parser().parse_args(["--entry","C","--profile","test-p4","--out","/example/new",
            "--phase-variant","phase-init","--spelling-variant","best","--source-dependencies","control"])
        self.assertEqual(parsed.source_dependencies,"control")
        self.assertEqual(build.spelling_selection(parsed.entry,parsed.representation,parsed.b_variant,
            parsed.phase_variant,parsed.spelling_variant)["variant"],"clock-type")

    def test_controls_have_no_stage(self):
        for family in "ABCEF":
            for representation in ("source-jit","packed-native","self-contained-elf"):
                self.assertIsNone(build.spelling_selection(family,representation,"control","control","control"))

    def test_selected_family_specific_minima(self):
        for family,variant in (("A","clock-type"),("B","atomic-assignment"),("C","clock-type"),
                               ("E","clock-type"),("F","atomic-assignment")):
            selected=build.spelling_selection(family,"source-jit",
                "tcec-final-lf" if family=="B" else "control",
                "control" if family=="B" else "phase-init","best")
            self.assertEqual(selected,{"path":build.SPELLING,"selection":"best","variant":variant})
            self.assertIn(variant,spelling.available(family))

    def test_compound_is_an_alternative_slot_and_b_is_existing_best(self):
        for family in "ABCEF":
            selected=build.spelling_selection(family,"source-jit",
                "tcec-final-lf" if family=="B" else "control",
                "control" if family=="B" else "phase-init","compound")
            expected=({"path":build.SPELLING,"selection":"best","variant":"atomic-assignment"}
                      if family=="B" else build.COMPOUND_DECLARATION)
            self.assertEqual(selected,expected)
            if family=="B":self.assertNotEqual(selected["path"],build.COMPOUND)
        parsed=build.argument_parser().parse_args(["--entry","F","--profile","test-p4",
            "--out","/example/new","--phase-variant","phase-init","--spelling-variant","compound"])
        self.assertEqual(parsed.spelling_variant,"compound")
        self.assertEqual(parsed.source_dependencies,"unused-includes")

    def test_compound_cannot_bypass_route_or_representation(self):
        for family,b,phase,representation in (("A","control","control","source-jit"),
            ("B","control","control","source-jit"),("F","control","phase-init","packed-native"),
            ("C","control","phase-init","self-contained-elf")):
            with self.assertRaises(ValueError):
                build.spelling_selection(family,representation,b,phase,"compound")

    def test_new_native_policy_is_only_for_f_compound(self):
        self.assertIsNone(build.compound_native_policy("A","test-p4",build.COMPOUND_DECLARATION,
            b"different",[],[],"other compiler"))
        old=build.spelling_selection("F","source-jit","control","phase-init","best")
        self.assertIsNone(build.compound_native_policy("F","test-p4",old,b"different",[],[],"other compiler"))

    def test_f_compound_rejects_alternate_compiler_and_unpinned_final_source(self):
        compiler=list(build.F_COMPOUND_COMPILER)
        for executor,version in ((["/usr/bin/gcc-11",*compiler[1:]],build.F_COMPOUND_COMPILER_VERSION),
                (compiler,"cc (different) 13.3.0")):
            with self.assertRaisesRegex(ValueError,"named GCC13"):
                build.compound_native_policy("F","test-p4",build.COMPOUND_DECLARATION,
                    b"not the admitted source",compiler,executor,version)
        with self.assertRaisesRegex(ValueError,"final source"):
            build.compound_native_policy("F","test-p4",build.COMPOUND_DECLARATION,
                b"not the admitted source",compiler,compiler,build.F_COMPOUND_COMPILER_VERSION)

    def test_non_source_representation_rejected(self):
        for representation in ("packed-native","self-contained-elf","unknown"):
            with self.assertRaises(ValueError):
                build.spelling_selection("A",representation,"control","phase-init","best")

    def test_control_or_different_post_route_rejected(self):
        for family,b,phase in (("A","control","control"),("E","control","control"),
            ("F","control","control"),("B","control","control"),("B","tcec-final-7","control"),
            ("B","tcec-final-lf","phase-init"),("A","tcec-final-lf","phase-init")):
            with self.assertRaises(ValueError):
                build.spelling_selection(family,"source-jit",b,phase,"best")

    def test_unknown_family_or_selection_rejected(self):
        for family,selection in (("D","best"),("F8","best"),("A","clock-type"),("A","unknown")):
            with self.assertRaises(ValueError):
                build.spelling_selection(family,"source-jit","control","phase-init",selection)

    def test_exact_proof_domain(self):
        self.assertEqual(set(spelling.INPUTS),{(family,profile) for family in "ABCEF"
            for profile in ("test-p4","test-p28","tcec-provisional")})
        self.assertEqual(len(spelling.VARIANTS),8)

    def test_nonpinned_source_rejected_before_parsing(self):
        for family in "ABCEF":
            for variant in spelling.available(family):
                with self.assertRaises(ValueError):
                    spelling.transform_source(b"int main(void){return 0;}\n",family=family,
                        profile_id="test-p4",variant=variant)

    def test_nonpinned_output_rejected(self):
        with self.assertRaises(ValueError):
            spelling.restore_source(b"changed",{"schema":spelling.SCHEMA,"output":{"bytes":7,"sha256":"wrong"}})

if __name__=="__main__":unittest.main()
