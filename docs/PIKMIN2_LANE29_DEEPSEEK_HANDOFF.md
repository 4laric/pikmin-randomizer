# Lane 29 — Jellyfloats, DeepSeek slice handoff (#243)

Owner: DeepSeek session via shared GitHub `4laric` (implementation owner recorded as
Codex). Lane 29 / Jellyfloats, tracking issue #243.

## Concrete source ID and missing gate addressed

- Source ID: **Kurage (Lesser Spotted Jellyfloat, `source_id` 57)**, `drop_type=BDT_Normal`
  (roster `docs/PIKMIN2_ENEMY_ROSTER.json`). Companion identity OniKurage (72, `BDT_Strong`)
  is modelled on the host side only; native wiring is Kurage-only this slice.
- Missing gate addressed: **death/corpse -> reward (corpse receipt) -> cleanup/re-entry**
  wiring. The source has no family-local reward function (audit
  `docs/PIKMIN2_FLYING_ENEMY_AUDIT.md` line 55: `EnemyBase::onKill`
  `enemyBase.cpp:1289` supplies a normal body). Previously the bound Kurage corpse
  was never resolvable to a generator at the Pod delivery path, so a delivered
  corpse aborted with `Unregistered P2 pod cargo`.

## What was added

Native (family module + one labelled shared hook):

- `pc_port/pc_p2_kurage_teki.{h,cpp}`: `pc_p2_kurage_receipt(PelletView*, unsigned&)`
  resolves a bound Kurage's dead-body `PelletView` to its generator; `pc_p2_kurage_bound_count()`
  diagnostic. Binding already tracked in the existing `s` map (no new engine state).
- `tools/p2_kurage_runtime.cpp`: new `--receiver-corpse-receipt` scenario proving the
  receipt resolves and that `pc_p2_kurage_teki_forget` clears it (cleanup/re-entry seam).
- `pc_port/pc_p2_preview.cpp` (labelled hook commit): added a `pc_p2_kurage_receipt`
  branch to `pc_p2_preview_deliver`, crediting `corpseValue` to the Pod economy as
  `corpse:<prefix>kurage:<generator>` — identical shape to the integrated mamuta branch.

Root:

- `experimental/pikmin2_kurage_rewards.py`: lane-06 receipt consumer for Kurage (57)
  and OniKurage (72), both `drop=corpse` on the `onion` ledger, `count=1`,
  `value=None` (exact source Poko from `enemyInfo.h` is deliberately not pinned;
  the experimental Pod owns `corpseValue`, matching the native hook).
- `tests/test_pikmin2_kurage_rewards.py`: 10 tests (schema, identity mapping,
  exactly-once, restart persistence, different-seed re-grant, revisit dedupe,
  unknown rejection, reconciliation coverage and pod-leak refusal).

## Ordered commits

Root (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; head `b2b38846cd86e3b724a92d9616597ccdc56308c2`, clean):

1. `b2b3884` `lane29: Kurage/OniKurage corpse reward consumer on shared receipts (57/72) (#243)`

