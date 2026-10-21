//! Bounded inert-input benchmark for cache churn, uncached source costs,
//! refinement planning, scheduling, and exact-byte roundtrip memory. An optional
//! input file is read as bytes only; this never executes a source or an engine.
//! Run the same example against both reviewed source revisions; wall time and
//! peak RSS are observations, never test pass thresholds.
use anyhow::{ensure, Result};
use nvcompact::{
    codec::{self, CodecPortfolio, Recipe},
    envelope_cost::{CacheBudget, WholeFileObjective},
    sha256,
};
use serde_json::json;
use std::time::Instant;
const HEADER: &[u8] = b"#!/bin/sh\ntail -n+3 \"$0\"|gzip -d\n";
fn recipe(format: &str, level: u32) -> Recipe {
    let mut value = Recipe::new(format);
    value.level = Some(level);
    value
}
fn objective(recipes: Vec<Recipe>, jobs: usize, cache: bool) -> Result<WholeFileObjective> {
    WholeFileObjective::new(
        HEADER,
        "gzip -d",
        CodecPortfolio::fixed(recipes)?,
        jobs,
        if cache {
            CacheBudget::default()
        } else {
            CacheBudget::disabled()
        },
    )
}
fn input(size: usize) -> Vec<u8> {
    let mut state = 123456789u64;
    (0..size)
        .map(|index| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            if index % 5 == 0 {
                state as u8
            } else {
                b"int a=42;return a*a;\n"[index % 20]
            }
        })
        .collect()
}

fn source_domain(size: usize) -> Vec<Recipe> {
    let mut recipes = vec![
        recipe("gzip", 1),
        recipe("gzip", 9),
        recipe("bzip2", 1),
        recipe("bzip2", 9),
    ];
    for (format, x86) in [
        ("alone", false),
        ("xz", false),
        ("raw", false),
        ("raw", true),
    ] {
        let mut value = Recipe::new(format);
        value.preset = Some(6);
        value.dict_size = Some(codec::dictionary_size(size, 8 << 20));
        value.x86 = x86;
        recipes.push(value);
    }
    recipes
}

fn cold_objective(portfolio: CodecPortfolio, jobs: usize) -> Result<WholeFileObjective> {
    WholeFileObjective::new(
        HEADER,
        "gzip -d",
        portfolio,
        jobs,
        CacheBudget {
            max_bytes: 0,
            max_entries: 0,
            ..CacheBudget::default()
        },
    )
}

