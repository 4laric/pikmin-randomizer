# Pikmin 2 elemental enemy source audit (issue #170)

This is a source audit for the ten requested IDs. It records behavior visible in the matching decompilation; it does not claim gameplay completion or authorize native edits.

## Provenance and scope

Read-only source: the `native/pikmin2-research` checkout, remote `https://github.com/projectPiki/pikmin2.git`, revision `632af93787b9c95b63f0c13be32b161375ce3a96`. Anchors below are repo-relative to that checkout and use the line numbers at that revision. Numeric IDs are declared in `include/Game/enemyInfo.h:79-84,118-121,152`.

| ID | Native type | Elemental interaction source | Initial/reset observation |
|---:|---|---|---|
| 20 | Hiba (fire geyser) | `Hiba::interactFireAttack` scans live Navi/Pikmin and stimulates `InteractFire` (`src/plugProjectNishimuraU/Hiba.cpp:148-178`). | `onInit` resets timer/alive and starts wait (`Hiba.cpp:31-50`); no persistent element state is set. |
| 21 | GasHiba (gas pipe) | `GasHiba::interactGasAttack` scans live Navi/Pikmin and stimulates `InteractGas` (`GasHiba.cpp:157-187`). | `onInit` resets timer, bridge/gate links, and starts wait (`GasHiba.cpp:33-53`); `setInitLivingThing` can temporarily mark it not living until a nearby bridge/gate changes (`GasHiba.cpp:193-296`). |
| 22 | ElecHiba (electric wire) | `interactDenkiAttack` applies `InteractDenki`, or Fire/Bubble in versus attribute modes (`ElecHiba.cpp:264-329`). | Birth creates a two-node team at ±`mSeperation/2` (`ElecHibaMgr.cpp:110-131`); init recursively initializes child, sets neutral mode and clears attribute counters (`ElecHiba.cpp:53-82`). |
| 24 | Tank / Ftank (fiery Blowhog) | `Tank::isAttackable` finds targets and calls virtual `interactCreature` (`src/plugProjectNishimuraU/Tank.cpp:266-319`); Ftank supplies `InteractFire` (`src/plugProjectNishimuraU/Ftank.cpp:121-125`). | `onInit` resets blow/attack timers and starts wait (`src/plugProjectNishimuraU/Tank.cpp:29-44`); `onKill` finishes effect before base kill (`Tank.cpp:50-54`). |
| 25 | Wtank (watery Blowhog) | `Wtank::interactCreature` stimulates `InteractBubble` (`Wtank.cpp:119-123`). | It inherits Tank FSM/timing and uses Wtank effects; stone/earthquake/movie hooks stop or hide effects (`Tank.cpp:117-207`, `Wtank.cpp:42-113`). |
| 59 | FireOtakara (Fiery Dweevil) | `interactCreature` stimulates `InteractFire` (`FireOtakara.cpp:41-46`); charge/discharge effects are `TOtaChargefire`/`TOtaFire` (`FireOtakara.cpp:52-94`). | Shared Otakara init/reset applies; no species-specific persistent element flag is assigned in this file. |
| 60 | WaterOtakara (Caustic Dweevil) | `interactCreature` stimulates `InteractBubble` (`WaterOtakara.cpp:42-47`); effects are `TOtaChargewat`/`TOtaWat` (`WaterOtakara.cpp:53-95`). | Same shared init/reset and treasure state as other Otakara types. |
| 61 | GasOtakara (Munge Dweevil) | `interactCreature` stimulates `InteractGas` (`GasOtakara.cpp:41-46`); effects are `TOtaChargegas`/`TOtaGas` (`GasOtakara.cpp:52-94`). | Same shared init/reset and treasure state as other Otakara types. |
| 62 | ElecOtakara (Anode Dweevil) | `interactCreature` builds direction and stimulates `InteractDenki` (`ElecOtakara.cpp:41-61`); effects are `TOtaChargeelec`/`TOtaElec` (`ElecOtakara.cpp:67-109`). | Same shared init/reset and treasure state as other Otakara types. |
| 93 | BombOtakara (Volatile Dweevil) | Its carried Bomb is delegated damage/explosion owner: damage calls Bomb `damageCallBack` only while bittered, otherwise `forceBomb`; earthquake also forces it (`BombOtakara.cpp:42-87`). | Shared `initBombOtakara` requests the separate `EnemyID_Bomb` payload, captures it on the `otakara` joint and sets `mCarrier` (`OtakaraBase.cpp:649-677`). The Dweevil's `doFinishWaitingBirthTypeDrop` reinitializes this payload (`OtakaraBase.cpp:321-327`). |

