#!/usr/bin/env python3
"""Focused real-AST source fixtures; no native compiler or engine execution."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():
        parser.error("new absolute output required")
    prepared = args.prepared.resolve()
    source_report = json.loads((prepared / "prepare.json").read_bytes())
    if not source_report["complete"]:
        raise ValueError("source preparation was not complete")
    base = prepared / "inputs/engines/scripts"
    for name in ("rename_c.py", "fixed_shipping_alpha.py"):
        relative = "engines/scripts/" + name
        raw = (base / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source_report["inputs"][relative]["sha256"]:
            raise ValueError("pure helper input changed")
    config = module(prepared / "producer-prepare.py", "private_test_config")
    sys.path.insert(0, str(config.LIB))
    from clang import cindex
    cindex.Config.set_library_file(str(config.LIB / "clang/native/libclang.so"))
    lexer = module(base / "rename_c.py", "private_test_lexer")
    opaque = module(base / "fixed_shipping_alpha.py", "private_test_opaque")
    renamer = module(prepared / "producer-rename.py", "private_test_renamer")
    arguments = ["-x", "c", "-std=c11", "-resource-dir", str(config.RESOURCE)]
    cases = []
    def run(name, source, check):
        output, meta = renamer.propose(source, cindex=cindex, arguments=arguments,
            lexer=lexer, opaque=opaque, filename="fixture.c")
        check(output, meta)
        if source != bytes(source) or not meta["reparsed_binding_and_shape_equal"]:
            raise ValueError("source/binding fixture invariant failed")
        cases.append({"case": name, "passed": True, "mapping": meta["mapping"],
                      "AST_signature_sha256": meta["AST_signature_sha256"]})
    def require(value):
        if not value:
            raise AssertionError("fixture expectation failed")
    run("static forward declaration and recursive direct calls", b"static int recurse(int);static int recurse(int n){return n?recurse(n-1):0;}int main(void){return recurse(2);}",
        lambda output, meta: require(set(meta["mapping"]) == {"recurse"} and len(meta["edits"]) == 4))
    run("external/main function spellings remain", b"int public_api(void){return 2;}static int private_helper(void){return public_api();}int main(void){return private_helper();}",
        lambda output, meta: require(set(meta["mapping"]) == {"private_helper"} and b"public_api" in output and b"main" in output))
    run("address-taken static excluded without special name list", b"static int callback(int n){return n;}int main(void){int(*f)(int)=callback;return f(2);}",
        lambda output, meta: require(not meta["mapping"] and any("address/argument" in reason for row in meta["functions"] for reason in row["excluded"])))
    run("constructor implicit consumer excluded", b"static void initialize(void)__attribute__((constructor));static void initialize(void){}int main(void){return 0;}",
        lambda output, meta: require(not meta["mapping"]))
    run("same-spelled automatic local conservatively excludes function", b"static int selected(void){return 1;}int other(void){int selected=2;return selected;}int main(void){return selected()+other();}",
        lambda output, meta: require(not meta["mapping"]))
    run("macro consumer preserved and excluded", b"#define INVOKE hidden\nstatic int hidden(void){return 1;}int main(void){return INVOKE();}",
        lambda output, meta: require(not meta["mapping"] and output.startswith(b"#define INVOKE hidden\n")))
    run("own function name observation excluded", b"static const char*observed(void){return __func__;}int main(void){return !observed();}",
        lambda output, meta: require(not meta["mapping"]))
    run("protocol string and comment exact despite same function spelling", b"/* command */static int command(void){return 1;}int main(void){const char*s=\"command\";return command()+*s;}",
        lambda output, meta: require(set(meta["mapping"]) == {"command"} and b'"command"' in output and b"/* command */" in output))
    run("macro declaration identity survives source-offset changes", b"#define BEFORE 1\nstatic int long_name(void){return BEFORE;}\n#define AFTER 2\nint main(void){return long_name()+AFTER;}",
        lambda output, meta: require(set(meta["mapping"]) == {"long_name"}))
    for label, source, message in (
        ("symbol observer", b"int dlsym;int main(void){return 0;}", "observer"),
        ("non-ASCII source", "int café;".encode(), "ASCII"),
        ("real AST syntax error", b"static int broken( {", "diagnostics"),
    ):
        try:
            renamer.propose(source, cindex=cindex, arguments=arguments, lexer=lexer, opaque=opaque)
        except ValueError as error:
            require(message in str(error))
            cases.append({"case": "reject " + label, "passed": True})
        else:
            raise AssertionError("expected guarded rejection")
    args.out.mkdir(parents=True)
    report = {"complete": True, "scope": __doc__, "cases": cases, "case_count": len(cases),
              "native_compiles": 0, "codec_calls": 0, "engine_executions": 0,
              "prepared_receipt_sha256": hashlib.sha256((prepared / "prepare.json").read_bytes()).hexdigest(),
              "tested_renamer": source_report["producer"]["rename.py"]}
    raw = (json.dumps(report, indent=2) + "\n").encode()
    (args.out / "tests.json").write_bytes(raw)
    print(json.dumps({"passed": len(cases), "receipt_sha256": hashlib.sha256(raw).hexdigest()}))


if __name__ == "__main__":
    main()
