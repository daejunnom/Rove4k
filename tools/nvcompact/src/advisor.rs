//! Read-only C short-coding advice. No finding is a transformation, candidate,
//! verifier result, or permission to change a submitted file.
//!
//! Clang owns binding and C conversion information. The range pass deliberately
//! implements a small intraprocedural subset: unsupported control flow loses
//! facts, address-taken/volatile/static objects are not tracked, and loops start
//! from widened states. A range describes one evaluated read, not a variable's
//! lifetime. Final-file cost and source-observation contracts remain external.
use crate::c_frontend::{FrontendConfig, FrontendSession, ParsedSource};
use crate::{notation::MAX_SOURCE, sha256};
use anyhow::{ensure, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::cell::Cell;
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::path::PathBuf;

mod cpp;
pub(crate) mod domain;
mod expressions;
mod flow;
pub mod nversion;
pub mod rust;
pub use domain::DomainSummary;
pub use expressions::ExpressionSite;

/// An explicit source-language contract. Unsupported languages never fall
/// through to a fixed-width C analysis based on filename or similar syntax.
#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum SourceLanguage {
    C,
    Cpp,
    Rust,
}

impl std::str::FromStr for SourceLanguage {
    type Err = anyhow::Error;

    fn from_str(value: &str) -> Result<Self> {
        match value {
            "c" => Ok(Self::C),
            "cpp" | "c++" => Ok(Self::Cpp),
            "rust" => Ok(Self::Rust),
            _ => anyhow::bail!(
                "unsupported advisory language {value:?}; supported: c, cpp, rust. Python and other languages are explicitly unsupported by this fixed-width domain analyzer"
            ),
        }
    }
}

