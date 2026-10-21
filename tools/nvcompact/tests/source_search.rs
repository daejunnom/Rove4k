//! Whole-submission integration checks with a small owned C program. Neither
//! the Python bootstrap nor its compiled C executable is started by these tests.
use nvcompact::{
    attempts,
    cflow::CFlowOptions,
    codec::{self, Recipe},
    csource::{self, CSourceOptions},
    envelope, process, sha256,
    source_payload::PayloadAdapter,
    source_search, write_json,
};
use serde_json::{json, Value};
use std::{fs, path::Path};

const SOURCE: &[u8] = b"int k=11;int f(int a){return a*a+a+k;}int g(int z){return z*z+z+k;}int main(void){return f(7)!=g(7);}\n";

fn tools() -> Option<(String, String)> {
    let clang = std::env::var("NVCOMPACT_CLANG").unwrap_or_else(|_| "clang".into());
    let compiler = std::env::var("CC").unwrap_or_else(|_| "cc".into());
    if process::resolve_tool(&clang).is_err() || process::resolve_tool(&compiler).is_err() {
        eprintln!("source-search integration not executed: provide NVCOMPACT_CLANG and CC");
        return None;
    }
    Some((clang, compiler))
}

fn compiler_argv(compiler: &str) -> Vec<String> {
    [
        compiler,
        "-x",
        "c",
        "-",
        "-std=c11",
        "-Os",
        "-s",
        "-fno-ident",
        "-Wl,--build-id=none",
        "-o",
        "{output}",
    ]
    .into_iter()
    .map(str::to_owned)
    .collect()
}

fn compression() -> Recipe {
    serde_json::from_value(
        json!({"format":"alone","preset":2147483657u32,"dict_size":4096,"lc":0,"lp":0,"pb":0}),
    )
    .unwrap()
}

fn payload() -> (Vec<u8>, Value) {
    // The selected literal is observed only as the compiler's stdin. Its bytes
    // are never inspected, hashed or used to select other bootstrap behavior.
    let prefix = b"import subprocess\np=subprocess.Popen(['cc','-x','c','-','-std=c11','-Os','-s','-fno-ident','-Wl,--build-id=none','-o','x'],stdin=subprocess.PIPE)\np.communicate(";
    let literal = [b"br'''".as_slice(), SOURCE, b"'''"].concat();
    let suffix = b")\nassert p.returncode==0\n";
    let payload = [prefix.as_slice(), &literal, suffix.as_slice()].concat();
    let embedding = json!({"kind":"python-bytes","start":prefix.len(),"end":prefix.len()+literal.len(),"sha256":sha256(&literal)});
    (payload, embedding)
}

fn options(clang: &str, embedding: Value) -> source_search::SourceSearchOptions {
    source_search::SourceSearchOptions {
        candidates: CSourceOptions {
            frontend: CFlowOptions {
                clang: clang.into(),
                token_contract: "no-token-observation".into(),
                ..Default::default()
            },
            max_candidates: 32,
            max_name_groups: 8,
            names_per_group: 4,
            integer_literals: false,
            character_literals: false,
            ..Default::default()
        },
        embedding: Some(embedding),
        embedding_contract: "compile-input-only".into(),
        conditions: false,
        max_rounds: 1,
        max_evaluations: 128,
        max_combinations: 16384,
        max_seconds: 60.0,
        max_retained_source_bytes: 64 << 20,
        compile_limits: process::Limits {
            seconds: 10.0,
            cpu_seconds: 15,
            output_bytes: 65536,
            ..Default::default()
        },
    }
}

