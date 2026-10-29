"""Private small-resource UCI driver; supervised by peer_exact_runner.

The engine and this driver share the runner-owned process group. Raw protocol
bytes remain in memory and never go to the driver stdout or the CI receipt.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import original_peer_uci

LIMIT = 1 << 20
MOVES = {f"{file}{start}{file}{end}" for file in "abcdefgh" for start, end in (("2", "3"), ("2", "4"))}
MOVES.update({"b1a3", "b1c3", "g1f3", "g1h3"})


class Channel:
    def __init__(self, process):
        self.process = process
        self.stdout = bytearray()
        self.stderr = bytearray()
        self.selector = selectors.DefaultSelector()
        for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            self.selector.register(stream, selectors.EVENT_READ, name)

    def send(self, command):
        if self.process.poll() is not None:
            raise RuntimeError("engine exited before command")
        self.process.stdin.write(command)
        self.process.stdin.flush()

    def pump(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("engine protocol timeout")
        for key, _ in self.selector.select(min(remaining, .1)):
            try:
                chunk = os.read(key.fileobj.fileno(), 65536)
            except BlockingIOError:
                continue
            if not chunk:
                self.selector.unregister(key.fileobj)
                continue
            target = self.stdout if key.data == "stdout" else self.stderr
            target.extend(chunk)
            if len(self.stdout) + len(self.stderr) > LIMIT:
                raise ValueError("engine output exceeded smoke limit")

    def until(self, predicate, deadline):
        while not predicate(original_peer_uci._complete_lines(bytes(self.stdout))):
            if self.process.poll() is not None:
                raise RuntimeError("engine exited before response")
            self.pump(deadline)


def smoke(peer, native_fd, timeout=30):
    if peer not in original_peer_uci._NAMES or type(native_fd) is not int or native_fd < 3:
        raise ValueError("invalid peer or native descriptor")
    if type(timeout) is not int or not 1 <= timeout <= 60:
        raise ValueError("invalid smoke timeout")
    # Inherit the original supervisor group. Do not create a new session or
    # signal the child by a potentially reusable PID from this driver.
    process = subprocess.Popen([f"/proc/self/fd/{native_fd}"], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=(native_fd,))
    channel = Channel(process)
    deadline = time.monotonic() + timeout
    try:
        channel.send(b"uci\n")
        channel.until(lambda lines: b"uciok" in lines, deadline)
        resources = {"hash_mib": 1, "workers": 1}
        ponder = original_peer_uci._check_startup(bytes(channel.stdout), peer, resources)
        channel.send(b"setoption name Hash value 1\nsetoption name Threads value 1\n")
        if ponder is not None:
            channel.send(b"setoption name Ponder value false\n")
        channel.send(b"isready\n")
        channel.until(lambda lines: b"readyok" in lines, deadline)
        original_peer_uci._check_startup(bytes(channel.stdout), peer, resources, final=True)
        channel.send(b"ucinewgame\nposition startpos\ngo wtime 1000 btime 1000 winc 0 binc 0\n")
        channel.until(lambda lines: any(line.startswith(b"bestmove ") for line in lines), deadline)
        lines = original_peer_uci._complete_lines(bytes(channel.stdout))
        best = [line.split() for line in lines if line.startswith(b"bestmove ")]
        if len(best) != 1 or len(best[0]) not in (2, 4):
            raise ValueError("invalid bestmove response")
        if len(best[0]) == 4 and (best[0][2] != b"ponder" or len(best[0][3]) not in (4, 5)):
            raise ValueError("invalid ponder response")
        move = best[0][1].decode("ascii")
        if move not in MOVES:
            raise ValueError("start-position bestmove is illegal")
        channel.send(b"quit\n")
        process.stdin.close()
        while process.poll() is None:
            channel.pump(deadline)
        # Drain both pipes after exit, still within the same deadline.
        while channel.selector.get_map():
            channel.pump(deadline)
        if process.returncode != 0:
            raise RuntimeError("engine did not exit normally")
        lines = original_peer_uci._complete_lines(bytes(channel.stdout))
        if sum(line.startswith(b"bestmove ") for line in lines) != 1:
            raise ValueError("unexpected duplicate bestmove")
        return {"hash_mib_requested": 1, "threads_requested": 1,
                "uciok": True, "readyok": True, "legal_startpos_bestmove": move,
                "quit_exit_code": 0, "ponder": "not-declared" if ponder is None else "false-requested",
                "stdout_bytes": len(channel.stdout), "stderr_bytes": len(channel.stderr),
                "stdout_sha256": hashlib.sha256(channel.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(channel.stderr).hexdigest()}
    finally:
        channel.selector.close()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()


if __name__ == "__main__":
    try:
        peer_name, fd_text = sys.argv[1:]
        print(json.dumps(smoke(peer_name, int(fd_text)), sort_keys=True, separators=(",", ":")))
    except BaseException:
        # Do not expose raw engine source or protocol output on CI logs.
        print("original peer small UCI smoke failed", file=sys.stderr)
        raise SystemExit(1)
