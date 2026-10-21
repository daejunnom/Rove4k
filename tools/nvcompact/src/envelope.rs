//! Repack inspected submission envelopes without inferring arbitrary shell ASTs.
//! A measured minimum is not automatically an accepted chess submission.
use crate::{
    codec::{self, CodecPortfolio, Recipe},
    envelope_cost::{CacheBudget, WholeFileObjective},
    process, sha256, write_json,
};
use anyhow::{bail, ensure, Context, Result};
use regex::bytes::Regex;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::fs;
use std::io::Read;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use std::time::Instant;

const MAX_ARTIFACT: usize = 4 << 20;

fn bounded_file(path: &Path, maximum: usize) -> Result<Vec<u8>> {
    let file = fs::File::open(path)?;
    let metadata = file.metadata()?;
    ensure!(
        metadata.is_file() && metadata.len() <= maximum as u64,
        "regular file exceeds {maximum}-byte input profile: {}",
        path.display()
    );
    let mut data = Vec::new();
    file.take(maximum as u64 + 1).read_to_end(&mut data)?;
    ensure!(
        data.len() <= maximum,
        "file grew past the input profile: {}",
        path.display()
    );
    Ok(data)
}

#[derive(Clone, Debug)]
pub struct EnvelopeOptions {
    pub thorough: bool,
    pub notation: bool,
    pub jobs: usize,
    /// Explicit external artifact location; never downloads or vendors input.
    pub artifact: Option<PathBuf>,
}
impl Default for EnvelopeOptions {
    fn default() -> Self {
        Self {
            thorough: false,
            notation: true,
            jobs: 2,
            artifact: None,
        }
    }
}

#[derive(Clone, Debug)]
struct Payload {
    id: String,
    data: Vec<u8>,
    equivalence: String,
}

fn text<'a>(value: &'a Value, key: &str) -> Result<&'a str> {
    value
        .get(key)
        .and_then(Value::as_str)
        .with_context(|| format!("missing string {key}"))
}
fn tail() -> &'static Regex {
    static PATTERN: OnceLock<Regex> = OnceLock::new();
    PATTERN.get_or_init(|| Regex::new(r"tail -(c|n)\s*\+(\d+)").unwrap())
}
fn count(data: &[u8], needle: &[u8]) -> usize {
    if needle.is_empty() {
        0
    } else {
        data.windows(needle.len())
            .filter(|part| *part == needle)
            .count()
    }
}
fn splice(data: &[u8], begin: usize, end: usize, replacement: &[u8]) -> Vec<u8> {
    let mut output = Vec::with_capacity(data.len() + replacement.len());
    output.extend_from_slice(&data[..begin]);
    output.extend_from_slice(replacement);
    output.extend_from_slice(&data[end..]);
    output
}

fn inspected_header<'a>(artifact: &'a [u8], spec: &Value) -> Result<&'a [u8]> {
    let header = if let Some(value) = spec.get("header") {
        let declared = value
            .as_str()
            .context("header must be a string")?
            .as_bytes();
        ensure!(
            artifact.starts_with(declared),
            "exact inspected header does not match artifact"
        );
        &artifact[..declared.len()]
    } else {
        let length = spec
            .get("header_bytes")
            .and_then(Value::as_u64)
            .context("header or header_bytes is required")?;
        ensure!(
            length > 0 && length <= artifact.len() as u64,
            "inspected header length exceeds artifact"
        );
        ensure!(
            spec.get("header_sha256").and_then(Value::as_str).is_some(),
            "metadata-only header requires header_sha256"
        );
        &artifact[..length as usize]
    };
    if let Some(length) = spec.get("header_bytes") {
        ensure!(
            length.as_u64() == Some(header.len() as u64),
            "header_bytes disagrees with inspected header"
        );
    }
    if let Some(expected) = spec.get("header_sha256") {
        ensure!(
            expected.as_str() == Some(sha256(header).as_str()),
            "inspected header hash differs from manifest"
        );
    }
    ensure!(
        header.ends_with(b"\n"),
        "inspected header must end in a newline"
    );
    Ok(header)
}

pub fn extract(artifact: &[u8], spec: &Value) -> Result<(Vec<u8>, Vec<u8>)> {
    ensure!(
        artifact.len() <= MAX_ARTIFACT,
        "artifact exceeds 4 MiB input bound"
    );
    let header = inspected_header(artifact, spec)?;
    ensure!(
        tail().find_iter(header).count() == 1,
        "exactly one supported tail offset is required"
    );
    let captures = tail().captures(header).unwrap();
    let expected = if &captures[1] == b"c" {
        header.len() + 1
    } else {
        header.iter().filter(|&&b| b == b'\n').count() + 1
    };
    let offset: usize = std::str::from_utf8(&captures[2])?.parse()?;
    ensure!(
        offset == expected,
        "submitted tail offset disagrees with exact header"
    );
    let decoder = text(spec, "decoder")?;
    ensure!(
        decoder.is_ascii() && count(header, decoder.as_bytes()) == 1,
        "decoder span is ambiguous or not ASCII"
    );
    let recipe: Recipe = serde_json::from_value(
        spec.get("payload_codec")
            .context("missing payload_codec")?
            .clone(),
    )?;
    Ok((
        header.to_vec(),
        codec::decode(&artifact[header.len()..], &recipe, codec::MAX_PAYLOAD)?,
    ))
}

