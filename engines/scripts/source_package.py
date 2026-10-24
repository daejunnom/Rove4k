"""Fixed-recipe source packages; no search or bootstrap rewriting.

The caller owns the exact bootstrap, prefix and compression decisions. The
three-line header reads its stream from stdin, so xz writes decoded Python to
stdout. Its failure exit, Python argv and exec behavior match the byte-offset
launcher; source/native/lifetime qualification remains the caller's concern.
"""
import lzma
import shlex


XZ_STDIN_HEADER = (b'#!/bin/sh\np=$(tail -n+4 "$0"|xz -d)||exit\n'
                   b'exec python3 -c "$p" "$0" "$@"\n')


def package(bootstrap, compression, *, prefix):
    """Encode one LZMA1 ALONE stream with the caller's complete prefix."""
    if not isinstance(bootstrap, bytes) or not isinstance(prefix, bytes):
        raise TypeError('immutable bootstrap and prefix bytes required')
    if (compression['format'], compression['filter'], compression['check']) != ('lzma-alone', 'LZMA1', 'NONE'):
        raise ValueError('source package requires the explicit LZMA1 ALONE recipe')
    preset = compression['preset'] | (lzma.PRESET_EXTREME if compression['extreme'] else 0)
    match_finder = {'BT4': lzma.MF_BT4, 'BT2': lzma.MF_BT2, 'HC4': lzma.MF_HC4}[compression['mf']]
    filters = [{'id': lzma.FILTER_LZMA1, 'preset': preset,
                'lc': compression['lc'], 'lp': compression['lp'], 'pb': compression['pb'],
                'mf': match_finder, 'dict_size': compression['dictionary_bytes'],
                'nice_len': compression['nice_len']}]
    return prefix + lzma.compress(bootstrap, format=lzma.FORMAT_ALONE,
                                  check=lzma.CHECK_NONE, filters=filters)


SHELL_COMPILER = ('cc', '-Os', '-pthread', '-x', 'c', '-', '-o', 'x', '-s')


def shell_header(*, kind, compiler=None, child_reaping='inherit'):
    """Build a separate delayed-cleanup shell policy, not the compiler owner.

    The source form checks extraction before compiling stdin in the private
    directory. The native form restores a complete executable ELF. Both retain
    the caller's cwd/environment for the engine and pass its original arguments,
    but argv0 and /proc/self/exe name the temporary executable. A separate child
    removes the private directory after one second. This changes cancellation,
    compiler status, file and child observations from the ordinary Python owner.
    The caller owns a known compiler recipe and a target with unset/absolute
    TMPDIR; arbitrary compiler option meanings or relative TMPDIR normalization
    are not admitted as equivalent to Python's temporary-directory contract.

    ``ignore-after-compile`` explicitly uses /bin/bash and ignores SIGCHLD only
    after the source compiler has finished and before creating the cleanup
    child. Dash resets this special disposition before exec, so /bin/sh is not
    a fallback for that policy. It is for an
    explicitly selected engine that does not fork/wait for process children;
    pthread workers are independent. ``inherit`` leaves SIGCHLD untouched and
    can leave a terminated cleanup child for the engine to reap. Neither policy
    inherits the ordinary owner's grace/group-settlement guarantees.
    """
    if kind not in ('source', 'native'):
        raise ValueError('an explicit source or complete native ELF policy is required')
    if child_reaping not in ('inherit', 'ignore-after-compile'):
        raise ValueError('unknown shell child-reaping policy')
    if kind == 'source':
        command = SHELL_COMPILER if compiler is None else tuple(compiler)
        if (not command or any(type(arg) is not str or not arg or
                               any(c in arg for c in '\x00\r\n') for arg in command)
                or command.count('-o') != 1 or command[command.index('-o') + 1:] == ()
                or command[command.index('-o') + 1] != 'x' or command.count('-') != 1):
            raise ValueError('closed compiler argv with stdin and private output x required')
    elif compiler is not None:
        raise ValueError('the native policy has no compiler')
    lines = [
        '#!/bin/bash' if child_reaping == 'ignore-after-compile' else '#!/bin/sh',
        'd=$(mktemp -d)||exit',
        "c(){ python3 -c 'import os,shutil,sys;p=sys.argv[1];os.path.lexists(p) and shutil.rmtree(p)' \"$d\"; }",
        'trap c 0',
        'tail -n+{line} "$0">"$d/p"||exit',
        'xz -d<"$d/p">"$d/' + ('c' if kind == 'source' else 'x') + '"||exit',
    ]
    if kind == 'source':
        lines.append('(cd "$d"&&TMPDIR="$d" ' + shlex.join(command) + ' <c)||exit')
    else:
        lines.append('chmod +x "$d/x"||exit')
    launch = '(trap - 0;sleep 1;c)&exec "$d/x" "$@";exit'
    if child_reaping == 'ignore-after-compile':
        launch = "trap '' CHLD;" + launch
    lines.append(launch)
    lines[4] = lines[4].format(line=len(lines) + 1)
    return ('\n'.join(lines) + '\n').encode('utf-8')


def package_shell(payload, compression, *, kind, compiler=None,
                  child_reaping='inherit', elf_admission=None):
    """Package one explicit shell policy while keeping package() unchanged.

    Native admission is supplied by the caller's frozen trusted ELF validator,
    which must raise on rejection;
    a zero-header ownELF restoration image or an arbitrary script is not an ELF
    input. The codec and all final bytes still belong to the caller's recipe.
    This pure producer does not claim runtime or tournament qualification.
    """
    if type(payload) is not bytes or not payload:
        raise TypeError('nonempty immutable payload bytes required')
    if kind == 'native':
        if not callable(elf_admission):
            raise ValueError('a trusted complete-ELF admission callback is required')
        elf_admission(payload)
    elif elf_admission is not None:
        raise ValueError('ELF admission is only used by the native policy')
    return package(payload, compression, prefix=shell_header(kind=kind,
        compiler=compiler, child_reaping=child_reaping))
