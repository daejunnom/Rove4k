"""Optional structural C-source reductions, applied before lexical compaction.

The canonical board/search remain in engines/c.  Shipping startpos does not need
a FEN interpreter; fixed Loose SMP does not need the root/group/PALS scheduler.
These are explicit domain specializations, not general C optimizer claims.
"""
from pathlib import Path
import hashlib
import re


HERE = Path(__file__).resolve().parent


def _mask(text):
    """Mask comments/literals/directives while retaining offsets and braces."""
    pattern = re.compile(r'(?m)^[ \t]*\#[^\n]*(?:\\\n[^\n]*)*|'
                         r'//[^\n]*|/\*[\s\S]*?\*/|'
                         r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
    return pattern.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m.group()), text)


def functions(text):
    """Find complete top-level C function definitions, excluding declarations.

    Operates on preprocessed owned declarations (system headers remain includes).
    It does not parse arbitrary C: unsupported top-level function syntax raises
    instead of removing a definition on a guessed name.
    """
    mask = _mask(text)
    depth = 0
    boundary = 0
    output = []
    i = 0
    while i < len(mask):
        c = mask[i]
        if c == '{':
            if depth == 0:
                prefix = mask[boundary:i]
                j = len(prefix) - 1
                while j >= 0 and prefix[j].isspace():
                    j -= 1
                name = None
                if j >= 0 and prefix[j] == ')':
                    end, nesting = j, 1
                    j -= 1
                    while j >= 0 and nesting:
                        if prefix[j] == ')': nesting += 1
                        if prefix[j] == '(': nesting -= 1
                        j -= 1
                    if nesting:
                        raise ValueError('unbalanced top-level function signature')
                    match = re.search(r'([A-Za-z_]\w*)\s*$', prefix[:j + 1])
                    if match:
                        name = match.group(1)
                        if name in ('__attribute__', '__declspec', 'asm', '__asm__'):
                            raise ValueError('unsupported post-declarator function attribute')
                    else:
                        raise ValueError('unsupported function declarator')
                start = boundary
            depth += 1
        elif c == '}':
            depth -= 1
            if depth < 0:
                raise ValueError('unbalanced C source')
            if depth == 0:
                if name:
                    # Prefix contains only whitespace/directives before this
                    # declaration; keep directives independently of its body.
                    start = boundary
                    while start < i and (text[start].isspace() or mask[start] == ' '):
                        start += 1
                    output.append((name, start, i + 1, text[start:i + 1]))
                boundary = i + 1
        elif c == ';' and depth == 0:
            boundary = i + 1
        i += 1
    if depth:
        raise ValueError('unbalanced C source')
    return output


def replace_function(text, name, replacement):
    matches = [item for item in functions(text) if item[0] == name]
    if len(matches) != 1:
        raise ValueError(f'expected exactly one {name} definition, got {len(matches)}')
    _, begin, end, _ = matches[0]
    return text[:begin] + replacement + text[end:]


