//! A deliberately small, source-only Rust advisory adapter.
//!
//! Parsing, Rust typing and Rust definedness own admission. The shared integer
//! search is only a candidate generator; its C evidence is never a Rust proof.
//! No compiler, build script, macro, user program or instrumentation is run.

use super::domain::{Domain, FINITE_LIMIT};
use super::nversion::{self, BinaryOp, CIntType, Expr, UnaryOp};
use super::{AdviceReport, AdvisorOptions, Finding, RangeSite, SourceLocation};
use crate::sha256;
use anyhow::{ensure, Result};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

const MAX_TOKENS: usize = 250_000;
const MAX_DEPTH: usize = 64;
const MAX_NODES: usize = 256;
const MAX_FUNCTIONS: usize = 4096;
const MAX_BINDINGS: usize = 4096;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Ty {
    Bool,
    I32,
    U32,
    I64,
    U64,
}

impl Ty {
    fn parse(s: &str) -> Option<Self> {
        Some(match s {
            "bool" => Self::Bool,
            "i32" => Self::I32,
            "u32" => Self::U32,
            "i64" => Self::I64,
            "u64" => Self::U64,
            _ => return None,
        })
    }
    fn name(self) -> &'static str {
        match self {
            Self::Bool => "bool",
            Self::I32 => "i32",
            Self::U32 => "u32",
            Self::I64 => "i64",
            Self::U64 => "u64",
        }
    }
    fn bits(self) -> u32 {
        match self {
            Self::Bool => 1,
            Self::I32 | Self::U32 => 32,
            _ => 64,
        }
    }
    fn signed(self) -> bool {
        matches!(self, Self::I32 | Self::I64)
    }
    fn bounds(self) -> (i128, i128) {
        if self.signed() {
            let n = 1i128 << (self.bits() - 1);
            (-n, n - 1)
        } else {
            (0, (1i128 << self.bits()) - 1)
        }
    }
    fn contains(self, n: i128) -> bool {
        let (lo, hi) = self.bounds();
        lo <= n && n <= hi
    }
    fn full(self) -> Domain {
        let (lo, hi) = self.bounds();
        Domain::interval(lo, hi, self.bits(), self.signed())
    }
    fn carrier(self) -> CIntType {
        match self {
            Self::Bool | Self::I32 => CIntType::I32,
            Self::U32 => CIntType::U32,
            Self::I64 => CIntType::I64,
            Self::U64 => CIntType::U64,
        }
    }
    fn from_carrier(ty: CIntType) -> Self {
        match ty {
            CIntType::I32 => Self::I32,
            CIntType::U32 => Self::U32,
            CIntType::I64 | CIntType::I64LongLong => Self::I64,
            CIntType::U64 | CIntType::U64LongLong => Self::U64,
        }
    }
}

#[derive(Clone, Copy, Debug)]
struct Span {
    start: usize,
    end: usize,
}
impl Span {
    fn through(self, other: Self) -> Self {
        Self {
            start: self.start,
            end: other.end,
        }
    }
}

#[derive(Clone, Debug)]
struct Token {
    text: String,
    span: Span,
}

fn lex(source: &str) -> std::result::Result<Vec<Token>, String> {
    let b = source.as_bytes();
    let mut i = 0;
    let mut out = Vec::new();
    while i < b.len() {
        if out.len() >= MAX_TOKENS {
            return Err("Rust token budget exceeded".into());
        }
        if b[i].is_ascii_whitespace() {
            i += 1;
            continue;
        }
        if b[i..].starts_with(b"//") {
            while i < b.len() && b[i] != b'\n' {
                i += 1;
            }
            continue;
        }
        if b[i..].starts_with(b"/*") {
            i += 2;
            let mut depth = 1usize;
            while i < b.len() && depth > 0 {
                if b[i..].starts_with(b"/*") {
                    depth += 1;
                    if depth > MAX_DEPTH {
                        return Err("nested comment budget exceeded".into());
                    }
                    i += 2;
                } else if b[i..].starts_with(b"*/") {
                    depth -= 1;
                    i += 2;
                } else {
                    i += 1;
                }
            }
            if depth != 0 {
                return Err("unterminated block comment".into());
            }
            continue;
        }
        let start = i;
        // Consume complete raw/ordinary literals so braces or fn tokens inside
        // unsupported strings can never be mistaken for source structure.
        let raw_start = if b[i] == b'r' {
            Some(i + 1)
        } else if b[i..].starts_with(b"br") || b[i..].starts_with(b"cr") {
            Some(i + 2)
        } else {
            None
        };
        if let Some(mut p) = raw_start {
            let h = p;
            while p < b.len() && b[p] == b'#' {
                p += 1;
            }
            if p < b.len() && b[p] == b'"' {
                let hashes = p - h;
                p += 1;
                let mut found = false;
                while p < b.len() {
                    if b[p] == b'"'
                        && p + 1 + hashes <= b.len()
                        && b[p + 1..p + 1 + hashes].iter().all(|&x| x == b'#')
                    {
                        p += 1 + hashes;
                        found = true;
                        break;
                    }
                    p += 1;
                }
                if !found {
                    return Err("unterminated raw string".into());
                }
                i = p;
                out.push(Token {
                    text: "<unsupported-literal>".into(),
                    span: Span { start, end: i },
                });
                continue;
            }
        }
        if b[i] == b'"'
            || b[i] == b'\''
            || ((b[i] == b'b' || b[i] == b'c') && b.get(i + 1) == Some(&b'"'))
        {
            if b[i] != b'"' && b[i] != b'\'' {
                i += 1;
            }
            let quote = b[i];
            i += 1;
            let mut found = false;
            while i < b.len() {
                if b[i] == b'\\' {
                    i = (i + 2).min(b.len());
                } else if b[i] == quote {
                    i += 1;
                    found = true;
                    break;
                } else {
                    i += 1;
                }
            }
            if !found {
                return Err("unterminated or unsupported quoted token/lifetime".into());
            }
            out.push(Token {
                text: "<unsupported-literal>".into(),
                span: Span { start, end: i },
            });
            continue;
        }
        if b[i].is_ascii_alphabetic() || b[i] == b'_' || b[i].is_ascii_digit() {
            i += 1;
            while i < b.len() && (b[i].is_ascii_alphanumeric() || b[i] == b'_') {
                i += 1;
            }
        } else {
            if !b[i].is_ascii() {
                return Err("non-ASCII identifiers are outside the admitted subset".into());
            }
            if i + 1 < b.len()
                && [
                    b"->", b"&&", b"||", b"==", b"!=", b"<=", b">=", b"<<", b">>", b"::", b"..",
                    b"+=", b"-=", b"*=", b"/=", b"%=", b"&=", b"|=", b"^=",
                ]
                .iter()
                .any(|p| b[i..].starts_with(*p))
            {
                i += 2;
            } else {
                i += 1;
            }
        }
        out.push(Token {
            text: source[start..i].into(),
            span: Span { start, end: i },
        });
        if out.len() > MAX_TOKENS {
            return Err("Rust token budget exceeded".into());
        }
    }
    Ok(out)
}

#[derive(Clone, Debug)]
enum RawKind {
    Name(String),
    Literal(String),
    Unary(UnaryOp, Box<Raw>),
    Binary(BinaryOp, Box<Raw>, Box<Raw>),
    Cast(Ty, Box<Raw>),
}
#[derive(Clone, Debug)]
struct Raw {
    kind: RawKind,
    span: Span,
    grouped: bool,
}
#[derive(Clone, Debug)]
enum Kind {
    Var(usize),
    Constant(i128),
    Unary(UnaryOp, Box<Node>),
    Binary(BinaryOp, Box<Node>, Box<Node>),
    Cast(Box<Node>),
    Conditional(Box<Node>, Box<Node>, Box<Node>),
}
#[derive(Clone, Debug)]
struct Node {
    kind: Kind,
    ty: Ty,
    span: Span,
}
impl Node {
    fn constant(n: i128, ty: Ty, span: Span) -> Self {
        Self {
            kind: Kind::Constant(n),
            ty,
            span,
        }
    }
    fn symbols(&self, symbols: &mut BTreeSet<usize>) {
        match &self.kind {
            Kind::Var(id) => {
                symbols.insert(*id);
            }
            Kind::Constant(_) => {}
            Kind::Unary(_, x) | Kind::Cast(x) => x.symbols(symbols),
            Kind::Binary(_, a, b) => {
                a.symbols(symbols);
                b.symbols(symbols);
            }
            Kind::Conditional(a, b, c) => {
                a.symbols(symbols);
                b.symbols(symbols);
                c.symbols(symbols);
            }
        }
    }
    fn node_count(&self) -> usize {
        match &self.kind {
            Kind::Var(_) | Kind::Constant(_) => 1,
            Kind::Unary(_, a) | Kind::Cast(a) => 1 + a.node_count(),
            Kind::Binary(_, a, b) => 1 + a.node_count() + b.node_count(),
            Kind::Conditional(a, b, c) => 1 + a.node_count() + b.node_count() + c.node_count(),
        }
    }
}

#[derive(Clone, Debug)]
struct Binding {
    name: String,
    ty: Ty,
    mutable: bool,
    span: Span,
    parameter: bool,
    reads: usize,
}
#[derive(Clone, Debug)]
enum Statement {
    Let(usize, Node),
    Assign(usize, Node),
    If(Node, Vec<Statement>, Vec<Statement>),
    Return(Option<Node>),
    Expr(Node),
    Tail(Node),
}
#[derive(Clone, Debug)]
struct Function {
    name: String,
    bindings: Vec<Binding>,
    body: Vec<Statement>,
}

struct Parser<'a> {
    tokens: &'a [Token],
    index: usize,
    bindings: Vec<Binding>,
    active: HashMap<String, usize>,
    ever: HashSet<String>,
    result: Option<Ty>,
}

fn identifier(s: &str) -> bool {
    s.as_bytes()
        .first()
        .is_some_and(|b| b.is_ascii_alphabetic() || *b == b'_')
        && s.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_')
        && ![
            "as", "async", "await", "break", "const", "continue", "crate", "dyn", "else", "enum",
            "extern", "false", "fn", "for", "if", "impl", "in", "let", "loop", "match", "mod",
            "move", "mut", "pub", "ref", "return", "self", "Self", "static", "struct", "super",
            "trait", "true", "type", "unsafe", "use", "where", "while", "yield", "gen", "_",
            "abstract", "become", "box", "do", "final", "macro", "override", "priv", "try",
            "typeof", "unsized", "virtual",
        ]
        .contains(&s)
}

