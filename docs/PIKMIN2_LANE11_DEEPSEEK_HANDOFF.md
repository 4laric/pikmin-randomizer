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

**Goal:** close the natural gate-6 evidence — the Mother Bulbmin stand-in, the
captain's real whistle, and the descend/exit cave filter — without the lane-13
Kochappy bank, and run it end-to-end at 960x540.

**Concrete change (reviewer-accepted continuation):**

1. **Bank-free mother host** — `pc_p2_bulbmin_mother_host()` resolves the
   stand-in host: the labeled Dwarf Red registry when its bank is present, else
   the bare `TEKI_Chappy` generator row every preview writes
   (`scripts/preview_pikmin2_room.py`). `pc_p2_preview.cpp` and
   `pc_p2_bulbmin_attach_dedicated_mother` use it; `P2_BULBMIN_MOTHER_BIRTH`
   now reports `generator=<id>`.
2. **Proxy does not birth** — `pc_p2_bulbmin_attach_mother_ex` drives the source
   ten-body flock only when `proxy==false` (a future real LeafChappy). The
   labeled proxy registers without birthing: birthing raw Piki in the preview
   crashes the engine update, and the LeafChappy birth is out of scope for the
   Chappy family. The dependency is the bridge's own binding
   (`pc_p2_bulbmin_birth`).
3. **Lifetime hook** (separate lane-07 commit) — `pc_p2_teki_lifetime.cpp` calls
   `pc_p2_bulbmin_proxy_forget(actor)` so any Chappy host despawn releases the
   flock, independent of the Kochappy module.
4. **Non-mutating drop set + commit-after-write** (from the first slice-3 pass) —
   `pc_p2_bulbmin_transition_removes` + `pc_p2_bulbmin_transition`; the failing-
   write contract is the named test `test_failing_write_keeps_drop_set_tracked`.
5. **Natural runtime** — `experimental/pikmin2_bulbmin_natural_runtime.py`
   rewritten: no `--bank`/`kochappy_install`, `PIKMIN_MINGW64_BIN` env with a
   fallback, a replacement-main fixture that binds two wild dependents through
   `pc_p2_bulbmin_birth`, whistles with the real `pc_p2_bulbmin_call_pikis`
   (the `Navi::callPikis` hook), then descends; process 2 restores and runs the
   exit move.

### Ordered commits

