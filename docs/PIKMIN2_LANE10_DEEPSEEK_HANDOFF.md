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

## Review fixes (fix2) — validator parity + denki attribution + labelling

1. **Validator now enforces what native guarantees.** `gas_lethal`/`denki_lethal`
   regexes require `species=1` (a fire-immune Red), not `species=\d+`; the
   synthetic `GOOD` seed was corrected from `species=2` (a Yellow the native
   `pc_p2_hiba_lethal_check` can never emit) to `species=1`; new negative tests
   assert a `species=0` LETHAL (a fire-vulnerable Blue) fails both gates.
2. **Denki-lethal attribution parity.** `pc_p2_hiba.cpp` denki loop now carries
   the `gasTargets.count(entry.first)` exclusion the gas loop already had, so a
   Red gassed *and* shocked is never counted denki-lethal on a gas death.
3. **Cross-lane labelling** (see "Files owned and changed"): `pc_p2_hiba.cpp` is
   lane 22's fixed-hazard module; lane-10 changed `emitScan` to call
   `p2_emitter_accepts`, so the emitter and the receivers cannot disagree about
   immunity. Future shared edits are labelled in the commit subject.
4. **Doc sync** — `docs/PIKMIN2_HIBA_NATIVE.md` sidecar row is now the 11-column
   (`<...> <link> <warningOverride>`) grammar the reader actually enforces.
5. **Lanes-10/11/12 policy test fix** — `tests/test_pikmin2_lanes_1012_policies.py`
   now asserts the electric/gas receivers route through `p2_hazard_reaction` (not
   the superseded `p2_species_immune` string) and prepends the MinGW bin dir to
   PATH for the `test_lane_policy_contract` compile/run (its 7 subtests now pass).
6. **Root/native land as a pair**: `NativePolicyTests` compiles
   `tests/pikmin2_hiba_policy.cpp` against the native `pc_p2_hiba_policy.h`, so
   the native (`warningOverride`) and root commits must merge together.

## Files owned and changed

**Native** (the receivers themselves were already present and are untouched; the
emitter hook and the fire-species/lethal-attribution fixes land here):

- `pc_port/pc_p2_hiba.cpp` — **lane 22's fixed-hazard module** (not owned by lane
  10). Lane-10 changed `emitScan` to route fire/gas/electric through
  `p2_emitter_accepts(...)` (the lane-10 contract) and deliver real
  `InteractFire`/`InteractGas`/`InteractDenki` (all via the lane-11
  `p2_species_immune` matrix), replacing the `P2_HIBA_APPLY_BLOCKED` branch.
  Added `gasTargets`/`denkiTargets` map bookkeeping, `pc_p2_hiba_lethal_check()`
  with fire-immune + element-exclusive attribution (gas-lethal excludes
  denki-tagged targets; denki-lethal excludes gas-tagged targets), per-element
  hit/immune/lethal flags, and `gates_ready()`.
