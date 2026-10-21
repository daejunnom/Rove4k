//! One AST lowering and one domain owner for static and observed n-version work.
use super::{
    domain::{Domain, DomainSummary, FINITE_LIMIT},
    nversion::{
        self, BinaryOp, CIntType, DomainProvenance, Expr, FiniteDomain, SearchBudget, SearchReport,
        SearchRequest, UnaryOp,
    },
    Analysis, SourceLocation,
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ExpressionSite {
    pub id: String,
    pub location: SourceLocation,
    pub function: String,
    pub symbol: String,
    pub c_type: String,
    pub result_type: String,
    pub original: String,
    pub expression: Expr,
    pub variable_type: CIntType,
    pub read_site_ids: Vec<String>,
    /// A read guaranteed to be evaluated whenever this expression is reached.
    /// Samples from a short-circuit RHS cannot stand in for expression entry.
    pub entry_site_id: Option<String>,
    pub static_domain: DomainSummary,
    pub domain_basis: Vec<String>,
    pub comparison: Option<SearchReport>,
    pub status: String,
}

pub(super) struct Lowered {
    pub expression: Expr,
    pub binding: String,
    pub variable_type: CIntType,
    pub read_nodes: Vec<usize>,
    pub entry_read: Option<usize>,
    pub nodes: usize,
}

fn binary(op: &str) -> Option<BinaryOp> {
    Some(match op {
        "+" => BinaryOp::Add,
        "-" => BinaryOp::Sub,
        "*" => BinaryOp::Mul,
        "/" => BinaryOp::Div,
        "%" => BinaryOp::Rem,
        "<<" => BinaryOp::Shl,
        ">>" => BinaryOp::Shr,
        "&" => BinaryOp::BitAnd,
        "|" => BinaryOp::BitOr,
        "^" => BinaryOp::BitXor,
        "==" => BinaryOp::Eq,
        "!=" => BinaryOp::Ne,
        "<" => BinaryOp::Lt,
        "<=" => BinaryOp::Le,
        ">" => BinaryOp::Gt,
        ">=" => BinaryOp::Ge,
        "&&" => BinaryOp::LogicalAnd,
        "||" => BinaryOp::LogicalOr,
        _ => return None,
    })
}

pub(super) fn is_target(a: &Analysis<'_>, n: usize) -> bool {
    ((a.kind(n) == "BinaryOperator" && binary(a.op(n)).is_some())
        || (a.kind(n) == "UnaryOperator" && matches!(a.op(n), "!" | "~" | "-"))
        || a.kind(n) == "ConditionalOperator")
        && a.location(n).is_some()
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
            let ty = CIntType::from_c_spelling(self.a.typ(n))?;
            let cs = self.a.nodes[n].children.clone();
            let result = match self.a.kind(n) {
                "IntegerLiteral" => Expr::Constant {
                    value: self.a.nodes[n].value["value"].as_str()?.parse().ok()?,
                    ty,
                },
                "CharacterLiteral" => Expr::Constant {
                    value: self.a.nodes[n].value["value"].as_i64()? as i128,
                    ty,
                },
                "DeclRefExpr" => {
                    let id = self.a.nodes[n].value["referencedDecl"]["id"].as_str()?;
                    if !(self.admitted)(id) {
                        return None;
                    }
                    if let Some((previous, previous_type)) = &self.binding {
                        if previous != id || *previous_type != ty {
                            return None;
                        }
                    } else {
                        self.binding = Some((id.to_owned(), ty));
                    }
                    let loc = self.a.location(n)?;
                    let name = self.a.nodes[n].value["referencedDecl"]["name"].as_str()?;
                    if self.a.source.get(loc.start..loc.end)? != name {
                        return None;
                    }
                    self.reads.push(n);
                    if required && self.entry.is_none() {
                        self.entry = Some(n);
                    }
                    Expr::Var
                }
                "ParenExpr" | "ConstantExpr" if cs.len() == 1 => {
                    self.visit(cs[0], required, depth + 1)?
                }
                "ImplicitCastExpr" | "CStyleCastExpr" if cs.len() == 1 => {
                    let operand = self.visit(cs[0], required, depth + 1)?;
                    if CIntType::from_c_spelling(self.a.typ(cs[0]))? == ty {
                        operand
                    } else {
                        Expr::Cast {
                            ty,
                            operand: Box::new(operand),
                        }
                    }
                }
                "UnaryOperator" if cs.len() == 1 => {
                    let operand = self.visit(cs[0], required, depth + 1)?;
                    if self.a.op(n) == "+" {
                        operand
                    } else {
                        Expr::Unary {
                            op: match self.a.op(n) {
                                "!" => UnaryOp::LogicalNot,
                                "~" => UnaryOp::BitNot,
                                "-" => UnaryOp::Negate,
                                _ => return None,
                            },
                            operand: Box::new(operand),
                        }
                    }
                }
                "BinaryOperator" if cs.len() == 2 => {
                    let op = binary(self.a.op(n))?;
                    let left = self.visit(cs[0], required, depth + 1)?;
                    let right = self.visit(
                        cs[1],
                        required && !matches!(op, BinaryOp::LogicalAnd | BinaryOp::LogicalOr),
                        depth + 1,
                    )?;
                    Expr::Binary {
                        op,
                        left: Box::new(left),
                        right: Box::new(right),
                    }
                }
                "ConditionalOperator" if cs.len() == 3 => Expr::Conditional {
                    condition: Box::new(self.visit(cs[0], required, depth + 1)?),
                    then_expr: Box::new(self.visit(cs[1], false, depth + 1)?),
                    else_expr: Box::new(self.visit(cs[2], false, depth + 1)?),
                },
                _ => return None,
            };
            // Do not silently reinterpret Clang promotions or result rank.
            let variable_type = self
                .binding
                .as_ref()
                .map(|(_, t)| *t)
                .unwrap_or(CIntType::I32);
            (result.infer_type(variable_type).ok()? == ty).then_some(result)
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
    Some(Lowered {
        expression,
        binding,
        variable_type,
        read_nodes: lowering.reads,
        entry_read: lowering.entry,
        nodes: lowering.nodes,
    })
}

pub(super) fn capture(
    a: &mut Analysis<'_>,
    function: usize,
    n: usize,
    lowered: Lowered,
    domain: Domain,
    basis: &str,
) {
    let Some(location) = a.location(n) else {
        return;
    };
    let id = format!("expression:{}:{}", location.start, location.end);
    if let Some(&index) = a.expression_ids.get(&id) {
        let merged = a.expression_domains[&id].union(&domain);
        a.expressions[index].static_domain = merged.summary();
        a.expressions[index].domain_basis.push(basis.into());
        a.expression_domains.insert(id, merged);
        return;
    }
    // Bound collection as well as search. Keep finite-domain opportunities
    // ahead of unbounded ones, deterministically; omissions remain visible.
    let rank = |s: &ExpressionSite| {
        (
            s.static_domain.finite_cardinality.is_some(),
            s.original.len(),
        )
    };
    let capacity = a.options.max_nversion_targets * 8;
    let replace = if a.expressions.len() >= capacity {
        a.expressions_omitted += 1;
        let (index, worst) = a
            .expressions
            .iter()
            .enumerate()
            .min_by_key(|(_, s)| rank(s))
            .unwrap();
        let incoming_rank = (
            domain.enumerate(FINITE_LIMIT).is_some(),
            location.end - location.start,
        );
        if incoming_rank <= rank(worst) {
            return;
        }
        Some(index)
    } else {
        None
    };
    let decl = a.declarations.get(&lowered.binding).copied();
    let symbol = decl.map(|d| a.name(d).to_owned()).unwrap_or_default();
    let site_id = |n| {
        a.location(n)
            .map(|l| format!("range:{}:{}", l.start, l.end))
    };
    let site = ExpressionSite {
        id: id.clone(),
        location: location.clone(),
        function: a.name(function).to_owned(),
        symbol,
        c_type: lowered.variable_type.c_name().into(),
        result_type: a.typ(n).into(),
        original: a.source[location.start..location.end].into(),
        expression: lowered.expression,
        variable_type: lowered.variable_type,
        read_site_ids: lowered.read_nodes.into_iter().filter_map(site_id).collect(),
        entry_site_id: lowered.entry_read.and_then(site_id),
        static_domain: domain.summary(),
        domain_basis: vec![basis.into()],
        comparison: None,
        status: "pending".into(),
    };
    let index = if let Some(index) = replace {
        a.expression_ids.remove(&a.expressions[index].id);
        a.expression_domains.remove(&a.expressions[index].id);
        a.expressions[index] = site;
        index
    } else {
        a.expressions.push(site);
        a.expressions.len() - 1
    };
    a.expression_ids.insert(id.clone(), index);
    a.expression_domains.insert(id, domain);
}

pub(super) fn finish(a: &mut Analysis<'_>) {
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
    for index in 0..a.expressions.len() {
        let site = &a.expressions[index];
        let domain = &a.expression_domains[&site.id];
        let Some(values) = domain.enumerate(FINITE_LIMIT) else {
            a.expressions[index].status =
                "static-domain-too-large; eligible for conditional profile hypotheses".into();
            continue;
        };
        let remaining = a.options.max_nversion_work.saturating_sub(a.nversion_work);
        if remaining < 1000 {
            a.expressions[index].status = "global-comparison-work-budget-exhausted".into();
            a.expressions_omitted += 1;
            continue;
        }
        let mut budget = SearchBudget::default();
        budget.max_evaluations = budget.max_evaluations.min(remaining);
        let request = SearchRequest {
            original: site.expression.clone(), original_source: site.original.clone(), symbol: site.symbol.clone(),
            variable_type: site.variable_type, domain: FiniteDomain {
                values, provenance: DomainProvenance::StaticConservative,
                description: "Entire conservative site domain: interval intersected with known bits and supported branch/assignment finite sets. Reachability remains intraprocedural and defined-execution scoped.".into(),
            }, budget,
        };
        match nversion::compare_and_suggest(&request) {
            Ok(comparison) => {
                a.nversion_work += comparison.statistics.evaluation_steps;
                let site = &a.expressions[index];
                let findings: Vec<_> = comparison.candidates.iter().filter(|c| c.bytes_saved > 0).take(3).map(|candidate| super::Finding {
                    id: format!("nversion:{}:{}:{}", site.location.start, site.location.end, candidate.source),
                    kind: "nversion-domain-equivalence".into(), assurance: "exhaustive-static-containing-domain".into(),
                    location: site.location.clone(), function: Some(site.function.clone()), symbol: Some(site.symbol.clone()),
                    message: format!("Typed {} result matches over all {} values of this site's conservative domain; candidate family {:?}. This is an advisory expression comparison, not whole-program or packed-file validation.", site.result_type, candidate.evidence.checked_values, candidate.family),
                    suggestion: Some(candidate.source.clone()), original: site.original.clone(), related_locations: vec![],
                    requirements: vec!["Preserve surrounding precedence, C type/rank, ordinary stable-read and source-observation contracts; manual review remains required.".into(),
                        "Recompile and measure the complete submitted artifact separately; raw expression bytes do not predict packed/native cost.".into()],
                    estimated_source_bytes_saved: Some(candidate.bytes_saved),
                }).collect();
                for finding in findings {
                    a.emit(finding);
                }
                a.expressions[index].status = if comparison.original_defined {
                    "compared"
                } else {
                    "original-not-total-on-containing-domain"
                }
                .into();
                a.expressions[index].comparison = Some(comparison);
            }
            Err(error) => {
                a.expressions[index].status = format!("comparison-withheld: {error}");
            }
        }
    }
    a.expressions.sort_by_key(|s| s.location.start);
    a.expression_domains.clear();
    a.expression_ids.clear();
    a.notes.insert("N-version candidates are compared with exact C integer types over a bounded containing set. Candidate grammar/search budgets are finite; observed-domain hypotheses never become static proof or compression candidates.".into());
}
