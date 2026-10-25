"""Bounded asynchronous publication over the verified S3Evidence port."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import queue
import threading
import math


@dataclass
class Ticket:
    key: str
    path: Path
    sha256: str
    bytes: int
    done: threading.Event = field(default_factory=threading.Event)
    acknowledgement: dict | None = None
    error: BaseException | None = None

    def result(self, timeout=125):
        if not self.done.wait(timeout):
            raise TimeoutError("evidence is not remotely acknowledged")
        if self.error is not None:
            raise RuntimeError("evidence publication failed") from self.error
        return dict(self.acknowledgement)


class DurableOutbox:
    """Only immutable local chunks enter the publisher; failed data is kept.

    publish(path,key) is the AWS module's checksum-verified S3Evidence port.
    No local write or queued request is treated as a remote acknowledgement.
    The actual AWS transport has a finite command timeout; callers must not
    provide an unbounded publisher to a running campaign.
    """
    def __init__(self, root, publisher, *, pending_limit=128):
        self.root = Path(root)
        if not self.root.is_absolute() or self.root.exists():
            raise ValueError("a new absolute owned outbox is required")
        if any((parent / ".git").exists() for parent in (self.root, *self.root.parents)):
            raise ValueError("evidence chunks must stay outside Git")
        if type(pending_limit) is not int or pending_limit < 1:
            raise ValueError("positive finite outbox limit required")
        self.root.mkdir(parents=True)
        self.publisher = publisher
        self.queue = queue.Queue(pending_limit)
        self.closed = threading.Event()
        self.cancelled = threading.Event()
        self.state_lock = threading.Lock()
        self.active_ticket = None
        self.max_publish_seconds = getattr(publisher, "max_publish_seconds", None)
        if (type(self.max_publish_seconds) not in (int, float) or not math.isfinite(self.max_publish_seconds)
                or not 0 < self.max_publish_seconds <= 120):
            raise ValueError("publisher must declare a finite per-publication bound no greater than 120 seconds")
        self.errors = []
        self.thread = threading.Thread(target=self._work, name="rove-evidence-publisher")
        self.thread.start()

    def submit(self, key, data):
        if self.closed.is_set():
            raise RuntimeError("outbox is closed")
        self.check()
        if not isinstance(data, bytes) or len(data) > 128 << 20:
            raise ValueError("immutable evidence bytes exceed the chunk bound")
        digest = hashlib.sha256(data).hexdigest()
        target = self.root / (digest + ".chunk")
        try:
            with target.open("xb") as output:
                output.write(data)
                output.flush()
                import os
                os.fsync(output.fileno())
        except FileExistsError:
            if target.is_symlink() or target.read_bytes() != data:
                raise ValueError("owned content-addressed evidence changed")
        ticket = Ticket(key, target, digest, len(data))
        try:
            self.queue.put_nowait(ticket)
        except queue.Full as error:
            raise RuntimeError("durability backlog exceeded its finite bound") from error
        return ticket

    def _work(self):
        while not self.closed.is_set() or not self.queue.empty():
            try:
                ticket = self.queue.get(timeout=.1)
            except queue.Empty:
                continue
            try:
                with self.state_lock:
                    if self.errors or self.cancelled.is_set():
                        raise RuntimeError("publisher stopped before starting another request")
                    self.active_ticket = ticket
                ack = self.publisher.publish(ticket.path, ticket.key)
                if (ack.get("verified") is not True or ack.get("acknowledged") is not True or
                        ack.get("backend") != "s3" or ack.get("sha256") != ticket.sha256 or
                        ack.get("bytes") != ticket.bytes or ack.get("object_key") != ticket.key):
                    raise ValueError("remote acknowledgement does not bind uploaded bytes")
                ticket.acknowledgement = dict(ack)
            except BaseException as error:
                ticket.error = error
                self.errors.append(error)
            finally:
                with self.state_lock:
                    self.active_ticket = None
                ticket.done.set()
                self.queue.task_done()

    def check(self):
        if self.errors:
            raise RuntimeError("durable evidence publication failed; stop new work") from self.errors[0]

    def close(self, timeout=125):
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("finite positive physical shutdown timeout required")
        self.closed.set()
        reserve = min(timeout, self.max_publish_seconds)
        self.thread.join(max(0, timeout - reserve))
        if self.thread.is_alive():
            with self.state_lock:
                self.cancelled.set()
            self.thread.join(reserve)
        if self.thread.is_alive():
            raise TimeoutError("publisher violated its finite in-flight bound; retain its live owner")
        self.check()

    def __enter__(self):
        return self

    def __exit__(self, *error):
        self.close()
