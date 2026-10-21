//! Bounded typed C source portfolios through Clang's JSON AST. Each changed
//! pass is reparsed, unsupported constructs retain identity, and every final
//! candidate still requires the application's real compile/verify contract.
use crate::c_frontend::{FrontendConfig, FrontendSession, ParsedSource};
use crate::notation::{lex, Token, Variant, MAX_SOURCE};
#[cfg(test)]
use crate::process::{run, Limits, Output};
use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
#[cfg(test)]
use std::path::Path;
use std::path::PathBuf;

pub const RULES: &[&str] = &[
    "if-return",
    "return-tail",
    "if-assignment",
    "if-effect",
    "guard",
    "boolean",
    "zero-test",
    "truth",
    "negation",
    "compound",
    "increment",
    "leaf-braces",
    "forever",
    "boolean-domain",
];
const INTEGERS: &[&str] = &[
    "_Bool",
    "char",
    "signed char",
    "unsigned char",
    "short",
    "unsigned short",
    "int",
    "unsigned int",
    "long",
    "unsigned long",
    "long long",
    "unsigned long long",
    "__int128",
    "unsigned __int128",
];
const EXPRS: &[&str] = &[
    "DeclRefExpr",
    "IntegerLiteral",
    "FloatingLiteral",
    "CharacterLiteral",
    "StringLiteral",
    "ParenExpr",
    "ImplicitCastExpr",
    "CStyleCastExpr",
    "UnaryOperator",
    "BinaryOperator",
    "CompoundAssignOperator",
    "ConditionalOperator",
    "CallExpr",
    "ArraySubscriptExpr",
    "MemberExpr",
    "PredefinedExpr",
];
const PROTECTED: &[&str] = &[
    "CompoundLiteralExpr",
    "StmtExpr",
    "GenericSelectionExpr",
    "ChooseExpr",
    "UnaryExprOrTypeTraitExpr",
    "VAArgExpr",
    "AtomicExpr",
    "GCCAsmStmt",
    "MSAsmStmt",
    "AddrLabelExpr",
    "IndirectGotoStmt",
];
const OBSERVERS: &[&str] = &[
    "setjmp",
    "_setjmp",
    "sigsetjmp",
    "__builtin_setjmp",
    "__builtin_constant_p",
    "__builtin_object_size",
    "__builtin_dynamic_object_size",
    "__builtin_frame_address",
    "__builtin_return_address",
];
const C_PUNCT: &[&str] = &[
    "[", "]", "(", ")", "{", "}", ".", "->", "++", "--", "&", "*", "+", "-", "~", "!", "/", "%",
    "<<", ">>", "<", ">", "<=", ">=", "==", "!=", "^", "|", "&&", "||", "?", ":", ";", "...", "=",
    "*=", "/=", "%=", "+=", "-=", "<<=", ">>=", "&=", "^=", "|=", ",", "#", "##", "<:", ":>", "<%",
    "%>", "%:", "%:%:",
];

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct CFlowOptions {
    pub clang: String,
    pub standard: String,
    pub compiler_args: Vec<String>,
    pub source_path: Option<PathBuf>,
    pub token_contract: String,
    pub max_variants: usize,
    pub max_passes: usize,
    /// Include valid equal/longer source edits for an external whole-file cost
    /// comparison. This never weakens the semantic or frontend guards.
    pub include_nonshrinking: bool,
    /// Emit bounded single-edit alternatives after the legacy rule portfolio.
    pub individual_edits: usize,
    pub frontend_seconds: f64,
    pub frontend_memory_bytes: u64,
    pub ast_bytes: usize,
}
impl Default for CFlowOptions {
    fn default() -> Self {
        Self {
            clang: "clang".into(),
            standard: "c11".into(),
            compiler_args: vec![],
            source_path: None,
            token_contract: "opaque".into(),
            max_variants: 16,
            max_passes: 2,
            include_nonshrinking: false,
            individual_edits: 0,
            frontend_seconds: 30.0,
            frontend_memory_bytes: 1 << 30,
            ast_bytes: 32 << 20,
        }
    }
}

pub use crate::c_frontend::validate_args;
pub(crate) use crate::c_frontend::FrontendOutputLimit;
#[cfg(test)]
use crate::c_frontend::{check_frontend_output, frontend_syntax_probe};

impl From<&CFlowOptions> for FrontendConfig {
    fn from(options: &CFlowOptions) -> Self {
        Self {
            clang: options.clang.clone(),
            standard: options.standard.clone(),
            compiler_args: options.compiler_args.clone(),
            source_path: options.source_path.clone(),
            seconds: options.frontend_seconds,
            memory_bytes: options.frontend_memory_bytes,
            ast_bytes: options.ast_bytes,
        }
    }
}

fn analysis_from_snapshot(
    source: &[u8],
    snapshot: ParsedSource,
    options: &CFlowOptions,
    tokens: Vec<Token>,
) -> Result<Analysis> {
    Analysis::new(
        std::str::from_utf8(source)?.to_owned(),
        snapshot.tree,
        snapshot.main_path,
        snapshot.macros,
        options.include_nonshrinking,
        tokens,
    )
}

fn parse_analysis(
    frontend: &FrontendSession,
    source: &[u8],
    options: &CFlowOptions,
) -> Result<Analysis> {
    let tokens = lex(std::str::from_utf8(source)?, "c")?
        .into_iter()
        .filter(|t| !matches!(t.kind, "space" | "comment"))
        .collect();
    analysis_from_snapshot(source, frontend.parse(source, true)?, options, tokens)
}

