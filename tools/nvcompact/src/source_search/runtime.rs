//! Per-run resource ownership for source search. Scheduling, retained evidence
//! and measured payload costs have separate lifetimes and failure boundaries.

use super::{SourceSearchOptions, MAX_RECORDS, MAX_REPORT_BYTES};
use crate::{attempts::Archive, notation::Variant, process, sha256};
use anyhow::{ensure, Result};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::Instant;

pub(super) struct RunBudget {
    pub(super) started: Instant,
    pub(super) evaluations: usize,
    pub(super) maximum: usize,
    pub(super) seconds: f64,
    pub(super) reason: Option<String>,
    pub(super) fresh_reservations: usize,
}

/// Created only at a scheduling boundary. It authorizes completion of that
/// candidate's bounded proof, never the start of another candidate after a
/// deadline. Retention failures and cancellation still revoke the permission.
pub(super) struct StartedCandidate(());

/// A scheduling quantum limits new work, not in-flight compiler/codec work.
/// Unused work remains in its lazy queue for the final work-conserving pass.
pub(super) struct WorkWindow {
    evaluation_ceiling: usize,
    elapsed_ceiling: f64,
}

impl WorkWindow {
    pub(super) fn stop(&self, budget: &RunBudget) -> Option<&'static str> {
        if budget.evaluations >= self.evaluation_ceiling {
            Some("phase-evaluation-quantum")
        } else if budget.started.elapsed().as_secs_f64() >= self.elapsed_ceiling {
            Some("phase-time-quantum")
        } else {
            None
        }
    }

    pub(super) fn describe(&self) -> Value {
        json!({"evaluation_ceiling":self.evaluation_ceiling,
            "elapsed_seconds_ceiling":self.elapsed_ceiling,
            "scope":"new candidate starts; an already started bounded candidate may finish"})
    }
}

impl RunBudget {
    pub(super) fn new(options: &SourceSearchOptions) -> Self {
        Self {
            started: Instant::now(),
            evaluations: 0,
            maximum: options.max_evaluations,
            seconds: options.max_seconds,
            reason: None,
            fresh_reservations: 1,
        }
    }

    pub(super) fn cancelled(&self) -> Result<()> {
        ensure!(!process::cancelled(), "source search cancelled");
        Ok(())
    }

    pub(super) fn available(&mut self) -> Result<bool> {
        self.cancelled()?;
        if self.reason.is_none() && self.started.elapsed().as_secs_f64() >= self.seconds {
            self.reason = Some("scheduling-time-budget".into());
        }
        Ok(self.reason.is_none())
    }

    pub(super) fn verification_available(&mut self) -> Result<bool> {
        self.cancelled()?;
        if self
            .reason
            .as_deref()
            .is_none_or(|r| r == "complete-file-evaluation-budget")
            && self.started.elapsed().as_secs_f64() >= self.seconds
        {
            self.reason = Some("scheduling-time-budget".into());
        }
        Ok(self
            .reason
            .as_deref()
            .is_none_or(|r| r == "complete-file-evaluation-budget"))
    }

    pub(super) fn start_candidate(&mut self) -> Result<Option<StartedCandidate>> {
        Ok(self.available()?.then_some(StartedCandidate(())))
    }

    pub(super) fn completion_available(&self, _: &StartedCandidate) -> Result<bool> {
        self.cancelled()?;
        Ok(self.reason.as_deref().is_none_or(|r| {
            matches!(
                r,
                "complete-file-evaluation-budget" | "scheduling-time-budget"
            )
        }))
    }

    pub(super) fn share(&self, remaining_phases: usize) -> WorkWindow {
        let elapsed = self.started.elapsed().as_secs_f64();
        let available = self
            .maximum
            .saturating_sub(self.evaluations + self.fresh_reservations);
        WorkWindow {
            evaluation_ceiling: self.evaluations + available.div_ceil(remaining_phases),
            elapsed_ceiling: elapsed + (self.seconds - elapsed).max(0.0) / remaining_phases as f64,
        }
    }

    pub(super) fn reserve_priority_seed(&mut self) -> bool {
        // Keep legacy priority exploration untouched. Only deferred exploration
        // pays for retaining both its input winner and a possibly different
        // final winner. At least one new cost must remain after both readbacks.
        if self.maximum.saturating_sub(self.evaluations) > self.fresh_reservations + 1 {
            self.fresh_reservations += 1;
            true
        } else {
            if self.reason.is_none() {
                self.reason = Some("priority-seed-evaluation-reservation".into());
            }
            false
        }
    }
}

pub(super) struct EvidenceJournal {
    pub(super) archive: Archive,
    pub(super) records: Vec<Value>,
    pub(super) record_bytes: usize,
    pub(super) retention_stop: Option<Value>,
}

impl EvidenceJournal {
    pub(super) fn new(archive: Archive) -> Self {
        Self {
            archive,
            records: Vec::new(),
            record_bytes: 0,
            retention_stop: None,
        }
    }

