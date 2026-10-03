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
