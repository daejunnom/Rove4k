# C material/SIMD vector sharing

This is one fixed closing shipping stage after the maintained C input-profile
stage. It starts at source 10886 / d6265b2c and yields 10831 / 207b07cc (-55 B).
Earlier canonical, alpha, scope, core, SIMD and input-profile stages are unchanged.
DEV bypasses this shipping-only experiment. The rejected residual-only and
position-only proposals are not part of this candidate.

The unchanged sixteen signed16 weights move from U's local `static const` array
to a file-local `static const int16_t qm[16]` before value. The redundant seven
int material values disappear. For piece magnitude a=0..6, `-qm[a+7]` gives
exactly 0,100,320,330,500,900,0. Integer promotion precedes negation; no new
overflow is introduced. Empty value stays zero, king positional value stays
signed, and the two capture-ordering value calls and promotion bonus order stay
exact. U keeps its original multiply-add, sixteen lanes and both-half AVX2 reduction.
The unaligned SIMD load imposes no new alignment contract.

`transform.py` admits one exact old whole source, performs two literal span
replacements, and checks the exact inverse, protected complement and new whole
identity. qm is absent from the old source and has exactly four new tokens.
The signature `int value(int,int)` remains unchanged; the new global has internal
linkage and follows stdint.h. Existing legal piece/square domains are retained.

`cost.py` reads the pinned normal output and receipt without copies or rebuilds.
It compiles only the candidate once with the unchanged normal argv, stdin,
inherited environment and private native cwd, then uses the same source-literal,
77-byte prefix and fixed ALONE (nice_len=64) once. Its pure strict decode requires
EOF, no trailing bytes and the exact expected bootstrap. All artifacts/reports
are outside Git. No C AST/PP, DEV build, engine, game or benchmark is included.
New native identity is expected; old full-ELF equality is not a requirement.

Source review and raw arithmetic are not native/whole or functional acceptance.
On whole tie/loss the lane stops. A whole win requires a separate focused
value/AVX2/ordering qualification and explicit normal-integration decision.

The one first-cost run passed: source 10831/207b07cc, native 26352/a053a60d,
bootstrap 11906/1e97d021 and whole 5159/89d55de0, a 14-byte whole reduction.
Compiler exit was 0, stderr empty and strict ALONE decode exact. The cost receipt
is 5450ee6b1f6bc5cfeed32b329eaf68d23d9d9684d5f1c0fefba669afb4abad56.
The four exact producing cost source files are preserved outside Git under
rove4k-c-material-vector-proof-20261021-evidence/cost-source; this README is
post-execution metadata. Original baseline/receipt/source pins remain historical
fixed inputs; advancing the normal recipe does not retroactively change them.
The focused actual-value/U/capture fixture passed, and the ordinary C stage was
then qualified by two shipping/two DEV generations and unchanged quit/EOF verifier
sessions. Their exact receipts are recorded in the maintained recipe. No extra
variant, compression, fresh extraction, game or benchmark was run.
