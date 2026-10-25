//! One bounded Clang process owner shared by source-spelling and flow analysis.
//! Sessions own their temporary translation unit and immutable invocation context.
//! Parsed snapshots are observations, not permission to reuse external input:
//! callers recheck preprocessing before reusing a cached original AST proof.
use crate::process::{self, Limits, Output};
use crate::sha256;
use anyhow::{bail, ensure, Context, Result};
use regex::bytes::Regex;
use serde::Serialize;
use serde_json::{json, Value};
use std::cell::Cell;
use std::collections::HashSet;
use std::path::PathBuf;

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct FrontendConfig {
    pub clang: String,
    pub standard: String,
    pub compiler_args: Vec<String>,
    pub source_path: Option<PathBuf>,
    pub seconds: f64,
    pub memory_bytes: u64,
    pub ast_bytes: usize,
}

impl FrontendConfig {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            matches!(self.standard.as_str(), "c11" | "c17" | "gnu11" | "gnu17"),
            "supported C standards: c11, c17, gnu11, gnu17"
        );
        self.validate_limits()
    }

    pub fn validate_cleanup(&self, language: &str) -> Result<()> {
        ensure!(matches!((language, self.standard.as_str()),
            ("c", "c11" | "c17" | "gnu11" | "gnu17") |
            ("cpp", "c++17" | "c++20" | "gnu++17" | "gnu++20")),
            "cleanup supports explicit C11/C17 or C++17/C++20 only; Rust, Python and other languages are unsupported");
        self.validate_limits()
    }

    fn validate_limits(&self) -> Result<()> {
        ensure!(
            self.seconds.is_finite()
                && self.seconds > 0.0
                && self.seconds <= 300.0
                && self.memory_bytes >= 64 << 20
                && (65536..=128 << 20).contains(&self.ast_bytes),
            "frontend budget outside supported bounds"
        );
        validate_args(&self.compiler_args)
    }
}

/// Language belongs to the frontend invocation, not to a filename heuristic.
/// Production C transformations retain their C-only constructor and validator.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum FrontendLanguage {
    C,
    Cpp,
}

impl FrontendLanguage {
    fn clang_name(self) -> &'static str {
        match self {
            Self::C => "c",
            Self::Cpp => "c++",
        }
    }

    fn translation_unit(self) -> &'static str {
        match self {
            Self::C => "translation.c",
            Self::Cpp => "translation.cpp",
        }
    }
}

#[derive(Clone)]
pub(crate) struct ParsedSource {
    pub tree: Value,
    pub macros: HashSet<String>,
    pub main_path: String,
    pub preprocessing: Option<PreprocessingObservation>,
}

#[derive(Clone)]
pub(crate) struct PreprocessingObservation {
    pub sha256: String,
    /// Cross-session identity normalizes only the owned translation-unit path
    /// in preprocessor line markers. Expanded literals and header paths/content
    /// remain exact; the raw sha256 above still guards all in-session reuse.
    pub stable_sha256: Option<String>,
    pub utf8: bool,
}

/// One original preprocessing context retained across a complete search or
/// replay, independently of its changing candidate bases and AST lifetimes.
/// This is an observation guard, not an additional C transformation or proof.
/// It deliberately accepts opaque header bytes and does not require an AST or
/// an LP64 probe, including when no source-spelling candidates are requested.
pub(crate) struct SourceContext {
    source: Box<[u8]>,
    frontend: FrontendSession,
    observation: PreprocessingObservation,
}

impl SourceContext {
    pub fn new(source: &[u8], config: FrontendConfig) -> Result<Self> {
        let frontend = FrontendSession::new(config, false)?;
        // Until the first observation exists, bounded output exhaustion keeps
        // its original capacity type: no cached proof has been invalidated.
        let bytes = frontend.preprocess(source)?;
        let observation = PreprocessingObservation {
            sha256: sha256(&bytes),
            stable_sha256: None,
            utf8: std::str::from_utf8(&bytes).is_ok(),
        };
        Ok(Self {
            source: source.into(),
            frontend,
            observation,
        })
    }