## Shared state machine, animation events, and damage

Hiba and GasHiba each register Dead/Wait/Attack (`HibaState.cpp:14-20`; `GasHibaState.cpp:13-19`). Wait transitions on health or timer. Hiba Attack stimulates every update and requests animation finish on death or active-time expiry (`HibaState.cpp:127-159`). GasHiba Attack stimulates only after `mAttackStartTime`; its active-time finish condition also requires positive `mWaitTime` (`GasHibaState.cpp:129-169`). Both return at `KEYEVENT_END` and fade effects in cleanup. Their Dead states disable targeting/damage, call `generatorKill`, and create a death effect (`HibaState.cpp:26-48`; `GasHibaState.cpp:25-48`).

ElecHiba registers Dead/Wait/Sign/Attack (`ElecHibaState.cpp:13-20`). Wait enters Sign on timer (or versus counter condition), Sign disables culling and charges for warning time, and Attack discharges until active time/counter completion (`ElecHibaState.cpp:93-131,145-198,204-268`). Only the parent executes FSM updates (`ElecHiba.cpp:88-93`), while child initialization is recursive (`ElecHiba.cpp:67-73`). Normal damage routes to the team head through `addDamageMyself` and `damageIncrement`; invulnerability is checked there (`ElecHiba.cpp:139-157,752-776`). Neutral/red/blue discharge changes both interaction and visual effect (`ElecHiba.cpp:307-324,841-860`). Counters are reset on init, and versus counters can change the mode during attack (`ElecHiba.cpp:74-81,904-940`); persistence across area reloads is not established by these functions.

Tank registers Dead/Wait/Move/MoveTurn/ChaseTurn/Attack/Flick (`TankState.cpp:9-19`). Its attack `KEYEVENT_2` starts the effect; while blowing, the expanding sweep tests targets and emits the concrete element, and `KEYEVENT_END` selects the next state (`TankState.cpp:844-899`). A sphere supplies broad-phase candidates; exact hit tests bound vertical/lateral separation by `mAttackRadius` and forward distance by the growing range. `emitCollideRatio` grows that range with `mAttackTimer` and traces a radius-2.5 sphere to stop growth at floor/wall collision (`Tank.cpp:266-319,325-368`). Ftank supplies Fire (`Ftank.cpp:121-125`); Wtank supplies Bubble (`Wtank.cpp:119-123`). Tank's effect lifecycle is stopped on kill, stone, earthquake-fit, movie and birth-drop hooks (`Tank.cpp:50-54,117-207`).

All five Dweevils use `OtakaraBase::FSM`, which registers normal, item-carry, and Bomb-carry states (`OtakaraBaseState.cpp:14-34`). Flick attack starts charge; animation event type 2 flicks Pikmin and event type 3 ends charge/creates discharge; event type 1000 selects move/turn/wait (`OtakaraBaseState.cpp:71-136`). While carrying a treasure, item-drop event type 2 calls `fallTreasure(true)` (`OtakaraBaseState.cpp:680-727`). Bomb-carry states kill the Dweevil if the payload pointer disappears and call `stimulateBomb` while chasing (`OtakaraBaseState.cpp:744-846,863-907`); after 1.5 seconds `stimulateBomb` disables culling and calls the payload Bomb's `forceBomb` (`OtakaraBase.cpp:699-707`).

## Treasure theft/drop and ownership

Shared Otakara code searches only alive, pickable, uncaptured pellets within the home territory (`OtakaraBase.cpp:395-417`), captures the chosen pellet on the `otakara` joint and gives it `mOtakaraLife` health (`OtakaraBase.cpp:472-524`). Damage while a treasure is held decrements treasure health; otherwise it damages the Dweevil (`OtakaraBase.cpp:550-574`). A death/stone/earthquake path calls `fallTreasure`, ending capture and resetting collision geometry (`OtakaraBase.cpp:530-544` and `242-304`). This is the evidence for theft/drop behavior; it does not prove a particular placement survives a reload.

