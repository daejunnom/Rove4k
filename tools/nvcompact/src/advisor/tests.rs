use super::*;

fn options() -> Option<AdvisorOptions> {
    let clang = std::env::var("NVCOMPACT_CLANG").unwrap_or_else(|_| "clang".into());
    if crate::process::resolve_tool(&clang).is_err() {
        eprintln!("advisor frontend checks not executed: set NVCOMPACT_CLANG");
        return None;
    }
    Some(AdvisorOptions {
        clang,
        ..Default::default()
    })
}
fn report(source: &str) -> Option<AdviceReport> {
    let options = options()?;
    Some(analyze(source.as_bytes(), &options).unwrap())
}

#[test]
fn nversion_uses_entry_domains_and_mask_guards_do_not_invent_bounds() {
    let source = "int bounded(int to){if(to<0||to>127)return -1;return (to>>4)==0||(to>>4)==7;}\nint board(int to){if(to<0||to>127||(to&0x88))return -1;return (to>>4)==0||(to>>4)==7;}\nint mask_only(int to){if(to&0x88)return -1;return (to>>4)==0||(to>>4)==7;}";
    let Some(r) = report(source) else {
        return;
    };
    let target = |name| {
        r.expressions
            .iter()
            .find(|s| s.function == name && s.original == "(to>>4)==0||(to>>4)==7")
            .unwrap()
    };
    for (name, count) in [("bounded", 128), ("board", 64)] {
        let site = target(name);
        let comparison = site.comparison.as_ref().unwrap();
        assert_eq!(comparison.domain.values.len(), count);
        assert!(comparison
            .candidates
            .iter()
            .any(|c| c.source == "!(to+16&96)" && c.evidence.equivalent && c.evidence.complete));
        assert_eq!(
            comparison.domain.provenance,
            nversion::DomainProvenance::StaticConservative
        );
        let first_read = r
            .ranges
            .iter()
            .find(|s| Some(&s.id) == site.entry_site_id.as_ref())
            .unwrap();
        assert_eq!(first_read.minimum, "0");
        assert!(first_read.maximum.parse::<i128>().unwrap() <= 127);
    }
    let mask = target("mask_only");
    assert!(mask.comparison.is_none());
    assert!(mask.status.contains("too-large"));
    assert!(mask.static_domain.maximum.parse::<i128>().unwrap() >= 256);
}

#[test]
fn sparse_branch_results_survive_join_assignment_and_ternary_spelling() {
    let source = "int joined(int c){int x;if(c)x=1;else x=9;return x==1||x==9;}\nint selected(int c){int x=c?1:9;return x==1||x==9;}\nint guarded(int x){if(x==1||x==9)return x&7;return -1;}\nint replaced(int c){int x=c?1:9;x=256;return (x>>4)==0||(x>>4)==7;}";
    let Some(r) = report(source) else {
        return;
    };
    for name in ["joined", "selected"] {
        let site = r
            .expressions
            .iter()
            .find(|s| s.function == name && s.original == "x==1||x==9")
            .unwrap();
        assert_eq!(
            site.static_domain.values.as_deref(),
            Some(["1".to_owned(), "9".to_owned()].as_slice())
        );
        assert!(site
            .comparison
            .as_ref()
            .unwrap()
            .candidates
            .iter()
            .any(|c| c.source == "1"));
    }
    let guarded = r
        .expressions
        .iter()
        .find(|s| s.function == "guarded" && s.original == "x&7")
        .unwrap();
    assert_eq!(guarded.static_domain.finite_cardinality, Some(2));
    let replaced = r
        .expressions
        .iter()
        .find(|s| s.function == "replaced" && s.original == "(x>>4)==0||(x>>4)==7")
        .unwrap();
    assert_eq!(replaced.static_domain.values, Some(vec!["256".into()]));
    assert!(!replaced
        .comparison
        .as_ref()
        .unwrap()
        .candidates
        .iter()
        .any(|c| c.source == "!(x+16&96)"));
}