Native (base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`; head `f8f186cf6692958d6d446efa7b41684b6d6e3857`, clean):

1. `13c08129` `lane29: Kurage corpse receipt registration + corpse-receipt fixture scenario (#243)`
2. `f8f186cf` `lane29: [hook] credit Kurage corpse in the Pod delivery receipt path (#243)`

Dirty state at handoff: both worktrees clean. Nothing pushed; never touched `main`
or the shared `native`/`build-randomizer` checkout.

## Interfaces / hooks touched and why

- `pc_p2_kurage_receipt` — new family-local corpse-receipt resolver, mirroring the
  integrated `pc_p2_mamuta_receipt`/`pc_p2_sheargrub_receipt` contract (takes the
  delivered body `PelletView`, returns generator). Belongs to lane 29; no provider
  interface change.
- `pc_p2_preview_deliver` — one additional labelled `else if` branch in the shared
  preview Pod reward router. Small, separately committed hook; does not alter any
  existing family or generic `corpses`/care-route resolution order (kurage resolves
  before the generic Chappy `corpses` fallback).
- Central lifetime seam unaffected: `pc_p2_kurage_teki_forget` was already wired
  into `pc_p2_forget_teki` (death funnel + slot reuse). The receipt map is exactly
  the existing binding map, so forget clears the corpse registration for free.

## Build evidence (from `output/dsw/l29-build-evidence.txt`)

- native commit: `f8f186cf6692958d6d446efa7b41684b6d6e3857`, `dirty=no`
- target: `pikmin_pc` -> `bin/nectar.exe`
- executable SHA-256: `ec1b3016acccdb207ba00b6c6afe935c8b2022d60b1853dbb8bf764a86486818`
- `ninja -n` result: `ninja: no work to do.`
- build dir: `C:/Users/alari/pikmin-randomizer/output/dsw/native-l29-build`
- config: Ninja, MinGW-w64 g++ 16.2.0, Release, `PIKMIN_NATIVE_JAUDIO=ON`,
  `-O3 -march=native -flto=auto`, absolute compiler/ninja paths.
- Build twice recorded (both `ninja -n` clean); production `pikmin_pc` linked 603/603.

Compile verification of the fixture scenario (added but not GL-run):

```
g++ -fsyntax-only -std=gnu++17 -fpermissive ... -Iinclude -Ipc_port -Itools ... tools/p2_kurage_runtime.cpp
```

returns EXIT 0 (only the codebase's known multi-character-constant warnings).

## Fixture adoption evidence (960x540 centred window / live starting Pikmin)

Not re-observed this slice: no real-GL run was performed. The mandatory baseline
components (`scripts/preview_pikmin2_room.py` overlay adding a 20-red starting
squad, and the native 960x540 centred `pc_window_center()` startup) are unchanged
from the pinned root/native bases and are not touched by this slice. A real-GL
fixture run that re-verifies `P2_KURAGE_WINDOW ... centered=1` and a live
20-red squad remains for the next runtime acceptance run (prior integrated lane 29
evidence already recorded both).

## Six arena gates (honest; injected vs natural labelled)

| Gate | Historical note | Evidence / note |
|---|---|---|
| 1. Exact identity and spawn | PARTIAL (inherited) | Kurage source ID 57, `BDT_Normal`. Binding (`P2_KURAGE_TEKI_READY` / `P2_KURAGE_AUTO_BIND_PASS`) was established by the prior integrated lane-29 slice; this slice adds `P2_KURAGE_CORPSE_READY` registration (compile-verified, not re-run). |
| 2. Autonomous movement and animation | source-backed N/A (unchanged) | Flight FSM, patrol/chase and per-state poses already integrated; not the subject of this slice. |
| 3. Attacks and receivers | source-backed N/A (unchanged) | Attack suction admission + ingestion receiver already integrated; not the subject of this slice. |
| 4. Death and corpse | PARTIAL | Corpse->generator receipt resolution added and compile-verified; natural death still relies on the P1 proxy body path. No natural kill + corpse re-observed this slice (injected/compile only). |
| 5. Actual transport and reward | BLOCKED | Receipt hook wired into `pc_p2_preview_deliver` (compile-verified). Actual Pikmin carry -> Pod deposit -> Pokos depends on lanes 06/07 natural transport; not observed. |
| 6. Cleanup and re-entry | PARTIAL | `pc_p2_kurage_receipt` clears via the existing central forget seam on death-funnel and slot reuse; runtime re-entry UNTESTED. |

Labels: nothing above is promoted to natural gameplay acceptance. Item 4/5 reward
wiring is a real receiver-side advance, not a natural gameplay PASS.

## Tests run and results

- `py -3.12 -m pytest -q tests/test_pikmin2_kurage_rewards.py` -> **10 passed**.
- Kurage-adjacent root suite
  (`test_pikmin2_kurage_rewards.py test_pikmin2_kurage_material_patch.py
   test_pikmin2_jellyfloat_envmap_assets.py test_pikmin2_envmap.py
   test_pikmin2_pose_blend.py`) -> **17 passed, 4 skipped, 11 subtests passed**
  (skips are asset-local fixtures/Windows symlink privilege).
- Native standalone `-fsyntax-only` of `tools/p2_kurage_runtime.cpp` -> EXIT 0.

## Assumptions made

- Exact source corpse Poko for Kurage/OniKurage is NOT pinned in this slice:
  `enemyInfo.h` is outside this worktree (parallel decomp checkout). The native
  hook uses the Pod's configured `corpseValue` (the established mamuta/sheargrub
  corpse pattern), and the host descriptors leave `value=None`. This is a
  documented experimental placeholder, not a source-audited Poko claim.
- The ordinary bound Kurage actor remains a P1 `TEKI_Frog` proxy; the reward
  registration keys the dead proxy's own `PelletView`, identical to the mamuta
  corpse receipt pattern.
- JAudio ON is mandatory to link (`Jac_NoteDemoSkipped`); the lane build wrapper's
  default configure marks compilers relative, which the fixture builder rejects, so
  this slice configured once with absolute compiler/ninja paths + `PIKMIN_NATIVE_JAUDIO=ON`.

## Remaining blockers (provider lane named)

- Natural death -> corpse -> Pikmin carry -> Pod/Onion deposit -> exactly-once
  receipt across restart: **lanes 06 (rewards/persistence) and 07 (lifecycle)**
  own the natural transport and durable Onion/AP endpoint; this slice only wires
  the family corpse so the existing Pod deliver path can credit it.
- Runtime re-verification (real-GL/input slot + a fresh staged room with the
  `p2-kurage-teki.txt` sidecar): blocked this session by host build-slot contention
  (two 20-minute waits) — the fixture scenario is added and compile-verified but not
  executed. Prior integrated lane-29 runtime evidence remains the binding baseline.

## Exact reproduction command

```
py -3.12 -m pytest -q tests/test_pikmin2_kurage_rewards.py
```

Native build (after `cmake -S ... -B ... -G Ninja -DCMAKE_C_COMPILER=<abs gcc>
-DCMAKE_CXX_COMPILER=<abs g++> -DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON
-DCMAKE_MAKE_PROGRAM=<abs ninja>`):

```
cmake --build C:/Users/alari/pikmin-randomizer/output/dsw/native-l29-build --target pikmin_pc -j 6
```

## Slice 2

Source ID: Kurage (Lesser Spotted Jellyfloat, 57). Goal: turn the corpse-receipt
gate from UNTESTED into a real runtime run, then attempt the natural kill path.
Root base `ef1cace7`, native base `b805d9c6`; both worktrees clean at handoff.

### Source-fidelity correction (from a decomp audit this slice)

Verified against `C:/Users/alari/pikmin-randomizer/native/pikmin2-research` @
`632af937` (read-only): a Jellyfloat **disables `EB_LeaveCarcass`**
(`Kurage.cpp:36`) and has no family-local reward function. On a natural kill,
`EnemyBase::deathProcedure` (`enemyBase.cpp:2525`) runs `throwupItemInDeathProcedure`
-> `throwupItem` (`:2590`), which births a **number pellet** via
`pelletMgr->makePelletInitArg(..., mPelletDropCode)`; `EnemyBase::onKill` (`:1289`)
then takes the "no carcass" branch -> `forceKillEffects` + `becomeCarcass`
(`:1403-1421`). It does **not** leave a carryable corpse body; bitter-honey drops
only when killed while `EB_Bittered`. No numeric Poko for ID 57/72 exists in
`enemyInfo.h` (only `mBitterDrops` = BDT_Normal/BDT_Strong).

Consequence (corrected this slice): the lane-06 descriptor's `drop` was
`corpse` (slice-1 assumption) and is now **`drop='pellet'`** in
`experimental/pikmin2_kurage_rewards.py`. The native `pc_p2_kurage_receipt`
corpse hook (`corpse:kurage:<gen>`, `corpseValue`) is retained as a **labelled
P1-proxy approximation**: the P1 TEKI_Frog proxy leaves a carryable body, whereas
the P2 source throws up a pellet. A source-faithful native pellet-reward slice
(reuse `pc_p2_receipt` `Ledger::Onion` `drop=pellet`) is future work.

### Native (three new commits; base `b805d9c6`, head `0099e634`)

1. `68814ed5` (integrator, pre-existing) keep naturally-dead Kurage bodies
   resolvable: post-death tick moves the corpse to a `corpses` map cleared only
   by forget/reset, and `--receiver-corpse-receipt` now zeroes health, ticks once
   and asserts the corpse still resolves.
2. `0099e634` this slice: add a `p2_kurage_runtime` replacement-main CMake target
   (`tools/p2_kurage_runtime.cpp` instead of `pc_main.cpp`), so
   `build_lane.py l29 --target p2_kurage_runtime` builds the fixture under the
   normal build semaphore (added to `PIKMIN_OPTIMIZED_TARGETS` for LTO/march).

### Build evidence (output/dsw/l29-build-evidence.txt)

- `p2_kurage_runtime` -> `p2_kurage_runtime.exe` SHA-256
  `0db537a064be93c472f0717c873bdfe9651e5197d9f1cd69b86876643247ce1c`, ninja -n clean.
- `pikmin_pc` -> `bin/nectar.exe` SHA-256
  `4a0da9eb4aad9736e94099ab04b6197c7fdc7d1ea1d52af7905fa07637a5d43a`, ninja -n clean.
- Config: Ninja MinGW g++ 16.2.0, Release, JAudio ON, absolute compiler/ninja paths.

### Runtime run (real-GL, `slot.py run gl l29`)

Command: `p2_kurage_runtime.exe --experimental-pikmin2-room --receiver-corpse-receipt`
in `output/dsw/l29-out/corpse-receipt-run` (assets reused read-only from
`output/p2-lane29-n-binding/assets`: staged frog-generator room + `kurage_attack.mod`
+ `kurage_wait.mod`; sidecars `p2-kurage-teki.txt` / `p2-cargo-free.txt` written
fresh). `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1`. Exit 0. Markers (full
log at `l29-out/corpse-receipt-run/stdout.log`):

```
P2_KURAGE_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter
P2_KURAGE_CORPSE_READY generator=201001 drop=BDT_Normal ledger=onion receipt=corpse:kurage:201001
P2_KURAGE_CORPSE_RECEIPT_PASS generator=201001 bound=1 drop=BDT_Normal
P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator=201001 injected=health_zero
P2_KURAGE_CORPSE_CLEANUP_PASS forgotten=1 bound=0
PASS KURAGE_RUNTIME corpse_receipt_cleanup
```

Fixture-baseline adoption: 960x540 centred window (`centered=1`), 20-red starting
squad (`red=20`), no immediate extinction.

### Natural-kill path (BLOCKED, furthest marker)

The natural path (Pikmin attacks -> frog proxy death, no health writes -> body
carried -> `pc_p2_preview_deliver` credits `corpse:kurage:<gen>`) was NOT reached
on the host:
- `tools/p2_kurage_runtime.cpp:188-189`: the isolated room preview *pauses the
  Teki manager's per-frame update*, so no ordinary P1 combat runs to reduce the
  bound frog's health.
- `pc_p2_kurage_teki_tick` (`pc_port/pc_p2_kurage_teki.cpp`) only reads
  `t->mHealth` (`:178/:185/:248`) as the FSM/receiver fact; it never drives the
  P1 damage->death->corpse flow.
- The corpse->carry->Pod delivery that fires `pc_p2_preview_deliver`
  (`pc_port/pc_p2_preview.cpp:310+`) is lane 07 (lifecycle) + lane 06 (transport/
  reward) territory (the lane-16 frog carry/combat fixture is the precedent, not
  forked here).
- Furthest natural marker logged: `P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS`
  (post-death corpse still resolvable after the health-zero-injected tick).
- Additionally source-inexact: even a P1-proxy natural corpse would be a body, but
  the P2 reward is a thrown-up number pellet (see correction above).

### Root

- `experimental/pikmin2_kurage_runtime.py` + `tests/test_pikmin2_kurage_runtime.py`
  (new): validator for the corpse-receipt markers; `validate_corpse_receipt`
  flips to FAIL when `P2_KURAGE_CORPSE_RECEIPT_PASS` / `P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS`
  is stripped; `native_corpsereceipt_flag_present()` resolves `PIKMIN_NATIVE_ROOT`
  (no hardcoded lane path). 7 tests.
- `experimental/pikmin2_kurage_rewards.py` + `tests/..._rewards.py`: corrected
  `drop='corpse'` -> `'pellet'` (source-fidelity), docstring documents the native
  corpse proxy. 10 tests.
- Combined run: `24 passed, 4 skipped, 11 subtests passed`.

### Subagent usage

- explore #1 (source audit): produced the authoritative `EB_LeaveCarcass` /
  `throwupItem` / no-Poko findings — used as-is, then I re-verified the key lines
  (`Kurage.cpp:36`, `enemyBase.cpp onKill/deathProcedure/throwupItem`) myself.
  High value (~saved 30+ min of decomp digging); it corrected the reward semantics.
- explore #2 (candidate inventory): used as-is to confirm no duplication and to
  locate the `p2_kurage_runtime.cpp` markers and `pc_p2_preview_deliver` branches;
  confirmed the `p2_kurage_runtime` CMake target did not yet exist. High value.
- general #3 (validator scaffolding): delivered a correct, path-free validator +
  7 passing tests; used as-is (minor sample-log pos/display values differ from the
  real 373,263/1707x1067 but are cosmetic). High value; saved ~15 min of writing.
- Net: subagents surfaced the source correction and delivered the validator;
  cost was negligible (read-only + cheap pytest). I retained solely native C++,
  build, GL run, commits and handoff.

### Six-gate update

| Gate | Historical note |
|---|---|
| 1 identity/spawn/bind | PASS (runtime) `P2_KURAGE_TEKI_READY` + `P2_KURAGE_CORPSE_READY generator=201001` |
| 2 movement/animation | source-backed N/A (unchanged; not this slice) |
| 3 attacks/receivers | source-backed N/A (unchanged) |
| 4 death/corpse | PASS (runtime, injected health-zero) corpse resolves post-death; labelled injected, not natural |
| 5 transport/reward | BLOCKED (carry->Pod depends on lanes 06/07; source reward is a pellet, not a corpse) |
| 6 cleanup/re-entry | PASS (runtime) forget clears corpse; recycled address never mis-resolves |

Reproduction:

```
py -3.12 -m pytest -q tests/test_pikmin2_kurage_rewards.py tests/test_pikmin2_kurage_runtime.py
```

## Slice 3 — natural carcass → Research Pod receipt, 57 Kurage (LANDED)

The previous slice recorded `transport_reward` BLOCKED: the isolated
`p2_kurage_runtime` replacement-main asserted the receipt resolver on an
injected `health_zero` death and never ran a natural kill → FreeMode carry →
Pod credit. This slice moves the lane onto the **production** `nectar.exe
--experimental-pikmin2-room` preview and lands the full natural chain.

Root base `dbc1a2f5`, native base `0099e634` (both clean at slice start).

### Ordered commits

Native branch `deepseek/p2-l29-native`:

1. `5cecfef2` — merge `claude/p2-deepseek-wave-native` (392 commits); no
   conflicts, both sides preserved.
2. `1771280d` — `lane29: natural Kurage carcass -> Pod receipt: free-mode ring,
   captain park, dead-Pikmin pellet suppression (#243)`

Root branch `deepseek/p2-l29`:

1. `lane29` — stager (`experimental/pikmin2_kurage_teki_stage.py`), natural-run
   validator (`experimental/pikmin2_kurage_pod_receipt.py`) + tests, handoff.

### What changed

- `experimental/pikmin2_kurage_teki_stage.py` (new): stages a generated
  `TEKI_Frog` (type 0) placement and its `p2-kurage-teki.txt` sidecar plus a
  cargo `p2-pod.txt` (`P2_POD_1 bolt 180 15 25 / Kochappy 2`) onto the committed
  room emitter. No `p2-cargo-free.txt`, so the preview does not refuse real
  cargo. The room already stages a `pr05` treasure actor, so the Pod anchor
  binds and `pc_p2_preview_deliver` is reachable.
- `pc_port/pc_p2_kurage_teki.cpp`: on natural proxy death the carcass Pellet is
  tracked (`P2_KURAGE_TEKI_DEAD`, `..._CORPSE_CONFIG`); the captain is parked
  beyond the 250u join-party range and the FreeMode survivors are ringed onto
  the carcass every 60 ticks until a TransportMode carrier latches, the carcass
  `carry_min` is forced to 1, and the survivors are re-formed once
  `pc_p2_kurage_receipt` is credited. Uncarried Red `pr01` number pellets are
  suppressed while the carcass is pending so a leftover dead-Pikmin/enemy pellet
  cannot hit the preview's deny-by-default cargo abort before the receipt. The
  converted `kurage_*.mod` visual setup is no longer fatal (the host body draws
  when they are absent).
- `experimental/pikmin2_kurage_pod_receipt.py` + `tests/test_pikmin2_kurage_pod_receipt.py`
  (new): parse the production run log and require the whole natural chain
  (death, carcass config, captain park, FreeMode recruit, a moving haul with
  latched carriers, the Pod receipt, and the post-receipt re-form); reject the
  injected `health_zero` fixture. 8 tests; the real run log validates.

### Runtime evidence (executed, production GL preview, natural kill + carry)

`pikmin_pc` (`nectar.exe`) built at native `1771280d` (built over the merge
`5cecfef2`), staged from the committed emitter at
`output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618`, run under
`slot.py run gl l29` at `PIKMIN_P2_ROOM_WINDOW=960x540` / `PYTHONUTF8=1`.
Log `output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log`
(sha256 `bd4da2e9621bdfb20b10a680675cef76d18143bd8bc67b91e84b19c77747f29c`;
copy `output/dsw/l29-out/kurage-pod-receipt-run.log`).

### Build evidence

`output/dsw/l29-build-evidence.txt` (Ninja + MinGW g++, private
`native-l29-build`):

```
lane=l29 target=pikmin_pc native=1771280dc559806bc8f19dbf5d3bfe3f56be3db3 dirty=no exe=...\bin\nectar.exe sha256=16ca37bed324030e5f54d2eabe25d458cd4689be2876cf152e33c6e8ed31ff90 ninja_n="ninja: no work to do."
```

The run above used exactly that executable (`sha256 16ca37be…`).

```
:727 P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter
:735 [Pikipelago] P2_POD_READY treasure=bolt value=180 weight=15 capacity=25 pokos=0
:808 P2_KURAGE_TEKI_DEAD generator=201001
:813 P2_KURAGE_TEKI_CORPSE_CONFIG carry_min=7 carry_max=14 min_free_slot=0 alive=1
:814 P2_KURAGE_TEKI_CAPTAIN_PARK x=81.150 z=427.742
:815 P2_KURAGE_TEKI_FREE_RECRUIT count=18 carriers=0 squad=18
:818 P2_KURAGE_TEKI_CORPSE tick=30 ... moved=29.930 carriers=8
:848 P2_KURAGE_TEKI_CORPSE tick=630 x=-202.928 z=-184.130 moved=421.858 carriers=15
:854 P2_KURAGE_TEKI_CORPSE tick=750 x=-212.791 z=-181.744 moved=426.828 carriers=1
:855 [Pikipelago] P2_POD_RECEIPT id=corpse:kurage:201001 value=2 new=1 pokos=2 seeds=0
:856 P2_KURAGE_TEKI_CORPSE_DELIVERED
```

Reading: the generated proxy is killed by the ordinary squad (`DEAD`); the
natural carcass spawns with `min_free_slot=0`; the captain is parked; 18
survivors are released FreeMode onto the carcass; carriers latch (8 … 18) and
haul it 29.9 → 426.8 units to the Pod; the Pod credits
`corpse:kurage:201001` (pokos 0 → 2); the survivors are re-formed. No injected
delivery call and no `health_zero` write exist on this path.

### Concrete source ID

Source ID: 57 Kurage (`source_id` 57, `BDT_Normal`).

| Gate | Historical note | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PARTIAL | output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log:727 (generated type-0 stand-in host, source 57 identity not claimed) | stand-in host |
| 2. Autonomous movement and animation | PARTIAL | output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log:745 placement bound at x=-65.970 y=30 z=48.269; approach sealed so the squad can engage | reachable placement engineered |
| 3. Attacks and receivers | PARTIAL | output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log:808 (ordinary squad kills the bound actor; suction receiver not re-exercised here) | receiver unchanged from prior slice |
| 4. Death and corpse | PASS | output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log:808 P2_KURAGE_TEKI_DEAD, :813 CORPSE_CONFIG carry_min=7 carry_max=14 min_free_slot=0 | natural |
| 5. Actual transport and reward | PASS | output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log:855 P2_POD_RECEIPT id=corpse:kurage:201001 value=2 new=1 pokos=2 seeds=0 (haul 426.8u, 18 carriers) | natural |
| 6. Cleanup and re-entry | UNTESTED | single session; central forget/reset seam wired | untested this slice |

Honest labels (fixture concessions): the bound actor is a P1 type-0 stand-in,
not the P2 Jellyfloat actor (gate 1 stays PARTIAL); the carcass `carry_min` is
lowered 7 → 1; the proxy is grounded/kept within the squad's attack volume so an
ordinary FreeMode kill can occur; and uncarried Red `pr01` number pellets are
suppressed while the carcass is pending. The receipt itself is a natural
FreeMode grasp → route → Pod credit through `pc_p2_preview_deliver` →
`pc_p2_kurage_receipt` — no injected delivery and no `health_zero` write.

Source-fidelity note (unchanged): the P2 Kurage source disables
`EB_LeaveCarcass` and throws up a number pellet rather than leaving a carryable
body (`Kurage.cpp:36`, `enemyBase.cpp` `onKill`/`throwupItem`). The native
`corpse:kurage:<gen>` credit is therefore a labelled stand-in for the source
pellet reward; a source-faithful native pellet-reward slice remains future work.

### Checker output

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md
57 Kurage (role=source):
  1. identity_spawn     ignored [PARTIAL]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  ignored [PARTIAL]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    ignored [UNTESTED]
72 OniKurage (role=source): warning (shared table) - named in prose but no table of its own; give it a `Source ID` line + six-gate table to claim its gates
EXIT=0
```

### Reproduction

```
py -3.12 -m experimental.pikmin2_kurage_teki_stage --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --converted C:/Users/alari/pikmin-randomizer/output/pikmin2-room105 --output C:/Users/alari/pikmin-randomizer/output/dsw/l29-out/kurage-arena
# then, in the printed run dir, under the GL slot:
py -3.12 output/deepseek-wave/slot.py run gl l29 -- py -3.12 <runner> <native-l29-build>/bin/nectar.exe 240
py -3.12 -m pytest -q tests/test_pikmin2_kurage_pod_receipt.py
```

## Slice 4 — natural flight movement/animation, receiver capture, cleanup/re-entry, 57 Kurage (LANDED)

Root base `b2b38846`; native base `1771280dc5`; native head
`50dde734928e402b2b1277920301628e89fb3fd3`. The current wave native
`claude/p2-deepseek-wave-native` (`7ed95228`) was already an ancestor of the lane
(the prior `5cecfef2` merge), so `git merge` reported `Already up to date`; no new
merge commit was needed. Three additive lane-local hooks, no shared-semantics change.

### What changed

- `pc_port/pc_p2_kurage_teki.cpp`: env-gated production showcase
  (`PIKMIN_P2_KURAGE_SHOWCASE=1`). When set, the bound generated actor runs the
  transcribed source flight lifecycle (`pc_p2_kurage_fsm.h`) and logs its own
  position plus animation state/counter every 30 ticks
  (`P2_KURAGE_MOVE tick=... x=... y=... z=... state=... motion=... anim=...`) and
  each state transition (`P2_KURAGE_STATE`). After the autonomous Wait/Move patrol,
  one live Pikmin is seeded into the source suction window so the real Attack
  receiver can be observed. The default (env unset) production path is unchanged.
- `pc_port/pc_p2_kurage_receiver.cpp`: the one-consumer receiver now logs its real
  engine actions on live Pikmin (`P2_KURAGE_RECEIVER_HIT`, `..._ATTACH
  stick_before=0 stick_after=1`, `..._KILL alive_after=0`). Suction/ingestion logic
  is unchanged.
- `pc_port/pc_p2_kurage_teki.cpp`: `pc_p2_kurage_teki_forget` / `pc_p2_kurage_teki_reset`
  now log the central seam (`P2_KURAGE_TEKI_FORGET`, `P2_KURAGE_TEKI_RESET`). These are
  the exact hooks `pc_p2_forget_teki` (`pc_port/pc_p2_teki_lifetime.cpp:89`) and
  `GameCoreSection::exitStage` (`src/plugPikiKando/gameCoreSection.cpp:887`) call.
- `tools/p2_kurage_runtime.cpp`: new `--receiver-reentry` scenario exercising
  forget -> reset -> re-bind and asserting the old address no longer resolves and
  exactly one actor re-binds.

### Build evidence

`output/dsw/l29-build-evidence.txt`:
- `pikmin_pc` -> `bin/nectar.exe` sha256 `335c275302d61d19ef8c79aeb645bcca23c3c5d49e9aaa43b5c673442adeae79`
- `p2_kurage_runtime` -> `p2_kurage_runtime.exe` sha256 `ec7e51c760e1407976890e1bd67b4c5552c4b24efaa0b5d8156ca71f754e2902`
- native `50dde734`, Ninja MinGW g++ 16.2.0, Release, JAudio ON, `ninja -n` no work.

### Runtime evidence (real-GL, `slot.py run gl l29`)

Movement/animation + receiver — production `nectar.exe --experimental-pikmin2-room`
with `PIKMIN_P2_KURAGE_SHOWCASE=1`, `PIKMIN_P2_ROOM_WINDOW=960x540`; log
`output/dsw/l29-out/kurage-arena/b7439430e78b48b6ad2c9400f50f4b02/run.log`:

```
:763 P2_KURAGE_STATE tick=1 state=1 motion=6 altitude=28.756
:764 P2_KURAGE_MOVE tick=30 x=-39.581 y=84.680 z=21.077 state=1 motion=6 anim=0.00
:771 P2_KURAGE_MOVE tick=120 x=-22.735 y=4.051 z=40.301 state=2 motion=6 anim=0.00
:788 P2_KURAGE_MOVE tick=330 x=-42.177 y=3.090 z=-9.779 state=4 motion=10 anim=1.00
:793 P2_KURAGE_RECEIVER_HIT owner=... piki=...487910 phase=mouth alive=1 stick=0
:794 P2_KURAGE_RECEIVER_ATTACH owner=... piki=...487910 stick_before=0 stick_after=1 alive=1 scale=1.00
:852 P2_KURAGE_RECEIVER_KILL owner=... piki=...487910 alive_after=0
:4080 P2_KURAGE_MOVE tick=4080 x=37.077 y=42.977 z=120.282 state=1 motion=6 anim=0.00
```

136 sampled `P2_KURAGE_MOVE` lines span ticks 30..4080: the actor changes position in
all three axes and cycles Wait(1)/Move(2)/Attack(4)/FlyFlick(9) with the attack clock
advancing `anim` 0 -> 61. The receiver admits 13 live Pikmin, attaches them
(stick 0 -> 1) and digests one to `alive_after=0`. The run ended at the 150 s harness
deadline (`TIMEOUT`) at tick 4080.

Cleanup/re-entry — isolated `p2_kurage_runtime.exe --experimental-pikmin2-room
--receiver-reentry`; log `output/dsw/l29-out/kurage-reentry-run/stdout.log`:

```
:766 P2_KURAGE_TEKI_FORGET bound=1 corpse=0 remaining=0
:767 P2_KURAGE_REENTRY_FORGET forgotten=1 bound=0 stale=0
:770 P2_KURAGE_TEKI_RESET bound_before=1 corpse_before=0 bound_after=0 corpse_after=0
:774 P2_KURAGE_REENTRY_PASS reset=1 stale_bound=0 rebound=1
:775 PASS KURAGE_RUNTIME cleanup_reentry
```

### Bound six-gate table

Source ID: 57 Kurage (`source_id` 57, `BDT_Normal`).

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PARTIAL | output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log:727 (generated type-0 placement; source 57 identity not claimed) | stand-in body |
| 2. Autonomous movement and animation | PASS | output/dsw/l29-out/kurage-arena/b7439430e78b48b6ad2c9400f50f4b02/run.log:764 (P2_KURAGE_MOVE tick=30 .. :4080, 136 samples; states 1/2/4/9, anim 0->61) | natural source FSM; body stand-in labelled |
| 3. Attacks and receivers | PASS | output/dsw/l29-out/kurage-arena/b7439430e78b48b6ad2c9400f50f4b02/run.log:793 P2_KURAGE_RECEIVER_HIT, :794 ATTACH stick_before=0 stick_after=1, :852 KILL alive_after=0 | natural receiver on live Pikmin |
| 4. Death and corpse | PASS | output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log:808 P2_KURAGE_TEKI_DEAD, :813 CORPSE_CONFIG carry_min=7 carry_max=14 min_free_slot=0 | natural |
| 5. Actual transport and reward | PASS | output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log:855 P2_POD_RECEIPT id=corpse:kurage:201001 value=2 new=1 pokos=2 seeds=0 | natural |
| 6. Cleanup and re-entry | PASS | output/dsw/l29-out/kurage-reentry-run/stdout.log:766 FORGET, :770 RESET bound_before=1, :774 REENTRY_PASS stale_bound=0 rebound=1 | natural forget/reset seam |

Honest labels: the bound actor body is the generated type-0 stand-in, not the P2
Jellyfloat actor (gate 1 stays PARTIAL). The showcase seeds one live Pikmin into the
suction window as a fixture concession; the receiver, its attachment and the ingestion
kill are the real engine receiver. The default (non-showcase) production path is
byte-identical, so gates 4/5 keep their earlier run citations.

### Checker output

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md
```

## Diagnostic slice: gate 1 (identity_spawn)

Kurage is still one gate from admission: `identity_spawn` remains PARTIAL. This
diagnostic did not relabel the old sidecar auto-bind as natural.

### Preferred generated-seed route

The lane-04/05 generated-seed route is unavailable for source 57 in this lane's
baseline:

- `randomizer/p2_placement_catalog.py` has candidate specs for other families but
  no Kurage (`Kurage`/57) candidate.
- The wave `docs/PIKMIN2_ADMITTED_PLACEMENT.json` has accepted slot UIDs only for
  other identities (BlueKochappy and the elemental Otakara cohort); it has no
  Kurage profile and no `accepted_slot_uids` for 57.
- `scripts/run_p2_generated_seed.py` is absent from this lane's root baseline.
- The committed roster may list 57 as bindable, but lane 02's overlay still denies
  admission by default, and target tokens must come from lane 04 placement.

### Arena fallback attempt

A fresh private arena was staged with its real Kurage frog generator
(`_70=201001`) plus a private room-preview seed bridge:

- `output/dsw/l29-out/identity-spawn-57/6df7d329494542e0a2173268b7d5bf02/enemy-p2-57.txt`:
  `ENEMY_P2 1 <compiled-roster-revision> 1`, then `201001 57`.
- `.../p2-placement-slots.txt`: real room `_70` values mapped to placement-slot
  UIDs, including `201001 201001`.
- `.../p2-kurage-teki.txt`: `P2_KURAGE_TEKI_1 1 201001 0`.
- Runtime: `p2_kurage_runtime.exe --experimental-pikmin2-room
  --receiver-corpse-receipt --randomizer-seed enemy-p2-57.txt` with
  `PIKMIN_P2_ROOM_WINDOW=960x540` and `PYTHONUTF8=1`, run from
  `output/dsw/l29-out/identity-spawn-57/6df7d329494542e0a2173268b7d5bf02`
  through `py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l29`.

Exact rerun (from that run directory):

```powershell
$env:PIKMIN_P2_ROOM_WINDOW = "960x540"
$env:PYTHONUTF8 = "1"
$env:PATH = "C:\msys64\mingw64\bin;" + $env:PATH
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l29 -- C:/Users/alari/pikmin-randomizer/output/dsw/native-l29-build/p2_kurage_runtime.exe --experimental-pikmin2-room --receiver-corpse-receipt --randomizer-seed enemy-p2-57.txt
```

The process did not reach actor birth. Its failure marker is:

- `output/dsw/l29-out/identity-spawn-57/6df7d329494542e0a2173268b7d5bf02/native.log:382`:
  `[Pikmin Randomizer] unknown saved generator ID`

A one-record Kurage-only diagnostic profile failed at the same startup point, so
this is not merely an unmapped extra Pikmin/goal record. The relevant provider
flow is:

- `native/pc_port/pc_randomizer.cpp:619-628`: generator binding checks cataloged
  P1 spawn slots, then the `p2-placement-slots.txt` `_70` join.
- `native/pc_port/pc_randomizer.cpp:587-596`: an unmapped generator aborts with
  `unknown saved generator ID`.
- `native/src/plugPikiNakata/genteki.cpp:131-146`: `P2_SEED_RESOLVE` can only be
  emitted afterward, inside `GenObjectTeki::birth`.

No `P2_SEED_RESOLVE source_id=57` and no new `P2_KURAGE_TEKI_READY` exists in the
failed run. The older ready/binding citations remain fixture-bound, not natural.

### Verdict

`BLOCKED gate1: missing lane-04 accepted Kurage placement slot for source 57.`
A provider-owned mapping/behavior is also needed so the room-preview seed bridge
can pass its private `_70`→slot join without aborting generator load for the
rest of the staged room profile.

### Validator and tests

- `experimental/pikmin2_kurage_spawn.py`: inline-text validator requiring both
  `P2_SEED_RESOLVE source_id=57 target=...` and `P2_KURAGE_TEKI_READY
  generator=...` with the same generator/token mapping.
- `tests/test_pikmin2_kurage_spawn.py`: 5 passed, covering a passing sample,
  stripped-seed failure, seed/bind mismatch, bind-only failure, and an explicit
  nonnumeric-target mapping case.

```powershell
$env:PYTHONUTF8 = "1"
py -3.12 -m pytest tests/test_pikmin2_kurage_spawn.py -q
# .....  5 passed in 0.10s
```

### Build evidence used here

`output/dsw/l29-build-evidence.txt`:

- `p2_kurage_runtime` at native `50dde734928e402b2b1277920301628e89fb3fd3`, dirty=no, `p2_kurage_runtime.exe`
  sha256 `ec7e51c760e1407976890e1bd67b4c5552c4b24efaa0b5d8156ca71f754e2902`, `ninja -n` no work.
- `pikmin_pc` at native `50dde734928e402b2b1277920301628e89fb3fd3`, dirty=no, `bin/nectar.exe`
  sha256 `335c275302d61d19ef8c79aeb645bcca23c3c5d49e9aaa43b5c673442adeae79`, `ninja -n` no work.

No native source changes were made for this diagnostic slice; the native branch
remains at `50dde734...`, clean.

### Subagent usage

- Source audit: corroborated the room-bridge and `_70`/spawn-slot distinction.
- Candidate inventory: confirmed that no lane-04 Kurage candidate/profile and no
  lane-05 cohort-57 runner exists in the lane baseline.
- Test scaffolding: delivered the spawn validator/test shape; its sample-token
  semantics and marker-strip cases were used as-is.
- The failed GL diagnosis, handoff edit, build evidence, and final gate verdict
  were done directly, without letting subagents build, run fixtures, commit, or
  touch shared files.

### Checker output

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md
57 Kurage (role=source):
  1. identity_spawn     ignored [PARTIAL]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    accepted [PASS]
72 OniKurage (role=source): warning (shared table) - named in prose but no table of its own; give it a `Source ID` line + six-gate table to claim its gates
```