pub fn make_header(
    header: &[u8],
    old_decoder: &str,
    new_decoder: &str,
    style: &str,
) -> Result<Vec<u8>> {
    ensure!(
        old_decoder.is_ascii()
            && new_decoder.is_ascii()
            && count(header, old_decoder.as_bytes()) == 1,
        "decoder replacement must identify one exact ASCII span"
    );
    let position = header
        .windows(old_decoder.len())
        .position(|part| part == old_decoder.as_bytes())
        .unwrap();
    let mut output = splice(
        header,
        position,
        position + old_decoder.len(),
        new_decoder.as_bytes(),
    );
    ensure!(
        tail().find_iter(&output).count() == 1,
        "exactly one supported tail offset is required"
    );
    if style != "original" {
        ensure!(
            matches!(style, "lines" | "bytes"),
            "unsupported tail spelling"
        );
        let range = tail().find(&output).unwrap();
        output = splice(
            &output,
            range.start(),
            range.end(),
            if style == "lines" {
                b"tail -n+0"
            } else {
                b"tail -c+0"
            },
        );
    }
    for _ in 0..16 {
        let captures = tail()
            .captures(&output)
            .context("tail offset disappeared")?;
        let offset = if &captures[1] == b"c" {
            output.len() + 1
        } else {
            output.iter().filter(|&&b| b == b'\n').count() + 1
        };
        let range = captures.get(2).unwrap();
        let changed = splice(
            &output,
            range.start(),
            range.end(),
            offset.to_string().as_bytes(),
        );
        if changed == output {
            return Ok(output);
        }
        output = changed;
    }
    bail!("tail offset did not converge")
}

pub fn best_header(header: &[u8], old_decoder: &str, new_decoder: &str) -> Result<Vec<u8>> {
    let mut best = make_header(header, old_decoder, new_decoder, "original")?;
    for style in ["lines", "bytes"] {
        let candidate = make_header(header, old_decoder, new_decoder, style)?;
        if candidate.len() < best.len() {
            best = candidate;
        }
    }
    Ok(best)
}

/// Only argv is accepted. This does not execute a shell or evaluate quoting.
pub fn decoder_command(decoder: &str) -> Result<Vec<String>> {
    ensure!(
        !decoder.is_empty() && decoder.is_ascii(),
        "decoder must be nonempty ASCII argv"
    );
    let words: Vec<String> = decoder
        .split_ascii_whitespace()
        .map(str::to_owned)
        .collect();
    ensure!(
        !words.is_empty()
            && words.iter().all(|word| word
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || b"_./=,+-".contains(&byte))),
        "unsupported decoder argv spelling"
    );
    Ok(words)
}

fn actual_decoder(
    blob: &[u8],
    decoder: &str,
    payload: &[u8],
    cwd: &Path,
    permit_original_failure: bool,
) -> Result<Value> {
    let command = decoder_command(decoder)?;
    let binary = process::resolve_tool(&command[0])?;
    let before = sha256(&fs::read(&binary)?);
    let output = process::run(
        &command,
        blob,
        cwd,
        &process::Limits {
            seconds: 10.0,
            output_bytes: codec::MAX_PAYLOAD + 65536,
            ..Default::default()
        },
    )?;
    ensure!(
        sha256(&fs::read(&binary)?) == before,
        "deployment decoder changed during check"
    );
    if !output.success() || output.stdout != payload {
        if permit_original_failure {
            return Ok(
                json!({"argv":command,"executable":binary,"executable_sha256":before,"status":"fail",
                "returncode":output.code,"stderr":String::from_utf8_lossy(&output.stderr),
                "meaning":"original deployment command failed; independent decoded payload hash remains checked"}),
            );
        }
        bail!(
            "deployment decoder failed byte identity: {decoder}; exit {}; {}",
            output.code,
            String::from_utf8_lossy(&output.stderr)
        );
    }
    Ok(
        json!({"argv":command,"executable":binary,"executable_sha256":before,
        "payload_sha256":sha256(payload),"status":"pass"}),
    )
}

