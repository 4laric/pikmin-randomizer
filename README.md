## Disable Tutorials

Use **F1 > Mods > Disable Tutorials > On**, then **Save**, to skip informational hints including nectar/flower, bombs, capacity and carry routes. Off by default. [Details and validation](docs/DISABLE_TUTORIALS.md).

# Pikipelago

Experimental standalone and Archipelago randomizer for Pikmin 1, built on the Open Nectar PC port. It randomizes the starting area and color, Pikmin stats and enemies, and turns exploration, population milestones, bestiary deliveries and structure completion into checks; new seeds contain 30 Ship Repairs, 25 of which unlock the Emperor Bulblax finale that ends the game.

The project is now called **Pikipelago**. Archipelago still lists it as `Pikmin Randomizer`; use that name in YAML. Package filenames and save folders retain their existing names for compatibility.

## Status

- Playtest quality. Native rendering, seed generation and reachability are tested; large parts of physical combat, carrying routes and full-campaign play still rely on player acceptance.
- Windows only. Linux is described in the inherited engine documentation but has not been validated for this randomizer.
- Physical ship parts remain in their vanilla positions; rewards come from checks, not from the parts themselves.
- Relaunching restores your checks, received rewards and the last day-end save. Progress made during a day that was not saved is lost and returns to the last saved day.
- Enemy randomization modes are experimental.
- There is no vanilla 30-day limit; the campaign failure deadline is disabled.

## Requirements

- Windows 10/11 x64.
- Your own legally obtained Pikmin 1 disc image (GameCube, USA Rev 1 `GPIE01` or Europe `GPIP01`, as `.iso`/`.gcm` or Dolphin's `.rvz`/`.wia`), or an already extracted assets directory containing `dataDir/stages/`. Assets are not included; see [the engine's asset instructions](engine/assets/README.md). The runner links to the directory and never writes to the original files.
- `Play.cmd` uses the bundled runtime when present, otherwise Python 3.12 with tkinter and the `websockets` package (`python -m pip install -r requirements-ap.txt`). tkinter provides the overlay and F8 tracker; `websockets` is only needed for Archipelago play.
- For Archipelago play: the `pikmin_randomizer` .apworld and an Archipelago 0.6 or newer host.

## Install and first launch

1. Download the release ZIP and, for multiworld, the matching `pikmin_randomizer-<version>.apworld`.
2. Extract the ZIP to a folder of your choice. Saves and settings live under `%APPDATA%\PikminRandomizer`, one session per seed, so the game folder can be replaced by a newer release without losing progress.
3. Run `Play.cmd`. The Pikipelago window opens.
4. Choose **New solo run** or **Open seed** (for AP, use the `.pikmin.json` file for your slot), then either choose your Pikmin disc image (`.iso`, `.gcm`, `.rvz` or `.wia`; USA Rev 1 or Europe) or a folder that already contains extracted `dataDir/stages/`. The first Play extracts about 650 MB of game data from the image into `%APPDATA%\PikminRandomizer\game-data`; the image itself is only read. RVZ and WIA images are decoded to a temporary ISO first (about half a minute, 1.4 GB of temporary disk space, deleted afterwards). GCZ, CISO and NKit images must be converted with dolphin-tool.
5. Play. Save at the end-of-day results screen, wait until the area map returns, then close the game. Relaunch the same `Play.cmd` to resume from that day.

## Solo play

Choose **New solo run** in the launcher. Leave the seed name blank for a fresh run, or reuse a name to return to the same seed. The starter preset uses a random starting area and color, standard stats, wall/bridge/box checks, no traps, and the Emperor Bulblax goal. Choose game data once, then click **Play solo**. Seeds and progress are stored in your user-data folder; the last selected run is restored when the launcher opens.

For Archipelago, use **Open seed** to select the `.pikmin.json` from your host, enter the server address and port shown on the room page (not the page URL), and click **Connect & play**. The slot comes from the seed file; the room password is optional and is not saved. The launcher reports connection retries and successful synchronization.

