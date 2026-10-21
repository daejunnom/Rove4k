//! Bounded, immutable evidence for source-compression attempts. Reading an
//! archive compares recorded costs; it never executes its commands, retries a
//! transformation, or grants a new semantic acceptance.
use crate::{sha256, source_search::SourceSearchOptions};
use anyhow::{ensure, Context, Result};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::os::unix::fs::OpenOptionsExt;
use std::path::{Path, PathBuf};

const SCHEMA: &str = "nvcompact-source-attempts-v1";
const COMPARISON_SCHEMA: &str = "nvcompact-source-attempt-comparison-v1";
const MAX_METADATA: usize = 8 << 20;
const MAX_EVENTS: usize = 33 << 20;
// Includes a producer's maximum 512 MiB of optional source snapshots plus
// mandatory inputs, journal and metadata. The bound is aggregate across runs.
const MAX_READ: usize = 1024 << 20;
const MAX_ARCHIVES: usize = 16;
const MAX_EVENT_COUNT: usize = 32772;

pub(crate) struct Archive {
    directory: PathBuf,
    events: File,
    events_hash: Sha256,
    events_bytes: usize,
    events_count: usize,
    context_sha256: String,
    objects: BTreeMap<String, Value>,
    mandatory_bytes: usize,
    candidate_bytes: usize,
    maximum_candidate_bytes: usize,
}

fn new_json(path: &Path, value: &Value) -> Result<()> {
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .with_context(|| format!("evidence output must be fresh: {}", path.display()))?;
    serde_json::to_writer_pretty(&mut file, value)?;
    file.write_all(b"\n")?;
    Ok(())
}

impl Archive {
    pub(crate) fn new(
        directory: &Path,
        payload: &[u8],
        options: &SourceSearchOptions,
        compiler: &[String],
        cost_objective: Option<&Value>,
    ) -> Result<Self> {
        fs::create_dir(directory)?;
        fs::create_dir(directory.join("objects"))?;
        let executable = std::env::current_exe()?;
        let context = json!({"schema":SCHEMA,"input_payload_sha256":sha256(payload),
            "input_payload_bytes":payload.len(),"options":options,"compiler_argv":compiler,
            "working_directory":std::env::current_dir()?.canonicalize()?,
            "nvcompact":{"version":env!("CARGO_PKG_VERSION"),"executable_sha256":sha256(&fs::read(executable)?)},
            "cost_objective":cost_objective,
            "comparison_scope":if cost_objective.is_some(){"exact-context"}else{"run-local: opaque cost callback"},
            "retention":{"additional_source_bytes":options.max_retained_source_bytes,
                "mandatory_input_bytes_at_most":2*crate::notation::MAX_SOURCE,
                "event_bytes_at_most":MAX_EVENTS,"event_count_at_most":MAX_EVENT_COUNT},
            "execution":"archive comparison never executes recorded commands"});
        ensure!(
            serde_json::to_vec_pretty(&context)?.len() < MAX_METADATA,
            "attempt context exceeds metadata bound"
        );
        new_json(&directory.join("context.json"), &context)?;
        let context_sha256 = sha256(&fs::read(directory.join("context.json"))?);
        let events = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(directory.join("events.jsonl"))?;
        let mut archive = Self {
            directory: directory.to_owned(),
            events,
            events_hash: Sha256::new(),
            events_bytes: 0,
            events_count: 0,
            context_sha256,
            objects: BTreeMap::new(),
            mandatory_bytes: 0,
            candidate_bytes: 0,
            maximum_candidate_bytes: options.max_retained_source_bytes,
        };
        archive.input("original-payload", payload)?;
        Ok(archive)
    }

    fn snapshot(&mut self, data: &[u8], role: &str, mandatory: bool) -> Result<bool> {
        ensure!(
            data.len() <= crate::notation::MAX_SOURCE,
            "attempt source exceeds input bound"
        );
        let hash = sha256(data);
        if self.objects.contains_key(&hash) {
            return Ok(true);
        }
        if !mandatory
            && data.len()
                > self
                    .maximum_candidate_bytes
                    .saturating_sub(self.candidate_bytes)
        {
            return Ok(false);
        }
        ensure!(
            self.objects.len() < MAX_EVENT_COUNT,
            "attempt object count exceeded"
        );
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(self.directory.join("objects").join(&hash))?;
        file.write_all(data)?;
        self.objects
            .insert(hash, json!({"bytes":data.len(),"role":role}));
        if mandatory {
            self.mandatory_bytes += data.len();
        } else {
            self.candidate_bytes += data.len();
        }
        Ok(true)
    }

