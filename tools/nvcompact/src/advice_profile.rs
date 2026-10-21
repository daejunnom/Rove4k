//! Optional diagnostic instrumentation and sample-only observations.
//! This module cannot create a compression candidate or admit a rewrite.
use crate::advisor::{
    domain::{Domain, FINITE_LIMIT},
    nversion::{self, DomainProvenance, FiniteDomain, SearchBudget, SearchRequest},
};
use crate::advisor::{AdviceReport, RangeSite};
use crate::sha256;
use anyhow::{ensure, Context, Result};
use serde::Serialize;
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};

const TRACE_PREFIX: &str = "NVCOMPACT_ADVICE_V1";
const MAX_TRACE_BYTES: usize = 16 << 20;

#[derive(Clone, Debug)]
pub struct InstrumentOptions {
    pub max_sites: usize,
    pub max_samples: usize,
}

impl Default for InstrumentOptions {
    fn default() -> Self {
        Self {
            max_sites: 128,
            max_samples: 100_000,
        }
    }
}

pub struct Instrumentation {
    pub source: Vec<u8>,
    pub header: Vec<u8>,
    pub header_name: String,
    pub manifest: Value,
}

fn integer_type(name: &str) -> Option<(i128, i128, bool)> {
    Some(match name {
        "_Bool" => (0, 1, false),
        "int" => (i32::MIN as i128, i32::MAX as i128, false),
        "unsigned int" => (0, u32::MAX as i128, true),
        "long" | "long int" | "long long" | "long long int" => {
            (i64::MIN as i128, i64::MAX as i128, false)
        }
        "unsigned long" | "unsigned long int" | "unsigned long long" | "unsigned long long int" => {
            (0, u64::MAX as i128, true)
        }
        _ => return None,
    })
}

fn direct_identifier(text: &str) -> bool {
    let mut bytes = text.bytes();
    matches!(bytes.next(), Some(b'a'..=b'z' | b'A'..=b'Z' | b'_'))
        && bytes.all(|b| b.is_ascii_alphanumeric() || b == b'_')
}

fn valid_digest(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|b| b.is_ascii_hexdigit())
}

fn check_report(report: &AdviceReport) -> Result<()> {
    ensure!(report.advisory_only, "profile requires an advisory report");
    ensure!(
        report.language_details.is_none()
            && report
                .frontend
                .get("language")
                .and_then(Value::as_str)
                .is_none_or(|language| language == "c"),
        "profile and instrumentation are currently supported only for C reports"
    );
    ensure!(
        valid_digest(&report.source_sha256) && valid_digest(&report.analysis_context_sha256),
        "invalid source/context fingerprint"
    );
    let mut ids = BTreeSet::new();
    for site in &report.ranges {
        ensure!(ids.insert(&site.id), "duplicate range site identity");
    }
    ensure!(
        report.expressions.len() <= 512,
        "expression site count exceeds advisory limit"
    );
    Ok(())
}