These launcher improvements require a build containing the installer UX changes; the existing playtest.3 download predates them.

Advanced generation options remain available through the `randomizer` package:

```powershell
python -m randomizer generate --seed <name> --output <dir>/seed.json
python -m randomizer run <dir>/seed.json --session-dir <dir>/session --exe <path to nectar.exe> --assets "C:/path/to/your/assets"
```

`generate` creates the seed manifest; `run` launches the game with that seed and a session directory. Use a new manifest file and session directory for a new seed. Keep the terminal open while playing. Useful `generate` flags (defaults in brackets):

| Flag | Meaning |
| --- | --- |
| `--goal repairs\|emperor_bulblax` | Finish at 25 repairs, or unlock and defeat the Emperor Bulblax at 25 repairs [`emperor_bulblax`] |
| `--starting-area forest\|navel\|impact\|spring\|trial\|random` | Starting area; `random` picks from the four non-Trial areas [`forest`] |
| `--starting-color red\|yellow\|blue\|random` | Starting Onion and 20 Pikmin [`red`] |
| `--starting-flarlic 1..10` | Initial field capacity in tens [1 = 10 Pikmin] |
| `--randomize-color-stats` | Seeded damage, movement, attack rate and carrying strength per color |
| `--progressive-color-stats` | 36 stat upgrade items across the three colors; enables permanent checks |
| `--permanent-checks` | Individual wall, bridge and box completion checks |
| `--collection-checks` | Onion corpse deliveries and population 10/25/50/100 per color [on] |
| `--campaign-enemies` | Campaign-wide enemy pools including Teki minibosses; overrides the older enemy toggles |
| `--enemy-shuffle`, `--per-spawn-enemies`, `--group-spawn-enemies`, `--miniboss-enemies` | Older, experimental enemy modes |
| `--bomb-rock-weight 0..10` | Bomb Rock Delivery filler weight; 0 disables [1] |
| `--all-areas` | Five-area catalog with a fixed start |
| `--expanded` | Legacy expanded check catalog |

Other subcommands: `validate <seed.json>` checks a manifest and reports its progression spheres; `status <seed.json> --session-dir <dir>` prints collected checks and bestiary sources; `enemy-spoiler <seed.json> --output enemy-spoiler.json` reveals the named enemy mapping (a spoiler; the normal overlay never shows it).

## Archipelago play

1. Put `pikmin_randomizer-<version>.apworld` in your Archipelago `worlds` folder (or build it yourself with `python scripts/build_apworld.py`, which writes `output/pikmin_randomizer.apworld`).
2. Start from [examples/Player1.yaml](examples/Player1.yaml), the current playtest configuration, and adjust the options below.
3. Generate the multiworld. The generator exports a `<slot>.pikmin.json` manifest for your slot; use that file, not a solo seed.
4. Run it with the server address:

```powershell
python -m randomizer run <slot>.pikmin.json --session-dir <dir>/session --exe <path to nectar.exe> --assets "C:/path/to/your/assets" --server host:port
```

For an Archipelago seed the window shows server and password fields; the password is passed to the game runner for that launch only and never saved. `Play.cmd --console <seed.json>` runs the text launcher instead of the window. When running the module directly, pass `--server host:port` and set the password in the `PIKMIN_AP_PASSWORD` environment variable before launching.

Universal Tracker is supported: install the same `.apworld` next to Universal Tracker, connect it to the room with your slot name, and it rebuilds this seed's exact check logic from the server's slot data without a YAML. The in-game F8 tracker keeps working alongside it.

