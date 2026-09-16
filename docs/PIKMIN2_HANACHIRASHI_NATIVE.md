# Hanachirashi (Withering Blowhog, EnemyID 55) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#166](https://github.com/4laric/pikmin-randomizer/issues/166); source contract
[#348](https://github.com/4laric/pikmin-randomizer/issues/348). Second flying
species of the Species behavior lane (after [Mar](PIKMIN2_MAR_NATIVE.md)).
Owner: Codex via shared `4laric`.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/Hanachirashi.cpp` /
`HanachirashiState.cpp`; retail parameters in
`experimental/pikmin2_flying_assets.py`. Host is the P1 Puffy Blowhog
(`TEKI_Mar`), generator `375002`.

| Source behavior | Implementation |
|---|---|
| `Wait` / `Move` / `Chase` | host wander/chase with source speed/territory |
| `Attack` (withering wind) | `attack` clip; one withering blow at the source attack event frame |
| `Laugh` | selected on a successful wind hit (source END transition) |
| `Dead` | `dead`; `die()` at clip end |
| Fly/Land/Ground/TakeOff/FlyFlick/GroundFlick | bounded gaps (stuck-Pikmin dependent) |

### Port adaptations

- No `InteractWind`/`InteractHanaChirashi`; the withering wind is a single
  `InteractFlick` blow/stagger on eligible non-Purple Pikmin at the attack event
  frame, not every active frame. Purple in the cone strips bud/flower → Leaf but
  is not blown (UNTESTED, fixture squad is Red only); invincible/KokeDamage
  exclusions are not representable.
- The 3D wither vector is replaced by a scalar `InteractFlick` impulse; the cone
  half-angle is a labelled port value (fp23 absent from the extracted block).

## Files

- `native/pc_port/pc_p2_hanachirashi.cpp`, `pc_p2_hanachirashi.h` (new).
- Additive hooks: `include/teki.h`, `tekibteki.cpp`, `tekimgr.cpp`,
  `pc_p2_batch3.cpp` (clip override + bind log), `pc_p2_preview.cpp`,
  `CMakeLists.txt`.
- `experimental/pikmin2_hanachirashi_behavior.py`, `tests/test_pikmin2_hanachirashi_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Executable SHA-256 | isolated `91C36D34981E5A6151B653EB23F80CD69F9C3196DC68D924909062718BCE0CA1` |
| Run directory | `output/p2-species-hanachirashi/e9836f7703ed46d2b284f600caaab837` |
| Hash | `native.log` `FFBA40DD…091DCF4B` |

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_HANACHIRASHI_BIND generator=375002 source_id=55`; `P2_BATCH3_BIND …key=flying|Hanachirashi visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS (partial) | states `wait/chase/attack/laugh`; clips `move1/attack/laugh`; 95.7 XZ spread; source `move`/fly states are bounded gaps |
| 3. Attacks / receivers | PASS (partial) | `P2_HANACHIRASHI_BLOW pikmin=19/11` at the attack event frame; Purple wither-strip UNTESTED |
| 4. Death + corpse | UNTESTED | death path implemented; 1800 HP not killed by the fixture |
| 5. Transport + reward | N/A | no carry/reward for this lane |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired |

## Remaining work

- Purple wither-strip and invincible/KokeDamage semantics; source `move`/fly states.
- Death/corpse/cleanup (#397).
