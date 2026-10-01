# Mar (Puffy Blowhog, EnemyID 29) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#166](https://github.com/4laric/pikmin-randomizer/issues/166); source contract
[#348](https://github.com/4laric/pikmin-randomizer/issues/348). First flying
species of the Species behavior lane. Owner: Codex via shared `4laric`.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/Mar.cpp` / `MarState.cpp` at
decomp revision `632af93787b9c95b63f0c13be32b161375ce3a96`; retail parameters in
`experimental/pikmin2_flying_assets.py`. Host is the P1 Puffy Blowhog
(`TEKI_Mar`), generator `375001`.

| Source behavior | Implementation |
|---|---|
| `Wait` / `Move` / `Chase` | host wander/chase with source speed/territory |
| `Attack` (wind) | `attack` clip; a single blow at the source attack event frame |
| `Dead` | `dead`; `die()` at clip end |
| `Fall`/`Land`/`Ground`/`TakeOff`/`FlyFlick`/`GroundFlick` | bounded gaps (stuck-Pikmin/mouth system dependent) |

### Port adaptations (recorded, not retail-faithful)

- The P1 engine has no `InteractWind`; the source wind (`Mar.cpp::windTarget`) is
  resolved as one `InteractFlick` blow/stagger on eligible non-Purple living
  Pikmin at the attack event frame, not every update. Purple is excluded
  (`mP2Purple`); invincible/KokeDamage exclusions are not representable.
- fp23 is absent from the extracted retail block, so a 45° half-angle is a
  labelled port value; turn rate is a port value.
- `ChaseInside` is folded into Chase/territory containment.

## Files

- `native/pc_port/pc_p2_mar.cpp`, `pc_p2_mar.h` (new).
- Additive hooks: `include/teki.h` (param chain), `tekibteki.cpp` (update),
  `tekimgr.cpp` (reset/forget), `pc_p2_batch3.cpp` (clip override + bind log),
  `pc_p2_preview.cpp` (setup), `CMakeLists.txt`.
- `experimental/pikmin2_mar_behavior.py`, `tests/test_pikmin2_mar_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Combined six+two exe SHA-256 | `C7D553523E4DFB231DAD9CAE8B65D460DE5B1F0481D76B60D8184834FC388977` |
| Isolated flying exe SHA-256 | `9204FD8825356DE8998A4565CCB6AD2546246B3DE34746F8C3203CBC012D6632` |
| Run directory | `output/p2-species-mar-combined/946397288af64d0a91cf719067b038fe` |
| Hash | `native.log` `12D21761…A0D4E50E` |

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_MAR_BIND generator=375001 source_id=29`; `P2_BATCH3_BIND …key=flying|Mar visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | `P2_MAR_STATE wait/chase/attack` cycles; `P2_MAR_POS` with clip phases; 112.7 XZ spread |
| 3. Attacks / receivers | PASS (bounded) | `P2_MAR_BLOW generator=375001 pikmin=20/20/2` at the source attack frame; Purple excluded |
| 4. Death + corpse | UNTESTED | `Dead`/corpse path implemented; fixture squad cannot damage the host |
| 5. Transport + reward | N/A | Mar has no P2 carry/reward |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired; no teardown exercised |

## Remaining work

- Full P2 wind cone/effect bank, stuck-Pikmin fall/flick states, death/cleanup (#397).
- Maintained `native/build-randomizer` rebuild and `scripts/export_native_source.py`
  stay integration-owned.
