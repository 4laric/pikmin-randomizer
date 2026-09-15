# DangoMushi (Segmented Crawbster, EnemyID 94) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#174](https://github.com/4laric/pikmin-randomizer/issues/174); source contract
[#351](https://github.com/4laric/pikmin-randomizer/issues/351). First
snagret/crawbster-family species of the Species behavior lane. Owner: Codex via
shared `4laric`.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/DangoMushi.cpp` /
`DangoMushiState.cpp`; retail parameters, state IDs and clip events in
`experimental/pikmin2_snagret_assets.py`. Host is the P1 Chappy placement vehicle
(`TEKI_Chappy`), generator `376003`.

| Source behavior | Implementation |
|---|---|
| `Stay` / `Appear` (fly) | emerge from the ground |
| `Wait` / `Move` | `move` wander with source speed and territory/home clamp |
| `Attack` (ball roll) | `attack` clip; roll starts at the banked `attack` KEYEVENT_4 frame (23) and steers at the target at the source roll speed |
| Roll contact | one `InteractFlick` knockback+damage on the first Pikmin/Navi inside the source fp22=100 hit radius, once per roll |
| `Turn` / `Recover` / `Flick` | crash turn, facing flip, and the `attack_2` arm sweep |
| `Dead` | `dead`; `die()` at clip end |

### Port adaptations

- The source `Obj::collisionCallback` `InteractPress` while rolling has no P1
  collision-callback path; the roll contact is a single `InteractFlick` at the
  first receiver inside the source hit radius.
- The source enters `Turn` only from `wallCallback` (roll speed > 100 into a
  wall); the P1 host exposes no wall normal, so `Turn` triggers on leaving the
  source fp09=150 territory or on the bounded roll timeout.
- Roll activation uses the source fp20=300 attack range without the narrow
  fp21=15° cone, because the P1 host has no wall-route roll and wandering rarely
  aligns the cone; the roll then steers at the target.
- Turn LOOP_START invulnerability is now applied through
  `pc_p2_dangomushi_invulnerable` (wired into `InteractAttack`/`InteractBomb`),
  and the Rock/Egg hazard decisions now birth real children by hosting the
  lane-20 `P2RockHazard` / `P2Egg` policies (see
  [the vulnerability-window and birth slice](PIKMIN2_DANGOMUSHI_VULN_APPLY.md));
  only the `dangomushi.brk` material loop is not reproduced.

## Files

- `native/pc_port/pc_p2_dangomushi.cpp`, `pc_p2_dangomushi.h` (new).
- Additive hooks: `include/teki.h`, `tekibteki.cpp`, `tekimgr.cpp`,
  `pc_p2_batch3.cpp` (clip override + bind log), `pc_p2_preview.cpp`,
  `CMakeLists.txt`.
- `experimental/pikmin2_dangomushi_behavior.py`, `tests/test_pikmin2_dangomushi_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Executable SHA-256 | combined `EE89B97D2A08FF90BCEBC85D07831AF473A0F14AD8309014662105D29642657C` |
| Run directory | `output/p2-species-dangomushi-fix1/da17ac0f3d2d4a118a8d66de31ee47d6` |
| Hash | `native.log` `D9D7B450…B7BB48` |

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_DANGOMUSHI_BIND generator=376003 source_id=94`; `P2_BATCH3_BIND …key=snagret|DangoMushi visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | states `stay/appear/wait/move/attack/turn/flick`; 228.3 XZ spread |
| 3. Attacks / receivers | PASS | `P2_DANGOMUSHI_ROLL frame=23.0` at the source KEYEVENT_4; one `P2_DANGOMUSHI_HIT` inside the roll window |
| 4. Death + corpse | UNTESTED | `Dead` coded; no damage source in the run |
| 5. Transport + reward | source-backed generic | host corpse/carry retained |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired |

## Remaining work

- `.brk` material loop, true `InteractPress` roll crush and `wallCallback` crash
  trigger. The Turn invulnerability window and the real Rock/Egg births are
  implemented in [the vulnerability-window and birth slice](PIKMIN2_DANGOMUSHI_VULN_APPLY.md).
- Death/corpse/cleanup (#397).
