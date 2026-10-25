"""One typed GNU-int atomic representation, separate from native-byte gates.

Twelve expanded generic load/store expressions become GNU _n operations.
All storage and all three fetch operations remain unchanged. This is a new
semantic/codegen experiment, not an identity waiver or an old admission.
GNU semantics: https://gcc.gnu.org/onlinedocs/gcc/_005f_005fatomic-Builtins.html
"""
from hashlib import sha256
import re

KIND = "D-typed-GNU-int-atomic-representation-v1"
INPUTS = {
    "main.c": {"bytes": 15781, "sha256": "14de622a0047aeed5334bf7557ad0f0fcfc6512f28a0d077e3c0f2c16076184d"},
    "start.S": {"bytes": 614, "sha256": "40ea09083dbe07feba76fba528b017f9a7dd4eecda7e857deeb874e1da1cddaa"},
    "image.ld": {"bytes": 446, "sha256": "38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b"},
}
# Half-open positions in the exact cleaned TU, independently inventoried.
# No pointer, value or order argument has side effects in this closed cohort.
OPS = (
    (4704,4873,"load","&T",None,"l"),
    (4933,5094,"store","&T","1","5"),
    (5837,5998,"store","&T","1","5"),
    (7361,7530,"load","&T",None,"l"),
    (8299,8468,"load","&T",None,"l"),
    (12465,12638,"load","&epoch",None,"L"),
    (12806,12967,"store","&P","0","G"),
    (13016,13177,"store","&T","1","l"),
    (13214,13383,"load","&P",None,"L"),
    (14439,14600,"store","&T","0","l"),
    (14614,14777,"store","&P","4+1","l"),
    (14981,15142,"store","&P","4","l"),
)
FETCHES = (
    b"__atomic_fetch_sub((&P),(1),(G))",
    b"__atomic_fetch_sub((&P),(1),(memory_order_acq_rel))",
    b"__atomic_fetch_add((&epoch),(1),(G))",
)
STORAGE = (
    b"typedef _Atomic int U;", b"extern U T;",
    b"Z ac[4];U T;g deadline,game_keys[4096];",
    b"static U epoch,P,ids[4];",
)
ASSERTIONS = b"""
_Static_assert(sizeof(int)==4&&sizeof(U)==4&&_Alignof(U)==_Alignof(int),"");
_Static_assert(__atomic_always_lock_free(sizeof(U),0),"");
_Static_assert(__builtin_types_compatible_p(__typeof__(T),U)&&__builtin_types_compatible_p(__typeof__(epoch),U)&&__builtin_types_compatible_p(__typeof__(P),U)&&__builtin_types_compatible_p(__typeof__(ids),U[4]),"");
_Static_assert(l==__ATOMIC_RELAXED&&L==__ATOMIC_ACQUIRE&&G==__ATOMIC_RELEASE&&memory_order_acq_rel==__ATOMIC_ACQ_REL&&memory_order_seq_cst==__ATOMIC_SEQ_CST,"");
"""
ORDERS = {"l": 0, "L": 2, "G": 3, "memory_order_acq_rel": 4, "5": 5}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(isinstance(data, bytes), "immutable actual source required")
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def pins(files):
    require(isinstance(files, dict) and all(isinstance(n, str) for n in files),
            "named immutable source mapping required")
    return {n: pin(d) for n, d in sorted(files.items())}


def expressions(operation, pointer, value, order):
    """Exact original GCC template and its typed scalar spelling."""
    require(operation in ("load", "store") and pointer in ("&T", "&epoch", "&P") and
            order in ORDERS and value in (None, "0", "1", "4", "4+1"),
            "closed scalar operation operands required")
    if operation == "load":
        require(value is None and ORDERS[order] in (0,2,5), "valid closed load order required")
        before = ("({__auto_type __atomic_load_ptr=(%s);__typeof__((void)0,*__atomic_load_ptr)"
                  "__atomic_load_tmp;__atomic_load(__atomic_load_ptr,&__atomic_load_tmp,(%s));"
                  "__atomic_load_tmp;})") % (pointer, order)
        # The original template follows the token __extension__ directly.
        # A parenthesized primary preserves that token boundary as well as
        # expression precedence; a bare builtin would merge identifiers.
        after = "(__atomic_load_n((int*)(%s),(%s)))" % (pointer, order)
    else:
        require(value is not None and ORDERS[order] in (0,3,5), "valid closed store order required")
        before = ("({__auto_type __atomic_store_ptr=(%s);__typeof__((void)0,*__atomic_store_ptr)"
                  "__atomic_store_tmp=(%s);__atomic_store(__atomic_store_ptr,&__atomic_store_tmp,(%s));})") % (pointer,value,order)
        after = "(__atomic_store_n((int*)(%s),(%s),(%s)))" % (pointer,value,order)
    return before.encode(), after.encode()


def _balanced(data, begin, opening, closing):
    require(data[begin:begin+1] == opening, "protected region opening differs")
    level, quote, escaped = 0, None, False
    for i in range(begin, len(data)):
        char=data[i:i+1]
        if quote:
            if escaped: escaped=False
            elif char == b"\\": escaped=True
            elif char == quote: quote=None
        elif char in (b"'",b'"'): quote=char
        elif char == opening: level+=1
        elif char == closing:
            level-=1
            if not level: return i+1
    raise ValueError("unterminated protected region")


