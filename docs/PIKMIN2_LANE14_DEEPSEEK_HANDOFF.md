# Lane 14 (Ground invertebrates) — DeepSeek handoff

Tracking issue [#165](https://github.com/4laric/pikmin-randomizer/issues/165); parent [#407](https://github.com/4laric/pikmin-randomizer/issues/407).
Implementation owner: Codex through shared account `4laric`; executing agent/session: DeepSeek (lane 14, `dsw/l14-root`).

## Slice delivered

**Source IDs owned / inspected:** Sokkuri 79 (implemented), Armor 15, ElecBug 28,
Imomushi 65, TamagoMushi 68, Hana 84 (audited, unchanged).

**Concrete slice:** Sokkuri (EnemyID 79) — natural-combat **damage** observability
plus the injected death/corpse/cleanup/re-entry chain. Before this slice the
module could not distinguish a naturally-fought death from a fixture-injected
`mHealth=0`; both only logged `P2_SOKKURI_DEAD ... health=0`. The slice adds a
per-frame health tracker so real Pikmin attack damage and the injection signature
are separately observable and honestly labelled.

## Ordered commits

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Both clean at handoff.

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l14-native` | `3370950c` | Sokkuri death marker reports prior_health for combat-vs-inject distinction (#165) |
| native | `0ec890de` | Sokkuri natural-combat damage/death observability markers (#165) |
| root `deepseek/p2-l14` | `f66624b` | prior_health death marker + separate combat-damage gate (harness+tests+doc) (#165) |
| root | `ae0aca4` | Sokkuri natural-vs-injected death labelling (harness+tests+doc) (#165) |

Dirty state: none (both clean).

## Interfaces / hooks touched and why

Only the family-owned `pc_port/pc_p2_sokkuri.cpp` changed (16 inserts and a
9-line revision). No shared file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`, CMake) was
edited — the Sokkuri module is already registered and hooked. The change is
read-only observability:

- `P2_SOKKURI_DAMAGE generator=%u source_id=79 health=%.1f` — incremental,
  still-positive health decrease = natural Pikmin attack damage.
- `P2_SOKKURI_DEAD ... health=0 prior_health=%.1f` — health one update before
  death, so a single injection (large `prior_health`) is distinguishable from a
  combat-culminated death (small `prior_health`).

Root: `experimental/pikmin2_ground_lifecycle_behavior.py` (validator +
`combat_damage` gate), `tests/test_pikmin2_ground_lifecycle_behavior.py`
(new tests + native-worktree path resolution), `docs/PIKMIN2_SOKKURI_NATURAL_COMBAT.md`.

## Build evidence (`output/dsw/l14-build-evidence.txt`)

- Native head `3370950c54caf9995d8580af18c4d8c729d6cda9`, clean.
- `nectar.exe` SHA-256 `855e50aeba0ffab7a6cd8915364e24e9261a516aa4a551f7e56ba077325d671f`.
- `ninja -n` → `ninja: no work to do.` (fresh).
- Config: Ninja + MinGW g++ 16.2.0, Release, `PIKMIN_NATIVE_JAUDIO=ON`
  (the OFF default fails to link on `Jac_NoteDemoSkipped`; configured once with
  `-DCMAKE_MAKE_PROGRAM=<python ninja>` then built through `build_lane.py`).
- Private replacement-main fixture `fixture.exe` SHA-256
  `d2df8045d4d7c20b365bae0dc8a568de33ef2bf8fbfe25708281cfed99f9c0bf`
  (`instrumentation.json` status `built`).

## Fixture adoption evidence

- Window: native.log `Experimental preview window set to 960x540 windowed and centered`.
- Live squad: `P2_LIFECYCLE_READY squad=20 sokkuri_gen=346005 armor_gen=346001`.
- No extinction; run exit 0.
- Run dir: `output/dsw/l14-out/run2/2c10ec7097254c3e84f0a1ca957ac935`.

