# External TCEC comparisons

These files describe externally held inputs. They contain no engine source, shell source headers, compressed payloads, executables, or source archives. URLs and full SHA-256 values identify the inputs; a public representative is not automatically the private file submitted to TCEC.

- `general/`: eleven public examples, with `category: "4k"`.
- `elf/`: separately named 4k.c v9.0 and historical v8.0 examples, with `category: "4k-elf"`.
- `metadata/`: source/asset provenance, historical PGN roster, availability gaps, and resource reasoning.
- `resource-examples/`: explicit resource-plan templates, containing no target execution.
- `configs/ordinary-short-clock.json`: six-case short-clock settings for ordinary bounded 4ku, Sunfish and we4k probes.

For `nvcompact engines --artifact-root DIRECTORY`, the external filename is the manifest's `name` / `artifact_key`. For a single `envelope` invocation, use `--artifact` to point to the external file. Do not create an input or vendor directory here. Exact original shell prefixes are verified using `header_bytes` and `header_sha256`, then read from the externally provided artifact.

See [TCEC-EXAMPLES.md](../docs/TCEC-EXAMPLES.md) for the measurement boundary, division rules, workflow and limitations. Historical Python minima in manifests remain historical comparator values; current Rust results belong in separately generated evidence.
