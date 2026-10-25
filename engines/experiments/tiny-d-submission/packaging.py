"""General-4K Python bootstraps; payload and bootstrap both count toward size.

Native payloads enter through a CLOEXEC memfd. Source-JIT inputs are compiled
in one private directory; the executable is opened and every pathname removed
before fdexec. Both routes preserve stdin and never unlink a stored baseline.
"""
import json
import lzma
import shlex


def envelope(code, payload):
    size = 0
    for _ in range(20):
        body = code.replace("PAYLOAD_OFFSET", str(size))
        header = ("#!/bin/sh\nexec python3 -c " + shlex.quote(body) + ' "$0"\n').encode()
        if len(header) == size:
            return header + payload, header
        size = len(header)
    raise ValueError("bootstrap offset failed to stabilize")


NATIVE_CODE = '''import os,lzma,sys
b=lzma.decompress(open(sys.argv[1],"rb").read()[PAYLOAD_OFFSET:])
f=os.memfd_create("Rove4k-D",1)
os.write(f,b)==len(b) or sys.exit(2)
os.execve(f,["Rove4k-D"],os.environ)'''

SOURCE_CODE = '''import os,lzma,sys,json,tempfile,pathlib,subprocess
b=json.loads(lzma.decompress(open(sys.argv[1],"rb").read()[PAYLOAD_OFFSET:]))
with tempfile.TemporaryDirectory(prefix="rove4k-d-") as d:
 for n,s in b["files"].items():pathlib.Path(d,n).write_text(s)
 subprocess.run(["cc",*b["flags"],*[d+"/"+n for n in b["units"]],"-Wl,-T,"+d+"/image.ld","-o",d+"/x"],stdin=subprocess.DEVNULL,check=True)
 f=os.open(d+"/x",os.O_RDONLY)
os.execve(f,["Rove4k-D"],os.environ)'''


def encode(data, kind):
    if kind == "alone":
        return lzma.compress(data, format=lzma.FORMAT_ALONE,
                             filters=[dict(id=lzma.FILTER_LZMA1, preset=9 | lzma.PRESET_EXTREME)])
    filters = [dict(id=lzma.FILTER_X86)] if kind == "xz-bcj" else []
    if kind not in ("xz", "xz-bcj"):
        raise ValueError("unknown finite general codec")
    return lzma.compress(data, format=lzma.FORMAT_XZ,
                         filters=filters + [dict(id=lzma.FILTER_LZMA2, preset=9 | lzma.PRESET_EXTREME)])


def package_native(native, kind):
    payload = encode(native, kind)
    if lzma.decompress(payload) != native:
        raise ValueError("native inverse differs")
    whole, header = envelope(NATIVE_CODE, payload)
    return whole, dict(codec=kind, header_bytes=len(header), payload_bytes=len(payload),
                       restoration="complete kernel-executable ELF", cleanup="memfd-CLOEXEC")


def package_source(files, flags, units):
    # No DEV/HQ headers or conditions remain in these preprocessed C units.
    bundle = json.dumps(dict(files={n: files[n].decode() for n in sorted(files)},
                             flags=list(flags), units=list(units)),
                        separators=(",", ":"), ensure_ascii=True).encode()
    payload = encode(bundle, "alone")
    if lzma.decompress(payload) != bundle:
        raise ValueError("source bundle inverse differs")
    whole, header = envelope(SOURCE_CODE, payload)
    return whole, dict(codec="alone", header_bytes=len(header), payload_bytes=len(payload),
                       source_bundle_bytes=len(bundle), restoration="preprocessed scalar D C/S/linker inputs",
                       cleanup="all filesystem inputs and native removed before fdexec")
