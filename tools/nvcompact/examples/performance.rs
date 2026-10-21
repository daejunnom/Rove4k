//! Bounded inert-input benchmark for cache churn, mixed-cost codec scheduling,
//! and exact-byte roundtrip memory. This never executes a source or an engine.
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
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(
        args.len() == 3,
        "usage: performance cache|churn|mixed|restore JOBS"
    );
    let jobs: usize = args[2].parse()?;
    ensure!((1..=16).contains(&jobs), "jobs must be 1..16");
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
    println!(
        "{}",
        serde_json::to_string(&json!({"mode":args[1],"jobs":jobs,"iterations":iterations,
        "measurement_seconds":elapsed,"total_seconds":started.elapsed().as_secs_f64(),
        "payload_bytes":payload.len(),"payload_sha256":sha256(&payload),
        "costs_sha256":sha256(&serde_json::to_vec(&expected_costs)?),
        "artifact_bytes":result.data.len(),"artifact_sha256":sha256(&result.data),
        "fresh_identity":true,"stats":stats,"codecs":codec::library_versions()}))?
    );
    Ok(())
}
