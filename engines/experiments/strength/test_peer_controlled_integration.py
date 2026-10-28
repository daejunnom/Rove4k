#!/usr/bin/env python3
"""Small-process exercise of the controlled peer lifecycle, not engine qualification."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('integration_peer_runtime', HERE / 'peer_runtime.py')
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)


class FakeReader:
    def until(self, predicate, budget, seconds=None):
        assert predicate(self.bytes())
    def bytes(self):
        return b'uciok\nreadyok\n'


class FakeOwned:
    """A real tiny child; protocol, resource and cgroup observations are fixtures."""
    instances = []
    fail_cleanup = False
    def __init__(self):
        self.process = subprocess.Popen([sys.executable, '-u', '-c',
            "import sys\nfor line in sys.stdin:\n if line.strip()=='quit': break\n"],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.stdout = FakeReader()
        self.budget = SimpleNamespace(left=lambda maximum: maximum)
        self.instances.append(self)
    def send(self, value):
        self.process.stdin.write(value)
        self.process.stdin.flush()
    def wait_line(self, value):
        assert value == b'readyok'
    def group_others(self):
        return []
    def close_input(self):
        self.process.stdin.close()
    def cleanup(self):
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait(timeout=5)
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        return {'owned_group_absent': not self.fail_cleanup, 'readers_joined': True, 'errors': []}


class FakeArtifact:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def verify_bytes(self):
        pass
    def identity(self):
        return {k: v for k, v in self.__dict__.items() if k != 'path'}


def write_json(path, value):
    data = json.dumps(value, sort_keys=True).encode()
    Path(path).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(sys.platform == 'linux', 'Linux /proc fixture')
class ControlledLifecycleIntegrationTests(unittest.TestCase):
    def setUp(self):
        FakeOwned.instances = []
        FakeOwned.fail_cleanup = False
        self.temp = tempfile.TemporaryDirectory(prefix='peer-controlled-integration-')
        self.root = Path(self.temp.name).resolve()
        self.ref_path = self.root / 'reference.json'
        self.ref_sha = 'c' * 64
        self.slot = {'id': 'slot-000', 'cpus': list(range(16)), 'memory_nodes': [0],
                     'workers': 16, 'smt': True, 'policy': 'default'}
        resources = {'id': 'test-p16', 'workers': 16, 'tt_bytes': 16 << 30, 'entry_bytes': 8}
        native = {'path': str(self.root / 'reference-1'), 'sha256': 'b' * 64}
        self.reference = {'format':'rove4k-peer-reference-v1', 'complete':True, 'engines_executed':0,
            'resources':resources, 'source_inputs':{}, 'build':{'path':str(self.root/'manifest.json'),'sha256':'d'*64},
            'peer':'ice4', 'native':native, 'entry_size_compile_assertion':True,
            'native_attempts':[{'path':str(self.root/('reference-'+str(i)))} for i in (1,2,3)],
            'dependencies':{'needed':[]}, 'tt_symbol':'tt', 'tt_symbol_value':1,
            'source':{}, 'compiler':'fixture'}
        self.admitted = {'peer':'ice4', 'layout':resources, 'record':{'whole':{'path':str(self.root/'whole'),
                          'sha256':'a'*64, 'bytes':1}}, 'whole':b'x', 'source':b's', 'tt_symbol':'tt'}
        self.context = object.__new__(runtime._ControlledPeer)
        self.context.token = runtime._CONTROLLED_PEER_TOKEN
        self.context.reference_sha, self.context.candidate_sha256 = self.ref_sha, 'e'*64
        self.context.artifact = SimpleNamespace(family='ice4', profile='test-p16', tt_bytes=16 << 30,
                                                sha256='a'*64, native_sha256='b'*64)
        self.context.slot = self.slot
        self.context.cgroup = {'path':'/sys/fs/cgroup/fake/slot-000'}
        self.context.launch_record = {'cgroup':self.context.cgroup, 'saved_cpus':list(range(16)),
                                      'saved_nodes':[0], 'whole_sha256':'a'*64}
        self.preexec = {'effective_cpus':list(range(16)), 'requested_policy':'default', 'requested_nodes':[0],
                        'runtime_limits':{'address_space':[100,100],'cpu':[200,201]},
                        'fallback':None, 'observed_policy':{'available':True,'mode':0}}
        self.events = []
        self.scope = SimpleNamespace(promotion_fixtures=lambda oracle: [],
            task_snapshot=lambda pid:{pid:{'cpu_ticks':1}})
        topology = SimpleNamespace(cpus=[SimpleNamespace(physical=i//2) for i in range(16)],
                                   to_record=lambda:{'cpus':[]})
        self.registry = SimpleNamespace(Artifact=FakeArtifact, CHECKS=('reproduction','size','startup','dependencies',
            'cleanup','protocol','legal_moves','resources','lifecycle','placement'),
            smt_runtime_evidence=lambda report, artifact:{'host_runtime_evidence_complete':False},
            admit_to_test_league=lambda *args: self.fail('diagnostic cannot enter registry'))
        self.peers = SimpleNamespace(external_new=lambda out:Path(out), write_json=write_json)
        self.topology_module = SimpleNamespace(Topology=SimpleNamespace(snapshot=lambda:topology))
        self.helper = SimpleNamespace(Budget=lambda seconds:SimpleNamespace(left=lambda maximum:maximum), OWNED=[])
        self.patches = [
            patch.object(runtime, 'sibling', side_effect=self.sibling),
            patch.object(runtime, 'read_record', side_effect=self.read_record),
            patch.object(runtime, '_verify_frozen'), patch.object(runtime, 'validate_build', return_value=self.admitted),
            patch.object(runtime, 'bound', side_effect=lambda path, pin:b's' if str(path).endswith('main.cpp') else b'n'),
            patch.object(runtime, 'Elf64', return_value=SimpleNamespace(dependencies=lambda:{'needed':[]},pointer_symbol=lambda n:1)),
            patch.object(runtime, 'validate_slot', return_value={'physical_cores':8,'logical_cpus':16,'qualified':False}),
            patch.object(runtime, 'observed_peer_runtime_budget', return_value={'address_space_bytes':100,'cpu_seconds':[200,201]}),
            patch.object(runtime, '_freeze', return_value={}), patch.object(runtime, '_check_controlled_sources'),
            patch.object(runtime, 'load', side_effect=self.load),
            patch.object(runtime, '_controlled_peer_preflight', side_effect=lambda *args:self.events.append('preflight') or {}),
            patch.object(runtime, '_controlled_peer_events', side_effect=self.oom_events),
            patch.object(runtime, '_controlled_peer_quiescent', side_effect=lambda *args:self.events.append('quiescent')),
            patch.object(runtime, '_write_launcher'), patch.object(runtime, 'construct_owned', side_effect=self.launch),
            patch.object(runtime, 'process_identity', side_effect=lambda pid:{'pid':pid,'pgid':pid,'session':pid,'start_ticks':1}),
            patch.object(runtime, '_observe_image', return_value={'path_exists':False,'tt':{'pointer':1}}),
            patch.object(runtime.os, 'sched_getaffinity', return_value=set(range(16))),
            patch.object(runtime, '_dependencies_live', return_value=[]),
            patch.object(runtime, '_search', return_value={'positive_cpu_worker_ids':list(range(16))}),
            patch.object(runtime, '_tt_numa_after_search', return_value={}),
            patch.object(runtime, '_finish_peer', side_effect=self.finish),
            patch.object(runtime, '_replay', return_value=None), patch.object(runtime.time, 'sleep'),
        ]
        for item in self.patches:
            item.start()
        self.oom_after = None
        self.event_reads = 0
        self.fail_session = None

    def tearDown(self):
        for owned in FakeOwned.instances:
            owned.cleanup()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def sibling(self, name, *args):
        return {'peers':self.peers, 'topology':self.topology_module, 'registry':self.registry}[name]
    def load(self, name, path):
        return {'peer_owned_helper':self.helper, 'peer_scope_helper':self.scope, 'peer_independent_oracle':object()}[name]
    def read_record(self, path, expected=None):
        return (self.reference, self.ref_sha) if Path(path) == self.ref_path else (self.preexec, 'f'*64)
    def launch(self, *args):
        self.events.append('launch')
        return FakeOwned()
    def finish(self, owned):
        if owned.process.stdin and not owned.process.stdin.closed:
            owned.process.stdin.close()
        owned.process.wait(timeout=5)
        return {'leader_exited_with_other_members':True}
    def oom_events(self, context):
        self.event_reads += 1
        changed = self.oom_after is not None and self.event_reads >= self.oom_after
        return {'oom':int(changed), 'oom_kill':int(changed)}
    def run_qualification(self, name='result'):
        return runtime.qualify_peer(self.ref_path, self.root/name, self.slot, reference_sha=self.ref_sha,
                                    allow_functional=True, _controlled=self.context)

    def test_four_lifecycles_use_owned_path_without_score_admission(self):
        result = self.run_qualification()
        self.assertEqual([s['label'] for s in result['record']['sessions']],
                         ['cold','warm','active-quit','active-eof'])
        self.assertEqual(self.events, ['preflight','launch','quiescent'] * 4)
        self.assertEqual(len(FakeOwned.instances), 4)
        self.assertFalse(result['qualified'])
        self.assertIsNone(result['admission'])
        self.assertFalse(result['record']['controlled_diagnostic']['authorizes_go'])
        self.assertTrue(all(x.process.poll() is not None for x in FakeOwned.instances))

    def test_oom_stops_next_session_and_retains_incomplete_result(self):
        self.oom_after = 2
        with self.assertRaisesRegex(ValueError, 'OOM event'):
            self.run_qualification('oom-result')
        self.assertEqual(len(FakeOwned.instances), 1)
        report = json.loads((self.root/'oom-result'/'qualification.json').read_text())
        self.assertFalse(report['complete'])
        self.assertIn('OOM event', report['failures'][0]['message'])
        self.assertIsNotNone(FakeOwned.instances[0].process.poll())

    def test_cleanup_failure_stops_next_session(self):
        FakeOwned.fail_cleanup = True
        with self.assertRaisesRegex(ValueError, 'cleanup did not physically settle'):
            self.run_qualification('cleanup-result')
        self.assertEqual(len(FakeOwned.instances), 1)
        report = json.loads((self.root/'cleanup-result'/'qualification.json').read_text())
        self.assertFalse(report['complete'])
        self.assertIsNotNone(FakeOwned.instances[0].process.poll())

    def test_source_change_after_first_session_stops_next_session(self):
        with patch.object(runtime, '_check_controlled_sources',
                          side_effect=[None, None, ValueError('source closure changed')]):
            with self.assertRaisesRegex(ValueError, 'source closure changed'):
                self.run_qualification('changed-source')
        self.assertEqual(len(FakeOwned.instances), 1)
        report = json.loads((self.root/'changed-source'/'qualification.json').read_text())
        self.assertFalse(report['complete'])
        self.assertIn('source closure changed', report['failures'][0]['message'])
        self.assertIsNotNone(FakeOwned.instances[0].process.poll())

if __name__ == '__main__':
    unittest.main()
