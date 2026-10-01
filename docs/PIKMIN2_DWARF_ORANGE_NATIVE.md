# Lane 13 — Dwarf Orange Bulborb (BlueKochappy 44) native candidate

> Integration: root diagnostics and candidate evidence are in draft #432; this sweep does not integrate the native actor or promote its worker runtime results to combined acceptance.

Fan-out lane 13 (`#120`/`#197`), parent `#186`. This is the "one exact variant"
natural-chain slice: source identity, native registration, source health, a real
natural fight → death → corpse → render path, and a bounded arena fixture.

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: opencode (deepseek-v4.1-flash). Root branch
`opencode/p2-lane13-15` (base `codex/p2-main-review` `e514e6d`). Native
candidate branch `opencode/p2-lane13-orange-native` @
`2e3941c8d41fe541998b46e58b19179eb899dea7`, based on the approved native
baseline `f14c6851`. The native branch is private and is **not** on the
maintained line: lane 01 owns export/acceptance.

This doc supersedes the "native installation … NOT implemented" status in
`docs/PIKMIN2_DWARF_VARIANTS.md` §8 for BlueKochappy only. `KumaKochappy`
(Dwarf Bulbear) remains staged only.

## 1. Implemented native slice

New disjoint family module on the current native line, mirroring the proven
Dwarf Red (`pc_p2_kochappy`) pattern:

- `pc_port/pc_p2_dwarf_orange.{h,cpp}` + `pc_port/pc_p2_dwarf_orange_policy.h`.
  Reads `p2-dwarf-orange-{profile,bank,actors}.txt` (headers
  `P2_DWARF_ORANGE_PROFILE_1` / `_BANK_1` / `_ACTORS_1`), loads the converted
  `dwarf_orange_<clip>_<NN>.mod` pose bank, verifies every actor is
  `TEKI_Chappy` with a unique configured generator, binds source `health 250`
  and registers the purple-`Earthquake` receiver.
- Source variant rules preserved: health `fp00=250` and purple-pikmin stun
  `fp38=5 s` (vs Dwarf Red 10 s). `pc_p2_kochappy_stun_register()` now takes a
  per-actor fit duration; `p2purpleimpact::updateFit()` takes the duration
  argument instead of the fixed `RedFitDuration`.
- Additive hooks (no-op for unregistered actors): `pc_p2_dwarf_orange_setup`
  from `pc_p2_preview.cpp`, `pc_p2_dwarf_orange_draw` from both
  `tekibteki.cpp` draw chains, `pc_p2_dwarf_orange_reset`/`_forget` from the
  `tekimgr.cpp` lifecycle lists, and the `TPF_Life` chain in `include/teki.h`.
  `pc_p2_purple_impact.cpp` accepts either bulborb registration.

Source of truth: read-only decomp `native/pikmin2-research`
(`Game/Entities/KochappyBase.h`, `kochappyState.cpp`, `BlueKochappy.cpp`) and
the retail `bluekochappy/enemyparm.txt` block audited in
`docs/PIKMIN2_DWARF_VARIANTS.md` §2.

## 2. Build provenance

- Private worktree `output/native-lane13-orange` @
  `2e3941c8d41fe541998b46e58b19179eb899dea7` (native base `f14c6851`).
- Private build `output/native-lane13-orange-build`, Ninja / MinGW
  `g++.exe (Rev3, MSYS2 project) 16.2.0`, `Release`, `PIKMIN_NATIVE_JAUDIO=ON`,
  `-j 6`. Full build `[545/545] Linking CXX executable bin\nectar.exe`,
  `ninja -n` → `no work to do`.
- `nectar.exe` SHA-256
  `F72EF559FB45147FB7468D54C636E3DC6F6BFB871B84D470E195F5358DAEBCFD`.

## 3. Fixture and natural acceptance

Root tooling (new):

- `experimental/pikmin2_dwarf_orange_runtime.py` — arena/prepare/observer driver.
  The observer is the proven Red-dwarf combat observer
  (`experimental/pikmin2_kochappy_arena_combat.py`) transformed for
  BlueKochappy (ids `211001`/`211002`, module `pc_p2_dwarf_orange`, health
  250). It injects **no enemy state**: it only repositions the captain
  (ticks 1/120) and deploys the 20-red free squad around the source actor
  (tick 240), then observes.
- Instrumented fixture built by `scripts/build_pikmin2_fixture.py` against the
  private build: `output/p2-lane13-orange-fixture2/baseline/fixture.exe`
  (provenance `status=built`, two `ninja: no work to do` checks), SHA-256
  `AFBD26F1DFD42D312B1B4036E8F2CECB3B8668553A12FC2E03937E78DE0B4FC6`.
- Arena `output/p2-lane13-orange-arena/d230089a8d2b40799ab941779d3ce5db`
  (original P1 Impact Site map/collision preserved; `chal0`, generator ids
  `211001` Dwarf Orange + `211002` P1 Chappy control, scatter circle zeroed).
- Run log/evidence
  `…/d230089a8d2b40799ab941779d3ce5db/observe2/` (`native.log`,
  `evidence.json`); observed centred `960x540` window, 20-red direct squad, no
  extinction.

Key witness lines:

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001
  x=-150.0 y=30.0 z=1850.0 health=250.0 max_health=250.0 behavior=P1 purple_stun=bluekochappy_5s
