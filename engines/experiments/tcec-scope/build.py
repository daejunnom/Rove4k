#!/usr/bin/env python3
"""Fresh full-C TCEC profiles, with maintained producers as exact controls.

Default builds require an explicitly selected literal recipe. --runtime selects
a development comparison; measurements never rewrite a selected expectation.
All products and receipts go to a new external directory. F8 always regenerates
the ordinary F2 source before the existing guarded eight-worker producer.
"""
import argparse
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
EXECUTING_BUILD = Path(__file__).read_bytes().replace(b'\r\n', b'\n')
CLASS = 'tcec-full-C-v1'
CONTROL = {
    'A': (8335, '2d077291e5615790206a43399d809b23aca5a2deec17623cd4c32f40fcb1ebf4', 4232),
    'B': (9744, '4b3412e3dddbe4cc9b40172be66d577aa998dc65e4ffa5876827f6b92654c5a8', 4712),
    'C': (8970, '391944ca8e3fbe1c0064793232ad0664b8e282b812455c47d3047fcee9baec62', 4375),
    'E': (8526, 'c0b01df4c8a330fce2fdfe28a15feb885ce1155e3dddf59b739c0c39f5652b75', 4323),
    'F': (7712, '546df93f9d7f6e6f8b8bdf76b8e3d5e7f9c92913f33db7bd77deec8d50bef20e', 4018),
    'F8': (7868, 'fb18e915ca1236a25c9c2969c8c2b45d8000e2a701aede3490306b6246eb4865', 4028),
}
VERIFIER_INPUTS = {
    'engines/compact/tiny-entry-d/verify.py': '18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae',
    'engines/tests/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
}
LIMITS = {'aggregate_wall': 1800, 'per_command_wall': 420,
          'parent_AS': 4 << 30, 'parent_CPU': 300, 'parent_CPU_hard': 330,
          'nested_producer_AS': 4 << 30,
          'child_AS': 2 << 30, 'child_CPU': 300, 'tool_output_bytes': 16 << 20}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(data):
    return {'bytes': len(data), 'sha256': sha(data)}


def normalized(path):
    data = path.read_bytes().replace(b'\r\n', b'\n')
    require(b'\r' not in data, 'lone CR in text input: ' + str(path))
    return data


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def producer_closure(entry):
    """Read only named active dependencies, never historical output folders."""
    contents = {}

    def add(path, expected=None):
        path = path.resolve()
        name = path.relative_to(REPO).as_posix()
        require(path.name not in ('inventory.json', 'package-lock.json', 'id_rsa', 'id_ecdsa', 'id_ed25519')
                and not path.name.startswith('.env')
                and not any(part in ('node_modules', 'dist', 'dist-server', 'build', 'coverage',
                                     'models', 'checkpoints', '.cache') for part in path.relative_to(REPO).parts),
                'non-source input is outside the named producer closure: ' + name)
        data = normalized(path)
        require(expected is None or sha(data) == expected, 'active producer pin differs: ' + name)
        require(name not in contents or contents[name] == data, 'source changed during closure read: ' + name)
        contents[name] = data

    def ordinary(family):
        directory = REPO / ('engines/compact/tiny-entry-' + family.lower())
        recipe = json.loads(normalized(directory / 'recipe.json'))
        add(directory / 'build.py')
        add(directory / 'recipe.json')
        for name, expected in recipe['local_input_sha256'].items():
            add(directory / name, expected)
        for key in ('shared_source_sha256', 'helper_sha256', 'selected_verifier_snapshot_sha256', 'shell_verifier_snapshot_sha256'):
            for name, expected in recipe.get(key, {}).items():
                add(REPO / name, expected)
        for name, expected in recipe.get('shell_wrapper', {}).get('verifier_snapshot_sha256', {}).items():
            add(REPO / name, expected)

    if entry != 'F8':
        ordinary(entry)
    else:
        ordinary('F')
        directory = REPO / 'engines/compact/tiny-entry-f-resource8'
        recipe = json.loads(normalized(directory / 'recipe.json'))
        for key in ('base_source_closure_sha256', 'positive_helper_sha256'):
            for name, expected in recipe[key].items():
                add(REPO / name, expected)
        for name in ('build.py', 'recipe.json', 'specialize.py', 'quiet_source.py', 'README.md', 'verify.py'):
            add(directory / name)
    return contents


