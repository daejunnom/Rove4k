#!/usr/bin/env python3
"""Seal one source-only P16/P192 build for the existing seed consumer.

This emits the existing source-bundle seal format from an owned CI build. It
does not run an engine, qualify runtime behavior, authenticate GitHub metadata,
or issue a league admission. GitHub source/run authentication is separate.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
SEED_MEMBER_LIMIT = 32 << 20
_BLOCKED = {'.git', '.ssh', '.aws', '.env', '.npmrc', '.pypirc', '.netrc',
            'node_modules', 'dist', 'dist-server', 'build', 'coverage',
            'models', 'checkpoints', '.cache', 'inventory.json',
            'package-lock.json', 'id_rsa', 'id_ed25519', 'id_dsa',
            'id_ecdsa', 'authorized_keys'}
_SECRET = re.compile(r'credential|service[-_ ]?account|api[-_ ]?key|ssh[-_ ]?key|private[-_ ]?key|password|passwd|secret', re.I)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _snapshot(build, target):
    """Collect only owned files; reject protected names before opening them."""
    reader = target.input_reader()
    stamp = reader.file_stamp
    members, stamps, directories = {}, {}, {}
    total, nodes = 0, 1

    def walk(descriptor, parts):
        nonlocal total, nodes
        before = os.fstat(descriptor)
        require(stat.S_ISDIR(before.st_mode), 'ordinary directory required')
        directories['/'.join(parts) or '.'] = stamp(before)
        names = []
        with os.scandir(descriptor) as scan:
            for entry in scan:
                nodes += 1
                require(nodes <= 10000, 'source node count exceeds bound')
                names.append(entry.name)
        for name in sorted(names):
            # Never open or descend into a protected component, even if it is
            # a directory containing otherwise innocuous-looking file names.
            folded = name.casefold()
            require(folded not in _BLOCKED and not folded.startswith('.env.')
                    and not re.match(r'^id_(rsa|ed25519|dsa|ecdsa)(?:\.|$)', folded)
                    and not _SECRET.search(name) and not folded.endswith(('.pem', '.key', '.p12', '.pfx')),
                    'protected or heavy source component is not transportable')
            relative = (*parts, name)
            logical = 'build/' + '/'.join(relative)
            target._member(logical)
            require(len(relative) <= 64 and len(logical.encode('utf-8')) <= 4096
                    and len(name.encode('utf-8')) <= 255, 'source path exceeds bound')
            value = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISDIR(value.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                try:
                    require(stamp(os.fstat(child)) == stamp(value), 'source directory changed')
                    walk(child, relative)
                    require(stamp(os.stat(name, dir_fd=descriptor, follow_symlinks=False)) == stamp(value),
                            'source directory changed after collection')
                finally:
                    os.close(child)
                continue
            require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1,
                    'source member is not an ordinary single-link file')
            require(value.st_size <= target.MAX_MEMBER and len(members) < 10000,
                    'source member exceeds bound')
            total += value.st_size
            require(total <= target.MAX_BUNDLE, 'expanded source exceeds bound')
            members[logical] = reader.read_regular_at(descriptor, name, limit=target.MAX_MEMBER, expected=value)
            stamps[logical] = stamp(value)
        require(stamp(os.fstat(descriptor)) == stamp(before), 'source directory changed during collection')

    descriptor = reader.open_directory(build)
    try:
        walk(descriptor, ())
        reader.same_directory(build, descriptor)
    finally:
        os.close(descriptor)
    require(members, 'source artifact is empty')
    return members, stamps, directories


def export(*, source_out, build, family, profile, runner_temp, ci_context,
           verify, target, transport):
    """Export actual owned files without claiming functional qualification."""
    require(family in tuple('ABCEF') and profile in ('test-p16', 'test-p192'),
            'one supported full P16/P192 family required')
    runner = transport._path(runner_temp, existing=True, directory=True)
    out = transport._path(source_out, existing=True, directory=True)
    build = transport._path(build, existing=True, directory=True)
    require(out != runner and out.is_relative_to(runner) and build == out / 'build',
            'exact build child of an owned RUNNER_TEMP output required')
    transport._outside_checkout(out)
    sources = transport._sources(target)
    context = transport._live_context(target, ci_context)
    # Check every component before admission can follow manifest references.
    before = _snapshot(build, target)
    require('build/build.json' in before[0] and len(before[0]['build/build.json']) <= 8 << 20,
            'bounded build manifest required')
    raw = before[0]['build/build.json']
    admitted = verify.admit_c_build(json.loads(raw), build)
    require(admitted.family == family and admitted.profile_id == profile
            and admitted.representation == 'source-jit' and admitted.full is True,
            'strict admitted family and profile must match')
    require(_snapshot(build, target) == before, 'source artifact changed during admission')
    data = transport._zip_bytes(before[0], before[1])
    require(len(data) <= min(target.MAX_BUNDLE, SEED_MEMBER_LIMIT),
            'source bundle exceeds the seed member bound')
    bundle, seal_path = out / 'source-bundle.zip', out / 'source-seal.json'
    require(not bundle.exists() and not seal_path.exists(), 'source outputs must be new')
    transport._write_new(bundle, data, target)
    layout = {'runner_temp_root': str(runner), 'output_root': str(out),
              'builds': {'build': str(build)}}
    seal = target.build_source_seal(bundle, [(admitted, build, 'build')], verify=verify,
                                    ci_context=ci_context, restore_layout=layout)
    target.validate_restore_layout(seal, runner_temp_root=str(runner))
    require(_snapshot(build, target) == before,
            'source artifact changed during collection')
    require(transport._read(bundle, target, limit=target.MAX_BUNDLE) == data,
            'source bundle changed during sealing')
    target._sealed_source(seal, data, context)
    seal_raw = (json.dumps(seal, indent=2) + '\n').encode()
    require(len(seal_raw) <= target.MAX_MEMBER, 'source seal exceeds bound')
    require(transport._sources(target) == sources, 'source authority changed during export')
    transport._write_new(seal_path, seal_raw, target)
    require(transport._read(seal_path, target) == seal_raw, 'source seal changed after write')
    return {'format': 'rove4k.league-source-export.v1', 'family': family,
            'profile': profile, 'source_context': context,
            'source_bundle': {'path': str(bundle), **target.pin(data)},
            'source_seal': {'path': str(seal_path), **target.pin(seal_raw)},
            'engine_executed': False, 'runtime_qualified': False}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, 'source module unavailable')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--runner-temp', type=Path, required=True)
    parser.add_argument('--family', choices=tuple('ABCEF'), required=True)
    parser.add_argument('--profile', choices=('test-p16', 'test-p192'), required=True)
    args = parser.parse_args()
    target = _load('rove4k_league_target_runtime', ROOT / 'engines/experiments/tcec-next/target_runtime.py')
    transport = _load('rove4k_league_source_transport', ROOT / 'engines/scripts/production_source_bundle.py')
    verify = _load('rove4k_league_profile_verify', ROOT / 'engines/experiments/tcec-next/profile_verify.py')
    result = export(source_out=args.out, build=args.out / 'build', family=args.family,
                    profile=args.profile, runner_temp=args.runner_temp,
                    ci_context=target.CIContext.from_environment(), verify=verify,
                    target=target, transport=transport)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
