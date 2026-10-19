"""Deterministic complete-file general 4K source/native launchers.

The launcher uses Python 3 and its standard library. Source packages additionally
invoke the selected compiler. No executable, model or configuration is downloaded.
All source, data, fixed compiler arguments and restoration code count in file size.
"""

import base64
import bz2
import hashlib
import io
import lzma
from pathlib import Path
import struct
import zlib
import zipfile


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def archive_files(files):
    result = bytearray(struct.pack("<I", len(files)))
    for name, data in sorted(files.items()):
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or not name or "\\" in name:
            raise ValueError("archive names must be safe relative POSIX paths")
        encoded = name.encode()
        if len(encoded) > 65535:
            raise ValueError("archive path is too long")
        result += struct.pack("<HI", len(encoded), len(data)) + encoded + data
    return bytes(result)


def make_launcher(files, *, command, binary="x", environment=None, codec="zlib", transport="base85"):
    raw = archive_files(files)
    codecs = {"zlib": ("zlib", zlib.compress(raw, 9)),
              "bz2": ("bz2", bz2.compress(raw, 9)),
              "lzma": ("lzma", lzma.compress(raw, preset=9, format=lzma.FORMAT_XZ))}
    if codec not in codecs:
        raise ValueError("unsupported launcher codec")
    module, compressed = codecs[codec]
    blob = base64.b85encode(compressed)
    # The compiler gets a private process group. Interruption forwards to the
    # entire compiler group and waits before TemporaryDirectory removes inputs.
    # After compilation the ELF stays open across cleanup, then fd exec replaces
    # Python. The running engine therefore has no wrapper parent or temp files.
    compile_line = ""
    if command:
        compile_line = " e=os.environ.copy();e.update(" + repr(environment or {}) + ")\n"
        compile_line += " try:\n"
        compile_line += "  m=signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n"
        compile_line += "  try:p=subprocess.Popen(" + repr(command) + ",cwd=d,env=e,start_new_session=True,preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,m))\n"
        compile_line += "  finally:signal.pthread_sigmask(signal.SIG_SETMASK,m)\n"
        compile_line += "  r=p.wait()\n"
        compile_line += " finally:\n"
        compile_line += "  if p is not None and p.poll() is None:\n"
        compile_line += "   try:os.killpg(p.pid,q)\n"
        compile_line += "   except ProcessLookupError:pass\n"
        compile_line += "   try:p.wait(timeout=5)\n"
        compile_line += "   except subprocess.TimeoutExpired:os.killpg(p.pid,9);p.wait()\n"
        compile_line += " if r:sys.exit(r)\n"
    script = (
        "#!/usr/bin/python3\n"
        "import base64,os,signal,struct,subprocess,sys,tempfile," + module + "\n"
        "p=None;q=15\n"
        "def stop(s,f):\n"
        " global q\n q=s\n"
        " signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n"
        " raise SystemExit(128+s)\n"
        "signal.signal(2,stop);signal.signal(15,stop)\n"
        "b=" + module + ".decompress(base64.b85decode(" + repr(blob) + "))\n"
        "with tempfile.TemporaryDirectory(prefix='r4-') as d:\n"
        " p=4\n"
        " for _ in range(struct.unpack_from('<I',b)[0]):\n"
        "  n,s=struct.unpack_from('<HI',b,p);p+=6;f=d+'/'+b[p:p+n].decode();p+=n\n"
        "  os.makedirs(os.path.dirname(f),exist_ok=True)\n"
        "  with open(f,'wb') as o:o.write(b[p:p+s])\n"
        "  p+=s\n"
        + compile_line +
        " f=d+'/" + binary + "';os.chmod(f,448)\n"
        " fd=os.open(f,os.O_RDONLY)\n"
        "signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n"
        "os.execve(fd,sys.argv,os.environ)\n"
    ).encode()
    output = script
    format_name = "python3-source" if command else "python3-native"
    payload_bytes, encoded_bytes = len(compressed), len(blob)
    if transport == "zip":
        # A Python zipapp stores binary compressed data directly. Its executable
        # archive, central directory and compressed bootstrap all count in size;
        # no base85 expansion and no runtime unzip subprocess are needed.
        script = script.replace(b"import base64,os,signal,struct,subprocess,sys,tempfile," + module.encode(),
                                b"import os,signal,struct,subprocess,sys,tempfile,zipfile")
        script = script.replace(b"b=" + module.encode() + b".decompress(base64.b85decode(" + repr(blob).encode() + b"))",
                                b"b=zipfile.ZipFile(sys.argv[0]).read('p')")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, data, compression in (("__main__.py", script, zipfile.ZIP_DEFLATED),
                                             ("p", raw, {"zlib": zipfile.ZIP_DEFLATED,
                                                         "bz2": zipfile.ZIP_BZIP2,
                                                         "lzma": zipfile.ZIP_LZMA}[codec])):
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = compression
                entry.create_system = 3
                entry.external_attr = 0o644 << 16
                archive.writestr(entry, data, compresslevel=9 if compression != zipfile.ZIP_LZMA else None)
            payload_bytes = archive.getinfo("p").compress_size
        output = b"#!/usr/bin/python3\n" + buffer.getvalue()
        format_name += "-zipapp"
        encoded_bytes = payload_bytes
    elif transport != "base85":
        raise ValueError("unknown launcher transport")
    return output, {"format": format_name,
                    "codec": codec, "payload_bytes": len(compressed),
                    "launcher_bytes": len(output) - encoded_bytes,
                    "encoded_payload_bytes": encoded_bytes, "bytes": len(output),
                    "transport": transport, "stored_payload_bytes": payload_bytes,
                    "sha256": sha256(output),
                    "external_programs": ["python3"] + ([command[0]] if command else []),
                    "category": "general-4k", "under_4096_bytes": len(output) <= 4096,
                    "rules_eligibility": "unproven_requires_runtime_and_full_rules_review"}


def write_launchers(files, destination, *, command=None, binary="x", environment=None):
    destination = Path(destination)
    if not destination.is_absolute():
        raise ValueError("output directory must be absolute")
    results = []
    for transport in ("base85", "zip"):
        for codec in ("zlib", "bz2", "lzma"):
            output = destination / (transport + "-" + codec) / "x"
            output.parent.mkdir(parents=True, exist_ok=True)
            data, record = make_launcher(files, command=command, binary=binary,
                                         environment=environment, codec=codec, transport=transport)
            output.write_bytes(data)
            output.chmod(0o755)
            record["path"] = str(output)
            results.append(record)
    return results
