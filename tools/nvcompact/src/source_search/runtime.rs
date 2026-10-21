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
}

impl RunBudget {
    pub(super) fn new(options: &SourceSearchOptions) -> Self {
        Self {
            started: Instant::now(),
            evaluations: 0,
            maximum: options.max_evaluations,
            seconds: options.max_seconds,
            reason: None,
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
        if self.started.elapsed().as_secs_f64() >= self.seconds {
            self.reason = Some("scheduling-time-budget".into());
        }
        Ok(self
            .reason
            .as_deref()
            .is_none_or(|r| r == "complete-file-evaluation-budget"))
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
        if budget.evaluations + 1 >= budget.maximum {
            budget.reason = Some("complete-file-evaluation-budget".into());
            return Ok(None);
        }
        budget.evaluations += 1;
        let cost = measure(payload)?;
        self.costs.insert(hash, cost);
        Ok(Some((cost, false)))
    }
}