impl<'a> Parser<'a> {
    fn new(tokens: &'a [Token]) -> Self {
        Self {
            tokens,
            index: 0,
            bindings: vec![],
            active: HashMap::new(),
            ever: HashSet::new(),
            result: None,
        }
    }
    fn at(&self, s: &str) -> bool {
        self.tokens.get(self.index).is_some_and(|t| t.text == s)
    }
    fn take(&mut self, s: &str) -> bool {
        if self.at(s) {
            self.index += 1;
            true
        } else {
            false
        }
    }
    fn token(&mut self) -> std::result::Result<Token, String> {
        let t = self
            .tokens
            .get(self.index)
            .cloned()
            .ok_or("unexpected end of function")?;
        self.index += 1;
        Ok(t)
    }
    fn need(&mut self, s: &str) -> std::result::Result<(), String> {
        if self.take(s) {
            Ok(())
        } else {
            Err(format!(
                "expected {s}; unsupported or invalid Rust syntax at byte {}",
                self.tokens.get(self.index).map_or(0, |t| t.span.start)
            ))
        }
    }
    fn name(&mut self) -> std::result::Result<Token, String> {
        let t = self.token()?;
        if identifier(&t.text) {
            Ok(t)
        } else {
            Err(format!("unsupported binding/name {}", t.text))
        }
    }
    fn ty(&mut self) -> std::result::Result<Ty, String> {
        let t = self.token()?;
        Ty::parse(&t.text).ok_or_else(|| format!("unsupported Rust type {}", t.text))
    }
    fn add_binding(
        &mut self,
        name: Token,
        ty: Ty,
        mutable: bool,
        parameter: bool,
    ) -> std::result::Result<usize, String> {
        if self.bindings.len() >= MAX_BINDINGS {
            return Err("binding budget exceeded".into());
        }
        if !self.ever.insert(name.text.clone()) {
            return Err(
                "shadowing and duplicate binding names are outside the admitted subset".into(),
            );
        }
        let id = self.bindings.len();
        self.active.insert(name.text.clone(), id);
        self.bindings.push(Binding {
            name: name.text,
            ty,
            mutable,
            span: name.span,
            parameter,
            reads: 0,
        });
        Ok(id)
    }
    fn function(mut self) -> std::result::Result<Function, String> {
        self.take("pub");
        self.need("fn")?;
        let name = self.name()?;
        self.need("(")?;
        while !self.at(")") {
            let mutable = self.take("mut");
            let n = self.name()?;
            self.need(":")?;
            let ty = self.ty()?;
            self.add_binding(n, ty, mutable, true)?;
            if !self.take(",") {
                break;
            }
        }
        self.need(")")?;
        if self.take("->") {
            self.result = Some(self.ty()?);
        }
        let body = self.block(true, 0)?;
        if self.index != self.tokens.len() {
            return Err("trailing tokens after function".into());
        }
        if self.result.is_some() && !always_returns(&body) {
            return Err(
                "non-unit function does not have a supported total return structure".into(),
            );
        }
        Ok(Function {
            name: name.text,
            bindings: self.bindings,
            body,
        })
    }
    fn expression(&mut self, min: u8, depth: usize) -> std::result::Result<Raw, String> {
        if depth > MAX_DEPTH {
            return Err("expression depth budget exceeded".into());
        }
        let t = self.token()?;
        let mut node = if t.text == "(" {
            let mut n = self.expression(0, depth + 1)?;
            self.need(")")?;
            n.span = t.span.through(self.tokens[self.index - 1].span);
            n.grouped = true;
            n
        } else if t.text == "!" || t.text == "-" {
            let n = self.expression(11, depth + 1)?;
            let span = t.span.through(n.span);
            Raw {
                kind: RawKind::Unary(
                    if t.text == "!" {
                        UnaryOp::LogicalNot
                    } else {
                        UnaryOp::Negate
                    },
                    Box::new(n),
                ),
                span,
                grouped: false,
            }
        } else if t.text == "true" || t.text == "false" || t.text.as_bytes()[0].is_ascii_digit() {
            Raw {
                kind: RawKind::Literal(t.text),
                span: t.span,
                grouped: false,
            }
        } else if identifier(&t.text) {
            Raw {
                kind: RawKind::Name(t.text),
                span: t.span,
                grouped: false,
            }
        } else {
            return Err(format!(
                "unsupported expression token {} at byte {}",
                t.text, t.span.start
            ));
        };
        while self.index < self.tokens.len() {
            if self.at("as") && 10 >= min {
                self.index += 1;
                let ty = self.ty()?;
                let span = node.span.through(self.tokens[self.index - 1].span);
                node = Raw {
                    kind: RawKind::Cast(ty, Box::new(node)),
                    span,
                    grouped: false,
                };
                if raw_nodes(&node) > MAX_NODES {
                    return Err("expression node budget exceeded".into());
                }
                continue;
            }
            let Some((op, p)) = binary(&self.tokens[self.index].text) else {
                break;
            };
            if p < min {
                break;
            }
            if matches!(op, BinaryOp::Lt | BinaryOp::Shl)
                && !node.grouped
                && matches!(node.kind, RawKind::Cast(_, _))
            {
                return Err("Rust requires parentheses around this cast before < or <<".into());
            }
            self.index += 1;
            let right = self.expression(p + 1, depth + 1)?;
            let span = node.span.through(right.span);
            if p == 3
                && !node.grouped
                && matches!(&node.kind,RawKind::Binary(old,_,_) if comparison(*old))
            {
                return Err(
                    "unparenthesized/chained comparisons are outside the admitted subset".into(),
                );
            }
            node = Raw {
                kind: RawKind::Binary(op, Box::new(node), Box::new(right)),
                span,
                grouped: false,
            };
            if raw_nodes(&node) > MAX_NODES {
                return Err("expression node budget exceeded".into());
            }
        }
        if raw_nodes(&node) > MAX_NODES {
            return Err("expression node budget exceeded".into());
        }
        Ok(node)
    }
    fn typed(&mut self, expected: Option<Ty>) -> std::result::Result<Node, String> {
        let raw = self.expression(0, 0)?;
        let node = resolve(&raw, &self.active, &self.bindings, expected)?;
        let mut counts = Vec::new();
        read_bindings(&node, &mut counts);
        for id in counts {
            self.bindings[id].reads += 1;
        }
        Ok(node)
    }
    fn block(&mut self, tail: bool, depth: usize) -> std::result::Result<Vec<Statement>, String> {
        if depth > MAX_DEPTH {
            return Err("block depth budget exceeded".into());
        }
        self.need("{")?;
        let active = self.active.clone();
        let mut body = Vec::new();
        while !self.at("}") {
            if self.take(";") {
                continue;
            }
            if self.take("let") {
                let mutable = self.take("mut");
                let name = self.name()?;
                self.need(":")?;
                let ty = self.ty()?;
                self.need("=")?;
                let value = self.typed(Some(ty))?;
                self.need(";")?;
                let id = self.add_binding(name, ty, mutable, false)?;
                body.push(Statement::Let(id, value));
            } else if self.take("if") {
                let condition = self.typed(Some(Ty::Bool))?;
                let yes = self.block(false, depth + 1)?;
                let no = if self.take("else") {
                    self.block(false, depth + 1)?
                } else {
                    vec![]
                };
                body.push(Statement::If(condition, yes, no));
            } else if self.take("return") {
                let n = if self.at(";") {
                    if self.result.is_some() {
                        return Err("missing return value".into());
                    }
                    None
                } else {
                    let ty = self.result.ok_or("unit function returns a value")?;
                    Some(self.typed(Some(ty))?)
                };
                self.need(";")?;
                body.push(Statement::Return(n));
            } else if self
                .tokens
                .get(self.index + 1)
                .is_some_and(|t| t.text == "=")
            {
                let name = self.name()?;
                self.need("=")?;
                let id = *self
                    .active
                    .get(&name.text)
                    .ok_or("assignment to unknown binding")?;
                if !self.bindings[id].mutable {
                    return Err("assignment requires an explicitly mutable binding".into());
                }
                let n = self.typed(Some(self.bindings[id].ty))?;
                self.need(";")?;
                body.push(Statement::Assign(id, n));
            } else {
                let raw = self.expression(0, 0)?;
                let is_tail = self.at("}") && tail;
                let expected = if is_tail { self.result } else { None };
                if is_tail && expected.is_none() {
                    return Err("non-unit tail in a unit function".into());
                }
                let n = resolve(&raw, &self.active, &self.bindings, expected)?;
                let mut reads = Vec::new();
                read_bindings(&n, &mut reads);
                for id in reads {
                    self.bindings[id].reads += 1;
                }
                if is_tail {
                    body.push(Statement::Tail(n));
                } else {
                    self.need(";")?;
                    body.push(Statement::Expr(n));
                }
            }
        }
        self.need("}")?;
        self.active = active;
        Ok(body)
    }
}

#[derive(Debug)]
enum Fault {
    Budget,
    Semantic(&'static str),
    Unavailable,
}
impl Fault {
    fn reason(&self) -> &'static str {
        match self {
            Self::Budget => "evaluation work budget exhausted",
            Self::Semantic(s) => s,
            Self::Unavailable => "expression depends on more than the finite scalar binding",
        }
    }
}
struct Work {
    limit: usize,
    spent: usize,
    exhausted: bool,
}
impl Work {
    fn new(limit: usize) -> Self {
        Self {
            limit,
            spent: 0,
            exhausted: false,
        }
    }
    fn step(&mut self) -> std::result::Result<(), Fault> {
        if self.spent >= self.limit {
            self.exhausted = true;
            Err(Fault::Budget)
        } else {
            self.spent += 1;
            Ok(())
        }
    }
    fn remaining(&self) -> usize {
        self.limit.saturating_sub(self.spent)
    }
}

fn cast_value(value: i128, ty: Ty) -> i128 {
    let mask = (1u128 << ty.bits()) - 1;
    let raw = (value as u128) & mask;
    if ty.signed() && raw & (1u128 << (ty.bits() - 1)) != 0 {
        raw as i128 - (1i128 << ty.bits())
    } else {
        raw as i128
    }
}

/// Values carry their type in Node. Arithmetic is admitted only if it is
/// defined with overflow checks both enabled and disabled; shifts truncate
/// shifted-out bits as Rust specifies, while their counts are always checked.
fn evaluate(
    node: &Node,
    input: Option<(usize, i128)>,
    work: &mut Work,
) -> std::result::Result<i128, Fault> {
    work.step()?;
    let value = match &node.kind {
        Kind::Var(id) => input
            .filter(|(i, _)| i == id)
            .map(|(_, v)| v)
            .ok_or(Fault::Unavailable)?,
        Kind::Constant(value) => *value,
        Kind::Cast(a) => cast_value(evaluate(a, input, work)?, node.ty),
        Kind::Unary(op, a) => {
            let v = evaluate(a, input, work)?;
            match op {
                UnaryOp::LogicalNot => i128::from(v == 0),
                UnaryOp::BitNot => cast_value(!v, node.ty),
                UnaryOp::Negate => -v,
            }
        }
        Kind::Conditional(c, a, b) => {
            if evaluate(c, input, work)? != 0 {
                evaluate(a, input, work)?
            } else {
                evaluate(b, input, work)?
            }
        }
        Kind::Binary(op, a, b) => {
            let x = evaluate(a, input, work)?;
            if *op == BinaryOp::LogicalAnd && x == 0 {
                return Ok(0);
            }
            if *op == BinaryOp::LogicalOr && x != 0 {
                return Ok(1);
            }
            let y = evaluate(b, input, work)?;
            match op {
                BinaryOp::Add => x
                    .checked_add(y)
                    .ok_or(Fault::Semantic("Rust arithmetic overflow"))?,
                BinaryOp::Sub => x
                    .checked_sub(y)
                    .ok_or(Fault::Semantic("Rust arithmetic overflow"))?,
                BinaryOp::Mul => x
                    .checked_mul(y)
                    .ok_or(Fault::Semantic("Rust arithmetic overflow"))?,
                BinaryOp::Div | BinaryOp::Rem => {
                    if y == 0 {
                        return Err(Fault::Semantic("Rust division/remainder by zero"));
                    }
                    if a.ty.signed() && x == a.ty.bounds().0 && y == -1 {
                        return Err(Fault::Semantic("Rust signed division/remainder overflow"));
                    }
                    if *op == BinaryOp::Div {
                        x / y
                    } else {
                        x % y
                    }
                }
                BinaryOp::Shl | BinaryOp::Shr => {
                    if y < 0 || y >= a.ty.bits() as i128 {
                        return Err(Fault::Semantic(
                            "Rust shift count outside the operand width",
                        ));
                    }
                    if *op == BinaryOp::Shl {
                        let raw = ((x as u128) & ((1u128 << a.ty.bits()) - 1)) << (y as u32);
                        cast_value(raw as i128, a.ty)
                    } else if a.ty.signed() {
                        x >> (y as u32)
                    } else {
                        ((x as u128) >> (y as u32)) as i128
                    }
                }
                BinaryOp::BitAnd => cast_value(x & y, node.ty),
                BinaryOp::BitOr => cast_value(x | y, node.ty),
                BinaryOp::BitXor => cast_value(x ^ y, node.ty),
                BinaryOp::Eq => i128::from(x == y),
                BinaryOp::Ne => i128::from(x != y),
                BinaryOp::Lt => i128::from(x < y),
                BinaryOp::Le => i128::from(x <= y),
                BinaryOp::Gt => i128::from(x > y),
                BinaryOp::Ge => i128::from(x >= y),
                BinaryOp::LogicalAnd => i128::from(x != 0 && y != 0),
                BinaryOp::LogicalOr => i128::from(x != 0 || y != 0),
            }
        }
    };
    if !node.ty.contains(value) {
        Err(Fault::Semantic("Rust arithmetic overflow"))
    } else {
        Ok(value)
    }
}

