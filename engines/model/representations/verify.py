#!/usr/bin/env python3
"""Actual decoded coefficients and production C/Rust E inference regression.

Compile only after the shared compiler window is free. Test outputs and binaries
must stay outside the checkout. Packaging smoke/reproduction is a separate gate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from generate import FORMATS, ROOT, load_model, metadata, sources


def validate_formats(candidates, formats):
    if (not formats or len(set(formats)) != len(formats) or
            any(fmt not in FORMATS or fmt not in candidates for fmt in formats) or
            any(fmt not in FORMATS for fmt in candidates)):
        raise ValueError("unknown, duplicate or unavailable representation")


def validate_producer_metadata(record, fmt, language, model):
    expected = metadata(fmt, model)
    if not isinstance(record, dict) or record.get("language") != language:
        raise ValueError("producer representation language mismatch")
    for key in ("runtime_representation", "canonical_reference_sha256", "restored_i16le_sha256"):
        if record.get(key) != expected[key]:
            raise ValueError("producer representation identity mismatch: " + key)


def run(command, timeout=120, env=None):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=env)
    record = {"command": command, "exit_code": result.returncode,
              "stdout": result.stdout, "stderr": result.stderr}
    if result.returncode:
        raise RuntimeError(json.dumps(record))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--prepared", type=Path)
    inputs.add_argument("--build", type=Path, nargs="+", help="actual producer build.json reports")
    parser.add_argument("--formats", help="defaults to varint,static16 for prepared inputs or producer formats")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rustc", required=True)
    parser.add_argument("--fixtures-root", type=Path,
                        help="explicit frozen engines/tests/rust; copied only into validation trees")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.resolve().is_relative_to(ROOT) or args.out.exists():
        parser.error("--out must be new, absolute and outside checkout")
    model = load_model()
    build_inputs = []
    if args.prepared:
        prepared = json.loads(args.prepared.read_text())
        candidates = {c["runtime_representation"]: c for c in prepared["candidates"]}
        formats = args.formats.split(",") if args.formats else ["varint", "static16"]
    else:
        candidates = {}
        for path in args.build:
            data = path.read_bytes()
            build = json.loads(data)
            if not build.get("complete"):
                raise ValueError("actual producer build must be complete")
            fmt = build["model_format"]
            if fmt not in FORMATS:
                raise ValueError("unknown producer model format")
            if fmt in candidates:
                raise ValueError("duplicate producer model format")
            roots, manifests, representations, configurations = {}, {}, {}, {}
            for language in ("c", "rust"):
                engines = [e for e in build["engines"] if e["id"].split("-")[1] == language]
                if len(engines) != 1:
                    raise ValueError("producer report must select exactly one engine per language")
                engine = engines[0]
                roots[language] = str(Path(engine["command"][0]).parent)
                manifests[language] = engine["sources"]
                representations[language] = engine["model_representation"]
                validate_producer_metadata(representations[language], fmt, language, model)
                configurations[language] = engine["configuration"]
                for source in engine["sources"]:
                    name = source["path"].removeprefix("engines/")
                    if (not name.startswith(("c/", "rust/", "model/")) or "\\" in name or
                            ".." in Path(name).parts or Path(name).suffix not in (".c", ".h", ".rs")):
                        raise ValueError("producer manifest contains a non-production source path")
                    actual = (Path(roots[language]) / name).read_bytes()
                    if hashlib.sha256(actual).hexdigest() != source["sha256"]:
                        raise ValueError("actual producer source changed: " + name)
                header = "frozen.h" if language == "c" else "frozen.rs"
                actual_header = (Path(roots[language]) / "model" / header).read_text()
                if actual_header != sources(fmt, model)[header]:
                    raise ValueError("actual producer model header does not match its declared representation")
            candidates[fmt] = {"runtime_representation": fmt, "source_root_by_language": roots,
                               "producer_source_inputs": manifests,
                               "producer_model_representation": representations,
                               "producer_configuration": configurations}
            build_inputs.append({"path": str(path), "sha256": hashlib.sha256(data).hexdigest()})
        formats = args.formats.split(",") if args.formats else list(candidates)
    validate_formats(candidates, formats)
    weights = model["evaluation"]["weights"] + model["ordering"]["weights"]
    expected = ",".join(map(str, weights))
    report = {"scope": "actual production model consumer and exact coefficient tests",
              "complete": False, "representations": [], "producer_build_inputs": build_inputs}
    fixtures = {}
    if args.fixtures_root:
        for path in sorted(args.fixtures_root.glob("*.rs")):
            fixtures[path.name] = path.read_bytes()
        if not fixtures:
            raise ValueError("explicit Rust fixture directory has no .rs fixtures")
    report["rust_fixture_inputs"] = [{"path": str(args.fixtures_root / name),
                                      "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                                     for name, data in fixtures.items()]
    args.out.mkdir(parents=True)
    try:
        for fmt in formats:
            candidate = candidates[fmt]
            by_language = candidate.get("source_root_by_language", {})
            source = Path(by_language.get("c", candidate.get("source_root", "")))
            rust_source = Path(by_language.get("rust", candidate.get("source_root", "")))
            directory = args.out / fmt
            directory.mkdir()
            configurations = candidate.get("producer_configuration", {})
            c_configuration = configurations.get("c", {"ROVE_VARIANT": "E", "ROVE_MODEL": "0"})
            variant = c_configuration["ROVE_VARIANT"]
            if variant not in ("C", "E") or (variant == "C" and c_configuration.get("ROVE_MODEL") != "1"):
                raise ValueError("producer verification requires E or explicit C+E")
            c_source = f'''#include <assert.h>
#include <string.h>
#include <stdio.h>
#define ROVE_VARIANT {ord(variant) - ord('A') + 1}
#define ROVE_MODEL {int(c_configuration.get('ROVE_MODEL', '0'))}
#include {json.dumps(str(source / "c/model.h"), ensure_ascii=False)}
static void kings(int b[128]){{memset(b,0,128*sizeof(int));b[4]=6;b[116]=-6;}}
int main(void){{
 const int16_t expected[21]={{{expected}}};rove_model_init();
 for(int i=0;i<21;i++)assert(rove_model_weights[i]==expected[i]);
 int b[128];kings(b);b[52]=1;assert(rove_model_eval(b,1)==132);assert(rove_model_eval(b,-1)==-112);
 b[68]=1;assert(rove_model_eval(b,1)==248);
 kings(b);b[51]=b[52]=1;assert(rove_model_eval(b,1)==270);
 kings(b);b[0]=b[7]=3;assert(rove_model_eval(b,1)==694);
 for(int q=0;q<128;q++){{b[q]=(q&136)?0:5;}}b[0]=6;b[55]=-6;
 assert(rove_model_eval(b,1)==20000);assert(rove_model_eval(b,-1)==-20000);
 assert(rove_model_order(1,-1,68,83,0)==1502);
 assert(rove_model_order(1,0,96,112,5)==9602);
 assert(rove_model_order(1,-4,96,113,5)==17504);
 assert(rove_model_order(6,-1,4,19,0)==1602);
 puts("exact21coefficients/production C evaluation/ordering/clamp pass");return 0;
}}
'''
            c_path = directory / "check.c"
            c_path.write_text(c_source)
            record = {"representation": fmt, "model": candidates[fmt]}
            report["representations"].append(record)
            record["c_compile"] = run(["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                                       "-fsanitize=address,undefined", str(c_path), "-o", str(directory / "c-check")])
            record["c_runtime"] = run([str(directory / "c-check")])
            # Test-only includes are resolved relative to a separate validation
            # tree. Neither producer inputs nor runtime archives acquire fixtures.
            validation = directory / "validation-sources"
            producer = {}
            for folder in ("rust", "model"):
                for path in sorted((rust_source / folder).glob("*.rs")):
                    name = path.relative_to(rust_source).as_posix()
                    producer[name] = path.read_bytes()
            if any(b'../tests/rust/' in data for data in producer.values()) and not fixtures:
                raise ValueError("current production sources require explicit --fixtures-root")
            for name, data in producer.items():
                path = validation / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            for name, data in fixtures.items():
                path = validation / "tests/rust" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            record["rust_producer_inputs"] = [{"path": str(rust_source / name),
                                               "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                                              for name, data in producer.items()]
            rust = f'''#[path={json.dumps(str(validation / "rust/board.rs"), ensure_ascii=False)}]mod board;
#[path={json.dumps(str(validation / "rust/eval.rs"), ensure_ascii=False)}]mod eval;
#[path={json.dumps(str(validation / "model/frozen.rs"), ensure_ascii=False)}]mod frozen;
#[test]fn exact_restored_coefficients(){{assert_eq!(frozen::model_weights(),[{expected}]);}}
fn main(){{}}
'''
            rust_path = directory / "check.rs"
            rust_path.write_text(rust)
            rust_configuration = configurations.get("rust", {"ROVE_VARIANT": "E", "ROVE_MODEL": "0"})
            env = dict(os.environ, ROVE_VARIANT=rust_configuration["ROVE_VARIANT"],
                       ROVE_MODEL=rust_configuration.get("ROVE_MODEL", "0"))
            record["rust_compile"] = run([args.rustc, "--edition=2021", "--test", str(rust_path),
                                          "-o", str(directory / "rust-check")], env=env)
            record["rust_runtime"] = run([str(directory / "rust-check"), "--test-threads=2"], env=env)
            print(fmt + ": exact coefficients + C/Rust production model inference pass", flush=True)
        report["complete"] = True
    except Exception as error:
        report["failure"] = str(error)
        raise
    finally:
        (args.out / "verification.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
