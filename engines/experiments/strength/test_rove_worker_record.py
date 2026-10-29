import copy
import hashlib
import json
import unittest

from rove_worker_record import inspect_worker_records


class WorkerRecordTests(unittest.TestCase):
    def setUp(self):
        self.artifact = {"id": "fixture", "profile": "test-p16", "workers": 16}
        self.source = "a" * 64
        self.candidate = "b" * 64
        self.report = {"format": "rove4k-owned-lifecycle-v1", "profile": "test-p16",
                       "artifact": self.artifact, "source_sha256": self.source,
                       "candidate_set_sha256": self.candidate,
                       "slot": {"cpus": list(range(16))}, "sessions": []}
        for label, pid in (("cold", 1000), ("warm", 2000)):
            tids = list(range(pid + 1, pid + 17))
            obs = [{"tid": tid, "start_ticks": tid * 2, "cpus": list(range(16)),
                    "cpu_ticks_first": 3, "cpu_ticks_last": 4} for tid in tids]
            self.report["sessions"].append({"label": label, "complete": True,
                "owner_identity": {"pid": pid, "pgid": pid, "session": pid, "start_ticks": pid},
                "search": {"label": label, "worker_ids": tids,
                           "positive_cpu_worker_ids": tids[:],
                           "worker_affinity_evidence": obs,
                           "worker_affinity_evidence_complete": True}})

    def inspect(self, report=None, *, digest=None, artifact=None, source=None):
        raw = json.dumps(self.report if report is None else report).encode()
        return inspect_worker_records(raw, expected_sha256=digest or hashlib.sha256(raw).hexdigest(),
            expected_artifact=artifact or self.artifact, expected_source_sha256=source or self.source,
            expected_candidate_sha256=self.candidate)

    def test_record_consistency_never_claims_actual_origin_or_qualification(self):
        result = self.inspect()
        self.assertTrue(result["recorded_searches_consistent"])
        for key in ("host_authenticated", "source_authenticated", "complete_worker_set_proven",
                    "tt_provenance_proven", "smt_qualification", "score_authorized"):
            self.assertIs(result[key], False)

    def test_independent_pins_required(self):
        for kwargs in ({"digest": "0" * 64}, {"source": "0" * 64},
                       {"artifact": {"id": "different"}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.inspect(**kwargs)

    def test_faults_do_not_pass(self):
        for fault in ("affinity", "no_progress", "missing", "tid_reuse", "duplicate_session",
                      "wrong_workers", "invalid_slot", "bool_tick", "incomplete"):
            report = copy.deepcopy(self.report)
            row = report["sessions"][0]
            search = row["search"]
            if fault == "affinity":
                search["worker_affinity_evidence"][0]["cpus"] = [0]
            elif fault == "no_progress":
                search["worker_affinity_evidence"][0]["cpu_ticks_last"] = 3
            elif fault == "missing":
                search["worker_affinity_evidence"].pop()
            elif fault == "tid_reuse":
                report["sessions"][1]["owner_identity"] = copy.deepcopy(row["owner_identity"])
            elif fault == "duplicate_session":
                report["sessions"].append(copy.deepcopy(row))
            elif fault == "wrong_workers":
                search["positive_cpu_worker_ids"].pop()
            elif fault == "invalid_slot":
                report["slot"]["cpus"][-1] = 0
            elif fault == "bool_tick":
                search["worker_affinity_evidence"][0]["cpu_ticks_first"] = True
            else:
                row["complete"] = False
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                self.inspect(report)

    def test_duplicate_keys_rejected_even_when_hash_matches(self):
        raw = b'{"format":"x","format":"rove4k-owned-lifecycle-v1"}'
        with self.assertRaises(ValueError):
            inspect_worker_records(raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
                expected_artifact=self.artifact, expected_source_sha256=self.source,
                expected_candidate_sha256=self.candidate)


if __name__ == "__main__":
    unittest.main()