fn fixture(
    directory: &Path,
    search: Option<&source_search::SourceSearchOptions>,
    compiler: &str,
) -> std::path::PathBuf {
    fs::create_dir_all(directory).unwrap();
    let (payload, _) = payload();
    let codec = compression();
    let header = b"#!/bin/sh\ntail -n+3 \"$0\"|lzma -dc|python3\n";
    let submitted = [
        header.as_slice(),
        &codec::compress(&payload, &codec).unwrap(),
    ]
    .concat();
    fs::write(directory.join("original"), &submitted).unwrap();
    let mut manifest = json!({"name":"owned-source-search","artifact":"original","category":"4k","sha256":sha256(&submitted),
        "payload_sha256":sha256(&payload),"language":"python","notation":{"token_contract":"opaque"},
        "compile_argv":compiler_argv(compiler),"envelope":{"header_bytes":header.len(),"header_sha256":sha256(header),
        "decoder":"lzma -dc","payload_codec":codec}});
    if let Some(search) = search {
        manifest["source_search"] = serde_json::to_value(search).unwrap();
    }
    let path = directory.join("manifest.json");
    write_json(&path, &manifest).unwrap();
    path
}

#[test]
fn whole_file_objective_retains_equal_length_name_improvements_and_replays() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    let directory = tempfile::tempdir().unwrap();
    let (original_payload, embedding) = payload();
    let opts = options(&clang, embedding);
    let adapter = PayloadAdapter::new(&original_payload, opts.embedding.as_ref()).unwrap();
    let variants = csource::generate_variants(SOURCE, &opts.candidates).unwrap();
    // This is a measured counterexample to source-length pruning. Both helper
    // functions already use one-letter bindings. Reusing a spelling across
    // their independent scopes improves real LZMA context/repetition.
    let improving = variants
        .iter()
        .skip(1)
        .find(|variant| {
            variant.data.len() == SOURCE.len()
                && adapter
                    .render(&variant.data)
                    .unwrap()
                    .iter()
                    .any(|rendered| {
                        let same_style = adapter.render_style(SOURCE, &rendered.style).unwrap();
                        codec::compress(&rendered.data, &compression())
                            .unwrap()
                            .len()
                            < codec::compress(&same_style.data, &compression())
                                .unwrap()
                                .len()
                    })
        })
        .expect("fixture must exercise a real compressed-byte gain with tied source length");
    csource::verify_variant(SOURCE, improving, &opts.candidates).unwrap();

    let legacy = fixture(&directory.path().join("legacy-input"), None, &compiler);
    let current = fixture(
        &directory.path().join("current-input"),
        Some(&opts),
        &compiler,
    );
    let settings = envelope::EnvelopeOptions {
        jobs: 1,
        ..Default::default()
    };
    let legacy_out = directory.path().join("legacy");
    let current_out = directory.path().join("current");
    let old = envelope::run(&legacy, &legacy_out, &settings).unwrap();
    let new = envelope::run(&current, &current_out, &settings).unwrap();
    assert!(new["winner"]["bytes"].as_u64().unwrap() <= old["winner"]["bytes"].as_u64().unwrap());
    assert_eq!(new["no_size_regression"], true);
    assert!(new["accepted"].is_null());
    assert_eq!(new["uci"]["status"], "not_run");
    let candidates: Vec<Value> =
        serde_json::from_slice(&fs::read(current_out.join("candidates.json")).unwrap()).unwrap();
    assert!(candidates
        .iter()
        .any(|c| c["id"] == "identity" && c["sha256"] == new["original_sha256"]));
    assert!(candidates
        .iter()
        .any(|c| c["variant"] == new["source_search"]["variant"]));
    let recipe = &new["source_search"]["recipe"];
    let retained = current_out.join("source-search/source-search/attempts");
    let comparison = attempts::compare(&[retained.clone()]).unwrap();
    assert_eq!(comparison["groups"][0]["cross_run_comparable"], true);
    assert_eq!(
        comparison["groups"][0]["context"]["cost_objective"]["kind"],
        "inspected-envelope-fixed-codec-v1"
    );
    assert_eq!(
        comparison["groups"][0]["context"]["cost_objective"]["codec"],
        serde_json::to_value(compression()).unwrap()
    );
    let measured_rows = comparison["groups"][0]["rows"].as_array().unwrap();
    assert!(measured_rows
        .iter()
        .any(|row| row["semantic_status"] == "recorded-verified"
            && row["selected_in_recorded_run"] == true));
    assert!(measured_rows
        .iter()
        .any(|row| row["semantic_status"] == "not-checked"
            && row["selected_in_recorded_run"] == false));
    for row in measured_rows
        .iter()
        .filter(|row| !row["base_source_sha256"].is_null())
    {
        let basis = row["base_source_sha256"].as_str().unwrap();
        assert_eq!(
            sha256(&fs::read(retained.join("objects").join(basis)).unwrap()),
            basis
        );
    }
    assert!(!recipe["steps"].as_array().unwrap().is_empty());
    let restored = source_search::replay(
        &original_payload,
        recipe,
        &compiler_argv(&compiler),
        &directory.path().join("source-replay"),
    )
    .unwrap();
    assert_eq!(
        sha256(&restored),
        recipe["final"]["payload_sha256"].as_str().unwrap()
    );
    let replay = envelope::reproduce(
        &current_out.join("summary.json"),
        &directory.path().join("envelope-replay"),
        "smallest",
    )
    .unwrap();
    assert_eq!(replay["sha256"], new["winner"]["sha256"]);
    assert_eq!(
        fs::read(directory.path().join("envelope-replay/reproduced")).unwrap(),
        fs::read(current_out.join("smallest")).unwrap()
    );
    assert!(
        !directory.path().join("current/x").exists(),
        "the bootstrap must never execute"
    );
}