fn executable(path: &Path, data: &[u8]) -> Result<()> {
    fs::write(path, data)?;
    fs::set_permissions(path, fs::Permissions::from_mode(0o755))?;
    Ok(())
}
fn fresh_directory(output: &Path) -> Result<PathBuf> {
    ensure!(
        !output.exists(),
        "output directory must be fresh: {}",
        output.display()
    );
    fs::create_dir_all(output)?;
    Ok(output.canonicalize()?)
}
fn runtime_fingerprint() -> Result<Value> {
    let binary = std::env::current_exe()?;
    Ok(
        json!({"version":env!("CARGO_PKG_VERSION"),"executable_sha256":sha256(&fs::read(&binary)?),
        "codecs":codec::library_versions(),"runtime":"Rust"}),
    )
}

fn compile_argv(manifest: &Value) -> Result<Option<Vec<String>>> {
    manifest
        .get("compile_argv")
        .map(|value| {
            value
                .as_array()
                .context("compile_argv must be an array")?
                .iter()
                .map(|word| {
                    word.as_str()
                        .map(str::to_owned)
                        .context("compile argv word must be string")
                })
                .collect()
        })
        .transpose()
}

pub(crate) fn native_fingerprint(
    source: &[u8],
    argv: &[String],
    directory: &Path,
    limits: &process::Limits,
) -> Result<Value> {
    ensure!(!argv.is_empty(), "compile_argv must not be empty");
    fs::create_dir_all(directory)?;
    let output = directory.join("compiled-engine");
    if output.exists() {
        fs::remove_file(&output)?;
    }
    let name = output
        .to_str()
        .context("compiler output path must be UTF-8")?;
    let command: Vec<String> = argv
        .iter()
        .map(|word| word.replace("{output}", name))
        .collect();
    ensure!(
        argv.iter().any(|word| word.contains("{output}")),
        "compile_argv must declare {{output}} placeholder"
    );
    let compiler = process::resolve_tool(&command[0])?;
    let fingerprint = sha256(&fs::read(&compiler)?);
    let result = process::run(&command, source, directory, limits)?;
    ensure!(
        sha256(&fs::read(&compiler)?) == fingerprint,
        "compiler changed during source comparison"
    );
    let mut detail = json!({"argv":command,"returncode":result.code,"compiler_sha256":fingerprint,
        "stdout_sha256":sha256(&result.stdout),"stderr_sha256":sha256(&result.stderr),
        "stderr":String::from_utf8_lossy(&result.stderr[result.stderr.len().saturating_sub(8192)..]),
        "seconds":result.wall_seconds,"timed_out":result.timed_out,"output_limited":result.output_limited});
    if result.success() && output.is_file() {
        let native = bounded_file(&output, 64 << 20)?;
        detail["sha256"] = json!(sha256(&native));
        detail["bytes"] = json!(native.len());
    }
    Ok(detail)
}

fn payload_variants(
    payload: &[u8],
    manifest: &Value,
    out: &Path,
    notation: bool,
) -> Result<(Vec<Payload>, Vec<Value>)> {
    let mut values = vec![Payload {
        id: "raw".into(),
        data: payload.to_vec(),
        equivalence: "decoded payload byte identity".into(),
    }];
    let mut reports = Vec::new();
    if !notation || manifest.get("language").is_none() {
        return Ok((values, reports));
    }
    let language = text(manifest, "language")?;
    let options = manifest.get("notation").cloned().unwrap_or(json!({}));
    let opts = crate::notation::NotationOptions {
        language: language.into(),
        target: options
            .get("target")
            .and_then(Value::as_str)
            .map(str::to_owned),
        token_contract: options
            .get("token_contract")
            .and_then(Value::as_str)
            .unwrap_or("opaque")
            .into(),
        compact: options
            .get("compact")
            .and_then(Value::as_bool)
            .unwrap_or(true),
        max_variants: 13,
    };
    let candidates = crate::notation::generate_variants(payload, &opts)?;
    let compiler = compile_argv(manifest)?;
    let limits: process::Limits =
        serde_json::from_value(manifest.get("compile_limits").cloned().unwrap_or(json!({})))?;
    let builddir = out.join("native-equivalence");
    // A Python bootstrap's optional compiler recipe describes embedded C, not
    // the Python payload. Python notation has its own typed-AST contract.
    let baseline = if let Some(argv) = compiler.as_ref().filter(|_| language != "python") {
        let record = native_fingerprint(payload, argv, &builddir, &limits)?;
        reports.push(json!({"id":"baseline","native":record}));
        Some(record)
    } else {
        None
    };
    let mut seen = HashMap::from([(sha256(payload), "raw".to_string())]);
    for item in candidates {
        if item.data == payload {
            continue;
        }
        let digest = sha256(&item.data);
        let mut report = json!({"id":item.id,"bytes":item.data.len(),"sha256":digest,
            "audit":item.audit,"notes":item.notes,"contract":item.contract});
        if let Some(previous) = seen.get(&digest) {
            report["duplicate_source_of"] = json!(previous);
            report["compiled_again"] = json!(false);
            reports.push(report);
            continue;
        }
        seen.insert(digest, item.id.clone());
        let (accepted, equivalence) = if language == "python" {
            // The notation module verifies its Python AST representation before
            // returning a changed candidate; no Python backend is invoked here.
            (
                true,
                "typed Python AST identity under explicit source observation contract",
            )
        } else if let (Some(argv), Some(base)) = (&compiler, &baseline) {
            let native = native_fingerprint(&item.data, argv, &builddir, &limits)?;
            let accepted =
                base.get("sha256").is_some() && native.get("sha256") == base.get("sha256");
            report["native"] = native;
            (
                accepted,
                "complete native bytes identical under submitted compile recipe",
            )
        } else {
            (
                false,
                "changed compiled source requires an explicit compile recipe",
            )
        };
        report["accepted"] = json!(accepted);
        report["equivalence"] = json!(equivalence);
        reports.push(report);
        if accepted {
            values.push(Payload {
                id: item.id,
                data: item.data,
                equivalence: equivalence.into(),
            });
        }
    }
    Ok((values, reports))
}

