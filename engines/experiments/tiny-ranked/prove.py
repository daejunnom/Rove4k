"""Narrow actual-code equivalence; owned outputs must be outside the checkout.

Two settings only: -Os and the same -Os with ASan/UBSan. The exact frozen
source is instrumented at function boundaries/sites in an external copy.
Ordered events use two canonical numeric rolling hashes. Complete final TT,
learning arrays, path, public root board and worker scalars are compared byte
for byte after explicit width-independent numeric serialization.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time


EXPECTED = {
    'baseline': '109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504',
    'ranked': '5a3b878a48210e9068e461fee1d94e96fd2664eff6dac21a487a0c7035b61e0e',
    'ranked32': '56f332401431f76358c7a8de0f671bc434a91d1d0e93c9bff8e57350b67066ee',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('frozen instrumentation site changed: ' + old[:100])
    return text.replace(old, new)


def end_brace(text, opening):
    level, quote, comment, i = 0, None, None, opening
    while i < len(text):
        ch = text[i]
        if comment == 'line':
            if ch == '\n': comment = None
        elif comment == 'block':
            if text[i:i+2] == '*/': comment = None; i += 1
        elif quote:
            if ch == '\\': i += 1
            elif ch == quote: quote = None
        elif text[i:i+2] == '//': comment = 'line'; i += 1
        elif text[i:i+2] == '/*': comment = 'block'; i += 1
        elif ch in '\"\'': quote = ch
        elif ch == '{': level += 1
        elif ch == '}':
            level -= 1
            if not level: return i + 1
        i += 1
    raise ValueError('unbalanced frozen source')


def wrap(text, declaration, renamed, wrapper):
    if text.count(declaration) != 1: raise ValueError(declaration)
    start = text.index(declaration)
    end = end_brace(text, text.index('{', start))
    body = text[start:end].replace(declaration, renamed, 1)
    return text[:start] + body + '\n' + wrapper + text[end:]


def instrument(source, fixture, form):
    text = source.decode()
    declarations = '''
#include <stddef.h>
static void proof_fail(const char *);
static void raw_move(Move);
static void trace_word(uint64_t);
static void trace_begin(unsigned);
static void rank_priority(int,Move,int);
static void rank_pick(Worker *,const Board *,int,int,Move);
int make(const Board *,Move,Board *);
static int search(Worker *,const Board *,int,int,int,int,int,Move *);
'''
    text = once(text, 'Board position;', 'Board position;\n' + declarations)
    is_base = form == 'baseline'
    marker = ('        if(PROMO(m))scores[i]+=400000+PROMO(m)*1000;' if is_base else
              '        if(PROMO(m))priority+=400000+(int)PROMO(m)*1000;')
    text = once(text, marker, marker + '\n        rank_priority(i,m,' + ('scores[i]' if is_base else 'priority') + ');')
    start = text.index('    for(int i=0;i<count;i++){\n        Move m=moves[i];int from=')
    rank_end = end_brace(text, text.index('{', start))
    selection_start = text.index('    for(int i=0;i<count;i++){', rank_end)
    selection_stop = text.index('        Board q;if(!make(p,m,&q))continue;', selection_start)
    rank_block = text[start:rank_end]
    select_prefix = text[selection_start:selection_stop]
    selector = ('static void select_fixture(Worker *w,const Board *p,int prior,Move tt,Move *moves,int count,Move *out){\n'
                + ('int scores[MOVES];\n' if is_base else '') + rank_block + '\n' + select_prefix
                + 'rank_pick(w,p,0,i,m);out[i]=m;\n}\n}\n')
    text = once(text, '        Board q;if(!make(p,m,&q))continue;',
                '        rank_pick(w,p,ply,i,m);\n        Board q;if(!make(p,m,&q))continue;')
    text = wrap(text, 'int make(const Board *p,Move m,Board *t)',
                'int real_make(const Board *p,Move m,Board *t)', '''
int make(const Board *p,Move m,Board *t){
    raw_move(m);trace_begin(3);trace_word(p->h);trace_word(p->r);trace_word((unsigned)m);
    int ok=real_make(p,m,t);trace_word(ok);if(ok){trace_word(t->h);trace_word(t->r);}return ok;
}''')
    text = wrap(text, 'int gen(const Board *p,Move *moves)',
                'int real_gen(const Board *p,Move *moves)', '''
int gen(const Board *p,Move *moves){
    int n=real_gen(p,moves);trace_begin(4);trace_word(p->h);trace_word(n);
    for(int i=0;i<n;i++){raw_move(moves[i]);trace_word((unsigned)moves[i]);}return n;
}''')
    text = wrap(text, 'static uint64_t probe(uint64_t key,uint64_t data)',
                'static uint64_t real_probe(uint64_t key,uint64_t data)', '''
static uint64_t probe(uint64_t key,uint64_t data){
    if(data){if(data>>43)proof_fail("TT payload has bits above its fixed layout");raw_move((Move)(data&131071));}
    uint64_t result=real_probe(key,data);trace_begin(5);trace_word(key);trace_word(data);trace_word(result);return result;
}''')
    text = wrap(text, 'static int capture(const Board *p,Move m)',
                'static int real_capture(const Board *p,Move m)', '''
static int capture(const Board *p,Move m){
    raw_move(m);int result=real_capture(p,m);trace_begin(6);trace_word(p->h);trace_word((unsigned)m);trace_word(result);return result;
}''')
    declaration = 'static int search(Worker *w,const Board *p,int depth,int alpha,int beta,int ply,int prior,Move *root)'
    text = wrap(text, declaration, declaration.replace(' search(', ' real_search('), '''
static int search(Worker *w,const Board *p,int depth,int alpha,int beta,int ply,int prior,Move *root){
    if(root)raw_move(*root);
    trace_begin(7);trace_word(p->h);trace_word(p->r);trace_word((uint64_t)(int64_t)depth);
    trace_word((uint64_t)(int64_t)alpha);trace_word((uint64_t)(int64_t)beta);trace_word(ply);trace_word(prior);trace_word(w->length);trace_word(root?1:0);
    int result=real_search(w,p,depth,alpha,beta,ply,prior,root);
    trace_begin(8);trace_word((uint64_t)(int64_t)result);trace_word(w->length);if(root){raw_move(*root);trace_word((unsigned)*root);}return result;
}''')
    text = once(text, 'int main(void)', 'int original_application_main(void)')
    prefix = '#if UINT_MAX != 0xffffffffu\n#error proof requires the frozen Linux unsigned32 target\n#endif\n#define PROOF_SCORE_ARRAY_BYTES ' + ('(MOVES*sizeof(int))' if is_base else '0') + '\n'
    # The selector definition is appended after the fixture prototype so no
    # second model or alternate engine search is introduced.
    combined = text + '\n' + prefix + fixture + '\n' + selector
    return combined.encode(), {'rank_block_sha256': sha(rank_block.encode()),
                               'select_prefix_sha256': sha(select_prefix.encode())}


def run(command, cwd, timeout):
    then = time.monotonic()
    p = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout)
    return {'command': [str(x) for x in command], 'returncode': p.returncode,
            'stdout': p.stdout, 'stderr': p.stderr, 'elapsed_seconds': time.monotonic()-then}


def native_metadata(sources, out):
    """Inspect/reproduce already selected native bytes at the same -Os setting."""
    frozen = json.loads((sources/'results.json').read_text())
    expected = {item['id']: item for item in frozen['forms']}
    result = []
    for form in EXPECTED:
        folder = out/'native-metadata'/form;folder.mkdir(parents=True)
        source = (sources/form/'main.c').read_bytes()
        actual = (sources/form/'x').read_bytes()
        if sha(source) != expected[form]['source_sha256'] or sha(actual) != expected[form]['native_sha256']:
            raise ValueError('actual native identity drift '+form)
        command = ['cc','-Os','-x','c','-','-o','x','-s','-fstack-usage']
        p = subprocess.run(command, input=source, cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        if p.returncode: raise RuntimeError('native stack compile '+p.stderr.decode())
        reproduced = (folder/'x').read_bytes()
        if actual != reproduced: raise RuntimeError('stack-usage instrumentation changed selected native bytes '+form)
        size = run(['size','-A',str((sources/form/'x').resolve())], folder, 10)
        sections = {}
        for line in size['stdout'].splitlines():
            cells = line.split()
            if len(cells)==3 and cells[0].startswith('.') and cells[1].isdigit(): sections[cells[0]]=int(cells[1])
        stack = []
        for path in folder.glob('*.su'): stack.extend(path.read_text().splitlines())
        # Type spellings are pinned by the exact source hash above. This ABI
        # query uses the shipping preprocessed types, not the DEV Worker.
        abi_source = once(source.decode(),'int main(void)','int original_application_main(void)') + '''
int main(void){printf("{\\"Board\\":%zu,\\"Worker\\":%zu,\\"Move\\":%zu,\\"Entry\\":%zu,\\"workers\\":%zu}\\n",sizeof(E),sizeof(ai),sizeof(Move),sizeof(Entry),sizeof workers);return 0;}
'''
        (folder/'abi.c').write_text(abi_source)
        abi_build = run(['cc','-Os','abi.c','-o','abi'], folder, 60)
        if abi_build['returncode']: raise RuntimeError('native ABI build '+abi_build['stderr'])
        abi_run = run([str(folder/'abi')], folder, 10)
        if abi_run['returncode']: raise RuntimeError('native ABI execution')
        # Recover the search function's fixed spelling from its eight-argument
        # signature in this exact preprocessed input, for readable stack data.
        match = re.search(r'static int (\w+)\(ai\*\w+,const E\*\w+,int \w+,int \w+,int \w+,int \w+,int \w+,Move\*\w+\)',source.decode())
        search_name = match.group(1) if match else None
        search_stack = [line for line in stack if search_name and re.search(r':'+re.escape(search_name)+r'\t',line)]
        result.append({'id':form,'actual_native_bytes':len(actual),'actual_native_sha256':sha(actual),
                       'native_reproduced_with_fstack_usage':True,'command':command,'sections':sections,
                       'stack_usage':stack,'search_spelling':search_name,'search_stack_usage':search_stack,
                       'shipping_abi':json.loads(abi_run['stdout'])})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--trace-bytes', action='store_true', help='also compare complete real-search event streams byte for byte')
    parser.add_argument('--Os-only', action='store_true', help='narrow supplemental capture; prior sanitizer proof remains separate')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    if out == root or root in out.parents: raise SystemExit('evidence must be outside checkout')
    out.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).with_name('equivalence.c.in').read_text()
    report = {'scope': __doc__, 'sources': {}, 'settings': [], 'comparisons': [], 'pass': False,
              'trace_byte_capture': args.trace_bytes,
              'fixture_sha256': sha(fixture.encode()), 'driver_sha256': sha(Path(__file__).read_bytes()),
              'compiler': run(['cc','--version'], out, 10)['stdout'].splitlines()[0],
              'trace_scope': 'ordered canonical numeric events: actual search entry/return, per-node priority/pick, gen outputs, make arguments/outcome/child h+r, capture arguments, TT request/result',
              'state_scope': 'full canonical numeric Board, Worker scalars, all key/history/continuation/correction arrays, counters, game path, searched/stopped, every TT key and data; atomic flags asserted clear',
              'limits': ['single worker deterministic fixed depth; no SMP timing, NPS or playing-strength claim',
                         'worker ids are the fixed production-admitted 0 and 1; arbitrary large int ids are outside this equivalence claim',
                         'ordered trace equality uses two 64-bit rolling hashes plus exact event/word counts; final full state equality is byte for byte',
                         'public Move and Worker ABI sizes intentionally differ and are metadata, not equal-state bytes']}
    def save(): (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    try:
        generated = {}
        for form, expected in EXPECTED.items():
            source = (args.sources/form/'combined.c').read_bytes()
            if sha(source) != expected: raise ValueError('frozen source hash mismatch '+form)
            body, info = instrument(source, fixture, form)
            generated[form] = body
            report['sources'][form] = {'readable_sha256': expected, 'instrumented_sha256': sha(body), **info}
        settings = [('Os', [])]
        if not args.Os_only: settings.append(('Os-ASan-UBSan', ['-fsanitize=address,undefined','-fno-omit-frame-pointer']))
        for setting, extra in settings:
            entry = {'id': setting, 'forms': []}; report['settings'].append(entry); save()
            baseline_records, baseline_state, baseline_trace = None, None, None
            for form, body in generated.items():
                folder = out/setting/form;folder.mkdir(parents=True)
                (folder/'proof.c').write_bytes(body)
                command = ['cc','-std=c11','-Os','-DDEV=1','-DWORKERS=1','-DTT_BITS=18','-fstack-usage',*extra,'proof.c','-pthread','-o','proof']
                build = run(command, folder, 60)
                result = {'id': form, 'build': build};entry['forms'].append(result);save()
                if build['returncode']: raise RuntimeError('proof compilation failed '+setting+'/'+form)
                execute = [str(folder/'proof'),str(folder/'state.bin')]
                if args.trace_bytes: execute.append(str(folder/'trace.bin'))
                execution = run(execute, folder, 240)
                result['execution'] = execution
                records = [json.loads(line) for line in execution['stdout'].splitlines()]
                result['records'] = records
                if execution['returncode']: save();raise RuntimeError('proof execution failed '+setting+'/'+form)
                state = (folder/'state.bin').read_bytes()
                result['state_bytes'] = len(state); result['state_sha256'] = sha(state)
                result['binary_sha256'] = sha((folder/'proof').read_bytes())
                semantic = [r for r in records if r['kind'] != 'abi']
                trace = (folder/'trace.bin').read_bytes() if args.trace_bytes else None
                if trace is not None:
                    result['trace_bytes'] = len(trace);result['trace_sha256'] = sha(trace)
                if baseline_records is None: baseline_records, baseline_state, baseline_trace = semantic, state, trace
                else:
                    comparison = {'setting': setting,'candidate': form,'ordered_trace_and_scalars_equal': semantic == baseline_records,
                                  'full_numeric_state_byte_equal': state == baseline_state}
                    report['comparisons'].append(comparison)
                    if args.trace_bytes: comparison['full_real_search_trace_byte_equal'] = trace == baseline_trace
                    if not all(comparison[k] for k in ('ordered_trace_and_scalars_equal','full_numeric_state_byte_equal')):
                        save();raise RuntimeError('equivalence mismatch '+setting+'/'+form)
                    if args.trace_bytes and not comparison['full_real_search_trace_byte_equal']:
                        save();raise RuntimeError('actual event byte stream mismatch '+setting+'/'+form)
                (folder/'state.bin.gz').write_bytes(gzip.compress(state, mtime=0))
                (folder/'state.bin').unlink()
                if trace is not None:
                    (folder/'trace.bin.gz').write_bytes(gzip.compress(trace, mtime=0))
                    (folder/'trace.bin').unlink()
                stack = []
                for path in folder.glob('*.su'):
                    stack.extend(path.read_text().splitlines())
                result['stack_usage'] = stack
                save()
            selection = next(r for r in baseline_records if r['kind']=='selection')
            searches = [r for r in baseline_records if r['kind']=='search']
            if selection['negative_history_values'] != 32768 or selection['negative_continuation_values'] != 32768:
                raise RuntimeError('full negative range was not exercised')
            if not all(sum(r[k] for r in searches)>0 for k in ('pvs','qs','hits','hist','cont','corr','corr_use')):
                raise RuntimeError('required retained search path was not exercised')
        report['native_metadata'] = native_metadata(args.sources, out)
        report['pass'] = True;save();print(json.dumps({'pass': True,'out': str(out),'comparisons': report['comparisons']}))
    except Exception as error:
        report['error'] = repr(error);save();raise


if __name__ == '__main__': main()