    pub(crate) fn input(&mut self, role: &str, data: &[u8]) -> Result<()> {
        ensure!(
            matches!(role, "original-payload" | "original-source"),
            "unknown mandatory input role"
        );
        ensure!(
            self.mandatory_bytes + data.len() <= 2 * crate::notation::MAX_SOURCE,
            "mandatory attempt inputs exceed bound"
        );
        self.snapshot(data, role, true)?;
        Ok(())
    }

    pub(crate) fn source(&mut self, data: &[u8]) -> Result<bool> {
        self.snapshot(data, "candidate-source", false)
    }

    pub(crate) fn append(&mut self, value: &Value) -> Result<()> {
        let mut line = serde_json::to_vec(value)?;
        line.push(b'\n');
        ensure!(
            self.events_count < MAX_EVENT_COUNT
                && line.len() <= MAX_EVENTS.saturating_sub(self.events_bytes),
            "attempt journal hard bound exceeded; prior evidence remains on disk"
        );
        self.events.write_all(&line)?;
        self.events.flush()?;
        self.events_hash.update(&line);
        self.events_bytes += line.len();
        self.events_count += 1;
        Ok(())
    }

    pub(crate) fn finish(&mut self, outcome: Value) -> Result<Value> {
        self.append(&json!({"stage":"search-finished","outcome":outcome}))?;
        let index = json!({"schema":SCHEMA,"context_sha256":self.context_sha256,
            "events_sha256":hex::encode(self.events_hash.clone().finalize()),
            "events_bytes":self.events_bytes,"events_count":self.events_count,
            "objects":self.objects,"mandatory_input_bytes":self.mandatory_bytes,
            "retained_candidate_source_bytes":self.candidate_bytes,
            "candidate_source_byte_limit":self.maximum_candidate_bytes,"outcome":outcome});
        new_json(&self.directory.join("index.json"), &index)?;
        let comparison = compare(&[self.directory.clone()])?;
        new_json(&self.directory.join("comparison.json"), &comparison)?;
        Ok(
            json!({"schema":SCHEMA,"directory":"attempts","index":"attempts/index.json",
            "comparison":"attempts/comparison.json","events":self.events_count,
            "retained_candidate_source_bytes":self.candidate_bytes,
            "candidate_source_byte_limit":self.maximum_candidate_bytes,
            "comparison_scope":"recorded costs and outcomes only; no revalidation or promotion"}),
        )
    }
}

fn read_bounded(path: &Path, maximum: usize, remaining: &mut usize) -> Result<Vec<u8>> {
    let file = OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
        .open(path)?;
    let metadata = file.metadata()?;
    ensure!(
        metadata.file_type().is_file() && metadata.len() <= maximum.min(*remaining) as u64,
        "attempt input is not a bounded regular file: {}",
        path.display()
    );
    let mut data = Vec::new();
    file.take(maximum.min(*remaining) as u64 + 1)
        .read_to_end(&mut data)?;
    ensure!(
        data.len() <= maximum.min(*remaining),
        "attempt input grew past read bound"
    );
    *remaining -= data.len();
    Ok(data)
}

