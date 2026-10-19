#!/usr/bin/env python3
"""Build native implementation portfolios, optionally verify and pack them.

Python 3.11+, POSIX process groups; no third-party Python packages. Project
commands are trusted build instructions, not a sandbox for untrusted code.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

VERSION = "0.3.0"
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
PLACEHOLDER = re.compile(r"\{([A-Za-z0-9][A-Za-z0-9_.-]*)\}")


class RunError(Exception):
    def __init__(self, phase, message, detail=None):
        super().__init__(message)
        self.phase, self.detail = phase, detail or {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path):
    return json.loads(path.read_text())


def named(items, label):
    if not isinstance(items, list) or not items:
        raise RunError("configuration", f"{label}: nonempty list required")
    result = {}
    for item in items:
        key = item.get("id", "")
        if not isinstance(key, str) or not IDENTIFIER.fullmatch(key) or key in result:
            raise RunError("configuration", f"{label}: invalid or duplicate id {key!r}")
        result[key] = item
    return result


def expand(argv, context):
    """Expand named placeholders in argv; an exact list placeholder splices argv.

    Braces not matching a known placeholder are literal. A manifest can avoid
    interpolation entirely for a token using {"literal": "..."}.
    """
    if not isinstance(argv, list) or not argv:
        raise RunError("configuration", "command must be a nonempty argv array")
    result = []
    for token in argv:
        if isinstance(token, dict) and set(token) == {"literal"}:
            if not isinstance(token["literal"], str):
                raise RunError("configuration", "literal argv must be a string")
            result.append(token["literal"])
            continue
        if not isinstance(token, str):
            raise RunError("configuration", "argv tokens must be strings or literal objects")
        match = PLACEHOLDER.fullmatch(token)
        if match and match[1] in context and isinstance(context[match[1]], list):
            result.extend(str(x) for x in context[match[1]])
            continue
        def replace(match):
            key = match[1]
            if key not in context:
                raise RunError("configuration", f"unknown placeholder {{{key}}}; use a literal token if intended")
            value = context[key]
            if isinstance(value, list):
                raise RunError("configuration", f"list placeholder {{{key}}} must occupy a whole token")
            return str(value)
        result.append(PLACEHOLDER.sub(replace, token))
    if not result or not result[0]:
        raise RunError("configuration", "empty executable")
    return result


def terminate_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def execute(argv, *, cwd, env, log, timeout, max_log_bytes, phase):
    """Bound direct-group wall time and captured log size without preexec_fn."""
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    out_path, err_path = log.with_suffix(".stdout"), log.with_suffix(".stderr")
    with out_path.open("wb") as out, err_path.open("wb") as err:
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, start_new_session=True)
        except OSError as exc:
            raise RunError(phase, f"could not start {argv[0]}: {exc}") from exc
        reason = None
        try:
            while proc.poll() is None:
                if time.monotonic() - started >= timeout:
                    reason = "timeout"
                    break
                if out_path.stat().st_size + err_path.stat().st_size > max_log_bytes:
                    reason = "log_limit"
                    break
                time.sleep(0.01)
        except BaseException:
            terminate_group(proc)
            raise
        if reason:
            terminate_group(proc)
        else:
            proc.wait()
            # Commands must not leave descendants in their owned process group.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if out_path.stat().st_size + err_path.stat().st_size > max_log_bytes:
            reason = reason or "log_limit"
    detail = {"argv": argv, "returncode": proc.returncode,
              "seconds": round(time.monotonic() - started, 6),
              "stdout": str(out_path), "stderr": str(err_path)}
    if reason or proc.returncode:
        detail["reason"] = reason or "nonzero_exit"
        with err_path.open("rb") as stream:
            stream.seek(max(0, err_path.stat().st_size - 4096))
            detail["stderr_tail"] = stream.read(4096).decode("utf-8", "replace")
        raise RunError(phase, reason or f"command exited {proc.returncode}", detail)
    return detail


def safe_input(root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not relative or path == Path("."):
        raise RunError("configuration", f"input must be project-relative: {relative!r}")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise RunError("configuration", f"input outside project or missing: {relative!r}")
    return resolved


def snapshot(manifest_path, destination):
    manifest = read_json(manifest_path)
    root = (manifest_path.parent / manifest.get("project_root", ".")).resolve()
    inputs = manifest.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise RunError("configuration", "declare inputs explicitly, including headers/scripts/linker files")
    hashes = {}
    destination.mkdir()
    for relative in inputs:
        if not isinstance(relative, str):
            raise RunError("configuration", "input paths must be strings")
        source = safe_input(root, relative)
        data = source.read_bytes()
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(source.stat().st_mode & 0o777)
        hashes[relative] = sha(data)
    manifest["project_root"] = "."
    return manifest, hashes


def check_snapshot(source, expected):
    for relative, digest in expected.items():
        if sha(safe_input(source, relative).read_bytes()) != digest:
            raise RunError("inputs", f"declared input changed: {relative}")


def failure_status(exc):
    return "incomplete" if exc.phase == "budget" or exc.detail.get("reason") in ("timeout", "log_limit") else "failed"


def tool_overrides(values):
    result = {}
    for value in values:
        name, sep, path = value.partition("=")
        if not sep or not name or not path:
            raise RunError("configuration", "--tool requires NAME=EXECUTABLE")
        result[name] = path
    return result


def selected_tools(manifest, selection, resolved_tools=None, *, include_verification=True):
    """Declared tool closure for one recipe, including explicit script dependencies."""
    tools = manifest.get("tools", {})
    build = named(manifest["build_profiles"], "build_profiles")[selection["build"]]
    link = named(manifest["link_profiles"], "link_profiles")[selection["link"]]
    specs = [build, link, *link.get("common", [])]
    components = named(manifest["components"], "components")
    for component, variant in selection["variants"].items():
        specs.append(named(components[component]["variants"], "variants")[variant])
    required = set(manifest.get("verify_requires_tools", [])) if include_verification else set()
    executables = resolved_tools or {name: spec["executable"] for name, spec in tools.items()}
    context = dict(executables)
    context.update(build.get("variables", {}))
    context.update(root="/declared-inputs", build="/declared-build", source="/declared-source",
                   sources=[], object="/declared-object", objects=[], binary="/declared-binary")
    commands = [link["argv"], *link.get("post_link", [])]
    if include_verification:
        if not manifest.get("verify"):
            raise RunError("configuration", "--verify requires a verify command in the manifest")
        commands.extend([manifest["verify"], manifest.get("verify_final", manifest["verify"])])
    for spec in specs:
        required.update(spec.get("requires_tools", []))
        commands.extend(spec.get("commands", []))
    for command in commands:
        for token in command:
            if isinstance(token, str):
                required.update(m[1] for m in PLACEHOLDER.finditer(token) if m[1] in tools)
        first = expand([command[0]], context)[0]
        for name, executable in executables.items():
            aliases = {executable, tools[name]["executable"]}
            if first in aliases:
                required.add(name)
    pending = list(required)
    while pending:
        name = pending.pop()
        if name not in tools:
            raise RunError("configuration", f"unknown required tool: {name}")
        for dependency in tools[name].get("requires_tools", []):
            if dependency not in required:
                required.add(dependency)
                pending.append(dependency)
    return required


def notation_options(spec):
    """Validate one explicit source-spelling contract using its owning module."""
    if "notation" not in spec:
        return None
    from nvnotation import generate_variants as notation_variants, NotationError
    options = spec["notation"]
    allowed = {"language", "target", "token_contract", "compact", "max_variants"}
    if not isinstance(options, dict) or set(options) - allowed or "language" not in options:
        raise RunError("configuration", "notation needs language and only target/token_contract/compact/max_variants options")
    sources = spec.get("sources")
    if not isinstance(sources, list) or not sources or not all(isinstance(p, str) for p in sources):
        raise RunError("configuration", "notation requires nonempty same-language sources")
    if len({str(Path(p)) for p in sources}) != len(sources):
        raise RunError("configuration", "notation sources must not repeat the same path")
    try:
        notation_variants(b"", **options)
    except (NotationError, TypeError) as exc:
        raise RunError("configuration", f"notation: {exc}") from exc
    return dict(options)


class Campaign:
    def __init__(self, manifest, source, out, args, expected_tools=None, *,
                 packing="portfolio", verification=True, additional_tools=()):
        self.m, self.source, self.out, self.args = manifest, source, out, args
        if packing not in ("portfolio", "none"):
            raise RunError("configuration", "packing must be portfolio or none")
        if packing == "portfolio" and not verification:
            raise RunError("configuration", "the packing portfolio requires execution verification")
        self.packing, self.verification = packing, verification
        self.components = named(manifest.get("components"), "components")
        self.builds = named(manifest.get("build_profiles"), "build_profiles")
        self.links = named(manifest.get("link_profiles"), "link_profiles")
        for link in self.links.values():
            if type(link.get("allow_section_header_removal", False)) is not bool:
                raise RunError("configuration", "allow_section_header_removal must be a JSON boolean")
            if link.get("common"):
                named(link["common"], "common units")
                for unit in link["common"]:
                    if packing == "portfolio":
                        notation_options(unit)
        for component in self.components.values():
            named(component.get("variants"), "variants")
            if not component.get("contract"):
                raise RunError("configuration", "each component needs a semantic/ABI contract")
            for unit in component["variants"]:
                if packing == "portfolio":
                    notation_options(unit)
        self.orders = manifest.get("orders", [{"id": "declared", "components": list(self.components)}])
        named(self.orders, "orders")
        for order in self.orders:
            if sorted(order.get("components", [])) != sorted(self.components):
                raise RunError("configuration", "each order must contain each component exactly once")
        if not isinstance(manifest.get("target"), str) or not manifest["target"].strip():
            raise RunError("configuration", "an explicit target is required")
        if verification and not manifest.get("verify"):
            raise RunError("configuration", "execution verification requires a verify command")
        self.deadline = time.monotonic() + args.max_seconds
        self.tools, self.tool_info = {}, {}
        overrides = tool_overrides(args.tool)
        all_tools = manifest.get("tools", {})
        for name in all_tools:
            if not isinstance(name, str) or not IDENTIFIER.fullmatch(name):
                raise RunError("configuration", f"invalid tool alias: {name!r}")
        if expected_tools is not None:
            active_names = set(expected_tools) | set(additional_tools)
        elif packing == "none":
            # A compile-only build must not need a missing engine runtime or
            # checker that is outside its selected build-command closure.
            _, selections = self.candidates()
            if verification and manifest.get("baseline"):
                selections.append(manifest["baseline"])
            active_names = set()
            for selection in selections:
                self.validate_recipe(selection)
                active_names.update(selected_tools(manifest, selection,
                                                    include_verification=verification))
        else:
            active_names = set(all_tools)
        if active_names - set(all_tools):
            raise RunError("configuration", f"unknown required tools: {sorted(active_names - set(all_tools))}")
        active_tools = {name: spec for name, spec in all_tools.items() if name in active_names}
        for name, spec in active_tools.items():
            executable = overrides.get(name, spec["executable"])
            found = shutil.which(executable)
            if not found:
                raise RunError("tool", f"missing {name}: {executable}; provide --tool {name}=PATH")
            # Keep symlink invocation paths: some compiler drivers inspect argv[0].
            found = str(Path(found).absolute())
            self.tools[name] = found
            self.tool_info[name] = {"executable": found, "sha256": sha(Path(found).read_bytes())}
        unknown = set(overrides) - set(all_tools)
        if unknown:
            raise RunError("configuration", f"unknown tool aliases: {sorted(unknown)}")
        path_dirs = list(dict.fromkeys(str(Path(p).parent) for p in self.tools.values()))
        # PATH is explicit in evidence; CPATH/RUSTFLAGS/LD_PRELOAD/etc are not inherited.
        path_dirs += ["/usr/bin", "/bin"]
        self.env = {"PATH": os.pathsep.join(path_dirs), "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
                    "SOURCE_DATE_EPOCH": "0", "PYTHONHASHSEED": "0", "PYTHONCOERCECLOCALE": "0"}
        for key, value in manifest.get("environment", {}).items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise RunError("configuration", "environment entries must be literal strings")
            self.env[key] = value
        for name, spec in active_tools.items():
            log = out / "tools" / name / "version"
            self.command([self.tools[name], *spec.get("version_args", ["--version"])],
                         out, log, "tool")
            self.tool_info[name]["version"] = log.with_suffix(".stdout").read_text(errors="replace").strip()
        if expected_tools is not None:
            for name, old in expected_tools.items():
                current = self.tool_info.get(name)
                if not current or current["sha256"] != old["sha256"] or current["version"] != old["version"]:
                    raise RunError("reproduce", f"tool contents/version differ: {name}")
        self.units = {}
        self.units_lock = threading.Lock()
        self.max_file = int(manifest.get("max_native_bytes", 64 * 1024 * 1024))
        self.audit_notation = expected_tools is None and packing == "portfolio"
        self.source_hashes = {str(safe_input(source, relative).relative_to(source.resolve())):
                              sha(safe_input(source, relative).read_bytes())
                              for relative in manifest.get("inputs", [])}

    def command(self, argv, cwd, log, phase):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise RunError("budget", "campaign time budget reached")
        return execute(argv, cwd=cwd, env=self.env, log=log,
                       timeout=min(self.args.command_seconds, remaining),
                       max_log_bytes=self.args.max_log_bytes, phase=phase)

    def context(self, build_id, work, **extra):
        context = dict(self.tools)
        context.update(self.builds[build_id].get("variables", {}))
        context.update(root=str(self.source), build=str(work))
        context.update(extra)
        return context

    def notation(self, build_id, key, spec, work, original_object):
        """Audit spelling candidates before linking; link the original object.

        A complete matching object is the boundary that allows a source spelling
        to be locked independently of later link choices. This is not the source
        payload packing portfolio: longer source may still compress better there.
        """
        options = notation_options(spec)
        if options is None:
            return None
        from nvnotation import generate_variants as notation_variants, NotationError
        if not self.audit_notation:
            return {"status": "not_repeated_for_native_reproduction",
                    "linked_object": "original", "reason": "notation candidates do not replace the linked object"}
        if not self.source_hashes:
            raise RunError("configuration", "notation needs declared snapshot inputs for isolated source overlays")
        check_snapshot(self.source, self.source_hashes)
        sources = [str(safe_input(self.source, p).relative_to(self.source.resolve())) for p in spec["sources"]]
        original_sources = {p: safe_input(self.source, p).read_bytes() for p in sources}
        original_bytes = original_object.read_bytes()
        original_hash = sha(original_bytes)
        original_record = {"id": "raw", "status": "baseline", "eligible": True,
                           "source_bytes": sum(map(len, original_sources.values())),
                           "source_sha256": {p: sha(data) for p, data in original_sources.items()},
                           "object_sha256": original_hash, "object_bytes": len(original_bytes)}
        audit = {"status": "completed", "search_complete": True, "linked_object": "original",
                 "contract": options, "selection_basis": "minimum source bytes among complete byte-identical objects",
                 "original_source_bytes": original_record["source_bytes"],
                 "original_object_sha256": original_hash, "source_bytes_saved": 0, "candidates": [original_record],
                 "selected": dict(original_record)}
        destination = work / "notation"
        destination.mkdir()
        try:
            variants = {p: {v["id"]: v for v in notation_variants(data, **options)}
                        for p, data in original_sources.items()}
        except NotationError as exc:
            audit.update(status="generation_failed", search_complete=False, error=str(exc))
            write_json(destination / "audit.json", audit)
            return audit
        ids = list(next(iter(variants.values())))
        audit["planned_source_recipes"] = len(ids)
        if any(list(group) != ids for group in variants.values()):
            raise RunError("notation", "source recipe IDs differ within a same-language unit")
        for identifier in ids:
            if identifier == "raw":
                continue
            row = {"id": identifier, "eligible": False,
                   "source_bytes": sum(len(group[identifier]["data"]) for group in variants.values()),
                   "source_sha256": {p: group[identifier]["sha256"] for p, group in variants.items()},
                   "rewrites": {p: group[identifier]["audit"] for p, group in variants.items()},
                   "notes": {p: group[identifier]["notes"] for p, group in variants.items()}}
            audit["candidates"].append(row)
            if all(group[identifier]["data"] == original_sources[p] for p, group in variants.items()):
                row.update(status="source_identical", reason="same source bytes as raw; no source reduction to lock")
                continue
            if time.monotonic() >= self.deadline:
                row.update(status="incomplete", reason="campaign budget reached before notation compilation")
                audit.update(status="incomplete", search_complete=False)
                break
            candidate = destination / identifier
            overlay, build = candidate / "root", candidate / "build"
            overlay.mkdir(parents=True)
            build.mkdir()
            check_snapshot(self.source, self.source_hashes)
            for relative in self.source_hashes:
                original = safe_input(self.source, relative)
                target = overlay / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, target)
                target.chmod(original.stat().st_mode & 0o777)
            overlay_hashes = dict(self.source_hashes)
            for relative, group in variants.items():
                target = safe_input(overlay, relative)
                mode = target.stat().st_mode & 0o777
                target.chmod(mode | 0o200)
                target.write_bytes(group[identifier]["data"])
                target.chmod(mode)
                overlay_hashes[relative] = group[identifier]["sha256"]
            obj = build / "unit.o"
            candidate_sources = [str(safe_input(overlay, p)) for p in sources]
            context = self.context(build_id, build, root=str(overlay), object=str(obj),
                                   sources=candidate_sources, source=candidate_sources[0], unit_id="/".join(key))
            row["overlay"] = str(overlay.relative_to(self.out))
            row["commands"] = []
            try:
                for index, command in enumerate(spec["commands"]):
                    row["commands"].append(self.command(expand(command, context), build,
                                                       build / f"compile-{index}", "notation_compile"))
                check_snapshot(overlay, overlay_hashes)
                if obj.is_symlink() or not obj.is_file() or obj.stat().st_size > self.max_file:
                    raise RunError("notation_compile", "missing, symlink or oversized candidate object")
                data = obj.read_bytes()
                row.update(object_bytes=len(data), object_sha256=sha(data))
                if data == original_bytes:
                    row.update(status="object_byte_identical", eligible=True)
                else:
                    row.update(status="rejected_object_difference",
                               reason="complete object bytes differ; source length cannot authorize replacement")
            except RunError as exc:
                row.update(status=failure_status(exc), phase=exc.phase, error=str(exc), detail=exc.detail)
                if row["status"] == "incomplete":
                    audit.update(status="incomplete", search_complete=False)
            # Do not hide a build command that escaped its overlay or mutated
            # the original linked artifact, even if its own comparison failed.
            check_snapshot(self.source, self.source_hashes)
            if original_object.read_bytes() != original_bytes:
                raise RunError("notation", "candidate build modified the original object")
        eligible = [r for r in audit["candidates"] if r["eligible"]]
        chosen = min(eligible, key=lambda r: (r["source_bytes"], r["id"] != "raw", r["id"]))
        audit["selected"] = {k: v for k, v in chosen.items() if k not in ("commands", "rewrites", "notes")}
        audit["source_bytes_saved"] = original_record["source_bytes"] - chosen["source_bytes"]
        write_json(destination / "audit.json", audit)
        return audit

    def unit(self, build_id, key, spec):
        cache_key = (build_id, key)
        with self.units_lock:
            if cache_key not in self.units:
                self.units[cache_key] = concurrent.futures.Future()
                owner = True
            else:
                owner = False
            future = self.units[cache_key]
        if not owner:
            return future.result()
        try:
            work = self.out / "objects" / build_id
            for part in key:
                work = work / part
            work.mkdir(parents=True)
            obj = work / "unit.o"
            sources = [str(safe_input(self.source, p)) for p in spec.get("sources", [])]
            context = self.context(build_id, work, object=str(obj), sources=sources,
                                   source=sources[0] if sources else "", unit_id="/".join(key))
            commands = spec.get("commands", [])
            if not commands:
                raise RunError("configuration", f"unit {key}: commands required")
            for index, command in enumerate(commands):
                self.command(expand(command, context), work, work / f"compile-{index}", "compile")
            if not obj.is_file() or obj.stat().st_size > self.max_file:
                raise RunError("compile", f"missing or oversized output: {key}")
            value = {"path": obj, "unit_id": "/".join(key), "sha256": sha(obj.read_bytes()), "bytes": obj.stat().st_size}
            notation = self.notation(build_id, key, spec, work, obj) if self.packing == "portfolio" else None
            if notation is not None:
                value["notation"] = notation
            future.set_result(value)
            return value
        except BaseException as exc:
            future.set_exception(exc)
            raise

    def native(self, recipe, work):
        self.validate_recipe(recipe)
        build_id, link_id = recipe["build"], recipe["link"]
        link = self.links[link_id]
        objects = []
        for unit in link.get("common", []):
            if not IDENTIFIER.fullmatch(unit.get("id", "")):
                raise RunError("configuration", "common unit needs a valid id")
            objects.append(self.unit(build_id, ("common", link_id, unit["id"]), unit))
        for component_id in recipe["order"]:
            variant_id = recipe["variants"][component_id]
            variant = named(self.components[component_id]["variants"], "variants")[variant_id]
            objects.append(self.unit(build_id, ("variant", component_id, variant_id), variant))
        work.mkdir(parents=True, exist_ok=True)
        binary = work / "native"
        context = self.context(build_id, work, objects=[str(x["path"]) for x in objects], binary=str(binary))
        self.command(expand(link["argv"], context), work, work / "link", "link")
        for index, command in enumerate(link.get("post_link", [])):
            self.command(expand(command, context), work, work / f"post-{index}", "post_link")
        if not binary.is_file() or not 0 < binary.stat().st_size <= self.max_file:
            raise RunError("link", "missing, empty or oversized native executable")
        binary.chmod(0o755)
        return binary, [{k: v for k, v in x.items() if k != "path"} for x in objects]

    def validate_recipe(self, recipe):
        if recipe.get("build") not in self.builds or recipe.get("link") not in self.links:
            raise RunError("configuration", "recipe references an unknown build/link profile")
        if sorted(recipe.get("order", [])) != sorted(self.components):
            raise RunError("configuration", "recipe order must contain each component exactly once")
        if set(recipe.get("variants", {})) != set(self.components):
            raise RunError("configuration", "recipe must select one variant for every component")
        for key, variant in recipe["variants"].items():
            if variant not in named(self.components[key]["variants"], "variants"):
                raise RunError("configuration", f"unknown variant for {key}: {variant}")

    def verify(self, binary, work, final=False):
        if not self.verification:
            return {"status": "not_run", "reason": "native execution verification requires --verify"}
        command = self.m.get("verify_final", self.m["verify"]) if final else self.m["verify"]
        context = dict(self.tools, root=str(self.source), binary=str(binary), build=str(work))
        log = work / ("verify-final" if final else "verify")
        before = binary.read_bytes()
        result = self.command(expand(command, context), work, log, "verify_final" if final else "verify")
        if binary.read_bytes() != before:
            raise RunError("verify", "checker modified the candidate artifact")
        output = log.with_suffix(".stdout").read_bytes()[:16384].decode("utf-8", "replace")
        try:
            result["checker_output"] = json.loads(output)
        except ValueError:
            result["checker_output"] = output
        return result

    def baseline(self):
        recipe = self.m.get("baseline")
        if not recipe:
            raise RunError("configuration", "an explicit baseline recipe is required")
        work = self.out / "baseline"
        binary, _ = self.native(recipe, work)
        result = self.verify(binary, work, final=True)
        return {"recipe": recipe, "sha256": sha(binary.read_bytes()), "bytes": binary.stat().st_size,
                "verification": result}

    def candidates(self):
        build_ids = self.args.profile or list(self.builds)
        link_ids = self.args.link_profile or list(self.links)
        if set(build_ids) - set(self.builds) or set(link_ids) - set(self.links):
            raise RunError("configuration", "unknown build/link profile filter")
        components = list(self.components)
        variants = [list(named(self.components[key]["variants"], "variants")) for key in components]
        total = len(build_ids) * len(link_ids) * len(self.orders) * math.prod(map(len, variants))
        selected = []
        for combination in itertools.islice(
                itertools.product(build_ids, link_ids, self.orders, *variants),
                self.args.max_candidates):
            build, link, order, *choices = combination
            selected.append({"build": build, "link": link, "order_id": order["id"],
                             "order": order["components"], "variants": dict(zip(components, choices))})
        return total, selected

    def evaluate(self, index, recipe):
        candidate_id = f"c{index:05d}"
        work = self.out / "candidates" / candidate_id
        result = {"id": candidate_id, "recipe": recipe, "artifacts": []}
        try:
            binary, objects = self.native(recipe, work)
            native_data = binary.read_bytes()
            result.update(native_bytes=len(native_data), native_sha256=sha(native_data), objects=objects)
            result["native_verification"] = self.verify(binary, work)
            if self.packing == "none":
                # Preserve the declared compile/link/post_link output bytes.
                # There is no ELF deployment rewrite, loader or codec here.
                limit = getattr(self.args, "max_bytes", None)
                status = "screened" if self.verification else "built"
                if limit is not None and len(native_data) > limit:
                    status = "over_size_limit"
                result["artifacts"].append({
                    "id": "linked", "artifact_kind": "linked", "deployment": "linked", "pack": "none",
                    "bytes": len(native_data), "sha256": sha(native_data),
                    "requirements": {"profile": "declared-native-build", "target": self.m["target"]},
                    "codec_roundtrip": None, "artifact": str(binary.relative_to(self.out)),
                    "verification": result["native_verification"], "status": status,
                    "reproduction": "not_run"})
                result["status"] = "completed"
                return result
            from nvpack import candidate_ids, pack_by_id
            from nvelf import deployment_variants
            link = self.links[recipe["link"]]
            transformed = deployment_variants(native_data,
                allow_section_header_removal=link.get("allow_section_header_removal", False))
            for deployment in transformed:
                for codec_id in candidate_ids(self.m["target"], self.m.get("codecs")):
                    if time.monotonic() >= self.deadline:
                        raise RunError("budget", "campaign budget reached between packing recipes")
                    packed = pack_by_id(deployment["data"], target=self.m["target"], pack_id=codec_id)
                    pack_id = deployment["id"] + "__" + packed["id"]
                    pack_work = work / pack_id
                    pack_work.mkdir()
                    path = pack_work / "artifact"
                    path.write_bytes(packed["data"])
                    path.chmod(0o755)
                    row = {"id": pack_id, "deployment": deployment["id"], "pack": packed["id"],
                           "bytes": len(packed["data"]), "sha256": sha(packed["data"]),
                           "payload_bytes": packed["payload_bytes"],
                           "requirements": packed["requirements"],
                           "codec_roundtrip": packed["roundtrip_verified"],
                           "artifact": str(path.relative_to(self.out)), "reproduction": "not_run"}
                    try:
                        row["verification"] = self.verify(path, pack_work)
                        limit = self.m.get("max_bytes")
                        row["status"] = "screened" if limit is None or row["bytes"] <= limit else "over_size_limit"
                    except RunError as exc:
                        row.update(status=failure_status(exc), phase=exc.phase, error=str(exc), detail=exc.detail)
                    result["artifacts"].append(row)
            result["status"] = "completed"
        except RunError as exc:
            result.update(status=failure_status(exc),
                          phase=exc.phase, error=str(exc), detail=exc.detail)
        except Exception as exc:
            result.update(status="internal_error", phase="tool", error=f"{type(exc).__name__}: {exc}")
        return result


def runtime_fingerprint(packing="portfolio"):
    if packing not in ("portfolio", "none"):
        raise RunError("configuration", "unknown recipe packing mode")
    root = Path(__file__).resolve().parent
    sources = ["nvcompact.py"]
    system = os.uname()
    result = {"version": VERSION, "python": platform.python_version(),
              # platform.platform() may spawn an unbudgeted `uname -p` probe.
              # This field is descriptive, so obtain it directly from the OS.
              "platform": f"{system.sysname}-{system.release}-{system.machine}", "packing": packing}
    if packing == "portfolio":
        import zlib
        result["zlib"] = zlib.ZLIB_RUNTIME_VERSION
        sources += ["nvpack.py", "nvelf.py", "nvnotation.py"]
    result["source_sha256"] = {name: sha((root / name).read_bytes()) for name in sources}
    return result


def check_runtime(expected):
    packing = expected.get("packing", "portfolio")
    actual = runtime_fingerprint(packing)
    keys = ("version", "python", "source_sha256")
    if packing == "portfolio":
        keys += ("zlib",)
    for key in keys:
        if actual[key] != expected[key]:
            raise RunError("reproduce", f"runner/Python/compressor fingerprint differs: {key}")
    # Kernel/platform description is evidence, not an equality gate. Actual
    # rebuilt bytes and target execution still have to match the contract.
    return actual


def new_output(value):
    path = Path(value).absolute()
    if path.exists() or path.is_symlink():
        raise RunError("configuration", f"output must be a new owned directory: {path}")
    path.mkdir(parents=True)
    return path.resolve()


def regenerate(recipe, source, out, args):
    # No candidate search or compiled-object reuse in reproduction.
    manifest = recipe["project"]
    check_snapshot(source, recipe["inputs"])
    packing = recipe.get("packing", "portfolio")
    if packing != recipe["runtime"].get("packing", "portfolio"):
        raise RunError("reproduce", "recipe and runtime packing modes disagree")
    verification = packing != "none" or bool(getattr(args, "verify", False))
    expected_tools = recipe["tools"]
    additional_tools = set()
    if packing == "none":
        if recipe.get("pack") != "none" or recipe.get("deployment") != "linked":
            raise RunError("reproduce", "a native recipe must select linked bytes and packing none")
        declared = {name: spec["executable"] for name, spec in manifest.get("tools", {}).items()}
        declared.update({name: spec["executable"] for name, spec in expected_tools.items()})
        build_tools = selected_tools(manifest, recipe["selection"], declared, include_verification=False)
        if build_tools - set(expected_tools):
            raise RunError("reproduce", "native recipe is missing recorded build-tool fingerprints")
        required = selected_tools(manifest, recipe["selection"], declared,
                                  include_verification=verification)
        # A later --verify may first introduce checker-only dependencies. They
        # are observed now; the recorded actual build tools remain pinned.
        additional_tools = required - set(expected_tools)
        expected_tools = {name: spec for name, spec in expected_tools.items() if name in required}
    campaign = Campaign(manifest, source, out, args, expected_tools=expected_tools,
                        packing=packing, verification=verification, additional_tools=additional_tools)
    work = out / "selected"
    native, _ = campaign.native(recipe["selection"], work)
    data = native.read_bytes()
    if packing == "none":
        path, final_data = native, data
    else:
        from nvpack import pack_by_id
        from nvelf import deployment_variants
        link = campaign.links[recipe["selection"]["link"]]
        deployments = deployment_variants(data,
            allow_section_header_removal=link.get("allow_section_header_removal", False))
        deployment = next((v for v in deployments if v["id"] == recipe["deployment"]), None)
        if deployment is None:
            raise RunError("reproduce", "selected deployment is no longer available")
        packed = pack_by_id(deployment["data"], target=manifest["target"], pack_id=recipe["pack"])
        final_data = packed["data"]
        path = work / "artifact"
        path.write_bytes(final_data)
        path.chmod(0o755)
    check = campaign.verify(path, work, final=True)
    if packing == "none":
        check["observed_tools"] = campaign.tool_info
    check_snapshot(source, recipe["inputs"])
    if sha(data) != recipe["native_sha256"] or sha(final_data) != recipe["artifact_sha256"]:
        raise RunError("reproduce", "rebuilt native/final bytes differ from selected recipe")
    return path, check


def run(args):
    out = new_output(args.out)
    packing = "none" if args.command == "build" else "portfolio"
    verification = packing != "none" or bool(getattr(args, "verify", False))
    report = {"format": 1, "status": "running", "packing": packing,
              "verification_requested": verification,
              "runtime": runtime_fingerprint(packing), "candidates": []}
    try:
        manifest, inputs = snapshot(Path(args.manifest).resolve(), out / "snapshot")
        write_json(out / "project.json", manifest)
        campaign = Campaign(manifest, out / "snapshot", out, args,
                            packing=packing, verification=verification)
        report.update(target=manifest["target"], input_sha256=inputs, tools=campaign.tool_info,
                      environment=campaign.env,
                      limits={"jobs": args.jobs, "command_seconds": args.command_seconds,
                              "max_seconds": args.max_seconds, "max_candidates": args.max_candidates,
                              "max_bytes": getattr(args, "max_bytes", None) if packing == "none"
                                           else manifest.get("max_bytes")})
        if verification:
            print("Checking the explicit baseline with the final checker...", flush=True)
            report["baseline"] = campaign.baseline()
        else:
            report["baseline"] = {"status": "not_run", "reason": "compile/link-only build"}
        total, candidates = campaign.candidates()
        report.update(planned_link_candidates=total, selected_link_candidates=len(candidates))
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = {pool.submit(campaign.evaluate, i, recipe): i for i, recipe in enumerate(candidates)}
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                report["candidates"].append(row)
                screened = sum(p["status"] == "screened" for p in row["artifacts"])
                built = sum(p["status"] == "built" for p in row["artifacts"])
                description = f"{screened} screened complete files" if verification else f"{built} linked files; checks not run"
                print(f"{row['id']} {row['status']}: {description}", flush=True)
        report["candidates"].sort(key=lambda c: c["id"])
        qualified = [(p["bytes"], row["id"], p["id"], row, p)
                     for row in report["candidates"] if row["status"] in ("completed", "incomplete")
                     for p in row["artifacts"] if p["status"] == ("screened" if verification else "built")]
        report["search_complete"] = len(candidates) == total and all(
            c["status"] == "completed" and all(a["status"] != "incomplete" for a in c["artifacts"])
            for c in report["candidates"])
        report["screened_complete_files"] = len(qualified) if verification else 0
        report["eligible_complete_files"] = len(qualified)
        if not qualified:
            qualifier = "checked" if verification else "linked"
            raise RunError("selection", f"no completed {qualifier} artifact meets the applicable size limit")
        _, _, _, candidate, artifact = min(qualified, key=lambda x: x[:3])
        check_snapshot(out / "snapshot", inputs)
        required_tools = selected_tools(manifest, candidate["recipe"], campaign.tools,
                                        include_verification=verification)
        recipe = {"format": 1, "snapshot": "snapshot", "inputs": inputs, "project": manifest,
                  "packing": packing, "verification": "passed" if verification else "not_run",
                  "runtime": report["runtime"],
                  "tools": {name: info for name, info in campaign.tool_info.items() if name in required_tools},
                  "selection": candidate["recipe"], "deployment": artifact["deployment"], "pack": artifact["pack"],
                  "native_sha256": candidate["native_sha256"], "artifact_sha256": artifact["sha256"],
                  "artifact_bytes": artifact["bytes"], "requirements": artifact["requirements"]}
        recipe["notation"] = [{"unit_id": obj["unit_id"], "linked_object": "original",
                                "selected": obj["notation"]["selected"],
                                "search_complete": obj["notation"]["search_complete"]}
                               for obj in candidate["objects"] if "notation" in obj]
        # Rebuild from another copied source path, without object/cache reuse.
        reproduction = out / "reproduction"
        reproduction.mkdir()
        source = reproduction / "snapshot"
        shutil.copytree(out / "snapshot", source)
        print("Rebuilding the selected recipe in a fresh directory" +
              (" and running its final checker..." if verification else "; execution checks are not requested..."), flush=True)
        rebuilt, check = regenerate(recipe, source, reproduction, args)
        selected = out / artifact["artifact"]
        if rebuilt.read_bytes() != selected.read_bytes():
            raise RunError("reproduce", "fresh rebuilt file is not byte-identical")
        check_snapshot(out / "snapshot", inputs)
        winner = out / "winner"
        shutil.copyfile(selected, winner)
        winner.chmod(0o755)
        artifact["reproduction"] = "byte_identical_fresh_build"
        report.update(status="accepted" if verification else "built", winner={"candidate": candidate["id"], **artifact},
                      final_verification=check)
        write_json(out / "winner.recipe.json", recipe)
        outcome = "Accepted" if verification else "Built without packing or execution checks:"
        print(f"{outcome} {artifact['bytes']} bytes: {candidate['id']} / {artifact['id']}", flush=True)
    except RunError as exc:
        report.update(status="failed", phase=exc.phase, error=str(exc), detail=exc.detail)
        print(f"{exc.phase}: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        report.update(status="interrupted")
    except Exception as exc:
        report.update(status="internal_error", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        write_json(out / "report.json", report)
    return 0 if report["status"] in ("accepted", "built") else 2


def reproduce(args):
    original = Path(args.recipe).resolve()
    recipe = read_json(original)
    actual_runtime = check_runtime(recipe["runtime"])
    source = (original.parent / recipe["snapshot"]).resolve()
    if not source.is_relative_to(original.parent):
        raise RunError("reproduce", "snapshot must be inside the recipe directory")
    check_snapshot(source, recipe["inputs"])
    out = new_output(args.out)
    copied = out / "snapshot"
    shutil.copytree(source, copied)
    try:
        result, check = regenerate(recipe, copied, out, args)
        shutil.copyfile(result, out / "winner")
        (out / "winner").chmod(0o755)
        write_json(out / "reproduction.json", {"status": "byte_identical", "sha256": sha(result.read_bytes()),
                                               "bytes": result.stat().st_size, "verification": check,
                                               "packing": recipe.get("packing", "portfolio"),
                                               "observed_runtime": actual_runtime})
        qualifier = " (execution checks not run)" if check.get("status") == "not_run" else ""
        print(f"Byte-identical reproduction{qualifier}: {result.stat().st_size} bytes")
        return 0
    except RunError as exc:
        write_json(out / "reproduction.json", {"status": "failed", "phase": exc.phase,
                                               "error": str(exc), "detail": exc.detail})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="build and compare a declared candidate portfolio")
    build_parser = commands.add_parser("build", help="compile/link only; no packing or automatic execution checks")
    for sub in (run_parser, build_parser):
        sub.add_argument("manifest")
        sub.add_argument("--jobs", type=int, default=2)
        sub.add_argument("--max-candidates", type=int, default=128)
        sub.add_argument("--profile", action="append")
        sub.add_argument("--link-profile", action="append")
    build_parser.add_argument("--verify", action="store_true", help="explicitly run the declared baseline and artifact checkers")
    build_parser.add_argument("--max-bytes", type=int, help="optional raw linked-file size limit; manifest.max_bytes is for run")
    repro_parser = commands.add_parser("reproduce", help="rebuild one selected recipe; no candidate search")
    repro_parser.add_argument("recipe")
    repro_parser.add_argument("--verify", action="store_true", help="explicitly run a native recipe's checker; packed recipes always check")
    for sub in (run_parser, build_parser, repro_parser):
        sub.add_argument("--out", required=True)
        sub.add_argument("--tool", action="append", default=[], metavar="NAME=EXECUTABLE")
        sub.add_argument("--max-seconds", type=float, default=600,
                         help="wall-time budget for search and, separately, fresh reproduction")
        sub.add_argument("--command-seconds", type=float, default=30)
        sub.add_argument("--max-log-bytes", type=int, default=1024 * 1024)
    args = parser.parse_args(argv)
    numeric = [args.max_seconds, args.command_seconds, args.max_log_bytes]
    if args.command in ("run", "build"):
        numeric += [args.jobs, args.max_candidates]
    if args.command == "build" and args.max_bytes is not None:
        numeric.append(args.max_bytes)
    if any(not math.isfinite(v) or v <= 0 for v in numeric):
        parser.error("budgets and worker counts must be positive finite values")
    try:
        return reproduce(args) if args.command == "reproduce" else run(args)
    except (RunError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
