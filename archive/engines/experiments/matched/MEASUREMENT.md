# Bounded matched-E measurements

`measure.py` measures the actual frozen `matched-c-policy-v1` E engines. It
does not generate or compile candidates and does not modify canonical source.
The manifests remain the source of compiler commands/identity, model, resource
policy and source/native hashes. The helper checks both the preserved generated
sources and their compiler-input copies before and after execution.

Run `prepare` first. It validates identity, resources and affinity availability
without launching an engine. Then `gate` runs one cold pair per fixture/profile,
requiring hash/model/legal equality and every completed iterative score. With
one worker, every depth's exact node count and the attaining move must also
match. Gate reports deliberately contain no measured wall/CPU/NPS fields.

```sh
python3 engines/experiments/matched/measure.py \
  --one /absolute/matched-one/generation.json \
  --four /absolute/matched-four/generation.json \
  --out /absolute/new-prepare --mode prepare \
  --cpus-one 0 --cpus-four 0,2,4,6 --depths 7,7,5
```

Use a new output directory for `--mode gate`. The local 8-logical-CPU WSL host
reports SMT pairs `0-1`, `2-3`, `4-5`, `6-7`. The example four-worker mask therefore
selects one logical CPU from each physical core. The input thread shares that
mask. A four-core campaign leaves no separate physical core for the supervisor;
it mostly waits in `select`, but this limitation remains explicit. The engine
process and all startup TIDs are checked against their inherited affinity.
Native processes receive only the explicit environment `PATH=/usr/bin:/bin`,
`LC_ALL=C`, `TZ=UTC`; uncontrolled supervisor loader/instrumentation variables
are not inherited or read. These values are included in the report.

Only after the coordinating owner confirms other compilation/test/timing
handles are physically terminal, reserve a quiet window and run `measure`:

```sh
python3 engines/experiments/matched/measure.py \
  --one /absolute/matched-one/generation.json \
  --four /absolute/matched-four/generation.json \
  --out /absolute/new-measure --mode measure --profiles both \
  --cpus-one 0 --cpus-four 0,2,4,6 --depths 7,7,5 \
  --samples 3 --budget 55 --quiet-window OWNER-RESERVATION-ID
```

`--quiet-window` records coordination evidence; the script cannot discover other
agents' handles or grant its own reservation. Each fixture/language/sample gets
a fresh process and first search, with no retained TT or learning. The pair order
alternates C/Rust and Rust/C, reversed by fixture/profile. Languages never execute
concurrently. At most three paired samples per fixture/profile are admitted.
An absolute campaign deadline bounds response waits; partial/failed evidence is
retained rather than silently retried or averaged away.
`--cases kiwipete` (or comma-separated/repeated known names) selects a bounded
subset. Depths keep their original `start,opening,kiwipete` positions, so
`--depths 7,7,5 --cases kiwipete` still uses depth 5. Reports preserve the exact
invocation budget, response timeout, selected profiles/cases, sample count,
argument vector and campaign UTC start/end. Separate campaigns stay separate;
a failed partial campaign is never rewritten as a successful full campaign.
`--sample-start 1 --samples 2` executes only global sample indices 1 and 2.
Pair alternation keeps the original profile index (one worker 0, four workers 1)
and original fixture index even when filtering; selected runs do not silently
renumber their order. Global indices remain bounded to 0, 1 and 2.

Search wall time starts immediately before writing/flushing `go` and ends on
the kernel stdout-read receipt containing the complete `bestmove` line. This is
parent-observed request/response latency: engine formatting, IPC and scheduling
are included. The measurement path uses no sampler thread and buffers transcripts
in memory; oracle/PV checking, `stats`, memory reads and disk logging occur after
the search endpoints. Launch-through-ready startup latency includes taskset,
loader, actual TT clear/prefault and protocol handshake. Preparation of the
position and semantic observations is recorded separately.

