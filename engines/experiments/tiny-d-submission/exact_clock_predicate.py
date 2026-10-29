"""One exact four-key predicate for the frozen full D search source class.

The source and the cleaned compiler input are both authenticated and inverted.
This pure helper does not read files, compile, package, run an engine or change
the existing valid-clock-domain predicates used by other engine families.
"""
from hashlib import sha256
import json

KIND = "D-exact-clock-Span-predicate-v1"
READABLE = {
    "tiny.h": (2970, "fac1d3f165d01e01efc7c6a2f89ee8767661e6d3aad0478febad21fa3814bf9e"),
    "board.c": (10361, "ecd9d567a1f6c5ee185012a70915ab63c741bbf68b7a294d1604334c59db4e62"),
    "search.c": (5909, "73ba9dbdf23906cff90e6098ee0903bdf38b4f95e826871042281c9894de6344"),
    "runtime.c": (15555, "0d80984d9bbb32969eb1c6ee76105a3742c09d7baa0a679195dde573e3aa183e"),
    "start.S": (845, "4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b"),
    "image.ld": (446, "38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b"),
}
SHIPPING = {
    "main.c": (15781, "14de622a0047aeed5334bf7557ad0f0fcfc6512f28a0d077e3c0f2c16076184d"),
    "start.S": (614, "40ea09083dbe07feba76fba528b017f9a7dd4eecda7e857deeb874e1da1cddaa"),
    "image.ld": READABLE["image.ld"],
}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "immutable source bytes required")
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def inventory(files):
    require(type(files) is dict and all(type(n) is str for n in files),
            "explicit named source mapping required")
    return {n: pin(d) for n, d in sorted(files.items())}


def same(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
        right, sort_keys=True, separators=(",", ":"))


def old_expression(name):
    require(name in ("token", "o"), "one of the two frozen token names required")
    return ("||".join('word('+name+',"'+word+'")' for word in
                      ("wtime", "btime", "winc", "binc"))).encode("ascii")


def predicate(name):
    """Only byte reads behind exact Span lengths; caller has n != 0."""
    require(name in ("token", "o"), "one of the two frozen token names required")
    return ((f"({name}.p[0]=='w'||{name}.p[0]=='b')&&"
             f"(({name}.n==5&&{name}.p[1]=='t'&&{name}.p[2]=='i'&&"
             f"{name}.p[3]=='m'&&{name}.p[4]=='e')||"
             f"({name}.n==4&&{name}.p[1]=='i'&&{name}.p[2]=='n'&&"
             f"{name}.p[3]=='c'))")).encode("ascii")


def _project(data, before, after):
    require(type(data) is bytes and type(before) is bytes and type(after) is bytes
            and before and after and before != after and data.count(before) == 1,
            "unique nonempty exact clock replacement required")
    begin = data.index(before)
    output = data[:begin] + after + data[begin+len(before):]
    proof = dict(input=pin(data), output=pin(output), begin=begin,
                 before=before.decode("ascii"), after=after.decode("ascii"),
                 gaps=[pin(data[:begin]), pin(data[begin+len(before):])])
    require(_restore(output, proof) == data, "exact clock source inverse differs")
    return output, proof


def _restore(data, proof):
    require(type(proof) is dict and pin(data) == proof.get("output"),
            "clock source output pin differs")
    begin, after = proof.get("begin"), proof.get("after")
    require(type(begin) is int and begin >= 0 and type(after) is str,
            "clock inverse coordinates or replacement differ")
    after = after.encode("ascii")
    require(data[begin:begin+len(after)] == after, "clock inverse span differs")
    first, last = data[:begin], data[begin+len(after):]
    require([pin(first), pin(last)] == proof.get("gaps"),
            "clock protected complement differs")
    before = proof.get("before")
    require(type(before) is str and before, "clock original replacement absent")
    output = first + before.encode("ascii") + last
    require(pin(output) == proof.get("input"), "clock inverse input differs")
    return output


def transform(readable, shipping):
    require(inventory(readable) == {n: dict(bytes=b, sha256=s) for n, (b, s) in READABLE.items()},
            "exact full six-file 5261-byte D source required")
    require(inventory(shipping) == {n: dict(bytes=b, sha256=s) for n, (b, s) in SHIPPING.items()},
            "exact cleaned 6832/6689-byte source-package control required")
    require(readable["runtime.c"].count(b"for(Span token;(token=scan(&cursor)).n;)") == 1
            and shipping["main.c"].count(b"for(Span o;(o=scan(&A)).n;)") == 1,
            "nonempty Span loop precondition differs")
    new_readable, new_shipping = dict(readable), dict(shipping)
    new_readable["runtime.c"], a = _project(readable["runtime.c"], old_expression("token"), predicate("token"))
    new_shipping["main.c"], b = _project(shipping["main.c"], old_expression("o"), predicate("o"))
    proof = dict(kind=KIND, input_readable=inventory(readable), output_readable=inventory(new_readable),
                 input_shipping=inventory(shipping), output_shipping=inventory(new_shipping),
                 edits=dict(readable_runtime=a, shipping_main=b), full_inverse=True,
                 contract="exact wtime/btime/winc/binc; nonempty bounded Span; byte reads and short circuit",
                 other_five_readable_files_unchanged=True, entry_and_linker_unchanged=True,
                 amount_decimal_lookahead_and_budget_unchanged=True, native_identity_claimed=False,
                 runtime_qualified=False, selected=False)
    return new_readable, new_shipping, proof


def restore(readable, shipping, proof):
    require(type(proof) is dict and proof.get("kind") == KIND
            and inventory(readable) == proof.get("output_readable")
            and inventory(shipping) == proof.get("output_shipping"),
            "complete exact clock proof and outputs required")
    require(type(proof.get("edits")) is dict and set(proof["edits"]) == {"readable_runtime", "shipping_main"},
            "two exact clock source roles required")
    original_readable, original_shipping = dict(readable), dict(shipping)
    original_readable["runtime.c"] = _restore(readable["runtime.c"], proof["edits"]["readable_runtime"])
    original_shipping["main.c"] = _restore(shipping["main.c"], proof["edits"]["shipping_main"])
    repeated_readable, repeated_shipping, expected = transform(original_readable, original_shipping)
    require(readable == repeated_readable and shipping == repeated_shipping and same(proof, expected),
            "canonical clock class/proof differs")
    return original_readable, original_shipping
