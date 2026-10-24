#!/usr/bin/env python3
"""Independent fixed-model H24/base10 encoder; Python standard library only.

This implements the inverse of the project-owned integer decoder ABI. It
never imports or invokes an upstream compressor, compiler, loader or engine.
CLI inputs and the fixed model file are supplied with explicit SHA-256 pins.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode=True
_range_path=Path(__file__).resolve().with_name('range_bits.py')
_range_spec=importlib.util.spec_from_file_location('rove_context_integer_range',_range_path)
_range_module=importlib.util.module_from_spec(_range_spec)
_range_spec.loader.exec_module(_range_module)
Encoder=_range_module.Encoder

U32=(1<<32)-1
U64=(1<<64)-1
FORMAT='rove4k-context-h24-base10-u32-zero4-v1'
PACKET_FORMAT='rove4k-context-h24-base10-fixed21-replay-zero4-v2'
TABLE_BYTES=1<<25

def sha(data):return hashlib.sha256(data).hexdigest()

def _crc_table():
    values=[]
    for byte in range(256):
        value=byte
        for _ in range(8):value=(value>>1)^(0x82f63b78 if value&1 else 0)
        values.append(value)
    return tuple(values)

CRC=_crc_table()

def crc_byte(state,byte):
    """Reflected CRC32C, raw state, no initial or final XOR."""
    return (state>>8)^CRC[(state^byte)&255]

def bcj(data,inverse=False):
    """Whole-file E8/E9 rel32 transform, including the ELF header.

    Each selected opcode consumes its next four operand bytes. Positions are
    file offsets; arithmetic is modulo 2**32. This is not a disassembler.
    """
    out=bytearray(data);at=0
    while at+4<len(out):
        if out[at]&254==232:
            value=int.from_bytes(out[at+1:at+5],'little')
            value=(value-(at+5) if inverse else value+(at+5))&U32
            out[at+1:at+5]=value.to_bytes(4,'little');at+=5
        else:at+=1
    return bytes(out)

def load_models(raw,profile):
    fixed=json.loads(raw)
    if (fixed.get('format')!=FORMAT or fixed.get('hash_bits')!=24 or fixed.get('base_probability')!=10
        or fixed.get('table_bytes')!=TABLE_BYTES or fixed.get('zero_tail_bytes')!=4
        or set(fixed.get('profiles',{}))!={'scalar-shipping','hq-shipping'}):
        raise ValueError('unsupported fixed model format')
    chosen=fixed['profiles'][profile];weightmask=int(chosen['weightmask'],16)
    if not 0<weightmask<=U32:raise ValueError('invalid u32 weightmask')
    declared=chosen['models']
    if len(declared)!=21:raise ValueError('this fixed profile requires exactly21 models')
    masks=[]
    for mask,weight in declared:
        if not isinstance(mask,str) or len(mask)!=2 or not isinstance(weight,int) or not 0<=weight<=9:
            raise ValueError('invalid mask/weight declaration')
        value=int(mask,16)
        if not 0<=value<=255:raise ValueError('mask outside byte domain')
        masks.append(value)
    scan=weightmask;count=0
    while True:
        one=scan>>31;scan=(scan<<1)&U32
        if not scan:break
        if not one:count+=1
    if count!=len(masks):raise ValueError('weightmask model count differs')
    working=weightmask;weight=0;models=[]
    for mask,(_,declared_weight) in zip(masks,declared):
        while working>>31:
            working=(working<<1)&U32;weight+=1
            if weight>9:raise ValueError('weight outside decoder domain')
        working=(working<<1)&U32
        if weight!=declared_weight:raise ValueError('weightmask order differs from fixed model data')
        models.append(((working&0xffffff00)|mask,mask,weight))
    return weightmask,bytes(masks),tuple(models)

def encode_context(data,model):
    """Encode exact post-BCJ bytes, including one leading coded1 sentinel."""
    if not isinstance(data,bytes) or len(data)>0x1fffffff:raise ValueError('decoder size domain exceeded')
    weightmask,masks,models=model;table=bytearray(TABLE_BYTES);coder=Encoder()
    history=0;prefix=0;symbols=0;alias_updates=0;counter_wraps=0
    def symbol(bit):
        nonlocal symbols,alias_updates,counter_wraps
        slots=[];p0=p1=10
        for seed,mask,weight in models:
            value=crc_byte(seed,prefix);past=history
            while mask:
                if mask&128:value=crc_byte(value,past&255)
                mask=(mask<<1)&255;past>>=8
            at=(value>>8)*2;c0=table[at];c1=table[at+1]
            shift=weight+(2 if not c0 or not c1 else 0)
            slots.append(at);p0+=c0<<shift;p1+=c1<<shift
        if p0>U32 or p1>U32:raise ValueError('probability sum outside decoder u32 domain')
        coder.update(bit,p0,p1)
        alias_updates+=len(slots)-len(set(slots))
        # Probabilities above are a snapshot. Every model updates, including
        # duplicate slots, in header order with unsigned-byte counter wrap.
        for at in slots:
            chosen=at+bit;opposite=at+(bit^1)
            before=table[chosen];table[chosen]=(before+1)&255
            counter_wraps+=before==255
            if table[opposite]>1:table[opposite]>>=1
        symbols+=1
    symbol(1);prefix=1
    for byte in data:
        for shift in range(7,-1,-1):
            bit=(byte>>shift)&1;symbol(bit);prefix=prefix*2+bit
        if prefix<256 or prefix&255!=byte:raise AssertionError('local prefix invariant')
        history=((history<<8)|byte)&U64;prefix=1
    body=coder.finish()
    header=masks
    payload=header+body+b'\0'*4
    return payload,{'format':PACKET_FORMAT,'decoded_bytes':len(data),'coded_symbols':symbols,
        'header_bytes':len(header),'arithmetic_body_bytes':len(body),'arithmetic_body_bits':coder.body_bits,
        'zero_tail_bytes':4,'payload_bytes':len(payload),'payload_sha256':sha(payload),
        'duplicate_slot_updates':alias_updates,'counter_wrap_updates':counter_wraps,
        'hash_bits':24,'base_probability':10,'table_bytes':TABLE_BYTES,'model_count':len(models),
        'weightmask':f'{weightmask:08X}','deterministic_integer_math':True}

def encode_native(native,model):
    transformed=bcj(native)
    if bcj(transformed,True)!=native:raise AssertionError('BCJ inverse did not recover native')
    payload,report=encode_context(transformed,model)
    report.update(native_bytes=len(native),native_sha256=sha(native),bcj_sha256=sha(transformed))
    return payload,report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models',type=Path,required=True);parser.add_argument('--model-sha256',required=True)
    parser.add_argument('--profile',choices=('scalar-shipping','hq-shipping'),required=True)
    parser.add_argument('--native',type=Path,required=True);parser.add_argument('--native-sha256',required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if not all(p.is_absolute() for p in (args.models,args.native,args.out)):parser.error('absolute input/output paths required')
    output=args.out.resolve()
    if output.exists() or any((p/'.git').exists() for p in (output,*output.parents)):
        parser.error('new output outside Git required')
    if args.native.stat().st_size>1048576 or args.models.stat().st_size>16384:parser.error('bounded data inputs required')
    native=args.native.read_bytes();raw=args.models.read_bytes()
    if sha(native)!=args.native_sha256 or sha(raw)!=args.model_sha256:raise ValueError('explicit input/model SHA-256 mismatch')
    model=load_models(raw,args.profile);payload,report=encode_native(native,model)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(payload)
    report.update(complete=True,profile=args.profile,model_sha256=sha(raw),output=str(output),
                  upstream_programs=0,native_compiles=0,engine_runs=0)
    print(json.dumps(report),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