#[test]
fn finite_flow_and_search_budgets_are_explicit_and_never_narrow_by_sampling() {
    let Some(mut options) = options() else {
        return;
    };
    options.max_finite_flow_work = 1_000;
    options.max_nversion_work = 1_000;
    let source =
        "int f(int x){if(x<0||x>127)return -1;if((x&7)==3)return (x>>4)==0||(x>>4)==7;return x;}";
    let r = analyze(source.as_bytes(), &options).unwrap();
    assert!(r.statistics["finite_flow_budget_exhausted"]
        .as_bool()
        .unwrap());
    assert!(r.statistics["finite_flow_reserved_work"].as_u64().unwrap() <= 1_000);
    assert!(
        r.statistics["nversion_scalar_evaluations"]
            .as_u64()
            .unwrap()
            <= 1_000
    );
    assert!(!r.complete);
    assert_eq!(r.statistics["compression_candidates_created"], 0);
    assert_eq!(r.source_sha256, sha256(source.as_bytes()));
}

#[test]
fn profile_compares_full_entry_interval_and_keeps_outside_witnesses_conditional() {
    let source = "int rank(int to){return (to>>4)==0||(to>>4)==7;}";
    let Some(r) = report(source) else {
        return;
    };
    let target = r
        .expressions
        .iter()
        .find(|s| s.original == "(to>>4)==0||(to>>4)==7")
        .unwrap();
    let entry = target.entry_site_id.as_ref().unwrap();
    let trace = |site: &str, values: &[i128]| {
        values
            .iter()
            .map(|v| {
                format!(
                    "NVCOMPACT_ADVICE_V1\t{}\t{}\t{}\t{}\n",
                    r.source_sha256, r.analysis_context_sha256, site, v
                )
            })
            .collect::<String>()
    };
    let before = serde_json::to_vec(&r).unwrap();
    let observations =
        crate::advice_profile::observe(&r, trace(entry, &[0, 127]).as_bytes()).unwrap();
    let row = observations["nversion"]["expressions"]
        .as_array()
        .unwrap()
        .iter()
        .find(|s| s["expression_id"] == target.id)
        .unwrap();
    assert_eq!(
        row["comparison"]["domain"]["values"]
            .as_array()
            .unwrap()
            .len(),
        128
    );
    assert_eq!(
        row["comparison"]["domain"]["provenance"],
        "observed_closure"
    );
    assert!(row["comparison"]["candidates"]
        .as_array()
        .unwrap()
        .iter()
        .any(|c| c["source"] == "!(to+16&96)"));
    let outside = row["outside_domain_checks"]
        .as_array()
        .unwrap()
        .iter()
        .find(|c| c["candidate"] == "!(to+16&96)")
        .unwrap();
    assert!(outside["counterexamples"]
        .as_array()
        .unwrap()
        .iter()
        .any(|c| c["input"] == "128"));
    assert_eq!(before, serde_json::to_vec(&r).unwrap());
    let wider =
        crate::advice_profile::observe(&r, trace(entry, &[0, 135, 256]).as_bytes()).unwrap();
    let wider = wider["nversion"]["expressions"]
        .as_array()
        .unwrap()
        .iter()
        .find(|s| s["expression_id"] == target.id)
        .unwrap();
    assert!(!wider["comparison"]["candidates"]
        .as_array()
        .unwrap()
        .iter()
        .any(|c| c["source"] == "!(to+16&96)"));
    let rhs = target.read_site_ids.iter().find(|id| *id != entry).unwrap();
    let rhs_only = crate::advice_profile::observe(&r, trace(rhs, &[16, 127]).as_bytes()).unwrap();
    assert!(!rhs_only["nversion"]["expressions"]
        .as_array()
        .unwrap()
        .iter()
        .any(|s| s["expression_id"] == target.id));
}

#[test]
fn constants_use_clang_types_and_unused_references_include_function_addresses() {
    let source = "unsigned long long f(void){return 0x5555555555555555ULL+6148914691236517205ULL;}\nunsigned long g(void){return 0xffffffff+4294967295;}\nstatic int callback(int x){return x;} int (*keep)(int)=callback; static int never(void){return 1;}\nextern int side(void);int h(void){int unused=side();return 0;}";
    let Some(r) = report(source) else {
        return;
    };
    let groups: Vec<_> = r
        .findings
        .iter()
        .filter(|f| f.kind == "duplicate-constant")
        .collect();
    assert_eq!(groups.len(), 1);
    assert!(groups[0].message.contains("unsigned long long"));
    assert_eq!(groups[0].related_locations.len(), 1);
    assert!(r
        .findings
        .iter()
        .any(|f| f.kind == "no-reference" && f.symbol.as_deref() == Some("never")));
    assert!(!r
        .findings
        .iter()
        .any(|f| f.kind == "no-reference" && f.symbol.as_deref() == Some("callback")));
    let unused = r
        .findings
        .iter()
        .find(|f| f.symbol.as_deref() == Some("unused"))
        .unwrap();
    assert!(unused.suggestion.is_none());
    assert!(unused
        .requirements
        .iter()
        .any(|s| s.contains("initializer side effects")));
    assert!(r.advisory_only);
    assert_eq!(r.source_sha256, sha256(source.as_bytes()));
}

