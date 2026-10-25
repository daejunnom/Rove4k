"""Independent C declaration-bound automatic-name reuse; no native compilation.

One conservative policy: aliases are unique across an entire function, and the
allocator restarts for the next function.  Only physical main-file automatic
VarDecl and real function parameters are candidates.  The implementation does
not contain or import ice4 code.
"""
import hashlib
import importlib
import itertools
import json
from pathlib import Path
import re
import string
import sys


class Rejected(ValueError):
    pass


KEYWORDS = frozenset('''auto break case char const continue default do double else
enum extern float for goto if inline int long register restrict return short
signed sizeof static struct switch typedef union unsigned void volatile while
_Alignas _Alignof _Atomic _Bool _Complex _Generic _Imaginary _Noreturn
_Static_assert _Thread_local asm typeof __asm __asm__ __typeof __typeof__'''.split())
SOURCE = 'scope-input.c'
WORD = re.compile(r'[A-Za-z_][A-Za-z_0-9]*\Z')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def clang_api(site):
    site = Path(site).resolve()
    library = site / 'clang/native/libclang.so'
    if not library.is_file() or not (site / 'clang/cindex.py').is_file():
        raise Rejected('explicit external libclang installation is incomplete')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(site))
    ci = importlib.import_module('clang.cindex')
    if ci.Config.loaded:
        if Path(ci.Config.library_file).resolve() != library:
            raise Rejected('another libclang library was already loaded')
    else:
        ci.Config.set_library_file(str(library))
    return ci


def main_location(location):
    return location.file is not None and location.file.name == SOURCE


def key(cursor):
    cursor = cursor.canonical
    loc = cursor.location
    return cursor.kind.name, loc.file.name if loc.file else '', loc.offset


def aliases():
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    for length in itertools.count(1):
        for parts in itertools.product(alphabet, repeat=length):
            yield ''.join(parts)