#[test]
fn losing_singles_remain_composable_and_fresh_cost_cannot_use_measurement_cache() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    const INPUT: &[u8] = b"int f(int alpha){return alpha+1;}int g(int beta){return beta+2;}int main(void){return f(1)!=g(0);}\n";
    struct NonMonotoneCost {
        fresh_calls: usize,
        fail_fresh: bool,
    }
    impl source_search::CompleteFileObjective for NonMonotoneCost {
        fn measure(&mut self, data: &[u8]) -> anyhow::Result<usize> {
            let source = std::str::from_utf8(data)?;
            Ok(match (source.contains("alpha"), source.contains("beta")) {
                (true, true) => 100,
                (false, false) => 90,
                _ => 101,
            })
        }
        fn fresh_measure(&mut self, data: &[u8]) -> anyhow::Result<usize> {
            self.fresh_calls += 1;
            Ok(self.measure(data)? + usize::from(self.fail_fresh))
        }
    }
    let directory = tempfile::tempdir().unwrap();
    let mut opts = options(&clang, Value::Null);
    opts.embedding = None;
    opts.embedding_contract = "opaque".into();
    opts.candidates.max_candidates = 3;
    opts.candidates.max_name_groups = 2;
    opts.candidates.names_per_group = 1;
    opts.max_combinations = 8;
    opts.max_evaluations = 16;
    let compile = compiler_argv(&compiler);
    let mut objective = NonMonotoneCost {
        fresh_calls: 0,
        fail_fresh: false,
    };
    let searched = source_search::search_with_objective(
        INPUT,
        &opts,
        &compile,
        &directory.path().join("combinations"),
        None,
        &mut objective,
    )
    .unwrap();
    assert_eq!(searched.report["selected_whole_file_bytes"], 90);
    assert_eq!(objective.fresh_calls, 1);
    let space = &searched.report["coverage"]["basis_spaces"][0];
    assert_eq!(space["generated_choices"], 2);
    assert_eq!(space["nontrivial_subsets"], "1");
    assert_eq!(space["systematic_subsets_attempted"], 1);
    assert_eq!(space["exhausted"], true);
    assert_eq!(space["all_declared_costs_evaluated"], true);
    let records = searched.report["records"].as_array().unwrap();
    assert_eq!(
        records
            .iter()
            .filter(|r| r["stage"] == "complete-file-cost" && r["whole_file_bytes"] == 101)
            .count(),
        2
    );
    assert!(records
        .iter()
        .any(|r| r["stage"] == "composition-admitted" && r["phase"] == "systematic"));
    assert_eq!(
        source_search::replay(
            INPUT,
            &searched.recipe,
            &compile,
            &directory.path().join("replay")
        )
        .unwrap(),
        searched.data
    );

    let out = directory.path().join("fresh-failure");
    let mut changed = NonMonotoneCost {
        fresh_calls: 0,
        fail_fresh: true,
    };
    let error =
        source_search::search_with_objective(INPUT, &opts, &compile, &out, None, &mut changed)
            .unwrap_err();
    assert!(format!("{error:#}").contains("final complete-file cost is not reproducible"));
    assert_eq!(changed.fresh_calls, 1);
    let compared = attempts::compare(&[out.join("source-search/attempts")]).unwrap();
    assert_eq!(compared["runs"][0]["status"], "failed");
}

