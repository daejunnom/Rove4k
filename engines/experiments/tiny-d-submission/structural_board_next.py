"""Pure follow-up board alternatives after the full PR #21 D composition.

These are explicit experiments, not selected production defaults. The input
must contain the material-signature, range-table and shared-put projection.
They preserve all move classes, their ordering, rule state and key values.
Every complete-artifact result and execution observation belongs to the caller.

Reconstruction options deliberately trade additional work for less update code.
Their temporary Board metadata is private to start/FEN/make; legality consumes
the mailbox and king squares, and all returned successful Boards are rebuilt.
The fused walk options make that legality traversal the update owner. Ordinary
attack/generation callers pass no update destination and remain read-only.
"""


def _function(data, prefix):
    if data.count(prefix) != 1:
        raise ValueError("one known D board function required: " + repr(prefix))
    start = data.index(prefix)
    opening = data.index(b"{", start)
    depth = 0
    for end in range(opening, len(data)):
        depth += (data[end] == 123) - (data[end] == 125)
        if not depth:
            return data[start:end + 1]
    raise ValueError("unclosed known D board function")


def _replace_function(files, prefix, after):
    result = dict(files)
    data = result["board.c"]
    result["board.c"] = data.replace(_function(data, prefix), after, 1)
    return result


def _edit(files, before, after, count=1):
    result = dict(files)
    if result["board.c"].count(before) != count:
        raise ValueError("expected D board role differs: " + repr(before))
    result["board.c"] = result["board.c"].replace(before, after)
    return result


def _mailbox_put(files):
    return _replace_function(files, b"static void put(", b'''static void put(Board *p,int q,int v){
    p->b[q]=(int8_t)v;
    if(abs(v)==6)p->k[v<0]=q;
}''')


def piece_pair(files, *, outlined=False):
    """Return evaluation and material weight together, sharing piece decoding."""
    attribute = b"__attribute__((noinline)) " if outlined else b""
    value = b'''typedef struct { int value; unsigned material; } PieceState;
static ''' + attribute + b'''PieceState piece_state(int v,int q){
    static const int values[7]={24576,48228,98624,65866,27124,41860,0};
    int kind=abs(v),a=values[kind],color=(q+(q>>4))&1;
    q^=v<0?112:0;
    int rank=q>>4;q^=(q>>2&17)*7;
    int center=2*(q&7)+(q>>3)-7;
    int score=(a&1023)+rank*((a>>10)&7)+center*((a>>13)-3);
    return (PieceState){v>0?score:-score,kind==6?0:1u<<(kind==2?10:kind==3?5*color:15)};
}
int value(int v,int q){return piece_state(v,q).value;}'''
    result = _replace_function(files, b"int value(", value)
    result = _replace_function(result, b"static unsigned material_piece(", b"")
    return _replace_function(result, b"static void put(", b'''static void put(Board *p,int q,int v){
    int old=p->b[q];p->b[q]=(int8_t)v;
    for(int sign=-1;sign<=1;sign+=2){
        if(old){PieceState part=piece_state(old,q);p->h^=piece(old,q);p->v+=sign*part.value;p->material+=sign*part.material;}old=v;
    }
    if(abs(v)==6)p->k[v<0]=q;
}''')


def piece_pair_outlined(files):
    return piece_pair(files, outlined=True)


def ep_outlined(files):
    # Move the rare EP trial Board out of every ordinary make stack frame.
    return _edit(files, b"static void ep(Board *p){", b"__attribute__((noinline)) static void ep(Board *p){")


def ep_guarded_outlined(files):
    # Normalization callers own the no-target check. The outlined body then
    # receives a real provisional target and still proves legal capturability.
    result = ep_outlined(files)
    result = _edit(result, b"    if(p->e<0)return;\n", b"")
    result = _edit(result, b"    ep(t);", b"    if(t->e>=0)ep(t);")
    return _edit(result, b"    ep(&t);", b"    if(t.e>=0)ep(&t);", count=2)


def inline_put(files):
    return _edit(files, b"static void put(Board *p,int q,int v){",
                 b"__attribute__((always_inline)) static inline void put(Board *p,int q,int v){")


def outline_material(files):
    return _edit(files, b"static unsigned material_piece(int v,int q){",
                 b"__attribute__((noinline)) static unsigned material_piece(int v,int q){")