/// Build a separate, explicitly requested diagnostic translation unit.
/// Each admitted expression is evaluated once and returned with its original
/// built-in integer type. Logging changes timing and I/O; this is not a shipping
/// artifact or a semantic-equivalence qualification run.
pub fn instrument(
    source: &[u8],
    report: &AdviceReport,
    options: &InstrumentOptions,
) -> Result<Instrumentation> {
    check_report(report)?;
    ensure!(
        sha256(source) == report.source_sha256,
        "source changed after advisory analysis"
    );
    ensure!(
        (1..=4096).contains(&options.max_sites),
        "probe site budget must be 1..4096"
    );
    ensure!(
        (1..=1_000_000).contains(&options.max_samples),
        "sample budget must be 1..1000000"
    );
    let text = std::str::from_utf8(source).context("instrumentation requires UTF-8 C source")?;
    let mut eligible: Vec<&RangeSite> = report
        .ranges
        .iter()
        .filter(|site| {
            site.instrumentable
                && integer_type(&site.c_type).is_some()
                && direct_identifier(&site.expression)
                && site.expression == site.symbol
        })
        .collect();
    eligible.sort_by_key(|s| (s.location.start, s.location.end));
    let eligible_count = eligible.len();
    eligible.truncate(options.max_sites);
    ensure!(
        !eligible.is_empty(),
        "no supported ordinary integer read sites to instrument"
    );
    let prefix = format!("nvcompact_advice_{}", &report.source_sha256[..16]);
    ensure!(
        !text.contains(&prefix),
        "diagnostic helper name conflicts with source"
    );
    let header_name = format!("{prefix}.h");
    let mut edited = Vec::with_capacity(source.len() + eligible.len() * 120);
    edited.extend_from_slice(format!("#include \"{header_name}\"\n#line 1\n").as_bytes());
    let mut position = 0;
    let mut labels = Vec::with_capacity(eligible.len());
    for (index, site) in eligible.iter().enumerate() {
        let loc = &site.location;
        ensure!(
            loc.start >= position && loc.start < loc.end && loc.end <= source.len(),
            "overlapping or out-of-bounds probe site"
        );
        ensure!(
            source.get(loc.start..loc.end) == Some(site.expression.as_bytes()),
            "probe source does not match the analyzed expression"
        );
        ensure!(
            site.id == format!("range:{}:{}", loc.start, loc.end),
            "unexpected probe site identity"
        );
        let unsigned = integer_type(&site.c_type).unwrap().2;
        let (helper, wide) = if unsigned {
            ("unsigned", "unsigned long long")
        } else {
            ("signed", "long long")
        };
        edited.extend_from_slice(&source[position..loc.start]);
        edited.extend_from_slice(
            format!(
                "(({ty}){prefix}_{helper}({index},({wide})({expr})))",
                ty = site.c_type,
                expr = site.expression
            )
            .as_bytes(),
        );
        position = loc.end;
        labels.push(format!("\"{}\"", site.id));
    }
    edited.extend_from_slice(&source[position..]);
    let header = format!(
        r#"/* Diagnostic-only instrumentation. Never include in a submission build. */
#ifndef {prefix}_included
#define {prefix}_included
#include <stdio.h>
#include <errno.h>
#include <stdint.h>
#include <stdatomic.h>
_Static_assert(sizeof(int)==4 && sizeof(long)==8 && sizeof(long long)==8,
               "NVCompact diagnostic instrumentation requires LP64");
static atomic_uint_fast64_t {prefix}_count = ATOMIC_VAR_INIT(0);
static const char *const {prefix}_sites[] = {{{labels}}};
static inline int {prefix}_reserve(void) {{
    uint_fast64_t n = atomic_load_explicit(&{prefix}_count, memory_order_relaxed);
    while(n < {max_samples}) {{
        if(atomic_compare_exchange_weak_explicit(&{prefix}_count, &n, n+1,
                memory_order_relaxed, memory_order_relaxed)) return 1;
    }}
    return 0;
}}
static inline long long {prefix}_signed(unsigned site, long long value) {{
    int saved_errno = errno;
    if({prefix}_reserve()) fprintf(stderr, "{TRACE_PREFIX}\t{source_hash}\t{context_hash}\t%s\t%lld\n", {prefix}_sites[site], value);
    errno = saved_errno;
    return value;
}}
static inline unsigned long long {prefix}_unsigned(unsigned site, unsigned long long value) {{
    int saved_errno = errno;
    if({prefix}_reserve()) fprintf(stderr, "{TRACE_PREFIX}\t{source_hash}\t{context_hash}\t%s\t%llu\n", {prefix}_sites[site], value);
    errno = saved_errno;
    return value;
}}
#endif
"#,
        labels = labels.join(","),
        max_samples = options.max_samples,
        source_hash = report.source_sha256,
        context_hash = report.analysis_context_sha256
    );
    let manifest = json!({
        "format_version": 1, "advisory_only": true,
        "source_sha256": report.source_sha256,
        "analysis_context_sha256": report.analysis_context_sha256,
        "instrumented_source_sha256": sha256(&edited),
        "header_sha256": sha256(header.as_bytes()),
        "header_name": header_name,
        "max_samples_per_process": options.max_samples,
        "eligible_sites": eligible_count, "instrumented_sites": eligible.len(),
        "omitted_sites": eligible_count - eligible.len(),
        "sites": eligible,
        "frontend": report.frontend,
        "execution": "not started; build and run this diagnostic copy explicitly",
        "contract": "Hosted C11 LP64 diagnostic build in ordinary thread contexts. Ordinary integer read evaluated once, original integer type returned; errno restored. Atomic global sample quota and stdio record serialization. Probes are not async-signal-safe: do not instrument signal/interrupt handlers. Logging, timing, stack, include context and source location observations change. No shipping-equivalence or performance claim.",
        "trace": "Capture stderr. Supply the same original source and compiler context to advise-c --profile. An unfinished or quota-limited trace is still only a finite sample; absence of a record is not unreachability.",
        "build": "Use the analyzed compiler flags and original quoted-include directory, plus this directory for the diagnostic header. Recheck all dependencies before building. This tool does not execute the generated code."
    });
    Ok(Instrumentation {
        source: edited,
        header: header.into_bytes(),
        header_name,
        manifest,
    })
}

