"""Finite entry projection for the selected full A/B/C/E/F ELF representation.

The fifteen pins are complete current P4/P28/W256 sources, including F compound-v2.
Only the private-argv0 unlink and its now-unused main parameters are removed.
Every other byte is protected. The old self_unlink inverse admits a different
historical stage and is deliberately not used to manufacture a parent proof.

The caller must authenticate the exact PROJECTION bytes before passing that
module. This module performs no reads, project imports, builds or execution.
The ELF consumer owns memfd/execveat packaging, source-chain admission and all
native, runtime, whole-file size and eligibility evidence.
"""
from hashlib import sha256
import json
import re


SCHEMA = "rove4k.elf-entry-mode.v1"
REPRESENTATION = "self-contained-elf"
PROFILES = ("test-p4", "test-p28", "tcec-provisional")
FAMILIES = ("A", "B", "C", "E", "F")
PROJECTION = {
    "path": "engines/experiments/tcec-next/spelling_compound.py",
    "bytes": 9472,
    "sha256": "4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce",
}
INPUTS = {
    ("A", "test-p4"): (7595, "02faeb563c435c02321fc6d497f54a31de01d9093be33bff5e44206a93dfbdc6"),
    ("A", "test-p28"): (7628, "f1d5465716752b23c31d63035bbcb94b12818a984c9afbc4ce20c0c843f82006"),
    ("A", "tcec-provisional"): (7597, "f85fa3716aed39fe9b2ca973ac3d87650dbac95dfa9cedbaf800ada4f6375a23"),
    ("B", "test-p4"): (7934, "09546a75f5e417125ec033994fec52b1e23da4d504e5146a54cead53966136ce"),
    ("B", "test-p28"): (7962, "326e18b0b480a42c16ab0c4ec06ff90770842aec2bd8c9e1ea91f70be9427eb6"),
    ("B", "tcec-provisional"): (7936, "5f64922b49923ef9637dc41328761a4c3f4eb0063e39bd9f04c46e3d19c9b62d"),
    ("C", "test-p4"): (8199, "86b7dd0e5f206d10086d098ce82083d4d12910df91a7f1215915727327f1d42a"),
    ("C", "test-p28"): (8232, "b3a968d2287a8418ce32b7b2f9f019c4695b55a32fd4f332eab89e16d012d2d0"),
    ("C", "tcec-provisional"): (8201, "ae131e49609b34eefaa54499f79f2aa738d103cbc800c1d7a70cde359106b807"),
    ("E", "test-p4"): (7815, "198bccf29d1441f63e3fd07b5da9ab4164fe3c31393af7ad35ab72d4d3fe08ff"),
    ("E", "test-p28"): (7848, "de83f406f1c7916277f71e75c4b6ac2a5aa77663ab9f7e3ec2af11e8480668b8"),
    ("E", "tcec-provisional"): (7817, "d3069c36dec5becdca14b69e49016b9a3a6b4c762da91471e7ba8c73debad4f3"),
    ("F", "test-p4"): (7030, "0aa062ec8440911d094a1b4eea48eceb96facfaa4ce94d654f46bfa19c83c7f0"),
    ("F", "test-p28"): (7063, "5a016f252e8efb4faf356de92397964d19e6c5e95863e063a5179864988dcdc5"),
    ("F", "tcec-provisional"): (7032, "7701b38ad0957066d427bb085575f26b511691a6ea60e67f44835ce9359db9df"),
}
OUTPUTS = {
    ("A", "test-p4"): (7567, "2d1affbe6da1dee8533e9b49a86bccf80177f8128788454dd460f32067d564da"),
    ("A", "test-p28"): (7600, "6bdd5e8f468d2d3045be9a0cc22eac35842cd887e1821f747c7a95b7cf4aa2f0"),
    ("A", "tcec-provisional"): (7569, "8293ce490aa30195285625ed6d5cd0855482630a1f7eb4553d30fa9a88adcc75"),
    ("B", "test-p4"): (7910, "a47984e36f57474cc9f5ed34a6c29a4d25d52a2daac45fc1c398cf3ba7a2fd74"),
    ("B", "test-p28"): (7938, "d8ebef763143eabbd254c8310d09d706f3e140efb946b33842748b8533e92f06"),
    ("B", "tcec-provisional"): (7912, "3f159fea6b3da82e3b721cab30c7e8a0a39d3aff432c0c52bc6b3b2927d6ff5c"),
    ("C", "test-p4"): (8164, "a1dcc2373aea7b1ccc5f20960bc7ef11a4da5f791001792c4fd50a99cab89e79"),
    ("C", "test-p28"): (8197, "844362b628c95221b3c704085be9b14c4161728b16a20a87bbd90c2651f9e103"),
    ("C", "tcec-provisional"): (8166, "2d3f87593094df7f360637e0f90d4f31b1d15d35f038505b460a2d9b33cb56d4"),
    ("E", "test-p4"): (7787, "7cd00a6b8939da73e5b202030743f40024b97e2ca63661085285e8bb1a9a9d3f"),
    ("E", "test-p28"): (7820, "fecee186efb23aa9d826bbeea762670fb087c385dc6669f0c96b33a3b97cd27e"),
    ("E", "tcec-provisional"): (7789, "5323f8afbd0ce27f8b583e8316d86009bfb4773a0c42afac45fa4d5cc0f62445"),
    ("F", "test-p4"): (7002, "a9d5d69f99d54598fb60c6ebbf9da945817fdfee65e7f404afe5c0517c7b26d5"),
    ("F", "test-p28"): (7035, "9979dcad56b580bd995721992e30e159c1e09c4ecc06770b05da103806af5671"),
    ("F", "tcec-provisional"): (7004, "cd8608273cc38c598cb86ad21d5e5634aceece62c2318ba6fd4320fbf721bb15"),
}
# These are the actual bindings in the pinned payloads. B's private parameters
# have been spelled v/w; equal names in earlier functions are separate bindings.
CONTEXT = {
    "A": dict(integer="L", returned="J", conditional="if", argc="z0", argv="z1"),
    "B": dict(integer="I", returned="l", conditional="W", argc="v", argv="w"),
    "C": dict(integer="int", returned="return", conditional="if", argc="z0", argv="z1"),
    "E": dict(integer="L", returned="J", conditional="if", argc="z0", argv="z1"),
    "F": dict(integer="S", returned="H", conditional="if", argc="z0", argv="z1"),
}
AFTER = "main(void){"
ROLE = "entry-private-argv0-cleanup"
COMPONENT = "elf-entry-mode"
EDIT_KEYS = {"input_begin", "output_begin", "before", "after", "role", "component"}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "immutable source bytes required")
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def _json(value):
    """Canonical proof comparison without tuple, float or bool/int aliases."""
    def check(item):
        if type(item) is dict:
            require(all(type(key) is str for key in item), "string proof keys required")
            for child in item.values():
                check(child)
        elif type(item) is list:
            for child in item:
                check(child)
        else:
            require(type(item) in (str, int, bool, type(None)), "typed finite JSON proof required")
    try:
        check(value)
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError("typed finite JSON proof required") from error


