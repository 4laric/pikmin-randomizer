# Pikmin Randomizer

Experimental standalone and Archipelago randomizer for Pikmin 1, built on Open Nectar.

## Current features

- Random starting area across all five areas, and random red/yellow/blue starting color.
- Area and Onion unlock items, 25 Ship Repair rewards for victory, and Flarlic increasing field capacity from a configurable default of 10 to 100.
- Exploration checks and optional Onion corpse-delivery bestiary checks; total-population milestones up to 500 include stored Pikmin and sprouts.
- Seeded Bulborb/Bulbear and Sheargrub family swaps, with protected enemies pinned.
- Optional seeded damage, movement, attack rate and carrying-strength profiles for each base color.
- Solo play, a standalone AP world, persistent check/reward history, and a transparent progress overlay.

**Prototype limitations:** physical ship parts remain in vanilla positions. Relaunch restores checks and rewards but starts a fresh native campaign; exact day/area/squad resume and extinction recovery are unfinished. Some starting combinations deliberately require remote progression in multiworld. Enemy-family swaps have player validation; corpse deliveries and the day-end save fix still need full gameplay acceptance.

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

Keep the terminal open while playing. Use a new manifest filename for a new seed. Omitting `--collection-checks` retains the older kill/field-count checks. No PowerShell script execution-policy changes are needed for these commands.

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
```

`starting_flarlic` accepts 1â€“10 and defaults to 1: each unit grants 10 field capacity. The pool contains the remaining Flarlic needed to reach 100 (nine at the default). The starter population is still 20; with a cap of 10, ten remain stored in the Onion. This option enables expanded checks. Solo generation uses the same default via `--starting-flarlic`. Existing manifests without this option retain their original capacity rules.

At cap 10, AP requests an early Flarlic for Forest of Hope starts, or early Forest of Hope access for other starts, so sparse opening checks can lead to farming and further progression. These items may be in another player's world. New configured seeds require the updated native build and AP world v0.8.0; older native builds reject the new bootstrap instead of silently using the wrong cap.

`progressive_color_stats: true` (AP world v0.11.0) adds separate progressive AP items for each color's damage, movement, attack rate and carrying strength. Each damage upgrade adds 25 percentage points (two copies per color); each carry upgrade adds 1 strength (two copies). Movement and attack rate each have one +25-percentage-point upgrade. Without initial rolls, colors start at their vanilla bases. The 18 upgrade items fit the existing 58 collection checks while preserving all unlocks and at least 25 repair rewards. Carry upgrades are progression; other stat upgrades are useful items. CLI: `--progressive-color-stats`. This opt-in enables collection checks. Received upgrades immediately affect existing Pikmin, are capped, survive receipt replay/reconnect, and appear in the live overlay/status. Carry logic credits only upgrades already owned. Throw height, water/fire abilities and bomb handling remain vanilla.

`randomize_color_stats: true` / `--randomize-color-stats` now rolls wider initial profiles: damage 25–200%, movement and attack rate 50–150%, all in 25-point steps, and carry strength 1–5. Enable both options for upgrades on top of those rolls: a carry-5 color reaches 7, a damage-25% color reaches 75%, and a damage-200% color reaches 250%. Bonuses add to the immutable baseline and never compound on reconnect. New rolls require `color-stats-v2`; existing saved v1 profiles retain their values. With both options off, stats remain vanilla. Throw height is unchanged.

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
