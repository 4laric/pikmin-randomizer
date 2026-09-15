# Lane 10 handoff — natural gas/electric fixed-hazard emitters through the P2 receivers (#408)

- Lane: **10 — Receivers** (parent [#170](https://github.com/4laric/pikmin-randomizer/issues/170), child [#408](https://github.com/4laric/pikmin-randomizer/issues/408)).
- Implementation owner: Codex through shared account `4laric`. Executing agent: DeepSeek (this lane session).
- Root branch `deepseek/p2-l10` (worktree `output/dsw/l10-root`); native branch `deepseek/p2-l10-native` (worktree `output/dsw/native-l10`).

## Slice delivered

The receivers ledger lists "remaining family emitters and physical elemental
receivers; ElecBug electric path is integrated". Electric was already proven by
the ElecBug emitter; **gas had a receiver but no natural emitter**. This slice
wires the existing fixed-hazard emitters **GasHiba (source id 21)** and
**ElecHiba (source id 22)** through the real lane-10 receivers, closing the gas
reception gap and re-proving electric through a second emitter:

- `GasHiba -> InteractGas -> PIKISTATE_Panic(36)` (gas) then poison `Dying -> Dead`.
- `ElecHiba -> InteractDenki -> PIKISTATE_DenkiDying(35)` then `Dead`.
- White (species 4) immune to gas; Yellow (species 2) immune to electricity;
  both rejected through the lane-11 `p2_species_immune` matrix via the lane-10
  `p2_hazard_emitter.h` contract. Gas-invincible gate honoured.
- Hiba fire path unchanged.

## Files owned and changed

**Native** (2 files, one small labelled family-emitter hook; the receivers themselves were already present and are untouched):

- `pc_port/pc_p2_hiba.cpp` — `emitScan` replaced the `P2_HIBA_APPLY_BLOCKED
  reason=no_engine_interaction` gas/denki branch with species-based routing
  through `p2_emitter_accepts(pc_p2_species(piki), P2HazardGas|P2HazardElectric,
  piki->gasInvicible())` and delivery of real `InteractGas`/`InteractDenki`.
  Added `gasHitTargets`/`denkiHitTargets` bookkeeping, `pc_p2_hiba_lethal_check()`
  (liveness-by-address, never dereferences a recycled Piki), per-element
  hit/immune/lethal flags, and extended `pc_p2_hiba_gates_ready()`.
- `pc_port/pc_p2_hiba.h` — declarations for the new gates.

**Root** (2 files):

- `experimental/pikmin2_hiba_runtime.py` — fixture recolours one Blue -> White
  and one Blue -> Yellow via `pc_p2_set_species` (`#include "pc_p2_species.h"`)
  to expose the immunity boundary; `validate()` gained `gas_hit`, `gas_pass`,
  `denki_hit`, `denki_pass`, `gas_lethal`, `denki_lethal`, `recolour`,
  `no_gas_blocked` and dropped the obsolete `gas_blocked`. Docstring updated.
- `tests/test_pikmin2_hiba_native.py` — synthetic-log gates updated, plus
  `GasReceiverNativeTests`.

No shared engine files were touched (`teki.h`, `tekiinteraction.cpp`,
`tekibteki.cpp`, `tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`,
`pc_p2_preview.cpp`, `interactBattle.cpp`, `Interactions.h`, `pikiState.cpp`,
CMake — all unchanged). The `InteractGas`/`InteractDenki` receivers and
`p2_hazard_reaction` routing were already integrated (§7/§9 of
`PIKMIN2_RECEIVER_PATHS.md`).

## Ordered commits

Native (base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`), clean:

```
55bd78a3 lane10: wire GasHiba/ElecHiba emitters to real InteractGas/InteractDenki receivers (#408)
```

Root (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`), clean:

```
40a29d4 lane10: natural GasHiba/ElecHiba emitter -> real InteractGas/InteractDenki receivers, runtime gate (#408)
```

Dirty state: both worktrees clean at handoff (build dirs, fixture and run output
are ignored/private).

## Build evidence (`output/dsw/l10-build-evidence.txt`)

```
2026-09-14T19:48:04 lane=l10 target=pikmin_pc native=55bd78a3abab1c6c18f6f9f633188d5d821513ee dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l10-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l10-build\bin\nectar.exe sha256=651cd0b51f637dc4924e69e0c71a3f83ece74e1aac41e4f2fc6eb71e2b322070 ninja_n="ninja: no work to do."
```

- `[603/603] Linking CXX executable bin\nectar.exe` (exit 0); `ninja -n pikmin_pc` -> `ninja: no work to do.`
- Fixture provenance `provenance.json` status `built` (`output/dsw/l10-out/hiba-fixture/build/provenance.json`).
- Fixture `fixture.exe` SHA-256 `8a3bafdba66c3d4ff03a4a6f52a96aa14580464ddc7597e5e13f3c372fca2da4`.

## Fixture baseline adoption

- Root commit + overlay source: `40a29d4` (clean); `experimental/pikmin2_hiba_runtime.py` uses `scripts/preview_pikmin2_room.overlay()` and authors an explicit 5-red/5-blue squad (per-scenario override needed to expose the fire gas/denki immunity boundary; recorded in `hiba-stage.json` `starting_squad={'red':5,'blue':5}`). No default 20-red top-up applies because an authored squad exists.
- Native commit + window: `55bd78a3` (clean), private build dir `output/dsw/native-l10-build`.
- Window: `SDL2 Window & OpenGL Context initialized successfully (960x540)` and `Experimental preview window set to 960x540 windowed and centered`.
- Live squad: `P2_HIBA_BASELINE red=5 blue=5`, then `P2_HIBA_RECOLOUR white=1 yellow=1`; no extinction.
- Run dir: `output/dsw/l10-out/hiba-run/hiba/75df7ddbd2bf49f8b796bf993f3f0532` (`result.json` `passed=true`, `exit_code=0`, `no_leftover_process=true`).

## Six arena gates

| Gate | Result | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | PASS | `P2_HIBA_READY` ×3 for Hiba/GasHiba/ElecHiba (ids 20/21/22) at their generators; `P2_HIBA_NODES` for the ±40 ElecHiba pair. Placement is fixture-injected on the live-Pikmin centroid; identity/source policy is native. |
| 2 Autonomous movement/animation | source-backed N/A | Fixed hazards are scenery; the native FSM `Wait->(Sign)->Attack` runs and is observed (`P2_HIBA_ACTIVATE`/`SIGN`/`DEACTIVATE`), but there is no locomotion clip. |
| 3 Attacks and receivers | PASS | Natural emitter -> real receiver: `InteractFire` (Hiba), `InteractGas`->`PIKISTATE_Panic`=36 (GasHiba), `InteractDenki`->`PIKISTATE_DenkiDying`=35 (ElecHiba). Immune rejection `P2_HIBA_GAS_PASS species=4` (White) and `P2_HIBA_DENKI_PASS species=2` (Yellow). Recolour is a labelled fixture injection. |
| 4 Death and corpse | PASS (death) | `P2_HIBA_GAS_LETHAL dead=1` (poison->Dying->Dead) and `P2_HIBA_DENKI_LETHAL dead=1` (0.3s wait->Dead). No enemy corpse (fixed hazards drop nothing). |
| 5 Actual transport and reward | source-backed N/A | Fixed hazards carry no treasure/pellet; no transport/reward path applies. |
| 6 Cleanup and re-entry | PASS (cleanup) / UNTESTED (re-entry) | `P2_HIBA_CLEANUP kill_all=1` + `P2_HIBA_DEAD` ×3, exit 0. Scene re-entry not run this slice. |

## Tests

- `tests/test_pikmin2_hiba_native.py` -> **19 passed**.
- Focused lane-10 receiver suite -> **85 passed**
  (`test_pikmin2_hiba_native`, `test_pikmin2_receivers_runtime`,
  `test_pikmin2_elemental_behavior`, `test_pikmin2_dweevil_native`,
  `test_pikmin2_elecbug_denki_runtime`).

Pre-existing failures (NOT introduced by this slice, no files shared with it):
`tests/test_pikmin2_lanes_1012_policies.py` — 8 failed:
- 7 × `test_lane_policy_contract[test_p2_*.cpp]`: the standalone `g++` invocation
  in that test does not put `C:/msys64/mingw64/bin` on PATH, so `g++`'s helper
  (`cc1plus.exe`/DLLs) is not found and it exits 1 silently (builds through
  `build_lane.py`, which sets PATH, succeed).
- 1 × `test_elemental_receivers_consult_species_capability_matrix`: stale
  assertion still greps the pre-§9 `p2_species_immune(..., P2HazardElectric/Gas)`;
  the current source routes electric/gas through `p2_hazard_reaction`. Its
  successor `test_denki_gas_receivers_route_to_p2_states` already asserts the
  correct anchors (and passes when the native source is visible).

## Assumptions

- GasHiba/ElecHiba were chosen as the natural gas/electric emitters because they
  already exist as actor-local FSMs in `pc_p2_hiba.cpp` (the single
  `P2_HIBA_APPLY_BLOCKED` branch to replace); no new emitter subsystem was built.
- Reused the lane-10 `p2_hazard_emitter.h` contract and the already-ported
  `InteractGas`/`InteractDenki` receivers unchanged; hence the defensive
  `__attribute__((used))` retention on the receivers is now obsolete but left
  untouched.
- RECONSTRUCTED / P1-derived (source audit findings retained as labels): gas
  panic plays `PIKIANIM_Moeru` not `GASDEAD`; no `PanicStateArg`/`PIKIPANIC_Gas`
  channel; `DenkiDying` forwards straight to `PIKISTATE_Dead` (no electric
  effect/counter/sound); `gasInvicible` is a boolean latch, not the source
  90-frame countdown.
- Recolour (`pc_p2_set_species`) and centroid placement are explicit fixture
  interventions labelled in the evidence.

## Remaining blockers (provider lane)

- Enemy-side gas/electric family emitters (dweevil `GasOtakara`/`ElecOtakara`
  discharge and `BombOtakara` payload, blowhog `Tank`/`Wtank` sweep) remain
  **lane 22 (#447)** / **lane 20 (#169)** family work; a Hiba fixture does not
  admit those identities.
- Corpse/transport/reward plus scene re-entry for these hazards remains
  **lane 07 (#397)** lifecycle territory.

## Reproduction

```powershell
py -3.12 output/deepseek-wave/build_lane.py l10
py -3.12 output/deepseek-wave/slot.py run build l10 -- py -3.12 -m experimental.pikmin2_hiba_runtime build --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l10 --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l10-build --output C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-fixture --head 55bd78a3abab1c6c18f6f9f633188d5d821513ee
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 output/deepseek-wave/slot.py run gl l10 -- py -3.12 -m experimental.pikmin2_hiba_runtime run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --output C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-run --exe C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-fixture/build/fixture.exe
```

## Subagent usage

Three subagents were launched in parallel (per the lane brief).

1. **`explore` — source audit** of the gas/denki receivers + panic/DenkiDying
   states + emitters (decomp `pikmin2-research` vs port). Result **used as-is**:
   it confirmed the routing/immunity table and produced the exact
   "RECONSTRUCTED"/"P1-derived" gap list now quoted in Assumptions. Saved ~30 min
   of decomp cross-referencing.
2. **`explore` — existing-candidate inventory** across root + native for the
   hazard/gas/denki/receiver identity. Result **used as-is**: it pinpointed
   `pc_p2_hiba.cpp` `emitScan` as the single blocking branch, the exact
   call sites (`pc_p2_preview.cpp`, `gameCoreSection.cpp`, `tekimgr.cpp`), and
   the already-encoded marker contract. Saved ~20 min of grep/audit.
3. **`general` — validator + tests**: extended `experimental/pikmin2_hiba_runtime.py::validate`
   and `tests/test_pikmin2_hiba_native.py` to the new gas/denki markers and ran
   pytest (19 passed). Result **used with correction**: its edits were adopted
   as-is for `validate()` and the tests; I separately added the `APP` C++
   recolour and the `#include "pc_p2_species.h"` (out of the subagent's remit).
   Saved ~20 min of test-bootstrap.

Net: ~70 minutes of parallel reading/testing off the critical path, with no
rework beyond the expected hand-off of the C++ fixture body back to me.
