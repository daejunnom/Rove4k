//! Binding-aware C spelling candidates for a measured whole-file objective.
//!
//! Generation is deliberately separate from selection. Equal-length and longer
//! spellings can compress better, so this module never chooses by source length.
//! A caller must validate an improving candidate with `verify_variant` and its
//! real compiler recipe before admitting it to a submission portfolio.
pub use crate::c_frontend::FrontendContextChanged;
use crate::c_frontend::{FrontendConfig, FrontendSession, ParsedSource as Parsed};
use crate::cflow::{self, CFlowOptions};
use crate::notation::{lex, literal_candidates, Token, Variant, MAX_SOURCE};
#[cfg(test)]
use crate::process;
use crate::sha256;
use anyhow::{ensure, Context, Result};
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

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
        matches!(
            front.token_contract.as_str(),
            "opaque" | "no-token-observation" | "preprocessed"
        ),
        "unknown source/token contract"
    );
    FrontendConfig::from(front).validate()
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

/// An immutable source basis and its typed observation. Candidate generation,
/// composition and admission have separate methods; none selects a winner.
/// A round shares lexical/AST setup, while every changed candidate still gets
/// a fresh AST and cached base proofs require current preprocessing readback.
pub struct PreparedSource {
    source: Vec<u8>,
    options: CSourceOptions,
    analysis: Option<PreparedAnalysis>,
}

struct PreparedAnalysis {
    frontend: FrontendSession,
    parsed: Parsed,
    tokens: Vec<Token>,
    signature: Value,
}

impl PreparedAnalysis {
    fn new(source: &[u8], options: &CSourceOptions) -> Result<Self> {
        let tokens = significant(std::str::from_utf8(source)?)?;
        let frontend = FrontendSession::new(FrontendConfig::from(&options.frontend), true)?;
        let parsed = frontend.parse(source, true)?;
        ensure!(
            parsed.preprocessing.as_ref().is_some_and(|p| p.utf8),
            "Clang preprocessing output is not UTF-8"
        );
        let signature = semantic_signature(&parsed.tree);
        Ok(Self {
            frontend,
            parsed,
            tokens,
            signature,
        })
    }
}

impl PreparedSource {
    pub fn new(source: &[u8], options: &CSourceOptions) -> Result<Self> {
        validate_options(options)?;
        ensure!(
            source.len() <= MAX_SOURCE,
            "source exceeds supported byte limit"
        );
        let analysis = if unchanged_reason(source, options).is_none() && options.max_candidates > 1
        {
            Some(PreparedAnalysis::new(source, options)?)
        } else {
            None
        };
        Ok(Self {
            source: source.to_vec(),
            options: options.clone(),
            analysis,
        })
    }

    pub fn source(&self) -> &[u8] {
        &self.source
    }

    pub fn statistics(&self) -> Value {
        self.analysis
            .as_ref()
            .map(|a| a.frontend.statistics())
            .unwrap_or_else(
                || json!({"commands":0,"ast_parses":0,"preprocessing_runs":0,"context_rechecks":0}),
            )
    }

    pub fn generate_variants(&self) -> Result<Vec<Variant>> {
        generate_prepared(self)
    }

    pub fn compose_variants(&self, choices: &[Variant]) -> Result<Variant> {
        let text = std::str::from_utf8(&self.source)?;
        if let Some(analysis) = &self.analysis {
            compose_with_tokens(&self.source, choices, &self.options, &analysis.tokens)
        } else {
            compose_with_tokens(&self.source, choices, &self.options, &significant(text)?)
        }
    }

