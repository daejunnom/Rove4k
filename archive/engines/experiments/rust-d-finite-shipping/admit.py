"""Separate literal candidate identity class; no original class is broadened.

The admit function body is the exact immutable data8 source function. Only its
NATIVE identity table and CLASS are new, after actual four-link geometry review.
"""
import hashlib

CLASS = 'rust-d-tiny-shipping-node-counter-data8-v1'
DATA = bytes.fromhex('4601400000000000')
NATIVE = {'candidate-scalar': {'bytes': 16816, 'sha256': 'df1945b23cbe3d7d6a4af5f775cc98ef6675758814feafa4ce56194541d78c7d', 'rx_filesz': 14256, 'load_sha256': '8a0c5f96b2b488572c82a7f44e82338bb73bc2a01a2ccb5b4619d0ab00fa4bbc'}, 'candidate-hq': {'bytes': 16816, 'sha256': 'b92d57e68d33c92fdc367ec7bfc339cbe7f53f0911082371ea5031ad8759f646', 'rx_filesz': 14704, 'load_sha256': '890fa0fe2ff8be62ae1fa2685b38651ba7ef3e700718ede9b011e99dd2bfe1f3'}}


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
