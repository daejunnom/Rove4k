"""Actual admitted Structural carriers, Board and startup projections.

This consumes a fresh StructuralAdmission above a real fresh SquareAdmission.
Each finite admission-owned variant has its own whole/native identity.
Fixture diagnostics are projected onto the actual counted-output runtime while
the shipping six-source input remains immutable. Local observations grant no
event approval, physical placement, playing strength or selection.
"""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import lzma
import math
from pathlib import Path, PurePosixPath
import sys
from types import CodeType, FunctionType, GetSetDescriptorType, ModuleType


KIND = "rove4k.D-structural-runtime-carrier.v1"
SOURCE_KIND = "rove4k.D-structural-source.v1"
SELECTOR = "full"
OPTIONS = ["previous-piece", "unsigned-history"]
POLICY = "TCEC-minimum-immediate-process-exit"
INPUT_CONTRACT = "TCEC-valid-non-NUL-lines-at-most-32767-bytes"
SCOPE = "local TCEC-targeted minimal shutdown contract; event approval unconfirmed"
ROUTE = "packed-xz-bcj-pb0"
D = "engines/experiments/tiny-d-submission/"
ADMISSION = D + "structural_admission.py"
SELF = D + "structural_carrier.py"
COMPONENT = D + "no_tid_runtime.py"
PACKAGING = D + "packaging.py"
READABLE = {"tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld"}
SHIPPING = {"main.c", "start.S", "image.ld"}
SELECTION = {
    "board": ["value-fold-center", "make-half", "rights-packed", "walk-ranges",
              "walk-castle-rights", "walk-signed-piece", "add-do", "material-signature-loop"],
    "search": ["moves432", "eval_bound", "mate_helper_noinline", "tt_bound_select"],
    "runtime": ["notation-inverse", "direct-output", "counted-output", "number-limit",
                "keys-own", "noinline-allocate", "shared-resolver"],
}
IDENTITY = {
    "linked": {"bytes": 7008, "sha256": "016a0b753b0a9c79a3dc5faacb16507cf675da5e73169230de403e37d2921295"},
    "stripped": {"bytes": 6656, "sha256": "6d67cc6d64b4d3fb66afa33d78afcebff34eaa788570a06a0ad754dd6d8efbd5"},
}
WHOLE = {"bytes": 4909, "sha256": "2de1e291393f59977393ae7a9e99754d8ec661b8c57d8c25989070ce8302205d"}
COMPONENT_PIN = {"bytes": 30622, "sha256": "a878b2401201b46565605a7ece66b451b7248df5ac2721887e725f5b40b53656"}
PACKAGING_PIN = {"bytes": 3184, "sha256": "928b7f2ea76787994a4d47f516395583af5cba0bfe840d54fc5321056558faa6"}
PROJECTION = D + "source.py"
PROJECTION_PIN = {"bytes": 9178, "sha256": "7bc2e917d3c267dd2526349a8faa47799eabca3d09d4261d2f0d63fd475ab72e"}
POISON = D + "test_startup.py"
POISON_PIN = {"bytes": 23298, "sha256": "8ec8f933fbb9846e8e9a687b6fd38225f46640a37dea874e16f693cdc80fb395"}
STORAGE_FIELDS = ("_valid", "_record", "_parent", "_parent_module", "_readable",
                  "_shipping", "_images", "_native", "_linked")
STARTUP_KIND = "D-structural-three-argument-startup-fixture-v1"
STARTUP_LABEL = "structural-startup-abi"
FIXED_STARTUP_KIND = "D-structural-fixed-entry-startup-fixture-v1"
FIXED_STARTUP_LABEL = "structural-fixed-startup-abi"
STARTUP_UNITS = ("board.c", "search.c", "runtime.c", "start.S")
STARTUP_FLAGS = ("-Os", "-std=c11", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic",
    "-fno-stack-protector", "-fno-builtin", "-fno-asynchronous-unwind-tables", "-fno-unwind-tables",
    "-fno-ident", "-fcf-protection=none", "-ffunction-sections", "-fdata-sections",
    "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack", "-flto", "-msse4.2", "-mcx16",
    "-DDEV=0", "-DD_HQ=0", "-DWORKERS=4", "-DTT_BITS=12")
STARTUP_STDIN = b"uci\nisready\nquit\n"
COUNTED_OUTPUT = (b"static void output_counted(const char *s,size_t n){while(n){long z=Dsc3(1,1,(long)s,(long)n);"
                  b"if(z==-4)continue;if(z<=0)abort();s+=z;n-=(size_t)z;}}\n")
TRACE_OUTPUT = (b"#if !DEV\n"
                b"/* Fixture diagnostics only; shipping output_counted remains unchanged. */\n"
                b"static void output(const char *s){size_t n=0;while(s[n])n++;output_counted(s,n);}\n"
                b"#endif\n")
FIXED_STARTUP_WRAPPER = b'''static atomic_uint test_spawn2_calls;
extern long fixture_actual_spawn2(void *,void *) __asm__("spawn");
static long fixture_spawn2(void *arg,void *stack){
    Worker *w=arg;unsigned n=atomic_fetch_add_explicit(&test_spawn2_calls,1,memory_order_relaxed);
    if(n>=WORKERS||w->id!=(int)n||((unsigned long)stack&15))abort();
    return fixture_actual_spawn2(arg,stack);
}'''
_EXECUTING_CODE = sys._getframe().f_code


def require(value, detail):
    if not value:
        raise ValueError(detail)


