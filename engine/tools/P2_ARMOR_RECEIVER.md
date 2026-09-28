# Armor (Cloaking Burrow-nit, EnemyID 15) damage receiver + stone flick

Issue #407 / #165. Source: `Game/Entities/Armor.cpp` at research revision
`632af93787b9c95b63f0c13be32b161375ce3a96` (`native/pikmin2-research`).

## Source rule (retail)

`Obj::damageCallBack` (:117-128):

```cpp
if (isEvent(0, EB_Bittered)) { addDamage(damage, 1.0f); return true; }
if (collpart && collpart->mCurrentID == 'dmg1') { addDamage(damage, 1.0f); return true; }
return false;
```

Damage is accepted only while bittered, or when the collided part id is
`'dmg1'`. A null part and every other part id reject. `Obj::hipdropCallBack`
(:134-141) routes through the same predicate and returns its negation.

`Obj::doStartStoneState` (:147-162) walks the actor's stickers and, for every
creature with `isStickToMouth()`, sends
`InteractFlick(this, 0.0f, 0.0f, FLICK_BACKWARD_ANGLE)`.

## P1 host facts

* `InteractAttack::mCollPart` for a stuck-Piki hit is the *target's* collision
  part (`aiAttack.cpp` passes `piki->getStickPart()`, and
  `Creature::startStickObject` stores the part passed on the stuck-to object).
  It is therefore `CollPart::getID().mId` on the host, the same value class as
  the source `mCurrentID`. Direct/throw hits carry `nullptr`.
* `InteractAttack::actTeki` / `InteractBomb::actTeki` are the shared routing
  points (`tekiinteraction.cpp`); `InteractAttack::actCommon` gates on
  `isVisible`, after which the strategy accumulates `mStoredDamage`.
* The Armor is a visual-only pose bank riding the P1 Chappy placement vehicle
  (`pc_p2_batch2.cpp`). Its collision comes from the P1 Chappy model, not the
  source Armor model. No `dmg1` string exists in the worktree or in
  `pikmin-local` assets; the port queries the loaded `CollInfo` at setup and
  reports `dmg1=present|absent` honestly.
* The P1 host has no `EB_Bittered` and no `doStartStoneState` /
  `doFinishStoneState` lifecycle.

## Port implementation

`pc_port/pc_p2_armor_receiver_policy.h` (pure, `<cstdint>` only) encodes the
exact source predicate and the port approximation:

```
sourceAccepts(bittered, has_part, part_id) == bittered || (has_part && part_id == 'dmg1')
decide({bittered, has_part, part_id, weakpoint_active, weakpoint_id}):
    bittered                                -> AcceptBittered
    has_part && part_id == 'dmg1'           -> AcceptDmg1
    weakpoint_active && has_part && part_id == weakpoint_id -> AcceptWeakpoint
    otherwise                               -> Reject
```

`pc_port/pc_p2_armor.cpp` registers the receiver with the FSM actors and:

* `resolveReceiverPart` prefers `CollInfo::getSphere('dmg1')`; when absent it
  registers the bounding sphere (the first collision part) as the documented
  single weakpoint sphere and logs
  `P2_ARMOR_RECEIVER_PART ... dmg1=absent weakpoint=<id> mode=port_bounding_sphere`.
  If neither resolves, `mode=reject_all`. This is a **port approximation, not
  retail fidelity**: the P1 weakpoint id is the Chappy bounding-sphere part, not
  the source Armor `dmg1`.
* `pc_p2_armor_receiver_rejects` is called from `InteractAttack::actTeki` and
  `InteractBomb::actTeki`; it returns true only for a registered Armor that the
  policy rejects, causing the hit to be dropped before `mStoredDamage`
  accumulates. Unregistered actors fall through unchanged. It logs
  `P2_ARMOR_RECEIVER ... decision=accept|reject reason=bittered|dmg1|weakpoint|reject`.
* `pc_p2_armor_set_bittered` is the explicit host/fixture input for the
  missing `EB_Bittered` event (logged as `P2_ARMOR_BITTERED`).
* `pc_p2_armor_start_stone` / `pc_p2_armor_finish_stone` implement the source
  flick (snapshot the sticker list, flick every `isStickToMouth()` sticker and
  the port mouth-slot capture with `InteractFlick(actor, 0, 0,
  FLICK_BACKWARDS_ANGLE)`). Because the host has no petrification, the update
  fires it on the rising edge of `TEKIOPT_Pressed` (the host flattened/
  incapacitated analogue); setup logs
  `P2_ARMOR_STONE_NOTE host_lifecycle=absent port_analogue=pressed`.

The source `hipdropCallBack` shares `sourceAccepts`; the P1 host routes purple/
press damage through `InteractPress`, which carries no collision part, so the
hipdrop leg is not separately wired here (recorded unmeasured).

## Tests

```
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port \
    tools/p2_armor_receiver_policy_test.cpp -o ../p2_armor_receiver_policy_test.exe
../p2_armor_receiver_policy_test.exe   # p2_armor_receiver_policy_test PASS
```

The matrix covers the exact source rule, the port weakpoint substitution, the
"never silently accept all damage" case (null part / active weakpoint still
rejects) and the bittered override. The compiler used for the native test is
`C:/msys64/mingw64/bin/g++.exe`.

## Honest limits

* Whether `dmg1` is actually present is only known at runtime; the port logs it
  and selects `source_dmg1` vs `port_bounding_sphere` vs `reject_all`.
* The weakpoint id substitution is a documented approximation. No claim of
  retail part-id fidelity is made.
* The stone flick is driven by the host press state, not a petrified lifecycle,
  because the P1 engine has none.
* Live fixture execution (`experimental/pikmin2_armor_receiver_behavior.py`) is
  owned by the runtime slot and is not run here.
