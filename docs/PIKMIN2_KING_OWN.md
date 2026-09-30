# Emperor Bulblax (KingChappy 53): own behaviour and arena placement

Wave-3 lane 53 (issue #289, parent #172). Implementation owner: Claude through the
shared `4laric` account. Native branch `claude/p2-wave3-53-emperor` (fork), root branch
of the same name.

## What runs

`KingChappy` is an own-identity actor of the Chappy family (`native pc_port/pc_p2_chappy.cpp`,
`FAMILY_KING`). The P1 Spotty Bulborb (`TEKI_Swallow`) is only the vehicle (body
pellet, carcass, Onion receipt as `onion:p2:53:<generator>`); the P2 FSM decides every tick.
The old `pc_p2_king_teki` sidecar (a P1-host proxy that only drew the King and counted
flick thresholds) is the retired fixture path and is not used by campaign or smoke seeds.

Source read: `pikmin2-research` `kingChappy.cpp`, `kingChappyState.cpp`,
`kingChappyMgr.cpp`, `enemyAction.cpp`, `bomb.cpp`, and the retail `attack.bca`,
`enemycoll.txt`, `enemyanimmgr.txt`.

| Source behaviour | Port | Evidence marker |
|---|---|---|
| `onInit` starts in HideWait | buried spawn: no atari, invulnerable, gauge hidden | `P2_CHAPPY_KING_UNDERGROUND` |
| HideWait wakes on a captain or Pikmin inside fp02 (disc 60), 3D, strict | `kingWakeInputs` | `P2_CHAPPY_KING_WAKE` |
| Appear KEYEVENT_3 flicks everything inside fp09 100 at fp10 200 | `doKingAppearShake` | `P2_CHAPPY_KING_APPEAR_SHAKE` |
| Walk -> Hide after the ip01 incubation (dive.bca), HideWait wake again | existing `walkTick` + dive clip | `P2_CHAPPY_STATE state=hide` |
| Attack: `eatBomb()` then `eatPikmin()` every frame from KEYEVENT_3 | `doEatBombs` + `doEat` | `P2_CHAPPY_BOMB_EAT`, `P2_CHAPPY_EAT` |
| Attack: tongue tip (bero6) traced each frame, floor/wall contact ends the lick | `kingTongueHits` (retail tip table) | `P2_CHAPPY_KING_TONGUE_HIT` |
| Attack exit: bombs -> Eat -> Damage, Pikmin -> Swallow, else Walk | `p2kinglife::attackExit` | `P2_CHAPPY_ATTACK ... bombs= tongue_abort=` |
| Damage: KEYEVENT_4 (frame 15) kills the mouth, bombs x fp05 200; KEYEVENT_6 (frame 60) starts the ip03 180 stun, loop 65..94 | `damageStep` clock | `P2_CHAPPY_KING_BOMB_DAMAGE`, `P2_CHAPPY_KING_STUN` |
| `bombCallBack`: external blast 0.25x + flick timer | `pc_p2_chappy_king_bomb` (`InteractBomb::actTeki`) | `P2_CHAPPY_KING_BLAST` |
| WarCry KEYEVENT_3 `Mgr::requestState` (Appear / WarCry on other Emperors) | `kingRequestState`, token order | `P2_CHAPPY_KING_REQUEST` |
| walk pursuit, checkFlick, shake, trample, damageCallBack filter | #884 work, unchanged | `P2_CHAPPY_KING_*` |
| Boss-scale collision: retail `enemycoll.txt` tree, only head/hana/kuti stickable | `kingBuildColl` / `kingUpdateColl` | `P2_CHAPPY_KING_COLL_BIND` |
| Emperor sounds | P1 Emperor boss bank via `pc_p2_sfx_policy.h` | `P2_SFX source_id=53` |

Clip map now follows `KingChappy.h` AnimID (Hide = `dive`, HideWait = `wait2`, Appear =
`type3`, Eat = `type2`, Swallow = `type1`, Caution = `waitact2`, Damage = `damage`); looping
clips wrap between their loop bounds instead of freezing on the last pose.

Fixed on the way: the Chappy family `Health` registry was bound with the `PelletView` base
pointer and looked up with the `BTeki*`, so the host's own life clamped the Emperor to 1100
(Bulbmin to 130) instead of 1300 / 300.

Key numbering note: `enemyanimmgr.txt` lists `frame type`; damage `15:4` is KEYEVENT_4 (the meal
and its damage), not the frame-46 event the earlier `pc_p2_king_policy.h` constant named.

## Dev and test switches (never set in normal play)

| Variable | Effect |
|---|---|
| `PIKMIN_P2_KING_WAKE_RANGE` | overrides the Appear wake radius (fp02 60). Smoke seeds set it so buried Emperors erupt near the start. |
| `PIKMIN_P2_KING_TEST_BOMBS=n` | labelled injection (`P2_CHAPPY_KING_TEST_BOMB ... label=test_only`): n dormant P1 bomb rocks are born 105 units ahead each time an Emperor leaves Caution. Used only for the bomb gate. |
| `PIKMIN_P2_KING_OWN_COLL=0` | keeps the P1 host collision tree (diagnostic). |

## Placement

The Emperor is an arena boss in real seeds (owner ruling 2026-09-29 #3, `BOSS_ENCOUNTERS`
`KingChappy`, descriptor `kingchappy_arena`). Its footprint is the tongue geometry, not a cast
list: the nine mouth slots reach 166.7 units from the root (`p2chappymouth::maxReach`), so the
encounter needs a flat, dry, wall-free disc of 175 (the next 25-unit clearance-probe step).
Every measured, unprotected arena covers it (Goolix 275, both Snagret pit/part 200, Beady
Long Legs 250, Puffstool 350, Cannon Beetle 250). The P1 Emperor arena `last_emperor` stays
protected (finale, owner ruling #901). Smoke seeds and the dev console place the Emperor on
any ordinary slot; there is no compiled slot list in native.

## Known gaps (recorded, not hidden)

- The Big variant (`f_03` / force-big: scale 1.5, life 1800) is not selectable in a seed.
- The WarCry `InteractAstonish` roar has no P1 receiver; the shake-off half is ported.
- A bomb rock in the mouth is removed on capture (no bomb-in-mouth visual); the slot stays taken
  and the damage is counted at KEYEVENT_4.
- The tongue-tip trace is a static-map trace with the retail tip table; P1 terrain is bumpier than
  the P2 cave floors, so a lick can end earlier than on P2 ground.
- Water ripples, dive/appear effects and camera vibration are not ported.
- Sound is a P1 approximation (P1 Emperor bank), not the P2 sound ids.
