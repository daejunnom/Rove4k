//! C++ language admission and native type/value checks on owned, bounded inputs.
use nvcompact::{
    advisor::{self, AdviceReport, AdvisorOptions, SourceLanguage},
    process::{self, Limits},
};
use serde_json::Value;
use std::fs;

fn options(standard: &str) -> Option<AdvisorOptions> {
    let clang = std::env::var("NVCOMPACT_CLANG").unwrap_or_else(|_| "clang".into());
    if process::resolve_tool(&clang).is_err() {
        eprintln!("C++ advisor integration not executed: set NVCOMPACT_CLANG");
        return None;
    }
    Some(AdvisorOptions {
        clang,
        standard: standard.into(),
        ..AdvisorOptions::default()
    })
}

fn analyze(source: &str, options: &AdvisorOptions) -> AdviceReport {
    advisor::analyze_source(source.as_bytes(), SourceLanguage::Cpp, options).unwrap()
}

fn sites(report: &AdviceReport) -> &[Value] {
    report.language_details.as_ref().unwrap()["expressions"]
        .as_array()
        .unwrap()
}

#[test]
fn real_cpp_modes_find_generic_rank_masks_inside_namespaces_and_linkage_contexts() {
    let source = r#"
namespace ranks {
bool rank128(int to) { if(to<0||to>127) return false; return (to>>4)==0||(to>>4)==7; }
bool rank64(int x) { if(x<0||x>63) return false; return (x>>3)==0||(x>>3)==7; }
}
extern "C" { int arithmetic(int x) { if(x<0||x>7) return 0; return x+0; } }
"#;
    for standard in ["c++17", "c++20"] {
        let Some(options) = options(standard) else {
            return;
        };
        let report = analyze(source, &options);
        assert_eq!(report.frontend["language"], "c++");
        assert_eq!(report.statistics["functions_analyzed"], 3);
        assert_eq!(report.statistics["functions_withheld"], 0);
        assert!(
            report.expressions.is_empty(),
            "C carrier must not be advertised as C++ IR"
        );
        assert!(report.ranges.iter().all(|r| !r.instrumentable));
        for (function, expected) in [("rank128", "!(to+16&96)"), ("rank64", "!(x+8&48)")] {
            let found = report.findings.iter().find(|f| {
                f.function.as_deref() == Some(function) && f.suggestion.as_deref() == Some(expected)
            });
            assert!(
                found.is_some(),
                "missing {function}: {expected}: {report:#?}"
            );
            let site = sites(&report)
                .iter()
                .find(|s| {
                    s["function"] == function && s["original"].as_str().unwrap().contains("||")
                })
                .unwrap();
            assert_eq!(site["result_type"], "bool");
            assert_eq!(site["value_category"], "prvalue");
        }
        assert_eq!(report.statistics["source_modified"], false);
        assert_eq!(report.statistics["compression_candidates_created"], 0);
    }
}