    pub fn recheck(&self) -> Result<()> {
        self.frontend
            .recheck_observation(&self.source, &self.observation)
    }

    /// Keep context validation outside the operation's success path. A failing
    /// compiler, cost callback or verifier must not hide changed dependencies.
    /// Retain an operation failure in the error explanation while preserving
    /// the typed context failure for the caller's fatal-error classification.
    pub fn observe<T>(&self, operation: impl FnOnce() -> Result<T>) -> Result<T> {
        self.recheck()?;
        let result = operation();
        match (self.recheck(), result) {
            (Ok(()), result) => result,
            (Err(context), Ok(_)) => Err(context),
            (Err(context), Err(operation)) => Err(context.context(format!(
                "operation also failed before post-operation context validation: {operation:#}"
            ))),
        }
    }

    pub fn statistics(&self) -> Value {
        json!({"source_sha256":sha256(&self.source),
            "preprocessing_sha256":self.observation.sha256,"frontend":self.frontend.info,
            "work":self.frontend.statistics(),
            "scope":"one original-source preprocessing observation across the run; no AST or transformation proof"})
    }
}

pub(crate) struct FrontendSession {
    config: FrontendConfig,
    language: FrontendLanguage,
    root: tempfile::TempDir,
    executable: PathBuf,
    executable_sha256: String,
    cwd: PathBuf,
    pub info: Value,
    commands: Cell<usize>,
    ast_parses: Cell<usize>,
    preprocessing_runs: Cell<usize>,
    context_rechecks: Cell<usize>,
}

/// Reusing an observation after an input/tool change is a campaign failure,
/// not a proof that one candidate is merely inapplicable. Consumers must not
/// continue admitting candidates against the stale source snapshot.
#[derive(Debug)]
pub struct FrontendContextChanged {
    reason: &'static str,
}

impl std::fmt::Display for FrontendContextChanged {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.reason)
    }
}

impl std::error::Error for FrontendContextChanged {}

impl FrontendSession {
    pub fn new(config: FrontendConfig, require_lp64: bool) -> Result<Self> {
        config.validate()?;
        Self::create(config, require_lp64, FrontendLanguage::C)
    }

    /// Advisory-only C++ entry. This does not widen the language accepted by
    /// source spelling, flow transformations, compression or context replay.
    pub fn new_for_advice(config: FrontendConfig) -> Result<Self> {
        let language = match config.standard.as_str() {
            "c11" | "c17" | "gnu11" | "gnu17" => FrontendLanguage::C,
            "c++17" | "c++20" | "gnu++17" | "gnu++20" => FrontendLanguage::Cpp,
            _ => bail!("supported advisory standards: c11, c17, gnu11, gnu17, c++17, c++20, gnu++17, gnu++20"),
        };
        config.validate_limits()?;
        Self::create(config, true, language)
    }

    /// Cleanup has a separately declared C/C++ subset. This constructor does
    /// not widen spelling/control-flow transforms or make advice executable.
    pub fn new_for_cleanup(config: FrontendConfig, language: &str) -> Result<Self> {
        config.validate_cleanup(language)?;
        let language = if language == "c" {
            FrontendLanguage::C
        } else {
            FrontendLanguage::Cpp
        };
        Self::create(config, false, language)
    }

