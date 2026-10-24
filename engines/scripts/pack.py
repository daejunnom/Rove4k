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
import os
from pathlib import Path
import struct
import sys
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


def _zip_output(script, raw, codec):
    """The same deterministic container for archive and direct-ELF payloads."""
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
    return b"#!/usr/bin/python3\n" + buffer.getvalue(), payload_bytes


def memfd_support():
    """Read this Linux host's support/policy; never change it or try weaker flags.

    The emitted MFD_EXEC request remains kernel-enforced if policy later changes.
    A missing old-kernel sysctl does not imply execution support: runtime still
    requires MFD_EXEC, without an EINVAL fallback. A real ELF fixture qualifies
    host execution separately from this source/preflight description.
    """
    if sys.platform != "linux" or not hasattr(os, "memfd_create") or os.execve not in os.supports_fd:
        raise ValueError("memfd requires Linux memfd_create and fd execve support")
    policy = None
    try:
        policy = int(Path("/proc/sys/vm/memfd_noexec").read_text().strip())
    except FileNotFoundError:
        pass
    if policy not in (None, 0, 1, 2):
        raise ValueError("unknown executable memfd policy")
    if policy == 2:
        raise ValueError("executable memfd is prohibited by vm.memfd_noexec=2")
    return {"vm.memfd_noexec": policy, "flags": 17,
            "weaker_flags_or_file_fallback": False, "execution_qualified": False}


def _single_native_launcher(files, *, command, binary, codec, transport, backend, elf_admission):
    # The caller passes its frozen ELF validator, like the frozen compiler owner.
    # This is an explicit producer dependency, not callback authentication.
    if command is not None or set(files) != {binary}:
        raise ValueError("single native backend requires one binary and no compiler")
    if type(binary) is not str or not binary or binary in (".", "..") or "/" in binary or "\\" in binary or "\0" in binary:
        raise ValueError("single native binary must be a safe leaf name")
    raw = files[binary]
    if type(raw) is not bytes or not callable(elf_admission):
        raise ValueError("immutable native bytes and the frozen ELF admission are required")
    elf = elf_admission(raw)
    if not isinstance(elf, dict):
        raise ValueError("ELF admission did not return its description")
    support = memfd_support() if backend == "memfd" else None
    compressors = {"zlib": lambda: zlib.compress(raw, 9),
                   "bz2": lambda: bz2.compress(raw, 9),
                   "lzma": lambda: lzma.compress(raw, preset=9, format=lzma.FORMAT_XZ)}
    if codec not in compressors or transport not in ("base85", "zip"):
        raise ValueError("unsupported single native codec or transport")
    compressed = compressors[codec]() if transport == "base85" else b""
    blob = base64.b85encode(compressed)
    imports = "base64,os,signal,sys" + (",tempfile" if backend == "file" else "") + "," + codec
    decode = codec + ".decompress(base64.b85decode(" + repr(blob) + "))"
    if transport == "zip":
        imports = "os,signal,sys" + (",tempfile" if backend == "file" else "") + ",zipfile"
        decode = "zipfile.ZipFile(sys.argv[0]).read('p')"
    preparation = (
        " with tempfile.TemporaryDirectory(prefix='r4-') as d:\n"
        "  f=d+" + repr('/'+binary) + "\n"
        "  with open(f,'wb') as o:put(o.fileno(),b)\n"
        "  os.chmod(f,448)\n"
        "  fd=os.open(f,os.O_RDONLY)\n"
        if backend == "file" else
        " fd=os.memfd_create('r4',getattr(os,'MFD_EXEC',16)|1)\n put(fd,b)\n")
    script = (
        "#!/usr/bin/python3\nimport " + imports + "\n"
        "def stop(s,f):\n signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n raise SystemExit(128+s)\n"
        "signal.signal(2,stop);signal.signal(15,stop)\n"
        "def put(fd,b):\n v=memoryview(b)\n while v:\n"
        "  n=os.write(fd,v)\n  if n<=0:raise OSError('native write made no progress')\n  v=v[n:]\n"
        "b=" + decode + "\nfd=None\ntry:\n" + preparation +
        " signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n"
        " os.execve(fd,sys.argv,os.environ)\n"
        "except BaseException:\n if fd is not None:\n"
        "  try:os.close(fd)\n  except OSError as e:\n"
        "   try:print('native FD close:',e,file=sys.stderr)\n   except BaseException:pass\n raise\n"
    ).encode()
    output, payload_bytes = script, len(compressed)
    format_name = "python3-native-single-" + backend
    encoded_bytes = len(blob)
    if transport == "zip":
        output, payload_bytes = _zip_output(script, raw, codec)
        format_name += "-zipapp"
        encoded_bytes = payload_bytes
    return output, {"format": format_name, "compiler_group": None,
                    "native_backend": backend, "native_bytes": len(raw), "native_sha256": sha256(raw),
                    "elf": elf, "memfd_host_support": support,
                    "codec": codec, "payload_bytes": payload_bytes,
                    "launcher_bytes": len(output)-encoded_bytes, "encoded_payload_bytes": encoded_bytes,
                    "bytes": len(output), "transport": transport, "stored_payload_bytes": payload_bytes,
                    "sha256": sha256(output), "external_programs": ["python3"],
                    "category": "general-4k", "under_4096_bytes": len(output) <= 4096,
                    "rules_eligibility": "unproven_requires_runtime_and_full_rules_review",
                    "observation_contract": {"argv": "sys.argv", "environment": "os.environ",
                        "signal_during_restore": "SystemExit(128+s), INT/TERM additionally blocked",
                        "success": "read-only file FD after path cleanup" if backend == "file" else "MFD_EXEC|CLOEXEC and fd exec, no weaker fallback",
                        "secondary_close_error": "stderr when writable; diagnostic failure cannot replace primary exception",
                        "self_path_and_AT_EXECFN": "memfd differs" if backend == "memfd" else "deleted private file"}}


