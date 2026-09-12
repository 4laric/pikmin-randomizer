# Pikmin 2 aquatic enemy source audit (#167)

Implementation owner: Codex using shared account 4laric. This is a source audit
only. It records what the checked-in decompilation establishes, not replacement
compatibility, successful native spawning in every generator, route safety,
carcass delivery, drops, or a completed gameplay sign-off.

**Scope and evidence.** Reviewed `projectPiki/pikmin2` at
`632af93787b9c95b63f0c13be32b161375ce3a96` (randomizer integration base
`93ad07f505f78c097757a5c5355dbf518bdde786`). The IDs and display identities are
declared in `include/Game/enemyInfo.h:76-86,122-123,130,159-160`. Live C++ was
read through the named functions below; large commented-out assembly blocks were
not treated as a second implementation. “Drop” in the Frog method names is an
effect/state term here, not evidence of loot.

Source paths below are relative to the decompilation checkout. Bare Frog, MaroFrog, Catfish, and Tadpole filenames are under `src/plugProjectNishimuraU/`; Jigumo and UmiMushi files are under `src/plugProjectMorimuraU/`; `enemyInfo.cpp`, `genEnemy.cpp`, and `generalEnemyMgr.cpp` are under `src/plugProjectYamashitaU/`.

## Registration, concrete classes, and aliases

`GeneralEnemyMgr` creates distinct managers for Frog, MaroFrog, Catfish,
Tadpole, and Jigumo at `src/plugProjectYamashitaU/generalEnemyMgr.cpp:241,256,
292,295,424`. It registers only `EnemyID_UmiMushiBase` at line 450. The generator
name dispatch nevertheless accepts the eight concrete generator IDs, including
JigumoNest and both Bloysters, at `genEnemy.cpp:495-573`; its base-ID case is
separate at line 591. That proves parser coverage, not a safe direct base spawn.

The data table says Frog 17 and MaroFrog 18 are independently spawnable and
day-end eligible (`enemyInfo.cpp:28-29`), while Catfish 26 and Tadpole 27 are
spawnable (`:49-50`). Jigumo 63 is spawnable and advertises PanHouse as one child
(`:100`). `enemyInfo.cpp:168` maps JigumoNest 64 to PanHouse only when resolving
the resource name; it has no independent table row. It must therefore not be
treated as an ordinary independent enemy. UmiMushiBase 100 has `EFlag_UseOwnID`
but lacks `EFlag_CanBeSpawned`; the header comment labels it “Bloyster base
(crashes),” which is a decomp annotation rather than reproduced runtime proof.
UmiMushi 71 and UmiMushiBlind 101 inherit its asset entry and are
marked spawnable (`enemyInfo.cpp:102-104`). Direct ID 100 generation is therefore
excluded from direct generation by this audit.

MaroFrog is a concrete subclass of `Frog::Obj` (`include/Game/Entities/MaroFrog.h:12`),
with its own manager allocating `Frog::Parms` and `MaroFrog::Obj`
(`MaroFrogMgr.cpp:20,29`). It shares Frog code but retains its own type ID, so it
is not an interchangeable table alias. Catfish is `KochappyBase::Obj` rather
than a new aquatic FSM: `Catfish::Obj::onInit` delegates to that base at
`Catfish.cpp:23`; it adds the `kosi` shadow joint, two mouth slots (`kamu1`,
`kamu2`) of radius 20 (`:83`), and press damage forwarding (`:63`). The base
Kochappy behavior remains an unresolved source trace for this batch.

## Frog, Wollywog, and Wogpole contracts

Frog initialises the shared FSM, alert/air flags, effects, and starts in Wait
(`Frog.cpp:36`); the FSM registers ten states at `FrogState.cpp:13`. Targeting in
`StateWait::exec` (`:85`) asks `getNearestPikminOrNavi`, checks view/sight and
attack range/angle, then selects Jump. `StateJump::exec` (`:245`) performs its
flick at animation key event 2, begins the jump attack, and selects water or dry
jump sound based on `mWaterBox`. `StateFall::exec` (`:339`) waits for a floor
triangle, and `StateAttack::init` (`:362`) calls `pressOnGround`; the latter
flicks stuck Pikmin and chooses water splash/sound or land-drop effect
(`Frog.cpp:385`). Falling collision presses a grounded Navi/Pikmin only while the Frog is not bittered and `mIsFalling` is set
(`Frog.cpp:177`). Thus the trace establishes event-driven stomp/flick mechanics
and water-sensitive presentation, not that all water geometry is navigable.

Death calls `deathProcedure` then kills at the dead animation end
(`FrogState.cpp:32,45`); `Obj::onKill` only finishes its jump effect before the
base kill (`Frog.cpp:52`). No concrete loot drop has been verified in these
functions. `doStartWaitingBirthTypeDrop` / `doFinishWaitingBirthTypeDrop` merely
hide/show effects (`Frog.cpp:246,256`), so they do not establish a drop table.

