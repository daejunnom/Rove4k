"""One guarded production unit-window specialization of the frozen F control.

The private search API becomes beta-only. This is not a transformation of a
general alpha/beta search: the sole production root caller supplies beta-1,beta.
Quiescence must still find a legal move before returning standpat at a cutoff.
"""
import re


def once(text,old,new):
    if text.count(old)!=1:raise ValueError("fixed F zero-window source changed: "+old[:80])
    return text.replace(old,new)


def transform(source):
    text=source.decode()
    if text.count("static int search(")!=1 or text.count("search(")!=5:
        raise ValueError("production F search caller inventory changed")
    text=once(text,"int depth,int alpha,int beta,int ply,int prior,Move *root)",
              "int depth,int beta,int ply,int prior,Move *root)")
    text=once(text,"legal=0,old=alpha,best=-MATE;","legal=0,best=-MATE;")
    text=once(text,"(bound==3&&score<=alpha)","(bound==3&&score<beta)")
    text=once(text,"if(quiet){best=evaluation;if(best>alpha)alpha=best;}","if(quiet)best=evaluation;")
    text=once(text,"if(quiet&&(!tactical||alpha>=beta))continue;","if(quiet&&(!tactical||best>=beta))continue;")
    old='''        if(legal==1||depth<=0)score=-search(w,&q,depth-1,-beta,-alpha,ply+1,next,0);
        else{
            COUNT(w,pvs);
            score=-search(w,&q,depth-1,-alpha-1,-alpha,ply+1,next,0);
            if(score>alpha&&score<beta)score=-search(w,&q,depth-1,-beta,-alpha,ply+1,next,0);
        }'''
    new='''#if DEV
        /* Retain the nonfirst-normal-probe observation in DEV only. */
        if(legal>1&&depth>0)COUNT(w,pvs);
#endif
        score=-search(w,&q,depth-1,1-beta,ply+1,next,0);'''
    text=once(text,old,new)
    text=once(text,"        if(score>alpha)alpha=score;\n","")
    text=once(text,"if(alpha>=beta){","if(score>=beta){")
    text=once(text,"bound=best<=old?3:best>=beta?2:1;","bound=best>=beta?2:3;")
    text=once(text,"score=search(w,p,depth,beta-1,beta,0,6,&move);","score=search(w,p,depth,beta,0,6,&move);")
    if re.search(r"\b(?:alpha|old)\b",text[text.index("static int search("):text.index("void think(")]):
        raise ValueError("unexpected alpha/old state remains")
    return text.encode(),{
        "production_precondition":"sole external-to-search caller is think's integer [beta-1,beta] MTD probe",
        "integer_invariant":"a raised alpha reaches beta; QS skips recursion and normal nodes cut immediately; actual child beta is 1-beta",
        "private_api_change":"search removes alpha parameter; original wide-window fixtures are reference-only, not candidate proof",
        "tt":"same full-key coherent single-bound Entry, context, exact horizon and mate normalization",
        "bounds":"store lower=2 iff best>=beta, otherwise upper=3; exact reader compatibility retained",
        "preserved":"board/terminal/draw/ply abort/keys/learning/root lower witness/MTD interval/pool/parser unchanged",
        "dev_counter":"old nonfirst-normal-probe counter retained behind DEV; no shipping conditional",
        "shipping_pvs_calls_removed":1,
    }


def strip_candidate(source):
    text=source.decode()
    text,definitions=re.subn(r"(?m)^#define COUNT\(w,f\) \(\(void\)0\)\n","",text)
    for statement in ("if(bound)COUNT(w,hits);","if(depth<=0)COUNT(w,qs);","if(correction)COUNT(w,corr_uses);"):
        text=once(text,statement,"")
    allowed={"ply_aborts","hist_updates","cont_updates","corr_updates","f_probes","f_lower","f_upper","f_converged","f_conflicts"}
    found=re.findall(r"COUNT\(w,(\w+)\);",text)
    if set(found)!=allowed or len(found)!=len(allowed) or definitions!=1:
        raise ValueError("candidate shipping diagnostic schema changed")
    text=re.sub(r"COUNT\(w,\w+\);","",text)
    if "COUNT(" in text:raise ValueError("unexpected diagnostic call remains")
    return text.encode(),{"removed_noop_counter_calls":len(found)+3,"pvs_conditional_in_shipping":False}
