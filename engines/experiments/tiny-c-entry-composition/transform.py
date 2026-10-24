"""Exactly seven literal sites implementing one C query/reset/startup composition."""
import hashlib

CONTROL_SHA256='1f0f18ffee91ecddea3cb31e7553e1d1415e25b3f759cdec4e0f375fcd0b2298'
CANDIDATE_SHA256='15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b'
REPLACEMENTS=[('w->nodes=0;w->depth=0;w->score=0;', 'w->nodes=0;w->depth=0;w->score=0;w->best=0;'), ('static int pending,ready,quitting;', 'static int pending=WORKERS,quitting;'), ('static Move first(const Board *b){Move list[MOVES];Board c;int n=gen(b,list);for(int i=0;i<n;i++)if(make(b,list[i],&c))return list[i];return 0;}\nstatic Move parse(const Board *b,const char *s){\n    Move list[MOVES];Board c;char name[6];int n=gen(b,list);\n    for(int i=0;i<n;i++){text(list[i],name);if(!strcmp(s,name)&&make(b,list[i],&c))return list[i];}return 0;\n}', 'static Move parse(const Board *b,const char *s,Board *c){\n    Move list[MOVES];char name[6];int n=gen(b,list);\n    for(int i=0;i<n;i++){\n        if(s){text(list[i],name);if(strcmp(s,name))continue;}\n        if(make(b,list[i],c))return list[i];\n    }return 0;\n}'), ('pthread_mutex_lock(&mutex);ready++;pthread_cond_broadcast(&finished);', 'pthread_mutex_lock(&mutex);--pending;pthread_cond_broadcast(&finished);'), ('Move m=parse(&b,t);if(!m||n==HISTORY||!make(&b,m,&c))return;b=c;keys[n++]=b.h;', 'if(n==HISTORY||!parse(&b,t,&c))return;b=c;keys[n++]=b.h;'), ('fallback=first(&position);atomic_store(&stopped,0);\n    for(int i=0;i<WORKERS;i++){workers[i].depth=workers[i].score=0;workers[i].best=0;workers[i].nodes=0;}', 'Board c;fallback=parse(&position,0,&c);atomic_store(&stopped,0);'), ('pthread_mutex_lock(&mutex);while(ready<WORKERS)pthread_cond_wait(&finished,&mutex);pthread_mutex_unlock(&mutex);\n    for(;;){\n        int status=read_line(line);', 'wait();\n    for(;;){\n        int status=read_line(line);')]

def transform(source):
    if hashlib.sha256(source).hexdigest()!=CONTROL_SHA256:raise ValueError('unknown C5723 readable control')
    text=source.decode()
    for before,after in REPLACEMENTS:
        if text.count(before)!=1:raise ValueError('fixed composition site changed')
        text=text.replace(before,after)
    result=text.encode()
    inverse=text
    for before,after in reversed(REPLACEMENTS):
        if inverse.count(after)!=1:raise ValueError('fixed inverse site changed')
        inverse=inverse.replace(after,before)
    if inverse.encode()!=source or hashlib.sha256(result).hexdigest()!=CANDIDATE_SHA256:
        raise ValueError('unexpected change outside seven sites')
    prefix=source[:source.index(b'void think(')]
    if prefix!=result[:result.index(b'void think(')]:raise ValueError('C core prefix changed')
    return result,{'control_sha256':CONTROL_SHA256,'candidate_sha256':CANDIDATE_SHA256,
        'replacement_sites':7,'core_prefix_bytes':len(prefix),'core_prefix_sha256':hashlib.sha256(prefix).hexdigest(),
        'core_prefix_byte_identical':True,'exact_inverse':True,'PP_compile_engine_qualification_executed':False}