fn carrier(node: &Node, symbol: usize) -> Option<Expr> {
    Some(match &node.kind {
        Kind::Var(id) if *id == symbol => Expr::Var,
        Kind::Var(_) => return None,
        Kind::Constant(n) => Expr::constant(*n, node.ty.carrier()),
        Kind::Unary(op, a) => Expr::unary(*op, carrier(a, symbol)?),
        Kind::Binary(op, a, b) => Expr::binary(*op, carrier(a, symbol)?, carrier(b, symbol)?),
        Kind::Cast(a) => Expr::cast(node.ty.carrier(), carrier(a, symbol)?),
        Kind::Conditional(c, a, b) => Expr::conditional(
            carrier(c, symbol)?,
            carrier(a, symbol)?,
            carrier(b, symbol)?,
        ),
    })
}

fn cast_node(node: Node, ty: Ty) -> Node {
    if node.ty == ty {
        node
    } else {
        // Cast the value once instead of retaining a runtime-shaped cast around
        // every generator literal. Integer destinations use Rust's truncating
        // conversion; a numeric value must never be folded into a bool literal.
        if ty != Ty::Bool {
            if let Kind::Constant(value) = node.kind {
                return Node::constant(cast_value(value, ty), ty, node.span);
            }
        }
        let span = node.span;
        Node {
            kind: Kind::Cast(Box::new(node)),
            ty,
            span,
        }
    }
}
fn truth(node: Node) -> Node {
    if node.ty == Ty::Bool {
        node
    } else if let Kind::Constant(n) = node.kind {
        Node::constant(i128::from(n != 0), Ty::Bool, node.span)
    } else {
        let span = node.span;
        let zero = Node::constant(0, node.ty, span);
        Node {
            kind: Kind::Binary(BinaryOp::Ne, Box::new(node), Box::new(zero)),
            ty: Ty::Bool,
            span,
        }
    }
}
fn logical_not(node: Node) -> Node {
    let span = node.span;
    if node.ty != Ty::Bool {
        let zero = Node::constant(0, node.ty, span);
        return Node {
            kind: Kind::Binary(BinaryOp::Eq, Box::new(node), Box::new(zero)),
            ty: Ty::Bool,
            span,
        };
    }
    match node.kind {
        Kind::Constant(n) => Node::constant(i128::from(n == 0), Ty::Bool, span),
        Kind::Unary(UnaryOp::LogicalNot, a) => *a,
        Kind::Binary(op, a, b) if comparison(op) => Node {
            kind: Kind::Binary(invert(op), a, b),
            ty: Ty::Bool,
            span,
        },
        kind => Node {
            kind: Kind::Unary(
                UnaryOp::LogicalNot,
                Box::new(Node {
                    kind,
                    ty: Ty::Bool,
                    span,
                }),
            ),
            ty: Ty::Bool,
            span,
        },
    }
}

// Interpret the generator's typed integer IR into Rust syntax. C promotions
// become explicit Rust casts; boolean results stay bool. Every resulting tree
// is re-parsed and independently compared before any advice is emitted.
fn adapt(expr: &Expr, variable: Ty) -> std::result::Result<Node, String> {
    let span = Span { start: 0, end: 0 };
    let carrier_ty = Ty::from_carrier(
        expr.infer_type(variable.carrier())
            .map_err(|e| e.to_string())?,
    );
    Ok(match expr {
        Expr::Var => Node {
            kind: Kind::Var(0),
            ty: variable,
            span,
        },
        Expr::Constant { value, ty } => Node::constant(*value, Ty::from_carrier(*ty), span),
        Expr::Unary { op, operand } => {
            let a = adapt(operand, variable)?;
            if *op == UnaryOp::LogicalNot {
                logical_not(a)
            } else {
                if *op == UnaryOp::Negate && !carrier_ty.signed() {
                    return Err("candidate uses unsigned unary negation".into());
                }
                Node {
                    kind: Kind::Unary(*op, Box::new(cast_node(a, carrier_ty))),
                    ty: carrier_ty,
                    span,
                }
            }
        }
        Expr::Cast { ty, operand } => cast_node(adapt(operand, variable)?, Ty::from_carrier(*ty)),
        Expr::Binary { op, left, right } => {
            let mut a = adapt(left, variable)?;
            let mut b = adapt(right, variable)?;
            let ty = if matches!(op, BinaryOp::LogicalAnd | BinaryOp::LogicalOr) {
                a = truth(a);
                b = truth(b);
                Ty::Bool
            } else if comparison(*op) {
                let common = Expr::binary(BinaryOp::Add, (**left).clone(), (**right).clone())
                    .infer_type(variable.carrier())
                    .map_err(|e| e.to_string())?;
                a = cast_node(a, Ty::from_carrier(common));
                b = cast_node(b, Ty::from_carrier(common));
                Ty::Bool
            } else if matches!(op, BinaryOp::Shl | BinaryOp::Shr) {
                a = cast_node(a, carrier_ty);
                let rt = right
                    .infer_type(variable.carrier())
                    .map_err(|e| e.to_string())?;
                b = cast_node(b, Ty::from_carrier(rt));
                carrier_ty
            } else {
                a = cast_node(a, carrier_ty);
                b = cast_node(b, carrier_ty);
                carrier_ty
            };
            Node {
                kind: Kind::Binary(*op, Box::new(a), Box::new(b)),
                ty,
                span,
            }
        }
        Expr::Conditional {
            condition,
            then_expr,
            else_expr,
        } => Node {
            kind: Kind::Conditional(
                Box::new(truth(adapt(condition, variable)?)),
                Box::new(cast_node(adapt(then_expr, variable)?, carrier_ty)),
                Box::new(cast_node(adapt(else_expr, variable)?, carrier_ty)),
            ),
            ty: carrier_ty,
            span,
        },
    })
}

fn spelling(op: BinaryOp) -> &'static str {
    match op {
        BinaryOp::Add => "+",
        BinaryOp::Sub => "-",
        BinaryOp::Mul => "*",
        BinaryOp::Div => "/",
        BinaryOp::Rem => "%",
        BinaryOp::Shl => "<<",
        BinaryOp::Shr => ">>",
        BinaryOp::BitAnd => "&",
        BinaryOp::BitOr => "|",
        BinaryOp::BitXor => "^",
        BinaryOp::Eq => "==",
        BinaryOp::Ne => "!=",
        BinaryOp::Lt => "<",
        BinaryOp::Le => "<=",
        BinaryOp::Gt => ">",
        BinaryOp::Ge => ">=",
        BinaryOp::LogicalAnd => "&&",
        BinaryOp::LogicalOr => "||",
    }
}
fn render(node: &Node, symbol: &str, suffix: bool) -> (String, u8) {
    match &node.kind {
        Kind::Var(_) => (symbol.into(), 13),
        Kind::Constant(n) => {
            if node.ty == Ty::Bool {
                (if *n == 0 { "false" } else { "true" }.into(), 13)
            } else {
                (
                    format!("{n}{}", if suffix { node.ty.name() } else { "" }),
                    if *n < 0 { 11 } else { 13 },
                )
            }
        }
        Kind::Unary(op, a) => {
            let (s, p) = render(a, symbol, suffix);
            let s = if p < 11 || (*op == UnaryOp::Negate && s.starts_with('-')) {
                format!("({s})")
            } else {
                s
            };
            (
                format!("{}{s}", if *op == UnaryOp::Negate { "-" } else { "!" }),
                11,
            )
        }
        Kind::Cast(a) => {
            let (s, p) = render(a, symbol, suffix);
            let s = if p < 10 { format!("({s})") } else { s };
            (format!("{s} as {}", node.ty.name()), 10)
        }
        Kind::Binary(op, a, b) => {
            let p = binary(spelling(*op)).unwrap().1;
            let (l, lp) = render(a, symbol, suffix);
            let (r, rp) = render(b, symbol, suffix);
            let l = if lp < p || (p == 3 && lp == 3) || matches!(a.kind, Kind::Cast(_)) {
                format!("({l})")
            } else {
                l
            };
            let r = if rp <= p || matches!(b.kind, Kind::Cast(_)) {
                format!("({r})")
            } else {
                r
            };
            (format!("{l}{}{r}", spelling(*op)), p)
        }
        Kind::Conditional(c, a, b) => {
            let (c, _) = render(c, symbol, suffix);
            let (a, _) = render(a, symbol, suffix);
            let (b, _) = render(b, symbol, suffix);
            (format!("if {c}{{{a}}}else{{{b}}}"), 0)
        }
    }
}

fn parse_candidate(source: &str, symbol: &str, ty: Ty) -> std::result::Result<Node, String> {
    let tokens = lex(source)?;
    let mut parser = Parser::new(&tokens);
    parser.add_binding(
        Token {
            text: symbol.into(),
            span: Span {
                start: 0,
                end: symbol.len(),
            },
        },
        ty,
        false,
        true,
    )?;
    let raw = parser.expression(0, 0)?;
    if parser.index != tokens.len() {
        return Err("generated Rust syntax is outside the admitted parser".into());
    }
    resolve(&raw, &parser.active, &parser.bindings, None)
}

fn always_returns(body: &[Statement]) -> bool {
    body.iter().any(|s| match s {
        Statement::Return(_) | Statement::Tail(_) => true,
        Statement::If(_, a, b) => always_returns(a) && always_returns(b),
        _ => false,
    })
}
fn raw_nodes(n: &Raw) -> usize {
    match &n.kind {
        RawKind::Name(_) | RawKind::Literal(_) => 1,
        RawKind::Unary(_, a) | RawKind::Cast(_, a) => 1 + raw_nodes(a),
        RawKind::Binary(_, a, b) => 1 + raw_nodes(a) + raw_nodes(b),
    }
}
fn read_bindings(n: &Node, out: &mut Vec<usize>) {
    match &n.kind {
        Kind::Var(id) => out.push(*id),
        Kind::Constant(_) => {}
        Kind::Unary(_, a) | Kind::Cast(a) => read_bindings(a, out),
        Kind::Binary(_, a, b) => {
            read_bindings(a, out);
            read_bindings(b, out);
        }
        Kind::Conditional(a, b, c) => {
            read_bindings(a, out);
            read_bindings(b, out);
            read_bindings(c, out);
        }
    }
}
fn comparison(op: BinaryOp) -> bool {
    matches!(
        op,
        BinaryOp::Eq | BinaryOp::Ne | BinaryOp::Lt | BinaryOp::Le | BinaryOp::Gt | BinaryOp::Ge
    )
}
fn binary(s: &str) -> Option<(BinaryOp, u8)> {
    Some(match s {
        "||" => (BinaryOp::LogicalOr, 1),
        "&&" => (BinaryOp::LogicalAnd, 2),
        "==" => (BinaryOp::Eq, 3),
        "!=" => (BinaryOp::Ne, 3),
        "<" => (BinaryOp::Lt, 3),
        "<=" => (BinaryOp::Le, 3),
        ">" => (BinaryOp::Gt, 3),
        ">=" => (BinaryOp::Ge, 3),
        "|" => (BinaryOp::BitOr, 4),
        "^" => (BinaryOp::BitXor, 5),
        "&" => (BinaryOp::BitAnd, 6),
        "<<" => (BinaryOp::Shl, 7),
        ">>" => (BinaryOp::Shr, 7),
        "+" => (BinaryOp::Add, 8),
        "-" => (BinaryOp::Sub, 8),
        "*" => (BinaryOp::Mul, 9),
        "/" => (BinaryOp::Div, 9),
        "%" => (BinaryOp::Rem, 9),
        _ => return None,
    })
}

