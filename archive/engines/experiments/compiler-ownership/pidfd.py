"""Separate Linux pidfd/poll experiment for the closed private C owner.

The normal compiler wait remains blocking WNOWAIT.  A pidfd changes only the
leader waits inside cleanup; the existing procfs group drain remains.  Setup
failure never enables execution without pidfd: the old monitor is retained only
to settle the already owned compiler before the original failure propagates.
Poll failure is likewise remembered, settled through the old monitor and raised
before native execution.  This producer does not select a shipping policy.
"""
import ast
import hashlib


def _pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _private_helpers(owner):
    return (owner._GROUP_SHARED.replace('return False', 'return 0')
            .replace('return True', 'return 1').replace('n.isdecimal()', 'n.isdigit()')
            .replace('kill(', 'k(').replace('def wait(', 'def w(').replace('live(', 'l('))


def _private_cleanup(owner):
    initial, cleanup, directory = owner.render_cleanup(state=True, shared=True)
    return initial, (cleanup.replace('if p is not None:', 'if p:')
                     .replace('kill(', 'k(').replace('not wait(', 'not w(')), \
        directory.replace('if d is not None:', 'if d:')


def _admit(script, owner):
    _require(type(script) is bytes and b'\r' not in script, 'LF owner bytes required')
    initial, cleanup, directory = _private_cleanup(owner)
    private = _private_helpers(owner)
    text = script.decode('utf-8')
    _, ordinary_cleanup, ordinary_directory = owner.render_cleanup(state=True, shared=True)
    for before, after in ((private, owner._GROUP_SHARED),
                          (cleanup, ordinary_cleanup), (directory, ordinary_directory)):
        _require(text.count(before) == 1, 'closed private owner region differs')
        text = text.replace(before, after, 1)
    unprivate = text.encode('utf-8')
    parts = owner._admit_prepared(unprivate, cleanup={'state': True})
    replay, _ = owner.compact_private_owner(unprivate)
    _require(replay == script, 'complete private owner replay differs')
    before = []
    for role, value in owner._prepared_parts(parts, state=True):
        before.append((role, private if role == 'helpers' else cleanup if role == 'cleanup'
                       else directory if role == 'directory_cleanup' else value))
    _require(owner._joined(before) == script, 'complete private owner reconstruction differs')
    return parts, before


def restore_bootstrap(candidate, proof):
    _require(type(candidate) is bytes and proof.get('kind') == 'pidfd-event-poll'
             and _pin(candidate) == proof.get('output'), 'pidfd output pin differs')
    result = candidate
    for span in reversed(proof['spans']):
        at, old, new = span['new_start'], span['old'].encode(), span['new'].encode()
        _require(result[at:at + len(new)] == new, 'pidfd inverse region differs')
        result = result[:at] + old + result[at + len(new):]
    _require(_pin(result) == proof.get('input'), 'pidfd inverse input differs')
    return result


def transform_bootstrap(script, *, owner, style='poll'):
    """Emit an experimental policy; ``owner`` is the frozen common producer.

    poll / nonzero / check-first are finite spellings of one event-wait policy.
    None is a hidden runtime fallback or a supported public build option.
    """
    _require(style in ('poll', 'nonzero', 'check-first'), 'unknown pidfd spelling')
    parts, before = _admit(script, owner)
    old_wait = ("def w(n,g=0):\n t=time.monotonic()+n\n"
                " while l() if g else os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None:\n"
                "  if time.monotonic()>t:return 0\n  if g:k(9)\n  time.sleep(.01)\n return 1\n")
    condition = 'not g and j'
    if style == 'nonzero':
        condition += ' and n'
    elif style == 'check-first':
        condition += ' and os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None'
    new_wait = old_wait.replace(' t=time.monotonic()+n\n',
        ' global j,v\n t=time.monotonic()+n\n if ' + condition + ':\n'
        '  try:j.poll(n*1000)\n  except BaseException as e:j=None;v=e\n', 1)
    after = []
    for role, value in before:
        if role == 'imports':
            value = value.rstrip('\n') + ',select\n'
        elif role == 'initial':
            _require(value == 'p=None;q=15;d=None\n', 'private initial state differs')
            value = 'p=None;q=15;d=z=j=v=None\n'
        elif role == 'helpers':
            _require(value.count(old_wait) == 1, 'private shared wait differs')
            value = value.replace(old_wait, new_wait, 1)
        elif role == 'call':
            value += ';z=os.pidfd_open(p.pid);e=select.poll();e.register(z,1);j=e'
        elif role == 'status_fd':
            value = ' if v is not None:raise v\n' + value
        elif role == 'directory_cleanup':
            _require(value == 'finally:\n if d:shutil.rmtree(d)\n', 'private directory owner differs')
            value = 'finally:\n if z is not None:os.close(z)\n if d:shutil.rmtree(d)\n'
        after.append((role, value))
    data = owner._joined(after)
    spans, gaps = [], []
    a = b = left = right = 0
    for (role, x), (_, y) in zip(before, after):
        x, y = x.encode(), y.encode()
        if x != y:
            gap = script[left:a]
            _require(gap == data[right:b], 'protected pidfd gap differs')
            gaps.append({'old_start': left, 'new_start': right, **_pin(gap)})
            spans.append({'role': role, 'old_start': a, 'new_start': b,
                          'old': x.decode(), 'new': y.decode()})
            left, right = a + len(x), b + len(y)
        a += len(x)
        b += len(y)
    _require(script[left:] == data[right:], 'protected pidfd suffix differs')
    gaps.append({'old_start': left, 'new_start': right, **_pin(script[left:])})
    old_tree, new_tree = ast.parse(script), ast.parse(data)
    protected = {}
    for attribute, name in (('subprocess', 'Popen'), ('f', 'write'), ('os', 'execve')):
        old = owner._call(old_tree, attribute, name)
        new = owner._call(new_tree, attribute, name)
        protected[attribute + '.' + name] = ast.dump(old) == ast.dump(new)
    _require(all(protected.values()), 'protected source/compiler/exec AST differs')
    proof = {'kind': 'pidfd-event-poll', 'style': style, 'input': _pin(script),
             'output': _pin(data), 'raw_delta': len(data) - len(script), 'spans': spans,
             'protected_gaps': gaps, 'full_inverse': True, 'protected_AST_equal': protected,
             'contract': {'minimum': 'Linux5.3/Python3.9 + poll', 'flags': 0,
                 'normal_compile_wait': 'unchanged blocking WNOWAIT',
                 'group_settlement': 'unchanged procfs loop; pidfd is not group readiness',
                 'setup_failure': 'settle already owned compiler using original monitor; propagate failure',
                 'poll_failure': 'remember primary event error; original bounded monitor settles; no native exec',
                 'retained_leader_and_final_reap': True, 'pidfd_closed_before_native_exec': True,
                 'compiler_signal_grace_and_125_preservation': True}, 'runtime_qualified': False}
    _require(restore_bootstrap(data, proof) == script, 'pidfd whole inverse differs')
    return data, proof