def pin(data):
    require(type(data) is bytes, "actual immutable bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def inventory(files):
    require(type(files) is dict and all(type(name) is str for name in files), "named immutable source mapping required")
    return {name: pin(data) for name, data in sorted(files.items())}


def _json(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def _relative(name):
    require(type(name) is str and name and not name.startswith("/") and
            not any(c in name for c in ("\\", ":", "\0")), "normalized relative carrier input required")
    parts = name.split("/")
    require(all(part not in ("", ".", "..") for part in parts), "carrier input escaped its namespace")
    blocked = {".git", ".ssh", ".aws", "node_modules", "dist", "dist-server", "build", "coverage",
               "models", "checkpoints", ".cache", "inventory.json", "package-lock.json"}
    require(not any(part.casefold() in blocked or part.casefold() == ".env" or
                    part.casefold().startswith(".env.") for part in parts), "protected carrier input")
    return name


def _absolute(path):
    require(type(path) is str and path.startswith("/") and path != "/" and
            str(PurePosixPath(path)) == path and ".." not in PurePosixPath(path).parts and
            not any(c in path for c in ("\\", ":", "\0")), "normalized absolute evidence path required")
    return path


def _settled(row):
    require(type(row) is dict and type(row.get("returncode")) is int and row["returncode"] == 0 and
            all(row.get(key) is True for key in ("started", "terminal", "reaped", "owned_group_absent",
                "original_identity_retained_until_other_members_absent")) and
            row.get("forced_cleanup") is False and row.get("other_group_members_before_reap") == [] and
            type(row.get("pid")) is int and row["pid"] > 0 and row.get("pgid") == row["pid"],
            "original Structural command did not settle naturally")


def _source(data, module, expected=None, *, logical=None):
    require(type(data) is dict and set(data) == {"current", "frozen"} and
            type(data["current"]) is bytes and data["current"] == data["frozen"],
            "current/frozen executing source differs")
    require(type(module) is ModuleType, "actual registered executing module required")
    namespace = module.__dict__
    require(type(namespace.get("__name__")) is str and sys.modules.get(namespace["__name__"]) is module,
            "actual registered executing module required")
    require(type(namespace.get("__file__")) is str, "actual authority source filename required")
    path = namespace["__file__"]
    roles = (logical,) if logical is not None else (ADMISSION, SELF, COMPONENT)
    require(all(role in (ADMISSION, SELF, COMPONENT) for role in roles) and
            any(Path(path).parts[-len(PurePosixPath(role).parts):] == PurePosixPath(role).parts for role in roles),
            "authority source occupies another role")
    code = compile(data["frozen"], path, "exec", dont_inherit=True)
    require(namespace.get("_EXECUTING_CODE") == code, "authority differs from its executing source")
    for item in code.co_consts:
        if not isinstance(item, CodeType) or item.co_name.startswith("<"):
            continue
        if item.co_flags & 2:
            actual = namespace.get(item.co_name)
            require(type(actual) is FunctionType and actual.__code__ == item and actual.__globals__ is namespace,
                    "executing authority function binding differs")
        elif item.co_name in ("SearchAdmission", "NoTidAdmission", "SquareAdmission", "StructuralAdmission"):
            actual = namespace.get(item.co_name)
            require(type(actual) is type and actual.__module__ == namespace["__name__"] and
                    actual.__name__ == item.co_name and actual.__qualname__ == item.co_name and
                    actual.__bases__ == (object,) and
                    not any(name in actual.__dict__ for name in ("__getattribute__", "__getattr__", "__slots__", *STORAGE_FIELDS)) and
                    type(actual.__dict__.get("__dict__")) is GetSetDescriptorType and
                    actual.__dict__["__dict__"].__objclass__ is actual,
                    "direct typed authority storage/class binding differs")
            for method in item.co_consts:
                if isinstance(method, CodeType) and method.co_flags & 2 and not method.co_name.startswith("<"):
                    function = actual.__dict__.get(method.co_name)
                    if isinstance(function, property):
                        function = function.fget
                    require(type(function) is FunctionType and function.__code__ == method and
                            function.__globals__ is namespace, "typed authority method binding differs")
    if expected is not None:
        require(pin(data["frozen"]) == expected, "executing authority source pin differs")
    return data["frozen"]


def validate_profile(profile):
    require(type(profile) is dict, "typed Structural P4 profile required")
    expected = {"workers": 4, "control_threads": 1, "os_threads": 5, "tt_bits": 23,
                "tt_entry_bytes": 16, "tt_entries": 1 << 23, "tt_mask": (1 << 23) - 1,
                "tt_bytes": 128 << 20, "tt_cap_bytes": 128 << 20}
    require(profile.get("id") == "test-p4" and profile.get("purpose") == "test" and
            all(type(profile.get(key)) is int and profile[key] == value for key, value in expected.items()) and
            all(profile.get(key) is True for key in ("parallel_init", "init_partition_requires_page_aligned_base",
                                                   "initialization_in_startup")) and
            profile.get("event_allocation_confirmed") is None, "exact typed W4/TT23/128MiB P4 geometry required")
    return deepcopy(profile)


def _admitted(token, admission_module):
    require(admission_module.__dict__.get("KIND") == SOURCE_KIND and
            type(token) is admission_module.__dict__.get("StructuralAdmission"), "exact StructuralAdmission required")
    cls = admission_module.StructuralAdmission
    require(cls.assert_valid(token) is token, "fresh Structural authority failed")
    record = cls.to_record(token)
    contract = admission_module.variant_contract(record.get("variant", "initial-full"))
    require(record.get("kind") == SOURCE_KIND and record.get("selector") == contract["selector"] and
            record.get("selected_route") == contract["route"] and record.get("structural_selection") == contract["selection"] and
            record.get("options") == OPTIONS and record.get("nonreturning") is contract["nonreturning"] and
            record.get("ownership_policy") == POLICY and record.get("last_search_output_required") is False and
            record.get("input_contract") == INPUT_CONTRACT, "closed Structural selection/input/ownership differs")
    require(all(record.get(key) is True for key in ("source_admitted", "native_admitted", "package_generation_admitted",
                "actual_search_semantics_admitted", "actual_startup_mechanism_admitted")) and
            all(record.get(key) is False for key in ("fresh_full_artifact_runtime", "rules_qualified",
                "physical_placement_qualified", "size_qualified", "strength_qualified", "event_target_confirmed", "selected")),
            "carrier consumes generation authority only")
    require(record.get("new_three_argument_startup_admitted") is (contract["startup_argument_count"] == 3) and
            record.get("new_fixed_entry_startup_admitted") is (contract["startup_argument_count"] == 2),
            "actual admitted startup ABI differs")
    require(record.get("board_contract") == contract["board_contract"], "Structural Board contract differs")
    validate_profile(record.get("profile"))
    require(set(token.readable) == READABLE and set(token.shipping) == SHIPPING, "complete Structural source sets required")
    return record


def _variant_contract(variant, admission_module, admission_source):
    """Use the authenticated admission owner's closed finite contract."""
    require(type(variant) is str and variant in ("initial-full", "fast-capacity"), "named Structural variant required")
    _source(admission_source, admission_module, logical=ADMISSION)
    contract = admission_module.variant_contract(variant)
    require(type(contract) is dict and contract.get("variant") == variant,
            "admission-owned named Structural contract differs")
    return contract


def _packaging_source(module):
    require(type(module) is ModuleType, "actual package helper required")
    namespace = module.__dict__
    require(type(namespace.get("__name__")) is str and sys.modules.get(namespace["__name__"]) is module,
            "actual package helper required")
    require(type(namespace.get("__file__")) is str, "package helper source filename required")
    path = Path(namespace["__file__"])
    require(path.parts[-4:] == PurePosixPath(PACKAGING).parts and path.is_file() and path.stat().st_size <= 1 << 20,
            "bounded fixed package helper source required")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in raw and pin(raw) == PACKAGING_PIN, "unchanged package helper source required")
    for item in compile(raw, str(path), "exec", dont_inherit=True).co_consts:
        if isinstance(item, CodeType) and item.co_flags & 2 and not item.co_name.startswith("<"):
            actual = namespace.get(item.co_name)
            require(type(actual) is FunctionType and actual.__code__ == item and actual.__globals__ is namespace,
                    "package helper executing function/globals differs")
    return raw


def _helper_source(module, logical, expected):
    """Authenticate a named fixed source and all of its function bindings."""
    require(type(module) is ModuleType, "actual fixed helper module required")
    namespace = module.__dict__
    require(type(namespace.get("__name__")) is str and sys.modules.get(namespace["__name__"]) is module and
            type(namespace.get("__file__")) is str, "registered fixed helper source required")
    path = Path(namespace["__file__"])
    parts = PurePosixPath(logical).parts
    require(path.parts[-len(parts):] == parts and path.is_file() and path.stat().st_size <= 1 << 20,
            "bounded fixed helper source role required")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in raw and pin(raw) == expected, "fixed helper source pin differs")
    for item in compile(raw, str(path), "exec", dont_inherit=True).co_consts:
        if isinstance(item, CodeType) and item.co_flags & 2 and not item.co_name.startswith("<"):
            actual = namespace.get(item.co_name)
            require(type(actual) is FunctionType and actual.__code__ == item and actual.__globals__ is namespace,
                    "fixed helper executing function/globals differs")
    return raw