- `pc_port/pc_p2_hiba.h` — declarations + cross-lane owner note.
- `pc_port/pc_p2_hiba_policy.h` — `HazardRow`/`readConfig` gained
  `warningOverride` (ElecHiba-only) for the fixture timing.
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
1c6ba3ce lane10: review fixes 2 - denki-lethal excludes gas-hit targets (#408)
11fb136c lane10 (owner lane22 pc_p2_hiba): add hazard-count probe for gate-6 re-entry (#408)
```

Root (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`), clean:

```
40a29d4 lane10: natural GasHiba/ElecHiba emitter -> real InteractGas/InteractDenki receivers, runtime gate (#408)
0135ae8 lane10: handoff doc (#408)
7426ff7 lane10: review fixes - two-cluster scene, per-element Red lethal witness (#408)
4defa3e lane10: review fixes - warning override wiring in harness+tests (#408)
f710f40 lane10: review fixes 2 - species=1 lethal gate, sidecar doc, lanes-1012 policies (#408)
5f5d6cc lane10: review fixes 2 handoff update (#408)
5570495 lane10: review fixes 2 - correct gate-1 citation line (#408)
b99fba2 lane10: slice 2 - gate-6 re-entry proof, receiver contract doc, PIKMIN_NATIVE_ROOT (#408)
```

Dirty state: both worktrees clean at handoff (build dirs, fixture and run
output are ignored/private).

## Build evidence (`output/dsw/l10-build-evidence.txt`)

First line (dirty base build) and final line (committed clean build):

```
2026-09-14T20:59:03 ... native=55bd78a3... dirty=yes ... exe=...\nectar.exe sha256=19e497175485e6a65c526c6555f2f00efb447075abbc50d535d0aef42fb16630 ninja_n="ninja: no work to do." seconds=74
2026-09-15T01:10:22 ... native=1c6ba3ce62e147649890ccf55717bb2dcf628529 dirty=no ... exe=...\nectar.exe sha256=323b2dfcef1476cea88394223c29fd9f2065c2d3a237ac661fc6ab34d0ab23df ninja_n="ninja: no work to do." seconds=0
```

- `[2/2] Linking CXX executable bin\nectar.exe` (exit 0); `ninja -n pikmin_pc` -> `ninja: no work to do.`
- Fixture provenance `provenance.json` status `built` (`output/dsw/l10-out/hiba-fixture5/build/provenance.json`).
- Fixture `fixture.exe` SHA-256 `450aa55b5600fc2ceab1abc877017ab179f7a7ae527a4c31c3b98032b0480404`.

## Fixture baseline adoption

- Root commit + overlay source: `f710f40` (clean); `experimental/pikmin2_hiba_runtime.py` uses `scripts/preview_pikmin2_room.overlay()` and authors an explicit 5-red/5-blue squad split across two X-separated clusters (recorded in `hiba-stage.json` `starting_squad={'red':5,'blue':5}`).
- Native commit + window: `1c6ba3ce` (clean), private build dir `output/dsw/native-l10-build`.
- Window: `SDL2 Window & OpenGL Context initialized successfully (960x540)` and `Experimental preview window set to 960x540 windowed and centered`.
- Live squad: `P2_HIBA_BASELINE red=5 blue=5`, then `P2_HIBA_RECOLOUR white=1 yellow=1`; no extinction.
- Run dir: `output/dsw/l10-out/hiba-run5/hiba/12cfd6c159a44129a83eaebbdb6fc98e` (`result.json` `passed=true`, `exit_code=0`, `no_leftover_process=true`).

## Six-gate evidence (ingest format)

Scenario note (labelled injection, not part of any PASS): the fixed hazards are
fixture-placed on two X-separated clusters and the squad is recoloured (one Blue
-> White, one Blue -> Yellow) to expose the immunity boundary. Gate 6 is proven
through the lane-07 lifetime seam: the fixture calls the engine's own
`pc_p2_reset_all_teki()` (which invokes `pc_p2_hiba_reset`) and then re-enters via
`pc_p2_hiba_setup()`; the trigger is staged, but the seam functions are the
production teardown/re-entry path (no full scene reload is exercised). Note two
things about "re-arm exactly once": `pc_p2_hiba_setup()` already calls
`pc_p2_hiba_reset()` itself (`pc_p2_hiba.cpp:292`), so the once-invariant is
partly guaranteed by construction; the probe's value is observing that
`pc_p2_reset_all_teki()` actually clears the hazards (`before=3 reset=0`), and the
re-arm re-reads the sidecar (`rearmed=3`, not a stale +3).

- Source ID: 20 `Hiba`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED (injected) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:712 | injected |
| 2. Autonomous movement and animation | N/A | fixed hazard: no locomotion clip | N/A |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:729 | natural |
| 4. Death and corpse | PASS (natural, no corpse) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:730 | natural |
| 5. Actual transport and reward | N/A | fixed hazard drops nothing | N/A |
| 6. Cleanup and re-entry | PASS (staged seam) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:762 | staged |

- Source ID: 21 `GasHiba`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED (injected) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:713 | injected |
| 2. Autonomous movement and animation | N/A | fixed hazard: no locomotion clip | N/A |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:735 | natural |
| 4. Death and corpse | PASS (natural, no corpse) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:752 | natural |
| 5. Actual transport and reward | N/A | fixed hazard drops nothing | N/A |
| 6. Cleanup and re-entry | PASS (staged seam) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:762 | staged |

- Source ID: 22 `ElecHiba`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED (injected) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:715 | injected |
| 2. Autonomous movement and animation | N/A | fixed hazard: no locomotion clip | N/A |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:721 | natural |
| 4. Death and corpse | PASS (natural, no corpse) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:733 | natural |
| 5. Actual transport and reward | N/A | fixed hazard drops nothing | N/A |
| 6. Cleanup and re-entry | PASS (staged seam) | output/dsw/l10-out/hiba-run7/hiba/2a55926119f5455fba1683f77b33a675/native.log:762 | staged |

`scripts/check_p2_handoff_gates.py` output (run against the wave branch's roster
module; all three identities are `hazard` classification, so they are correctly
*ignored for enemy admission* rather than admitted — no refused PASS rows):

```text
20 Hiba (role=hazard): ignored (role)
21 GasHiba (role=hazard): ignored (role)
22 ElecHiba (role=hazard): ignored (role)
EXIT=0
```

## Tests (run with `PIKMIN_NATIVE_ROOT` pointing at the native worktree)

- `tests/test_pikmin2_hiba_native.py` + `tests/test_pikmin2_lanes_1012_policies.py` -> **40 passed** (`PIKMIN_NATIVE_ROOT` set to the native repo root; the C++ policy contracts compile from `<root>/pc_port` + `<root>/tools`, and the `p2_hazard_reaction`/reaction-state/piki.h source greps resolve under `<root>/src` + `<root>/include`).
- Focused lane-10 receiver suite -> **77 passed**
  (`test_pikmin2_hiba_native`, `test_pikmin2_receivers_runtime`,
  `test_pikmin2_elemental_behavior`, `test_pikmin2_elecbug_denki_runtime`).

Negative tests: a fire-only death must not satisfy the gas gate; a bare/untagged
LETHAL is rejected; missing `gas_hit_red` fails; a `species=0` LETHAL fails; and
(slice 2) a wrong re-entry (`rearmed=6`, `once=0`) or a missing `P2_HIBA_REENTRY`
line fails the fixture validator.

## Assumptions

- GasHiba/ElecHiba were chosen as the natural gas/electric emitters because they
  already exist as actor-local FSMs in `pc_p2_hiba.cpp` (the single
  `P2_HIBA_APPLY_BLOCKED` branch to replace); no new emitter subsystem was built.
- Reused the lane-10 `p2_hazard_emitter.h` contract and the already-ported
  `InteractGas`/`InteractDenki` receivers unchanged; the defensive
  `__attribute__((used))` retention on the receivers is now documented as
  defensive (the emitters reference them).
- **Attribution rule:** a target is gas-lethal only if it is fire-immune (Red)
  and never denki-tagged; denki-lethal only if fire-immune (Red) **and never
  gas-tagged**. This makes `PIKISTATE_Panic`/`PIKISTATE_DenkiDying` the
  gas-/electric-exclusive fatal chains and rules out fire-burn and cross-element
  contamination.
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
py -3.12 output/deepseek-wave/slot.py run build l10 -- py -3.12 -m experimental.pikmin2_hiba_runtime build --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l10 --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l10-build --output C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-fixture5 --head 1c6ba3ce62e147649890ccf55717bb2dcf628529
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 output/deepseek-wave/slot.py run gl l10 -- py -3.12 -m experimental.pikmin2_hiba_runtime run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --output C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-run5 --exe C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-fixture5/build/fixture.exe
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

Fix2 slice used three more subagents:

1. **`explore` — source audit** of the receiver routing (`interactBattle.cpp`
   `p2_hazard_reaction` line numbers) and the `pc_p2_hiba_lethal_check()` gas vs
   denki loop asymmetry (denki lacked the `gasTargets` exclusion). Result **used
   as-is**: gave the exact line for the one-line native fix and the exact
   assertion strings. Saved ~15 min.
2. **`explore` — candidate inventory** of the LETHAL markers, the `GOOD` seed, the
   `docs/PIKMIN2_HIBA_NATIVE.md` 10-vs-11 column doc, and the run4 native.log
   evidence line numbers. Result **used as-is**: gave the run5 line numbers cited
   in the gate table and the doc snippet to sync. Saved ~15 min.
3. **`general` — validator + tests**: tightened `gas_lethal`/`denki_lethal` to
   `species=1`, corrected the `GOOD` seed, added `species=0`-must-fail negative
   tests, fixed the lanes-1012 `p2_hazard_reaction` assertions and the MinGW-PATH
   in `test_lane_policy_contract` (38 passed). Result **used as-is**. Saved ~20 min.

Net: ~50 min of parallel work off the critical path.

## Slice 2

Receiver provider consumed by more families with natural attackers; gate-6
(cleanup/re-entry) and the receiver contract.

1. **Gate 6 cleanup/re-entry (was UNTESTED).** The fixture now proves the lane-07
   lifetime seam for the fixed hazards: after the gates pass it calls
   `pc_p2_reset_all_teki()` (the production stage-boundary teardown, which invokes
   `pc_p2_hiba_reset`) and then re-enters via `pc_p2_hiba_setup()`, logging
   `P2_HIBA_REENTRY before=3 reset=0 rearmed=3 once=1` — hazards reset to 0 and
   re-arm **exactly once** (3, not a stale +3 duplicate). Native hook
   `pc_p2_hiba_hazard_count()` added (labeled lane-22 module). Run7
   `native.log:762`, `hiba True`, exit 0.
2. **Receiver-side contract documented** in
   `docs/PIKMIN2_LANE10_RECEIVER_CONTRACT.md`: the `Interact*` class/constructor
   per element, the immunity helper (`p2_species_immune` for Fire/Water,
   `p2_hazard_reaction` for Gas/Electric), the reaction state, and the `P2_RECV_*`
   log. It records that lane 14 ElecBug already delivers `InteractDenki` via
   `p2_emitter_accepts` (the reference pattern), and that lane 22 Otakara maps
   Water/Gas/Elec/Bomb stimuli but its native module is capture/carry policy only
   — the discharge step should mirror ElecBug's `p2_emitter_accepts` +
   `stimulate(Interact<X>)` + accepted/immune log. Run7 re-proves the gas and
   electric receivers end-to-end through the natural fixed-hazard emitters, so the
   receiver side can prove attacks/receivers and death/corpse as natural.
3. **Gate tables** for Hiba 20 / GasHiba 21 / ElecHiba 22 in the ingest format with
   run7 log citations; `check_p2_handoff_gates.py` exit 0 (all three `role=hazard`,
   ignored — no refused PASS rows).
4. **`PIKMIN_NATIVE_ROOT` convention**: `tests/test_pikmin2_lanes_1012_policies.py`
   and `tests/test_pikmin2_hiba_native.py` now probe the native repo root via
   `PIKMIN_NATIVE_ROOT` (then `P2_NATIVE_PC_PORT`, then `ROOT/native`) and no
   longer probe `engine/` or hard-coded lane-worktree names (no lane paths in
   tests).

Reproduction (slice 2 head `11fb136c` / root `b99fba2`):

```powershell
py -3.12 output/deepseek-wave/build_lane.py l10
py -3.12 output/deepseek-wave/slot.py run build l10 -- py -3.12 -m experimental.pikmin2_hiba_runtime build --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l10 --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l10-build --output C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-fixture6 --head 11fb136c186317dbda6e568e6e9c5fddada8d726
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 output/deepseek-wave/slot.py run gl l10 -- py -3.12 -m experimental.pikmin2_hiba_runtime run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --output C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-run7 --exe C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/hiba-fixture6/build/fixture.exe
```

Subagent usage (slice 2):

1. **`explore` — source audit** of the receiver classes (`InteractFire/Bubble/Gas/Denki`),
   the immunity matrix, and the Otakara/ElecBug emitter status. Result **used
   as-is**: became the receiver-contract table, incl. the finding that Fire/Bubble
   use the P1 `startFire`/`PIKISTATE_Bubble` path while Gas/Denki match the decomp
   reaction states. Saved ~25 min.
2. **`explore` — candidate inventory** of the lane-07 seam (`pc_p2_reset_all_teki`
   -> `pc_p2_hiba_reset`), the hiba hook call sites, and the `PIKMIN_NATIVE_ROOT`
   convention. Result **used as-is**: confirmed the seam wiring and no existing
   scene-transition fixture (my gate-6 proof is a staged seam invocation), and
   gave the env-var helper to mirror. Saved ~20 min.
3. **`general` — validator + tests**: switched lanes-1012 policy tests to
   `PIKMIN_NATIVE_ROOT`, added the `reentry` gate + negative tests. Result **used
   with corrections**: I had to fix two caller rel strings the agent left pointing
   at `engine/…`/`native/…`/`output/…` (they had silently skipped), and I added the
   `pc_p2_hiba_hazard_count()` native hook + the `APP` re-entry block myself (out
   of its remit). Saved ~20 min, reclaimed ~5 min of correction.

Net: ~60 min of parallel work off the critical path.

## Review fixes 3

1. **Merged `claude/p2-deepseek-wave-native`** into `deepseek/p2-l10-native`
   (merge commit `762ed2e4`, +222 commits) so the receiver audit runs against the
   current wave, not the stale lane-10 snapshot.
2. **Receiver contract corrected (was audited against stale native).**
   `pc_p2_otakara.cpp` is the second integrated consumer, not policy-only: on the
   OtakaraBase Flick `attack1` frame-35 event, `dweevilAccepts` routes Fire/Water
   through `p2_species_immune` and Gas/Denki through `p2_emitter_accepts`
   (`:210`/`:211`), then `doDischarge` `stimulate(InteractFire/Bubble/Gas/Denki)`
   (`:238`/`:241`/`:244`/`:248`) and logs `P2_OTAKARA_DISCHARGE_IMMUNE`/`HIT`.
   `docs/PIKMIN2_LANE10_RECEIVER_CONTRACT.md` now cites `pc_p2_otakara.cpp:210-248`
   and `pc_p2_elecbug.cpp:665` and marks `P2_RECV_GAS/DENKI` as `PRINT` debug-only
   (`include/DebugLog.h:68`; run7 has 7 `P2_HIBA_GAS_HIT` + 1 `P2_HIBA_DENKI_HIT`
   and zero `P2_RECV_*`).
3. **Item 2 delivered (family emitter run on the merged native).** Ran
   `experimental/pikmin2_elecbug_denki_runtime` against the merged native
   (`nectar.exe` `ea12f423…`, fixture `8e9861d6…`): exit 0, all ten checks true —
   `P2_ELECBUG_DENKI emitter=sweep target=0 accepted=1 target_state=35(DenkiDying)`
   (natural ElecBug emission through the real `InteractDenki`, `native.log:913`),
   `P2_ELECBUG_IMMUNE` Yellow/Bulbmin (`:915-916`), `P2_DENKI_LETHAL` Blue dead +
   Yellow/Bulbmin alive with `violation=0` (`:929`). The receiver side therefore
   proves **attacks/receivers** (natural emitter -> accepted + DenkiDying + immune
   rejection) and **death** (electric-exclusive lethal path) as natural. The
   Otakara arena harness (`pikmin2_otakara_runtime.py`) is lane 22's and absent
   from this root; its `P2_OTAKARA_DISCHARGE` traffic is present under
   `output/dsw/l22-*` (lane 22 evidence), and its receiver code is above.
4. **Gate 6 re-labelled** `PASS (staged seam)` / `staged` (the trigger is fixture
   code calling `pc_p2_reset_all_teki()` + `pc_p2_hiba_setup()` from the idle loop;
   no real stage exit/re-entry). Noted that `pc_p2_hiba_setup()` self-resets
   (`pc_p2_hiba.cpp:292`), so "exactly once" is partly by construction; the probe's
   value is observing the reset clears (`h1=0`).
5. **Test style fix** — `_port_candidates()` in
   `tests/test_pikmin2_lanes_1012_policies.py` now uses a plain `if` (not the
   obscure generator-`yield` expression); 40 focused tests pass.

Reproduction (fix3: native `762ed2e4`, root `HEAD`):

```powershell
py -3.12 output/deepseek-wave/build_lane.py l10
py -3.12 output/deepseek-wave/slot.py run build l10 -- py -3.12 -m experimental.pikmin2_elecbug_denki_runtime build --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l10 --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l10-build --output C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/elecbug-denki-fixture --head 762ed2e42f38e31ee6e31721203d2a577d1176a4
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 output/deepseek-wave/slot.py run gl l10 -- py -3.12 -m experimental.pikmin2_elecbug_denki_runtime run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/ground" --output C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/elecbug-denki-run --exe C:/Users/alari/pikmin-randomizer/output/dsw/l10-out/elecbug-denki-fixture/fixture.exe --seconds 90
```

Subagent usage (fix3):

1. **`explore` — source audit** of the merged Otakara + ElecBug emitters, the
   `PRINT` no-op (`include/DebugLog.h:68`), and the run7 `P2_RECV_*` count. Result
   **used as-is**: gave the exact Otakara `dweevilAccepts`/`doDischarge` line
   numbers and confirmed `P2_RECV_*` is compiled out. Saved ~20 min.
2. **`explore` — candidate inventory** of the Otakara/ElecBug runtime harnesses and
   their asset requirements. Result **used as-is**: found `--imported` =
   `output/dsw/l14-out/ground` (exists) for the ElecBug denki fixture, and that the
   Otakara harness is lane-22's (absent here). Drove the decision to run ElecBug
   denki. Saved ~25 min.
3. **`general` — test fix**: `_port_candidates()` plain-if + pytest (13 passed).
   Result **used as-is**. Saved ~10 min.

Net: ~55 min of parallel work off the critical path.
