#!/usr/bin/env python3
"""npm launch and owned subprocess lifetime boundary.

Own only subprocess groups created by this process. Known nested core scripts
and byte-identical bundled example verifier copies reenter this adapter so they
can clean their own groups. Arbitrary external helpers must not daemonize or
create detached sessions whose lifetime they do not manage. This is not a
process-tree scanner or an execution sandbox.
"""
import sys

if sys.version_info < (3, 11) or sys.implementation.name != "cpython":
    print("nvcompact: CPython >=3.11 is required; got " + sys.version.replace("\n", " "), file=sys.stderr)
    raise SystemExit(2)
if sys.platform != "linux":
    print("nvcompact: this release supports Linux only", file=sys.stderr)
    raise SystemExit(2)

import argparse
import ast
import concurrent.futures
import contextlib
import hashlib
import json
import os
from pathlib import Path
import platform
import runpy
import signal
import subprocess
import threading

ROOT = Path(__file__).resolve().parent
SCRIPTS = {
    "build": ("nvcompact.py", "build"),
    "run": ("nvcompact.py", "run"),
    "reproduce": ("nvcompact.py", "reproduce"),
    "notation": ("nvnotation.py",),
    "rewrite-c": ("nvcflow.py",),
    "envelope": ("nvenvelope.py",),
    "uci": ("nvuci.py",),
    "replay": ("nvreproduce.py",),
    "engines": ("run_engines.py",),
    "resource": ("nvresource.py",),
}


def runtime_check(*, codecs=True):
    """Fingerprint the adapter; explicit doctor additionally exercises codecs.

    Ordinary commands load the dependencies used by their selected execution
    path. In particular a plain build or a read-only resource plan performs no
    diagnostic compression and does not require unused codec modules.
    """
    result = {"python": sys.executable, "implementation": platform.python_implementation(),
              "version": platform.python_version(), "platform": sys.platform,
              "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "checks": {}, "scope": "local launcher runtime; not compilers, optional chess oracle, tournament eligibility or engine performance"}
    try:
        version = next(node.value for node in ast.parse((ROOT / "nvcompact.py").read_text()).body
                       if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "VERSION" for target in node.targets))
        result["core_version"] = ast.literal_eval(version)
        if not codecs:
            result.update(status="pass", codec_probes="not_requested")
            return result
        import bz2
        import gzip
        import lzma
        data = b"NVCompact runtime codec probe\0" * 16
        for name, packed, restored in (
            ("bz2", bz2.compress(data), bz2.decompress),
            ("gzip", gzip.compress(data, mtime=0), gzip.decompress),
            ("lzma_alone", lzma.compress(data, format=lzma.FORMAT_ALONE), lzma.decompress),
            ("xz", lzma.compress(data, format=lzma.FORMAT_XZ), lzma.decompress),
        ):
            if restored(packed) != data:
                raise RuntimeError(name + " round-trip failed")
            result["checks"][name] = "pass"
        filters = [{"id": lzma.FILTER_X86}, {"id": lzma.FILTER_LZMA2, "dict_size": 4096}]
        packed = lzma.compress(data, format=lzma.FORMAT_RAW, filters=filters)
        if lzma.decompress(packed, format=lzma.FORMAT_RAW, filters=filters) != data:
            raise RuntimeError("raw LZMA2 + x86 BCJ round-trip failed")
        result["checks"]["raw_lzma2_x86"] = "pass"
        for name in ("MF_HC3", "MF_HC4", "MF_BT2", "MF_BT3", "MF_BT4"):
            getattr(lzma, name)
        result["checks"]["match_finder_api"] = "pass"
    except Exception as exc:
        result.update(status="error", error=str(exc))
        return result
    result["status"] = "pass"
    return result


class Cancelled(KeyboardInterrupt):
    """A BaseException path that lets unchanged finally blocks clean up."""


_original_popen = subprocess.Popen
_original_killpg = os.killpg
_original_executor = concurrent.futures.ThreadPoolExecutor
_owned = {}
_owned_lock = threading.RLock()
_cancel_signal = None
_critical_depth = 0
_handling_cancel = False
_cleanup_errors = []
_main_thread = threading.main_thread()
_known_scripts = {(ROOT / entry[0]).resolve() for entry in SCRIPTS.values()}
_verifier = ROOT.parent / "examples" / "mixed" / "verifier.py"
_verifier_hash = hashlib.sha256(_verifier.read_bytes()).digest() if _verifier.is_file() else None


