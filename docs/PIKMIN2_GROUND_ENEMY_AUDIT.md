# Pikmin 2 ground enemy source audit (#165)

Source: [projectPiki/pikmin2](https://github.com/projectPiki/pikmin2), revision `632af93787b9c95b63f0c13be32b161375ce3a96`, inspected read-only through `native/pikmin2-research`. Source-relative paths and function/registration line anchors below identify the reviewed code. Numeric identities come from `include/Game/enemyInfo.h`. This covers nine IDs as a source specification; it does not establish native implementation or natural playthrough acceptance.

## Sheargrubs: UjiA (12), UjiB (13)

UjiA registration (`src/plugProjectNishimuraU/UjiaState.cpp:16`) lists Dead, Press, Stay, Appear, Dive, Move, MoveSide, MoveCentre, MoveTop, GoHome, Attack1. UjiB (`UjibState.cpp:16`) adds Attack2 and Eat. These are separate FSMs with shared-looking states, not an identical combat contract.

UjiA `StateAttack1::exec` (UjiaState.cpp:510) chooses continued bridge attack, movement on the bridge, or home based on bridge state; event 2 calls `breakTargetBridge` only if the bridge is still breakable. END takes the selected state. This is bridge destruction, not a Pikmin bite. UjiB `StateAttack2::exec` (UjibState.cpp:922) applies in-water damage, toggles NoInterrupt at events 2/3, and calls `attackNavi` plus `eatPikmin` at event 4. END prioritizes death, then Eat when Pikmin are attached, then territory/home versus Move. Validate bridge ownership, destroyed-bridge interruption and mouth attachment separately.

## Shearwig: Tobi (14)

Tobi registration (`src/plugProjectNishimuraU/TobiState.cpp:16`) contains the UjiB-style state names plus Fly. `StateAttack2::exec` (672) is its own bite implementation and must not be replaced by UjiA bridge attack. `Tobi.cpp::isFlyingLife` (278) compares health/general health with the takeoff-health ratio. `randomFlyingTarget` (248) selects a target above map ground by configured flight height and adjusts vertical target velocity.

Fly init (TobiState.cpp:547) enables invulnerability and untargetability. Fly exec (562) updates target movement and requests landing once health ratio exceeds the land-health ratio; END returns to Move. This documents entry/exit gates, not the complete source of health regeneration. Verify regeneration/update ordering, flight terrain clearance, thrown Pikmin interactions and bitter/earthquake interruption before treating the species as complete.

## Cloaking Burrow-nit: Armor (15)

Registration (`src/plugProjectNishimuraU/ArmorState.cpp:17`) lists Dead, Stay, Appear, Dive, Move, MoveSide, MoveCentre, MoveTop, GoHome, Attack1, Attack2, Eat, Flick, Fail. `Armor.cpp::damageCallBack` (117) accepts damage while bittered or when the collision part has ID `dmg1`; other parts are rejected. A single generic body hitbox would erase that vulnerability rule. `doStartStoneState` (147) sends Flick to mouth-stuck creatures.

`StateAttack2::exec` (ArmorState.cpp:582) calls `attackPikmin` only for motion frames strictly between 17 and 27; event 2 creates an effect, event 3 attacks Navi, and END selects Dead, Eat or Fail. `StateEat::exec` (644) calls `killSlotPiki` at event 2. Capture, visible attack and lethal consumption are distinct boundaries. Verify front/rear collision parts, the exact frame window, bitter release, empty slots, death during capture and emergence geometry.

## Anode Beetle: ElecBug (28)

Registration (`src/plugProjectNishimuraU/ElecBugState.cpp:21`) lists Dead, Wait, Turn, Move, Charge, Discharge, ChildCharge, ChildDischarge, Reverse, Return. Init (`ElecBug.cpp:31`) enables invulnerability and starts with no partner. Pairing links existing objects: `startChargeState` (301) calls `startChildChargeState` (311), setting reciprocal pointers. This is not the ElecHiba manager's two-node allocation contract. `resetPartnerPtr` (273) and `finishPartnerAndEffect` (379) clear reciprocal references; onKill (46) uses the latter.

Discharge exec (ElecBugState.cpp:299) calls `checkInteract` every update with a partner; event 2 starts the discharge visual and END returns to Turn. Missing partner ends the effect and requests motion finish. ChildDischarge exec (408) similarly finishes on partner loss, but END returns to Wait. `ElecBug.cpp::checkInteract` (411) implements between-beetle Denki geometry; `collisionCallback` (108) also shocks direct contacts during discharge when not bittered.

`pressCallBack` (ElecBug.cpp:136) can flip a living, non-bittered beetle when a Pikmin presses it in eligible states; an actively discharging beetle also sends Denki to that Pikmin. Reverse init (ElecBugState.cpp:443) unlinks the pair and disables invulnerability; cleanup restores it. Stone entry (ElecBug.cpp:189) also removes invulnerability and pairing. Verify both sides when one beetle flips, dies or petrifies; verify singleton recovery and stale-pointer prevention.

Receiver boundaries: `src/plugProjectKandoU/interactPiki.cpp::InteractDenki::actPiki` (334) excludes Yellow/Bulbmin and checks invincibility/state transition eligibility before DenkiDying. `interactNavi.cpp::InteractDenki::actNavi` (85) checks active-world state and Dream Material. Enemy-side vulnerability and target-side electrical immunity are separate rules.

## Ravenous Whiskerpillar: Imomushi (65)

Registration (`src/plugProjectNishimuraU/ImomushiState.cpp:19`) lists Dead, FallDive, FallMove, Stay, Appear, Dive, Move, GoHome, Climb, Attack, Wait and three Zukan states. `Imomushi.cpp::getRandFruitsPlant` (723) chooses among living fruit-bearing plants within the home-centered territory radius. Its local candidate array has 32 entries without a visible append bound; generated content exceeding that candidate count needs a bounded implementation decision, not an assumed safe placement.

`startClimbPlant` (754) attaches to the target's tube collision part and computes inverse tube length. Null parts return, but zero-length geometry needs validation. `eatTsuyukusa` (803) operates on the attached living plant and sends `InteractEat(PelletType::Berry)` only after the eating-time threshold, then resets the timer. Visual fruit-color effects do not themselves consume berries. Verify plant removal/depletion, attachment cleanup, valid tubes, candidate limits and the plant's receiving interaction before claiming complete berry predation.

## Mitite: TamagoMushi (68)

Registration (`src/plugProjectMorimuraU/tamagoMushiState.cpp:18`) lists Walk, Turn, Appear, Hide, Dead, Wait. Group creation is manager-owned: `tamagoMushiMgr.cpp::createGroup` (122) sets the leader and attempts `count - 1` follower births. Successful followers are initialized and linked; null births are tolerated. Ground versus object-explosion origin changes offsets and velocities. `createGroupByBigFoot` (187) has its own position/velocity distribution. Ten is used by a caller (`tamagoMushi.cpp:579`), not a universal count hardcoded into the group helper.

`tamagoMushi.cpp::genItem` (326) runs outside Piklopedia, checks HoneyRate, requires the Honey manager and null-checks birth of yellow nectar. Collision code sends Astonish (226/250); the receiver `src/plugProjectKandoU/interactPiki.cpp::InteractAstonish::actPiki` (473) excludes Purple and requires an eligible non-invincible state. Test partial groups, leader death/reuse, group dispersal and reward allocation; leader teardown is not established merely by successful births.

## Skitter Leaf: Sokkuri (79)

Registration (`src/plugProjectNishimuraU/SokkuriState.cpp:18`) lists Dead, Press, Stay, Appear, Disappear, Wait, MoveGround, MoveWater, Flick. `Sokkuri.cpp::getSearchedTarget` (203) seeks Pikmin in Piklopedia and Navi otherwise. `isDisappear` (229) requires being inside home radius with no target; target selection is mode-dependent, not a different species.

`updateMoveState` (269) targets home outside territory. In water it adds upward velocity and approaches underwater movement speed; on land it approaches normal speed. `resetMoveVelocity` (292) also branches on water. Validate camouflage transitions, wall responses and entry/exit from water with collision assets. The state names alone do not establish complete movement fidelity or save reconstruction.

## Creeping Chrysanthemum: Hana (84)

Hana inherits ChappyBase (`src/plugProjectNishimuraU/Hana.cpp::onInit`, 26), then sets underground state. `isWakeup` (88) accepts nearby Olimar OR Pikmin. `initMouthSlots` (72) creates three mouths (`kamu1`, `kamu2`, `kamu3`), each radius 30. `eatAttackPikmin` (145) uses `ConditionNotStickSlot` with the shared eating helper.

`flickStatePikmin` (109) flicks attached/nearby Pikmin and nearby Navi. Despite its name, `flickAttackBomb` (128) flicks attached Pikmin and creates the THanaMiss visual, camera vibration and rumble; it does not birth a Bomb. `resetUnderGround` (155) clears buried/bitter-immune/no-interrupt state and constraints. The inherited ChappyBase attack/death event trace and full discovery/drop behavior remain dependencies. Validate disguised wake-up, mouth occupancy and emergence clearance rather than substituting a generic Bulborb.

## Shared lifecycle and acceptance boundary

The nine identities need source parameter/model/collision assets as well as these state contracts. Fixed numeric hitbox dimensions not established above must come from the relevant source assets, not an imported mesh's bounds. Test hostile interactions against each Pikmin kind and both captains, including invincibility, existing attachments and missing managers.

`EnemyBase::onKill` (`src/plugProjectYamashitaU/enemyBase.cpp:1289`) and birth metadata contribute carcasses, rewards and discovery; lack of a species-local drop function is not evidence of no drop. Complete enemy-held treasure and regional accounting remain integration checks.

`Creature::save` (`src/plugProjectKandoU/creature.cpp:262`) optionally writes position and calls default `doSave` (`include/Game/Creature.h:254`); generator flags are handled at `gameGenerator.cpp:282`. These paths do not establish preservation of partners, bridge/plant references, group leaders or transient FSM state across cave/day saves. Agree reconstruction semantics with the lifecycle lane, then test isolated restart/transition cases and natural combat/cargo recovery. No executable tests, native builds or gameplay runs were performed for this documentation batch.
