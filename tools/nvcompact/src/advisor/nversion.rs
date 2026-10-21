//! Bounded, advisory-only comparison of pure integer expressions.
//!
//! The caller owns binding, purity, ABI and reachability evidence. This module
//! proves only typed, defined evaluation equality on the supplied finite domain.
//! In particular, observations are never promoted to a static invariant. The
//! grammar is deliberately finite; exhausting it is not global optimality.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap, HashSet, VecDeque};
use std::hash::{Hash, Hasher};

const MAX_EXPR_NODES: usize = 256;
const MAX_EXPR_DEPTH: usize = 64;

/// Integer ranks in the supported C11 LP64, two's-complement target model.
/// `I64`/`U64` denote `long`; `long long` keeps its distinct C rank.
#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq, Hash, PartialOrd, Ord)]
#[serde(rename_all = "snake_case")]
pub enum CIntType {
    I32,
    U32,
    I64,
    U64,
    I64LongLong,
    U64LongLong,
}

impl CIntType {
    pub fn bits(self) -> u32 {
        match self {
            Self::I32 | Self::U32 => 32,
            _ => 64,
        }
    }

    pub fn is_unsigned(self) -> bool {
        matches!(self, Self::U32 | Self::U64 | Self::U64LongLong)
    }

    pub fn bounds(self) -> (i128, i128) {
        if self.is_unsigned() {
            (0, (1_i128 << self.bits()) - 1)
        } else {
            let high = 1_i128 << (self.bits() - 1);
            (-high, high - 1)
        }
    }

    pub fn contains(self, value: i128) -> bool {
        let (lo, hi) = self.bounds();
        lo <= value && value <= hi
    }

    pub fn c_name(self) -> &'static str {
        match self {
            Self::I32 => "int",
            Self::U32 => "unsigned int",
            Self::I64 => "long",
            Self::U64 => "unsigned long",
            Self::I64LongLong => "long long",
            Self::U64LongLong => "unsigned long long",
        }
    }

    pub fn from_c_spelling(spelling: &str) -> Option<Self> {
        match spelling.trim() {
            "int" | "signed int" | "signed" => Some(Self::I32),
            "unsigned int" | "unsigned" => Some(Self::U32),
            "long" | "long int" | "signed long" | "signed long int" => Some(Self::I64),
            "unsigned long" | "unsigned long int" => Some(Self::U64),
            "long long" | "long long int" | "signed long long" | "signed long long int" => {
                Some(Self::I64LongLong)
            }
            "unsigned long long" | "unsigned long long int" => Some(Self::U64LongLong),
            _ => None,
        }
    }

    pub fn unsigned(self) -> Self {
        match self {
            Self::I32 | Self::U32 => Self::U32,
            Self::I64 | Self::U64 => Self::U64,
            Self::I64LongLong | Self::U64LongLong => Self::U64LongLong,
        }
    }

    fn rank(self) -> u8 {
        match self {
            Self::I32 | Self::U32 => 3,
            Self::I64 | Self::U64 => 4,
            Self::I64LongLong | Self::U64LongLong => 5,
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "snake_case")]
pub enum UnaryOp {
    LogicalNot,
    BitNot,
    Negate,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "snake_case")]
pub enum BinaryOp {
    Add,
    Sub,
    Mul,
    Div,
    Rem,
    Shl,
    Shr,
    BitAnd,
    BitOr,
    BitXor,
    Eq,
    Ne,
    Lt,
    Le,
    Gt,
    Ge,
    LogicalAnd,
    LogicalOr,
}

impl BinaryOp {
    fn boolean(self) -> bool {
        matches!(
            self,
            Self::Eq
                | Self::Ne
                | Self::Lt
                | Self::Le
                | Self::Gt
                | Self::Ge
                | Self::LogicalAnd
                | Self::LogicalOr
        )
    }

    fn spelling(self) -> &'static str {
        match self {
            Self::Add => "+",
            Self::Sub => "-",
            Self::Mul => "*",
            Self::Div => "/",
            Self::Rem => "%",
            Self::Shl => "<<",
            Self::Shr => ">>",
            Self::BitAnd => "&",
            Self::BitOr => "|",
            Self::BitXor => "^",
            Self::Eq => "==",
            Self::Ne => "!=",
            Self::Lt => "<",
            Self::Le => "<=",
            Self::Gt => ">",
            Self::Ge => ">=",
            Self::LogicalAnd => "&&",
            Self::LogicalOr => "||",
        }
    }

    fn precedence(self) -> u8 {
        match self {
            Self::LogicalOr => 2,
            Self::LogicalAnd => 3,
            Self::BitOr => 4,
            Self::BitXor => 5,
            Self::BitAnd => 6,
            Self::Eq | Self::Ne => 7,
            Self::Lt | Self::Le | Self::Gt | Self::Ge => 8,
            Self::Shl | Self::Shr => 9,
            Self::Add | Self::Sub => 10,
            Self::Mul | Self::Div | Self::Rem => 11,
        }
    }
}

/// A single stable ordinary variable; the caller must exclude volatile reads,
/// atomics, side effects and expressions whose bindings are not this variable.
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq, Hash)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Expr {
    Var,
    Constant {
        #[serde(with = "decimal")]
        value: i128,
        ty: CIntType,
    },
    Unary {
        op: UnaryOp,
        operand: Box<Expr>,
    },
    Binary {
        op: BinaryOp,
        left: Box<Expr>,
        right: Box<Expr>,
    },
    Cast {
        ty: CIntType,
        operand: Box<Expr>,
    },
    Conditional {
        condition: Box<Expr>,
        then_expr: Box<Expr>,
        else_expr: Box<Expr>,
    },
}

impl Expr {
    pub fn constant(value: i128, ty: CIntType) -> Self {
        Self::Constant { value, ty }
    }

    pub fn unary(op: UnaryOp, operand: Self) -> Self {
        Self::Unary {
            op,
            operand: Box::new(operand),
        }
    }

    pub fn binary(op: BinaryOp, left: Self, right: Self) -> Self {
        Self::Binary {
            op,
            left: Box::new(left),
            right: Box::new(right),
        }
    }

    pub fn cast(ty: CIntType, operand: Self) -> Self {
        Self::Cast {
            ty,
            operand: Box::new(operand),
        }
    }

    pub fn conditional(condition: Self, then_expr: Self, else_expr: Self) -> Self {
        Self::Conditional {
            condition: Box::new(condition),
            then_expr: Box::new(then_expr),
            else_expr: Box::new(else_expr),
        }
    }

    pub fn infer_type(&self, variable_type: CIntType) -> Result<CIntType, EvalError> {
        validate_expr(self)?;
        infer_type(self, variable_type)
    }

    /// Rendering preserves the IR's grouping, integer literal types and ranks.
    /// The caller supplies the actual identifier, never a substituted expression.
    pub fn render(&self, symbol: &str) -> String {
        render(self, symbol).0
    }
}

fn validate_expr(expr: &Expr) -> Result<(), EvalError> {
    let mut stack = vec![(expr, 1)];
    let mut count = 0;
    while let Some((node, depth)) = stack.pop() {
        count += 1;
        if count > MAX_EXPR_NODES || depth > MAX_EXPR_DEPTH {
            return Err(EvalError::ExpressionLimit);
        }
        match node {
            Expr::Var => {}
            Expr::Constant { value, ty } => {
                if !ty.contains(*value) {
                    return Err(EvalError::InvalidConstant);
                }
            }
            Expr::Unary { operand, .. } | Expr::Cast { operand, .. } => {
                stack.push((operand, depth + 1));
            }
            Expr::Binary { left, right, .. } => {
                stack.push((left, depth + 1));
                stack.push((right, depth + 1));
            }
            Expr::Conditional {
                condition,
                then_expr,
                else_expr,
            } => {
                stack.push((condition, depth + 1));
                stack.push((then_expr, depth + 1));
                stack.push((else_expr, depth + 1));
            }
        }
    }
    Ok(())
}

fn common_type(left: CIntType, right: CIntType) -> CIntType {
    if left.is_unsigned() == right.is_unsigned() {
        if left.rank() >= right.rank() {
            left
        } else {
            right
        }
    } else {
        let (unsigned, signed) = if left.is_unsigned() {
            (left, right)
        } else {
            (right, left)
        };
        if unsigned.rank() >= signed.rank() {
            unsigned
        } else if signed.bits() > unsigned.bits() {
            signed
        } else {
            signed.unsigned()
        }
    }
}

fn binary_type(op: BinaryOp, left: CIntType, right: CIntType) -> CIntType {
    if op.boolean() {
        CIntType::I32
    } else if matches!(op, BinaryOp::Shl | BinaryOp::Shr) {
        left
    } else {
        common_type(left, right)
    }
}

fn infer_type(expr: &Expr, variable_type: CIntType) -> Result<CIntType, EvalError> {
    Ok(match expr {
        Expr::Var => variable_type,
        Expr::Constant { ty, .. } | Expr::Cast { ty, .. } => *ty,
        Expr::Unary { op, operand } => match op {
            UnaryOp::LogicalNot => CIntType::I32,
            _ => infer_type(operand, variable_type)?,
        },
        Expr::Binary { op, left, right } => binary_type(
            *op,
            infer_type(left, variable_type)?,
            infer_type(right, variable_type)?,
        ),
        Expr::Conditional {
            then_expr,
            else_expr,
            ..
        } => common_type(
            infer_type(then_expr, variable_type)?,
            infer_type(else_expr, variable_type)?,
        ),
    })
}

