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
        cleanup: false,
        scheduling: source_search::SchedulingPolicy::LegacyPriority,
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
    assert_eq!(
        new["source_search"]["report"]["observation_contract"]["declaration"],
        "caller-established precondition; not proven by masked AST/native identity"
    );
    assert_eq!(
        new["source_search"]["report"]["observation_contract"]["python_wrapper"],
        "source/token/location/traceback non-observation required"
    );
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
    let strategies = new["source_search_portfolio"].as_array().unwrap();
    assert_eq!(
        strategies
            .iter()
            .filter(|s| s["seed_role"] == "final-winner")
            .count(),
        2
    );
    assert_eq!(new["source_search_budget"]["strategies"], 2);
    assert_eq!(
        new["source_search_budget"]["retained_source_seeds"],
        strategies.len()
    );
    assert!(strategies
        .iter()
        .any(|s| s["strategy"] == "source-search" && s["scheduling"] == "legacy_priority"));
    assert!(strategies
        .iter()
        .any(|s| s["strategy"] == "source-search-portfolio"
            && s["scheduling"] == "interleaved_online"));
    assert_eq!(
        new["source_search_budget"]["maximum_complete_payload_evaluations"],
        256
    );
    let both_contexts = attempts::compare(&[
        retained.clone(),
        current_out.join("source-search-portfolio/source-search/attempts"),
    ])
    .unwrap();
    assert_eq!(both_contexts["groups"].as_array().unwrap().len(), 2);
    for (index, strategy) in strategies.iter().enumerate() {
        assert!(candidates
            .iter()
            .any(|c| c["variant"] == strategy["canonical_variant"]));
        if strategy["seed_role"] == "legacy-priority-seed" {
            let replayed = source_search::replay(
                &original_payload,
                &strategy["recipe"],
                &compiler_argv(&compiler),
                &directory
                    .path()
                    .join(format!("priority-seed-replay-{index}")),
            )
            .unwrap();
            assert_eq!(
                sha256(&replayed),
                strategy["recipe"]["final"]["payload_sha256"]
            );
        }
    }
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
    let source_record = candidates
        .iter()
        .find(|c| c["variant"] == new["source_search"]["variant"])
        .unwrap();
    let original_file = fs::read(directory.path().join("current-input/original")).unwrap();
    let mut portfolio_only = new.clone();
    portfolio_only
        .as_object_mut()
        .unwrap()
        .remove("source_search");
    let from_portfolio = envelope::reproduce_record(
        &portfolio_only,
        source_record,
        &original_file,
        &directory.path().join("portfolio-only-replay"),
    )
    .unwrap();
    let mut historical = new.clone();
    historical
        .as_object_mut()
        .unwrap()
        .remove("source_search_portfolio");
    let from_historical = envelope::reproduce_record(
        &historical,
        source_record,
        &original_file,
        &directory.path().join("historical-replay"),
    )
    .unwrap();
    assert_eq!(from_portfolio, from_historical);
    assert_eq!(
        sha256(&from_portfolio),
        source_record["sha256"].as_str().unwrap()
    );
    assert!(
        !directory.path().join("current/x").exists(),
        "the bootstrap must never execute"
    );
}