fn valid_hash(hash: &str) -> bool {
    hash.len() == 64
        && hash
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

struct Retained {
    path: PathBuf,
    context: Value,
    index: Value,
    events: Vec<Value>,
    comparison_context: Value,
    key: String,
    comparable: bool,
}

fn load(path: &Path, remaining: &mut usize) -> Result<Retained> {
    let directory = if path.is_dir() {
        path
    } else {
        ensure!(
            path.file_name().is_some_and(|n| n == "index.json"),
            "expected attempt archive directory or index.json"
        );
        path.parent().context("attempt index has no directory")?
    }
    .canonicalize()?;
    let index: Value = serde_json::from_slice(&read_bounded(
        &directory.join("index.json"),
        MAX_METADATA,
        remaining,
    )?)?;
    ensure!(
        index["schema"] == SCHEMA,
        "unsupported attempt archive schema"
    );
    let context_bytes = read_bounded(&directory.join("context.json"), MAX_METADATA, remaining)?;
    ensure!(
        index["context_sha256"] == sha256(&context_bytes),
        "attempt context hash mismatch"
    );
    let context: Value = serde_json::from_slice(&context_bytes)?;
    ensure!(
        context["schema"] == SCHEMA,
        "unsupported attempt context schema"
    );
    let event_bytes = read_bounded(&directory.join("events.jsonl"), MAX_EVENTS, remaining)?;
    ensure!(
        index["events_sha256"] == sha256(&event_bytes)
            && index["events_bytes"].as_u64() == Some(event_bytes.len() as u64),
        "attempt journal hash/length mismatch"
    );
    let events: Vec<Value> = event_bytes
        .split(|&b| b == b'\n')
        .filter(|b| !b.is_empty())
        .map(serde_json::from_slice)
        .collect::<std::result::Result<_, _>>()?;
    ensure!(
        events.len() <= MAX_EVENT_COUNT
            && index["events_count"].as_u64() == Some(events.len() as u64),
        "attempt journal count mismatch"
    );
    ensure!(
        events.last().is_some_and(
            |event| event["stage"] == "search-finished" && event["outcome"] == index["outcome"]
        ),
        "attempt journal is not sealed by its outcome"
    );
    ensure!(
        matches!(
            index["outcome"]["status"].as_str(),
            Some("completed" | "budget-exhausted" | "failed")
        ),
        "attempt outcome status is missing or invalid"
    );
    let final_record = &index["outcome"]["final"];
    if index["outcome"]["status"] != "failed" {
        for key in ["source_sha256", "payload_sha256"] {
            ensure!(
                final_record[key].as_str().is_some_and(valid_hash),
                "final attempt identity missing: {key}"
            );
        }
        ensure!(
            final_record["whole_file_bytes"].as_u64().is_some()
                && final_record["source_bytes"].as_u64().is_some()
                && final_record["payload_bytes"].as_u64().is_some()
                && final_record["style"].as_str().is_some(),
            "final attempt cost/style/length missing"
        );
    }
    let objects = index["objects"]
        .as_object()
        .context("attempt objects missing")?;
    ensure!(objects.len() <= MAX_EVENT_COUNT, "too many attempt objects");
    for (hash, description) in objects {
        ensure!(valid_hash(hash), "invalid attempt object hash");
        let data = read_bounded(
            &directory.join("objects").join(hash),
            crate::notation::MAX_SOURCE,
            remaining,
        )?;
        ensure!(
            sha256(&data) == *hash && description["bytes"].as_u64() == Some(data.len() as u64),
            "attempt source snapshot hash/length mismatch: {hash}"
        );
    }
    let original = context["input_payload_sha256"]
        .as_str()
        .context("missing attempt input identity")?;
    ensure!(
        valid_hash(original) && objects.contains_key(original),
        "original payload snapshot missing"
    );
    if index["outcome"]["status"] != "failed" {
        let hash = final_record["source_sha256"].as_str().unwrap();
        ensure!(
            objects
                .get(hash)
                .is_some_and(|object| object["bytes"] == final_record["source_bytes"]),
            "final source snapshot missing or length differs"
        );
    }
    for event in &events {
        if matches!(
            event["stage"].as_str(),
            Some("spelling-candidate" | "condition-candidate" | "composed-candidate")
        ) {
            for hash in [&event["variant"]["sha256"], &event["base_source_sha256"]] {
                ensure!(
                    hash.as_str().is_some_and(|h| objects.contains_key(h)),
                    "candidate or source-basis snapshot missing"
                );
            }
            let hash = event["variant"]["sha256"].as_str().unwrap();
            ensure!(
                event["variant"]["id"].is_string()
                    && event["round"].as_u64().is_some()
                    && event["variant"]["bytes"].as_u64().is_some()
                    && event["variant"]["bytes"] == objects[hash]["bytes"],
                "candidate identity/length missing"
            );
        }
        if matches!(
            event["stage"].as_str(),
            Some("complete-file-cost" | "complete-file-cost-failed" | "baseline-cost")
        ) {
            ensure!(
                event["payload_sha256"].as_str().is_some_and(valid_hash),
                "measured payload identity missing"
            );
            if event["stage"] != "complete-file-cost-failed" {
                ensure!(
                    event["whole_file_bytes"].as_u64().is_some()
                        && event["payload_bytes"].as_u64().is_some(),
                    "measurement cost/length missing"
                );
            }
            if event["stage"] != "baseline-cost" {
                ensure!(
                    event["source_sha256"]
                        .as_str()
                        .is_some_and(|hash| objects.contains_key(hash))
                        && event["round"].as_u64().is_some()
                        && event["id"].is_string()
                        && event["style"].is_string(),
                    "measured source identity missing"
                );
            }
        }
    }
    let pinned = events
        .iter()
        .find(|e| e["stage"] == "search-context")
        .cloned()
        .unwrap_or(Value::Null);
    ensure!(
        !pinned.is_null()
            || !events.iter().any(|e| matches!(
                e["stage"].as_str(),
                Some("baseline-cost" | "complete-file-cost" | "complete-file-cost-failed")
            )),
        "measured attempt lacks its source/compiler context"
    );
    if !pinned.is_null() {
        ensure!(
            pinned["input_source_sha256"]
                .as_str()
                .is_some_and(|h| objects.contains_key(h)),
            "original source snapshot missing"
        );
    }
    let baseline_events: Vec<&Value> = events
        .iter()
        .filter(|event| event["stage"] == "baseline-compile")
        .collect();
    let baselines: Vec<Value> = baseline_events
        .iter()
        .filter_map(|event| native_observation(&event["native"]))
        .collect();
    let reproducible_baseline = baseline_events.len() == 2
        && baselines.len() == 2
        && baselines[0] == baselines[1]
        && baselines[0]["compiler_sha256"] == pinned["compiler"]["sha256"];
    let options = &context["options"];
    let frontend = &options["candidates"]["frontend"];
    let comparison_context = json!({"input_payload_sha256":original,
        "input_source_sha256":pinned["input_source_sha256"],"compiler_argv":context["compiler_argv"],
        "compiler_sha256":pinned["compiler"]["sha256"],"frontend_sha256":pinned["frontend"]["sha256"],
        "nvcompact":context["nvcompact"],"cost_objective":context["cost_objective"],
        "baseline_native":if reproducible_baseline {baselines.first()}else{None},
        "working_directory":context["working_directory"],
        "contracts":{"target":options["candidates"]["target"],"embedding":options["embedding"],
            "embedding_contract":options["embedding_contract"],"standard":frontend["standard"],
            "compiler_args":frontend["compiler_args"],"source_path":frontend["source_path"],
            "token_contract":frontend["token_contract"]}});
    let comparable = context["cost_objective"].is_object()
        && reproducible_baseline
        && pinned["compiler"]["sha256"]
            .as_str()
            .is_some_and(valid_hash)
        && pinned["frontend"]["sha256"]
            .as_str()
            .is_some_and(valid_hash)
        && pinned["input_source_sha256"]
            .as_str()
            .is_some_and(valid_hash);
    let key = if comparable {
        sha256(&serde_json::to_vec(&comparison_context)?)
    } else {
        format!("run-local:{}", directory.display())
    };
    Ok(Retained {
        path: directory,
        context,
        index,
        events,
        comparison_context,
        key,
        comparable,
    })
}

fn native_observation(native: &Value) -> Option<Value> {
    if native["returncode"] != 0
        || native["timed_out"] != false
        || native["output_limited"] != false
        || native["bytes"].as_u64().is_none()
    {
        return None;
    }
    let mut result = json!({"bytes":native["bytes"]});
    for key in [
        "sha256",
        "compiler_sha256",
        "stdout_sha256",
        "stderr_sha256",
    ] {
        if !native[key].as_str().is_some_and(valid_hash) {
            return None;
        }
        result[key] = native[key].clone();
    }
    Some(result)
}

fn identity(event: &Value) -> String {
    serde_json::to_string(&json!([
        event["round"],
        event["id"],
        event["source_sha256"]
    ]))
    .unwrap()
}

fn relation(cost: Option<u64>, baseline: Option<u64>) -> &'static str {
    match (cost, baseline) {
        (Some(cost), Some(base)) if cost < base => "smaller",
        (Some(cost), Some(base)) if cost == base => "equal",
        (Some(_), Some(_)) => "larger",
        _ => "unmeasured",
    }
}

