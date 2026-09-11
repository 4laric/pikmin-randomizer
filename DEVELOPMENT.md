# Standalone milestone: local implementation

## Seeded enemy sources drive bestiary logic (issue #36)

AP v0.15.0 adds optional-for-compatibility `enemy_layout` to schema 9; every newly generated schema-9 manifest includes it. `family-sources-v1` records 28 campaign source classes (stage, original species, actual seeded species, protected flag, earliest day). Generation resolves the existing three-bit mask before fill; strict canonical validation rejects inconsistent species, protection, schedules, versions or mask/layout pairs. Fingerprinting/slot-data/session recovery already cover the complete manifest. No native ABI, bootstrap fields, location IDs or item counts changed; the native saved ENEMIES mask remains authoritative for actual spawning.

`randomizer/enemies.py` preserves the three native pairings and source facts. `scripts/audit_enemy_sources.py` reads supplied retail campaign v10 generators, excludes non-campaign filenames, and checks the same personality-ID/Parameter0 protection predicate as GenObjectTeki. The 28 rows match the files, and 203 logged native births from five area boots agree with source protection and permutation. Unprotected Clamclamp shell type 10 is the guaranteed source for pearl type 13 (the protected ship-part shell is excluded); Puffy 16 remains a defeat check. All 19 bestiary species have at least one source under every mask, so counts remain 59/120. Future absent-source layouts fail validation rather than silently adding unreachable checks.