#[test]
fn online_search_admits_a_nonmonotone_pair_before_the_singleton_batch_can_exhaust_budget() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    const INPUT: &[u8] = b"int f(int alpha){return alpha+1;}int g(int beta){return beta+2;}int main(void){return f(1)!=g(0);}\n";
    let directory = tempfile::tempdir().unwrap();
    let mut opts = options(&clang, Value::Null);
    opts.embedding = None;
    opts.embedding_contract = "opaque".into();
    opts.candidates.max_candidates = 3;
    opts.candidates.max_name_groups = 2;
    opts.candidates.names_per_group = 1;
    opts.max_evaluations = 4;
    let compile = compiler_argv(&compiler);
    let cost = |data: &[u8]| -> anyhow::Result<usize> {
        let text = std::str::from_utf8(data)?;
        Ok(match (text.contains("alpha"), text.contains("beta")) {
            (true, true) => 100,
            (false, false) => 90,
            _ => 101,
        })
    };
    let legacy = source_search::search(
        INPUT,
        &opts,
        &compile,
        &directory.path().join("legacy"),
        &mut cost.clone(),
    )
    .unwrap();
    assert_eq!(legacy.report["selected_whole_file_bytes"], 100);
    opts.scheduling = source_search::SchedulingPolicy::InterleavedOnline;
    let online = source_search::search(
        INPUT,
        &opts,
        &compile,
        &directory.path().join("online"),
        &mut cost.clone(),
    )
    .unwrap();
    assert_eq!(online.report["selected_whole_file_bytes"], 90);
    assert_eq!(online.report["evaluations"], 4);
    assert_eq!(online.report["scheduling"], "interleaved_online");
    assert_eq!(
        online.report["coverage"]["basis_spaces"][0]["systematic_subsets_attempted"],
        1
    );
    let records = online.report["records"].as_array().unwrap();
    let costs: Vec<_> = records
        .iter()
        .filter(|r| r["stage"] == "complete-file-cost" && r["id"] != "original-source")
        .map(|r| r["whole_file_bytes"].as_u64().unwrap())
        .collect();
    assert_eq!(costs, vec![101, 90]);
    assert!(records
        .iter()
        .any(|r| r["stage"] == "composition-admitted" && r["phase"] == "interleaved-online"));
    assert_eq!(
        source_search::replay(
            INPUT,
            &online.recipe,
            &compile,
            &directory.path().join("replay")
        )
        .unwrap(),
        online.data
    );
}

#[test]
fn online_sibling_winners_replace_the_basis_prefix_and_subset_cap_does_not_starve_singles() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    const INPUT: &[u8] = b"int f(int alpha){return alpha+1;}int g(int beta){return beta+2;}int main(void){return f(1)!=g(0);}\n";
    let directory = tempfile::tempdir().unwrap();
    let mut opts = options(&clang, Value::Null);
    opts.embedding = None;
    opts.embedding_contract = "opaque".into();
    opts.scheduling = source_search::SchedulingPolicy::InterleavedOnline;
    opts.candidates.max_candidates = 3;
    opts.candidates.max_name_groups = 2;
    opts.candidates.names_per_group = 1;
    opts.max_combinations = 1;
    let compile = compiler_argv(&compiler);
    let mut cost = |data: &[u8]| -> anyhow::Result<usize> {
        let text = std::str::from_utf8(data)?;
        Ok(match (text.contains("alpha"), text.contains("beta")) {
            (true, true) => 100,
            (false, true) => 90,
            (true, false) => 80,
            (false, false) => 95,
        })
    };
    let result = source_search::search(
        INPUT,
        &opts,
        &compile,
        &directory.path().join("online"),
        &mut cost,
    )
    .unwrap();
    assert_eq!(result.report["selected_whole_file_bytes"], 80);
    assert_eq!(
        result.report["records"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|r| r["stage"] == "composition-admitted")
            .count(),
        2
    );
    assert_eq!(result.recipe["steps"].as_array().unwrap().len(), 1);
    assert_eq!(
        result.recipe["steps"][0]["input_source_sha256"],
        sha256(INPUT)
    );
    assert_eq!(
        source_search::replay(
            INPUT,
            &result.recipe,
            &compile,
            &directory.path().join("replay")
        )
        .unwrap(),
        result.data
    );

    // A subset cap removes only that queue's new work in the online policy.
    // Other generated alternatives remain measurable and the omitted subsets
    // remain explicitly incomplete instead of being reported as exhausted.
    opts.candidates.max_candidates = 4;
    opts.candidates.names_per_group = 2;
    let capped = source_search::search(
        INPUT,
        &opts,
        &compile,
        &directory.path().join("capped"),
        &mut |_| Ok(100),
    )
    .unwrap();
    let space = &capped.report["coverage"]["basis_spaces"][0];
    assert_eq!(space["singles_attempted"], space["generated_choices"]);
    assert_eq!(space["systematic_subsets_attempted"], 1);
    assert_eq!(space["stop"], "combination-attempt-budget");
    assert_eq!(space["exhausted"], false);
    assert_eq!(capped.report["status"], "space-incomplete");
}