fn rows(archive: &Retained, run: usize) -> Vec<Value> {
    let baseline = archive
        .events
        .iter()
        .find(|e| e["stage"] == "baseline-cost");
    let baseline_cost = baseline.and_then(|e| e["whole_file_bytes"].as_u64());
    let outcome = &archive.index["outcome"];
    let final_record = &outcome["final"];
    let original_source = &archive.comparison_context["input_source_sha256"];
    let mut candidates = BTreeMap::<String, Value>::new();
    let mut statuses = HashMap::<String, Value>::new();
    let mut measured = Vec::new();
    for event in &archive.events {
        match event["stage"].as_str() {
            Some("spelling-candidate" | "condition-candidate" | "composed-candidate") => {
                let variant = &event["variant"];
                let candidate = json!({"round":event["round"],"id":variant["id"],"source_sha256":variant["sha256"],
                    "source_bytes":variant["bytes"],"base_source_sha256":event["base_source_sha256"],
                    "derivation_stage":event["stage"]});
                candidates.insert(identity(&candidate), candidate);
            }
            Some("complete-file-cost" | "complete-file-cost-failed") => {
                measured.push(event.clone())
            }
            Some(
                "composition-admitted"
                | "condition-admitted"
                | "semantic-rejected"
                | "candidate-compile",
            ) => {
                let key = identity(event);
                let old = statuses.entry(key).or_insert_with(|| json!({}));
                if event["stage"] == "candidate-compile" {
                    old["native"] = event["native"].clone();
                } else {
                    old["decision"] = event.clone();
                }
            }
            _ => (),
        }
    }
    let mut output = Vec::new();
    let completed = matches!(
        outcome["status"].as_str(),
        Some("completed" | "budget-exhausted")
    );
    let mut measured_keys = HashSet::new();
    if let Some(base) = baseline {
        output.push(
            json!({"run":run,"id":"baseline","source_sha256":original_source,
            "payload_sha256":base["payload_sha256"],"payload_bytes":base["payload_bytes"],
            "whole_file_bytes":base["whole_file_bytes"],"size_relation":"equal",
            "semantic_status":"recorded-source-identity","outcome":"baseline",
            "selected_in_recorded_run":completed
                && final_record["payload_sha256"] == base["payload_sha256"]
                && final_record["source_sha256"] == *original_source
                && final_record["whole_file_bytes"] == base["whole_file_bytes"]}),
        );
    }
    for event in measured {
        let key = identity(&event);
        let candidate = candidates.get(&key).cloned().unwrap_or(Value::Null);
        measured_keys.insert(key.clone());
        let status = statuses.get(&key);
        let decision = status.map(|s| &s["decision"]);
        let native = status.map(|s| &s["native"]);
        let final_match = completed
            && event["stage"] == "complete-file-cost"
            && event["source_sha256"] == final_record["source_sha256"]
            && event["payload_sha256"] == final_record["payload_sha256"]
            && event["whole_file_bytes"] == final_record["whole_file_bytes"];
        let mut semantic = "not-checked";
        if original_source.as_str().is_some_and(valid_hash)
            && event["source_sha256"] == *original_source
        {
            semantic = "recorded-source-identity";
        }
        if let Some(decision) = decision {
            match decision["stage"].as_str() {
                Some("semantic-rejected") => semantic = "rejected",
                Some("composition-admitted" | "condition-admitted")
                    if native_observation(&decision["native"]).is_some_and(|native| {
                        native == archive.comparison_context["baseline_native"]
                    }) =>
                {
                    semantic = "recorded-verified";
                }
                _ => (),
            }
        }
        if let Some(native) = native.filter(|v| v.is_object()) {
            if native["timed_out"] == true
                || native["output_limited"] == true
                || native["returncode"].as_i64().is_some_and(|code| code < 0)
            {
                semantic = "incomplete";
            } else if native["returncode"] != 0 || native["sha256"].is_null() {
                semantic = "compile-failed";
            }
        }
        let selected =
            final_match && matches!(semantic, "recorded-verified" | "recorded-source-identity");
        let cost = event["whole_file_bytes"].as_u64();
        let size_relation = relation(cost, baseline_cost);
        let reason = decision
            .map(|d| d["reason"].clone())
            .filter(|v| !v.is_null())
            .unwrap_or_else(|| event["reason"].clone());
        let disposition = if event["stage"] == "complete-file-cost-failed" {
            "cost-failed"
        } else if selected {
            "selected-in-recorded-run"
        } else if matches!(semantic, "rejected" | "compile-failed" | "incomplete") {
            semantic
        } else if semantic == "recorded-verified" {
            "verified-but-not-final"
        } else if event["whole_file_bytes"]
            .as_u64()
            .zip(event["compared_to_whole_file_bytes"].as_u64())
            .is_some_and(|(a, b)| a >= b)
        {
            "not-smaller-than-incumbent"
        } else {
            "not-admitted"
        };
        output.push(json!({"run":run,"round":event["round"],"id":event["id"],
            "source_sha256":event["source_sha256"],"source_bytes":event["source_bytes"],
            "base_source_sha256":candidate["base_source_sha256"],"style":event["style"],
            "payload_sha256":event["payload_sha256"],"payload_bytes":event["payload_bytes"],
            "whole_file_bytes":event["whole_file_bytes"],"baseline_whole_file_bytes":baseline_cost,
            "size_relation":size_relation,"compared_to_whole_file_bytes":event["compared_to_whole_file_bytes"],
            "incumbent_size_relation":relation(cost,event["compared_to_whole_file_bytes"].as_u64()),
            "semantic_status":semantic,"outcome":disposition,"reason":reason,
            "selected_in_recorded_run":selected,"cost_reused":event["cost_reused"]}));
    }
    for (key, candidate) in candidates {
        if measured_keys.contains(&key) {
            continue;
        }
        let mut row = candidate;
        row["run"] = json!(run);
        row["size_relation"] = json!("unmeasured");
        row["semantic_status"] = json!("not-checked");
        row["outcome"] = json!("unmeasured");
        row["reason"] = if outcome["exhaustion_reason"].is_null() {
            json!("not reached before search completion or failure")
        } else {
            outcome["exhaustion_reason"].clone()
        };
        row["selected_in_recorded_run"] = json!(false);
        output.push(row);
    }
    output
}

