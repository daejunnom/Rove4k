"""Finite reversible native-operand experiment, separate from production.

Jcc is deliberately a byte scanner, not an instruction decoder. Its markers
remain unchanged and every accepted marker skips its four-byte operand in
both directions, so arbitrary data also round-trips. RIP fields require a
build-time objdump proof tied to the actual ELF RX bytes. Nothing here runs
an engine, reads files, invokes tools, or changes a production admission.
"""
from hashlib import sha256
import lzma
import re
import struct

KIND="D-native-operand-filter-experiment-v1"
MODES=("control","jcc","rip","union")
MASK32=(1<<32)-1
_INSN=re.compile(r"^\s*([0-9a-fA-F]+):\s*((?:[0-9a-fA-F]{2}(?:\s+|$))+)(\S.*)?$")
_RIP=re.compile(r"\[\s*rip\s*([+-])\s*(0x[0-9a-fA-F]+|[0-9]+)\s*\]",re.I)
_REG=re.compile(r"(?:r(?:[89]|1[0-5])(?:b|w|d)?|[re]?[abcd]x|[abcd][lh]|[re]?(?:si|di|sp|bp)|[sd]il|[sb]pl)\Z",re.I)
_SAFE=frozenset(("mov","movzx","movsx","movsxd","lea","add","sub","and","or","xor","cmp","test","xchg","inc","dec","neg","not"))


def require(value,message):
    if not value:raise ValueError(message)


def pin(data):
    require(isinstance(data,bytes),"actual bytes required")
    return dict(bytes=len(data),sha256=sha256(data).hexdigest())


def _bytes(data):
    require(isinstance(data,bytes),"filter input must be immutable bytes")
    return data


def jcc(data,*,inverse=False):
    """0F 8x disp32 <-> 0F 8x absolute-file-target32, modulo 2^32."""
    require(type(inverse) is bool,"explicit Jcc direction required")
    output=bytearray(_bytes(data));i=0
    while i+6<=len(output):
        if output[i]==15 and output[i+1]&240==128:
            value=struct.unpack_from("<I",output,i+2)[0]
            value=value-i-6 if inverse else value+i+6
            struct.pack_into("<I",output,i+2,value&MASK32)
            i+=6
        else:i+=1
    return bytes(output)


def validate_offsets(offsets,extent):
    require(type(extent) is int and 0<=extent<65536,"16-bit map body extent required")
    require(isinstance(offsets,(tuple,list)) and len(offsets)<65536,"finite offset sequence required")
    previous=-4
    for position in offsets:
        require(type(position) is int and 0<=position<=65535 and previous+4<=position
                and position+4<=extent,"sorted nonoverlapping in-bounds disp32 map required")
        previous=position
    return tuple(offsets)


def _rip(data,offsets,*,inverse):
    output=bytearray(_bytes(data))
    offsets=validate_offsets(offsets,len(output))
    for position in offsets:
        value=struct.unpack_from("<I",output,position)[0]
        value=value-position-4 if inverse else value+position+4
        struct.pack_into("<I",output,position,value&MASK32)
    return bytes(output)


def normalize(data,mode,offsets=()):
    require(mode in MODES,"unknown finite native filter mode")
    _bytes(data)
    if mode in ("control","jcc"):
        require(not offsets,"map-free mode cannot consume a RIP map")
    else:validate_offsets(offsets,len(data))
    if mode in ("rip","union"):data=_rip(data,offsets,inverse=False)
    if mode in ("jcc","union"):data=jcc(data)
    return data


def restore(data,mode,offsets=()):
    require(mode in MODES,"unknown finite native filter mode")
    _bytes(data)
    if mode in ("control","jcc"):
        require(not offsets,"map-free mode cannot consume a RIP map")
    else:validate_offsets(offsets,len(data))
    if mode in ("jcc","union"):data=jcc(data,inverse=True)
    if mode in ("rip","union"):data=_rip(data,offsets,inverse=True)
    return data


def encode_map(offsets,extent=65535):
    offsets=validate_offsets(offsets,extent)
    return struct.pack("<H",len(offsets))+b"".join(struct.pack("<H",p) for p in offsets)


def decode_map(mapping,extent):
    _bytes(mapping)
    require(len(mapping)>=2,"truncated RIP map count")
    count=struct.unpack_from("<H",mapping)[0];end=2+2*count
    require(end==len(mapping),"RIP map extent differs")
    offsets=tuple(value[0] for value in struct.iter_unpack("<H",mapping[2:end]))
    validate_offsets(offsets,extent)
    require(encode_map(offsets,extent)==mapping,"noncanonical RIP map")
    return offsets


