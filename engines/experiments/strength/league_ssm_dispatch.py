"""One-shot SSM transport for a pinned, non-scoring league diagnostic.

The caller MUST supply a live authority adapter which verifies the current
controller, owned instance, immutable seed provenance, budget and launch
policy. No such production adapter is supplied here: a ping, a hash, or a
serialized flag is not authority. This module never launches or terminates an
instance or authorizes a scored game. The durable journal fences replay only
for one journal owner, not for another controller or a different host. The
producer, version and boot fields are declarations bound to request bytes;
their presence is not authentication or proof of a fetched S3 version.
Rove artifact metadata and upstream peer source/build provenance use distinct
request and receipt formats. Neither format grants live authority.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
import shlex

try:
    from . import campaign, ledger
except ImportError:
    import campaign
    import ledger

_HEX = re.compile(r'[0-9a-f]{64}\Z')
_GIT = re.compile(r'[0-9a-f]{40}\Z')
_INSTANCE = re.compile(r'i-[0-9a-f]{17}\Z')
_ACCOUNT = re.compile(r'[0-9]{12}\Z')
_REGION = re.compile(r'[a-z]{2}(?:-gov)?-[a-z]+-[0-9]+\Z')
_DECIMAL = re.compile(r'[1-9][0-9]{0,19}\Z')
_BOOT = re.compile(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\Z')


def _validate_common(request):
    for item in (request.campaign_id, request.job_id):
        ledger.valid_id(item)
    if (len(request.job_id) > 93 or not isinstance(request.instance_id, str) or not _INSTANCE.fullmatch(request.instance_id)
            or not isinstance(request.account_id, str) or not _ACCOUNT.fullmatch(request.account_id)
            or not isinstance(request.region, str) or not _REGION.fullmatch(request.region)
            or not isinstance(request.source_head, str) or not _GIT.fullmatch(request.source_head)
            or not isinstance(request.seed_manifest_sha256, str) or not _HEX.fullmatch(request.seed_manifest_sha256)
            or not isinstance(request.artifact_bucket, str)
            or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', request.artifact_bucket)
            or request.repository != 'daejunnom/Rove4k'
            or any(not isinstance(value, str) or not _DECIMAL.fullmatch(value) for value in
                   (request.producer_run_id, request.producer_run_attempt))
            or not isinstance(request.seed_bucket, str)
            or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', request.seed_bucket)
            or not isinstance(request.seed_key, str) or not request.seed_key.startswith(request.campaign_id + '/seed/')
            or len(request.seed_key.encode('utf-8', 'surrogatepass')) > 1024
            or any(part in ('', '.', '..') for part in request.seed_key.split('/'))
            or any(ord(char) < 32 or 127 <= ord(char) < 160 or 0xd800 <= ord(char) <= 0xdfff
                   for char in request.seed_key)
            or not isinstance(request.seed_version_id, str) or request.seed_version_id in ('', 'null')
            or len(request.seed_version_id) > 1024
            or any(ord(char) < 32 or 127 <= ord(char) < 160 or 0xd800 <= ord(char) <= 0xdfff
                   for char in request.seed_version_id)
            or len(request.seed_version_id.encode('utf-8')) > 1024
            or not isinstance(request.seed_archive_sha256, str) or not _HEX.fullmatch(request.seed_archive_sha256)
            or type(request.seed_archive_bytes) is not int or not 0 < request.seed_archive_bytes <= 128 << 20
            or not isinstance(request.boot_id, str) or not _BOOT.fullmatch(request.boot_id)
            or request.boot_id == '00000000-0000-0000-0000-000000000000'
            or request.profile not in ('test-p16', 'test-p192')
            or type(request.wall_seconds) is not int or not 90 <= request.wall_seconds <= 300):
        raise ValueError('exact account, instance, seed and bounded P16/P192 request required')


@dataclass(frozen=True)
class Request:
    campaign_id: str
    job_id: str
    instance_id: str
    account_id: str
    region: str
    seed_manifest_sha256: str
    source_head: str
    candidates_sha256: str
    profile: str
    artifact_id: str
    artifact_bucket: str
    repository: str
    producer_run_id: str
    producer_run_attempt: str
    producer_artifact_id: str
    seed_bucket: str
    seed_key: str
    seed_version_id: str
    seed_archive_sha256: str
    seed_archive_bytes: int
    boot_id: str
    wall_seconds: int = 120

    def __post_init__(self):
        _validate_common(self)
        ledger.valid_id(self.artifact_id)
        if (not isinstance(self.candidates_sha256, str) or not _HEX.fullmatch(self.candidates_sha256)
                or not isinstance(self.producer_artifact_id, str) or not _DECIMAL.fullmatch(self.producer_artifact_id)):
            raise ValueError('exact Rove candidate and artifact identity required')

    def record(self):
        return {'format': 'rove4k-ssm-functional-request-v2', 'campaign_id': self.campaign_id,
                'job_id': self.job_id, 'instance_id': self.instance_id, 'account_id': self.account_id,
                'region': self.region, 'seed_manifest_sha256': self.seed_manifest_sha256,
                'source_head': self.source_head, 'candidates_sha256': self.candidates_sha256,
                'profile': self.profile, 'artifact_id': self.artifact_id,
                'artifact_bucket': self.artifact_bucket, 'repository': self.repository,
                'producer_run_id': self.producer_run_id, 'producer_run_attempt': self.producer_run_attempt,
                'producer_artifact_id': self.producer_artifact_id, 'seed_bucket': self.seed_bucket,
                'seed_key': self.seed_key, 'seed_version_id': self.seed_version_id,
                'seed_archive_sha256': self.seed_archive_sha256, 'seed_archive_bytes': self.seed_archive_bytes,
                'boot_id': self.boot_id, 'wall_seconds': self.wall_seconds}


@dataclass(frozen=True)
class PeerRequest:
    """Pinned peer upstream identity; candidate is generated on the host."""
    campaign_id: str
    job_id: str
    instance_id: str
    account_id: str
    region: str
    seed_manifest_sha256: str
    source_head: str
    profile: str
    artifact_bucket: str
    repository: str
    producer_run_id: str
    producer_run_attempt: str
    seed_bucket: str
    seed_key: str
    seed_version_id: str
    seed_archive_sha256: str
    seed_archive_bytes: int
    boot_id: str
    family: str
    upstream_repository: str
    upstream_revision: str
    wall_seconds: int = 120
    preparation_seconds: int = 3600

    def __post_init__(self):
        _validate_common(self)
        try:
            from . import peers
        except ImportError:
            import peers
        spec = peers.peer_spec(self.family)
        if (self.upstream_repository != spec.repository or self.upstream_revision != spec.revision
                or type(self.preparation_seconds) is not int or not 600 <= self.preparation_seconds <= 7200):
            raise ValueError('exact pinned upstream peer and bounded preparation time required')

    def record(self):
        return {'format': 'rove4k-ssm-peer-request-v1', **self.__dict__}


def bootstrap_loader_manifest_sha256(pins):
    """Canonical identity of the independently declared loader list."""
    try:
        from .league_pinned_bootstrap import LoaderPin
    except ImportError:
        from league_pinned_bootstrap import LoaderPin
    if (type(pins) is not tuple or not 1 <= len(pins) <= 64
            or any(type(pin) is not LoaderPin for pin in pins)
            or len({pin.name for pin in pins}) != len(pins)):
        raise ValueError('bounded distinct loader pins required')
    rows = sorted((asdict(pin) for pin in pins), key=lambda row: row['name'])
    return ledger.digest({'format': 'rove4k-bootstrap-loader-pins-v1', 'loaders': rows})


@dataclass(frozen=True)
class BootstrapEnvelope:
    """Versioned, diagnostic-only binding; none of its assertions is authority."""
    diagnostic: Request | PeerRequest
    bootstrap: object
    expected_bootstrap_sha256: str
    expected_loader_manifest_sha256: str

    def __post_init__(self):
        try:
            from .league_pinned_bootstrap import BootstrapRequest
        except ImportError:
            from league_pinned_bootstrap import BootstrapRequest
        d, b = self.diagnostic, self.bootstrap
        if type(d) not in (Request, PeerRequest) or type(b) is not BootstrapRequest:
            raise ValueError('typed diagnostic and bootstrap request required')
        bindings = ((d.campaign_id, b.campaign), (d.account_id, b.host_account),
            (d.region, b.host_region), (d.instance_id, b.host_instance_id), (d.boot_id, b.host_boot_id),
            (d.profile, b.profile), (d.seed_bucket, b.bucket), (d.seed_key, b.key),
            (d.seed_version_id, b.version_id), (d.seed_archive_sha256, b.archive_sha256),
            (d.seed_archive_bytes, b.archive_bytes), (d.seed_manifest_sha256, b.manifest_sha256),
            (d.repository, b.repository), (d.source_head, b.source_head),
            (d.producer_run_id, b.producer_run_id), (d.producer_run_attempt, b.producer_run_attempt))
        if (any(left != right or type(left) is not type(right) for left, right in bindings)
                or b.loader_pins != tuple(sorted(b.loader_pins, key=lambda pin: pin.name))
                or type(self.expected_bootstrap_sha256) is not str or not _HEX.fullmatch(self.expected_bootstrap_sha256)
                or self.expected_bootstrap_sha256 != b.bootstrap_sha256
                or type(self.expected_loader_manifest_sha256) is not str or not _HEX.fullmatch(self.expected_loader_manifest_sha256)
                or self.expected_loader_manifest_sha256 != bootstrap_loader_manifest_sha256(b.loader_pins)):
            raise ValueError('diagnostic, bootstrap and independent source pins differ')

    def record(self):
        b = asdict(self.bootstrap)
        b['loader_pins'] = sorted(b['loader_pins'], key=lambda row: row['name'])
        return {'format': 'rove4k-ssm-seed-bootstrap-v3', 'diagnostic': self.diagnostic.record(),
                'bootstrap': b, 'expected_bootstrap_sha256': self.expected_bootstrap_sha256,
                'expected_loader_manifest_sha256': self.expected_loader_manifest_sha256}


def parse_bootstrap_diagnostic(raw, *, expected_request_sha256):
    """Parse canonical fake wire with an independent SHA; not authentication."""
    try:
        from .league_pinned_bootstrap import BootstrapRequest, LoaderPin
    except ImportError:
        from league_pinned_bootstrap import BootstrapRequest, LoaderPin
    if type(raw) is not bytes or not 0 < len(raw) <= 512 << 10:
        raise ValueError('bounded canonical diagnostic wire bytes required')
    def unique(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError('duplicate diagnostic wire field')
        return result
    def reject(_value):
        raise ValueError('non-finite diagnostic wire number')
    try:
        record = json.loads(raw, object_pairs_hook=unique, parse_constant=reject)
        if ledger.canonical(record) != raw:
            raise ValueError('noncanonical diagnostic wire')
    except (ValueError, TypeError, UnicodeError, OverflowError):
        raise ValueError('invalid diagnostic bootstrap wire data') from None
    if (type(record) is not dict or set(record) != {'format', 'diagnostic', 'bootstrap',
            'expected_bootstrap_sha256', 'expected_loader_manifest_sha256'}
            or record['format'] != 'rove4k-ssm-seed-bootstrap-v3'
            or type(record['diagnostic']) is not dict or type(record['bootstrap']) is not dict
            or type(expected_request_sha256) is not str or not _HEX.fullmatch(expected_request_sha256)):
        raise ValueError('exact diagnostic bootstrap wire required')
    try:
        if hashlib.sha256(raw).hexdigest() != expected_request_sha256:
            raise ValueError('diagnostic bootstrap wire SHA differs')
    except (TypeError, OverflowError):
        raise ValueError('invalid diagnostic bootstrap wire data') from None
    diagnostic = dict(record['diagnostic'])
    kind = diagnostic.pop('format', None)
    target = {'rove4k-ssm-functional-request-v2': Request,
              'rove4k-ssm-peer-request-v1': PeerRequest}.get(kind)
    if target is None:
        raise ValueError('unsupported diagnostic wire format')
    bootstrap = dict(record['bootstrap'])
    pins = bootstrap.pop('loader_pins', None)
    if type(pins) is not list or any(type(pin) is not dict for pin in pins):
        raise ValueError('canonical loader list required')
    try:
        return BootstrapEnvelope(target(**diagnostic),
            BootstrapRequest(**bootstrap, loader_pins=tuple(LoaderPin(**pin) for pin in pins)),
            record['expected_bootstrap_sha256'], record['expected_loader_manifest_sha256'])
    except (TypeError, KeyError, ValueError):
        raise ValueError('invalid diagnostic bootstrap wire fields') from None


class DiagnosticSSMSink:
    """In-memory fixture only: cannot contact SSM or persist a replay fence."""
    def __init__(self, region):
        if not isinstance(region, str) or not _REGION.fullmatch(region):
            raise ValueError('explicit fixture SSM region required')
        self.region = region
        self._records = []

    @property
    def records(self):
        return [json.loads(item) for item in self._records]


def record_bootstrap_diagnostic(envelope, *, plan, sink, bootstrap_source,
                                expected_bootstrap_sha256, expected_loader_manifest_sha256):
    """Record a non-sending bootstrap intent, never invoke SSM or source code.

    A concrete live verifier and durable journal are still absent; this fixture
    cannot be passed to public dispatch or authorize a launch, game or GO.
    """
    try:
        from .league_controller import LeaguePlan
    except ImportError:
        from league_controller import LeaguePlan
    if type(envelope) is not BootstrapEnvelope or type(plan) is not LeaguePlan or type(sink) is not DiagnosticSSMSink:
        raise ValueError('typed diagnostic envelope, plan and in-memory sink required')
    d, b = envelope.diagnostic, envelope.bootstrap
    hosts = [h for h in plan.hosts if h.launch_token == b.host_launch_token]
    if (len(hosts) != 1 or b.plan_sha256 != plan.sha256 or b.campaign != plan.campaign
            or b.bucket != plan.bucket or b.bucket_region != plan.home_region
            or b.bucket_owner != plan.account or b.host_account != plan.account
            or b.host_region != hosts[0].region or b.profile not in (hosts[0].profile, *hosts[0].later_profiles)
            or sink.region != b.host_region or plan.table.split(':', 5)[3] != plan.home_region
            or plan.watchdog_arn.split(':', 5)[3] != plan.home_region):
        raise ValueError('declared host, home region, plan or fixture SSM region differs')
    if (type(bootstrap_source) is not bytes or not 0 < len(bootstrap_source) <= 512 << 10
            or type(expected_bootstrap_sha256) is not str or not _HEX.fullmatch(expected_bootstrap_sha256)
            or type(expected_loader_manifest_sha256) is not str or not _HEX.fullmatch(expected_loader_manifest_sha256)
            or expected_bootstrap_sha256 != envelope.expected_bootstrap_sha256
            or expected_loader_manifest_sha256 != envelope.expected_loader_manifest_sha256
            or hashlib.sha256(bootstrap_source).hexdigest() != expected_bootstrap_sha256):
        raise ValueError('independently supplied bootstrap or loader pin differs')
    record = envelope.record()
    request_sha = ledger.digest(record)
    if any(json.loads(item)['request_sha256'] == request_sha for item in sink._records):
        raise ValueError('duplicate in-memory diagnostic intent')
    result = {'format': 'rove4k-ssm-bootstrap-intent-v1', 'request_sha256': request_sha,
              'request': record,
              'bootstrap_sha256': envelope.expected_bootstrap_sha256,
              'loader_manifest_sha256': envelope.expected_loader_manifest_sha256,
              'host_region': d.region, 'bucket_region': b.bucket_region,
              'instance_id': d.instance_id, 'host_boot_id': d.boot_id,
              'scope': {'ssm_contacted': False, 'journal_durable': False, 'replay_fenced': False,
                        'running_bootstrap_authenticated': False, 'complete_loader_closure_verified': False,
                        'host_authenticated': False, 'producer_authenticated': False,
                        'aws_cost_confirmed': False, 'materialized': False,
                        'runtime_qualified': False, 'launch_authorized': False, 'go_authorized': False}}
    sink._records.append(ledger.canonical(result))
    return json.loads(sink._records[-1])


# The program is fixed; only the encoded canonical request varies. Materialize
# every manifest member into a fresh private snapshot before importing Python
# sources. It cannot authenticate the host or prove the source producer: those
# are the external authority adapter's responsibility. A malicious local root
# user is outside this process-level boundary.
_REMOTE = r'''import hashlib,json,os,pathlib,re,stat,sys,tempfile
p=json.loads(__import__('base64').b64decode(PAYLOAD)); canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
request_sha=hashlib.sha256(canonical(p)).hexdigest()
def check_boot():
 if pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=p['boot_id']: raise ValueError('declared host boot differs')
check_boot()
base=pathlib.Path('/var/lib/rove4k/diagnostics')/p['campaign_id']
def safe_dir(path):
 if not path.is_absolute() or any(q.is_symlink() for q in (path,*path.parents)) or path.resolve(strict=True)!=path or not path.is_dir(): raise ValueError('unsafe pre-existing directory')
 st=path.stat()
 if st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o700: raise ValueError('directory must be private and owned')
 return path
safe_dir(base); safe_dir(base/'state'); safe_dir(base/'inputs'); safe_dir(base/'results'); safe_dir(base/'snapshots'); src=safe_dir(base/'seed')
def read_file(path,limit):
 if not path.is_absolute() or '..' in path.parts: raise ValueError('invalid absolute member path')
 directory=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  for part in path.parts[1:-1]:
   next_fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
   os.close(directory); directory=next_fd
  fd=os.open(path.parts[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
 finally: os.close(directory)
 try:
  s=os.fstat(fd)
  if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size<0 or s.st_size>limit: raise ValueError('member is not bounded regular file')
  with os.fdopen(fd,'rb',closefd=False) as f: data=f.read(limit+1)
  after=os.fstat(fd)
  if len(data)!=s.st_size or (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns): raise ValueError('member changed while reading')
  return data
 finally: os.close(fd)
raw=read_file(src/'seed.json',4<<20)
if hashlib.sha256(raw).hexdigest()!=p['seed_manifest_sha256']: raise ValueError('seed manifest hash differs')
m=json.loads(raw)
origin=m.get('source_origin',{})
if raw!=canonical(m)+b'\n' or m.get('format')!='rove4k-cloud-seed-v1' or not isinstance(origin,dict) or set(origin)!={'repository','head_sha','run_id','run_attempt'} or origin['repository']!=p['repository'] or origin['head_sha']!=p['source_head']: raise ValueError('seed provenance differs')
for key,expected_value in (('run_id',p['producer_run_id']),('run_attempt',p['producer_run_attempt'])):
 value=origin[key]
 if type(value) not in (str,int) or not re.fullmatch('[1-9][0-9]{0,19}',str(value)) or str(value)!=expected_value: raise ValueError('seed provenance differs')
members=m.get('members')
if not isinstance(members,dict) or not 0<len(members)<20000: raise ValueError('invalid seed members')
blocked={'.git','.aws','.ssh','.npmrc','node_modules','dist','dist-server','build','coverage','models','checkpoints','.cache','inventory.json','package-lock.json'}
def parts(name):
 if not isinstance(name,str) or not name or '\\' in name or ':' in name or '\0' in name: raise ValueError('unsafe member name')
 q=pathlib.PurePosixPath(name)
 if q.is_absolute() or any(x in ('','.','..') or x.lower() in blocked or x.lower().startswith('.env') or x.lower().endswith(('.pem','.key','.p12','.pfx')) or re.search(r'credential|service[-_ ]?account|api[-_ ]?key|access[-_ ]?key|ssh[-_ ]?key|secret|password|^token(?:\.|$)|[_-]token$|^id_(?:rsa|dsa|ecdsa|ed25519)(?:[.-].*)?$|^ssh_host_.*_key(?:\.pub)?$',x,re.I) for x in name.split('/')): raise ValueError('protected seed member')
 return q
snapshot=pathlib.Path(tempfile.mkdtemp(prefix='rove-seed-',dir=base/'snapshots')); total=0
for name,pin in sorted(members.items()):
 q=parts(name)
 if not isinstance(pin,dict) or set(pin)!={'bytes','sha256','mode'} or type(pin['bytes']) is not int or not 0<=pin['bytes']<=32<<20 or not isinstance(pin['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',pin['sha256']) or pin['mode'] not in (384,448): raise ValueError('invalid member pin')
 total+=pin['bytes']
 if total>256<<20: raise ValueError('seed expanded bound exceeded')
 data=read_file(src/q,32<<20)
 if len(data)!=pin['bytes'] or hashlib.sha256(data).hexdigest()!=pin['sha256']: raise ValueError('seed member differs')
 dest=snapshot/q; dest.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 with dest.open('xb') as f: f.write(data)
 dest.chmod(pin['mode'])
(snapshot/'seed.json').write_bytes(raw)
candidate_raw=read_file(base/'inputs'/'candidates.json',4<<20)
if hashlib.sha256(candidate_raw).hexdigest()!=p['candidates_sha256']: raise ValueError('candidate set hash differs')
candidates=json.loads(candidate_raw); selected=[r for r in candidates.get('candidates',[]) if isinstance(r,dict) and isinstance(r.get('artifact'),dict) and r['artifact'].get('id')==p['artifact_id']]
if len(selected)!=1 or candidates.get('profile')!=p['profile'] or selected[0]['artifact'].get('profile')!=p['profile']: raise ValueError('candidate identity differs')
family=selected[0]['artifact'].get('family'); rows=[r for r in m.get('rove',[]) if isinstance(r,dict) and r.get('family')==family and r.get('profile')==p['profile']]
if family in ('ice4','c4ke'): raise ValueError('peer producer artifact binding not implemented')
if len(rows)!=1 or rows[0].get('artifact_metadata') not in members: raise ValueError('candidate metadata mapping differs')
metadata=json.loads(read_file(snapshot/parts(rows[0]['artifact_metadata']),4<<20)); workflow=metadata.get('workflow_run',{})
if type(metadata.get('id')) is not int or str(metadata['id'])!=p['producer_artifact_id'] or type(workflow) is not dict or str(workflow.get('id'))!=p['producer_run_id']: raise ValueError('producer artifact metadata differs')
build=parts(rows[0].get('build')); build_name=str(build/'build.json')
if build_name not in members: raise ValueError('candidate build metadata missing')
build_record=json.loads(read_file(snapshot/build_name,4<<20)); expected=build_record.get('expected_contract',{}); artifact=selected[0]['artifact']
for role, candidate in (('whole',{'sha256':artifact.get('sha256'),'bytes':artifact.get('whole_bytes')}),('source',selected[0].get('source')),('native',selected[0].get('native'))):
 if not isinstance(candidate,dict) or {k:candidate.get(k) for k in ('sha256','bytes')}!={k:expected.get(role+'_'+k) for k in ('sha256','bytes')}: raise ValueError('candidate build pins differ')
if artifact.get('native_sha256')!=expected.get('native_sha256'): raise ValueError('candidate native pin differs')
for role, name in (('whole','x'),('source','main.c'),('native','native/x')):
 pin=members.get(str(build/name))
 if not isinstance(pin,dict) or {k:pin.get(k) for k in ('sha256','bytes')}!={k:expected.get(role+'_'+k) for k in ('sha256','bytes')}: raise ValueError('seed build member pins differ')
source=snapshot/parts(m['source_tree']); siblings=source/'engines/experiments/strength'
if not (siblings/'cloud_runtime.py').is_file() or not (siblings/'league_functional_host.py').is_file(): raise ValueError('missing diagnostic closure')
sys.path.insert(0,str(siblings)); import cloud_runtime,league_functional_host
rows=pathlib.Path('/proc/self/cgroup').read_text().splitlines()
if len(rows)!=1 or not rows[0].startswith('0::/'): raise ValueError('missing unified cgroup')
relative=pathlib.PurePosixPath(rows[0][3:]);
if '..' in relative.parts: raise ValueError('invalid delegated cgroup')
root=pathlib.Path('/sys/fs/cgroup')/str(relative).lstrip('/')
if str(root)!=EXPECTED_ROOT: raise ValueError('unexpected delegated systemd unit path')
cloud_runtime.delegate_controller(root)
result=league_functional_host.run(state_dir=base/'state',root=root,campaign=p['campaign_id'],candidates=base/'inputs'/'candidates.json',candidates_sha256=p['candidates_sha256'],profile=p['profile'],artifact=p['artifact_id'],out=base/'results'/p['job_id'],wall_seconds=p['wall_seconds'])
check_boot()
print(json.dumps({'format':'rove4k-ssm-functional-v2','request_sha256':request_sha,'observed_boot_id':p['boot_id'],'result':result},sort_keys=True,separators=(',',':')))
sys.exit(0 if result['status']=='complete' else 1)
'''


# The common prefix checks boot, the declared seed origin, every seed member
# and its pinned snapshot. The peer tail never interprets a GitHub artifact
# as the output of an upstream engine built on this host.
_PEER_REMOTE = _REMOTE.split("candidate_raw=", 1)[0] + r'''rows=[r for r in m.get('peers',[]) if isinstance(r,dict) and r.get('family')==p['family'] and r.get('profile')==p['profile']]
if len(rows)!=1 or rows[0].get('repository')!=p['upstream_repository'] or rows[0].get('revision')!=p['upstream_revision']: raise ValueError('peer source identity differs')
source=snapshot/parts(m['source_tree']); siblings=source/'engines/experiments/strength'
if not all((siblings/name).is_file() for name in ('cloud_runtime.py','league_functional_host.py','peer_diagnostic_prepare.py')): raise ValueError('missing peer diagnostic closure')
sys.path.insert(0,str(siblings)); import cloud_runtime,league_functional_host,peer_diagnostic_prepare
rows=pathlib.Path('/proc/self/cgroup').read_text().splitlines()
if len(rows)!=1 or not rows[0].startswith('0::/'): raise ValueError('missing unified cgroup')
relative=pathlib.PurePosixPath(rows[0][3:]);
if '..' in relative.parts: raise ValueError('invalid delegated cgroup')
root=pathlib.Path('/sys/fs/cgroup')/str(relative).lstrip('/')
if str(root)!=EXPECTED_ROOT: raise ValueError('unexpected delegated systemd unit path')
preparation_dir=base/'inputs'/('peer-'+p['job_id'])
prepared=peer_diagnostic_prepare.prepare(seed_root=snapshot,seed_sha256=p['seed_manifest_sha256'],family=p['family'],profile=p['profile'],cpu=min(os.sched_getaffinity(0)),out=preparation_dir)
if prepared.get('family')!=p['family'] or prepared.get('profile')!=p['profile'] or prepared.get('seed_sha256')!=p['seed_manifest_sha256'] or prepared.get('candidate',{}).get('path')!=str(preparation_dir/'candidate.json'): raise ValueError('prepared peer identity differs')
check_boot()
cloud_runtime.delegate_controller(root)
result=league_functional_host.run(state_dir=base/'state',root=root,campaign=p['campaign_id'],candidates=preparation_dir/'candidate.json',candidates_sha256=prepared['candidate']['sha256'],profile=p['profile'],artifact=prepared['artifact_id'],out=base/'results'/p['job_id'],wall_seconds=p['wall_seconds'])
check_boot()
print(json.dumps({'format':'rove4k-ssm-peer-functional-v1','request_sha256':request_sha,'observed_boot_id':p['boot_id'],'preparation':prepared,'result':result},sort_keys=True,separators=(',',':')))
sys.exit(0 if result['status']=='complete' else 1)
'''


def command(request):
    """Produce the fixed systemd delegated command; never contact AWS."""
    if type(request) not in (Request, PeerRequest):
        raise ValueError('validated immutable Request required')
    payload = base64.b64encode(ledger.canonical(request.record())).decode('ascii')
    unit = _unit(request)
    script = (_PEER_REMOTE if type(request) is PeerRequest else _REMOTE).replace('PAYLOAD', repr(payload)).replace('EXPECTED_ROOT', repr('/sys/fs/cgroup/system.slice/' + unit))
    argv = ['/usr/bin/systemd-run', '--unit=' + unit, '--slice=system.slice', '--property=Delegate=yes', '--property=Type=exec']
    if type(request) is PeerRequest:
        argv.append('--property=RuntimeMaxSec=' + str(request.preparation_seconds + request.wall_seconds + 60))
    argv += ['--wait', '--pipe', '--collect', '/usr/bin/python3', '-I', '-B', '-c', script]
    return 'exec ' + ' '.join(shlex.quote(arg) for arg in argv)


def _unit(request):
    return 'rove4k-diag-' + ledger.digest(request.record())[:32] + '.service'


def expected_receipt_inputs(request):
    """Derive collector pins from the same immutable dispatch request."""
    if type(request) not in (Request, PeerRequest):
        raise ValueError('validated immutable Request required')
    base = PurePosixPath('/var/lib/rove4k/diagnostics') / request.campaign_id
    if type(request) is PeerRequest:
        return {'state_dir': str(base / 'state'), 'root': '/sys/fs/cgroup/system.slice/' + _unit(request),
                'campaign': request.campaign_id, 'preparation_dir': str(base / 'inputs' / ('peer-' + request.job_id)),
                'profile': request.profile, 'family': request.family, 'out': str(base / 'results' / request.job_id),
                'wall_seconds': request.wall_seconds, 'boot_id': request.boot_id,
                'seed_manifest_sha256': request.seed_manifest_sha256,
                'upstream_repository': request.upstream_repository, 'upstream_revision': request.upstream_revision}
    return {'state_dir': str(base / 'state'), 'root': '/sys/fs/cgroup/system.slice/' + _unit(request),
            'campaign': request.campaign_id, 'candidates': str(base / 'inputs' / 'candidates.json'),
            'candidates_sha256': request.candidates_sha256, 'profile': request.profile,
            'artifact': request.artifact_id, 'out': str(base / 'results' / request.job_id),
            'wall_seconds': request.wall_seconds, 'boot_id': request.boot_id}


def dispatch(request, *, plan, journal, client):
    """Fail closed until a live owned-host/source authority is implemented.

    A caller-provided callable, SSM ping or JSON flag is not authentication.
    This entrypoint never calls AWS until the concrete verifier is integrated.
    """
    raise RuntimeError('live host, source provenance and budget verifier is not implemented')


def _dispatch_with_verified_authority(request, *, plan, journal, client, authority):
    """Protocol implementation for tests and a future concrete verifier.

    This private function must not be wired as public dispatch until authority
    is implemented independently. The journal fences only its own local owner.
    """
    if type(request) not in (Request, PeerRequest) or not callable(authority):
        raise ValueError('validated request and live authority adapter required')
    if (getattr(plan, 'campaign_id', None) != request.campaign_id or
            getattr(plan, 'region', None) != request.region or getattr(plan, 'account_id', None) != request.account_id or
            getattr(plan, 'artifact_bucket', None) != request.artifact_bucket or journal.campaign != request.campaign_id):
        raise ValueError('plan, journal and request identity differ')
    if any(row['event'] == 'league.functional_ssm_requested' and
           (row['data'].get('job_id') == request.job_id or row['data'].get('instance_id') == request.instance_id)
           for row in journal.rows):
        raise ValueError('prior diagnostic on this instance requires independent reconciliation')
    record = request.record()
    digest = ledger.digest(record)
    attestation = authority(client=client, request=record)
    expected = {'campaign_id': request.campaign_id, 'instance_id': request.instance_id,
                'account_id': request.account_id, 'region': request.region,
                'seed_manifest_sha256': request.seed_manifest_sha256, 'source_head': request.source_head,
                'artifact_bucket': request.artifact_bucket, 'repository': request.repository,
                'producer_run_id': request.producer_run_id, 'producer_run_attempt': request.producer_run_attempt,
                'seed_bucket': request.seed_bucket,
                'seed_key': request.seed_key, 'seed_version_id': request.seed_version_id,
                'seed_archive_sha256': request.seed_archive_sha256, 'seed_archive_bytes': request.seed_archive_bytes,
                'boot_id': request.boot_id, 'request_sha256': digest}
    if type(request) is Request:
        expected['producer_artifact_id'] = request.producer_artifact_id
    else:
        expected.update(family=request.family, upstream_repository=request.upstream_repository,
                        upstream_revision=request.upstream_revision, preparation_seconds=request.preparation_seconds)
    if type(attestation) is not dict or attestation.get('verified') is not True or any(attestation.get(k) != v for k, v in expected.items()):
        raise ValueError('live authority did not verify the exact diagnostic binding')
    ssm = campaign.SSMCommands(client)
    if not ssm.ready(request.instance_id)['ready']:
        raise ValueError('bound Linux SSM agent is not online')
    cmd = command(request)
    execution_seconds = request.wall_seconds + 180 + (request.preparation_seconds if type(request) is PeerRequest else 0)
    wire = {'InstanceIds': [request.instance_id], 'DocumentName': 'AWS-RunShellScript',
            'Parameters': {'commands': [cmd], 'executionTimeout': [str(execution_seconds)]},
            'TimeoutSeconds': 60, 'MaxConcurrency': '1', 'MaxErrors': '0',
            'Comment': 'rove4k:' + request.job_id, 'OutputS3BucketName': request.artifact_bucket,
            'OutputS3KeyPrefix': request.campaign_id + '/ssm/' + request.job_id}
    journal.append('league.functional_ssm_requested', {'job_id': request.job_id, 'instance_id': request.instance_id,
        'request_sha256': digest, 'command_sha256': hashlib.sha256(cmd.encode()).hexdigest(),
        'ssm_request_sha256': ledger.digest(wire)})
    try:
        command_id = ssm.send(plan, request.instance_id, cmd, request.job_id, execution_seconds)
    except Exception:
        journal.append('league.functional_ssm_uncertain', {'job_id': request.job_id, 'request_sha256': digest})
        raise
    journal.append('league.functional_ssm_sent', {'job_id': request.job_id, 'instance_id': request.instance_id,
        'request_sha256': digest, 'command_id': command_id})
    return {'request_sha256': digest, 'command_id': command_id, 'instance_id': request.instance_id,
            'transport_only': True, 'scored_game_admitted': False}