def package_native(native, packaging, *, variant="initial-full", admission_module=None,
                   admission_source=None, codec=None):
    """Reproduce the named admitted recipe; preserve the historical PB0 default."""
    require(type(variant) is str and variant in ("initial-full", "fast-capacity"), "named Structural variant required")
    if variant != "initial-full":
        contract = _variant_contract(variant, admission_module, admission_source)
        require(pin(native) == contract["identity"]["stripped"], "admitted variant native identity required before encoding")
        _packaging_source(packaging)
        recipe = contract["codec"]
        _helper_source(codec, recipe["path"], recipe["pin"])
        whole, detail = codec.package(native, deepcopy(recipe["config"]), packaging, unnamed=True)
        boundary = detail.get("header_bytes") if type(detail) is dict else None
        require(type(whole) is bytes and type(boundary) is int and 0 < boundary < len(whole) and
                pin(whole) == contract["whole"] and pin(whole[:boundary]) == contract["header"] and
                detail.get("codec") == "xz-bcj" and detail.get("check") == "CRC64" and
                detail.get("config") == recipe["config"] and detail.get("unnamed_memfd") is True and
                detail.get("dict_size") == 8192 and detail.get("payload_bytes") == len(whole) - boundary and
                detail.get("native_argv0") == "Rove4k-D" and
                all(detail.get(key) is True for key in ("environment_preserved", "descriptor_close_on_exec", "complete_native_restored")) and
                whole.startswith(b"#!/bin/sh\nexec python3 -c "), "admitted complete HC3 unnamed header/payload differs")
        decoder = lzma.LZMADecompressor()
        restored = decoder.decompress(whole[boundary:], max_length=len(native) + 1)
        require(decoder.eof and not decoder.unused_data and restored == native,
                "HC3 strict EOF/complete native inverse differs")
        return whole, detail
    require(pin(native) == IDENTITY["stripped"], "initial Structural native identity required before encoding")
    _packaging_source(packaging)
    payload = lzma.compress(native, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64,
        filters=[{"id": lzma.FILTER_X86}, {"id": lzma.FILTER_LZMA2,
            "preset": 9 | lzma.PRESET_EXTREME, "dict_size": 8192, "lc": 3, "lp": 0, "pb": 0}])
    whole, header = packaging.envelope(packaging.NATIVE_CODE, payload)
    detail = {"codec": "xz-bcj", "check": "CRC64", "dict_size": 8192, "lc": 3, "lp": 0, "pb": 0,
              "header_bytes": len(header), "payload_bytes": len(payload),
              "restoration": "complete kernel-executable ELF", "cleanup": "memfd-CLOEXEC"}
    require(pin(whole) == WHOLE and whole == header + payload and
            whole.startswith(b"#!/bin/sh\nexec python3 -c "), "new complete PB0 header/payload identity differs")
    decoder = lzma.LZMADecompressor()
    restored = decoder.decompress(payload, max_length=len(native) + 1)
    require(decoder.eof and not decoder.unused_data and restored == native,
            "PB0 strict EOF/complete native inverse differs")
    return whole, detail