#[test]
fn retained_attempts_survive_budget_stops_and_failed_costs() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    let directory = tempfile::tempdir().unwrap();
    let mut opts = options(&clang, Value::Null);
    opts.embedding = None;
    opts.embedding_contract = "opaque".into();
    opts.max_evaluations = 2;
    let compile = compiler_argv(&compiler);
    let mut measure = |data: &[u8]| -> anyhow::Result<usize> {
        Ok(40 + codec::compress(data, &compression())?.len())
    };
    let out = directory.path().join("evaluation-stop");
    let result = source_search::search(SOURCE, &opts, &compile, &out, &mut measure).unwrap();
    assert_eq!(result.data, SOURCE);
    assert_eq!(
        result.report["exhaustion_reason"],
        "complete-file-evaluation-budget"
    );
    let comparison = attempts::compare(&[out.join("source-search/attempts")]).unwrap();
    assert!(comparison["groups"][0]["rows"]
        .as_array()
        .unwrap()
        .iter()
        .any(|row| row["outcome"] == "unmeasured" && row["selected_in_recorded_run"] == false));

    opts.max_evaluations = 128;
    opts.max_retained_source_bytes = 0;
    let out = directory.path().join("retention-stop");
    let result = source_search::search(SOURCE, &opts, &compile, &out, &mut measure).unwrap();
    assert_eq!(result.data, SOURCE);
    assert_eq!(
        result.report["exhaustion_reason"],
        "retained-source-byte-budget"
    );
    assert_eq!(
        result.report["retention_stop"]["unretained_candidate"],
        true
    );
    assert_eq!(
        result.report["attempts"]["retained_candidate_source_bytes"],
        0
    );
    attempts::compare(&[out.join("source-search/attempts")]).unwrap();

    opts.max_retained_source_bytes = 64 << 20;
    let out = directory.path().join("codec-failure");
    let mut calls = 0;
    let error = source_search::search(SOURCE, &opts, &compile, &out, &mut |data| {
        calls += 1;
        if calls > 1 {
            anyhow::bail!("owned failing complete-file measurement");
        }
        measure(data)
    })
    .unwrap_err();
    assert!(format!("{error:#}").contains("owned failing complete-file measurement"));
    let comparison = attempts::compare(&[out.join("source-search/attempts")]).unwrap();
    assert_eq!(comparison["runs"][0]["status"], "failed");
    assert!(comparison["groups"][0]["rows"]
        .as_array()
        .unwrap()
        .iter()
        .any(|row| row["outcome"] == "cost-failed" && row["selected_in_recorded_run"] == false));
    assert!(out.join("source-search/failed-report.json").is_file());

    let out = directory.path().join("baseline-compile-failure");
    let mut bad_compile = compile.clone();
    bad_compile.push("-nvcompact-owned-invalid-option".into());
    let error = source_search::search(SOURCE, &opts, &bad_compile, &out, &mut measure).unwrap_err();
    assert!(format!("{error:#}").contains("declared source compiler did not complete successfully"));
    let comparison = attempts::compare(&[out.join("source-search/attempts")]).unwrap();
    assert_eq!(comparison["runs"][0]["status"], "failed");
    assert_eq!(comparison["groups"][0]["cross_run_comparable"], false);

    let out = directory.path().join("preserve-both-errors");
    let mut calls = 0;
    let error = source_search::search(SOURCE, &opts, &compile, &out, &mut |data| {
        calls += 1;
        if calls > 1 {
            fs::write(out.join("source-search/attempts/context.json"), b"{}").unwrap();
            anyhow::bail!("owned original cost failure before archive sealing");
        }
        measure(data)
    })
    .unwrap_err();
    let error = format!("{error:#}");
    assert!(error.contains("owned original cost failure before archive sealing"));
    assert!(error.contains("attempt context hash mismatch"));
    let receipt: Value =
        serde_json::from_slice(&fs::read(out.join("source-search/failed-report.json")).unwrap())
            .unwrap();
    assert!(receipt["search_error"]
        .as_str()
        .unwrap()
        .contains("owned original cost failure"));
    assert!(receipt["evidence_error"]
        .as_str()
        .unwrap()
        .contains("context hash mismatch"));
}

