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
