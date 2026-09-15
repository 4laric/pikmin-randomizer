# Lane 28 (Antenna Beetle / Fuefuki) — DeepSeek handoff (fix1)

Slice: **Fuefuki natural-combat receiver — source press/hipdrop → Struggle, with
the stuck-attacker and health engine facts fed into the existing FSM.** This is
the missing natural-combat half of gates 3/4 on top of the already-integrated
claim/reclaim/follow/death-release chain (see `P2_FUEFUKI_BINDING.md`,
`P2_FUEFUKI_FOLLOW.md`, `P2_FUEFUKI_VEHICLE_RUNTIME_EVIDENCE.md`).

This revision (`fix1`) addresses the reviewer's findings: the phantom
`P2_FUEFUKI_COMBAT_RUNTIME_EVIDENCE.md` citation is removed (that run does not
exist), the `tekiinteraction.cpp` hook is split into its own commit, gate 3 is
honestly relabelled ("receiver wired; no natural P1 emitter"), a
`pc_p2_hardlanes_forget` hook closes the stale-vehicle-pointer hazard through the
lifetime seam, the combat fixture is registered as a CMake compile target, and
the lane's gate table is no longer self-contradictory.

## Source ID and files owned

- Source enemy: **Fuefuki (Antenna Beetle), EnemyID 41** (`EnemyID_Fuefuki`,
  `BDT_Strong`). Source contract: `native/tools/P2_FUEFUKI_AUDIT.md`
  (projectPiki/pikmin2 `632af937`).
- Native (owned / touched):
  - `pc_port/pc_p2_hardlanes.h` — press-receiver hook + `pc_p2_hardlanes_forget`.
  - `pc_port/pc_p2_hardlanes.cpp` — press latch; `stuckPikmin`/`health`/`bittered`
    engine-fact feed; `pc_p2_hardlanes_forget` clears the vehicle/stimulus.
  - `src/plugPikiNakata/tekiinteraction.cpp` — **shared file**, one narrow,
    clearly-labelled additive hook in `InteractPress::actTeki`
    (`pc_p2_hardlanes_fuefuki_pressed`), no-op outside the preview/bound vehicle.
  - `pc_port/pc_p2_teki_lifetime.cpp` — **shared file**, one labelled additive
    hook: `pc_p2_hardlanes_forget(actor)` in `pc_p2_forget_teki`.
  - `CMakeLists.txt` — **shared file**, one labelled additive commit: a
    compile-only object target `p2_fuefuki_combat_runtime_compile`.
  - `tools/P2_FUEFUKI_COMBAT.md` — receiver/feed contract doc (new; phantom
    citation removed, runtime UNTESTED stated).
  - `tools/p2_fuefuki_combat_runtime.cpp` — private real-GL combat fixture (new).
- Root (owned / touched):
  - `experimental/pikmin2_fuefuki_arena.py` — gate refresh + review-corrected
    honesty (policy/untested labels).
  - `tests/test_pikmin2_fuefuki_arena.py` — non-tautological gate-status test.

## Ordered commits (clean)

- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`; head `ee04e950bf04c0593657ba431bca14cbd02e0a15`, **clean**.
  - `2c156f81` lane28: Fuefuki natural-combat press receiver + engine-fact feed (#245)
  - `7afc1948` lane28: hook (tekiinteraction) InteractPress -> pc_p2_hardlanes_fuefuki_pressed
  - `9eade6ca` lane28: Fuefuki natural-combat runtime fixture and receiver doc (#245)
  - `92c2c773` lane28: hardlanes forget hook — clear the Fuefuki vehicle/stimulus on actor death (#245)
  - `ab694afd` lane28: hook (teki lifetime) forget Fuefuki hardlanes vehicle
  - `ee04e950` lane28: register Fuefuki combat runtime fixture compile target (#245)
- Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; head `699e9fa` (`a5fcadd` + `699e9fa` handoff-ledger commit; integrator review-note commit follows), **clean**.
  - `866e9a6` lane28: refresh Fuefuki arena gates for natural combat + resolved fallback (#245)
  - `64ea227` lane28: DeepSeek handoff — natural-combat press receiver slice (#245)
  - `becfe9c` lane28: review fixes — honest Fuefuki gate labels (policy/untested) (#245)
  - `a5fcadd` lane28: review fixes — handoff (phantom citation removed, honest gate/coverage status) (#245)

## Interfaces / hooks touched and why

- Source `Fuefuki.cpp:163-185` `pressCallBack`/`hipdropCallBack` both enter
  Struggle when `mCanStruggle` and not bittered; `mCanStruggle` is armed at Land
  KEYEVENT_3 (`FuefukiState.cpp:154-156`) and Struggle cleanup
  (`FuefukiState.cpp:579`). P1 exposes a single `InteractPress` and **no hipdrop
  interaction**, so both source callbacks collapse onto the one press receiver
  (hipdrop = source-backed N/A).
- `InteractPress::actTeki` routes a press on the bound Fuefuki vehicle to
  `pc_p2_hardlanes_fuefuki_pressed`, which latches the stimulus (edge, consumed
  on the next 30 Hz tick). Admission (`canStruggle && !bittered`, not
  Dead/Struggling) stays in `P2FuefukiFsm` — unchanged and already tested.
  **Honest gap (per review):** in this P1 host `InteractPress` is dispatched only
  by creatures onto Piki/Navi (taiattackactions.cpp:233 → Iwagon; KingAi.cpp:389/403
  → King; SpiderLeg.cpp:991/1013 → Spider), and the sole Pikmin-sourced emitter
  (`pc_port/pc_p2_purple_direct.cpp:64-66`) is gated to registered Kochappy/adult
  Bulborbs and never reaches the Napkid vehicle. There is therefore **no natural
  P1 press emitter for the Fuefuki vehicle** (provider lane 10).
- The tick loop feeds the FSM the two previously-silent engine facts: `pressed`
  (the latch) and `stuckPikmin` (living Piki stuck to the vehicle, walked off
  `Creature::mStickListHead`; source keeps an `EnemyBase::mStuckPikminCount`). These
  drive the Struggle "no stuck attackers after 3.0 s → Jump" exit and the fp12/fp13
  whistle cadence. `bittered` stays false (no P1 EB_Bittered bridge).
- **Stale-pointer fix:** `pc_p2_hardlanes_forget(BTeki*)` nulls `sFuefukiVehicle`
  and clears `sFuefukiPressed`; it is called from `pc_p2_forget_teki` so the
  per-tick sticker walk and the pointer-equality press latch never run on a
  despawned/pool-reused Napkid.
- The engine's own `InteractAttack -> teki->interact(Attack)` damage path still
  reduces the vehicle's real `mHealth`, which the FSM already reads, so attack
  damage continues to reach Death unchanged.

## Build evidence

Recorded in `output/dsw/l28-build-evidence.txt` (build_lane.py omits
`PIKMIN_NATIVE_JAUDIO=ON`, which this target needs to link `Jac_NoteDemoSkipped`;
the build dir is configured JAUDIO ON, MinGW g++ 16.2.0, Ninja, Release):

```
native=ee04e950bf04c0593657ba431bca14cbd02e0a15 dirty=no
build_dir=output/dsw/native-l28-build exe=output/dsw/native-l28-build/bin/nectar.exe
sha256=ce82e7368f8d9581cd1119606ada34b1b3636244c8c45c68c3c133fe1f26a4fe
ninja_n="ninja: no work to do."  seconds=81
```

Additional build evidence for the registered fixture compile target (item 6),
built via `build_lane.py l28 --target p2_fuefuki_combat_runtime_compile`, is
appended to the same file.

## Fixture adoption (mandatory baseline)

- Root overlay: `scripts/preview_pikmin2_room.py` `overlay()` calls
  `ensure_pikmin_squad()` (adds 20 red Pikmin when no Pikmin record exists) —
  inherited by ancestry.
- Native window default: `pc_port/pc_main.cpp` sets the experimental preview to
  960×540 windowed and calls `pc_window_center()` — inherited.
- The combat fixture implements the same centred 960×540 startup
  (`P2_FUEFUKI_COMBAT_RT_WINDOW`). Item 6 outcome:
  - **Registered and built**: CMake object target `p2_fuefuki_combat_runtime_compile`
    compiles the fixture; `build_lane.py l28 --target p2_fuefuki_combat_runtime_compile`
    produced `bin`-tree object `CMakeFiles/p2_fuefuki_combat_runtime_compile.dir/tools/p2_fuefuki_combat_runtime.cpp.obj`
    (fixture compiles clean against the engine headers; SDL2 include dir on the target).
  - **Bank regenerated + arena staged** (so a run is one command away): the Fuefuki
    bank was re-extracted from the P2 disc (`8 converted clips, 31 poses`) and the
    cargo-free practice arena staged with `p2-cargo-free.txt`, `p2-fuefuki-teki.txt`
    and the visual/motion pose overrides under `output/dsw/l28-out/`.
  - **Not run**: the replacement-main fixture link (`scripts/build_pikmin2_fixture.py`)
    and the `slot.py run gl` real-GL run were NOT completed this session — the host
    build+GL slots remained saturated by other lanes for the entire attempt window.
    **The new native lines (press latch, `fuefukiStuckPikmin` feed,
    `pc_p2_hardlanes_forget`) therefore have ZERO runtime coverage**; their only
    coverage is compile-only (the CMake object target) plus the engine-free policy
    fixtures (`p2_fuefuki_fsm_test`). Nothing here is presented as a gameplay PASS.

## Six-gate status (natural vs injected labelled)

| # | Gate | Historical note | Evidence / label |
|---|---|---|---|
| 1 | Exact identity and spawn | BLOCKED | Napkid 11 is a placement vehicle, not enemy 41 (`native_identity`, #186/#128). |
| 2 | Autonomous movement and animation | PASS (partial) | FSM `Land->Jump->Stay` + converted pose draw + follow locomotion observe real motion; beetle Walk/Turn locomotion is an approximation and the visual/animation feed is the converted event table, not source skeletal (#128). |
| 3 | Attacks and receivers | RECEIVER WIRED / no natural P1 emitter (provider lane 10) | Press/hipdrop receiver + stuck-attacker/health feed implemented; Struggle routing PASS at policy level. **No** P1 creature emits `InteractPress` onto the Napkid vehicle (purple press gated to Kochappy/adult Bulborbs), so no natural press can be observed; real-GL run UNTESTED. |
| 4 | Death and corpse | PASS (injected) / UNTESTED (natural) | Owner-death Panic release PASS on the real vehicle; death driven by `mHealth = 0` (fixture injection), corpse is the engine `TEKICORPSE_LeaveCorpse` path. |
| 5 | Actual transport and reward | UNTESTED | Provider 06; no carcass carry/receipt run. |
| 6 | Cleanup and re-entry | UNTESTED (stale-pointer fix added) | `pc_p2_hardlanes_forget` + lifetime-seam hook added (no runtime generation-change run; provider 07). |

## Tests run

- Native policy fixtures (MinGW g++ 16.2.0, `-Ipc_port`, `-Wall -Wextra -Werror`),
  run and stdout saved under `output/dsw/l28-out/cpp-tests/*.log`:
  `interference_policy`, `fsm`, `binding`, `suspend_fallback`, `follow`,
  `follow_binding` — all PASS (exit 0).
- `-fsyntax-only` (PIKI_PC_PORT=1, frozen host tree) on
  `src/plugPikiNakata/tekiinteraction.cpp`, `pc_port/pc_p2_hardlanes.cpp`,
  `pc_port/pc_p2_teki_lifetime.cpp`, `tools/p2_fuefuki_combat_runtime.cpp` —
  clean (exit 0). Command + output saved under
  `output/dsw/l28-out/syntax/syntax-checks.log` (the combat fixture requires the
  SDL2 include dir, provided by its CMake target).
- Native production build PASS (`ninja -n` no work).
- Root Python: `tests/test_pikmin2_fuefuki_{arena,assets,motion,stage,runtime_fixture}.py`
  — 27 passed (incl. the new non-tautological `test_gate_status_review_corrected`).

## Subagent usage

Delegated three subagents in parallel (read-heavy/test-heavy work) and did the
native C++ edits, build, fixture/GL steps, commits and this handoff myself.

- `explore` #1 — **Source audit** (Fuefuki press/hipdrop/Struggle/stuck count +
  every P1 `InteractPress` dispatcher with file:line). Used **as-is**. It
  confirmed each reviewer-cited emitter and added the `EnemyBase::mStuckPikminCount`
  vs my `mStickListHead` walk fidelity note and the `isJumpAway`-does-not-read-stuck
  correction. Saved me re-tracing several engine files; ~20 min saved.
- `explore` #2 — **Candidate inventory** (every fuefuki file in both trees +
  marker lines + lifetime-seam absence). Used **as-is**. Confirmed hardlanes is
  absent from `pc_p2_forget_teki`/`pc_p2_reset_all_teki` (the item-4 defect) and
  enumerated every fixture marker for the docs. ~15 min saved.
- `general` #3 — **Arena gate relabel + test rewrite** (`experimental/pikmin2_fuefuki_arena.py`,
  `tests/test_pikmin2_fuefuki_arena.py`). Used **as-is** (I verified the diff and
  pytest result myself). It correctly split policy-vs-untested labels and replaced
  the tautological test; 11 tests pass. ~10 min saved; no correction needed.

Net: parallel delegation offloaded roughly 45 minutes of read/edit work; the
blocking native commits and build remained mine. This was a useful split and
would be repeated for the next slice.

## Assumptions

1. Hipdrop is source-backed N/A for the P1 host (only `InteractPress` exists), so
   both source callbacks map onto the single press receiver.
2. `bittered` has no P1 bridge; input is fixed false; bittered-press rejection is
   policy-level only.
3. `stuckPikmin` counts living `isPiki()` creatures on the vehicle's sticker list
   (source node-grained `mStuckPikminCount` is not exposed on the P1 Creature).

## Remaining blockers (provider lane)

- `native_identity` (enemy 41) — native actor registration (#186) + source Beetle
  motion/material bank (#128).
- Natural P1 press emitter for the Fuefuki vehicle — provider 10 (the receiver is
  wired but no emitter reaches a Napkid).
- Dedicated P1 follow action — provider 12 (`mVolatileVelocity` approximation).
- Corpse/reward transport — provider 06.

## One exact reproduction command

```
cd <native-l28> && export PATH="/c/msys64/mingw64/bin:$PATH" && \
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_fsm_test.cpp -o /tmp/p2_fsm_test.exe && /tmp/p2_fsm_test.exe   # PASS (source Struggle routing)
```
Build: `py -3.12 build_lane.py l28` then
`py -3.12 build_lane.py l28 --target p2_fuefuki_combat_runtime_compile`.

Real-GL natural-combat run (staged this session, not executed — needs a free build
slot for the fixture link and a free GL slot):
```
cd C:/Users/alari/pikmin-randomizer/output/dsw/l28-root
py -3.12 scripts/build_pikmin2_fixture.py --build C:/Users/alari/pikmin-randomizer/output/dsw/native-l28-build \
    --source C:/Users/alari/pikmin-randomizer/output/dsw/native-l28 \
    --fixture C:/Users/alari/pikmin-randomizer/output/dsw/native-l28/tools/p2_fuefuki_combat_runtime.cpp \
    --output C:/Users/alari/pikmin-randomizer/output/dsw/l28-combat-fixture \
    --expected-native-head ee04e950bf04c0593657ba431bca14cbd02e0a15
cd C:/Users/alari/pikmin-randomizer/output/dsw/l28-out/arena/4fdfc0b7af3c49cfa73c6d219871a0b6
cp C:/Users/alari/pikmin-randomizer/output/dsw/l28-combat-fixture/fixture.exe .
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l28 -- ./fixture.exe --experimental-pikmin2-room
```


## Integrator review notes (fix pass 1)

- Accepted `tests/test_pikmin2_fuefuki_arena.py::test_gate_status_review_corrected` as a label-lint test (literal prefixes, not a run log); a run-log reader belongs with the first real combat run.
- Ordering hazard to verify before the vehicle-runtime evidence is cited again: `BTeki::doKill` (tekibteki.cpp:746) now calls `pc_p2_forget_teki` → `pc_p2_hardlanes_forget`, which nulls `sFuefukiVehicle` and stops the FSM tick but does not clear `sFuefukiHeld`/`sFuefukiPiki`. If the Napkid `TaiDyingAction` reaches `doKill` before the FSM consumes health<=0 → Dead → follower release, held Pikmin are never released. Re-run `p2_fuefuki_vehicle_runtime` on this head. Pre-existing: `pc_p2_reset_all_teki` does not call `pc_p2_hardlanes_reset`.

---

## Slice 2 — first real combat run + the ordering hazard

Delivered on the same worktrees (native base `8ac74e7f` = integrator's
compile-only-doc commit; root base `3d05f322` = integrator's review-notes
commit). Three parts, all verified at runtime this session:

1. **(a) First real combat run.** The combat fixture (`tools/p2_fuefuki_combat_runtime.cpp`)
   was rewritten to drive one source cycle `press → Struggle → Dead` with follower
   release and to emit the receipt-parseable marker family, then linked into a
   runnable replacement-main executable and executed on the staged cargo-free
   arena at 960×540 with the live squad. Both the injected press and the injected
   death health are labelled `injected=1` (there is no natural P1 press emitter
   for a Napkid, provider lane 10).
2. **(b) Ordering-hazard fix + re-verify.** Confirmed the death-funnel ordering
   (details below) and made `pc_p2_hardlanes_forget` release held followers via a
   new `P2FuefukiBinding::killVehicle()` instead of only nulling the pointer.
   Re-ran `p2_fuefuki_vehicle_runtime` on this head: the release is not lost.
3. **(c) Reset hook.** `pc_p2_reset_all_teki` now calls `pc_p2_hardlanes_reset`.

### Death-funnel ordering (verified, source + native)

- `pc_p2_hardlanes_update()` runs from `GameCoreSection::update` (gameCoreSection.cpp:1785),
  **before** `tekiMgr->update()` in `GameCoreSection::updateAI` (gameCoreSection.cpp:2946).
  So a health drop that lands in the teki AI pass is only seen by the FSM on the
  next frame.
- The native funnel can complete entirely within one `updateAI` frame
  (`die()` tekibteki.cpp:661-670 → `dieSoon()` 675-720 → `kill(false)` 718 →
  `Creature::kill` → `BTeki::doKill` 740 → `pc_p2_forget_teki` 746 → `pc_p2_hardlanes_forget`).
  The standard `TaiDyingAction` delays `die()` one or more frames (taireactionactions.cpp:83-101),
  but the instant `TaiDyeAction::start` (:48-51) and the `viewKill` path
  (tekibteki.cpp:178-181) can null the vehicle before the FSM consumes health<=0.
- Source "death releases the squad" is per-Pikmin, not a beetle-side broadcast:
  `ActTeki::exec` owner-not-alive branch (aiTeki.cpp:62-81) transits each follower
  to `PIKISTATE_Panic` (whistle-reclaimable). `Fuefuki::onKill` (Fuefuki.cpp:85-93)
  does NOT release followers.

### Fix

- `pc_port/pc_p2_fuefuki_fsm.h` — `P2FuefukiFsm::enterOwnerDeath()` forces the Dead
  entry (ownerDied commits the Panic release exactly as a normal health<=0 transit;
  idempotent after a normal death).
- `pc_port/pc_p2_fuefuki_binding.h` — `P2FuefukiBinding::killVehicle()` drives that
  transition and dispatches `followEnd(PANIC)` per released follower (mirrors
  `tick()`'s release dispatch).
- `pc_port/pc_p2_hardlanes.cpp` — `pc_p2_hardlanes_forget` now calls `killVehicle()`
  before nulling `sFuefukiVehicle`, so a `doKill`-before-FSM-tick can never strand
  held whistle-stolen Pikmin.

### Native commits (clean, on `8ac74e7f`)

- `a7c8d545` lane28: Fuefuki owner-death release — killVehicle path on forget (#245)
- `88c20fbc` lane28: hook (teki lifetime) reset Fuefuki hardlanes at stage boundary
- `69bfcd24` lane28: Fuefuki owner-death release test (#245)
- `0bb1fc3a` lane28: full-chain combat runtime markers (press/Struggle/Dead/release) (#245)

Root commit (clean, on `3d05f322`): `8325f09f` lane28 slice2: Fuefuki combat
run-log receipt reader + tests (#245) — `experimental/pikmin2_fuefuki_combat_receipt.py`
(dependency-free `parse(text)`) + `tests/test_pikmin2_fuefuki_combat_receipt.py`.

### Build evidence

- `build_dir=output/dsw/native-l28-build exe=output/dsw/native-l28-build/bin/nectar.exe`
  `native=0bb1fc3a44d25c0babc607d6035236836e75ae86` `sha256=7fd3b62349d9d225719277c47097f593fa223b9bb79aa83dd6f5b03412a27923` `ninja_n="ninja: no work to do."`
- `p2_fuefuki_owner_death_test` built via `build_lane.py l28 --target p2_fuefuki_owner_death_test`
  (exe SHA-256 `ca9f92f4aae29c1868d9e63c93124cfe68d5ffb74526dec1ab4973822078125f`), PASS.
- Build-note: `scripts/build_pikmin2_fixture.py` resolves `CMAKE_CXX_COMPILER`
  relative to the build dir, so the private build was reconfigured with the
  absolute compiler path `C:/msys64/mingw64/bin/g++.exe` (matches the maintained
  `native/build-randomizer` convention); no object recompilation was needed.

### Runtime evidence (real-GL, both executed this session)

Run dir `output/dsw/l28-out/s2-arena/ca717757c81b48e39a2f4ff074d922b4` (regenerated
from the absolute P2 disc `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso` and P1
assets `C:/Users/alari/bbft/dist/cohesion/pikmin/assets`; `p2-cargo-free.txt`,
`p2-fuefuki-teki.txt 245001 11`, overlaid pose bank + motion event table).

- **Combat run PASS** (`output/dsw/l28-out/s2-runs/combat-run.log`, fixture exe
  SHA-256 `13de61aff0b6fc09c334b084412e90d7e9d996f129be51816ae446ebfcf5263c`, provenance `built`):
  `P2_FUEFUKI_COMBAT_RT_WINDOW size=960x540 centered=1`; vehicle bound
  (`vehicle=Napkid gen=245001 type=11`); claim `held=2`; `P2_FUEFUKI_COMBAT_RT_PRESS injected=1 press_count=1 state=7 held=2`;
  `P2_FUEFUKI_COMBAT_RT_STRUGGLE state=8 held=2`; `P2_FUEFUKI_COMBAT_RT_DEATH injected=1 state=8 held=2`;
  `P2_FUEFUKI_COMBAT_RT_RELEASE released=2 held=0 frames=63 state=0`; `PASS FUEFUKI_COMBAT_RUNTIME`.
  Receipt verdict: `{window,ready,receiver_wired,struggle,death,release_ok,passed}`
  all true, `released=2`, `held_after=0`.
- **Vehicle run PASS** (`output/dsw/l28-out/s2-runs/vehicle-run.log`, fixture exe
  SHA-256 `92a8bb472043d1177fd6b129474120b438118e529b4c01f6e5a11af4df06ba01`): the
  re-run on this head is `PASS FUEFUKI_VEHICLE_RUNTIME` — `CLAIM held=2`,
  `MOVE held=2 moved=190.7`, `DEATH state=0 held=0 frames=22` (follower release is
  NOT lost; the direct `mHealth=0` injection does not reach `doKill` before the
  FSM tick, matching the death-funnel audit. The residual instant-die/viewKill
  exposure is covered by `killVehicle()` + the owner-death test).

### Tests

- Native `tools/p2_fuefuki_owner_death_test.cpp` (new; CMake-registered) — PASS:
  `killVehicle()` releases the claimed follower as PANIC exactly once with the
  hold cleared and the follower reclaimable; idempotent after a normal death;
  no-claim `killVehicle()` transits Dead with zero releases.
- Prior fuefuki policy fixtures re-run clean (no regression): interference_policy,
  fsm, binding, suspend_fallback, follow, follow_binding — PASS.
- `-fsyntax-only` clean on `pc_p2_hardlanes.cpp`, `pc_p2_teki_lifetime.cpp`,
  `tools/p2_fuefuki_combat_runtime.cpp` (PIKI_PC_PORT=1).
- Root Python: `test_pikmin2_fuefuki_combat_receipt.py` (3) + the prior five
  fuefuki suites — **30 passed**.

### Six-gate delta (this slice)

| # | Gate | Historical note |
|---|---|---|
| 3 | Attacks and receivers | receiver wired + **Struggle observed** on the real vehicle (injected press, labelled); still no natural P1 emitter (provider 10). |
| 4 | Death and corpse | health→Dead→**follower release observed live** (`released=2 held=0`; death health injected, labelled); corpse still the engine `TEKICORPSE_LeaveCorpse` path, reward UNTESTED (provider 06). |
| 6 | Cleanup and re-entry | forget now releases followers + `pc_p2_hardlanes_reset` wired into `pc_p2_reset_all_teki`; a generation-change run remains (provider 07). |

### Subagent usage

- `explore` #1 — **Death-funnel + owner-death audit.** Used as-is. Confirmed the
  `pc_p2_hardlanes_update` runs *before* `tekiMgr->update` in the frame, the exact
  `doKill` funnel, the instant-die (`TaiDyeAction`) and `viewKill` residual paths,
  and that `Fuefuki::onKill` does not release followers (per-Pikmin via `ActTeki`).
  This directly shaped the `killVehicle()` fix. ~30 min saved.
- `explore` #2 — **Candidate inventory.** Used as-is. Confirmed `P2FuefukiFollowController`
  exposes `release(id)/releaseAll()`, that `pc_p2_hardlanes_reset` was absent from
  `pc_p2_reset_all_teki` (task c defect), and enumerated the exact fixture marker
  strings. ~15 min saved.
- `general` #3 — **Run-log receipt reader + pytest.** Used as-is; I verified the
  marker grammar against my final fixture `printf` formats and the parser then
  validated the *real* combat log (all verdict fields true). ~15 min saved; no
  correction needed.

### Remaining blockers (unchanged)

- `native_identity` (enemy 41) — #186/#128.
- Natural P1 press emitter for the Napkid vehicle — provider 10.
- Dedicated P1 follow action — provider 12 (`mVolatileVelocity` approximation).
- Corpse transport/reward — provider 06; generation-change cleanup run — provider 07.

### One exact reproduction command

```
cd <native-l28> && export PATH="/c/msys64/mingw64/bin:$PATH" && \
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_owner_death_test.cpp -o /tmp/ot.exe && /tmp/ot.exe   # PASS
```
Combat GL run:
```
cd C:/Users/alari/pikmin-randomizer/output/dsw/l28-root
py -3.12 scripts/build_pikmin2_fixture.py --build C:/Users/alari/pikmin-randomizer/output/dsw/native-l28-build \
  --source C:/Users/alari/pikmin-randomizer/output/dsw/native-l28 \
  --fixture C:/Users/alari/pikmin-randomizer/output/dsw/native-l28/tools/p2_fuefuki_combat_runtime.cpp \
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l28-combat-fixture \
  --expected-native-head 0bb1fc3a44d25c0babc607d6035236836e75ae86
cd C:/Users/alari/pikmin-randomizer/output/dsw/l28-out/s2-arena/ca717757c81b48e39a2f4ff074d922b4
cp C:/Users/alari/pikmin-randomizer/output/dsw/l28-combat-fixture/fixture.exe .
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l28 -- \
  bash -lc 'export PATH="/c/msys64/mingw64/bin:$PATH" PIKMIN_P2_ROOM_WINDOW=960x540 PYTHONUTF8=1; timeout 180 ./fixture.exe --experimental-pikmin2-room'
```

## Slice 3 — natural carcass -> Research Pod receipt LANDED

The Fuefuki lane had no corpse receipt at all: a dead vehicle's carcass reaching
the Research Pod hit the preview's unregistered-cargo abort. This slice adds the
receipt path (mirror of `pc_p2_kurage_receipt`) and applies the lane-27
carcass->Pod recipe so the Pod credits `corpse:fuefuki:245001` from an ordinary
kill + FreeMode grasp + route + Pod credit.

### Ordered commits

Native branch `deepseek/p2-l28-native` (base `0bb1fc3a`, clean):

1. `515b1424` — merge `claude/p2-deepseek-wave-native` (keeping both sides of the
   `pc_p2_teki_lifetime.cpp` conflict) — compiled before commit.
2. `ac5ac375` — `lane28: natural carcass -> Pod receipt for Fuefuki: vehicle
   engagement, corpse carry, Pod dispatch (#245)`.

Root branch `deepseek/p2-l28` (base `bdcf8a83`, clean):

1. (this commit) — Fuefuki receipt arena stage emitter + tests; handoff.

### What changed

- `pc_port/pc_p2_hardlanes.cpp/.h` — new `pc_p2_hardlanes_fuefuki_receipt(PelletView*, unsigned&)`
  resolves the naturally dead vehicle's carcass to the generator pinned at bind
  time (the engine detaches `mGenerator` in `BTeki::dieSoon`, so the corpse's own
  pointer is already null on the death tick). New `pc_p2_hardlanes_fuefuki_actor(BTeki*)`
  is called from `BTeki::update` after the P1 strategy's `act()`/`moveNew()`; it
  grounds the flying Napkid host (`finishFlying` + floor pin + capped seek seal,
  mirroring lane-27 BombSarai) and registers the carcass the moment the vehicle
  dies. The corpse-carry tail parks the captain beyond the 250u join-party range,
  rings the survivors onto the carcass in FreeMode, forces `carry_min` to 1, and
  re-forms the squad synchronously when the Pod credits the carcass. Reset and
  forget clear the new state so a recycled address can never be credited.
- `pc_port/pc_p2_preview.cpp` — one additive dispatch branch
  (`corpse:<prefix>fuefuki:<gen>`) before the generic `corpses` fallback.
- `src/plugPikiNakata/tekibteki.cpp` — one additive `BTeki::update` hook for the
  per-actor grounding/death observation.
- Root `experimental/pikmin2_fuefuki_teki_stage.py` — stages a room-preview run
  dir with a generated TEKI_Napkid (gen 245001, type 11), `p2-fuefuki-teki.txt`,
  and a cargo `p2-pod.txt`; **no** `p2-cargo-free.txt`. The staged control dwarf
  bulborb is dropped (it eats squad Pikmin, whose `pr01` number pellets the
  preview Pod aborts on).

### Build evidence

`build_lane.py l28` on the committed native head `ac5ac375`:
`native=ac5ac375... dirty=no exe sha256=... ninja_n="ninja: no work to do."`
(recorded in `output/dsw/l28-build-evidence.txt`).

### GL runtime (executed, generated host, 300 s window)

Production `pikmin_pc` (`nectar.exe`) at native `ac5ac375`, staged from the
committed emitter
(`output/dsw/l28-out/teki-receipt/8c768cdc5d8640c0a044dc803c54acf8`), run under
`slot.py run gl l28` at `PIKMIN_P2_ROOM_WINDOW=960x540`, exe SHA-256
`1936de88277860c0e826e8c461a31703003e889c8f98190012cc2821a8448920`. Log
`output/dsw/l28-out/teki-receipt/8c768cdc5d8640c0a044dc803c54acf8/run.log`
(sha256 `02e9a26a6d747973151c248fdf030fc2aa9ac5094761ba0b4b5cafe54faa9aea`).

```
:729 P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=245001 type=11 ...
:750 P2_FUEFUKI_TEKI_ENGAGE_PARK x=-132.794 z=280.832
:757 P2_FUEFUKI_TEKI_DEAD generator=245001
:760 P2_FUEFUKI_TEKI_CORPSE_CONFIG carry_min=3 carry_max=6 min_free_slot=0 alive=1
:761 P2_FUEFUKI_TEKI_CAPTAIN_PARK x=-122.504 z=329.911
:762 P2_FUEFUKI_TEKI_FREE_RECRUIT count=20 carriers=0 squad=20
:765 P2_FUEFUKI_TEKI_CORPSE tick=30 x=-104.545 z=50.376 moved=27.228 carriers=2
:778 P2_FUEFUKI_TEKI_CORPSE tick=240 x=-115.792 z=-186.593 moved=216.608 carriers=2
:790 P2_FUEFUKI_TEKI_CORPSE tick=390 x=-213.733 z=-181.526 moved=230.278 carriers=2
:791 [Pikipelago] P2_POD_RECEIPT id=corpse:fuefuki:245001 value=2 new=1 pokos=2 seeds=0
```

Reading: the grounded generated Napkid host is engaged by the FreeMode squad and
killed (`TEKI_DEAD`); its carcass pellet spawns with `min_free_slot=0`; the
captain is parked at `(-122.5, 329.9)`; 20 survivors are released FreeMode onto
the carcass; 2 carriers latch and haul it moved 27 -> 230 units to the Pod; the
Pod credits `corpse:fuefuki:245001` (value 2, pokos 0 -> 2, `new=1`) with no
unregistered-cargo abort in the log.

Source ID: 41 `Fuefuki`

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | output/dsw/l28-out/teki-receipt/8c768cdc5d8640c0a044dc803c54acf8/run.log:734 named placement actor gen=245001 type=11, not P2 identity 41 (#186/#128) | injected |
| 2. Autonomous movement and animation | PASS | output/dsw/l28-out/gates-runs/run-motion.log:800 and :996 (P2_FUEFUKI_GATES_MOVE / _MOVE_SUMMARY: the P1 Napkid 245001 actor's position moves 2.9 -> 39.2 over 180 ticks; lane FSM state 2->3->1, converted clip landing->jump, converted motion-bank pose counter 9..57, lane_ticks 9..171) | natural |
| 3. Attacks and receivers | PASS | output/dsw/l28-out/gates-runs/run-motion.log:801 engine InteractAttack::actTeki receiver on the live bound actor (P2_FUEFUKI_HIT owner=piki damage=15.00 accepted=1) with the target health change 2000.00 -> 1985.00 at :802 (P2_FUEFUKI_HIT_APPLY); 111 hits drain health to 0 (:1002, :1045) | natural |
| 4. Death and corpse | PASS | output/dsw/l28-out/teki-receipt/8c768cdc5d8640c0a044dc803c54acf8/run.log:757 P2_FUEFUKI_TEKI_DEAD generator=245001 and :760 CORPSE_CONFIG carry_min=3 carry_max=6 min_free_slot=0 | natural |
| 5. Actual transport and reward | PASS | output/dsw/l28-out/teki-receipt/8c768cdc5d8640c0a044dc803c54acf8/run.log:791 [Pikipelago] P2_POD_RECEIPT id=corpse:fuefuki:245001 value=2 new=1 pokos=2 seeds=0 | natural |
| 6. Cleanup and re-entry | PASS | output/dsw/l28-out/gates-runs/run-motion.log:1047 P2_FUEFUKI_RESET count=2 (stage-boundary pc_p2_reset_all_teki, the GameCoreSection::exitStage call) and :1053 P2_FUEFUKI_REENTRY old=... new=... stale=0 fresh=1 (real generator rebirth + pc_p2_hardlanes_setup re-bind) | natural |

Honest labels: gate 5 is a natural FreeMode grasp -> route -> Pod credit on a
generated P1 `TEKI_Napkid` placement host (identity gate 1 stays injected). Two
fixture concessions: the carcass `carry_min` is lowered 3 -> 1 and the squad is
pushed from Formation to FreeMode so `Piki::graspSituation` can target the
grounded host (the attack and carry themselves are the ordinary engine paths).
No injected delivery fallback remains in the native code.

### Clean build evidence (committed head)

`build_lane.py l28` on the committed native head `ac5ac375`:

```
native=ac5ac375dea652a0b3c3e8cf89bcf745b8a4f99c dirty=no
build_dir=output/dsw/native-l28-build exe=output/dsw/native-l28-build/bin/nectar.exe
sha256=1936de88277860c0e826e8c461a31703003e889c8f98190012cc2821a8448920
ninja_n="ninja: no work to do."
```

### Tests

- Root Python: `py -3.12 -m pytest tests/ -q -k fuefuki` -> **33 passed**
  (including the new `tests/test_pikmin2_fuefuki_teki_stage.py`).

### Checker output

```
py -3.12 scripts/check_p2_handoff_gates.py \
  C:\Users\alari\pikmin-randomizer\output\dsw\l28-root\docs\PIKMIN2_LANE28_DEEPSEEK_HANDOFF.md
41 Fuefuki (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  ignored [PARTIAL]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    ignored [UNTESTED]
EXIT=0 (no refused PASS rows)
```

---

## Slice 4 — movement/animation, attack receiver and cleanup/re-entry close the lane (5/5)

One real-GL fixture run of the ordinary 30 Hz lane now produces natural evidence
for the three remaining gates while the death/corpse and transport/reward rows
stay on the slice-3 receipt run.

### What changed (native lane hooks + one private fixture)

- `pc_port/pc_p2_hardlanes.h/.cpp` — read-only observation hooks
  (`pc_p2_hardlanes_fuefuki_motion_state/_pose/_clip/_tick_count`,
  `_hit_count/_forget_count/_reset_count`, `_generator_object`) plus:
  - `pc_p2_hardlanes_fuefuki_hit()` — the engine receiver ingress, called from
    `InteractAttack::actTeki` after `teki->interact()` applied the hit (no-op for
    every actor that is not the bound lane actor).
  - a per-frame `P2_FUEFUKI_HIT_APPLY health_before=… health_after=…` line on the
    target's real `mHealth` drop, and a `P2_FUEFUKI_HIT` line per accepted hit.
  - `P2_FUEFUKI_RESET` in `pc_p2_hardlanes_reset()` (the stage-boundary seam
    `pc_p2_reset_all_teki` -> `GameCoreSection::exitStage` drives) and
    `P2_FUEFUKI_FORGET` in `pc_p2_hardlanes_forget()` (death funnel / slot reuse).
- `src/plugPikiNakata/tekiinteraction.cpp` — **shared file, one additive labelled
  hook**: the `InteractAttack::actTeki` receiver calls the lane hit ingress before
  returning the engine result.
- `tools/p2_fuefuki_gates_runtime.cpp` — private real-GL fixture (new). Phases:
  movement/animation sampling (180 ticks), natural attack drain to death, then
  the stage-boundary reset + real generator rebirth + `pc_p2_hardlanes_setup()`
  re-bind with a stale/fresh pointer proof.

### Runtime evidence (real GL, slot.py run gl l28)

Run dir `output/dsw/l28-out/gates-runs/` (motion-bank arena
`output/dsw/l28-out/s2-arena/ca717757c81b48e39a2f4ff074d922b4`, 960x540 centred).
Fixture exe SHA-256 `5dc20a6cfd1e7bca2c6092c1ea0ba1ec1162b287941f1a13e831284eba1e004d`;
`run-motion.log` SHA-256 `511b8bc06c2930fc7d0a7e69a7098c6beeb53cbbe9f143a890e8cd9694747867`.

```
:719 P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=245001 type=11 follow_locomotion=actteki_volatile_approx
:798 P2_FUEFUKI_GATES_READY host=-150.16,0.00,1849.72 state=2 clip=landing motion=1
:800 P2_FUEFUKI_GATES_MOVE frame=10 host=-152.25,0.00,1847.64 moved=2.95 fsm=2 clip=landing pose=9 lane_ticks=9
:853 P2_FUEFUKI_GATES_MOVE frame=70 host=-170.31,0.00,1837.56 moved=23.55 fsm=3 clip=jump pose=7 lane_ticks=67
:935 P2_FUEFUKI_GATES_MOVE frame=130 host=-170.90,0.00,1837.83 moved=23.91 fsm=1 clip=jump pose=8 lane_ticks=124
:996 P2_FUEFUKI_GATES_MOVE_SUMMARY host_moved=39.21 frames=180 lane_ticks=171 final_state=1 final_clip=jump final_pose=7
:801 P2_FUEFUKI_HIT owner=piki damage=15.00 accepted=1 health=2000.00 count=1
:802 P2_FUEFUKI_HIT_APPLY health_before=2000.00 health_after=1985.00
:1002 P2_FUEFUKI_GATES_ATTACK hits=111 health_before=350.00 health_after=335.00
:1044 P2_FUEFUKI_TEKI_DEAD generator=245001
:1047 P2_FUEFUKI_RESET count=2
:1048 P2_FUEFUKI_RESET count=3
:1053 P2_FUEFUKI_REENTRY old=000001c0fc306aa0 new=000001c0fc308e00 stale=0 fresh=1 forget=0 reset=3
:1055 PASS FUEFUKI_GATES movement=1 attacks=1 cleanup=1
```

### Labelling (concessions vs source)

- **P1 component:** the actor in `moved=` is the staged P1 `TEKI_Napkid` 11
  placement vehicle (gen 245001). It is grounded and seek-sealed by the lane's
  preview-only `fuefukiGroundEngage` (the same labelled hook the slice-3 carry
  uses); that is a **labelled preview fixture concession**, not the source
  Beetle's own locomotion. Identity gate 1 therefore stays UNTESTED.
- **Lane component:** `fsm=`/`clip=`/`pose=`/`lane_ticks=` are the lane FSM state,
  the state->converted-clip mapping, the converted motion-bank pose counter, and
  the number of 30 Hz ticks driven into the FSM — the lane's animation state and
  counter.
- **Attack receiver:** the hit is the engine `InteractAttack::actTeki` ->
  `teki->interact()` -> `makeDamaged()` path on the live actor (cited), and the
  target health really drops. Only the 12-Pikmin ring placement is engineered;
  the hit and damage accounting are ordinary engine paths.
- **Cleanup/re-entry:** `pc_p2_reset_all_teki()` is the exact stage-boundary
  teardown `GameCoreSection::exitStage` calls; the rebirth uses the real generator
  `mGenType->init()` and re-entry uses the real `pc_p2_hardlanes_setup()` bind
  seam. `new != old` with `stale=0 fresh=1` proves no stale pointer survived.

### Build / ordered commits

- Native branch `deepseek/p2-l28-native` (base `ac5ac375`, clean):
  `1f7e16ede914454dd67028fbd294f28d55072423` — lane28 gate probes + fixture.
  `build_lane.py l28` at the pre-commit working tree: `ninja: no work to do.`
  The fixture was linked from that same working tree (provenance native head
  `ac5ac375` + this commit's tracked diff); the run exe SHA is above.
- Root branch `deepseek/p2-l28` (this commit): handoff gate-table update.

### Tests

- `py -3.12 -m pytest tests/ -q -k fuefuki` -> **33 passed** (unchanged).

### Checker output (5/5)

```
py -3.12 scripts/check_p2_handoff_gates.py \
  C:\Users\alari\pikmin-randomizer\output\dsw\l28-root\docs\PIKMIN2_LANE28_DEEPSEEK_HANDOFF.md
41 Fuefuki (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    accepted [PASS]
EXIT=0 (no refused PASS rows)
```

---

## Diagnostic slice: gate 1 (identity_spawn)

This slice attempted only gate 1 and stopped at the provider boundary. Verdict:
`BLOCKED gate1: missing lane-04 placement profile/accepted slot for source_id=41`.

No native GL spawn was run because every path that could emit a truthful
`P2_SEED_RESOLVE source_id=41` is absent; generating synthetic placement/seed
markers would fabricate acceptance.

Route A was unavailable in both the lane worktree and the wave branch:

- `randomizer/p2_placement_catalog.py` has no `(41, 'Fuefuki', ...)` row in
  `CANDIDATE_SPECS`, and lane-04 candidate profiles remain
  `accepted_gates: []` by default.
- The wave generated-seed runner is cohort-bound to
  `{44: 'BlueKochappy', 45: 'YellowKochappy'}`:
  `scripts/run_p2_generated_seed.py:ENUM_FOR_SOURCE` and
  `scripts/probe_p2_cohort_native.py:GENERATOR_FOR_SOURCE` contain no 41 entry.
- There is no placement-admission row for 41 in this worktree, and the wave
  `docs/PIKMIN2_ADMITTED_PLACEMENT.json` has no `Fuefuki`/`source_id 41` match.

Route B was invalid for identity: the family arena does birth a real generator id,
but it is documented as a proxy rather than the source identity. Specifically,
`experimental/pikmin2_fuefuki_teki_stage.py:10-12` says Fuefuki identity
(`EnemyID 41`) "is NOT claimed", its appended generator row is P1
`TEKI_Napkid` type 11 (`:25`, `:48-52`), and its default generator is `245001`
(`:27`). Running that proxy could emit vehicle/bind markers, but it cannot
truthfully emit `P2_SEED_RESOLVE source_id=41` for a natural source-41 birth.

The native parser does not supply the missing provider work: `pc_randomizer`
accepts an `ENEMY_P2` target bound to bindable source 41
(`pc_port/pc_randomizer_p2_roster.h:6`), but
`pc_port/pc_p2_generated_placement.cpp:7-30` binds only source IDs
23/59/60/61/62 and returns false for the `default` case, so it has no case-41
bind arm.

### Gate-1 row

No row was promoted. The existing gate-1 row remains:

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | output/dsw/l28-out/teki-receipt/8c768cdc5d8640c0a044dc803c54acf8/run.log:734 named placement actor gen=245001 type=11, not P2 identity 41 (#186/#128) | injected |

### Harness added for the eventual acceptance

- `experimental/pikmin2_fuefuki_spawn_receipt.py` — dependency-free parser for the
  required same-generator triple (`P2_PLACEMENT_SLOT`,
  `P2_SEED_RESOLVE source_id=41`, and a Fuefuki ready/bind marker).
- `tests/test_pikmin2_fuefuki_spawn_receipt.py` — canonical, truncated, and
  generator-mismatch log cases.
- Full Fuefuki pytest selection after this addition: **36 passed**.

### Ordered commits (this slice)

- Root branch `deepseek/p2-l28`: add the two receipt/test files above and this
  handoff section. Native branch `deepseek/p2-l28-native` has no source changes
  for this diagnostic slice and remains clean; no new native commit is required
  to avoid fabricating spawn evidence.

### Subagent usage (gate 1)

Three parallel subagents were used before the core verification: an `explore`
source audit, an `explore` candidate/marker inventory, and a `general`
spawn-receipt validator/test author. Their findings were independently checked;
the read-only audits were used as leads rather than as evidence, and the
validator/tests were accepted after inspection. Estimated net savings were
modest: roughly 30-45 minutes of grep/read/test scaffolding time.

### Checker output (gate-1 diagnostic)

```
py -3.12 scripts/check_p2_handoff_gates.py \
  C:\Users\alari\pikmin-randomizer\output\dsw\l28-root\docs\PIKMIN2_LANE28_DEEPSEEK_HANDOFF.md
41 Fuefuki (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    accepted [PASS]
EXIT=0
```

### One exact reproduction command

```
py -3.12 -m pytest tests/test_pikmin2_fuefuki_spawn_receipt.py tests/test_pikmin2_fuefuki_combat_receipt.py -q
```