#[derive(Clone, Debug)]
struct Node {
    value: Value,
    inner: Vec<usize>,
    slots: Vec<Option<usize>>,
    parent: Option<usize>,
}
#[derive(Clone, Debug)]
struct Edit {
    start: usize,
    end: usize,
    text: String,
    rule: String,
    proof: String,
    function: String,
}
struct Analysis {
    source: String,
    nodes: Vec<Node>,
    tokens: Vec<Token>,
    main_path: String,
    declarations: HashMap<String, usize>,
    macros: HashSet<String>,
    functions: Vec<(usize, usize)>,
    notes: Vec<String>,
    include_nonshrinking: bool,
}
fn flatten(mut value: Value, parent: Option<usize>, nodes: &mut Vec<Node>) -> usize {
    // The removed array is already owned. Cloning it here recursively copied
    // every descendant again at each ancestor before flattening the same AST.
    let inner = match value.as_object_mut().and_then(|m| m.remove("inner")) {
        Some(Value::Array(inner)) => inner,
        _ => Vec::new(),
    };
    let id = nodes.len();
    nodes.push(Node {
        value,
        inner: vec![],
        slots: vec![],
        parent,
    });
    for item in inner {
        if item.get("kind").and_then(Value::as_str).is_some() {
            let child = flatten(item, Some(id), nodes);
            nodes[id].inner.push(child);
            nodes[id].slots.push(Some(child));
        } else {
            nodes[id].slots.push(None);
        }
    }
    id
}
fn ordinary(typ: &str) -> bool {
    INTEGERS.contains(&typ)
        || (typ.contains('*')
            && !["volatile", "_Atomic", "__attribute__"]
                .iter()
                .any(|s| typ.contains(s)))
}
fn op_precedence(op: &str) -> u8 {
    match op {
        "," => 1,
        "=" | "+=" | "-=" | "*=" | "/=" | "%=" | "&=" | "|=" | "^=" | "<<=" | ">>=" => 2,
        "||" => 4,
        "&&" => 5,
        "|" => 6,
        "^" => 7,
        "&" => 8,
        "==" | "!=" => 9,
        "<" | ">" | "<=" | ">=" => 10,
        "<<" | ">>" => 11,
        "+" | "-" => 12,
        "*" | "/" | "%" => 13,
        _ => 0,
    }
}
impl Analysis {
    fn new(
        source: String,
        tree: Value,
        main_path: String,
        macros: HashSet<String>,
        include_nonshrinking: bool,
        tokens: Vec<Token>,
    ) -> Result<Self> {
        let mut result = Self {
            source,
            nodes: vec![],
            tokens,
            main_path,
            declarations: HashMap::new(),
            macros,
            functions: vec![],
            notes: vec![],
            include_nonshrinking,
        };
        flatten(tree, None, &mut result.nodes);
        for (i, node) in result.nodes.iter().enumerate() {
            if result.kind(i).ends_with("Decl") {
                if let Some(id) = node.value["id"].as_str() {
                    result.declarations.insert(id.into(), i);
                }
            }
        }
        for id in result.nodes[0].inner.clone() {
            if result.kind(id) != "FunctionDecl" {
                continue;
            }
            let Some(body) = result.nodes[id]
                .inner
                .iter()
                .copied()
                .find(|&n| result.kind(n) == "CompoundStmt")
            else {
                continue;
            };
            let loc = &result.nodes[id].value["loc"];
            if loc.get("includedFrom").is_some()
                || loc["file"].as_str().unwrap_or(&result.main_path) != result.main_path
                || result.span(body).is_none()
            {
                continue;
            }
            if let Some(reason) = result.protection(body) {
                result.notes.push(format!(
                    "function {} left unchanged: {reason}",
                    result.name(id)
                ));
            } else {
                result.functions.push((id, body));
            }
        }
        Ok(result)
    }
    fn kind(&self, n: usize) -> &str {
        self.nodes[n].value["kind"].as_str().unwrap_or("")
    }
    fn name(&self, n: usize) -> &str {
        self.nodes[n].value["name"].as_str().unwrap_or("?")
    }
    fn op(&self, n: usize) -> &str {
        self.nodes[n].value["opcode"].as_str().unwrap_or("")
    }
    fn typ(&self, n: usize) -> &str {
        let t = &self.nodes[n].value["type"];
        let typ = t["desugaredQualType"]
            .as_str()
            .or_else(|| t["qualType"].as_str())
            .unwrap_or("");
        // Clang can print C's built-in _Bool as `bool` when <stdbool.h> is
        // active. Desugar first: a user typedef such as `typedef int bool`
        // must remain int, not acquire a Boolean-domain proof by its name.
        if typ == "bool" {
            "_Bool"
        } else {
            typ
        }
    }
    fn unwrap(&self, mut n: usize) -> usize {
        while matches!(self.kind(n), "ImplicitCastExpr" | "ParenExpr")
            && self.nodes[n].inner.len() == 1
        {
            n = self.nodes[n].inner[0];
        }
        n
    }
    fn value_type(&self, mut n: usize) -> &str {
        while self.nodes[n].inner.len() == 1 {
            if self.kind(n) == "ParenExpr" {
                n = self.nodes[n].inner[0];
            } else if self.kind(n) == "ImplicitCastExpr" {
                if matches!(
                    self.nodes[n].value["castKind"].as_str(),
                    Some("LValueToRValue" | "ArrayToPointerDecay" | "FunctionToPointerDecay")
                ) {
                    return self.typ(n);
                }
                n = self.nodes[n].inner[0];
            } else {
                break;
            }
        }
        self.typ(n)
    }
    fn same_values(&self, a: usize, b: usize, void: bool) -> bool {
        self.value_type(a) == self.value_type(b)
            && (ordinary(self.value_type(a)) || void && self.value_type(a) == "void")
    }
    fn literal(&self, n: usize, value: &str, int_only: bool) -> bool {
        let n = self.unwrap(n);
        self.kind(n) == "IntegerLiteral"
            && self.nodes[n].value["value"].as_str() == Some(value)
            && (!int_only || self.typ(n) == "int")
    }
    fn boolean_result(&self, n: usize) -> bool {
        let n = self.unwrap(n);
        self.typ(n) == "int"
            && (self.kind(n) == "UnaryOperator" && self.op(n) == "!"
                || self.kind(n) == "BinaryOperator"
                    && matches!(
                        self.op(n),
                        "==" | "!=" | "<" | ">" | "<=" | ">=" | "&&" | "||"
                    ))
    }
    /// Prove the evaluated source value belongs to {0, 1}; do not infer a range
    /// from sampled outputs or from the destination of a later conversion.
    fn boolean_domain(&self, n: usize) -> bool {
        // Keep the source value type before stripping casts. In particular,
        // lvalue-to-rvalue removes const from an actual _Bool object; an int
        // converted to _Bool only by a surrounding context is not a proof.
        if self.value_type(n) == "_Bool" {
            return true;
        }
        let n = self.unwrap(n);
        if self.boolean_result(n) {
            return true;
        }
        if self.kind(n) == "IntegerLiteral"
            && INTEGERS.contains(&self.typ(n))
            && matches!(self.nodes[n].value["value"].as_str(), Some("0" | "1"))
        {
            return true;
        }
        // A signed one-bit field can hold -1 and therefore is not Boolean.
        // Restrict this extension to C's standard unsigned-int bitfield form.
        if self.kind(n) == "MemberExpr" && self.typ(n) == "unsigned int" {
            return self.nodes[n].value["referencedMemberDecl"]
                .as_str()
                .and_then(|id| self.declarations.get(id))
                .is_some_and(|&field| {
                    self.kind(field) == "FieldDecl"
                        && self.nodes[field].value["isBitfield"].as_bool() == Some(true)
                        && self.nodes[field].inner.first().is_some_and(|&width| {
                            matches!(self.kind(width), "ConstantExpr" | "IntegerLiteral")
                                && self.nodes[width].value["value"].as_str() == Some("1")
                        })
                });
        }
        false
    }
    fn binding(&self, n: usize) -> Option<&str> {
        let n = self.unwrap(n);
        if self.kind(n) == "DeclRefExpr" {
            self.nodes[n].value["referencedDecl"]["id"].as_str()
        } else {
            None
        }
    }
    fn precedence(&self, mut n: usize) -> u8 {
        while self.kind(n) == "ImplicitCastExpr" && self.nodes[n].inner.len() == 1 {
            n = self.nodes[n].inner[0];
        }
        match self.kind(n) {
            "BinaryOperator" | "CompoundAssignOperator" => op_precedence(self.op(n)),
            "ConditionalOperator" => 3,
            "UnaryOperator" | "CStyleCastExpr" => {
                if self.nodes[n].value["isPostfix"].as_bool() == Some(true) {
                    15
                } else {
                    14
                }
            }
            _ => 16,
        }
    }
    fn walk(&self, n: usize) -> Vec<usize> {
        let mut todo = vec![n];
        let mut out = vec![];
        while let Some(n) = todo.pop() {
            out.push(n);
            todo.extend(self.nodes[n].inner.iter().rev().copied());
        }
        out
    }
    fn span(&self, n: usize) -> Option<(usize, usize)> {
        let r = &self.nodes[n].value["range"];
        let (begin, end) = (&r["begin"], &r["end"]);
        for p in [begin, end] {
            if ["spellingLoc", "expansionLoc", "includedFrom"]
                .iter()
                .any(|k| p.get(k).is_some())
                || p["file"].as_str().unwrap_or(&self.main_path) != self.main_path
            {
                return None;
            }
        }
        let a = begin["offset"].as_u64()? as usize;
        let b = end["offset"].as_u64()? as usize;
        let length = end["tokLen"].as_u64()? as usize;
        let end = b.checked_add(length)?;
        if a <= b
            && b < end
            && end <= self.source.len()
            && self.source.is_char_boundary(a)
            && self.source.is_char_boundary(end)
        {
            Some((a, end))
        } else {
            None
        }
    }
    fn text(&self, n: usize) -> String {
        self.span(n)
            .map(|(a, b)| self.source[a..b].to_string())
            .unwrap_or_default()
    }
    fn expression(&self, n: usize, minimum: u8) -> String {
        let text = self.text(n);
        if self.precedence(n) < minimum {
            format!("({text})")
        } else {
            text
        }
    }
    fn next_token(&self, offset: usize) -> Option<&Token> {
        self.tokens
            .get(self.tokens.partition_point(|t| t.start < offset))
    }
    fn statement_span(&self, n: usize) -> Option<(usize, usize)> {
        let span = self.span(n)?;
        if self.kind(n) == "CompoundStmt" {
            return Some(span);
        }
        if self.kind(n) == "IfStmt" {
            return Some((span.0, self.statement_span(*self.nodes[n].inner.last()?)?.1));
        }
        if EXPRS.contains(&self.kind(n))
            || matches!(
                self.kind(n),
                "ReturnStmt" | "BreakStmt" | "ContinueStmt" | "NullStmt"
            )
        {
            if &self.source[span.1 - 1..span.1] == ";" {
                return Some(span);
            }
            let token = self.next_token(span.1)?;
            if token.text == ";" {
                return Some((span.0, token.end));
            }
        }
        None
    }
    fn protection(&self, n: usize) -> Option<String> {
        if let Some((a, b)) = self.span(n) {
            for t in self.tokens.iter().filter(|t| a <= t.start && t.start < b) {
                if t.kind == "identifier"
                    && (self.macros.contains(&t.text)
                        || matches!(t.text.as_str(), "_Pragma" | "__pragma"))
                {
                    return Some("macro or pragma operator in source tokens, including AST-invisible preprocessing effects".into());
                }
                if t.kind == "directive" {
                    return Some("preprocessing directive in function body".into());
                }
            }
        }
        for n in self.walk(n) {
            let kind = self.kind(n);
            let typ = self.typ(n);
            if self.span(n).is_none() && self.nodes[n].value.get("range").is_some() {
                return Some("macro expansion or non-main-file source location".into());
            }
            if PROTECTED.contains(&kind) || kind.ends_with("Attr") {
                return Some(format!("context/lifetime-sensitive AST construct: {kind}"));
            }
            if typ.contains("volatile") || typ.contains("_Atomic") {
                return Some("volatile or atomic access/type".into());
            }
            if kind == "CallExpr" {
                let callee = self.nodes[n].inner.first().copied().map(|x| self.unwrap(x));
                if !callee.is_some_and(|c| {
                    self.kind(c) == "DeclRefExpr"
                        && self.nodes[c].value["referencedDecl"]["kind"] == "FunctionDecl"
                }) {
                    return Some("indirect call: target context/returns-twice attributes are not established".into());
                }
                if !(ordinary(typ) || matches!(typ, "void" | "float" | "double" | "long double")) {
                    return Some("aggregate or unsupported call result lifetime".into());
                }
            }
            if kind == "DeclRefExpr" {
                let refer = &self.nodes[n].value["referencedDecl"];
                let observing = refer["name"]
                    .as_str()
                    .is_some_and(|s| OBSERVERS.contains(&s));
                let twice = refer["id"]
                    .as_str()
                    .and_then(|id| self.declarations.get(id))
                    .is_some_and(|&id| {
                        self.nodes[id]
                            .inner
                            .iter()
                            .any(|&n| self.kind(n) == "ReturnsTwiceAttr")
                    });
                if observing || twice {
                    return Some("source/context observation or returns-twice call".into());
                }
            }
            if kind.ends_with("Expr") && !EXPRS.contains(&kind) {
                return Some(format!("unsupported expression kind: {kind}"));
            }
        }
        None
    }
    fn leaf(&self, n: usize) -> Option<usize> {
        if self.kind(n) == "CompoundStmt" {
            if self.nodes[n].inner.len() != 1 {
                return None;
            }
            let child = self.nodes[n].inner[0];
            if EXPRS.contains(&self.kind(child))
                || matches!(
                    self.kind(child),
                    "ReturnStmt" | "BreakStmt" | "ContinueStmt"
                )
            {
                Some(child)
            } else {
                None
            }
        } else {
            Some(n)
        }
    }
    fn safe_rhs(&self, n: usize) -> bool {
        self.walk(n).into_iter().all(|n| {
            !matches!(self.kind(n), "CallExpr" | "CompoundAssignOperator")
                && !(self.kind(n) == "BinaryOperator" && self.op(n) == "=")
                && !(self.kind(n) == "UnaryOperator" && matches!(self.op(n), "++" | "--"))
        })
    }
    fn fit_parent(&self, mut n: usize, text: String, prec: u8) -> String {
        let mut parent = self.nodes[n].parent;
        while parent.is_some_and(|p| self.kind(p) == "ImplicitCastExpr") {
            n = parent.unwrap();
            parent = self.nodes[n].parent;
        }
        let Some(p) = parent else { return text };
        let protect = match self.kind(p) {
            "ParenExpr" | "ReturnStmt" | "IfStmt" | "WhileStmt" | "DoStmt" | "ForStmt"
            | "CompoundStmt" => false,
            "BinaryOperator"
            | "CompoundAssignOperator"
            | "ConditionalOperator"
            | "UnaryOperator"
            | "CStyleCastExpr" => prec <= self.precedence(p),
            "CallExpr" | "ArraySubscriptExpr" | "InitListExpr" | "VarDecl" => prec < 2,
            _ => prec < 16,
        };
        if protect {
            format!("({text})")
        } else {
            text
        }
    }
    fn separate(&self, start: usize, end: usize, mut text: String) -> Result<String> {
        let generated: Vec<_> = lex(&text, "c")?
            .into_iter()
            .filter(|t| !matches!(t.kind, "space" | "comment"))
            .collect();
        if generated.is_empty() {
            return Ok(text);
        }
        let merges = |a: &Token, b: &Token| -> Result<bool> {
            let together = lex(&format!("{}{}", a.text, b.text), "c")?;
            Ok(together
                .iter()
                .map(|t| (t.kind, t.text.as_str()))
                .collect::<Vec<_>>()
                != vec![(a.kind, a.text.as_str()), (b.kind, b.text.as_str())])
        };
        let before = self
            .tokens
            .partition_point(|t| t.start < start)
            .checked_sub(1);
        let after = self.tokens.partition_point(|t| t.start < end);
        let original_len = text.len();
        if let Some(before) = before {
            if self.tokens[before].end == start
                && generated[0].start == 0
                && merges(&self.tokens[before], &generated[0])?
            {
                text.insert(0, ' ');
            }
        }
        if let Some(after) = self.tokens.get(after) {
            if after.start == end
                && generated.last().unwrap().end == original_len
                && merges(generated.last().unwrap(), after)?
            {
                text.push(' ');
            }
        }
        Ok(text)
    }
    #[allow(clippy::too_many_arguments)]
    fn add(
        &self,
        edits: &mut Vec<Edit>,
        enabled: &HashSet<&str>,
        function: &str,
        n: usize,
        text: String,
        rule: &str,
        proof: &str,
        range: Option<(usize, usize)>,
        prec: Option<u8>,
    ) -> Result<()> {
        if !enabled.contains(rule) {
            return Ok(());
        }
        let Some((start, end)) = range.or_else(|| self.span(n)) else {
            return Ok(());
        };
        let text = if let Some(p) = prec {
            self.fit_parent(n, text, p)
        } else {
            text
        };
        let text = self.separate(start, end, text)?;
        if self
            .tokens
            .iter()
            .any(|t| start <= t.start && t.start < end && t.kind == "directive")
        {
            return Ok(());
        }
        if text != self.source[start..end]
            && (self.include_nonshrinking || text.len() < end - start)
        {
            edits.push(Edit {
                start,
                end,
                text,
                rule: rule.into(),
                proof: proof.into(),
                function: function.into(),
            });
        }
        Ok(())
    }
    fn ternary(&self, condition: usize, left: usize, right: usize) -> String {
        format!(
            "{}?{}:{}",
            self.expression(condition, 4),
            self.expression(left, 1),
            self.expression(right, 3)
        )
    }
    #[allow(clippy::too_many_arguments)]
    fn returns(
        &self,
        edits: &mut Vec<Edit>,
        enabled: &HashSet<&str>,
        function: &str,
        condition: usize,
        left: Option<usize>,
        right: Option<usize>,
        owner: usize,
        range: Option<(usize, usize)>,
        rule: &str,
    ) -> Result<()> {
        if let (Some(left), Some(right)) = (left, right) {
            if self.kind(left) == "ReturnStmt"
                && self.kind(right) == "ReturnStmt"
                && self.nodes[left].inner.len() == 1
                && self.nodes[right].inner.len() == 1
            {
                let a = self.nodes[left].inner[0];
                let b = self.nodes[right].inner[0];
                if self.same_values(a, b, false) {
                    self.add(edits, enabled, function, owner, format!("return {};", self.ternary(condition, a, b)), rule, "same source value type before return conversion; condition once, selected operand once", range, None)?;
                }
            }
        }
        Ok(())
    }
    fn find(&self, enabled: &HashSet<&str>) -> Result<Vec<Edit>> {
        let mut edits = vec![];
        for &(declaration, body) in &self.functions {
            let function = self.name(declaration);
            for n in self.walk(body) {
                let kind = self.kind(n);
                let inner = &self.nodes[n].inner;
                if kind == "IfStmt" && matches!(inner.len(), 2 | 3) {
                    let condition = inner[0];
                    let left = self.leaf(inner[1]);
                    if inner.len() == 3 && self.nodes[n].value["hasElse"].as_bool() == Some(true) {
                        let right = self.leaf(inner[2]);
                        self.returns(
                            &mut edits,
                            enabled,
                            function,
                            condition,
                            left,
                            right,
                            n,
                            self.statement_span(n),
                            "if-return",
                        )?;
                        if let (Some(left), Some(right)) = (left, right) {
                            if self.kind(left) == "BinaryOperator"
                                && self.kind(right) == "BinaryOperator"
                                && self.op(left) == "="
                                && self.op(right) == "="
                            {
                                let la = &self.nodes[left].inner;
                                let ra = &self.nodes[right].inner;
                                if la.len() == 2
                                    && ra.len() == 2
                                    && self.binding(la[0]).is_some()
                                    && self.binding(la[0]) == self.binding(ra[0])
                                    && ordinary(self.typ(self.unwrap(la[0])))
                                    && self.same_values(la[1], ra[1], false)
                                {
                                    self.add(&mut edits, enabled, function, n, format!("{}={};", self.text(la[0]), self.ternary(condition, la[1], ra[1])), "if-assignment", "same ordinary plain binding; matching pre-assignment RHS types; one selected store", self.statement_span(n), None)?;
                                }
                            }
                            if EXPRS.contains(&self.kind(left))
                                && EXPRS.contains(&self.kind(right))
                                && self.same_values(left, right, true)
                            {
                                self.add(&mut edits, enabled, function, n, format!("{};", self.ternary(condition, left, right)), "if-effect", "discarded same-type or void expressions; selected branch and short-circuit order unchanged", self.statement_span(n), None)?;
                            }
                        }
                    } else if inner.len() == 2 {
                        if let Some(left) = left.filter(|&l| {
                            EXPRS.contains(&self.kind(l)) && ordinary(self.value_type(l))
                        }) {
                            self.add(&mut edits, enabled, function, n, format!("{}&&{};", self.expression(condition, 5), self.expression(left, 6)), "guard", "discarded integer/pointer result; condition then selected effect once", self.statement_span(n), None)?;
                        }
                    }
                }
                if kind == "CompoundStmt" {
                    for pair in inner.windows(2) {
                        let (first, second) = (pair[0], pair[1]);
                        let ci = &self.nodes[first].inner;
                        if self.kind(first) == "IfStmt"
                            && ci.len() == 2
                            && self.nodes[first].value["hasElse"].as_bool() != Some(true)
                            && self.kind(second) == "ReturnStmt"
                        {
                            if let (Some(a), Some(b)) =
                                (self.span(first), self.statement_span(second))
                            {
                                self.returns(
                                    &mut edits,
                                    enabled,
                                    function,
                                    ci[0],
                                    self.leaf(ci[1]),
                                    Some(second),
                                    first,
                                    Some((a.0, b.1)),
                                    "return-tail",
                                )?;
                            }
                        }
                    }
                }
                if kind == "ConditionalOperator" && inner.len() == 3 && self.typ(n) == "int" {
                    let (condition, left, right) = (inner[0], inner[1], inner[2]);
                    if self.literal(left, "1", true) && self.literal(right, "0", true) {
                        let (text, prec) = if self.boolean_result(condition) {
                            (self.text(condition), self.precedence(condition))
                        } else {
                            (format!("!!{}", self.expression(condition, 14)), 14)
                        };
                        self.add(
                            &mut edits,
                            enabled,
                            function,
                            n,
                            text,
                            "boolean",
                            "exact C int 0/1 result; one scalar truth evaluation",
                            None,
                            Some(prec),
                        )?;
                    } else if self.literal(left, "0", true) && self.literal(right, "1", true) {
                        self.add(
                            &mut edits,
                            enabled,
                            function,
                            n,
                            format!("!{}", self.expression(condition, 14)),
                            "boolean",
                            "exact C int 0/1 result; one scalar truth evaluation",
                            None,
                            Some(14),
                        )?;
                    }
                }
                if kind == "BinaryOperator" && inner.len() == 2 {
                    let (left, right) = (inner[0], inner[1]);
                    if matches!(self.op(n), "==" | "!=") {
                        let value = if self.literal(right, "0", false) {
                            Some(left)
                        } else if self.literal(left, "0", false) {
                            Some(right)
                        } else {
                            None
                        };
                        if let Some(value) = value {
                            self.add(&mut edits, enabled, function, n, format!("{}{}", if self.op(n) == "==" { "!" } else { "!!" }, self.expression(value, 14)), "zero-test", "C logical-not/equality-to-zero correspondence; one scalar read; int result", None, Some(14))?;
                        }
                        let value = if self.literal(right, "1", false) {
                            Some(left)
                        } else if self.literal(left, "1", false) {
                            Some(right)
                        } else {
                            None
                        };
                        if let Some(value) = value.filter(|&v| self.boolean_domain(v)) {
                            let (text, prec) = if self.op(n) == "!=" {
                                (format!("!{}", self.expression(value, 14)), 14)
                            } else if self.boolean_result(value) {
                                (self.text(value), self.precedence(value))
                            } else {
                                (format!("!!{}", self.expression(value, 14)), 14)
                            };
                            self.add(&mut edits, enabled, function, n, text, "boolean-domain", "source value proven in {0,1} by _Bool, Boolean operator, integer literal, or unsigned-int one-bit field; evaluation once and int comparison result preserved", None, Some(prec))?;
                        }
                    }
                    if self.op(n) == "="
                        && self.binding(left).is_some()
                        && ordinary(self.typ(self.unwrap(left)))
                    {
                        let rhs = self.unwrap(right);
                        let ri = &self.nodes[rhs].inner;
                        if self.kind(rhs) == "BinaryOperator"
                            && matches!(
                                self.op(rhs),
                                "+" | "-" | "*" | "/" | "%" | "&" | "|" | "^" | "<<" | ">>"
                            )
                            && ri.len() == 2
                            && self.binding(ri[0]) == self.binding(left)
                            && self.safe_rhs(ri[1])
                        {
                            self.add(&mut edits, enabled, function, n, format!("{}{}={}", self.text(left), self.op(rhs), self.expression(ri[1], 2)), "compound", "same ordinary plain binding; C compound-assignment conversion; no RHS call or mutation", None, Some(2))?;
                        }
                    }
                }
                if kind == "CompoundAssignOperator"
                    && inner.len() == 2
                    && matches!(self.op(n), "+=" | "-=")
                {
                    if self.binding(inner[0]).is_some()
                        && ordinary(self.typ(self.unwrap(inner[0])))
                        && self.literal(inner[1], "1", true)
                    {
                        self.add(&mut edits, enabled, function, n, format!("{}{}", if self.op(n) == "+=" { "++" } else { "--" }, self.expression(inner[0], 14)), "increment", "plain ordinary binding; exact source int literal 1; prefix yields stored new value", None, Some(14))?;
                    }
                }
                if kind == "UnaryOperator" && self.op(n) == "!" && inner.len() == 1 {
                    let operand = self.unwrap(inner[0]);
                    let oi = &self.nodes[operand].inner;
                    if self.kind(operand) == "UnaryOperator"
                        && self.op(operand) == "!"
                        && oi.len() == 1
                        && self.boolean_result(oi[0])
                    {
                        self.add(
                            &mut edits,
                            enabled,
                            function,
                            n,
                            self.text(oi[0]),
                            "boolean",
                            "double negation of an existing int 0/1 result",
                            None,
                            Some(self.precedence(oi[0])),
                        )?;
                    }
                    if self.kind(operand) == "BinaryOperator" && oi.len() == 2 {
                        let op = self.op(operand);
                        if matches!(op, "&&" | "||") {
                            let replacement = if op == "&&" { "||" } else { "&&" };
                            self.add(&mut edits, enabled, function, n, format!("!{}{}!{}", self.expression(oi[0], 14), replacement, self.expression(oi[1], 14)), "negation", "De Morgan over C truth values; same left-before-right short-circuit decision; int 0/1 result", None, Some(op_precedence(replacement)))?;
                        }
                        if let Some(replacement) = match op {
                            "==" => Some("!="),
                            "!=" => Some("=="),
                            "<" => Some(">="),
                            ">" => Some("<="),
                            "<=" => Some(">"),
                            ">=" => Some("<"),
                            _ => None,
                        } {
                            if matches!(op, "==" | "!=")
                                || oi.iter().all(|&x| ordinary(self.value_type(x)))
                            {
                                let prec = op_precedence(replacement);
                                self.add(&mut edits, enabled, function, n, format!("{}{}{}", self.expression(oi[0], prec + 1), replacement, self.expression(oi[1], prec + 1)), "negation", "complementary comparison; relational inversion excludes floating-point NaNs", None, Some(prec))?;
                            }
                        }
                    }
                }
                let truth_nodes: Vec<_> = match kind {
                    "IfStmt" | "WhileStmt" | "ConditionalOperator" => {
                        inner.first().copied().into_iter().collect()
                    }
                    "DoStmt" => inner.last().copied().into_iter().collect(),
                    "ForStmt" if self.nodes[n].slots.len() == 5 => {
                        self.nodes[n].slots[2].into_iter().collect()
                    }
                    "BinaryOperator" if matches!(self.op(n), "&&" | "||") => inner.clone(),
                    _ => vec![],
                };
                for value in truth_nodes {
                    let plain = self.unwrap(value);
                    let vi = &self.nodes[plain].inner;
                    let mut replacement = None;
                    if self.kind(plain) == "BinaryOperator"
                        && self.op(plain) == "!="
                        && vi.len() == 2
                    {
                        replacement = if self.literal(vi[1], "0", false) {
                            Some(vi[0])
                        } else if self.literal(vi[0], "0", false) {
                            Some(vi[1])
                        } else {
                            None
                        };
                    } else if self.kind(plain) == "UnaryOperator"
                        && self.op(plain) == "!"
                        && vi.len() == 1
                    {
                        let nested = self.unwrap(vi[0]);
                        if self.kind(nested) == "UnaryOperator"
                            && self.op(nested) == "!"
                            && self.nodes[nested].inner.len() == 1
                        {
                            replacement = Some(self.nodes[nested].inner[0]);
                        }
                    }
                    if let Some(replacement) = replacement {
                        self.add(&mut edits, enabled, function, value, self.text(replacement), "truth", "only a scalar controlling or short-circuit context consumes this value", None, Some(self.precedence(replacement)))?;
                    }
                }
                if kind == "CompoundStmt" && n != body {
                    if self.nodes[n].parent.is_some_and(|p| {
                        matches!(self.kind(p), "IfStmt" | "WhileStmt" | "ForStmt" | "DoStmt")
                    }) {
                        if let Some(leaf) = self.leaf(n) {
                            if let Some(span) = self.statement_span(leaf) {
                                self.add(&mut edits, enabled, function, n, self.source[span.0..span.1].to_string(), "leaf-braces", "single non-declaration leaf; no label, nested if or compound-literal lifetime; function scope retained", None, None)?;
                            }
                        }
                    }
                }
                if kind == "WhileStmt" && !self.macros.contains("for") && inner.len() == 2 {
                    let condition = self.unwrap(inner[0]);
                    if self.kind(condition) == "IntegerLiteral"
                        && self.nodes[condition].value["value"]
                            .as_str()
                            .is_some_and(|x| x != "0")
                    {
                        if let (Some(a), Some(b)) = (self.span(n), self.span(inner[1])) {
                            self.add(&mut edits, enabled, function, n, "for(;;)".into(), "forever", "nonzero integer-literal control; identical loop body and continue/break targets", Some((a.0, b.0)), None)?;
                        }
                    }
                }
            }
        }
        Ok(edits)
    }
}
fn apply_pass(analysis: &Analysis, enabled: &HashSet<&str>) -> Result<(Vec<u8>, Vec<Value>)> {
    let mut edits = analysis.find(enabled)?;
    edits.sort_by(|a, b| {
        let saved_a = (a.end - a.start) as i64 - a.text.len() as i64;
        let saved_b = (b.end - b.start) as i64 - b.text.len() as i64;
        saved_b
            .cmp(&saved_a)
            .then_with(|| (a.start, a.end, &a.rule).cmp(&(b.start, b.end, &b.rule)))
    });
    let mut selected: Vec<Edit> = vec![];
    for edit in edits {
        if !selected
            .iter()
            .any(|old| edit.start < old.end && old.start < edit.end)
        {
            selected.push(edit);
        }
    }
    selected.sort_by_key(|e| std::cmp::Reverse(e.start));
    let mut source = analysis.source.clone();
    let mut audit = vec![];
    for e in selected {
        audit.push(json!({"start":e.start,"end":e.end,"before":&source[e.start..e.end],"after":e.text,"rule":e.rule,"proof":e.proof,"function":e.function,"source_bytes_saved":(e.end-e.start) as i64-e.text.len() as i64}));
        source.replace_range(e.start..e.end, &e.text);
    }
    audit.reverse();
    Ok((source.into_bytes(), audit))
}

