//! Binding-aware C spelling candidates for a measured whole-file objective.
//!
//! Generation is deliberately separate from selection. Equal-length and longer
//! spellings can compress better, so this module never chooses by source length.
//! A caller must validate an improving candidate with `verify_variant` and its
//! real compiler recipe before admitting it to a submission portfolio.
use crate::cflow::{validate_args, CFlowOptions};
use crate::notation::{lex, literal_candidates, Token, Variant, MAX_SOURCE};
use crate::{process, sha256};
use anyhow::{ensure, Context, Result};
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::path::PathBuf;

const MAX_PORTFOLIO_BYTES: usize = 64 << 20;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct CSourceOptions {
    pub frontend: CFlowOptions,
    pub target: String,
    pub max_candidates: usize,
    pub max_name_groups: usize,
    pub names_per_group: usize,
    pub rename_locals: bool,
    pub integer_literals: bool,
    pub character_literals: bool,
}

impl Default for CSourceOptions {
    fn default() -> Self {
        Self {
            frontend: CFlowOptions::default(),
            target: "c11-lp64".into(),
            max_candidates: 256,
            max_name_groups: 36,
            names_per_group: 4,
            rename_locals: true,
            integer_literals: true,
            character_literals: true,
        }
    }
}

pub(crate) fn validate_options(options: &CSourceOptions) -> Result<()> {
    ensure!(
        options.target == "c11-lp64",
        "C source spelling supports the declared c11-lp64 type model"
    );
    ensure!(
        (1..=512).contains(&options.max_candidates),
        "max_candidates must be 1..512"
    );
    ensure!(
        options.max_name_groups <= 128 && (1..=16).contains(&options.names_per_group),
        "max_name_groups must be 0..128 and names_per_group 1..16"
    );
    let front = &options.frontend;
    ensure!(
        matches!(front.standard.as_str(), "c11" | "c17" | "gnu11" | "gnu17"),
        "supported C standards: c11, c17, gnu11, gnu17"
    );
    ensure!(
        matches!(
            front.token_contract.as_str(),
            "opaque" | "no-token-observation" | "preprocessed"
        ),
        "unknown source/token contract"
    );
    ensure!(
        front.frontend_seconds.is_finite()
            && front.frontend_seconds > 0.0
            && front.frontend_seconds <= 300.0
            && front.frontend_memory_bytes >= 64 << 20
            && (65536..=128 << 20).contains(&front.ast_bytes),
        "frontend budget outside supported bounds"
    );
    validate_args(&front.compiler_args)
}

fn unchanged_reason(source: &[u8], options: &CSourceOptions) -> Option<&'static str> {
    if options.frontend.token_contract == "opaque" {
        Some("source/token/location non-observation has not been declared")
    } else if !source.is_ascii()
        || source.contains(&0)
        || source.contains(&b'$')
        || source
            .windows(2)
            .any(|s| matches!(s, b"\\\n" | b"??" | b"\\u" | b"\\U"))
        || source.windows(3).any(|s| s == b"\\\r\n")
    {
        Some("non-ASCII/extended identifiers, NUL, line splicing or trigraph-like input is outside the byte-range contract")
    } else {
        None
    }
}

struct Frontend {
    options: CFlowOptions,
    root: tempfile::TempDir,
    executable: PathBuf,
    executable_sha256: String,
    cwd: PathBuf,
    info: Value,
}

struct Parsed {
    tree: Value,
    macros: HashSet<String>,
    main_path: String,
}

impl Frontend {
    fn new(options: &CFlowOptions) -> Result<Self> {
        let executable = process::resolve_tool(&options.clang)?;
        let cwd = options
            .source_path
            .as_ref()
            .map(|p| -> Result<PathBuf> {
                Ok(p.canonicalize()?
                    .parent()
                    .context("source has no parent")?
                    .to_owned())
            })
            .transpose()?
            .unwrap_or(std::env::current_dir()?);
        let executable_sha256 = sha256(&std::fs::read(&executable)?);
        let mut result = Self {
            options: options.clone(),
            root: tempfile::tempdir()?,
            executable,
            executable_sha256,
            cwd,
            info: Value::Null,
        };
        let version = result.execute(
            vec![
                result.executable.to_string_lossy().into_owned(),
                "--version".into(),
            ],
            b"",
            65536,
        )?;
        let version = String::from_utf8_lossy(&version).trim().to_string();
        ensure!(
            version.to_ascii_lowercase().contains("clang version"),
            "frontend must identify itself as Clang"
        );
        // Test the actual frontend ABI rather than trusting a user-supplied
        // target label or redefinable __SIZEOF_* preprocessing names.
        let mut probe = result.prefix();
        probe.extend(["-fsyntax-only".into(), "-".into()]);
        result.execute(probe, b"_Static_assert(sizeof(int)==4 && sizeof(long)==8 && sizeof(long long)==8 && sizeof(void*)==8 && ~0U==4294967295U,\"NVCompact c11-lp64 model mismatch\");\n", 65536)?;
        result.info = json!({"executable":result.executable,"executable_sha256":result.executable_sha256,"version":version,
            "standard":options.standard,"compiler_args":options.compiler_args,"source_include_directory":result.cwd,
            "seconds_per_parse":options.frontend_seconds,"address_space_bytes":options.frontend_memory_bytes,"ast_output_bytes":options.ast_bytes});
        Ok(result)
    }