fn literal(s: &str) -> std::result::Result<(i128, Option<Ty>), String> {
    if s == "true" || s == "false" {
        return Ok((i128::from(s == "true"), Some(Ty::Bool)));
    }
    let mut s = s.to_owned();
    let mut ty = None;
    for suffix in ["i32", "u32", "i64", "u64"] {
        if s.ends_with(suffix) {
            s.truncate(s.len() - suffix.len());
            ty = Ty::parse(suffix);
            break;
        }
    }
    let (radix, digits) = if let Some(d) = s.strip_prefix("0x") {
        (16, d)
    } else if let Some(d) = s.strip_prefix("0b") {
        (2, d)
    } else if let Some(d) = s.strip_prefix("0o") {
        (8, d)
    } else {
        (10, s.as_str())
    };
    let n = i128::from_str_radix(&digits.replace('_', ""), radix)
        .map_err(|_| "unsupported or invalid integer literal")?;
    Ok((n, ty))
}

fn hint(
    raw: &Raw,
    active: &HashMap<String, usize>,
    bindings: &[Binding],
) -> std::result::Result<Option<Ty>, String> {
    Ok(match &raw.kind {
        RawKind::Name(n) => {
            Some(bindings[*active.get(n).ok_or("unknown binding or function name")?].ty)
        }
        RawKind::Literal(s) => literal(s)?.1,
        RawKind::Cast(ty, _) => Some(*ty),
        RawKind::Unary(_, a) => hint(a, active, bindings)?,
        RawKind::Binary(op, a, b) => {
            if comparison(*op) || matches!(op, BinaryOp::LogicalAnd | BinaryOp::LogicalOr) {
                Some(Ty::Bool)
            } else if matches!(op, BinaryOp::Shl | BinaryOp::Shr) {
                hint(a, active, bindings)?
            } else {
                hint(a, active, bindings)?.or(hint(b, active, bindings)?)
            }
        }
    })
}

fn resolve(
    raw: &Raw,
    active: &HashMap<String, usize>,
    bindings: &[Binding],
    expected: Option<Ty>,
) -> std::result::Result<Node, String> {
    let node = match &raw.kind {
        RawKind::Name(name) => {
            let id = *active
                .get(name)
                .ok_or("unknown binding or unsupported call")?;
            Node {
                kind: Kind::Var(id),
                ty: bindings[id].ty,
                span: raw.span,
            }
        }
        RawKind::Literal(s) => {
            let (n, suffix) = literal(s)?;
            let ty = suffix.or(expected).unwrap_or(Ty::I32);
            if ty == Ty::Bool && suffix != Some(Ty::Bool) {
                return Err("Rust integer literals cannot infer the bool type".into());
            }
            if !ty.contains(n) {
                return Err("literal is outside its Rust type".into());
            }
            Node::constant(n, ty, raw.span)
        }
        RawKind::Unary(op, a) => {
            let ty = hint(a, active, bindings)?.or(expected).unwrap_or(Ty::I32);
            if *op == UnaryOp::Negate {
                if !ty.signed() {
                    return Err("Rust unary minus requires a signed integer in this subset".into());
                }
                if let RawKind::Literal(s) = &a.kind {
                    let (n, suffix) = literal(s)?;
                    if suffix.is_none_or(|t| t == ty) && n == -ty.bounds().0 {
                        if expected.is_some_and(|t| t != ty) {
                            return Err("Rust literal type does not match the required type".into());
                        }
                        return Ok(Node::constant(-n, ty, raw.span));
                    }
                }
            }
            let operand = resolve(a, active, bindings, Some(ty))?;
            let op = if *op == UnaryOp::LogicalNot && ty != Ty::Bool {
                UnaryOp::BitNot
            } else {
                *op
            };
            Node {
                kind: Kind::Unary(op, Box::new(operand)),
                ty,
                span: raw.span,
            }
        }
        RawKind::Cast(ty, a) => {
            if *ty == Ty::Bool {
                return Err("casts to bool are outside the admitted Rust subset".into());
            }
            let operand = resolve(a, active, bindings, None)?;
            Node {
                kind: Kind::Cast(Box::new(operand)),
                ty: *ty,
                span: raw.span,
            }
        }
        RawKind::Binary(op, a, b) => {
            let logical = matches!(op, BinaryOp::LogicalAnd | BinaryOp::LogicalOr);
            let shift = matches!(op, BinaryOp::Shl | BinaryOp::Shr);
            let child_ty = if logical {
                Ty::Bool
            } else {
                hint(a, active, bindings)?
                    .or(if shift {
                        None
                    } else {
                        hint(b, active, bindings)?
                    })
                    .or(if comparison(*op) { None } else { expected })
                    .unwrap_or(Ty::I32)
            };
            let left = resolve(a, active, bindings, Some(child_ty))?;
            let right = resolve(
                b,
                active,
                bindings,
                if shift { None } else { Some(child_ty) },
            )?;
            if shift {
                if left.ty == Ty::Bool || right.ty == Ty::Bool {
                    return Err("Rust shift operands must be integers".into());
                }
            } else if left.ty != right.ty {
                return Err("Rust integer types cannot be implicitly mixed".into());
            }
            if child_ty == Ty::Bool
                && !logical
                && !comparison(*op)
                && !matches!(op, BinaryOp::BitAnd | BinaryOp::BitOr | BinaryOp::BitXor)
            {
                return Err("Rust bool has no arithmetic operators".into());
            }
            Node {
                kind: Kind::Binary(*op, Box::new(left), Box::new(right)),
                ty: if comparison(*op) || logical {
                    Ty::Bool
                } else {
                    child_ty
                },
                span: raw.span,
            }
        }
    };
    if expected.is_some_and(|ty| ty != node.ty) {
        return Err("Rust expression type does not match the declared/required type".into());
    }
    Ok(node)
}

type Environment = Vec<Option<Domain>>;
fn join(a: Option<Environment>, b: Option<Environment>) -> Option<Environment> {
    match (a, b) {
        (None, x) | (x, None) => x,
        (Some(a), Some(b)) => Some(
            a.into_iter()
                .zip(b)
                .map(|(x, y)| match (x, y) {
                    (Some(x), Some(y)) => Some(x.union(&y)),
                    _ => None,
                })
                .collect(),
        ),
    }
}

fn constant(node: &Node) -> Option<i128> {
    if let Kind::Constant(n) = node.kind {
        Some(n)
    } else {
        None
    }
}
fn variable(node: &Node) -> Option<usize> {
    if let Kind::Var(id) = node.kind {
        Some(id)
    } else {
        None
    }
}
fn invert(op: BinaryOp) -> BinaryOp {
    match op {
        BinaryOp::Eq => BinaryOp::Ne,
        BinaryOp::Ne => BinaryOp::Eq,
        BinaryOp::Lt => BinaryOp::Ge,
        BinaryOp::Le => BinaryOp::Gt,
        BinaryOp::Gt => BinaryOp::Le,
        BinaryOp::Ge => BinaryOp::Lt,
        _ => op,
    }
}
fn reverse(op: BinaryOp) -> BinaryOp {
    match op {
        BinaryOp::Lt => BinaryOp::Gt,
        BinaryOp::Le => BinaryOp::Ge,
        BinaryOp::Gt => BinaryOp::Lt,
        BinaryOp::Ge => BinaryOp::Le,
        _ => op,
    }
}

fn refine(node: &Node, truth: bool, mut env: Environment, work: &mut Work) -> Option<Environment> {
    if work.step().is_err() {
        return Some(env);
    }
    match &node.kind {
        Kind::Constant(n) => return ((*n != 0) == truth).then_some(env),
        Kind::Unary(UnaryOp::LogicalNot, a) => return refine(a, !truth, env, work),
        Kind::Binary(BinaryOp::LogicalAnd, a, b) => {
            return if truth {
                refine(a, true, env, work).and_then(|e| refine(b, true, e, work))
            } else {
                let left = refine(a, false, env.clone(), work);
                let right = refine(a, true, env, work).and_then(|e| refine(b, false, e, work));
                join(left, right)
            };
        }
        Kind::Binary(BinaryOp::LogicalOr, a, b) => {
            return if !truth {
                refine(a, false, env, work).and_then(|e| refine(b, false, e, work))
            } else {
                let left = refine(a, true, env.clone(), work);
                let right = refine(a, false, env, work).and_then(|e| refine(b, true, e, work));
                join(left, right)
            };
        }
        _ => {}
    }
    let mut symbols = BTreeSet::new();
    node.symbols(&mut symbols);
    if symbols.len() == 1 {
        let id = *symbols.first().unwrap();
        let domain = env[id].as_ref()?;
        if let Some(values) = domain.enumerate(FINITE_LIMIT) {
            let mut retained = Vec::new();
            for value in values {
                match evaluate(node, Some((id, value)), work) {
                    Ok(result) if (result != 0) == truth => retained.push(value),
                    Ok(_) => {}
                    // An overflow under the conservative checked model may be
                    // defined in another profile. Never remove such inputs.
                    Err(Fault::Semantic(_)) | Err(Fault::Unavailable) => retained.push(value),
                    Err(Fault::Budget) => return Some(env),
                }
            }
            env[id] = Some(Domain::from_values(retained, domain.bits, domain.signed)?);
            return Some(env);
        }
    }
    if let Kind::Binary(op, a, b) = &node.kind {
        if comparison(*op) {
            let op = if truth { *op } else { invert(*op) };
            let direct = variable(a)
                .zip(constant(b))
                .map(|(id, n)| (id, n, op))
                .or_else(|| {
                    variable(b)
                        .zip(constant(a))
                        .map(|(id, n)| (id, n, reverse(op)))
                });
            if let Some((id, n, op)) = direct {
                let d = env[id].as_mut()?;
                let (lo, hi) = (d.lo, d.hi);
                let okay = match op {
                    BinaryOp::Eq => d.restrict_interval(n, n),
                    BinaryOp::Ne => {
                        if n == lo {
                            d.restrict_interval(lo + 1, hi)
                        } else if n == hi {
                            d.restrict_interval(lo, hi - 1)
                        } else {
                            true
                        }
                    }
                    BinaryOp::Lt => d.restrict_interval(lo, n - 1),
                    BinaryOp::Le => d.restrict_interval(lo, n),
                    BinaryOp::Gt => d.restrict_interval(n + 1, hi),
                    BinaryOp::Ge => d.restrict_interval(n, hi),
                    _ => true,
                };
                return okay.then_some(env);
            }
            if op == BinaryOp::Eq {
                for (mask_node, wanted) in [(a.as_ref(), constant(b)), (b.as_ref(), constant(a))] {
                    if let (Kind::Binary(BinaryOp::BitAnd, left, right), Some(wanted)) =
                        (&mask_node.kind, wanted)
                    {
                        if let Some((id, mask)) = variable(left)
                            .zip(constant(right))
                            .or_else(|| variable(right).zip(constant(left)))
                        {
                            let width = (1u128 << mask_node.ty.bits()) - 1;
                            let mask = (mask as u128 & width) as u64;
                            let wanted = (wanted as u128 & width) as u64;
                            if wanted & !mask != 0 {
                                return None;
                            }
                            let d = env[id].as_mut()?;
                            return d
                                .restrict_bits(mask & !wanted, mask & wanted)
                                .then_some(env);
                        }
                    }
                }
            }
        }
    }
    Some(env)
}

