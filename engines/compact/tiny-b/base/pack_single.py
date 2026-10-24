"""Complete ZIP source launcher specialized to one C translation unit on stdin.

The selected fixed compiler command must consume C on stdin and produce `x`.
The runtime owns its temporary directory, forwards compile interruption to the
whole compiler process group, waits for it, removes all files, and fd-execs the
ELF. The specialization removes the generic multi-file restoration parser.
"""
import hashlib
import io
from pathlib import Path
import zipfile


def make_single(source, command, codec="lzma"):
    if codec not in ("zlib", "bz2", "lzma"):
        raise ValueError("unsupported codec")
    script = (
        "import os,signal,subprocess,sys,tempfile,zipfile\n"
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
        "  p.communicate(zipfile.ZipFile(sys.argv[0]).read('c'))\n"
        " finally:\n"
        "  if p is not None and p.poll() is None:\n"
        "   try:os.killpg(p.pid,q)\n"
        "   except ProcessLookupError:pass\n"
        "   try:p.wait(timeout=5)\n"
        "   except subprocess.TimeoutExpired:os.killpg(p.pid,9);p.wait()\n"
        " if p.returncode:sys.exit(p.returncode)\n"
        " fd=os.open(d+'/x',os.O_RDONLY)\n"
        "signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n"
        "os.execve(fd,sys.argv,os.environ)\n"
    ).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data, compression in (("__main__.py", script, zipfile.ZIP_DEFLATED),
                                         ("c", source, {"zlib": zipfile.ZIP_DEFLATED,
                                                        "bz2": zipfile.ZIP_BZIP2,
                                                        "lzma": zipfile.ZIP_LZMA}[codec])):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = compression
            entry.create_system = 3
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, data, compresslevel=9 if compression != zipfile.ZIP_LZMA else None)
        payload = archive.getinfo("c").compress_size
    output = b"#!/usr/bin/python3\n" + buffer.getvalue()
    return output, {"format": "python3-source-zipapp-single", "codec": codec, "bytes": len(output),
                    "payload_bytes": payload, "launcher_bytes": len(output) - payload,
                    "sha256": hashlib.sha256(output).hexdigest(), "external_programs": ["python3", command[0]],
                    "under_4096_bytes": len(output) <= 4096, "category": "general-4k",
                    "rules_eligibility": "unproven_requires_runtime_and_full_rules_review"}


def write_single(source, destination, command):
    destination = Path(destination)
    if not destination.is_absolute():
        raise ValueError("absolute external output required")
    results = []
    for codec in ("zlib", "bz2", "lzma"):
        data, record = make_single(source, command, codec)
        path = destination / codec / "x"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o755)
        record["path"] = str(path)
        results.append(record)
    return results
