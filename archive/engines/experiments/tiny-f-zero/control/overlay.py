"""Strict TinyA board/runtime overlay for a distinct full-depth MTD(f) core.

Inputs are frozen before this module runs. Hash admission is LF-normalized for
Git checkout portability; the manifest separately hashes every actual byte.
"""
import hashlib
import re

EXPECTED = {
    "tiny.h": "e209d37be5c1a8b320c45de87944ed3dc55b8c006713834ad4fd1cfb5eeae19d",
    "board-generated.c.in": "d96f3981b46c13ae152da97ecf884c0a35d81081cd3b242c659ffe39b2d74235",
    "main.c": "46e31d2cd761cab09afe537af82cec1e6941eb96bdd72b9d4455ea47ca5c6b63",
}
COUNTERS = ("f_probes", "f_lower", "f_upper", "f_converged", "f_conflicts", "f_upper_other")


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("fixed TinyF overlay changed: " + old[:80])
    return text.replace(old, new)


def transform(sources, search):
    result = {}
    for name, expected in EXPECTED.items():
        data = sources[name].replace(b"\r\n", b"\n")
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("TinyF requires the admitted TinyA input: " + name)
        result[name] = data
    header = result["tiny.h"].decode()
    header = once(header, "    uint64_t pvs,qs,hits,hist_updates,cont_updates,corr_updates,corr_uses,ply_aborts;",
                  "    uint64_t pvs,qs,hits,hist_updates,cont_updates,corr_updates,corr_uses,ply_aborts;\n    uint64_t " + ",".join(COUNTERS) + ";")
    runtime = result["main.c"].decode().replace("id name Rove4k A", "id name Rove4k F full-depth MTD")
    runtime = once(runtime, "    uint64_t pvs=0,qs=0,hits=0,hist=0,cont=0,corr=0,uses=0,aborts=0;int depth=0;",
                   "    uint64_t pvs=0,qs=0,hits=0,hist=0,cont=0,corr=0,uses=0,aborts=0;int depth=0;\n    uint64_t " + ",".join(name+"=0" for name in COUNTERS) + ";")
    runtime = once(runtime, "        pvs+=w->pvs;", "        " + "".join(name+"+=w->"+name+";" for name in COUNTERS) + "\n        pvs+=w->pvs;")
    runtime = once(runtime, 'printf("{\\\"workers\\\":%d,',
                   'printf("{' + "".join('\\\"'+name+'\\\":%llu,' for name in COUNTERS) + '\\\"workers\\\":%d,')
    runtime = once(runtime, "WORKERS,WORKERS+1,(unsigned long long)atomic_load(&searched)",
                   ",".join("(unsigned long long)"+name for name in COUNTERS) + ",WORKERS,WORKERS+1,(unsigned long long)atomic_load(&searched)")
    result["tiny.h"] = header.encode()
    result["main.c"] = runtime.encode()
    result["search.c"] = search.replace(b"\r\n", b"\n")
    return result


def strip_counters(source):
    text = source.decode()
    text, definitions = re.subn(r"(?m)^#define COUNT\(w,f\) \(\(void\)0\)\n", "", text)
    for statement in ("if(bound)COUNT(w,hits);", "if(depth<=0)COUNT(w,qs);", "if(correction)COUNT(w,corr_uses);"):
        text = once(text, statement, "")
    allowed = {"ply_aborts", "pvs", "hist_updates", "cont_updates", "corr_updates", *COUNTERS}-{"f_upper_other"}
    found = re.findall(r"COUNT\(w,(\w+)\);", text)
    if set(found) != allowed or definitions != 1:
        raise ValueError("TinyF diagnostic schema changed")
    text = re.sub(r"COUNT\(w,\w+\);", "", text)
    if "COUNT(" in text:
        raise ValueError("unexpected diagnostic expression")
    return text.encode(), {"removed_noop_counter_calls": len(found)+3,
                           "required_complete_native_byte_identity": True}


def co_design(sources):
    """Discard only dead selected prefixes; pass the actual prior piece index.

    Positive learner bonuses and a nonzero TT write marker reduce duplicate
    source state. The evaluator bound is the unchanged admitted TinyA proof.
    Every operation keeps F's exact horizons/interval/witness semantics intact.
    """
    result=dict(sources);search=result["search.c"].decode();board=result["board-generated.c.in"].decode()
    search=once(search,"Move m=moves[j];moves[j]=moves[i];moves[i]=m;\n        int t=scores[j];scores[j]=scores[i];scores[i]=t;",
                "Move m=moves[j];moves[j]=moves[i];scores[j]=scores[i];")
    search=once(search,"Move previous,Move *root)","int prior,Move *root)")
    search=once(search,"    int prior=previous?piece_index(p->b[TO(previous)]):6;\n","")
    search=once(search,"int from=FROM(m),to=TO(m),tactical=capture(p,m)||PROMO(m);",
                "int from=FROM(m),to=TO(m),tactical=capture(p,m)||PROMO(m),next=piece_index(q.b[to]);")
    if search.count(",ply+1,m,0)")!=3:raise ValueError("TinyF recursive PVS call count changed")
    search=search.replace(",ply+1,m,0)",",ply+1,next,0)")
    search=once(search,"search(w,p,depth,beta-1,beta,0,0,&move)","search(w,p,depth,beta-1,beta,0,6,&move)")
    search=once(search,"probe(uint64_t key,int write,uint64_t data)","probe(uint64_t key,uint64_t data)")
    search=once(search,"if(write)e->key=key,e->data=data;","if(data)e->key=key,e->data=data;")
    search=once(search,"data=probe(key,0,0)","data=probe(key,0)")
    search=once(search,"probe(key,1,data);","probe(key,data);")
    search=once(search,"*cell+=bonus-*cell*abs(bonus)/16384;","*cell+=bonus-*cell*bonus/16384;")
    if board.count("if(++counts[v<0]>16)return 0;")!=2:
        raise ValueError("TinyF static bound requires the fixed piece admission")
    begin=board.index("int value(");end=board.index("\n}",begin)+2
    if hashlib.sha256(board[begin:end].encode()).hexdigest()!="65505eb0dfdd40abc342bfb12b032b713c884b60976593b509ccde5656073ddb":
        raise ValueError("TinyF static bound requires the enumerated unchanged evaluator")
    search=once(search,"    if(evaluation>MATE-PLY-1)evaluation=MATE-PLY-1;\n    if(evaluation< -MATE+PLY+1)evaluation=-MATE+PLY+1;\n","")
    search="#if MATE-PLY-1<=32*910\n#error admitted HCE exceeds static bound\n#endif\n"+search
    result["search.c"]=search.encode()
    return result,{"operations":["discard_selected_prefix","pass_prior_piece","nonzero_tt_write_marker","positive_bonus","unreachable_hce_clip"],
                   "static_hce_proof":"actual pinned value <=910 in absolute value; <=16 pieces per side; 32*910 < MATE-PLY-1",
                   "policy":"same move order, node visits, learners, exact F horizons and bounds"}
