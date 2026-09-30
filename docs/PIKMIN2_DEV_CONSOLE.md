# In-game dev console (#942)

Hand-test ported Pikmin 2 species without regenerating seeds: one Forest of Hope
session with the whole playable pool staged, then `spawn <id>` next to the captain.

## One-time content preparation (PowerShell)

```powershell
$env:PYTHONUTF8 = '1'
py -3.12 scripts/p2_dev_console.py --iso 'C:\Users\alari\Downloads\PIKMIN2 for GAMECUBE.iso' --prepare-only
```

Extracts every playable species into `output/p2-dev-content/` (reused by every
later launch; delete the directory to re-extract) and writes the dev seed to
`output/p2-dev-session/dev-seed.json`.

## Launch

```powershell
py -3.12 scripts/p2_dev_console.py --exe <path\to\nectar.exe> --assets C:\Users\alari\bbft\dist\cohesion\pikmin\assets
```

`--exe` must be a build that includes `pc_port/pc_dev_console.cpp` (native
branch `claude/dev-console`). Equivalent low-level form: `py -3.12 -m randomizer run
<seed> --p2-content <content> --p2-actors <actors.json> --dev-console ...`.

## In game

Press the backquote key (`` ` ``) to open the input line, type a command, press
Enter. Esc closes it; Up recalls the last line. Output appears on screen and in
`native.log` as `DEV_CONSOLE ...` lines. Headless: append lines to the script
file the launcher prints (`<session>/dev-console.txt`):

```powershell
Add-Content output\p2-dev-session\dev-console.txt 'spawn 41'
```

| Command | Effect |
|---|---|
| `spawn <id\|Enum\|Common_Name\|p1 teki name> [count] [norebind]` | Creates the species' P1 host next to the captain and binds it through the family's own path (same as a seed placement). Families without a per-actor binder re-run their stage setup (`rebind`) unless `norebind`. |
| `kill [all]` / `killall` | `die()` on the nearest (or every) live enemy: the corpse follows the natural family/P1 path and can be carried. |
| `pikmin <red\|yellow\|blue> [n]` | Adds n Pikmin to the squad (default 5). |
| `day <n>` / `time <hours\|0..1>` | World clock. |
| `tp <x> <z>` / `tp <arena_id>` / `pos` | Move the captain (arena ids from `randomizer/p2_boss_arenas.py`). |
| `list` | Species staged in this session (spawnable) and not staged. |
| `rebind` | Re-run every P2 family setup for the scene. |

## How it works

The dev seed binds each staged species to a synthetic *dev target uid*
`0xDE000000 + source_id` (`randomizer/dev_console.py`, mirrored by native
`pc_port/pc_dev_console_parser.h`). No real generator carries that uid, so
nothing spawns on its own; `spawn` creates a runtime `Generator` registered under
it, so `pc_p2_campaign_token()`, the family sidecars (`p2-*-actors.txt`,
`p2-*-teki.txt`) and the delivery receipts all see the same token a placed
actor would. The only placement rule bypassed is the compiled slot whitelist
(`p2campaign::accepted`), and only for dev uids while the console is enabled.

Gating: `PIKMIN_DEV_CONSOLE=1` only; the console refuses to enable when a
netplay switch (`--netplay-host/--netplay-join`, `PIKMIN_NETPLAY_HOST/JOIN`) is
present. With the variable unset no key is read and no line is logged.
