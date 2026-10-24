#!/usr/bin/env python3
"""One actual frozen kernel-wrapper identity/start/stop/quit witness.

This is not the full shipping suite, an algorithm check, or a speed/strength
measurement. Filesystem absence is sampled after UCI-ready; before-fd-exec
cleanup is supported separately by the exact frozen bootstrap source ordering.
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
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXPECTED_NATIVE = "d2049419376fb686cc939b0a1b801fa8644b32d25625cc247c875a0df32b8f89"


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
    calls = [node for node in ast.walk(ast.parse(script)) if isinstance(node, ast.Call)
             and len(node.args) == 1 and isinstance(node.func, ast.Attribute)
             and isinstance(node.func.value, ast.Name)
             and node.func.value.id == owner and node.func.attr == method]
    require(len(calls) == 1, "expected exactly one source/compiler argument")
    return calls[0].args[0]


def literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [literal(item) for item in node.elts]
        require(all(isinstance(item, str) for item in values), "non-string compiler argv")
        return values
    if (isinstance(node, ast.Call) and not node.args and not node.keywords
            and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)):
        if node.func.attr == "encode":
            return node.func.value.value.encode()
        if node.func.attr == "split":
            return node.func.value.value.split()
    raise ValueError("nonliteral source/compiler expression")


def decode(whole):
    prefix = re.match(rb'#!/bin/sh\np=\$\(tail -c\+([0-9]+) "\$0"\|xz -dc\)\|\|exit\n'
                      rb'exec python3 -c "\$p" "\$0" "\$@"\n', whole)
    require(prefix is not None and int(prefix[1]) == prefix.end() + 1,
            "unexpected full shell prefix or payload offset")
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
    script = decoder.decompress(whole[prefix.end():])
    require(decoder.eof and not decoder.unused_data, "one complete XZ stream required")
    ast.parse(script)
    return whole[:prefix.end()], script


def live_owned_descendants(engine):
    survivors = []
    for pid, start in engine.descendants.items():
        try:
            fields = (Path("/proc") / str(pid) / "stat").read_text().rpartition(") ")[2].split()
            if fields[19] == start and fields[0] != "Z":
                survivors.append(pid)
        except OSError:
            pass
    return survivors


def prove(results, output):
    output = output.resolve()
    require(not output.exists() and output != ROOT and ROOT not in output.parents,
            "new external output required")
    output.mkdir(parents=True)
    frozen = output / "frozen"
    frozen.mkdir()
    producer_dir = frozen / "producer"
    producer_dir.mkdir()
    proof = {"schema": 1, "passed": False,
             "scope": "one exact whole-wrapper identity/start/clocked-stop/quit witness",
             "excluded": ["full five-group shipping suite", "algorithm qualification", "NPS/Elo",
                          "all-position correctness", "independent pre-input filesystem sample", "4K acceptance"],
             "limits_seconds": {"startup": 60, "response": 5, "stop": 2},
             "forced_cleanup": [], "frozen_sha256": {}}
    save(output / "identity.json", proof)
    engine = None
    try:
        report_bytes = results.read_bytes()
        report = json.loads(report_bytes)
        require(report["passed"] is True and report["workers"] == 2 and report["tt_bits"] == 18,
                "requires successful frozen two-worker TT18 cost report")
        forms = [item for item in report["forms"] if item["id"] == "kernel"]
        require(len(forms) == 1, "expected one frozen kernel")
        form = forms[0]
        require(form["native_sha256"] == EXPECTED_NATIVE, "unexpected native reference class")
        form_dir = results.parent / "kernel"
        source = (form_dir / "main.c").read_bytes()
        script = (form_dir / "bootstrap.py").read_bytes()
        whole = Path(form["wrapper"]).read_bytes()
        native = (form_dir / "x").read_bytes()
        require(sha(source) == form["source_sha256"] and len(source) == form["source_bytes"], "encoded C changed")
        require(sha(whole) == form["whole_sha256"] and len(whole) == form["whole_bytes"], "complete wrapper changed")
        require(sha(native) == EXPECTED_NATIVE and len(native) == form["native_bytes"], "native reference changed")
        prefix, decoded = decode(whole)
        require(decoded == script and sha(script) == form["artifact"]["decoded_sha256"], "bootstrap changed")
        restored = literal(argument(script, "p", "communicate"))
        argv = literal(argument(script, "subprocess", "Popen"))
        require(restored == source and isinstance(restored, bytes), "restored source is not exact")
        require(argv == form["command"] == ["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"],
                "restored compiler argv changed")
        snapshots = {"identity.py": Path(__file__).read_bytes(), "results.json": report_bytes,
                     "main.c": source, "bootstrap.py": script, "selected-wrapper": whole,
                     "native-reference": native,
                     "verify.py": (ROOT / "engines/tests/verify.py").read_bytes(),
                     "chess_oracle.py": (ROOT / "engines/tests/chess_oracle.py").read_bytes()}
        for name, data in snapshots.items():
            (frozen / name).write_bytes(data)
            proof["frozen_sha256"][name] = sha(data)
        for name, expected in report["input_sha256"].items():
            require(Path(name).name == name, "unexpected producer input path")
            data = (results.parent / "frozen" / name).read_bytes()
            require(sha(data) == expected, "producer frozen input differs: " + name)
            (producer_dir / name).write_bytes(data)
            proof["frozen_sha256"]["producer/" + name] = sha(data)
        executable = frozen / "selected-wrapper"
        executable.chmod(0o755)
        expression = module("kernel_identity_expression", producer_dir / "encoding_campaign.py")
        producer = module("kernel_identity_producer", producer_dir / "pack_stream.py")
        control, _ = producer.bootstrap(source, argv)
        def skeleton(data):
            data = expression.replace_argument(data, "p", "communicate", "b'SOURCE'")
            return expression.replace_argument(data, "subprocess", "Popen", "['COMMAND']")
        require(skeleton(script) == skeleton(control), "signal/wait/cleanup/fd-exec skeleton changed")
        proof.update(source_sha256=sha(source), source_restored_exactly=True, compiler_argv=argv,
                     compiler_argv_exact=True, bootstrap_sha256=sha(script), bootstrap_skeleton_unchanged=True,
                     whole_bytes=len(whole), whole_sha256=sha(whole), launcher_bytes=len(prefix),
                     native_reference_sha256=sha(native), native_bytes=len(native))
        save(output / "identity.json", proof)

        oracle = module("chess_oracle", frozen / "chess_oracle.py")
        verifier = module("kernel_identity_verifier", frozen / "verify.py")
        class TracedEngine(verifier.Engine):
            def terminate(self):
                if self.process.poll() is None:
                    proof["forced_cleanup"].append({"action": "kill-owned-process-group",
                                                    "pid": self.process.pid,
                                                    "basis": "bounded failure cleanup; never acceptance"})
                return super().terminate()
        spec = {"id": "kernel-actual-once", "command": [str(executable)],
                "cwd": str(frozen), "profile": "shipping", "workers": 2,
                "startup_threads": 3, "startup_timeout": 60}
        engine = TracedEngine(spec, output, "actual", 5)
        launched = engine.process.pid
        engine.initialize()
        engine.assert_threads_stable()
        proc = Path("/proc") / str(launched)
        image = (proc / "exe").read_bytes()
        require(image == native and sha(image) == EXPECTED_NATIVE, "actual restored native differs")
        executable_link = os.readlink(proc / "exe")
        require(executable_link.endswith("/x (deleted)"), "native fd-exec image is not removed x")
        owned_temp = Path(executable_link.removesuffix(" (deleted)")).parent
        require(not owned_temp.exists(), "compiler directory remains after UCI-ready")
        status = dict(line.split(":", 1) for line in (proc / "status").read_text().splitlines())
        require(int(status["Pid"]) == launched and int(status["PPid"]) == os.getpid(),
                "intermediate wrapper process remains")
        children = (proc / "task" / str(launched) / "children").read_text().strip()
        require(not children, "compiler children remain after UCI-ready")
        ids = engine.task_ids()
        require(len(ids) == 3 and ids == engine.startup_task_ids, "startup TIDs changed")
        (output / "actual-native").write_bytes(image)
        proof.update(launched_pid=launched, observed_native_pid=int(status["Pid"]),
                     observed_parent_pid=int(status["PPid"]), expected_parent_pid=os.getpid(),
                     same_pid_fd_exec=True, actual_restored_native_sha256=sha(image),
                     executable_link=executable_link, startup_thread_ids=sorted(ids), startup_threads=3,
                     startup_threads_observed_before_first_command=True, compiler_children_after_uci_ready=[],
                     temporary_directory=str(owned_temp), temporary_directory_absent_after_uci_ready=True,
                     temporary_directory_observation="after_uci_ready",
                     cleanup_before_fd_exec_basis="unchanged frozen bootstrap source ordering")
        save(output / "identity.json", proof)

        require(not any(line.startswith("bestmove ") for _, line in engine.stdout_events),
                "unsolicited result before search")
        engine.position()
        before, activity = verifier.begin_lifecycle_search(engine, SimpleNamespace(suite="shipping"))
        require(activity["active_before_signal"] and not any(line.startswith("bestmove ") for line in before),
                "active stop witness unavailable: search already completed or work unobserved")
        engine.send("stop")
        lines, move = verifier.finish_signalled_search(engine, before, timeout=2)
        verifier.record_completed_signal(engine, activity, "stop")
        require(activity["cancellation_coverage"] == "work_observed_before_signal_result_received_after_signal",
                "result did not follow the observed-work stop signal")
        legal = sorted(str(candidate) for candidate in oracle.Board.from_fen().legal_moves())
        require(move in legal, "bestmove is illegal in independent startpos oracle")
        require(not any(line.startswith("bestmove ") for line in engine.ready()), "extra result before readyok")
        require(not any(line.startswith("bestmove ") for line in engine.quiet()), "duplicate result after stop")
        engine.assert_threads_stable()
        engine.close()
        all_best = [line for _, line in engine.stdout_events if line.startswith("bestmove ")]
        require(len(all_best) == 1 and all_best[0] == "bestmove " + move, "search did not settle exactly once")
        require(not proof["forced_cleanup"], "forced cleanup cannot pass this proof")
        survivors = live_owned_descendants(engine)
        require(not survivors, "observed owned descendant remains after quit")
        require(not proc.exists(), "native PID remains after waited quit")
        proof.update(passed=True, search={"position": "startpos", "bestmove": move,
                                       "bestmove_count": len(all_best), "legal_moves": legal,
                                       "activity": activity, "response_lines": lines},
                     thread_ids_preserved_through_stop=True, runtime_exitcode=engine.process.returncode,
                     runtime_stderr=engine.stderr, observed_owned_descendants=sorted(engine.descendants),
                     surviving_observed_owned_descendants=survivors,
                     orphan_check_scope="observed owned descendants, native PID and post-handshake child sample",
                     transcript=str(engine.path))
    except Exception as error:
        proof["passed"] = False
        proof["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if engine is not None:
            try:
                if engine.process.poll() is None:
                    engine.terminate()
                elif not engine.log.closed:
                    engine.finish()
                proof["runtime_exitcode"] = engine.process.returncode
                proof["runtime_stderr"] = engine.stderr
                proof["observed_owned_descendants"] = sorted(engine.descendants)
                proof["surviving_observed_owned_descendants"] = live_owned_descendants(engine)
                if proof["surviving_observed_owned_descendants"] or proof["forced_cleanup"]:
                    proof["passed"] = False
            except Exception as error:
                proof["cleanup_error"] = type(error).__name__ + ": " + str(error)
                proof["passed"] = False
    save(output / "identity.json", proof)
    print(json.dumps({"passed": proof["passed"], "identity": str(output / "identity.json"),
                      "error": proof.get("error"), "forced_cleanup": proof["forced_cleanup"]}), flush=True)
    return 0 if proof["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.results.is_absolute() or not args.results.is_file():
        parser.error("--results must be an absolute existing frozen cost report")
    if not args.out.is_absolute():
        parser.error("--out must be absolute")
    return prove(args.results, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
