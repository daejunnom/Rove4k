"""Late ownership repair for the project's three compiler-wrapper shapes.

Pure source transformation, after the producer's literal/argv checks and before
encoding.  No file/environment reads or execution.  The old wrapper is rebuilt
exactly; closed command/source, archive restoration, environment and FD execution
expressions are retained.  Runtime settlement is shared with qualified Rust/C
stream wrappers: keep the original leader unreaped until its live group drains.
"""
import ast
import hashlib

_GROUP = "def kill(s):\n try:os.killpg(p.pid,s)\n except ProcessLookupError:pass\ndef wait(n):\n t=time.monotonic()+n\n while os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None:\n  if time.monotonic()>t:return False\n  time.sleep(.01)\n return True\ndef live():\n for n in os.listdir('/proc'):\n  if n.isdecimal():\n   try:\n    with open('/proc/'+n+'/stat') as f:a=f.read().rsplit(')',1)[1].split()\n    if int(a[2])==p.pid and a[0]!='Z':return True\n   except (OSError,ValueError,IndexError):pass\n return False\n"
_STOP = 'def stop(s,f):\n global q\n q=s\n signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n raise SystemExit(128+s)\n'
_REGISTER = ('signal.signal(2,stop);signal.signal(15,stop)\n', 'for s in 2,15:signal.signal(s,stop)\n')
_RESET = ('signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n', 'for s in 2,15:signal.signal(s,signal.SIG_DFL)\n')
_MASK = 'signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})'
_UNMASK = 'signal.pthread_sigmask(signal.SIG_SETMASK,m)'
_DIRECTORY = "with tempfile.TemporaryDirectory(prefix='r4-') as d:\n"
_RESTORE = " a=4\n for _ in range(struct.unpack_from('<I',b)[0]):\n  n,s=struct.unpack_from('<HI',b,a);a+=6;f=d+'/'+b[a:a+n].decode();a+=n\n  os.makedirs(os.path.dirname(f),exist_ok=True)\n  with open(f,'wb') as o:o.write(b[a:a+s])\n  a+=s\n"
_WAIT = 'def wait(n):\n t=time.monotonic()+n\n while os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None:\n  if time.monotonic()>t:return False\n  time.sleep(.01)\n return True\n'
_SHARED_WAIT = 'def wait(n,g=0):\n t=time.monotonic()+n\n while live() if g else os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT|os.WNOHANG) is None:\n  if time.monotonic()>t:return False\n  if g:kill(9)\n  time.sleep(.01)\n return True\n'
_GROUP_SHARED = _GROUP.replace(_WAIT, _SHARED_WAIT, 1)
_STOP_KILL = 'def stop(s,f):\n signal.pthread_sigmask(signal.SIG_BLOCK,{2,15})\n raise SystemExit(128+s)\n'


def render_cleanup(*, state=False, wait=False, termination='grace', shared=False):
    """Render one cleanup policy, shared by the legacy and compact producers.

    These are build-time choices. ``state`` uses the path as deletion authority;
    ``wait`` skips a redundant leader grace wait once waitable. Immediate kill
    removes the compiler's graceful signal opportunity, not normal compile wait,
    parent cancellation status, retained identity, group drain or final reap.
    """
    if any(type(value) is not bool for value in (state, wait, shared)):
        raise ValueError('explicit cleanup Boolean choices required')
    if termination not in ('grace', 'kill') or (termination == 'kill' and wait):
        raise ValueError('unknown cleanup policy; wait applies only to grace')
    fail = ('d=None' if state else 'clean=False') + ';raise SystemExit(125)\n'
    initial = 'p=None;' + ('q=15;' if termination == 'grace' else '') + 'd=None' + ('' if state else ';clean=True') + '\n'
    if termination == 'kill':
        leader = '   kill(9)\n   if not wait(5):' + fail
    elif wait:
        leader = ('   if not wait(0):\n    kill(q)\n    if not wait(5):\n'
                  '     kill(9)\n     if not wait(5):' + fail)
    else:
        leader = ('   if not wait(0):kill(q)\n   if not wait(5):\n'
                  '    kill(9)\n    if not wait(5):' + fail)
    drain = ('   kill(9)\n   if not wait(5,1):' + fail) if shared else (
        '   kill(9);t=time.monotonic()+5\n   while live():\n'
        '    if time.monotonic()>t:' + fail + '    kill(9);time.sleep(.01)\n')
    cleanup = ' finally:\n  ' + _MASK + '\n  if p is not None:\n' + leader + drain + '   p.wait()\n'
    directory = 'finally:\n if d is not None' + ('' if state else ' and clean') + ':shutil.rmtree(d)\n'
    return initial, cleanup, directory


