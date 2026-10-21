//! Explicit source embedding in an otherwise byte-preserved submission payload.
//! RustPython parses a declared bytes literal; no Python interpreter executes.
//! Callers must declare source/token/position non-observation and separately
//! establish the embedded source's native equivalence under its compile recipe.

use anyhow::{bail, ensure, Context, Result};
use rustpython_ast::fold::{Fold, Foldable};
use rustpython_parser::{
    ast,
    text_size::{TextRange, TextSize},
    Parse,
};
use serde_json::Value;

const MAX_BYTES: usize = crate::codec::MAX_PAYLOAD;

#[derive(Clone, Debug)]
pub struct Rendered {
    pub data: Vec<u8>,
    pub style: String,
}

#[derive(Debug, PartialEq)]
struct MaskedTree {
    statements: Vec<ast::Stmt<()>>,
    floating_bits: Vec<u64>,
}

struct MaskBytes {
    range: TextRange,
    found: Vec<Vec<u8>>,
    floating_bits: Vec<u64>,
}

impl Fold<TextRange> for MaskBytes {
    type TargetU = ();
    type Error = anyhow::Error;
    type UserContext = ();

    fn will_map_user(&mut self, _user: &TextRange) {}
    fn map_user(&mut self, _user: TextRange, _context: ()) -> Result<()> {
        Ok(())
    }
    fn fold_expr_constant(
        &mut self,
        mut node: ast::ExprConstant<TextRange>,
    ) -> Result<ast::ExprConstant<()>> {
        if node.range == self.range {
            let ast::Constant::Bytes(bytes) = &node.value else {
                bail!("declared embedding is not a Python bytes constant");
            };
            self.found.push(bytes.clone());
            node.value = ast::Constant::Bytes(Vec::new());
        }
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

fn range(start: usize, end: usize) -> Result<TextRange> {
    ensure!(
        start < end && end <= MAX_BYTES,
        "embedding range is empty or exceeds the payload bound"
    );
    Ok(TextRange::new(
        TextSize::try_from(start).context("embedding start exceeds parser range")?,
        TextSize::try_from(end).context("embedding end exceeds parser range")?,
    ))
}

fn utf8_python(payload: &[u8]) -> Result<&str> {
    ensure!(
        payload.len() <= MAX_BYTES,
        "Python payload exceeds the byte bound"
    );
    let text = std::str::from_utf8(payload).context("Python embedding requires UTF-8 source")?;
    // RustPython is explicitly a UTF-8 frontend here. Do not parse a differently
    // declared encoding as UTF-8 and then claim its runtime string values agree.
    let cookie = regex::Regex::new(r"coding[:=]\s*([-\w.]+)")?;
    for line in text.lines().take(2) {
        if line.trim_start().starts_with('#') {
            if let Some(found) = cookie.captures(line) {
                let encoding = found[1].to_ascii_lowercase().replace('_', "-");
                ensure!(
                    matches!(encoding.as_str(), "utf-8" | "utf8"),
                    "Python embedding requires a UTF-8 encoding declaration"
                );
            }
        }
    }
    Ok(text)
}

fn masked_tree(payload: &[u8], selected: TextRange) -> Result<(MaskedTree, Vec<u8>)> {
    let text = utf8_python(payload)?;
    let tree = ast::Suite::parse(text, "<nvcompact-payload>")
        .map_err(|error| anyhow::anyhow!("Python payload parse failed: {error}"))?;
    let mut folder = MaskBytes {
        range: selected,
        found: Vec::new(),
        floating_bits: Vec::new(),
    };
    let statements = tree.fold(&mut folder)?;
    ensure!(folder.found.len() == 1,
        "embedding must match exactly one whole bytes-constant AST range; partial or compound expressions are unsupported");
    let source = folder.found.pop().unwrap();
    Ok((
        MaskedTree {
            statements,
            floating_bits: folder.floating_bits,
        },
        source,
    ))
}

fn literal_value(literal: &[u8]) -> Result<Vec<u8>> {
    let text = std::str::from_utf8(literal).context("literal spelling must be UTF-8")?;
    let parsed = ast::Expr::parse(text, "<nvcompact-bytes>")
        .map_err(|error| anyhow::anyhow!("Python bytes literal parse failed: {error}"))?;
    let ast::Expr::Constant(constant) = parsed else {
        bail!("embedding span is a compound expression rather than one bytes constant");
    };
    ensure!(
        constant.range == range(0, literal.len())?,
        "embedding span includes bytes outside the selected constant"
    );
    let ast::Constant::Bytes(bytes) = constant.value else {
        bail!("embedding span must contain a bytes constant");
    };
    Ok(bytes)
}

#[derive(Debug)]
struct PythonBytes {
    start: usize,
    end: usize,
    tree: MaskedTree,
}

#[derive(Debug)]
pub struct PayloadAdapter {
    payload: Vec<u8>,
    source: Vec<u8>,
    embedding: Option<PythonBytes>,
}

impl PayloadAdapter {
    /// `sha256` pins the literal's exact original spelling at `start..end`.
    /// Adjacent literal tokens are permitted only when their entire combined
    /// Constant range is declared; selecting one token of that Constant fails.
    pub fn new(payload: &[u8], embedding: Option<&Value>) -> Result<Self> {
        ensure!(payload.len() <= MAX_BYTES, "payload exceeds the byte bound");
        let Some(spec) = embedding else {
            return Ok(Self {
                payload: payload.into(),
                source: payload.into(),
                embedding: None,
            });
        };
        let object = spec.as_object().context("embedding must be an object")?;
        ensure!(
            object
                .keys()
                .all(|key| matches!(key.as_str(), "kind" | "start" | "end" | "sha256")),
            "unknown embedding field"
        );
        ensure!(spec["kind"] == "python-bytes", "unsupported embedding kind");
        let start = usize::try_from(
            spec["start"]
                .as_u64()
                .context("embedding start must be an unsigned byte offset")?,
        )?;
        let end = usize::try_from(
            spec["end"]
                .as_u64()
                .context("embedding end must be an unsigned byte offset")?,
        )?;
        let selected = range(start, end)?;
        ensure!(
            end <= payload.len(),
            "embedding range exceeds the actual payload"
        );
        ensure!(
            spec["sha256"].as_str() == Some(crate::sha256(&payload[start..end]).as_str()),
            "embedding literal hash differs from the declaration"
        );
        let (tree, source) = masked_tree(payload, selected)?;
        ensure!(
            literal_value(&payload[start..end])? == source,
            "standalone literal and whole-payload parse disagree"
        );
        Ok(Self {
            payload: payload.into(),
            source,
            embedding: Some(PythonBytes { start, end, tree }),
        })
    }

    pub fn source(&self) -> &[u8] {
        &self.source
    }

    /// At most five spellings, in deterministic order. Source length is not the
    /// objective; callers measure the entire rendered submission envelope.
    pub fn render(&self, source: &[u8]) -> Result<Vec<Rendered>> {
        ensure!(
            source.len() <= MAX_BYTES,
            "embedded source exceeds the byte bound"
        );
        if self.embedding.is_none() {
            return Ok(vec![self.render_style(source, "direct")?]);
        }
        let mut result = Vec::new();
        if source == self.source {
            result.push(self.render_style(source, "original")?);
        }
        for style in [
            "raw-single",
            "raw-double",
            "escaped-single",
            "escaped-double",
        ] {
            if let Some(literal) = encode_literal(source, style)? {
                let embedded = self.embedding.as_ref().unwrap();
                if self.payload.len() - (embedded.end - embedded.start) + literal.len() > MAX_BYTES
                {
                    continue;
                }
                let rendered = self.join_literal(literal, style)?;
                // A raw triple quote can have grammar-sensitive boundaries.
                // Parse it before it enters the portfolio; never trust a byte
                // delimiter heuristic as the semantic acceptance condition.
                if let Err(error) = self.verify(source, &rendered) {
                    if matches!(style, "raw-single" | "raw-double") {
                        continue;
                    }
                    return Err(error)
                        .context("escaped bytes spelling failed its verification invariant");
                }
                if !result.iter().any(|old| old.data == rendered.data) {
                    result.push(rendered);
                }
            }
        }
        ensure!(!result.is_empty(), "no valid bounded Python bytes spelling");
        Ok(result)
    }

    pub fn render_style(&self, source: &[u8], style: &str) -> Result<Rendered> {
        ensure!(
            source.len() <= MAX_BYTES,
            "embedded source exceeds the byte bound"
        );
        let rendered = if self.embedding.is_none() {
            ensure!(style == "direct", "direct payload requires direct spelling");
            Rendered {
                data: source.into(),
                style: style.into(),
            }
        } else if style == "original" {
            ensure!(
                source == self.source,
                "original spelling cannot contain changed source"
            );
            Rendered {
                data: self.payload.clone(),
                style: style.into(),
            }
        } else {
            let literal = encode_literal(source, style)?
                .context("requested bytes spelling is inapplicable")?;
            self.join_literal(literal, style)?
        };
        self.verify(source, &rendered)?;
        Ok(rendered)
    }

    fn join_literal(&self, literal: Vec<u8>, style: &str) -> Result<Rendered> {
        let embedded = self.embedding.as_ref().context("no literal embedding")?;
        let length = self.payload.len() - (embedded.end - embedded.start) + literal.len();
        ensure!(
            length <= MAX_BYTES,
            "rendered payload exceeds the byte bound"
        );
        let mut data = Vec::with_capacity(length);
        data.extend_from_slice(&self.payload[..embedded.start]);
        data.extend_from_slice(&literal);
        data.extend_from_slice(&self.payload[embedded.end..]);
        Ok(Rendered {
            data,
            style: style.into(),
        })
    }

    pub fn verify(&self, source: &[u8], rendered: &Rendered) -> Result<()> {
        ensure!(
            source.len() <= MAX_BYTES && rendered.data.len() <= MAX_BYTES,
            "source or rendered payload exceeds the byte bound"
        );
        let Some(embedded) = &self.embedding else {
            ensure!(
                rendered.style == "direct" && rendered.data == source,
                "direct payload changed bytes"
            );
            return Ok(());
        };
        let prefix = &self.payload[..embedded.start];
        let suffix = &self.payload[embedded.end..];
        ensure!(
            rendered.data.len() >= prefix.len() + suffix.len()
                && rendered.data.starts_with(prefix)
                && rendered.data.ends_with(suffix),
            "rendered payload changed bytes outside the declared literal"
        );
        let end = rendered.data.len() - suffix.len();
        let literal = &rendered.data[embedded.start..end];
        if rendered.style == "original" {
            ensure!(
                source == self.source && rendered.data == self.payload,
                "original spelling or source changed"
            );
        } else {
            let spelling = encode_literal(source, &rendered.style)?
                .context("inapplicable recorded bytes spelling")?;
            ensure!(
                spelling == literal,
                "rendered literal differs from its declared spelling recipe"
            );
        }
        ensure!(
            literal_value(literal)? == source,
            "rendered bytes literal does not recover the exact source"
        );
        let (tree, parsed_source) = masked_tree(&rendered.data, range(embedded.start, end)?)?;
        ensure!(
            parsed_source == source,
            "whole-payload bytes constant differs from the embedded source"
        );
        ensure!(
            tree == embedded.tree,
            "rendered payload changed outer typed AST or floating bits"
        );
        Ok(())
    }
}

fn encode_literal(source: &[u8], style: &str) -> Result<Option<Vec<u8>>> {
    let (raw, quote) = match style {
        "raw-single" => (true, b'\''),
        "raw-double" => (true, b'"'),
        "escaped-single" => (false, b'\''),
        "escaped-double" => (false, b'"'),
        _ => bail!("unknown bytes spelling recipe"),
    };
    let mut out = Vec::with_capacity(source.len().saturating_add(8).min(MAX_BYTES));
    if raw {
        let delimiter = [quote; 3];
        if !source.is_ascii()
            || source.contains(&0)
            || source.contains(&b'\r')
            || source.windows(3).any(|part| part == delimiter)
            || source.last() == Some(&quote)
            || source
                .iter()
                .rev()
                .take_while(|&&byte| byte == b'\\')
                .count()
                % 2
                != 0
        {
            return Ok(None);
        }
        if source.len() + 8 > MAX_BYTES {
            return Ok(None);
        }
        out.extend_from_slice(b"br");
        out.extend_from_slice(&delimiter);
        out.extend_from_slice(source);
        out.extend_from_slice(&delimiter);
    } else {
        const HEX: &[u8; 16] = b"0123456789abcdef";
        out.extend_from_slice(&[b'b', quote]);
        for &byte in source {
            match byte {
                b'\\' => out.extend_from_slice(b"\\\\"),
                b'\n' => out.extend_from_slice(b"\\n"),
                b'\r' => out.extend_from_slice(b"\\r"),
                b'\t' => out.extend_from_slice(b"\\t"),
                byte if byte == quote => out.extend_from_slice(&[b'\\', byte]),
                32..=126 => out.push(byte),
                byte => out.extend_from_slice(&[
                    b'\\',
                    b'x',
                    HEX[(byte >> 4) as usize],
                    HEX[(byte & 15) as usize],
                ]),
            }
            if out.len() >= MAX_BYTES {
                return Ok(None);
            }
        }
        out.push(quote);
    }
    Ok(Some(out))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn adapter(prefix: &[u8], literal: &[u8], suffix: &[u8]) -> PayloadAdapter {
        let payload = [prefix, literal, suffix].concat();
        PayloadAdapter::new(
            &payload,
            Some(&json!({"kind":"python-bytes", "start":prefix.len(),
            "end":prefix.len()+literal.len(), "sha256":crate::sha256(literal)})),
        )
        .unwrap()
    }

    #[test]
    fn direct_payload_has_no_hidden_wrapper() {
        let adapter = PayloadAdapter::new(b"int x;", None).unwrap();
        assert_eq!(adapter.source(), b"int x;");
        let rendered = adapter.render(b"\0\xff").unwrap();
        assert_eq!(rendered.len(), 1);
        assert_eq!(rendered[0].data, b"\0\xff");
        assert!(adapter.render_style(b"x", "original").is_err());
        assert!(adapter
            .verify(
                b"x",
                &Rendered {
                    data: b"y".to_vec(),
                    style: "direct".into()
                }
            )
            .is_err());
    }

    #[test]
    fn python_spelling_recovers_source_and_preserves_outer_tree() {
        let adapter = adapter(
            b"values=(0.0,-0.0,1e300,2.5j)\nx=",
            b"b'int x;'",
            b"\ny=b'int x;'\n",
        );
        assert_eq!(adapter.source(), b"int x;");
        let baseline = adapter.render(adapter.source()).unwrap();
        assert_eq!(baseline[0].style, "original");
        assert!(baseline
            .iter()
            .all(|candidate| adapter.verify(adapter.source(), candidate).is_ok()));
        let changed = b"int main(void){return 0;}\n";
        let candidates = adapter.render(changed).unwrap();
        assert!(candidates
            .iter()
            .all(|candidate| candidate.style != "original"));
        assert!(candidates
            .iter()
            .any(|candidate| candidate.style == "raw-single"));
        for candidate in candidates {
            adapter.verify(changed, &candidate).unwrap();
            assert_eq!(
                adapter
                    .render_style(changed, &candidate.style)
                    .unwrap()
                    .data,
                candidate.data
            );
            assert!(candidate.data.ends_with(b"\ny=b'int x;'\n"));
        }
        let tree = &adapter.embedding.as_ref().unwrap().tree;
        assert_eq!(
            tree.floating_bits,
            vec![
                0.0_f64.to_bits(),
                0.0_f64.to_bits(),
                1e300_f64.to_bits(),
                0.0_f64.to_bits(),
                2.5_f64.to_bits()
            ]
        );
    }

    #[test]
    fn quote_backslash_control_and_non_ascii_bytes_have_exact_fallbacks() {
        let adapter = adapter(b"x=", b"b''", b"\n");
        for source in [
            b"'''\"\"\"\\".as_slice(),
            b"a\r\nb\0\xff\\",
            "한글".as_bytes(),
            b"'",
            b"\\",
            b"",
        ] {
            let variants = adapter.render(source).unwrap();
            assert!(variants
                .iter()
                .any(|item| item.style == "escaped-single" || item.style == "original"));
            for rendered in variants {
                adapter.verify(source, &rendered).unwrap();
                assert_eq!(
                    literal_value(&rendered.data[2..rendered.data.len() - 1]).unwrap(),
                    source
                );
            }
        }
        assert!(adapter.render_style(b"\xff", "raw-single").is_err());
        assert!(adapter.render_style(b"\\", "raw-double").is_err());
    }

    #[test]
    fn embedding_requires_exact_constant_range_and_literal_hash() {
        let payload = b"x=b'a' b'b'\n";
        let spec = |start: usize, end: usize| {
            json!({"kind":"python-bytes", "start":start,
            "end":end, "sha256":crate::sha256(&payload[start..end])})
        };
        assert!(PayloadAdapter::new(payload, Some(&spec(2, 6))).is_err());
        assert!(PayloadAdapter::new(payload, Some(&spec(3, 10))).is_err());
        let whole = PayloadAdapter::new(payload, Some(&spec(2, 11))).unwrap();
        assert_eq!(whole.source(), b"ab");
        assert!(whole.render(b"cd").is_ok());
        let mut wrong = spec(2, 11);
        wrong["sha256"] = json!("0".repeat(64));
        assert!(PayloadAdapter::new(payload, Some(&wrong)).is_err());
        for expression in [
            b"b'a'+b'b'".as_slice(),
            b"(b'a')",
            b"bytes([97])",
            b"'a'",
            b" b'a' ",
        ] {
            let source = [b"x=".as_slice(), expression, b"\n"].concat();
            let declaration = json!({"kind":"python-bytes", "start":2, "end":2+expression.len(),
                "sha256":crate::sha256(expression)});
            assert!(
                PayloadAdapter::new(&source, Some(&declaration)).is_err(),
                "accepted {:?}",
                expression
            );
        }
    }

    #[test]
    fn outer_byte_mutations_and_expression_injection_are_rejected() {
        let adapter = adapter(b"x=", b"b'a'", b"; y=1.0\n");
        let good = adapter.render_style(b"b", "escaped-single").unwrap();
        let mut prefix = good.clone();
        prefix.data[0] = b'z';
        assert!(adapter.verify(b"b", &prefix).is_err());
        let mut suffix = good.clone();
        *suffix.data.last_mut().unwrap() = b' ';
        assert!(adapter.verify(b"b", &suffix).is_err());
        let injected = Rendered {
            data: b"x=b'b'+danger(); y=1.0\n".to_vec(),
            style: "escaped-single".into(),
        };
        assert!(adapter.verify(b"b", &injected).is_err());
        let changed_type = Rendered {
            data: b"x='b'; y=1.0\n".to_vec(),
            style: "escaped-single".into(),
        };
        assert!(adapter.verify(b"b", &changed_type).is_err());
    }

    #[test]
    fn frontend_does_not_ignore_encoding_or_out_of_bounds_declarations() {
        let literal = b"b'a'";
        let payload = [b"# coding: latin-1\nx=".as_slice(), literal, b"\n"].concat();
        let start = payload.len() - literal.len() - 1;
        let spec = json!({"kind":"python-bytes", "start":start, "end":start+literal.len(),
            "sha256":crate::sha256(literal)});
        assert!(PayloadAdapter::new(&payload, Some(&spec)).is_err());
        assert_eq!(
            adapter(b"# coding: utf-8\nx=", literal, b"\n").source(),
            b"a"
        );
        let mut out = spec;
        out["end"] = json!(u64::MAX);
        assert!(PayloadAdapter::new(&payload, Some(&out)).is_err());
    }
}
