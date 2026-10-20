"""Independent complete-function composition proof; no new engine policy."""

SIGNATURES=("static void go(char *s){","int main(void){")


def compose(state, ordered, minimal, order_overlay, uci):
    expected_minimal,policy=uci.transform(state,"E")
    if expected_minimal!=minimal:
        raise ValueError("qualified minimal UCI source was not reproduced")
    expected_order,ordering=order_overlay.overlay(state,"model")
    if expected_order!=ordered:
        raise ValueError("qualified model-capture-prior source was not reproduced")
    final,final_ordering=order_overlay.overlay(minimal,"model")
    if final_ordering!=ordering:
        raise ValueError("ordering policy changed during composition")
    base,old,new=state.decode(),ordered.decode(),minimal.decode()
    replacements=[]
    for signature in SIGNATURES:
        sb,se=uci.region(base,signature);ob,oe=uci.region(old,signature);mb,me=uci.region(new,signature)
        if base[sb:se]!=old[ob:oe]:
            raise ValueError("ordering component changed a UCI function")
        replacements.append((ob,oe,new[mb:me]))
    independent=old
    for begin,end,value in sorted(replacements,reverse=True):
        independent=independent[:begin]+value+independent[end:]
    if independent.encode()!=final:
        raise ValueError("two independent composition orders differ")
    protected=uci.protected_bytes(ordered)
    if uci.protected_bytes(final)!=protected:
        raise ValueError("composition changed code outside go/main")
    return final,{"policy":policy,"ordering":ordering,
        "independent_function_transplant_equal":True,
        "protected_bytes":len(protected),"protected_sha256":uci.sha(protected),
        "same_ordered_core_outside_go_main":True,
        "DEV_policy":"new capture prior with unchanged strong UCI diagnostics/control"}
