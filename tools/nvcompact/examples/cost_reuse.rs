//! A bounded, synthetic comparison of repeated whole-file costs with and
//! without retained codec/header work. No shell, compiler or engine is run.
//!
//! cargo run --release --locked -p nvcompact --example cost_reuse
//!
//! This isolates reuse on identical work. It is not a benchmark of an engine
//! campaign: a broader search can do more work and take longer overall.
use anyhow::{ensure, Result};
use nvcompact::{
    codec::{self, CodecPortfolio, Recipe},
    envelope_cost::{CacheBudget, WholeFileObjective},
    sha256,
};
use serde_json::{json, Value};
use std::time::Instant;

const HEADER: &[u8] = b"#!/bin/sh\ntail -n+3 \"$0\"|gzip -d\n";
const REPEATS: usize = 16;
const TRIALS: usize = 4;

fn recipes() -> Vec<Recipe> {
    [1, 6, 9]
        .into_iter()
        .map(|level| {
            let mut recipe = Recipe::new("gzip");
            recipe.level = Some(level);
            recipe
        })
        .collect()
}

fn inputs() -> Vec<Vec<u8>> {
    // Deliberately owned, inert data with both repeated and changing fields.
    (0..8)
        .map(|variant| {
            (0..256)
                .map(|row| {
                    format!(
                        "sample={variant};row={row};value={}; repeated complete-file cost input\n",
                        (row * 17 + variant * 31) % 257
                    )
                })
                .collect::<String>()
                .into_bytes()
        })
        .collect()
}

fn run(inputs: &[Vec<u8>], reuse: bool) -> Result<(Value, Vec<String>)> {
    let started = Instant::now();
    let mut objective = WholeFileObjective::new(
        HEADER,
        "gzip -d",
        CodecPortfolio::fixed(recipes())?,
        1,
        if reuse {
            CacheBudget::default()
        } else {
            CacheBudget::disabled()
        },
    )?;
    let mut identities = Vec::new();
    for repeat in 0..REPEATS {
        for (index, payload) in inputs.iter().enumerate() {
            let result = objective.evaluate("owned-sample", payload, "inert byte identity")?;
            let identity = sha256(&result.data);
            if repeat == 0 {
                identities.push(identity);
            } else {
                ensure!(identity == identities[index], "repeated cost changed bytes");
            }
        }
    }
    let elapsed = started.elapsed().as_secs_f64();
    let measured = objective.stats();
    let fresh_started = Instant::now();
    for (index, payload) in inputs.iter().enumerate() {
        let fresh = objective.fresh_evaluate("owned-sample", payload, "inert byte identity")?;
        ensure!(
            sha256(&fresh.data) == identities[index],
            "fresh codec domain differs from measured artifact"
        );
    }
    Ok((
        json!({
            "reuse": reuse,
            "measurement_seconds": elapsed,
            "fresh_check_seconds": fresh_started.elapsed().as_secs_f64(),
            "measurement_stats": measured,
            "stats_after_fresh": objective.stats(),
            "fresh_artifact_identity": "passed for every unique input"
        }),
        identities,
    ))
}

fn main() -> Result<()> {
    ensure!(
        std::env::args_os().len() == 1,
        "this bounded example accepts no arguments"
    );
    let inputs = inputs();
    let mut reference = None;
    let mut trials = Vec::new();
    for trial in 0..TRIALS {
        // Reverse the execution order between trials; report individual runs.
        for reuse in if trial % 2 == 0 {
            [false, true]
        } else {
            [true, false]
        } {
            let (mut record, identities) = run(&inputs, reuse)?;
            if let Some(expected) = &reference {
                ensure!(
                    &identities == expected,
                    "cache policy changed winning artifacts"
                );
            } else {
                reference = Some(identities);
            }
            record["trial"] = json!(trial + 1);
            trials.push(record);
        }
    }
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "schema": "nvcompact-cost-reuse-example-v1",
            "scope": "same fixed recipe domain and identical repeated inert inputs; not whole-campaign speed",
            "jobs": 1,
            "unique_payloads": inputs.len(),
            "payloads": inputs.iter().map(|data| json!({"bytes":data.len(),"sha256":sha256(data)})).collect::<Vec<_>>(),
            "repeats_per_payload": REPEATS,
            "recipe_domain": recipes(),
            "codecs": codec::library_versions(),
            "artifact_sha256": reference,
            "trials": trials
        }))?
    );
    Ok(())
}