    fn prefix(&self) -> Vec<String> {
        let mut result = vec![
            self.executable.to_string_lossy().into_owned(),
            "-x".into(),
            "c".into(),
            format!("-std={}", self.options.standard),
        ];
        result.extend(self.options.compiler_args.clone());
        result.extend(["-iquote".into(), self.cwd.to_string_lossy().into_owned()]);
        result
    }

    fn execute(&self, command: Vec<String>, input: &[u8], maximum: usize) -> Result<Vec<u8>> {
        let limits = process::Limits {
            seconds: self.options.frontend_seconds,
            memory_bytes: self.options.frontend_memory_bytes,
            output_bytes: maximum,
            cpu_seconds: self.options.frontend_seconds.ceil() as u64 + 1,
            file_bytes: maximum as u64,
        };
        let output = process::run(&command, input, &self.cwd, &limits)?;
        output.check("Clang source spelling frontend")?;
        ensure!(
            sha256(&std::fs::read(&self.executable)?) == self.executable_sha256,
            "frontend changed during source analysis"
        );
        Ok(output.stdout)
    }

    fn parse(&self, source: &[u8], definitions: bool) -> Result<Parsed> {
        let path = self.root.path().join("translation.c");
        std::fs::write(&path, source)?;
        let mut command = self.prefix();
        command.extend([
            "-fsyntax-only".into(),
            "-Xclang".into(),
            "-ast-dump=json".into(),
            path.to_string_lossy().into_owned(),
        ]);
        let tree: Value =
            serde_json::from_slice(&self.execute(command, b"", self.options.ast_bytes)?)
                .context("Clang AST JSON is invalid or exceeds supported nesting")?;
        ensure!(
            tree["kind"] == "TranslationUnitDecl",
            "unsupported Clang AST shape"
        );
        let mut macros = HashSet::new();
        if definitions {
            let mut command = self.prefix();
            command.extend([
                "-E".into(),
                "-dD".into(),
                path.to_string_lossy().into_owned(),
            ]);
            let bytes = self.execute(command, b"", self.options.ast_bytes)?;
            let text = String::from_utf8(bytes)?;
            // Include definitions later undefined: such macros may have been
            // active at one of the source positions under consideration.
            let pattern = Regex::new(r"(?m)^\s*#\s*define\s+([A-Za-z_][A-Za-z_0-9]*)")?;
            macros.extend(pattern.captures_iter(&text).map(|c| c[1].to_owned()));
        }
        Ok(Parsed {
            tree,
            macros,
            main_path: path.to_string_lossy().into_owned(),
        })
    }
}

fn children(node: &Value) -> impl Iterator<Item = &Value> {
    node.get("inner")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
}

fn walk<'a>(node: &'a Value, result: &mut Vec<&'a Value>) {
    result.push(node);
    for child in children(node) {
        walk(child, result);
    }
}

fn direct_location(value: &Value, main: &str, length: usize) -> Option<(usize, usize)> {
    if ["spellingLoc", "expansionLoc", "includedFrom"]
        .iter()
        .any(|k| value.get(k).is_some())
        || value
            .get("file")
            .and_then(Value::as_str)
            .is_some_and(|s| s != main)
    {
        return None;
    }
    let start = usize::try_from(value["offset"].as_u64()?).ok()?;
    let size = usize::try_from(value["tokLen"].as_u64()?).ok()?;
    let end = start.checked_add(size)?;
    (start < end && end <= length).then_some((start, end))
}

fn direct_span(node: &Value, main: &str, length: usize) -> Option<(usize, usize)> {
    let begin = direct_location(&node["range"]["begin"], main, length)?;
    let end = direct_location(&node["range"]["end"], main, length)?;
    (begin.0 <= end.0).then_some((begin.0, end.1))
}

fn significant(source: &str) -> Result<Vec<Token>> {
    Ok(lex(source, "c")?
        .into_iter()
        .filter(|t| !matches!(t.kind, "space" | "comment"))
        .collect())
}

