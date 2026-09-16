# Pikmin 2 flying enemy source audit (#166)

Source: [projectPiki/pikmin2](https://github.com/projectPiki/pikmin2), revision `632af93787b9c95b63f0c13be32b161375ce3a96`, inspected read-only through `native/pikmin2-research`. Paths and function-start line numbers below refer to that revision. This is an implementation specification, not runtime or playthrough evidence. Numeric identities come from `include/Game/enemyInfo.h`.

## Honeywisp: Qurione (16)

`src/plugProjectNishimuraU/QurioneState.cpp`, FSM registration at 14, lists Stay, Appear, Disappear, Move, Drop, Dead. The carried reward exists before release: `Qurione.cpp`, `Obj::attachItem` (284), births an Egg, null-checks it, initializes it and captures it at the `water` joint. `dropItem` (302) ends capture, clears the pointer and updates discovery. Drop execution (QurioneState.cpp:214) releases at event 2; it does not allocate the Egg. Egg reward selection is covered by the cannon audit. `isFlyKill` (Qurione.cpp:271) tests visibility and the configured death time. Verify pool exhaustion, visibility-driven removal, and interruption while carrying an Egg.

## Snitchbugs: Sarai (23), Demon (32)

Sarai FSM registration (`src/plugProjectNishimuraU/SaraiState.cpp:18`) lists Dead, Fall, Damage, TakeOff, Flick, Wait, Move, Attack, Fail, CatchFly, FallMeck. `StateAttack::exec` (424) has a frame-dependent descent: it calls `catchTarget` after frame 16 within its descent window through frame 30, subject to its floor/timer guard. Event 2 sets pursuit velocity, event 3 clears NoInterrupt, event 4 selects Fail if nothing was caught, and END selects CatchFly or Move. Imported poses alone cannot reproduce this capture window.

Demon inherits `Sarai::Obj` (`include/Game/Entities/Demon.h:11`) and its FSM, but overrides target and catch methods. `Demon.cpp`, `getAttackableTarget` (20), searches living captains not already mouth-stuck after a three-second attack timer, within territory/view/range. `catchTarget` (57) tests free mouth-slot radii and sends `InteractSarai`; its counter increments without checking the stimulus return, so the count does not prove attachment.

`Sarai.cpp`, `fallMeckGround` (228), sends `InteractFallMeck` to mouth-stuck creatures and assigns downward velocity only after an accepted stimulus. `flickStickTarget` (321) sends Flick to occupied mouth slots. `getNextStateOnHeight` (276) treats an attached Purple as a fall trigger; other attached counts feed a probability calculation. Captured targets are excluded from Sarai's attached-attacker count, while Demon overrides that count (`Demon.h:19`).

Receiver boundary: `src/plugProjectKandoU/interactNavi.cpp`, `InteractSarai::actNavi` (29), attaches only when not already stuck, under the active-world/no-gameSystem branch, and enters NSID_Sarai. Test actual attachment and release, not just enemy counters, for both captains, existing attachments, death and ground interruption.

## Flying Blowhogs: Mar (29), Hanachirashi (55)

FSM registration at `src/plugProjectNishimuraU/MarState.cpp:18` and `HanachirashiState.cpp:18` lists Dead, Wait, Move, Chase, ChaseInside, Attack, Fall, Land, Ground, TakeOff, FlyFlick, GroundFlick; Hanachirashi adds Laugh.

Mar `StateAttack::exec` (MarState.cpp:869) adjusts height, applies wind each update while active, enables wind/effects at event 2, and returns to Wait at END. Cleanup clears the flag and wind scale and fades the effect. Hanachirashi's counterpart (HanachirashiState.cpp:877) follows the same activation boundary, but a successful `windTarget` selects Laugh for the END transition. Target volumes and emitted stimuli are implemented by `Mar.cpp::windTarget` (1006) and `Hanachirashi.cpp::windTarget` (752); imported effects must not replace those collision queries.

Receiver boundary: `src/plugProjectKandoU/interactPiki.cpp`, `InteractWind::actPiki` (253), rejects invincible, Purple, KokeDamage and dead states. `InteractHanaChirashi::actPiki` (278) still strips a Purple bud/flower to Leaf, then returns false; other eligible Pikmin enter Blow with the withering arguments. Wind resistance is not flower immunity. `interactNavi.cpp::InteractWind::actNavi` (60) checks Repugnant Appendage and repeated same-source Flick/KokeDamage. Validate color, growth stage, captain equipment and repeated contacts separately.

## Jellyfloats: Kurage (57), OniKurage (72)

FSM registrations at `src/plugProjectNishimuraU/KurageState.cpp:20` and `OniKurageState.cpp:21` list Dead, Wait, Move, Chase, Attack, Fall, Land, Ground, TakeOff, FlyFlick, GroundFlick; OniKurage adds Drop. Attack functions are KurageState.cpp:322 and OniKurageState.cpp:327. Kurage's suction loop (`Kurage.cpp:511`) sends `InteractSuikomi_Test` to living Pikmin not already attached to it. OniKurage has separate Pikmin and captain loops (`OniKurage.cpp:575` and 610); captains use free mouth slots and `InteractSarai`. Its two mouth slots are configured at `OniKurage.cpp:253`.

OniKurage Drop is a falling state, not a reward generator: `StateDrop::init` (OniKurageState.cpp:470) starts Fall motion; exec (486) requests finish when ground distance is below 25, vertical velocity is positive, or the timer exceeds three seconds. END chooses Dead or Land. Captain release has explicit Flick/Bomb branches in `OniKurage.cpp::flickStickNavi` (714); validate these separately from Pikmin stomach recovery.

Pikmin ingestion is completed in receiver/state code. `src/plugProjectKandoU/interactPiki.cpp::InteractSuikomi_Test::actPiki` (423) rejects invincibility and enters Suikomi. In `pikiState.cpp`, init (2071) stores owner/collision references; exec (2091) restores scale and enters Walk when the owner is no longer alive. `execMouth` (2113) approaches the mouth/stomach and starts `mKurageKillTime` upon stomach capture; the tube path is handled by `execString` (2163). `execStomach` (2196) decrements the timer only while the enemy is not bittered and health is positive. Timer expiry begins a 0.5-second shrink phase before death. Outside that shrink phase, loss of the target collision object causes downward Blow recovery. Cleanup (2240) ends stomach capture and restores movement. Owner health reaching zero and owner becoming not alive are distinct gates.

Death animation also matters: Kurage `StateDead::exec` (KurageState.cpp:61) flicks attached Pikmin at event 2, runs deathProcedure at event 3 and kills at END. Verify capture interruption, stomach-reference lifetime, bitter timer pauses, death animation, and both captain release paths.

## Careening Dirigibug: BombSarai (58)

`src/plugProjectNishimuraU/BombSaraiState.cpp:22` registers Dead, Damage, Wait, BombWait, Move, BombMove, Supply, Release, Fall, TakeOff1, TakeOff2, Flick, BombFlick. Supply init (460) calls `supplyBomb`; allocation is not an animation-event side effect. Release exec (522) throws at event 2 using horizontal speed 50 and vertical speed 100, clears NoInterrupt, and chooses the next height-dependent state or Wait at END.

`BombSarai.cpp::supplyBomb` (263) checks the Bomb manager and birth result, initializes the payload, captures it at `kamu_jnt1`, and sets `mCarrier`. `throwBomb` (285) ends capture, sets velocity/facing and clears `mHeldBomb`; onKill (57) calls it with zero velocity. The thrown Bomb retains its own lifecycle and carrier attribution; see the cannon audit. Test failed supply, death while carrying, repeated release, and carrier death/reuse while a thrown Bomb remains active.

## Antenna Beetle: Fuefuki (41)

`src/plugProjectNishimuraU/FuefukiState.cpp:17` registers Dead, Stay, Land, Jump, Wait, Turn, Walk, Whisle, Struggle. Whisle exec (487) calls `updateWhisle` each update; after three seconds it requests Turn or Wait based on the squad timer, with jump/death overrides, and transitions at END. Cleanup stops the whistle. `Fuefuki.cpp::updateWhisle` (362) scans living true Pikmin not mouth-stuck or already owned by this beetle and sends the whistle stimulus inside its radius.

`interactPiki.cpp::InteractFueFuki::actPiki` (34) rejects invincible/non-Pikmin/already-ACT_Teki targets and requires a callable state before starting ACT_Teki. `src/plugProjectKandoU/aiTeki.cpp::ActTeki::init` (27) stores the owner; exec (62) enters Panic and continues on owner death, or returns Success with `mToEmote` for a flying owner or bittered Fuefuki. Those returns are not proof of permanent detachment without the brain's follow-through. Validate competing captains/beetles, whistle interruption and owner death; do not rewrite save ownership from this audit.

## Unmarked Spectralids: ShijimiChou (77)

`src/plugProjectMorimuraU/shijimiChouState.cpp:19` registers Wait, Fly, Fall, Dead, Leave, Rest. `shijimiChou.cpp::checkFlyStart` (543) considers Piklopedia mode, spawn source and group leader; do not replace swarm behavior with independent flyers. `genItem` (507) runs outside Piklopedia and requires plant origin or a nectar-rate roll. Red/Purple require their corresponding first-spray demo flag, otherwise they return without a drop. Successful Honey birth is null-checked and gets `mSpecType`. This differs from Egg's fallback rules. Test each color/source combination and exhausted item pools; full leader teardown semantics remain to be traced.

## Shared persistence and remaining acceptance

`EnemyBase::onKill` (`src/plugProjectYamashitaU/enemyBase.cpp:1289`) and manager birth/drop metadata contribute corpses and rewards; absence of a family-local reward function does not mean no reward. Discovery counters, enemy-held treasure and all regional behavior require additional integration checks.

`Creature::save` (`src/plugProjectKandoU/creature.cpp:262`) optionally writes position and calls the empty default `doSave` (`include/Game/Creature.h:254`); generator position flags are handled at `gameGenerator.cpp:282`. This does not establish cave/day reconstruction. Captures, owner pointers, stomach timers, bombs and whistle-controlled Pikmin must be tested across the chosen lifecycle boundaries without assuming either persistence or universal reset.

For native acceptance, exercise every listed ID through normal targeting, attack, interruption, defeat and recovery with source assets, then repeat with invalid/missing owners, occupied slots and exhausted pools. Verify swept/area attack geometry at walls, ceilings, water and floor transitions, using measured source parameters. Run isolated save/reload and cave/day cases after the lifecycle contract is agreed. No executable tests, native builds or gameplay runs were performed for this documentation batch.
