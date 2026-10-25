# Maintained experiment dependencies

This directory contains experiments that still supply a current production,
evaluation or CI consumer. Inactive campaigns have moved to
[`archive/engines/experiments`](../../archive/engines/experiments), with their
original bytes and a pinned original-path replay procedure. A retained path is
a dependency classification, not a claim of tournament qualification.

| Directory | Current consumer / reason for retention |
| --- | --- |
| `tcec-next` | Current production profile source projection, runtime/rule/compiler checks |
| `tcec-scope` | Selected predecessor controls and process ownership helpers used by current profiles and peer evaluation |
| `tiny-d-submission` | Current D production source, storage, packaging and runtime profiles |
| `strength` | Current league evaluation, peer runtime and bounded AWS campaign tooling |
| `tiny-c-table` | CI model-table transformation contracts and retained C-table comparison |
| `tiny-e-state` | CI state transformation contracts; input to `tiny-e-order` |
| `tiny-e-order` | CI ordering transformation contracts and retained E comparison |
| `packaging-control` | Literal predecessor producers required by `tiny-e-state` and `tiny-e-order` |
| `tiny-d-loader` | CI decoder contracts for maintained D ELF work |
| `tiny-encoding` | CI codec tests and the codec producer consumed by `tiny-semaphore` |
| `tiny-semaphore` | CI C pool ownership contract and its retained comparison source |

Do not import inactive archive paths into current production recipes. A new
adoption belongs to its current source owner and needs a fresh size/behavior
comparison. E19 corpus, training and inference work lives in `../training/e19`;
it does not consume the archived E19 model-structure experiment as an oracle.
