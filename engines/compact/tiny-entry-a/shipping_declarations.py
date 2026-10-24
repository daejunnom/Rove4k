"""Fixed shipping-only adjacent declarations and completion sequence.

This ordinary source owns its literal policy. It reads no experiment, report,
old artifact, C parser, external engine or network input. DEV bypasses it.
"""
import hashlib


def sha(raw):return hashlib.sha256(raw).hexdigest()


READABLE = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
SOURCE = (9713, '1f4097d43c5f6e84d7cbd17906100354da25be205d44ca08fbf52732e63b624c')
RESULT = (9687, '6946861173a6b1dee660e83d72db40cde36a066be04e3c4457d4b67a6ab7ae4e')
PAIRS = (('HCE-value', b'int a=abs(v),d=q>>4,f=q&7,g=v>0?d:7-d;int i=7-abs(2*f-7)-abs(2*d-7);int l=qi[a]+g*(a==1?7:a==4?2:0)+i*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);', b'int a=abs(v),d=q>>4,f=q&7,g=v>0?d:7-d,i=7-abs(2*f-7)-abs(2*d-7),l=qi[a]+g*(a==1?7:a==4?2:0)+i*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);'), ('make-locals', b'int o=FROM(m),a=TO(m),d=PROMO(m),s=p->s;int v=p->b[o],f=p->b[a];', b'int o=FROM(m),a=TO(m),d=PROMO(m),s=p->s,v=p->b[o],f=p->b[a];'), ('walk-direction-range', b'int j=a==1?(s>0?12:14):a==2?0:a==3?12:8;int m=a==1?j+2:a==2?8:a==4?12:16;', b'int j=a==1?(s>0?12:14):a==2?0:a==3?12:8,m=a==1?j+2:a==2?8:a==4?12:16;'), ('search-draw-locals', b'int n=aa(p,p->k[p->s<0],-p->s),t=p->aI>=100;int u=0,x=w->at-1-p->aI;', b'int n=aa(p,p->k[p->s<0],-p->s),t=p->aI>=100,u=0,x=w->at-1-p->aI;'), ('search-score-locals', b'int y[MOVES],z=ar(p,B),A=0,D=G,H=-MATE;int F=p->s*p->v;', b'int y[MOVES],z=ar(p,B),A=0,D=G,H=-MATE,F=p->s*p->v;'), ('worker-completion-sequence', b'if(!--qk){aP();pthread_cond_broadcast(&qf);}', b'if(!--qk)aP(),pthread_cond_broadcast(&qf);'))


def transform_source(source, *, readable):
    if sha(readable)!=READABLE or (len(source),sha(source))!=SOURCE:
        raise ValueError('fixed declaration stage source/readable differs')
    old=source;pieces=[];old_parts=[];cursor=0;spans=[]
    for role,before,after in PAIRS:
        if old.count(before)!=1:raise ValueError('declaration preimage changed: '+role)
        start=old.index(before)
        if start<cursor:raise ValueError('declaration source order/overlap changed')
        unchanged=old[cursor:start];pieces.extend((unchanged,after));old_parts.append(unchanged)
        spans.append({'role':role,'old_offset':start,'old_bytes':len(before),'new_bytes':len(after),
                      'old_sha256':sha(before),'new_sha256':sha(after)})
        cursor=start+len(before)
    pieces.append(old[cursor:]);old_parts.append(old[cursor:]);result=b''.join(pieces)
    if (len(result),sha(result))!=RESULT:raise ValueError('sole declaration output differs')
    inverse=result;new_parts=[];cursor=0
    for row,(_,before,after) in zip(spans,PAIRS):
        if result.count(after)!=1:raise ValueError('declaration inverse fragment changed')
        start=result.index(after)
        if start<cursor:raise ValueError('declaration inverse order changed')
        row['new_offset']=start;new_parts.append(result[cursor:start]);cursor=start+len(after)
    new_parts.append(result[cursor:])
    if old_parts!=new_parts:raise ValueError('declaration protected complement changed')
    for row,(_,before,after) in reversed(list(zip(spans,PAIRS))):
        start=row['new_offset']
        if inverse[start:start+len(after)]!=after:raise ValueError('declaration inverse mismatch')
        inverse=inverse[:start]+before+inverse[start+len(after):]
    if inverse!=old:raise ValueError('declaration exact inverse changed')
    complement=b''.join(old_parts)
    return result,{'stage':'shipping-after-input-only','source_sha256':sha(old),
                   'result_sha256':sha(result),'source_delta':len(result)-len(old),
                   'readable_sha256':sha(readable),'exact_inverse':True,
                   'protected_complement_exact':True,'protected_complement_bytes':len(complement),
                   'protected_complement_sha256':sha(complement),'spans':spans,
                   'DEV_transform':False,'external_inputs':False}