Modern bestiary reachability uses any accessible resolved source area, the actual corpse minimum (legacy species' loaded values included), and conservative all-color/weakest-carry constraints. It replaces the partial Bulborb/Bulbear special cases for new manifests; historical manifests keep their old rules. Schedules assume the player can wait/advance days (all recorded first appearances are within the repeat-day policy); no current-day state enters AP CollectionState. Status output reports later-day sources explicitly. Physical per-spawn return-route audits remain open; this does not claim every corpse route has been played through.

Validation: 56 Python tests; all eight mask fingerprints/layouts/solo fills; protected dwarf/male survivors; alternate and scheduled sources; field/carry/color gates; tamper rejection and old-manifest compatibility. Native probe agrees for all 35 type IDs, protected overrides and all masks. Modern bestiary protocol still passes. Packaged AP passed 2,580 fills (including every mask × five starts × three colors with both stat modes) plus remote-Blue, remote-Carry and a new remote-area gate for the swapped Bulborb check. No native rebuild required: the unchanged production boss-fixed executable is used.

Local package: `output/turkey-layout-01/Play.cmd`, Forest of Hope/yellow, mask 4, both stat modes, 120 checks; `checks.md` lists seeded sources. AP artifact: `output/pikmin_randomizer-0.15.0.apworld`. Validation sessions are separate from the fresh player session.

## Boss generator bit layout (issue #35)

Player reports of multiple Beady Long Legs were caused by the inherited native generator reader, not the family-shuffle mapping. `GenObjectBoss::readParameters` used C++ bitfields whose allocation order differs between the original target and the Windows compiler. Boss kind occupies bits 0–3 in the file; the old PC reader took bits 28–31. Real packed words such as 0xc4 (Flint Beetle), 0x08/09 (geysers), 0x45/85 (Candypop colors) and the Snagret entries consequently decoded as Spider. The same defect corrupted carried-item parameters.

Explicit masks/shifts now implement the fixed wire format in both read and write paths: kind 0–3, item index 4–5, color 6–7, count 8–11, pellet-index-plus-one 12–31. Legacy versioned readers remain unchanged. Native cache writes now match retail layout. The bitfield code is present in our integrated upstream revision 18ce1303; this source fix does not change the randomizer permutation. New spawn diagnostics record decoded boss kind and birth result during standalone runs.

The test-hook fixture exercises real GenObjectBoss read/write methods and RamStream for six retail words and 7,680 parameter combinations, including no-pellet and maximum-payload boundaries. Separate hidden area boots audit real generators and require one Spider in Navel and none elsewhere. Candypop creation legitimately returns null when the matching Onion is unavailable, as guarded in BossMgr::create; the audit permits this skip only for Candypops. Tests cover startup and spawn identity, not full boss fights or player-driven day-end save UI. User assets remain untouched.

Local corrected playtest: `output/turkey-bossfix-01/Play.cmd`, Forest of Hope/yellow, cap 10, both stat modes, enemy-family shuffle and 120 checks. Old packaged executables remain old builds; use the new launcher or rebuild current source.

## Remove landing checks (issue #34)

New schema-9 manifests require `no_exploration: true` and `no-exploration-v1` instead of `landing-only-v1`. CHECKSET bit 1 selects exploration-free immutable arrays; bit 0 still selects permanent structures. The native observer returns before awarding exploration checks. Existing schema-9 manifests without this field retain their 64/125 catalogs, and schemas 1–8 are unchanged. Remaining AP IDs are unchanged; no retired ID is reused. New pools have 59/120 locations and at least 25 repairs with both stat modes at starting Flarlic 1. The modern remote-carry test now places its reward at population 20 instead of landing.

51 Python tests and compiled bestiary/legacy collection protocols validate catalog compatibility, no landing/scout rewards, initial progression, replay and pool balance. Production build keeps TEST_HOOKS OFF. Local package: `output/turkey-no-land-01/Play.cmd`. AP v0.14.0.

## Bestiary through minibosses; landing-only exploration (issue #33)

Schema 9 / AP v0.13.0 adds eleven species checks and removes five scout checks: 64 collection locations, or 125 with permanent structures. The required boolean `permanent_checks` selects the two immutable native check arrays via `CHECKSET 0/1`. `bestiary-v2`, `landing-only-v1` and `check-set-v1` are required handshake capabilities. Existing AP IDs are retained; new IDs start at LOCATION_BASE + 200. Retired scout IDs remain reserved. Schema 1–8 manifests and journals retain their original order and behavior. The generation helper's `legacy_checks=True` is for compatibility tests; CLI and AP defaults use modern collection checks.

Ten new species use the real Onion absorption callback, including Clamclamp's pearl (native TEKI_Pearl 13, stored as a corpse pellet). Puffy Blowhog (16) alone uses health-depleted BTeki::die; non-gameplay cleanup, nonlethal removal, other corpse-species deaths and delivery of a fictitious Puffy corpse do not award it. Actual species IDs survive family swaps. New source routes conservatively require all colors plus the representative area's access, with Hope substituted for shuffled Bulbears. Mamuta still follows the native Impact Site day schedule. New corpse checks use conservative body-cap requirements; rolled carrying strength is not yet credited toward these bounds.

Loaded native carry minima: Dwarf Bulbear 3, Wogpole 1, Spotty Bulbear 10, Yellow Wollywog 7, Snitchbug 3, Breadbug 3, Puffstool 10, Cannon Beetle 30, Clamclamp pearl 3, Mamuta 8. Existing bestiary rules stay unchanged.

Validation: 50 Python tests including stable IDs, schema-7/8 compatibility, complete solo fills, carrier requirements, pool size and journal replay. Packaged AP: 2,460 fills plus remote-Blue/remote-Carry two-player cases. Compiled new-bestiary protocol covers both catalog sizes, all eleven additions, defeat/delivery/gameplay/area gating, scout suppression, duplicate delivery and journal recovery; legacy collection and permanent protocols also pass. A TEST_HOOKS fixture sends ten real loaded corpse/pearl configurations through GoalItem::suckMe and exercises the Puffy type through BTeki::die. It verifies all eleven emitted checks; it substitutes configurations/type in an isolated process and does not claim ten physical carry routes or a full Puffy combat animation were played through. Production build disables test hooks.

Local playtest: `output/turkey-bestiary-01/Play.cmd`, both stat modes, enemy-family shuffle, cap 10 and 125 checks. Full physical route/combat acceptance remains open; campaign resume remains #6.

## Damage-based structure work (issue #32)

Native `9c1bac13` replaces elapsed-minute wall/bridge work with damage per native animation event in ready standalone randomizer sessions. `ActBreakWall` consumes Action0, `ActBridge` consumes LoopEnd, and `ActBoMake` builds on Action0. Walls/bridges receive `Piki::getAttackPower() / 600`; sticks receive `getAttackPower() / 10`, followed by the existing 0.4 height conversion. This preserves the native base-10 stick contribution and uses one old one-minute wall/bridge work quantum per base-10 event as initial tuning. It does not promise identical vanilla completion times; field balance remains a playtest concern. Ordinary non-randomizer play retains its previous work calculation.

Actual damage includes red's native bonus and current rolled/progressive color modifiers. The alternate Job2 wall motion now receives attack-rate scaling while in BreakwallMode, alongside the existing Kuttuku work animation. Bomb-wall rejection still occurs in the original InteractAttack handler. No object/save layout, check identity, AP item pool, throw height or color ability changed. No new AP option or manifest schema is needed; existing randomizer seeds receive this behavior with the updated executable.

Validation: 48 Python tests. `scripts/test_work_damage_native.py` with TEST_HOOKS ON uses real Navel actors/objects and feeds native animation callbacks; it checks three damage profiles (10, 18.75, 15), identical per-hit work at elapsed 0/1/59 game minutes, one-time wall event consumption, bridge flag consumption, stick height, both work-animation rate multipliers and bomb-wall rejection. The separate permanent fixture passed all 17 Navel structures: partial rejection, completed-state serialization/reload and repeated-frame reward deduplication. These are synthetic action/observer tests, not unattended player pathfinding or full construction playthroughs.

Fresh local package: `output/turkey-work-01/Play.cmd`, Forest Navel / blue (color rolled), cap 10, 119 checks, both stat options and enemy-family shuffle. Navel was selected to expose walls, bridges and sticks together. Production build has TEST_HOOKS OFF; startup evidence and binary hash are recorded in UPSTREAM_SYNC.md. Player session is separate from validation sessions.

## Permanent structures and scalable checks (issue #31)

AP world v0.12.0 option `permanent_checks` / CLI `--permanent-checks` creates schema 8 with 119 locations. The first 58 native journal indices and all existing AP location IDs remain unchanged. Ten new population thresholds and 51 individual structures are appended; new AP IDs start at `LOCATION_BASE + 100`. Native schema 8 uses `CHECKS count index...` with bounded, unique indices and a required `check-set-v1` capability. Internal storage is a set, avoiding shifts beyond 64 bits; schemas 1–7 retain their original mask protocol. Check journals remain one index per complete line and merge idempotently on relaunch.

The 19 total-population thresholds are 20–100 every 10, 125/150/175/200, and 250–500 every 50. Populations still count living field/stored/sprout bodies, not carrying strength. Extra checks currently add repair rewards above the unchanged 25-repair goal; future item-pool changes can use this space.

The native all-area audit identified the following retail generator instances. `randomizer/obstacles.py` stores stable area, kind and rounded generator-position-plus-offset identities; it never identifies moving boxes by their current position. Full native observations are compared with this catalog by `scripts/audit_permanent_checks.py`.

| Area | Walls | Sticks | Bridges | Boxes |
| --- | ---: | ---: | ---: | ---: |
| Impact Site | 2 | 1 | 0 | 1 |
| Forest of Hope | 9 | 0 | 2 | 1 |
| Forest Navel | 8 | 4 | 5 | 0 |
| Distant Spring | 5 | 3 | 4 | 0 |
| Final Trial | 3 | 0 | 2 | 1 |

Active-gameplay observers scan the native MeltingPot item manager for walls/climbing sticks and WorkObject manager for bridges/boxes. Completion uses `BuildingItem::isCompleted`, built stick health reaching its maximum, `Bridge::isFinished`, and `HinderRock::isFinished`. Unknown identities, partial work, paused/unready observations and inaccessible areas do not award checks. Repeated frames/revisits deduplicate through the same native/session journal. These hooks do not alter object layouts or native save formats.

Route logic deliberately requires area access and all three colors for each structure; boxes additionally require capacity 100. This is conservative pending per-instance approach playtests, and does not credit rolled carrying strength toward the vanilla box pusher-body count. The status command lists structures and logic availability. Physical campaign/obstacle resume remains issue #6; AP journal recovery alone does not restore the native world.

Validation: 48 Python tests; 2,460 packaged AP fills including 100 new all-area/random-color/both-stat-mode schema-8 seeds, plus remote-Blue and remote-Carry two-player cases. Native protocol tests exercise restoration above index 64, all 19 milestones/all 51 identities, malformed/duplicate/out-of-range sets, partial and unknown identity suppression, and journal deduplication. Existing legacy, all-area/color, collection and progressive-stat protocols pass. Five hidden TEST_HOOKS fixtures validated all 51 real structures: partial state produces no check, completed values survive each object's actual native doSave/doLoad routines, the central gameplay observer reports only that area's structures, and repeated frames do not duplicate rewards. The bridge fixture explicitly sets saved work-progress values as well as completed geometry.

Native source `165ff3c5`; production TEST_HOOKS OFF build passed the fresh seed startup, ten blue field Pikmin, live stat receipts, other-color grants exactly once, area/goal gates, and only the landing/population-20/population-30 checks (30 follows the two five-Pikmin Onion grants). No obstacle was spuriously checked during startup.

Fresh local playtest: `output/turkey-build-01/Play.cmd`, Impact Site/blue, field cap 10, both stat options, enemy-family shuffle and permanent checks. Player session is fresh; tests use separate private sessions. AP artifact: `output/pikmin_randomizer-0.12.0.apworld`. Full player-driven route/combat/day-end acceptance is still pending.

## Combined wide rolls and upgrades (issue #30)

AP v0.11.0 supports both stat options together. New initial rolls use `color-stats-v2`, the `COLOR_STATS_WIDE` bootstrap marker and an independent v2 random stream: damage 25–200%, movement/attack rate 50–150% (25-point increments), carrying strength 1–5. Original v1 manifests and their narrower ranges remain valid. Native stores the immutable initial profiles separately from current profiles; each authenticated tier adds +25 percentage points or +1 carrying strength to that baseline. Maximum upgraded values are damage 250%, movement/attack rate 175%, carry 7. Existing color abilities and throw heights are unchanged.

Validated 45 Python tests, 2,360 packaged AP fills (including 50 combined-mode seeds), both existing two-player cases, native combined-mode receipt/cap/retraction protocol and standalone stats/Flarlic protocols. Production TEST_HOOKS OFF startup passed the exact new seed's rolled area/color/options, live upgrades, expected checks, color grants and area/goal gates. Native source `622ae8f8`. Wider extremes still need player-driven combat/route feedback; the prior weighted-crew fixture validates the underlying carrying hooks.

Fresh local test package: `output/turkey-mixed-01/Play.cmd`, Forest of Hope/blue, field cap 10, enemy-family shuffle, collection checks and both stat modes. Starting profiles (damage/movement/attack/carry): red 100/125/100/5; yellow 150/150/100/5; blue 125/50/125/1. AP package: `output/pikmin_randomizer-0.11.0.apworld`. The player session is fresh; hidden startup used a separate private session.

## Progressive per-color AP upgrades (issue #29)

AP world v0.10.0 adds `progressive_color_stats` / `--progressive-color-stats`. Twelve item types (one per color/stat), eighteen total copies: damage has two +25% tiers, carry strength has two +1 tiers, movement and attack rate each have one +25% tier. Starts use vanilla values; the original red damage bonus remains. Collection checks are enabled to retain the 25-repair goal and every unlock within the 58-location pool. Carry items are progression and other stat items useful. Rolled-stat mode remains supported but is mutually exclusive with progressive mode.

The bootstrap requires `PROGRESSIVE_STATS 1` and the matching `progressive-color-stats-v1` handshake. Authenticated cumulative receipts produce twelve capped `UPGRADES` counts in native state; parsing rejects missing, malformed, excessive and retracted tiers before committing the state. Live getters serve existing actors and weighted crews. Overlay/status derive profiles from the same receipts; route logic credits only received carry tiers. Receipt replay and journal recovery preserve upgrades; extension-aware journal validation also fixes relaunch for starting-Flarlic and rolled-stat seeds. This does not implement native day/squad persistence.

Validation: 42 Python tests, 2,360 packaged AP fills, remote-Blue and remote-Red-Carry two-player fills. The latter makes a weight-40 part reachable at field cap 20 only after a remote red carry upgrade. Native progressive protocol validates baseline, independent tiers, receipt replay, caps and retraction rejection; old rolled-stat and Flarlic protocol suites pass. The live test-hook fixture starts with vanilla stats, receives upgrades after actors exist, then verifies all three damage/movement/attack hooks and seven bodies lifting a weight-20 part, including put-down after losing strength. Native source commit `568ec58f`. Full player-driven combat/routes remain pending.

Fresh local seed: `output/turkey-upgrades-01/Play.cmd` (Forest of Hope/blue, cap 10, enemy swaps, collection checks, progressive stats). The accompanying production binary has TEST_HOOKS OFF; hidden startup passed rendered world, ten blue Pikmin, one-time other-color grants, live stat receipts, area/goal gates and only the expected opening checks. Player session remains fresh. AP artifact: `output/pikmin_randomizer-0.10.0.apworld`. Generated seeds, binaries and test logs stay local.

## Per-color stat randomization (issue #28)

Opt-in `randomize_color_stats` YAML / `--randomize-color-stats` CLI, AP world v0.9.0. Profiles use an independent SHA256 stream and integer percentages; `color-stats-v1` is required by the manifest/handshake and `COLOR_STATS` is a strict bootstrap extension. Old seeds omit both and retain unity multipliers. Damage is 50–150% of the existing color-specific base; movement and attack rate are 75–125%; carry strength is integer 1–3. No throw or ability changes.

Native hooks: `Piki::getAttackPower`, all walking-speed entry points, and attack-loop playback after animation metadata chooses its speed. `ActTransport` lift/continuation/gauge counts and `Pellet` active-carrier checks sum strength; slot allocation and population remain body counts. Hauling averages crew movement multipliers, with bounded effective-carrier speed bonuses. Native type arrays and save layouts are unchanged. The overlay/status displays all profiles. Logic reduces part headcounts conservatively using the weakest required route-color strength; it does not assume an off-route strong color can perform the delivery.

The synthetic native fixture uses real Pikmin and a real ship-part pellet, checks damage/walking/attack timing for all three colors, then attaches a mixed crew, skips their lifting animation, invokes native route/lift behavior and verifies put-down after losing sufficient strength. It does not establish a complete player-driven carry route or combat playthrough. Run `scripts/test_color_stats_protocol.py` with the native probe; run `scripts/test_color_stats_native.py` with a TEST_HOOKS build and private user assets. Production builds must have TEST_HOOKS disabled.

Validation: 38 Python tests; 2,260 packaged AP single-slot fills plus the remote-Blue two-player case; native color-stat/legacy, Flarlic, all-area/color, enemy and collection protocol tests. The live fixture passed with seven bodies supplying strength 20 for a weight-20 ship part, including slot allocation, hauling speed and put-down after one red detached. Native commit `9783304e` built with native JAudio, portable CPU settings and TEST_HOOKS OFF in `native/build-stats`. Its production startup rendered Impact Site with ten yellows, emitted only the two expected opening checks, applied other-color grants once and passed area/goal gates without test fixtures.

Local playtest: `output/turkey-stats-01/Play.cmd`, fresh solo seed, random area/color (rolled Impact Site/yellow), collection checks, enemy swaps, starting Flarlic 1 and randomized stats. Separate private smoke-test sessions were used; the player's session is fresh. AP package: `output/pikmin_randomizer-0.9.0.apworld`. These generated files and user assets are excluded from source control. Full player-driven combat and carrying-route acceptance remain to be tested.

## Starting Flarlic (issue #24)

New YAML/CLI generations default to `starting_flarlic: 1` (10 field capacity), configurable from 1 through 10. The remaining `10 - starting_flarlic` Flarlic items are in the pool. Native startup withdraws at most the cap from the original 20 starter Pikmin, leaving the remainder stored. Overlay, status, carry-weight logic and native state use the same initial capacity. Existing manifests remain unchanged. An optional manifest field and required `starting-flarlic-v1` capability accompany a strict `STARTING_FLARLIC` bootstrap extension; old native builds reject it. AP package version is 0.8.0.

AP's global early-item request provides Flarlic for Forest of Hope starts or Forest of Hope access for other cap-10 starts, allowing remote delivery while avoiding reverse-fill dead ends. Validation: 34 Python tests, 2,160 AP single-slot fills and a remote-Blue two-slot fill; native capacity/legacy protocol tests; production startup with ten red Pikmin in the field and ten stored, total-population-20 check, color grants, area gating and goal handling.

The native port now has a separate `--randomizer-seed` adapter and a Python solo/AP runner. No BBFT conductor or shared AP installation link is required. Physical parts are still at their original positions: the native adapter deliberately rejects relocation manifests until the slot/carry audit is complete.

## Implemented

- Strict versioned manifest with separate native part IDs, permanent location IDs and reward IDs; standalone game identity `Pikmin Randomizer`.
- Thirty checks (28 parts and two Onion discoveries), 25 repair rewards and five color/area unlocks. Victory requires 25 received repairs, not physical part count. This fixes the specification's initial item-count mismatch.
- Deterministic solo reward fill with backtracking and conservative inherited color/area rules.
- Packaged standalone AP world with identical check requirements and an exported `.pikmin.json` manifest. AP rewards are authoritative; local collection does not immediately award its remote reward.
- Version/capability handshake through private file IPC; per-run token, per-manifest fingerprint, native check journal, atomic runner saves, AP receipt overlap validation and exclusive session writer lock.
- Recovery of complete native check records after runner interruption. Native stale-heartbeat hold and normal foreground/input gates remain active.
- Independent day-two Forest of Hope boot with twenty reds and received Yellow/Blue/area unlocks. No BBFT shared tools or travel controls.
- Engine calendar repeats day 29 to retain safe bounds in the original 30-entry diary tables. Standalone disables vanilla ending authority; repair progress/victory appears in the native window title and log. This is not a new ending cutscene.

## Important current limits

Full native campaign resume is not implemented. Relaunching restores check/reward history but starts a fresh day-two native campaign and starter population. Do not treat this as save/resume sign-off: day/area/squad persistence and extinction recovery remain issue #6. Day-29 sunset behavior needs physical testing. New placement routes are not validated, no parts are relocated, and expansion types/treasures/caves are not implemented.

## Build

Configured build directory: `native/build-randomizer`, MinGW GCC 16.2, CMake/Ninja, matching SDL2, native JAudio, CPU-specific optimization disabled. Executable: `native/build-randomizer/bin/nectar.exe`. Matching SDL2.dll and libwinpthread-1.dll are beside it. The compiler/bin tools must be on PATH for rebuilding and running the small test executables.

```powershell
cmake --build native/build-randomizer --target pikmin_pc pc_randomizer_probe pc_bbft_test jaudio_bbft_test -j 6
python -m unittest discover -s tests -v
python scripts/test_native_protocol.py native/build-randomizer/pc_randomizer_probe.exe
python scripts/build_apworld.py
python scripts/test_apworld.py C:/Users/alari/Archipelago
```

The AP test reads that source installation and loads our packaged world in its own process; it does not install a world or change a link.

## Solo launch

Run from this repository root. Use a fresh output filename for each generation; generation refuses to overwrite an existing manifest.

```powershell
python -m randomizer generate --seed first-pikmin --output output/first-pikmin.json
python -m randomizer validate output/first-pikmin.json
python -m randomizer run output/first-pikmin.json --session-dir output/first-pikmin-session --exe native/build-randomizer/bin/nectar.exe --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets
```

The assets argument points to existing extracted files containing `dataDir/stages/`. The runner makes a directory junction into a new private runtime folder; saves/logs/settings stay in that folder. It does not copy or write original assets. Close the game to end the runner. AP mode requires `websockets` (tested with 13.1); solo does not.

## AP launch

Build `output/pikmin_randomizer.apworld` and install it into a separate AP setup, generate a `Pikmin Randomizer` slot, and use that generation's exported `.pikmin.json`. Do not manufacture an unrelated AP-mode manifest: the client must match the generated slot's manifest and fingerprint. Launch as above with `--server localhost:38281`. Optional server password comes from `PIKMIN_AP_PASSWORD`. AP authentication validates room/team/slot identity and waits for received-item synchronization before releasing native gameplay.

## Expanded checks (opt-in)

### Enemy family swaps (schema 6 prototype)

Enable `--enemy-shuffle` during CLI generation or `enemy_shuffle: true` in AP. This enables the five-area catalog with 58 checks and unchanged reward pool. Seed and slot select one of seven nonempty combinations of three swaps: dwarf Bulborb/Bulbear, adult Bulborb/Bulbear, female/male Sheargrub. These are global species-family swaps, not independent arbitrary replacements at every spawn. Starting area/color selections are unaffected by the separate enemy stream.

Only those six native type IDs can change. Named pellet/drop IDs and nonzero special personality parameters pin a generator; bosses, water creatures, spawners, plants and hazards are outside the pool. Original generator type data is not mutated; replacement assets are marked for loading before birth, then the replacement uses its own native AI with the original spawn personality. All seven masks and protected-spawn overrides are verified in the compiled probe.

Bestiary checks still mean defeating the actual species. Adult Bulborb rules move conservatively to Distant Spring with all colors when its swap is enabled; native Spring startup confirms adult Bulbears become Bulborbs. Dwarf Bulborb rules retain Forest of Hope because protected dwarf spawns remain there; the audit did not find an original dwarf Bulbear source in Spring and makes no such assumption.

Evidence: 28 Python tests (including 200 randomized enemy seeds), 2,000 AP single-slot fills plus the remote-Blue two-slot fill, and both legacy native probes pass. Production Forest/Spring startup with all three swaps passes. `scripts/audit_enemy_smoke.py output/enemy-forest-smoke output/enemy-spring-smoke` verifies 60/46 real native births with 19/6 replacements, protected spawns and the original Cannon Beetle retained. This is spawn/initial-AI evidence, not combat, carcass delivery or save/revisit acceptance. Those remain open in issue #19 and full native resume remains #6. No existing playtest is changed.

### All five areas (current schema 5)

New generation with `--starting-area random` now samples all five areas. Fixed choices are `impact`, `forest`, `navel`, `spring`, and `trial`; `--all-areas` enables the five-area catalog with a fixed Forest/Navel start. Combine with `--starting-color random` or a fixed color. AP uses `starting_area: randomized`, the named choices, and `all_areas: true` when retaining a fixed Forest/Navel start. Old manifests remain valid and are not rerolled.

All 15 area/color pairs are intentionally allowed, including risky Distant Spring red/yellow starts. No automatic blue grant, rescue, local placement restriction or hazard adjustment is made. In multiworld, a player may exhaust local checks and wait for a remote item. The AP test explicitly places the Spring player's Blue Onion at the other player's landing check and verifies water access only after receipt. Global solvability does not promise continuous local progression. Solo uses a constructive local fill.

The starting area is free; the other four area access items are shuffled. Impact Site now has landing, scouting and Positron Generator checks (new IDs 55-57); Main Engine remains synthetic tutorial completion and not a check. Total: 58 checks, two color unlocks, four area unlocks, eight Flarlic and 44 repair rewards; goal remains 25. No part relocation is introduced.

Restricted starts cannot assume population farming above 20 until Forest of Hope access, or Navel access with reds. No early boss kill or non-blue water crossing is assumed. These are conservative rules, not claims of complete route or extinction acceptance. Impact Site runs day two with tutorial completion state. Received colors without a current camp Onion remain stored until a subsequent landing; exact campaign resume remains unfinished.

Validation: 26 Python tests; 1,900 AP single-slot fills plus a remote-Blue two-slot fill; compiled gates for all 15 area/color pairs, including native journal IDs 55-57. Production startup matrix evidence is in `output/all-area-matrix.log`. Physical Positron delivery, repeated visits, day transitions and complete seed playtests remain open under #16/#6/#7. Earlier sections below describe previous schema milestones where their scope differs.

All 15 production native starts pass: selected area renders, matching 20-Pikmin squad deploys, only starting area is accessible initially, other-color receipts grant once, all received area gates open, and only landing/population-20 checks fire. Legacy protocol probes and the three targeted BBFT/audio regressions pass. Fresh standalone example: `output/turkey-spring-01/Play.cmd` (fixed Spring/yellow); it is a solo playtest, not an AP-connected slot.

### Randomized starting color (schema 4)

Add `--starting-color random` to generation, or choose `red`, `yellow`, or `blue`. In AP use `starting_color: randomized` (or a named color). Non-default color options enable expanded checks. Area and color use separate deterministic streams; selecting a color does not reroll the area. The chosen color is recorded explicitly in schema 4. Schemas 1-3 retain red starts and their existing reward layouts.

The selected Onion starts owned with 20 stored Pikmin, then withdraws the matching squad through native Onion behavior. The other two Onion unlocks are shuffled; non-red starts introduce Red Onion while removing the starting color's unlock from the pool. Received other-color unlocks grant five stored Pikmin once. When no camp Onion actor exists in the current area, that stock becomes usable on a subsequent landing. The overlay always counts the selected starting color as owned and does not assume red access.

Logic conservatively requires red for ship parts, scouting and Navel bestiary approaches because legacy routes assumed permanent red access. Non-red Navel starts cannot use population checks above 20 in logic until red or Forest of Hope access is obtained. These restrictions can be relaxed only after fire-free routes and breeding access are audited. Native hazards retain their original behavior. This feature does not implement full campaign resume/extinction recovery.

Tests cover 300 randomized solo seeds across all six area/color combinations, red item receipts and session recovery, 900 AP single-slot fills and one mixed-color two-slot fill. `scripts/test_starting_color_matrix.py` exercises native starts with synthetic receipts for the other colors; it does not certify physical breeding or day/area transitions. Gameplay acceptance remains tracked in issue #18.

All six production native startup tests pass (`output/start-color-matrix.log`): selected area renders, matching 20-Pikmin squad deploys, other colors grant five once, starting color receives no extra grant, and only the expected starting checks fire. 23 Python tests, both legacy native protocol probes and three targeted BBFT/audio regressions also pass. A fresh example package is `output/turkey-spin-05/Play.cmd` (Navel/blue).

### Starting area options

Use `python -m randomizer generate --starting-area random --seed my-seed --output output/my-seed.json`.
AP option: `starting_area: randomized` (also `forest` or `navel`). Randomized/Navel starts automatically enable expanded checks and schema 3. Supported random pool: Forest of Hope and Forest Navel, with deterministic selection from seed and slot. Spring and Trial starts are disabled pending opening audits. The selected profile is recorded in the manifest; old schema-1/2 seeds remain unchanged.

Navel starts grant Navel access and replace its pool item with Forest of Hope access. Other area unlocks remain independent items; this is not a forced linear level order. Start with 20 reds and a 20 field cap in either area. Color and weight requirements remain conservative; no new color-route assumptions are introduced. Population checks are available in the starting area; species and location checks retain their area gates. Keep the 55-check/25-repair pool balance.

Validation: 20 Python tests (including 200 randomized-start solo fills), 400 AP single-slot fills plus one mixed-start two-slot fill. Native Navel startup verifies rendered gameplay, Red Onion withdrawal of 20 reds, initial travel gates, received area/color grants and the two expected starting checks. Complete Navel breeding, travel/day transitions, scouting and full-seed completion still require player acceptance. Full native campaign resume remains incomplete as documented above.

Track implementation and remaining acceptance in issue #16. The current playtest executable is copied into its package, so rebuilding does not change an active playtest.

The three implementation batches are specified in [BATCH_PLAN.md](BATCH_PLAN.md).
Use `python -m randomizer generate --expanded --seed exploration --output output/exploration.json`
or set `expanded_checks: true` in an AP player configuration. Run with the same session runner above.
Schema 2 has 55 checks: the original 30, nine actual deployed-population milestones, eight first-defeat species and eight landing/scouting objectives. Start at 20 capacity; eight Progressive Flarlic items raise it to 100. Heavy parts require their native minimum carrier count in generation logic. The goal remains 25 repairs, with 17 surplus repairs in the expanded pool.

Use `python -m randomizer status output/exploration.json --session-dir output/exploration-session --output output/exploration-status.md` for the check list. Population completion is historical, not a live population display. Scout means grounded travel 600 horizontal world units from the ship; named landmarks are future work.

Builds reserve object capacity for 100 while enforcing the received deployment limit. Original settings and schema-1 limits are preserved. The generated native catalog must agree with Python: `python scripts/generate_native_catalog.py --check`.

`scripts/test_expanded_native.py` tests compiled event/protocol behavior. The optional `PIKMIN_RANDOMIZER_TEST_HOOKS=ON` CMake build supports `scripts/test_expanded_startup.py`, which supplies synthetic Onion stock and sets one enemy's health to zero to exercise native withdrawal and death lifecycles. It is not evidence of player combat or breeding. Production builds must keep this option OFF (the default). Add `C:/msys64/mingw64/bin` to PATH for build and smoke commands.

Expanded validation: 17 Python tests, 100 solo seeds per profile, 200 actual AP single-slot fills plus one mixed-profile two-slot fill, and the expanded compiled native probe pass. Full player-driven route/combat/day/save acceptance remains pending.

## Evidence

### Corpse deliveries and total population (#22, schema 7)

Generate with `--collection-checks` (AP option `collection_checks: true`).
This enables the five-area expanded catalog. Existing schemas 1–6 retain their
original semantics and IDs. Schema 7 uses distinct AP IDs for the replacement
checks, advertises `total-population-v1`/`corpse-delivery-v1`, and supports
enemy shuffle either enabled or disabled.

Population milestones are 20, 40, 60, 80, 100, 150, 200, 300, and 500 total
living Pikmin, using the game's `GameStat::allPikis` (field, sprouts, and Onion
storage). These are historical milestones, not cumulative births. Above 20,
logic requires an audited farming area; Flarlic is not required to accumulate
stored population. Flarlic still gates deployment and ship-part carry weights.

