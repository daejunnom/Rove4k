//! Closed-translation-unit cleanup candidates, separate from read-only advice.
//!
//! Removing a declaration requires a declaration-identity reachability proof
//! and a fresh comparison of the surviving typed program. Removing an include
//! requires identical expanded compiler tokens, including emitted pragmas.
//! Neither proof ranks source length nor replaces the actual compiler/native,
//! diagnostic and complete-file-cost gates in source search.
use crate::c_frontend::{FrontendConfig, FrontendOutputLimit, FrontendSession, ParsedSource};
use crate::cflow::CFlowOptions;
use crate::notation::{lex, Token, Variant, MAX_SOURCE};
use crate::sha256;
use anyhow::{ensure, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, HashMap, HashSet};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct CleanupOptions {
    pub language: String,
    pub frontend: CFlowOptions,
    pub includes: bool,
    pub functions: bool,
    /// Bounds proof attempts as well as emitted alternatives. The original
    /// source is retained independently and is never charged as a candidate.
    pub max_candidates: usize,
}

impl Default for CleanupOptions {
    fn default() -> Self {
        Self {
            language: "c".into(),
            frontend: CFlowOptions::default(),
            includes: true,
            functions: true,
            max_candidates: 64,
        }
    }
}

impl CleanupOptions {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            (1..=128).contains(&self.max_candidates),
            "cleanup max_candidates must be 1..128"
        );
        ensure!(
            matches!(
                self.frontend.token_contract.as_str(),
                "opaque" | "no-token-observation" | "preprocessed"
            ),
            "unsupported cleanup token contract"
        );
        FrontendConfig::from(&self.frontend).validate_cleanup(&self.language)
    }
}

#[derive(Clone)]
struct Edit {
    start: usize,
    end: usize,
    rule: &'static str,
    declaration_ids: Vec<String>,
}

fn contract(options: &CleanupOptions) -> Value {
    json!({"language":options.language,"standard":options.frontend.standard,
        "token_contract":options.frontend.token_contract,
        "scope":"literal includes with identical expanded compiler tokens; unreferenced ordinary top-level static free functions with compiler-use roots and surviving typed AST equality",
        "reference_policy":"Clang isUsed/isReferenced declarations are roots even when JSON omits their bindings; referenced dead SCCs require a more complete frontend and are retained",
        "unsupported":"Rust/Python; C++ methods/namespaces/templates/dependent lookup; macro declarations; attributed declarations; assembly/alias string references",
        "acceptance":"candidate only; actual compiler diagnostics and native identity plus complete-file cost remain separate gates",
        "advisor":"read-only advisor is not a source of deletion permission"})
}

fn blocked(source: &[u8], options: &CleanupOptions) -> Option<&'static str> {
    if options.frontend.token_contract == "opaque" {
        Some("source/token/location non-observation was not declared")
    } else if !source.is_ascii()
        || source.contains(&0)
        || source.contains(&b'$')
        || source.windows(2).any(|w| w == b"\\\n" || w == b"??")
        || source.windows(3).any(|w| w == b"\\\r\n")
        || source.windows(2).any(|w| w == b"\\u" || w == b"\\U")
    {
        Some("unsupported source encoding, extended identifier or preprocessing splice")
    } else {
        None
    }
}

pub fn generate_variants(source: &[u8], options: &CleanupOptions) -> Result<Vec<Variant>> {
    options.validate()?;
    ensure!(source.len() <= MAX_SOURCE, "cleanup source exceeds 8 MiB");
    if let Some(reason) = blocked(source, options) {
        return Ok(vec![Variant::new(
            "raw",
            source,
            source.to_vec(),
            vec![],
            vec![reason.into()],
            contract(options),
        )]);
    }
    let frontend = FrontendSession::new_for_cleanup((&options.frontend).into(), &options.language)?;
    let snapshot = frontend.parse(source, true)?;
    generate_variants_with_snapshot(source, options, &frontend, &snapshot)
}