DeathLink is supported. With `death_link: true`, every `death_link_pikmin` ordinary Pikmin deaths (default 10, remainder kept across days) send one link to the room, and each received link kills up to that many living field Pikmin through their normal death; Olimar and Onion stock are never touched. Links that arrive while the game is closed are dropped, and a link is applied only during active gameplay. The HUD and F8 tracker show the received count and progress toward the next send. Pikmin left behind at sunset do not count. Received items are applied while you play and persist across relaunches; consumable rewards received on the area map wait until you land. Some starting combinations deliberately require progression from other players' worlds.

## Options

YAML options for the `Pikmin Randomizer` game. Defaults are those of the .apworld; [examples/Player1.yaml](examples/Player1.yaml) enables more than the defaults.

| Option | Meaning | Default |
| --- | --- | --- |
| `goal` | `repairs` completes at 25 repairs. `emperor_bulblax` unlocks the fight at 25 repairs and requires defeating him; Final Trial Access is still required. | `emperor_bulblax` |
| `starting_area` | `forest`, `navel`, `impact`, `spring`, `trial` or `randomized`. Randomized excludes Final Trial. | `forest` |
| `random_start_areas` | Eligible areas for a randomized start; nonempty list of `impact`, `forest`, `navel`, `spring`. | all four |
| `starting_color` | `red`, `yellow`, `blue` or `randomized` starting Onion and 20 Pikmin. | `red` |
| `starting_flarlic` | Initial field capacity in tens (1–10). Remaining Flarlic items raise the cap to 100. | 1 |
| `collection_checks` | Bestiary corpse deliveries (Puffy Blowhog defeat and Clamclamp pearl) plus population 10/25/50/100 per color. Enables all five areas. | true |
| `permanent_checks` | Adds 43 individual walls, bridges and boxes (105 total checks). Climbing sticks are excluded because they reset daily. | false |
| `randomize_color_stats` | Seeded damage, movement and attack rate at 25/50/75/100% per color; carrying strength starts at 1. | false |
| `initial_damage_min` / `initial_damage_max`, `initial_movement_min` / `..._max`, `initial_attack_rate_min` / `..._max` | Bounds for the rolled initial stats: 25, 50, 75 or 100; each minimum must not exceed its maximum. Equal bounds fix the stat. | 25 / 100 |
| `progressive_color_stats` | Per-color stat upgrades as items (36 at the default counts). Enables permanent checks. | false |
| `damage_upgrades` / `carry_upgrades` | Copies per color, 0–4. +25 percentage points damage / +1 carrying strength each. | 4 / 4 |
| `movement_upgrades` / `attack_rate_upgrades` | Copies per color, 0–2. +25 percentage points each. | 2 / 2 |
| `death_link` | Archipelago DeathLink in Pikmin units (see Archipelago play). | `false` |
| `death_link_pikmin` | DeathLink unit: deaths per outgoing link and casualties per received link, 1 to 100. | `10` |
| `bomb_trap_weight` | Filler weight for Bomb Ambush: five lit bomb rocks in a ring around Olimar, classified as a trap. 0 disables. | `0` |
| `progg_trap_weight` | Filler weight for Smoky Progg Ambush: spawns one native Smoky Progg nearby, classified as a trap. 0 disables. | `0` |
| `bomb_rock_weight` | Filler weight for Bomb Rock Delivery (3); Pikmin Delivery / Flower Shower weights are 2 / 1. 0 disables. | 1 |
| `campaign_enemies` | Campaign-wide ground, frog, flying, small-enemy and aquatic pools with a Teki miniboss in Hope, Navel and Spring. Overrides the older enemy toggles. | false |
| `enemy_shuffle` | Seeded compatible enemy-family swaps. | false |
| `per_spawn_enemies` | Individual adult Bulborb/Bulbear assignments at 15 named points; overrides `enemy_shuffle`. | false |
| `group_spawn_enemies` | Experimental: one seeded species per dwarf/Sheargrub group; implies per-spawn adults. | false |
| `miniboss_enemies` | Experimental: three adult slots become Puffstool, Mamuta and Cannon Beetle; implies per-spawn adults. | false |
| `all_areas` | Five-area catalog with a fixed start. | false |
| `expanded_checks` | Legacy expanded catalog; modern collection checks already enable it. | false |

