"""Explicit D board alternatives for the fast-capacity/BSS cost cohort.

These edit readable producer output, never a compiled or compressed artifact.
They are independent, unselected experiments; size and execution qualification
belong to the caller.  The source-role checks deliberately reject a different
board contract rather than silently applying an approximate transformation.
"""

from __future__ import annotations


def _replace(data: bytes, before: bytes, after: bytes) -> bytes:
    if data.count(before) != 1:
        raise ValueError("D board role changed: " + repr(before[:100]))
    return data.replace(before, after, 1)


_BOARD = b"typedef struct { int s,c,e,k[2],half,v; unsigned material; uint64_t h,r; int8_t b[128]; } Board;"
_EP = b'''static void ep(Board *p){
    if(p->e<0)return;
    for(int d=-1;d<=1;d+=2){
        int q=p->e-p->s*16+d;
        if(!(q&0x88)&&p->b[q]==p->s){
            Board t;if(make(p,MOVE(q,p->e,0),&t))return;
        }
    }
    p->e=-1;
}'''
_EP_OCCUPANCY = b'''static void ep(Board *p){
    if(p->e<0)return;
    int to=p->e,s=p->s,victim=to-s*16;
    for(int d=-1;d<=1;d+=2){
        int from=victim+d;
        if(!(from&0x88)&&p->b[from]==s){
            p->b[from]=p->b[victim]=0;p->b[to]=(int8_t)s;
            int legal=!attacked(p,p->k[s<0],-s);
            p->b[from]=(int8_t)s;p->b[victim]=(int8_t)-s;p->b[to]=0;
            if(legal)return;
        }
    }
    p->e=-1;
}'''


def ep_occupancy(files: dict[str, bytes]) -> dict[str, bytes]:
    """Canonicalize EP using only the state the legality query consumes.

    Every caller owns an unpublished Board: make's child, fen's local Board,
    or verify_board's reconstruction.  The existing contract proves an empty
    target, the opposing pawn at target-side*16, and a valid own king.  The
    three cells are distinct.  Restore all three before either returning or
    trying the other pawn.  Attack mode consumes mailbox/king geometry, not
    hash, evaluation, material, halfmove, EP or reversible-path metadata.
    Thus both pinned-pawn and discovered slider attacks remain real occupancy
    queries; no guessed adjacent-pawn test replaces legal EP canonicalization.
    """
    result = dict(files)
    result["board.c"] = _replace(result["board.c"], _EP, _EP_OCCUPANCY)
    return result


def ep_occupancy_shared(files: dict[str, bytes]) -> dict[str, bytes]:
    # GCC13 inlined the occupancy trial into make, adding 78 text bytes in the
    # first measured cohort. Keep its temporary indices and restore state in
    # one separate owner; the failed inline candidate remains reproducible.
    result = ep_occupancy(files)
    result["board.c"] = _replace(result["board.c"], b"static void ep(Board *p){",
        b"static __attribute__((noinline,noclone)) void ep(Board *p){")
    return result


_START = b'''void start(Board *p){
    static const int8_t back[8]={4,2,3,5,6,3,2,4};
    *p=(Board){0};p->s=1;p->c=15;p->e=-1;
    p->k[0]=4;p->k[1]=116;p->v=0;p->material=725058;
    p->h=p->r=UINT64_C(0x227e84707c3337b6);
    for(int f=0;f<8;f++){p->b[f]=back[f];p->b[16+f]=1;p->b[96+f]=-1;p->b[112+f]=-back[f];}
}'''
_START_IMAGE = b'''void start(Board *p){
    static const Board initial={
        .s=1,.c=15,.e=-1,.k={4,116},.material=725058,
        .h=UINT64_C(0x227e84707c3337b6),.r=UINT64_C(0x227e84707c3337b6),
        .b={4,2,3,5,6,3,2,4,[16]=1,1,1,1,1,1,1,1,
            [96]=-1,-1,-1,-1,-1,-1,-1,-1,[112]=-4,-2,-3,-5,-6,-3,-2,-4}
    };
    *p=initial;
}'''


def start_image(files: dict[str, bytes]) -> dict[str, bytes]:
    """Trade initialization instructions for one highly repetitive image.

    The source-derived start constants and full board representation are
    unchanged.  Larger native rodata can still give a smaller whole package;
    the cost runner must include both the copy code and all image bytes.
    """
    result = dict(files)
    result["board.c"] = _replace(result["board.c"], _START, _START_IMAGE)
    return result


def start_image_shared(files: dict[str, bytes]) -> dict[str, bytes]:
    # The first image assignment lost the shared 115-byte start function:
    # GCC13 split/inlined it twice and grew main by 202 bytes. An explicit
    # whole-image copy plus one non-cloned call owner prevents that duplication.
    result = start_image(files)
    data = _replace(result["board.c"], b"void start(Board *p){",
        b"__attribute__((noinline,noclone)) void start(Board *p){")
    result["board.c"] = _replace(data, b"    *p=initial;", b"    memcpy(p,&initial,sizeof *p);")
    return result


