# Lane 10/11: natural ElecBug electrical emitter through the P2 receivers

Lanes 10 (receivers) and 11 (species/Bulbmin) of
[PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md), paired with
the lane 14 Anode Beetle (ElecBug, source id 28). Parent issues
[#408](https://github.com/4laric/pikmin-randomizer/issues/408) (receivers) and
[#131](https://github.com/4laric/pikmin-randomizer/issues/131) (species).
Implementation owner: Codex through shared account `4laric`; executing agent:
`opencode-go/deepseek-v4.1-flash`.

This slice closes the next-wave gate that the receivers lane had left as
"LTO retention or direct API injection": the electrical interaction is now
produced by the **acting family emitter** (the source two-beetle Discharge
sweep), delivered to the real lane-10 `InteractDenki` receiver, and gated by the
lane-11 species capability matrix. It is the first paired lane 10 + 11 + family
natural emitter test.

## What changed

### Native (lane 10 contract + family consumer)

- **Lane 10 `pc_port/pc_p2_hazard_emitter.h`** — a named, header-only
  emitter/attack-volume contract. `p2_emitter_accepts(species, hazard,
  gasInvincible)` is the *same* `p2_hazard_reaction` table the Pikmin receiver
  consults, so an emitter and its receiver cannot disagree about immunity.
  Pinned by `tools/test_p2_hazard_emitter.cpp` (`PASS P2_HAZARD_EMITTER`).
- **`pc_port/pc_p2_elecbug.cpp`** — the Discharge/ChildDischarge sweep is the
  emitter. It no longer uses `InteractKill` and no longer enforces Yellow with a
  colour literal; it selects the nearest target with
  `p2_hazard_reaction(pc_p2_species(p), P2HazardElectric, ...)` (via the
  emitter contract) and delivers the real `InteractDenki`. The same path is used
  by the press-to-flip discharge. The emitter logs the receiver's return value
  and the target's resulting state, and emits one `P2_ELECBUG_IMMUNE` marker per
  rejected immune species (Yellow, Bulbmin) inside the sweep.

### Root (runtime gate)

- `experimental/pikmin2_elecbug_denki_runtime.py` — instrumented
  replacement-main fixture. It stages two registered ElecBugs (source 60-unit
  pair inside the 300-unit pairing radius and the 200-unit sight radius of the
  squad), marks the whole starting squad electric-immune except one Blue (so
  matrix-based target selection can only resolve to Blue), and parks Yellow,
  Bulbmin and Blue inside the source 70-unit sweep while a beetle is
  discharging. It observes the Blue target's `PIKISTATE_DenkiDying` and its
  death directly. The emitter shock and receiver are **native**; only the
  recolouring and the positioning are fixture actions.
- `tests/test_pikmin2_elecbug_denki_runtime.py` — validator unit tests, including
  the failure modes (injected receiver, immune target, missing Bulbmin marker,
  missing lethal path, immune reaction state).

## Natural runtime evidence

Fixture/runtime exe SHA-256
`1F230F40A5492C7C4DAF5D72BB4B3739C38EB448D6C7DC4F2C8699ED1EA057C4`.
Native `nectar.exe` SHA-256
`E0FF74BC66E1F36867A657C060986E633E3E8C0EA2DB9DED79D6C1ED3DE42311`.
Run directory
`output/p2-lanes1011-elecbug-denki-run-02/ccff4c8e64854f70bb8ec2b710f59a03/`
(`capture/native.log`, `elecbug-denki-validation.json`).

```text
Experimental preview window set to 960x540 windowed and centered
P2_DENKI_SQUAD alive=20 reds=18 yellow=2 bulbmin=5 blue=0
P2_ELECBUG_BIND generator=346002 source_id=28 visual_only=0
P2_ELECBUG_BIND generator=346008 source_id=28 visual_only=0
P2_ELECBUG_LINK generator=346002 partner=346008
P2_ELECBUG_DENKI generator=346002 source_id=28 emitter=sweep target=0 accepted=1 target_state=35(DenkiDying)
P2_ELECBUG_IMMUNE generator=346002 source_id=28 pikmin=yellow species=2
P2_ELECBUG_IMMUNE generator=346002 source_id=28 pikmin=bulbmin species=5
P2_DENKI_ACCEPT target=blue yellow_state=0 bulbmin_state=0 observed=101
P2_DENKI_LETHAL target=blue alive=0 yellow_alive=1 yellow_state=0 bulbmin_alive=1 bulbmin_state=0 violation=0 observed=111
PASS P2_ELECBUG_DENKI_RUNTIME
```

Interpretation: the emitter's matrix-based selection resolved to Blue
(`target=0`); the lane-10 receiver accepted it (`accepted=1`) and the target
transited `PIKISTATE_DenkiDying` (`target_state=35`); Yellow and Bulbmin were
inside the sweep and were rejected (`P2_ELECBUG_IMMUNE`); the shock target then
ran the source lethal pipeline (`DenkiDying -> Dead`); neither immune species
entered `DenkiDying` (`violation=0`); no extinction.

## Gates

| Gate | Result |
|---|---|
| A Identity/content | PASS — two ElecBug source ids 28 bound at their generators, 20-Pikmin live squad |
| B Source behavior | PASS — pair link, Charge/ChildCharge -> Discharge/ChildDischarge |
| C Combat/receivers | PASS — natural emitter -> real `InteractDenki`; valid hit accepted and lethal; Yellow/Bulbmin rejected |
| D Death/drop/transport | PASS (death) — `DenkiDying -> Dead`; corpse/transport is the family lane's remaining work |
| E Lifetime | UNTESTED in this slice — no scene exit/re-entry run |
| F Persistence | schema-validated (see below); live cave save/load not run here |
| G Product/mixed scene | NOT reached — arena is an engineered fixture, not production placement |

## Lane 11 capability routing and checkpoint schema

- Species routing is the lane-11 matrix: `p2_species_capability` /
  `p2_species_immune` decide the emitter target and the receiver; Yellow =
  electric-immune, Bulbmin = all-hazard immune, Red/Blue/Purple/White affected.
  `PASS P2_SPECIES_POLICY`, `PASS P2_HAZARD_REACTION`, `PASS P2_HAZARD_EMITTER`,
  `PASS P2_ELEMENTAL_RECEIVERS` on this tree.
- Checkpoint persistence is the versioned schema `pc_p2_species_schema.h`
  (v1 Purple, v2 White, v3 Bulbmin) wired into `pc_p2_cave.cpp`
  (`P2_CAVE_ENTRY_3`). `PASS P2_SPECIES_SCHEMA` proves old readers keep their
  behavior and reject a newer species explicitly, and totals are conserved.
  A live cave save/load restart run is **not** part of this slice.

## Reproduction

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
cmake --build output/native-lanes1011-elecbug-build --target pikmin_pc -j 6
py -3.12 -m experimental.pikmin2_elecbug_denki_runtime build `
  --native output/native-lanes1011-elecbug `
  --build-dir output/native-lanes1011-elecbug-build `
  --output output/p2-lanes1011-elecbug-denki-fixture2 `
  --head eddbf832e0f24f24266c05a1e1af919bcc3636ad
py -3.12 -m experimental.pikmin2_elecbug_denki_runtime run `
  --assets output/release-lynk-graphics-post/assets `
  --imported output/p2-lane-verify/ground `
  --output output/p2-lanes1011-elecbug-denki-run-03 `
  --exe output/p2-lanes1011-elecbug-denki-fixture2/fixture.exe --seconds 90
```

## Base composition and limits

- Native `opencode/p2-lanes1011-elecbug` = `opencode/p2-submerged-native`
  (`3d65f611`, lanes 10-12) merged with `opencode/p2-species-elecflip`
  (`3ae68101`, species umbrella incl. ElecBug), then the focused commits:
  `058b67fc` (emitter contract), `c94cd610` (ElecBug receiver + immunity),
  `d345b108` (accept/state logging), `eddbf832` (per-species immunity marker).
- Root `opencode/p2-lanes1011-root` = `opencode/p2-submerged-root` (`c03be34`)
  plus the copied ElecBug harness tooling and the new denki runtime gate.
- This is a private candidate, not a lane-01 integrated build. Lane 01 must
  reconcile it; it pulls the lane 14 ElecBug actor (not otherwise in the
  lanes 10-12 candidate).
- Port adaptations retained: nearest (not uniform-random) partner selection; the
  interaction is delivered to a single nearest shockable target rather than a
  full line sweep; no electric effect particles. The Chappy placement vehicle,
  not a native `ElecBug` actor class, still hosts the behavior.
- Remaining: lane 14 corpse/transport/re-entry; lane 11 live restart; generated
  seed/installation and mixed-scene budgets (lanes 03/05/33).
