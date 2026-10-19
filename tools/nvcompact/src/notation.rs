//! Deterministic spelling portfolios. A token contract is required; identity is
//! always retained. C integer spelling uses the declared LP64 type model, never
//! value equality alone. The caller still owns compilation and final acceptance.
use anyhow::{bail, Context, Result};
use num_bigint::{BigInt, BigUint};
use num_rational::BigRational;
use num_traits::{One, ToPrimitive, Zero};
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{BTreeSet, HashMap, HashSet};
use std::sync::LazyLock;

pub const MAX_SOURCE: usize = 8 << 20;
pub const MAX_LITERAL: usize = 512;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Variant {
    pub id: String,
    #[serde(skip)]
    pub data: Vec<u8>,
    pub sha256: String,
    pub bytes: usize,
    pub source_bytes: usize,
    pub audit: Vec<Value>,
    pub notes: Vec<String>,
    pub contract: Value,
    pub size_claim: String,
}

impl Variant {
    pub fn new(
        id: &str,
        source: &[u8],
        data: Vec<u8>,
        audit: Vec<Value>,
        notes: Vec<String>,
        contract: Value,
    ) -> Self {
        Self {
            id: id.into(),
            sha256: crate::sha256(&data),
            bytes: data.len(),
            source_bytes: source.len(),
            data,
            audit,
            notes,
            contract,
            size_claim:
                "source bytes only; final submitted-file bytes must be compared independently"
                    .into(),
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct NotationOptions {
    pub language: String,
    pub target: Option<String>,
    pub compact: bool,
    pub token_contract: String,
    pub max_variants: usize,
}
impl Default for NotationOptions {
    fn default() -> Self {
        Self {
            language: "c".into(),
            target: None,
            compact: false,
            token_contract: "opaque".into(),
            max_variants: 16,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Token {
    pub kind: &'static str,
    pub text: String,
    pub start: usize,
    pub end: usize,
}
fn ident_start(c: u8) -> bool {
    c.is_ascii_alphabetic() || c == b'_' || c >= 128
}
fn ident(c: u8) -> bool {
    ident_start(c) || c.is_ascii_digit()
}
fn quoted_end(s: &[u8], pos: usize, quote: u8) -> Result<usize> {
    let mut i = pos + 1;
    while i < s.len() {
        if s[i] == b'\\' {
            i += 2;
        } else if s[i] == quote {
            return Ok(i + 1);
        } else {
            i += 1;
        }
    }
    bail!("unterminated quoted token")
}
static RAW_C: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"^(?:u8|u|U|L)?R\"([^ ()\\\t\r\n]{0,16})\("#).unwrap());
static RAW_RUST: LazyLock<Regex> = LazyLock::new(|| Regex::new(r##"^(?:br|cr|r)(#*)\""##).unwrap());
static QUOTE_C: LazyLock<Regex> = LazyLock::new(|| Regex::new(r#"^(?:u8|u|U|L)?[\"']"#).unwrap());
static QUOTE_RUST: LazyLock<Regex> = LazyLock::new(|| Regex::new(r#"^(?:b|c)?[\"']"#).unwrap());
static RUST_LIFETIME: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^'(?:r#)?[A-Za-z_][A-Za-z_0-9]*").unwrap());

/// Lossless byte-offset lexer. Unknown tokens stay opaque; this is not a parser.
pub(crate) fn lex(source: &str, language: &str) -> Result<Vec<Token>> {
    const PUNCT: &[&str] = &[
        "%:%:", ">>=", "<<=", "...", "->*", "<=>", "..=", "::", "->", "++", "--", "<<", ">>", "<=",
        ">=", "==", "!=", "&&", "||", "*=", "/=", "%=", "+=", "-=", "&=", "^=", "|=", "##", "<:",
        ":>", "<%", "%>", "%:", ".*", "..", "=>",
    ];
    let s = source.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    let mut line_code = false;
    while i < s.len() {
        let start = i;
        let mut kind = "punct";
        if s[i].is_ascii_whitespace() {
            i += 1;
            while i < s.len() && s[i].is_ascii_whitespace() {
                i += 1;
            }
            kind = "space";
        } else if s[i..].starts_with(b"//") {
            i += 2;
            while i < s.len() {
                if language != "rust" && s[i..].starts_with(b"\\\n") {
                    i += 2;
                } else if s[i] == b'\n' {
                    break;
                } else {
                    i += 1;
                }
            }
            kind = if language == "rust"
                && (s[start..].starts_with(b"//!")
                    || (s[start..].starts_with(b"///") && !s[start..].starts_with(b"////")))
            {
                "doc"
            } else {
                "comment"
            };
        } else if s[i..].starts_with(b"/*") {
            let mut depth = 1;
            i += 2;
            while i < s.len() && depth != 0 {
                if language == "rust" && s[i..].starts_with(b"/*") {
                    depth += 1;
                    i += 2;
                } else if s[i..].starts_with(b"*/") {
                    depth -= 1;
                    i += 2;
                } else {
                    i += 1;
                }
            }
            if depth != 0 {
                bail!("unterminated block comment");
            }
            kind = if language == "rust"
                && (s[start..].starts_with(b"/*!")
                    || (s[start..].starts_with(b"/**") && !s[start..].starts_with(b"/***")))
            {
                "doc"
            } else {
                "comment"
            };
        } else if language != "rust" && !line_code && (s[i] == b'#' || s[i..].starts_with(b"%:")) {
            while i < s.len() {
                if s[i..].starts_with(b"\\\n") {
                    i += 2;
                } else if s[i..].starts_with(b"\\\r\n") {
                    i += 3;
                } else if s[i] == b'\n' {
                    i += 1;
                    break;
                } else {
                    i += 1;
                }
            }
            kind = "directive";
        } else {
            let tail = &source[i..];
            let rc = if language == "cpp" {
                RAW_C.captures(tail)
            } else {
                None
            };
            let rr = if language == "rust" {
                RAW_RUST.captures(tail)
            } else {
                None
            };
            let life = if language == "rust" {
                RUST_LIFETIME.find(tail)
            } else {
                None
            };
            let quote = if language == "rust" {
                QUOTE_RUST.find(tail)
            } else {
                QUOTE_C.find(tail)
            };
            if let Some(raw) = rc {
                let prefix = raw.get(0).unwrap().end();
                let marker = format!("){}\"", &raw[1]);
                let end = tail[prefix..]
                    .find(&marker)
                    .context("unterminated C++ raw string")?;
                i += prefix + end + marker.len();
                kind = "quoted";
            } else if let Some(raw) = rr {
                let prefix = raw.get(0).unwrap().end();
                let marker = format!("\"{}", &raw[1]);
                let end = tail[prefix..]
                    .find(&marker)
                    .context("unterminated Rust raw string")?;
                i += prefix + end + marker.len();
                kind = "quoted";
            } else if let Some(life) = life.filter(|m| tail.as_bytes().get(m.end()) != Some(&b'\''))
            {
                i += life.end();
                kind = "lifetime";
            } else if let Some(quote) = quote {
                let pos = i + quote.end() - 1;
                i = quoted_end(s, pos, s[pos])?;
                kind = "quoted";
            } else if s[i].is_ascii_digit()
                || (language != "rust"
                    && s[i] == b'.'
                    && s.get(i + 1).is_some_and(u8::is_ascii_digit))
            {
                i += 1;
                if language == "rust" {
                    if s[start..].starts_with(b"0x")
                        || s[start..].starts_with(b"0o")
                        || s[start..].starts_with(b"0b")
                    {
                        i = start + 2;
                        while i < s.len() && ident(s[i]) {
                            i += 1;
                        }
                    } else {
                        while i < s.len() && (s[i].is_ascii_digit() || s[i] == b'_') {
                            i += 1;
                        }
                        if s.get(i) == Some(&b'.')
                            && s.get(i + 1) != Some(&b'.')
                            && !s.get(i + 1).copied().is_some_and(ident_start)
                        {
                            i += 1;
                            while i < s.len() && (s[i].is_ascii_digit() || s[i] == b'_') {
                                i += 1;
                            }
                        }
                        if s.get(i).is_some_and(|c| matches!(c, b'e' | b'E')) {
                            i += 1;
                            if s.get(i).is_some_and(|c| matches!(c, b'+' | b'-')) {
                                i += 1;
                            }
                        }
                        while i < s.len() && ident(s[i]) {
                            i += 1;
                        }
                    }
                } else {
                    while i < s.len() {
                        if ident(s[i])
                            || matches!(s[i], b'.' | b'\'')
                            || (matches!(s[i], b'+' | b'-')
                                && matches!(s[i - 1], b'e' | b'E' | b'p' | b'P'))
                        {
                            i += 1;
                        } else {
                            break;
                        }
                    }
                }
                kind = "number";
            } else if ident_start(s[i]) {
                i += 1;
                while i < s.len() && ident(s[i]) {
                    i += 1;
                }
                if language == "rust"
                    && &s[start..i] == b"r"
                    && s.get(i) == Some(&b'#')
                    && s.get(i + 1).copied().is_some_and(ident_start)
                {
                    i += 2;
                    while i < s.len() && ident(s[i]) {
                        i += 1;
                    }
                }
                kind = "identifier";
            } else {
                i += PUNCT
                    .iter()
                    .find(|p| s[i..].starts_with(p.as_bytes()))
                    .map_or(1, |p| p.len());
            }
            if kind == "quoted" && matches!(language, "cpp" | "rust") {
                while i < s.len() && ident(s[i]) {
                    i += 1;
                }
            }
        }
        // Every non-ASCII byte outside a quoted token belongs to an opaque
        // identifier, so slicing preserves complete UTF-8 code points.
        let text = source
            .get(start..i)
            .context("unsupported non-UTF-8 token boundary")?
            .to_string();
        if let Some((_, last)) = text.rsplit_once('\n') {
            line_code = !last.trim().is_empty()
                && !matches!(kind, "space" | "comment" | "doc" | "directive");
        } else if !matches!(kind, "space" | "comment" | "doc") {
            line_code = true;
        }
        out.push(Token {
            kind,
            text,
            start,
            end: i,
        });
    }
    Ok(out)
}

fn significant(tokens: &[Token]) -> Vec<(&str, &str)> {
    tokens
        .iter()
        .filter(|t| !matches!(t.kind, "space" | "comment"))
        .map(|t| (t.kind, t.text.as_str()))
        .collect()
}
fn protected_tokens(tokens: &[Token], language: &str) -> HashSet<usize> {
    let sig: Vec<_> = tokens
        .iter()
        .enumerate()
        .filter(|(_, t)| !matches!(t.kind, "space" | "comment" | "doc"))
        .map(|(i, _)| i)
        .collect();
    let mut stack = Vec::new();
    let mut closes = HashMap::new();
    let mut protected = HashSet::new();
    for (p, &i) in sig.iter().enumerate() {
        let t = tokens[i].text.as_str();
        if let Some(end) = match t {
            "(" => Some(")"),
            "[" => Some("]"),
            "{" => Some("}"),
            _ => None,
        } {
            stack.push((p, end));
        } else if matches!(t, ")" | "]" | "}") {
            if stack.last().is_some_and(|(_, expected)| *expected == t) {
                let (start, _) = stack.pop().unwrap();
                closes.insert(start, p);
            } else {
                stack.clear();
            }
        }
    }
    let keywords = [
        "if",
        "while",
        "for",
        "switch",
        "sizeof",
        "_Alignof",
        "_Generic",
        "alignof",
        "decltype",
        "noexcept",
        "static_assert",
    ];
    for (p, &i) in sig.iter().enumerate() {
        let t = &tokens[i];
        let mut begin = None;
        if language == "rust" {
            if t.text == "!" && p != 0 && tokens[sig[p - 1]].kind == "identifier" {
                let mut j = p + 1;
                if j < sig.len() && tokens[sig[j]].kind == "identifier" {
                    j += 1;
                }
                if j < sig.len() && matches!(tokens[sig[j]].text.as_str(), "(" | "[" | "{") {
                    begin = Some(j);
                }
            } else if t.text == "#" {
                let mut j = p + 1;
                if j < sig.len() && tokens[sig[j]].text == "!" {
                    j += 1;
                }
                if j < sig.len() && tokens[sig[j]].text == "[" {
                    begin = Some(j);
                }
            } else if t.kind == "number" && p != 0 && tokens[sig[p - 1]].text == "." {
                protected.insert(i);
            }
        } else if t.text == "("
            && p != 0
            && tokens[sig[p - 1]].kind == "identifier"
            && !keywords.contains(&tokens[sig[p - 1]].text.as_str())
        {
            begin = Some(p);
        }
        if let Some(begin) = begin {
            if let Some(&end) = closes.get(&begin) {
                protected.extend(sig[begin]..=sig[end]);
            }
        }
    }
    protected
}

fn target_pair<'a>(language: &'a str, target: Option<&'a str>) -> Result<(&'a str, &'a str)> {
    let language = match language {
        "c++" => "cpp",
        "py" => "python",
        x => x,
    };
    let target = target.unwrap_or(match language {
        "c" => "c11-lp64",
        "cpp" => "cpp17-lp64",
        "rust" => "rust2021",
        "python" => "python3",
        _ => "",
    });
    if !matches!(
        (language, target),
        ("c", "c11-lp64" | "c23-lp64")
            | ("cpp", "cpp17-lp64")
            | ("rust", "rust2021")
            | ("python", "python3")
    ) {
        bail!("unsupported language/target pair");
    }
    Ok((language, target))
}

fn c_type(value: &BigUint, base: u32, suffix: &str) -> Option<&'static str> {
    let decimal = base == 10;
    let suffix = suffix.to_ascii_lowercase();
    let choices: &[&str] = match suffix.as_str() {
        "" if decimal => &["int", "long", "long long"],
        "" => &[
            "int",
            "unsigned int",
            "long",
            "unsigned long",
            "long long",
            "unsigned long long",
        ],
        "u" => &["unsigned int", "unsigned long", "unsigned long long"],
        "l" if decimal => &["long", "long long"],
        "l" => &["long", "unsigned long", "long long", "unsigned long long"],
        "ul" | "lu" => &["unsigned long", "unsigned long long"],
        "ll" if decimal => &["long long"],
        "ll" => &["long long", "unsigned long long"],
        "ull" | "llu" => &["unsigned long long"],
        _ => &[],
    };
    choices.iter().copied().find(|typ| {
        let bits = if matches!(*typ, "int" | "unsigned int") {
            32
        } else {
            64
        };
        value
            < &(BigUint::one()
                << if typ.starts_with("unsigned") {
                    bits
                } else {
                    bits - 1
                })
    })
}
fn int_forms(value: &BigUint) -> [(u32, &'static str, String); 4] {
    [
        (10, "decimal", value.to_str_radix(10)),
        (16, "hex", format!("0x{}", value.to_str_radix(16))),
        (8, "octal", format!("0o{}", value.to_str_radix(8))),
        (2, "binary", format!("0b{}", value.to_str_radix(2))),
    ]
}
fn integer_forms(
    text: &str,
    language: &str,
    target: &str,
) -> Result<Option<(Value, BTreeSet<(String, String)>)>> {
    let mut forms = BTreeSet::new();
    if matches!(language, "c" | "cpp") {
        if text.contains('\'')
            && (target == "c11-lp64"
                || Regex::new(r"(^|[^0-9a-fA-F])'|'([^0-9a-fA-F]|$)")?.is_match(text))
        {
            return Ok(None);
        }
        let text = text.replace('\'', "");
        let re = Regex::new(r"^(0[xX][0-9a-fA-F]+|0[bB][01]+|0[0-7]*|[1-9][0-9]*)([uUlL]*)$")?;
        let Some(c) = re.captures(&text) else {
            return Ok(None);
        };
        if c[2].contains("lL") || c[2].contains("Ll") {
            return Ok(None);
        }
        let body = &c[1];
        let (base, digits) = if body.starts_with("0x") || body.starts_with("0X") {
            (16, &body[2..])
        } else if body.starts_with("0b") || body.starts_with("0B") {
            (2, &body[2..])
        } else if body.starts_with('0') {
            (8, body)
        } else {
            (10, body)
        };
        if base == 2 && target == "c11-lp64" {
            return Ok(None);
        }
        let Some(value) = BigUint::parse_bytes(digits.as_bytes(), base) else {
            return Ok(None);
        };
        let Some(typ) = c_type(&value, base, &c[2]) else {
            return Ok(None);
        };
        for (base, family, mut body) in int_forms(&value) {
            if base == 2 && target == "c11-lp64" {
                continue;
            }
            if base == 8 {
                body = if value.is_zero() {
                    "0".into()
                } else {
                    format!("0{}", value.to_str_radix(8))
                };
            }
            for suffix in ["", "u", "l", "ul", "ll", "ull"] {
                if c_type(&value, base, suffix) == Some(typ) {
                    forms.insert((format!("{body}{suffix}"), family.into()));
                }
            }
        }
        return Ok(Some((
            json!({"model":target,"kind":"integer","value":value.to_str_radix(10),"type":typ}),
            forms,
        )));
    }
    let compact = text.replace('_', "");
    let re = if language == "rust" {
        Regex::new(
            r"^(0x[0-9a-fA-F]+|0o[0-7]+|0b[01]+|[0-9]+)(u8|i8|u16|i16|u32|i32|u64|i64|u128|i128|usize|isize)?$",
        )?
    } else {
        Regex::new(r"^(0[xX][0-9a-fA-F]+|0[oO][0-7]+|0[bB][01]+|[0-9]+)$")?
    };
    let Some(c) = re.captures(&compact) else {
        return Ok(None);
    };
    let body = &c[1];
    let suffix = c.get(2).map_or("", |m| m.as_str());
    let (base, digits) = if body.to_ascii_lowercase().starts_with("0x") {
        (16, &body[2..])
    } else if body.to_ascii_lowercase().starts_with("0o") {
        (8, &body[2..])
    } else if body.to_ascii_lowercase().starts_with("0b") {
        (2, &body[2..])
    } else {
        (10, body)
    };
    let Some(value) = BigUint::parse_bytes(digits.as_bytes(), base) else {
        return Ok(None);
    };
    if language == "rust" && value.bits() > 128 {
        return Ok(None);
    }
    // Python rejects decimal leading zeroes except an all-zero spelling.
    if language == "python" && base == 10 && body.starts_with('0') && !value.is_zero() {
        return Ok(None);
    }
    for (_, family, body) in int_forms(&value) {
        forms.insert((format!("{body}{suffix}"), family.into()));
    }
    let typ = if language == "python" {
        "int"
    } else if suffix.is_empty() {
        "inferred integer"
    } else {
        suffix
    };
    Ok(Some((
        json!({"model":target,"kind":"integer","value":value.to_str_radix(10),"type":typ}),
        forms,
    )))
}

fn exact_fraction(text: &str) -> Option<BigRational> {
    let lower = text.to_ascii_lowercase();
    let hex = lower.starts_with("0x");
    let (digits, exponent) =
        if let Some((left, right)) = lower.split_once(if hex { 'p' } else { 'e' }) {
            (left, right.parse::<i32>().ok()?)
        } else if hex {
            return None;
        } else {
            (lower.as_str(), 0)
        };
    if exponent.unsigned_abs() > 2048 {
        return None;
    }
    let digits = if hex { &digits[2..] } else { digits };
    let (before, after) = digits.split_once('.').unwrap_or((digits, ""));
    let joined = format!("{before}{after}");
    let n = BigInt::parse_bytes(joined.as_bytes(), if hex { 16 } else { 10 })?;
    let base = BigInt::from(if hex { 2 } else { 10 });
    let exponent = exponent - after.len() as i32 * if hex { 4 } else { 1 };
    if exponent >= 0 {
        Some(BigRational::from_integer(n * base.pow(exponent as u32)))
    } else {
        Some(BigRational::new(n, base.pow((-exponent) as u32)))
    }
}
fn decimal_forms(value: &BigRational, language: &str, suffix: &str) -> BTreeSet<(String, String)> {
    let mut denominator = value.denom().clone();
    let mut twos = 0u32;
    let mut fives = 0u32;
    while (&denominator % 2u8).is_zero() {
        denominator /= 2u8;
        twos += 1;
    }
    while (&denominator % 5u8).is_zero() {
        denominator /= 5u8;
        fives += 1;
    }
    let mut forms = BTreeSet::new();
    if denominator != BigInt::one() {
        return forms;
    }
    let places = twos.max(fives);
    let mut digits =
        (value.numer() * BigInt::from(2).pow(places - twos) * BigInt::from(5).pow(places - fives))
            .to_str_radix(10);
    let mut exponent = -(places as i32);
    if value.is_zero() {
        digits = "0".into();
        exponent = 0;
    } else {
        while digits.ends_with('0') {
            digits.pop();
            exponent += 1;
        }
    }
    if digits.len() > MAX_LITERAL {
        return forms;
    }
    for k in 1..=digits.len() {
        let mantissa = if k == digits.len() {
            digits.clone()
        } else {
            format!("{}.{}", &digits[..k], &digits[k..])
        };
        forms.insert((
            format!(
                "{mantissa}e{}{suffix}",
                exponent + digits.len() as i32 - k as i32
            ),
            "scientific".into(),
        ));
    }
    let point = digits.len() as i32 + exponent;
    if point.unsigned_abs() <= MAX_LITERAL as u32 {
        let mut fixed = if point <= 0 {
            format!("0.{}{digits}", "0".repeat((-point) as usize))
        } else if (point as usize) < digits.len() {
            format!(
                "{}.{}",
                &digits[..point as usize],
                &digits[point as usize..]
            )
        } else {
            format!("{digits}{}.", "0".repeat(point as usize - digits.len()))
        };
        if language == "rust" && !suffix.is_empty() && fixed.ends_with('.') {
            fixed.pop();
        }
        forms.insert((format!("{fixed}{suffix}"), "decimal".into()));
        if language != "rust" && fixed.starts_with("0.") {
            forms.insert((format!("{}{suffix}", &fixed[1..]), "decimal".into()));
        }
    }
    forms
}
fn ieee_bits(value: &BigRational, fraction_bits: usize, exponent_bits: usize) -> Option<u64> {
    if value.is_zero() {
        return Some(0);
    }
    let n = value.numer().to_biguint()?;
    let d = value.denom().to_biguint()?;
    let mut e = n.bits() as i32 - d.bits() as i32;
    if if e >= 0 {
        n < (&d << e as usize)
    } else {
        (&n << (-e) as usize) < d
    } {
        e -= 1;
    }
    let bias = (1i32 << (exponent_bits - 1)) - 1;
    let minimum = 1 - bias;
    let unit = e.max(minimum) - fraction_bits as i32;
    let (n, d) = if unit >= 0 {
        (n, d << unit as usize)
    } else {
        (n << (-unit) as usize, d)
    };
    let mut mantissa = &n / &d;
    let remainder = &n % &d;
    let twice = remainder << 1usize;
    if twice > d || (twice == d && (&mantissa & BigUint::one()) == BigUint::one()) {
        mantissa += BigUint::one();
    }
    if e < minimum {
        return mantissa.to_u64();
    }
    if mantissa == (BigUint::one() << (fraction_bits + 1)) {
        mantissa >>= 1usize;
        e += 1;
    }
    if e > bias {
        return None;
    }
    Some((((e + bias) as u64) << fraction_bits) | (mantissa.to_u64()? - (1u64 << fraction_bits)))
}
fn float_forms(
    text: &str,
    language: &str,
    target: &str,
) -> Result<Option<(Value, BTreeSet<(String, String)>)>> {
    let compact = if matches!(language, "rust" | "python") {
        text.replace('_', "")
    } else if target != "c11-lp64" {
        text.replace('\'', "")
    } else {
        text.into()
    };
    let decimal = r"(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[0-9]+[eE][+-]?[0-9]+";
    let pattern = if language == "rust" {
        format!(r"^({decimal}|[0-9]+)(f32|f64)?$")
    } else if language == "python" {
        format!(r"^({decimal})$")
    } else {
        format!(
            r"^({decimal}|0[xX](?:[0-9a-fA-F]+\.?[0-9a-fA-F]*|\.[0-9a-fA-F]+)[pP][+-]?[0-9]+)([fFlL]?)$"
        )
    };
    let re = Regex::new(&pattern)?;
    let Some(c) = re.captures(&compact) else {
        return Ok(None);
    };
    let body = &c[1];
    let suffix = c.get(2).map_or("", |m| m.as_str()).to_ascii_lowercase();
    if suffix == "l"
        || (language == "rust"
            && (body.starts_with('.')
                || (!suffix.is_empty() && body.ends_with('.'))
                || (suffix.is_empty()
                    && !body.contains('.')
                    && !body.to_ascii_lowercase().contains('e'))))
    {
        return Ok(None);
    }
    let typ = if language == "python" {
        "float"
    } else if language == "rust" {
        if suffix.is_empty() {
            "inferred float"
        } else {
            &suffix
        }
    } else if suffix == "f" {
        "float"
    } else {
        "double"
    };
    let Some(value) = exact_fraction(body) else {
        return Ok(None);
    };
    let mut forms = decimal_forms(&value, language, &suffix);
    let mut widths = vec![(52, 11)];
    if (typ == "float" && language != "python") || typ == "f32" {
        widths = vec![(23, 8)];
    }
    if typ == "inferred float" {
        widths.push((23, 8));
    }
    let mut bits = serde_json::Map::new();
    for (f, e) in widths {
        bits.insert(
            format!("binary{}", if f == 23 { 32 } else { 64 }),
            json!(ieee_bits(&value, f, e)),
        );
    }
    if bits.values().all(Value::is_null) {
        return Ok(None);
    }
    if matches!(language, "c" | "cpp") {
        let d = value.denom().to_biguint().unwrap();
        if (&d & (&d - BigUint::one())).is_zero() {
            let mut n = value.numer().to_biguint().unwrap();
            let mut exponent = -(d.bits() as i32 - 1);
            if !n.is_zero() {
                while (&n & BigUint::one()).is_zero() {
                    n >>= 1usize;
                    exponent += 1;
                }
            }
            let digits = n.to_str_radix(16);
            if digits.len() <= MAX_LITERAL {
                for k in 1..=digits.len() {
                    let mantissa = if k == digits.len() {
                        digits.clone()
                    } else {
                        format!("{}.{}", &digits[..k], &digits[k..])
                    };
                    forms.insert((
                        format!(
                            "0x{mantissa}p{}{suffix}",
                            exponent + 4 * (digits.len() - k) as i32
                        ),
                        "hex".into(),
                    ));
                }
            }
        }
    }
    Ok(Some((
        json!({"model":target,"kind":"float","exact_value":format!("{}/{}",value.numer(),value.denom()),"type":typ,"round_nearest_even_bits":bits,"compiler_condition":"target floating conversion must agree; compile/native-byte verification required"}),
        forms,
    )))
}

pub fn literal_candidates(text: &str, language: &str, target: Option<&str>) -> Result<Vec<Value>> {
    let (language, target) = target_pair(language, target)?;
    if text.len() > MAX_LITERAL {
        return Ok(vec![]);
    }
    if language == "python" {
        return python_literal_candidates(text);
    }
    let parsed = if let Some(x) = integer_forms(text, language, target)? {
        Some(x)
    } else {
        float_forms(text, language, target)?
    };
    let Some((proof, forms)) = parsed else {
        return Ok(vec![]);
    };
    let mut forms: Vec<_> = forms
        .into_iter()
        .filter(|(s, _)| s.len() <= MAX_LITERAL)
        .collect();
    forms.sort_by(|a, b| (a.0.len(), &a.0, &a.1).cmp(&(b.0.len(), &b.0, &b.1)));
    let mut seen = HashSet::new();
    Ok(forms
        .into_iter()
        .filter(|(s, _)| seen.insert(s.clone()))
        .map(|(spelling, family)| json!({"spelling":spelling,"family":family,"proof":proof}))
        .collect())
}
fn choose<'a>(candidates: &'a [Value], original: &str, policy: &str) -> Option<&'a Value> {
    let ordered: Vec<_> = candidates.iter().collect();
    if policy != "shortest" {
        if let Some(value) = ordered
            .iter()
            .find(|c| c["family"].as_str() == Some(policy))
        {
            return Some(value);
        }
    }
    ordered.first().copied().filter(|c| {
        c["spelling"]
            .as_str()
            .is_some_and(|s| s.len() < original.len())
    })
}
fn compact_c_like(source: &str, language: &str) -> Result<(String, Option<String>)> {
    let tokens = lex(source, language)?;
    let protected = protected_tokens(&tokens, language);
    let mut out = String::new();
    let mut prev: Vec<&Token> = vec![];
    let mut i = 0;
    while i < tokens.len() {
        let t = &tokens[i];
        if protected.contains(&i) {
            let start = i;
            while i + 1 < tokens.len() && protected.contains(&(i + 1)) {
                i += 1;
            }
            out.push_str(&source[tokens[start].start..tokens[i].end]);
            prev = vec![&tokens[i]];
        } else if !matches!(t.kind, "space" | "comment") {
            if matches!(t.kind, "directive" | "doc") {
                if !out.is_empty() && !out.ends_with('\n') {
                    out.push('\n');
                }
                out.push_str(&t.text);
                if !t.text.ends_with('\n') {
                    out.push('\n');
                }
                prev.clear();
            } else {
                if !prev.is_empty() {
                    let left: String = prev.iter().map(|t| t.text.as_str()).collect();
                    let mut expected: Vec<_> =
                        prev.iter().map(|t| (t.kind, t.text.as_str())).collect();
                    expected.push((t.kind, t.text.as_str()));
                    let joined = lex(&format!("{left}{}", t.text), language);
                    let rust_prefix = language == "rust"
                        && prev.last().unwrap().kind == "identifier"
                        && (t.kind == "quoted" || t.text.starts_with(['#', '\'']));
                    if joined.as_ref().map_or(true, |v| significant(v) != expected)
                        || rust_prefix
                        || (left.ends_with('?') && t.text.starts_with('?'))
                    {
                        out.push(' ');
                        prev.clear();
                    }
                }
                out.push_str(&t.text);
                prev.push(t);
                if prev.len() > 2 {
                    prev.remove(0);
                }
            }
        }
        i += 1;
    }
    if lex(&out, language).is_ok_and(|other| significant(&other) == significant(&tokens)) {
        Ok((out, None))
    } else {
        Ok((
            source.into(),
            Some("compaction omitted: complete token sequence did not match".into()),
        ))
    }
}
fn rewrite_c_like(
    source: &str,
    language: &str,
    target: &str,
    policy: &str,
    compact: bool,
) -> Result<(Vec<u8>, Vec<Value>, Vec<String>)> {
    let tokens = lex(source, language)?;
    if source.contains("\\\n")
        || source.contains("\\\r\n")
        || Regex::new(r"\?\?[=/(')!<>-]")?.is_match(source)
        || tokens.iter().any(|t| t.kind == "punct" && t.text == "\\")
    {
        return Ok((source.as_bytes().into(), vec![], vec!["identity retained: line-splicing, trigraph or unsupported backslash preprocessing token".into()]));
    }
    let protected = protected_tokens(&tokens, language);
    let mut out = String::new();
    let mut audit = vec![];
    let mut cache = HashMap::new();
    for (i, token) in tokens.iter().enumerate() {
        let mut replacement = token.text.clone();
        let mut proof = None;
        if !protected.contains(&i) {
            if token.kind == "number" {
                if !cache.contains_key(&token.text) {
                    cache.insert(
                        token.text.clone(),
                        literal_candidates(&token.text, language, Some(target))?,
                    );
                }
                if let Some(record) = choose(&cache[&token.text], &token.text, policy) {
                    replacement = record["spelling"].as_str().unwrap().into();
                    proof = Some(record["proof"].clone());
                }
            } else if matches!(language, "c" | "cpp") && token.kind == "punct" {
                if let Some(r) = match token.text.as_str() {
                    "<:" => Some("["),
                    ":>" => Some("]"),
                    "<%" => Some("{"),
                    "%>" => Some("}"),
                    _ => None,
                } {
                    replacement = r.into();
                    proof = Some(json!({"kind":"alternative punctuator"}));
                }
            } else if language == "cpp" && token.kind == "identifier" {
                if let Some(r) = match token.text.as_str() {
                    "and" => Some("&&"),
                    "or" => Some("||"),
                    "not" => Some("!"),
                    "bitand" => Some("&"),
                    "bitor" => Some("|"),
                    "xor" => Some("^"),
                    "compl" => Some("~"),
                    "and_eq" => Some("&="),
                    "or_eq" => Some("|="),
                    "xor_eq" => Some("^="),
                    "not_eq" => Some("!="),
                    _ => None,
                } {
                    replacement = r.into();
                    proof = Some(json!({"kind":"C++ alternative operator token"}));
                }
            }
        }
        if replacement != token.text {
            let mut neighbors = Vec::new();
            if i != 0 {
                neighbors.push(tokens[i - 1].clone());
            }
            let alternative = proof
                .as_ref()
                .and_then(|p| p["kind"].as_str())
                .is_some_and(|p| p.starts_with("alternative") || p.starts_with("C++"));
            neighbors.push(Token {
                kind: if alternative { "punct" } else { token.kind },
                text: replacement.clone(),
                start: 0,
                end: replacement.len(),
            });
            if i + 1 < tokens.len() {
                neighbors.push(tokens[i + 1].clone());
            }
            let text: String = neighbors.iter().map(|t| t.text.as_str()).collect();
            if lex(&text, language).map_or(true, |v| significant(&v) != significant(&neighbors)) {
                replacement = token.text.clone();
                proof = None;
            }
        }
        out.push_str(&replacement);
        if replacement != token.text {
            audit.push(json!({"start_byte":token.start,"end_byte":token.end,"before":token.text,"after":replacement,"proof":proof}));
        }
    }
    let mut notes = vec![];
    if compact {
        let (changed, note) = compact_c_like(&out, language)?;
        if let Some(note) = note {
            notes.push(note);
        } else if changed != out {
            audit.push(json!({"operation":"comments and whitespace","proof":{"same_token_sequence":true,"contract":"source/token spelling and locations unobserved"}}));
        }
        out = changed;
    }
    Ok((out.into_bytes(), audit, notes))
}

pub fn generate_variants(source: &[u8], options: &NotationOptions) -> Result<Vec<Variant>> {
    let (language, target) = target_pair(&options.language, options.target.as_deref())?;
    if source.len() > MAX_SOURCE {
        bail!("source exceeds {MAX_SOURCE} bytes");
    }
    if !(1..=32).contains(&options.max_variants) {
        bail!("max_variants must be 1..32");
    }
    if !matches!(
        options.token_contract.as_str(),
        "opaque" | "no-token-observation" | "preprocessed"
    ) {
        bail!("unknown token contract");
    }
    if options.token_contract == "preprocessed" && !matches!(language, "c" | "cpp") {
        bail!("preprocessed token contract is C/C++ only");
    }
    let contract = json!({"language":language,"target":target,"token_contract":options.token_contract,"compact":options.compact,"source_sha256":crate::sha256(source),"required_acceptance":"compile plus program verification; prefer identical native bytes for spelling-only changes","implementation":"native Rust"});
    let mut result = vec![Variant::new(
        "raw",
        source,
        source.into(),
        vec![],
        vec![],
        contract.clone(),
    )];
    if options.token_contract == "opaque" {
        result[0]
            .notes
            .push("no rewriting without an explicit source/token non-observation contract".into());
        return Ok(result);
    }
    let source_text = match std::str::from_utf8(source) {
        Ok(text) => text,
        Err(_) => {
            result[0]
                .notes
                .push("identity retained: this Rust frontend requires UTF-8 source".into());
            return Ok(result);
        }
    };
    let mut recipes = vec![("shortest".to_string(), "shortest", false)];
    if options.compact {
        recipes.push(("shortest-compact".into(), "shortest", true));
    }
    for policy in ["hex", "decimal", "scientific", "octal", "binary"] {
        recipes.push((policy.into(), policy, false));
    }
    if options.compact {
        for policy in ["hex", "decimal", "scientific", "octal", "binary"] {
            recipes.push((format!("{policy}-compact"), policy, true));
        }
    }
    for (id, policy, compact) in recipes.into_iter().take(options.max_variants - 1) {
        let (data, audit, notes) = if language == "python" {
            rewrite_python(source_text, policy, compact)?
        } else {
            rewrite_c_like(source_text, language, target, policy, compact)?
        };
        result.push(Variant::new(
            &id,
            source,
            data,
            audit,
            notes,
            contract.clone(),
        ));
    }
    Ok(result)
}

// RustPython is a parser dependency, not an embedded interpreter. Locations are
// erased structurally while typed constants, contexts, names and float bits are
// retained. No Python subprocess or inherited Python implementation is used.
use rustpython_ast::fold::{Fold, Foldable};
use rustpython_parser::{ast, lexer, text_size::TextRange, Mode, Parse, Tok};

#[derive(Default)]
struct Canonical {
    floating_bits: Vec<u64>,
}
impl Fold<TextRange> for Canonical {
    type TargetU = ();
    type Error = std::convert::Infallible;
    type UserContext = ();
    fn will_map_user(&mut self, _user: &TextRange) {}
    fn map_user(&mut self, _user: TextRange, _context: ()) -> std::result::Result<(), Self::Error> {
        Ok(())
    }
    fn fold_expr_constant(
        &mut self,
        node: ast::ExprConstant<TextRange>,
    ) -> std::result::Result<ast::ExprConstant<()>, Self::Error> {
        match &node.value {
            ast::Constant::Float(value) => self.floating_bits.push(value.to_bits()),
            ast::Constant::Complex { real, imag } => {
                self.floating_bits.push(real.to_bits());
                self.floating_bits.push(imag.to_bits());
            }
            _ => {}
        }
        rustpython_ast::fold::fold_expr_constant(self, node)
    }
}
fn python_tree(source: &str) -> Result<(Vec<ast::Stmt<()>>, Vec<u64>)> {
    let tree = ast::Suite::parse(source, "<nvcompact>")
        .map_err(|e| anyhow::anyhow!("Python parse failed: {e}"))?;
    let mut folder = Canonical::default();
    let tree = tree.fold(&mut folder).unwrap();
    Ok((tree, folder.floating_bits))
}
fn python_expr(source: &str) -> Result<(ast::Expr<()>, Vec<u64>)> {
    let tree = ast::Expr::parse(source, "<nvcompact-literal>")
        .map_err(|e| anyhow::anyhow!("Python literal parse failed: {e}"))?;
    let mut folder = Canonical::default();
    let tree = tree.fold(&mut folder).unwrap();
    Ok((tree, folder.floating_bits))
}
fn python_quote(value: &str, quote: char) -> String {
    let mut out = String::new();
    out.push(quote);
    for c in value.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c == quote => {
                out.push('\\');
                out.push(c);
            }
            c if c.is_control() && (c as u32) <= 255 => {
                out.push_str(&format!("\\x{:02x}", c as u32))
            }
            c if c.is_control() && (c as u32) <= 65535 => {
                out.push_str(&format!("\\u{:04x}", c as u32))
            }
            c if c.is_control() => out.push_str(&format!("\\U{:08x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push(quote);
    out
}
fn python_bytes_quote(value: &[u8], quote: char) -> String {
    let mut out = format!("b{quote}");
    for &b in value {
        match b {
            b'\\' => out.push_str("\\\\"),
            b'\n' => out.push_str("\\n"),
            b'\r' => out.push_str("\\r"),
            b'\t' => out.push_str("\\t"),
            b if b == quote as u8 => {
                out.push('\\');
                out.push(quote);
            }
            32..=126 => out.push(b as char),
            b => out.push_str(&format!("\\x{b:02x}")),
        }
    }
    out.push(quote);
    out
}
fn normalize_python_float(text: &str) -> String {
    let mut text = text.to_ascii_lowercase();
    if let Some((mantissa, exponent)) = text.split_once('e') {
        if let Ok(exponent) = exponent.parse::<i32>() {
            let mantissa = if mantissa.contains('.') {
                mantissa.trim_end_matches('0').trim_end_matches('.')
            } else {
                mantissa
            };
            text = format!("{mantissa}e{exponent}");
        }
    }
    if !text.contains('.') && !text.contains('e') {
        text.push('.');
    }
    if text.starts_with("0.") {
        text.remove(0);
    }
    text
}
fn python_literal_candidates(text: &str) -> Result<Vec<Value>> {
    let Ok(original) = python_expr(text) else {
        return Ok(vec![]);
    };
    let ast::Expr::Constant(constant) = &original.0 else {
        return Ok(vec![]);
    };
    let mut forms = BTreeSet::new();
    let kind;
    match &constant.value {
        ast::Constant::Int(value) => {
            kind = "int";
            let Some(value) = BigUint::parse_bytes(value.to_string().as_bytes(), 10) else {
                return Ok(vec![]);
            };
            for (_, family, spelling) in int_forms(&value) {
                forms.insert((spelling, family.to_string()));
            }
        }
        ast::Constant::Float(value) if value.is_finite() && *value >= 0.0 => {
            kind = "float";
            let mut candidates = vec![value.to_string()];
            // Every format must parse back to the same typed constant and exact
            // binary64 bits. Decimal presentation heuristics are not proof.
            for precision in 0..=16 {
                candidates.push(format!("{value:.precision$e}"));
                let exponent = if *value == 0.0 {
                    0
                } else {
                    value.abs().log10().floor() as i32
                };
                let places = precision as i32 - exponent;
                if (0..=340).contains(&places) {
                    candidates.push(format!("{value:.places$}", places = places as usize));
                }
            }
            for candidate in candidates {
                let spelling = normalize_python_float(&candidate);
                let family = if spelling.contains('e') {
                    "scientific"
                } else {
                    "decimal"
                };
                forms.insert((spelling, family.into()));
            }
        }
        ast::Constant::Str(value) => {
            kind = "str";
            forms.insert((python_quote(value, '\''), "string".into()));
            forms.insert((python_quote(value, '"'), "string".into()));
            forms.insert((serde_json::to_string(value)?, "string".into()));
        }
        ast::Constant::Bytes(value) => {
            kind = "bytes";
            forms.insert((python_bytes_quote(value, '\''), "string".into()));
            forms.insert((python_bytes_quote(value, '"'), "string".into()));
        }
        _ => return Ok(vec![]),
    }
    let mut forms: Vec<_> = forms
        .into_iter()
        .filter(|(s, _)| s.len() <= MAX_LITERAL)
        .collect();
    forms.sort_by(|a, b| (a.0.len(), &a.0).cmp(&(b.0.len(), &b.0)));
    let mut seen = HashSet::new();
    let mut result = vec![];
    for (spelling, family) in forms {
        if seen.insert(spelling.clone())
            && python_expr(&spelling).is_ok_and(|tree| tree == original)
        {
            result.push(json!({"spelling":spelling,"family":family,"proof":{"model":"python3","kind":kind,"typed_ast_equal":true,"binary64_bits_equal":true,"frontend":"rustpython-parser 0.4"}}));
        }
    }
    Ok(result)
}
#[derive(Clone)]
struct PyToken {
    token: Tok,
    start: usize,
    end: usize,
}
fn python_tokens(source: &str) -> Result<Vec<PyToken>> {
    lexer::lex(source, Mode::Module)
        .map(|r| {
            let (token, range) =
                r.map_err(|e| anyhow::anyhow!("Python tokenization failed: {e:?}"))?;
            let start = usize::from(range.start()).min(source.len());
            let end = usize::from(range.end()).min(source.len());
            Ok(PyToken { token, start, end })
        })
        .collect()
}
fn protected_python_comment(source: &str, token: &PyToken) -> bool {
    matches!(token.token, Tok::Comment(_))
        && ((token.start == 0 && source[token.start..token.end].starts_with("#!"))
            || source[..token.start]
                .bytes()
                .filter(|&b| b == b'\n')
                .count()
                < 2
                && Regex::new(r"coding[=:]\s*[-\w.]+")
                    .unwrap()
                    .is_match(&source[token.start..token.end]))
}
fn python_token_signature(source: &str, tokens: &[PyToken]) -> Vec<(String, String)> {
    tokens
        .iter()
        .filter(|t| {
            !matches!(t.token, Tok::EndOfFile)
                && (!matches!(t.token, Tok::Comment(_)) || protected_python_comment(source, t))
                && (!matches!(t.token, Tok::Newline | Tok::NonLogicalNewline) || t.end != t.start)
        })
        .map(|t| (format!("{:?}", t.token), source[t.start..t.end].to_string()))
        .collect()
}
fn python_joinable(source: &str, left: &PyToken, right: &PyToken) -> bool {
    let a = &source[left.start..left.end];
    let b = &source[right.start..right.end];
    // CPython treats a number immediately followed by any identifier/keyword as
    // an invalid decimal literal even where a lexer can split the pair.
    if matches!(
        left.token,
        Tok::Int { .. } | Tok::Float { .. } | Tok::Complex { .. }
    ) && b.as_bytes().first().copied().is_some_and(ident_start)
    {
        return false;
    }
    // A fragment beginning with a closing delimiter is valid in its original
    // program, but RustPython stops before yielding that token without an open
    // delimiter. Two inert opening parentheses cover the two-token fragment;
    // only tokens wholly inside the original fragment are compared. The full
    // program is parsed again after compaction, so this does not grant a grammar
    // exception for mismatched delimiters or invalid surrounding expressions.
    let joined = format!("(({a}{b}");
    let mut observed = vec![];
    for entry in lexer::lex(&joined, Mode::Module) {
        let Ok((token, range)) = entry else { break };
        if !matches!(
            token,
            Tok::Newline | Tok::NonLogicalNewline | Tok::Indent | Tok::Dedent | Tok::EndOfFile
        ) {
            let start = usize::from(range.start()).min(joined.len());
            let end = usize::from(range.end()).min(joined.len());
            if start >= 2 {
                observed.push((format!("{token:?}"), joined[start..end].to_string()));
            }
        }
    }
    observed
        == vec![
            (format!("{:?}", left.token), a.to_string()),
            (format!("{:?}", right.token), b.to_string()),
        ]
}
fn compact_python(source: &str) -> Result<(String, Option<Value>, Option<String>)> {
    let tokens = python_tokens(source)?;
    let mut out = String::new();
    let mut cursor = 0;
    let mut previous: Option<&PyToken> = None;
    let mut removed_comments = 0;
    let mut shortened_gaps = 0;
    for token in &tokens {
        if token.start < cursor {
            return Ok((
                source.into(),
                None,
                Some("Python compaction omitted: overlapping lexer source ranges".into()),
            ));
        }
        let mut gap = source[cursor..token.start].to_string();
        let leading = previous.is_none_or(|p| {
            matches!(
                p.token,
                Tok::Indent | Tok::Dedent | Tok::Newline | Tok::NonLogicalNewline
            )
        }) || gap.contains('\n');
        if !gap.is_empty() && !leading && gap.bytes().all(|c| matches!(c, b' ' | b'\t' | 12)) {
            let replacement = if matches!(
                token.token,
                Tok::Comment(_) | Tok::Newline | Tok::NonLogicalNewline | Tok::EndOfFile
            ) || python_joinable(source, previous.unwrap(), token)
            {
                ""
            } else {
                " "
            };
            if replacement.len() < gap.len() {
                gap = replacement.into();
                shortened_gaps += 1;
            }
        }
        out.push_str(&gap);
        if matches!(token.token, Tok::Comment(_)) && !protected_python_comment(source, token) {
            removed_comments += 1;
        } else {
            out.push_str(&source[token.start..token.end]);
        }
        cursor = token.end;
        previous = Some(token);
    }
    out.push_str(&source[cursor..]);
    if out == source {
        return Ok((out, None, None));
    }
    let same_tokens = python_tokens(&out).is_ok_and(|other| {
        python_token_signature(&out, &other) == python_token_signature(source, &tokens)
    });
    let same_tree = python_tree(&out)
        .ok()
        .zip(python_tree(source).ok())
        .is_some_and(|(a, b)| a == b);
    if !(same_tokens && same_tree) {
        return Ok((
            source.into(),
            None,
            Some(
                "Python compaction omitted: complete token sequence or typed AST did not match"
                    .into(),
            ),
        ));
    }
    let saved = source.len() - out.len();
    Ok((
        out,
        Some(
            json!({"operation":"source-position comments/whitespace","removed_comments":removed_comments,"shortened_horizontal_gaps":shortened_gaps,"source_bytes_saved":saved,"proof":{"same_token_sequence":true,"whole_program_typed_ast_equal":true,"binary64_bits_equal":true,"preserved":["shebang","encoding cookie","indentation","line endings"],"contract":"source/token spelling and locations unobserved","frontend":"rustpython-parser 0.4"}}),
        ),
        None,
    ))
}
fn rewrite_python(
    source: &str,
    policy: &str,
    compact: bool,
) -> Result<(Vec<u8>, Vec<Value>, Vec<String>)> {
    let (prefix, text) = if let Some(text) = source.strip_prefix('\u{feff}') {
        ("\u{feff}", text)
    } else {
        ("", source)
    };
    let cookie = Regex::new(r"coding[=:]\s*([-\w.]+)")?;
    for line in text.lines().take(2) {
        if let Some(c) = cookie.captures(line) {
            let encoding = c[1].to_ascii_lowercase().replace('_', "-");
            if !matches!(encoding.as_str(), "utf-8" | "utf8" | "utf-8-sig")
                && !(text.is_ascii()
                    && matches!(
                        encoding.as_str(),
                        "ascii" | "us-ascii" | "latin-1" | "latin1" | "iso-8859-1"
                    ))
            {
                return Ok((source.as_bytes().into(), vec![], vec!["identity retained: declared Python source encoding is outside this UTF-8 parser contract".into()]));
            }
        }
    }
    let tree = match python_tree(text) {
        Ok(tree) => tree,
        Err(e) => {
            return Ok((
                source.as_bytes().into(),
                vec![],
                vec![format!(
                    "identity retained: unsupported Python frontend syntax: {e}"
                )],
            ));
        }
    };
    let tokens = python_tokens(text)?;
    let mut changes = vec![];
    let mut audit = vec![];
    let mut notes = vec![];
    let mut cache = HashMap::new();
    for token in &tokens {
        if matches!(
            token.token,
            Tok::Int { .. } | Tok::Float { .. } | Tok::String { .. }
        ) {
            let spelling = &text[token.start..token.end];
            if !cache.contains_key(spelling) {
                cache.insert(
                    spelling.to_string(),
                    literal_candidates(spelling, "python", None)?,
                );
            }
            if let Some(record) = choose(&cache[spelling], spelling, policy) {
                let replacement = record["spelling"].as_str().unwrap();
                if replacement != spelling {
                    changes.push((token.start, token.end, replacement.to_string()));
                    audit.push(json!({"start_byte":prefix.len()+token.start,"end_byte":prefix.len()+token.end,"before":spelling,"after":replacement,"proof":record["proof"]}));
                }
            }
        }
    }
    let mut out = text.to_string();
    for (start, end, replacement) in changes.into_iter().rev() {
        out.replace_range(start..end, &replacement);
    }
    if !python_tree(&out).is_ok_and(|other| other == tree) {
        bail!("Python transformed whole-program typed AST or float bits did not match");
    }
    if compact {
        let (other, record, note) = compact_python(&out)?;
        out = other;
        if let Some(record) = record {
            audit.push(record);
        }
        if let Some(note) = note {
            notes.push(note);
        }
    }
    if !python_tree(&out).is_ok_and(|other| other == tree) {
        bail!("Python compacted whole-program typed AST or float bits did not match");
    }
    Ok((format!("{prefix}{out}").into_bytes(), audit, notes))
}

#[cfg(test)]
mod tests {
    use super::*;
    fn spellings(text: &str, language: &str) -> Vec<String> {
        literal_candidates(text, language, None)
            .unwrap()
            .into_iter()
            .map(|x| x["spelling"].as_str().unwrap().to_string())
            .collect()
    }
    fn opts(language: &str) -> NotationOptions {
        NotationOptions {
            language: language.into(),
            compact: true,
            token_contract: "no-token-observation".into(),
            ..Default::default()
        }
    }

    #[test]
    fn typed_literals_do_not_turn_integer_expressions_into_floats() {
        assert!(!spellings("100000", "c").iter().any(|x| x.contains('e')));
        assert!(spellings("100000.", "c").contains(&"1e5".into()));
        assert!(!spellings("2147483648", "c").contains(&"0x80000000".into()));
        assert!(spellings("2147483648", "c").contains(&"0x80000000l".into()));
        assert!(!spellings("0xffffffff", "c").contains(&"4294967295".into()));
        assert!(spellings("0xffffffff", "c").contains(&"4294967295u".into()));
        assert!(spellings("100_000usize", "rust")
            .iter()
            .all(|x| x.ends_with("usize")));
        assert!(spellings("1.0L", "c").is_empty());
    }
    #[test]
    fn floating_candidates_preserve_exact_rational_and_inference_class() {
        let values = literal_candidates("0x1.8p-1f", "c", None).unwrap();
        assert!(values.iter().any(|v| v["spelling"] == ".75f"));
        assert!(values
            .iter()
            .all(|v| v["proof"]["exact_value"] == "3/4" && v["proof"]["type"] == "float"));
        let values = literal_candidates("100000f32", "rust", None).unwrap();
        assert!(values.iter().any(|v| v["spelling"] == "1e5f32"));
        assert!(!spellings("100000", "rust").iter().any(|v| v.contains('e')));
    }
    #[test]
    fn token_boundaries_macros_and_opaque_contract_are_preserved() {
        let source =
            b"#define M(x) #x\nint f(void){ /* note */ return M(100000)[0] + 00016 + 14 + 1;}\n";
        let variants = generate_variants(source, &opts("c")).unwrap();
        assert_eq!(variants[0].data, source);
        let compact = &variants
            .iter()
            .find(|v| v.id == "shortest-compact")
            .unwrap()
            .data;
        let text = String::from_utf8(compact.clone()).unwrap();
        assert!(text.contains("M(100000)"));
        assert!(text.contains("14"));
        assert!(!text.contains("note"));
        for variant in variants {
            assert!(lex(std::str::from_utf8(&variant.data).unwrap(), "c").is_ok());
        }
        let opaque = generate_variants(source, &NotationOptions::default()).unwrap();
        assert_eq!(opaque.len(), 1);
        assert!(!opaque[0].notes.is_empty());
        let ucn = b"int f(int c){int \\u03b1=1;if(c){\\u03b1=2;}else{\\u03b1=3;}return \\u03b1;}";
        assert!(generate_variants(ucn, &opts("c"))
            .unwrap()
            .iter()
            .all(|v| v.data == ucn));
    }
    #[test]
    fn rust_attributes_macros_tuple_indices_and_docs_remain_token_exact() {
        let source = b"/// Keep doc\n#[repr(align(16))]\nstruct A(u8);fn f()->i32{let x=(10,20);m!(100000);x.0+100000}\n";
        let all = generate_variants(source, &opts("rust")).unwrap();
        for v in all {
            let text = String::from_utf8(v.data).unwrap();
            assert!(text.contains("/// Keep doc"));
            assert!(text.contains("#[repr(align(16))]"));
            assert!(text.contains("m!(100000)"));
            assert!(text.contains("x.0"));
        }
    }
    #[test]
    fn python_typed_ast_float_bits_strings_and_source_trivia() {
        let source = "#!/usr/bin/env python3\n# coding: utf-8\nx = 100000.0  # a comment\ny = 0x10\nif x:\n    z = (\"a\"  \"b\", b'\\x41', -0.0)\n    print(z, y)\n";
        let original = python_tree(source).unwrap();
        let variants = generate_variants(source.as_bytes(), &opts("python")).unwrap();
        assert_eq!(variants.len(), 13);
        for v in &variants {
            let text = std::str::from_utf8(&v.data).unwrap();
            assert_eq!(python_tree(text).unwrap(), original);
            assert!(text.starts_with("#!/usr/bin/env python3\n# coding: utf-8\n"));
            assert!(text.contains("\n    "));
            assert_eq!(
                text.bytes().filter(|&b| b == b'\n').count(),
                source.bytes().filter(|&b| b == b'\n').count()
            );
        }
        let compact = variants
            .iter()
            .find(|v| v.id == "shortest-compact")
            .unwrap();
        assert!(compact.bytes < source.len());
        assert!(!std::str::from_utf8(&compact.data)
            .unwrap()
            .contains("a comment"));
        assert!(spellings("100000.0", "python").contains(&"1e5".into()));
        assert!(!spellings("100000", "python").contains(&"1e5".into()));
        assert!(spellings("True", "python").is_empty());
        assert!(spellings("1j", "python").is_empty());
        assert!(spellings("u'abc'", "python").is_empty());
    }
    #[test]
    fn python_preserves_bom_encoding_splices_multiline_strings_and_boundaries() {
        let source = "\u{feff}# coding: utf-8\na = 1 if True else 0\nb = \\\n    2\ns = '''first\n  second\n''' # remove\n";
        let variants = generate_variants(source.as_bytes(), &opts("python")).unwrap();
        for v in variants {
            let text = std::str::from_utf8(&v.data).unwrap();
            assert!(text.starts_with('\u{feff}'));
            assert!(text.contains("1 if"));
            assert!(text.contains("\\\n    "));
            assert_eq!(
                python_tree(text.trim_start_matches('\u{feff}')).unwrap(),
                python_tree(source.trim_start_matches('\u{feff}')).unwrap()
            );
        }
        let outside = "# coding: latin-1\ns='é'\n";
        assert!(generate_variants(outside.as_bytes(), &opts("python"))
            .unwrap()
            .iter()
            .all(|v| v.data == outside.as_bytes()));
        let source = "for (a,b) in [(1,2)]:\n    z = [a] and {b} or (a)\n";
        let (compact, _, note) = compact_python(source).unwrap();
        assert!(note.is_none());
        assert!(compact.contains(")in"));
        assert!(compact.contains("]and"));
        assert!(compact.contains("}or"));
        assert_eq!(python_tree(&compact).unwrap(), python_tree(source).unwrap());
    }
}