P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000 texture_attach_calls=1
P2_DWARF_ORANGE_ARENA_BIRTH id=211001 x=-150.000 y=30.000 z=1850.000 health=250.0 fallback=130.0 red=1
P2_DWARF_ORANGE_ARENA_BIRTH id=211002 x=150.000 y=30.000 z=1550.000 health=130.0 fallback=130.0 red=0
P2_DWARF_ORANGE_DRAW corpse=0
P2_DWARF_ORANGE_DRAW corpse=1
DONE P2_DWARF_ORANGE_COMBAT
```

Combat metrics: first damage tick 24, zero-health tick 62, corpse tick 62;
health samples include 250→0; `state=11` chase with `target=1`; exit code 0.

## 4. Admission gates (this slice)

| Gate | Status | Evidence |
|---|---|---|
| A Identity/content | PASS (candidate) | `P2_ENEMY_READY source_id=44`, birth XYZ, converted `dwarf_orange` bank (64 poses) |
| B Source behavior | PARTIAL — host P1 AI; source health 250 and 5 s purple stun applied | ready marker + `P2_PURPLE_QUAKE` receiver path |
| C Combat/receivers | PASS at P1-proxy level | natural target/damage to 0 with a real squad; source-backed N/A for any P2-only attack |
| D Death/drop/transport | PASS at P1-proxy level | corpse spawned/drawn, then carried by the real squad to a goal (distance 341.2, `goal=1`); P2 reward untested |
| E Lifetime | BLOCKED | manager-swap precondition not met: the source actor is naturally killed by the overlay squad before the swap tick; needs a squad-free non-extinct baseline (#397) |
| F Persistence | PASS (identity/content across process restart) | two independent sequential runs publish identical `P2_ENEMY_READY source_id=44 health=250.0 max_health=250.0`, `P2_DWARF_ORANGE_BANK poses=64` and birth health/XYZ for 211001/211002; no save file changed; P2 reward duplication N/A (lane 06). `docs/PIKMIN2_DWARF_ORANGE_RESTART.md`, `output/p2-lane13-dwarf-orange-restart/restart.json` |
| G Product/mixed scene | BLOCKED | native candidate not integrated; no generated-session launch or mixed scene |

Injected evidence is absent in gates C and D: the only interventions are
captain/squad placement (combat) and the P1 carry task (delivery); enemy
health/state/animation are untouched.

### 3b. Delivery (gate D) and re-entry (gate E) probes

- `experimental/pikmin2_dwarf_orange_delivery.py` — transforms the proven Red
  P1-corpse delivery observer. Run
  `output/p2-lane13-orange-arena2/bd2b9fff954a474b88a7f6e467314cfc/deliver/`
  → PASS: `P2_DWARF_ORANGE_P1_HAUL` shows real TransportMode Pikmin carrying the
  corpse from `distance 59.2` to `341.2` with `goal=1`, then
  `PASS P2_DWARF_ORANGE_P1_DELIVERY … p2_receipts=not_applicable`. No carry task
  was injected (`transport_task_injected=false`).
- `experimental/pikmin2_dwarf_orange_reentry.py` — transforms the Red manager
  replacement observer. BLOCKED, reproducibly: in the plain arena the source
  actor engages and is killed by the overlay starting squad around tick 60, so
  the `observed==120` swap cannot preserve `oldRed`; stderr shows
  `FAIL p2 room: arena actor not live/unfrozen`. Relocating the overlay squad to
  a distant valid map point (`185,-180`) removes the fight but the engine then
  enters its result/movie flow (`P2_DWARF_ORANGE_ARENA_GATE … teki=1 …
  movie=1`), so `observed` stops advancing and the swap never runs. Both are
  shared fixture/lifecycle gaps (#397): a squad-free, non-extinct baseline that
  does not trip the day-flow is required. Recorded, not worked around by
  injecting enemy state or disabling extinction.

## 5. Limits and next consumer

- `behavior=P1` — the shared `KochappyBase::FSM` is not ported; the host P1
  AI approximates chase/attack/flick. The source notice cry
  (`PSSE_EN_KOCHAPPY_NOTICE`, wait1 frame 61), press timing and final death
  ordering are not claimed.
- Effects/glow, encounter placement legality and yaw are unmeasured.
- The measured `pc_p2_kochappy_stun` change is shared with Dwarf Red; lane 01
  must review it before this candidate reaches the maintained line.
- Next consumer: lane 01 integration; then lane 06 (transport/reward) and the
  #397 lifetime chain for gates D/E/F, and lane 02/33 for admission/QA.

## 6. Tests

- `tests/test_pikmin2_dwarf_orange_runtime.py` — observer transform (no Red
  identity/health left), all-pass witness, wrong-species/missing-corpse/
  extinction rejection, positions roster validation.
- `tests/test_pikmin2_dwarf_orange_chain.py` — delivery/re-entry transforms and
  evidence validation (including the blocked re-entry case).
- Native policy test `tools/p2_purple_impact_policy_test.cpp` adds the 5 s
  BlueKochappy fit case and the new `updateFit` signature (runs when lane 01
  exports the native line; the maintained `engine/` copy is untouched here).
- Existing dwarf-orange profile/bank/install/arena suites unchanged: 52 passed
  across the four lane-13 files.
