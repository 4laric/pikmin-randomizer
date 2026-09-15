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

## Review fixes (fix1) — natural-vs-injected attribution corrected

The review flagged two attribution defects (both fixed and re-verified at runtime):

1. **Fire contamination of the gas/denki lethal gate.** `P2_HIBA_GAS_LETHAL`
   fired on *any* recorded gas target, so a Pikmin burned by the adjacent Hiba
   satisfied it. Now gas-lethal requires a **fire-immune species (Red)**, never
   denki-tagged, and no longer alive; denki-lethal requires a fire-immune Red
   that is no longer alive (its `PIKISTATE_DenkiDying` is electric-exclusive).
   Both `P2_HIBA_GAS_LETHAL`/`P2_HIBA_DENKI_LETHAL` now print `species=`, which
   the runtime reports as **species=1 (Red)** for both gates.
2. **Fire branch used P1 colour.** `policyColour`/`pikminImmune` let a
   recoloured White (whose `mColor` is Red) pass as fire-immune. Fire now routes
   through `p2_species_immune(species, P2HazardFire)` and logs `species=`; a
   recoloured White is correctly fire-vulnerable.
3. To guarantee the gas and denki witnesses are *different* fire-immune Reds
   (gas-panicked and fire-deferred update otherwise scatters the squad, and the
   later-attacking ElecHiba could reach no live target), the fixture now stages
   **two ~150-unit X-separated clusters**: Hiba+GasHiba on G (with the gas
   witness Reds), ElecHiba on E (with the denki witness Red + denki-immune
   Yellow). ElecHiba gains a `warning_override` config field (0.05) so it
   attacks before the gas-cluster panic-run.
4. Hit-targets use `std::map<const void*,int>` (address -> species) and stop
   inserting once the element's lethal flag is set (no recycled-slot death
   masking).
5. `interactBattle.cpp` `__attribute__((used))` receiver comments updated (the
   ElecBug/ElecHiba/GasHiba emitters now reference both receivers).

## Files owned and changed

**Native** (the receivers themselves were already present and are untouched; the
emitter hook and the fire-species/lethal-attribution fixes land here):

- `pc_port/pc_p2_hiba.cpp` — `emitScan` replaced `P2_HIBA_APPLY_BLOCKED` with
  species-based routing through `p2_emitter_accepts(...)` and real
  `InteractFire`/`InteractGas`/`InteractDenki` delivery (fire, gas and electric
  all via the lane-11 `p2_species_immune` matrix). Added `gasTargets`/
  `denkiTargets` map bookkeeping, `pc_p2_hiba_lethal_check()` with fire-immune +
  element-exclusive attribution, per-element hit/immune/lethal flags, and
  `gates_ready()`.
- `pc_port/pc_p2_hiba.h` — declarations + cross-lane owner note.
- `pc_port/pc_p2_hiba_policy.h` — `HazardRow`/`readConfig` gained
  `warningOverride` (ElecHiba-only) for the fixture timing.
- `src/plugPikiKando/interactBattle.cpp` — updated the two obsolete
  `__attribute__((used))` "no emitter references this receiver yet" comments
  (comment-only).

**Root** (4 files):

- `experimental/pikmin2_hiba_runtime.py` — two X-separated clusters, position-based
  recolour (G Blue -> White, E Blue -> Yellow), ElecHiba `warning_override`, and
  `validate()` gates: `fire_hit`, `fire_pass`, `gas_hit`, `gas_hit_red`,
  `gas_pass`, `denki_hit`, `denki_pass`, species-tagged `gas_lethal`/
  `denki_lethal`, `recolour`, `no_gas_blocked`, `no_apply_blocked`.
- `tests/test_pikmin2_hiba_native.py` — updated synthetic-log gates + negative
  tests (a fire death must not satisfy the gas gate; a bare/untagged LETHAL is
  rejected; missing `gas_hit_red` fails).
- `tests/pikmin2_hiba_policy.cpp` — config coverage for `warningOverride`.

No shared engine files were touched except the two comment-only edits in
`interactBattle.cpp` (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`,
`Interactions.h`, `pikiState.cpp`, CMake — all unchanged).

## Ordered commits

Native (base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`), clean:

