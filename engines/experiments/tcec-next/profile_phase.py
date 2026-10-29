"""Exact optional lifecycle factoring for full A/C/E/F resource profiles.

This pure post-projection consumes freshly regenerated resource-profile C,
never a historical source as a producer input. Search, evaluation, SIMD,
learners and F's MTD/witness logic are outside its admitted edit spans.
"""
from hashlib import sha256
import re

SCHEMA = "rove4k.portable-phase-source.v1"
VARIANTS = ("phase", "phase-init")
DOMAINS = {"test-p4": (4, 22), "test-p28": (28, 24), "tcec-provisional": (256, 33)}
INPUTS = {
 ("A","test-p4","private-path"): (7867,"703b8c07b419766621a7f58e577ff91842329eb42e15afcdfa012e96b3fd3060"),
 ("A","test-p4","none"): (7839,"c8cb32a56ffa79177260bfea28b017d0a4e531b82c4193a8e3940b8186d7b888"),
 ("A","test-p28","private-path"): (7868,"8beb3e6e87dc412b2f2f980d5e240166823d1453692062e26473952ff68c1f83"),
 ("A","test-p28","none"): (7840,"38f380503bc2e2d54e6d0160eb0524b6c69c7d4d4ea1cabe7365f56cec7527bd"),
 ("A","tcec-provisional","private-path"): (7869,"8ad7b2996c50c54abfe4a845e06f4552e1e75b828121ca80a6759a6113017d81"),
 ("A","tcec-provisional","none"): (7841,"a1dd21a8b231f3e3248861c43f11f47045f2ae86d73b0216ca4525cdc03a51dc"),
 ("C","test-p4","private-path"): (8501,"e834536d3a2972e83056fcbadbab354a0eb068a5d92cb14d2a44ceb11baf8f22"),
 ("C","test-p4","none"): (8466,"4a252ef87f6f2af95a75f1942581c7b3397c1d370da3aabb6848ae47bb43e666"),
 ("C","test-p28","private-path"): (8502,"6c32625c51a7d45b1149ce60165dadc492d124bdbc1d47261a0e7a9111eb9b9a"),
 ("C","test-p28","none"): (8467,"4fdeb0bc9495d48444f37262eb5bc6ce6d39400d9efae5f132b397e9726c09e7"),
 ("C","tcec-provisional","private-path"): (8503,"920a6515bc210a8909832d078cc8842621e26a6ba43ba521917983cd39518793"),
 ("C","tcec-provisional","none"): (8468,"919e1415c865de3cf94b7b9833f72dd69b3bb5b0a589d0799b0d811d3f3a72b5"),
 ("E","test-p4","private-path"): (8060,"84bb4ceb3e2841dd3fbf611ce68651a8bc6c190654a6166bc8611c685223f55d"),
 ("E","test-p4","none"): (8032,"8944b2bf6ed9875fe9b74482e389d6916c07bab0118f10e1f6b5849e1692adc4"),
 ("E","test-p28","private-path"): (8061,"e76871df278721ae92f6f0f4c2f2af3110e4139b138d15ff89d6f762f646748a"),
 ("E","test-p28","none"): (8033,"000fdf2029d71eb147724ab037ff42dada514330938f0b0ac531967423ade9b4"),
 ("E","tcec-provisional","private-path"): (8062,"f70dd3b89a1ccbe0cf8032b2a60fa146ad3bd54a5aaa4372fb2f935a3e22f882"),
 ("E","tcec-provisional","none"): (8034,"38eba07fef5cc918af27af9e6b5df1d52868908df770af21379513ab817109ad"),
 ("F","test-p4","private-path"): (7295,"55a2737c6a3acc420dd7c5679021338247fb23aeb9037f3fc9571888491ebf7b"),
 ("F","test-p4","none"): (7267,"39f00ef4b43d94d9ab5a5c983237a069a2016eed7f0b780f0f253c9fc4cc576d"),
 ("F","test-p28","private-path"): (7296,"38a37e17999adcaf544aab4e93b845dacfc5d0e5965f8023e04baef977a5fd5d"),
 ("F","test-p28","none"): (7268,"2ce263c1554ff935d24133868756f043a59aca9b72da3dfcb623f46b97023d87"),
 ("F","tcec-provisional","private-path"): (7297,"94ecb1104e1c69bdb24b0e12827049ea5b0b1b1ce816bb5bcc420f4312d92fec"),
 ("F","tcec-provisional","none"): (7269,"0ab9522cb0d7b16a14e969990216feeba4f252cf614fda1fe00d8c9aeac9cb52"),
}
CONTEXT = {
 "A": dict(st="static", integer="L", returned="J", pointer_zero="0", thread_zero="0",
  worker="A", search="C", board="F", pending="I", selector="x", join="j", joined="qk",
  handles="qb", cancel="X", clear="B", worker_type="M", workers="K", ident="id", depth="C",
  table="N", key="aT", data="U", lock="zN", learners=("zC","an","ah")),
 "C": dict(st="static", integer="int", returned="return", pointer_zero="0", thread_zero="0",
  worker="A", search="C", board="ql", pending="qj", selector="x", join="j", joined="qk",
  handles="qb", cancel="qp", clear="B", worker_type="ai", workers="qr", ident="id", depth="C",
  table="qq", key="aT", data="U", lock="zN", learners=("zC","an","ah")),
 "E": dict(st="static", integer="L", returned="J", pointer_zero="0", thread_zero="0",
  worker="A", search="C", board="ql", pending="qj", selector="x", join="j", joined="qk",
  handles="qb", cancel="qp", clear="B", worker_type="ai", workers="qr", ident="id", depth="C",
  table="qq", key="aT", data="U", lock="zN", learners=("zC","an","ah")),
 "F": dict(st="aa", integer="S", returned="H", pointer_zero="NULL", thread_zero="NULL",
  worker="qq", search="i", board="Z", pending="A", selector="y", join="k", joined="C",
  handles="t", cancel="V", clear="qk", worker_type="X", workers="U", ident="a", depth="b",
  table="B", key="a", data="b", lock="zN", learners=("h","i","j")),
}


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _search_region(text, context):
    """Locate only the known search definition, without interpreting C input."""
    expression = (r"\b" + re.escape("void " + context["search"] + "(") +
                  r"[^;{}]*\)\{")
    matches = list(re.finditer(expression, text))
    require(len(matches) == 1, "one pinned full search definition required")
    start, at, level = matches[0].start(), matches[0].end(), 1
    quote = None
    while level:
        require(at < len(text), "unterminated pinned search definition")
        char = text[at]
        if quote:
            if char == "\\":
                at += 2
                continue
            if char == quote:
                quote = None
        elif char in ("\"", "'"):
            quote = char
        elif char == "{":
            level += 1
        elif char == "}":
            level -= 1
        at += 1
    return start, text[start:at].encode("ascii")