#[derive(Debug, Serialize)]
struct Observation<'a> {
    site_id: &'a str,
    location: &'a crate::advisor::SourceLocation,
    symbol: &'a str,
    function: &'a str,
    c_type: &'a str,
    operation: &'a Option<String>,
    samples: usize,
    minimum: String,
    maximum: String,
    outside_static_range: bool,
    outside_static_domain: bool,
    static_membership_scope: &'static str,
    observed_known_zero: String,
    observed_known_one: String,
    distinct_values: Vec<String>,
    distinct_values_complete: bool,
    assurance: &'static str,
    suggestion: Option<String>,
    requirements: Vec<&'static str>,
}

struct Samples {
    count: usize,
    min: i128,
    max: i128,
    zero: u64,
    one: u64,
    distinct: BTreeSet<i128>,
    distinct_complete: bool,
    outside_domain: bool,
}

fn domain_for_site(site: &RangeSite) -> Result<Domain> {
    let (lo, hi, _) = integer_type(&site.c_type).context("unsupported observation integer type")?;
    let bits = if site.c_type == "_Bool" {
        1
    } else if hi <= u32::MAX as i128 {
        32
    } else {
        64
    };
    let signed = lo < 0;
    let min = site
        .minimum
        .parse()
        .context("invalid static range minimum")?;
    let max = site
        .maximum
        .parse()
        .context("invalid static range maximum")?;
    ensure!(
        min <= max && min >= lo && max <= hi,
        "invalid static integer bounds"
    );
    if let Some(summary) = &site.domain {
        let domain = Domain::from_summary(summary).context("invalid static domain summary")?;
        ensure!(
            (domain.bits, domain.signed, domain.lo, domain.hi) == (bits, signed, min, max),
            "static domain/type mismatch"
        );
        Ok(domain)
    } else {
        Ok(Domain::interval(min, max, bits, signed))
    }
}

