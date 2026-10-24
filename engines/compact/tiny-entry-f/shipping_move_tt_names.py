"""One fixed18-role/117-token F object/type/member spelling stage.

Only source8265/c858083e is admitted. Actual libclang18.1.1 proof compared
all242 declarations,1979 deduplicated and2022 full position/multiplicity
reference edges, canonical type identity/layout and physical token stream.
The ordinary function/global-function map and all local/static-local names
are unchanged. Anonymous record display names follow the two typedefs only.

Nine atomic-macro argument tokens (qq/qp/zN) had physical token annotations
for the exact selected declaration, matching expanded references, and real
pinned stdatomic definitions without stringification or token-paste. The
literal invocation/physical-argument contracts below bind that proof here.
Headers, macro definitions/callees, API/main, strings and directives are not
edited. This guard does not generalize to arbitrary source/header versions.

Normal use consumes supplied source bytes only. No Clang, external engine,
experiment, report, file lookup, allocation policy or training input is read.
Whole-native equality dbbe4984 is separately established by the actual fixed
cc -Os -pthread -x c - -o x -s cost, not assumed from the name proof.
"""
import hashlib
import re
INPUT_BYTES=8265
INPUT_SHA='c858083e36683b1e83028e0c4e1b8d611ae12fc7058e4842ab4952fbd2de9c08'
OUTPUT_BYTES=8148
OUTPUT_SHA='5ee725c0e3d1479210ff023f6af75c965a421cf04645f9d60abc1ae7cedae91b'
ROLES=[('za', 'E', [361, 656, 1156, 1244, 1401, 1429, 1478, 1674, 1680, 1699, 1796, 1936, 1945, 2535, 3274, 3313, 3360, 3889, 4141, 4565, 4860, 5641, 5659, 6517, 7348]), ('zN', 'c', [540, 3574, 3680, 6490]), ('zc', 'I', [601, 609, 3728, 3878, 4849, 5826, 5995]), ('qq', 'S', [606, 3513, 6484, 7533, 7564, 7572, 8250]), ('qr', 'T', [612, 5831, 5857, 5872, 7625, 7664]), ('qp', 'F', [629, 3759, 3832, 4204, 4719, 5070, 5128, 5206, 6315, 7382]), ('qc', 'p', [634, 3814, 7317]), ('qg', 'M', [637, 4914, 6801, 7595]), ('qh', 't', [653, 4899, 4917, 6789, 7606]), ('ql', 'H', [659, 6172, 6784, 7194, 7359, 7591, 7601]), ('qo', 'G', [783, 2874]), ('qj', 'm', [5284, 6035, 6120, 6163, 6196, 6264, 6341, 6377, 6403, 7408, 7472, 8131, 8190]), ('qb', 'K', [5335, 6116, 7446, 8164]), ('qf', 'f', [5363, 6068, 6237, 6373]), ('qd', 'L', [5407, 6089, 6138, 7417]), ('qk', 'J', [5421, 6041, 6206, 6351, 7412]), ('qm', 'O', [5426, 6094, 6127, 8135]), ('qe', 'P', [5438, 5891, 7353])]
MACRO_ARGUMENTS=[('zN', 3574, 3536, 3598, b'atomic_flag_test_and_set_explicit(&e->zN,memory_order_acquire)', 'atomic_flag_test_and_set_explicit', ['MACRO_DEFINITION', '/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain/clang18-headers/root/usr/lib/llvm-18/lib/clang/18/include/stdatomic.h', 7956], '1fa3d4b0e5ec03abc8cb826575bfba73003c02ca30980c777eca05950b15812f'), ('zN', 3680, 3649, 3704, b'atomic_flag_clear_explicit(&e->zN,memory_order_release)', 'atomic_flag_clear_explicit', ['MACRO_DEFINITION', '/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain/clang18-headers/root/usr/lib/llvm-18/lib/clang/18/include/stdatomic.h', 8158], 'e25c4fc5050e0cc042f23af435508c3506c8951fcacb9682f4e872ce0b900b0e'), ('zN', 6490, 6465, 6493, b'atomic_flag_clear(&qq[i].zN)', 'atomic_flag_clear', ['MACRO_DEFINITION', '/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain/clang18-headers/root/usr/lib/llvm-18/lib/clang/18/include/stdatomic.h', 8065], 'd979d5282e36f7ca33dd069a51475187313f2ac4ba11057cb9bf30016e6cb81f'), ('qq', 6484, 6465, 6493, b'atomic_flag_clear(&qq[i].zN)', 'atomic_flag_clear', ['MACRO_DEFINITION', '/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain/clang18-headers/root/usr/lib/llvm-18/lib/clang/18/include/stdatomic.h', 8065], 'd979d5282e36f7ca33dd069a51475187313f2ac4ba11057cb9bf30016e6cb81f'), ('qp', 3832, 3818, 3837, b'atomic_store(&qp,1)', 'atomic_store', ['MACRO_DEFINITION', '/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain/clang18-headers/root/usr/lib/llvm-18/lib/clang/18/include/stdatomic.h', 5533], 'fc9a947f8b4944ae2e730b6d47070dac17a7b824120a08ab5de0adb45be31286'), ('qp', 4204, 4190, 4209, b'atomic_store(&qp,1)', 'atomic_store', ['MACRO_DEFINITION', '/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain/clang18-headers/root/usr/lib/llvm-18/lib/clang/18/include/stdatomic.h', 5533], 'fc9a947f8b4944ae2e730b6d47070dac17a7b824120a08ab5de0adb45be31286'), ('qp', 5128, 5114, 5133, b'atomic_store(&qp,1)', 'atomic_store', ['MACRO_DEFINITION', '/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain/clang18-headers/root/usr/lib/llvm-18/lib/clang/18/include/stdatomic.h', 5533], 'fc9a947f8b4944ae2e730b6d47070dac17a7b824120a08ab5de0adb45be31286'), ('qp', 6315, 6301, 6320, b'atomic_store(&qp,1)', 'atomic_store', ['MACRO_DEFINITION', '/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain/clang18-headers/root/usr/lib/llvm-18/lib/clang/18/include/stdatomic.h', 5533], 'fc9a947f8b4944ae2e730b6d47070dac17a7b824120a08ab5de0adb45be31286'), ('qp', 7382, 7368, 7387, b'atomic_store(&qp,0)', 'atomic_store', ['MACRO_DEFINITION', '/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain/clang18-headers/root/usr/lib/llvm-18/lib/clang/18/include/stdatomic.h', 5533], 'fc9a947f8b4944ae2e730b6d47070dac17a7b824120a08ab5de0adb45be31286')]
COMPLEMENT_BYTES=8031
COMPLEMENT_SHA='f8bba80d9f7c81d9dc5a1f0a70ec7144ba01183beac530343f44fd4695716f96'
AST_PROOF_METADATA_SHA='04b87f97e986557230f2c02a42a4644e68cb5448b7d3f1361e05f82318e07d05'
ATOMIC_HEADER_METADATA=('/mnt/c/Users/강민수/Documents/Codex/rove4k-pr12-size-reference-20261020/toolchain/clang18-headers/root/usr/lib/llvm-18/lib/clang/18/include/stdatomic.h', '4e4de7f617643a9f6e49c678866c05266b3d8d4145eb653066f1ca3f6e49b0be')
OPAQUE=re.compile(rb'(?m)^[ \t]*#[^\n]*(?:\n|$)|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*(?:\n|$)|/\*.*?\*/',re.S)

