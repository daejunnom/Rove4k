"""Opt-in full C/E EP stage with canonical final include cleanup kept last.

The finite compact_ep owner edits the actual final source. The existing
source_edits owner transports that exact edit back through include cleanup.
This module composes their complete proofs; it owns no new splice algorithm,
compiler, codec, process, runtime qualification or default recipe selection.
"""
from hashlib import sha256
import json


SELF = "engines/experiments/tcec-next/profile_ep.py"
SCHEMA = "rove4k.profile-ep-source.v1"
DECLARATION = dict(path=SELF, variant="legal-maker")
NEXT = "engines/experiments/tcec-next/"
SUPPORT = {
    "ep": dict(path=NEXT + "compact_ep.py", bytes=7267,
               sha256="42963c889070f29da4dc05d08d5fc4749afb7aec36b0d00735ccc9d271215c6c",
               schema="rove4k.compact-ep-source.v1"),
    "projection": dict(path=NEXT + "spelling_compound.py", bytes=9472,
                       sha256="4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce",
                       schema="rove4k.selected-spelling-compound.v1"),
    "dependencies": dict(path=NEXT + "profile_dependencies.py", bytes=12217,
                         sha256="f7ab7f13e4d66d10ecd9f7bb8b8616dce3d88351aba4da43efaf519195dbc3b4",
                         schema="rove4k.profile-dependencies.v1"),
    "edits": dict(path=NEXT + "source_edits.py", bytes=3197,
                  sha256="11907bbdfc1e4629c61b4475ede0a6230fc3331e5d8fab445a6a5ca541cacf6b",
                  schema=None),
}
PROFILES = ("test-p4", "test-p28", "tcec-provisional")
COMPILER_VERSION = "cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
NATIVE_POLICY = "CE-legal-maker-gcc13-v1"
# Filled only from actual independently audited fresh cost source/native bytes.
# An absent profile is deliberately not admitted; no original control pin moves.
IMAGES = {
    ("C", "test-p4"): dict(
        source=dict(bytes=8164, sha256="c13d4216301b6a60390e7c7998225e3ff5a98ad19b2c9c3140d7b2664a1599fc"),
        native=dict(bytes=18568, sha256="d211a13ec4e32f68d8cf2afd7d6aec34505cb5f8a8cab2a48fd1773d63aec7ca")),
    ("C", "test-p28"): dict(
        source=dict(bytes=8197, sha256="b587635942dc331fd79c09788e0ef32f00d6293a68a75ee6525ab1b76c98b297"),
        native=dict(bytes=18568, sha256="2e4955879d5f6de9d63716f0095189282bf61c99f6db0c969e8532a8d3d200b6")),
    ("C", "tcec-provisional"): dict(
        source=dict(bytes=8166, sha256="c7b2ec5554f35af50f90b63f7c3c728c76d725d9de5a37aef96d95bbcb13b0f0"),
        native=dict(bytes=18568, sha256="93228167f95a684161c3e766873066af4b0a248fcc2c4faf6dd700334454ac53")),
    ("E", "test-p4"): dict(
        source=dict(bytes=7778, sha256="fc08a94db7593439322910bdc6bc3be307a1a8c3e65f948842a15f1cf7b95335"),
        native=dict(bytes=18568, sha256="95703fc67c112e3a9d50d70c0d25c6ffd25fc88939311343cdc53d0e1daaddac")),
    ("E", "test-p28"): dict(
        source=dict(bytes=7811, sha256="aa09156e76702f42068cfdba85e0e07ffc2f7dc63607b113cba6f5c694f8bbfb"),
        native=dict(bytes=18568, sha256="70a52840481b92f34ed52edf094251c8205bc5b2bea8492f28eac4e5d3b5eb78")),
    ("E", "tcec-provisional"): dict(
        source=dict(bytes=7780, sha256="d9da4822b16da457786b6517675015c7a91c110a6685ffb9444eea945bbcff58"),
        native=dict(bytes=18568, sha256="ba29db7adf798b9a1b816da7791facfb32e61b8ec751bf4525a04292be225311")),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def selection(family, representation, phase_variant, post_spelling, post_scan,
              dependencies, variant):
    require(type(variant) is str and variant in ("control", "legal-maker"),
            "finite EP selection required")
    if variant == "control":
        return None
    require(family in ("C", "E") and representation == "source-jit"
            and phase_variant == "phase-init"
            and post_spelling == dict(path=NEXT + "spelling_compound.py", selection="compound",
                                     variant="clock-atomic-launcher")
            and post_scan == (dict(path=NEXT + "profile_scan.py", variant="square-successor")
                              if family == "C" else None)
            and dependencies == "unused-includes",
            "EP requires selected C/E full source-JIT phase/compound, C square-successor and final include cleanup")
    return dict(DECLARATION)


def _context(family, profile_id, helpers):
    require(type(family) is str and family in ("C", "E")
            and type(profile_id) is str and profile_id in PROFILES,
            "finite full C/E profile required")
    require(set(helpers) == set(SUPPORT)
            and all(getattr(helpers[name], "SCHEMA", None) == row["schema"]
                    for name, row in SUPPORT.items()),
            "explicit authenticated EP/projection/dependency/edit owners required")


def transform_source(source, *, family, profile_id, ep, projection, dependencies, edits):
    helpers = dict(ep=ep, projection=projection, dependencies=dependencies, edits=edits)
    _context(family, profile_id, helpers)
    require(type(source) is bytes, "actual pre-cleanup full source bytes required")
    final, original_dependency = dependencies.transform_source(source)
    candidate, ep_proof = ep.transform_source(final, family=family, profile_id=profile_id,
                                             projection=projection)
    require(ep.restore_source(candidate, ep_proof, projection=projection) == final,
            "actual final-source EP inverse differs")
    lifted, final_dependency, commuting = edits.lift_source_edits(source, final, candidate,
        ep_proof, original_dependency, projection=projection, dependencies=dependencies)
    require(projection._inverse_edits(lifted, commuting["lifted_edits"]) == source,
            "complete pre-cleanup EP inverse differs")
    proof = dict(schema=SCHEMA, family=family, profile_id=profile_id, variant="legal-maker",
        input=pin(source), output=pin(lifted), support={key: dict(row) for key, row in SUPPORT.items()}, compact_ep=ep_proof,
        final_dependency=final_dependency, commuting=commuting, full_inverse=True,
        source_only=True, final_cleanup_last=True, resources_changed=False,
        models_changed=False, features_removed=False, production_default_changed=False,
        native_identity_claimed=False, runtime_qualified=False)
    return lifted, proof


def restore_source(candidate, proof, *, ep, projection, dependencies, edits):
    require(type(candidate) is bytes and type(proof) is dict and proof.get("schema") == SCHEMA
            and type(proof.get("commuting")) is dict and pin(candidate) == proof.get("output"),
            "complete lifted EP output proof required")
    _context(proof.get("family"), proof.get("profile_id"),
             dict(ep=ep, projection=projection, dependencies=dependencies, edits=edits))
    source = projection._inverse_edits(candidate, proof["commuting"]["lifted_edits"])
    require(pin(source) == proof.get("input"), "lifted EP inverse input differs")
    replay, expected = transform_source(source, family=proof["family"], profile_id=proof["profile_id"],
        ep=ep, projection=projection, dependencies=dependencies, edits=edits)
    require(replay == candidate and canonical(expected) == canonical(proof),
            "lifted EP support/domain/full-inverse/canonical-cleanup proof differs")
    return source


def native_policy(family, profile_id, source, compiler, compile_executor, version):
    require((family, profile_id) in IMAGES,
            "EP profile has no audited literal source/native cost policy yet")
    expected = ["cc", "-Os", *(["-mavx2"] if family == "C" else []), "-x", "c", "-", "-o", "x", "-s"]
    require(list(compiler) == list(compile_executor) == expected and version == COMPILER_VERSION,
            "EP requires its named GCC13 compiler; target compilers consume a sealed source")
    identities = IMAGES[family, profile_id]
    require(type(source) is bytes and pin(source) == identities["source"],
            "EP final source differs from its named profile policy")
    return dict(kind=NATIVE_POLICY, family=family, profile_id=profile_id,
        post_ep=dict(DECLARATION), compiler=expected, compiler_version=COMPILER_VERSION,
        source=dict(identities["source"]), native=dict(identities["native"]))
