"""Finite D search-source experiments, without build or publication side effects.

Input is the complete readable scalar-D cohort after the existing previous-piece
and unsigned-history transformations. Each role has one checked source boundary;
non-applicable or conflicting combinations fail instead of editing a near match.
The caller owns the source/cohort proof, full shipping-cost measurement, and rules,
search, cancellation and runtime qualification. No selector itself certifies a
candidate, and size results are deliberately not embedded in this source module.

BEST keeps every search feature. REDUCED_OPTIONS remove search heuristics and are
feasibility-only profiles requiring separate strength evaluation; they are never
selected implicitly. Retained ABI and helper alternatives include cost failures,
because final packed costs are nonadditive and depend on the combined cohort.
"""
from __future__ import annotations

FILES = frozenset(('tiny.h', 'board.c', 'search.c', 'runtime.c', 'start.S', 'image.ld'))
FULL_OPTIONS = (
    'tie_mod', 'moves432', 'moves413', 'moves416',
    'history_rows120', 'history_square120', 'root_field',
    'tt_split', 'tt_data_signal', 'tt_split_signal',
    'mate_helper', 'mate_sign', 'mate_ternary', 'mate_helper_noinline',
    'mate_abs_noinline', 'mate_range_noinline', 'learn_noinline', 'tt_noinline',
    'eval_bound', 'bestmove_nonzero', 'tt_bound_select', 'tt_bound_bits',
    'error_abs', 'depth_zero', 'prior_slots', 'prior_pack', 'prior_slots_root',
    'prior_pack_root', 'score_helper', 'draw_helper', 'select_helper',
    'prior_board_root',
)
REDUCED_OPTIONS = ('reduced_no_correction', 'reduced_no_continuation')
OPTIONS = FULL_OPTIONS + REDUCED_OPTIONS
BEST = ('moves432', 'eval_bound', 'mate_helper_noinline', 'tt_bound_select')


def apply(files: dict[str, bytes], options: tuple[str, ...]) -> dict[str, bytes]:
    """Apply only the requested finite selectors to an unchanged input mapping.

    Source-domain requirements: valid 0x88 squares, exactly one king and at most
    16 pieces per side, current scalar value() semantics, valid search windows,
    and the current depth/mate and coherent TT publication contracts. The
    TT-data sentinel alternative additionally requires nonzero production store
    payloads. These are D-specific projections, not generic C rewrites.
    """
    if set(files) != FILES or any(type(data) is not bytes for data in files.values()):
        raise ValueError('complete six-file normalized D source required')
    if isinstance(options, str):
        raise ValueError('explicit selector sequence required')
    options = tuple(options)
    if any(option not in OPTIONS for option in options) or len(set(options)) != len(options):
        raise ValueError('unique known D structural search selectors required')
    return _apply(files, options)


def _once(data, before, after):
    if isinstance(before, str): before=before.encode()
    if isinstance(after, str): after=after.encode()
    if data.count(before)!=1:
        raise ValueError('unique source boundary required: '+repr(before[:100]))
    return data.replace(before,after)