    pub fn verify_variant(&self, candidate: &Variant) -> Result<()> {
        ensure!(
            candidate.data.len() <= MAX_SOURCE,
            "source exceeds supported byte limit"
        );
        ensure!(
            unchanged_reason(&self.source, &self.options).is_none(),
            "source does not satisfy spelling observation contract"
        );
        let temporary;
        let analysis = if let Some(analysis) = &self.analysis {
            analysis
        } else {
            temporary = PreparedAnalysis::new(&self.source, &self.options)?;
            &temporary
        };
        audited_edits_with_tokens(&self.source, candidate, &analysis.tokens)?;
        analysis.frontend.recheck(&self.source, &analysis.parsed)?;
        let changed = analysis.frontend.parse(&candidate.data, false);
        // A source-context mutation can itself cause a parse/proof failure.
        // Revalidate before classifying that failure as candidate-specific.
        analysis.frontend.recheck(&self.source, &analysis.parsed)?;
        let changed = changed?;
        ensure!(
            analysis.signature == semantic_signature(&changed.tree),
            "candidate changed typed AST structure or declaration/reference bindings"
        );
        Ok(())
    }

    /// Policy knobs may differ; the physical frontend invocation must match.
    /// The flow analyzer owns its view of this snapshot and reparses changes.
    pub fn flow_variants(&self, options: &CFlowOptions) -> Result<Vec<Variant>> {
        ensure!(
            options.token_contract == self.options.frontend.token_contract,
            "flow and spelling observation contracts differ"
        );
        if let Some(analysis) = &self.analysis {
            ensure!(
                analysis.frontend.matches(&FrontendConfig::from(options)),
                "flow and spelling frontend configurations differ"
            );
            analysis.frontend.recheck(&self.source, &analysis.parsed)?;
            let variants = cflow::generate_variants_with_snapshot(
                &self.source,
                options,
                &analysis.frontend,
                &analysis.parsed,
                &analysis.tokens,
            );
            analysis.frontend.recheck(&self.source, &analysis.parsed)?;
            variants
        } else {
            cflow::generate_variants(&self.source, options)
        }
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
    apply_edits_with_tokens(source, edits, &significant(source)?)
}

fn apply_edits_with_tokens(source: &str, edits: &[Edit], tokens: &[Token]) -> Result<Vec<u8>> {
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
) -> (Vec<Group>, Value) {
    if !options.rename_locals {
        return (
            vec![],
            json!({"enabled":false,"discovered_groups":0,"available_choices":0,"selected_groups":0,"selected_choices":0,
            "max_name_groups":options.max_name_groups,"names_per_group":options.names_per_group}),
        );
    }
    let mut frequency = HashMap::<String, usize>::new();
    for token in tokens
        .iter()
        .filter(|t| t.kind == "identifier" && t.text.len() == 1)
    {
        *frequency.entry(token.text.clone()).or_default() += 1;
    }
    let mut groups = Vec::new();
    let mut available_choices = 0usize;
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
        let available_for_group = choices.len();
        choices.truncate(options.names_per_group);
        if choices.is_empty() {
            continue;
        }
        let mut declarations: BTreeMap<String, Vec<&Value>> = BTreeMap::new();
        let mut references: HashMap<&str, Vec<&Value>> = HashMap::new();
        for node in &nodes {
            if matches!(node["kind"].as_str(), Some("VarDecl" | "ParmVarDecl")) {
                if let Some(name) = node["name"].as_str().filter(|s| !s.is_empty()) {
                    declarations.entry(name.into()).or_default().push(node);
                }
            } else if node["kind"] == "DeclRefExpr" {
                if let Some(id) = node["referencedDecl"]["id"].as_str() {
                    references.entry(id).or_default().push(node);
                }
            }
        }
        for (old, declarations) in declarations {
            if parsed.macros.contains(&old) {
                continue;
            }
            let mut ids = HashSet::new();
            let mut bindings = Vec::new();
            let mut complete = true;
            for declaration in &declarations {
                if matches!(
                    declaration["storageClass"].as_str(),
                    Some("static" | "extern" | "private_extern")
                ) || declaration["tls"].as_str().is_some()
                {
                    complete = false;
                    continue;
                }
                let binding = (|| {
                    let id = declaration["id"].as_str()?;
                    if !ids.insert(id) {
                        return None;
                    }
                    let (start, end) =
                        direct_location(&declaration["loc"], &parsed.main_path, source.len())?;
                    if !(lo <= start && end <= hi && source.get(start..end) == Some(old.as_str())) {
                        return None;
                    }
                    let mut sites = BTreeSet::from([(start, end)]);
                    for node in references.get(id).into_iter().flatten() {
                        let (a, b) = direct_span(node, &parsed.main_path, source.len())?;
                        if !(lo <= a && b <= hi && source.get(a..b) == Some(old.as_str())) {
                            return None;
                        }
                        sites.insert((a, b));
                    }
                    Some((start, sites))
                })();
                if let Some(binding) = binding {
                    bindings.push(binding);
                } else {
                    complete = false;
                }
            }
            // Preserve the old same-spelling batch and its budget priority.
            // Per-declaration alternatives follow it, rather than replacing
            // an existing multi-binding candidate with costly compositions.
            if complete && !bindings.is_empty() {
                let sites = bindings.iter().flat_map(|(_, sites)| sites.iter().copied()).collect::<BTreeSet<_>>();
                if sites.len() >= 2 {
                    let mut binding_ids = bindings.iter().map(|(start, _)| format!("declaration-at-{start}")).collect::<Vec<_>>();
                    binding_ids.sort();
                    available_choices += available_for_group;
                    groups.push(Group { rule: "c-source-local-name", old:old.clone(), sites, choices: choices.clone(),
                        proof: json!({"function":function["name"],"function_start":lo,"binding_ids":binding_ids,
                            "scope":"automatic locals and parameters; declaration/reference identity; fresh in whole function, expanded references and encountered macros"}) });
                }
            }
            // A spelling is not a binding. Keep independently measurable
            // shadowed declarations, using only their resolved references.
            // Destinations remain fresh in the entire function: no scope
            // reuse, simultaneous swap or lookup-conflict relaxation.
            if declarations.len() > 1 {
                for (start, sites) in bindings.into_iter().filter(|(_, sites)| sites.len() >= 2) {
                    available_choices += available_for_group;
                    groups.push(Group { rule: "c-source-local-name", old:old.clone(), sites, choices: choices.clone(),
                        proof: json!({"function":function["name"],"function_start":lo,"declaration_start":start,
                            "independent_binding":true,"binding_ids":[format!("declaration-at-{start}")],
                            "scope":"one automatic declaration and its resolved references; fresh in whole function, expanded references and encountered macros"}) });
                }
            }
        }
    }
    groups.sort_by(|a, b| {
        a.proof["independent_binding"].as_bool().unwrap_or(false)
            .cmp(&b.proof["independent_binding"].as_bool().unwrap_or(false))
            .then_with(|| b.sites.len().cmp(&a.sites.len()))
            .then_with(|| {
                a.proof["function_start"]
                    .as_u64()
                    .cmp(&b.proof["function_start"].as_u64())
            })
            .then_with(|| a.old.cmp(&b.old))
            .then_with(|| {
                a.proof["declaration_start"]
                    .as_u64()
                    .cmp(&b.proof["declaration_start"].as_u64())
            })
    });
    let discovered_groups = groups.len();
    let choices_after_name_limit = groups.iter().map(|g| g.choices.len()).sum::<usize>();
    groups.truncate(options.max_name_groups);
    let coverage = json!({"enabled":true,"scope":"eligible automatic declaration groups, preserved same-spelling batches and fresh ASCII letters a-z/A-Z",
        "group_order":"legacy same-spelling groups first, then independent shadowed declarations; use count, function offset, spelling and declaration offset",
        "discovered_groups":discovered_groups,"available_choices":available_choices,
        "choices_after_names_per_group":choices_after_name_limit,"selected_groups":groups.len(),
        "selected_choices":groups.iter().map(|g|g.choices.len()).sum::<usize>(),
        "max_name_groups":options.max_name_groups,"names_per_group":options.names_per_group});
    (groups, coverage)
}

