"""Small build-only trials; no peer or engine source is included."""
import lzma
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from . import peer_lzma1ext_trial as trial
except ImportError:
    import peer_lzma1ext_trial as trial


class Lzma1ExtTrialTests(unittest.TestCase):
    def test_parameter_validation_rejects_boolean_and_unsupported_values(self):
        for settings in (
            (True, 0, 0, lzma.MF_BT4, 128, 65536, 0),
            (3, 2, 0, lzma.MF_BT4, 128, 65536, 0),
            (2, 0, 5, lzma.MF_BT4, 128, 65536, 0),
            (2, 0, 0, 999, 128, 65536, 0),
            (2, 0, 0, lzma.MF_BT4, 128, 4095, 0),
            (2, 0, 0, lzma.MF_BT4, 128, 65537, 0),
        ):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                trial._parameters(*settings)

    def test_unsupported_helper_is_not_silently_used(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "helper"
            helper.write_bytes(b"fixed helper fixture")
            with patch.object(trial, "_run", return_value=(
                    b"header=5.2 runtime=5.2 header_number=50020000 "
                    b"runtime_number=50020000 ext=0\n")):
                with self.assertRaisesRegex(ValueError, "unavailable"):
                    trial.encode_verified(b"a", helper=helper, xz="xz")

    def test_oversize_or_nonbytes_fails_before_tool_access(self):
        for source in (bytearray(b"a"), b"x" * (trial.INPUT_LIMIT + 1)):
            with self.subTest(kind=type(source)), self.assertRaises(ValueError):
                trial.encode_verified(source, helper="not-opened", xz="xz")

    def test_invalid_header_and_nondeterministic_output_are_rejected(self):
        version = (b"header=5.4.0 runtime=5.4.0 header_number=50040002 "
                   b"runtime_number=50040002 ext=1\n")
        header = bytes([2]) + (65536).to_bytes(4, "little") + (1).to_bytes(8, "little")
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "helper"
            helper.write_bytes(b"fixed helper fixture")
            wrong_headers = (
                bytes([3]) + header[1:],
                header[:1] + (131072).to_bytes(4, "little") + header[5:],
                header[:5] + (2).to_bytes(8, "little"),
            )
            for wrong in wrong_headers:
                payload = wrong + b"synthetic"
                with self.subTest(header=wrong), patch.object(
                        trial, "_run", side_effect=[version, payload, payload]):
                    with self.assertRaisesRegex(ValueError, "header"):
                        trial.encode_verified(b"a", helper=helper, xz="xz", dict_size=65536)
            with patch.object(trial, "_run", side_effect=[version, header + b"a", header + b"b"]):
                with self.assertRaisesRegex(ValueError, "not reproducible"):
                    trial.encode_verified(b"a", helper=helper, xz="xz", dict_size=65536)

    def test_trailing_bytes_and_xz_mismatch_are_rejected(self):
        version = (b"header=5.4.0 runtime=5.4.0 header_number=50040002 "
                   b"runtime_number=50040002 ext=1\n")
        payload = bytes([2]) + (65536).to_bytes(4, "little") + (1).to_bytes(8, "little") + b"dummy"
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "helper"
            helper.write_bytes(b"fixed helper fixture")
            trailing = SimpleNamespace(decompress=lambda *_args, **_kwargs: b"a",
                                       eof=True, unused_data=b"trailing")
            with patch.object(trial, "_run", side_effect=[version, payload, payload]), \
                 patch.object(trial.lzma, "LZMADecompressor", return_value=trailing):
                with self.assertRaisesRegex(ValueError, "trailing"):
                    trial.encode_verified(b"a", helper=helper, xz="xz", dict_size=65536)
            clean = SimpleNamespace(decompress=lambda *_args, **_kwargs: b"a",
                                    eof=True, unused_data=b"")
            with patch.object(trial, "_run", side_effect=[version, payload, payload, b"xz version", b"bad"]), \
                 patch.object(trial.lzma, "LZMADecompressor", return_value=clean):
                with self.assertRaisesRegex(ValueError, "xz .lzma restore differs"):
                    trial.encode_verified(b"a", helper=helper, xz="xz", dict_size=65536)
            with patch.object(trial, "_run", side_effect=[
                    version, payload, payload, b"xz version", ValueError("xz failed")]), \
                 patch.object(trial.lzma, "LZMADecompressor", return_value=clean):
                with self.assertRaisesRegex(ValueError, "xz failed"):
                    trial.encode_verified(b"a", helper=helper, xz="xz", dict_size=65536)

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("cc") and shutil.which("xz"),
                         "requires Linux cc, liblzma headers and xz")
    def test_real_no_eos_streams_cross_restore_and_are_deterministic(self):
        source_path = Path(__file__).with_name("peer_lzma1ext_trial.c")
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "peer-lzma1ext"
            compile_result = subprocess.run(
                [shutil.which("cc"), "-std=c11", "-O2", "-Wall", "-Wextra",
                 str(source_path), "-llzma", "-o", str(helper)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr.decode(errors="replace"))
            version = subprocess.run([str(helper), "--version"], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, check=True).stdout
            match = trial._VERSION.fullmatch(version)
            self.assertIsNotNone(match)
            if match.group(5) == b"0":
                with self.assertRaisesRegex(ValueError, "unavailable"):
                    trial.encode_verified(b"a", helper=helper, xz=shutil.which("xz"), dict_size=65536)
                self.skipTest("the installed liblzma does not support LZMA1EXT")
            for source in (b"", b"synthetic chess source; " * 40, bytes(range(256))):
                with self.subTest(size=len(source)):
                    payload, receipt = trial.encode_verified(
                        source, helper=helper, xz=shutil.which("xz"), dict_size=65536)
                    self.assertEqual(int.from_bytes(payload[5:13], "little"), len(source))
                    self.assertEqual(receipt["input"]["bytes"], len(source))
                    self.assertEqual(receipt["payload"]["bytes"], len(payload))
                    self.assertTrue(receipt["repeatable_same_helper"])
                    self.assertFalse(receipt["independent_build_reproducible"])
                    self.assertFalse(receipt["helper_build_provenance_verified"])
                    self.assertTrue(receipt["python_and_xz_restore_verified"])
                    self.assertFalse(receipt["runtime_qualified"])
                    self.assertFalse(receipt["league_qualified"])
                    raw = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{
                        "id": lzma.FILTER_LZMA1, "dict_size": 65536,
                        "lc": 2, "lp": 0, "pb": 0,
                    }])
                    self.assertEqual(raw.decompress(payload[13:]), source)
                    self.assertFalse(raw.eof, "raw LZMA1 normally requires an end marker")
            for lc, lp, pb in ((2, 1, 0), (2, 0, 1)):
                with self.subTest(lc=lc, lp=lp, pb=pb):
                    _payload, receipt = trial.encode_verified(
                        b"synthetic positional source" * 8, helper=helper,
                        xz=shutil.which("xz"), dict_size=65536, lc=lc, lp=lp, pb=pb)
                    self.assertEqual((receipt["settings"]["lc"], receipt["settings"]["lp"],
                                      receipt["settings"]["pb"]), (lc, lp, pb))


if __name__ == "__main__":
    unittest.main()
