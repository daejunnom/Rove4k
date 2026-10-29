"""Pure checks for the finite B/F header-cost experiment.

These fixtures are shell text and synthetic preprocessor observations. They do
not contain engine sources, replace source pins, invoke the producer, or run a
compiler, codec, native image, engine, or transposition table.
"""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("finite_header_cost_tests", HERE / "header_cost.py")
header_cost = importlib.util.module_from_spec(spec)
spec.loader.exec_module(header_cost)


CONTROL_HEADERS = {
    "B": (b'#!/bin/bash\nset -eo pipefail\nf=`mktemp`\n'
          b'tail -n+6 "$0"|xz -d|cc -std=c11 -Os -pthread -xc - -o"$f"\n'
          b'exec "$f"\n'),
    "F": (b'#!/bin/bash\nset -eo pipefail\nf=`mktemp`\n'
          b'tail -n+6 "$0"|xz -d|cc -Os -pthread -xc - -o"$f" -s\n'
          b'exec "$f"\n'),
}
SOURCE_PINS = {
    "B": dict(bytes=7934, sha256="09546a75f5e417125ec033994fec52b1e23da4d504e5146a54cead53966136ce"),
    "F": dict(bytes=7030, sha256="0aa062ec8440911d094a1b4eea48eceb96facfaa4ce94d654f46bfa19c83c7f0"),
}
PROFILES = ("test-p4", "test-p28", "tcec-provisional")
EXTENDED_CONTROL_PINS = {
    ("B", "test-p28"): {
        "source": (7962, "326e18b0b480a42c16ab0c4ec06ff90770842aec2bd8c9e1ea91f70be9427eb6"),
        "native": (25744, "755dffaf68cb2eff582260550f6c7a174bb09de9e5bf7a773f311c7c1dce9a24"),
        "header": (109, "579c456c8ca9af8acde4bc4a41307807bc85d76d11b56ec5fcdcaa7e304ed911"),
        "payload": (3972, "987817e100c9371abe9bcbbdc7507f507e5ba1259d8a57fe788d470a55599b27"),
        "whole": (4081, "93634a5bb12dcef46e7e80242982511de3ef62db1e60c70ee082b24186f30123"),
    },
    ("F", "test-p28"): {
        "source": (7063, "5a016f252e8efb4faf356de92397964d19e6c5e95863e063a5179864988dcdc5"),
        "native": (18568, "843bbc1ea78ef68c4cde578df93218f6d36b5f3c48cfa794ba6022b75e949262"),
        "header": (103, "de8e199aa72661012417d5a9004e3c4c5079d704d6558286bd282319c078a8a0"),
        "payload": (3499, "81905d60d0ba5f9ed48d307ad3281c503ec2c2099405f0c2c7dc40f9a1ab82ca"),
        "whole": (3602, "7c5b930a2a113a2cc294e97d56457896418f90b3df90eebfccba489b61342baa"),
    },
    ("B", "tcec-provisional"): {
        "source": (7936, "5f64922b49923ef9637dc41328761a4c3f4eb0063e39bd9f04c46e3d19c9b62d"),
        "native": (25744, "db780f8318783991535a56e3d26f3d9e18e3a139fdbd9f0ced56784f7f236613"),
        "header": (109, "579c456c8ca9af8acde4bc4a41307807bc85d76d11b56ec5fcdcaa7e304ed911"),
        "payload": (3963, "e680022b57423066591d73d18918b3edb71e9e72669240ca6613ff7b69b9b180"),
        "whole": (4072, "2f1cd9e6559594fa6142188df851c8ff6a8e57edd4de49c14fcdbbb67214f6b6"),
    },
    ("F", "tcec-provisional"): {
        "source": (7032, "7701b38ad0957066d427bb085575f26b511691a6ea60e67f44835ce9359db9df"),
        "native": (18568, "e536de10e8792573548864d6267e8ce3cde76102b6134552f9dbca0d2672437b"),
        "header": (103, "de8e199aa72661012417d5a9004e3c4c5079d704d6558286bd282319c078a8a0"),
        "payload": (3486, "90405436b74f2dc5e72a45340aff53b22a6c5845d8db40e4b62f890b268575b6"),
        "whole": (3589, "28f3f9024443b7dd63955b543ed2e6849905e1d0767a52c1d35ff51017889f30"),
    },
}
CONTROL_COMPILERS = {
    "B": ["cc", "-std=c11", "-Os", "-pthread", "-x", "c", "-", "-o", "x"],
    "F": ["cc", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s"],
}


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def macro_fixture(family, mode, *, minimal=False, replace=None, remove=()):
    macros = {
        "__GNUC__": "13" if mode == "producer" else "11",
        "__GNUC_MINOR__": "3" if mode == "producer" else "4",
        "__GLIBC__": "2",
        "__GLIBC_MINOR__": "39" if mode == "producer" else "35",
        "__STDC_VERSION__": "201112L" if family == "B" and not minimal else "201710L",
        "_POSIX_C_SOURCE": "200809L",
        "__x86_64__": "1",
        "__LP64__": "1",
        "_LP64": "1",
        "__SIZEOF_POINTER__": "8",
        "__SIZEOF_SIZE_T__": "8",
        "__SIZEOF_INT__": "4",
        "__SIZEOF_LONG__": "8",
        "__STDC_HOSTED__": "1",
    }
    if not minimal:
        macros["_REENTRANT"] = "1"
        if family == "B":
            macros["__STRICT_ANSI__"] = "1"
    macros.update(replace or {})
    for name in remove:
        macros.pop(name, None)
    return "".join(f"#define {name} {value}\n" for name, value in macros.items()).encode("ascii")


class HeaderCost(unittest.TestCase):
    def test_plan_keeps_the_two_original_full_p4_routes_and_five_control_pins(self):
        for family in "BF":
            for mode, gcc, os_version, libc, commands in (
                    ("producer", 13, "24.04", "2.39", 13),
                    ("replay", 11, "22.04", "2.35", 12)):
                with self.subTest(family=family, mode=mode):
                    plan = header_cost.plan(family, mode)
                    self.assertEqual((plan["family"], plan["profile"], plan["mode"]),
                                     (family, "test-p4", mode))
                    self.assertEqual(plan["cases"], ["control", "minimal"])
                    self.assertEqual(plan["compiler"], CONTROL_COMPILERS[family])
                    self.assertEqual(plan["minimal_compiler"],
                                     [arg for arg in CONTROL_COMPILERS[family]
                                      if arg not in ("-std=c11", "-pthread")])
                    self.assertEqual(plan["header_delta"], -18 if family == "B" else -9)
                    self.assertEqual(plan["expected_commands"], commands)
                    self.assertEqual((plan["GCC_major"], plan["os_version"], plan["libc"]),
                                     (gcc, os_version, libc))
                    self.assertEqual(set(plan["control"]),
                                     {"source", "native", "header", "payload", "whole"})
                    self.assertEqual(plan["control"]["source"], SOURCE_PINS[family])
                    self.assertEqual(plan["control"]["header"], pin(CONTROL_HEADERS[family]))
                    for part in plan["control"].values():
                        self.assertGreater(part["bytes"], 0)
                        self.assertRegex(part["sha256"], r"^[0-9a-f]{64}$")

    def test_six_profile_plans_keep_exact_original_parts_and_the_same_finite_schedule(self):
        self.assertEqual(set(header_cost.PROFILE_CONTROL),
                         {(family, profile) for family in "BF" for profile in PROFILES})
        for family in "BF":
            for mode in ("producer", "replay"):
                original = header_cost.plan(family, mode)
                for profile in PROFILES:
                    with self.subTest(family=family, mode=mode, profile=profile):
                        expected = dict(original, profile=profile)
                        if profile != "test-p4":
                            expected["control"] = {
                                name: dict(bytes=value[0], sha256=value[1])
                                for name, value in EXTENDED_CONTROL_PINS[family, profile].items()}
                        actual = header_cost.plan(family, mode, profile=profile)
                        self.assertEqual(actual, expected)
                        self.assertEqual(actual["expected_commands"], 13 if mode == "producer" else 12)
                        self.assertEqual(actual["control"]["header"], pin(CONTROL_HEADERS[family]))
                        self.assertFalse(actual["source_changed"])
                        self.assertFalse(actual["payload_recompressed"])

    def test_plan_rejects_other_families_modes_and_profile_like_inputs(self):
        for family, mode in (("A", "producer"), ("D", "producer"), ("F8", "producer"),
                             ("b", "producer"), ("B", "test-p28"), ("F", "tcec-provisional"),
                             ("F", ""), ("B", None)):
            with self.subTest(family=family, mode=mode), self.assertRaises(ValueError):
                header_cost.plan(family, mode)

    def test_profile_selection_rejects_unknown_values_and_booleans(self):
        for profile in ("test-p1", "test-p4 ", "TCEC-provisional", "", None, False, True):
            for family in "BF":
                for mode in ("producer", "replay"):
                    with self.subTest(family=family, mode=mode, profile=profile), self.assertRaises(ValueError):
                        header_cost.plan(family, mode, profile=profile)
                with self.subTest(family=family, profile=profile), self.assertRaises(ValueError):
                    header_cost.factory_argv(family, Path("outside-repository"), profile=profile)
                control = CONTROL_HEADERS[family]
                minimal = control.replace(b" -std=c11", b"").replace(b" -pthread", b"")
                with self.assertRaises(ValueError):
                    header_cost.candidate_header(control, minimal, family=family, profile=profile)
                with self.assertRaises(ValueError):
                    header_cost.macro_observation(family, "producer",
                        macro_fixture(family, "producer"), macro_fixture(family, "producer", minimal=True),
                        profile=profile)

    def test_factory_argv_preserves_reviewed_full_source_projections(self):
        expected_options = {"--entry", "--profile", "--representation", "--out",
                            "--b-variant", "--phase-variant", "--spelling-variant",
                            "--source-dependencies", "--ep-variant"}
        for family, selections in (
                ("B", ("tcec-final-lf", "control", "best")),
                ("F", ("control", "phase-init", "compound-v2"))):
            with self.subTest(family=family):
                output = Path("outside-repository") / family
                argv = header_cost.factory_argv(family, output)
                self.assertIsInstance(argv, list)
                self.assertNotIn("--execute", argv)
                self.assertEqual({arg for arg in argv if arg.startswith("--")}, expected_options)
                expected = dict(zip(("--b-variant", "--phase-variant", "--spelling-variant"), selections))
                expected.update({"--entry": family, "--profile": "test-p4",
                                 "--representation": "source-jit", "--out": str(output),
                                 "--source-dependencies": "unused-includes", "--ep-variant": "control"})
                for option, value in expected.items():
                    self.assertEqual(argv.count(option), 1)
                    self.assertEqual(argv[argv.index(option) + 1], value)

    def test_explicit_profile_changes_only_the_factory_profile_argument(self):
        for family in "BF":
            out = Path("outside-repository") / family
            original = header_cost.factory_argv(family, out)
            for profile in PROFILES:
                with self.subTest(family=family, profile=profile):
                    expected = list(original)
                    expected[expected.index("--profile") + 1] = profile
                    self.assertEqual(header_cost.factory_argv(family, out, profile=profile), expected)

    def test_header_change_is_exact_literal_removal_with_an_exact_inverse(self):
        for family, control in CONTROL_HEADERS.items():
            minimal = control.replace(b" -std=c11", b"").replace(b" -pthread", b"")
            self.assertEqual(header_cost.candidate_header(control, minimal, family=family), minimal)
            for profile in PROFILES:
                with self.subTest(family=family, profile=profile):
                    actual = header_cost.candidate_header(control, minimal, family=family, profile=profile)
                    self.assertEqual(actual, minimal)
                    self.assertEqual(actual.splitlines()[:3], control.splitlines()[:3])
                    self.assertEqual(actual.splitlines()[-1], b'exec "$f"')
                    self.assertEqual(len(actual.splitlines()), 5)
                    self.assertIn(b'tail -n+6 "$0"|xz -d|', actual)
                    self.assertEqual(len(actual) - len(control), -18 if family == "B" else -9)
                    flags = b"cc -std=c11 -Os -pthread -xc" if family == "B" else b"cc -Os -pthread -xc"
                    self.assertEqual(actual.replace(b"cc -Os -xc", flags, 1), control)

    def test_header_guard_rejects_changed_pipeline_boundaries_flags_and_control_pins(self):
        for family, control in CONTROL_HEADERS.items():
            minimal = control.replace(b" -std=c11", b"").replace(b" -pthread", b"")
            for changed in (control, minimal + b"\n", minimal.replace(b"tail -n+6", b"tail -n+5"),
                            minimal.replace(b"cc -Os", b"cc -O2"),
                            minimal.replace(b'set -eo pipefail', b'set -e'),
                            minimal.replace(b'exec "$f"', b'"$f"')):
                with self.subTest(family=family, candidate=changed), self.assertRaises(ValueError):
                    header_cost.candidate_header(control, changed, family=family)
            with self.assertRaises(ValueError):
                header_cost.candidate_header(control.replace(b"mktemp", b"mktemp -t x"),
                                             minimal, family=family)
            with self.assertRaises(ValueError):
                header_cost.candidate_header(control, minimal, family="A")

    def test_macro_parser_keeps_literal_values_for_selected_observations(self):
        self.assertEqual(header_cost.parse_macros(
            b'#define _POSIX_C_SOURCE 200809L\n#define __GNUC_MINOR__ 3\n'
            b'#define __VERSION__ "13.3.0"\n'),
            {"_POSIX_C_SOURCE": "200809L", "__GNUC_MINOR__": "3", "__VERSION__": '"13.3.0"'})

    def test_macro_parser_rejects_diagnostics_duplicates_and_wrong_byte_mode(self):
        for data in (b"", b"#define X 1\r\n", b"warning: diagnostic\n#define X 1\n",
                     b"#define X 1\n#define X 2\n", bytearray(b"#define X 1\n")):
            with self.subTest(data=data), self.assertRaises(ValueError):
                header_cost.parse_macros(data)

    def test_macro_observation_admits_only_the_expected_dialect_and_reentrant_changes(self):
        for family in "BF":
            for mode in ("producer", "replay"):
                old = macro_fixture(family, mode)
                new = macro_fixture(family, mode, minimal=True)
                original = header_cost.macro_observation(family, mode, old, new)
                for profile in PROFILES:
                    with self.subTest(family=family, mode=mode, profile=profile):
                        observed = header_cost.macro_observation(family, mode, old, new, profile=profile)
                        self.assertEqual(observed, original)
                        expected = {"_REENTRANT": {"control": "1", "minimal": None}}
                        if family == "B":
                            expected.update({"__STRICT_ANSI__": {"control": "1", "minimal": None},
                                             "__STDC_VERSION__": {"control": "201112L", "minimal": "201710L"}})
                        self.assertEqual(observed["differences"], expected)
                        for case, raw in (("control", old), ("minimal", new)):
                            selected = observed["selected"][case]
                            parsed = header_cost.parse_macros(raw)
                            for name, value in selected.items():
                                self.assertEqual(value, parsed.get(name))
                            self.assertEqual(selected["_POSIX_C_SOURCE"], "200809L")
                            self.assertIsNone(selected["_GNU_SOURCE"])
                            self.assertIsNone(selected["_DEFAULT_SOURCE"])

    def test_extra_macro_differences_are_diagnostic_and_do_not_claim_cpp_equality(self):
        for family in "BF":
            with self.subTest(family=family):
                observed = header_cost.macro_observation(family, "producer",
                    macro_fixture(family, "producer"),
                    macro_fixture(family, "producer", minimal=True,
                                  replace={"harmless_extra_macro": "1"}))
                self.assertEqual(observed["differences"]["harmless_extra_macro"],
                                 {"control": None, "minimal": "1"})
                self.assertNotIn("CPP_equal", observed)
                self.assertNotIn("native_equal", observed)

    def test_macro_guard_rejects_wrong_target_abi_features_and_dialect(self):
        for family in "BF":
            for mode in ("producer", "replay"):
                old = macro_fixture(family, mode)
                changes = ({"__GNUC__": "12"}, {"__GNUC_MINOR__": "unknown"},
                           {"__GLIBC__": "3"}, {"__GLIBC_MINOR__": "34"},
                           {"__x86_64__": "0"}, {"__SIZEOF_POINTER__": "4"},
                           {"__SIZEOF_SIZE_T__": "4"}, {"__SIZEOF_INT__": "8"},
                           {"__SIZEOF_LONG__": "4"}, {"__STDC_HOSTED__": "0"},
                           {"_POSIX_C_SOURCE": "199506L"}, {"__STDC_VERSION__": "201112L"},
                           {"_REENTRANT": "1"}, {"__STRICT_ANSI__": "1"},
                           {"_GNU_SOURCE": "1"}, {"_DEFAULT_SOURCE": "1"}, {"__cplusplus": "201703L"})
                for replacement in changes:
                    with self.subTest(family=family, mode=mode, replacement=replacement), self.assertRaises(ValueError):
                        header_cost.macro_observation(
                            family, mode, old, macro_fixture(family, mode, minimal=True, replace=replacement))
                with self.assertRaises(ValueError):
                    header_cost.macro_observation(family, mode,
                        macro_fixture(family, mode, remove=("_REENTRANT",)),
                        macro_fixture(family, mode, minimal=True))

    def test_synthetic_source_never_replaces_admitted_engine_source_pins(self):
        source = b"#define _POSIX_C_SOURCE 200809L\nint main(void){return 0;}\n"
        for family in "BF":
            with self.subTest(family=family), self.assertRaises(ValueError):
                header_cost.source_context(source, family=family)
            for profile in PROFILES:
                with self.subTest(family=family, profile=profile), self.assertRaises(ValueError):
                    header_cost.source_context(source, family=family, profile=profile)

    def test_ci_context_rejects_local_or_changed_repository_and_run_identity(self):
        env = dict(GITHUB_ACTIONS="true", GITHUB_REPOSITORY="daejunnom/Rove4k",
                   GITHUB_REPOSITORY_OWNER="daejunnom", GITHUB_SHA="a" * 40,
                   GITHUB_RUN_ID="7", GITHUB_RUN_ATTEMPT="1",
                   GITHUB_WORKFLOW="Experimental compiler header cost",
                   GITHUB_WORKFLOW_REF="daejunnom/Rove4k/.github/workflows/header-cost.yml@refs/pull/12/merge")
        context = header_cost.ci_context(env)
        self.assertEqual((context["repository"], context["owner"], context["sha"],
                          context["workflow"], context["workflow_ref"]),
                         (env["GITHUB_REPOSITORY"], env["GITHUB_REPOSITORY_OWNER"], env["GITHUB_SHA"],
                          env["GITHUB_WORKFLOW"], env["GITHUB_WORKFLOW_REF"]))
        self.assertEqual((int(context["run_id"]), int(context["run_attempt"])), (7, 1))
        changes = ({"GITHUB_ACTIONS": "false"}, {"GITHUB_REPOSITORY": "other/Rove4k"},
                   {"GITHUB_REPOSITORY_OWNER": "other"}, {"GITHUB_REPOSITORY_OWNER": ""},
                   {"GITHUB_SHA": "A" * 40}, {"GITHUB_SHA": "a" * 39},
                   {"GITHUB_RUN_ID": "0"}, {"GITHUB_RUN_ID": "-1"},
                   {"GITHUB_RUN_ATTEMPT": "not-a-number"}, {"GITHUB_RUN_ATTEMPT": "0"},
                   {"GITHUB_WORKFLOW": ""}, {"GITHUB_WORKFLOW": "Header cost"},
                   {"GITHUB_WORKFLOW_REF": ""},
                   {"GITHUB_WORKFLOW_REF": "daejunnom/Rove4k/.github/workflows/other.yml@refs/heads/main"},
                   {"GITHUB_WORKFLOW_REF": "other/Rove4k/.github/workflows/header-cost.yml@refs/heads/main"},
                   {"GITHUB_WORKFLOW_REF": "daejunnom/Rove4k/.github/workflows/header-cost.yml@refs/"},
                   {"GITHUB_WORKFLOW_REF": "daejunnom/Rove4k/.github/workflows/header-cost.yml@refs/heads/main\n"})
        for replacement in changes:
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                header_cost.ci_context(dict(env, **replacement))
        for missing in ("GITHUB_REPOSITORY_OWNER", "GITHUB_WORKFLOW_REF"):
            incomplete = dict(env)
            incomplete.pop(missing)
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                header_cost.ci_context(incomplete)
        with self.assertRaises(ValueError):
            header_cost.ci_context({})

    def test_inactive_measure_refuses_before_source_capture_or_output_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            for family in "BF":
                for mode in ("producer", "replay"):
                    for profile in PROFILES:
                        out = Path(temporary) / family / mode / profile / "not-created"
                        with mock.patch.object(header_cost, "capture", side_effect=AssertionError("source capture before opt-in")), \
                             mock.patch.object(Path, "mkdir", side_effect=AssertionError("output before opt-in")):
                            with self.assertRaises(ValueError):
                                header_cost.measure(family, out, mode=mode, profile=profile, execute=False)
                        self.assertFalse(out.exists())

    def test_invalid_profile_never_reaches_source_capture_even_with_execute_opt_in(self):
        with tempfile.TemporaryDirectory() as temporary:
            for profile in ("test-p1", None, False, True):
                out = Path(temporary) / "not-created"
                with mock.patch.object(header_cost, "capture", side_effect=AssertionError("invalid profile captured source")), \
                     mock.patch.object(Path, "mkdir", side_effect=AssertionError("invalid profile created output")):
                    with self.assertRaises(ValueError):
                        header_cost.measure("B", out, mode="producer", profile=profile, execute=True)
                self.assertFalse(out.exists())

    def test_cli_missing_execute_exits_before_measure_and_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            for profile in (None, *PROFILES):
                out = Path(temporary) / (profile or "default") / "not-created"
                argv = ["--entry", "B", "--mode", "producer", "--out", str(out)]
                if profile is not None:
                    argv.extend(["--profile", profile])
                with mock.patch.object(header_cost, "measure", side_effect=AssertionError("inactive CLI measured")), \
                     contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as failure:
                        header_cost.main(argv)
                self.assertEqual(failure.exception.code, 2)
                self.assertFalse(out.exists())

    def test_cli_explicit_profile_is_forwarded_without_measuring(self):
        for family in "BF":
            for mode in ("producer", "replay"):
                for profile in PROFILES:
                    with self.subTest(family=family, mode=mode, profile=profile):
                        out = Path("outside-repository") / family / mode / profile
                        producer = Path("outside-producer") if mode == "replay" else None
                        argv = ["--entry", family, "--mode", mode, "--profile", profile,
                                "--out", str(out), "--execute"]
                        if producer is not None:
                            argv.extend(["--producer", str(producer)])
                        with mock.patch.object(header_cost, "measure", return_value={
                                "complete": False, "whole_delta": -18 if family == "B" else -9}) as measure, \
                             contextlib.redirect_stdout(io.StringIO()):
                            header_cost.main(argv)
                        measure.assert_called_once_with(family, out, mode=mode, producer=producer,
                                                        profile=profile, execute=True)


if __name__ == "__main__":
    unittest.main()