Fewer stat upgrades mean more consumable filler. Editing the YAML affects newly generated seeds only.

## Playing

Controls and quality-of-life additions:

- **F8** opens a searchable tracker window over the game: checks by area and status, received items, Onion unlocks, field capacity, repairs and discovered color stats. F8 or Esc closes it. The game keeps running underneath, so pause first if needed.
- **D-pad Left/Right** (Left/Right arrow keys with default bindings) cycle the throwable squad color; with a Pikmin already held, they swap it while keeping the charge.
- **Start/Enter** skips cinematics. Text, results and save screens keep their normal controls.
- **Whistle**: tap B to recall idle Pikmin without interrupting workers; double-tap within 350 ms, or hold B for 0.6 s, to recall busy Pikmin in range.
- **Hold A** while plucking to continue to the next sprout.
- **F1 > Graphics** switches between Original and Enhanced (FXAA, 8x anisotropy, subtle bloom); Enhanced is the default for fresh settings.
- Pikmin attacking a Pellet Posy wait for it to die and carry the dropped pellet.
- A progress overlay shows current status, including whistle and movement percentages and each color's stats once its Onion is known.

Reward items: Ship Repair (30 in the pool, 25 required), Onion unlocks for the other colors, area access items, Flarlic (+10 field capacity each, up to 100), Pikmin Delivery (10 leaf Pikmin to the smallest unlocked Onion), Flower Shower (five drinkable nectar drops near Olimar), Progressive Whistle Radius (two +25% steps), Progressive Olimar Speed (two +25% steps to movement and plucking), Bomb Rock Delivery (three loose bombs near a landing Onion), the optional Bomb Ambush (five lit bombs around Olimar) and Smoky Progg Ambush traps, and per-color stat upgrades. Consumables wait for active gameplay outside pauses, menus, cutscenes and day-end.

Check categories: exploration (area access and Onion discovery), population milestones at 10/25/50/100 per color (field, stored and sprouts of that color), bestiary corpse deliveries to an Onion (Puffy Blowhog by defeat, Clamclamp by pearl; each species once), and with permanent checks the completion of individual walls, bridges and pushable boxes. Structure work uses each Pikmin's actual damage and attack rate, so stat upgrades speed it up.

Saving: at the end-of-day results screen choose to save, wait until the area map returns, then close the game. Relaunching the same `Play.cmd` continues at the next saved day; checks and received rewards are restored, consumables not present in the saved world are reapplied, and a day that was not saved rolls back. `session/campaign/` holds the saves; keep it with `session.json` and do not mix seeds.

## Known limitations

- Physical ship parts stay in vanilla positions.
- Mid-day squad positions are not saved; only day-end saves resume.
- Extinction recovery still needs gameplay acceptance.
- Enemy modes: native births, rendering and reachability are tested, but combat, larger enemy footprints (notably Bulbears and the Teki minibosses), corpse-return routes and revisit behavior need player acceptance. Terrain audits are samples, not proof of full footprint clearance.
- Structure and bestiary logic conservatively requires all three colors and area access; boxes also require field capacity 100. Logic can under-credit a strong specialized crew.
- Some starting combinations deliberately require remote progression in multiworld.
- Physical controller feel for held throws, D-pad held switching, whistle, multi-sprout plucking and bomb swapping remains open.
- The F8 tracker is a companion window, not a pause menu.
- Existing seeds and saves are not migrated to newer features; use a fresh seed for new options.
- Emperor Bulblax finale: the real fight and ending UI still need player acceptance; no ending cinematic is forced.

## Reporting problems

Open an issue at <https://github.com/4laric/pikmin-randomizer/issues>. Please include:

- the release version (ZIP and .apworld),
- the seed fingerprint (`python -m randomizer validate <seed.json>`) or the YAML options used,
- whether you played solo or Archipelago,
- the area and day, and the steps that led to the problem,
- `native.log` from the session's `runs/<token>/` directory for that launch.

## Developers

Seed logic, the session runner and the overlay live in `randomizer/`; the AP integration in `apworld/`; tests and packaging in `tests/` and `scripts/`. [DEVELOPMENT.md](DEVELOPMENT.md) records implementation details and historical validation (its `native/` paths refer to the maintainer's isolated checkout; use `engine/` in a public checkout), [SPEC.md](SPEC.md) and [BATCH_PLAN.md](BATCH_PLAN.md) hold the design and roadmap, [ENEMY_RANDOMIZER_ROADMAP.md](ENEMY_RANDOMIZER_ROADMAP.md) the enemy randomizer plan, and [CHANGELOG.md](CHANGELOG.md) the per-release notes including the Windows build instructions. `engine/` is the complete engine snapshot with licenses and provenance in [ENGINE_SOURCE.md](ENGINE_SOURCE.md).

## AI disclosure

Most of this project's code was written with LLM assistance (Codex and Claude), directed and reviewed by the maintainer. That is stated up front because this community has good reasons to be wary of AI-built worlds: the usual failure is a world nobody can debug because nobody understands it, and the usual cost falls on the people running the multiworld, not the author.

What is done about that:

- AI-written code is treated as broken until a test proves otherwise. The Python suite in `tests/` covers the apworld, the seed logic, DeathLink, traps, the launcher and the packaging, and the engine patches have their own C++ test harness. All of it runs before every release.
- The maintainer understands the codebase and is the one answering bug reports. Every feature has a GitHub issue with scope, acceptance criteria and validation notes, and the issue is closed only when the evidence is there.
- Everything is open. The code is CC0, the engine is Open Nectar (also CC0), and no game data is distributed. Audit, fork or replace any of it.
- Human playtime is still limited. Enemy modes, traps and DeathLink kills have engine-level testing but not many hours in real hands, which is why the current builds are an invited playtest and not a release.

If you would rather not play an AI-assisted world, that is a fair choice and [TheLynk's Dolphin Pikmin apworld](https://github.com/TheLynk/Archipelago) is a good one. If you do play, bug reports with the seed id and `native.log` get fixed quickly; see [Reporting problems](#reporting-problems).

## Credits

Built on [Open Nectar](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port) and the [projectPiki Pikmin decompilation](https://github.com/projectPiki/pikmin). Thanks to TheLynk for permission to use the Pikmin AP world's logic and locations as a reference; this remains a separate project as requested. This project's own code and documentation are public domain under [CC0 1.0](LICENSE); see [LEGAL.md](LEGAL.md). The engine keeps its own [license](engine/LICENSE.MD) and [third-party notice](engine/LEGAL.md).

### Setup and connection controls

After installation the launcher shows **Pikmin installed ✓**; **Change** reveals the source controls. The selected run shows whether it has recorded progress. **Continue solo** uses that same session; **New solo run** with a blank name creates a distinct seed. The displayed area describes the starting area, not a decoded native save location.

For AP, correct the server/password and use **Reconnect** to keep the current game and seed session alive. A refused login waits for correction. A different seed or slot manifest is still rejected. Password updates travel through a private process pipe and are not saved.

**Copy diagnostics** copies a small report of version, seed fingerprint, mode, setup readiness and recognized error categories/exit codes. It excludes passwords, server addresses, personal paths and raw logs. Nothing is uploaded automatically.

### Finding settings and understanding speed

Press **F1** while playing for game settings (graphics, audio and controls); **F8** opens the tracker. The launcher shows unusual starting-color stats before launch. In the bundled example seed, Red Pikmin start with 50% movement and 25% damage: those are randomized seed rules, not an overall game-speed setting. **New solo run** uses standard starting stats.
