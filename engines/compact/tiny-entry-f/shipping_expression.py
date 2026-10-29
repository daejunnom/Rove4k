"""Pure fixed full-F scalar-expression compaction; no IO or policy changes.

Three move-mask initializer expressions and one continuation subscript lose
redundant parentheses.  One MTD assignment loses its enclosing braces without
changing the else binding.  Y is exactly typedef unsigned, so the cast has the
same type.  On the admitted Linux x86-64 compiler, unsigned is 32 bits: the TT
clear index uses 0..262143 and terminates at 262144, preserving all addresses
without wraparound when size_t is replaced with Y.  Native equality is checked
by the producer; this transform itself does not qualify runtime behavior.
"""
import ast,hashlib
INPUT=(7740, 'f99f1c48e8a77d1f9483b09d46f2d68f7b1e92ea94dd437d708cc3e5a10dcfa9')
OUTPUT=(7712, '546df93f9d7f6e6f8b8bdf76b8e3d5e7f9c92913f33db7bd77deec8d50bef20e')
EDITS=((1766, 1766, b'((m)&119)', b'm&119'), (3848, 3844, b'(unsigned)p->a', b'(Y)p->a'), (4018, 4007, b'((m)&119)', b'm&119'), (4115, 4100, b'w->i[g][(p->b[L]+6)]', b'w->i[g][p->b[L]+6]'), (4388, 4371, b'((m)&119)', b'm&119'), (5013, 4992, b'if(q<i){f=q;}else{d=q;if(j)b=j;}', b'if(q<i)f=q;else{d=q;if(j)b=j;}'), (6194, 6171, b'for(size_t i=0;i<(1<<18);i++)', b'for(Y i=0;i<(1<<18);i++)'))
GAPS=((0, 0, 1766, '64575069b0eb0108fc131d442087304b864859f5ec8a8e7c22d958352d84f46c'), (1775, 1771, 2073, 'db7f7add821736a86b8206caa644779f738a8396418161bac586118297efa409'), (3862, 3851, 156, '42f4a806aca4210b538e855f1912004a6457edd170889b6f51f2793ef513134b'), (4027, 4012, 88, '28984ef32ebbe32d91fad96b1579e5c8ebc79428e102063672b3648489cde3ef'), (4135, 4118, 253, '8b67613267f79c6aa7f743644c104e13f5dd0d5cb45155316fb1b155d505ca1b'), (4397, 4376, 616, '292dc7d26fd7f605d979b0edc1bcaa8798964d7b900d0b071ff5401ce1dccab7'), (5045, 5022, 1149, '674add83845ccd8ab68b77a2b3dcb983794e461b54a2f3bd4b8dd80c81e97db2'), (6223, 6195, 1517, 'cda987e461de8340a4516b15c7cff9f6c6c93ec886e5839751ca0bb01da460d0'))


def pin(data):return len(data),hashlib.sha256(data).hexdigest()

def rewrite(source,inverse=False):
 if type(source)is not bytes or pin(source)!=(OUTPUT if inverse else INPUT):raise ValueError('fixed full-F expression input differs')
 result=source
 for a,b,old,new in reversed(EDITS):
  at,before,after=(b,new,old)if inverse else(a,old,new)
  if source[at:at+len(before)]!=before:raise ValueError('fixed full-F expression span differs')
  result=result[:at]+after+result[at+len(before):]
 if pin(result)!=(INPUT if inverse else OUTPUT):raise ValueError('fixed full-F expression output differs')
 return result

def restore_source(source):return rewrite(source,True)

def transform_source(source):
 result=rewrite(source)
 if restore_source(result)!=source:raise ValueError('fixed full-F expression full inverse differs')
 for a,b,n,h in GAPS:
  if source[a:a+n]!=result[b:b+n]or pin(source[a:a+n])!=(n,h):raise ValueError('fixed full-F expression protected gap differs')
 return result,{'stage':'late-full-F-scalar-expression-compaction','input':INPUT,'output':OUTPUT,'raw_delta':-28,'spans':len(EDITS),'protected_gaps':len(GAPS),'full_inverse':True,'target':'Linux x86-64 unsigned32','table_index_range':[0,262143],'table_termination_index':262144,'engine_policy_unchanged':True,'runtime_qualified':False}

def source_literal(source,previous):
 original=restore_source(source);expression,kind=previous(original)
 if ast.literal_eval(expression)!=original:raise ValueError('actual prior full-F expression literal differs')
 old,new=original.decode('ascii'),source.decode('ascii')
 if expression.count(old)!=1:raise ValueError('one full-F expression literal required')
 result=expression.replace(old,new,1)
 if result.replace(new,old,1)!=expression or ast.literal_eval(result)!=source:raise ValueError('full-F expression literal inverse differs')
 return result,kind
