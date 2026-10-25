"""Frozen-source shared walk/picker prototype; never edits canonical tiny A.

This changes ordering policy. Every pseudo move has a stable generation ordinal
and an independent visited bit, so descendant learning cannot skip or duplicate
unsearched moves when rescoring the remaining candidates. Public gen and attack
queries still use the same geometric walker as the search picker.
"""
import hashlib

BASELINE_SHA256='109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504'


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('fixed streaming source changed: '+old[:80])
    return text.replace(old,new)


def function(text,needle):
    start=text.index(needle);open_=text.index('{',start);depth=1;i=open_+1
    # Only called on the pinned, comment/string-brace-free small functions.
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return start,i,text[start:i]


ADD='''static void add(const Board *p,Pick *pick,int *n,int from,int to,int pawn){
    int promotion=pawn&&((to>>4)==0||(to>>4)==7);
    for(int z=promotion?2:0;z<=(promotion?5:0);z++){
        if(*n>=MOVES)abort();
        Move m=MOVE(from,to,z);int ordinal=(*n)++;
        if(pick->list)pick->list[ordinal]=m;
        else if(!(pick->seen[ordinal>>6]>> (ordinal&63)&1)){
            Worker *w=pick->w;
            int score=m==pick->tt?1000000:capture(p,m)?500000+abs(value(p->b[to],to))*16-abs(value(p->b[from],from)):
                w->history[from][to]+w->continuation[pick->prior][piece_index(p->b[from])]+(int)((m*37u+w->id*19u)%17);
            if(z)score+=400000+z*1000;
            if(score>pick->score)pick->score=score,pick->move=m,pick->index=ordinal;
        }
    }
}'''


def transform(source):
    if hashlib.sha256(source).hexdigest()!=BASELINE_SHA256:
        raise ValueError('shared walk prototype requires exact frozen readable search winner')
    text=source.decode()
    text=once(text,'} Worker;','''} Worker;
typedef struct{Move *list,move,tt;Worker *w;int prior,score,index;uint64_t seen[MOVES/64];} Pick;''')
    helpers=[]
    for name in ('static int piece_index(', 'static int capture('):
        begin,end,body=function(text,name);helpers.append(body);text=text[:begin]+text[end:]
    begin,end,_=function(text,'static void add(')
    text=text[:begin]+'\n'.join(helpers)+'\n'+ADD+text[end:]
    text=once(text,'static int walk(const Board *,Move *,int,int);','static int walk(const Board *,Pick *,int,int);')
    text=once(text,'static int walk(const Board *p,Move *moves,int sq,int s){','static int walk(const Board *p,Pick *moves,int sq,int s){')
    begin,end,walk=function(text,'static int walk(const Board *p,')
    walk=walk.replace('add(moves,&n,','add(p,moves,&n,')
    walk=once(walk,'    for(int from=0;from<128;from++){',
              '    for(int from=0;from<128;from++){\n        if(moves&&moves->w&&atomic_load_explicit(&stopped,memory_order_relaxed))break;')
    text=text[:begin]+walk+text[end:]
    text=once(text,'int gen(const Board *p,Move *moves){return walk(p,moves,0,p->s);}',
              'int gen(const Board *p,Move *moves){Pick pick={.list=moves};return walk(p,&pick,0,p->s);}')
    begin,end,search=function(text,'static int search(')
    search=once(search,'    Move moves[MOVES],bestmove=0;\n    int scores[MOVES],count=gen(p,moves),legal=0,old=alpha,best=-MATE;',
                '    Move bestmove=0;\n    int legal=0,old=alpha,best=-MATE,terminal=draw||ply==PLY-1;')
    start=search.index('    if(draw||ply==PLY-1){');stop=search.index('    uint64_t key=',start)
    search=search[:start]+search[stop:]
    search=once(search,'data=probe(key,0);','data=terminal?0:probe(key,0);')
    # The original TT prelude stays; terminal nodes have no TT bound and reach
    # the same legal witness/mate precedence through the shared picker below.
    start=search.index('    for(int i=0;i<count;i++){');stop=search.index('        Board q;if(!make(p,m,&q))continue;',start)
    search=search[:start]+'''    Pick pick={.w=w,.prior=prior,.tt=tt};
    for(;;){
        if(atomic_load_explicit(&stopped,memory_order_relaxed)||now()>=deadline){atomic_store(&stopped,1);return 0;}
        pick.move=0;pick.score=INT_MIN;walk(p,&pick,0,p->s);
        if(atomic_load_explicit(&stopped,memory_order_relaxed))return 0;
        Move m=pick.move;if(!m)break;
        pick.seen[pick.index>>6]|=UINT64_C(1)<<(pick.index&63);
'''+search[stop:]
    search=once(search,'        ++legal;',
                '        if(terminal){if(!draw){COUNT(w,ply_aborts);atomic_store(&stopped,1);}return 0;}\n        ++legal;')
    text=text[:begin]+search+text[end:]
    return text.encode(),{
        'policy_change':'stable generation ties and live remaining-move scores; original score categories/learners retained',
        'coverage':'per-node immutable generation ordinals+512-bit seen set; no rank threshold vulnerable to learning changes',
        'timing_change':'deadline checked at each picker request and cancellation checked while scanning pieces',
        'risk':'repeated full generation/value scoring can be substantially slower; no fair NPS result',
        'shared':'public generation, attack query and search move picking use the existing walk/add geometry',
        'not_changed':'PVS/QS/TT scale/fullkey locking/history/continuation/correction/LMR/SMP/result completion boundary',
    }