fn observed_comparisons(
    report: &AdviceReport,
    observations: &BTreeMap<&str, Samples>,
) -> Result<Value> {
    let budget_total = report.statistics["nversion_work_budget"]
        .as_u64()
        .unwrap_or(16_000_000)
        .min(100_000_000) as usize;
    let mut work = 0;
    let mut rows = Vec::new();
    let mut sites: Vec<_> = report.expressions.iter().collect();
    sites.sort_by_key(|s| (std::cmp::Reverse(s.original.len()), s.location.start));
    for site in sites {
        let Some(entry) = site.entry_site_id.as_deref() else {
            continue;
        };
        let Some(samples) = observations.get(entry) else {
            continue;
        };
        let domain = Domain::interval(
            samples.min,
            samples.max,
            site.variable_type.bits(),
            !site.variable_type.is_unsigned(),
        );
        let base = json!({"expression_id": site.id, "location":site.location, "original":site.original,
            "entry_site_id":entry,"samples":samples.count,
            "assurance":"conditional-observed-interval-closure", "outside_static_domain":samples.outside_domain,
            "hypothesis":domain.summary(),
            "closure":"Every integer between the observed minimum and maximum, including unobserved values. Observed fixed bits and sparse samples do not narrow this closure.",
            "requirements":["Independently establish that all executions reaching this expression stay inside this hypothesis before shortening.",
                "Finite profiling, passing outside probes and static containing-domain comparison have distinct evidence scopes.",
                "Preserve types, stable ordinary reads, source observations and full submitted-file cost; never apply automatically."]});
        let mut row = base;
        if samples.outside_domain {
            row["status"] = json!("withheld: observations contradict static domain; investigate the source/context or analysis");
            rows.push(row);
            continue;
        }
        let Some(values) = domain.enumerate(FINITE_LIMIT) else {
            row["status"] = json!("observed interval closure exceeds finite-domain budget");
            rows.push(row);
            continue;
        };
        let remaining = budget_total.saturating_sub(work);
        if remaining < 1000 {
            row["status"] = json!("observed comparison work budget exhausted");
            rows.push(row);
            continue;
        }
        let mut budget = SearchBudget::default();
        budget.max_evaluations = budget.max_evaluations.min(remaining);
        let request = SearchRequest {
            original: site.expression.clone(), original_source: site.original.clone(), symbol: site.symbol.clone(),
            variable_type: site.variable_type, domain: FiniteDomain { values, provenance: DomainProvenance::ObservedClosure,
                description: "Conditional full interval closure of expression-entry samples; no all-executions reachability claim.".into() }, budget,
        };
        let comparison = nversion::compare_and_suggest(&request).map_err(anyhow::Error::msg)?;
        work += comparison.statistics.evaluation_steps;
        let outside: Vec<_> = comparison.candidates.iter().filter(|c| c.bytes_saved > 0).take(8).map(|candidate| {
            let witnesses = nversion::probe_outside_domain(&site.expression, &candidate.expression, site.variable_type, &request.domain, 32)
                .map_err(anyhow::Error::msg)?;
            Ok(json!({"candidate":candidate.source,"max_probes":32,"exhaustive":false,"counterexamples":witnesses,
                "scope":"Outside-hypothesis diagnostics only; a witness prevents a universal claim, and no witness does not prove one."}))
        }).collect::<Result<_>>()?;
        row["status"] = json!("compared-conditionally; static facts unchanged");
        row["comparison"] = serde_json::to_value(comparison)?;
        row["outside_domain_checks"] = json!(outside);
        rows.push(row);
    }
    Ok(
        json!({"work_budget":budget_total,"evaluation_steps":work,"expressions":rows,
        "outside_probe_limits":{"max_candidates_per_expression":8,"max_values_per_candidate":32,
            "scope":"separately bounded diagnostics; excluded from synthesis evaluation-step counts"},
        "static_facts_changed":false,"compression_candidates_created":0}),
    )
}

