"""Wave validation plus bounded toy/real-runner fault checks outside Git.

The CLI runtime checks are protocol fixtures only. They do not admit engines,
produce league scores, or supply training examples.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


wave = module("checked_rove_wave", HERE / "wave.py")


class Contracts(unittest.TestCase):
    def test_terminal_gate_class_never_promotes_uncertain_delivery(self):
        self.assertEqual(wave._terminal_gate_class({}), ("completed", "completed"))
        self.assertEqual(wave._terminal_gate_class({"gate_transport": "sent"}), ("completed", "completed"))
        self.assertEqual(wave._terminal_gate_class({"gate_transport": "uncertain"}),
                         ("delivery_uncertain", "delivery_unresolved"))
        for key in ("gate_transport_observation_error", "gate_release_event_error"):
            self.assertEqual(wave._terminal_gate_class({"gate_transport": "sent", key: "failed"}),
                             ("delivery_uncertain", "delivery_unresolved"))
        self.assertEqual(wave._terminal_gate_class({"gate_cancelled": True}), ("cancelled", "cancelled_before_go"))
        self.assertEqual(wave._terminal_gate_class({"gate_cancelled": True, "gate_authorized": True}),
                         ("cancelled", "cancelled_unreconciled"))
        self.assertEqual(wave._terminal_gate_class({"gate_cancelled": True, "gate_authorization_unknown": True}),
                         ("cancelled", "cancelled_unreconciled"))

    @staticmethod
    def release_children(*, fail_index=None):
        timeline = []

        class Gate:
            def __init__(self, index):
                self.index = index
            def sendall(self, data):
                timeline.append(("send", self.index, data))
                if self.index == fail_index and data == b"GO\n":
                    raise OSError("partial transport fixture")
            def shutdown(self, how):
                timeline.append(("shutdown", self.index, how))

        children = []
        for index in range(3):
            job = wave.WaveJob(f"game-{index}", ("/tmp/engine",), {},
                               {"game": f"game-{index}", "attempt_id": f"attempt-{index:08d}"}, Path(f"/tmp/engine-{index}"))
            obs = {"gate_released": False, "status": "ready"}
            children.append(wave._Child(job, dict(job.start_job), obs, control=Gate(index)))
        return children, timeline

    def test_per_game_denial_drains_only_unsent_gates(self):
        children, timeline = self.release_children()
        def authorize(job, observation):
            timeline.append(("authorize", job.identity))
            return job.identity != "game-1"
        def observe(job, observation):
            timeline.append(("observe", job.identity, observation["gate_transport"]))
        def emit(name, child):
            timeline.append(("event", child.job.identity, name))
        drained = wave._release_individually(children, lambda child: dict(child.observation), authorize, observe, emit)
        self.assertTrue(drained)
        self.assertEqual(timeline, [("authorize", "game-0"), ("send", 0, b"GO\n"),
            ("observe", "game-0", "sent"), ("event", "game-0", "released"),
            ("authorize", "game-1"), ("send", 1, b"ABORT\n"), ("send", 2, b"ABORT\n")])
        self.assertTrue(children[0].observation["gate_released"])
        self.assertTrue(children[1].observation["gate_cancelled"])
        self.assertFalse(children[1].observation["gate_authorized"])
        self.assertFalse(children[2].observation["gate_authorized"])

    def test_drain_notification_occurs_once_before_remaining_gates_are_cancelled(self):
        children, timeline = self.release_children()
        wave._release_individually(children, lambda child: dict(child.observation),
            lambda job, obs: job.identity != "game-1", lambda job, obs: None,
            lambda name, child: None,
            notify_drain=lambda child, reason: timeline.append(("drain", child.job.identity, reason)))
        self.assertEqual([row for row in timeline if row[0] == "drain"],
                         [("drain", "game-1", "authorization_denied")])
        self.assertLess(timeline.index(("drain", "game-1", "authorization_denied")),
                        timeline.index(("send", 1, b"ABORT\n")))
        self.assertNotIn(("send", 0, b"ABORT\n"), timeline)

    @staticmethod
    def fence(job, observation, start=99, end=101, *, game_id=None, binding=None):
        return wave.ReleaseFence(job.identity if game_id is None else game_id, "fence-1",
            observation["gate_fence_binding_sha256"] if binding is None else binding, start, end)

    def test_fence_checks_exact_game_attempt_and_local_time(self):
        for kind in ("other_game", "other_attempt", "expired", "not_yet_valid", "malformed", "error"):
            with self.subTest(kind=kind):
                children, timeline = self.release_children()
                seen = []
                def fencing(job, observation):
                    if kind == "other_game":
                        return self.fence(job, observation, game_id="other")
                    if kind == "other_attempt":
                        return self.fence(job, observation, binding="0" * 64)
                    if kind == "expired":
                        return self.fence(job, observation, 99, 100)
                    if kind == "not_yet_valid":
                        return self.fence(job, observation, 101, 102)
                    if kind == "malformed":
                        return True
                    raise RuntimeError("fence source unavailable")
                with patch.object(wave.time, "monotonic", return_value=100):
                    wave._release_individually(children, lambda child: dict(child.observation),
                        lambda job, obs: True, lambda job, obs: None, lambda name, child: None,
                        release_fence=fencing, notify_drain=lambda child, why: seen.append(why))
                self.assertTrue(children[0].observation["gate_authorized"])
                self.assertTrue(children[0].observation["gate_cancelled"])
                self.assertEqual(children[0].observation["gate_transport"], "not_attempted")
                self.assertEqual(wave._terminal_gate_class(children[0].observation)[1], "cancelled_unreconciled")
                self.assertNotIn(("send", 0, b"GO\n"), timeline)
                self.assertNotIn(("send", 1, b"GO\n"), timeline)
                self.assertEqual(len(seen), 1)

    def test_fence_types_and_window_bounds_reject_ambiguous_values(self):
        for start, end in ((True, 101), (99, float("nan")), (99, float("inf")),
                           (-1, 1), (100, 100), (100, 161)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                wave.ReleaseFence("game", "fence-1", "1" * 64, start, end)

    def test_valid_fence_is_checked_after_callback_and_admission_deadline(self):
        children, timeline = self.release_children()
        now = [100.0]
        def fencing(job, observation):
            now[0] = 102.0
            return self.fence(job, observation, 99, 103)
        with patch.object(wave.time, "monotonic", side_effect=lambda: now[0]):
            wave._release_individually(children, lambda child: dict(child.observation),
                lambda job, obs: True, lambda job, obs: None, lambda name, child: None,
                deadline=101, release_fence=fencing)
        self.assertEqual(children[0].observation["drain_reason"], "deadline_before_go")
        self.assertNotIn(("send", 0, b"GO\n"), timeline)

    def test_send_crossing_fence_expiry_is_uncertain_and_never_retried(self):
        children, timeline = self.release_children()
        now = [100.0]
        gate = children[0].control
        original = gate.sendall
        def delayed(data):
            original(data)
            if data == b"GO\n":
                now[0] = 101.0
        gate.sendall = delayed
        observed, notifications = [], []
        with patch.object(wave.time, "monotonic", side_effect=lambda: now[0]):
            wave._release_individually(children, lambda child: dict(child.observation),
                lambda job, obs: True, lambda job, obs: observed.append((job.identity, obs["gate_transport"])),
                lambda name, child: None, release_fence=self.fence,
                notify_drain=lambda child, why: notifications.append(why))
        self.assertEqual(observed, [("game-0", "uncertain")])
        self.assertTrue(children[0].observation["gate_fence_send_time_uncertain"])
        self.assertTrue(children[0].observation["gate_released"])
        self.assertEqual(wave._terminal_gate_class(children[0].observation)[1], "delivery_unresolved")
        self.assertEqual(notifications, ["release_fence_send_time_uncertain"])
        self.assertEqual(timeline.count(("send", 0, b"GO\n")), 1)
        self.assertNotIn(("send", 0, b"ABORT\n"), timeline)
        self.assertNotIn(("send", 1, b"GO\n"), timeline)

    def test_send_crossing_admission_deadline_is_uncertain_even_with_live_fence(self):
        children, timeline = self.release_children()
        now = [100.0]
        gate = children[0].control
        original = gate.sendall
        def delayed(data):
            original(data)
            if data == b"GO\n":
                now[0] = 101.0
        gate.sendall = delayed
        with patch.object(wave.time, "monotonic", side_effect=lambda: now[0]):
            wave._release_individually(children, lambda child: dict(child.observation),
                lambda job, obs: True, lambda job, obs: None, lambda name, child: None,
                deadline=101, release_fence=lambda job, obs: self.fence(job, obs, 99, 102))
        self.assertEqual(children[0].observation["gate_transport"], "uncertain")
        self.assertEqual(wave._terminal_gate_class(children[0].observation)[1], "delivery_unresolved")
        self.assertNotIn(("send", 0, b"ABORT\n"), timeline)
        self.assertNotIn(("send", 1, b"GO\n"), timeline)

    def test_per_game_partial_go_is_uncertain_and_does_not_kill_prior_game(self):
        children, timeline = self.release_children(fail_index=1)
        def observe(job, observation):
            timeline.append(("observe", job.identity, observation["gate_transport"]))
        wave._release_individually(children, lambda child: dict(child.observation), lambda job, obs: True,
                                   observe, lambda name, child: None,
                                   notify_drain=lambda child, reason: timeline.append(("drain", child.job.identity, reason)))
        self.assertEqual(children[1].observation["gate_transport"], "uncertain")
        self.assertTrue(children[1].observation["gate_authorized"])
        self.assertFalse(children[1].observation["gate_released"])
        self.assertIn(("observe", "game-1", "uncertain"), timeline)
        self.assertIn(("send", 2, b"ABORT\n"), timeline)
        self.assertNotIn(("send", 0, b"ABORT\n"), timeline)
        self.assertNotIn(("send", 1, b"ABORT\n"), timeline)
        self.assertEqual([row for row in timeline if row[0] == "drain"],
                         [("drain", "game-1", "go_transport_uncertain")])

    def test_release_observer_failure_prevents_new_go_and_preserves_sent_game(self):
        children, timeline = self.release_children()
        def broken(job, observation):
            raise RuntimeError("durable observation failed")
        wave._release_individually(children, lambda child: dict(child.observation), lambda job, obs: True,
                                   broken, lambda name, child: None,
                                   notify_drain=lambda child, reason: timeline.append(("drain", child.job.identity, reason)))
        self.assertTrue(children[0].observation["gate_released"])
        self.assertIn("durable observation failed", children[0].observation["gate_transport_observation_error"])
        self.assertNotIn(("send", 0, b"ABORT\n"), timeline)
        self.assertIn(("send", 1, b"ABORT\n"), timeline)
        self.assertIn(("send", 2, b"ABORT\n"), timeline)
        self.assertEqual([row for row in timeline if row[0] == "drain"],
                         [("drain", "game-0", "transport_observation_failed")])

    def test_lost_authorization_response_is_not_a_known_pre_authorization_cancel(self):
        children, timeline = self.release_children()
        def broken(job, observation):
            raise RuntimeError("authorization response lost")
        wave._release_individually(children, lambda child: dict(child.observation), broken,
                                   lambda job, obs: None, lambda name, child: None)
        self.assertTrue(children[0].observation["gate_authorization_unknown"])
        self.assertTrue(children[0].observation["gate_cancelled"])
        self.assertEqual(children[0].observation["gate_transport"], "not_attempted")
        self.assertNotIn(("send", 0, b"GO\n"), timeline)

    def test_non_boolean_authorization_response_is_uncertain(self):
        for response in (None, 1, "yes"):
            children, timeline = self.release_children()
            with self.subTest(response=response):
                wave._release_individually(children, lambda child: dict(child.observation),
                    lambda job, obs: response, lambda job, obs: None, lambda name, child: None)
                self.assertTrue(children[0].observation["gate_authorization_unknown"])
                self.assertTrue(children[0].observation["gate_cancelled"])
                self.assertNotIn(("send", 0, b"GO\n"), timeline)

    def test_elapsed_deadline_after_authorization_never_sends_stale_go(self):
        children, timeline = self.release_children()
        with patch.object(wave.time, "monotonic", side_effect=[99.0, 100.0] + [100.0] * 10):
            wave._release_individually(children, lambda child: dict(child.observation),
                                       lambda job, obs: True, lambda job, obs: None,
                                       lambda name, child: None, deadline=100.0)
        self.assertTrue(children[0].observation["gate_authorized"])
        self.assertTrue(children[0].observation["gate_cancelled"])
        self.assertEqual(children[0].observation["gate_transport"], "not_attempted")
        self.assertIn("deadline expired after authorization", children[0].observation["gate_transport_error"])
        self.assertEqual([row for row in timeline if row[0] == "send"],
                         [("send", 0, b"ABORT\n"), ("send", 1, b"ABORT\n"), ("send", 2, b"ABORT\n")])

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_real_gate_denial_keeps_already_sent_toy_running_until_natural_exit(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-drain-") as folder:
            root = Path(folder)
            script = root / "toy.py"
            script.write_text(TOY)
            jobs = []
            for index in range(3):
                target = root / str(index)
                argv = (sys.executable, str(script), "brief", str(target / "events.jsonl"))
                jobs.append(wave.WaveJob(f"game-{index}", argv, {}, {"game": str(index)}, target))
            seen = []
            results = wave.WaveExecutor().run_wave(jobs, 5,
                authorize_go=lambda job, obs: job.identity != "game-1",
                observe_transport=lambda job, obs: seen.append((job.identity, obs["gate_transport"])))
            self.assertEqual(seen, [("game-0", "sent")])
            self.assertEqual(results[0]["status"], "completed")
            self.assertEqual(results[0]["returncode"], 0)
            self.assertFalse(results[0]["cleanup_forced"])
            self.assertTrue(results[0]["gate_released"])
            self.assertEqual([row["status"] for row in results[1:]], ["cancelled_before_go"] * 2)
            self.assertTrue(all(row["gate_cancelled"] and not row["gate_released"] for row in results[1:]))
            self.assertTrue(all(not row["remaining_processes"] and row["readers_done"] for row in results))

    @unittest.skipUnless(sys.platform == "linux", "Linux admission boundary")
    def test_per_game_release_requires_both_authority_and_transport_ports(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-ports-") as folder:
            out = Path(folder) / "not-created"
            job = wave.WaveJob("x", ("/does-not-exist",), {}, {"game": "x"}, out)
            for options in ({"authorize_go": lambda job, obs: True},
                            {"observe_transport": lambda job, obs: None}):
                with self.subTest(options=options), self.assertRaisesRegex(ValueError, "supplied together"):
                    wave.WaveExecutor().run_wave([job], 1, **options)
                self.assertFalse(out.exists())

            with self.assertRaisesRegex(ValueError, "drain notification requires"):
                wave.WaveExecutor().run_wave([job], 1, on_drain=lambda *args: None)
            with self.assertRaisesRegex(ValueError, "release fence requires"):
                wave.WaveExecutor().run_wave([job], 1, release_fence=lambda *args: None)
            with self.assertRaisesRegex(ValueError, "distinct explicit attempt identities"):
                wave.WaveExecutor().run_wave([job], 1, authorize_go=lambda *args: True,
                    observe_transport=lambda *args: None, release_fence=lambda *args: None)
            duplicate = [wave.WaveJob(f"g-{i}", ("/does-not-exist",), {},
                         {"attempt_id": "same-attempt-0001"}, Path(folder) / str(i)) for i in range(2)]
            with self.assertRaisesRegex(ValueError, "distinct explicit attempt identities"):
                wave.WaveExecutor().run_wave(duplicate, 1, authorize_go=lambda *args: True,
                    observe_transport=lambda *args: None, release_fence=lambda *args: None)
            self.assertTrue(all(not item.out.exists() for item in duplicate))
            self.assertFalse(out.exists())

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_expired_second_game_fence_preserves_first_real_toy(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-fence-") as folder:
            root = Path(folder)
            script = root / "toy.py"
            script.write_text(TOY)
            jobs = []
            for index in range(2):
                target = root / str(index)
                argv = (sys.executable, str(script), "brief", str(target / "events.jsonl"))
                jobs.append(wave.WaveJob(f"game-{index}", argv, {},
                    {"game": str(index), "attempt_id": f"attempt-{index:08d}"}, target))
            notices, receipts = [], []
            def fencing(job, observation):
                now = time.monotonic()
                return self.fence(job, observation, now - 1, now + 10 if job.identity == "game-0" else now)
            results = wave.WaveExecutor().run_wave(jobs, 5,
                authorize_go=lambda job, obs: True, release_fence=fencing,
                observe_transport=lambda job, obs: receipts.append((job.identity, obs["gate_transport"])),
                on_drain=lambda reason, job, obs: notices.append((reason, job.identity)))
            self.assertEqual(receipts, [("game-0", "sent")])
            self.assertEqual(notices, [("release_fence_not_valid", "game-1")])
            self.assertEqual(results[0]["status"], "completed")
            self.assertEqual(results[0]["returncode"], 0)
            self.assertFalse(results[0]["cleanup_forced"])
            self.assertEqual(results[1]["status"], "cancelled_unreconciled")
            self.assertTrue(results[1]["gate_authorized"])
            self.assertTrue(all(not row["remaining_processes"] for row in results))

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_failed_global_drain_notification_still_preserves_sent_game(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-drain-notify-") as folder:
            root = Path(folder)
            script = root / "toy.py"
            script.write_text(TOY)
            jobs = []
            for index in range(3):
                target = root / str(index)
                argv = (sys.executable, str(script), "brief", str(target / "events.jsonl"))
                jobs.append(wave.WaveJob(f"game-{index}", argv, {}, {"game": str(index)}, target))
            notifications = []
            def failed(reason, job, observation):
                notifications.append((reason, job.identity, observation["gate_transport"]))
                raise RuntimeError("coordinator unavailable")
            results = wave.WaveExecutor().run_wave(jobs, 5,
                authorize_go=lambda job, obs: job.identity != "game-1",
                observe_transport=lambda job, obs: None, on_drain=failed)
            self.assertEqual(notifications, [("authorization_denied", "game-1", "not_attempted")])
            self.assertEqual(results[1]["drain_notification"], "failed")
            self.assertIn("coordinator unavailable", results[1]["drain_notification_error"])
            self.assertEqual(results[0]["status"], "completed")
            self.assertEqual(results[0]["returncode"], 0)
            self.assertFalse(results[0]["cleanup_forced"])
            self.assertTrue(all(row["gate_cancelled"] for row in results[1:]))
            self.assertTrue(all(not row["remaining_processes"] for row in results))

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_expired_admission_deadline_does_not_kill_earlier_sent_game(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-deadline-") as folder:
            root = Path(folder)
            script = root / "toy.py"
            script.write_text(TOY)
            jobs = []
            for index in range(2):
                target = root / str(index)
                argv = (sys.executable, str(script), "five", str(target / "events.jsonl"))
                jobs.append(wave.WaveJob(f"game-{index}", argv, {}, {"game": str(index)}, target))
            def authorize(job, observation):
                if job.identity == "game-1":
                    time.sleep(4.1)  # Expires only the pre-GO admission deadline.
                return True
            results = wave.WaveExecutor().run_wave(jobs, 4, authorize_go=authorize,
                observe_transport=lambda job, obs: None)
            self.assertEqual(results[0]["status"], "completed")
            self.assertEqual(results[0]["returncode"], 0)
            self.assertFalse(results[0]["cleanup_forced"])
            self.assertEqual(results[1]["status"], "cancelled_unreconciled")
            self.assertTrue(results[1]["gate_authorized"])
            self.assertEqual(results[1]["gate_transport"], "not_attempted")
            self.assertTrue(all(not row["remaining_processes"] and row["readers_done"] for row in results))

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_stuck_unstarted_gate_alone_is_cleaned_while_sent_game_finishes(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-cancel-") as folder:
            root = Path(folder)
            script = root / "toy.py"
            script.write_text(TOY)
            jobs = []
            for index, mode in enumerate(("three", "ignore_abort")):
                target = root / str(index)
                argv = (sys.executable, str(script), mode, str(target / "events.jsonl"))
                jobs.append(wave.WaveJob(f"game-{index}", argv, {}, {"game": str(index)}, target))
            results = wave.WaveExecutor().run_wave(jobs, 5,
                authorize_go=lambda job, obs: job.identity == "game-0",
                observe_transport=lambda job, obs: None)
            self.assertEqual(results[0]["returncode"], 0)
            self.assertFalse(results[0]["cleanup_forced"])
            self.assertTrue(results[1]["gate_cancelled"])
            self.assertEqual(results[1]["gate_transport"], "not_attempted")
            self.assertTrue(results[1]["cleanup_forced"])
            self.assertTrue(all(not row["remaining_processes"] and row["readers_done"] for row in results))

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_cancelled_receipt_failure_quarantines_but_does_not_kill_sent_game(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-journal-") as folder:
            root = Path(folder)
            script = root / "toy.py"
            script.write_text(TOY)
            jobs = []
            for index, mode in enumerate(("three", "brief")):
                target = root / str(index)
                argv = (sys.executable, str(script), mode, str(target / "events.jsonl"))
                jobs.append(wave.WaveJob(f"game-{index}", argv, {}, {"game": str(index)}, target))
            notices = []
            def event(name, job, observation):
                if name == "cancelled":
                    raise RuntimeError("fixture durable receipt failed")
            results = wave.WaveExecutor().run_wave(jobs, 5, on_event=event,
                authorize_go=lambda job, obs: job.identity == "game-0",
                observe_transport=lambda job, obs: None,
                on_drain=lambda reason, job, obs: notices.append((reason, job.identity)))
            self.assertEqual(results[0]["returncode"], 0)
            self.assertFalse(results[0]["cleanup_forced"])
            self.assertTrue(results[0].get("event_error"))
            self.assertTrue(results[1]["gate_cancelled"])
            self.assertTrue(all(not row["remaining_processes"] and row["readers_done"] for row in results))
            # The denied GO triggered the first drain notification; the later
            # receipt failure must not send a duplicate notification.
            self.assertEqual(notices, [("authorization_denied", "game-1")])

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_completed_receipt_failure_notifies_drain_without_killing_sibling(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-complete-notify-") as folder:
            root = Path(folder)
            script = root / "toy.py"
            script.write_text(TOY)
            jobs = []
            for index, mode in enumerate(("brief", "three")):
                target = root / str(index)
                argv = (sys.executable, str(script), mode, str(target / "events.jsonl"))
                jobs.append(wave.WaveJob(f"game-{index}", argv, {}, {"game": str(index)}, target))
            notices = []
            def event(name, job, observation):
                if name == "completed":
                    raise RuntimeError("fixture completion receipt failed")
            results = wave.WaveExecutor().run_wave(jobs, 5, on_event=event,
                authorize_go=lambda job, obs: True, observe_transport=lambda job, obs: None,
                on_drain=lambda reason, job, obs: notices.append((reason, job.identity)))
            self.assertEqual(notices, [("completion_event_failed", "game-0")])
            self.assertEqual(results[1]["returncode"], 0)
            self.assertFalse(results[1]["cleanup_forced"])
            self.assertTrue(all(not row["remaining_processes"] for row in results))

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_partial_real_gate_delivery_stays_unresolved_after_original_owner_exit(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-uncertain-") as folder:
            root = Path(folder)
            script = root / "toy.py"
            script.write_text(TOY)
            jobs = []
            for index, mode in enumerate(("three", "brief")):
                target = root / str(index)
                argv = (sys.executable, str(script), mode, str(target / "events.jsonl"))
                jobs.append(wave.WaveJob(f"game-{index}", argv, {}, {"game": str(index)}, target))
            original = wave.socket.socket.sendall
            sent_go = []
            events = []
            def partial(sock, data, *args):
                if data == b"GO\n":
                    sent_go.append(sock)
                    if len(sent_go) == 2:
                        original(sock, b"G")
                        raise OSError("injected partial GO")
                return original(sock, data, *args)
            with patch.object(wave.socket.socket, "sendall", partial):
                results = wave.WaveExecutor().run_wave(jobs, 5,
                    authorize_go=lambda job, obs: True, observe_transport=lambda job, obs: None,
                    on_event=lambda name, job, obs: events.append((name, job.identity)))
            self.assertEqual(results[0]["returncode"], 0)
            self.assertFalse(results[0]["cleanup_forced"])
            self.assertEqual(results[1]["gate_transport"], "uncertain")
            self.assertEqual(results[1]["status"], "delivery_unresolved")
            self.assertIn(("delivery_uncertain", "game-1"), events)
            self.assertNotIn(("completed", "game-1"), events)
            self.assertTrue(all(not row["remaining_processes"] and row["readers_done"] for row in results))

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_failed_transport_receipt_never_promotes_naturally_finished_child(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-receipt-") as folder:
            root = Path(folder)
            script = root / "toy.py"
            script.write_text(TOY)
            jobs = []
            for index in range(2):
                target = root / str(index)
                argv = (sys.executable, str(script), "brief", str(target / "events.jsonl"))
                jobs.append(wave.WaveJob(f"game-{index}", argv, {}, {"game": str(index)}, target))
            events = []
            def bad_receipt(job, observation):
                raise RuntimeError("fixture transport receipt failed")
            results = wave.WaveExecutor().run_wave(jobs, 5,
                authorize_go=lambda job, obs: True, observe_transport=bad_receipt,
                on_event=lambda name, job, obs: events.append((name, job.identity)))
            self.assertEqual(results[0]["returncode"], 0)
            self.assertFalse(results[0]["cleanup_forced"])
            self.assertEqual(results[0]["gate_transport"], "sent")
            self.assertEqual(results[0]["status"], "delivery_unresolved")
            self.assertIn(("delivery_uncertain", "game-0"), events)
            self.assertNotIn(("completed", "game-0"), events)
            self.assertEqual(results[1]["status"], "cancelled_before_go")

    def test_ready_metadata_compares_json_types(self):
        self.assertFalse(wave._same_json({"slot": 1}, {"slot": True}))
        self.assertFalse(wave._same_json({"slot": 1}, {"slot": 1.0}))
        self.assertTrue(wave._same_json({"slot": 1, "game": "g"}, {"game": "g", "slot": 1}))

    def test_proc_exit_race_is_absence(self):
        with patch.object(Path, "read_text", side_effect=ProcessLookupError()):
            self.assertIsNone(wave._proc_identity(123))

    def test_unverified_identity_is_unknown_and_never_signalled(self):
        job = wave.WaveJob("unknown", ("/tmp/e",), {}, {"attempt_id": "unknown"}, Path("/tmp/unknown"))
        observed = {"pid": 123, "pgid": 123, "session": 123, "start_ticks": None, "ownership_unverified": True}
        child = wave._Child(job, {}, observed, process=type("OwnedHandle", (), {"pid": 123})())
        with patch.object(wave.os, "killpg") as killpg:
            self.assertEqual(wave._owned_members(child)[0]["state"], "ownership_unverified")
            self.assertFalse(wave._signal(child, 15))
            self.assertTrue(all(call.args == (123, 0) for call in killpg.call_args_list))
        self.assertNotIn("pid_reused", observed)

    def test_job_contract(self):
        with self.assertRaises(ValueError):
            wave.WaveJob("x", ("relative",), {}, {"attempt_id": "x"}, Path("/tmp/a"))
        with self.assertRaises(ValueError):
            wave.WaveJob("x", ("/tmp/e",), {}, {"x": float("nan")}, Path("/tmp/a"))
        with self.assertRaises(ValueError):
            wave.WaveJob("x", ("/tmp/e",), {}, {"attempt_id": "x"}, Path("relative"))
        job = wave.WaveJob("x", ("/tmp/e",), {}, {"attempt_id": "x"}, Path("/tmp/a"))
        self.assertEqual(job.id, "x")

    def test_bounded_executor_contract(self):
        with self.assertRaises(ValueError):
            wave.WaveExecutor(ready_seconds=181)
        with self.assertRaises(ValueError):
            wave.WaveExecutor(output_limit_bytes=0)

    @unittest.skipUnless(sys.platform == "linux", "Linux admission boundary")
    def test_duplicate_rejects_before_spawn_or_output(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-admission-") as temporary:
            out = Path(temporary) / "not-created"
            job = wave.WaveJob("same", ("/does-not-exist",), {}, {"attempt_id": "a"}, out)
            with self.assertRaisesRegex(ValueError, "distinct"):
                wave.WaveExecutor().run_wave([job, job], 1)
            self.assertFalse(out.exists())

    @unittest.skipUnless(sys.platform == "linux", "Linux admission boundary")
    def test_stale_engine_evidence_is_preserved_before_spawn(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-stale-") as temporary:
            for name in ("game.pgn", "raw.log", "config.json"):
                out = Path(temporary) / name.replace(".", "-")
                out.mkdir()
                evidence = out / name
                evidence.write_text("old evidence\n")
                job = wave.WaveJob(name, ("/does-not-exist",), {}, {"attempt_id": name}, out)
                with self.assertRaisesRegex(ValueError, "evidence already exists"):
                    wave.WaveExecutor().run_wave([job], 1)
                self.assertEqual(evidence.read_text(), "old evidence\n")
                self.assertFalse((out / "runner.stdout.log").exists())
            out = Path(temporary) / "broken-link"
            out.mkdir()
            (out / "raw.log").symlink_to(out / "absent-target")
            job = wave.WaveJob("broken-link", ("/does-not-exist",), {}, {"attempt_id": "broken-link"}, out)
            with self.assertRaisesRegex(ValueError, "evidence already exists"):
                wave.WaveExecutor().run_wave([job], 1)
            self.assertFalse((out / "absent-target").exists())


TOY = r'''import json, os, socket, sys, time
from pathlib import Path
mode, trace = sys.argv[1:3]
def note(event):
    with open(trace, 'a') as f: f.write(json.dumps({'event':event,'time':time.monotonic()})+'\n')
note('spawn')
if mode=='pre_exit': sys.exit(7)
if mode=='delayed': time.sleep(1.1)
control=socket.socket(fileno=int(os.environ['ROVE_START_FD']))
job=json.loads(os.environ['ROVE_START_JOB'])
if mode=='wrong_job': job['attempt_id']='different'
ready={'event':'READY','job':job,'white_clock_ms':1803000,'black_clock_ms':1803000}
if mode=='wrong_clock': ready['white_clock_ms']=1802999
control.sendall((json.dumps(ready)+'\n').encode())
data=b''
while b'\n' not in data:
    chunk=control.recv(32)
    if not chunk: sys.exit(3)
    data+=chunk
if data!=b'GO\n':
    note('abort')
    if mode=='ignore_abort': time.sleep(30)
    sys.exit(2)
note('go')
if mode=='long': time.sleep(10)
if mode=='brief': time.sleep(.2)
if mode=='three': time.sleep(3)
if mode=='five': time.sleep(5)
if mode=='flood':
    for _ in range(12): os.write(1,b'x'*65536)
if mode=='local_exit': sys.exit(9)
print('finished toy runner',flush=True)
print('toy stderr',file=sys.stderr,flush=True)
note('finish')
'''


def _external_out(out):
    if not out.is_absolute() or out.exists():
        raise ValueError("new absolute external evidence directory required")
    if any((parent / ".git").exists() for parent in (out, *out.parents)):
        raise ValueError("runtime evidence must remain outside Git")
    out.mkdir(parents=True)
    return out


def _read_rows(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def toy_checks(out: Path) -> dict:
    out = _external_out(out)
    script = out / "toy.py"
    script.write_text(TOY)
    cases = [
        ("delayed", ("normal", "delayed"), None, None, 5),
        ("pre_exit", ("normal", "pre_exit"), None, None, 5),
        ("wrong_job", ("normal", "wrong_job"), None, None, 5),
        ("wrong_clock", ("normal", "wrong_clock"), None, None, 5),
        ("denied", ("normal", "normal"), lambda: False, None, 5),
        ("release_exception", ("normal", "normal"), lambda: (_ for _ in ()).throw(RuntimeError("fixture release failure")), None, 5),
        ("local_exit", ("normal", "local_exit"), None, None, 5),
        ("wall", ("long", "long"), None, None, .3),
        ("partial_wall", ("normal", "long"), None, None, .3),
        ("event_exception", ("normal", "long"), None, None, 5),
        ("flood", ("flood", "normal"), None, None, 5),
        ("simultaneous_fault", ("normal", "flood"), None, None, 5),
        ("spawn_failure", ("normal", "missing"), None, None, 5),
    ]
    report = {"complete": False, "scope": "toy process/gate/fault checks; no engine acceptance", "cases": []}
    def save():
        (out / "toy-wave.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    for name, modes, release, _, wall in cases:
        directory = out / name
        directory.mkdir()
        jobs = []
        for index, mode in enumerate(modes):
            target = directory / str(index)
            argv = (sys.executable, str(script), mode, str(target / "events.jsonl"))
            if mode == "missing":
                argv = (str(out / "missing-executable"),)
            jobs.append(wave.WaveJob(f"{name}-{index}", argv, {},
                {"wave_id": name, "game_id": str(index), "attempt_id": f"{name}-{index}-1"}, target))
        events = []
        def event_callback(event, job, obs):
            events.append({"event": event, "identity": job.identity, "time": time.monotonic()})
            if name == "simultaneous_fault" and event == "released" and job.identity == jobs[0].identity:
                time.sleep(.08)  # Coalesce terminal EOF and sibling overflow into one poll batch.
            if name == "event_exception" and event == "tick" and any(item["event"] == "completed" for item in events):
                raise RuntimeError("fixture tick journal failure")
        before_fds = len(list(Path("/proc/self/fd").iterdir()))
        results = wave.WaveExecutor(output_limit_bytes=4096).run_wave(jobs, wall,
            release_callback=release, on_event=event_callback)
        report["cases"].append({"case": name, "observations": results, "events": events})
        save()
        if any(result["remaining_processes"] or not result["readers_done"] for result in results):
            raise AssertionError("owned runtime did not settle: " + repr(results))
        if len(list(Path("/proc/self/fd").iterdir())) != before_fds:
            raise AssertionError("wave leaked controller file descriptors: " + name)
        if name in ("delayed", "local_exit"):
            if any(result["wave_aborted"] for result in results):
                raise AssertionError("normal/local runner result aborted unrelated jobs")
            if max(result["ready_monotonic"] for result in results) > min(result["released_monotonic"] for result in results):
                raise AssertionError("a runner was released before all READY")
            if name == "local_exit" and sorted(result["returncode"] for result in results) != [0, 9]:
                raise AssertionError("individual nonzero runner exit was lost")
            if name == "delayed" and not any(event["event"] == "tick" and event["time"] - events[0]["time"] >= .7 for event in events):
                raise AssertionError("readiness wait emitted no continuing tick")
        elif name in ("partial_wall", "event_exception"):
            if results[0]["status"] != "completed" or results[0]["wave_aborted"] or results[0]["returncode"] != 0:
                raise AssertionError("earlier completed colour was discarded on later wave abort")
            if not results[1]["wave_aborted"] or not results[0].get("wave_error_context"):
                raise AssertionError("later interruption context was not preserved")
            completed = [event for event in events if event["event"] == "completed" and event["identity"] == jobs[0].identity]
            if len(completed) != 1 or completed[0]["time"] >= results[1]["completed_monotonic"]:
                raise AssertionError("completed event was not emitted while the other game was active")
        elif name == "flood":
            if not results[0]["wave_aborted"]:
                raise AssertionError("output overflow was accepted")
        elif name == "simultaneous_fault":
            if results[0]["status"] != "completed" or results[0]["wave_aborted"] or not results[1]["wave_aborted"]:
                raise AssertionError("terminal sibling was discarded by a simultaneous other fault")
        else:
            if not all(result["wave_aborted"] for result in results):
                raise AssertionError("infrastructure failure was accepted: " + name)
            if name not in ("wall", "flood") and any(result["gate_released"] for result in results):
                raise AssertionError("GO escaped a failed pregame wave: " + name)
        if name == "flood" and any(Path(result["stdout_path"]).stat().st_size > 4096 for result in results):
            raise AssertionError("stdio cap did not bound saved bytes")
    report["complete"] = True
    report["owned_live_jobs"] = 0
    save()
    return report


def identity_failure_check(out: Path) -> dict:
    out = _external_out(out)
    script = out / "toy.py"
    script.write_text(TOY)
    job = wave.WaveJob("missing-initial-identity", (sys.executable, str(script), "long", str(out / "attempt" / "events.jsonl")),
                       {}, {"attempt_id": "identity-fault-1"}, out / "attempt")
    original = wave._proc_identity
    calls = 0
    def missing_once(pid):
        nonlocal calls
        calls += 1
        return None if calls == 1 else original(pid)
    report = {"complete": False, "scope": "initial identity lookup fault; no engine acceptance", "cases": []}
    (out / "identity-fault.json").write_text(json.dumps(report, indent=2) + "\n")
    before_fds = len(list(Path("/proc/self/fd").iterdir()))
    with patch.object(wave, "_proc_identity", side_effect=missing_once):
        observed = wave.WaveExecutor().run_wave([job], 3)[0]
    report["cases"].append({"case": "missing_initial_identity", "observation": observed})
    (out / "identity-fault.json").write_text(json.dumps(report, indent=2) + "\n")
    if not observed["wave_aborted"] or observed["gate_released"] or not observed.get("initial_identity_failed"):
        raise AssertionError("failed identity admission was accepted")
    if not observed.get("identity_verified_during_cleanup") or observed["remaining_processes"] or not observed["readers_done"]:
        raise AssertionError("original child identity and stdio did not settle")
    if len(list(Path("/proc/self/fd").iterdir())) != before_fds:
        raise AssertionError("initial identity failure leaked controller descriptors")
    report.update(complete=True, owned_live_jobs=0)
    (out / "identity-fault.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def fastchess_checks(build: Path, out: Path) -> dict:
    fc = module("wave_actual_fastchess", HERE / "fastchess.py")
    fixture = module("wave_actual_fastchess_fixture", HERE / "test_fastchess.py")
    record = json.loads(build.read_text())
    binary = Path(record["binary"])
    if not record["complete"] or record["upstream_commit"] != fc.PIN or record["patch_sha256"] != fc.sha(fc.PATCH.read_bytes()) or record["binary_sha256"] != fc.sha(binary.read_bytes()):
        raise ValueError("exact reviewed runner build required")
    out = _external_out(out)
    mock_text = fixture.MOCK.replace("    if line == 'uci':\n", "    if line == 'uci':\n        if mode == 'startup_exit':\n            time.sleep(.4)\n            sys.exit(7)\n")
    mock_text = mock_text.replace("    elif line == 'isready':\n", "    elif line == 'isready':\n        if mode == 'delay': time.sleep(1.1)\n")
    mock = out / "mock.py"
    mock.write_text(mock_text)
    book = out / "book.pgn"
    book.write_text('[Event "Fixture only"]\n[Result "*"]\n\n1. f3 e5 *\n')
    report = {"complete": False, "scope": "actual patched Fastchess waves with protocol mocks only",
              "binary_sha256": record["binary_sha256"], "cases": []}
    for case in ("two_ready", "one_startup_failure"):
        base = out / case
        base.mkdir()
        jobs = []
        for index in range(2):
            directory = base / str(index)
            directory.mkdir()
            mode = "normal" if index == 0 else "delay" if case == "two_ready" else "startup_exit"
            white = fc.EngineCommand("mock-white", (sys.executable, str(mock), str(directory / "white.jsonl"), mode))
            black = fc.EngineCommand("mock-black", (sys.executable, str(mock), str(directory / "black.jsonl"), "normal"))
            argv = tuple(fc.single_game_argv(binary, white, black, opening_pgn=book, opening_start=1, out=directory))
            metadata = {"wave_id": case, "game_id": f"game-{index}", "attempt_id": f"{case}-{index}-1",
                        "slot_id": str(index), "opening_id": "fixture-foolsmate"}
            jobs.append(wave.WaveJob(metadata["attempt_id"], argv, {}, metadata, directory))
        events = []
        results = wave.WaveExecutor().run_wave(jobs, 15,
            on_event=lambda event, job, obs: events.append({"event": event, "identity": job.identity, "time": time.monotonic()}))
        if any(result["remaining_processes"] or not result["readers_done"] for result in results):
            raise AssertionError("actual wave did not physically settle")
        if case == "two_ready":
            if any(result["wave_aborted"] or result["returncode"] != 0 for result in results):
                raise AssertionError("actual ready wave failed: " + repr(results))
            if max(result["ready_monotonic"] for result in results) > min(result["released_monotonic"] for result in results):
                raise AssertionError("a real runner started before the delayed peer was ready")
            for job in jobs:
                pgn = (job.out / "game.pgn").read_text()
                if '[Result "0-1"]' not in pgn:
                    raise AssertionError("actual legal mate fixture failed")
        else:
            if not all(result["wave_aborted"] and not result["gate_released"] for result in results):
                raise AssertionError("startup failure released another game")
            if any((job.out / "game.pgn").exists() and (job.out / "game.pgn").read_text().strip() for job in jobs):
                raise AssertionError("failed pregame wave produced a scored game")
        report["cases"].append({"case": case, "observations": results, "events": events})
        (out / "actual-wave.json").write_text(json.dumps(report, indent=2) + "\n")
    report["complete"] = True
    report["owned_live_jobs"] = 0
    (out / "actual-wave.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    if "--toy-out" in sys.argv or "--build" in sys.argv or "--identity-out" in sys.argv:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--toy-out", type=Path)
        parser.add_argument("--identity-out", type=Path)
        parser.add_argument("--build", type=Path)
        parser.add_argument("--out", type=Path)
        args = parser.parse_args()
        if args.toy_out:
            result = toy_checks(args.toy_out)
        elif args.identity_out:
            result = identity_failure_check(args.identity_out)
        else:
            if not args.build or not args.out:
                parser.error("--build and --out are required for actual runner checks")
            result = fastchess_checks(args.build, args.out)
        print(json.dumps({"complete": result["complete"], "cases": len(result["cases"]), "owned_live_jobs": result["owned_live_jobs"]}))
    else:
        unittest.main()