def _projection(projection):
    require(getattr(projection, "SCHEMA", None) == "rove4k.selected-spelling-compound.v1"
            and callable(getattr(projection, "_splice", None))
            and callable(getattr(projection, "_inverse_edits", None)),
            "caller-authenticated pinned compound projection required")


def _key(family, profile_id):
    require(type(family) is str and type(profile_id) is str
            and (family, profile_id) in INPUTS, "finite full A/B/C/E/F P4/P28/W256 profile required")
    return family, profile_id


def _before(family):
    require(type(family) is str and family in CONTEXT, "finite entry family required")
    c = CONTEXT[family]
    return (f"main({c['integer']} {c['argc']},char**{c['argv']}){{"
            f"{c['conditional']}(remove(*{c['argv']})){c['returned']} 2;")


def _identifiers(text):
    # Same literal/comment protection as the current profile_spelling.token_spans
    # owner. Exact input pins make the retained main tail a finite source region.
    pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/|[A-Za-z_][A-Za-z_0-9]*'
    return {match.group() for match in re.finditer(pattern, text)
            if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", match.group())}


def _entry_edit(source, family):
    """Build the one entry edit; this internal context check is not admission."""
    require(type(source) is bytes, "immutable source bytes required")
    try:
        text = source.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("ASCII entry source required") from error
    before, c = _before(family), CONTEXT[family]
    require(text.count(before) == 1 and text.count(c["integer"] + " " + before) == 1,
            "one exact typed private-argv0 entry required")
    definitions = {}
    for match in re.finditer(r"^#[ \t]*define[ \t]+([A-Za-z_][A-Za-z_0-9]*)([^\n]*)$", text, re.M):
        definitions.setdefault(match[1], []).append(match[2].strip())
    require(all(not definitions.get(keyword) for keyword in ("int", "return", "if", "void")),
            "entry keywords must retain their C meaning")
    for alias, keyword in ((c["integer"], "int"), (c["returned"], "return"),
                           (c["conditional"], "if")):
        require(definitions.get(alias, []) == ([] if alias == keyword else [keyword]),
                "actual entry int/return/if binding differs")
    at = text.index(before)
    retained_main = _identifiers(text[at + len(before):])
    require(c["argc"] not in retained_main and c["argv"] not in retained_main,
            "private entry parameters are used after the owned cleanup")
    return dict(input_begin=at, before=before, after=AFTER, role=ROLE, component=COMPONENT)


def _inverse(candidate, edits, *, family, projection):
    """Check the exact typed single span before using the pinned inverse owner."""
    require(type(candidate) is bytes and type(edits) is list and len(edits) == 1,
            "one typed entry inverse edit required")
    row = edits[0]
    require(type(row) is dict and set(row) == EDIT_KEYS
            and type(row["input_begin"]) is int and type(row["output_begin"]) is int
            and row["input_begin"] == row["output_begin"]
            and 0 <= row["output_begin"] <= len(candidate)
            and all(type(row[key]) is str for key in ("before", "after", "role", "component"))
            and row["before"] == _before(family) and row["after"] == AFTER
            and row["role"] == ROLE and row["component"] == COMPONENT,
            "exact typed entry inverse span required")
    return projection._inverse_edits(candidate, edits)


def _project(source, *, family, projection):
    """Internal finite spelling operation; public callers must use admission."""
    _projection(projection)
    candidate, edits, gaps = projection._splice(source, [_entry_edit(source, family)])
    require(len(edits) == 1 and len(gaps) == 2
            and _inverse(candidate, edits, family=family, projection=projection) == source,
            "entry projection shape or full inverse differs")
    for gap in gaps:
        old = source[gap["input_begin"]:gap["input_begin"] + gap["bytes"]]
        new = candidate[gap["output_begin"]:gap["output_begin"] + gap["bytes"]]
        require(old == new and pin(new) == {name: gap[name] for name in ("bytes", "sha256")},
                "entry projection protected complement differs")
    return candidate, edits, gaps


def transform_source(source, *, family, profile_id, projection):
    """Remove only private-argv0 cleanup from one exact selected full source."""
    key = _key(family, profile_id)
    require(type(source) is bytes and (len(source), sha256(source).hexdigest()) == INPUTS[key],
            "exact selected full entry source required")
    candidate, edits, gaps = _project(source, family=family, projection=projection)
    require((len(candidate), sha256(candidate).hexdigest()) == OUTPUTS[key],
            "exact finite ELF entry output required")
    proof = dict(schema=SCHEMA, family=family, profile_id=profile_id,
        representation=REPRESENTATION, entry_cleanup="none", input=pin(source), output=pin(candidate),
        projection=dict(PROJECTION), entry_context=dict(CONTEXT[family]), edits=edits,
        protected_gaps=gaps, full_inverse=True, raw_source_delta=len(candidate) - len(source),
        source_only=True, submitted_elf_preserved=True, resources_changed=False, search_changed=False,
        production_selected=False, native_identity_claimed=False, runtime_equivalence_claimed=False,
        elf_eligibility_claimed=False,
        scope="private-argv0 entry cleanup and unused parameters only; every other source byte protected")
    return candidate, proof


def restore_source(candidate, proof, *, projection):
    """Restore exact selected source and replay the complete typed proof."""
    require(type(candidate) is bytes and type(proof) is dict and proof.get("schema") == SCHEMA,
            "exact ELF entry candidate and complete proof required")
    supplied = _json(proof)
    key = _key(proof.get("family"), proof.get("profile_id"))
    require((len(candidate), sha256(candidate).hexdigest()) == OUTPUTS[key]
            and pin(candidate) == proof.get("output"), "finite ELF entry output identity differs")
    _projection(projection)
    source = _inverse(candidate, proof.get("edits"), family=key[0], projection=projection)
    repeated, expected = transform_source(source, family=key[0], profile_id=key[1], projection=projection)
    require(repeated == candidate and _json(expected) == supplied,
            "ELF entry proof, protected gaps or full canonical inverse differs")
    return source
