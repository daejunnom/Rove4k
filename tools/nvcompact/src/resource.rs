//! Read-only resource planning, followed by a separate explicit execution step.
//! Availability is an observation, not a reservation or an allocation guarantee.
use anyhow::{bail, Context, Result};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::os::unix::fs::PermissionsExt;
use std::path::{Component, Path, PathBuf};
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use crate::{
    process,
    uci::{self, UciConfig},
};

pub const SPEC_FORMAT: &str = "nvcompact.resource-spec.v1";
pub const PLAN_FORMAT: &str = "nvcompact.resource-plan.v2";
pub const RUN_FORMAT: &str = "nvcompact.resource-run.v2";
const JSON_LIMIT: u64 = 1 << 20;

fn read_json(path: &Path) -> Result<Value> {
    if fs::metadata(path)?.len() > JSON_LIMIT {
        bail!("JSON input exceeds one MiB: {}", path.display());
    }
    let data = fs::read(path)?;
    if data.len() as u64 > JSON_LIMIT {
        bail!("JSON input grew past one MiB: {}", path.display());
    }
    let value: Value = serde_json::from_slice(&data)?;
    if !value.is_object() {
        bail!("JSON input must be an object");
    }
    Ok(value)
}

fn absolute(path: &Path) -> Result<PathBuf> {
    // Do not collapse a/../ lexically: `a` may be a symlink, in which case the
    // kernel's traversal can identify a different file. Canonical targets are
    // recorded separately without changing the actual invocation spelling.
    Ok(if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir()?.join(path)
    })
}

fn fingerprint(path: &Path, role: &str) -> Result<Value> {
    let invocation = absolute(path)?;
    let resolved = fs::canonicalize(&invocation)?;
    let mut file = fs::File::open(&resolved)?;
    let state = file.metadata()?;
    if !state.is_file() {
        bail!("expected a regular input: {}", path.display());
    }
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 65536];
    let mut bytes = 0u64;
    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        digest.update(&buffer[..n]);
        bytes += n as u64;
    }
    if bytes != state.len() {
        bail!(
            "input size changed while fingerprinting: {}",
            path.display()
        );
    }
    Ok(
        json!({"role": role, "path": invocation, "resolved_path": resolved,
        "bytes": bytes, "mode": state.permissions().mode() & 0o777,
        "sha256": hex::encode(digest.finalize())}),
    )
}

fn digest(value: &Value) -> Result<String> {
    // serde_json's default map is ordered; plan digests are stable by key order.
    Ok(crate::sha256(&serde_json::to_vec(value)?))
}

fn write_new(path: &Path, value: &Value) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut file, value)?;
    file.write_all(b"\n")?;
    Ok(())
}

fn amount(path: &Path) -> Result<Option<u64>> {
    let text = fs::read_to_string(path)?;
    if text.trim() == "max" {
        Ok(None)
    } else {
        Ok(Some(text.trim().parse()?))
    }
}

fn fields(path: &Path) -> Result<BTreeMap<String, u64>> {
    let mut values = BTreeMap::new();
    for line in fs::read_to_string(path)?.lines() {
        let mut words = line.split_whitespace();
        if let (Some(key), Some(value)) = (words.next(), words.next()) {
            values.insert(key.trim_end_matches(':').to_owned(), value.parse()?);
        }
    }
    Ok(values)
}

fn unescape_mount(text: &str) -> String {
    text.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
}

fn rlimits() -> Value {
    let mut limits = json!({});
    for (name, kind) in [
        ("RLIMIT_AS", libc::RLIMIT_AS),
        ("RLIMIT_CPU", libc::RLIMIT_CPU),
        ("RLIMIT_FSIZE", libc::RLIMIT_FSIZE),
        ("RLIMIT_CORE", libc::RLIMIT_CORE),
        ("RLIMIT_STACK", libc::RLIMIT_STACK),
    ] {
        let mut pair = libc::rlimit {
            rlim_cur: 0,
            rlim_max: 0,
        };
        if unsafe { libc::getrlimit(kind, &mut pair) } == 0 {
            limits[name] = json!([
                if pair.rlim_cur == libc::RLIM_INFINITY {
                    None
                } else {
                    Some(pair.rlim_cur)
                },
                if pair.rlim_max == libc::RLIM_INFINITY {
                    None
                } else {
                    Some(pair.rlim_max)
                }
            ]);
        } else {
            limits[name] = Value::Null;
        }
    }
    limits
}

pub fn probe_resources() -> Value {
    probe_resources_from(Path::new("/proc"))
}