def startup_component():
    """Authenticate the fixed no-TID three-argument mechanism, never its carrier."""
    path = Path(__file__).resolve().parent / "no_tid_runtime.py"
    require(path.is_file() and path.stat().st_size <= 1 << 20, "bounded no-TID startup component required")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in raw and pin(raw) == COMPONENT_PIN, "unchanged startup mechanism component required")
    spec = importlib.util.spec_from_file_location("D_structural_authenticated_startup_component", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    _source({"current": raw, "frozen": raw}, module, COMPONENT_PIN, logical=COMPONENT)
    require(module.KIND == "rove4k.D-no-TID-runtime-carrier.v1" and tuple(module.STARTUP_FLAGS) == STARTUP_FLAGS and
            tuple(module.STARTUP_UNITS) == STARTUP_UNITS and module.STARTUP_STDIN == STARTUP_STDIN,
            "only the pinned startup mechanism is reusable")
    return module, raw


def _startup_helper(logical, expected, name):
    path = Path(__file__).resolve().parent / PurePosixPath(logical).name
    require(path.is_file() and path.stat().st_size <= 1 << 20, "bounded fixed startup helper required")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in raw and pin(raw) == expected, "fixed startup helper source differs before loading")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    _helper_source(module, logical, expected)
    return module, raw


def diagnostic_projection(readable):
    """Add one fixture-only wrapper; all actual shipping bytes remain recoverable."""
    require(type(readable) is dict and set(readable) == READABLE and all(type(data) is bytes for data in readable.values()),
            "actual immutable Structural six-file input required")
    original = readable["runtime.c"]
    require(original.count(COUNTED_OUTPUT) == 1 and TRACE_OUTPUT not in original and
            original.count(b"#if DEV\nstatic void output(const char *s)") == 1,
            "actual initial counted-output runtime role differs")
    offset = original.index(COUNTED_OUTPUT) + len(COUNTED_OUTPUT)
    projected = original[:offset] + TRACE_OUTPUT + original[offset:]
    require(projected[:offset] + projected[offset + len(TRACE_OUTPUT):] == original,
            "diagnostic wrapper failed its complete inverse")
    generated = dict(readable)
    generated["runtime.c"] = projected
    proof = {"kind": "D-structural-counted-output-diagnostic-projection-v1",
             "input": inventory(readable), "output": inventory(generated),
             "edit": {"begin": offset, "before": "", "after": TRACE_OUTPUT.decode()},
             "gaps": [{"begin": 0, "end": offset, **pin(original[:offset])},
                      {"begin": offset, "end": len(original), **pin(original[offset:])}],
             "complete_inverse": True, "shipping_source_changed": False, "DEV": 0,
             "diagnostic_sink": "actual output_counted", "counted_output": pin(COUNTED_OUTPUT)}
    return generated, proof


def _fixed_startup_fixture(readable, contract):
    """Instrument the actual two-argument fixed entry; keep its ASM unchanged."""
    adapted, adapter = diagnostic_projection(readable)
    actual = adapted["runtime.c"]
    prototype = b"extern long spawn(void *,void *);"
    call = b"spawn(workers+created,stack+1048576+4096)"
    require(contract["startup_argument_count"] == 2 and contract["nonreturning"] is True and
            actual.count(prototype) == actual.count(call) == 1 and
            actual.count(b"__attribute__((used,externally_visible)) _Noreturn void work(void *p){") == 1 and
            b"typedef char *Span;" in actual and b"if(!stack)abort();" in actual and
            b"mov %rdi,(%rsi)" in readable["start.S"] and b"mov (%rsp),%rdi" in readable["start.S"] and
            b"jmp work" in readable["start.S"] and b"0x50f00" in readable["start.S"] and
            b"call *%rax" not in readable["start.S"], "actual fixed-entry/NUL/abort startup source differs")
    component, authority = startup_component()
    projection, projection_raw = _startup_helper(PROJECTION, PROJECTION_PIN, "D_structural_fixed_projection")
    poison, poison_raw = _startup_helper(POISON, POISON_PIN, "D_structural_fixed_poison")
    compatibility = [
        ("fixture-status-for-shared-poison", b"int created=0;char line[32768];", b"int created=0,status=0;char line[32768];"),
        ("fixture-table-anchor-for-shared-poison", b"if(!table)abort();start(&position);", b"if(!table)return 2;start(&position);"),
        ("fixture-barrier-anchor-for-shared-poison", b"    }\n    wait();\n    for(;;){",
         b"    }\n    if(status)goto shutdown;\n    wait();\n    for(;;){"),
        ("fixture-return-anchor-for-shared-poison", b"#endif\n#endif\n    }\n    return 0;\n}\n",
         b"#endif\n#endif\n    }\nshutdown:\n    return status;\n}\n"),
    ]
    compatible, compatibility_proof = projection.project(actual, compatibility)
    compatible_files = {**adapted, "runtime.c": compatible}
    poisoned, poison_proof = poison.instrument(dict(compatible_files), go=False)
    _helper_source(poison, POISON, POISON_PIN)
    _helper_source(projection, PROJECTION, PROJECTION_PIN)
    require(set(poisoned) == READABLE and all(poisoned[name] == readable[name] for name in READABLE - {"runtime.c"}) and
            poison_proof["input"] == pin(compatible) and poison_proof["output"] == pin(poisoned["runtime.c"]) and
            projection.restore(poisoned["runtime.c"], poison_proof) == compatible,
            "shared poison changed actual fixed-entry inputs or lost its inverse")
    restoration = [
        ("restore-actual-abort-status", b"int created=0,status=0;char line[32768];", b"int created=0;char line[32768];"),
        ("restore-actual-abort-table", b"if(!table)return 2;", b"if(!table)abort();"),
        ("restore-actual-abort-barrier", b"    if(status)goto shutdown;\n", b""),
        ("restore-actual-main-return", b"shutdown:\n    return status;", b"    return 0;"),
        ("fixture-poison-failure-aborts", b"status=7;goto shutdown;", b"abort();"),
        ("fixture-owner-failure-aborts", b"status=8;goto shutdown;", b"abort();"),
        ("fixture-arrival-failure-aborts", b"status=9;goto shutdown;", b"abort();"),
    ]
    restored, restoration_proof = projection.project(poisoned["runtime.c"], restoration)
    roles = [
        ("actual-two-argument-wrapper", prototype, FIXED_STARTUP_WRAPPER),
        ("actual-two-argument-call", call, b"fixture_spawn2(workers+created,stack+1048576+4096)"),
        ("hold-last-real-fixed-worker-before-first-touch", b"    for(size_t p=begin/256;",
         component.STARTUP_HOLD + b"    for(size_t p=begin/256;"),
        ("check-two-argument-transports", b'    output("TEST_INITIALIZED\\n");',
         b'    if(atomic_load_explicit(&test_spawn2_calls,memory_order_relaxed)!=4)abort();\n'
         b'    output("TEST_SPAWN2_4\\nTEST_INITIALIZED\\n");'),
    ]
    output, fixed_proof = projection.project(restored, roles)
    inverse_restored = projection.restore(output, fixed_proof)
    inverse_poisoned = projection.restore(inverse_restored, restoration_proof)
    inverse_compatible = projection.restore(inverse_poisoned, poison_proof)
    require(projection.restore(inverse_compatible, compatibility_proof) == actual,
            "complete fixed-entry diagnostic/startup source inverse differs")
    dialogue, dialogue_proof = projection.project(component.STARTUP_DIALOGUE.encode(), [
        ("honest-fixed-entry-dialogue-description", b"bounded three-argument startup fixture",
         b"bounded fixed-entry two-argument startup fixture")])
    require(projection.restore(dialogue, dialogue_proof) == component.STARTUP_DIALOGUE.encode(),
            "fixed-entry dialogue full inverse differs")
    generated = {**adapted, "runtime.c": output}
    require(all(generated[name] == readable[name] for name in READABLE - {"runtime.c"}) and
            b"TEST_SPAWN3_4" not in output and b"fixture_spawn3" not in output and
            b"typedef char *Span;" in output and b"if(!table)abort();" in output and
            b"if(!stack)abort();" in output,
            "fixed-entry fixture changed actual ASM/NUL/failure ownership or claimed three arguments")
    return generated, {"kind": "D-structural-fixed-entry-startup-fixture-projection-v1",
        "variant": contract["variant"], "selector": contract["selector"], "input": inventory(readable),
        "output": inventory(generated), "diagnostic_projection": adapter,
        "component_path": COMPONENT, "component_authority": pin(authority),
        "projection_authority": pin(projection_raw), "poison_authority": pin(poison_raw),
        "compatibility_projection": compatibility_proof, "shared_poison_projection": poison_proof,
        "restore_abort_projection": restoration_proof, "fixed_entry_projection": fixed_proof,
        "dialogue_projection": dialogue_proof, "dialogue_source": dialogue.decode(),
        "dialogue": pin(dialogue), "complete_inverse": True, "spawn_argument_count": 2,
        "fixed_entry": True, "actual_start_S_unchanged": True, "actual_structural_board": pin(readable["board.c"]),
        "worker_count": 4, "TT_bits": 12, "TT_bytes": 65536, "poison_byte": 165,
        "held_last_worker": 3, "logical_Worker_id_transport_checked": True, "stack_alignment_checked": 16,
        "flags": list(STARTUP_FLAGS), "units": list(STARTUP_UNITS),
        "component_role": "unchanged shared poison/hold/dialogue; actual two-argument fixed-entry transport",
        "full128MiB_qualified": False, "runtime_qualified": False}


