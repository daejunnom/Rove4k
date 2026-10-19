use anyhow::{bail, ensure, Context, Result};
use clap::{Args, Parser, Subcommand};
use nvcompact::{cflow, envelope, native, notation, process, resource, uci, write_json};
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::fs;
use std::io::{Read, Write};
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

#[derive(Parser)]
#[command(
    version,
    about = "Rove4k internal N-version compression, native builds and TCEC submission probes"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}
#[derive(Subcommand)]
enum Command {
    /// Compile/link only. Target and verifier execution requires --verify.
    Build(BuildArgs),
    /// Compare declared implementation/link/deployment/packing candidates.
    Run(BuildArgs),
    /// Freshly rebuild one Rust native recipe; native checks require --verify anew.
    Reproduce(ReproduceArgs),
    /// Generate typed literal/trivia spelling variants with an explicit contract.
    Notation(NotationArgs),
    /// Generate typed C expression/control-flow variants via Clang AST.
    RewriteC(RewriteArgs),
    /// Repack an explicitly described complete external submission file.
    Envelope(EnvelopeArgs),
    /// Reproduce one exact envelope result, without another compression search.
    Replay(ReplayArgs),
    /// Run actual final-artifact UCI and independent legal-move probes.
    Uci(UciArgs),
    /// Read-only resource plan; actual run needs a separate --start.
    Resource {
        #[command(subcommand)]
        command: ResourceCommand,
    },
    /// Run external comparison manifests; never downloads or vendors engine code.
    Engines(EnginesArgs),
    /// Report this Rust runtime and codec versions without starting targets.
    Doctor {
        #[arg(long)]
        json: bool,
    },
}
#[derive(Args, Clone)]
struct BudgetArgs {
    #[arg(long, default_value_t = 600.0)]
    max_seconds: f64,
    #[arg(long, default_value_t = 60.0)]
    command_seconds: f64,
    #[arg(long, default_value_t = 2_147_483_648u64)]
    memory_bytes: u64,
    #[arg(long, default_value_t = 120)]
    cpu_seconds: u64,
    #[arg(long, default_value_t = 1_048_576)]
    max_log_bytes: usize,
    #[arg(long,action=clap::ArgAction::Append)]
    tool: Vec<String>,
}
#[derive(Args)]
struct BuildArgs {
    manifest: PathBuf,
    #[arg(long)]
    out: PathBuf,
    #[arg(long, default_value_t = 2)]
    jobs: usize,
    #[arg(long, default_value_t = 128)]
    max_candidates: usize,
    #[arg(long)]
    profile: Vec<String>,
    #[arg(long)]
    link_profile: Vec<String>,
    #[arg(long)]
    verify: bool,
    #[arg(long)]
    max_bytes: Option<usize>,
    #[command(flatten)]
    budget: BudgetArgs,
}
#[derive(Args)]
struct ReproduceArgs {
    recipe: PathBuf,
    #[arg(long)]
    out: PathBuf,
    #[arg(long)]
    verify: bool,
    #[command(flatten)]
    budget: BudgetArgs,
}
#[derive(Args)]
struct NotationArgs {
    source: PathBuf,
    #[arg(long, default_value = "c")]
    language: String,
    #[arg(long)]
    target: Option<String>,
    #[arg(long, default_value = "opaque")]
    token_contract: String,
    #[arg(long)]
    compact: bool,
    #[arg(long, default_value_t = 16)]
    max_variants: usize,
    #[arg(long)]
    portfolio: Option<PathBuf>,
    #[arg(long)]
    output: Option<PathBuf>,
    #[arg(long, default_value = "shortest")]
    variant: String,
}
#[derive(Args)]
struct RewriteArgs {
    source: PathBuf,
    #[arg(long, default_value = "clang")]
    clang: String,
    #[arg(long, default_value = "c11")]
    standard: String,
    #[arg(long = "compiler-arg", allow_hyphen_values = true)]
    compiler_args: Vec<String>,
    #[arg(long, default_value = "opaque")]
    token_contract: String,
    #[arg(long, default_value_t = 16)]
    max_variants: usize,
    #[arg(long, default_value_t = 2)]
    max_passes: usize,
    #[arg(long)]
    portfolio: Option<PathBuf>,
    #[arg(long)]
    output: Option<PathBuf>,
    #[arg(long)]
    variant: Option<String>,
    #[arg(long)]
    run_manifest: bool,
    #[arg(long)]
    verifier: Option<PathBuf>,
    #[arg(long)]
    run_target: Option<String>,
    #[arg(long)]
    run_contract: Option<String>,
    #[arg(long)]
    codec: Vec<String>,
}
#[derive(Args)]
struct EnvelopeArgs {
    manifest: PathBuf,
    #[arg(long, alias = "out")]
    output: PathBuf,
    #[arg(long)]
    artifact: Option<PathBuf>,
    #[arg(long)]
    thorough: bool,
    #[arg(long)]
    no_notation: bool,
    #[arg(long, default_value_t = 2)]
    jobs: usize,
    #[arg(long)]
    uci: bool,
    #[arg(long)]
    uci_config: Option<PathBuf>,
}
#[derive(Args)]
struct ReplayArgs {
    summary: PathBuf,
    #[arg(long, alias = "out")]
    output: PathBuf,
    #[arg(long, default_value = "smallest")]
    selection: String,
    #[arg(long)]
    uci: bool,
    #[arg(long)]
    uci_config: Option<PathBuf>,
}
#[derive(Args)]
struct UciArgs {
    #[arg(long)]
    binary: PathBuf,
    #[arg(long)]
    report: PathBuf,
    #[arg(long)]
    config: Option<PathBuf>,
    #[arg(long)]
    clock_ms: Option<u64>,
    #[arg(long)]
    increment_ms: Option<u64>,
    #[arg(long)]
    search_seconds: Option<f64>,
    #[arg(long)]
    max_seconds: Option<f64>,
    #[arg(long)]
    memory_bytes: Option<u64>,
    #[arg(long)]
    quick: bool,
    #[arg(long)]
    extensions: bool,
    /// Explicitly set Hash/Threads from config instead of preserving engine defaults.
    #[arg(long)]
    configure_engine_options: bool,
}
#[derive(Subcommand)]
enum ResourceCommand {
    Plan {
        specification: PathBuf,
        #[arg(long)]
        output: PathBuf,
    },
    Run {
        plan: PathBuf,
        #[arg(long)]
        output: PathBuf,
        #[arg(long)]
        start: bool,
    },
}
#[derive(Args)]
struct EnginesArgs {
    #[arg(long)]
    manifests: PathBuf,
    #[arg(long)]
    artifact_root: PathBuf,
    #[arg(long)]
    output: PathBuf,
    #[arg(long)]
    thorough: bool,
    #[arg(long)]
    no_notation: bool,
    #[arg(long, default_value_t = 2)]
    jobs: usize,
    #[arg(long)]
    only: Vec<String>,
    #[arg(long)]
    uci: bool,
    #[arg(long)]
    uci_config: Option<PathBuf>,
}

