//! C++ advisory boundary over the common, defined LP64 integer subset.
//!
//! Clang parses real C++ and owns bindings/conversions. The C evaluator is only
//! a numeric carrier: this module separately checks C++ type and value category
//! at every lowered node and again for every retained candidate. No C++ profile,
//! source rewrite or compression candidate is produced.
use super::{
    domain::FINITE_LIMIT,
    expressions::{self, Lowered},
    flow,
    nversion::{
        self, BinaryOp, CIntType, DomainProvenance, Expr, FiniteDomain, SearchBudget,
        SearchRequest, UnaryOp,
    },
    AdviceReport, AdvisorOptions, Analysis, Finding,
};
use crate::c_frontend::{FrontendConfig, FrontendSession};
use crate::sha256;
use anyhow::{ensure, Result};
use serde::Serialize;
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet, HashSet};

pub(super) fn is_cpp(a: &Analysis<'_>) -> bool {
    cpp_standard(&a.options.standard)
}

fn cpp_standard(standard: &str) -> bool {
    matches!(standard, "c++17" | "c++20" | "gnu++17" | "gnu++20")
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum ScalarType {
    Bool,
    Integer(CIntType),
}

impl ScalarType {
    fn parse(spelling: &str) -> Option<Self> {
        if spelling == "bool" {
            Some(Self::Bool)
        } else {
            CIntType::from_c_spelling(spelling).map(Self::Integer)
        }
    }

    fn name(self) -> &'static str {
        match self {
            Self::Bool => "bool",
            Self::Integer(t) => t.c_name(),
        }
    }

    fn promoted(self) -> CIntType {
        match self {
            Self::Bool => CIntType::I32,
            Self::Integer(t) => t,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
enum Category {
    Lvalue,
    Prvalue,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Surface {
    ty: ScalarType,
    category: Category,
}

impl Surface {
    fn prvalue(ty: ScalarType) -> Self {
        Self {
            ty,
            category: Category::Prvalue,
        }
    }
}

fn raw_type<'a>(a: &'a Analysis<'_>, n: usize) -> &'a str {
    let value = &a.nodes[n].value["type"];
    value["desugaredQualType"]
        .as_str()
        .or_else(|| value["qualType"].as_str())
        .unwrap_or("")
}

fn ast_surface(a: &Analysis<'_>, n: usize) -> Option<Surface> {
    Some(Surface {
        ty: ScalarType::parse(raw_type(a, n))?,
        category: match a.nodes[n].value["valueCategory"].as_str()? {
            "lvalue" => Category::Lvalue,
            "prvalue" => Category::Prvalue,
            _ => return None,
        },
    })
}

/// This is C++ built-in scalar typing, independently of the numeric carrier.
/// In particular, a same-valued int cannot replace bool, and a variable lvalue
/// cannot replace an arithmetic prvalue. No reference casts or class operands
/// exist in the admitted IR.
fn surface(expr: &Expr, variable: CIntType) -> Surface {
    let integer = ScalarType::Integer;
    match expr {
        Expr::Var => Surface {
            ty: integer(variable),
            category: Category::Lvalue,
        },
        Expr::Constant { ty, .. } | Expr::Cast { ty, .. } => Surface::prvalue(integer(*ty)),
        Expr::Unary { op, operand } => Surface::prvalue(match op {
            UnaryOp::LogicalNot => ScalarType::Bool,
            UnaryOp::BitNot | UnaryOp::Negate => integer(surface(operand, variable).ty.promoted()),
        }),
        Expr::Binary { op, left, right } => {
            let left = surface(left, variable).ty.promoted();
            let right = surface(right, variable).ty.promoted();
            Surface::prvalue(match op {
                BinaryOp::Eq
                | BinaryOp::Ne
                | BinaryOp::Lt
                | BinaryOp::Le
                | BinaryOp::Gt
                | BinaryOp::Ge
                | BinaryOp::LogicalAnd
                | BinaryOp::LogicalOr => ScalarType::Bool,
                BinaryOp::Shl | BinaryOp::Shr => integer(left),
                _ => integer(nversion::common_type(left, right)),
            })
        }
        Expr::Conditional {
            then_expr,
            else_expr,
            ..
        } => {
            let yes = surface(then_expr, variable);
            let no = surface(else_expr, variable);
            if yes == no {
                yes
            } else if yes.ty == no.ty {
                Surface::prvalue(yes.ty)
            } else {
                Surface::prvalue(integer(nversion::common_type(
                    yes.ty.promoted(),
                    no.ty.promoted(),
                )))
            }
        }
    }
}

pub(super) fn lower(
    a: &Analysis<'_>,
    n: usize,
    admitted: &impl Fn(&str) -> bool,
) -> Option<Lowered> {
    struct Lowering<'a, 'b, F> {
        a: &'a Analysis<'b>,
        admitted: &'a F,
        binding: Option<(String, CIntType)>,
        reads: Vec<usize>,
        entry: Option<usize>,
        nodes: usize,
    }
    impl<F: Fn(&str) -> bool> Lowering<'_, '_, F> {
        fn visit(&mut self, n: usize, required: bool, depth: usize) -> Option<Expr> {
            self.nodes += 1;
            if depth > 48 || self.nodes > 192 {
                return None;
            }
            let expected = ast_surface(self.a, n)?;
            let children = self.a.nodes[n].children.clone();
            let result = match self.a.kind(n) {
                "IntegerLiteral" => {
                    let ScalarType::Integer(ty) = expected.ty else {
                        return None;
                    };
                    Expr::constant(self.a.nodes[n].value["value"].as_str()?.parse().ok()?, ty)
                }
                "CXXBoolLiteralExpr" => Expr::unary(
                    UnaryOp::LogicalNot,
                    Expr::constant(
                        (!self.a.nodes[n].value["value"].as_bool()?) as i128,
                        CIntType::I32,
                    ),
                ),
                "DeclRefExpr" => {
                    let id = self.a.nodes[n].value["referencedDecl"]["id"].as_str()?;
                    if !(self.admitted)(id) {
                        return None;
                    }
                    let ScalarType::Integer(ty) = expected.ty else {
                        return None;
                    };
                    if let Some((binding, previous)) = &self.binding {
                        if binding != id || *previous != ty {
                            return None;
                        }
                    } else {
                        self.binding = Some((id.into(), ty));
                    }
                    let location = self.a.location(n)?;
                    let name = self.a.nodes[n].value["referencedDecl"]["name"].as_str()?;
                    if self.a.source.get(location.start..location.end)? != name {
                        return None;
                    }
                    self.reads.push(n);
                    if required && self.entry.is_none() {
                        self.entry = Some(n);
                    }
                    Expr::Var
                }
                "ParenExpr" | "ConstantExpr" if children.len() == 1 => {
                    self.visit(children[0], required, depth + 1)?
                }
                "ImplicitCastExpr" | "CStyleCastExpr" if children.len() == 1 => {
                    if !matches!(
                        self.a.nodes[n].value["castKind"].as_str(),
                        Some("LValueToRValue" | "IntegralCast" | "IntegralToBoolean" | "NoOp")
                    ) {
                        return None;
                    }
                    let operand = self.visit(children[0], required, depth + 1)?;
                    match expected.ty {
                        ScalarType::Bool => {
                            if ast_surface(self.a, children[0])? == expected {
                                operand
                            } else {
                                Expr::unary(
                                    UnaryOp::LogicalNot,
                                    Expr::unary(UnaryOp::LogicalNot, operand),
                                )
                            }
                        }
                        ScalarType::Integer(ty) => {
                            // Keep Bool->int and lvalue->prvalue conversions even
                            // when the C numeric carrier already has type int.
                            if ast_surface(self.a, children[0])? == expected {
                                operand
                            } else {
                                Expr::cast(ty, operand)
                            }
                        }
                    }
                }
                "UnaryOperator" if children.len() == 1 => {
                    let operand = self.visit(children[0], required, depth + 1)?;
                    match self.a.op(n) {
                        "+" => Expr::cast(expected.ty.promoted(), operand),
                        "!" => Expr::unary(UnaryOp::LogicalNot, operand),
                        "~" => Expr::unary(UnaryOp::BitNot, operand),
                        "-" => Expr::unary(UnaryOp::Negate, operand),
                        _ => return None,
                    }
                }
                "BinaryOperator" if children.len() == 2 => {
                    let op = expressions::binary(self.a.op(n))?;
                    Expr::binary(
                        op,
                        self.visit(children[0], required, depth + 1)?,
                        self.visit(
                            children[1],
                            required && !matches!(op, BinaryOp::LogicalAnd | BinaryOp::LogicalOr),
                            depth + 1,
                        )?,
                    )
                }
                "ConditionalOperator" if children.len() == 3 => Expr::conditional(
                    self.visit(children[0], required, depth + 1)?,
                    self.visit(children[1], false, depth + 1)?,
                    self.visit(children[2], false, depth + 1)?,
                ),
                _ => return None,
            };
            let variable = self.binding.as_ref().map_or(CIntType::I32, |(_, t)| *t);
            if surface(&result, variable) != expected
                || result.infer_type(variable).ok()? != expected.ty.promoted()
            {
                return None;
            }
            Some(result)
        }
    }
    let mut lowering = Lowering {
        a,
        admitted,
        binding: None,
        reads: vec![],
        entry: None,
        nodes: 0,
    };
    let expression = lowering.visit(n, true, 0)?;
    let (binding, variable_type) = lowering.binding?;
    let mut pending = vec![&expression];
    let mut carrier_nodes = 0;
    while let Some(node) = pending.pop() {
        carrier_nodes += 1;
        match node {
            Expr::Var | Expr::Constant { .. } => {}
            Expr::Unary { operand, .. } | Expr::Cast { operand, .. } => pending.push(operand),
            Expr::Binary { left, right, .. } => pending.extend([left.as_ref(), right.as_ref()]),
            Expr::Conditional {
                condition,
                then_expr,
                else_expr,
            } => pending.extend([condition.as_ref(), then_expr.as_ref(), else_expr.as_ref()]),
        }
    }
    Some(Lowered {
        expression,
        binding,
        variable_type,
        read_nodes: lowering.reads,
        entry_read: lowering.entry,
        // Conversion nodes inserted by the bridge participate in flow budgets.
        nodes: carrier_nodes,
    })
}

fn scope(a: &Analysis<'_>, mut n: usize) -> Vec<String> {
    let mut names = vec![];
    while let Some(parent) = a.nodes[n].parent {
        if a.kind(parent) == "NamespaceDecl" {
            names.push(a.name(parent).into());
        }
        n = parent;
    }
    names.reverse();
    names
}

fn admission_reason(
    a: &Analysis<'_>,
    function: usize,
    overloaded: &BTreeSet<(Vec<String>, String)>,
) -> Option<String> {
    if a.kind(function) != "FunctionDecl" {
        return Some("methods, constructors, destructors and conversion functions".into());
    }
    let mut ancestor = a.nodes[function].parent;
    while let Some(n) = ancestor {
        if !matches!(
            a.kind(n),
            "TranslationUnitDecl" | "NamespaceDecl" | "LinkageSpecDecl"
        ) {
            return Some(format!(
                "function context {} (including templates/classes)",
                a.kind(n)
            ));
        }
        ancestor = a.nodes[n].parent;
    }
    if overloaded.contains(&(scope(a, function), a.name(function).into()))
        || a.name(function).starts_with("operator")
    {
        return Some("overload set or overloaded operator".into());
    }
    if a.nodes[function].value["variadic"].as_bool() == Some(true) {
        return Some("variadic function".into());
    }
    let result = raw_type(a, function).split(" (").next().unwrap_or("");
    if result != "void" && ScalarType::parse(result).is_none() {
        return Some(format!("function result type {}", raw_type(a, function)));
    }
    for n in a.descendants(function).into_iter().skip(1) {
        let kind = a.kind(n);
        if matches!(kind, "ParmVarDecl" | "VarDecl") {
            if !matches!(
                ScalarType::parse(raw_type(a, n)),
                Some(ScalarType::Integer(_))
            ) {
                return Some(format!("non-admitted declaration type {} (Bool variables, references, qualifiers and objects are withheld)", raw_type(a, n)));
            }
            if matches!(
                a.nodes[n].value["storageClass"].as_str(),
                Some("static" | "extern")
            ) || a.nodes[n].value.get("tls").is_some()
            {
                return Some("non-automatic local storage".into());
            }
        } else if !raw_type(a, n).is_empty() && ScalarType::parse(raw_type(a, n)).is_none() {
            return Some(format!(
                "non-built-in scalar expression type {}",
                raw_type(a, n)
            ));
        }
        if kind == "DeclRefExpr" {
            let Some(id) = a.nodes[n].value["referencedDecl"]["id"].as_str() else {
                return Some("unresolved declaration reference".into());
            };
            if !a
                .declarations
                .get(id)
                .is_some_and(|&d| a.function_of[d] == Some(function))
            {
                return Some("nonlocal declaration reference or function call".into());
            }
        }
        if matches!(kind, "ImplicitCastExpr" | "CStyleCastExpr")
            && !matches!(
                a.nodes[n].value["castKind"].as_str(),
                Some("LValueToRValue" | "IntegralCast" | "IntegralToBoolean" | "NoOp")
            )
        {
            return Some(format!("cast kind {}", a.nodes[n].value["castKind"]));
        }
        if kind == "UnaryOperator" && !matches!(a.op(n), "+" | "-" | "~" | "!" | "++" | "--") {
            return Some(format!("unary operation {}", a.op(n)));
        }
        if !matches!(
            kind,
            "CompoundStmt"
                | "DeclStmt"
                | "ReturnStmt"
                | "IfStmt"
                | "ForStmt"
                | "WhileStmt"
                | "DoStmt"
                | "SwitchStmt"
                | "CaseStmt"
                | "DefaultStmt"
                | "BreakStmt"
                | "ContinueStmt"
                | "NullStmt"
                | "ParmVarDecl"
                | "VarDecl"
                | "IntegerLiteral"
                | "CXXBoolLiteralExpr"
                | "DeclRefExpr"
                | "ParenExpr"
                | "ConstantExpr"
                | "ImplicitCastExpr"
                | "CStyleCastExpr"
                | "UnaryOperator"
                | "BinaryOperator"
                | "CompoundAssignOperator"
                | "ConditionalOperator"
                | "UnusedAttr"
                | "NoInlineAttr"
                | "AlwaysInlineAttr"
        ) {
            return Some(format!("AST node {kind}"));
        }
    }
    None
}

fn admitted_functions(a: &mut Analysis<'_>) -> (Vec<(usize, usize)>, Vec<Value>) {
    // Count distinct signatures in the real namespace context; redeclarations
    // of one signature do not invent an overload. Templates remain withheld.
    let mut signatures: BTreeMap<(Vec<String>, String), BTreeSet<String>> = BTreeMap::new();
    for n in 0..a.nodes.len() {
        if a.kind(n) == "FunctionDecl" {
            signatures
                .entry((scope(a, n), a.name(n).into()))
                .or_default()
                .insert(raw_type(a, n).into());
        }
    }
    let overloaded = signatures
        .into_iter()
        .filter_map(|(name, types)| (types.len() > 1).then_some(name))
        .collect();
    let mut admitted = vec![];
    let mut withheld = vec![];
    let mut seen = HashSet::new();
    for function in 0..a.nodes.len() {
        if !matches!(
            a.kind(function),
            "FunctionDecl"
                | "CXXMethodDecl"
                | "CXXConstructorDecl"
                | "CXXDestructorDecl"
                | "CXXConversionDecl"
        ) {
            continue;
        }
        let Some(location) = a.location(function) else {
            continue;
        };
        let Some(body) = a.nodes[function].children.iter().copied().find(|&b| {
            matches!(
                a.kind(b),
                "CompoundStmt" | "CXXTryStmt" | "CoroutineBodyStmt"
            )
        }) else {
            continue;
        };
        if !seen.insert((location.start, location.end)) {
            continue;
        }
        if let Some(reason) = admission_reason(a, function, &overloaded) {
            a.functions_withheld += 1;
            a.notes.insert(format!(
                "C++ analysis of {} withheld: {reason}.",
                a.name(function)
            ));
            withheld
                .push(json!({"function": a.name(function), "location": location, "reason":reason}));
        } else {
            admitted.push((function, body));
        }
    }
    (admitted, withheld)
}

fn diagnostics(a: &mut Analysis<'_>, functions: &[(usize, usize)]) {
    let accepted: HashSet<_> = functions.iter().map(|(f, _)| *f).collect();
    let eligible_starts: HashSet<_> = (0..a.nodes.len())
        .filter(|&n| {
            a.function_of[n].is_some_and(|f| accepted.contains(&f))
                || (a.function_of[n].is_none()
                    && a.kind(n) == "VarDecl"
                    && matches!(
                        ScalarType::parse(raw_type(a, n)),
                        Some(ScalarType::Integer(_))
                    ))
        })
        .filter_map(|n| a.location(n).map(|l| l.start))
        .collect();
    a.constants();
    a.unused();
    a.findings
        .retain(|f| f.kind == "duplicate-constant" || eligible_starts.contains(&f.location.start));
    for finding in &mut a.findings {
        if finding.kind == "duplicate-constant" {
            finding.requirements = vec![
                "Preserve each C++ use's exact type, value category, constant-expression requirements, binding and macro/stringification behavior; constexpr aliases require declaration-context review.".into(),
                "Overloads, templates and deduced types can observe a type change; equal mathematical values alone do not permit substitution.".into(),
                "Repeated bytes may already compress well; no compressed or native-size saving is inferred.".into(),
            ];
        }
    }
}

fn finish(a: &mut Analysis<'_>) -> (Vec<Value>, usize) {
    a.expressions.sort_by_key(|s| {
        (
            std::cmp::Reverse(s.static_domain.finite_cardinality.is_some()),
            std::cmp::Reverse(s.original.len()),
            s.location.start,
        )
    });
    if a.expressions.len() > a.options.max_nversion_targets {
        a.expressions_omitted += a.expressions.len() - a.options.max_nversion_targets;
        a.expressions.truncate(a.options.max_nversion_targets);
    }
    let mut details = vec![];
    let mut incomplete = 0;
    for site in a.expressions.clone() {
        let original_surface = surface(&site.expression, site.variable_type);
        let mut detail = json!({
            "id":site.id, "location":site.location, "function":site.function,
            "symbol":site.symbol, "variable_type":site.variable_type.c_name(),
            "result_type":original_surface.ty.name(), "value_category":original_surface.category,
            "original":site.original, "static_domain":site.static_domain, "domain_basis":site.domain_basis,
            "status":"pending", "comparison":null
        });
        let Some(values) = a.expression_domains[&site.id].enumerate(FINITE_LIMIT) else {
            detail["status"] = json!("static-domain-too-large; C++ observations are not supported");
            details.push(detail);
            continue;
        };
        let remaining = a.options.max_nversion_work.saturating_sub(a.nversion_work);
        if remaining < 1000 {
            a.expressions_omitted += 1;
            detail["status"] = json!("global-comparison-work-budget-exhausted");
            details.push(detail);
            continue;
        }
        let mut budget = SearchBudget::default();
        budget.max_evaluations = budget.max_evaluations.min(remaining);
        let request = SearchRequest {
            original:site.expression.clone(), original_source:site.original.clone(), symbol:site.symbol.clone(),
            variable_type:site.variable_type, domain:FiniteDomain {
                values, provenance:DomainProvenance::StaticConservative,
                description:"Entire conservative intraprocedural C++ site domain; numeric comparison is restricted to the common defined C/C++ LP64 integer subset; surface type and value category checked separately.".into(),
            }, budget,
        };
        match nversion::compare_and_suggest(&request) {
            Ok(comparison) => {
                a.nversion_work += comparison.statistics.evaluation_steps;
                incomplete += (!comparison.complete) as usize;
                let mut retained = vec![];
                let mut type_rejections = vec![];
                for candidate in &comparison.candidates {
                    let candidate_surface = surface(&candidate.expression, site.variable_type);
                    if candidate_surface != original_surface {
                        type_rejections.push(json!({"source":candidate.source, "type":candidate_surface.ty.name(), "value_category":candidate_surface.category,
                            "reason":"C++ type or value category differs from the original; equal numeric carrier values are insufficient"}));
                        continue;
                    }
                    retained.push(json!({
                        "source":candidate.source, "source_bytes":candidate.source_bytes, "bytes_saved":candidate.bytes_saved,
                        "family":candidate.family, "result_type":candidate_surface.ty.name(), "value_category":candidate_surface.category,
                        "evidence":{"equivalent":candidate.evidence.equivalent, "complete":candidate.evidence.complete,
                            "checked_values":candidate.evidence.checked_values, "scope":candidate.evidence.scope,
                            "cpp_surface_type_and_category_preserved":true, "numeric_semantics":"common-defined-c-cpp-lp64-integer-subset"}
                    }));
                    if candidate.bytes_saved > 0 && retained.len() <= 3 {
                        a.emit(Finding {
                            id:format!("cpp-nversion:{}:{}:{}",site.location.start,site.location.end,candidate.source),
                            kind:"nversion-domain-equivalence".into(), assurance:"exhaustive-static-cpp-containing-domain".into(),
                            location:site.location.clone(), function:Some(site.function.clone()), symbol:Some(site.symbol.clone()),
                            message:format!("C++ {} prvalue is preserved, with equal defined numeric results for all {} inputs in this site's conservative domain; candidate family {:?}.", original_surface.ty.name(),candidate.evidence.checked_values,candidate.family),
                            suggestion:Some(candidate.source.clone()), original:site.original.clone(), related_locations:vec![],
                            requirements:vec![
                                "Preserve surrounding precedence, C++ type and value category, ordinary stable-read and source-observation contracts; this is not a whole-program proof or an applied edit.".into(),
                                "Only built-in scalar operations in the common defined C/C++ model are admitted; unsupported C++ semantics are withheld rather than classified as C++ undefined behavior.".into(),
                                "Recompile and measure the complete submitted artifact after manual review; source bytes do not predict native or packed size.".into(),
                            ], estimated_source_bytes_saved:Some(candidate.bytes_saved),
                        });
                    }
                }
                detail["status"] = json!(if comparison.original_defined {
                    "compared"
                } else {
                    "outside-common-defined-integer-model"
                });
                detail["comparison"] = json!({
                    "advisory_only":true, "original_defined_in_common_model":comparison.original_defined,
                    "common_model_failure":comparison.original_failure, "candidates":retained,
                    "cpp_type_rejections":type_rejections, "numeric_rejection_samples":comparison.rejections,
                    "numeric_search_statistics":comparison.statistics, "budget":comparison.budget,
                    "complete_generated_numeric_grammar":comparison.complete, "stop_reasons":comparison.stop_reasons,
                    "grammar":comparison.grammar, "numeric_model_limitations":comparison.limitations,
                    "numeric_carrier_types_are_not_cpp_surface_types":true,
                });
            }
            Err(error) => detail["status"] = json!(format!("comparison-withheld: {error}")),
        }
        details.push(detail);
    }
    details.sort_by_key(|s| s["location"]["start"].as_u64().unwrap_or(0));
    a.expressions.clear();
    a.expression_domains.clear();
    a.expression_ids.clear();
    (details, incomplete)
}

pub(super) fn analyze(source: &[u8], options: &AdvisorOptions) -> Result<AdviceReport> {
    super::validate_options(source, options)?;
    ensure!(
        cpp_standard(&options.standard),
        "C++ advisor supports c++17, c++20, gnu++17 and gnu++20"
    );
    let source = std::str::from_utf8(source)?;
    let frontend = FrontendSession::new_for_advice(FrontendConfig {
        clang: options.clang.clone(),
        standard: options.standard.clone(),
        compiler_args: options.compiler_args.clone(),
        source_path: options.source_path.clone(),
        seconds: options.frontend_seconds,
        memory_bytes: options.frontend_memory_bytes,
        ast_bytes: options.ast_bytes,
    })?;
    let parsed = frontend.parse_for_advice(source.as_bytes())?;
    let context = sha256(&serde_json::to_vec(&json!({
        "source_sha256":sha256(source.as_bytes()), "frontend":frontend.info,
        "preprocessing_sha256":parsed.preprocessing.as_ref().and_then(|p|p.stable_sha256.as_ref()),
        "analysis":"intraprocedural-cpp-lp64-surface-typed-carrier-v1",
        "finite_flow_work_budget":options.max_finite_flow_work
    }))?);
    let mut analysis = Analysis::new(source, parsed, options);
    analysis.notes = BTreeSet::from([
        "C++17/20 source is parsed as C++ by Clang. Advice never edits source or enters compression search; complete-file recompilation and measurement remain separate.".into(),
        "Only admitted non-overloaded free functions with ordinary automatic int/unsigned/long/long-long scalars are modeled. Namespaces and language-linkage declarations retain their actual AST ancestry.".into(),
        "Templates, methods, class objects, references, pointers, Bool variables, qualified storage, nonlocal reads, calls, named casts, overloaded/rewritten operators and unrecognized AST constructs withhold the function's flow and equivalence analysis. Directly observed typed literal duplicates may still be reported as separate diagnostics.".into(),
        "C++ bool expression results and lvalue/prvalue categories are validated separately from a private C integer value carrier. Candidates preserve both; only prvalue targets are advised.".into(),
        "The common defined integer model is deliberately stricter than C++17/20: negative signed shifts, out-of-range signed casts and other unsupported cases withhold comparison, even where a C++ version specifies a value.".into(),
        "Static domains describe individual evaluated reads in admitted defined executions, not whole-program invariants. C++ runtime profiling/instrumentation is not supported.".into(),
        "Candidate generation, domain enumeration and comparison budgets are finite. C++ type filtering can discard retained numeric candidates; absence of a suggestion is not an optimality proof.".into(),
    ]);
    let (functions, withheld) = admitted_functions(&mut analysis);
    diagnostics(&mut analysis, &functions);
    flow::analyze_functions(&mut analysis, functions);
    let (expressions, incomplete) = finish(&mut analysis);
    for range in &mut analysis.ranges {
        range.instrumentable = false;
    }
    analysis.findings.sort_by(|a, b| {
        (a.location.start, &a.kind, &a.id).cmp(&(b.location.start, &b.kind, &b.id))
    });
    analysis.ranges.sort_by_key(|r| r.location.start);
    Ok(AdviceReport {
        format_version: 2,
        advisory_only: true,
        source_sha256: sha256(source.as_bytes()),
        analysis_context_sha256: context,
        frontend: frontend.info.clone(),
        statistics: json!({
            "ast_nodes":analysis.nodes.len(), "functions_analyzed":analysis.functions_analyzed,
            "functions_withheld":analysis.functions_withheld, "findings_emitted":analysis.findings.len(),
            "findings_omitted":analysis.findings_omitted, "range_sites_emitted":analysis.ranges.len(),
            "range_sites_omitted":analysis.ranges_omitted, "expression_sites_emitted":expressions.len(),
            "expression_sites_omitted":analysis.expressions_omitted, "nversion_work_budget":options.max_nversion_work,
            "nversion_scalar_evaluations":analysis.nversion_work, "nversion_searches_incomplete":incomplete,
            "finite_flow_work_budget":options.max_finite_flow_work, "finite_flow_reserved_work":analysis.finite_flow_work.get(),
            "finite_flow_budget_exhausted":analysis.finite_flow_exhausted.get(), "frontend_work":frontend.statistics(),
            "source_modified":false, "compression_candidates_created":0, "final_file_bytes_measured":false,
        }),
        language_details: Some(
            json!({"language":"cpp", "supported_standard":options.standard,
            "numeric_model":"common-defined-c-cpp-lp64-integer-subset", "expressions":expressions,
            "withheld_functions":withheld, "instrumentation_supported":false}),
        ),
        findings: analysis.findings,
        ranges: analysis.ranges,
        expressions: vec![],
        limitations: analysis.notes.into_iter().collect(),
        complete: analysis.findings_omitted == 0
            && analysis.ranges_omitted == 0
            && analysis.expressions_omitted == 0
            && !analysis.finite_flow_exhausted.get()
            && incomplete == 0,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn surface_types_preserve_bool_promotion_and_value_category() {
        let zero = Expr::constant(0, CIntType::I32);
        let yes = Expr::unary(UnaryOp::LogicalNot, zero.clone());
        assert_eq!(
            surface(&yes, CIntType::I32),
            Surface::prvalue(ScalarType::Bool)
        );
        assert_eq!(
            surface(&Expr::unary(UnaryOp::BitNot, yes.clone()), CIntType::I32).ty,
            ScalarType::Integer(CIntType::I32)
        );
        assert_eq!(
            surface(&Expr::cast(CIntType::I32, yes.clone()), CIntType::I32).ty,
            ScalarType::Integer(CIntType::I32)
        );
        assert_eq!(
            surface(
                &Expr::conditional(yes.clone(), yes.clone(), yes.clone()),
                CIntType::I32
            )
            .ty,
            ScalarType::Bool
        );
        assert_eq!(
            surface(
                &Expr::conditional(yes.clone(), yes.clone(), zero),
                CIntType::I32
            )
            .ty,
            ScalarType::Integer(CIntType::I32)
        );
        assert_eq!(
            surface(&Expr::conditional(yes, Expr::Var, Expr::Var), CIntType::I32).category,
            Category::Lvalue
        );
        assert_ne!(
            surface(&Expr::Var, CIntType::I32),
            surface(&Expr::cast(CIntType::I32, Expr::Var), CIntType::I32)
        );
    }
}