    fn create(
        config: FrontendConfig,
        require_lp64: bool,
        language: FrontendLanguage,
    ) -> Result<Self> {
        let executable = process::resolve_tool(&config.clang)?;
        let cwd = config
            .source_path
            .as_ref()
            .map(|p| -> Result<PathBuf> {
                Ok(p.canonicalize()?
                    .parent()
                    .context("source has no parent")?
                    .to_owned())
            })
            .transpose()?
            .unwrap_or(std::env::current_dir()?);
        let executable_sha256 = sha256(&std::fs::read(&executable)?);
        let mut result = Self {
            config,
            language,
            root: tempfile::tempdir()?,
            executable,
            executable_sha256,
            cwd,
            info: Value::Null,
            commands: Cell::new(0),
            ast_parses: Cell::new(0),
            preprocessing_runs: Cell::new(0),
            context_rechecks: Cell::new(0),
        };
        let version = result.execute(
            vec![
                result.executable.to_string_lossy().into_owned(),
                "--version".into(),
            ],
            b"",
            65536,
        )?;
        let version = String::from_utf8_lossy(&version).trim().to_owned();
        ensure!(
            version.to_ascii_lowercase().contains("clang version"),
            "frontend must identify itself as Clang"
        );
        if require_lp64 {
            let mut probe = result.prefix();
            probe.extend(["-fsyntax-only".into(), "-".into()]);
            let assertion = match result.language {
                FrontendLanguage::C => "_Static_assert",
                FrontendLanguage::Cpp => "static_assert",
            };
            let language_name = match result.language {
                FrontendLanguage::C => "C",
                FrontendLanguage::Cpp => "C++",
            };
            let input = format!("{assertion}(sizeof(int)==4 && sizeof(long)==8 && sizeof(long long)==8 && sizeof(void*)==8 && ~0U==4294967295U && ~0UL==18446744073709551615UL && ~0ULL==18446744073709551615ULL && ~0==-1 && ~0L==-1L && ~0LL==-1LL,\"NVCompact {language_name} LP64 two's-complement integer model mismatch\");\n");
            result.execute(probe, input.as_bytes(), 65536)?;
        }
        result.info = json!({"executable":result.executable,"executable_sha256":result.executable_sha256,
            "version":version,"standard":result.config.standard,"compiler_args":result.config.compiler_args,
            "source_include_directory":result.cwd,"seconds_per_parse":result.config.seconds,
            "address_space_bytes":result.config.memory_bytes,"ast_output_bytes":result.config.ast_bytes});
        // Preserve existing C context identities and report snapshots exactly.
        if result.language == FrontendLanguage::Cpp {
            result.info["language"] = json!("c++");
        }
        Ok(result)
    }

    pub fn matches(&self, config: &FrontendConfig) -> bool {
        self.config == *config
    }

    pub fn statistics(&self) -> Value {
        json!({"commands":self.commands.get(),"ast_parses":self.ast_parses.get(),
            "preprocessing_runs":self.preprocessing_runs.get(),"context_rechecks":self.context_rechecks.get(),
            "scope":"one owned frontend session; counters include failed attempts; final native/cost/replay checks are separate"})
    }

    fn ensure_current(&self) -> Result<()> {
        let bytes = std::fs::read(&self.executable).context(FrontendContextChanged {
            reason: "frontend executable became unreadable during source analysis",
        })?;
        if sha256(&bytes) != self.executable_sha256 {
            return Err(FrontendContextChanged {
                reason: "frontend executable changed during source analysis",
            }
            .into());
        }
        Ok(())
    }

    fn prefix(&self) -> Vec<String> {
        let mut result = vec![
            self.executable.to_string_lossy().into_owned(),
            "-x".into(),
            self.language.clang_name().into(),
            format!("-std={}", self.config.standard),
        ];
        result.extend(self.config.compiler_args.clone());
        result.extend(["-iquote".into(), self.cwd.to_string_lossy().into_owned()]);
        result
    }

    fn execute(&self, command: Vec<String>, input: &[u8], maximum: usize) -> Result<Vec<u8>> {
        self.ensure_current()?;
        let limits = Limits {
            seconds: self.config.seconds,
            memory_bytes: self.config.memory_bytes,
            output_bytes: maximum,
            cpu_seconds: self.config.seconds.ceil() as u64 + 1,
            file_bytes: maximum as u64,
        };
        self.commands.set(self.commands.get() + 1);
        let output = process::run(&command, input, &self.cwd, &limits)?;
        self.ensure_current()?;
        if output.output_limited && !output.timed_out {
            if let Some(probe) = frontend_syntax_probe(&command) {
                let probe_limits = Limits {
                    output_bytes: maximum.min(65536),
                    file_bytes: maximum.min(65536) as u64,
                    ..limits
                };
                self.commands.set(self.commands.get() + 1);
                let checked = process::run(&probe, input, &self.cwd, &probe_limits)?;
                self.ensure_current()?;
                checked.check("Clang syntax recheck after frontend output exhaustion")?;
                return check_frontend_output(output, "Clang frontend", maximum);
            }
        }
        output.check("Clang frontend")?;
        Ok(output.stdout)
    }

