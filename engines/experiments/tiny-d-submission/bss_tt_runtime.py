"""Conditional kernel-zero/no-startup-join source prototype for full scalar D.

The caller supplies the exact audited fast-capacity readable bytes and existing
source.project/restore owner. This module performs no I/O, compilation, package
generation, execution or admission. It is not the older anonymous-mapping lazy
case, the fixed 4 MiB loader-BSS policy, or a change to the selected 4737 B D.
"""
from __future__ import annotations

import hashlib


SCHEMA = 'rove4k.d.kernel-zero-no-startup-join.source.v1'
INPUT = {
    'tiny.h': (3052, 'd24ccd0ea44a0fa8c984bf3085a9495e54bc76c75b4c7bcd8b217d938e07417b'),
    'board.c': (10346, '4f00f4c88eefe89fb6a61445a566c034095d074b14db37a07919fc3c45b48070'),
    'search.c': (6001, 'c25fe0cc2faf50397e9cf24af92eab5de4133341a893a05a740672f939282099'),
    'runtime.c': (15784, 'eea671466ff74b3f619d99f90278f30b491c163e40335d61dbe585090deea4e4'),
    'start.S': (697, '701f24836cffd49614235cfe11e6b961ee1b2c2b7d2466965b0916217cf43586'),
    'image.ld': (446, '38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b'),
}
TT_SYMBOL = 'D_kernel_tt'
TT_INPUT_SECTION = '.rove4k_tt'
TT_OUTPUT_SECTION = '.kernel_tt'


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def pins(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def _admit(files):
    if (type(files) is not dict or set(files) != set(INPUT) or
            any(type(data) is not bytes for data in files.values())):
        raise ValueError('exact audited six-file byte dictionary required')
    expected = {name: dict(bytes=size, sha256=sha) for name, (size, sha) in INPUT.items()}
    if pins(files) != expected or any(b'\r' in data for data in files.values()):
        raise ValueError('audited fast-capacity LF source pin differs')


def _span(data, begin, end):
    if data.count(begin) != 1 or data.count(end) != 1:
        raise ValueError('unique kernel-zero source boundaries required')
    first, last = data.index(begin), data.index(end)
    if last <= first:
        raise ValueError('ordered kernel-zero source boundaries required')
    return data[first:last]


def transform(files, source, *, tt_bits):
    """Return a new six-file mapping plus the existing owner's inverse proof.

    tt_bits is mandatory and binds the C compiler profile to the literal ASM
    reservation. Only exact int 8..33 is admitted, including TT33/128 GiB; the
    renderer itself reserves no memory and creates no giant byte string/object.
    """
    _admit(files)
    if type(tt_bits) is not int or not 8 <= tt_bits <= 33:
        raise ValueError('exact int TT bits in 8..33 required')
    tt_bytes = (1 << tt_bits) * 16
    runtime = files['runtime.c']
    startup = _span(runtime, b'    /* Entry=16B, pages=256 entries:',
                    b'    for(;;){\n        int current=atomic_load_explicit(&epoch,memory_order_acquire);')
    old_comment = (b'/* pending counts startup arrivals, then workers plus an output reservation.\n'
                   b' * Only zero releases storage after the complete bestmove has been written. */')
    new_comment = (b'/* pending counts dispatched workers plus an output reservation.\n'
                   b' * Kernel zero owns idle startup; no worker startup arrival is counted.\n'
                   b' * Only zero releases storage after the complete bestmove has been written. */')
    declaration = (f'extern Entry table[] __asm__("{TT_SYMBOL}");\n'
                   f'_Static_assert(TT_BITS=={tt_bits},"kernel TT profile binding");').encode()
    storage = f'''/* Logical TT zero is supplied by kernel ELF loading, not worker writes.
 * NOBITS keeps the profile-sized reservation out of the object/file payload. */
.section {TT_INPUT_SECTION},"aw",@nobits
.balign 4096
.global {TT_SYMBOL}
.type {TT_SYMBOL},@object
{TT_SYMBOL}:
    .skip {tt_bytes}
.size {TT_SYMBOL},.-{TT_SYMBOL}

'''.encode()
    bss = b'    .bss (NOLOAD) : { *(.bss .bss.*) *(COMMON) } :memory\n'
    layout = (bss + f'''    /* Small globals precede the large zero-file TT extent. */
    {TT_OUTPUT_SECTION} ALIGN(4096) (NOLOAD) : {{ KEEP(*({TT_INPUT_SECTION})) }} :memory
    ASSERT(ADDR({TT_OUTPUT_SECTION})<0x80000000,"kernel TT base exceeds small code model")
    ASSERT({TT_SYMBOL}==ADDR({TT_OUTPUT_SECTION}),"kernel TT symbol differs from section base")
    ASSERT(SIZEOF({TT_OUTPUT_SECTION})=={tt_bytes},"kernel TT profile size differs")
'''.encode())
    stack_note = b'.section .note.GNU-stack,"",@progbits\n'
    edits = {
        'tiny.h': [('kernel-TT-C-declaration-and-compiler-profile-binding',
                    b'extern Entry *table;', declaration)],
        'runtime.c': [
            ('remove-C-TT-pointer-storage', b'Entry *table;\n', b''),
            ('remove-worker-prefault-and-startup-arrival-together', startup, b''),
            ('search-only-pending-description', old_comment, new_comment),
            ('kernel-TT-replaces-runtime-TT-mmap',
             b'table=allocate(((size_t)1<<TT_BITS)*sizeof *table);if(!table)abort();', b''),
            ('remove-main-startup-arrival-count',
             b'    atomic_store_explicit(&pending,WORKERS,memory_order_relaxed);\n', b''),
            ('remove-only-preinput-startup-join',
             b'    wait();\n    for(;;){\n        int valid=read_line(line);',
             b'    for(;;){\n        int valid=read_line(line);'),
        ],
        'start.S': [('kernel-TT-NOBITS-storage-before-unchanged-stack-note',
                     stack_note, storage + stack_note)],
        'image.ld': [('kernel-TT-last-NOLOAD-storage-after-small-globals', bss, layout)],
    }
    output = dict(files)
    proof = dict(schema=SCHEMA, input=pins(files), source_edits={},
                 tt_bits=tt_bits, tt_entry_bytes=16, tt_bytes=tt_bytes,
                 fixed_ASM_symbol=TT_SYMBOL, compiler_profile_binding='mandatory header static assertion',
                 initialization_strategy='kernel-ELF-zero/no-startup-join',
                 pending_strategy='idle zero; dispatched WORKERS+1 including output reservation',
                 first_job_strategy='all children created before input; every child starts seen=0',
                 prior_parallel_page_owner_proof='inapplicable; not weakened or reused',
                 status='conditional source prototype; not yet costed or admitted')
    for name, roles in edits.items():
        output[name], proof['source_edits'][name] = source.project(files[name], roles)
    # These unchanged source owners are recorded in addition to every protected
    # complement. They include the normal first/subsequent job and output fence.
    protected = {
        'worker-seen-zero': b'    Worker *w=p;int seen=0;\n',
        'worker-job-loop-and-output-completion': _span(runtime,
            b'    for(;;){\n        int current=atomic_load_explicit(&epoch,memory_order_acquire);', old_comment),
        'normal-job-wait': _span(runtime, b'static void wait(void){', b'#if DEV\nstatic void clear(void)'),
        'normal-go-parser-publication-and-reservation': _span(runtime, b'static void go(char *s){',
            b'#if DEV\nstatic uint64_t perft('),
    }
    for role, data in protected.items():
        if output['runtime.c'].count(data) != 1:
            raise ValueError('protected kernel-zero consumer differs: ' + role)
    if any(output[name] != files[name] for name in ('board.c', 'search.c')):
        raise ValueError('kernel-zero prototype changed Board/search')
    proof['protected_runtime'] = {role: pin(data) for role, data in protected.items()}
    proof['output'] = pins(output)
    if restore(output, proof, source) != files:
        raise ValueError('kernel-zero complete source inverse differs')
    return output, proof


def restore(files, proof, source):
    """Restore the complete original six-file input through the supplied owner."""
    if proof.get('schema') != SCHEMA or pins(files) != proof['output']:
        raise ValueError('kernel-zero projection output differs')
    restored = dict(files)
    for name, record in proof['source_edits'].items():
        restored[name] = source.restore(files[name], record)
    _admit(restored)
    if pins(restored) != proof['input']:
        raise ValueError('kernel-zero projection input differs')
    return restored
