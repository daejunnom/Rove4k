"""Finite follow-up search experiments on the full D structural candidate.

All selectors preserve the full search policy and all promotion choices. The
caller must compare actual search observations and complete shipping costs.
The classes below are hypotheses about work, not measured speed or Elo claims.
This module performs no I/O and never applies an option implicitly.
"""
from __future__ import annotations
import re

FAST_OPTIONS = (
    "late_gen", "late_check_gen", "repetition_split", "repetition_break",
    "order_union", "root_current", "late_gen_guard", "late_check_gen_guard",
    "terminal_first", "terminal_first_late_check", "capacity413",
    "tt_decode_on_use", "mate_inline", "known_child_check",
)
SMALL_OVERHEAD_OPTIONS = ("select_helper", "ranked_select_helper")
HIGH_OVERHEAD_OPTIONS = ("order_recompute",)
OPTIONS = FAST_OPTIONS + SMALL_OVERHEAD_OPTIONS + HIGH_OVERHEAD_OPTIONS
BEST = ("terminal_first_late_check", "root_current")


def _once(data: bytes, before: bytes | str, after: bytes | str) -> bytes:
    if isinstance(before, str):
        before = before.encode()
    if isinstance(after, str):
        after = after.encode()
    if data.count(before) != 1:
        raise ValueError("unique full-D search boundary required: " + repr(before[:90]))
    return data.replace(before, after)


def _score_helper(source: bytes) -> tuple[bytes, bytes]:
    """Extract the same pure score calculation; do not read a TT twice."""
    first = source.index(b"    for(int i=0;i<count;i++){\n        Move m=moves[i];int from=FROM(m)")
    last = source.index(b"    for(int i=0;i<count;i++){\n        int j=i;", first)
    loop = source[first:last]
    body = loop.replace(b"    for(int i=0;i<count;i++){\n        Move m=moves[i];", b"")
    body = body.replace(b"scores[i]=", b"int score=").replace(b"scores[i]+=", b"score+=")
    body = _once(body, b"    }\n", b"    return score;\n}\n")
    helper = (b"static __attribute__((noinline)) int order_score(Worker *w,const Board *p,Move m,Move tt,int prior){\n"
              + body)
    return loop, helper


def runtime_dependencies(files: dict[str, bytes]) -> bytes:
    """Return the measured terminal resolver dependency for a search fixture.

    Insert after board.c and before search.c. These are the actual runtime
    function bodies, not substitutes. The finite selected bodies have no braces
    inside string literals/comments; compound literals are balanced normally.
    """
    if b"static Move first(const Board *);" not in files["search.c"]:
        return b""
    source = files["runtime.c"].decode()
    # Two separately owned token representations are supported: an immutable
    # pointer/length span or a NUL-terminated token in the input owner's line.
    # Keep the measured type and all measured consumers together.
    types = ("typedef struct{const char *p;unsigned n;} Span;", "typedef char *Span;")
    spans = [item for item in types if source.count(item) == 1]
    if len(spans) != 1 or any(source.count(item) > 1 for item in types):
        raise ValueError("one measured span or NUL-token resolver type required")
    bodies = [spans[0]]
    for name in ("text", "word", "resolve_move", "first"):
        matches = list(re.finditer(r"^static [^{\n]*\b" + name + r"\([^{}\n]*\)\s*\{", source, re.M))
        if len(matches) != 1:
            raise ValueError("unique measured runtime dependency required: " + name)
        match = matches[0]
        index, depth = match.end(), 1
        while depth and index < len(source):
            depth += (source[index] == "{") - (source[index] == "}")
            index += 1
        if depth:
            raise ValueError("unbalanced measured runtime dependency: " + name)
        bodies.append(source[match.start():index])
    return ("\n".join(bodies) + "\n").encode()


