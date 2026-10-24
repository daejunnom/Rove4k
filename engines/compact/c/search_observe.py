"""Remove private diagnostic writes from compiler-specialized shipping C only.

These counters have no shipping reader. Worker/session node accounting, policy
costs and every abort/stop operation are outside this transform's allowlist.
Unknown uses fail closed; this is not a general dead-store or atomic optimizer.
"""
import hashlib
import re


COUNTERS = frozenset((
    'rove_simd_calls', 'rove_model_calls', 'rove_see_calls',
    'rove_singular_calls', 'rove_mtd_probes', 'rove_mtd_conflicts',
    'rove_mtd_converged',
))
_NAMES = '|'.join(sorted(COUNTERS))
_REFERENCE = re.compile(r'\b(?:' + _NAMES + r')\b')
_INCREMENT = re.compile(
    r'\batomic_fetch_add_explicit\s*\(\s*&\s*(?P<name>' + _NAMES +
    r')\s*,\s*1\s*,\s*memory_order_relaxed\s*\)\s*;')
_DECLARATION = re.compile(
    r'\b(?:extern\s+)?_Atomic\s+uint64_t\s+'
    r'(?P<names>[A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*;')


def _code(text):
    # Retain offsets, newlines and preprocessor identifiers. References hidden
    # in an unfamiliar macro must still cause rejection after the known edits.
    pattern = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|'
                         r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
    return pattern.sub(lambda m: ''.join('\n' if c == '\n' else ' '
                                        for c in m.group()), text)


def _contexts(code):
    # Delimiters in directives are not C expression/function scopes. Keep the
    # separate unmasked code for the final unknown-reference check.
    code = re.sub(r'(?m)^[ \t]*\#[^\n]*(?:\\\n[^\n]*)*',
                  lambda m: ' ' * len(m.group()), code)
    braces = parens = brackets = 0
    result = []
    for char in code:
        result.append((braces, parens, brackets))
        if char == '{': braces += 1
        if char == '}': braces -= 1
        if char == '(': parens += 1
        if char == ')': parens -= 1
        if char == '[': brackets += 1
        if char == ']': brackets -= 1
        if min(braces, parens, brackets) < 0:
            raise ValueError('unbalanced specialized C delimiters')
    if braces or parens or brackets:
        raise ValueError('unbalanced specialized C delimiters')
    return result


def strip_shipping_diagnostics(files, *, development):
    """Return copied files and observations, or reject an unknown counter use.

    Input is the actual compiler-specialized owned C, before or after lexical
    compaction. Development callers must retain diagnostics and are rejected.
    Only bare, complete atomic +1 relaxed expression statements and global
    declarations containing exclusively the seven known names are removable.
    """
    if development:
        raise ValueError('diagnostic removal requires shipping development=False')
    result, observations = dict(files), []
    for filename, data in files.items():
        if not filename.endswith('.c'):
            continue
        text = data.decode()
        code = _code(text)
        contexts = _contexts(code)
        edits, increments, declarations = [], {}, {}
        for match in _INCREMENT.finditer(code):
            prefix = code[:match.start()].rstrip()
            braces, parens, brackets = contexts[match.start()]
            if not braces or parens or brackets or not prefix or prefix[-1] not in '{;}':
                raise ValueError(f'{filename}: diagnostic increment is not a supported standalone statement')
            name = match.group('name')
            increments[name] = increments.get(name, 0) + 1
            edits.append((match.start(), match.end()))
        for match in _DECLARATION.finditer(code):
            names = re.findall(r'[A-Za-z_]\w*', match.group('names'))
            prefix = code[:match.start()].rstrip()
            if set(names) <= COUNTERS and contexts[match.start()] == (0, 0, 0) and (
                    not prefix or prefix[-1] in ';}'):
                for name in names:
                    declarations[name] = declarations.get(name, 0) + 1
                edits.append((match.start(), match.end()))
        for begin, end in sorted(edits, reverse=True):
            text = text[:begin] + text[end:]
        remaining = sorted(set(_REFERENCE.findall(_code(text))))
        if remaining:
            raise ValueError(f'{filename}: unsupported live diagnostic references: {", ".join(remaining)}')
        output = text.encode()
        result[filename] = output
        if edits:
            observations.append({
                'applied': True, 'operation': 'shipping-unobserved-diagnostic-counters',
                'file': filename, 'increments_removed': increments,
                'declarations_removed': declarations,
                'bytes_before': len(data), 'bytes_after': len(output),
                'sha256_before': hashlib.sha256(data).hexdigest(),
                'sha256_after': hashlib.sha256(output).hexdigest(),
                'contract': 'no shipping counter readers; only known standalone relaxed +1 writes and bare global declarations removed; abort and node/policy accounting retained',
            })
    if not observations:
        observations.append({'applied': False,
                             'operation': 'shipping-unobserved-diagnostic-counters',
                             'reason': 'no diagnostic writes or declarations present'})
    return result, observations