/// Accepting an explicit proc root makes nested cgroup behavior testable without
/// modifying real cgroups, process limits, or the parent environment.
pub fn probe_resources_from(proc_root: &Path) -> Value {
    let mut facts = json!({"platform": std::env::consts::OS, "memory": {}, "cgroup_v2": [], "errors": [], "rlimits": rlimits()});
    let mut errors = Vec::new();
    let mut cgroups = Vec::new();
    match fields(&proc_root.join("meminfo")) {
        Ok(values) => {
            if let (Some(total), Some(available)) =
                (values.get("MemTotal"), values.get("MemAvailable"))
            {
                facts["memory"] = json!({"physical_total_bytes": total.saturating_mul(1024), "physical_available_bytes": available.saturating_mul(1024)});
            } else {
                errors.push("MemTotal or MemAvailable missing".into());
            }
        }
        Err(e) => errors.push(format!("physical memory observation unavailable: {e}")),
    }
    let mut set: libc::cpu_set_t = unsafe { std::mem::zeroed() };
    facts["affinity_cpu_count"] =
        if unsafe { libc::sched_getaffinity(0, std::mem::size_of_val(&set), &mut set) } == 0 {
            json!(unsafe { libc::CPU_COUNT(&set) })
        } else {
            Value::Null
        };
    let online = unsafe { libc::sysconf(libc::_SC_NPROCESSORS_ONLN) };
    facts["online_cpu_count"] = if online > 0 {
        json!(online)
    } else {
        Value::Null
    };
    let mut common_flags: Option<BTreeSet<String>> = None;
    if let Ok(info) = fs::read_to_string(proc_root.join("cpuinfo")) {
        for line in info.lines() {
            let Some((key, values)) = line.split_once(':') else {
                continue;
            };
            if !matches!(key.trim(), "flags" | "Features") {
                continue;
            }
            let flags: BTreeSet<String> = values.split_whitespace().map(str::to_owned).collect();
            common_flags = Some(match common_flags {
                None => flags,
                Some(previous) => previous.intersection(&flags).cloned().collect(),
            });
        }
    }
    facts["common_cpu_flags"] = json!(common_flags);
    facts["proc_pid_namespace_matches"] = fs::read_to_string(proc_root.join("self/stat"))
        .ok()
        .and_then(|s| {
            s.split_whitespace()
                .next()
                .and_then(|v| v.parse::<u32>().ok())
        })
        .map_or(Value::Null, |pid| json!(pid == std::process::id()));
    let inspect = (|| -> Result<()> {
        let memberships = fs::read_to_string(proc_root.join("self/cgroup"))?;
        let unified = memberships
            .lines()
            .find_map(|line| line.strip_prefix("0::"));
        let memory_v1 = memberships.lines().any(|line| {
            line.split(':')
                .nth(1)
                .is_some_and(|v| v.split(',').any(|s| s == "memory"))
        });
        if unified.is_none() && memory_v1 {
            bail!("cgroup v1 memory accounting unsupported; require v2 or an unconfined host");
        }
        if let Some(membership) = unified {
            let membership = PathBuf::from(membership);
            if !membership.is_absolute()
                || membership
                    .components()
                    .any(|v| matches!(v, Component::ParentDir))
            {
                bail!("invalid cgroup membership path");
            }
            let mounts = fs::read_to_string(proc_root.join("self/mountinfo"))?;
            let mut locations = Vec::new();
            for line in mounts.lines() {
                let Some((before, after)) = line.split_once(" - ") else {
                    continue;
                };
                if after.split_whitespace().next() != Some("cgroup2") {
                    continue;
                }
                let parts: Vec<_> = before.split_whitespace().collect();
                if parts.len() < 5 {
                    bail!("incomplete cgroup mountinfo");
                }
                let mount_root = PathBuf::from(unescape_mount(parts[3]));
                let mount_at = PathBuf::from(unescape_mount(parts[4]));
                if let Ok(relative) = membership.strip_prefix(&mount_root) {
                    locations.push((mount_at.join(relative), mount_at));
                }
            }
            if locations.is_empty() {
                bail!("current cgroup v2 mount could not be resolved");
            }
            let mut seen = BTreeSet::new();
            for (mut current, mount_at) in locations {
                loop {
                    if !current.starts_with(&mount_at) {
                        bail!("cgroup escaped observed mount");
                    }
                    if seen.insert(current.clone()) {
                        let maximum = current.join("memory.max");
                        let usage = current.join("memory.current");
                        if maximum.exists() != usage.exists() {
                            bail!("incomplete cgroup memory files at {}", current.display());
                        }
                        if maximum.exists() {
                            let cap = amount(&maximum)?;
                            let used = amount(&usage)?.context("memory.current cannot be max")?;
                            let stat = if current.join("memory.stat").exists() {
                                fields(&current.join("memory.stat"))?
                            } else {
                                BTreeMap::new()
                            };
                            let inactive = stat
                                .get("inactive_file")
                                .copied()
                                .unwrap_or(0)
                                .min(stat.get("file").copied().unwrap_or(0))
                                .min(used);
                            let mut item = json!({"path": current, "memory_max_bytes": cap, "memory_current_bytes": used,
                                "inactive_file_bytes": inactive, "raw_headroom_bytes": cap.map(|n| n.saturating_sub(used)),
                                "estimated_available_bytes": cap.map(|n| n.saturating_sub(used.saturating_sub(inactive)))});
                            if current.join("cpu.max").exists() {
                                item["cpu_max"] =
                                    json!(fs::read_to_string(current.join("cpu.max"))?.trim());
                            }
                            cgroups.push(item);
                        }
                    }
                    if current == mount_at {
                        break;
                    }
                    current = current
                        .parent()
                        .context("cgroup path has no parent")?
                        .to_path_buf();
                }
            }
        }
        Ok(())
    })();
    if let Err(err) = inspect {
        errors.push(format!("cgroup observation unavailable: {err}"));
    }
    for key in ["RLIMIT_AS", "RLIMIT_CPU", "RLIMIT_FSIZE", "RLIMIT_CORE"] {
        if facts["rlimits"][key].is_null() {
            errors.push(format!("cannot read inherited {key}"));
        }
    }
    let mut available: Vec<u64> = facts["memory"]["physical_available_bytes"]
        .as_u64()
        .into_iter()
        .collect();
    available.extend(
        cgroups
            .iter()
            .filter_map(|v| v["estimated_available_bytes"].as_u64()),
    );
    facts["estimated_available_memory_bytes"] = json!(available.into_iter().min());
    facts["cgroup_v2"] = json!(cgroups);
    facts["errors"] = json!(errors);
    facts["memory_estimate_scope"] = json!("min(physical MemAvailable, every visible cgroup max-current+inactive_file); transient reclaim estimate, not reservation or allocation success");
    facts
}

