//! Declared implementation/link portfolios. Build-only never runs a checker or
//! codec. Every selected result is rebuilt from a new snapshot before delivery.
use crate::{
    elf, notation, pack,
    process::{self, Limits},
    sha256, write_json,
};
use anyhow::{ensure, Context, Result};
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io::Read;
use std::os::unix::fs::PermissionsExt;
use std::path::{Component as PathComponent, Path, PathBuf};
use std::sync::{
    atomic::{AtomicUsize, Ordering},
    Mutex,
};
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct NativeOptions {
    pub packing: bool,
    pub verify: bool,
    pub jobs: usize,
    pub max_candidates: usize,
    pub profiles: Vec<String>,
    pub link_profiles: Vec<String>,
    pub max_seconds: f64,
    pub limits: Limits,
    pub max_bytes: Option<usize>,
    pub tools: BTreeMap<String, String>,
}
impl Default for NativeOptions {
    fn default() -> Self {
        Self {
            packing: true,
            verify: true,
            jobs: 2,
            max_candidates: 128,
            profiles: vec![],
            link_profiles: vec![],
            max_seconds: 600.0,
            limits: Limits::default(),
            max_bytes: None,
            tools: BTreeMap::new(),
        }
    }
}
#[derive(Clone, Debug, Serialize, Deserialize)]
struct Selection {
    build: String,
    link: String,
    order: Vec<String>,
    variants: BTreeMap<String, String>,
}

fn read_json(path: &Path) -> Result<Value> {
    ensure!(
        path.metadata()?.len() <= 4 << 20,
        "manifest exceeds four MiB"
    );
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}
fn id(value: &str) -> Result<()> {
    ensure!(
        Regex::new(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
            .unwrap()
            .is_match(value),
        "invalid identifier: {value}"
    );
    Ok(())
}
fn named(value: &Value, label: &str) -> Result<BTreeMap<String, Value>> {
    let entries = value
        .as_array()
        .with_context(|| format!("{label} must be an array"))?;
    ensure!(!entries.is_empty(), "{label} must not be empty");
    let mut result = BTreeMap::new();
    for item in entries {
        let name = item["id"].as_str().context("missing id")?;
        id(name)?;
        ensure!(
            result.insert(name.into(), item.clone()).is_none(),
            "duplicate {label} id: {name}"
        );
    }
    Ok(result)
}
fn strings(value: &Value) -> Result<Vec<String>> {
    value
        .as_array()
        .context("expected string array")?
        .iter()
        .map(|v| v.as_str().map(str::to_owned).context("expected string"))
        .collect()
}
pub fn expand(argv: &Value, context: &BTreeMap<String, Value>) -> Result<Vec<String>> {
    let pattern = Regex::new(r"\{([A-Za-z0-9][A-Za-z0-9_.-]*)\}").unwrap();
    let tokens = argv.as_array().context("command must be argv array")?;
    let mut output = Vec::new();
    for token in tokens {
        if let Some(obj) = token.as_object() {
            ensure!(
                obj.len() == 1 && obj.contains_key("literal"),
                "invalid literal argv object"
            );
            output.push(
                obj["literal"]
                    .as_str()
                    .context("literal must be a string")?
                    .into(),
            );
            continue;
        }
        let text = token
            .as_str()
            .context("argv must contain strings or literal objects")?;
        if let Some(caps) = pattern.captures(text) {
            if caps.get(0).unwrap().as_str() == text {
                if let Some(v) = context.get(&caps[1]) {
                    if v.is_array() {
                        output.extend(strings(v)?);
                        continue;
                    }
                }
            }
        }
        let mut updated = String::new();
        let mut last = 0;
        for caps in pattern.captures_iter(text) {
            let span = caps.get(0).unwrap();
            updated.push_str(&text[last..span.start()]);
            let value = context.get(&caps[1]).with_context(|| {
                format!("unknown placeholder {}; use a literal object", &caps[0])
            })?;
            ensure!(
                !value.is_array() && !value.is_object(),
                "list placeholders must occupy a complete token"
            );
            updated.push_str(
                value
                    .as_str()
                    .map(str::to_owned)
                    .unwrap_or_else(|| value.to_string())
                    .as_str(),
            );
            last = span.end();
        }
        updated.push_str(&text[last..]);
        output.push(updated);
    }
    ensure!(!output.is_empty() && !output[0].is_empty(), "empty command");
    ensure!(
        output.iter().all(|s| !s.contains('\0')),
        "NUL in command argument"
    );
    Ok(output)
}
fn safe_input(root: &Path, name: &str) -> Result<PathBuf> {
    let path = Path::new(name);
    ensure!(
        !path.is_absolute()
            && !name.is_empty()
            && path
                .components()
                .all(|p| matches!(p, PathComponent::Normal(_))),
        "input must be a plain project-relative path: {name}"
    );
    let actual = root
        .join(path)
        .canonicalize()
        .with_context(|| format!("missing declared input {name}"))?;
    ensure!(
        actual.starts_with(root) && actual.is_file(),
        "input escapes project: {name}"
    );
    Ok(actual)
}
fn bounded_read(path: &Path, max: usize) -> Result<Vec<u8>> {
    let file = fs::File::open(path)?;
    let meta = file.metadata()?;
    ensure!(
        meta.is_file() && meta.len() <= max as u64,
        "input/output exceeds its byte budget: {}",
        path.display()
    );
    let limit = (max as u64)
        .checked_add(1)
        .context("file byte budget overflow")?;
    let mut bytes = Vec::new();
    file.take(limit).read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() <= max,
        "file grew beyond its byte budget: {}",
        path.display()
    );
    Ok(bytes)
}
fn copy_inputs(
    root: &Path,
    destination: &Path,
    inputs: &[String],
) -> Result<BTreeMap<String, String>> {
    fs::create_dir_all(destination)?;
    let mut hashes = BTreeMap::new();
    for name in inputs {
        let source = safe_input(root, name)?;
        let bytes = bounded_read(&source, 64 << 20)?;
        let target = destination.join(name);
        fs::create_dir_all(target.parent().unwrap())?;
        fs::write(&target, &bytes)?;
        fs::set_permissions(&target, source.metadata()?.permissions())?;
        ensure!(
            hashes.insert(name.clone(), sha256(&bytes)).is_none(),
            "duplicate input: {name}"
        );
    }
    Ok(hashes)
}
fn check_inputs(root: &Path, expected: &BTreeMap<String, String>) -> Result<()> {
    for (name, hash) in expected {
        ensure!(
            &sha256(&bounded_read(&safe_input(root, name)?, 64 << 20)?) == hash,
            "declared input changed: {name}"
        );
    }
    Ok(())
}
fn checked_file(path: &Path, max: usize) -> Result<Vec<u8>> {
    let meta = fs::symlink_metadata(path).context("missing build output")?;
    ensure!(
        meta.file_type().is_file() && meta.len() > 0 && meta.len() <= max as u64,
        "output is not a bounded nonempty regular file"
    );
    bounded_read(path, max)
}
fn notation_options(spec: &Value) -> Result<Option<notation::NotationOptions>> {
    let Some(value) = spec.get("notation") else {
        return Ok(None);
    };
    let object = value.as_object().context("notation must be an object")?;
    ensure!(object.keys().all(|k|["language","target","token_contract","compact","max_variants"].contains(&k.as_str()))
        &&object.get("language").and_then(Value::as_str).is_some_and(|s|!s.is_empty()),
        "notation needs explicit language and only target/token_contract/compact/max_variants options");
    let sources = strings(&spec["sources"])?;
    ensure!(
        !sources.is_empty() && sources.iter().collect::<BTreeSet<_>>().len() == sources.len(),
        "notation requires unique, nonempty same-language sources"
    );
    let options: notation::NotationOptions =
        serde_json::from_value(value.clone()).context("invalid typed notation options")?;
    notation::generate_variants(b"", &options).context("invalid notation contract")?;
    Ok(Some(options))
}
fn submission_category(manifest: &Value) -> Result<Option<&str>> {
    match manifest.get("category") {
        None | Some(Value::Null) => Ok(None),
        Some(value) => {
            let category = value
                .as_str()
                .context("submission category must be a string")?;
            ensure!(
                matches!(category, "4k" | "4k-elf"),
                "supported submission categories are 4k and 4k-elf"
            );
            Ok(Some(category))
        }
    }
}
fn validate_submission_policy(manifest: &Value, options: &NativeOptions) -> Result<()> {
    let category = submission_category(manifest)?;
    if options.packing && category == Some("4k-elf") && !manifest["codecs"].is_null() {
        ensure!(strings(&manifest["codecs"])?.iter().all(|id|id=="raw"),"4k-elf permits only native ELF deployment; remove wrapper codec requests or declare only raw");
    }
    Ok(())
}
fn final_size_cap(manifest: &Value, options: &NativeOptions) -> Option<usize> {
    // Build-only reports raw linked bytes; packed-file budgets do not silently
    // constrain that separate path. The explicit caller cap always applies.
    if !options.packing {
        return options.max_bytes;
    }
    let tournament = matches!(manifest["category"].as_str(), Some("4k" | "4k-elf")).then_some(4096);
    [
        manifest["max_bytes"].as_u64().map(|n| n as usize),
        options.max_bytes,
        tournament,
    ]
    .into_iter()
    .flatten()
    .min()
}
fn command_tools(
    commands: &[&Value],
    all: &serde_json::Map<String, Value>,
    required: &mut BTreeSet<String>,
) -> Result<()> {
    let placeholders = Regex::new(r"\{([A-Za-z0-9][A-Za-z0-9_.-]*)\}").unwrap();
    for command in commands {
        if let Some(args) = command.as_array() {
            for token in args {
                if let Some(text) = token.as_str() {
                    for cap in placeholders.captures_iter(text) {
                        if all.contains_key(&cap[1]) {
                            required.insert(cap[1].into());
                        }
                    }
                }
            }
            if let Some(first) = args.first().and_then(Value::as_str) {
                for (name, spec) in all {
                    if spec["executable"].as_str() == Some(first) {
                        required.insert(name.clone());
                    }
                }
            }
        }
    }
    loop {
        let before = required.len();
        for name in required.clone() {
            let spec = all.get(&name).context("required tool not declared")?;
            if !spec["requires_tools"].is_null() {
                required.extend(strings(&spec["requires_tools"])?);
            }
        }
        if before == required.len() {
            break;
        }
    }
    Ok(())
}
fn runtime() -> Result<Value> {
    Ok(json!({"version":env!("CARGO_PKG_VERSION"),"backend":"rust",
    "binary_sha256":sha256(&fs::read(std::env::current_exe()?)?)}))
}

