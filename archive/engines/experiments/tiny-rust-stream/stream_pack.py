"""A single compressed Python bootstrap and Rust compiler-stdin image.

Adapted from the byte-pinned TinyA stream helper recorded in ORIGIN.  The
runtime uses no file map or ZIP header.  Shell immediately becomes the Python
decoder, which reads this file rather than the engine's stdin.  Python restores
one source literal, compiles in a private directory, drains that compiler's
process group, removes the directory and fd-execs the resulting ELF.

The process contract is Linux /proc, ordinary signalable children remaining in
the compiler process group, and a target PATH containing python3 and rustc.
Detached descendants and an unkillable kernel task are outside that contract;
if the latter prevents draining, status 125 preserves the directory rather than
deleting compiler work underneath a live task.  Direct program names are an
audit list, not a sandbox or a complete rules-eligibility claim.
"""

import bz2
import gzip
import hashlib
import io
import lzma
from pathlib import Path
import types


CODECS = ("xz", "gzip", "bzip2")
ORIGIN = {
    "path": "engines/experiments/packaging-control/pack_stream.py",
    "sha256": "b4addefbb1233881e85707aa525ca4af7f8210d9d27f56fbb52e4440a966b99e",
}
ALLOWED = frozenset(("sh", "python3", "rustc"))
COMMAND = (
    "rustc", "--edition=2024", "-C", "opt-level=z", "-C", "lto=fat",
    "-C", "codegen-units=1", "-C", "panic=abort", "-C", "strip=symbols",
    "-C", "debuginfo=0", "-C", "link-arg=-Wl,--build-id=none",
    "--check-cfg", "cfg(tiny_dev)", "--crate-name", "rove4k", "-", "-o", "x",
)
ENVIRONMENT = ("ROVE_WORKERS", "ROVE_TT_BITS", "SOURCE_DATE_EPOCH", "LC_ALL", "TZ")
FIXED_RESOURCE_SOURCE = (22981, "516aab3e2f9085dd4a95503cc4ebc1a02670034a0a2daee8350081957f056e0b")
# The ordinary builder freezes these shared producers alongside this module.
OWNER_BINDINGS = {
    "compiler_stdin.py": "fc92bb6146fcfc5a6c73cd9f68929192a90d22a875bf591caf2cf3b32b87055b",
    "compiler_seek.py": "8ca5fd736f010cd9dd1e3b668065c0cf7d82f9e98653580b8f9b4c23e7d75a41",
}


def source_literal(source):
    """Preserve the frozen helper's byte-exact source-literal selection."""
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError:
        return repr(source), "bytes-repr"
    trailing = len(text) - len(text.rstrip("\\"))
    if "\r" not in text and "\0" not in text and not trailing % 2:
        for quote, kind in (("'''", "raw-single"), ('"""', "raw-double")):
            if quote not in text and not text.endswith(quote[0]):
                return "r" + quote + text + quote + ".encode()", kind
    return repr(source), "bytes-repr"


def _guard(source, command, environment, *, omit_resource_environment=False):
    if not isinstance(source, bytes):
        raise TypeError("Rust source must be bytes")
    if not isinstance(command, (list, tuple)) or tuple(command) != COMMAND:
        raise ValueError("the fixed Rust 2024 compiler-stdin recipe is required")
    if not isinstance(environment, dict) or set(environment) != set(ENVIRONMENT):
        raise ValueError("the five explicit public compiler environment keys are required")
    if not all(isinstance(value, str) for value in environment.values()):
        raise ValueError("compiler environment values must be strings")
    for key, low, high in (("ROVE_WORKERS", 1, 512), ("ROVE_TT_BITS", 8, 26)):
        value = environment[key]
        if not value.isascii() or not value.isdecimal() or str(int(value)) != value or not low <= int(value) <= high:
            raise ValueError("unsupported fixed resource value: " + key)
    if any(environment[key] != value for key, value in (("SOURCE_DATE_EPOCH", "0"), ("LC_ALL", "C"), ("TZ", "UTC"))):
        raise ValueError("the fixed reproducible compiler environment is required")
    if type(omit_resource_environment) is not bool:
        raise ValueError("explicit resource environment policy required")
    if omit_resource_environment and ((len(source), hashlib.sha256(source).hexdigest()) != FIXED_RESOURCE_SOURCE
            or (environment["ROVE_WORKERS"], environment["ROVE_TT_BITS"]) != ("2", "18")):
        raise ValueError("resource overrides may be omitted only for the exact embodied2/18 source")
    return {key: environment[key] for key in (ENVIRONMENT[2:] if omit_resource_environment else ENVIRONMENT)}