def rebuild_position(files, *, fields="all"):
    """Replace some incremental maintenance with one complete mailbox scan."""
    if fields not in ("all", "hash", "evaluation"):
        raise ValueError("unknown position reconstruction")
    result = dict(files)
    if fields == "all":
        result = _mailbox_put(result)
    elif fields == "hash":
        result = _edit(result, b"p->h^=piece(old,q);", b"")
    else:
        result = _edit(result, b"p->v+=sign*value(old,q);p->material+=sign*material_piece(old,q);", b"")
    reset, update = b"", b""
    if fields in ("all", "hash"):
        reset += b"p->h=0;"
        update += b"p->h^=piece(v,q);"
        result = _edit(result, b"*t=*p;t->h^=state(p);", b"*t=*p;")
    if fields in ("all", "evaluation"):
        reset += b"p->v=0;p->material=0;"
        update += b"p->v+=value(v,q);p->material+=material_piece(v,q);"
    rebuild = b"static void rebuild(Board *p){\n    " + reset + b"\n    for(int q=0;q<128;q=q+9&~8){int v=p->b[q];if(v){" + update + b"}}\n}\n"
    result = _edit(result, b"static int walk(const Board *,Move *,int,int);",
                   rebuild + b"static int walk(const Board *,Move *,int,int);")
    result = _edit(result, b"ep(t);t->h^=state(t);", b"ep(t);rebuild(t);t->h^=state(t);")
    result = _edit(result, b"t.h^=state(&t);t.r=t.h;", b"rebuild(&t);t.h^=state(&t);t.r=t.h;", count=2)
    result = _edit(result, b"    if(kings[0]!=1||kings[1]!=1||memcmp(p->k,t.k,sizeof t.k)||p->v!=t.v||p->material!=t.material)return 0;",
                   b"    rebuild(&t);\n    if(kings[0]!=1||kings[1]!=1||memcmp(p->k,t.k,sizeof t.k)||p->v!=t.v||p->material!=t.material)return 0;")
    return result


def rebuild_hash(files):
    return rebuild_position(files, fields="hash")


def rebuild_evaluation(files):
    return rebuild_position(files, fields="evaluation")


def fused_walk_rebuild(files, *, delta=False):
    """Use the required legality scan as the complete/delta update traversal.

    In delta mode the counters describe a prefix from the child and suffix from
    the parent while walking. A legal transfer can temporarily duplicate one
    nonking piece before its origin is visited. Its bucket can reach 31, still
    within five bits; captures/promotions cannot create a second duplicate.
    No incomplete child is returned after an early king-safety rejection.
    """
    result = _mailbox_put(files)
    if delta:
        signature = b"static int walk(const Board *p,Move *moves,int sq,int s,const Board *previous,Board *updated){"
        declaration = b"static int walk(const Board *,Move *,int,int,const Board *,Board *);"
        normal_tail = b",0,0)"
        make_call = b"walk(t,0,t->k[s<0],-s,p,t)"
        build_call = b"walk(&t,0,0,0,0,&t);"
        reset = b""
        observe = b'''        int v=p->b[from];
        if(updated){
            int old=previous?previous->b[from]:0;
            if(old!=v)for(int sign=-1;sign<=1;sign+=2){
                if(old){updated->h^=piece(old,from);updated->v+=sign*value(old,from);updated->material+=sign*material_piece(old,from);}old=v;
            }
        }
        int a=v*s;if(a<=0)continue;'''
    else:
        signature = b"static int walk(const Board *p,Move *moves,int sq,int s,Board *updated){"
        declaration = b"static int walk(const Board *,Move *,int,int,Board *);"
        normal_tail = b",0)"
        make_call = b"walk(t,0,t->k[s<0],-s,t)"
        build_call = b"walk(&t,0,0,0,&t);"
        reset = b"if(updated){updated->h=0;updated->v=0;updated->material=0;}"
        observe = b'''        int v=p->b[from];
        if(updated&&v){updated->h^=piece(v,from);updated->v+=value(v,from);updated->material+=material_piece(v,from);}
        int a=v*s;if(a<=0)continue;'''
        result = _edit(result, b"*t=*p;t->h^=state(p);", b"*t=*p;")
    result = _edit(result, b"static int walk(const Board *,Move *,int,int);", declaration)
    result = _edit(result, b"static int walk(const Board *p,Move *moves,int sq,int s){\n    int n=0;",
                   signature + b"\n    int n=0;" + reset, count=2)
    result = _edit(result, b"return walk(p,0,sq,side);", b"return walk(p,0,sq,side" + normal_tail + b";")
    # Both explicit mode encodings are supported in compositions; the source
    # role still has to match exactly one admitted generation wrapper.
    targets = [target for target in (b"0", b"-1")
               if b"return walk(p,moves," + target + b",p->s);" in result["board.c"]]
    if len(targets) != 1:
        raise ValueError("one explicit generation target required")
    generation = b"return walk(p,moves," + targets[0] + b",p->s"
    result = _edit(result, generation + b");", generation + normal_tail + b";")
    result = _edit(result, b"        int a=p->b[from]*s;if(a<=0)continue;", observe, count=2)
    result = _edit(result, b"if(attacked(t,t->k[s<0],-s))return 0;", b"if(" + make_call + b")return 0;")
    result = _edit(result, b"t.h^=state(&t);t.r=t.h;", build_call + b"t.h^=state(&t);t.r=t.h;", count=2)
    result = _edit(result, b"    if(kings[0]!=1||kings[1]!=1||memcmp(p->k,t.k,sizeof t.k)||p->v!=t.v||p->material!=t.material)return 0;",
                   b"    " + build_call + b"\n    if(kings[0]!=1||kings[1]!=1||memcmp(p->k,t.k,sizeof t.k)||p->v!=t.v||p->material!=t.material)return 0;")
    return result


