"""Pure, pinned specialization of canonical C's fixed explicit-root policy.

This module removes unreachable policy branches from the supplied canonical
source.  It contains no alternate scheduler and performs no file/process I/O.
The caller owns translation, lexical compaction, compilation and packaging.
"""
import hashlib


CANONICAL = {
    'c/parallel.h': (16756, '4cc244382353644ec802d1c07e79d532e9d5e79ac84cb0f3b403a37ca649f174'),
    'c/search.c': (22128, '00f2a88240be02caa96de06b3b2ce762be081a94275bede7d776c994e801b53e'),
    'c/main.c': (9959, '2d5287d4effe243c2b859330adc93c954dd588038d66ca398beabf8cdf0bc036'),
    'c/rove.h': (3812, '04e70b42700d2b9325d1fa4b1e4906699b0ccb2f59882e3842763dc74313c9f9'),
}


def _pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


class _Plan:
    def __init__(self, text, functions, mask):
        self.text, self.functions, self.mask = text, functions, mask
        self.edits = []

    def function(self, name):
        found = [item for item in self.functions(self.text) if item[0] == name]
        if len(found) != 1:
            raise ValueError(f'fixed root expected one {name} definition')
        _, start, end, _ = found[0]
        return start, end

    def locate(self, name, spelling):
        start, end = self.function(name) if name else (0, len(self.text))
        if self.text[start:end].count(spelling) != 1:
            raise ValueError(f'fixed root expected one {spelling!r} in {name}')
        return self.text.index(spelling, start, end)

    def edit(self, start, end, replacement, reason):
        if not 0 <= start <= end <= len(self.text):
            raise ValueError('fixed root invalid source span')
        self.edits.append((start, end, replacement, reason))

    def replace(self, name, old, new, reason):
        start = self.locate(name, old)
        self.edit(start, start + len(old), new, reason)

    def block(self, name, prefix):
        start = self.locate(name, prefix)
        opening = start + len(prefix) - 1
        if self.text[opening] != '{':
            raise ValueError('fixed root block prefix must end in opening brace')
        masked = self.mask(self.text)
        depth = 1
        end = opening + 1
        while depth and end < len(masked):
            depth += (masked[end] == '{') - (masked[end] == '}')
            end += 1
        if depth:
            raise ValueError('fixed root unterminated owned branch')
        return start, opening + 1, end

    def remove_block(self, name, prefix, reason):
        start, _, end = self.block(name, prefix)
        self.edit(start, end, '', reason)

    def remove_function(self, name, reason):
        start, end = self.function(name)
        self.edit(start, end, '', reason)

    def finish(self):
        edits = sorted(self.edits)
        parts, gaps, inverse, observations = [], [], [], []
        cursor = output_cursor = 0
        for start, end, replacement, reason in edits:
            if start < cursor:
                raise ValueError('fixed root overlapping source edits')
            gap = self.text[cursor:start]
            old = self.text[start:end]
            parts.extend((gap, replacement))
            gaps.append(gap)
            output_cursor += len(gap)
            inverse.extend((gap, old))
            observations.append({
                'reason': reason, 'input_start': start, 'input_end': end,
                'output_start': output_cursor, 'output_end': output_cursor + len(replacement),
                'before': _pin(old.encode()), 'after': _pin(replacement.encode()),
            })
            output_cursor += len(replacement)
            cursor = end
        tail = self.text[cursor:]
        parts.append(tail)
        gaps.append(tail)
        inverse.append(tail)
        result = ''.join(parts)
        if ''.join(inverse) != self.text:
            raise ValueError('fixed root inverse mismatch')
        # Read unchanged gaps back from the output; matching old text alone is
        # insufficient evidence if output offsets or a replacement were wrong.
        cursor = 0
        for gap, observation in zip(gaps, observations):
            if result[cursor:observation['output_start']] != gap:
                raise ValueError('fixed root protected gap mismatch')
            cursor = observation['output_end']
        if result[cursor:] != tail:
            raise ValueError('fixed root protected tail mismatch')
        return result.encode(), {
            'input': _pin(self.text.encode()), 'output': _pin(result.encode()),
            'raw_delta': len(result.encode()) - len(self.text.encode()),
            'regions': observations, 'protected_gaps': len(gaps),
            'protected_complement': _pin(''.join(gaps).encode()),
            'all_gaps_equal': True, 'full_inverse': True,
        }