```
55bd78a3 lane10: wire GasHiba/ElecHiba emitters to real InteractGas/InteractDenki receivers (#408)
cfacff01 lane10: review fixes - species-based fire, element-attributed lethal (#408)
7910d838 lane10: review fixes - fire-immune-only gas/denki lethal witness (#408)
f34abccf lane10: review fixes - ElecHiba warning override + two-cluster scene (#408)
```

Root (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`), clean:

```
40a29d4 lane10: natural GasHiba/ElecHiba emitter -> real InteractGas/InteractDenki receivers, runtime gate (#408)
0135ae8 lane10: handoff doc (#408)
7426ff7 lane10: review fixes - two-cluster scene, per-element Red lethal witness (#408)
4defa3e lane10: review fixes - warning override wiring in harness+tests (#408)
```

Dirty state: both worktrees clean at handoff (build dirs, fixture and run
output are ignored/private).

## Build evidence (`output/dsw/l10-build-evidence.txt`)

First line (dirty base build) and final line (committed clean build):

```
2026-09-14T20:59:03 ... native=55bd78a3... dirty=yes ... exe=...\nectar.exe sha256=19e497175485e6a65c526c6555f2f00efb447075abbc50d535d0aef42fb16630 ninja_n="ninja: no work to do." seconds=74
2026-09-14T23:12:32 ... native=f34abccf9dc8b9e5818ccc603aa036796de5c0eb dirty=no ... exe=...\nectar.exe sha256=36bbb47e1fdc028ba623c903ebf8390766642989390b5f3c41f39bb5fbcf1969 ninja_n="ninja: no work to do." seconds=0
```

- `[2/2] Linking CXX executable bin\nectar.exe` (exit 0); `ninja -n pikmin_pc` -> `ninja: no work to do.`
- Fixture provenance `provenance.json` status `built` (`output/dsw/l10-out/hiba-fixture4/build/provenance.json`).
- Fixture `fixture.exe` SHA-256 `e484846f29a0afb0a4456e519929321b3b7546f758d1ffddf8a2bab059557db2`.

## Fixture baseline adoption

- Root commit + overlay source: `4defa3e` (clean); `experimental/pikmin2_hiba_runtime.py` uses `scripts/preview_pikmin2_room.overlay()` and authors an explicit 5-red/5-blue squad split across two X-separated clusters (recorded in `hiba-stage.json` `starting_squad={'red':5,'blue':5}`).
- Native commit + window: `f34abccf` (clean), private build dir `output/dsw/native-l10-build`.
- Window: `SDL2 Window & OpenGL Context initialized successfully (960x540)` and `Experimental preview window set to 960x540 windowed and centered`.
- Live squad: `P2_HIBA_BASELINE red=5 blue=5`, then `P2_HIBA_RECOLOUR white=1 yellow=1`; no extinction.
- Run dir: `output/dsw/l10-out/hiba-run4/hiba/e4616143bb624d7d852f304ba15906dc` (`result.json` `passed=true`, `exit_code=0`, `no_leftover_process=true`).

## Six arena gates

| Gate | Result | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | PASS | `P2_HIBA_READY` ×3 for Hiba/GasHiba/ElecHiba (ids 20/21/22) at their generators; `P2_HIBA_NODES` for the ±40 ElecHiba pair. Placement is fixture-injected on two X-separated clusters; identity/source policy is native. |
| 2 Autonomous movement/animation | source-backed N/A | Fixed hazards are scenery; the native FSM `Wait->(Sign)->Attack` runs and is observed (`P2_HIBA_ACTIVATE`/`SIGN`/`DEACTIVATE`), but there is no locomotion clip. |
| 3 Attacks and receivers | PASS | Natural emitter -> real receiver: `InteractFire` (Hiba, species-based; White species=4 now fire-HIT, Red species=1 fire-PASS), `InteractGas`->`PIKISTATE_Panic`=36 (GasHiba; Red species=1 hit), `InteractDenki`->`PIKISTATE_DenkiDying`=35 (ElecHiba; Red species=1 hit). Immune rejection `P2_HIBA_GAS_PASS species=4` (White) and `P2_HIBA_DENKI_PASS species=2` (Yellow). |
| 4 Death and corpse | PASS (death, element-attributed) | `P2_HIBA_GAS_LETHAL dead=1 species=1` (fire-immune Red, gas-exclusive Panic->Dying->Dead) and `P2_HIBA_DENKI_LETHAL dead=1 species=1` (fire-immune Red, denki-exclusive DenkiDying->Dead, 0.3s). No enemy corpse (fixed hazards drop nothing). |
| 5 Actual transport and reward | source-backed N/A | Fixed hazards carry no treasure/pellet; no transport/reward path applies. |
| 6 Cleanup and re-entry | PASS (cleanup) / UNTESTED (re-entry) | `P2_HIBA_CLEANUP kill_all=1` + `P2_HIBA_DEAD` ×3, exit 0. Scene re-entry not run this slice. |

## Tests

- `tests/test_pikmin2_hiba_native.py` -> **23 passed** (with `P2_NATIVE_PC_PORT` set to the native worktree so the C++ policy test compiles against the new `warningOverride` reader).
- Focused lane-10 receiver suite -> **77 passed**
  (`test_pikmin2_hiba_native`, `test_pikmin2_receivers_runtime`,
  `test_pikmin2_elemental_behavior`, `test_pikmin2_elecbug_denki_runtime`).

Negative tests added for the gas gate: a fire-only death must NOT satisfy it; a
bare `P2_HIBA_GAS_LETHAL dead=1` (untagged) and a missing `gas_hit_red` both
fail the validator.

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
  `InteractGas`/`InteractDenki` receivers unchanged; the defensive
  `__attribute__((used))` retention on the receivers is now documented as
  defensive (the emitters reference them).
- **Attribution rule:** a target is gas-lethal only if it is fire-immune (Red)
  and never denki-tagged; denki-lethal only if fire-immune (Red). This makes
  `PIKISTATE_Panic`/`PIKISTATE_DenkiDying` the gas-/electric-exclusive fatal
  chains and rules out fire-burn contamination.
- **Two-cluster scene:** the gas (fire-immune Red) and denki (fire-immune Red)
  witnesses are placed in X-separated clusters ~150 units apart so neither
  co-exposes a Pikmin to the other element; ElecHiba uses a `warning_override`
  (0.05) so it attacks before the gas-cluster panic-run. Both witness Reds
  report `species=1`.
- RECONSTRUCTED / P1-derived (source audit findings retained as labels): gas
  panic plays `PIKIANIM_Moeru` not `GASDEAD`; no `PanicStateArg`/`PIKIPANIC_Gas`
  channel; `DenkiDying` forwards straight to `PIKISTATE_Dead` (no electric
  effect/counter/sound); `gasInvicible` is a boolean latch, not the source
  90-frame countdown.
- Recolour (`pc_p2_set_species`) and two-cluster placement are explicit fixture
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
py -3.12 output/deepseek-wave/slot.py run build l10 -- py -3.12 -m experimental.pikmin2_hiba_runtime build --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l10 --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l10-build --output C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-fixture4 --head f34abccf9dc8b9e5818ccc603aa036796de5c0eb
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 output/deepseek-wave/slot.py run gl l10 -- py -3.12 -m experimental.pikmin2_hiba_runtime run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --output C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-run4 --exe C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-fixture4/build/fixture.exe
```

## Subagent usage

First slice (see prior handoff) used three subagents. This fix1 slice used three
more:

1. **`explore` — source audit** of the fire/gas/electric immunity matrix +
   panic/DenkiDying states + White fire-vulnerability (decomp vs port). Result
   **used as-is**: confirmed White must be fire-vulnerable per P2 and that
   `PIKISTATE_Panic`(36) / `PIKISTATE_DenkiDying`(35) are gas-/electric-exclusive,
   which underpins the fire-immune attribution. Saved ~25 min.
2. **`explore` — candidate inventory** of every `P2_HIBA_*` marker, the exact
   `policyColour`/`colourName` call sites, the `interactBattle.cpp`
   `__attribute__((used))` comment blocks, and the build-evidence lines. Result
   **used as-is**: pinpointed the fire-branch colour usage to remove and the
   comment text to update. Saved ~20 min.
3. **`general` — validator + tests**: converted `validate()` to the species-based
   fire markers + species-tagged LETHAL + `gas_hit_red`/`no_apply_blocked` and
   added the fire-death-must-not-satisfy negative tests (23 passed). Result
   **used as-is**; I only later added the `warningOverride` config coverage and
   the two-cluster `APP`/`stage`/`protocol` changes (out of its remit). Saved
   ~20 min.

Net: ~65 min of parallel reading/testing off the critical path.
