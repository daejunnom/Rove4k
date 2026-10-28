"""One-shot SSM transport for a pinned, non-scoring league diagnostic.

The caller MUST supply a live authority adapter which verifies the current
controller, owned instance, immutable seed provenance, budget and launch
policy. No such production adapter is supplied here: a ping, a hash, or a
serialized flag is not authority. This module never launches or terminates an
instance or authorizes a scored game. The durable journal fences replay only
for one journal owner, not for another controller or a different host.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
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
    wall_seconds: int = 120

    def __post_init__(self):
        for item in (self.campaign_id, self.job_id, self.artifact_id):
            ledger.valid_id(item)
        if (len(self.job_id) > 93 or not isinstance(self.instance_id, str) or not _INSTANCE.fullmatch(self.instance_id)
                or not isinstance(self.account_id, str) or not _ACCOUNT.fullmatch(self.account_id)
                or not isinstance(self.region, str) or not _REGION.fullmatch(self.region)
                or not isinstance(self.source_head, str) or not _GIT.fullmatch(self.source_head)
                or not isinstance(self.seed_manifest_sha256, str) or not _HEX.fullmatch(self.seed_manifest_sha256)
                or not isinstance(self.candidates_sha256, str) or not _HEX.fullmatch(self.candidates_sha256)
                or not isinstance(self.artifact_bucket, str)
                or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', self.artifact_bucket)
                or self.profile not in ('test-p16', 'test-p192')
                or type(self.wall_seconds) is not int or not 90 <= self.wall_seconds <= 300):
            raise ValueError('exact account, instance, seed, candidate and bounded P16/P192 request required')

    def record(self):
        return {'format': 'rove4k-ssm-functional-request-v1', 'campaign_id': self.campaign_id,
                'job_id': self.job_id, 'instance_id': self.instance_id, 'account_id': self.account_id,
                'region': self.region, 'seed_manifest_sha256': self.seed_manifest_sha256,
                'source_head': self.source_head, 'candidates_sha256': self.candidates_sha256,
                'profile': self.profile, 'artifact_id': self.artifact_id,
                'artifact_bucket': self.artifact_bucket, 'wall_seconds': self.wall_seconds}


# The program is fixed; only the encoded canonical request varies. Materialize
# every manifest member into a fresh private snapshot before importing Python
# sources. It cannot authenticate the host or prove the source producer: those
# are the external authority adapter's responsibility. A malicious local root
# user is outside this process-level boundary.
_REMOTE = r'''import hashlib,json,os,pathlib,re,stat,sys,tempfile
p=json.loads(__import__('base64').b64decode(PAYLOAD)); canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
request_sha=hashlib.sha256(canonical(p)).hexdigest()
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
if raw!=canonical(m)+b'\n' or m.get('format')!='rove4k-cloud-seed-v1' or m.get('source_origin',{}).get('repository')!='daejunnom/Rove4k' or m.get('source_origin',{}).get('head_sha')!=p['source_head']: raise ValueError('seed provenance differs')
members=m.get('members')
if not isinstance(members,dict) or not 0<len(members)<20000: raise ValueError('invalid seed members')
blocked={'.git','.aws','.ssh','node_modules','dist','dist-server','build','coverage','models','checkpoints','.cache','inventory.json','package-lock.json'}
def parts(name):
 if not isinstance(name,str) or not name or '\\' in name or ':' in name or '\0' in name: raise ValueError('unsafe member name')
 q=pathlib.PurePosixPath(name)
 if q.is_absolute() or any(x in ('','.','..') or x.lower() in blocked or x.lower().startswith('.env') or re.search(r'credential|service[-_ ]?account|api[-_ ]?key|ssh[-_ ]?key|^id_(rsa|ed25519)$',x,re.I) for x in name.split('/')): raise ValueError('protected seed member')
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
print(json.dumps({'format':'rove4k-ssm-functional-v1','request_sha256':request_sha,'result':result},sort_keys=True,separators=(',',':')))
sys.exit(0 if result['status']=='complete' else 1)
'''


def command(request):
    """Produce the fixed systemd delegated command; never contact AWS."""
    if type(request) is not Request:
        raise ValueError('validated immutable Request required')
    payload = base64.b64encode(ledger.canonical(request.record())).decode('ascii')
    unit = _unit(request)
    script = _REMOTE.replace('PAYLOAD', repr(payload)).replace('EXPECTED_ROOT', repr('/sys/fs/cgroup/system.slice/' + unit))
    argv = ['/usr/bin/systemd-run', '--unit=' + unit, '--slice=system.slice', '--property=Delegate=yes', '--property=Type=exec',
            '--wait', '--pipe', '--collect', '/usr/bin/python3', '-I', '-B', '-c', script]
    return 'exec ' + ' '.join(shlex.quote(arg) for arg in argv)


def _unit(request):
    return 'rove4k-diag-' + ledger.digest(request.record())[:32] + '.service'


def expected_receipt_inputs(request):
    """Derive collector pins from the same immutable dispatch request."""
    if type(request) is not Request:
        raise ValueError('validated immutable Request required')
    base = PurePosixPath('/var/lib/rove4k/diagnostics') / request.campaign_id
    return {'state_dir': str(base / 'state'), 'root': '/sys/fs/cgroup/system.slice/' + _unit(request),
            'campaign': request.campaign_id, 'candidates': str(base / 'inputs' / 'candidates.json'),
            'candidates_sha256': request.candidates_sha256, 'profile': request.profile,
            'artifact': request.artifact_id, 'out': str(base / 'results' / request.job_id),
            'wall_seconds': request.wall_seconds}


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
    if type(request) is not Request or not callable(authority):
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
                'artifact_bucket': request.artifact_bucket, 'request_sha256': digest}
    if type(attestation) is not dict or attestation.get('verified') is not True or any(attestation.get(k) != v for k, v in expected.items()):
        raise ValueError('live authority did not verify the exact diagnostic binding')
    ssm = campaign.SSMCommands(client)
    if not ssm.ready(request.instance_id)['ready']:
        raise ValueError('bound Linux SSM agent is not online')
    cmd = command(request)
    wire = {'InstanceIds': [request.instance_id], 'DocumentName': 'AWS-RunShellScript',
            'Parameters': {'commands': [cmd], 'executionTimeout': [str(request.wall_seconds + 180)]},
            'TimeoutSeconds': 60, 'MaxConcurrency': '1', 'MaxErrors': '0',
            'Comment': 'rove4k:' + request.job_id, 'OutputS3BucketName': request.artifact_bucket,
            'OutputS3KeyPrefix': request.campaign_id + '/ssm/' + request.job_id}
    journal.append('league.functional_ssm_requested', {'job_id': request.job_id, 'instance_id': request.instance_id,
        'request_sha256': digest, 'command_sha256': hashlib.sha256(cmd.encode()).hexdigest(),
        'ssm_request_sha256': ledger.digest(wire)})
    try:
        command_id = ssm.send(plan, request.instance_id, cmd, request.job_id, request.wall_seconds + 180)
    except Exception:
        journal.append('league.functional_ssm_uncertain', {'job_id': request.job_id, 'request_sha256': digest})
        raise
    journal.append('league.functional_ssm_sent', {'job_id': request.job_id, 'instance_id': request.instance_id,
        'request_sha256': digest, 'command_id': command_id})
    return {'request_sha256': digest, 'command_id': command_id, 'instance_id': request.instance_id,
            'transport_only': True, 'scored_game_admitted': False}
