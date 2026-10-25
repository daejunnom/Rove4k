"""The single qualified minimal UCI policy, on four literal source controls."""
import hashlib

READABLE_SHA256 = {
    'B': '8130f0cde0c30679c84e6ec8c5bb6967e9d9b8ed19223c3856a05126cee4fa7c',
    'C': '8d951ec4e451bccf89064f30aaead77e49410017d825536d65c9c7e39a4cdb96',
    'E': '09e67b5a2b4b17f04f08eebeb1b70421eb47eb235f7027099d1ff8ad5173b5e1',
    'F': 'ccc7a4b232cebdad7f00c5fe6b0dbff718b51c895db0c9996467679841af59a3',
}
ID_NAMES = {'B': 'Rove4k B', 'C': 'Rove4k C', 'E': 'Rove4k E', 'F': 'Rove4k F full-depth MTD'}
POLICY = {
    'uci': 'uciok only', 'stop': 'consume without cancellation',
    'ucinewgame': 'consume without waiting or TT clear',
    'bare_go_ms': 1000,
    'infinite': 'ignored shipping token; clockless go has the same finite default',
    'clocked_go': 'existing own-side calculation, minimum 1ms, maximum 86400000ms',
    'internal_fences': 'go/position/quit/EOF retain cancellation and actual completion wait',
    'DEV': 'unchanged strong control, identification and diagnostics',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('unknown UCI source shape: ' + before[:90])
    return text.replace(before, after, 1)


def region(text, signature):
    """Locate one complete C function, ignoring braces in comments/literals."""
    if text.count(signature) != 1:
        raise ValueError('unknown function shape: ' + signature)
    begin = text.index(signature)
    pos = begin + len(signature)
    depth, state = 1, 'code'
    while pos < len(text):
        ch = text[pos]
        nxt = text[pos:pos + 2]
        if state in ('string', 'char'):
            if ch == '\\':
                pos += 2
                continue
            if ch == ('"' if state == 'string' else "'"):
                state = 'code'
        elif state == 'line':
            if ch == '\n':
                state = 'code'
        elif state == 'block':
            if nxt == '*/':
                state = 'code'
                pos += 2
                continue
        elif nxt in ('//', '/*'):
            state = 'line' if nxt == '//' else 'block'
            pos += 2
            continue
        elif ch in ('"', "'"):
            state = 'string' if ch == '"' else 'char'
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return begin, pos + 1
        pos += 1
    raise ValueError('unterminated function: ' + signature)


def protected_bytes(data):
    text = data.decode('utf-8')
    spans = sorted(region(text, signature) for signature in ('static void go(char *s){', 'int main(void){'))
    parts, start = [], 0
    for begin, end in spans:
        parts.extend((text[start:begin], '/* UCI policy function */'))
        start = end
    parts.append(text[start:])
    return ''.join(parts).encode()


def transform(data, family):
    if family not in READABLE_SHA256 or sha(data) != READABLE_SHA256[family]:
        raise ValueError('unknown readable family control')
    text = data.decode('utf-8')
    text = replace_once(text, '    wait();deadline=UINT64_MAX;\n', '''    wait();
#if DEV
    deadline=UINT64_MAX;
#endif
''')
    original = '    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;char *save;\n'
    text = replace_once(text, original, '#if DEV\n' + original + '''#else
    uint64_t clock=0,inc=0,budget=0;int present=0;char *save;
#endif
''')
    text = replace_once(text, '        else if(!strcmp(t,"infinite"))infinite=1;\n#if DEV\n',
                        '#if DEV\n        else if(!strcmp(t,"infinite"))infinite=1;\n')
    original = '    if(!infinite){if(!budget&&present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}if(budget)deadline=now()+(budget>86400000?86400000:budget);}\n'
    shipping = '''    if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}
    else budget=1000;
    deadline=now()+(budget>86400000?86400000:budget);
'''
    text = replace_once(text, original, '#if DEV\n' + original + '#else\n' + shipping + '#endif\n')
    original = '        if(!strcmp(line,"uci")){puts("id name ' + ID_NAMES[family] + '\\nuciok");fflush(stdout);}\n'
    text = replace_once(text, original, '''        if(!strcmp(line,"uci")){
#if DEV
            puts("id name ''' + ID_NAMES[family] + '''\\nuciok");
#else
            puts("uciok");
#endif
            fflush(stdout);
        }
''')
    original = '        else if(!strcmp(line,"stop"))wait();\n        else if(!strcmp(line,"ucinewgame")){wait();clear();}\n'
    text = replace_once(text, original, '#if DEV\n' + original + '#endif\n')
    for fence in ('static void wait(void){atomic_store(&stopped,1);',
                  '    wait();\n#if DEV\n    deadline=UINT64_MAX;',
                  'else if(!strncmp(line,"position ",9)){wait();set_position(line+9);}',
                  '    wait();\nshutdown:',
                  'for(int i=0;i<created;i++)if(pthread_join(threads[i],NULL))status=2;',
                  'if(!table)return 2;clear();start(&position);'):
        if text.count(fence) != 1:
            raise ValueError('lifetime/startup boundary changed: ' + fence)
    output = text.encode()
    before = protected_bytes(data)
    if protected_bytes(output) != before:
        raise ValueError('code outside go/main changed')
    return output, {'policy': dict(POLICY), 'family': family, 'input_sha256': sha(data),
                    'output_sha256': sha(output), 'protected_bytes': len(before),
                    'protected_sha256': sha(before), 'all_bytes_outside_go_main_identical': True}