The eight bestiary locations now require corpse absorption at an Onion.
`GoalItem::suckMe` identifies corpse configs by type, color, and actual species
model ID, so ordinary pellets and ship parts do not count. Kills are suppressed
for schema 7. The original death hook remains for old seeds. Delivery logic
conservatively requires all three colors for carry-home routes. Loaded corpse
minimum weights were audited as 3, 10, 1, 1, 1, 7, 5, and 7 respectively, all
below starting capacity 20.

Validation: 32 Python tests, 2100 AP single-slot fills including 100 schema-7
fills, existing remote-Blue multiworld coverage, new native protocol tests,
legacy expanded/enemy probes, and three native/audio regressions. A test-hook
fixture (`--collection-fixture` in `test_native_startup.py`) adds 480 stored
Pikmin alongside 20 deployed, confirms the 500 milestone at capacity 20, kills
a real Dwarf Bulborb without a check, then invokes the Onion callback on its
corpse and verifies the delivery check. This tests native callbacks and loaded
configs; player carrying/absorption animations remain acceptance work. Test
hooks must be OFF for delivered builds.

### Consecutive saves after direct boot (#21)

The day-end crash dump contains a serialized day-4 save at `cardData - 0x2000`:
the first save rotated the unset current index (zero) into the backup index,
and a later save used block index -1. Padding erased adjacent globals,
including `playerState`, which then crashed ship rendering. A first save now
derives the redundant backup block from card quick-info records when the old
current index is invalid. The writer rejects backup indices outside 1–4 before
touching state or card data; the save UI requests card preparation for unset
indices.