/// The source-search owner lends its immutable AST and process context. No
/// second frontend, cost cache or weakened spelling verifier is introduced.
pub(crate) fn generate_variants_with_snapshot(
    source: &[u8],
    options: &CleanupOptions,
    frontend: &FrontendSession,
    snapshot: &ParsedSource,
) -> Result<Vec<Variant>> {
    options.validate()?;
    ensure!(source.len() <= MAX_SOURCE, "cleanup source exceeds 8 MiB");
    ensure!(
        frontend.matches(&FrontendConfig::from(&options.frontend)),
        "cleanup frontend configuration differs from its snapshot"
    );
    let mut variants = vec![Variant::new(
        "raw",
        source,
        source.to_vec(),
        vec![],
        vec![],
        contract(options),
    )];
    if let Some(reason) = blocked(source, options) {
        variants[0].notes.push(reason.into());
        return Ok(variants);
    }
    frontend.recheck(source, snapshot)?;
    // These nodes omit their evaluated value in Clang JSON. Erasing physical
    // AST locations or preprocessing line markers would erase an observable
    // input, including default arguments and std::source_location. The
    // caller's non-observation declaration cannot prove these nodes harmless.
    fn location_observer(node: &Value) -> bool {
        node["kind"] == "SourceLocExpr" || children(node).any(location_observer)
    }
    if location_observer(&snapshot.tree) {
        variants[0].notes.push("source-location builtins/default arguments need a location-sensitive proof; both cleanup passes are unsupported for this translation unit".into());
        variants[0].contract["generation"] =
            json!({"checks":0,"status":"unsupported-source-location-observation"});
        return Ok(variants);
    }
    let tokens = lex(std::str::from_utf8(source)?, &options.language)?;
    // C++'s preflight and include proof share one expanded observation. Looking
    // only at source spelling would miss constructs introduced by macros or
    // headers, including type-only dependencies absent from Clang's JSON.
    let has_includes = options.includes && tokens.iter().any(literal_include);
    let expanded = if has_includes || options.functions && options.language == "cpp" {
        Some(observe(frontend, source, snapshot, || {
            expanded_tokens(frontend, source, &options.language)
        })?)
    } else {
        None
    };
    let mut attempts = Vec::new();
    let mut checks = 0;
    let mut bytes = source.len();
    let mut seen = HashSet::from([sha256(source)]);
    let mut function_edits = Vec::new();
    if options.functions {
        match unreachable_functions(
            source,
            snapshot,
            &tokens,
            &options.language,
            expanded.as_deref(),
        ) {
            Ok(edits) => function_edits = edits,
            Err(reason) => attempts.push(
                json!({"rule":"unreachable-functions","status":"unsupported","reason":reason}),
            ),
        }
    }
    if !function_edits.is_empty() && checks < options.max_candidates {
        checks += 1;
        let data = apply(source, &function_edits)?;
        let removed: HashSet<_> = function_edits
            .iter()
            .flat_map(|e| e.declaration_ids.iter().cloned())
            .collect();
        let expected = surviving_signature(&snapshot.tree, &removed);
        let proof = observe(frontend, source, snapshot, || {
            let changed = frontend.parse(&data, false)?;
            ensure!(
                expected == surviving_signature(&changed.tree, &HashSet::new()),
                "surviving typed program or declaration bindings changed"
            );
            Ok(
                json!({"kind":"compiler-use-roots-declaration-graph-and-surviving-typed-ast", "surviving_typed_ast":"equal", "replay":"recompute compiler-use roots, graph and exact in-session AST comparison"}),
            )
        });
        record_candidate(
            source,
            data,
            &function_edits,
            "cleanup-functions",
            proof,
            &mut variants,
            &mut attempts,
            &mut seen,
            &mut bytes,
            options,
        )?;
    }
    if has_includes && checks < options.max_candidates {
        let baseline = expanded
            .as_ref()
            .context("include proof lacks expanded compiler input")?;
        let mut safe_includes = Vec::new();
        for token in tokens.iter().filter(|t| literal_include(t)) {
            if checks == options.max_candidates {
                break;
            }
            checks += 1;
            let edit = Edit {
                start: token.start,
                end: token.end,
                rule: "unused-include",
                declaration_ids: vec![],
            };
            let data = apply(source, std::slice::from_ref(&edit))?;
            let proof = observe(frontend, source, snapshot, || {
                ensure!(
                    expanded_tokens(frontend, &data, &options.language)?.as_slice()
                        == baseline.as_slice(),
                    "expanded compiler tokens or pragmas changed"
                );
                Ok(
                    json!({"kind":"identical-expanded-compiler-tokens", "expanded_token_count":baseline.len(), "replay":"recompute exact in-session expanded tokens"}),
                )
            });
            let id = format!("cleanup-include-{}", token.start);
            if record_candidate(
                source,
                data,
                std::slice::from_ref(&edit),
                &id,
                proof,
                &mut variants,
                &mut attempts,
                &mut seen,
                &mut bytes,
                options,
            )? {
                safe_includes.push(edit);
            }
        }
        // Individually redundant headers need not be jointly redundant. The
        // union is freshly preprocessed rather than assuming composability.
        if safe_includes.len() > 1 && checks < options.max_candidates {
            checks += 1;
            let data = apply(source, &safe_includes)?;
            let proof = observe(frontend, source, snapshot, || {
                ensure!(
                    expanded_tokens(frontend, &data, &options.language)?.as_slice()
                        == baseline.as_slice(),
                    "combined include removal changes expanded compiler tokens or pragmas"
                );
                Ok(
                    json!({"kind":"identical-expanded-compiler-tokens", "expanded_token_count":baseline.len(), "replay":"recompute exact in-session expanded tokens"}),
                )
            });
            record_candidate(
                source,
                data,
                &safe_includes,
                "cleanup-includes",
                proof,
                &mut variants,
                &mut attempts,
                &mut seen,
                &mut bytes,
                options,
            )?;
        }
    }
    frontend.recheck(source, snapshot)?;
    variants[0].contract["generation"] = json!({"checks":checks,"max_checks":options.max_candidates,
        "checks_limit_reached":checks == options.max_candidates,"attempts":attempts,
        "retained_source_bytes":bytes,"retained_source_limit":64 << 20,
        "composition":"compiler-unreferenced functions and individual/proven-union includes; fresh search rounds reanalyze dependencies after removal"});
    variants[0].contract["frontend_work"] = frontend.statistics();
    Ok(variants)
}

