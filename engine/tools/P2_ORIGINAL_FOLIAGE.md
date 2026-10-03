# Original brown Figwort91 / Foxtail88 (#1251)

Native factories use genuine source models, sampled single animations, static
retail collision and literal generator identity. TEKI_Palm7 is allocation and
cleanup storage only; its model, AI, physics, carcass and rewards never execute.
`foliage-bank.txt` and all converted/legal assets remain private.

Build: production plus `pikmin_ci_fixture_original_foliage` with
`-DPIKMIN_CI_FIXTURES=original_foliage`; pure controls target
`pc_p2_original_foliage_test`.

Generate: `tools/p2_original_foliage_resources.py --randomizer-root <root>
--iso <privateISO> --source <read-onlyP2research> --output <freshbank>`.
Stage: `tools/p2_original_foliage_stage.py --baseline <private20Redtutorialrun>
--bank <bank> --output <freshstage>`; it preserves the five legacy stage-table
entries and appended tutorial, changes only the zero-count chassis4->7 row and
adds the24 genuine models. Use fresh per-run settings/cards and bounded60-second
supervision. Never modify the source baseline or shared legal asset installation.

Fixture arguments: `--experimental-pikmin2-surface tutorial`.
Default checks disclosed initialization/collision controls, invulnerability,
normal animation update, static collision, resource-zero rows, cleanup and disc
cache reentry. `P2_ORIGINAL_FOLIAGE_WALK=1` instead moves through actual SDL input;
it performs no captain transform/velocity writes or synthetic collision calls.
The initialized fixture positions are explicitly relocated. These checks do not
establish whole-course startup, original-placement acceptance or RAM resume.

