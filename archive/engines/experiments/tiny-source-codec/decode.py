"""Strict, nonexecuting package input recovery for explicit XZ or LZMA ALONE.

The caller freezes the complete expected bootstrap, source, compiler argv, and
75- or 77-byte prefix. Format is selected explicitly; no format is autodetected.
Encoder filters/preset/match finder/nice length are the producer's fixed inputs,
not inferred here. No module from another experiment is imported.

XZ must carry CRC64. ALONE has no container checksum: its different corruption
contract is complete bounded decoding plus exact expected-bootstrap equality and
exact recovered compiler-stdin equality. These data checks do not create a CRC,
execute Python/C, or establish native/ABI/runtime/release qualification.
"""
import ast
import hashlib
import lzma


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _named_call(node, receiver, method):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == receiver and node.func.attr == method)


def _literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as error:
        raise ValueError('bootstrap argument is not an admitted literal') from error


def _stdin_bytes(node):
    if isinstance(node, ast.Call):
        _require(isinstance(node.func, ast.Attribute) and node.func.attr == 'encode'
                 and not node.args and not node.keywords,
                 'only argument-free literal str.encode() is allowed')
        value = _literal(node.func.value)
        _require(type(value) is str, 'encode receiver must be a literal str')
        try:
            return value.encode(), 'literal_str.encode_default_utf8'
        except UnicodeEncodeError as error:
            raise ValueError('literal str cannot encode as default UTF-8') from error
    value = _literal(node)
    _require(type(value) is bytes, 'stdin must be literal bytes or literal str.encode()')
    return value, 'literal_bytes'


def _argv_literal(node):
    if isinstance(node, ast.Call):
        _require(isinstance(node.func, ast.Attribute) and node.func.attr == 'split'
                 and not node.args and not node.keywords,
                 'only argument-free literal str.split() argv is allowed')
        value = _literal(node.func.value)
        _require(type(value) is str, 'split receiver must be a literal str')
        return value.split(), 'literal_str.split_default_whitespace'
    value = _literal(node)
    _require(type(value) is list and all(type(arg) is str for arg in value),
             'compiler argv must be a literal list of strings or literal str.split()')
    return value, 'literal_list'


def verify(whole, prefix, source, compiler, expected_script, *, expected_format):
    """Return a JSON-safe receipt or reject with ValueError.

    `expected_format` is exactly 'xz' or 'alone'. A recipe must bind that choice
    and the supplied exact prefix; both admitted prefix lengths are explicit.
    Remaining Python statements/bindings are controlled by exact script bytes,
    rather than by a general Python safety or name-resolution analysis.
    """
    _require(type(expected_format) is str and expected_format in ('xz', 'alone'),
             'explicit expected format must be xz or alone')
    _require(all(type(value) is bytes for value in (whole, prefix, source, expected_script)),
             'immutable package/prefix/source/bootstrap bytes required')
    _require(type(compiler) is list and compiler and all(type(arg) is str for arg in compiler),
             'exact compiler argv list of strings required')
    _require(len(prefix) in (75, 77) and whole[:len(prefix)] == prefix,
             'exact caller-supplied 75- or 77-byte prefix required')
    payload = whole[len(prefix):]
    format_id = lzma.FORMAT_XZ if expected_format == 'xz' else lzma.FORMAT_ALONE
    try:
        decoder = lzma.LZMADecompressor(format=format_id)
        decoded = decoder.decompress(payload, max_length=len(expected_script) + 1)
    except (lzma.LZMAError, EOFError) as error:
        raise ValueError('invalid payload for explicitly expected format') from error
    _require(decoded == expected_script, 'decoded bootstrap differs from exact expected bytes')
    _require(decoder.eof and not decoder.unused_data, 'one complete stream with no unused bytes required')
    if expected_format == 'xz':
        _require(decoder.check == lzma.CHECK_CRC64, 'XZ requires a CRC64 container check')
        checksum = 'CRC64'
        corruption_contract = 'XZ CRC64 plus exact decoded bootstrap and recovered compiler stdin'
    else:
        _require(decoder.check == lzma.CHECK_NONE, 'ALONE has no container checksum')
        checksum = 'none'
        corruption_contract = ('ALONE has no container checksum; complete decoding and exact expected '
                               'bootstrap/source bindings are required, without CRC protection')
    try:
        tree = ast.parse(decoded)
    except (SyntaxError, ValueError, UnicodeError, MemoryError, RecursionError) as error:
        raise ValueError('invalid bootstrap Python syntax') from error
    popens = [node for node in ast.walk(tree) if _named_call(node, 'subprocess', 'Popen')]
    _require(len(popens) == 1, 'one literal subprocess.Popen call required')
    popen = popens[0]
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and node.value is popen and len(node.targets) == 1
                   and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'p']
    _require(len(assignments) == 1, 'Popen must assign directly to the sole Name p')
    _require(len(popen.args) == 1, 'Popen requires one positional literal argv argument')
    argv, argv_kind = _argv_literal(popen.args[0])
    _require(type(argv) is list and all(type(arg) is str for arg in argv) and argv == compiler,
             'literal Popen argv differs from exact compiler argv')
    communicates = [node for node in ast.walk(tree) if _named_call(node, 'p', 'communicate')]
    _require(len(communicates) == 1, 'one p.communicate call required')
    communicate = communicates[0]
    _require(len(communicate.args) == 1 and not communicate.keywords,
             'communicate requires one positional source argument and no keywords')
    restored, literal_kind = _stdin_bytes(communicate.args[0])
    _require(restored == source, 'recovered compiler stdin differs from exact source bytes')
    return {
        'complete': True, 'scope': 'bounded package decode and restricted AST literal input recovery',
        'whole': {'bytes': len(whole), 'sha256': _sha(whole)},
        'prefix': {'bytes': len(prefix), 'sha256': _sha(prefix), 'exact': True},
        'stream': {'bytes': len(payload), 'sha256': _sha(payload),
                   'expected_format': expected_format, 'format_id': format_id,
                   'format_autodetected': False, 'stream_count': 1,
                   'check': checksum, 'check_id': decoder.check,
                   'container_checksum_available': expected_format == 'xz',
                   'CRC64_required': expected_format == 'xz',
                   'eof': decoder.eof, 'unused_bytes': len(decoder.unused_data),
                   'corruption_contract': corruption_contract},
        'bootstrap': {'bytes': len(decoded), 'sha256': _sha(decoded),
                      'expected_sha256': _sha(expected_script), 'exact_expected_bytes': True},
        'compiler': list(argv),
        'Popen': {'count': 1, 'line': popen.lineno, 'assignment_name': 'p',
                  'assignment_line': assignments[0].lineno, 'argv_literal_kind': argv_kind},
        'communicate': {'count': 1, 'line': communicate.lineno, 'arguments': 1,
                        'keywords': 0, 'literal_kind': literal_kind},
        'source': {'bytes': len(restored), 'sha256': _sha(restored), 'exact': True},
        'encoder_settings_inferred': False, 'caller_must_pin_recipe_inputs': True,
        'bootstrap_executed': False, 'native_executed': False,
        'compiler_runs': 0, 'engine_runs': 0, 'codec_compressions': 0,
        'native_or_runtime_qualification': False,
    }
