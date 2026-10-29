"""Experimental fixed-PGID compiler owner using Linux subreaper child waits.

This pure generator accepts the project's complete private prepared C owner by
reconstructing its canonical predecessor through the supplied compiler_group
module. It changes ownership, rather than silently implementing the old
leader-last-reap algorithm. It is not connected to maintained builders.
"""
import ast
import hashlib


def pin(value):
    return {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}


def _admit(script, owner):
    if type(script) is not bytes or b'\r' in script:
        raise ValueError('immutable LF prepared C owner required')
    text = script.decode('utf-8')
    tree = ast.parse(text)
    call = owner._call(tree, 'subprocess', 'Popen')
    write = owner._call(tree, 'f', 'write')
    source = ast.get_source_segment(text, write.args[0])
    if type(ast.literal_eval(source)) is not bytes:
        raise ValueError('this experiment supports only literal C source')
    environment = ''
    if owner._dump(call.keywords[1].value) == owner._dump(owner._expression('e')):
        environment = next((value for value in (
            " e=dict(os.environ,TMPDIR=d)\n", " e=os.environ.copy();e['TMPDIR']=d\n")
            if text.count(value) == 1), None)
        if environment is None:
            raise ValueError('prepared environment changed')
    parts = {
        'imports': 'import os,signal,subprocess,sys,tempfile,shutil,time\n',
        'environment': environment, 'source': source,
        'call': ast.get_source_segment(text, call),
        'open': ast.get_source_segment(text, owner._call(tree, 'os', 'open')),
        'exec': ast.get_source_segment(text, owner._call(tree, 'os', 'execve')),
        'register': next((value for value in owner._REGISTER if text.count(value) == 1), None),
        'reset': next((value for value in owner._RESET if text.count(value) == 1), None)}
    if parts['register'] is None or parts['reset'] is None:
        raise ValueError('prepared signal pairs changed')
    before = owner._joined(owner._prepared_parts(parts, state=True))
    owner._admit_prepared(before, cleanup={'state': True})
    expected, proof = owner.compact_private_owner(before)
    if expected != script or owner.restore_bootstrap(expected, proof) != before:
        raise ValueError('complete private prepared owner differs')
    return parts, owner._prepared_parts(parts, state=True)


REAP = (
    'def a():\n'
    ' while 1:\n'
    '  try:i,s=os.waitpid(-p.pid,os.WNOHANG)\n'
    '  except ChildProcessError:return 0\n'
    '  if not i:return 1\n'
    '  if i==p.pid:p.returncode=os.waitstatus_to_exitcode(s)\n'
    'def k(s):\n'
    ' if a():\n'
    '  try:os.killpg(p.pid,s)\n'
    '  except ProcessLookupError:pass\n'
    'def w(n,g=0):\n'
    ' t=time.monotonic()+n\n'
    ' while a()and(g or p.returncode is None):\n'
    '  if time.monotonic()>t:return 0\n'
    '  if g:k(9)\n'
    '  time.sleep(.01)\n'
    ' return 1\n')


def transform_bootstrap(script, *, owner, abi='pointer'):
    """Produce a separate Linux x86-64, sole-reaper, fixed-PGID contract.

    Raw wait/reap happens only inside the existing INT/TERM-masked cleanup.
    A positive PID is processed and immediately re-waited without a signal.
    ECHILD ends that ownership scope; every group signal probes a fresh owned
    unreaped child first. SIGCHLD DFL and no independently reaping Popen call
    are required. Descendant PGID/session movement and ptrace are unsupported.
    Subreaper setup precedes compiler spawn; restoration precedes engine exec.
    On an earlier failure the wrapper exits without executing the engine.
    """
    if abi not in ('pointer', 'ulong'):
        raise ValueError('explicit prctl argument ABI required')
    parts, before = _admit(script, owner)
    ffi = ('pr=ctypes.CDLL(None,use_errno=True).prctl\n'
           'v=ctypes.c_int()\n')
    if abi == 'pointer':
        ffi += ('pr.argtypes=ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong\n')
        get = 'ctypes.byref(v)'
    else:
        ffi += 'u=ctypes.c_ulong\npr.argtypes=ctypes.c_int,u,u,u,u\n'
        get = 'ctypes.addressof(v)'
    ffi += ('def sr(n,a):\n'
            " if pr(n,a,0,0,0):raise OSError(ctypes.get_errno(),'prctl')\n")
    values = dict(before)
    values['imports'] = values['imports'].rstrip('\n') + ',ctypes\n'
    values['helpers'] = ffi + REAP
    values['directory_start'] = values['directory_start'].replace(
        '\ntry:\n', '\ntry:\n sr(37,' + get + ');sr(36,1)\n', 1)
    values['cleanup'] = (
        ' finally:\n  ' + owner._MASK + '\n  if p is not None:\n'
        '   if not w(0):k(q)\n   if not w(5):\n'
        '    k(9)\n    if not w(5):d=None;raise SystemExit(125)\n'
        '   k(9)\n   if not w(5,1):d=None;raise SystemExit(125)\n')
    values['directory_cleanup'] = 'finally:\n if d:shutil.rmtree(d)\n'
    values['execute'] = 'sr(36,v.value)\n' + values['execute']
    after = [(role, values[role]) for role, _ in before]
    result = owner._joined(after)
    ast.parse(result)
    tree = ast.parse(result)
    for attribute in ('wait', 'poll', 'communicate'):
        if owner._calls(tree, 'p', attribute):
            raise ValueError('independent Popen reap remains')
    if owner._dump(owner._call(tree, 'subprocess', 'Popen')) != owner._dump(ast.parse(parts['call'], mode='eval').body):
        raise ValueError('compiler fields changed')
    if owner._dump(owner._call(tree, 'os', 'execve')) != owner._dump(ast.parse(parts['exec'], mode='eval').body):
        raise ValueError('engine FD/argv changed')
    record = {'kind': 'experimental-Linux-subreaper-fixed-PGID-v1',
        'input': pin(script), 'output': pin(result), 'raw_delta': len(result)-len(script),
        'source_expression': pin(parts['source'].encode()), 'source_spelling_unchanged': True,
        'compiler_and_FD_exec_AST_equal': True, 'prctl_abi': abi,
        'normal_wait': 'blocking waitid WNOWAIT; no reaping',
        'cleanup': 'masked sole raw waiter; positive PID immediately re-waits; fresh0 authorizes signal; ECHILD ends scope',
        'compiler_status': 'waitstatus_to_exitcode assigned to retained Popen.returncode; legacy sys.exit(returncode)',
        'parent_cancel_status': 'SystemExit128+signal', 'subreaper_restore': 'captured flag restored before engine exec; earlier errors exit wrapper',
        'required': ['Linux x86-64', 'fixed private PGID/session', 'single reaper', 'SIGCHLD DFL; no SA_NOCLDWAIT',
                     'no ptrace', 'no descendant PGID/session movement'],
        'runtime_qualified': False, 'default_builder_connected': False}
    return result, record