    pub(super) fn record(&mut self, budget: &mut RunBudget, value: Value) -> Result<bool> {
        budget.cancelled()?;
        let bytes = serde_json::to_vec(&value)?.len();
        if self.records.len() >= MAX_RECORDS
            || bytes > MAX_REPORT_BYTES.saturating_sub(self.record_bytes)
        {
            // Unlike exhaustion of new cost measurements, losing the ability
            // to retain evidence also stops verification of measured singles.
            budget.reason = Some("report-memory-budget".into());
            // Keep one bounded emergency receipt on disk. A large unretained
            // derivation cannot be measured or admitted after this boundary.
            if self.retention_stop.is_none() {
                let detail = if bytes <= 65536 {
                    value.clone()
                } else {
                    json!({"stage":value["stage"],"round":value["round"],
                        "id":value["id"],"unretained_record_bytes":bytes,
                        "unretained_record_sha256":sha256(&serde_json::to_vec(&value)?)})
                };
                let stop = json!({"stage":"retention-capacity-stop","reason":"report-memory-budget",
                    "last_observation":detail,"candidate_not_admitted":true});
                self.archive.append(&stop)?;
                self.retention_stop = Some(stop);
            }
            return Ok(false);
        }
        self.archive.append(&value)?;
        self.record_bytes += bytes;
        self.records.push(value);
        Ok(true)
    }

    pub(super) fn candidate(
        &mut self,
        budget: &mut RunBudget,
        stage: &str,
        round: usize,
        base: &[u8],
        variant: &Variant,
    ) -> Result<bool> {
        ensure!(
            sha256(&variant.data) == variant.sha256 && variant.data.len() == variant.bytes,
            "candidate snapshot differs from its derivation identity"
        );
        if !self.archive.source(base)? || !self.archive.source(&variant.data)? {
            budget.reason = Some("retained-source-byte-budget".into());
            let stop = json!({"stage":"retention-capacity-stop","reason":budget.reason,"round":round,
                "id":variant.id,"source_sha256":variant.sha256,"source_bytes":variant.bytes,
                "base_source_sha256":sha256(base),"unretained_candidate":true,
                "retained":"last fully verified incumbent; remaining generated candidates not explored"});
            self.retention_stop = Some(stop.clone());
            self.record(budget, stop)?;
            return Ok(false);
        }
        self.record(
            budget,
            json!({"stage":stage,"round":round,"variant":variant,
                "base_source_sha256":sha256(base)}),
        )
    }
}

/// Complete-payload cost reuse is confined to one search run with one fixed
/// objective. It supplies no semantic acceptance or fresh final reproduction.
pub(super) struct CostMemo {
    pub(super) costs: HashMap<String, usize>,
}

impl CostMemo {
    pub(super) fn new() -> Self {
        Self {
            costs: HashMap::new(),
        }
    }

    /// The caller charges and independently measures the original payload
    /// before seeding its known cost; this insertion consumes no evaluation.
    pub(super) fn insert_baseline(&mut self, payload: &[u8], cost: usize) {
        self.costs.insert(sha256(payload), cost);
    }

    pub(super) fn measure(
        &mut self,
        budget: &mut RunBudget,
        payload: &[u8],
        measure: &mut impl FnMut(&[u8]) -> Result<usize>,
    ) -> Result<Option<(usize, bool)>> {
        let hash = sha256(payload);
        if let Some(&cost) = self.costs.get(&hash) {
            return Ok(Some((cost, true)));
        }
        if !budget.available()? {
            return Ok(None);
        }
        // Reserve the last allowed measurement for fresh final-cost readback.
        // A one-evaluation request therefore returns the measured raw input.
        if budget.evaluations + budget.fresh_reservations >= budget.maximum {
            budget.reason = Some("complete-file-evaluation-budget".into());
            return Ok(None);
        }
        budget.evaluations += 1;
        let cost = measure(payload)?;
        self.costs.insert(hash, cost);
        Ok(Some((cost, false)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn started_candidate_can_finish_after_deadline_but_strong_stops_win() {
        let mut budget = RunBudget::new(&SourceSearchOptions::default());
        let started = budget.start_candidate().unwrap().unwrap();
        budget.started = Instant::now() - Duration::from_secs(301);
        assert!(!budget.available().unwrap());
        assert!(budget.completion_available(&started).unwrap());
        assert!(budget.start_candidate().unwrap().is_none());
        for reason in [
            "report-memory-budget",
            "retained-source-byte-budget",
            "frontend-output-budget",
        ] {
            budget.reason = Some(reason.into());
            assert!(!budget.verification_available().unwrap());
            assert!(!budget.completion_available(&started).unwrap());
            assert_eq!(budget.reason.as_deref(), Some(reason));
        }
    }

    #[test]
    fn extra_seed_reservation_does_not_take_a_legacy_priority_measurement() {
        let mut budget = RunBudget::new(&SourceSearchOptions::default());
        budget.maximum = 4;
        budget.evaluations = 2;
        assert_eq!(budget.fresh_reservations, 1);
        assert!(!budget.reserve_priority_seed());
        assert_eq!(budget.fresh_reservations, 1);
        budget.reason = None;
        budget.maximum = 5;
        assert!(budget.reserve_priority_seed());
        assert_eq!(budget.fresh_reservations, 2);
        assert_eq!(budget.evaluations, 2);
    }
}
