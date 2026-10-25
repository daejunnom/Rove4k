"""Finite unselected spelling experiments after the current full projections.

The exact input pins name phase-init A/C/E/F and final-lf B.  They are
admission boundaries, not historical production inputs: the checker freshly
regenerates each input from the maintained canonical producer and replays its
resource/post/model chain. No default producer consumes this module.
"""
from hashlib import sha256
import re

SCHEMA = "rove4k.selected-spelling-experiment.v1"
VARIANTS = ("launcher-short", "positive-history", "ack-merge", "clock-type",
            "protocol-prefix", "atomic-assignment", "null-zero", "format-loop")
INPUTS = {
 ("A","tcec-provisional"):(7723,"2303b2dbf1a033d252d7530d9f594ded64e36d34d628156c413c98bf9b941e5a"),
 ("A","test-p28"):(7754,"8c95c00ef0dccf7bae64cffb17487b768aed950c7276dd4d6f718f2ff62b3d3d"),
 ("A","test-p4"):(7721,"a70850f6db48f8d1e95527cc99b1abadad5d46c159c3c57ffbb3065c002944f6"),
 ("B","tcec-provisional"):(8011,"1b9d41a84c8d4e5a3b3771b17cbcb452c4770fda407b5288bc447ede659518a9"),
 ("B","test-p28"):(8037,"ea16616b1b57231c44acd029a72721087617a92d323136fb639452a694fdce54"),
 ("B","test-p4"):(8009,"750b47aa14234247e07fd6b609a1dc6e6ac90b3cfab471662de8709b893e4144"),
 ("C","tcec-provisional"):(8346,"639b7956bf3f35528bc40b24780fb2ab5a45efd8af6fe1dfa6b8c255c79a9592"),
 ("C","test-p28"):(8377,"6faa52ace32571299ef96543c2c1d30d92be6baa7d11c18bed7aba4acced3f6f"),
 ("C","test-p4"):(8344,"78c080b80d79cf9d44fd08e25703ba47938877ea021c966603c61b483d47a3ea"),
 ("E","tcec-provisional"):(7914,"5d12f933263e38b192c2aa932040dc54ab57c9f571a34007767b36d541353b1e"),
 ("E","test-p28"):(7945,"a231d0c46a43d152c99df2ac3d8d1fde493f75b2f0398473b0cf06232e216603"),
 ("E","test-p4"):(7912,"cd3653843abd14882004339410db9294dd0b797dbce6de7d615c8b0ec0862027"),
 ("F","tcec-provisional"):(7151,"ae5f2148544f290a4bf39074e2077918b7f8d4e0d5beed1764c6a1f6d46cd6a2"),
 ("F","test-p28"):(7182,"d78f49121ba2f7bb072bfbb0dcb015b728266e504a7e690c26e25e306bebe757"),
 ("F","test-p4"):(7149,"6fef41e82139101f9bb42287df348ba1e045f8169abc28c893cd2a396ae56f73"),
}
CONTEXT = {
 "A":dict(integer="L",ret="J",st="static",token="g",signed="qp",hist="zC",cont="an",corr="ah",learn="O"),
 "B":dict(integer="I",ret="l",st="J",token="d",signed="int16_t",hist="h",cont="c",corr="f",learn="F"),
 "C":dict(integer="int",ret="return",st="static",token="g",signed="X",hist="zC",cont="an",corr="ah",learn="O"),
 "E":dict(integer="L",ret="J",st="static",token="g",signed="X",hist="zC",cont="an",corr="ah",learn="O"),
 "F":dict(integer="S",ret="H",st="aa",token="l",signed="zc",hist="h",cont="i",corr="j",learn="an"),
}

def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())

def require(value, detail):
    if not value:
        raise ValueError(detail)

