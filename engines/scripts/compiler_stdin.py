"""Terminal input-file and shared-wait stages for exactly admitted owners.

This is a pure producer transform, not a general Python rewrite. The existing
compiler_group output is reconstructed exactly before either declared stage.
W1 changes compiler stdin transport for stream/ZIP only; W2 shares the existing
leader/group wait body for all three admitted shapes. Neither stage is engine
runtime qualification. Existing compiler_group.py is intentionally unchanged.
"""
import ast
import copy
import hashlib


_GROUP = "def kill(s):\n try:os.killpg(p.pid,s)\n except ProcessLookupError:pass\ndef wait(n):\n t=time.monotonic()+n\n while os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None:\n  if time.monotonic()>t:return False\n  time.sleep(.01)\n return True\ndef live():\n for n in os.listdir('/proc'):\n  if n.isdecimal():\n   try:\n    with open('/proc/'+n+'/stat') as f:a=f.read().rsplit(')',1)[1].split()\n    if int(a[2])==p.pid and a[0]!='Z':return True\n   except (OSError,ValueError,IndexError):pass\n return False\n"
_STOP = 'def stop(s,f):\n global q\n q=s\n signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n raise SystemExit(128+s)\n'
_REGISTER = ('signal.signal(2,stop);signal.signal(15,stop)\n', 'for s in 2,15:signal.signal(s,stop)\n')
_RESET = ('signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n', 'for s in 2,15:signal.signal(s,signal.SIG_DFL)\n')
_MASK = 'signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})'
_UNMASK = 'signal.pthread_sigmask(signal.SIG_SETMASK,m)'
_RESTORE = " a=4\n for _ in range(struct.unpack_from('<I',b)[0]):\n  n,s=struct.unpack_from('<HI',b,a);a+=6;f=d+'/'+b[a:a+n].decode();a+=n\n  os.makedirs(os.path.dirname(f),exist_ok=True)\n  with open(f,'wb') as o:o.write(b[a:a+s])\n  a+=s\n"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _expression(text):
    return ast.parse(text, mode='eval').body


def _calls(tree, owner, name):
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == name
            and isinstance(node.func.value, ast.Name) and node.func.value.id == owner]


def _one(tree, owner, name):
    nodes = _calls(tree, owner, name)
    _require(len(nodes) == 1, 'expected one ' + owner + '.' + name + ' call')
    return nodes[0]


def _segment(text, node):
    value = ast.get_source_segment(text, node)
    _require(value is not None, 'missing exact expression source')
    return value