class Host:
    """Bounded development commands; retain original PID until group settles."""
    def __init__(self, out, report, save):
        self.out, self.report, self.save = out, report, save
        self.deadline = time.monotonic() + LIMITS['aggregate_wall']
        self.owned = {}
        self.handled = (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)
        self.old_handlers = {s: signal.signal(s, self.interrupt) for s in self.handled}
        resource.setrlimit(resource.RLIMIT_AS, (LIMITS['parent_AS'],) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (LIMITS['parent_CPU'], LIMITS['parent_CPU_hard']))
        signal.alarm(LIMITS['aggregate_wall'])

    @staticmethod
    def interrupt(sig, frame):
        raise TimeoutError('bounded builder signal ' + str(sig))

    @staticmethod
    def exited(child):
        return os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None

    @staticmethod
    def others(child):
        rows = []
        for path in Path('/proc').iterdir():
            if not path.name.isdecimal() or int(path.name) == child.pid:
                continue
            try:
                fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
                if int(fields[2]) == child.pid:
                    rows.append({'pid': int(path.name), 'state': fields[0]})
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                pass
        return rows

    def settle(self, child, row, force=False):
        if row.get('reaped'):
            return
        if force or not self.exited(child) or self.others(child):
            row['forced_cleanup'] = True
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(child.pid, sig)
                except ProcessLookupError:
                    pass
                # The old F8 producer owns separate compiler sessions. Allow
                # its bounded TERM/KILL settlement and receipt publication
                # before escalating against that owner itself.
                grace = row.get('cooperative_termination_seconds', 3) if sig == signal.SIGTERM else 3
                end = time.monotonic() + grace
                while time.monotonic() < end:
                    if self.exited(child) and not self.others(child):
                        break
                    time.sleep(.025)
                if self.exited(child) and not self.others(child):
                    break
        row['other_group_members_before_reap'] = self.others(child)
        require(self.exited(child) and not row['other_group_members_before_reap'],
                'owned command group did not settle while original leader identity retained')
        row['original_identity_retained_until_other_members_absent'] = True
        child.wait(timeout=3)
        row.update(returncode=child.returncode, terminal=True, reaped=True)
        # Observation only after reap; never signal a stale numeric PGID.
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            row['owned_group_absent'] = True
        else:
            row['owned_group_absent'] = False
        self.owned.pop(child)

    def run(self, command, *, cwd, kind, data=None, nested_receipt=None):
        row = {'kind': kind, 'command': [str(x) for x in command], 'cwd': str(cwd),
               'started': False, 'forced_cleanup': False}
        if nested_receipt is not None:
            row.update(nested_owner_receipt=str(nested_receipt), cooperative_termination_seconds=15)
        child_AS = LIMITS['nested_producer_AS'] if nested_receipt is not None else LIMITS['child_AS']
        row['child_limits'] = {'AS': child_AS, 'CPU': LIMITS['child_CPU']}
        self.report['commands'].append(row)
        self.save()
        stem = self.out / ('tool-' + str(len(self.report['commands'])) + '-' + kind)
        output_path, error_path = stem.with_suffix('.stdout'), stem.with_suffix('.stderr')
        input_path = stem.with_suffix('.stdin')
        if data is not None:
            input_path.write_bytes(data)
        child = None
        started = time.monotonic()
        with output_path.open('wb') as output, error_path.open('wb') as error, \
                (input_path.open('rb') if data is not None else open(os.devnull, 'rb')) as source:
            try:
                inherited = signal.pthread_sigmask(signal.SIG_BLOCK, set(self.handled))

                def setup():
                    resource.setrlimit(resource.RLIMIT_AS, (child_AS,) * 2)
                    resource.setrlimit(resource.RLIMIT_CPU, (LIMITS['child_CPU'],) * 2)
                    signal.pthread_sigmask(signal.SIG_SETMASK, inherited)

                try:
                    child = subprocess.Popen(row['command'], cwd=cwd, stdin=source,
                        stdout=output, stderr=error, start_new_session=True, preexec_fn=setup,
                        env={**os.environ, 'LC_ALL': 'C', 'TZ': 'UTC', 'PYTHONDONTWRITEBYTECODE': '1'})
                    self.owned[child] = row
                    row.update(started=True, pid=child.pid, pgid=child.pid)
                    self.save()
                finally:
                    signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
                while not self.exited(child):
                    if time.monotonic() - started > LIMITS['per_command_wall'] or time.monotonic() > self.deadline:
                        raise TimeoutError('tool wall limit: ' + kind)
                    require(output_path.stat().st_size + error_path.stat().st_size <= LIMITS['tool_output_bytes'],
                            'tool output cap: ' + kind)
                    time.sleep(.025)
            finally:
                if child is not None:
                    inherited = signal.pthread_sigmask(signal.SIG_BLOCK, set(self.handled))
                    try:
                        self.settle(child, row, force=not self.exited(child))
                    finally:
                        row['elapsed_diagnostic_seconds'] = time.monotonic() - started
                        row['stdout'] = {'path': str(output_path), **pin(output_path.read_bytes())}
                        row['stderr'] = {'path': str(error_path), **pin(error_path.read_bytes())}
                        if nested_receipt is not None:
                            try:
                                raw = nested_receipt.read_bytes()
                                nested = json.loads(raw)
                                keys = ('started', 'terminal', 'reaped', 'returncode', 'owned_group_absent',
                                        'group_absent_at_settlement', 'forced_cleanup', 'forced_group_cleanup',
                                        'other_group_members_before_reap',
                                        'original_identity_retained_until_other_members_absent')
                                row['nested_owner'] = {key: nested.get(key) for key in
                                    ('complete', 'source_reproduced', 'native_reproduced', 'whole_reproduced',
                                     'shell_header_reproduced', 'owned_active_tool', 'owned_tool_handles', 'first_failure')}
                                row['nested_owner'].update(receipt=pin(raw),
                                    commands=[{key: command.get(key) for key in keys}
                                              for command in nested.get('commands', [])])
                            except (FileNotFoundError, json.JSONDecodeError) as error:
                                row['nested_owner'] = {'receipt_unavailable': str(error)}
                        self.save()
                        signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
        require(row['returncode'] == 0 and row['owned_group_absent'] and not row['forced_cleanup'],
                'tool failed or needed forced cleanup; evidence preserved: ' + kind)
        if nested_receipt is not None:
            nested = row['nested_owner']
            require(all(nested.get(key) is True for key in
                        ('complete', 'source_reproduced', 'native_reproduced', 'whole_reproduced', 'shell_header_reproduced'))
                    and nested.get('owned_active_tool') is None and nested.get('owned_tool_handles') == 0
                    and not nested.get('first_failure') and nested.get('commands')
                    and all(command['started'] and command['terminal'] and command['reaped']
                            and command['returncode'] == 0 and command['owned_group_absent']
                            and command['group_absent_at_settlement'] and not command['forced_cleanup']
                            and not command['forced_group_cleanup']
                            and command['other_group_members_before_reap'] == []
                            and command['original_identity_retained_until_other_members_absent']
                            for command in nested['commands']),
                    'nested F8 owner receipt is incomplete or unsettled; evidence preserved')
        return output_path.read_bytes()

    def close(self):
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, set(self.handled))
        try:
            failures = []
            for child, row in list(self.owned.items()):
                try:
                    self.settle(child, row, force=True)
                except BaseException as error:
                    failures.append(str(error))
            self.report['host_cleanup'] = {'unsettled_commands': len(self.owned), 'errors': failures}
            self.save()
            require(not failures and not self.owned, 'owned commands remain unsettled')
        finally:
            signal.alarm(0)
            for sig, handler in self.old_handlers.items():
                signal.signal(sig, handler)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)