fn occupied_pair(left: &str, right: &str) -> Result<bool> {
    let result = significant(&format!("{left}{right}"))?;
    Ok(result.len() != 2 || result[0].text != left || result[1].text != right)
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct Edit {
    start: usize,
    end: usize,
    before: String,
    after: String,
    replacement: String,
}

fn make_edits(
    source: &str,
    tokens: &[Token],
    sites: &BTreeSet<(usize, usize)>,
    replacement: &str,
) -> Result<Vec<Edit>> {
    let replacement_tokens = significant(replacement)?;
    ensure!(
        replacement_tokens.len() == 1 && replacement_tokens[0].text == replacement,
        "a spelling replacement must be one preprocessing token"
    );
    let mut edits = Vec::new();
    for &(start, end) in sites {
        let index = tokens
            .binary_search_by_key(&start, |t| t.start)
            .map_err(|_| anyhow::anyhow!("edit does not start at an observed token"))?;
        let token = &tokens[index];
        ensure!(
            token.end == end && !matches!(token.kind, "directive" | "doc"),
            "edit must identify one ordinary complete token"
        );
        let mut after = replacement.to_owned();
        if let Some(left) = index.checked_sub(1).and_then(|i| tokens.get(i)) {
            if left.end == start && occupied_pair(&left.text, replacement)? {
                after.insert(0, ' ');
            }
        }
        if let Some(right) = tokens.get(index + 1) {
            if end == right.start && occupied_pair(replacement, &right.text)? {
                after.push(' ');
            }
        }
        edits.push(Edit {
            start,
            end,
            before: source[start..end].into(),
            after,
            replacement: replacement.into(),
        });
    }
    Ok(edits)
}

fn apply_edits(source: &str, edits: &[Edit]) -> Result<Vec<u8>> {
    let tokens = significant(source)?;
    let mut sorted = edits.to_vec();
    sorted.sort_by_key(|e| (e.start, e.end));
    let mut end = 0;
    let mut expected = tokens.iter().map(|t| t.text.clone()).collect::<Vec<_>>();
    for edit in &sorted {
        ensure!(
            edit.start >= end
                && edit.start < edit.end
                && source.get(edit.start..edit.end) == Some(edit.before.as_str()),
            "overlapping or stale source spelling edit"
        );
        let index = tokens
            .binary_search_by_key(&edit.start, |t| t.start)
            .map_err(|_| anyhow::anyhow!("edit does not start at a token"))?;
        ensure!(
            tokens[index].end == edit.end,
            "edit is not a complete token"
        );
        let replacement = significant(&edit.after)?;
        ensure!(
            replacement.len() == 1 && replacement[0].text == edit.replacement,
            "edit replacement contains unexpected tokens"
        );
        expected[index] = edit.replacement.clone();
        end = edit.end;
    }
    let mut output = source.to_owned();
    for edit in sorted.iter().rev() {
        output.replace_range(edit.start..edit.end, &edit.after);
    }
    ensure!(
        significant(&output)?
            .iter()
            .map(|t| t.text.as_str())
            .eq(expected.iter().map(String::as_str)),
        "spelling edit changed an unintended preprocessing-token boundary"
    );
    Ok(output.into_bytes())
}

fn type_of(node: &Value) -> &str {
    node["type"]["desugaredQualType"]
        .as_str()
        .or_else(|| node["type"]["qualType"].as_str())
        .unwrap_or("")
}

fn top_level_source_nodes<'a>(parsed: &'a Parsed, source: &str) -> Vec<&'a Value> {
    children(&parsed.tree)
        .filter(|node| {
            let Some(name) = node["name"].as_str() else {
                return false;
            };
            let Some((a, b)) = direct_location(&node["loc"], &parsed.main_path, source.len())
            else {
                return false;
            };
            source.get(a..b) == Some(name)
                && direct_span(node, &parsed.main_path, source.len()).is_some()
        })
        .collect()
}

struct Group {
    rule: &'static str,
    old: String,
    sites: BTreeSet<(usize, usize)>,
    choices: Vec<String>,
    proof: Value,
}

