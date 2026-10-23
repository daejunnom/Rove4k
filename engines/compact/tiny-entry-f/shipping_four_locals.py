"""Four fixed full-F local spellings, after the return-keyword stage.

The exact four declarations/fourteen physical tokens were proved with the
project's real AST binding graph. Three fixed MOVE/PROMO argument bridges
retain the owned pure macro definitions; no stringification/token paste is
present. All251 declaration shapes except these names and2310 reference edges
remain equal. This is a closed replay, not a regex renamer or allocator.
DEV and actual optional policies bypass it; explicit full_reference applies it.
No AST, report, experiment, historical output or file is a function input.
"""
import ast
import hashlib

INPUT=(8167,'d9cb34ee6302822ab5a1b399039809d10be74cf69d50cc0ba3a14ecbdac6e86a')
OUTPUT=(8153,'62784180e34291403f2ad32a314bd83fb9de9167d820960ffe0099402879a8dc')
COMPLEMENT=(8139,'f68ab407375d210ec1820afd344ca7d0e59a523a3064076377dc0f415b7f78d8')
EDITS=((2264,2264,b'zA',b'c'),(2269,2268,b'to',b'g'),
       (2288,2286,b'to',b'g'),(2362,2359,b'zA',b'c'),(2365,2361,b'to',b'g'),
       (5090,5085,b'yk',b'b'),(5271,5265,b'yk',b'b'),(5345,5338,b'yk',b'b'),
       (5365,5357,b'yk',b'b'),(5399,5390,b'yk',b'b'),(5413,5403,b'yk',b'b'),
       (5491,5480,b'yk',b'b'),(6034,6022,b'fb',b'b'),(6060,6047,b'fb',b'b'))

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)

def _rewrite(source,inverse=False):
    _need(type(source)is bytes and _pin(source)==(OUTPUT if inverse else INPUT),
          'fixed full-F four-local source differs')
    parts=[];gaps=[];cursor=0
    for a,b,old,new in EDITS:
        start,expected,replacement=(b,new,old)if inverse else(a,old,new)
        _need(start>=cursor and source[start:start+len(expected)]==expected,
              'fixed local declaration/reference span differs')
        gap=source[cursor:start];parts.extend((gap,replacement));gaps.append(gap)
        cursor=start+len(expected)
    parts.append(source[cursor:]);gaps.append(source[cursor:]);result=b''.join(parts)
    _need(_pin(result)==(INPUT if inverse else OUTPUT)and _pin(b''.join(gaps))==COMPLEMENT,
          'fixed local output/protected complement differs')
    return result

def restore_source(source):return _rewrite(source,True)

def transform_source(source):
    result=_rewrite(source)
    _need(restore_source(result)==source,'fixed local full inverse differs')
    return result,{'family':'F','policy':'full-fixed2','stage':'four-locals-after-return',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'bindings':4,'physical_edits':14,'macro_arguments':3,'raw_source_delta':-14,
        'protected_gaps':15,'protected_bytes':COMPLEMENT[0],
        'protected_sha256':COMPLEMENT[1],'full_inverse':True,
        'canonical_DEV_actual_optional_changed':False,'external_reads':0}

def source_literal(source,previous):
    """Restore8167 and consume the actual return/successor/common literal chain."""
    restored=restore_source(source);expression,kind=previous(restored)
    _need(ast.literal_eval(expression)==restored,'previous F literal differs')
    old=restored.decode('ascii');new=source.decode('ascii')
    _need(expression.count(old)==1,'previous raw literal interior differs')
    result=expression.replace(old,new,1)
    _need(result.count(new)==1 and result.replace(new,old,1)==expression and ast.literal_eval(result)==source,
          'four-local literal inverse/restoration differs')
    return result,kind
