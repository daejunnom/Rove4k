"""Fixed full-F return-keyword dictionary, after valid-square successor.

The admitted source has42 return keyword tokens and no H identifier, including
its directives and quoted bytes. The physical ledger was checked token-wise;
all other bytes, including seven includes, existing S/MOVE macros and quoted
tokens, stay in protected gaps. The exact target CPP and entire native were
equal at first cost. Macro dumps, diagnostics and source locations differ;
this is not a general macro equivalence rule. Actual optional policies, DEV
and F8 bypass this stage; separate optional full_reference uses it explicitly.
No file, report, experiment, AST tool or process is an input to these functions.
"""
import ast
import hashlib
import re

INPUT=(8360,'b4e8f79615eb08c4d5dcb8db9e1cac76cecbef172f2096c64cafcebbc54cabf8')
OUTPUT=(8167,'d9cb34ee6302822ab5a1b399039809d10be74cf69d50cc0ba3a14ecbdac6e86a')
COMPLEMENT=(8108,'ce64daeb63d85acf49300ae5ae5265ec33b7b86c5a47bfa595e6f945624df575')
RETURN_OFFSETS=(664,859,1052,1089,1140,1469,1505,1543,1568,1578,1639,1747,
    1781,1936,2225,2293,2821,3141,3442,3548,3626,3680,3697,3831,3956,4328,
    4678,4869,4995,5112,5837,6112,6125,6566,6806,6920,6976,7023,7130,7161,
    7684,8349)
DEFINITION=b'#define H return\n'
EDITS=((167,167,b'',DEFINITION),)+tuple(
    (a,a+len(DEFINITION)-5*i,b'return',b'H')for i,a in enumerate(RETURN_OFFSETS))


def _pin(data):return len(data),hashlib.sha256(data).hexdigest()


def _need(ok,message):
    if not ok:raise ValueError(message)


def _rewrite(source,inverse=False):
    _need(type(source)is bytes and _pin(source)==(OUTPUT if inverse else INPUT),
          'fixed full-F return source differs')
    parts=[];gaps=[];cursor=0
    for a,b,old,new in EDITS:
        start,expected,replacement=(b,new,old)if inverse else(a,old,new)
        _need(start>=cursor and source[start:start+len(expected)]==expected,
              'fixed return token literal/offset differs')
        gap=source[cursor:start];parts.extend((gap,replacement));gaps.append(gap)
        cursor=start+len(expected)
    parts.append(source[cursor:]);gaps.append(source[cursor:]);result=b''.join(parts)
    _need(_pin(result)==(INPUT if inverse else OUTPUT)and _pin(b''.join(gaps))==COMPLEMENT,
          'fixed return output/protected complement differs')
    return result


def restore_source(source):return _rewrite(source,True)


def transform_source(source):
    _need(type(source)is bytes and _pin(source)==INPUT,'fixed full-F successor input differs')
    _need(re.search(rb'\bH\b',source)is None and
          tuple(m.start()for m in re.finditer(rb'\breturn\b',source))==RETURN_OFFSETS,
          'fixed fresh H/return physical roles differ')
    _need(source[:167].count(b'#include')==7 and source[167:181]==b'#define S int\n',
          'fixed seven-include/S insertion boundary differs')
    result=_rewrite(source)
    _need(restore_source(result)==source,'fixed return full inverse differs')
    return result,{'family':'F','policy':'full-fixed2','stage':'return-keyword-after-square-successor',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'return_tokens':42,'definition_bytes':17,'macro_insert_offset':167,'raw_source_delta':-193,
        'edits':43,'protected_gaps':44,'protected_bytes':COMPLEMENT[0],
        'protected_sha256':COMPLEMENT[1],'full_inverse':True,
        'canonical_DEV_actual_optional_F8_changed':False,'external_reads':0}


def source_literal(source,previous):
    """Restore8360, consume the actual previous guards, then forward the literal."""
    restored=restore_source(source)
    expression,kind=previous(restored)
    _need(ast.literal_eval(expression)==restored,'previous F literal did not restore exact successor source')
    old=restored.decode('ascii');new=source.decode('ascii')
    _need(expression.count(old)==1,'previous F raw source literal interior differs')
    result=expression.replace(old,new,1)
    _need(result.count(new)==1 and result.replace(new,old,1)==expression and ast.literal_eval(result)==source,
          'F return literal inverse/restoration differs')
    return result,kind
