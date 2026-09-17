# Mar corpse emission on natural death (#716)

Lane `mar-corpse-emission-native`, issue #716 (OPEN). Implementation owner:
Codex through shared account 4laric. Adds the missing Mar corpse emission the
#375 kill needs for `transport_reward` via the #668 receipt arm. No
#668-receipt/preview edits, no other family/shared edits, no ADMIT.

## Missing input (traced)

`shard-enemies-2-mar29-observer` (#375, blocked gen 9) completes the natural
Mar kill (health 3000.00 -> 0.00, `P2_MAR_DEAD`, exit 0) but no corpse pellet
is emitted, so `transport_reward` stays open. Confirmed in `pc_p2_mar.cpp`:
`MAR_DEAD` played the dead clip and called `actor->die()` with no
corpse/pellet emission. Evidence: `PIKMIN2_MUSE_MAR_HANDOFF.md` sha256
`132a9959eeca482a3f69750c2ced9e72089e64a8a37a53a6d1b4b8f48729c95e`.

## Change (native, private branch)

`pc_port/pc_p2_mar.{h,cpp}` on `codex/mar-corpse-emission-native` at
`780de444` (#668 head):

- New `bool pc_p2_mar_emit_corpse(BTeki* actor)`: mirrors the family corpse
  convention (`BTeki::dieSoon` -> `PelletView::becomePellet`) by binding a
  corpse Pellet to the dead Mar (`TekiMgr::getTypeId(mTekiType)`,
  `getPosition()`, `getDirection()`), guarded once via `corpseEmitted`, and
  emitting `P2_MAR_CORPSE_EMITTED` only when a pellet with `mPelletView` bound
  to the actor is found. Returns whether a pellet is bound.
- `MAR_DEAD` finalization calls the emission before `die()`; Wait/Move/Chase/
  Attack are untouched.
- Verified against the sibling armor/sokkuri host-handoff notes and the engine
  `becomePellet`/`newPellet` contract. No behavior change outside death.

## Proof fixture + helper

- `native/tools/p2_mar_corpse_emission_fixture.cpp`: standalone
  replacement-main RoomApp. Boots over a staged Mar arena (generator 375001,
  same contract as the #375 observer), parks the captain, kills the bound Mar
  with real squad Attack orders (no mHealth/TransportMode writes), then proves
  a corpse Pellet with `mPelletView` bound to the dead Mar plus #668 receipt
  resolution (`P2_MAR_CORPSE_RECEIPT_RESOLVED`) and exits
  `PASS P2_MAR_CORPSE_EMISSION`. Guard-first #632, honest FAIL on stall, gate 6
  UNTESTED.
- `scripts/build_p2_mar_corpse_emission.py`: private leased build/run helper
  driving the maintained builder and validating the markers.
- `experimental/pikmin2_mar_corpse_emission.py` +
  `tests/test_pikmin2_mar_corpse_emission.py`: receipt-marker parsing and
  source-contract pin checks (8 tests pass).

## Compiled evidence

- Private leased build of the Mar tree: production `nectar.exe` builds clean
  with the emission change (exit 0).
- Fixture binary built by the maintained builder from the committed native
  tree (provenance recorded).

## Status / remaining blocker

Runtime proof of natural Mar death emission needs a Mar-capable run: the Mar
arena staging (flying-install system, generator 375001, Pod cargo) is a
separate owner system and is not yet staged in this lane's run output, so the
fixture has not yet observed a live Mar. The fixture fails closed naming that
exact input. Requires existing-owner review + #186 before shared-line landing.

## Captain safety (#632)

Guard runs first after engine idle, before returns/observation; captain parked
outside attack reach; no blanket invincibility. Guard header sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`.