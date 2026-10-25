"""Explicit Clang static-kernel recipe, separate from GCC source-JIT admission.

This recipe consumes freshly regenerated readable C. It has no LTO dependency,
does not edit algorithms, and does not admit its output through an old hash map.
Actual semantic/runtime and target qualification remain separate observations.
"""
import hashlib
import struct

KIND = "D-Clang18-static-native-recipe-v1"
OPTS = ("z", "s")
UNITS = ("main.c", "start.S")
DRIVER = b'#include "board.c"\n#include "search.c"\n#include "runtime.c"\n'


def pin(data):
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def flags(profile,opt):
    if opt not in OPTS:
        raise ValueError("finite explicit Clang optimization required")
    return ["--target=x86_64-pc-linux-gnu","-O"+opt,"-std=c11","-nostdlib","-static","-no-pie",
        "-fno-pie","-fno-pic","-fno-stack-protector","-fno-builtin","-fno-asynchronous-unwind-tables",
        "-fno-unwind-tables","-fno-ident","-fcf-protection=none","-ffunction-sections","-fdata-sections",
        "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack","-msse4.2","-mcx16","-DDEV=0","-DD_HQ=0",
        f"-DWORKERS={profile.workers}",f"-DTT_BITS={profile.layout(16).bits}"]


def prepared(source,storage,startup,owner,publication,arity,profile):
    base,production=startup.prepared(source,profile,True,storage,"prefix")
    owned,owner_proof=owner.transform(base,publication)
    if owner.restore(owned,owner_proof,publication)!=base:
        raise ValueError("Clang recipe owner inverse differs")
    files,arity_proof=arity.transform(owned,owner,publication,owner_proof,noinline_wake=True,immediate_exit=True)
    if arity.restore(files,arity_proof,owner,publication)!=owned:
        raise ValueError("Clang recipe arity inverse differs")
    if any(files[n]!=base[n] for n in ("tiny.h","board.c","search.c","start.S","image.ld")):
        raise ValueError("Clang recipe altered protected algorithm/input files")
    return files,dict(kind=KIND,production=production,owner=owner_proof,arity=arity_proof,
        readable={n:pin(d) for n,d in files.items()},resource=profile.to_record(16),
        single_TU_driver=pin(DRIVER),LTO=False,compiler_codegen_changed=True,
        no_old_native_identity_claim=True,source_JIT_compiler_changed=False,
        search_features_removed=False,runtime_qualified=False,target22_qualified=False,selected=False)


def kernel_type(image):
    if (image[:7]!=b"\x7fELF\x02\x01\x01" or len(image)<232 or
            struct.unpack_from("<HH",image,16)!=(2,62)):
        raise ValueError("static x86-64 little-endian ET_EXEC required")
    phoff=struct.unpack_from("<Q",image,32)[0]
    size,count=struct.unpack_from("<HH",image,54)
    if size!=56 or count!=3 or phoff+size*count>len(image):
        raise ValueError("closed three program-header kernel shape required")
    kinds=[struct.unpack_from("<I",image,phoff+i*size)[0] for i in range(count)]
    if kinds!=[1,1,0x6474E551]:
        raise ValueError("interpreter/dynamic/TLS or unknown ELF segment")
    return dict(elf_class=64,endianness="little",machine=62,type="ET_EXEC",static=True,
                PT_INTERP=False,PT_DYNAMIC=False,PT_TLS=False,program_header_types=kinds)
