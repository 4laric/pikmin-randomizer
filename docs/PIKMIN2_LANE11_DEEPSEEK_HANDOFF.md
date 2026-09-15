# Lane 11 (Species/Bulbmin) — DeepSeek handoff

Parent [#131](https://github.com/4laric/pikmin-randomizer/issues/131);
checkpoint tracking [#112](https://github.com/4laric/pikmin-randomizer/issues/112).
Implementation owner: Codex through shared `4laric`; executing session/agent:
DeepSeek (lane 11, `dsw/l11-root` / `dsw/native-l11`).

## Slice delivered

**Source IDs owned / inspected:** Bulbmin = species 5
(`include/Game/Piki.h:54`), Mother Bulbmin = LeafChappy/KumaChappy
(`include/Game/Entities/LeafChappy.h:7,12`). Related inspected species files:
Purple/White modules (unchanged).

**Concrete slice:** reconcile recruitment with checkpoint schema by closing the
one live-wiring gap in the "identity storage → capability routing → recruitment →
checkpoint schema" series. The lane already had identity (species 5), the hazard
capability matrix, the whistle→recruited recruitment path and the schema-3 wire
format, but **`pc_p2_bulbmin_transition` had no live engine caller** (review note: it still has none after this slice; what landed is the separate `pc_p2_bulbmin_should_save` predicate wired into the cave checkpoint) and the
actual cave checkpoint wrote *every* surviving Bulbmin (wild or not). The source
`PikiMgr::caveSaveAllPikmins` / `saveAllPikmins` filter
(`src/plugProjectKandoU/pikiMgr.cpp:723,762`) never saves a wild (unwhistled)
Bulbmin. This slice adds that source-faithful rule to the live checkpoint.

## Ordered commits

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Both clean at handoff.

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l11-native` | `f16fa173f75cf63c4fe6fd6f15fd2f2b1741f6be` | lane11: source-faithful Bulbmin cave save filter (wild dependents never saved) (#131) |
| root `deepseek/p2-l11` | `76aa6b345fcbbcaf4c8f3b917dc6466d9bc689fa` | lane11: cave-filter contract test (wild Bulbmin never saved) (#131) |

Dirty state: none (both clean).

## Interfaces / hooks touched and why

Native `pc_p2_*` modules plus one narrow, separately reviewable cave hook:

- `pc_port/pc_p2_bulbmin_policy.h` — new engine-free `inline bool
  p2_bulbmin_should_save(int species, int phase)`, the source predicate mirrored
  over the port's species/phase representation (wild → never save).
- `pc_port/pc_p2_bulbmin.h/.cpp` — new `pc_p2_bulbmin_phase(const Piki*)`
  (`-1`/`P2BulbminWild`/`P2BulbminRecruited`) and
  `pc_p2_bulbmin_should_save(const Piki*, bool isExitingCave)`. Reads the live
  bridge ledger; inert unless `pc_p2_bulbmin_active()` (default off).
- `pc_port/pc_p2_cave.cpp` — additive hook in `pc_p2_cave_checkpoint`: a wild
  Bulbmin dependent is excluded from the checkpoint squad and the run logs
  `P2_CAVE_BULBMIN_FILTER wild=N recruited=M dropped=D kept=K exiting=0|1`.
  No behavior change with no opt-in config.
- `CMakeLists.txt` — add `bulbmin_cave_filter` to the engine-free `-UNDEBUG`
  contract-test foreach (target `p2_bulbmin_cave_filter_test`).
- `tools/test_p2_bulbmin_cave_filter.cpp` — new standalone gate
  `PASS P2_BULBMIN_CAVE_FILTER`.

Root: `tests/test_pikmin2_bulbmin_cave_filter.py` (compile-and-run gate + source
wiring assertions + pure-Python source-rule contract).

No shared engine file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`) was
edited; `pc_p2_cave.cpp` (a lane-11-owned Bulbmin carrier per #131 history)
received only the additive filter hook.

## Build evidence (`output/dsw/l11-build-evidence.txt`)

- `pikmin_pc` build: `[603/603] Linking CXX executable bin\nectar.exe` (exit 0);
  `ninja -n` → `ninja: no work to do.`
- `nectar.exe` SHA-256 `e00c73c0fcd1a3c67d6d99398df921f397e25ca27f67c10b2e3c6ce7d30324c4`.
- Config: Ninja + MinGW g++ 16.2.0, Release, `PIKMIN_NATIVE_JAUDIO=ON`.
- Evidence line was captured while the tree was still dirty (the same content
  that is now commit `f16fa173`); a clean-label re-run was attempted but the
  host-wide build semaphore (LIMITS build=2) was fully occupied by concurrent
  lanes across the session. Verified in the built image regardless:
  `nm -C` shows `T pc_p2_bulbmin_phase(Piki const*)` and
  `pc_p2_bulbmin_should_save(Piki const*, bool)`, and `strings` shows the
  `P2_CAVE_BULBMIN_FILTER ...` literal.

## Fixture adoption evidence

Not exercised this slice: a live GL arena was deliberately not run because the
slice is a cave-persistence/policy slice, not a combat/actor slice, and the only
way to produce a live wild dependent is a real Mother Bulbmin (LeafChappy)
actor, which the port still lacks (see blockers). The current 960×540 centred
window and live starting-Pikmin overlay were therefore **not** re-verified in a
new run here — the prior lane-11 checkpoint-restart evidence and the other
lanes' this-wave runs cover that baseline. No extinction-screen or fabricated
run is claimed.

## Six arena gates (Bulbmin cave persistence slice)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | source-backed N/A this slice (identity unchanged) | species 5 wired via `pc_p2_species`/`pc_p2_make_bulbmin`; no new spawn path |
| 2. Autonomous movement + animation | source-backed N/A this slice | no mother actor |
| 3. Attacks / receivers | source-backed N/A this slice | hazard immunity already runtime-proven by lane 10/14 (`interactBattle.cpp`, ElecBug Denki) |
| 4. Death + corpse | source-backed N/A this slice | Bulbmin death is ordinary Piki death; unchanged |
| 5. Transport + reward | source-backed N/A this slice | Bulbmin are not carried/rewarded |
| 6. Cleanup + re-entry | **PASS (contract/build), live-drop BLOCKED** | `PASS P2_BULBMIN_CAVE_FILTER`; `p2_bulbmin_should_save` linked into `nectar.exe`; live wild-drop needs a mother actor |

Labels: the filter predicate and the cave hook are pure source logic (no
injected health/state). The `PASS P2_BULBMIN_CAVE_FILTER` is a compile-and-run
contract gate, **not** a gameplay PASS; a live wild-dependent drop was not
observed because no Mother Bulbmin actor exists to birth a wild dependent.

## Subagent usage

- **explore #1 (source audit)** — extracted the exact `pikiMgr.cpp:722-725/762`
  save-filter predicate, `LeafChappy.cpp:131-152` birth loop, and
  `interactPiki.cpp` whistle/immunity lines. Used as-is; it pinned the filter to
  `(kind != Bulbmin || isPikmin())` and confirmed `isPikmin()` is false for wild.
- **explore #2 (candidate inventory)** — found the key gap (`pc_p2_bulbmin_transition`
  has no live caller) and the full caller map, plus the PASS banners. Used as-is;
  it directly selected this slice's target.
- **general #3 (pytest scaffolding)** — wrote `tests/test_pikmin2_bulbmin_cave_filter.py`
  with skip-if-absent semantics. Used as-is; after I landed the native code it
  ran 4/4. It also caught that `native-l11` already existed (so tests 2/3 assert
  on content, not file presence).

Net: the audits selected the slice and removed ~40 min of manual grep/read; the
scaffold removed the test-authoring pass. No result was discarded; none was used
to falsify evidence.

## Tests run

```
py -3.12 -m pytest tests/test_pikmin2_bulbmin_cave_filter.py -q        -> 4 passed
py -3.12 -m pytest tests/test_pikmin2_bulbmin_{bridge,mother,cave_filter}.py \
                    tests/test_pikmin2_cave_transfer.py \
                    tests/test_pikmin2_campaign_bulbmin.py \
                    tests/test_pikmin2_lanes_1012_policies.py \
                    tests/test_pikmin2_cave_restart_runtime.py -q
        -> 34 passed, 1 skipped, 1 failed
```

The one failure is **pre-existing and unrelated to this slice**:
`test_pikmin2_lanes_1012_policies.py::test_elemental_receivers_consult_species_capability_matrix`
asserts `p2_species_immune(pc_p2_species(piki), P2HazardElectric)` appears in
`interactBattle.cpp`, but the electric/gas receivers were already migrated to
`p2_hazard_reaction(pc_p2_species(piki), P2HazardElectric, …)` in a prior sweep
(`PIKMIN2_RECEIVER_PATHS.md` §9). This slice does not touch `interactBattle.cpp`;
the test is stale against the current base and is left for the receivers lane.

## Assumptions

- On the port, "wild" is represented only by a tracked dependent in the live
  `P2BulbminFlock`; an injected/restored Bulbmin (not in the ledger) is treated
  as already-whistled (`isPikmin()`), so it is carried. This mirrors the source
  flag semantics (`FPFLAGS_IsWildBulbmin` only set at mother birth).
- The source's exit-only drop (a Bulbmin never *leaves* the cave) is deferred:
  the preview has no surface-rebirth target to convert a carried Bulbmin into.
  `pc_p2_bulbmin_should_save` takes `isExitingCave` and logs `exiting=` so a
  future surface path can enforce it; the current filter drops wild dependents
  only. Documented deviation, not a bug.
- A standalone `g++` compile of the contract test is equivalent to the CTest
  target for establishing the predicate (the CTest registration is additive and
  will run in integration's CTest sweep).

## Remaining blockers (named provider)

- **Natural Mother Bulbmin (LeafChappy/KumaChappy actor + `piki_kochappy`
  model):** still missing; a live wild-dependent birth and therefore the live
  wild-drop observation is blocked on the Chappy-family actor lane (lane 13,
  #120) providing a real Bulbmin/mother actor. The existing Kochappy registration
  is only a labelled proxy.
- **Production cave placement / surface roundtrip:** cave lane (#112/#114).
- The stale receivers test above: receivers lane (#408) should refresh the
  `p2_hazard_reaction` assertion.

## Exact reproduction

```powershell
$env:PYTHONUTF8='1'
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
py -3.12 -m pytest tests/test_pikmin2_bulbmin_cave_filter.py -q
```

(Standalone native contract gate, without the GL slot:
`C:\msys64\mingw64\bin\g++.exe -std=c++17 -Wall -Wextra -I pc_port tools/test_p2_bulbmin_cave_filter.cpp -o cf.exe && cf.exe`
→ `PASS P2_BULBMIN_CAVE_FILTER`.)

## Slice 2

**Goal:** give `pc_p2_bulbmin_transition` its live caller and reconcile the
recruitment/dependency transition with the schema-3 checkpoint, proven in a
960x540 runtime.

**Concrete change:** `pc_p2_bulbmin_transition(P2BulbminCaveTransition)` now
returns `std::vector<Piki*>` (the live bodies the source
`PikiMgr::caveSaveAllPikmins` filter — `pikiMgr.cpp:723` — drops), and
`pc_p2_cave_checkpoint` is its single live caller: after the squad guards pass
it applies `P2BulbminDescendFloor`/`P2BulbminExitCave` and builds the persisted
squad from the surviving bodies, logging
`P2_CAVE_BULBMIN_TRANSITION move=<descend|exit> removed=N kept=M exiting=0|1`.
On a descent a wild (unwhistled) dependent is removed and a recruited one kept;
on an exit every tracked Bulbmin is removed. Untracked (already-restored/
injected) Bulbmin are kept — they represent an established recruited body and
the preview has no surface-rebirth target for the source's exit-only drop
(documented deviation). The prior slice-1 per-Piki `pc_p2_bulbmin_should_save`
inline filter was replaced by this authoritative transition call;
`pc_p2_bulbmin_phase` remains the public per-Piki query.

### Ordered commits

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l11-native` | `c4173f2b8909cdf1012b33beb3b459928444f86e` | lane11: wire pc_p2_bulbmin_transition into the live cave checkpoint (#131) |
| root `deepseek/p2-l11` | `318bf48` | lane11: Bulbmin transition runtime gate (wild dropped, recruited survives) (#131) |

Dirty state: none (both clean).

### Interfaces / hooks touched

- `pc_port/pc_p2_bulbmin.h/.cpp` — `pc_p2_bulbmin_transition` return type
  `std::vector<std::uint32_t>` → `std::vector<Piki*>`, capturing the dropped
  bodies before ledger erasure.
- `pc_port/pc_p2_cave.cpp` — checkpoint gathers live `Piki*`, and after the
  guards calls the transition once and rebuilds the squad; no shared engine file
  outside lane-11-owned cave/bulbmin modules changed.
- Root: `experimental/pikmin2_bulbmin_transition_runtime.py` (replacement-main
  fixture + two-process validator), `tests/test_pikmin2_bulbmin_transition_runtime.py`
  (7 unit tests), `tests/test_pikmin2_bulbmin_cave_filter.py` (wiring assertion
  updated from `pc_p2_bulbmin_should_save` to `pc_p2_bulbmin_transition`).

### Build + runtime evidence

- `pikmin_pc` rebuild `[8/8] Linking CXX executable bin\nectar.exe`, `ninja -n`
  → `no work to do`; `nectar.exe` SHA-256
  `76adf843443e77ce405ab61c07e75083296b131ac3814299e16a9353392bd510`
  (build_lane captured the still-dirty tree; content == commit `c4173f2b`).
  `nm -C` shows `T pc_p2_bulbmin_transition(P2BulbminCaveTransition)`.
- Fixture `fixture.exe` SHA-256
  `90370c27310f98cfdd6e28fe51c158193ea849cacb20e8b1c7337e40e1300819`
  (status `built`; `build_fixture` enforces clean native head `c4173f2b`).
- Live run `output/dsw/l11-out/tx-run` (write exit 42, read exit 0), 960x540
  centred window in both processes.

### Six arena gates (Bulbmin cave-transition slice)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS (source-backed identity; no new actor) | 18 reds + bridge-made dependents; `P2_BULBMIN_READY mother_epoch=1 dependents=10` |
| 2. Autonomous movement | source-backed N/A this slice | no mother actor |
| 3. Attacks / receivers | source-backed N/A this slice | hazard immunity unchanged (lane 10/14) |
| 4. Death + corpse | source-backed N/A this slice | `pc_p2_bulbmin_birth` for dependency only |
| 5. Transport + reward | source-backed N/A this slice | Bulbmin are not carried |
| 6. Cleanup + re-entry | **PASS** | transition live caller drops wild, keeps recruited; schema-3 restart preserves the recruited body |

Natural vs injected: the dependency is exercised through the bridge's public
`pc_p2_bulbmin_birth`/`pc_p2_bulbmin_whistle` entrypoints (no Mother Bulbmin
actor; its birth is out of scope). The transition filter + checkpoint + restore
are the real engine path; no health/state was injected.

### Runtime markers (write → read)

```
Experimental preview window set to 960x540 windowed and centered
P2_BULBMIN_READY mother_epoch=1 dependents=10 ... captain_table=1
P2_CAVE_READY floor=1 survivors=18 health=0.625
P2_BULBMIN_TX_WILD made=1 phase=0
P2_BULBMIN_TX_RECRUIT made=1 phase=1
P2_CAVE_BULBMIN_TRANSITION move=descend removed=1 kept=17 exiting=0
P2_CAVE_TRANSFER floor=1 survivors=17 health=0.625 failed=0
P2_BULBMIN_TX_CHECKPOINT ok=1
# read process
P2_CAVE_RESTORE species=5 maturity=0   (x1) ; species=1 (x16)
P2_CAVE_READY floor=2 survivors=17 health=0.625
P2_BULBMIN_TX_READ bulbmin=1 observed=60
PASS P2_BULBMIN_TRANSITION_RESTORE
```

All 13 validator checks `passed=true`.

### Subagent usage (slice 2)

- explore #1 (source audit) — confirmed the exact `caveSaveAllPikmins`/
  `saveAllPikmins` filters, `baseGameSection.cpp:1301` and
  `singleGS_CaveGame.cpp:656` cave-flow branches, and that leader/wild state is
  runtime-only (never in `CaveSaveData`; restored Bulbmin is self-owned). Used
  as-is; it pinned the descend-vs-exit semantics my transition implements.
- explore #2 (candidate inventory) — confirmed `pc_p2_bulbmin_transition` was
  still uncalled, quoted the slice-1 predicate code, mapped `mLeaderCreature`
  (Piki.h:307), and documented the cave_restart fixture env/squad/flow I reused.
  Used as-is; it selected the integration point and confirmed no birth/whistle
  harness existed yet.
- general #3 (scaffold) — wrote `experimental/pikmin2_bulbmin_transition_runtime.py`
  + `tests/test_pikmin2_bulbmin_transition_runtime.py` per my marker spec. Used
  as-is (7 unit tests pass; the live run's validator consumed the same `validate`).

### Reproduce

```powershell
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
# 1) stage asset modules (already done once into output/dsw/l11-out)
py -3.12 -m experimental.pikmin2_cave  --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --output output/dsw/l11-out/imported
py -3.12 -m experimental.pikmin2_pod   --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --output output/dsw/l11-out/pod
py -3.12 -m experimental.pikmin2_purple --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --output output/dsw/l11-out/purple
# 2) build fixture (build slot) — see the exact command already run above
# 3) run (gl slot)
py -3.12 output/deepseek-wave/slot.py run gl l11 -- py -3.12 -m experimental.pikmin2_bulbmin_transition_runtime run `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --imported output/dsw/l11-out/imported `
  --treasure output/dsw/l11-out/pod/treasure.mod `
  --pod output/dsw/l11-out/pod --purple output/dsw/l11-out/purple `
  --exe output/dsw/l11-out/tx-fixture/fixture.exe `
  --output output/dsw/l11-out/tx-run --seconds 75
```

### Remaining

- A live Mother Bulbmin actor (LeafChappy/KumaChappy) birth — Chappy family
  (lane 13/#120); the runtime exercises the dependency through the bridge API.
- Production cave placement / surface rebirth for the exit-drop — cave lane.
- `pc_p2_bulbmin_should_save` is now superseded at the live checkpoint by the
  transition; it remains as the per-Piki semantic predicate covered by
  `tools/test_p2_bulbmin_cave_filter.cpp`.

## Slice 3

**Goal:** fold the integrator's slice-2 review findings and start gate 6 natural
(Mother Bulbmin through the ordinary generator sidecar + the captain's real
whistle).

**Concrete change:**

1. `pc_p2_cave_checkpoint` now computes the Bulbmin drop set **non-mutatingly**
   via a new `pc_p2_bulbmin_transition_removes` and commits the mutating
   `pc_p2_bulbmin_transition` only **after `writeTransfer` succeeds**, closing the
   retry hole a failed write previously left (removed wild bodies became
   untracked and were kept on retry). `P2BulbminFlock` gains a const
   `removedOn`, the bridge an inline `transitionRemoves`, and
   `tools/test_p2_bulbmin_mother.cpp` adds `test_transition_removes_is_nonmutating`
   (the failing-write contract: the non-mutating query returns the same drop set
   twice without erasing, and only the commit erases).
2. Deleted the dead engine wrapper `pc_p2_bulbmin_should_save(const Piki*, bool)`
   (`pc_p2_bulbmin.cpp:185`). The engine-free policy predicate
   `p2_bulbmin_should_save(int, int)` stays as a contract-only mirror, kept alive
   by `tools/test_p2_bulbmin_cave_filter.cpp`.
3. Added observable natural-recruitment markers on the already-wired natural path:
   `P2_BULBMIN_MOTHER_BIRTH model=.. dependents=N wild=W recruited=R`
   (`pc_p2_bulbmin_attach_mother_ex`) and
   `P2_BULBMIN_WHISTLE recruited=N wild=W recruited_total=R`
   (`pc_p2_bulbmin_call_pikis`, the navi.cpp real-whistle hook). No behavior change;
   these make gate 6 measurable.
4. New root harness `experimental/pikmin2_bulbmin_natural_runtime.py`
   (validator + run scaffold) and `tests/test_pikmin2_bulbmin_natural_runtime.py`
   (six source-log unit tests + one PIKMIN_NATIVE_ROOT wiring test); the cave-filter
   test now asserts the compute-before-write/commit-after-write ordering and the
   removed dead wrapper.

### Ordered commits

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l11-native` | `94b6a79439e3748d4af0d73eca95ddd5c2cefcc5` | lane11: non-mutating Bulbmin drop set + commit after write; drop dead pc_p2_bulbmin_should_save (#131) |
| native `deepseek/p2-l11-native` | `952ba1a5c5b5e95f9f64eefb1e961d2f686031dd` | lane11: observable natural recruitment markers (mother birth + real-whistle recruit counts) (#131) |
| root `deepseek/p2-l11` | `f897409d577c7a6784fc42a91f86aa13e0a6d356` | lane11: cave-filter test proves non-mutating compute + commit-after-write and dead-wrapper removal (#131) |
| root `deepseek/p2-l11` | `ef0f75052c95f6ca5a0896424de7e12ebd603ad1` | lane11: natural Mother Bulbmin real-whistle gate 6 validator + tests (#131) |

Dirty state: none (both clean).

### Interfaces / hooks touched

- `pc_port/pc_p2_bulbmin_policy.h` — const `P2BulbminFlock::removedOn` mirroring
  `applyTransition`'s removal rule without erasing.
- `pc_port/pc_p2_bulbmin.h/.cpp` — `P2BulbminBridge::transitionRemoves` (inline)
  and live `pc_p2_bulbmin_transition_removes`; `pc_p2_bulbmin_should_save` removed;
  two natural-path log lines added to `pc_p2_bulbmin_attach_mother_ex` and
  `pc_p2_bulbmin_call_pikis`.
- `pc_port/pc_p2_cave.cpp` (lane-11-owned carrier) — checkpoint reorder: compute
  drop set, build squad, write transfer, then commit the ledger mutation.
- `tools/test_p2_bulbmin_mother.cpp` — non-mutating/commit contract stage.

No shared engine file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`) was edited;
the `navi.cpp` real-whistle hook and `pc_p2_preview.cpp` mother auto-attach were
already present from prior slices.

### Build evidence (`output/dsw/l11-build-evidence.txt`)

- Clean build at native `952ba1a5`, `dirty=no`,
  `[2/2] Linking CXX executable bin\nectar.exe`, `ninja -n` → `no work to do`
  (`seconds=80`).
- `nectar.exe` SHA-256 `e865b126f53ef28787c9631bdf3f42784e5367728b4d60cff1d9eaddb974785b`.
- `nm -C` shows `T pc_p2_bulbmin_transition` and (in the object)
  `T pc_p2_bulbmin_transition_removes`; `pc_p2_bulbmin_should_save` is absent.
  `strings` shows `P2_BULBMIN_MOTHER_BIRTH` and `P2_BULBMIN_WHISTLE`.

### Fixture adoption / six arena gates (natural gate 6)

The engine wiring for natural gate 6 already exists (mother auto-attach from the
Kochappy generator sidecar in `pc_p2_preview.cpp`, the captain's real whistle via
`navi.cpp` → `pc_p2_bulbmin_call_pikis`, and the descend/exit transition filter in
`pc_p2_cave.cpp`). This slice adds the observable markers and the validator.

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | source-backed (mother stand-in labeled) | Kochappy actor + bridge `P2_BULBMIN_READY`; no LeafChappy actor |
| 2. Autonomous movement | source-backed N/A | no mother actor this slice |
| 3. Attacks / receivers | source-backed N/A | hazard immunity unchanged (lane 10/14) |
| 4. Death + corpse | source-backed N/A | Bulbmin death is ordinary Piki death |
| 5. Transport + reward | source-backed N/A | Bulbmin are not carried |
| 6. Cleanup + re-entry | **engine contract PASS (unit) / live GL BLOCKED** | `tools/test_p2_bulbmin_mother.cpp` proves descend drops wild + exit drops all tracked; live GL run blocked on the lane-13 Kochappy bank (see blockers) |

Natural vs injected: the recruitment is the captain's real whistle (navi.cpp
hook), the mother birth is the generator-sidecar auto-attach, and the drop is the
live checkpoint filter — none are injected birth/whistle API calls. A live GL run
is not claimed; it is blocked on assets, not on logic.

### Subagent usage

This session had no `task`/subagent tool available, so the three delegated tasks
could not be spawned. The source audit (pc_p2_cave/pc_p2_bulbmin/pc_p2_kochappy
read-through), the candidate inventory
(`grep` for `pc_p2_bulbmin_*` callers, the Kochappy bank/arena harnesses, and the
missing-asset check under `output/`), and the pytest scaffolding
(`tests/test_pikmin2_bulbmin_natural_runtime.py`, the cave-filter test update)
were all done inline with the read/grep tools. Net: no time saved by subagents;
the shared-host restriction (three subagents max) was moot. Honest negative
result: the audit/inventory were still necessary and the absence of the
Chappy-family bank under `output/` (no `dwarf-red.bmd`, `kochappy-profile.json`,
`kochappy_*.mod`) was discovered manually — exactly the check an `explore`
inventory would have returned.

### Tests run

```
py -3.12 -m pytest tests/test_pikmin2_bulbmin_natural_runtime.py \
                    tests/test_pikmin2_bulbmin_cave_filter.py \
                    tests/test_pikmin2_bulbmin_transition_runtime.py -q
        -> 18 passed
py -3.12 -m pytest tests/test_pikmin2_bulbmin_{bridge,mother,cave_filter,transition,natural}_runtime.py \
                    tests/test_pikmin2_campaign_bulbmin.py \
                    tests/test_pikmin2_cave_transfer.py \
                    tests/test_pikmin2_cave_restart_runtime.py -q
        -> 29 passed, 1 skipped
```

(`PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l11`,
MinGW on PATH.) The engine-free tool tests also compile and pass directly:
`tools/test_p2_bulbmin_mother.cpp` → `PASS P2_BULBMIN_MOTHER`,
`tools/test_p2_bulbmin_cave_filter.cpp` → `PASS P2_BULBMIN_CAVE_FILTER`.

The pre-existing failure
`tests/test_pikmin2_lanes_1012_policies.py::test_elemental_receivers_consult_species_capability_matrix`
remains stale on the wave and is **lane 10's** (`p2_species_immune` →
`p2_hazard_reaction` migration); not touched here.

### Assumptions

- "Every tracked Bulbmin is removed" on exit is a contract over the *tracked*
  ledger. In the natural flow the descent already dropped the wild dependents and
  the whistled bodies become free Pikmin after the schema-3 restore, so the exit
  move runs over zero tracked dependents (`removed=0`); the all-tracked-removed
  guarantee is asserted at the policy/tool level, not via a fabricated GL run.
- `experimental/pikmin2_bulbmin_natural_runtime.run()` is an orchestration
  scaffold: it stages the cave floor (+ Kochappy bank) and runs the two processes,
  but the replacement-main `RoomApp` fixture that injects the captain's whistle
  *input* (the real Navi whistle path, not the API) and then invokes the
  checkpoint is still to be written. Completing it needs the Kochappy bank to
  validate, so it remains gated on the same lane-13 asset blocker.

### Remaining blockers (named provider)

- **Chappy-family bank + reference import (lane 13, #120):** `pikmin2_kochappy_bank`
  needs `kochappy-profile.json`, `dwarf-red.bmd` and `source-animation/*.bca`; none
  exist under `output/`, so the natural gate-6 GL run cannot register the Kochappy
  mother stand-in. Once lane 13 stages these, the reproduction below is unblocked.

### Exact reproduction

```powershell
$env:PYTHONUTF8='1'; $env:PIKMIN_NATIVE_ROOT='C:/Users/alari/pikmin-randomizer/output/dsw/native-l11'
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
py -3.12 -m pytest tests/test_pikmin2_bulbmin_natural_runtime.py tests/test_pikmin2_bulbmin_cave_filter.py -q
# live natural gate 6 (GL slot) once the lane-13 Kochappy bank exists:
py -3.12 output/deepseek-wave/slot.py run gl l11 -- py -3.12 -m experimental.pikmin2_bulbmin_natural_runtime run `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --imported output/dsw/l11-out/imported `
  --bank <lane13 kochappy bank dir> `
  --treasure output/dsw/l11-out/pod/treasure.mod `
  --pod output/dsw/l11-out/pod --purple output/dsw/l11-out/purple `
  --exe output/dsw/l11-out/tx-fixture/fixture.exe `
  --output output/dsw/l11-out/natural-run --seconds 75
```
