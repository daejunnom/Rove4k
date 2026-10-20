# Independent agent review

A separate read-only agent audited the production consumers before the change
and inspected the implemented producer, overlay, checker, contract, saved build,
generated source diff and actual-consumer reports afterward. It did not modify
files, compile or execute the candidate. This is an independent source review,
not a human approval or a substitute for the runtime evidence.

It confirmed that after shipping-cache removal the only shipping `value()`
calls were the legacy capture-priority expression, that DEV still needs the HCE
oracle, and that the actual source diff consists of the DEV guard and replacement
of that expression with `500000`. The single-TU stitcher already removes the API
prototype, so no prototype edit is necessary. It found no SEE dependency.

The 21 coefficients, leaf clamp, correction residual, exact model-order sum,
capture classification, EP handling, TT priority, promotion base and all-four-
promotion generation remain unchanged. The ordering and later search/learning
effects are explicit policy changes. The reviewer verified zero `value()` calls
in the compact model source and all 30 frozen recipe input hashes in the saved
v3 build.

The test-only observer was reviewed as reading the actual score after the real
production assignment and model addition. Its independent formula covers quiet
history/continuation/ties, captures, EP, promotions and TT priority. The six
saved optimized/sanitizer production-consumer reports passed their numeric
priority and model/board contracts. The reviewer found no blocking engine or
observer defect. It did not inspect the separate terminal black-box or
restoration reports; those were verified by the implementing agent.

Two reporting nits were corrected: the intermediate state-overlay record is
now labeled before the ordering overlay, with an explicit final shipping-HCE
consumer field; and the candidate is described as removing the duplicated HCE
capture prior, since non-model capture-class/promotion/TT priorities remain.
The exact metadata-only difference and final-image identity are recorded by the
external freeze receipt. The original reports are retained.
