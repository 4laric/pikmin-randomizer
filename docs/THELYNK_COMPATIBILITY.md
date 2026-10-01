# TheLynk APWorld compatibility (#1093)

Reference: [TheLynk/Archipelago `Apworld-Pikmin`](https://github.com/TheLynk/Archipelago/tree/24f4c1216e640b1b13ace84c330a1b627e3e3ea0/worlds/pikmin), commit `24f4c1216e640b1b13ace84c330a1b627e3e3ea0`, APWorld version 7. Implementation owner: Codex through shared GitHub account 4laric.

## Stable naming

`randomizer.compatibility` maps all 30 physical ship parts by native index and fourCC to their TheLynk item/location names and numeric IDs. Our existing names, IDs, manifests and fingerprints are unchanged. `part_identity()` resolves either naming convention; the two Ionium Jets map to `#1 Ionium Jet` / `#2 Ionium Jet`. Main Engine has no local location ID because our existing standalone catalog excludes that tutorial check.

Export the mapping without loading or changing a seed:

```powershell
py -3.12 -m randomizer naming-crosswalk --output output/thelynk-names.json
```

The output records the upstream source pin. It does not alias population checks: TheLynk's `Red Pikmin: 10` means ten followers in Olimar's squad; our `Population: 10 total Red Pikmin` includes Onion stock and sprouts.

## Universal Tracker

APWorld 0.32.0 supports generation without YAML through `interpret_slot_data`, `generate_early` and `re_gen_passthrough`. It restores the exact authoritative manifest, validates the existing fingerprint and uses the stored resolved start, enemy layouts, stats, check set and goal. Current option defaults and RNG do not regenerate these values. Solo, malformed and fingerprint-mismatched manifests are rejected. The manifest is copied so tracker reconstruction cannot mutate server data.

Item groups: Ship Repairs, Onions, Area Access, Color Upgrades, Benefits, Traps.
Location groups: Ship Parts, Onion Discovery, Population, Bestiary, Exploration, Structures.

Build a private package with `scripts/build_apworld.py --output output/pikmin_randomizer.apworld`. Do not relink a shared Archipelago installation.

## Experimental native TheLynk client

This is a separate client for TheLynk-generated `.appik1` files. It connects as `Pikmin`; our existing client still connects as `Pikmin Randomizer`. The native executable requires the new `PIKMIN_THELYNK` bootstrap and capability handshake. An older executable fails rather than accepting this seed as a local repair seed.

```powershell
py -3.12 -m randomizer.thelynk output/AP_Player.appik1 `
  --server archipelago.gg:PORT `
  --session-dir output/thelynk-session `
  --exe output/native-thelynk-build/bin/nectar.exe `
  --assets C:/Users/alari/AppData/Roaming/PikminRandomizer/game-data/assets
```

Set `PIKMIN_AP_PASSWORD` in the environment when the server requires a password. Use a separate session directory for every seed/slot. Neither the official Dolphin client nor an ISO patch is launched; the `.appik1` supplies metadata for the native adapter.

Supported behavior:

- All 30 ship-part checks, including Main Engine, use TheLynk location IDs.
- Physical checks never grant progression. Received named parts determine ship count, radar/jet effects, visuals, the 1/5/12/29 area unlock thresholds and thirty-part goal.
- Fresh Impact Site startup and ordinary Onion discovery are retained. Onion access is not replaced with randomized unlock items. Normal days cycle through 2–29, wrapping to 2, as in the upstream client.
- Optional per-color follower checks honor the upstream enabled colors and intervals. Workers, sprouts and Onion stock do not satisfy them.
- All 18 rewards of 1/5 Red/Yellow/Blue Leaf/Bud/Flower Pikmin add the matching persistent Onion stock, including before that color is discovered.
- Full item Sync and matching server version, seed/slot, options, check set and data-package IDs are required before starting the executable. Receipt conflicts, gaps and unique-part duplicates fail closed.
- Native checks are fsynced and recovered across runner crashes. Typed reward consumption is saved with the native day-end checkpoint; unsaved days roll back and replay their unsaved rewards. Room updates reconcile remotely checked locations.

The initial implementation requires these explicit TheLynk YAML settings:

```yaml
normal_first_day: false
disable_pikmin_trip: off
skip_events: []
always_min_one_leaf: false
day_cycle_mode: normal
ship_part_hint_mode: none
death_link: off
pikmin_bond: false
olimar_bond: false
trap_link: false
trap_percentage: 0
```

The upstream defaults for several of these differ. Existing seeds using those defaults are rejected before launch. Traps, Trip Immunity, linked effects, custom/fixed day cycles, minimum-leaf protection and cutscene/hint QoL need additional native support. Unexpected unsupported items, including plando traps, stop the client when received. This mode does not claim general compatibility with every TheLynk seed or future APWorld version.

## Validation and remaining acceptance

`tests/test_compatibility.py` covers crosswalk identities, tracker validation, server contracts, receipts, session isolation, journal recovery and a simulated AP connection. `scripts/test_thelynk_compatibility.py` loads the actual packaged world without installing it and checks twelve fills plus exact tracker manifests, locations and rules under empty, partial and full inventories. Its optional `--native-probe` exercises the compiled native adapter's check/reward separation, follower thresholds, all 18 bonus types, checkpoint consumption, area/goal boundaries and malformed state rejection.

Native builds are private and leased through the canonical workflow registry. Build pins, executable hashes, logs and Ninja dry runs live under `output/thelynk-build-*`. The first attempt used the default legacy audio configuration and failed linking an inherited missing `Jac_NoteDemoSkipped` symbol; it also failed source immutability and is not acceptance evidence. The subsequent attempt uses the maintained Release/Ninja/MinGW/JAudio configuration and a frozen native commit.

Compiled and protocol evidence does not establish full campaign gameplay acceptance. Real ship-part absorption/repair animations, tutorial exit, world-map refresh, pre-discovery typed stock, sunset extinction and full campaign save/re-entry still require a supervised native playtest and player sign-off. This experimental mode is delivered on the private native branch for integration review; it is not installed into the maintained executable or exported source.
