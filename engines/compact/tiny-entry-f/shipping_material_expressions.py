"""Fixed material-F expression spelling after object/type/member names.

This is a pure byte transform, not a renamer or compiler. It accepts one full
8148-byte source and returns one8130-byte source. Four literal roles, opaque
literals/comments, every directive, inverse and all unchanged bytes are bound.
No Clang, report, fixture, executable, network or other source is an input.

C value equivalence in the qualified Linux int/unsigned32 profile:
* Merging int H;int K=... retains blockscope, uninitialized H and K's same
  initializer reads/order. H still receives the actual recursive result.
* Y m is unsigned. m*37 remains unsigned as with37u. Workerid .a is assigned
  d in fixed0<=d<2; signed a*19 is0..19 without overflow before the same unsigned
  addition. Generated m is17bit; sum<=4849646; modulo17 is0..16. Removing the
  explicit int conversion preserves this exact representable value.
* The enclosing conditional gains unsigned common type, but its TT1000000,
  capture499100..514400 and noise0..16 alternatives all fit int32 exactly at
  assignment. Unchanged promotion bonus<=405000 also leaves the sum representable.
* f==128-1 equals f==127. Starting at1, a<=128-2 equals a<127, admits1..126,
  and terminates at127 with no overflow. No policy/depth/stop/resource change.

Full/default and DEV admission are caller-owned branches and must bypass this
material-only stage. Source pins preserve the complete policy/input/runtime.
"""
import hashlib
import re
INPUT_BYTES=8148
INPUT_SHA256='5ee725c0e3d1479210ff023f6af75c965a421cf04645f9d60abc1ae7cedae91b'
OUTPUT_BYTES=8130
OUTPUT_SHA256='c63cf3d6216c9b9376c08a1f8ca753170b3b322536b31b39b45cf188ea3e2a47'
COMPLEMENT_BYTES=8085
COMPLEMENT_SHA256='25c1a62dff1972aac936c912e23e0b666e59ac80ca61d794cefec103079271ee'
REGIONS=({'new': 'f==127',
  'new_end': 4099,
  'new_sha256': '531fb72bf63913270ca06887bf363ef44bfb2934a649f53414a9f8b7df1ba6bc',
  'new_start': 4093,
  'old': 'f==128-1',
  'old_end': 4101,
  'old_sha256': 'f746c91e8aec7301248f8445c277058f97dc4ee6f036c436ae4efd8d6d88247f',
  'old_start': 4093,
  'role': 'exact ply guard'},
 {'new': 'int H,K=a<=0&&!n;',
  'new_end': 4230,
  'new_sha256': '4e739ac4a3b56fc2385eacc9e73fac1058cc3813e4c03623df565b2676c59bc3',
  'new_start': 4213,
  'old': 'int H;int K=a<=0&&!n;',
  'old_end': 4236,
  'old_sha256': 'e5a0489222701fb588a9dc3a714226a26b5380e852b0955acc4c2fe562da7ba4',
  'old_start': 4215,
  'role': 'adjacent int declarations'},
 {'new': '(m*37+w->a*19)%17',
  'new_end': 4372,
  'new_sha256': 'e7fd2fc692f36a87b98137c4cfa7c369c57b703c4b574c57f04eda036a687ea5',
  'new_start': 4355,
  'old': '(int)((m*37u+w->a*19u)%17)',
  'old_end': 4387,
  'old_sha256': '94c42911e1993bf45ddbfccf1a8145988f7d8a44a9bfa1c3d941d306cbe3ed51',
  'old_start': 4361,
  'role': 'bounded quiet noise cast/suffix'},
 {'new': 'a<127',
  'new_end': 4886,
  'new_sha256': '21609b78b233b0e3f759e4f873ae019465f3ceaae7a3160588a207e536c62be2',
  'new_start': 4881,
  'old': 'a<=128-2',
  'old_end': 4904,
  'old_sha256': '7bee00c8ad1ef89f5e1d2bfd97ac5fdd77f96d92c56fd26f30850e3c31e57e6a',
  'old_start': 4896,
  'role': 'same iterative depths'})
PROTECTED={'typedef unsigned Y;': 1, 'T[d].a=d;': 1, 'for(;d<2;d++)': 1, 'Y m=x[i];': 1, 'G=N(p->h,0)': 1, 'N(p->h,y);': 1, 'if(!R(w))return 0;': 1, 'if(atomic_load_explicit(&F,memory_order_relaxed))return 0;': 2, 'w->d=yk;w->c=g;w->b=a;': 1}
OPAQUE = re.compile(rb"""//[^\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'""")
DIRECTIVE = re.compile(rb'(?m)^[ \t]*#[^\n]*(?:\\\n[^\n]*)*')
VALUE_BOUNDS = {'worker_id':[0,1], 'raw_Move_bits':17, 'quiet_sum_max':4849646,
                'noise':[0,16], 'TT_priority':[1000000,1000000],
                'capture_priority':[499100,514400], 'promotion_bonus_max':405000,
                'assigned_priority_max':1405000, 'int32_max':2147483647,
                'same_iteration_depths':[1,126], 'same_exhaustion_ply':127}

def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,msg):
 if not ok:raise ValueError(msg)
def transform_source(source):
 need(type(source) is bytes and len(source)==INPUT_BYTES and sha(source)==INPUT_SHA256,'fixed F4180 source differs')
 opaque=[(m.start(),m.end(),m.group()) for m in OPAQUE.finditer(source)]
 directives=[(m.start(),m.end(),m.group()) for m in DIRECTIVE.finditer(source)]
 out=[];gaps=[];last=0
 for r in REGIONS:
  a,z=r['old_start'],r['old_end'];old,new=r['old'].encode(),r['new'].encode()
  need(a>=last and source[a:z]==old and source.count(old)==1,'literal role differs')
  need(not any(a<end and z>start for start,end,_ in opaque+directives),'edit overlaps protected opaque/directive bytes')
  need(sha(old)==r['old_sha256'] and sha(new)==r['new_sha256'],'literal hash differs')
  gap=source[last:a];gaps.append(gap);out.extend((gap,new));last=z
 out.append(source[last:]);gaps.append(source[last:]);result=b''.join(out);inverse=result
 for r in reversed(REGIONS):
  a,z=r['new_start'],r['new_end'];need(inverse[a:z]==r['new'].encode(),'inverse preimage differs');inverse=inverse[:a]+r['old'].encode()+inverse[z:]
 c=b''.join(gaps);need(inverse==source and len(result)==OUTPUT_BYTES and sha(result)==OUTPUT_SHA256,'inverse/output differs')
 need(len(c)==COMPLEMENT_BYTES and sha(c)==COMPLEMENT_SHA256,'protected complement differs')
 for v,n in PROTECTED.items():need(source.count(v.encode())==result.count(v.encode())==n,'admitted type/id/consumer/control differs')
 need([m.group() for m in OPAQUE.finditer(result)]==[v for _,_,v in opaque],'opaque literal/comment inventory differs')
 need([m.group() for m in DIRECTIVE.finditer(result)]==[v for _,_,v in directives],'directive inventory differs')
 return result,{'stage':'material-only-after-object-type-names','opaque_and_directive_bytes_exact':True,'C_value_bounds':VALUE_BOUNDS,'regions':REGIONS,'exact_inverse':True,'complement_bytes':COMPLEMENT_BYTES,'complement_sha256':COMPLEMENT_SHA256}
