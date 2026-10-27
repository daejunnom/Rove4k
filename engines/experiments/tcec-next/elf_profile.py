#!/usr/bin/env python3
"""Produce and admit full ABCEF profiles as self-restoring Linux ELF files.

The parent is always a fresh, strictly admitted selected source-JIT build. Only
the reviewed entry cleanup is projected; include cleanup is replayed last and
checked on actual preprocessed input and native images. Two complete ELF builds
retain the original native image, interpreter, TLS and libraries. Runtime and
actual-source rules have separate consumers below. Size alone never qualifies.
The submission profile is compile/package-only; those consumers accept TEST
profiles and reject it before native admission, probes or available-RAM checks.

All generated files belong outside Git. Compilation, packing, rules probes and
engine execution require explicit CLI actions; importing this module does none.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = "engines/experiments/tcec-next/"
SELF = PREFIX + "elf_profile.py"
ENTRY = PREFIX + "elf_entry_mode.py"
PROJECTION = PREFIX + "spelling_compound.py"
DEPENDENCIES = PREFIX + "profile_dependencies.py"
BUILDER = PREFIX + "profile_build.py"
VERIFIER = PREFIX + "profile_verify.py"
RULES = PREFIX + "profile_rules.py"
OWNER = "engines/experiments/tcec-scope/build.py"
UTILITY = "engines/experiments/tiny-d-submission/structural_size.py"
ELF = "engines/scripts/elf_loader.py"
ELF_DEPENDENCIES = "engines/scripts/elf_dependencies.py"
PRODUCTION = "engines/scripts/production.py"
LOADER = ("engines/scripts/elf-loader/loader.c", "engines/scripts/elf-loader/loader.ld")
SUPPORT = (SELF, ENTRY, PROJECTION, DEPENDENCIES, BUILDER, VERIFIER, RULES,
           OWNER, UTILITY, ELF, ELF_DEPENDENCIES, PRODUCTION, *LOADER)
FIXED = {
    ENTRY: (12623, "28eb3f656bb35b4bcbf794bcf131302291ea62fda929b41f528dc97f6255d346"),
    PROJECTION: (9472, "4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce"),
    ELF_DEPENDENCIES: (13855, "93e5fe74050ffc60d3bfa06740c5bc96aa0a8f11d70d172d2bf489626d7a6601"),
}
CLASS = "rove4k-full-profile-elf-v1"
RULES_CLASS = "rove4k-full-profile-elf-rules-v1"
FAMILIES = ("A", "B", "C", "E", "F")
TEST_PROFILES = ("test-p4", "test-p28")
PROFILES = (*TEST_PROFILES, "tcec-provisional")
NATIVE_VARIANTS = ("baseline", "lean")
LEAN_FLAGS = ("-fno-asynchronous-unwind-tables", "-fno-unwind-tables", "-Wl,--build-id=none")
BANNER = "cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
MAX_FILE = 16 << 20
FSIZE = 8 << 20
WORK_SECONDS = 600
CLEANUP_SECONDS = 30
_EXECUTING_CODE = sys._getframe().f_code
# Source identities also belong to the entry owner. The remaining four literal
# identities authenticate the complete unchanged selected parent before edits.
CONTROL = {
    ("A", "test-p4"): ((18568, "dc2dc95fe41fc3ecb8dde3b5ace90961fb691caba45484cb8b55f31ebdce0a9e"), (3781, "afc51befbc02956e7b91a30f83f562e6e7c9a84531204dd2d9d84f9b813bf893"), (3687, "be6ef5c4266ac536b475157d39ec1e5e580ed51b13afd547dbb5ccdd734d1896")),
    ("A", "test-p28"): ((18568, "4303194fb29769c10fe0800377370cd6a64e94428e9b26123caee3aab2cd29c1"), (3790, "260e2025154d88cc8970e9aa12a4d08607827e3cc185852240b8755ea0f4f03b"), (3696, "fb44982d1bc75444f9968db0a0d8c1debcd52c0ecc8091131b2ea128291a7025")),
    ("B", "test-p4"): ((25744, "89b695055e8fbcdfd64f9cfd07e127180eb9827e4245631afd0525d2e0609e29"), (4071, "c64753dc77b2c287d13612f985ed4c77d53caafc532530169ec328ee577dbeae"), (3962, "2ff39681818973f97a03591af52d7ac77c6363aedd2e9df879e1e937d08f790e")),
    ("B", "test-p28"): ((25744, "755dffaf68cb2eff582260550f6c7a174bb09de9e5bf7a773f311c7c1dce9a24"), (4081, "93634a5bb12dcef46e7e80242982511de3ef62db1e60c70ee082b24186f30123"), (3972, "987817e100c9371abe9bcbbdc7507f507e5ba1259d8a57fe788d470a55599b27")),
    ("C", "test-p4"): ((18568, "16031542896ac9d28cf6e7d70f32a8eef041baff2e65bcf030edea7eae689462"), (3915, "48f201d454749957eb9ada8589de8d75d7e331571f6958e31a15542cf2d00546"), (3814, "eb3969b146752bb83d39192730346d8987afdd610d5a777a4b839f90421132ef")),
    ("C", "test-p28"): ((18568, "798beb0201c23da1de875be256d19626ee8a922c595c98588c5618a11d4a8544"), (3926, "362c2e81c1b7af8b629355e85e1347add5fc71c0605f517a9d1ca59d76a2192d"), (3825, "9a8c3aa148a1ee9cb9fb079cd3a8a180cf5cfdce6795e8a349d68d3abbb8771f")),
    ("E", "test-p4"): ((18568, "fafa02d83ca754ee094d3a38f0a78208465c4cf6acb98f470aa7e15b049cfead"), (3882, "872f64c2205e74e8100ded20bf2d4e13986f615af45b4bd4d46a885998ec3ba2"), (3788, "1beca73bd77c4094b0de9f50955776abd60a5eb56e5f460f72ec812b3f8843cc")),
    ("E", "test-p28"): ((18568, "562afe71a92484a8a9ebb472f29cfd3ad7421c4e128f196a888d3c67e1e3b109"), (3894, "796a7d86b783bb69760afb28bcc9c3e8000b50c92e4f714d5461dfe7c0d49baf"), (3800, "14bbdc83024f1036914a4f4fe7c187dad11c6a12f487e76de7958ff52da0bba9")),
    ("F", "test-p4"): ((18568, "5b4e662a29f7a989c8b7a81f8a41e46a96df5c3e805f4b7b29929b6a2725ae50"), (3587, "c4e5be74f6aed58b7407444119e4de834f9ee3e4c9e99998922685a4f80fd343"), (3484, "f31169149c99192d914e906dd13b601975e490528657cbec04371b3a14c34760")),
    ("F", "test-p28"): ((18568, "843bbc1ea78ef68c4cde578df93218f6d36b5f3c48cfa794ba6022b75e949262"), (3602, "7c5b930a2a113a2cc294e97d56457896418f90b3df90eebfccba489b61342baa"), (3499, "81905d60d0ba5f9ed48d307ad3281c503ec2c2099405f0c2c7dc40f9a1ab82ca")),
    ("A", "tcec-provisional"): ((18568, "e5a644a334125a96e60f495fb24d40b00c8f7cc16a3a3dc7195494fc0a5dd4b7"), (3782, "54924a8ad75e0b5304c38b1dfdca69d9006fe2c23603c0bd1d76eba5fe56a346"), (3688, "a0e71d239bb9ca0bccd5a323cc5368334a673dd691d4dbc4f7f1f74d9553adbc")),
    ("B", "tcec-provisional"): ((25744, "db780f8318783991535a56e3d26f3d9e18e3a139fdbd9f0ced56784f7f236613"), (4072, "2f1cd9e6559594fa6142188df851c8ff6a8e57edd4de49c14fcdbbb67214f6b6"), (3963, "e680022b57423066591d73d18918b3edb71e9e72669240ca6613ff7b69b9b180")),
    ("C", "tcec-provisional"): ((18568, "3850273327e027346316df07b94c88f7e6b7df44da8dbbffbae69d777ed7c459"), (3915, "1c34d6b25453a61b3daf9f10ff7db3b6d3e8dcd2cf0135eaf0c0e8743f512961"), (3814, "189149a70c6e6cb6c549849b34b0a99eb566ff6aa4065b68a8585abeb8eba8de")),
    ("E", "tcec-provisional"): ((18568, "cddcae2dcbd2ea4a8e4e6ccffc9da1d507d60b972d41da2c9e692c93fd149b80"), (3883, "1732d897f9953a40db6ed290afe171502cda588205f03be05a2b2f847ecb1029"), (3789, "648c36dec4118f5d81aeb42b5d41f969e0ac4d8ab63984f0c4ea4c6fc53582de")),
    ("F", "tcec-provisional"): ((18568, "e536de10e8792573548864d6267e8ce3cde76102b6134552f9dbca0d2672437b"), (3589, "28f3f9024443b7dd63955b543ed2e6849905e1d0767a52c1d35ff51017889f30"), (3486, "90405436b74f2dc5e72a45340aff53b22a6c5845d8db40e4b62f890b268575b6")),
}
HEADERS = {
    "A": (94, "44b95bde0944d710e4bd20c4ab2a8c3d380c824bfc442f54e69901e6bb32406e"),
    "B": (109, "579c456c8ca9af8acde4bc4a41307807bc85d76d11b56ec5fcdcaa7e304ed911"),
    "C": (101, "05292d5798f864fcd3fee2d387e258d7105085d6753a123100dd246796bf4a38"),
    "E": (94, "44b95bde0944d710e4bd20c4ab2a8c3d380c824bfc442f54e69901e6bb32406e"),
    "F": (103, "de8e199aa72661012417d5a9004e3c4c5079d704d6558286bd282319c078a8a0"),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "immutable artifact bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def expected(pair):
    return {"bytes": pair[0], "sha256": pair[1]}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def plan(family, profile_id="test-p4", *, native_variant="baseline"):
    require(type(family) is str and family in FAMILIES and type(profile_id) is str
            and profile_id in PROFILES, "finite full ABCEF test or tcec-provisional profile required")
    require(type(native_variant) is str and native_variant in NATIVE_VARIANTS,
            "finite baseline/lean native compiler variant required")
    control_compiler = ["cc", *(["-std=c11"] if family == "B" else []), "-Os",
                *(["-pthread"] if family in ("B", "F") else []),
                *(["-mavx2"] if family == "C" else []), "-x", "c", "-", "-o", "x",
                *([] if family == "B" else ["-s"])]
    at = control_compiler.index("-x")
    # The strict source-JIT parent keeps its original compiler. Only the opt-in
    # derived native suppresses unwind/build-id metadata and adds B's missing
    # strip flag. The full compiler ELF remains the pack/restore/runtime image.
    extra = [*LEAN_FLAGS, *([] if "-s" in control_compiler else ["-s"])] if native_variant == "lean" else []
    compiler = [*control_compiler[:at], *extra, *control_compiler[at:]]
    return dict(family=family, profile=profile_id, full=True, representation="self-contained-elf",
        purpose="test" if profile_id in TEST_PROFILES else "submission", execution_policy="compile-package-only",
        runtime_profile_supported=profile_id in TEST_PROFILES,
        entry_cleanup="none", native_variant=native_variant, control_compiler=control_compiler,
        compiler=compiler, compiler_version=BANNER,
        work_seconds=WORK_SECONDS, cleanup_seconds=CLEANUP_SECONDS,
        outer_commands=10,
        size_limit_bytes=4096, packing_filter="auto", loader_timeout_seconds=120,
        runtime_external_programs=[], runtime_qualified=False, submission_qualified=False,
        event_target_confirmed=False, selected=False)


def require_test_profile(profile_id):
    """Submission profiles are preparation-only; never inspect RAM or run probes."""
    require(type(profile_id) is str and profile_id in TEST_PROFILES,
            "runtime, rules and qualification require test-p4/test-p28; submission profile is compile/package-only")


def factory_argv(family, output, profile_id="test-p4"):
    plan(family, profile_id)
    return [sys.executable, "-I", "-B", str(ROOT / BUILDER), "--entry", family,
        "--profile", profile_id, "--representation", "source-jit", "--b-variant",
        "tcec-final-lf" if family == "B" else "control", "--phase-variant",
        "control" if family == "B" else "phase-init", "--spelling-variant",
        "best" if family == "B" else "compound-v2" if family == "F" else "compound",
        "--source-dependencies", "unused-includes",
        *(["--scan-variant", "square-successor"] if family in ("A", "C") else []),
        "--out", str(output)]


def read_source(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_FILE,
            "bounded named regular source required")
    data = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named source")
    return data


def capture():
    files = {name: read_source(ROOT / name) for name in SUPPORT}
    require(compile(files[SELF], _EXECUTING_CODE.co_filename, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "executing ELF owner differs from captured source")
    for name, identity in FIXED.items():
        require(pin(files[name]) == expected(identity), "reviewed ELF source owner differs: " + name)
    return files


def load_bytes(name, logical, data):
    spec = importlib.util.spec_from_file_location(name, ROOT / logical)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(ROOT / logical), "exec", dont_inherit=True), module.__dict__)
    return module


def modules(files):
    return {name: load_bytes("elf_profile_" + name, path, files[path]) for name, path in (
        ("R", VERIFIER), ("entry", ENTRY), ("projection", PROJECTION),
        ("dependencies", DEPENDENCIES), ("elf", ELF), ("elf_dependencies", ELF_DEPENDENCIES),
        ("production", PRODUCTION))}


def write(root, name, data):
    require(type(data) is bytes and len(data) <= MAX_FILE, "bounded output bytes required")
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def json_bytes(record):
    return (json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def settled(commands):
    return type(commands) is list and bool(commands) and all(
        type(row) is dict and row.get("started") is True and row.get("terminal") is True
        and row.get("reaped") is True and type(row.get("returncode")) is int
        and row["returncode"] == 0 and row.get("owned_group_absent") is True
        and row.get("forced_cleanup") is False
        and row.get("other_group_members_before_reap") == []
        and row.get("original_identity_retained_until_other_members_absent") is True for row in commands)


def limit_plan(cpu, address_space, file_size):
    for pair in (cpu, address_space, file_size):
        require(type(pair) is tuple and len(pair) == 2
                and all(type(n) is int and (n == -1 or n > 0) for n in pair),
                "positive inherited resource pair required")
        require(pair[1] == -1 or pair[0] != -1 and pair[0] <= pair[1], "inconsistent inherited limits")
    hard = min([630] + ([cpu[1]] if cpu[1] != -1 else []))
    soft = min([600, hard] + ([cpu[0]] if cpu[0] != -1 else []))
    require(hard >= 480 and all(n == -1 or n >= 4 << 30 for n in address_space),
            "fresh unchanged factory requires CPU480 and AS4GiB")
    fsize = min([FSIZE] + [n for n in file_size if n != -1])
    return dict(parent_CPU=(soft, hard), parent_AS=4 << 30, FSIZE=(fsize, fsize))


def run_command(host, owner, command, *, cwd, kind, data=None, factory=False):
    require(len(host.report["commands"]) < host.report["outer_command_limit"], "finite outer command cap exceeded")
    previous = dict(owner.LIMITS)
    limits = dict(AS=4 << 30, CPU=480) if factory else dict(AS=2 << 30, CPU=120)
    owner.LIMITS.update(child_AS=limits["AS"], child_CPU=limits["CPU"])
    first = len(host.report["commands"])
    try:
        return host.run(command, cwd=cwd, kind=kind, data=data)
    finally:
        owner.LIMITS.clear()
        owner.LIMITS.update(previous)
        for row in host.report["commands"][first:]:
            require(row.get("child_limits") == limits, "actual child bounds differ")
            for stream in ("stdout", "stderr"):
                if stream in row:
                    path = Path(row[stream]["path"])
                    require(path.is_file() and path.stat().st_size <= FSIZE, "individual stdio cap exceeded")
        host.save()


def parent_artifacts(manifest, build, family, profile_id, m):
    """Strict current factory admission plus all five literal selected pins."""
    R, entry = m["R"], m["entry"]
    admitted = R.admit_c_build(manifest, build)
    policy = plan(family, profile_id)
    require(admitted.family == family and admitted.profile_id == profile_id and admitted.full is True
            and admitted.representation == "source-jit" and manifest["plan"]["entry_cleanup"] == "private-path"
            and manifest["compiler"] == policy["control_compiler"]
            and manifest["compile_executor"] == policy["control_compiler"]
            and manifest["compile_executor_version"] == BANNER, "fresh strict parent context differs")
    control = json.loads(R.checked_artifact(build, "control/build.json", manifest["control"]["report"]))
    for record, kind in ((manifest, "rove4k-production-profile-v1"), (control, "tcec-full-C-v1")):
        require(type(record) is dict and type(record.get("format")) is int and record["format"] == 1
                and record.get("class") == kind and record.get("family") == family and record.get("entry") == family
                and record.get("complete") is True and record.get("reproducible") is True
                and record.get("host_cleanup") == {"unsettled_commands": 0, "errors": []}
                and settled(record.get("commands")), "complete settled factory and control receipts required")
    native, whole, payload = CONTROL[family, profile_id]
    identities = dict(source=expected(entry.INPUTS[family, profile_id]), native=expected(native),
                      whole=expected(whole), payload=expected(payload), header=expected(HEADERS[family]))
    artifacts = {key: R.checked_artifact(build, path, identities[key]) for key, path in (
        ("source", "main.c"), ("native", "native/x"), ("whole", "x"),
        ("header", "header.sh"), ("payload", "payload.lzma"))}
    require(artifacts["whole"] == artifacts["header"] + artifacts["payload"], "five-part selected control differs")
    return admitted, artifacts


def validate_target_abi_absence(manifest, family):
    """Bind the current finite route's lack of an extra ABI probe to its owner.

    B's selected tcec-final-lf preserves ordinary mmap spelling and emits no
    mmap-abi probe. Another owning proof requires a separately reviewed finite
    policy; this producer never invents assertions or a future compiler branch.
    """
    stages = manifest.get("source_proofs")
    require(type(stages) is list and all(type(stage) is dict for stage in stages),
            "strict parent source proof chain required before ABI lookup")
    owners = [stage for stage in stages if stage.get("schema") == "rove4k.profile-b-source.v1"]
    require(all("target_abi_probe" not in stage for stage in stages if stage not in owners),
            "target ABI probe must belong to the B profile proof")
    if family != "B":
        require(not owners, "unexpected B ABI proof owner in another family")
        return
    post = manifest.get("post_profile")
    require(len(owners) == 1 and type(post) is dict
            and post.get("path") == PREFIX + "profile_b.py"
            and owners[0].get("variant") == post.get("variant") == "tcec-final-lf",
            "one matching admitted B profile proof owner required")
    require("target_abi_probe" not in owners[0], "unexpected B target ABI probe requires a reviewed finite policy")


def derive_source(source, old_dependency, *, family, profile_id, entry, projection, dependencies):
    """Lift the one reviewed entry edit through real final include cleanup."""
    before = dependencies.restore_source(source, old_dependency)
    replay, replay_proof = dependencies.transform_source(before)
    require(replay == source and canonical(replay_proof) == canonical(old_dependency), "parent final dependency relation differs")
    candidate, entry_proof = entry.transform_source(source, family=family, profile_id=profile_id, projection=projection)
    require(entry.restore_source(candidate, json.loads(canonical(entry_proof)), projection=projection) == source,
            "complete entry inverse differs")
    spans = old_dependency["spans"]
    require(type(spans) is list and len(spans) <= 1, "finite original include cleanup required")
    offset, removed = None, b""
    if spans:
        span = spans[0]
        offset, removed = span["offset"], span["before"].encode("ascii")
        require(type(offset) is int and 0 <= offset <= len(source) and removed == dependencies.DIRECTIVE
                and span["after"] == "" and before[:offset] == source[:offset]
                and before[offset:offset + len(removed)] == removed and before[offset + len(removed):] == source[offset:],
                "one exact original include deletion required")
    lifted = []
    for edit in entry_proof["edits"]:
        at, length = edit["input_begin"], len(edit["before"].encode("ascii"))
        if spans:
            require(at >= offset or at + length <= offset, "entry edit crosses removed include")
            at += len(removed) if at >= offset else 0
        lifted.append({key: edit[key] for key in ("before", "after", "role", "component")} | {"input_begin": at})
    pre_dependency, edits, gaps = projection._splice(before, lifted)
    require(projection._inverse_edits(pre_dependency, edits) == before, "lifted full entry inverse differs")
    final, dependency_proof = dependencies.transform_source(pre_dependency)
    require(final == candidate and dependencies.restore_source(final, dependency_proof) == pre_dependency,
            "entry and final dependency cleanup do not commute")
    return final, pre_dependency, dict(entry=entry_proof, dependency=dependency_proof,
        original_dependency=old_dependency, lifted_edits=edits, protected_gaps=gaps,
        original_pre_dependency=pin(before), pre_dependency=pin(pre_dependency),
        canonical_cleanup_last=True, complete_parent_inverse=True)


def packed_restore(whole, native, detail, *, elf, dependency):
    """Consume real payload bytes and dependency tables, never metadata flags."""
    require(type(whole) is bytes and type(native) is bytes and len(whole) <= MAX_FILE
            and len(native) <= MAX_FILE and type(detail) is dict, "bounded actual ELF bytes and metadata required")
    count = detail.get("payload_bytes")
    require(type(count) is int and 0 < count < len(whole), "typed actual ELF payload extent required")
    selected_filter = detail.get("filter")
    require(selected_filter in ("none", "bcj") and detail.get("requested_filter") == "auto"
            and detail.get("format") == "elf64-x86_64-self-restoring"
            and detail.get("codec") == "rove4k-lz-runs-v1"
            and detail.get("runtime_external_tools") == []
            and detail.get("input_bytes") == len(native) and detail.get("input_sha256") == pin(native)["sha256"]
            and detail.get("output_bytes") == len(whole) and detail.get("output_sha256") == pin(whole)["sha256"]
            and detail.get("loader_and_headers_bytes") == len(whole) - count
            and detail.get("size_limit_bytes") == 4096 and type(detail.get("within_size_limit")) is bool
            and detail["within_size_limit"] == (len(whole) <= 4096)
            and detail.get("input_elf") == elf._elf(native), "actual ELF pack identity/contract differs")
    payload = whole[-count:]
    restored = elf._decompress(payload, len(native))
    if selected_filter == "bcj":
        restored = elf._bcj(restored, inverse=True)
    require(restored == native, "complete restored native ELF differs")
    filtered = native if selected_filter == "none" else elf._bcj(native)
    require(elf._compress(filtered) == payload, "selected actual codec payload does not reproduce")
    candidates = detail.get("filter_candidates")
    require(type(candidates) is list and len(candidates) == 2
            and [row.get("filter") for row in candidates] == ["none", "bcj"], "both finite loader candidates required")
    for row in candidates:
        require(type(row.get("output_bytes")) is int and row["output_bytes"] > 0
                and type(row.get("payload_bytes")) is int and row["payload_bytes"] > 0
                and type(row.get("loader_and_headers_bytes")) is int and row["loader_and_headers_bytes"] > 0
                and row["output_bytes"] == row["payload_bytes"] + row["loader_and_headers_bytes"],
                "candidate whole component accounting differs")
    selected = min(candidates, key=lambda row: row["output_bytes"])
    require(selected["filter"] == selected_filter and all(selected[key] == detail[key] for key in
            ("output_bytes", "output_sha256", "payload_bytes", "loader_and_headers_bytes", "compiler_options")),
            "selected complete ELF is not the finite minimum")
    native_meta, outer_meta = dependency.inspect_dependencies(native), dependency.inspect_dependencies(whole)
    require(outer_meta["interpreter"] is None and not outer_meta["has_dynamic"] and not outer_meta["needed"],
            "outer loader must be static with no runtime dynamic dependency")
    return dict(native=native_meta, outer=outer_meta,
                native_policy=dependency.check_tcec_policy(native_meta),
                outer_policy=dependency.check_tcec_policy(outer_meta)), whole[:-count], payload


def _expected_artifacts(source, native, whole, header, payload):
    return {prefix + "_" + key: value for prefix, data in (
        ("source", source), ("native", native), ("whole", whole), ("header", header), ("payload", payload))
        for key, value in pin(data).items()}


def _bounded_host(out, report, save, files, started):
    """Reuse the existing owner and the single whole-work deadline."""
    import resource
    owner = load_bytes("elf_profile_process_owner", OWNER, files[OWNER])
    require(owner.EXECUTING_BUILD == files[OWNER], "process owner reread differs")
    inherited = {"CPU": resource.getrlimit(resource.RLIMIT_CPU), "AS": resource.getrlimit(resource.RLIMIT_AS),
                 "FSIZE": resource.getrlimit(resource.RLIMIT_FSIZE)}
    applied = limit_plan(inherited["CPU"], inherited["AS"], inherited["FSIZE"])
    resource.setrlimit(resource.RLIMIT_FSIZE, applied["FSIZE"])
    previous = dict(owner.LIMITS)
    remaining = math.floor(WORK_SECONDS - (time.monotonic() - started))
    require(remaining > 0, "whole work budget expired before owner construction")
    owner.LIMITS.update(aggregate_wall=remaining, per_command_wall=WORK_SECONDS,
        parent_AS=applied["parent_AS"], parent_CPU=applied["parent_CPU"][0],
        parent_CPU_hard=applied["parent_CPU"][1], tool_output_bytes=MAX_FILE)

    class Host(owner.Host):
        def settle(self, child, row, force=False):
            if row.get("kind") == "fresh-profile":
                row["cooperative_termination_seconds"] = 15
            return super().settle(child, row, force)

    host = Host(out, report, save)
    report["limits"] = dict(inherited=inherited, applied=applied, work_seconds=WORK_SECONDS,
        cleanup_budget_seconds=CLEANUP_SECONDS, aggregate_work_alarm_seconds=remaining,
        individual_stdio_bytes=FSIZE, combined_stdio_bytes=MAX_FILE,
        actual_parent_CPU=resource.getrlimit(resource.RLIMIT_CPU), actual_parent_AS=resource.getrlimit(resource.RLIMIT_AS),
        actual_FSIZE=resource.getrlimit(resource.RLIMIT_FSIZE))
    return owner, previous, host


def produce(family, out, *, profile_id="test-p4", native_variant="baseline", execute=False):
    require(execute is True, "explicit --execute required before output creation or factory execution")
    policy = plan(family, profile_id, native_variant=native_variant)
    require(sys.platform == "linux" and platform.machine() == "x86_64" and os.sysconf("SC_PAGE_SIZE") == 4096,
            "Linux x86-64 with actual 4096-byte base pages required")
    started, files = time.monotonic(), capture()
    utility = load_bytes("elf_profile_cost_utility", UTILITY, files[UTILITY])
    out = utility.new_output(out)
    out.mkdir(parents=True)
    for name, data in files.items():
        write(out / "support", name, data)
    report = dict(format=1, **{"class": CLASS}, family=family, profile=profile_id, complete=False,
        reproducible=False, native_variant=native_variant, control_compiler=policy["control_compiler"],
        policy=policy, commands=[], attempts=[], source_root=str(ROOT),
        artifact_directory=str(out),
        support={name: pin(data) for name, data in files.items()}, outer_command_limit=policy["outer_commands"],
        engine_executed=False, TT_allocated=False, runtime_qualified=False, elf_qualified=False, selected=False,
        execution_policy="compile-package-only", submission_qualified=False, event_target_confirmed=False,
        host_context=dict(python=sys.version, uname=list(os.uname()), load_page_bytes=os.sysconf("SC_PAGE_SIZE")),
        actual={"source": "main.c", "native": "native/x", "program": "x"})

    def save():
        (out / "build.json").write_bytes(json_bytes(report))

    save()
    owner = previous = host = None
    body_error = None
    previous_chld = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    try:
        owner, previous, host = _bounded_host(out, report, save, files, started)
        m, parent = modules(files), out / "fresh-profile"
        R = m["R"]
        run_command(host, owner, factory_argv(family, parent, profile_id), cwd=out, kind="fresh-profile", factory=True)
        parent_raw = R.input_reader().read_regular(R.artifact_file(parent, "build.json"), limit=MAX_FILE)
        parent_manifest = json.loads(parent_raw)
        admitted, artifacts = parent_artifacts(parent_manifest, parent, family, profile_id, m)
        validate_target_abi_absence(parent_manifest, family)
        require(all(R.checked_artifact(parent, "inputs/" + name, admitted.input_pins[name]) == data
                    for name, data in files.items() if name in admitted.input_pins), "factory and captured support differ")
        inputs = {name: R.checked_artifact(parent, "inputs/" + name, identity)
                  for name, identity in admitted.input_pins.items()}
        for name, data in files.items():
            require(name not in inputs or inputs[name] == data, "source closure identity conflict")
            inputs[name] = data
        for name, data in inputs.items():
            write(out / "inputs", name, data)
        final, before, proof = derive_source(artifacts["source"], parent_manifest["source_proofs"][-1],
            family=family, profile_id=profile_id, entry=m["entry"], projection=m["projection"], dependencies=m["dependencies"])
        assertions = parent_manifest["source_proofs"][0]["target_type_assertions"]
        require(type(assertions) is list and assertions and all(type(value) is str and value.startswith("_Static_assert(")
                for value in assertions), "actual selected resource type assertions required")
        compiler = policy["compiler"]
        actual_banner = run_command(host, owner, [compiler[0], "--version"], cwd=out,
                                    kind="compiler-version").decode("utf-8", "strict").splitlines()[0]
        require(actual_banner == BANNER, "actual projected compiler context differs")
        report.update(parent_manifest=pin(parent_raw), inputs={name: pin(data) for name, data in inputs.items()},
            resources=admitted.resources, runtime_policy=admitted.runtime_policy, source_proof=proof,
            compiler=compiler, compile_executor_version=actual_banner,
            source_closure=dict(parent=parent_manifest["source_closure"], derived_tools=list(SUPPORT)),
            factory_profile_commands=parent_manifest["commands"],
            factory_control_commands=json.loads(R.checked_artifact(parent, "control/build.json",
                parent_manifest["control"]["report"]))["commands"],
            nested_command_count_is_not_exhaustive_physical_process_count=True)
        api = m["production"]
        actual_plan = api.ArtifactPlan(api.engine_spec(family), api.resource_profile(profile_id), "self-contained-elf", "none", full=True)
        report["plan"] = actual_plan.to_record()
        for attempt in ("first", "repeat"):
            directory = out / attempt
            native_dir, type_dir = directory / "native", directory / "types"
            native_dir.mkdir(parents=True)
            type_dir.mkdir()
            write(directory, "main.c", final)
            write(directory, "pre-dependency.c", before)
            write(directory, "source-proof.json", json_bytes(proof))
            asserted = before + b"\n" + ("\n".join(assertions) + "\n").encode()
            write(type_dir, "asserted.c", asserted)
            run_command(host, owner, compiler, cwd=type_dir, kind=attempt + "-types", data=asserted)
            run_command(host, owner, compiler, cwd=native_dir, kind=attempt + "-native", data=final)
            native = R.input_reader().read_regular(native_dir / "x", limit=MAX_FILE)
            require(R.input_reader().read_regular(type_dir / "x", limit=MAX_FILE) == native,
                    "pre-cleanup asserted native and final native differ")
            cpp_source = before if attempt == "first" else final
            expanded = run_command(host, owner, m["dependencies"].preprocess_command(compiler),
                cwd=directory, kind=attempt + "-CPP", data=cpp_source)
            write(directory, "expanded.i", expanded)
            raw = run_command(host, owner, [sys.executable, "-I", "-B", str(ROOT / ELF),
                str(native_dir / "x"), str(directory / "x"), "--cc", compiler[0], "--timeout", "120", "--filter", "auto"],
                cwd=directory, kind=attempt + "-pack")
            detail = json.loads(raw)
            write(directory, "pack.json", raw)
            whole = R.input_reader().read_regular(directory / "x", limit=MAX_FILE)
            dependency, header, payload = packed_restore(whole, native, detail, elf=m["elf"], dependency=m["elf_dependencies"])
            write(directory, "header.bin", header)
            write(directory, "payload.bin", payload)
            report["attempts"].append(dict(directory=attempt,
                expected=_expected_artifacts(final, native, whole, header, payload),
                pre_dependency=pin(before), asserted=pin(asserted), CPP=pin(expanded),
                CPP_input=pin(cpp_source), CPP_stage="before-cleanup" if attempt == "first" else "final",
                source_proof=proof, dependencies=dependency, pack=detail,
                target_type_gate=dict(image_identical=True, assertions=assertions)))
            save()
        first, repeat = report["attempts"]
        for key in ("expected", "pre_dependency", "asserted", "CPP", "source_proof", "dependencies", "target_type_gate"):
            require(canonical(first[key]) == canonical(repeat[key]), "complete derived source/native/CPP reproduction differs: " + key)
        stable_pack = lambda value: {key: child for key, child in value.items() if key not in ("input", "output")}
        require(canonical(stable_pack(first["pack"])) == canonical(stable_pack(repeat["pack"])),
                "complete independent loader metadata reproduction differs")
        for name in ("main.c", "pre-dependency.c", "source-proof.json", "native/x", "types/x", "types/asserted.c",
                     "expanded.i", "x", "header.bin", "payload.bin"):
            data = R.input_reader().read_regular(out / "first" / name, limit=MAX_FILE)
            require(data == R.input_reader().read_regular(out / "repeat" / name, limit=MAX_FILE),
                    "independent actual artifact bytes differ: " + name)
            write(out, name, data)
        # Byte publication creates a new inode; retain the actual submission's
        # executable mode rather than inheriting the data-file creation mode.
        (out / "x").chmod(0o755)
        expected_contract = first["expected"]
        report.update(expected_contract=expected_contract, reproducible=True,
            wrapper_contract=dict(policy="self-contained-memfd-loader", entry_cleanup="none",
                temp_strategy="anonymous-memfd-execveat", cleanup_seconds=0, parent_removed=False,
                runtime_external_tools=[], submitted_file_preserved=True),
            size_decisions=[actual_plan.size_decision(expected_contract["whole_bytes"], division)
                            for division in ("general4k", "elf4k")],
            status=("deferred_size" if expected_contract["whole_bytes"] > 4096 else
                    "pending_runtime" if profile_id in TEST_PROFILES else "prepared_unqualified"),
            component_costs=dict(source_bytes=len(final), native_bytes=expected_contract["native_bytes"],
                payload_bytes=expected_contract["payload_bytes"], loader_and_headers_bytes=expected_contract["header_bytes"],
                whole_bytes=expected_contract["whole_bytes"], filter_candidates=first["pack"]["filter_candidates"]),
            retest_conditions=["new source or compiler or loader/codec bytes require two fresh builds and strict admission",
                "actual final-source rules, restored-image startup/UCI/full workers/resources and ownership remain separate",
                "whole ELF <=4096 plus all runtime/rules/placement gates required before ELF qualification"])
        require(len(report["commands"]) == policy["outer_commands"] and settled(report["commands"]), "finite producer commands not settled")
        parent_artifacts(parent_manifest, parent, family, profile_id, m)
        require(R.input_reader().read_regular(parent / "build.json", limit=MAX_FILE) == parent_raw,
                "fresh parent receipt changed")
        require(all(read_source(ROOT / name) == data and R.checked_artifact(out, "inputs/" + name, pin(data)) == data
                    for name, data in inputs.items()), "complete current/frozen source closure changed")
        report["source_closure_rechecked"] = True
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        try:
            utility.finish_report(host, report, save, body_error)
        finally:
            if owner is not None and previous is not None:
                owner.LIMITS.clear()
                owner.LIMITS.update(previous)
            signal.signal(signal.SIGCHLD, previous_chld)
    # This is the same independent reader used by runtime, not a success flag.
    try:
        admit_build(report, out)
    except BaseException as error:
        report.update(complete=False, failure={"type": type(error).__name__, "message": str(error),
                                               "stage": "post-settlement-independent-readmission"})
        save()
        raise
    return report


def _command_evidence(manifest, build, R):
    commands = manifest.get("commands")
    require(settled(commands) and manifest.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
            "complete naturally settled ELF commands required")
    outputs, inputs = {}, {}
    directory = manifest.get("artifact_directory")
    require(type(directory) is str and Path(directory).is_absolute(), "original owned artifact directory required")
    for index, row in enumerate(commands, 1):
        require(type(row.get("kind")) is str, "named owned command required")
        limits = {"AS": 4 << 30, "CPU": 480} if row["kind"] == "fresh-profile" else {"AS": 2 << 30, "CPU": 120}
        require(row.get("child_limits") == limits and type(row.get("pid")) is int and row["pid"] > 0
                and row.get("pgid") == row["pid"] and type(row.get("elapsed_diagnostic_seconds")) in (int, float)
                and 0 <= row["elapsed_diagnostic_seconds"] <= WORK_SECONDS,
                "actual owned process identity or finite resource bounds differ")
        stem = "tool-" + str(index) + "-" + row["kind"]
        for stream in ("stdout", "stderr"):
            record = row.get(stream, {})
            require(Path(record.get("path", "")) == Path(directory) / (stem + "." + stream),
                    "owned command log must bind the original owned artifact directory")
            data = R.checked_artifact(build, stem + "." + stream, {key: record[key] for key in ("bytes", "sha256")})
            if stream == "stdout":
                outputs[row["kind"]] = data
            else:
                require(data == b"", "ELF compiler/pack diagnostics are not empty")
        inputs[row["kind"]] = stem + ".stdin"
    return {row["kind"]: row for row in commands}, outputs, inputs


def admit_build(manifest, build):
    """Readmit the complete derived source, proof, native and whole ELF chain."""
    require(type(manifest) is dict and type(manifest.get("format")) is int and manifest["format"] == 1
            and manifest.get("class") == CLASS and manifest.get("complete") is True
            and manifest.get("reproducible") is True and manifest.get("source_closure_rechecked") is True
            and "failure" not in manifest and "cleanup_failure" not in manifest, "complete fresh full-profile ELF build required")
    family, profile_id = manifest.get("family"), manifest.get("profile")
    policy = plan(family, profile_id, native_variant=manifest.get("native_variant"))
    require(canonical(manifest.get("policy")) == canonical(policy) and manifest.get("actual") ==
            {"source": "main.c", "native": "native/x", "program": "x"}, "finite ELF build policy/layout differs")
    files, build = capture(), Path(build)
    m, R = modules(files), None
    R = m["R"]
    require(manifest.get("support") == {name: pin(data) for name, data in files.items()}, "current ELF consumer support differs")
    for name, data in files.items():
        require(R.checked_artifact(build, "support/" + name, pin(data)) == data, "frozen ELF consumer support differs")
    parent = R.artifact_file(build, "fresh-profile/build.json")
    parent_raw = R.input_reader().read_regular(parent, limit=MAX_FILE)
    require(pin(parent_raw) == manifest.get("parent_manifest"), "fresh parent receipt identity differs")
    parent_manifest = json.loads(parent_raw)
    admitted, artifacts = parent_artifacts(parent_manifest, parent.parent, family, profile_id, m)
    validate_target_abi_absence(parent_manifest, family)
    for name, data in files.items():
        if name in admitted.input_pins:
            require(admitted.input_pins[name] == pin(data)
                    and R.checked_artifact(parent.parent, "inputs/" + name, admitted.input_pins[name]) == data,
                    "fresh parent and derived consumer support identity conflict")
    union = {**admitted.input_pins, **{name: pin(data) for name, data in files.items()}}
    require(manifest.get("inputs") == union, "complete inherited and derived input closure differs")
    for name, identity in union.items():
        data = R.checked_artifact(build, "inputs/" + name, identity)
        require(read_source(ROOT / name) == data, "current full ELF source closure differs")
    source, before, proof = derive_source(artifacts["source"], parent_manifest["source_proofs"][-1],
        family=family, profile_id=profile_id, entry=m["entry"], projection=m["projection"], dependencies=m["dependencies"])
    require(canonical(manifest.get("source_proof")) == canonical(proof), "derived complete ELF source proof differs")
    api = m["production"]
    actual_plan = api.ArtifactPlan(api.engine_spec(family), api.resource_profile(profile_id), "self-contained-elf", "none", full=True)
    require(manifest.get("plan") == actual_plan.to_record() and manifest.get("resources") == admitted.resources
            and manifest.get("runtime_policy") == admitted.runtime_policy, "derived ELF resources or runtime topology differs")
    parent_control = json.loads(R.checked_artifact(parent.parent, "control/build.json", parent_manifest["control"]["report"]))
    require(manifest.get("source_closure") == {"parent": parent_manifest["source_closure"], "derived_tools": list(SUPPORT)}
            and manifest.get("factory_profile_commands") == parent_manifest["commands"]
            and manifest.get("factory_control_commands") == parent_control["commands"]
            and manifest.get("control_compiler") == policy["control_compiler"]
            and manifest.get("compiler") == policy["compiler"] and manifest.get("compile_executor_version") == BANNER
            and manifest.get("host_context", {}).get("load_page_bytes") == 4096
            and manifest.get("outer_command_limit") == policy["outer_commands"],
            "derived closure, complete factory receipts or compiler/page context differs")
    commands, outputs, stdin_names = _command_evidence(manifest, build, R)
    kinds = ["fresh-profile", "compiler-version"] + [attempt + "-" + kind for attempt in ("first", "repeat")
        for kind in ("types", "native", "CPP", "pack")]
    require(list(commands) == kinds and len(manifest["commands"]) == policy["outer_commands"], "exact finite ELF command sequence differs")
    factory_command = commands["fresh-profile"]["command"]
    requested = factory_argv(family, Path("fresh-profile"), profile_id)
    require(len(factory_command) == len(requested) and factory_command[1:3] == ["-I", "-B"]
            and Path(factory_command[3]).parts[-4:] == ("engines", "experiments", "tcec-next", "profile_build.py")
            and factory_command[4:-1] == requested[4:-1] and Path(factory_command[-1]).name == "fresh-profile",
            "actual fresh selected factory invocation differs")
    original = Path(manifest["artifact_directory"])
    require(commands["fresh-profile"]["cwd"] == str(original)
            and commands["compiler-version"]["cwd"] == str(original)
            and Path(factory_command[-1]) == original / "fresh-profile", "actual fresh factory ownership directory differs")
    require(outputs["compiler-version"].decode("utf-8", "strict").splitlines()[0] == BANNER
            and commands["compiler-version"]["command"] == ["cc", "--version"], "actual compiler observation differs")
    assertions = parent_manifest["source_proofs"][0]["target_type_assertions"]
    asserted = before + b"\n" + ("\n".join(assertions) + "\n").encode()
    expected_contract = manifest["expected_contract"]
    rows = manifest.get("attempts")
    require(type(rows) is list and [row.get("directory") for row in rows] == ["first", "repeat"], "two complete ELF attempts required")
    cpp_values = []
    for row, attempt in zip(rows, ("first", "repeat")):
        require(row.get("expected") == expected_contract and canonical(row.get("source_proof")) == canonical(proof)
                and row.get("pre_dependency") == pin(before) and row.get("asserted") == pin(asserted)
                and row.get("target_type_gate") == {"image_identical": True, "assertions": assertions},
                "derived source/type proof attempt differs")
        prefix = attempt + "/"
        actual_source = R.checked_artifact(build, prefix + "main.c", pin(source))
        require(actual_source == source and R.checked_artifact(build, prefix + "pre-dependency.c", pin(before)) == before
                and R.checked_artifact(build, prefix + "types/asserted.c", pin(asserted)) == asserted
                and R.checked_artifact(build, prefix + "source-proof.json", pin(json_bytes(proof))) == json_bytes(proof),
                "actual derived sources or complete proof differ")
        native = R.checked_artifact(build, prefix + "native/x", R._field_pin(expected_contract, "native"))
        require(R.checked_artifact(build, prefix + "types/x", pin(native)) == native, "actual target type/native gate differs")
        whole = R.checked_artifact(build, prefix + "x", R._field_pin(expected_contract, "whole"))
        require(R.artifact_file(build, prefix + "x").stat().st_mode & 0o7777 == 0o755,
                "actual rebuilt ELF executable mode differs")
        pack_raw = R.input_reader().read_regular(R.artifact_file(build, prefix + "pack.json"), limit=MAX_FILE)
        require(outputs[attempt + "-pack"] == pack_raw and json.loads(pack_raw) == row["pack"], "actual pack command receipt differs")
        dependency, header, payload = packed_restore(whole, native, row["pack"], elf=m["elf"], dependency=m["elf_dependencies"])
        require(canonical(dependency) == canonical(row["dependencies"]), "actual restored-native/outer dependency DATA differs")
        for name, data, label in (("header.bin", header, "header"), ("payload.bin", payload, "payload")):
            require(R.checked_artifact(build, prefix + name, R._field_pin(expected_contract, label)) == data,
                    "actual whole ELF component differs")
        require(_expected_artifacts(source, native, whole, header, payload) == expected_contract,
                "actual complete five-part derived identity differs")
        cpp_source = before if attempt == "first" else source
        require(row.get("CPP_input") == pin(cpp_source) and row.get("CPP_stage") ==
                ("before-cleanup" if attempt == "first" else "final"), "real final include CPP gate differs")
        expanded = R.checked_artifact(build, prefix + "expanded.i", row["CPP"])
        require(outputs[attempt + "-CPP"] == expanded, "actual preprocessor command output differs")
        cpp_values.append(expanded)
        for kind, data, command in (("types", asserted, policy["compiler"]), ("native", source, policy["compiler"]),
            ("CPP", cpp_source, m["dependencies"].preprocess_command(policy["compiler"]))):
            require(commands[attempt + "-" + kind]["command"] == command
                    and R.checked_artifact(build, stdin_names[attempt + "-" + kind], pin(data)) == data,
                    "actual derived compiler mode/stdin differs")
            expected_tail = (attempt,) if kind == "CPP" else (attempt, "types" if kind == "types" else "native")
            require(Path(commands[attempt + "-" + kind]["cwd"]) == original.joinpath(*expected_tail),
                    "actual derived compiler working directory differs")
        require("target_abi_gate" not in row, "an ABI gate was fabricated outside the current finite policy")
        pack_command = commands[attempt + "-pack"]["command"]
        require(len(pack_command) == 12 and pack_command[1:3] == ["-I", "-B"]
                and Path(pack_command[3]).parts[-3:] == ("engines", "scripts", "elf_loader.py")
                and Path(pack_command[4]).parts[-3:] == (attempt, "native", "x")
                and Path(pack_command[5]).parts[-2:] == (attempt, "x")
                and pack_command[6:] == ["--cc", "cc", "--timeout", "120", "--filter", "auto"],
                "actual self-restoring pack invocation differs")
        require(Path(pack_command[4]) == original / attempt / "native/x"
                and Path(pack_command[5]) == original / attempt / "x"
                and Path(commands[attempt + "-pack"]["cwd"]) == original / attempt,
                "actual ELF pack input/output/cwd do not share the owned attempt")
        require(row["pack"].get("input") == pack_command[4] and row["pack"].get("output") == pack_command[5]
                and row["pack"].get("compiler") == BANNER, "actual ELF pack metadata path/compiler context differs")
        require(row["pack"]["source_sha256"] == {"elf-loader/loader.c": pin(files[LOADER[0]])["sha256"],
            "elf-loader/loader.ld": pin(files[LOADER[1]])["sha256"], "elf_loader.py": pin(files[ELF])["sha256"]},
            "pack command did not bind the current loader source closure")
        for name in ("main.c", "native/x", "x", "header.bin", "payload.bin", "pre-dependency.c", "types/x", "types/asserted.c", "expanded.i", "source-proof.json"):
            data = R.input_reader().read_regular(R.artifact_file(build, prefix + name), limit=MAX_FILE)
            require(R.checked_artifact(build, name, pin(data)) == data, "published/attempt derived bytes differ")
    require(cpp_values[0] == cpp_values[1], "actual before/final include expanded compiler input differs")
    require(R.artifact_file(build, "x").stat().st_mode & 0o7777 == 0o755,
            "published ELF submission must retain its reproduced executable mode")
    stable_pack = lambda value: {key: child for key, child in value.items() if key not in ("input", "output")}
    require(canonical(stable_pack(rows[0]["pack"])) == canonical(stable_pack(rows[1]["pack"])),
            "complete independent loader metadata reproduction differs")
    wrapper = dict(policy="self-contained-memfd-loader", entry_cleanup="none", temp_strategy="anonymous-memfd-execveat",
        cleanup_seconds=0, parent_removed=False, runtime_external_tools=[], submitted_file_preserved=True)
    require(manifest.get("wrapper_contract") == wrapper
            and manifest.get("size_decisions") == [actual_plan.size_decision(expected_contract["whole_bytes"], division)
                for division in ("general4k", "elf4k")]
            and manifest.get("status") == ("deferred_size" if expected_contract["whole_bytes"] > 4096 else
                "pending_runtime" if profile_id in TEST_PROFILES else "prepared_unqualified")
            and manifest.get("engine_executed") is False and manifest.get("TT_allocated") is False
            and manifest.get("elf_qualified") is False and manifest.get("runtime_qualified") is False
            and manifest.get("execution_policy") == "compile-package-only"
            and manifest.get("submission_qualified") is False and manifest.get("event_target_confirmed") is False,
            "ELF ownership, size or observation scope differs")
    require(manifest.get("component_costs") == dict(source_bytes=len(source), native_bytes=expected_contract["native_bytes"],
                payload_bytes=expected_contract["payload_bytes"], loader_and_headers_bytes=expected_contract["header_bytes"],
                whole_bytes=expected_contract["whole_bytes"], filter_candidates=rows[0]["pack"]["filter_candidates"]),
            "actual whole ELF component cost report differs")
    # This public record is the common runtime bridge. No structural-admission
    # token is manufactured and no old private-path manifest is renamed.
    require(isinstance(getattr(R, "AnonymousMemfdContract", None), type), "common runtime lacks its reviewed ELF ownership contract")
    return R.AdmittedBuild(family, profile_id, "self-contained-elf", "x", "main.c", "native/x", expected_contract,
        admitted.resources, admitted.runtime_policy, R.AnonymousMemfdContract(), union,
        dict(kind="fresh-full-profile-elf-entry", parent=manifest["parent_manifest"], proof=proof,
             dependencies=rows[0]["dependencies"], full_rules_generation="pending-actual-final-ELF-source-fixture"), full=True)


def read_build(build, *, test_only=False):
    require(type(test_only) is bool, "explicit test-only reader mode required")
    files = capture()
    R = load_bytes("elf_profile_read_R", VERIFIER, files[VERIFIER])
    raw = R.input_reader().read_regular(R.artifact_file(Path(build), "build.json"), limit=MAX_FILE)
    manifest = json.loads(raw)
    if test_only:
        # Refuse the named submission profile before native/codec admission,
        # runtime evidence, rule rendering or effective-memory inspection.
        require_test_profile(manifest.get("profile"))
    admitted = admit_build(manifest, Path(build))
    # The public ownership marker belongs to the exact R instance which made
    # admitted. A second dynamic import would create a different Python type.
    return manifest, admitted, sys.modules["elf_profile_R"], files


def runtime(build, out, *, execute=False):
    require(execute is True, "explicit --execute required before engine runtime/TT allocation")
    require(sys.platform == "linux" and os.sysconf("SC_PAGE_SIZE") == 4096, "supported Linux 4KiB target required")
    manifest, admitted, R, files = read_build(build, test_only=True)
    dependency = admitted.source_contract["dependencies"]
    require(dependency["native_policy"]["allowed"] is True and dependency["outer_policy"]["allowed"] is True,
            "actual restored native and outer ELF dependencies must satisfy the reviewed TCEC policy before runtime")
    utility = load_bytes("elf_profile_runtime_output", UTILITY, files[UTILITY])
    out = utility.new_output(out)
    limits = R.execution_limits(admitted, R.effective_available_bytes())
    return R.run_runtime(admitted, Path(build), out, limits)


def rules(build, out, *, execute=False):
    """Run both existing actual-source oracle probes with this source owner."""
    require(execute is True, "explicit --execute required before C rules probes")
    require(sys.platform == "linux" and os.sysconf("SC_PAGE_SIZE") == 4096, "supported Linux 4KiB target required")
    started = time.monotonic()
    manifest, admitted, R, files = read_build(build, test_only=True)
    utility = load_bytes("elf_profile_rules_output", UTILITY, files[UTILITY])
    helper = load_bytes("elf_profile_rules_renderer", RULES, files[RULES])
    out = utility.new_output(out)
    out.mkdir(parents=True)
    source = R.checked_artifact(Path(build), "main.c", R._field_pin(admitted.expected, "source"))
    cases, coverage = helper.fixture_cases()
    fixture = helper.render_fixture(source, admitted.family, cases)
    write(out, "fixture.c", fixture)
    write(out, "cases.json", json_bytes([{k: v for k, v in case.items() if k != "board"} for case in cases]))
    report = dict(format=RULES_CLASS, complete=False, commands=[], modes=[], outer_command_limit=4,
        artifact_directory=str(out),
        build=pin(R.input_reader().read_regular(R.artifact_file(Path(build), "build.json"), limit=MAX_FILE)),
        family=admitted.family, profile=admitted.profile_id, source=pin(source), fixture=pin(fixture), coverage=coverage,
        oracle={"path": helper.ORACLE, "sha256": helper.ORACLE_SHA},
        renderer=pin(files[RULES]), owner=pin(files[SELF]), TT_allocated=False, original_entry_called=False)

    def save():
        (out / "rules.json").write_bytes(json_bytes(report))

    save()
    owner = previous = host = None
    body_error = None
    previous_chld = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    try:
        owner, previous, host = _bounded_host(out, report, save, files, started)
        for mode in ("plain", "ubsan"):
            executable = out / ("probe-" + mode)
            flags = [] if mode == "plain" else ["-fsanitize=undefined", "-fno-sanitize-recover=all"]
            command = ["cc", "-std=c11", "-O1", "-pthread", "-g0", *flags, str(out / "fixture.c"), "-o", str(executable)]
            run_command(host, owner, command, cwd=out, kind="rules-compile-" + mode)
            observed = run_command(host, owner, [str(executable)], cwd=out, kind="rules-execute-" + mode)
            comparison = helper._compare_output(observed, cases)
            require(comparison["cases"] == 105 and comparison["legal_moves_compared"] == 2858,
                    "actual-source independent oracle coverage differs")
            report["modes"].append(dict(mode=mode, native=pin(R.input_reader().read_regular(executable, limit=MAX_FILE)), **comparison))
            save()
        read_build(build, test_only=True)
        require(all(read_source(ROOT / name) == data for name, data in files.items()), "rules support changed")
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        try:
            utility.finish_report(host, report, save, body_error)
        finally:
            if owner is not None and previous is not None:
                owner.LIMITS.clear()
                owner.LIMITS.update(previous)
            signal.signal(signal.SIGCHLD, previous_chld)
    try:
        rules_receipt(build, out / "rules.json")
    except BaseException as error:
        report.update(complete=False, failure={"type": type(error).__name__, "message": str(error),
                                               "stage": "post-settlement-independent-readmission"})
        save()
        raise
    return report


def rules_receipt(build, rules_path):
    """Read actual final-source fixtures, binaries, owner logs and oracle sets."""
    manifest, admitted, R, files = read_build(build, test_only=True)
    helper = load_bytes("elf_profile_rules_receipt_renderer", RULES, files[RULES])
    path = Path(rules_path)
    require(path.is_absolute() and path.name == "rules.json", "absolute named ELF rules receipt required")
    raw = R.input_reader().read_regular(R.artifact_file(path.parent, path.name), limit=MAX_FILE)
    record = json.loads(raw)
    require(record.get("format") == RULES_CLASS and record.get("complete") is True and "failure" not in record
            and record.get("TT_allocated") is False and record.get("original_entry_called") is False
            and record.get("family") == admitted.family and record.get("profile") == admitted.profile_id
            and record.get("renderer") == pin(files[RULES]) and record.get("owner") == pin(files[SELF])
            and record.get("build") == pin(R.input_reader().read_regular(R.artifact_file(Path(build), "build.json"), limit=MAX_FILE)),
            "complete same-build final-source ELF rules evidence required")
    source = R.checked_artifact(Path(build), "main.c", R._field_pin(admitted.expected, "source"))
    cases, coverage = helper.fixture_cases()
    fixture = helper.render_fixture(source, admitted.family, cases)
    require(record.get("source") == pin(source) and record.get("fixture") == pin(fixture)
            and record.get("coverage") == coverage and record.get("oracle") == {"path": helper.ORACLE, "sha256": helper.ORACLE_SHA}
            and R.checked_artifact(path.parent, "fixture.c", pin(fixture)) == fixture,
            "actual final-source ELF rules fixture differs")
    cases_raw = json_bytes([{k: v for k, v in case.items() if k != "board"} for case in cases])
    require(R.checked_artifact(path.parent, "cases.json", pin(cases_raw)) == cases_raw, "independent rules cases differ")
    commands, outputs, _ = _command_evidence(record, path.parent, R)
    require(list(commands) == ["rules-" + action + "-" + mode for mode in ("plain", "ubsan") for action in ("compile", "execute")]
            and type(record.get("modes")) is list and [row.get("mode") for row in record["modes"]] == ["plain", "ubsan"],
            "both actual rules probe modes and terminal command sequence required")
    for mode in record["modes"]:
        name = mode["mode"]
        compile_row, execute_row = commands["rules-compile-" + name], commands["rules-execute-" + name]
        command = compile_row["command"]
        flags = [] if name == "plain" else ["-fsanitize=undefined", "-fno-sanitize-recover=all"]
        original = Path(record["artifact_directory"])
        require(command[:5 + len(flags)] == ["cc", "-std=c11", "-O1", "-pthread", "-g0", *flags]
                and len(command) == 8 + len(flags) and Path(command[-3]) == original / "fixture.c"
                and command[-2] == "-o" and Path(command[-1]) == original / ("probe-" + name)
                and execute_row["command"] == [command[-1]] and compile_row["cwd"] == str(original)
                and execute_row["cwd"] == str(original), "actual final-source rules compiler/probe invocation differs")
        R.checked_artifact(path.parent, "probe-" + name, mode["native"])
        comparison = helper._compare_output(outputs["rules-execute-" + name], cases)
        require(comparison == {key: mode.get(key) for key in comparison}
                and comparison["cases"] == 105 and comparison["legal_moves_compared"] == 2858,
                "actual final-source rules output differs from independent oracle")
    return dict(nbrq_generation=True, family=admitted.family, cases=105, legal_moves_compared=2858,
        modes=["plain", "ubsan"], coverage=coverage, runtime_qualified=False,
        scope="actual final ELF-source start/generate/make legal sets; original entry and TT never called",
        evidence=dict(rules_report={"path": str(path), **pin(raw)}, source=pin(source), fixture=pin(fixture)))


def qualify(build, runtime_path, *, rules_path=None):
    """Bind existing runtime/rules evidence; never execute or waive a gate."""
    manifest, admitted, R, _ = read_build(build, test_only=True)
    result = R.qualification_record(admitted, Path(build), Path(runtime_path), rules_path=None)
    generated = rules_receipt(build, rules_path) if rules_path is not None else None
    policy = admitted.source_contract["dependencies"]
    result["division"] = "elf4k"
    result["checks"]["dependencies"] = result["checks"]["dependencies"] is True and \
        policy["native_policy"]["allowed"] is True and policy["outer_policy"]["allowed"] is True
    result["checks"]["legal_moves"] = generated is not None and generated["nbrq_generation"] is True
    result["failures"] = [name for name, passed in result["checks"].items() if passed is not True]
    result["complete"] = not result["failures"]
    result["test_qualified"] = result["complete"] and R.contracts().resource_profile(admitted.profile_id).purpose == "test"
    result["elf_qualified"] = result["test_qualified"]
    result["release_qualified"] = False
    result["status"] = "deferred_size" if admitted.expected["whole_bytes"] > 4096 else \
        "elf_test_qualified" if result["test_qualified"] else "pending_runtime_or_rules"
    result["evidence"]["rules"] = generated
    result["evidence"]["ELF_dependency_metadata"] = policy
    result["observations"]["nbrq_generation"] = generated is not None
    result["scope"] = "full restored-native ELF TEST evidence; event target, release and playing strength remain separate"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    planner = sub.add_parser("plan")
    planner.add_argument("--entry", choices=FAMILIES, required=True)
    planner.add_argument("--profile", choices=PROFILES, default="test-p4")
    planner.add_argument("--native-variant", choices=NATIVE_VARIANTS, default="baseline")
    producer = sub.add_parser("produce")
    producer.add_argument("--entry", choices=FAMILIES, required=True)
    producer.add_argument("--profile", choices=PROFILES, default="test-p4")
    producer.add_argument("--native-variant", choices=NATIVE_VARIANTS, default="baseline")
    producer.add_argument("--out", type=Path, required=True)
    producer.add_argument("--execute", action="store_true")
    reader = sub.add_parser("admit")
    reader.add_argument("--build", type=Path, required=True)
    for action in ("runtime", "rules"):
        command = sub.add_parser(action)
        command.add_argument("--build", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--execute", action="store_true")
    qualifier = sub.add_parser("qualify")
    qualifier.add_argument("--build", type=Path, required=True)
    qualifier.add_argument("--runtime", type=Path, required=True)
    qualifier.add_argument("--rules", type=Path)
    qualifier.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action == "plan":
        print(json.dumps(plan(args.entry, args.profile, native_variant=args.native_variant), sort_keys=True))
        return
    if args.action == "produce":
        result = produce(args.entry, args.out, profile_id=args.profile, native_variant=args.native_variant,
                         execute=args.execute)
    elif args.action == "admit":
        manifest, admitted, _, _ = read_build(args.build)
        result = dict(class_name=CLASS, family=admitted.family, profile=admitted.profile_id,
                      representation=admitted.representation, status=manifest["status"], complete=True)
    elif args.action in ("runtime", "rules"):
        result = globals()[args.action](args.build, args.out, execute=args.execute)
    else:
        result = qualify(args.build, args.runtime, rules_path=args.rules)
        files = capture()
        utility = load_bytes("elf_profile_qualification_output", UTILITY, files[UTILITY])
        out = utility.new_output(args.out)
        out.mkdir(parents=True)
        write(out, "qualification.json", json_bytes(result))
    print(json.dumps({key: result[key] for key in ("complete", "family", "profile", "status", "failures") if key in result}, sort_keys=True))


if __name__ == "__main__":
    main()
