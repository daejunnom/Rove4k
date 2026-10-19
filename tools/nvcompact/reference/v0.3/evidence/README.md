# Evidence boundaries

`core-migration.json` records the eight Python source files copied unchanged
from the completed NVCompact 0.2.0 delivery. It is evidence for this migration,
not a permanent prohibition on future core improvements.

`engine-results-v02.csv` and `engine-report-v02.ko.md` are preserved historical
results: 11 representative input files, 10 smaller and one unchanged, 294 bytes
saved in aggregate, five final files passing the recorded UCI profile. They
are not new npm-package campaign measurements. Their old relative links refer
to the preserved full `nvcompact-v02.zip` archive.

New package validation records the actual npm tarball, fresh installation,
launcher behavior and selected integration runs separately. An unchanged core
hash alone does not certify the new launcher, installation boundaries or signal
handling.

## Version 0.3

Start with `integration-validation-v03.json` for the complete local suite and
the narrowly scoped runner follow-up, `package-validation.json` for the final
installed tarball checks, and `c-rewrites-v03.json` / `c-rewrite-review-v03.json`
for actual C portfolio measurements and independent semantic review.

The `*-v03` records belong to the native-build, resource-plan and typed C rewrite
work. They include the source hashes and actual invocation scope of each check.
The four original resource plans are plan-only records: no original high-memory
engine was executed. Small fixture results do not replace those engine results.

The initial GitHub Actions run for commit `5e6ee4b` failed on Node 22 because the
old test command used an unsupported `--test-isolation=none` CLI flag. Version
0.3 loads the public `node:test` suites directly and validates both Node 22 and
24. Local reports and remote CI results remain separately attributable.

Earlier `core-validation.json`, `cli-validation.json` and the older timestamped
entries in `package-validation-runs/` describe the 0.2 packaging stage.
`package-validation.json` points to the most recent actual installation check;
its package version and timestamp distinguish the run. Old run records and the
initial Git commit retain their original results and are not relabeled.

The original full research archive SHA256 is:

`1b336f2bf8dc1acb9b4ca2787769c9e786ec6c1e91aa96e6ffc7eb0e277af97d`
