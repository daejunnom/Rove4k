# One selected A ownership/query candidate

The only control is the maintained selected readable A source, SHA-256
`321ab861fe8e8ebc1791cbd389edbecc53091ede195e172e9983f2455ee12c6d`.
All existing folders, including `tiny-entry-a`, remain read-only. This folder
does not change the decoder, generator, move application, board/hash/search
policy, compiler, fixed token choices or compression recipe. No sweep is run.

The private move query owns its complete child result. A null text pointer asks
for the first legal witness; a non-null token is compared with the same generated
move text by the same exact strcmp as the control. A successful make writes a
caller-owned scratch Board. Position replay commits that already-made child,
removing a second identical make. Failed queries may change only this scratch
object, which no caller reads on failure. The global position and history commit
only after the complete input history is admitted. The helper is never called
with an output aliasing its input; alias support is not added to make.

The per-GO worker reset moves to each worker's think entry, where nodes, depth
and score already reset. Best is also set to zero there. Every published job must
run think even if stopped before its first claim. A worker resets before it
decrements pending, and result reads all workers only after the last decrement.
Thus zero-completed-depth and immediate-stop jobs retain the same legal fallback.
Startup does not dispatch a job before all workers are ready; partial creation
failure joins only created workers and does not call result. Main and DEV stats
wait for physical completion before inspecting/reusing worker results.

This does change a broader internal-consumer contract: a direct think call with
a preseeded best now clears it, including a stopped or zero-iteration call.
Production GO already cleared best, so this is an ownership consolidation within
the published-job contract, not a claim that all arbitrary direct calls are
identical. Iterative deepening still preserves best between completed iterations
inside one think call. Board/search body hashes identify the unchanged coverage
that can be reused; they do not qualify the changed query/reset boundaries.

First reproduce the exact control's compact C, stripped ELF, bootstrap and 5207
whole file under the selected fixed recipe, then produce the candidate twice.
Report first cost before runtime proof. A loss ends this candidate. A gain allows
only narrow query/token/transaction/special-move proof, early-stop/direct-call
reset evidence, real repeated active GO/position/quit/EOF fences and selected
whole-image/startup-TID/cleanup proof. No broad matrix, games, NPS or canonical
promotion belongs to this experiment.
