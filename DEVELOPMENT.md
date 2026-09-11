# Standalone milestone: local implementation

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

- 11 Python contract/session/protocol tests pass; includes 100 solo seeds, duplicates, corrupted manifests, replay conflicts, crash-journal recovery and fake AP server handshake/check/goal exchanges.
- 100 actual AP single-slot fills and one two-slot fill pass with the packaged world: `output/apworld-tests.log`.
- Three inherited BBFT/audio CTest regressions pass.
- Compiled native protocol probe passes opt-out, handshake, durable duplicate suppression, incompatible version/placement/state, mixed BBFT/standalone rejection and single-use-run checks.
- Hidden, silent native startup passes rendered Forest of Hope, twenty field reds, received color stocks, area unlocks, repair goal and zero invented checks: `output/native-startup-1.log` and its linked native log. This uses synthetic AP receipts to exercise native item handling; it is not a real AP server end-to-end gameplay run.
- Full native build passes. Initial build exposed an inherited missing `bbft_checked` test stub; adding that fake-transport function fixed the test link.

Physical part carrying, full-seed solo/AP completion, day rollover and exact campaign resume remain open acceptance work. Planning/issues: https://github.com/4laric/pikmin-randomizer/issues/1 .
