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
