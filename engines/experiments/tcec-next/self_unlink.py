"""Finite TCEC entry-owned unlink experiment, separate from old wrappers.

Only the six exact full 7f711448 TCEC C sources are admitted.  The wrapper must
exec its own private absolute regular-file output with that path as argv[0].
The new entry removes that name before allocating resources or starting workers;
failure returns status 2.  Source, submitted script and preserved native controls
are never removal targets.  Direct native testing requires a disposable copy.

The package remains five shell lines, so the old tail -n+6 stream boundary and
errexit/pipefail behavior are preserved.  No delayed cleanup child is started.
No full profile/default is selected by this experiment.
"""

from hashlib import sha256
import re

SCHEMA = 'rove4k.tcec-entry-self-unlink.v1'
PROFILES = {
    'A': (7869, '248479972fb803223e353b37fbe85f95248d469b4c1c3382babeb15625b0aa72', 'L', 'J'),
    'B': (8770, '23d9de0788b0058c0a11744290bdf2d39582b16d6af48501d9021bbb57f54bfe', 'I', 'l'),
    'C': (8486, 'ade8c284fdc5e116e6efd5607a18ba018dbdabf4110675d5eb920eb50fd6aa15', 'int', 'return'),
    'E': (8063, '80f7c14239baffca5ab1cca8a2f4777691f3dfc7d068b511dc022332590889e5', 'L', 'J'),
    'F': (6901, '46bd9a21026afb7e289acbec67078235563534685f9413fbb989664f7728ea22', 'S', 'H'),
    'F8': (7049, 'ef538c8d400dcb0fb50e16a4e80886ff7ef192ea4d44a480d49031d71c109e5e', 'S', 'H'),
}
VARIANTS = ('return-short', 'exit-short', 'return-long', 'exit-long')
OLD_CLEANUP_LINE = b'(sleep 1;python3 -c \'import os;os.unlink(input())\'<<<"$f")&exec "$f"\n'
NEW_EXEC_LINE = b'exec "$f"\n'


def pin(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def _change(family, variant):
    if family not in PROFILES or variant not in VARIANTS:
        raise ValueError('explicit admitted family and unlink variant required')
    _, _, integer, returned = PROFILES[family]
    argc, argv = ('z0', 'z1') if variant.endswith('short') else ('argc', 'argv')
    failure = returned + ' 2' if variant.startswith('return') else 'exit(2)'
    old = b'main(void){'
    new = f'main({integer} {argc},char**{argv}){{if(remove(*{argv})){failure};'.encode('ascii')
    return old, new, (argc, argv)


def transform_source(source, *, family, variant='return-short'):
    old, new, parameters = _change(family, variant)
    size, digest, integer, _ = PROFILES[family]
    if type(source) is not bytes or (len(source), sha256(source).hexdigest()) != (size, digest):
        raise ValueError('unknown full TCEC source for entry-owned unlink')
    if source.count(old) != 1 or source.count(integer.encode() + b' ' + old) != 1:
        raise ValueError('unique admitted main signature missing')
    identifiers = set(re.findall(rb'[A-Za-z_][A-Za-z_0-9]*', source))
    if any(name.encode() in identifiers for name in (*parameters, 'remove')):
        raise ValueError('entry identifier collides with admitted source')
    offset = source.index(old)
    candidate = source[:offset] + new + source[offset + len(old):]
    proof = {
        'schema': SCHEMA, 'family': family, 'variant': variant,
        'input': pin(source), 'output': pin(candidate),
        'edit': {'input_begin': offset, 'output_begin': offset,
                 'before': pin(old), 'after': pin(new)},
        'protected_spans': [dict(input_begin=0, output_begin=0, **pin(source[:offset])),
                            dict(input_begin=offset + len(old), output_begin=offset + len(new),
                                 **pin(source[offset + len(old):]))],
        'full_inverse': True,
        'contract': {'argv0': 'wrapper-owned private absolute regular executable file',
                     'delete_target': 'argv[0] only, before original entry actions',
                     'unlink_failure_status': 2, 'direct_native': 'disposable copies only',
                     'unchanged': 'all original entry actions, chess/search/learner/clock/thread code'},
    }
    if candidate.replace(new, old, 1) != source:
        raise ValueError('entry-owned unlink inverse differs')
    return candidate, proof


def restore_source(candidate, proof):
    if proof.get('schema') != SCHEMA or pin(candidate) != proof.get('output'):
        raise ValueError('self-unlink output identity differs')
    old, new, _ = _change(proof.get('family'), proof.get('variant'))
    if candidate.count(new) != 1:
        raise ValueError('unique self-unlink entry missing')
    source = candidate.replace(new, old, 1)
    repeated, expected = transform_source(source, family=proof['family'], variant=proof['variant'])
    if repeated != candidate or expected != proof:
        raise ValueError('self-unlink full inverse/protected spans differ')
    return source


def source_edits(source, *, family, variant='return-short'):
    """Expose one original-coordinate edit only after exact base admission.

    The integrator owns admission, overlap checks, full inverse and provenance
    of the other independently admitted changes.  Apply this entry edit last,
    after checking its new identifiers against the approved composed body.
    """
    transform_source(source, family=family, variant=variant)
    old, new, _ = _change(family, variant)
    return ({'role': 'entry-self-unlink', 'begin': source.index(old),
             'before': old, 'after': new},)


def check_entry_context(source, *, family, variant='return-short'):
    """Collision/precondition check, not a source admission or transform API."""
    old, _, parameters = _change(family, variant)
    integer = PROFILES[family][2].encode('ascii')
    if type(source) is not bytes or source.count(integer + b' ' + old) != 1:
        raise ValueError('composed source lacks its unique admitted entry shape')
    identifiers = set(re.findall(rb'[A-Za-z_][A-Za-z_0-9]*', source))
    if any(name.encode() in identifiers for name in (*parameters, 'remove')):
        raise ValueError('composed source collides with entry-owned unlink identifiers')
    return True


def tcec_header(packaging, *, compiler=None, environment=None):
    """Retain the existing pipeline and five-line stream boundary exactly."""
    old = packaging.tcec_header(compiler=compiler, mode='pipe', environment=environment)
    if len(old.splitlines()) != 5 or old.count(OLD_CLEANUP_LINE) != 1 or not old.endswith(OLD_CLEANUP_LINE):
        raise ValueError('unknown minimal TCEC delayed-unlink header')
    new = old[:-len(OLD_CLEANUP_LINE)] + NEW_EXEC_LINE
    if len(new.splitlines()) != 5 or new.splitlines()[:4] != old.splitlines()[:4]:
        raise ValueError('self-unlink changed the decode/compile pipeline')
    return new


def package(packaging, source, compression, *, compiler=None, environment=None):
    return packaging.package(source, compression, prefix=tcec_header(
        packaging, compiler=compiler, environment=environment))


def contract(packaging, *, compiler=None, environment=None):
    result = packaging.tcec_contract(compiler=compiler, mode='pipe', environment=environment)
    if result['dependencies'][-2:] != ['sleep', 'python3']:
        raise ValueError('unknown delayed cleanup dependencies')
    result.update(policy='tcec-source-pipe-engine-unlink',
                  dependencies=result['dependencies'][:-2],
                  cleanup_owner='engine-entry', cleanup_delay_seconds=0, cleanup_seconds=60,
                  child_reaping='no-cleanup-child', private_absolute_regular_argv0=True,
                  unlink_failure_status=2, direct_native='disposable-copy-only')
    return result
