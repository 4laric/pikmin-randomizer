# Lane 07 (Lifetime/fixtures) — DeepSeek handoff (review fix 1)

Tracking issue: [#397](https://github.com/4laric/pikmin-randomizer/issues/397); coordination [#186](https://github.com/4laric/pikmin-randomizer/issues/186).
Implementation owner: Codex through shared account `4laric`; executing agent/session: DeepSeek (lane 07, `dsw/l07-root`).

This revision addresses the review of the first handoff: it stops forking the lane's
own reusable harness, drops the fixture `*_forget`, makes the ENGINE `doKill ->
pc_p2_forget_teki` seam the forget authority on a natural death, and honestly
reports the address-reuse / manager-reset legs.

## Slice delivered

**Consumer (one live family):** Dwarf Orange Bulborb — species `BlueKochappy`,
source_id `44`, native module `pc_p2_dwarf_orange` (generator id `211001`), with
an ordinary P1 Chappy control (`211002`).

**Concrete slice:** add `dwarf-orange` to the reusable lane-07 lifecycle harness
(`experimental/pikmin2_lifecycle_runtime.py`) and drive it through the engine
lifetime seam — **no fixture `_forget` call anywhere**. The harness:

1. Natural death through the real damage receiver (repeated `InteractAttack`;
   the lethal damage value `100000` is the injected part of an otherwise real hit).
2. **Corpse retains registration** at death (`P2_LIFECYCLE_FORGET
   registered_at_death=1`): the engine does *not* prematurely clear a
   corpse-leaving `TEKI_Chappy`, whose `doKill` runs at corpse disposal.
3. Injected corpse disposal (`corpsePtr->kill(false)`) reaches
   `Pellet::doKill -> BTeki::viewKill -> kill -> doKill -> pc_p2_forget_teki`,
   so `registered_after_dispose=0` is the **engine** clearing the map, not the
   fixture. (Disposal trigger is injected only because the cargo-free arena has
   no Onion/Pod to dispose the corpse naturally.)
4. **Address reuse** (`P2_LIFECYCLE_REENTRY ... reused=1`): driving death through
   `dieSoon` (instead of a raw `kill(false)`) correctly detaches the generator
   via `informDeath`, so the freed pool slot is handed straight back to the
   generator re-birth at the *same* address.
5. Late birth + clean re-registration (`P2_ENEMY_READY` emitted a second time;
   `rebound`), and the control actor unaffected (`control=1`).

## Ordered commits

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`.

| Branch | Commit | Subject |
|---|---|---|
| root `deepseek/p2-l07` | `16d4599` | lane07: Dwarf Orange engine-driven lifetime/re-entry probe (forget/rebind/late-birth) (#397) — *superseded/retired by the review fix* |
| root | `23374f7` | lane07: handoff doc for Dwarf Orange lifetime/re-entry slice (#397) — *superseded by this doc* |
| root | `(this fix)` | lane07: review fixes — generalize shared harness for dwarf-orange, drop fixture forget, retire standalone module (#397) |

Native `deepseek/p2-l07-native`: **no commits** (the shared seam is already at
the pinned base; no native source change was needed). Both worktrees clean.

## Interfaces / hooks touched

- `experimental/pikmin2_lifecycle_runtime.py` (lane-07-owned shared harness):
  added `dwarf-orange` to `FAMILIES`, a `FAMILY_HOOKS` mapping (batch2+long-legs
  for the original three families; `pc_p2_dwarf_orange_*` for dwarf-orange),
  `--family` on `build`, `--bank`/`--profile` on `run`, and a dwarf-orange
  `_arena()` branch that normalizes the family manifest (`control`,
  `native_teki_type=3`). Removed the explicit `pc_p2_batch2_forget`/
  `pc_p2_long_legs_forget` fixture call; replaced it with an engine-observed
  corpse-disposal forget. `find()` now checks `isAlive()`.
- `tests/test_pikmin2_lifecycle_runtime.py`: updated the FORGET markers and added
  no-fixture-forget / dwarf-orange routing / dwarf-orange validate tests.
- Retired `experimental/pikmin2_dwarf_orange_lifetime.py` and its test (the
  forked module this review objected to). Its behaviour is now covered by the
  reusable harness.
- No shared engine file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
  `tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`, CMake)
  was edited.

## Build evidence (`output/dsw/l07-build-evidence.txt`)

```
2026-09-14T19:44:59 lane=l07 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no
  build_dir=.../native-l07-build exe=.../bin/nectar.exe
  sha256=2d507c6cf0a827ce4bbf4e3beb22aac1998b1bf310f90bf4005048388921accc ninja_n="ninja: no work to do." seconds=147
```

- Native head `b805d9c6` (clean), Ninja + MinGW g++ 16.2.0, Release, `PIKMIN_NATIVE_JAUDIO=ON`, LTO.
- `nectar.exe` SHA-256 `2d507c6cf0a827ce4bbf4e3beb22aac1998b1bf310f90bf4005048388921accc`.
- Replacement-main dwarf-orange fixture SHA-256 `f8f55cc79b21c9abf79ac243f76a7aee85371f570e136a87a7d59533b638acd1` (`provenance.json` status `built`).

## Fixture adoption evidence

- Window: `Experimental preview window set to 960x540 windowed and centered`.
- Live squad: `P2_LIFECYCLE_SQUAD alive=20`.
- No extinction; exit 0.
- Run dir: `output/dsw/l07-out/lf-run/d9954e2348314db683cbce6bbe56161b`
  (native.log SHA-256 `343f87ffa6feedcf74369053285ffd6229c7abcf0894ac4da64e451a711b6009`).

## Six arena gates (Dwarf Orange 44)

| Gate | Result | Evidence (natural vs injected) |
|---|---|---|
| 1. Identity + spawn | PASS (natural) | `P2_ENEMY_READY species=BlueKochappy source_id=44 generator=211001 x=-150 y=30 z=1850 health=250.0 max_health=250.0` |
| 2. Autonomous movement + animation | PASS (observed) | `P2_LIFECYCLE_MOVE id=211001 dist=4.062`; `P2_DWARF_ORANGE_DRAW` present |
| 3. Attacks + receivers | natural receiver, injected lethal value | `P2_LIFECYCLE_ATTACK accepted=1 health=250.0 -> 0.0` (real `InteractAttack` receiver; value injected) |
| 4. Death + corpse | death natural(receiver); disposal injected; engine forget | `registered_at_death=1` (corpse retains) -> `registered_after_dispose=0 engine=doKill` |
| 5. Transport + reward | N/A | cargo-free arena, no Onion/Pod; lane 06 |
| 6. Cleanup + re-entry | **PASS** | engine forget (`engine=doKill`), address reuse (`reused=1`), late birth (frame 128), control `=1` |

Completion marker `PASS P2_LIFECYCLE_RUNTIME` (exit 0).

## Review-item dispositions

1. **Reuse the shared harness + drop fixture forget + retire the fork** — done:
   `--family dwarf-orange` now routes through `pikmin2_lifecycle_runtime.py`; no
   fixture `*_forget` remains; the standalone module and its test are deleted.
2. **Address-reuse leg non-vacuous** — the natural-death path now deterministically
   reuses the freed slot (`reused=1`), and `registered_before_rebind` is no longer
   the proof: the proof is `registered_after_dispose=0` (engine) + `reused=1`.
   No `reuse_clean`/`same_address` gated field remains.
3. **"No manager reset" corrected** — `pc_p2_dwarf_orange_setup()` begins with
   `pc_p2_dwarf_orange_reset()` (`pc_p2_dwarf_orange.cpp:33-34`), so the re-entry
   re-registration IS a family-level re-setup, not a bare rebind. The ledger legs
   "repeatable teardown" and "manager reset vs full scene/day/restart" remain OPEN.
4. **`find()` checks `isAlive()`** — the harness `find()` now requires
   `a->isAlive()`, so the pooled dead `TEKI_Chappy` no longer competes on
   iteration order.
5. **Repro path corrected** — the reproduction below writes a fresh uuid subdir
   under `l07-out/lf-run-fix1` (it does not read a pre-existing `run-final`).
6. **Plain import** — the retired module's test is deleted alongside the module.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_lifecycle_runtime.py -q` -> **9 passed**.
Focused battery (`test_pikmin2_lifecycle_runtime.py` +
`test_pikmin2_dwarf_orange_{chain,runtime}.py` + `test_pikmin2_dwarf_orange.py`)
-> **50 passed**.

## Assumptions

- `corpsePtr->kill(false)` is the engine corpse-disposal funnel
  (`Pellet::doKill -> viewKill -> doKill`), the same path the engine's Onion
  disposal uses; only the *trigger* is injected.
- `registered_at_death=1` is expected for a corpse-leaving `TEKI_Chappy` (the
  corpse still needs its draw/material registration until disposal).

## Remaining blockers (named provider lane)

- Repeatable full-scene teardown and "manager reset vs full scene/day/restart"
  for this family: remains OPEN; full scene/day/restart evidence is owned by
  lane **01** (combined build) / lane **33** (QA). The Snow-level teardown gate
  is separate.
- Natural transport/reward and natural corpus delivery: family lane **13** and
  reward lane **06**.

## Subagent usage

- **explore #1 — source audit** (harness call sites, native registration
  signatures, `doKill`-vs-corpse-disposal timing, `find()` alive-blindness):
  used as-is; its finding that all four families are corpse-leaving `TEKI_Chappy`
  (so `doKill` fires at corpse disposal, not at the death animation) directly
  shaped the corpse-disposal forget design.