fn value_domain(node: &Node, env: &Environment, work: &mut Work) -> Domain {
    if work.step().is_err() {
        return node.ty.full();
    }
    if let Some(id) = variable(node) {
        return env[id].clone().unwrap_or_else(|| node.ty.full());
    }
    if let Some(n) = constant(node) {
        return Domain::interval(n, n, node.ty.bits(), node.ty.signed());
    }
    let mut symbols = BTreeSet::new();
    node.symbols(&mut symbols);
    let inputs = if symbols.is_empty() {
        Some(vec![None])
    } else if symbols.len() == 1 {
        let id = *symbols.first().unwrap();
        env[id]
            .as_ref()
            .and_then(|d| d.enumerate(FINITE_LIMIT))
            .map(|v| v.into_iter().map(|n| Some((id, n))).collect())
    } else {
        None
    };
    if let Some(inputs) = inputs {
        let mut values = Vec::new();
        let mut complete = true;
        for input in inputs {
            match evaluate(node, input, work) {
                Ok(v) => values.push(v),
                Err(_) => {
                    complete = false;
                    break;
                }
            }
        }
        if complete {
            if let Some(d) = Domain::from_values(values, node.ty.bits(), node.ty.signed()) {
                return d;
            }
        }
    }
    if let Kind::Binary(BinaryOp::BitAnd, a, b) = &node.kind {
        if let Some(mask) = constant(b).or_else(|| constant(a)) {
            let mut d = node.ty.full();
            let full = ((1u128 << node.ty.bits()) - 1) as u64;
            if d.restrict_bits(!mask as u64 & full, 0) {
                return d;
            }
        }
    }
    // A full input type may become finite inside an operation, for example
    // (x & 1) + 4294967294u32. Propagate those finite intermediate values instead
    // of losing the bound just because the original binding was not enumerable.
    // Cartesian products deliberately forget correlations, so they contain all
    // reachable pairs; the same shared work budget bounds every evaluation.
    let mut values = Vec::new();
    match &node.kind {
        Kind::Unary(_, a) | Kind::Cast(a) => {
            if let Some(inputs) = value_domain(a, env, work).enumerate(FINITE_LIMIT) {
                for value in inputs {
                    let child = Box::new(Node::constant(value, a.ty, a.span));
                    let kind = match &node.kind {
                        Kind::Unary(op, _) => Kind::Unary(*op, child),
                        _ => Kind::Cast(child),
                    };
                    let temporary = Node {
                        kind,
                        ty: node.ty,
                        span: node.span,
                    };
                    match evaluate(&temporary, None, work) {
                        Ok(value) => values.push(value),
                        Err(_) => return node.ty.full(),
                    }
                }
            }
        }
        Kind::Binary(op, a, b) => {
            let left = value_domain(a, env, work).enumerate(FINITE_LIMIT);
            let right = value_domain(b, env, work).enumerate(FINITE_LIMIT);
            if let (Some(left), Some(right)) = (left, right) {
                if left.len().saturating_mul(right.len()) <= FINITE_LIMIT {
                    for x in left {
                        for &y in &right {
                            let temporary = Node {
                                kind: Kind::Binary(
                                    *op,
                                    Box::new(Node::constant(x, a.ty, a.span)),
                                    Box::new(Node::constant(y, b.ty, b.span)),
                                ),
                                ty: node.ty,
                                span: node.span,
                            };
                            match evaluate(&temporary, None, work) {
                                Ok(value) => values.push(value),
                                Err(_) => return node.ty.full(),
                            }
                        }
                    }
                }
            }
        }
        _ => {}
    }
    if let Some(domain) = Domain::from_values(values, node.ty.bits(), node.ty.signed()) {
        return domain;
    }
    node.ty.full()
}

struct Analysis<'a> {
    source: &'a str,
    options: &'a AdvisorOptions,
    context: String,
    line_starts: Vec<usize>,
    findings: Vec<Finding>,
    ranges: Vec<RangeSite>,
    expressions: Vec<Value>,
    withheld: Vec<Value>,
    flow_work: Work,
    search_work: Work,
    targets: usize,
    findings_omitted: usize,
    ranges_omitted: usize,
    targets_omitted: usize,
    incomplete_searches: usize,
    functions_analyzed: usize,
    seen_ranges: HashSet<(usize, usize)>,
    seen_expressions: HashSet<(usize, usize)>,
}

impl<'a> Analysis<'a> {
    fn location(&self, span: Span) -> SourceLocation {
        let line = self
            .line_starts
            .partition_point(|&start| start <= span.start);
        let line_start = self.line_starts[line - 1];
        SourceLocation {
            start: span.start,
            end: span.end,
            line,
            column: self.source[line_start..span.start].chars().count() + 1,
        }
    }
    fn id(&self, kind: &str, span: Span) -> String {
        sha256(format!("{}:{kind}:{}:{}", self.context, span.start, span.end).as_bytes())
    }
    fn finding(&mut self, finding: Finding) {
        if self.findings.len() < self.options.max_findings {
            self.findings.push(finding);
        } else {
            self.findings_omitted += 1;
        }
    }
    fn read(&mut self, node: &Node, id: usize, env: &Environment, function: &Function) {
        if !self.seen_ranges.insert((node.span.start, node.span.end)) {
            return;
        }
        let Some(d) = &env[id] else {
            return;
        };
        if self.ranges.len() >= self.options.max_ranges {
            self.ranges_omitted += 1;
            return;
        }
        self.ranges.push(RangeSite{id:self.id("rust-range",node.span),location:self.location(node.span),function:function.name.clone(),symbol:function.bindings[id].name.clone(),expression:self.source[node.span.start..node.span.end].into(),c_type:node.ty.name().into(),minimum:d.lo.to_string(),maximum:d.hi.to_string(),basis:vec!["Explicit Rust primitive binding type; accepted intraprocedural guards, assignments, and conservative branch joins.".into()],operation:Some("rust_scalar_read".into()),instrumentable:false,domain:Some(d.summary())});
    }
    fn visit(&mut self, node: &Node, env: &Environment, function: &Function) {
        if self.flow_work.step().is_err() {
            return;
        }
        // Prefer a complete user expression before its smaller subexpressions
        // consume the explicit search budget. Child read domains are still
        // refined in Rust's short-circuit evaluation order below.
        self.suggest(node, env, function);
        match &node.kind {
            Kind::Var(id) => self.read(node, *id, env, function),
            Kind::Constant(_) => {}
            Kind::Unary(_, a) | Kind::Cast(a) => self.visit(a, env, function),
            Kind::Binary(op, a, b) => {
                self.visit(a, env, function);
                if matches!(op, BinaryOp::LogicalAnd | BinaryOp::LogicalOr) {
                    if let Some(right) = refine(
                        a,
                        *op == BinaryOp::LogicalAnd,
                        env.clone(),
                        &mut self.flow_work,
                    ) {
                        self.visit(b, &right, function);
                    }
                } else {
                    self.visit(b, env, function);
                }
            }
            Kind::Conditional(_, _, _) => {}
        }
    }
    fn block(
        &mut self,
        body: &[Statement],
        mut env: Environment,
        function: &Function,
    ) -> Option<Environment> {
        for statement in body {
            if self.flow_work.step().is_err() {
                return Some(env);
            }
            match statement {
                Statement::Let(id, node) | Statement::Assign(id, node) => {
                    self.visit(node, &env, function);
                    env[*id] = Some(value_domain(node, &env, &mut self.flow_work));
                }
                Statement::If(condition, yes, no) => {
                    self.visit(condition, &env, function);
                    let a = refine(condition, true, env.clone(), &mut self.flow_work)
                        .and_then(|e| self.block(yes, e, function));
                    let b = refine(condition, false, env, &mut self.flow_work)
                        .and_then(|e| self.block(no, e, function));
                    env = join(a, b)?;
                }
                Statement::Return(node) => {
                    if let Some(node) = node {
                        self.visit(node, &env, function);
                    }
                    return None;
                }
                Statement::Tail(node) => {
                    self.visit(node, &env, function);
                    return None;
                }
                Statement::Expr(node) => self.visit(node, &env, function),
            }
        }
        Some(env)
    }
    fn function(&mut self, function: &Function) {
        self.functions_analyzed += 1;
        let env = function
            .bindings
            .iter()
            .map(|b| b.parameter.then(|| b.ty.full()))
            .collect();
        self.block(&function.body, env, function);
        for b in &function.bindings {
            if b.reads == 0 && !b.name.starts_with('_') {
                self.finding(Finding{id:self.id("rust-unused-binding",b.span),kind:"unused_binding".into(),assurance:"syntactic_no_reads_in_admitted_function".into(),location:self.location(b.span),function:Some(function.name.clone()),symbol:Some(b.name.clone()),message:format!("Rust {} {} has no reads in this completely parsed function.",if b.parameter{"parameter"}else{"local"},b.name),suggestion:None,original:self.source[b.span.start..b.span.end].into(),related_locations:vec![],requirements:vec!["Review public function signatures and preserve initializer/assignment evaluation, including possible panics; no deletion is applied.".into()],estimated_source_bytes_saved:None});
            }
        }
        self.constants(function);
    }

