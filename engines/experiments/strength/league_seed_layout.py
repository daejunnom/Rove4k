"""Plan an injective physical layout from an independently pinned seed.

This is a pure, diagnostic mapping: no path is opened, directory made, member
extracted, transported code executed, or host/producer/GO authenticated. The
sealed manifest and member pins remain expressed in logical archive names;
future consumers must explicitly translate filesystem access with this map.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
import hashlib
import io
import json
import re
import unicodedata
import zipfile

try:
    from . import cloud_runtime as cloud
    from .league_seed_archive import inspect_snapshot
except ImportError:
    import cloud_runtime as cloud
    from league_seed_archive import inspect_snapshot

_ALIAS = '__rove_seed_build_v1__'
_BLOCKED = {'.git', '.aws', '.ssh', '.npmrc', 'node_modules', 'dist', 'dist-server',
            'coverage', 'models', 'checkpoints', '.cache', 'inventory.json', 'package-lock.json'}
_PROTECTED = re.compile(r'credential|service[-_ ]?account|api[-_ ]?key|access[-_ ]?key|'
                        r'ssh[-_ ]?key|private[-_ ]?key|secret|password|'
                        r'^id_(?:rsa|dsa|ecdsa|ed25519)(?:[.-].*)?$|^ssh_host_.*_key(?:\.pub)?$', re.I)
_DEVICE = re.compile(r'(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z', re.I)
_SNAPSHOT_TOKEN = object()


def _parts(value):
    cloud.member(value)
    if len(value.encode('utf-8', 'surrogatepass')) > 4096:
        raise ValueError('logical path exceeds bound')
    parts = value.split('/')
    if len(parts) > 128:
        raise ValueError('logical path depth exceeds bound')
    for part in parts:
        lower = part.casefold()
        if (len(part.encode('utf-8', 'surrogatepass')) > 255 or lower in _BLOCKED
                or lower == _ALIAS.casefold() or lower.startswith('.env')
                or lower == 'token' or lower.startswith('token.') or lower.endswith(('-token', '_token'))
                or _PROTECTED.search(part) or _DEVICE.fullmatch(part)
                or lower.endswith(('.pem', '.key', '.p12', '.pfx'))
                or part.endswith((' ', '.'))
                or any(ord(c) < 32 or 127 <= ord(c) < 160 or 0xd800 <= ord(c) <= 0xdfff for c in part)):
            raise ValueError('protected, reserved or nonportable logical path')
    return tuple(parts)


def _case_key(parts):
    return tuple(unicodedata.normalize('NFC', unicodedata.normalize('NFD', part).casefold()) for part in parts)


def _map_parts(parts):
    return tuple(_ALIAS if part.casefold() == 'build' else part for part in parts)


@dataclass(frozen=True, slots=True)
class Entry:
    logical: str
    physical: str
    sha256: str
    bytes: int
    mode: int

    def __post_init__(self):
        if (type(self.logical) is not str or type(self.physical) is not str
                or type(self.sha256) is not str or not cloud.SHA.fullmatch(self.sha256)
                or type(self.bytes) is not int or not 0 <= self.bytes <= cloud.MAX_MEMBER
                or type(self.mode) is not int or self.mode not in (0o600, 0o700)):
            raise ValueError('exact typed bounded layout member pin required')


@dataclass(frozen=True, slots=True)
class Layout:
    """Frozen pins and path pairs; lookups do not touch the filesystem."""
    archive_sha256: str
    manifest_sha256: str
    entries: tuple[Entry, ...]
    _pairs: tuple[tuple[str, str], ...] = field(repr=False)
    _manifest_raw: bytes = field(repr=False)
    _factory: object = field(repr=False, compare=False)

    def __post_init__(self):
        if (self._factory is not _SNAPSHOT_TOKEN or type(self._manifest_raw) is not bytes
                or not isinstance(self.archive_sha256, str) or not cloud.SHA.fullmatch(self.archive_sha256)
                or not isinstance(self.manifest_sha256, str) or not cloud.SHA.fullmatch(self.manifest_sha256)
                or hashlib.sha256(self._manifest_raw).hexdigest() != self.manifest_sha256):
            raise ValueError('validated snapshot layout required')
        manifest = cloud.validate_seed_manifest(json.loads(self._manifest_raw))
        if cloud.ledger.canonical(manifest) + b'\n' != self._manifest_raw:
            raise ValueError('original canonical manifest required')
        pins = dict(manifest['members'])
        pins['seed.json'] = {'bytes': len(self._manifest_raw), 'sha256': self.manifest_sha256, 'mode': 0o600}
        pairs = _pairs_for(tuple(pins))
        destinations = dict(pairs)
        entries = tuple(Entry(name, destinations[name], pin['sha256'], pin['bytes'], pin['mode'])
                        for name, pin in sorted(pins.items()))
        if self._pairs != pairs or self.entries != entries:
            raise ValueError('layout differs from its exact manifest')

    @property
    def manifest(self):
        # Do not hand a mutable manifest that can mutate our retained evidence.
        return json.loads(self._manifest_raw)

    def physical_for(self, logical):
        if type(logical) is not str:
            raise ValueError('logical name was not pinned by this layout')
        index = bisect_left(self._pairs, (logical, ''))
        if index == len(self._pairs) or self._pairs[index][0] != logical:
            raise ValueError('logical name was not pinned by this layout')
        return self._pairs[index][1]

    def logical_for(self, physical):
        values = {p: q for q, p in self._pairs}
        if type(physical) is not str or physical not in values:
            raise ValueError('physical name was not pinned by this layout')
        return values[physical]

    def scope(self):
        # Object-local claims can be reconstructed by Python code. A consumer
        # must call verify_for with independent pins immediately before use.
        return {'archive_pin_checked': False, 'manifest_and_members_checked': False,
                'independent_snapshot_recheck_required': True, 'mapping_injective': True, 'materialized': False,
                'host_authenticated': False, 'producer_authenticated': False,
                'runtime_qualified': False, 'go_authorized': False}

    def verify_for(self, snapshot, *, expected_archive_sha256, expected_archive_bytes,
                   expected_manifest_sha256, expected_origin):
        """Recompute mapping against caller-provided independent pins.

        A Python factory token or stored hash is not live authority. This
        catches self-consistent dataclass replacement before consumption.
        """
        expected = build_layout(snapshot, expected_archive_sha256=expected_archive_sha256,
                                expected_archive_bytes=expected_archive_bytes,
                                expected_manifest_sha256=expected_manifest_sha256,
                                expected_origin=expected_origin)
        if self != expected:
            raise ValueError('layout differs from independent pinned snapshot')
        return self


def _pairs_for(files):
    """Build an injective map for files and every implicit parent directory."""
    if type(files) is not tuple or not files or len(files) > cloud.MAX_SEED_MEMBERS + 1:
        raise ValueError('bounded explicit member names required')
    logical_nodes, physical_nodes = {}, {}
    logical_files, pairs = set(), {}
    for value in files:
        parts = _parts(value)
        folded_file = _case_key(parts)
        if folded_file in logical_files:
            raise ValueError('duplicate or casefold-equivalent file')
        logical_files.add(folded_file)
        for count in range(1, len(parts) + 1):
            logical = parts[:count]
            physical = _map_parts(logical)
            key, dest = _case_key(logical), _case_key(physical)
            previous = logical_nodes.get(key)
            if previous is not None and previous != logical:
                raise ValueError('casefold or Unicode-normalized path collision')
            previous_dest = physical_nodes.get(dest)
            if previous_dest is not None and previous_dest != logical:
                raise ValueError('casefold or alias destination collision')
            logical_nodes[key], physical_nodes[dest] = logical, logical
            pairs['/'.join(logical)] = '/'.join(physical)
    for file_key in logical_files:
        if any(file_key[:count] in logical_files for count in range(1, len(file_key))):
            raise ValueError('file and directory namespace collision')
    return tuple(sorted(pairs.items()))


def build_layout(snapshot, *, expected_archive_sha256, expected_archive_bytes,
                 expected_manifest_sha256, expected_origin):
    """Reinspect exact bytes before deriving any mappings or exposing pins.

    Callers must authenticate pins and bind any later consumer independently;
    this check does not make the source or host trustworthy.
    """
    result = inspect_snapshot(snapshot, expected_archive_sha256=expected_archive_sha256,
                              expected_archive_bytes=expected_archive_bytes,
                              expected_manifest_sha256=expected_manifest_sha256,
                              expected_origin=expected_origin, require_workflow_proof=True)
    with zipfile.ZipFile(io.BytesIO(snapshot)) as archive:
        manifest, raw, _ = cloud.seed_archive_manifest(archive, expected_manifest_sha256=expected_manifest_sha256)
    pins = dict(manifest['members'])
    pins['seed.json'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'mode': 0o600}
    pairs = _pairs_for(tuple(pins))
    destinations = dict(pairs)
    entries = tuple(Entry(name, destinations[name], expected['sha256'], expected['bytes'], expected['mode'])
                    for name, expected in sorted(pins.items()))
    return Layout(result['archive_sha256'], expected_manifest_sha256, entries, pairs, raw, _SNAPSHOT_TOKEN)