Process CPU is the delta of `/proc/PID/stat` **utime plus stime**, which already
includes all engine threads. Neither task/TID CPU nor waited-for child CPU is
added again. Raw endpoints, process start ticks and `CLK_TCK` are recorded.
On this host `CLK_TCK=100`: the conservative endpoint quantization bound is
20 ms. CPU NPS/utilization is omitted when the observed CPU interval is at most
two ticks; longer intervals still carry that uncertainty. CPU reads immediately
follow bestmove receipt, before validation, and the endpoint skew is recorded.

Startup and postsearch `/proc/PID/status` fields preserve actual `VmRSS`,
`VmHWM`, mappings and fixed TIDs. Kernel RSS accounting is approximate.
`VmHWM` is a process lifetime maximum; its change is not a sum of search
allocations. `VmStk` does not aggregate all worker stack reservations. No padding
is added to make languages' resident footprints equal.

Four workers can finish different amounts of real work as shared TT scheduling
changes. A root's last info line can precede other workers' completion; the tool
keeps its reported nodes and the final actual aggregate stats separately. Wall
NPS uses that completed aggregate. One-worker pairs must have exact equal work.
The report preserves each sample and gives median/range only within its exact
profile/fixture/engine; it does not merge the workloads into a language ranking.
These bounded developer-native observations establish no causal language effect,
Elo, general NPS superiority, submission-file eligibility or target-server scaling.

Initial non-timed readiness on 2026-10-20 passed all six cold pairs at depths
`7,7,5`. The earlier depths `6,6,4` also passed, with exact one-worker totals
17,249, 39,350 and 35,479 nodes respectively. The first four-worker gate failure
was an overly strict helper premise that required final aggregate stats to equal
an earlier selected root info count; that failed run is retained outside Git.
The corrected helper accepts a greater final aggregate only with multiple workers
and keeps exact equality with one worker. No engine logic or expected score was
changed to obtain these passes.

## Completed bounded campaign, 2026-10-20

The combined evidence index has **18 valid cold pairs / 36 paired engine runs**:
three pairs for each of start depth 7, opening depth 7 and Kiwipete depth 5,
with one and four workers. Every included pair passed its semantic gate. Every
one-worker pair matched every completed depth's score and exact node count,
plus the attaining bestmove. Four-worker pairs matched completed scores; their
actual work can vary with shared-TT scheduling.

The original campaigns retain distinct states:

| Logical evidence | Original status | Included pairs | Other preserved attempts |
| --- | --- | ---: | --- |
| `ROVE-MATCHED-E-20261020-Q1` / `results.json` | `passed: false`, reservation-deadline timeout | 16 | One completed C singleton and one incomplete Rust attempt |
| `ROVE-MATCHED-E-20261020-Q2` / `results.json` | `passed: true` | 2 | None |
| Combined `index.json` | `coverage_complete: true`; source campaign states retained | 18 | Both Q1 exclusions referenced separately |

Q2 ran only four-worker Kiwipete samples **1 and 2**, using
`--profiles four --cases kiwipete --depths 7,7,5 --sample-start 1 --samples 2`.
The original fixture/profile/sample indices preserved the planned C/Rust order;
sample 0 was not duplicated. The Q1 singleton and incomplete attempt do not
enter any median, range, node total or memory summary below. Q1 was never
rewritten as a successful full campaign. Its older helper did not record exact
invocation-budget/UTC fields; Q2 did. Q2's recorded budget was 33.974 seconds,
and its campaign interval was 00:01:52.140834–00:01:52.877244 UTC.

Q1 used helper SHA-256 `025aef6682a7308aa80cbe1a79ae45186f4e2f4529bcd3d80d934bd1e097aa1c`;
Q2 used `2af7f32c2e281986702b29cda0518634f01e755e5781d6db3549c1424fecc6a6`.
The logical `q1-q2-invariance.json` and `q1-q2-helper.diff` preserve the exact
old/new helpers. Nine measurement/core source segments, including `Session`,
`run_case`, CPU/memory readers and pair checks, are byte-identical. Frozen
generation/source/native/tool records also match; changes are CLI selection,
global sample indexing and invocation/UTC metadata. Both reservations are
represented in the combined index, rather than portrayed as one uninterrupted run.