def _pin(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def _calls(tree, owner, name):
    return [n for n in ast.walk(tree) if isinstance(n,ast.Call)
            and isinstance(n.func,ast.Attribute) and n.func.attr==name
            and isinstance(n.func.value,ast.Name) and n.func.value.id==owner]


def _call(tree, owner, name):
    calls=_calls(tree,owner,name)
    if len(calls)!=1:raise ValueError('expected one '+owner+'.'+name+' call')
    return calls[0]


def _dump(node):
    return ast.dump(node,include_attributes=False)


def _expression(text):
    return ast.parse(text,mode='eval').body


def transform_bootstrap(script):
    """Repair one admitted stream, ZIP-stdin or restored-files compiler owner.

    This is deliberately not a general Python rewriting API.  Source wrappers
    are accepted by exact reconstruction, not by family name or loose markers.
    Native-only wrappers and the separately qualified Rust stream are not inputs.
    """
    if type(script) is not bytes or b'\r' in script:
        raise ValueError('LF UTF-8 bootstrap bytes required')
    text=script.decode('utf-8');tree=ast.parse(text)
    popen=_call(tree,'subprocess','Popen')
    fdopen=_call(tree,'os','open');execute=_call(tree,'os','execve')
    feeds=_calls(tree,'p','communicate')
    if len(popen.args)!=1 or len(feeds)>1:
        raise ValueError('fixed compiler call differs')
    command=ast.get_source_segment(text,popen.args[0])
    if any(isinstance(n,ast.Name) for n in ast.walk(popen.args[0])):
        raise ValueError('closed compiler command required')
    call=ast.get_source_segment(text,popen)
    open_call=ast.get_source_segment(text,fdopen)
    exec_call=ast.get_source_segment(text,execute)
    registration=next((x for x in _REGISTER if text.count(x)==1),None)
    reset=next((x for x in _RESET if text.count(x)==1),None)
    if registration is None or reset is None:
        raise ValueError('fixed signal handlers differ')
    if exec_call not in ('os.execve(fd,sys.argv[1:],os.environ)',
                         'os.execve(fd,sys.argv,os.environ)'):
        raise ValueError('fixed FD argv execution differs')
    timeout='5' if '   try:p.wait(5)\n' in text else 'timeout=5'
    guard='p is not None' if '  if p is not None and p.poll() is None:\n' in text else 'p'
    cleanup=(' finally:\n  if '+guard+' and p.poll() is None:\n'+
             '   try:os.killpg(p.pid,q)\n   except ProcessLookupError:pass\n'+
             '   try:p.wait('+timeout+')\n'+
             '   except subprocess.TimeoutExpired:os.killpg(p.pid,9);p.wait()\n')
    source=None;restore='';before_fd='';archive=''
    if feeds:
        feed=feeds[0]
        if len(feed.args)!=1 or feed.keywords:
            raise ValueError('fixed compiler stdin differs')
        source=ast.get_source_segment(text,feed.args[0])
        zipped=source=="zipfile.ZipFile(sys.argv[0]).read('c')"
        if not zipped and any(isinstance(n,ast.Name) and n.id!='__ROVE_SOURCE_LITERAL__'
                              for n in ast.walk(feed.args[0])):
            raise ValueError('closed source literal or fixed ZIP source required')
        if [k.arg for k in popen.keywords]!=['cwd','env','stdin','start_new_session','preexec_fn']:
            raise ValueError('fixed compiler stdin options differ')
        env=popen.keywords[1].value
        if _dump(env)==_dump(_expression('e')):
            env_line=next((line for line in (" e=dict(os.environ,TMPDIR=d)\n",
                " e=os.environ.copy();e['TMPDIR']=d\n") if text.count(line)==1),None)
            if env_line is None:raise ValueError('fixed compiler environment differs')
        elif _dump(env)==_dump(_expression('dict(os.environ,TMPDIR=d)')):
            env_line=''
        else:raise ValueError('fixed compiler environment differs')
        if open_call not in ("os.open(d+'/x',0)","os.open(d+'/x',os.O_RDONLY)"):
            raise ValueError('fixed compiler result FD differs')
        imports='import os,signal,subprocess,sys,tempfile'+(',zipfile' if zipped else '')+'\n'
        prefix=imports+'p=None;q=15\n'+_STOP+registration
        expected=(prefix+_DIRECTORY+env_line+
            ' try:\n  m='+_MASK+'\n  try:p='+call+'\n  finally:'+_UNMASK+'\n'+
            '  p.communicate('+source+')\n'+cleanup+
            ' if p.returncode:sys.exit(p.returncode)\n fd='+open_call+'\n'+reset+exec_call+'\n')
        token='stdin=subprocess.PIPE,start_new_session=True'
        if call.count(token)!=1:raise ValueError('fixed pipe shape differs')
        new_call=call.replace(token,'stdin=subprocess.PIPE,bufsize=0,start_new_session=True',1)
        status=' if p.returncode:sys.exit(p.returncode)\n'
        shape='stdin-ZIP' if zipped else 'stdin-stream'
    else:
        if [k.arg for k in popen.keywords]!=['cwd','env','start_new_session','preexec_fn']:
            raise ValueError('fixed restored-files compiler options differ')
        if open_call!='os.open(f,os.O_RDONLY)':
            raise ValueError('fixed restored-files result FD differs')
        update=_call(tree,'e','update')
        if len(update.args)!=1 or update.keywords or not isinstance(ast.literal_eval(update.args[0]),dict):
            raise ValueError('closed environment overrides required')
        env_line=" e=os.environ.copy();e.update("+ast.get_source_segment(text,update.args[0])+");e['TMPDIR']=d\n"
        module=next((name for name in ('zlib','bz2','lzma')
                     if text.startswith('#!/usr/bin/python3\nimport base64,os,signal,struct,subprocess,sys,tempfile,'+name+'\n')),None)
        if module is None:raise ValueError('fixed restored-files imports differ')
        imports='#!/usr/bin/python3\nimport base64,os,signal,struct,subprocess,sys,tempfile,'+module+'\n'
        assignments=[n for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1
                     and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='b']
        if len(assignments)!=1:raise ValueError('fixed archive payload differs')
        archive=ast.get_source_segment(text,assignments[0])+'\n'
        value=assignments[0].value
        blob=value.args[0].args[0] if isinstance(value,ast.Call) and len(value.args)==1 and isinstance(value.args[0],ast.Call) and len(value.args[0].args)==1 else None
        if not isinstance(blob,ast.Constant) or type(blob.value) is not bytes or archive!=('b='+module+'.decompress(base64.b85decode('+repr(blob.value)+'))\n'):
            raise ValueError('fixed archive decoding differs')
        directory=[n for n in tree.body if isinstance(n,ast.With)]
        if len(directory)!=1:raise ValueError('fixed private directory differs')
        fields=directory[0].body
        chmod=[n for n in fields if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
               and _dump(n.value.func)==_dump(_expression('os.chmod'))]
        if len(chmod)!=1:raise ValueError('fixed restored result mode differs')
        at=fields.index(chmod[0])
        if at<1 or not isinstance(fields[at-1],ast.Assign):
            raise ValueError('fixed restored result path differs')
        path_assignment=ast.get_source_segment(text,fields[at-1])
        path_value=fields[at-1].value
        if (not isinstance(path_value,ast.BinOp) or not isinstance(path_value.op,ast.Add)
                or _dump(path_value.left)!=_dump(_expression('d'))
                or not isinstance(path_value.right,ast.Constant)
                or type(path_value.right.value) is not str
                or not path_value.right.value.startswith('/')
                or _dump(chmod[0].value)!=_dump(_expression('os.chmod(f,448)'))):
            raise ValueError('fixed restored result path/mode differs')
        before_fd=' '+path_assignment+';os.chmod(f,448)\n'
        restore=_RESTORE
        prefix=imports+'p=None;q=15\n'+_STOP+registration
        expected=(prefix+archive+_DIRECTORY+restore+env_line+
            ' try:\n  m='+_MASK+'\n  try:p='+call+'\n  finally:'+_UNMASK+'\n'+
            '  r=p.wait()\n'+cleanup+' if r:sys.exit(r)\n'+before_fd+
            ' fd='+open_call+'\n'+reset+exec_call+'\n')
        new_call=call;status=' r=p.returncode\n if r:sys.exit(r)\n';shape='restored-files'
    if expected.encode('utf-8')!=script:
        raise ValueError('bootstrap contains an unrecognized change')
    imports=imports.rstrip('\n')+',shutil,time\n'
    initial,cleanup_owner,directory_owner=render_cleanup()
    data=(imports+initial+_STOP+_GROUP+registration+archive+
        'h=signal.signal(signal.SIGCHLD,signal.SIG_DFL)\nm='+_MASK+'\ntry:\n'+
        " d=tempfile.mkdtemp(prefix='r4-')\n"+restore+env_line+
        ' try:\n  try:p='+new_call+'\n  finally:'+_UNMASK+'\n'+
        (('  try:\n   v=memoryview('+source+')\n   while v:v=v[os.write(p.stdin.fileno(),v):]\n'+
          '  except BrokenPipeError:pass\n  finally:p.stdin.close()\n') if source is not None else '')+
        '  os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT)\n'+cleanup_owner+
        status+before_fd+' fd='+open_call+'\n'+directory_owner+reset+
        'signal.signal(signal.SIGCHLD,h)\n'+_UNMASK+'\n'+exec_call+'\n').encode('utf-8')
    after=ast.parse(data.decode('utf-8'));newp=_call(after,'subprocess','Popen')
    old_fields=[_dump(x) for x in (popen.args[0],*popen.keywords)]
    new_fields=[_dump(x) for x in (newp.args[0],*(k for k in newp.keywords if k.arg!='bufsize'))]
    if old_fields!=new_fields or _dump(fdopen)!=_dump(_call(after,'os','open')) or _dump(execute)!=_dump(_call(after,'os','execve')):
        raise ValueError('protected command/environment/FD expression changed')
    if source is not None:
        views=[n for n in ast.walk(after) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='memoryview']
        if len(views)!=1 or ast.get_source_segment(data.decode('utf-8'),views[0].args[0])!=source:
            raise ValueError('source expression changed')
    return data,{'shape':shape,'input':_pin(script),'output':_pin(data),'raw_delta':len(data)-len(script),
                 'source_expression':_pin(source.encode('utf-8')) if source is not None else None,
                 'command_expression':command,'protected_Popen_fields_equal':True,
                 'protected_source_expression_equal':True,'protected_FD_exec_equal':True,
                 'intentional_Popen_change':'bufsize=0 for os.write stdin loop' if source is not None else None,
                 'compiler_status_policy':'legacy sys.exit(compiler returncode)',
                 'original_wrapper_shape_exact':True}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _prepared_parts(parts, *, state=False, wait=False, termination='grace'):
    """Canonical current W1/shared-wait/seek owner, split at owned regions."""
    initial, cleanup, directory = render_cleanup(state=state, wait=wait,
        termination=termination, shared=True)
    return [
        ('imports', parts['imports']), ('initial', initial),
        ('stop', _STOP if termination == 'grace' else _STOP_KILL),
        ('helpers', _GROUP_SHARED), ('register', parts['register']),
        ('directory_start', 'h=signal.signal(signal.SIGCHLD,signal.SIG_DFL)\nm='+_MASK+
         "\ntry:\n d=tempfile.mkdtemp(prefix='r4-')\n"),
        ('environment', parts['environment']),
        ('source_start', " try:\n  with open(d+'/c','w+b') as f:\n   f.write("),
        ('source', parts['source']),
        ('publication_start', ');f.seek(0)\n   try:p='), ('call', parts['call']),
        ('publication_end', '\n   finally:'+_UNMASK+
         '\n  os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT)\n'),
        ('cleanup', cleanup),
        ('status_fd', ' if p.returncode:sys.exit(p.returncode)\n fd='+parts['open']+'\n'),
        ('directory_cleanup', directory), ('reset', parts['reset']),
        ('execute', 'signal.signal(signal.SIGCHLD,h)\n'+_UNMASK+'\n'+parts['exec']+'\n')]


def _joined(parts):
    return ''.join(value for _,value in parts).encode('utf-8')


def _admit_prepared(script, *, cleanup=None):
    """Recognize the complete current prepared-file owner, not loose markers.

    Scope is the closed C stream/ZIP W1+W2+seek owner. Restored-files and Rust's
    separate environment/status contracts require their own explicit admission.
    The consumer still checks its exact old bootstrap pin before calling us.
    """
    _require(type(script) is bytes and b'\r' not in script, 'LF UTF-8 owner required')
    text=script.decode('utf-8');tree=ast.parse(text)
    popen=_call(tree,'subprocess','Popen');write=_call(tree,'f','write')
    opening=_call(tree,'os','open');execute=_call(tree,'os','execve')
    _require(len(popen.args)==1 and not any(isinstance(n,ast.Name) for n in ast.walk(popen.args[0])),
             'closed compiler argv required')
    _require([k.arg for k in popen.keywords]==['cwd','env','stdin','start_new_session','preexec_fn'],
             'prepared compiler fields differ')
    fixed=('d',None,'f','True','lambda:signal.pthread_sigmask(signal.SIG_SETMASK,m)')
    for keyword,expected in zip(popen.keywords,fixed):
        if expected is not None:
            _require(_dump(keyword.value)==_dump(_expression(expected)), 'prepared compiler field differs')
    environment=''
    if _dump(popen.keywords[1].value)==_dump(_expression('e')):
        environment=next((line for line in (" e=dict(os.environ,TMPDIR=d)\n",
            " e=os.environ.copy();e['TMPDIR']=d\n") if text.count(line)==1),None)
        _require(environment is not None, 'prepared environment differs')
    else:
        _require(_dump(popen.keywords[1].value)==_dump(_expression('dict(os.environ,TMPDIR=d)')),
                 'prepared inline environment differs')
    _require(len(write.args)==1 and not write.keywords, 'one prepared source value required')
    source=ast.get_source_segment(text,write.args[0]);call=ast.get_source_segment(text,popen)
    zipped=source=="zipfile.ZipFile(sys.argv[0]).read('c')"
    if not zipped:
        try:value=ast.literal_eval(write.args[0])
        except (ValueError,TypeError,SyntaxError) as error:raise ValueError('closed source bytes required') from error
        _require(type(value) is bytes, 'closed source bytes required')
    open_call=ast.get_source_segment(text,opening);exec_call=ast.get_source_segment(text,execute)
    _require(open_call in ("os.open(d+'/x',0)","os.open(d+'/x',os.O_RDONLY)"), 'prepared result FD differs')
    _require(exec_call in ('os.execve(fd,sys.argv[1:],os.environ)','os.execve(fd,sys.argv,os.environ)'),
             'prepared FD execution differs')
    registration=next((value for value in _REGISTER if text.count(value)==1),None)
    reset=next((value for value in _RESET if text.count(value)==1),None)
    _require(registration is not None and reset is not None, 'prepared signal pairs differ')
    parts={'imports':'import os,signal,subprocess,sys,tempfile'+(',zipfile' if zipped else '')+',shutil,time\n',
           'environment':environment,'source':source,'call':call,'open':open_call,'exec':exec_call,
           'register':registration,'reset':reset}
    _require(_joined(_prepared_parts(parts,**(cleanup or {})))==script, 'unknown prepared owner scaffold')
    return parts


def _rewrite_parts(before, after, kind, contract):
    _require([tag for tag,_ in before]==[tag for tag,_ in after], 'owner region roles differ')
    old=_joined(before);new=_joined(after);spans=[];gaps=[];a=b=left=right=0
    for (tag,x),(_,y) in zip(before,after):
        x,y=x.encode('utf-8'),y.encode('utf-8')
        if x!=y:
            gap=old[left:a]
            _require(gap==new[right:b], 'protected owner gap differs')
            gaps.append({'old_start':left,'new_start':right,**_pin(gap)})
            spans.append({'role':tag,'old_start':a,'new_start':b,'old':x.decode(),'new':y.decode()})
            left,right=a+len(x),b+len(y)
        a+=len(x);b+=len(y)
    _require(old[left:]==new[right:], 'protected owner suffix differs')
    gaps.append({'old_start':left,'new_start':right,**_pin(old[left:])})
    record={'kind':kind,'input':_pin(old),'output':_pin(new),'raw_delta':len(new)-len(old),
            'spans':spans,'protected_gaps':gaps,'full_inverse':True,
            'opaque_source_spelling_equal':True,'all_protected_gaps_equal':True,
            'contract':contract,'runtime_qualified':False}
    _require(restore_bootstrap(new,record)==old, 'complete owner inverse differs')
    return new,record


def restore_bootstrap(candidate, metadata):
    """Restore one compact/normalized prepared owner, including identity."""
    _require(type(candidate) is bytes and metadata.get('kind') in
             ('compact-cleanup','normalized-prepared-template','private-owner-spelling') and _pin(candidate)==metadata.get('output'),
             'owner candidate pin differs')
    result=candidate
    for span in reversed(metadata['spans']):
        at=span['new_start'];old,new=span['old'].encode('utf-8'),span['new'].encode('utf-8')
        _require(result[at:at+len(new)]==new, 'owner inverse span differs')
        result=result[:at]+old+result[at+len(new):]
    _require(_pin(result)==metadata.get('input'), 'owner inverse input differs')
    return result


def _owners(tree):
    outer=[node for node in tree.body if isinstance(node,ast.Try)]
    _require(len(outer)==1, 'one directory owner required')
    inner=[node for node in outer[0].body if isinstance(node,ast.Try)]
    _require(len(inner)==1, 'one compiler owner required')
    return outer[0],inner[0]


def _compact_view(raw, *, state, wait, termination):
    tree=ast.parse(raw);kill=termination=='kill'
    hidden={'clean'} if state else set()
    if kill:hidden.add('q')
    tree.body=[node for node in tree.body if not (isinstance(node,ast.Assign) and len(node.targets)==1
        and isinstance(node.targets[0],ast.Name) and node.targets[0].id in hidden)]
    outer,inner=_owners(tree)
    if state or wait or kill:inner.finalbody=[ast.Expr(value=ast.Name(id='__COMPILER_CLEANUP__',ctx=ast.Load()))]
    if state:outer.finalbody=[ast.Expr(value=ast.Name(id='__DIRECTORY_CLEANUP__',ctx=ast.Load()))]
    if kill:
        stop=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='stop']
        _require(len(stop)==1, 'one cancellation handler required');stop[0].body=[ast.Pass()]
    return _dump(tree)


