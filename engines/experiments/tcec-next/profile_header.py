"""Finite opt-in B/F source-JIT header recipes with separate compiler roles.

The build compiler and its source/native proofs remain the original recipe.
Only the runtime wrapper compiler loses the named flags. Literal observations
below come from the independently audited six-profile GCC13/GCC11 trial; they
are not a portability rule or a replacement for current compiler receipts,
strict artifact admission, or actual runtime executable identity.

This owner is pure: it reads no files, loads no project code, runs no compiler
or codec, and grants no runtime qualification or maintained selection.
"""
from hashlib import sha256
import json


SELF = "engines/experiments/tcec-next/profile_header.py"
SCHEMA = "rove4k.profile-header.v1"
POLICY = "BF-minimal-wrapper-gcc13-gcc11-v1"
DECLARATION = dict(path=SELF, variant="minimal")
NEXT = "engines/experiments/tcec-next/"
PROFILES = ("test-p4", "test-p28", "tcec-provisional")
BUILD_VERSION = "cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
BUILD_COMPILERS = {
    "B": ("cc", "-std=c11", "-Os", "-pthread", "-x", "c", "-", "-o", "x"),
    "F": ("cc", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s"),
}
WRAPPER_COMPILERS = {
    "B": ("cc", "-Os", "-x", "c", "-", "-o", "x"),
    "F": ("cc", "-Os", "-x", "c", "-", "-o", "x", "-s"),
}
HEADERS = {
    "B": (b'#!/bin/bash\nset -eo pipefail\nf=`mktemp`\n'
          b'tail -n+6 "$0"|xz -d|cc -std=c11 -Os -pthread -xc - -o"$f"\nexec "$f"\n'),
    "F": (b'#!/bin/bash\nset -eo pipefail\nf=`mktemp`\n'
          b'tail -n+6 "$0"|xz -d|cc -Os -pthread -xc - -o"$f" -s\nexec "$f"\n'),
}
HOSTS = {
    "ubuntu24-gcc13-glibc239": dict(
        os="24.04", GCC="13.3.0", libc="2.39",
        compiler=dict(path="/usr/bin/x86_64-linux-gnu-gcc-13", bytes=1023032,
                      sha256="1b99826121ae6682a634e5efe09bd3e3df58ce58e0b28f849114ab5b89139c26")),
    "ubuntu22-gcc11-glibc235": dict(
        os="22.04", GCC="11.4.0", libc="2.35",
        compiler=dict(path="/usr/bin/x86_64-linux-gnu-gcc-11", bytes=928584,
                      sha256="821af3c74506283c179ca413bb33e6b528805a4dd8a5c09df125e5ad560a9e89")),
}
EVIDENCE = dict(
    run_id="40509200981", run_attempt="1",
    sha="65ee53f9a65ab0c68e7c90ccdc32839218537375",
    source_head="fe20d35f6a730f9a7a025e07ad5c6fb18e0cbb18",
    workflow_ref="daejunnom/Rove4k/.github/workflows/header-cost.yml@refs/pull/12/merge",
    named_inputs=dict(bytes=9685, sha256="34b7f013160b6c828ac517b78d187023bfb71e082c72ab5abf3ee9c6da27e7be"),
    audit=dict(bytes=53414, sha256="cb960a883f663342c515356e16fe1a2b87ecd632691f4fddd4620ab106620eb8"),
    observation="actual repeated control/minimal full CPP and whole native identity within each named host",
    cross_host_native_identity_claimed=False, replay_payload_produced=False)

# Source, payload and both whole pins are actual GCC13 producer artifacts.
# Native/CPP rows are separate actual observations for each named host. There
# is intentionally no interpolation across profiles, compilers or source edits.
ROWS = {
    ("B", "test-p4"): dict(
        source=(7934, "09546a75f5e417125ec033994fec52b1e23da4d504e5146a54cead53966136ce"),
        native13=(25744, "89b695055e8fbcdfd64f9cfd07e127180eb9827e4245631afd0525d2e0609e29"),
        CPP13=(86474, "6a0a7d4ef0ea8e8772c95f22e16e5a96c830e27de857e9f9cb8dee25c2ed2bb9"),
        native11=(25784, "74e6dbdbd58580cfa41e68c960fbb9bf5d58447522b2b398485545d11d37d91b"),
        CPP11=(83537, "95155f218b14eb4fa78975ba7bd93ec3f780cab60d47ac96417bf5b0f711e631"),
        payload=(3962, "2ff39681818973f97a03591af52d7ac77c6363aedd2e9df879e1e937d08f790e"),
        original=(4071, "c64753dc77b2c287d13612f985ed4c77d53caafc532530169ec328ee577dbeae"),
        minimal=(4053, "b0fe1879205bdcb6e6b3641d334858505b58f0b2c5c37a1d3dc5794c0ffeb438")),
    ("B", "test-p28"): dict(
        source=(7962, "326e18b0b480a42c16ab0c4ec06ff90770842aec2bd8c9e1ea91f70be9427eb6"),
        native13=(25744, "755dffaf68cb2eff582260550f6c7a174bb09de9e5bf7a773f311c7c1dce9a24"),
        CPP13=(86498, "035472cbc90fec536dba740642d8705f0ffbabc7141cc0f9774729d93145e8f3"),
        native11=(25784, "ad7b8fd60632c60131c147f401c16fcddd80afc0d4ab0110eea27f58851802b6"),
        CPP11=(83561, "67bb40a35e9a2f1bcc7422fed64130480ffb51177003f0b8d690b2d42f1db3b8"),
        payload=(3972, "987817e100c9371abe9bcbbdc7507f507e5ba1259d8a57fe788d470a55599b27"),
        original=(4081, "93634a5bb12dcef46e7e80242982511de3ef62db1e60c70ee082b24186f30123"),
        minimal=(4063, "aabfd4aa2b6d434cf275f0c4a89a75e4a583fa8674316d498a35aa27e290a2ae")),
    ("B", "tcec-provisional"): dict(
        source=(7936, "5f64922b49923ef9637dc41328761a4c3f4eb0063e39bd9f04c46e3d19c9b62d"),
        native13=(25744, "db780f8318783991535a56e3d26f3d9e18e3a139fdbd9f0ced56784f7f236613"),
        CPP13=(86490, "1488d1a3ebba36d58d0475fd8df743664959fb422be0eefb8ce53792c3275e77"),
        native11=(25784, "59006461d7c27e73e50816f0f41e46a5320509281ab106531ec976a6c3596818"),
        CPP11=(83553, "e76cc309df7156d89e2e9209da24107055604cab4f1e7bf5c71f5f3920026251"),
        payload=(3963, "e680022b57423066591d73d18918b3edb71e9e72669240ca6613ff7b69b9b180"),
        original=(4072, "2f1cd9e6559594fa6142188df851c8ff6a8e57edd4de49c14fcdbbb67214f6b6"),
        minimal=(4054, "99b90db98ebab923011fd8aa414b4d52948b58f0efede7fca55debf06796bfce")),
    ("F", "test-p4"): dict(
        source=(7030, "0aa062ec8440911d094a1b4eea48eceb96facfaa4ce94d654f46bfa19c83c7f0"),
        native13=(18568, "5b4e662a29f7a989c8b7a81f8a41e46a96df5c3e805f4b7b29929b6a2725ae50"),
        CPP13=(84898, "2246c3205e5cd947a7f2872876c4b582a1148adfeb728be3d81ee82770e8a495"),
        native11=(18568, "22acc4cbb0123b26e928f164a34ecaaee028a9fc37aec9fd8a0cfca1670557e1"),
        CPP11=(81961, "21e3ef97b87611e87fe74e9fa083fe3da1cd48b36f8a6db6b4bb0bb541f8fb20"),
        payload=(3484, "f31169149c99192d914e906dd13b601975e490528657cbec04371b3a14c34760"),
        original=(3587, "c4e5be74f6aed58b7407444119e4de834f9ee3e4c9e99998922685a4f80fd343"),
        minimal=(3578, "1293f6d9608004c43b5a7f97cef7a2fcbc411e13409e6a93f1de1684138034da")),
    ("F", "test-p28"): dict(
        source=(7063, "5a016f252e8efb4faf356de92397964d19e6c5e95863e063a5179864988dcdc5"),
        native13=(18568, "843bbc1ea78ef68c4cde578df93218f6d36b5f3c48cfa794ba6022b75e949262"),
        CPP13=(84922, "b98353decc4bb71bfefd602e975f44fadf5a9ad8c2645c5b7048a2ef47b1324e"),
        native11=(18568, "f0db697053301089aa0888ceb8709a0bfcae73fff28cdaa3eac4ed0445c1eaa0"),
        CPP11=(81985, "ec2de560e50338e506488275b3510bd5258b9b82d1aed48ec66186d6890981a6"),
        payload=(3499, "81905d60d0ba5f9ed48d307ad3281c503ec2c2099405f0c2c7dc40f9a1ab82ca"),
        original=(3602, "7c5b930a2a113a2cc294e97d56457896418f90b3df90eebfccba489b61342baa"),
        minimal=(3593, "6d327d551c204f5b27b25600468e121763fe9bf080046d8c12b1ee87fdbd41a3")),
    ("F", "tcec-provisional"): dict(
        source=(7032, "7701b38ad0957066d427bb085575f26b511691a6ea60e67f44835ce9359db9df"),
        native13=(18568, "e536de10e8792573548864d6267e8ce3cde76102b6134552f9dbca0d2672437b"),
        CPP13=(84914, "88c650632c7dedfcf4d3683c3d3e6e94d3e5b52e4db1fc9142a495776e2d523a"),
        native11=(18568, "6d5a221b7f13a0747652be4afa82b23253733799e2d810c8f822630abca0c872"),
        CPP11=(81977, "55b6e7203b182226fe5872a234a2f4b25d1735bcbad658f94d14630b1b05bb83"),
        payload=(3486, "90405436b74f2dc5e72a45340aff53b22a6c5845d8db40e4b62f890b268575b6"),
        original=(3589, "28f3f9024443b7dd63955b543ed2e6849905e1d0767a52c1d35ff51017889f30"),
        minimal=(3580, "97a4043791288cc7504a4284313aa955fe7a48de95ece3b737ddb5fe3ee7169a")),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "actual immutable bytes required")
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _copy(value):
    return json.loads(canonical(value))


def _pin(pair):
    return dict(bytes=pair[0], sha256=pair[1])


def _row(family, profile_id):
    require(type(family) is str and family in BUILD_COMPILERS
            and type(profile_id) is str and profile_id in PROFILES,
            "finite full B/F header profile required")
    return ROWS[family, profile_id]


def selection(family, representation, b_variant, phase_variant, post_spelling,
              post_scan, dependencies, variant, post_ep=None):
    """Controls acquire no new fields; minimal is an exact full-source recipe."""
    require(type(variant) is str and variant in ("control", "minimal"),
            "finite header selection required")
    if variant == "control":
        return None
    expected = (dict(path=NEXT + "profile_spelling.py", selection="best", variant="atomic-assignment")
                if family == "B" else dict(path=NEXT + "spelling_compound.py", selection="compound-v2",
                                             variant="clock-atomic-launcher-parentheses"))
    require(type(family) is str and family in BUILD_COMPILERS and representation == "source-jit"
            and (b_variant, phase_variant) == (("tcec-final-lf", "control") if family == "B"
                                                else ("control", "phase-init"))
            and post_spelling == expected and post_scan is None and post_ep is None
            and dependencies == "unused-includes",
            "minimal header requires the measured full B/F source-JIT spelling and final include cleanup")
    return dict(DECLARATION)


def transform_header(control_header, *, family, profile_id):
    """Return the exact finite deletion and a replayable complete inverse."""
    _row(family, profile_id)
    require(type(control_header) is bytes and control_header == HEADERS[family],
            "exact original five-line private-path header required")
    result = control_header
    tokens = (b" -std=c11", b" -pthread") if family == "B" else (b" -pthread",)
    for token in tokens:
        require(result.count(token) == 1, "unique measured compiler token required")
        result = result.replace(token, b"", 1)
    require(len(result.splitlines()) == 5 and len(result) - len(control_header) == (-18 if family == "B" else -9)
            and result.splitlines()[:3] == control_header.splitlines()[:3]
            and result.splitlines()[4:] == control_header.splitlines()[4:]
            and result.count(b'tail -n+6 "$0"|xz -d|cc -Os -xc - -o"$f"') == 1,
            "minimal header changed its source stream or file ownership")
    proof = dict(schema=SCHEMA, kind=POLICY, family=family, profile_id=profile_id,
        input=pin(control_header), output=pin(result),
        compiler=list(BUILD_COMPILERS[family]), wrapper_compiler=list(WRAPPER_COMPILERS[family]),
        deleted=[token.decode("ascii") for token in tokens], full_inverse=True,
        source_changed=False, build_compiler_changed=False, runtime_qualified=False, selected=False)
    return result, proof


def restore_header(header, proof):
    require(type(proof) is dict and proof.get("schema") == SCHEMA,
            "owned minimal header inverse proof required")
    family, profile_id = proof.get("family"), proof.get("profile_id")
    _row(family, profile_id)
    expected, expected_proof = transform_header(HEADERS[family], family=family, profile_id=profile_id)
    require(type(header) is bytes and header == expected and canonical(proof) == canonical(expected_proof),
            "minimal header/inverse/compiler-role proof differs")
    original = b"|cc -std=c11 -Os -pthread " if family == "B" else b"|cc -Os -pthread "
    restored = header.replace(b"|cc -Os ", original, 1)
    require(restored == HEADERS[family] and pin(restored) == proof["input"],
            "complete original header restoration differs")
    return restored


def expected_policy(family, profile_id):
    """Return measured literals, not admission of any caller's artifacts."""
    row = _row(family, profile_id)
    header, _ = transform_header(HEADERS[family], family=family, profile_id=profile_id)
    compatibility = {}
    for host, suffix in (("ubuntu24-gcc13-glibc239", "13"), ("ubuntu22-gcc11-glibc235", "11")):
        compatibility[host] = dict(context=_copy(HOSTS[host]), source=_pin(row["source"]),
            CPP=_pin(row["CPP" + suffix]), native=_pin(row["native" + suffix]),
            comparison="four actual control/minimal compilations and full CPP/native identity within this host")
    return dict(schema=SCHEMA, kind=POLICY, family=family, profile_id=profile_id,
        header_variant=dict(DECLARATION), compiler=list(BUILD_COMPILERS[family]),
        compile_executor=list(BUILD_COMPILERS[family]), compiler_version=BUILD_VERSION,
        wrapper_compiler=list(WRAPPER_COMPILERS[family]), source=_pin(row["source"]), native=_pin(row["native13"]),
        original=dict(header=pin(HEADERS[family]), payload=_pin(row["payload"]), whole=_pin(row["original"])),
        minimal=dict(header=pin(header), payload=_pin(row["payload"]), whole=_pin(row["minimal"])),
        compatibility=compatibility, evidence=_copy(EVIDENCE),
        requires_actual_compiler_receipts=True, requires_actual_runtime_image=True,
        source_changed=False, build_compiler_changed=False, runtime_qualified=False, selected=False)


def compiler_policy(family, profile_id, source, compiler, compile_executor, version):
    """Validate the original build recipe; return a separate wrapper recipe.

    The caller still authenticates actual compiler commands/context. Returning
    this record does not assert that a minimal-wrapper compiler was executed.
    """
    policy = expected_policy(family, profile_id)
    require(type(source) is bytes and pin(source) == policy["source"],
            "final source differs from the named minimal-header profile")
    require(type(compiler) in (list, tuple) and type(compile_executor) in (list, tuple)
            and list(compiler) == list(compile_executor) == policy["compiler"]
            and type(version) is str and version == BUILD_VERSION,
            "minimal header requires its unchanged original named GCC13 build compiler")
    directive = b"#define _POSIX_C_SOURCE 200809L\n"
    require(source.count(directive) == 1 and directive in source[:source.index(b"#include")],
            "measured explicit POSIX2008 source premise differs")
    return policy


def check_compiler_observation(policy, *, source, expanded, native, host, context):
    """Compare actual bytes/context to one finite historical observation.

    The I/O owner must authenticate these bytes and context from real settled
    commands. This function does not substitute for command/provenance checks.
    """
    require(type(policy) is dict, "named header compiler policy required")
    expected = expected_policy(policy.get("family"), policy.get("profile_id"))
    require(canonical(policy) == canonical(expected) and type(host) is str and host in HOSTS,
            "header policy or exact named compiler host differs")
    row = expected["compatibility"][host]
    require(type(context) is dict and canonical(context) == canonical(row["context"])
            and pin(source) == row["source"] and pin(expanded) == row["CPP"] and pin(native) == row["native"],
            "actual source/CPP/native/compiler context differs from its measured row")
    return _copy(row)


def check_artifacts(policy, *, source, native, control_header, header, payload, whole):
    """Check actual final files and recover the original dependency-cost whole.

    The returned control whole preserves the original compiler's dependency
    before/after package comparison. Header savings remain a separate proof.
    Payload decompression, compiler provenance and runtime identity stay with
    the existing strict producer/verifier; no codec or execution happens here.
    """
    require(type(policy) is dict, "named header artifact policy required")
    family, profile_id = policy.get("family"), policy.get("profile_id")
    expected = expected_policy(family, profile_id)
    require(canonical(policy) == canonical(expected), "header artifact policy differs")
    require(pin(source) == expected["source"] and pin(native) == expected["native"],
            "actual original build source/native differs")
    candidate, header_proof = transform_header(control_header, family=family, profile_id=profile_id)
    require(type(header) is bytes and header == candidate and restore_header(header, header_proof) == control_header,
            "actual wrapper header/full inverse differs")
    require(pin(payload) == expected["minimal"]["payload"] and type(whole) is bytes
            and whole == header + payload and pin(whole) == expected["minimal"]["whole"],
            "actual minimal payload/whole differs from the same-source measured package")
    original = control_header + payload
    require(pin(original) == expected["original"]["whole"]
            and len(whole) - len(original) == (-18 if family == "B" else -9),
            "restored original whole or independent header cost differs")
    proof = dict(schema=SCHEMA, kind=POLICY, family=family, profile_id=profile_id,
        policy=pin(canonical(expected).encode("utf-8")), source=pin(source), native=pin(native), payload=pin(payload),
        original=dict(header=pin(control_header), whole=pin(original)),
        minimal=dict(header=pin(header), whole=pin(whole)), header_inverse=header_proof,
        unchanged_payload=True, whole_delta=len(whole) - len(original),
        dependency_cost_uses_original_header=True, runtime_qualified=False, selected=False)
    return original, proof
