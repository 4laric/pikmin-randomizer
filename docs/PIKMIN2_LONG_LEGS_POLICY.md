# Long Legs source policy (#173 / #312)

Lane 26 bounded slice: an engine-free, deterministic implementation of the
shared Long Legs lifecycle and attack scheduling used by Damagumo (56, Beady
Long Legs), Houdai (66, Man-at-Legs) and BigFoot (69, Raging Long Legs).

Implementation owner: Codex via shared account `4laric`. Executing session:
opencode (deepseek-v4.1-flash), 2026-09-13. Native candidate:
`opencode/p2-longlegs-fsm` head `a62a8931`, base `f9e139d8` (never pushed to
native origin). Patch: `native-candidates/long-legs-policy/`.

## What this slice is

The previous lane evidence was the source audit
([PIKMIN2_LONG_LEGS_AUDIT.md](PIKMIN2_LONG_LEGS_AUDIT.md)) plus a visual-only
bind-pose draw path (`pc_port/pc_p2_long_legs.cpp`, `native_fsm=unimplemented`).
This slice adds the first source-mechanics layer the lane owns:

- `pc_port/pc_p2_long_legs_fsm.h` / `.cpp`: a pure policy for the shared
  Stay/Land/Wait/Flick/Walk cycle and the per-species rules, with retail
  parameters per identity.
- `tools/p2_long_legs_fsm_test.cpp`: an engine-free compiled fixture that
  scripts the host inputs and asserts the transitions.
- `CMakeLists.txt`: the policy is added to the `pikmin_pc` sources and the
  fixture is registered as the `p2_long_legs_fsm_test` ctest target.

The policy never dereferences a game object. The host owns IKSystemMgr, joint
shadows, tube collision, animation key events, RNG state and effects; the
policy consumes a per-tick input struct and emits intents (`footCrush`,
`shake`, `fireShell`, `dropTreasure`, `birthChildren`). This matches the
established lane pattern used by `pc_p2_bombsarai_fsm.*`.

## Source mapping

| Behavior | Source fact | Policy |
|---|---|---|
| Wake | all three sit hidden in Stay until a captain or Pikmin enters `mPrivateRadius` 75 (disc) | `Stay -> Land` on `wakeTargetNearby` |
| Landing | `landing` key 2 removes bitter immunity and fires all four feet | `landingKey2` sets `feetFired`, `footCrush`; `bitterImmune`/`damageable` flip |
| Wait/Walk | Damagumo 1.75-3.5 s / 3.25-6.5 s; Houdai 1.5-3 s / 3.5-7 s; BigFoot fixed 5 s / 10 s (`mNormalTravelTime`) | per-species `waitMin/Max`, `walkMin/Max`; host `roll` picks the duration |
| Accumulating Pikmin | `isStartFlick` interrupts Wait or Walk with Flick | `pikminAccumulating -> Flick` |
| Flick | key 2 shakes with `mShakeChance/Knockback/Damage` | `flickKey2 -> output.shake` (effect host-owned) |
| Foot crush | a foot only presses while descending or planting with move ratio above 1; Houdai has no press code | `crushGate()` requires `footDescendingOrPlanting && ikMoveRatio > 1 && pressDamage > 0` |
| Damage | US build: only a Pikmin stuck to a collision part damages them; no carcass | `damageRequiresStuck` documented; death is terminal with no carcass flag |
| Death | held treasure is thrown straight down from `kosi`; with no treasure, Beady births 25 ShijimiChou and Raging births 30 Mitites | `dropTreasure` vs `birthChildren` 25 / 0 / 30 |
| Raging one-cycle rage | `mIsEnraged` set when Flick ends, cleared when the next Walk ends; that Walk uses fp21 5 s post-shake travel | `mEnraged` gates `walkPostFlickSeconds` and `output.enragedWalk` |
| Man-at-Legs Shot | entered from Wait when the burst cooldown reaches the reused `mSearchHeight` 50 s, and always after a Flick; damage resets the cooldown; shell on each attack loop during a 2.5 s on / 1.0 s off burst | `Shot` state, `shotCooldownSeconds`, `burstOn/OffSeconds`, `output.fireShell` |

## Six-gate status for this commit

| Gate | Status | Evidence |
|---|---|---|
| 1. Exact identity and spawn | source-backed audit (PASS at audit level) | audit identity table; no runtime spawn in this slice |
| 2. Autonomous movement and animation | BLOCKED | requires IKSystemMgr + animation key events; none exist in the port yet |
| 3. Attacks and receivers | PARTIAL (policy) | `footCrush`, `shake`, `fireShell` intents tested; receivers and the lane-20 shell pool not wired |
| 4. Death and corpse | PARTIAL (policy) | `dropTreasure` / `birthChildren` tested; no runtime death/corpse path |
| 5. Actual transport and reward | UNTESTED | depends on #06 reward/cargo lane |
| 6. Cleanup and re-entry | UNTESTED | needs the actor lifecycle host |

This is a source-mechanics increment, not a runtime acceptance claim. It must
not be reported as playable or as family complete.

## Remaining blockers and next bounded slices

1. **IK host.** The port has no `IKSystemMgr`/leg-joint equivalent. Until one
   exists, Walk cannot move the body and foot crush cannot be driven by real
   leg state. This is the largest blocker for gates 2-4.
2. **Animation key events.** `landingKey2`, `flickKey2` and `shotLoop` must come
   from the authoritative animation clock (lane 08) once the bank exists. The
   current visual path is bind-pose only.
3. **Man-at-Legs shells.** `fireShell` must be consumed by lane 20's projectile
   contract (pool of 10, speed 600, `InteractBomb` 10 / 500). No request should
   spawn a shell in this module.
4. **Stuck-Pikmin damage and collision parts.** `tama`/leg-tube collision and
   the "only stuck Pikmin damage" rule are host-side; they belong with the
   collision and receiver lanes.
5. **Death children.** ShijimiChou and Mitites births depend on the flying lane
   (15) and ground lane (14) managers.

## Shell pool budget (follow-up, native `a75734d9`)

Man-at-Legs shell emission is now bounded by the source in-flight pool of 10:
the host reports `shellsInFlight` and the policy suppresses a `shotLoop` request
while the pool is full (`pc_p2_long_legs_fsm.cpp`). This is the lane's
"projectile/helper budget" boundary; the actual shell object and lifetime remain
lane 20. Patch `native-candidates/long-legs-policy/0002-*.patch`; standalone and
ctest `PASS LONG_LEGS_FSM`.

## Integration

The maintained integration lead should apply
`native-candidates/long-legs-policy/0001-*.patch` (native base
`f9e139d8`) and then `0002-*.patch` on top (they apply to the #446-integrated
policy, whose file content is identical), and keep the module additive. The host
wiring (IK, animation events, projectile consumption) is a later, separately
reviewed slice.
