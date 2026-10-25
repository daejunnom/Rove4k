//! The cleanup frontend is a proof boundary, not a text-name unused counter.
use nvcompact::{
    ccleanup::{self, CleanupOptions},
    cflow::CFlowOptions,
    process,
};
use std::fs;

fn options(language: &str) -> Option<CleanupOptions> {
    let clang = std::env::var("NVCOMPACT_CLANG").unwrap_or_else(|_| "clang".into());
    if process::resolve_tool(&clang).is_err() {
        eprintln!("cleanup integration not executed: provide NVCOMPACT_CLANG");
        return None;
    }
    Some(CleanupOptions {
        language: language.into(),
        frontend: CFlowOptions {
            clang,
            standard: if language == "cpp" {
                "c++17".into()
            } else {
                "c11".into()
            },
            token_contract: "no-token-observation".into(),
            ..Default::default()
        },
        ..Default::default()
    })
}

#[test]
fn compiler_references_keep_recursive_groups_callbacks_and_exported_roots() {
    let Some(options) = options("c") else {
        return;
    };
    let source = b"static int leaf(void){return 11;}static int isolated(void){return leaf();}static int even(int);static int odd(int n){return n?even(n-1):0;}static int even(int n){return n?odd(n-1):1;}static int callback(int n){return n+1;}int (*handler)(int)=callback;static int helper(void){return 3;}int exported(void){return helper();}int main(void){return handler(2)!=exported();}\n";
    let variants = ccleanup::generate_variants(source, &options).unwrap();
    let changed = variants
        .iter()
        .find(|v| v.id == "cleanup-functions")
        .unwrap_or_else(|| panic!("{variants:#?}"));
    let text = std::str::from_utf8(&changed.data).unwrap();
    assert!(!text.contains("isolated"));
    assert!(text.contains("leaf"));
    let next = ccleanup::generate_variants(&changed.data, &options).unwrap();
    let next = next.iter().find(|v| v.id == "cleanup-functions").unwrap();
    assert!(!std::str::from_utf8(&next.data).unwrap().contains("leaf"));
    assert!(text.contains("even") && text.contains("odd"));
    assert!(text.contains("callback") && text.contains("helper") && text.contains("exported"));
    assert_eq!(
        ccleanup::replay_variant(source, changed, &options)
            .unwrap()
            .data,
        changed.data
    );
    let mut forged = changed.clone();
    forged.audit[0]["start"] = serde_json::json!(1);
    assert!(ccleanup::replay_variant(source, &forged, &options).is_err());
}

#[test]
fn attributes_assembly_and_macro_declarations_do_not_become_dead_text() {
    let Some(options) = options("c") else {
        return;
    };
    for source in [
        "static int main(void){return 0;}",
        "static void __attribute__((constructor)) init(void){}int main(void){return 0;}",
        "static void __attribute__((used)) retained(void){}int main(void){return 0;}",
        "static int hidden(void){return 1;}int main(void){__asm__(\"call hidden\");return 0;}",
        "#define DECL static int hidden(void){return 1;}\nDECL\nint main(void){return 0;}",
    ] {
        let variants = ccleanup::generate_variants(source.as_bytes(), &options).unwrap();
        assert_eq!(variants.len(), 1, "must retain: {source}: {variants:#?}");
    }
}

#[test]
fn cpp_free_function_subset_keeps_initializers_constructors_and_overloads() {
    let Some(options) = options("cpp") else {
        return;
    };
    let source = b"static int state;static int tick(){return ++state;}static int unused(){return 9;}static int initialized=tick();struct Init{Init(){tick();}};static Init instance;static int f(int n){return n;}static int f(double n){return (int)n+1;}int main(){return f(1)+state;}\n";
    let variants = ccleanup::generate_variants(source, &options).unwrap();
    let changed = variants
        .iter()
        .find(|v| v.id == "cleanup-functions")
        .unwrap_or_else(|| panic!("{variants:#?}"));
    let text = std::str::from_utf8(&changed.data).unwrap();
    assert!(!text.contains("unused") && !text.contains("double"));
    assert!(text.contains("tick") && text.contains("instance") && text.contains("f(int"));
    let template = b"static int target(){return 1;}template<class T>int f(T t){return t()+target();}int main(){return f(target);}";
    assert_eq!(
        ccleanup::generate_variants(template, &options)
            .unwrap()
            .len(),
        1
    );
}

