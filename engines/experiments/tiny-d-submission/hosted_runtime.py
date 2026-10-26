"""Separate hosted-C general-4K projection of the audited fast-capacity D.

Rendering is pure: callers supply the exact six readable inputs and the existing
source.project/restore owner. Board/search bytes are preserved. A later approved
cost runner owns preprocessing, compilation, compression, output and settlement;
importing or transforming here never performs those operations.
"""
from __future__ import annotations

import hashlib
from types import SimpleNamespace


INPUT = {
    'tiny.h': (3052, 'd24ccd0ea44a0fa8c984bf3085a9495e54bc76c75b4c7bcd8b217d938e07417b'),
    'board.c': (10346, '4f00f4c88eefe89fb6a61445a566c034095d074b14db37a07919fc3c45b48070'),
    'search.c': (6001, 'c25fe0cc2faf50397e9cf24af92eab5de4133341a893a05a740672f939282099'),
    'runtime.c': (15784, 'eea671466ff74b3f619d99f90278f30b491c163e40335d61dbe585090deea4e4'),
    'start.S': (697, '701f24836cffd49614235cfe11e6b961ee1b2c2b7d2466965b0916217cf43586'),
    'image.ld': (446, '38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b'),
}
UNITS = ('tiny.h', 'board.c', 'search.c', 'runtime.c')
SCHEMA = 'rove4k.d.hosted-runtime-source.v1'

HEADERS = b'''#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <unistd.h>
#include <sys/mman.h>
#include <pthread.h>
#include <semaphore.h>
/* The audited syscall failure owner exits the whole process with status 2. */
#define abort() _Exit(2)
'''

PLATFORM = b'''/* libc owns syscall ABI, errno, TLS and pthread stack creation. The TT
 * remains a fresh page-aligned anonymous mapping, first-touched by workers. */
static void semaphore_wait(sem_t *semaphore){
    int status;
    do{status=sem_wait(semaphore);}while(status&&errno==EINTR);
    if(status)abort();
}
static void semaphore_post(sem_t *semaphore){if(sem_post(semaphore))abort();}

'''

POOL = b'''/* Every callback uses the pthread void *(*)(void *) ABI. One job semaphore
 * belongs to each persistent worker; the input thread alone owns busy. */
static void *work(void *p){
    Worker *w=p;
    /* Entry=16B, pages=256 entries: each worker owns whole fresh pages.
     * All writes precede the existing release arrival; main waits acquire.
     * bits<=34 and workers<=512 keep every intermediate within size_t. */
    size_t pages=((size_t)1<<TT_BITS)/256;
    size_t begin=pages*(unsigned)w->id/WORKERS*256;
    size_t end=pages*((unsigned)w->id+1)/WORKERS*256;
    memset(table+begin,0,(end-begin)*sizeof *table);
    if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==1)semaphore_post(&completed);
    for(;;){
        semaphore_wait(jobs+w->id);
        w->best=0;think(w,&position);
        if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==1){
            result();semaphore_post(&completed);
        }
    }
}
/* A completion includes every worker arrival and the complete counted output.
 * Exactly one completion token is consumed for each input-owned busy phase. */
static void wait(void){
    atomic_store_explicit(&stopped,1,memory_order_relaxed);
    if(busy){semaphore_wait(&completed);busy=0;}
}
'''

