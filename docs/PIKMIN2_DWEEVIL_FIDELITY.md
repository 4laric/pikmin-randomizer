# P2 Dweevil family fidelity (#999)

Owner playtest of the smoke roster, 2026-09-30, Otakara family: Fiery 59, Caustic 60, Munge 61,
Anode 62. Volatile 93 (BombOtakara) shares the code but its mechanics branch (#964) is unmerged;
see "Volatile 93" below. This page is the audit record: what the decomp says, why the port
differed, what changed, and the evidence. Native code is on `claude/p2-dweevil-fidelity`
(fork/main `b9b06912d` base). Follow-up to #884.

Decomp citations are `native/pikmin2-research/src/...` at the pinned revision
`632af93787b9c95b63f0c13be32b161375ce3a96`; `enemycoll.txt` is the disc file
`otakara/enemycoll.txt` as staged in `output/p2-content-dense/FireOtakara/FireOtakara/`.

## Summary

| # | Owner report | P2 truth | Port cause | Fix |
|---|---|---|---|---|
| 1 | too slow | horizontal target speed is exactly fp06 (80; Munge 100) on any slope | fp06 was applied correctly, but the P1 host projects the drive onto the ground plane and re-normalises it, so the horizontal part shrank with the slope (80 -> 61 at 40 degrees); the log also showed stop-and-go which is the source Move/Turn/Wait rhythm | slope gain so the projected horizontal speed is fp06 again; the stop-and-go is unchanged because it is source |
| 2 | stuck on a slope | no pathfinding: one fp06 step directly away from the nearest Pikmin/Navi, clamped to the 200 territory | the P1 host treats slip-coded and steep triangles as sliding ground or walls, so a blind straight escape can pin the body | stalled-Move detector plus side-step heading (no teleport); logs each stall and the choice |
| 3 | never saw a treasure pickup | Take/ItemWait/ItemMove/ItemTurn/ItemFlick/ItemDrop states, treasure health fp01 (80, Munge 100) | no item states and no carried object existed; the header called them "N/A" | real P1 pellet carried through the engine mouth stick; all six item states; staging for the smoke package |
| 4 | no visual for the attack itself | charge emitter on the body during the wind-up, burst at mPosition on event 3, `attackTarget()` window of 1 s | one fire-and-forget particle at the feet; no charge visual; one-frame application | charge at the body, burst at the Dweevil, 1 s window with the source reach test, captains included |
| 5 | legs invincible, throw at the body | collision tree has exactly one stickable, damageable part (`body` r10, joint 11); `damageCallBack` damages only through a part | the P1 Chappy host tree is stickable/damageable everywhere and a captain punch (partless) did 10 damage | retail two-sphere tree; partless Pikmin/Navi attack refused |
| 6 | lingering effects | charge fades at event 3; nothing else persists | the Hiba flame generator was never finished (`pc_p2_otakara_fx_update/clear/reset` had no caller) | per-actor ledger with start/stop pairs on discharge, window end, death, forget |

## 5. Legs: the audit

Verdict: the owner is right about the legs and about every hit that does not go through a part.
One precision: the source does not say "from the ground", it says "through a part".

Collision tree (disc `otakara/enemycoll.txt`, all five species share it):

```
{none} {____} radius 15  joint 11   root / bounding sphere, not stickable, takes no hit
{body} {st__} radius 10  joint 11   the only stickable, damageable part
```

Joint 11 is `otakara` (the model's joint table: center, antennaL/R, four back-leg and four front-leg
joints, otakara). There is no sphere on any leg joint. The body joint sits 35.9 to 38.6 above the
feet in `wait1`/`move1`/`pivot1` (sampled from the disc `.bca` clips against the model hierarchy),
so the lowest stickable point is about 27 above the feet.

Every damage path:

| Path | Source | Result | Port |
|---|---|---|---|
| Pikmin attack while latched | `OtakaraBase::damageCallBack` damages only `if (collpart)` (OtakaraBase.cpp:190-197); the part is the stick part (aiAttack.cpp:88-90) | damage (to the treasure while carrying) | accepted, logged `part=body form=latched` |
| Ground punch / captain punch | partless `InteractAttack` (P1 aiAttack.cpp:688/707, navi.cpp:1879, naviState.cpp:3252) -> `damageCallBack` returns false | refused | refused, logged `part=none form=ground_punch`; 200 refusals in one run, health stayed 150 |
| Thrown Pikmin landing (press / fly collision) | `OtakaraBase` has no `pressCallBack`; `EnemyBase::pressCallBack` returns false (enemyBase.cpp:2790-2793); the Pikmin latches only if the part `isStickable()` (collinfo.cpp:806-808, pikiState.cpp:2336) | no damage; latches onto `body` only | consumed (#884); only `body` is stickable now |
| Purple hipdrop | `hipdropCallBack`: with a part, `damageTreasure(carrying ? otakaraLife : damage)`, then `EnemyBase::hipdropCallBack` adds the stun damage (OtakaraBase.cpp:203-217, enemyBase.cpp:2808-2818) | damage | unchanged (goes through `InteractAttack` with a part) |
| Bomb | `bombCallBack` -> `damageTreasure` (OtakaraBase.cpp:232-235), partless, accepted | damage | unchanged (`InteractBomb` path, not gated) |
| Earthquake | `earthquakeCallBack`: carrying -> `damageTreasure(otakaraLife)` (OtakaraBase.cpp:220-226) | drops the treasure | not modelled (no earthquake source in the P1 host) |

BombOtakara (93) overrides `damageCallBack` with no part test (BombOtakara.cpp), so it keeps the partless
path in the port.

## 4 and 6. Attack visuals and lifecycle

Source: `StateFlick::init` starts the charge emitter (`efx::TOtaCharge{fire,wat,gas,elec}`) on the center
joint; event type 3 (bank frame 35) fades it, creates the discharge burst at `mPosition` and sets
`mAttackActiveTimer = 0`; `Obj::doUpdateCommon` (OtakaraBase.cpp:85-92) then calls `attackTarget()` every frame
for one second in any state (OtakaraBase.cpp:580-610: XZ < 60, height within -25..+25, Navi and Piki).
`onKill`, stone and earthquake states call `finishChargeEffect`.

P1 stand-ins (`pc_p2_otakara_fxplan.h`): see the file header. Each generator is owned by a per-actor ledger
and every `P2_OTAKARA_FX_START` has exactly one `P2_OTAKARA_FX_STOP` (reasons: `discharge_start`, `window_end`,
`dead`, `forget`, `teardown`).

## Evidence

Run logs and frames live under `output/dweevil-runs/` (local, ignored). Baseline exe (fork/main
`b9b06912d`) sha256 `136524862af6344edd8d2702290d000b0ba893c59db4b1557a7e0c602218cea0`; final exe
(native `claude/p2-dweevil-fidelity` @ `0a4b1797b`) sha256
`649954b16aa7c3ea07c57f0dfbac8687e24db71660ffd2f523e194b3f33b6a40`, `ninja -n`: no work to do.

- Speed: measured horizontal speed while walking is 78 u/s at 80 commanded (Fire, Water) and 91 at
  100 (Munge) on flat ground; the port applies raw fp06 and the repo documents no P1 scale factor for
  any P2 species. The owner's Anode log showed 40-54 u/s in Move; I could not reproduce that in any
  bot run (terrain within the 200 territory of that slot is flat: mean 2.6 degrees, max 5.7). The
  source cycle Move -> Turn -> Wait at the 200 sight edge, and the captain's 160 u/s
  (NaviParms `p004`) against 80, are source behaviour and unchanged. What was wrong and is fixed:
  the horizontal speed shrank on slopes (P1 re-normalises the projected drive).
- Slopes: terrain grids around the five Forest of Hope slots (25-unit spacing) show steep cells
  (up to 50-69 degrees) only near the territory edges of slots 3138990329, 1877315663 and
  4222852521. No stall was reproduced in the bot runs; the detector and side-step are covered by
  unit tests and log `P2_OTAKARA_STALL` when they fire.
- Legs: baseline run, 9 of 15 hits on Fiery 59 were captain punches (`attacker=creature`, 10 each).
  Fixed build: `P2_OTAKARA_PART ... owner=navi part=none form=ground_punch verdict=partless_refused`,
  200 refusals in one run with health staying 150; Pikmin hits logged `part=body form=latched`.
- Treasure: `P2_OTAKARA_TREASURE_TARGET -> TAKE -> CARRY` (pellet 24 above the feet, stuck to the
  mouth, no free carry slot) `-> TREASURE_HIT` x6 (80 -> 0) `-> DROP reason=itemdrop pop=1`.
- Visuals and lifecycle: frames show the flame ring at the Dweevil during the window and a clean
  scene 36 frames after it; the baseline frames show a flame column still burning 20 s later.
  Logs: every `P2_OTAKARA_FX_START` has one `P2_OTAKARA_FX_STOP` in all runs.

## Open

- Earthquake and stone states are not modelled for the Dweevil (no source trigger in the P1 host).
- Electric and water stand-ins are approximate P1 particles; the shared attack-stream module
  (`claude/p2-titan-effects`) can replace `pc_p2_otakara_fxplan.h` when it lands.
- Volatile 93: shares the tree, slope speed and stall code; its bomb payload stays on #964. The
  partless refusal does not apply to it (BombOtakara.cpp has no part test).
