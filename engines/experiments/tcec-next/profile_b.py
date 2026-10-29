"""Finite lossless source expressions for the exact full production B profiles.

Inputs are outputs of the maintained tracked-source producer and the named
resource projection, never historical generated inputs.  This module is pure:
it neither builds nor executes an engine and never chooses a winning recipe.
Startup/search callback sharing uses qh's existing lifetime: zero until all TT
initializers have joined, then at least one throughout the process lifetime.
"""
from hashlib import sha256
import re

SCHEMA = 'rove4k.profile-b-source.v1'
INPUTS = {
    ('test-p4', 'private-path'): (8664, 'fb3b8cb59408f0cfce604518b4df27f4f83216363bcd670e2575aa1826fb2ffe'),
    ('test-p4', 'none'): (8639, '6dddd3c112b5f71f2fcf7ace3a665ac6091eabcd5714db42ae5a1faf0b095d69'),
    ('test-p16', 'private-path'): (8665, '87093b6f8b13dc028d7fdaddee92064f3186c12a0e0faafba4c033985c445dfa'),
    ('test-p28', 'private-path'): (8665, 'e5b8c918408ac72031d5ada96840f4b6c073006a22f99562862d7a7d43f907e3'),
    ('test-p28', 'none'): (8640, 'f3cd589937a6ed2fe104180b911bbe82ba0e844dacf43092bd5c6f564d01e398'),
    ('test-p192', 'private-path'): (8666, 'e8d486dd31c999baaadb6c302ceb4f9ebf80f7a88c69e29d6f0c32670dfecabd'),
    ('tcec-provisional', 'private-path'): (8666, 'fff746dfa5da7c0f0307be1f3ad4d3e53104a6fb45ec7097e8695559f015b0b5'),
    ('tcec-provisional', 'none'): (8641, '5f764a24878828ced0d5929c1d6c2c44e6d347a432e616ef12b0e07b64afcaf2'),
}
# P28 and P192 divide page units unequally; preserve original page-owned
# boundaries, not a mathematically distinct per-entry floor division.
PAGE_FLOOR_PROFILES = frozenset(('test-p28', 'test-p192'))
VARIANTS = {
    'gain': (),
    'init': ('init',),
    'launch': ('init', 'launch'),
    'phase': ('init', 'phase'),
    'phase-load': ('init', 'phase', 'load'),
    'phase-load-store': ('init', 'phase', 'load', 'store'),
    'phase-names': ('init', 'phase', 'names'),
    'phase-load-names': ('init', 'phase', 'load', 'names'),
    'phase-load-store-names': ('init', 'phase', 'load', 'store', 'names'),
    'phase-q': ('init', 'phase', 'q'),
    'phase-q-load': ('init', 'phase', 'q', 'load'),
    'phase-q-load-store': ('init', 'phase', 'q', 'load', 'store'),
    'phase-q-load-names': ('init', 'phase', 'q', 'load', 'names'),
    'phase-compound': ('init', 'phase', 'compound'),
    'phase-compound-load': ('init', 'phase', 'compound', 'load'),
    'phase-compound-load-store': ('init', 'phase', 'compound', 'load', 'store'),
    'phase-compound-load-names': ('init', 'phase', 'compound', 'load', 'names'),
    'phase-compound-loop': ('init', 'phase', 'compound', 'loop'),
    'phase-loop': ('init', 'phase', 'loop'),
    'phase-loop-load-store': ('init', 'phase', 'loop', 'load', 'store'),
    'phase-if': ('init', 'phase', 'load', 'names', 'if'),
    'phase-void': ('init', 'phase', 'load', 'names', 'void'),
    'phase-const': ('init', 'phase', 'load', 'names', 'const'),
    'phase-if-store': ('init', 'phase', 'load', 'store', 'names', 'if'),
    'phase-if-loop': ('init', 'phase', 'load', 'names', 'if', 'loop'),
    'tcec-parser': ('init', 'phase', 'load', 'store', 'names', 'if', 'parser'),
    'tcec-parser-loop': ('init', 'phase', 'load', 'names', 'if', 'loop', 'parser'),
    'tcec-packed-move': ('init', 'phase', 'load', 'store', 'names', 'if', 'parser', 'packed-move'),
    'tcec-output': ('init', 'phase', 'load', 'store', 'names', 'if', 'parser', 'output'),
    'tcec-material': ('init', 'phase', 'load', 'store', 'names', 'if', 'parser', 'output', 'material'),
    'tcec-rights': ('init', 'phase', 'load', 'store', 'names', 'if', 'parser', 'output', 'rights'),
    'tcec-core': ('init', 'phase', 'load', 'store', 'names', 'if', 'parser', 'output', 'material', 'rights', 'numeric'),
    'tcec-core-loop': ('init', 'phase', 'load', 'names', 'if', 'loop', 'parser', 'output', 'material', 'rights', 'numeric'),
}
# Finite interaction comparison, not a selected expectation or an unbounded
# search. Each flag retains its own exact edit and semantic observation.
for _loop in (False, True):
    for _mask in range(16):
        VARIANTS['tcec-mix-'+('loop-' if _loop else '')+str(_mask)] = (
            'init', 'phase', 'load', 'names', 'if', 'parser',
            *(('loop',) if _loop else ('store',)),
            *(flag for bit, flag in enumerate(('output', 'material', 'rights', 'numeric')) if _mask & (1 << bit)))
