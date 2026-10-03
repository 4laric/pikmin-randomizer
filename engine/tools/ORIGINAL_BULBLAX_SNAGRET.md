# Original Fiery Bulblax and Burrowing Snagret (#1253)

Implementation owner: Codex through shared GitHub account 4laric.

Source ID 33 is FireChappy (Fiery Bulblax), real TEKI_Swallow 4 body with the
imported ChappyBase/FireChappy FSM. Source ID 34 is SnakeCrow (Burrowing Snagret),
real TEKI_Chappy 3 body with the imported SnakeJoint burrow/peck/swallow FSM.
These IDs belong to the original catalog; no AP source roster is required.
Retail genEnemy.cpp chooses EnemyGeneratorBase for both: literal ???? version,
empty tail and null initArg. Common placement, UID, count/deathCount, facing,
drop settings and lifecycle remain in the original catalog and GroupCourse.
Unsupported tails/birthType/treasure codes refuse whole admission. Source33
supports literal held code841 only; native preflight passes its unchanged row
to pc_p2_original_drop_resources and requires genuine authenticated held cargo.

Provider: p2original::bulblax_snagret::Native::provider(), a GroupProvider.
Central native forget must call pc_p2_original_bulblax_snagret_forget(actor)
before registry retirement/address reuse (Snagret additionally does so in its
family forget). Resource dependencies: Chappy original API including source 33;
batch3 original resources/birth APIs for 34. The course consumer must prepare
the complete Chappy source union (e.g. 2/33/43) once BEFORE per-provider preflight.
Real enemy corpses use PelletView config plus their physical dead bank;
ordinary number drops separately preload their Pellet shapes.

Compile tools/test_p2_original_bulblax_snagret.cpp with provider,
pc_p2_original_spawn_plan.cpp, pc_p2_original_drop.cpp and
pc_p2_original_catalog.cpp. Pass an actual private p2-snagret-bank.txt to test
strict 13-clip timing checks. This controlled-engine guard establishes admission,
reservation, attempted ordinal permanence, null/partial births and failed-bind
cleanup; it does not establish real combat, transport or persistence.

## Direct human gameplay (pending)

Stage a fresh private imported tutorial day 5 with the original literal rows,
20 live Pikmin and a centered 960x540 window. Preserve legal assets/saves/logs
under ignored output. Use the actual course consumer and source positions;
never substitute an AP slot or generated proxy encounter.

1. Confirm 20 Pikmin and the window baseline. Approach the Fiery Bulblax with
   reds using ordinary controls. Observe wake/chase, fire aura, bite/swallow,
   damage and flick. Verify vulnerable colors catch fire and reds resist it.
2. Defeat it through ordinary attacks, wait through the actual death clip,
   and verify one natural corpse plus literal probability/count number drops.
   Verify the literal watch841 releases once as a physical treasure without
   granting Pokos. Its retail carry minimum30 exceeds this20-Pikmin baseline:
   ordinary delivery testing requires recruiting sufficient Pikmin through
   gameplay. Carry it to the typed ship; require completed suction before the
   unique110-Poko receipt. Checkpoint must refuse pending uncollected cargo
   until the physical graph has authenticated save/restore support.
   Carry its real corpse to an Onion and observe population and removal.
3. Approach the Burrowing Snagret. Observe the buried state, authored fast/slow
   emergence, directional peck, held Pikmin capture and swallow, dive/flick,
   and return to the buried state. Attack while buried and emerged to observe
   the actual invulnerability gate. Defeat and carry its corpse normally.
4. Leave/reenter through the real course path: verify cleanup and no stale
   actors/mouth occupants/private pose registrations; observe original respawn
   timing. Save through the actual campaign save UI, exit, relaunch, and verify
   generator deaths/drop state and subsequent respawn timing persist.

Record native commit/executable SHA256/no-work build result and fresh logs.
Stop captain-down/lockout observations; kill only processes owned by this test.
Build and synthetic tests cannot satisfy this human mechanic acceptance.


The real-engine fixture pikmin_ci_fixture_original_snagret uses ONLY the literal
nonloop/5-29.txt#2 SnakeCrow row (UID1389661387), checks real family birth/health,
20-Pikmin and960x540 startup, then observes180 engine updates and cleans/reenters
with a fresh activation. It is partial source admission, never whole-course or
natural attack/save acceptance. Use canonical bounded run_pikmin2_fixture.py
with --experimental-pikmin2-surface tutorial arguments, a fresh staged private
run directory and PASS P2_ORIGINAL_SNAGRET_RUNTIME marker. --manual-encounter
leaves that unmodified literal Snagret running for ordinary human controls.
Actual source33 initgen.txt#17 carries treasure841 and is structurally supported.
Physical admission still refuses without held provider9a2aaba90e218bfea4cd2c45f1c73bfd51cdfcdf,
its typed startup/collector dependencies, and an authenticated TREASURE_SOURCE
activation matching the literal catalog/ship/model descriptor. Consumer must
call held_unload before course/App-heap teardown and block SAVE while
held_pending is nonzero. No completed delivery or persistence is claimed.
Never remove that treasure to manufacture an accepted row.

Held dependency composition from the607c base (coordinate typed startup APIs
with their owner; do not import the entire startup branch automatically):
4001c9a65a80d18d64713579392f14fc3912f29b receipt codec,
d2dec15dc4bb33f56802a72583afdbb664d78881 physical descriptor,
a1a55f19a5444fdf6b40aedf2bea4de5495f68f2 input verifier,
78da5f594cb7506eceb815081422b9eefa5004e1 receipt query,
d8e5924a174242edfb9b31f0d53069b30f0cf567 equipment reconcile,
then9a2aaba90e218bfea4cd2c45f1c73bfd51cdfcdf held provider.
Equivalent composed collector pins are ac34e5c379be42b64202d8e0348206233d795a83,
89f18c391e4c3cc26dc3149fdb4f2b95d3a844d7,
003d618a16f589e663fe4c4eef791ff955acfc2b and
f59c35d1908d52d1b1ef2ac058e0df2ff70f055b. Preserve all existing CMake
targets and new -UNDEBUG test flags when resolving additive tail conflicts.
Typed startup must provide original manifest and Onyon identity APIs;
SAVE must provide TREASURE_SOURCE dual verification and its selected source
getter, authenticated receipt restore, and pending cargo refusal before mutation.
Source33 needs no additional geometry hook: held provider uses the actor's
actual bounding centre and treasure velocity(0,200,0).

The fixture vendors scripts/p2_fixture_captain_guard.h exactly as the owned
p2_original_snagret_captain_guard.h. It checks dead state, dead flag,
nonfinite/low HP and disappearance of an initialized captain immediately
AFTER engine idle and BEFORE movie/pause/readiness/observation/PASS gates.
--guard-negative-test exercises that guard before engine boot: require raw
exit86, P2_FIXTURE_CAPTAIN_DOWN and no PASS. The standalone guard test checks
the same truth table. Diagnostic mode parks the captain on actual course
terrain at least700XZ units from the literal encounter; it does not modify
health. --manual-encounter bypasses diagnostic parking for ordinary controls.


Original SnakeCrow death throws its literal source drops at dead KEYEVENT3,
authored frame131, exactly once; END165 separately finalizes the natural corpse
and retires the generator. AP/P1 death paths are unaffected. The provider test
checks no early drop, exact131, crossed timestep delivery, no repeated emission
throughEND and AP exclusion. A natural combat death run must observe the new
P2_ORIGINAL_SNAKECROW_DROP marker and actual number pellets before accepting
runtime death/drop timing; the controlled policy test alone is not that evidence.