Tadpole has its own six-state FSM (`TadpoleState.cpp:14`), begins Wait
(`Tadpole.cpp:32`), and targets only the nearest *Navi* in Wait/Move
(`TadpoleState.cpp:79,135`), then computes a position away from it bounded by
territory (`Tadpole.cpp:110`). Its Wait, Move, and Escape states immediately
enter Leap when `mWaterBox` is absent (`TadpoleState.cpp:79,135,242`).
`StateLeap::exec` (`:307`) ends/leaves its leaping cycle when it encounters a
water box, otherwise steers toward a random target, and emits water dive versus
dry effect at animation keys through `createLeapEffect` (`Tadpole.cpp:173`).
Hipdrop kills a live, non-bittered Tadpole by adding its entire health
(`Tadpole.cpp:89`). This is a strong placement boundary: dry placement has
specific leap fallback, but it is not proof of recoverable routing.

## Hermit Crawmad and nest ownership

`Jigumo::Obj::birth` creates a PanHouse through its manager, stores it in
`mHouse`, assigns house type from the Crawmad type, and scales it
(`jigumo.cpp:73`). It tests `nestMgr`, but after birth asserts the resulting
`nest` (`P2ASSERTLINE(86)`), so manager capacity/exhaustion is a real native
acceptance risk, not a graceful no-nest fallback. `onKill` calls the base then
`killNest`; `killNest` sets the house death timer to one and nulls the owner
reference (`:548,1737`). This is an actual owner link,
not evidence that ID 64 can be independently shuffled. The nest manager/type,
day-end reset behavior, and persistence serialization were not fully traced and
remain unresolved.

The fourteen-state FSM is registered at `jigumoState.cpp:16`. Appear/hide make
the actor constrained/inactive around its house; attack activates collision at
key 2, attacks Navis, calls `eatPikmin`, and if it catches one enters Carry
(`StateAttack::exec:314`). Carry returns to the home goal and enters Eat near
it (`StateCarry::exec:517`); Eat calls `swallowPikmin(enemy, 300.0f, nullptr)`
at key 8 then hides (`StateEat::exec:648`). Short attack has the analogous
swallow at key 10 (`StateSAttack::exec:792`). Its damage callback only permits
normal damage in Carry/Return and rejects hits closer to head than body
(`jigumo.cpp:325`); it also distinguishes water/soil attack effects by
`mWaterBox`. `outWaterCallback` delegates to base and applies gravity
(`:383`), which is a concrete dry/out-of-water behavior but not a navigation
guarantee.

## Bloyster shared base and receiver boundaries

One `UmiMushi::Mgr` allocates objects tagged first as UmiMushi then Blind based
on per-ID counts (`umiMushiMgr.cpp:86`). `Obj::onInit` (`umiMushi.cpp:94`) starts
the shared FSM in Walk. For Blind it calls `setParameters` (scale 0.5, tail
weak-point scale), overwrites health with `mBlindHealth`, and installs eye/weak
joint callbacks; ordinary UmiMushi takes the mid-boss sound path. Both initialise
seven mouth slots, radius 30 ordinary or 25 Blind (`umiMushi.cpp:552`).

The shared walk state explicitly bifurcates: Ranging Bloyster continuously uses
`walkFunc`; Toady Bloyster alternates configured move and wait timers
(`umiMushiState.cpp:130`). Captain targeting is concrete rather than assumed:
the state transitions consult `isChangeNavi`, target selection is represented by
`mTargetNavi`, and the ordinary/Blind distinction alters movement. The concrete
`Obj::isChangeNavi` helper starts at `umiMushi.cpp:843`: Blind returns false;
ordinary two-player operation chooses the nearest Navi, otherwise the active one;
an existing target expands the range by 1.2 and a live, in-range change updates
both target and goal. Its null-Navi path retains the old target. That still does
not demonstrate all caller/receiver lifetime conditions, so captain behaviour
outside these branches remains unresolved.

Weakpoint/receiver behavior is also bounded. `damageCallBack` (`umiMushi.cpp:467`)
accepts bitter damage; otherwise it asserts a source, casts it to Piki without an
explicit `isPiki` rejection, and accepts a live `isStickTo` source with a
collision part, or a live source below body height without one (then applies
`mDamageRate`). Press/hipdrop/earthquake scale Purple Pikmin damage
(`:493, :512, :531`). This does not prove a tail collision-ID rule or every
collision-part weakpoint receiver: that caller chain remains outside the reviewed
functions.
`StateAttack::exec` (`umiMushiState.cpp:510`) marks tongue activity at key 3,
uses `eatPikmin`, optionally attacks Navis at key 5 only if `mCanEatNavis`, and
flicks nearby/stuck Pikmin and Navis at key 6. `StateEat::exec` (`:606`) swallows
at animation end. Death performs `deathProcedure` and kills at end
(`:634,649`). Neither establishes a randomized loot drop or persistent reset.

## Audit disposition

These IDs are source-identified candidates only. Before enabling a swap: exercise
generator parsing and birth for every concrete ID; reject ID 100; preserve the
Jigumo-to-PanHouse ownership relation; observe water/dry anchors, stomp/swallow
receivers, captain selection, death/carcass carry, drops, day-end restore and
persistence. The incomplete Catfish base trace, Bloyster target helper/receiver
trace, nest persistence, and all physical route tests are explicit open work.