def parse(ci, source, resource_dir, arguments):
    resource_dir = Path(resource_dir).resolve()
    if not (resource_dir / 'include/stdatomic.h').is_file():
        raise Rejected('real Clang resource headers are required')
    args = ['-x', 'c', '-resource-dir', str(resource_dir), *arguments]
    tu = ci.Index.create().parse(
        SOURCE, args=args, unsaved_files=[(SOURCE, source)],
        options=ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    diagnostics = [{'severity': d.severity, 'message': d.spelling,
                    'location': str(d.location)} for d in tu.diagnostics]
    if any(d['severity'] >= ci.Diagnostic.Error for d in diagnostics):
        raise Rejected('AST diagnostics contain errors: ' + json.dumps(diagnostics))
    return tu, args, diagnostics


def intersect(start, end, intervals):
    return any(start < b and a < end for a, b in intervals)


def snapshot(ci, tu):
    """Names, declaration shapes and source-ordered referenced-declaration edges.

    Main-file declaration ordinals survive identifier length changes.  Header
    declarations keep their canonical USR and spelling.  No same-spelling scope
    lookup is used to reconstruct a binding.
    """
    cursors = list(tu.cursor.walk_preorder())
    declarations = []
    ids = {}
    for cursor in cursors:
        if main_location(cursor.location) and (cursor.kind.is_declaration() or
                cursor.kind == ci.CursorKind.MACRO_DEFINITION):
            ident = key(cursor)
            if ident not in ids:
                ids[ident] = len(declarations)
                declarations.append(cursor)
    shapes = []
    for cursor in declarations:
        if cursor.kind == ci.CursorKind.MACRO_DEFINITION:
            # Declaration-only C API attributes are undefined for preprocessing
            # cursors.  Bind the real macro name/body tokens and every use edge.
            body = tuple((token.kind.name, token.spelling) for token in cursor.get_tokens())
            shapes.append((cursor.kind.name, cursor.spelling, body, 'PREPROCESSING', 'PREPROCESSING'))
        else:
            shapes.append((cursor.kind.name, cursor.spelling, cursor.type.kind.name,
                           cursor.storage_class.name, cursor.linkage.name))
    refs = {}
    for cursor in cursors:
        if not main_location(cursor.location) or cursor.kind.is_declaration():
            continue
        reference = cursor.referenced
        if reference is None:
            continue
        ident = key(reference)
        if ident in ids:
            target = ('main', ids[ident])
        else:
            target = ('external', reference.kind.name, reference.spelling,
                      reference.canonical.get_usr())
        token = (cursor.location.offset, cursor.kind.name, target)
        refs[token] = (cursor.kind.name, target)
    return declarations, ids, shapes, [refs[k] for k in sorted(refs)]


def inverse(candidate, edits):
    result = bytearray(candidate)
    for edit in reversed(edits):
        start, end = edit['candidate_start'], edit['candidate_end']
        if result[start:end] != edit['new'].encode():
            raise Rejected('inverse edit does not identify the produced alias')
        result[start:end] = edit['old'].encode()
    return bytes(result)


def rewrite(source, *, clang_site, resource_dir, arguments=(), protected=()):
    if type(source) is not bytes:
        raise Rejected('immutable bytes input required')
    try:
        source.decode('ascii')
    except UnicodeDecodeError as error:
        raise Rejected('first policy admits ASCII C only') from error
    if b'??' in source or b'\\\n' in source or b'\\\r\n' in source:
        raise Rejected('trigraph/phase-two splice input is outside this policy')
    ci = clang_api(clang_site)
    tu, args, diagnostics = parse(ci, source, resource_dir, arguments)
    all_cursors = list(tu.cursor.walk_preorder())
    declarations, decl_ids, shapes, refs = snapshot(ci, tu)
    macros = {c.spelling for c in all_cursors if c.kind == ci.CursorKind.MACRO_DEFINITION}
    macro_spans = [(c.extent.start.offset, c.extent.end.offset) for c in all_cursors
                   if c.kind == ci.CursorKind.MACRO_INSTANTIATION and main_location(c.location)]
    eligibility_protected = KEYWORDS | frozenset(protected) | macros
    protected_names = eligibility_protected
    # All main-file declarations outside the automatic/parameter namespaces stay
    # reserved, even if a particular function does not currently reference them.
    kept = {c.spelling for c in declarations if c.kind not in
            (ci.CursorKind.PARM_DECL, ci.CursorKind.VAR_DECL) or
            c.storage_class not in (ci.StorageClass.NONE, ci.StorageClass.AUTO,
                                    ci.StorageClass.REGISTER) or
            c.semantic_parent.kind != ci.CursorKind.FUNCTION_DECL}
    protected_names |= kept
    tokens = list(tu.get_tokens(extent=tu.cursor.extent))
    identifier_tokens = {t.extent.start.offset: t for t in tokens
                         if main_location(t.location) and t.kind == ci.TokenKind.IDENTIFIER}
    opaque = [(t.extent.start.offset, t.extent.end.offset) for t in tokens
              if main_location(t.location) and t.kind in
              (ci.TokenKind.COMMENT, ci.TokenKind.LITERAL)]
    functions = sorted((c for c in tu.cursor.get_children() if
                        c.kind == ci.CursorKind.FUNCTION_DECL and c.is_definition()
                        and main_location(c.location)), key=lambda c: c.location.offset)
    edits = []
    renamed_ids = {}
    rows = []
    for function in functions:
        start, end = function.extent.start.offset, function.extent.end.offset
        function_tokens = [t for t in tokens if main_location(t.location) and
                           start <= t.extent.start.offset < end]
        words = {t.spelling for t in function_tokens if t.kind == ci.TokenKind.IDENTIFIER}
        forbidden = {t.spelling for t in function_tokens} & {'asm', '__asm', '__asm__', '__func__', '__FUNCTION__',
                             '__PRETTY_FUNCTION__', '__builtin_dump_struct'}
        if forbidden:
            rows.append({'function': function.spelling, 'skipped': 'name-observer/asm',
                         'spellings': sorted(forbidden)})
            continue
        candidates = {}
        immediate_parameters = {key(c) for c in function.get_children()
                                if c.kind == ci.CursorKind.PARM_DECL}
        for cursor in function.walk_preorder():
            if not main_location(cursor.location) or not WORD.fullmatch(cursor.spelling):
                continue
            if cursor.spelling.startswith('_') or len(cursor.spelling) < 2:
                continue
            if cursor.kind == ci.CursorKind.PARM_DECL:
                if key(cursor) not in immediate_parameters:
                    continue
            elif cursor.kind == ci.CursorKind.VAR_DECL:
                if key(cursor.semantic_parent) != key(function):
                    continue
                if cursor.storage_class not in (ci.StorageClass.NONE, ci.StorageClass.AUTO,
                                                ci.StorageClass.REGISTER):
                    continue
                if cursor.linkage != ci.LinkageKind.NO_LINKAGE:
                    continue
            else:
                continue
            if cursor.spelling in eligibility_protected:
                continue
            candidates[key(cursor)] = {'cursor': cursor, 'positions': {cursor.location.offset},
                                       'rejected': None}
        for cursor in function.walk_preorder():
            reference = cursor.referenced
            if reference is None or key(reference) not in candidates or cursor.kind.is_declaration():
                continue
            row = candidates[key(reference)]
            if not main_location(cursor.location):
                row['rejected'] = 'non-main-file reference'
            else:
                row['positions'].add(cursor.location.offset)
        for ident, row in candidates.items():
            name = row['cursor'].spelling
            for position in row['positions']:
                token = identifier_tokens.get(position)
                if (token is None or token.spelling != name or
                        source[position:token.extent.end.offset] != name.encode() or
                        intersect(position, position + len(name), opaque + macro_spans)):
                    row['rejected'] = 'macro/opaque/nonphysical identifier reference'
                    break
                owner = token.cursor.referenced or token.cursor
                if key(owner) != ident:
                    row['rejected'] = 'token annotation does not confirm declaration identity'
                    break
            # TLS local declarations are not ordinary automatic storage.  Clang
            # exposes the storage keyword as a token even on API versions without
            # a Python TLS-kind property.
            declaration_words = {t.spelling for t in function_tokens if
                                 row['cursor'].extent.start.offset <= t.extent.start.offset <
                                 row['cursor'].extent.end.offset}
            if declaration_words & {'_Thread_local', '__thread', 'static', 'extern'}:
                row['rejected'] = 'nonautomatic storage spelling'
        pool = aliases()
        reserved = set(protected_names | words)
        function_row = {'function': function.spelling, 'declarations': [], 'skipped_declarations': []}
        for ident, row in sorted(candidates.items(), key=lambda item: item[1]['cursor'].location.offset):
            old = row['cursor'].spelling
            if row['rejected']:
                function_row['skipped_declarations'].append({'name': old, 'reason': row['rejected']})
                continue
            new = next(name for name in pool if name not in reserved)
            reserved.add(new)
            if len(new) >= len(old):
                function_row['skipped_declarations'].append({'name': old, 'reason': 'no strict source saving'})
                continue
            ordinal = decl_ids[ident]
            renamed_ids[ordinal] = new
            positions = sorted(row['positions'])
            function_row['declarations'].append({'ordinal': ordinal, 'old': old, 'new': new,
                                                  'occurrences': len(positions), 'offsets': positions})
            for position in positions:
                edits.append({'start': position, 'end': position + len(old),
                              'old': old, 'new': new, 'declaration_ordinal': ordinal})
        rows.append(function_row)
    edits.sort(key=lambda edit: edit['start'])
    pieces = []
    offset = 0
    candidate_offset = 0
    for edit in edits:
        if edit['start'] < offset or source[edit['start']:edit['end']] != edit['old'].encode():
            raise Rejected('overlapping edit or wrong physical input bytes')
        unchanged = source[offset:edit['start']]
        pieces.extend((unchanged, edit['new'].encode()))
        candidate_offset += len(unchanged)
        edit['candidate_start'] = candidate_offset
        candidate_offset += len(edit['new'])
        edit['candidate_end'] = candidate_offset
        offset = edit['end']
    pieces.append(source[offset:])
    candidate = b''.join(pieces)
    if inverse(candidate, edits) != source:
        raise Rejected('position-bound inverse did not reconstruct exact input')
    after, after_args, after_diagnostics = parse(ci, candidate, resource_dir, arguments)
    _, _, after_shapes, after_refs = snapshot(ci, after)
    expected_shapes = list(shapes)
    for ordinal, name in renamed_ids.items():
        original = shapes[ordinal]
        expected_shapes[ordinal] = (original[0], name, *original[2:])
    if after_shapes != expected_shapes or after_refs != refs:
        raise Rejected('reparse declaration shape or referenced-declaration graph changed')
    if after_args != args:
        raise Rejected('parser configuration changed')
    return candidate, {'policy': 'automatic-function-wide-reuse-v1',
        'input_bytes': len(source), 'input_sha256': digest(source),
        'candidate_bytes': len(candidate), 'candidate_sha256': digest(candidate),
        'source_saved_bytes': len(source) - len(candidate), 'parser_args': args,
        'diagnostics': diagnostics, 'candidate_diagnostics': after_diagnostics,
        'macro_names': sorted(macros), 'macro_expansion_count': len(macro_spans),
        'functions': rows, 'renamed_declarations': len(renamed_ids), 'edits': edits,
        'position_bound_inverse_exact': True, 'reparse_binding_graph_equal': True,
        'protected_declaration_shapes_equal': True, 'native_compile_executed': False}