def render_startup_fixture(readable, *, variant="initial-full", admission_module=None, admission_source=None):
    """Project diagnostics and the honest three- or two-argument startup mechanism."""
    require(type(variant) is str and variant in ("initial-full", "fast-capacity"), "named Structural variant required")
    if variant != "initial-full":
        contract = _variant_contract(variant, admission_module, admission_source)
        return _fixed_startup_fixture(readable, contract)
    adapted, adapter = diagnostic_projection(readable)
    component, authority = startup_component()
    generated, projection = component.render_startup_fixture(dict(adapted))
    require(projection["input"] == inventory(adapted) and projection["output"] == inventory(generated) and
            all(generated[name] == readable[name] for name in READABLE - {"runtime.c"}),
            "startup mechanism changed actual Structural header/Board/search/ASM/linker inputs")
    return generated, {"kind": "D-structural-actual-startup-fixture-projection-v1", "variant": variant, "selector": SELECTOR,
        "input": inventory(readable), "output": inventory(generated), "diagnostic_projection": adapter,
        "component_path": COMPONENT, "component_authority": pin(authority), "component_projection": projection,
        "component_role": "three-argument poison/held startup mechanism only; no historical carrier/native authority",
        "actual_structural_board": pin(readable["board.c"]), "flags": list(STARTUP_FLAGS), "units": list(STARTUP_UNITS),
        "full128MiB_qualified": False, "runtime_qualified": False}


def startup_receipt(raw):
    """Reject loose JSON metadata before invoking the fixed startup component."""
    require(type(raw) is bytes, "actual startup receipt bytes required")
    record = json.loads(raw)
    require(type(record) is dict, "actual startup receipt object required")
    require(type(record.get("returncode")) is int and record["returncode"] == 0 and
            all(type(record.get(key)) is int and record[key] > 0 for key in ("pid", "pgid", "owner_pgid")),
            "typed successful startup process metadata required")
    held = record.get("held_window_seconds")
    require(type(held) in (int, float), "typed finite held window required")
    try:
        finite = math.isfinite(held)
    except OverflowError:
        finite = False
    require(finite and held >= .05, "typed finite held window of at least .05 seconds required")
    return record


