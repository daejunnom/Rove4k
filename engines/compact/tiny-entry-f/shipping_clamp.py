"""Express the full-F local correction clamp with one assignment.

The plain, non-escaping int has the same value for every representable int.
In-range assignment has no observer. All guards, learners and full-F features
are outside this span. DEV bypass and separate optional references are caller
responsibilities. This pure stage reads no receipt or external source.
"""
import hashlib

INPUT=(8939,'53f3326c9062601fa037212f853c91c34cd1b36a076a571d8e1f52624514e08c')
OUTPUT=(8933,'cc8ef7dab0e35e2a62fee66d427eab09698e6eeebfa6eed3abb0e20d20b1a0a1')
OFFSET=6004
OLD=b'if(l>256)l=256;if(l< -256)l=-256;'
NEW=b'l=l>256?256:l< -256?-256:l;'
COMPLEMENT=(8906,'90bf520b7f92682ebd7c762694d733be9c4d2015b780adc70bff81b5a8d8a2a9')


def _pin(data):
    return len(data),hashlib.sha256(data).hexdigest()


def transform_source(source):
    """Admit the measured full-default input; preserve every complementary byte."""
    if type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('full-F correction clamp input differs')
    prefix=source[:OFFSET];suffix=source[OFFSET+len(OLD):]
    if source[OFFSET:OFFSET+len(OLD)]!=OLD or source.count(OLD)!=1:
        raise ValueError('full-F correction clamp literal differs')
    if _pin(prefix+suffix)!=COMPLEMENT:
        raise ValueError('full-F correction clamp complement differs')
    candidate=prefix+NEW+suffix
    if (_pin(candidate)!=OUTPUT
            or candidate[:OFFSET]+OLD+candidate[OFFSET+len(NEW):]!=source):
        raise ValueError('full-F correction clamp output or inverse differs')
    return candidate,{
        'family':'F','policy':'full','stage':'local-correction-clamp-expression',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-6,'offset':OFFSET,'exact_inverse':True,
        'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'domain':'all int values; plain local with no address escape',
        'native_entire_bytes_equal_at_first_cost':True,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0,
    }