fn literal_groups(parsed: &Parsed, source: &str, options: &CSourceOptions) -> Result<Vec<Group>> {
    let mut groups: BTreeMap<(String, String, String), Group> = BTreeMap::new();
    let character =
        Regex::new(r#"^'(?:[^'\\\r\n]|\\(?:[abfnrtv?'"\\]|[0-7]{1,3}|x[0-9a-fA-F]+))'$"#)?;
    for root in top_level_source_nodes(parsed, source) {
        let mut nodes = Vec::new();
        walk(root, &mut nodes);
        for node in nodes {
            let kind = node["kind"].as_str().unwrap_or("");
            let enabled = kind == "IntegerLiteral" && options.integer_literals
                || kind == "CharacterLiteral" && options.character_literals;
            if !enabled {
                continue;
            }
            let Some(begin) =
                direct_location(&node["range"]["begin"], &parsed.main_path, source.len())
            else {
                continue;
            };
            let Some(end) = direct_location(&node["range"]["end"], &parsed.main_path, source.len())
            else {
                continue;
            };
            if begin != end {
                continue;
            }
            let old = &source[begin.0..begin.1];
            let typ = type_of(node);
            let (rule, value, choices) = if kind == "IntegerLiteral" {
                let Some(value) = node["value"].as_str() else {
                    continue;
                };
                let choices = literal_candidates(old, "c", Some(&options.target))?
                    .into_iter()
                    .filter(|v| {
                        v["proof"]["kind"] == "integer"
                            && v["proof"]["type"].as_str() == Some(typ)
                            && v["proof"]["value"].as_str() == Some(value)
                    })
                    .filter_map(|v| v["spelling"].as_str().map(str::to_owned))
                    .collect::<Vec<_>>();
                ("c-source-integer", value.to_owned(), choices)
            } else {
                let Some(value) = node["value"].as_u64().filter(|v| *v <= 127) else {
                    continue;
                };
                if typ != "int" || !character.is_match(old) {
                    continue;
                }
                let octal = if value == 0 {
                    "0".into()
                } else {
                    format!("0{value:o}")
                };
                (
                    "c-source-character",
                    value.to_string(),
                    vec![value.to_string(), format!("0x{value:x}"), octal],
                )
            };
            if choices.is_empty() {
                continue;
            }
            let key = (rule.to_owned(), typ.to_owned(), old.to_owned());
            let group = groups.entry(key).or_insert_with(|| Group { rule, old: old.to_owned(), sites: BTreeSet::new(), choices,
                proof: json!({"type":typ,"value":value,"target":options.target,"scope":"same integer value, rank and signedness at direct non-macro AST token"}) });
            group.sites.insert(begin);
        }
    }
    Ok(groups.into_values().collect())
}

fn name_groups(
    parsed: &Parsed,
    source: &str,
    tokens: &[Token],
    options: &CSourceOptions,
) -> Vec<Group> {
    if !options.rename_locals {
        return vec![];
    }
    let mut frequency = HashMap::<String, usize>::new();
    for token in tokens
        .iter()
        .filter(|t| t.kind == "identifier" && t.text.len() == 1)
    {
        *frequency.entry(token.text.clone()).or_default() += 1;
    }
    let mut groups = Vec::new();
    for function in top_level_source_nodes(parsed, source)
        .into_iter()
        .filter(|node| node["kind"] == "FunctionDecl")
    {
        if !children(function).any(|n| n["kind"] == "CompoundStmt") {
            continue;
        }
        let Some((lo, hi)) = direct_span(function, &parsed.main_path, source.len()) else {
            continue;
        };
        let mut nodes = Vec::new();
        walk(function, &mut nodes);
        if nodes.iter().any(|n| {
            matches!(
                n["kind"].as_str(),
                Some("GCCAsmStmt" | "MSAsmStmt" | "AsmLabelAttr" | "BlockDecl" | "BlockExpr")
            )
        }) {
            continue;
        }
        let mut used = parsed.macros.clone();
        used.extend(
            tokens
                .iter()
                .filter(|t| t.start >= lo && t.end <= hi && t.kind == "identifier")
                .map(|t| t.text.clone()),
        );
        // A macro may refer to a free identifier absent from the original
        // function tokens. Counting its resolved reference prevents capture.
        for node in &nodes {
            for key in ["name", "referencedDecl"] {
                let name = if key == "name" {
                    node[key].as_str()
                } else {
                    node[key]["name"].as_str()
                };
                if let Some(name) = name {
                    used.insert(name.to_owned());
                }
            }
        }
        let mut choices = (b'a'..=b'z')
            .chain(b'A'..=b'Z')
            .map(|c| (c as char).to_string())
            .filter(|s| !used.contains(s))
            .collect::<Vec<_>>();
        choices.sort_by(|a, b| {
            frequency
                .get(b)
                .unwrap_or(&0)
                .cmp(frequency.get(a).unwrap_or(&0))
                .then_with(|| a.cmp(b))
        });
        choices.truncate(options.names_per_group);
        if choices.is_empty() {
            continue;
        }
        let mut declarations: BTreeMap<String, Vec<&Value>> = BTreeMap::new();
        for node in &nodes {
            if matches!(node["kind"].as_str(), Some("VarDecl" | "ParmVarDecl")) {
                if let Some(name) = node["name"].as_str().filter(|s| !s.is_empty()) {
                    declarations.entry(name.into()).or_default().push(node);
                }
            }
        }
        for (old, declarations) in declarations {
            if parsed.macros.contains(&old)
                || declarations.iter().any(|n| {
                    matches!(
                        n["storageClass"].as_str(),
                        Some("static" | "extern" | "private_extern")
                    ) || n["tls"].as_str().is_some()
                })
            {
                continue;
            }
            let ids = declarations
                .iter()
                .filter_map(|n| n["id"].as_str())
                .collect::<HashSet<_>>();
            if ids.len() != declarations.len() {
                continue;
            }
            let mut binding_ids = Vec::new();
            let mut sites = BTreeSet::new();
            let mut valid = true;
            for node in declarations {
                match direct_location(&node["loc"], &parsed.main_path, source.len()) {
                    Some((a, b))
                        if lo <= a && b <= hi && source.get(a..b) == Some(old.as_str()) =>
                    {
                        sites.insert((a, b));
                        binding_ids.push(format!("declaration-at-{a}"));
                    }
                    _ => {
                        valid = false;
                        break;
                    }
                }
            }
            if !valid {
                continue;
            }
            for node in &nodes {
                if node["kind"] == "DeclRefExpr"
                    && node["referencedDecl"]["id"]
                        .as_str()
                        .is_some_and(|id| ids.contains(id))
                {
                    match direct_span(node, &parsed.main_path, source.len()) {
                        Some((a, b))
                            if lo <= a && b <= hi && source.get(a..b) == Some(old.as_str()) =>
                        {
                            sites.insert((a, b));
                        }
                        _ => {
                            valid = false;
                            break;
                        }
                    }
                }
            }
            if !valid || sites.len() < 2 {
                continue;
            }
            binding_ids.sort();
            groups.push(Group { rule: "c-source-local-name", old, sites, choices: choices.clone(),
                proof: json!({"function":function["name"],"function_start":lo,"binding_ids":binding_ids,
                    "scope":"automatic locals and parameters; declaration/reference identity; fresh in whole function, expanded references and encountered macros"}) });
        }
    }
    groups.sort_by(|a, b| {
        b.sites
            .len()
            .cmp(&a.sites.len())
            .then_with(|| {
                a.proof["function_start"]
                    .as_u64()
                    .cmp(&b.proof["function_start"].as_u64())
            })
            .then_with(|| a.old.cmp(&b.old))
    });
    groups.truncate(options.max_name_groups);
    groups
}

fn contract(source: &[u8], options: &CSourceOptions) -> Value {
    json!({"language":"c","target":options.target,"token_contract":options.frontend.token_contract,
        "source_sha256":sha256(source),"implementation":"native Rust","candidate_objective":"unranked whole-file candidates; equal/longer source allowed",
        "required_acceptance":"verify_variant typed AST/binding check and complete native byte equality under the actual submitted compile recipe"})
}

/// Generate raw plus independently applicable groups. The upper bound includes
/// raw; exhaustion is deterministic and does not imply global optimality.
pub fn generate_variants(source: &[u8], options: &CSourceOptions) -> Result<Vec<Variant>> {
    validate_options(options)?;
    ensure!(
        source.len() <= MAX_SOURCE,
        "source exceeds supported byte limit"
    );
    let mut contract = contract(source, options);
    let mut result = vec![Variant::new(
        "raw",
        source,
        source.into(),
        vec![],
        vec![],
        contract.clone(),
    )];
    if let Some(reason) = unchanged_reason(source, options) {
        result[0].notes.push(reason.into());
        return Ok(result);
    }
    if options.max_candidates == 1 {
        return Ok(result);
    }
    let text = std::str::from_utf8(source)?;
    let tokens = significant(text)?;
    let frontend = Frontend::new(&options.frontend)?;
    let parsed = frontend.parse(source, true)?;
    contract["frontend"] = frontend.info.clone();
    result[0].contract = contract.clone();
    let names = name_groups(&parsed, text, &tokens, options);
    let literals = literal_groups(&parsed, text, options)?;
    // Names first reserves useful one-letter redistribution even when a TU has
    // thousands of literal groups; each family is bounded by the global cap.
    let mut seen = HashSet::from([sha256(source)]);
    let mut retained_bytes = source.len();
    for group in names.into_iter().chain(literals) {
        for replacement in group.choices {
            if replacement == group.old {
                continue;
            }
            let edits = make_edits(text, &tokens, &group.sites, &replacement)?;
            let data = apply_edits(text, &edits)?;
            if data.len() > MAX_SOURCE || retained_bytes + data.len() > MAX_PORTFOLIO_BYTES {
                result[0].notes.push(
                    "source spelling portfolio reached the 64 MiB retained-candidate byte bound"
                        .into(),
                );
                return Ok(result);
            }
            if !seen.insert(sha256(&data)) {
                continue;
            }
            retained_bytes += data.len();
            let mut audit = group.proof.clone();
            audit["rule"] = json!(group.rule);
            audit["before"] = json!(group.old);
            audit["after"] = json!(replacement);
            audit["edits"] = json!(edits);
            let id = format!("c-source-{}", &sha256(&data)[..16]);
            result.push(Variant::new(&id, source, data, vec![audit], vec!["candidate only; typed AST/binding and submitted native comparison still required".into()], contract.clone()));
            if result.len() == options.max_candidates {
                return Ok(result);
            }
        }
    }
    Ok(result)
}

fn recorded_edits(source: &[u8], variant: &Variant) -> Result<Vec<Edit>> {
    ensure!(
        variant.contract["source_sha256"].as_str() == Some(sha256(source).as_str()),
        "candidate belongs to a different original source"
    );
    let mut edits = Vec::new();
    for audit in &variant.audit {
        ensure!(
            matches!(
                audit["rule"].as_str(),
                Some("c-source-local-name" | "c-source-integer" | "c-source-character")
            ),
            "unsupported source spelling audit"
        );
        let current: Vec<Edit> = serde_json::from_value(audit["edits"].clone())
            .context("invalid spelling edit audit")?;
        ensure!(!current.is_empty(), "empty changed spelling group");
        edits.extend(current);
    }
    Ok(edits)
}

fn audited_edits(source: &[u8], variant: &Variant) -> Result<Vec<Edit>> {
    ensure!(
        variant.sha256 == sha256(&variant.data) && variant.bytes == variant.data.len(),
        "candidate byte identity is stale"
    );
    let edits = recorded_edits(source, variant)?;
    ensure!(
        apply_edits(std::str::from_utf8(source)?, &edits)? == variant.data,
        "audited edits do not reconstruct candidate"
    );
    Ok(edits)
}

/// Compose only independently generated groups from the same source. No
/// rebasing of offsets, overlap repair or name-collision exception is inferred.
pub fn compose_variants(
    source: &[u8],
    choices: &[Variant],
    options: &CSourceOptions,
) -> Result<Variant> {
    validate_options(options)?;
    let mut edits = Vec::new();
    let mut audits = Vec::new();
    let mut names = HashSet::new();
    for choice in choices {
        edits.extend(audited_edits(source, choice)?);
        for audit in &choice.audit {
            if audit["rule"] == "c-source-local-name" {
                let function = audit["function_start"]
                    .as_u64()
                    .context("rename function identity missing")?;
                let name = audit["after"].as_str().context("rename spelling missing")?;
                ensure!(
                    names.insert((function, name.to_owned())),
                    "composed local renames collide in the same function"
                );
            }
            audits.push(audit.clone());
        }
    }
    let data = apply_edits(std::str::from_utf8(source)?, &edits)?;
    let id = format!("c-source-composed-{}", &sha256(&data)[..16]);
    Ok(Variant::new(&id, source, data, audits, vec!["composed candidate; verify typed AST/bindings and actual native bytes before acceptance".into()], contract(source, options)))
}

fn local_ids(tree: &Value) -> HashSet<String> {
    fn collect(node: &Value, in_function: bool, result: &mut HashSet<String>) {
        let in_function = in_function || node["kind"] == "FunctionDecl";
        if in_function
            && matches!(node["kind"].as_str(), Some("VarDecl" | "ParmVarDecl"))
            && !matches!(
                node["storageClass"].as_str(),
                Some("static" | "extern" | "private_extern")
            )
        {
            if let Some(id) = node["id"].as_str() {
                result.insert(id.into());
            }
        }
        for child in children(node) {
            collect(child, in_function, result);
        }
    }
    let mut result = HashSet::new();
    collect(tree, false, &mut result);
    result
}

/// Drop physical locations and canonicalize allocation-specific declaration
/// IDs. Keep every other AST property, including all reference relationships,
/// conversion types, attributes, calls, operators and literal values.
fn semantic_signature(tree: &Value) -> Value {
    fn normalize(
        value: &Value,
        key: &str,
        locals: &HashSet<String>,
        ids: &mut HashMap<String, usize>,
    ) -> Value {
        match value {
            Value::Object(object) => {
                let local = object
                    .get("id")
                    .and_then(Value::as_str)
                    .is_some_and(|id| locals.contains(id));
                let constant = matches!(
                    object.get("kind").and_then(Value::as_str),
                    Some("CharacterLiteral" | "IntegerLiteral")
                );
                let mut result = Map::new();
                for (k, v) in object {
                    if matches!(k.as_str(), "loc" | "range")
                        || local && matches!(k.as_str(), "name" | "mangledName")
                    {
                        continue;
                    }
                    let v = if constant && k == "kind" {
                        json!("TypedIntegerConstant")
                    } else if constant && k == "value" {
                        json!(v
                            .as_str()
                            .map(str::to_owned)
                            .unwrap_or_else(|| v.to_string()))
                    } else {
                        normalize(v, k, locals, ids)
                    };
                    result.insert(k.clone(), v);
                }
                Value::Object(result)
            }
            Value::Array(array) => Value::Array(
                array
                    .iter()
                    .map(|v| normalize(v, key, locals, ids))
                    .collect(),
            ),
            Value::String(id)
                if (matches!(
                    key,
                    "id" | "previousDecl"
                        | "canonicalDecl"
                        | "referencedMemberDecl"
                        | "declId"
                        | "parentDeclContextId"
                ) || key.ends_with("DeclId"))
                    && id.starts_with("0x") =>
            {
                let next = ids.len();
                let index = *ids.entry(id.clone()).or_insert(next);
                json!(index)
            }
            other => other.clone(),
        }
    }
    normalize(tree, "", &local_ids(tree), &mut HashMap::new())
}

/// Independent frontend readback for an improving spelling candidate. This
/// checks binding/type preservation, not a different program's equivalence.
/// The actual submitted compiler's complete native-byte comparison remains a
/// separate admission requirement, including charset/ABI/toolchain behavior.
pub fn verify_variant(source: &[u8], candidate: &Variant, options: &CSourceOptions) -> Result<()> {
    validate_options(options)?;
    ensure!(
        source.len() <= MAX_SOURCE && candidate.data.len() <= MAX_SOURCE,
        "source exceeds supported byte limit"
    );
    ensure!(
        unchanged_reason(source, options).is_none(),
        "source does not satisfy spelling observation contract"
    );
    audited_edits(source, candidate)?;
    let frontend = Frontend::new(&options.frontend)?;
    let original = frontend.parse(source, false)?;
    let changed = frontend.parse(&candidate.data, false)?;
    ensure!(
        semantic_signature(&original.tree) == semantic_signature(&changed.tree),
        "candidate changed typed AST structure or declaration/reference bindings"
    );
    Ok(())
}

/// Restore an exact recorded choice without another spelling search. `Variant`
/// deliberately omits source bytes when serialized; the preserved source hash,
/// token edits and expected output identity are sufficient to reconstruct them.
/// Readback still checks the typed AST/bindings, and the caller must separately
/// perform its actual compiler/whole-submission replay checks.
pub fn replay_variant(
    source: &[u8],
    recorded: &Variant,
    options: &CSourceOptions,
) -> Result<Variant> {
    validate_options(options)?;
    ensure!(
        source.len() <= MAX_SOURCE && recorded.bytes <= MAX_SOURCE,
        "recorded source exceeds supported byte limit"
    );
    let edits = recorded_edits(source, recorded)?;
    let data = apply_edits(std::str::from_utf8(source)?, &edits)?;
    ensure!(
        data.len() == recorded.bytes && sha256(&data) == recorded.sha256,
        "recorded spelling edits do not reproduce expected bytes/hash"
    );
    let mut result = recorded.clone();
    result.data = data;
    verify_variant(source, &result, options)?;
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn options() -> Option<CSourceOptions> {
        let clang = std::env::var("NVCOMPACT_CLANG").unwrap_or_else(|_| "clang".into());
        if process::resolve_tool(&clang).is_err() {
            eprintln!("C source spelling frontend fixture not executed: set NVCOMPACT_CLANG");
            return None;
        }
        Some(CSourceOptions {
            frontend: CFlowOptions {
                clang,
                token_contract: "no-token-observation".into(),
                ..Default::default()
            },
            ..Default::default()
        })
    }

    #[test]
    fn opaque_is_identity_without_a_frontend() {
        let options = CSourceOptions {
            frontend: CFlowOptions {
                clang: "/missing/clang".into(),
                ..Default::default()
            },
            ..Default::default()
        };
        let variants = generate_variants(b"int f(int x){return x+100000;}", &options).unwrap();
        assert_eq!(variants.len(), 1);
        assert_eq!(variants[0].data, b"int f(int x){return x+100000;}");
    }

    #[test]
    fn replacement_keeps_keyword_and_hex_exponent_boundaries() {
        for (source, before, after, expected) in [
            (
                "int f(void){return'a';}",
                "'a'",
                "97",
                "int f(void){return 97;}",
            ),
            (
                "int f(void){return 30+1;}",
                "30",
                "0x1e",
                "int f(void){return 0x1e +1;}",
            ),
        ] {
            let start = source.find(before).unwrap();
            let sites = BTreeSet::from([(start, start + before.len())]);
            let edits = make_edits(source, &significant(source).unwrap(), &sites, after).unwrap();
            assert_eq!(apply_edits(source, &edits).unwrap(), expected.as_bytes());
        }
    }

    #[test]
    fn groups_preserve_literal_types_and_macro_bindings() {
        let Some(mut options) = options() else {
            return;
        };
        options.max_candidates = 512;
        let source = b"#define M x\n#define ID(q) q\nint x=17;int f(int input){int old=input+131071;return old+M;}int g(int item){return ID(item);}unsigned long h(void){return 4294967295;}int c(void){return'\\n';}\n";
        let variants = generate_variants(source, &options).unwrap();
        assert!(variants.len() > 1);
        assert!(variants.iter().any(|v| v
            .audit
            .iter()
            .any(|a| a["rule"] == "c-source-integer" && a["after"] == "0377777")));
        assert!(variants.iter().any(|v| v
            .audit
            .iter()
            .any(|a| a["rule"] == "c-source-character" && a["after"] == "10")));
        for variant in variants.iter().skip(1) {
            for audit in &variant.audit {
                assert!(!(audit["rule"] == "c-source-local-name" && audit["after"] == "x"));
                assert!(!(audit["rule"] == "c-source-local-name" && audit["before"] == "item"));
                if audit["before"] == "4294967295" {
                    assert_ne!(audit["after"], "0xffffffff");
                }
            }
            verify_variant(source, variant, &options).unwrap();
        }
    }

    #[test]
    fn one_letter_alternatives_and_safe_composition_are_not_length_pruned() {
        let Some(options) = options() else {
            return;
        };
        let source = b"struct S{struct T*p;int field;};int f(int x){struct S s={0,x};int y=x+131071;if(x<0)goto done;done:return y+x+s.field;}\n";
        let variants = generate_variants(source, &options).unwrap();
        let rename = variants
            .iter()
            .find(|v| {
                v.audit
                    .iter()
                    .any(|a| a["rule"] == "c-source-local-name" && a["before"] == "x")
            })
            .unwrap();
        assert_eq!(rename.data.len(), source.len());
        let number = variants
            .iter()
            .find(|v| {
                v.audit
                    .iter()
                    .any(|a| a["rule"] == "c-source-integer" && a["after"] == "0377777")
            })
            .unwrap();
        assert!(number.data.len() > source.len());
        let combined =
            compose_variants(source, &[rename.clone(), number.clone()], &options).unwrap();
        verify_variant(source, &combined, &options).unwrap();
        let recorded: Variant =
            serde_json::from_slice(&serde_json::to_vec(&combined).unwrap()).unwrap();
        assert!(recorded.data.is_empty());
        assert_eq!(
            replay_variant(source, &recorded, &options).unwrap().data,
            combined.data
        );
        let mut corrupt = recorded.clone();
        corrupt.sha256 = "0".repeat(64);
        assert!(replay_variant(source, &corrupt, &options)
            .unwrap_err()
            .to_string()
            .contains("expected bytes/hash"));
        assert!(compose_variants(source, &[rename.clone(), rename.clone()], &options).is_err());
        let other = variants
            .iter()
            .find(|v| {
                v.audit.iter().any(|a| {
                    a["rule"] == "c-source-local-name"
                        && a["before"] == "y"
                        && a["after"] == rename.audit[0]["after"]
                })
            })
            .unwrap();
        assert!(compose_variants(source, &[rename.clone(), other.clone()], &options).is_err());
    }

    #[test]
    fn readback_rejects_capture_and_value_equal_type_changes() {
        let Some(options) = options() else {
            return;
        };
        for (source, before, after) in [
            ("int a=7;int f(int x){return x+a;}\n", "x", "a"),
            (
                "unsigned long f(void){return 4294967295;}\n",
                "4294967295",
                "0xffffffff",
            ),
        ] {
            let tokens = significant(source).unwrap();
            let sites = tokens
                .iter()
                .filter(|t| t.text == before)
                .map(|t| (t.start, t.end))
                .collect();
            let edits = make_edits(source, &tokens, &sites, after).unwrap();
            let data = apply_edits(source, &edits).unwrap();
            let audit =
                json!({"rule":"c-source-integer","before":before,"after":after,"edits":edits});
            let candidate = Variant::new(
                "forged",
                source.as_bytes(),
                data,
                vec![audit],
                vec![],
                contract(source.as_bytes(), &options),
            );
            let error = verify_variant(source.as_bytes(), &candidate, &options).unwrap_err();
            assert!(
                error
                    .to_string()
                    .contains("typed AST structure or declaration/reference bindings"),
                "unexpected boundary: {error:#}"
            );
        }
    }
}