def _nested_script(argv):
    if not isinstance(argv, (tuple, list)) or len(argv) < 2:
        return None
    try:
        if Path(argv[0]).resolve() != Path(sys.executable).resolve():
            return None
        script = Path(argv[1]).resolve()
        if script in _known_scripts:
            return script
        # nvcompact copies this shipped verifier into each immutable snapshot.
        # A matching basename alone is insufficient to alter user code launch.
        if _verifier_hash and script.name == "verifier.py" and script.is_file():
            if hashlib.sha256(script.read_bytes()).digest() == _verifier_hash:
                return script
    except (TypeError, OSError, ValueError):
        pass
    return None


@contextlib.contextmanager
def _creation_boundary():
    global _critical_depth
    main = threading.current_thread() is _main_thread
    if main:
        _critical_depth += 1
    try:
        yield
    finally:
        if main:
            _critical_depth -= 1
            if _cancel_signal and not _critical_depth and not _handling_cancel:
                _cancel_now()


def _kill_owned_group(pgid, sig):
    # A core bounded-command finally must not SIGKILL a nested Python helper
    # before that helper has stopped its own independent engine/compiler groups.
    with _creation_boundary():
        with _owned_lock:
            record = _owned.get(pgid)
        if sig == signal.SIGKILL and record and record[1]:
            proc = record[0]
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    _cleanup_errors.append("nested helper cleanup exceeded 10 seconds: " + str(proc.pid))
                    print("nvcompact: nested helper cleanup exceeded 10 seconds; terminating its original group", file=sys.stderr)
        try:
            return _original_killpg(pgid, sig)
        finally:
            if sig == signal.SIGKILL:
                with _owned_lock:
                    _owned.pop(pgid, None)


