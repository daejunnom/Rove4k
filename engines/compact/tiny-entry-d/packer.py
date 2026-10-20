"""Fixed admitted TinyD layout and existing selected loader recipe.

The ELF parsing, section stripping, payload assembly, macro order and loader
invocation retain the project-owned dedicated-v3/compose recipe.  This module
does not read historical reports or images, and does not select a codec.
"""
import json
from pathlib import Path
import struct


def elf(data):
    if len(data) < 64 or data[:9] != b"\x7fELF\x02\x01\x01\0\0":
        raise ValueError("expected ELF64 little-endian System V ABI")
    kind, machine, version = struct.unpack_from("<HHI", data, 16)
    entry, phoff, shoff = struct.unpack_from("<QQQ", data, 24)
    flags, ehsize, phsize, phnum, shsize, shnum, shstr = struct.unpack_from("<IHHHHHH", data, 48)
    if (kind, machine, version, flags, ehsize, phoff, phsize) != (2, 62, 1, 0, 64, 64, 56):
        raise ValueError("unsupported ELF header")
    if not 1 <= phnum <= 3 or phoff + phnum*phsize > len(data):
        raise ValueError("invalid program header extent")
    segments = [dict(zip(("type", "flags", "offset", "vaddr", "paddr", "filesz", "memsz", "align"),
                         struct.unpack_from("<IIQQQQQQ", data, phoff+i*phsize))) for i in range(phnum)]
    return {"entry": entry, "section_offset": shoff, "section_size": shsize, "section_count": shnum,
            "section_names": shstr, "segments": segments}


def strip_native(data):
    """Keep all PT_LOAD bytes and remove only section metadata, as before."""
    data = bytearray(data)
    if data[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("expected ELF64 little endian")
    phoff = struct.unpack_from("<Q", data, 32)[0]
    phentsize, count = struct.unpack_from("<HH", data, 54)
    end = 64
    for at in range(phoff, phoff + count * phentsize, phentsize):
        kind, _, offset, _, _, size, _, _ = struct.unpack_from("<IIQQQQQQ", data, at)
        if kind == 3:
            raise ValueError("standalone D must have no interpreter")
        if kind == 1:
            end = max(end, offset + size)
    struct.pack_into("<Q", data, 40, 0)
    struct.pack_into("<HHH", data, 58, 0, 0, 0)
    return bytes(data[:end])


def admit(data, expected, digest):
    if len(data) != expected['native_bytes'] or digest(data) != expected['native_sha256']:
        raise ValueError('unknown selected TinyD native image')
    parsed = elf(data)
    layout = expected['layout']
    if any(parsed[name] != layout[name] for name in parsed):
        raise ValueError('selected TinyD layout differs')
    # These are the same two already admitted compose images, with exact
    # constants; this maintained entry does not broaden the loader ABI.
    if (layout['image_base'], layout['image_pages'], layout['bss_base'], layout['bss_size'],
        layout['bss_pages'], layout['guard_base'], layout['reserve_size'], layout['upper_guard']) != (
        0x400000, 0x3000, 0x403000, 175092, 0x2b000, 0x3ff000, 0x30000, 0x42e000):
        raise ValueError('unsupported fixed mapping contract')
    return dict(layout)


def stripped_loader(data):
    parsed = elf(data)
    loads = [s for s in parsed['segments'] if s['type'] == 1]
    if len(loads) != 1 or len(parsed['segments']) != 2 or loads[0]['flags'] != 5 or loads[0]['vaddr'] != 0x10000000:
        raise ValueError('loader must contain exactly one fixed RX image and nonexec stack')
    stack = next(s for s in parsed['segments'] if s['type'] == 0x6474e551)
    if stack['flags'] != 6 or any(s['flags'] & 3 == 3 for s in parsed['segments']):
        raise ValueError('loader has executable writable mapping/stack')
    segment = loads[0]
    if segment['filesz'] != segment['memsz'] or segment['offset']:
        raise ValueError('loader unexpectedly needs writable state')
    out = bytearray(data[:segment['filesz']])
    struct.pack_into('<Q', out, 40, 0)
    struct.pack_into('<HHH', out, 58, 0, 0, 0)
    return bytes(out)


def compile_loader(directory, sources, payload, layout, flags, run, digest, checkpoint=False):
    directory.mkdir(parents=True)
    payload_path = directory / 'payload.bin'
    payload_path.write_bytes(payload)
    quoted = str(payload_path).replace('\\', '\\\\').replace('"', '\\"')
    assembly = directory / 'payload.S'
    assembly.write_text('.section .payload,"a",@progbits\n.global payload,payload_end\npayload:\n'
                        '.incbin "' + quoted + '"\npayload_end:\n.section .note.GNU-stack,"",@progbits\n')
    definitions = {'IMAGE_BASE': layout['image_base'], 'IMAGE_SIZE': layout['image_size'], 'IMAGE_PAGES': layout['image_pages'],
                   'IMAGE_ENTRY': layout['entry'], 'BSS_BASE': layout['bss_base'], 'BSS_PAGES': layout['bss_pages'],
                   'GUARD_BASE': layout['guard_base'], 'RESERVE_SIZE': layout['reserve_size'],
                   'CODEC_FIXED': 1, 'CHECKPOINT': int(checkpoint)}
    command = ['cc', *flags, *[f'-D{name}={value}UL' for name, value in definitions.items()],
               str(sources/'loader.c'), str(assembly), '-Wl,-T,' + str(sources/'image.ld'), '-o', str(directory/'linked')]
    record = run(command)
    (directory/'compile.json').write_text(json.dumps(record, indent=2)+'\n')
    data = stripped_loader((directory/'linked').read_bytes())
    target = directory/'x'
    target.write_bytes(data)
    target.chmod(0o755)
    return {'path': str(target), 'bytes': len(data), 'sha256': digest(data), 'compile': record,
            'definitions': definitions, 'payload_bytes': len(payload), 'loader_and_headers_bytes': len(data)-len(payload)}
