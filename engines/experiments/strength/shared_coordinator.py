"""Serialized, recoverable local writer for the shared budget ledger.

This is a journal integration, not a distributed game-start coordinator.
The caller must own a POSIX-locked external Journal and protect its history and
initial Anchor independently.  The lock serializes one local process only;
S3 CAS plus a local journal does not fence other hosts or prevent ABA. The
coordinator fsyncs the journal's ancestor directories before any remote
write; storage-level loss, rollback and independent anchor protection remain
outside this implementation and require a separate recovery procedure.
Methods below perform synchronous I/O and MUST NOT run in WaveExecutor callbacks.
Neither a journal receipt nor an S3 acknowledgement is a release fence, proof
of GO receipt, or physical settlement.  The scored league remains closed until
an authenticated, fenced owner, trusted time and host transport are integrated.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import os
import threading

try:
    from .global_budget import Anchor, S3SharedBudget
    from .ledger import Journal, canonical
except ImportError:
    from global_budget import Anchor, S3SharedBudget
    from ledger import Journal, canonical


class CoordinatorBlocked(RuntimeError):
    """The journal and remote state require independent reconciliation."""


_OWNER_LOCK = threading.Lock()


def _sync_journal_directories(journal):
    """Durably link the already-open journal and any newly created parents.

    Each directory is fsynced from child to root. Refuse filesystems without
    this operation; a file fsync alone does not persist the directory entry.
    The separate journal inode comparison prevents silently syncing a replaced
    path instead of the locked handle. It is not a defence against arbitrary
    concurrent path renames or storage hardware that misrepresents durability.
    """
    flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    for index, directory in enumerate(journal.path.parents):
        descriptor = os.open(directory, flags)
        try:
            if index == 0:
                path_stat = os.stat(journal.path.name, dir_fd=descriptor, follow_symlinks=False)
                locked_stat = os.fstat(journal.file.fileno())
                if (path_stat.st_dev, path_stat.st_ino) != (locked_stat.st_dev, locked_stat.st_ino):
                    raise ValueError('journal path differs from its locked file')
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


class SharedBudgetJournal:
    """Write intent before the S3 side effect and retain uncertain requests.

    `root_anchor` must be an independently trusted, externally protected
    checkpoint, not one derived from the S3 object being checked. Journal
    rollback/replacement and multi-host single-writer fencing are outside this
    implementation. A failure or an interrupted request permanently blocks new
    submissions from this object and survives process restart. Inspection never
    resends, settles a game, or automatically reopens admission.
    """
    provides_go_authority = False

    def __init__(self, store: S3SharedBudget, journal: Journal, root_anchor: Anchor):
        if os.name != 'posix':
            raise ValueError('POSIX exclusive journal locking is required')
        if not isinstance(store, S3SharedBudget) or not isinstance(journal, Journal) or not isinstance(root_anchor, Anchor):
            raise TypeError('actual shared budget store, locked journal and trusted root anchor required')
        if journal.campaign != store.campaign or root_anchor.authority != store.authority:
            raise ValueError('journal, trusted root and shared ledger identities differ')
        # Journal's OS file lock excludes separately opened handles on POSIX.
        # This separate in-process guard also excludes two coordinators that
        # were mistakenly given the exact same Journal object and OS handle.
        with _OWNER_LOCK:
            if getattr(journal, '_shared_coordinator_owner', None) is not None:
                raise ValueError('journal already belongs to a coordinator')
            journal._shared_coordinator_owner = self
        try:
            self._store, self._journal = store, journal
            self._lock = threading.Lock()
            self._root = root_anchor
            self._anchor = root_anchor
            self._pending = None
            self._blocked = False
            _sync_journal_directories(journal)
            self._read_history()
            # Always compare with the real store. A later unrelated object
            # version is not silently adopted even if it extends the anchor.
            snapshot = self._store.load(self._anchor)
            if snapshot.anchor != self._anchor:
                self._blocked = True
        except BaseException:
            with _OWNER_LOCK:
                if journal._shared_coordinator_owner is self:
                    del journal._shared_coordinator_owner
            raise

    @property
    def blocked(self):
        return self._blocked

    @property
    def anchor(self):
        return self._anchor

    @staticmethod
    def _make_anchor(data):
        if not isinstance(data, dict) or set(data) != {'seq', 'sha256', 'authority', 'opening_sha256'}:
            raise ValueError('journal anchor fields differ')
        return Anchor(**data)

    def _read_history(self):
        rows = self._journal.rows
        if not rows:
            self._journal.append('shared.genesis', {'anchor': asdict(self._root)})
            return
        genesis = rows[0]
        if genesis['event'] != 'shared.genesis' or genesis['data'] != {'anchor': asdict(self._root)}:
            raise ValueError('journal root differs from independent trusted anchor')
        for row in rows[1:]:
            name, data = row['event'], row['data']
            if name == 'shared.intent':
                if self._pending is not None or not isinstance(data, dict) or set(data) != {'request_id', 'event', 'data', 'at'}:
                    raise ValueError('multiple or invalid outstanding journal intents')
                self._pending = data
            elif name == 'shared.commit':
                if self._pending is None or not isinstance(data, dict) or set(data) != {'request_id', 'anchor'}:
                    raise ValueError('journal commit has no matching intent')
                if data['request_id'] != self._pending['request_id']:
                    raise ValueError('journal commit request differs')
                new = self._make_anchor(data['anchor'])
                if (new.authority != self._anchor.authority or new.opening_sha256 != self._anchor.opening_sha256
                        or new.seq != self._anchor.seq + 1):
                    raise ValueError('journal anchor sequence or identity differs')
                self._anchor, self._pending = new, None
            else:
                raise ValueError('unexpected shared coordinator journal event')
        if self._pending is not None:
            self._blocked = True

    def record(self, *, request_id, event, data, at):
        """Persist one budget event; never call from a wave callback.

        Any exception after intent fsync is treated as uncertain. No automatic
        retry or rollback occurs, even if a remote response appears definitive.
        """
        with self._lock:
            if self._blocked or self._pending is not None:
                raise CoordinatorBlocked('pending or divergent ledger requires reconciliation')
            # JSON round-trip fixes caller mutation before writing intent.
            frozen = json.loads(canonical(data))
            pending = {'request_id': request_id, 'event': event, 'data': frozen, 'at': at}
            # An incomplete write or a failing fsync can leave a partial or
            # complete intent on disk. Even before S3 is called the local
            # journal must be quarantined rather than reported as writable.
            self._blocked = True
            self._journal.append('shared.intent', pending)
            self._pending = pending
            result = self._store.append(trusted=self._anchor, expected_head=self._anchor,
                                        request_id=request_id, event=event, data=frozen, at=at)
            if result.anchor.seq != self._anchor.seq + 1:
                raise CoordinatorBlocked('unexpected ledger advance; preserve pending request')
            self._journal.append('shared.commit', {'request_id': request_id, 'anchor': asdict(result.anchor)})
            self._anchor, self._pending, self._blocked = result.anchor, None, False
            return result

    def inspect_pending(self):
        """Read-only reconciliation aid; absence is not proof of no effect."""
        with self._lock:
            if self._pending is None:
                raise ValueError('no pending request')
            snapshot = self._store.load(self._anchor)
            matches = [row for row in snapshot.rows if row['request_id'] == self._pending['request_id']]
            if len(matches) > 1:
                raise CoordinatorBlocked('duplicate request identity in remote history')
            if not matches:
                return {'status': 'not_observed', 'anchor': snapshot.anchor}
            row = matches[0]
            expected = self._pending
            if (row['event'] != expected['event'] or row['data'] != expected['data']
                    or row['time_utc'] != expected['at']):
                raise CoordinatorBlocked('remote request identity carries different contents')
            return {'status': 'observed', 'anchor': snapshot.anchor, 'request_id': row['request_id']}