fn number<'a>(value: &'a Value, key: &str) -> Result<u64> {
    value[key]
        .as_u64()
        .with_context(|| format!("budget.{key} must be an unsigned integer"))
}
fn validate_budget(budget: &Value) -> Result<()> {
    for key in [
        "required_memory_bytes",
        "reserve_memory_bytes",
        "address_space_bytes",
        "cpu_seconds_per_process",
        "file_bytes",
        "output_bytes_per_session",
    ] {
        let n = number(budget, key)?;
        if (n == 0 && key != "reserve_memory_bytes") || n > i64::MAX as u64 {
            bail!("invalid budget.{key}");
        }
    }
    if number(budget, "address_space_bytes")? < number(budget, "required_memory_bytes")? {
        bail!("address-space cap is below declared memory requirement");
    }
    number(budget, "required_memory_bytes")?
        .checked_add(number(budget, "reserve_memory_bytes")?)
        .context("memory budget overflow")?;
    let wall = budget["wall_seconds"]
        .as_f64()
        .context("wall_seconds must be a number")?;
    if !wall.is_finite() || wall <= 0.0 || wall > 86400.0 {
        bail!("wall_seconds must be positive, finite, and <=86400");
    }
    Ok(())
}

fn requested_limits(budget: &Value) -> Value {
    json!({"RLIMIT_AS": budget["address_space_bytes"], "RLIMIT_CPU": budget["cpu_seconds_per_process"],
        "RLIMIT_FSIZE": budget["file_bytes"], "RLIMIT_CORE": 0})
}

fn validate_preconditions(value: &Value) -> Result<()> {
    let fields = value
        .as_object()
        .context("preconditions must be an object")?;
    for (key, entry) in fields {
        match key.as_str() {
            "max_online_cpu_count" | "max_inherited_stack_bytes" => {
                if entry.as_u64().is_none_or(|n| n == 0) {
                    bail!("preconditions.{key} must be positive");
                }
            }
            "required_cpu_flags" => {
                let flags = entry
                    .as_array()
                    .context("required_cpu_flags must be an array")?;
                if flags.iter().any(|v| {
                    v.as_str().is_none_or(|s| {
                        s.is_empty() || !s.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_')
                    })
                }) {
                    bail!("invalid required CPU flag");
                }
            }
            _ => bail!("unknown resource precondition: {key}"),
        }
    }
    Ok(())
}