fn render(expr: &Expr, symbol: &str) -> (String, u8) {
    match expr {
        Expr::Var => (symbol.to_owned(), 13),
        Expr::Constant { value, ty } => {
            let suffix = match ty {
                CIntType::I32 => "",
                CIntType::U32 => "U",
                CIntType::I64 => "L",
                CIntType::U64 => "UL",
                CIntType::I64LongLong => "LL",
                CIntType::U64LongLong => "ULL",
            };
            if !ty.is_unsigned() && *value == ty.bounds().0 {
                (format!("(-{}{suffix}-1)", ty.bounds().1), 13)
            } else {
                (format!("{value}{suffix}"), if *value < 0 { 12 } else { 13 })
            }
        }
        Expr::Unary { op, operand } => {
            let (child, precedence) = render(operand, symbol);
            let operator = match op {
                UnaryOp::LogicalNot => "!",
                UnaryOp::BitNot => "~",
                UnaryOp::Negate => "-",
            };
            let child = if precedence < 12 || (operator == "-" && child.starts_with('-')) {
                format!("({child})")
            } else {
                child
            };
            (format!("{operator}{child}"), 12)
        }
        Expr::Cast { ty, operand } => {
            let (child, precedence) = render(operand, symbol);
            let child = if precedence < 12 {
                format!("({child})")
            } else {
                child
            };
            // The shorter spelling denotes the same supported C type.
            let name = if *ty == CIntType::U32 {
                "unsigned"
            } else {
                ty.c_name()
            };
            (format!("({name}){child}"), 12)
        }
        Expr::Binary { op, left, right } => {
            let precedence = op.precedence();
            let (left, lp) = render(left, symbol);
            let (right, rp) = render(right, symbol);
            let left = if lp < precedence {
                format!("({left})")
            } else {
                left
            };
            // Do not reassociate even + or *: signed overflow is observable in
            // this definedness contract and unsigned conversions can differ.
            let right = if rp <= precedence {
                format!("({right})")
            } else {
                right
            };
            let separation = if *op == BinaryOp::Sub && right.starts_with('-') {
                " "
            } else {
                ""
            };
            (
                format!("{left}{}{separation}{right}", op.spelling()),
                precedence,
            )
        }
        Expr::Conditional {
            condition,
            then_expr,
            else_expr,
        } => {
            let (condition, precedence) = render(condition, symbol);
            let condition = if precedence <= 1 {
                format!("({condition})")
            } else {
                condition
            };
            (
                format!(
                    "{condition}?{}:{}",
                    render(then_expr, symbol).0,
                    render(else_expr, symbol).0
                ),
                1,
            )
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "snake_case")]
pub enum EvalError {
    ExpressionLimit,
    InvalidConstant,
    InputOutsideType,
    SignedOverflow,
    DivisionByZero,
    InvalidShift,
    NegativeSignedRightShift,
    SignedConversionOutOfRange,
}

impl std::fmt::Display for EvalError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let text = match self {
            Self::ExpressionLimit => "expression node/depth limit exceeded",
            Self::InvalidConstant => "constant is not representable in its declared C type",
            Self::InputOutsideType => "domain input is outside the variable's C type",
            Self::SignedOverflow => "signed arithmetic overflow is not admitted",
            Self::DivisionByZero => "division or remainder by zero",
            Self::InvalidShift => {
                "negative/out-of-width shift or unrepresentable signed left shift"
            }
            Self::NegativeSignedRightShift => {
                "negative signed right shift is implementation-defined"
            }
            Self::SignedConversionOutOfRange => {
                "out-of-range conversion to a signed type is implementation-defined"
            }
        };
        f.write_str(text)
    }
}

impl std::error::Error for EvalError {}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct TypedValue {
    #[serde(with = "decimal")]
    pub value: i128,
    pub c_type: CIntType,
}

fn convert(value: i128, to: CIntType) -> Result<i128, EvalError> {
    if to.is_unsigned() {
        Ok(value.rem_euclid(1_i128 << to.bits()))
    } else if to.contains(value) {
        Ok(value)
    } else {
        Err(EvalError::SignedConversionOutOfRange)
    }
}

fn from_bits(value: u128, ty: CIntType) -> i128 {
    let modulus = 1_u128 << ty.bits();
    let bits = value & (modulus - 1);
    if !ty.is_unsigned() && bits >= modulus / 2 {
        bits as i128 - modulus as i128
    } else {
        bits as i128
    }
}

fn unary_value(op: UnaryOp, value: i128, ty: CIntType) -> Result<i128, EvalError> {
    match op {
        UnaryOp::LogicalNot => Ok(i128::from(value == 0)),
        UnaryOp::BitNot => Ok(from_bits(!(value as u128), ty)),
        UnaryOp::Negate if ty.is_unsigned() => Ok((-value).rem_euclid(1_i128 << ty.bits())),
        UnaryOp::Negate => {
            let negated = -value;
            if ty.contains(negated) {
                Ok(negated)
            } else {
                Err(EvalError::SignedOverflow)
            }
        }
    }
}

fn binary_value(
    op: BinaryOp,
    left: i128,
    left_type: CIntType,
    right: i128,
    right_type: CIntType,
) -> Result<i128, EvalError> {
    if matches!(op, BinaryOp::LogicalAnd | BinaryOp::LogicalOr) {
        return Ok(i128::from(if op == BinaryOp::LogicalAnd {
            left != 0 && right != 0
        } else {
            left != 0 || right != 0
        }));
    }
    if matches!(op, BinaryOp::Shl | BinaryOp::Shr) {
        if right < 0 || right >= i128::from(left_type.bits()) {
            return Err(EvalError::InvalidShift);
        }
        if op == BinaryOp::Shr {
            if left < 0 && !left_type.is_unsigned() {
                return Err(EvalError::NegativeSignedRightShift);
            }
            return Ok(left >> (right as u32));
        }
        if left_type.is_unsigned() {
            return Ok(from_bits((left as u128) << (right as u32), left_type));
        }
        let shifted = left << (right as u32);
        return if left >= 0 && left_type.contains(shifted) {
            Ok(shifted)
        } else {
            Err(EvalError::InvalidShift)
        };
    }
    let ty = common_type(left_type, right_type);
    let left = convert(left, ty)?;
    let right = convert(right, ty)?;
    let comparison = match op {
        BinaryOp::Eq => Some(left == right),
        BinaryOp::Ne => Some(left != right),
        BinaryOp::Lt => Some(left < right),
        BinaryOp::Le => Some(left <= right),
        BinaryOp::Gt => Some(left > right),
        BinaryOp::Ge => Some(left >= right),
        _ => None,
    };
    if let Some(value) = comparison {
        return Ok(i128::from(value));
    }
    if matches!(op, BinaryOp::Div | BinaryOp::Rem) {
        if right == 0 {
            return Err(EvalError::DivisionByZero);
        }
        if !ty.is_unsigned() && left == ty.bounds().0 && right == -1 {
            return Err(EvalError::SignedOverflow);
        }
    }
    if matches!(op, BinaryOp::BitAnd | BinaryOp::BitOr | BinaryOp::BitXor) {
        let bits = match op {
            BinaryOp::BitAnd => (left as u128) & (right as u128),
            BinaryOp::BitOr => (left as u128) | (right as u128),
            _ => (left as u128) ^ (right as u128),
        };
        return Ok(from_bits(bits, ty));
    }
    if ty.is_unsigned() {
        let (left, right) = (left as u128, right as u128);
        let bits = match op {
            BinaryOp::Add => left.wrapping_add(right),
            BinaryOp::Sub => left.wrapping_sub(right),
            BinaryOp::Mul => left.wrapping_mul(right),
            BinaryOp::Div => left / right,
            BinaryOp::Rem => left % right,
            _ => unreachable!("all logical, shift, comparison and bitwise operators handled"),
        };
        return Ok(from_bits(bits, ty));
    }
    // All operands are at most signed 64-bit; the product fits in i128.
    let result = match op {
        BinaryOp::Add => left + right,
        BinaryOp::Sub => left - right,
        BinaryOp::Mul => left * right,
        BinaryOp::Div => left / right,
        BinaryOp::Rem => left % right,
        _ => unreachable!("all logical, shift, comparison and bitwise operators handled"),
    };
    if ty.contains(result) {
        Ok(result)
    } else {
        Err(EvalError::SignedOverflow)
    }
}

fn eval_inner(expr: &Expr, input: i128, variable_type: CIntType) -> Result<TypedValue, EvalError> {
    let (value, ty) = match expr {
        Expr::Var => (input, variable_type),
        Expr::Constant { value, ty } => (*value, *ty),
        Expr::Cast { ty, operand } => (
            convert(eval_inner(operand, input, variable_type)?.value, *ty)?,
            *ty,
        ),
        Expr::Unary { op, operand } => {
            let operand = eval_inner(operand, input, variable_type)?;
            (
                unary_value(*op, operand.value, operand.c_type)?,
                if *op == UnaryOp::LogicalNot {
                    CIntType::I32
                } else {
                    operand.c_type
                },
            )
        }
        Expr::Binary { op, left, right } => {
            let left = eval_inner(left, input, variable_type)?;
            if *op == BinaryOp::LogicalAnd && left.value == 0 {
                (0, CIntType::I32)
            } else if *op == BinaryOp::LogicalOr && left.value != 0 {
                (1, CIntType::I32)
            } else {
                let right = eval_inner(right, input, variable_type)?;
                (
                    binary_value(*op, left.value, left.c_type, right.value, right.c_type)?,
                    binary_type(*op, left.c_type, right.c_type),
                )
            }
        }
        Expr::Conditional {
            condition,
            then_expr,
            else_expr,
        } => {
            let ty = common_type(
                infer_type(then_expr, variable_type)?,
                infer_type(else_expr, variable_type)?,
            );
            let selected = if eval_inner(condition, input, variable_type)?.value != 0 {
                then_expr
            } else {
                else_expr
            };
            (
                convert(eval_inner(selected, input, variable_type)?.value, ty)?,
                ty,
            )
        }
    };
    Ok(TypedValue { value, c_type: ty })
}