def _protected(files):
    data=files["main.c"]
    regions={}
    for token in (b"__asm__",b"_Static_assert"):
        rows=[]
        for match in re.finditer(rb"\b"+token+rb"\b",data):
            start=data.find(b"(",match.end())
            require(start>=0,"protected expression opening absent")
            end=_balanced(data,start,b"(",b")")
            rows.append(pin(data[match.start():end]))
        regions[token.decode()]=rows
    signatures={}
    for name in ("main","work","memcpy","memset","abort"):
        matches=list(re.finditer(rb"\b"+name.encode()+rb"\([^;{}]*\)\s*\{",data))
        require(len(matches)==1,"unique retained root/support definition required: "+name)
        signatures[name]=pin(matches[0].group())
    for expression in (*FETCHES,*STORAGE):
        require(data.count(expression)==1,"retained fetch/storage declaration differs")
    return dict(asm=regions["__asm__"],assertions=regions["_Static_assert"],
        signatures=signatures,fetches=[pin(x) for x in FETCHES],storage=[pin(x) for x in STORAGE],
        assembler=pin(files["start.S"]),linker=pin(files["image.ld"]))


def transform(files):
    require(pins(files)==INPUTS,"exact cleaned14de622 D source required")
    data=files["main.c"]; before_protected=_protected(files)
    parts,edits,gaps=[],[],[]
    at,target=0,0
    for begin,end,operation,pointer,value,order in OPS:
        before,after=expressions(operation,pointer,value,order)
        require(at<=begin<end<=len(data) and data[begin:end]==before,
                "exact inventoried atomic template differs")
        gap=data[at:begin]
        parts.extend((gap,after));gaps.append(pin(gap));target+=len(gap)
        edits.append(dict(begin=begin,end=end,target=target,before=before.decode(),after=after.decode(),
            operation=operation,pointer=pointer,value=value,order=order,order_value=ORDERS[order],
            pointer_evaluations=1,value_evaluations=int(value is not None),order_evaluations=1,
            closed_arguments_have_side_effects=False))
        target+=len(after);at=end
    parts.extend((data[at:],ASSERTIONS));gaps.append(pin(data[at:]))
    output=b"".join(parts);result={**files,"main.c":output}
    after_protected=_protected(result)
    require(after_protected["assertions"][:len(before_protected["assertions"])]==before_protected["assertions"] and
            len(after_protected["assertions"])==len(before_protected["assertions"])+4 and
            {k:v for k,v in after_protected.items() if k!="assertions"}==
            {k:v for k,v in before_protected.items() if k!="assertions"},
            "ASM/storage/fetch/root/assert preservation differs")
    require(sum(e["operation"]=="load" for e in edits)==5 and
            sum(e["operation"]=="store" for e in edits)==7 and
            sum(e["operation"]=="store" and e["order_value"]==5 for e in edits)==2,
            "twelve typed atomic operations/two seq_cst stores required")
    proof=dict(kind=KIND,input=pins(files),output=pins(result),edits=edits,gaps=gaps,
        appended_assertions=ASSERTIONS.decode(),retained=before_protected,
        output_retained=after_protected,operation_count=15,specialized_loads=5,specialized_stores=7,
        unchanged_fetches=3,storage="_Atomic int U; T/epoch/P/ids[4] unchanged",
        atomic128_TT_changed=False,old_native_identity_waived=False,
        GNU_target_extension=True,strict_ISO_C11_claimed=False,
        docs="https://gcc.gnu.org/onlinedocs/gcc/_005f_005fatomic-Builtins.html",
        semantic_qualified=False,runtime_qualified=False,selected=False)
    require(_restore(output,proof)==data,"full typed source inverse differs")
    return result,proof


def _restore(output,proof):
    require(pin(output)==proof["output"]["main.c"] and
            output.endswith(proof["appended_assertions"].encode()),"typed output/assert suffix differs")
    body=output[:-len(proof["appended_assertions"].encode())]
    parts,gaps=[],[];at=0;original_at=0
    for row in proof["edits"]:
        target=row["target"];after=row["after"].encode();before=row["before"].encode()
        require(type(target) is int and at<=target and body[target:target+len(after)]==after,
                "typed inverse operation differs")
        gap=body[at:target]
        require(row["begin"]==original_at+len(gap) and row["end"]==row["begin"]+len(before),
                "typed inverse source offsets differ")
        parts.extend((gap,before));gaps.append(pin(gap))
        at=target+len(after);original_at=row["end"]
    parts.append(body[at:]);gaps.append(pin(body[at:]))
    source=b"".join(parts)
    require(pin(source)==proof["input"]["main.c"] and gaps==proof["gaps"],
            "typed inverse/protected complement differs")
    return source


def restore(files,proof):
    require(proof.get("kind")==KIND and pins(files)==proof["output"],"typed atomic class/output differs")
    original={**files,"main.c":_restore(files["main.c"],proof)}
    regenerated,expected=transform(original)
    require(regenerated==files and expected==proof,"complete typed operation/proof replay differs")
    return original