/// A failing candidate must never hide a change to the original dependency
/// context. This uses the same process owner/recheck boundary as spelling.
fn observe<T>(
    frontend: &FrontendSession,
    source: &[u8],
    snapshot: &ParsedSource,
    operation: impl FnOnce() -> Result<T>,
) -> Result<T> {
    frontend.recheck(source, snapshot)?;
    let result = operation();
    match (frontend.recheck(source, snapshot), result) {
        (Ok(()), result) => result,
        (Err(context), Ok(_)) => Err(context),
        (Err(context), Err(operation)) => {
            Err(context.context(format!("cleanup operation also failed: {operation:#}")))
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn record_candidate(
    source: &[u8],
    data: Vec<u8>,
    edits: &[Edit],
    id: &str,
    proof: Result<Value>,
    variants: &mut Vec<Variant>,
    attempts: &mut Vec<Value>,
    seen: &mut HashSet<String>,
    bytes: &mut usize,
    options: &CleanupOptions,
) -> Result<bool> {
    let reconstruction: Vec<_> = edits
        .iter()
        .map(|e| json!({"start":e.start,"end":e.end,"after":"\n","rule":e.rule}))
        .collect();
    let proof = match proof {
        Ok(proof) => proof,
        Err(error) => {
            if error
                .downcast_ref::<crate::c_frontend::FrontendContextChanged>()
                .is_some()
                || error.downcast_ref::<FrontendOutputLimit>().is_some()
            {
                return Err(error);
            }
            attempts.push(json!({"id":id,"status":"proof-rejected","reason":format!("{error:#}"),
                "input_source_sha256":sha256(source),"source_sha256":sha256(&data),"edits":reconstruction}));
            return Ok(false);
        }
    };
    if !seen.insert(sha256(&data)) {
        return Ok(true);
    }
    if data.len() > (64usize << 20).saturating_sub(*bytes) {
        attempts.push(
            json!({"id":id,"status":"retention-budget","source_sha256":sha256(&data),
            "input_source_sha256":sha256(source),"edits":reconstruction}),
        );
        return Ok(false);
    }
    let audit = edits
        .iter()
        .map(|edit| {
            json!({"start":edit.start,"end":edit.end,
        "before":std::str::from_utf8(&source[edit.start..edit.end]).unwrap(),"after":"\n",
        "rule":edit.rule,"proof":proof})
        })
        .collect();
    *bytes += data.len();
    variants.push(Variant::new(
        id,
        source,
        data,
        audit,
        vec![],
        contract(options),
    ));
    attempts.push(json!({"id":id,"status":"source-proof-passed","proof":proof}));
    Ok(true)
}

fn apply(source: &[u8], edits: &[Edit]) -> Result<Vec<u8>> {
    let mut edits: Vec<_> = edits.iter().collect();
    edits.sort_by_key(|e| e.start);
    let mut output = Vec::with_capacity(source.len());
    let mut end = 0;
    for edit in edits {
        ensure!(
            end <= edit.start && edit.start < edit.end && edit.end <= source.len(),
            "cleanup ranges overlap or exceed input"
        );
        output.extend_from_slice(&source[end..edit.start]);
        // Do not join surviving tokens, or move a following directive into
        // preceding code. A single newline also preserves directive boundaries.
        output.push(b'\n');
        end = edit.end;
    }
    output.extend_from_slice(&source[end..]);
    Ok(output)
}

fn literal_include(token: &Token) -> bool {
    if token.kind != "directive" {
        return false;
    }
    let text = token.text.trim();
    let Some(rest) = text
        .strip_prefix('#')
        .map(str::trim_start)
        .and_then(|s| s.strip_prefix("include"))
    else {
        return false;
    };
    let rest = rest.trim();
    if let Some(rest) = rest.strip_prefix('<') {
        rest.find('>')
            .is_some_and(|end| rest[end + 1..].trim().is_empty())
    } else if let Some(rest) = rest.strip_prefix('"') {
        rest.find('"')
            .is_some_and(|end| rest[end + 1..].trim().is_empty())
    } else {
        false
    }
}

fn expanded_tokens(
    frontend: &FrontendSession,
    source: &[u8],
    language: &str,
) -> Result<Vec<(String, String)>> {
    let bytes = frontend.expanded_source(source)?;
    let text = std::str::from_utf8(&bytes)
        .context("expanded source must be UTF-8 for cleanup token comparison")?;
    Ok(lex(text, language)?
        .into_iter()
        .filter(|t| !matches!(t.kind, "space" | "comment"))
        .map(|t| {
            (
                t.kind.into(),
                if t.kind == "directive" {
                    t.text.trim().into()
                } else {
                    t.text
                },
            )
        })
        .collect())
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

fn direct_offset(location: &Value, main_path: &str) -> Option<usize> {
    if location.get("spellingLoc").is_some()
        || location.get("expansionLoc").is_some()
        || location.get("includedFrom").is_some()
        || location
            .get("file")
            .and_then(Value::as_str)
            .is_some_and(|f| f != main_path)
    {
        return None;
    }
    location["offset"]
        .as_u64()
        .and_then(|v| usize::try_from(v).ok())
}

/// Only declarations represented directly at translation-unit scope are
/// removable. All other declarations, initializers, addresses and implicit
/// references are roots. String-named and dependent bindings fail closed.
fn unreachable_functions(
    source: &[u8],
    parsed: &ParsedSource,
    tokens: &[Token],
    language: &str,
    expanded: Option<&[(String, String)]>,
) -> std::result::Result<Vec<Edit>, String> {
    let mut all = Vec::new();
    walk(&parsed.tree, &mut all);
    if language == "cpp" {
        // Clang JSON is not a complete semantic graph for C++ compile-time and
        // type-only computation. In particular exception specifications can
        // contain an overload call only as qualType text, and CXXNoexceptExpr
        // omits its evaluated result. Require coverage before graph traversal;
        // reparsing an equally incomplete JSON tree is not a proof.
        let unsupported_tokens = expanded.is_none_or(|tokens| {
            tokens.iter().any(|(kind, text)| {
                kind == "identifier"
                    && matches!(
                        text.as_str(),
                        "noexcept"
                            | "throw"
                            | "decltype"
                            | "typeof"
                            | "__typeof"
                            | "__typeof__"
                            | "sizeof"
                            | "alignof"
                            | "__alignof"
                            | "__alignof__"
                            | "alignas"
                            | "typeid"
                            | "constexpr"
                            | "consteval"
                            | "constinit"
                            | "static_assert"
                            | "template"
                            | "requires"
                    )
            })
        });
        let unsupported_nodes = all.iter().any(|node| {
            node["kind"] == "ParmVarDecl" && node.get("init").is_some()
                || node["kind"].as_str().is_some_and(|kind| {
                    matches!(
                        kind,
                        "CXXNoexceptExpr"
                            | "TypeTraitExpr"
                            | "UnaryExprOrTypeTraitExpr"
                            | "DecltypeType"
                            | "TypeOfExprType"
                            | "RequiresExpr"
                            | "UserDefinedLiteral"
                    )
                })
        });
        if unsupported_tokens || unsupported_nodes {
            return Err("C++ compile-time/type-query/exception/default-argument constructs lack complete binding/value coverage in Clang JSON; function cleanup is unsupported for this translation unit".into());
        }
    }
    if all.iter().any(|n| {
        matches!(
            n["kind"].as_str(),
            Some(
                "FileScopeAsmDecl"
                    | "GCCAsmStmt"
                    | "MSAsmStmt"
                    | "AsmLabelAttr"
                    | "AliasAttr"
                    | "IFuncAttr"
                    | "WeakRefAttr"
            )
        )
    }) {
        return Err(
            "assembly or string-named linkage references require a separate reachability model"
                .into(),
        );
    }
    if all.iter().any(|n| {
        n["kind"].as_str().is_some_and(|k| {
            k.contains("Template")
                || k.contains("Dependent")
                || k.contains("Unresolved")
                || matches!(
                    k,
                    "UsingDecl" | "UsingShadowDecl" | "UsingDirectiveDecl" | "ImportDecl"
                )
        })
    }) {
        return Err(
            "dependent/template/import/using bindings are outside the closed free-function subset"
                .into(),
        );
    }
    let functions: Vec<_> = all
        .iter()
        .copied()
        .filter(|n| n["kind"] == "FunctionDecl")
        .collect();
    if functions.len() > 4096 {
        return Err("function declaration graph exceeds the 4096-declaration proof budget".into());
    }
    let mut previous = HashMap::new();
    for n in &functions {
        if let (Some(id), Some(prev)) = (n["id"].as_str(), n["previousDecl"].as_str()) {
            previous.insert(id.to_owned(), prev.to_owned());
        }
    }
    let canonical = |id: &str| -> String {
        let mut id = id;
        for _ in 0..functions.len() {
            match previous.get(id) {
                Some(p) => id = p,
                None => break,
            }
        }
        id.to_owned()
    };
    let mut identities = HashMap::new();
    let mut groups: BTreeMap<String, Vec<&Value>> = BTreeMap::new();
    for n in &functions {
        if let Some(id) = n["id"].as_str() {
            let group = canonical(id);
            identities.insert(id.to_owned(), group.clone());
            groups.entry(group).or_default().push(n);
        }
    }
    let top: HashSet<_> = children(&parsed.tree)
        .filter_map(|n| n["id"].as_str())
        .collect();
    let mut candidates: BTreeMap<String, Vec<Edit>> = BTreeMap::new();
    for (group, declarations) in &groups {
        if !declarations
            .iter()
            .any(|n| children(n).any(|c| c["kind"] == "CompoundStmt"))
        {
            continue;
        }
        let mut edits = Vec::new();
        for n in declarations {
            let id = n["id"].as_str().unwrap();
            if !top.contains(id)
                || n["storageClass"] != "static"
                // Clang accepts static main as a C extension. Language entry
                // is a root even when the spelling requests internal linkage.
                || n["name"] == "main"
                || n["isImplicit"] == true
                || children(n).any(|c| c["kind"].as_str().is_some_and(|k| k.ends_with("Attr")))
            {
                edits.clear();
                break;
            }
            let range = &n["range"];
            let Some(start) = direct_offset(&range["begin"], &parsed.main_path) else {
                edits.clear();
                break;
            };
            let Some(last) = direct_offset(&range["end"], &parsed.main_path) else {
                edits.clear();
                break;
            };
            let Some(length) = range["end"]["tokLen"].as_u64() else {
                edits.clear();
                break;
            };
            let Some(mut end) = last.checked_add(length as usize) else {
                edits.clear();
                break;
            };
            if direct_offset(&n["loc"], &parsed.main_path).is_none()
                || start >= end
                || end > source.len()
            {
                edits.clear();
                break;
            }
            let definition = children(n).any(|c| c["kind"] == "CompoundStmt");
            if !definition {
                let next = tokens
                    .iter()
                    .find(|t| t.start >= end && !matches!(t.kind, "space" | "comment"));
                match next {
                    Some(t) if t.text == ";" => end = t.end,
                    _ => {
                        edits.clear();
                        break;
                    }
                }
            }
            if tokens
                .iter()
                .any(|t| t.start >= start && t.start < end && t.kind == "directive")
            {
                edits.clear();
                break;
            }
            edits.push(Edit {
                start,
                end,
                rule: "unreachable-static-function",
                declaration_ids: vec![id.to_owned()],
            });
        }
        if edits.len() == declarations.len() {
            candidates.insert(group.clone(), edits);
        }
    }
    // Any shared declarator range is indivisible, even when both declarations
    // appear dead. Removing one would delete a different declaration's tokens.
    let spans: Vec<_> = candidates
        .iter()
        .flat_map(|(g, es)| es.iter().map(move |e| (g.clone(), e.start, e.end)))
        .collect();
    let mut overlapping = HashSet::new();
    for (i, (a, start, end)) in spans.iter().enumerate() {
        for (b, other_start, other_end) in &spans[..i] {
            if start < other_end && other_start < end {
                overlapping.insert(a.clone());
                overlapping.insert(b.clone());
            }
        }
    }
    candidates.retain(|group, _| !overlapping.contains(group));
    fn references(
        node: &Value,
        identities: &HashMap<String, String>,
        output: &mut HashSet<String>,
    ) {
        match node {
            Value::String(id) => {
                if let Some(group) = identities.get(id) {
                    output.insert(group.clone());
                }
            }
            Value::Array(array) => {
                for child in array {
                    references(child, identities, output);
                }
            }
            Value::Object(object) => {
                for value in object.values() {
                    references(value, identities, output);
                }
            }
            _ => {}
        }
    }
    // JSON omits some genuine bindings (C parameter/VLA bounds, C++ exception
    // specifications and type-only expressions). Clang's semantic-use flags
    // therefore contribute roots independently of the visible graph. This is
    // declaration evidence, never a count of identifier spellings. A referenced
    // dead cycle is deliberately retained until a frontend can prove *all* of
    // its incoming edges; ordinary dead call chains can shrink across rounds.
    let mut roots: HashSet<String> = functions
        .iter()
        .filter(|node| node["isUsed"] == true || node["isReferenced"] == true)
        .filter_map(|node| {
            node["id"]
                .as_str()
                .and_then(|id| identities.get(id))
                .cloned()
        })
        .collect();
    let mut edges: HashMap<String, HashSet<String>> = HashMap::new();
    for node in children(&parsed.tree) {
        let group = node["id"].as_str().and_then(|id| identities.get(id));
        if let Some(group) = group.filter(|g| candidates.contains_key(*g)) {
            references(node, &identities, edges.entry(group.clone()).or_default());
        } else {
            references(node, &identities, &mut roots);
        }
    }
    let mut queue: Vec<_> = roots.iter().cloned().collect();
    while let Some(group) = queue.pop() {
        if let Some(next) = edges.get(&group) {
            for group in next {
                if roots.insert(group.clone()) {
                    queue.push(group.clone());
                }
            }
        }
    }
    let mut edits: Vec<_> = candidates
        .into_iter()
        .filter(|(group, _)| !roots.contains(group))
        .flat_map(|(_, edits)| edits)
        .collect();
    edits.sort_by_key(|e| e.start);
    Ok(edits)
}

/// Exact surviving AST comparison, except physical locations, allocation IDs
/// and Clang's inferred used/reference flags. No names, types, conversions,
/// values, attributes or declaration-reference relationships are erased.
fn surviving_signature(tree: &Value, removed: &HashSet<String>) -> Value {
    fn normalize(
        node: &Value,
        key: &str,
        removed: &HashSet<String>,
        ids: &mut HashMap<String, usize>,
    ) -> Value {
        match node {
            Value::Object(object) => {
                let mut result = Map::new();
                for (key, value) in object {
                    if matches!(key.as_str(), "loc" | "range" | "isUsed" | "isReferenced") {
                        continue;
                    }
                    result.insert(key.clone(), normalize(value, key, removed, ids));
                }
                Value::Object(result)
            }
            Value::Array(array) => Value::Array(
                array
                    .iter()
                    .filter(|n| {
                        !(key == "inner"
                            && n["kind"] == "FunctionDecl"
                            && n["id"].as_str().is_some_and(|id| removed.contains(id)))
                    })
                    .map(|n| normalize(n, key, removed, ids))
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
                json!(*ids.entry(id.clone()).or_insert(next))
            }
            other => other.clone(),
        }
    }
    normalize(tree, "", removed, &mut HashMap::new())
}

/// Replay always recomputes the original graph/token proof. Audit offsets and
/// hashes alone are evidence identifiers, never permission to delete code.
pub fn replay_variant(
    source: &[u8],
    recorded: &Variant,
    options: &CleanupOptions,
) -> Result<Variant> {
    let selected = generate_variants(source, options)?
        .into_iter()
        .find(|v| v.id == recorded.id)
        .context("recorded cleanup candidate is no longer available")?;
    ensure!(
        selected.sha256 == recorded.sha256
            && selected.bytes == recorded.bytes
            && selected.audit == recorded.audit,
        "recorded cleanup derivation changed"
    );
    Ok(selected)
}
