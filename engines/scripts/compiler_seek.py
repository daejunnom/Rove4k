"""Terminal seek-implied-flush stage for an exactly replayed W1/W2 owner.

The caller supplies its trusted, unchanged owner producer and inverse; callbacks
are an admission dependency, not an authentication boundary. Only the builtin
open(d+'/c','w+b') regular BufferedRandom contract is covered. Python 3.12 says a
BufferedRandom seek writes its buffer to the raw stream:
https://docs.python.org/3.12/library/io.html#io.BufferedWriter

Removing the explicit flush preserves preparation before spawn, but a pending
write failure now surfaces at seek. Explicit flush hooks/tracebacks, monkeypatches
and arbitrary file-like objects are outside this contract. This producer neither
executes the wrapper nor qualifies compiler/engine runtime behavior.
"""
import ast
import copy
import hashlib


_KIND = 'seek-implied-flush-terminal'
_REMOVED = b'f.flush();'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _call(node, owner, name):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == owner and node.func.attr == name)


def _source_file(tree):
    files = [node for node in ast.walk(tree) if isinstance(node, ast.With)
             and len(node.items) == 1
             and _dump(node.items[0].context_expr) == _dump(ast.parse(
                 "open(d+'/c','w+b')", mode='eval').body)]
    _require(len(files) == 1, 'one fixed builtin source-file owner required')
    owner = files[0]
    binding = owner.items[0].optional_vars
    _require(isinstance(binding, ast.Name) and binding.id == 'f'
             and len(owner.body) == 4 and isinstance(owner.body[3], ast.Try),
             'fixed source-file binding/publication differs')
    writes, flushes, seeks = ([node for node in ast.walk(tree) if _call(node, 'f', name)]
                             for name in ('write', 'flush', 'seek'))
    _require(len(writes) == len(flushes) == len(seeks) == 1,
             'one source write/flush/seek required')
    write, flush, seek = writes[0], flushes[0], seeks[0]
    _require(all(isinstance(node, ast.Expr) for node in owner.body[:3])
             and [node.value for node in owner.body[:3]] == [write, flush, seek]
             and len(write.args) == 1 and not write.keywords
             and not flush.args and not flush.keywords
             and _dump(seek) == _dump(ast.parse('f.seek(0)', mode='eval').body),
             'fixed consecutive source preparation differs')
    publications = [node for node in ast.walk(owner.body[3])
                    if _call(node, 'subprocess', 'Popen')]
    _require(len(publications) == 1
             and any(keyword.arg == 'stdin' and isinstance(keyword.value, ast.Name)
                     and keyword.value.id == 'f' for keyword in publications[0].keywords),
             'source-file compiler publication differs')
    return owner, write, flush, seek


def restore_bootstrap(candidate, metadata):
    """Restore the exact W1/W2 input; its own inverse remains caller-owned."""
    _require(type(candidate) is bytes and isinstance(metadata, dict)
             and metadata.get('kind') == _KIND
             and _pin(candidate) == metadata.get('output'), 'seek candidate pin differs')
    edit = metadata.get('edit', {})
    start = edit.get('start')
    _require(type(start) is int and 0 <= start <= len(candidate)
             and edit.get('old') == _REMOVED.decode('ascii') and edit.get('new') == '',
             'seek inverse span differs')
    previous = candidate[:start] + _REMOVED + candidate[start:]
    _require(_pin(previous) == metadata.get('input'), 'seek inverse input differs')
    return previous


