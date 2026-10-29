"""Experimental source-JIT envelope with the compiler program compressed once.

This preserves packaging.SOURCE_CODE's entire temporary-directory, compiler,
open-before-unlink and fdexec suffix. Only bundle decoding moves outside that
program. A size observation is not admission, engine execution or 4K acceptance.
"""
import ast
import hashlib
import json
import lzma
from pathlib import Path


OUTER = '''import lzma,sys
exec(lzma.decompress(open(sys.argv[1],"rb").read()[PAYLOAD_OFFSET:]))'''
IMPORTS = "import os,tempfile,pathlib,subprocess\n"
ANCHOR = "with tempfile.TemporaryDirectory(prefix=\"rove4k-d-\") as d:\n"


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def package_source(files, flags, units, packaging):
    original = dict(files={n: files[n].decode() for n in sorted(files)},
                    flags=list(flags), units=list(units))
    # This deliberately accepts only JSON's string/list/dict subset, which is
    # also a Python literal. Never execute source-file text as Python code.
    if (any(not isinstance(s, str) for s in (*original["flags"], *original["units"])) or
            any(not isinstance(n, str) for n in original["files"])):
        raise ValueError("literal source bundle requires string keys and values")
    literal = json.dumps(original, separators=(",", ":"), ensure_ascii=True)
    if ast.literal_eval(literal) != original:
        raise ValueError("JSON/Python literal inverse differs")
    if packaging.SOURCE_CODE.count(ANCHOR) != 1:
        raise ValueError("unique original compiler/cleanup suffix required")
    suffix = ANCHOR + packaging.SOURCE_CODE.split(ANCHOR, 1)[1]
    program = (IMPORTS + "b=" + literal + "\n" + suffix).encode()
    tree = ast.parse(program)
    if (len(tree.body) != 4 or not isinstance(tree.body[0], ast.Import) or
            not isinstance(tree.body[1], ast.Assign) or
            ast.literal_eval(tree.body[1].value) != original or
            not isinstance(tree.body[2], ast.With) or
            not isinstance(tree.body[3], ast.Expr)):
        raise ValueError("compressed compiler program structure differs")
    payload = packaging.encode(program, "alone")
    if lzma.decompress(payload) != program:
        raise ValueError("compressed compiler program inverse differs")
    whole, header = packaging.envelope(OUTER, payload)
    return whole, dict(kind="D-compressed-source-bootstrap-v1", codec="alone",
                       header_bytes=len(header), payload_bytes=len(payload),
                       program=pin(program), compiler_cleanup_suffix=pin(suffix.encode()),
                       original_source_code=pin(packaging.SOURCE_CODE.encode()),
                       files={n: pin(d) for n, d in sorted(files.items())},
                       flags=list(flags), units=list(units),
                       cleanup="original all-paths-removed-before-fdexec suffix unchanged",
                       input_bundle_literal_inverted=True,
                       runtime_qualified=False, selected=False)


def main():
    import argparse
    import importlib.util
    import sys
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out, build = args.out.resolve(), args.build.resolve()
    if (not args.out.is_absolute() or out.exists() or
            any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("new absolute output outside Git required")
    manifest = (build / "build.json").read_bytes()
    control = json.loads(manifest)
    if not (control.get("complete") and control.get("frozen_execution") and
            control.get("family") == "D" and control.get("native_reproduced")):
        raise ValueError("complete frozen D source control required")
    packaging_name = "engines/experiments/tiny-d-submission/packaging.py"
    host_name = "engines/experiments/tcec-scope/build.py"
    frozen = {"bootstrap.py": Path(__file__).read_bytes(), "build.json": manifest}
    for name in (packaging_name, host_name):
        data = (build / "inputs" / name).read_bytes()
        if pin(data) != control["inputs"][name]:
            raise ValueError("named frozen control tool differs")
        frozen[name] = data
    files = {}
    for name, expected in control["shipping_inputs"].items():
        if name not in ("main.c", "board.c", "search.c", "runtime.c", "start.S", "image.ld"):
            raise ValueError("unknown D source unit")
        data = (build / "shipping-inputs" / name).read_bytes()
        if pin(data) != expected:
            raise ValueError("control shipping input differs")
        frozen["shipping-inputs/" + name] = files[name] = data
    out.mkdir()
    for name, data in frozen.items():
        path = out / "inputs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    frozen_self = load("D_compressed_bootstrap_frozen", out / "inputs/bootstrap.py")
    packaging = load("D_compressed_bootstrap_control", out / "inputs" / packaging_name)
    owner = load("D_compressed_bootstrap_owner", out / "inputs" / host_name)
    owner.LIMITS = {**owner.LIMITS, "aggregate_wall": 30, "parent_CPU": 20,
                    "parent_CPU_hard": 25}
    report = dict(kind="D-compressed-bootstrap-cost-v1", complete=False, commands=[],
                  inputs={n: pin(d) for n, d in frozen.items()},
                  resource=control["resource"], input_control_native=control["source_jit_native"],
                  native_compiled=False,
                  scope="exact compiler-program suffix and source-bundle inverse; no engine execution",
                  runtime_qualified=False, selected=False)
    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    host = owner.Host(out, report, save)
    try:
        original, _ = packaging.package_source(files, control["flags"], control["units"])
        controls = [row for row in control["candidates"] if row["representation"] == "source-jit"]
        if (len(controls) != 1 or
                pin(original) != {key: controls[0][key] for key in ("bytes", "sha256")}):
            raise ValueError("reconstructed source-JIT differs from recorded control artifact")
        whole, detail = frozen_self.package_source(files, control["flags"], control["units"], packaging)
        repeated, _ = frozen_self.package_source(files, control["flags"], control["units"], packaging)
        if whole != repeated:
            raise ValueError("compressed bootstrap reproduction differs")
        (out / "source-jit").write_bytes(whole)
        (out / "source-jit").chmod(0o755)
        report.update(original=pin(original), candidate=pin(whole), detail=detail,
                      whole_saving=len(original)-len(whole), package_reproduced=True, complete=True)
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        report["complete"] = False
        raise
    finally:
        try:
            host.close()
        except BaseException as error:
            report["complete"] = False
            report["cleanup_failure"] = dict(type=type(error).__name__, message=str(error))
            raise
        finally:
            if report.get("host_cleanup", {}).get("errors") or report.get("host_cleanup", {}).get("unsettled_commands"):
                report["complete"] = False
            save()
    print(json.dumps(dict(complete=report["complete"], original=len(original),
                          candidate=len(whole), whole_saving=report["whole_saving"])))


if __name__ == "__main__":
    main()