/// A separate replay owns a new objective and bypasses measurement caches.
fn evaluate(
    variant: &Payload,
    recipe: &Recipe,
    header: &[u8],
    old_decoder: &str,
) -> Result<(Value, Vec<u8>)> {
    WholeFileObjective::new(
        header,
        old_decoder,
        CodecPortfolio::fixed(vec![recipe.clone()])?,
        1,
        CacheBudget::disabled(),
    )?
    .fresh_evaluate_recipe(&variant.id, &variant.data, &variant.equivalence, recipe)
}

pub fn check_deployed_payload(
    path: &Path,
    record: &Value,
    manifest: &Value,
    original: &[u8],
    payload: &[u8],
) -> Result<Value> {
    let Some(spec) = manifest.get("envelope") else {
        return Ok(json!({"status":"native_payload_checked_by_packer"}));
    };
    let header = inspected_header(original, spec)?;
    let (prefix, decoder) = if record["id"] == "identity" {
        (header.to_vec(), text(spec, "decoder")?.to_string())
    } else {
        let recipe = record.get("recipe").context("candidate recipe missing")?;
        let decoder = if recipe["format"] == "submitted" {
            text(recipe, "decoder")?.into()
        } else {
            codec::decoder_for(&serde_json::from_value(recipe.clone())?)?
        };
        (
            best_header(header, text(spec, "decoder")?, &decoder)?,
            decoder,
        )
    };
    let captures = tail().captures(&prefix).context("tail offset missing")?;
    let flag = format!(
        "-{}+{}",
        std::str::from_utf8(&captures[1])?,
        std::str::from_utf8(&captures[2])?
    );
    let command = vec![
        "tail".into(),
        flag,
        path.canonicalize()?
            .to_str()
            .context("artifact path must be UTF-8")?
            .into(),
    ];
    let full = bounded_file(path, MAX_ARTIFACT)?;
    ensure!(
        full.starts_with(&prefix),
        "candidate prefix changed before decoder check"
    );
    let tail_binary = process::resolve_tool("tail")?;
    let tail_sha = sha256(&fs::read(&tail_binary)?);
    let suffix = process::run(
        &command,
        b"",
        path.parent().unwrap(),
        &process::Limits {
            seconds: 10.0,
            ..Default::default()
        },
    )?;
    suffix.check("deployed tail")?;
    ensure!(
        suffix.stdout == full[prefix.len()..],
        "deployed tail failed to restore exact compressed suffix"
    );
    ensure!(
        sha256(&fs::read(&tail_binary)?) == tail_sha,
        "tail executable changed during check"
    );
    if record["id"] == "submitted-payload" {
        let original_header = header.len();
        ensure!(
            suffix.stdout == original[original_header..],
            "submitted compressed payload changed"
        );
    }
    Ok(
        json!({"tail_argv":command,"tail_status":"pass","tail_executable_sha256":tail_sha,
        "decoder":actual_decoder(&suffix.stdout,&decoder,payload,path.parent().unwrap(),false)?}),
    )
}

