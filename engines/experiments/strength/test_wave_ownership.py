"""Focused synthetic checks for conservative process-group observations."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from . import wave
except ImportError:
    import wave


class OwnershipObservationTests(unittest.TestCase):
    def child(self):
        return SimpleNamespace(process=SimpleNamespace(pid=100), observation={
            "start_ticks": 12, "pgid": 100, "session": 100,
        })

    def test_visible_zombie_and_unreadable_pid_preserve_unknown_group(self):
        child = self.child()
        zombie = {"pid": 100, "state": "Z", "pgid": 100, "session": 100, "start_ticks": 12}

        def identity(pid):
            if pid == 200:
                raise PermissionError("stat unavailable")
            return zombie

        with patch.object(wave.Path, "iterdir", return_value=[Path("/proc/100"), Path("/proc/200")]), \
                patch.object(wave, "_proc_identity", side_effect=identity), \
                patch.object(wave.os, "killpg") as killpg:
            members = wave._owned_members(child)
            self.assertEqual([member["state"] for member in members], ["Z", "group_members_unobservable"])
            self.assertTrue(child.observation["ownership_unreadable"])
            self.assertFalse(wave._signal(child, 15))
            killpg.assert_not_called()
            self.assertEqual([member["state"] for member in wave._live_owned_members(child)],
                             ["group_members_unobservable"])

    def test_live_filter_excludes_only_zombies_and_keeps_unknown(self):
        child = self.child()
        members = [{"pid": 1, "state": "Z"}, {"pid": 2, "state": "R"},
                   {"pid": None, "state": "group_members_unobservable"},
                   {"pid": None, "state": "group_exists_unobserved"},
                   {"pid": 3, "state": "unreadable"}]
        with patch.object(wave, "_owned_members", return_value=members):
            self.assertEqual(wave._live_owned_members(child), members[1:])

    def test_observed_zombie_alone_is_not_live(self):
        child = self.child()
        zombie = {"pid": 100, "state": "Z", "pgid": 100, "session": 100, "start_ticks": 12}
        with patch.object(wave.Path, "iterdir", return_value=[Path("/proc/100")]), \
                patch.object(wave, "_proc_identity", return_value=zombie):
            self.assertEqual(wave._owned_members(child), [zombie])
            self.assertEqual(wave._live_owned_members(child), [])
            self.assertNotIn("ownership_unreadable", child.observation)

    def test_unreadable_unrelated_pid_blocks_until_observation_recovers(self):
        child = self.child()
        zombie = {"pid": 100, "state": "Z", "pgid": 100, "session": 100, "start_ticks": 12}
        unrelated = {"pid": 200, "state": "R", "pgid": 200, "session": 200, "start_ticks": 20}
        readable = False

        def identity(pid):
            if pid == 200:
                if not readable:
                    raise PermissionError("unrelated process unavailable")
                return unrelated
            return zombie

        with patch.object(wave.Path, "iterdir", return_value=[Path("/proc/100"), Path("/proc/200")]), \
                patch.object(wave, "_proc_identity", side_effect=identity):
            self.assertEqual([member["state"] for member in wave._live_owned_members(child)],
                             ["group_members_unobservable"])
            readable = True
            self.assertEqual(wave._live_owned_members(child), [])
            # Historic uncertainty remains visible and prevents later signals.
            self.assertTrue(child.observation["ownership_unreadable"])
            self.assertFalse(wave._signal(child, 15))


if __name__ == "__main__":
    unittest.main()