    fn constants(&mut self, function: &Function) {
        fn nodes<'n>(node: &'n Node, out: &mut Vec<&'n Node>) {
            match &node.kind {
                Kind::Constant(_) => out.push(node),
                Kind::Var(_) => {}
                Kind::Unary(_, a) | Kind::Cast(a) => nodes(a, out),
                Kind::Binary(_, a, b) => {
                    nodes(a, out);
                    nodes(b, out);
                }
                Kind::Conditional(a, b, c) => {
                    nodes(a, out);
                    nodes(b, out);
                    nodes(c, out);
                }
            }
        }
        fn block<'n>(body: &'n [Statement], out: &mut Vec<&'n Node>) {
            for s in body {
                match s {
                    Statement::Let(_, n)
                    | Statement::Assign(_, n)
                    | Statement::Expr(n)
                    | Statement::Tail(n) => nodes(n, out),
                    Statement::Return(Some(n)) => nodes(n, out),
                    Statement::Return(None) => {}
                    Statement::If(n, a, b) => {
                        nodes(n, out);
                        block(a, out);
                        block(b, out);
                    }
                }
            }
        }
        let mut all = Vec::new();
        block(&function.body, &mut all);
        let mut groups: BTreeMap<(&str, i128), Vec<Span>> = BTreeMap::new();
        for n in all {
            if let Kind::Constant(value) = n.kind {
                if n.ty != Ty::Bool && (value >= 256 || value <= -256) {
                    groups.entry((n.ty.name(), value)).or_default().push(n.span);
                }
            }
        }
        for ((ty, value), spans) in groups {
            if spans.len() < 2 {
                continue;
            }
            let declaration = format!("const K: {ty} = {value};");
            let first = spans[0];
            let saved = spans
                .iter()
                .map(|s| (s.end - s.start) as isize - 1)
                .sum::<isize>()
                - declaration.len() as isize;
            self.finding(Finding{id:self.id("rust-repeated-constant",first),kind:"repeated_constant".into(),assurance:"same_typed_integer_value_in_admitted_function".into(),location:self.location(first),function:Some(function.name.clone()),symbol:None,message:format!("The Rust {ty} value {value} occurs {} times; a scoped constant may share its spelling.",spans.len()),suggestion:Some(declaration),original:self.source[first.start..first.end].into(),related_locations:spans.iter().skip(1).map(|&s|self.location(s)).collect(),requirements:vec!["Choose a fresh binding name and a scope visible to every use; preserve the exact primitive type.".into(),"This spelling estimate includes the proposed declaration and one-character references, but does not measure whole-file compression or machine code.".into()],estimated_source_bytes_saved:Some(saved)});
        }
    }

    fn suggest(&mut self, node: &Node, env: &Environment, function: &Function) {
        if node.node_count() < 2 || self.flow_work.exhausted {
            return;
        }
        let mut symbols = BTreeSet::new();
        node.symbols(&mut symbols);
        if symbols.len() != 1 {
            return;
        }
        let id = *symbols.first().unwrap();
        let Some(domain) = &env[id] else {
            return;
        };
        let Some(values) = domain.enumerate(FINITE_LIMIT) else {
            return;
        };
        if values.is_empty()
            || !self
                .seen_expressions
                .insert((node.span.start, node.span.end))
        {
            return;
        }
        if self.targets >= self.options.max_nversion_targets {
            self.targets_omitted += 1;
            return;
        }
        self.targets += 1;
        let binding = &function.bindings[id];
        let original = &self.source[node.span.start..node.span.end];
        let domain_hash = sha256(
            values
                .iter()
                .map(ToString::to_string)
                .collect::<Vec<_>>()
                .join(",")
                .as_bytes(),
        );
        let mut record = json!({"id":self.id("rust-expression",node.span),"location":self.location(node.span),"function":function.name,"symbol":binding.name,"variable_type":binding.ty.name(),"result_type":node.ty.name(),"original":original,"static_domain":domain.summary(),"domain_values":values.iter().map(ToString::to_string).collect::<Vec<_>>(),"domain_sha256":domain_hash,"domain_basis":"Conservative explicit primitive type, admitted guards/assignments, and branch unions; no observations or runtime profile used.","candidates":[],"rejections":[],"advisory_only":true});
        if binding.ty == Ty::Bool {
            record["status"] = json!("candidate_generation_unsupported_boolean_input");
            self.expressions.push(record);
            return;
        }
        let mut expected = Vec::with_capacity(values.len());
        for &value in &values {
            match evaluate(node, Some((id, value)), &mut self.search_work) {
                Ok(result) => expected.push(result),
                Err(error) => {
                    record["status"] = json!(if matches!(error, Fault::Budget) {
                        "incomplete_budget"
                    } else {
                        "original_not_total_in_checked_rust_model"
                    });
                    record["original_failure"] = json!({"input":value.to_string(),"reason":error.reason(),"checked_values":expected.len()+usize::from(!matches!(error,Fault::Budget))});
                    if matches!(error, Fault::Budget) {
                        self.incomplete_searches += 1;
                    }
                    self.expressions.push(record);
                    return;
                }
            }
        }
        record["original_rust_defined"] = json!(true);
        let Some(ir) = carrier(node, id) else {
            return;
        };
        if self.search_work.remaining() == 0 {
            self.search_work.exhausted = true;
            self.incomplete_searches += 1;
            record["status"] = json!("incomplete_budget");
            self.expressions.push(record);
            return;
        }
        let budget = nversion::SearchBudget {
            max_evaluations: self.search_work.remaining().min(2_000_000),
            max_results: 64,
            ..Default::default()
        };
        let request=nversion::SearchRequest{original:ir,original_source:original.into(),symbol:binding.name.clone(),variable_type:binding.ty.carrier(),domain:nversion::FiniteDomain{values:values.clone(),provenance:nversion::DomainProvenance::StaticConservative,description:"Internal integer carrier for Rust candidate generation; Rust admission is checked separately.".into()},budget};
        let search = match nversion::compare_and_suggest(&request) {
            Ok(search) => search,
            Err(reason) => {
                record["status"] = json!("candidate_generator_withheld");
                record["candidate_generator_limitation"] = json!(reason);
                self.expressions.push(record);
                return;
            }
        };
        self.search_work.spent += search.statistics.evaluation_steps;
        if self.search_work.spent >= self.search_work.limit {
            self.search_work.exhausted = true;
        }
        record["internal_candidate_generator"] = json!({"language":"c11_integer_carrier","is_rust_proof":false,"original_defined_in_carrier":search.original_defined,"complete":search.complete,"stop_reasons":search.stop_reasons,"statistics":search.statistics,"grammar":search.grammar});
        if !search.original_defined {
            record["status"] = json!("rust_original_defined_candidate_generator_withheld");
            record["candidate_generator_limitation"] = json!(
                "The C integer carrier may withhold Rust-defined shifts or casts. This limits discovery; it is not a Rust undefinedness result."
            );
            if !search.complete && search.original_failure.is_none() {
                self.incomplete_searches += 1;
            }
            self.expressions.push(record);
            return;
        }
        if !search.complete {
            self.incomplete_searches += 1;
        }
        let mut candidates: Vec<Value> = Vec::new();
        let mut rejections: Vec<Value> = Vec::new();
        let mut seen = HashSet::new();
        for candidate in search.candidates {
            let adapted = match adapt(&candidate.expression, binding.ty) {
                Ok(n) => n,
                Err(reason) => {
                    rejections
                        .push(json!({"internal_carrier_source":candidate.source,"reason":reason}));
                    continue;
                }
            };
            let adapted = if node.ty == Ty::Bool {
                truth(adapted)
            } else if adapted.ty == Ty::Bool {
                cast_node(adapted, node.ty)
            } else {
                adapted
            };
            if adapted.ty != node.ty {
                rejections.push(json!({"reason":"Rust candidate result type differs"}));
                continue;
            }
            let mut parsed = None;
            for suffix in [false, true] {
                let text = render(&adapted, &binding.name, suffix).0;
                if let Ok(tree) = parse_candidate(&text, &binding.name, binding.ty) {
                    if tree.ty == node.ty {
                        parsed = Some((text, tree));
                        break;
                    }
                }
            }
            let Some((text, tree)) = parsed else {
                rejections.push(json!({"reason":"Rust candidate syntax/type could not be independently reparsed"}));
                continue;
            };
            if text == original || !seen.insert(text.clone()) {
                continue;
            }
            let mut failure = None;
            let mut checked = 0;
            for (&input, &expected) in values.iter().zip(&expected) {
                match evaluate(&tree, Some((0, input)), &mut self.search_work) {
                    Ok(actual) if actual == expected => checked += 1,
                    Ok(actual) => {
                        checked += 1;
                        failure = Some(
                            json!({"input":input.to_string(),"expected":expected.to_string(),"actual":actual.to_string(),"reason":"Rust typed result differs"}),
                        );
                        break;
                    }
                    Err(error) => {
                        if matches!(error, Fault::Budget) {
                            self.incomplete_searches += 1;
                        }
                        failure = Some(
                            json!({"input":input.to_string(),"reason":error.reason(),"budget_exhausted":matches!(error,Fault::Budget)}),
                        );
                        break;
                    }
                }
            }
            if let Some(failure) = failure {
                rejections
                    .push(json!({"source":text,"checked_values":checked,"counterexample":failure}));
                if self.search_work.exhausted {
                    break;
                }
                continue;
            }
            let saved = original.len() as isize - text.len() as isize;
            candidates.push(json!({"source":text,"source_bytes":text.len(),"bytes_saved":saved,"family":candidate.family,"result_type":node.ty.name(),"evidence":{"language":"rust","status":"exhaustive_static_domain","checked_values":checked,"domain_sha256":domain_hash,"same_result_type":true,"source_reparsed":true,"overflow_model":"defined with overflow checks enabled and disabled"}}));
        }
        candidates.sort_by(|a, b| {
            (a["source_bytes"].as_u64(), a["source"].as_str())
                .cmp(&(b["source_bytes"].as_u64(), b["source"].as_str()))
        });
        for candidate in candidates
            .iter()
            .take(3)
            .filter(|c| c["bytes_saved"].as_i64().is_some_and(|n| n > 0))
        {
            self.finding(Finding{id:self.id(&format!("rust-nversion-{}",candidate["source"].as_str().unwrap()),node.span),kind:"n_version_expression".into(),assurance:"exhaustive_rust_typed_static_domain".into(),location:self.location(node.span),function:Some(function.name.clone()),symbol:Some(binding.name.clone()),message:format!("A Rust {} expression matches every one of {} conservatively included input values at this site.",node.ty.name(),values.len()),suggestion:Some(candidate["source"].as_str().unwrap().into()),original:original.into(),related_locations:vec![],requirements:vec!["This equivalence requires the reported binding identity and static domain; reanalyze after edits.".into(),"Both original and candidate must remain defined under the checked Rust arithmetic model; no dynamic observations are promoted to invariants.".into(),"Source bytes are an estimate; whole-file compression, generated machine code, and engine strength are not measured.".into()],estimated_source_bytes_saved:candidate["bytes_saved"].as_i64().map(|n|n as isize)});
        }
        record["status"] = json!(if search.complete && !self.search_work.exhausted {
            "compared_finite_rust_domain"
        } else {
            "compared_partial_candidate_search"
        });
        record["candidates"] = json!(candidates);
        record["rejections"] = json!(rejections);
        self.expressions.push(record);
    }
}

