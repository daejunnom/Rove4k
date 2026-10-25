"""Exact reviewed query/made-child fragment composition, no compiler."""
import hashlib


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def produce(control, recipe):
    candidate = dict(control)
    for name, raw in control.items():
        if sha(raw) != recipe['source_sha256']['control/'+name]:
            raise ValueError('exact current control source differs: '+name)
    for row in recipe['changes']:
        name, old, new = row['file'], row['old'].encode(), row['new'].encode()
        if candidate[name].count(old) != 1:
            raise ValueError('one exact reviewed old fragment required: '+name)
        candidate[name] = candidate[name].replace(old, new, 1)
    inverse = dict(candidate)
    for row in reversed(recipe['changes']):
        name, old, new = row['file'], row['old'].encode(), row['new'].encode()
        if inverse[name].count(new) != 1:
            raise ValueError('one exact reviewed inverse fragment required: '+name)
        inverse[name] = inverse[name].replace(new, old, 1)
    if inverse != control:
        raise ValueError('reviewed literal inverse/complement differs')
    for name, raw in candidate.items():
        expected = recipe['candidate_source_expected'][name]
        if len(raw) != expected['bytes'] or sha(raw) != expected['sha256']:
            raise ValueError('only the reviewed exact candidate is admitted: '+name)
    return candidate