#[test]
fn includes_require_expanded_tokens_and_pragmas_to_remain_identical() {
    for language in ["c", "cpp"] {
        let Some(mut options) = options(language) else {
            return;
        };
        let directory = tempfile::tempdir().unwrap();
        fs::write(directory.path().join("unused.h"), "#define UNUSED 19\n").unwrap();
        fs::write(directory.path().join("used.h"), "#define USED 7\n").unwrap();
        fs::write(directory.path().join("pragma.h"), "#pragma pack(push,1)\n").unwrap();
        fs::write(
            directory.path().join("declaration.h"),
            "extern volatile int observed;\n",
        )
        .unwrap();
        let source = b"#include \"unused.h\"\n#include \"used.h\"\n#include \"pragma.h\"\n#include \"declaration.h\"\nstruct X{char a;int b;};int main(void){return USED+sizeof(struct X);}\n";
        let path = directory.path().join(if language == "cpp" {
            "source.cpp"
        } else {
            "source.c"
        });
        fs::write(&path, source).unwrap();
        options.frontend.source_path = Some(path);
        let variants = ccleanup::generate_variants(source, &options).unwrap();
        assert_eq!(variants.len(), 2, "{variants:#?}");
        let text = std::str::from_utf8(&variants[1].data).unwrap();
        assert!(!text.contains("unused.h"));
        assert!(
            text.contains("used.h") && text.contains("pragma.h") && text.contains("declaration.h")
        );
    }
}

#[test]
fn individually_redundant_headers_are_not_assumed_jointly_redundant() {
    let Some(mut options) = options("c") else {
        return;
    };
    let directory = tempfile::tempdir().unwrap();
    for header in ["first.h", "second.h"] {
        fs::write(
            directory.path().join(header),
            "#ifndef VALUE\n#define VALUE 7\n#endif\n",
        )
        .unwrap();
    }
    let source = b"#include \"first.h\"\n#include \"second.h\"\nint main(void){return VALUE;}\n";
    let path = directory.path().join("source.c");
    fs::write(&path, source).unwrap();
    options.frontend.source_path = Some(path);
    let variants = ccleanup::generate_variants(source, &options).unwrap();
    assert_eq!(variants.len(), 3, "{variants:#?}");
    assert!(!variants.iter().any(|v| v.id == "cleanup-includes"));
}

#[test]
fn language_and_source_observation_contracts_are_explicit() {
    for language in ["rust", "python", "javascript"] {
        let options = CleanupOptions {
            language: language.into(),
            ..Default::default()
        };
        assert!(format!(
            "{:#}",
            ccleanup::generate_variants(b"", &options).unwrap_err()
        )
        .contains("unsupported"));
    }
    let variants = ccleanup::generate_variants(
        b"static int unused(void){return 1;}",
        &CleanupOptions::default(),
    )
    .unwrap();
    assert_eq!(variants.len(), 1);
    assert!(variants[0].notes[0].contains("non-observation"));
}

