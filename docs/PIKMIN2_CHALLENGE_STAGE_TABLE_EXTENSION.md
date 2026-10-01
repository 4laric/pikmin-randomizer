# P2 challenge stage extension table: LeafChappy + 02tile (#730)

Lane challenge-stage-table-extension-native, parent #569. Shared producer for
the stopped consumers `p2-challenge-ch-abem-leafchappy-p1` (#550) and
`p2-challenge-ch-nari-02tile-p1` (#537): the engine `kP2ChallengeStages` table
(`pc_port/pc_bbft.cpp`, lane #675) holds only `ch_NARI_01kusachi`, so neither
LeafChappy nor 02tile can resolve and no live stage-table owner exists.

## Scope and boundary

New files only (listed below); **no edits** to `pc_bbft.cpp`, `CMakeLists.txt`
or any shared/family module. Wiring the extension into the engine lookup is
the serialized one-line `pc_bbft.cpp` integration owned by READY #728, plus
`CMakeLists.txt` membership for the fixture TU; both are specified below as
follow-on and require #186 review before landing. No ADMIT, no gameplay claim.

## Pinned rows (source: lane plan + family issues, read-only)

`docs/PIKMIN2_CONTENT_IMPORT_LANES.json` entries `p2-challenge-ch_abem_leafchappy`
(issue #550) and `p2-challenge-ch_nari_02tile` (issue #537):

| Field | ch_ABEM_LeafChappy (#550) | ch_NARI_02tile (#537) |
|---|---|---|
| cave path | user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt | user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt |
| sha256 | 49cc9076...2baf | d047060c...79ea |
| ui_index / table_order / floors | 17 / 4 / 2 | 4 / 19 / 2 |
| floor_seconds | 85.0, 100.0 | 200.0, 150.0 |
| roster (7x3) | 10/10/10 leaf (=30) | 50 leaf row 0 |
| bitter / spicy | 1 / 1 | 0 / 5 |
| legacy_time / treasure | 400.0 / 11 | 0.0 / 0 |

## Owned files (this slice only)

Native (`output/.../challenge-stage-table-extension-native-native`):
- `pc_port/pc_p2_challenge_stages_ext.{h,cpp}` — 2 pinned rows + lookup;
  kusachi never resolves here (engine owns it).
- `tools/p2_challenge_stage_table_ext_fixture.cpp` — guarded replacement-main
  fixture (unity-includes the ext TU, so no CMake edit).
  Readiness is 600 guarded live ticks with a live squad recorded
  (a preview treasure is not staged, so `pc_p2_preview_ready()` is not
  the gate); the window check accepts centered-on-any-display to stay
  robust to SDL display-index attribution on scaled setups.

Root (`output/.../challenge-stage-table-extension-native-root`):
- `scripts/build_p2_challenge_stage_table_ext.py` — stage + build + run + validate.
- `docs/PIKMIN2_CHALLENGE_STAGE_TABLE_EXTENSION.md` — this file.
- `experimental/pikmin2_challenge_stage_table_extension.py` — pins + log validator.
- `tests/test_pikmin2_challenge_stage_table_extension.py` — 11 tests.

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_challenge_stage_table_extension.py -q`
  -> 11 passed (pin identity vs lane plan, validator good/bad paths, strict
  MinGW `-Wall -Wextra -Werror` compile-and-run of the ext table).
- Fixture run proves both rows resolve with pins intact, kusachi resolves via
  the untouched engine table only, the engine refuses both new keys, unknown
  keys are refused, and the window is 960x540 centered (see run evidence).

## Serialized follow-on (blocked on #728, needs #186 review)

1. `pc_port/pc_bbft.cpp`: one-line fallthrough in `pc_p2_challenge_stage_lookup`
   to `pc_p2_challenge_stages_ext_lookup` when the engine table misses.
2. `CMakeLists.txt`: `pikmin_pc` membership for `pc_p2_challenge_stages_ext.cpp`
   (or keep it fixture-unity-included; integrator decides).
3. Downstream consumers #550 + #537 observe once landed. No ADMIT requested.

## Remaining work

- Integrator disposition + #186 review of the follow-on above.
- Captain safety #632 adopted in the fixture (vendored guard sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
  called before pause/movie returns); six gates UNTESTED by design.
