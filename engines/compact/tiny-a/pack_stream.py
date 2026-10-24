"""One compressed Python bootstrap and C stdin source behind a shell prefix.

The complete shell prefix and compressed stream both count toward file size.
The shell waits for tail and the decoder before replacing itself with Python;
Python compiles in a private directory, waits and cleans, then fd-execs the ELF.
"""
import bz2
import gzip
import hashlib
import io
import lzma
from pathlib import Path


CODECS = ("xz", "gzip", "bzip2")
ALLOWED = frozenset(("bzip2", "bash", "c++", "cargo", "cc", "clang", "chmod", "gzip",
                     "lzma", "mktemp", "perl", "python", "python3", "pypy3", "rustc",
                     "sh", "sleep", "tail", "xz"))


def source_literal(source):
    """Preserve input bytes, including CRLF, NUL and non-UTF-8 fallbacks."""
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError:
        return repr(source), "bytes-repr"
    # Python normalizes physical CRLF inside literals; raw strings cannot end
    # in an odd backslash, and a trailing delimiter character is ambiguous.
    trailing = len(text) - len(text.rstrip("\\"))
    if "\r" not in text and "\0" not in text and not trailing % 2:
        for quote, kind in (("'''", "raw-single"), ('"""', "raw-double")):
            if quote not in text and not text.endswith(quote[0]):
                return "r" + quote + text + quote + ".encode()", kind
    return repr(source), "bytes-repr"


def bootstrap(source, command):
    literal, kind = source_literal(source)
    script = (
        "import os,signal,subprocess,sys,tempfile\n"
        "p=None;q=15\n"
        "def stop(s,f):\n"
        " global q\n q=s\n"
        " signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n"
        " raise SystemExit(128+s)\n"
        "signal.signal(2,stop);signal.signal(15,stop)\n"
        "with tempfile.TemporaryDirectory(prefix='r4-') as d:\n"
        " e=os.environ.copy();e['TMPDIR']=d\n"
        " try:\n"
        "  m=signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n"
        "  try:p=subprocess.Popen(" + repr(command) + ",cwd=d,env=e,stdin=subprocess.PIPE,start_new_session=True,preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,m))\n"
        "  finally:signal.pthread_sigmask(signal.SIG_SETMASK,m)\n"
        "  p.communicate(" + literal + ")\n"
        " finally:\n"
        "  if p is not None and p.poll() is None:\n"
        "   try:os.killpg(p.pid,q)\n"
        "   except ProcessLookupError:pass\n"
        "   try:p.wait(timeout=5)\n"
        "   except subprocess.TimeoutExpired:os.killpg(p.pid,9);p.wait()\n"
        " if p.returncode:sys.exit(p.returncode)\n"
        " fd=os.open(d+'/x',os.O_RDONLY)\n"
        "signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n"
        "os.execve(fd,sys.argv[1:],os.environ)\n"
    ).encode("utf-8")
    return script, kind


def make_stream(source, command, codec="xz", *, compiler_group):
    if not isinstance(source, bytes):
        raise TypeError("C source must be bytes")
    if not isinstance(command, (list, tuple)) or not command or not all(isinstance(part, str) and part and "\0" not in part for part in command):
        raise ValueError("a fixed compiler command is required")
    if codec not in CODECS:
        raise ValueError("unsupported codec")
    script, kind = bootstrap(source, command)
    script, ownership = compiler_group(script)
    if codec == "xz":
        payload = lzma.compress(script, format=lzma.FORMAT_XZ, preset=9 | lzma.PRESET_EXTREME)
    elif codec == "bzip2":
        payload = bz2.compress(script, compresslevel=9)
    else:
        buffer = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as archive:
            archive.write(script)
        payload = buffer.getvalue()
    offset = 1
    while True:
        prefix = ("#!/bin/sh\np=$(tail -c+" + str(offset) + " \"$0\"|" + codec +
                  " -dc)||exit\nexec python3 -c \"$p\" \"$0\" \"$@\"\n").encode("ascii")
        if offset == len(prefix) + 1:
            break
        offset = len(prefix) + 1
    output = prefix + payload
    programs = ["sh", "tail", codec, "python3", command[0]]
    return output, {
        "format": "sh-python3-source-stream-single", "codec": codec, "bytes": len(output),
        "payload_bytes": len(payload), "stub_bytes": len(prefix), "launcher_bytes": len(prefix),
        "payload_scope": "shared compressed Python bootstrap and source literal", "payload_offset_1based": offset,
        "compiler_group": ownership, "python_bytes": len(script), "source_bytes": len(source), "source_literal": kind,
        "sha256": hashlib.sha256(output).hexdigest(), "external_programs": programs,
        "allowlisted_programs_only": all(program in ALLOWED for program in programs),
        "rules_reference": "https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853",
        "under_4096_bytes": len(output) <= 4096, "category": "general-4k",
        "rules_eligibility": "unproven_requires_runtime_and_full_rules_review",
    }


def write_stream(source, destination, command, *, compiler_group):
    destination = Path(destination)
    if not destination.is_absolute():
        raise ValueError("absolute external output required")
    results = []
    for codec in CODECS:
        data, record = make_stream(source, command, codec, compiler_group=compiler_group)
        path = destination / codec / "x"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o755)
        record["path"] = str(path)
        results.append(record)
    return results
