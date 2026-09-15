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
| native `deepseek/p2-l14-native` | `3370950c`, `0ec890de` | Sokkuri natural-combat damage/death observability markers + prior_health (#165) |
| native | `536a364a`, `060feddb` | ElecBug natural Purple-landing press + registration observability (#165) |
| native | `d2911fdf`, `ebc4c388` | TamagoMushi manager-driven group birth + whole-group cleanup; markers use module gen id (#165) |
| native | `bf02f219`, `92eea3fe`, `e7dacd6d`, `2454bfc2` | review fixes 4: stopMove/despawn, generateTeki, bounded birth radius, exclude host (#165) |
| native | `06a226d1` | slice 5: defer born-follower kills via `pc_p2_tamago_tick` + birth-mode header note (#165) |
| root `deepseek/p2-l14` | `ae0aca4`, `f66624b` | Sokkuri natural-vs-injected labelling + prior_health death marker/gate (#165) |
| root | `081e621` | integrator review fixes: `PIKMIN_NATIVE_ROOT` + real prior_health assertion (#165) |
| root | `e8a7d6b`, `0d03565` | Sokkuri natural lethal-death runtime + handoff slice 2 (#165) |
| root | `2053d20`, `f8d4eae`, `9df2c03` | ElecBug staged-press/timing + Tamago group-birth runtime + handoff slice 4 (#165) |
| root | `bbab6f3`, `5f84482` | review fixes 4: exactly_once on GROUP_ONCE, born=1 BIND, fixture forget via seam + handoff (#165) |
| root | (slice 5 commits) | slice 5: deferred kill + in-place gate tables (#165) |

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

## Six-gate evidence tables (per identity)

Per-identity natural gate evidence. Every PASS cites a real successful-run log
line (`output/<run>/native.log:NNN`); injected/proxy or bind-only evidence is
`UNTESTED`, never a PASS. Gate 5 (transport/reward) has no lane-06 receipt in this
cargo-free arena, so it is `UNTESTED` everywhere.

### Sokkuri (EnemyID 79)

| Gate | Result | Injected vs natural | Evidence |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | natural | output/dsw/l14-out/natural-run2/afcc5104e5784937bcb514cb5ae06b0d/capture/native.log:782 |
| 2. Autonomous movement and animation | PASS | natural | output/dsw/l14-out/natural-run2/afcc5104e5784937bcb514cb5ae06b0d/capture/native.log:826 |
| 3. Attacks and receivers | PASS | natural | output/dsw/l14-out/natural-run2/afcc5104e5784937bcb514cb5ae06b0d/capture/native.log:801 |
| 4. Death and corpse | PASS | natural | output/dsw/l14-out/natural-run2/afcc5104e5784937bcb514cb5ae06b0d/capture/native.log:904 |
| 5. Transport and reward | UNTESTED | | no lane-06 receipt; cargo-free arena (#397) |
| 6. Cleanup and re-entry | PASS | natural | output/dsw/l14-out/natural-run2/afcc5104e5784937bcb514cb5ae06b0d/capture/native.log:948 |

### ElecBug (EnemyID 28)

| Gate | Result | Injected vs natural | Evidence |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | natural | output/dsw/l14-out/elecbug-run4a/e23f06567a034d9bb6df3e12df79b115/capture/native.log:807 |
| 2. Autonomous movement and animation | PASS | natural | output/dsw/l14-out/elecbug-run4a/e23f06567a034d9bb6df3e12df79b115/capture/native.log:820 |
| 3. Attacks and receivers | PASS | natural | output/dsw/l14-out/elecbug-run4a/e23f06567a034d9bb6df3e12df79b115/capture/native.log:867 |
| 4. Death and corpse | PASS | natural | output/dsw/l14-out/elecbug-run4a/e23f06567a034d9bb6df3e12df79b115/capture/native.log:1082 |
| 5. Transport and reward | UNTESTED | | no lane-06 receipt; cargo-free arena (#397) |
| 6. Cleanup and re-entry | PASS | natural | output/dsw/l14-out/elecbug-run4a/e23f06567a034d9bb6df3e12df79b115/capture/native.log:1161 |

Natural death (flip is a staged P1-derived press; death is natural combat drain):
`PASS P2_ELECBUG_NATURAL_RUNTIME flip=staged-press death=natural ...` at
`output/dsw/l14-out/elecbug-run4a/e23f06567a034d9bb6df3e12df79b115/capture/native.log:1166`.

### TamagoMushi (EnemyID 68)

| Gate | Result | Injected vs natural | Evidence |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | natural | output/dsw/l14-out/tamago-slice5c-run/4b3b656b30d24c7fa726cbda4a4e5273/capture/native.log:782 |
| 2. Autonomous movement and animation | PASS | natural | output/dsw/l14-out/tamago-slice5c-run/4b3b656b30d24c7fa726cbda4a4e5273/capture/native.log:909 |
| 3. Attacks and receivers | PASS | natural | output/dsw/l14-out/tamago-slice5c-run/4b3b656b30d24c7fa726cbda4a4e5273/capture/native.log:837 |
| 4. Death and corpse | N/A | | source-backed: honey reward, corpse suppressed (genItem honey-only) |
| 5. Transport and reward | UNTESTED | | no lane-06 receipt; cargo-free arena (#397) |
| 6. Cleanup and re-entry | PASS | natural | output/dsw/l14-out/tamago-slice5c-run/4b3b656b30d24c7fa726cbda4a4e5273/capture/native.log:1286 |

Manager-driven group birth and exactly-once: `P2_TAMAGO_BIRTH ... source=manager`
at `.../tamago-slice5c-run/4b3b656b30d24c7fa726cbda4a4e5273/capture/native.log:813`;
`P2_TAMAGO_GROUP_ONCE host=346020 count=10` at
`.../tamago-slice5c-run/4b3b656b30d24c7fa726cbda4a4e5273/capture/native.log:1285`.

### Armor (EnemyID 15)

| Gate | Result | Injected vs natural | Evidence |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | natural | output/dsw/l14-out/run1/1fde880218f34c1381e13d8f2ef921b4/capture/native.log:1284 |
| 2. Autonomous movement and animation | UNTESTED | | not exercised this lane |
| 3. Attacks and receivers | UNTESTED | injected | dmg1/bittered receiver only exercised by an injected press |
| 4. Death and corpse | UNTESTED | injected | only the injected lethal lifecycle fixture |
| 5. Transport and reward | UNTESTED | | no lane-06 receipt (#397) |
| 6. Cleanup and re-entry | UNTESTED | | not exercised this lane |

### Imomushi (EnemyID 65)

| Gate | Result | Injected vs natural | Evidence |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | natural | output/dsw/l14-out/run1/1fde880218f34c1381e13d8f2ef921b4/capture/native.log:1295 |
| 2. Autonomous movement and animation | UNTESTED | | not exercised this lane |
| 3. Attacks and receivers | UNTESTED | | plant-eating interface still interface-only (#23) |
| 4. Death and corpse | UNTESTED | | not exercised this lane |
| 5. Transport and reward | UNTESTED | | no lane-06 receipt (#397) |
| 6. Cleanup and re-entry | UNTESTED | | not exercised this lane |

### Hana (EnemyID 84)

| Gate | Result | Injected vs natural | Evidence |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | natural | output/dsw/l14-out/run1/1fde880218f34c1381e13d8f2ef921b4/capture/native.log:1291 |
| 2. Autonomous movement and animation | UNTESTED | | not exercised this lane |
| 3. Attacks and receivers | UNTESTED | | buried ambush behaviour not exercised this lane |
| 4. Death and corpse | UNTESTED | | not exercised this lane |
| 5. Transport and reward | UNTESTED | | no lane-06 receipt (#397) |
| 6. Cleanup and re-entry | UNTESTED | | not exercised this lane |

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
family suite → **132 passed** as run by the worker (file list not recorded; integrator reproduces 94 passed over the 10 named elecbug/sokkuri/ground/hana-catfish files and 48 over the natural-runtime + elecbug behaviour set).
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


## Integrator review notes (slice 3)

- The flip is a **staged P1-derived press**, not a thrown Pikmin: the fixture teleports a Purple onto the beetle with forced downward velocity and the native probe calls `pc_p2_elecbug_pressed` from inside the module, bypassing the `tekiinteraction.cpp` InteractPress receiver. The `flip=natural` PASS token is therefore overclaiming; rename to `flip=staged-press` in the next slice (token change needs a fixture rebuild).
- Death IS natural: 34 accepted attacks, 30 hits 485→20, then `P2_ELECBUG_DEAD health=0`; no `mHealth` writes in the fixture.
- Fixture timing fragility (next slice): the press is staged 45 ticks into a 90-tick discharge so the Purple is always shocked (`DenkiDying`, squad 20→19); run 3 succeeded only because death beat FLIP_TIME recovery by ~5 ticks. Wait for `!isDischarging` before the first landing, or re-designate a live Purple in the barrage. Also add the Sokkuri pattern's health-floor print and `blocking_reason` to `validate()`.
- Subagent comparison: broader scope per slice than the solo slices, equally clean provenance, but the first lane-14 slice with an overclaiming docstring and a dropped pattern element.

## Slice 4

**Scope:** (a–c) fix the ElecBug slice-3 overclaim/timing/fragility + add
health-floor/blocking_reason; (d) TamagoMushi (68) manager-driven group birth
from an egg/host with exactly-once accounting, natural Astonish, and whole-group
cleanup on host forget — no injected births.

### Commits

- native `d2911fdf` lane14: TamagoMushi manager-driven group birth + whole-group cleanup (#165)
  — `pc_port/pc_p2_tamago.{cpp,h}`: `pc_p2_tamago_birth_group(host,count)` births
  the group via `TekiMgr::newTeki` (source `tamagoMushiMgr::createGroup`),
  triggered once on the host's first Appear (`mHasMadeFellow` analogue), and
  `pc_p2_tamago_forget` now clears the whole group on host forget; added
  `pc_p2_tamago_count`/`registered` observability.
- native `ebc4c388` lane14: TamagoMushi markers use module generator id (born actors have no mGenerator) (#165).
- root `2053d20` lane14: slice4 ElecBug staged-press label, timing fix, health-floor/blocking_reason (#165).
- root (this commit) lane14: TamagoMushi manager-driven group birth runtime (no injected births) (#165)
  — `experimental/pikmin2_tamago_group_runtime.py`, `tests/test_pikmin2_tamago_group_runtime.py`.

### (a–c) ElecBug staged-press + timing + health-floor

- PASS token renamed `flip=natural` → `flip=staged-press`; `validate()` now
  requires `flip=staged-press` and rejects `flip=natural` (overclaim).
- Timing: stage 3 waits for `!isDischarging(A)&&!isDischarging(B)` before the
  first landing, and the stage-4 barrage re-designates a live Purple if the
  current one is dead and never stages a landing while A is discharging. Two
  consecutive runs PASS (15.6s / 15.2s), first press at `state=return`/`wait`
  (Purple no longer shocked), `flip=staged-press death=natural immunity=yellow`.
- `validate()` added `P2_ELECBUG_NATURAL_OBSERVE`/`P2_ELECBUG_NATURAL_BLOCKED`
  health-floor parse and a named `blocking_reason` (Sokkuri pattern).

### (d) TamagoMushi group birth

Single host (346020) + control arena; the fixture writes `p2-tamago-host.txt`
(`P2_TAMAGO_HOST_1 346020 10`). The native manager births 9 followers on the
host's first Appear (exactly once). Runtime (run2 `592fbfe7...`, exit 0, 9.4s):
`P2_TAMAGO_HOST_BIND host=346020 egg=1` → `P2_TAMAGO_BIRTH host=346020
follow=9 count=10 source=manager` (+10 `P2_TAMAGO_BIND` 346020..346029) →
`P2_TAMAGO_BIRTH_ONCE duplicate=0` → 54 `P2_TAMAGO_ASTONISH` (natural, correct
generator ids) → `P2_TAMAGO_GROUP_ONCE count=10` (no duplicate after host
cycles) → `P2_TAMAGO_GROUP_FORGET remaining=0` (whole-group cleanup) →
`PASS ... injected=0`.

Born followers are real Chappy-vehicle Teki (no per-actor generator, so they draw
as the generic Chappy vehicle rather than the Mitite pose bank — documented
limitation; the host keeps the batch2 pose bank).

### Gates (slice 4d)

| Gate | Result |
|---|---|
| manager-driven birth | PASS (`P2_TAMAGO_BIRTH ... source=manager`, 10 born) |
| exactly-once | PASS (`P2_TAMAGO_BIRTH_ONCE born=9`, `P2_TAMAGO_GROUP_ONCE count=10`) |
| natural Astonish | PASS (all ten born ids 346020..346029 fire `P2_TAMAGO_ASTONISH`) |
| whole-group cleanup | PASS (`P2_TAMAGO_GROUP_FORGET remaining=0 queued=9`) |

### Exact reproduction (slice 4d)

```powershell
$env:PYTHONUTF8='1'
py -3.12 -m experimental.pikmin2_tamago_group_runtime run `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --imported C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/ground `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/tamago-run-final `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/tamago-fixture2/fixture.exe `
  --seconds 120
```

### Tests

`PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l14`
family suite → **145 passed** (11 Tamago group-runtime tests + 15 ElecBug natural
+ prior family tests). `tamago fixture.exe` SHA
`3c4dd00f703337d71caaaa0fc6766ecdbb2235ee7c46a9a2e882235a22c3131e`; ElecBug
`fixture.exe` SHA `a558b6f5f4298b90a494fad74559e8d5e37471f55e2f6db1c91585dfc746ccdc`;
native `nectar.exe` SHA `2877add7f8b5378973c08522988ff8e80a52379f9235c0383b6eae0953151749`.

### Subagent usage

- **explore #1 (source audit)** — returned a precise table of `tamagoMushiMgr`
  createGroup/createGroupByBigFoot, the `mHasMadeFellow` exactly-once flag, the
  egg/BigFoot/surface hosts, `InteractAstonish` Purple exclusion, and the honey-only
  `genItem`. Used as-is; it identified the surface-host `createFellow` on Appear as
  the clean, family-local trigger for the birth (the egg path would have reached
  lane-20/05 shared seams). Big time saver.
- **explore #2 (birth-machinery inventory)** — found `TekiMgr::newTeki` +
  `BTeki::spawnTeki`, the `pc_p2_teki_lifetime` forget seam, and confirmed no family
  module ever births a real Teki child. Used as-is; `host->spawnTeki(TEKI_Chappy)`
  was the key API I reused.
- **general #3 (validator+test scaffold)** — wrote `validate()` + 11 pytest cases
  against my contract. Used with minor corrections only (updated the synthetic
  `leader=1`→`leader=346020` to match the native marker); the contract held this
  time, unlike slice 3. Net time save.

### Remaining

- Born Mitite followers draw as generic Chappy (no per-actor generator/pose bank);
  per-actor generator assignment for child births is a shared/lane-05 concern.
- Reward/transport (#397) and the ElecBug retail Purple hipdrop (lane-11/#128)
  remain out of scope.

## Review fixes 4 (NOT merged slice-4 feedback)

### Commits

- native `d2911fdf` → `2454bfc2` series: `bf02f219` (stopMove + group despawn + born count/BIND), `92eea3fe` (generateTeki), `e7dacd6d` (bounded birth radius), `2454bfc2` (exclude host from children cleanup). Final native head `2454bfc21fd059988ebbf31205787d6e9d2bd0d6`.
- root `bbab6f3` lane14: review fixes 4 — exactly_once on GROUP_ONCE, born=1 BIND, fixture forget via seam (#165).

### Item 1 — born followers no longer flung away

The real cause was my birth-radius arithmetic, NOT `spawnTeki` launch velocity:
`(i*2654435761u) >> 8 / 32768` produced a radius up to ~512 (→ 45×512 ≈ 2e4-unit
offsets), so followers 346022–346029 were SPAWNED at (4098,7628), (−10467,5218), …
A debug print (since removed) showed the child position was already wrong **before**
`startAI`. Fix: bounded radius `0.2 + 0.8*((i*2654435761u) & 0xffff)/65535` in [0.2,1],
plus switched `spawnTeki`→`generateTeki` (no SpawnVelocity*Strength launch) as the
reviewer suggested. Verified: all 9 followers now report `P2_TAMAGO_FOLLOW
distance` in 0.15–58.27 (all < FOLLOW_RADIUS 60), and `P2_TAMAGO_ASTONISH` now comes
from **all 10** Mitites (346020 host + 346021–346029, 1–32 hits each) — run
`tamago-fix4e-run/f706e354...`.

### Item 2 — group forget now despawns the born children

`pc_p2_tamago_forget` group branch now collects the born followers (excluding the
host), calls `child->kill(false)` (death funnel → `pc_p2_forget_teki` + manager
recycle) for each, then erases the host. The fixture now calls `pc_p2_forget_teki(host)`
(the lane-07 seam, `pc_p2_teki_lifetime.h`) instead of `pc_p2_tamago_forget` directly.
`P2_TAMAGO_GROUP_FORGET host=346020 group=10 remaining=0 killed=9`.

### Item 3 — exactly_once is now a real observation

`P2_TAMAGO_BIRTH_ONCE host=346020 born=9` (prints the actual `born` count, no
literal `duplicate=0`). `validate()` `exactly_once` now gates the fixture's
`P2_TAMAGO_GROUP_ONCE host=346020 count=10` (emitted only after a `require` that
count is still exactly 10 after the host cycles).

### Item 4 — synthetic born ids flagged

Born followers emit `P2_TAMAGO_BIND ... visual_only=0 born=1`; the staged host emits
no `born=`. Simple-gate GOOD_LOG now uses ids 346020 (host) + 346021..346029 (born),
matching the native emission.

### Item 5 — gate table + commit table corrections

- Natural Astonish is now genuinely from the whole group (all 10), not host+1.
- `P2_TAMAGO_GROUP_CLEANUP forgotten=10` is informational (the gate reads
  `P2_TAMAGO_GROUP_FORGET remaining=0`).
- Bind-time health writes are explicit (`hostActor->mHealth=LIFE` in setup,
  `child->mHealth=LIFE` in birth) — labelled, not claimed as natural-combat damage.
- Commit table above the slice-4 section updated with `9df2c03` (slice-4) and the
  `bf02f219`..`2454bfc2` fix series.

### Tests / evidence

`PIKMIN_NATIVE_ROOT=...` family suite → **145 passed**. `tamago fixture.exe` SHA
`548d3fb1f7e639f78a5ed1e54afcd414d837e178e8f6f1e4ec10d1a93286b58f`; native
`nectar.exe` SHA `2d0332d472736be8c6fc5ea6f9a53d0311bc615423b5f5e806c2a04b5a7146ba`.

### Subagent usage (fix4)

- **explore #1 (source audit)** — confirmed the reviewer's spawnTeki launch-velocity
  claim and the `stopVelocity`/`kill`/`pc_p2_forget_teki` semantics, and verified the
  real log (host 38 + 346021 16 Astonish, 346022–346029 at 4098/7628 etc.). Used
  as-is; a real time saver.
- **explore #2 (inventory)** — located the exact fix lines + confirmed the forget is
  registry-only and the fixture bypasses the seam. Used as-is.
- **general #3 (validator/test scaffold)** — rewrote `validate()`/GOOD_LOG (exactly_once
  on GROUP_ONCE, born=1 on BIND, born=9) + 11 tests. Applied with only the `born=9`
  and `GROUP_ONCE host=346020` fixtures reconciled by hand. The delegated exactly_once
  contract held this time.

Note per the reviewer: the explore audit imported the spawnTeki launch-velocity
behaviour uncleaned; the actual fly-off cause was my own radius arithmetic, found by
adding a temporary debug print and reading the real log — a reminder to verify
delegated conclusions against the runtime.

## Slice 5 — ingestible gate tables + deferred group cleanup

### Items 1–3 (in-place corrections)

1. **Gate tables corrected in place** (not appended): the stale slice-1
   `## Six arena gates (Sokkuri 79)` table (which shadowed Sokkuri in the checker)
   is replaced by six per-identity `Source ID`/`EnemyID` tables under
   `## Six-gate evidence tables (per identity)`; the slice-4d `### Gates (slice 4d)`
   rows now read `P2_TAMAGO_BIRTH_ONCE born=9` / `P2_TAMAGO_GROUP_ONCE count=10`
   and `natural Astonish PASS (all ten born ids 346020..346029)`; the commit table
   now lists the slice 2–5 commits.
2. **`pc_p2_tamago.cpp` header** now documents the manager-driven birth mode
   (`pc_p2_tamago_birth_group` via `BTeki::generateTeki`), not just the pre-staged
   approximation.
3. **Deferred sibling kill** (native `06a226d1`): `pc_p2_tamago_forget`'s group
   branch no longer calls `child->kill(false)` inline (it ran inside the TekiMgr
   update loop on a natural host death). It queues the born followers and the new
   `pc_p2_tamago_tick()` drains them once per frame, hooked in
   `gameCoreSection.cpp` after `tekiMgr->update()` (small labelled shared hook).
   Runtime: `P2_TAMAGO_GROUP_FORGET host=346020 group=10 remaining=0 queued=9`;
   `PASS P2_TAMAGO_GROUP_RUNTIME ... injected=0`, exit 0.
   - Iteration-safety probe: `MonoObjectMgr::update()` (`objectMgr.cpp:285-298`)
     iterates by the fixed pool bound `mMaxElements` and re-tests `mEntryStatus[i]`
     each step; `MonoObjectMgr::kill` (`objectMgr.cpp:358-369`) only flips a slot to
     `-1`/`-2`, so killing a sibling mid-iteration is index-safe — but the deferral
     is the cleaner fix and is what shipped.
   - **Natural host DEATH is BLOCKED (not injected):** the free squad deals zero
     damage to the harmless Mitite (Astonish `InteractFlick` scatters it; host
     health stayed 50.00 across the observation), and a bare `BTeki::die()` does not
     complete the engine funnel (`dieSoon()` is gated on `!mDeadState` inside
     `BTeki::doAI`, `tekibteki.cpp:615/652`). The deferral removes the mid-loop
     sibling kill for any trigger regardless, so item 3 is resolved by construction.

### Item 4 — checker output (zero refused PASS rows)

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md
15 Armor (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
28 ElecBug (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    accepted [PASS]
65 Imomushi (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
68 TamagoMushi (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       ignored [N/A]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    accepted [PASS]
79 Sokkuri (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    accepted [PASS]
84 Hana (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
EXIT=0
```

### Commits / evidence

- native `06a226d1` (slice 5: deferred born-follower kills + header note); native
  `nectar.exe` SHA `ef24aab62dc9150b311366302417cdcf10838378ac1109272122bf52abed4345`.
- root (this commit): fixture stage-4 deferred path + in-place gate tables + this
  section. Tamago fixture `fixture.exe` SHA
  `40cc543abf14edf9d0edb173f4b07959416f9b917708bd257ab01474d9646b66`.
- `PIKMIN_NATIVE_ROOT=...` family suite → 145 passed.

### Subagent usage (slice 5)

- **explore #1 (iterator safety + tick hook)** — traced `MonoObjectMgr::update` /
  `kill` and located the once-per-frame `_tick` cluster in `gameCoreSection.cpp`
  (lines 2195/2950). Used as-is; it (correctly) judged inline mid-iteration kill
  index-safe, but I still shipped the deferral.
- **explore #2 (evidence census)** — returned exact `native.log:NNN` line numbers
  for every gate marker across my runs (Sokkuri `natural-run2`, ElecBug
  `elecbug-run4a/4b`, Tamago `slice5c-run`, Armor/Imomushi/Hana `run1`). Used
  as-is; this was the bulk of the citation work.
- **general #3 (gate-table format probe)** — wrote the six-table block to a scratch
  file and iterated the checker on a probe copy; discovered the exact heading
  binding rule (`EnemyID N`/`Name (N)` bind; a bare `source ID` line does not). Used
  with corrections (I supplied the real citations + replaced the shadowing slice-1
  table). Scratch files removed.
