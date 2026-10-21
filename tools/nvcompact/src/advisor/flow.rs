use super::{
    domain::{Domain, FINITE_LIMIT},
    expressions, nversion, Analysis, RangeSite,
};
use std::collections::{HashMap, HashSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Range {
    lo: i128,
    hi: i128,
}
impl Range {
    fn one(v: i128) -> Self {
        Self { lo: v, hi: v }
    }
    fn union(self, other: Self) -> Self {
        Self {
            lo: self.lo.min(other.lo),
            hi: self.hi.max(other.hi),
        }
    }
    fn singleton(self) -> Option<i128> {
        (self.lo == self.hi).then_some(self.lo)
    }
    fn boolean(self) -> bool {
        self.lo >= 0 && self.hi <= 1
    }
    fn truth(self) -> Option<bool> {
        if self.lo == 0 && self.hi == 0 {
            Some(false)
        } else if self.lo > 0 || self.hi < 0 {
            Some(true)
        } else {
            None
        }
    }
}

#[derive(Clone, Copy)]
struct IntType {
    bounds: Range,
    bits: u32,
    unsigned: bool,
    boolean: bool,
}
fn int_type(t: &str) -> Option<IntType> {
    // FrontendSession's LP64 probe establishes the supported 32/64-bit model.
    // Do not guess char signedness, short/enum width or qualified storage.
    let (bits, unsigned, boolean) = match t {
        "_Bool" => (1, true, true),
        "int" => (32, false, false),
        "unsigned int" => (32, true, false),
        "long" | "long long" => (64, false, false),
        "unsigned long" | "unsigned long long" => (64, true, false),
        _ => return None,
    };
    let bounds = if unsigned {
        Range {
            lo: 0,
            hi: (1i128 << bits) - 1,
        }
    } else {
        Range {
            lo: -(1i128 << (bits - 1)),
            hi: (1i128 << (bits - 1)) - 1,
        }
    };
    Some(IntType {
        bounds,
        bits,
        unsigned,
        boolean,
    })
}
fn convert(r: Range, t: IntType) -> Range {
    if t.boolean {
        return r
            .truth()
            .map(|v| Range::one(v as i128))
            .unwrap_or(Range { lo: 0, hi: 1 });
    }
    if r.lo >= t.bounds.lo && r.hi <= t.bounds.hi {
        return r;
    }
    if t.unsigned {
        if let Some(v) = r.singleton() {
            return Range::one(v.rem_euclid(1i128 << t.bits));
        }
    }
    // Signed out-of-range conversions are implementation-defined; unsigned
    // intervals may wrap into a disjoint set. A full type interval is safe.
    t.bounds
}
#[derive(Clone)]
struct Fact {
    domain: Domain,
    basis: String,
}
impl Fact {
    fn new(range: Range, t: IntType, basis: String) -> Self {
        Self {
            domain: Domain::interval(range.lo, range.hi, t.bits, !t.unsigned),
            basis,
        }
    }
    fn range(&self) -> Range {
        Range {
            lo: self.domain.lo,
            hi: self.domain.hi,
        }
    }
}
type Env = HashMap<String, Fact>;

pub(super) fn analyze(a: &mut Analysis<'_>) {
    let functions: Vec<_> = a.nodes[0]
        .children
        .iter()
        .copied()
        .filter_map(|f| {
            if a.kind(f) != "FunctionDecl" || a.location(f).is_none() {
                return None;
            }
            a.nodes[f]
                .children
                .iter()
                .copied()
                .find(|&b| a.kind(b) == "CompoundStmt")
                .map(|b| (f, b))
        })
        .collect();
    analyze_functions(a, functions);
}

/// The language adapter owns function admission and AST ancestry. The shared
/// intraprocedural pass never reparents namespace or template AST nodes.
pub(super) fn analyze_functions(a: &mut Analysis<'_>, functions: Vec<(usize, usize)>) {
    for (function, body) in functions {
        let mut flow = Flow {
            a,
            function,
            tracked: HashMap::new(),
            unsafe_expressions: HashSet::new(),
        };
        let nodes = flow.a.descendants(body);
        let reason = nodes.iter().find_map(|&n| {
            if matches!(
                flow.a.kind(n),
                "GotoStmt"
                    | "IndirectGotoStmt"
                    | "AddrLabelExpr"
                    | "LabelStmt"
                    | "GCCAsmStmt"
                    | "MSAsmStmt"
                    | "StmtExpr"
                    | "GenericSelectionExpr"
                    | "ChooseExpr"
                    | "AtomicExpr"
            ) {
                Some(flow.a.kind(n).to_owned())
            } else if flow.a.kind(n) == "DeclRefExpr"
                && matches!(
                    flow.a.nodes[n].value["referencedDecl"]["name"].as_str(),
                    Some(
                        "setjmp"
                            | "_setjmp"
                            | "sigsetjmp"
                            | "longjmp"
                            | "siglongjmp"
                            | "__builtin_setjmp"
                            | "__builtin_longjmp"
                    )
                )
            {
                Some("nonlocal control flow".into())
            } else {
                None
            }
        });
        if let Some(reason) = reason {
            flow.a.functions_withheld += 1;
            flow.a.notes.insert(format!(
                "Range analysis of {} withheld: unsupported {reason}.",
                flow.a.name(function)
            ));
            continue;
        }
        let mut escaped = HashSet::new();
        for &n in &nodes {
            if flow.a.kind(n) == "UnaryOperator" && flow.a.op(n) == "&" {
                for child in flow.a.descendants(n) {
                    if let Some(id) = flow.a.nodes[child].value["referencedDecl"]["id"].as_str() {
                        escaped.insert(id.to_owned());
                    }
                }
            }
        }
        for n in flow.a.descendants(function) {
            if !matches!(flow.a.kind(n), "VarDecl" | "ParmVarDecl") {
                continue;
            }
            // A macro initializer does not make the declaration's own direct
            // identifier a macro expansion. Check the identifier loc, not the
            // full declaration range (whose end may be a macro token).
            let loc = &flow.a.nodes[n].value["loc"];
            if ["spellingLoc", "expansionLoc", "includedFrom"]
                .iter()
                .any(|k| loc.get(k).is_some())
                || loc["file"].as_str().is_some_and(|p| p != flow.a.main_path)
                || loc["offset"].as_u64().and_then(|v| {
                    flow.a
                        .source
                        .get(v as usize..(v as usize).saturating_add(flow.a.name(n).len()))
                }) != Some(flow.a.name(n))
            {
                continue;
            }
            let Some(id) = flow.a.nodes[n].value["id"].as_str() else {
                continue;
            };
            if escaped.contains(id)
                || matches!(
                    flow.a.nodes[n].value["storageClass"].as_str(),
                    Some("static" | "extern")
                )
            {
                continue;
            }
            if let Some(t) = int_type(flow.a.typ(n)) {
                flow.tracked.insert(id.to_owned(), (n, t));
            }
        }
        let mut env = Env::new();
        for (id, &(decl, t)) in &flow.tracked {
            if flow.a.kind(decl) == "ParmVarDecl" {
                env.insert(
                    id.clone(),
                    Fact::new(
                        t.bounds,
                        t,
                        if super::cpp::is_cpp(flow.a) {
                            "declared parameter type in a defined C++ execution admitted by the common integer model".into()
                        } else {
                            "declared parameter type in a defined C execution".into()
                        },
                    ),
                );
            }
        }
        flow.a.functions_analyzed += 1;
        flow.statement(body, &mut env);
    }
}

struct Flow<'a, 'b> {
    a: &'a mut Analysis<'b>,
    function: usize,
    tracked: HashMap<String, (usize, IntType)>,
    /// Expressions whose removal could discard a potentially undefined or
    /// implementation-signalling arithmetic operation. Flow can still widen
    /// their result; read-only suggestions must not erase the operation.
    unsafe_expressions: HashSet<usize>,
}

impl Flow<'_, '_> {
    fn finite_evaluate(
        &self,
        lowered: &expressions::Lowered,
        values: &[i128],
    ) -> Option<Vec<nversion::TypedValue>> {
        // eval also checks the IR and infers types recursively. Reserve a
        // containing operation bound, rather than counting only input values.
        let cost = values
            .len()
            .checked_mul((lowered.nodes + 1).checked_pow(2)?)?
            .checked_mul(2)?;
        let used = self.a.finite_flow_work.get();
        if cost > self.a.options.max_finite_flow_work.saturating_sub(used) {
            self.a.finite_flow_exhausted.set(true);
            return None;
        }
        self.a.finite_flow_work.set(used + cost);
        values
            .iter()
            .map(|&v| nversion::eval(&lowered.expression, v, lowered.variable_type).ok())
            .collect()
    }
    fn lower(&self, n: usize) -> Option<expressions::Lowered> {
        expressions::lower(self.a, n, &|id| self.tracked.contains_key(id))
    }

    /// Evaluate a pure, single-binding expression over its entire containing
    /// input set. Failure loses precision; it never drops troublesome values.
    fn image(&self, n: usize, env: &Env) -> Option<Vec<i128>> {
        if !self.pure(n) {
            return None;
        }
        let children = &self.a.nodes[n].children;
        if let Some(value) = self.constant(n).and_then(Range::singleton) {
            return Some(vec![value]);
        }
        if matches!(self.a.kind(n), "ParenExpr" | "ConstantExpr") && children.len() == 1 {
            return self.image(children[0], env);
        }
        if matches!(self.a.kind(n), "ImplicitCastExpr" | "CStyleCastExpr") && children.len() == 1 {
            let t = int_type(self.a.typ(n))?;
            return self
                .image(children[0], env)?
                .into_iter()
                .map(|v| convert(Range::one(v), t).singleton())
                .collect();
        }
        if self.a.kind(n) == "ConditionalOperator" && children.len() == 3 {
            // Branch-result union is the same abstract operation used for an
            // if/else assignment. Do not convexify a sparse result merely
            // because the source spells the control flow with ?:.
            let mut values = Vec::new();
            for (truth, branch) in [(true, children[1]), (false, children[2])] {
                if let Some(branch_env) = self.refine(children[0], truth, env.clone()) {
                    values.extend(self.image(branch, &branch_env)?);
                }
            }
            values.sort_unstable();
            values.dedup();
            return (!values.is_empty() && values.len() <= FINITE_LIMIT).then_some(values);
        }
        let lowered = self.lower(n)?;
        let values = env.get(&lowered.binding)?.domain.enumerate(FINITE_LIMIT)?;
        Some(
            self.finite_evaluate(&lowered, &values)?
                .into_iter()
                .map(|v| v.value)
                .collect(),
        )
    }

    fn assigned_fact(
        &self,
        range: Range,
        t: IntType,
        exact: Option<Vec<i128>>,
        basis: String,
    ) -> Fact {
        let mut fact = Fact::new(range, t, basis);
        if let Some(values) = exact {
            let converted: Option<Vec<_>> = values
                .into_iter()
                .map(|v| convert(Range::one(v), t).singleton())
                .collect();
            if let Some(domain) =
                converted.and_then(|v| Domain::from_values(v, t.bits, !t.unsigned))
            {
                fact.domain = domain;
                fact.basis
                    .push_str("; complete finite-domain image with C conversions");
            }
        }
        fact
    }

    fn capture_expression(&mut self, n: usize, env: &Env) {
        if !expressions::is_target(self.a, n) {
            return;
        }
        let Some(lowered) = self.lower(n) else {
            return;
        };
        let mut parent = self.a.nodes[n].parent;
        while parent.is_some_and(|p| {
            matches!(
                self.a.kind(p),
                "ParenExpr" | "ImplicitCastExpr" | "ConstantExpr"
            )
        }) {
            parent = parent.and_then(|p| self.a.nodes[p].parent);
        }
        if let Some(parent) = parent {
            if expressions::is_target(self.a, parent)
                && !matches!(self.a.op(parent), "&&" | "||")
                && self
                    .lower(parent)
                    .is_some_and(|p| p.binding == lowered.binding)
            {
                return;
            }
        }
        let Some(fact) = env.get(&lowered.binding) else {
            return;
        };
        expressions::capture(
            self.a,
            self.function,
            n,
            lowered,
            fact.domain.clone(),
            &fact.basis,
        );
    }

    fn unwrap(&self, mut n: usize) -> usize {
        while self.a.nodes[n].children.len() == 1
            && matches!(self.a.kind(n), "ParenExpr" | "ImplicitCastExpr")
        {
            n = self.a.nodes[n].children[0];
        }
        n
    }
    /// Only conversions that preserve the entire declared value domain can
    /// carry a condition back to the original declaration.
    fn binding(&self, mut n: usize) -> Option<String> {
        loop {
            if self.a.kind(n) == "ParenExpr" && self.a.nodes[n].children.len() == 1 {
                n = self.a.nodes[n].children[0];
            } else if self.a.kind(n) == "ImplicitCastExpr" && self.a.nodes[n].children.len() == 1 {
                let child = self.a.nodes[n].children[0];
                let src = int_type(self.a.typ(child))?;
                let dst = int_type(self.a.typ(n))?;
                if src.bounds.lo < dst.bounds.lo || src.bounds.hi > dst.bounds.hi {
                    return None;
                }
                n = child;
            } else {
                break;
            }
        }
        if self.a.kind(n) != "DeclRefExpr" {
            return None;
        }
        let id = self.a.nodes[n].value["referencedDecl"]["id"].as_str()?;
        self.tracked.contains_key(id).then(|| id.to_owned())
    }
    fn pure(&self, n: usize) -> bool {
        match self.a.kind(n) {
            "IntegerLiteral" | "CharacterLiteral" => true,
            "CXXBoolLiteralExpr" if super::cpp::is_cpp(self.a) => true,
            "DeclRefExpr" => self.binding(n).is_some(),
            "ParenExpr" | "ImplicitCastExpr" | "CStyleCastExpr" | "ConstantExpr" => {
                int_type(self.a.typ(n)).is_some()
                    && self.a.nodes[n].children.iter().all(|&c| self.pure(c))
            }
            "UnaryOperator" => {
                matches!(self.a.op(n), "+" | "-" | "!" | "~")
                    && self.a.nodes[n].children.iter().all(|&c| self.pure(c))
            }
            "BinaryOperator" => {
                !matches!(self.a.op(n), "=" | ",")
                    && self.a.nodes[n].children.iter().all(|&c| self.pure(c))
            }
            "ConditionalOperator" => self.a.nodes[n].children.iter().all(|&c| self.pure(c)),
            _ => false,
        }
    }
    fn widen(&self, env: &mut Env, why: &str) {
        for (id, fact) in env.iter_mut() {
            if let Some((_, t)) = self.tracked.get(id) {
                *fact = Fact::new(t.bounds, *t, why.into());
            }
        }
    }
    fn join(&self, left: &Env, right: &Env) -> Env {
        left.iter()
            .filter_map(|(id, l)| {
                let r = right.get(id)?;
                Some((
                    id.clone(),
                    Fact {
                        domain: l.domain.union(&r.domain),
                        basis: if l.domain == r.domain && l.basis == r.basis {
                            l.basis.clone()
                        } else {
                            "union of reachable branch states".into()
                        },
                    },
                ))
            })
            .collect()
    }
    fn record(&mut self, n: usize, env: &Env, read: bool) {
        if !read {
            return;
        }
        let Some(id) = self.binding(n) else {
            return;
        };
        let Some(fact) = env.get(&id) else {
            return;
        };
        let (decl, _) = self.tracked[&id];
        let Some(location) = self.a.location(n) else {
            return;
        };
        let expression = self.a.source[location.start..location.end].to_owned();
        if expression != self.a.name(decl) || expression.is_empty() {
            return;
        }
        let site_id = format!("range:{}:{}", location.start, location.end);
        if let Some(&index) = self.a.range_ids.get(&site_id) {
            let previous = &mut self.a.ranges[index];
            if let (Ok(lo), Ok(hi)) = (
                previous.minimum.parse::<i128>(),
                previous.maximum.parse::<i128>(),
            ) {
                let range = (Range { lo, hi }).union(fact.range());
                previous.minimum = range.lo.to_string();
                previous.maximum = range.hi.to_string();
                // A repeated traversal may have a different state; do not keep
                // a previously narrow bit/set summary beside a wider interval.
                previous.domain = None;
            }
            return;
        }
        if self.a.ranges.len() >= self.a.options.max_ranges {
            self.a.ranges_omitted += 1;
            return;
        }
        let mut parent = self.a.nodes[n].parent;
        let mut operation = None;
        while let Some(p) = parent {
            if matches!(
                self.a.kind(p),
                "BinaryOperator" | "CompoundAssignOperator" | "UnaryOperator"
            ) {
                operation = Some(self.a.op(p).to_owned());
                break;
            }
            if !matches!(
                self.a.kind(p),
                "ImplicitCastExpr" | "ParenExpr" | "CStyleCastExpr"
            ) {
                break;
            }
            parent = self.a.nodes[p].parent;
        }
        self.a
            .range_ids
            .insert(site_id.clone(), self.a.ranges.len());
        self.a.ranges.push(RangeSite {
            id: site_id, location,
            function: self.a.name(self.function).to_owned(), symbol: self.a.name(decl).to_owned(),
            expression, c_type: self.a.typ(decl).to_owned(),
            minimum: fact.domain.lo.to_string(), maximum: fact.domain.hi.to_string(),
            basis: vec![fact.basis.clone(), "supported-flow interval, known bits and containing finite set at this evaluated read; other sites may have different domains".into()],
            operation, instrumentable: true,
            domain: Some(fact.domain.summary()),
        });
    }
    fn proposal(&mut self, n: usize, kind: &str, text: String, evidence: String) {
        // C++ expression types affect overload resolution, decltype and auto.
        // Its adapter admits proposals only after independent surface typing;
        // numeric 0/1 flow facts alone do not authorize C spelling advice.
        if super::cpp::is_cpp(self.a) {
            return;
        }
        if !self.pure(n) || text.is_empty() {
            return;
        }
        if self
            .a
            .descendants(n)
            .iter()
            .any(|n| self.unsafe_expressions.contains(n))
        {
            return;
        }
        let Some(mut finding) =
            self.a
                .finding(n, kind, "supported-flow-condition", evidence, Some(text))
        else {
            return;
        };
        if finding.estimated_source_bytes_saved.is_some_and(|d| d <= 0) {
            return;
        }
        finding.requirements = vec![
            "Valid only for this source, frontend context, evaluated site and supported defined-execution range; not a whole-program equivalence certificate.".into(),
            "Preserve surrounding precedence, token/source observation, type and side-effect contracts; recompile and measure the complete submitted file after review.".into(),
        ];
        self.a.emit(finding);
    }
    fn atom(&self, n: usize) -> String {
        let n = self.unwrap(n);
        let text = self.a.text(n);
        if matches!(
            self.a.kind(n),
            "DeclRefExpr" | "IntegerLiteral" | "CharacterLiteral" | "ParenExpr"
        ) {
            text
        } else {
            format!("({text})")
        }
    }
    fn statement(&mut self, n: usize, env: &mut Env) -> bool {
        let children = self.a.nodes[n].children.clone();
        match self.a.kind(n) {
            "CompoundStmt" => {
                for child in children {
                    if !self.statement(child, env) {
                        return false;
                    }
                }
            }
            "DeclStmt" => {
                for decl in children {
                    if self.a.kind(decl) != "VarDecl" {
                        // A block typedef can introduce a VLA and evaluate its
                        // bound immediately, despite having no initializer.
                        self.widen(
                            env,
                            "unmodeled declaration may evaluate variably modified type bounds",
                        );
                        continue;
                    }
                    if self.a.typ(decl).contains('[') {
                        self.widen(env, "array declaration may evaluate variable-length bounds");
                    }
                    let id = self.a.nodes[decl].value["id"]
                        .as_str()
                        .unwrap_or("")
                        .to_owned();
                    let init = self.a.nodes[decl]
                        .children
                        .iter()
                        .copied()
                        .find(|&c| !self.a.kind(c).ends_with("Attr"));
                    if let Some(init) = init {
                        let exact = self.image(init, env);
                        let r = self.expression(init, env, false, true);
                        if let Some((_, t)) = self.tracked.get(&id) {
                            if let Some(r) = r {
                                env.insert(
                                    id,
                                    self.assigned_fact(
                                        convert(r, *t),
                                        *t,
                                        exact,
                                        format!(
                                            "initializer at byte {} with typed interval transfer",
                                            self.a.location(init).map_or(0, |l| l.start)
                                        ),
                                    ),
                                );
                            }
                        }
                    }
                }
            }
            "IfStmt" if children.len() == 2 || children.len() == 3 => {
                let cond = children[0];
                let value = self.expression(cond, env, true, true);
                let mut yes = self.refine(cond, true, env.clone());
                let mut no = self.refine(cond, false, env.clone());
                if value.and_then(Range::truth) == Some(false) {
                    yes = None;
                }
                if value.and_then(Range::truth) == Some(true) {
                    no = None;
                }
                let yes = yes.and_then(|mut e| self.statement(children[1], &mut e).then_some(e));
                let no = no.and_then(|mut e| {
                    if children.len() < 3 || self.statement(children[2], &mut e) {
                        Some(e)
                    } else {
                        None
                    }
                });
                match (yes, no) {
                    (Some(y), Some(z)) => *env = self.join(&y, &z),
                    (Some(e), None) | (None, Some(e)) => *env = e,
                    (None, None) => return false,
                }
            }
            "WhileStmt" if children.len() == 2 => {
                self.widen(env, "loop entry widened to declared types; no fixed-point or iteration-count assumption");
                let cond = children[0];
                self.expression(cond, env, true, true);
                if let Some(mut body) = self.refine(cond, true, env.clone()) {
                    self.statement(children[1], &mut body);
                }
                self.widen(env, "loop exit widened; break/zero-iteration/iteration states are not distinguished");
            }
            "ForStmt" if self.a.nodes[n].slots.len() == 5 => {
                let slots = self.a.nodes[n].slots.clone();
                if let Some(init) = slots[0] {
                    self.statement(init, env);
                }
                self.widen(env, "for-loop entry widened to declared types");
                let mut body = env.clone();
                if let Some(cond) = slots[2] {
                    self.expression(cond, &mut body, true, true);
                    if let Some(refined) = self.refine(cond, true, body.clone()) {
                        body = refined;
                    }
                }
                if let Some(stmt) = slots[4] {
                    self.statement(stmt, &mut body);
                }
                // Increment can also be reached by continue, bypassing the body
                // tail; only widened facts may describe that shared point.
                self.widen(
                    &mut body,
                    "for increment widened because continue can bypass body assignments",
                );
                if let Some(increment) = slots[3] {
                    self.expression(increment, &mut body, false, true);
                }
                self.widen(env, "for-loop exit widened");
            }
            "DoStmt" if children.len() == 2 => {
                self.widen(env, "do-loop entry widened to declared types");
                let mut body = env.clone();
                self.statement(children[0], &mut body);
                self.widen(
                    &mut body,
                    "do-loop condition widened because continue can bypass body assignments",
                );
                self.expression(children[1], &mut body, true, true);
                self.widen(env, "do-loop exit widened");
            }
            "ReturnStmt" => {
                for child in children {
                    self.expression(child, env, false, true);
                }
                return false;
            }
            "BreakStmt" | "ContinueStmt" => return false,
            "NullStmt" => {}
            "SwitchStmt" => {
                self.widen(
                    env,
                    "switch/fallthrough is outside the supported flow subset",
                );
                self.a.notes.insert("Switch bodies are withheld from range advice; control flow after a switch uses widened facts.".into());
            }
            k if k.ends_with("Expr") || k.ends_with("Operator") || k.ends_with("Literal") => {
                self.expression(n, env, false, true);
            }
            _ => {
                self.widen(env, "unsupported statement invalidated narrow facts");
                self.a.notes.insert(format!(
                    "Unsupported statement {} withholds nested range advice.",
                    self.a.kind(n)
                ));
            }
        }
        true
    }

    fn expression(
        &mut self,
        n: usize,
        env: &mut Env,
        truth_context: bool,
        observe: bool,
    ) -> Option<Range> {
        if observe {
            self.capture_expression(n, env);
        }
        let children = self.a.nodes[n].children.clone();
        let typ = int_type(self.a.typ(n));
        let op = self.a.op(n).to_owned();
        match self.a.kind(n) {
            "IntegerLiteral" => self.a.nodes[n].value["value"]
                .as_str()?
                .parse()
                .ok()
                .map(Range::one),
            "CharacterLiteral" => self.a.nodes[n].value["value"]
                .as_i64()
                .map(|n| Range::one(n as i128)),
            "CXXBoolLiteralExpr" if super::cpp::is_cpp(self.a) => self.a.nodes[n].value["value"]
                .as_bool()
                .map(|v| Range::one(v as i128)),
            "DeclRefExpr" => {
                // A bare declaration reference is an lvalue. Its parent cast
                // determines whether an actual value read occurs.
                let mut parent = self.a.nodes[n].parent;
                while parent.is_some_and(|p| self.a.kind(p) == "ParenExpr") {
                    parent = parent.and_then(|p| self.a.nodes[p].parent);
                }
                let is_read = parent.is_some_and(|p| {
                    self.a.kind(p) == "ImplicitCastExpr"
                        && self.a.nodes[p].value["castKind"] == "LValueToRValue"
                });
                self.record(n, env, observe && is_read);
                self.binding(n).and_then(|id| env.get(&id).map(Fact::range))
            }
            "ParenExpr" | "ConstantExpr" if children.len() == 1 => {
                self.expression(children[0], env, truth_context, observe)
            }
            "ImplicitCastExpr" | "CStyleCastExpr" if children.len() == 1 => {
                let range = self.expression(children[0], env, truth_context, observe);
                if range
                    .zip(typ)
                    .is_some_and(|(r, t)| !t.unsigned && (r.lo < t.bounds.lo || r.hi > t.bounds.hi))
                {
                    self.unsafe_expressions.insert(n);
                }
                if typ.is_none() {
                    // A cast to a variably modified pointer type may evaluate
                    // bounds omitted from JSON child expressions.
                    self.widen(env, "unmodeled cast type invalidated narrow facts");
                }
                range.zip(typ).map(|(r, t)| convert(r, t))
            }
            "UnaryExprOrTypeTraitExpr" => {
                // sizeof(VLA-type) may evaluate bound side effects. Never read
                // or instrument its nested nodes; conservatively lose facts.
                self.widen(env, "sizeof/alignof boundary widened because variably modified types may evaluate bounds");
                None
            }
            "UnaryOperator" if children.len() == 1 => {
                if op == "&" {
                    return None;
                }
                if matches!(op.as_str(), "++" | "--") {
                    let id = self.binding(children[0]);
                    let before = id.as_ref().and_then(|id| env.get(id)).map(Fact::range);
                    if let (Some(id), Some(before), Some(t)) = (id, before, typ) {
                        let delta = if op == "++" { 1 } else { -1 };
                        let after = interval_binary("+", before, Range::one(delta), t);
                        env.insert(
                            id,
                            Fact::new(
                                after,
                                t,
                                "increment/decrement with typed overflow widening".into(),
                            ),
                        );
                        return Some(
                            if self.a.nodes[n].value["isPostfix"].as_bool() == Some(true) {
                                before
                            } else {
                                after
                            },
                        );
                    }
                    self.widen(env, "unmodeled increment invalidated narrow facts");
                    return typ.map(|t| t.bounds);
                }
                let r = self.expression(children[0], env, op == "!", observe)?;
                match op.as_str() {
                    "!" => Some(
                        r.truth()
                            .map(|v| Range::one((!v) as i128))
                            .unwrap_or(Range { lo: 0, hi: 1 }),
                    ),
                    "+" => Some(r),
                    "-" => {
                        let t = typ?;
                        if !t.unsigned && r.lo <= t.bounds.lo {
                            self.unsafe_expressions.insert(n);
                        }
                        Some(
                            r.hi.checked_neg()
                                .zip(r.lo.checked_neg())
                                .map(|(lo, hi)| convert(Range { lo, hi }, t))
                                .unwrap_or(t.bounds),
                        )
                    }
                    "~" => {
                        let t = typ?;
                        if t.unsigned {
                            Some(Range {
                                lo: t.bounds.hi - r.hi,
                                hi: t.bounds.hi - r.lo,
                            })
                        } else {
                            Some(t.bounds)
                        }
                    }
                    _ => typ.map(|t| t.bounds),
                }
            }
            "BinaryOperator" | "CompoundAssignOperator" if children.len() == 2 => {
                let left = children[0];
                let right = children[1];
                if op == "=" || self.a.kind(n) == "CompoundAssignOperator" {
                    let id = self.binding(left);
                    let exact = if op == "=" {
                        self.image(right, env)
                    } else {
                        None
                    };
                    let rhs = self.expression(right, env, false, observe);
                    if let Some(id) = id {
                        let (_, t) = self.tracked[&id];
                        let value = if op == "=" {
                            rhs.map(|r| convert(r, t))
                        } else {
                            let computation_type = |key: &str| {
                                let node = &self.a.nodes[n].value[key];
                                node["desugaredQualType"]
                                    .as_str()
                                    .or_else(|| node["qualType"].as_str())
                                    .and_then(int_type)
                            };
                            env.get(&id)
                                .map(Fact::range)
                                .zip(rhs)
                                .zip(computation_type("computeLHSType"))
                                .zip(computation_type("computeResultType"))
                                .map(|(((l, r), lhs_type), result_type)| {
                                    convert(
                                        interval_binary(
                                            op.trim_end_matches('='),
                                            convert(l, lhs_type),
                                            convert(r, result_type),
                                            result_type,
                                        ),
                                        t,
                                    )
                                })
                        };
                        let r = value.unwrap_or(t.bounds);
                        env.insert(
                            id,
                            self.assigned_fact(
                                r,
                                t,
                                exact,
                                format!(
                                    "assignment at byte {} with typed interval transfer",
                                    self.a.location(n).map_or(0, |l| l.start)
                                ),
                            ),
                        );
                        return Some(r);
                    }
                    self.widen(env, "indirect or unmodeled store invalidated narrow facts");
                    return typ.map(|t| t.bounds);
                }
                if op == "," {
                    self.expression(left, env, false, observe);
                    return self.expression(right, env, truth_context, observe);
                }
                if op == "&&" || op == "||" {
                    let l = self.expression(left, env, true, observe);
                    let take = op == "&&";
                    let mut rhs_env = self.refine(left, take, env.clone());
                    if l.and_then(Range::truth) == Some(!take) {
                        rhs_env = None;
                    }
                    let right_range = if let Some(e) = rhs_env.as_mut() {
                        self.expression(right, e, true, observe)
                    } else {
                        None
                    };
                    let skip_env = self.refine(left, !take, env.clone());
                    match (rhs_env, skip_env) {
                        (Some(a), Some(b)) => *env = self.join(&a, &b),
                        (Some(a), None) | (None, Some(a)) => *env = a,
                        _ => {}
                    }
                    return Some(
                        match (l.and_then(Range::truth), right_range.and_then(Range::truth)) {
                            (Some(false), _) if op == "&&" => Range::one(0),
                            (Some(true), _) if op == "||" => Range::one(1),
                            (Some(true), Some(r)) if op == "&&" => Range::one(r as i128),
                            (Some(false), Some(r)) if op == "||" => Range::one(r as i128),
                            (_, Some(false)) if op == "&&" => Range::one(0),
                            (_, Some(true)) if op == "||" => Range::one(1),
                            _ => Range { lo: 0, hi: 1 },
                        },
                    );
                }
                // Operand evaluation order is unspecified. Nested side effects
                // must not acquire left-before-right flow facts or read probes.
                let pure = self.pure(left) && self.pure(right);
                if !pure {
                    self.widen(env, "unordered operand effects invalidated narrow facts");
                }
                let l = self.expression(left, env, false, observe && pure);
                let r = self.expression(right, env, false, observe && pure);
                if !pure {
                    self.widen(env, "unordered operand effects invalidated narrow facts");
                }
                let (l, r, t) = (l?, r?, typ?);
                if !total_binary(&op, l, r, t) {
                    self.unsafe_expressions.insert(n);
                }
                let result = interval_binary(&op, l, r, t);
                if observe && pure {
                    self.binary_advice(n, left, right, &op, l, r, result, truth_context);
                }
                Some(result)
            }
            "ConditionalOperator" if children.len() == 3 => {
                let c = self.expression(children[0], env, true, observe);
                let mut yes = self.refine(children[0], true, env.clone());
                let mut no = self.refine(children[0], false, env.clone());
                if c.and_then(Range::truth) == Some(false) {
                    yes = None;
                }
                if c.and_then(Range::truth) == Some(true) {
                    no = None;
                }
                let y = yes
                    .as_mut()
                    .and_then(|e| self.expression(children[1], e, truth_context, observe));
                let z = no
                    .as_mut()
                    .and_then(|e| self.expression(children[2], e, truth_context, observe));
                match (&yes, &no) {
                    (Some(a), Some(b)) => *env = self.join(a, b),
                    (Some(a), None) | (None, Some(a)) => *env = a.clone(),
                    _ => {}
                }
                if observe
                    && c.is_some_and(Range::boolean)
                    && y == Some(Range::one(1))
                    && z == Some(Range::one(0))
                    && (truth_context || self.a.typ(children[0]) == self.a.typ(n))
                {
                    self.proposal(n, "boolean-selection", self.atom(children[0]), "The condition is in 0..1 at this site and the two selected values are 1 and 0; result type/truth context is preserved.".into());
                }
                // Unknown values and unreachable branches are different. A
                // reachable unmodeled operand contributes the full result
                // type; it must not disappear from a join.
                let y = if yes.is_some() {
                    y.or_else(|| typ.map(|t| t.bounds))
                } else {
                    None
                };
                let z = if no.is_some() {
                    z.or_else(|| typ.map(|t| t.bounds))
                } else {
                    None
                };
                match (y, z) {
                    (Some(y), Some(z)) => Some(y.union(z)),
                    (Some(y), None) | (None, Some(y)) => Some(y),
                    _ => typ.map(|t| t.bounds),
                }
            }
            "CallExpr" => {
                // Arguments also have unspecified relative evaluation order.
                // Do not instrument/advise reads inside an unmodeled call.
                self.widen(env, "call boundary invalidated narrow facts");
                typ.map(|t| t.bounds)
            }
            _ => {
                if !self.pure(n) {
                    self.widen(env, "unsupported expression invalidated narrow facts");
                }
                typ.map(|t| t.bounds)
            }
        }
    }

    fn binary_advice(
        &mut self,
        n: usize,
        left: usize,
        right: usize,
        op: &str,
        l: Range,
        r: Range,
        result: Range,
        truth_context: bool,
    ) {
        if matches!(op, "==" | "!=" | "<" | ">" | "<=" | ">=") {
            if let Some(v) = result.singleton() {
                self.proposal(n, "constant-comparison", v.to_string(), format!("At this operation the left range is {}..{} and the right range is {}..{}; {op} is always {v}. Both operands are non-observable supported expressions.", l.lo, l.hi, r.lo, r.hi));
                return;
            }
            let (operand, range, constant) = if let Some(v) = r.singleton() {
                (left, l, v)
            } else if let Some(v) = l.singleton() {
                (right, r, v)
            } else {
                return;
            };
            if range.boolean() && matches!(op, "==" | "!=") && matches!(constant, 0 | 1) {
                let positive = (op == "==") == (constant == 1);
                let original_type = self.a.typ(self.unwrap(operand));
                if !positive || truth_context || original_type == "int" {
                    let text = if positive {
                        self.atom(operand)
                    } else {
                        format!("!{}", self.atom(operand))
                    };
                    self.proposal(n, "boolean-domain-comparison", text, format!("The tested value is in {}..{} at this read; comparing a 0/1 value with {constant} preserves this {} result.", range.lo, range.hi, if truth_context { "truth-context" } else { "int" }));
                }
            }
        } else if op == "&" {
            if let Some(mask) = r.singleton() {
                if mask > 0
                    && mask & (mask + 1) == 0
                    && l.lo >= 0
                    && l.hi <= mask
                    && self.a.typ(self.unwrap(left)) == self.a.typ(n)
                {
                    self.proposal(n, "redundant-mask", self.atom(left), format!("The operand range {}..{} already fits the low-bit mask {mask}; no bit outside that mask can be set at this site.", l.lo, l.hi));
                }
            }
        } else if matches!(op, "%" | "/")
            && r.singleton().is_some_and(|d| d > 0)
            && l.lo >= 0
            && l.hi < r.lo
        {
            let text = if op == "/" {
                "0".into()
            } else {
                self.atom(left)
            };
            // 0 must preserve the operator's integer type; emit only int here.
            if op == "%" && self.a.typ(self.unwrap(left)) == self.a.typ(n)
                || op == "/" && self.a.typ(n) == "int"
            {
                self.proposal(n, "bounded-arithmetic", text, format!("The nonnegative dividend range {}..{} is below divisor {}; {op} can be simplified at this site.", l.lo, l.hi, r.lo));
            }
        }
    }

    fn constant(&self, n: usize) -> Option<Range> {
        let cs = &self.a.nodes[n].children;
        match self.a.kind(n) {
            "IntegerLiteral" => self.a.nodes[n].value["value"]
                .as_str()?
                .parse()
                .ok()
                .map(Range::one),
            "CharacterLiteral" => self.a.nodes[n].value["value"]
                .as_i64()
                .map(|v| Range::one(v as i128)),
            "CXXBoolLiteralExpr" if super::cpp::is_cpp(self.a) => self.a.nodes[n].value["value"]
                .as_bool()
                .map(|v| Range::one(v as i128)),
            "ParenExpr" | "ConstantExpr" if cs.len() == 1 => self.constant(cs[0]),
            "ImplicitCastExpr" | "CStyleCastExpr" if cs.len() == 1 => {
                Some(convert(self.constant(cs[0])?, int_type(self.a.typ(n))?))
            }
            "UnaryOperator" if cs.len() == 1 && self.a.op(n) == "-" => {
                let r = self.constant(cs[0])?;
                Some(convert(
                    Range {
                        lo: r.hi.checked_neg()?,
                        hi: r.lo.checked_neg()?,
                    },
                    int_type(self.a.typ(n))?,
                ))
            }
            _ => None,
        }
    }

    fn refine(&self, n: usize, truth: bool, mut env: Env) -> Option<Env> {
        if !self.pure(n) {
            return Some(env);
        }
        if let Some(lowered) = self.lower(n) {
            if let Some(fact) = env.get(&lowered.binding) {
                if let Some(values) = fact.domain.enumerate(FINITE_LIMIT) {
                    if let Some(evaluated) = self.finite_evaluate(&lowered, &values) {
                        let values = values
                            .into_iter()
                            .zip(evaluated)
                            .filter_map(|(v, result)| ((result.value != 0) == truth).then_some(v))
                            .collect();
                        let domain =
                            Domain::from_values(values, fact.domain.bits, fact.domain.signed)?;
                        env.insert(lowered.binding, Fact { domain, basis: format!(
                            "{} branch at byte {}; exhaustive typed filtering of the incoming conservative finite domain",
                            if truth { "true" } else { "false" }, self.a.location(n).map_or(0, |l| l.start)) });
                        return Some(env);
                    }
                }
            }
        }
        let cs = &self.a.nodes[n].children;
        match self.a.kind(n) {
            "ParenExpr" | "ImplicitCastExpr" if cs.len() == 1 => {
                // Only value-preserving conversion/truth of _Bool can refine.
                if self.a.kind(n) == "ParenExpr"
                    || self.a.nodes[n].value["castKind"] == "LValueToRValue"
                    || (super::cpp::is_cpp(self.a)
                        && self.a.nodes[n].value["castKind"] == "IntegralToBoolean")
                    || self.binding(n).is_some()
                {
                    return self.refine(cs[0], truth, env);
                }
            }
            "UnaryOperator" if self.a.op(n) == "!" && cs.len() == 1 => {
                return self.refine(cs[0], !truth, env)
            }
            "BinaryOperator" if cs.len() == 2 => {
                let mut op = self.a.op(n).to_owned();
                if op == "&&" && truth || op == "||" && !truth {
                    return self.refine(cs[1], truth, self.refine(cs[0], truth, env)?);
                }
                if op == "&&" || op == "||" {
                    let short = self.refine(cs[0], truth, env.clone());
                    let long = self
                        .refine(cs[0], !truth, env)
                        .and_then(|e| self.refine(cs[1], truth, e));
                    return match (short, long) {
                        (Some(a), Some(b)) => Some(self.join(&a, &b)),
                        (Some(a), None) | (None, Some(a)) => Some(a),
                        _ => None,
                    };
                }
                // A zero mask test fixes every masked bit. A nonzero test
                // fixes a one bit only for a single-bit mask.
                if op == "&" {
                    if let Some((id, mask)) = self.mask_binding(n) {
                        if !truth || mask.count_ones() == 1 {
                            let fact = env.get_mut(&id)?;
                            if !fact.domain.restrict_bits(
                                if truth { 0 } else { mask },
                                if truth { mask } else { 0 },
                            ) {
                                return None;
                            }
                            fact.basis =
                                "controlling mask test intersected with the incoming domain".into();
                            return Some(env);
                        }
                        if mask == 0 && truth {
                            return None;
                        }
                    }
                }
                if op == "==" && truth || op == "!=" && !truth {
                    let masked = self
                        .mask_binding(cs[0])
                        .zip(self.constant(cs[1]).and_then(Range::singleton))
                        .or_else(|| {
                            self.mask_binding(cs[1])
                                .zip(self.constant(cs[0]).and_then(Range::singleton))
                        });
                    if let Some(((id, mask), value)) = masked {
                        if value < 0 || value > u64::MAX as i128 || value as u64 & !mask != 0 {
                            return None;
                        }
                        let value = value as u64;
                        let fact = env.get_mut(&id)?;
                        if !fact.domain.restrict_bits(mask & !value, value) {
                            return None;
                        }
                        fact.basis =
                            "masked equality intersected with the incoming interval and known bits"
                                .into();
                        return Some(env);
                    }
                }
                let pair = self
                    .binding(cs[0])
                    .zip(self.constant(cs[1]).and_then(Range::singleton))
                    .or_else(|| {
                        let p = self
                            .binding(cs[1])
                            .zip(self.constant(cs[0]).and_then(Range::singleton));
                        if p.is_some() {
                            op = match op.as_str() {
                                "<" => ">",
                                ">" => "<",
                                "<=" => ">=",
                                ">=" => "<=",
                                x => x,
                            }
                            .into();
                        }
                        p
                    });
                if let Some((id, value)) = pair {
                    if !truth {
                        op = match op.as_str() {
                            "<" => ">=",
                            ">" => "<=",
                            "<=" => ">",
                            ">=" => "<",
                            "==" => "!=",
                            "!=" => "==",
                            x => x,
                        }
                        .into();
                    }
                    if let Some(fact) = env.get_mut(&id) {
                        let incoming = fact.range();
                        let range = match op.as_str() {
                            "<" => Range {
                                lo: i128::MIN,
                                hi: value.checked_sub(1)?,
                            },
                            "<=" => Range {
                                lo: i128::MIN,
                                hi: value,
                            },
                            ">" => Range {
                                lo: value.checked_add(1)?,
                                hi: i128::MAX,
                            },
                            ">=" => Range {
                                lo: value,
                                hi: i128::MAX,
                            },
                            "==" => Range::one(value),
                            "!=" if incoming.lo == value => Range {
                                lo: value.checked_add(1)?,
                                hi: incoming.hi,
                            },
                            "!=" if incoming.hi == value => Range {
                                lo: incoming.lo,
                                hi: value.checked_sub(1)?,
                            },
                            _ => incoming,
                        };
                        if !fact.domain.restrict_interval(range.lo, range.hi) {
                            return None;
                        }
                        fact.basis = format!(
                            "{} branch at byte {}; intersected with incoming supported-flow range",
                            if truth { "true" } else { "false" },
                            self.a.location(n).map_or(0, |l| l.start)
                        );
                    }
                }
            }
            "DeclRefExpr" => {
                if let Some(id) = self.binding(n) {
                    if let Some(fact) = env.get_mut(&id) {
                        let incoming = fact.range();
                        let restriction = if !truth {
                            Range::one(0)
                        } else if incoming.lo == 0 {
                            Range {
                                lo: 1,
                                hi: incoming.hi,
                            }
                        } else if incoming.hi == 0 {
                            Range {
                                lo: incoming.lo,
                                hi: -1,
                            }
                        } else {
                            incoming
                        };
                        if !fact
                            .domain
                            .restrict_interval(restriction.lo, restriction.hi)
                        {
                            return None;
                        }
                        fact.basis =
                            "intersection with the controlling expression's truth branch".into();
                    }
                }
            }
            _ => {}
        }
        Some(env)
    }

    fn mask_binding(&self, mut n: usize) -> Option<(String, u64)> {
        while self.a.kind(n) == "ParenExpr" && self.a.nodes[n].children.len() == 1 {
            n = self.a.nodes[n].children[0];
        }
        let cs = &self.a.nodes[n].children;
        if self.a.kind(n) != "BinaryOperator" || self.a.op(n) != "&" || cs.len() != 2 {
            return None;
        }
        let (id, mask) = self
            .binding(cs[0])
            .zip(self.constant(cs[1]).and_then(Range::singleton))
            .or_else(|| {
                self.binding(cs[1])
                    .zip(self.constant(cs[0]).and_then(Range::singleton))
            })?;
        let (_, t) = self.tracked[&id];
        // Do not carry bits across a narrowing or sign-changing conversion.
        let result = int_type(self.a.typ(n))?;
        (t.bits == result.bits && mask >= 0 && mask <= u64::MAX as i128)
            .then_some((id, mask as u64))
    }
}

/// Is evaluating the supported arithmetic total over these operand intervals?
/// This guard is stricter than merely obtaining a containing result interval:
/// removing a comparison must not erase possible division/shift/overflow UB.
fn total_binary(op: &str, l: Range, r: Range, t: IntType) -> bool {
    let fits = |x: Option<i128>| x.is_some_and(|v| (t.bounds.lo..=t.bounds.hi).contains(&v));
    match op {
        "+" if !t.unsigned => fits(l.lo.checked_add(r.lo)) && fits(l.hi.checked_add(r.hi)),
        "-" if !t.unsigned => fits(l.lo.checked_sub(r.hi)) && fits(l.hi.checked_sub(r.lo)),
        "*" if !t.unsigned => [l.lo, l.hi]
            .into_iter()
            .all(|a| [r.lo, r.hi].into_iter().all(|b| fits(a.checked_mul(b)))),
        "/" | "%" => {
            (r.hi < 0 || r.lo > 0)
                && (t.unsigned || !(l.lo <= t.bounds.lo && r.lo <= -1 && r.hi >= -1))
        }
        "<<" | ">>" => {
            r.lo >= 0
                && r.hi < t.bits as i128
                && (t.unsigned || l.lo >= 0)
                && (op != "<<" || t.unsigned || fits(l.hi.checked_shl(r.hi as u32)))
        }
        _ => true,
    }
}

fn interval_binary(op: &str, l: Range, r: Range, t: IntType) -> Range {
    let comparison = match op {
        "==" if l.hi < r.lo || r.hi < l.lo => Some(false),
        "==" if l.singleton().is_some() && l == r => Some(true),
        "!=" if l.hi < r.lo || r.hi < l.lo => Some(true),
        "!=" if l.singleton().is_some() && l == r => Some(false),
        "<" if l.hi < r.lo => Some(true),
        "<" if l.lo >= r.hi => Some(false),
        "<=" if l.hi <= r.lo => Some(true),
        "<=" if l.lo > r.hi => Some(false),
        ">" if l.lo > r.hi => Some(true),
        ">" if l.hi <= r.lo => Some(false),
        ">=" if l.lo >= r.hi => Some(true),
        ">=" if l.hi < r.lo => Some(false),
        _ => None,
    };
    if matches!(op, "==" | "!=" | "<" | "<=" | ">" | ">=") {
        return comparison
            .map(|b| Range::one(b as i128))
            .unwrap_or(Range { lo: 0, hi: 1 });
    }
    let range = match op {
        "+" => {
            l.lo.checked_add(r.lo)
                .zip(l.hi.checked_add(r.hi))
                .map(|(lo, hi)| Range { lo, hi })
        }
        "-" => {
            l.lo.checked_sub(r.hi)
                .zip(l.hi.checked_sub(r.lo))
                .map(|(lo, hi)| Range { lo, hi })
        }
        "*" => {
            let values: Option<Vec<_>> = [l.lo, l.hi]
                .into_iter()
                .flat_map(|a| [r.lo, r.hi].into_iter().map(move |b| a.checked_mul(b)))
                .collect();
            values.map(|v| Range {
                lo: *v.iter().min().unwrap(),
                hi: *v.iter().max().unwrap(),
            })
        }
        "/" if r.singleton().is_some_and(|v| v != 0) => {
            let divisor = r.lo;
            l.lo.checked_div(divisor)
                .zip(l.hi.checked_div(divisor))
                .map(|(a, b)| Range {
                    lo: a.min(b),
                    hi: a.max(b),
                })
        }
        "%" if l.singleton().is_some() && r.singleton().is_some_and(|v| v != 0) => {
            l.lo.checked_rem(r.lo).map(Range::one)
        }
        "%" if r.singleton().is_some_and(|v| v != 0) => r.lo.checked_abs().map(|d| {
            let b = d - 1;
            Range {
                lo: if l.lo < 0 { l.lo.max(-b) } else { 0 },
                hi: if l.hi > 0 { l.hi.min(b) } else { 0 },
            }
        }),
        "&" if r.singleton().is_some_and(|v| v >= 0) => {
            Some(if l.lo >= 0 && l.singleton().is_some() {
                Range::one(l.lo & r.lo)
            } else {
                Range { lo: 0, hi: r.lo }
            })
        }
        "&" if l.singleton().is_some_and(|v| v >= 0) => Some(Range { lo: 0, hi: l.lo }),
        "|" | "^"
            if l.lo >= 0 && r.lo >= 0 && l.singleton().is_some() && r.singleton().is_some() =>
        {
            Some(Range::one(if op == "|" {
                l.lo | r.lo
            } else {
                l.lo ^ r.lo
            }))
        }
        "|" | "^" if l.lo >= 0 && r.lo >= 0 => {
            let high = l.hi.max(r.hi) as u128;
            let bits = 128 - high.leading_zeros();
            (bits < 127).then(|| Range {
                lo: 0,
                hi: (1i128 << bits) - 1,
            })
        }
        "<<" if r.singleton().is_some_and(|v| v >= 0 && v < t.bits as i128) && l.lo >= 0 => {
            l.lo.checked_shl(r.lo as u32)
                .zip(l.hi.checked_shl(r.lo as u32))
                .map(|(lo, hi)| Range { lo, hi })
        }
        ">>" if r.singleton().is_some_and(|v| v >= 0 && v < t.bits as i128) && l.lo >= 0 => {
            Some(Range {
                lo: l.lo >> r.lo,
                hi: l.hi >> r.lo,
            })
        }
        _ => None,
    };
    range.map(|r| convert(r, t)).unwrap_or(t.bounds)
}

#[cfg(test)]
mod unit {
    use super::*;
    #[test]
    fn typed_interval_transfer_respects_wrap_and_negative_remainders() {
        let signed = int_type("int").unwrap();
        let unsigned = int_type("unsigned int").unwrap();
        assert_eq!(
            interval_binary("+", Range::one(4294967295), Range::one(1), unsigned),
            Range::one(0)
        );
        assert_eq!(
            interval_binary("+", Range::one(2147483647), Range::one(1), signed),
            signed.bounds
        );
        assert_eq!(
            interval_binary("%", Range { lo: -10, hi: 10 }, Range::one(2), signed),
            Range { lo: -1, hi: 1 }
        );
        assert_eq!(
            interval_binary("&", signed.bounds, Range::one(1), signed),
            Range { lo: 0, hi: 1 }
        );
        assert_eq!(convert(Range { lo: -1, hi: 1 }, unsigned), unsigned.bounds);
        assert!(int_type("char").is_none());
        assert!(int_type("volatile int").is_none());
    }
}