def prepare_sources(files, *, variant, parallel=0, development=False, model=False):
    """Return transformed sources and source/provenance observations.

    Only fixed Loose SMP (mode 0) is supported.  Other policies retain canonical
    sources.  Development keeps canonical FEN admission and diagnostics.
    """
    if variant not in 'ABCDEF' or len(variant) != 1:
        raise ValueError('one A-F candidate is required')
    result = dict(files)
    changes = []
    if parallel != 0:
        return result, [{'applied': False, 'reason': 'fixed-loose specialization requires parallel=0'}]
    if variant in 'ADF' and not model:
        # Every admitted/produced mailbox cell is in -6..6. Explicit signed
        # eight-bit cells preserve integer promotion at consumers, while copy-
        # make no longer carries four bytes per cell. E/model's int[128] API and
        # C's SIMD packing are intentionally left unchanged.
        header_text = result['c/rove.h'].decode()
        if header_text.count('int b[128], side') != 1:
            raise ValueError('expected the canonical signed-piece mailbox declaration')
        result['c/rove.h'] = header_text.replace('int b[128], side',
                                               'int8_t b[128];int side').encode()
        changes.append({'applied': True, 'operation': 'signed-byte-mailbox',
                        'contract': 'piece values -6..6; integer-promoted consumers; A/D/F without model API only',
                        'mailbox_bytes_before': 512, 'mailbox_bytes_after': 128})
    header = HERE / 'fixed_loose.h'
    result['c/parallel.h'] = header.read_bytes()
    changes.append({'applied': True, 'operation': 'fixed-loose-persistent-pool',
                    'template': str(header), 'sha256': hashlib.sha256(header.read_bytes()).hexdigest()})
    if not development:
        main_template = HERE / 'uci.c.in'
        main = main_template.read_text()
        if main.count('@VARIANT@') != 2:
            raise ValueError('shipping UCI template must have one comment and one variant marker')
        result['c/main.c'] = main.replace('@VARIANT@', variant).encode()
        changes.append({'applied': True, 'operation': 'shipping-session-owned-uci',
                        'template': str(main_template),
                        'sha256': hashlib.sha256(main_template.read_bytes()).hexdigest(),
                        'contract': 'fixed startup coordinator; session-owned board/history; transactional position; same minimum UCI'})
        text = result['c/board.c'].decode()
        text = replace_function(text, 'board_start', '''void board_start(Board *p){
    *p=(Board){0};p->side=1;p->castle=15;p->ep=-1;p->full=1;
    static const int rank[8]={4,2,3,5,6,3,2,4};
    for(int q=0;q<8;q++){
        put(p,q,rank[q]);put(p,q+16,1);
        put(p,q+96,-1);put(p,q+112,-rank[q]);
    }
    p->key=board_key(p);
}''')
        result['c/board.c'] = text.encode()
        changes.append({'applied': True, 'operation': 'direct-startpos-initialization',
                        'contract': 'same Board fields and generated initial position; no FEN parser at shipping runtime'})
    # The fixed scheduler only emits complete-root tasks (first=0, group=0,
    # groups=1), so eliminate the alternate root-move/counterreply callback.
    text = result['c/search.c'].decode()
    text = replace_function(text, 'parallel_task', '''static RoveResult parallel_task(void *arg,const RoveTask *task,unsigned worker){
    ParallelContext *c=arg;Session *s=c->session;RoveResult r={0};
    if(task->generation!=c->generation||worker>=ROVE_WORKERS||parallel_stopped(arg))return r;
    Worker *w=&c->workers[worker];w->aborted=0;w->seldepth=0;w->hint=0;w->hint_ply=-1;
    memcpy(w->path,s->history,(size_t)s->history_len*sizeof(uint64_t));w->path_len=s->history_len;
    w->table=rove_tt;w->table_mask=((size_t)1<<ROVE_TT_BITS)-1;
    uint64_t before=w->nodes;
    int score=search(w,&s->board,task->depth,task->alpha,task->beta,0,0,1);
    if(w->pvlen[0])r.first=w->pv[0][0];if(w->pvlen[0]>1)r.reply=w->pv[0][1];
    r.nodes=w->nodes-before;if(w->aborted||parallel_stopped(arg))return r;
    r.score=score;r.complete=1;
    r.bound=score<=task->alpha?ROVE_UPPER:score>=task->beta?ROVE_LOWER:ROVE_EXACT;
    return r;
}''')
    result['c/search.c'] = text.encode()
    changes.append({'applied': True, 'operation': 'complete-root-callback-specialization',
                    'contract': 'only first=0 group=0 groups=1 emitted by fixed-loose-persistent-pool'})
    if not development:
        text = result['c/search.c'].decode()
        text = replace_function(text, 'run_parallel', '''static void run_parallel(Session *s,Worker *workers){
    Move moves[MAXMOVES];int n=generate(&s->board,moves,0);
    if(!legal_witness(&s->board,moves,n)){
        s->score=in_check(&s->board)?-MATE:0;s->completed_depth=1;return;
    }
    int guess=0;
    for(int depth=1;depth<=s->depth;depth++){
        ParallelContext context={s,workers,s->generation*MAXPLY+(unsigned)depth,1};
        for(int i=1;i<ROVE_WORKERS;i++)
            memcpy(workers[i].correction,workers[0].correction,sizeof workers[0].correction);
        RoveParallelResult result={0};
#if ROVE_VARIANT == 6
        int lower=-INF,upper=INF,score=guess;unsigned best=s->best;
        while(lower<upper){
            int beta=score==lower?score+1:score;
            atomic_fetch_add_explicit(&rove_mtd_probes,1,memory_order_relaxed);
            result=rove_parallel_search(parallel_task,&context,0,0,depth,beta-1,beta,0,0,
                parallel_stopped,ROVE_WORKERS,0,context.generation,0);
            if(!result.completedall||!result.best.complete||parallel_stopped(&context))break;
            score=result.best.score;
            if(score<beta)upper=score;else{lower=score;best=result.best.first;}
        }
        if(lower!=upper||!result.best.complete||parallel_stopped(&context))break;
        result.best.score=score;result.best.first=best;
#else
        result=rove_parallel_search(parallel_task,&context,0,0,depth,-INF,INF,0,0,
            parallel_stopped,ROVE_WORKERS,0,context.generation,0);
        if(!result.completedall||!result.best.complete||parallel_stopped(&context))break;
#endif
        s->score=result.best.score;s->completed_depth=depth;
        if(result.best.first)s->best=result.best.first;
        guess=s->score;
        if(abs(s->score)>MATE-MAXPLY)break;
    }
}''')
        result['c/search.c'] = text.encode()
        changes.append({'applied': True, 'operation': 'shipping-loose-iteration-controller',
                        'contract': 'same root search and completed result; removes unused split-root moves, diagnostic PV copy and shipping counters'})
    return result, changes


