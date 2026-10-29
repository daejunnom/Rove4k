#!/usr/bin/env python3
"""Two bounded actual-wrapper ownership/output-fence witnesses, not a suite.

Shipping stop/infinite are deliberately unused. Four clocked epochs per session
cover replacement, transactional new-position publication, an immediately
replaced zero-clock job, and active quit or EOF. Work before a signal and output
after it are observations; cancellation causality stays unproven.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import re
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
NATIVE = "6d9a3c192078f22914e17a0332ef2f0dbd134050833c1fceb0ccb221ecba34e2"
LONG = "go wtime 300000 btime 300000 winc 0 binc 0"
ZERO = "go wtime 0 btime 0 winc 0 binc 0"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def argument(script, owner, method):
    calls = [item for item in ast.walk(ast.parse(script)) if isinstance(item, ast.Call)
             and len(item.args) == 1 and isinstance(item.func, ast.Attribute)
             and isinstance(item.func.value, ast.Name) and item.func.value.id == owner
             and item.func.attr == method]
    require(len(calls) == 1, "expected one literal source/compiler call")
    return calls[0].args[0]


def literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return node.value
    if (isinstance(node, ast.Call) and not node.args and not node.keywords
            and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)):
        if node.func.attr == "encode":
            return node.func.value.value.encode()
        if node.func.attr == "split":
            return node.func.value.value.split()
    raise ValueError("unexpected source/compiler expression")


def erase_source(script):
    node = argument(script, "p", "communicate")
    starts = [0] + [match.end() for match in re.finditer(rb"\r\n|\r|\n", script)]
    begin = starts[node.lineno - 1] + node.col_offset
    end = starts[node.end_lineno - 1] + node.end_col_offset
    return script[:begin] + b"b'SOURCE'" + script[end:]


def survivors(engine):
    found = []
    for pid, started in engine.descendants.items():
        try:
            fields = (Path("/proc") / str(pid) / "stat").read_text().rpartition(") ")[2].split()
            if fields[19] == started and fields[0] != "Z":
                found.append(pid)
        except OSError:
            pass
    return found


def batch(engine, commands):
    require(engine.process.poll() is None, "engine exited before queued replacement")
    stamp = time.monotonic() - engine.start
    for command in commands:
        engine.record("stdin", command)
        engine.sent_times[command.split()[0]] = stamp
    engine.record("atomic_input_batch", {"commands": commands, "posted_seconds": stamp})
    engine.process.stdin.write("\n".join(commands) + "\n")
    engine.process.stdin.flush()
    return stamp


def active(engine, verifier, epoch):
    before = verifier.process_cpu_ticks(engine)
    started = time.monotonic()
    lines = engine.quiet(0.04)
    after = verifier.process_cpu_ticks(engine)
    ticks = None if before is None or after is None else after - before
    if not any(line.startswith("bestmove ") for line in lines) and not (ticks is not None and ticks > 0):
        lines += engine.quiet(0.06)
        after = verifier.process_cpu_ticks(engine)
        ticks = None if before is None or after is None else after - before
    require(not any(line.startswith("bestmove ") for line in lines), "epoch completed before its replacement/exit witness")
    require(ticks is not None and ticks > 0, "active epoch work was not observed")
    engine.assert_threads_stable()
    return {"epoch": epoch, "unfinished_with_observed_work": True,
            "cpu_ticks_delta": ticks, "observation_seconds": time.monotonic() - started,
            "cancellation_causality": "unproven",
            "scope": "whole-process CPU observed while no result was received; no internal worker preemption claim"}


def run_session(label, frozen, output, native, verifier, oracle):
    directory = output / label
    directory.mkdir()
    result = {"name": label, "passed": False, "forced_cleanup": [], "epochs": [], "activity": []}
    engine = None
    try:
        class TracedEngine(verifier.Engine):
            def terminate(self):
                if self.process.poll() is None:
                    result["forced_cleanup"].append({"action": "kill-owned-process-group",
                        "pid": self.process.pid, "basis": "failure cleanup is never acceptance"})
                return super().terminate()
        executable = frozen / "program/x"
        spec = {"id": "ownership-" + label, "command": [str(executable)],
                "cwd": str(executable.parent), "profile": "shipping", "workers": 2,
                "startup_threads": 3, "startup_timeout": 60}
        engine = TracedEngine(spec, directory, "actual", 5)
        engine.initialize()
        engine.assert_threads_stable()
        pid = engine.process.pid
        proc = Path("/proc") / str(pid)
        actual = (proc / "exe").read_bytes()
        require(actual == native and sha(actual) == NATIVE, "restored native image differs")
        image_link = os.readlink(proc / "exe")
        require(image_link.endswith("/x (deleted)"), "native fd-exec did not use removed x")
        temporary = Path(image_link.removesuffix(" (deleted)")).parent
        require(not temporary.exists(), "compiler directory remains after UCI-ready")
        state = dict(line.split(":", 1) for line in (proc / "status").read_text().splitlines())
        require(int(state["Pid"]) == pid and int(state["PPid"]) == os.getpid(), "wrapper parent remains")
        children = (proc / "task" / str(pid) / "children").read_text().strip()
        require(not children, "compiler children remain after UCI-ready")
        (directory / "actual-native").write_bytes(actual)
        result["identity"] = {"launched_pid": pid, "native_pid": int(state["Pid"]),
            "parent_pid": int(state["PPid"]), "actual_native_sha256": sha(actual),
            "same_pid_fd_exec": True, "executable_link": image_link,
            "startup_thread_ids": sorted(engine.startup_task_ids), "startup_threads": 3,
            "startup_observation": "before first UCI input; exact TIDs retained at sampled phase boundaries",
            "compiler_children_after_uci_ready": [], "temporary_directory": str(temporary),
            "temporary_directory_absent_after_uci_ready": True,
            "filesystem_observation": "after_uci_ready",
            "cleanup_before_fd_exec_basis": "unchanged frozen bootstrap source ordering"}
        save(directory / "result.json", result)
        white = oracle.Board.from_fen()
        black = white.play("e2e4")
        boards = [white, white, black, black]
        engine.position()
        engine.send(LONG)
        result["activity"].append(active(engine, verifier, 1))
        engine.send(LONG)
        replacement = engine.sent_times["go"]

        def best(epoch, trigger, reason):
            lines = engine.until(lambda line: line.startswith("bestmove "), timeout=2)
            moves = [line.split()[1] for line in lines if line.startswith("bestmove ")]
            require(len(moves) == 1, "epoch output frame count differs")
            legal = sorted(str(move) for move in boards[epoch - 1].legal_moves())
            require(moves[0] in legal, "stale or illegal move for epoch " + str(epoch))
            receipts = [(stamp, line) for stamp, line in engine.stdout_events if line.startswith("bestmove ")]
            require(len(receipts) >= epoch, "result receipt timestamp missing")
            require(receipts[epoch - 1][0] > trigger, "result preceded its submitted replacement")
            result["epochs"].append({"epoch": epoch, "side": "white" if epoch < 3 else "black",
                "bestmove": moves[0], "legal_moves": legal, "trigger": reason,
                "trigger_posted_seconds": trigger, "bestmove_received_seconds": receipts[epoch - 1][0],
                "cancellation_causality": "unproven"})
        best(1, replacement, "clocked GO replacement")
        require(not any(line.startswith("bestmove ") for line in engine.ready()), "extra result before replacement readiness")
        result["activity"].append(active(engine, verifier, 2))
        queued = batch(engine, ["position startpos moves e2e4", ZERO, LONG])
        result["queued_commands"] = {"posted_seconds": queued,
            "commands": ["position startpos moves e2e4", ZERO, LONG],
            "scope": "one input flush; immediate cancellation submission, not proof of any specific worker schedule"}
        best(2, queued, "position cancels old white-root epoch")
        best(3, queued, "zero-clock black-root GO immediately followed by long GO")
        require(not any(line.startswith("bestmove ") for line in engine.ready()), "extra result before final active epoch")
        result["activity"].append(active(engine, verifier, 4))
        require(len([line for _, line in engine.stdout_events if line.startswith("bestmove ")]) == 3,
                "unexpected result before active exit")
        engine.assert_threads_stable()
        engine.close(eof=label == "eof")
        exit_signal = "EOF" if label == "eof" else "quit"
        trigger = engine.sent_times[exit_signal]
        received = [(stamp, line) for stamp, line in engine.stdout_events if line.startswith("bestmove ")]
        require(len(received) == 4, "session did not emit exactly one result for each of four epochs")
        move = received[3][1].split()[1]
        legal = sorted(str(candidate) for candidate in black.legal_moves())
        require(move in legal and received[3][0] > trigger, "active exit did not settle one legal new-root result")
        result["epochs"].append({"epoch": 4, "side": "black", "bestmove": move,
            "legal_moves": legal, "trigger": "active " + exit_signal,
            "trigger_posted_seconds": trigger, "bestmove_received_seconds": received[3][0],
            "cancellation_causality": "unproven"})
        require(engine.output_error is None and all(not reader.is_alive() for reader in engine.readers),
                "physical stdout/stderr reader EOF was not settled")
        require(not proc.exists() and not survivors(engine), "native PID or observed owned descendant survives")
        require(not result["forced_cleanup"], "forced cleanup cannot pass the session")
        result.update(passed=True, exactly_four_bestmoves=True, thread_ids_preserved=True,
            physical_stdout_stderr_eof=True, native_pid_absent_after_wait=True,
            observed_owned_descendants=sorted(engine.descendants), surviving_observed_owned_descendants=[],
            runtime_exitcode=engine.process.returncode, runtime_stderr=engine.stderr,
            transcript=str(engine.path), orphan_scope="native PID, observed owned descendants and post-handshake child sample")
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if engine is not None:
            try:
                if engine.process.poll() is None:
                    engine.terminate()
                elif not engine.log.closed:
                    engine.finish()
                result.update(runtime_exitcode=engine.process.returncode, runtime_stderr=engine.stderr,
                    observed_owned_descendants=sorted(engine.descendants),
                    surviving_observed_owned_descendants=survivors(engine))
                if result["forced_cleanup"] or result["surviving_observed_owned_descendants"]:
                    result["passed"] = False
            except Exception as error:
                result["passed"] = False
                result["cleanup_error"] = type(error).__name__ + ": " + str(error)
    save(directory / "result.json", result)
    return result


def prove(build, out):
    out = out.resolve()
    require(not out.exists() and out != REPO and REPO not in out.parents, "new external output required")
    out.mkdir(parents=True)
    frozen = out / "frozen"
    frozen.mkdir()
    proof = {"format": 1, "complete": False, "passed": False, "sessions": [], "frozen_sha256": {},
        "scope": "two sessions, four clocked epochs each; physical output/ownership/reset witnesses",
        "limits_seconds": {"startup": 60, "response_or_exit": 5, "result_after_replacement": 2},
        "excluded": ["stop/infinite shipping commands", "generic full shipping suite", "games", "NPS/Elo",
            "per-worker forced scheduling", "all-position correctness", "independent pre-input filesystem sample", "4KiB acceptance"]}
    save(out / "results.json", proof)
    try:
        build_bytes = build.read_bytes()
        report = json.loads(build_bytes)
        require(report["complete"] is True and report["resources"] ==
            {"workers": 2, "tt_bits": 18, "ply": 128, "dev_default": False}, "unexpected cost profile")
        forms = [form for form in report["forms"] if form["name"] == "candidate"]
        require(len(forms) == 1 and forms[0]["complete"] is True, "one complete candidate required")
        form = forms[0]
        require(form["native_sha256"] == NATIVE, "unexpected proof native class")
        program = build.parent / "candidate"
        source = (program / "main.c").read_bytes()
        native = Path(form["native_path"]).read_bytes()
        whole = Path(form["whole_path"]).read_bytes()
        script = (program / "bootstrap.py").read_bytes()
        readable = (program / "engine.c").read_bytes()
        require(sha(source) == form["source_sha256"] and len(source) == form["source_bytes"], "source changed")
        require(sha(native) == NATIVE and len(native) == form["native_bytes"], "native changed")
        require(sha(whole) == form["whole_sha256"] and len(whole) == form["whole_bytes"], "wrapper changed")
        require(sha(script) == form["bootstrap_sha256"] and sha(readable) == form["readable_sha256"], "bootstrap/readable changed")
        def freeze(name, data):
            path = frozen / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            proof["frozen_sha256"][name] = sha(data)
        freeze("proof.py", Path(__file__).read_bytes())
        freeze("build.json", build_bytes)
        for name in ("provenance.json", "validation-manifest.json", "readable.diff"):
            freeze(name, (build.parent / name).read_bytes())
        for key, metadata in report["inputs"].items():
            require(not Path(key).is_absolute() and ".." not in Path(key).parts, "unexpected producer input path")
            for spelling, hash_key in (("raw", "raw_sha256"), ("LF", "LF_sha256")):
                data = (build.parent / "inputs" / spelling / key).read_bytes()
                require(sha(data) == metadata[hash_key], "frozen producer input changed: " + key)
                freeze("producer/" + spelling + "/" + key, data)
        for name, data in (("x", whole), ("main.c", source), ("engine.c", readable),
                            ("bootstrap.py", script), ("native-reference", native)):
            freeze("program/" + name, data)
        (frozen / "program/x").chmod(0o755)
        for name in ("verify.py", "chess_oracle.py"):
            freeze("shared/" + name, (REPO / "engines/tests" / name).read_bytes())
        prefix = (frozen / "producer/LF/selected/launcher.sh").read_bytes()
        template = (frozen / "producer/LF/selected/bootstrap.py.in").read_bytes()
        require(whole.startswith(prefix) and len(prefix) == 75, "launcher prefix changed")
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        require(decoder.decompress(whole[len(prefix):]) == script and decoder.eof and not decoder.unused_data,
                "one exact bootstrap XZ stream required")
        require(literal(argument(script, "p", "communicate")) == source, "compiler stdin restoration changed")
        argv = literal(argument(script, "subprocess", "Popen"))
        require(argv == ["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"], "compiler argv changed")
        require(erase_source(script) == template.replace(b"__ROVE_SOURCE_LITERAL__", b"b'SOURCE'"),
                "bootstrap signal/wait/cleanup/fdexec skeleton changed")
        proof["package"] = {"whole_bytes": len(whole), "whole_sha256": sha(whole),
            "source_sha256": sha(source), "native_sha256": sha(native), "compiler_argv": argv,
            "bootstrap_sha256": sha(script), "source_restored_exactly": True,
            "bootstrap_skeleton_unchanged": True}
        save(out / "results.json", proof)
        oracle = module("chess_oracle", frozen / "shared/chess_oracle.py")
        verifier = module("ownership_runtime_engine", frozen / "shared/verify.py")
        for label in ("quit", "eof"):
            result = run_session(label, frozen, out, native, verifier, oracle)
            proof["sessions"].append(result)
            save(out / "results.json", proof)
            if not result["passed"]:
                raise RuntimeError("session failed: " + label + "; partial evidence retained")
        proof.update(complete=True, passed=True)
    except Exception as error:
        proof["error"] = type(error).__name__ + ": " + str(error)
    save(out / "results.json", proof)
    print(json.dumps({"passed": proof["passed"], "results": str(out / "results.json"),
        "sessions": [(item["name"], item["passed"], item.get("runtime_exitcode")) for item in proof["sessions"]],
        "error": proof.get("error")}), flush=True)
    return 0 if proof["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.build.is_absolute() or not args.build.is_file() or not args.out.is_absolute():
        parser.error("absolute existing build and new external output paths required")
    return prove(args.build, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
