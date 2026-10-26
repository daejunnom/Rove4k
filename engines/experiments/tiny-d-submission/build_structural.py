"""Generate only the reviewed full P4 fast-capacity D source/native/packages.

This is a generation adapter, not StructuralAdmission or runtime authority.
Upper qualification and production/Ubuntu22 acceptance remain adoption gates.
Execution requires --execute, a new external output, and an external hard wall.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import lzma
from pathlib import Path, PurePosixPath
import platform
import stat
import sys
from types import CodeType, FunctionType, ModuleType

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
SELF = D + "build_structural.py"
FORMAT = "rove4k-D-structural-production-v1"
PROFILE = "test-p4"
VARIANT = "fast-capacity"
READABLE = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")
UNITS = ("main.c", "start.S")
PACKED = "D-packed-xz-bcj-hc3-unnamed"
JIT = "D-source-jit"
CONFIG = {"lc": 0, "lp": 0, "pb": 0, "mf": lzma.MF_HC3, "nice_len": 32, "depth": 64}
_EXECUTING_CODE = sys._getframe().f_code

# The existing LF owners and canonical inputs of this one reviewed class.
# The adapter itself is captured separately, without a recursive self hash.
REVIEWED_INPUTS = {
    D+"source.py": (9178, "7bc2e917d3c267dd2526349a8faa47799eabca3d09d4261d2f0d63fd475ab72e"),
    D+"build.py": (16475, "1e51803539f0038e7e729431b9f73bbc325f735d512cde24a70c9a66e9754a41"),
    D+"storage.py": (9118, "477f07d2d659613732124e1f3ea79100e09a2557acb63ff927c42c32a9fe8eee"),
    D+"publication.py": (9482, "9958da259d9b622f7ff2559f248bf4e5c70ab0cb69f0c5b13af1d829e115c10f"),
    D+"process_owner.py": (11279, "e8951daa552e01dca79214f4bc06780f2eeed8542cad4f48ab97e1ca4be359f2"),
    D+"syscall_arity.py": (10414, "9c294abe9c26747cbe188d0bc5c86ff450656870e213664802a4fd1dae8163fd"),
    D+"valid_input.py": (7755, "2aa36a2b0e8ba9b8c90739223b36a77fddf5fc9f718d36a8a92711f8fc75cdb0"),
    D+"search_compact.py": (10087, "cd5fa7b2c3c9c1d40664153bbd7f1e3146b03e3de8b237134f6e8321f8e0d8d6"),
    D+"no_tid_startup.py": (10414, "3c48e05083cfbeab1caeaedff0bdb271260890fda5b64728f5ac6f6395c3d350"),
    D+"d_square_successor.py": (12482, "4dd3348605d7816577e6c1953d1830132bfc553cf502d2816211d3cc3110e4e1"),
    D+"packaging.py": (3184, "928b7f2ea76787994a4d47f516395583af5cba0bfe840d54fc5321056558faa6"),
    D+"reduce.py": (5294, "9394a7e11e8d23be6189ee8d3e1b17d1a7f1e86c127147394dbf04ca25d59f17"),
    D+"probe_d_square_successor.py": (23747, "1737f63a966cff9677c1ffc653753770e7ccbbb7ba43ab2973ad01b2c28d8fe9"),
    D+"structural_admission.py": (53311, "f0c1acc0f1093c26c1cf9b771cece96068560854667e27716fb4e1d4ccffa1af"),
    D+"structural_size.py": (19309, "4723b27096973c59e98098ffbd3c69655eb29ba35c17ced3843084b78cf64f0d"),
    D+"structural_codec.py": (5425, "09a00445ab551b4c212e9e46e506878c02101fff653a16193b782c658a4eae65"),
    D+"structural_board.py": (26842, "c988f05cf18f5d9710204b6464ab53d4972824a59b631d7a4dafb868902e0595"),
    D+"structural_search.py": (16838, "2b3e874e1cc7f3f4e0902bb0f799bb6b0f78840f4404176bc1442c2657e92be1"),
    D+"structural_runtime.py": (21364, "000cc9cf56518574479e18672810ab95d82ab62a49de7d6f606786e14a3fb65a"),
    D+"structural_board_next.py": (23995, "25e65e641ef806f4c49fb2245ba53e21bc67f371ddcf71fa08c0bf90bf4fb5c3"),
    D+"structural_search_next.py": (20395, "8de9083fe73e2abef96382567cbdbe5b3a29892fb003ce2b903b86d4e45c9ae6"),
    D+"structural_platform.py": (16797, "89badb65c686d012b0c23ce2419b068d47a7a9c19865450e6eb97cd361731c5f"),
    D+"search_admission.py": (53743, "287947522e4d13f57ee9acb59791af666074812d935f47dbb633fc91086e319c"),
    "engines/scripts/production.py": (21126, "b32737b69b07a93438aa319ccf9f18186d1e5ad0f552b9f637d8748b8c90fbcd"),
    "engines/scripts/minify.py": (6624, "eb5eeca57b8f0f7225e639c8ee9e13fd1d5a5f159e58c38d66e0dea3b0433c3b"),
    "engines/scripts/rename_c.py": (12574, "9d7d09e2787cfda21701384be94ed00d588165574da5d8aacdf731fcb317cbe5"),
    "engines/scripts/source_composition.py": (5359, "1422d3e97f6ab0dc969e0feee6a04e3c97d6677323b3e91c00f1383f8baaeadd"),
    "engines/compact/tiny-entry-d/shipping_fused_ray.py": (5252, "1d9d23699300c0d1ef3c27a06f4f705b2074bba2e5bc5b684716c11e02f4e54b"),
    "engines/compact/tiny-entry-d/packer.py": (9528, "af95c8fd8a38f999bb846f024e13689d417e28c0ce0ec830f8a200b4cef3fd7e"),
    "engines/experiments/tcec-scope/build.py": (34364, "5fa10c6f8f032be374bf3a86bbe6ca558076630a2cc3170b41890f691688f563"),
    "engines/compact/tiny-entry-d/recipe.json": (111894, "3dfe79a11ece740f70468948a8b579f7a110b919d116ad0acb21052968b3de73"),
    "engines/common/board.c": (4553, "7f231ee347a66f8117d15934bda4adb188309db433598b5634afc46bbb61d1e8"),
    "engines/common/move.c": (3246, "e01d84200956050c6c064acc9d6fe812a6ade6e934993a332db518ffd27f2e9c"),
    "engines/compact/tiny-entry-d/native/tiny.h": (2917, "55a0a29dc2a5c378937443c4cc6c2067520a280793d7ecdd14a733941351e4ba"),
    "engines/compact/tiny-entry-d/native/board.c": (5700, "baa95dfecdd4fcc632ca9aea89ec3902b36e81ee5e84f2b15cce0ef051001155"),
    "engines/compact/tiny-entry-d/native/search.c": (6317, "6f28dc49b1caf346ead734b4d054039418ce863d039a9ad18cd5b9477884f150"),
    "engines/compact/tiny-entry-d/native/runtime.c": (14885, "2febf5acec5a3c74ab3a6dcb2fd2a1eb2ba44fab4d6892d9c354fcdcebfe4342"),
    "engines/compact/tiny-entry-d/native/start.S": (845, "4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b"),
    "engines/compact/tiny-entry-d/native/image.ld": (446, "38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b"),
}
MODULES = {
    **{name: D+filename+".py" for name, filename in (
        ("source", "source"), ("build", "build"), ("storage", "storage"),
        ("publication", "publication"), ("owner", "process_owner"), ("arity", "syscall_arity"),
        ("valid", "valid_input"), ("search", "search_compact"), ("no_tid", "no_tid_startup"),
        ("square", "d_square_successor"), ("packaging", "packaging"), ("reducer", "reduce"),
        ("legacy", "probe_d_square_successor"), ("structural_admission", "structural_admission"),
        ("codec", "structural_codec"), ("search_admission", "search_admission"), ("terminal", "structural_size"),
        *(("structural_"+name, "structural_"+name) for name in
          ("board", "search", "runtime", "board_next", "search_next", "platform")))},
    "minifier": "engines/scripts/minify.py", "lexical": "engines/scripts/rename_c.py",
    "packer": "engines/compact/tiny-entry-d/packer.py",
    "host": "engines/experiments/tcec-scope/build.py",
}
EXPECTED_READABLE = {
    "board.c": (10346, "4f00f4c88eefe89fb6a61445a566c034095d074b14db37a07919fc3c45b48070"),
    "image.ld": REVIEWED_INPUTS["engines/compact/tiny-entry-d/native/image.ld"],
    "runtime.c": (15784, "eea671466ff74b3f619d99f90278f30b491c163e40335d61dbe585090deea4e4"),
    "search.c": (6001, "c25fe0cc2faf50397e9cf24af92eab5de4133341a893a05a740672f939282099"),
    "start.S": (697, "701f24836cffd49614235cfe11e6b961ee1b2c2b7d2466965b0916217cf43586"),
    "tiny.h": (3052, "d24ccd0ea44a0fa8c984bf3085a9495e54bc76c75b4c7bcd8b217d938e07417b"),
}
EXPECTED_SHIPPING = {
    "image.ld": EXPECTED_READABLE["image.ld"],
    "main.c": (16868, "d4db3843c11ea9dee8940d8b40bb9aa1deaecb62153f03e220bb02dbc3fcdf17"),
    "start.S": (456, "8b0207037af14e205537cf3b831708604a4c8e48abd9db6762775412c9227046"),
}
EXPECTED_LINKED = (6816, "548acb314429f506fe0db89ed67c607684001e0bd56bbfddeac123c00b5e66b1")
EXPECTED_NATIVE = (6464, "66f79c85ef322611b193a13ff85dd410a90779cb32c4f63dcde33f4897c0fe17")
EXPECTED_WHOLE = (4737, "f7a34bd51c186a328f7146e00d092e562eddc4217e145b6a350d6a4755fcd5f0")
EXPECTED_JIT = (7072, "b58c845d4fac1863279d48140d7924eb376f4584c016d8d09274adaebf31a807")
EXPECTED_HEADER = (205, "848c6636bf51635078cddf8ca2a94eae29e2b4d33153997d36ae11f523a0d84c")
EXPECTED_BEFORE_REDUCTION = (21138, "d3215655a49578b89ae3b59de09e4f468a8d25c241e9837011790f6c2649736e")
EXPECTED_REDUCTION_STAGES = (
    ("unused-scalar-typedefs", "accepted", EXPECTED_LINKED[1]),
    ("batch-alpha", "rejected-native-differs", "de4d144be5b01e499e6bc8e956d1284fe0e6ea8b83971ff808ca115de628dd68"),
)


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def expected(pair):
    return {"bytes": pair[0], "sha256": pair[1]}


def inventory(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def selection(profile, variant):
    require(type(profile) is str and profile == PROFILE and type(variant) is str and variant == VARIANT,
            "only the explicit reviewed test-p4 fast-capacity producer is available")


def normalized(path):
    path = Path(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= 1 << 20,
            "bounded regular source input required")
    data = path.read_bytes().replace(b"\r\n", b"\n")
    after = path.lstat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and b"\r" not in data,
            "source changed during read or contains a lone CR")
    return data


def validate_inputs(inputs):
    require(type(inputs) is dict and set(inputs) == set(REVIEWED_INPUTS) | {SELF}, "exact producer input closure required")
    for name, identity in REVIEWED_INPUTS.items():
        require(type(inputs[name]) is bytes and b"\r" not in inputs[name] and pin(inputs[name]) == expected(identity),
                "reviewed LF producer input differs: " + name)
    require(type(inputs[SELF]) is bytes and b"\r" not in inputs[SELF], "adapter LF source required")
    require(normalized(Path(__file__)) == inputs[SELF] and
            compile(inputs[SELF], __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "producer adapter input differs from its executing source")


def capture_inputs(root=ROOT):
    inputs = {name: normalized(Path(root) / name) for name in (*REVIEWED_INPUTS, SELF)}
    validate_inputs(inputs)
    require(compile(inputs[SELF], __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "producer source differs from its executing module")
    return inputs


def _load(name, path, raw):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def load_modules(root, inputs):
    validate_inputs(inputs)
    result = {role: _load("D_structural_producer_"+role, Path(root) / name, inputs[name])
              for role, name in MODULES.items()}
    validate_modules(result, inputs)
    return result


def validate_modules(modules, inputs):
    require(type(modules) is dict and set(modules) == set(MODULES), "exact actual producer module roles required")
    for role, logical in MODULES.items():
        module = modules[role]
        require(type(module) is ModuleType and sys.modules.get(module.__name__) is module,
                "registered actual producer module required")
        path = Path(module.__file__)
        require(path.parts[-len(PurePosixPath(logical).parts):] == PurePosixPath(logical).parts and
                normalized(path) == inputs[logical], "executing producer role/source differs")
        code = compile(inputs[logical], str(path), "exec", dont_inherit=True)
        for item in code.co_consts:
            if isinstance(item, CodeType) and item.co_flags & 2 and not item.co_name.startswith("<"):
                function = module.__dict__.get(item.co_name)
                require(type(function) is FunctionType and function.__code__ == item and
                        function.__globals__ is module.__dict__, "executing producer function differs")


def prepare_sources(modules, inputs, *, profile=PROFILE, variant=VARIANT):
    """Pure finite source composition; no compiler, encoder or token factory."""
    selection(profile, variant)
    validate_inputs(inputs)
    validate_modules(modules, inputs)
    m = modules
    api = m["source"].production()
    resource = api.resource_profile(profile)
    require(resource.workers == 4 and resource.layout(16).bits == 23 and resource.to_record(16)["tt_bytes"] == 128 << 20,
            "exact W4/TT23 P4 resource required")
    files, canonical = m["source"].prepare(resource, equivalent_edits=True)
    stages = [{"role": "canonical", "proof": canonical, "output": inventory(files)}]
    def record(role, before, after, proof):
        stages.append({"role": role, "input": inventory(before), "output": inventory(after), "proof": proof})
        return after
    before = files
    files, storage = m["storage"].transform(files, prefix=True, dense=False)
    require(m["storage"].restore(files, storage) == before, "complete prefix storage inverse differs")
    record("prefix-storage", before, files, storage)
    before = files
    files, owner = m["owner"].transform(files, m["publication"])
    require(m["owner"].restore(files, owner, m["publication"]) == before, "process-owner inverse differs")
    record("process-owner", before, files, owner)
    before = files
    files, arity = m["arity"].transform(files, m["owner"], m["publication"], owner,
                                         noinline_wake=True, immediate_exit=True)
    require(m["arity"].restore(files, arity, m["owner"], m["publication"]) == before, "syscall arity inverse differs")
    record("syscall-arity", before, files, arity)
    before = files
    files, valid = m["valid"].transform(files, m["arity"], m["owner"], m["publication"], arity, mode="one-byte-valid")
    require(m["valid"].restore(files, valid, m["arity"], m["owner"], m["publication"]) == before, "valid-input inverse differs")
    record("valid-input", before, files, valid)
    before = files
    files, search = m["search"].transform(files, m["valid"], m["arity"], m["owner"], m["publication"], valid,
                                          options=("previous-piece", "unsigned-history"))
    require(m["search"].restore(files, search, m["valid"], m["arity"], m["owner"], m["publication"]) == before,
            "search source inverse differs")
    record("search-compact", before, files, search)
    for role in ("no_tid", "square"):
        before = files
        files, proof = m[role].transform(files)
        require(m[role].restore(files, proof) == before, "complete " + role + " source inverse differs")
        record(role, before, files, proof)
    initial, initial_proof = m["structural_admission"].transform(files, m, inputs, "initial-full")
    final, proof = m["structural_admission"].transform(files, m, inputs, variant)
    require(proof["stages"][:3] == initial_proof["stages"] and
            inventory(initial) == proof["stages"][2]["output"], "initial full structural prefix differs")
    require(set(final) == set(READABLE) and inventory(final) == {n: expected(v) for n, v in EXPECTED_READABLE.items()},
            "reviewed complete final readable source differs")
    engine_inputs = canonical["source_closure"]["engine_inputs"]
    closure = api.SourceClosure.validate(api.engine_spec("D"), engine_inputs=engine_inputs,
        tool_inputs=tuple(n for n in inputs if n not in engine_inputs))
    return final, {"kind": FORMAT+".source", "variant": variant, "resource": resource.to_record(16),
                   "parent_stages": stages, "initial_structural": initial_proof, "structural": proof,
                   "output": inventory(final), "source_closure": closure.to_record()}


def restore_scalar_rounds(files, rounds):
    """Invert only the accepted owner-produced scalar typedef removal records."""
    result = dict(files)
    for row in reversed(rounds):
        for name, proof in row.items():
            current = result[name]
            require(pin(current) == proof["output"], "typedef inverse output differs")
            text, parts, at, original_at = current.decode(), [], 0, 0
            for edit in proof["removed"]:
                begin, end, declaration = edit["begin"], edit["end"], edit["declaration"]
                require(type(begin) is int and type(end) is int and original_at <= begin < end and
                        len(declaration) == end-begin, "typedef inverse edit extent differs")
                gap = begin-original_at
                require(at+gap <= len(text), "typedef inverse gap exceeds remaining output")
                parts.extend((text[at:at+gap], declaration))
                at += gap
                original_at = end
            parts.append(text[at:])
            restored = "".join(parts).encode()
            require(pin(restored) == proof["input"], "complete typedef inverse differs")
            result[name] = restored
    return result


def strict_decode(payload, wanted):
    decoder = lzma.LZMADecompressor()
    decoded = decoder.decompress(payload, max_length=len(wanted)+1)
    require(decoded == wanted and decoder.eof and not decoder.unused_data,
            "strict complete input inverse/EOF/trailing bytes differ")
    return {"decoded": pin(decoded), "strict_EOF": True, "trailing_bytes": 0, "complete_input_inverse": True}


def _save(out, report):
    (out / "build.json").write_text(json.dumps(report, indent=2) + "\n")


def build_snapshot(out, snapshot, current_root, inputs):
    """Execute the finite generation; caller supplies the whole-operation wall."""
    validate_inputs(inputs)
    m = load_modules(snapshot, inputs)
    files, proof = prepare_sources(m, inputs)
    resource = m["source"].production().resource_profile(PROFILE)
    flags = m["build"].native_flags(resource, "s")
    report = {"format": FORMAT, "family": "D", "variant": VARIANT, "resource": resource.to_record(16),
              "complete": False, "frozen_execution": True, "inputs": inventory(inputs), "proof": proof,
              "flags": flags, "units": list(UNITS), "commands": [], "candidates": [],
              "scope": "finite source/proof generation and native/whole reproduction only; upper qualification is a separate adoption precondition"}
    raw = out / "generated-readable"
    raw.mkdir()
    for name, data in files.items():
        (raw / name).write_bytes(data)
    save = lambda: _save(out, report)
    save()
    host, body_error = None, None
    owner = m["host"]
    owner.LIMITS = {**owner.LIMITS, "aggregate_wall": 180, "per_command_wall": 45,
                    "parent_CPU": 1200, "parent_CPU_hard": 1260, "child_CPU": 40, "tool_output_bytes": 8 << 20}
    try:
        host = owner.Host(out, report, save)
        report["compiler"] = host.run(["cc", "--version"], cwd=out, kind="compiler-version").decode().splitlines()[0]
        require(report["compiler"] == m["legacy"].BANNER, "reviewed Ubuntu GCC13 compiler banner required")
        cpp = host.run(["cc", "-E", "-P", *flags, "-I", str(raw), "-x", "c", "-"], cwd=raw,
                       kind="preprocess-single-TU", data=m["legacy"].DRIVER)
        entry = host.run(["cc", "-E", "-P", "-x", "assembler-with-cpp", str(raw / "start.S")], cwd=raw, kind="preprocess-entry")
        emitted = {"main.c": m["minifier"].compact_source(cpp, "c"), "start.S": entry, "image.ld": files["image.ld"]}
        report["single_TU"] = {"members": ["board.c", "search.c", "runtime.c"],
                               "driver": pin(m["legacy"].DRIVER), "preprocessed": pin(cpp)}
        legacy = m["legacy"].LEGACY
        require(len(set(legacy.values())) == len(legacy) and not set(legacy) & set(legacy.values()) and
                not set(legacy.values()) & set(m["lexical"]._ANY_WORD.findall(emitted["main.c"].decode())), "legacy identifier ownership/capture differs")
        original = emitted["main.c"]
        mapped = {"main.c": original}
        for before, after in legacy.items():
            mapped = m["lexical"]._replace(mapped, before, after)
        inverse = dict(mapped)
        for before, after in reversed(tuple(legacy.items())):
            inverse = m["lexical"]._replace(inverse, after, before)
        require(inverse["main.c"] == original and pin(mapped["main.c"]) == expected(EXPECTED_BEFORE_REDUCTION), "complete legacy inverse/pre-reduction source differs")
        emitted.update(mapped)
        def compile_files(contents, directory, kind):
            directory.mkdir()
            for name, data in contents.items():
                (directory / name).write_bytes(data)
            host.run(["cc", *flags, str(directory / "main.c"), str(directory / "start.S"),
                      "-Wl,-T,"+str(directory / "image.ld"), "-o", str(directory / "linked")], cwd=directory, kind=kind)
            linked = (directory / "linked").read_bytes()
            native = m["packer"].strip_native(linked)
            (directory / "native").write_bytes(native)
            return linked, native
        def digest(contents, trial):
            return pin(compile_files({**emitted, **contents}, out / ("reduction-"+trial), "reduce-"+trial)[0])["sha256"]
        reduced, reduction = m["reducer"].reduce_sources(mapped, digest, m["lexical"],
            reserve=m["lexical"]._ANY_WORD.findall((entry + emitted["image.ld"]).decode()))
        require(tuple((r["kind"], r["status"], r["native_sha256"]) for r in reduction["stages"]) == EXPECTED_REDUCTION_STAGES and
                reduction["baseline_native_sha256"] == reduction["final_native_sha256"] == EXPECTED_LINKED[1], "reviewed finite reduction gate outcomes differ")
        pruned, rounds = m["reducer"].prune_typedefs(mapped, m["lexical"])
        require(pruned == reduced and rounds == reduction["stages"][0]["rounds"] and
                restore_scalar_rounds(reduced, rounds) == mapped, "owner scalar reduction/full inverse differs")
        emitted.update(reduced)
        require(inventory(emitted) == {n: expected(v) for n, v in EXPECTED_SHIPPING.items()}, "reviewed final shipping inputs differ")
        report["source_reduction"] = reduction
        report["identifier_composition"] = m["search_admission"]._composition(legacy, reduction)
        report["shipping_inputs"] = inventory(emitted)
        shipping = out / "shipping-inputs"
        shipping.mkdir()
        for name, data in emitted.items():
            (shipping / name).write_bytes(data)
        native_rows, linked_rows, images = [], [], []
        for index in range(2):
            directory = out / ("attempt-"+str(index))
            linked, native = compile_files(emitted, directory, "compile-native-"+str(index))
            require(report["commands"][-1]["stderr"]["bytes"] == 0 and pin(linked) == expected(EXPECTED_LINKED) and
                    pin(native) == expected(EXPECTED_NATIVE), "reviewed final linked/native identity or diagnostics differ")
            geometry = m["build"].kernel_geometry(m["packer"], native, resource.workers)
            native_rows.append({"path": str(directory / "native"), **pin(native), "geometry": geometry})
            linked_rows.append({"path": str(directory / "linked"), **pin(linked),
                                "geometry": m["build"].kernel_geometry(m["packer"], linked, resource.workers)})
            images.append((linked, native))
        require(images[0] == images[1], "two actual linked/native generations differ")
        report.update(native=native_rows[0], native_rebuilds=native_rows, native_reproduced=True,
                      source_jit_native=linked_rows[0], source_jit_native_rebuilds=linked_rows)
        report["source_jit_native_reuse"] = {"source": inventory(emitted), "flags": flags, "units": list(UNITS),
            "compiler": report["compiler"], "postprocess": "none: source-JIT executes the same linked ELF; packed route alone strips it",
            "linked_generations": [pin(image[0]) for image in images]}
        for route in (PACKED, JIT):
            wholes, details, inverses = [], [], []
            for _, native in images:
                if route == PACKED:
                    require(len(native) <= 8192, "dict8192 native domain exceeded")
                    whole, detail = m["codec"].package(native, dict(CONFIG), m["packaging"], unnamed=True)
                    require(detail["config"] == CONFIG and detail["dict_size"] == 8192 and detail["check"] == "CRC64" and
                            detail["unnamed_memfd"] is True and pin(whole) == expected(EXPECTED_WHOLE), "fixed HC3 whole recipe differs")
                    code = m["packaging"].NATIVE_CODE.replace('os.memfd_create("Rove4k-D",1)', 'os.memfd_create("",1)', 1)
                    wanted = native
                else:
                    whole, detail = m["packaging"].package_source(emitted, flags, UNITS)
                    code = m["packaging"].SOURCE_CODE
                    wanted = json.dumps({"files": {n: emitted[n].decode() for n in sorted(emitted)},
                        "flags": flags, "units": list(UNITS)}, separators=(",", ":"), ensure_ascii=True).encode()
                    require(pin(whole) == expected(EXPECTED_JIT), "reviewed source-JIT sibling differs")
                boundary = detail["header_bytes"]
                require(type(boundary) is int and 0 < boundary < len(whole) and detail["payload_bytes"] == len(whole)-boundary, "whole payload extent differs")
                header, payload = whole[:boundary], whole[boundary:]
                if route == PACKED:
                    require(pin(header) == expected(EXPECTED_HEADER), "reviewed empty-name bootstrap differs")
                inverse = strict_decode(payload, wanted)
                rebuilt, rebuilt_header = m["packaging"].envelope(code, payload)
                require(rebuilt == whole and rebuilt_header == header, "complete header/offset/whole inverse differs")
                wholes.append(whole)
                details.append(detail)
                inverses.append(inverse)
            require(wholes[0] == wholes[1] and details[0] == details[1], "two independent whole generations differ")
            program = out / route
            program.write_bytes(wholes[0])
            program.chmod(0o755)
            row = {"path": str(program), "representation": "packed-native" if route == PACKED else "source-jit",
                   "native": native_rows[0] if route == PACKED else linked_rows[0], **pin(wholes[0]), **details[0],
                   "package_reproduced": True, "package_rebuilds": [pin(d) for d in wholes], "inverse_rebuilds": inverses}
            if route == PACKED:
                row.update(cleanup="memfd-CLOEXEC", recipe={"codec": "xz-bcj", "check": "CRC64", "config": dict(CONFIG),
                    "dict_size": 8192, "unnamed_memfd": True})
            report["candidates"].append(row)
        require({n: normalized(Path(current_root) / n) for n in inputs} == inputs and
                {n: normalized(Path(snapshot) / n) for n in inputs} == inputs, "producer source closure changed")
        validate_modules(m, inputs)
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        m["terminal"].finish_report(host, report, save, body_error)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="execute generation only; caller must apply an external whole-operation hard wall")
    args = parser.parse_args(argv)
    selection(args.profile, args.variant)
    require(args.execute, "generation is inactive without explicit --execute")
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 producer required")
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p / ".git").exists() for p in (out, *out.parents)),
            "new absolute output outside every Git checkout required")
    inputs = capture_inputs()
    out.mkdir(parents=True)
    snapshot = out / "inputs"
    for name, data in inputs.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    require(capture_inputs() == inputs, "source changed during producer snapshot")
    executing = _load("D_structural_frozen_producer", snapshot / SELF, inputs[SELF])
    result = executing.build_snapshot(out, snapshot, ROOT, inputs)
    print(json.dumps({"format": result["format"], "profile": PROFILE, "variant": VARIANT,
        "complete": result["complete"], "native": result["native"]["bytes"],
        "candidates": {Path(row["path"]).name: row["bytes"] for row in result["candidates"]}}), flush=True)


if __name__ == "__main__":
    main()
