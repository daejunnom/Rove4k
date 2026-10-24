"""Exact B full-shipping overlong-line drain stage after clock presence.

Pure bytes only; no file, recipe, artifact, process, compiler or codec inputs.
The sole span preserves getchar order/count and terminal LF/EOF admission;
any nonterminal byte causes the same full drain/discard. DEV bypass belongs
to the caller. Only the fixed full B source domain below is admitted.
"""
import hashlib

INPUT = (10565, '6124424eff02466a28e900ca7abf0f8ff36f74d39de020e4c83b6909b95387cf')
OUTPUT = (10548, 'd91416e56e2b7716b9df2bec5db22c1f9d3f6ded5598d80741d68487ecc09bbb')
OFFSET = 10056
OLD = br"int n=getchar();if(n!=EOF&&n!='\n'){do{n=getchar();}while(n!=EOF&&n!='\n');continue;}"
NEW = br"int n,bad=0;while((n=getchar())!=EOF&&n!='\n')bad=1;if(bad)continue;"
COMPLEMENT = (10480, '795960b37e4950d6fb298ab8b6e7778128d3ce1f53e26a4d99d1a4f336334902')


def _pin(data):
    return len(data), hashlib.sha256(data).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def transform_source(source):
    """Apply the sole admitted B85-to68-byte drain composition."""
    _require(type(source) is bytes and _pin(source) == INPUT,
             'B line-drain input bytes/SHA-256 differs')
    _require(source.count(OLD) == 1 and source[OFFSET:OFFSET+len(OLD)] == OLD,
             'B line-drain unique fixed old span differs')
    head, tail = source[:OFFSET], source[OFFSET+len(OLD):]
    _require(_pin(head+tail) == COMPLEMENT, 'B line-drain complement differs')
    candidate = head + NEW + tail
    _require(_pin(candidate) == OUTPUT and candidate.count(NEW) == 1,
             'B line-drain output bytes/SHA-256 or unique new span differs')
    _require(candidate[:OFFSET] == head and candidate[OFFSET+len(NEW):] == tail,
             'B line-drain protected source gaps differ')
    _require(candidate[OFFSET:OFFSET+len(NEW)] == NEW and
             candidate[:OFFSET]+OLD+candidate[OFFSET+len(NEW):] == source,
             'B line-drain exact inverse differs')
    return candidate, {
        'stage': 'B fixed full-shipping line drain after clock presence',
        'input_bytes': INPUT[0], 'input_sha256': INPUT[1],
        'output_bytes': OUTPUT[0], 'output_sha256': OUTPUT[1],
        'offset': OFFSET, 'old_bytes': len(OLD), 'new_bytes': len(NEW),
        'each_gap_exact': True, 'exact_inverse': True,
        'complement_bytes': COMPLEMENT[0], 'complement_sha256': COMPLEMENT[1],
        'declared_policy': 'same getchar sequence and terminal LF/EOF; '
                           'nonterminal-byte presence selects full drain/discard',
    }
