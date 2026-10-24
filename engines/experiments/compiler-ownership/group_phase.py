"""Experimental fixed-group grace/KILL policy for closed C compiler owners.

This pure producer changes the termination contract.  A live compiler leader
gets a group-wide graceful phase of five seconds, followed if needed by one
five-second group KILL/settlement phase.  A waitable leader skips grace.  The
original leader remains unreaped until all live group members settle.  The
normal compile wait, source, compiler command, signal mask and final FD exec
are retained.  This is not a replacement for the maintained grace policy.
"""
import ast
import hashlib


VARIANTS = ('nested', 'short', 'loop')
HELPERS = (
    'def k(s):\n try:os.killpg(p.pid,s)\n except ProcessLookupError:pass\n'
    'def w(n,s=0):\n t=time.monotonic()+n\n'
    ' while os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None or l():\n'
    '  if time.monotonic()>t:return 0\n  if s:k(s)\n  time.sleep(.01)\n return 1\n'
)
ALIVE = 'os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None'


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def _private_parts(script, owner):
    """Replay the full existing private owner; opaque C is never rewritten."""
    require(type(script) is bytes and b'\r' not in script, 'LF owner bytes required')
    text = script.decode('utf-8')
    helpers = (owner._GROUP_SHARED.replace('return False', 'return 0')
        .replace('return True', 'return 1').replace('n.isdecimal()', 'n.isdigit()')
        .replace('kill(', 'k(').replace('def wait(', 'def w(').replace('live(', 'l('))
    _, cleanup, directory = owner.render_cleanup(state=True, shared=True)
    private_cleanup = cleanup.replace('if p is not None:', 'if p:').replace('kill(', 'k(').replace('not wait(', 'not w(')
    private_directory = directory.replace('if d is not None:', 'if d:')
    for old, new in ((helpers, owner._GROUP_SHARED), (private_cleanup, cleanup), (private_directory, directory)):
        require(text.count(old) == 1, 'one exact private owner region required')
        text = text.replace(old, new, 1)
    restored = text.encode('utf-8')
    parts = owner._admit_prepared(restored, cleanup={'state': True, 'wait': False, 'termination': 'grace'})
    current, proof = owner.compact_private_owner(restored)
    require(current == script, 'complete current private owner replay differs')
    changes = {span['role']: span['new'] for span in proof['spans']}
    result = [(role, changes.get(role, value)) for role, value in owner._prepared_parts(parts, state=True)]
    require(owner._joined(result) == script, 'private owner part replay differs')
    return parts, result


def _cleanup(variant, mask):
    start = ' finally:\n  ' + mask + '\n  if p:\n   a=d;d=None\n'
    if variant == 'nested':
        phase = ('   b=0\n   if ' + ALIVE + ':\n    k(q);b=w(5)\n'
            '   if not b and not(k(9)or w(5,9)):raise SystemExit(125)\n')
    elif variant == 'short':
        phase = ('   if not((' + ALIVE + ' and(k(q)or w(5)))or k(9)or w(5,9)):'
            'raise SystemExit(125)\n')
    else:
        phase = ('   b=' + ALIVE + '\n   if b:k(q)\n'
            '   for s in (0,9)if b else(9,):\n    if s:k(s)\n'
            '    if w(5,s):break\n   else:raise SystemExit(125)\n')
    return start + phase + '   p.wait();d=a\n'


def transform_bootstrap(script, *, owner, variant='short'):
    """Transform only the complete current state=True/private grace scaffold."""
    require(variant in VARIANTS, 'explicit group-phase variant required')
    parts, before = _private_parts(script, owner)
    after = []
    for role, value in before:
        if role == 'helpers':
            live = value[value.index('def l():'):]
            value = HELPERS + live
        elif role == 'cleanup':
            value = _cleanup(variant, owner._MASK)
        after.append((role, value))
    data = owner._joined(after)
    ast.parse(data)
    left = right = a = b = 0
    spans, gaps = [], []
    for (role, old), (_, new) in zip(before, after):
        old, new = old.encode(), new.encode()
        if old != new:
            require(script[left:a] == data[right:b], 'protected owner gap differs')
            gaps.append({'old_start': left, 'new_start': right, **pin(script[left:a])})
            spans.append({'role': role, 'old_start': a, 'new_start': b, 'old': old.decode(), 'new': new.decode()})
            left, right = a + len(old), b + len(new)
        a += len(old)
        b += len(new)
    require(script[left:] == data[right:], 'protected owner suffix differs')
    gaps.append({'old_start': left, 'new_start': right, **pin(script[left:])})
    record = {'kind': 'group-phase-owner-v1', 'variant': variant, 'input': pin(script), 'output': pin(data),
        'spans': spans, 'protected_gaps': gaps, 'raw_delta': len(data)-len(script), 'full_inverse': True,
        'source_expression': pin(parts['source'].encode()), 'opaque_source_spelling_equal': True,
        'runtime_qualified': False, 'contract': {
            'normal_compile_wait': 'unchanged blocking WNOWAIT', 'live_leader_group_grace_seconds': 5,
            'waitable_leader_skips_grace': True, 'group_KILL_settlement_seconds': 5,
            'group_KILL_repeated_during_poll': True, 'retained_leader_and_last_reap': True,
            'each_phase_requires_leader_waitability_and_no_live_group': True,
            'workspace_preserved_until_successful_settlement': True, 'settlement_timeout_status': 125,
            'compiler_and_parent_cancel_status': 'unchanged on successful cleanup; cleanup exceptions retain Python finally precedence',
            'fixed_private_PGID': True,
            'same_as_maintained_grace': False, 'policy_change': 'group-wide two-phase termination with two nominal five-second deadlines',
            'limits': ['no malicious process-group movement containment', 'same Linux procfs live-group observation as current owner']}}
    require(restore_bootstrap(data, record) == script, 'group-phase full inverse differs')
    return data, record


def restore_bootstrap(candidate, record):
    require(type(candidate) is bytes and record.get('kind') == 'group-phase-owner-v1'
        and pin(candidate) == record.get('output'), 'group-phase candidate identity differs')
    result = candidate
    for span in reversed(record['spans']):
        at, old, new = span['new_start'], span['old'].encode(), span['new'].encode()
        require(result[at:at+len(new)] == new, 'group-phase inverse span differs')
        result = result[:at] + old + result[at+len(new):]
    require(pin(result) == record.get('input'), 'group-phase inverse input differs')
    return result