impl SourceLanguage {
    pub fn default_standard(self) -> &'static str {
        match self {
            Self::C => "c11",
            Self::Cpp => "c++17",
            Self::Rust => "rust2021",
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct AdvisorOptions {
    pub clang: String,
    pub standard: String,
    pub compiler_args: Vec<String>,
    pub source_path: Option<PathBuf>,
    pub frontend_seconds: f64,
    pub frontend_memory_bytes: u64,
    pub ast_bytes: usize,
    pub max_findings: usize,
    pub max_ranges: usize,
    pub max_nversion_targets: usize,
    pub max_nversion_work: usize,
    pub max_finite_flow_work: usize,
}

impl Default for AdvisorOptions {
    fn default() -> Self {
        Self {
            clang: "clang".into(),
            standard: "c11".into(),
            compiler_args: vec![],
            source_path: None,
            frontend_seconds: 30.0,
            frontend_memory_bytes: 1 << 30,
            ast_bytes: 32 << 20,
            max_findings: 1_000,
            max_ranges: 10_000,
            max_nversion_targets: 64,
            max_nversion_work: 16_000_000,
            max_finite_flow_work: 8_000_000,
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct SourceLocation {
    /// UTF-8 byte offsets; end is exclusive. Line/column are one-based.
    pub start: usize,
    pub end: usize,
    pub line: usize,
    pub column: usize,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Finding {
    pub id: String,
    pub kind: String,
    pub assurance: String,
    pub location: SourceLocation,
    pub function: Option<String>,
    pub symbol: Option<String>,
    pub message: String,
    /// A reviewable expression or a design suggestion, never an applied edit.
    pub suggestion: Option<String>,
    pub original: String,
    pub related_locations: Vec<SourceLocation>,
    pub requirements: Vec<String>,
    /// Counts only this spelling's source bytes, never compressed/native bytes.
    pub estimated_source_bytes_saved: Option<isize>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RangeSite {
    /// Stable only together with source_sha256 and analysis_context_sha256.
    pub id: String,
    pub location: SourceLocation,
    pub function: String,
    pub symbol: String,
    pub expression: String,
    pub c_type: String,
    pub minimum: String,
    pub maximum: String,
    pub basis: Vec<String>,
    pub operation: Option<String>,
    /// Only direct, evaluated, non-volatile local scalar reads are eligible.
    #[serde(default)]
    pub instrumentable: bool,
    #[serde(default)]
    pub domain: Option<DomainSummary>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AdviceReport {
    pub format_version: u32,
    pub advisory_only: bool,
    pub source_sha256: String,
    pub analysis_context_sha256: String,
    pub frontend: Value,
    pub statistics: Value,
    pub findings: Vec<Finding>,
    pub ranges: Vec<RangeSite>,
    #[serde(default)]
    pub expressions: Vec<ExpressionSite>,
    /// Language-specific typed evidence. C++/Rust adapters do not expose their
    /// internal C candidate carrier as a proof of source-language semantics.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub language_details: Option<Value>,
    pub limitations: Vec<String>,
    /// False when report budgets omit findings or range sites. True is not a
    /// claim to cover unsupported C or to prove whole-program equivalence.
    pub complete: bool,
}

pub(super) fn validate_options(source: &[u8], options: &AdvisorOptions) -> Result<()> {
    ensure!(source.len() <= MAX_SOURCE, "advisor source exceeds 8 MiB");
    ensure!(
        (1..=100_000).contains(&options.max_findings)
            && (1..=100_000).contains(&options.max_ranges),
        "advisor finding/range budgets must be in 1..=100000"
    );
    ensure!(
        (1..=512).contains(&options.max_nversion_targets)
            && (1_000..=100_000_000).contains(&options.max_nversion_work)
            && (1_000..=100_000_000).contains(&options.max_finite_flow_work),
        "n-version targets must be 1..512 and work budgets 1000..100000000"
    );
    Ok(())
}

pub fn analyze_source(
    source: &[u8],
    language: SourceLanguage,
    options: &AdvisorOptions,
) -> Result<AdviceReport> {
    match language {
        SourceLanguage::C => analyze(source, options),
        SourceLanguage::Cpp => cpp::analyze(source, options),
        SourceLanguage::Rust => rust::analyze(source, options),
    }
}

pub fn analyze(source: &[u8], options: &AdvisorOptions) -> Result<AdviceReport> {
    validate_options(source, options)?;
    let source = std::str::from_utf8(source)?;
    let frontend = FrontendSession::new(
        FrontendConfig {
            clang: options.clang.clone(),
            standard: options.standard.clone(),
            compiler_args: options.compiler_args.clone(),
            source_path: options.source_path.clone(),
            seconds: options.frontend_seconds,
            memory_bytes: options.frontend_memory_bytes,
            ast_bytes: options.ast_bytes,
        },
        true,
    )?;
    let parsed = frontend.parse_for_advice(source.as_bytes())?;
    let context = sha256(&serde_json::to_vec(&json!({
        "source_sha256": sha256(source.as_bytes()),
        "frontend": frontend.info,
        "preprocessing_sha256": parsed.preprocessing.as_ref().and_then(|p| p.stable_sha256.as_ref()),
        "analysis": "intraprocedural-c-lp64-domains-nversion-v2",
        "finite_flow_work_budget": options.max_finite_flow_work
    }))?);
    let mut analysis = Analysis::new(source, parsed, options);
    analysis.constants();
    analysis.unused();
    flow::analyze(&mut analysis);
    expressions::finish(&mut analysis);
    analysis.findings.sort_by(|a, b| {
        (a.location.start, &a.kind, &a.id).cmp(&(b.location.start, &b.kind, &b.id))
    });
    analysis.ranges.sort_by_key(|r| r.location.start);
    let incomplete_searches = analysis
        .expressions
        .iter()
        .filter(|s| s.comparison.as_ref().is_some_and(|c| !c.complete))
        .count();
    Ok(AdviceReport {
        format_version: 2,
        advisory_only: true,
        language_details: None,
        source_sha256: sha256(source.as_bytes()),
        analysis_context_sha256: context,
        frontend: frontend.info.clone(),
        statistics: json!({
            "ast_nodes": analysis.nodes.len(),
            "functions_analyzed": analysis.functions_analyzed,
            "functions_withheld": analysis.functions_withheld,
            "findings_emitted": analysis.findings.len(),
            "findings_omitted": analysis.findings_omitted,
            "range_sites_emitted": analysis.ranges.len(),
            "range_sites_omitted": analysis.ranges_omitted,
            "expression_sites_emitted": analysis.expressions.len(),
            "expression_sites_omitted": analysis.expressions_omitted,
            "nversion_work_budget": options.max_nversion_work,
            "nversion_scalar_evaluations": analysis.nversion_work,
            "nversion_searches_incomplete": incomplete_searches,
            "finite_flow_work_budget": options.max_finite_flow_work,
            "finite_flow_reserved_work": analysis.finite_flow_work.get(),
            "finite_flow_budget_exhausted": analysis.finite_flow_exhausted.get(),
            "frontend_work": frontend.statistics(),
            "source_modified": false,
            "compression_candidates_created": 0,
            "final_file_bytes_measured": false
        }),
        findings: analysis.findings,
        ranges: analysis.ranges,
        expressions: analysis.expressions,
        limitations: analysis.notes.into_iter().collect(),
        complete: analysis.findings_omitted == 0
            && analysis.ranges_omitted == 0
            && analysis.expressions_omitted == 0
            && !analysis.finite_flow_exhausted.get()
            && incomplete_searches == 0,
    })
}

struct Node {
    value: Value,
    children: Vec<usize>,
    slots: Vec<Option<usize>>,
    parent: Option<usize>,
}

struct Analysis<'a> {
    source: &'a str,
    line_starts: Vec<usize>,
    main_path: String,
    nodes: Vec<Node>,
    declarations: HashMap<String, usize>,
    function_of: Vec<Option<usize>>,
    findings: Vec<Finding>,
    ranges: Vec<RangeSite>,
    expressions: Vec<ExpressionSite>,
    expression_domains: HashMap<String, domain::Domain>,
    expression_ids: HashMap<String, usize>,
    finding_ids: HashSet<String>,
    range_ids: HashMap<String, usize>,
    notes: BTreeSet<String>,
    options: &'a AdvisorOptions,
    functions_analyzed: usize,
    functions_withheld: usize,
    findings_omitted: usize,
    ranges_omitted: usize,
    expressions_omitted: usize,
    nversion_work: usize,
    finite_flow_work: Cell<usize>,
    finite_flow_exhausted: Cell<bool>,
}

fn flatten(mut value: Value, parent: Option<usize>, nodes: &mut Vec<Node>) -> usize {
    let children = value
        .as_object_mut()
        .and_then(|m| m.remove("inner"))
        .and_then(|v| match v {
            Value::Array(a) => Some(a),
            _ => None,
        })
        .unwrap_or_default();
    let id = nodes.len();
    nodes.push(Node {
        value,
        children: vec![],
        slots: vec![],
        parent,
    });
    for child in children {
        if child.get("kind").and_then(Value::as_str).is_some() {
            let c = flatten(child, Some(id), nodes);
            nodes[id].children.push(c);
            nodes[id].slots.push(Some(c));
        } else {
            nodes[id].slots.push(None);
        }
    }
    id
}

impl<'a> Analysis<'a> {
    fn new(source: &'a str, parsed: ParsedSource, options: &'a AdvisorOptions) -> Self {
        let mut nodes = vec![];
        flatten(parsed.tree, None, &mut nodes);
        let mut result = Self {
            source,
            line_starts: std::iter::once(0).chain(source.bytes().enumerate().filter_map(|(i, b)| (b == b'\n').then_some(i+1))).collect(),
            main_path: parsed.main_path,
            function_of: vec![None; nodes.len()],
            nodes,
            declarations: HashMap::new(),
            findings: vec![],
            ranges: vec![],
            expressions: vec![],
            expression_domains: HashMap::new(),
            expression_ids: HashMap::new(),
            finding_ids: HashSet::new(),
            range_ids: HashMap::new(),
            notes: BTreeSet::from([
                "Advice never edits source, enters compression search, or certifies a replacement. Recompile and measure the entire final file after manual review.".into(),
                "Ranges describe supported, defined C executions at individual read sites in this translation unit. Samples and whole-program facts are separate evidence.".into(),
                "Plain char, short, enum, __int128, floating point, memory objects and interprocedural relations have no range model; unsupported operations widen or withhold facts.".into(),
                "Constant reuse and no-reference diagnostics require scope/linkage/initializer review. Equal mathematical values with different C types remain separate groups.".into(),
            ]),
            options,
            functions_analyzed: 0,
            functions_withheld: 0,
            findings_omitted: 0,
            ranges_omitted: 0,
            expressions_omitted: 0,
            nversion_work: 0,
            finite_flow_work: Cell::new(0),
            finite_flow_exhausted: Cell::new(false),
        };
        for n in 0..result.nodes.len() {
            if result.kind(n).ends_with("Decl") {
                if let Some(id) = result.nodes[n].value["id"].as_str() {
                    result.declarations.insert(id.to_owned(), n);
                }
            }
            result.function_of[n] = if result.kind(n) == "FunctionDecl" {
                Some(n)
            } else {
                result.nodes[n].parent.and_then(|p| result.function_of[p])
            };
        }
        result
    }

    fn kind(&self, n: usize) -> &str {
        self.nodes[n].value["kind"].as_str().unwrap_or("")
    }
    fn name(&self, n: usize) -> &str {
        self.nodes[n].value["name"].as_str().unwrap_or("")
    }
    fn op(&self, n: usize) -> &str {
        self.nodes[n].value["opcode"].as_str().unwrap_or("")
    }
    fn typ(&self, n: usize) -> &str {
        let t = &self.nodes[n].value["type"];
        let t = t["desugaredQualType"]
            .as_str()
            .or_else(|| t["qualType"].as_str())
            .unwrap_or("");
        if t == "bool" {
            "_Bool"
        } else {
            t
        }
    }
    fn location(&self, n: usize) -> Option<SourceLocation> {
        let begin = &self.nodes[n].value["range"]["begin"];
        let end = &self.nodes[n].value["range"]["end"];
        for p in [begin, end, &self.nodes[n].value["loc"]] {
            if ["spellingLoc", "expansionLoc", "includedFrom"]
                .iter()
                .any(|k| p.get(k).is_some())
                || p["file"].as_str().is_some_and(|s| s != self.main_path)
            {
                return None;
            }
        }
        let a = begin["offset"].as_u64()? as usize;
        let b = (end["offset"].as_u64()? as usize).checked_add(end["tokLen"].as_u64()? as usize)?;
        if a >= b
            || b > self.source.len()
            || !self.source.is_char_boundary(a)
            || !self.source.is_char_boundary(b)
        {
            return None;
        }
        // Included AST children sometimes omit inherited file fields. The
        // nearest declaration's explicit location still establishes ownership.
        let mut parent = self.nodes[n].parent;
        while let Some(p) = parent {
            let loc = &self.nodes[p].value["loc"];
            if loc.get("includedFrom").is_some()
                || loc["file"].as_str().is_some_and(|s| s != self.main_path)
            {
                return None;
            }
            parent = self.nodes[p].parent;
        }
        let line = self.line_starts.partition_point(|&start| start <= a) - 1;
        Some(SourceLocation {
            start: a,
            end: b,
            line: line + 1,
            column: a - self.line_starts[line] + 1,
        })
    }
    fn text(&self, n: usize) -> String {
        self.location(n)
            .map(|l| self.source[l.start..l.end].to_owned())
            .unwrap_or_default()
    }
    fn function_name(&self, n: usize) -> Option<String> {
        self.function_of[n].map(|f| self.name(f).to_owned())
    }
    fn emit(&mut self, finding: Finding) {
        if !self.finding_ids.insert(finding.id.clone()) {
            return;
        }
        if self.findings.len() >= self.options.max_findings {
            self.findings_omitted += 1;
        } else {
            self.findings.push(finding);
        }
    }
    fn finding(
        &self,
        n: usize,
        kind: &str,
        assurance: &str,
        message: String,
        suggestion: Option<String>,
    ) -> Option<Finding> {
        let location = self.location(n)?;
        let original = self.source[location.start..location.end].to_owned();
        let saved = suggestion
            .as_ref()
            .map(|s| original.len() as isize - s.len() as isize);
        Some(Finding {
            id: format!("{kind}:{}:{}", location.start, location.end),
            kind: kind.into(),
            assurance: assurance.into(),
            location,
            function: self.function_name(n),
            symbol: None,
            message,
            suggestion,
            original,
            related_locations: vec![],
            requirements: vec![],
            estimated_source_bytes_saved: saved,
        })
    }
    fn descendants(&self, root: usize) -> Vec<usize> {
        let mut stack = vec![root];
        let mut out = vec![];
        while let Some(n) = stack.pop() {
            out.push(n);
            stack.extend(self.nodes[n].children.iter().rev());
        }
        out
    }
    fn literal_key(&self, n: usize) -> Option<(String, String)> {
        if self.kind(n) != "IntegerLiteral" || self.location(n).is_none() {
            return None;
        }
        Some((
            self.typ(n).to_owned(),
            self.nodes[n].value["value"].as_str()?.to_owned(),
        ))
    }

    fn constants(&mut self) {
        let mut groups: BTreeMap<(String, String), BTreeMap<usize, usize>> = BTreeMap::new();
        for n in 0..self.nodes.len() {
            if let Some(key) = self.literal_key(n) {
                // Tiny literals are not useful magic-number diagnostics.
                if self.text(n).len() >= 4 {
                    groups
                        .entry(key)
                        .or_default()
                        .insert(self.location(n).unwrap().start, n);
                }
            }
        }
        for ((typ, value), sites) in groups {
            if sites.len() < 2 {
                continue;
            }
            let sites: Vec<_> = sites.into_values().collect();
            let mut aliases = BTreeSet::new();
            for &n in &sites {
                let mut p = self.nodes[n].parent;
                while let Some(i) = p {
                    if self.kind(i) == "VarDecl" {
                        if self.typ(i).starts_with("const ") && !self.name(i).is_empty() {
                            aliases.insert(self.name(i).to_owned());
                        }
                        break;
                    }
                    if !matches!(self.kind(i), "ImplicitCastExpr" | "ParenExpr") {
                        break;
                    }
                    p = self.nodes[i].parent;
                }
            }
            let alias_note = if aliases.is_empty() {
                String::new()
            } else {
                format!(" Existing named constant candidates: {} (visibility and exact declaration type must be reviewed).", aliases.into_iter().collect::<Vec<_>>().join(", "))
            };
            if let Some(mut finding) = self.finding(sites[0], "duplicate-constant", "typed-ast-observation",
                format!("{} direct source occurrences have value {value} and Clang type {typ}.{alias_note}", sites.len()),
                Some("Consider one scope-valid typed alias or a literal macro; compare the complete final file after choosing the spelling.".into())) {
                finding.related_locations = sites.iter().skip(1).filter_map(|&n| self.location(n)).collect();
                finding.estimated_source_bytes_saved = None;
                finding.requirements = vec![
                    "Preserve each use's exact C type, integer-constant-expression requirements, macro/stringification behavior and binding.".into(),
                    "A C const object is not generally an integer constant expression; an enum may change type or fail for large values.".into(),
                    "Repeated bytes may already compress well; no compressed or native-size saving is inferred.".into(),
                ];
                self.emit(finding);
            }
        }
    }

    fn unused(&mut self) {
        let mut referenced = HashSet::new();
        let mut uses: HashMap<String, Vec<usize>> = HashMap::new();
        for (index, n) in self.nodes.iter().enumerate() {
            if let Some(id) = n.value["referencedDecl"]["id"].as_str() {
                referenced.insert(id.to_owned());
                uses.entry(id.to_owned()).or_default().push(index);
            }
        }
        for n in 0..self.nodes.len() {
            let kind = self.kind(n);
            if !matches!(kind, "VarDecl" | "ParmVarDecl" | "FunctionDecl")
                || self.name(n).is_empty()
                || self.location(n).is_none()
            {
                continue;
            }
            if kind == "FunctionDecl"
                && (!self.nodes[n]
                    .children
                    .iter()
                    .any(|&c| self.kind(c) == "CompoundStmt")
                    || self.name(n) == "main")
            {
                continue;
            }
            if kind == "ParmVarDecl"
                && !self.function_of[n].is_some_and(|f| {
                    self.nodes[f]
                        .children
                        .iter()
                        .any(|&c| self.kind(c) == "CompoundStmt")
                })
            {
                continue;
            }
            let Some(id) = self.nodes[n].value["id"].as_str() else {
                continue;
            };
            if kind == "VarDecl"
                && self.function_of[n].is_some()
                && !matches!(
                    self.nodes[n].value["storageClass"].as_str(),
                    Some("static" | "extern")
                )
                && matches!(
                    self.typ(n),
                    "_Bool"
                        | "int"
                        | "unsigned int"
                        | "long"
                        | "unsigned long"
                        | "long long"
                        | "unsigned long long"
                )
                && uses.get(id).is_some_and(|sites| {
                    !sites.is_empty()
                        && sites.iter().all(|&site| {
                            let mut child = site;
                            while self.nodes[child]
                                .parent
                                .is_some_and(|p| self.kind(p) == "ParenExpr")
                            {
                                child = self.nodes[child].parent.unwrap();
                            }
                            self.nodes[child].parent.is_some_and(|p| {
                                self.kind(p) == "BinaryOperator"
                                    && self.op(p) == "="
                                    && self.nodes[p].children.first() == Some(&child)
                            })
                        })
                })
            {
                if let Some(mut finding) = self.finding(n, "write-only-local", "translation-unit-observation",
                    format!("All AST references to automatic local {} are simple assignment destinations; no value read or address use was found.", self.name(n)), None) {
                    finding.symbol = Some(self.name(n).to_owned());
                    finding.requirements = vec![
                        "Preserve initializer and assignment RHS side effects, assignment-expression results, evaluation order, cleanup and scope lifetime; no deletion is applied.".into(),
                        "This is not dead-store or whole-program liveness proof; inspect generated/assembly uses and the complete function before removing storage.".into(),
                    ];
                    self.emit(finding);
                }
                continue;
            }
            if referenced.contains(id)
                || self.nodes[n].value["isUsed"].as_bool() == Some(true)
                || self.nodes[n].value["isReferenced"].as_bool() == Some(true)
            {
                continue;
            }
            // Explicit retention/entry attributes are a known external use.
            if self.nodes[n].children.iter().any(|&c| {
                matches!(
                    self.kind(c),
                    "UsedAttr"
                        | "RetainAttr"
                        | "ConstructorAttr"
                        | "DestructorAttr"
                        | "AliasAttr"
                        | "WeakRefAttr"
                )
            }) {
                continue;
            }
            let storage = self.nodes[n].value["storageClass"].as_str().unwrap_or("");
            let external = kind == "FunctionDecl" && storage != "static"
                || kind == "VarDecl" && self.function_of[n].is_none() && storage != "static"
                || storage == "extern";
            let label = match kind {
                "FunctionDecl" => "function",
                "ParmVarDecl" => "parameter",
                _ => "variable",
            };
            let scope = if external {
                "in this translation unit; external callers/linker use remain unknown"
            } else {
                "in the parsed translation unit"
            };
            if let Some(mut finding) = self.finding(
                n,
                "no-reference",
                "translation-unit-observation",
                format!(
                    "No AST reference to {label} {} was found {scope}.",
                    self.name(n)
                ),
                None,
            ) {
                finding.symbol = Some(self.name(n).to_owned());
                finding.requirements = vec![
                    "Check linker/export/assembly uses, ABI and generated callers before removing a declaration.".into(),
                    "Preserve initializer side effects, cleanup/lifetime effects and any parameter/calling convention contract.".into(),
                ];
                self.emit(finding);
            }
        }
    }
}

#[cfg(test)]
mod tests;
