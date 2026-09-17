# ch_NARI_02tile stage-boot record acceptance (issue #711)

Lane `challenge-stage-boot-02tile-record-native`. Owner: Codex through shared
account 4laric. Root-only docs plus one native TU (`native/tools/p2_challenge_stage_boot_fixture.cpp`).

## Why

`p2-challenge-ch-nari-02tile-p1` (#537, blocked gen 3) verified the #705
selector resolves `ch_NARI_02tile` (ui_index 4, kusachi preserved, unknown
keys refused) but the staged boot exited 1 with `reason=bad-record`. Root
cause: the #675 fixture `readRecord()` hardcoded
`sourcePath != "user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt"` and
refused every other record.

## Change (minimal, fixture only)

`native/tools/p2_challenge_stage_boot_fixture.cpp`:

- Added a pinned allowlist `kP2PinnedSources` of (cave_id, source path,
  source sha256) triples: kusachi and 02tile.
- `readRecord()` now accepts a record only when its `(cave, sourcePath,
  sourceSha)` matches a pinned triple; every other/mismatched record is still
  refused fail-closed. Kusachi acceptance is unchanged.
- When the record is accepted but the engine table row is not yet serialized
  (#710 follow-on), the fixture emits `P2_CHALLENGE_STAGE_RESOLVED ... engine_row=pending`,
  then `P2_CHALLENGE_STAGE_ENGINE_ROW_PENDING ... follow_on=710`, then
  `P2_CHALLENGE_STAGE_BLOCKED reason=engine-table-row-pending`, and exits 3.
  It never reaches READY/PASS. Exit 3 is distinct from guard 86 and refusal 1.

## Pinned 02tile record (from #537 staged pins)

| field | value |
|---|---|
| cave_id | `ch_NARI_02tile` |
| source | `user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt` |
| source sha256 | `d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6` |
| ui_index / table_order | 4 / 19 |
| floors / seconds | 2 / [200.0, 150.0] |
| sprays bitter/spicy | 0 / 5 |
| roster | total 50 at cell [0][2] |

Kusachi pin (preserved): sha `b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85`,
ui 3, 1 floor [180.0].

## Compiled evidence (leased private build)

- Lease token `cb4ba10a...` on `build:...\output\challenge-stage-boot-02tile-record-build`
  (elastic cap read live; private dir, not `native/build-randomizer`).
- `pikmin_pc` builds and links (`bin/nectar.exe`); `ninja -n pikmin_pc` ->
  "no work to do." (see `out/ninja-fresh.log`).
- Fixture: `output/.../out/fixture-build/fixture.exe`, sha256
  `d28599edea31d3f6fde026df3210cf87c7becf2ff95b779f5d74d40adb32d242`.
- Runs (`out/stage-runs.json`, `out/native-*.log`):
  - `ch_NARI_01kusachi`: exit 0, markers FLAG/SIDECAR/TABLE/RESOLVED/READY and
    `PASS CHALLENGE_STAGE_BOOT` (kusachi preserved).
  - `ch_NARI_02tile`: exit 3, markers FLAG/SIDECAR/RESOLVED/ENGINE_ROW_PENDING/
    BLOCKED; **no `bad-record`**, no `P2_CHALLENGE_STAGE_REFUSED`, no PASS.
- Captain safety #632: guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
  (vendored in the fixture, consumed read-only). Guard first-after-idle; a
  guard trip exits BLOCKED/86. No guard provider created.

Consumed prerequisite: #704 `Jac_NoteDemoSkipped` stub (cherry-pick
`f4ad1748`), required to link `pikmin_pc`; still owned by #704.

## Engine table-row follow-on (specified, NOT implemented; blocked on #710)

`challenge-hostmode-engine-hook-native` (#710) owns `native/pc_port/pc_bbft.cpp`.
Append to `kP2ChallengeStages` after #710 lands:

```cpp
{ "ch_NARI_02tile",
  "user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt",
  "d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6",
  4, 19, 2,
  { 200.0f, 150.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f },
  { {0,0,50}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },
  0, 5, 0.0f, 0 },
```

Then the #675 fixture's engine-table path resolves 02tile and full boot can be
attempted. `engine_table_row_followon()` in the experimental module carries the
same content machine-readably.

## Downstream

`p2-challenge-ch-nari-02tile-p1` (#537). All six runtime gates UNTESTED. No
ADMIT, no shared-line landing, no #710 edits.
