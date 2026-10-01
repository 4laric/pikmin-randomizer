# Muse contributor l65 — Honeywisp (Qurione) natural flight and Egg-reward handoff (#505)

Implementation owner: Codex through shared GitHub account `4laric`. Executing
contributor: Muse Spark 1.3 through OpenCode
(`opencode/muse-spark-1.3-contributor-free`), lane `muse-honeywisp`.
Parent #166; wave #491; integration #437/#186.

## Scope delivered

Bounded slice: validate Qurione-16 flight and the natural player-contact /
Egg-to-nectar reward against actual decomp source; corpse hauling is a
source-backed N/A; no pellet reward is invented. Prioritized honest gate:
**gate 5 (`transport_reward`) source-backed N/A case**, with gate 3
(`attacks_receivers`) source-backed N/A analysis as supporting work.
Accepted gates 1/4/6 are preserved and distinguished (same-wisp second
appearance vs new-actor re-entry via generator continuity).

Read first: lane-15 fix5 handoff (`docs/PIKMIN2_LANE15_DEEPSEEK_HANDOFF.md`
§3.4) and source audit (`docs/PIKMIN2_QURIONE_LIFECYCLE.md`). The wave report
ranks Qurione near ADMIT; that claim was re-verified citation by citation
below and is **not** taken as fresh evidence.

## Source verification (this lane, read-only decomp @ `632af93787b9c95b63f0c13be32b161375ce3a96`)

- Qurione birth attaches a carried Egg: `attachItem()` births
  `EnemyTypeID_Egg` (37) and `startCapture()`s it to the `water` joint
  (`src/plugProjectNishimuraU/Qurione.cpp:284-296`).
- Release is once-only: `dropItem()` calls `endCapture()` and nulls `mEgg`
  (`Qurione.cpp:302-307`); `StateDrop` fires it on Damage `KEYEVENT_2`, then
  `KEYEVENT_END → dead` (`QurioneState.cpp:214-224`).
- No carcass anywhere: `EB_LeaveCarcass` is disabled on Qurione
  (`Qurione.cpp:57`) and on the Egg (`src/plugProjectMorimuraU/egg.cpp:38`);
  `mDropGroup = EDG_None` (`Qurione.cpp:60`).
- Egg break births field items: `genItem()` (`egg.cpp:243-383`) — Single/Double
  nectar as `HONEY_Y`, mitite group with `HONEY_Y` fallback (`egg.cpp:351-360`).
  Number-pellet branches (`egg.cpp:294-306`) require `mForcedDropType`
  (`egg.cpp:277-279`), which defaults to 0 (`Egg.h:124`) and is never assigned
  on the Qurione path — so a Honeywisp Egg rolls nectar/mitites only.
- No attack path: the only creature callback is `flyCollisionCallBack`
  (`Qurione.cpp:136-144`) — Piki contact in `QURIONE_Move` transits to Drop.
  The wisp is `EB_Untargetable` + `EB_Invulnerable` (`Qurione.cpp:52-53`).
- Flight: `StateMove::exec` runs `moveFaceDir()` and transits past `mFlyDist`
  200 (`QurioneState.cpp:172-187`); `moveFaceDir()` bobs about
  `minY + fp03*sin(pitch) + fp01` (`Qurione.cpp:210-220`). Stay re-appears when
  `mUtilityTimer > 1.0` and `isAppear()` (nearest Pikmin/Navi in
  viewAngle/sightRadius, `Qurione.cpp:253-265`).

## Six-gate table (PIKMIN2_ENEMY_ROSTER.md §Gate table format)