def compact_cleanup(script, *, state=True, wait=False, termination='grace'):
    """Select a cleanup policy after the caller's exact old owner guards.

    Grace preserves the original signal/grace contract. Kill deliberately removes
    compiler graceful handling while preserving parent128+s, signal masking,
    separate post-KILL/group budgets, unreaped leader and 125 workspace policy.
    Unknown scaffolds and wait=True with kill are rejected. No engine policy or
    runtime selector is added. An output is not a fresh input to this API.
    """
    parts=_admit_prepared(script)
    before=_prepared_parts(parts)
    after=_prepared_parts(parts,state=state,wait=wait,termination=termination)
    data,record=_rewrite_parts(before,after,'compact-cleanup',{
        'state_authority':'path' if state else 'flag','skip_waitable_leader_grace_wait':wait,
        'termination':termination,'normal_compile_wait':'unbounded WNOWAIT',
        'compiler_grace':termination=='grace','post_KILL_leader_seconds':5,'live_group_seconds':5,
        'retained_leader_and_last_reap':True,'workspace_preserved_on_settlement125':True,
        'parent_cancel_status':'SystemExit128+s','mask_SIGCHLD_and_final_FD_exec_preserved':True,
        'observation_exclusions':['Python private cleanup variable snapshots','exact traceback locations',
            *(['compiler INT/TERM handler logs and cleanup opportunity'] if termination=='kill' else [])]})
    _require(_compact_view(script,state=state,wait=wait,termination=termination)==
             _compact_view(data,state=state,wait=wait,termination=termination),
             'AST outside declared cleanup regions differs')
    record['outside_owned_AST_equal']=True
    record['source_expression']=_pin(parts['source'].encode('utf-8'))
    return data,record