def _admit(script):
    _require(type(script) is bytes and b'\r' not in script, 'LF UTF-8 bootstrap bytes required')
    text = script.decode('utf-8')
    tree = ast.parse(text)
    popen = _one(tree, 'subprocess', 'Popen')
    fdopen = _one(tree, 'os', 'open')
    execute = _one(tree, 'os', 'execve')
    _require(len(popen.args) == 1, 'fixed compiler call differs')
    _require(not any(isinstance(node, ast.Name) for node in ast.walk(popen.args[0])),
             'closed compiler argv required')
    command = _segment(text, popen.args[0])
    call = _segment(text, popen)
    open_call = _segment(text, fdopen)
    exec_call = _segment(text, execute)
    _require(exec_call in ('os.execve(fd,sys.argv[1:],os.environ)',
                          'os.execve(fd,sys.argv,os.environ)'), 'fixed FD argv execution differs')
    registration = next((value for value in _REGISTER if text.count(value) == 1), None)
    reset = next((value for value in _RESET if text.count(value) == 1), None)
    _require(registration is not None and reset is not None, 'fixed signal handlers differ')
    views = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == 'memoryview']
    _require(len(views) <= 1, 'fixed compiler stdin differs')
    source = None
    restore = before_fd = archive = ''
    if views:
        feed = views[0]
        _require(len(feed.args) == 1 and not feed.keywords, 'fixed memoryview differs')
        source = _segment(text, feed.args[0])
        zipped = source == "zipfile.ZipFile(sys.argv[0]).read('c')"
        _require(zipped or not any(isinstance(node, ast.Name) and node.id != '__ROVE_SOURCE_LITERAL__'
                                  for node in ast.walk(feed.args[0])), 'closed source expression required')
        _require([key.arg for key in popen.keywords] ==
                 ['cwd', 'env', 'stdin', 'bufsize', 'start_new_session', 'preexec_fn'],
                 'fixed compiler stdin options differ')
        fixed = ('d', None, 'subprocess.PIPE', '0', 'True', 'lambda:signal.pthread_sigmask(signal.SIG_SETMASK,m)')
        for key, expected in zip(popen.keywords, fixed):
            if expected is not None:
                _require(_dump(key.value) == _dump(_expression(expected)), 'fixed Popen field differs: ' + key.arg)
        env = popen.keywords[1].value
        if _dump(env) == _dump(_expression('e')):
            env_line = next((line for line in (" e=dict(os.environ,TMPDIR=d)\n",
                " e=os.environ.copy();e['TMPDIR']=d\n") if text.count(line) == 1), None)
            _require(env_line is not None, 'fixed compiler environment differs')
        else:
            _require(_dump(env) == _dump(_expression('dict(os.environ,TMPDIR=d)')),
                     'fixed inline compiler environment differs')
            env_line = ''
        _require(open_call in ("os.open(d+'/x',0)", "os.open(d+'/x',os.O_RDONLY)"),
                 'fixed compiler result FD differs')
        imports = 'import os,signal,subprocess,sys,tempfile' + (',zipfile' if zipped else '') + ',shutil,time\n'
        status = ' if p.returncode:sys.exit(p.returncode)\n'
        shape = 'stdin-ZIP' if zipped else 'stdin-stream'
    else:
        _require([key.arg for key in popen.keywords] ==
                 ['cwd', 'env', 'start_new_session', 'preexec_fn'], 'fixed restored compiler options differ')
        fixed = ('d', 'e', 'True', 'lambda:signal.pthread_sigmask(signal.SIG_SETMASK,m)')
        for key, expected in zip(popen.keywords, fixed):
            _require(_dump(key.value) == _dump(_expression(expected)), 'fixed Popen field differs: ' + key.arg)
        _require(open_call == 'os.open(f,os.O_RDONLY)', 'fixed restored result FD differs')
        update = _one(tree, 'e', 'update')
        _require(len(update.args) == 1 and not update.keywords
                 and isinstance(ast.literal_eval(update.args[0]), dict), 'closed environment overrides required')
        env_line = " e=os.environ.copy();e.update(" + _segment(text, update.args[0]) + ");e['TMPDIR']=d\n"
        assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                       and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id == 'b']
        _require(len(assignments) == 1, 'fixed archive assignment differs')
        archive = _segment(text, assignments[0]) + '\n'
        module = next((name for name in ('zlib', 'bz2', 'lzma') if text.startswith(
            '#!/usr/bin/python3\nimport base64,os,signal,struct,subprocess,sys,tempfile,' + name + ',shutil,time\n')), None)
        if module is None:
            imports = '#!/usr/bin/python3\nimport os,signal,struct,subprocess,sys,tempfile,zipfile,shutil,time\n'
            _require(text.startswith(imports) and archive == "b=zipfile.ZipFile(sys.argv[0]).read('p')\n",
                     'fixed ZIP transport archive differs')
        else:
            imports = '#!/usr/bin/python3\nimport base64,os,signal,struct,subprocess,sys,tempfile,' + module + ',shutil,time\n'
            value = assignments[0].value
            blob = value.args[0].args[0] if isinstance(value, ast.Call) and len(value.args) == 1 \
                and isinstance(value.args[0], ast.Call) and len(value.args[0].args) == 1 else None
            _require(isinstance(blob, ast.Constant) and type(blob.value) is bytes
                     and archive == 'b=' + module + '.decompress(base64.b85decode(' + repr(blob.value) + '))\n',
                     'fixed base85 archive differs')
        outer = [node for node in tree.body if isinstance(node, ast.Try)]
        _require(len(outer) == 1, 'fixed outer owner differs')
        fields = outer[0].body
        paths = [node for node in fields if isinstance(node, ast.Assign) and len(node.targets) == 1
                 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'f']
        _require(len(paths) == 1, 'fixed restored path differs')
        path = paths[0]
        _require(isinstance(path.value, ast.BinOp) and isinstance(path.value.op, ast.Add)
                 and _dump(path.value.left) == _dump(_expression('d'))
                 and isinstance(path.value.right, ast.Constant) and type(path.value.right.value) is str
                 and path.value.right.value.startswith('/'), 'fixed restored path value differs')
        before_fd = ' ' + _segment(text, path) + ';os.chmod(f,448)\n'
        restore = _RESTORE
        status = ' r=p.returncode\n if r:sys.exit(r)\n'
        shape = 'restored-files'
    expected = (imports + 'p=None;q=15;d=None;clean=True\n' + _STOP + _GROUP + registration + archive +
        'h=signal.signal(signal.SIGCHLD,signal.SIG_DFL)\nm=' + _MASK + '\ntry:\n' +
        " d=tempfile.mkdtemp(prefix='r4-')\n" + restore + env_line +
        ' try:\n  try:p=' + call + '\n  finally:' + _UNMASK + '\n' +
        (('  try:\n   v=memoryview(' + source + ')\n   while v:v=v[os.write(p.stdin.fileno(),v):]\n' +
          '  except BrokenPipeError:pass\n  finally:p.stdin.close()\n') if source is not None else '') +
        '  os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT)\n finally:\n  ' + _MASK + '\n' +
        '  if p is not None:\n   if not wait(0):kill(q)\n   if not wait(5):\n    kill(9)\n' +
        '    if not wait(5):clean=False;raise SystemExit(125)\n' +
        '   kill(9);t=time.monotonic()+5\n   while live():\n' +
        '    if time.monotonic()>t:clean=False;raise SystemExit(125)\n' +
        '    kill(9);time.sleep(.01)\n   p.wait()\n' + status + before_fd + ' fd=' + open_call + '\n' +
        'finally:\n if d is not None and clean:shutil.rmtree(d)\n' + reset +
        'signal.signal(signal.SIGCHLD,h)\n' + _UNMASK + '\n' + exec_call + '\n').encode('utf-8')
    _require(expected == script, 'bootstrap contains an unknown owner scaffold change')
    return text, tree, shape, command



