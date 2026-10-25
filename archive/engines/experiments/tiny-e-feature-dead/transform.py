"""One exact E shipping feature/dead fusion; pure bytes in and bytes out.

The original DEV definitions and search expressions remain verbatim branches.
No file, compiler, project module, codec, or engine is accessed here. Literal
region reconstruction proves source scope, not C semantics or runtime identity.
"""

import hashlib


INPUT_BYTES = 28001
INPUT_SHA256 = "0a7fe69022051e1893ffbd52ade7a2fbb3f342fe20b581bb786d6997b46fb712"

_DEAD = b"""int dead(const Board *p){
    int minors=0,knights=0,colors=0;
    for(int q=0;q<128;q++)if(!(q&0x88)){
        int a=abs(p->b[q]);
        if(a==2){minors++;knights++;}
        else if(a==3){minors++;colors|=1<<((q+(q>>4))&1);}
        else if(a&&a<6)return 0;
    }
    return minors<2||(!knights&&colors!=3);
}
"""

_WHITE_RAW = b"""static int tiny_white(const Board *p){
    int pawns[2][10]={{0}},bishops[2]={0},score=p->s*tiny_weights[15];
    for(int q=0;q<128;q++)if(!(q&0x88)&&p->b[q]){
        int v=p->b[q],black=v<0,a=abs(v),sign=black?-1:1;
        score+=sign*((a<6?tiny_weights[a-1]:0)+tiny_weights[a+4]*tiny_center(q));
        if(a==1){
            pawns[black][(q&7)+1]++;
            score+=sign*tiny_weights[11]*((black?7-(q>>4):q>>4)-1);
        }
        if(a==3)bishops[black]++;
    }
    for(int black=0;black<2;black++){
        int s=bishops[black]>1?tiny_weights[14]:0;
        for(int f=1;f<9;f++){
            int n=pawns[black][f];
            if(n){s+=tiny_weights[12]*(n-1);
                if(!pawns[black][f-1]&&!pawns[black][f+1])s+=tiny_weights[13]*n;}
        }
        score+=black?-s:s;
    }
    return score;
}
static int tiny_raw(const Board *p){
#if DEV
    atomic_fetch_add_explicit(&tiny_leaf_calls,1,memory_order_relaxed);
#endif
    int s=tiny_white(p);return s>20000?20000:s< -20000?-20000:s;
}
"""

_DRAW = b"    draw|=repetitions>=2||dead(p);\n"
_EVALUATION = b"""    int evaluation=p->s*tiny_raw(p);
    if(evaluation>MATE-PLY-1)evaluation=MATE-PLY-1;
    if(evaluation< -MATE+PLY+1)evaluation=-MATE+PLY+1;
"""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _once(data, before, after, label):
    if not before or data.count(before) != 1:
        raise ValueError("literal shape/count differs: " + label)
    return data.replace(before, after, 1)


def _shipping_white_raw():
    raw_at = _WHITE_RAW.index(b"static int tiny_raw(")
    white = _WHITE_RAW[:raw_at]
    white = _once(white, b"static int tiny_white(const Board *p){",
                  b"static int tiny_white(const Board *p,int *dead_out){", "white signature")
    white = _once(white, b"score=p->s*tiny_weights[15];",
                  b"score=p->s*tiny_weights[15],knights=0,colors=0,heavy=0;", "feature locals")
    white = _once(white, b"        if(a==3)bishops[black]++;\n",
                  b"        if(a==3){bishops[black]++;colors|=1<<((q+(q>>4))&1);}\n"
                  b"        if(a==2)knights++;\n"
                  b"        if(a==1||a==4||a==5)heavy=1;\n", "feature classification")
    white = _once(white, b"    return score;\n",
                  b"    *dead_out=!heavy&&((knights+bishops[0]+bishops[1]<2)||(!knights&&colors!=3));\n"
                  b"    return score;\n", "dead output")
    raw = b"""static int tiny_raw(const Board *p,int *dead_out){
    int s=tiny_white(p,dead_out);return s>20000?20000:s< -20000?-20000:s;
}
"""
    return white + raw


