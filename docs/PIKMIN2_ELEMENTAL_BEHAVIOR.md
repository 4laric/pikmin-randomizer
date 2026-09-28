# Pikmin 2 lane-22 elemental/dweevil behavior model (#170, child #349)

This lane adds a pure-Python, engine-independent, source-anchored behavior
model for the lane-22 roster. It is the **policy/model slice only**; no native
FSM, receiver or actor install is added. Implementation owner: Codex through
shared account `4laric`.

- Module: `experimental/pikmin2_elemental_behavior.py`
- Tests: `tests/test_pikmin2_elemental_behavior.py`
- Primary source audit: [PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md](PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md) (#170)
- Receiver contract: [PIKMIN2_RECEIVER_PATHS.md](PIKMIN2_RECEIVER_PATHS.md) (#408)
- Supplementary: [PIKMIN2_DWEEVIL_ASSETS.md](PIKMIN2_DWEEVIL_ASSETS.md) (#349)

All decompilation anchors are repo-relative to `native/pikmin2-research` at
revision `632af93787b9c95b63f0c13be32b161375ce3a96` and use the line numbers at
that revision. Header (build-time) defaults and retail disc values are kept as
distinct fields and never flattened.

## 1. Roster

| ID | Constant | Classification | Emitted stimulus |
|---:|---|---|---|
| 20 | `Hiba` | `fixed_hazard` | `InteractFire` |
| 21 | `GasHiba` | `fixed_hazard` | `InteractGas` |
| 22 | `ElecHiba` | `fixed_hazard` | `InteractDenki` (or Fire/Bubble in versus mode) |
| 24 | `Tank` / `Ftank` | `blowhog` | `InteractFire` |
| 25 | `Wtank` | `blowhog` | `InteractBubble` |
| 59 | `FireOtakara` | `dweevil` | `InteractFire` |
| 60 | `WaterOtakara` | `dweevil` | `InteractBubble` |
| 61 | `GasOtakara` | `dweevil` | `InteractGas` |
| 62 | `ElecOtakara` | `dweevil` | `InteractDenki` |
| 93 | `BombOtakara` | `dweevil` | none (delegates to its Bomb payload) |

IDs are declared in `include/Game/enemyInfo.h:79-84,118-121,152` (audit line 7).
The three hazard IDs are registered spawnables but carry `EFlag_HasNoInfo` with
empty resource slots and `BDT_Empty`, so the module records them as fixed,
scenery-adjacent hazards rather than Piklopedia enemies (audit lines 11-13,49;
assets lines 46-58).

## 2. Fixed hazards Hiba / GasHiba / ElecHiba

**Activation and cadence.** Hiba and GasHiba register Dead/Wait/Attack
(`HibaState.cpp:14-20`, `GasHibaState.cpp:13-19`); Wait leaves on health or
timer and each Attack stimulates its target scan every update until death or
active-time expiry (`HibaState.cpp:127-159`, `GasHibaState.cpp:129-169`; audit
line 24). GasHiba's Attack stimulates only after `mAttackStartTime`, and its
active-time finish condition additionally requires a positive `mWaitTime`.
ElecHiba registers Dead/Wait/Sign/Attack (`ElecHibaState.cpp:13-20`): Wait
enters Sign on timer (or the versus counter), Sign charges for the warning
time, and Attack discharges until the active time or counter completes.

**Header vs disc timing.** The audit calls out the geyser timing differences.
The module keeps `HAZARD_TIMING_HEADER` (build-time defaults) separate from
`HAZARD_TIMING_DISC` (US GPVE01 rev 0 `<hazard>/enemyparm.txt`, assets lines
161-166):

| Hazard | Header wait/active/stop | Disc wait/active/stop |
|---|---|---|
| Hiba | 2.5 / 2.5 / 10.0 | 3.0 / 2.5 / 30.0 |
| GasHiba | 2.5 / 2.5 / 10.0 (+attack start 1.0) | 0.0 / 3.0 / 30.0 (+attack start 0.6) |
| ElecHiba | 2.5 / 2.5 warning / 10.0 | 1.5 / 1.5 warning / 30.0 |

**Linked-wire ownership.** GasHiba is associated with a nearby bridge/gate in
story outdoor mode and `setInitLivingThing` can temporarily mark it not living
until that link changes (`GasHiba.cpp:193-296,204-272`; audit lines 12,49).
ElecHiba is one two-node team born at ±`mSeperation/2`
(`ElecHibaMgr.cpp:110-131`, `ElecHiba.cpp:249-258`); only the parent drives FSM
updates (`ElecHiba.cpp:88-93`) and normal damage routes to the team head where
invulnerability is checked (`ElecHiba.cpp:139-157,752-776`; audit lines 13,26).
Neutral/red/blue discharge selects Denki/Fire/Bubble for both interaction and
visual effect (`ElecHiba.cpp:264-329,307-324,841-860`).

## 3. Blowhogs Tank (24) / Wtank (25)

Tank registers Dead/Wait/Move/MoveTurn/ChaseTurn/Attack/Flick
(`TankState.cpp:9-19`) and resets its blow/attack timers to Wait on init
(`Tank.cpp:29-44`). During Attack the expanding sweep supplies a sphere of
broad-phase candidates, then bounds vertical/lateral separation by
`mAttackRadius` and forward distance by the growing range; a radius-2.5 sphere
trace stops growth at a floor/wall collision (`Tank.cpp:266-319,325-368`,
`TankState.cpp:844-899`; audit line 28). Ftank supplies `InteractFire`
(`Ftank.cpp:121-125`); Wtank supplies `InteractBubble` (`Wtank.cpp:119-123`).
`onKill` finishes the effect before the base kill (`Tank.cpp:50-54`).
`blowhog_attack(...)` returns the concrete stimulus (or `None`) and
`blowhog_range(...)` models the range growth.

## 4. Dweevils (59-62) and BombOtakara (93)

All five share one `OtakaraBase` FSM with 14 states (`OtakaraBase.h:22-39`,
`OtakaraBaseState.cpp:14-34`) and one `interactCreature` stimulus per species
(audit lines 16-19,30).

**Treasure theft and exactly-once drop.** The shared search accepts only alive,
pickable, uncaptured pellets inside the home territory and only while not
already carrying (`OtakaraBase.cpp:395-417`). A chosen pellet is captured on
the `otakara` joint and given `mOtakaraLife` health
(`OtakaraBase.cpp:472-524`). Damage while a treasure is held decrements the
treasure's health, otherwise the Dweevil (`OtakaraBase.cpp:550-574`). A
death/stone/earthquake path (and the item-drop event type 2) calls
`fallTreasure`, ending capture and resetting collision geometry
(`OtakaraBase.cpp:530-544,242-304`, `OtakaraBaseState.cpp:680-727`; audit lines
30,34). `dweevil_drop(...)` enforces the exactly-once property: a second drop
for the same capture returns no drop, so a treasure cannot be refunded twice.

**BombOtakara payload boundary.** `initBombOtakara` requests the separate
`EnemyID_Bomb` payload, captures it on the `otakara` joint and sets `mCarrier`
(`OtakaraBase.cpp:649-677`); `doFinishWaitingBirthTypeDrop` reinitializes it
(`OtakaraBase.cpp:321-327`). Damage delegates to the payload: while bittered,
the Bomb `damageCallBack`; otherwise `forceBomb`; an earthquake also forces it
(`BombOtakara.cpp:42-87`; audit line 20). The bomb-carry states kill the
carrier if the payload pointer disappears and call `stimulateBomb` while
chasing; after 1.5 s `stimulateBomb` disables culling and calls the payload's
`forceBomb` (`OtakaraBaseState.cpp:744-846,863-907`, `OtakaraBase.cpp:699-707`;
audit line 30). This module **consumes** that shared blast contract and does
not duplicate projectile/explosion primitives (see projectiles lane #169).

## 5. Receiver immunity boundary

The emitted stimulus does not define immunity; the receiving Pikmin colour
decides. In `src/plugProjectKandoU/interactPiki.cpp` (audit line 43):

| Stimulus | Rejected colours | Extra gate | Panic |
|---|---|---|---|
| `InteractFire` (`:445`) | Red, Bulbmin | — | Fire |
| `InteractBubble` (`:503`) | Blue, Bulbmin | — | Bubble |
| `InteractGas` (`:531`) | White, Bulbmin | `gasInvicible` | Gas |
| `InteractDenki` (`:334`) | Yellow, Bulbmin | — | DenkiDying |

`pikmin_immune(...)` and `receiver_accepts(...)` encode this table, including
the generic invincibility gate that rejects before any elemental check
(receiver contract #408 section 4). Captain equipment and enemy-side
immunities must be audited separately and must not copy these Pikmin rules.

## 6. Reconstructed and unknown behavior

`RECONSTRUCTED` marks behavior the audit does not pin exactly; each function
also carries a `.reconstructed = True` attribute:

- `gashiba_linked_owner` — the exact `setInitLivingThing` gate is not
  reproduced.
- `elechiba_versus_stimulus` — the versus counter that selects the mode and its
  persistence across an area reload are not pinned (audit lines 26,51).
- `blowhog_range` — the source `emitCollideRatio` growth curve is modelled as
  linear (audit line 28; exact parms unknown, audit line 51).
- `bomb_otakara_payload` — the Bomb's own explosion lifetime/carcass is outside
  the audit (audit line 36).

`UNKNOWNS` records the remaining source-only gaps (audit lines 36,43,51):
exact runtime frame timing/radii, save/area-reload persistence, terrain
clearance for randomized placements, complete Bomb explosion lifetime, and the
absence of a captain/enemy-side immunity audit.

## 7. Scope, blockers and next native slice

**In scope:** the source-anchored policy model and its synthetic tests only.

**Not in scope / remaining blockers:**

1. **Native receiver wiring.** The P2 Gas/Denki receivers and the elemental
   discharge paths are source-anchored but not ported (receiver contract #408
   section 4; the port currently exercises P1 `InteractAttack::actPiki`).
2. **BombOtakara consuming lane 20 primitives.** The payload's damage and
   explosion must reuse the shared Bomb/projectile contract; do not fork a
   second explosion implementation.
3. **Source emission states.** The runtime receive states (Hiba/GasHiba
   emission, blowhog expanding sweep, dweevil discharge) are not installed.
4. **Cleanup / re-entry.** Save/reload, area re-entry and day transitions for
   theft, drop and payload chase are untested (audit line 51).

**Recommended next native slice:** add the shared-base dweevil spawn profile
and treasure capture/drop receiver first (IDs 59-62, then 93 reusing the
existing Bomb contract), gated by a focused fixture that verifies exactly-once
theft/drop and no duplicate explosion, then the fixed-hazard emission states
(20/21/22) with the ElecHiba two-node team.

## 8. Verification

```powershell
py -3.12 -m pytest tests/test_pikmin2_elemental_behavior.py -q   # 36 passed
py -3.12 -m pytest tests/test_pikmin2_bulblax_behavior.py -q     # import safety
```

This slice makes no runtime/native acceptance claim.
