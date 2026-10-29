"""One exact F source-only, original-position, reparse-gated alias pass."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import string
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(test, message):
    if not test:
        raise ValueError(message)


def load(path, pin):
    raw = path.read_bytes()
    need(sha(raw) == pin, 'frozen scope API changed')
    spec = importlib.util.spec_from_file_location('frozen_scope_API', path)
    result = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), result.__dict__)
    return result


def apply(source, inventory, names):
    edits = sorted(({'start': p, 'end': p+len(row['old']), 'old': row['old'],
                     'new': names[ordinal], 'ordinal': ordinal}
                    for ordinal, row in inventory.items() if names[ordinal] != row['old']
                    for p in row['offsets']), key=lambda e: e['start'])
    parts, end, produced = [], 0, 0
    for edit in edits:
        a, b = edit['start'], edit['end']
        need(a >= end and source[a:b] == edit['old'].encode(), 'original physical edit mismatch')
        gap = source[end:a]
        parts.extend((gap, edit['new'].encode()))
        edit['candidate_start'] = produced+len(gap)
        edit['candidate_end'] = edit['candidate_start']+len(edit['new'])
        produced = edit['candidate_end']
        end = b
    parts.append(source[end:])
    return b''.join(parts), edits


def type_shapes(ci, declarations):
    result = []
    for cursor in declarations:
        if cursor.kind == ci.CursorKind.MACRO_DEFINITION:
            result.append(None)
            continue
        typ = cursor.type
        result.append((typ.spelling, typ.get_canonical().spelling, typ.get_size(), typ.get_align(),
                       typ.is_const_qualified(), typ.is_volatile_qualified(), typ.is_restrict_qualified(),
                       cursor.get_field_offsetof() if cursor.kind == ci.CursorKind.FIELD_DECL else None))
    return result


def reference_projection(api, tu, ids, edits):
    """Keep original physical positions and cursor multiplicities, not just order."""
    def original(offset):
        delta = 0
        for edit in edits:
            if offset < edit['candidate_start']:
                break
            if offset < edit['candidate_end']:
                need(offset == edit['candidate_start'], 'reference inside edited identifier without token-start identity')
                return edit['start']
            delta += len(edit['new'])-len(edit['old'])
        return offset-delta
    result = []
    for cursor in tu.cursor.walk_preorder():
        if not api.main_location(cursor.location) or cursor.kind.is_declaration() or cursor.referenced is None:
            continue
        referenced = cursor.referenced
        ident = api.key(referenced)
        target = ('main', ids[ident]) if ident in ids else (
            'external', referenced.kind.name, referenced.spelling, referenced.canonical.get_usr())
        result.append((original(cursor.location.offset), cursor.kind.name, target))
    return sorted(result)


def inventory(api, ci, tu, source, declarations, ids):
    cursors = list(tu.cursor.walk_preorder())
    tokens = [t for t in tu.get_tokens(extent=tu.cursor.extent) if api.main_location(t.location)]
    words = {t.spelling for t in tokens}
    forbidden = {'asm', '__asm', '__asm__', '__func__', '__FUNCTION__', '__PRETTY_FUNCTION__',
                 '__builtin_dump_struct', '__builtin_offsetof', 'offsetof', 'typeof', '__typeof',
                 '__typeof__', '_Generic', '__builtin_choose_expr', '__builtin_types_compatible_p',
                 '__attribute', '__attribute__', '_Alignas'}
    need(not words & forbidden, 'fixed-source name/type/asm observer outside policy')

    def vm(typ):
        typ = typ.get_canonical()
        if typ.kind.name in {'VARIABLEARRAY', 'DEPENDENTSIZEDARRAY'}:
            return True
        if typ.kind.name == 'POINTER':
            return vm(typ.get_pointee())
        if typ.kind.name == 'CONSTANTARRAY':
            return vm(typ.get_array_element_type())
        return False

    for cursor in cursors:
        if not api.main_location(cursor.location) or cursor.kind.is_preprocessing():
            continue
        need(not vm(cursor.type), 'variably modified type outside fixed-source policy')
        terms = [t.spelling for t in cursor.get_tokens()]
        need(cursor.kind.name != 'COMPOUND_LITERAL_EXPR', 'compound literal context outside policy')
        need(not (cursor.kind == ci.CursorKind.PARM_DECL and '[' in terms), 'array-form parameter outside policy')
        need(not (terms and terms[0] in {'sizeof', '_Alignof', '__alignof', '__alignof__'} and '[' in terms),
             'bracketed size/alignment type context outside policy')

    macros = {c.spelling for c in cursors if c.kind == ci.CursorKind.MACRO_DEFINITION}
    macro_spans = [(c.extent.start.offset, c.extent.end.offset) for c in cursors
                   if c.kind == ci.CursorKind.MACRO_INSTANTIATION and api.main_location(c.location)]
    opaque = [(t.extent.start.offset, t.extent.end.offset) for t in tokens
              if t.kind in (ci.TokenKind.COMMENT, ci.TokenKind.LITERAL)]
    physical = {t.extent.start.offset: t for t in tokens if t.kind == ci.TokenKind.IDENTIFIER}
    functions = [c for c in tu.cursor.get_children() if api.main_location(c.location) and
                 c.kind == ci.CursorKind.FUNCTION_DECL and c.is_definition()]
    candidates, skipped, automatic_ids = {}, [], set()
    for function in functions:
        parameters = {api.key(c) for c in function.get_children() if c.kind == ci.CursorKind.PARM_DECL}
        for cursor in function.walk_preorder():
            if not api.main_location(cursor.location) or not api.WORD.fullmatch(cursor.spelling):
                continue
            ident = api.key(cursor)
            if cursor.kind == ci.CursorKind.PARM_DECL:
                if ident not in parameters:
                    continue
            elif cursor.kind == ci.CursorKind.VAR_DECL:
                if api.key(cursor.semantic_parent) != api.key(function) or cursor.storage_class not in (
                        ci.StorageClass.NONE, ci.StorageClass.AUTO, ci.StorageClass.REGISTER) or cursor.linkage != ci.LinkageKind.NO_LINKAGE:
                    continue
            else:
                continue
            automatic_ids.add(ident)
            reason = None
            if cursor.spelling.startswith('_') or cursor.spelling in api.KEYWORDS | macros:
                reason = 'protected identifier spelling'
            terms = {t.spelling for t in cursor.get_tokens()}
            if terms & {'static', 'extern', '__thread', '_Thread_local'}:
                reason = 'nonautomatic storage spelling'
            candidates[ident] = {'cursor': cursor, 'function': function.spelling,
                                 'positions': {cursor.location.offset}, 'reason': reason}
    for cursor in cursors:
        if cursor.kind.is_declaration() or cursor.referenced is None:
            continue
        ident = api.key(cursor.referenced)
        if ident not in candidates:
            continue
        row = candidates[ident]
        if not api.main_location(cursor.location):
            row['reason'] = 'non-main-file reference'
        else:
            row['positions'].add(cursor.location.offset)
    result = {}
    for ident, row in sorted(candidates.items(), key=lambda pair: pair[1]['cursor'].location.offset):
        cursor = row['cursor']
        for offset in row['positions']:
            token = physical.get(offset)
            if token is None or token.spelling != cursor.spelling or source[offset:token.extent.end.offset] != cursor.spelling.encode():
                row['reason'] = 'nonphysical identifier reference'
                break
            if api.intersect(offset, token.extent.end.offset, opaque+macro_spans):
                row['reason'] = 'macro/opaque affected declaration or reference'
                break
            if api.key(token.cursor.referenced or token.cursor) != ident:
                row['reason'] = 'token annotation does not bind exact declaration'
                break
        ordinal = ids[ident]
        item = {'ordinal': ordinal, 'old': cursor.spelling, 'function': row['function'],
                'offsets': sorted(row['positions']), 'kind': cursor.kind.name}
        if row['reason']:
            skipped.append({**item, 'reason': row['reason']})
        else:
            result[ordinal] = item
    reserved = set(api.KEYWORDS) | macros
    reserved.update(c.spelling for c in declarations if api.key(c) not in automatic_ids)
    return result, skipped, tokens, reserved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--clang-site', type=Path, required=True)
    parser.add_argument('--resource-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)),
         'new absolute output outside Git required')
    out.mkdir(parents=True)
    started = time.monotonic()
    report = {'complete': False, 'status': 'preparation', 'AST_parses': 0, 'attempts': [], 'decisions': [],
              'native_compiles': 0, 'PP_executions': 0, 'codec_calls': 0, 'engine_executions': 0}
    def save():
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    def event(row):
        with (out/'events.jsonl').open('a') as stream:
            stream.write(json.dumps(row)+'\n')
            stream.flush()
    save()
    try:
        admission_raw = (HERE/'inputs.json').read_bytes()
        admission = json.loads(admission_raw)
        source = args.source.read_bytes()
        need(len(source) == admission['input']['bytes'] and sha(source) == admission['input']['sha256'], 'only exact F9728 input admitted')
        source.decode('ascii')
        need(b'\r' not in source and b'??' not in source and b'\\\n' not in source, 'outside physical ASCII/LF policy')
        api_path = args.reference.resolve()
        api = load(api_path, admission['API_sha256'])
        def toolpins():
            for name, pin in admission['clang_site_sha256'].items():
                need(sha((args.clang_site/name).read_bytes()) == pin, 'external Clang input changed: '+name)
            for name, pin in admission['header_sha256'].items():
                need(sha(Path(name).read_bytes()) == pin, 'included header changed: '+name)
        toolpins()
        ci = api.clang_api(args.clang_site)
        parser_args = ['-x', 'c', '-resource-dir', str(args.resource_dir.resolve()), *admission['arguments']]
        def parse(candidate):
            report['AST_parses'] += 1
            tu = ci.Index.create().parse(api.SOURCE, args=parser_args, unsaved_files=[(api.SOURCE, candidate)],
                options=ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
            diagnostics = [{'severity': d.severity, 'message': d.spelling, 'location': str(d.location),
                            'file': d.location.file.name if d.location.file else ''} for d in tu.diagnostics]
            if any(d['severity'] >= ci.Diagnostic.Fatal or
                   (d['severity'] >= ci.Diagnostic.Error and d['file'] != api.SOURCE) for d in diagnostics):
                event({'phase': 'fatal-or-nonlocal-diagnostic', 'diagnostics': diagnostics})
                raise RuntimeError('fatal/nonlocal/resource parser diagnostic')
            return tu, diagnostics
        before, diagnostics = parse(source)
        need(not any(d['severity'] >= ci.Diagnostic.Error for d in diagnostics), 'input contains parser error')
        headers = {str(row.include) for row in before.get_includes()}
        need(headers == set(admission['header_sha256']), 'fixed actual header closure changed')
        declarations, ids, shapes, refs = api.snapshot(ci, before)
        types = type_shapes(ci, declarations)
        projection = reference_projection(api, before, ids, [])
        rows, skipped, tokens, reserved = inventory(api, ci, before, source, declarations, ids)
        reserved.update(target[2] for _, target in refs if target[0] == 'external')
        names = {ordinal: row['old'] for ordinal, row in rows.items()}
        report.update(input_bytes=len(source), input_sha256=sha(source), inventory=list(rows.values()),
                      eligible_declarations=len(rows), eligible_one_character=sum(len(row['old']) == 1 for row in rows.values()),
                      eligible_occurrences=sum(len(row['offsets']) for row in rows.values()), skipped=skipped,
                      protected_names=sorted(reserved), diagnostics=diagnostics, reference_projection_edges=len(refs),
                      declaration_shapes=len(shapes), original_position_reference_edges=len(projection),
                      parser_args=parser_args, source_admission_sha256=sha(admission_raw))
        (out/'inventory.json').write_text(json.dumps({k: report[k] for k in ('inventory', 'skipped', 'protected_names')}, indent=2)+'\n')
        expected_base_tokens = [(t.kind.name, t.spelling) for t in tokens]
        def check(candidate, edits, assignment, phase):
            need(api.inverse(candidate, edits) == source, 'exact original-position inverse failed')
            # apply() constructs only admitted identifiers and copies every intervening byte verbatim.
            (out/'active-trial.c').write_bytes(candidate)
            (out/'active-trial.json').write_text(json.dumps({'phase': phase, 'edits': edits}, indent=2)+'\n')
            after, ds = parse(candidate)
            errors = [d for d in ds if d['severity'] >= ci.Diagnostic.Error]
            if errors:
                return False, {'reason': 'main-file parser error; alias rejected', 'diagnostics': ds}
            if [(d['severity'], d['message']) for d in ds] != [(d['severity'], d['message']) for d in diagnostics]:
                return False, {'reason': 'diagnostic projection changed', 'diagnostics': ds}
            after_decls, after_ids, after_shapes, after_refs = api.snapshot(ci, after)
            expected = list(shapes)
            for ordinal, name in assignment.items():
                shape = expected[ordinal]
                expected[ordinal] = (shape[0], name, *shape[2:])
            if after_shapes != expected or after_refs != refs or type_shapes(ci, after_decls) != types:
                return False, {'reason': 'declaration/type shape or exact reference projection changed', 'diagnostics': ds}
            try:
                projected = reference_projection(api, after, after_ids, edits)
            except ValueError as error:
                return False, {'reason': str(error), 'diagnostics': ds}
            if projected != projection:
                return False, {'reason': 'original-position reference projection or multiplicity changed', 'diagnostics': ds}
            replacement = {e['start']: e['new'] for e in edits}
            wanted = [(kind, replacement.get(token.extent.start.offset, spelling))
                      for token, (kind, spelling) in zip(tokens, expected_base_tokens)]
            actual = [(t.kind.name, t.spelling) for t in after.get_tokens(extent=after.cursor.extent)
                      if api.main_location(t.location)]
            if actual != wanted or {str(row.include) for row in after.get_includes()} != headers:
                return False, {'reason': 'remaining physical tokens or included header closure changed', 'diagnostics': ds}
            return True, {'reason': 'zero errors; inverse/complement/shapes/types/reference projection exact', 'diagnostics': ds}
        def checkpoint(done, phase):
            candidate, edits = apply(source, rows, names)
            need(api.inverse(candidate, edits) == source, 'checkpoint inverse differs')
            state = {'complete': False, 'phase': phase, 'declarations_done': done,
                     'candidate_bytes': len(candidate), 'candidate_sha256': sha(candidate), 'edits': edits,
                     'names': names, 'AST_parses': report['AST_parses'], 'elapsed_seconds': time.monotonic()-started}
            (out/'checkpoint.c').write_bytes(candidate)
            (out/'checkpoint.json').write_text(json.dumps(state, indent=2)+'\n')
        checkpoint(0, 'exact-original-fallback')
        deadline = started+admission['soft_budget_seconds']
        done, complete = 0, True
        for ordinal, row in rows.items():
            if time.monotonic() >= deadline:
                complete = False
                break
            selected = False
            for alias in api.aliases():
                if len(alias) > len(row['old']):
                    break
                if time.monotonic() >= deadline:
                    complete = False
                    break
                if alias in reserved:
                    continue
                proposed = dict(names)
                proposed[ordinal] = alias
                candidate, edits = apply(source, rows, proposed)
                accepted, detail = check(candidate, edits, proposed, 'trial')
                attempt = {'ordinal': ordinal, 'function': row['function'], 'old': row['old'],
                           'alias': alias, 'accepted': accepted, **detail}
                event(attempt)
                report['attempts'].append(attempt)
                if not accepted:
                    if not (out/'first-rejected-trial.c').exists():
                        (out/'first-rejected-trial.c').write_bytes(candidate)
                        (out/'first-rejected-trial.json').write_text(json.dumps(attempt, indent=2)+'\n')
                    continue
                names = proposed
                report['decisions'].append({'ordinal': ordinal, 'function': row['function'], 'old': row['old'],
                                            'new': alias, 'occurrences': len(row['offsets'])})
                selected = True
                break
            if not complete:
                break
            done += 1
            if not selected:
                report['decisions'].append({'ordinal': ordinal, 'function': row['function'], 'old': row['old'],
                                            'new': names[ordinal], 'fallback_retained': True})
            checkpoint(done, 'accepted-step-or-original-name-retained')
            save()
        candidate, edits = apply(source, rows, names)
        accepted, detail = check(candidate, edits, names, 'final')
        need(accepted, 'final independent parse/inverse/complement failed: '+json.dumps(detail))
        toolpins()
        need((HERE/'inputs.json').read_bytes() == admission_raw and sha(api_path.read_bytes()) == admission['API_sha256'],
             'admission/reference changed during one pass')
        (out/'candidate.c').write_bytes(candidate)
        report.update(complete=complete, final_validation_complete=True,
                      status='complete fixed greedy pass' if complete else 'incomplete; soft budget; validated best-so-far',
                      declarations_done=done, elapsed_seconds=time.monotonic()-started,
                      candidate_bytes=len(candidate), candidate_sha256=sha(candidate), raw_source_saved_bytes=len(source)-len(candidate),
                      alias_changed_declarations=sum(names[o] != row['old'] for o, row in rows.items()),
                      physical_identifier_changes=len(edits), edits=edits,
                      exact_original_position_inverse=True, exact_remaining_byte_complement=True,
                      declaration_type_shapes_equal=True, exact_reference_projection_equal=True,
                      exact_original_position_reference_projection_and_multiplicity=True,
                      candidate_diagnostics=detail['diagnostics'], selected_for_shipping=False,
                      whole_gain='unmeasured', arbitrary_C_equivalence_claim=False)
        event({'phase': 'terminal', 'status': report['status'], 'candidate_sha256': sha(candidate)})
        print(json.dumps({k: report[k] for k in ('complete', 'status', 'candidate_bytes', 'candidate_sha256',
              'raw_source_saved_bytes', 'eligible_declarations', 'eligible_one_character', 'declarations_done',
              'alias_changed_declarations', 'physical_identifier_changes', 'AST_parses', 'elapsed_seconds')}))
    except BaseException as error:
        report.update(complete=False, status='aborted; no automatic retry', error={'type': type(error).__name__, 'message': str(error)},
                      elapsed_seconds=time.monotonic()-started)
        event({'phase': 'abort', 'error': report['error']})
        if (out/'active-trial.c').exists():
            (out/'aborted-active-trial.c').write_bytes((out/'active-trial.c').read_bytes())
            (out/'aborted-active-trial.json').write_bytes((out/'active-trial.json').read_bytes())
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
