# Frog/MaroFrog source and asset contract

Child #194, parent #167, integration #186. Codex owns this extraction-only slice through shared account4laric. Owned files: experimental/pikmin2_frog_assets.py, tests/test_pikmin2_frog_assets.py and this document. No shared converter, native, build, export, player-session or QA-bundle changes.

## Concrete identities and resources

The supplied disc is US GPVE01 revision0. Local decomp revision632af93787b9c95b63f0c13be32b161375ce3a96. include/Game/enemyInfo.h identifies Frog17 (Yellow Wollywog), MaroFrog18 (Wollywog). src/plugProjectYamashitaU/enemyInfo.cpp:28-29 marks both spawnable and UseOwnID. Each has its own enemy/data/SPECIES/{model,anim}.szs; none of the corresponding11BCA files are byte-identical between species. Neither is a helper or resource-only alias. MaroFrog::Obj inherits Frog::Obj and shared Frog FSM but overrides attackNaviPosition to retarget living captains; the base override is empty. Do not collapse that behavioral difference.

Each source model has16joints,1weighted envelope and18draw matrices. Full source joint names and collision trees are in frogs.json. Both have root collision radius40 at joint0 offset(20,-15,0); head attachment is joint1. Frog head radius23 offset(-1,-16,0), MaroFrog21 offset(-1.5,-7,0). These are source collision data, not an installed native collision contract. Source enemyparm, enemycoll, enemyanimmgr and enemystoneinfo bytes/hashes are retained locally.

## Retail parameters and rewards

General and proper blocks remain separate; duplicate fp01 etc must not be flattened. Definitions: include/Game/EnemyParmsBase.h and Entities/Frog.h. The proper block is exactly fp01 air time, fp02 jump speed, fp03 failure probability, fp04 fall speed. Sight radius is general fp12, not search-distance fp14.

| Retail field | Frog | MaroFrog |
| --- | ---: | ---: |
| Health |800|1100|
| Sight radius |360|360|
| Maximum attack range |200|250|
| Attack damage |10|20|
| Air time |1|1|
| Jump speed |320|350|
| Jump-failure probability |0.2|0.1|
| Fall speed |300|330|
| Corpse Pokos |5|7|
| Carry minimum/maximum |7/14|7/14|
| Onion return minimum/maximum |8/8|8/8|

Rewards come from user/Abe/Pellet/us/carcass_config.txt, whose full source SHA is in the manifest. Corpse pickup radius22, radius30,height14; offsets differ: Frog(-27.3,0,12.3), MaroFrog(-0.6,0,-34). No reward receiver is installed. Source corpse shadow radius differs by region in Frog.cpp; this import documents the supplied US data, not untested JP/PAL parity.

## Motions, events and behavior boundaries

Both registries contain11ordered clips: dead135frames, wait1 30, waitact2 60, move1 35, waitact1 40, type1 25, wait2 30, type2 18, attack27, damage35, type5 40. BCA loop attribute2 means J3D repeat; registry event0/1 boundaries are recorded separately. FSM completion and native animation control can override repetition; metadata alone must never trigger gameplay.

FrogState.cpp registers Dead,Wait,Turn,Jump,JumpWait,Fall,Attack,Fail,TurnToHome,GoHome. Motion mapping is explicit in Entities/Frog.h: Wait2 means waitact2, Turn means waitact1, Jump means type1, JumpWait means wait2, Fall means type2, Fail means damage, Carry means type5. Important registry events: dead67/2; move1 0/0,4/2,28/3,34/1; waitact1 10/0,29/1; type1 8/2; wait2 18/0,19/1; type5 10/0,29/1. All event frames and clip endpoints survive sampling.

Jump event2 calls startJumpAttack, sets Untargetable and velocity based on target displacement/air time plus jump speed (Frog.cpp:354). Falling collision presses grounded Navi/Pikmin unless Bittered (Frog.cpp:174); it is not simply visual impact timing. Landing flicks attached Pikmin and uses water-aware effects. Jump failure/turn-home/alert logic, Maro captain retargeting, water/stone/Purple receivers, effects, corpse attachment transforms and cleanup remain unimplemented in P1.

## Conversion and reproducibility

Command: `py -3.12 -m experimental.pikmin2_frog_assets --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --source native/pikmin2-research --output output/p2-frog-import/import04` (repeat with import05).

Uses existing read-only archive/BCA readers and weighted draw_matrices plus decode/write_model. Every clip preserves all event/loop boundaries and endpoints, filling remaining largest intervals deterministically to at most12poses. Bounds:512KiB perclip,10MiB total. The original8MiB probe reached the final Maro carry clip; the explicitly revised10MiB cap permits the full bank. Budget excess aborts without a completed manifest. Unsupported conversion errors remain explicit perclip; unknown skinning/materials are not silently dropped. Per-species immutable texture/material resource chunks must match across poses. Approximate TEV/material conversion remains a visual limitation.

Final import04/import05 each converted all22clips into264MOD poses,8,583,168 bytes. All561files match byte-for-byte. Runs took2.20s and2.29s on this host, not a runtime loading budget. Manifest SHA256 b228f17f48e800fccb72fab1ccc5986f29e647e7a6126035386f010133ebfcb4. Evidence output/p2-frog-import/reproducibility-final.json. Raw disc resources, generated models and executables remain private.

Seven focused tests pass: deterministic event coverage, malformed/out-of-range/noninteger event/cap rejection, separate retail parameter blocks/nonfinite rejection, byte caps, invalid corpse data, overwrite refusal, wrong-region refusal before output. Native_ready remainsfalse.

## Next bounded integration

P1 counterpart candidates are TEKI_Frog0 and TEKI_Frow33 (native/include/teki.h); Iwagen is unrelated. An opt-in visual proxy can reuse those actors only with explicit P1 jump/press AI and source identity/reward binding. Proposed new family installer/stage then serial integration-owner hooks for registration/render/reset/forget; no hooks are requested in this patch. Ground/collision/model-origin compatibility must be measured in an original P1 arena before gameplay claims.

| Gate | Status |
| --- | --- |
| Concrete source/resource/FSM contract |PASS|
| Real converted assets and reproducibility |PASS|
| Native recognizable display and exact spawn |UNTESTED|
| Natural jump/crush receivers and death |UNTESTED|
| Corpse hauling/rewards/duplicate suppression |UNTESTED|
| Full cleanup/reentry/mixed-scene performance |UNTESTED|
| Full P2 behavior parity |UNIMPLEMENTED|

The8.6MB disk bank is not a mixed-roster memory/performance certification. Shared immutable material loading, animation pause/phase, corpse pose, both species' independent resources and ordinary P1 controls need dedicated native acceptance.