- Source ID: 16 `Qurione`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l15-out/arena-runs/4eb9093898ff4d8a9e73110675683570/drop-run.log:748 | natural (preserved lane-15 fix5 evidence, re-validated read-only by experimental/pikmin2_muse_honeywisp.py) |
| 2. Autonomous movement and animation | PARTIAL (one full cycle, re-appear stalls without nearby squad) | output/dsw/l15-out/arena-runs/4eb9093898ff4d8a9e73110675683570/qurione-run.log:793-797 | natural (preserved lane-15 fix5 evidence, re-validated read-only; dz=161.2 over 3 distinct Move positions, 0 =nan) |
| 3. Attacks and receivers | N/A (source: no attack; contact is the Drop trigger) | src/plugProjectNishimuraU/Qurione.cpp:136-144 flyCollisionCallBack | natural (source-backed; contact trigger observed in output/dsw/l15-out/arena-runs/4eb9093898ff4d8a9e73110675683570/drop-run.log:769) |
| 4. Death and corpse | PASS (natural) | output/dsw/l15-out/arena-runs/4eb9093898ff4d8a9e73110675683570/drop-run.log:777,782 | natural (preserved lane-15 fix5 evidence, re-validated read-only) |
| 5. Actual transport and reward | N/A (reward is field-consumed nectar; no receivable item) | src/plugProjectMorimuraU/egg.cpp:243-289 genItem | natural (source-backed; real DoubleNectar birth observed in output/dsw/l15-out/arena-runs/4eb9093898ff4d8a9e73110675683570/drop-run.log:773-775) |
| 6. Cleanup and re-entry | PASS (natural) | output/dsw/l15-out/arena-runs/4eb9093898ff4d8a9e73110675683570/cleanup6-run.log:782,800 | natural (preserved lane-15 fix5 evidence, re-validated read-only; same wisp: one BIND, 2 appears, generator=203001, single FORGET) |

Gate 5 note: the carried Egg breaks into `HONEY_Y` honey absorbed in place
(never `ACT_Transport`); pellets are unreachable (`mForcedDropType` stays 0);
neither Qurione nor Egg leaves a carcass. There is no lane-06 receipt to wait
for, so N/A keeps the ledger from blocking on a receipt that cannot exist.
Gate 2 note: the flight leg is real (finite Move displacement, pitch-bob
velocity) but re-appear needs a Pikmin/Navi inside sight; the new
`sustained-flight` fixture (below) parks the squad in the sight ring so a
future run can close this gate without changing any owned native source.

`scripts/check_p2_handoff_gates.py` output for this file is recorded in the
child issue; N/A/PARTIAL rows are intentionally non-advancing (integrator
review decides).

## Files owned and changed (private worktrees only)

Root `output/msw/l65-root` (branch `codex/muse-l65-honeywisp`):

- `experimental/pikmin2_muse_honeywisp.py` (new) — source-fact registry
  (`GATE5_NA_CASE`, `GATE3_NA_CASE`, `GATE2_SOURCE`) plus a runtime-log
  validator (`gate_status()`) that grades identity/movement/contact/reward/
  death/re-entry and distinguishes same-wisp re-appearance from new-actor
  re-entry by generator continuity.
- `tests/test_pikmin2_muse_honeywisp.py` (new) — 16 tests, all hermetic
  synthetic logs; NaN/frozen/broken-chain/non-nectar/double-bind regressions.
- `docs/PIKMIN2_MUSE_HONEYWISP_HANDOFF.md` (new) — this file.

Native `output/msw/native-l65` (branch `codex/muse-l65-honeywisp-native`):

- `native/tools/p2_muse_honeywisp_fixture.cpp` (new) — sustained-flight
  replacement-main fixture: parks reds in the sight ring (inside SIGHT 200,
  outside HIT_RADIUS 30) so Stay re-triggers across cycles without tripping
  Drop; emits `P2_QURIONE_MUSE_*` cycle markers for the observer.
- `native/pc_port/pc_p2_qurione.cpp` / `.h` / `pc_p2_qurione_policy.h` —
  **unchanged** (inherited lane-15 fix5 implementation verified correct
  against source; no defect reproduced, so no edit).

No shared-file changes. No Egg/shared-host changes (none needed; consumer use
of lane-20 `P2Egg` policy is already integrated).

## Tests and validation

- `py -3.12 -m pytest tests/test_pikmin2_muse_honeywisp.py -q` → 16 passed.
- Read-only re-validation of preserved lane-15 fix5 logs with the new observer:
  `output/muse-wave/l65/legacy-revalidation.txt` (drop: contact→2 real nectar→
  dead; qurione-run: 3 Move positions dz=161.2, 0 NaN; cleanup6: same-wisp
  2 appears, single forget).
- Private leased build + `ninja -n` dry run + fixture provenance build:
  recorded in the child issue with executable SHA-256.

## Remaining work

- Gate 2 closure needs one fresh GL run of the new sustained-flight fixture
  (built, provenance-recorded, not yet run): sustained Move displacement across
  ≥2 re-appeared cycles with 0 NaN. No source change is expected.
- Gate 5/3 N/A admission is an integrator decision; this handoff supplies the
  source case and the supporting natural observations.
