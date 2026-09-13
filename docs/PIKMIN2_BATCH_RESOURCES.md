# P2 batch sessions — assets and engine runbook

Every batch session reads this before starting. Paths are for this Windows checkout (`C:\Users\alari\pikmin-randomizer`). Batch mandates: [PIKMIN2_FAMILY_BATCHES.md](PIKMIN2_FAMILY_BATCHES.md). Live status: [PIKMIN2_FAMILY_STATUS.md](PIKMIN2_FAMILY_STATUS.md).

## 1. Game assets

| What | Path | Notes |
|---|---|---|
| Pikmin 2 disc (US GPVE01 rev 0) | `output/pikmin2-runtime/pikmin2-source-test.iso` | 1,000,762,688 bytes. Primary for all extraction. |
| Pikmin 2 disc (staged copy) | `assets/disc/PIKMIN2 for GAMECUBE.iso` | 995,557,376 bytes. Same region/revision. |
| Pikmin 1 extracted assets (to run the engine) | `C:\Users\alari\bbft\dist\cohesion\pikmin\assets` | Has `dataDir/stages/practice` and `dataDir/stages/chal0`. This is the `--assets` path for arenas and the room preview. |
| Decomp source (read-only) | `native/pikmin2-research` | `--source` argument for extraction modules (git rev-parse only). |

Never commit extracted assets, generated models, executables, saves or ISO content. Generated output stays under the ignored `output/` tree.

## 2. Build environment (shared, serialize this)

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
cmake --build native/build-randomizer --target pikmin_pc -j 6
cmake --build native/build-randomizer --target pikmin_pc -- -n   # expect: ninja: no work to do.
```

- `cmake` is `C:\Program Files\CMake\bin\cmake.exe`; the generator is Ninja (the Python-bundled `ninja.exe`). `g++`/`gcc` are under `C:\msys64\mingw64\bin`.
- Built executable: `native/build-randomizer/bin/nectar.exe` (with `SDL2.dll`, `libwinpthread-1.dll`). Add `native/build-randomizer/bin` to `PATH` when launching.
- **One `native/` build at a time.** Private per-family worktree builds are allowed in parallel; the shared checkout build is the serialized resource.

## 3. Extract assets from the disc (pipeline §2–3)

```powershell
python -m experimental.pikmin2_<family>_assets `
  --iso output/pikmin2-runtime/pikmin2-source-test.iso `
  --source native/pikmin2-research `
  --output output/p2-<family>-import/run1 --pose-limit 3
```

Writes `output/p2-<family>-import/run1/<Family>.json` (schema 1) plus per-species pose files. Existing-family examples: `pikmin2_aquatic_assets`, `pikmin2_flying_assets`, `pikmin2_snagret_assets`, `pikmin2_ground_inverts_assets`, `pikmin2_dweevil_assets`, `pikmin2_cannon_projectile_assets`, `pikmin2_waterwraith_assets`, `pikmin2_flora_assets`.

## 4. Install + stage a private arena (pipeline §4)

```powershell
# install: hash-bound poses/configs into a private run
python -m experimental.pikmin2_<family>_install --imported <import dir> --run <new run dir> --generators <id ...>
# arena: original P1 stage + engineered placements, calls install
python -m experimental.pikmin2_<family>_arena --assets "C:\Users\alari\bbft\dist\cohesion\pikmin\assets" --imported <import dir> --output <new output dir>
```

The arena writes a unique run directory containing `arena.json`, the configs, and `assets/dataDir/courses/pikmin2room/`. `--assets` must be the Pikmin 1 tree above.

## 5. Run the engine

Room-preview overlay (recommended; creates a fresh run dir):

```powershell
python scripts/preview_pikmin2_room.py --assets "C:\Users\alari\bbft\dist\cohesion\pikmin\assets" --exe "C:\Users\alari\pikmin-randomizer\native\build-randomizer\bin\nectar.exe"
```

Launch a prepared private run (this is the `--experimental-pikmin2-room` path; it rejects AP/BBFT session args):

```powershell
$env:PATH='C:\Users\alari\pikmin-randomizer\native\build-randomizer\bin;'+$env:PATH
& "C:\Users\alari\pikmin-randomizer\native\build-randomizer\bin\nectar.exe" --experimental-pikmin2-room
```

Private fixture build (only run an executable whose `provenance.json` status is `built`):

```powershell
py -3.12 scripts/build_pikmin2_fixture.py --source native --build native\build-randomizer `
  --fixture <fixture.cpp> --expected-native-head <40-char-head> --output <new private dir>
```

Reference: [PIKMIN2_ROOM_PREVIEW.md](PIKMIN2_ROOM_PREVIEW.md), [PIKMIN2_FIXTURE_BUILDS.md](PIKMIN2_FIXTURE_BUILDS.md), [PIKMIN2_ENEMY_ARENA.md](PIKMIN2_ENEMY_ARENA.md).

## 6. Serialized shared resources

- One maintained `native/` build at a time; one real-GL run/fixture at a time.
- Reserve a slot with the orchestrator (this session / `#186`) before building `native/` or launching a GL window. Private worktree builds/launches are separate.
- Never push native origin. Root source is exported with `py -3.12 scripts/export_native_source.py` and committed/pushed from the root repo only.

## 7. Tests

```powershell
python -m pytest tests/test_pikmin2_<family>_assets.py tests/test_pikmin2_<family>_install.py -q
```

Add new family-prefixed test files; keep the existing suites green.