def compact_private_owner(script, *, wait=False, termination='grace'):
    """Shorten private truth consumers and helper names in the selected C owner.

    This optional terminal stage admits only the complete state=True prepared
    owner. The engine source, compiler fields, masks, deadlines, signal
    order, retained leader, final reap and 125 preservation are untouched. Return
    0/1 is consumed only by the closed wait/live conditions. Builtin Popen is
    truthy and mkdtemp returns a nonempty path, or these owners remain None.
    Linux procfs PID entries use ASCII decimal names; isdigit is scoped to that
    fixed enumeration. Private helper names, value types, namespace snapshots,
    exact exception traces and exotic procfs substitutions are not preserved.
    This is not a general Python optimizer or an input to compact_cleanup.
    """
    _require(type(wait) is bool and termination in ('grace','kill') and not (wait and termination=='kill'),
             'explicit private owner wait/termination required')
    parts=_admit_prepared(script,cleanup={'state':True,'wait':wait,'termination':termination})
    before=_prepared_parts(parts,state=True,wait=wait,termination=termination)
    after=[]
    for role,value in before:
        if role=='helpers':
            value=(value.replace('return False','return 0').replace('return True','return 1')
                .replace('n.isdecimal()','n.isdigit()').replace('kill(','k(')
                .replace('def wait(','def w(').replace('live(','l('))
        elif role=='cleanup':
            value=value.replace('if p is not None:','if p:').replace('kill(','k(').replace('not wait(','not w(')
        elif role=='directory_cleanup':
            value=value.replace('if d is not None:','if d:')
        after.append((role,value))
    data,record=_rewrite_parts(before,after,'private-owner-spelling',{
        'termination':termination,'skip_waitable_leader_grace_wait':wait,
        'scope':'closed selected C prepared owner; state=True',
        'truth_contexts':'wait/live results become 0/1; builtin Popen and nonempty mkdtemp path guards',
        'pid_names':'ASCII decimal PID entries of Linux /proc; no arbitrary directory input',
        'helper_names':{'kill':'k','wait':'w','live':'l'},
        'retained_leader_and_last_reap':True,'workspace_preserved_on_settlement125':True,
        'signals_masks_deadlines_and_FD_exec_unchanged':True,
        'observation_exclusions':['private helper names and control value types','private namespace snapshots',
            'exact exception traces','substituted or exotic non-Linux procfs']})
    for raw in (script,data):
        tree=ast.parse(raw);outer,inner=_owners(tree)
        inner.finalbody=[ast.Pass()];outer.finalbody=[ast.Pass()]
        tree.body=[node for node in tree.body if not (isinstance(node,ast.FunctionDef) and
            node.name in ('kill','wait','live','k','w','l'))]
        if raw==script:original=_dump(tree)
        else:_require(original==_dump(tree), 'AST outside private owner regions differs')
    record.update(outside_owned_AST_equal=True,source_expression=_pin(parts['source'].encode('utf-8')))
    return data,record


