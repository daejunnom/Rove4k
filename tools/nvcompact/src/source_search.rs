//! Measured C-source search inside a declared, byte-preserved payload adapter.
//!
//! Source length and native-code identity are deliberately different costs.
//! Spelling candidates retain their own source hashes even when their complete
//! native images agree. Only a smaller complete-file cost can advance the
//! incumbent; typed source checks and the actual compiler gate precede adoption.
use crate::cflow;
use crate::csource::{self, CSourceOptions};
use crate::envelope::native_fingerprint;
use crate::notation::Variant;
use crate::process::{self, Limits};
use crate::source_payload::PayloadAdapter;
use crate::{sha256, write_json};
use anyhow::{bail, ensure, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

const SCHEMA: &str = "nvcompact-source-search-v1";
const MAX_RECORDS: usize = 32768;
const MAX_REPORT_BYTES: usize = 32 << 20;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct SourceSearchOptions {
    pub candidates: CSourceOptions,
    pub embedding: Option<Value>,
    pub embedding_contract: String,
    pub conditions: bool,
    pub max_rounds: usize,
    pub max_evaluations: usize,
    pub max_seconds: f64,
    pub compile_limits: Limits,
}

impl Default for SourceSearchOptions {
    fn default() -> Self {
        Self {
            candidates: CSourceOptions::default(),
            embedding: None,
            embedding_contract: "opaque".into(),
            conditions: true,
            max_rounds: 2,
            max_evaluations: 2048,
            max_seconds: 300.0,
            compile_limits: Limits::default(),
        }
    }
}

impl SourceSearchOptions {
    fn validate(&self) -> Result<()> {
        csource::validate_options(&self.candidates)?;
        ensure!(
            (1..=8).contains(&self.max_rounds),
            "max_rounds must be 1..8"
        );
        ensure!(
            (1..=16384).contains(&self.max_evaluations),
            "max_evaluations must be 1..16384"
        );
        ensure!(
            self.max_seconds.is_finite() && self.max_seconds > 0.0 && self.max_seconds <= 86400.0,
            "max_seconds must be finite, positive and at most 86400"
        );
        ensure!(
            matches!(
                self.candidates.frontend.token_contract.as_str(),
                "no-token-observation" | "preprocessed"
            ),
            "source search requires explicit source/token/location non-observation"
        );
        if self.embedding.is_some() {
            ensure!(self.embedding_contract == "compile-input-only",
                "embedded C requires embedding_contract=compile-input-only: the wrapper must not observe source bytes except as the declared compiler input");
        } else {
            ensure!(
                matches!(
                    self.embedding_contract.as_str(),
                    "opaque" | "compile-input-only"
                ),
                "unknown embedding observation contract"
            );
        }
        self.compile_limits.validate()
    }
}

#[derive(Debug)]
pub struct SearchResult {
    pub data: Vec<u8>,
    pub report: Value,
    pub recipe: Value,
}

#[derive(Clone, Debug)]
struct Score {
    cost: usize,
    style: String,
    payload_sha256: String,
}

struct Budget {
    started: Instant,
    evaluations: usize,
    maximum: usize,
    seconds: f64,
    reason: Option<String>,
    frontend_capacity_stop: Option<Value>,
    records: Vec<Value>,
    record_bytes: usize,
    costs: HashMap<String, usize>,
}

impl Budget {
    fn new(options: &SourceSearchOptions) -> Self {
        Self {
            started: Instant::now(),
            evaluations: 0,
            maximum: options.max_evaluations,
            seconds: options.max_seconds,
            reason: None,
            frontend_capacity_stop: None,
            records: Vec::new(),
            record_bytes: 0,
            costs: HashMap::new(),
        }
    }

    fn cancelled(&self) -> Result<()> {
        ensure!(!process::cancelled(), "source search cancelled");
        Ok(())
    }

    fn available(&mut self) -> Result<bool> {
        self.cancelled()?;
        if self.reason.is_none() && self.started.elapsed().as_secs_f64() >= self.seconds {
            self.reason = Some("scheduling-time-budget".into());
        }
        Ok(self.reason.is_none())
    }

    fn verification_available(&mut self) -> Result<bool> {
        self.cancelled()?;
        if self.started.elapsed().as_secs_f64() >= self.seconds {
            self.reason = Some("scheduling-time-budget".into());
        }
        Ok(self
            .reason
            .as_deref()
            .is_none_or(|r| r == "complete-file-evaluation-budget"))
    }

    fn record(&mut self, value: Value) -> Result<bool> {
        self.cancelled()?;
        let bytes = serde_json::to_vec(&value)?.len();
        if self.records.len() == MAX_RECORDS
            || bytes > MAX_REPORT_BYTES.saturating_sub(self.record_bytes)
        {
            // Unlike exhaustion of new cost measurements, losing the ability
            // to retain evidence also stops verification of measured singles.
            self.reason = Some("report-memory-budget".into());
            return Ok(false);
        }
        self.record_bytes += bytes;
        self.records.push(value);
        Ok(true)
    }

    fn stop_for_frontend_capacity(
        &mut self,
        error: &anyhow::Error,
        phase: &str,
        round: usize,
        id: &str,
    ) -> Result<bool> {
        self.cancelled()?;
        let Some(capacity) = error.downcast_ref::<cflow::FrontendOutputLimit>() else {
            return Ok(false);
        };
        let evidence = json!({"stage":"frontend-capacity-stop","phase":phase,"round":round,"id":id,
            "reason":format!("{error:#}"),"capture":capacity,"syntax_recheck":"passed",
            "frontend_proof":"incomplete","truncated_output_accepted":false,
            "retained":"last fully verified incumbent; unchanged C retains byte-identity proof"});
        self.reason = Some("frontend-output-budget".into());
        // Retain this bounded receipt even if the detailed-record budget fills
        // at this point. No partial frontend output can become an accepted AST.
        self.frontend_capacity_stop = Some(evidence.clone());
        self.record(evidence)?;
        Ok(true)
    }

    fn measure(
        &mut self,
        payload: &[u8],
        measure: &mut impl FnMut(&[u8]) -> Result<usize>,
    ) -> Result<Option<(usize, bool)>> {
        let hash = sha256(payload);
        if let Some(&cost) = self.costs.get(&hash) {
            return Ok(Some((cost, true)));
        }
        if !self.available()? {
            return Ok(None);
        }
        // Reserve the last allowed measurement for fresh final-cost readback.
        // A one-evaluation request therefore returns the measured raw input.
        if self.evaluations + 1 >= self.maximum {
            self.reason = Some("complete-file-evaluation-budget".into());
            return Ok(None);
        }
        self.evaluations += 1;
        let cost = measure(payload)?;
        self.costs.insert(hash, cost);
        Ok(Some((cost, false)))
    }
}

fn tool_pin(name: &str) -> Result<Value> {
    let path = process::resolve_tool(name)?;
    Ok(json!({"path":path,"sha256":sha256(&fs::read(&path)?)}))
}

fn check_tool(name: &str, pin: &Value, role: &str) -> Result<()> {
    let actual = tool_pin(name)?;
    ensure!(
        actual["sha256"] == pin["sha256"] && pin["sha256"].as_str().is_some(),
        "{role} executable changed from the recorded source-search tool"
    );
    Ok(())
}

fn native_identity(record: &Value) -> Result<Value> {
    ensure!(
        record["returncode"] == 0
            && record["timed_out"] == false
            && record["output_limited"] == false,
        "declared source compiler did not complete successfully"
    );
    for name in [
        "sha256",
        "compiler_sha256",
        "stdout_sha256",
        "stderr_sha256",
    ] {
        ensure!(
            record[name].as_str().is_some_and(|s| s.len() == 64),
            "native record lacks {name}"
        );
    }
    ensure!(
        record["bytes"].as_u64().is_some(),
        "declared source compiler did not produce a native file"
    );
    Ok(json!({"sha256":record["sha256"],"bytes":record["bytes"],
        "compiler_sha256":record["compiler_sha256"],"stdout_sha256":record["stdout_sha256"],
        "stderr_sha256":record["stderr_sha256"]}))
}

fn same_native(record: &Value, baseline: &Value) -> Result<()> {
    ensure!(
        native_identity(record)? == native_identity(baseline)?,
        "complete native bytes, compiler or compiler diagnostics differ from the baseline"
    );
    Ok(())
}

fn cflow_options(options: &SourceSearchOptions) -> cflow::CFlowOptions {
    cflow::CFlowOptions {
        include_nonshrinking: true,
        individual_edits: 32,
        max_variants: 64,
        ..options.candidates.frontend.clone()
    }
}

fn score_source(
    budget: &mut Budget,
    adapter: &PayloadAdapter,
    source: &[u8],
    id: &str,
    round: usize,
    measure: &mut impl FnMut(&[u8]) -> Result<usize>,
) -> Result<Option<Score>> {
    let mut best: Option<Score> = None;
    for rendered in adapter.render(source)? {
        if !budget.available()? {
            break;
        }
        let payload_hash = sha256(&rendered.data);
        let measured = match budget.measure(&rendered.data, measure) {
            Ok(value) => value,
            Err(error) => {
                budget.record(json!({"stage":"complete-file-cost-failed","round":round,"id":id,
                    "source_sha256":sha256(source),"style":rendered.style,"payload_sha256":payload_hash,
                    "reason":format!("{error:#}")}))?;
                return Err(error).context("candidate complete-file cost failed");
            }
        };
        let Some((cost, reused)) = measured else {
            break;
        };
        if !budget.record(json!({"stage":"complete-file-cost","round":round,"id":id,
            "source_sha256":sha256(source),"source_bytes":source.len(),"style":rendered.style,
            "payload_sha256":payload_hash,"payload_bytes":rendered.data.len(),"whole_file_bytes":cost,
            "cost_reused":reused,"semantic_acceptance":"not established by size measurement"}))? { break; }
        if best.as_ref().is_none_or(|b| cost < b.cost) {
            best = Some(Score {
                cost,
                style: rendered.style,
                payload_sha256: payload_hash,
            });
        }
    }
    Ok(best)
}

fn payload_for(adapter: &PayloadAdapter, source: &[u8], score: &Score) -> Result<Vec<u8>> {
    let rendered = adapter.render_style(source, &score.style)?;
    ensure!(
        sha256(&rendered.data) == score.payload_sha256,
        "payload rendering changed since cost measurement"
    );
    Ok(rendered.data)
}

fn admit(
    source: &[u8],
    variant: &Variant,
    spelling: bool,
    options: &SourceSearchOptions,
    compiler: &[String],
    native_dir: &Path,
    baseline: &Value,
    frontend: &Value,
) -> Result<Value> {
    check_tool(&options.candidates.frontend.clang, frontend, "frontend")?;
    if spelling {
        csource::verify_variant(source, variant, &options.candidates)?;
    }
    let native = native_fingerprint(&variant.data, compiler, native_dir, &options.compile_limits)?;
    same_native(&native, baseline)
        .with_context(|| format!("candidate native receipt: {native}"))?;
    check_tool(&options.candidates.frontend.clang, frontend, "frontend")?;
    Ok(native)
}

fn owned_directory(out: &Path, name: &str) -> Result<PathBuf> {
    fs::create_dir_all(out)?;
    let directory = out.join(name);
    fs::create_dir(&directory).with_context(|| {
        format!(
            "source-search output must be fresh: {}",
            directory.display()
        )
    })?;
    Ok(directory)
}

/// Search a fixed, caller-declared complete-file cost. The callback must include
/// every header, loader, source/bootstrap and compressed payload byte that the
/// selected submission charges. It must not execute the candidate program.
pub fn search(
    payload: &[u8],
    options: &SourceSearchOptions,
    compiler: &[String],
    out: &Path,
    measure: &mut impl FnMut(&[u8]) -> Result<usize>,
) -> Result<SearchResult> {
    options.validate()?;
    ensure!(
        !compiler.is_empty(),
        "source search needs an explicit compile argv"
    );
    let directory = owned_directory(out, "source-search")?;
    let mut budget = Budget::new(options);
    let result = search_inner(payload, options, compiler, &directory, measure, &mut budget);
    if let Err(error) = &result {
        write_json(
            &directory.join("failed-report.json"),
            &json!({"schema":SCHEMA,"status":"failed",
            "error":format!("{error:#}"),"input_payload_sha256":sha256(payload),
            "evaluations":budget.evaluations,"records":budget.records,"seconds":budget.started.elapsed().as_secs_f64()}),
        )?;
    }
    result
}

fn search_inner(
    payload: &[u8],
    options: &SourceSearchOptions,
    compiler: &[String],
    directory: &Path,
    measure: &mut impl FnMut(&[u8]) -> Result<usize>,
    budget: &mut Budget,
) -> Result<SearchResult> {
    budget.cancelled()?;
    let adapter = PayloadAdapter::new(payload, options.embedding.as_ref())?;
    let original_source = adapter.source().to_vec();
    let compiler_pin = tool_pin(&compiler[0])?;
    let frontend_pin = tool_pin(&options.candidates.frontend.clang)?;
    let native_dir = directory.join("native");
    let baseline = native_fingerprint(
        &original_source,
        compiler,
        &native_dir,
        &options.compile_limits,
    )?;
    budget.record(json!({"stage":"baseline-compile","attempt":1,"native":baseline}))?;
    native_identity(&baseline)?;
    let repeated = native_fingerprint(
        &original_source,
        compiler,
        &native_dir,
        &options.compile_limits,
    )?;
    budget.record(json!({"stage":"baseline-compile","attempt":2,"native":repeated}))?;
    same_native(&repeated, &baseline).context("original native compilation is not reproducible")?;
    check_tool(&compiler[0], &compiler_pin, "compiler")?;
    budget.evaluations += 1;
    let initial_cost = measure(payload).context("original complete-file cost failed")?;
    budget.costs.insert(sha256(payload), initial_cost);
    budget.record(json!({"stage":"baseline-cost","whole_file_bytes":initial_cost,"payload_bytes":payload.len(),"payload_sha256":sha256(payload)}))?;
    let initial_style = if options.embedding.is_some() {
        "original"
    } else {
        "direct"
    };
    let mut source = original_source.clone();
    let mut current_payload = payload.to_vec();
    let mut current = Score {
        cost: initial_cost,
        style: initial_style.into(),
        payload_sha256: sha256(payload),
    };
    let mut steps = Vec::new();

    // Literal-envelope spelling alone can improve a submission. This is kept
    // separate from a C source edit and needs no fictitious source derivation.
    if let Some(score) = score_source(budget, &adapter, &source, "original-source", 0, measure)? {
        if score.cost < current.cost {
            let rendered = payload_for(&adapter, &source, &score)?;
            if budget.record(json!({"stage":"accepted-payload-spelling","style":score.style,
                "source_unchanged":true,"whole_file_bytes":score.cost,"payload_sha256":score.payload_sha256}))? {
                current_payload = rendered;
                current = score;
            }
        }
    }

    for round in 1..=options.max_rounds {
        if !budget.available()? {
            break;
        }
        let before_cost = current.cost;
        let round_source = source.clone();
        check_tool(
            &options.candidates.frontend.clang,
            &frontend_pin,
            "frontend",
        )?;
        let generated = match csource::generate_variants(&round_source, &options.candidates)
            .context("C spelling candidate generation failed")
        {
            Ok(value) => value,
            Err(error) => {
                if budget.stop_for_frontend_capacity(
                    &error,
                    "spelling-generation",
                    round,
                    "round-input",
                )? {
                    break;
                }
                return Err(error);
            }
        };
        if !budget.record(
            json!({"stage":"generation-summary","family":"c-source","round":round,
            "variants_including_raw":generated.len(),"raw":generated.first()}),
        )? {
            break;
        }
        let mut singles = Vec::new();
        let mut seen = HashSet::from([sha256(&round_source)]);
        for variant in generated {
            if !seen.insert(variant.sha256.clone()) {
                continue;
            }
            if !budget.available()? {
                break;
            }
            if !budget
                .record(json!({"stage":"spelling-candidate","round":round,"variant":variant}))?
            {
                break;
            }
            if let Some(score) =
                score_source(budget, &adapter, &variant.data, &variant.id, round, measure)?
            {
                if score.cost < before_cost {
                    singles.push((variant, score));
                }
            }
        }
        singles.sort_by(|a, b| (a.1.cost, &a.0.id).cmp(&(b.1.cost, &b.0.id)));
        let mut selected = Vec::<Variant>::new();
        let mut selected_best: Option<(Variant, Score, Value)> = None;
        let mut best_cost = current.cost;
        for (single, single_score) in singles {
            if !budget.verification_available()? {
                break;
            }
            // Once cost exploration is exhausted, previously measured single
            // candidates can still reach their semantic gate. An unmeasured
            // composition cannot borrow the sum of their individual savings.
            if !selected.is_empty() && !budget.available()? {
                break;
            }
            let mut proposed = selected.clone();
            proposed.push(single.clone());
            let combined = if selected.is_empty() {
                single
            } else {
                match csource::compose_variants(&round_source, &proposed, &options.candidates) {
                    Ok(value) => value,
                    Err(error) => {
                        budget.record(json!({"stage":"composition-rejected","round":round,
                            "id":single.id,"reason":format!("{error:#}"),"classification":"overlap or binding-contract inapplicability"}))?;
                        continue;
                    }
                }
            };
            if !budget
                .record(json!({"stage":"composed-candidate","round":round,"variant":combined}))?
            {
                break;
            }
            let score = if selected.is_empty() {
                single_score
            } else {
                let Some(score) = score_source(
                    budget,
                    &adapter,
                    &combined.data,
                    &combined.id,
                    round,
                    measure,
                )?
                else {
                    continue;
                };
                score
            };
            if score.cost >= best_cost {
                continue;
            }
            if !budget.verification_available()? {
                break;
            }
            match admit(
                &round_source,
                &combined,
                true,
                options,
                compiler,
                &native_dir,
                &baseline,
                &frontend_pin,
            ) {
                Ok(native) => {
                    payload_for(&adapter, &combined.data, &score)?;
                    if !budget.record(json!({"stage":"composition-admitted","round":round,
                        "id":combined.id,"whole_file_bytes":score.cost,"native":native,
                        "scope":"typed AST/binding identity and complete native/diagnostic equality; no engine execution"}))? { break; }
                    best_cost = score.cost;
                    selected = proposed;
                    selected_best = Some((combined, score, native));
                }
                Err(error) => {
                    if budget.stop_for_frontend_capacity(
                        &error,
                        "spelling-admission",
                        round,
                        &combined.id,
                    )? {
                        break;
                    }
                    budget.cancelled()?;
                    budget.record(
                        json!({"stage":"semantic-rejected","round":round,"id":combined.id,
                        "reason":format!("{error:#}"),"measured_whole_file_bytes":score.cost}),
                    )?;
                }
            }
        }
        if let Some((variant, score, native)) = selected_best {
            current_payload = payload_for(&adapter, &variant.data, &score)?;
            steps.push(
                json!({"kind":"c-source","round":round,"input_source_sha256":sha256(&round_source),
                "variant":variant,"style":score.style,"payload_sha256":score.payload_sha256,
                "whole_file_bytes":score.cost,"native":native}),
            );
            source = variant.data;
            current = score;
        }

        if options.conditions && budget.available()? {
            let flow_options = cflow_options(options);
            let flows = match cflow::generate_variants(&source, &flow_options)
                .context("typed C condition candidate generation failed")
            {
                Ok(value) => value,
                Err(error) => {
                    if budget.stop_for_frontend_capacity(
                        &error,
                        "condition-generation",
                        round,
                        "round-input",
                    )? {
                        break;
                    }
                    return Err(error);
                }
            };
            if !budget.record(
                json!({"stage":"generation-summary","family":"c-flow","round":round,
                "variants_including_raw":flows.len(),"raw":flows.first()}),
            )? {
                break;
            }
            let mut candidates = Vec::new();
            let mut seen = HashSet::from([sha256(&source)]);
            for variant in flows {
                if !seen.insert(variant.sha256.clone()) {
                    continue;
                }
                if !budget.available()? {
                    break;
                }
                if !budget.record(
                    json!({"stage":"condition-candidate","round":round,"variant":variant}),
                )? {
                    break;
                }
                if let Some(score) =
                    score_source(budget, &adapter, &variant.data, &variant.id, round, measure)?
                {
                    if score.cost < current.cost {
                        candidates.push((variant, score));
                    }
                }
            }
            candidates.sort_by(|a, b| (a.1.cost, &a.0.id).cmp(&(b.1.cost, &b.0.id)));
            for (variant, score) in candidates {
                if !budget.verification_available()? {
                    break;
                }
                match admit(
                    &source,
                    &variant,
                    false,
                    options,
                    compiler,
                    &native_dir,
                    &baseline,
                    &frontend_pin,
                ) {
                    Ok(native) => {
                        let rendered = payload_for(&adapter, &variant.data, &score)?;
                        if !budget.record(json!({"stage":"condition-admitted","round":round,"id":variant.id,
                            "whole_file_bytes":score.cost,"native":native,
                            "scope":"generated typed local rule guards and complete native/diagnostic equality; no engine execution"}))? { break; }
                        steps.push(json!({"kind":"c-flow","round":round,"input_source_sha256":sha256(&source),
                            "variant":variant,"style":score.style,"payload_sha256":score.payload_sha256,
                            "whole_file_bytes":score.cost,"native":native}));
                        current_payload = rendered;
                        source = variant.data;
                        current = score;
                        break;
                    }
                    Err(error) => {
                        budget.cancelled()?;
                        budget.record(
                            json!({"stage":"semantic-rejected","round":round,"id":variant.id,
                            "reason":format!("{error:#}"),"measured_whole_file_bytes":score.cost}),
                        )?;
                    }
                }
            }
        }
        if current.cost == before_cost {
            break;
        }
    }

    budget.cancelled()?;
    check_tool(&compiler[0], &compiler_pin, "compiler")?;
    check_tool(
        &options.candidates.frontend.clang,
        &frontend_pin,
        "frontend",
    )?;
    ensure!(
        current.cost <= initial_cost,
        "source search regressed the original complete-file cost"
    );
    let final_native = if source == original_source {
        repeated
    } else {
        let checked = native_fingerprint(&source, compiler, &native_dir, &options.compile_limits)?;
        same_native(&checked, &baseline)
            .context("final selected source failed fresh native reproduction")?;
        checked
    };
    ensure!(
        payload_for(&adapter, &source, &current)? == current_payload,
        "final payload replay differs"
    );
    if current_payload != payload {
        ensure!(
            budget.evaluations < options.max_evaluations,
            "final complete-file measurement reservation lost"
        );
        budget.evaluations += 1;
        ensure!(
            measure(&current_payload)? == current.cost,
            "final complete-file cost is not reproducible"
        );
    }
    let source_unchanged = source == original_source;
    let source_proof = if source_unchanged {
        "byte-identical-to-original"
    } else {
        "accepted-typed-derivations"
    };
    let final_record = json!({"source_sha256":sha256(&source),"source_bytes":source.len(),
        "source_unchanged":source_unchanged,"source_proof":source_proof,
        "payload_sha256":sha256(&current_payload),"payload_bytes":current_payload.len(),
        "style":current.style,"whole_file_bytes":current.cost,"native":final_native});
    let recipe = json!({"schema":SCHEMA,"options":options,"compiler_argv":compiler,
        "compiler":compiler_pin,"frontend":frontend_pin,"input_payload_sha256":sha256(payload),
        "input_source_sha256":sha256(&original_source),"baseline_native":baseline,
        "baseline_whole_file_bytes":initial_cost,"steps":steps,"final":final_record});
    let report = json!({"schema":SCHEMA,"status":if budget.reason.is_some(){"budget-exhausted"}else{"completed"},
        "exhaustion_reason":budget.reason,"frontend_capacity_stop":budget.frontend_capacity_stop,
        "evaluations":budget.evaluations,"evaluation_limit":options.max_evaluations,
        "seconds":budget.started.elapsed().as_secs_f64(),"time_limit_kind":"scheduling deadline between bounded operations; final acceptance completes separately",
        "original_whole_file_bytes":initial_cost,"selected_whole_file_bytes":current.cost,
        "saved_whole_file_bytes":initial_cost-current.cost,"input_payload_sha256":sha256(payload),
        "input_source_sha256":sha256(&original_source),"final":final_record,"accepted_steps":steps.len(),
        "records":budget.records,"engine_execution":"not performed","optimality":"bounded measured portfolio only",
        "embedding_contract":options.embedding_contract,
        "acceptance":"unchanged C bytes or applicable typed source proof; complete native and diagnostic identity; exact payload-adapter readback"});
    write_json(&directory.join("report.json"), &report)?;
    write_json(&directory.join("recipe.json"), &recipe)?;
    fs::write(directory.join("selected-payload"), &current_payload)?;
    Ok(SearchResult {
        data: current_payload,
        report,
        recipe,
    })
}

/// Reconstruct the recorded accepted derivations, with no cost search. Each C
/// spelling step replays audited offsets and typed AST/bindings; each condition
/// step regenerates its bounded recorded rule recipe. Native bytes and compiler
/// diagnostics must match the original baseline at every accepted step.
pub fn replay(payload: &[u8], recipe: &Value, compiler: &[String], out: &Path) -> Result<Vec<u8>> {
    ensure!(
        recipe["schema"] == SCHEMA,
        "unsupported source-search recipe"
    );
    let options: SourceSearchOptions = serde_json::from_value(recipe["options"].clone())?;
    options.validate()?;
    ensure!(
        recipe["input_payload_sha256"] == sha256(payload),
        "source-search input payload changed"
    );
    ensure!(
        !compiler.is_empty() && recipe["compiler_argv"] == json!(compiler),
        "source-search compile argv changed"
    );
    check_tool(&compiler[0], &recipe["compiler"], "compiler")?;
    check_tool(
        &options.candidates.frontend.clang,
        &recipe["frontend"],
        "frontend",
    )?;
    let steps = recipe["steps"]
        .as_array()
        .context("source-search recipe steps missing")?;
    ensure!(
        steps.len() <= options.max_rounds * 2,
        "source-search recipe exceeds accepted-step bound"
    );
    ensure!(
        serde_json::to_vec(recipe)?.len() <= MAX_REPORT_BYTES,
        "source-search recipe exceeds byte bound"
    );
    let directory = owned_directory(out, "source-replay")?;
    let adapter = PayloadAdapter::new(payload, options.embedding.as_ref())?;
    let mut source = adapter.source().to_vec();
    ensure!(
        recipe["input_source_sha256"] == sha256(&source),
        "embedded source identity changed"
    );
    let native_dir = directory.join("native");
    let baseline = native_fingerprint(&source, compiler, &native_dir, &options.compile_limits)?;
    same_native(&baseline, &recipe["baseline_native"])?;
    let repeated = native_fingerprint(&source, compiler, &native_dir, &options.compile_limits)?;
    same_native(&repeated, &baseline)?;
    let mut receipts = vec![
        json!({"stage":"baseline-compile","attempt":1,"native":baseline}),
        json!({"stage":"baseline-compile","attempt":2,"native":repeated}),
    ];
    for (index, step) in steps.iter().enumerate() {
        ensure!(!process::cancelled(), "source replay cancelled");
        ensure!(
            step["input_source_sha256"] == sha256(&source),
            "source-search step input changed"
        );
        let recorded: Variant = serde_json::from_value(step["variant"].clone())
            .context("invalid recorded source variant")?;
        let candidate = match step["kind"].as_str() {
            Some("c-source") => csource::replay_variant(&source, &recorded, &options.candidates)?,
            Some("c-flow") => {
                ensure!(
                    options.conditions,
                    "recorded condition step is disabled by its contract"
                );
                let generated = cflow::generate_variants(&source, &cflow_options(&options))?;
                let selected = generated
                    .into_iter()
                    .find(|v| v.id == recorded.id)
                    .context("recorded condition recipe is no longer available")?;
                ensure!(
                    selected.sha256 == recorded.sha256
                        && selected.bytes == recorded.bytes
                        && selected.audit == recorded.audit,
                    "recorded condition derivation changed"
                );
                selected
            }
            _ => bail!("unknown recorded source derivation"),
        };
        let native = native_fingerprint(
            &candidate.data,
            compiler,
            &native_dir,
            &options.compile_limits,
        )?;
        same_native(&native, &baseline)?;
        same_native(&native, &step["native"])?;
        let style = step["style"]
            .as_str()
            .context("recorded payload spelling missing")?;
        let rendered = adapter.render_style(&candidate.data, style)?;
        ensure!(
            step["payload_sha256"] == sha256(&rendered.data),
            "recorded step payload changed"
        );
        receipts.push(json!({"stage":"accepted-step-replay","index":index,"source_sha256":candidate.sha256,"native":native}));
        source = candidate.data;
    }
    let final_record = &recipe["final"];
    ensure!(
        final_record["source_sha256"] == sha256(&source)
            && final_record["source_bytes"].as_u64() == Some(source.len() as u64),
        "final source identity changed"
    );
    let style = final_record["style"]
        .as_str()
        .context("final payload spelling missing")?;
    let rendered = adapter.render_style(&source, style)?;
    ensure!(
        final_record["payload_sha256"] == sha256(&rendered.data)
            && final_record["payload_bytes"].as_u64() == Some(rendered.data.len() as u64),
        "final source-search payload changed"
    );
    let final_native = native_fingerprint(&source, compiler, &native_dir, &options.compile_limits)?;
    same_native(&final_native, &baseline)?;
    same_native(&final_native, &final_record["native"])?;
    check_tool(&compiler[0], &recipe["compiler"], "compiler")?;
    check_tool(
        &options.candidates.frontend.clang,
        &recipe["frontend"],
        "frontend",
    )?;
    receipts.push(json!({"stage":"final-replay","native":final_native,"payload_sha256":sha256(&rendered.data)}));
    write_json(
        &directory.join("report.json"),
        &json!({"schema":SCHEMA,"status":"replayed",
        "records":receipts,"engine_execution":"not performed","cost_search":"not performed"}),
    )?;
    fs::write(directory.join("selected-payload"), &rendered.data)?;
    Ok(rendered.data)
}
