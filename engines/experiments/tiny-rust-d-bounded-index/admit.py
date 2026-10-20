"""Separate literal bounded-index data8 class; original guards unchanged."""
import hashlib
CLASS='rust-d-bounded-index-data8-v1'
DATA=bytes.fromhex('4601400000000000')
NATIVE={'control-scalar': {'bytes': 16816, 'sha256': 'bd0e3bd1567ae906d4ab9704603204d22302895df1f05679f6221d6445aef878', 'rx_filesz': 14240, 'load_sha256': '8498ceeabf31a8c688b2344585f126dad086193c2ffe5dc07fb7a994887b5b37'}, 'control-hq': {'bytes': 16816, 'sha256': 'f8581a68f09d4d9cdc3e1413aa45ffb385bafd8240f1432403629ec2a0e544f8', 'rx_filesz': 14688, 'load_sha256': '995e9464eb61e2a5894263f49da545767315f6616c405d9e01540a71b4fc8da0'}, 'candidate-scalar': {'bytes': 16816, 'sha256': '9707192f0792196f7c6591bdfe3efe043d14e5a00830c7b34ea0afe8ad194294', 'rx_filesz': 14176, 'load_sha256': '6490afdb6e4869f8b2158dd045464887ed1f6057d4b21e321b20a3697a00da2c'}, 'candidate-hq': {'bytes': 16816, 'sha256': '60665e0e0f32f163a601151952225f50dfc3f21c2080a798ffc50fa37671ccc8', 'rx_filesz': 14624, 'load_sha256': 'bdb6f68fb4dfbc137833f623a153326045854114bfaf3b622c18c17d5c112b0b'}}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)


def admit(native, form, packer):
    """A new literal class; the snapshot's existing C admit is never called."""
    expected = NATIVE[form]
    require(len(native) == expected['bytes'] and sha(native) == expected['sha256'],
            'unknown original qualified Rust D native')
    parsed = packer.elf(native)
    expected_segments = [
        {'type': 1, 'flags': 5, 'offset': 0, 'vaddr': 0x400000, 'paddr': 0x400000,
         'filesz': expected['rx_filesz'], 'memsz': expected['rx_filesz'], 'align': 4096},
        {'type': 1, 'flags': 6, 'offset': 0x4000, 'vaddr': 0x404000, 'paddr': 0x404000,
         'filesz': 8, 'memsz': 12, 'align': 4096},
        {'type': 0x6474e551, 'flags': 6, 'offset': 0, 'vaddr': 0, 'paddr': 0,
         'filesz': 0, 'memsz': 0, 'align': 0},
    ]
    require(parsed['entry'] == 0x4000f0 and parsed['segments'] == expected_segments,
            'literal original Rust segment or entry mismatch')
    require(native[0x4000:0x4008] == DATA, 'initialized memcpy data pointer differs')
    require(int.from_bytes(DATA, 'little') == 0x400146 and
            0x4000f0 <= 0x400146 < 0x400000+expected['rx_filesz'], 'initialized pointer is outside actual RX')
    require(not any(native[expected['rx_filesz']:0x4000]), 'unexpected nonzero file gap')
    load = packer.strip_native(native)
    require(len(load) == 16392 and sha(load) == expected['load_sha256'],
            'sectionless Rust load span differs')
    transformed = packer.elf(load)
    require(transformed['entry'] == parsed['entry'] and transformed['segments'] == parsed['segments'],
            'section stripping changed entry or program headers')
    require(all(transformed[name] == 0 for name in
                ('section_offset', 'section_size', 'section_count', 'section_names')),
            'section metadata not removed')
    permitted = set(range(40, 48)) | set(range(58, 64))
    changed = [i for i, (old, new) in enumerate(zip(native, load)) if old != new]
    require(set(changed) <= permitted and all(load[i] == 0 for i in permitted),
            'unexpected retained PT_LOAD change')
    require(native[0xf0:0x4008] == load[0xf0:0x4008], 'text/rodata/gap/data changed')
    for segment in expected_segments[:2]:
        require(segment['offset'] + segment['filesz'] <= len(load), 'truncated PT_LOAD bytes')
        require(segment['vaddr'] - 0x400000 == segment['offset'], 'noncontiguous virtual/file bias')
    require(0x400000 + 0x5000 == 0x405000 and 0x3ff000 + 0x7000 == 0x406000,
            'guard reservation mismatch')
    # The decoded stream ends BEFORE OUTPUT/BSS. Its four initial zero bytes
    # and all RW page padding remain anonymous untouched bytes. This is a
    # source/static proof; actual initial memory needs the later checkpoint.
    require(len(load) == 0x404008 - 0x400000, 'decoded data overlaps BSS')
    require(0x404008 + 4 <= 0x405000 and 0x406000 < 0x10000000, 'layout overlap')
    return load, {
        'class': CLASS, 'original_native_bytes': len(native), 'original_native_sha256': sha(native),
        'sectionless_bytes': len(load), 'sectionless_sha256': sha(load),
        'entry': parsed['entry'], 'program_headers_unchanged': True,
        'PT_LOAD_bytes_equal_except_declared_ELF_section_metadata': True,
        'changed_retained_header_offsets': changed, 'text_rodata_file_gap_data_identical': True,
        'initialized_data_hex': DATA.hex(), 'data_sha256': sha(DATA),
        'required_zero_BSS': {'address': 0x404008, 'bytes': 4, 'symbol': 'os::OUTPUT'},
        'static_zero_tail_source_proof_only': True,
        'original_rx_sha256': sha(native[:expected['rx_filesz']]),
        'sectionless_rx_sha256': sha(load[:expected['rx_filesz']]),
        'final_rx_pages': 0x4000, 'decode_protection_pages': 0x5000,
        'final_rw_pages': 0x1000, 'old_C_class_used_or_broadened': False,
    }