def _rx_segments(native):
    _bytes(native)
    require(len(native)>=64 and native[:7]==b"\x7fELF\x02\x01\x01","little-endian ELF64 input required")
    fields=struct.unpack_from("<HHIQQQIHHHHHH",native,16)
    kind,machine,version,entry,phoff,_,_,ehsize,phsize,count,*_=fields
    require((kind,machine,version,ehsize,phsize)==(2,62,1,64,56) and 1<=count<=64
            and phoff>=64 and phoff+count*56<=len(native),"bounded static x86-64 ELF header required")
    rx=[]
    for index in range(count):
        ptype,flags,offset,address,_,size,_,_=struct.unpack_from("<IIQQQQQQ",native,phoff+56*index)
        if ptype==1 and flags&1:
            require(flags&4 and not flags&2 and offset+size<=len(native),"bounded read-execute segment required")
            rx.append((offset,address,size))
    require(rx and any(address<=entry<address+size for _,address,size in rx),"entry must belong to RX bytes")
    return rx,phoff+count*56


def _file_offset(address,length,segments,header_end,extent):
    candidates=[offset+address-base for offset,base,size in segments
                if base<=address and address+length<=base+size]
    require(len(candidates)==1,"decoded instruction must belong to one RX segment")
    position=candidates[0]
    require(header_end<=position and position+length<=extent,"decoded instruction overlaps ELF headers or image end")
    return position


def _operands(text):
    values=[];begin=depth=0
    for index,char in enumerate(text):
        if char=="[":depth+=1
        elif char=="]":depth-=1
        elif char=="," and depth==0:values.append(text[begin:index].strip());begin=index+1
        require(depth>=0,"unbalanced decoded operand")
    require(depth==0,"unbalanced decoded operand")
    values.append(text[begin:].strip())
    return values


def decode_rip_map(native,objdump_text):
    """Admit only ordinary no-immediate RIP disp32 fields ending instructions.

    objdump must have been run on the fresh linked image with
    ``-d -Mintel --insn-width=16``. The caller pins that command/tool/output.
    This proof binds every parsed instruction's bytes to native RX bytes;
    unsupported RIP forms are explicitly excluded rather than guessed.
    """
    require(isinstance(objdump_text,(str,bytes)),"actual objdump output required")
    if isinstance(objdump_text,bytes):objdump_text=objdump_text.decode("utf-8",errors="strict")
    segments,header_end=_rx_segments(native)
    selected=[];excluded=[];instructions=[];rip_count=0
    for line in objdump_text.splitlines():
        match=_INSN.fullmatch(line)
        if not match:continue
        address=int(match[1],16);raw=bytes.fromhex(match[2]);text=(match[3] or "").strip()
        require(1<=len(raw)<=15 and text,"complete decoded instruction line required")
        position=_file_offset(address,len(raw),segments,header_end,len(native))
        require(native[position:position+len(raw)]==raw,"decoded instruction bytes differ from native RX input")
        instructions.append((position,len(raw)))
        if "rip" not in text.lower():continue
        rip_count+=1
        reason=None;code=text.split("#",1)[0].strip()
        if code.startswith("lock "):code=code[5:].strip()
        words=code.split(None,1);mnemonic=words[0].lower();operand_text=words[1] if len(words)>1 else ""
        rip=list(_RIP.finditer(operand_text))
        operands=_operands(operand_text)
        if mnemonic not in _SAFE:reason="unsupported mnemonic"
        elif len(rip)!=1:reason="unsupported RIP addressing form"
        elif not 1<=len(operands)<=2:reason="unsupported operand count"
        elif sum(bool(_RIP.search(value)) for value in operands)!=1:reason="ambiguous RIP operand"
        elif any(not _RIP.search(value) and not _REG.fullmatch(value) for value in operands):
            reason="immediate or unsupported nonmemory operand"
        elif len(raw)<6 or raw[-5]&0xc7!=5:reason="not a trailing ModRM RIP disp32"
        if reason:
            excluded.append(dict(address=address,file_offset=position,bytes=raw.hex(),text=text,reason=reason));continue
        displacement=int(rip[0][2],0)*(1 if rip[0][1]=="+" else -1)
        if struct.unpack_from("<I",raw,len(raw)-4)[0] != displacement&MASK32:
            excluded.append(dict(address=address,file_offset=position,bytes=raw.hex(),text=text,
                                 reason="last four bytes do not equal decoded RIP displacement"));continue
        annotation=re.search(r"#\s*([0-9a-fA-F]+)\b",text)
        if annotation:
            require(int(annotation[1],16)==(address+len(raw)+displacement)&((1<<64)-1),
                    "decoded RIP annotation target differs")
        selected.append(dict(address=address,file_offset=position,bytes=raw.hex(),length=len(raw),text=text,
            offset=position+len(raw)-4,next_ip=position+len(raw),displacement_u32=displacement&MASK32))
    require(instructions,"objdump contains no complete RX instructions")
    previous=-1
    for position,length in sorted(instructions):
        require(previous<=position,"overlapping or duplicate decoded instruction range")
        previous=position+length
    selected.sort(key=lambda value:value["offset"])
    offsets=validate_offsets(tuple(value["offset"] for value in selected),len(native))
    return offsets,dict(kind="D-binutils-trailing-RIP-disp32-map-v1",native=pin(native),
        objdump=pin(objdump_text.encode()),decoded_instructions=len(instructions),rip_candidates=rip_count,
        offsets=list(offsets),selected=selected,excluded=excluded,immediate_trailing_allowed=False,
        map=pin(encode_map(offsets,len(native))),program_executed=False)