#[test]
fn cpp_boolean_type_and_prvalue_category_survive_every_retained_native_candidate() {
    let Some(options) = options("c++20") else {
        return;
    };
    let cxx = std::env::var("CXX").unwrap_or_else(|_| "c++".into());
    if process::resolve_tool(&cxx).is_err() {
        eprintln!("native C++ oracle not executed: set CXX");
        return;
    }
    let source = r#"
bool rank(int x) { if(x<0||x>127) return false; return (x>>4)==0||(x>>4)==7; }
bool normalized(int x) { if(x<0||x>1) return false; return x==1; }
int promoted(int x) { if(x<0||x>1) return 0; return (x==1)+0; }
bool chosen(int x) { if(x<0||x>1) return false; return x?true:false; }
int arithmetic(int x) { if(x<0||x>7) return 0; return x+0; }
int glvalue(int x) { if(x<0||x>1) return 0; return x?x:x; }
"#;
    let report = analyze(source, &options);
    assert!(!sites(&report)
        .iter()
        .any(|s| s["function"] == "glvalue" && s["original"] == "x?x:x"));
    assert!(!report
        .findings
        .iter()
        .any(|f| f.original == "x==1" && f.suggestion.as_deref() == Some("x")));
    let mut native = String::from("int main(){\n");
    let mut comparisons = 0;
    for site in sites(&report) {
        let Some(candidates) = site["comparison"]["candidates"].as_array() else {
            continue;
        };
        let lo: i128 = site["static_domain"]["minimum"]
            .as_str()
            .unwrap()
            .parse()
            .unwrap();
        let hi: i128 = site["static_domain"]["maximum"]
            .as_str()
            .unwrap()
            .parse()
            .unwrap();
        let original = site["original"].as_str().unwrap();
        for candidate in candidates {
            let proposed = candidate["source"].as_str().unwrap();
            native.push_str(&format!("{{int x=0; static_assert(__is_same(decltype(({original})),decltype(({proposed}))),\"surface type/category\"); for(x={lo};x<={hi};++x)if(({original})!=({proposed}))return 1;}}\n"));
            comparisons += 1;
        }
    }
    assert!(
        comparisons >= 4,
        "expected meaningful native coverage, got {comparisons}"
    );
    native.push_str("return 0;}\n");
    let directory = tempfile::tempdir().unwrap();
    fs::write(directory.path().join("oracle.cpp"), native).unwrap();
    let executable = directory.path().join("oracle");
    let limits = Limits {
        seconds: 30.0,
        cpu_seconds: 30,
        memory_bytes: 1 << 30,
        output_bytes: 1 << 20,
        file_bytes: 8 << 20,
    };
    let built = process::run(
        &[
            cxx,
            "-x".into(),
            "c++".into(),
            "-std=c++20".into(),
            "-fsanitize=undefined".into(),
            "-fno-sanitize-recover=undefined".into(),
            "oracle.cpp".into(),
            "-o".into(),
            executable.to_string_lossy().into_owned(),
        ],
        b"",
        directory.path(),
        &limits,
    )
    .unwrap();
    built
        .check("native C++ type/category oracle compilation")
        .unwrap();
    let executed = process::run(
        &[executable.to_string_lossy().into_owned()],
        b"",
        directory.path(),
        &limits,
    )
    .unwrap();
    executed
        .check("native C++ complete-domain value oracle")
        .unwrap();
    assert!(executed.stderr.is_empty());
}

#[test]
fn unsupported_cpp_bindings_and_semantics_withhold_whole_functions() {
    let Some(options) = options("c++20") else {
        return;
    };
    let source = r#"
int overloaded(int x){return x+0;}
long overloaded(long x){return x+0L;}
template<class T>T templated(T x){return x+0;}
struct Box { int value; bool method(int x){return x==1;} operator bool()const{return value;} };
bool conversion(Box x){return x;}
int reference(int x){int &r=x; r=5; return x==0;}
int pointer(int *p){return *p+0;}
int named(int x){return static_cast<int>(x)+0;}
bool boolean(bool x){return x==true;}
int volatile_read(volatile int x){return x+0;}
int external; int global_read(int x){return x+external;}
int pure(int x){if(x<0||x>7)return 0; return x+0;}
"#;
    let report = analyze(source, &options);
    assert_eq!(report.statistics["functions_analyzed"], 1);
    assert!(report.statistics["functions_withheld"].as_u64().unwrap() >= 10);
    assert!(sites(&report).iter().all(|s| s["function"] == "pure"));
    let withheld = report.language_details.as_ref().unwrap()["withheld_functions"]
        .as_array()
        .unwrap();
    for name in [
        "overloaded",
        "templated",
        "method",
        "conversion",
        "reference",
        "pointer",
        "named",
        "boolean",
        "volatile_read",
        "global_read",
    ] {
        assert!(
            withheld.iter().any(|f| f["function"] == name),
            "missing reason for {name}: {withheld:#?}"
        );
    }
}

#[test]
fn c_entry_remains_c_only_and_cpp_defined_extensions_are_explicitly_withheld() {
    let Some(options) = options("c++20") else {
        return;
    };
    let error = advisor::analyze(b"int f(int x){return x+0;}", &options).unwrap_err();
    assert!(error.to_string().contains("supported C standards"));
    let report = analyze(
        "bool negative(int x){if(x < -2 || x > -1)return false; return (x>>1)==-1;}",
        &options,
    );
    let shift = sites(&report)
        .iter()
        .find(|s| s["original"] == "(x>>1)==-1")
        .unwrap();
    assert_eq!(shift["status"], "outside-common-defined-integer-model");
    assert!(shift["comparison"]["candidates"]
        .as_array()
        .unwrap()
        .is_empty());
    assert!(report
        .limitations
        .iter()
        .any(|l| l.contains("even where a C++ version specifies a value")));
}
