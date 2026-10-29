"""Restore a sealed Rove seed candidate for diagnostics, without running it.

ZIP names are transport identifiers; the selected ``build/`` prefix is never
created on disk.  File pins and a supplied producer-observation report do not
authenticate their origin, establish a source-to-native build, or authorize GO.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile

sys.dont_write_bytecode = True
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from . import cloud_runtime, diagnostic_candidates, registry, rove_b_static_tt, seed
except ImportError:
    import cloud_runtime
    import diagnostic_candidates
    import registry
    import rove_b_static_tt
    import seed


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _virtual_name(name):
    """Check prohibited names without resolving or opening ZIP member paths."""
    cloud_runtime.member(name)
    parts = PurePosixPath(name).parts
    # build is legal only as a ZIP namespace, not as an on-disk destination.
    safe = Path('/virtual') / Path(*(('transport-build' if p.casefold() == 'build' else p) for p in parts))
    diagnostic_candidates._check_path_components(safe)


def _report_matches(report, manifest, row, seal, metadata, artifact):
    origin = manifest['source_origin']
    _require(report.get('format') == 'rove4k.github-source-observation-v1'
             and report.get('repository') == origin['repository']
             and str(report.get('run_id')) == str(origin['run_id'])
             and str(report.get('run_attempt')) == str(origin['run_attempt'])
             and report.get('source_head') == origin['head_sha']
             and report.get('family') == row['family'] and report.get('profile') == row['profile']
             and report.get('artifact_id') == metadata.get('id')
             and 'sha256:' + str(report.get('artifact_sha256')) == metadata.get('digest')
             and report.get('source_bundle_sha256') == seal['bundle']['sha256']
             and report.get('source_seal_sha256') == manifest['members'][row['source_seal']]['sha256']
             and report.get('candidate_pins_match') is True
             and report.get('candidate_files_observed') is False
             and report.get('runtime_qualified') is False and report.get('authorizes_go') is False,
             'producer observation does not match seed identity or scope')
    profiles = [p for p in seal.get('profiles', [])
                if (p.get('family'), p.get('profile')) == (row['family'], row['profile'])]
    _require(len(profiles) == 1 and artifact.sha256 == profiles[0]['old_expected_contract']['whole_sha256'],
             'candidate whole does not match producer seal')


def _b_static_evidence(*, family, profile, selected, build_manifest, report, legacy):
    """Correlate sealed bytes with a supplied report; neither authenticates it."""
    names = diagnostic_candidates._B_STATIC_NAMES
    if family != 'B':
        _require(not legacy, 'legacy B diagnostic mode is only for B')
        return None
    present = tuple(name in selected for name in names)
    _require(not any(present) or all(present), 'incomplete B static evidence')
    if not any(present):
        _require(legacy, 'B seed has no static evidence; explicit legacy diagnostic mode required')
        _require(report is None or report.get('b_static_correlation') is None,
                 'legacy seed cannot match a producer static correlation')
        return {'mode': 'legacy-no-static', 'static_files': {}, 'static_correlation': None,
                'producer_report_authenticated': False, 'authorizes_go': False}
    _require(not legacy, 'legacy mode cannot be used for a B seed with static evidence')
    _require(report is not None and report.get('variant') == 'league-atomic',
             'B static evidence requires the matching league-atomic producer observation')
    raw = selected['b-static-tt.json']
    static = rove_b_static_tt.validate_report_bytes(
        raw, profile=profile, source=selected['main.c'], native=selected['native/x'],
        manifest=build_manifest, compiler_sha=selected['compiler-sha256.txt'].decode('ascii').strip(),
        linker_sha=selected['linker-sha256.txt'].decode('ascii').strip())
    static['report_sha256'] = hashlib.sha256(raw).hexdigest()
    diagnostic_candidates._b_producer_matches(report, profile, static)
    return {'mode': 'sealed-static-correlated',
            'static_files': {name: diagnostic_candidates._b_pin(selected[name]) for name in names},
            'static_correlation': static,
            'producer_report_authenticated': False, 'authorizes_go': False}


def prepare(*, archive_path, archive_sha256, manifest_sha256, family, profile, out,
            producer_report=None, producer_report_sha256=None, legacy_b_diagnostic=False):
    _require(family in tuple('ABCEF') and profile in ('test-p16', 'test-p192'),
             'a non-D Rove P16/P192 candidate is required')
    _require(type(legacy_b_diagnostic) is bool and (family == 'B' or not legacy_b_diagnostic),
             'explicit legacy mode is available only for B')
    _require(all(isinstance(v, str) and cloud_runtime.SHA.fullmatch(v)
                 for v in (archive_sha256, manifest_sha256)), 'independent archive and manifest pins required')
    archive_path = diagnostic_candidates._safe_input_path(archive_path)
    raw = cloud_runtime.ordinary(archive_path, limit=cloud_runtime.MAX_SEED)
    _require(hashlib.sha256(raw).hexdigest() == archive_sha256, 'seed archive identity differs')
    output = diagnostic_candidates._safe_output_path(out)
    _require(output.parent.is_dir(), 'output parent must already exist')
    _require((producer_report is None) == (producer_report_sha256 is None), 'producer report and pin must be paired')
    report = None
    if producer_report is not None:
        report_path = diagnostic_candidates._safe_input_path(producer_report)
        report_raw = cloud_runtime.ordinary(report_path, limit=cloud_runtime.MAX_SEED_MANIFEST)
        _require(isinstance(producer_report_sha256, str) and cloud_runtime.SHA.fullmatch(producer_report_sha256)
                 and hashlib.sha256(report_raw).hexdigest() == producer_report_sha256, 'producer report pin differs')
        report = diagnostic_candidates._strict_json(report_raw)
        if report.get('format') == 'rove4k-source-observations-56d-v1':
            _require(report.get('authorizes_go') is False and report.get('engine_executed') is False
                     and report.get('seed_manifests', {}).get(profile) == manifest_sha256,
                     'observation collection seed or scope differs')
            matches = [r for r in report.get('results', []) if type(r) is dict
                       and (r.get('family'), r.get('profile')) == (family, profile)]
            _require(len(matches) == 1, 'observation collection lacks a unique selected report')
            report = matches[0]

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        manifest, _, infos = cloud_runtime.seed_archive_manifest(archive, expected_manifest_sha256=manifest_sha256)
        rows = [r for r in manifest['rove'] if (r['family'], r['profile']) == (family, profile)]
        _require(len(rows) == 1, 'exactly one selected Rove seed required')
        row = rows[0]
        prefix = row['build'] + '/'
        selected = {}
        workflow = cloud_runtime.workflow_provenance_schema(manifest)
        provenance_names = (set(workflow['inputs']) | set(workflow['artifact_metadata'])) if workflow else set()
        saved = {}
        for info in infos:
            _virtual_name(info.filename)
            if info.filename == 'seed.json':
                continue
            with archive.open(info) as source:
                data = source.read(cloud_runtime.MAX_MEMBER + 1)
            expected = manifest['members'][info.filename]
            _require(cloud_runtime.pin(data) == {k: expected[k] for k in ('bytes', 'sha256')},
                     'seed member identity differs')
            if info.filename.startswith(prefix):
                selected[info.filename[len(prefix):]] = data
            if info.filename in (row['source_bundle'], row['source_seal'], row['artifact_metadata']) or info.filename in provenance_names:
                saved[info.filename] = data
        cloud_runtime.validate_workflow_provenance(manifest, lambda name: saved[name])
    bundle = saved[row['source_bundle']]
    seal = json.loads(saved[row['source_seal']])
    metadata = json.loads(saved[row['artifact_metadata']])
    _require(seal.get('format') == 'rove4k.source-bundle-seal.v1'
             and seal.get('ci_context') == manifest['source_origin']
             and seal.get('producer') == {'ID': 'ubuntu', 'VERSION_ID': '24.04'}
             and seal.get('bundle_format') == 'zip' and seal.get('bundle') == cloud_runtime.pin(bundle),
             'source bundle seal differs')
    with zipfile.ZipFile(io.BytesIO(bundle)) as z:
        for info in z.infolist():
            _virtual_name(info.filename)
    nested = seed.archive_members(bundle)
    _require(seal.get('members') == {name: cloud_runtime.pin(value[0]) for name, value in sorted(nested.items())},
             'sealed complete member map differs')
    profiles = [p for p in seal.get('profiles', []) if (p.get('family'), p.get('profile')) == (family, profile)]
    _require(len(profiles) == 1 and profiles[0].get('archive_prefix') == 'build'
             and profiles[0].get('full') is True and profiles[0].get('representation') == 'source-jit',
             'sealed profile differs')
    _require(set(nested) == {'build/' + name for name in selected} and
             all(nested['build/' + name][0] == data for name, data in selected.items()),
             'selected seed build differs from complete sealed bundle')
    for name in selected:
        diagnostic_candidates._check_path_components(output / name)
    _require(all(k in selected for k in ('build.json', 'main.c', 'x', 'native/x')), 'build closure incomplete')
    build_manifest = json.loads(selected['build.json'])
    _require(profiles[0]['input_manifest'] == cloud_runtime.pin(selected['build.json']), 'build report pin differs')
    expected = build_manifest['expected_contract']
    _require(profiles[0]['old_expected_contract'] == expected, 'producer expected contract differs')
    for name, key in (('main.c', 'source'), ('native/x', 'native'), ('x', 'whole')):
        _require(cloud_runtime.pin(selected[name]) == {'bytes': expected[key + '_bytes'],
                 'sha256': expected[key + '_sha256']}, 'source/whole/native seal differs')
    b_static = _b_static_evidence(family=family, profile=profile, selected=selected,
                                  build_manifest=build_manifest, report=report, legacy=legacy_b_diagnostic)
    if b_static is not None and b_static['mode'] == 'sealed-static-correlated':
        _require('__rove_b_producer_observation__.json' not in selected,
                 'producer observation destination conflicts with the sealed source')
    output.mkdir(mode=0o700)
    for name, data in sorted(selected.items()):
        cloud_runtime.write_new(output / name, data, manifest['members'][prefix + name]['mode'])
    if b_static is not None and b_static['mode'] == 'sealed-static-correlated':
        producer_copy = output / '__rove_b_producer_observation__.json'
        cloud_runtime.write_new(producer_copy, report_raw, 0o600)
    admitted = diagnostic_candidates._profile_verifier().admit_c_build(build_manifest, output)
    _require((admitted.family, admitted.profile_id, admitted.representation, admitted.full) ==
             (family, profile, 'source-jit', True), 'restored source profile differs')
    resources = admitted.resources
    whole, source, native = (output / admitted.program, output / admitted.source, output / admitted.native)
    artifact = registry.Artifact(id=f"{family}-{profile}-{expected['whole_sha256'][:8]}-{expected['native_sha256'][:8]}",
        family=family, path=whole, purpose='test', profile=profile, workers=resources['workers'],
        tt_bytes=resources['tt_bytes'], entry_bytes=resources['tt_entry_bytes'], representation='source-jit',
        full=True, sha256=expected['whole_sha256'], whole_bytes=expected['whole_bytes'],
        native_sha256=expected['native_sha256'])
    if report is not None:
        _report_matches(report, manifest, row, seal, metadata, artifact)
    def pin_path(path):
        return {'path': str(path), **cloud_runtime.pin(cloud_runtime.ordinary(path, limit=256 << 20))}
    candidate = {'artifact': {**artifact.identity(), 'path': str(whole)}, 'source': pin_path(source),
                 'native': pin_path(native), 'evidence': {'kind': 'rove-profile-build-v1',
                                                          'build': pin_path(output / 'build.json')}}
    if b_static is not None:
        candidate['evidence'].update(b_static_mode=b_static['mode'], b_static_files=b_static['static_files'],
            b_producer_report=pin_path(producer_copy) if b_static['mode'] == 'sealed-static-correlated' else None)
    value = {'format': 'rove4k-diagnostic-candidate-set-v1', 'profile': profile, 'candidates': [candidate]}
    target = output / 'candidate.json'
    pin = cloud_runtime.json_new(target, value)
    checked, digest = diagnostic_candidates.read_candidates(target, pin['sha256'], profile, allow_single=True)
    _require(len(checked) == 1 and checked[0]['artifact'].id == artifact.id and digest == pin['sha256'],
             'candidate failed exact diagnostic replay')
    if b_static is not None:
        _require(checked[0]['evidence'].get('b_static_mode') == b_static['mode'],
                 'B diagnostic candidate static mode differs from seed')
    if b_static is not None and b_static['mode'] == 'sealed-static-correlated':
        _require(checked[0]['evidence'].get('b_static_correlation') == b_static['static_correlation'],
                 'B diagnostic candidate static correlation differs from sealed producer')
    return {'format': 'rove4k-rove-diagnostic-preparation-v1', 'candidate': {'path': str(target), **pin},
            'seed_archive_sha256': archive_sha256, 'seed_manifest_sha256': manifest_sha256,
            'producer_report_sha256': producer_report_sha256, 'artifact_id': artifact.id,
            'source_contract_verified': True, 'producer_report_matches_seed': report is not None,
            'producer_report_authenticated': False, 'source_to_native_proven': False,
            'b_static_evidence': b_static,
            'runtime_qualified': False, 'authorizes_go': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('archive-path', 'archive-sha256', 'manifest-sha256', 'family', 'profile', 'out'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--producer-report')
    p.add_argument('--producer-report-sha256')
    p.add_argument('--legacy-b-diagnostic', action='store_true')
    print(json.dumps(prepare(**vars(p.parse_args())), sort_keys=True))


if __name__ == '__main__':
    main()
