# P2 seed quickstart: one command to play

`scripts/p2_play.py` turns the manual three-step flow (generate -> prepare
content + actors -> run) into one command for both solo and Archipelago seeds.
It reuses `scripts/p2_prepare_content.py` for ISO extraction (it does not
duplicate it), caches the content root per retail-ISO sha256, writes the seed's
actor bindings, picks a short session directory, and runs `randomizer run`.

Generated content lives under `output/` (gitignored) and the session under
`C:/p2play/`; nothing extracted from the ISO is ever committed.

## Prerequisites

- Python 3.12 (`py -3.12`) and the repo checkout.
- P2 retail ISO, default
  `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`.
- Extracted P1 assets containing `dataDir/stages/`, default
  `C:/Users/alari/bbft/dist/cohesion/pikmin/assets`.
- Optional native executable (`--exe`, e.g. a built `nectar.exe`). Omit it to
  stage a session only.
- For AP: a local Archipelago install, default `C:/Users/alari/Archipelago`,
  and a player YAML with the Pikmin Randomizer world enabled.

## Solo

Preview every step and path without generating, extracting or launching:

```powershell
py -3.12 scripts/p2_play.py --seed demo --dry-run
```

Stage a playable-pool session (writes `p2-binding-receipt.json` once the
identity-keyed content is installed, then stops):

```powershell
py -3.12 scripts/p2_play.py --seed demo
```

Launch the game with a native executable:

```powershell
py -3.12 scripts/p2_play.py --seed demo --exe C:/path/to/nectar.exe
```

`--pool all` prepares every admitted species instead of the playable pool
(44 BlueKochappy, 54 Mamuta, 59-62 Otakar). `--session-dir` overrides the
default `C:/p2play/<seed>-<n>`.

## Archipelago

Build the packaged world from `scripts/build_apworld.py`, install it into the
Archipelago `custom_worlds/`, generate the room from your YAML with
`Generate.py`, and stage the resulting player manifest:

```powershell
py -3.12 scripts/p2_play.py --apworld-yaml C:/path/to/player.yaml --server localhost:38281 --exe C:/path/to/nectar.exe
```

`--server host:port` is required for AP mode; it is passed through to
`randomizer run --server`. The `.apworld` is built with
`scripts/build_apworld.py`, copied to
`<ap-root>/custom_worlds/pikmin_randomizer.apworld`, and the YAML is generated
through `<ap-root>/Generate.py --player_files_path <work>/players
--outputpath <work>/ap-output`. The single `*.pikmin.json` that
`PikminRandomizerWorld.generate_output` writes becomes the seed manifest.

## Options

| Flag | Meaning |
|---|---|
| `--seed <text>` | Solo seed (mutually exclusive with `--apworld-yaml`). |
| `--apworld-yaml <yaml>` | AP player YAML; requires `--server`. |
| `--server host:port` | AP server; also passed to `randomizer run`. |
| `--pool playable\|all` | Species pool to prepare (default `playable`). |
| `--iso <iso>` | Retail P2 ISO (default above). |
| `--assets <dir>` | P1 assets root with `dataDir/stages/` (default above). |
| `--exe <exe>` | Native executable; omit to stage only. |
| `--session-dir <dir>` | Session directory (default `C:/p2play/<name>-<n>`). |
| `--work-dir <dir>` | Manifest/actors/AP output location. |
| `--cache-dir <dir>` | Content cache namespace (default `output/p2-play-cache`). |
| `--ap-root <dir>` | Local Archipelago install (default above). |
| `--pose-limit <2-8>` | Sampled poses per clip for the family banks. |
| `--stage-timeout <s>` | Seconds to wait for the binding receipt when staging. |
| `--dry-run` | Print every step and path; do nothing. |

## Cache and path rules

- The content root is keyed by the retail ISO sha256 and reused on the next
  run (`content (cached)`); delete `--cache-dir` to force re-extraction.
- Any run path over 200 characters is refused (`PlayPathError`), because
  Windows' 260-character limit makes deep `.mod` loads fail.
- The child process gets `C:/msys64/mingw64/bin` prepended to `PATH`.

## Runtime safety

Staging a session does not launch the game. When you pass `--exe`, a real
native run starts: follow the mandatory captain-safety policy in
`docs/PIKMIN2_IMPLEMENTATION_FANOUT.md` §"Mandatory captain safety (#632)" and
park the captain outside attack reach when captain hits are not the test.