def _view(tree):
    views = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == 'memoryview']
    _require(len(views) == 1 and len(views[0].args) == 1 and not views[0].keywords,
             'one admitted source view required')
    return views[0]


def _owned(tree):
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    call = _one(tree, 'subprocess', 'Popen')
    assignment = parents[call]
    publication = parents[assignment]
    owner = parents[publication]
    _require(isinstance(assignment, ast.Assign) and isinstance(publication, ast.Try)
             and isinstance(owner, ast.Try) and len(owner.body) == 3
             and owner.body[0] is publication and isinstance(owner.body[1], ast.Try),
             'fixed pipe publication/feed/wait owner differs')
    return parents, call, publication, owner, owner.body[1]


def _restore_file(candidate, metadata):
    _require(_pin(candidate) == metadata['output'], 'candidate pin differs')
    edit = metadata['edit']
    start = edit['start']
    new = edit['new'].encode('utf-8')
    _require(candidate[start:start + len(new)] == new, 'W1 transport span differs')
    old = candidate[:start] + edit['old'].encode('utf-8') + candidate[start + len(new):]
    _require(_pin(old) == metadata['input'], 'W1 inverse input differs')
    return old


def _file_stdin(script, admitted):
    text, tree, shape, command = admitted
    _require(shape in ('stdin-stream', 'stdin-ZIP'), 'W1 not applicable: restored-files has no stdin pipe')
    parents, popen, publication, owner, feed = _owned(tree)
    view = _view(tree)
    source = ast.get_source_segment(text, view.args[0])
    call = ast.get_source_segment(text, popen)
    _require(source is not None and call is not None, 'exact opaque expression source required')
    token = 'stdin=subprocess.PIPE,bufsize=0'
    _require(call.count(token) == 1, 'fixed pipe stdin/bufsize differs')
    new_call = call.replace(token, 'stdin=f', 1)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == 'f':
            parent = node
            while parent in parents and not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                parent = parents[parent]
            _require(isinstance(parent, ast.FunctionDef) and parent.name == 'live',
                     'private source file module binding f collision')
    unmask = 'signal.pthread_sigmask(signal.SIG_SETMASK,m)'
    before = ('  try:p=' + call + '\n  finally:' + unmask + '\n' +
              '  try:\n   v=memoryview(' + source + ')\n' +
              '   while v:v=v[os.write(p.stdin.fileno(),v):]\n' +
              '  except BrokenPipeError:pass\n  finally:p.stdin.close()\n').encode('utf-8')
    after = ("  with open(d+'/c','w+b') as f:\n" +
             '   f.write(' + source + ');f.flush();f.seek(0)\n' +
             '   try:p=' + new_call + '\n   finally:' + unmask + '\n').encode('utf-8')
    lines = script.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    start = starts[publication.lineno - 1]
    end = starts[feed.end_lineno]
    _require(script[start:end] == before and script.count(before) == 1,
             'fixed owner input transport span differs')
    candidate = script[:start] + after + script[end:]
    result_tree = ast.parse(candidate.decode('utf-8'))
    expected_tree = copy.deepcopy(tree)
    _, expected_popen, expected_publication, expected_owner, expected_feed = _owned(expected_tree)
    expected_source = _view(expected_tree).args[0]
    expected_with = ast.parse("with open(d+'/c','w+b') as f:\n f.write(0);f.flush();f.seek(0)\n pass\n").body[0]
    expected_with.body[0].value.args[0] = copy.deepcopy(expected_source)
    expected_popen.keywords = [keyword for keyword in expected_popen.keywords if keyword.arg != 'bufsize']
    for keyword in expected_popen.keywords:
        if keyword.arg == 'stdin':
            keyword.value = ast.Name(id='f', ctx=ast.Load())
    expected_with.body[-1] = expected_publication
    expected_owner.body[:2] = [expected_with]
    _require(_dump(result_tree) == _dump(expected_tree), 'candidate differs beyond declared W1 AST exception')
    new_popen = _one(result_tree, 'subprocess', 'Popen')
    old_fields = [popen.args[0], *(keyword for keyword in popen.keywords if keyword.arg not in ('stdin', 'bufsize'))]
    new_fields = [new_popen.args[0], *(keyword for keyword in new_popen.keywords if keyword.arg != 'stdin')]
    _require([_dump(field) for field in old_fields] == [_dump(field) for field in new_fields],
             'protected Popen argv/environment/session/mask fields differ')
    write = _one(result_tree, 'f', 'write')
    _require(len(write.args) == 1 and not write.keywords
             and ast.get_source_segment(candidate.decode('utf-8'), write.args[0]) == source,
             'opaque source/ZIP expression spelling differs')
    for name in ('open', 'execve'):
        _require(_dump(_one(tree, 'os', name)) == _dump(_one(result_tree, 'os', name)),
                 'protected engine FD expression differs')
    gaps = [{'old_start': 0, 'new_start': 0, **_pin(script[:start])},
            {'old_start': end, 'new_start': start + len(after), **_pin(script[end:])}]
    for gap in gaps:
        _require(script[gap['old_start']:gap['old_start'] + gap['bytes']] ==
                 candidate[gap['new_start']:gap['new_start'] + gap['bytes']], 'owner gap differs')
    metadata = {'applied': True, 'kind': 'declared-stdin-transport-W1', 'shape': shape,
        'input': _pin(script), 'output': _pin(candidate), 'raw_delta': len(candidate) - len(script),
        'exact_previous_owner_admission': True,
        'edit': {'start': start, 'old': before.decode('utf-8'), 'new': after.decode('utf-8')},
        'protected_gaps': gaps, 'declared_AST_transform_equal': True,
        'declared_AST_exceptions': ['pre-spawn private buffered regular file write/flush/rewind and owned with block',
            'Popen stdin PIPE to f and removal of pipe-only bufsize0',
            'remove post-spawn memoryview/os.write/BrokenPipe/p.stdin.close transport only'],
        'source_expression': _pin(source.encode('utf-8')), 'source_expression_evaluations': 1,
        'command_expression': command, 'protected_other_Popen_fields_equal': True,
        'protected_source_spelling_equal': True, 'protected_engine_FD_open_exec_equal': True,
        'parent_FD0_modified': False, 'compiler_argv_x_c_stdin_unchanged': True,
        'new_observable_contract': 'compiler FD0 is seekable regular file, not pipe; source preparation errors happen before spawn',
        'preparation_mask': 'existing INT/TERM blocked interval retained and extended through file preparation; pending cancel may be delivered only after spawn publication/unmask',
        'prepare_cancel_compiler0_guarantee': False,
        'file_ownership': 'with inside compiler-owning try; full buffered write/flush/seek0 before Popen; close after publication/unmask and before wait/settlement/engine exec; no parent offset operations after spawn',
        'inheritance': 'open creates non-inheritable parent descriptor; Popen duplicates source onto child FD0; no pass_fds or parent dup2',
        'owner_policy_preserved': 'leader WNOWAIT, original mask/spawn/publication/unmask, live group drain before reap, readable-proc and cleanFalse125 workspace policy',
        'runtime_claim': 'none; only source/AST and codec evidence in this phase'}
    inverse = _restore_file(candidate, metadata)
    _require(inverse == script and _dump(ast.parse(inverse.decode('utf-8'))) == _dump(tree),
             'whole byte/AST inverse differs')
    metadata.update(full_byte_inverse=True, whole_AST_inverse_equal=True)
    return candidate, metadata

