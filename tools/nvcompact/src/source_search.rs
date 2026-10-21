//! Measured C-source search inside a declared, byte-preserved payload adapter.
//!
//! Source length and native-code identity are deliberately different costs.
//! Spelling candidates retain their own source hashes even when their complete
//! native images agree. Only a smaller complete-file cost can advance the
//! incumbent; typed source checks and the actual compiler gate precede adoption.
use crate::csource::{self, CSourceOptions};
use crate::envelope::native_fingerprint;
use crate::notation::Variant;
use crate::process::{self, Limits};
use crate::source_payload::PayloadAdapter;
use crate::{attempts::Archive, cflow};
use crate::{sha256, write_json};
use anyhow::{bail, ensure, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};

mod plan;
mod runtime;

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
    /// Composition attempts, including incompatible subsets. This is separate
    /// from expensive whole-file measurements and never filters by source size.
    pub max_combinations: usize,
    pub max_seconds: f64,
    /// Additional deduplicated source snapshots. Original inputs are retained
    /// separately under the existing 8 MiB per-input bound.
    pub max_retained_source_bytes: usize,
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
            max_combinations: 16384,
            max_seconds: 300.0,
            max_retained_source_bytes: 64 << 20,
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
            (1..=1_048_576).contains(&self.max_combinations),
            "max_combinations must be 1..1048576"
        );
        ensure!(
            self.max_seconds.is_finite() && self.max_seconds > 0.0 && self.max_seconds <= 86400.0,
            "max_seconds must be finite, positive and at most 86400"
        );
        ensure!(
            self.max_retained_source_bytes <= 512 << 20,
            "max_retained_source_bytes must be 0..536870912"
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

/// A caller owns the whole-file objective, including codec/header context.
/// Fresh validation is a different operation from reusable cost measurement.
pub trait CompleteFileObjective {
    fn measure(&mut self, payload: &[u8]) -> Result<usize>;
    fn fresh_measure(&mut self, payload: &[u8]) -> Result<usize>;
}

struct CallbackObjective<'a, F>(&'a mut F);
impl<F: FnMut(&[u8]) -> Result<usize>> CompleteFileObjective for CallbackObjective<'_, F> {
    fn measure(&mut self, payload: &[u8]) -> Result<usize> {
        (self.0)(payload)
    }
    fn fresh_measure(&mut self, payload: &[u8]) -> Result<usize> {
        (self.0)(payload)
    }
}

/// Deferred systematic work owns immutable bases and derivations, never ASTs
/// for every branch. Priority scheduling and eligibility are independent.
struct RoundSpace {
    source: Vec<u8>,
    choices: Vec<Variant>,
    prefix: Vec<Value>,
    round: usize,
}

const MAX_PLAN_SOURCE_BYTES: usize = 64 << 20;

/// One run wires independent owners together; scheduling does not own evidence,
/// and evidence retention cannot silently turn a measured candidate into proof.
struct SearchRun {
    budget: runtime::RunBudget,
    journal: runtime::EvidenceJournal,
    costs: runtime::CostMemo,
    frontend_capacity_stop: Option<Value>,
}

