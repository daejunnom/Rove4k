"""One fixed-stage fused producer, deliberately changing ordering/LMR policy."""
import hashlib
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
EXPECTED='109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504'


def function(text,name):
    found=re.search(r'(?m)^(?:static )?[^\n;]*\b'+re.escape(name)+r'\([^\n]*\)\{',text)
    if not found:raise ValueError('frozen function missing: '+name)
    begin=found.start();i=text.index('{',begin)+1;depth=1
    while depth:
        if text.startswith('//',i):i=text.index('\n',i)+1;continue
        if text.startswith('/*',i):i=text.index('*/',i)+2;continue
        if text[i] in ('"',"'"):
            quote=text[i];i+=1
            while text[i]!=quote:i+=2 if text[i]=='\\' else 1
            i+=1;continue
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return begin,i,text[begin:i]


def replace(text,name,body):
    a,b,_=function(text,name);return text[:a]+body+text[b:]


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('frozen consumer changed: '+old[:90])
    return text.replace(old,new)


def transform(source):
    if hashlib.sha256(source).hexdigest()!=EXPECTED:raise ValueError('unknown frozen Tiny A')
    text=source.decode()
    text=once(text,'static int walk(const Board *,Move *,int,int);\nint attacked(const Board *p,int sq,int side){return walk(p,0,sq,side);}',(HERE/'types.c.in').read_text())
    a,b,dead=function(text,'dead');text=text[:a]+'#if DEV\n'+dead+'\n#endif'+text[b:]
    text=replace(text,'make',(HERE/'transition.c.in').read_text())
    text=replace(text,'add','')
    text=replace(text,'gen','')
    text=replace(text,'walk',(HERE/'walk.c.in').read_text())
    text=replace(text,'capture','')
    text=replace(text,'search',(HERE/'search.c.in').read_text())
    text=replace(text,'parse','')
    text=replace(text,'first',(HERE/'queries.c.in').read_text())
    text=once(text,'        Move m=parse(&b,t);if(!m||n==HISTORY||!make(&b,m,&c))return;b=c;keys[n++]=b.h;',
                   '        if(n==HISTORY||!parse(&b,t,&c))return;b=c;keys[n++]=b.h;')
    return text.encode(),{
        'kind':'explicit fixed-stage ordering and LMR placement policy change',
        'stages':['TT','best tactical','remaining tacticals in geometry order','best quiet','remaining quiets in geometry order'],
        'snapshot':'best prefixes frozen in survey; descendant learning never reranks unvisited moves',
        'source':'one Fact producer and offer for first/witness/input-match/DEV-collect/search; no shipping gen/make adapters',
        'enumerations':'survey+tactical+quiet at most; fixed prefix visits do not enumerate; geometric attack/EP probes separate',
        'additional_policy':'EP tactical priority uses actual captured pawn/PST rather than empty destination',
        'not_claimed':['identical search nodes/order','NPS or strength improvement','size improvement'],
    }