_OLD_WAIT = b'def wait(n):\n t=time.monotonic()+n\n while os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None:\n  if time.monotonic()>t:return False\n  time.sleep(.01)\n return True\n'
_NEW_WAIT = b'def wait(n,g=0):\n t=time.monotonic()+n\n while live() if g else os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None:\n  if time.monotonic()>t:return False\n  if g:kill(9)\n  time.sleep(.01)\n return True\n'
_OLD_DRAIN = b'   kill(9);t=time.monotonic()+5\n   while live():\n    if time.monotonic()>t:clean=False;raise SystemExit(125)\n    kill(9);time.sleep(.01)\n'
_NEW_DRAIN = b'   kill(9)\n   if not wait(5,1):clean=False;raise SystemExit(125)\n'


def _restore_wait(candidate, metadata):
    _require(_pin(candidate) == metadata['output'], 'shared-wait candidate pin differs')
    inverse = candidate
    for span in reversed(metadata['spans']):
        start = span['new_start']
        old, new = span['old'].encode('utf-8'), span['new'].encode('utf-8')
        _require(inverse[start:start + len(new)] == new, 'shared-wait span differs')
        inverse = inverse[:start] + old + inverse[start + len(new):]
    _require(_pin(inverse) == metadata['input'], 'shared-wait inverse pin differs')
    return inverse


