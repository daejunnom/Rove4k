# TCEC 4K experiment workspace

This private workspace preserves the 11 representative inputs from the completed
NVCompact 0.2 campaign, together with manifests, original license texts and
corresponding public source archives. The Rove4k engine has its own repository.

The `engines`, `inputs` and `vendor` directories keep their original relative
layout. The files in `vendor/source-manifest.json` are resolved against this lab
workspace, while manifest-relative paths are resolved against `engines/`.

From the monorepo root:

```sh
npm exec -- nvcompact engines --manifests packages/tcec4k-lab/engines \
  --only sunfish --output runs/sunfish-campaign-01 --jobs 2 \
  --oracle-path .deps \
  --uci-config packages/nvcompact/profiles/protocol-15s.json
```

Alternatively, the workspace script is available after `npm ci`:

```sh
npm run campaign -w nvcompact-tcec4k-lab -- \
  --only sunfish --output ../../runs/sunfish-campaign-02 --pack-only
```

The script executes with this workspace as its working directory. `--pack-only`
performs no UCI acceptance and produces no accepted file.

Version/source gaps and original resource settings remain recorded. A public
representative release is not necessarily the exact private tournament upload.
The unchanged public we4k and 4ku mini profiles have different resource settings
from some tournament profiles. No settings were reduced during packaging.

Read `research/BUILD-REQUIREMENTS.md`, `research/ENGINE-ROSTER.md`, `research/available-artifacts.json` and
the per-engine source/licensing metadata. Historical links in these copied
research records refer to the full 0.2 research archive where applicable.

## High-memory original engines

The `resource-profiles/` directory describes the original ice4, c4ke, M4sseur
and Molly settings. Generate a plan without starting an engine:

```sh
npm exec -- nvcompact resource plan \
  packages/tcec4k-lab/resource-profiles/ice4-v6.1-original.json \
  --output runs/ice4-resource-plan.json
```

Actual execution is a separate `resource run PLAN --start --output NEW_DIR`
command on a host with sufficient resources. Plans and failed preflight checks
are not UCI passes. See [resource testing](../../docs/RESOURCE-TESTING.md) for
the memory estimates, limits, original option preservation and result states.

The previous measured summary is retained in the monorepo's `evidence/`:
11 files at or below baseline, 10 strictly smaller, 294 bytes saved in total,
five final files with the recorded UCI profile passing. This packaging work
does not claim to repeat that entire campaign.