/// Verify retained file hashes and rank historical measurements only within an
/// exact cost/observation/tool/input context. No archived argv is executed.
pub fn compare(paths: &[PathBuf]) -> Result<Value> {
    ensure!(
        (1..=MAX_ARCHIVES).contains(&paths.len()),
        "compare-attempts requires 1..16 archives"
    );
    let mut remaining = MAX_READ;
    let mut groups = BTreeMap::<String, (Value, Vec<Value>, Vec<usize>, bool)>::new();
    let mut runs = Vec::new();
    for (run, path) in paths.iter().enumerate() {
        let archive = load(path, &mut remaining)?;
        let group = groups.entry(archive.key.clone()).or_insert_with(|| {
            (
                archive.comparison_context.clone(),
                Vec::new(),
                Vec::new(),
                archive.comparable,
            )
        });
        group.1.extend(rows(&archive, run));
        group.2.push(run);
        runs.push(json!({"run":run,"archive":archive.path,"context_sha256":archive.index["context_sha256"],
            "events_sha256":archive.index["events_sha256"],"status":archive.index["outcome"]["status"],
            "exhaustion_reason":archive.index["outcome"]["exhaustion_reason"],
            "comparison_group":archive.key,"comparison_scope":archive.context["comparison_scope"],
            "outcome":archive.index["outcome"]}));
    }
    let groups: Vec<Value> = groups.into_iter().map(|(key,(context,mut rows,runs,comparable))| {
        rows.sort_by(|a,b|(a["whole_file_bytes"].as_u64().unwrap_or(u64::MAX),a["run"].as_u64(),a["id"].as_str(),a["style"].as_str())
            .cmp(&(b["whole_file_bytes"].as_u64().unwrap_or(u64::MAX),b["run"].as_u64(),b["id"].as_str(),b["style"].as_str())));
        json!({"id":key,"cross_run_comparable":comparable,"context":context,"runs":runs,"rows":rows})
    }).collect();
    Ok(
        json!({"schema":COMPARISON_SCHEMA,"runs":runs,"groups":groups,
        "comparison":"ranked whole-file measurements within exact contexts; separate groups must not be ranked together",
        "semantics":"historical recorded status only; size never grants acceptance",
        "execution":"none: no compiler, target, loader, codec or archived command is executed",
        "revalidation":"not performed; new searches and replays require fresh applicable guards",
        "bounds":{"maximum_archives":MAX_ARCHIVES,"read_bytes":MAX_READ-remaining,"maximum_read_bytes":MAX_READ}}),
    )
}

