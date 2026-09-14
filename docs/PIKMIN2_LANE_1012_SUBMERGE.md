# Lanes 10-12 consolidated candidate (sub-merge)

Consolidated, review-ready candidate for the lane 10-12 worker slices, so lane 01
has one merge instead of four overlapping branches. Implementation owner: Codex
through shared `4laric`; executing sessions: opencode main session plus three
opencode subagents (`opencode-go/deepseek-v4.1-flash`).

- Root branch: `opencode/p2-submerged-root`, base `opencode/p2-lanes-1012` @
  `5b1e981`, then merges of `opencode/p2-sub-captains`,
  `opencode/p2-sub-bulbmin`, `opencode/p2-sub-elements` (all clean).
- Native branch: `opencode/p2-submerged-native` @ `4f7485d5`, base
  `5a0cb4ee`; complete series from maintained native `f9e139d8` is exported as
  `native-candidates/p2-submerged/0001..0011`. Native origin not pushed.
- Worktrees: `output/native-submerged`, `output/native-submerged-build`,
  `output/p2-submerged-root`.

## Combined build

```text
cmake -S output/native-submerged -B output/native-submerged-build -G Ninja \
  -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON
cmake --build output/native-submerged-build --target pikmin_pc -j 4
# [522/522] Linking CXX executable bin\nectar.exe   (exit 0)
# ninja -n pikmin_pc -> no work to do
```

`nectar.exe` SHA-256 `6E14D8096BFEB1439B4C6D83BEDD2D3CBB70B9A5DC4C7CA66B2197C345528766`.

## Combined policy tests (all from the merged native tree)

```text
PASS P2_CAPTAIN_POLICY
PASS P2_CAPTAIN_ADAPTER
PASS P2_BULBMIN_POLICY
PASS P2_BULBMIN_BRIDGE
PASS P2_SPECIES_POLICY
PASS P2_SPECIES_SCHEMA
PASS P2_ELEMENTAL_RECEIVERS
```

Root suite: `pytest tests/test_pikmin2_lanes_1012_policies.py
tests/test_pikmin2_captain_adapter.py tests/test_pikmin2_bulbmin_bridge.py -q`
-> **11 passed**.

## Contents and per-slice evidence

| Slice | Native commit(s) | Detail doc |
|---|---|---|
| L12 captain/squad contract + captive semantics + slot-0 adapter (#130) | `fd40992c` | `PIKMIN2_CAPTAIN_SQUAD_CONTRACT.md` |
| L11 Bulbmin contract + identity + engine bridge (#131) | `9f9d0783` | `PIKMIN2_BULBMIN_CONTRACT.md` |
| L11 capability matrix + versioned schema + cave schema 3 (#131/#395) | `a21e12b5`, `5a0cb4ee` | `PIKMIN2_SPECIES_CAPABILITY_MATRIX.md` |
| L10 electric/gas receivers (#170/#408) | `7e2ab032`, `05ee72d7` | `PIKMIN2_RECEIVER_PATHS.md` |
| L10 fire/bubble matrix routing | `d28ff29c` | `PIKMIN2_RECEIVER_PATHS.md` §6 |

## Limits (all slices are compile / engine-double, not live runtime)

- L12: port is single-captain; no `mNaviIndex`, single `NaviMgr::getNavi()`, only
  `mNaviShapeObject[0]` built. Adapter binds slot 0 only.
- L11: no LeafChappy/KumaChappy mother actor, no spawner, no `piki_kochappy`
  model; bridge is inert without config.
- L10: `PIKISTATE_DenkiDying`/`PIKISTATE_Panic` and the `gasInvicible` gate are
  now added and the non-immune receivers route into them (see
  `PIKMIN2_RECEIVER_PATHS.md` §9); no electricity/gas emitter exists yet, so no
  live hazard encounter is claimed.
- Cave schema 3 is validation/build-backed; no Bulbmin spawns.

Shared-semantics edits in this candidate (`Piki.h`, `interactBattle.cpp`,
`navi.cpp`, `Interactions.h`, `pc_p2_cave.cpp`, `pc_p2_preview.cpp`, captain
adapter, CMake) require #186 review before lane 01 integrates.

## Wave 2 — engine-prerequisite layer

Native `opencode/p2-submerged-native` @ `95bfa756`; root
`opencode/p2-submerged-root` updated. Series `native-candidates/p2-submerged/`
now 13 patches (from `f9e139d8`).

| Slice | Native commit | Result |
|---|---|---|
| L12 opt-in second-captain primitives + slot-1 binding | `8352ef91` | helpers `Navi::getNaviIndex/getOtherNaviIndex`, `NaviMgr::getOtherNavi/getActiveNavi/getAliveOrima/getDeadOrima/...`; slot-1 binding; live spawn gated OFF (`second_captain_live_allowed()` false). `PASS P2_CAPTAIN_ROSTER/ADAPTER/POLICY`. |
| L11 Bulbmin driver from the Chappy registration | `1d16e381` | `pc_p2_kochappy` path drives the bridge: 10-body `birthChildren`, whistle claim into the captain ownership table, death/forget; inert without config. `PASS P2_BULBMIN_BRIDGE/POLICY/ADAPTER`. |
| L10 electric/gas **runtime** proof | base unchanged | Extended `experimental/pikmin2_receivers_runtime.py` probe injects `InteractDenki`/`InteractGas`; engine-double + **real GL run** `passed=true`. |

Combined build: `[149/150] Linking CXX executable bin\nectar.exe` (exit 0),
`ninja -n pikmin_pc` no work; `nectar.exe` SHA-256
`B007710788E0283EF48EB4E797CA0B4B6D9EDFD1706F69F2BFAF59AFE19067A0`.

Combined policy tests (8): `PASS P2_CAPTAIN_POLICY`, `P2_CAPTAIN_ADAPTER`,
`P2_CAPTAIN_ROSTER`, `P2_BULBMIN_POLICY`, `P2_BULBMIN_BRIDGE`,
`P2_SPECIES_POLICY`, `P2_SPECIES_SCHEMA`, `P2_ELEMENTAL_RECEIVERS`.
Root pytest `tests/test_pikmin2_lanes_1012_policies.py
tests/test_pikmin2_captain_adapter.py tests/test_pikmin2_bulbmin_bridge.py
tests/test_pikmin2_receivers_runtime.py -q` -> **24 passed**.

L10 runtime evidence (private): run
`output/tracks/p2-receivers-sub2/runs-recv/stages/bc3940c92ffa4d05bb237c4388751538`,
exit 0 `passed=true`, window 960x540 centred, `P2_RECV_SQUAD alive=20 reds=20`,
`P2_RECV_ELEMENT_EXT yellow_denki=0 white_gas=0 bulbmin_denki=0 bulbmin_gas=0 red_denki=1 red_gas=1`
(Yellow immune to electricity, White immune to gas, Bulbmin immune to both, Red
affected by both). Fixture provenance `status=built`.

Still blocked, not faked: real two-captain play (follow/split-squad AI, camera,
controls, HUD, survivor-gated game over — `file:line` in the captain contract);
a Mother Bulbmin actor/model and live spawn; enemy-side electricity/gas
emitters (the Pikmin-side `PIKISTATE_DenkiDying`/`PIKISTATE_Panic`/gas gate are
now present, native `2a4521da`). `PIKMIN_P2_SECOND_CAPTAIN` remains inert.