def _validate_fixed_startup_observation(result, generated, expected, *, old, seen):
    require(type(result) is dict and result.get("kind") == FIXED_STARTUP_KIND and result.get("label") == FIXED_STARTUP_LABEL and
            result.get("generated") == generated and result.get("proof") == expected and
            result.get("input_pins") == expected.get("input") and expected.get("selector") == "fast-capacity" and
            expected.get("kind") == "D-structural-fixed-entry-startup-fixture-projection-v1" and
            expected.get("output") == inventory(generated) and expected.get("complete_inverse") is True and
            expected.get("spawn_argument_count") == 2 and expected.get("fixed_entry") is True and
            expected.get("actual_start_S_unchanged") is True, "actual fixed-entry source/projection/role differs")
    record = startup_receipt(result.get("receipt_raw"))
    component, authority = startup_component()
    projection, projection_raw = _startup_helper(PROJECTION, PROJECTION_PIN, "D_structural_fixed_validation_projection")
    require(expected.get("component_authority") == pin(authority) == COMPONENT_PIN and
            expected.get("component_path") == COMPONENT and expected.get("projection_authority") == pin(projection_raw) and
            expected.get("poison_authority") == POISON_PIN,
            "fixed-entry shared mechanism/projection authority differs")
    restored = projection.restore(generated["runtime.c"], expected["fixed_entry_projection"])
    poisoned = projection.restore(restored, expected["restore_abort_projection"])
    compatible = projection.restore(poisoned, expected["shared_poison_projection"])
    adapted = projection.restore(compatible, expected["compatibility_projection"])
    adapter = expected["diagnostic_projection"]
    offset = adapter.get("edit", {}).get("begin")
    require(type(offset) is int and 0 <= offset <= len(adapted) and
            adapted[offset:offset + len(TRACE_OUTPUT)] == TRACE_OUTPUT and
            adapter.get("edit", {}).get("before") == "" and adapter.get("edit", {}).get("after") == TRACE_OUTPUT.decode() and
            adapter.get("complete_inverse") is True and adapter.get("DEV") == 0 and
            adapter.get("counted_output") == pin(COUNTED_OUTPUT), "fixed-entry diagnostic wrapper differs")
    actual = adapted[:offset] + adapted[offset + len(TRACE_OUTPUT):]
    require(adapter.get("input") == expected["input"] and adapter.get("output", {}).get("runtime.c") == pin(adapted) and
            expected["input"]["runtime.c"] == pin(actual) and
            adapter.get("gaps") == [{"begin": 0, "end": offset, **pin(actual[:offset])},
                                    {"begin": offset, "end": len(actual), **pin(actual[offset:])}] and
            all(expected["input"][name] == expected["output"][name] for name in READABLE - {"runtime.c"}),
            "fixed-entry complete actual-source inverse/protected complement differs")
    dialogue = expected.get("dialogue_source")
    require(type(dialogue) is str and expected.get("dialogue") == pin(dialogue.encode()) and
            projection.restore(dialogue.encode(), expected["dialogue_projection"]) == component.STARTUP_DIALOGUE.encode(),
            "fixed-entry dialogue source/inverse differs")
    directory = _absolute(result.get("directory")); binary = _absolute(result.get("binary_path"))
    paths = result.get("source_paths", {})
    require(result.get("flags") == list(STARTUP_FLAGS) and result.get("units") == list(STARTUP_UNITS) and
            paths == {name: directory + "/" + name for name in generated} and binary == directory + "/fixture",
            "fixed-entry fixture flags/units/source paths differ")
    compiled, executed = result.get("compile", {}), result.get("execute", {})
    old._fresh_paths(compiled, [directory, *paths.values(), binary], seen)
    require(compiled.get("command") == ["cc", *STARTUP_FLAGS, *[directory + "/" + name for name in STARTUP_UNITS],
            "-Wl,-T," + directory + "/image.ld", "-o", binary] and compiled.get("cwd") == directory,
            "actual fixed-entry original compiler argv differs")
    require(type(result.get("binary")) is bytes and result["binary"].startswith(b"\x7fELF"),
            "actual no-libc fixed-entry fixture binary required")
    dialogue_path, receipt_path = directory + "/dialogue.py", directory + "/dialogue.json"
    old._fresh_paths(executed, [dialogue_path, receipt_path], seen)
    require(executed.get("command") == [sys.executable, "-I", "-B", dialogue_path, binary, receipt_path] and
            executed.get("cwd") == directory and result.get("dialogue") == dialogue.encode() and
            result.get("stdin") == STARTUP_STDIN, "actual fixed-entry dialogue argv/input differs")
    output = result.get("output"); raw = result["receipt_raw"]
    require(type(output) is bytes and {key: executed["stdout"].get(key) for key in ("bytes", "sha256")} == pin(output),
            "fixed-entry observation differs from original owner pipe")
    require(record.get("complete") is True and record.get("engine_started") is True and
            record.get("engine_reaped") is True and record.get("forced_cleanup") is False and
            record.get("inherits_owner_group") is True and record["owner_pgid"] == record["pgid"] == executed.get("pgid") and
            record.get("no_uci_during_held_window") is True,
            "fixed-entry child did not settle naturally or lacked held-window observation")
    events = record.get("events", [])
    require(type(events) is list and all(type(event) is dict for event in events) and result.get("events") == events and
            b"".join(event["send"].encode() for event in events if "send" in event) == STARTUP_STDIN and
            b"".join(event["receive"].encode() for event in events if "receive" in event) == output,
            "fixed-entry actual event/input/output streams differ")
    lines = output.splitlines()
    markers = [b"TEST_LAST_HELD", b"TEST_LAST_RELEASED", b"TEST_SPAWN2_4", b"TEST_INITIALIZED", b"uciok", b"readyok"]
    require(b"TEST_SPAWN3_4" not in lines and all(lines.count(marker) == 1 for marker in markers) and
            [lines.index(marker) for marker in markers] == sorted(lines.index(marker) for marker in markers),
            "actual two-argument count/first-touch/held/UCI marker ordering differs")
    return {"kind": "D-structural-fixed-entry-startup-observation-v1", "variant": "fast-capacity",
        "source": inventory(generated), "new_projection": deepcopy(expected), "component_authority": pin(authority),
        "compile": deepcopy(compiled), "execute": deepcopy(executed), "binary": pin(result["binary"]),
        "output": pin(output), "receipt": pin(raw), "worker_count": 4, "spawn_argument_count": 2,
        "fixed_entry": True, "actual_start_S_unchanged": True, "TT_bits": 12, "TT_bytes": 65536,
        "held_window_seconds": record["held_window_seconds"], "natural_cleanup": True,
        "parent_carrier_used": False, "full128MiB_qualified": False, "runtime_qualified": False}


