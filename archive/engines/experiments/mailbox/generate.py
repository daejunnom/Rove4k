#!/usr/bin/env python3
"""Controlled A mailbox/update experiment over a pinned canonical C input.

This transforms source, not an engine's wire protocol or index adapter. Both
layouts have their own stored squares, ray/knight steps and recursive updates.
Unexpected source drift fails generation rather than silently dropping work.
"""
from pathlib import Path
import hashlib
import re


INPUTS = ("rove.h", "board.c", "search.c", "main.c", "parallel.h", "model.h")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"canonical source drift: expected one {old[:90]!r}, got {text.count(old)}")
    return text.replace(old, new)


def geometry(layout):
    if layout == "0x88":
        body = """
#define MB_SIZE 128
#define STRIDE 16
#define SQ(r,f) ((r)*16+(f))
#define RANK(q) ((q)>>4)
#define FILE_OF(q) ((q)&7)
#define SQ_OK(q) (((q)&0x88)==0)
#define KNIGHT_STEPS {33,31,18,14,-14,-18,-31,-33}
#define RAY_STEPS {1,-1,16,-16,17,15,-15,-17}
"""
    elif layout == "10x12":
        body = """
#define MB_SIZE 120
#define STRIDE 10
#define SQ(r,f) (21+(r)*10+(f))
#define RANK(q) ((q)/10-2)
#define FILE_OF(q) ((q)%10-1)
#define SQ_OK(q) ((q)>=21&&(q)<=98&&(q)%10>=1&&(q)%10<=8)
#define KNIGHT_STEPS {21,19,12,8,-8,-12,-19,-21}
#define RAY_STEPS {1,-1,10,-10,11,9,-9,-11}
"""
    else:
        raise ValueError(layout)
    # Normalize the physical square in the original Zobrist and worker tie
    # domains. Otherwise a layout change would also change TT collisions/order.
    return body + """
#define Q88(q) (RANK(q)*16+FILE_OF(q))
#define NORMAL_MOVE(m) MOVE(Q88(FROM(m)),Q88(TO(m)),PROM(m))
"""


def board_geometry(text):
    text = text.replace("{33,31,18,14,-14,-18,-31,-33}", "KNIGHT_STEPS")
    text = text.replace("{1,-1,16,-16,17,15,-15,-17}", "RAY_STEPS")
    # The original square domains for the random keys remain unchanged.
    text = text.replace("pieces[(v>0?v-1:5-v)][q]", "pieces[(v>0?v-1:5-v)][Q88(q)]")
    text = text.replace("pieces[old>0?old-1:5-old][q]", "pieces[old>0?old-1:5-old][Q88(q)]")
    text = text.replace("pieces[v>0?v-1:5-v][q]", "pieces[v>0?v-1:5-v][Q88(q)]")
    text = text.replace("if(q&0x88){q+=7;continue;}", "if(!SQ_OK(q))continue;")
    text = text.replace("if(from&0x88){from+=7;continue;}", "if(!SQ_OK(from))continue;")
    text = text.replace("for(int q=0;q<128;q++){if(!SQ_OK(q))", "for(int q=0;q<MB_SIZE;q++){if(!SQ_OK(q))")
    text = text.replace("for(int from=0;from<128;from++)", "for(int from=0;from<MB_SIZE;from++)")
    text = text.replace("(from|to)&0x88", "(!SQ_OK(from)||!SQ_OK(to))")
    for var in ("q", "to"):
        text = text.replace(f"!({var}&0x88)", f"SQ_OK({var})")
    for var in ("FROM(m)", "TO(m)", "p->ep", "to", "from", "q"):
        text = text.replace(f"({var}>>4)", f"RANK({var})")
        text = text.replace(f"{var}>>4", f"RANK({var})")
        text = text.replace(f"({var}&7)", f"FILE_OF({var})")
        text = text.replace(f"{var}&7", f"FILE_OF({var})")
    text = text.replace("rank*16+file++", "SQ(rank,file++)")
    text = text.replace("r*16+f", "SQ(r,f)")
    text = text.replace("side*16", "side*STRIDE")
    text = text.replace("abs(to-from)==32", "abs(to-from)==2*STRIDE")
    text = text.replace("side>0?4:116", "side>0?SQ(0,4):SQ(7,4)")
    for numeric, square in ((116, "SQ(7,4)"), (119, "SQ(7,7)"), (112, "SQ(7,0)")):
        text = re.sub(rf"\b{numeric}\b", square, text)
    for numeric, square in ((4, "SQ(0,4)"), (7, "SQ(0,7)"), (0, "SQ(0,0)")):
        for left in ("from", "to"):
            text = text.replace(f"{left}=={numeric}", f"{left}=={square}")
        text = text.replace(f"t.b[{numeric}]", f"t.b[{square}]")
    if "0x88" in text or "*16" in text or "&7" in text:
        raise ValueError("unconverted board geometry: " + "; ".join(line for line in text.splitlines() if any(x in line for x in ("0x88", "*16", "&7"))))
    return text