def transform_source(source, *, family, profile_id, entry_cleanup="private-path", variant="phase"):
    key = family, profile_id, entry_cleanup
    require(type(source) is bytes and INPUTS.get(key) == (len(source), sha256(source).hexdigest()),
            "exact named full A/C/E/F resource-profile source required")
    require(variant in VARIANTS, "explicit finite portable phase variant required")
    text, c = source.decode("ascii"), CONTEXT[family]
    workers, bits = DOMAINS[profile_id]
    entries, unit = 1 << bits, 512
    require(text.startswith(f"#define RVW {workers}\n#define RVN ((size_t)1<<{bits})\n#define RVU {unit}\n"),
            "pinned resource definitions differ")
    require(entries * workers < 1 << 64 and
            (profile_id == "test-p28" or (entries // unit) % workers == 0),
            "64-bit equal-page partition domain differs")
    require("rv_spawn" not in set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", text)),
            "shared launcher identifier collides")
    mutations = re.findall(r"\bqh(?:\+\+|--|[+*/%&|^-]?=(?!=))", text)
    require(sorted(mutations) == ["qh++", "qh=", "qh="] and text.count("qh=1;") == 2 and
            not re.search(r"(?:\+\+|--)\s*qh\b|&\s*qh\b", text),
            "pinned main-owned history lifetime differs")
    before_search_at, before_search = _search_region(text, c)
    st, integer, returned = (c[name] for name in ("st", "integer", "returned"))
    wt, ws, ident, depth = (c[name] for name in ("worker_type", "workers", "ident", "depth"))
    tt, handles = c["table"], c["handles"]
    init_body = (f"{wt}*w=p;size_t rv_n=w->{ident},"
        "rv_i=(RVN/RVU*rv_n/RVW)*RVU,rv_e=(RVN/RVU*(rv_n+1)/RVW)*RVU;"
        f"for(;rv_i<rv_e;rv_i++){{{tt}[rv_i].{c['key']}={tt}[rv_i].{c['data']}=0;"
        f"atomic_flag_clear_explicit(&{tt}[rv_i].{c['lock']},memory_order_relaxed);}}")
    new_init = init_body
    if variant == "phase-init":
        ranges = ("i=RVN*n/RVW,e=RVN*(n+1)/RVW" if profile_id != "test-p28" else
                  "i=RVN/RVU*n/RVW*RVU,e=RVN/RVU*(n+1)/RVW*RVU")
        new_init = (f"size_t n=(({wt}*)p)->{ident}," + ranges +
            f";for(;i<e;i++){{{tt}[i].{c['key']}={tt}[i].{c['data']}=0;"
            f"atomic_flag_clear_explicit(&{tt}[i].{c['lock']},memory_order_relaxed);}}")
    search_body = f"{c['search']}(p,&{c['board']});if(!--{c['pending']}){c['selector']}();"
    callback = f"{st} void*{c['worker']}(void*p){{"
    callback_end = f"{returned} {c['pointer_zero']};}}"
    launcher = (f"{st} void rv_spawn(void){{for({integer} n=0;n<RVW;n++)"
        f"{{{ws}[n].{ident}=n;{ws}[n].{depth}=0;"
        f"if(pthread_create({handles}+n,{c['thread_zero']},{c['worker']},{ws}+n))exit(2);}}}}")
    launch = (f"for({integer} n=0;n<RVW;n++){{{ws}[n].{ident}=n;{ws}[n].{depth}=0;"
        f"if(pthread_create({handles}+n,{c['thread_zero']},{c['worker']},{ws}+n))exit(2);}}")
    startup = (f"for({integer} n=0;n<RVW;n++){{{ws}[n].{ident}=n;"
        f"if(pthread_create({handles}+n,0,{c['clear']},{ws}+n))exit(2);}}"
        f"for({integer} n=0;n<RVW;n++)if(pthread_join({handles}[n],0))exit(2);")
    edits = []
    def edit(role, old, new):
        require(text.count(old) == 1, "one exact lifecycle consumer required: " + role)
        edits.append((role, text.index(old), old, new))
    edit("shared phase callback and launcher", callback + search_body + callback_end,
         callback + "if(qh){" + search_body + "}else{" + new_init + "}" + callback_end + launcher)
    edit("remove separate initializer", f"{st} void*{c['clear']}(void*p){{" + init_body + returned + " 0;}", "")
    edit("same GO launch after count publication", launch, "rv_spawn();")
    edit("same startup join before history and UCI", startup,
         f"{c['joined']}=RVW;rv_spawn();{c['join']}();")
    if variant == "phase-init" and profile_id != "test-p28":
        edit("unused complete-page unit", "#define RVU 512\n", "")
    ordered = sorted(edits, key=lambda item: item[1])
    end = 0
    for role, at, old, new in ordered:
        require(at >= end, "overlapping lifecycle consumers: " + role)
        end = at + len(old)
    result = source
    for role, at, old, new in reversed(ordered):
        result = result[:at] + new.encode("ascii") + result[at + len(old):]
    spans, gaps, old_at, new_at, delta = [], [], 0, 0, 0
    for role, at, old, new in ordered:
        target = at + delta
        gap = source[old_at:at]
        require(gap == result[new_at:target], "protected lifecycle complement differs")
        gaps.append(dict(old_start=old_at, new_start=new_at, **pin(gap)))
        spans.append(dict(role=role, old_start=at, new_start=target, old=old, new=new))
        old_at, new_at = at + len(old), target + len(new)
        delta += len(new) - len(old)
    require(source[old_at:] == result[new_at:], "protected lifecycle suffix differs")
    gaps.append(dict(old_start=old_at, new_start=new_at, **pin(source[old_at:])))
    after_search_at, after_search = _search_region(result.decode("ascii"), c)
    require(before_search == after_search, "full search/learner/MTD body changed")
    proof = dict(schema=SCHEMA, family=family, profile_id=profile_id, entry_cleanup=entry_cleanup,
        variant=variant, input=pin(source), output=pin(result), spans=spans, protected_gaps=gaps,
        full_inverse=True, runtime_qualified=False,
        protected_search=dict(name=c["search"], old_start=before_search_at,
            new_start=after_search_at, **pin(before_search)),
        history=dict(symbol="qh", startup_value=0, search_minimum=1, main_owned=True,
            writes="two qh=1 assignments and one bounded qh++", position_reuse_after_join=True),
        initialization=dict(callback=c["worker"], phase="qh==0", launcher="rv_spawn",
            join=c["join"], pending_unchanged_zero=True, assigned_worker_fields=[ident, depth],
            partition_domain=dict(workers=workers, entries=entries, unit_entries=unit,
                equal_page_units=(entries // unit) % workers == 0,
                largest_new_range_product=entries * workers, required_arithmetic_bits=64),
            cancellation="existing join sets one; init ignores; every GO resets zero before spawn",
            partition="same 512-entry floor boundaries" if profile_id=="test-p28" or variant=="phase" else
                      "equal whole-page ranges; workers divide original page units",
            kernel_zero_assumed=False, learners_preserved=list(c["learners"])),
        search=dict(callback=c["worker"], phase="qh>=1", completion=c["pending"],
            completion_statement_preserved=True, selector=c["selector"], core_unchanged=True),
        mechanism_fixture_scope="new phase-aware emitted-C fixture required; control fixture is not reused")
    require(restore_source(result, proof) == source, "portable phase full inverse differs")
    return result, proof


def restore_source(candidate, proof):
    require(type(candidate) is bytes and proof.get("schema") == SCHEMA and
            proof.get("variant") in VARIANTS and pin(candidate) == proof.get("output"),
            "portable phase output identity differs")
    key = proof.get("family"), proof.get("profile_id"), proof.get("entry_cleanup")
    expected = INPUTS.get(key)
    require(expected is not None and proof.get("input") == dict(bytes=expected[0],sha256=expected[1]),
            "portable phase input admission differs")
    result = candidate
    for span in reversed(proof["spans"]):
        at, old, new = span["new_start"], span["old"].encode("ascii"), span["new"].encode("ascii")
        require(result[at:at+len(new)] == new, "portable phase inverse span differs")
        result = result[:at] + old + result[at+len(new):]
    require(pin(result) == proof["input"], "portable phase restored identity differs")
    return result
