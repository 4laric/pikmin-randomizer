# Mar emission re-verification vs landed #772 family fix (#814)

Lane `mar-emission-reverify-native`, issue #814 (OPEN, assigned 4laric).
Downstream blocked consumer: shard-enemies-2-mar29-observer (#375,
transport_reward).

## Context

- mar-corpse-emission-native (#716, blocked gen 3): consumer check FAILED -
  natural Mar death completes but `becomePellet` binds no pellet (no
  `P2_MAR_CORPSE_EMITTED`, `P2_MAR_CORPSE_RECEIPT_RESOLVED`).
- mar-family-corpse-type-native (#772, done gen 6): `TPI_CorpseType =
  TEKICORPSE_LeaveCorpse` + guarded probe fixture, native head `586b2e20`.
- The port emission was never re-verified against the landed family fix.

## Method

Private native tree at `e19e0071` (#716 head) plus the adopted #772 fix
commit `586b2e20` (verification build only; authorship preserved in the
private commit message). No shared/maintained edits. Driver
`experimental/pikmin2_mar_emission_reverify.py` builds the guarded emission
fixture through the maintained `scripts/build_pikmin2_fixture.py`, stages a
fresh run dir (assets junctioned read-only from the #716 consumer-run
staging, small JSONs copied), and runs headed 960x540 with the #632 captain
guard enforced (`d2f678c9`, CAPTAIN_DOWN forces BLOCKED, captain parked,
no blanket invincibility).

## Verdict rule

- `pellet_bound` (non-null `pellet=` in `P2_MAR_CORPSE_EMITTED_OBSERVED`) +
  `PASS P2_MAR_CORPSE_EMISSION` + no captain-down: hand the corpse to the
  #668 arm / #375 observer.
- Otherwise: diagnose binding vs arena vs receipt with file:symbol pins.

All six gates stay UNTESTED unless observed. No ADMIT.
