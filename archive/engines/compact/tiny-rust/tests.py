"""Compile and exercise Tiny Rust A without placing artifacts in the checkout.

This runner tests real Rust programs and the existing independent development
process oracle. Production uses tiny-rust-stream/tcec_build.py and the explicit
TCEC verifier class, whose finite protocol and process exit differ from the
development lifecycle. No throughput, strength or target scaling is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRODUCTION = ("main.rs", "board.rs", "search.rs", "runtime.rs")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def execute(command, cwd, path, *, env=None, timeout=180):
    process = subprocess.run([str(v) for v in command], cwd=cwd, env=env,
                             text=True, capture_output=True, timeout=timeout)
    evidence = {"command": [str(v) for v in command], "cwd": str(cwd),
                "returncode": process.returncode, "stdout": process.stdout,
                "stderr": process.stderr}
    write_json(path, evidence)
    if process.returncode:
        raise AssertionError(f"command failed ({process.returncode}); see {path}")
    return evidence


def load_builder():
    spec = importlib.util.spec_from_file_location("tiny_rust_validation_build", HERE / "build.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUILDER_FIXTURE = r'''#![allow(dead_code)]
#[cfg(tiny_dev)] fn unused_dev() { panic!("development only"); }
#[cfg(test)] fn unused_test() { panic!("test only"); }
#[cfg(not(tiny_dev))] fn chosen() -> i32 { 7 }
#[cfg(tiny_dev)] fn chosen() -> i32 { 13 }
struct Record {
    #[cfg(tiny_dev)] dev: i32,
    #[cfg(all(not(tiny_dev), not(test)))] ship: i32,
    common: i32,
}
fn main() {
    let record = Record {
        #[cfg(tiny_dev)] dev: 3,
        #[cfg(all(not(tiny_dev), not(test)))] ship: 5,
        common: 11,
    };
    let mut n = 17;
    #[cfg(tiny_dev)] { n += record.dev; }
    #[cfg(all(not(tiny_dev), not(test)))] { n += record.ship; }
    #[cfg(not(test))]
    #[allow(unused_mut)]
    let mut common = record.common;
    #[cfg(any(tiny_dev, test))] { common += 19; }
    // #[cfg(tiny_dev)] fn not_a_declaration() { broken }
    let text = r##"#[cfg(tiny_dev)] } /* not syntax */"##;
    println!("{}:{}:{}:{}", chosen(), n, common, text.len());
}
'''


def builder_contract(builder, rustc, out, env):
    """Compare actual executions before/after cfg pruning, including fields."""
    fixtures = out / "builder"
    fixtures.mkdir()
    inputs = {name: b"" for name in PRODUCTION}
    inputs["main.rs"] = BUILDER_FIXTURE.encode()
    inputs["dev.rs"] = b"// this entire file must not ship\n"
    frozen = dict(inputs)
    results = []
    for development, expected in ((False, "7:22:11:35\n"), (True, "13:20:30:35\n")):
        transformed, metadata = builder.specialize(inputs, development=development)
        assert inputs == frozen, "specialize mutated its input mapping"
        assert ("dev.rs" in transformed) == development, "DEV file admission is incorrect"
        name = "dev" if development else "shipping"
        local = fixtures / name
        local.mkdir()
        source = local / "main.rs"
        source.write_bytes(transformed["main.rs"])
        original = local / "original.rs"
        original.write_text(BUILDER_FIXTURE, encoding="utf-8")
        outputs = []
        for label, path in (("original", original), ("specialized", source)):
            binary = local / (label + (".exe" if os.name == "nt" else ""))
            command = [rustc, path, "--edition=2024", "-O", "-o", binary]
            if development:
                command.extend(["--cfg", "tiny_dev"])
            execute(command, local, local / f"{label}-compile.json", env=env)
            actual = execute([binary], local, local / f"{label}-run.json", env=env)["stdout"]
            outputs.append(actual)
        assert outputs == [expected, expected], (name, outputs, expected)
        results.append({"profile": name, "output": outputs[0], "metadata": metadata})
    bad = dict(inputs)
    bad["main.rs"] = b"#[cfg(unrecognized)] fn hidden() {}\nfn main(){}\n"
    try:
        builder.specialize(bad, development=False)
    except (ValueError, RuntimeError):
        pass
    else:
        raise AssertionError("unknown cfg must fail closed")
    bad["main.rs"] = b"fn main(){#[cfg(tiny_dev)] if true {panic!(\"dev\");} println!(\"ship\");}\n"
    try:
        builder.specialize(bad, development=False)
    except (ValueError, RuntimeError):
        pass
    else:
        raise AssertionError("unsupported cfg-controlled expression must fail closed")
    illegal = dict(inputs)
    illegal["tests/private.rs"] = b"#[test] fn never_ship(){}"
    try:
        builder.specialize(illegal, development=False)
    except (ValueError, RuntimeError):
        pass
    else:
        raise AssertionError("test inputs must not be admitted into runtime archive")
    return {"passed": True, "fixtures": results,
            "unknown_cfg_rejected": True, "unsupported_cfg_expression_rejected": True, "test_input_rejected": True,
            "input_mapping_unchanged": True}


def copy_sources(destination, files):
    destination.mkdir(parents=True)
    for name, data in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def clock_contract(binary, out, env):
    """Keep stdin open: EOF/stop must not conceal an unbounded clock bug."""
    local = out / "clock-regression"
    local.mkdir()
    cases = []
    for side in ("white", "black"):
        moving, other = ("wtime", "btime") if side == "white" else ("btime", "wtime")
        position = "position startpos" + (" moves e2e4" if side == "black" else "")
        for label, value in (("malformed", "garbage"), ("negative", "-1"),
                             ("overflow", "18446744073709551616"), ("missing", None), ("zero", "0")):
            command = (f"go {other} 300000 {moving}" if value is None
                       else f"go {moving} {value} {other} 300000")
            transcript = []
            events = queue.Queue()
            process = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, bufsize=1, cwd=out, env=env)
            def reader(pipe, stream):
                for line in pipe:
                    events.put((stream, line.rstrip("\r\n"), time.monotonic()))
                events.put((stream, None, time.monotonic()))
            threads = [threading.Thread(target=reader, args=(process.stdout, "stdout"), daemon=True),
                       threading.Thread(target=reader, args=(process.stderr, "stderr"), daemon=True)]
            for thread in threads:
                thread.start()
            received_bytes = 0
            def receive(prefix, deadline):
                nonlocal received_bytes
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise AssertionError(f"{side}/{label}: no {prefix!r} before deadline with stdin open")
                    try:
                        stream, line, instant = events.get(timeout=remaining)
                    except queue.Empty:
                        raise AssertionError(f"{side}/{label}: no {prefix!r} before deadline with stdin open") from None
                    transcript.append({"at": instant, "stream": stream, "line": line})
                    if line is not None:
                        received_bytes += len(line.encode("utf-8"))
                    if received_bytes > 8 * 1024 * 1024:
                        raise AssertionError("clock regression output bound exceeded")
                    if stream == "stdout" and line is None:
                        raise AssertionError(f"{side}/{label}: process exited before {prefix}")
                    if stream == "stdout" and line.startswith(prefix):
                        return line, instant
            def send(text):
                instant = time.monotonic()
                transcript.append({"at": instant, "stream": "stdin", "line": text})
                process.stdin.write(text + "\n")
                process.stdin.flush()
                return instant
            evidence = {"side": side, "case": label, "command": command, "passed": False,
                        "no_stop_or_eof_before_bestmove": True, "maximum_wait_seconds": 8}
            try:
                send("uci")
                receive("uciok", time.monotonic() + 8)
                send("isready")
                receive("readyok", time.monotonic() + 8)
                send(position)
                started = send(command)
                line, completed = receive("bestmove ", started + 8)
                move = line.split()[1]
                # This oracle has no Tiny Rust imports and validates the move.
                spec = importlib.util.spec_from_file_location("tiny_clock_oracle", ROOT / "engines/tests/chess_oracle.py")
                oracle = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = oracle
                spec.loader.exec_module(oracle)
                board = oracle.Board.from_fen()
                if side == "black":
                    board = board.play("e2e4")
                assert move in {str(m) for m in board.legal_moves()}, f"illegal clock result {move}"
                send("quit")
                assert process.wait(timeout=2) == 0, "clock regression quit was abnormal"
                evidence.update(passed=True, bestmove=move, elapsed_seconds=completed-started,
                                returncode=process.returncode)
            except Exception as error:
                evidence["error"] = f"{type(error).__name__}: {error}"
                raise
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=2)
                process.stdin.close()
                for thread in threads:
                    thread.join(timeout=2)
                while not events.empty():
                    stream, line, instant = events.get_nowait()
                    transcript.append({"at": instant, "stream": stream, "line": line})
                evidence["transcript"] = transcript
                write_json(local / f"{side}-{label}.json", evidence)
            cases.append({k: v for k, v in evidence.items() if k != "transcript"})
    result = {"passed": True, "cases": cases, "program_sha256": digest(binary.read_bytes())}
    write_json(local / "results.json", result)
    return result


def main():
    raise SystemExit("Rust A is retired; this historical test CLI no longer builds or runs Rust A.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rustc", default=os.environ.get("RUSTC", "rustc"))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--tt-bits", type=int, default=10)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--suite", choices=("all", "builder", "unit", "process"), default="all")
    args = parser.parse_args()
    out = args.out.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error("--out must be outside the checkout")
    if not 1 <= args.workers <= 512 or not 8 <= args.tt_bits <= 26:
        parser.error("invalid fixed startup resources")
    out.mkdir(parents=True, exist_ok=False)
    rustc = shutil.which(args.rustc)
    if rustc is None:
        parser.error(f"rustc unavailable: {args.rustc}")
    env = dict(os.environ, ROVE_WORKERS=str(args.workers), ROVE_TT_BITS=str(args.tt_bits))
    sources = {name: (HERE / name).read_bytes() for name in (*PRODUCTION, "dev.rs")}
    hashes = {name: digest(data) for name, data in sources.items()}
    report = {"schema": 1, "scope": "actual Tiny Rust A builder, semantic units and tiny_dev process checks",
              "production_process_validation": {"executed_here": False,
                  "producer": "engines/experiments/tiny-rust-stream/tcec_build.py",
                  "verifier": "engines/experiments/tcec-scope/verify.py",
                  "class": "tcec-full-Rust-A-v1"},
              "excluded": ["strength", "NPS", "large-machine scaling", "4KiB eligibility"],
              "platform": sys.platform, "configuration": {"workers": args.workers, "tt_bits": args.tt_bits},
              "inputs": hashes, "checks": {}, "passed": False}
    write_json(out / "report.json", report)
    try:
        builder = load_builder()
        version = execute([rustc, "--version", "--verbose"], out, out / "rustc.json", env=env)
        report["rustc"] = version["stdout"]
        if args.suite in ("all", "builder"):
            report["checks"]["builder"] = builder_contract(builder, rustc, out, env)
        if args.suite in ("all", "unit"):
            unit_sources = dict(sources)
            for path in sorted((HERE / "tests").glob("*.rs")):
                unit_sources["tests/" + path.name] = path.read_bytes()
            local = out / "unit"
            copy_sources(local, unit_sources)
            binary = local / ("unit-tests.exe" if os.name == "nt" else "unit-tests")
            execute([rustc, local / "main.rs", "--edition=2024", "--test", "--cfg", "tiny_dev",
                     "-C", "opt-level=z", "-C", "lto=fat", "-C", "codegen-units=1",
                     "-o", binary], local, local / "compile.json", env=env)
            execution = execute([binary, "--test-threads=1", "--nocapture"], local,
                                local / "run.json", env=env)
            report["checks"]["unit"] = {"passed": True, "program_sha256": digest(binary.read_bytes()),
                                          "stdout": execution["stdout"]}
        if args.suite in ("all", "process"):
            # Optional stop/reset/final-result contracts belong to tiny_dev.
            # The separate production verifier exercises the minimum TCEC class.
            for development in (True,):
                name = "dev" if development else "shipping"
                output_files, metadata = builder.specialize(sources, development=development)
                assert ("dev.rs" in output_files) == development
                assert all(not p.startswith("tests/") for p in output_files)
                local = out / name
                copy_sources(local, output_files)
                binary = local / ("native.exe" if os.name == "nt" else "native")
                command = [rustc, local / "main.rs", "--edition=2024", "-C", "opt-level=z",
                           "-C", "panic=abort", "-C", "codegen-units=1", "-C", "lto=fat", "-o", binary]
                if development:
                    command.extend(["--cfg", "tiny_dev"])
                execute(command, local, local / "compile.json", env=env)
                manifest = {"engines": [{"id": "TinyRustA-" + name, "command": [str(binary)],
                            "cwd": str(local), "profile": name,
                            "workers": args.workers, "max_threads": args.workers + 1,
                            "startup_threads": args.workers + 1,
                            "expected_program_sha256": digest(binary.read_bytes())}]}
                write_json(local / "manifest.json", manifest)
                command = [sys.executable, "-B", ROOT / "engines/tests/verify.py", "--manifest",
                           local / "manifest.json", "--out", local / "process", "--plies", "12"]
                if not development:
                    command.extend(["--suite", "shipping"])
                if args.quick:
                    command.append("--quick")
                execute(command, local, local / "process-run.json", env=env, timeout=300)
                actual = json.loads((local / "process/results.json").read_text(encoding="utf-8"))
                assert actual["passed"]
                clocks = None if development else clock_contract(binary, local, env)
                report["checks"][name] = {"passed": True, "specialization": metadata,
                     "program_sha256": digest(binary.read_bytes()),
                     "source_files": {p: digest(data) for p, data in output_files.items()},
                     "results": str(local / "process/results.json"), "clock_regression": clocks}
        assert hashes == {name: digest((HERE / name).read_bytes()) for name in sources}, "inputs changed during validation"
        report["passed"] = True
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        write_json(out / "report.json", report)
    print(out / "report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