#[test]
fn ranges_are_per_read_and_reassignment_prevents_stale_boolean_advice() {
    let source =
        "int f(int x){int flag=x&1;if(flag==1){flag=2;if(flag==1)return 3;}return flag!=1;}";
    let Some(r) = report(source) else {
        return;
    };
    assert!(r
        .findings
        .iter()
        .any(|f| f.kind == "boolean-domain-comparison"
            && f.original == "flag==1"
            && f.suggestion.as_deref() == Some("flag")));
    assert!(r.findings.iter().any(|f| f.kind == "constant-comparison"
        && f.original == "flag==1"
        && f.suggestion.as_deref() == Some("0")));
    assert!(!r
        .findings
        .iter()
        .any(|f| f.kind == "boolean-domain-comparison" && f.original == "flag!=1"));
    let last = r
        .ranges
        .iter()
        .filter(|s| s.symbol == "flag")
        .last()
        .unwrap();
    assert_eq!((&*last.minimum, &*last.maximum), ("0", "2"));
    assert!(r
        .ranges
        .iter()
        .all(|s| s.instrumentable && &source[s.location.start..s.location.end] == s.expression));
}

#[test]
fn early_return_and_short_circuit_refine_operation_inputs() {
    let source = "int f(int x){if(x<0||x>1)return -1;return x==1;} int g(unsigned x){unsigned b=x&1;if(b==1)return 2;return b==1;}";
    let Some(r) = report(source) else {
        return;
    };
    assert!(r.findings.iter().any(|f| f.function.as_deref() == Some("f")
        && f.original == "x==1"
        && f.suggestion.as_deref() == Some("x")));
    // Unsigned values can replace an int comparison only in truth contexts.
    let g: Vec<_> = r
        .findings
        .iter()
        .filter(|f| f.function.as_deref() == Some("g") && f.kind == "boolean-domain-comparison")
        .collect();
    assert_eq!(g.len(), 1);
    assert_eq!(g[0].suggestion.as_deref(), Some("b"));
}

#[test]
fn loop_escape_volatile_and_shadow_boundaries_withhold_false_facts() {
    let source = "extern void mutate(int*);int f(int x){int flag=x&1;mutate(&flag);return flag==1;} int g(void){volatile int b=1;return b==1;} int h(void){int b=0;while(b<3){if(b==0)b++;else b+=2;}return b==0;} int s(int x){int b=x&1;{int b=x; if(b==1)return 7;}return b!=1;}";
    let Some(r) = report(source) else {
        return;
    };
    assert!(!r
        .ranges
        .iter()
        .any(|s| s.function == "f" && s.symbol == "flag"));
    assert!(!r.ranges.iter().any(|s| s.function == "g"));
    assert!(
        !r.findings.iter().any(|f| f.function.as_deref() == Some("h")
            && matches!(
                f.kind.as_str(),
                "constant-comparison" | "boolean-domain-comparison"
            ))
    );
    let s: Vec<_> = r
        .findings
        .iter()
        .filter(|f| f.function.as_deref() == Some("s") && f.kind == "boolean-domain-comparison")
        .collect();
    assert_eq!(s.len(), 1);
    assert_eq!(s[0].original, "b!=1");
    assert_eq!(s[0].suggestion.as_deref(), Some("!b"));
}

#[test]
fn negative_remainder_unsigned_wrap_and_boolean_types_keep_correct_domains() {
    let source = "int neg(int x){int b=x%2;return b==1;} int wrap(void){unsigned x=4294967295U;x+=1;return x==0;} typedef int bool;int named(bool x){return x==1;}int actual(_Bool x){if(x==1)return 1;return x==1;}";
    let Some(r) = report(source) else {
        return;
    };
    assert!(!r
        .findings
        .iter()
        .any(|f| f.function.as_deref() == Some("neg") && f.kind == "boolean-domain-comparison"));
    let neg = r
        .ranges
        .iter()
        .find(|s| s.function == "neg" && s.symbol == "b")
        .unwrap();
    assert_eq!((&*neg.minimum, &*neg.maximum), ("-1", "1"));
    assert!(r
        .findings
        .iter()
        .any(|f| f.function.as_deref() == Some("wrap") && f.suggestion.as_deref() == Some("1")));
    assert!(!r
        .findings
        .iter()
        .any(|f| f.function.as_deref() == Some("named") && f.kind == "boolean-domain-comparison"));
}

