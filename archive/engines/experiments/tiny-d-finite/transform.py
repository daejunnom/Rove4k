"""One explicit shipping-only finite minimal-UCI policy on exact maintained D."""
import hashlib

CONTROL = 'ec9ba6fce84fac501a25a3317a326bc62c9e420002a81303475230702ae1c773'
POLICY = {
    'uci': 'uciok only; omit optional identification line',
    'stop_ucinewgame': 'consume as unsupported commands; no cancellation, wait or TT clear',
    'bare_or_no_own_clock_ms': 1000,
    'infinite': 'unsupported token; same finite default or admitted own-side clock budget',
    'clock': 'unchanged own clock/30 + capped inc*3/4, capped clock/5, minimum1ms, maximum86400000ms',
    'internal_fences': 'nextgo, position, quit and EOF still cancel and wait for completed epoch after result output',
    'DEV': 'original control behavior and declaration order preserved',
}


def once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('unexpected control fragment: ' + before[:80])
    return source.replace(before, after, 1)


def transform(data):
    if hashlib.sha256(data).hexdigest() != CONTROL:
        raise ValueError('unknown maintained D runtime')
    source = data.decode()
    source = once(source, '    wait();deadline=UINT64_MAX;\n', '#if DEV\n    wait();deadline=UINT64_MAX;\n#else\n    wait();\n#endif\n')
    source = once(source, '    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;\n',
                  '#if DEV\n    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;\n#else\n    uint64_t clock=0,inc=0,budget=0;int present=0;\n#endif\n')
    source = once(source, '        else if(word(token,"infinite"))infinite=1;\n#if DEV\n',
                  '#if DEV\n        else if(word(token,"infinite"))infinite=1;\n')
    old = '    if(!infinite){if(!budget&&present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}if(budget)deadline=now()+(budget>86400000?86400000:budget);}\n'
    new = '    if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}else budget=1000;\n    deadline=now()+(budget>86400000?86400000:budget);\n'
    source = once(source, old, '#if DEV\n'+old+'#else\n'+new+'#endif\n')
    source = once(source, '        else if(word(command,"uci")){output("id name Rove4k D syscall\\nuciok\\n");}\n',
                  '        else if(word(command,"uci")){output("uciok\\n");}\n')
    source = once(source, '        else if(word(command,"stop"))wait();\n        else if(word(command,"ucinewgame")){wait();clear();}\n', '')
    # Source complement outside the two declared functions must remain exact.
    def complement(text):
        begin = text.index('static void go(char *s){')
        end = text.index('#if DEV\nstatic uint64_t perft', begin)
        main = text.index('int main(void){', end)
        return text[:begin] + '<GO>' + text[end:main] + '<MAIN>'
    if complement(source) != complement(data.decode()):
        raise ValueError('source changed outside go/main')
    return source.encode(), dict(POLICY)