UNDO_DECL = """
/* Only changed squares and reversible metadata are saved. Bitboards, pawn key,
 * material and HCE are restored by reversing put; no hidden Board copy. */
typedef struct {
    int side,castle,ep,half,full,king[2];
    uint64_t key;
    unsigned char count,square[4];
    int value[4];
} Undo;
int make_inplace(Board *,unsigned,Undo *);
void unmake(Board *,const Undo *);
"""


def inplace_board(text):
    start = text.index("int make_move(const Board *p,unsigned m,Board *t){")
    end = text.index("static void add(", start)
    reference = text[start:end].replace("int make_move(", "int copy_reference(")
    # Validate all potentially failing conditions before altering the board.
    # Legality after make is the sole post-update failure and rolls back.
    replacement = """static void save_square(Board *p,Undo *u,int q,int v){
    if(u->count==4)abort();
    u->square[u->count]=(unsigned char)q;u->value[u->count++]=p->b[q];put(p,q,v);
}
void unmake(Board *p,const Undo *u){
    for(int i=u->count;i-->0;)put(p,u->square[i],u->value[i]);
    p->side=u->side;p->castle=u->castle;p->ep=u->ep;p->half=u->half;p->full=u->full;
    p->king[0]=u->king[0];p->king[1]=u->king[1];p->key=u->key;
}
int make_inplace(Board *p,unsigned m,Undo *u){
    int from=FROM(m),to=TO(m),prom=PROM(m),side=p->side;
    if(!SQ_OK(from)||!SQ_OK(to))return 0;
    int v=p->b[from],target=p->b[to],pawn=abs(v)==1;
    if(!v||v*side<0||target*side>0||abs(target)==6)return 0;
    int capture_ep=pawn&&to==p->ep&&!target;
    if(capture_ep&&p->b[to-side*STRIDE]!=-side)return 0;
    if(pawn&&(RANK(to)==0||RANK(to)==7)){if(prom<2||prom>5)return 0;}
    else if(prom)return 0;
    int castle=abs(v)==6&&abs(to-from)==2;
    int rfrom=to>from?from+3:from-4,rto=to>from?from+1:from-1;
    if(castle&&(p->b[rfrom]!=side*4||in_check(p)||attacked(p,rto,-side)))return 0;
    *u=(Undo){.side=side,.castle=p->castle,.ep=p->ep,.half=p->half,.full=p->full,
        .king={p->king[0],p->king[1]},.key=p->key};
    int oldep=ep_file(p);p->key^=rights[p->castle]^(oldep<0?0:eps[oldep]);
    p->half++;p->ep=-1;if(side<0)p->full++;
    if(pawn){p->half=0;if(capture_ep)save_square(p,u,to-side*STRIDE,0);
        if(abs(to-from)==2*STRIDE)p->ep=from+side*STRIDE;
        if(prom)v=side*prom;}
    if(target)p->half=0;
    if(castle){save_square(p,u,rfrom,0);save_square(p,u,rto,side*4);}
    save_square(p,u,from,0);save_square(p,u,to,v);
    if(from==SQ(0,4))p->castle&=~3;if(from==SQ(7,4))p->castle&=~12;
    if(from==SQ(0,0)||to==SQ(0,0))p->castle&=~2;if(from==SQ(0,7)||to==SQ(0,7))p->castle&=~1;
    if(from==SQ(7,0)||to==SQ(7,0))p->castle&=~8;if(from==SQ(7,7)||to==SQ(7,7))p->castle&=~4;
    p->side=-side;p->key^=turn^rights[p->castle];int e=ep_file(p);if(e>=0)p->key^=eps[e];
    if(attacked(p,p->king[side<0],-side)){unmake(p,u);return 0;}
    return 1;
}
int make_move(const Board *p,unsigned m,Board *t){*t=*p;Undo u;return make_inplace(t,m,&u);}
"""
    text = text[:start] + replacement + "\n#if ROVE_DEV\n" + reference + "#endif\n" + text[end:]
    old = "uint64_t perft(const Board *p,int depth){if(!depth)return 1;Move m[MAXMOVES];int n=generate(p,m,0);uint64_t nodes=0;for(int i=0;i<n;i++){Board t;if(make_move(p,m[i].m,&t))nodes+=perft(&t,depth-1);}return nodes;}"
    new = """static uint64_t perft_inplace(Board *p,int depth){if(!depth)return 1;Move m[MAXMOVES];int n=generate(p,m,0);uint64_t nodes=0;for(int i=0;i<n;i++){Undo u;if(make_inplace(p,m[i].m,&u)){nodes+=perft_inplace(p,depth-1);unmake(p,&u);}}return nodes;}
uint64_t perft(const Board *p,int depth){Board root=*p;return perft_inplace(&root,depth);}"""
    return replace_once(text, old, new)


