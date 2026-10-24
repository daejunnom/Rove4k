"""Finite getline candidates after the frozen TCEC runtime and input stages.

The admitted inputs are full A/B/C/E process-final-immediate + c_input and
full F2/F8 async-per-GO + c_input, with two exact optional operator refinements.
No recipe or default is selected here.  The
portable size_t variant and an explicitly ABI-qualified word-alias variant are
separate experiments.  Both retain NULL + zero initial ownership and a signed
positive-result loop; neither inspects failed getline contents.

Successful records have no new fixed line-size limit.  One libc-owned reusable
buffer grows with the longest logical line, while the unchanged engine history
bound remains 4096 states.  EOF, I/O error and allocation failure leave the loop
for the already-admitted whole-process terminal path; its buffer is reclaimed
by process exit.  NUL-free input remains the upstream protocol contract.
"""

from hashlib import sha256


SCHEMA = "rove4k.tcec-c-line.v1"
VARIANTS = ("size_t", "word")
PROFILES = {
    "A": (7973, "fb4aa3da7b723da7cbc859cdadc373f16e54fe2bed49c89dcdd690d9695c1dc1", "R", "L", "W"),
    "B": (9370, "c4ac5454dd41f91d521eec410cf91e495adf86d7efbb26db8c3a08e2000df168", "j", "I", "D"),
    "C": (8592, "87e51729e5e1c075670fd73845885bcbf60f95c57890a64f1398f126f06e520f", "R", "int", "W"),
    "E": (8167, "ca897f4c2db49b8199129a11d7e77b372e2d13959f6127abe8e059f0bbc49ab4", "R", "L", "W"),
    "F2": (7043, "9511f2b0542bf04abeb06cae49a2dd559535b912ac0dec6cc2852cd451e9fc71", "g", "S", "W"),
    "F8": (7186, "d5abfdd3000b956b0a2a1de11d65fbe379e99d8a327f1470c5439d077a0e0748", "g", "S", "W"),
}
ADMISSIONS = {family: ((row[0], row[1]),) for family, row in PROFILES.items()}
ADMISSIONS["F2"] += ((7005, "bd5d59e8ea684687650de059eb8ba30393a74b5ad68e7fb287516e8ce7567982"),)
ADMISSIONS["F8"] += ((7148, "a5e910a08cb34e2b01e5eb25dfe7081a5e5401f73dd04e4af9aab451a60e202c"),)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _edits(family, variant):
    if family not in PROFILES or variant not in VARIANTS:
        raise ValueError("explicit admitted getline family and variant required")
    _, _, buffer, integer, word = PROFILES[family]
    length = "size_t" if variant == "size_t" else word
    declaration = (f"char {buffer}[32768];", f"char*{buffer}=0;{length} n=0;")
    prefix = f"while(fgets({buffer},sizeof {buffer},stdin)){{if(!strchr({buffer},'\\n')){{"
    if family == "B":
        prefix += f"{integer} n,bad=0;while((n=getchar())!=EOF&&n!='\\n')bad=1;if(bad)continue;}}"
    else:
        prefix += (f"{integer} n=getchar();if(n!=EOF&&n!='\\n'){{do{{n=getchar();}}"
                   "while(n!=EOF&&n!='\\n');continue;}}")
    loop = (prefix, f"while(getline(&{buffer},&n,stdin)>0){{")
    return tuple((role, old.encode("ascii"), new.encode("ascii")) for role, (old, new)
                 in (("buffer", declaration), ("read-loop", loop)))


def _patch(source, edits):
    rows = []
    for role, old, new in edits:
        if source.count(old) != 1:
            raise ValueError(f"{role}: unique admitted line-input span missing")
        rows.append((source.index(old), role, old, new))
    rows.sort()
    parts, projection, protected = [], [], []
    consumed = emitted = 0
    for begin, role, old, new in rows:
        if begin < consumed:
            raise ValueError("line-input spans overlap")
        gap = source[consumed:begin]
        parts.extend((gap, new))
        protected.append({"input_begin": consumed, "output_begin": emitted, **pin(gap)})
        emitted += len(gap)
        projection.append({"role": role, "input_begin": begin, "output_begin": emitted,
                           "before": pin(old), "after": pin(new)})
        consumed, emitted = begin + len(old), emitted + len(new)
    gap = source[consumed:]
    parts.append(gap)
    protected.append({"input_begin": consumed, "output_begin": emitted, **pin(gap)})
    return b"".join(parts), projection, protected


def transform_source(source, *, family, variant):
    """Project one pinned source; word additionally requires target type proof.

    A word candidate must pass the proof's C11 _Generic assertion with the actual
    compiler before use.  Equal widths alone do not prove pointer compatibility.
    """
    changes = _edits(family, variant)
    _, _, _, _, word = PROFILES[family]
    if type(source) is not bytes or (len(source), sha256(source).hexdigest()) not in ADMISSIONS[family]:
        raise ValueError("unknown combined TCEC source for getline experiment")
    macro = b"#define _POSIX_C_SOURCE 200809L\n"
    if source.count(macro) != 1 or source.index(macro) > source.index(b"#include"):
        raise ValueError("getline requires the admitted POSIX feature-test macro before headers")
    candidate, edits, protected = _patch(source, changes)
    restored, _, _ = _patch(candidate, tuple((role, new, old) for role, old, new in changes))
    if restored != source:
        raise ValueError("getline full source inverse differs")
    assertion = (f'_Static_assert(_Generic((size_t*)0,{word}*:1,default:0),'
                 '"getline size pointer type");') if variant == "word" else None
    return candidate, {
        "schema": SCHEMA, "family": family, "variant": variant,
        "input": pin(source), "output": pin(candidate), "edits": edits,
        "protected_spans": protected, "inverse_exact": True,
        "feature_test": "_POSIX_C_SOURCE=200809L before all system headers; stdio declares getline",
        "required_target_type_assertion": assertion,
        "contract": {
            "loop": "NULL pointer + zero capacity; getline >0; never inspect failed buffer",
            "memory": "one reusable buffer grows to longest line; process exit owns reclamation",
            "scope": "all NUL-free logical lines; unchanged 4096-position history limit",
            "unchanged": "all root/history/move/NBRQ/clock/search/thread logic and terminal policy",
        },
    }


def restore_source(candidate, proof):
    if proof.get("schema") != SCHEMA or pin(candidate) != proof.get("output"):
        raise ValueError("getline output identity differs")
    family, variant = proof.get("family"), proof.get("variant")
    changes = _edits(family, variant)
    original, _, _ = _patch(candidate, tuple((role, new, old) for role, old, new in changes))
    regenerated, expected = transform_source(original, family=family, variant=variant)
    if pin(original) != proof.get("input") or regenerated != candidate or expected != proof:
        raise ValueError("getline full inverse or protected-span proof differs")
    return original
