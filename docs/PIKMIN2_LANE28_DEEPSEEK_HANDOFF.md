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

| # | Gate | Status | Evidence / label |
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

| # | Gate | Status |
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