    fn preprocess(&self, source: &[u8]) -> Result<Vec<u8>> {
        let path = self.root.path().join(self.language.translation_unit());
        std::fs::write(&path, source)?;
        let mut command = self.prefix();
        command.extend([
            "-E".into(),
            "-dD".into(),
            path.to_string_lossy().into_owned(),
        ]);
        self.preprocessing_runs
            .set(self.preprocessing_runs.get() + 1);
        self.execute(command, b"", self.config.ast_bytes)
    }

    /// Expanded compiler input for dependency cleanup. Unlike the context
    /// observation, definitions and line markers are omitted; emitted pragmas,
    /// expanded literals and all actual source tokens remain observable.
    pub fn expanded_source(&self, source: &[u8]) -> Result<Vec<u8>> {
        let path = self.root.path().join(self.language.translation_unit());
        std::fs::write(&path, source)?;
        let mut command = self.prefix();
        command.extend([
            "-E".into(),
            "-P".into(),
            path.to_string_lossy().into_owned(),
        ]);
        self.preprocessing_runs
            .set(self.preprocessing_runs.get() + 1);
        self.execute(command, b"", self.config.ast_bytes)
    }

    /// A previously parsed base is reusable only while its actual preprocessing
    /// observation still agrees. This checks include resolution and macro state
    /// rather than guessing a complete cache key from header filenames.
    pub fn recheck(&self, source: &[u8], snapshot: &ParsedSource) -> Result<()> {
        let expected = snapshot
            .preprocessing
            .as_ref()
            .context("snapshot has no preprocessing observation")?;
        self.recheck_observation(source, expected)
    }

    fn recheck_observation(
        &self,
        source: &[u8],
        expected: &PreprocessingObservation,
    ) -> Result<()> {
        self.context_rechecks.set(self.context_rechecks.get() + 1);
        let bytes=self.preprocess(source).context(FrontendContextChanged {
            reason: "original preprocessing context could not be revalidated; recorded source analysis cannot be reused",
        })?;
        if sha256(&bytes) != expected.sha256 {
            return Err(FrontendContextChanged {
                reason: "original preprocessing context changed; recorded source analysis cannot be reused",
            }
            .into());
        }
        Ok(())
    }

    pub fn parse(&self, source: &[u8], definitions: bool) -> Result<ParsedSource> {
        self.parse_impl(source, definitions, false)
    }

    /// Advisory profiles need an identity across independently created sessions.
    /// Ordinary compression/flow/spelling paths do not compute this extra hash.
    pub fn parse_for_advice(&self, source: &[u8]) -> Result<ParsedSource> {
        self.parse_impl(source, true, true)
    }

    fn parse_impl(&self, source: &[u8], definitions: bool, stable: bool) -> Result<ParsedSource> {
        let before = if definitions {
            Some(sha256(&self.preprocess(source)?))
        } else {
            None
        };
        let path = self.root.path().join(self.language.translation_unit());
        std::fs::write(&path, source)?;
        let mut command = self.prefix();
        command.extend([
            "-fsyntax-only".into(),
            "-Xclang".into(),
            "-ast-dump=json".into(),
            path.to_string_lossy().into_owned(),
        ]);
        self.ast_parses.set(self.ast_parses.get() + 1);
        let tree: Value =
            serde_json::from_slice(&self.execute(command, b"", self.config.ast_bytes)?)
                .context("Clang AST JSON is invalid or exceeds supported nesting")?;
        ensure!(
            tree["kind"] == "TranslationUnitDecl",
            "unsupported Clang AST shape"
        );
        let mut macros = HashSet::new();
        let preprocessing = if definitions {
            let bytes = self.preprocess(source)?;
            let digest = sha256(&bytes);
            if Some(&digest) != before.as_ref() {
                return Err(FrontendContextChanged {
                    reason: "preprocessing context changed while capturing a source AST snapshot",
                }
                .into());
            }
            let utf8 = std::str::from_utf8(&bytes).is_ok();
            let pattern = Regex::new(r"(?m)^\s*#\s*define\s+([A-Za-z_][A-Za-z_0-9]*)")?;
            // The C macro names admitted here are ASCII. The original flow
            // analyzer allowed non-UTF-8 header literals; spelling analysis
            // applies its own stricter encoding contract to this observation.
            for capture in pattern.captures_iter(&bytes) {
                macros.insert(std::str::from_utf8(&capture[1])?.to_owned());
            }
            Some(PreprocessingObservation {
                sha256: digest,
                stable_sha256: stable
                    .then(|| stable_preprocessing_digest(&bytes, &path.to_string_lossy())),
                utf8,
            })
        } else {
            None
        };
        Ok(ParsedSource {
            tree,
            macros,
            main_path: path.to_string_lossy().into_owned(),
            preprocessing,
        })
    }
}

