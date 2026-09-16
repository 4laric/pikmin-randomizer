# SnakeCrow (34) / SnakeWhole (70) snagret pair — native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#174](https://github.com/4laric/pikmin-randomizer/issues/174); source contract
[#351](https://github.com/4laric/pikmin-randomizer/issues/351). The shared-base
snagret pair of the Species behavior lane, implemented in one module. Owner:
Codex via shared `4laric`.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/` `SnakeCrow.cpp`/
`SnakeCrowState.cpp`, `SnakeWhole.cpp`/`SnakeWholeState.cpp` and the shared
`SnakeJointMgr`/`SnakeJoint` base; retail parameters and clip events in
`experimental/pikmin2_snagret_assets.py`. Host is the P1 Chappy placement vehicle
(`TEKI_Chappy`), generators `376001` (SnakeCrow) and `376002` (SnakeWhole).

| Source behavior | Implementation |
|---|---|
| Burrow `Stay` → `Appear1`/`Appear2` | emerge from the ground |
| `Wait` / `Walk` / `Home` | locomotion (SnakeWhole mobile; SnakeCrow stationary by source fp06=0) |
| Directional `Attack` (bite) | capture at the banked `hit` KEYEVENT_3 frame 34, one kill at the banked `waitact1` KEYEVENT_2 swallow |
| `Eat` | swallow then return |
| `Disappear` / `Dead` | re-burrow / `die()` |

### Port adaptations

- The shared `SnakeJointMgr` `bodyjnt3`–`bodyjnt8` spine matrices are not
  representable on the P1 host (flat translation-only body).
- The five-directional bite (`hit_near`/`hit`/`hit_far`/`hit_r`/`hit_l`) is
  approximated as the nearest target in the source attack sweep; the normal `hit`
  stem at the banked frame 34 is always played.
- Full-hemisphere detection; `appearNearByTarget` 120-unit emerge reposition not
  applied; walk speed clamped to a P1-host value; SnakeCrow `mWFGHealth` fp31
  override is N/A. Turn rate/flick radius are documented P1-host values.

## Files

- `native/pc_port/pc_p2_snakejoint.cpp`, `pc_p2_snakejoint.h` (new, shared).
- Additive hooks: `include/teki.h`, `tekibteki.cpp`, `tekimgr.cpp`,
  `pc_p2_batch3.cpp` (clip override + bind logs), `pc_p2_preview.cpp`,
  `CMakeLists.txt`.
- `experimental/pikmin2_snakejoint_behavior.py`, `tests/test_pikmin2_snakejoint_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Executable SHA-256 | combined `D1BFCAC21BBFC013BAFDEF09671F033B75710CCA06C17F4F7B7A1737785C9AF2` |
| Run directory | `output/p2-species-snakejoint-final/2214854899a44dcf9f12b8bf698986d4` |
| Hash | `native.log` `680D23AB…1B523C214` |

## Six arena gates (both species)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_SNAKEJOINT_BIND generator=376001/376002 source_id=34/70`; `P2_BATCH3_BIND key=snagret|SnakeCrow` / `snagret|SnakeWhole visual_only=0` |
| 2. Autonomous movement + animation | PASS | both `stay→appear→attack→eat`; SnakeWhole mobile (29.6 XZ spread); SnakeCrow stationary by source |
| 3. Attacks / receivers | PASS | bites at frame 34 with exactly-once `P2_SNAKEJOINT_EAT` per bite for both species |
| 4. Death + corpse | UNTESTED | `Dead` coded; no damage source |
| 5. Transport + reward | source-backed generic | host corpse/carry retained |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired; `disappear→stay` re-burrow loop observed |

## Remaining work

- Shared joint/spine matrices, five-way directional bite, emerge reposition,
  `mWFGHealth`, falling Rock/Egg spawner.
- Death/corpse/cleanup (#397).
