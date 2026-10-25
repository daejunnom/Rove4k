#!/usr/bin/env python3
"""Inventory one conservative F declaration-join policy, without mutating C.

Only the exact qualified shipping source is admitted. One real Clang AST is
parsed through the frozen scope tool's API. This script does not rewrite the
source, compile native code, package a wrapper or run an engine.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import sys
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
INPUT_BYTES = 9954
INPUT_SHA256 = '00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916'
SCOPE_SHA256 = '02ca17d1c251945f1c021e3482272ef891485c2227a90b4712a36b987d29f08b'
INDEX_SHA256 = '1031451e19ab5db19ae42da4563f8db8e5c853f9bf3508a2a39a7d57c92eeccd'
LIBCLANG_RECEIPT_SHA256 = '34774b478aa3c57a4851596f85796b476baea2a238a8fbee9159143631f12e89'
HEADERS_RECEIPT_SHA256 = 'd0a453bc55f1156a8fcbf3d5137c77bd32ef4256819e58c650c88f111ba752bf'
SPECIFIERS = frozenset('const signed unsigned short long char int float double _Bool'.split())
TYPEDEFS = frozenset('int8_t uint8_t int16_t uint16_t int32_t uint32_t int64_t uint64_t size_t ptrdiff_t'.split())
OBSERVERS = frozenset('sizeof _Alignof alignof _Generic typeof __typeof __typeof__ __auto_type __builtin_types_compatible_p __builtin_offsetof offsetof __builtin_classify_type'.split())
ARITHMETIC = frozenset('BOOL CHAR_U UCHAR CHAR16 CHAR32 USHORT UINT ULONG ULONGLONG CHAR_S SCHAR WCHAR SHORT INT LONG LONGLONG FLOAT DOUBLE LONGDOUBLE FLOAT128 HALF FLOAT16'.split())
WORD = re.compile(rb'[A-Za-z_][A-Za-z_0-9]*\Z')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked(path, expected):
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError('pinned input changed: ' + str(path))
    return data


def pin(path, data):
    return {'path': str(path), 'bytes': len(data), 'sha256': sha(data)}


def intersects(a, b, ranges):
    return any(a < y and x < b for x, y in ranges)


def inventory(source, api, ci, tu):
    """Return original source locations only; never construct a mutated source."""
    all_cursors = list(tu.cursor.walk_preorder())
    tokens = [t for t in tu.get_tokens(extent=tu.cursor.extent) if api.main_location(t.location)]
    macros = [(c.extent.start.offset, c.extent.end.offset) for c in all_cursors
              if c.kind == ci.CursorKind.MACRO_INSTANTIATION and api.main_location(c.location)]
    opaque = [(t.extent.start.offset, t.extent.end.offset) for t in tokens
              if t.kind in (ci.TokenKind.COMMENT, ci.TokenKind.LITERAL)]
    directives = []
    offset = 0
    for line in source.splitlines(keepends=True):
        if line.lstrip().startswith(b'#'):
            directives.append((offset, offset + len(line)))
        offset += len(line)

    def attributes(cursor):
        return any(c.kind.name.endswith('_ATTR') for c in cursor.walk_preorder())

    def declaration(stmt):
        start, end = stmt.extent.start.offset, stmt.extent.end.offset
        row = {'start': start, 'end': end, 'original': source[start:end].decode('ascii')}
        children = list(stmt.get_children())
        if len(children) != 1 or children[0].kind != ci.CursorKind.VAR_DECL:
            row['rejected'] = 'DeclStmt does not contain exactly one VarDecl'
            return row
        var = children[0]
        row.update(name=var.spelling, name_offset=var.location.offset,
                   type=var.type.spelling, canonical_type=var.type.get_canonical().spelling,
                   canonical_kind=var.type.get_canonical().kind.name,
                   storage=var.storage_class.name)
        prefix = source[start:var.location.offset]
        row['explicit_prefix'] = prefix.decode('ascii')
        if (not api.main_location(var.location) or not api.main_location(var.extent.start)
                or not api.main_location(var.extent.end)
                or var.semantic_parent.kind != ci.CursorKind.FUNCTION_DECL
                or var.storage_class != ci.StorageClass.NONE):
            row['rejected'] = 'nonphysical or non-implicit-automatic variable'
            return row
        if (source[var.location.offset:var.location.offset + len(var.spelling)] != var.spelling.encode()
                or source[end - 1:end] != b';'):
            row['rejected'] = 'physical name or terminating semicolon mismatch'
            return row
        canonical = var.type.get_canonical()
        if (canonical.kind.name not in ARITHMETIC or canonical.is_volatile_qualified()
                or canonical.is_restrict_qualified()):
            row['rejected'] = 'not admitted arithmetic scalar type or volatile/restrict type'
            return row
        if attributes(var):
            row['rejected'] = 'attribute on declaration or initializer subtree'
            return row
        local_tokens = [t for t in tokens if start <= t.extent.start.offset < end]
        prefix_tokens = [t for t in local_tokens if t.extent.end.offset <= var.location.offset]
        prefix_words = [t.spelling for t in prefix_tokens]
        if (not prefix_words or any(word not in SPECIFIERS | TYPEDEFS for word in prefix_words)
                or not prefix.endswith((b' ', b'\t', b'\n'))
                or any(t.kind not in (ci.TokenKind.KEYWORD, ci.TokenKind.IDENTIFIER) for t in prefix_tokens)):
            row['rejected'] = 'prefix not restricted explicit arithmetic specifier/typedef grammar'
            return row
        if any(t.spelling in OBSERVERS for t in local_tokens):
            row['rejected'] = 'type observer in declaration or initializer'
            return row
        if intersects(start, end, macros + directives):
            row['rejected'] = 'macro expansion or directive in declaration'
            return row
        if intersects(start, var.location.offset, opaque):
            row['rejected'] = 'opaque prefix token'
            return row
        type_refs = []
        for child in var.get_children():
            if child.kind != ci.CursorKind.TYPE_REF:
                continue
            target = child.referenced
            if target is None or attributes(target):
                row['rejected'] = 'unbound or attributed typedef reference'
                return row
            type_refs.append({'spelling': child.spelling, 'target': api.key(target),
                              'USR': target.canonical.get_usr()})
        row['type_references'] = type_refs
        row['const_qualified'] = canonical.is_const_qualified()
        row['size'] = var.type.get_size()
        row['alignment'] = var.type.get_align()
        if row['size'] != canonical.get_size() or row['alignment'] != canonical.get_align():
            row['rejected'] = 'typedef changes canonical size/alignment'
            return row
        row['eligible_declaration'] = True
        return row

    functions = sorted((c for c in tu.cursor.get_children() if c.kind == ci.CursorKind.FUNCTION_DECL
                        and c.is_definition() and api.main_location(c.location)),
                       key=lambda c: c.location.offset)
    pairs = []
    decls = {}
    blocks = 0
    for function in functions:
        for block in function.walk_preorder():
            if block.kind != ci.CursorKind.COMPOUND_STMT or not api.main_location(block.extent.start):
                continue
            blocks += 1
            siblings = list(block.get_children())
            for stmt in siblings:
                if stmt.kind == ci.CursorKind.DECL_STMT:
                    key = stmt.extent.start.offset
                    if key not in decls:
                        decls[key] = declaration(stmt)
            for left, right in zip(siblings, siblings[1:]):
                if left.kind != ci.CursorKind.DECL_STMT or right.kind != ci.CursorKind.DECL_STMT:
                    continue
                a = decls[left.extent.start.offset]
                b = decls[right.extent.start.offset]
                row = {'function': function.spelling, 'block_start': block.extent.start.offset,
                       'left': a['start'], 'right': b['start'],
                       'original_pair': source[a['start']:b['end']].decode('ascii')}
                if not a.get('eligible_declaration') or not b.get('eligible_declaration'):
                    row['rejected'] = 'one or both declarations outside policy'
                elif a['explicit_prefix'] != b['explicit_prefix']:
                    row['rejected'] = 'different exact explicit prefixes'
                elif any(a[key] != b[key] for key in ('canonical_type', 'canonical_kind', 'const_qualified',
                                                       'size', 'alignment', 'type_references')):
                    row['rejected'] = 'different bound type/qualifiers/alignment/typedef references'
                elif a['name'] == b['name']:
                    row['rejected'] = 'same physical name'
                elif source[a['end']:b['start']].strip() or intersects(a['end'] - 1, b['name_offset'], opaque + macros + directives):
                    row['rejected'] = 'non-whitespace or opaque/macro/directive join boundary'
                else:
                    row.update(proposed=True, removed_raw_prefix_bytes=len(b['explicit_prefix'].encode()),
                               proposal={'replace_semicolon_offset': a['end'] - 1,
                                         'replace_semicolon_with': ',',
                                         'remove_duplicate_prefix_start': b['start'],
                                         'remove_duplicate_prefix_end': b['name_offset'],
                                         'initializer_bytes_preserved': True,
                                         'declarator_order_preserved': True})
                pairs.append(row)
    proposed = [p for p in pairs if p.get('proposed')]
    # Counts are arithmetic over disjoint prefix-removal proposals, not a source rewrite.
    return {'main_functions': len(functions), 'compound_blocks': blocks,
            'block_direct_DeclStmt_count': len(decls), 'adjacent_DeclStmt_pairs': len(pairs),
            'eligible_declarations': sum(d.get('eligible_declaration', False) for d in decls.values()),
            'proposed_join_boundaries': len(proposed),
            'raw_duplicate_type_prefix_bytes': sum(p['removed_raw_prefix_bytes'] for p in proposed),
            'proposed_raw_source_length_arithmetic_only': len(source) - sum(p['removed_raw_prefix_bytes'] for p in proposed),
            'macro_expansions_in_main': len(macros),
            'declaration_rejection_counts': dict(collections.Counter(d['rejected'] for d in decls.values() if 'rejected' in d)),
            'pair_rejection_counts': dict(collections.Counter(p['rejected'] for p in pairs if 'rejected' in p)),
            'declarations': [decls[k] for k in sorted(decls)], 'pairs': pairs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--scope-api', type=Path, required=True)
    parser.add_argument('--clang-site', type=Path, required=True)
    parser.add_argument('--resource-dir', type=Path, required=True)
    parser.add_argument('--normal-index', type=Path, required=True)
    parser.add_argument('--libclang-receipt', type=Path, required=True)
    parser.add_argument('--headers-receipt', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if (not args.out.is_absolute() or out.exists() or out == REPO or REPO in out.parents
            or any((p / '.git').exists() for p in (out, *out.parents))):
        parser.error('a new absolute external output directory is required')
    source = checked(args.source, INPUT_SHA256)
    if len(source) != INPUT_BYTES or b'??' in source or b'\\\n' in source or b'\\\r\n' in source:
        raise ValueError('source outside exact ASCII/no-splice policy')
    source.decode('ascii')
    raw = checked(args.scope_api, SCOPE_SHA256)
    index = checked(args.normal_index, INDEX_SHA256)
    tool = checked(args.libclang_receipt, LIBCLANG_RECEIPT_SHA256)
    headers = checked(args.headers_receipt, HEADERS_RECEIPT_SHA256)
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one read-only AST inventory; proposed locations only; no candidate mutation',
              'policy': 'adjacent single implicit-automatic arithmetic-scalar DeclStmt siblings, exact explicit prefix and bound type; macro/observer/attribute/opaque-boundary excluded',
              'source': pin(args.source, source), 'scope_API': pin(args.scope_api, raw),
              'normal_index': pin(args.normal_index, index), 'libclang_receipt': pin(args.libclang_receipt, tool),
              'headers_receipt': pin(args.headers_receipt, headers),
              'executed': {'AST_parses': 0, 'candidate_mutations': 0, 'native_compiles': 0,
                           'codec_runs': 0, 'engine_runs': 0},
              'raw_savings_are_not_whole_cost': True, 'policy_review_required_before_mutation': True}
    def save():
        (out / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        api = types.ModuleType('pinned_scope_inventory')
        api.__file__ = str(args.scope_api)
        exec(compile(raw, str(args.scope_api), 'exec'), api.__dict__)
        ci = api.clang_api(args.clang_site)
        report['executed']['AST_parses'] = 1
        tu, arguments, diagnostics = api.parse(ci, source, args.resource_dir, ('-Os', '-pthread', '-std=gnu17'))
        report.update(parser_args=arguments, diagnostics=diagnostics)
        report['inventory'] = inventory(source, api, ci, tu)
        if args.source.read_bytes() != source:
            raise ValueError('source changed during inventory')
        report['complete'] = True
        save()
        print(json.dumps({'complete': True, 'out': str(out), 'source_sha256': INPUT_SHA256,
                          **{k: v for k, v in report['inventory'].items() if k not in ('declarations', 'pairs')}}, indent=2))
    except Exception as error:
        report['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