/// Preserve everything except the session-owned source path inside Clang line
/// directives. In particular, do not normalize an expanded __FILE__ literal:
/// such a program observes the temporary frontend path and must not silently
/// acquire cross-session equality. Hash incrementally instead of copying AST-
/// sized preprocessor output into another buffer.
fn stable_preprocessing_digest(bytes: &[u8], main_path: &str) -> String {
    use sha2::{Digest, Sha256};
    use std::sync::LazyLock;
    static MARKER: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r#"^#\s+[0-9]+\s+\"([^\"]+)\""#).expect("fixed line marker pattern")
    });
    let mut hash = Sha256::new();
    for line in bytes.split_inclusive(|&b| b == b'\n') {
        if let Some(path) = MARKER.captures(line).and_then(|c| c.get(1)) {
            if path.as_bytes() == main_path.as_bytes() {
                hash.update(&line[..path.start()]);
                hash.update(b"<nvcompact-owned-translation-unit>");
                hash.update(&line[path.end()..]);
                continue;
            }
        }
        hash.update(line);
    }
    hex::encode(hash.finalize())
}

pub fn validate_args(values: &[String]) -> Result<()> {
    const PAIRED: &[&str] = &[
        "-I",
        "-isystem",
        "-iquote",
        "-D",
        "-U",
        "--target",
        "-target",
        "--sysroot",
        "-isysroot",
    ];
    const FIXED: &[&str] = &[
        "-m32",
        "-m64",
        "-mavx2",
        "-msse4.2",
        "-mcx16",
        "-funsigned-char",
        "-fsigned-char",
        "-fshort-enums",
        "-ffreestanding",
        "-fno-builtin",
        "-pthread",
    ];
    const PREFIX: &[&str] = &[
        "-I",
        "-D",
        "-U",
        "--target=",
        "--sysroot=",
        "-march=",
        "-mcpu=",
        "-mtune=",
    ];
    let mut i = 0;
    while i < values.len() {
        let v = &values[i];
        if v.contains('\0') {
            bail!("NUL in compiler argv");
        }
        if PAIRED.contains(&v.as_str()) {
            let next = values
                .get(i + 1)
                .context("paired compiler option requires one literal operand")?;
            if next.is_empty() || next.starts_with('-') || next.contains('\0') {
                bail!("{v} requires one literal operand");
            }
            i += 2;
        } else if FIXED.contains(&v.as_str())
            || PREFIX.iter().any(|p| v.starts_with(p) && v.len() > p.len())
        {
            i += 1;
        } else {
            bail!("unsupported frontend argument {v:?}; only declared frontend/ABI inputs, no plugins/response files/output actions");
        }
    }
    Ok(())
}
/// A bounded frontend capture is incomplete. This is not an AST, a successful
/// parse, or evidence that no transformation applies. Callers only expose this
/// error for AST/preprocessing stages after a separate syntax-only check passes.
#[derive(Debug, Serialize)]
pub(crate) struct FrontendOutputLimit {
    label: String,
    maximum_bytes: usize,
    returncode: i32,
    stdout_bytes: usize,
    stderr_bytes: usize,
    captured_stdout_sha256: String,
    captured_stderr_sha256: String,
    stderr_tail: String,
    wall_seconds: f64,
}