fn planning(jobs: usize) -> Result<()> {
    let mut submitted = Recipe::new("raw");
    submitted.x86 = true;
    submitted.dict_size = Some(16384);
    submitted.lc = Some(2);
    let portfolio = CodecPortfolio::legacy(true, Some(submitted));
    let plan = portfolio.plan(12_345);
    let costs: Vec<_> = (0..plan.initial.len())
        .map(|index| {
            if index + 1 == plan.initial.len() {
                0
            } else {
                100 + index % 17
            }
        })
        .collect();
    let expected = portfolio.refinement_recipes(&plan, &costs)?;
    let iterations = 128;
    let started = Instant::now();
    for _ in 0..iterations {
        let actual = std::hint::black_box(portfolio.refinement_recipes(&plan, &costs)?);
        ensure!(actual == expected, "refinement domain changed");
    }
    println!(
        "{}",
        serde_json::to_string(&json!({
            "mode":"planning", "jobs":jobs, "iterations":iterations,
            "measurement_seconds":started.elapsed().as_secs_f64(),
            "scope":"recipe planning only; synthetic initial costs; no compression execution",
            "initial_recipes":plan.initial.len(), "refinement_recipes":expected.len(),
            "initial_sha256":sha256(&serde_json::to_vec(&plan.initial)?),
            "refinement_sha256":sha256(&serde_json::to_vec(&expected)?),
            "costs_sha256":sha256(&serde_json::to_vec(&costs)?)
        }))?
    );
    Ok(())
}

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(
        args.len() == 3 || (args.len() == 4 && args[1] == "file"),
        "usage: performance cache|churn|tiny|small|legacy|mixed|restore|planning JOBS, or performance file JOBS INPUT"
    );
    let jobs: usize = args[2].parse()?;
    ensure!((1..=16).contains(&jobs), "jobs must be 1..16");
    if args[1] == "planning" {
        return planning(jobs);
    }
    let started = Instant::now();
    let (mut cost, payload, iterations, expected_costs, elapsed) = match args[1].as_str() {
        "cache" | "churn" => {
            let domain = vec![recipe("gzip", 1)];
            let mut cost = objective(domain, jobs, true)?;
            let payloads: Vec<Vec<u8>> = (0..4096)
                .map(|index| {
                    format!("/* inert cache key {index:06} */ int a=12345; int b=67890;\n")
                        .into_bytes()
                })
                .collect();
            let mut costs = Vec::new();
            for payload in &payloads {
                costs.push(cost.measure(payload)?);
            }
            let measured = Instant::now();
            let iterations = if args[1] == "cache" { 8 } else { 2 };
            for pass in 0..iterations {
                for (index, payload) in payloads.iter().enumerate() {
                    if args[1] == "cache" {
                        ensure!(
                            cost.measure(payload)? == costs[index],
                            "cached cost changed"
                        );
                    } else {
                        let mut next = payload.clone();
                        next.extend_from_slice(format!("/* pass {pass} */").as_bytes());
                        cost.measure(&next)?;
                    }
                }
            }
            (
                cost,
                payloads[0].clone(),
                iterations * payloads.len(),
                costs,
                measured.elapsed().as_secs_f64(),
            )
        }
        "tiny" | "small" | "legacy" | "file" => {
            let payload = match args[1].as_str() {
                "tiny" => input(64),
                "small" => input(16 << 10),
                "legacy" => input(8 << 10),
                _ => {
                    let path = std::path::Path::new(&args[3]);
                    ensure!(
                        path.metadata()?.len() <= codec::MAX_PAYLOAD as u64,
                        "input exceeds payload profile"
                    );
                    std::fs::read(path)?
                }
            };
            let portfolio = if args[1] == "tiny" {
                CodecPortfolio::fixed(vec![recipe("gzip", 1)])?
            } else if args[1] == "legacy" {
                CodecPortfolio::legacy(false, None)
            } else {
                CodecPortfolio::fixed(source_domain(payload.len()))?
            };
            let mut cost = cold_objective(portfolio, jobs)?;
            let iterations = match args[1].as_str() {
                "tiny" => 16_384,
                "small" => 24,
                "legacy" => 3,
                _ => 24,
            };
            let mut costs = Vec::with_capacity(iterations);
            let measured = Instant::now();
            for pass in 0..iterations {
                // The explicit file mode measures the exact retained input;
                // generated source-like modes exercise distinct cold keys.
                if args[1] == "file" {
                    costs.push(cost.measure(&payload)?);
                } else {
                    let mut next = payload.clone();
                    next.extend_from_slice(format!("/* {pass} */").as_bytes());
                    costs.push(cost.measure(&next)?);
                }
            }
            (
                cost,
                payload,
                iterations,
                costs,
                measured.elapsed().as_secs_f64(),
            )
        }
        "mixed" => {
            let mut domain = Vec::new();
            for level in 1..=9 {
                domain.push(recipe("bzip2", level));
                domain.push(recipe("gzip", level));
            }
            let mut cost = objective(domain, jobs, false)?;
            let payload = input(512 << 10);
            let measured = Instant::now();
            let first = cost.measure(&payload)?;
            for _ in 1..3 {
                ensure!(cost.measure(&payload)? == first, "cost changed");
            }
            (
                cost,
                payload,
                3,
                vec![first],
                measured.elapsed().as_secs_f64(),
            )
        }
        "restore" => {
            let mut cost = objective(
                (1..=4).map(|level| recipe("gzip", level)).collect(),
                jobs,
                false,
            )?;
            let payload = vec![b'x'; codec::MAX_PAYLOAD];
            let measured = Instant::now();
            let first = cost.measure(&payload)?;
            (
                cost,
                payload,
                1,
                vec![first],
                measured.elapsed().as_secs_f64(),
            )
        }
        _ => anyhow::bail!("unknown benchmark mode"),
    };
    let stats = cost.stats();
    let result = cost.evaluate("inert", &payload, "exact input bytes")?;
    let fresh = cost.fresh_evaluate("inert", &payload, "exact input bytes")?;
    ensure!(result.data == fresh.data, "fresh artifact differs");
    let recipe_results: Vec<_> = result
        .records
        .iter()
        .map(|record| {
            json!({
                "recipe":record["recipe"], "bytes":record["bytes"], "sha256":record["sha256"]
            })
        })
        .collect();
    let fresh_recipe_results: Vec<_> = fresh
        .records
        .iter()
        .map(|record| {
            json!({
                "recipe":record["recipe"], "bytes":record["bytes"], "sha256":record["sha256"]
            })
        })
        .collect();
    ensure!(
        recipe_results == fresh_recipe_results,
        "fresh recipe results differ"
    );
    println!(
        "{}",
        serde_json::to_string(&json!({"mode":args[1],"jobs":jobs,"iterations":iterations,
        "measurement_seconds":elapsed,"total_seconds":started.elapsed().as_secs_f64(),
        "payload_bytes":payload.len(),"payload_sha256":sha256(&payload),
        "input_path":args.get(3),
        "costs_sha256":sha256(&serde_json::to_vec(&expected_costs)?),
        "recipe_results_sha256":sha256(&serde_json::to_vec(&recipe_results)?),
        "recipe_results":recipe_results,
        "cost_vector_scope":if matches!(args[1].as_str(), "cache" | "churn") {
            "warmup input minimum costs"
        } else { "all timed input minimum costs, except repeated equal mixed costs coalesced" },
        "artifact_bytes":result.data.len(),"artifact_sha256":sha256(&result.data),
        "fresh_identity":true,"stats":stats,"codecs":codec::library_versions()}))?
    );
    Ok(())
}