pub fn preflight(plan: &Value, facts: &Value) -> Value {
    let mut reasons = facts["errors"]
        .as_array()
        .cloned()
        .unwrap_or_else(|| vec![json!("resource errors missing")]);
    if facts["platform"] != "linux" {
        reasons.push(json!("resource execution supports Linux"));
    }
    let budget = &plan["budget"];
    let needed = budget["required_memory_bytes"]
        .as_u64()
        .and_then(|n| n.checked_add(budget["reserve_memory_bytes"].as_u64()?));
    let available = facts["estimated_available_memory_bytes"].as_u64();
    if needed.is_none() || available.is_none() || available < needed {
        reasons.push(json!(
            "declared memory plus reserve exceeds observed available estimate"
        ));
    }
    for (name, required) in requested_limits(budget).as_object().unwrap() {
        let values = facts["rlimits"][name].as_array();
        if values.is_none()
            || values.unwrap().iter().any(|v| {
                v.as_u64()
                    .is_some_and(|n| n < required.as_u64().unwrap_or(u64::MAX))
            })
        {
            reasons.push(json!(format!(
                "inherited {name} below planned limit; no limit will be raised"
            )));
        }
    }
    if let Some(tools) = plan["tools"].as_array() {
        for tool in tools {
            if tool["path"].is_null() {
                reasons.push(json!(format!("declared tool missing: {}", tool["name"])));
            }
        }
    }
    if let Some(maximum) = plan["preconditions"]["max_online_cpu_count"].as_u64() {
        if facts["online_cpu_count"]
            .as_u64()
            .is_none_or(|n| n > maximum)
        {
            reasons.push(json!("online CPU count exceeds or cannot verify the declared resource profile; worker counts are not changed"));
        }
    }
    if let Some(maximum) = plan["preconditions"]["max_inherited_stack_bytes"].as_u64() {
        if facts["rlimits"]["RLIMIT_STACK"][0]
            .as_u64()
            .is_none_or(|n| n > maximum)
        {
            reasons.push(json!("inherited stack bound exceeds or cannot verify the declared resource profile; stack limits are not changed"));
        }
    }
    if let Some(required) = plan["preconditions"]["required_cpu_flags"].as_array() {
        let flags = facts["common_cpu_flags"].as_array();
        for flag in required {
            if flags.is_none_or(|values| !values.contains(flag)) {
                reasons.push(json!(format!(
                    "required CPU flag not observed across visible CPUs: {flag}"
                )));
            }
        }
    }
    json!({"status": if reasons.is_empty() { "ready" } else { "blocked" }, "reasons": reasons,
        "declared_required_plus_reserve_bytes": needed, "estimated_available_memory_bytes": available,
        "scope": "read-only prerequisites; ready is neither execution nor protocol success"})
}

fn resolve_declared(name: &str, base: &Path) -> Result<PathBuf> {
    let path = Path::new(name);
    let lookup = if path.components().count() > 1 && !path.is_absolute() {
        base.join(path).to_string_lossy().into_owned()
    } else {
        name.into()
    };
    let result = process::resolve_tool(&lookup)?;
    if fs::metadata(&result)?.permissions().mode() & 0o111 == 0 {
        bail!("declared tool is not executable: {}", result.display());
    }
    Ok(result)
}