def _owner_modules():
    result = {}
    for filename, expected in OWNER_BINDINGS.items():
        path = Path(__file__).resolve().parents[2] / "scripts" / filename
        data = path.read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("shared Rust owner producer changed: " + filename)
        loaded = types.ModuleType("rust_stream_" + path.stem)
        loaded.__file__ = str(path)
        exec(compile(data, str(path), "exec"), loaded.__dict__)
        result[path.stem] = loaded
    return result


def bootstrap(source, command, *, environment, prepared=False, omit_resource_environment=False):
    if type(prepared) is not bool:
        raise ValueError("explicit prepared-input policy required")
    fixed = _guard(source, command, environment, omit_resource_environment=omit_resource_environment)
    literal, kind = source_literal(source)
    script = (
        "import os,signal,subprocess,sys,tempfile,shutil,time\n"
        "p=None;q=15;d=None;clean=True\n"
        "def stop(s,f):\n global q\n q=s\n signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n raise SystemExit(128+s)\n"
        "def kill(s):\n"
        " try:os.killpg(p.pid,s)\n except ProcessLookupError:pass\n"
        "def wait(n):\n"
        " t=time.monotonic()+n\n"
        " while os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None:\n"
        "  if time.monotonic()>t:return False\n"
        "  time.sleep(.01)\n"
        " return True\n"
        "def live():\n"
        " for n in os.listdir('/proc'):\n"
        "  if n.isdecimal():\n"
        "   try:\n"
        "    with open('/proc/'+n+'/stat') as f:a=f.read().rsplit(')',1)[1].split()\n"
        "    if int(a[2])==p.pid and a[0]!='Z':return True\n"
        "   except (OSError,ValueError,IndexError):pass\n"
        " return False\n"
        "signal.signal(2,stop);signal.signal(15,stop)\n"
        "h=signal.signal(signal.SIGCHLD,signal.SIG_DFL)\n"
        "m=signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n"
        "try:\n"
        " d=tempfile.mkdtemp(prefix='r4s-')\n"
        " e=os.environ.copy();e.update(" + repr(fixed) + ");e['TMPDIR']=d\n"
        " try:\n"
        "  try:p=subprocess.Popen(" + repr(list(command)) + ",cwd=d,env=e,stdin=subprocess.PIPE,bufsize=0,start_new_session=True,preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,m))\n"
        "  finally:signal.pthread_sigmask(signal.SIG_SETMASK,m)\n"
        "  try:\n"
        "   v=memoryview(" + literal + ")\n"
        "   while v:v=v[os.write(p.stdin.fileno(),v):]\n"
        "  except BrokenPipeError:pass\n"
        "  finally:p.stdin.close()\n"
        "  os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT)\n"
        " finally:\n"
        "  signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n"
        "  if p is not None:\n"
        "   if not wait(0):kill(q)\n"
        "   if not wait(5):\n"
        "    kill(9)\n"
        "    if not wait(5):clean=False;raise SystemExit(125)\n"
        "   kill(9);t=time.monotonic()+5\n"
        "   while live():\n"
        "    if time.monotonic()>t:clean=False;raise SystemExit(125)\n"
        "    kill(9);time.sleep(.01)\n"
        "   p.wait()\n"
        " if p.returncode:sys.exit(p.returncode if p.returncode>0 else 128-p.returncode)\n"
        " fd=os.open(d+'/x',os.O_RDONLY)\n"
        "finally:\n"
        " if d is not None and clean:shutil.rmtree(d)\n"
        "signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n"
        "signal.signal(signal.SIGCHLD,h)\n"
        "signal.pthread_sigmask(signal.SIG_SETMASK,m)\n"
        "os.execve(fd,sys.argv[1:],os.environ)\n"
    ).encode("utf-8")
    if prepared:
        owners = _owner_modules()
        stdin = owners['compiler_stdin']
        def prepare(data, *, shared_wait=True):
            return stdin.transform_bootstrap(data, shared_wait=shared_wait, contract='rust-stream-v1')
        script, metadata = prepare(script)
        script, _ = owners['compiler_seek'].transform_bootstrap(script, owner_metadata=metadata,
            prepare_owner=prepare, restore_owner=stdin.restore_bootstrap)
    return script, kind


