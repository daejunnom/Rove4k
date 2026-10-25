"""One exact E composition; no alternative edits or dynamic admission."""
import hashlib

def sha(data):return hashlib.sha256(data).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)

EDITS=(
(b'w->nodes=0;w->depth=0;w->score=0;',b'w->nodes=0;w->depth=0;w->score=0;w->best=0;'),
(b'static int pending,ready,quitting;',b'static int pending=WORKERS,quitting;'),
(b'''static Move first(const Board *b){Move list[MOVES];Board c;int n=gen(b,list);for(int i=0;i<n;i++)if(make(b,list[i],&c))return list[i];return 0;}
static Move parse(const Board *b,const char *s){
    Move list[MOVES];Board c;char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){text(list[i],name);if(!strcmp(s,name)&&make(b,list[i],&c))return list[i];}return 0;
}''',b'''static Move parse(const Board *b,const char *s,Board *c){
    Move list[MOVES];char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){
        if(s){text(list[i],name);if(strcmp(s,name))continue;}
        if(make(b,list[i],c))return list[i];
    }return 0;
}'''),
(b'Worker *w=p;unsigned seen=0;pthread_mutex_lock(&mutex);ready++;pthread_cond_broadcast(&finished);',b'Worker *w=p;unsigned seen=0;pthread_mutex_lock(&mutex);--pending;pthread_cond_broadcast(&finished);'),
(b'Move m=parse(&b,t);if(!m||n==HISTORY||!make(&b,m,&c))return;b=c;keys[n++]=b.h;',b'if(n==HISTORY||!parse(&b,t,&c))return;b=c;keys[n++]=b.h;'),
(b'''fallback=first(&position);atomic_store(&stopped,0);
    for(int i=0;i<WORKERS;i++){workers[i].depth=workers[i].score=0;workers[i].best=0;workers[i].nodes=0;}''',b'Board c;fallback=parse(&position,0,&c);atomic_store(&stopped,0);'),
(b'pthread_mutex_lock(&mutex);while(ready<WORKERS)pthread_cond_wait(&finished,&mutex);pthread_mutex_unlock(&mutex);',b'wait();'),
(b'wait();Move m=parse(&position,line+6);printf("order %d\\n",m?tiny_order(&position,m):INT_MIN);',b'wait();Board c;Move m=parse(&position,line+6,&c);printf("order %d\\n",m?tiny_order(&position,m):INT_MIN);'),
)

def readable(control):
    data=control
    for old,new in EDITS:
        need(data.count(old)==1,'literal composition fragment count drift')
        data=data.replace(old,new)
    marker=b'void think(Worker *w,const Board *p)'
    need(control.split(marker)[0]==data.split(marker)[0],'E model/Board/search prefix changed')
    need(b'tiny_order(&position,m)'in data and b'tiny_order(&c,m)'not in data,'E order original board lost')
    return data
