"""Observe a P16/P192 source artifact against GitHub and a pinned seed.

This is source-transport evidence, not host ownership, a runtime result,
budget authority, or permission to send GO.  The GitHub REST artifact schema
does not identify an upload job directly; the workflow's unique source job
name and successful seal/upload steps provide the correlation checked here.
The caller must separately pin and review the producer workflow commit.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

try:
    from . import cloud_runtime as cloud, seed
except ImportError:
    import cloud_runtime as cloud
    import seed

_REPO = 'daejunnom/Rove4k'
_WORKFLOW = '.github/workflows/league-profile-bootstrap.yml'
_HEX = re.compile(r'[0-9a-f]{64}\Z')
_SHA = re.compile(r'[0-9a-f]{40}\Z')
_DEC = re.compile(r'[1-9][0-9]{0,19}\Z')
_VARIANT = re.compile(r'[a-z0-9][a-z0-9-]{0,63}\Z')
_MAX_JSON = 8 << 20
_MAX_ARCHIVE = 128 << 20
_MAX_EXPANDED = 512 << 20
_MAX_FILES = 10000
_NO_SECRETS = re.compile(r'credential|service[-_ ]?account|api[-_ ]?key|ssh[-_ ]?key|private[-_ ]?key|password|secret|^id_(rsa|ed25519|dsa|ecdsa)$|^token(?:\.|$)|[_-]token$', re.I)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _decimal(value):
    _require(type(value) in (int, str) and _DEC.fullmatch(str(value)) is not None, 'positive canonical ID required')
    return int(value)


def _json(raw):
    _require(type(raw) is bytes and len(raw) <= _MAX_JSON, 'bounded API JSON bytes required')
    def unique(pairs):
        out = {}
        for key, value in pairs:
            _require(key not in out, 'duplicate JSON member')
            out[key] = value
        return out
    def bad(_):
        raise ValueError('non-finite JSON number')
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=bad)
    _require(type(value) is dict, 'JSON object required')
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _read_response(request, limit):
    # Never automatically forward a bearer token to a redirect destination.
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(request, timeout=20) as response:
        _require(response.status == 200, 'unexpected GitHub response status')
        raw = response.read(limit + 1)
    _require(len(raw) <= limit, 'GitHub response exceeds bound')
    return raw


def _api_headers():
    token = os.environ.get('GH_TOKEN', '')
    _require(bool(token), 'GitHub workflow token required')
    return {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'Rove4k-producer-observer'}


def _gh_endpoint(path):
    """Allow only the fixed read-only endpoints used by this observer."""
    prefix = '/repos/' + _REPO + '/'
    _require(type(path) is str and path.startswith(prefix), 'fixed GitHub endpoint required')
    tail = path[len(prefix):]
    digit = r'[1-9][0-9]{0,19}'
    patterns = (
        r'actions/runs/' + digit + r'/attempts/' + digit,
        r'actions/runs/' + digit + r'/attempts/' + digit + r'/jobs\?per_page=100&page=' + digit,
        r'actions/runs/' + digit + r'/artifacts\?per_page=100&page=' + digit,
        r'actions/artifacts/' + digit + r'(?:/zip)?',
        r'git/commits/[0-9a-f]{40}',
        r'pulls/' + digit,
    )
    _require(any(re.fullmatch(pattern, tail) for pattern in patterns), 'fixed GitHub endpoint required')
    return path


def _gh_read(path, limit, *, timeout=30):
    """Read bounded bytes using gh's existing authentication, never its token."""
    _gh_endpoint(path)
    _require(type(limit) is int and 0 < limit <= _MAX_ARCHIVE, 'invalid response limit')
    _require(type(timeout) in (int, float) and 0 < timeout <= 300, 'invalid response timeout')
    # Linux first; Windows gh.exe may also be on PATH under WSL.  Do not
    # switch accounts after an authentication error from an existing gh.
    proc = None
    for executable in ('gh', 'gh.exe'):
        try:
            proc = subprocess.Popen([executable, 'api', '--hostname', 'github.com', '--method', 'GET', path],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            break
        except FileNotFoundError:
            continue
        except OSError:
            raise RuntimeError('GitHub CLI observation failed') from None
    if proc is None:
        raise RuntimeError('GitHub CLI observation failed')
    deadline = time.monotonic() + timeout
    output = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise RuntimeError('GitHub CLI observation timed out')
                data = os.read(proc.stdout.fileno(), min(65536, limit + 1 - len(output)))
                if not data:
                    break
                output.extend(data)
                _require(len(output) <= limit, 'GitHub response exceeds bound')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError('GitHub CLI observation timed out')
        try:
            status = proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            raise RuntimeError('GitHub CLI observation timed out') from None
        if status != 0:
            raise RuntimeError('GitHub CLI observation failed')
        return bytes(output)
    except OSError:
        raise RuntimeError('GitHub CLI observation failed') from None
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        proc.stdout.close()


def _gh_api_json(path):
    return _json(_gh_read(path, _MAX_JSON))


def _gh_api_archive(artifact_id):
    artifact_id = _decimal(artifact_id)
    return _gh_read('/repos/' + _REPO + '/actions/artifacts/' + str(artifact_id) + '/zip', _MAX_ARCHIVE)


def _api_json(path):
    prefix = '/repos/' + _REPO + '/'
    _require(path.startswith(prefix) and not any(c in path for c in '\r\n#') and
             (path.startswith(prefix + 'actions/') or re.fullmatch(re.escape(prefix) + r'git/commits/[0-9a-f]{40}', path)
              or re.fullmatch(re.escape(prefix) + r'pulls/[1-9][0-9]{0,19}', path)),
             'fixed repository Actions endpoint required')
    return _json(_read_response(urllib.request.Request('https://api.github.com' + path, headers=_api_headers()), _MAX_JSON))


def _storage_url(value):
    parsed = urllib.parse.urlsplit(value)
    host = (parsed.hostname or '').lower()
    _require(parsed.scheme == 'https' and parsed.username is None and parsed.password is None
             and parsed.port in (None, 443) and not parsed.fragment
             and any(host.endswith('.' + suffix) for suffix in
                     ('blob.core.windows.net', 'actions.githubusercontent.com', 'githubusercontent.com')),
             'artifact redirect is not an approved HTTPS storage host')
    return value


def _api_archive(artifact_id):
    artifact_id = _decimal(artifact_id)
    path = '/repos/' + _REPO + '/actions/artifacts/' + str(artifact_id) + '/zip'
    first = urllib.request.Request('https://api.github.com' + path, headers=_api_headers())
    try:
        return _read_response(first, _MAX_ARCHIVE)
    except urllib.error.HTTPError as exc:
        _require(exc.code in (301, 302, 303, 307, 308), 'artifact download was rejected')
        location = exc.headers.get('Location')
        _require(isinstance(location, str), 'artifact redirect lacks a location')
    # Signed storage URLs are never logged and never receive the API token.
    request = urllib.request.Request(_storage_url(location), headers={'User-Agent': 'Rove4k-producer-observer'})
    try:
        return _read_response(request, _MAX_ARCHIVE)
    except Exception:
        raise RuntimeError('artifact storage request failed') from None


def _safe_name(name, *, directory):
    _require(type(name) is str and name and '\\' not in name and ':' not in name and '\0' not in name,
             'invalid ZIP member name')
    value = name[:-1] if directory and name.endswith('/') else name
    _require(value and not value.startswith('/') and all(part not in ('', '.', '..') for part in value.split('/')),
             'ZIP member escaped its namespace')
    blocked = {'.git', '.aws', '.ssh', 'node_modules', 'dist', 'dist-server', 'coverage', 'models',
               'checkpoints', '.cache', 'inventory.json', 'package-lock.json', '.npmrc', '.pypirc', '.netrc'}
    _require(not any(part.casefold() in blocked or part.casefold().startswith('.env') or _NO_SECRETS.search(part)
                     or part.casefold().endswith(('.pem', '.key', '.p12', '.pfx')) for part in value.split('/')),
             'protected ZIP path')
    return value


def _zip_members(raw, wanted, *, limit=_MAX_ARCHIVE):
    """Preflight every member before reading only explicitly selected files."""
    _require(type(raw) is bytes and len(raw) <= limit, 'bounded ZIP bytes required')
    _require(type(wanted) is set and wanted, 'explicit selected ZIP members required')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        _require(len(infos) <= _MAX_FILES, 'too many ZIP members')
        seen, files, directories, total = set(), {}, set(), 0
        for info in infos:
            directory = info.is_dir()
            name = _safe_name(info.filename, directory=directory)
            mode = info.external_attr >> 16
            kind = stat.S_IFMT(mode)
            _require(name not in seen and not info.flag_bits & 1 and
                     kind in ((0, stat.S_IFDIR) if directory else (0, stat.S_IFREG)),
                     'duplicate, encrypted, linked or nonregular ZIP member')
            seen.add(name)
            total += info.file_size
            _require(0 <= info.file_size <= _MAX_ARCHIVE and total <= _MAX_EXPANDED,
                     'ZIP expansion exceeds bound')
            if directory:
                directories.add(name)
            else:
                files[name] = info
        for name in files:
            _require(not any('/'.join(name.split('/')[:i]) in files for i in range(1, len(name.split('/')))),
                     'ZIP file/directory collision')
        _require(wanted <= files.keys(), 'required ZIP member is missing')
        result = {}
        for name in sorted(wanted):
            data = archive.read(files[name])
            _require(len(data) == files[name].file_size, 'ZIP member length differs')
            result[name] = data
    return result


def _pages(path, key, get):
    rows, ids, total = [], set(), None
    for page in range(1, 101):
        value = get(path + '?per_page=100&page=' + str(page))
        current, items = value.get('total_count'), value.get(key)
        _require(type(current) is int and 0 <= current <= _MAX_FILES and type(items) is list
                 and len(items) <= 100 and (total is None or total == current), 'invalid job pagination')
        total = current
        for item in items:
            _require(type(item) is dict and type(item.get('id')) is int and item['id'] > 0 and item['id'] not in ids,
                     'duplicate or invalid job')
            ids.add(item['id'])
            rows.append(item)
        _require(len(rows) <= total, 'job count exceeds total')
        if len(rows) == total:
            return rows
        _require(len(items) == 100, 'incomplete job pagination')
    raise ValueError('job pagination exceeded bound')


def _all_jobs(run_id, attempt, get):
    return _pages('/repos/' + _REPO + '/actions/runs/' + str(run_id) + '/attempts/' + str(attempt) + '/jobs', 'jobs', get)


def _member_bytes(manifest, root, name):
    _safe_name(name, directory=False)
    cloud.member(name)
    expected = manifest['members'].get(name)
    _require(type(expected) is dict, 'selected seed member absent')
    data = cloud.ordinary(Path(root) / name, limit=_MAX_ARCHIVE)
    _require(cloud.pin(data) == {k: expected[k] for k in ('bytes', 'sha256')}, 'seed member pin differs')
    return data


def _safe_absolute_file(path):
    path = Path(path)
    _require(path.is_absolute() and len(path.parts) > 1, 'absolute evidence file required')
    _safe_name('/'.join(path.parts[1:]), directory=False)
    return path


def _candidate_record(request, candidate_path, family):
    _require(type(request.candidates_sha256) is str and _HEX.fullmatch(request.candidates_sha256),
             'pinned candidate manifest required')
    raw = cloud.ordinary(_safe_absolute_file(candidate_path), limit=_MAX_JSON)
    _require(hashlib.sha256(raw).hexdigest() == request.candidates_sha256, 'candidate manifest differs')
    value = _json(raw)
    _require(value.get('format') == 'rove4k-diagnostic-candidate-set-v1'
             and value.get('profile') == request.profile and type(value.get('candidates')) is list,
             'named candidate set required')
    selected = [x for x in value['candidates'] if type(x) is dict and type(x.get('artifact')) is dict
                and x['artifact'].get('id') == request.artifact_id]
    _require(len(selected) == 1 and selected[0]['artifact'].get('family') == family
             and selected[0]['artifact'].get('profile') == request.profile
             and selected[0]['artifact'].get('representation') == 'source-jit'
             and selected[0]['artifact'].get('full') is True, 'candidate identity differs')
    return selected[0]


def _live_pr_merge(manifest, run, get):
    """Bind a simple PR merge to the current authenticated GitHub snapshots.

    An old base/head or changed merge is deliberately rejected. This checks
    transport identity only; it does not establish trusted workflow behavior.
    """
    proof = manifest.get('workflow_provenance')
    _require(type(proof) is dict and proof.get('kind') == 'pull-request-merge',
             'simple PR producer proof required')
    origin = manifest['source_origin']
    repo = run['repository']
    _require(proof.get('event') == 'pull_request' and proof.get('repository') == _REPO
             and proof.get('repository_id') == repo['id'] and _decimal(proof.get('run_id')) == _decimal(origin['run_id'])
             and _decimal(proof.get('run_attempt')) == _decimal(origin['run_attempt'])
             and proof.get('checkout_sha') == origin['head_sha'] and proof.get('api_head_sha') == run['head_sha'],
             'seed PR run identity differs')
    number = _decimal(proof.get('pull_request'))
    commit = get('/repos/' + _REPO + '/git/commits/' + origin['head_sha'])
    pull = get('/repos/' + _REPO + '/pulls/' + str(number))
    tree, parents = commit.get('tree'), commit.get('parents')
    _require(commit.get('sha') == origin['head_sha'] and type(tree) is dict and _SHA.fullmatch(str(tree.get('sha')))
             and type(parents) is list and len(parents) == 2 and all(type(p) is dict and _SHA.fullmatch(str(p.get('sha'))) for p in parents),
             'live merge commit identity differs')
    parent_shas = [p['sha'] for p in parents]
    _require(proof.get('execution_tree') == tree['sha'] and proof.get('execution_parents') == parent_shas
             and parent_shas[1] == run['head_sha'] and pull.get('number') == number
             and pull.get('merge_commit_sha') == origin['head_sha'], 'PR merge tree or parents changed')
    base, head, rows, head_repo = pull.get('base'), pull.get('head'), run.get('pull_requests'), run.get('head_repository')
    _require(type(base) is dict and type(head) is dict and type(base.get('repo')) is dict and type(head.get('repo')) is dict
             and type(head_repo) is dict and type(rows) is list and len(rows) == 1 and type(rows[0]) is dict
             and rows[0].get('number') == number and all(type(rows[0].get(side)) is dict
                 and type(rows[0][side].get('repo')) is dict for side in ('base', 'head')),
             'live PR snapshots are incomplete')
    _require(base['repo'].get('full_name') == _REPO and base['repo'].get('id') == repo['id']
             and base.get('sha') == parent_shas[0] and head.get('sha') == parent_shas[1]
             and type(head['repo'].get('id')) is int and head['repo']['id'] > 0
             and type(head['repo'].get('full_name')) is str
             and re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', head['repo']['full_name'])
             and head['repo'].get('id') == head_repo.get('id') == proof.get('head_repository_id')
             and head['repo'].get('full_name') == head_repo.get('full_name')
             and type(head.get('ref')) is str and head['ref'] and head['ref'] == run.get('head_branch') == proof.get('head_branch')
             and type(base.get('ref')) is str and base['ref']
             and all(rows[0][side].get('sha') == value.get('sha') and rows[0][side].get('ref') == value.get('ref')
                     and rows[0][side]['repo'].get('id') == value['repo'].get('id')
                     for side, value in (('base', base), ('head', head))), 'live PR source, base or repositories differ')
    return True


def _inspect(request, *, seed_root, candidate_path, family, variant, get, archive):
    _require(request.repository == _REPO and family in tuple('ABCEF') and request.profile in ('test-p16', 'test-p192')
             and type(variant) is str and _VARIANT.fullmatch(variant), 'explicit supported producer selection required')
    run_id, attempt, artifact_id = map(_decimal, (request.producer_run_id, request.producer_run_attempt,
                                                   request.producer_artifact_id))
    _require(type(request.seed_manifest_sha256) is str and _HEX.fullmatch(request.seed_manifest_sha256)
             and type(request.source_head) is str and _SHA.fullmatch(request.source_head), 'pinned seed and source required')
    root = _safe_absolute_file(seed_root)
    raw_manifest = cloud.ordinary(root / 'seed.json', limit=_MAX_JSON)
    _require(hashlib.sha256(raw_manifest).hexdigest() == request.seed_manifest_sha256, 'seed manifest changed')
    manifest = _json(raw_manifest)
    cloud.validate_seed_manifest(manifest)
    origin = manifest['source_origin']
    _require(origin['repository'] == _REPO and origin['head_sha'] == request.source_head
             and _decimal(origin['run_id']) == run_id and _decimal(origin['run_attempt']) == attempt,
             'seed source origin differs')
    selection = [x for x in manifest['rove'] if (x['family'], x['profile']) == (family, request.profile)]
    _require(len(selection) == 1, 'seed producer selection is ambiguous')
    row = selection[0]
    candidate = _candidate_record(request, candidate_path, family)
    read = lambda name: _member_bytes(manifest, root, name)
    metadata = _json(read(row['artifact_metadata']))
    bundle, seal = read(row['source_bundle']), read(row['source_seal'])
    seal_json = _json(seal)
    _require(seal_json.get('format') == 'rove4k.source-bundle-seal.v1' and seal_json.get('ci_context') == origin
             and seal_json.get('bundle') == cloud.pin(bundle), 'seed source seal differs')
    profiles = [x for x in seal_json.get('profiles', []) if (x.get('family'), x.get('profile')) == (family, request.profile)]
    _require(len(profiles) == 1 and profiles[0].get('archive_prefix') == 'build', 'sealed profile differs')
    run = get('/repos/' + _REPO + '/actions/runs/' + str(run_id) + '/attempts/' + str(attempt))
    repo, head_repo = run.get('repository'), run.get('head_repository')
    _require(type(repo) is dict and repo.get('full_name') == _REPO and type(repo.get('id')) is int
             and repo['id'] > 0 and run.get('id') == run_id and run.get('run_attempt') == attempt
             and run.get('status') == 'completed' and run.get('conclusion') == 'success'
             and str(run.get('path', '')).split('@', 1)[0] == _WORKFLOW
             and type(head_repo) is dict and type(head_repo.get('id')) is int and head_repo['id'] > 0
             and type(run.get('head_branch')) is str and run['head_branch']
             and type(run.get('head_sha')) is str and _SHA.fullmatch(run['head_sha']), 'producer run identity differs')
    # PR head SHA and checkout merge SHA legitimately differ; existing Git
    # proof ties the two. Its pinned inputs are NOT themselves authenticated.
    if run.get('event') == 'pull_request':
        if manifest.get('workflow_provenance', {}).get('kind') == 'pull-request-merge':
            _live_pr_merge(manifest, run, get)
        else:
            provenance = cloud.validate_workflow_provenance(manifest, read)
            head_repo, rows = run.get('head_repository'), run.get('pull_requests')
            _require(provenance is not None and provenance['api_head_sha'] == run['head_sha']
                     and provenance['repository_id'] == repo['id'] and type(head_repo) is dict
                     and type(head_repo.get('id')) is int and head_repo['id'] > 0
                     and head_repo.get('id') == provenance.get('head_repository_id')
                     and type(run.get('head_branch')) is str and run['head_branch']
                     and run.get('head_branch') == provenance.get('head_branch')
                     and type(rows) is list and len(rows) == 1 and type(rows[0]) is dict
                     and rows[0].get('number') == provenance.get('pull_request')
                     and type(rows[0].get('head')) is dict and type(rows[0].get('base')) is dict
                     and type(rows[0]['head'].get('repo')) is dict and type(rows[0]['base'].get('repo')) is dict
                     and rows[0]['head'].get('sha') == run['head_sha']
                     and rows[0]['head']['repo'].get('id') == head_repo.get('id')
                     and rows[0]['head'].get('ref') == provenance.get('head_branch')
                     and rows[0]['base'].get('sha') == provenance.get('reported_base_sha')
                     and rows[0]['base']['repo'].get('id') == repo['id']
                     and type(rows[0]['base'].get('ref')) is str and rows[0]['base']['ref']
                     and 'refs/heads/' + rows[0]['base']['ref'] == provenance.get('base_ref'),
                     'PR source provenance is absent or differs')
    else:
        _require(run.get('event') in ('push', 'workflow_dispatch') and run['head_sha'] == request.source_head,
                 'non-PR producer checkout differs')
    job_name = 'source-' + family + '-' + request.profile + '-' + variant
    jobs = [x for x in _all_jobs(run_id, attempt, get) if x.get('name') == job_name]
    _require(len(jobs) == 1 and jobs[0].get('run_id') == run_id and jobs[0].get('status') == 'completed'
             and jobs[0].get('head_sha') == run['head_sha'] and jobs[0].get('conclusion') == 'success',
             'exact source job was not uniquely successful')
    steps = jobs[0].get('steps')
    _require(type(steps) is list, 'source job steps missing')
    for step_name in ('Seal the admitted source for P16 and P192 seed transport',
                      'Preserve actual artifacts, bounded command logs and failures'):
        hits = [s for s in steps if type(s) is dict and s.get('name') == step_name]
        _require(len(hits) == 1 and hits[0].get('status') == 'completed' and hits[0].get('conclusion') == 'success',
                 'source sealing or artifact upload was not successful')
    artifact = get('/repos/' + _REPO + '/actions/artifacts/' + str(artifact_id))
    name = 'league-source-' + family + '-' + request.profile + '-' + variant + '-' + request.source_head + '-' + str(attempt)
    listed = _pages('/repos/' + _REPO + '/actions/runs/' + str(run_id) + '/artifacts', 'artifacts', get)
    matches = [item for item in listed if item.get('name') == name]
    _require(len(matches) == 1 and matches[0].get('id') == artifact_id,
             'artifact name was not unique within the producer run')
    ref = artifact.get('workflow_run')
    saved_ref = metadata.get('workflow_run')
    _require(artifact.get('id') == artifact_id and metadata.get('id') == artifact_id
             and artifact.get('name') == metadata.get('name') == name and artifact.get('expired') is False
             and type(ref) is dict and ref.get('id') == run_id and ref.get('repository_id') == repo['id']
             and ref.get('head_sha') == run['head_sha'] and ref.get('head_repository_id') == head_repo['id']
             and ref.get('head_branch') == run['head_branch'] and type(saved_ref) is dict
             and all(saved_ref.get(key) == ref.get(key) for key in
                     ('id', 'repository_id', 'head_sha', 'head_repository_id', 'head_branch')),
             'artifact identity or run differs')
    digest = artifact.get('digest')
    _require(type(digest) is str and re.fullmatch(r'sha256:[0-9a-f]{64}', digest)
             and metadata.get('digest') == digest, 'artifact digest absent or differs from seed metadata')
    data = archive(artifact_id)
    _require(type(data) is bytes and hashlib.sha256(data).hexdigest() == digest[7:], 'artifact ZIP digest differs')
    selected = {'source-bundle.zip', 'source-seal.json', 'build/build.json', 'build/main.c', 'build/native/x', 'build/x'}
    outer = _zip_members(data, selected)
    _require(outer['source-bundle.zip'] == bundle and outer['source-seal.json'] == seal,
             'artifact transport files differ from seed')
    build = row['build']
    for item in ('build.json', 'main.c', 'native/x', 'x'):
        _require(outer['build/' + item] == read(build + '/' + item), 'artifact build member differs from seed')
    whole, source, native = (cloud.pin(outer[name]) for name in ('build/x', 'build/main.c', 'build/native/x'))
    _require(candidate['artifact'].get('sha256') == whole['sha256']
             and candidate['artifact'].get('whole_bytes') == whole['bytes']
             and candidate['artifact'].get('native_sha256') == native['sha256']
             and type(candidate.get('source')) is dict and type(candidate.get('native')) is dict
             and all(candidate['source'].get(key) == source[key] and candidate['native'].get(key) == native[key]
                     for key in ('bytes', 'sha256')), 'candidate pins differ from producer build')
    nested = _zip_members(bundle, {'build/build.json', 'build/main.c', 'build/native/x', 'build/x'})
    _require(all(nested[name] == outer[name] for name in nested), 'source bundle build differs from artifact')
    # `_zip_members` has already preflighted every nested name and type with
    # the stronger protected-path policy before the shared collector reads it.
    expanded = seed.archive_members(bundle)
    _require(seal_json.get('members') == {name: cloud.pin(value[0]) for name, value in sorted(expanded.items())},
             'source seal does not match the complete bundle member map')
    return {'format': 'rove4k.github-source-observation-v1', 'repository': _REPO, 'run_id': run_id,
            'run_attempt': attempt, 'artifact_id': artifact_id, 'job_id': jobs[0]['id'],
            'source_head': request.source_head, 'api_head': run['head_sha'], 'family': family,
            'profile': request.profile, 'variant': variant, 'artifact_sha256': digest[7:],
            'source_bundle_sha256': hashlib.sha256(bundle).hexdigest(),
            'source_seal_sha256': hashlib.sha256(seal).hexdigest(),
            'candidate_pins_match': True, 'candidate_files_observed': False,
            'workflow_commit_reviewed': False, 'host_authenticated': False,
            'runtime_qualified': False, 'authorizes_go': False}


def observe_github(request, *, seed_root, candidate_path, family, variant):
    """Read GitHub over HTTPS; direct source evidence only, never GO authority."""
    _require(sys.platform == 'linux', 'raw ZIP path verification requires Linux')
    return _inspect(request, seed_root=seed_root, candidate_path=candidate_path, family=family, variant=variant,
                    get=_api_json, archive=_api_archive)


def observe_github_via_gh(request, *, seed_root, candidate_path, family, variant):
    """Read via gh's existing authentication without accessing token values."""
    _require(sys.platform == 'linux', 'raw ZIP path verification requires Linux')
    return _inspect(request, seed_root=seed_root, candidate_path=candidate_path, family=family, variant=variant,
                    get=_gh_api_json, archive=_gh_api_archive)