## Six arena gates (Sokkuri 79)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0` |
| 2. Autonomous movement + animation | PASS (source-backed) | `P2_SOKKURI_STATE state=appear/flick`; prior sokkuri run evidence; not re-verified here |
| 3. Attacks / receivers | natural damage PASS; lethal injected | `P2_SOKKURI_DAMAGE health=105.0` (natural squad attack); `P2_LIFECYCLE_INJECT not_natural_combat=1` (lethal step injected) |
| 4. Death + corpse | PASS (injected lethal) | `P2_SOKKURI_DEAD prior_health=105.0`; `P2_LIFECYCLE_CORPSE species=Sokkuri pellet=1` |
| 5. Transport + reward | UNTESTED (deferred #397) | cargo-free arena, no Pod; source carry clip `type5` exists → not source-backed N/A |
| 6. Cleanup + re-entry | PASS (generator re-bind) | `P2_LIFECYCLE_FORGET count=0`; `P2_LIFECYCLE_REENTRY stale=0 fresh=1 count=1` |

Injected vs natural is labelled: injected lethal step is explicit
(`P2_LIFECYCLE_INJECT ... not_natural_combat=1`, `injected=1` completion marker);
natural combat **damage** is separately proven by `P2_SOKKURI_DAMAGE`. A natural
**lethal** death (health fully drained by combat, no injection) is still open.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_{ground_lifecycle,sokkuri,armor,armor_receiver}_behavior.py -q`
→ 40 passed. Full family suite
(`test_pikmin2_{ground*,sokkuri*,armor*,elecbug*,imomushi*,hana*,tamago*}.py`)
→ 112 passed.

## Assumptions

- Incremental health decrease == natural combat damage (Pikmin throw/retaliation);
  a single jump to 0 == injected lethal step (signature: large `prior_health`).
- The cargo-free private arena has no Onion/Pod, so reward is untested (not N/A).
- The Skitter Leaf is harmless (attack params zeroed); its only receiver is Flick,
  so a natural *lethal* kill needs the squad to fully drain 120 HP without the
  fixture's injection — not achieved in this bounded run.

## Remaining blockers (named provider)

- Natural lethal death + true natural re-entry beyond generator `init`: needs lane
  33/07 (lifecycle, #397) and a non-injecting natural-combat fixture; the P1 proxy
  AI alone did not fully drain the enemy within the observation window.
- Actual transport/reward: lane 06 / #397 (Pod/Onion endpoint not present in the
  cargo-free arena).
- Pair discharge (ElecBug 28) and Mitite group births (TamagoMushi 68) remaining
  evidence are tracked separately in this family; ElecBug/Damago modules are
  implemented but not re-exercised here.

## Exact reproduction

```powershell
$env:PYTHONUTF8='1'
py -3.12 -m experimental.pikmin2_ground_lifecycle_behavior run `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --imported C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/ground `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/run-final `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/fixture2/fixture.exe `
  --seconds 150
```

(Prerequisite, already done once: extract `ground` bank
`py -3.12 -m experimental.pikmin2_ground_inverts_assets --iso "<P2 disc>" --source "<pikmin2-research checkout>" --output ...`;
build `fixture.exe` via `... build --native .../native-l14 --build-dir .../native-l14-build --head 3370950c54caf9995d8580af18c4d8c729d6cda9`.)

## Slice 2

**Source ID:** Sokkuri 79. **Slice:** natural lethal death — the live 20-red
squad fully drains Sokkuri's 120 HP through the real `InteractAttack` receiver
with **no injected health**, then corpse → cleanup → re-entry.

### Commit (root)

- `e8a7d6b` lane14: Sokkuri natural lethal-death runtime (no injected health) (#165)
  — `experimental/pikmin2_sokkuri_natural_runtime.py`,
  `tests/test_pikmin2_sokkuri_natural_runtime.py`.
- Native: no change this slice (unchanged at `3370950c`); the slice-1
  `P2_SOKKURI_DAMAGE`/`prior_health` markers are consumed directly.

### What was investigated / fixed

- Why the slice-1 run stalled at 105 HP: the fixture injected at `observed>=30`
  (≈1 s) — it never gave the squad time; a single `P2_SOKKURI_DAMAGE` (120→105)
  was the only combat damage before injection.
- Fix (arena/fixture, no enemy stat change, extinction untouched): a
  Sokkuri-only ground roster (`p2-ground-actors.txt` = only `346005 Sokkuri`) so
  the hostile Armor/ElecBug neighbours can't eat/scatter the squad, free-mode
  deploy (`changeMode(PikiMode::FreeMode)`) of the 20 reds in a 16-unit ring
  around the Sokkuri, and #128 `normalize_pose_names` applied to the Sokkuri-only
  bank (`appear1` pose `_01`→`_00`).

### Natural lethal-death evidence (run `l14-out/natural-run2/afcc5104...`)

`P2_SOKKURI_DAMAGE` 90.0 → 75.0 → 60.0 → 45.0 → 30.0 → 15.0, then
`P2_SOKKURI_DEAD ... prior_health=15.0` (6 combat hits, small prior, no
`not_natural_combat` marker), `P2_SOKKURI_NATURAL_CORPSE pellet=1`,
`P2_SOKKURI_NATURAL_FORGET count=0`, `P2_SOKKURI_NATURAL_REENTRY stale=0 fresh=1
count=1`, `PASS P2_SOKKURI_NATURAL_RUNTIME ... injected=0`. Exit 0, elapsed 10.3s.
The flick knockback fires repeatedly (frame 18) but free-mode Pikmin re-engage and
drain; blocking mechanism not triggered.

### Gates (slice 2)

| Gate | Result |
|---|---|
| 3. Attacks/receivers | natural PASS (`P2_SOKKURI_DAMAGE` sequence) |
| 4. Death + corpse | natural PASS (`prior_health=15.0`, corpse pellet) |
| 6. Cleanup + re-entry | PASS (`forget count=0`, fresh re-bind `stale=0`) |

`no_inject` check confirms no `mHealth` write anywhere (`mHealth=0.0f` absent from
the instrumented source).

### Exact reproduction (slice 2)

```powershell
$env:PYTHONUTF8='1'
py -3.12 -m experimental.pikmin2_sokkuri_natural_runtime run `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --imported C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/ground `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/natural-run-final `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/natural-fixture/fixture.exe `
  --seconds 150
```

### Tests

`PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l14`
family suite → **119 passed** (7 new natural-runtime tests).
`fixture.exe` SHA `466ca847b95e07ee37aac487129be88740d470a29fd4212882b10d7304a47959`.

### Remaining

- True natural re-entry without the fixture's `mGenType->init` remains a
  lifetime-lane (#397) concern; the slice proves fresh re-bind after a natural
  death.
- Reward/transport still UNTESTED (cargo-free arena, #397).
- ElecBug pair discharge + TamagoMushi group births remain for later slices.

## Slice 3

**Source ID:** ElecBug 28. **Slice:** natural press-to-flip → lethal death →
Yellow discharge-immunity → corpse/cleanup/re-entry, with no injected health or
state.

### Commits

- native `536a364a` lane14: ElecBug natural Purple-landing press + registration observability (#165)
  — `pc_port/pc_p2_elecbug.{cpp,h}`: `pc_p2_elecbug_check_landing_press` (family-
  local `pressCallBack` adaptation: a descending Purple overlapping the beetle
  flips it via the existing `pc_p2_elecbug_pressed`), plus `pc_p2_elecbug_count`
  /`registered` observability mirroring Sokkuri/Armor. No shared file touched.
- root `c5115e6` lane14: ElecBug natural press-to-flip→death runtime (no injected state) (#165)
  — `experimental/pikmin2_elecbug_natural_runtime.py`, `tests/test_pikmin2_elecbug_natural_runtime.py`.

### What was implemented / investigated

- The P1 host has **no Pikmin→enemy `InteractPress`** emission (P1 thrown Pikmin
  stick via `InteractAttack`; `InteractPress` in P1 is only enemy→Pikmin). The
  prior immunity fixture therefore injected `pc_p2_elecbug_pressed` directly.
- Slice 3 adds a family-local natural probe: `pc_p2_elecbug_check_landing_press`
  runs in `pc_p2_elecbug_update` and, when a Purple Pikmin
  (`pc_p2_species(p)==P2SpeciesPurple`) is descending (`mVelocity.y<-0.01`) within
  30 units of the beetle, delegates to the source-equivalent press receiver.
  P1-derived, logged `P2_ELECBUG_NATURAL_PRESS`; no shared lane-11 Purple edit.
- The pair-discharge/immunity race: the Purple kept landing during Charge and
  breaking the pair before discharge. Fixed by parking Purple+reds far away until
  the pair discharges (Yellow parked at the pair midpoint survives, being
  electric-immune), then staging the Purple landing in a barrage so the beetle
  stays flipped until the 500 HP drain completes.

### Runtime evidence (run `l14-out/elecbug-run3/6be6f3e6...`, exit 0, 14.9s)

`P2_ELECBUG_IMMUNE ... pikmin=yellow species=2` (Yellow immune to the natural
pair discharge) → `P2_ELECBUG_NATURAL_PRESS ... state=discharge` +
`P2_ELECBUG_FLIP` + `state=reverse` (natural Purple press flipped a discharging
beetle) → 30 `P2_ELECBUG_HIT` steps (485→20) → `P2_ELECBUG_DEAD health=0` →
`P2_ELECBUG_NATURAL_CORPSE pellet=1` → `P2_ELECBUG_NATURAL_FORGET count=1` →
`P2_ELECBUG_NATURAL_REENTRY ... stale=0 fresh=1 count=2` → `PASS ...
injected=0`. No `mHealth=` write anywhere in the instrumented source.

### Gates (slice 3)

| Gate | Result |
|---|---|
| (a) natural press→flip | PASS (Purple landing → `P2_ELECBUG_FLIP` + `state=reverse` + `P2_ELECBUG_NATURAL_PRESS`) |
| (b) vulnerability → lethal | PASS (30 `P2_ELECBUG_HIT` → dead) |
| (c) Yellow immunity | PASS (`P2_ELECBUG_IMMUNE ... pikmin=yellow species=2`) |
| (d) corpse/cleanup/reentry | PASS (corpse + forget + generator re-bind) |

Purple species deployed at runtime via lane-11 `pc_p2_set_species(p,
P2SpeciesPurple)` storage; the landing press is documented P1-derived.

### Exact reproduction (slice 3)

```powershell
$env:PYTHONUTF8='1'
py -3.12 -m experimental.pikmin2_elecbug_natural_runtime run `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --imported C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/ground `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/elecbug-run-final `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/elecbug-fixture3/fixture.exe `
  --seconds 120
```

### Tests

`PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l14`
family suite → **132 passed** (13 ElecBug natural-runtime tests).
`fixture.exe` SHA `0a318e60132188fecf2be639cdedc56d26fafc00ed89641497fdadccc1996af7`;
native `nectar.exe` SHA `765fc8d01d59ecf452b08311a0dcd68a44d18d0aae31bd6e4899d0e8b6502a8a`.

### Subagent usage

- **explore #1 (source audit)** — returned a precise source-facts table
  (`pressCallBack`, Purple `hipdropCallBack`, `StateReverse` invulnerability,
  `InteractDenki` Yellow/Bulbmin border, `becomePellet`). Used as-is; it correctly
  flagged the missing P1-host `InteractPress` routing, which shaped the
  landing-probe design. Estimated saving: large (I would have had to grep the decomp
  myself for the press/hipdrop wiring).
- **explore #2 (candidate inventory)** — confirmed the immunity fixture already
  injected the flip, listed every `pc_p2_*` marker, and the `pc_p2_set_species` /
  `pc_p2_make_purple` deployment API. Used as-is; the `pc_p2_set_species`
  discovery let me deploy Purple/Yellow without reading lane-11 sources.
- **general #3 (validator + test scaffold)** — wrote `validate()` + 12 pytest
  cases against the marker contract I supplied. Used with corrections: I expanded
  the marker contract (added `P2_ELECBUG_NATURAL_PRESS` to `natural_flip`,
  pair-aware counts, second BIND) and replaced the "scaffold-only" placeholder
  with the actual `APP`/`prepare`/`instrument`/`build`/`run`, then updated the
  tests. Estimated: saved the boilerplate but the contract churn meant I still
  edited both files substantially.

### Remaining

- TamagoMushi group births and any further reward/transport remain for later
  slices (#397 for reward/lifetime).
- The press is P1-derived (documented); retail Purple hipdrop physics is
  lane-11/#128 scope.
