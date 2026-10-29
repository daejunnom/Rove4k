"""Exercise two unique mates in the actual selected E TEST-P4 source.

This is a local tactical regression, not a W256 or playing-strength gate.
The producer is run separately; this check recompiles its exact output and
requires its native hash before exercising the UCI process.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import time

import chess


CASES = (
    ("f2f3 e7e5 g2g4", "d8h4"),
    ("e2e4 e7e5 d1h5 b8c6 f1c4 g8f6", "h5f7"),
)
GO = "go wtime 120000 btime 120000 winc 0 binc 0"


def check_source(build: Path) -> tuple[bytes, str, str]:
    metadata = json.loads((build / "build.json").read_bytes())
    verifier_path = Path(__file__).with_name("profile_verify.py")
    spec = importlib.util.spec_from_file_location("e_mate_profile_verify", verifier_path)
    verifier = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = verifier
    spec.loader.exec_module(verifier)
    admitted = verifier.admit_c_build(metadata, build)
    if admitted.family != "E" or admitted.profile_id != "test-p4":
        raise ValueError("selected E TEST-P4 admission required")
    if metadata["complete"] is not True or metadata["family"] != "E" or metadata["resources"]["id"] != "test-p4":
        raise ValueError("complete selected E TEST-P4 build required")
    if metadata["post_compact"] != {
        "path": "engines/compact/tiny-entry-e/profile_eval_unit.py",
        "variant": "e-fixed-coeff-macros",
    }:
        raise ValueError("selected E compaction required")
    if metadata["actual"]["source"] != "main.c":
        raise ValueError("unexpected source path")
    source = (build / "main.c").read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    attempts = metadata["attempts"]
    if len(attempts) != 2 or not all(row["source_sha256"] == digest and row["source_bytes"] == len(source)
                                    for row in attempts):
        raise ValueError("selected source differs from producer attempts")
    native = attempts[0]["native_sha256"]
    if attempts[1]["native_sha256"] != native:
        raise ValueError("producer native attempts differ")
    return source, native, metadata["compile_executor_version"]


def oracle() -> None:
    for moves, expected in CASES:
        board = chess.Board()
        for move in moves.split():
            board.push_uci(move)
        mates = []
        for move in board.legal_moves:
            board.push(move)
            if board.is_checkmate():
                mates.append(move.uci())
            board.pop()
        if mates != [expected]:
            raise ValueError(f"position does not have the expected unique mate: {mates}")


class Lines:
    def __init__(self, stream):
        self.stream = stream
        self.pending = b""
        self.selector = selectors.DefaultSelector()
        self.selector.register(stream, selectors.EVENT_READ)

    def receive(self, wanted: bytes, timeout: float) -> str:
        end = time.monotonic() + timeout
        while True:
            while b"\n" in self.pending:
                line, self.pending = self.pending.split(b"\n", 1)
                if line.startswith(wanted):
                    return line.decode("ascii")
            remaining = end - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise TimeoutError(f"missing {wanted!r}")
            data = os.read(self.stream.fileno(), 4096)
            if not data:
                raise RuntimeError("engine exited before response")
            self.pending += data
            if len(self.pending) > 65536:
                raise ValueError("engine line too long")


def run(binary: Path) -> list[dict]:
    process = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    lines = Lines(process.stdout)

    def send(command: str) -> None:
        process.stdin.write((command + "\n").encode("ascii"))
        process.stdin.flush()

    try:
        send("uci")
        if lines.receive(b"uciok", 30) != "uciok":
            raise ValueError("invalid uciok")
        send("isready")
        if lines.receive(b"readyok", 10) != "readyok":
            raise ValueError("invalid readyok")
        answers = []
        for moves, expected in CASES:
            send("position startpos moves " + moves)
            started = time.monotonic()
            send(GO)
            answer = lines.receive(b"bestmove ", 30)
            if answer != "bestmove " + expected:
                raise AssertionError(f"expected unique mate {expected}, got {answer}")
            answers.append({"moves": moves, "expected_unique_mate": expected,
                            "answer": answer, "elapsed_ms": round((time.monotonic() - started) * 1000)})
        send("quit")
        if process.wait(timeout=10) != 0:
            raise RuntimeError("engine failed on quit")
        return answers
    finally:
        lines.selector.close()
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new JSON receipt outside the checkout")
    args = parser.parse_args()
    if (not args.out.is_absolute() or
            Path(__file__).resolve().parents[3] in args.out.resolve().parents):
        parser.error("receipt must be an absolute path outside the checkout")
    source, expected_native, expected_compiler = check_source(args.build)
    oracle()
    with tempfile.TemporaryDirectory(prefix="rove-e-mate-") as directory:
        binary = Path(directory) / "x"
        compiler = subprocess.run(["cc", "--version"], check=True, capture_output=True,
                                  text=True, timeout=10).stdout.splitlines()[0]
        if compiler != expected_compiler:
            raise ValueError("compiler version differs from selected producer")
        subprocess.run(["cc", "-Os", "-x", "c", "-", "-o", str(binary), "-s"],
                       input=source, check=True, timeout=60)
        if hashlib.sha256(binary.read_bytes()).hexdigest() != expected_native:
            raise ValueError("recompiled binary differs from selected producer native")
        answers = run(binary)
    receipt = {"schema": "rove4k.e-selected-mate-regression.v1", "family": "E", "profile": "test-p4",
               "source_sha256": hashlib.sha256(source).hexdigest(), "native_sha256": expected_native,
               "compiler_version": compiler, "oracle": "chess==" + chess.__version__,
               "clock_command": GO, "answers": answers,
               "w256_runtime_proven": False, "strength_proven": False}
    with args.out.open("x", encoding="utf-8") as output:
        json.dump(receipt, output, sort_keys=True)
        output.write("\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