- **explore #2 — existing-candidate inventory** (arena `prepare` signatures, the
  dwarf-orange manifest gaps `control`/`native_teki_type`, existing tests):
  used as-is; drove the `_arena()` manifest normalization and the `--bank`/
  `--profile` plumbing.
- **general #3 — tests + harness scaffolding** (from the previous wave): its
  pytest skeleton was written for the now-retired module; superseded/discarded in
  this fix, where I rewrote the shared-harness tests directly. Net: the two
  explore agents saved substantial read time; the earlier test-scaffolding was a
  small sunk cost because the SLICE semantics (engine forget vs injected forget)
  changed after the audit.

## Exact reproduction

```powershell
$env:PYTHONUTF8 = '1'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l07 -- `
  py -3.12 -m experimental.pikmin2_lifecycle_runtime run `
    --family dwarf-orange `
    --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
    --bank C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank `
    --profile C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref `
    --output C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf-run-fix1 `
    --exe C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf-build/baseline/fixture.exe
```

Prerequisite (already done): build the fixture for the family
`py -3.12 -m experimental.pikmin2_lifecycle_runtime build --native .../native-l07 --build-dir .../native-l07-build --output .../lf-build --head b805d9c626e4f4558c95aef7cac311a5d9a2068f --family dwarf-orange`
(after `build_lane.py l07` produces `nectar.exe`).

