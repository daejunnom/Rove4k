"""Fixed shipping-only adjacent declarations and completion sequence.

This ordinary source owns its literal policy. It reads no experiment, report,
old artifact, C parser, external engine or network input. DEV bypasses it.
"""
import hashlib


def sha(raw):return hashlib.sha256(raw).hexdigest()


READABLE = 'ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd'
SOURCE = (9728, '845f731a0f1fabd62bae629ad191aadd39525d0db7d59628224e315f09c0519d')
RESULT = (9702, '60a74d16a6b3fbd7c1fc2d05207cfe4b860a52746caca137f7d34418762eab99')
PAIRS = (('HCE-value', b'int a=abs(v),d=q>>4,f=q&7,g=v>0?d:7-d;int i=7-abs(2*f-7)-abs(2*d-7);int j=qi[a]+g*(a==1?7:a==4?2:0)+i*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);', b'int a=abs(v),d=q>>4,f=q&7,g=v>0?d:7-d,i=7-abs(2*f-7)-abs(2*d-7),j=qi[a]+g*(a==1?7:a==4?2:0)+i*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);'), ('make-locals', b'int a=FROM(m),d=TO(m),f=PROMO(m),s=p->s;int v=p->b[a],g=p->b[d];', b'int a=FROM(m),d=TO(m),f=PROMO(m),s=p->s,v=p->b[a],g=p->b[d];'), ('walk-direction-range', b'int m=a==1?(s>0?12:14):a==2?0:a==3?12:8;int o=a==1?m+2:a==2?8:a==4?12:16;', b'int m=a==1?(s>0?12:14):a==2?0:a==3?12:8,o=a==1?m+2:a==2?8:a==4?12:16;'), ('search-draw-locals', b'int n=aa(p,p->k[p->s<0],-p->s),o=p->a>=100;int t=0,u=w->g-1-p->a;', b'int n=aa(p,p->k[p->s<0],-p->s),o=p->a>=100,t=0,u=w->g-1-p->a;'), ('search-score-locals', b'int z[MOVES],A=ah(p,x),B=0,C=-MATE;int D=p->s*p->v;', b'int z[MOVES],A=ah(p,x),B=0,C=-MATE,D=p->s*p->v;'), ('worker-completion-sequence', b'if(!--qk){at();pthread_cond_broadcast(&qf);}', b'if(!--qk)at(),pthread_cond_broadcast(&qf);'))


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
