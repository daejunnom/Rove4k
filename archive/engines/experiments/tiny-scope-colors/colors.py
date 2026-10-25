"""Source-only F prototype: deterministic reparse-gated local alias reuse."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reference(path, pin):
    raw = Path(path).read_bytes()
    if sha(raw) != pin:
        raise ValueError('frozen reference implementation changed')
    spec = importlib.util.spec_from_file_location('scope_colors_frozen_reference', path)
    result = importlib.util.module_from_spec(spec)
    # Execute the bytes that were actually pinned, not a second path read.
    exec(compile(raw, str(path), 'exec'), result.__dict__)
    return result


def apply(source, inventory, names):
    edits = []
    for ordinal, row in inventory.items():
        for position in row['offsets']:
            edits.append({'start': position, 'end': position + len(row['old']),
                          'old': row['old'], 'new': names[ordinal],
                          'declaration_ordinal': ordinal})
    edits.sort(key=lambda row: row['start'])
    parts, end, produced = [], 0, 0
    for row in edits:
        if row['start'] < end or source[row['start']:row['end']] != row['old'].encode():
            raise ValueError('overlap or changed original physical identifier')
        unchanged = source[end:row['start']]
        parts.extend((unchanged, row['new'].encode()))
        produced += len(unchanged)
        row['candidate_start'] = produced
        produced += len(row['new'])
        row['candidate_end'] = produced
        end = row['end']
    parts.append(source[end:])
    return b''.join(parts), edits


def reject_unmodelled_types(ref, ci, tu):
    """The first prototype admits fixed F, not arbitrary variably modified C."""
    def variably_modified(typ):
        kind = typ.get_canonical().kind.name
        if kind in {'VARIABLEARRAY', 'DEPENDENTSIZEDARRAY'}:
            return True
        if kind == 'POINTER':
            return variably_modified(typ.get_canonical().get_pointee())
        if kind == 'CONSTANTARRAY':
            return variably_modified(typ.get_canonical().get_array_element_type())
        return False
    forbidden = {'typeof', '__typeof', '__typeof__', '_Generic',
                 '__builtin_choose_expr', '__builtin_types_compatible_p',
                 '__builtin_offsetof'}
    for cursor in tu.cursor.walk_preorder():
        if not ref.main_location(cursor.location):
            continue
        if not cursor.kind.is_preprocessing() and variably_modified(cursor.type):
            raise ref.Rejected('variably modified cursor/type is outside first F policy')
        words = [token.spelling for token in cursor.get_tokens()]
        if cursor.kind == ci.CursorKind.FUNCTION_DECL and cursor.is_definition():
            if forbidden & set(words):
                raise ref.Rejected('unmodelled type-expression context')
        if cursor.kind == ci.CursorKind.PARM_DECL and '[' in words:
            raise ref.Rejected('array-form parameter declarator is outside first policy')
        if cursor.kind.name == 'COMPOUND_LITERAL_EXPR':
            raise ref.Rejected('compound literal type context is outside first policy')
        if words and words[0] in {'sizeof', '_Alignof', '__alignof', '__alignof__'} and '[' in words:
            raise ref.Rejected('bracket-containing size/alignment operand is outside first policy')


def rewrite(source, *, reference_path, clang_site, resource_dir, progress=None):
    started = time.monotonic()
    admission_raw = (HERE / 'inputs.json').read_bytes()
    admission = json.loads(admission_raw)
    if type(source) is not bytes or len(source) != admission['input']['bytes'] or sha(source) != admission['input']['sha256']:
        raise ValueError('only the explicitly pinned F post-storage source is admitted')
    ref = reference(reference_path, admission['reference_sha256'])
    for name, pin in admission['clang_site_inputs'].items():
        if sha((Path(clang_site) / name).read_bytes()) != pin:
            raise ValueError('external Clang tool input changed: ' + name)
    if sha((Path(resource_dir) / 'include/stdatomic.h').read_bytes()) != admission['stdatomic_sha256']:
        raise ValueError('qualified real resource header changed')
    arguments = admission['parser_arguments']
    deadline = started + admission['soft_budget_seconds']
    baseline, proof = ref.rewrite(source, clang_site=clang_site, resource_dir=resource_dir,
                                  arguments=arguments)
    if len(baseline) != admission['function_wide_baseline']['bytes'] or sha(baseline) != admission['function_wide_baseline']['sha256']:
        raise ref.Rejected('function-wide source baseline changed')
    ci = ref.clang_api(clang_site)
    tu, args, diagnostics = ref.parse(ci, source, resource_dir, arguments)
    reject_unmodelled_types(ref, ci, tu)
    declarations, ids, shapes, edges = ref.snapshot(ci, tu)
    inventory, names, functions = {}, {}, {}
    for function in proof['functions']:
        for row in function.get('declarations', []):
            ordinal = row['ordinal']
            inventory[ordinal] = row
            names[ordinal] = row['new']
            functions[ordinal] = function['function']
    if len(inventory) != admission['expected_renamed_declarations'] or len(proof['edits']) != admission['expected_edits']:
        raise ref.Rejected('fixed F declaration/reference inventory changed')
    # Same protected namespaces as the reference, plus referenced external names.
    # Automatic local words alone cease to be reserved across the whole function.
    reserved = set(ref.KEYWORDS) | set(proof['macro_names'])
    for function in proof['functions']:
        reserved.update(row['name'] for row in function.get('skipped_declarations', []))
    for cursor in declarations:
        ordinary = cursor.kind in (ci.CursorKind.PARM_DECL, ci.CursorKind.VAR_DECL)
        ordinary &= cursor.storage_class in (ci.StorageClass.NONE, ci.StorageClass.AUTO,
                                             ci.StorageClass.REGISTER) if ordinary else False
        ordinary &= cursor.semantic_parent.kind == ci.CursorKind.FUNCTION_DECL if ordinary else False
        if not ordinary:
            reserved.add(cursor.spelling)
    reserved.update(target[2] for _, target in edges if target[0] == 'external')
    attempts, decisions = [], []
    initial, initial_edits = apply(source, inventory, names)
    if initial != baseline or ref.inverse(initial, initial_edits) != source:
        raise ref.Rejected('inventory does not reproduce exact known-safe fallback')
    if progress:
        progress({'candidate': initial, 'edits': initial_edits, 'declarations_done': 0,
                  'parse_trials': 0, 'complete': False, 'phase': 'known-safe-fallback'})

    def check(candidate, assignment, collision_alias=None):
        # Same fixed parser configuration as the frozen parse API, but retain
        # diagnostics before deciding whether a syntax collision rejects an alias.
        # Fatal resource/library/infrastructure failures must abort the run.
        after = ci.Index.create().parse(ref.SOURCE, args=args,
            unsaved_files=[(ref.SOURCE, candidate)],
            options=ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
        after_diagnostics = [{'severity': d.severity, 'message': d.spelling,
                              'location': str(d.location),
                              'file': d.location.file.name if d.location.file else ''}
                             for d in after.diagnostics]
        if any(d['severity'] >= ci.Diagnostic.Fatal for d in after_diagnostics):
            raise RuntimeError('fatal parser diagnostic: ' + json.dumps(after_diagnostics))
        errors = [d for d in after_diagnostics if d['severity'] >= ci.Diagnostic.Error]
        if errors and any(d['file'] != ref.SOURCE or collision_alias is None or
                not d['message'].startswith(("redefinition of '" + collision_alias + "'",
                                             "redefinition of parameter '" + collision_alias + "'"))
                for d in errors):
            raise RuntimeError('nonlocal or unclassified parser error: ' + json.dumps(errors))
        if errors:
            raise ref.Rejected('trial syntax/semantic collision: ' + json.dumps(after_diagnostics))
        _, _, after_shapes, after_edges = ref.snapshot(ci, after)
        expected = list(shapes)
        for ordinal, name in assignment.items():
            item = shapes[ordinal]
            expected[ordinal] = (item[0], name, *item[2:])
        if after_shapes != expected or after_edges != edges:
            raise ref.Rejected('declaration shape or exact referenced-declaration graph changed')
        return after_diagnostics

    complete = True
    for ordinal in sorted(inventory, key=lambda value: inventory[value]['offsets'][0]):
        if time.monotonic() >= deadline:
            complete = False
            break
        row = inventory[ordinal]
        for alias in ref.aliases():
            if time.monotonic() >= deadline:
                complete = False
                break
            if len(alias) >= len(row['old']):
                raise ref.Rejected('no graph-safe strictly shorter alias, including known fallback')
            if alias in reserved:
                continue
            proposed = dict(names)
            proposed[ordinal] = alias
            candidate, _ = apply(source, inventory, proposed)
            try:
                check(candidate, proposed, alias)
            except ref.Rejected as error:
                attempts.append({'ordinal': ordinal, 'alias': alias, 'accepted': False,
                                 'reason': str(error)})
                continue
            names = proposed
            attempts.append({'ordinal': ordinal, 'alias': alias, 'accepted': True})
            decisions.append({'ordinal': ordinal, 'function': functions[ordinal],
                              'old': row['old'], 'function_wide': row['new'], 'new': alias})
            if progress:
                accepted, accepted_edits = apply(source, inventory, names)
                progress({'candidate': accepted, 'edits': accepted_edits,
                          'declarations_done': len(decisions), 'parse_trials': len(attempts),
                          'complete': False, 'phase': 'accepted-greedy-step'})
            break
        if not complete:
            break
    candidate, edits = apply(source, inventory, names)
    if ref.inverse(candidate, edits) != source:
        raise ref.Rejected('exact physical inverse changed')
    after_diagnostics = check(candidate, names)
    if (HERE / 'inputs.json').read_bytes() != admission_raw:
        raise ref.Rejected('admission bytes changed during source experiment')
    return candidate, {'policy': admission['policy'], 'complete': complete,
        'elapsed_seconds': time.monotonic()-started,
        'soft_budget_seconds': admission['soft_budget_seconds'], 'input_bytes': len(source),
        'input_sha256': sha(source), 'function_wide_bytes': len(baseline),
        'function_wide_sha256': sha(baseline), 'candidate_bytes': len(candidate),
        'candidate_sha256': sha(candidate), 'raw_saved_from_function_wide': len(baseline)-len(candidate),
        'decisions': decisions, 'attempts': attempts, 'edits': edits,
        'position_bound_inverse_exact': True, 'reparse_binding_graph_equal': True,
        'protected_declaration_shapes_equal': True, 'diagnostics': diagnostics,
        'candidate_diagnostics': after_diagnostics, 'native_codec_engine_executions': 0}