With `PIKMIN_RANDOMIZER_TEST_HOOKS=ON`, pass `--save-fixture` to
`scripts/test_native_startup.py` using a fresh disposable output directory.
The fixture checks rejected indices 0/5/255 against an unchanged card buffer
and live state pointers, creates a private card, makes two consecutive saves
starting with current index zero, and verifies the resulting slot metadata.
It deliberately creates a new card in that test run only. Production builds
must use test hooks OFF. This is native save/rotation coverage, not full
day-end UI or exact campaign resume acceptance; #6 remains open.

### Enemy health gauges (#20)

`DGXGraphics::drawOneTri` now calls `GXEnd` on PC. The hardware consumes a
primitive's declared vertex count, but the PC renderer submits it in
`pc_gfx_end`; without that call the next `GXBegin` discarded each health-gauge
triangle. This affected ordinary seeds as well as enemy shuffle.

An isolated Spring fixture moved one Bulbear near Olimar and held its health
at 50%. Before the fix, its gauge reached Display state with ratio 0.5 and a
valid screen projection, but the captured framebuffer had no gauge. After
the fix, the framebuffer shows the yellow half-circle and black border.
Local captures: `output/gauge-diagnostic-03/frame.png` and
`output/gauge-fixed-01/frame.png`. This is scripted rendering evidence,
not a player-combat test. Diagnostic modifications were saved to
`output/gauge-diagnostic.patch` and removed; production test hooks remain OFF.
The change affects other callers of the same triangle helper too. Full-health
hiding and death behavior were not changed; player acceptance remains in #20.