impl SearchRun {
    fn new(options: &SourceSearchOptions, archive: Archive) -> Self {
        Self {
            budget: runtime::RunBudget::new(options),
            journal: runtime::EvidenceJournal::new(archive),
            costs: runtime::CostMemo::new(),
            frontend_capacity_stop: None,
        }
    }
    fn cancelled(&self) -> Result<()> {
        self.budget.cancelled()
    }
    fn available(&mut self) -> Result<bool> {
        self.budget.available()
    }
    fn verification_available(&mut self) -> Result<bool> {
        self.budget.verification_available()
    }
    fn record(&mut self, value: Value) -> Result<bool> {
        self.journal.record(&mut self.budget, value)
    }
    fn candidate(
        &mut self,
        stage: &str,
        round: usize,
        base: &[u8],
        variant: &Variant,
    ) -> Result<bool> {
        self.journal
            .candidate(&mut self.budget, stage, round, base, variant)
    }
    fn measure(
        &mut self,
        payload: &[u8],
        measure: &mut impl FnMut(&[u8]) -> Result<usize>,
    ) -> Result<Option<(usize, bool)>> {
        self.costs.measure(&mut self.budget, payload, measure)
    }
    fn stop_for_frontend_capacity(
        &mut self,
        error: &anyhow::Error,
        phase: &str,
        round: usize,
        id: &str,
    ) -> Result<bool> {
        self.cancelled()?;
        ensure!(
            error
                .downcast_ref::<csource::FrontendContextChanged>()
                .is_none(),
            "source-search frontend context changed: {error:#}"
        );
        let Some(capacity) = error.downcast_ref::<cflow::FrontendOutputLimit>() else {
            return Ok(false);
        };
        let evidence = json!({"stage":"frontend-capacity-stop","phase":phase,"round":round,"id":id,
            "reason":format!("{error:#}"),"capture":capacity,"syntax_recheck":"passed",
            "frontend_proof":"incomplete","truncated_output_accepted":false,
            "retained":"last fully verified incumbent; unchanged C retains byte-identity proof"});
        self.budget.reason = Some("frontend-output-budget".into());
        self.frontend_capacity_stop = Some(evidence.clone());
        self.record(evidence)?;
        Ok(true)
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
    budget: &mut SearchRun,
    adapter: &PayloadAdapter,
    source: &[u8],
    id: &str,
    round: usize,
    incumbent_cost: usize,
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
            "compared_to_whole_file_bytes":incumbent_cost,
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
    prepared: Option<&csource::PreparedSource>,
    options: &SourceSearchOptions,
    compiler: &[String],
    native_dir: &Path,
    baseline: &Value,
    frontend: &Value,
    budget: &mut SearchRun,
    round: usize,
) -> Result<Value> {
    check_tool(&options.candidates.frontend.clang, frontend, "frontend")?;
    if spelling {
        if let Some(prepared) = prepared {
            ensure!(prepared.source() == source, "prepared source basis differs");
            prepared.verify_variant(variant)?;
        } else {
            csource::verify_variant(source, variant, &options.candidates)?;
        }
    }
    let native = native_fingerprint(&variant.data, compiler, native_dir, &options.compile_limits)?;
    ensure!(
        budget.record(
            json!({"stage":"candidate-compile","round":round,"id":variant.id,
        "source_sha256":variant.sha256,"native":native})
        )?,
        "candidate compile completed but its evidence budget is exhausted; candidate not admitted"
    );
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
    search_with_cost_context(payload, options, compiler, out, None, measure)
}

/// The explicit objective describes the actual inspected header/decoder/codec
/// and its implementation. Without it, retained costs are comparable only
/// inside this run; an opaque callback is not a cross-run contract.
pub fn search_with_cost_context(
    payload: &[u8],
    options: &SourceSearchOptions,
    compiler: &[String],
    out: &Path,
    cost_objective: Option<&Value>,
    measure: &mut impl FnMut(&[u8]) -> Result<usize>,
) -> Result<SearchResult> {
    search_with_objective(
        payload,
        options,
        compiler,
        out,
        cost_objective,
        &mut CallbackObjective(measure),
    )
}

pub fn search_with_objective(
    payload: &[u8],
    options: &SourceSearchOptions,
    compiler: &[String],
    out: &Path,
    cost_objective: Option<&Value>,
    objective: &mut impl CompleteFileObjective,
) -> Result<SearchResult> {
    options.validate()?;
    ensure!(
        !compiler.is_empty(),
        "source search needs an explicit compile argv"
    );
    let directory = owned_directory(out, "source-search")?;
    if let Some(context) = cost_objective {
        ensure!(context.is_object(), "cost objective must be an object");
    }
    let archive = Archive::new(
        &directory.join("attempts"),
        payload,
        options,
        compiler,
        cost_objective,
    )?;
    let mut budget = SearchRun::new(options, archive);
    let mut result = search_inner(
        payload,
        options,
        compiler,
        &directory,
        objective,
        &mut budget,
    );
    let outcome = match &result {
        Ok(searched) => {
            json!({"status":searched.report["status"],"exhaustion_reason":budget.budget.reason,
            "retention_stop":budget.journal.retention_stop,"final":searched.recipe["final"]})
        }
        Err(error) => json!({"status":"failed","error":format!("{error:#}"),
            "exhaustion_reason":budget.budget.reason,"retention_stop":budget.journal.retention_stop}),
    };
    let attempts = match budget.journal.archive.finish(outcome) {
        Ok(value) => value,
        Err(archive_error) => {
            let original_error = result.as_ref().err().map(|error| format!("{error:#}"));
            let receipt_error = write_json(&directory.join("failed-report.json"),
                &json!({"schema":SCHEMA,"status":"failed","input_payload_sha256":sha256(payload),
                    "search_error":original_error,"evidence_error":format!("{archive_error:#}"),
                    "records":budget.journal.records,"evaluations":budget.budget.evaluations,
                    "preserved":"existing source snapshots, event journal and any completed search files; not a completed evidence archive"}))
                .err().map(|error|format!("{error:#}"));
            let detail = format!("retained-attempt finalization failed: {archive_error:#}; failed-receipt write error: {}",
                receipt_error.as_deref().unwrap_or("none"));
            return match result {
                Err(error) => Err(error.context(detail)),
                Ok(_) => Err(archive_error.context(detail)),
            };
        }
    };
    if let Ok(searched) = &mut result {
        searched.report["attempts"] = attempts;
        write_json(&directory.join("report.json"), &searched.report)?;
    } else if let Err(error) = &result {
        if let Err(report_error) = write_json(
            &directory.join("failed-report.json"),
            &json!({"schema":SCHEMA,"status":"failed",
            "error":format!("{error:#}"),"input_payload_sha256":sha256(payload),
            "evaluations":budget.budget.evaluations,"records":budget.journal.records,"attempts":attempts,
            "seconds":budget.budget.started.elapsed().as_secs_f64()}),
        ) {
            let original = result.expect_err("failed-report branch has a search failure");
            return Err(
                original.context(format!("failed to write failure receipt: {report_error:#}"))
            );
        }
    }
    result
}

fn search_inner(
    payload: &[u8],
    options: &SourceSearchOptions,
    compiler: &[String],
    directory: &Path,
    objective: &mut impl CompleteFileObjective,
    budget: &mut SearchRun,
) -> Result<SearchResult> {
    let measure = &mut |data: &[u8]| objective.measure(data);
    budget.cancelled()?;
    let adapter = PayloadAdapter::new(payload, options.embedding.as_ref())?;
    let original_source = adapter.source().to_vec();
    let compiler_pin = tool_pin(&compiler[0])?;
    let frontend_pin = tool_pin(&options.candidates.frontend.clang)?;
    budget
        .journal
        .archive
        .input("original-source", &original_source)?;
    budget.record(
        json!({"stage":"search-context","input_source_sha256":sha256(&original_source),
        "compiler":compiler_pin,"frontend":frontend_pin}),
    )?;
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
    budget.budget.evaluations += 1;
    let initial_cost = measure(payload).context("original complete-file cost failed")?;
    budget.costs.insert_baseline(payload, initial_cost);
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
    let mut spaces = Vec::new();
    let mut plan_bytes = 0usize;
    let mut coverage = Vec::new();
    let mut frontend_work = Vec::new();

    // Literal-envelope spelling alone can improve a submission. This is kept
    // separate from a C source edit and needs no fictitious source derivation.
    if let Some(score) = score_source(
        budget,
        &adapter,
        &source,
        "original-source",
        0,
        current.cost,
        measure,
    )? {
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
        let prepared = match csource::PreparedSource::new(&round_source, &options.candidates)
            .context("C spelling basis preparation failed")
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
        let generated = prepared
            .generate_variants()
            .context("C spelling candidate generation failed")?;
        if !budget.record(
            json!({"stage":"generation-summary","family":"c-source","round":round,
            "variants_including_raw":generated.len(),"raw":generated.first()}),
        )? {
            break;
        }
        let generation = generated.first().map(|v| v.contract["generation"].clone());
        let mut singles = Vec::new();
        let mut seen = HashSet::from([sha256(&round_source)]);
        let mut choices = Vec::new();
        for variant in generated {
            if !seen.insert(variant.sha256.clone()) {
                continue;
            }
            if !budget.candidate("spelling-candidate", round, &round_source, &variant)? {
                break;
            }
            choices.push(variant.clone());
            // Generation is already bounded: preserve remaining candidates
            // after a scheduling/evaluation stop without running new work.
            if !budget.available()? {
                continue;
            }
            if let Some(score) = score_source(
                budget,
                &adapter,
                &variant.data,
                &variant.id,
                round,
                before_cost,
                measure,
            )? {
                if score.cost < before_cost {
                    singles.push((variant, score));
                }
            }
        }
        let retained_bytes =
            round_source.len() + choices.iter().map(|v| v.data.len()).sum::<usize>();
        let scheduled = retained_bytes <= MAX_PLAN_SOURCE_BYTES.saturating_sub(plan_bytes);
        coverage.push(json!({"round":round,"basis_source_sha256":sha256(&round_source),
            "generated_choices":choices.len(),"nontrivial_subsets":plan::Combinations::cardinality(choices.len()),
            "systematic_subsets_attempted":0,"incompatible_subsets":0,"duplicate_sources":0,
            "scheduled":scheduled,"stop":if scheduled{Value::Null}else{json!("plan-source-memory-budget")},
            "generation":generation,
            "scope":"all subsets of generated spelling choices on this visited priority basis; compatible audited edits commute"}));
        if scheduled {
            plan_bytes += retained_bytes;
            spaces.push(RoundSpace {
                source: round_source.clone(),
                choices,
                prefix: steps.clone(),
                round,
            });
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
                match prepared.compose_variants(&proposed) {
                    Ok(value) => value,
                    Err(error) => {
                        budget.record(json!({"stage":"composition-rejected","round":round,
                            "id":single.id,"base_source_sha256":sha256(&round_source),
                            "components":proposed.iter().map(|v|json!({"id":v.id,"source_sha256":v.sha256})).collect::<Vec<_>>(),
                            "reason":format!("{error:#}"),"classification":"overlap or binding-contract inapplicability"}))?;
                        continue;
                    }
                }
            };
            if !budget.candidate("composed-candidate", round, &round_source, &combined)? {
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
                    best_cost,
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
                Some(&prepared),
                options,
                compiler,
                &native_dir,
                &baseline,
                &frontend_pin,
                budget,
                round,
            ) {
                Ok(native) => {
                    payload_for(&adapter, &combined.data, &score)?;
                    if !budget.record(json!({"stage":"composition-admitted","round":round,
                        "id":combined.id,"source_sha256":combined.sha256,
                        "payload_sha256":score.payload_sha256,"whole_file_bytes":score.cost,"native":native,
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
                        "source_sha256":combined.sha256,
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
            let flows = match (|| {
                if source == round_source {
                    prepared.flow_variants(&flow_options)
                } else {
                    csource::PreparedSource::new(&source, &options.candidates)?
                        .flow_variants(&flow_options)
                }
            })()
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
                if !budget.candidate("condition-candidate", round, &source, &variant)? {
                    break;
                }
                if !budget.available()? {
                    continue;
                }
                if let Some(score) = score_source(
                    budget,
                    &adapter,
                    &variant.data,
                    &variant.id,
                    round,
                    current.cost,
                    measure,
                )? {
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
                    None,
                    options,
                    compiler,
                    &native_dir,
                    &baseline,
                    &frontend_pin,
                    budget,
                    round,
                ) {
                    Ok(native) => {
                        let rendered = payload_for(&adapter, &variant.data, &score)?;
                        if !budget.record(json!({"stage":"condition-admitted","round":round,"id":variant.id,
                            "source_sha256":variant.sha256,"payload_sha256":score.payload_sha256,
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
                        if budget.stop_for_frontend_capacity(
                            &error,
                            "condition-admission",
                            round,
                            &variant.id,
                        )? {
                            break;
                        }
                        budget.cancelled()?;
                        budget.record(
                            json!({"stage":"semantic-rejected","round":round,"id":variant.id,
                            "source_sha256":variant.sha256,
                            "reason":format!("{error:#}"),"measured_whole_file_bytes":score.cost}),
                        )?;
                    }
                }
            }
        }
        frontend_work.push(
            json!({"round":round,"phase":"priority","basis_source_sha256":sha256(&round_source),
            "shared_analysis":prepared.statistics()}),
        );
        if current.cost == before_cost {
            break;
        }
    }

    // Cost is not monotone under composition. The priority pass above is only
    // an ordering policy; a losing or tied single remains eligible here.
    let mut combination_attempts = 0usize;
    for space in spaces {
        let entry = coverage
            .iter_mut()
            .find(|v| v["round"] == space.round)
            .unwrap();
        if !budget.available()? {
            entry["stop"] = json!(budget.budget.reason);
            continue;
        }
        if space.choices.len() < 2 {
            entry["exhausted"] = json!(true);
            continue;
        }
        let prepared = match csource::PreparedSource::new(&space.source, &options.candidates) {
            Ok(value) => value,
            Err(error) => {
                if budget.stop_for_frontend_capacity(
                    &error,
                    "combination-basis",
                    space.round,
                    "round-input",
                )? {
                    entry["stop"] = json!(budget.budget.reason);
                    continue;
                }
                return Err(error);
            }
        };
        let mut seen: HashSet<String> = space.choices.iter().map(|v| v.sha256.clone()).collect();
        seen.insert(sha256(&space.source));
        let mut attempted = 0usize;
        let mut incompatible = 0usize;
        let mut duplicate = 0usize;
        let mut exhausted = true;
        for indices in plan::Combinations::new(space.choices.len()) {
            if !budget.available()? || combination_attempts >= options.max_combinations {
                exhausted = false;
                if budget.budget.reason.is_none() {
                    budget.budget.reason = Some("combination-attempt-budget".into());
                }
                entry["stop"] = json!(budget
                    .budget
                    .reason
                    .as_deref()
                    .unwrap_or("combination-attempt-budget"));
                break;
            }
            attempted += 1;
            combination_attempts += 1;
            let proposed: Vec<_> = indices.iter().map(|&i| space.choices[i].clone()).collect();
            let combined = match prepared.compose_variants(&proposed) {
                Ok(value) => value,
                Err(error) => {
                    incompatible += 1;
                    budget.record(json!({"stage":"composition-rejected","round":space.round,
                        "phase":"systematic","base_source_sha256":sha256(&space.source),
                        "components":indices,"reason":format!("{error:#}"),
                        "classification":"overlap or binding-contract inapplicability"}))?;
                    continue;
                }
            };
            if !seen.insert(combined.sha256.clone()) {
                duplicate += 1;
                continue;
            }
            if !budget.candidate("composed-candidate", space.round, &space.source, &combined)? {
                exhausted = false;
                entry["stop"] = json!(budget.budget.reason);
                break;
            }
            let Some(score) = score_source(
                budget,
                &adapter,
                &combined.data,
                &combined.id,
                space.round,
                current.cost,
                measure,
            )?
            else {
                continue;
            };
            if score.cost >= current.cost || !budget.verification_available()? {
                continue;
            }
            match admit(
                &space.source,
                &combined,
                true,
                Some(&prepared),
                options,
                compiler,
                &native_dir,
                &baseline,
                &frontend_pin,
                budget,
                space.round,
            ) {
                Ok(native) => {
                    let rendered = payload_for(&adapter, &combined.data, &score)?;
                    if !budget.record(json!({"stage":"composition-admitted","round":space.round,
                        "phase":"systematic","id":combined.id,"source_sha256":combined.sha256,
                        "payload_sha256":score.payload_sha256,"whole_file_bytes":score.cost,"native":native}))? {
                        exhausted = false;
                        entry["stop"] = json!(budget.budget.reason);
                        break;
                    }
                    steps = space.prefix.clone();
                    steps.push(json!({"kind":"c-source","round":space.round,
                        "input_source_sha256":sha256(&space.source),"variant":combined,"style":score.style,
                        "payload_sha256":score.payload_sha256,"whole_file_bytes":score.cost,"native":native}));
                    source = combined.data;
                    current_payload = rendered;
                    current = score;
                }
                Err(error) => {
                    if budget.stop_for_frontend_capacity(
                        &error,
                        "combination-admission",
                        space.round,
                        &combined.id,
                    )? {
                        exhausted = false;
                        entry["stop"] = json!(budget.budget.reason);
                        break;
                    }
                    budget.cancelled()?;
                    budget.record(json!({"stage":"semantic-rejected","round":space.round,
                        "id":combined.id,"source_sha256":combined.sha256,"reason":format!("{error:#}"),
                        "measured_whole_file_bytes":score.cost}))?;
                }
            }
        }
        entry["systematic_subsets_attempted"] = json!(attempted);
        entry["incompatible_subsets"] = json!(incompatible);
        entry["duplicate_sources"] = json!(duplicate);
        entry["exhausted"] = json!(exhausted);
        entry["all_declared_costs_evaluated"] = json!(exhausted && budget.budget.reason.is_none());
        frontend_work.push(json!({"round":space.round,"phase":"systematic",
            "basis_source_sha256":sha256(&space.source),"shared_analysis":prepared.statistics()}));
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
            budget.budget.evaluations < options.max_evaluations,
            "final complete-file measurement reservation lost"
        );
        budget.budget.evaluations += 1;
        ensure!(
            objective.fresh_measure(&current_payload)? == current.cost,
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
    let report = json!({"schema":SCHEMA,"status":if budget.budget.reason.is_some(){"budget-exhausted"}else{"completed"},
        "exhaustion_reason":budget.budget.reason,"frontend_capacity_stop":budget.frontend_capacity_stop,
        "retention_stop":budget.journal.retention_stop,
        "evaluations":budget.budget.evaluations,"evaluation_limit":options.max_evaluations,
        "seconds":budget.budget.started.elapsed().as_secs_f64(),"time_limit_kind":"scheduling deadline between bounded operations; final acceptance completes separately",
        "original_whole_file_bytes":initial_cost,"selected_whole_file_bytes":current.cost,
        "saved_whole_file_bytes":initial_cost-current.cost,"input_payload_sha256":sha256(payload),
        "input_source_sha256":sha256(&original_source),"final":final_record,"accepted_steps":steps.len(),
        "records":budget.journal.records,"engine_execution":"not performed","optimality":"bounded declared search space only",
        "coverage":{"basis_spaces":coverage,"combination_attempts":combination_attempts,
            "combination_limit":options.max_combinations,"plan_source_bytes":plan_bytes,
            "plan_source_byte_limit":MAX_PLAN_SOURCE_BYTES,"priority":"legacy improving-incumbent rounds first",
            "all_equivalent_programs_explored":false,"all_rewrite_sequences_explored":false},
        "frontend_work":frontend_work,
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