def transform_bootstrap(script, *, owner_metadata, prepare_owner, restore_owner):
    """Remove only the explicit flush from an exactly replayed W1/W2 input.

    Pass the same trusted owner callbacks used to prepare owner_metadata; this
    module deliberately does not import or modify that frozen producer. Changed
    opaque source is admitted with its newly generated metadata. Restored-files
    and shared_wait=False inputs are outside this terminal stage.
    """
    _require(type(script) is bytes and b'\r' not in script,
             'LF UTF-8 bootstrap bytes required')
    _require(isinstance(owner_metadata, dict) and owner_metadata.get('output') == _pin(script),
             'owner output pin differs')
    _require(callable(prepare_owner) and callable(restore_owner), 'trusted owner callbacks required')
    predecessor = restore_owner(script, owner_metadata)
    _require(type(predecessor) is bytes, 'owner inverse bytes required')
    replay = prepare_owner(predecessor, shared_wait=True)
    _require(isinstance(replay, tuple) and len(replay) == 2
             and type(replay[0]) is bytes and isinstance(replay[1], dict),
             'owner replay result differs')
    replay_script, canonical = replay
    _require(replay_script == script and canonical.get('input') == _pin(predecessor)
             and canonical.get('output') == _pin(script), 'exact owner replay differs')
    _require(canonical.get('shared_wait') is True
             and canonical.get('W1', {}).get('applied') is True
             and canonical.get('W2', {}).get('applied') is True
             and canonical.get('shape') in ('stdin-stream', 'stdin-ZIP'),
             'seek stage requires applied W1 and shared W2')

    text = script.decode('utf-8')
    tree = ast.parse(text)
    owner, write, flush, seek = _source_file(tree)
    # AST columns are UTF-8 byte offsets, not Python string indices.
    starts = [0]
    for line in script.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))

    def position(node, end=False):
        line = node.end_lineno if end else node.lineno
        column = node.end_col_offset if end else node.col_offset
        return starts[line - 1] + column

    start, end = position(flush), position(flush, True) + 1
    _require(script[position(write, True):start] == b';'
             and script[position(flush, True):position(seek)] == b';'
             and script[start:end] == _REMOVED, 'exact flush statement span differs')
    data = script[:start] + script[end:]
    after_text = data.decode('utf-8')
    after = ast.parse(after_text)
    expected = copy.deepcopy(tree)
    expected_owner, _, _, _ = _source_file(expected)
    del expected_owner.body[1]
    _require(_dump(after) == _dump(expected), 'AST differs beyond explicit flush removal')
    source = ast.get_source_segment(text, write.args[0])
    new_writes = [node for node in ast.walk(after) if _call(node, 'f', 'write')]
    _require(source is not None and len(new_writes) == 1
             and ast.get_source_segment(after_text, new_writes[0].args[0]) == source,
             'opaque source expression spelling differs')
    gaps = [{'old_start': 0, 'new_start': 0, **_pin(script[:start])},
            {'old_start': end, 'new_start': start, **_pin(script[end:])}]
    for gap in gaps:
        _require(script[gap['old_start']:gap['old_start'] + gap['bytes']] ==
                 data[gap['new_start']:gap['new_start'] + gap['bytes']],
                 'protected source gap differs')
    metadata = {'kind': _KIND, 'applied': True, 'shape': canonical['shape'],
                'input': _pin(script), 'output': _pin(data), 'raw_delta': len(data) - len(script),
                'owner_input': _pin(predecessor), 'owner_output': _pin(script),
                'exact_owner_restore_and_replay': True,
                'edit': {'start': start, 'old': _REMOVED.decode('ascii'), 'new': ''},
                'protected_gaps': gaps, 'declared_AST_transform_equal': True,
                'declared_AST_exceptions': ['remove explicit f.flush() before BufferedRandom.seek(0)'],
                'source_expression': _pin(source.encode('utf-8')),
                'protected_source_spelling_equal': True,
                'new_observable_contract': 'builtin regular BufferedRandom seek flushes before rewind/spawn; a pending write error surfaces at seek instead of explicit flush; method hooks and traceback identity excluded',
                'owner_policy_preserved': 'no change to descriptor ownership, source evaluation, mask/publication, parent FD0, WNOWAIT or settlement source',
                'runtime_qualified': False}
    inverse = restore_bootstrap(data, metadata)
    _require(inverse == script and _dump(ast.parse(inverse.decode('utf-8'))) == _dump(tree),
             'whole byte/AST inverse differs')
    metadata.update(full_byte_inverse=True, whole_AST_inverse_equal=True)
    return data, metadata