/// Analyze only the documented standalone function/scalar subset. Unsupported
/// surrounding items withhold the whole file because they can change primitive
/// name resolution; unsupported body syntax withholds that complete function.
pub fn analyze(source: &[u8], options: &AdvisorOptions) -> Result<AdviceReport> {
    super::validate_options(source, options)?;
    ensure!(
        matches!(options.standard.as_str(), "rust2021" | "rust2024"),
        "Rust advisory dialect must be rust2021 or rust2024"
    );
    ensure!(
        options.compiler_args.is_empty(),
        "Rust scalar advice does not accept compiler/preprocessor arguments"
    );
    let source = std::str::from_utf8(source)?;
    let source_hash = sha256(source.as_bytes());
    let context=sha256(serde_json::to_vec(&json!({"source_sha256":source_hash,"language":"rust","edition":options.standard,"adapter":"rust-scalar-v1","overflow":"defined in checked and unchecked profiles; shifts truncate, counts checked","macros":"never expanded","flow_work":options.max_finite_flow_work,"search_work":options.max_nversion_work}))?.as_slice());
    let line_starts = std::iter::once(0)
        .chain(
            source
                .bytes()
                .enumerate()
                .filter_map(|(i, b)| (b == b'\n').then_some(i + 1)),
        )
        .collect();
    let mut analysis = Analysis {
        source,
        options,
        context: context.clone(),
        line_starts,
        findings: vec![],
        ranges: vec![],
        expressions: vec![],
        withheld: vec![],
        flow_work: Work::new(options.max_finite_flow_work),
        search_work: Work::new(options.max_nversion_work),
        targets: 0,
        findings_omitted: 0,
        ranges_omitted: 0,
        targets_omitted: 0,
        incomplete_searches: 0,
        functions_analyzed: 0,
        seen_ranges: HashSet::new(),
        seen_expressions: HashSet::new(),
    };
    let mut parsed = Vec::new();
    let mut file_failure = None;
    match lex(source) {
        Err(reason) => file_failure = Some(reason),
        Ok(tokens) => {
            let mut i = 0;
            let mut names = HashSet::new();
            let mut function_count = 0;
            while i < tokens.len() {
                let start = i;
                if tokens[i].text == "pub" {
                    i += 1;
                }
                if !tokens.get(i).is_some_and(|t| t.text == "fn") {
                    file_failure=Some("Only standalone optional-pub fn items are admitted. Attributes, imports, aliases, modules, impls, macros, and other surrounding items can change name/type resolution and withhold the whole file.".into());
                    break;
                }
                let name = tokens
                    .get(i + 1)
                    .map(|t| t.text.clone())
                    .unwrap_or_default();
                if !names.insert(name.clone()) {
                    file_failure = Some(
                        "duplicate function names make the source invalid or ambiguous".into(),
                    );
                    break;
                }
                function_count += 1;
                if function_count > MAX_FUNCTIONS {
                    file_failure = Some("function budget exceeded".into());
                    break;
                }
                while i < tokens.len() && tokens[i].text != "{" && tokens[i].text != ";" {
                    i += 1;
                }
                if i == tokens.len() || tokens[i].text != "{" {
                    file_failure = Some("a supported function body could not be delimited".into());
                    break;
                }
                let mut depth = 1usize;
                i += 1;
                while i < tokens.len() && depth > 0 {
                    if tokens[i].text == "{" {
                        depth += 1;
                    } else if tokens[i].text == "}" {
                        depth -= 1;
                    }
                    i += 1;
                }
                if depth != 0 {
                    file_failure = Some("unbalanced function braces".into());
                    break;
                }
                let span = tokens[start].span.through(tokens[i - 1].span);
                match Parser::new(&tokens[start..i]).function(){Ok(function)=>parsed.push(function),Err(reason)=>analysis.withheld.push(json!({"function":name,"location":analysis.location(span),"reason":reason,"scope":"whole_function","findings_emitted":0}))}
            }
        }
    }
    if let Some(reason) = file_failure {
        analysis.withheld.clear();
        analysis
            .withheld
            .push(json!({"scope":"whole_file","reason":reason,"findings_emitted":0}));
    } else {
        for function in &parsed {
            analysis.function(function);
        }
    }
    analysis
        .findings
        .sort_by_key(|f| (f.location.start, f.kind.clone(), f.id.clone()));
    analysis.ranges.sort_by_key(|r| r.location.start);
    let complete = analysis.withheld.is_empty()
        && !analysis.flow_work.exhausted
        && !analysis.search_work.exhausted
        && analysis.findings_omitted == 0
        && analysis.ranges_omitted == 0
        && analysis.targets_omitted == 0
        && analysis.incomplete_searches == 0;
    Ok(AdviceReport{format_version:2,advisory_only:true,source_sha256:source_hash,analysis_context_sha256:context,
        frontend:json!({"language":"rust","standard":options.standard,"backend":"bounded_rust_scalar_parser","compiler_invocations":0,"macro_expansion":false,"dynamic_instrumentation":false,"overflow_model":"original and candidate must be defined with overflow checks enabled and disabled"}),
        statistics:json!({"functions_analyzed":analysis.functions_analyzed,"functions_or_files_withheld":analysis.withheld.len(),"expression_sites_emitted":analysis.expressions.len(),"expression_sites_omitted":analysis.targets_omitted,"findings_emitted":analysis.findings.len(),"findings_omitted":analysis.findings_omitted,"ranges_emitted":analysis.ranges.len(),"ranges_omitted":analysis.ranges_omitted,"finite_flow_work":analysis.flow_work.spent,"finite_flow_work_exhausted":analysis.flow_work.exhausted,"nversion_work":analysis.search_work.spent,"nversion_work_exhausted":analysis.search_work.exhausted,"nversion_incomplete_searches":analysis.incomplete_searches,"source_modified":false,"compression_candidates_created":0,"final_file_bytes_measured":false}),
        findings:analysis.findings,ranges:analysis.ranges,expressions:vec![],
        language_details:Some(json!({"adapter":"rust-scalar-v1","support":{"typed_repeated_constants":"within admitted functions","unused_bindings":"parameters and locals without reads in admitted functions; no whole-crate unused-function claim","ranges":"explicit primitive bindings, branches, assignments, finite scalar transfer, conservative joins","nversion":"integer-input finite static domains with independent Rust typed admission; C carrier limits discovery","dynamic_profiles":"unsupported","instrumentation":"unsupported"},"expressions":analysis.expressions,"withheld":analysis.withheld,"admitted_syntax":"standalone fn/pub fn; explicit i32/u32/i64/u64/bool parameters and initialized locals; mut assignment; if/else blocks, return and function-tail expressions; primitive scalar operators and integer as casts","internal_carrier_is_rust_proof":false})),
        limitations:vec!["This is a standalone scalar Rust subset, not rustc name resolution or full-crate analysis. All surrounding imports/items/attributes are withheld; macros, calls, references, loops, shadowing, and unknown body syntax withhold the whole function.".into(),"Rust bool is distinct from integers; integer ! is bitwise. Arithmetic overflow, division failure, and out-of-range shift counts reject proof. Left shifts truncate, signed right shifts are arithmetic, and integer as casts truncate/reinterpret.".into(),"The shared C integer search is a proposal generator only. Rust-defined operations unsupported by that carrier limit candidate discovery; retained candidates are reparsed, typed, and exhaustively re-evaluated under Rust rules.".into(),"All suggestions are reviewable source estimates only. No source is changed, no compression candidate is created, and no external code or compiler is executed.".into(),"Only finite scalar domains up to 4096 values are compared. Dynamic observation, instrumentation, whole-crate unused-function detection, and multi-variable synthesis are unsupported.".into()],complete})
}

#[cfg(test)]
mod tests {
    use super::*;

    fn options() -> AdvisorOptions {
        AdvisorOptions {
            standard: "rust2021".into(),
            ..Default::default()
        }
    }
    fn report(source: &str) -> AdviceReport {
        analyze(source.as_bytes(), &options()).unwrap()
    }
    fn parse(source: &str) -> std::result::Result<Function, String> {
        let tokens = lex(source)?;
        Parser::new(&tokens).function()
    }
    fn expr(source: &str, ty: Ty) -> Node {
        parse_candidate(source, "x", ty).unwrap()
    }
    fn value(source: &str, ty: Ty, input: i128) -> std::result::Result<i128, Fault> {
        evaluate(&expr(source, ty), Some((0, input)), &mut Work::new(10_000))
    }
    fn details(report: &AdviceReport) -> &Value {
        report.language_details.as_ref().unwrap()
    }

    #[test]
    fn rust_primitive_semantics_do_not_inherit_c_promotions_or_wrapping() {
        assert_eq!(value("!x", Ty::U32, 0).unwrap(), u32::MAX as i128);
        assert_eq!(expr("!x", Ty::Bool).ty, Ty::Bool);
        assert_eq!(value("!x", Ty::Bool, 1).unwrap(), 0);
        assert_eq!(expr("x==1", Ty::U64).ty, Ty::Bool);
        assert!(parse_candidate("x+1i32", "x", Ty::U32).is_err());
        assert!(parse_candidate("x&&1", "x", Ty::Bool).is_err());
        assert!(parse_candidate("x as bool", "x", Ty::I32).is_err());
        assert!(value("x+1", Ty::U32, u32::MAX as i128).is_err());
        assert!(value("x-1", Ty::U64, 0).is_err());
        assert!(value("x+1", Ty::I64, i64::MAX as i128).is_err());
        assert!(value("-x", Ty::I32, i32::MIN as i128).is_err());
        assert!(value("x/-1", Ty::I32, i32::MIN as i128).is_err());
        assert!(value("x%-1", Ty::I32, i32::MIN as i128).is_err());
        assert_eq!(value("x<<1", Ty::I32, -1).unwrap(), -2);
        assert_eq!(
            value("x<<1", Ty::U32, u32::MAX as i128).unwrap(),
            u32::MAX as i128 - 1
        );
        assert_eq!(value("x>>1", Ty::I32, -3).unwrap(), -2);
        assert!(value("x<<32", Ty::I32, 1).is_err());
        assert!(value("x>>-1", Ty::I32, 1).is_err());
        assert_eq!(value("x as i32", Ty::U64, u64::MAX as i128).unwrap(), -1);
        assert_eq!(value("x as u32", Ty::I64, -1).unwrap(), u32::MAX as i128);
        assert_eq!(value("true as u64", Ty::I32, 0).unwrap(), 1);
        assert_eq!(
            value("-9223372036854775808i64", Ty::I32, 0).unwrap(),
            i64::MIN as i128
        );
        assert_eq!(value("x==0||1/x==1", Ty::I32, 0).unwrap(), 1);
        assert_eq!(value("x!=0&&1/x==1", Ty::I32, 0).unwrap(), 0);
    }

    #[test]
    fn complete_function_admission_rejects_unknown_rust_and_type_errors() {
        let invalid = [
            "fn f(x:i32)->bool{x}",
            "fn f()->bool{1}",
            "fn f(){if 1{return;}}",
            "fn f(x:bool)->bool{x&1}",
            "fn f()->bool{let b:bool=0;b}",
            "fn f(x:i32)->bool{x as bool}",
            "fn f(x:u32)->u32{x+1i32}",
            "fn f(x:i32)->i32{let y=x;y}",
            "fn f(x:i32)->i32{let x:i32=1;x}",
            "fn f(x:i32)->i32{x=1;x}",
            "fn f(x:i32)->i32{unknown(x)}",
            "fn f(x:i32)->i32{identity!(x)}",
            "fn f(x:i32)->i32{let y:i32=&x;y}",
            "fn f(x:i32)->i32{while x>0{}x}",
            "fn f(x:i32)->i32{loop{}x}",
            "fn f(x:i32)->i32{let y:i32=0_xff;y}",
            "fn f(x:i32)->i32{let y:i32=1i_32;y}",
            "fn f(x:i32)->bool{x as u32<16}",
            "fn f(x:i32)->u32{x as u32<<2}",
            "fn f(try:i32)->i32{try}",
            "fn abstract(x:i32)->i32{x}",
        ];
        for source in invalid {
            assert!(parse(source).is_err(), "admitted {source}");
            let r = report(source);
            assert!(r.findings.is_empty() && r.ranges.is_empty());
            assert!(!r.complete);
            assert_eq!(details(&r)["withheld"][0]["scope"], "whole_function");
        }
        assert!(
            parse("pub fn f(mut x:i32)->bool{let y:i32=1;x=y;if x<2{return true;}false}").is_ok()
        );
        assert!(parse("fn f(x:i32)->bool{(x as u32)<16}").is_ok());
        assert!(parse("fn f(x:i32)->u32{(x as u32)<<2}").is_ok());
        assert!(parse("fn f(x:i32)->bool{(x==0)==true}").is_ok());
    }

    #[test]
    fn surrounding_items_and_opaque_literals_never_leak_function_findings() {
        let safe = "fn safe(x:i32)->bool{let y:i32=x&1;y==0}";
        for item in [
            "type i32=u32;",
            "use other::i32;",
            "struct bool;",
            "#[cfg(any())]",
            "macro_rules! m{()=>{fn fake(x:i32)->bool{x==0}}}",
            "impl T{}",
            "mod hidden{}",
        ] {
            let r = report(&format!("{safe}{item}"));
            assert!(!r.complete);
            assert!(r.findings.is_empty() && r.ranges.is_empty());
            assert_eq!(details(&r)["withheld"][0]["scope"], "whole_file");
        }
        for body in [
            "let text:i32=\"} fn fake(x:i32)->bool{x==0} {\";0",
            "let text:i32=r###\"} fn fake(){ }\"###;0",
        ] {
            let r = report(&format!("fn real()->i32{{{body}}}"));
            assert_eq!(r.statistics["functions_analyzed"], 0);
            assert_eq!(details(&r)["withheld"].as_array().unwrap().len(), 1);
            assert!(r.findings.is_empty());
        }
        let r = report("/* outer /* fn fake(){} */ still comment */ fn actual()->i32{1}");
        assert_eq!(r.statistics["functions_analyzed"], 1);
        assert!(r.complete);
    }

    #[test]
    fn flow_intersects_guards_joins_branches_and_kills_assigned_facts() {
        let mut o = options();
        o.max_nversion_work = 1000;
        let source = "fn f(x:i32)->bool{let mut y:i32=x&1;if x<0{y=2;}y==0}";
        let r = analyze(source.as_bytes(), &o).unwrap();
        let read = r.ranges.iter().rev().find(|r| r.symbol == "y").unwrap();
        assert_eq!(
            read.domain.as_ref().unwrap().values,
            Some(vec!["0".into(), "1".into(), "2".into()])
        );
        let source = "fn f(x:i32)->bool{let mut y:i32=x&1;y=x;y==0}";
        let r = analyze(source.as_bytes(), &o).unwrap();
        let read = r.ranges.iter().rev().find(|r| r.symbol == "y").unwrap();
        assert_eq!(read.minimum, i32::MIN.to_string());
        assert_eq!(read.maximum, i32::MAX.to_string());
        assert!(!read.instrumentable);
        let source = "fn f(x:i32)->bool{if x<0||x>127{return false;}if x&136!=0{return false;}x>>4==0||x>>4==7}";
        let r = analyze(source.as_bytes(), &o).unwrap();
        let entry = r
            .ranges
            .iter()
            .find(|read| read.location.start == source.find("x>>4==0").unwrap())
            .unwrap();
        let d = entry.domain.as_ref().unwrap();
        assert_eq!(d.finite_cardinality, Some(64));
        assert_eq!(d.minimum, "0");
        assert_eq!(d.maximum, "119");
        assert!(!d.values.as_ref().unwrap().contains(&"8".into()));
        let rhs = r.ranges.last().unwrap().domain.as_ref().unwrap();
        assert_eq!(rhs.finite_cardinality, Some(56));
        assert_eq!(rhs.minimum, "16");
        assert_eq!(rhs.maximum, "119");
    }