fn read_json(path: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&bounded_input(path, 4 << 20)?)?)
}
fn bounded_input(path: &Path, limit: usize) -> Result<Vec<u8>> {
    let file = fs::File::open(path)?;
    let meta = file.metadata()?;
    ensure!(
        meta.is_file() && meta.len() <= limit as u64,
        "input must be a bounded regular file"
    );
    let mut bytes = Vec::new();
    file.take(limit as u64 + 1).read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() <= limit,
        "input grew beyond its declared byte limit"
    );
    Ok(bytes)
}
fn new_file(path: &Path, data: &[u8]) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)?
        .write_all(data)?;
    Ok(())
}
fn new_json(path: &Path, value: &Value) -> Result<()> {
    let mut bytes = serde_json::to_vec_pretty(value)?;
    bytes.push(b'\n');
    new_file(path, &bytes)
}
fn native_options(args: &BudgetArgs) -> Result<native::NativeOptions> {
    let mut tools = BTreeMap::new();
    for pair in &args.tool {
        let (k, v) = pair
            .split_once('=')
            .context("--tool needs NAME=EXECUTABLE")?;
        ensure!(
            !k.is_empty() && !v.is_empty() && tools.insert(k.into(), v.into()).is_none(),
            "empty/duplicate tool override"
        );
    }
    Ok(native::NativeOptions {
        max_seconds: args.max_seconds,
        tools,
        limits: process::Limits {
            seconds: args.command_seconds,
            memory_bytes: args.memory_bytes,
            cpu_seconds: args.cpu_seconds,
            output_bytes: args.max_log_bytes,
            ..Default::default()
        },
        ..Default::default()
    })
}
fn source(path: &Path) -> Result<Vec<u8>> {
    bounded_input(path, 8 << 20)
}
fn portfolio(path: &Path, variants: &[notation::Variant], extension: &str) -> Result<()> {
    ensure!(!path.exists(), "portfolio must be a fresh directory");
    fs::create_dir_all(path)?;
    for item in variants {
        new_file(&path.join(format!("{}.{}", item.id, extension)), &item.data)?;
    }
    write_json(&path.join("variants.json"), &variants)?;
    Ok(())
}
fn uci_config(path: Option<&Path>) -> Result<uci::UciConfig> {
    match path {
        Some(p) => Ok(serde_json::from_value(read_json(p)?)?),
        None => Ok(Default::default()),
    }
}
fn protocol(path: &Path, config: &uci::UciConfig, report: &Path) -> Result<Value> {
    let invocation = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir()?.join(path)
    };
    let mut settings = config.clone();
    settings.artifact_path = Some(invocation.to_string_lossy().into_owned());
    let result = uci::verify_engine(&[invocation.to_string_lossy().into_owned()], &settings)?;
    new_json(report, &result)?;
    Ok(result)
}
fn envelope_uci(summary: &mut Value, out: &Path, config: &uci::UciConfig) -> Result<()> {
    if summary["manifest"]["runtime_blocked"].as_str().is_some() {
        summary["uci"] = json!({"status":"blocked","reason":"original resource profile requires separate resource plan and explicit start","historical_note":summary["manifest"]["runtime_blocked"]});
        write_json(&out.join("summary.json"), summary)?;
        return Ok(());
    }
    let baseline = protocol(
        &out.join("original"),
        config,
        &out.join("uci-original.json"),
    )?;
    let candidate = protocol(
        &out.join("smallest"),
        config,
        &out.join("uci-smallest.json"),
    )?;
    summary["uci"] = json!({"status":candidate["verdict"],"original":baseline["verdict"],"smallest":candidate["verdict"]});
    if candidate["verdict"] == "pass" {
        let replay = out.join("protocol-replay");
        envelope::reproduce(&out.join("summary.json"), &replay, "smallest")?;
        let replay_file = replay.join("reproduced");
        let final_result = protocol(&replay_file, config, &out.join("uci-final.json"))?;
        ensure!(
            final_result["verdict"] == "pass",
            "fresh selected artifact failed UCI; investigate cause"
        );
        let bytes = fs::read(out.join("smallest"))?;
        ensure!(
            fs::read(&replay_file)? == bytes,
            "envelope replay changed bytes"
        );
        new_file(&out.join("accepted"), &bytes)?;
        fs::set_permissions(out.join("accepted"), fs::Permissions::from_mode(0o755))?;
        summary["accepted"] = summary["winner"].clone();
        summary["accepted"]["protocol_verdict"] = json!("pass");
        summary["acceptance"] = json!(
            "finite UCI verified; external-command, profile and organizer-rule review separate"
        );
    }
    write_json(&out.join("summary.json"), summary)?;
    Ok(())
}
fn export_rewrite(
    args: &RewriteArgs,
    variants: &[notation::Variant],
    directory: &Path,
) -> Result<()> {
    let verifier = args
        .verifier
        .as_ref()
        .context("--run-manifest requires --verifier")?;
    let target = args
        .run_target
        .as_ref()
        .context("--run-manifest requires --run-target")?;
    let contract = args
        .run_contract
        .as_ref()
        .filter(|s| !s.is_empty())
        .context("--run-manifest requires explicit --run-contract")?;
    // A standalone TU export cannot silently omit local include dependencies.
    let original = String::from_utf8(source(&args.source)?)?;
    ensure!(
        !regex::Regex::new(r#"(?m)^\s*#\s*include\s*\""#)?.is_match(&original),
        "local headers require a hand-written native manifest with explicit inputs"
    );
    ensure!(
        !args.compiler_args.iter().any(|x| x == "-I"
            || x == "-iquote"
            || x == "-isystem"
            || x.starts_with("--sysroot")
            || x.starts_with("-I")),
        "external include trees require explicit native manifest inputs"
    );
    new_file(&directory.join("verify.py"), &source(verifier)?)?;
    let clang = process::resolve_tool(&args.clang)?;
    let mut inputs = variants
        .iter()
        .map(|v| format!("{}.c", v.id))
        .collect::<Vec<_>>();
    inputs.push("verify.py".into());
    let mut commands = vec![
        json!("{cc}"),
        json!(format!("-std={}", args.standard)),
        json!("-Os"),
        json!("-fno-ident"),
        json!("-ffile-prefix-map={root}=."),
    ];
    commands.extend(args.compiler_args.iter().map(|s| json!({"literal":s})));
    commands.extend([
        json!("-c"),
        json!("{source}"),
        json!("-o"),
        json!("{object}"),
    ]);
    let specs:Vec<_>=variants.iter().map(|v|json!({"id":v.id,"language":"c","sources":[format!("{}.c",v.id)],"commands":[commands]})).collect();
    let codecs = if args.codec.is_empty() {
        vec!["gzip-9".to_owned(), "xz-6".to_owned()]
    } else {
        args.codec.clone()
    };
    let manifest = json!({"project_root":".","target":target,"inputs":inputs,"tools":{"cc":{"executable":clang},"python":{"executable":"python3"}},
        "components":[{"id":"program","contract":contract,"variants":specs}],"build_profiles":[{"id":"size"}],
        "link_profiles":[{"id":"hosted","argv":["{cc}","{objects}","-s","-Wl,--build-id=none","-o","{binary}"]}],
        "verify":["{python}","{root}/verify.py","{binary}"],"verify_final":["{python}","{root}/verify.py","{binary}"],
        "baseline":{"build":"size","link":"hosted","order":["program"],"variants":{"program":"raw"}},"codecs":codecs});
    new_json(&directory.join("manifest.json"), &manifest)
}

fn dispatch(command: Command) -> Result<(Value, bool)> {
    match command {
        Command::Build(args) | Command::Run(args) => unreachable_build(args),
        Command::Reproduce(args) => {
            let mut opts = native_options(&args.budget)?;
            opts.verify = args.verify;
            let report = native::reproduce(&args.recipe, &args.out, &opts)?;
            Ok((report, true))
        }
        Command::Notation(args) => {
            let original = source(&args.source)?;
            let opts = notation::NotationOptions {
                language: args.language.clone(),
                target: args.target,
                compact: args.compact,
                token_contract: args.token_contract,
                max_variants: args.max_variants,
            };
            let variants = notation::generate_variants(&original, &opts)?;
            if let Some(p) = &args.portfolio {
                portfolio(
                    p,
                    &variants,
                    match args.language.as_str() {
                        "cpp" => "cpp",
                        "rust" => "rs",
                        "python" => "py",
                        _ => "c",
                    },
                )?;
            }
            if let Some(out) = &args.output {
                let chosen = variants
                    .iter()
                    .find(|v| v.id == args.variant)
                    .or_else(|| {
                        if variants.len() == 1 && variants[0].id == "raw" {
                            variants.first()
                        } else {
                            None
                        }
                    })
                    .context("requested source variant unavailable")?;
                new_file(out, &chosen.data)?;
            }
            Ok((
                json!({"variants":variants,"source_sha256":nvcompact::sha256(&original)}),
                true,
            ))
        }
        Command::RewriteC(args) => {
            let original = source(&args.source)?;
            let opts = cflow::CFlowOptions {
                clang: args.clang.clone(),
                standard: args.standard.clone(),
                compiler_args: args.compiler_args.clone(),
                source_path: Some(args.source.canonicalize()?),
                token_contract: args.token_contract.clone(),
                max_variants: args.max_variants,
                max_passes: args.max_passes,
                ..Default::default()
            };
            let variants = cflow::generate_variants(&original, &opts)?;
            if let Some(p) = &args.portfolio {
                portfolio(p, &variants, "c")?;
            }
            if args.run_manifest {
                export_rewrite(
                    &args,
                    &variants,
                    args.portfolio
                        .as_ref()
                        .context("--run-manifest needs --portfolio")?,
                )?;
            }
            if let Some(out) = &args.output {
                let name = args.variant.as_deref().unwrap_or(
                    if variants.iter().any(|v| v.id == "c-all") {
                        "c-all"
                    } else {
                        "raw"
                    },
                );
                new_file(
                    out,
                    &variants
                        .iter()
                        .find(|v| v.id == name)
                        .context("requested C variant unavailable")?
                        .data,
                )?;
            }
            Ok((
                json!({"variants":variants,"source_sha256":nvcompact::sha256(&original)}),
                true,
            ))
        }
        Command::Envelope(args) => {
            let opts = envelope::EnvelopeOptions {
                thorough: args.thorough,
                notation: !args.no_notation,
                jobs: args.jobs,
                artifact: args.artifact,
            };
            let mut report = envelope::run(&args.manifest, &args.output, &opts)?;
            if args.uci {
                envelope_uci(
                    &mut report,
                    &args.output,
                    &uci_config(args.uci_config.as_deref())?,
                )?;
            }
            let success = !args.uci || !report["accepted"].is_null();
            Ok((report, success))
        }
        Command::Replay(args) => {
            let report = envelope::reproduce(&args.summary, &args.output, &args.selection)?;
            if args.uci {
                let p = args.output.join("reproduced");
                let result = protocol(
                    &p,
                    &uci_config(args.uci_config.as_deref())?,
                    &args.output.join("uci.json"),
                )?;
                let good = result["verdict"] == "pass";
                Ok((json!({"reproduction":report,"uci":result}), good))
            } else {
                Ok((report, true))
            }
        }
        Command::Uci(args) => {
            let mut config = uci_config(args.config.as_deref())?;
            if let Some(v) = args.clock_ms {
                config.clock_ms = v;
            }
            if let Some(v) = args.increment_ms {
                config.increment_ms = v;
            }
            if let Some(v) = args.search_seconds {
                config.search_seconds = v;
            }
            if let Some(v) = args.max_seconds {
                config.max_seconds = v;
            }
            if let Some(v) = args.memory_bytes {
                config.memory_bytes = v;
            }
            config.quick |= args.quick;
            config.extensions |= args.extensions;
            if args.configure_engine_options {
                config.preserve_engine_options = false;
            }
            let result = protocol(&args.binary, &config, &args.report)?;
            let good = result["verdict"] == "pass";
            Ok((result, good))
        }
        Command::Resource { command } => match command {
            ResourceCommand::Plan {
                specification,
                output,
            } => {
                let result = resource::create_plan(&specification)?;
                new_json(&output, &result)?;
                Ok((result, true))
            }
            ResourceCommand::Run {
                plan,
                output,
                start,
            } => {
                let result = resource::execute_plan(&plan, &output, start)?;
                let good = result["status"] == "pass";
                Ok((result, good))
            }
        },
        Command::Engines(args) => {
            ensure!(!args.output.exists(), "campaign output must be new");
            fs::create_dir_all(&args.output)?;
            let mut manifests = fs::read_dir(&args.manifests)?
                .map(|r| r.map(|e| e.path()))
                .collect::<std::io::Result<Vec<_>>>()?;
            manifests.retain(|p| p.extension().is_some_and(|s| s == "json"));
            manifests.sort();
            let mut rows = Vec::new();
            for path in manifests {
                let manifest = read_json(&path)?;
                let name = manifest["name"].as_str().context("manifest name missing")?;
                if !args.only.is_empty() && !args.only.iter().any(|s| s == name) {
                    continue;
                }
                ensure!(
                    Path::new(name).components().count() == 1 && name != "..",
                    "invalid engine name"
                );
                ensure!(
                    regex::Regex::new(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")?.is_match(name),
                    "engine name must be one ordinary identifier"
                );
                let output = args.output.join(name);
                let opts = envelope::EnvelopeOptions {
                    thorough: args.thorough,
                    notation: !args.no_notation,
                    jobs: args.jobs,
                    artifact: Some(args.artifact_root.join(name)),
                };
                let result = (|| -> Result<Value> {
                    let mut r = envelope::run(&path, &output, &opts)?;
                    if args.uci {
                        envelope_uci(&mut r, &output, &uci_config(args.uci_config.as_deref())?)?;
                    }
                    Ok(r)
                })();
                rows.push(match result{Ok(r)=>json!({"name":name,"status":"measured","original_bytes":r["original_bytes"],"winner":r["winner"],"no_size_regression":r["no_size_regression"],"uci":r["uci"],"accepted":r["accepted"]}),Err(e)=>json!({"name":name,"status":"failed","error":format!("{e:#}")})});
                write_json(&args.output.join("results.json"), &rows)?;
            }
            ensure!(!rows.is_empty(), "no matching external manifests");
            let good = rows
                .iter()
                .all(|r| r["status"] == "measured" && (!args.uci || !r["accepted"].is_null()));
            Ok((json!({"results":rows}), good))
        }
        Command::Doctor { json: _ } => Ok((
            json!({"version":env!("CARGO_PKG_VERSION"),"runtime":"Rust","python_backend":false,"platform":std::env::consts::OS,"architecture":std::env::consts::ARCH,"codecs":nvcompact::codec::library_versions(),"resource_probe":resource::probe_resources(),"targets_started":false}),
            true,
        )),
    }
}
fn unreachable_build(_: BuildArgs) -> Result<(Value, bool)> {
    bail!("internal build dispatch")
}
fn main() {
    let cli = Cli::parse();
    let result = (|| -> Result<(Value, bool)> {
        process::install_signal_handlers()?;
        match cli.command {
            Command::Build(args) => build(args, false),
            Command::Run(args) => build(args, true),
            other => dispatch(other),
        }
    })();
    let code = match result {
        Ok((value, success)) => {
            let mut out = std::io::stdout().lock();
            let written = serde_json::to_writer_pretty(&mut out, &value)
                .and_then(|_| out.write_all(b"\n").map_err(serde_json::Error::io));
            if written.is_err() {
                2
            } else if success {
                0
            } else {
                2
            }
        }
        Err(e) => {
            eprintln!("nvcompact: {e:#}");
            2
        }
    };
    std::process::exit(code);
}
fn build(args: BuildArgs, packing: bool) -> Result<(Value, bool)> {
    let mut options = native_options(&args.budget)?;
    options.packing = packing;
    options.verify = packing || args.verify;
    options.jobs = args.jobs;
    options.max_candidates = args.max_candidates;
    options.profiles = args.profile;
    options.link_profiles = args.link_profile;
    options.max_bytes = args.max_bytes;
    let report = native::run(&args.manifest, &args.out, &options)?;
    Ok((report, true))
}