def _replace_environment(call):
    tree=ast.parse(call,mode='eval');keyword=tree.body.keywords[1]
    _require(keyword.arg=='env' and _dump(keyword.value)==_dump(_expression('e')), 'single-use environment differs')
    lines=call.encode('utf-8').splitlines(keepends=True);starts=[0]
    for line in lines:starts.append(starts[-1]+len(line))
    node=keyword.value;a=starts[node.lineno-1]+node.col_offset;b=starts[node.end_lineno-1]+node.end_col_offset
    raw=call.encode('utf-8');_require(raw[a:b]==b'e', 'environment byte span differs')
    return (raw[:a]+b'dict(os.environ,TMPDIR=d)'+raw[b:]).decode('utf-8')


def _normalize_view(raw, parts):
    tree=ast.parse(raw);outer,_=_owners(tree)
    outer.body=[node for node in outer.body if not (isinstance(node,ast.Assign) and len(node.targets)==1
        and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='e')]
    _call(tree,'subprocess','Popen').keywords[1].value=ast.Constant(value='__ENVIRONMENT__')
    for role,code in (('REGISTER',parts['register']),('RESET',parts['reset'])):
        target=ast.parse(code).body;matches=[]
        for i in range(len(tree.body)-len(target)+1):
            if [_dump(n) for n in tree.body[i:i+len(target)]]==[_dump(n) for n in target]:matches.append(i)
        _require(len(matches)==1, 'one signal pair required')
        i=matches[0];tree.body[i:i+len(target)]=[ast.Expr(value=ast.Name(id='__'+role+'__',ctx=ast.Load()))]
    return _dump(tree)


