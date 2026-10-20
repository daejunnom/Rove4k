"""Two explicit TinyE forms: frozen baseline, or shipping cache removal.

The E leaf and correction residual consume tiny_raw(), but the pre-existing
tactical ordering still consumes value(). Only Board.v and its two put() updates
are conditionalized. DEV retains the exact original incremental HCE oracle.
"""
import re


SITES = (
    ("typedef struct { int8_t b[128]; int s,c,e,k[2],half,v; uint64_t h,r; } Board;",
     "typedef struct { int8_t b[128]; int s,c,e,k[2],half;\n#if DEV\nint v;\n#endif\nuint64_t h,r; } Board;"),
    ("if(old){p->h^=piece(old,q);p->v-=value(old,q);}",
     "if(old){p->h^=piece(old,q);\n#if DEV\np->v-=value(old,q);\n#endif\n}"),
    ("if(v){p->h^=piece(v,q);p->v+=value(v,q);if(abs(v)==6)p->k[v<0]=q;}",
     "if(v){p->h^=piece(v,q);\n#if DEV\np->v+=value(v,q);\n#endif\nif(abs(v)==6)p->k[v<0]=q;}"),
)


def overlay(source, form):
    if form not in ("baseline", "state"):
        raise ValueError("only baseline/state structural forms are supported")
    text = source.decode()
    # Fail on both missing expected sites and newly introduced cache consumers.
    if len(re.findall(r"\bp->v\b", text)) != 3 or "position.v" in text:
        raise ValueError("TinyE cached-HCE consumer shape changed")
    for contract in ("int evaluation=p->s*tiny_raw(p);", "int error=best-evaluation;",
                     "500000+abs(value(p->b[to],to))*16-abs(value(p->b[from],from)):",
                     "scores[i]+=tiny_order(p,m);"):
        if text.count(contract) != 1:
            raise ValueError("TinyE production consumer shape changed: " + contract)
    for before, after in SITES:
        if text.count(before) != 1:
            raise ValueError("TinyE state overlay shape changed: " + before)
        if form == "state":
            text = text.replace(before, after)
    return text.encode(), {"form": form, "exact_overlay_sites": 3 if form == "state" else 0,
        "shipping_cached_hce": form == "baseline", "dev_incremental_hce": True,
        "value_function_retained": "shipping tactical ordering consumes its exact values",
        "evaluation_ordering_and_search_changes": False}