BombOtakara is an exception: the captured object is a live Bomb enemy, created by `initBombOtakara` and linked with `mCarrier` (`OtakaraBase.cpp:649-677`). Its own callbacks hand control to that Bomb or force it to explode (`BombOtakara.cpp:42-87`). The Bomb's exact explosion cleanup/lifetime is owned by the Bomb implementation, outside this bounded audit; acceptance must observe both the payload and carrier after detonation.

The shared base also starts the normal dead animation and calls `kill` on animation end (`OtakaraBaseState.cpp:40-57`). The broader `EnemyBase::onKill` drop branch is shared engine behavior; source review identified an ItemHoney manager guard in the non-JP branch and a JP comment about a possible BombOtakara Piklopedia crash. That comment is not evidence of a reproduced crash and is not treated as one here.


## Receiver immunity boundary

The emitted stimulus does not itself define species immunity. In `src/plugProjectKandoU/interactPiki.cpp`, `InteractDenki::actPiki` (334) excludes Yellow/Bulbmin and requests DenkiDying; `InteractFire::actPiki` (445) excludes Red/Bulbmin; `InteractBubble::actPiki` (503) excludes Blue/Bulbmin; `InteractGas::actPiki` (531) excludes White/Bulbmin and checks `gasInvicible`. Fire/Bubble/Gas request their corresponding Panic subtype. Current-state invincibility and transition eligibility also gate these reactions. Captain equipment and enemy-side immunities require their own receiver audit; do not copy Pikmin rules to them.

## Wire linkage and persistence classification

Confirmed reset-on-init state: Hiba/GasHiba timers and alive flags; GasHiba bridge/gate pointers; ElecHiba versus mode/counters and child init; Tank timers/blow flag; Otakara target, treasure pointer/health, offsets and collision radii (`Hiba.cpp:31-50`; `GasHiba.cpp:33-53,193-198`; `ElecHiba.cpp:53-81`; `Tank.cpp:29-44`; `OtakaraBase.cpp:33-66,450-466`).

Confirmed runtime linkage: ElecHiba parent/child team and ±separation placement (`ElecHibaMgr.cpp:110-131`); `setElecHibaPosition` computes ±separation in `ElecHiba.cpp:249-258`; GasHiba bridge/gate association in story outdoor mode (`GasHiba.cpp:204-272`); Otakara treasure capture joint and Bomb payload/carrier (`OtakaraBase.cpp:493-521,649-677`).

Unresolved from source-only inspection: whether randomized placements preserve valid terrain/clearance for every elemental footprint; whether state survives a save/area reload or day transition; exact frame timing and radius values from runtime parameter assets; and complete Bomb explosion object lifetime/carcass/Piklopedia behavior. These remain implementation and playtest risks.

## Acceptance tests for a gameplay implementation

1. Spawn each ID 20, 21, 22, 24, 25, 59, 60, 61, 62 and 93 in a controlled room. Verify its normal target interaction (Fire, Gas, Denki, Fire, Bubble, Fire, Bubble, Gas, Denki, Bomb respectively), damage, animation event timing, and effect start/fade.
2. For ID 22, verify the two wire nodes are correctly separated, one parent drives the attack, damage is team-owned, versus red/blue counters select the documented Fire/Bubble mode, and the birth path safely handles failure to allocate the partner (`ElecHibaMgr.cpp:110-131`).
3. For IDs 59-62, give each a pickable pellet, verify capture on theft, treasure-health damage, forced drop on stone/earthquake/death, and successful Pikmin recovery.
4. For ID 93, verify Bomb payload birth, `mCarrier` linkage, bittered damage path, normal/earthquake forced detonation, and cleanup of both payload and carrier without duplicate explosion or stale capture.
5. Save/reload and leave/re-enter the area during wait, attack, theft, drop and (for ID 93) payload chase. Compare state, effects, collision, generator counts and drops to the intended reset/persistence policy.
6. Repeat representative placements on dry, water, gas, electric and obstructed terrain; verify no elemental hazard is spawned inside walls, invalid water volumes, bridges or gates and that all attack/collision routes remain reachable.

No native files were edited and no gameplay tests were run for this audit.
