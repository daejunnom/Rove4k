"""One explicit, bounded shipping UCI policy; DEV behavior is unchanged."""
import hashlib

CONTROL_SHA256 = '109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504'
POLICY = {
    'uci': 'uciok only; id is optional and omitted',
    'stop': 'consume without cancellation',
    'ucinewgame': 'consume without waiting or clearing the transposition table',
    'bare_go_ms': 1000,
    'infinite': 'unknown shipping token, so clockless go uses the same 1000 ms default',
    'clocked_go': 'unchanged own-side clock/30 + capped increment*3/4, capped to clock/5; minimum 1 ms, maximum 86400000 ms',
    'internal_fences': 'next go, position, quit and EOF cancel and wait before reuse/free',
    'development': 'original id, stop, newgame and go-infinite behavior retained',
}


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('unexpected readable control: ' + before[:70])
    return text.replace(before, after, 1)


def transform(data):
    if hashlib.sha256(data).hexdigest() != CONTROL_SHA256:
        raise ValueError('unknown readable A control')
    text = data.decode('utf-8')
    text = replace_once(text, '    wait();deadline=UINT64_MAX;\n', '''    wait();
#if DEV
    deadline=UINT64_MAX;
#endif
''')
    text = replace_once(text,
        '    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;char *save;\n',
        '''#if DEV
    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;char *save;
#else
    uint64_t clock=0,inc=0,budget=0;int present=0;char *save;
#endif
''')
    text = replace_once(text,
        '        else if(!strcmp(t,"infinite"))infinite=1;\n#if DEV\n',
        '#if DEV\n        else if(!strcmp(t,"infinite"))infinite=1;\n')
    original = '    if(!infinite){if(!budget&&present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}if(budget)deadline=now()+(budget>86400000?86400000:budget);}\n'
    shipping = '''    if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}
    else budget=1000;
    deadline=now()+(budget>86400000?86400000:budget);
'''
    text = replace_once(text, original, '#if DEV\n' + original + '#else\n' + shipping + '#endif\n')
    text = replace_once(text,
        '        if(!strcmp(line,"uci")){puts("id name Rove4k A\\nuciok");fflush(stdout);}\n',
        '''        if(!strcmp(line,"uci")){
#if DEV
            puts("id name Rove4k A\\nuciok");
#else
            puts("uciok");
#endif
            fflush(stdout);
        }
''')
    text = replace_once(text,
        '        else if(!strcmp(line,"stop"))wait();\n        else if(!strcmp(line,"ucinewgame")){wait();clear();}\n',
        '''#if DEV
        else if(!strcmp(line,"stop"))wait();
        else if(!strcmp(line,"ucinewgame")){wait();clear();}
#endif
''')
    # These lines are the physical lifetime boundaries, deliberately unchanged.
    for fence in ('static void wait(void){atomic_store(&stopped,1);',
                  '    wait();\n#if DEV\n    deadline=UINT64_MAX;',
                  'else if(!strncmp(line,"position ",9)){wait();set_position(line+9);}',
                  '    wait();\nshutdown:',
                  'for(int i=0;i<created;i++)if(pthread_join(threads[i],NULL))status=2;',
                  'if(!table)return 2;clear();start(&position);'):
        if text.count(fence) != 1:
            raise ValueError('lifetime/startup fence missing: ' + fence)
    return text.encode('utf-8'), dict(POLICY)