STARTUP = b'''int main(void){
    char line[32768];pthread_attr_t attributes;
    table=mmap(0,((size_t)1<<TT_BITS)*sizeof *table,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(table==MAP_FAILED)abort();
    start(&position);game_keys[0]=position.h;game_length=1;
    if(sem_init(&completed,0,0)||pthread_attr_init(&attributes))abort();
    if(pthread_attr_setstacksize(&attributes,1048576)||pthread_attr_setguardsize(&attributes,4096))abort();
    for(int index=0;index<WORKERS;index++)if(sem_init(jobs+index,0,0))abort();
    atomic_store_explicit(&pending,WORKERS,memory_order_relaxed);busy=1;
    for(int index=0;index<WORKERS;index++){
        pthread_t thread;workers[index].id=index;
        if(pthread_create(&thread,&attributes,work,workers+index))abort();
    }
    if(pthread_attr_destroy(&attributes))abort();
    wait();
'''


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def pins(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def _span(data, begin, end):
    if data.count(begin) != 1 or data.count(end) != 1:
        raise ValueError('unique hosted source boundary required')
    first, last = data.index(begin), data.index(end)
    if last <= first:
        raise ValueError('ordered hosted source boundaries required')
    return data[first:last]


def _admit(files):
    if set(files) != set(INPUT) or any(type(data) is not bytes for data in files.values()):
        raise ValueError('exact audited six-file byte input required')
    expected = {name: dict(bytes=size, sha256=sha) for name, (size, sha) in INPUT.items()}
    if pins(files) != expected or any(b'\r' in data for data in files.values()):
        raise ValueError('audited fast-capacity LF source pin differs')


def transform(files, source):
    """Project only platform ownership; return four readable units and full inverse."""
    _admit(files)
    runtime, tiny = files['runtime.c'], files['tiny.h']
    declarations = _span(tiny, b'/* This candidate supplies', b'#if DEV\nextern int tiny_errno;')
    platform = _span(runtime, b'/* Linux x86-64 only.', b'Entry *table;\n')
    pool = _span(runtime, b'__attribute__((used,externally_visible)) _Noreturn void work',
                 b'#if DEV\nstatic void clear(void)')
    startup = _span(runtime, b'int main(void){\n', b'    for(;;){\n        int valid=read_line(line);')
    old_clock = b'uint64_t now(void){long t[2];if(Dsc2(228,(long)(1),(long)(t)))abort();return (uint64_t)t[0]*1000+(uint64_t)t[1]/1000000;}'
    new_clock = b'uint64_t now(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}'
    edits = {
        'tiny.h': [('hosted-library-declarations-and-status2-failure', declarations, HEADERS)],
        'runtime.c': [
            ('libc-platform-and-semaphore-error-owner', platform, PLATFORM),
            ('input-owned-busy-and-semaphore-storage', b'static atomic_int epoch,pending;',
             b'static atomic_int pending;\nstatic sem_t jobs[WORKERS],completed;\nstatic int busy;'),
            ('libc-monotonic-clock', old_clock, new_clock),
            ('libc-counted-write-and-EINTR',
             b'long z=Dsc3(1,1,(long)s,(long)n);if(z==-4)continue;',
             b'long z=write(1,s,n);if(z<0&&errno==EINTR)continue;'),
            ('pthread-pool-completion-and-output-publication', pool, POOL),
            ('libc-read-and-EINTR',
             b'got=Dsc3(0,(long)(0),(long)(&c),(long)(1));\n        if(got==-4)continue;',
             b'got=read(0,&c,1);\n        if(got<0&&errno==EINTR)continue;'),
            ('semaphore-job-dispatch',
             b'    atomic_store_explicit(&pending,WORKERS+1,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake(&epoch);',
             b'    atomic_store_explicit(&pending,WORKERS,memory_order_relaxed);busy=1;\n    for(int index=0;index<WORKERS;index++)semaphore_post(jobs+index);'),
            ('pthread-startup-with-explicit-resource-requests', startup, STARTUP),
        ],
    }
    output = {name: files[name] for name in UNITS}
    proof = dict(schema=SCHEMA, input=pins(files), source_edits={},
                 removed={name: files[name].decode() for name in ('start.S', 'image.ld')},
                 resource=dict(workers='unchanged', input_threads=1,
                               requested_stack_bytes=1048576, requested_guard_bytes=4096,
                               actual_pthread_mapping_identity=False,
                               tt_mapping='fresh anonymous mmap, unchanged page ranges',
                               dispatch='one semaphore post per worker'),
                 observation=dict(protocol='unchanged owned scanner and counted I/O',
                                  failure='whole-process status 2',
                                  completion='after all arrivals and full bestmove write',
                                  quit_eof='immediate main return; no added join/drain'),
                 runtime_qualified=False, selected=False)
    for name, roles in edits.items():
        output[name], proof['source_edits'][name] = source.project(files[name], roles)
    proof['output'] = pins(output)
    if restore(output, proof, source) != files:
        raise ValueError('hosted full six-file inverse differs')
    return output, proof


def restore(files, proof, source):
    if proof.get('schema') != SCHEMA or pins(files) != proof['output']:
        raise ValueError('hosted projection output differs')
    restored = dict(files)
    for name, record in proof['source_edits'].items():
        restored[name] = source.restore(files[name], record)
    restored.update({name: data.encode() for name, data in proof['removed'].items()})
    _admit(restored)
    if pins(restored) != proof['input']:
        raise ValueError('hosted projection input differs')
    return restored


def compiler_flags(workers, tt_bits):
    """One hosted compiler contract; no compiler or target probing occurs here."""
    if type(workers) is not int or type(tt_bits) is not int or not (1 <= workers <= 512 and 8 <= tt_bits <= 34):
        raise ValueError('admitted D worker/TT domain required')
    return ['-Os', '-std=c11', '-pthread', '-D_GNU_SOURCE', '-msse4.2', '-mcx16',
            '-DDEV=0', '-DD_HQ=0', '-DWORKERS=' + str(workers), '-DTT_BITS=' + str(tt_bits)]


def preprocessing_input(files):
    """Give the existing Host CPP owner local C with library includes withheld.

    CPP selects the actual DEV=0/D_HQ=0/profile branches without expanding system
    headers. The exact includes are restored before lexical compaction/compile.
    No C expression, type, table, move or search policy is rewritten here.
    """
    if set(files) != set(UNITS) or any(type(data) is not bytes for data in files.values()):
        raise ValueError('four hosted readable byte units required')
    headers, body = [], []
    for name in UNITS:
        data = files[name]
        if name != 'tiny.h':
            if data.count(b'#include "tiny.h"\n') != 1:
                raise ValueError('unique local header include required')
            data = data.replace(b'#include "tiny.h"\n', b'', 1)
        for line in data.splitlines(keepends=True):
            if line.startswith(b'#include <'):
                headers.append(line)
            else:
                body.append(line)
        body.append(b'\n')
    if len(headers) != len(set(headers)):
        raise ValueError('unique hosted library includes required')
    return b''.join(body), b''.join(headers)


def shipping_source(preprocessed, headers, minifier):
    """Restore direct library includes, using the existing lexical minifier."""
    if type(preprocessed) is not bytes or type(headers) is not bytes:
        raise ValueError('captured CPP output and exact header bytes required')
    if not headers or any(not line.startswith(b'#include <') for line in headers.splitlines()):
        raise ValueError('direct hosted library includes required')
    if b'#include' in preprocessed:
        raise ValueError('unexpected includes in header-withheld CPP output')
    return minifier.compact_source(headers + preprocessed, 'c')


def package_source(main, flags, packaging, bootstrap, source):
    """Later approved cost only: reuse the existing envelope/codec/bootstrap owners.

    This explicitly removes the old mandatory own-ELF linker-script argument.
    Temporary-directory cleanup, open-before-unlink and fdexec stay owned by the
    existing source bootstrap. Calling this function compresses; rendering does not.
    """
    original = packaging.SOURCE_CODE.encode()
    code, projection = source.project(original, [
        ('hosted-compiler-without-own-ELF-linker-script',
         b',"-Wl,-T,"+d+"/image.ld"', b''),
    ])
    adapter = SimpleNamespace(SOURCE_CODE=code.decode(), encode=packaging.encode,
                              envelope=packaging.envelope)
    whole, detail = bootstrap.package_source({'main.c': main}, flags, ('main.c',), adapter)
    detail.update(kind='D-hosted-source-bootstrap-v1', compiler_projection=projection,
                  carrier='general-4K hosted C; ELF packaging deferred',
                  runtime_qualified=False, selected=False)
    return whole, detail