def _share_wait(script):
    _require(script.count(_OLD_WAIT) == script.count(_OLD_DRAIN) == 1,
             'exact wait/drain regions required')
    edits = [(script.index(_OLD_WAIT), _OLD_WAIT, _NEW_WAIT),
             (script.index(_OLD_DRAIN), _OLD_DRAIN, _NEW_DRAIN)]
    cursor = written = 0
    out, spans, gaps = [], [], []
    for start, old, new in sorted(edits):
        _require(start >= cursor and script[start:start + len(old)] == old,
                 'shared-wait input span differs')
        gap = script[cursor:start]
        gaps.append({'old_start': cursor, 'new_start': written, **_pin(gap)})
        out.extend((gap, new))
        written += len(gap)
        spans.append({'old_start': start, 'new_start': written,
                      'old': old.decode('utf-8'), 'new': new.decode('utf-8')})
        written += len(new)
        cursor = start + len(old)
    gap = script[cursor:]
    gaps.append({'old_start': cursor, 'new_start': written, **_pin(gap)})
    out.append(gap)
    data = b''.join(out)
    for gap in gaps:
        _require(script[gap['old_start']:gap['old_start'] + gap['bytes']] ==
                 data[gap['new_start']:gap['new_start'] + gap['bytes']],
                 'shared-wait protected gap differs')
    before = script.replace(_OLD_WAIT, b'def wait():pass\n').replace(_OLD_DRAIN, b'   __W2_DRAIN__\n')
    after = data.replace(_NEW_WAIT, b'def wait():pass\n').replace(_NEW_DRAIN, b'   __W2_DRAIN__\n')
    _require(_dump(ast.parse(before.decode('utf-8'))) == _dump(ast.parse(after.decode('utf-8'))),
             'AST outside declared shared-wait regions differs')
    metadata = {'applied': True, 'kind': 'shared-leader-and-group-wait-W2',
                'input': _pin(script), 'output': _pin(data), 'raw_delta': len(data) - len(script),
                'spans': spans, 'protected_gaps': gaps, 'outside_owned_regions_AST_equal': True,
                'declared_AST_exceptions': ['wait(n,g=0) body', 'final live-group wait call'],
                'contract': 'each call starts its own deadline; normal WNOWAIT remains unbounded; initial final KILL and repeated KILL after deadline check preserved',
                'runtime_claim': 'none; source transformation alone is not wait/group qualification'}
    _require(_restore_wait(data, metadata) == script, 'shared-wait full inverse differs')
    metadata['full_byte_inverse'] = True
    return data, metadata


