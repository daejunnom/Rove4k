"""Fixed shipping literal-header gap compaction; DEV bypass is caller-owned.

Only the space between include and a literal angle-header is removed. Header
bytes/order, newlines, macro/conditional directives and all code stay exact.
A is deliberately excluded after its measured complete-file loss. F MoveTT
is admitted as a raw-source reduction with unchanged complete-file size.
No external cost artifact or source is read during ordinary builds.
"""
import hashlib

CASES = {('B', 'full'): ((10595, '036d9c1aaec37b68508ec76ea335e77775d486bf4141dd7d4e94698a6313e33b'),
                 (10588, '13f1b0d74752f7aa2743616ad6465d1ee8e1497d70da7d3db242e38bdccc5c3b'),
                 ((33, 33, b'#include <stdint.h>', b'#include<stdint.h>'),
                  (53, 52, b'#include <stdatomic.h>', b'#include<stdatomic.h>'),
                  (76, 74, b'#include <pthread.h>', b'#include<pthread.h>'),
                  (97, 94, b'#include <stdlib.h>', b'#include<stdlib.h>'),
                  (117, 113, b'#include <stdio.h>', b'#include<stdio.h>'),
                  (136, 131, b'#include <string.h>', b'#include<string.h>'),
                  (156, 150, b'#include <time.h>', b'#include<time.h>'))),
 ('C', 'full'): ((10123, '0eeee8fd2c976cd5a0221365e1765ad01714c68609183381ea19eb8f4b3118ff'),
                 (10114, 'fde89cdc49ef55d075343cd2480a5e65a02d18e94884271890b579ae60e93304'),
                 ((33, 33, b'#include <stdint.h>', b'#include<stdint.h>'),
                  (53, 52, b'#include <stdatomic.h>', b'#include<stdatomic.h>'),
                  (76, 74, b'#include <pthread.h>', b'#include<pthread.h>'),
                  (97, 94, b'#include <stdlib.h>', b'#include<stdlib.h>'),
                  (117, 113, b'#include <stdio.h>', b'#include<stdio.h>'),
                  (136, 131, b'#include <string.h>', b'#include<string.h>'),
                  (156, 150, b'#include <time.h>', b'#include<time.h>'),
                  (175, 168, b'#include <limits.h>', b'#include<limits.h>'),
                  (3887, 3879, b'#include <immintrin.h>', b'#include<immintrin.h>'))),
 ('E', 'full'): ((10477, '1bf5ca54da0a0ae5ae7c96deabf3830bace04db821c56fd9759c35e317da7436'),
                 (10470, '5a3352258412593216641c095762a3171a40a0f3e4d02fa434f67824281b1012'),
                 ((33, 33, b'#include <stdint.h>', b'#include<stdint.h>'),
                  (53, 52, b'#include <stdatomic.h>', b'#include<stdatomic.h>'),
                  (76, 74, b'#include <pthread.h>', b'#include<pthread.h>'),
                  (97, 94, b'#include <stdlib.h>', b'#include<stdlib.h>'),
                  (117, 113, b'#include <stdio.h>', b'#include<stdio.h>'),
                  (136, 131, b'#include <string.h>', b'#include<string.h>'),
                  (156, 150, b'#include <time.h>', b'#include<time.h>'))),
 ('F', 'full'): ((8966, '298f9b9670f7de293e99e56a6c9b7532b29e009fd7f38f90751845f9d675d85b'),
                 (8959, '601ea9b983a6b86fa74ff09555d2c9349433b9b0d7c664c636fb87aa19316acf'),
                 ((33, 33, b'#include <stdint.h>', b'#include<stdint.h>'),
                  (53, 52, b'#include <stdatomic.h>', b'#include<stdatomic.h>'),
                  (76, 74, b'#include <pthread.h>', b'#include<pthread.h>'),
                  (97, 94, b'#include <stdlib.h>', b'#include<stdlib.h>'),
                  (117, 113, b'#include <stdio.h>', b'#include<stdio.h>'),
                  (136, 131, b'#include <string.h>', b'#include<string.h>'),
                  (156, 150, b'#include <time.h>', b'#include<time.h>'))),
 ('F', 'material-noise'): ((8545, '918a6837918d83d692c816062063c4085e847efb897c74eea68ce850c77f6fd2'),
                           (8538, '95b9c72aa25e10bdafdad338e3a8e067d545741086329d4348efeadca0c48fd1'),
                           ((33, 33, b'#include <stdint.h>', b'#include<stdint.h>'),
                            (53, 52, b'#include <stdatomic.h>', b'#include<stdatomic.h>'),
                            (76, 74, b'#include <pthread.h>', b'#include<pthread.h>'),
                            (97, 94, b'#include <stdlib.h>', b'#include<stdlib.h>'),
                            (117, 113, b'#include <stdio.h>', b'#include<stdio.h>'),
                            (136, 131, b'#include <string.h>', b'#include<string.h>'),
                            (156, 150, b'#include <time.h>', b'#include<time.h>'))),
 ('F', 'material-move-tt'): ((7778, 'e94399e7bec9ab24d6bc144986e38033bf0db92e89427bbea955a0839155517b'),
                             (7771, 'e1f4e4069ed0fd69d27034cff49c09e890cd18db97905d881d69507141b55505'),
                             ((33, 33, b'#include <stdint.h>', b'#include<stdint.h>'),
                              (53, 52, b'#include <stdatomic.h>', b'#include<stdatomic.h>'),
                              (76, 74, b'#include <pthread.h>', b'#include<pthread.h>'),
                              (97, 94, b'#include <stdlib.h>', b'#include<stdlib.h>'),
                              (117, 113, b'#include <stdio.h>', b'#include<stdio.h>'),
                              (136, 131, b'#include <string.h>', b'#include<string.h>'),
                              (156, 150, b'#include <time.h>', b'#include<time.h>')))}

