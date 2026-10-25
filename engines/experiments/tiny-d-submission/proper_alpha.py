"""One protected whole-TU alpha projection for the frozen full D compiler input.

Unlike the old native-identity reducer, this class preserves GNU attributes and
records a new source candidate even when ordinary identifier spelling changes
compiler layout. It does not claim semantic/native/runtime admission.
"""
from collections import Counter
from hashlib import sha256
import json
import re

KIND = "D-protected-whole-TU-alpha-v1"
INPUTS = {
    "main.c": (15781,"14de622a0047aeed5334bf7557ad0f0fcfc6512f28a0d077e3c0f2c16076184d"),
    "start.S": (614,"40ea09083dbe07feba76fba528b017f9a7dd4eecda7e857deeb874e1da1cddaa"),
    "image.ld": (446,"38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b"),
}
EXPORTS = ("main","spawn","memcpy","memset","memcmp","abort","_start")
ATTRIBUTE = b"__attribute__((noinline))"


def require(value,message):
    if not value:raise ValueError(message)


def pin(data):
    require(type(data) is bytes,"immutable source bytes required")
    return dict(bytes=len(data),sha256=sha256(data).hexdigest())


def inventory(files):
    require(type(files) is dict and all(type(n) is str for n in files),"explicit source mapping required")
    return {n:pin(d) for n,d in sorted(files.items())}


def same(left,right):
    return json.dumps(left,sort_keys=True,separators=(",",":")) == json.dumps(right,sort_keys=True,separators=(",",":"))


def attribute_inventory(data):
    """The closed input has one non-reference-bearing GNU attribute only."""
    require(type(data) is bytes,"attribute source bytes required")
    starts=[m.start() for m in re.finditer(rb"\b__attribute__\b",data)]
    require(len(starts)==1,"exact one-attribute cleaned D inventory required")
    begin=starts[0]
    require(data[begin:begin+len(ATTRIBUTE)]==ATTRIBUTE,"unsupported or reference-bearing GNU attribute")
    require(b"__declspec" not in data and b"[[" not in data,"unsupported compiler attribute syntax")
    return [dict(begin=begin,end=begin+len(ATTRIBUTE),source=ATTRIBUTE.decode(),
                 identifiers=["__attribute__","noinline"],reference_arguments=False)]


def _project(data,spans,names):
    pieces,edits,gaps,at,target=[],[],[],0,0
    for begin,end,old in spans:
        if old not in names:continue
        require(type(begin) is int and type(end) is int and at<=begin<end<=len(data)
                and data[begin:end]==old.encode(),"ordered actual identifier spans required")
        new=names[old].encode();gap=data[at:begin]
        pieces.extend((gap,new));gaps.append(pin(gap));target+=len(gap)
        edits.append(dict(begin=begin,end=end,target=target,before=old,after=new.decode()))
        target+=len(new);at=end
    pieces.append(data[at:]);gaps.append(pin(data[at:]));output=b"".join(pieces)
    proof=dict(input=pin(data),output=pin(output),edits=edits,gaps=gaps)
    require(_restore(output,proof)==data,"alpha source full inverse differs")
    return output,proof


def _restore(data,proof):
    require(type(proof) is dict and pin(data)==proof.get("output"),"alpha output pin differs")
    pieces,gaps,at,source_at=[],[],0,0
    for row in proof.get("edits",[]):
        target,after,before=row.get("target"),row.get("after"),row.get("before")
        require(type(target) is int and at<=target<=len(data) and type(after) is str
                and type(before) is str and after and before,"alpha inverse coordinates differ")
        after,before=after.encode(),before.encode();gap=data[at:target]
        require(data[target:target+len(after)]==after and row.get("begin")==source_at+len(gap)
                and row.get("end")==row["begin"]+len(before),"alpha inverse span differs")
        pieces.extend((gap,before));gaps.append(pin(gap));at=target+len(after);source_at=row["end"]
    pieces.append(data[at:]);gaps.append(pin(data[at:]));output=b"".join(pieces)
    require(pin(output)==proof.get("input") and gaps==proof.get("gaps"),"alpha inverse/complement differs")
    return output


def transform(files,lexical):
    require(inventory(files)=={n:dict(bytes=b,sha256=s) for n,(b,s) in INPUTS.items()},
            "exact cleaned full D source class required")
    data=files["main.c"];text=data.decode("ascii");attributes=attribute_inventory(data)
    spans=list(lexical._identifier_spans(text))
    reserved=set(lexical._KEYWORDS)|set(EXPORTS)
    for n,d in files.items():
        if n!="main.c":reserved.update(lexical._ANY_WORD.findall(d.decode("ascii")))
    # Every directive/literal/comment/number gap remains opaque. Spellings used
    # there are protected on both sides, including quoted ASM symbol operands.
    at=0
    for begin,end,token in spans:
        reserved.update(lexical._ANY_WORD.findall(text[at:begin]));at=end
    reserved.update(lexical._ANY_WORD.findall(text[at:]))
    for attr in attributes:reserved.update(attr["identifiers"])
    reserved.update(token for _,_,token in spans if token.startswith("__"))
    used=set(lexical._ANY_WORD.findall(text))|reserved
    counts=Counter(token for _,_,token in spans)
    candidates=sorted((n for n in counts if len(n)>1 and n not in reserved
        and lexical._ASCII_IDENTIFIER.fullmatch(n)),key=lambda n:(-(len(n)-1)*counts[n],n))
    generated=lexical._short_names();names={}
    for old in candidates:
        new=next(n for n in generated if n not in used)
        used.add(new)
        if len(new)<len(old):names[old]=new
    require(names and len(set(names.values()))==len(names) and not(set(names)&reserved)
            and not(set(names.values())&reserved),"nonempty collision-free protected alpha map required")
    output,projection=_project(data,spans,names)
    result={**files,"main.c":output}
    after_attributes=attribute_inventory(output)
    require([a["source"] for a in after_attributes]==[a["source"] for a in attributes],"GNU attribute bytes changed")
    for attr in attributes:
        require(not any(row["begin"]<attr["end"] and row["end"]>attr["begin"] for row in projection["edits"]),
                "alpha map entered a protected GNU attribute")
    proof=dict(kind=KIND,input=inventory(files),output=inventory(result),renames=names,
        projection=projection,reserved=sorted(reserved),attributes_before=attributes,attributes_after=after_attributes,
        exports=list(EXPORTS),entry_and_linker_unchanged=True,compiler_attributes_unchanged=True,
        quoted_ASM_and_literals_unchanged=True,full_inverse=True,semantics_qualified=False,
        native_identity_claimed=False,runtime_qualified=False,selected=False,
        family_applicability={"D":"one measured source class; new qualification required",
            **{n:"own source/lexical closure already exists; independent cost/admission required" for n in "ABCEF"}})
    return result,proof


def restore(files,proof,lexical):
    require(type(proof) is dict and proof.get("kind")==KIND and inventory(files)==proof.get("output"),
            "complete protected alpha proof/output required")
    original={**files,"main.c":_restore(files["main.c"],proof["projection"])}
    repeated,expected=transform(original,lexical)
    require(repeated==files and same(expected,proof),"canonical protected alpha class/map differs")
    return original
