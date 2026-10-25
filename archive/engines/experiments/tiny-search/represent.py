"""Independent fixed-shape search representations for the optional tiny A core.

The canonical tiny-A files remain unchanged. These experiments require the
readable fixed API and reject an unfamiliar source rather than edit generated C.
"""
from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError("fixed search expression changed: " + before[:72])
    return text.replace(before, after)


def apply(sources, choices):
    result = dict(sources)
    search = result["search.c"].decode()
    header = result["tiny.h"].decode()
    for choice in choices:
        if choice == "discard":
            # The selected prefix is never read again. Keep the exact remaining
            # order of the original selection sort, including equal scores.
            search = once(search,
                "Move m=moves[j];moves[j]=moves[i];moves[i]=m;\n"
                "        int t=scores[j];scores[j]=scores[i];scores[i]=t;",
                "Move m=moves[j];moves[j]=moves[i];scores[j]=scores[i];")
        elif choice == "loop":
            begin = search.index("        if(legal==1||depth<=0)score=-search(")
            end = search.index("        --w->length;", begin)
            search = search[:begin] + (HERE / "pvs_loop.c.in").read_text() + search[end:]
        elif choice == "trial":
            search = once(search, "Move previous,Move *root)", "Move previous)")
            search = once(search, "if(root)*root=m;", "if(!ply)w->trial=m;")
            calls = search.count(",ply+1,m,0)")
            if calls not in (1, 4):
                raise ValueError("unexpected recursive call count")
            search = search.replace(",ply+1,m,0)", ",ply+1,m)")
            search = once(search, "Move best=w->best;", "w->trial=w->best;")
            search = once(search, "0,0,&best);", "0,0);")
            search = once(search, "w->best=best;w->score=score;", "w->best=w->trial;w->score=score;")
            header = once(header, "int id,depth,score; Move best;", "int id,depth,score; Move best,trial;")
        elif choice == "prior":
            search = once(search, "Move previous)", "int prior)") if "trial" in choices else once(search, "Move previous,Move *root)", "int prior,Move *root)")
            search = once(search, "    int prior=previous?piece_index(p->b[TO(previous)]):6;\n", "")
            search = once(search,
                "int from=FROM(m),to=TO(m),tactical=capture(p,m)||PROMO(m);",
                "int from=FROM(m),to=TO(m),tactical=capture(p,m)||PROMO(m),next=piece_index(q.b[to]);")
            search = search.replace(",ply+1,m", ",ply+1,next")
            search = once(search, "search(w,p,depth,-MATE,MATE,0,0);" if "trial" in choices else "search(w,p,depth,-MATE,MATE,0,0,&best);",
                          "search(w,p,depth,-MATE,MATE,0,6);" if "trial" in choices else "search(w,p,depth,-MATE,MATE,0,6,&best);")
        elif choice == "packed":
            search = once(search, "int scores[MOVES],count=gen(p,moves),legal=0,old=alpha,best=-MATE;",
                          "uint64_t scores[MOVES];int count=gen(p,moves),legal=0,old=alpha,best=-MATE;")
            search = once(search, "scores[i]=m==tt?", "int order=m==tt?")
            search = once(search,
                "if(PROMO(m))scores[i]+=400000+PROMO(m)*1000;",
                "if(PROMO(m))order+=400000+PROMO(m)*1000;\n"
                "        scores[i]=((uint64_t)order<<17)|m;")
            search = once(search, "if(scores[k]>scores[j])j=k;", "if((scores[k]>>17)>(scores[j]>>17))j=k;")
            search = once(search,
                "Move m=moves[j];moves[j]=moves[i];moves[i]=m;\n"
                "        int t=scores[j];scores[j]=scores[i];scores[i]=t;",
                "Move m=scores[j]&131071;scores[j]=scores[i];")
        elif choice == "bounded-eval":
            # Admission keeps at most 16 pieces of each colour. Exhaustive
            # evaluation of value(piece,square) gives abs(value)<=910, hence
            # abs(incremental HCE)<=32*910=29120. For this admitted ply/mate
            # profile the static clamp is unreachable. No mate score is clipped
            # here, and the correction error's actual 256 clamp stays intact.
            board = next(data.decode() for name,data in result.items() if name.startswith('board'))
            if board.count('if(++counts[v<0]>16)return 0;') != 2 or '#define MATE 30000' not in header:
                raise ValueError('bounded HCE requires actual 16-per-colour admission')
            begin=board.index('int value(');end=board.index('\n}',begin)+2
            if hashlib.sha256(board[begin:end].encode()).hexdigest()!='65505eb0dfdd40abc342bfb12b032b713c884b60976593b509ccde5656073ddb':
                raise ValueError('bounded HCE requires the exhaustively checked piece-square evaluator')
            search = once(search,
                '    if(evaluation>MATE-PLY-1)evaluation=MATE-PLY-1;\n'
                '    if(evaluation< -MATE+PLY+1)evaluation=-MATE+PLY+1;\n', '')
            search = '#if MATE-PLY-1<=32*910\n#error admitted HCE exceeds static bound\n#endif\n' + search
        else:
            raise ValueError("unknown search representation: " + choice)
    result["search.c"] = search.encode()
    result["tiny.h"] = header.encode()
    return result