def _apply(files, labels):
    result=dict(files)
    if isinstance(labels,str): labels=(labels,)
    for label in labels:
        s=result['search.c']; h=result['tiny.h']
        if label=='tie_mod':
            s=_once(s,'(m*37u+w->id*19u)%17','(m*3u+w->id*2u)%17')
        elif label=='moves432':
            h=_once(h,'#define MOVES 512','#define MOVES 432')
        elif label in ('moves413','moves416'):
            h=_once(h,'#define MOVES 512','#define MOVES '+label[5:])
            # One king contributes at most eight; each of at most 15 others
            # contributes at most 27. Castling has at most 5+2 king moves.
            h=_once(h,
                '/* Admission preserves <=16 pieces/side; each piece has <=27 pseudo moves,\n * including all promotions/castles, so the conservative bound is 432. */',
                '/* Admission preserves one king and <=16 pieces/side. The king has <=8\n * pseudo moves (home-rank castles <=5+2); others have <=27, including\n * all promotions. Thus 15*27+8=413 is a conservative capacity bound. */')
        elif label=='history_rows120':
            h=_once(h,'history[128][128]','history[120][128]')
        elif label=='history_square120':
            h=_once(h,'history[128][128]','history[120][120]')
        elif label=='root_field':
            h=_once(h,'int id,depth; Move best;','int id,depth; Move best,current;')
            s=_once(s,'int ply,int prior,Move *root)','int ply,int prior)')
            s=_once(s,'-alpha,ply+1,piece_index(q.b[to]),0);','-alpha,ply+1,piece_index(q.b[to]));')
            s=_once(s,'if(root)*root=m;','if(!ply)w->current=m;')
            s=_once(s,'Move best=w->best;','w->current=w->best;')
            s=_once(s,'search(w,p,depth,-MATE,MATE,0,6,&best);','search(w,p,depth,-MATE,MATE,0,6);')
            s=_once(s,'w->best=best;w->depth=depth;','w->best=w->current;w->depth=depth;')
        elif label=='tt_split':
            s=_once(s,'for(int i=0;i<=!!write;i++)\n        __asm__ volatile("lock cmpxchg16b %0":"+m"(*e),"+a"(lo),"+d"(hi):"b"(i?key:0ull),"c"(i?data:0ull):"cc","memory");',
                '__asm__ volatile("lock cmpxchg16b %0":"+m"(*e),"+a"(lo),"+d"(hi):"b"(0ull),"c"(0ull):"cc","memory");\n    if(write)__asm__ volatile("lock cmpxchg16b %0":"+m"(*e),"+a"(lo),"+d"(hi):"b"(key),"c"(data):"cc","memory");')
        elif label=='tt_data_signal':
            s=_once(s,'probe(uint64_t key,int write,uint64_t data)','probe(uint64_t key,uint64_t data)')
            s=_once(s,'i<=!!write','i<=!!data')
            s=_once(s,'return write?data:','return data?data:')
            s=_once(s,'probe(key,0,0)','probe(key,0)')
            s=_once(s,'probe(key,1,data)','probe(key,data)')
        elif label=='tt_split_signal':
            result['search.c']=s;result['tiny.h']=h
            result= _apply(result,'tt_split')
            s=result['search.c']
            s=_once(s,'probe(uint64_t key,int write,uint64_t data)','probe(uint64_t key,uint64_t data)')
            s=_once(s,'if(write)__asm__','if(data)__asm__')
            s=_once(s,'return write?data:','return data?data:')
            s=_once(s,'probe(key,0,0)','probe(key,0)')
            s=_once(s,'probe(key,1,data)','probe(key,data)')
        elif label=='mate_helper':
            marker='static int search('
            helper='static int mate_score(int score,int ply){return score+(score>MATE-PLY?ply:score< -MATE+PLY?-ply:0);}\n'
            s=_once(s,marker,helper+marker)
            s=_once(s,'    if(score>MATE-PLY)score-=ply;\n    if(score< -MATE+PLY)score+=ply;','    score=mate_score(score,-ply);')
            s=_once(s,'    if(score>MATE-PLY)score+=ply;\n    if(score< -MATE+PLY)score-=ply;','    score=mate_score(score,ply);')
        elif label=='mate_sign':
            s=_once(s,'    if(score>MATE-PLY)score-=ply;\n    if(score< -MATE+PLY)score+=ply;','    score-=((score>MATE-PLY)-(score< -MATE+PLY))*ply;')
            s=_once(s,'    if(score>MATE-PLY)score+=ply;\n    if(score< -MATE+PLY)score-=ply;','    score+=((score>MATE-PLY)-(score< -MATE+PLY))*ply;')
        elif label=='mate_ternary':
            s=_once(s,'    if(score>MATE-PLY)score-=ply;\n    if(score< -MATE+PLY)score+=ply;','    score+=score>MATE-PLY?-ply:score< -MATE+PLY?ply:0;')
            s=_once(s,'    if(score>MATE-PLY)score+=ply;\n    if(score< -MATE+PLY)score-=ply;','    score+=score>MATE-PLY?ply:score< -MATE+PLY?-ply:0;')
        elif label=='mate_helper_noinline':
            result['search.c']=s;result['tiny.h']=h
            result= _apply(result,'mate_helper')
            s=_once(result['search.c'],'static int mate_score(','static __attribute__((noinline)) int mate_score(')
        elif label in ('mate_abs_noinline','mate_range_noinline'):
            result['search.c']=s;result['tiny.h']=h
            result= _apply(result,'mate_helper_noinline')
            s=result['search.c']
            condition='abs(score)>MATE-PLY' if label=='mate_abs_noinline' else '(unsigned)(score+MATE-PLY)>2*(MATE-PLY)'
            s=_once(s,'score>MATE-PLY?ply:score< -MATE+PLY?-ply:0',condition+'?(score<0?-ply:ply):0')
        elif label=='learn_noinline':
            s=_once(s,'static void learn(','static __attribute__((noinline)) void learn(')
        elif label=='tt_noinline':
            s=_once(s,'static uint64_t probe(','static __attribute__((noinline)) uint64_t probe(')
        elif label=='eval_bound':
            # Every admitted side has at most 16 pieces; actual value() has
            # abs(value)<=910 on each valid mailbox square. 32*910=29120.
            # Keep the clamp for configurations whose mate threshold is lower.
            clamp=(b'    if(evaluation>MATE-PLY-1)evaluation=MATE-PLY-1;\n'
                   b'    if(evaluation< -MATE+PLY+1)evaluation=-MATE+PLY+1;\n')
            s=_once(s,clamp,b'#if MATE-PLY-1<=32*910\n'+clamp+b'#endif\n')
        elif label=='bestmove_nonzero':
            s=_once(s,'bound==1&&!check&&bestmove&&','bound==1&&!check&&')
        elif label=='tt_bound_select':
            s=_once(s,'(bound==1||(bound==2&&score>=beta)||(bound==3&&score<=alpha))','(bound==1||(bound==2?score>=beta:score<=alpha))')
        elif label=='tt_bound_bits':
            s=_once(s,'bound=best<=old?3:best>=beta?2:1;','bound=1+2*(best<=old)+(best>=beta);')
        elif label=='error_abs':
            s=_once(s,'if(error>256)error=256;if(error< -256)error=-256;','if(abs(error)>256)error=error<0?-256:256;')
        elif label=='depth_zero':
            s=_once(s,'    if(!claim(w))return 0;','    if(!claim(w))return 0;\n    if(depth<0)depth=0;')
            s=s.replace(b'(depth>0?depth:0)',b'depth')
        elif label=='prior_slots':
            h=_once(h,'uint64_t nodes,keys[PLY];','uint64_t nodes,keys[PLY];\n    uint8_t priors[PLY];')
            s=_once(s,'int ply,int prior,Move *root)','int ply,Move *root)')
            s=_once(s,'    if(!claim(w))return 0;','    if(!claim(w))return 0;\n    int prior=w->priors[ply];')
            s=_once(s,'        w->keys[ply]=q.h;','        w->keys[ply]=q.h;w->priors[ply+1]=piece_index(q.b[to]);')
            s=_once(s,'-alpha,ply+1,piece_index(q.b[to]),0);','-alpha,ply+1,0);')
            s=_once(s,'    w->nodes=0;w->depth=0;','    w->nodes=0;w->depth=0;w->priors[0]=6;')
            s=_once(s,'search(w,p,depth,-MATE,MATE,0,6,&best);','search(w,p,depth,-MATE,MATE,0,&best);')
        elif label=='prior_pack':
            s=_once(s,'int ply,int prior,Move *root)','int packed,Move *root)')
            s=_once(s,'    if(!claim(w))return 0;','    if(!claim(w))return 0;\n    int ply=packed&255,prior=packed>>8;')
            s=_once(s,'-alpha,ply+1,piece_index(q.b[to]),0);','-alpha,(ply+1)|(piece_index(q.b[to])<<8),0);')
            s=_once(s,'search(w,p,depth,-MATE,MATE,0,6,&best);','search(w,p,depth,-MATE,MATE,6<<8,&best);')
        elif label=='prior_slots_root':
            result['search.c']=s;result['tiny.h']=h
            result= _apply(result,'prior_slots')
            s=result['search.c'];h=result['tiny.h']
            h=_once(h,'int id,depth; Move best;','int id,depth; Move best,current;')
            s=_once(s,'int ply,Move *root)','int ply)')
            s=_once(s,'-alpha,ply+1,0);','-alpha,ply+1);')
            s=_once(s,'if(root)*root=m;','if(!ply)w->current=m;')
            s=_once(s,'Move best=w->best;','w->current=w->best;')
            s=_once(s,'search(w,p,depth,-MATE,MATE,0,&best);','search(w,p,depth,-MATE,MATE,0);')
            s=_once(s,'w->best=best;w->depth=depth;','w->best=w->current;w->depth=depth;')
        elif label=='prior_pack_root':
            result['search.c']=s;result['tiny.h']=h
            result= _apply(result,'prior_pack')
            s=result['search.c'];h=result['tiny.h']
            h=_once(h,'int id,depth; Move best;','int id,depth; Move best,current;')
            s=_once(s,'int packed,Move *root)','int packed)')
            s=_once(s,'-alpha,(ply+1)|(piece_index(q.b[to])<<8),0);','-alpha,(ply+1)|(piece_index(q.b[to])<<8));')
            s=_once(s,'if(root)*root=m;','if(!ply)w->current=m;')
            s=_once(s,'Move best=w->best;','w->current=w->best;')
            s=_once(s,'search(w,p,depth,-MATE,MATE,6<<8,&best);','search(w,p,depth,-MATE,MATE,6<<8);')
            s=_once(s,'w->best=best;w->depth=depth;','w->best=w->current;w->depth=depth;')
        elif label=='score_helper':
            start=s.index(b'    for(int i=0;i<count;i++){\n        Move m=moves[i];int from=FROM(m),to=TO(m),pi=piece_index(p->b[from]);')
            end=s.index(b'    for(int i=0;i<count;i++){\n        int j=i;',start)
            body=s[start:end]
            helper=body.replace(b'    for(int i=0;i<count;i++){\n        Move m=moves[i];',b'')
            helper=helper.replace(b'scores[i]=',b'int score=').replace(b'scores[i]+=',b'score+=')
            helper=helper.replace(b'    }\n',b'    return score;\n}\n')
            helper=b'static __attribute__((noinline)) int order_score(Worker *w,const Board *p,Move m,Move tt,int prior){\n'+helper
            s=_once(s,body,b'    for(int i=0;i<count;i++)scores[i]=order_score(w,p,moves[i],tt,prior);\n')
            s=_once(s,b'static int search(',helper+b'static int search(')
        elif label=='draw_helper':
            start=s.index(b'    /* Only positions since the last irreversible move may repeat.')
            end=s.index(b'    Move moves[MOVES],bestmove=0;',start)
            body=s[start:end]
            helper=body.replace(b'    draw|=repetitions>=2||dead(p);',b'    return p->half>=100||repetitions>=2||dead(p);')
            helper=b'static __attribute__((noinline)) int is_draw(Worker *w,const Board *p,int ply){\n'+helper+b'}\n'
            s=_once(s,body,b'')
            s=_once(s,b'draw=p->half>=100;',b'draw=is_draw(w,p,ply);')
            s=_once(s,b'static int search(',helper+b'static int search(')
        elif label=='select_helper':
            old=b'        int j=i;for(int k=i+1;k<count;k++)if(scores[k]>scores[j])j=k;\n        Move m=moves[j];moves[j]=moves[i];\n        scores[j]=scores[i];'
            helper=b'static __attribute__((noinline)) Move select_move(Move *moves,int *scores,int i,int count){\n'+old.replace(b'        ',b'    ')+b'\n    return m;\n}\n'
            s=_once(s,old,b'        Move m=select_move(moves,scores,i,count);')
            s=_once(s,b'static int search(',helper+b'static int search(')
        elif label=='prior_board_root':
            result['search.c']=s;result['tiny.h']=h
            result= _apply(result,'root_field')
            s=result['search.c'];h=result['tiny.h']
            h=_once(h,'int s,c,e,k[2],half,v;','int s,c,e,k[2],half,v,prior;')
            s=_once(s,'int ply,int prior)','int ply)')
            s=_once(s,'    if(!claim(w))return 0;','    if(!claim(w))return 0;\n    int prior=ply?p->prior:6;')
            s=_once(s,'        w->keys[ply]=q.h;','        w->keys[ply]=q.h;q.prior=piece_index(q.b[to]);')
            s=_once(s,'-alpha,ply+1,piece_index(q.b[to]));','-alpha,ply+1);')
            s=_once(s,'search(w,p,depth,-MATE,MATE,0,6);','search(w,p,depth,-MATE,MATE,0);')
        elif label=='reduced_no_correction':
            s=_once(s,'            if(reduce){COUNT(w,corr_uses);reduce=evaluation+w->correction[p->h&1023]/64<alpha+100;}\n','')
            a=s.index(b'    if(depth>0&&bound==1&&!check&&bestmove&&')
            b=s.index(b'    score=best;',a)
            s=s[:a]+s[b:]
            h=_once(h,';int16_t correction[1024];',';')
            result['runtime.c']=_once(result['runtime.c'],'        memset(workers[i].correction,0,sizeof workers[i].correction);\n','') if b'        memset(workers[i].correction,0,sizeof workers[i].correction);\n' in result['runtime.c'] else result['runtime.c']
        elif label=='reduced_no_continuation':
            s=_once(s,'+w->continuation[prior][pi]','')
            s=_once(s,'                learn(&w->continuation[prior][piece_index(p->b[from])],bonus);\n','')
            s=_once(s,'COUNT(w,hist_updates);COUNT(w,cont_updates);','COUNT(w,hist_updates);')
            h=_once(h,',continuation[13][13]','')
            s=_once(s,'int ply,int prior,Move *root)','int ply,Move *root)')
            s=_once(s,'-alpha,ply+1,piece_index(q.b[to]),0);','-alpha,ply+1,0);')
            s=_once(s,'search(w,p,depth,-MATE,MATE,0,6,&best);','search(w,p,depth,-MATE,MATE,0,&best);')
            result['runtime.c']=_once(result['runtime.c'],'        memset(workers[i].continuation,0,sizeof workers[i].continuation);\n','') if b'        memset(workers[i].continuation,0,sizeof workers[i].continuation);\n' in result['runtime.c'] else result['runtime.c']
        else:
            raise ValueError(label)
        result['search.c']=s;result['tiny.h']=h
    return result
