"""Fixed Ffull ASCII digit guard and Linux readonly-open spelling.

The source entry accepts only actual post-local-rank C, before any Python raw
literal insertion. Null short circuit and one char load stay; with ASCII48,
int32 and unsigned32, (unsigned)(v-48) == v-48u modulo2**32. The strtoull/end/
63-bit guard and all clock/parser/worker consumers remain protected bytes.
The template entry accepts only the full prepared947-byte marker template,
before embedding C. Standard os.O_RDONLY is0 on the selected Linux ABI.
Path, FD lifetime, signal/Popen/group cleanup, argv/stdin/stderr stay exact.
Python bytecode/source/attribute/traceback and timing observations are outside
this spelling contract; no OS-generic or arbitrary binding claim is made.
Canonical/DEV, optional selected products and F8 bypass both late transforms.
No files, environment, compiler, codec, report or network are consulted.
"""
import hashlib

SOURCE_INPUT=(8509,'a2d094c954ca7e0d02d38e0810c62c9fc8e754a536ee7770bc98214dee7d3142')
SOURCE_OUTPUT=(8497,'08532c38268ecf4691890a13529d09227a76eadb039813d3bb6f886170966954')
SOURCE_START=7251
SOURCE_OLD=b"if(!s||(unsigned)(*s-'0')>9)return 0;"
SOURCE_NEW=b'if(!s||*s-48u>9)return 0;'
SOURCE_GAPS=((7251,'762d33d008c1b3aa00b94b544cd0164ab7e9afb8d1d63ef95410c33c837db3f6'),
             (1221,'f6cefe45ee77c772e16d02bb7346504cae806f801fcd56b97abb108cc763ca5c'))
TEMPLATE_INPUT=(947,'7719272010d58735a2768064ce4b30733b8eed4a96488864a111030da7cab533')
TEMPLATE_OUTPUT=(937,'bad1dfa1a3af76d75a40f2508de5a864ec0449a5c576e902d8e0e895c4300d2a')
TEMPLATE_START=832
TEMPLATE_OLD=b"fd=os.open(d+'/x',os.O_RDONLY)"
TEMPLATE_NEW=b"fd=os.open(d+'/x',0)"
TEMPLATE_GAPS=((832,'31e311583854400a6efac186cdac98ce15ecf159464bd9fa20299295d4b86982'),
               (85,'ea71ccb4c92908e177cf823351f01ff598e603b862214871dfd72a88ef94cd8a'))


def _pin(data):return len(data),hashlib.sha256(data).hexdigest()


def _transform(data,expected,result_pin,start,old,new,gap_pins,stage):
    if type(data) is not bytes or _pin(data)!=expected:
        raise ValueError('fixed F digit/FD '+stage+' input differs')
    end=start+len(old)
    if data.count(old)!=1 or data[start:end]!=old:
        raise ValueError('fixed F digit/FD '+stage+' span differs')
    gaps=(data[:start],data[end:]);result=gaps[0]+new+gaps[1]
    if (tuple(map(_pin,gaps))!=gap_pins or _pin(result)!=result_pin
            or result.count(new)!=1 or result[start:start+len(new)]!=new
            or (result[:start],result[start+len(new):])!=gaps
            or result[:start]+old+result[start+len(new):]!=data):
        raise ValueError('fixed F digit/FD '+stage+' output/gaps/inverse differs')
    return result,{'family':'F','policy':'full-fixed2','stage':stage,
        'input_bytes':expected[0],'input_sha256':expected[1],
        'output_bytes':result_pin[0],'output_sha256':result_pin[1],
        'raw_delta':len(new)-len(old),'edits':1,'gaps':2,
        'full_inverse':True,'all_gaps_equal':True,'external_reads':0}


def transform_source(source):
    """One actual C guard after local_rank; not a bootstrap raw-literal edit."""
    return _transform(source,SOURCE_INPUT,SOURCE_OUTPUT,SOURCE_START,
                      SOURCE_OLD,SOURCE_NEW,SOURCE_GAPS,'ASCII-digit-after-local-rank')


def transform_template(template):
    """Full prepared marker template only, before source literal insertion."""
    return _transform(template,TEMPLATE_INPUT,TEMPLATE_OUTPUT,TEMPLATE_START,
                      TEMPLATE_OLD,TEMPLATE_NEW,TEMPLATE_GAPS,'Linux-readonly-full-template')
