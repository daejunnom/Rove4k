"""Collect exact P16/P192 producer artifacts into a seed.prepare configuration.

The caller supplies the clean checkout and pinned Fastchess/opening inputs. This
only reads GitHub and writes a new external staging directory. The resulting
configuration is not a seed, engine qualification, host authorization or GO.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

try:
    from . import league_github_producer as producer, seed
except ImportError:
    import league_github_producer as producer
    import seed


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _json(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def _selected_members(raw, *, remaining):
    """Inspect ZIP names before opening any data, then read only required files."""
    _require(type(raw) is bytes and len(raw) <= producer._MAX_ARCHIVE, 'bounded artifact ZIP required')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        _require(len(infos) <= producer._MAX_FILES, 'too many artifact ZIP members')
        # Reject protected names, duplicate names, special files and every
        # oversized selected member before opening any ZIP member.
        seen = set()
        selected_bytes = 0
        for info in infos:
            name = producer._safe_name(info.filename, directory=info.is_dir())
            _require(name not in seen, 'duplicate artifact ZIP member')
            seen.add(name)
            if not info.is_dir() and (name in ('source-bundle.zip', 'source-seal.json') or name.startswith('rules/')):
                _require(0 <= info.file_size <= seed.MAX_MEMBER, 'selected artifact member exceeds seed limit')
                selected_bytes += info.file_size
        _require(selected_bytes <= remaining, 'selected artifact exceeds remaining seed budget')
        names = [x.filename for x in infos if not x.is_dir()]
    wanted = {'source-bundle.zip', 'source-seal.json'} | {n for n in names if n.startswith('rules/')}
    _require({'rules/commands.json', 'rules/probe/rules.json', 'rules/probe/cases.json',
              'rules/probe/fixture.c'} <= wanted, 'rules closure is incomplete')
    data = producer._zip_members(raw, wanted)
    # seed.prepare reads every bundled member; preflight their protected paths
    # before it can do so, without inspecting unrelated outer artifact files.
    with zipfile.ZipFile(io.BytesIO(data['source-bundle.zip'])) as bundle:
        nested = bundle.infolist()
        _require(len(nested) <= producer._MAX_FILES, 'too many bundled members')
        expanded = 0
        for info in nested:
            producer._safe_name(info.filename, directory=info.is_dir())
            if not info.is_dir():
                _require(0 <= info.file_size <= seed.MAX_MEMBER, 'bundled member exceeds seed limit')
                expanded += info.file_size
        _require(expanded + selected_bytes <= remaining, 'bundle exceeds remaining seed budget')
    producer._zip_members(data['source-bundle.zip'], {'build/build.json'})
    return data, expanded


def assemble(base_config, selections, *, out, get, archive):
    """Construct explicit seed inputs from authenticated-transport observations.

    get and archive are injectable for tests; a caller-supplied transport is
    not automatically trusted. CLI uses the bounded read-only gh transport.
    """
    _require(type(base_config) is dict and base_config.get('format') == 'rove4k-seed-prepare-v1',
             'base must be an explicit seed prepare configuration')
    config = json.loads(_json(base_config))
    origin = seed.origin_check(config['source_origin'])
    _require(origin['repository'] == producer._REPO and re.fullmatch(r'[0-9a-f]{40}', origin['head_sha'])
             and config['checkout']['commit'] == origin['head_sha'], 'pinned repository and checkout required')
    _require(type(selections) is list and 0 < len(selections) <= 10 and not config.get('rove'),
             'explicit unique selections and an empty base rove list required')
    _require(type(config.get('inputs')) is dict and type(config.get('original_layout')) is dict
             and type(config['original_layout'].get('roots')) is list, 'explicit base inputs/layout required')
    base_bytes = 0
    for name, descriptor in config['inputs'].items():
        seed.member(name)
        producer._safe_name(name, directory=False)
        item = seed.input_descriptor(descriptor)
        # seed.prepare later reads these paths; reject known protected names
        # here before producing a configuration that could read them.
        for component in Path(item['path']).parts[1:]:
            producer._safe_name(component, directory=False)
            _require(component.casefold() != 'build', 'generated base input path is not allowed')
        base_bytes += item['bytes']
    _require(base_bytes <= seed.MAX_SEED, 'base inputs exceed seed expansion bound')
    run_id, attempt = (producer._decimal(origin[k]) for k in ('run_id', 'run_attempt'))
    prefix = '/repos/' + producer._REPO + '/'
    run = get(prefix + f'actions/runs/{run_id}/attempts/{attempt}')
    repo, head_repo = run.get('repository'), run.get('head_repository')
    _require(type(repo) is dict and repo.get('full_name') == producer._REPO and type(repo.get('id')) is int
             and repo['id'] > 0 and type(head_repo) is dict and type(head_repo.get('id')) is int
             and head_repo['id'] > 0 and run.get('id') == run_id and run.get('run_attempt') == attempt
             and run.get('status') == 'completed' and run.get('conclusion') == 'success'
             and str(run.get('path', '')).split('@', 1)[0] == producer._WORKFLOW
             and type(run.get('head_sha')) is str and producer._SHA.fullmatch(run['head_sha'])
             and type(run.get('head_branch')) is str and run['head_branch'], 'producer run identity differs')
    jobs = producer._all_jobs(run_id, attempt, get)
    artifacts = producer._pages(prefix + f'actions/runs/{run_id}/artifacts', 'artifacts', get)
    staged, expanded_bundles = {}, 0

    def add(name, raw):
        seed.member(name)
        _require(name not in staged and name not in config['inputs'] and type(raw) is bytes
                 and len(raw) <= seed.MAX_MEMBER, 'duplicate or oversized seed input')
        _require(base_bytes + expanded_bundles + sum(len(item) for item in staged.values()) + len(raw)
                 <= seed.MAX_SEED, 'selected inputs exceed seed expansion bound')
        staged[name] = raw

    docs = {'run': 'metadata/workflow-run.json', 'commit': 'metadata/execution-commit.json'}
    add(docs['run'], _json(run))
    commit = get(prefix + 'git/commits/' + origin['head_sha'])
    _require(commit.get('sha') == origin['head_sha'], 'execution commit identity differs')
    add(docs['commit'], _json(commit))
    if run.get('event') == 'pull_request':
        rows = run.get('pull_requests')
        _require(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict
                 and type(rows[0].get('number')) is int and rows[0]['number'] > 0, 'unique PR required')
        pr = get(prefix + 'pulls/' + str(rows[0]['number']))
        _require(pr.get('number') == rows[0]['number'] and pr.get('merge_commit_sha') == origin['head_sha'],
                 'live PR merge differs from pinned checkout')
        docs['pull_request'] = 'metadata/pull-request.json'
        add(docs['pull_request'], _json(pr))
    else:
        _require(run.get('event') in ('push', 'workflow_dispatch') and run['head_sha'] == origin['head_sha'],
                 'ordinary workflow checkout differs')
    _require('workflow_provenance' not in config, 'workflow provenance is collected from the pinned run')
    config['workflow_provenance'] = docs
    config['rove'] = []
    keys, ids = set(), set()
    for row in selections:
        _require(type(row) is dict and set(row) == {'family', 'profile', 'variant', 'artifact_id'},
                 'explicit family/profile/variant/artifact identity required')
        family, profile, variant = row['family'], row['profile'], row['variant']
        _require(type(family) is str and family in tuple('ABCEF') and profile in ('test-p16', 'test-p192')
                 and type(variant) is str and producer._VARIANT.fullmatch(variant), 'unsupported selection')
        artifact_id = producer._decimal(row['artifact_id'])
        _require((family, profile) not in keys and artifact_id not in ids, 'duplicate selection or artifact')
        keys.add((family, profile)); ids.add(artifact_id)
        job_name = f'source-{family}-{profile}-{variant}'
        selected_jobs = [j for j in jobs if j.get('name') == job_name]
        _require(len(selected_jobs) == 1 and selected_jobs[0].get('run_id') == run_id
                 and selected_jobs[0].get('head_sha') == run['head_sha']
                 and selected_jobs[0].get('status') == 'completed' and selected_jobs[0].get('conclusion') == 'success',
                 'matching source job was not uniquely successful')
        steps = selected_jobs[0].get('steps')
        _require(type(steps) is list, 'source job steps absent')
        for name in ('Seal the admitted source for P16 and P192 seed transport',
                     'Preserve actual artifacts, bounded command logs and failures'):
            matching = [s for s in steps if type(s) is dict and s.get('name') == name]
            _require(len(matching) == 1 and matching[0].get('status') == 'completed'
                     and matching[0].get('conclusion') == 'success', 'source seal/upload step failed')
        expected_name = f'league-source-{family}-{profile}-{variant}-{origin["head_sha"]}-{attempt}'
        found = [x for x in artifacts if x.get('name') == expected_name]
        _require(len(found) == 1 and found[0].get('id') == artifact_id, 'artifact selection differs')
        metadata = get(prefix + f'actions/artifacts/{artifact_id}')
        ref, digest = metadata.get('workflow_run'), metadata.get('digest')
        _require(metadata.get('id') == artifact_id and metadata.get('name') == expected_name
                 and metadata.get('expired') is False and type(ref) is dict and ref.get('id') == run_id
                 and ref.get('repository_id') == repo['id'] and ref.get('head_repository_id') == head_repo['id']
                 and ref.get('head_sha') == run['head_sha'] and ref.get('head_branch') == run['head_branch']
                 and type(digest) is str and re.fullmatch(r'sha256:[0-9a-f]{64}', digest), 'artifact metadata differs')
        data = archive(artifact_id)
        _require(type(data) is bytes and hashlib.sha256(data).hexdigest() == digest[7:], 'artifact ZIP digest differs')
        metadata_raw = _json(metadata)
        remaining = seed.MAX_SEED - base_bytes - expanded_bundles - sum(map(len, staged.values())) - len(metadata_raw)
        parts, expanded = _selected_members(data, remaining=remaining)
        seal = producer._json(parts['source-seal.json'])
        _require(seal.get('format') == 'rove4k.source-bundle-seal.v1' and seal.get('ci_context') == origin
                 and seal.get('producer') == {'ID': 'ubuntu', 'VERSION_ID': '24.04'}
                 and seal.get('bundle_format') == 'zip' and seal.get('bundle') == seed.pin(parts['source-bundle.zip']),
                 'source seal origin or bundle differs')
        bundled = seed.archive_members(parts['source-bundle.zip'])
        _require(seal.get('members') == {name: seed.pin(value[0]) for name, value in sorted(bundled.items())},
                 'source seal member map differs')
        profiles = [x for x in seal.get('profiles', []) if type(x) is dict
                    and (x.get('family'), x.get('profile')) == (family, profile)]
        layout = seal.get('restore_layout')
        _require(len(profiles) == 1 and profiles[0].get('archive_prefix') == 'build'
                 and profiles[0].get('full') is True and profiles[0].get('representation') == 'source-jit'
                 and type(layout) is dict and set(layout) == {'runner_temp_root', 'output_root', 'builds'}
                 and layout['runner_temp_root'] == '/home/runner/work/_temp'
                 and type(layout['output_root']) is str
                 and profiles[0].get('build_root') == layout['output_root'] + '/build'
                 and layout['builds'] == {'build': profiles[0]['build_root']}
                 and all(name.startswith('build/') for name in bundled)
                 and 'build/build.json' in bundled
                 and profiles[0].get('input_manifest') == seed.pin(bundled['build/build.json'][0]),
                 'sealed layout differs')
        logical = f'origin/{family}-{profile}'
        metadata_name = f'metadata/{family}-{profile}-artifact.json'
        add(metadata_name, metadata_raw)
        for name, raw in parts.items():
            add(logical + '/' + name, raw)
        expanded_bundles += expanded
        config['rove'].append({'family': family, 'profile': profile, 'build': logical + '/build',
            'source_bundle': logical + '/source-bundle.zip', 'source_seal': logical + '/source-seal.json',
            'artifact_metadata': metadata_name, 'rules': logical + '/rules/probe/rules.json'})
        config['original_layout']['roots'].append({'original_root': layout['output_root'], 'seed_prefix': logical})

    target = seed.new_external(out)
    target.mkdir(parents=True)
    for name, raw in sorted(staged.items()):
        path = target / 'inputs' / name
        seed.write_new(path, raw)
        config['inputs'][name] = {'path': str(path), **seed.pin(raw)}
    config_path = target / 'seed-prepare.json'
    seed.write_new(config_path, _json(config))
    return {'config': str(config_path), 'source_origin': origin, 'selections': len(config['rove']),
            'observed_files': len(staged), 'seed_prepared': False, 'engine_executed': False,
            'authorizes_go': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True, help='explicit common seed prepare JSON')
    parser.add_argument('--selections', type=Path, required=True, help='explicit JSON selection array')
    parser.add_argument('--out', type=Path, required=True, help='new external staging directory')
    args = parser.parse_args(argv)
    base = producer._json(seed.ordinary(args.base, limit=producer._MAX_JSON))
    def unique(pairs):
        value = {}
        for key, item in pairs:
            _require(key not in value, 'duplicate selection JSON member')
            value[key] = item
        return value
    def bad(_):
        raise ValueError('non-finite JSON number')
    selections = json.loads(seed.ordinary(args.selections, limit=producer._MAX_JSON),
                            object_pairs_hook=unique, parse_constant=bad)
    result = assemble(base, selections, out=args.out, get=producer._gh_api_json, archive=producer._gh_api_archive)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