def fused_walk_delta(files):
    return fused_walk_rebuild(files, delta=True)


def material_by_move(files):
    """Update material only for captures/promotions, never a legal relocation.

    Bishops preserve square color on every generated diagonal step; every
    other nonpromoting piece has a square-independent weight. Castling also
    preserves all buckets. put still owns mailbox/hash/evaluation/king state.
    start has known counts; DEV FEN and verification accumulate in their
    existing construction loops. No successful make returns stale material.
    """
    result = _edit(files, b"p->material+=sign*material_piece(old,q);", b"")
    result = _edit(result,
        b"*t=*p;t->h^=state(p);t->half=abs(v)==1||target?0:p->half+1;t->e=-1;",
        b"*t=*p;t->h^=state(p);t->half=abs(v)==1||target?0:p->half+1;t->e=-1;\n    if(target)t->material-=material_piece(target,to);")
    result = _edit(result, b"if(to==p->e&&!target)put(t,to-s*16,0);",
        b"if(to==p->e&&!target){put(t,to-s*16,0);t->material-=32768;}")
    result = _edit(result, b"if(prom)v=s*prom;",
        b"if(prom){v=s*prom;t->material+=material_piece(v,to)-32768;}")
    result = _edit(result, b"Board t={0};t.s=1;t.c=15;t.e=-1;",
        b"Board t={0};t.s=1;t.c=15;t.e=-1;t.material=22*32768+4*1024+2*32+2;")
    result = _edit(result, b"put(&t,rank*16+file++,v);",
        b"int q=rank*16+file++;put(&t,q,v);t.material+=material_piece(v,q);")
    return _edit(result, b"put(&t,q,v);if(abs(v)==6)kings[v<0]++;",
        b"put(&t,q,v);t.material+=material_piece(v,q);if(abs(v)==6)kings[v<0]++;")


def material_table(files):
    return _replace_function(files, b"static unsigned material_piece(", b'''static unsigned material_piece(int v,int q){
    static const uint16_t weight[7]={0,32768,1024,0,32768,32768,0};
    int a=abs(v);
    return a==3?1u<<(5*((q+(q>>4))&1)):weight[a];
}''')


def material_by_move_loop(files):
    # Same ownership as material_by_move, with one shared weight call site
    # for captured/promoted pieces so the decoder is not duplicated/out-of-line.
    result = material_by_move(files)
    result = _edit(result, b"    if(target)t->material-=material_piece(target,to);\n", b"")
    result = _edit(result, b"{put(t,to-s*16,0);t->material-=32768;}", b"{put(t,to-s*16,0);target=-s;}")
    result = _edit(result, b"if(prom){v=s*prom;t->material+=material_piece(v,to)-32768;}", b"if(prom){v=s*prom;t->material-=32768;}")
    return _edit(result, b"    if(abs(v)==6&&abs(to-from)==2){", b'''    for(int old=target,sign=-1;sign<=1;sign+=2){
        if(old)t->material+=sign*material_piece(old,to);old=prom?v:0;
    }
    if(abs(v)==6&&abs(to-from)==2){''')