#[test]
fn online_phase_quantum_leaves_work_for_typed_condition_candidates() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    const INPUT: &[u8] = b"int f(_Bool alpha){return alpha!=1;}int main(void){return f(1);}\n";
    let directory = tempfile::tempdir().unwrap();
    let mut opts = options(&clang, Value::Null);
    opts.embedding = None;
    opts.embedding_contract = "opaque".into();
    opts.conditions = true;
    opts.scheduling = source_search::SchedulingPolicy::InterleavedOnline;
    opts.candidates.max_candidates = 17;
    opts.candidates.max_name_groups = 1;
    opts.candidates.names_per_group = 16;
    opts.max_evaluations = 8;
    let compile = compiler_argv(&compiler);
    let result = source_search::search(
        INPUT,
        &opts,
        &compile,
        &directory.path().join("online"),
        &mut |data| {
            Ok(if std::str::from_utf8(data)?.contains("!=1") {
                100
            } else {
                90
            })
        },
    )
    .unwrap();
    assert_eq!(result.report["selected_whole_file_bytes"], 90);
    let spaces = result.report["coverage"]["basis_spaces"]
        .as_array()
        .unwrap();
    let spelling = spaces.iter().find(|s| s["family"] == "c-source").unwrap();
    let flow = spaces.iter().find(|s| s["family"] == "c-flow").unwrap();
    assert!(
        spelling["singles_attempted"].as_u64().unwrap()
            < spelling["generated_choices"].as_u64().unwrap()
    );
    assert!(flow["singles_attempted"].as_u64().unwrap() > 0);
    assert!(result.report["records"]
        .as_array()
        .unwrap()
        .iter()
        .any(|r| r["stage"] == "condition-admitted" && r["phase"] == "interleaved-online"));
    assert!(result.report["evaluations"].as_u64().unwrap() <= opts.max_evaluations as u64);
    assert_eq!(
        source_search::replay(
            INPUT,
            &result.recipe,
            &compile,
            &directory.path().join("replay")
        )
        .unwrap(),
        result.data
    );
}

