"""One TinyE ordering-policy change over the shipping-cache-removal form.

tiny_order already consumes the model's victim/attacker material coefficients.
Drop only the duplicate legacy HCE/PST capture prior. This changes ordering,
subsequent LMR and learning; it is not a lossless source transformation.
"""

OLD = "500000+abs(value(p->b[to],to))*16-abs(value(p->b[from],from)):"
NEW = "500000:"
VALUE = """int value(int v,int q){
    static const int material[7]={0,100,320,330,500,900,0};
    int a=abs(v),rank=q>>4,file=q&7,advance=v>0?rank:7-rank;
    int center=7-abs(2*file-7)-abs(2*rank-7);
    int score=material[a]+advance*(a==1?7:a==4?2:0)+
        center*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);
    return v>0?score:-score;
}"""


def overlay(source, form):
    if form not in ("control", "model"):
        raise ValueError("only control/model ordering forms are supported")
    text = source.decode()
    for site in (OLD, VALUE, "scores[i]+=tiny_order(p,m);",
                 "int evaluation=p->s*tiny_raw(p);", "int error=best-evaluation;"):
        if text.count(site) != 1:
            raise ValueError("TinyE ordering consumer shape changed: " + site)
    if form == "model":
        text = text.replace(OLD, NEW)
        text = text.replace(VALUE, "#if DEV\n" + VALUE + "\n#endif")
    return text.encode(), {"form": form, "policy_change": form == "model",
        "capture_base": "500000 + legacy HCE/PST MVV/LVA" if form == "control" else "500000",
        "model_order_prediction": "unchanged exact five-weight sum on every move",
        "model_leaf": "unchanged exact sixteen-weight evaluation and clamp",
        "dev_incremental_hce": True,
        "shipping_legacy_hce_function": form == "control",
        "possible_effects": ["capture ordering", "search nodes and result", "LMR eligibility and learning"] if form == "model" else []}