#[test]
fn compound_assignment_uses_clang_computation_types_before_narrowing() {
    let source = "int f(void){int x=-1;unsigned y=2;x/=y;return x==0;}int g(void){int x=-1;unsigned y=2;x%=y;return x==1;}";
    let Some(r) = report(source) else {
        return;
    };
    let f = r
        .ranges
        .iter()
        .find(|s| s.function == "f" && s.symbol == "x")
        .unwrap();
    assert_eq!((&*f.minimum, &*f.maximum), ("2147483647", "2147483647"));
    let g = r
        .ranges
        .iter()
        .find(|s| s.function == "g" && s.symbol == "x")
        .unwrap();
    assert_eq!((&*g.minimum, &*g.maximum), ("1", "1"));
    assert!(r
        .findings
        .iter()
        .any(|f| f.function.as_deref() == Some("f") && f.suggestion.as_deref() == Some("0")));
}

#[test]
fn write_only_diagnostics_preserve_rhs_effects_and_parenthesized_reads_are_sites() {
    let source =
        "extern int side(void);int f(int x){int unused=0;(unused)=side();int b=x&1;return (b)!=1;}";
    let Some(r) = report(source) else {
        return;
    };
    let warning = r
        .findings
        .iter()
        .find(|f| f.kind == "write-only-local")
        .unwrap();
    assert_eq!(warning.symbol.as_deref(), Some("unused"));
    assert!(warning.suggestion.is_none());
    assert!(warning
        .requirements
        .iter()
        .any(|s| s.contains("RHS side effects")));
    assert!(r
        .ranges
        .iter()
        .any(|s| s.symbol == "b" && s.expression == "b"));
}

#[test]
fn constant_comparisons_do_not_erase_potentially_undefined_arithmetic() {
    let source = "int f(int x,int y){return x/y<=2147483647;}int g(int x){return x+1<=2147483647;}int h(int x){if(x<0||x>10)return 0;return x+1<=2147483647;}";
    let Some(r) = report(source) else {
        return;
    };
    assert!(!r.findings.iter().any(
        |f| matches!(f.function.as_deref(), Some("f" | "g")) && f.kind == "constant-comparison"
    ));
    assert!(r
        .findings
        .iter()
        .any(|f| f.function.as_deref() == Some("h") && f.kind == "constant-comparison"));
}

#[test]
fn macro_locations_and_unevaluated_reads_are_not_instrumentable_sites() {
    let source = "#define READ(x) ((x)&1)\nint f(int x){int b=READ(x);(void)sizeof(b);return b==1;} int g(int x){return sizeof(x);}";
    let Some(r) = report(source) else {
        return;
    };
    assert!(!r.ranges.iter().any(|s| s.symbol == "x"));
    assert_eq!(r.ranges.iter().filter(|s| s.symbol == "b").count(), 1);
    assert!(r.ranges.iter().all(|s| s.expression == s.symbol));
}

#[test]
fn reachable_unknown_ternary_and_vla_sizeof_do_not_disappear_from_flow() {
    let source = "int f(int c){const int x=3;int v=c?x:0;return v==0;}int g(void){int n=0;sizeof(int[++n]);return n==0;}int h(void){int n=0;int a[++n];return n==0;}int t(void){int n=0;typedef int A[++n];return n==0;}";
    let Some(r) = report(source) else {
        return;
    };
    assert!(!r.findings.iter().any(|f| f.kind == "constant-comparison"));
    let v = r
        .ranges
        .iter()
        .find(|s| s.function == "f" && s.symbol == "v")
        .unwrap();
    assert_eq!((&*v.minimum, &*v.maximum), ("-2147483648", "2147483647"));
}