Search wall times below are **median [minimum–maximum] milliseconds**, with
three paired samples per cell. Node columns report actual completed aggregate
work; a range means that scheduling changed the work across the three runs.

| Workers | Fixture / depth | C wall ms | Rust wall ms | C actual nodes | Rust actual nodes |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Start / 7 | 142.48 [139.86–150.32] | 185.67 [176.09–187.68] | 84,834 | 84,834 |
| 1 | Opening / 7 | 224.18 [221.44–235.29] | 266.20 [239.33–275.44] | 92,847 | 92,847 |
| 1 | Kiwipete / 5 | 325.00 [281.36–391.68] | 326.83 [301.42–337.35] | 88,002 | 88,002 |
| 4 | Start / 7 | 70.52 [69.61–93.80] | 88.27 [83.34–90.57] | 143,373–172,403 | 148,213–149,585 |
| 4 | Opening / 7 | 114.71 [110.63–122.69] | 130.70 [129.51–154.71] | 175,848–185,916 | 164,632–185,735 |
| 4 | Kiwipete / 5 | 181.44 [156.30–186.79] | 162.50 [161.55–187.93] | 155,171–180,517 | 164,154–192,974 |

The corresponding aggregate process CPU values are **median [minimum–maximum]
seconds**. Each raw interval carries the conservative **20 ms quantization
bound** described above; displaying two decimal places does not increase its
precision. The CPU value includes the input/coordinator and all search workers.

| Workers | Fixture | C CPU seconds | Rust CPU seconds |
| ---: | --- | ---: | ---: |
| 1 | Start | 0.14 [0.14–0.15] | 0.18 [0.18–0.19] |
| 1 | Opening | 0.23 [0.22–0.23] | 0.27 [0.26–0.27] |
| 1 | Kiwipete | 0.31 [0.27–0.39] | 0.32 [0.31–0.34] |
| 4 | Start | 0.29 [0.28–0.39] | 0.37 [0.35–0.38] |
| 4 | Opening | 0.47 [0.46–0.48] | 0.54 [0.48–0.61] |
| 4 | Kiwipete | 0.60 [0.53–0.65] | 0.66 [0.60–0.72] |

The combined index retains every sample's actual nodes, wall NPS and CPU NPS.
Wall NPS divides that run's final actual aggregate nodes by its search wall
interval, not by the chosen root's earlier info count. Four-worker node totals
are unequal, so their time/NPS observations are not a fixed-work comparison or
a proof of stronger search. No cross-fixture average or overall language rank
is derived. A CPU/wall ratio slightly above the assigned core count can occur
at this tick resolution and is not evidence of extra effective cores.

Startup and memory observations below pool the nine included runs per
language/profile. Startup is **median [minimum–maximum] milliseconds** from
process launch through readiness; resident values are the kernel's reported kB.
Both real 4 MiB TTs were cleared/prefaulted before the startup memory snapshot.

| Workers | Engine | Startup ms | Startup VmRSS kB | Postsearch lifetime VmHWM kB |
| ---: | --- | ---: | ---: | ---: |
| 1 | C | 3.88 [3.64–6.77] | 5,760 | 5,888–6,016 |
| 1 | Rust | 3.93 [3.79–4.54] | 6,144–6,272 | 6,144–6,272 |
| 4 | C | 3.78 [3.54–4.42] | 5,760 | 6,016–6,272 |
| 4 | Rust | 4.21 [3.90–4.85] | 6,400 | 6,528–6,784 |

All included runs retained the same two or five startup thread IDs and requested
CPU masks. These are short developer-native searches on one four-core WSL host,
in two reservations, with only three pairs per fixture/profile. The supervisor
was allowed on all eight logical CPUs and had no separate physical core in the
four-worker profile. Three samples also leave a 2:1 first-language imbalance
within an individual fixture/profile. Those limitations, variable work and the
observed ranges remain part of the result. These measurements establish no
causal language effect, general NPS superiority, Elo, submission-file eligibility
or scaling to the tournament's target hardware.