VARIANTS['tcec-owner'] = (*VARIANTS['tcec-mix-14'], 'position-owner')
VARIANTS['tcec-owner-loop'] = (*VARIANTS['tcec-mix-loop-14'], 'position-owner')
VARIANTS['tcec-owner-rights'] = (*VARIANTS['tcec-mix-12'], 'position-owner')
VARIANTS['tcec-mmap'] = (*VARIANTS['tcec-owner'], 'mmap')
VARIANTS['tcec-mmap-loop'] = (*VARIANTS['tcec-owner-loop'], 'mmap')
VARIANTS['tcec-bound'] = (*VARIANTS['tcec-owner-loop'], 'bound')
VARIANTS['tcec-mmap-bound'] = (*VARIANTS['tcec-owner-loop'], 'mmap', 'bound')
VARIANTS['tcec-mmap-abi'] = (*VARIANTS['tcec-owner-loop'], 'mmap-abi', 'bound')
VARIANTS['tcec-rights-bits'] = (*VARIANTS['tcec-owner-loop'], 'bound', 'rights-bits')
VARIANTS['tcec-mmap-abi-bits'] = (*VARIANTS['tcec-owner-loop'], 'mmap-abi', 'bound', 'rights-bits')
VARIANTS['tcec-moves'] = (*VARIANTS['tcec-bound'], 'moves')
VARIANTS['tcec-moves-unsigned'] = (*VARIANTS['tcec-bound'], 'moves-unsigned')
VARIANTS['tcec-moves-promo'] = (*VARIANTS['tcec-bound'], 'moves', 'promo')
for _mask in range(8):
    VARIANTS['tcec-decimal-'+str(_mask)] = (*VARIANTS['tcec-bound'],
        *(str(bit)+'decimal' for bit in range(3) if _mask & (1 << bit)))
for _name in 'abcdfqtz':
    VARIANTS['tcec-main-'+_name] = (*VARIANTS['tcec-moves-promo'], 'main-'+_name)
VARIANTS['tcec-moves-decimal'] = (*VARIANTS['tcec-moves-promo'], '0decimal', '1decimal', '2decimal')
VARIANTS['tcec-compact'] = (*VARIANTS['tcec-moves-decimal'], 'compact')
VARIANTS['tcec-compact-arity'] = (*VARIANTS['tcec-moves-decimal'], 'compact', 'arity')
for _mask in range(8):
    VARIANTS['tcec-final-'+str(_mask)] = (*VARIANTS['tcec-moves-promo'], 'compact', 'arity', 'main-d',
        *(str(bit)+'decimal' for bit in range(3) if _mask & (1 << bit)))