struct Campaign<'a> {
    manifest: &'a Value,
    source: PathBuf,
    out: PathBuf,
    options: NativeOptions,
    tools: BTreeMap<String, String>,
    tool_info: Value,
    environment: BTreeMap<String, String>,
    hashes: BTreeMap<String, String>,
    builds: BTreeMap<String, Value>,
    links: BTreeMap<String, Value>,
    components: BTreeMap<String, Value>,
    started: Instant,
    audit_notation: bool,
}
impl<'a> Campaign<'a> {
    fn selections(manifest: &Value, options: &NativeOptions) -> Result<(usize, Vec<Selection>)> {
        let builds = named(&manifest["build_profiles"], "build_profiles")?;
        let links = named(&manifest["link_profiles"], "link_profiles")?;
        let components = named(&manifest["components"], "components")?;
        validate_submission_policy(manifest, options)?;
        let choose = |all: &BTreeMap<String, Value>, requested: &[String]| -> Result<Vec<String>> {
            if requested.is_empty() {
                Ok(all.keys().cloned().collect())
            } else {
                ensure!(
                    requested.iter().all(|x| all.contains_key(x)),
                    "unknown requested profile"
                );
                ensure!(
                    requested.iter().collect::<BTreeSet<_>>().len() == requested.len(),
                    "duplicate profile filter"
                );
                Ok(requested.to_vec())
            }
        };
        let build_ids = choose(&builds, &options.profiles)?;
        let link_ids = choose(&links, &options.link_profiles)?;
        let declared: Vec<String> = manifest["components"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v["id"].as_str().unwrap().to_owned())
            .collect();
        let orders = if manifest["orders"].is_null() {
            vec![declared.clone()]
        } else {
            named(&manifest["orders"], "orders")?;
            manifest["orders"]
                .as_array()
                .unwrap()
                .iter()
                .map(|v| strings(&v["components"]))
                .collect::<Result<Vec<_>>>()?
        };
        for order in &orders {
            ensure!(
                order.len() == components.len()
                    && order.iter().collect::<BTreeSet<_>>() == components.keys().collect(),
                "order must contain every component once"
            );
        }
        let mut products = vec![BTreeMap::new()];
        let mut variant_count = 1usize;
        for name in &declared {
            let component = &components[name];
            ensure!(
                component["contract"]
                    .as_str()
                    .is_some_and(|s| !s.is_empty()),
                "component needs semantic/ABI contract"
            );
            let variants = named(&component["variants"], "variants")?;
            variant_count = variant_count
                .checked_mul(variants.len())
                .context("candidate count overflow")?;
            let mut next = Vec::new();
            for product in &products {
                for key in variants.keys() {
                    if next.len() >= options.max_candidates {
                        break;
                    }
                    let mut p = product.clone();
                    p.insert(name.clone(), key.clone());
                    next.push(p);
                }
            }
            products = next;
        }
        let total = build_ids
            .len()
            .checked_mul(link_ids.len())
            .and_then(|n| n.checked_mul(orders.len()))
            .and_then(|n| n.checked_mul(variant_count))
            .context("candidate count overflow")?;
        let mut result = Vec::new();
        'outer: for build in build_ids {
            for link in &link_ids {
                for order in &orders {
                    for variants in &products {
                        if result.len() >= options.max_candidates {
                            break 'outer;
                        }
                        result.push(Selection {
                            build: build.clone(),
                            link: link.clone(),
                            order: order.clone(),
                            variants: variants.clone(),
                        });
                    }
                }
            }
        }
        Ok((total, result))
    }
    fn new(
        manifest: &'a Value,
        source: PathBuf,
        out: PathBuf,
        options: NativeOptions,
        selections: &[Selection],
        expected: Option<&Value>,
    ) -> Result<Self> {
        options.limits.validate()?;
        ensure!(
            options.jobs > 0
                && options.jobs <= 32
                && options.max_candidates > 0
                && options.max_candidates <= 4096,
            "jobs must be 1..32; candidates 1..4096"
        );
        ensure!(
            options.max_seconds.is_finite()
                && options.max_seconds > 0.0
                && options.max_seconds <= 86400.0,
            "invalid campaign wall limit"
        );
        ensure!(
            manifest["target"].as_str().is_some_and(|s| !s.is_empty()),
            "explicit target required"
        );
        let builds = named(&manifest["build_profiles"], "build_profiles")?;
        let links = named(&manifest["link_profiles"], "link_profiles")?;
        let components = named(&manifest["components"], "components")?;
        validate_submission_policy(manifest, &options)?;
        for key in ["max_bytes", "max_native_bytes"] {
            if !manifest[key].is_null() {
                ensure!(
                    manifest[key]
                        .as_u64()
                        .is_some_and(|v| v > 0 && usize::try_from(v).is_ok()),
                    "{key} must be a positive platform-sized JSON integer"
                );
            }
        }
        ensure!(
            options.max_bytes.is_none_or(|n| n > 0),
            "native --max-bytes must be positive"
        );
        for link in links.values() {
            for key in ["allow_section_header_removal", "allow_load_zero_tail"] {
                if let Some(value) = link.get(key) {
                    ensure!(value.is_boolean(), "{key} must be a JSON boolean");
                }
            }
            ensure!(
                link["allow_load_zero_tail"] != true
                    || link["allow_section_header_removal"] == true,
                "allow_load_zero_tail also requires allow_section_header_removal"
            );
            if let Some(common) = link.get("common") {
                ensure!(common.is_array(), "common units must be an array");
            }
            if options.packing {
                if let Some(common) = link["common"].as_array() {
                    for spec in common {
                        notation_options(spec)?;
                    }
                }
            }
        }
        if options.packing {
            for component in components.values() {
                for spec in component["variants"]
                    .as_array()
                    .context("variants must be an array")?
                {
                    notation_options(spec)?;
                }
            }
        }
        let all = manifest["tools"]
            .as_object()
            .context("tools object required")?;
        ensure!(
            options.tools.keys().all(|k| all.contains_key(k)),
            "unknown tool override"
        );
        let mut required = BTreeSet::new();
        let mut commands = Vec::new();
        let mut specs = Vec::new();
        for selection in selections {
            let build = builds.get(&selection.build).context("unknown build")?;
            let link = links.get(&selection.link).context("unknown link")?;
            specs.extend([build, link]);
            commands.push(&link["argv"]);
            if let Some(post) = link["post_link"].as_array() {
                commands.extend(post);
            }
            if let Some(common) = link["common"].as_array() {
                specs.extend(common);
            }
            ensure!(
                selection.order.len() == components.len()
                    && selection.order.iter().collect::<BTreeSet<_>>()
                        == components.keys().collect(),
                "invalid selection order"
            );
            ensure!(
                selection.variants.len() == components.len(),
                "invalid selection variants"
            );
            for name in &selection.order {
                let variants = components[name]["variants"].as_array().unwrap();
                let wanted = selection
                    .variants
                    .get(name)
                    .context("missing component selection")?;
                specs.push(
                    variants
                        .iter()
                        .find(|v| v["id"].as_str() == Some(wanted))
                        .context("unknown variant")?,
                );
            }
        }
        for spec in specs {
            if let Some(c) = spec["commands"].as_array() {
                commands.extend(c);
            }
            if !spec["requires_tools"].is_null() {
                required.extend(strings(&spec["requires_tools"])?);
            }
        }
        let mut build_required = required.clone();
        command_tools(&commands, all, &mut build_required)?;
        if options.verify || options.packing {
            ensure!(
                manifest["verify"].is_array(),
                "verification needs explicit verify argv"
            );
            commands.push(&manifest["verify"]);
            if manifest["verify_final"].is_array() {
                commands.push(&manifest["verify_final"]);
            }
            if !manifest["verify_requires_tools"].is_null() {
                required.extend(strings(&manifest["verify_requires_tools"])?);
            }
        }
        command_tools(&commands, all, &mut required)?;
        let mut tools = BTreeMap::new();
        let mut info = serde_json::Map::new();
        for name in required {
            id(&name)?;
            let spec = &all[&name];
            let executable = options
                .tools
                .get(&name)
                .map(String::as_str)
                .or_else(|| spec["executable"].as_str())
                .context("tool executable required")?;
            let invocation = process::resolve_tool(executable)?;
            let canonical = invocation.canonicalize()?;
            let digest = sha256(&fs::read(&canonical)?);
            if let Some(old) = expected.and_then(|x| x.get(&name)) {
                ensure!(
                    old["sha256"].as_str() == Some(&digest),
                    "recorded tool changed: {name}"
                );
            } else if expected.is_some() && build_required.contains(&name) {
                anyhow::bail!("selected build tool has no recorded fingerprint: {name}");
            }
            tools.insert(name.clone(), invocation.to_string_lossy().into_owned());
            info.insert(name,json!({"executable":invocation,"resolved":canonical,"sha256":digest,"version_probe":"not_run"}));
        }
        // Replay validates the selected tool dependency closure. Other portfolio
        // candidates may have required additional compilers; their fingerprints
        // do not make those compilers dependencies of this selected recipe.
        // New verifier-only tools remain allowed for an explicit --verify run.
        let mut directories: Vec<String> = tools
            .values()
            .filter_map(|s| {
                Path::new(s)
                    .parent()
                    .map(|p| p.to_string_lossy().into_owned())
            })
            .collect();
        directories.extend(["/usr/bin".into(), "/bin".into()]);
        directories.dedup();
        let mut environment = BTreeMap::from([
            ("PATH".into(), directories.join(":")),
            ("LANG".into(), "C".into()),
            ("LC_ALL".into(), "C".into()),
            ("TZ".into(), "UTC".into()),
            ("SOURCE_DATE_EPOCH".into(), "0".into()),
            ("PYTHONHASHSEED".into(), "0".into()),
            ("PYTHONCOERCECLOCALE".into(), "0".into()),
        ]);
        if let Some(env) = manifest["environment"].as_object() {
            for (k, v) in env {
                environment.insert(
                    k.clone(),
                    v.as_str()
                        .context("environment value must be string")?
                        .into(),
                );
            }
        }
        let mut hashes = BTreeMap::new();
        for input in strings(&manifest["inputs"])? {
            hashes.insert(
                input.clone(),
                sha256(&bounded_read(&safe_input(&source, &input)?, 64 << 20)?),
            );
        }
        let audit_notation = expected.is_none() && options.packing;
        Ok(Self {
            manifest,
            source,
            out,
            options,
            tools,
            tool_info: Value::Object(info),
            environment,
            hashes,
            builds,
            links,
            components,
            started: Instant::now(),
            audit_notation,
        })
    }
    fn context(&self, build: &str, work: &Path) -> BTreeMap<String, Value> {
        let mut ctx: BTreeMap<_, _> = self
            .tools
            .iter()
            .map(|(k, v)| (k.clone(), json!(v)))
            .collect();
        if let Some(vars) = self.builds[build]["variables"].as_object() {
            ctx.extend(vars.iter().map(|(k, v)| (k.clone(), v.clone())));
        }
        ctx.insert("root".into(), json!(self.source));
        ctx.insert("build".into(), json!(work));
        ctx
    }
    fn command(&self, argv: Vec<String>, work: &Path, label: &str) -> Result<Value> {
        let remaining = self.options.max_seconds - self.started.elapsed().as_secs_f64();
        ensure!(
            remaining > 0.0 && !process::cancelled(),
            "campaign wall budget/cancellation reached"
        );
        let mut limits = self.options.limits.clone();
        limits.seconds = limits.seconds.min(remaining);
        let out = process::run_with_env(&argv, b"", work, &limits, Some(&self.environment))?;
        fs::write(work.join(format!("{label}.stdout")), &out.stdout)?;
        fs::write(work.join(format!("{label}.stderr")), &out.stderr)?;
        let record = json!({"argv":argv,"returncode":out.code,"seconds":out.wall_seconds,"stdout":format!("{label}.stdout"),"stderr":format!("{label}.stderr"),"timed_out":out.timed_out,"output_limited":out.output_limited});
        write_json(&work.join(format!("{label}.json")), &record)?;
        out.check(label)?;
        Ok(record)
    }
    fn unit(&self, selection: &Selection, spec: &Value, work: &Path, key: &str) -> Result<PathBuf> {
        fs::create_dir_all(work)?;
        let object = work.join("unit.o");
        let sources = if spec["sources"].is_null() {
            vec![]
        } else {
            strings(&spec["sources"])?
        };
        let paths = sources
            .iter()
            .map(|s| safe_input(&self.source, s).map(|p| p.to_string_lossy().into_owned()))
            .collect::<Result<Vec<_>>>()?;
        let mut ctx = self.context(&selection.build, work);
        ctx.insert("sources".into(), json!(paths));
        ctx.insert(
            "source".into(),
            json!(paths.first().map(String::as_str).unwrap_or("")),
        );
        ctx.insert("object".into(), json!(object));
        ctx.insert("unit_id".into(), json!(key));
        let commands = spec["commands"]
            .as_array()
            .context("unit commands missing")?;
        ensure!(!commands.is_empty(), "empty unit commands");
        for (index, command) in commands.iter().enumerate() {
            self.command(expand(command, &ctx)?, work, &format!("compile-{index}"))?;
        }
        checked_file(&object, self.max_file())?;
        if self.options.packing {
            if let Some(mut audit) = self.notation(selection, spec, work, key, &object)? {
                // Keep full per-edit evidence beside the unit, while the aggregate
                // campaign report carries bounded recipe metadata instead of copies
                // of every source edit and compiler transcript.
                if let Some(rows) = audit["candidates"].as_array_mut() {
                    for row in rows {
                        if let Some(object) = row.as_object_mut() {
                            for key in ["commands", "rewrites", "notes"] {
                                object.remove(key);
                            }
                        }
                    }
                }
                if work.join("notation/audit.json").exists() {
                    audit["audit_file"] = json!("notation/audit.json");
                }
                write_json(&work.join("notation.json"), &audit)?;
            }
        }
        Ok(object)
    }
    fn max_file(&self) -> usize {
        self.manifest["max_native_bytes"]
            .as_u64()
            .unwrap_or(64 << 20)
            .min(self.options.limits.file_bytes) as usize
    }
    /// The unmodified object remains the linker input. A source recipe can be
    /// locked before link combinations only after full object-byte equality;
    /// source length alone never authorizes an object replacement.
    fn notation(
        &self,
        selection: &Selection,
        spec: &Value,
        work: &Path,
        key: &str,
        original_object: &Path,
    ) -> Result<Option<Value>> {
        let Some(options) = notation_options(spec)? else {
            return Ok(None);
        };
        if !self.audit_notation {
            return Ok(Some(
                json!({"status":"not_repeated_for_native_reproduction","linked_object":"original","reason":"notation candidates never replace the original linker input"}),
            ));
        }
        check_inputs(&self.source, &self.hashes)?;
        let sources = strings(&spec["sources"])?;
        ensure!(
            sources.iter().all(|p| self.hashes.contains_key(p)),
            "notation source must be an explicitly declared snapshot input"
        );
        let original = checked_file(original_object, self.max_file())?;
        let mut originals = BTreeMap::new();
        let mut source_hashes = BTreeMap::new();
        for name in &sources {
            let data = bounded_read(&safe_input(&self.source, name)?, notation::MAX_SOURCE)?;
            source_hashes.insert(name.clone(), sha256(&data));
            originals.insert(name.clone(), data);
        }
        let source_bytes: usize = originals.values().map(Vec::len).sum();
        let raw = json!({"id":"raw","status":"baseline","eligible":true,"source_bytes":source_bytes,"source_sha256":source_hashes,"object_sha256":sha256(&original),"object_bytes":original.len()});
        let mut audit = json!({"status":"completed","search_complete":true,"unit_id":key,"linked_object":"original","contract":options,"selection_basis":"minimum source bytes among complete byte-identical objects; source only","original_source_bytes":source_bytes,"original_object_sha256":sha256(&original),"source_bytes_saved":0,"selected":raw,"candidates":[raw]});
        let destination = work.join("notation");
        fs::create_dir(&destination)?;
        let generated = (|| -> Result<BTreeMap<String, Vec<notation::Variant>>> {
            originals
                .iter()
                .map(|(path, data)| {
                    Ok((path.clone(), notation::generate_variants(data, &options)?))
                })
                .collect()
        })();
        let variants = match generated {
            Ok(v) => v,
            Err(e) => {
                audit["status"] = json!("generation_failed");
                audit["search_complete"] = json!(false);
                audit["error"] = json!(format!("{e:#}"));
                write_json(&destination.join("audit.json"), &audit)?;
                return Ok(Some(audit));
            }
        };
        let ids: Vec<_> = variants
            .values()
            .next()
            .unwrap()
            .iter()
            .map(|v| v.id.clone())
            .collect();
        if variants
            .values()
            .any(|v| v.iter().map(|v| &v.id).collect::<Vec<_>>() != ids.iter().collect::<Vec<_>>())
        {
            audit["status"] = json!("generation_inapplicable");
            audit["search_complete"] = json!(false);
            audit["reason"]=json!("same-language sources yielded different supported recipe sets; original object retained");
            write_json(&destination.join("audit.json"), &audit)?;
            return Ok(Some(audit));
        }
        audit["planned_source_recipes"] = json!(ids.len());
        for (index, identifier) in ids.iter().enumerate().skip(1) {
            let candidate_sources: BTreeMap<_, _> = variants
                .iter()
                .map(|(p, v)| (p.clone(), &v[index]))
                .collect();
            let total: usize = candidate_sources.values().map(|v| v.data.len()).sum();
            let mut row = json!({"id":identifier,"eligible":false,"source_bytes":total,
                "source_sha256":candidate_sources.iter().map(|(p,v)|(p.clone(),v.sha256.clone())).collect::<BTreeMap<_,_>>(),
                "rewrites":candidate_sources.iter().map(|(p,v)|(p.clone(),v.audit.clone())).collect::<BTreeMap<_,_>>(),
                "notes":candidate_sources.iter().map(|(p,v)|(p.clone(),v.notes.clone())).collect::<BTreeMap<_,_>>()});
            if candidate_sources
                .iter()
                .all(|(p, v)| v.data == originals[p])
            {
                row["status"] = json!("source_identical");
                row["reason"] =
                    json!("same source bytes as raw; no alternative compilation needed");
            } else if self.started.elapsed().as_secs_f64() >= self.options.max_seconds
                || process::cancelled()
            {
                row["status"] = json!("incomplete");
                row["reason"] =
                    json!("campaign budget or cancellation before notation compilation");
                audit["status"] = json!("incomplete");
                audit["search_complete"] = json!(false);
                audit["candidates"].as_array_mut().unwrap().push(row);
                break;
            } else {
                let folder = destination.join(identifier);
                let overlay = folder.join("root");
                let build = folder.join("build");
                fs::create_dir_all(&build)?;
                let mut overlay_hashes = copy_inputs(
                    &self.source,
                    &overlay,
                    &self.hashes.keys().cloned().collect::<Vec<_>>(),
                )?;
                for (name, variant) in &candidate_sources {
                    let path = overlay.join(name);
                    let mode = path.metadata()?.permissions();
                    fs::set_permissions(&path, fs::Permissions::from_mode(mode.mode() | 0o200))?;
                    fs::write(&path, &variant.data)?;
                    fs::set_permissions(&path, mode)?;
                    overlay_hashes.insert(name.clone(), variant.sha256.clone());
                }
                let object = build.join("unit.o");
                let paths = sources
                    .iter()
                    .map(|p| safe_input(&overlay, p).map(|p| p.to_string_lossy().into_owned()))
                    .collect::<Result<Vec<_>>>()?;
                let mut context = self.context(&selection.build, &build);
                context.insert("root".into(), json!(overlay));
                context.insert("sources".into(), json!(paths));
                context.insert("source".into(), json!(paths[0]));
                context.insert("object".into(), json!(object));
                context.insert("unit_id".into(), json!(key));
                row["overlay"] = json!(overlay.strip_prefix(&self.out)?);
                row["commands"] = json!([]);
                let compiled = (|| -> Result<Vec<u8>> {
                    for (index, command) in spec["commands"]
                        .as_array()
                        .context("notation commands missing")?
                        .iter()
                        .enumerate()
                    {
                        let command = self.command(
                            expand(command, &context)?,
                            &build,
                            &format!("compile-{index}"),
                        )?;
                        row["commands"].as_array_mut().unwrap().push(command);
                    }
                    check_inputs(&overlay, &overlay_hashes)?;
                    checked_file(&object, self.max_file())
                })();
                match compiled {
                    Ok(data) => {
                        row["object_bytes"] = json!(data.len());
                        row["object_sha256"] = json!(sha256(&data));
                        if data == original {
                            row["status"] = json!("object_byte_identical");
                            row["eligible"] = json!(true);
                        } else {
                            row["status"] = json!("rejected_object_difference");
                            row["reason"]=json!("complete object bytes differ; source size is not an equivalence gate");
                        }
                    }
                    Err(e) => {
                        row["status"] = json!("failed");
                        row["error"] = json!(format!("{e:#}"));
                        if self.started.elapsed().as_secs_f64() >= self.options.max_seconds
                            || process::cancelled()
                        {
                            row["status"] = json!("incomplete");
                            audit["status"] = json!("incomplete");
                            audit["search_complete"] = json!(false);
                        }
                    }
                }
                check_inputs(&self.source, &self.hashes)?;
                ensure!(
                    checked_file(original_object, self.max_file())? == original,
                    "notation build modified the original linked object"
                );
            }
            audit["candidates"].as_array_mut().unwrap().push(row);
        }
        let mut eligible: Vec<_> = audit["candidates"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|r| r["eligible"] == true)
            .cloned()
            .collect();
        eligible.sort_by(|a, b| {
            (
                a["source_bytes"].as_u64(),
                a["id"] != "raw",
                a["id"].as_str(),
            )
                .cmp(&(
                    b["source_bytes"].as_u64(),
                    b["id"] != "raw",
                    b["id"].as_str(),
                ))
        });
        let mut selected = eligible.remove(0);
        if let Some(object) = selected.as_object_mut() {
            for key in ["commands", "rewrites", "notes"] {
                object.remove(key);
            }
        }
        audit["source_bytes_saved"] =
            json!(source_bytes as u64 - selected["source_bytes"].as_u64().unwrap());
        audit["selected"] = selected;
        write_json(&destination.join("audit.json"), &audit)?;
        Ok(Some(audit))
    }
    fn native(&self, selection: &Selection, work: &Path) -> Result<Vec<u8>> {
        fs::create_dir_all(work)?;
        let link = &self.links[&selection.link];
        let mut objects = Vec::new();
        if let Some(common) = link["common"].as_array() {
            if !common.is_empty() {
                named(&link["common"], "common")?;
            }
            for spec in common {
                let name = spec["id"].as_str().context("common id missing")?;
                id(name)?;
                objects.push(self.unit(
                    selection,
                    spec,
                    &work.join("common").join(name),
                    &format!("common/{}/{name}", selection.link),
                )?);
            }
        }
        for name in &selection.order {
            let variant = &selection.variants[name];
            let specs = named(&self.components[name]["variants"], "variants")?;
            objects.push(self.unit(
                selection,
                &specs[variant],
                &work.join("variant").join(name).join(variant),
                &format!("variant/{name}/{variant}"),
            )?);
        }
        let notation_reports: Vec<_> = objects
            .iter()
            .filter_map(|p| p.parent().map(|p| p.join("notation.json")))
            .filter(|p| p.exists())
            .map(|p| read_json(&p))
            .collect::<Result<Vec<_>>>()?;
        write_json(&work.join("notation.json"), &notation_reports)?;
        let binary = work.join("native");
        let mut ctx = self.context(&selection.build, work);
        ctx.insert("objects".into(), json!(objects));
        ctx.insert("binary".into(), json!(binary));
        self.command(expand(&link["argv"], &ctx)?, work, "link")?;
        if let Some(post) = link["post_link"].as_array() {
            for (index, command) in post.iter().enumerate() {
                self.command(expand(command, &ctx)?, work, &format!("post-{index}"))?;
            }
        }
        let bytes = checked_file(&binary, self.max_file())?;
        fs::set_permissions(binary, fs::Permissions::from_mode(0o755))?;
        check_inputs(&self.source, &self.hashes)?;
        Ok(bytes)
    }
    fn verify(
        &self,
        selection: &Selection,
        binary: &Path,
        work: &Path,
        final_check: bool,
    ) -> Result<Value> {
        if !(self.options.verify || self.options.packing) {
            return Ok(json!({"status":"not_run"}));
        }
        let mut ctx = self.context(&selection.build, work);
        ctx.insert("binary".into(), json!(binary));
        let command = if final_check && !self.manifest["verify_final"].is_null() {
            &self.manifest["verify_final"]
        } else {
            &self.manifest["verify"]
        };
        let before = fs::read(binary)?;
        let record = self.command(
            expand(command, &ctx)?,
            work,
            if final_check {
                "verify-final"
            } else {
                "verify"
            },
        )?;
        ensure!(
            fs::read(binary)? == before,
            "checker changed candidate artifact"
        );
        Ok(json!({"status":"pass","command":record}))
    }
    fn evaluate(&self, index: usize, selection: &Selection) -> Value {
        let result = (|| -> Result<Value> {
            let work = self.out.join("candidates").join(format!("c{index:05}"));
            let native = self.native(selection, &work)?;
            let verification = self.verify(selection, &work.join("native"), &work, false)?;
            let mut artifacts = Vec::new();
            let cap = final_size_cap(self.manifest, &self.options);
            if !self.options.packing {
                artifacts.push(json!({"id":"linked","deployment":"linked","pack":"none","bytes":native.len(),"sha256":sha256(&native),"artifact":work.join("native").strip_prefix(&self.out)?,"verification":verification,"status":if cap.is_some_and(|n|native.len()>n){"over_size_limit"}else if self.options.verify{"screened"}else{"built"}}));
            } else {
                let allow = self.links[&selection.link]["allow_section_header_removal"]
                    .as_bool()
                    .unwrap_or(false);
                let codecs = if self.manifest["category"] == "4k-elf" {
                    Some(vec!["raw".into()])
                } else if self.manifest["codecs"].is_null() {
                    None
                } else {
                    Some(strings(&self.manifest["codecs"])?)
                };
                let zero_tail = self.links[&selection.link]["allow_load_zero_tail"]
                    .as_bool()
                    .unwrap_or(false);
                for deployment in elf::deployment_variants_with_options(&native, allow, zero_tail)?
                {
                    for packed in pack::pack_variants(
                        &deployment.data,
                        self.manifest["target"].as_str().unwrap(),
                        codecs.as_deref(),
                    )? {
                        let name = format!("{}__{}", deployment.id, packed.id);
                        let folder = work.join(&name);
                        fs::create_dir(&folder)?;
                        let path = folder.join("artifact");
                        fs::write(&path, &packed.data)?;
                        fs::set_permissions(&path, fs::Permissions::from_mode(0o755))?;
                        let verified = self.verify(selection, &path, &folder, false);
                        let (status, check) = match verified {
                            Ok(v) => (
                                if cap.is_some_and(|n| packed.data.len() > n) {
                                    "over_size_limit"
                                } else {
                                    "screened"
                                },
                                v,
                            ),
                            Err(e) => (
                                "failed",
                                json!({"status":"failed","error":format!("{e:#}")}),
                            ),
                        };
                        artifacts.push(json!({"id":name,"deployment":deployment.id,"pack":packed.id,"bytes":packed.data.len(),"sha256":sha256(&packed.data),"artifact":path.strip_prefix(&self.out)?,"status":status,"verification":check,"payload_bytes":packed.payload_bytes,"loader_bytes":packed.loader_bytes}));
                    }
                }
            }
            Ok(
                json!({"id":format!("c{index:05}"),"status":"completed","recipe":selection,"native_bytes":native.len(),"native_sha256":sha256(&native),"notation":read_json(&work.join("notation.json"))?,"artifacts":artifacts}),
            )
        })();
        match result {
            Ok(row) => row,
            Err(error) => {
                json!({"id":format!("c{index:05}"),"status":"failed","recipe":selection,"error":format!("{error:#}"),"artifacts":[]})
            }
        }
    }
}