#[test]
fn report_budget_and_unsupported_control_flow_are_explicit() {
    let Some(mut options) = options() else {
        return;
    };
    options.max_ranges = 1;
    options.max_findings = 1;
    let source = b"int f(int x){int b=x&1;if(b==1)return b!=1;return b==1;}int g(int x){again: if(x--)goto again;return x==0;}";
    let r = analyze(source, &options).unwrap();
    assert!(!r.complete);
    assert!(r.statistics["range_sites_omitted"].as_u64().unwrap() > 0);
    assert_eq!(r.statistics["functions_withheld"], 1);
    assert!(!r.ranges.iter().any(|s| s.function == "g"));
}

#[test]
fn analysis_context_is_stable_between_sessions_but_tracks_header_content() {
    let Some(mut options) = options() else {
        return;
    };
    let directory = tempfile::tempdir().unwrap();
    let input = directory.path().join("input.c");
    let header = directory.path().join("range.h");
    let source = b"#include \"range.h\"\nint f(int x){int b=x&MASK;return b==1;}";
    std::fs::write(&input, source).unwrap();
    std::fs::write(&header, "#define MASK 1\n").unwrap();
    options.source_path = Some(input);
    let a = analyze(source, &options).unwrap();
    let b = analyze(source, &options).unwrap();
    assert_eq!(a.analysis_context_sha256, b.analysis_context_sha256);
    std::fs::write(&header, "#define MASK 3\n").unwrap();
    let c = analyze(source, &options).unwrap();
    assert_ne!(a.analysis_context_sha256, c.analysis_context_sha256);
    assert_eq!(a.source_sha256, c.source_sha256);
}

#[test]
fn suggested_site_edits_match_independent_native_execution_on_boundary_inputs() {
    let Some(options) = options() else {
        return;
    };
    let compiler = std::env::var("CC").unwrap_or_else(|_| "cc".into());
    let Ok(compiler) = crate::process::resolve_tool(&compiler) else {
        eprintln!("advisor native comparison not executed: provide CC");
        return;
    };
    let cases = [
        (
            "int f(int x){int b=x&1;return b!=1;}",
            "boolean-domain-comparison",
        ),
        (
            "int f(int x){if(x<0||x>31)return 0;return x&31;}",
            "redundant-mask",
        ),
        (
            "int f(int x){if(x<0||x>7)return 0;return x%8;}",
            "bounded-arithmetic",
        ),
        (
            "int f(int x){int b=(x<9);return b?1:0;}",
            "boolean-selection",
        ),
        (
            "int f(int x){if(x<0||x>1)return 7;return x==1;}",
            "boolean-domain-comparison",
        ),
    ];
    let mut program = String::new();
    for (i, (source, kind)) in cases.iter().enumerate() {
        let r = analyze(source.as_bytes(), &options).unwrap();
        let advice = r
            .findings
            .iter()
            .find(|f| f.kind == *kind)
            .expect("expected supported site suggestion");
        let mut edited = source.to_string();
        edited.replace_range(
            advice.location.start..advice.location.end,
            advice.suggestion.as_ref().unwrap(),
        );
        program += &source.replacen("int f(", &format!("int f{i}("), 1);
        program += &edited.replacen("int f(", &format!("int g{i}("), 1);
    }
    program += "int main(void){int edge[]={(-2147483647-1),-2147483647,-2,-1,0,1,2,7,8,9,31,32,2147483647};";
    for i in 0..cases.len() {
        program += &format!("for(int x=-100;x<=100;x++)if(f{i}(x)!=g{i}(x))return 1;for(unsigned j=0;j<sizeof(edge)/sizeof(*edge);j++)if(f{i}(edge[j])!=g{i}(edge[j]))return 2;");
    }
    program += "return 0;}";
    let dir = tempfile::tempdir().unwrap();
    let executable = dir.path().join("advice-comparison");
    let limits = crate::process::Limits {
        seconds: 10.0,
        memory_bytes: 512 << 20,
        output_bytes: 65536,
        cpu_seconds: 10,
        file_bytes: 2 << 20,
    };
    let argv = vec![
        compiler.to_string_lossy().into_owned(),
        "-std=c11".into(),
        "-O2".into(),
        "-x".into(),
        "c".into(),
        "-".into(),
        "-o".into(),
        executable.to_string_lossy().into_owned(),
    ];
    crate::process::run(&argv, program.as_bytes(), dir.path(), &limits)
        .unwrap()
        .check("advisor native comparison compile")
        .unwrap();
    crate::process::run(
        &[executable.to_string_lossy().into_owned()],
        b"",
        dir.path(),
        &limits,
    )
    .unwrap()
    .check("advisor native comparison execution")
    .unwrap();
}