## Slice 2

Tracking the two open ledger legs on the same lane-07 reusable harness
(`experimental/pikmin2_lifecycle_runtime.py`): (a) repeatable teardown, and
(b) manager-reset vs full-scene teardown.

### (a) Repeatable teardown — two full cycles

`--cycles 2 --teardown manager-reset` on Dwarf Orange (source_id 44) runs
`death -> engine forget (corpse disposal) -> respawn -> re-entry` twice on the
same generator, then a final manager-reset teardown:

```
P2_LIFECYCLE_CYCLE cycle=1 -> DEATH frame=7 -> REENTRY frame=128 reused=1 -> REGISTRY cycle=1 count=1
P2_LIFECYCLE_CYCLE cycle=2 -> DEATH frame=133 -> REENTRY frame=254 reused=1 -> REGISTRY cycle=2 count=1
P2_LIFECYCLE_REWARD pokos=-1                     # cargo-free: no reward grew
P2_LIFECYCLE_TEARDOWN_MODE mode=manager-reset
P2_LIFECYCLE_SUMMARY ... control=1               # control actor untouched across both cycles
PASS P2_LIFECYCLE_RUNTIME                        # exit 0
```

- **No registry growth**: each re-entry leaves exactly one registration
  (`registry_growth_ok=true`, both cycles `count=1`).
- **No duplicate reward**: `pokos=-1` (cargo-free arena; nothing grew).
- **Control untouched**: `control=1` at the end of both cycles.
- **Address reuse**: `reused=1` in both re-entries (natural death -> corpse
  disposal releases the generator ref, so the freed slot is handed back).

The `SUMMARY alive=0` is expected, not a defect: the re-born mortal Chappy is
killed by the idle 20-red squad during the 120-frame post-teardown observation
window (labelled mortal/hostile behavior); the *control* is what must stay
alive, and it does.

### (b) Manager reset vs scene teardown

`--teardown manager-reset` (default) re-enters through the family's own
`pc_p2_*_setup()` (which resets *just that family*). `--teardown scene-teardown`
instead calls the production `pc_p2_reset_all_teki()` (the
`GameCoreSection::exitStage` family-reset hook, `gameCoreSection.cpp:890`), which
clears every family in one call:

