# One occupancy-swap ordering policy first cost

The only candidate replaces the actual qualified B5357 SEE with the separately
declared geometric occupancy-swap policy in `transform.py`. It is not an exact
legal-LVA rewrite. Initial actual make rejects illegal moves and resolves EP
and the selected initial promotion. The subsequent scratch removes only
origins, reuses the exact shared fixed-target query, ignores nonking pins and
check evasion, filters a selected king's geometric destination safety and ends
on that king. Target-invariant material algebra takes the maximum of all four
recapture promotions at queen value. The existing four initial promotion
members, private tactical tag, TT17, ordering unknown guard and absence of
QS negative SEE pruning remain unchanged.

The incoherent scratch is query-only. It never reaches make, evaluation,
hash/path/repetition, TT, singular or learning. Production startpos plus legal
replay admits at most32 pieces, and each continuation deletes one distinct
off-target origin: gain[32] is sufficient. Its128 planned local bytes are not
a measured native frame or a performance/stack claim.

This measured candidate changes the model and can change ordering, search,
scores and learned values. The frozen external source-only proposal is
`C:/Users/강민수/Documents/Codex/rove4k-b-occupancy-swap-source-only-20261021-proposal.md`,
14795 bytes SHA cb505a179fd72834a55c817d60d27ed2db506dbb4a8c25aa079d1adb65d381f5.
Its hand-derived, unexecuted b5c6 pin example expects legal-LVA+100 versus
geometry-230. This approximate negative cannot certify a losing capture.

One fixed native compile and one unchanged fixed ALONE compression are
authorized after source freeze, with strict pure decodes of baseline and
candidate. Baseline actual source/native/bootstrap/whole are read-only inputs
under `/home/stemxstudio/rove4k-b-tactical-normal-20261021/build` and pinned in
recipe.json. No controls are copied, compiled or compressed. No engine,
fixture/oracle, normal/shared source, Git, DEV, PP/Clang, variant, flags/name/
codec sweep or retry is allowed. All generated output and reports stay outside
Git. Neither old legal-LVA/minimax DEV qualification nor stack receipts apply.

Run exactly once from Linux after freeze:

`python3 -I -B engines/experiments/tiny-b-occupancy-swap-20261021/cost.py --out /absolute/fresh/non-Git/path`

The producer strictly decodes the original and new sole ALONE streams,
checks source/compiler argv literals and full inverse, compiles via stdin in a
private cwd/owned bounded process group, records the complete new identity
without metadata exceptions, reports gain or loss, and stops. make/M/C remain
normal search dependencies and are never counted as removed code.
