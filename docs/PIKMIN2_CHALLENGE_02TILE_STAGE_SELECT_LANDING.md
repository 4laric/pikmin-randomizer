# ch_NARI_02tile stage-select landing (lane challenge-02tile-stage-select-landing, #705)

Bounded landing+extension unblocking `p2-challenge-ch-nari-02tile-p1` (#537):
the only stage selector (#669, done, owner gone, never handed off/integrated)
hardcodes `ch_NARI_01kusachi` and rejects `ch_NARI_02tile`. This lane extends
the committed selector read-only and lands the extension via handoff + packet.
No #669-file duplication, no family/shared/native edits, no runtime, no ADMIT.

## #669 re-verification (read-only)

Committed selector at root commit `01a35f3a` verified byte-identical
(`experimental/pikmin2_challenge_stage_select_boot.py` sha256
`d8c2413cb60616571e3df02be1f9ef0b40ced36f9580a513fb760fa4203410f0`),
loaded via git object store (never re-derived). kusachi still resolves
(ui_index 3) through the untouched #669 path.

## 02tile extension (new table row, canonical baseline only)

`ch_NARI_02tile` resolves with ui_index 4 from the canonical plan+inventory
cross-check (table_order 19, 2 floors, timers 200/150, sprays 0/5, roster
matrix, legacy 0.0, treasure field 0, source
`user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt` sha256 `d047060c...`).
Boot records render in the identical `P2_CHALLENGE_STAGE_SELECT_1` grammar.
Unknown keys (including P1 `chal<N>` slots) are refused with explicit reasons.

## Staged layout pins (read-only refs from #537 blocker record)

- `stage-manifest.json`: `d8634b9c...`
- `p1-input-package.json`: `5dea109e...`
- `run-plan.json`: `7193bedb...`

## Acceptance check for the integrator

`run_stage_fixture.py --exe <integrated-stage-boot-fixture>/fixture.exe
--stage ch_NARI_02tile` with this extension landed: selector resolves
02tile (no SelectionError), kusachi preserved, unknown keys rejected,
staged run boots under #632, no ADMIT.

## Gates

All six runtime gates UNTESTED; no playability claim. Downstream consumer:
`p2-challenge-ch-nari-02tile-p1` (#537, blocked gen 2).