Forest species work is tracked separately in
[issue1267](https://github.com/4laric/pikmin-randomizer/issues/1267); issue1251
remains the initial91/88 scope. Optional `P2_ORIGINAL_FOLIAGE_FOREST=1` selects Clover47
from `forest/plantsgen.txt#23` (UID1376717705, facing0) and small Figwort49 from
`forest/plantsgen.txt#0` (UID1389527839, facing180). Their original count1,
reserved0, respawn0, common fields and empty `????` tail remain literal; only
placement moves to the same surveyed east tutorial camp positions. The scene
still starts with `--experimental-pikmin2-surface tutorial`. This is a species
fixture, and does not qualify the whole forest course or original forest ground.
The other original47/49 forest rows and the full ten physical placements remain
startup integration gates after the two representative actors qualify.
Use a genuine four-species bank for this batch. Default behavior remains91/88.

The Linux supervisor accepts `--batch tutorial|forest` (default `tutorial`) with
its existing `--mode diagnostic|walk|refusal|captain-down`. It clears inherited
batch/mode flags, records the selected source IDs in evidence, and requires
batch-specific diagnostic/walk PASS markers. Forest results say `sources=47,49`.
Set both `P2_ORIGINAL_FOLIAGE_FOREST=1` and `P2_ORIGINAL_FOLIAGE_HUMAN=1` for the
same human walking script below using Clover and small Figwort in place of the
brown Figwort and Foxtail. Preserve the20Red baseline and centered960x540 window.

Additional literal species fixtures are tracked in
[issue1272](https://github.com/4laric/pikmin-randomizer/issues/1272). They retain
the same20Red tutorial arena, centered960x540 window,60-second supervisor,
captain guard and phased native pool cleanup. Default tutorial91/88 and
forest47/49 batches are preserved. Select the new batches with the supervisor's
`--batch` argument, or set `P2_ORIGINAL_FOLIAGE_BATCH` for direct fixture launch:

| Batch | Source pair | Literal source keys and UIDs | Facing degrees |
| --- | --- | --- | --- |
| `dandelion` |46,80| `forest/plantsgen.txt#13` UID1375741226; `forest/plantsgen.txt#5` UID1390227387 |0;90|
| `shoots` |51,52| `yakushima/plantsgen.txt#0` UID1382955810; `yakushima/plantsgen.txt#5` UID1390174228 |240;270|
| `horsetails` |90,88| `forest/plantsgen.txt#14` UID1384248119; `tutorial/plantsgen.txt#4` UID1381420794 |270;95|

The new sources are Tanpopo46, Wakame_s51, Wakame_l52, Tukushi80 and Zenmai90.
The batch names are test groups. These representative rows keep literal count1,
reserved0, respawn0, common fields, zero offset and empty `????` generator tail.
Their positions are disclosed fixture relocations. Every batch still launches
the tutorial scene and reports its exact source pair in the PASS marker; this
does not qualify original forest/yakushima positions or whole-course admission.

Source51/52/80/88/90 LOD uses retail cylinder plane support, including strict
tangency exclusion and source88's backward50 offset. Pure controls cover those
boundaries and all nine distinct resource identities, count-zero resource rows,
ownership, retained cleanup failures and touch timing. These controls and the
visible fixture do not prove fully culled animation scheduling: retail
`isCullingOff()` depends on nearby Pikmin, and an equivalent native predicate
remains unproved. Plain frustum visibility must not be substituted for it.

Brown large Figwort92 is tracked separately in
[issue1279](https://github.com/4laric/pikmin-randomizer/issues/1279). Select
`--batch brown-large` in the Linux supervisor, or
`P2_ORIGINAL_FOLIAGE_BATCH=brown-large` for direct fixture launch. The batch
pairs92/91 at the same surveyed east tutorial points. Existing tutorial91/88
and forest47/49 selections are preserved; no generic foliage batch dependency
is required.

The92 representative is literal `last/plantsgen.txt#0`, UID1390080862, index0,
facing0, count1, reserved0, respawn0 and zero offset. Its source object version
`0004` retains the constructor's birthType0 default, as decoded explicitly by
startup; generator version is still `????` with an empty tail. All remaining
common/drop fields stay literal. Its genuine model is `KareOoinu_l`, with stem
`flora_KareOoinu_l_karaooinu_l`; the source animation's `karao` spelling is kept.

The fixture checks92's static root50/child35 collision radii and both centres
through touch animation, normal60-frame motion ending at59, equivalent native
leaf-touch sound, invulnerability, no rewards, owned cleanup and disc cache
reentry. PASS markers identify `sources=92,91`. It still launches tutorial with
20Red Pikmin and a centered960x540 window under bounded60-second supervision.
These representative controls do not qualify original Last positions, full
Last-course admission, cave placement or RAM saved-creature loading.

Cave integration uses `foliage::Native::provider()` through the existing
`GroupProvider` preflight/reserve/birth/bind/release interface. A caller outside
the global `GroupCourse` must keep each actual Generator alive until its actors
release, then explicitly retire its original registry associations. Global
native retirement scans the global course; it does not retire a separate cave
owner's bindings. Keep source92 identity and resource admission independent of
the allocation chassis and test the actual cave path before gameplay sign-off.

Human test (set `P2_ORIGINAL_FOLIAGE_HUMAN=1`; fixture remains open10minutes):

1. Confirm centered960x540 gameplay and20Red Pikmin. Walk toward each of the two
   plants beside camp. Brown small Figwort and Foxtail must show their own model
   at the ground, with no Posy number pellet or enemy health gauge.
2. Walk through each plant from two directions, then stop. Each plant plays its
   source touch motion and returns to rest. Stand still against it; it must not
   repeatedly restart or push/move its root. Walk offscreen and return; an active
   touch motion must have completed normally.
3. Punch and throw Reds nearby. No plant HP loss, carcass, nectar, seed or treasure
   appears. The plant does not attack, eat, chase or displace any Pikmin.
4. Record appearance, touch audio/motion, ground placement and actor behavior.
   Close the owned fixture; do not alter player saves.

After whole-course integration, repeat on all11source91 +3source88 original day5
rows. Leave/reenter the course and save/relaunch through normal UI; verify the
same scheduled rows and no duplicate resources/rewards. RAM saved-creature
loading is a separate integration gate and is not established by the disc-cache
fixture. Keep that gate open until the ordinary route works.

Known presentation differences:12sampled poses with vertex interpolation,
accepted diffuse TEV approximation, equivalent native touch-leaf cue, and a
conservative sphere enclosing Foxtail's retail LOD cylinder. Source radius,
orientation, root, post-shadow drawing and static collision remain literal.

Typed cave leaf control (issue1279 extended scope):
`P2_ORIGINAL_FOLIAGE_BATCH=cave`, or supervisor `--batch cave --mode diagnostic`,
selects the genuine tutorial_1 floor2 TekiInfo rows91/92/47 and their exact
minimum counts6/4/2. Other floor families are skipped. The descriptor source SHA,
floor, vector row, source key and UID authenticate each association. `CAVE` is
an association transport marker on `SourceForm::CaveTekiInfo`; it is not a retail
GenEnemy version. Surface decode refuses these rows. No fabricated GenEnemy,
`????` surface envelope, floor layout or full FloorSession is used.

All twelve native leaves are born on the initialized tutorial arena's surveyed
east approach. This bounded placement is disclosed in each run; it establishes
neither cave layout nor cave entry/save/resume acceptance. The direct collision
control exercises real engine dispatch, normal animation completion, source92
END59, invulnerability, unchanged static colliders and no rewards. Leaf actors
and Hosts carry null native generators. Caller-owned real association generators
retain sentinel alive/day bookkeeping through release, then the caller explicitly
retires every actor and generator registry association. Thirty normal updates
allow deferred native pool recycling before a new epoch/activation births all
twelve again; the final release repeats this cleanup gate. No cave walking or
human mode is qualified by this diagnostic. `--mode refusal` verifies absent
banks before any native leaf allocation. The supervisor remains bounded60seconds
and requires a cave-specific marker and successful process exit; an interrupted
run cannot qualify.

Pure controls retain all existing surface cases and add authenticated cave
provenance/envelope tampering, missing resources, exact whole reservation12,
foreign-family skip, surface/cave route separation, ordinal and retired-token
reuse refusal while unused slots remain, caller registry identity/retirement,
null native generator ownership and allocation/cleanup failure recovery. These
are controlled tests and do not claim native gameplay.
