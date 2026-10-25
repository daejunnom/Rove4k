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