pub fn run(manifest_path: &Path, output: &Path, options: &EnvelopeOptions) -> Result<Value> {
    ensure!((1..=16).contains(&options.jobs), "jobs must be 1..16");
    let manifest_path = manifest_path.canonicalize()?;
    let manifest: Value = serde_json::from_slice(&bounded_file(&manifest_path, 16 << 20)?)?;
    let category = text(&manifest, "category")?;
    ensure!(
        matches!(category, "4k" | "4k-elf"),
        "category must be 4k or 4k-elf"
    );
    for key in ["allow_section_header_removal", "allow_load_zero_tail"] {
        if let Some(value) = manifest.get(key) {
            ensure!(value.is_boolean(), "{key} must be a JSON boolean");
        }
    }
    ensure!(
        manifest["allow_load_zero_tail"] != true
            || manifest["allow_section_header_removal"] == true,
        "allow_load_zero_tail also requires allow_section_header_removal"
    );
    let source = match &options.artifact {
        Some(path) => path.canonicalize()?,
        None => manifest_path
            .parent()
            .unwrap()
            .join(text(&manifest, "artifact")?)
            .canonicalize()?,
    };
    let original = bounded_file(&source, MAX_ARTIFACT)?;
    ensure!(
        original.len() <= MAX_ARTIFACT && sha256(&original) == text(&manifest, "sha256")?,
        "submitted artifact size/hash differs from manifest"
    );
    if category == "4k-elf" {
        ensure!(
            original.starts_with(b"\x7fELF") && manifest.get("envelope").is_none(),
            "ELF-only category requires a native ELF file and no script envelope"
        );
    }
    let output = fresh_directory(output)?;
    let started = Instant::now();
    executable(&output.join("original"), &original)?;
    let identity = json!({"id":"identity","bytes":original.len(),"sha256":sha256(&original),
        "variant":"raw","equivalence":"complete submitted file byte identity"});
    let mut records = vec![identity.clone()];
    let mut best = identity;
    let mut best_data = original.clone();
    let mut summary = json!({"format":"nvcompact.envelope.v2","version":env!("CARGO_PKG_VERSION"),
        "name":text(&manifest,"name")?,"manifest":manifest,"manifest_path":manifest_path,"artifact_path":source,
        "tool":runtime_fingerprint()?,"original_bytes":original.len(),"original_sha256":sha256(&original),
        "scope":"finite full-file codec/spelling portfolio; no global compression optimum or engine equivalence proof",
        "accepted":null,"uci":{"status":"not_run"},"notation":[],"options":{"thorough":options.thorough,"notation":options.notation,"jobs":options.jobs}});
    if let Some(spec) = manifest.get("envelope") {
        let (header, payload) = extract(&original, spec)?;
        let pinned = manifest.get("payload_sha256").and_then(Value::as_str);
        if let Some(expected) = pinned {
            ensure!(
                sha256(&payload) == expected,
                "decoded payload differs from independent payload hash"
            );
        }
        let old_decoder = text(spec, "decoder")?;
        let original_blob = &original[header.len()..];
        let original_decoder = actual_decoder(
            original_blob,
            old_decoder,
            &payload,
            &output,
            pinned.is_some(),
        )?;
        summary["original_deployment_equivalent"] = json!(original_decoder["status"] == "pass");
        summary["original_decoder_check"] = original_decoder;
        fs::write(output.join("original-payload"), &payload)?;
        summary["payload_sha256"] = json!(sha256(&payload));
        summary["payload_bytes"] = json!(payload.len());
        let (mut variants, reports) =
            payload_variants(&payload, &manifest, &output, options.notation)?;
        summary["notation"] = json!(reports);
        let submitted_recipe: Recipe = serde_json::from_value(spec["payload_codec"].clone())?;
        let mut objective = WholeFileObjective::new(
            &header,
            old_decoder,
            CodecPortfolio::legacy(options.thorough, Some(submitted_recipe.clone())),
            options.jobs,
            CacheBudget::default(),
        )?;
        if options.notation {
            if let Some(search_spec) = manifest.get("source_search") {
                let mut search: crate::source_search::SourceSearchOptions =
                    serde_json::from_value(search_spec.clone())?;
                ensure!(
                    manifest["language"]
                        == if search.embedding.is_some() {
                            "python"
                        } else {
                            "c"
                        },
                    "source search requires C or an explicitly declared Python bytes embedding"
                );
                if search_spec.get("compile_limits").is_none() {
                    if let Some(limits) = manifest.get("compile_limits") {
                        search.compile_limits = serde_json::from_value(limits.clone())?;
                    }
                }
                let compiler = compile_argv(&manifest)?
                    .context("source search requires the submitted C compile_argv recipe")?;
                let cost_decoder = codec::decoder_for(&submitted_recipe)?;
                let cost_header = best_header(&header, old_decoder, &cost_decoder)?;
                let cost_objective = json!({"kind":"inspected-envelope-fixed-codec-v1","category":category,
                    "inspected_header_sha256":sha256(&header),"inspected_header_bytes":header.len(),
                    "cost_header_sha256":sha256(&cost_header),"cost_header_bytes":cost_header.len(),
                    "inspected_decoder":old_decoder,"cost_decoder":cost_decoder,
                    "codec":submitted_recipe,"implementation":summary["tool"],
                    "scope":"entire encoded payload plus entire inspected cost header; no engine execution"});
                let portfolio_search = match manifest.get("source_search_portfolio") {
                    Some(value) => value
                        .as_bool()
                        .context("source_search_portfolio must be a boolean")?,
                    None => true,
                };
                let searched = crate::envelope_source::search(
                    &payload,
                    &search,
                    &compiler,
                    &mut objective,
                    &submitted_recipe,
                    &output,
                    cost_objective,
                    &summary["tool"],
                    portfolio_search,
                )?;
                summary["source_search_budget"] = json!({"strategies":searched.len(),
                    "maximum_complete_payload_evaluations":searched.len()*search.max_evaluations,
                    "maximum_combination_attempts":searched.len()*search.max_combinations,
                    "total_scheduling_seconds":searched.len() as f64*search.max_seconds,
                    "scope":"separate per-strategy scheduling deadlines; bounded in-flight operation and final acceptance may complete afterward; codec scratch and final portfolio are separate",
                    "codec_cache":"shared across strategies and final comparison"});
                let mut strategy_summaries = Vec::new();
                for mut candidate in searched {
                    let existing = variants.iter().find(|v| v.data == candidate.data);
                    candidate.summary["canonical_variant"] =
                        json!(existing.map_or(candidate.id.as_str(), |v| v.id.as_str()));
                    candidate.summary["alias_of"] = existing.map_or(Value::Null, |v| json!(v.id));
                    if existing.is_none() {
                        variants.push(Payload { id: candidate.id.clone(), data: candidate.data,
                            equivalence: "unchanged C bytes or verified typed source derivation; complete native and compiler diagnostic byte identity; exact payload readback under declared embedding contract".into() });
                    }
                    strategy_summaries.push(candidate.summary);
                }
                summary["source_search"] = strategy_summaries[0].clone();
                summary["source_search_portfolio"] = json!(strategy_summaries);
            }
        }
        let submitted_decoder = codec::decoder_for(&submitted_recipe)?;
        let prefix = best_header(&header, old_decoder, &submitted_decoder)?;
        let mut submitted = prefix.clone();
        submitted.extend_from_slice(original_blob);
        let submitted_record = json!({"id":"submitted-payload","variant":"raw","bytes":submitted.len(),
            "sha256":sha256(&submitted),"header_bytes":prefix.len(),
            "packed_bytes":original_blob.len(),"equivalence":"original compressed payload; inspected tail/decoder spelling",
            "recipe":{"format":"submitted","decoder":submitted_decoder}});
        if submitted.len() < best_data.len() {
            best = submitted_record.clone();
            best_data = submitted;
        }
        records.push(submitted_record);
        let mut per_variant = Vec::new();
        for variant in &variants {
            let evaluated = objective.evaluate(&variant.id, &variant.data, &variant.equivalence)?;
            records.extend(evaluated.records);
            if evaluated.data.len() < best_data.len() {
                best = evaluated.best.clone();
                best_data = evaluated.data;
            }
            let mut result = evaluated.best;
            result["coverage"] = evaluated.coverage;
            per_variant.push(result);
        }
        summary["variants"] = json!(per_variant);
        let selected = variants
            .iter()
            .find(|item| json!(item.id) == best["variant"])
            .context("winning payload variant missing")?;
        let regenerated = if best["id"] == "identity" {
            original.clone()
        } else if best["id"] == "submitted-payload" {
            let mut data = best_header(&header, old_decoder, text(&best["recipe"], "decoder")?)?;
            data.extend_from_slice(original_blob);
            data
        } else {
            objective
                .fresh_evaluate_recipe(
                    &selected.id,
                    &selected.data,
                    &selected.equivalence,
                    &serde_json::from_value(best["recipe"].clone())?,
                )?
                .1
        };
        ensure!(
            regenerated == best_data,
            "selected compression recipe does not reproduce exactly"
        );
        summary["cost_evaluator"] =
            json!({"context":objective.context(),"statistics":objective.stats()});
        executable(&output.join("smallest"), &best_data)?;
        if best["id"] != "identity" {
            summary["smallest_payload_check"] = check_deployed_payload(
                &output.join("smallest"),
                &best,
                &manifest,
                &original,
                &selected.data,
            )?;
            fs::write(output.join("selected-payload"), &selected.data)?;
        }
    } else if original.starts_with(b"\x7fELF") {
        let allow = manifest
            .get("allow_section_header_removal")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let zero_tail = manifest
            .get("allow_load_zero_tail")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        for deployed in crate::elf::deployment_variants_with_options(&original, allow, zero_tail)? {
            let choices = if category == "4k-elf" {
                vec!["raw".to_string()]
            } else {
                crate::pack::candidate_ids("x86_64-unknown-linux-gnu", None)?
            };
            for pack_id in choices {
                if deployed.id == "original" && pack_id == "raw" {
                    continue;
                }
                let packed =
                    crate::pack::pack_by_id(&deployed.data, "x86_64-unknown-linux-gnu", &pack_id)?;
                let record = json!({"id":format!("{}-{pack_id}",deployed.id),"variant":"raw","bytes":packed.data.len(),
                    "sha256":sha256(&packed.data),"recipe":{"format":"native_pack","pack_id":pack_id,"deployment":deployed.id},
                    "equivalence":if deployed.id=="original"{"original native ELF restored byte-for-byte under loader contract"}
                        else{"explicit ELF deployment contract; native file roundtrip only"},
                    "deployment_preconditions":deployed.preconditions,"packing":packed});
                if packed.data.len() < best_data.len() {
                    best = record.clone();
                    best_data = packed.data;
                }
                records.push(record);
            }
        }
        let regenerated = regenerate_native(&original, &best, &manifest)?;
        ensure!(
            regenerated == best_data,
            "selected native recipe does not reproduce"
        );
        executable(&output.join("smallest"), &best_data)?;
    } else {
        executable(&output.join("smallest"), &best_data)?;
        summary["unsupported_transform_scope"] =
            json!("No inspected compressed envelope or native ELF; identity preserved");
    }
    summary["winner"] = best;
    summary["saved_bytes"] = json!(original.len() - best_data.len());
    summary["no_size_regression"] = json!(best_data.len() <= original.len());
    summary["candidates"] = json!(records.len());
    summary["compression_seconds"] = json!(started.elapsed().as_secs_f64());
    summary["recipe_rebuild"] =
        json!("pass; a separate reproduce invocation is still recorded independently");
    summary["acceptance"] = json!(
        "no_accepted_artifact; measurement_only; protocol and competition rule review are separate"
    );
    ensure!(
        bounded_file(&source, MAX_ARTIFACT)? == original
            && bounded_file(&output.join("smallest"), MAX_ARTIFACT)? == best_data,
        "input or winning artifact mutated during campaign"
    );
    write_json(&output.join("candidates.json"), &records)?;
    let mut summary_bytes = serde_json::to_vec_pretty(&summary)?;
    summary_bytes.push(b'\n');
    ensure!(summary_bytes.len() <= 32 << 20,
        "completed envelope summary exceeds the 32 MiB replay input bound; detailed outputs were retained");
    fs::write(output.join("summary.json"), summary_bytes)?;
    Ok(summary)
}