pub fn create_plan(spec_path: &Path) -> Result<Value> {
    let spec_path = fs::canonicalize(spec_path)?;
    let base = spec_path.parent().context("specification needs a parent")?;
    let spec = read_json(&spec_path)?;
    if spec["format"] != SPEC_FORMAT {
        bail!("unsupported resource specification format");
    }
    let mut pins = vec![fingerprint(&spec_path, "specification")?];
    let mut manifest = Value::Null;
    let artifact_path = if let Some(path) = spec["manifest"].as_str() {
        let path = fs::canonicalize(base.join(path))?;
        manifest = read_json(&path)?;
        pins.push(fingerprint(&path, "engine_manifest")?);
        absolute(
            &path.parent().unwrap().join(
                manifest["artifact"]
                    .as_str()
                    .context("engine manifest missing artifact")?,
            ),
        )?
    } else {
        absolute(
            &base.join(
                spec["artifact"]
                    .as_str()
                    .context("specification needs artifact or manifest")?,
            ),
        )?
    };
    let artifact = fingerprint(&artifact_path, "artifact")?;
    let expected = if manifest.is_null() {
        &spec["sha256"]
    } else {
        &manifest["sha256"]
    };
    if !expected.is_null() && expected != &artifact["sha256"] {
        bail!("artifact SHA256 does not match specification");
    }
    pins.push(artifact.clone());
    let raw_command = spec
        .get("command")
        .cloned()
        .unwrap_or_else(|| json!(["{artifact}"]));
    let command: Vec<String> = raw_command
        .as_array()
        .context("command must be an argv array")?
        .iter()
        .map(|v| {
            v.as_str()
                .context("command items must be strings")
                .map(|s| s.replace("{artifact}", &artifact_path.to_string_lossy()))
        })
        .collect::<Result<_>>()?;
    if command.is_empty() || command.iter().any(|s| s.is_empty() || s.contains('\0')) {
        bail!("command must contain nonempty NUL-free arguments");
    }
    let executable = resolve_declared(&command[0], base)?;
    pins.push(fingerprint(&executable, "command_executable")?);
    pins.push(fingerprint(
        &std::env::current_exe()?,
        "nvcompact_executable",
    )?);
    let mut tools = Vec::new();
    if let Some(declared) = spec.get("tools") {
        for value in declared.as_array().context("tools must be an array")? {
            let name = value.as_str().context("tool names must be strings")?;
            if name.is_empty() || name.contains('\0') {
                bail!("invalid tool name");
            }
            let found = resolve_declared(name, base).ok();
            tools.push(json!({"name": name, "path": found, "base": base}));
            if let Some(path) = found {
                pins.push(fingerprint(&path, &format!("declared_tool:{name}"))?);
            }
        }
    }
    let budget = spec["budget"].clone();
    validate_budget(&budget)?;
    let preconditions = spec
        .get("preconditions")
        .cloned()
        .unwrap_or_else(|| json!({}));
    validate_preconditions(&preconditions)?;
    let mut settings = spec.get("uci").cloned().unwrap_or_else(|| json!({}));
    if !settings.is_object() {
        bail!("uci must be an object");
    }
    if settings.get("artifact_path").is_some() || settings.get("invocation_argv0").is_some() {
        bail!("UCI artifact_path and invocation_argv0 are derived from the plan");
    }
    for (key, value) in [
        ("max_seconds", budget["wall_seconds"].clone()),
        ("memory_bytes", budget["address_space_bytes"].clone()),
        ("cpu_seconds", budget["cpu_seconds_per_process"].clone()),
        ("file_bytes", budget["file_bytes"].clone()),
    ] {
        let matches_budget = if key == "max_seconds" {
            settings[key].as_f64() == value.as_f64()
        } else {
            settings[key].as_u64() == value.as_u64()
        };
        if settings.get(key).is_some() && !matches_budget {
            bail!("uci.{key} differs from the resource budget");
        }
        settings[key] = value;
    }
    if settings.get("max_output_bytes").is_none() {
        settings["max_output_bytes"] = budget["output_bytes_per_session"].clone();
    }
    if settings["max_output_bytes"]
        .as_u64()
        .is_none_or(|n| n > number(&budget, "output_bytes_per_session").unwrap())
    {
        bail!("UCI output cap exceeds budget");
    }
    settings["artifact_path"] = json!(artifact_path);
    settings["invocation_argv0"] = json!(command[0]);
    let config: UciConfig = serde_json::from_value(settings)?;
    config.validate()?;
    let facts = probe_resources();
    let now = SystemTime::now().duration_since(UNIX_EPOCH)?.as_millis() as u64;
    let mut plan = json!({"format": PLAN_FORMAT, "status": "planned", "engine_started": false,
        "created_at_unix_ms": now, "name": spec.get("name").cloned().unwrap_or_else(|| json!(artifact_path.file_name().unwrap().to_string_lossy())),
        "command": command, "executable_path": executable, "artifact_path": artifact_path,
        "artifact": artifact, "inputs": pins, "tools": tools, "budget": budget, "preconditions": preconditions,
        "uci_configuration": config, "specification": spec, "previous_runtime_blocked": manifest["runtime_blocked"],
        "resources_at_plan": facts, "engine_option_policy": if config.preserve_engine_options { "preserve original defaults and embedded constants" } else { "explicit UCI profile; not original configuration equivalence" },
        "scope": {"execution": "no target, allocation probe, compiler or version process executed while planning",
            "limits": "inherited child-only AS/CPU/file limits and verifier wall/output bounds; no aggregate cgroup is created",
            "cleanup": "original owned process group, not escaped sessions", "memory": "transient observation; no RAM reservation"}});
    plan["preflight_at_plan"] = preflight(&plan, &facts);
    plan["plan_sha256"] = json!(digest(&plan)?);
    Ok(plan)
}

