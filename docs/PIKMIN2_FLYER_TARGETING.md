# P2 flyers in the Pikmin 1 port: the targeting rule (#960)

Pikmin 1 Pikmin never acquire or keep an airborne enemy as a target
(`piki.cpp` `graspSituation` requires `!isFlying()`, `aiAttack.cpp` `findTarget`
and the `ActAttack` re-target at `:325` drop it). In Pikmin 2 the same enemies are
hit: thrown Pikmin latch onto a hovering body, and once enough weight drags it
down (or it lands to attack) the whole squad fights it. The port keeps generic
Pikmin AI exactly as it is and reproduces the Pikmin 2 rule with the existing
Pikmin 1 flag.

## The rule

Pikmin 2 `EnemyBase::isFlying()` is `isEvent(0, EB_Untargetable)`
(`native/pikmin2-research/include/Game/EnemyBase.h:167`). A flyer's states set and
clear `EB_Untargetable`; the port mirrors that onto the bound actor's
`CF_IsFlying` every source tick (`pc_port/pc_p2_flyer.h`, `airborne()`):

| flyer state | `EB_Untargetable` | port: `CF_IsFlying` | consequence |
|---|---|---|---|
| Wait / Move / Chase / Attack / FlyFlick, TakeOff after its KEY2, Fall before its descent frame | set | set | ground Pikmin skip it (`piki.cpp:1000`, `aiAttack.cpp:217`) and abandon an unstuck attack (`aiAttack.cpp:325`); no gravity, the FSM owns the height |
| Fall after its descent frame, Land, Ground, GroundFlick, TakeOff before KEY2 | cleared | cleared | gravity applies, the whole squad can engage it |
| Dead | set | cleared (falls) | corpse settles on the ground |

The other half of the contract needs no engine change:

* **Thrown Pikmin latch.** `PikiFlyingState::procCollideMsg` sticks a thrown Pikmin
  to any `st__` collision part of an organic teki and has no flying check; the
  actor wears the species' retail `enemycoll` tree instead of its vehicle's
  (`pc_port/pc_p2_flyer_coll.*`, update-inactive parts placed by the host every
  tick, so the collision never depends on the actor being drawn). The Lock-On
  cursor already pins a flying target at twice the offset so the throw's peak lands
  on it (`navi.cpp` `pcPinCursorToLock`, `lockPinScale`).
* **Stuck Pikmin keep biting.** `aiAttack.cpp:743` attacks the stick object with
  no flying check.
* **Weight brings it down.** The species FSM counts the stuck Pikmin
  (`getFlyingNextState`: `ip01` stuck or `fp04` seconds), so latching drags it into
  Fall, Land and Ground, and a shake-off (FlyFlick) flicks them off otherwise.

The flag is a pure function of the species FSM state. The FSM runs on a fixed 30 Hz
source clock with an LCG seeded from the generator token, so it is deterministic
and identical on every netplay peer (no wall clock, no `rand()` in sim state).

Vanilla Pikmin 1 flyers (Snitchbugs, Bulbmin, ...) do not go through this path and
behave as before.

## Adding a flyer

1. Give the actor the species' retail collision tree (`P2FlyerColl::bind`) and
   release the host's platform (`mPlatMgr.release()`, done by `bind`): a leftover
   platform mesh reports contacts whose part the tree cannot resolve.
2. Mirror `EB_Untargetable` with `startFlying()` / `finishFlying()` from the FSM
   output each tick and drive the height only while flying (the host integrates the
   velocity, so map collision still applies).
3. Refuse to capture a Pikmin that is mid-throw (`PIKISTATE_Flying`): the captain
   adapter clears `Piki::mNavi`, which the flying state reads every tick.

## Species

* **57 Kurage / 72 OniKurage** (Lesser / Greater Spotted Jellyfloat):
  `pc_port/pc_p2_kurage_own_host.*`, retail parms, collision trees and clips in
  `pc_port/pc_p2_kurage_own.h`. The Greater also sucks the captain into a mouth
  slot (`suckNavi`, one captain through the shared demon captain bridge), carries
  it into Drop, and vomits it out with the fp24 damage from GroundFlick (or Dead).
* **77 ShijimiChou** (Unmarked Spectralids): not admissible without a kill path.
  Its `damageCallBack` returns false (`shijimiChou.cpp:384`), so Pikmin, thrown or
  latched, never damage it; the only death is `EB_Bittered` plus touching the ground
  (`shijimiChou.cpp:313`, the bitter spray), and the port has no bitter spray.
  It is untargetable while flying and leaves a carcass only through that path, so a
  natural kill, carry and Onion receipt is unreachable. This is the same class as the
  unkillable enemies of the #888 no-check rule; it needs an owner ruling (exclude it
  like 9, 10, 11 and 16, or wait for a spray mechanic).

## Jellyfloat suction polish (owner playtest 2026-09-30, #960)

Four owner findings, three causes:

* **Standing Pikmin were never sucked** (both species). Source
  `Kurage::suckPikmin` takes every live Pikmin under the bell; the port's receiver
  gated admission on P1 `Piki::mayIstick()`, which is true only mid-throw or in
  attack/carry mode, so a Pikmin walking under the body never entered the suction
  and the body "just hovered". The receiver now uses a source-shaped eligibility
  for campaign OWN owners (`pc_p2_kurage_suction_policy.h`): every live Pikmin not
  already stuck, except unsafe P1 states (thrown, dying, held, ...). The
  Lesser (57) only ever sucks Pikmin (`Kurage.cpp:463-526` iterates `pikiMgr`
  only); only the Greater (72) sucks the captain (`OniKurage::suckNavi`).
* **Capture height.** The source stomach is the `suck` part on the `Proom` joint
  (enemycoll.txt, joint 4), not the body origin. The port held Pikmin at the
  origin minus the part radius (15/25 units under the bell). The host now places
  the part at the retail Proom position of the drawn pose
  (`pc_p2_kurage_proom.h`, regenerate/check with
  `scripts/kurage_proom_offsets.py`), pulls Pikmin to it and holds them on a
  ring inside the stomach sphere; the Greater's captain hangs from it
  (+ `kCaptainHoldLift`). `P2_KURAGE_HOLD` logs the held height against the body
  origin and centre.
* **Stale translucency.** The no-depth-write, deferred translucent bell from #973
  never reached the smoke package: `output/p2-content-dense` still held the
  pre-#973 Kurage/OniKurage/MiniHoudai bakes (recorded only as "24 poses"), so the
  bell wrote depth and hid the Onion beam and the carry counter flares behind it.
  Cache entries now record converter revisions (`density.REQUIRED_REVISIONS`) and
  `p2_smoke_seed.stage_content` re-extracts a stale entry like a sparse one.
* **Suction wind** (`pc_p2_kurage_fx.*`): while the attack clip's suction window is
  open, one P1 Blowhog wind jet (`EFF_Mar_WindJet`) plus its ground dust is emitted
  per 30 Hz source tick, aimed up from the ground under the body. Visual only;
  logged as `P2_KURAGE_FX kind=suction`.