- 11 Python contract/session/protocol tests pass; includes 100 solo seeds, duplicates, corrupted manifests, replay conflicts, crash-journal recovery and fake AP server handshake/check/goal exchanges.
- 100 actual AP single-slot fills and one two-slot fill pass with the packaged world: `output/apworld-tests.log`.
- Three inherited BBFT/audio CTest regressions pass.
- Compiled native protocol probe passes opt-out, handshake, durable duplicate suppression, incompatible version/placement/state, mixed BBFT/standalone rejection and single-use-run checks.
- Hidden, silent native startup passes rendered Forest of Hope, twenty field reds, received color stocks, area unlocks, repair goal and zero invented checks: `output/native-startup-1.log` and its linked native log. This uses synthetic AP receipts to exercise native item handling; it is not a real AP server end-to-end gameplay run.
- Full native build passes. Initial build exposed an inherited missing `bbft_checked` test stub; adding that fake-transport function fixed the test link.

Physical part carrying, full-seed solo/AP completion, day rollover and exact campaign resume remain open acceptance work. Planning/issues: https://github.com/4laric/pikmin-randomizer/issues/1 .

## Per-color population milestones (2026-09-11, issue #39)

New schema-9 manifests carry color_population=true and color-population-v1; CHECKSET bit 4 selects the new native catalogs and older binaries reject that check set. Existing schema-9 manifests without the flag and earlier versions preserve their catalogs. Fresh AP IDs begin at LOCATION_BASE+300, reserving all retired aggregate IDs.