fn regenerate_native(original: &[u8], record: &Value, manifest: &Value) -> Result<Vec<u8>> {
    if record["id"] == "identity" {
        return Ok(original.to_vec());
    }
    ensure!(
        record["recipe"]["format"] == "native_pack",
        "unknown native replay recipe"
    );
    let deployment = record["recipe"]
        .get("deployment")
        .and_then(Value::as_str)
        .unwrap_or("original");
    let allow = manifest["allow_section_header_removal"]
        .as_bool()
        .unwrap_or(false);
    let zero_tail = manifest["allow_load_zero_tail"].as_bool().unwrap_or(false);
    let native = crate::elf::deployment_variants_with_options(original, allow, zero_tail)?
        .into_iter()
        .find(|candidate| candidate.id == deployment)
        .context("recorded ELF deployment lacks its declaration or is unavailable")?
        .data;
    let id = text(&record["recipe"], "pack_id")?;
    ensure!(
        manifest["category"] != "4k-elf" || id == "raw",
        "ELF-only replay cannot use a script loader"
    );
    Ok(crate::pack::pack_by_id(&native, "x86_64-unknown-linux-gnu", id)?.data)
}

fn derive_payload(summary: &Value, record: &Value, payload: &[u8], work: &Path) -> Result<Payload> {
    let id = text(record, "variant")?;
    if id == "raw" {
        return Ok(Payload {
            id: id.into(),
            data: payload.to_vec(),
            equivalence: "decoded payload byte identity".into(),
        });
    }
    let source_recipe = summary
        .get("source_search_portfolio")
        .and_then(Value::as_array)
        .and_then(|all| all.iter().find(|item| item["variant"].as_str() == Some(id)))
        .or_else(|| {
            (summary["source_search"]["variant"].as_str() == Some(id))
                .then_some(&summary["source_search"])
        });
    if let Some(searched) = source_recipe {
        let compiler = compile_argv(&summary["manifest"])?
            .context("recorded source search compile recipe is missing")?;
        let data = crate::source_search::replay(
            payload,
            &searched["recipe"],
            &compiler,
            &work.join("source-search"),
        )?;
        return Ok(Payload {
            id: id.into(),
            data,
            equivalence: text(record, "equivalence")?.into(),
        });
    }
    payload_variants(payload, &summary["manifest"], work, true)?
        .0
        .into_iter()
        .find(|item| item.id == id)
        .context("source derivation no longer produces the recorded accepted variant")
}

