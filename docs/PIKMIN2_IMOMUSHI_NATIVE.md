# Imomushi (Ravenous Whiskerpillar, EnemyID 65) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#165](https://github.com/4laric/pikmin-randomizer/issues/165); source contract
[#346](https://github.com/4laric/pikmin-randomizer/issues/346). Fifth ground
species of the Species behavior lane. Owner: Codex via shared `4laric`.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/Imomushi.cpp` /
`ImomushiState.cpp` at decomp revision
`632af93787b9c95b63f0c13be32b161375ce3a96`. Retail parameters (GPVE01 rev 0):
life 200, move speed 40, territory 500, home radius 30, sight 500.

| Source behavior | Implementation |
|---|---|
| `Stay` (hidden) | frozen `set` frame 0; wakes when a Pikmin/Navi is inside the sight radius |
| `Appear` / `Dive` | `set` / `dive` surface-and-burrow cycle |
| `Move` / `GoHome` | `move1`/`move2` wander inside territory/home clamp |
| `Fall` / `Dead` | `fall1`/`fall2`/`dead`; `die()` at the dead clip end |
| Plant eating (`getRandFruitsPlant`/`startClimbPlant`/`eatTsuyukusa`) | **source-backed N/A** — the arena stages no fruit-bearing plants; never faked |

### Port adaptations (recorded, not retail-faithful)

- Wake uses sight of a Pikmin/Navi as the stand-in for plant availability, since
  no fruit plant is staged; the cycle is observable but the source plant-attract
  gate is not.
- `FallMove`/`FallDive` are entered on death so the banked fall/dead clips are
  exercised (the source Climb/Attack routes are plant-bound and N/A).
- Turn rate is a fixed ~π rad/s adaptation.

## Files

- `native/pc_port/pc_p2_imomushi.cpp`, `pc_p2_imomushi.h` (new).
- Additive hooks: `include/teki.h` (param chain), `tekibteki.cpp` (update),
  `tekimgr.cpp` (reset/forget), `pc_p2_batch2.cpp` (clip override + bind log),
  `pc_p2_preview.cpp` (setup), `CMakeLists.txt`.
- `experimental/pikmin2_imomushi_behavior.py`, `tests/test_pikmin2_imomushi_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Isolated executable SHA-256 | `8692057EFA06EDC900E16B8E25BF925A9C929F50C4FFF4E9A859355947D7860A` |
| Combined six-species exe | `AAF17C0D36BA0C86AB621C4924C5826FCF43883A25E5CA085B9F12A6D8003ADB` |
| Isolated run directory | `output/p2-species-imomushi/630abee40e074918a23cbb2e99b59a65` |
| Combined run directory | `output/p2-species-combined/4550a6a23d9b43a19d7701325e7b7026` |
| Hashes | isolated `native.log` `76213F0C…BD400C`; `imomushi-override.json` `5B0D56EB…9A603D`; combined `native.log` `C12A87E1…D1DA03` |

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_IMOMUSHI_BIND generator=346003 source_id=65`; `P2_BATCH2_BIND …ground|Imomushi visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | `P2_IMOMUSHI_HIDDEN hidden=1` → `state=appear` → `state=move`/`gohome`/`dive`/`stay`; 132.6 XZ spread (isolated), 14 samples |
| 3. Attacks / receivers | source-backed N/A | Imomushi's source attack is plant eating with no player-damage receiver; no fruit plants staged |
| 4. Death + corpse | UNTESTED | Fall/Dead implemented; no damage source in the unattended run |
| 5. Transport + reward | source-backed N/A / UNTESTED | plant-food delivery N/A; host corpse carry not exercised |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired; no teardown cycle |

## Remaining work

- Plant/tube eating and berry receiver require staged fruit flora.
- Death/corpse/transport/cleanup (lifecycle #397).
- Maintained `native/build-randomizer` rebuild and `scripts/export_native_source.py`
  stay integration-owned.
