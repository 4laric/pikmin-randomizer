# Lane 13 - Dwarf Orange Bulborb (BlueKochappy 44) process-restart gate F

Fan-out lane 13 (`#120`/`#186`). This doc records the **gate F persistence**
slice for the native Dwarf Orange Bulborb candidate: identity/content stability
across an independent process restart. It closes the `UNTESTED` gate F row in
`docs/PIKMIN2_DWARF_ORANGE_NATIVE.md`.

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: opencode. Branch `opencode/p2-lane13-restart`, base `ef34e84`.

## 1. Scope

Gate F here is **identity/content persistence across process restart**. The same
instrumented fixture executable is launched as **two independent, strictly
sequential processes** inside a private copy of the two-actor arena. Both
processes must publish the identical BlueKochappy 44 identity, the identical
64-pose bank marker, and the identical `P2_DWARF_ORANGE_ARENA_BIRTH` health/XYZ
for generators `211001` (source) and `211002` (P1 Chappy control).

Reward duplication/loss is **not applicable** to this slice: there is no P2
Pod/reward binding in the Dwarf Orange candidate, so there is no once-credit
receipt to duplicate or lose across restart. P2 reward/once-credit is lane 06
(`docs/PIKMIN2_IMPLEMENTATION_FANOUT.md`, lane 06).

## 2. Method

`experimental/pikmin2_dwarf_orange_restart.py`:

- `copy_arena(source, dest)` copies the arena to a private directory; the
  original is never mutated.
- Both runs launch `--experimental-pikmin2-room` with
  `PIKMIN_P2_ROOM_WINDOW=960x540`, each with its own `native.log`/`capture.json`
  output directory.
- The two launches are **one serialized session** (`serialized()` holds an
  advisory GL lock; `SessionBusy` refuses a concurrent start) and exactly
  `MAX_RUNS = 2` processes are started.
- `markers()` / `compare()` parse and compare the requested identity/content
  markers; the bank `load_seconds` field is treated as volatile and excluded.
- `snapshot()` / `save_delta()` / `session_dirs()` record any save-tree change.

Reproduction:

```powershell
$env:PIKMIN2_RUNTIME_BIN='C:\msys64\mingw64\bin'   # libgcc/libstdc++/SDL2
py -3.12 -m experimental.pikmin2_dwarf_orange_restart run `
  --arena <arena.sha-dir> `
  --exe C:\Users\alari\pikmin-randomizer\output\p2-lane13-orange-fixture2\baseline\fixture.exe `
  --output output\p2-lane13-dwarf-orange-restart
```

## 3. Evidence

- Driver: `experimental/pikmin2_dwarf_orange_restart.py`.
- Report: `output/p2-lane13-dwarf-orange-restart/restart.json`.
- Run 1 log: `output/p2-lane13-dwarf-orange-restart/run1/native.log`.
- Run 2 log: `output/p2-lane13-dwarf-orange-restart/run2/native.log`.
- Arena copy (private, source untouched):
  `output/p2-lane13-dwarf-orange-restart/arena` (copied from
  `output/p2-lane13-orange-arena2/bd2b9fff954a474b88a7f6e467314cfc`).
- Fixture SHA-256 `AFBD26F1DFD42D312B1B4036E8F2CECB3B8668553A12FC2E03937E78DE0B4FC6`.
- Exit codes: run 1 `0` (11.1 s), run 2 `0` (10.3 s); both `960x540`; no
  extinction; both `DONE P2_DWARF_ORANGE_COMBAT`.

Compared marker sets (all `identical=true`):

| Marker | Run 1 | Run 2 | Match |
|---|---|---|---|
| `P2_ENEMY_READY species=BlueKochappy source_id=44 ... health=250.0 max_health=250.0` | exact line | exact line | yes |
| `P2_DWARF_ORANGE_BANK poses=64` | `poses=64 ... load_seconds=0.005` | `poses=64 ... load_seconds=0.012` | yes (`poses`/content; timing volatile) |
| `P2_DWARF_ORANGE_ARENA_BIRTH` 211001 health/XYZ | `x=-150.000 y=30.000 z=1850.000 health=250.0` | same | yes |
| `P2_DWARF_ORANGE_ARENA_BIRTH` 211002 health/XYZ | `x=150.000 y=30.000 z=1550.000 health=130.0` | same | yes |

Exact compared lines:

```text
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0 max_health=250.0 behavior=P1 purple_stun=bluekochappy_5s
P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000 texture_attach_calls=1 load_seconds=<volatile>
P2_DWARF_ORANGE_ARENA_BIRTH id=211001 x=-150.000 y=30.000 z=1850.000 health=250.0 fallback=130.0 red=1
P2_DWARF_ORANGE_ARENA_BIRTH id=211002 x=150.000 y=30.000 z=1550.000 health=130.0 fallback=130.0 red=0
```

## 4. Save/state observation

- Save-tree content: **unchanged**. `assets/dataDir/savedata/test.card` has the
  same SHA-256 before run 1, after run 1 and after run 2; no save file was
  added, removed or modified.
- Each process created one new empty session scaffolding directory under
  `save/bbft_sessions/` (added `1789394596649116800` after run 1,
  `1789394607712865500` after run 2, each containing empty `card0`/`card1`
  directories). There are no regular files in any session directory, so no game
  save data changed. This is launch session scaffolding, not persistent progress.
- Screenshot `.ppm` artifacts are regenerated in the arena copy by the observer;
  they are run output, not save state.

## 5. Gate table (this slice)

| Gate | Status | Evidence |
|---|---|---|
| A Identity/content | PASS (candidate) | `P2_ENEMY_READY source_id=44`, birth XYZ, 64-pose bank |
| B Source behavior | PARTIAL | host P1 AI; source health 250 / 5 s stun; see native doc |
| C Combat/receivers | PASS at P1-proxy level | native doc |
| D Death/drop/transport | PASS at P1-proxy level | native doc |
| E Lifetime | BLOCKED | manager-swap precondition (#397) |
| **F Persistence (process restart)** | **PASS** | this doc; `restart.json`; run 1 == run 2 |
| G Product/mixed scene | BLOCKED | candidate not integrated |

Gate F is PASS for this slice only. It does **not** claim reward once-credit,
campaign/day resume, or a generated-session restart; P2 reward persistence is
lane 06.

## 6. Limits

- Deterministic room-preview fixture: each process rebuilds actors from the same
  arena assets, so identity/content is expected to be stable. This proves
  restart-stable identity/content and unchanged save files, not durable
  progress serialization.
- No P2 Pod/reward in this slice, so reward duplication/loss is not applicable.
- Manager recreation / full scene teardown remain gate E and are out of scope.

## 7. Tests

- `tests/test_pikmin2_dwarf_orange_restart.py` - pure marker parsing,
  cross-run comparison (including volatile bank timing, changed health/XYZ,
  missing birth), content checks, save-delta/snapshot/session-dir logic,
  private arena copy (source intact, overlap refused), GL lock exclusivity,
  runtime `PATH` handling and the `MAX_RUNS = 2` bound.
