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
    data=(imports+'p=None;q=15;d=None;clean=True\n'+_STOP+_GROUP+registration+archive+
        'h=signal.signal(signal.SIGCHLD,signal.SIG_DFL)\nm='+_MASK+'\ntry:\n'+
        " d=tempfile.mkdtemp(prefix='r4-')\n"+restore+env_line+
        ' try:\n  try:p='+new_call+'\n  finally:'+_UNMASK+'\n'+
        (('  try:\n   v=memoryview('+source+')\n   while v:v=v[os.write(p.stdin.fileno(),v):]\n'+
          '  except BrokenPipeError:pass\n  finally:p.stdin.close()\n') if source is not None else '')+
        '  os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOWAIT)\n finally:\n  '+_MASK+'\n'+
        '  if p is not None:\n   if not wait(0):kill(q)\n   if not wait(5):\n    kill(9)\n'+
        '    if not wait(5):clean=False;raise SystemExit(125)\n'+
        '   kill(9);t=time.monotonic()+5\n   while live():\n'+
        '    if time.monotonic()>t:clean=False;raise SystemExit(125)\n'+
        '    kill(9);time.sleep(.01)\n   p.wait()\n'+status+before_fd+' fd='+open_call+'\n'+
        'finally:\n if d is not None and clean:shutil.rmtree(d)\n'+reset+
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
