"""Configure a previously owned upstream OpenBench peer for a TEST profile.

This helper neither starts nor owns a process. Its caller must already own and
place it and verify process identity and fixed configuration. Current free or
available memory is not an admission condition. UCI readiness is not proof of
a successful allocation, the target ABI, worker placement, source provenance,
or league GO.
"""
from __future__ import annotations

import math
import re
import time

_PROFILES = {
    "test-p16": {"workers": 16, "hash_mib": 16384},
    "test-p192": {"workers": 192, "hash_mib": 262144},
}
_NAMES = {"ice4": b"id name ice4 v6.1", "c4ke": b"id name c4ke v3.0"}
_SPIN = re.compile(rb"option name (Hash|Threads) type spin default ([0-9]+) min ([0-9]+) max ([0-9]+)")
_PONDER = re.compile(rb"option name Ponder type check default (true|false)")
_EXPECTED = {b"Hash": (8, 1, 67108864), b"Threads": (1, 1, 2048)}
_MAX_OUTPUT = 1 << 20


def _complete_lines(raw):
    if not isinstance(raw, bytes) or len(raw) > _MAX_OUTPUT or b"\x00" in raw:
        raise ValueError("invalid or oversized UCI output")
    # Ignore a trailing partial line; it cannot authenticate an acknowledgement.
    end = raw.rfind(b"\n")
    if end < 0:
        return []
    return raw[:end + 1].splitlines()


def _check_startup(raw, peer, resources, *, final=False):
    lines = _complete_lines(raw)
    if lines.count(b"uciok") != 1 or lines.count(_NAMES[peer]) != 1:
        raise ValueError("upstream UCI identity or acknowledgement differs")
    if sum(line.startswith(b"id name ") for line in lines) != 1:
        raise ValueError("ambiguous reported engine name")
    if any(line.startswith(b"bestmove") for line in lines):
        raise ValueError("unsolicited UCI response during initialization")
    if final:
        if lines.count(b"readyok") != 1 or lines.index(b"readyok") < lines.index(b"uciok"):
            raise ValueError("duplicate or out-of-order ready acknowledgement")
    elif b"readyok" in lines:
        raise ValueError("unsolicited UCI response during initialization")
    options = {}
    ponder = None
    for index, line in enumerate(lines):
        parts = line.split()
        if len(parts) < 2 or parts[:2] != [b"option", b"name"]:
            continue
        if index > lines.index(b"uciok"):
            raise ValueError("UCI option declared after uciok")
        if len(parts) < 3:
            raise ValueError("malformed UCI option declaration")
        match = _SPIN.fullmatch(line)
        if match:
            name = match.group(1)
            if name in options:
                raise ValueError("duplicate upstream resource option")
            values = tuple(int(value) for value in match.groups()[1:])
            if values != _EXPECTED[name]:
                raise ValueError("upstream resource option declaration differs")
            options[name] = values
            continue
        if parts[2] in (b"Hash", b"Threads"):
            raise ValueError("malformed upstream resource option")
        if parts[2] == b"Ponder":
            match = _PONDER.fullmatch(line)
            if match is None or ponder is not None:
                raise ValueError("malformed or duplicate Ponder option")
            ponder = match.group(1).decode("ascii")
    if set(options) != set(_EXPECTED):
        raise ValueError("required upstream resource options unavailable")
    if not options[b"Hash"][1] <= resources["hash_mib"] <= options[b"Hash"][2]:
        raise ValueError("requested Hash outside declared range")
    if not options[b"Threads"][1] <= resources["workers"] <= options[b"Threads"][2]:
        raise ValueError("requested Threads outside declared range")
    return ponder


def configure_owned(owned, *, peer, profile, verify_owned_policy, timeout_seconds=60):
    """Send resource options to an already owned peer; never grant score GO.

    ``verify_owned_policy(owned, resources)`` must validate owned-process
    identity and fixed CPU, NUMA and hard-limit configuration and return exactly
    True. It must not test current free/available memory or cgroup remaining
    capacity. This hook is a caller contract, not independent authentication.
    The caller remains responsible for cleanup if any operation fails.
    """
    if type(peer) is not str or peer not in _NAMES or type(profile) is not str or profile not in _PROFILES:
        raise ValueError("unsupported original peer or TEST profile")
    if (not callable(verify_owned_policy) or isinstance(timeout_seconds, bool) or
            type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or
            not 0 < timeout_seconds <= 600):
        raise ValueError("a bounded timeout and explicit owned-policy check are required")
    resources = dict(_PROFILES[profile])
    resources["tt_bytes_expected_if_entry_8"] = resources["hash_mib"] * (1 << 20)
    started = time.monotonic()

    def remaining():
        value = timeout_seconds - (time.monotonic() - started)
        if value <= 0:
            raise TimeoutError("original peer UCI setup timed out")
        return value

    def until_line(line):
        owned.stdout.until(lambda raw: line in _complete_lines(raw), owned.budget, seconds=remaining())

    # An already-used output buffer could supply a stale uciok/readyok.
    if owned.stdout.bytes() != b"":
        raise ValueError("a fresh original UCI output stream is required")
    owned.send(b"uci\n")
    until_line(b"uciok")
    ponder_default = _check_startup(owned.stdout.bytes(), peer, resources)
    # Validate identity and static placement before Hash; do not gate on a
    # point-in-time free-memory or cgroup-remaining observation.
    if verify_owned_policy(owned, dict(resources)) is not True:
        raise ValueError("original peer ownership or fixed policy rejected")
    remaining()
    owned.send(f"setoption name Hash value {resources['hash_mib']}\n".encode("ascii"))
    owned.send(f"setoption name Threads value {resources['workers']}\n".encode("ascii"))
    if ponder_default is not None:
        owned.send(b"setoption name Ponder value false\n")
    remaining()
    owned.send(b"isready\n")
    until_line(b"readyok")
    if _check_startup(owned.stdout.bytes(), peer, resources, final=True) != ponder_default:
        raise ValueError("original peer option declarations changed during setup")
    return {
        "format": "original-peer-uci-test-v1", "peer": peer, "profile": profile,
        "resources_requested": resources, "reported_name": _NAMES[peer].decode("ascii"),
        "ponder": "not-declared" if ponder_default is None else "false-requested",
        "available_memory_preflight": False, "uci_ready_observed": True,
        "source_identity_authenticated": False,
        "tt_abi_observed": False, "tt_allocation_observed": False,
        "worker_placement_observed": False, "runtime_qualified": False,
        "league_qualified": False, "scored_game_admitted": False,
        "limitations": ["owned-policy verification is supplied by caller and is not independent authentication",
                        "setoption has no acknowledgement; readyok does not prove allocation",
                        "UCI main thread and search workers require separate live observation",
                        "original time manager ignores increment tokens",
                        "ucinewgame clears the table and must be observed separately"],
    }
