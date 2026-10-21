//! End-to-end advisory behavior on small owned programs. No external engine runs.
use nvcompact::{
    process::{self, Limits},
    sha256,
};
use serde_json::Value;
use std::{fs, path::Path};

fn frontend() -> Option<String> {
    let name = std::env::var("NVCOMPACT_CLANG").unwrap_or_else(|_| "clang".into());
    if process::resolve_tool(&name).is_err() {
        eprintln!("advice integration not executed: set NVCOMPACT_CLANG");
        None
    } else {
        Some(name)
    }
}

fn run(argv: &[String], cwd: &Path) -> process::Output {
    process::run(
        argv,
        b"",
        cwd,
        &Limits {
            seconds: 60.0,
            cpu_seconds: 60,
            memory_bytes: 2 << 30,
            output_bytes: 4 << 20,
            file_bytes: 8 << 20,
        },
    )
    .unwrap()
}

fn cli(arguments: &[String], cwd: &Path) -> process::Output {
    let mut argv = vec![env!("CARGO_BIN_EXE_nvcompact").to_owned()];
    argv.extend_from_slice(arguments);
    run(&argv, cwd)
}

#[test]
fn unsupported_languages_and_language_specific_features_fail_before_frontend_or_writes() {
    let directory = tempfile::tempdir().unwrap();
    let root = directory.path();
    for language in ["python", "javascript", "unknown"] {
        let args = [
            "advise-source",
            "absent.input",
            "--language",
            language,
            "--clang",
            "/absent/compiler",
            "--report",
            "unexpected.json",
        ]
        .map(str::to_owned);
        let result = cli(&args, root);
        assert!(!result.success());
        assert!(String::from_utf8_lossy(&result.stderr).contains("unsupported advisory language"));
        assert!(!root.join("unexpected.json").exists());
    }
    for language in ["cpp", "rust"] {
        for option in ["--profile", "--instrument"] {
            let args = [
                "advise-source",
                "absent.input",
                "--language",
                language,
                option,
                "unexpected",
            ]
            .map(str::to_owned);
            let result = cli(&args, root);
            assert!(!result.success());
            assert!(String::from_utf8_lossy(&result.stderr).contains("static-only"));
            assert!(!root.join("unexpected").exists());
        }
    }
}

#[test]
fn separate_instrumentation_preserves_owned_results_and_bounds_multithreaded_samples() {
    let Some(clang) = frontend() else {
        return;
    };
    let cc = std::env::var("CC").unwrap_or_else(|_| "cc".into());
    if process::resolve_tool(&cc).is_err() {
        eprintln!("advice native integration not executed: set CC");
        return;
    }
    let directory = tempfile::tempdir().unwrap();
    let root = directory.path();
    let source=br#"#include <pthread.h>
#include <stdio.h>
static void *worker(void *arg) {
    unsigned input=(unsigned)(unsigned long)arg;
    int sum=0;
    for(unsigned j=0;j<64;++j) {
        int flag=(input+j)&1;
        if(flag==1) sum+=1; else sum+=2;
    }
    return (void*)(unsigned long)sum;
}
int main(void) {
    pthread_t threads[4]; unsigned sum=0;
    for(unsigned j=0;j<4;++j) if(pthread_create(&threads[j],0,worker,(void*)(unsigned long)j)) return 2;
    for(unsigned j=0;j<4;++j) { void *result; if(pthread_join(threads[j],&result)) return 3; sum+=(unsigned)(unsigned long)result; }
    printf("%u\n",sum); return sum!=384;
}
"#;
    fs::write(root.join("program.c"), source).unwrap();
    let args: Vec<String> = [
        "advise-c",
        "program.c",
        "--clang",
        &clang,
        "--instrument",
        "diagnostic",
        "--max-samples",
        "37",
    ]
    .into_iter()
    .map(str::to_owned)
    .collect();
    let exported = cli(&args, root);
    exported.check("export diagnostic source").unwrap();
    let report: Value = serde_json::from_slice(&exported.stdout).unwrap();
    assert_eq!(report["source_sha256"], sha256(source));
    assert_eq!(report["instrumentation"]["max_samples_per_process"], 37);
    assert!(
        report["instrumentation"]["instrumented_sites"]
            .as_u64()
            .unwrap()
            > 0
    );
    for (input, output) in [
        ("program.c", "original"),
        ("diagnostic/instrumented.c", "diagnostic/probe"),
    ] {
        let built = run(
            &[
                cc.clone(),
                "-std=c11".into(),
                "-pthread".into(),
                input.into(),
                "-o".into(),
                output.into(),
            ],
            root,
        );
        built.check("compile owned observation fixture").unwrap();
    }
    let original = run(
        &[root.join("original").to_string_lossy().into_owned()],
        root,
    );
    let sampled = run(
        &[root.join("diagnostic/probe").to_string_lossy().into_owned()],
        root,
    );
    original.check("owned original").unwrap();
    sampled.check("owned diagnostic").unwrap();
    assert_eq!(original.stdout, b"384\n");
    assert_eq!(sampled.stdout, original.stdout);
    assert_eq!(
        String::from_utf8_lossy(&sampled.stderr)
            .lines()
            .filter(|l| l.starts_with("NVCOMPACT_ADVICE_V1\t"))
            .count(),
        37
    );
    fs::write(root.join("observations.log"), &sampled.stderr).unwrap();
    let imported = cli(
        &[
            "advise-c".into(),
            "program.c".into(),
            "--clang".into(),
            clang,
            "--profile".into(),
            "observations.log".into(),
        ],
        root,
    );
    imported
        .check("re-analyze and import the diagnostic samples")
        .unwrap();
    let observed: Value = serde_json::from_slice(&imported.stdout).unwrap();
    assert_eq!(
        observed["analysis_context_sha256"],
        report["analysis_context_sha256"]
    );
    assert_eq!(observed["observations"]["records"], 37);
    assert_eq!(observed["observations"]["static_ranges_changed"], false);
    assert_eq!(observed["observations"]["coverage_complete"], false);
    assert_eq!(observed["ranges"], report["ranges"]);
    assert_eq!(fs::read(root.join("program.c")).unwrap(), source);
    let again = cli(&args, root);
    assert!(again.check("existing diagnostic directory").is_err());
}

#[test]
fn final_artifact_inventory_reports_unaligned_mask_without_mutation() {
    let directory = tempfile::tempdir().unwrap();
    let root = directory.path();
    let bytes = [
        b"abc".as_slice(),
        &0x5555555555555555u64.to_le_bytes(),
        b"12345",
        &0x5555555555555555u64.to_le_bytes(),
    ]
    .concat();
    fs::write(root.join("submission"), &bytes).unwrap();
    let output = cli(
        &[
            "inspect-binary".into(),
            "submission".into(),
            "--word-bytes".into(),
            "8".into(),
        ],
        root,
    );
    output.check("final artifact advice").unwrap();
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["advisory_only"], true);
    let magic = report["findings"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["bytes_hex"] == "5555555555555555")
        .unwrap();
    assert_eq!(magic["offsets"], serde_json::json!([3, 16]));
    assert_eq!(magic["occurrences"], 2);
    assert!(magic["semantic_constant"].is_null());
    assert!(magic["estimated_savings_bytes"].is_null());
    assert_eq!(fs::read(root.join("submission")).unwrap(), bytes);
}