def validate_startup_observation(result, generated, expected, *, old, seen):
    require(type(expected) is dict and expected.get("variant", "initial-full") in ("initial-full", "fast-capacity"),
            "named actual startup projection required")
    if expected.get("variant") == "fast-capacity":
        return _validate_fixed_startup_observation(result, generated, expected, old=old, seen=seen)
    require(type(result) is dict and result.get("kind") == STARTUP_KIND and result.get("label") == STARTUP_LABEL and
            result.get("generated") == generated and result.get("proof") == expected and
            result.get("input_pins") == expected.get("input") and expected.get("selector") == SELECTOR and
            expected.get("output") == inventory(generated),
            "actual Structural startup source/projection/role differs")
    startup_receipt(result.get("receipt_raw"))
    component, authority = startup_component()
    adapter = expected.get("diagnostic_projection", {})
    projection = expected.get("component_projection", {})
    require(expected.get("component_authority") == pin(authority) == COMPONENT_PIN and
            expected.get("component_path") == COMPONENT and adapter.get("complete_inverse") is True and
            adapter.get("DEV") == 0 and adapter.get("input") == expected.get("input") and
            adapter.get("edit", {}).get("before") == "" and adapter.get("edit", {}).get("after") == TRACE_OUTPUT.decode() and
            adapter.get("counted_output") == pin(COUNTED_OUTPUT) and projection.get("input") == adapter.get("output") and
            projection.get("output") == expected.get("output"),
            "Structural startup component or diagnostic projection differs")
    observation = component.validate_startup_observation(result, generated, projection, old=old, seen=seen)
    return {"kind": "D-structural-three-argument-startup-observation-v1", "source": inventory(generated),
        "new_projection": deepcopy(expected), "component_observation": observation,
        "component_authority": pin(authority), "compile": deepcopy(observation["compile"]),
        "execute": deepcopy(observation["execute"]), "parent_carrier_used": False,
        "full128MiB_qualified": False, "runtime_qualified": False}


def reserved_paths(record):
    values = record.get("reserved_evidence_paths")
    require(type(values) is list and all(type(path) is str for path in values) and values == sorted(set(values)),
            "canonical immutable parent/archive namespace required")
    return {_absolute(path) for path in values}


def argv_paths(arguments):
    result = set()
    for value in arguments:
        if type(value) is str:
            if value.startswith("-Wl,-T,"):
                value = value[len("-Wl,-T,"):]
            if value.startswith("/"):
                result.add(_absolute(value))
    return result


def require_fresh_paths(paths, used):
    require(len(paths) == len(set(paths)) and not used.intersection(paths),
            "new Structural Board preprocessing reused parent/archive/source/output evidence")


def prepare_carrier(token, *, admission_module, admission_source, bridge_source, runtime, packaging, frozen_inputs, codec=None):
    own = _source(bridge_source, sys.modules[__name__], logical=SELF)
    authority = _source(admission_source, admission_module, logical=ADMISSION)
    record = _admitted(token, admission_module)
    variant = record.get("variant", "initial-full")
    selected = _variant_contract(variant, admission_module, admission_source)
    route = selected["route"]
    require(pin(authority) == record["admission_source"] and pin(own) == record["startup_fixture_authority"],
            "actual Structural authority/renderer source differs")
    require(type(frozen_inputs) is dict and inventory(frozen_inputs) == token.input_pins,
            "carrier complete frozen source closure differs")
    for name in frozen_inputs:
        _relative(name)
    native, linked = token.native, token.linked
    require(record["identity"] == selected["identity"] == {"linked": pin(linked), "stripped": pin(native)},
            "actual new Structural linked/native bytes differ")
    package_options = {"variant": variant, "admission_module": admission_module, "admission_source": admission_source, "codec": codec}
    whole, detail = package_native(native, packaging, **package_options)
    repeated, again = package_native(native, packaging, **package_options)
    rows = [row for row in token.packages if row.get("route") == route]
    require(len(rows) == 1 and whole == repeated == token.package_bytes(route) and detail == again and
            rows[0].get("whole") == pin(whole) and rows[0].get("detail") == detail and
            rows[0].get("reproduced") is True and rows[0].get("whole_repeats") == 2 and pin(whole) == selected["whole"],
            "two actual selected whole repetitions differ from admission")
    boundary = detail["header_bytes"]
    expected = {**{"native_" + key: value for key, value in pin(native).items()},
                **{"whole_" + key: value for key, value in pin(whole).items()},
                "header_bytes": boundary, "payload_bytes": len(whole) - boundary}
    inputs = deepcopy(token.input_pins)
    contract = {"kind": KIND, "source_admission_kind": SOURCE_KIND, "variant": variant, "selector": selected["selector"],
        "structural_selection": deepcopy(selected["selection"]), "options": list(OPTIONS), "selected_route": route,
        "nonreturning": selected["nonreturning"], "startup_argument_count": selected["startup_argument_count"],
        "ownership_policy": POLICY, "last_search_output_required": False, "input_contract": INPUT_CONTRACT,
        "shutdown_scope": SCOPE, "event_target_confirmed": False, "admission": record,
        "identifier_composition": token.identifier_composition, "actual_rules_generation": "pending-fresh-structural-Board-fixture"}
    manifest = {"kind": KIND, "family": "D", "variant": variant, "profile": deepcopy(record["profile"]), "route": route,
        "representation": "packed", "expected": expected, "native_identity": deepcopy(selected["identity"]),
        "source_contract": contract, "input_pins": inputs, "readable_inputs": inventory(token.readable),
        "shipping_inputs": inventory(token.shipping), "fresh_replay_commands": token.fresh_commands,
        "source_native_package_admitted": True, "fresh_full_artifact_runtime": False, "rules_qualified": False,
        "physical_placement_qualified": False, "size_qualified": False, "selected": False,
        "shutdown_scope": SCOPE, "event_target_confirmed": False}
    files = {"program": whole, "native/image": native, "native/linked": linked,
        **{"generated-readable/" + name: data for name, data in token.readable.items()},
        **{"shipping-inputs/" + name: data for name, data in token.shipping.items()},
        **{"inputs/" + name: data for name, data in frozen_inputs.items()},
        "source-admission.json": _json(record), "build.json": _json(manifest)}
    policy = {"mode": "persistent", "variant": "raw-clone", "startup_threads": 5, "between_GO_threads": 5,
              "active_threads": 5, "input_during_GO": "asynchronous", "initialization_join_before_uci": True}
    wrapper = {"entry_cleanup": "loader-owned-fd", "temp_strategy": "memfd-CLOEXEC", "cleanup_seconds": 0, "parent_removed": False}
    admitted = runtime.AdmittedBuild("D", "test-p4", "packed", "program", "shipping-inputs/main.c", "native/image",
        expected, {**record["profile"], "ply": 128, "max_position_plies": 4095}, policy, wrapper, inputs, contract)
    return files, admitted