def material_put_flags(files):
    # Keep one put owner, but give it independent remove/add material flags.
    # Every relocation skips both weights; construction, captures, EP and
    # promotions explicitly request only the count changes they actually own.
    result = _replace_function(files, b"static void put(", b'''static void put(Board *p,int q,int v,unsigned material){
    int old=p->b[q];p->b[q]=(int8_t)v;
    for(int sign=-1;sign<=1;sign+=2){
        if(old){p->h^=piece(old,q);p->v+=sign*value(old,q);if(material&1)p->material+=sign*material_piece(old,q);}old=v;material>>=1;
    }
    if(abs(v)==6)p->k[v<0]=q;
}''')
    for before, after in (
        (b"put(t,to-s*16,0);", b"put(t,to-s*16,0,1);"),
        (b"put(t,rook,0);put(t,transit,s*4);", b"put(t,rook,0,0);put(t,transit,s*4,0);"),
        (b"put(t,from,0);put(t,to,v);", b"put(t,from,0,!!prom);put(t,to,v,!!target|2*!!prom);"),
        (b"put(&t,f,back[f]);put(&t,16+f,1);put(&t,96+f,-1);put(&t,112+f,-back[f]);",
         b"put(&t,f,back[f],2);put(&t,16+f,1,2);put(&t,96+f,-1,2);put(&t,112+f,-back[f],2);"),
        (b"put(&t,rank*16+file++,v);", b"put(&t,rank*16+file++,v,2);"),
        (b"put(&t,q,v);", b"put(&t,q,v,2);"),
    ):
        result = _edit(result, before, after)
    return result


def castle_empty_ray(files):
    # Rights imply valid home/rook endpoints; the short ray visits precisely
    # the original two kingside or three queenside empty squares in order.
    return _edit(files, b'''                for(int d=1;d>=-1;d-=2)
                    if((rights&(d>0?1:2))&&!p->b[home+d]&&!p->b[home+2*d]&&(d>0||!p->b[home-3])&&!attacked(p,home+d,-s))add(moves,&n,from,home+2*d,0);''', b'''                for(int d=1;d>=-1;d-=2)if(rights&(d>0?1:2)){
                    int rook=home+(d>0?3:-4),q=home+d;
                    while(q!=rook&&!p->b[q])q+=d;
                    if(q==rook&&!attacked(p,home+d,-s))add(moves,&n,from,home+2*d,0);
                }''', count=2)


def mode_target_sentinel(files):
    # Generation uses an impossible board destination. Thus destination equality
    # alone is the attack success test; no per-square output-pointer test is
    # needed. Every ordinary attack query remains an admitted onboard square.
    result = _edit(files, b"return walk(p,moves,0,p->s);", b"return walk(p,moves,-1,p->s);")
    return _edit(result, b"if(!moves&&to==sq)return 1;", b"if(to==sq)return 1;", count=3)


def mode_sign_sentinel(files):
    result = mode_target_sentinel(files)
    for before, after, count in (
        (b"if(moves&&a==1)", b"if(sq<0&&a==1)", 2),
        (b"(moves&&a==1&&!target&&to!=p->e)", b"(sq<0&&a==1&&!target&&to!=p->e)", 2),
        (b"if(moves&&p->b[to]*s<=0)", b"if(sq<0&&p->b[to]*s<=0)", 1),
        (b"if(moves)add(", b"if(sq<0)add(", 2),
        (b"if(moves&&a==6)", b"if(sq<0&&a==6)", 2),
    ):
        result = _edit(result, before, after, count=count)
    return result


VARIANTS = {
    "piece-pair": piece_pair,
    "piece-pair-outlined": piece_pair_outlined,
    "ep-outlined": ep_outlined,
    "ep-guarded-outlined": ep_guarded_outlined,
    "inline-put": inline_put,
    "outline-material": outline_material,
    "rebuild-position": rebuild_position,
    "rebuild-hash": rebuild_hash,
    "rebuild-evaluation": rebuild_evaluation,
    "fused-walk-rebuild": fused_walk_rebuild,
    "fused-walk-delta": fused_walk_delta,
    "material-by-move": material_by_move,
    "material-by-move-loop": material_by_move_loop,
    "material-put-flags": material_put_flags,
    "material-table": material_table,
    "castle-empty-ray": castle_empty_ray,
    "mode-target-sentinel": mode_target_sentinel,
    "mode-sign-sentinel": mode_sign_sentinel,
}


def apply(files, options):
    if type(files) is not dict or not {"tiny.h", "board.c"} <= files.keys() or not all(type(data) is bytes for data in files.values()):
        raise ValueError("explicit immutable D source mapping required")
    if type(options) not in (tuple, list) or len(set(options)) != len(options) or not set(options) <= VARIANTS.keys():
        raise ValueError("explicit nonrepeated board follow-up options required")
    result = dict(files)
    for name in options:
        result = VARIANTS[name](result)
    return result