pub fn changed_inputs(plan: &Value) -> Vec<Value> {
    let mut changes = Vec::new();
    let Some(inputs) = plan["inputs"].as_array() else {
        return vec![json!({"error": "missing input fingerprints"})];
    };
    for expected in inputs {
        let Some(path) = expected["path"].as_str() else {
            changes.push(json!({"error": "fingerprint missing path"}));
            continue;
        };
        let role = expected["role"].as_str().unwrap_or("unknown");
        match fingerprint(Path::new(path), role) {
            Ok(actual) if actual == *expected => {}
            Ok(actual) => {
                changes.push(json!({"role": role, "expected": expected, "actual": actual}))
            }
            Err(err) => changes.push(json!({"role": role, "path": path, "error": err.to_string()})),
        }
        let executing = match role {
            "artifact" => plan["artifact_path"].as_str().map(PathBuf::from),
            "command_executable" => plan["executable_path"].as_str().map(PathBuf::from),
            "nvcompact_executable" => std::env::current_exe().ok(),
            _ => None,
        };
        if let Some(path) = executing {
            match fingerprint(&path, role) {
                Ok(actual) if actual == *expected => {},
                Ok(actual) => changes.push(json!({"role": format!("executing_{role}"), "expected": expected, "actual": actual})),
                Err(err) => changes.push(json!({"role": format!("executing_{role}"), "error": err.to_string()})),
            }
        }
    }
    if let Some(tools) = plan["tools"].as_array() {
        for tool in tools {
            let Some(name) = tool["name"].as_str() else {
                changes.push(json!({"error": "tool missing name"}));
                continue;
            };
            let base = tool["base"]
                .as_str()
                .map(Path::new)
                .unwrap_or(Path::new("/"));
            let actual = resolve_declared(name, base).ok();
            if json!(actual) != tool["path"] {
                changes.push(json!({"role": "tool_resolution", "name": name, "expected": tool["path"], "actual": actual}));
            }
        }
    }
    changes
}