#[test]
fn legacy_priority_seed_has_its_own_fresh_proof_and_never_exceeds_the_shared_evaluation_limit() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    const INPUT: &[u8] = b"int f(int alpha){return alpha+1;}int g(int beta){return beta+2;}int h(int gamma){return gamma+3;}int main(void){return f(1)+g(0)!=h(1);}\n";
    struct Cost {
        fresh_calls: usize,
    }
    impl source_search::CompleteFileObjective for Cost {
        fn measure(&mut self, data: &[u8]) -> anyhow::Result<usize> {
            let text = std::str::from_utf8(data)?;
            Ok(
                match (
                    text.contains("alpha"),
                    text.contains("beta"),
                    text.contains("gamma"),
                ) {
                    (true, true, true) => 100,
                    (false, true, true) => 90,
                    (false, false, true) => 85,
                    (false, true, false) => 92,
                    (true, false, false) => 80,
                    (false, false, false) => 95,
                    _ => 101,
                },
            )
        }
        fn fresh_measure(&mut self, data: &[u8]) -> anyhow::Result<usize> {
            self.fresh_calls += 1;
            self.measure(data)
        }
    }
    let directory = tempfile::tempdir().unwrap();
    let mut opts = options(&clang, Value::Null);
    opts.embedding = None;
    opts.embedding_contract = "opaque".into();
    opts.candidates.max_candidates = 4;
    opts.candidates.max_name_groups = 3;
    opts.candidates.names_per_group = 1;
    opts.max_evaluations = 16;
    let compile = compiler_argv(&compiler);
    let mut cost = Cost { fresh_calls: 0 };
    let result = source_search::search_with_objective(
        INPUT,
        &opts,
        &compile,
        &directory.path().join("both"),
        None,
        &mut cost,
    )
    .unwrap();
    assert_eq!(result.report["selected_whole_file_bytes"], 80);
    let priority = result
        .priority_seed
        .as_ref()
        .expect("distinct priority source retained");
    assert_eq!(priority.recipe["final"]["whole_file_bytes"], 90);
    assert_eq!(cost.fresh_calls, 2);
    assert_eq!(result.report["fresh_measurement_reservations"], 2);
    assert_eq!(result.report["retained_seed_count"], 2);
    assert!(result.report["evaluations"].as_u64().unwrap() <= opts.max_evaluations as u64);
    for (name, data, recipe) in [
        ("final", &result.data, &result.recipe),
        ("priority", &priority.data, &priority.recipe),
    ] {
        assert_eq!(
            recipe["final"]["cost_reproduction"],
            "fresh-objective-evaluation"
        );
        assert_eq!(
            source_search::replay(INPUT, recipe, &compile, &directory.path().join(name)).unwrap(),
            *data
        );
    }
    // The priority pass gets the same budget as before. Insufficient room for
    // a new deferred cost plus two final readbacks leaves that winner intact.
    opts.max_evaluations = 6;
    let mut cost = Cost { fresh_calls: 0 };
    let limited = source_search::search_with_objective(
        INPUT,
        &opts,
        &compile,
        &directory.path().join("limited"),
        None,
        &mut cost,
    )
    .unwrap();
    assert_eq!(limited.report["selected_whole_file_bytes"], 90);
    assert_eq!(
        limited.report["exhaustion_reason"],
        "priority-seed-evaluation-reservation"
    );
    assert_eq!(limited.report["evaluations"], 5);
    assert_eq!(limited.report["fresh_measurement_reservations"], 1);
    assert!(limited.priority_seed.is_none());
    assert_eq!(cost.fresh_calls, 1);
    // Old v1 recipes did not have a scheduling field; reconstruction remains
    // identical and cannot silently opt old searches into the online policy.
    let mut old_recipe = limited.recipe.clone();
    old_recipe["options"]
        .as_object_mut()
        .unwrap()
        .remove("scheduling");
    let old_options: source_search::SourceSearchOptions =
        serde_json::from_value(old_recipe["options"].clone()).unwrap();
    assert_eq!(
        old_options.scheduling,
        source_search::SchedulingPolicy::LegacyPriority
    );
    assert_eq!(
        source_search::replay(
            INPUT,
            &old_recipe,
            &compile,
            &directory.path().join("old-recipe")
        )
        .unwrap(),
        limited.data
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

    // Already measured singles can still be admitted after the new-evaluation
    // limit, with the last measurement reserved for independent readback.
    opts.max_evaluations = 3;
    let mut calls = 0;
    let limited = source_search::search(
        INPUT,
        &opts,
        &compile,
        &directory.path().join("measured-single"),
        &mut |data| {
            calls += 1;
            Ok(if data == INPUT { 100 } else { 90 })
        },
    )
    .unwrap();
    assert_eq!(limited.report["selected_whole_file_bytes"], 90);
    assert_eq!(calls, 3);
    assert_eq!(
        limited.report["exhaustion_reason"],
        "complete-file-evaluation-budget"
    );

    opts.max_evaluations = 32;
    opts.max_combinations = 1;
    opts.candidates.max_candidates = 4;
    opts.candidates.names_per_group = 2;
    let partial = source_search::search(
        INPUT,
        &opts,
        &compile,
        &directory.path().join("combination-limit"),
        &mut |_| Ok(100),
    )
    .unwrap();
    assert_eq!(partial.data, INPUT);
    assert_eq!(
        partial.report["exhaustion_reason"],
        "combination-attempt-budget"
    );
    assert_eq!(partial.report["coverage"]["combination_attempts"], 1);
    assert_eq!(
        partial.report["coverage"]["basis_spaces"][0]["exhausted"],
        false
    );
    assert_eq!(
        partial.report["coverage"]["declared_basis_spaces_complete"],
        false
    );
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
fn changed_frontend_context_is_fatal_at_the_search_admission_boundary() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    let directory = tempfile::tempdir().unwrap();
    let header = directory.path().join("value.h");
    struct ChangingCost<'a> {
        input: &'a [u8],
        header: &'a Path,
        phase: &'a str,
        changes: usize,
        fresh_calls: usize,
    }
    impl ChangingCost<'_> {
        fn change_header(&mut self) -> anyhow::Result<()> {
            fs::write(self.header, b"enum { OFFSET = 2 };\n")?;
            self.changes += 1;
            Ok(())
        }
        fn cost(&self, data: &[u8]) -> usize {
            if data == self.input || self.phase == "unchanged" {
                100
            } else {
                90
            }
        }
    }
    impl source_search::CompleteFileObjective for ChangingCost<'_> {
        fn measure(&mut self, data: &[u8]) -> anyhow::Result<usize> {
            if self.changes == 0
                && (self.phase == "baseline"
                    || data != self.input
                        && matches!(self.phase, "spelling" | "flow" | "unchanged"))
            {
                self.change_header()?;
            }
            Ok(self.cost(data))
        }
        fn fresh_measure(&mut self, data: &[u8]) -> anyhow::Result<usize> {
            self.fresh_calls += 1;
            if matches!(self.phase, "final" | "failed-final") {
                self.change_header()?;
            }
            anyhow::ensure!(self.phase != "failed-final", "injected fresh-cost failure");
            Ok(self.cost(data))
        }
    }
    for (scheduling, phase) in [
        source_search::SchedulingPolicy::LegacyPriority,
        source_search::SchedulingPolicy::InterleavedOnline,
    ]
    .into_iter()
    .flat_map(|policy| {
        [
            "spelling",
            "flow",
            "unchanged",
            "final",
            "failed-final",
            "baseline",
        ]
        .into_iter()
        .map(move |phase| (policy, phase))
    }) {
        fs::write(&header, b"enum { OFFSET = 1 };\n").unwrap();
        let input = format!("#include \"{}\"\nint k=OFFSET;int f(_Bool alpha){{return alpha!=1;}}int main(void){{return f(1)+k;}}\n", header.display()).into_bytes();
        let mut opts = options(&clang, Value::Null);
        opts.embedding = None;
        opts.embedding_contract = "opaque".into();
        opts.scheduling = scheduling;
        opts.candidates.max_candidates = if phase == "spelling" { 2 } else { 1 };
        opts.candidates.max_name_groups = 1;
        opts.candidates.names_per_group = 1;
        opts.conditions = phase != "spelling";
        let out = directory.path().join(format!("{scheduling:?}-{phase}"));
        let mut objective = ChangingCost {
            input: &input,
            header: &header,
            phase,
            changes: 0,
            fresh_calls: 0,
        };
        let error = source_search::search_with_objective(
            &input,
            &opts,
            &compiler_argv(&compiler),
            &out,
            None,
            &mut objective,
        )
        .unwrap_err();
        let explanation = format!("{error:#}");
        assert!(explanation.contains("changed"), "{phase}: {explanation}");
        assert!(
            error
                .downcast_ref::<csource::FrontendContextChanged>()
                .is_some(),
            "{phase}: {explanation}"
        );
        assert_eq!(objective.changes, 1, "{phase}");
        if matches!(phase, "final" | "failed-final") {
            assert_eq!(objective.fresh_calls, 1, "{phase}");
        }
        if phase == "failed-final" {
            assert!(explanation.contains("injected fresh-cost failure"));
        }
        let receipt: Value = serde_json::from_slice(
            &fs::read(out.join("source-search/failed-report.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(receipt["status"], "failed");
        assert!(
            !receipt["records"]
                .as_array()
                .unwrap()
                .iter()
                .any(|r| r["stage"] == "semantic-rejected"),
            "{phase}"
        );
        if phase == "flow" {
            assert!(receipt["records"]
                .as_array()
                .unwrap()
                .iter()
                .any(|r| r["stage"] == "condition-candidate"));
        }
        assert_eq!(
            attempts::compare(&[out.join("source-search/attempts")]).unwrap()["runs"][0]["status"],
            "failed"
        );
    }
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

#[test]
fn cleanup_reanalyzes_dead_dependencies_and_uses_native_cost_and_replay_gates() {
    let Some((clang, compiler)) = tools() else {
        return;
    };
    let directory = tempfile::tempdir().unwrap();
    let header = "no_longer_required_after_function_cleanup.h";
    fs::write(
        directory.path().join(header),
        "#define UNREFERENCED_FACTOR 139\n",
    )
    .unwrap();
    let source = format!("#include \"{header}\"\nstatic int obsolete_helper(int n){{return n*UNREFERENCED_FACTOR+31;}}int main(void){{return 0;}}\n").into_bytes();
    let path = directory.path().join("source.c");
    fs::write(&path, &source).unwrap();
    let mut opts = source_search::SourceSearchOptions {
        candidates: CSourceOptions {
            frontend: CFlowOptions {
                clang,
                source_path: Some(path),
                token_contract: "no-token-observation".into(),
                ..Default::default()
            },
            rename_locals: false,
            integer_literals: false,
            character_literals: false,
            ..Default::default()
        },
        conditions: false,
        cleanup: true,
        max_rounds: 2,
        max_evaluations: 32,
        max_seconds: 60.0,
        ..Default::default()
    };
    let mut compile = compiler_argv(&compiler);
    compile.extend(["-I".into(), directory.path().to_string_lossy().into_owned()]);
    let mut measure = |data: &[u8]| -> anyhow::Result<usize> {
        Ok(32 + codec::compress(data, &compression())?.len())
    };
    let searched = source_search::search(
        &source,
        &opts,
        &compile,
        &directory.path().join("search"),
        &mut measure,
    )
    .unwrap();
    assert!(measure(&searched.data).unwrap() < measure(&source).unwrap());
    assert!(!searched
        .data
        .windows(b"obsolete_helper".len())
        .any(|w| w == b"obsolete_helper"));
    assert!(!searched
        .data
        .windows(b"#include".len())
        .any(|w| w == b"#include"));
    assert!(searched.recipe["steps"]
        .as_array()
        .unwrap()
        .iter()
        .all(|step| step["kind"] == "c-cleanup"));
    assert_eq!(
        source_search::replay(
            &source,
            &searched.recipe,
            &compile,
            &directory.path().join("replay")
        )
        .unwrap(),
        searched.data
    );
    opts.scheduling = source_search::SchedulingPolicy::InterleavedOnline;
    let online = source_search::search(
        &source,
        &opts,
        &compile,
        &directory.path().join("online"),
        &mut measure,
    )
    .unwrap();
    assert_eq!(online.data, searched.data);
    assert_eq!(
        source_search::replay(
            &source,
            &online.recipe,
            &compile,
            &directory.path().join("online-replay")
        )
        .unwrap(),
        online.data
    );
    opts.scheduling = source_search::SchedulingPolicy::LegacyPriority;
    let mut tampered = searched.recipe.clone();
    tampered["options"]["cleanup"] = json!(false);
    assert!(source_search::replay(
        &source,
        &tampered,
        &compile,
        &directory.path().join("disabled-replay")
    )
    .is_err());
    opts.cleanup = false;
    assert_eq!(
        source_search::search(
            &source,
            &opts,
            &compile,
            &directory.path().join("disabled"),
            &mut measure
        )
        .unwrap()
        .data,
        source
    );

    // A source proof does not authorize changing compiler diagnostics. Native
    // bytes alone would miss the removed -Wunused-function warning.
    opts.cleanup = true;
    compile.push("-Wall".into());
    let rejected = source_search::search(
        &source,
        &opts,
        &compile,
        &directory.path().join("diagnostics"),
        &mut measure,
    )
    .unwrap();
    assert_eq!(rejected.data, source);
    assert!(rejected.report.to_string().contains("semantic-rejected"));
}