#[test]
fn search_replay_rejects_changed_contract_tools_and_recipe_edits() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    let directory = tempfile::tempdir().unwrap();
    let (payload, embedding) = payload();
    let opts = options(&clang, embedding);
    let compile = compiler_argv(&compiler);
    let prefix = b"#!/bin/sh\ntail -n+3 \"$0\"|lzma -dc|python3\n";
    let mut measure = |data: &[u8]| -> anyhow::Result<usize> {
        Ok(prefix.len() + codec::compress(data, &compression())?.len())
    };
    let searched = source_search::search(
        &payload,
        &opts,
        &compile,
        &directory.path().join("search"),
        &mut measure,
    )
    .unwrap();
    assert!(measure(&searched.data).unwrap() <= measure(&payload).unwrap());
    let mut invalid = opts.clone();
    invalid.embedding_contract = "opaque".into();
    let error = source_search::search(
        &payload,
        &invalid,
        &compile,
        &directory.path().join("invalid-contract"),
        &mut measure,
    )
    .unwrap_err();
    assert!(format!("{error:#}").contains("compile-input-only"));
    let mut invalid = opts.clone();
    invalid.max_evaluations = 1;
    invalid.candidates.max_candidates = 0;
    let error = source_search::search(
        &payload,
        &invalid,
        &compile,
        &directory.path().join("invalid-nested-bounds"),
        &mut measure,
    )
    .unwrap_err();
    assert!(format!("{error:#}").contains("max_candidates"));
    let mut altered_compile = compile.clone();
    altered_compile.push("-fwrapv".into());
    let error = source_search::replay(
        &payload,
        &searched.recipe,
        &altered_compile,
        &directory.path().join("changed-command"),
    )
    .unwrap_err();
    assert!(format!("{error:#}").to_ascii_lowercase().contains("compil"));
    for key in ["compiler", "frontend"] {
        let mut bad = searched.recipe.clone();
        bad[key]["sha256"] = json!("0".repeat(64));
        let error = source_search::replay(
            &payload,
            &bad,
            &compile,
            &directory.path().join(format!("changed-{key}")),
        )
        .unwrap_err();
        assert!(
            format!("{error:#}").to_ascii_lowercase().contains(key),
            "wrong rejection boundary: {error:#}"
        );
    }
    let mut bad = searched.recipe.clone();
    let first = bad["steps"]
        .as_array_mut()
        .unwrap()
        .first_mut()
        .expect("spelling change required");
    assert_eq!(first["kind"], "c-source");
    first["variant"]["audit"][0]["edits"][0]["after"] = json!("INVALID_REPLAY_TOKEN");
    let error = source_search::replay(
        &payload,
        &bad,
        &compile,
        &directory.path().join("changed-edit"),
    )
    .unwrap_err();
    assert!(
        format!("{error:#}").to_ascii_lowercase().contains("edit")
            || format!("{error:#}").contains("reconstruct"),
        "wrong rejection boundary: {error:#}"
    );
}