fn new_output(path: &Path) -> Result<PathBuf> {
    ensure!(
        !path.exists() && !path.is_symlink(),
        "output must be a new directory"
    );
    fs::create_dir_all(path)?;
    Ok(path.canonicalize()?)
}
fn rebuild(
    recipe: &Value,
    source: &Path,
    out: &Path,
    options: &NativeOptions,
) -> Result<(Vec<u8>, Value)> {
    let current = runtime()?;
    ensure!(
        recipe["runtime"] == current,
        "Rust runner fingerprint changed; original recipe runtime required"
    );
    let expected: BTreeMap<String, String> = serde_json::from_value(recipe["inputs"].clone())?;
    check_inputs(source, &expected)?;
    let selection: Selection = serde_json::from_value(recipe["selection"].clone())?;
    let packing = recipe["packing"] == "portfolio";
    let mut effective = options.clone();
    effective.packing = packing;
    effective.verify = packing || options.verify;
    // Keep invocation paths including symlinks; every required build tool is pinned.
    if let Some(tools) = recipe["tools"].as_object() {
        for (name, info) in tools {
            effective.tools.entry(name.clone()).or_insert(
                info["executable"]
                    .as_str()
                    .context("recorded executable missing")?
                    .into(),
            );
        }
    }
    let campaign = Campaign::new(
        &recipe["project"],
        source.into(),
        out.into(),
        effective,
        &[selection.clone()],
        Some(&recipe["tools"]),
    )?;
    if packing && recipe["project"]["category"] == "4k-elf" {
        ensure!(
            recipe["pack"] == "raw",
            "4k-elf reproduction cannot use a script wrapper"
        );
    }
    let work = out.join("selected");
    let native = campaign.native(&selection, &work)?;
    ensure!(
        sha256(&native) == recipe["native_sha256"],
        "fresh native bytes differ"
    );
    let data = if !packing {
        ensure!(
            recipe["pack"] == "none" && recipe["deployment"] == "linked",
            "invalid plain native recipe"
        );
        native
    } else {
        let allow = campaign.links[&selection.link]["allow_section_header_removal"]
            .as_bool()
            .unwrap_or(false);
        let zero_tail = campaign.links[&selection.link]["allow_load_zero_tail"]
            .as_bool()
            .unwrap_or(false);
        let deployment = elf::deployment_variants_with_options(&native, allow, zero_tail)?
            .into_iter()
            .find(|d| Some(d.id.as_str()) == recipe["deployment"].as_str())
            .context("selected ELF deployment unavailable")?;
        pack::pack_by_id(
            &deployment.data,
            recipe["project"]["target"]
                .as_str()
                .context("target missing")?,
            recipe["pack"].as_str().context("pack id missing")?,
        )?
        .data
    };
    ensure!(
        sha256(&data) == recipe["artifact_sha256"]
            && data.len() as u64
                == recipe["artifact_bytes"]
                    .as_u64()
                    .context("artifact size missing")?,
        "fresh final bytes differ"
    );
    if let Some(cap) = final_size_cap(&recipe["project"], &campaign.options) {
        ensure!(
            data.len() <= cap,
            "reproduced final artifact exceeds effective byte limit"
        );
    }
    if packing && recipe["project"]["category"] == "4k-elf" {
        elf::validate_executable(
            &data,
            recipe["project"]["target"]
                .as_str()
                .context("target missing")?,
        )?;
    }
    let file = work.join("artifact");
    fs::write(&file, &data)?;
    fs::set_permissions(&file, fs::Permissions::from_mode(0o755))?;
    let check = campaign.verify(&selection, &file, &work, true)?;
    check_inputs(source, &expected)?;
    Ok((data, check))
}
pub fn run(manifest_path: &Path, output: &Path, options: &NativeOptions) -> Result<Value> {
    let path = manifest_path.canonicalize()?;
    let mut manifest = read_json(&path)?;
    let root = path
        .parent()
        .unwrap()
        .join(manifest["project_root"].as_str().unwrap_or("."))
        .canonicalize()?;
    let inputs = strings(&manifest["inputs"])?;
    ensure!(
        !inputs.is_empty(),
        "declare inputs including headers/linker/verifier scripts"
    );
    let out = new_output(output)?;
    let result = (|| -> Result<Value> {
        let source = out.join("snapshot");
        let hashes = copy_inputs(&root, &source, &inputs)?;
        manifest["project_root"] = json!(".");
        write_json(&out.join("project.json"), &manifest)?;
        let (total, selections) = Campaign::selections(&manifest, options)?;
        let mut active = selections.clone();
        let verification = options.packing || options.verify;
        let baseline = if verification {
            let s: Selection = serde_json::from_value(manifest["baseline"].clone())
                .context("verified run needs explicit baseline selection")?;
            active.push(s.clone());
            Some(s)
        } else {
            None
        };
        let campaign = Campaign::new(
            &manifest,
            source.clone(),
            out.clone(),
            options.clone(),
            &active,
            None,
        )?;
        let base_check = if let Some(selection) = baseline {
            let work = out.join("baseline");
            let data = campaign.native(&selection, &work)?;
            json!({"bytes":data.len(),"sha256":sha256(&data),"verification":campaign.verify(&selection,&work.join("native"),&work,true)?})
        } else {
            json!({"status":"not_run"})
        };
        let cursor = AtomicUsize::new(0);
        let results = Mutex::new(Vec::new());
        std::thread::scope(|scope| {
            for _ in 0..options.jobs.min(selections.len()) {
                scope.spawn(|| loop {
                    let i = cursor.fetch_add(1, Ordering::Relaxed);
                    if i >= selections.len() {
                        break;
                    }
                    let row = campaign.evaluate(i, &selections[i]);
                    results.lock().unwrap().push(row);
                });
            }
        });
        let mut rows = results.into_inner().unwrap();
        rows.sort_by(|a, b| a["id"].as_str().cmp(&b["id"].as_str()));
        let wanted = if verification { "screened" } else { "built" };
        let mut eligible = Vec::new();
        for (row_index, row) in rows.iter().enumerate() {
            for artifact in row["artifacts"].as_array().unwrap() {
                if artifact["status"] == wanted {
                    eligible.push((
                        artifact["bytes"].as_u64().unwrap(),
                        row_index,
                        artifact.clone(),
                    ));
                }
            }
        }
        eligible.sort_by(|a, b| {
            a.0.cmp(&b.0)
                .then(a.1.cmp(&b.1))
                .then(a.2["id"].as_str().cmp(&b.2["id"].as_str()))
        });
        let mut report = json!({"format":"nvcompact.native.v2","runtime":runtime()?,"backend":"rust","packing":if options.packing{"portfolio"}else{"none"},"submission_category":manifest["category"],"effective_max_bytes":final_size_cap(&manifest,options),"packing_policy":if options.packing&&manifest["category"]=="4k-elf"{"native ELF only; raw codec; complete file <=4096 bytes"}else{"declared general deployment portfolio"},"verification_requested":verification,"baseline":base_check,"planned_link_candidates":total,"selected_link_candidates":selections.len(),"candidates":rows,"tools":campaign.tool_info,"environment":campaign.environment,"input_sha256":hashes,"search_complete":total==selections.len()&&rows.iter().all(|r|r["status"]=="completed"&&r["notation"].as_array().is_none_or(|units|units.iter().all(|u|u["search_complete"]!=false))),"status":"failed"});
        write_json(&out.join("report.json"), &report)?;
        let (_, row_index, artifact) = eligible.first().context(
            "no completed eligible file meets size and verification requirements; see report.json",
        )?;
        let row = &rows[*row_index];
        let notation:Vec<_>=row["notation"].as_array().into_iter().flatten().map(|u|json!({"unit_id":u["unit_id"],"linked_object":"original","selected":u["selected"],"search_complete":u["search_complete"]})).collect();
        let selected: Selection = serde_json::from_value(row["recipe"].clone())?;
        let selected_tools = Campaign::new(
            &manifest,
            source.clone(),
            out.clone(),
            options.clone(),
            &[selected],
            Some(&campaign.tool_info),
        )?
        .tool_info;
        let recipe = json!({"format":"nvcompact.native-recipe.v2","runtime":runtime()?,"packing":if options.packing{"portfolio"}else{"none"},"verification":if verification{"passed"}else{"not_run"},"project":manifest,"snapshot":"snapshot","inputs":hashes,"tools":selected_tools,"selection":row["recipe"],"notation":notation,"deployment":artifact["deployment"],"pack":artifact["pack"],"native_sha256":row["native_sha256"],"artifact_sha256":artifact["sha256"],"artifact_bytes":artifact["bytes"]});
        let reproduction = out.join("reproduction");
        fs::create_dir(&reproduction)?;
        let fresh = reproduction.join("snapshot");
        copy_inputs(&source, &fresh, &inputs)?;
        let mut replay_options = options.clone();
        replay_options.verify = verification;
        let (data, check) = rebuild(&recipe, &fresh, &reproduction, &replay_options)?;
        ensure!(
            fs::read(out.join(artifact["artifact"].as_str().unwrap()))? == data,
            "selected result changed before delivery"
        );
        check_inputs(&source, &hashes)?;
        check_inputs(&root, &hashes)?;
        fs::write(out.join("winner"), &data)?;
        fs::set_permissions(out.join("winner"), fs::Permissions::from_mode(0o755))?;
        write_json(&out.join("winner.recipe.json"), &recipe)?;
        report["status"] = json!(if verification { "accepted" } else { "built" });
        report["winner"] = artifact.clone();
        report["final_verification"] = check;
        report["reproduction"] = json!("byte_identical_fresh_build");
        write_json(&out.join("report.json"), &report)?;
        Ok(report)
    })();
    if let Err(error) = &result {
        let p = out.join("report.json");
        let mut report = read_json(&p).unwrap_or_else(|_| json!({"format":"nvcompact.native.v2"}));
        report["status"] = json!("failed");
        report["error"] = json!(format!("{error:#}"));
        write_json(&p, &report)?;
    }
    result
}
pub fn reproduce(recipe_path: &Path, output: &Path, options: &NativeOptions) -> Result<Value> {
    let path = recipe_path.canonicalize()?;
    let recipe = read_json(&path)?;
    ensure!(
        recipe["format"] == "nvcompact.native-recipe.v2",
        "historical Python recipes require the preserved Python reference runtime"
    );
    let parent = path.parent().unwrap();
    let source = parent
        .join(
            recipe["snapshot"]
                .as_str()
                .context("snapshot path missing")?,
        )
        .canonicalize()?;
    ensure!(
        source.starts_with(parent),
        "recipe snapshot outside recipe directory"
    );
    let expected: BTreeMap<String, String> = serde_json::from_value(recipe["inputs"].clone())?;
    check_inputs(&source, &expected)?;
    let out = new_output(output)?;
    let copied = out.join("snapshot");
    copy_inputs(
        &source,
        &copied,
        &expected.keys().cloned().collect::<Vec<_>>(),
    )?;
    let result = rebuild(&recipe, &copied, &out, options);
    match result {
        Ok((data, check)) => {
            fs::write(out.join("winner"), &data)?;
            fs::set_permissions(out.join("winner"), fs::Permissions::from_mode(0o755))?;
            let report = json!({"status":"byte_identical","bytes":data.len(),"sha256":sha256(&data),"verification":check,"packing":recipe["packing"]});
            write_json(&out.join("reproduction.json"), &report)?;
            Ok(report)
        }
        Err(e) => {
            write_json(
                &out.join("reproduction.json"),
                &json!({"status":"failed","error":format!("{e:#}")}),
            )?;
            Err(e)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn expansion_preserves_literals_and_splices_only_lists() {
        let ctx = BTreeMap::from([
            ("cc".into(), json!("compiler with spaces")),
            ("flags".into(), json!(["-Os", "literal $x"])),
            ("root".into(), json!("/a b")),
        ]);
        assert_eq!(
            expand(
                &json!(["{cc}","{flags}","-I{root}",{"literal":"{unknown}"}]),
                &ctx
            )
            .unwrap(),
            vec![
                "compiler with spaces",
                "-Os",
                "literal $x",
                "-I/a b",
                "{unknown}"
            ]
        );
        assert!(expand(&json!(["{cc}", "prefix{flags}"]), &ctx).is_err());
        assert!(expand(&json!(["{unknown}"]), &ctx).is_err());
    }
    fn fixture(root: &Path, source: &[u8], mapped: bool) -> (Value, Selection) {
        fs::write(root.join("f.c"), source).unwrap();
        let mut argv = vec![
            json!("{cc}"),
            json!("-std=c11"),
            json!("-O0"),
            json!("-fno-ident"),
        ];
        if mapped {
            argv.push(json!("-ffile-prefix-map={root}=."));
        }
        argv.extend([
            json!("-c"),
            json!("{source}"),
            json!("-o"),
            json!("{object}"),
        ]);
        let manifest = json!({"target":"x86_64-unknown-linux-gnu","inputs":["f.c"],"tools":{"cc":{"executable":"cc"}},
            "components":[{"id":"program","contract":"project-owned integer fixture","variants":[{"id":"one","sources":["f.c"],"commands":[argv],
            "notation":{"language":"c","compact":true,"token_contract":"no-token-observation","max_variants":3}}]}],
            "build_profiles":[{"id":"size"}],"link_profiles":[{"id":"hosted","argv":["{cc}","{objects}","-o","{binary}"]}],"verify":["{binary}"]});
        let selection = Selection {
            build: "size".into(),
            link: "hosted".into(),
            order: vec!["program".into()],
            variants: BTreeMap::from([("program".into(), "one".into())]),
        };
        (manifest, selection)
    }
    #[test]
    fn prelink_notation_accepts_only_complete_identical_objects() {
        let root = tempfile::tempdir().unwrap();
        let out = tempfile::tempdir().unwrap();
        let (manifest, selection) = fixture(
            root.path(),
            b"int value(void) { /* only source trivia */ return 100000; }\n",
            true,
        );
        let campaign = Campaign::new(
            &manifest,
            root.path().to_owned(),
            out.path().to_owned(),
            NativeOptions::default(),
            &[selection.clone()],
            None,
        )
        .unwrap();
        let work = out.path().join("unit");
        let original = campaign
            .unit(
                &selection,
                &manifest["components"][0]["variants"][0],
                &work,
                "program/one",
            )
            .unwrap();
        let audit = read_json(&work.join("notation/audit.json")).unwrap();
        assert_eq!(audit["linked_object"], "original");
        assert!(audit["source_bytes_saved"].as_u64().unwrap() > 0);
        assert_eq!(audit["selected"]["status"], "object_byte_identical");
        assert_eq!(
            audit["selected"]["object_sha256"],
            sha256(&fs::read(&original).unwrap())
        );
        assert!(audit["candidates"]
            .as_array()
            .unwrap()
            .iter()
            .any(|r| r["id"] == "raw" && r["eligible"] == true));
        assert_eq!(
            fs::read(root.path().join("f.c")).unwrap(),
            b"int value(void) { /* only source trivia */ return 100000; }\n"
        );
    }
    #[test]
    fn prelink_detects_path_observation_and_plain_build_skips_declared_notation() {
        let root = tempfile::tempdir().unwrap();
        let out = tempfile::tempdir().unwrap();
        let(manifest,selection)=fixture(root.path(),b"const char path[]=__FILE__;int value(void) { /* retained observer */ return 100000; }\n",false);
        let campaign = Campaign::new(
            &manifest,
            root.path().to_owned(),
            out.path().to_owned(),
            NativeOptions::default(),
            &[selection.clone()],
            None,
        )
        .unwrap();
        let work = out.path().join("unit");
        campaign
            .unit(
                &selection,
                &manifest["components"][0]["variants"][0],
                &work,
                "program/one",
            )
            .unwrap();
        let audit = read_json(&work.join("notation/audit.json")).unwrap();
        assert_eq!(audit["selected"]["id"], "raw");
        assert_eq!(audit["source_bytes_saved"], 0);
        assert!(audit["candidates"]
            .as_array()
            .unwrap()
            .iter()
            .any(|r| r["status"] == "rejected_object_difference"));
        let options = NativeOptions {
            packing: false,
            verify: false,
            ..Default::default()
        };
        let plain = Campaign::new(
            &manifest,
            root.path().to_owned(),
            out.path().to_owned(),
            options,
            &[selection.clone()],
            None,
        )
        .unwrap();
        let work = out.path().join("plain");
        plain
            .unit(
                &selection,
                &manifest["components"][0]["variants"][0],
                &work,
                "program/one",
            )
            .unwrap();
        assert!(!work.join("notation").exists());
        assert!(!work.join("notation.json").exists());
    }
    #[test]
    fn category_and_caller_budgets_are_explicit_and_elf_stays_native() {
        let root = tempfile::tempdir().unwrap();
        let out = tempfile::tempdir().unwrap();
        let (mut manifest, selection) = fixture(root.path(), b"int main(void){return 0;}\n", true);
        manifest["components"][0]["variants"][0]
            .as_object_mut()
            .unwrap()
            .remove("notation");
        manifest["category"] = json!("4k-elf");
        let options = NativeOptions {
            max_bytes: Some(100),
            ..Default::default()
        };
        assert_eq!(final_size_cap(&manifest, &options), Some(100));
        assert_eq!(
            final_size_cap(&manifest, &NativeOptions::default()),
            Some(4096)
        );
        let campaign = Campaign::new(
            &manifest,
            root.path().to_owned(),
            out.path().to_owned(),
            options,
            &[selection.clone()],
            None,
        )
        .unwrap();
        let result = campaign.evaluate(0, &selection);
        assert_eq!(result["status"], "completed", "{result}");
        let artifacts = result["artifacts"].as_array().unwrap();
        assert_eq!(artifacts.len(), 1);
        assert_eq!(artifacts[0]["pack"], "raw");
        assert_eq!(artifacts[0]["status"], "over_size_limit");
        assert!(
            fs::read(out.path().join(artifacts[0]["artifact"].as_str().unwrap()))
                .unwrap()
                .starts_with(b"\x7fELF")
        );
        manifest["codecs"] = json!(["gzip-9"]);
        assert!(validate_submission_policy(&manifest, &NativeOptions::default()).is_err());
        manifest["category"] = json!("4k");
        manifest["max_bytes"] = json!(80);
        assert_eq!(
            final_size_cap(
                &manifest,
                &NativeOptions {
                    max_bytes: Some(100),
                    ..Default::default()
                }
            ),
            Some(80)
        );
        assert_eq!(
            final_size_cap(
                &manifest,
                &NativeOptions {
                    packing: false,
                    max_bytes: None,
                    ..Default::default()
                }
            ),
            None
        );
        manifest["link_profiles"][0]["allow_section_header_removal"] = json!("true");
        assert!(Campaign::new(
            &manifest,
            root.path().to_owned(),
            out.path().to_owned(),
            NativeOptions::default(),
            &[selection],
            None
        )
        .is_err());
    }
    #[test]
    fn input_byte_budget_is_checked_before_read_and_notation_schema_is_strict() {
        let root = tempfile::tempdir().unwrap();
        let out = tempfile::tempdir().unwrap();
        let huge = fs::File::create(root.path().join("large.bin")).unwrap();
        huge.set_len((64 << 20) + 1).unwrap();
        assert!(copy_inputs(root.path(), out.path(), &["large.bin".into()]).is_err());
        assert!(!out.path().join("large.bin").exists());
        let invalid = json!({"sources":["f.c"],"notation":{"language":"c","compact":"yes"}});
        assert!(notation_options(&invalid).is_err());
        let unknown = json!({"sources":["f.c"],"notation":{"language":"c","skip_type_check":true}});
        assert!(notation_options(&unknown).is_err());
    }
    #[test]
    fn replay_requires_selected_build_tools_without_requiring_unused_portfolio_compilers() {
        let root = tempfile::tempdir().unwrap();
        let out = tempfile::tempdir().unwrap();
        let (mut manifest, selection) = fixture(root.path(), b"int main(void){return 0;}\n", true);
        manifest["tools"]["other"] = json!({"executable":"/no/unused/compiler"});
        manifest["components"][0]["variants"].as_array_mut().unwrap().push(json!({"id":"other-language","sources":["f.c"],"commands":[["{other}","{source}","-o","{object}"]]}));
        let first = Campaign::new(
            &manifest,
            root.path().to_owned(),
            out.path().to_owned(),
            NativeOptions::default(),
            &[selection.clone()],
            None,
        )
        .unwrap();
        let mut recorded = first.tool_info.clone();
        recorded["other"] =
            json!({"sha256":"unused portfolio compiler","executable":"/no/unused/compiler"});
        let replay = Campaign::new(
            &manifest,
            root.path().to_owned(),
            out.path().to_owned(),
            NativeOptions::default(),
            &[selection.clone()],
            Some(&recorded),
        )
        .unwrap();
        assert!(replay.tool_info.get("other").is_none());
        assert!(replay.tool_info.get("cc").is_some());
        recorded["cc"]["sha256"] = json!("changed");
        assert!(Campaign::new(
            &manifest,
            root.path().to_owned(),
            out.path().to_owned(),
            NativeOptions::default(),
            &[selection.clone()],
            Some(&recorded)
        )
        .is_err());
        recorded.as_object_mut().unwrap().remove("cc");
        assert!(Campaign::new(
            &manifest,
            root.path().to_owned(),
            out.path().to_owned(),
            NativeOptions::default(),
            &[selection],
            Some(&recorded)
        )
        .is_err());
    }
}