def restore_bootstrap(candidate, metadata):
    """Undo the declared stages; metadata belongs to this exact candidate."""
    _require(type(candidate) is bytes and _pin(candidate) == metadata['output'],
             'terminal candidate pin differs')
    previous = candidate
    if metadata['W2']['applied']:
        previous = _restore_wait(previous, metadata['W2'])
    if metadata['W1']['applied']:
        previous = _restore_file(previous, metadata['W1'])
    _require(_pin(previous) == metadata['input'], 'terminal inverse pin differs')
    return previous


def transform_bootstrap(script, *, shared_wait=True):
    """Apply W1 where applicable, then optional W2 (default True).

    Input must be the exact current compiler_group emission, including the
    general ZIP transport's declared final archive expression. Restored-files
    explicitly records W1 as not applicable; it still receives W2 by default.
    The caller must supply its established compile-input-only source contract.
    """
    _require(type(shared_wait) is bool, 'shared_wait must be an explicit bool')
    admitted = _admit(script)
    shape = admitted[2]
    if shape in ('stdin-stream', 'stdin-ZIP'):
        data, file_metadata = _file_stdin(script, admitted)
        file_metadata['compile_input_only_required'] = True
        file_metadata['named_file_observation'] = 'private cwd gains c; arbitrary source/include/argv filesystem observations are outside this transform contract'
        file_metadata['parent_stdin_contract'] = 'original open UCI FD0 is preserved; parent performs no dup2'
    else:
        data = script
        file_metadata = {'applied': False, 'kind': 'declared-stdin-transport-W1',
                         'shape': shape, 'input': _pin(script), 'output': _pin(script), 'raw_delta': 0,
                         'reason': 'restored-files has no compiler stdin pipe; W1 is not applicable',
                         'full_byte_inverse': True, 'whole_AST_inverse_equal': True}
    if shared_wait:
        data, wait_metadata = _share_wait(data)
    else:
        wait_metadata = {'applied': False, 'kind': 'shared-leader-and-group-wait-W2',
                         'input': _pin(data), 'output': _pin(data), 'raw_delta': 0,
                         'reason': 'shared_wait=False explicitly selects the previous wait representation',
                         'full_byte_inverse': True}
    metadata = {'shape': shape, 'input': _pin(script), 'output': _pin(data),
                'raw_delta': len(data) - len(script), 'shared_wait': shared_wait,
                'exact_corrected_owner_reconstruction': True, 'W1': file_metadata, 'W2': wait_metadata,
                'observational_contract': 'declared input transport and wait representation; no general Python or arbitrary compiler equivalence',
                'runtime_qualified': False}
    inverse = restore_bootstrap(data, metadata)
    _require(inverse == script and _dump(ast.parse(inverse.decode('utf-8'))) == _dump(admitted[1]),
             'terminal whole byte/AST inverse differs')
    metadata.update(full_byte_inverse=True, whole_AST_inverse_equal=True)
    return data, metadata
