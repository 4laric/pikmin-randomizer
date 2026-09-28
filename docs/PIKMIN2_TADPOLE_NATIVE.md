# Tadpole (Wogpole, EnemyID 27) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#167](https://github.com/4laric/pikmin-randomizer/issues/167); source contract
[#347](https://github.com/4laric/pikmin-randomizer/issues/347). First aquatic
species of the Species behavior lane. Owner: Codex via shared `4laric`.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/Tadpole.cpp` /
`TadpoleState.cpp` at decomp revision
`632af93787b9c95b63f0c13be32b161375ce3a96`; retail parameters in
`experimental/pikmin2_aquatic_assets.py`. Host is the P1 Wogpole (`TEKI_Otama`),
generator `374002`.

| Source behavior | Implementation |
|---|---|
| `Wait` / `Move` | `wait1`/`move1` wander with source speed |
| `Amaze` / `Escape` | `waitact1` reaction when a Pikmin/Navi comes near |
| `Leap` | `piti1` vertical hop (dry-land fallback; see adaptations) |
| `Dead` | `dead`; `die()` at clip end |
| Attack / receivers | **source-backed N/A** — Tadpole is harmless (fp24=0); no attack interaction is raised |

### Port adaptations (recorded, not retail-faithful)

- The P1 host has no water box, so the source water-leap gate is deferred to each
  state's animation/timer end; the hop is a labelled port value.
- Target detection accepts the nearest Navi/Pikmin (source Wait/Move use the
  nearest Navi only); view angle is a full hemisphere; turn rate is a port value.
- The source `Amaze` panic flick is deliberately omitted because it is a
  non-damaging shake and attacks/receivers are N/A.

## Files

- `native/pc_port/pc_p2_tadpole.cpp`, `pc_p2_tadpole.h` (new).
- Additive hooks: `include/teki.h` (param chain), `tekibteki.cpp` (update),
  `tekimgr.cpp` (reset/forget), `pc_p2_batch3.cpp` (clip override + bind log),
  `pc_p2_preview.cpp` (setup), `CMakeLists.txt`.
- `experimental/pikmin2_tadpole_behavior.py`, `tests/test_pikmin2_tadpole_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Combined six+two exe SHA-256 | `C7D553523E4DFB231DAD9CAE8B65D460DE5B1F0481D76B60D8184834FC388977` |
| Isolated aquatic exe SHA-256 | `7CFFE31157998FE5A142D2AD71FB07E2018A380195D9C8D25A1E97A0992C4B4F` |
| Run directory | `output/p2-species-tadpole/a012de6d5b9549a79224fd37a11ade21` |
| Hash | `native.log` `2964A6DE…B0D3F2` |

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_TADPOLE_BIND generator=374002 source_id=27`; `P2_BATCH3_BIND …key=aquatic|Tadpole visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | states `wait/move/amaze/escape/leap`; clips `wait1/move1/waitact1/piti1`; 77.6 XZ spread |
| 3. Attacks / receivers | source-backed N/A | fp24=0 and all attack params zeroed; no attack raised |
| 4. Death + corpse | UNTESTED | `Dead` coded; no damage source in the run |
| 5. Transport + reward | N/A | no verified source loot drop |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired; no teardown exercised |

## Remaining work

- True `MoveWater`/nest behavior and group birth.
- Death/corpse/cleanup (#397).
- Maintained `native/build-randomizer` rebuild and `scripts/export_native_source.py`
  stay integration-owned.
