"""Actual raw PP/inverse and macro/header freshness; no native build or execution."""
from collections import Counter
import hashlib
import json
import re
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def inverse(data, aliases, lexer):
    text = data.decode()
    parts, offset, counts = [], 0, Counter()
    for start, end, word in lexer._identifier_spans(text):
        if word in aliases:
            parts.extend((text[offset:start], aliases[word]))
            offset = end
            counts[word] += 1
    parts.append(text[offset:])
    return ''.join(parts).encode(), dict(counts)


def verify(before, candidate, directory, *, alpha, storage, lexer):
    directory.mkdir()
    af, sf = json.loads(alpha.POLICY_BYTES), json.loads(storage._POLICY_BYTES)
    mapping = {**af['mapping'], **sf['mapping']}
    aliases = {value: key for key, value in mapping.items()}
    require(len(mapping) == len(aliases) == 49, 'unchanged 31+18 aliases must all remain reserved')
    restored, raw_counts = inverse(candidate, aliases, lexer)
    (directory/'inverse-source.c').write_bytes(restored)
    require(restored == before, 'raw source inverse differs')
    observations = []
    outputs = {}
    for label, data in (('before', before), ('candidate', candidate)):
        for kind, flags in (('pp', ['-E', '-P']), ('macros', ['-E', '-dM'])):
            command = ['cc', '-Os', '-x', 'c', *flags, '-']
            process = subprocess.run(command, input=data, capture_output=True, timeout=30)
            (directory/(label+'.'+kind)).write_bytes(process.stdout)
            (directory/(label+'.'+kind+'.stderr')).write_bytes(process.stderr)
            observations.append({'label': label, 'kind': kind, 'argv': command,
                'returncode': process.returncode, 'bytes': len(process.stdout), 'sha256': sha(process.stdout),
                'stderr_bytes': len(process.stderr), 'stderr_sha256': sha(process.stderr)})
            (directory/'commands.json').write_text(json.dumps(observations, indent=2)+'\n')
            require(process.returncode == 0 and not process.stderr, 'actual '+label+' '+kind+' failed')
            outputs[label, kind] = process.stdout
    words = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
    header_conflicts = sorted(set(aliases) & set(words.findall(outputs['before', 'pp'].decode())))
    macro_conflicts = sorted(set(aliases) & set(words.findall(outputs['before', 'macros'].decode())))
    require(not header_conflicts and not macro_conflicts, 'alias collision in actual full headers/macro environment')
    inverse_pp, pp_counts = inverse(outputs['candidate', 'pp'], aliases, lexer)
    (directory/'inverse.pp').write_bytes(inverse_pp)
    require(inverse_pp == outputs['before', 'pp'], 'actual raw PP inverse is not byte-identical')
    require(outputs['before', 'macros'] == outputs['candidate', 'macros'], 'actual macro dump changed')
    result = {'complete': True, 'raw_source_inverse_exact': True, 'actual_raw_PP_inverse_exact': True,
        'actual_macro_dumps_identical': True, 'all_49_aliases_reserved': True,
        'actual_full_PP_header_alias_conflicts': header_conflicts, 'actual_macro_alias_conflicts': macro_conflicts,
        'inverse_source_sha256': sha(restored), 'inverse_PP_sha256': sha(inverse_pp),
        'raw_inverse_counts': raw_counts, 'PP_inverse_counts': pp_counts,
        'actual_commands': observations, 'native_compilations': 0, 'engine_runs': 0}
    (directory/'checks.json').write_text(json.dumps(result, indent=2)+'\n')
    return result
