#!/usr/bin/env python3
"""FIRST COST ONLY: one PPM source codec versus the frozen 5,207-byte A entry.

No compiler, engine, games, fault campaign, profile or parameter search runs.
Two independent encodes/reference decodes reconstruct source/bootstrap bytes,
then the complete executable file (all decoder/framing/launcher bytes) counts.
"""
import argparse
import ast
import base64
import hashlib
import json
import lzma
from pathlib import Path
import shutil

import codec
import reference

HERE = Path(__file__).resolve().parent
ENTRY = HERE.parents[1]/"compact"/"tiny-entry-a"
EXPECTED = {
    "source":(11148,"5e0e77321110371aec3a7a06f93290e7581f08f721fc9bb07fcef26c406429b7"),
    "bootstrap":(None,"11679fb20e24e7cb777cb49e4bee5a7ee7ea999278651fbba6d622320e751d44"),
    "whole":(5207,"085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36"),
}


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/".git").exists() for p in (out,*out.parents)):
        parser.error("--out must be new, absolute and outside Git")
    original = {"source":(args.control/"main.c").read_bytes(),
                "bootstrap":(args.control/"bootstrap.py").read_bytes(),"whole":(args.control/"x").read_bytes()}
    for name,data in original.items():
        size,digest = EXPECTED[name]
        if (size is not None and len(data)!=size) or sha(data)!=digest:
            raise ValueError("frozen A identity mismatch: "+name)
    template = (ENTRY/"bootstrap.py.in").read_bytes().replace(b"\r\n",b"\n")
    launcher = (ENTRY/"launcher.sh").read_bytes().replace(b"\r\n",b"\n")
    source = original["source"]
    literal = b"r'''"+source+b"'''.encode()"
    marker = b"__ROVE_SOURCE_LITERAL__"
    if len(launcher)!=75 or template.count(marker)!=1 or template.replace(marker,literal)!=original["bootstrap"]:
        raise ValueError("exact maintained bootstrap/literal reconstruction failed")
    if launcher+lzma.compress(original["bootstrap"],format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                             filters=[{"id":lzma.FILTER_LZMA2,"preset":9|lzma.PRESET_EXTREME,"lc":2,"lp":0,"pb":0}])!=original["whole"]:
        raise ValueError("unchanged complete5,207 control did not reproduce")
    out.mkdir(parents=True)
    frozen = out/"recipe";frozen.mkdir()
    for name in ("codec.py","reference.py","build.py"):
        shutil.copyfile(HERE/name,frozen/name)
    for name,data in (("source.c",source),("control-bootstrap.py",original["bootstrap"]),("control-x",original["whole"]),
                      ("bootstrap.py.in",template),("launcher.sh",launcher)):
        (frozen/name).write_bytes(data)
    report = {"complete":False,"scope":"bounded first-cost only; no engine/runtime qualification",
              "algorithm":"one fixed original order4PPMC-with-exclusion plus byte-range coder",
              "training":False,"parameters_searched":False,"compiler_invocations":0,"engine_launches":0,
              "source_sha256":sha(source),"source_bytes":len(source),"control_whole_bytes":5207,
              "control_whole_sha256":sha(original["whole"]),"control_reproduced_unchanged":True,
              "allowed_existing_programs":["sh","tail","xz","python3","cc"],
              "recipe_sha256":{p.name:sha(p.read_bytes()) for p in sorted(frozen.iterdir())},"attempts":[]}
    first = None
    try:
        decoder = (frozen/"reference.py").read_bytes()
        for attempt in (1,2):
            frame,stats = codec.encode(bytes(source))
            restored = reference.decode(frame)
            if restored!=source:
                raise ValueError("independent full source roundtrip mismatch")
            restored_bootstrap = template.replace(marker,b"r'''"+restored+b"'''.encode()")
            if restored_bootstrap!=original["bootstrap"]:
                raise ValueError("original compiler/bootstrap bytes changed")
            # The wrapper restores the complete original bootstrap byte-for-byte
            # before exec; its original compiler and lifecycle code are intact.
            transport = base64.b85encode(frame)
            wrapper = (decoder+b"\nimport base64\nS=decode(base64.b85decode("+repr(transport).encode()+b"))\n"
                       +b"T="+repr(template).encode()+b"\n"
                       +b'exec(T.replace(b"__ROVE_SOURCE_LITERAL__",b"r\x27\x27\x27"+S+b"\x27\x27\x27.encode()"))\n')
            ast.parse(wrapper)
            captured = []
            exec(wrapper,{"exec":captured.append})
            if captured != [original["bootstrap"]]:
                raise ValueError("packaged wrapper did not restore exact original bootstrap")
            stream = lzma.compress(wrapper,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
                                   filters=[{"id":lzma.FILTER_LZMA2,"preset":9|lzma.PRESET_EXTREME,"lc":2,"lp":0,"pb":0}])
            whole = launcher+stream
            if first is None:first=(frame,wrapper,whole)
            elif first!=(frame,wrapper,whole):raise ValueError("independent encoding/complete file reproduction mismatch")
            directory = out/("attempt-"+str(attempt));directory.mkdir()
            (directory/"source.ppm").write_bytes(frame)
            (directory/"wrapper.py").write_bytes(wrapper)
            (directory/"restored.c").write_bytes(restored)
            (directory/"restored-bootstrap.py").write_bytes(restored_bootstrap)
            (directory/"x").write_bytes(whole);(directory/"x").chmod(0o755)
            report["attempts"].append({"attempt":attempt,**stats,"base85_bytes":len(transport),
                "decoder_source_bytes":len(decoder),"wrapper_source_bytes":len(wrapper),"launcher_bytes":len(launcher),
                "whole_bytes":len(whole),"whole_sha256":sha(whole),"frame_sha256":sha(frame),
                "source_roundtrip_sha256":sha(restored),"bootstrap_roundtrip_sha256":sha(restored_bootstrap),
                "delta_from5207":len(whole)-5207,"under4096":len(whole)<=4096})
        report["complete"] = True
        report["result"] = "size_loss_stop" if len(first[2])>=5207 else "first_cost_gain_requires_separate_qualification"
        report["whole_bytes"] = len(first[2])
        report["runtime_validation"] = "not_run_first_cost_only"
    except Exception as error:
        report["failure"] = repr(error)
        raise
    finally:
        (out/"first-cost.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":main()
