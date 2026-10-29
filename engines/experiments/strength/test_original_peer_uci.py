"""Small, fake-owned UCI tests; no engine, allocation, or external process."""
from __future__ import annotations

import unittest

import original_peer_uci as subject


def startup(peer, *, options=None):
    if options is None:
        options = (b"option name Hash type spin default 8 min 1 max 67108864\n"
                   b"option name Threads type spin default 1 min 1 max 2048\n")
    return subject._NAMES[peer] + b"\r\nid author example\n" + options + b"uciok\n"


class FakeOutput:
    def __init__(self, data=b""):
        self.data = data

    def bytes(self):
        return self.data

    def until(self, predicate, budget, seconds):
        if seconds <= 0 or not predicate(self.data):
            raise TimeoutError("expected complete acknowledgement unavailable")


class FakeOwned:
    def __init__(self, peer="ice4", *, initial=b"", greeting=None, ready=b"readyok\n"):
        self.stdout = FakeOutput(initial)
        self.budget = object()
        self.greeting = startup(peer) if greeting is None else greeting
        self.ready = ready
        self.sent = []

    def send(self, command):
        self.sent.append(command)
        if command == b"uci\n":
            self.stdout.data += self.greeting
        if command == b"isready\n":
            self.stdout.data += self.ready


class OriginalPeerUciTests(unittest.TestCase):
    def configure(self, owned, *, peer="ice4", profile="test-p16", guard=None, timeout=60):
        if guard is None:
            guard = lambda owner, resources: True
        return subject.configure_owned(owned, peer=peer, profile=profile,
                                       verify_owned_policy=guard, timeout_seconds=timeout)

    def test_both_upstream_names_and_resource_profiles(self):
        for peer in ("ice4", "c4ke"):
            for profile, size, workers in (("test-p16", 16384, 16), ("test-p192", 262144, 192)):
                with self.subTest(peer=peer, profile=profile):
                    owned = FakeOwned(peer)
                    seen = []
                    result = self.configure(owned, peer=peer, profile=profile,
                                            guard=lambda owner, values: seen.append((owner, values)) or True)
                    self.assertEqual(owned.sent, [b"uci\n", f"setoption name Hash value {size}\n".encode(),
                                                  f"setoption name Threads value {workers}\n".encode(), b"isready\n"])
                    self.assertEqual(seen[0][0], owned)
                    self.assertEqual(seen[0][1]["tt_bytes_expected_if_entry_8"], size << 20)
                    self.assertEqual(set(seen[0][1]), {"workers", "hash_mib", "tt_bytes_expected_if_entry_8"})
                    self.assertEqual(result["ponder"], "not-declared")
                    self.assertTrue(result["uci_ready_observed"])
                    for name in ("available_memory_preflight", "source_identity_authenticated", "tt_abi_observed", "tt_allocation_observed",
                                 "worker_placement_observed", "runtime_qualified", "league_qualified",
                                 "scored_game_admitted"):
                        self.assertIs(result[name], False)
                    self.assertTrue(any("increment" in item for item in result["limitations"]))
                    self.assertTrue(any("main thread" in item for item in result["limitations"]))

    def test_ponder_when_declared_is_disabled(self):
        greeting = startup("ice4").replace(b"uciok\n", b"option name Ponder type check default true\nuciok\n")
        owned = FakeOwned(greeting=greeting)
        result = self.configure(owned)
        self.assertEqual(result["ponder"], "false-requested")
        self.assertEqual(owned.sent[-2:], [b"setoption name Ponder value false\n", b"isready\n"])

    def test_bad_or_duplicate_declarations_do_not_allocate(self):
        base = startup("ice4")
        cases = [base.replace(b"min 1 max 67108864", b"min 1 max 100"),
                 base.replace(b"type spin default 8", b"type string default 8"),
                 base.replace(b"uciok\n", b"option name Hash type spin default 8 min 1 max 67108864\nuciok\n"),
                 base.replace(b"uciok\n", b"option name Hash\nuciok\n"),
                 base.replace(b"uciok\n", b"option name Hash\ttype spin default 8 min 1 max 67108864\nuciok\n"),
                 base.replace(b"uciok\n", b"option name Ponder\nuciok\n"),
                 base.replace(b"uciok\n", b"option name Ponder type spin default 1 min 0 max 1\nuciok\n"),
                 base.replace(b"id name ice4 v6.1", b"id name different"),
                 base.replace(b"uciok\n", b"uciok\nuciok\n"),
                 base.replace(b"uciok\n", b"readyok\nuciok\n"),
                 base.replace(b"uciok\n", b"bestmove e2e4\nuciok\n")]
        for greeting in cases:
            with self.subTest(greeting=greeting):
                owned = FakeOwned(greeting=greeting)
                with self.assertRaises(ValueError):
                    self.configure(owned)
                self.assertEqual(owned.sent, [b"uci\n"])

    def test_owned_policy_must_be_explicit_boolean_true_before_hash(self):
        for decision in (False, 1, None):
            with self.subTest(decision=decision):
                owned = FakeOwned()
                with self.assertRaises(ValueError):
                    self.configure(owned, guard=lambda _owner, _resources: decision)
                self.assertEqual(owned.sent, [b"uci\n"])

    def test_no_available_memory_input_is_needed_for_setup(self):
        owned = FakeOwned("c4ke")
        seen = []
        result = self.configure(owned, peer="c4ke", profile="test-p192",
                                guard=lambda owner, fixed: seen.append((owner, fixed)) or True)
        self.assertEqual(seen, [(owned, {"workers": 192, "hash_mib": 262144,
                                         "tt_bytes_expected_if_entry_8": 256 << 30})])
        self.assertIn(b"setoption name Hash value 262144\n", owned.sent)
        self.assertFalse(result["tt_allocation_observed"])

    def test_wrong_peer_profile_and_timeout_rejected_without_sending(self):
        for kwargs in ({"peer": "ice4\nquit"}, {"profile": "test-p192\nquit"},
                       {"timeout": True}, {"timeout": 0}, {"timeout": float("nan")},
                       {"timeout": 601}):
            with self.subTest(kwargs=kwargs):
                owned = FakeOwned()
                with self.assertRaises(ValueError):
                    self.configure(owned, **kwargs)
                self.assertEqual(owned.sent, [])

    def test_partial_stale_duplicate_and_missing_acks_fail(self):
        cases = [FakeOwned(initial=b"stale\n"), FakeOwned(greeting=startup("ice4")[:-1]),
                 FakeOwned(ready=b"readyok"), FakeOwned(ready=b"readyok\nreadyok\n"),
                 FakeOwned(ready=b"option name Hash type spin default 8 min 1 max 67108864\nreadyok\n"),
                 FakeOwned(ready=b"option name Ponder type check default false\nreadyok\n"),
                 FakeOwned(ready=b"bestmove e2e4\nreadyok\n")]
        for owned in cases:
            with self.subTest(owned=owned):
                with self.assertRaises((ValueError, TimeoutError)):
                    self.configure(owned)

    def test_guard_cannot_change_requested_values(self):
        owned = FakeOwned()
        def mutate(_owner, values):
            values["hash_mib"] = 1
            values["workers"] = 1
            return True
        result = self.configure(owned, profile="test-p192", guard=mutate)
        self.assertEqual(result["resources_requested"]["hash_mib"], 262144)
        self.assertIn(b"setoption name Hash value 262144\n", owned.sent)


if __name__ == "__main__":
    unittest.main()