fn contract(source: &[u8], options: &CSourceOptions) -> Value {
    json!({"language":"c","target":options.target,"token_contract":options.frontend.token_contract,
        "source_sha256":sha256(source),"implementation":"native Rust","candidate_objective":"unranked whole-file candidates; equal/longer source allowed",
        "required_acceptance":"verify_variant typed AST/binding check and complete native byte equality under the actual submitted compile recipe"})
}

/// Generate raw plus independently applicable groups. The upper bound includes
/// raw; exhaustion is deterministic and does not imply global optimality.
pub fn generate_variants(source: &[u8], options: &CSourceOptions) -> Result<Vec<Variant>> {
    PreparedSource::new(source, options)?.generate_variants()
}

fn generate_prepared(prepared: &PreparedSource) -> Result<Vec<Variant>> {
    let source = prepared.source.as_slice();
    let options = &prepared.options;
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
        result[0].contract["generation"] = json!({"status":"inapplicable","reason":reason,"generated_variants":1,"scope":"registered guarded source spellings only"});
        return Ok(result);
    }
    if options.max_candidates == 1 {
        result[0].contract["generation"] = json!({"status":"bounded","stop_reason":"max_candidates","generated_variants":1,"discovery":"not performed"});
        return Ok(result);
    }
    let text = std::str::from_utf8(source)?;
    let analysis = prepared
        .analysis
        .as_ref()
        .context("prepared source analysis missing")?;
    let tokens = &analysis.tokens;
    let parsed = &analysis.parsed;
    contract["frontend"] = analysis.frontend.info.clone();
    result[0].contract = contract.clone();
    let (names, name_coverage) = name_groups(parsed, text, tokens, options);
    let literals = literal_groups(parsed, text, options)?;
    let literal_groups = literals.len();
    let literal_choices = literals
        .iter()
        .map(|g| g.choices.iter().filter(|s| **s != g.old).count())
        .sum::<usize>();
    let scheduled_choices = names
        .iter()
        .map(|g| g.choices.iter().filter(|s| **s != g.old).count())
        .sum::<usize>()
        + literal_choices;
    let mut generation = json!({"scope":"registered guarded spelling groups; no spelling combinations or arbitrary C programs",
        "names":name_coverage,"literal_groups":literal_groups,"literal_choices":literal_choices,
        "scheduled_choices":scheduled_choices,"max_candidates":options.max_candidates,
        "source_byte_limit":MAX_SOURCE,
        "retained_candidate_byte_limit":MAX_PORTFOLIO_BYTES,"generated_variants":1,
        "visited_choices":0,"duplicate_choices":0,"stop_reason":null});
    let mut visited = 0usize;
    let mut duplicates = 0usize;
    let mut stop_reason = None;
    // Preserve the existing name/literal portfolio prefix under the global
    // candidate/memory budget. New binding alternatives follow it, so adding
    // them does not silently evict a previously reachable literal spelling.
    let (legacy_names, independent_names): (Vec<_>, Vec<_>) = names
        .into_iter()
        .partition(|g| g.proof["independent_binding"] != true);
    let mut seen = HashSet::from([sha256(source)]);
    let mut retained_bytes = source.len();
    'groups: for group in legacy_names.into_iter().chain(literals).chain(independent_names) {
        for replacement in group.choices {
            if replacement == group.old {
                continue;
            }
            visited += 1;
            let edits = make_edits(text, tokens, &group.sites, &replacement)?;
            let data = apply_edits_with_tokens(text, &edits, tokens)?;
            if data.len() > MAX_SOURCE || retained_bytes + data.len() > MAX_PORTFOLIO_BYTES {
                result[0].notes.push(
                    if data.len() > MAX_SOURCE {
                        "source spelling candidate exceeds the supported source-byte bound"
                    } else {
                        "source spelling portfolio reached the 64 MiB retained-candidate byte bound"
                    }
                    .into(),
                );
                stop_reason = Some(if data.len() > MAX_SOURCE {
                    "source-byte-limit"
                } else {
                    "retained-candidate-byte-limit"
                });
                break 'groups;
            }
            if !seen.insert(sha256(&data)) {
                duplicates += 1;
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
            if result.len() == options.max_candidates && visited < scheduled_choices {
                stop_reason = Some("max_candidates");
                break 'groups;
            }
        }
    }
    generation["generated_variants"] = json!(result.len());
    generation["visited_choices"] = json!(visited);
    generation["duplicate_choices"] = json!(duplicates);
    generation["stop_reason"] = json!(stop_reason);
    let names_complete = generation["names"]["discovered_groups"]
        == generation["names"]["selected_groups"]
        && generation["names"]["available_choices"] == generation["names"]["selected_choices"];
    generation["status"] = json!(if stop_reason.is_none() && names_complete {
        "registered-single-space-exhausted"
    } else {
        "bounded"
    });
    generation["retained_candidate_bytes"] = json!(retained_bytes);
    result[0].contract["generation"] = generation;
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