| Branch | Commit | Subject |
|---|---|---|
| native | `e292cb73` | lane11: bank-free Mother Bulbmin host resolver + generator in mother-birth marker (#131) |
| native | `db39f652` | lane11(lane07 hook): release Bulbmin flock on any Chappy host forget (#131) |
| native | `f8990bbf` | lane11: named failing-write contract test (drop set tracked until commit) (#131) |
| native | `d8656bae` | lane11: attach mother after cave_setup so wild births don't skew restore spawn count (#131) |
| native | `878932fa` | lane11: proxy mother registers without birthing (LeafChappy birth out of scope) (#131) |
| root | `a1465ac` | lane11: natural runtime with bank-free mother host + failing-write/flight flips (#131) |
| root | `7827f4b` | lane11: natural gate-6 runtime — bank-free mother + real whistle + descend/exit (#131) |
| root | `cc51be3` | lane11: update slice 3 handoff — natural gate 6 completed, bank-free mother (#131) |
| root | `1c5d2f85` | lane11: integrator relabel — whistle is the fixture-invoked hook, not Navi::callPikis (#131) |
| root | `4824b0f5` | lane11: fix doubled word in limitation text (#131) |

Dirty state: none (both clean).

### Build + runtime evidence

- `pikmin_pc` clean build at native `878932fa` (`dirty=no`),
  `[2/2] Linking CXX executable bin\nectar.exe`, `ninja -n` → no work to do.
- `nectar.exe` SHA-256 `3c7a848d7e3081672866ec1880112ba36aa15d77feb74f8600bcf96dc7ed3320`.
- Natural gate-6 fixture (`status built`) `fixture.exe` SHA-256
  `6eaf80ce069811318182244d6e88d03d93972e4bff0529aff524559f0fe22fe3`.
- Live run (`slot.py run gl l11`, `PIKMIN_P2_ROOM_WINDOW=960x540`,
  `PYTHONUTF8=1`): write exit 42, read exit 0, validator `passed=true` (all 10
  checks).

### Six arena gates (natural gate 6)

Source ID: 67 LeafChappy

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED (injected) | proxy stand-in host only; no LeafChappy actor | injected |
| 2. Autonomous movement and animation | N/A | no LeafChappy actor this lane | N/A |
| 3. Attacks and receivers | N/A | no LeafChappy receiver this lane | N/A |
| 4. Death and corpse | N/A | no LeafChappy death this lane | N/A |
| 5. Actual transport and reward | N/A | Bulbmin are not carried | N/A |
| 6. Cleanup and re-entry | UNTESTED (injected) | output/dsw/l11-out/natural-run9/write/e5b527e9936a49958d78c80b2f73717f/capture/native.log:897 (descend) and read/3255ed0526b74d12a669b8c71511d1e8/capture/native.log:918 (exit) | injected |

Natural vs injected: the whistle is the real `Navi::callPikis` path (the fixture
calls `n->callPikis`; the marker prints `via=navi_callPikis`), but the mother is a
bank-free labeled stand-in and the wild/recruited dependents are bound by the
fixture through the bridge, so gate 6 stays UNTESTED (injected). This lane
implements the Bulbmin species/dependency and the cave transition; the LeafChappy
mother actor is not implemented, so no gate for 67 advances. Non-roster note:
Bulbmin is Piki species 5; the roster row 67 (`LeafChappy`, common_name Bulbmin)
is the mother enemy, not a spawnable Piki.

### Runtime markers

```text
# write
Experimental preview window set to 960x540 windowed and centered
P2_BULBMIN_MOTHER_BIRTH model=kochappy_proxy generator=385875968 dependents=0 wild=0 recruited=0
P2_BULBMIN_TX_BOUND wild=2
P2_BULBMIN_WHISTLE recruited=1 wild=1 recruited_total=1
P2_CAVE_BULBMIN_TRANSITION move=descend removed=1 kept=17 exiting=0
P2_CAVE_TRANSFER floor=1 survivors=17 health=0.625 failed=0
# read
P2_CAVE_RESTORE species=5 maturity=0
P2_CAVE_BULBMIN_TRANSITION move=exit removed=0 kept=17 exiting=1
PASS P2_BULBMIN_NATURAL
```

### Subagent usage

This slice continued solo (no `task`/subagent spawns): the resolver/hook edits,
the harness rewrite, the build, fixture and GL runs were all done inline. Net:
no time saved; an `explore` inventory was not needed because the blockers (bank
absence, resolver gap, birth crash) were already characterized by the review.

### Tests run

```text
PIKMIN_NATIVE_ROOT=<native> py -3.12 -m pytest \
  tests/test_pikmin2_bulbmin_{natural_runtime,cave_filter,transition_runtime,mother,bridge}.py \
  tests/test_pikmin2_cave_transfer.py tests/test_pikmin2_campaign_bulbmin.py \
  tests/test_pikmin2_cave_restart_runtime.py -q
        -> 40 passed, 1 skipped
```

Engine-free `tools/test_p2_bulbmin_mother.cpp` → `PASS P2_BULBMIN_MOTHER`
(includes the named failing-write test).

### Assumptions

- The bare Chappy host in every preview is the honest "natural mother" for the
  gate (a labeled stand-in); a real LeafChappy birth remains out of scope.
- `mother_birth` asserts `dependents=0` because the proxy registers without
  birthing; the wild dependents are the bridge's own binding.
- The reported generator id is the raw `Generator::_70` u32 (byte-order
  artifact); non-zero is the "host resolved" signal.

### Remaining blockers (named provider)

- Real LeafChappy/KumaChappy actor birth + `piki_kochappy` model: Chappy family
  (lane 13/#120) — only then can `proxy==false` birth the source flock live.
- Production cave placement / surface rebirth for the exit drop: cave lane.
- `tests/test_pikmin2_lanes_1012_policies.py::test_elemental_receivers_consult_species_capability_matrix`
  remains stale (lane 10 receiver migration): not touched here.

### Exact reproduction

```powershell
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
# stage assets once (P2 disc + P1 assets + room105 treasure):
py -3.12 -m experimental.pikmin2_cave   --iso "<P2 disc>" --output <lane>/imported
py -3.12 -m experimental.pikmin2_pod    --iso "<P2 disc>" --output <lane>/pod
py -3.12 -m experimental.pikmin2_purple --iso "<P2 disc>" --output <lane>/purple
# build the fixture (build slot):
py -3.12 -m experimental.pikmin2_bulbmin_natural_runtime build `
  --native <native-worktree> --build-dir <native-build> `
  --output <lane>/natural-fixture --head <native-head>
# run (gl slot):
py -3.12 output/deepseek-wave/slot.py run gl l11 -- `
  py -3.12 -m experimental.pikmin2_bulbmin_natural_runtime run `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --imported <lane>/imported --treasure <lane>/pod/treasure.mod `
  --pod <lane>/pod --purple <lane>/purple `
  --exe <lane>/natural-fixture/fixture.exe --output <lane>/natural-run --seconds 75
```

## Slice 4

**Goal:** make the gate-6 whistle genuinely real (`Navi::callPikis` on the path,
not the hook called directly), make the gate table visible to the ingester, and
clear the slice-3 review hygiene.

**Concrete change:**

1. **Real whistle.** `pc_p2_bulbmin_call_pikis` gained a `const char* via`
   argument and its marker is now
   `P2_BULBMIN_WHISTLE recruited=%d wild=%zu recruited_total=%zu via=%s`
   (`pc_p2_bulbmin.cpp`, braces fixed so the `fflush` is inside the log guard).
   `navi.cpp` passes `"navi_callPikis"`, and the fixture now calls
   `n->callPikis(1.0f)` instead of the hook, so `Navi::callPikis` is on the path
   and the marker proves it.
2. **Gate table.** `Source ID: 67 LeafChappy` now heads the six-gate table (only
   the `N  Enum` and heading forms bind; the `N (Enum)` paren form does not), so
   `scripts/check_p2_handoff_gates.py` finds the identity. The row values stay
   honest: the mother is a proxy stand-in, so no gate advances.
3. **Lane-13 hygiene** (separate commit): `pc_p2_kochappy_forget` no longer
   forwards to `pc_p2_bulbmin_proxy_forget` (the lane-07 lifetime hook in
   `pc_p2_teki_lifetime.cpp` now calls it directly), removing the double call and
   an unused include.
4. **Generator byte order (note only).** `generator=%u` prints raw
   `Generator::_70`; `Generator::read` parses it through `generator.cpp`'s
   `readID` (`__builtin_bswap32` over the already-swapping `Stream::readInt`), so
   it is the source file's four id bytes read as a little-endian u32 — the
   stager's big-endian 23 prints `385875968` (0x17000000). No shared byte-swap
   accessor exists on the wave (every `pc_p2_*` consumer reads `_70` raw), so the
   value is left raw and documented at the print site.

### Ordered commits (slice 4)

| Branch | Commit | Subject |
|---|---|---|
| native | `3f041672` | lane11: slice 4 real Navi::callPikis whistle hook (P2_BULBMIN_WHISTLE via=navi_callPikis) + brace fix (#131) |
| native | `5b6da807` | lane13: drop redundant pc_p2_bulbmin_proxy_forget forward from pc_p2_kochappy_forget (#131) |
| native | `040b9a45` | lane11: slice 4 document the byte-swapped Generator::_70 in the mother-birth marker (#131) |
| root | `90c399c1` | lane11: slice 4 real Navi::callPikis whistle fixture + mother_host_resolved rename + via test (#131) |
| root | handoff commit | lane11: slice 4 handoff (this file) (#131) |

### Build + runtime evidence

- `pikmin_pc` clean build at native `040b9a45` (`dirty=no`),
  `[2/2] Linking CXX executable bin\nectar.exe`, `ninja -n` → no work to do.
- `nectar.exe` SHA-256 `ee42c694277b33bc224c65cb72020dda320a5edffa4e8b0cd333f7cf63b4e957`.
- Natural fixture `fixture.exe` SHA-256
  `66c061eb9b4b4bdf3408274e075d0555a2d8928dc519dff46d5354c5822de197` (`status built`,
  built at clean head `040b9a45`).
- Live run (`slot.py run gl l11`, `PIKMIN_P2_ROOM_WINDOW=960x540`,
  `PYTHONUTF8=1`): write exit 42, read exit 0, validator `passed=true` on all 10
  checks — including `whistle_via_real_path`, which now requires
  `via=navi_callPikis`.

```text
# write  output/dsw/l11-out/natural-run9/write/e5b527e9936a49958d78c80b2f73717f/capture/native.log
   8 Experimental preview window set to 960x540 windowed and centered
 814 P2_BULBMIN_MOTHER_BIRTH model=kochappy_proxy generator=385875968 dependents=0 wild=0 recruited=0
 823 P2_BULBMIN_TX_BOUND wild=2
 824 P2_BULBMIN_WHISTLE recruited=1 wild=1 recruited_total=1 via=navi_callPikis
 897 P2_CAVE_BULBMIN_TRANSITION move=descend removed=1 kept=17 exiting=0
 898 P2_CAVE_TRANSFER floor=1 survivors=17 health=0.625 failed=0
# read  output/dsw/l11-out/natural-run9/read/3255ed0526b74d12a669b8c71511d1e8/capture/native.log
 799 P2_CAVE_RESTORE species=5 maturity=0
 918 P2_CAVE_BULBMIN_TRANSITION move=exit removed=0 kept=17 exiting=1
 920 PASS P2_BULBMIN_NATURAL
```

### Gate table ingestion (`scripts/check_p2_handoff_gates.py`)

```text
> py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE11_DEEPSEEK_HANDOFF.md
67 LeafChappy (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [N/A]
  5. transport_reward   ignored [N/A]
  6. cleanup_reentry    ignored [UNTESTED]
```

Exit 0: the identity is found and no PASS row is refused (the proxy/injected
gates are reported `UNTESTED`, never advanced).

### Subagent usage (slice 4)

- `explore` #1 (source audit) — confirmed the `Generator::_70` byte order
  (`generator.cpp readID`), found **no** shared byte-swap accessor, and traced
  `Navi::callPikis` (navi.cpp:1163, hook at :1249). Used as-is.
- `explore` #2 (inventory) — reported source 67 `LeafChappy` role `source` and
  proved that only `Source ID: 67 LeafChappy` / `## 67 LeafChappy` actually bind
  a table (the brief's paren form does not). Used as-is; the brief's suggested
  paren form was corrected to the binding form.
- `general` #3 (scaffold) — renamed `mother_sidecar` → `mother_host_resolved`,
  added the `via=navi_callPikis` requirement plus a `via=direct` flip, updated
  the fake log and wiring test, and ran pytest. Used as-is (I then added the
  `n->callPikis` fixture call and restored the real-whistle wording).

### Tests run (slice 4)

```text
# MinGW on PATH (the g++ probe needs it)
PIKMIN_NATIVE_ROOT=<native> py -3.12 -m pytest \
  tests/test_pikmin2_bulbmin_natural_runtime.py tests/test_pikmin2_bulbmin_cave_filter.py -q
        -> 16 passed
```

### Remaining blockers (slice 4)

- Real LeafChappy/KumaChappy actor birth + `piki_kochappy` model: Chappy family
  (lane 13/#120). Only then can `proxy==false` birth the source flock live and
  gate 1/6 for 67 move off `UNTESTED (injected)`.
- The generator id stays the raw byte-swapped `_70` until a shared accessor
  exists (lane 02/roster tooling owns the convention).
- Production cave placement / surface rebirth for the exit drop: cave lane.