/// Import bounded trace records. Values stay decimal strings in JSON so a
/// consumer cannot lose 64-bit integer precision through a floating-point JSON
/// number. No sample narrows or replaces a static range.
pub fn observe(report: &AdviceReport, trace: &[u8]) -> Result<Value> {
    check_report(report)?;
    ensure!(
        trace.len() <= MAX_TRACE_BYTES,
        "observation trace exceeds 16 MiB"
    );
    let text = std::str::from_utf8(trace).context("observation trace must be UTF-8")?;
    let sites: BTreeMap<&str, &RangeSite> =
        report.ranges.iter().map(|s| (s.id.as_str(), s)).collect();
    let domains: BTreeMap<&str, Domain> = sites
        .iter()
        .map(|(&id, site)| Ok((id, domain_for_site(site)?)))
        .collect::<Result<_>>()?;
    let mut observations: BTreeMap<&str, Samples> = BTreeMap::new();
    let mut ignored_lines = 0usize;
    let mut records = 0usize;
    for raw_line in text.split_inclusive('\n') {
        if !raw_line.starts_with(TRACE_PREFIX) {
            ignored_lines += 1;
            continue;
        }
        ensure!(
            raw_line.ends_with('\n'),
            "truncated observation record: missing final newline"
        );
        let line = raw_line
            .strip_suffix('\n')
            .unwrap()
            .strip_suffix('\r')
            .unwrap_or_else(|| raw_line.strip_suffix('\n').unwrap());
        let fields: Vec<_> = line.split('\t').collect();
        ensure!(
            fields.len() == 5 && fields[0] == TRACE_PREFIX,
            "malformed observation record"
        );
        ensure!(
            fields[1] == report.source_sha256,
            "observation source fingerprint mismatch"
        );
        ensure!(
            fields[2] == report.analysis_context_sha256,
            "observation analysis context mismatch"
        );
        let site = sites.get(fields[3]).context("unknown observation site")?;
        ensure!(
            site.instrumentable,
            "observation site was not eligible for instrumentation"
        );
        let (lo, hi, _) =
            integer_type(&site.c_type).context("unsupported observation integer type")?;
        let value: i128 = fields[4].parse().context("invalid observation integer")?;
        ensure!(
            value.to_string() == fields[4] && (lo..=hi).contains(&value),
            "observation integer is noncanonical or outside its C type"
        );
        records += 1;
        ensure!(records <= 1_000_000, "observation record limit exceeded");
        let entry = observations.entry(site.id.as_str()).or_insert(Samples {
            count: 0,
            min: value,
            max: value,
            zero: u64::MAX >> (64 - domains[site.id.as_str()].bits),
            one: u64::MAX >> (64 - domains[site.id.as_str()].bits),
            distinct: BTreeSet::new(),
            distinct_complete: true,
            outside_domain: false,
        });
        entry.count += 1;
        entry.min = entry.min.min(value);
        entry.max = entry.max.max(value);
        entry.zero &= !(value as u64);
        entry.one &= value as u64;
        entry.outside_domain |= !domains[site.id.as_str()].contains(value);
        if entry.distinct.len() < 256 {
            entry.distinct.insert(value);
        } else if !entry.distinct.contains(&value) {
            entry.distinct_complete = false;
        }
    }
    ensure!(records > 0, "no NVCompact observation records found");
    let comparisons = observed_comparisons(report, &observations)?;
    let mut rows = Vec::new();
    for (id, samples) in observations {
        let (min, max) = (samples.min, samples.max);
        let site = sites[id];
        let static_min: i128 = site
            .minimum
            .parse()
            .context("invalid static range minimum")?;
        let static_max: i128 = site
            .maximum
            .parse()
            .context("invalid static range maximum")?;
        let outside = min < static_min || max > static_max;
        let suggestion = if samples.outside_domain {
            Some("Recorded values contradict the reported static interval. Check source, dependencies, instrumentation build and analysis assumptions before considering any rewrite.".into())
        } else if min >= 0 && max <= 1 {
            Some(format!("Samples at this use contain only 0/1. If that domain is established for every execution reaching the use, inspect `{0} == 1` -> `{0}` or `{0} != 1` -> `!{0}` in truth contexts, and redundant masks. Preserve result type in value contexts.", site.symbol))
        } else if min == max {
            Some(format!("This use observed only {min}. Investigate a path invariant or specialization; finite samples do not justify replacing the read with a constant."))
        } else {
            None
        };
        rows.push(Observation {
            site_id: id,
            location: &site.location,
            symbol: &site.symbol,
            function: &site.function,
            c_type: &site.c_type,
            operation: &site.operation,
            samples: samples.count,
            minimum: min.to_string(),
            maximum: max.to_string(),
            outside_static_range: outside,
            outside_static_domain: samples.outside_domain,
            static_membership_scope: if site.domain.as_ref().is_some_and(|d| d.values_omitted > 0) {
                "interval and known bits; omitted finite-set holes are not checked"
            } else {
                "reported interval, known bits and complete listed finite set when present"
            },
            observed_known_zero: format!("0x{:x}", samples.zero),
            observed_known_one: format!("0x{:x}", samples.one),
            distinct_values: samples
                .distinct
                .into_iter()
                .map(|v| v.to_string())
                .collect(),
            distinct_values_complete: samples.distinct_complete,
            assurance: "observed-samples-only",
            suggestion,
            requirements: vec![
                "Establish the full reachable domain independently before shortening.",
                "Preserve C promotions, result type, evaluation count, side effects and binding.",
                "Measure the complete final artifact after a separately reviewed change.",
            ],
        });
    }
    Ok(
        json!({"format_version":2,"advisory_only":true,"assurance":"observed-samples-only",
        "source_sha256":report.source_sha256,"analysis_context_sha256":report.analysis_context_sha256,
        "trace_sha256":sha256(trace),"records":records,"ignored_lines":ignored_lines,
        "observed_sites":rows,"unobserved_sites":report.ranges.len()-rows.len(),
        "nversion":comparisons,
        "coverage_complete":false,"static_ranges_changed":false,
        "scope":"Finite diagnostic samples, potentially quota-limited or interrupted. No claim of all paths, all values, program equivalence, performance, or actual packed-byte savings."}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn report() -> AdviceReport {
        serde_json::from_value(json!({"format_version":1,"advisory_only":true,
            "source_sha256":sha256(b"int f(int x){return x;}"),
            "analysis_context_sha256":"a".repeat(64),"frontend":{},"statistics":{},
            "findings":[],"ranges":[{"id":"range:20:21","location":{"start":20,"end":21,"line":1,"column":21},
                "function":"f","symbol":"x","expression":"x","c_type":"int",
                "minimum":"-2147483648","maximum":"2147483647","basis":[],"operation":"return",
                "instrumentable":true}],"limitations":[],"complete":true})).unwrap()
    }

    fn record(report: &AdviceReport, value: &str) -> String {
        format!(
            "{TRACE_PREFIX}\t{}\t{}\trange:20:21\t{value}\n",
            report.source_sha256, report.analysis_context_sha256
        )
    }

    #[test]
    fn c_profile_contract_rejects_other_language_reports() {
        for language in ["cpp", "rust", "python"] {
            let mut report = report();
            report.frontend["language"] = json!(language);
            assert!(observe(&report, b"").is_err());
            assert!(instrument(
                b"int f(int x){return x;}",
                &report,
                &InstrumentOptions::default()
            )
            .is_err());
        }
        let mut report = report();
        report.language_details = Some(json!({"adapter":"other-language"}));
        assert!(observe(&report, b"").is_err());
    }

    #[test]
    fn samples_never_narrow_static_facts_and_mismatches_fail() {
        let report = report();
        let before = serde_json::to_vec(&report).unwrap();
        let trace = format!(
            "other stderr\n{}{}",
            record(&report, "0"),
            record(&report, "1")
        );
        let result = observe(&report, trace.as_bytes()).unwrap();
        assert_eq!(result["records"], 2);
        assert_eq!(result["observed_sites"][0]["minimum"], "0");
        assert_eq!(result["observed_sites"][0]["maximum"], "1");
        assert_eq!(
            result["observed_sites"][0]["assurance"],
            "observed-samples-only"
        );
        assert_eq!(result["static_ranges_changed"], false);
        assert_eq!(before, serde_json::to_vec(&report).unwrap());
        assert!(observe(
            &report,
            trace
                .replace(&report.analysis_context_sha256, &"b".repeat(64))
                .as_bytes()
        )
        .is_err());
        assert!(observe(
            &report,
            trace
                .replace(&report.source_sha256, &"c".repeat(64))
                .as_bytes()
        )
        .is_err());
        assert!(observe(&report, record(&report, "2147483648").as_bytes()).is_err());
        assert!(observe(&report, record(&report, "00").as_bytes()).is_err());
        let incomplete = record(&report, "123");
        assert!(observe(&report, incomplete[..incomplete.len() - 2].as_bytes()).is_err());
        assert!(observe(&report, incomplete[..incomplete.len() - 1].as_bytes()).is_err());
        assert!(observe(&report, incomplete.as_bytes()).is_ok());
        assert!(observe(&report, b"no samples").is_err());
    }

    #[test]
    fn diagnostic_source_is_separate_bounded_and_single_read() {
        let report = report();
        let source = b"int f(int x){return x;}";
        let output = instrument(
            source,
            &report,
            &InstrumentOptions {
                max_sites: 1,
                max_samples: 3,
            },
        )
        .unwrap();
        let edited = String::from_utf8(output.source).unwrap();
        assert!(edited.contains("_signed(0,(long long)(x))"));
        assert_eq!(output.manifest["max_samples_per_process"], 3);
        assert_eq!(output.manifest["instrumented_sites"], 1);
        assert_eq!(source, b"int f(int x){return x;}");
        let mut report = report;
        report.ranges[0].instrumentable = false;
        assert!(instrument(source, &report, &InstrumentOptions::default()).is_err());
        report.ranges[0].instrumentable = true;
        report.ranges[0].location.start = 19;
        assert!(instrument(source, &report, &InstrumentOptions::default()).is_err());
    }

    #[test]
    fn wide_unsigned_samples_are_exact_and_contradictions_visible() {
        let mut report = report();
        report.ranges[0].c_type = "unsigned long long".into();
        report.ranges[0].minimum = "0".into();
        report.ranges[0].maximum = "1".into();
        let result = observe(&report, record(&report, "18446744073709551615").as_bytes()).unwrap();
        assert_eq!(
            result["observed_sites"][0]["maximum"],
            "18446744073709551615"
        );
        assert_eq!(result["observed_sites"][0]["outside_static_range"], true);
        assert!(observe(&report, record(&report, "-1").as_bytes()).is_err());
        assert!(observe(&report, record(&report, "18446744073709551616").as_bytes()).is_err());
    }
}