```
P2_LIFECYCLE_TEARDOWN_MODE mode=scene-teardown
P2_LIFECYCLE_TEARDOWN refs_before=1 refs_after=0    # dwarf_orange registry cleared
P2_LIFECYCLE_SUMMARY ... control=1
PASS P2_LIFECYCLE_RUNTIME                           # exit 0
```

The evidence JSON labels the mode (`teardown_mode`) and gate (`scene_teardown_ok`);
`refs_before=1 -> refs_after=0` is the raw surviving-reference report.

**Boundary (honest):** the in-place fixture calls `pc_p2_reset_all_teki()`, not
the full day-end `exitStage()`/section re-enter (which nulls `naviMgr` and the
gen factories and can only continue through the menu/map-select section
transition — the Snow-campaign `pc_p2_input_script` path owned by lane 01). So
"manager reset vs full scene/day/restart" remains OPEN at the section level;
this slice pins the family-reset hook that the scene boundary reuses.

### (c) Second family (Sokkuri)

`FAMILY_HOOKS` now includes `sokkuri` (routes `pc_p2_sokkuri_registered/
setup/...`; string-tested via `test_sokkuri_hooks_route_to_its_module`).
`--family sokkuri` fails fast with a clear deferral: the available ground arena
co-stages Armor/ElecBug/Imomushi/TamagoMushi/Hana, and a clean Sokkuri-only run
needs a Sokkuri-only arena (cross-lane, lane 14). The "torn down together"
mechanism is unchanged and cited: `pc_p2_reset_all_teki()` resets both
`pc_p2_dwarf_orange_reset()` (`pc_p2_teki_lifetime.cpp:110`) and
`pc_p2_sokkuri_reset()` (`:135`) in one call; this slice proves it clears
dwarf_orange at runtime, and the prior seam evidence (`P2_TEARDOWN_PROBE
before=6 after=0` in docs/PIKMIN2_TEKI_LIFETIME_SEAM.md) proves the multi-family
clear.

### Commits (slice 2)

| Branch | Commit | Subject |
|---|---|---|
| root `deepseek/p2-l07` | `(this)` | lane07: repeatable teardown (--cycles) + manager/scene teardown + sokkuri hooks (#397) |

### Evidence pins

- native `b805d9c6` (unchanged), `nectar.exe` SHA
  `2d507c6cf0a827ce4bbf4e3beb22aac1998b1bf310f90bf4005048388921accc`.
- fixture SHA `b56047fee2deec65b2f12cb34dc5d046982831e2d9f167b334c9f49a6e737092`.
- 2-cycle run `output/dsw/l07-out/lf2c-cycles2/a32d581e99c747d593d45b9a6fa9e2ee`.
- scene run `output/dsw/l07-out/lf2c-scene/f8ec0e1adb67470fbe0a286a4bf29d9a`.
- `tests/test_pikmin2_lifecycle_runtime.py` -> 16 passed.

### Exact reproduction (slice 2)

```powershell
$env:PYTHONUTF8 = '1'
# two-cycle repeatable teardown (manager reset)
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l07 -- `
  py -3.12 -m experimental.pikmin2_lifecycle_runtime run --family dwarf-orange `
    --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
    --bank C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank `
    --profile C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref `
    --output C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf2c-cycles2 `
    --exe C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf2c-build/baseline/fixture.exe `
    --cycles 2 --teardown manager-reset
# scene teardown
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l07 -- `
  py -3.12 -m experimental.pikmin2_lifecycle_runtime run --family dwarf-orange `
    --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
    --bank C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank `
    --profile C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref `
    --output C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf2c-scene `
    --exe C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf2c-build/baseline/fixture.exe `
    --cycles 1 --teardown scene-teardown
```

Fixture build (after `build_lane.py l07`):
`py -3.12 -m experimental.pikmin2_lifecycle_runtime build --native .../native-l07 --build-dir .../native-l07-build --output .../lf2c-build --head b805d9c626e4f4558c95aef7cac311a5d9a2068f --family dwarf-orange`.

### Subagent usage (slice 2)

- **explore #1 — source audit** (day-end/exitStage/finalSetup, `_reset_all_teki`
  callers, Sokkuri module, corpse-leaving `TEKI_Chappy`): used as-is; its
  finding that in-place `exitStage()` nulls the section (so the fixture can only
  call the `pc_p2_reset_all_teki()` hook) directly shaped the scene-mode scope.