def _plan():
    dead = b"#if DEV\n" + _DEAD + b"#endif\n"
    white_raw = b"#if DEV\n" + _WHITE_RAW + b"#else\n" + _shipping_white_raw() + b"#endif\n"
    draw = (b"#if DEV\n" + _DRAW + b"#else\n"
            b"    draw|=repetitions>=2;\n#endif\n")
    evaluation = (b"#if DEV\n" + _EVALUATION + b"#else\n"
                  b"    int dead_out,evaluation=p->s*tiny_raw(p,&dead_out);\n"
                  b"    if(evaluation>MATE-PLY-1)evaluation=MATE-PLY-1;\n"
                  b"    if(evaluation< -MATE+PLY+1)evaluation=-MATE+PLY+1;\n"
                  b"    draw|=dead_out;\n#endif\n")
    return (("reference_dead", _DEAD, dead),
            ("white_raw", _WHITE_RAW, white_raw),
            ("search_draw", _DRAW, draw),
            ("search_evaluation", _EVALUATION, evaluation))


def transform_sources(data: bytes):
    """Return (candidate bytes, metadata) for the sole admitted readable E.

    All four regions are fixed literals. There are no policy options, generated
    aliases, alternate model weights, file dependencies, or hidden compiler work.
    The caller must qualify new source/native/DEV identities independently.
    """
    if not isinstance(data, bytes) or len(data) != INPUT_BYTES or _sha(data) != INPUT_SHA256:
        raise ValueError("unknown original E readable bytes")
    edits = _plan()
    intervals = []
    for label, before, after in edits:
        if data.count(before) != 1 or before not in after or after.count(before) != 1:
            raise ValueError("original DEV fragment not retained once: " + label)
        start = data.index(before)
        intervals.append((start, start + len(before), label, before, after))
    intervals.sort()
    cursor, parts, regions = 0, [], []
    for start, end, label, before, after in intervals:
        if start < cursor:
            raise ValueError("overlapping literal regions")
        parts.extend((data[cursor:start], after))
        regions.append({"label": label, "original_offset": start,
                        "original_bytes": len(before), "candidate_bytes": len(after),
                        "original_sha256": _sha(before), "candidate_sha256": _sha(after),
                        "original_DEV_fragment_retained_verbatim": True})
        cursor = end
    parts.append(data[cursor:])
    candidate = b"".join(parts)
    original_masked, candidate_masked, reconstructed = data, candidate, candidate
    for label, before, after in edits:
        marker = b"/*__E_FEATURE_DEAD_" + label.encode("ascii") + b"__*/\n"
        if marker in data or marker in candidate:
            raise ValueError("proof marker appears in source")
        original_masked = _once(original_masked, before, marker, label + " original mask")
        candidate_masked = _once(candidate_masked, after, marker, label + " candidate mask")
        reconstructed = _once(reconstructed, after, before, label + " literal inverse")
    if original_masked != candidate_masked or reconstructed != data:
        raise ValueError("source complement or original reconstruction differs")
    return candidate, {
        "policy": "E-shipping-feature-dead-fusion-v1", "literal_regions": regions,
        "input": {"bytes": len(data), "sha256": _sha(data)},
        "output": {"bytes": len(candidate), "sha256": _sha(candidate)},
        "complement": {"bytes": len(original_masked), "sha256": _sha(original_masked),
                       "exact_bytes_equal": True},
        "literal_inverse_reconstruction_sha256": _sha(reconstructed),
        "DEV_original_fragments_retained_verbatim": True,
        "shipping_dead": "!heavy && ((knights+bishops[0]+bishops[1]<2)||(!knights&&colors!=3))",
        "shipping_out_pointer": "one nonnull search-local int; assigned by tiny_white before use",
        "dead_OR_order": "after existing evaluation/clamps, before terminal/TT tests",
        "protected_outside_regions": ["21 weights", "tiny_order", "Board/move/attack",
                                      "TT/context/mate encoding", "pool", "protocol"],
        "preprocessed_DEV_identity_checked": False,
        "compiler_or_runtime_checks_executed": False,
        "scope": "fixed readable-source transform and literal-region proof only",
    }
