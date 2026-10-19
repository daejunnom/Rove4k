#!/usr/bin/env python3
"""Exact alternative storage for the frozen E model; no fitting or quantization.

Outputs are generated outside the checkout. Existing canonical inputs are never
modified. static16 additionally returns explicit consumer changes for a separate
immutable-data candidate rather than pretending a constant-return decoder removes
the consumers' initialization machinery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

MODEL_DIR = Path(__file__).resolve().parents[1]
ROOT = MODEL_DIR.parents[1]
sys.path.insert(0, str(MODEL_DIR))
from codec import (canonical_bytes, coefficient_bounds, decode_signed, encode_signed,
                   generated_sources, load_model)

FORMATS = ("varint", "int16", "split8", "scaled8", "scaled6", "static16")


def checked_weights(weights):
    if len(weights) != 21:
        raise ValueError("exactly 21 evaluation-then-ordering weights required")
    encode_signed(weights)
    return list(weights)


def scaled_values(weights):
    if any(w % 10 for w in weights[:5]):
        raise ValueError("material coefficients must be exactly divisible by 10")
    return [w // 10 for w in weights[:5]] + list(weights[5:])


def pack_weights(fmt, weights):
    weights = checked_weights(weights)
    if fmt == "varint":
        return encode_signed(weights)
    if fmt in ("int16", "static16"):
        return struct.pack("<21h", *weights)
    if fmt == "split8":
        if any(not -128 <= w <= 127 for w in weights[5:]):
            raise ValueError("split8 tail must fit signed 8-bit")
        return struct.pack("<5h16b", *weights)
    if fmt in ("scaled8", "scaled6"):
        values = scaled_values(weights)
        if any(not -128 <= w <= 127 for w in values[:5]):
            raise ValueError("scaled material quotients must fit signed 8-bit")
        tail_limit = 128 if fmt == "scaled8" else 32
        if any(not -tail_limit <= w < tail_limit for w in values[5:]):
            raise ValueError("scaled tail outside its signed storage range")
        if fmt == "scaled8":
            return struct.pack("21b", *values)
        out = bytearray(struct.pack("5b", *values[:5]))
        accumulator = bits = 0
        for value in values[5:]:
            u = 2 * value if value >= 0 else -2 * value - 1
            accumulator |= u << bits
            bits += 6
            while bits >= 8:
                out.append(accumulator & 255)
                accumulator >>= 8
                bits -= 8
        if bits:
            raise AssertionError("16 six-bit coefficients must be byte-aligned")
        return bytes(out)
    raise ValueError("unknown representation: " + fmt)


def unpack_weights(fmt, data):
    sizes = {"int16": 42, "static16": 42, "split8": 26, "scaled8": 21, "scaled6": 17}
    if fmt in sizes and len(data) != sizes[fmt]:
        raise ValueError("representation length mismatch")
    if fmt == "varint":
        values = decode_signed(data, 21)
    elif fmt in ("int16", "static16"):
        values = list(struct.unpack("<21h", data))
    elif fmt == "split8":
        values = list(struct.unpack("<5h16b", data))
    elif fmt == "scaled8":
        values = [v * (10 if i < 5 else 1) for i, v in enumerate(struct.unpack("21b", data))]
    elif fmt == "scaled6":
        values = [v * 10 for v in struct.unpack("5b", data[:5])]
        accumulator = bits = 0
        p = 5
        for _ in range(16):
            while bits < 6:
                accumulator |= data[p] << bits
                bits += 8
                p += 1
            u = accumulator & 63
            values.append(-(u // 2) - 1 if u & 1 else u // 2)
            accumulator >>= 6
            bits -= 6
    else:
        raise ValueError("unknown representation: " + fmt)
    if pack_weights(fmt, values) != bytes(data):
        raise ValueError("noncanonical representation")
    return values


def sources(fmt, model):
    if max(coefficient_bounds(model)) >= 2**31:
        raise ValueError("model may overflow the signed-32 runtime accumulator")
    weights = model["evaluation"]["weights"] + model["ordering"]["weights"]
    payload = pack_weights(fmt, weights)
    if unpack_weights(fmt, payload) != weights:
        raise ValueError("representation changed model coefficients")
    if fmt == "varint":
        return generated_sources(model)
    values = ",".join(map(str, weights))
    signed_bytes = ",".join(map(str, struct.unpack(f"{len(payload)}b", payload)))
    unsigned_bytes = ",".join(map(str, payload))
    if fmt in ("int16", "static16"):
        c_data = f"static const int16_t rove_e_static_weights[21]={{{values}}};"
        c_body = "for(unsigned i=0;i<21;i++)out[i]=rove_e_static_weights[i];"
        rs_data = f"pub static MODEL_WEIGHTS:[i16;21]=[{values}];"
        rs_body = "MODEL_WEIGHTS"
    elif fmt == "split8":
        first = ",".join(map(str, weights[:5]))
        tail = ",".join(map(str, weights[5:]))
        c_data = (f"static const int16_t rove_e_material[5]={{{first}}};\n"
                  f"static const int8_t rove_e_tail[16]={{{tail}}};")
        c_body = ("for(unsigned i=0;i<5;i++)out[i]=rove_e_material[i];"
                  "for(unsigned i=0;i<16;i++)out[i+5]=rove_e_tail[i];")
        rs_data = f"const MATERIAL:[i16;5]=[{first}];\nconst TAIL:[i8;16]=[{tail}];"
        rs_body = ("let mut out=[0;21];for i in 0..5{out[i]=MATERIAL[i];}"
                   "for i in 0..16{out[i+5]=i16::from(TAIL[i]);}out")
    elif fmt == "scaled8":
        c_data = f"static const int8_t rove_e_packed[21]={{{signed_bytes}}};"
        c_body = "for(unsigned i=0;i<21;i++)out[i]=(int16_t)(rove_e_packed[i]*(i<5?10:1));"
        rs_data = f"const PACKED:[i8;21]=[{signed_bytes}];"
        rs_body = ("let mut out=[0;21];for i in 0..21{"
                   "out[i]=i16::from(PACKED[i])*if i<5{10}else{1};}out")
    elif fmt == "scaled6":
        c_data = f"static const uint8_t rove_e_packed[17]={{{unsigned_bytes}}};"
        c_body = ("for(unsigned i=0;i<5;i++)out[i]=(int16_t)(10*((int)(rove_e_packed[i]^128)-128));"
                  "unsigned a=0,bits=0,p=5;for(unsigned i=5;i<21;i++){"
                  "while(bits<6){a|=(unsigned)rove_e_packed[p++]<<bits;bits+=8;}"
                  "unsigned u=a&63;int v=(int)(u>>1);out[i]=(int16_t)((u&1)?-v-1:v);a>>=6;bits-=6;}")
        rs_data = f"const PACKED:[u8;17]=[{unsigned_bytes}];"
        rs_body = ("let mut out=[0;21];for i in 0..5{out[i]=i16::from(PACKED[i] as i8)*10;}"
                   "let(mut a,mut bits,mut p)=(0u32,0,5);for i in 5..21{"
                   "while bits<6{a|=u32::from(PACKED[p])<<bits;bits+=8;p+=1;}"
                   "let u=a&63;let v=(u>>1) as i16;out[i]=if u&1!=0{-v-1}else{v};"
                   "a>>=6;bits-=6;}out")
    else:
        raise ValueError("unknown representation: " + fmt)
    digest = hashlib.sha256(canonical_bytes(model)).hexdigest()
    comment = (f"Generated exact runtime representation: {fmt}; payload {len(payload)} bytes. "
               f"Canonical reference model SHA-256: {digest}. "
               "frozen.json.encoding identifies its reference codec, not this experiment.")
    c = (f"/* {comment} */\n#ifndef ROVE_E_FROZEN_H\n#define ROVE_E_FROZEN_H\n#include <stdint.h>\n"
         "enum{ROVE_E_EVAL_COUNT=16,ROVE_E_ORDER_COUNT=5,ROVE_E_WEIGHT_COUNT=21};\n"
         f"{c_data}\nstatic inline void rove_e_weights(int16_t out[21]){{{c_body}}}\n#endif\n")
    rust = f"// {comment}\n{rs_data}\npub fn model_weights()->[i16;21]{{{rs_body}}}\n"
    return {"frozen.h": c, "frozen.rs": rust}


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError("consumer contract changed; inspect and update the explicit static16 transform")
    return source.replace(before, after)


def static_consumer(language, source):
    """Explicit code/data candidate transform, applied to frozen copies only."""
    source = source.replace("\r\n", "\n")
    if language == "c":
        source = replace_once(source,
            "static int16_t rove_model_weights[ROVE_E_WEIGHT_COUNT];",
            "#define rove_model_weights rove_e_static_weights")
        return replace_once(source,
            "static inline void rove_model_init(void)\n{\n    rove_e_weights(rove_model_weights);\n}",
            "static inline void rove_model_init(void) {}")
    if language == "rust":
        source = replace_once(source, "use std::sync::OnceLock;\n", "")
        source = replace_once(source, "static MODEL: OnceLock<[i16; 21]> = OnceLock::new();\n", "")
        source = replace_once(source,
            "pub fn init_model() {\n    MODEL.get_or_init(frozen::model_weights);\n}",
            "pub fn init_model() {}")
        before = "MODEL.get_or_init(frozen::model_weights)"
        if source.count(before) != 3:
            raise ValueError("expected exactly model, SIMD model and ordering weight consumers")
        return source.replace(before, "&frozen::MODEL_WEIGHTS")
    raise ValueError("unknown language")


def metadata(fmt, model):
    weights = model["evaluation"]["weights"] + model["ordering"]["weights"]
    payload = pack_weights(fmt, weights)
    return {"runtime_representation": fmt, "parameters": 21, "payload_bytes": len(payload),
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "model_id": model["id"], "provenance": model["provenance"],
            "canonical_reference_sha256": hashlib.sha256(canonical_bytes(model)).hexdigest(),
            "restored_i16le_sha256": hashlib.sha256(struct.pack("<21h", *weights)).hexdigest(),
            "consumer": "immutable direct table, no decoder/OnceLock" if fmt == "static16" else
                        "same startup decode/copy API and initialized i16 consumers",
            "is_quantization": False, "whole_artifact_cost": "must be measured separately"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=FORMATS, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-tree", type=Path, help="optional frozen c/model.h or rust/eval.rs input tree")
    parser.add_argument("--language", choices=("c", "rust"), help="consumer to transform for static16")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.resolve().is_relative_to(ROOT):
        parser.error("--out must be absolute and outside the checkout")
    if args.format == "static16" and (args.source_tree is None or args.language is None):
        parser.error("static16 requires explicit frozen --source-tree and --language")
    model = load_model()
    output = {"model/" + name: text for name, text in sources(args.format, model).items()}
    if args.format == "static16":
        path = "c/model.h" if args.language == "c" else "rust/eval.rs"
        output[path] = static_consumer(args.language, (args.source_tree / path).read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    for name, text in output.items():
        path = args.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    record = metadata(args.format, model)
    (args.out / "representation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