pub fn reproduce_record(
    summary: &Value,
    record: &Value,
    original: &[u8],
    work: &Path,
) -> Result<Vec<u8>> {
    ensure!(
        sha256(original) == text(summary, "original_sha256")?,
        "original artifact changed before replay"
    );
    let manifest = summary
        .get("manifest")
        .context("recorded manifest missing")?;
    let data = if record["id"] == "identity" {
        original.to_vec()
    } else if let Some(spec) = manifest.get("envelope") {
        let (header, payload) = extract(original, spec)?;
        if let Some(expected) = manifest.get("payload_sha256").and_then(Value::as_str) {
            ensure!(
                sha256(&payload) == expected,
                "independent payload hash changed during replay"
            );
        }
        if record["id"] == "submitted-payload" {
            let mut data = best_header(
                &header,
                text(spec, "decoder")?,
                text(&record["recipe"], "decoder")?,
            )?;
            data.extend_from_slice(&original[header.len()..]);
            data
        } else {
            let selected = derive_payload(summary, record, &payload, work)?;
            if let Some(expected) = record.get("payload_sha256").and_then(Value::as_str) {
                ensure!(
                    sha256(&selected.data) == expected,
                    "derived source payload changed"
                );
            }
            evaluate(
                &selected,
                &serde_json::from_value(record["recipe"].clone())?,
                &header,
                text(spec, "decoder")?,
            )?
            .1
        }
    } else {
        regenerate_native(original, record, manifest)?
    };
    ensure!(
        data.len() as u64 == record["bytes"].as_u64().context("missing recipe size")?
            && sha256(&data) == text(record, "sha256")?,
        "exact final-file replay failed; fix its cause instead of adding an exception"
    );
    Ok(data)
}