    #[test]
    fn zero_x88_advice_is_rust_bool_and_proved_on_every_static_value() {
        let source = "fn edge(to:i32)->bool{if to<0||to>127{return false;}if to&136!=0{return false;}(to>>4)==0||(to>>4)==7}";
        let r = report(source);
        assert!(r.expressions.is_empty());
        assert_eq!(r.frontend["language"], "rust");
        let site = details(&r)["expressions"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["original"] == "(to>>4)==0||(to>>4)==7")
            .unwrap();
        assert_eq!(site["result_type"], "bool");
        assert_eq!(site["static_domain"]["finite_cardinality"], 64);
        assert_eq!(site["domain_values"].as_array().unwrap().len(), 64);
        let candidates = site["candidates"].as_array().unwrap();
        assert!(!candidates.is_empty(), "{site}");
        let expected: Vec<_> = (0..128).filter(|n| n & 136 == 0).collect();
        let mut has_affine_mask = false;
        for c in candidates {
            assert_eq!(c["result_type"], "bool");
            assert_eq!(c["evidence"]["checked_values"], 64);
            assert_eq!(c["evidence"]["language"], "rust");
            assert_eq!(c["evidence"]["domain_sha256"], site["domain_sha256"]);
            let text = c["source"].as_str().unwrap();
            assert!(!text.contains('~'));
            assert!(!text.ends_with("UL"));
            let tree = parse_candidate(text, "to", Ty::I32).unwrap();
            assert_eq!(tree.ty, Ty::Bool);
            for &n in &expected {
                assert_eq!(
                    evaluate(&tree, Some((0, n)), &mut Work::new(10_000)).unwrap(),
                    i128::from(n >> 4 == 0 || n >> 4 == 7)
                );
            }
            has_affine_mask |= text.contains("+16") && text.contains("96");
        }
        assert!(has_affine_mask, "{site}");
        assert!(r
            .findings
            .iter()
            .any(|f| f.original == "(to>>4)==0||(to>>4)==7"
                && f.estimated_source_bytes_saved.is_some_and(|n| n > 0)));
        let package = report("pub fn mask(x:i32)->i32{if x<0||x>7{return 0;}x&7}");
        assert!(package.findings.iter().any(|finding| finding.assurance
            == "exhaustive_rust_typed_static_domain"
            && finding.suggestion.as_deref() == Some("x")));
    }

    #[test]
    fn checked_original_rejects_overflow_but_rust_defined_casts_are_not_called_undefined() {
        let r = report("fn f(x:u32)->bool{let y:u32=x&1;y+4294967295u32==0}");
        let site = details(&r)["expressions"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["original"] == "y+4294967295u32==0")
            .unwrap();
        assert_eq!(site["status"], "original_not_total_in_checked_rust_model");
        assert!(site["candidates"].as_array().unwrap().is_empty());
        assert_eq!(site["original_failure"]["input"], "1");
        let r = report("fn f(x:u32)->i32{let y:u32=(x&1)+4294967294u32;y as i32}");
        let site = details(&r)["expressions"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["original"] == "y as i32")
            .unwrap();
        assert_eq!(site["original_rust_defined"], true);
        assert_eq!(
            site["status"],
            "rust_original_defined_candidate_generator_withheld"
        );
        assert!(site["candidate_generator_limitation"]
            .as_str()
            .unwrap()
            .contains("not a Rust undefinedness"));
    }

    #[test]
    fn constants_unused_bindings_and_site_identity_remain_advisory() {
        let source = "fn f(unused:i32,x:u64)->u64{let spare:i32=0;let a:u64=x&0x5555555555555555u64;a|0x5555555555555555u64}";
        let r = report(source);
        assert!(r.findings.iter().any(|f| f.kind == "repeated_constant"
            && f.related_locations.len() == 1
            && f.suggestion.as_ref().unwrap().contains("u64")));
        for symbol in ["unused", "spare"] {
            assert!(r
                .findings
                .iter()
                .any(|f| f.kind == "unused_binding" && f.symbol.as_deref() == Some(symbol)));
        }
        assert_eq!(r.statistics["compression_candidates_created"], 0);
        assert_eq!(r.statistics["source_modified"], false);
        let mut o = options();
        o.standard = "rust2024".into();
        let other = analyze(source.as_bytes(), &o).unwrap();
        assert_ne!(r.analysis_context_sha256, other.analysis_context_sha256);
        assert!(r.ranges.iter().all(|s| !s.instrumentable));
    }

    #[test]
    fn explicit_work_and_parser_limits_produce_incomplete_results() {
        let mut o = options();
        o.max_nversion_work = 1000;
        let r = analyze(
            b"fn f(x:i32)->bool{let y:i32=x&255;(y>>4)==0||(y>>4)==7}",
            &o,
        )
        .unwrap();
        assert!(!r.complete);
        assert!(r.statistics["nversion_work"].as_u64().unwrap() <= 1000);
        assert_eq!(r.statistics["nversion_work_exhausted"], true);
        let cast_chain = format!("fn f(x:i32)->i32{{x{}}}", " as i32".repeat(MAX_NODES + 50));
        let r = report(&cast_chain);
        assert!(!r.complete);
        assert!(details(&r)["withheld"][0]["reason"]
            .as_str()
            .unwrap()
            .contains("node budget"));
        let binary_chain = format!("fn f(x:i32)->i32{{x{}}}", "+1".repeat(MAX_NODES + 50));
        assert!(parse(&binary_chain).unwrap_err().contains("node budget"));
        let nested = format!(
            "fn f(x:i32)->i32{{{}x{}}}",
            "(".repeat(MAX_DEPTH + 2),
            ")".repeat(MAX_DEPTH + 2)
        );
        assert!(parse(&nested).unwrap_err().contains("depth budget"));
        let tokens = "a ".repeat(MAX_TOKENS + 1);
        assert!(lex(&tokens).unwrap_err().contains("token budget"));
        o.standard = "c11".into();
        assert!(analyze(b"fn f(){}", &o).is_err());
        o.standard = "rust2021".into();
        o.compiler_args = vec!["--cfg=feature".into()];
        assert!(analyze(b"fn f(){}", &o).is_err());
    }

    #[test]
    fn typed_renderer_groups_casts_and_never_confuses_integer_not_with_bool_not() {
        let span = Span { start: 0, end: 0 };
        let x = Node {
            kind: Kind::Var(0),
            ty: Ty::I32,
            span,
        };
        let cast = cast_node(x, Ty::U32);
        for op in [BinaryOp::Lt, BinaryOp::Shl] {
            let tree = Node {
                kind: Kind::Binary(
                    op,
                    Box::new(cast.clone()),
                    Box::new(Node::constant(2, Ty::U32, span)),
                ),
                ty: if op == BinaryOp::Lt {
                    Ty::Bool
                } else {
                    Ty::U32
                },
                span,
            };
            let text = render(&tree, "x", false).0;
            assert!(text.starts_with("(x as u32)"));
            assert!(parse_candidate(&text, "x", Ty::I32).is_ok());
        }
        let c = Expr::unary(
            UnaryOp::LogicalNot,
            Expr::binary(
                BinaryOp::BitAnd,
                Expr::binary(BinaryOp::Add, Expr::Var, Expr::constant(16, CIntType::I32)),
                Expr::constant(96, CIntType::I32),
            ),
        );
        let rust = adapt(&c, Ty::I32).unwrap();
        assert_eq!(rust.ty, Ty::Bool);
        let text = render(&rust, "x", false).0;
        assert_eq!(text, "x+16&96==0");
        assert_eq!(parse_candidate(&text, "x", Ty::I32).unwrap().ty, Ty::Bool);
    }

    #[test]
    fn folded_constant_casts_preserve_rust_types_and_cross_type_shortening() {
        let span = Span { start: 4, end: 9 };
        for (value, source, target, expected) in [
            (-1, Ty::I32, Ty::U32, u32::MAX as i128),
            (u32::MAX as i128, Ty::U32, Ty::I32, -1),
            (u64::MAX as i128, Ty::U64, Ty::I32, -1),
            ((1i128 << 32) + 1, Ty::U64, Ty::U32, 1),
            (i32::MIN as i128, Ty::I32, Ty::I64, i32::MIN as i128),
            (u32::MAX as i128, Ty::U32, Ty::I64, u32::MAX as i128),
            (u64::MAX as i128, Ty::U64, Ty::I64, -1),
            (1, Ty::Bool, Ty::U64, 1),
            (0, Ty::Bool, Ty::I32, 0),
        ] {
            let folded = cast_node(Node::constant(value, source, span), target);
            assert!(matches!(folded.kind, Kind::Constant(n) if n == expected));
            assert_eq!(folded.ty, target);
            assert_eq!((folded.span.start, folded.span.end), (4, 9));
            let text = render(&folded, "x", true).0;
            let parsed = parse_candidate(&text, "x", Ty::I32).unwrap();
            assert_eq!(parsed.ty, target);
            assert_eq!(
                evaluate(&parsed, None, &mut Work::new(100)).unwrap(),
                expected
            );
        }
        // The folding rule does not turn an invalid numeric-to-bool cast into
        // an admitted boolean constant. The existing parser still rejects it.
        let invalid = cast_node(Node::constant(1, Ty::I32, span), Ty::Bool);
        assert!(matches!(invalid.kind, Kind::Cast(_)));
        assert!(parse_candidate(&render(&invalid, "x", true).0, "x", Ty::I32).is_err());

        let candidate = Expr::unary(
            UnaryOp::LogicalNot,
            Expr::binary(
                BinaryOp::BitAnd,
                Expr::binary(BinaryOp::Add, Expr::Var, Expr::constant(8, CIntType::I32)),
                Expr::constant(48, CIntType::I32),
            ),
        );
        for ty in [Ty::U32, Ty::I64, Ty::U64] {
            let adapted = adapt(&candidate, ty).unwrap();
            let text = render(&adapted, "x", false).0;
            assert_eq!(text, "x+8&48==0");
            let parsed = parse_candidate(&text, "x", ty).unwrap();
            assert_eq!(parsed.ty, Ty::Bool);
            for input in 0..64 {
                assert_eq!(
                    evaluate(&parsed, Some((0, input)), &mut Work::new(100)).unwrap(),
                    i128::from(input >> 3 == 0 || input >> 3 == 7)
                );
            }
            let guard = if ty.signed() { "x<0||x>63" } else { "x>63" };
            let source = format!(
                "fn edge(x:{})->bool{{if {guard}{{return false;}}(x>>3)==0||(x>>3)==7}}",
                ty.name()
            );
            let report = report(&source);
            let site = details(&report)["expressions"]
                .as_array()
                .unwrap()
                .iter()
                .find(|site| site["original"] == "(x>>3)==0||(x>>3)==7")
                .unwrap();
            let retained = site["candidates"]
                .as_array()
                .unwrap()
                .iter()
                .find(|candidate| candidate["source"] == text)
                .unwrap_or_else(|| panic!("{} mask candidate missing: {site}", ty.name()));
            assert_eq!(retained["result_type"], "bool");
            assert_eq!(retained["evidence"]["checked_values"], 64);
            assert_eq!(retained["evidence"]["domain_sha256"], site["domain_sha256"]);
            assert!(retained["bytes_saved"].as_i64().unwrap() > 0);
        }
    }
}