def shipping_board(token, board_preprocessed, *, admission_module, admission_source, minifier, lexical):
    authority = _source(admission_source, admission_module, logical=ADMISSION)
    record = _admitted(token, admission_module)
    require(pin(authority) == record["admission_source"] and type(board_preprocessed) is bytes,
            "actual Structural Board source/preprocess required")
    composition = token.identifier_composition
    board = minifier.compact_source(board_preprocessed, "c").rstrip(b"\n")
    for old, new in composition["legacy"].items():
        board = lexical._replace({"main.c": board}, old, new)["main.c"]
    for rounds in composition["scalar_typedef_rounds"]:
        for step in rounds:
            pieces, offset = [], 0
            for removal in step.get("main.c", {}).get("removed", []):
                begin, end = removal["begin"], removal["end"]
                require(type(begin) is int and type(end) is int and offset <= begin < end, "actual typedef deletion interval differs")
                if begin >= len(board):
                    continue
                require(end <= len(board) and board[begin:end] == removal["declaration"].encode(),
                        "full-TU deletion cuts or differs inside actual Structural Board prefix")
                pieces.append(board[offset:begin]); offset = end
            pieces.append(board[offset:]); board = b"".join(pieces)
    text, pieces, offset = board.decode(), [], 0
    for begin, end, name in lexical._identifier_spans(text):
        if name in composition["accepted_alpha"]:
            pieces.extend((text[offset:begin], composition["accepted_alpha"][name])); offset = end
    pieces.append(text[offset:]); board = "".join(pieces).encode()
    require(board.endswith(b"}") and token.shipping["main.c"].startswith(board),
            "actual Structural Board is not the complete admitted shipping prefix")
    return board


def render_rules(token, cases, *, admission_module, admission_source, preprocess_board, shared, minifier, lexical):
    authority = _source(admission_source, admission_module, logical=ADMISSION)
    record = _admitted(token, admission_module)
    require(pin(authority) == record["admission_source"], "actual Structural rules authority differs")
    readable, flags, label = token.readable, record["flags"], "structural-actual-board"
    receipt = preprocess_board(dict(readable), list(flags), label)
    require(type(receipt) is dict and receipt.get("kind") == "D-search-board-preprocess-v1" and
            receipt.get("label") == label and receipt.get("input_pins") == inventory(readable) and receipt.get("flags") == list(flags),
            "fresh Structural Board source/flags/role differs")
    directory = _absolute(receipt.get("readable_dir"))
    row = receipt.get("command", {}); _settled(row)
    require(row.get("command") == ["cc", "-E", "-P", *flags, directory + "/board.c"] and row.get("cwd") == directory,
            "fresh actual Structural Board original argv differs")
    used = reserved_paths(record)
    for old in token.fresh_commands:
        for command in old.get("commands", [old.get("command", {})]):
            old_directory = command.get("cwd")
            used.add(old_directory)
            used.update(command.get(stream, {}).get("path") for stream in ("stdout", "stderr"))
            if type(old_directory) is str:
                used.update(old_directory + "/" + _relative(name) for name in old.get("input_pins", {}))
            used.update(argv_paths(command.get("command", [])))
        used.update(old.get("source_paths", {}).values())
        used.update(old.get(name) for name in ("linked_path", "stripped_path", "binary_path"))
    paths = [directory, *[directory + "/" + name for name in readable],
             *[_absolute(row.get(stream, {}).get("path")) for stream in ("stdout", "stderr")]]
    require_fresh_paths(paths, used)
    output = receipt.get("output")
    require(type(output) is bytes and {key: row["stdout"].get(key) for key in ("bytes", "sha256")} == pin(output),
            "actual Structural Board stdout differs")
    board = shipping_board(token, output, admission_module=admission_module, admission_source=admission_source,
                           minifier=minifier, lexical=lexical)
    renames = token.identifier_composition["composed"]
    require(not set(renames).intersection({"memcpy", "memset", "abort"}), "actual Board memory/abort names must remain original")
    counts = {}
    for _, _, name in lexical._identifier_spans(board.decode()):
        counts[name] = counts.get(name, 0) + 1
    for name in ("strlen", "strcmp", "strtok_r"):
        require(counts.get(renames.get(name, name)) == 1, "fixture-only string declaration acquired an actual Board consumer")
    size = renames.get("size_t", "size_t")
    declarations = b"\n" + (("typedef " + size + " size_t;\n").encode() if size != "size_t" else b"")
    declarations += (b"extern size_t strlen(const char *);extern int strcmp(const char *,const char *);"
        b"extern char *strtok_r(char *,const char *,char **);extern int printf(const char *,...);"
        b"extern int puts(const char *);extern char *strcpy(char *,const char *);\n")
    fixture = shared.render_bound_fixture(board, {"board": renames.get("Board", "Board"), "start": renames.get("start", "start"),
        "generate": renames.get("gen", "gen"), "make": renames.get("make", "make"), "four_args": False}, cases, declarations)
    return fixture, {"kind": KIND + ".actual-board-fixture", "source_admission": pin(_json(record)),
        "fresh_preprocess": {"label": label, "input_pins": receipt["input_pins"], "flags": list(flags), "command": deepcopy(row), "output": pin(output)},
        "shipping_main": pin(token.shipping["main.c"]), "shipping_board_prefix": pin(board), "fixture": pin(fixture),
        "TT_allocated": False, "native_entry_called": False, "compiled": False, "executed": False, "rules_qualified": False,
        "input_contract": INPUT_CONTRACT, "last_search_output_required": False, "shutdown_scope": SCOPE, "event_target_confirmed": False}
