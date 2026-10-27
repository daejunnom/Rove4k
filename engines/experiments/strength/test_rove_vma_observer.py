"""Bounded synthetic proc fixtures; no engine or privileged process starts."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

try:
    from . import rove_vma_observer as observer
except ImportError:
    import rove_vma_observer as observer


PID = 1234
START = 9321
MAPS = ("00001000-00002000 rw-p 00000000 00:00 0 \n"
        "00002000-00004000 rw-p 00000000 00:00 0 /path with spaces\n"
        "00005000-00006000 r--p 00000000 00:00 0 \n")
NUMA = ("1000 default anon=2 N0=2 kernelpagesize_kB=4\n"
        "2000 default anon=3 N1=3 kernelpagesize_kB=2048\n"
        "5000 default\n")


def process_stat(start=START, *, state="S", pgid=77, session=77):
    fields = [state, "1", str(pgid), str(session)] + ["0"] * 15 + [str(start)]
    return f"{PID} (a name ) with parens) " + " ".join(fields) + "\n"


class VmaObservation(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.proc = Path(self.temporary.name)
        self.root = self.proc / str(PID)
        self.root.mkdir()
        self.write("stat", process_stat())
        self.write("maps", MAPS)
        self.write("numa_maps", NUMA)

    def write(self, name, text):
        (self.root / name).write_text(text, encoding="utf-8")

    def observe(self, **kwargs):
        args = dict(expected_start_ticks=START, address=0x1800, length=0x1800,
                    allowed_nodes=[0, 1], proc=self.proc)
        args.update(kwargs)
        return observer.observe_range(PID, **args)

    def test_partial_multi_vma_range_retains_raw_pages_and_limitations(self):
        result = self.observe()
        self.assertEqual(result["owner"], {"pid": PID, "pgid": 77, "session": 77, "start_ticks": START})
        self.assertEqual([x["start"] for x in result["mappings"]], [0x1000, 0x2000])
        self.assertEqual(result["mappings"][1]["path"], "/path with spaces")
        self.assertEqual([x["node_pages"] for x in result["vmas"]], [{0: 2}, {1: 3}])
        self.assertEqual(result["observed_page_nodes"], [0, 1])
        self.assertTrue(result["source"]["fixture"])
        self.assertTrue(result["all_mapping_starts_observed"])
        self.assertTrue(all(value is False for value in result["claims"].values()))
        self.assertIn("whole VMAs", result["scope"])

    def test_missing_node_counts_are_not_zero_residency_proof(self):
        self.write("numa_maps", "1000 default\n2000 default\n5000 default\n")
        result = self.observe()
        self.assertEqual(result["observed_page_nodes"], [])
        self.assertEqual([x["node_pages"] for x in result["vmas"]], [{}, {}])
        self.assertFalse(any(x["page_count_fields_present"] for x in result["vmas"]))
        self.assertFalse(result["claims"]["tt_only_residency"])

    def test_range_validation_rejects_overflow_bad_nodes_and_booleans(self):
        for options in ({"address": 0}, {"length": 0}, {"address": (1 << 64) - 1, "length": 2},
                        {"address": True}, {"allowed_nodes": []}, {"allowed_nodes": [0, 0]},
                        {"allowed_nodes": [True]}, {"expected_start_ticks": START + 1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.observe(**options)

    def test_gap_shared_and_nonwritable_mapping_are_rejected(self):
        for changed in (MAPS.replace("00002000-00004000", "00002100-00004000"),
                        MAPS.replace("00002000-00004000 rw-p", "00002000-00004000 rw-s"),
                        MAPS.replace("00002000-00004000 rw-p", "00002000-00004000 r--p")):
            with self.subTest(changed=changed):
                self.write("maps", changed)
                with self.assertRaises(ValueError):
                    self.observe()

    def test_numamap_missing_duplicate_malformed_and_foreign_nodes_rejected(self):
        bad = ("1000 default N0=2\n5000 default\n",
               "1000 default N0=2\n1000 default N0=3\n2000 default N1=3\n",
               "1000 default N0=2 N0=3\n2000 default N1=3\n",
               "1000 default N0=-1\n2000 default N1=3\n",
               "1000 default N02=1\n2000 default N1=3\n",
               "1000 default N2=1\n2000 default N1=3\n")
        for content in bad:
            with self.subTest(content=content):
                self.write("numa_maps", content)
                with self.assertRaises(ValueError):
                    self.observe()

    def test_same_owner_mapping_change_is_rejected(self):
        original = observer._read
        counts = {"maps": 0}
        def changing(path, limit):
            if path.name == "maps":
                counts["maps"] += 1
                if counts["maps"] == 2:
                    return MAPS.replace("/path with spaces", "/different file").encode()
            return original(path, limit)
        with mock.patch.object(observer, "_read", side_effect=changing):
            with self.assertRaisesRegex(ValueError, "changed"):
                self.observe()

    def test_owner_replacement_or_exit_during_observation_rejected(self):
        original = observer._read
        for replacement in (process_stat(start=START + 1), process_stat(state="Z"), process_stat(pgid=78)):
            counts = {"stat": 0}
            def changing(path, limit):
                if path.name == "stat":
                    counts["stat"] += 1
                    if counts["stat"] == 2:
                        return replacement.encode()
                return original(path, limit)
            with self.subTest(replacement=replacement), mock.patch.object(observer, "_read", side_effect=changing):
                with self.assertRaises(ValueError):
                    self.observe()

    def test_unknown_or_unreadable_proc_observation_is_not_success(self):
        (self.root / "numa_maps").unlink()
        with self.assertRaises(OSError):
            self.observe()


if __name__ == "__main__":
    unittest.main()