GameCoreSection observes GameStat::allPikis[color], the existing per-color sum of formation/free/work Pikmin, sprouts (mePikis), and Onion storage. Native observation requires gameplay, a ready session and the matching unlocked Onion; it awards milestones once via the durable check journal. The aggregate observer is suppressed in color mode. Logic requires the matching color and existing audited farming routes, except the starting color's initial 20. Native source commit: 386eb6ae; public snapshot refreshed.

Validation: production game and protocol probe builds pass with test hooks OFF. All 59 Python tests pass. Twelve compiled per-color cases cover all starting colors, both milestone sets, locked/all-Onion inventories, thresholds 19/20/500 at cap 10, inactive/invalid observations and journal replay. Legacy collection and modern bestiary protocol regressions pass. Native counter wiring reviewed against GameStat::update and sprout registration; player validation of growing/storing Pikmin remains pending. Local package output/turkey-population-01/Play.cmd has 158 checks, Forest of Hope/yellow, cap 10, enemy shuffle, wide stat rolls and progressive stat items. AP world version 0.16.0.
`scripts/test_apworld.py` also passes: 2,580 single-slot fills across legacy/new catalogs, starting combinations, stat modes and enemy masks, plus three multiworld cases. Log: output/color-population-ap-tests.log.


## Useful benefits (2026-09-11, issue #40)

