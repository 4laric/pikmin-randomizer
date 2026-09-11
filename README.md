# Pikmin Randomizer

Experimental standalone and Archipelago randomizer for Pikmin 1, built on Open Nectar.

## Completion playtest (v0.20.0)

Fresh collection seeds now have population checks at **10, 25, 50 and 100 per color** (12 total), and no Captain Heal in the item pool. Full permanent-structure mode has 113 checks; without structures there are 62. Matching location names retain their AP IDs; new 10/25 milestones use new IDs. Existing manifests retain their original check sets and rewards. Fresh bonus slots use two Pikmin Deliveries per Flower Shower, after the captain upgrades.

Opt-in `miniboss_enemies: true` / `--miniboss-enemies` replaces three named adult slots with one Puffstool, one Mamuta and one Armored Cannon Beetle. It implies per-spawn mode and combines with grouped enemies. Choices are saved before fill, and the seed preserves early renewable Bulborb/Bulbear sources in both areas. That currently leaves the replacements in Hope. Counts, schedules, protected originals and original drop personality stay intact. Cannon Beetle projectile dependencies are preloaded. Boss-manager encounters, Progg and density changes are excluded.

**Experimental:** native births/rendering and solo/AP reachability pass, but combat, enlarged footprint clearance, corpse-return routes and actual revisit behavior need player acceptance (#61/#46). Day-end campaign saves now resume on the next launch (#6); mid-day quitting returns to the last saved day. This is not a fully validated full-campaign release.

Fresh local solo seed: `output/turkey-finish-01/Play.cmd`. Resolved random start is Hope/red, cap 10, wide stats and progressive upgrades, 113 checks, five logic spheres, 25 Ship Repairs to finish. Includes the recent bestiary, counter, Posy, D-pad and graphics changes. Start/Enter can skip cinematics through their gameplay event boundaries; text/result/save screens retain normal controls (engine/tools/CUTSCENE_SKIP.md). Named enemy mappings are in the optional `enemy-spoiler.json`.

## Current features

- Random starting area across all five areas, and random red/yellow/blue starting color.
- Area and Onion unlock items, 25 Ship Repair rewards for victory, and Flarlic increasing field capacity from a configurable default of 10 to 100.
- Exploration checks and optional Onion corpse-delivery bestiary checks; total-population milestones up to 500 include stored Pikmin and sprouts.
- Seeded Bulborb/Bulbear and Sheargrub family swaps, with protected enemies pinned.
- Optional seeded damage, movement, attack rate and carrying-strength profiles for each base color.
- HUD and status profiles reveal when each color's Onion is unlocked; the starting color is visible immediately. Upgrades received before discovery stay hidden until that unlock.
- Solo play, a standalone AP world, persistent check/reward history, and a transparent progress overlay.

**Prototype limitations:** physical ship parts remain in vanilla positions. Relaunch restores checks/rewards and the last committed day-end campaign checkpoint. Mid-day squad positions are not saved; extinction recovery still needs gameplay acceptance. Some starting combinations deliberately require remote progression in multiworld. Enemy-family swaps have player validation; corpse deliveries and the day-end save fix still need full gameplay acceptance.

The current native build fixes a boss-generator decoding bug that turned Snagrets, geysers, beetles and other entries into Beady Long Legs on PC. Rebuild or use the corrected package; changing a seed alone cannot fix an older executable.

## Per-spawn adult enemies (v0.18.0, experimental)

**v0.19.0 adds `group_spawn_enemies: true` / `--group-spawn-enemies`.** This implies adult per-spawn mode and adds 12 fixed-count circular generators: two Hope dwarf singles, six Hope Sheargrub groups, and four Spring dwarf groups that activate from day 16. Each generator rolls one species for its entire group. Group sizes, distributions, schedules and protected drops are preserved; per-species body totals can change. The seed guarantees early Hope sources for both dwarf types and both Sheargrub sexes, and keeps Spring's later timing in bestiary logic. Protected farming sources remain untouched.

Vanilla caches store group survivor counts rather than individual member identities. Group-wide choices prevent a survivor changing species on reload. Native fixtures cover reduced survivor counts and the respawn interval; full physical route/combat/day-cycle acceptance remains open. Use a fresh seed and an executable with `enemy-groups-v1`. Local grouped playtest: `output/turkey-groups-01/Play.cmd`; named mappings are available through `enemy-spoiler`.

Set AP YAML `per_spawn_enemies: true`, or generate with `--per-spawn-enemies`, for independent choices at 15 named adult Bulborb/Bulbear generators in Forest of Hope and Distant Spring. Both species have early renewable sources in both areas; total counts remain nine Bulborbs and six Bulbears. Other species keep vanilla identities in this mode. This option overrides the global `enemy_shuffle` mask; it is off by default and old seeds retain their choices.

The seed records every choice before AP fill. Owned generator IDs survive tagged native cache records, without changing vanilla names, positions, schedules or drops. Source hashes reject incompatible generator assets before launch. Use a fresh seed and an executable supporting `enemy-slots-v1`; campaign progress resumes from the last day-end save.

For an explicit named mapping, run `python -m randomizer enemy-spoiler <seed.json> --output enemy-spoiler.json`. It includes original/replacement species and schedule/source facts; the normal overlay does not reveal the mapping. Local playtest: `output/turkey-slots-01/Play.cmd`.

All-five-area disk/cache audits, actual mixed births, generation and AP reachability tests pass. Physical combat and return-route acceptance remain open, especially the larger Bulbear footprint. Mixed species within a single group, cross-family pools, density changes and bosses remain future tracks.

## D-pad throw color selection

Tap D-pad Left/Right (keyboard Left/Right arrows with default bindings) to cycle available throwable squad colors. Once a Pikmin is held ready to throw, the same controls swap it while preserving charge. Existing throw preview shows the selected Pikmin. One available color is a no-op; Up/Down and menu controls retain their functions. Works with mouse-wheel camera zoom. Physical controller/held-release acceptance remains in #58.

## Pellet Posy follow-through

On PC, Pikmin attacking a Pellet Posy wait for its death animation and attempt to carry its actual dropped pellet. This works with Chain Actions off. Whistled-away Pikmin are excluded, and normal transport handles carrier slots and randomized strength. Physical throw-to-delivery acceptance is pending in #57.

## Graphics presets

Fresh settings now default to Enhanced (FXAA, 8x anisotropy and subtle bloom). Saved preferences are preserved. Open F1, choose Graphics, and select Original or Enhanced with Left/Right. Enhanced adds FXAA, 8x anisotropic filtering and subtle bloom while retaining original fog and neutral colors. Save to retain changes; closing without saving restores the previous graphics. Individual changes show Custom. Resolution and gameplay settings are preserved.

## Useful rewards (v0.17.0)

New collection seeds contain exactly **25 Ship Repairs**, the existing unlocks/Flarlic/stat items, and these benefits in the remaining slots:

| Item | Effect |
| --- | --- |
| Pikmin Delivery (10) | Adds 10 leaf Pikmin to the unlocked, booted Onion with the smallest total population. Does not spawn extra field Pikmin or unlock colors. |
| Flower Shower | Flowers living field Pikmin, maintaining their formation counts. Waits if there are no eligible Pikmin. Stored Pikmin and sprouts are unchanged. |
| Captain Heal | Fully heals a living, injured Olimar. Waits while health is full. |
| Progressive Whistle Radius | Two +25% upgrades, reaching 150% radius; the displayed circle grows with the effective radius. |
| Progressive Plucking Speed | Two +25% upgrades, reaching 150% plucking animation speed. |

Each seed gets two copies of each captain upgrade. Remaining benefits cycle 2 deliveries : 1 flower shower : 1 heal, with a partial cycle when needed. They are useful AP items; conservative logic does not depend on deliveries to satisfy population checks. Solo filler placement is seeded and shuffled. The HUD/status shows current whistle and plucking percentages.

Consumables wait for active gameplay outside pauses, menus, cutscenes and day-end. Day-end checkpoints store native world data and consumed-bonus counters together. Relaunch retains current AP checks/receipts, restores the saved world and only reapplies bonuses absent from that saved world. Permanent upgrades come from current receipts. An unsaved day rolls back; bonuses consumed during it become pending again. Incomplete checkpoint writes are ignored; corrupt or foreign-seed committed checkpoints stop launch instead of silently resetting progress.

Save at the normal end-of-day results screen and wait until the area-selection screen returns before closing. Relaunch the same `Play.cmd` and session directory to continue at the next saved day. `session/campaign/` contains immutable save generations and the native card. Keep it with `session.json`; do not mix seeds. Older builds' per-run card files are preserved but are not automatically imported: this resume path starts with the first save made by the new build.

Old seeds retain their original pool. Use a fresh seed and updated executable; native capability `benefit-items-v1` gates the new protocol. Local playtest: `output/turkey-benefits-01/Play.cmd`.

## Color-specific population checks (v0.16.0)

New collection seeds replace every aggregate population milestone with separate Red, Yellow and Blue milestones. Totals include field Pikmin, stored Pikmin and sprouts of that color; colors never combine toward a threshold. There are 27 population checks (9 per color), or 57 (19 per color) with permanent checks enabled, for **77/158 total locations**. Thresholds still run through 500 per color. Extra locations use the existing reward pool, leaving room for future bonuses and traps.

Logic requires the matching Onion and audited farming access; only the starting color's initial 20 is credited without farming. Flarlic limits the field, not these totals. New checks use fresh AP IDs and a `color-population-v1` capability; old manifests retain their aggregate checks and IDs. Use a fresh seed and updated native executable. Test package: `output/turkey-population-01/Play.cmd` (Hope/yellow, field cap 10, enemy shuffle, wide stats and progressive upgrades).

Enemy randomizer development plan: [phased roadmap](ENEMY_RANDOMIZER_ROADMAP.md), from individual spawn shuffling through opt-in boss encounters.

## Enemy layout and progression (v0.15.0)

Enemy-family swaps were already deterministic in `enemy_mask`. New seeds additionally contain a versioned `enemy_layout` describing the resulting species sources, protected spawns and earliest campaign days. All 19 bestiary rules use those sources rather than fixed area assumptions. Changing a mask without updating the matching layout is rejected. Native still consumes the same saved mask; it does not reroll on launch.

For example, swapping adult Bulborbs/Bulbears moves the Bulborb check to Distant Spring and the Bulbear check to Forest of Hope. Protected Dwarf Bulborbs remain available in Hope even when unprotected dwarfs swap. Later sources also count: unshuffled Dwarf Bulbears appear in Spring from day 16, and Snitchbugs have sources in both Hope and Spring. The status report lists source areas and later-day availability. Logic assumes days can be advanced under the existing repeat-day policy; the schedule is not a new item gate.

Return routes conservatively require all three colors. Carry requirements use the actual species' native corpse weight and the weakest owned/rolled carrying strength among those required colors; damage and movement upgrades do not bypass area/color access. The pool still has 59/120 checks. Older manifests without `enemy_layout` retain their previous logic; generate a fresh seed for the revised rules.

## No exploration rewards (v0.14.0)

New collection-mode seeds award neither landing nor scout checks. There are **59 checks**, or **120 with permanent structures**, including all 19 bestiary checks. Population milestones supply opening checks; the repair goal remains 25. Existing seeds retain their saved catalogs, including any landing checks. Use the new native build and a fresh seed for this change.

## Expanded bestiary (v0.13.0)

New collection-mode seeds have **19 bestiary checks** and **five landing checks**; scout-distance checks are retired. Collection mode is now the CLI/AP default. There are 64 locations without permanent structures, or 125 with `permanent_checks: true`. Existing manifests retain their original catalogs and IDs; use a fresh seed and current native build for the new list. Explicit legacy AP collection opt-out still selects the older catalog.

The eleven additions are Dwarf Bulbear, Wogpole, Spotty Bulbear, Yellow Wollywog, Puffy Blowhog, Swooping Snitchbug, Breadbug, Puffstool, Armored Cannon Beetle, Pearly Clamclamp and Mamuta. Deliver bodies to an Onion for all except Puffy Blowhog (defeat it; no corpse) and Clamclamp (deliver its pearl). Each species pays once; boss and harmless-creature checks remain outside this batch. Family swaps report the actual species. Carry-home routes remain conservative and require all colors; the new checks also respect native corpse weights, including 30 carriers for the Cannon Beetle. Damage does not auto-complete any location.

## Build on Windows

Install Python 3.12 (including tkinter), Git, CMake, Ninja, and MSYS2's MinGW64 GCC and SDL2 packages. Run in PowerShell with the MinGW64 `bin` directory on PATH. This is the tested platform; inherited engine documentation also describes Linux, which has not been validated for this randomizer.

```powershell
git clone https://github.com/4laric/pikmin-randomizer.git
cd pikmin-randomizer
$env:PATH = "C:\msys64\mingw64\bin;" + $env:PATH
cmake -S engine -B engine/build-randomizer -G Ninja -DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON -DPIKMIN_NATIVE_OPTIMIZE=OFF -DPIKMIN_RANDOMIZER_TEST_HOOKS=OFF
cmake --build engine/build-randomizer --target pikmin_pc pc_randomizer_probe -j 6
python -m pip install -r requirements-ap.txt
python -m unittest discover -s tests -v
python scripts/test_collection_protocol.py engine/build-randomizer/pc_randomizer_probe.exe
```

The game executable is `engine/build-randomizer/bin/nectar.exe`. Keep MinGW64 on PATH when launching so its runtime DLLs can be found. Game assets are not included: supply your own extracted assets directory containing `dataDir/stages/`. See [the engine's asset instructions](engine/assets/README.md).

## Try a solo seed

```powershell
python -m randomizer generate --seed first-spin --expanded --starting-area random --starting-color random --enemy-shuffle --collection-checks --output output/first-spin.json
python -m randomizer run output/first-spin.json --session-dir output/first-spin-session --exe engine/build-randomizer/bin/nectar.exe --assets "C:/path/to/your/assets"
```

Keep the terminal open while playing. Use a new manifest filename for a new seed. `--collection-checks` is enabled by default; existing saved seeds retain their original kill/delivery rules. No PowerShell script execution-policy changes are needed for these commands.

## Archipelago

```powershell
python -m pip install -r requirements-ap.txt
python scripts/build_apworld.py
```

Install `output/pikmin_randomizer.apworld` into your Archipelago setup. Generate a `Pikmin Randomizer` slot, then launch its exported `.pikmin.json` with the run command above and `--server HOST:PORT`. Use that generated manifest, not an unrelated solo seed. The AP option `collection_checks: true` selects corpse deliveries and total population. Optional server password: `PIKMIN_AP_PASSWORD` environment variable.

```yaml
Pikmin Randomizer:
  starting_flarlic: 1
  collection_checks: true
  progressive_color_stats: true
  randomize_color_stats: true
  permanent_checks: true
```

`starting_flarlic` accepts 1–10 and defaults to 1: each unit grants 10 field capacity. The pool contains the remaining Flarlic needed to reach 100 (nine at the default). The starter population is still 20; with a cap of 10, ten remain stored in the Onion. This option enables expanded checks. Solo generation uses the same default via `--starting-flarlic`. Existing manifests without this option retain their original capacity rules.

At cap 10, AP requests an early Flarlic for Forest of Hope starts, or early Forest of Hope access for other starts, so sparse opening checks can lead to farming and further progression. These items may be in another player's world. New configured seeds require the updated native build and AP world v0.8.0; older native builds reject the new bootstrap instead of silently using the wrong cap.

`progressive_color_stats: true` (AP world v0.11.0) adds separate progressive AP items for each color's damage, movement, attack rate and carrying strength. Each damage upgrade adds 25 percentage points (two copies per color); each carry upgrade adds 1 strength (two copies). Movement and attack rate each have one +25-percentage-point upgrade. Without initial rolls, colors start at their vanilla bases. The 18 upgrade items fit the existing 58 collection checks while preserving all unlocks and at least 25 repair rewards. Carry upgrades are progression; other stat upgrades are useful items. CLI: `--progressive-color-stats`. This opt-in enables collection checks. Received upgrades immediately affect existing Pikmin, are capped, survive receipt replay/reconnect, and appear in the live overlay/status. Carry logic credits only upgrades already owned. Throw height, water/fire abilities and bomb handling remain vanilla.

`randomize_color_stats: true` / `--randomize-color-stats` now rolls wider initial profiles: damage 25–200%, movement and attack rate 50–150%, all in 25-point steps, and carry strength 1–5. Enable both options for upgrades on top of those rolls: a carry-5 color reaches 7, a damage-25% color reaches 75%, and a damage-200% color reaches 250%. Bonuses add to the immutable baseline and never compound on reconnect. New rolls require `color-stats-v2`; existing saved v1 profiles retain their values. With both options off, stats remain vanilla. Throw height is unchanged.

`permanent_checks: true` (AP v0.12.0), or CLI `--permanent-checks`, originally expanded the pool to **119 checks** (125 in new v0.13.0 seeds): 19 total-population milestones and individual completion checks for 27 walls, 8 climbing sticks, 13 bridges and 3 pushable boxes across all five areas. Population thresholds are every 10 from 20 through 100, every 25 through 200, then every 50 through 500. Partial damage/building never counts; each finished structure pays once. Old location IDs and old seeds remain supported; a new schema uses a scalable check set beyond 64 locations. New checks currently add repair rewards beyond the unchanged 25-repair goal, leaving room to rebalance future upgrade pools.

Wall, bridge and climbing-stick work now uses each worker's actual damage per animation event in randomizer sessions. Damage upgrades increase work per hit; attack-rate upgrades increase work frequency, including the alternate wall animation. Red Pikmin's native damage bonus counts. Waiting between hits adds no accumulated work. Bomb walls still require bombs. Structure completions remain location checks only; receiving an item never completes a structure.

Initial tuning converts damage to native work units: walls/bridges use damage / 600 per event; sticks use damage / 10 (then the engine's 0.4 height conversion). These are starting balance values, not a claim of identical vanilla completion times. Existing randomizer manifests use this behavior when launched with the updated engine; no new YAML option is required.

Structure rules conservatively require area access and all three colors until individual approaches are playtested; boxes additionally require field capacity 100. The status report lists each structure and its current logic availability. AP journal persistence prevents duplicate rewards after revisiting/relaunching; full native campaign/physical-obstacle resume is still unfinished.

Carrying sums the strength of attached Pikmin while each still occupies one physical slot and one field-cap slot. Hauling uses the crew's average movement multiplier; the existing flower/extra-carrier speed bonus is bounded for stronger crews. Part logic uses `ceil(weight / guaranteed strength)` while retaining the inherited route-color requirements. Guaranteed strength is the weakest profile among the required route colors (including the inherited red-access assumption), so the logic can under-credit a stronger specialized crew rather than invent a route. Population checks still count bodies. Full-route gameplay acceptance remains separate from the native mixed-crew fixture.

## Source and development

- `randomizer/`: standalone seed logic, session runner, and overlay.
- `apworld/`: AP integration; `tests/` and `scripts/`: validation and packaging.
- `engine/`: complete source snapshot required by this randomizer, with licenses and provenance in [ENGINE_SOURCE.md](ENGINE_SOURCE.md). No separate BBFT checkout is needed.
- [DEVELOPMENT.md](DEVELOPMENT.md): detailed implementation and historical validation; its `native/` paths refer to the maintainer's isolated development checkout. Use `engine/` in a public checkout.
- [SPEC.md](SPEC.md), [BATCH_PLAN.md](BATCH_PLAN.md), and [GitHub issues](https://github.com/4laric/pikmin-randomizer/issues): roadmap and outstanding work.

Builds, extracted assets, seeds, saves, logs, and runtime state are excluded. This source upload is not a prebuilt game release.

## Credits

Built on [Open Nectar](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port) and the [projectPiki Pikmin decompilation](https://github.com/projectPiki/pikmin). Thanks to TheLynk for permission to use the Pikmin AP world's logic and locations as a reference; this remains a separate project as requested. See the preserved [engine license](engine/LICENSE.MD) and [third-party notice](engine/LEGAL.md).