pub fn execute_plan(plan_path: &Path, output: &Path, start: bool) -> Result<Value> {
    if !start {
        bail!("explicit --start required; creating a plan never starts an engine");
    }
    let plan = read_json(plan_path)?;
    if plan["format"] != PLAN_FORMAT || plan["status"] != "planned" {
        bail!("expected a Rust resource plan; regenerate old Python plans");
    }
    let mut unsigned = plan.clone();
    unsigned.as_object_mut().unwrap().remove("plan_sha256");
    if plan["plan_sha256"] != digest(&unsigned)? {
        bail!("plan checksum changed; regenerate from specification");
    }
    validate_budget(&plan["budget"])?;
    validate_preconditions(plan.get("preconditions").unwrap_or(&json!({})))?;
    let config: UciConfig = serde_json::from_value(plan["uci_configuration"].clone())?;
    config.validate()?;
    if json!(config.artifact_path) != plan["artifact_path"]
        || config.max_seconds != plan["budget"]["wall_seconds"].as_f64().unwrap()
        || config.memory_bytes != number(&plan["budget"], "address_space_bytes")?
        || config.cpu_seconds != number(&plan["budget"], "cpu_seconds_per_process")?
        || config.file_bytes != number(&plan["budget"], "file_bytes")?
        || config.max_output_bytes as u64 > number(&plan["budget"], "output_bytes_per_session")?
    {
        bail!("UCI configuration differs from pinned artifact/budget");
    }
    let output = absolute(output)?;
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::create_dir(&output).context("resource output directory must be new")?;
    let started = Instant::now();
    let facts = probe_resources();
    let changes = changed_inputs(&plan);
    let before_environment: BTreeMap<_, _> = std::env::vars_os().collect();
    let before_limits = rlimits();
    let mut report = json!({"format": RUN_FORMAT, "status": "blocked", "engine_started": false,
        "plan_sha256": plan["plan_sha256"], "plan": plan, "resources_before": facts,
        "preflight": preflight(&plan, &facts), "changed_inputs_before": changes, "uci": null});
    write_new(&output.join("plan.json"), &plan)?;
    if !changes.is_empty() {
        report["preflight"]["status"] = json!("blocked");
        report["preflight"]["reasons"]
            .as_array_mut()
            .unwrap()
            .push(json!(
                "pinned input or tool resolution changed; regenerate plan"
            ));
    }
    if process::cancelled() {
        report["status"] = json!("interrupted");
    } else if report["preflight"]["status"] == "ready" {
        let mut command: Vec<String> = serde_json::from_value(plan["command"].clone())?;
        if command.is_empty() {
            bail!("plan command is empty");
        }
        if config.invocation_argv0.as_deref() != Some(command[0].as_str()) {
            bail!("argv[0] differs from pinned command");
        }
        command[0] = plan["executable_path"]
            .as_str()
            .context("missing executable path")?
            .into();
        report["requested_rlimits"] = requested_limits(&plan["budget"]);
        report["engine_started"] = Value::Null;
        match uci::verify_engine(&command, &config) {
            Ok(result) => {
                report["engine_started"] = result["engine_started"].clone();
                report["status"] = result["verdict"].clone();
                write_new(&output.join("uci.json"), &result)?;
                report["uci"] = result;
            }
            Err(err) => {
                report["status"] = json!("error");
                report["error"] = json!(err.to_string());
            }
        }
        report["changed_inputs_after"] = json!(changed_inputs(&plan));
        if !report["changed_inputs_after"]
            .as_array()
            .unwrap()
            .is_empty()
        {
            report["status"] = json!("fail");
            report["input_preservation_error"] =
                json!("input changed during execution; no automatic restoration");
        }
    }
    report["environment_unchanged"] = json!(before_environment == std::env::vars_os().collect());
    report["parent_rlimits_unchanged"] = json!(before_limits == rlimits());
    report["resources_after"] = probe_resources();
    report["elapsed_seconds"] = json!(started.elapsed().as_secs_f64());
    write_new(&output.join("result.json"), &report)?;
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::symlink;

    fn fixture(dir: &Path, required: u64) -> PathBuf {
        let artifact = dir.join("engine.sh");
        fs::write(&artifact, "while IFS= read -r c; do case \"$c\" in uci) echo uciok;;isready) echo readyok;;quit) exit 0;;'position startpos') move=e2e4;;*'e1g1') move=f8e7;;position*) move=e7e5;;go*) echo bestmove $move;;esac;done\n").unwrap();
        let spec = json!({"format": SPEC_FORMAT, "name": "small-fixture", "artifact": "engine.sh", "command": ["/bin/sh", "{artifact}"], "tools": ["/bin/sh"],
            "budget": {"required_memory_bytes": required, "reserve_memory_bytes": 0, "address_space_bytes": required.max(64<<20),
                "cpu_seconds_per_process": 10, "wall_seconds": 5.0, "file_bytes": 1<<20, "output_bytes_per_session": 65536},
            "uci": {"quick": true, "cleanup_seconds": 0.1}});
        let path = dir.join("spec.json");
        fs::write(&path, serde_json::to_vec_pretty(&spec).unwrap()).unwrap();
        path
    }

    #[test]
    fn planning_never_starts_target_and_missing_start_is_an_error() {
        let dir = tempfile::tempdir().unwrap();
        let spec = fixture(dir.path(), 1);
        let target = dir.path().join("engine.sh");
        fs::write(&target, "touch was-started\n").unwrap();
        let plan = create_plan(&spec).unwrap();
        assert_eq!(plan["engine_started"], false);
        assert!(!dir.path().join("was-started").exists());
        let plan_path = dir.path().join("plan.json");
        write_new(&plan_path, &plan).unwrap();
        assert!(execute_plan(&plan_path, &dir.path().join("run"), false).is_err());
        assert!(!dir.path().join("run").exists());
    }

    #[test]
    fn modified_source_and_symlink_target_are_detected() {
        let dir = tempfile::tempdir().unwrap();
        let spec = fixture(dir.path(), 1);
        let original = dir.path().join("engine.sh");
        let backup = dir.path().join("original.sh");
        fs::rename(&original, &backup).unwrap();
        symlink("original.sh", &original).unwrap();
        let plan = create_plan(&spec).unwrap();
        assert!(changed_inputs(&plan).is_empty());
        let alternative = dir.path().join("alternative.sh");
        fs::copy(&backup, &alternative).unwrap();
        fs::remove_file(&original).unwrap();
        symlink("alternative.sh", &original).unwrap();
        assert!(!changed_inputs(&plan).is_empty());
    }

    #[test]
    fn explicit_small_run_preserves_inputs_parent_limits_and_environment() {
        let dir = tempfile::tempdir().unwrap();
        let spec = fixture(dir.path(), 1);
        let plan = create_plan(&spec).unwrap();
        assert_eq!(plan["preflight_at_plan"]["status"], "ready", "{plan:#}");
        let path = dir.path().join("plan.json");
        write_new(&path, &plan).unwrap();
        let result = execute_plan(&path, &dir.path().join("run"), true).unwrap();
        assert_eq!(result["status"], "pass", "{result:#}");
        assert_eq!(result["engine_started"], true);
        assert_eq!(result["environment_unchanged"], true);
        assert_eq!(result["parent_rlimits_unchanged"], true);
        assert_eq!(result["changed_inputs_after"], json!([]));
    }

    #[test]
    fn nested_cgroup_limits_and_reclaim_estimate_are_observed() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        fs::create_dir(root.join("self")).unwrap();
        fs::write(
            root.join("meminfo"),
            "MemTotal: 1000 kB\nMemAvailable: 900 kB\n",
        )
        .unwrap();
        fs::write(
            root.join("self/stat"),
            format!("{} (fixture) R", std::process::id()),
        )
        .unwrap();
        fs::write(root.join("self/cgroup"), "0::/child\n").unwrap();
        let cg = root.join("cg");
        fs::create_dir_all(cg.join("child")).unwrap();
        fs::write(
            root.join("self/mountinfo"),
            format!("0 0 0:0 / {} rw - cgroup2 cgroup rw\n", cg.display()),
        )
        .unwrap();
        for (path, maximum, used, inactive) in [
            (cg.clone(), 100000, 80000, 10000),
            (cg.join("child"), 200000, 10000, 0),
        ] {
            fs::write(path.join("memory.max"), maximum.to_string()).unwrap();
            fs::write(path.join("memory.current"), used.to_string()).unwrap();
            fs::write(
                path.join("memory.stat"),
                format!("inactive_file {inactive}\nfile {inactive}\n"),
            )
            .unwrap();
        }
        let facts = probe_resources_from(root);
        assert_eq!(facts["errors"], json!([]), "{facts:#}");
        assert_eq!(facts["estimated_available_memory_bytes"], 30000);
        assert_eq!(facts["cgroup_v2"].as_array().unwrap().len(), 2);
    }

    #[test]
    fn insufficient_memory_run_remains_blocked_without_launch() {
        let dir = tempfile::tempdir().unwrap();
        let spec = fixture(dir.path(), 1u64 << 60);
        let plan = create_plan(&spec).unwrap();
        let path = dir.path().join("plan.json");
        write_new(&path, &plan).unwrap();
        let result = execute_plan(&path, &dir.path().join("run"), true).unwrap();
        assert_eq!(result["status"], "blocked");
        assert_eq!(result["engine_started"], false);
        assert_eq!(result["environment_unchanged"], true);
        assert_eq!(result["parent_rlimits_unchanged"], true);
    }

    #[test]
    fn checksum_tampering_is_not_silently_repaired() {
        let dir = tempfile::tempdir().unwrap();
        let spec = fixture(dir.path(), 1);
        let mut plan = create_plan(&spec).unwrap();
        plan["budget"]["required_memory_bytes"] = json!(2);
        let path = dir.path().join("plan.json");
        write_new(&path, &plan).unwrap();
        assert!(execute_plan(&path, &dir.path().join("run"), true)
            .unwrap_err()
            .to_string()
            .contains("checksum"));
    }

    #[test]
    fn integer_budget_comparison_does_not_round_through_floats() {
        let dir = tempfile::tempdir().unwrap();
        let path = fixture(dir.path(), 1);
        let mut spec = read_json(&path).unwrap();
        spec["budget"]["address_space_bytes"] = json!(1u64 << 54);
        spec["uci"]["memory_bytes"] = json!((1u64 << 54) + 1);
        fs::write(&path, serde_json::to_vec(&spec).unwrap()).unwrap();
        assert!(create_plan(&path)
            .unwrap_err()
            .to_string()
            .contains("differs from the resource budget"));
    }

    #[test]
    fn declared_cpu_stack_and_instruction_preconditions_block_without_changing_resources() {
        let mut plan = json!({"tools": [], "budget": {"required_memory_bytes": 1,
            "reserve_memory_bytes": 0, "address_space_bytes": 1,
            "cpu_seconds_per_process": 1, "file_bytes": 1},
            "preconditions": {"max_online_cpu_count": 16, "max_inherited_stack_bytes": 8388608,
                "required_cpu_flags": ["avx512f", "vaes"]}});
        let facts = json!({"platform": "linux", "errors": [], "estimated_available_memory_bytes": 100,
            "online_cpu_count": 8, "common_cpu_flags": ["avx512f", "vaes"],
            "rlimits": {"RLIMIT_AS": [null,null], "RLIMIT_CPU": [null,null],
                "RLIMIT_FSIZE": [null,null], "RLIMIT_CORE": [0,null], "RLIMIT_STACK": [8388608,null]}});
        assert_eq!(preflight(&plan, &facts)["status"], "ready");
        for (key, value) in [
            ("max_online_cpu_count", json!(4)),
            ("max_inherited_stack_bytes", json!(4194304)),
            ("required_cpu_flags", json!(["missing_isa"])),
        ] {
            let before = plan["preconditions"][key].clone();
            plan["preconditions"][key] = value;
            assert_eq!(preflight(&plan, &facts)["status"], "blocked");
            plan["preconditions"][key] = before;
        }
        assert!(validate_preconditions(&json!({"unrecognized_cpu_override": 1})).is_err());
    }
}