pub fn reproduce(summary_path: &Path, output: &Path, selection: &str) -> Result<Value> {
    ensure!(
        matches!(selection, "smallest" | "accepted"),
        "selection must be smallest or accepted"
    );
    let summary_path = summary_path.canonicalize()?;
    let summary: Value = serde_json::from_slice(&bounded_file(&summary_path, 32 << 20)?)?;
    ensure!(summary["format"]=="nvcompact.envelope.v2","old Python recipes require their generating implementation; no silent version substitution");
    ensure!(
        summary["tool"] == runtime_fingerprint()?,
        "generating Rust executable or codec runtime changed"
    );
    let record = if selection == "smallest" {
        &summary["winner"]
    } else {
        &summary["accepted"]
    };
    ensure!(record.is_object(), "search has no {selection} candidate");
    let original = bounded_file(
        &summary_path.parent().unwrap().join("original"),
        MAX_ARTIFACT,
    )?;
    let output = fresh_directory(output)?;
    let data = reproduce_record(&summary, record, &original, &output)?;
    let path = output.join("reproduced");
    executable(&path, &data)?;
    let mut report = json!({"format":"nvcompact.envelope-replay.v2","selection":selection,"byte_replay":"pass",
        "expected_sha256":record["sha256"],"sha256":sha256(&data),"bytes":data.len(),
        "semantic_scope":record["equivalence"],"tool":runtime_fingerprint()?,"uci":{"status":"not_run"}});
    if record["id"] != "identity" && summary["manifest"].get("envelope").is_some() {
        let spec = &summary["manifest"]["envelope"];
        let (header, original_payload) = extract(&original, spec)?;
        // reproduce_record already regenerated and verified the source. Read
        // back this exact artifact for the independent deployed decoder check;
        // do not launch another source search or compile the same derivation twice.
        let payload = if record["id"] == "submitted-payload" {
            original_payload
        } else {
            let codec: Recipe = serde_json::from_value(record["recipe"].clone())?;
            let prefix = best_header(
                &header,
                text(spec, "decoder")?,
                &codec::decoder_for(&codec)?,
            )?;
            ensure!(
                data.starts_with(&prefix),
                "replayed header differs before decoder check"
            );
            let restored = codec::decode(&data[prefix.len()..], &codec, codec::MAX_PAYLOAD)?;
            ensure!(
                sha256(&restored) == text(record, "payload_sha256")?,
                "replayed payload hash differs"
            );
            restored
        };
        report["payload_check"] =
            check_deployed_payload(&path, record, &summary["manifest"], &original, &payload)?;
    }
    ensure!(
        bounded_file(&path, MAX_ARTIFACT)? == data,
        "reproduced artifact changed during check"
    );
    write_json(&output.join("replay.json"), &report)?;
    Ok(report)
}