New collection manifests opt into benefit_items=true / benefit-items-v1. Exactly 25 repairs remain; two +25% whistle and two +25% plucking items are followed by a 2:1:1 delivery/flowers/heal cycle. Solo filler is shuffled deterministically. AP marks these items useful; population logic stays conservative and does not assume any delivery receipts.

Native commit 4d34dd25 journals consumable counts in session/benefits-used.txt, bound to the manifest fingerprint. Counts are monotonic and persisted before applying effects, preventing replay on reconnect/relaunch. There is a narrow consume-before-effect crash window; full campaign state is still not restored on launch, and already-spent effects are not recreated. Invalid/partial/foreign journals fail closed. Effects run only during active gameplay outside day-end and wait for an applicable target. Permanent receipt tiers cap at two and apply without compounding. Whistle draw and hold/release calls use the same multiplier; only the Nuku animation receives the plucking multiplier. Flowers update both the visible leaf model and formation counts one growth stage at a time.

Validation: 62 Python tests pass, with the benefits tests rechecked after adding tier clamping. Compiled protocol tests cover delayed receipts, duplicate AP replay, consumed-item relaunch, later new receipts, malformed/retracted state and foreign journal rejection; color-population, progressive-stat, legacy collection and bestiary regressions also pass. AP validation passes 2,580 single-slot fills and three multiworld fills with the new pool. Three hidden/silent native actor fixtures (red/yellow/blue starts, cap 10) verify +10 stored Pikmin without other-color stocks, all ten field actors flowered, full captain healing, 150% upgrade multipliers and no second application. Logs: output/benefits-native-01/*/runs/*/native.log. Whistle/pluck interaction feel remains for player testing; fixtures verify received multipliers, with call-site integration reviewed. The production build disables test hooks.

Local package: output/turkey-benefits-01/Play.cmd, Hope/yellow, 158 checks, wide initial stats, progressive stat items, seeded enemy shuffle and the new reward pool. AP artifact: output/pikmin_randomizer-0.17.0.apworld. Old seed catalogs/pools remain unchanged.

## Per-spawn adult enemies (2026-09-11, #42/#43)

Native 8f2b045d, AP world 0.18.0. Opt-in per_spawn_enemies resolves 15 adult Bulborb/Bulbear slots before fill, preserving nine Bulborbs/six Bulbears and both species in early renewable Hope/Spring sources. It overrides the global family mask; other species remain vanilla. Old seeds remain unchanged. Independent owned IDs bind audited stage/file/record identities and survive a tagged eight-byte enemy cache trailer. Vanilla generator names, original species, schedules, personality/drop fields and coordinates remain unchanged. Header/source hashes and enemy-slots-v1 reject incompatible seeds/assets/caches. Explicit enemy-spoiler CLI exports readable names and schedules outside the HUD.

Audit: 116 generator files, 690 Teki/boss-manager records across all five areas; 28 rounded-coordinate collisions are why coordinates are not identity. The native disk/cache audit agrees with all 690 facts. Real stage-cache save/preload restores all nine Hope and six Spring adult IDs/choices (1053/702 bytes respectively). Corrupted tagged records fail explicitly. The audit does not certify physical clearance or carry paths, or full campaign save/resume.

Validation: 71-test Python suite passed, then an added source-file mismatch/missing/extra-generator test passed along with the other three slot tests (72 total tests now). New generation tests cover 200 layouts, all 15 starts/colors at cap 10 with stats, all 19 species sources and every enabled solo check. Packaged AP tests pass 150 new-mode fills and 10 remote-Blue multiworlds with every check reachable, plus the existing 2580 fills/three multiworld cases. Compiled tests pass exact assignments across reverse load order/restored IDs, five malformed bootstraps, legacy family masks and modern bestiary behavior. Five-area native audit sees matching actual births; production TEST_HOOKS OFF starts in both Hope/Spring render with mixed adult species, yellow cap 10 and exact capability handshake. Evidence: output/slots43-*.

Production local test: output/turkey-slots-01/Play.cmd, Hope/yellow, 158 checks, cap 10, wide stats/progressive upgrades; solo placement has three full-check spheres. Executable SHA-256 EF22C49B57EBB61EE90F22FBFBC3AE1278FD4022A7CEF12EF1F51BE29DC71BA7. Output enemy-spoiler.json is intentionally a spoiler. Existing TheLynk bundle remains unchanged.

