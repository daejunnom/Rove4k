# One F4720 pthread-preserving futex-pool cost

This experiment admits only the current 9464-byte F shipping source
`d942731c54f82da8dfa1aa5fedcc6328b56b32fe0ab527b5396847ceea541f26`.
The normal source and DEV generation remain unchanged. There is one fixed stage,
one candidate native compile and one original ALONE compression. No control is
copied or regenerated, and no engine or bootstrap is executed by this producer.

The stage retains ordinary `pthread_create` and successful-prefix `pthread_join`,
worker count2 plus stdin, TT18, PLY128, result selection and output locking,
worker reset, clocks, transaction fences, and minimal shipping UCI. It replaces
the mutex/two-cond publication and wait mechanism with three sequentially
consistent atomic words. Startup pending2 is reused for search pending3:
the final worker changes2 to1, writes and flushes bestmove, then publishes0.
Notification is a Linux x86-64 private futex operation; the atomic words remain
the authority. Wait retries only EINTR/EAGAIN, while an unexpected wait error or
any failed wake exits2. That fatal process failure is not successful join proof.

The actual old pool-related replacement regions total778 source bytes. That is
not a saving: the new syscall declaration, platform/lock-free ABI assertions,
errno path, state and worker/wait/publication code all count. The previous
four-word tiny-A futex loss and semaphore12-byte gain concern different source
seeds and are not transferred to this F candidate.

`build.py --out /absolute/new/external/directory` reads only literal pinned
control paths and ordinary helpers from `recipe.json`. It verifies the current
normal tuple and unchanged bootstrap template, performs exact positional edits
and inverse/complement checks, compiles compiler stdin in a private cwd, then
uses the unchanged77-byte prefix and LZMA1 preset9 extreme lc2/lp0/pb0 BT4 64MiB
nice32. Strict nonexecuting decode recovers the exact source/bootstrap/argv.
Generated source, native, whole and logs remain outside Git.

Cost discovery is separate from lifecycle qualification. There are no games,
benchmarks, A extension, normal promotion, claimed runtime pass or4KiB result.

## Actual first cost: loss, stopped

The single native compile and original fixed-codec compression completed with
strict decoded-bootstrap/source/compiler-argv recovery. The fixed candidate was
not changed after this measurement, and no engine/lifecycle run followed.

| Complete input or artifact | Current control | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Shipping C |9464|9570|+106|
| Native ELF |18576|18576|0 bytes, different complete identity|
| Bootstrap Python |10463|10569|+106|
| Whole launcher+ALONE |4720|4864|**+144**|

The replaced778-byte pool domain becomes585 bytes: atomic state48, syscall/error
helper172, worker221, wait78, GO publication33 and shutdown publication33. That
domain saves193 raw bytes. Added source outside it is299 bytes: errno header19,
Linux/x86-64 target guard82, word/long/align/lock-free static assertions167, and
the syscall declaration31. **The compile-time platform and ABI guards therefore
occupy249 actual submitted source bytes.** Total source delta is -193+299=+106.
Moving these guards to build-only admission would be a separate candidate; it
was not done to hide this loss. Individual raw deltas do not predict compressed
whole deltas.

Candidate source SHA-256 is
`09fc92039abf097c2b5dc52f9d77ffeb3c5fa662b08328363bf781585fbd8e38`,
native `bf32cae411e23c9691627358e2543aebdc199d7f7dc5cd158c9e1e90a5747a92`,
and whole `4ba71cb60817bd8a3c1acdf8e2d29ab153fbff406870fcd33db79c20bfc784e2`.
The new native imports the expected syscall/errno/_Exit APIs and has no dynamic
external atomic helper. Static ABI assertions and independent source review
passed; neither establishes an executed runtime or codegen-performance result.

Actual result directory is
`/home/stemxstudio/rove4k-f-futex-pool-first-cost-20261021-v2`.
`cost.json` SHA-256 is
`3b625fca1710d3379839f76b9a366eb648439cde2228d6f35ecf38c607840a49`;
`decode.json` is
`1328d9d1c70dd8b92ae07122ac65ed080ef4ba4251217942da9a0b43a38b3b99`.
The initial output without `-v2` preserves a preparation failure: a PowerShell
JSON writer produced CRLF, rejected before any compiler or compression call.
Only recipe line endings were corrected, and the actual WSL user was selected
explicitly for the fresh output. No candidate C/guard/flags variation followed.

The producing five ordinary inputs remain frozen in the actual result's
`inputs/`. This paragraph is a post-run README metadata overlay; producer,
transform and recipe bytes are unchanged. No whole reproduction, runtime
qualification, target-profile scalability, strength or tournament eligibility
is claimed. The candidate remains768 bytes over4096 and is not selected.