def normalize_bootstrap(script):
    """Inline the single-use environment and loop signal pairs, or identity.

    The environment snapshot moves after source write/seek into Popen argument
    evaluation. Allocation/audit-hook/failure trace ordering can differ; this is
    not general Python trace equivalence. Private e disappears, loop s remains15.
    """
    parts=_admit_prepared(script);selected=dict(parts)
    if parts['environment']:
        selected['environment']='';selected['call']=_replace_environment(parts['call'])
    selected['register']=_REGISTER[1];selected['reset']=_RESET[1]
    data,record=_rewrite_parts(_prepared_parts(parts),_prepared_parts(selected),
        'normalized-prepared-template',{
            'environment':'same values under closed builtin preparation contract; snapshot moves to Popen args',
            'signals':'same2,15 registration/reset order and points','private_names':'e omitted; loop s remains15',
            'exclusions':['concurrent/custom environment mutation','audit-hook/allocation first-error ordering',
                          'private Python namespace and exact tracebacks']})
    _require(_normalize_view(script,parts)==_normalize_view(data,selected),
             'AST outside declared environment/signal normalization differs')
    _require(_admit_prepared(data)==selected, 'normalized owner replay differs')
    record.update(identity=data==script,outside_owned_AST_equal=True,
                  source_expression=_pin(parts['source'].encode('utf-8')))
    return data,record