fn audited_edits_with_tokens(
    source: &[u8],
    variant: &Variant,
    tokens: &[Token],
) -> Result<Vec<Edit>> {
    ensure!(
        variant.sha256 == sha256(&variant.data) && variant.bytes == variant.data.len(),
        "candidate byte identity is stale"
    );
    let edits = recorded_edits(source, variant)?;
    ensure!(
        apply_edits_with_tokens(std::str::from_utf8(source)?, &edits, tokens)? == variant.data,
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
    compose_with_tokens(
        source,
        choices,
        options,
        &significant(std::str::from_utf8(source)?)?,
    )
}

fn compose_with_tokens(
    source: &[u8],
    choices: &[Variant],
    options: &CSourceOptions,
    tokens: &[Token],
) -> Result<Variant> {
    let mut edits = Vec::new();
    let mut audits = Vec::new();
    let mut names = HashSet::new();
    for choice in choices {
        edits.extend(audited_edits_with_tokens(source, choice, tokens)?);
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
    let data = apply_edits_with_tokens(std::str::from_utf8(source)?, &edits, tokens)?;
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
    audited_edits_with_tokens(
        source,
        candidate,
        &significant(std::str::from_utf8(source)?)?,
    )?;
    let frontend = FrontendSession::new(FrontendConfig::from(&options.frontend), true)?;
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
    fn prepared_source_reuses_base_analysis_without_changing_candidates_or_proofs() {
        let Some(mut options) = options() else {
            return;
        };
        options.max_name_groups = 1;
        options.names_per_group = 2;
        options.max_candidates = 8;
        let source=b"int f(int input){int local=input+131071;return local+input;}int b(_Bool flag){return flag!=1;}\n";
        let prepared = PreparedSource::new(source, &options).unwrap();
        let variants = prepared.generate_variants().unwrap();
        let coverage = &variants[0].contract["generation"];
        assert!(
            coverage["names"]["discovered_groups"].as_u64().unwrap()
                > coverage["names"]["selected_groups"].as_u64().unwrap()
        );
        assert!(
            coverage["names"]["available_choices"].as_u64().unwrap()
                > coverage["names"]["selected_choices"].as_u64().unwrap()
        );
        assert_eq!(coverage["status"], "bounded");
        let ast_before = prepared.statistics()["ast_parses"].as_u64().unwrap();
        let changed = variants
            .iter()
            .filter(|v| v.data != source)
            .take(2)
            .collect::<Vec<_>>();
        assert_eq!(changed.len(), 2);
        for candidate in &changed {
            prepared.verify_variant(candidate).unwrap();
            verify_variant(source, candidate, &options).unwrap();
        }
        assert_eq!(
            prepared.statistics()["ast_parses"].as_u64().unwrap() - ast_before,
            changed.len() as u64,
            "shared gate must freshly parse each changed candidate without redoing base AST"
        );
        let mut flows = options.frontend.clone();
        flows.max_variants = 32;
        flows.individual_edits = 4;
        flows.include_nonshrinking = true;
        let shared = prepared.flow_variants(&flows).unwrap();
        let separate = cflow::generate_variants(source, &flows).unwrap();
        assert_eq!(
            shared
                .iter()
                .map(|v| (&v.id, &v.data, &v.audit))
                .collect::<Vec<_>>(),
            separate
                .iter()
                .map(|v| (&v.id, &v.data, &v.audit))
                .collect::<Vec<_>>()
        );
        assert_eq!(shared[0].contract["generation"]["source_ast_reused"], true);
        assert_eq!(
            shared[0].contract["generation"]["all_edit_combinations_explored"],
            false
        );
        flows.compiler_args.push("-funsigned-char".into());
        assert!(prepared
            .flow_variants(&flows)
            .unwrap_err()
            .to_string()
            .contains("configurations differ"));
    }

    #[test]
    fn prepared_proof_refuses_changed_include_context_and_keeps_generation_limits_explicit() {
        let Some(mut options) = options() else {
            return;
        };
        let directory = tempfile::tempdir().unwrap();
        let source_path = directory.path().join("input.c");
        let header = directory.path().join("values.h");
        let source = b"#include \"values.h\"\nint f(int value){return value+VALUE;}\n";
        std::fs::write(&source_path, source).unwrap();
        std::fs::write(&header, b"#define VALUE 17\n").unwrap();
        options.frontend.source_path = Some(source_path);
        options.max_candidates = 2;
        let prepared = PreparedSource::new(source, &options).unwrap();
        let variants = prepared.generate_variants().unwrap();
        assert_eq!(
            variants[0].contract["generation"]["stop_reason"],
            "max_candidates"
        );
        prepared.verify_variant(&variants[1]).unwrap();
        std::fs::write(&header, b"#define VALUE 18\n").unwrap();
        let changed = prepared.verify_variant(&variants[1]).unwrap_err();
        assert!(changed
            .to_string()
            .contains("preprocessing context changed"));
        assert!(changed.downcast_ref::<FrontendContextChanged>().is_some());
        assert!(prepared
            .flow_variants(&options.frontend)
            .unwrap_err()
            .to_string()
            .contains("preprocessing context changed"));
        // A separate proof has a new input context; a previous observation is
        // never silently promoted to that new context by the cached session.
        verify_variant(source, &variants[1], &options).unwrap();
        std::fs::remove_file(header).unwrap();
        let missing = prepared.verify_variant(&variants[1]).unwrap_err();
        assert!(
            missing.downcast_ref::<FrontendContextChanged>().is_some(),
            "an unreadable include context cannot become a candidate-only rejection"
        );
    }

    #[test]
    fn context_mutation_is_not_hidden_by_a_failed_candidate_parse() {
        use std::os::unix::fs::PermissionsExt;
        let Some(mut options) = options() else {
            return;
        };
        let directory = tempfile::tempdir().unwrap();
        let source_path = directory.path().join("input.c");
        let header = directory.path().join("values.h");
        let trigger = directory.path().join("change-on-ast");
        let wrapper = directory.path().join("observed-clang");
        let real = process::resolve_tool(&options.frontend.clang).unwrap();
        let word =
            |path: &std::path::Path| format!("'{}'", path.to_string_lossy().replace('\'', "'\\''"));
        let script=format!("#!/bin/sh\nfor arg do\n if [ \"$arg\" = -ast-dump=json ] && [ -f {} ]; then\n  printf '#error changed during candidate parse\\n' > {}\n fi\ndone\nexec {} \"$@\"\n",word(&trigger),word(&header),word(&real));
        std::fs::write(&wrapper, script).unwrap();
        std::fs::set_permissions(&wrapper, std::fs::Permissions::from_mode(0o700)).unwrap();
        // Keep the macro out of the transformed function: the existing flow
        // guard correctly protects functions that directly observe macros.
        let source = b"#include \"values.h\"\nint marker=VALUE;int f(int value){if(value)return 17;else return 0;}\n";
        std::fs::write(&source_path, source).unwrap();
        options.frontend.clang = wrapper.to_string_lossy().into_owned();
        options.frontend.source_path = Some(source_path);
        options.max_candidates = 2;
        for flow in [false, true] {
            std::fs::write(&header, b"#define VALUE 17\n").unwrap();
            if trigger.exists() {
                std::fs::remove_file(&trigger).unwrap();
            }
            let prepared = PreparedSource::new(source, &options).unwrap();
            let variants = prepared.generate_variants().unwrap();
            std::fs::write(&trigger, b"armed").unwrap();
            let failure = if flow {
                prepared.flow_variants(&options.frontend).unwrap_err()
            } else {
                prepared.verify_variant(&variants[1]).unwrap_err()
            };
            assert!(
                failure.downcast_ref::<FrontendContextChanged>().is_some(),
                "a failed parse must still detect mutation of the reused base: {failure:#}"
            );
        }
    }

    #[test]
    fn shared_frontend_preserves_the_consumers_encoding_contracts() {
        let Some(mut options) = options() else {
            return;
        };
        let directory = tempfile::tempdir().unwrap();
        let source_path = directory.path().join("input.c");
        let source = b"#include \"bytes.h\"\nint f(int value){if(value)return 1;else return 2;}\n";
        std::fs::write(&source_path, source).unwrap();
        // An unused macro preserves a raw literal byte in -E -dD output while
        // the actual translation unit is valid and its function is ordinary C.
        std::fs::write(directory.path().join("bytes.h"), b"#define RAW \"\xff\"\n").unwrap();
        options.frontend.source_path = Some(source_path);
        let flows = cflow::generate_variants(source, &options.frontend).unwrap();
        assert!(
            flows.iter().any(|v| v.data != source),
            "the shared frontend must retain flow's header-byte support"
        );
        let error = generate_variants(source, &options).unwrap_err();
        assert!(
            error.to_string().contains("not UTF-8"),
            "spelling analysis keeps its existing stricter contract: {error:#}"
        );
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
    fn shadowed_declarations_have_independent_replayable_binding_candidates() {
        let Some(mut options) = options() else {
            return;
        };
        options.integer_literals = false;
        options.character_literals = false;
        options.names_per_group = 2;
        let source = b"int f(int value){int total=value;{int initial=value;int value=initial+1;total+=value;}return total+value;}\n";
        let text = std::str::from_utf8(source).unwrap();
        let parameter_at = text.find("value").unwrap();
        let local_at = text.find("int value=initial").unwrap() + 4;
        let prepared = PreparedSource::new(source, &options).unwrap();
        let variants = prepared.generate_variants().unwrap();
        let parameter = variants.iter().find(|v| {
            v.audit.iter().any(|a| a["independent_binding"] == true
                && a["declaration_start"].as_u64() == Some(parameter_at as u64))
        }).unwrap();
        let parameter_name = parameter.audit[0]["after"].as_str().unwrap();
        let local = variants.iter().find(|v| {
            v.audit.iter().any(|a| a["independent_binding"] == true
                && a["declaration_start"].as_u64() == Some(local_at as u64)
                && a["after"].as_str() != Some(parameter_name))
        }).unwrap();
        let local_name = local.audit[0]["after"].as_str().unwrap();
        // The initializer before the inner declaration still resolves to the
        // parameter. The later inner use must remain a different binding.
        let expected_parameter = text
            .replace("f(int value)", &format!("f(int {parameter_name})"))
            .replace("total=value", &format!("total={parameter_name}"))
            .replace("initial=value", &format!("initial={parameter_name}"))
            .replace("return total+value", &format!("return total+{parameter_name}"));
        let expected_local = text
            .replace("int value=initial", &format!("int {local_name}=initial"))
            .replace("total+=value", &format!("total+={local_name}"));
        assert_eq!(parameter.data, expected_parameter.as_bytes());
        assert_eq!(local.data, expected_local.as_bytes());
        prepared.verify_variant(parameter).unwrap();
        prepared.verify_variant(local).unwrap();
        let combined = prepared.compose_variants(&[parameter.clone(), local.clone()]).unwrap();
        prepared.verify_variant(&combined).unwrap();
        let expected_both = expected_parameter
            .replace("int value=initial", &format!("int {local_name}=initial"))
            .replace("total+=value", &format!("total+={local_name}"));
        assert_eq!(combined.data, expected_both.as_bytes());
        let recorded: Variant = serde_json::from_slice(&serde_json::to_vec(&combined).unwrap()).unwrap();
        assert_eq!(replay_variant(source, &recorded, &options).unwrap().data, combined.data);
        let same_destination = variants.iter().find(|v| {
            v.audit.iter().any(|a| a["independent_binding"] == true
                && a["declaration_start"].as_u64() == Some(local_at as u64)
                && a["after"].as_str() == Some(parameter_name))
        }).unwrap();
        assert!(prepared.compose_variants(&[parameter.clone(), same_destination.clone()]).is_err());
    }

    #[test]
    fn legacy_shadowed_batch_keeps_its_bounded_candidate_priority() {
        let Some(mut options) = options() else {
            return;
        };
        options.integer_literals = false;
        options.character_literals = false;
        options.max_name_groups = 1;
        options.names_per_group = 1;
        options.max_candidates = 2;
        let source = b"int f(int item){int sum=item;{int item=1;sum+=item;}{int item=2;sum+=item;}{int item=3;sum+=item;}return sum+item;}\n";
        let prepared = PreparedSource::new(source, &options).unwrap();
        let variants = prepared.generate_variants().unwrap();
        let batch = variants.iter().find(|v| v.audit.iter().any(|a| a["before"] == "item")).unwrap();
        let audit = &batch.audit[0];
        assert_eq!(audit["binding_ids"].as_array().unwrap().len(), 4);
        assert_ne!(audit["independent_binding"], true);
        let replacement = audit["after"].as_str().unwrap();
        assert_eq!(batch.data, std::str::from_utf8(source).unwrap().replace("item", replacement).as_bytes());
        prepared.verify_variant(batch).unwrap();
        assert!(variants[0].contract["generation"]["names"]["discovered_groups"].as_u64().unwrap() > 1);
        assert_eq!(variants[0].contract["generation"]["names"]["selected_groups"], 1);
    }

    #[test]
    fn independent_bindings_follow_the_legacy_name_and_literal_portfolio() {
        let Some(mut options) = options() else {
            return;
        };
        options.names_per_group = 1;
        let source = b"int f(int value){int total=value;{int value=131071;total+=value;}return total+value;}\n";
        let variants = generate_variants(source, &options).unwrap();
        let first_independent = variants.iter().position(|v| {
            v.audit.iter().any(|a| a["independent_binding"] == true)
        }).unwrap();
        let last_literal = variants.iter().rposition(|v| {
            v.audit.iter().any(|a| a["rule"] == "c-source-integer")
        }).unwrap();
        assert!(last_literal < first_independent);
        options.max_candidates = first_independent;
        let bounded = generate_variants(source, &options).unwrap();
        assert_eq!(bounded.len(), first_independent);
        assert!(bounded.iter().all(|v| v.audit.iter().all(|a| a["independent_binding"] != true)));
        for (before, after) in variants.iter().zip(bounded.iter()).skip(1) {
            assert_eq!(before.id, after.id);
            assert_eq!(before.data, after.data);
        }
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