VARIANTS['tcec-final-lf'] = (*VARIANTS['tcec-final-7'], 'lf')
ABI_PROBE = ('#define _GNU_SOURCE\n#include<sys/mman.h>\n'
             '_Static_assert((PROT_READ|PROT_WRITE)==3,"mmap protection ABI");\n'
             '_Static_assert((MAP_PRIVATE|MAP_ANONYMOUS)==34,"mmap flags ABI");\n'
             '_Static_assert(MAP_FAILED==(void*)-1,"mmap failure ABI");\n'
             'int main(void){return 0;}\n')


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def require(value, message):
    if not value:
        raise ValueError(message)


def transform_source(source, *, profile_id, entry_cleanup='private-path', variant='phase'):
    require(type(source) is bytes and INPUTS.get((profile_id, entry_cleanup)) ==
            (len(source), sha256(source).hexdigest()), 'exact named current full B profile required')
    require(variant in VARIANTS, 'explicit finite B profile variant required')
    flags = VARIANTS[variant]
    stages = []
    result = source

    def edit(role, before, after, *, count=1):
        nonlocal result
        before, after = before.encode(), after.encode()
        require(result.count(before) == count, 'one exact B profile consumer required: ' + role)
        offsets = [m.start() for m in re.finditer(re.escape(before), result)]
        rows, shift = [], 0
        for at in offsets:
            rows.append(dict(at=at, target=at+shift, before=before.decode(), after=after.decode()))
            shift += len(after) - len(before)
        old = result
        result = result.replace(before, after)
        stages.append(dict(role=role, input=pin(old), output=pin(result), edits=rows,
                           protected_gaps=_gaps(old, result, rows)))

    edit('bounded material gain product', '1+qi[abs(i)]+(qi[f]-100*!!f)',
         '1+qi[abs(i)]+qi[f]-!!f*100')
    init_old = ('J void*B(void*p){zd*w=p;size_t rv_n=w->i,'
                'rv_i=(RVN/RVU*rv_n/RVW)*RVU,rv_e=(RVN/RVU*(rv_n+1)/RVW)*RVU;'
                'for(;rv_i<rv_e;rv_i++){qq[rv_i].h=qq[rv_i].v=0;'
                'atomic_flag_clear_explicit(&qq[rv_i].a,memory_order_relaxed);}l 0;}')
    if 'init' in flags:
        # W4/W16/W256 divide the complete-page units. W28/W192 keep the
        # original floor partition exactly, including unequal page-owned ranges.
        ranges = ('i=RVN*n/RVW,e=RVN*(n+1)/RVW' if profile_id not in PAGE_FLOOR_PROFILES else
                  'i=RVN/RVU*n/RVW*RVU,e=RVN/RVU*(n+1)/RVW*RVU')
        init_body = ('size_t n=((zd*)p)->i,' + ranges +
                     ';for(;i<e;i++){qq[i].h=qq[i].v=0;'
                     'atomic_flag_clear_explicit(&qq[i].a,memory_order_relaxed);}')
        edit('same page-owned TT initialization', init_old, 'J void*B(void*p){'+init_body+'l 0;}')
        if profile_id not in PAGE_FLOOR_PROFILES:
            edit('unused unit constant', '#define RVU 512\n', '')
    launch = ('for(I n=0;n<RVW;n++){qr[n].i=n;qr[n].d=0;'
              'if(pthread_create(qb+n,0,s,qr+n))exit(2);}')
    startup = ('for(I n=0;n<RVW;n++){qr[n].i=n;'
               'if(pthread_create(qb+n,0,B,qr+n))exit(2);}')
    if 'launch' in flags:
        helper = ('J void V(void*(*f)(void*)){for(I n=0;n<RVW;n++)'
                  '{qr[n].i=n;qr[n].d=0;if(pthread_create(qb+n,0,f,qr+n))exit(2);}}')
        edit('shared spawn owner', 'J char*nt(void){', helper+'J char*nt(void){')
        edit('same GO callbacks', launch, 'V(s);')
        edit('same startup callbacks', startup, 'V(B);')
    if 'phase' in flags:
        # qh is main-owned and unchanged while either thread phase is alive.
        # Startup does not publish a result or decrement qj. U's qp=1 has no
        # consumer before E's existing qp=0 store before every search launch.
        edit('same worker in startup/search phase', 'J void*s(void*p){i(p,&ql);if(!--qj)d();l 0;}',
             'J void*s(void*p){if(qh){i(p,&ql);if(!--qj)d();}else{'+init_body+'}l 0;}')
        edit('remove separate initializer callback', 'J void*B(void*p){'+init_body+'l 0;}', '')
        helper = ('J void V(void){for(I n=0;n<RVW;n++)'
                  '{qr[n].i=n;qr[n].d=0;if(pthread_create(qb+n,0,s,qr+n))exit(2);}}')
        edit('same GO callback launch', launch, 'V();')
        edit('shared spawn owner', 'J char*nt(void){', helper+'J char*nt(void){')
        joins = 'for(I n=0;n<RVW;n++)if(pthread_join(qb[n],0))exit(2);'
        edit('same initialization join owner', startup+joins, 'qk=RVW;V();U();')
    if 'q' in flags:
        edit('same legal LVA local loop',
             'for(I k=1;k<7;k++){D b=d;while(b){I i=__builtin_ctzll(b),zJ=i+(i&56);b&=b-1;'
             'if(abs(t.b[zJ])==k){I z=k==1&&!(yv+16&96)?5:0;I a=Q(&t,MOVE(zJ,yv,z));'
             'if(a==SEE_INCOMPLETE)l SEE_INCOMPLETE;if(a!=-30000)l j-(a>0?a:0);}}}',
             'for(I k=1;k<7;k++)for(D b=d;b;b&=b-1){I i=__builtin_ctzll(b),zJ=i+(i&56);'
             'if(abs(t.b[zJ])==k){I a=Q(&t,MOVE(zJ,yv,k==1&&!(yv+16&96)?5:0));'
             'if(a==SEE_INCOMPLETE)l SEE_INCOMPLETE;if(a!=-30000)l j-(a>0?a:0);}}')
    if 'packed-move' in flags:
        edit('valid standard-UCI coordinate move consumer',
             'J N H(const za*b,const char*s,za*j){N a[512];char d[6];I n=c(b,a,0,b->s);'
             'for(I i=0;i<n;i++){if(s){T(a[i],d);if(strcmp(s,d))continue;}'
             'if(h(b,a[i],j))l a[i];}l 0;}',
             'J N H(const za*b,const char*s,za*j){N a[512],m=0;if(s){if(strlen(s)-4>1)l 0;'
             'm=MOVE(s[0]-97+(s[1]-49)*16,s[2]-97+(s[3]-49)*16,'
             's[4]?s[4]==110?2:s[4]==98?3:s[4]==114?4:5:0);}'
             'I n=c(b,a,0,b->s);for(I i=0;i<n;i++)'
             'if((!s||(a[i]&~8u)==m)&&h(b,a[i],j))l a[i];l 0;}')
    if 'parser' in flags:
        # Required standard TCEC commands have distinct initial characters,
        # except position/ponderhit and uci/ucinewgame. Keep exact uci and the
        # position prefix separate so optional commands remain ignored.
        for before, after, role in (
            ('!strcmp(p,"isready")', '*p==\'i\'', 'ready command'),
            ('!strcmp(p,"quit")', '*p==\'q\'', 'quit command'),
            ('!strcmp(p,"position")', '!strncmp(p,"pos",3)', 'position versus ponderhit'),
            ('!strcmp(p,"go")', '*p==\'g\'', 'GO command'),
            ('strcmp(d,"startpos")', '*d!=\'s\'', 'standard-start position'),
            ('(!strcmp(t+1,"time")||!strcmp(t+1,"inc"))',
             '(t[1]==\'t\'||t[1]==\'i\')', 'standard side clocks'),
        ):
            edit('restricted valid-TCEC '+role, before, after)
    if 'position-owner' in flags:
        edit('position guard owns join before state reuse',
             'if(!d||*d!=\'s\')l;k(&ql);', 'if(!d||*d!=\'s\')l;U();k(&ql);')
        edit('optional ponderhit has no position argument',
             'else if(!strncmp(p,"pos",3)){U();R();}', 'else if(*p==\'p\')R();')
    if 'bound' in flags:
        start = 'RVN*n/RVW' if profile_id not in PAGE_FLOOR_PROFILES else 'RVN/RVU*n/RVW*RVU'
        end = 'RVN*(n+1)/RVW' if profile_id not in PAGE_FLOOR_PROFILES else 'RVN/RVU*(n+1)/RVW*RVU'
        edit('pure invariant end bound', 'i='+start+',e='+end+';for(;i<e;i++)',
             'i='+start+';for(;i<'+end+';i++)')
    if 'mmap' in flags or 'mmap-abi' in flags:
        require(b'free(qq)' not in result, 'mapping lifetime must remain process-owned')
        if 'mmap' in flags:
            edit('named Linux anonymous mapping availability', '#define _POSIX_C_SOURCE 200809L', '#define _GNU_SOURCE')
        edit('mapping declarations', '#include<time.h>', '#include<time.h>\n#include<sys/mman.h>')
        edit('kernel-zero page-aligned TT allocation',
             'qq=aligned_alloc(4096,RVN*sizeof*qq);if(!qq)l 2;',
             ('qq=mmap(0,RVN*sizeof*qq,3,34,-1,0);if(qq==(void*)-1)l 2;' if 'mmap-abi' in flags else
              'qq=mmap(0,RVN*sizeof*qq,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(qq==MAP_FAILED)l 2;'))
        edit('kernel-initialized key and data', 'qq[i].h=qq[i].v=0;', '')
    if 'output' in flags:
        edit('one ready or UCI response emission',
             'if(!strcmp(p,"uci")){puts("uciok");fflush(stdout);}else if(*p==\'i\'){puts("readyok");fflush(stdout);}',
             'if(*p==\'i\'||!strcmp(p,"uci")){puts(*p==\'i\'?"readyok":"uciok");fflush(stdout);}')
    if 'material' in flags:
        edit('same insufficient-material classification',
             'I y(const za*p){I d=0;for(I q=0;q<128;q++)if(!(q&0x88)){I a=abs(p->b[q]);'
             'if(a==2){if(d)l 0;d=-1;}else if(a==3){if(d<0)l 0;d|=1<<((q+(q>>4))&1);'
             'if(d==3)l 0;}else if(a&&a<6)l 0;}l 1;}',
             'I y(const za*p){I d=0,n=0;for(I q=0;q<128;q++)if(!(q&0x88)){I a=abs(p->b[q]);'
             'if(a==2)n++;else if(a==3)d|=1<<((q+(q>>4))&1);else if(a&&a<6)l 0;}'
             'l n?n==1&&!d:d!=3;}')
    if 'rights' in flags:
        edit('same rights on legal mailbox squares',
             'J I O(I q){l q==4?3:q==116?12:q==0?2:q==7?1:q==112?8:q==119?4:0;}',
             'J I O(I q){I f=q%112;l (f==4?3:f==0?2:f==7)<<(q/112*2);}')
    if 'rights-bits' in flags:
        edit('same legal-square rights bitfield lookup',
             'J I O(I q){I f=q%112;l (f==4?3:f==0?2:f==7)<<(q/112*2);}',
             'J I O(I q){l q/16%7?0:(2109442>>(q&7)*3&7)<<(q/112*2);}')
    if 'numeric' in flags:
        edit('88 numeric spelling', '0x88', '136', count=result.count(b'0x88'))
        edit('unsigned splitmix constants', 'UL;', ';', count=3)
        edit('same bitboard cast precedence', 'l ((D)1)<<', 'l(D)1<<')
    if 'moves' in flags or 'moves-unsigned' in flags:
        edit('move target mask on closed legal 0x88 domain', '#define TO(m) (((m)>>7)&127)', '#define TO(m) FROM((m)>>7)')
        edit('same promotion shift precedence', '#define PROMO(m) (((m)>>14)&7)', '#define PROMO(m) ((m)>>14&7)')
        edit('nonnegative bounded move intermediates',
             '#define MOVE(f,t,p) ((N)(f)|((N)(t)<<7)|((N)(p)<<14))',
             ('#define MOVE(f,t,p) ((f)|((t)<<7)|((p)<<14))' if 'moves' in flags else
              '#define MOVE(f,t,p) ((N)((f)|((t)<<7)|((p)<<14)))'))
    if 'promo' in flags:
        edit('closed 17-bit move promotion domain', '#define PROMO(m) ((m)>>14&7)', '#define PROMO(m) ((m)>>14)')
    for bit, literal in enumerate(('0x9e3779b97f4a7c15', '0xbf58476d1ce4e5b9', '0x94d049bb133111eb')):
        if str(bit)+'decimal' in flags:
            edit('same unsigned 64-bit hash constant '+str(bit), literal, str(int(literal, 16))+'UL')
    for name in 'abcdfqtz':
        if 'main-'+name in flags:
            main = result[result.index(b'I main('):].decode()
            # Skip entire quoted tokens, so the dispatch character 'p' stays
            # the protocol constant rather than the pointer's new spelling.
            token = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_][A-Za-z_0-9]*'
            renamed = re.sub(token, lambda match: name if match.group() == 'p' else match.group(), main)
            edit('main local pointer spelling '+name, main, renamed)
    if 'compact' in flags:
        edit('null pointer token', 'strtok(NULL,', 'strtok(0,')
        while b'\n\n' in result:
            edit('empty source lines', '\n\n', '\n', count=result.count(b'\n\n'))
        edit('function separator whitespace', '}\nJ', '}J', count=result.count(b'}\nJ'))
        if result.endswith(b'\n'):
            # No preprocessor line is at EOF; the last token is main's brace.
            require(result.endswith(b'}\n'), 'closed final C function required')
            edit('final source newline', result[-40:].decode(), result[-40:-1].decode())
    if 'arity' in flags:
        # These are internal zero-argument definitions in one closed C11 TU.
        # Every admitted call supplies zero arguments, and no callback/pointer
        # consumer uses these function types. void* pthread entries unchanged.
        edit('closed zero-argument definitions', '(void)', '()', count=result.count(b'(void)'))
    if 'compound' in flags:
        edit('exclusive complete TT object initialization',
             '{qq[i].h=qq[i].v=0;atomic_flag_clear_explicit(&qq[i].a,memory_order_relaxed);}',
             'qq[i]=(zb){ATOMIC_FLAG_INIT};')
    if 'loop' in flags:
        # V is a function in the source; X is only the local P move array.
        # Rename that array first, then reuse its released preprocessor token.
        edit('local P array consumers', 'X[', 'qX[', count=6)
        edit('local P array generator', 'c(p,X,0,p->s)', 'c(p,qX,0,p->s)')
        edit('loop keyword alias', 'for(', 'X(', count=result.count(b'for('))
        edit('loop keyword definition', '#define I int\n', '#define X for\n#define I int\n')
    keywords = set(flags) & {'if', 'void', 'const'}
    if keywords:
        require(len(keywords) == 1 and not re.search(rb'\bzW\b', result), 'one free scoped keyword alias required')
        edit('P prefix count spelling', 'I V=0,W=qh+n;', 'I V=0,zW=qh+n;')
        edit('P prefix count consumers', 'i=W-3;i>=0&&i>=W-1-p->n', 'i=zW-3;i>=0&&i>=zW-1-p->n')
        keyword = next(iter(keywords))
        before = keyword+'(' if keyword == 'if' else keyword
        after = 'W(' if keyword == 'if' else 'W'
        edit('same keyword alias '+keyword, before, after, count=result.count(before.encode()))
        edit('keyword definition '+keyword, '#define I int\n', '#define W '+keyword+'\n#define I int\n')
    definitions = ''
    if 'load' in flags:
        edit('same explicit relaxed cancellation read', 'atomic_load_explicit(&qp,memory_order_relaxed)', 'qv', count=6)
        definitions += '#define qv atomic_load_explicit(&qp,memory_order_relaxed)\n'
    if 'store' in flags:
        edit('same cancellation store', 'atomic_store(&qp,1)', 'qw', count=4)
        definitions += '#define qw atomic_store(&qp,1)\n'
    if definitions:
        edit('local source aliases', '#define I int\n', definitions+'#define I int\n')
    if 'names' in flags:
        for before, after in (('RVW','qW'),('RVN','qN'),('RVU','qU')):
            matches = list(re.finditer(r'\b'+before+r'\b', result.decode()))
            if matches:
                require(not re.search(rb'\b'+after.encode()+rb'\b',result), 'resource name collision')
                edit('resource spelling '+before, before, after, count=len(matches))
    if 'lf' in flags:
        require(result.endswith(b'}'), 'closed source terminator required')
        edit('standard translation final newline', result[-40:].decode(), result[-40:].decode()+'\n')
    proof = dict(schema=SCHEMA, variant=variant, profile_id=profile_id, entry_cleanup=entry_cleanup,
                 input=pin(source), output=pin(result), stages=stages, full_inverse=True,
                 unchanged='full NBRQ/legal-LVA/singular/search/learners/repetition/50move/cancellation',
                 startup_phase='qh=0 until all initialization joins; qh>=1 before UCI and thereafter',
                 parser_domain=('standard valid TCEC UCI plus optional commands ignored; unsupported token aliases may differ'
                                if 'parser' in flags else 'unchanged original exact command/move tokens'),
                 runtime_qualified=False)
    if 'mmap-abi' in flags:
        proof['target_abi_probe'] = ABI_PROBE
    require(restore_source(result, proof) == source, 'B profile complete inverse differs')
    return result, proof


def _gaps(before, after, rows):
    old = new = 0
    result = []
    for row in rows:
        gap = before[old:row['at']]
        require(gap == after[new:row['target']], 'B protected complement differs')
        result.append(pin(gap))
        old, new = row['at']+len(row['before']), row['target']+len(row['after'])
    require(before[old:] == after[new:], 'B protected suffix differs')
    return [*result, pin(before[old:])]


def restore_source(candidate, proof):
    require(type(candidate) is bytes and proof.get('schema') == SCHEMA and pin(candidate) == proof.get('output'),
            'exact B profile candidate required')
    result = candidate
    for stage in reversed(proof['stages']):
        require(pin(result) == stage['output'], 'B inverse stage output differs')
        for row in reversed(stage['edits']):
            at, before, after = row['target'], row['before'].encode(), row['after'].encode()
            require(result[at:at+len(after)] == after, 'B inverse edited interval differs')
            result = result[:at]+before+result[at+len(after):]
        require(pin(result) == stage['input'], 'B inverse stage input differs')
    require(pin(result) == proof['input'] and
            INPUTS.get((proof['profile_id'], proof['entry_cleanup'])) ==
            (len(result), sha256(result).hexdigest()), 'B inverse named producer input differs')
    return result
