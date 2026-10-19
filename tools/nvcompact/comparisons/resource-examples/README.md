# Resource specification templates

Copy the required JSON **outside the repository**, then set its `artifact` to the actual external file. The default `../inputs/<artifact_key>` assumes external `specs/` and `inputs/` sibling directories. Retain the original SHA-256. The executable and every required deployment tool must be available through the declared invocation paths and the same `PATH` at plan/run time.

`resource plan` reads the prepared specification and generates a Rust plan. It fingerprints the input, declared tools, original invocation/resolved executable and verifier binary, and reads current resource facts. It does not start the engine, a compiler, an allocation probe, or a tool-version command. `resource run ... --start` performs a new check and starts only when the plan is still valid and admission is ready. Rebuilds or symlink retargeting require a new plan; outputs are never overwritten.

| Templates | Original workload preserved | Declared admission budget |
|---|---|---|
| ice4, c4ke | 256 GiB major allocation; 256 workers | 256 GiB + 8 GiB reserve; 288 GiB AS |
| STRO4K | 256 GiB; 509 workers; approximately 266 GiB virtual LOAD | 256 GiB + 8 GiB reserve; 288 GiB AS; AVX512F/VAES prerequisite |
| M4sseur | Eager 64 GiB; 103 workers | 64 GiB + 8 GiB reserve; 96 GiB AS |
| molly | Eager 96 GiB; 101 workers; nine-second cleanup helper | 96 GiB + 8 GiB reserve; 128 GiB AS; 12-second cleanup grace |
| 4k.c v9.0 | Original 22 GiB virtual LOAD, unknown exact resident profile | Conservative 22 GiB admission budget + 2 GiB reserve; 28 GiB AS; this is not a measured physical requirement |
| pygone | 2²⁷ pointer table; unchanged PyPy search/time management | 1 GiB table + 512 MiB runtime/search allowance + separate 512 MiB reserve; 3 GiB AS |
| moonfish | Host online-CPU worker count; dynamic tree; 1024 expansions per worker/batch | 1 GiB working allowance + 512 MiB reserve; 4 GiB AS; at most 32 online CPUs and an inherited stack bound no larger than 8 MiB |
| 4ku | Public one-worker, 64 MiB mini; original startup compiler | 512 MiB working allowance + 256 MiB reserve; 1 GiB AS |
| sunfish, we4k | Original public interpreter/profile | 256 MiB working allowance + 128 MiB reserve; 1 GiB AS |
| 4k.c v8.0 | Historical 256 MiB virtual LOAD | 256 MiB + 256 MiB reserve; 512 MiB AS |

The source-derived large allocations are distinct from measured RSS. Smaller workload allowances are explicit engineering estimates for finite probes. They are not guarantees about every search, compiler, interpreter, or future host. See [resource-analysis.json](../metadata/resource-analysis.json) for the source reasoning. Moonfish has no fixed total tree-memory bound; its preconditions prevent silently applying this particular estimate to a far larger worker count. A precondition blocks the run and does not change CPUs, stack limits or engine options.

Ordinary templates request six short-clock positions. Pygone and Moonfish use ten-second clocks: Pygone's original manager adds three seconds to its allocation even for short supplied clocks. The additional v8.0 official-clock template requests **one startpos_white case** with 30 minutes plus 3 seconds, a 1000-second observation cap and 1080-second total cap. Its source formula explains that observation budget, but a cap reached before the full supplied clock is `incomplete`, not evidence of an engine time loss. Case coverage is explicit in the report.

Admission is deliberately conservative: it uses physical `MemAvailable` and visible cgroup limits with inactive file cache as the reclaim allowance. Clean active file cache may also be reclaimable, so a temporary `blocked` result can be conservative. This implementation neither flushes cache nor changes VM or parent process settings. Retry the same justified budget after resources change naturally; do not lower the original workload or tune the budget to the observed admission threshold.

Preserve `preserve_engine_options: true`. All actual runs require explicit `--start`, finite wall/CPU/output/file limits and new output directories. Child limits are per-process, with scoped process-group cleanup; no aggregate memory cgroup or global filesystem audit is claimed. A ready plan is not a reservation, a protocol pass, or organizer certification.