Remaining: physical combat/corpse routes (Bulbear is larger), culling/day-cycle playtest acceptance, full campaign resume, grouped/distributed dwarf/grub adapters, then wider habitat pools/density/boss tracks. #42/#43 stay open for those remaining gates. Existing protected farming sources are preserved; randomized bonus drops remain separate #47.

## Fixed-count family groups (2026-09-11, #53)

Native eddbd6d7, AP 0.19.0. group_spawn_enemies / --group-spawn-enemies implies adult per-spawn mode and adds 12 fixed-count circular generators: two Hope dwarf singles, six Hope Sheargrub groups and four Spring day-16 dwarf groups. Each whole generator receives one species; original group count, circular distribution, schedule and personality/drop fields stay intact. Per-species body totals may change. Protected farming sources remain pinned. Both dwarf types and both Sheargrub sexes have early Hope sources; Spring group logic retains day 16. Old adult-slot and global-mask seeds keep their existing layout.

Vanilla count-only caches cannot identify individual surviving members. Group-wide assignment therefore preserves species even when survivor ordering changes. enemy-groups-v1 and a separate saved group_layout gate the new protocol; existing owned IDs/cache tags are reused. Explicit enemy-spoiler output now includes all 27 choices. A new option defaults off; no added checks or filler changes.

Validation: 74 Python tests pass, including 100 group layouts with every-check solo reachability, all starts/colors and legacy/tamper cases. Packaged AP testing passes 150 grouped fills and 10 remote-Blue multiworlds with every enabled check reachable. Native group protocol verifies assignments, reverse order, protected identities, reconnect journal recovery and four malformed bootstrap cases; adult-slot, global family, bestiary and color-population protocol regressions pass. Five-area audits (690 records) pass twice: cached groups retain original-count-minus-one survivors, then full original counts when the respawn interval is reached. Real native birth callbacks match the assigned species in both fixture paths. Production TEST_HOOKS OFF startup passes in Hope/Spring with grouped mode, rendered world and yellow cap 10. Evidence: output/groups53-*.

Local seed: output/turkey-groups-01/Play.cmd, Hope/yellow, cap 10, wide stats/progressive upgrades, 158 checks and three solo spheres. Production SHA256 5AB1CD89521F30579D6206E537C1BDA29819345C950F6660954E38736B5DF830. AP artifact: output/pikmin_randomizer-0.19.0.apworld. Previous seeds/bundles are unchanged.

Physical combat/clearance/corpse-return and player-driven day transitions remain acceptance work; fixtures exercise native survivor/respawn mechanics, not a complete campaign. Full campaign resume remains #6. Mixed species within one generator would need persistent per-member identity and is deferred; broader habitat pools, density and boss adapters remain later tracks.

## Direct-launch performance counters (#54)

PC initialization now starts with TS_Off, so direct gameplay launches do not inherit the polys/anims renderer overlay. The legacy debug menu is not compiled into this port. Original non-PC initialization is preserved. Native commit: 44e3fef2.

Validation: production build with test hooks OFF passes; isolated grouped startup in Hope and Spring renders, handshakes and matches seeded births (output/timers54-startup). Source inspection confirms the performance text is gated by TS_Off; no framebuffer comparison was performed. Local turkey-mixed-01 and turkey-groups-01 launchers now use bin/nectar-no-counters.exe; running processes and sessions were preserved. SHA256: f89db3d3afe13acbfe30356256380f6c96764d99bf0ffbb2b1609e3de795b48a.

## Corpse catalog index repair (#55)

Native 4ddb72cd resolves the original eight corpse checks by stable collection names instead of positions in the active catalog. Color population milestones had shifted those positions, causing a Bulborb to award Wogpole. Expanded bestiary protocol now exercises all nineteen species and rejects premature Wogpole credit; both modern check sets and legacy collection protocol pass. Existing session rewards/history are preserved rather than retroactively rewritten.
Production build and isolated grouped Hope/Spring startup also pass (output/corpse55-startup). Both local mixed/groups launchers use nectar-corpse-fix.exe on next launch; running game remains untouched.

## Enhanced graphics defaults (#56)

Native 88557248 sets both PcConfig initializers and applyDefaults to the Enhanced preset: FXAA, subtle bloom, 8x anisotropy, original fog and neutral grading. Config loading still overlays saved preferences; reset-to-defaults also selects Enhanced. Source comparison against graphicsPresetFor/applyGraphicsPreset confirms matching values.
Production build passes with hooks OFF; fresh isolated Hope/Spring grouped startup renders and handshakes (output/enhanced56-startup). Both local playtest launchers point to nectar-enhanced.exe on next launch. Saved configs and active game preserved; no visual-quality benchmark performed.

## Pellet Posy follow-through (#57)

Native 699a7c3a keeps nearby eligible Posy attackers waiting during the death animation. spawnPellets hands that exact drop to Pikmin still assigned to the source via ActTransport; no nearby-work scan is used. Whistle/action changes, holding items, mushroom status, day end, distance and occupied slots exclude handoff. Non-PC behavior stays unchanged. Normal transport handles landing, slots, routes and randomized carrying strength. Source review confirms normal cleanup releases the attack target and carrying uses calcCarryStrength. Physical single/multiple-attacker, whistle cancellation and full Onion delivery acceptance remain open.
Production build (hooks OFF) passes: output/posy57-build.log. Isolated grouped Hope/Spring startup renders and handshakes: output/posy57-startup. These startup checks do not exercise the new Posy interaction. Local mixed/groups launchers now use nectar-posy.exe without changing active sessions.

## D-pad color selection (#58)

Native f8d36e1c cycles on mapped D-pad Left/Right press edges in Walk and established ThrowWait. Searches only normal, alive, throwable squad Pikmin within the existing 200-unit selection radius, skips absent colors, and cancels simultaneous left/right. A held swap returns the prior Pikmin to Normal, puts the replacement in Hanged and retains captain charge/animation. Existing next-throw HUD follows selection. Wheel zoom retains its input and D-pad preferences. Initial grab/pending approach must finish before held swapping is accepted. Source-reviewed zero/one-color no-ops, wraparound and input cancellation; physical gamepad, emptying squad and throw-release acceptance remain open.
Production build passes (hooks OFF), with isolated grouped Hope/Spring render/handshake startup passing in output/dpad58-startup. Startup does not exercise the input/swap interaction. Local mixed/groups launchers now select nectar-dpad.exe; current processes/session data preserved.