def transform_source(source, *, family, policy='full'):
    """Compact only frozen literal header gaps; preserve every other byte."""
    before, after, edits = CASES[(family, policy)]
    if type(source) is not bytes or (len(source), hashlib.sha256(source).hexdigest()) != before:
        raise ValueError('include forms input differs from fixed late source')
    pieces=[];gaps=[];cursor=target_cursor=0
    for start,target,old,new in edits:
        if start<cursor or source[start:start+len(old)]!=old:
            raise ValueError('include forms literal differs')
        gap=source[cursor:start]
        if target_cursor+len(gap)!=target:
            raise ValueError('include forms target differs')
        pieces.extend((gap,new));gaps.append(gap)
        cursor=start+len(old);target_cursor=target+len(new)
    pieces.append(source[cursor:]);gaps.append(source[cursor:]);candidate=b''.join(pieces)
    if (len(candidate),hashlib.sha256(candidate).hexdigest())!=after:
        raise ValueError('include forms output differs')
    inverse=candidate;new_gaps=[];cursor=0
    for start,target,old,new in edits:
        if candidate[target:target+len(new)]!=new:
            raise ValueError('include forms candidate span differs')
        new_gaps.append(candidate[cursor:target]);cursor=target+len(new)
    new_gaps.append(candidate[cursor:])
    for start,target,old,new in reversed(edits):
        inverse=inverse[:target]+old+inverse[target+len(new):]
    if inverse!=source or gaps!=new_gaps:
        raise ValueError('include forms inverse/complement differs')
    remainder=b''.join(gaps)
    return candidate,dict(stage='late-literal-include-gap',family=family,policy=policy,
        input_bytes=before[0],input_sha256=before[1],output_bytes=after[0],output_sha256=after[1],
        literal_include_gaps=len(edits),exact_inverse=True,complement_bytes=len(remainder),
        complement_sha256=hashlib.sha256(remainder).hexdigest(),
        external_reads=0,compiler_codec_engine_executed_by_transform=0)