def _code(mode,packaging):
    require(mode in MODES,"unknown finite package mode")
    if mode=="control":return packaging.NATIVE_CODE
    code='import os,lzma,sys,struct\nd=lzma.decompress(open(sys.argv[1],"rb").read()[PAYLOAD_OFFSET:])\n'
    if mode in ("rip","union"):
        code+='n=int.from_bytes(d[:2],"little");m=struct.unpack("<"+"H"*n,d[2:2+2*n]);b=bytearray(d[2+2*n:])\n'
    else:code+='b=bytearray(d)\n'
    code+='u=struct.unpack_from;p=struct.pack_into\n'
    if mode in ("jcc","union"):
        code+='i=0\nwhile i+5<len(b):\n if b[i]==15 and b[i+1]&240==128:p("<I",b,i+2,(u("<I",b,i+2)[0]-i-6)&4294967295);i+=6\n else:i+=1\n'
    if mode in ("rip","union"):
        code+='for i in m:p("<I",b,i,(u("<I",b,i)[0]-i-4)&4294967295)\n'
    code+='f=os.memfd_create("Rove4k-D",1)\nos.write(f,b)==len(b) or sys.exit(2)\nos.execve(f,["Rove4k-D"],os.environ)'
    return code


def package(native,mode,offsets,packaging):
    _bytes(native);require(mode in MODES,"unknown finite package mode")
    transformed=normalize(native,mode,offsets)
    require(restore(transformed,mode,offsets)==native,"native filter inverse differs")
    mapping=encode_map(offsets,len(native)) if mode in ("rip","union") else b""
    container=mapping+transformed;payload=packaging.encode(container,"xz-bcj")
    code=_code(mode,packaging);whole,header=packaging.envelope(code,payload)
    if mode=="control":
        expected,detail=packaging.package_native(native,"xz-bcj")
        require(whole==expected,"control package differs from production byte baseline")
    else:detail=None
    metadata=dict(kind=KIND,mode=mode,codec="xz-bcj",offsets=list(offsets),native=pin(native),
        transformed=pin(transformed),map=pin(mapping),map_bytes=len(mapping),container=pin(container),
        inverse_code=pin(code.encode()),header=pin(header),header_bytes=len(header),payload=pin(payload),
        whole=pin(whole),control_package=detail,restoration="complete exact kernel ELF",
        cleanup="memfd-CLOEXEC",engine_executed=False,selected=False)
    require(restore_package(whole,metadata,packaging)==native,"counted package restoration differs")
    return whole,metadata


def restore_package(whole,metadata,packaging):
    """Offline decoder: validates exact header/map/payload/native without exec."""
    _bytes(whole)
    require(metadata.get("kind")==KIND and metadata.get("mode") in MODES,"unknown native package metadata")
    mode=metadata["mode"];boundary=metadata["header_bytes"]
    require(type(boundary) is int and 0<boundary<len(whole) and pin(whole)==metadata["whole"],"whole package identity differs")
    header,payload=whole[:boundary],whole[boundary:]
    require(pin(header)==metadata["header"] and pin(payload)==metadata["payload"],"package boundary identity differs")
    code=_code(mode,packaging)
    regenerated,_=packaging.envelope(code,payload)
    require(regenerated==whole and pin(code.encode())==metadata["inverse_code"],"self-contained inverse program differs")
    maximum=metadata["container"]["bytes"]
    require(type(maximum) is int and 0<=maximum<1<<18,"bounded container extent required")
    decoder=lzma.LZMADecompressor();container=decoder.decompress(payload,max_length=maximum+1)
    require(decoder.eof and not decoder.unused_data and pin(container)==metadata["container"],"complete single payload required")
    extent=metadata["native"]["bytes"]
    if mode in ("rip","union"):
        require(len(container)>=2,"truncated RIP map count")
        map_end=2+2*struct.unpack_from("<H",container)[0]
        require(map_end<=len(container) and len(container)-map_end==extent,"RIP map/body extent differs")
        mapping,transformed=container[:map_end],container[map_end:]
        offsets=decode_map(mapping,extent)
        require(list(offsets)==metadata["offsets"] and pin(mapping)==metadata["map"]
                and len(mapping)==metadata["map_bytes"],"counted RIP map differs")
    else:
        require(metadata["offsets"]==[] and metadata["map_bytes"]==0 and metadata["map"]==pin(b""),"map-free package acquired a map")
        offsets=();transformed=container
    require(pin(transformed)==metadata["transformed"],"normalized native identity differs")
    native=restore(transformed,mode,offsets)
    require(pin(native)==metadata["native"],"restored native identity differs")
    return native