pub fn generate_variants(source: &[u8], options: &CFlowOptions) -> Result<Vec<Variant>> {
    generate_variants_inner(source, options, None)
}

fn undiscovered_coverage(options: &CFlowOptions, reason: &str) -> Value {
    json!({"scope":"registered guarded C flow recipes","status":"inapplicable",
        "reason":reason,"discovery":"not performed","generated_variants":1,
        "max_variants":options.max_variants,"max_passes":options.max_passes,
        "individual_edit_limit":options.individual_edits,"all_edit_combinations_explored":false})
}

pub(crate) fn generate_variants_with_snapshot(
    source: &[u8],
    options: &CFlowOptions,
    frontend: &FrontendSession,
    snapshot: &ParsedSource,
    tokens: &[Token],
) -> Result<Vec<Variant>> {
    generate_variants_inner(source, options, Some((frontend, snapshot, tokens)))
}

fn generate_variants_inner(
    source: &[u8],
    options: &CFlowOptions,
    prepared: Option<(&FrontendSession, &ParsedSource, &[Token])>,
) -> Result<Vec<Variant>> {
    if source.len() > MAX_SOURCE {
        bail!("source exceeds {MAX_SOURCE} bytes");
    }
    if !matches!(
        options.token_contract.as_str(),
        "opaque" | "no-token-observation" | "preprocessed"
    ) {
        bail!("unknown source/token contract");
    }
    if !(1..=128).contains(&options.max_variants)
        || !(1..=8).contains(&options.max_passes)
        || options.individual_edits > 128
    {
        bail!("max_variants must be 1..128, max_passes 1..8 and individual_edits 0..128");
    }
    FrontendConfig::from(options).validate()?;
    let mut contract = json!({"language":"c","token_contract":options.token_contract,"standard":options.standard,"source_sha256":crate::sha256(source),"compiler_args":options.compiler_args,"include_nonshrinking":options.include_nonshrinking,"individual_edits":options.individual_edits,"required_acceptance":"fixed compatible frontend/ABI, compilation and application verification; final submitted-file size selection","proof_scope":"guarded local C rules; not whole-program equivalence proof","implementation":"native Rust"});
    let mut result = vec![Variant::new(
        "raw",
        source,
        source.into(),
        vec![],
        vec![],
        contract.clone(),
    )];
    let reason = if options.token_contract == "opaque" {
        Some("source/token/location non-observation has not been declared")
    } else if source.windows(2).any(|x| matches!(x, b"\\\n" | b"??"))
        || source.windows(3).any(|x| x == b"\\\r\n")
        || source.contains(&0)
    {
        Some(
            "line splicing, trigraph-like input or NUL is outside the byte-range frontend contract",
        )
    } else {
        None
    };
    if let Some(reason) = reason {
        result[0].notes.push(format!("identity only: {reason}"));
        result[0].contract["generation"] = undiscovered_coverage(options, reason);
        return Ok(result);
    }
    let text = match std::str::from_utf8(source) {
        Ok(s) => s,
        Err(_) => {
            result[0]
                .notes
                .push("identity only: unsupported source encoding; UTF-8 required".into());
            result[0].contract["generation"] =
                undiscovered_coverage(options, "unsupported source encoding; UTF-8 required");
            return Ok(result);
        }
    };
    let tokens = if let Some((_, _, tokens)) = prepared {
        tokens.to_vec()
    } else {
        lex(text, "c")?
            .into_iter()
            .filter(|t| !matches!(t.kind, "space" | "comment"))
            .collect()
    };
    if tokens.iter().any(|t| {
        t.kind == "punct" && !C_PUNCT.contains(&t.text.as_str())
            || !matches!(t.kind, "quoted" | "comment" | "space" | "directive") && !t.text.is_ascii()
    }) {
        result[0].notes.push("identity only: unsupported preprocessing token/identifier spelling; ASCII identifier splice boundaries are required".into());
        result[0].contract["generation"] = undiscovered_coverage(
            options,
            "unsupported preprocessing token/identifier spelling",
        );
        return Ok(result);
    }
    let owned_frontend;
    let (frontend, original) = if let Some((frontend, snapshot, _)) = prepared {
        if !frontend.matches(&FrontendConfig::from(options)) {
            bail!("flow frontend configuration differs from prepared snapshot");
        }
        (
            frontend,
            analysis_from_snapshot(source, snapshot.clone(), options, tokens)?,
        )
    } else {
        owned_frontend = FrontendSession::new(FrontendConfig::from(options), false)?;
        let original =
            analysis_from_snapshot(source, owned_frontend.parse(source, true)?, options, tokens)?;
        (&owned_frontend, original)
    };
    contract["frontend"] = frontend.info.clone();
    result[0].contract = contract.clone();
    let mut recipes = vec![(
        "c-all".to_string(),
        RULES.iter().copied().collect::<HashSet<_>>(),
    )];
    for rule in RULES {
        recipes.push((format!("c-{rule}"), HashSet::from([*rule])));
    }
    let registered_recipes = recipes.len();
    let selected_recipes = (options.max_variants - 1).min(registered_recipes);
    for (id, enabled) in recipes.into_iter().take(options.max_variants - 1) {
        let mut data = source.to_vec();
        let mut audits = vec![];
        let mut notes = original.notes.clone();
        let mut changed_analysis: Option<Analysis> = None;
        for pass in 0..options.max_passes {
            let analysis = changed_analysis.as_ref().unwrap_or(&original);
            let (changed, mut records) = apply_pass(analysis, &enabled)?;
            if records.is_empty() {
                break;
            }
            let checked = parse_analysis(frontend, &changed, options)?;
            let affected: HashSet<_> = records
                .iter()
                .filter_map(|r| r["function"].as_str())
                .collect();
            let eligible: HashSet<_> = checked
                .functions
                .iter()
                .map(|&(d, _)| checked.name(d))
                .collect();
            if !affected.is_subset(&eligible) {
                notes.push("pass inapplicable after frontend protection: newly context-sensitive or macro-expanded function".into());
                break;
            }
            for r in &mut records {
                r["pass"] = json!(pass + 1);
            }
            audits.extend(records);
            data = changed;
            changed_analysis = Some(checked);
        }
        if audits.is_empty() {
            notes.push("no applicable shorter rewrite for this recipe".into());
        }
        result.push(Variant::new(
            &id,
            source,
            data,
            audits,
            notes,
            contract.clone(),
        ));
    }
    let enabled = RULES.iter().copied().collect();
    let mut individuals = original.find(&enabled)?;
    individuals.sort_by(|a, b| {
        (a.start, a.end, &a.rule, &a.text).cmp(&(b.start, b.end, &b.rule, &b.text))
    });
    let discovered_individual_edits = individuals.len();
    let selected_individual_edits = options
        .individual_edits
        .min(options.max_variants - result.len())
        .min(discovered_individual_edits);
    let before_individuals = result.len();
    for (ordinal, e) in individuals
        .into_iter()
        .take(
            options
                .individual_edits
                .min(options.max_variants - result.len()),
        )
        .enumerate()
    {
        let mut data = original.source.clone();
        data.replace_range(e.start..e.end, &e.text);
        let checked = parse_analysis(frontend, data.as_bytes(), options)?;
        if !checked
            .functions
            .iter()
            .any(|&(d, _)| checked.name(d) == e.function)
        {
            continue;
        }
        let audit = json!({"start":e.start,"end":e.end,"before":&original.source[e.start..e.end],"after":e.text,"rule":e.rule,"proof":e.proof,"function":e.function,"source_bytes_saved":(e.end-e.start) as i64-e.text.len() as i64,"pass":1});
        result.push(Variant::new(
            &format!("c-one-{ordinal:03}-{}", e.rule),
            source,
            data.into_bytes(),
            vec![audit],
            original.notes.clone(),
            contract.clone(),
        ));
    }
    result[0].contract["generation"] = json!({
        "scope":"registered greedy non-overlap rule recipes plus bounded individual edits; not the edit powerset",
        "registered_rule_recipes":registered_recipes,"selected_rule_recipes":selected_recipes,
        "discovered_individual_edits":discovered_individual_edits,"selected_individual_edits":selected_individual_edits,
        "emitted_individual_variants":result.len()-before_individuals,"max_variants":options.max_variants,
        "generated_variants":result.len(),
        "individual_edit_limit":options.individual_edits,"max_passes":options.max_passes,
        "source_ast_reused":prepared.is_some(),"registered_recipe_space_exhausted":selected_recipes==registered_recipes && selected_individual_edits==discovered_individual_edits,
        "all_edit_combinations_explored":false});
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn frontend_capacity_is_typed_and_only_recognized_commands_get_syntax_probes() {
        let prefix = vec![
            "clang".to_string(),
            "-x".into(),
            "c".into(),
            "-mavx2".into(),
            "-DVALUE=2".into(),
        ];
        let mut expected = prefix.clone();
        expected.extend(["-fsyntax-only".into(), "translation.c".into()]);
        let mut ast = prefix.clone();
        ast.extend([
            "-fsyntax-only".into(),
            "-Xclang".into(),
            "-ast-dump=json".into(),
            "translation.c".into(),
        ]);
        assert_eq!(frontend_syntax_probe(&ast), Some(expected.clone()));
        let mut macros = prefix;
        macros.extend(["-E".into(), "-dD".into(), "translation.c".into()]);
        assert_eq!(frontend_syntax_probe(&macros), Some(expected.clone()));
        assert!(frontend_syntax_probe(&expected).is_none());
        assert!(frontend_syntax_probe(&["clang".into(), "--version".into()]).is_none());

        let output = |code, output_limited, timed_out| Output {
            code,
            stdout: b"partial".to_vec(),
            stderr: b"diagnostic".to_vec(),
            wall_seconds: 0.1,
            timed_out,
            output_limited,
        };
        let limited = check_frontend_output(output(125, true, false), "fixture", 17).unwrap_err();
        assert!(limited.downcast_ref::<FrontendOutputLimit>().is_some());
        for failed in [
            output(1, false, false),
            output(125, false, false),
            output(124, true, true),
        ] {
            assert!(check_frontend_output(failed, "fixture", 17)
                .unwrap_err()
                .downcast_ref::<FrontendOutputLimit>()
                .is_none());
        }
        assert_eq!(
            check_frontend_output(output(0, false, false), "fixture", 17).unwrap(),
            b"partial"
        );
    }

    fn options() -> Option<CFlowOptions> {
        let clang = std::env::var("NVCOMPACT_CLANG").unwrap_or_else(|_| "clang".into());
        if crate::process::resolve_tool(&clang).is_err() {
            eprintln!("Clang-dependent fixture not executed: set NVCOMPACT_CLANG");
            return None;
        }
        Some(CFlowOptions {
            clang,
            token_contract: "no-token-observation".into(),
            ..Default::default()
        })
    }
    fn compile_run(compiler: &str, source: &[u8], root: &Path, name: &str) -> Vec<u8> {
        let input = root.join(format!("{name}.c"));
        let output = root.join(name);
        std::fs::write(&input, source).unwrap();
        let built = run(
            &[
                compiler.into(),
                "-std=c11".into(),
                "-O0".into(),
                input.to_string_lossy().into_owned(),
                "-o".into(),
                output.to_string_lossy().into_owned(),
            ],
            b"",
            root,
            &Limits::default(),
        )
        .unwrap();
        built.check("compile C semantic fixture").unwrap();
        let result = run(
            &[output.to_string_lossy().into_owned()],
            b"",
            root,
            &Limits::default(),
        )
        .unwrap();
        result.check("execute C semantic fixture").unwrap();
        assert!(result.stderr.is_empty());
        result.stdout
    }
    #[test]
    fn opaque_and_unsupported_spelling_never_start_frontend() {
        let options = CFlowOptions {
            clang: "/does/not/exist".into(),
            ..Default::default()
        };
        let v = generate_variants(b"int f(void){return 1;}", &options).unwrap();
        assert_eq!(v.len(), 1);
        let options = CFlowOptions {
            token_contract: "no-token-observation".into(),
            ..options
        };
        for source in [
            b"int f(int c){int \\u03b1=1;if(c){\\u03b1=2;}else{\\u03b1=3;}return \\u03b1;}"
                .as_slice(),
            "int α=1;".as_bytes(),
            b"int $x;",
        ] {
            let v = generate_variants(source, &options).unwrap();
            assert_eq!(v.len(), 1);
            assert_eq!(v[0].data, source);
            assert!(!v[0].notes.is_empty());
        }
        assert!(validate_args(&["-Xclang".into(), "-load".into()]).is_err());
        assert!(validate_args(&[
            "-I".into(),
            "include dir".into(),
            "--target=x86_64-linux-gnu".into()
        ])
        .is_ok());
        assert!(validate_args(&["-mavx2".into(), "-msse4.2".into(), "-mcx16".into()]).is_ok());
    }
    #[test]
    fn full_portfolio_preserves_independent_integer_and_nan_oracle() {
        let Some(options) = options() else { return };
        let source = br#"#include <stdio.h>
int choose(int c){if(c)return 7;else return 9;}
int tail(int c){if(c)return 7;return 9;}
int assign(int c){int x;if(c){x=7;}else{x=9;}return x;}
int effect(int c){int x=3;if(c){x++;}else{x--;}return x;}
int guard(int c){int x=3;if(c){x++;}return x;}
int boolean(int c){return c?1:0;}
int zero(int c){return c==0;}
int truth(int c){if(c!=0)return 1;return 0;}
int neg(int c){return !(c<2);}
int compound(int c){c=c+3;return c;}
int increment(int c){return c+=1;}
int leaf(int c){if(c){return 2;}return 3;}
int forever(int c){while(1){if(c--==0)break;}return c;}
int domain(_Bool c){return c!=1;}
unsigned long mixed(int c){if(c)return -1;else return 1U;}
int nan_guard(double x){return !(x<0);}
int main(void){for(int i=0;i<4;i++)printf("%d %d %d %d %d %d %d %d %d %d %d %d %d\n",choose(i),tail(i),assign(i),effect(i),guard(i),boolean(i),zero(i),truth(i),neg(i),compound(i),increment(i),leaf(i),forever(i));printf("%lu %d\n",mixed(1),nan_guard(__builtin_nan("")));printf("%d %d\n",domain(0),domain(1));}
"#;
        let variants = generate_variants(source, &options).unwrap();
        assert_eq!(variants.len(), RULES.len() + 2);
        assert!(variants.iter().find(|v| v.id == "c-all").unwrap().bytes < source.len());
        let exercised: HashSet<_> = variants
            .iter()
            .flat_map(|v| v.audit.iter())
            .filter_map(|r| r["rule"].as_str())
            .collect();
        assert_eq!(exercised, RULES.iter().copied().collect());
        assert!(!variants
            .iter()
            .flat_map(|v| v.audit.iter())
            .any(|r| r["function"] == "mixed"
                && matches!(r["rule"].as_str(), Some("if-return" | "return-tail"))));
        assert!(!variants
            .iter()
            .flat_map(|v| v.audit.iter())
            .any(|r| r["function"] == "nan_guard" && r["rule"] == "negation"));
        let mut expected = String::new();
        for i in 0..4 {
            let choose = if i != 0 { 7 } else { 9 };
            expected.push_str(&format!(
                "{choose} {choose} {choose} {} {} {} {} {} {} {} {} {} -1\n",
                if i != 0 { 4 } else { 2 },
                if i != 0 { 4 } else { 3 },
                i32::from(i != 0),
                i32::from(i == 0),
                i32::from(i != 0),
                i32::from(i >= 2),
                i + 3,
                i + 1,
                if i != 0 { 2 } else { 3 }
            ));
        }
        expected.push_str(&format!("{} 1\n", u64::MAX));
        expected.push_str("1 0\n");
        let directory = tempfile::tempdir().unwrap();
        for v in variants {
            assert_eq!(
                compile_run(&options.clang, &v.data, directory.path(), &v.id),
                expected.as_bytes(),
                "variant {}",
                v.id
            );
        }
    }
    #[test]
    fn macros_pragmas_indirect_returns_twice_and_volatile_are_protected() {
        let Some(options) = options() else { return };
        let cases: &[&[u8]] = &[
            b"#define P _Pragma(\"pack(1)\")\nint f(int c){if(c){P return 1;}else{return 2;}}\nstruct X{char a;int b;};",
            b"#define E\nint f(int c){if(c){E return 1;}else{return 2;}}\n#undef E\n",
            b"int f(int c){volatile int x=0;if(c){x=1;}else{x=2;}return x;}",
            b"#include <stdbool.h>\nint f(_Bool a){return a!=true;}",
            b"#include <stdbool.h>\nint f(_Bool a){bool b=a;return b!=1;}",
            b"int f(volatile _Bool a){return a!=1;}",
            b"int f(_Atomic _Bool a){return a!=1;}",
            b"int f(int c,int(*callback)(void)){if(c){return callback();}else{return callback();}}",
            b"int target(void)__attribute__((returns_twice));int f(int c){if(c){return target();}else{return target();}}",
            b"int f(int c){return _Generic(c,int:!!c,default:0);}",
        ];
        for source in cases {
            let variants = generate_variants(source, &options).unwrap();
            assert!(variants.iter().all(|v| v.data == *source));
            assert!(variants.iter().skip(1).all(|v| !v.notes.is_empty()));
        }
        let source = b"#define for(x) nope\nint f(void){while(1){break;}return 0;}";
        let variants = generate_variants(source, &options).unwrap();
        assert!(variants
            .iter()
            .all(|v| !v.audit.iter().any(|r| r["rule"] == "forever")));
    }
    #[test]
    fn increment_requires_source_int_one_and_token_splices_remain_valid() {
        let Some(options) = options() else { return };
        let source = b"int f(int c){int x=1;if(c){x+=1U;}else{x+=1L;}return x;}int g(int c){while(c){if(c==2){break;}else{continue;}}return 0;}";
        let variants = generate_variants(source, &options).unwrap();
        assert!(!variants
            .iter()
            .flat_map(|v| v.audit.iter())
            .any(|r| r["rule"] == "increment"));
        assert!(variants
            .iter()
            .all(|v| !String::from_utf8_lossy(&v.data).contains("elsecontinue")));
    }

    #[test]
    fn boolean_domain_keeps_int_counterexample_signed_fields_and_effect_counts() {
        let Some(options) = options() else { return };
        let source = br#"#include <stdio.h>
typedef int bool;
struct B{unsigned u:1;signed s:1;};
int calls;
int touch(int value){calls++;return value;}
int plain(int a){return a!=1;}
int misleading_name(bool a){return a!=1;}
int boolean_not(_Bool a){return a!=1;}
int boolean_equal(_Bool a){return 1==a;}
int unsigned_field(struct B *p){return p->u!=1;}
int signed_field(struct B *p){return p->s!=1;}
int effect(int a){return (touch(a)>0)!=1;}
unsigned long mixed(int c){if(c)return -1;else return 1U;}
int main(void){struct B b;for(int a=-2;a<=2;a++){b.u=a!=0;b.s=a!=0?-1:0;calls=0;int x=effect(a);printf("%d %d %d %d %d %d %d %d\n",plain(a),misleading_name(a),boolean_not(a),boolean_equal(a),unsigned_field(&b),signed_field(&b),x,calls);}printf("%lu\n",mixed(1));}
"#;
        let variants = generate_variants(source, &options).unwrap();
        let records: Vec<_> = variants.iter().flat_map(|v| &v.audit).collect();
        for function in ["boolean_not", "boolean_equal", "unsigned_field", "effect"] {
            assert!(
                records
                    .iter()
                    .any(|r| { r["function"] == function && r["rule"] == "boolean-domain" }),
                "expected a proven Boolean-domain rewrite for {function}"
            );
        }
        for function in ["plain", "misleading_name", "signed_field"] {
            assert!(
                !records
                    .iter()
                    .any(|r| { r["function"] == function && r["rule"] == "boolean-domain" }),
                "unproved or signed range must remain unchanged for {function}"
            );
        }
        let mut expected = String::new();
        for a in -2..=2 {
            expected.push_str(&format!(
                "{} {} {} {} {} 1 {} 1\n",
                i32::from(a != 1),
                i32::from(a != 1),
                i32::from(a == 0),
                i32::from(a != 0),
                i32::from(a == 0),
                i32::from(a <= 0),
            ));
        }
        expected.push_str(&format!("{}\n", u64::MAX));
        let directory = tempfile::tempdir().unwrap();
        for v in variants {
            assert_eq!(
                compile_run(&options.clang, &v.data, directory.path(), &v.id),
                expected.as_bytes(),
                "variant {}",
                v.id
            );
        }
    }

    #[test]
    fn stdbool_aliases_qualification_effects_and_reparsed_chains_keep_the_oracle() {
        let Some(options) = options() else { return };
        let source = br#"#include <stdio.h>
#include <stdbool.h>
typedef _Bool Flag;
typedef const _Bool ConstFlag;
int calls;
_Bool touch_bool(int a){calls++;return a;}
int direct(_Bool a){return a!=1;}
int reversed(bool a){return 1!=a;}
int alias(Flag a){return a!=1;}
int qualified(ConstFlag a){return a!=1;}
int explicit_bool(int a){return (_Bool)a!=1;}
int explicit_int(int a){return (int)a!=1;}
int call_once(int a){return touch_bool(a)!=1;}
int postincrement(_Bool *a){return (*a)++!=1;}
int chain(_Bool a){return (a!=1)!=1;}
int normalized(int a){return (a?1:0)!=1;}
int main(void){for(int a=-2;a<=2;a++){calls=0;int x=call_once(a);_Bool b=a;int y=postincrement(&b);printf("%d %d %d %d %d %d %d %d %d %d %d %d\n",direct(a),reversed(a),alias(a),qualified(a),explicit_bool(a),explicit_int(a),x,calls,y,b,chain(a),normalized(a));}}
"#;
        let variants = generate_variants(source, &options).unwrap();
        let records: Vec<_> = variants.iter().flat_map(|v| &v.audit).collect();
        for function in [
            "direct",
            "reversed",
            "alias",
            "qualified",
            "explicit_bool",
            "call_once",
            "postincrement",
            "chain",
            "normalized",
        ] {
            assert!(
                records
                    .iter()
                    .any(|r| r["function"] == function && r["rule"] == "boolean-domain"),
                "expected a proven Boolean-domain rewrite for {function}"
            );
        }
        assert!(!records
            .iter()
            .any(|r| r["function"] == "explicit_int" && r["rule"] == "boolean-domain"));
        for function in ["direct", "reversed", "alias", "qualified"] {
            assert!(records.iter().any(|r| {
                r["function"] == function && r["rule"] == "boolean-domain" && r["after"] == "!a"
            }));
        }
        let combined = variants.iter().find(|v| v.id == "c-all").unwrap();
        assert!(combined.audit.iter().any(|r| {
            r["function"] == "normalized" && r["rule"] == "boolean" && r["pass"] == 1
        }));
        assert!(combined.audit.iter().any(|r| {
            r["function"] == "normalized" && r["rule"] == "boolean-domain" && r["pass"] == 2
        }));
        // The all-rule recipe may prefer equality inversion on pass two.
        // Check the domain-only recipe to exercise the nested proof itself.
        let domain = variants
            .iter()
            .find(|v| v.id == "c-boolean-domain")
            .unwrap();
        assert!(domain.audit.iter().any(|r| {
            r["function"] == "chain" && r["rule"] == "boolean-domain" && r["pass"] == 2
        }));
        let mut expected = String::new();
        for a in -2..=2 {
            let not = i32::from(a == 0);
            expected.push_str(&format!(
                "{not} {not} {not} {not} {not} {} {not} 1 {not} 1 {} {not}\n",
                i32::from(a != 1),
                i32::from(a != 0),
            ));
        }
        let directory = tempfile::tempdir().unwrap();
        for v in variants {
            assert_eq!(
                compile_run(&options.clang, &v.data, directory.path(), &v.id),
                expected.as_bytes(),
                "variant {}",
                v.id
            );
        }
    }

    #[test]
    fn individual_portfolio_keeps_equal_and_growing_edits_when_requested() {
        let Some(mut options) = options() else { return };
        // A short compound spelling can become longer when logical operands
        // need parentheses; individual alternatives must not be source-pruned.
        let source = b"int f(int a,int b,int c){return !(a&&b||c);}int g(int x){return (x!=0)+1;}";
        options.max_variants = 64;
        options.individual_edits = 32;
        options.include_nonshrinking = true;
        let variants = generate_variants(source, &options).unwrap();
        assert!(variants.iter().any(|v| {
            v.audit
                .iter()
                .any(|r| r["source_bytes_saved"].as_i64().unwrap() <= 0)
        }));
        assert!(variants.iter().any(|v| v.id.starts_with("c-one-")));
        assert_eq!(variants[0].data, source);
        for variant in variants.iter().filter(|v| v.id.starts_with("c-one-")) {
            assert_eq!(variant.audit.len(), 1);
            let edit = &variant.audit[0];
            let mut replay = source.to_vec();
            replay.splice(
                edit["start"].as_u64().unwrap() as usize..edit["end"].as_u64().unwrap() as usize,
                edit["after"].as_str().unwrap().bytes(),
            );
            assert_eq!(replay, variant.data);
        }
        options.include_nonshrinking = false;
        let shrinking = generate_variants(source, &options).unwrap();
        assert!(shrinking.iter().all(|v| v
            .audit
            .iter()
            .all(|r| { r["source_bytes_saved"].as_i64().unwrap() > 0 })));
    }
}
