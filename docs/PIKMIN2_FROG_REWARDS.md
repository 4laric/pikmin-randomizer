# Frog/MaroFrog corpse transport and reward consumer

Lane 16 (#167, #201), child of the reward/persistence lane 06 consumer slice.
Implementation owner: Codex through shared `4laric`. This slice is host-side
bookkeeping; it does not complete the family or touch a player save.

New source: `experimental/pikmin2_frog_rewards.py` and
`tests/test_pikmin2_frog_rewards.py`. Extended host model:
`experimental/pikmin2_frog_behavior.py` (`landing_press_victims`, `carry_route`)
and `tests/test_pikmin2_frog_behavior.py`. Native-only additive instrumentation:
`native/pc_port/pc_p2_frog.cpp` `P2_FROG_PRESS` marker (unbuilt here).

## What is now modelled

- Two concrete source identities only: `enemy:17` (Frog) and `enemy:18`
  (MaroFrog). Both drop `corpse` on the ordinary `onion` ledger, `value` equal
  to the audited source corpse Pokos (Frog 5, MaroFrog 7), `count` 1. No pellet,
  Pod or invented reward is declared.
- The transport contract is read from `pikmin2_frog_behavior.carry_route()`:
  carry 7/14, Onion return 8/8 and the per-species corpse pickup radius, height
  and offset. `pikmin2_frog_rewards.carry_route()` resolves an `enemy:<id>` back
  to that source contract.
- `landing_press_victims(bittered, grounded_pikmin, grounded_navi)` implements
  the source rule that a falling frog presses every grounded Navi/Pikmin on
  contact and skips a Bittered victim.
- The shared lane-06 `experimental.pikmin2_receipts` schema provides
  exactly-once pickup accounting, including restart persistence through
  `receipts.JsonReceiptPersistence`, different-seed re-grant and revisit dedupe.

## Host-only scope

All of the above is host Python bookkeeping over the shared receipt schema. It
does not run the native FSM, does not carry a corpse, does not deposit into an
Onion and never reads or mutates a Pikmin 2 save. The receipt state is an
ordinary JSON document, not a memory card.

## Native gaps

- The registered frog is still a P1-proxy body: no native corpse carry, pickup
  or Onion/receipt wiring exists, so gates D (transport/reward) and F
  (persistence) remain UNTESTED natively. Only the injected-death PelletView
  corpse and the P1 pellet fallback have been observed. The bounded
  carry-observation fixture `experimental/pikmin2_frog_carry.py` now exists to
  watch the ordinary P1 carry path (attach, route, Onion absorption) but its
  native run is pending the coordinated GL slot. It needs no native hook: it
  reads existing public `Pellet::mPelletView`/`mPikiCarrier`/`mCarrierCount`,
  `Creature::getStickObject` and `Pellet::isAlive`, so `pc_p2_frog.cpp` is
  unchanged. Because a frog corpse out-prices the survivors' free recruitment,
  the fixture snaps the corpse onto `mapMgr->getMinY(x,z,true)` and, if fewer
  than the config's `mCarryMinPikis` carriers attach, assigns the native
  `PikiAction::Transport` task to the surviving squad — the same labelled
  original-map recipe as `pikmin2_kochappy_arena_delivery`. A missing carry or
  delivery is reported as unobserved, never as a delivery.
- `P2_FROG_PRESS` is family-local instrumentation emitted from the existing
  `pc_p2_frog_draw` path when a registered frog's P1-proxy `TekiMotion::Attack`
  is active. It is edge-triggered, a no-op for unregistered actors and cleared
  on reset/forget. It records the proxy motion only; it is **not** proof of the
  source landing press, it was not built or run in this slice, and it mutates no
  gameplay state. Intended build command:
  `cmake --build output/lanes16-18-native-build --target pikmin_pc -j 6` from
  the lane native worktree (do not build the shared `native/build-randomizer`).
- No native save mutation, no `pc_pikipelago` receipt delivery and no real
  generated-session carry route are implemented.

## Verification

`py -3.12 -m pytest -q tests/test_pikmin2_frog_rewards.py tests/test_pikmin2_frog_behavior.py tests/test_pikmin2_frog_runtime.py tests/test_pikmin2_frog_carry.py`

Remaining consumer work belongs to lanes 03/06/07 and the native corpse/Onion
integration: bind the two descriptors to a real carried corpse and prove no
duplicate or lost reward across revisit and process restart.
