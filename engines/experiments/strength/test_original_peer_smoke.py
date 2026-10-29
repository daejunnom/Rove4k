"""Small synthetic owned-process tests; never download or run peer sources."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import original_peer_smoke_ci as smoke
import peer_exact_runner as runner


class ReceiptIdentity(unittest.TestCase):
    def test_ci_identity_checks_exact_event_checkout(self):
        env = {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'owner/repo',
               'GITHUB_EVENT_NAME': 'pull_request', 'CHECKOUT_SHA': 'a' * 40,
               'GITHUB_SHA': 'a' * 40, 'PR_HEAD_SHA': 'b' * 40,
               'GITHUB_WORKFLOW_REF': 'owner/repo/.github/workflows/original-peer-uci-smoke.yml@refs/pull/1/merge',
               'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1'}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(smoke.ci_identity()['checkout_sha'], 'a' * 40)
            os.environ['CHECKOUT_SHA'] = 'c' * 40
            with self.assertRaises(ValueError):
                smoke.ci_identity()


TOY = '''#!/usr/bin/python3
import sys,time
for line in sys.stdin:
    command=line.strip()
    if command == "uci":
        print("id name ice4 v6.1")
        print("option name Hash type spin default 8 min 1 max 67108864")
        print("option name Threads type spin default 1 min 1 max 2048")
        print("uciok", flush=True)
    elif command == "isready": print("readyok", flush=True)
    elif command.startswith("go "):
        {action}
    elif command == "quit": break
'''


@unittest.skipUnless(sys.platform == 'linux', 'owned-process runner requires Linux')
class SmallSmoke(unittest.TestCase):
    def execute(self, action, timeout=10):
        with tempfile.TemporaryDirectory(prefix='rove4k-uci-smoke-') as root:
            out = Path(root) / 'owned'
            out.mkdir(mode=0o700)
            (out / 'home').mkdir(mode=0o700)
            native = (TOY.format(action=action)).encode()
            (out / 'peer-native-1').write_bytes(native)
            summary = {'bytes': len(native), 'sha256': hashlib.sha256(native).hexdigest()}
            return smoke.run_smoke('ice4', out, summary, min(os.sched_getaffinity(0)), timeout=timeout)

    def test_legal_move_and_clean_quit(self):
        result = self.execute('print("bestmove e2e4", flush=True)')
        self.assertEqual(result['legal_startpos_bestmove'], 'e2e4')
        self.assertEqual(result['hash_mib_requested'], 1)
        self.assertEqual(result['threads_requested'], 1)

    def test_illegal_move_rejected(self):
        with self.assertRaises(runner.BuildCommandFailure):
            self.execute('print("bestmove e2e5", flush=True)')

    def test_duplicate_bestmove_rejected(self):
        with self.assertRaises(runner.BuildCommandFailure):
            self.execute('print("bestmove e2e4\\nbestmove d2d4", flush=True)')

    def test_timeout_cleans_owned_group(self):
        with self.assertRaises(runner.BuildCommandFailure):
            self.execute('time.sleep(20)', timeout=2)
        self.assertFalse(runner._UNSETTLED)


if __name__ == '__main__':
    unittest.main()
