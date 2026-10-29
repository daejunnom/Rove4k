"""Pure optional fixed2 A speculative NORMAL completed-slot source form.

Same A normal h, fixed HCE and normal selective policy across roles. Private
normal order/history/id variation is permitted. No altered-role evaluator,
extra pruning/reduction, excluded replies, or lowered requested depth is admitted.
This is a new search/parallel policy, not an equal-search expression compression.
Fresh zero TT/fixed roles; helper TT payload writes blocked. No external reads.
Source-only: no compiler/codec/engine/native/wrapper qualification is claimed.
"""
import hashlib

POLICY='root-normal-slots'
BEFORE=(8821, 'c8efc687c503e9872e004431af9fd07c07867ebb19a996fb9c4c0f4d6508f529')
AFTER=(10835, 'bb15535fcedec21e16c7b1c83646dcda77248539022dfbbaa67c1c08821a6691')
EDITS=((4110, 4110, b'static int h(ai*w,const E*p,int C,int G,int a,int d,int f,Y*g){', b'static pthread_mutex_t qj=PTHREAD_MUTEX_INITIALIZER;\nstatic pthread_cond_t qb=PTHREAD_COND_INITIALIZER;\nstatic struct{int done,open,count,next,busy,depth,state[MOVES],score[MOVES];Y move[MOVES];}R2;\nstatic void R2begin(const E*p,int depth,Y*move,int*order,int count){\n for(int i=0;i<count;i++){int j=i;for(int k=i+1;k<count;k++)if(order[k]>order[j])j=k;Y m=move[j];move[j]=move[i];move[i]=m;order[j]=order[i];}\n int first=count;E child;for(int i=0;i<count;i++)if(v(p,move[i],&child)){first=i;break;}\n pthread_mutex_lock(&qj);R2.count=count;R2.next=first+1;R2.depth=depth;memcpy(R2.move,move,count*sizeof(Y));memset(R2.state,0,count*sizeof(int));if(first<count)R2.state[first]=2;R2.open=1;pthread_cond_broadcast(&qb);pthread_mutex_unlock(&qj);\n}\nstatic int R2take(int i,int*score){\n pthread_mutex_lock(&qj);if(!R2.state[i])R2.state[i]=2;while(R2.state[i]==1)pthread_cond_wait(&qb,&qj);int ready=R2.state[i]==3;if(ready)*score=R2.score[i];pthread_mutex_unlock(&qj);return ready;\n}\nstatic void R2end(void){pthread_mutex_lock(&qj);R2.open=0;pthread_cond_broadcast(&qb);while(R2.busy)pthread_cond_wait(&qb,&qj);pthread_mutex_unlock(&qj);}\nstatic void R2help(ai*,const E*);\nstatic int h(ai*w,const E*p,int C,int G,int a,int d,int f,Y*g){'), (4877, 6045, b'for(int i=0;i<z;i++){int j=i;for(int k=i+1;k<z;k++)if(y[k]>y[j])j=k;Y m=B[j];', b'int split=!d&&w==qr&&p==&ql&&C>0&&!t;if(split)R2begin(p,C,B,y,z);for(int i=0;i<z;i++){int j=i;if(!split)for(int k=i+1;k<z;k++)if(y[k]>y[j])j=k;Y m=B[j];'), (5143, 6386, b'if(A==1||C<=0)l=-h(w,&q,C-1,-a,-G,d+1,R,0);else{', b'if(!(split&&A>1&&R2take(i,&l))){if(A==1||C<=0)l=-h(w,&q,C-1,-a,-G,d+1,R,0);else{'), (5351, 6626, b'if(l>G&&l<a)l=-h(w,&q,C-1,-a,-G,d+1,R,0);}if(atomic_load_explicit(&qp,memory_order_relaxed))return 0;', b'if(l>G&&l<a)l=-h(w,&q,C-1,-a,-G,d+1,R,0);}}if(atomic_load_explicit(&qp,memory_order_relaxed))return 0;'), (5849, 7125, b'V(I,U);return H;}', b'if(w==qr)V(I,U);return H;}'), (5866, 7151, b'void C(ai*w,const E*p){w->a5=0;', b'static void R2help(ai*w,const E*p){\n pthread_mutex_lock(&qj);\n for(;;){\n  while(!R2.done&&(!R2.open||R2.next>=R2.count))pthread_cond_wait(&qb,&qj);\n  if(R2.done)break;\n  int i=R2.next++;if(R2.state[i])continue;\n  R2.state[i]=1;R2.busy=1;Y move=R2.move[i];int depth=R2.depth;\n  pthread_mutex_unlock(&qj);\n  E child;int valid=v(p,move,&child),score=0;\n  if(valid){w->aA[qh]=child.h;score=-h(w,&child,depth-1,-MATE,MATE,1,s(child.b[TO(move)]),0);}\n  pthread_mutex_lock(&qj);\n  if(valid&&!atomic_load_explicit(&qp,memory_order_relaxed)&&score>-MATE&&score<MATE){R2.score[i]=score;R2.state[i]=3;}else R2.state[i]=4;\n  R2.busy=0;pthread_cond_broadcast(&qb);\n }\n pthread_mutex_unlock(&qj);\n}\nvoid C(ai*w,const E*p){w->a5=0;'), (5918, 7888, b'memcpy(w->aA,qg,qh*sizeof(W));for(int C=1;', b'memcpy(w->aA,qg,qh*sizeof(W));if(w!=qr){R2help(w,p);return;}for(int C=1;'), (5983, 7983, b'int l=h(w,p,C,-MATE,MATE,0,6,&H);if(atomic_load_explicit(&qp,memory_order_relaxed))break;', b'int l=h(w,p,C,-MATE,MATE,0,6,&H);R2end();if(atomic_load_explicit(&qp,memory_order_relaxed))break;'), (6072, 8080, b'w->H=H;w->l=l;w->C=C;}}static pthread_mutex_t qj=PTHREAD_MUTEX_INITIALIZER;static pthread_cond_t qb=PTHREAD_COND_INITIALIZER;', b'w->H=H;w->l=l;w->C=C;}pthread_mutex_lock(&qj);R2.done=1;pthread_cond_broadcast(&qb);pthread_mutex_unlock(&qj);}'), (7961, 9955, b'pthread_mutex_lock(&qj);qk=2;qd++;', b'pthread_mutex_lock(&qj);R2.done=0;R2.open=0;qk=2;qd++;'))
GAPS=((0, 0, 4110, '64deda1db9770a79e0d93d0b220b80dd406b698d927e4ff488b18f9f645bed7f'), (4173, 5341, 704, '9f4805eafa2ac0dd0cfedd4a79e6dc66cfd4fbadfcbacafa5b9ac4d76ce5617d'), (4954, 6197, 189, '1879bef68a1f0bc9b9afb272324188749d08c965331fb4626bec5eb54299e7b2'), (5191, 6466, 160, '0cc0fe234376d070b4c1e53018493078602a395efa1ede44b68ffedd68847c44'), (5452, 6728, 397, '44b232318f58032f051981294d597e00ba1ad367cd6c780c69b566e06132d665'), (5866, 7151, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (5897, 7867, 21, 'f717520e98b249fbcc0b5da917a1d6aeb2c1939db949f3a83873b31dbfa688cf'), (5960, 7960, 23, '389b6bf888ef9d81be7083fa8bba42af266c7e86eee641cd6d6e251000dbb039'), (6072, 8080, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (6197, 8191, 1764, '325f56faa6dab43f67deabc8cef89d3c0e4f9f86d0f34f1bb166f4e63f301adb'), (7995, 10009, 826, '2d25b5a36f719cecca518e4a59b19bfd47414a76a6db983f5b36968ae726feac'))
BASE_SINGLE=(8829, 'd32ece21d8fa03174186718092b18a16a46640f6a2c456cf26a7d194b528ed47')
BASE_DOUBLE=(8829, '4bb7e888ed3797e0183841ce3eaae475de837fa079532e2f8aff7c55c2c297bc')
POLICY_SINGLE=(10843, '9a6ba7dc7e7cd020a43cd7b43ad6ea785fb4a7e6269901cb1d9db53cd03b86f9')
POLICY_DOUBLE=(10843, '6ede3d33370e7ac3e8bc80057f35112351c1942dea20737237c42479bd1d5e47')

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)
def _forward(source):
    _need(type(source)is bytes and _pin(source)==BEFORE,'fixed current A8821 shipping source required')
    result=source
    for at,newat,old,new in reversed(EDITS):
        _need(source[at:at+len(old)]==old,'A NORMAL input anchor differs')
        result=result[:at]+new+result[at+len(old):]
    _need(_pin(result)==AFTER,'fixed A NORMAL result differs')
    return result
def _inverse(result):
    _need(type(result)is bytes and _pin(result)==AFTER,'fixed A NORMAL source required')
    source=result
    for at,newat,old,new in reversed(EDITS):
        _need(source[newat:newat+len(new)]==new,'A NORMAL inverse anchor differs')
        source=source[:newat]+old+source[newat+len(new):]
    _need(_pin(source)==BEFORE,'fixed A NORMAL inverse differs')
    return source
def transform_source(source):
    result=_forward(source)
    _need(_inverse(result)==source,'A NORMAL full inverse differs')
    for at,newat,length,digest in GAPS:
        before=source[at:at+length];after=result[newat:newat+length]
        _need(before==after and hashlib.sha256(before).hexdigest()==digest,'A NORMAL protected gap differs')
    _need(result.count(b'R2take(i,&l)')==1 and b'R2take(i,&proposal)'not in result and b'!avoid'not in result,'direct NORMAL consumer differs')
    _need(result.count(b'if(w==qr)V(I,U);')==1,'helper TT payload writer fence differs')
    return result,{'policy':POLICY,'scope':'source-only new speculative normal search/parallel policy',
        'regions':len(EDITS),'protected_gaps':len(GAPS),'full_inverse':True,
        'workers':2,'total_threads':3,'tt_bits':18,'ply':128,
        'same_A_NORMAL_policy':True,'private_normal_order_history_variation_permitted':True,
        'helper_completed_slot_direct_to_leader_l':True,'helper_TT_payload_store':False,
        'same_Loose_search_claimed':False,'formal_minimax_or_identical_private_function_claimed':False,
        'runtime_qualified':False,'external_reads':0}
def transform_literal(expression,previous):
    _need(type(expression)is str and _pin(expression.encode())==POLICY_SINGLE,'fixed A NORMAL raw-single required')
    _need(expression[:5]=='br'+chr(39)*3 and expression[-3:]==chr(39)*3,'A NORMAL raw-single delimiter differs')
    original=expression[:5]+_inverse(expression[5:-3].encode()).decode()+expression[-3:]
    _need(_pin(original.encode())==BASE_SINGLE,'current A output preimage differs')
    guarded=previous(original)
    _need(type(guarded)is str and _pin(guarded.encode())==BASE_DOUBLE,'existing output/condition/names literal guard differs')
    _need(guarded[:5]=='br'+chr(34)*3 and guarded[-3:]==chr(34)*3,'A output raw-double delimiter differs')
    selected=guarded[:5]+_forward(guarded[5:-3].encode()).decode()+guarded[-3:]
    _need(_pin(selected.encode())==POLICY_DOUBLE,'fixed A NORMAL raw-double differs')
    return selected
