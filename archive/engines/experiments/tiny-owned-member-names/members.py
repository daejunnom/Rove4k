#!/usr/bin/env python3
"""One exact F member-name map using the immutable scope AST API; no compiler."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def module(path):
    spec = importlib.util.spec_from_file_location('frozen_scope_API', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def layout(api, ci, declarations, ids):
    records, fields = {}, []
    for cursor in declarations:
        if cursor.kind != ci.CursorKind.FIELD_DECL:
            continue
        parent = cursor.semantic_parent
        need(parent.kind == ci.CursorKind.STRUCT_DECL and api.main_location(parent.location), 'non-owned struct field')
        need(not cursor.is_bitfield(), 'bitfield outside exact F policy')
        owner = ids[api.key(parent)]
        records[owner] = (parent.spelling, parent.type.get_size(), parent.type.get_align())
        fields.append((ids[api.key(cursor)], owner, cursor.type.spelling, cursor.type.get_canonical().spelling,
                       cursor.type.kind.name, cursor.type.get_canonical().kind.name,
                       cursor.type.get_size(), cursor.type.get_align(), cursor.get_field_offsetof(),
                       cursor.type.is_const_qualified(), cursor.type.is_volatile_qualified(), cursor.type.is_restrict_qualified()))
    need(len(fields) == 22 and len(records) == 3, 'owned field/record domain differs')
    return records, fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--clang-site', type=Path, required=True)
    parser.add_argument('--resource-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and
         not any((p/'.git').exists() for p in (out, *out.parents)), 'new absolute output outside Git required')
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one exact F owned-member source map only',
              'native_compiles': 0, 'codec_calls': 0, 'engine_executions': 0,
              'original_control_copied': False, 'source_input_path': str(args.source.resolve())}

    def save():
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        inputs = json.loads((HERE/'inputs.json').read_bytes())
        source = args.source.read_bytes()
        need(type(source) is bytes and len(source) == inputs['source_bytes'] and sha(source) == inputs['source_sha256'], 'exact F10011 input required')
        source.decode('ascii')
        need(b'\r' not in source and b'??' not in source and b'\\\n' not in source, 'outside physical ASCII/LF policy')
        api_path = HERE.parents[2]/inputs['API_relative']
        need(sha(api_path.read_bytes()) == inputs['API_sha256'], 'immutable scope API differs')

        def tool_pins():
            for name, expected in inputs['clang_site_sha256'].items():
                need(sha((args.clang_site/name).read_bytes()) == expected, 'external Clang installation differs: '+name)
            for name, expected in inputs['header_sha256'].items():
                need(sha(Path(name).read_bytes()) == expected, 'actual included header differs: '+name)

        tool_pins()
        api = module(api_path)
        ci = api.clang_api(args.clang_site)
        tu, parser_args, diagnostics = api.parse(ci, source, args.resource_dir, inputs['arguments'])
        need({str(row.include) for row in tu.get_includes()} == set(inputs['header_sha256']), 'actual header closure differs')
        cursors = list(tu.cursor.walk_preorder())
        declarations, ids, shapes, refs = api.snapshot(ci, tu)
        before_layout = layout(api, ci, declarations, ids)
        need({name: [size, align] for name, size, align in before_layout[0].values()} == inputs['owned_record_layout'], 'literal F record layout differs')
        tokens = [t for t in tu.get_tokens(extent=tu.cursor.extent) if api.main_location(t.location)]
        words = {t.spelling for t in tokens if t.kind in (ci.TokenKind.IDENTIFIER, ci.TokenKind.KEYWORD)}
        need(not words & {'asm', '__asm', '__asm__', '__func__', '__FUNCTION__', '__PRETTY_FUNCTION__',
                          '__builtin_dump_struct', '__builtin_offsetof', 'offsetof', '__attribute__', '__attribute',
                          '_Alignas', '_Generic'}, 'name/asm/offset/attribute observer outside exact map')
        macros = {c.spelling for c in cursors if c.kind == ci.CursorKind.MACRO_DEFINITION}
        macro_spans = [(c.extent.start.offset, c.extent.end.offset) for c in cursors
                       if c.kind == ci.CursorKind.MACRO_INSTANTIATION and api.main_location(c.location)]
        opaque = [(t.extent.start.offset, t.extent.end.offset) for t in tokens
                  if t.kind in (ci.TokenKind.COMMENT, ci.TokenKind.LITERAL)]
        physical = {t.extent.start.offset: t for t in tokens if t.kind == ci.TokenKind.IDENTIFIER}
        fields = {ids[api.key(c)]: c for c in declarations if c.kind == ci.CursorKind.FIELD_DECL}
        planned = {row['ordinal']: row for row in inputs['renames']}
        need(len(planned) == 13, 'exact thirteen-field map required')
        owner_names = {}
        for ordinal, cursor in fields.items():
            name = planned[ordinal]['new'] if ordinal in planned else cursor.spelling
            owner_names.setdefault(ids[api.key(cursor.semantic_parent)], []).append(name)
        need(all(len(names) == len(set(names)) for names in owner_names.values()), 'member collision within one struct')
        edits, renamed, rows = [], {}, []
        for ordinal, plan in planned.items():
            cursor = fields[ordinal]
            ident = api.key(cursor)
            need(cursor.spelling == plan['old'] and cursor.semantic_parent.spelling == plan['owner'] and
                 ids[api.key(cursor.semantic_parent)] == plan['owner_ordinal'], 'literal field identity differs')
            need(len(plan['new']) == 1 and plan['new'].isalpha() and plan['new'] not in api.KEYWORDS | macros,
                 'alias is not one safe physical identifier')
            members = [c for c in cursors if c.kind == ci.CursorKind.MEMBER_REF_EXPR and
                       c.referenced is not None and api.key(c.referenced) == ident]
            need(all(api.main_location(c.location) for c in members), 'non-main member reference')
            positions = {cursor.location.offset, *[c.location.offset for c in members]}
            # Clang may repeat a member edge on an UNEXPOSED_EXPR wrapper. It
            # must share an already identified physical member-token offset.
            for reference in cursors:
                if reference.kind.is_declaration() or reference.referenced is None or api.key(reference.referenced) != ident:
                    continue
                need(api.main_location(reference.location) and reference.location.offset in positions,
                     'field edge outside a physical FIELD_DECL/MEMBER_REF_EXPR token')
            need(sorted(positions) == plan['offsets'], 'complete literal field occurrence set differs')
            for position in sorted(positions):
                token = physical.get(position)
                need(token is not None and token.spelling == plan['old'] and
                     token.cursor.kind in (ci.CursorKind.FIELD_DECL, ci.CursorKind.MEMBER_REF_EXPR) and
                     source[position:token.extent.end.offset] == plan['old'].encode() and
                     api.key(token.cursor.referenced or token.cursor) == ident,
                     'physical token annotation does not confirm exact field declaration')
                need(not api.intersect(position, token.extent.end.offset, opaque+macro_spans), 'macro/opaque field use is protected')
                edits.append({'start': position, 'end': token.extent.end.offset, 'old': plan['old'],
                              'new': plan['new'], 'declaration_ordinal': ordinal})
            renamed[ordinal] = plan['new']
            rows.append({**plan, 'occurrences': len(positions)})
        need(len(edits) == 57, 'exact physical edit count differs')
        pieces, offset, produced = [], 0, 0
        for edit in sorted(edits, key=lambda row: row['start']):
            need(edit['start'] >= offset, 'overlapping field edits')
            gap = source[offset:edit['start']]
            pieces.extend((gap, edit['new'].encode()))
            edit['candidate_start'] = produced+len(gap)
            produced = edit['candidate_start']+len(edit['new'])
            edit['candidate_end'] = produced
            offset = edit['end']
        pieces.append(source[offset:])
        candidate = b''.join(pieces)
        edits.sort(key=lambda row: row['start'])
        need(len(candidate) == inputs['candidate_expected_bytes'] and api.inverse(candidate, edits) == source, 'exact inverse or source saving differs')
        (out/'candidate.c').write_bytes(candidate)
        after, after_args, after_diagnostics = api.parse(ci, candidate, args.resource_dir, inputs['arguments'])
        after_declarations, after_ids, after_shapes, after_refs = api.snapshot(ci, after)
        expected_shapes = list(shapes)
        for ordinal, name in renamed.items():
            original = shapes[ordinal]
            expected_shapes[ordinal] = (original[0], name, *original[2:])
        need(after_shapes == expected_shapes and after_refs == refs, 'full declaration/reference graph changed')
        need(after_args == parser_args and layout(api, ci, after_declarations, after_ids) == before_layout, 'field order/type/offset/size/alignment or parser changed')
        after_tokens = [t for t in after.get_tokens(extent=after.cursor.extent) if api.main_location(t.location)]
        replacement = {e['start']: e['new'] for e in edits}
        expected_tokens = [(t.kind.name, replacement.get(t.extent.start.offset, t.spelling)) for t in tokens]
        need([(t.kind.name, t.spelling) for t in after_tokens] == expected_tokens, 'physical tokens beyond admitted member names changed')
        need({str(row.include) for row in after.get_includes()} == set(inputs['header_sha256']), 'candidate header closure changed')
        tool_pins()
        report.update(complete=True, input_bytes=len(source), input_sha256=sha(source), candidate_bytes=len(candidate),
                      candidate_sha256=sha(candidate), source_saved_bytes=len(source)-len(candidate),
                      parser_args=parser_args, diagnostics=diagnostics, candidate_diagnostics=after_diagnostics,
                      API_sha256=inputs['API_sha256'], inputs_sha256=sha((HERE/'inputs.json').read_bytes()),
                      clang_site_sha256=inputs['clang_site_sha256'], actual_header_sha256=inputs['header_sha256'],
                      renamed_fields=rows, edited_tokens=len(edits), edits=edits, exact_inverse=True,
                      full_binding_graph_equal=True, field_type_order_offset_size_align_equal=True,
                      protected_declaration_shapes_equal=True, physical_tokens_only_member_names_changed=True,
                      opaque_macro_header_names_preserved=True, protected_member=inputs['protected_member'],
                      owned_record_layout=inputs['owned_record_layout'], reference_edges=len(refs),
                      member_namespace_reuse_across_structs=True, AST_parses=2)
        save()
        print(json.dumps({k: report[k] for k in ('complete', 'input_bytes', 'candidate_bytes', 'candidate_sha256',
                                                'source_saved_bytes', 'edited_tokens', 'reference_edges')}))
    except BaseException as error:
        report['complete'] = False
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
