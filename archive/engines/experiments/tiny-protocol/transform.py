"""Independent MIT protocol co-design; no external engine source is included.

The readable frozen core is transformed, not its existing generated artifacts.
Move geometry remains the production generator's authority. Search, board, TT,
startup and completion code are not rewritten by this experiment.
"""
from pathlib import Path

HERE=Path(__file__).resolve().parent


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('fixed protocol source changed: '+old[:90])
    return text.replace(old,new)


def function(text,name):
    import re
    # Only the pinned readable functions are passed here. Scan quotes/comments
    # so JSON/string braces cannot change the outer function boundary.
    match=re.search(r'(?m)^(?:static )?[^\n;]*\b'+re.escape(name)+r'\([^\n]*\)\{',text)
    if not match:raise ValueError('fixed function missing: '+name)
    begin=match.start();i=text.index('{',match.start());depth=1;i+=1
    while depth:
        if text.startswith('//',i):
            end=text.find('\n',i);i=len(text) if end<0 else end+1;continue
        if text.startswith('/*',i):i=text.index('*/',i)+2;continue
        if text[i] in ('"',"'"):
            quote=text[i];i+=1
            while text[i]!=quote:
                i+=2 if text[i]=='\\' else 1
            i+=1;continue
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return begin,i,text[begin:i]


def replace(text,name,new):
    begin,end,_=function(text,name);return text[:begin]+new+text[end:]


def transform(source,*,family):
    if family not in ('A','D'):raise ValueError('only frozen tiny A/D runtime shapes are admitted')
    text=source.decode().replace('\r\n','\n')
    if '\r' in text:raise ValueError('lone CR in readable source')
    text=replace(text,'number','')
    text=replace(text,'parse',(HERE/'span.c.in').read_text())
    text=replace(text,'set_position',(HERE/'position.c.in').read_text())
    begin,end,go=function(text,'go')
    go=go.replace(';char *save;',';')
    start=go.index('    for(char *t=strtok_r(');stop=go.index('    if(!infinite)',start)
    go=go[:start]+(HERE/'go-loop.c.in').read_text()+go[stop:]
    text=text[:begin]+go+text[end:]
    # Existing optional DEV commands keep their separate full-line parser.
    text=once(text,'number(line+6)','number((Span){line+6,(unsigned)strlen(line+6)})')
    begin,end,main=function(text,'main')
    start=main.index('        size_t n=strlen(line);');stop=main.index('\n#if DEV\n        else if',start)
    old_dispatch=main[start:stop]
    emission='puts("id name Rove4k A\\nuciok");fflush(stdout);' if family=='A' else 'output("id name Rove4k D syscall\\nuciok\\n");'
    ready='puts("readyok");fflush(stdout);' if family=='A' else 'output("readyok\\n");'
    dispatch='''        const char *cursor=line;Span command=scan(&cursor);
        if(word(command,"position")){wait();set_position((char *)cursor);}
        else if(word(command,"go"))go((char *)cursor);
        else if(scan(&cursor).n)continue;
        else if(word(command,"uci")){EMIT}
        else if(word(command,"isready")){READY}
        else if(word(command,"quit"))break;
        else if(word(command,"stop"))wait();
        else if(word(command,"ucinewgame")){wait();clear();}'''.replace('EMIT',emission).replace('READY',ready)
    # The following DEV `else if` tail belongs to the old full-line chain.
    # Keep that complete chain in DEV; only shipping uses the span dispatcher.
    main=main[:start]+'#if !DEV\n'+dispatch+'\n#else\n'+old_dispatch+main[stop:]
    # Close the new outer DEV branch after the original optional-command tail.
    at=main.index('\n#endif\n    }',start)
    main=main[:at]+main[at:].replace('\n#endif\n    }','\n#endif\n#endif\n    }',1)
    text=text[:begin]+main+text[end:]
    if family=='D':
        begin=text.index('size_t strlen(');stop=text.index('\n#if DEV\nint tiny_errno',begin)
        text=text[:begin]+'#if DEV\n'+text[begin:stop]+'\n#endif'+text[stop:]
        text=once(text,'static void output(const char *s){size_t n=strlen(s);',
                  'static void output(const char *s){size_t n=0;while(s[n])n++;')
        text=once(text,'size_t n=strlen(move);memcpy(s,move,n);','size_t n=4+!!PROMO(best);memcpy(s,move,n);')
    return text.encode(),{
        'family':family,'move_application':'exact 4/5-byte decode, production gen membership, one make returns child',
        'protocol_changes':['ASCII whitespace span scan','no-argument commands with extra tokens ignored',
                            'nonnumeric missing value is reprocessed as a key/unknown token','empty moves list accepted'],
        'unchanged':['full-line NUL/long-line drain','transactional replay commit','clock budget formula',
                     'startup pool','wait/result completion epochs','board/search/TT algorithms'],
        'DEV':'keeps old full-line dispatch; startpos/FEN replay and go use shared new span helpers',
    }