#[test]
fn cpp_cli_exports_selected_candidate_and_actual_native_bytes_stay_equal() {
    let Some(options) = options("cpp") else {
        return;
    };
    let compiler = std::env::var("CXX").unwrap_or_else(|_| "c++".into());
    if process::resolve_tool(&compiler).is_err() {
        eprintln!("C++ native proof not executed: provide CXX");
        return;
    }
    let directory = tempfile::tempdir().unwrap();
    let source=b"static int state;static void tick(){++state;}static int unused(){return 19;}struct Init{Init(){tick();}};static Init instance;int main(){return state!=1;}\n";
    let input = directory.path().join("source.cpp");
    fs::write(&input, source).unwrap();
    let output = directory.path().join("selected.cpp");
    let portfolio = directory.path().join("portfolio");
    let argv = vec![
        env!("CARGO_BIN_EXE_nvcompact").into(),
        "cleanup-source".into(),
        input.to_string_lossy().into_owned(),
        "--language".into(),
        "cpp".into(),
        "--token-contract".into(),
        "no-token-observation".into(),
        "--clang".into(),
        options.frontend.clang,
        "--output".into(),
        output.to_string_lossy().into_owned(),
        "--variant".into(),
        "cleanup-functions".into(),
        "--portfolio".into(),
        portfolio.to_string_lossy().into_owned(),
    ];
    let result = process::run(&argv, b"", directory.path(), &process::Limits::default()).unwrap();
    assert_eq!(
        result.code,
        0,
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    let changed = fs::read(output).unwrap();
    assert!(!std::str::from_utf8(&changed).unwrap().contains("unused"));
    let compile = vec![
        compiler,
        "-x".into(),
        "c++".into(),
        "-".into(),
        "-std=c++17".into(),
        "-Os".into(),
        "-s".into(),
        "-fno-ident".into(),
        "-Wl,--build-id=none".into(),
        "-o".into(),
        "{output}".into(),
    ];
    let mut images = Vec::new();
    let mut diagnostics = Vec::new();
    for data in [source.as_slice(), changed.as_slice()] {
        let mut command = compile.clone();
        *command.last_mut().unwrap() = directory
            .path()
            .join("native")
            .to_string_lossy()
            .into_owned();
        let result = process::run(
            &command,
            data,
            directory.path(),
            &process::Limits::default(),
        )
        .unwrap();
        assert_eq!(
            result.code,
            0,
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        images.push(fs::read(directory.path().join("native")).unwrap());
        diagnostics.push((result.stdout, result.stderr));
    }
    assert_eq!(images[0], images[1]);
    assert_eq!(diagnostics[0], diagnostics[1]);
}

#[test]
fn include_proof_replays_with_a_new_frontend_temporary_path() {
    let Some(mut options) = options("c") else {
        return;
    };
    let directory = tempfile::tempdir().unwrap();
    fs::write(directory.path().join("empty.h"), "#define UNUSED 1\n").unwrap();
    let source = b"#include \"empty.h\"\nconst char *location=__FILE__;int main(void){return 0;}\n";
    let path = directory.path().join("source.c");
    fs::write(&path, source).unwrap();
    options.frontend.source_path = Some(path);
    let variants = ccleanup::generate_variants(source, &options).unwrap();
    assert_eq!(variants.len(), 2, "{variants:#?}");
    assert_eq!(
        ccleanup::replay_variant(source, &variants[1], &options)
            .unwrap()
            .data,
        variants[1].data
    );
}

#[test]
fn hidden_type_dependencies_are_roots_in_both_languages() {
    for (language, source) in [
        ("cpp", "static constexpr bool f(int){return true;}static constexpr bool f(...){return false;}void g() noexcept(f(0)){}int main(){return f(\"\")||noexcept(g());}"),
        ("cpp", "static int state;static int f(int){state=1;return 2;}static int f(...){state=2;return 3;}int main(){f(\"\");int a[f(0)];return state;}"),
        ("c", "static int state;static int f(void){state++;return 2;}void g(int a[f()]){}int main(void){int a[2];g(a);return state;}"),
        ("c", "static int state;static int f(void){state++;return 2;}int main(void){int a[f()];return state;}"),
        ("cpp", "static int f(int){return 1;}static double f(...){return 2;}decltype(f(0)) value;int main(){return f(\"\")+value;}"),
        ("cpp", "static int f(){return 2;}int g(int n=f()){return n;}int main(){return g();}"),
        ("cpp", "static constexpr int f(){return 8;}alignas(f()) int value;int main(){return value;}"),
    ] {
        let Some(options)=options(language) else {return;};
        let variants=ccleanup::generate_variants(source.as_bytes(),&options).unwrap();
        assert_eq!(variants.len(),1,"must retain hidden binding: {source}: {variants:#?}");
        assert_eq!(variants[0].data,source.as_bytes());
    }
}

#[test]
fn source_location_builtins_disable_function_and_include_cleanup() {
    for (language, body) in [
        ("c", "int main(void){return __builtin_LINE()+__builtin_COLUMN();}"),
        ("cpp", "int current(int line=__builtin_LINE()){return line;}int main(){return current();}"),
        ("cpp", "#include <source_location>\nint main(){return std::source_location::current().line();}"),
    ] {
        let Some(mut options)=options(language) else {return;};
        if language=="cpp" {options.frontend.standard="c++20".into();}
        let directory=tempfile::tempdir().unwrap();
        fs::write(directory.path().join("empty.h"),"#define UNUSED 9\n").unwrap();
        let source=format!("#include \"empty.h\"\nstatic int unused(void){{\nreturn 7;\n}}\n{body}\n");
        let path=directory.path().join("source.c");fs::write(&path,&source).unwrap();options.frontend.source_path=Some(path);
        let variants=ccleanup::generate_variants(source.as_bytes(),&options).unwrap();
        assert_eq!(variants.len(),1,"{variants:#?}");
        assert!(variants[0].notes.iter().any(|s|s.contains("source-location")),"{variants:#?}");
    }
}
