# Preparing a release

The current local npm candidate is version 0.3.0. The repository
is now hosted at https://github.com/daejunnom/NVCompact. npm registry publication
has not been performed.

## Produce the concrete artifact

```sh
npm ci --ignore-scripts --offline --no-audit --no-fund
npm test
npm run check
npm run pack:cli
npm run verify:package
```

Use `npm run test:core` when changes affect core behavior or migration evidence.
The CLI lifecycle suite and core UCI cases use the development oracle documented
in the root README. Set `NVUCI_ORACLE_PATH` when running the complete suite;
otherwise three CLI UCI cancellation checks are reported as skipped. The pack
and installation checks inspect the actual `.tgz`, not a workspace link.

The typed C rewrite tests require Clang. Select its executable with
`NVCOMPACT_CLANG` when it is not on PATH. CI checks that a Clang executable
exists before running the core tests. Resource tests use small fixtures;
the original high-memory engines are not started by CI or package verification.

The candidate's own `files` allow-list controls the npm contents. Install hooks
do not fetch interpreters, build native executables or install Python packages.

## Registry publication

The owner supplied the repository MIT license, which is also included in the
CLI package. Repository metadata points at the actual NVCompact repository.
Root, CLI candidate and lab currently retain `private: true`.

A future registry release can select the actual npm name or owned scope and
change the CLI publication setting. Repack and revalidate after any metadata
or source change. Keep the root and lab as private workspaces. External lab
licenses remain attached to their inputs.

Publication is a separate action. This preparation has not run `npm publish`
and does not embed registry credentials or an automatic publish workflow.

## Version and evidence changes

The Node package version describes the distributed wrapper and contents. The
Python core version and hashes describe the backend. A future packaging-only
patch can report a different package version while retaining the same core.

`evidence/core-migration.json` records the initial 0.2.0 move, not a rule freezing
those eight Python files forever. Version 0.3.0 intentionally changes the core
and records its own validation. An intentional algorithm change should
have its own rationale and relevant verification. Do not update a failed
reproduction's expected hashes to hide a mismatch.

Native recipes fingerprint their generating core. Reproducing a 0.2 native
recipe still requires its recorded 0.2 runtime and inputs; upgrading the CLI
does not rewrite that recipe or weaken the hash comparison. Keep the original
package/source snapshot for historical reproduction. A new 0.3 campaign creates
its own recipe and evidence.

CI prepares and checks artifacts; it does not include an automatic publication
job. Local success does not claim that a remote CI run has already occurred.
