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
    return _admit_mapping(expected['native_sha256'], expected['native_bytes'], layout, hq=expected['hq'])


def _native_mapping(native_sha256, native_bytes):
    # Bind each exact native identity to its own qualified private mapping ABI.
    # This is not a generic permission for arbitrary two/three-page images.
    fixed = {
        ('662b0eb10046d0b0ab105bba0f793371bb869eb61aa4419c8c2fa95f7d39c32d', 7612): (0, 4201533, (4194304, 8192, 4202496, 175092, 176128, 4190208, 192512, 4378624)),
        ('49fb8e2916ba394cda6665f287df7ff4bfcd7c76ef95dc613628f3513394c6b6', 8000): (1, 4201848, (4194304, 8192, 4202496, 175092, 176128, 4190208, 192512, 4378624)),
        ('3c662941aa11af8521d3c601322e9aa38405a3bfbeb9332d55008907217a4b2e', 8000): (1, 4201846, (4194304, 8192, 4202496, 175064, 176128, 4190208, 192512, 4378624)),
        ('395fea4ddf80d155227700fa8da9b06437082837a1878a818605f268506de50c', 7388): (0, 4201328, (4194304, 8192, 4202496, 175092, 176128, 4190208, 192512, 4378624)),
        ('2456cedd1eea62d87b50423a24bbc321a84c5cdb86e64adeafb33bf9472d6af6', 7324): (0, 4201269, (4194304, 8192, 4202496, 4369412, 4370432, 4190208, 4386816, 8572928)),
    }.get((native_sha256, native_bytes))
    if fixed is None:
        raise ValueError('unknown exact compiled native identity')
    return fixed


def _admit_mapping(native_sha256, native_bytes, layout, *, hq):
    fixed = _native_mapping(native_sha256, native_bytes)
    geometry = tuple(layout[key] for key in ('image_base', 'image_pages', 'bss_base', 'bss_size',
                      'bss_pages', 'guard_base', 'reserve_size', 'upper_guard'))
    if fixed != (hq, layout['entry'], geometry) or layout['image_size'] != native_bytes:
        raise ValueError('unsupported exact identity/form mapping contract')
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


def body_image(expected):
    """Separate exact body232 class; admit() and the default loader stay full RX."""
    restored = {
        (7612, '662b0eb10046d0b0ab105bba0f793371bb869eb61aa4419c8c2fa95f7d39c32d'):
            '07b6754aabefd1171fbdfae84ce30e1b50cff8a527a124d99998e18170f0d07c',
        (8000, '3c662941aa11af8521d3c601322e9aa38405a3bfbeb9332d55008907217a4b2e'):
            'f2b4804631d293ccb4742ed8718869a29736bfb46f840044659e44c8d0f95d4b',
        (7388, '395fea4ddf80d155227700fa8da9b06437082837a1878a818605f268506de50c'):
            'b2982877c1c1bf97cafcfcd5b9dd210835a3eded07dcbf3c38e8c991c4d8943a',
        (7324, '2456cedd1eea62d87b50423a24bbc321a84c5cdb86e64adeafb33bf9472d6af6'):
            '08e48273a79303ef363eefd26f043185d6f9de7aec66a23f29454f279e316d5d',
    }.get((expected['native_bytes'], expected['native_sha256']))
    if restored is None:
        raise ValueError('unknown body232 compiled native')
    image = {'format': 'rove4k-context-h24-base10-fixed21-body232-zero4-v3', 'zero_prefix_bytes': 232,
             'compiled_native_bytes': expected['native_bytes'], 'compiled_native_sha256': expected['native_sha256'],
             'restored_image_bytes': expected['native_bytes'], 'restored_image_sha256': restored}
    if expected.get('image') != image:
        raise ValueError('body232 restored-image literal differs')
    return image


def compile_loader(directory, sources, payload, layout, flags, run, digest, *, model_wmask, checkpoint=False, image=None):
    # Native bytes/layout were admitted above; bind its private model literal.
    fixed_model = {(7612, 4201533): 16847486, (8000, 4201848): 135274878, (8000, 4201846): 135274878, (7388, 4201328): 16847486, (7324, 4201269): 16847486}.get((layout['image_size'], layout['entry']))
    if type(model_wmask) is not int or model_wmask != fixed_model:
        raise ValueError('unsupported exact native/model mapping contract')
    if image is not None:
        body_image({'native_bytes': layout['image_size'], 'native_sha256': image['compiled_native_sha256'], 'image': image})
        _admit_mapping(image['compiled_native_sha256'], image['compiled_native_bytes'], layout,
                       hq=_native_mapping(image['compiled_native_sha256'], image['compiled_native_bytes'])[0])
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
                   'CHECKPOINT': int(checkpoint), 'MODEL_WMASK': model_wmask}
    if image is not None:
        definitions['DECODE_PREFIX'] = image['zero_prefix_bytes']
    command = ['cc', *flags, *[f'-D{name}={value}UL' for name, value in definitions.items()],
               str(sources/'loader.c'), str(assembly), '-Wl,-T,' + str(sources/'image.ld'), '-o', str(directory/'linked')]
    record = run(command)
    (directory/'compile.json').write_text(json.dumps(record, indent=2)+'\n')
    data = stripped_loader((directory/'linked').read_bytes())
    target = directory/'x'
    target.write_bytes(data)
    target.chmod(0o755)
    result = {'path': str(target), 'bytes': len(data), 'sha256': digest(data), 'compile': record,
              'definitions': definitions, 'payload_bytes': len(payload), 'loader_and_headers_bytes': len(data)-len(payload)}
    if image is not None:
        result['image'] = dict(image)
    return result