def prune_sources(files):
    """Conservatively remove unreachable definitions after C specialization.

    Any occurrence of an owned function name in a reachable body is a dependency,
    including address-taking and function-pointer arguments.  Globals, macros and
    declarations are roots too.  Name collisions conservatively retain all same-
    named definitions.  This only removes definitions; unused declarations and
    types remain and the compiler must still accept the generated source.
    """
    parsed = {name: functions(data.decode()) for name, data in files.items() if name.endswith('.c')}
    definitions = {}
    for entries in parsed.values():
        for name, _, _, body in entries:
            definitions.setdefault(name, []).append(body)
    names = set(definitions)
    dependencies = {name: set(re.findall(r'\b[A-Za-z_]\w*\b', _mask('\n'.join(body)))) & names
                    for name, body in definitions.items()}
    reachable = {'main'} & names
    # Global/typedef/macro references may take function addresses. Prototypes do
    # not, but treating prototypes as roots would retain every public dev helper.
    # Reject such uncertain non-prototype references conservatively per name.
    for filename, entries in parsed.items():
        text = files[filename].decode()
        for _, begin, end, _ in reversed(entries):
            text = text[:begin] + (' ' * (end - begin)) + text[end:]
        # Macro aliases can hide address-taking or calls from lexical bodies.
        # Retaining their referenced definitions is deliberately conservative.
        directives = '\n'.join(re.findall(r'(?m)^[ \t]*\#[^\n]*(?:\\\n[^\n]*)*', text))
        reachable |= set(re.findall(r'\b[A-Za-z_]\w*\b', directives)) & names
        text = re.sub(r'(?m)^[^;{}\n]*\b[A-Za-z_]\w*\s*\([^;{}]*\)\s*;', '', _mask(text))
        reachable |= set(re.findall(r'\b[A-Za-z_]\w*\b', text)) & names
    pending = list(reachable)
    while pending:
        for dependency in dependencies[pending.pop()] - reachable:
            reachable.add(dependency)
            pending.append(dependency)
    result, observations = dict(files), []
    for filename, entries in parsed.items():
        text = files[filename].decode()
        for name, begin, end, body in reversed(entries):
            if name not in reachable:
                text = text[:begin] + text[end:]
                observations.append({'file': filename, 'function': name,
                                     'removed_bytes': len(body.encode()),
                                     'reason': 'no reference from main or owned global initializer'})
        result[filename] = text.encode()
    return result, observations
