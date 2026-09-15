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
- Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; head `a5fcadd`, **clean**.
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