def runtime_policy(mode, variant, workers):
    per_go = mode == 'per-go'
    active = workers if per_go and variant == 'main' else workers + 1
    return {'mode': mode, 'variant': variant if per_go else None,
            'startup_threads': 1 if per_go else workers + 1, 'active_threads': active,
            'between_GO_threads': 1 if per_go else workers + 1,
            'input_during_GO': 'queued_until_join' if per_go and variant != 'async' else 'asynchronous',
            'terminal': 'maintained-shutdown' if mode == 'control' else 'process-exit',
            'worker_learning': 'persistent', 'full_promotions': 'NBRQ'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entry', choices=tuple(CONTROL), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--runtime', choices=('control', 'final', 'per-go'),
                        help='explicit development comparison, never updates selected pins')
    parser.add_argument('--variant', choices=('spawn', 'main', 'async'))
    parser.add_argument('--final', choices=('drain', 'immediate'))
    parser.add_argument('--input-profile', choices=('control', 'valid-tcec'))
    parser.add_argument('--operators', action='store_true',
                        help='explicit async atomic-expression comparison after valid-input specialization')
    parser.add_argument('--line-profile', choices=('control', 'size_t', 'word'),
                        help='explicit getline comparison after runtime/input/operator stages')
    parser.add_argument('--b-compact', action='store_true',
                        help='explicit full-B equivalent forms after word-alias getline')
    parser.add_argument('--b-fields', action='store_true',
                        help='explicit full-B field aliases after its admitted compact stage')
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and platform.machine() == 'x86_64', 'Linux x86-64 required')
    require(args.out.is_absolute() and not out.exists() and REPO not in (out, *out.parents)
            and not any((p / '.git').exists() for p in (out, *out.parents)),
            'a new absolute output outside any Git checkout is required')
    recipe_raw = normalized(HERE / 'recipe.json')
    recipe = json.loads(recipe_raw)
    require(recipe['format'] == 1 and recipe['class'] == CLASS, 'unknown TCEC recipe')
    selected = recipe['selected'].get(args.entry)
    experimental = args.runtime is not None
    require(experimental or selected is not None, 'no selected literal TCEC recipe for this entry; compare with explicit --runtime first')
    require(experimental or not any((args.variant, args.final, args.input_profile, args.operators,
                                    args.line_profile, args.b_compact, args.b_fields)),
            'policy overrides require explicit experimental --runtime')
    policy = ({'runtime': args.runtime, 'variant': args.variant or 'async',
               'final': args.final or 'drain', 'input_profile': args.input_profile or 'valid-tcec',
               'wrapper': 'pipe', 'operators': args.operators,
               'line_profile': args.line_profile or 'control',
               'b_compact': args.b_compact, 'b_fields': args.b_fields} if experimental else selected['policy'])
    require(policy['runtime'] != 'per-go' or args.entry in ('F', 'F8'), 'per-GO policy supports only full F2/F8')
    require(experimental or policy['runtime'] != 'per-go' or policy['variant'] == 'async',
            'selected TCEC profile must keep isready responsive during GO')
    require(args.variant is None or args.runtime == 'per-go', '--variant only applies to per-go')
    require(args.final is None or args.runtime == 'final', '--final only applies to final')
    require(not policy.get('operators', False) or
            (policy['runtime'] == 'per-go' and policy['variant'] == 'async'
             and policy['input_profile'] == 'valid-tcec'),
            'operator comparison requires the exact post-input async source')
    require(policy.get('line_profile', 'control') == 'control' or
            (policy['input_profile'] == 'valid-tcec' and
             ((policy['runtime'] == 'final' and policy['final'] == 'immediate') or
              (policy['runtime'] == 'per-go' and policy['variant'] == 'async'))),
            'getline comparison requires its exact admitted runtime/input stage')
    require(not policy.get('b_compact', False) or
            (args.entry == 'B' and policy['runtime'] == 'final' and policy['final'] == 'immediate'
             and policy['input_profile'] == 'valid-tcec' and policy.get('line_profile') == 'word'),
            'full-B compact comparison requires the exact post-word-line source')
    require(not policy.get('b_fields', False) or policy.get('b_compact', False),
            'full-B field aliases require the exact compact predecessor')
    family, workers = ('F' if args.entry == 'F8' else args.entry), (8 if args.entry == 'F8' else 2)
    report = {'format': 1, 'class': CLASS, 'complete': False, 'entry': args.entry, 'family': family,
              'resources': {'workers': workers, 'tt_bits': 18, 'ply': 128, 'max_position_plies': 4095},
              'policy': policy, 'runtime_policy': runtime_policy(policy['runtime'], policy['variant'], workers),
              'commands': [], 'attempts': [], 'limits': LIMITS,
              'qualification': {'selection': 'experimental-measurement' if experimental else 'selected-literal-recipe',
                                'runtime': False, 'rules_eligibility': 'unproven', 'game_strength': 'unproven'},
              'authority': 'fresh named project-source closure and maintained exact producer; no historical binary/source inputs'}
    out.mkdir()

    def save():
        (out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')

    host = Host(out, report, save)
    try:
        closure = producer_closure(args.entry)
        frozen = out / 'producer-repo'
        for name, data in closure.items():
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        report['control_source_closure'] = {name: pin(data) for name, data in sorted(closure.items())}
        own_names = ['build.py', 'verify.py', 'recipe.json', 'c_input.py']
        if policy['runtime'] != 'control':
            own_names.append('c_per_go.py' if policy['runtime'] == 'per-go' else 'c_final.py')
        if policy.get('operators', False):
            own_names.append('c_per_go_operators.py')
        if policy.get('line_profile', 'control') != 'control':
            own_names.append('c_line.py')
        if policy.get('b_compact', False):
            own_names.append('b_compact.py')
        if policy.get('b_fields', False):
            own_names.append('b_fields.py')
        own_inputs = {str((HERE / name).relative_to(REPO).as_posix()): normalized(HERE / name) for name in own_names}
        require(own_inputs[HERE.relative_to(REPO).as_posix() + '/build.py'] == EXECUTING_BUILD,
                'executing builder changed before input freeze')
        require(own_inputs[HERE.relative_to(REPO).as_posix() + '/recipe.json'] == recipe_raw,
                'TCEC selection recipe changed during input freeze')
        own_inputs['engines/scripts/source_package.py'] = normalized(REPO / 'engines/scripts/source_package.py')
        for name, expected in VERIFIER_INPUTS.items():
            data = normalized(REPO / name)
            require(sha(data) == expected, 'verifier helper pin differs: ' + name)
            own_inputs[name] = data
        inputs = out / 'inputs'
        for name, data in own_inputs.items():
            target = inputs / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        report['inputs'] = {name: pin(data) for name, data in sorted(own_inputs.items())}
        if not experimental:
            actual_producers = {name: row['sha256'] for name, row in report['inputs'].items() if not name.endswith('/recipe.json')}
            common_producers = recipe['common_producer_sha256']
            require(not (common_producers.keys() & selected['producer_sha256'].keys()),
                    'selected producer cannot replace a shared literal source pin')
            require(actual_producers == {**common_producers, **selected['producer_sha256']},
                    'selected TCEC producer source closure differs')
        verifier_name = 'engines/experiments/tcec-scope/verify.py'
        report['selected_verifier'] = {'path': verifier_name, 'inputs': report['inputs'],
            'command': [sys.executable, '-I', '-B', str(inputs / verifier_name), '--build', str(out), '--out', '<new external output>']}
        save()
        if args.entry == 'F8':
            host.run([sys.executable, '-I', '-B', frozen / 'engines/compact/tiny-entry-f/build.py',
                      '--wrapper', 'shell', '--out', out / 'control-f2'], cwd=out, kind='control-F2')
            control_dir = frozen / 'engines/compact/tiny-entry-f-resource8'
            host.run([sys.executable, '-I', '-B', control_dir / 'build.py', '--base-source',
                      out / 'control-f2/main.c', '--wrapper', 'shell', '--out', out / 'control'],
                     cwd=out, kind='control-F8', nested_receipt=out / 'control/build.json')
            control = out / 'control/first'
        else:
            control_dir = frozen / ('engines/compact/tiny-entry-' + args.entry.lower())
            host.run([sys.executable, '-I', '-B', control_dir / 'build.py', '--wrapper', 'shell',
                      '--out', out / 'control'], cwd=out, kind='control-' + args.entry)
            control = out / 'control'
        base = (control / 'main.c').read_bytes()
        require((len(base), sha(base), (control / 'x').stat().st_size) == CONTROL[args.entry],
                'regenerated maintained full control identity differs')
        report['control'] = {'source': pin(base), 'native': pin((control / 'native/x').read_bytes()),
                             'whole': pin((control / 'x').read_bytes()), 'path': str(control)}
        control_recipe = json.loads(normalized(control_dir / 'recipe.json'))
        compression, compiler = control_recipe['compression'], control_recipe['compiler']
        own = inputs / HERE.relative_to(REPO)
        input_helper = load_module('tcec_input_frozen', own / 'c_input.py')
        input_family = 'F8' if workers == 8 else ('F2' if family == 'F' else family)
        compiler, compiler_proof = input_helper.compiler_for(base, family=input_family, original=compiler)
        compiler = list(compiler)
        report['compiler_proof'] = compiler_proof
        packaging = load_module('tcec_package_frozen', inputs / 'engines/scripts/source_package.py')
        header = packaging.tcec_header(compiler=compiler, mode=policy['wrapper'])
        report['wrapper_contract'] = packaging.tcec_contract(compiler=compiler, mode=policy['wrapper'])
        report.update(compiler=compiler, compression=compression)
        stage_helper = None
        if policy['runtime'] != 'control':
            stage_helper = load_module('tcec_runtime_frozen', own /
                ('c_per_go.py' if policy['runtime'] == 'per-go' else 'c_final.py'))
        operators = (load_module('tcec_operators_frozen', own / 'c_per_go_operators.py')
                     if policy.get('operators', False) else None)
        line_helper = (load_module('tcec_line_frozen', own / 'c_line.py')
                       if policy.get('line_profile', 'control') != 'control' else None)
        b_compact = (load_module('tcec_b_compact_frozen', own / 'b_compact.py')
                     if policy.get('b_compact', False) else None)
        b_fields = (load_module('tcec_b_fields_frozen', own / 'b_fields.py')
                    if policy.get('b_fields', False) else None)

        def transform():
            source, proofs = base, []
            if stage_helper is not None:
                if policy['runtime'] == 'per-go':
                    candidate, proof = stage_helper.transform_source(source,
                        family='F8' if workers == 8 else 'F2', variant=policy['variant'])
                else:
                    candidate, proof = stage_helper.transform_source(source, family=family,
                        workers=workers, final=policy['final'])
                require(stage_helper.restore_source(candidate, proof) == source, 'full runtime inverse differs')
                proofs.append({'stage': policy['runtime'], 'proof': proof, 'full_inverse': True})
                source = candidate
            if policy['input_profile'] != 'control':
                candidate, proof = input_helper.transform_source(source, family=input_family, mode=policy['input_profile'])
                require(input_helper.restore_source(candidate, proof) == source, 'full valid-input inverse differs')
                proofs.append({'stage': 'valid-tcec-input', 'proof': proof, 'full_inverse': True})
                source = candidate
            if operators is not None:
                candidate, proof = operators.transform_source(source, family=input_family)
                require(operators.restore_source(candidate, proof) == source, 'full atomic-expression inverse differs')
                proofs.append({'stage': 'async-atomic-expressions', 'proof': proof, 'full_inverse': True})
                source = candidate
            if line_helper is not None:
                candidate, proof = line_helper.transform_source(source, family=input_family,
                    variant=policy['line_profile'])
                require(line_helper.restore_source(candidate, proof) == source, 'full getline inverse differs')
                proofs.append({'stage': 'getline', 'proof': proof, 'full_inverse': True})
                source = candidate
            if b_compact is not None:
                forms = ('score', 'see', 'constants', 'promotion', 'bitindex', 'hash', 'return', 'static')
                candidate, proof = b_compact.transform_source(source, forms=forms)
                require(b_compact.restore_source(candidate, proof) == source, 'full-B compact inverse differs')
                proofs.append({'stage': 'full-B-equivalent-forms', 'proof': proof, 'full_inverse': True})
                source = candidate
            if b_fields is not None:
                candidate, proof = b_fields.transform_source(source)
                require(b_fields.restore_source(candidate, proof) == source, 'full-B field inverse differs')
                proofs.append({'stage': 'full-B-field-aliases', 'proof': proof, 'full_inverse': True})
                source = candidate
            checked_compiler, new_compiler_proof = input_helper.compiler_for(source, family=input_family, original=compiler)
            require(list(checked_compiler) == compiler, 'source transform changed compiler selection')
            proofs.append({'stage': 'compiler', 'proof': new_compiler_proof,
                           'full_inverse': True, 'source_changed': False})
            return source, proofs

        type_gate_native = None
        for name in ('first', 'repeat'):
            directory = out / name
            directory.mkdir()
            source, proofs = transform()
            (directory / 'main.c').write_bytes(source)
            if name == 'first':
                assertions = [row['proof'].get('required_target_type_assertion') for row in proofs]
                assertions = [assertion for assertion in assertions if assertion is not None]
                if assertions:
                    gate = out / 'target-type-gate'
                    gate.mkdir()
                    gate_source = source + b'\n' + ('\n'.join(assertions) + '\n').encode('ascii')
                    (gate / 'main.c').write_bytes(gate_source)
                    host.run(compiler, cwd=gate, kind='target-type-gate', data=gate_source)
                    type_gate_native = (gate / 'x').read_bytes()
                    report['target_type_gate'] = {'shipping_source': pin(source), 'assertions': assertions,
                                                  'gate_source': pin(gate_source), 'native': pin(type_gate_native)}
            native_dir = directory / 'native'
            native_dir.mkdir()
            host.run(compiler, cwd=native_dir, kind=name + '-compile', data=source)
            native = (native_dir / 'x').read_bytes()
            require(type_gate_native is None or type_gate_native == native,
                    'target type gate changed the compiled shipping image')
            if type_gate_native is not None:
                report['target_type_gate']['native_identical_to_raw_shipping_compile'] = True
            whole = packaging.package_tcec(source, compression, compiler=compiler, mode=policy['wrapper'])
            require(whole.startswith(header), 'TCEC wrapper header differs')
            payload = whole[len(header):]
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            restored = decoder.decompress(payload, max_length=len(source) + 1)
            require(restored == source and decoder.eof and not decoder.unused_data, 'strict source payload restoration differs')
            (directory / 'header.sh').write_bytes(header)
            (directory / 'payload.lzma').write_bytes(payload)
            (directory / 'x').write_bytes(whole)
            (directory / 'x').chmod(0o700)
            (directory / 'source-proof.json').write_text(json.dumps(proofs, indent=2) + '\n')
            expected = {prefix + '_' + key: value for prefix, data in
                (('source', source), ('native', native), ('whole', whole), ('header', header), ('payload', payload))
                for key, value in pin(data).items()}
            report['attempts'].append({'directory': name, **expected, 'source_proofs': proofs})
            save()
        first, repeat = report['attempts']
        require({k: v for k, v in first.items() if k != 'directory'} ==
                {k: v for k, v in repeat.items() if k != 'directory'}, 'independent transformation/compile/package reproduction differs')
        actual = {key: value for key, value in first.items() if key not in ('directory', 'source_proofs')}
        if not experimental:
            require(actual == selected['expected'], 'selected literal source/native/whole/header/payload identity differs')
        report['expected_contract'] = selected['expected'] if not experimental else actual
        report['source_proofs'] = first['source_proofs']
        report['actual'] = {'source': 'main.c', 'native': 'native/x', 'program': 'x'}
        for name in ('main.c', 'native/x', 'x', 'header.sh', 'payload.lzma', 'source-proof.json'):
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(out / 'first' / name, target)
        (out / 'x').chmod(0o700)
        (out / 'native/x').chmod(0o700)
        report.update(complete=True, reproducible=True,
                      whole_delta_vs_control=actual['whole_bytes'] - report['control']['whole']['bytes'])
        save()
    except BaseException as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        save()
        raise
    finally:
        host.close()
    print(json.dumps({'complete': True, 'entry': args.entry, 'selection': report['qualification']['selection'],
                      **report['expected_contract'], 'runtime_qualified': False, 'build': str(out)}, indent=2))


if __name__ == '__main__':
    main()