- **explore #2 — existing-candidate inventory** (day-end/repeat/ground/mixed
  fixtures, Sokkuri arena realities, `pc_p2_preview_pokos()==-1`): used as-is;
  confirmed the ground arena is a 6-species mix (no Sokkuri-only arena) and that
  `pokos=-1` in cargo-free mode — both drove the honest boundary/deferral notes.
- **general #3 — tests scaffolding**: returned a `TEARDOWN_MODES`/`--cycles`/
  `--teardown` contract; adopted almost verbatim (I only harmonized the existing
  single-cycle test log to add the required `P2_LIFECYCLE_TEARDOWN_MODE`
  marker, and extended `validate()` to match). Estimated it saved the full
  pytest-authoring pass for the new gates.

---

# Review fix 2 (l07-fix2)

Reviewed: slice-2 handoff NOT merged (root merges clean; native had no commits).
This fix addresses all six review items on the same branches; both teardown
modes now pass end-to-end with a real registry-count gate and a real movement
gate.

## What changed (per review item)

1. **Movement gate restored and now gated.** `validate()` adds a `moved` check
   (≥1 `P2_LIFECYCLE_MOVE` line with `dist>=1.0`); the native summary
   `require(moved>=1, "lifecycle no autonomous movement")` is restored as
   `require(moveObserved==1, ...)`. The probe was flaky in two ways: (a) the
   finishing early-return skipped the fixed `observed==150` probe, and (b) the
   idle Dwarf Orange Bulborb does not autonomously locomote in the cargo-free
   arena (the one-shot slice-1 `dist=4.062` was a squad-engagement fluke). The
   movement is now sampled a fixed number of frames after the re-entry, with a
   labelled **locomotion lure** injection (relocate up to 10 live Pikmin onto the
   re-entered target's front arc) so the real P1 pursuit path drives observable
   motion — the same injection category as the lethal hit and the corpse-disposal
   trigger.
2. **Real registry count.** Added `pc_p2_dwarf_orange_count()` (native hook
   commit `7a0865c1`); `pc_p2_sokkuri_count()` already existed. `FAMILY_HOOKS`
   now carries `count`/`reset` per family; the fixture prints the real count at
   each re-entry (`require(cnt==1, ...)`) and the post-teardown re-entry, and
   `validate()` gates `registry_growth = all per-cycle counts == 1` on real ints
   (no longer `int(bool(registered))`).
3. **manager-reset performs a real teardown.** Both modes now reset the family
   at the teardown point (`manager-reset` → family `_reset`; `scene-teardown` →
   `pc_p2_reset_all_teki()`), print the same `P2_LIFECYCLE_TEARDOWN
   refs_before/after` line, and `require(refs_after==0)`.
4. **scene-teardown re-enters/rebinds.** After the teardown line both modes call
   `_setup` again and print a post-teardown `P2_LIFECYCLE_REGISTRY cycle=N+1
   count=1` (`require(post==1, ...)`); docstring now says "family-reset hook",
   not section teardown (in-place `exitStage()` out of reach — deferral noted).
5. **Sokkuri labelled hooks-only.** Handoff section (c) now says "hooks only,
   not run"; the `_arena()` fast-fail raise is unchanged.
6. **Tests.** Deleted the dead `_require_slice2()` guard and its calls; added the
   `pc_p2_reset_all_teki()` routing assert to the dwarf-orange instrument test;
   refreshed the synthetic logs for the new teardown/registry markers.

## Commits

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l07-native` | `7a0865c1` | lane07: add pc_p2_dwarf_orange_count for registry-growth fixture evidence (#397) |
| root `deepseek/p2-l07` | `14bf97f` | lane07: review fixes 2 — real registry count, movement gate, symmetric teardown+re-entry (#397) |

Native base unchanged (`b805d9c6`), root base unchanged (`ef1cace7`).

## Build evidence

`py -3.12 .../build_lane.py l07` →
`native=7a0865c1adb0594b37136774bb9c839be7fdc4af dirty=no`
`nectar.exe sha256=83087329e888d5ab656cc7e7ad6af2d9cc7a9185cee038b4c18c9e8ae62c2be4`
`ninja_n="ninja: no work to do." seconds=107`.

Replacement-main dwarf-orange fixture `sha256=53aa3212e11d5fc7992fdf90a389af1616ecfa93a28cda0c6f618ffac18ae0da`
(`lf2c-fix2d-build`).

## Runtime evidence (both modes)

- **manager-reset `--cycles 2`** — `lf2c-fix2d-cycles2/888d57dabd3a4b42bb11bbff2f57007b`:
  `passed=true`, `registry=[[1,1],[2,1],[3,1]]`, `moved=true` (dist 2.780 / 4.074),
  `teardown_cleared=true`, `teardown_reentry=true`, `control_untouched=true`,
  `reused_observed=true`, `bind_lines=4 draw_lines=4`, exit 0.
- **scene-teardown `--cycles 1`** — `lf2c-fix2d-scene/633edceb40e745568e91ab0c6a09d1d4`:
  `passed=true`, `registry=[[1,1],[2,1]]`, `moved=true` (dist 4.201),
  `teardown_cleared=true` (`refs_before=1 refs_after=0`),
  `teardown_reentry=true` (`cycle=2 count=1`), `control_untouched=true`, exit 0.

Both runs: real registry count stays `1` across cycles (no growth), reward
`pokos=-1` (cargo-free), control actor survives, window 960x540 centred.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_lifecycle_runtime.py -q` → **16 passed**.
Focused battery (`..._lifecycle_runtime.py` + `dwarf_orange_runtime/chain/dwarf_orange`)
→ **57 passed**.

## Six-gate table (Dwarf Orange 44) — updated for fix 2

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS (natural) | `P2_ENEMY_READY species=BlueKochappy source_id=44 generator=211001 health=250.0 max_health=250.0` |
| 2. Autonomous movement + animation | PASS (injected lure → real pursuit) | `P2_LIFECYCLE_MOVE dist=2.780/4.074/4.201`; `P2_DWARF_ORANGE_DRAW corpse=0` |
| 3. Attacks + receivers | natural receiver, injected lethal value | `P2_LIFECYCLE_ATTACK accepted=1 health=250.0 -> 0.0` |
| 4. Death + corpse | death natural; disposal injected; engine forget | `registered_at_death=1` → `registered_after_dispose=0 engine=doKill` |
| 5. Transport + reward | N/A | cargo-free; `pokos=-1`, lane 06 |
| 6. Cleanup + re-entry | **PASS** | engine forget, `reused=1`, real `count=1` both cycles, `teardown refs 1->0`, post-teardown `count=1`, control `=1` |

## Assumptions / honesty

- The locomotion lure (Pikmin relocation) is injected and labelled; it does not
  fabricate the movement — the pursuit is the real engine P1 AI. Without it the
  idle Bulborb does not reliably exceed `dist>=1` in the cargo-free arena.
- `scene_teardown_ok` still means "the `pc_p2_reset_all_teki()` family-reset
  hook cleared the family"; the full in-place day-end section re-enter remains
  lane-01/lane-33 territory (unchanged deferral).

## Subagent usage (review fix 2)

- The brief instructed a three-subagent split, but **no `task` subagent tool was
  exposed in this session**, so the source audit, candidate inventory and
  test/harness work were all performed inline. Net effect: the three-way
  parallelization did not happen (could not), and its time-saving benefit was
  therefore zero; the findings documented in the prior slices' "Subagent usage"
  sections were reused as-is where relevant.

## Exact reproduction

```powershell
$env:PYTHONUTF8 = '1'; $env:PIKMIN_P2_ROOM_WINDOW = '960x540'
# build native once
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l07
# replacement-main fixture
py -3.12 -m experimental.pikmin2_lifecycle_runtime build --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l07 --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l07-build --output C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf2c-fix2d-build --head 7a0865c1adb0594b37136774bb9c839be7fdc4af --family dwarf-orange
# manager-reset, 2 cycles
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l07 -- py -3.12 -m experimental.pikmin2_lifecycle_runtime run --family dwarf-orange --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --bank C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank --profile C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref --output C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf2c-fix2d-cycles2 --exe C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf2c-fix2d-build/baseline/fixture.exe --cycles 2 --teardown manager-reset
# scene-teardown, 1 cycle
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l07 -- py -3.12 -m experimental.pikmin2_lifecycle_runtime run --family dwarf-orange --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --bank C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank --profile C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref --output C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf2c-fix2d-scene --exe C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/lf2c-fix2d-build/baseline/fixture.exe --cycles 1 --teardown scene-teardown
```