def make_launcher(files, *, command, binary="x", environment=None, codec="zlib", transport="base85", compiler_group=None,
                  native_backend="archive", elf_admission=None):
    if native_backend not in ("archive", "file", "memfd"):
        raise ValueError("unknown native backend")
    if native_backend != "archive":
        return _single_native_launcher(files, command=command, binary=binary, codec=codec,
                                       transport=transport, backend=native_backend, elf_admission=elf_admission)
    raw = archive_files(files)
    codecs = {"zlib": lambda: zlib.compress(raw, 9),
              "bz2": lambda: bz2.compress(raw, 9),
              "lzma": lambda: lzma.compress(raw, preset=9, format=lzma.FORMAT_XZ)}
    if codec not in codecs:
        raise ValueError("unsupported launcher codec")
    module, compressed = codec, codecs[codec]() if transport == "base85" else b""
    blob = base64.b85encode(compressed)
    # The compiler gets a private process group. Interruption forwards to the
    # entire compiler group and waits before TemporaryDirectory removes inputs.
    # After compilation the ELF stays open across cleanup, then fd exec replaces
    # Python. The running engine therefore has no wrapper parent or temp files.
    compile_line = ""
    if command:
        compile_line = " e=os.environ.copy();e.update(" + repr(environment or {}) + ");e['TMPDIR']=d\n"
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
        " a=4\n"
        " for _ in range(struct.unpack_from('<I',b)[0]):\n"
        "  n,s=struct.unpack_from('<HI',b,a);a+=6;f=d+'/'+b[a:a+n].decode();a+=n\n"
        "  os.makedirs(os.path.dirname(f),exist_ok=True)\n"
        "  with open(f,'wb') as o:o.write(b[a:a+s])\n"
        "  a+=s\n"
        + compile_line +
        " f=d+'/" + binary + "';os.chmod(f,448)\n"
        " fd=os.open(f,os.O_RDONLY)\n"
        "signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n"
        "os.execve(fd,sys.argv,os.environ)\n"
    ).encode()
    ownership = None
    if command:
        if compiler_group is None:
            raise ValueError("source packaging requires the frozen compiler-group owner")
        script, ownership = compiler_group(script)
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
        output, payload_bytes = _zip_output(script, raw, codec)
        format_name += "-zipapp"
        encoded_bytes = payload_bytes
    elif transport != "base85":
        raise ValueError("unknown launcher transport")
    return output, {"format": format_name, "compiler_group": ownership,
                    "codec": codec, "payload_bytes": payload_bytes,
                    "launcher_bytes": len(output) - encoded_bytes,
                    "encoded_payload_bytes": encoded_bytes, "bytes": len(output),
                    "transport": transport, "stored_payload_bytes": payload_bytes,
                    "sha256": sha256(output),
                    "external_programs": ["python3"] + ([command[0]] if command else []),
                    "category": "general-4k", "under_4096_bytes": len(output) <= 4096,
                    "rules_eligibility": "unproven_requires_runtime_and_full_rules_review"}


def write_launchers(files, destination, *, command=None, binary="x", environment=None, compiler_group=None,
                    native_backend="archive", elf_admission=None):
    destination = Path(destination)
    if not destination.is_absolute():
        raise ValueError("output directory must be absolute")
    results = []
    for transport in ("base85", "zip"):
        for codec in ("zlib", "bz2", "lzma"):
            output = destination / (transport + "-" + codec) / "x"
            output.parent.mkdir(parents=True, exist_ok=True)
            data, record = make_launcher(files, command=command, binary=binary,
                                         environment=environment, codec=codec, transport=transport,
                                         compiler_group=compiler_group, native_backend=native_backend,
                                         elf_admission=elf_admission)
            output.write_bytes(data)
            output.chmod(0o755)
            record["path"] = str(output)
            results.append(record)
    return results