def make_stream(source, command, codec="xz", *, environment, prepared=False, omit_resource_environment=False):
    if codec not in CODECS:
        raise ValueError("unsupported codec")
    script, kind = bootstrap(source, command, environment=environment, prepared=prepared,
                             omit_resource_environment=omit_resource_environment)
    if codec == "xz":
        payload = lzma.compress(script, format=lzma.FORMAT_XZ, preset=9 | lzma.PRESET_EXTREME)
        module = "lzma"
    elif codec == "bzip2":
        payload = bz2.compress(script, compresslevel=9)
        module = "bz2"
    else:
        buffer = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as archive:
            archive.write(script)
        payload = buffer.getvalue()
        module = "gzip"
    offset = 0
    while True:
        prefix = ("#!/bin/sh\nexec python3 -c 'import sys," + module + ";exec(" + module +
                  ".decompress(open(sys.argv[1],\"rb\").read()[" + str(offset) +
                  ":]))' \"$0\" \"$@\"\n").encode("ascii")
        if offset == len(prefix):
            break
        offset = len(prefix)
    output = prefix + payload
    programs = ["sh", "python3", command[0]]
    return output, {
        "format": "sh-python3-rust-source-stream-single", "codec": codec,
        "bytes": len(output), "payload_bytes": len(payload), "stub_bytes": len(prefix),
        "launcher_bytes": len(prefix), "payload_scope": "shared compressed Python bootstrap and single Rust source literal",
        "payload_offset_1based": offset + 1, "payload_offset_0based": offset,
        "python_bytes": len(script), "source_bytes": len(source), "source_literal": kind,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "wrapper_policy": "prepared-W1-W2-seek" if prepared else "legacy-pipe",
        "compiler_environment": _guard(source, command, environment, omit_resource_environment=omit_resource_environment),
        "resource_environment_overrides_omitted": omit_resource_environment,
        "owner_helper_bindings": dict(OWNER_BINDINGS) if prepared else {},
        "sha256": hashlib.sha256(output).hexdigest(), "external_programs": programs,
        "allowlisted_programs_only": all(program in ALLOWED for program in programs),
        "upstream_helper": dict(ORIGIN), "upstream_helper_sha256": ORIGIN["sha256"],
        "adaptations": ["fixed Rust stdin recipe and public compiler-only environment", "immediate shell exec to Python stdlib decoder",
                        "retain compiler leader with waitid WNOWAIT until process group drained, then final reap",
                        "normalize inherited SIGCHLD for compiler waitability and restore it before engine exec",
                        "always drain compiler process group including a leader-exit descendant", "conventional 128+signal compiler status"],
        "compiler_signal_status": "normal status unchanged; signal termination maps to 128+signal",
        "cleanup_scope": "Linux /proc; signalable compiler children remaining in its process group; status125 retains directory if live group cannot drain",
        "rules_reference": "https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853",
        "under_4096_bytes": len(output) <= 4096, "category": "general-4k",
        "rules_eligibility": "unproven_requires_runtime_and_full_rules_review",
    }


def write_stream(source, destination, command, *, environment, prepared=False, omit_resource_environment=False):
    destination = Path(destination)
    if not destination.is_absolute():
        raise ValueError("absolute external output required")
    results = []
    for codec in CODECS:
        data, record = make_stream(source, command, codec, environment=environment,
                                   prepared=prepared, omit_resource_environment=omit_resource_environment)
        path = destination / codec / "x"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o755)
        record["path"] = str(path)
        results.append(record)
    return results