def _stop_owned():
    with _owned_lock:
        entries = list(_owned.values())
    # Stop adapters first: they transitively own groups absent from this table.
    entries.sort(key=lambda entry: not entry[1])
    for proc, _ in entries:
        try:
            _kill_owned_group(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as exc:
            _cleanup_errors.append("owned process group cleanup failed: " + str(exc))
            print("nvcompact: owned process group cleanup failed: " + str(exc), file=sys.stderr)
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _cleanup_errors.append("owned process reap exceeded 2 seconds: " + str(proc.pid))
            print("nvcompact: owned process could not be reaped within cleanup grace: " + str(proc.pid), file=sys.stderr)


def _cancel_now():
    global _handling_cancel
    if _handling_cancel:
        return
    _handling_cancel = True
    _stop_owned()
    raise Cancelled()


def _on_signal(signum, _frame):
    global _cancel_signal
    if _cancel_signal is not None:
        return
    _cancel_signal = signum
    if not _critical_depth:
        _cancel_now()


class OwnedPopen(_original_popen):
    def __init__(self, args, *positional, **options):
        if _cancel_signal:
            raise Cancelled()
        nested = _nested_script(args)
        if nested is not None:
            args = [args[0], "-B", str(ROOT / "nvlaunch.py"), "_script", str(nested), *args[2:]]
        # Defer asynchronous main-thread exceptions until a child is registered.
        # Worker creation is serialized with registry snapshots; no child can
        # slip between cancellation's snapshot and the cancellation flag.
        with _creation_boundary(), _owned_lock:
            if _cancel_signal:
                raise Cancelled()
            super().__init__(args, *positional, **options)
            if options.get("start_new_session"):
                _owned[self.pid] = (self, nested is not None)
        if _cancel_signal:
            try:
                _kill_owned_group(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.wait()
            raise Cancelled()


class OwnedExecutor(_original_executor):
    def submit(self, fn, /, *args, **kwargs):
        def guarded():
            if _cancel_signal:
                raise Cancelled()
            return fn(*args, **kwargs)
        if _cancel_signal:
            raise Cancelled()
        return super().submit(guarded)

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.shutdown(wait=True, cancel_futures=bool(_cancel_signal) or isinstance(exc_value, KeyboardInterrupt))
        except KeyboardInterrupt:
            # Cancellation can also arrive while an ordinary context exit is
            # already joining workers, after cancel_futures was evaluated false.
            self.shutdown(wait=True, cancel_futures=True)
            raise
        return False


def validate_engine_selection(argv):
    if "--help" in argv or "-h" in argv:
        return
    parser = argparse.ArgumentParser(prog="nvcompact engines", add_help=False, allow_abbrev=False)
    parser.add_argument("--manifests", type=Path, required=True)
    parser.add_argument("--only", nargs="+")
    selected, _ = parser.parse_known_args(argv)
    if not selected.manifests.is_dir():
        parser.error("--manifests must name an existing directory")
    files = sorted(path for path in selected.manifests.glob("*.json") if path.is_file())
    if not files:
        parser.error("--manifests must contain at least one .json manifest")
    missing = set(selected.only or ()) - {path.stem for path in files}
    if missing:
        parser.error("unknown engine names: " + ", ".join(sorted(missing)))


def cancellation_status():
    signum = _cancel_signal or signal.SIGINT
    cleanup = "owned process cleanup incomplete; inspect preceding diagnostics" if _cleanup_errors else "owned process cleanup completed"
    print("nvcompact: cancelled by " + signal.Signals(signum).name + "; " + cleanup, file=sys.stderr)
    return 128 + signum


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("nvcompact: a subcommand is required", file=sys.stderr)
        return 2
    diagnostic = runtime_check(codecs=argv[0] == "doctor")
    if argv[0] == "doctor":
        parser = argparse.ArgumentParser(prog="nvcompact doctor", description="Check the locally installed launcher runtime without installing anything")
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args(argv[1:])
        if args.json:
            print(json.dumps(diagnostic, indent=2))
        else:
            print("NVCompact runtime: " + diagnostic["status"])
            print("Python: " + diagnostic["python"] + " (" + diagnostic["implementation"] + " " + diagnostic["version"] + ")")
            for name, status in diagnostic["checks"].items():
                print("  " + name + ": " + status)
            print(diagnostic["scope"])
            if "error" in diagnostic:
                print(diagnostic["error"], file=sys.stderr)
        return 0 if diagnostic["status"] == "pass" else 2
    if diagnostic["status"] != "pass":
        print("nvcompact: Python runtime diagnostic failed: " + diagnostic["error"], file=sys.stderr)
        return 2
    if argv[0] == "_script" and len(argv) >= 2:
        # This internal entry retains ordinary Python script argv/cwd semantics.
        script, args = Path(argv[1]).resolve(), argv[2:]
        if script not in _known_scripts and not (_verifier_hash and script.is_file() and
                hashlib.sha256(script.read_bytes()).digest() == _verifier_hash):
            print("nvcompact: internal adapter target is not a shipped helper", file=sys.stderr)
            return 2
    elif argv[0] in SCRIPTS:
        if argv[0] == "engines":
            validate_engine_selection(argv[1:])
        name, *prefix = SCRIPTS[argv[0]]
        script, args = ROOT / name, [*prefix, *argv[1:]]
    else:
        print("nvcompact: unknown adapter command " + repr(argv[0]), file=sys.stderr)
        return 2
    subprocess.Popen = OwnedPopen
    os.killpg = _kill_owned_group
    concurrent.futures.ThreadPoolExecutor = OwnedExecutor
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    old_argv = sys.argv
    sys.argv = [str(script), *args]
    sys.path[0] = str(script.parent)
    code = 0
    try:
        runpy.run_path(str(script), run_name="__main__", init_globals={"_NVCOMPACT_MANAGED": True})
    except ImportError as exc:
        print("nvcompact: selected command requires an unavailable Python dependency: " + str(exc), file=sys.stderr)
        code = 2
    except SystemExit as exc:
        if exc.code is None:
            code = 0
        elif isinstance(exc.code, int):
            code = exc.code
        else:
            print(exc.code, file=sys.stderr)
            code = 1
    except KeyboardInterrupt:
        code = 130
    finally:
        sys.argv = old_argv
        _stop_owned()
    if _cancel_signal:
        return cancellation_status()
    return 2 if _cleanup_errors and code == 0 else code


if __name__ == "__main__":
    try:
        status = main()
    except KeyboardInterrupt:
        # Cover cancellation at startup/after runpy and during the outer cleanup
        # boundary too, preserving TERM=143 rather than Python's default INT=130.
        status = cancellation_status()
    raise SystemExit(status)
