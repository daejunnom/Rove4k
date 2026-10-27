"""Finite, source-owned size experiments after the BSS P4 candidate.

Reuses the unchanged strict producer for the control and the existing generic
generation/packaging data path for new candidates.  Results do not select a
production recipe or grant semantic, runtime, strength or event qualification.
Compiler and codec execution require --execute and an externally bounded host.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
EXTRA = ("structural_next.py", "runtime_size_next.py", "board_size_next.py",
         "search_size_next.py", "move_input_size.py")
BSS_NATIVE = (6368, "293b85f0ce95a763037bca96ba736f52974553ec632a2b540054f246f8e74afd")
BSS_WHOLE = (4689, "9f385a06f13eeb3272243cef598f0abd6e19cbb907696f98b3d3be6985cf4ab5")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def prepare(root=ROOT):
    owner = load("D_next_bss_owner", Path(root) / D / "structural_bss_cost.py")
    inputs = owner.capture_inputs(root)
    core = owner._core(root)
    baseline = owner.validate_inputs(inputs, core)
    modules = core.load_modules(root, baseline)
    control, proof = core.prepare_sources(modules, baseline)
    helper = owner._bss(root, inputs[owner.BSS])
    bss, bss_proof = owner._apply_bss(helper, control, modules["source"], 23)
    changes = {name: load("D_next_" + name, Path(root) / D / (name + "_size_next.py"))
               for name in ("runtime", "board", "search")}
    changes["move"] = load("D_next_move_input", Path(root) / D / "move_input_size.py")
    return owner, core, baseline, modules, control, bss, proof, bss_proof, changes


def options(changes):
    result = {"runtime/" + name: ("runtime", name) for name in changes["runtime"].VARIANTS}
    result.update({"board/" + name: ("board", name) for name in changes["board"].VARIANTS})
    result.update({"search/" + name: ("search", name) for name in changes["search"].OPTIONS})
    result["input/decode-move"] = ("move", "decode-move")
    return result


def project(files, selected, changes):
    available = options(changes)
    if len(set(selected)) != len(selected) or any(name not in available for name in selected):
        raise ValueError("explicit nonrepeated structural selectors required")
    selected = set(selected)
    result = dict(files)
    # Board changes precede a worker-owned Board path. Runtime and move input
    # remain separately owned consumers of the unchanged Board contract.
    for group in ("board", "search", "runtime", "move"):
        names = tuple(local for key, (family, local) in available.items()
                      if family == group and key in selected)
        if not names:
            continue
        if group == "runtime":
            result["runtime.c"] = changes[group].transform(result["runtime.c"].decode(), names).encode()
        elif group == "move":
            result = changes[group].apply(result)
        else:
            result = changes[group].apply(result, names)
    return result


def context_selection(context, selector, available):
    """Compose explicit dependencies and replace incompatible representations.

    A failed singleton can still improve the current source context. This
    source search compares complete candidates; it never adds byte deltas.
    """
    if selector not in available or not set(context) <= available.keys():
        raise ValueError("known context selector required")
    selected = set(context)
    for alternatives in (("runtime/numeric-scan", "runtime/numeric-skip"),
                         ("board/ep-occupancy", "board/ep-occupancy-shared"),
                         ("board/start-image", "board/start-image-shared")):
        if selector in alternatives:
            selected.difference_update(alternatives)
    if selector == "search/board_keys":
        selected.discard("search/repetition_prefix")
        selected.add("search/board_path")
    elif selector == "search/repetition_prefix":
        selected.discard("search/board_keys")
    selected.add(selector)
    return tuple(name for name in available if name in selected)


def _save(out, report):
    (out / "portfolio.json").write_text(json.dumps(report, indent=2) + "\n")


def _observation_view(out, row, report, core):
    """Expose the actual data through the existing observation input format.

    This is not a substitute cost measurement: every identity comes from the
    repeated native/package generation and the shared settled process owner.
    """
    directory = out / row["name"]
    generation, package = row["generation"], row["package"]
    native = (directory / "attempt-0/native").read_bytes()
    actual = {key: generation["native_rebuilds"][0][key] for key in ("bytes", "sha256")}
    if core.pin(native) != actual:
        raise ValueError("observed native differs from measured candidate")
    native_dir = directory / "native"
    native_dir.mkdir()
    (native_dir / "native").write_bytes(native)
    (native_dir / "native").chmod(0o755)
    packed = (directory / core.PACKED).read_bytes()
    if core.pin(packed) != {key: package[key] for key in ("bytes", "sha256")}:
        raise ValueError("observed package differs from measured candidate")
    (directory / "packed-xz-bcj-pb0").write_bytes(packed)
    view = {"label": row["name"], "complete": True, "input": row["source"],
            "flags": generation["flags"], "profile": "test-p4", "workers": 4,
            "commands": report["commands"][row["command_begin"]:row["command_end"]],
            "host_cleanup": report["host_cleanup"],
            "native_runs": [{"linked": {key: linked[key] for key in ("bytes", "sha256")},
                             "native": {key: native[key] for key in ("bytes", "sha256")}}
                            for linked, native in zip(generation["linked_rebuilds"], generation["native_rebuilds"])],
            "reduction": generation["source_reduction"], "shipping": generation["shipping_inputs"],
            "packages": {"packed-xz-bcj-pb0": package},
            "selectors": row["selectors"], "optimization": row["optimization"],
            "engine_executed": False, "runtime_qualified": False, "selected": False,
            "origin": "actual repeated generation DATA in portfolio.json; no admission"}
    (directory / "result.json").write_text(json.dumps(view, indent=2) + "\n")


def run(out, snapshot, current_root, inputs, requested):
    owner, core, baseline, modules, control, bss, proof, bss_proof, changes = prepare(snapshot)
    available = options(changes)
    if requested and any(name not in available for name in requested):
        raise ValueError("unknown requested selector")
    selected = tuple(requested or available)
    resource = modules["source"].production().resource_profile(core.PROFILE)
    flags = modules["build"].native_flags(resource, "s")
    report = {"format": "rove4k-D-bss-structural-next-v1", "complete": False,
              "inputs": core.inventory(inputs), "source_proof": proof, "bss_proof": bss_proof,
              "commands": [], "cases": [], "candidate_failures": [],
              "resource": resource.to_record(16), "requested": list(selected),
              "scope": "finite size portfolio; no generated engine execution or production selection"}
    save = lambda: _save(out, report)
    save()
    host, body_error = None, None
    try:
        report["file_size_limit"] = owner._file_limit()
        host = core.open_generation_host(out, report, save, modules, baseline, wall_seconds=600)
        directory = out / "strict-control"
        directory.mkdir()
        fixed = core.generate_fixed_p4(control, flags, directory, modules, baseline, host)
        report["strict_control"] = fixed["record"]
        save()

        measured = {}

        def measure(name, selectors=(), optimize="s"):
            selectors = tuple(name for name in available if name in selectors)
            identity = (selectors, optimize)
            if identity in measured:
                report.setdefault("identical_source_reuse", []).append({"requested_name": name,
                    "measured_name": measured[identity]["name"], "selectors": list(selectors),
                    "optimization": optimize, "scope": "same source, flags, tools and fixed recipe in this owner"})
                save()
                return measured[identity]
            files = project(bss, selectors, changes)
            repeated = project(dict(bss), selectors, changes)
            if files != repeated:
                raise ValueError("source projection is not deterministic")
            directory = out / name
            directory.mkdir()
            begin = len(report["commands"])
            emitted = core.emit_native_generation(files, modules["build"].native_flags(resource, optimize),
                                                   directory, modules, baseline, host)
            packed = core.package_native_generation(emitted, modules, baseline)
            layout = owner.layout_data(emitted["images"][0][0], modules, baseline, core, tt_bits=23)
            row = {"name": name, "selectors": list(selectors), "optimization": optimize,
                   "source": core.inventory(files), "generation": emitted["record"],
                   "package": packed["row"], "layout": layout,
                   "command_begin": begin, "command_end": len(report["commands"]),
                   "semantic_status": "not-yet-observed", "selected": False}
            report["cases"].append(row)
            measured[identity] = row
            save()
            return row

        def attempt(name, selectors, optimize="s"):
            begin = len(report["commands"])
            try:
                return measure(name, selectors, optimize)
            except (TimeoutError, MemoryError):
                raise
            except Exception as error:
                report["candidate_failures"].append({"name": name, "selectors": list(selectors),
                    "optimization": optimize, "type": type(error).__name__, "message": str(error),
                    "command_begin": begin, "command_end": len(report["commands"])})
                save()
                return None

        base = measure("baseline")
        if ({key: base["generation"]["native_rebuilds"][0][key] for key in ("bytes", "sha256")} != core.expected(BSS_NATIVE)
                or {key: base["package"][key] for key in ("bytes", "sha256")} != core.expected(BSS_WHOLE)):
            raise ValueError("latest BSS 4689-byte comparison baseline did not reproduce")
        winners = []
        for selector in selected:
            name = selector.replace("/", "-")
            row = attempt(name, context_selection((), selector, available))
            if row is not None and row["package"]["bytes"] < base["package"]["bytes"]:
                winners.append((selector, row["package"]["bytes"]))
        if winners:
            combined = ()
            # Better singleton choices replace conflicting alternatives last.
            for selector, _ in sorted(winners, key=lambda item: -item[1]):
                combined = context_selection(combined, selector, available)
            attempt("combined", combined)
        context = min(report["cases"], key=lambda row: row["package"]["bytes"])
        report["context_search"] = {"round_limit": 2, "order": list(selected), "improvements": []}
        for round_index in range(2):
            changed = False
            for index, selector in enumerate(selected):
                trial = context_selection(context["selectors"], selector, available)
                row = attempt(f"context-{round_index}-{index}", trial)
                if row is not None and row["package"]["bytes"] < context["package"]["bytes"]:
                    report["context_search"]["improvements"].append({"before": context["name"],
                        "after": row["name"], "before_bytes": context["package"]["bytes"],
                        "after_bytes": row["package"]["bytes"]})
                    context, changed = row, True
            if not changed:
                break
        attempt("best-source-Oz", tuple(context["selectors"]), "z")
        report["minimum_measured"] = min(report["cases"], key=lambda row: row["package"]["bytes"])["name"]
        if any(owner._normalized(Path(current_root) / path) != data for path, data in inputs.items()):
            raise ValueError("source inputs changed during experiment")
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        modules["terminal"].finish_report(host, report, save, body_error)
    report["generation_complete"] = True
    try:
        for row in report["cases"]:
            _observation_view(out, row, report, core)
    except BaseException as error:
        report["complete"] = False
        report["failure"] = {"phase": "observation-inputs", "type": type(error).__name__, "message": str(error)}
        save()
        raise
    report["observation_inputs_complete"] = True
    save()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--cases", default="", help="comma-separated selectors; empty uses the finite portfolio")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("compiler/codec work is inactive without --execute")
    owner = load("D_next_capture", HERE / "structural_bss_cost.py")
    inputs = owner.capture_inputs()
    inputs.update({D + name: owner._normalized(HERE / name) for name in EXTRA})
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((parent / ".git").exists() for parent in (out, *out.parents)):
        parser.error("new absolute output outside every Git checkout required")
    out.mkdir(parents=True)
    snapshot = out / "inputs"
    for name, data in inputs.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    frozen = load("D_next_frozen_controller", snapshot / D / "structural_next.py")
    report = frozen.run(out, snapshot, ROOT, inputs, tuple(filter(None, args.cases.split(","))))
    print(json.dumps({"complete": report["complete"], "minimum_measured": report["minimum_measured"],
        "cases": [{"name": row["name"], "native": row["generation"]["native_rebuilds"][0]["bytes"],
                   "whole": row["package"]["bytes"]} for row in report["cases"]],
        "candidate_failures": report["candidate_failures"]}), flush=True)


if __name__ == "__main__":
    main()