_STEPS = b"static const int8_t steps[16]={33,31,18,14,-14,-18,-31,-33,1,-1,16,-16,17,15,-15,-17};"
_PAWN_STEPS = b"static const int8_t steps[22]={33,31,18,14,-14,-18,-31,-33,1,-1,16,-16,17,15,-15,-17,16,17,15,-16,-15,-17};"
_SCALAR_WALK = b'''#else
static int walk(const Board *p,Move *moves,int sq,int s){
    int n=0;
    for(int from=0;from<128;from=from+9&~8){
        int a=p->b[from]*s;if(a<=0)continue;
        if(sq<0&&a==1){
            int to=from+s*16;
            if(!(to&0x88)&&!p->b[to]){
                add(moves,&n,from,to,2);
                if((from>>4)==(s>0?1:6)&&!p->b[to+s*16])add(moves,&n,from,to+s*16,0);
            }
        }
        static const unsigned char ranges[7]={0,62,32,70,52,68,68};
        int range=ranges[a],offset=a==1&&s<0?2:0;
        int first=2*(range&7)+offset,last=2*(range>>3)+offset;
        for(int i=first;i<last;i++){
            int step=steps[i];
            for(int to=from+step;!(to&0x88);to+=step){
                int target=p->b[to];
                if(to==sq)return 1;
                if(target*s>0||(sq<0&&a==1&&!target&&to!=p->e))break;
                if(sq<0)add(moves,&n,from,to,a==1?3:!!target);
                if(target||a<3||a==6)break;
            }
        }
        if(sq<0&&a==6){
            int home=from,rights=p->c>>(s<0?2:0)&3;
            if(rights&&!attacked(p,home,-s)){
                for(int d=1;d>=-1;d-=2)
                    if((rights&(d>0?1:2))&&!p->b[home+d]&&!p->b[home+2*d]&&(d>0||!p->b[home-3])&&!attacked(p,home+d,-s))add(moves,&n,from,home+2*d,0);
                }
        }
    }
    return n;
}
#endif'''
_PAWN_WALK = b'''#else
static int walk(const Board *p,Move *moves,int sq,int s){
    int n=0;
    for(int from=0;from<128;from=from+9&~8){
        int a=p->b[from]*s;if(a<=0)continue;
        static const uint16_t ranges[7]={0,624,256,524,392,520,520};
        int pawn=a==1,range=ranges[a],offset=pawn&&s<0?3:0;
        int first=(range&31)+offset,last=(range>>5)+offset;
        for(int i=first;i<last;i++){
            int push=pawn&&i==first;if(push&&sq>=0)continue;
            int reach=a>=3&&a<=5?8:push&&(from>>4)==(s>0?1:6)?2:1;
            int step=steps[i];
            for(int to=from+step;!(to&0x88)&&reach--;to+=step){
                int target=p->b[to];
                if(to==sq)return 1;
                if(target*s>0||(pawn&&(push?target:sq<0&&!target&&to!=p->e)))break;
                if(sq<0)add(moves,&n,from,to,pawn?3-push:!!target);
                if(target)break;
            }
        }
        if(sq<0&&a==6){
            int home=from,rights=p->c>>(s<0?2:0)&3;
            if(rights&&!attacked(p,home,-s)){
                for(int d=1;d>=-1;d-=2)
                    if((rights&(d>0?1:2))&&!p->b[home+d]&&!p->b[home+2*d]&&(d>0||!p->b[home-3])&&!attacked(p,home+d,-s))add(moves,&n,from,home+2*d,0);
                }
        }
    }
    return n;
}
#endif'''


def pawn_ray(files: dict[str, bytes]) -> dict[str, bytes]:
    """Use the bounded ray owner for pawn pushes and ordinary destinations.

    White pawn directions remain +16,+17,+15, black -16,-15,-17.  A starting
    pawn has reach two only along its push direction; all other pawn rays
    have reach one.  Geometric attack queries skip pushes.  Promotion uses
    the unchanged add owner and keeps N/B/R/Q and the complete move order.
    DEV with scalar selection exercises this same algorithm instead of
    implicitly switching to the independent HQ generator.
    """
    result = dict(files)
    data = _replace(result["board.c"], _STEPS, _PAWN_STEPS)
    data = _replace(data, b"#if D_HQ || DEV\nstatic int walk(", b"#if D_HQ\nstatic int walk(")
    result["board.c"] = _replace(data, _SCALAR_WALK, _PAWN_WALK)
    return result


VARIANTS = {"ep-occupancy": ep_occupancy, "start-image": start_image,
            "pawn-ray": pawn_ray, "ep-occupancy-shared": ep_occupancy_shared,
            "start-image-shared": start_image_shared}
_EXCLUSIVE = (frozenset(("ep-occupancy", "ep-occupancy-shared")),
              frozenset(("start-image", "start-image-shared")))


def apply(files: dict[str, bytes], options: tuple[str, ...] | list[str]) -> dict[str, bytes]:
    if (type(files) is not dict or not {"board.c", "tiny.h"} <= files.keys()
            or not all(type(name) is str and type(data) is bytes for name, data in files.items())):
        raise ValueError("explicit immutable D source mapping required")
    if files["tiny.h"].count(_BOARD) != 1:
        raise ValueError("fast-capacity D Board representation required")
    if (type(options) not in (tuple, list) or not all(type(name) is str for name in options)
            or len(options) != len(set(options)) or not set(options) <= VARIANTS.keys()):
        raise ValueError("explicit nonrepeated board size options required")
    if any(len(set(options) & group) > 1 for group in _EXCLUSIVE):
        raise ValueError("board size alternatives change the same owner")
    result = dict(files)
    for name in options:
        result = VARIANTS[name](result)
    return result