def inplace_search(text):
    text = replace_once(text, "static int qsearch(Worker *w,const Board *p,", "static int qsearch(Worker *w,Board *p,")
    text = replace_once(text, "int search(Worker *w,const Board *p,", "int search(Worker *w,Board *p,")
    old = "Board t;if(!make_move(p,m,&t))continue;w->path[w->path_len++]=t.key;w->previous[ply]=m;int s=-qsearch(w,&t,-beta,-alpha,ply+1);w->path_len--;"
    new = "Undo undo;if(!make_inplace(p,m,&undo))continue;w->path[w->path_len++]=p->key;w->previous[ply]=m;int s=-qsearch(w,p,-beta,-alpha,ply+1);w->path_len--;unmake(p,&undo);"
    text = replace_once(text, old, new)
    old = "Board t;if(!make_move(p,m,&t))continue;\n        int quiet=!is_capture(p,m);w->previous[ply]=m;w->path[w->path_len++]=t.key;"
    new = "int quiet=!is_capture(p,m);Undo undo;if(!make_inplace(p,m,&undo))continue;\n        w->previous[ply]=m;w->path[w->path_len++]=p->key;"
    text = replace_once(text, old, new)
    start = text.index("int search(Worker *w,Board *p,")
    end = text.index("static void info(", start)
    function = text[start:end].replace("search(w,&t,", "search(w,p,").replace("in_check(&t)", "in_check(p)")
    function = replace_once(function, "w->path_len--;if(w->aborted", "w->path_len--;unmake(p,&undo);if(w->aborted")
    text = text[:start] + function + text[end:]
    # Loose workers used to share a const root. Mutable search must own its
    # root before recursing; no shared Session.board mutation is permitted.
    text = replace_once(text, "if(!task->first){score=search(w,&s->board,", "if(!task->first){Board root=s->board;score=search(w,&root,")
    return text


def generate(inputs, layout, update):
    files = {name: data.decode("utf-8").replace("\r\n", "\n") for name, data in inputs.items()}
    h = files["rove.h"]
    h = replace_once(h, "typedef struct {\n    int b[128]", geometry(layout) + f"\n#define MB_UNMAKE {int(update == 'unmake')}\n" + "\ntypedef struct {\n    int b[MB_SIZE]")
    h = h.replace("int history[2][128][128]", "int history[2][MB_SIZE][MB_SIZE]")
    b = board_geometry(files["board.c"])
    s = files["search.c"]
    s = s.replace("for(int q=0;q<128;q++){if(q&0x88){q+=7;continue;}", "for(int q=0;q<MB_SIZE;q++){if(!SQ_OK(q))continue;")
    s = s.replace("((from>>4)*8+(from&7))", "(RANK(from)*8+FILE_OF(from))")
    s = s.replace("m*(unsigned)(w->id*17+13)", "NORMAL_MOVE(m)*(unsigned)(w->id*17+13)")
    if update == "unmake":
        h = replace_once(h, "typedef struct { unsigned m; int score; } Move;", UNDO_DECL + "\ntypedef struct { unsigned m; int score; } Move;")
        h = h.replace("int search(Worker *,const Board *", "int search(Worker *,Board *")
        b, s = inplace_board(b), inplace_search(s)
    elif update != "copy":
        raise ValueError(update)
    else:
        b += "\n#if ROVE_DEV\nint copy_reference(const Board *p,unsigned m,Board *t){return make_move(p,m,t);}\n#endif\n"
    h = replace_once(h, "int make_move(const Board *,unsigned,Board *);", "int make_move(const Board *,unsigned,Board *);\n#if ROVE_DEV\nint copy_reference(const Board *,unsigned,Board *);\n#endif")
    files.update({"rove.h": h, "board.c": b, "search.c": s})
    # The selected experiment is strictly A; other variant-only geometry is
    # deliberately retained behind preprocessor guards, never built as B-F.
    return {name: data.encode() for name, data in files.items()}
