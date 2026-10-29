"""Opt-in material-move-tt: full-key coherent move ordering, no score cache.

The input is the ordinary post-material-capture shipping form. The separate
policy keeps full-depth MTD, material, rules, actual history and pool, but drops
TT score/depth/bound reuse and the now TT-only rolling Board.r. It is not a
strength/performance equivalence claim. Full and material-noise/DEV bypass it.
All literals are owned here; no experiment, receipt or generated input is read.
"""
import hashlib

INPUT_BYTES=8602
INPUT_SHA256='3752a0c745efb63a2c1ba08974789c10dc56b815428d11903fbc8f2b5461ea3b'
OUTPUT_BYTES=8265
OUTPUT_SHA256='c858083e36683b1e83028e0c4e1b8d611ae12fc7058e4842ab4952fbd2de9c08'
EDITS=(('unused score alias', 289, 289, b'typedef int16_t X;', b''), ('remove TT-only reversible-path member', 374, 356, b'W h,r;}za;', b'W h;}za;'), ('fullkey move lock record', 525, 505, b'typedef struct{atomic_flag zN;W a,b;}Z;', b'typedef struct{W a;Y b;atomic_flag zN;}Z;'), ('remove TT-only reversible-path make update', 2356, 2338, b't->r=t->a?((p->r<<1)|(p->r>>63))^t->h:t->h;', b''), ('remove TT-only reversible-path start initialization', 3543, 3482, b't.r=t.h;', b''), ('move payload return and parameter', 3558, 3489, b'static W N(W a,W d)', b'static Y N(W a,Y d)'), ('ordering-only probe; no score cutoff', 4310, 4241, b'W E=p->h^h(p->r+(unsigned)p->a),F=N(E,0);Y G=F&131071;int H=(X)(F>>17),I=(F>>41)&3,J=(F>>33)&255;if(H>MATE-128)H-=f;if(H< -MATE+128)H+=f;if(f&&I&&J==(a>0?a:0)&&I!=2+(H>=d))return H;', b'Y G=N(p->h,0);int H;'), ('move-only write; no score depth bound packing', 5052, 4822, b'I=C>=d?2:3;H=C;if(H>MATE-128)H+=f;if(H< -MATE+128)H-=f;F=y|((W)(uint16_t)H<<17)|((W)(a>0?a:0)<<33)|((W)I<<41);N(E,F);return C;', b'N(p->h,y);return C;'))
GAPS=((0, 0, 289, '10493752212e63e4081ea7c351a3bc46b0b3b8750312de2f499e6781e55e8801'), (307, 289, 67, 'ebf85e6bab5a0c51033b88bb309b77c4c2cba92bec9b4fc534822a90f1c071cb'), (384, 364, 141, 'ff19e992c1b29e86ac7dfa3d09309f618953a8ee630e7af2084c7692eabd4ffd'), (564, 546, 1792, '8c0966345646e8cea39abef086b523e3d9bda51e83ce61bcbcd4ae32ba57d7b7'), (2399, 2338, 1144, 'aac9068b6cd9e0e7979c6367f42800d9beb8432261f968d3728f6e55e927902c'), (3551, 3482, 7, '291ef71281b63f78e4b50684b9d8ed74fd3c5067fb1ca4c1e791b7a4f1ff0c4e'), (3577, 3508, 733, 'f7a96287c1d827a4a147147e11904b73e4d426682aa8d72291cce8865b4fda1d'), (4491, 4261, 561, '761e0cef61eabcd58d4081d5cab941807be950780fb6c857d06da679d316ed79'), (5178, 4841, 3424, 'ac134a7b22939e2d66322b5494ae625615fc7a69ad696266fea8483909acba7f'))

def sha(data):return hashlib.sha256(data).hexdigest()

def transform_source(source):
    if type(source) is not bytes or len(source)!=INPUT_BYTES or sha(source)!=INPUT_SHA256:
        raise ValueError('exact post-material-capture F source required for MoveTT')
    parts=[];previous=0
    for role,oa,na,old,new in EDITS:
        if oa<previous or source[oa:oa+len(old)]!=old or source.count(old)!=1:
            raise ValueError('fixed MoveTT role differs: '+role)
        parts.extend((source[previous:oa],new));previous=oa+len(old)
    parts.append(source[previous:]);result=b''.join(parts);inverse=[];previous=0
    for role,oa,na,old,new in EDITS:
        if result[na:na+len(new)]!=new:raise ValueError('MoveTT output role differs: '+role)
        inverse.extend((result[previous:na],old));previous=na+len(new)
    inverse.append(result[previous:])
    if b''.join(inverse)!=source:raise ValueError('MoveTT exact inverse differs')
    for oa,na,size,pin in GAPS:
        old=source[oa:oa+size];new=result[na:na+size]
        if old!=new or sha(old)!=pin:raise ValueError('MoveTT protected complement differs')
    if len(result)!=OUTPUT_BYTES or sha(result)!=OUTPUT_SHA256:
        raise ValueError('fixed MoveTT output identity differs')
    return result,{'policy':'F-MTD-MaterialNoise-MoveTT-v1','stage':'shipping-after-material-capture',
                   'role_edits':8,'protected_gaps':9,'exact_inverse':True,
                   'source_bytes':len(result),'source_sha256':sha(result),
                   'full64key':True,'payload':'generated Move only; zero parameter reads, never clears',
                   'publication':'unchanged coherent acquire/release trylock; busy miss',
                   'TT_score_depth_bound_cutoffs':False,'TT_only_Board_r_removed':True,
                   'repetition_half_draw_mate_QS_MTD_witness_lastcomplete_stop_pool_preserved':True,
                   'full_material_noise_DEV_bypass':True,'policy_change_not_equivalence':True}
