//! Repack inspected submission envelopes without inferring arbitrary shell ASTs.
//! A measured minimum is not automatically an accepted chess submission.
use crate::{
    codec::{self, Recipe},
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
use std::sync::{
    atomic::{AtomicUsize, Ordering},
    mpsc, OnceLock,
};
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

fn native_fingerprint(
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
    let baseline = if let Some(argv) = &compiler {
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

fn evaluate(
    variant: &Payload,
    recipe: &Recipe,
    header: &[u8],
    old_decoder: &str,
) -> Result<(Value, Vec<u8>)> {
    ensure!(!process::cancelled(), "cancelled before codec candidate");
    let blob = codec::compress(&variant.data, recipe)?;
    ensure!(
        codec::decode(&blob, recipe, codec::MAX_PAYLOAD)? == variant.data,
        "codec roundtrip changed payload"
    );
    let prefix = best_header(header, old_decoder, &codec::decoder_for(recipe)?)?;
    let mut data = prefix.clone();
    data.extend_from_slice(&blob);
    let id = sha256(&serde_json::to_vec(&json!([variant.id, recipe]))?)[..16].to_string();
    let record = json!({"id":id,"variant":variant.id,"recipe":recipe,"bytes":data.len(),
        "header_bytes":prefix.len(),"packed_bytes":blob.len(),"source_bytes":variant.data.len(),
        "sha256":sha256(&data),"payload_sha256":sha256(&variant.data),"equivalence":variant.equivalence});
    Ok((record, data))
}

/// At most `jobs` codecs and their result buffers run concurrently. Completion
/// order cannot change record order or tie selection. Streams never cross
/// thread boundaries and every scoped worker is joined before returning.
fn evaluate_batch(
    variant: &Payload,
    recipes: &[Recipe],
    header: &[u8],
    decoder: &str,
    jobs: usize,
) -> Result<(Vec<Value>, Value, Vec<u8>)> {
    ensure!(!recipes.is_empty(), "empty codec batch");
    let next = AtomicUsize::new(0);
    let (sender, receiver) = mpsc::sync_channel(jobs);
    let mut records = vec![Value::Null; recipes.len()];
    let mut best: Option<(usize, Value, Vec<u8>)> = None;
    let mut failure: Option<anyhow::Error> = None;
    std::thread::scope(|scope| {
        let mut handles = Vec::new();
        for _ in 0..jobs.min(recipes.len()) {
            let sender = sender.clone();
            let next = &next;
            handles.push(scope.spawn(move || loop {
                let index = next.fetch_add(1, Ordering::Relaxed);
                if index >= recipes.len() {
                    break;
                }
                let result = evaluate(variant, &recipes[index], header, decoder);
                if sender.send((index, result)).is_err() {
                    break;
                }
            }));
        }
        drop(sender);
        for (index, result) in receiver {
            match result {
                Ok((record, data)) => {
                    if best.as_ref().is_none_or(|(old_index, _, old)| {
                        (data.len(), index) < (old.len(), *old_index)
                    }) {
                        best = Some((index, record.clone(), data));
                    }
                    records[index] = record;
                }
                Err(error) => {
                    if failure.is_none() {
                        failure = Some(error);
                    }
                }
            }
        }
        for handle in handles {
            if handle.join().is_err() && failure.is_none() {
                failure = Some(anyhow::anyhow!("codec worker panicked"));
            }
        }
    });
    if let Some(error) = failure {
        return Err(error);
    }
    ensure!(
        records.iter().all(|item| !item.is_null()),
        "codec worker failed to return all recipes"
    );
    let (_, record, data) = best.context("no measured codec candidates")?;
    Ok((records, record, data))
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
        let (variants, reports) = payload_variants(&payload, &manifest, &output, options.notation)?;
        summary["notation"] = json!(reports);
        let submitted_recipe: Recipe = serde_json::from_value(spec["payload_codec"].clone())?;
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
            let initial = codec::recipes(variant.data.len(), options.thorough);
            let (measured, mut variant_best, mut variant_data) =
                evaluate_batch(variant, &initial, &header, old_decoder, options.jobs)?;
            let sizes: Vec<(Recipe, usize)> = initial
                .iter()
                .cloned()
                .zip(
                    measured
                        .iter()
                        .map(|item| item["bytes"].as_u64().unwrap() as usize),
                )
                .collect();
            records.extend(measured);
            let refinements = codec::refinements(&sizes, options.thorough);
            if !refinements.is_empty() {
                let (mut refined, record, data) =
                    evaluate_batch(variant, &refinements, &header, old_decoder, options.jobs)?;
                for item in &mut refined {
                    item["phase"] = json!("match-finder-refinement");
                }
                records.extend(refined);
                if data.len() < variant_data.len() {
                    variant_best = record;
                    variant_data = data;
                }
            }
            if variant_data.len() < best_data.len() {
                best = variant_best.clone();
                best_data = variant_data;
            }
            per_variant.push(variant_best);
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
            evaluate(
                selected,
                &serde_json::from_value(best["recipe"].clone())?,
                &header,
                old_decoder,
            )?
            .1
        };
        ensure!(
            regenerated == best_data,
            "selected compression recipe does not reproduce exactly"
        );
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
        for deployed in crate::elf::deployment_variants(&original, allow)? {
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
                        else{"explicit section-removal deployment contract; native file roundtrip only"},
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
    write_json(&output.join("summary.json"), &summary)?;
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
    let native = if deployment == "original" {
        original.to_vec()
    } else {
        ensure!(
            deployment == "no-section-headers" && manifest["allow_section_header_removal"] == true,
            "section removal replay lacks declaration"
        );
        crate::elf::sectionless(original)?
    };
    let id = text(&record["recipe"], "pack_id")?;
    ensure!(
        manifest["category"] != "4k-elf" || id == "raw",
        "ELF-only replay cannot use a script loader"
    );
    Ok(crate::pack::pack_by_id(&native, "x86_64-unknown-linux-gnu", id)?.data)
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
            let variant_id = text(record, "variant")?;
            let variants = if variant_id == "raw" {
                vec![Payload {
                    id: "raw".into(),
                    data: payload,
                    equivalence: "decoded payload byte identity".into(),
                }]
            } else {
                payload_variants(&payload, manifest, work, true)?.0
            };
            let selected = variants
                .iter()
                .find(|item| item.id == variant_id)
                .context("source derivation no longer produces the recorded accepted variant")?;
            if let Some(expected) = record.get("payload_sha256").and_then(Value::as_str) {
                ensure!(
                    sha256(&selected.data) == expected,
                    "derived source payload changed"
                );
            }
            evaluate(
                selected,
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
        let (_, payload) = extract(&original, spec)?;
        let payload = if record["variant"] == "raw" {
            payload
        } else {
            payload_variants(&payload, &summary["manifest"], &output, true)?
                .0
                .into_iter()
                .find(|item| json!(item.id) == record["variant"])
                .context("replay payload variant missing")?
                .data
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