def sha(data):return hashlib.sha256(data).hexdigest()
def need(value,message):
    if not value:raise ValueError(message)

def transform_source(source):
    need(type(source)is bytes and len(source)==INPUT_BYTES and sha(source)==INPUT_SHA,'exact F MoveTT8265 source required')
    need(b'\r'not in source and b'??'not in source and b'\\\n'not in source,'fixed ASCII/LF physical source required');source.decode('ascii')
    opaque=[m.span()for m in OPAQUE.finditer(source)]
    edits=sorted((position,old.encode(),new.encode())for old,new,positions in ROLES for position in positions)
    need(len(ROLES)==18 and len(edits)==117,'fixed role/edit arity differs')
    for old,physical,start,end,invocation,macro,definition_key,definition_tokens_sha in MACRO_ARGUMENTS:
        need(source[start:end]==invocation and invocation.startswith(macro.encode()+b'('),'fixed atomic macro invocation differs')
        need(start<physical<end and source[physical:physical+len(old)]==old.encode(),'fixed physical macro argument differs')
        need(any(position==physical and before==old.encode()for position,before,after in edits),'macro argument edit absent')
    parts=[];gaps=[];rows=[];offset=produced=0
    for position,before,after in edits:
        end=position+len(before)
        need(position>=offset and source[position:end]==before,'fixed physical edit differs')
        need((position==0 or not(chr(source[position-1]).isalnum()or source[position-1]==95))and(end==len(source)or not(chr(source[end]).isalnum()or source[end]==95)),'identifier boundary differs')
        need(not any(position<b and a<end for a,b in opaque),'directive/comment/literal edit prohibited')
        gap=source[offset:position];gaps.append(gap);parts.extend((gap,after));start=produced+len(gap);rows.append((start,start+len(after),position,end));produced=start+len(after);offset=end
    parts.append(source[offset:]);gaps.append(source[offset:]);result=b''.join(parts)
    inverse=[];after_gaps=[];offset=0
    for start,end,old_start,old_end in rows:
        inverse.extend((result[offset:start],source[old_start:old_end]));after_gaps.append(result[offset:start]);offset=end
    inverse.append(result[offset:]);after_gaps.append(result[offset:]);complement=b''.join(gaps)
    need(b''.join(inverse)==source and gaps==after_gaps,'full inverse/protected complement failed')
    need(len(complement)==COMPLEMENT_BYTES and sha(complement)==COMPLEMENT_SHA,'fixed untouched byte complement differs')
    need(len(result)==OUTPUT_BYTES and sha(result)==OUTPUT_SHA,'fixed F names output differs')
    return result,{'fixed_roles':18,'physical_identifier_edits':117,'source_bytes_saved':117,'exact_inverse':True,'protected_complement_exact':True,'directive_comment_literal_edits':0,'macro_callee_definition_edits':0,'fixed_atomic_argument_bridges':9,'header_definition_proof_metadata':ATOMIC_HEADER_METADATA,'AST_proof_metadata_sha256':AST_PROOF_METADATA_SHA,'Clang_report_external_input':False,'local_function_static_names_unchanged':True}