/// Exact evaluation within the supported model, including C short-circuiting.
pub fn eval(expr: &Expr, input: i128, variable_type: CIntType) -> Result<TypedValue, EvalError> {
    validate_expr(expr)?;
    if !variable_type.contains(input) {
        return Err(EvalError::InputOutsideType);
    }
    eval_inner(expr, input, variable_type)
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum DomainProvenance {
    /// The caller established that all values reaching this site are included.
    StaticConservative,
    /// A hypothesis/closure inferred from observations, not a reachability proof.
    ObservedClosure,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct FiniteDomain {
    #[serde(with = "decimal_values")]
    pub values: Vec<i128>,
    pub provenance: DomainProvenance,
    pub description: String,
}

impl FiniteDomain {
    fn normalized(&self, variable_type: CIntType, limit: usize) -> Result<Self, String> {
        if self.values.is_empty() {
            return Err("empty domains cannot establish expression equivalence".to_owned());
        }
        if self.values.len() > limit {
            return Err(format!(
                "domain has {} supplied values, above the {limit} value budget",
                self.values.len()
            ));
        }
        if let Some(value) = self
            .values
            .iter()
            .find(|value| !variable_type.contains(**value))
        {
            return Err(format!(
                "domain value {value} is outside {}",
                variable_type.c_name()
            ));
        }
        let mut domain = self.clone();
        domain.values.sort_unstable();
        domain.values.dedup();
        Ok(domain)
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(default)]
pub struct SearchBudget {
    pub max_candidates: usize,
    /// Includes memo lookups as well as computations, bounding evaluator work.
    pub max_evaluations: usize,
    pub max_domain_values: usize,
    /// Bounded (expression node, input value) memo entries.
    pub max_cached_values: usize,
    pub max_results: usize,
    pub max_rejections: usize,
}

impl Default for SearchBudget {
    fn default() -> Self {
        Self {
            max_candidates: 10_000,
            max_evaluations: 2_000_000,
            max_domain_values: 4096,
            max_cached_values: 131_072,
            max_results: 24,
            max_rejections: 24,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct SearchRequest {
    pub original: Expr,
    pub original_source: String,
    pub symbol: String,
    pub variable_type: CIntType,
    pub domain: FiniteDomain,
    #[serde(default)]
    pub budget: SearchBudget,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct Counterexample {
    #[serde(with = "decimal")]
    pub input: i128,
    pub original: Option<TypedValue>,
    pub candidate: Option<TypedValue>,
    pub original_error: Option<EvalError>,
    pub candidate_error: Option<EvalError>,
    pub reason: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct Comparison {
    pub equivalent: bool,
    pub complete: bool,
    /// The comparison was reused after exact typed full-domain aliasing.
    #[serde(default)]
    pub reused: bool,
    pub checked_values: usize,
    pub original_type: CIntType,
    pub candidate_type: CIntType,
    pub scope: DomainProvenance,
    pub counterexample: Option<Counterexample>,
    pub reason: Option<String>,
}

fn difference(
    input: i128,
    original: Result<TypedValue, EvalError>,
    candidate: Result<TypedValue, EvalError>,
) -> Option<Counterexample> {
    let reason = match (&original, &candidate) {
        (Err(_), _) => "original is not defined in the supported evaluation model",
        (Ok(_), Err(_)) => "candidate is not defined where the original is defined",
        (Ok(left), Ok(right)) if left != right => "typed result differs",
        _ => return None,
    };
    Some(Counterexample {
        input,
        original: original.as_ref().ok().cloned(),
        candidate: candidate.as_ref().ok().cloned(),
        original_error: original.err(),
        candidate_error: candidate.err(),
        reason: reason.to_owned(),
    })
}

/// Compare an explicitly supplied candidate, retaining the first failed input.
/// An original undefined input rejects the entire proposed equivalence contract.
pub fn compare_expressions(
    original: &Expr,
    candidate: &Expr,
    variable_type: CIntType,
    domain: &FiniteDomain,
) -> Result<Comparison, String> {
    let domain = domain.normalized(variable_type, SearchBudget::default().max_domain_values)?;
    let original_type = original
        .infer_type(variable_type)
        .map_err(|error| error.to_string())?;
    let candidate_type = candidate
        .infer_type(variable_type)
        .map_err(|error| error.to_string())?;
    let mut comparison = Comparison {
        equivalent: false,
        complete: true,
        reused: false,
        checked_values: 0,
        original_type,
        candidate_type,
        scope: domain.provenance,
        counterexample: None,
        reason: None,
    };
    if original_type != candidate_type {
        comparison.reason = Some("C result type/rank differs".to_owned());
        return Ok(comparison);
    }
    for input in domain.values {
        comparison.checked_values += 1;
        if let Some(counterexample) = difference(
            input,
            eval_inner(original, input, variable_type),
            eval_inner(candidate, input, variable_type),
        ) {
            comparison.reason = Some(counterexample.reason.clone());
            comparison.counterexample = Some(counterexample);
            return Ok(comparison);
        }
    }
    comparison.equivalent = true;
    Ok(comparison)
}

/// Diagnostic boundary probes are intentionally separate from domain proof.
/// They can expose a missing invariant; absence of a witness proves nothing.
pub fn probe_outside_domain(
    original: &Expr,
    candidate: &Expr,
    variable_type: CIntType,
    domain: &FiniteDomain,
    max_probes: usize,
) -> Result<Vec<Counterexample>, String> {
    let domain = domain.normalized(variable_type, SearchBudget::default().max_domain_values)?;
    validate_expr(original).map_err(|error| error.to_string())?;
    validate_expr(candidate).map_err(|error| error.to_string())?;
    if max_probes > 256 {
        return Err("outside-domain probe budget must be at most 256".to_owned());
    }
    let (lo, hi) = (domain.values[0], domain.values[domain.values.len() - 1]);
    let (type_lo, type_hi) = variable_type.bounds();
    let mut probes = vec![hi + 1, lo - 1, 0, -1, 1, type_lo, type_hi];
    for bit in 0..variable_type.bits() {
        let power = 1_i128 << bit;
        probes.extend([power, power - 1, -power]);
    }
    let mut seen = HashSet::new();
    let mut witnesses = Vec::new();
    for input in probes
        .into_iter()
        .filter(|input| {
            variable_type.contains(*input)
                && domain.values.binary_search(input).is_err()
                && seen.insert(*input)
        })
        .take(max_probes)
    {
        if let Some(witness) = difference(
            input,
            eval_inner(original, input, variable_type),
            eval_inner(candidate, input, variable_type),
        ) {
            witnesses.push(witness);
        }
    }
    Ok(witnesses)
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq, Hash, PartialOrd, Ord)]
#[serde(rename_all = "snake_case")]
pub enum CandidateFamily {
    Direct,
    Boolean,
    BitMask,
    AffineMask,
    ShiftMask,
    Comparison,
    Range,
    UnsignedRange,
    Arithmetic,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Candidate {
    pub expression: Expr,
    pub source: String,
    pub source_bytes: usize,
    /// A source estimate, never compressed-file or execution cost evidence.
    pub bytes_saved: isize,
    pub family: CandidateFamily,
    pub evidence: Comparison,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Rejection {
    pub expression: Expr,
    pub source: String,
    pub family: CandidateFamily,
    pub evidence: Comparison,
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub struct SearchStatistics {
    pub generated: usize,
    pub compared: usize,
    pub equivalent: usize,
    pub structurally_reused: usize,
    pub semantic_signatures: usize,
    pub semantic_duplicates: usize,
    pub comparison_reuses: usize,
    pub evaluation_steps: usize,
    pub computed_values: usize,
    pub cache_hits: usize,
    pub cached_values: usize,
    pub reclaimed_cached_values: usize,
    pub memo_capacity_skips: usize,
    pub compared_inputs: usize,
    pub original_inputs_checked: usize,
    pub retained: usize,
    pub equivalent_not_retained: usize,
    pub rejection_samples_omitted: usize,
    pub rejection_counts: BTreeMap<String, usize>,
    pub family_counts: BTreeMap<CandidateFamily, usize>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct SearchReport {
    pub advisory_only: bool,
    pub original: Expr,
    pub original_source: String,
    pub original_source_bytes: usize,
    pub original_rendered: String,
    pub variable_type: CIntType,
    pub result_type: CIntType,
    pub domain: FiniteDomain,
    pub original_defined: bool,
    pub original_failure: Option<Counterexample>,
    pub candidates: Vec<Candidate>,
    pub rejections: Vec<Rejection>,
    pub statistics: SearchStatistics,
    pub budget: SearchBudget,
    /// True only when the documented generated grammar was exhausted.
    pub complete: bool,
    pub stop_reasons: Vec<String>,
    pub grammar: String,
    pub limitations: Vec<String>,
}

#[derive(Clone, Copy, Debug, Hash, PartialEq, Eq)]
enum NodeKey {
    Var,
    Constant(i128, CIntType),
    Unary(UnaryOp, usize),
    Binary(BinaryOp, usize, usize),
    Cast(CIntType, usize),
    Conditional(usize, usize, usize),
}

#[derive(Clone, Copy)]
struct CompiledNode {
    key: NodeKey,
    ty: CIntType,
}

type Outcome = Result<i128, EvalError>;

struct Evaluator<'a> {
    variable_type: CIntType,
    inputs: &'a [i128],
    budget: &'a SearchBudget,
    nodes: Vec<CompiledNode>,
    interned: HashMap<NodeKey, usize>,
    memo: HashMap<(usize, usize), Outcome>,
    filled: Vec<usize>,
    aliases: Vec<Option<usize>>,
    signatures: HashMap<u64, Vec<usize>>,
    stats: SearchStatistics,
}

impl<'a> Evaluator<'a> {
    fn new(variable_type: CIntType, inputs: &'a [i128], budget: &'a SearchBudget) -> Self {
        Self {
            variable_type,
            inputs,
            budget,
            nodes: Vec::new(),
            interned: HashMap::new(),
            memo: HashMap::new(),
            filled: Vec::new(),
            aliases: Vec::new(),
            signatures: HashMap::new(),
            stats: SearchStatistics::default(),
        }
    }

    fn compile(&mut self, expr: &Expr) -> usize {
        let (key, ty) = match expr {
            Expr::Var => (NodeKey::Var, self.variable_type),
            Expr::Constant { value, ty } => (NodeKey::Constant(*value, *ty), *ty),
            Expr::Unary { op, operand } => {
                let child = self.compile(operand);
                let ty = if *op == UnaryOp::LogicalNot {
                    CIntType::I32
                } else {
                    self.nodes[child].ty
                };
                (NodeKey::Unary(*op, child), ty)
            }
            Expr::Binary { op, left, right } => {
                let left = self.compile(left);
                let right = self.compile(right);
                let ty = binary_type(*op, self.nodes[left].ty, self.nodes[right].ty);
                (NodeKey::Binary(*op, left, right), ty)
            }
            Expr::Cast { ty, operand } => {
                let child = self.compile(operand);
                (NodeKey::Cast(*ty, child), *ty)
            }
            Expr::Conditional {
                condition,
                then_expr,
                else_expr,
            } => {
                let condition = self.compile(condition);
                let then_expr = self.compile(then_expr);
                let else_expr = self.compile(else_expr);
                let ty = common_type(self.nodes[then_expr].ty, self.nodes[else_expr].ty);
                (NodeKey::Conditional(condition, then_expr, else_expr), ty)
            }
        };
        if let Some(id) = self.interned.get(&key) {
            return self.canonical(*id);
        }
        let id = self.nodes.len();
        self.nodes.push(CompiledNode { key, ty });
        self.filled.push(0);
        self.aliases.push(None);
        self.interned.insert(key, id);
        id
    }

    fn canonical(&self, id: usize) -> usize {
        // Representatives are fully cached and never evicted or subsequently
        // aliased. Each alias therefore has exactly one hop.
        self.aliases[id].unwrap_or(id)
    }

    fn signature_hash(&self, id: usize) -> u64 {
        let mut hash = std::collections::hash_map::DefaultHasher::new();
        self.nodes[id].ty.hash(&mut hash);
        for input in 0..self.inputs.len() {
            self.memo.get(&(id, input)).hash(&mut hash);
        }
        hash.finish()
    }

    fn register_full_vector(&mut self, id: usize) {
        // Partial vectors must never identify equivalence: the missing values
        // might be exactly where a rewrite fails or becomes undefined.
        if self.filled[id] != self.inputs.len() {
            return;
        }
        let hash = self.signature_hash(id);
        let representative = self.signatures.get(&hash).and_then(|bucket| {
            bucket.iter().copied().find(|other| {
                self.nodes[*other].ty == self.nodes[id].ty
                    && (0..self.inputs.len())
                        .all(|input| self.memo.get(&(*other, input)) == self.memo.get(&(id, input)))
            })
        });
        if let Some(representative) = representative {
            if representative == id {
                return;
            }
            // The hash is only an index. Every value/error and the C type/rank
            // were checked before sharing this complete domain-scoped vector.
            self.aliases[id] = Some(representative);
            self.stats.semantic_duplicates += 1;
            for input in 0..self.inputs.len() {
                self.memo.remove(&(id, input));
            }
            self.stats.reclaimed_cached_values += self.inputs.len();
        } else {
            self.signatures.entry(hash).or_default().push(id);
            self.stats.semantic_signatures += 1;
        }
    }

    fn evaluate(&mut self, id: usize, input: usize) -> Result<Outcome, ()> {
        if self.stats.evaluation_steps >= self.budget.max_evaluations {
            return Err(());
        }
        self.stats.evaluation_steps += 1;
        let id = self.canonical(id);
        if let Some(value) = self.memo.get(&(id, input)) {
            self.stats.cache_hits += 1;
            return Ok(*value);
        }
        let node = self.nodes[id];
        let value = match node.key {
            NodeKey::Var => Ok(self.inputs[input]),
            NodeKey::Constant(value, _) => Ok(value),
            NodeKey::Unary(op, operand) => self
                .evaluate(operand, input)?
                .and_then(|value| unary_value(op, value, self.nodes[operand].ty)),
            NodeKey::Cast(ty, operand) => self
                .evaluate(operand, input)?
                .and_then(|value| convert(value, ty)),
            NodeKey::Binary(op, left, right) => match self.evaluate(left, input)? {
                Err(error) => Err(error),
                Ok(0) if op == BinaryOp::LogicalAnd => Ok(0),
                Ok(value) if op == BinaryOp::LogicalOr && value != 0 => Ok(1),
                Ok(left_value) => self.evaluate(right, input)?.and_then(|right_value| {
                    binary_value(
                        op,
                        left_value,
                        self.nodes[left].ty,
                        right_value,
                        self.nodes[right].ty,
                    )
                }),
            },
            NodeKey::Conditional(condition, then_expr, else_expr) => {
                match self.evaluate(condition, input)? {
                    Err(error) => Err(error),
                    Ok(condition) => self
                        .evaluate(if condition != 0 { then_expr } else { else_expr }, input)?
                        .and_then(|value| convert(value, node.ty)),
                }
            }
        };
        self.stats.computed_values += 1;
        if self.memo.len() < self.budget.max_cached_values {
            self.memo.insert((id, input), value);
            self.filled[id] += 1;
            self.register_full_vector(id);
        } else {
            self.stats.memo_capacity_skips += 1;
        }
        Ok(value)
    }
}

struct Search<'a> {
    request: &'a SearchRequest,
    domain: &'a FiniteDomain,
    evaluator: Evaluator<'a>,
    original_type: CIntType,
    expected: Vec<i128>,
    seen: HashSet<Expr>,
    comparisons: HashMap<usize, Comparison>,
    counterexample_order: VecDeque<usize>,
    candidates: BTreeMap<CandidateFamily, Vec<Candidate>>,
    rejections: Vec<Rejection>,
    stop_reasons: Vec<String>,
}

impl Search<'_> {
    fn stopped(&self) -> bool {
        !self.stop_reasons.is_empty()
    }

    fn stop(&mut self, reason: &str) {
        if !self.stop_reasons.iter().any(|existing| existing == reason) {
            self.stop_reasons.push(reason.to_owned());
        }
    }

    fn evidence(&self, ty: CIntType) -> Comparison {
        Comparison {
            equivalent: false,
            complete: true,
            reused: false,
            checked_values: 0,
            original_type: self.original_type,
            candidate_type: ty,
            scope: self.domain.provenance,
            counterexample: None,
            reason: None,
        }
    }

    fn reject(
        &mut self,
        expression: Expr,
        family: CandidateFamily,
        evidence: Comparison,
        kind: &str,
    ) {
        *self
            .evaluator
            .stats
            .rejection_counts
            .entry(kind.to_owned())
            .or_default() += 1;
        if self.rejections.len() < self.request.budget.max_rejections {
            self.rejections.push(Rejection {
                source: expression.render(&self.request.symbol),
                expression,
                family,
                evidence,
            });
        } else {
            self.evaluator.stats.rejection_samples_omitted += 1;
        }
    }

    fn consider(&mut self, expression: Expr, family: CandidateFamily) -> bool {
        if self.stopped() {
            return false;
        }
        if self.evaluator.stats.generated >= self.request.budget.max_candidates {
            self.stop("candidate generation budget exhausted");
            return false;
        }
        self.evaluator.stats.generated += 1;
        *self
            .evaluator
            .stats
            .family_counts
            .entry(family)
            .or_default() += 1;
        if !self.seen.insert(expression.clone()) {
            self.evaluator.stats.structurally_reused += 1;
            return true;
        }
        let id = self.evaluator.compile(&expression);
        let ty = self.evaluator.nodes[id].ty;
        let mut evidence = self.evidence(ty);
        if ty != self.original_type {
            evidence.reason = Some("C result type/rank differs".to_owned());
            self.reject(expression, family, evidence, "result_type");
            return true;
        }
        if let Some(mut evidence) = self.comparisons.get(&id).cloned() {
            evidence.reused = true;
            self.evaluator.stats.comparison_reuses += 1;
            if evidence.equivalent {
                self.retain(expression, family, evidence);
            } else {
                let kind = if evidence
                    .counterexample
                    .as_ref()
                    .is_some_and(|witness| witness.candidate_error.is_some())
                {
                    "candidate_undefined"
                } else {
                    "value_mismatch"
                };
                self.reject(expression, family, evidence, kind);
            }
            return true;
        }
        self.evaluator.stats.compared += 1;
        // Previously distinguishing inputs are tested first, but admission
        // always visits every domain value. This is a scheduling heuristic.
        let mut scheduled = vec![false; self.domain.values.len()];
        let mut order = Vec::with_capacity(scheduled.len());
        for &index in &self.counterexample_order {
            if !scheduled[index] {
                scheduled[index] = true;
                order.push(index);
            }
        }
        order.extend((0..scheduled.len()).filter(|index| !scheduled[*index]));
        for index in order {
            let actual = match self.evaluator.evaluate(id, index) {
                Ok(actual) => actual,
                Err(()) => {
                    evidence.complete = false;
                    evidence.reason =
                        Some("evaluation budget exhausted before complete comparison".to_owned());
                    self.reject(expression, family, evidence, "incomplete");
                    self.stop("evaluation budget exhausted");
                    return false;
                }
            };
            evidence.checked_values += 1;
            self.evaluator.stats.compared_inputs += 1;
            if actual != Ok(self.expected[index]) {
                let kind = if actual.is_err() {
                    "candidate_undefined"
                } else {
                    "value_mismatch"
                };
                evidence.counterexample = difference(
                    self.domain.values[index],
                    Ok(TypedValue {
                        value: self.expected[index],
                        c_type: self.original_type,
                    }),
                    actual.map(|value| TypedValue { value, c_type: ty }),
                );
                evidence.reason = evidence
                    .counterexample
                    .as_ref()
                    .map(|witness| witness.reason.clone());
                self.counterexample_order.retain(|old| *old != index);
                self.counterexample_order.push_front(index);
                self.counterexample_order.truncate(16);
                self.comparisons
                    .insert(self.evaluator.canonical(id), evidence.clone());
                self.reject(expression, family, evidence, kind);
                return true;
            }
        }
        evidence.equivalent = true;
        self.comparisons
            .insert(self.evaluator.canonical(id), evidence.clone());
        self.retain(expression, family, evidence);
        true
    }

    fn retain(&mut self, expression: Expr, family: CandidateFamily, evidence: Comparison) {
        self.evaluator.stats.equivalent += 1;
        let source = expression.render(&self.request.symbol);
        let candidate = Candidate {
            source_bytes: source.len(),
            bytes_saved: self.request.original_source.len() as isize - source.len() as isize,
            source,
            expression,
            family,
            evidence,
        };
        // Keep representatives from distinct algorithms. Raw length only orders
        // representatives within a family; it never proves compressed dominance.
        let representatives = self.candidates.entry(family).or_default();
        representatives.push(candidate);
        representatives
            .sort_by(|a, b| (a.source_bytes, &a.source).cmp(&(b.source_bytes, &b.source)));
        representatives.truncate(2);
    }

    fn evaluate_seed(&mut self, expression: &Expr, index: usize) -> Option<i128> {
        if self.stopped() {
            return None;
        }
        let id = self.evaluator.compile(expression);
        match self.evaluator.evaluate(id, index) {
            Ok(value) => value.ok(),
            Err(()) => {
                self.stop("evaluation budget exhausted");
                None
            }
        }
    }
}

fn literal(value: i128) -> Expr {
    let ty = if CIntType::I32.contains(value) {
        CIntType::I32
    } else if CIntType::I64.contains(value) {
        CIntType::I64
    } else {
        CIntType::U64
    };
    Expr::constant(value, ty)
}

fn shifted(shift: u32) -> Expr {
    if shift == 0 {
        Expr::Var
    } else {
        Expr::binary(BinaryOp::Shr, Expr::Var, literal(i128::from(shift)))
    }
}

fn translated(offset: i128) -> Expr {
    if offset == 0 {
        Expr::Var
    } else if offset < 0 {
        Expr::binary(BinaryOp::Sub, Expr::Var, literal(-offset))
    } else {
        Expr::binary(BinaryOp::Add, Expr::Var, literal(offset))
    }
}

fn integer_constants(expr: &Expr, output: &mut Vec<i128>) {
    match expr {
        Expr::Var => {}
        Expr::Constant { value, .. } => output.push(*value),
        Expr::Unary { operand, .. } | Expr::Cast { operand, .. } => {
            integer_constants(operand, output)
        }
        Expr::Binary { left, right, .. } => {
            integer_constants(left, output);
            integer_constants(right, output);
        }
        Expr::Conditional {
            condition,
            then_expr,
            else_expr,
        } => {
            integer_constants(condition, output);
            integer_constants(then_expr, output);
            integer_constants(else_expr, output);
        }
    }
}

fn active_bits(domain: &FiniteDomain, ty: CIntType) -> u32 {
    if domain.values[0] < 0 {
        return ty.bits();
    }
    let highest = *domain.values.last().unwrap() as u128;
    let significant = (128 - highest.leading_zeros()).max(1);
    // One carry bit permits translation across the observed/static upper bound.
    (significant + 1).min(ty.bits())
}

fn masks(bits: u32, original: &Expr) -> Vec<i128> {
    let mut masks = Vec::new();
    // Contiguous bit fields are generated from widths, never board encodings.
    for width in 1..=bits {
        for low in 0..=bits - width {
            masks.push(((1_i128 << width) - 1) << low);
        }
    }
    // Source literals and regular bit runs cover additional noncontiguous fields.
    let mut source_constants = Vec::new();
    integer_constants(original, &mut source_constants);
    masks.extend(source_constants.into_iter().filter(|value| *value > 0));
    for run in [1, 2, 4, 8, 16, 32] {
        if run >= bits {
            break;
        }
        let mut mask = 0_i128;
        for bit in 0..bits {
            if (bit / run) % 2 == 0 {
                mask |= 1_i128 << bit;
            }
        }
        masks.push(mask);
    }
    let mut seen = HashSet::new();
    masks.retain(|mask| seen.insert(*mask));
    masks
}

fn synthesize_ranges(search: &mut Search<'_>) {
    if search.original_type != CIntType::I32
        || search
            .expected
            .iter()
            .any(|value| *value != 0 && *value != 1)
    {
        return;
    }
    for true_region in [true, false] {
        let region: Vec<i128> = search
            .domain
            .values
            .iter()
            .zip(&search.expected)
            .filter_map(|(&input, &output)| ((output != 0) == true_region).then_some(input))
            .collect();
        if region.is_empty() {
            continue;
        }
        let (lo, hi) = (region[0], region[region.len() - 1]);
        let inside = Expr::binary(
            BinaryOp::LogicalAnd,
            Expr::binary(BinaryOp::Ge, Expr::Var, literal(lo)),
            Expr::binary(BinaryOp::Le, Expr::Var, literal(hi)),
        );
        let outside = Expr::binary(
            BinaryOp::LogicalOr,
            Expr::binary(BinaryOp::Lt, Expr::Var, literal(lo)),
            Expr::binary(BinaryOp::Gt, Expr::Var, literal(hi)),
        );
        if !search.consider(
            if true_region { inside } else { outside },
            CandidateFamily::Range,
        ) {
            return;
        }
        let subtraction = Expr::binary(
            BinaryOp::Sub,
            Expr::cast(search.request.variable_type.unsigned(), Expr::Var),
            literal(lo),
        );
        let comparison = Expr::binary(
            if true_region {
                BinaryOp::Le
            } else {
                BinaryOp::Gt
            },
            subtraction,
            literal(hi - lo),
        );
        if !search.consider(comparison, CandidateFamily::UnsignedRange) {
            return;
        }
    }
}

fn synthesize_masks(search: &mut Search<'_>, bits: u32, masks: &[i128]) {
    let boolean = search.original_type == CIntType::I32
        && search
            .expected
            .iter()
            .all(|value| *value == 0 || *value == 1);
    let true_input = search.expected.iter().position(|value| *value != 0);
    let false_input = search.expected.iter().position(|value| *value == 0);
    let mut offsets = vec![0];
    for bit in 0..bits {
        offsets.extend([1_i128 << bit, -(1_i128 << bit)]);
    }
    // Affine mask enumeration precedes the broader comparison grammar so a
    // useful shift/add/mask family cannot be starved by unrelated comparisons.
    for offset in offsets {
        let translated = translated(offset);
        let family = if offset == 0 {
            CandidateFamily::BitMask
        } else {
            CandidateFamily::AffineMask
        };
        for &mask in masks {
            let masked = Expr::binary(BinaryOp::BitAnd, translated.clone(), literal(mask));
            if !search.consider(masked.clone(), family) {
                return;
            }
            if !boolean {
                continue;
            }
            if !search.consider(Expr::unary(UnaryOp::LogicalNot, masked.clone()), family) {
                return;
            }
            if !search.consider(
                Expr::unary(
                    UnaryOp::LogicalNot,
                    Expr::unary(UnaryOp::LogicalNot, masked.clone()),
                ),
                family,
            ) {
                return;
            }
            // Inverse synthesis proposes a masked comparison constant from one
            // labelled input, then independently checks every domain input.
            for (input, op) in [(true_input, BinaryOp::Eq), (false_input, BinaryOp::Ne)] {
                if let Some(input) = input {
                    if let Some(value) = search.evaluate_seed(&masked, input) {
                        if value != 0
                            && !search
                                .consider(Expr::binary(op, masked.clone(), literal(value)), family)
                        {
                            return;
                        }
                    }
                    if search.stopped() {
                        return;
                    }
                }
            }
        }
    }
}

fn synthesize_other(search: &mut Search<'_>, bits: u32) {
    let mut constants = vec![0, 1, -1];
    integer_constants(&search.request.original, &mut constants);
    constants.extend([
        search.domain.values[0],
        *search.domain.values.last().unwrap(),
    ]);
    for bit in 0..bits {
        constants.extend([1_i128 << bit, (1_i128 << bit) - 1]);
    }
    let mut seen = HashSet::new();
    constants.retain(|value| seen.insert(*value));
    for shift in 0..bits {
        let shifted = shifted(shift);
        if !search.consider(shifted.clone(), CandidateFamily::Arithmetic) {
            return;
        }
        for &value in &constants {
            for op in [
                BinaryOp::Eq,
                BinaryOp::Ne,
                BinaryOp::Lt,
                BinaryOp::Le,
                BinaryOp::Gt,
                BinaryOp::Ge,
            ] {
                if !search.consider(
                    Expr::binary(op, shifted.clone(), literal(value)),
                    CandidateFamily::Comparison,
                ) {
                    return;
                }
            }
        }
        for width in 1..=bits - shift {
            let mask = (1_i128 << width) - 1;
            let expr = Expr::binary(BinaryOp::BitAnd, shifted.clone(), literal(mask));
            if !search.consider(expr.clone(), CandidateFamily::ShiftMask) {
                return;
            }
            if !search.consider(
                Expr::unary(UnaryOp::LogicalNot, expr),
                CandidateFamily::ShiftMask,
            ) {
                return;
            }
        }
    }
    for &constant in &constants {
        for op in [
            BinaryOp::Add,
            BinaryOp::Sub,
            BinaryOp::Mul,
            BinaryOp::Div,
            BinaryOp::Rem,
            BinaryOp::BitXor,
            BinaryOp::BitOr,
        ] {
            if !search.consider(
                Expr::binary(op, Expr::Var, literal(constant)),
                CandidateFamily::Arithmetic,
            ) {
                return;
            }
        }
    }
}

fn check_budget(budget: &SearchBudget) -> Result<(), String> {
    if budget.max_candidates == 0 || budget.max_candidates > 100_000 {
        return Err("candidate budget must be in 1..=100000".to_owned());
    }
    if budget.max_evaluations == 0 || budget.max_evaluations > 100_000_000 {
        return Err("evaluation budget must be in 1..=100000000".to_owned());
    }
    if budget.max_domain_values == 0 || budget.max_domain_values > 4096 {
        return Err("domain value budget must be in 1..=4096".to_owned());
    }
    if budget.max_cached_values > 1_048_576
        || budget.max_results > 128
        || budget.max_rejections > 128
    {
        return Err("memo/result/rejection retention budget exceeds supported limits".to_owned());
    }
    Ok(())
}

/// Run finite n-version synthesis without modifying source or admitting a
/// compression candidate. All retained alternatives include their typed proof
/// scope; even a longer representative can later win an actual-file comparison.
pub fn compare_and_suggest(request: &SearchRequest) -> Result<SearchReport, String> {
    check_budget(&request.budget)?;
    validate_expr(&request.original).map_err(|error| error.to_string())?;
    if request.symbol.is_empty()
        || !request
            .symbol
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
        || request.symbol.as_bytes()[0].is_ascii_digit()
    {
        return Err("rendering requires one ordinary ASCII C identifier".to_owned());
    }
    let domain = request
        .domain
        .normalized(request.variable_type, request.budget.max_domain_values)?;
    let original_type =
        infer_type(&request.original, request.variable_type).map_err(|error| error.to_string())?;
    let mut evaluator = Evaluator::new(request.variable_type, &domain.values, &request.budget);
    let original_id = evaluator.compile(&request.original);
    let mut expected = Vec::with_capacity(domain.values.len());
    let mut original_failure = None;
    let mut stop_reasons = Vec::new();
    for (index, &input) in domain.values.iter().enumerate() {
        match evaluator.evaluate(original_id, index) {
            Ok(Ok(value)) => {
                expected.push(value);
                evaluator.stats.original_inputs_checked += 1;
            }
            Ok(Err(error)) => {
                evaluator.stats.original_inputs_checked += 1;
                original_failure = Some(Counterexample {
                    input,
                    original: None,
                    candidate: None,
                    original_error: Some(error),
                    candidate_error: None,
                    reason: "original is not defined in the supported evaluation model".to_owned(),
                });
                stop_reasons.push(
                    "original domain includes an unsupported or undefined evaluation".to_owned(),
                );
                break;
            }
            Err(()) => {
                stop_reasons
                    .push("evaluation budget exhausted while validating the original".to_owned());
                break;
            }
        }
    }
    let original_defined = expected.len() == domain.values.len();
    let mut search = Search {
        request,
        domain: &domain,
        evaluator,
        original_type,
        expected,
        seen: HashSet::from([request.original.clone()]),
        comparisons: HashMap::new(),
        counterexample_order: VecDeque::from([0, domain.values.len() - 1, domain.values.len() / 2]),
        candidates: BTreeMap::new(),
        rejections: Vec::new(),
        stop_reasons,
    };
    if original_defined {
        let mut original_evidence = search.evidence(original_type);
        original_evidence.equivalent = true;
        original_evidence.checked_values = domain.values.len();
        search
            .comparisons
            .insert(search.evaluator.canonical(original_id), original_evidence);
        let first = search.expected[0];
        if search.expected.iter().all(|value| *value == first) {
            search.consider(
                Expr::constant(first, original_type),
                CandidateFamily::Direct,
            );
        }
        for expr in [
            Expr::Var,
            Expr::unary(UnaryOp::LogicalNot, Expr::Var),
            Expr::unary(
                UnaryOp::LogicalNot,
                Expr::unary(UnaryOp::LogicalNot, Expr::Var),
            ),
            Expr::unary(UnaryOp::BitNot, Expr::Var),
            Expr::unary(UnaryOp::Negate, Expr::Var),
        ] {
            if !search.consider(expr, CandidateFamily::Boolean) {
                break;
            }
        }
        synthesize_ranges(&mut search);
        let bits = active_bits(&domain, request.variable_type);
        synthesize_masks(&mut search, bits, &masks(bits, &request.original));
        if !search.stopped() {
            synthesize_other(&mut search, bits);
        }
    }
    let mut candidates: Vec<Candidate> = search.candidates.into_values().flatten().collect();
    // Round-robin the best family representatives before any second member.
    // Only the explicit result retention budget may then remove a whole family.
    candidates.sort_by(|a, b| {
        (a.source_bytes, &a.source, a.family).cmp(&(b.source_bytes, &b.source, b.family))
    });
    let mut families = HashSet::new();
    let mut first = Vec::new();
    let mut remaining = Vec::new();
    for candidate in candidates {
        if families.insert(candidate.family) {
            first.push(candidate);
        } else {
            remaining.push(candidate);
        }
    }
    first.extend(remaining);
    first.truncate(request.budget.max_results);
    first.sort_by(|a, b| {
        (a.source_bytes, &a.source, a.family).cmp(&(b.source_bytes, &b.source, b.family))
    });
    search.evaluator.stats.cached_values = search.evaluator.memo.len();
    search.evaluator.stats.retained = first.len();
    search.evaluator.stats.equivalent_not_retained = search
        .evaluator
        .stats
        .equivalent
        .saturating_sub(first.len());
    Ok(SearchReport {
        advisory_only: true,
        original: request.original.clone(),
        original_source: request.original_source.clone(),
        original_source_bytes: request.original_source.len(),
        original_rendered: request.original.render(&request.symbol),
        variable_type: request.variable_type,
        result_type: original_type,
        domain: domain.clone(),
        original_defined,
        original_failure,
        candidates: first,
        rejections: search.rejections,
        statistics: search.evaluator.stats,
        budget: request.budget.clone(),
        complete: search.stop_reasons.is_empty(),
        stop_reasons: search.stop_reasons,
        grammar: "typed direct/Boolean forms; labelled interval and unsigned-interval predicates; power-of-two translations with contiguous/source/regular-run masks and labelled comparisons; shifts with comparisons and low masks; scalar arithmetic with source/boundary/power-of-two constants".to_owned(),
        limitations: vec![
            "Equality is exhaustive only over the supplied finite input domain; caller-supplied static reachability and binding evidence are not proved here.".to_owned(),
            "Observed-closure domains remain conditional hypotheses even when every value in their closure is compared.".to_owned(),
            "The model is C11 LP64 two's-complement integer evaluation with distinct int/long/long-long ranks; implementation-defined signed casts/right shifts are withheld.".to_owned(),
            "A single stable ordinary variable is assumed. Volatile/atomic accesses, side effects, evaluation counts and binding identity must be excluded by the caller.".to_owned(),
            "The bounded grammar and representative retention are heuristic; raw source bytes do not establish compressed-file size, machine-code cost or global optimality.".to_owned(),
            "Semantic signature hashes are verified by full typed vectors; early mismatches retain a counterexample instead of pretending the full vector was evaluated.".to_owned(),
        ],
    })
}

mod decimal {
    use serde::{Deserialize, Deserializer, Serializer};

    pub fn serialize<S: Serializer>(value: &i128, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&value.to_string())
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<i128, D::Error> {
        String::deserialize(deserializer)?
            .parse()
            .map_err(serde::de::Error::custom)
    }
}

mod decimal_values {
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub fn serialize<S: Serializer>(values: &[i128], serializer: S) -> Result<S::Ok, S::Error> {
        values
            .iter()
            .map(ToString::to_string)
            .collect::<Vec<_>>()
            .serialize(serializer)
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<Vec<i128>, D::Error> {
        Vec::<String>::deserialize(deserializer)?
            .into_iter()
            .map(|value| value.parse().map_err(serde::de::Error::custom))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn integer(value: i128) -> Expr {
        Expr::constant(value, CIntType::I32)
    }

    fn edge_predicate(shift: i128, last: i128) -> Expr {
        let rank = Expr::binary(BinaryOp::Shr, Expr::Var, integer(shift));
        Expr::binary(
            BinaryOp::LogicalOr,
            Expr::binary(BinaryOp::Eq, rank.clone(), integer(0)),
            Expr::binary(BinaryOp::Eq, rank, integer(last)),
        )
    }

    fn affine_predicate(offset: i128, mask: i128) -> Expr {
        Expr::unary(
            UnaryOp::LogicalNot,
            Expr::binary(
                BinaryOp::BitAnd,
                Expr::binary(BinaryOp::Add, Expr::Var, integer(offset)),
                integer(mask),
            ),
        )
    }

    fn domain(values: impl IntoIterator<Item = i128>) -> FiniteDomain {
        FiniteDomain {
            values: values.into_iter().collect(),
            provenance: DomainProvenance::StaticConservative,
            description: "test caller-proved finite domain".to_owned(),
        }
    }

    fn request(original: Expr, values: impl IntoIterator<Item = i128>) -> SearchRequest {
        SearchRequest {
            original_source: original.render("to"),
            original,
            symbol: "to".to_owned(),
            variable_type: CIntType::I32,
            domain: domain(values),
            budget: SearchBudget::default(),
        }
    }

    #[test]
    fn discovers_affine_mask_from_domain_and_generic_grammar() {
        let report = compare_and_suggest(&request(edge_predicate(4, 7), 0..128)).unwrap();
        let candidate = report
            .candidates
            .iter()
            .find(|candidate| candidate.source == "!(to+16&96)")
            .unwrap_or_else(|| {
                panic!(
                    "affine candidate missing: {:?}; {:?}; {:?}",
                    report
                        .candidates
                        .iter()
                        .map(|candidate| &candidate.source)
                        .collect::<Vec<_>>(),
                    report.statistics,
                    report.stop_reasons
                )
            });
        assert_eq!(candidate.evidence.checked_values, 128);
        assert!(candidate.evidence.equivalent);
        assert_eq!(candidate.evidence.original_type, CIntType::I32);
        assert!(report.statistics.evaluation_steps <= report.budget.max_evaluations);
        assert!(report.statistics.cache_hits > 0);
        assert!(report.statistics.semantic_duplicates > 0);
        assert!(report.statistics.comparison_reuses > 0);
        assert!(report.statistics.reclaimed_cached_values > 0);
        assert!(report
            .candidates
            .iter()
            .any(|candidate| candidate.family == CandidateFamily::Range));
        assert!(report
            .candidates
            .iter()
            .any(|candidate| candidate.family == CandidateFamily::UnsignedRange));

        let mut different = request(edge_predicate(2, 7), 0..32);
        different.symbol = "lane".to_owned();
        different.original_source = different.original.render("lane");
        let report = compare_and_suggest(&different).unwrap();
        assert!(report
            .candidates
            .iter()
            .any(|candidate| candidate.source == "!(lane+4&24)"));
    }

    #[test]
    fn valid_board_subset_is_not_a_name_or_encoding_special_case() {
        let mut input = request(
            edge_predicate(4, 7),
            (0..128).filter(|value| value & 0x88 == 0),
        );
        input.symbol = "destination".to_owned();
        let report = compare_and_suggest(&input).unwrap();
        assert_eq!(report.domain.values.len(), 64);
        for candidate in &report.candidates {
            assert!(
                compare_expressions(
                    &input.original,
                    &candidate.expression,
                    input.variable_type,
                    &input.domain
                )
                .unwrap()
                .equivalent
            );
        }
        // Representative retention may keep a still shorter field on this
        // smaller domain, but the proposed PR expression must independently pass.
        assert!(
            compare_expressions(
                &input.original,
                &affine_predicate(16, 96),
                input.variable_type,
                &input.domain
            )
            .unwrap()
            .equivalent
        );
    }

    #[test]
    fn outside_domain_values_and_overflow_are_real_counterexamples() {
        let original = edge_predicate(4, 7);
        let candidate = affine_predicate(16, 96);
        let rejected =
            compare_expressions(&original, &candidate, CIntType::I32, &domain(0..129)).unwrap();
        assert!(!rejected.equivalent);
        let witness = rejected.counterexample.unwrap();
        assert_eq!(witness.input, 128);
        assert_eq!(witness.original.unwrap().value, 0);
        assert_eq!(witness.candidate.unwrap().value, 1);
        let rejected = compare_expressions(
            &original,
            &candidate,
            CIntType::I32,
            &domain([i32::MAX as i128]),
        )
        .unwrap();
        assert_eq!(
            rejected.counterexample.unwrap().candidate_error,
            Some(EvalError::SignedOverflow)
        );
        let rejected =
            compare_expressions(&original, &candidate, CIntType::I32, &domain([-1])).unwrap();
        assert_eq!(
            rejected.counterexample.unwrap().original_error,
            Some(EvalError::NegativeSignedRightShift)
        );
        let witnesses =
            probe_outside_domain(&original, &candidate, CIntType::I32, &domain(0..128), 12)
                .unwrap();
        assert!(witnesses
            .iter()
            .any(|witness| witness.input == 128 && witness.reason == "typed result differs"));
        let high_bit_guard_values = domain([0, 7, 112, 119, 256]);
        assert!(
            !compare_expressions(&original, &candidate, CIntType::I32, &high_bit_guard_values)
                .unwrap()
                .equivalent
        );
    }

    #[test]
    fn observed_closure_never_acquires_static_provenance() {
        let mut input = request(edge_predicate(4, 7), 0..128);
        input.domain.provenance = DomainProvenance::ObservedClosure;
        let report = compare_and_suggest(&input).unwrap();
        assert_eq!(report.domain.provenance, DomainProvenance::ObservedClosure);
        assert!(!report.candidates.is_empty());
        assert!(report
            .candidates
            .iter()
            .all(|candidate| candidate.evidence.scope == DomainProvenance::ObservedClosure));
        // A broader inferred closure must actually be compared, not represented
        // by the sparse endpoints which happened to be sampled.
        let candidate = Expr::binary(BinaryOp::Ne, Expr::Var, integer(5));
        assert!(
            compare_expressions(&integer(1), &candidate, CIntType::I32, &domain([0, 10]))
                .unwrap()
                .equivalent
        );
        assert!(
            !compare_expressions(&integer(1), &candidate, CIntType::I32, &domain(0..11))
                .unwrap()
                .equivalent
        );
    }

    #[test]
    fn c_integer_conversions_wrap_and_preserve_rank() {
        let u32_add = Expr::binary(BinaryOp::Add, Expr::Var, integer(1));
        assert_eq!(
            eval(&u32_add, u32::MAX as i128, CIntType::U32).unwrap(),
            TypedValue {
                value: 0,
                c_type: CIntType::U32
            }
        );
        let u64_mul = Expr::binary(BinaryOp::Mul, Expr::Var, Expr::Var);
        assert_eq!(
            eval(&u64_mul, u64::MAX as i128, CIntType::U64)
                .unwrap()
                .value,
            1
        );
        let mixed = Expr::binary(BinaryOp::Lt, Expr::Var, Expr::constant(0, CIntType::U32));
        assert_eq!(eval(&mixed, -1, CIntType::I32).unwrap().value, 0);
        let widened = Expr::binary(BinaryOp::Add, Expr::Var, Expr::constant(-1, CIntType::I64));
        assert_eq!(
            eval(&widened, u32::MAX as i128, CIntType::U32).unwrap(),
            TypedValue {
                value: u32::MAX as i128 - 1,
                c_type: CIntType::I64
            }
        );
        let ranked = Expr::binary(
            BinaryOp::Add,
            Expr::Var,
            Expr::constant(-1, CIntType::I64LongLong),
        );
        assert_eq!(
            eval(&ranked, 0, CIntType::U64).unwrap(),
            TypedValue {
                value: u64::MAX as i128,
                c_type: CIntType::U64LongLong
            }
        );
        let comparison = compare_expressions(
            &Expr::cast(CIntType::I64LongLong, Expr::Var),
            &Expr::Var,
            CIntType::I64,
            &domain([0, 1]),
        )
        .unwrap();
        assert!(!comparison.equivalent);
        assert_eq!(
            comparison.reason.as_deref(),
            Some("C result type/rank differs")
        );
        assert_eq!(
            eval(
                &Expr::cast(CIntType::I32, Expr::Var),
                u32::MAX as i128,
                CIntType::U32
            ),
            Err(EvalError::SignedConversionOutOfRange)
        );
    }

    #[test]
    fn undefined_and_implementation_defined_operations_are_withheld() {
        let cases = [
            (
                Expr::binary(BinaryOp::Add, Expr::Var, integer(1)),
                i32::MAX as i128,
                EvalError::SignedOverflow,
            ),
            (
                Expr::unary(UnaryOp::Negate, Expr::Var),
                i32::MIN as i128,
                EvalError::SignedOverflow,
            ),
            (
                Expr::binary(BinaryOp::Div, Expr::Var, integer(-1)),
                i32::MIN as i128,
                EvalError::SignedOverflow,
            ),
            (
                Expr::binary(BinaryOp::Rem, Expr::Var, integer(-1)),
                i32::MIN as i128,
                EvalError::SignedOverflow,
            ),
            (
                Expr::binary(BinaryOp::Rem, Expr::Var, integer(0)),
                12,
                EvalError::DivisionByZero,
            ),
            (
                Expr::binary(BinaryOp::Shr, Expr::Var, integer(1)),
                -1,
                EvalError::NegativeSignedRightShift,
            ),
            (
                Expr::binary(BinaryOp::Shl, Expr::Var, integer(32)),
                0,
                EvalError::InvalidShift,
            ),
            (
                Expr::binary(BinaryOp::Shl, Expr::Var, integer(-1)),
                0,
                EvalError::InvalidShift,
            ),
            (
                Expr::binary(BinaryOp::Shl, Expr::Var, integer(1)),
                -1,
                EvalError::InvalidShift,
            ),
            (
                Expr::binary(BinaryOp::Shl, Expr::Var, integer(31)),
                1,
                EvalError::InvalidShift,
            ),
        ];
        for (expr, value, error) in cases {
            assert_eq!(
                eval(&expr, value, CIntType::I32),
                Err(error),
                "{} at {value}",
                expr.render("x")
            );
        }
        let report = compare_and_suggest(&request(edge_predicate(4, 7), [-1, 0])).unwrap();
        assert!(!report.original_defined);
        assert!(!report.complete);
        assert!(report.candidates.is_empty());
        assert_eq!(
            report.original_failure.unwrap().original_error,
            Some(EvalError::NegativeSignedRightShift)
        );
    }

    #[test]
    fn short_circuit_suppresses_only_unexecuted_failures() {
        let bad = Expr::binary(BinaryOp::Div, integer(1), integer(0));
        let and = Expr::binary(BinaryOp::LogicalAnd, Expr::Var, bad.clone());
        let or = Expr::binary(BinaryOp::LogicalOr, Expr::Var, bad);
        assert_eq!(eval(&and, 0, CIntType::I32).unwrap().value, 0);
        assert_eq!(eval(&and, 1, CIntType::I32), Err(EvalError::DivisionByZero));
        assert_eq!(eval(&or, 1, CIntType::I32).unwrap().value, 1);
        assert_eq!(eval(&or, 0, CIntType::I32), Err(EvalError::DivisionByZero));
        let hidden_shift = Expr::binary(
            BinaryOp::LogicalOr,
            integer(1),
            Expr::binary(BinaryOp::Shr, Expr::Var, integer(100)),
        );
        assert!(
            compare_expressions(
                &hidden_shift,
                &integer(1),
                CIntType::I32,
                &domain([-1, 0, 1])
            )
            .unwrap()
            .equivalent
        );
        let report = compare_and_suggest(&request(and, [0])).unwrap();
        assert!(report.original_defined);
        assert!(report
            .candidates
            .iter()
            .any(|candidate| candidate.source == "0"));
    }

    #[test]
    fn conditional_is_lazy_and_converts_selected_branch_to_the_common_type() {
        let expr = Expr::conditional(Expr::Var, integer(-1), Expr::constant(0, CIntType::U32));
        assert_eq!(
            eval(&expr, 1, CIntType::I32).unwrap(),
            TypedValue {
                value: u32::MAX as i128,
                c_type: CIntType::U32
            }
        );
        assert_eq!(
            eval(&expr, 0, CIntType::I32).unwrap(),
            TypedValue {
                value: 0,
                c_type: CIntType::U32
            }
        );
        let lazy = Expr::conditional(
            integer(1),
            integer(7),
            Expr::binary(BinaryOp::Div, integer(1), integer(0)),
        );
        assert!(
            compare_expressions(&lazy, &integer(7), CIntType::I32, &domain([0, 1]))
                .unwrap()
                .equivalent
        );
        let report = compare_and_suggest(&request(lazy, [0, 1])).unwrap();
        assert!(report.original_defined);
        assert!(report
            .candidates
            .iter()
            .any(|candidate| candidate.source == "7"));
        let grouped = Expr::conditional(
            Expr::conditional(Expr::Var, integer(0), integer(1)),
            integer(2),
            Expr::conditional(Expr::Var, integer(3), integer(4)),
        );
        assert_eq!(grouped.render("x"), "(x?0:1)?2:x?3:4");
        let nested_arithmetic = Expr::binary(
            BinaryOp::Add,
            integer(1),
            Expr::conditional(Expr::Var, integer(0), integer(7)),
        );
        assert_eq!(nested_arithmetic.render("x"), "1+(x?0:7)");
    }

    #[test]
    fn source_rendering_preserves_precedence_association_and_literal_types() {
        assert_eq!(affine_predicate(16, 96).render("to"), "!(to+16&96)");
        assert_eq!(
            Expr::binary(BinaryOp::Sub, Expr::Var, integer(-1)).render("x"),
            "x- -1"
        );
        assert_eq!(
            Expr::unary(UnaryOp::Negate, integer(-1)).render("x"),
            "-(-1)"
        );
        let association = Expr::binary(
            BinaryOp::Add,
            Expr::Var,
            Expr::binary(BinaryOp::Add, integer(1), integer(2)),
        );
        assert_eq!(association.render("x"), "x+(1+2)");
        assert_eq!(
            Expr::constant(i32::MIN as i128, CIntType::I32).render("x"),
            "(-2147483647-1)"
        );
        assert_eq!(
            Expr::constant(i64::MIN as i128, CIntType::I64LongLong).render("x"),
            "(-9223372036854775807LL-1)"
        );
        assert_eq!(
            Expr::constant(u64::MAX as i128, CIntType::U64).render("x"),
            "18446744073709551615UL"
        );
        assert_eq!(
            Expr::unary(UnaryOp::LogicalNot, Expr::unary(UnaryOp::BitNot, Expr::Var)).render("x"),
            "!~x"
        );
    }

    #[test]
    fn finite_budgets_never_turn_incomplete_comparison_into_equivalence() {
        let mut input = request(edge_predicate(4, 7), 0..128);
        input.budget.max_evaluations = 3;
        let report = compare_and_suggest(&input).unwrap();
        assert!(!report.complete);
        assert!(!report.original_defined);
        assert!(report.candidates.is_empty());
        assert_eq!(report.statistics.evaluation_steps, 3);
        input.budget = SearchBudget {
            max_candidates: 5,
            max_cached_values: 0,
            ..SearchBudget::default()
        };
        let report = compare_and_suggest(&input).unwrap();
        assert!(!report.complete);
        assert_eq!(report.statistics.generated, 5);
        assert_eq!(report.statistics.cached_values, 0);
        assert!(report.statistics.memo_capacity_skips > 0);
        for candidate in report.candidates {
            assert_eq!(candidate.evidence.checked_values, 128);
        }
        input.domain.values.clear();
        assert!(compare_and_suggest(&input).unwrap_err().contains("empty"));
    }

    #[test]
    fn serialization_preserves_full_unsigned_values_and_expression_contract() {
        let expr = Expr::constant(u64::MAX as i128, CIntType::U64LongLong);
        let json = serde_json::to_string(&expr).unwrap();
        assert!(json.contains("\"18446744073709551615\""));
        assert_eq!(serde_json::from_str::<Expr>(&json).unwrap(), expr);
        let original = domain([0, u64::MAX as i128]);
        let encoded = serde_json::to_string(&original).unwrap();
        assert_eq!(
            serde_json::from_str::<FiniteDomain>(&encoded).unwrap(),
            original
        );
    }

    #[test]
    fn signature_hashes_are_indexes_not_equality_proofs() {
        let budget = SearchBudget::default();
        let inputs = [0, 1];
        let mut evaluator = Evaluator::new(CIntType::I32, &inputs, &budget);
        let zero = evaluator.compile(&integer(0));
        let one = evaluator.compile(&integer(1));
        for input in 0..inputs.len() {
            evaluator.memo.insert((zero, input), Ok(0));
            evaluator.memo.insert((one, input), Ok(1));
        }
        evaluator.filled[zero] = inputs.len();
        evaluator.filled[one] = inputs.len();
        // Inject an actual index collision instead of trusting a probabilistic
        // test to happen upon the same u64 hash.
        evaluator
            .signatures
            .insert(evaluator.signature_hash(one), vec![zero]);
        evaluator.register_full_vector(one);
        assert_eq!(evaluator.canonical(one), one);
        assert_eq!(evaluator.stats.semantic_duplicates, 0);
        assert_eq!(evaluator.stats.semantic_signatures, 1);
        assert_eq!(evaluator.evaluate(one, 1).unwrap(), Ok(1));
    }

    #[test]
    fn semantic_memo_requires_complete_vectors_and_exact_definedness_and_type() {
        let budget = SearchBudget::default();
        let inputs = [0, 1, 2];
        let mut evaluator = Evaluator::new(CIntType::I32, &inputs, &budget);
        let zero = evaluator.compile(&integer(0));
        for index in 0..inputs.len() {
            evaluator.evaluate(zero, index).unwrap().unwrap();
        }
        let masked = evaluator.compile(&Expr::binary(BinaryOp::BitAnd, Expr::Var, integer(1)));
        assert_eq!(evaluator.evaluate(masked, 0).unwrap(), Ok(0));
        assert_ne!(evaluator.canonical(masked), zero);
        assert_eq!(evaluator.evaluate(masked, 1).unwrap(), Ok(1));
        assert_eq!(evaluator.evaluate(masked, 2).unwrap(), Ok(0));
        assert_ne!(evaluator.canonical(masked), zero);
        let subtraction = evaluator.compile(&Expr::binary(BinaryOp::Sub, Expr::Var, Expr::Var));
        for index in 0..inputs.len() {
            assert_eq!(evaluator.evaluate(subtraction, index).unwrap(), Ok(0));
        }
        assert_eq!(evaluator.canonical(subtraction), zero);
        assert_eq!(evaluator.stats.reclaimed_cached_values, inputs.len());
        let unsigned_zero = evaluator.compile(&Expr::constant(0, CIntType::U32));
        for index in 0..inputs.len() {
            evaluator.evaluate(unsigned_zero, index).unwrap().unwrap();
        }
        assert_ne!(evaluator.canonical(unsigned_zero), zero);

        let one = evaluator.compile(&integer(1));
        for index in 0..inputs.len() {
            evaluator.evaluate(one, index).unwrap().unwrap();
        }
        let quotient_expr = Expr::binary(BinaryOp::Div, Expr::Var, Expr::Var);
        let quotient = evaluator.compile(&quotient_expr);
        assert_eq!(
            evaluator.evaluate(quotient, 0).unwrap(),
            Err(EvalError::DivisionByZero)
        );
        for index in 1..inputs.len() {
            assert_eq!(evaluator.evaluate(quotient, index).unwrap(), Ok(1));
        }
        assert_ne!(evaluator.canonical(quotient), one);
        let guarded = evaluator.compile(&Expr::conditional(Expr::Var, quotient_expr, integer(1)));
        for index in 0..inputs.len() {
            assert_eq!(evaluator.evaluate(guarded, index).unwrap(), Ok(1));
        }
        assert_eq!(evaluator.canonical(guarded), one);
        // A new request has a new input domain and a new memo: no prior alias can
        // promote sampled-domain coincidence to a broader equivalence.
        let other_inputs = [0, 1, 3];
        let mut other = Evaluator::new(CIntType::I32, &other_inputs, &budget);
        let masked = other.compile(&Expr::binary(BinaryOp::BitAnd, Expr::Var, integer(1)));
        assert_eq!(other.evaluate(masked, 2).unwrap(), Ok(1));
    }

    #[test]
    fn shared_dag_matches_scalar_semantics_across_types_operators_and_boundaries() {
        let types = [
            CIntType::I32,
            CIntType::U32,
            CIntType::I64,
            CIntType::U64,
            CIntType::I64LongLong,
            CIntType::U64LongLong,
        ];
        let operators = [
            BinaryOp::Add,
            BinaryOp::Sub,
            BinaryOp::Mul,
            BinaryOp::Div,
            BinaryOp::Rem,
            BinaryOp::Shl,
            BinaryOp::Shr,
            BinaryOp::BitAnd,
            BinaryOp::BitOr,
            BinaryOp::BitXor,
            BinaryOp::Eq,
            BinaryOp::Ne,
            BinaryOp::Lt,
            BinaryOp::Le,
            BinaryOp::Gt,
            BinaryOp::Ge,
            BinaryOp::LogicalAnd,
            BinaryOp::LogicalOr,
        ];
        let budget = SearchBudget::default();
        for variable_type in types {
            let (minimum, maximum) = variable_type.bounds();
            let mut inputs = vec![
                minimum,
                minimum + 1,
                -1,
                0,
                1,
                2,
                31,
                32,
                63,
                64,
                maximum - 1,
                maximum,
            ];
            inputs.retain(|value| variable_type.contains(*value));
            inputs.sort_unstable();
            inputs.dedup();
            let mut evaluator = Evaluator::new(variable_type, &inputs, &budget);
            let mut expressions = vec![Expr::Var];
            for op in [UnaryOp::Negate, UnaryOp::BitNot, UnaryOp::LogicalNot] {
                expressions.push(Expr::unary(op, Expr::Var));
            }
            for ty in types {
                expressions.push(Expr::cast(ty, Expr::Var));
                let (lo, hi) = ty.bounds();
                let constants = [-1, 0, 1, 31, 32, 63, 64, lo, hi];
                for constant in constants.into_iter().filter(|value| ty.contains(*value)) {
                    let literal = Expr::constant(constant, ty);
                    for op in operators {
                        expressions.push(Expr::binary(op, Expr::Var, literal.clone()));
                    }
                    expressions.push(Expr::conditional(Expr::Var, literal.clone(), Expr::Var));
                    expressions.push(Expr::conditional(Expr::Var, Expr::Var, literal));
                }
            }
            for expression in expressions {
                let id = evaluator.compile(&expression);
                let expected_type = expression.infer_type(variable_type).unwrap();
                assert_eq!(evaluator.nodes[id].ty, expected_type);
                // Nonsequential visitation also exercises incomplete cache
                // entries: only the last missing input may create an alias.
                for index in (0..inputs.len()).rev() {
                    let actual = evaluator
                        .evaluate(id, index)
                        .expect("bounded differential test");
                    let expected =
                        eval(&expression, inputs[index], variable_type).map(|value| value.value);
                    assert_eq!(
                        actual,
                        expected,
                        "{} at {} ({})",
                        expression.render("value"),
                        inputs[index],
                        variable_type.c_name()
                    );
                }
            }
            assert!(evaluator.stats.semantic_duplicates > 0);
            assert!(evaluator.memo.len() <= budget.max_cached_values);
        }
    }
}