def token_spans(text):
    """Only C identifiers; string/character literals and comments are protected."""
    pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/|[A-Za-z_][A-Za-z_0-9]*'
    return [m for m in re.finditer(pattern, text)
            if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", m.group())]

def available(family):
    variants = ["positive-history", "ack-merge"]
    if family != "B":
        variants += ["launcher-short", "clock-type", "protocol-prefix", "null-zero"]
    variants.append("atomic-assignment")
    if family in "ABCE":
        variants.append("format-loop")
    return tuple(v for v in VARIANTS if v in variants)

def transform_source(source, *, family, profile_id, variant):
    require(type(source) is bytes and INPUTS.get((family,profile_id)) ==
            (len(source),sha256(source).hexdigest()), "exact selected full input required")
    require(variant in available(family), "explicit applicable one-factor candidate required")
    text, c = source.decode("ascii"), CONTEXT[family]
    edits = []
    def change(before, after, role):
        require(text.count(before) == 1, "unique candidate span required: " + role)
        edits.append((text.index(before), before, after, role))
    def tokens(before, after, role):
        spans=token_spans(text)
        require(after not in {m.group() for m in spans}, "candidate token collision")
        found=[m for m in spans if m.group()==before]
        require(found, "candidate token absent")
        edits.extend((m.start(),before,after,role) for m in found)
    integer, ret = c["integer"], c["ret"]
    scope = "C abstract-machine spelling; complete mandatory and optional I/O retained"
    if variant == "launcher-short":
        tokens("rv_spawn","J" if family=="F" else "rv","private-launcher-name")
    elif variant == "positive-history":
        h,k,a,s = c["hist"],c["cont"],c["corr"],c["signed"]
        before=f"{s} {h}[128][128],{k}[13][13],{a}[1024];"
        after=f"uint16_t {h}[128][128],{k}[13][13];{s} {a}[1024];"
        change(before,after,"positive-table-types-layout-preserved")
        expr="*a+=d-*a*d/16384;" if family=="F" else "*a+=(d-*a*d/16384);"
        before=f"{c['st']} void {c['learn']}({s}*a,{integer} d){{{expr}}}"
        after=f"{c['st']} void {c['learn']}(uint16_t*a,unsigned d){{{expr}}}"
        change(before,after,"positive-only-learner")
        scope=("reachable BSS-zero history/continuation with only depth-squared positive updates; "
               "depth 1..126, bonus<=15876, cells0..16384, product<=260112384; "
               "signed correction, worker layout and all consumers unchanged")
    elif variant == "ack-merge":
        t=c["token"]; iff="W" if family=="B" else "if"
        condition=(f"*{t}=='i'" if family=="B" else f'!strcmp({t},"isready")')
        before=(f'{iff}(!strcmp({t},"uci")){{puts("uciok");fflush(stdout);}}else '
                f'{iff}({condition}){{puts("readyok");fflush(stdout);}}')
        after=(f'{iff}(!strcmp({t},"uci")||{condition})'
               f'{{puts(*{t}==\'u\'?"uciok":"readyok");fflush(stdout);}}')
        change(before,after,"shared-ack-output")
    elif variant == "clock-type":
        change('(!strcmp(t+1,"time")||!strcmp(t+1,"inc"))',
               "(t[1]=='t'||t[1]=='i')","valid-clock-token-kind")
        scope="valid TCEC go clock tokens; bare-go fallback unchanged; unrelated optional commands unchanged"
    elif variant == "protocol-prefix":
        t=c["token"]
        for command,condition in (("isready",f"*{t}=='i'"),("quit",f"*{t}=='q'"),
                                  ("position",f'!strncmp({t},"pos",3)'),("go",f"*{t}=='g'")):
            change(f'!strcmp({t},"{command}")',condition,"valid-command-"+command)
        scope=("TCEC mandatory exact command domain; ucinewgame/setoption/stop/ponderhit/debug/register "
               "remain ignored with no false GO; pos prefix distinguishes ponderhit")
    elif variant == "atomic-assignment":
        stop={"A":"X","B":"qp","C":"qp","E":"qp","F":"V"}[family]
        require(f"atomic_int {stop};" in text,"pinned stop object must remain atomic_int")
        spans=list(re.finditer(r"atomic_store\(&"+stop+r",([01])\);",text))
        require(len(spans)==(5 if family in "BF" else 4),"pinned standalone atomic stores differ")
        for match in spans:
            edits.append((match.start(),match.group(),stop+"="+match.group(1)+";",
                          "implicit-seq-cst-atomic-assignment"))
        scope="C11 atomic_int standalone assignment retains sequentially consistent stores; explicit relaxed/acquire/release operations unchanged"
    elif variant == "null-zero":
        spans=[m for m in token_spans(text) if m.group()=="NULL"]
        require(spans,"NULL token absent")
        edits.extend((m.start(),"NULL","0","null-pointer-constant") for m in spans)
    elif variant == "format-loop":
        iff="W" if family=="B" else "if"
        before=(f'{iff}(!m){{strcpy(s,"0000");{ret};}}'
                "s[0]='a'+(FROM(m)&7);s[1]='1'+(FROM(m)>>4);"
                "s[2]='a'+(TO(m)&7);s[3]='1'+(TO(m)>>4);")
        loop="X" if family=="B" else "for"
        after=(f"{loop}({integer} i=0;i<4;i++)s[i]=m?(i&1?'1':'a')+"
               "((m>>(i/2*7+(i&1)*4))&7):'0';")
        change(before,after,"complete-coordinate-output-loop")
    edits.sort(key=lambda row: row[0])
    old_at=new_at=0; pieces=[]; rows=[]; gaps=[]
    for at,before,after,role in edits:
        require(at>=old_at,"candidate edit overlap")
        gap=text[old_at:at].encode(); pieces.append(gap)
        gaps.append(dict(input_begin=old_at,output_begin=new_at,**pin(gap)))
        new_at+=len(gap)
        require(text[at:at+len(before)]==before,"candidate span differs")
        rows.append(dict(input_begin=at,output_begin=new_at,before=before,after=after,role=role))
        pieces.append(after.encode()); new_at+=len(after); old_at=at+len(before)
    gap=text[old_at:].encode(); pieces.append(gap)
    gaps.append(dict(input_begin=old_at,output_begin=new_at,**pin(gap)))
    candidate=b"".join(pieces)
    proof=dict(schema=SCHEMA,family=family,profile_id=profile_id,variant=variant,
        input=pin(source),output=pin(candidate),edits=rows,protected_gaps=gaps,full_inverse=True,
        scope=scope,resources_changed=False,features_removed=False,production_selected=False)
    require(candidate!=source,"no-op candidate is not a new compression improvement")
    return candidate,proof

def restore_source(candidate, proof):
    require(proof.get("schema")==SCHEMA and pin(candidate)==proof.get("output"),
            "candidate/proof output identity differs")
    old=candidate
    for row in reversed(proof["edits"]):
        at=row["output_begin"]; after=row["after"].encode()
        require(old[at:at+len(after)]==after,"candidate inverse span differs")
        old=old[:at]+row["before"].encode()+old[at+len(after):]
    repeated,expected=transform_source(old,family=proof["family"],
        profile_id=proof["profile_id"],variant=proof["variant"])
    require(repeated==candidate and expected==proof,"full candidate inverse/protected gaps differ")
    return old
