"""Read a complete fixed-prefix package without executing its bootstrap or ELF.

The caller binds prefix, compiler, source, and expected bootstrap bytes to its
frozen ordinary recipe. This decoder checks one CRC64 XZ stream and the exact
bootstrap/input representation; it does not infer encoder preset/filter options
or establish native, ABI, runtime, strength, or release qualification.
"""
import ast
import hashlib
import lzma


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _call(node, receiver, method):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == receiver and node.func.attr == method)


def _literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as error:
        raise ValueError('nonliteral bootstrap argument') from error


def _stdin_literal(node):
    if isinstance(node, ast.Call):
        _check(isinstance(node.func, ast.Attribute) and node.func.attr == 'encode'
               and not node.args and not node.keywords,
               'only argument-free literal str.encode() is allowed')
        value = _literal(node.func.value)
        _check(type(value) is str, 'encode receiver must be a literal str')
        try:
            return value.encode(), 'literal_str.encode_default_utf8'
        except UnicodeEncodeError as error:
            raise ValueError('literal str is not encodable as default UTF-8') from error
    value = _literal(node)
    _check(type(value) is bytes, 'stdin argument must be literal bytes or literal str.encode()')
    return value, 'literal_bytes'


def verify(whole, prefix, source, compiler, expected_script):
    """Return a JSON-safe byte/AST receipt or reject the package with ValueError.

    `ast.literal_eval` is used only for literal argv/source values. No generated
    statement, expression, bootstrap, subprocess, compiler, or ELF is executed.
    """
    _check(all(type(value) is bytes for value in (whole, prefix, source, expected_script)),
           'immutable whole/prefix/source/bootstrap bytes required')
    _check(type(compiler) is list and compiler and all(type(arg) is str for arg in compiler),
           'literal compiler argv list of strings required')
    _check(len(prefix) == 75 and whole[:75] == prefix, 'exact 75-byte prefix required')
    payload = whole[75:]
    try:
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        decoded = decoder.decompress(payload, max_length=len(expected_script) + 1)
    except (lzma.LZMAError, EOFError) as error:
        raise ValueError('invalid XZ package payload') from error
    _check(decoded == expected_script, 'decoded bootstrap differs from exact expected bytes')
    _check(decoder.eof and not decoder.unused_data, 'exactly one complete XZ stream required')
    _check(decoder.check == lzma.CHECK_CRC64, 'XZ stream must use CRC64')
    try:
        tree = ast.parse(decoded)
    except (SyntaxError, ValueError, UnicodeError, MemoryError, RecursionError) as error:
        raise ValueError('invalid bootstrap Python syntax') from error
    popen_calls = [node for node in ast.walk(tree) if _call(node, 'subprocess', 'Popen')]
    _check(len(popen_calls) == 1, 'unique literal subprocess.Popen call required')
    popen = popen_calls[0]
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and node.value is popen and len(node.targets) == 1
                   and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'p']
    _check(len(assignments) == 1, 'Popen must be assigned directly to the sole Name p')
    _check(len(popen.args) == 1, 'Popen must have one literal positional argv argument')
    argv = _literal(popen.args[0])
    _check(type(argv) is list and all(type(arg) is str for arg in argv) and argv == compiler,
           'Popen literal argv differs from exact compiler argv')
    communicates = [node for node in ast.walk(tree) if _call(node, 'p', 'communicate')]
    _check(len(communicates) == 1, 'unique p.communicate call required')
    communicate = communicates[0]
    _check(len(communicate.args) == 1 and not communicate.keywords,
           'p.communicate requires one positional source argument and no keywords')
    restored, literal_kind = _stdin_literal(communicate.args[0])
    _check(restored == source, 'literal compiler stdin differs from exact source bytes')
    return {
        'complete': True, 'scope': 'pure package-byte decoding and restricted AST input recovery',
        'whole': {'bytes': len(whole), 'sha256': _sha(whole)},
        'prefix': {'bytes': 75, 'sha256': _sha(prefix), 'exact': True},
        'xz': {'bytes': len(payload), 'sha256': _sha(payload), 'format': 'XZ',
               'check': 'CRC64', 'check_id': decoder.check, 'stream_count': 1,
               'eof': decoder.eof, 'unused_bytes': len(decoder.unused_data)},
        'bootstrap': {'bytes': len(decoded), 'sha256': _sha(decoded),
                      'expected_sha256': _sha(expected_script), 'exact_expected_bytes': True},
        'compiler': list(argv),
        'Popen': {'count': 1, 'line': popen.lineno, 'assignment_name': 'p',
                  'assignment_line': assignments[0].lineno},
        'communicate': {'count': 1, 'line': communicate.lineno, 'arguments': 1,
                        'keywords': 0, 'literal_kind': literal_kind},
        'source': {'bytes': len(restored), 'sha256': _sha(restored), 'exact': True},
        'encoder_settings_inferred': False, 'caller_must_pin_recipe_inputs': True,
        'bootstrap_executed': False, 'native_executed': False,
        'compiler_runs': 0, 'engine_runs': 0, 'codec_compressions': 0,
        'native_or_runtime_qualification': False,
    }
