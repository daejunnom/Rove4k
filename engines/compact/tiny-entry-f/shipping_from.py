"""Pure full-F FROM exact expansion; all prior literal guards are consumed.
Three unsigned local m arguments retain one evaluation and exact parentheses.
Canonical/DEV and optional selected source pipelines bypass this stage.
"""
import ast
import hashlib
INPUT=(7905, '04e5472a5970a87ca784a71fa8a6ce483fa728e254ca45bc71e9de638b54bec7')
OUTPUT=(7885, '47419319e3bfa0eb0e43a9ced1705c7f6283218af8a92157bda47c49ac2dd852')
EDITS=((313, 313, b'#define FROM(m) ((m)&119)\n', b''), (1808, 1782, b'FROM(m)', b'((m)&119)'), (4086, 4062, b'FROM(m)', b'((m)&119)'), (4454, 4432, b'FROM(m)', b'((m)&119)'))
GAPS=((0, 0, 313, '2a8dbe6f9f4c32d738957176c49016dedd30e93c535faf37f1e6134b15cfc4fd'), (339, 313, 1469, '390fb02e9f47e088de8b240f7f5182e60de111c36c8034687da9115a0324531e'), (1815, 1791, 2271, '8d31b788b5adfefbb1de4b21a1219342e43741fec5a68ad6ea840857f090b92b'), (4093, 4071, 361, '3ea44471ae160f0afaa702019f4d30b8992edcdab79c1b460306d55a0d18c926'), (4461, 4441, 3444, 'aaed495aeaa2cdbf961439580c72be2d371908e29eacabfcfb69663f568d5c81'))
METADATA={'stage': 'late-full-F-FROM-macro-exact-inline', 'input': (7905, '04e5472a5970a87ca784a71fa8a6ce483fa728e254ca45bc71e9de638b54bec7'), 'output': (7885, '47419319e3bfa0eb0e43a9ced1705c7f6283218af8a92157bda47c49ac2dd852'), 'raw_delta': -20, 'spans': 4, 'protected_gaps': 5, 'full_inverse': True, 'definition_removed': 1, 'exact_fixed_calls': 3, 'unsigned_local_m_single_evaluation': True, 'header_CPP_and_native_whole_identity_observed_separately': True, 'other_macros_and_atomics_unchanged': True, 'canonical_DEV_optional_outputs_untouched': True, 'runtime_qualified': False}

def _pin(b):return len(b),hashlib.sha256(b).hexdigest()
def _rewrite(source,inverse=False):
 if type(source)is not bytes or _pin(source)!=(OUTPUT if inverse else INPUT):raise ValueError('fixed FROM exact inline input differs')
 result=source
 for a,b,old,new in reversed(EDITS):
  at,old,new=(b,new,old)if inverse else(a,old,new)
  if source[at:at+len(old)]!=old:raise ValueError('fixed FROM exact inline span differs')
  result=result[:at]+new+result[at+len(old):]
 if _pin(result)!=(INPUT if inverse else OUTPUT):raise ValueError('fixed FROM exact inline output differs')
 return result
def restore_source(source):return _rewrite(source,True)
def transform_source(source):
 result=_rewrite(source)
 if restore_source(result)!=source:raise ValueError('full FROM exact inline inverse differs')
 for a,b,n,h in GAPS:
  if source[a:a+n]!=result[b:b+n]or _pin(source[a:a+n])!=(n,h):raise ValueError('FROM exact inline gap differs')
 return result,dict(METADATA)
def source_literal(source,previous):
 original=restore_source(source);expression,kind=previous(original)
 if ast.literal_eval(expression)!=original:raise ValueError('actual prior FROM exact inline literal differs')
 old,new=original.decode('ascii'),source.decode('ascii')
 if expression.count(old)!=1:raise ValueError('one FROM exact inline literal required')
 result=expression.replace(old,new,1)
 if result.replace(new,old,1)!=expression or ast.literal_eval(result)!=source:raise ValueError('FROM exact inline literal inverse differs')
 return result,kind