pub fn compare_to_file(paths: &[PathBuf], output: &Path) -> Result<Value> {
    let result = compare(paths)?;
    if let Some(parent) = output.parent().filter(|p| !p.as_os_str().is_empty()) {
        fs::create_dir_all(parent)?;
    }
    new_json(output, &result)?;
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    const INPUT: &[u8] = b"int main(void){return 0;}\n";
    const CANDIDATE: &[u8] = b"int main(void){return 00;}\n";

    fn fixture(directory: &Path, objective: Option<Value>, decision: &str) -> Archive {
        let mut archive = Archive::new(
            directory,
            INPUT,
            &SourceSearchOptions::default(),
            &["recorded-compiler-not-executed".into()],
            objective.as_ref(),
        )
        .unwrap();
        archive.input("original-source", INPUT).unwrap();
        let tool = sha256(b"owned synthetic compiler identity");
        archive
            .append(
                &json!({"stage":"search-context","input_source_sha256":sha256(INPUT),
            "compiler":{"sha256":tool},"frontend":{"sha256":sha256(b"owned frontend identity")}}),
            )
            .unwrap();
        let native = json!({"returncode":0,"timed_out":false,"output_limited":false,"bytes":100,
            "sha256":sha256(b"native"),"compiler_sha256":tool,
            "stdout_sha256":sha256(b""),"stderr_sha256":sha256(b"")});
        for attempt in 1..=2 {
            archive
                .append(&json!({"stage":"baseline-compile","attempt":attempt,"native":native}))
                .unwrap();
        }
        archive
            .append(&json!({"stage":"baseline-cost","whole_file_bytes":80,
            "payload_bytes":INPUT.len(),"payload_sha256":sha256(INPUT)}))
            .unwrap();
        archive.source(CANDIDATE).unwrap();
        archive.append(&json!({"stage":"spelling-candidate","round":1,
            "base_source_sha256":sha256(INPUT),"variant":{"id":"owned-spelling","sha256":sha256(CANDIDATE),
                "bytes":CANDIDATE.len(),"audit":[{"guard":"owned synthetic record; no command execution"}]}})).unwrap();
        for (style, cost) in [("first", 79), ("second", 81)] {
            archive
                .append(
                    &json!({"stage":"complete-file-cost","round":1,"id":"owned-spelling",
                "source_sha256":sha256(CANDIDATE),"source_bytes":CANDIDATE.len(),"style":style,
                "payload_sha256":sha256(style.as_bytes()),"payload_bytes":CANDIDATE.len(),
                "whole_file_bytes":cost,"compared_to_whole_file_bytes":80}),
                )
                .unwrap();
        }
        if decision == "compile-failed" || decision == "incomplete" {
            archive.append(&json!({"stage":"candidate-compile","round":1,"id":"owned-spelling",
                "source_sha256":sha256(CANDIDATE),"native":{"returncode":if decision=="incomplete"{-24}else{1},
                    "timed_out":false,"output_limited":false}})).unwrap();
        }
        if decision == "native-only" {
            archive
                .append(
                    &json!({"stage":"candidate-compile","round":1,"id":"owned-spelling",
                "source_sha256":sha256(CANDIDATE),"native":native}),
                )
                .unwrap();
        }
        if !matches!(decision, "not-checked" | "native-only") {
            archive
                .append(
                    &json!({"stage":"semantic-rejected","round":1,"id":"owned-spelling",
                "source_sha256":sha256(CANDIDATE),"reason":"owned rejection receipt"}),
                )
                .unwrap();
        }
        archive
    }

    fn completed() -> Value {
        json!({"status":"completed","final":{"source_sha256":sha256(INPUT),"source_bytes":INPUT.len(),
            "payload_sha256":sha256(INPUT),"payload_bytes":INPUT.len(),"style":"direct","whole_file_bytes":80}})
    }

    #[test]
    fn comparison_keeps_failure_and_unchecked_costs_separate_from_acceptance() {
        let root = tempfile::tempdir().unwrap();
        let objective = json!({"header_sha256":sha256(b"header"),"codec":{"format":"owned"}});
        let mut paths = Vec::new();
        for status in ["not-checked", "rejected", "compile-failed", "incomplete"] {
            let path = root.path().join(status);
            let mut archive = fixture(&path, Some(objective.clone()), status);
            archive.finish(completed()).unwrap();
            paths.push(path);
        }
        let result = compare(&paths).unwrap();
        assert_eq!(result["groups"].as_array().unwrap().len(), 1);
        for row in result["groups"][0]["rows"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|row| row["id"] == "owned-spelling")
        {
            let run = row["run"].as_u64().unwrap() as usize;
            assert_eq!(
                row["semantic_status"],
                ["not-checked", "rejected", "compile-failed", "incomplete"][run]
            );
            assert_eq!(row["base_source_sha256"], sha256(INPUT));
            assert_eq!(row["selected_in_recorded_run"], false);
        }
        let output = root.path().join("comparison.json");
        compare_to_file(&paths, &output).unwrap();
        assert!(
            compare_to_file(&paths, &output).is_err(),
            "comparison must not overwrite evidence"
        );
        fs::write(paths[0].join("objects").join(sha256(CANDIDATE)), b"changed").unwrap();
        assert!(
            format!("{:#}", compare(&paths).unwrap_err()).contains("snapshot hash/length mismatch")
        );
        let path = root.path().join("native-only");
        let mut archive = fixture(&path, Some(objective), "native-only");
        let mut outcome = completed();
        outcome["final"] = json!({"source_sha256":sha256(CANDIDATE),"source_bytes":CANDIDATE.len(),
            "payload_sha256":sha256(b"first"),"payload_bytes":CANDIDATE.len(),"style":"first","whole_file_bytes":79});
        archive.finish(outcome).unwrap();
        let result = compare(&[path]).unwrap();
        assert!(result["groups"][0]["rows"]
            .as_array()
            .unwrap()
            .iter()
            .all(|row| row["selected_in_recorded_run"] == false));
        assert!(result["groups"][0]["rows"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|row| row["id"] == "owned-spelling")
            .all(|row| row["semantic_status"] == "not-checked"));
    }

    #[test]
    fn cost_contract_mismatch_and_opaque_callbacks_do_not_merge() {
        let root = tempfile::tempdir().unwrap();
        let mut paths = Vec::new();
        for (index, objective) in [
            Some(json!({"codec":"a","header_bytes":1})),
            Some(json!({"codec":"a","header_bytes":2})),
            None,
            None,
        ]
        .into_iter()
        .enumerate()
        {
            let path = root.path().join(index.to_string());
            fixture(&path, objective, "not-checked")
                .finish(completed())
                .unwrap();
            paths.push(path);
        }
        let result = compare(&paths).unwrap();
        assert_eq!(result["groups"].as_array().unwrap().len(), 4);
        assert_eq!(
            result["groups"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|group| group["cross_run_comparable"] == false)
                .count(),
            2
        );
        // A valid record that changes its baseline native observation belongs
        // to a separate context even when the compiler executable is unchanged.
        let path = root.path().join("changed-baseline");
        let mut archive = fixture(
            &path,
            Some(json!({"codec":"a","header_bytes":1})),
            "not-checked",
        );
        archive
            .append(&json!({"stage":"baseline-compile","native":{"returncode":1}}))
            .unwrap();
        archive.finish(completed()).unwrap();
        let changed = compare(&[path]).unwrap();
        assert_eq!(changed["groups"][0]["cross_run_comparable"], false);
    }

    #[test]
    fn malformed_measurements_cannot_turn_nulls_into_selected_identity() {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("missing-status");
        let mut archive = fixture(&path, None, "not-checked");
        archive
            .append(&json!({"stage":"complete-file-cost"}))
            .unwrap();
        assert!(archive.finish(json!({})).is_err());
        assert!(compare(&[path]).is_err());
        let path = root.path().join("missing-identities");
        let mut archive = fixture(&path, None, "not-checked");
        archive
            .append(&json!({"stage":"complete-file-cost"}))
            .unwrap();
        assert!(archive.finish(completed()).is_err());
        assert!(compare(&[path]).is_err());
        let path = root.path().join("retention-bound");
        let mut options = SourceSearchOptions::default();
        options.max_retained_source_bytes = 0;
        let mut archive =
            Archive::new(&path, INPUT, &options, &["never-executed".into()], None).unwrap();
        archive.input("original-source", INPUT).unwrap();
        assert!(!archive.source(CANDIDATE).unwrap());
        assert!(
            archive.source(INPUT).unwrap(),
            "original source remains retained"
        );
    }
}
