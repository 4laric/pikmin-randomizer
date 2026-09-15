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

| Gate | Result | Evidence / note |
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

| Gate | Slice 2 result |
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