#[test]
fn frontend_output_budget_preserves_verified_input_without_hiding_source_errors() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    let directory = tempfile::tempdir().unwrap();
    // A small owned source can have a much larger typed JSON AST. The late
    // conditional error also exercises the mandatory syntax-only recheck:
    // filling the AST output budget must never hide an ordinary source error.
    let mut source = String::new();
    for index in 0..400 {
        source.push_str(&format!("int declared_global_{index};\n"));
    }
    source.push_str("#ifdef NVCOMPACT_FRONTEND_REJECT\n#error NVCompact fixture frontend rejection\n#endif\nint main(void){return 0;}\n");
    let source = source.into_bytes();
    let mut opts = options(&clang, Value::Null);
    opts.embedding = None;
    opts.embedding_contract = "opaque".into();
    opts.candidates.frontend.ast_bytes = 65536;
    let compile = compiler_argv(&compiler);
    let header = b"#!/bin/sh\ntail -n+3 \"$0\"|xz -d|cc -x c - -o x\n";
    let submitted = [
        header.as_slice(),
        &codec::compress(&source, &compression()).unwrap(),
    ]
    .concat();
    let make_fixture = |name: &str, search: bool| {
        let input = directory.path().join(name);
        fs::create_dir(&input).unwrap();
        fs::write(input.join("original"), &submitted).unwrap();
        let mut manifest = json!({"name":"owned-frontend-capacity","artifact":"original","category":"4k",
            "sha256":sha256(&submitted),"payload_sha256":sha256(&source),"language":"c",
            "notation":{"token_contract":"opaque"},"compile_argv":compile,
            "envelope":{"header_bytes":header.len(),"header_sha256":sha256(header),
                "decoder":"xz -d","payload_codec":compression()}});
        if search {
            manifest["source_search"] = serde_json::to_value(&opts).unwrap();
        }
        let path = input.join("manifest.json");
        write_json(&path, &manifest).unwrap();
        path
    };
    let envelope_options = envelope::EnvelopeOptions {
        jobs: 1,
        ..Default::default()
    };
    let old = envelope::run(
        &make_fixture("legacy-input", false),
        &directory.path().join("legacy"),
        &envelope_options,
    )
    .unwrap();
    let current_out = directory.path().join("current");
    let new = envelope::run(
        &make_fixture("current-input", true),
        &current_out,
        &envelope_options,
    )
    .unwrap();
    assert!(new["winner"]["bytes"].as_u64().unwrap() <= old["winner"]["bytes"].as_u64().unwrap());
    assert_eq!(new["winner"]["variant"], "raw");
    assert_eq!(new["source_search"]["report"]["status"], "budget-exhausted");
    assert_eq!(
        new["source_search"]["report"]["exhaustion_reason"],
        "frontend-output-budget"
    );
    let recipe = &new["source_search"]["recipe"];
    assert!(recipe["steps"].as_array().unwrap().is_empty());
    assert_eq!(recipe["final"]["source_sha256"], sha256(&source));
    let report: Value = serde_json::from_slice(
        &fs::read(
            current_out.join(
                new["source_search"]["report"]["detail"]["path"]
                    .as_str()
                    .unwrap(),
            ),
        )
        .unwrap(),
    )
    .unwrap();
    let exhausted = report["records"]
        .as_array()
        .unwrap()
        .iter()
        .find(|record| record["stage"] == "frontend-capacity-stop")
        .expect("frontend capacity exhaustion must retain a receipt");
    assert_eq!(exhausted["frontend_proof"], "incomplete");
    assert_eq!(exhausted["syntax_recheck"], "passed");
    assert_eq!(exhausted["truncated_output_accepted"], false);
    let replayed = source_search::replay(
        &source,
        recipe,
        &compile,
        &directory.path().join("capacity-replay"),
    )
    .unwrap();
    assert_eq!(replayed, source);

    let mut measure = |data: &[u8]| -> anyhow::Result<usize> {
        Ok(header.len() + codec::compress(data, &compression())?.len())
    };
    let mut invalid_frontend = opts.clone();
    invalid_frontend
        .candidates
        .frontend
        .compiler_args
        .push("-DNVCOMPACT_FRONTEND_REJECT=1".into());
    let error = source_search::search(
        &source,
        &invalid_frontend,
        &compile,
        &directory.path().join("frontend-error"),
        &mut measure,
    )
    .unwrap_err();
    assert!(
        format!("{error:#}").contains("NVCompact fixture frontend rejection"),
        "frontend syntax error must remain fatal even after output exhaustion: {error:#}"
    );
    let error = source_search::search(
        b"int main( {\n",
        &opts,
        &compile,
        &directory.path().join("native-baseline-error"),
        &mut measure,
    )
    .unwrap_err();
    assert!(
        format!("{error:#}").contains("declared source compiler did not complete successfully"),
        "native baseline failure must not be treated as optional exploration: {error:#}"
    );
}