impl std::fmt::Display for FrontendOutputLimit {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} exceeded its {}-byte output budget (captured stdout {}, stderr {}, exit {}); frontend proof is incomplete",
            self.label, self.maximum_bytes, self.stdout_bytes, self.stderr_bytes, self.returncode)
    }
}
impl std::error::Error for FrontendOutputLimit {}

pub(crate) fn check_frontend_output(
    output: Output,
    label: &str,
    maximum: usize,
) -> Result<Vec<u8>> {
    if crate::process::cancelled() {
        bail!("cancelled during frontend capture");
    }
    if output.output_limited && !output.timed_out {
        return Err(FrontendOutputLimit {
            label: label.into(),
            maximum_bytes: maximum,
            returncode: output.code,
            stdout_bytes: output.stdout.len(),
            stderr_bytes: output.stderr.len(),
            captured_stdout_sha256: crate::sha256(&output.stdout),
            captured_stderr_sha256: crate::sha256(&output.stderr),
            stderr_tail: String::from_utf8_lossy(
                &output.stderr[output.stderr.len().saturating_sub(8192)..],
            )
            .into_owned(),
            wall_seconds: output.wall_seconds,
        }
        .into());
    }
    output.check(label)?;
    Ok(output.stdout)
}

/// Recognize only the two internally generated AST/preprocessing suffixes.
/// Version/ABI commands and arbitrary argv never become optional capacity stops.
pub(crate) fn frontend_syntax_probe(argv: &[String]) -> Option<Vec<String>> {
    let n = argv.len();
    let prefix = if n >= 4
        && argv[n - 4] == "-fsyntax-only"
        && argv[n - 3] == "-Xclang"
        && argv[n - 2] == "-ast-dump=json"
    {
        n - 4
    } else if n >= 3 && argv[n - 3] == "-E" && matches!(argv[n - 2].as_str(), "-dD" | "-P") {
        n - 3
    } else {
        return None;
    };
    let mut probe = argv[..prefix].to_vec();
    probe.extend(["-fsyntax-only".into(), argv[n - 1].clone()]);
    Some(probe)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt;

    fn real_config(source_path: PathBuf) -> Option<FrontendConfig> {
        let clang = std::env::var("NVCOMPACT_CLANG").unwrap_or_else(|_| "clang".into());
        if process::resolve_tool(&clang).is_err() {
            eprintln!("source context fixture not executed: set NVCOMPACT_CLANG");
            return None;
        }
        Some(FrontendConfig {
            clang,
            standard: "c11".into(),
            compiler_args: vec![],
            source_path: Some(source_path),
            seconds: 5.0,
            memory_bytes: 1 << 30,
            ast_bytes: 65536,
        })
    }

    #[test]
    fn expanded_preprocessing_output_limit_is_incomplete_after_syntax_validation() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("main.c");
        let source = format!("int values[]={{ {} }};\n", "1,".repeat(40_000));
        std::fs::write(&path, &source).unwrap();
        let Some(config) = real_config(path) else {
            return;
        };
        let frontend = FrontendSession::new(config, false).unwrap();
        let error = frontend.expanded_source(source.as_bytes()).unwrap_err();
        assert!(
            error.downcast_ref::<FrontendOutputLimit>().is_some(),
            "{error:#}"
        );
    }

    #[test]
    fn source_context_needs_no_ast_and_preserves_opaque_header_bytes() {
        let directory = tempfile::tempdir().unwrap();
        let source_path = directory.path().join("main.c");
        let header = directory.path().join("context.h");
        let source = b"#include \"context.h\"\nint f(int b){if(b)return 3;else return 4;}\n";
        std::fs::write(&source_path, source).unwrap();
        std::fs::write(&header, b"#define UNUSED_TEXT \"\xff\"\n").unwrap();
        let Some(config) = real_config(source_path) else {
            return;
        };
        let context = SourceContext::new(source, config).unwrap();
        assert!(!context.observation.utf8);
        context.recheck().unwrap();
        assert_eq!(context.statistics()["work"]["ast_parses"], 0);
        // An unused header can change without changing GCC's output. It still
        // invalidates the declared original frontend observation for the run.
        std::fs::write(&header, b"#define UNUSED_TEXT \"different\"\n").unwrap();
        let error = context.recheck().unwrap_err();
        assert!(error.downcast_ref::<FrontendContextChanged>().is_some());
    }

    #[test]
    fn source_context_observes_failed_operations_and_rejects_stale_preconditions() {
        let directory = tempfile::tempdir().unwrap();
        let source_path = directory.path().join("main.c");
        let header = directory.path().join("context.h");
        let source = b"#include \"context.h\"\nint f(void){return 0;}\n";
        std::fs::write(&source_path, source).unwrap();
        std::fs::write(&header, b"#define UNUSED_VALUE 1\n").unwrap();
        let Some(config) = real_config(source_path) else {
            return;
        };
        let context = SourceContext::new(source, config).unwrap();
        let error = context
            .observe(|| -> Result<()> {
                std::fs::write(&header, b"#error changed while compiling\n")?;
                bail!("original compile operation failure")
            })
            .unwrap_err();
        assert!(error.downcast_ref::<FrontendContextChanged>().is_some());
        assert!(format!("{error:#}").contains("original compile operation failure"));
        assert!(format!("{error:#}").contains("changed while compiling"));
        let called = Cell::new(false);
        let error = context
            .observe(|| {
                called.set(true);
                Ok(())
            })
            .unwrap_err();
        assert!(!called.get());
        assert!(error.downcast_ref::<FrontendContextChanged>().is_some());
    }

    #[test]
    fn source_context_distinguishes_initial_capacity_from_later_invalidated_context() {
        let directory = tempfile::tempdir().unwrap();
        let source_path = directory.path().join("main.c");
        let header = directory.path().join("context.h");
        let source = b"#include \"context.h\"\nint f(void){return 0;}\n";
        std::fs::write(&source_path, source).unwrap();
        std::fs::write(&header, b"#define UNUSED_VALUE 1\n").unwrap();
        let Some(config) = real_config(source_path) else {
            return;
        };
        let context = SourceContext::new(source, config.clone()).unwrap();
        let oversized = format!("#define UNUSED_TEXT \"{}\"\n", "x".repeat(100_000));
        let error = context
            .observe(|| {
                std::fs::write(&header, oversized.as_bytes())?;
                Ok(())
            })
            .unwrap_err();
        assert!(error.downcast_ref::<FrontendContextChanged>().is_some());
        assert!(error.downcast_ref::<FrontendOutputLimit>().is_some());
        let error = SourceContext::new(source, config).err().unwrap();
        assert!(error.downcast_ref::<FrontendOutputLimit>().is_some());
        assert!(error.downcast_ref::<FrontendContextChanged>().is_none());
    }

    #[test]
    fn changed_frontend_is_a_context_failure_before_another_parse() {
        let directory = tempfile::tempdir().unwrap();
        let executable = directory.path().join("frontend");
        std::fs::write(
            &executable,
            b"#!/bin/sh\nprintf 'clang version fixture\\n'\n",
        )
        .unwrap();
        std::fs::set_permissions(&executable, std::fs::Permissions::from_mode(0o700)).unwrap();
        let frontend = FrontendSession::new(
            FrontendConfig {
                clang: executable.to_string_lossy().into_owned(),
                standard: "c11".into(),
                compiler_args: vec![],
                source_path: None,
                seconds: 2.0,
                memory_bytes: 64 << 20,
                ast_bytes: 65536,
            },
            false,
        )
        .unwrap();
        std::fs::write(
            &executable,
            b"#!/bin/sh\nprintf 'replacement frontend\\n'\n",
        )
        .unwrap();
        let error = frontend
            .parse(b"int f(void){return 0;}\n", false)
            .err()
            .unwrap();
        assert!(error.downcast_ref::<FrontendContextChanged>().is_some());
        assert_eq!(
            frontend.statistics()["commands"],
            1,
            "modified tool must not execute"
        );
    }
}