def specialize_sources(files, *, functions, mask):
    """Specialize one exact canonical snapshot; preserve all other input files.

    Inputs must already use LF, as normalized by prepare_sources.  The supplied
    parser/mask are the generator's existing owned-C helpers, not a second parser.
    """
    result = dict(files)
    for name, (size, digest) in CANONICAL.items():
        data = result[name]
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f'fixed root canonical source binding changed: {name}')
    plans = {name: _Plan(result[name].decode('ascii'), functions, mask)
             for name in ('c/parallel.h', 'c/search.c', 'c/rove.h')}
    p = plans['c/parallel.h']
    p.remove_function('rove_parallel_refutes', 'no constrained counterreply producer in fixed mode1')
    p.remove_block('rove_parallel_worker', 'if(p->mode==0) {', 'no whole-root Loose worker')
    p.replace('rove_parallel_worker', 'ROVE_NORMAL,p->groups>1?(int)id/4:0,p->generation,p->groups',
              'ROVE_NORMAL,0,p->generation,1', 'all NORMAL root tasks use group0/groups1')
    p.replace('rove_parallel_worker',
              '        if(p->groups>1 && p->bestalpha>p->alpha && p->bestgroup!=task.group)\n'
              '            p->result.shared_bounds++;\n', '', 'one group has no cross-group bound publication')
    p.replace('rove_parallel_search', 'p.groups=mode==2?(workers+3)/4:1;', 'p.groups=1;',
              'fixed root has one shared total-budget TT group')
    p.replace('rove_parallel_search',
              'workers<1 || workers>512 || n<1 || alpha>=beta || stopped(context)',
              'workers!=2 || mode!=1 || n<1 || alpha>=beta || stopped(context)',
              'reject calls outside the fixed source/build profile')
    p.remove_block('rove_parallel_search', 'if(mode==0) {', 'no Loose dispatch in fixed root')
    p.remove_block('rove_parallel_search', 'if(mode==4) {', 'no hybrid policy selection in fixed mode1')
    p.remove_block('rove_parallel_search', 'if(p.mode==3 && depth>1 && r.bound!=ROVE_UPPER) {',
                   'no selector/counterreply/Repair producer in fixed mode1')

    p = plans['c/search.c']
    p.remove_function('parallel_reply', 'no PALS reply selector consumer')
    p.replace('parallel_task',
              'task->generation!=c->generation||worker>=ROVE_WORKERS||parallel_stopped(arg)',
              'task->generation!=c->generation||worker>=ROVE_WORKERS||'
              'task->kind!=ROVE_NORMAL||!task->first||task->group||task->groups!=1||parallel_stopped(arg)',
              'only nonzero first NORMAL/group0/groups1 tasks reach the child callback')
    p.remove_block('parallel_task', 'if(task->kind==ROVE_SELECT_REPLY){', 'no selector task in fixed mode1')
    p.replace('parallel_task',
              'size_t total=(size_t)1<<ROVE_TT_BITS,part=total;while(part*(size_t)task->groups>total)part>>=1;'
              'w->table=rove_tt+(size_t)task->group*part;w->table_mask=part-1;',
              'w->table=rove_tt;w->table_mask=((size_t)1<<ROVE_TT_BITS)-1;',
              'group0/groups1 consumes the complete existing shared TT allocation')
    start, _, end = p.block('parallel_task', 'if(!task->first){')
    suffix = '\n    else '
    if p.text[end:end + len(suffix)] != suffix:
        raise ValueError('fixed root expected whole-root/partial-root alternative')
    p.edit(start, end + len(suffix), '', 'remove whole-root-only callback alternative')
    p.replace('parallel_task', 'task->kind!=ROVE_COUNTERREPLY&&drawn(', 'drawn(',
              'NORMAL root draw test still precedes child make')
    counter, _, counter_end = p.block('parallel_task', 'if(task->kind==ROVE_COUNTERREPLY){')
    repair, _, repair_end = p.block('parallel_task', 'else{if(task->kind==ROVE_REPAIR){')
    # That prefix enters the inner if. Match the outer else independently, then
    # copy its NORMAL continuation verbatim after the unreachable Repair hint.
    else_start = repair
    outer_open = else_start + len('else{')
    masked = p.mask(p.text)
    depth, outer_end = 1, outer_open
    while depth and outer_end < len(masked):
        depth += (masked[outer_end] == '{') - (masked[outer_end] == '}')
        outer_end += 1
    if depth or p.text[counter_end:else_start].strip():
        raise ValueError('fixed root expected paired counterreply/normal branches')
    continuation = p.text[repair_end:outer_end - 1]
    expected = ('score=-search(w,&child,task->depth-1,-task->beta,-task->alpha,1,0,1);'
                'if(w->pvlen[1])r.reply=w->pv[1][0];')
    if continuation != expected:
        raise ValueError('fixed root NORMAL partial-child continuation changed')
    p.edit(counter, outer_end, continuation,
           'extract canonical NORMAL ply1 continuation, no constrained reply or Repair hint')

    p = plans['c/rove.h']
    guard = ('#if ROVE_VARIANT != 1 || ROVE_DEV || ROVE_MODEL || ROVE_PARALLEL != 1 || '
             'ROVE_WORKERS != 2 || ROVE_TT_BITS != 18\n'
             '#error fixed root source requires shipping A, mode1, workers2 and TT18\n'
             '#endif\n')
    offset = p.locate(None, '#define MAXPLY 96\n')
    p.edit(offset, offset, guard, 'source/build fixed profile, no public UCI option')

    observations = {}
    for name, plan in plans.items():
        result[name], observations[name] = plan.finish()
    # Preserve critical owned functions byte-for-byte, rather than just their
    # names or line counts. No score, learner, Board or TT algorithm is replaced.
    protected = {}
    for name, symbols in {
        'c/parallel.h': ('rove_parallel_reusable', 'rove_parallel_valid', 'rove_parallel_accept',
                         'rove_parallel_helper', 'rove_parallel_join', 'rove_parallel_init',
                         'rove_parallel_shutdown', 'rove_parallel_pool'),
        'c/search.c': ('search', 'parallel_stopped', 'run_parallel', 'session_run'),
    }.items():
        old = {n: body for n, _, _, body in functions(files[name].decode('ascii'))}
        new = {n: body for n, _, _, body in functions(result[name].decode('ascii'))}
        for symbol in symbols:
            if old[symbol] != new[symbol]:
                raise ValueError(f'fixed root protected function changed: {symbol}')
            protected[symbol] = _pin(new[symbol].encode())
    unchanged = {name: _pin(data) for name, data in files.items() if result[name] == data}
    return result, {
        'applied': True, 'operation': 'fixed-root-source-specialization',
        'producer': 'canonical-C-mode1-policy-extraction-v1',
        'profile': {'variant': 'A', 'parallel': 1, 'development': False, 'model': False,
                    'search_workers': 2, 'tt_bits': 18, 'total_engine_threads': 3},
        'files': observations, 'unchanged_files': unchanged, 'protected_functions': protected,
        'normal_cache': 'same invocation; complete generation/depth/first and compatible EXACT/LOWER/UPPER',
        'repair_producer': False, 'new_scheduler': False,
        'partial_first': 'canonical make + child key + previous[0] + negated ply1 search',
        'observation_scope': 'fixed production policy; source locations and out-of-profile callback admission change; canonical data declarations retained',
        'native_whole_runtime_measured': False,
    }
