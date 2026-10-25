"""Transport an owned, settled Ubuntu24 source artifact to its exact old root.

The target-runtime module owns source/context/seal admission. This module only
collects ordinary owned files, writes a deterministic ZIP, and safely restores
the validated transport layout. It never compiles or executes an engine.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import stat
import sys
import zipfile

sys.dont_write_bytecode = True
_EXECUTING_CODE = sys._getframe().f_code
ROOT = Path(__file__).resolve().parents[2]
PREFIX = "artifact"
BUNDLE = "source-bundle.zip"
SEAL = "source-seal.json"


def require(value, message):
    if not value:
        raise ValueError(message)


def _source_identity(target):
    data = _read(Path(__file__), target).replace(b"\r\n", b"\n")
    require(compile(data, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "source transport changed after its executing module was compiled")
    return data


def _sources(target):
    reader = target.input_reader()
    inputs = reader.source_identity()
    own = _source_identity(target)
    authority = _read(Path(target.__file__), target).replace(b"\r\n", b"\n")
    require(compile(authority, target.__file__, "exec", dont_inherit=True) == target._EXECUTING_CODE,
            "source seal authority changed after its executing module was compiled")
    return own, authority, inputs


def _path(value, *, existing=False, directory=False):
    path = Path(value)
    require(path.is_absolute() and ".." not in path.parts and
            not any(p.is_symlink() for p in (path, *path.parents)), "absolute non-link transport path required")
    require(path.resolve() == path, "original normalized transport path required")
    if existing:
        require(path.is_dir() if directory else path.is_file(), "existing ordinary transport path required")
    return path


def _outside_checkout(path):
    require(ROOT not in (path, *path.parents) and
            not any((p / ".git").exists() for p in (path, *path.parents)),
            "transport output must remain outside every Git checkout")


def _owned_roots(source_out, build, runner_temp, *, new=False):
    runner = _path(runner_temp, existing=True, directory=True)
    out = _path(source_out, existing=not new, directory=True)
    artifact = _path(build, existing=not new, directory=True)
    require(out != runner and out.is_relative_to(runner) and artifact == out / PREFIX,
            "one explicit artifact child of the owned RUNNER_TEMP output is required")
    _outside_checkout(out)
    require(not new or not out.exists(), "exact original source output root must be new before restore")
    return runner, out, artifact


def _live_context(target, expected):
    live = target.CIContext.from_environment()
    context = target._ci(expected)
    require(live.to_record() == context, "live workflow context changed or differs from its source context")
    return context


def _safe_member(target, name):
    target._member(name)
    parts = name.split("/")
    require(len(parts) <= 64 and len(name.encode("utf-8")) <= 4096
            and all(len(part.encode("utf-8")) <= 255 for part in parts),
            "source member path exceeds bounded filesystem geometry")
    leaf = name.rsplit("/", 1)[-1].casefold()
    require(leaf not in ("id_dsa", "id_ecdsa") and
            not any(token in leaf for token in ("api-key", "apikey", "ssh-key", "private_key", "private-key")),
            "protected key input is not a source artifact member")
    return name


def _read(path, target, *, limit=None):
    path = _path(path, existing=True)
    return target.input_reader().read_regular(path, limit=target.MAX_MEMBER if limit is None else limit)


def _snapshot(root, target):
    """Walk only the explicit owned artifact; reject before opening each file."""
    reader = target.input_reader()
    stamp = reader.file_stamp
    members, stamps, directories = {}, {}, {}
    total, nodes = 0, 1
    def walk(descriptor, parts):
        nonlocal total, nodes
        before = os.fstat(descriptor)
        require(stat.S_ISDIR(before.st_mode), "source artifact directory cannot be a link or non-directory")
        directories["/".join(parts) or "."] = stamp(before)
        names = []
        with os.scandir(descriptor) as scan:
            for entry in scan:
                nodes += 1
                require(nodes <= 10000, "source artifact total node count exceeds transport bound")
                names.append(entry.name)
        for name in sorted(names):
            relative_parts = (*parts, name)
            relative = "/".join(relative_parts)
            _safe_member(target, PREFIX + "/" + relative)
            value = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISDIR(value.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                try:
                    require(stamp(os.fstat(child)) == stamp(value), "source directory changed before collection")
                    walk(child, relative_parts)
                    require(stamp(os.stat(name, dir_fd=descriptor, follow_symlinks=False)) == stamp(value),
                            "source directory changed after collection")
                finally:
                    os.close(child)
                continue
            require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1,
                    "source artifact contains a link or unknown nonregular file")
            require(name not in (BUNDLE, SEAL), "source artifact cannot contain its own transport files")
            require(value.st_size <= target.MAX_MEMBER and len(members) < 10000,
                    "source artifact member count or size exceeds transport bound")
            total += value.st_size
            require(total <= target.MAX_BUNDLE, "expanded source artifact exceeds transport bound")
            name = PREFIX + "/" + relative
            members[name] = reader.read_regular_at(descriptor, relative_parts[-1], limit=target.MAX_MEMBER, expected=value)
            stamps[name] = stamp(value)
        require(stamp(os.fstat(descriptor)) == stamp(before), "source artifact directory changed during collection")
    root_fd = reader.open_directory(root)
    try:
        walk(root_fd, ())
        reader.same_directory(root, root_fd)
    finally:
        os.close(root_fd)
    require(members, "source artifact is empty")
    return members, stamps, directories


def _zip_bytes(members, stamps):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            mode = stamps[name][2]
            require(not mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX), "special source artifact permissions are not transported")
            info.external_attr = (stat.S_IFREG | (mode & 0o777)) << 16
            archive.writestr(info, members[name], compress_type=zipfile.ZIP_STORED)
    return stream.getvalue()


def _write_new(path, data, target):
    reader = target.input_reader()
    stamp = reader.file_stamp
    parent = reader.open_directory(path.parent)
    descriptor = None
    try:
        descriptor = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
        value = os.fstat(descriptor)
        require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1 and value.st_size == len(data)
                and stamp(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) == stamp(value),
                "new transport evidence changed during its write")
        reader.same_directory(path.parent, parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def _pipeline(path, out, family, context, target):
    path = _path(path, existing=True)
    require(path == out / "pipeline-functional.json", "immutable named functional pipeline receipt required")
    raw = _read(path, target)
    record = json.loads(raw)
    require(record.get("format") == "rove4k-production-ci-functional-v1"
            and record.get("family") == family and record.get("profile") == "test-p4"
            and record.get("backend") == "ubuntu-24.04-gcc13-host-cc"
            and record.get("source_context") == context and record.get("complete") is True
            and record.get("functional_complete") is True and not record.get("failure")
            and not record.get("cleanup_failure")
            and record.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
            "a completed same-CI Ubuntu24 functional pipeline is required before export")
    commands = record.get("commands", [])
    require(commands and all(all(row.get(key) is True for key in
        ("started", "terminal", "reaped", "owned_group_absent", "original_identity_retained_until_other_members_absent"))
        and row.get("forced_cleanup") is False and row.get("other_group_members_before_reap") == []
        and type(row.get("returncode")) is int and row["returncode"] == 0 for row in commands),
        "source pipeline still owns failed or unsettled commands")
    stages = record.get("stages", [])
    require([row.get("name") for row in stages] == ["generation", "mechanism", "rules", "runtime"]
            and all(row.get("complete") is True for row in stages), "source pipeline stages are incomplete")
    paths = ("artifact/build.json", "mechanism/result.json" if family == "B" else "mechanism/results.json",
             "rules/commands.json", "runtime/runtime.json")
    for row, relative in zip(stages, paths):
        expected = out / relative
        require(row.get("receipt") == {"path": str(expected), **target.pin(_read(expected, target))},
                "functional pipeline stage differs from its actual owned receipt")
    return raw


def _admit(verify, build, family, target):
    record = json.loads(_read(build / "build.json", target, limit=8 << 20))
    admitted = (verify.admit_d_build(record, build, "D-source-jit") if family == "D"
                else verify.admit_c_build(record, build))
    require(admitted.family == family and admitted.profile_id == "test-p4"
            and admitted.representation == "source-jit" and admitted.full is True,
            "one full selected TEST-P4 source-JIT admission required")
    return admitted


def export_bundle(source_out, build, *, family, runner_temp, verify, target, ci_context, pipeline_receipt):
    sources = _sources(target)
    require(family in tuple("ABCDEF"), "explicit active C family required")
    runner, out, build = _owned_roots(source_out, build, runner_temp)
    context = _live_context(target, ci_context)
    pipeline = _pipeline(pipeline_receipt, out, family, context, target)
    admitted = _admit(verify, build, family, target)
    before = _snapshot(build, target)
    data = _zip_bytes(before[0], before[1])
    require(len(data) <= target.MAX_BUNDLE, "raw source bundle exceeds transport bound")
    bundle, seal_path = out / BUNDLE, out / SEAL
    require(not bundle.exists() and not seal_path.exists(), "source bundle and seal are immutable new outputs")
    _write_new(bundle, data, target)
    layout = {"runner_temp_root": str(runner), "output_root": str(out), "builds": {PREFIX: str(build)}}
    seal = target.build_source_seal(bundle, [(admitted, build, PREFIX)], verify=verify,
                                    ci_context=ci_context, restore_layout=layout)
    layout = target.validate_restore_layout(seal, runner_temp_root=str(runner))
    require(_snapshot(build, target) == before, "source artifact changed after collection/sealing")
    require(_pipeline(pipeline_receipt, out, family, context, target) == pipeline,
            "functional source receipt changed during export")
    require(_read(bundle, target, limit=target.MAX_BUNDLE) == data, "source bundle changed after creation")
    target._sealed_source(seal, data, _live_context(target, ci_context))
    raw = (json.dumps(seal, indent=2) + "\n").encode()
    require(len(raw) <= target.MAX_MEMBER, "source seal exceeds transport bound")
    require(_sources(target) == sources, "source transport or seal authority changed during export")
    _write_new(seal_path, raw, target)
    require(_read(seal_path, target) == raw, "source seal changed after creation")
    return {"format": "rove4k.source-bundle-export.v1", "family": family, "profile": "test-p4",
            "source_context": context, "restore_layout": layout,
            "source_bundle": {"path": str(bundle), **target.pin(data)},
            "source_seal": {"path": str(seal_path), **target.pin(raw)},
            "functional_pipeline": {"path": str(pipeline_receipt), **target.pin(pipeline)},
            "artifact_files": len(before[0]), "engine_executed_by_export": False}


def _zip_modes(data, members, target):
    require(len(data) <= target.MAX_BUNDLE, "raw source bundle exceeds transport bound")
    modes = {}
    expanded = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        require(len(archive.infolist()) <= 10000, "source bundle member count exceeds transport bound")
        for item in archive.infolist():
            _safe_member(target, item.filename)
            mode = item.external_attr >> 16
            require(not item.is_dir() and stat.S_ISREG(mode) and
                    not mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX),
                    "restore accepts only regular source members with ordinary permissions")
            require(item.compress_type == zipfile.ZIP_STORED and item.compress_size == item.file_size
                    and not item.flag_bits & 1 and item.file_size <= target.MAX_MEMBER,
                    "restore accepts only bounded uncompressed source members")
            expanded += item.file_size
            require(expanded <= target.MAX_BUNDLE, "expanded source bundle exceeds transport bound")
            require((members is None or item.filename in members) and item.filename not in modes,
                    "restore member topology differs")
            modes[item.filename] = mode & 0o777
    require(members is None or set(modes) == set(members), "restore member mode set differs from its seal")
    for name in modes:
        parts = name.split("/")
        require(not any("/".join(parts[:count]) in modes for count in range(1, len(parts))),
                "source member file collides with a parent directory")
    return modes


def _create_root(runner, out):
    """Anchor all writes to directory handles; no extractall or symlink follow."""
    require(os.name == "posix" and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),
            "POSIX no-follow directory handles are required for source restore")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(runner.anchor, flags)
    try:
        for part in runner.parts[1:]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        parts = out.relative_to(runner).parts
        for index, part in enumerate(parts):
            try:
                os.mkdir(part, 0o700, dir_fd=descriptor)
            except FileExistsError:
                require(index != len(parts) - 1, "exact original source root already exists")
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _restore_files(root_fd, members, modes):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    for name, data in sorted(members.items()):
        descriptor = os.dup(root_fd)
        try:
            parts = name.split("/")
            for part in parts[:-1]:
                try:
                    os.mkdir(part, 0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(part, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            file_fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=descriptor)
            try:
                with os.fdopen(file_fd, "wb", closefd=False) as stream:
                    stream.write(data)
                    stream.flush()
                os.fchmod(file_fd, modes[name])
            finally:
                os.close(file_fd)
        finally:
            os.close(descriptor)


def restore_bundle(bundle, source_seal, *, family, runner_temp, verify, target, ci_context, reserved_out):
    sources = _sources(target)
    require(family in tuple("ABCDEF"), "explicit active C family required")
    bundle, source_seal = _path(bundle, existing=True), _path(source_seal, existing=True)
    require(bundle.name == BUNDLE and source_seal.name == SEAL, "explicit source-bundle.zip and source-seal.json required")
    context = _live_context(target, ci_context)
    data, raw = _read(bundle, target, limit=target.MAX_BUNDLE), _read(source_seal, target)
    seal = json.loads(raw)
    modes = _zip_modes(data, None, target)
    members = target._sealed_source(seal, data, context)
    require(set(modes) == set(members), "restore member mode set differs from its seal")
    layout = target.validate_restore_layout(seal, runner_temp_root=str(_path(runner_temp, existing=True, directory=True)))
    profiles = seal.get("profiles", [])
    require(len(profiles) == 1 and profiles[0].get("family") == family and profiles[0].get("profile") == "test-p4"
            and profiles[0].get("representation") == "source-jit" and profiles[0].get("full") is True
            and profiles[0].get("archive_prefix") == PREFIX, "one sealed full selected TEST-P4 source-JIT profile required")
    runner, out, build = _owned_roots(layout["output_root"], layout["builds"][PREFIX], runner_temp, new=True)
    reserved = _path(reserved_out)
    require(reserved != runner and reserved.is_relative_to(runner) and not reserved.exists()
            and not reserved.is_relative_to(out) and not out.is_relative_to(reserved),
            "target output must be a distinct new RUNNER_TEMP root")
    _outside_checkout(reserved)
    require(all(name.startswith(PREFIX + "/") for name in members), "source bundle contains an unowned build member")
    require(all(len((str(out) + "/" + name).encode("utf-8")) <= 4096 for name in members),
            "restored absolute member path exceeds filesystem bound")
    # All context, paths, member identities, topology and caps are checked
    # before the first new directory is created.
    root_fd = _create_root(runner, out)
    try:
        _restore_files(root_fd, members, modes)
    finally:
        os.close(root_fd)
    actual = _snapshot(build, target)[0]
    require(actual == members, "restored raw source members differ from the sealed bundle")
    require(_read(bundle, target, limit=target.MAX_BUNDLE) == data and _read(source_seal, target) == raw,
            "transport evidence changed during restore")
    _live_context(target, ci_context)
    admitted = _admit(verify, build, family, target)
    target.source_bundle_binding(admitted, build, verify=verify, source_bundle=bundle,
                                 source_seal=source_seal, expected_ci=ci_context)
    require(_sources(target) == sources, "source transport or seal authority changed during restore")
    return {"format": "rove4k.source-bundle-restoration.v1", "family": family, "profile": "test-p4",
            "output_root": str(out), "build_root": str(build), "source_context": context,
            "restore_layout": layout, "source_bundle": {"path": str(bundle), **target.pin(data)},
            "source_seal": {"path": str(source_seal), **target.pin(raw)},
            "restored_files": len(members), "exact_original_paths": True,
            "source_validated_after_restore": True, "factory_replayed_on_target": False}
