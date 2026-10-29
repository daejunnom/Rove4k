"""Diagnostic consumption of a cohort peak receipt; never an admission.

The caller supplies context from an independent authority, not the receipt.
The receipt's own digest is only an integrity check, not an authentication
mechanism. Even a well-formed, matching receipt may have been fabricated.
"""
from __future__ import annotations

try:
    from . import overhead
except ImportError:
    import overhead


_UNPROVEN = (
    "artifact_source_provenance_verified", "all_tt_resident_verified",
    "representative_search_workload_verified", "future_peak_bound_verified",
    "external_cgroup_writer_excluded", "process_charges_complete",
    "executable_continuity_verified", "observer_loaded_source_verified",
    "observer_and_external_system_charges_included", "physical_topology_verified",
    "simultaneous_cohort_presence_verified", "runtime_admission", "scored_qualification",
)
_CONTEXT = {
    "profile", "plan", "boot_id", "cgroup_root", "controller_cgroup_path",
    "runner_sha256", "controller_sha256", "observer_source_sha256",
    "now_monotonic_ns", "max_age_ns",
}


def inspect_diagnostic(report, *, expected):
    """Validate receipt integrity/context and return diagnostic-only metadata.

    Expected fields must originate independently; obtaining them from report
    merely checks a receipt against itself. No values are output for memory
    preflight, and no evidence of authenticity or actual owner is asserted.
    """
    if type(expected) is not dict or set(expected) != _CONTEXT:
        raise ValueError("independent expected receipt context is required")
    checked = overhead.inspect_report(report, **expected)
    if report.get("test_inputs") is not False:
        raise ValueError("synthetic observation cannot be recorded as live diagnostic")
    if any(report.get(key) is not False for key in _UNPROVEN):
        raise ValueError("diagnostic observation claims unsupported qualification")
    if report.get("game_groups_empty_observed") is not True or report.get("controller_cleanup_observed") is not False:
        raise ValueError("observation lifecycle is incomplete or misrepresented")
    plan = expected["plan"]
    count = 11 if expected["profile"] == "test-p16" else 1
    if (len(plan) != count or any(type(row) is not dict or
            set(row) != {"slot", "cgroup_path", "cpus", "nodes", "artifacts"} or
            type(row["slot"]) is not str or not row["slot"] or
            type(row["artifacts"]) is not list or len(row["artifacts"]) != 2 for row in plan)):
        raise ValueError("expected cohort plan is incomplete")
    slots = {row["slot"] for row in plan}
    samples, finished = report.get("samples"), report.get("finished_game_groups")
    if (len(slots) != count or type(samples) is not list or not 1 <= len(samples) <= 64 or
            type(finished) is not list or len(finished) != count or
            any(type(row) is not dict or row.get("slot") not in slots for row in finished) or
            len({row["slot"] for row in finished}) != count or
            any(type(sample) is not dict or type(sample.get("games")) is not list or
                len(sample["games"]) != count or
                any(type(row) is not dict or row.get("slot") not in slots for row in sample["games"]) or
                len({row["slot"] for row in sample["games"]}) != count for sample in samples)):
        raise ValueError("diagnostic receipt is missing complete cohort observations")
    if checked.get("authenticated") is not False or checked.get("actual_owner_verified") is not False:
        raise ValueError("diagnostic integrity cannot authenticate an observer")
    return {
        "format": "rove4k-peak-receipt-diagnostic-v1",
        "profile": expected["profile"],
        "observation_sha256": report["observation_sha256"],
        "integrity_and_expected_context_match": True,
        "authenticated": False,
        "actual_owner_verified": False,
        "artifact_source_provenance_verified": False,
        "all_tt_resident_verified": False,
        "representative_search_workload_verified": False,
        "future_peak_bound_verified": False,
        "runtime_admission": False,
        "scored_qualification": False,
    }


def record_diagnostic(append, report, *, expected):
    """Record diagnostic metadata only; never change scoring or budget state."""
    if not callable(append):
        raise TypeError("a journal append callable is required")
    result = inspect_diagnostic(report, expected=expected)
    append("campaign.memory_peak_diagnostic", result)
    return result