def adapt_root_observer(driver: bytes, files: dict[str, bytes]) -> bytes:
    """Connect the old fixture's root output to the actual private current slot.

    The original fixture initializes its local best to zero for each root call.
    Preserve that initial value and observe the actual slot afterward. This
    changes only the call interface; no expected result or search body changes.
    """
    if b"Move best,current;" not in files["tiny.h"]:
        return driver
    return _once(driver,
        b"Move best=0;int score=search(&fixture_worker,p,depth,-MATE,MATE,0,6,&best);",
        b"fixture_worker.current=0;int score=search(&fixture_worker,p,depth,-MATE,MATE,0,6);Move best=fixture_worker.current;")


def apply(files: dict[str, bytes], options: tuple[str, ...]) -> dict[str, bytes]:
    """Apply explicit alternatives to fresh full structural source files.

    The input contract is the existing full D cohort with previous-piece,
    unsigned-history and the first structural search BEST already applied.
    Incompatible combinations fail on their source boundaries. No runtime,
    board implementation, compiler flag or packaging policy is changed.
    """
    if isinstance(options, str):
        raise ValueError("explicit selector sequence required")
    options = tuple(options)
    if any(name not in OPTIONS for name in options) or len(set(options)) != len(options):
        raise ValueError("unique known follow-up search selectors required")
    result = dict(files)
    for name in options:
        source, header = result["search.c"], result["tiny.h"]
        if name in ("late_gen", "late_check_gen"):
            # gen() only writes its private list; a TT return consumes none of
            # it. Draw/ply-limit paths still generate and establish legality
            # before returning a draw or a mate result.
            source = _once(source, "count=gen(p,moves),legal=0", "count,legal=0")
            source = _once(source, "    if(draw||ply==PLY-1){\n        Board q;",
                           "    if(draw||ply==PLY-1){\n        count=gen(p,moves);Board q;")
            source = _once(source, "    if(depth<=0)COUNT(w,qs);",
                           "    count=gen(p,moves);\n    if(depth<=0)COUNT(w,qs);")
            if name == "late_check_gen":
                source = _once(source,
                    "int check=attacked(p,p->k[p->s<0],-p->s),draw=p->half>=100;",
                    "int check,draw=p->half>=100;")
                source = _once(source, "        return check?-MATE+ply:0;",
                    "        return attacked(p,p->k[p->s<0],-p->s)?-MATE+ply:0;")
                source = _once(source, "    count=gen(p,moves);\n    if(depth<=0)",
                    "    check=attacked(p,p->k[p->s<0],-p->s);\n    count=gen(p,moves);\n    if(depth<=0)")
        elif name in ("late_gen_guard", "late_check_gen_guard"):
            # One gen call serves both terminal and ordinary nodes. TT reads
            # remain bypassed on terminal paths, so no extra hit or publication
            # is introduced; after the terminal return all TT locals are set.
            source = _once(source, "count=gen(p,moves),legal=0", "count,legal=0")
            first = source.index(b"    if(draw||ply==PLY-1){")
            last = source.index(b"    uint64_t key=", first)
            terminal = source[first:last]
            begin = last
            end = source.index(b"    if(depth<=0)COUNT(w,qs);", begin)
            table = source[begin:end]
            table = _once(table, "    uint64_t key=", "        key=")
            table = _once(table, ",data=probe(key,0,0);", ";data=probe(key,0,0);")
            table = _once(table, "    Move tt=", "        tt=")
            table = _once(table, "    int score=", "        score=")
            table = _once(table, ",bound=(data>>41)&3,ttdepth=(data>>33)&255;",
                          ";bound=(data>>41)&3;int ttdepth=(data>>33)&255;")
            new = (b"    int terminal=draw||ply==PLY-1;\n"
                   b"    uint64_t key,data;Move tt;int score,bound;\n"
                   b"    if(!terminal){\n" + table + b"    }\n"
                   b"    count=gen(p,moves);\n" + terminal.replace(b"if(draw||ply==PLY-1)", b"if(terminal)"))
            source = _once(source, source[first:end], new)
            if name == "late_check_gen_guard":
                source = _once(source,
                    "int check=attacked(p,p->k[p->s<0],-p->s),draw=p->half>=100;",
                    "int check,draw=p->half>=100;")
                source = _once(source, "        return check?-MATE+ply:0;",
                    "        return attacked(p,p->k[p->s<0],-p->s)?-MATE+ply:0;")
                source = _once(source, "    if(depth<=0)COUNT(w,qs);",
                    "    check=attacked(p,p->k[p->s<0],-p->s);\n    if(depth<=0)COUNT(w,qs);")
        elif name in ("terminal_first", "terminal_first_late_check"):
            source = _once(source, "static int search(",
                "static Move first(const Board *);\nstatic int search(")
            source = _once(source, "count=gen(p,moves),legal=0", "count,legal=0")
            source = _once(source,
                "        Board q;\n        for(int i=0;i<count;i++)if(make(p,moves[i],&q)){",
                "        if(first(p)){")
            source = _once(source, "    if(depth<=0)COUNT(w,qs);",
                "    count=gen(p,moves);\n    if(depth<=0)COUNT(w,qs);")
            if name == "terminal_first_late_check":
                source = _once(source,
                    "int check=attacked(p,p->k[p->s<0],-p->s),draw=p->half>=100;",
                    "int check,draw=p->half>=100;")
                source = _once(source, "        return check?-MATE+ply:0;",
                    "        return attacked(p,p->k[p->s<0],-p->s)?-MATE+ply:0;")
                source = _once(source, "    count=gen(p,moves);\n    if(depth<=0)",
                    "    check=attacked(p,p->k[p->s<0],-p->s);\n    count=gen(p,moves);\n    if(depth<=0)")
            # Fail now if a different runtime resolver contract was supplied.
            runtime_dependencies({**result, "search.c": source})
        elif name == "capacity413":
            header = _once(header, "#define MOVES 432", "#define MOVES 413")
            header = _once(header,
                "/* Admission preserves <=16 pieces/side; each piece has <=27 pseudo moves,\n * including all promotions/castles, so the conservative bound is 432. */",
                "/* One admitted king has <=8 pseudo moves (home-rank castles <=5+2).\n * Each of at most 15 other pieces has <=27, including all promotions.\n * The conservative capacity bound is therefore 15*27+8=413. */")
        elif name == "tt_decode_on_use":
            # TT score is consumed only by a qualified non-root cutoff test.
            # Move ordering reads tt, while every later score use follows a
            # child return or score=best. Avoid mate conversion on TT misses,
            # shallow entries and root probes without changing any TT access.
            source = _once(source,
                "    int score=(int16_t)(data>>17),bound=(data>>41)&3,ttdepth=(data>>33)&255;\n"
                "    if(bound)COUNT(w,hits);\n"
                "    score=mate_score(score,-ply);\n"
                "    if(ply&&bound&&ttdepth>=(depth>0?depth:0)&&\n"
                "       (bound==1||(bound==2?score>=beta:score<=alpha)))return score;",
                "    int score,bound=(data>>41)&3,ttdepth=(data>>33)&255;\n"
                "    if(bound)COUNT(w,hits);\n"
                "    if(ply&&bound&&ttdepth>=(depth>0?depth:0)){\n"
                "        score=mate_score((int16_t)(data>>17),-ply);\n"
                "        if(bound==1||(bound==2?score>=beta:score<=alpha))return score;\n"
                "    }")
        elif name == "mate_inline":
            source = _once(source, "static __attribute__((noinline)) int mate_score(",
                           "static inline int mate_score(")
        elif name == "known_child_check":
            # LMR already sometimes asks whether the child gives check. Pass
            # that exact answer, but leave the cache unknown on paths which
            # never asked; do not eagerly add attacked() before a child TT hit.
            # The low four bits remain the original piece index. Mask before
            # claim/observation, ordering or either heuristic-table consumer.
            source = _once(source, "int ply,int prior", "int ply,int packed")
            source = _once(source, "    if(!claim(w))return 0;",
                           "    int prior=packed&15;\n    if(!claim(w))return 0;")
            source = _once(source, "check=attacked(p,p->k[p->s<0],-p->s)",
                           "check=packed&16?!!(packed&32):attacked(p,p->k[p->s<0],-p->s)")
            source = _once(source, "        int narrow=legal>1&&depth>0,reduce=0;\n",
                           "        int narrow=legal>1&&depth>0,reduce=0;\n        int child_check=0;\n")
            source = _once(source,
                "            reduce=depth>=4&&legal>=4&&!tactical&&!check&&!attacked(&q,q.k[q.s<0],-q.s);",
                "            reduce=depth>=4&&legal>=4&&!tactical&&!check;\n"
                "            if(reduce){child_check=16+32*!!attacked(&q,q.k[q.s<0],-q.s);reduce=!(child_check&32);}")
            source = _once(source, "ply+1,piece_index(q.b[to])", "ply+1,piece_index(q.b[to])|child_check")
        elif name == "repetition_split":
            # Each key is still visited in the same order. Select the owned
            # suffix versus immutable game prefix once per loop, not per key.
            source = _once(source,
                "    for(int i=length-3;i>=end;i-=2)\n"
                "        repetitions+=(i<game_length?game_keys[i]:w->keys[i-game_length])==p->h;",
                "    int boundary=end-game_length;if(boundary<0)boundary=0;\n"
                "    int i=ply-3;\n"
                "    for(;i>=boundary;i-=2)repetitions+=w->keys[i]==p->h;\n"
                "    for(i+=game_length;i>=end;i-=2)repetitions+=game_keys[i]==p->h;")
        elif name == "repetition_break":
            # Only the threshold >=2 is consumed. Neither array is volatile
            # and neither is modified during this node's repetition scan.
            source = _once(source,
                "        repetitions+=(i<game_length?game_keys[i]:w->keys[i-game_length])==p->h;",
                "        if((i<game_length?game_keys[i]:w->keys[i-game_length])==p->h&&++repetitions==2)break;")
        elif name == "order_union":
            source = _once(source,
                "    Move moves[MOVES],bestmove=0;",
                "    typedef struct{Move move;int score;} Ranked;\n"
                "    union{Move raw[MOVES];Ranked ranked[MOVES];} order;\n"
                "    _Static_assert(sizeof(Move)==4&&sizeof(int)==4&&sizeof(Ranked)==8&&offsetof(Ranked,score)==4,\"ranked scratch\");\n"
                "    Move bestmove=0;")
            source = _once(source, "int scores[MOVES],count", "int count")
            if not 1 <= source.count(b"gen(p,moves)") <= 2:
                raise ValueError("one generation per live branch required")
            source = source.replace(b"gen(p,moves)", b"gen(p,order.raw)")
            terminal = b"for(int i=0;i<count;i++)if(make(p,moves[i],&q))"
            if terminal in source:
                source = _once(source, terminal,
                               "for(int i=0;i<count;i++)if(make(p,order.raw[i],&q))")
            source = _once(source,
                "    for(int i=0;i<count;i++){\n        Move m=moves[i];int from=FROM(m),to=TO(m),pi=piece_index(p->b[from]);\n        scores[i]=",
                "    for(int i=count;i--;){\n        Move m=order.raw[i];int from=FROM(m),to=TO(m),pi=piece_index(p->b[from]);\n        order.ranked[i].move=m;order.ranked[i].score=")
            source = _once(source, "if(PROMO(m))scores[i]+=", "if(PROMO(m))order.ranked[i].score+=")
            source = _once(source,
                "        int j=i;for(int k=i+1;k<count;k++)if(scores[k]>scores[j])j=k;\n        Move m=moves[j];moves[j]=moves[i];\n        scores[j]=scores[i];",
                "        int j=i;for(int k=i+1;k<count;k++)if(order.ranked[k].score>order.ranked[j].score)j=k;\n        Move m=order.ranked[j].move;order.ranked[j]=order.ranked[i];")
        elif name == "root_current":
            # This worker-private field uses the original padding. Preserve
            # best publication only after an uncancelled complete iteration.
            header = _once(header, "int id,depth; Move best;", "int id,depth; Move best,current;")
            source = _once(source, "int ply,int prior,Move *root)", "int ply,int prior)")
            source = _once(source, "-alpha,ply+1,piece_index(q.b[to]),0);", "-alpha,ply+1,piece_index(q.b[to]));")
            source = _once(source, "if(root)*root=m;", "if(!ply)w->current=m;")
            source = _once(source, "Move best=w->best;", "w->current=w->best;")
            source = _once(source, "search(w,p,depth,-MATE,MATE,0,6,&best);", "search(w,p,depth,-MATE,MATE,0,6);")
            source = _once(source, "w->best=best;w->depth=depth;", "w->best=w->current;w->depth=depth;")
        elif name == "select_helper":
            old = (b"        int j=i;for(int k=i+1;k<count;k++)if(scores[k]>scores[j])j=k;\n"
                   b"        Move m=moves[j];moves[j]=moves[i];\n        scores[j]=scores[i];")
            helper = (b"static __attribute__((noinline)) Move select_move(Move *moves,int *scores,int i,int count){\n"
                      + old + b"\n    return m;\n}\n")
            source = _once(source, old, b"        Move m=select_move(moves,scores,i,count);")
            source = _once(source, "static int search(", helper + b"static int search(")
        elif name == "ranked_select_helper":
            # Pair storage reduces the helper interface to a cursor and count.
            result["search.c"], result["tiny.h"] = source, header
            ranked = apply(result, ("order_union",))
            source, header = ranked["search.c"], ranked["tiny.h"]
            typedef = b"    typedef struct{Move move;int score;} Ranked;\n"
            source = _once(source, typedef, b"")
            helper = (b"typedef struct{Move move;int score;} Ranked;\n"
                b"static __attribute__((noinline)) Move select_ranked(Ranked *order,int count){\n"
                b"    int j=0;for(int k=1;k<count;k++)if(order[k].score>order[j].score)j=k;\n"
                b"    Move move=order[j].move;order[j]=order[0];return move;\n}\n")
            source = _once(source,
                "        int j=i;for(int k=i+1;k<count;k++)if(order.ranked[k].score>order.ranked[j].score)j=k;\n        Move m=order.ranked[j].move;order.ranked[j]=order.ranked[i];",
                "        Move m=select_ranked(order.ranked+i,count-i);")
            source = _once(source, "static int search(", helper + b"static int search(")
        elif name == "order_recompute":
            # Recomputing lazily after children would read mutated history and
            # continuation, changing order. Finish the complete permutation
            # before any child search, while these score inputs are frozen.
            # This removes scores[] but performs O(n^2) expensive score calls
            # and completes ordering even when search will cut off early.
            loop, helper = _score_helper(source)
            source = _once(source, loop,
                "    for(int i=0;i<count;i++){\n"
                "        int j=i,bestscore=order_score(w,p,moves[i],tt,prior);\n"
                "        for(int k=i+1;k<count;k++){\n"
                "            int candidate=order_score(w,p,moves[k],tt,prior);\n"
                "            if(candidate>bestscore){bestscore=candidate;j=k;}\n"
                "        }\n"
                "        Move m=moves[j];moves[j]=moves[i];moves[i]=m;\n"
                "    }\n")
            source = _once(source, "int scores[MOVES],count=gen(p,moves)", "int count=gen(p,moves)")
            source = _once(source,
                "        int j=i;for(int k=i+1;k<count;k++)if(scores[k]>scores[j])j=k;\n        Move m=moves[j];moves[j]=moves[i];\n        scores[j]=scores[i];",
                "        Move m=moves[i];")
            source = _once(source, "static int search(", helper + b"static int search(")
        else:
            raise ValueError(name)
        result["search.c"], result["tiny.h"] = source, header
    return result
