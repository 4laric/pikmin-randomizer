# Lane 28 (Antenna Beetle / Fuefuki) — DeepSeek handoff

Slice: **Fuefuki natural-combat receiver — source press/hipdrop → Struggle, with
the stuck-attacker and health engine facts fed into the existing FSM.** This is
the missing natural-combat half of gates 3/4 on top of the already-integrated
claim/reclaim/follow/death-release chain (see `P2_FUEFUKI_BINDING.md`,
`P2_FUEFUKI_FOLLOW.md`, `P2_FUEFUKI_VEHICLE_RUNTIME_EVIDENCE.md`).

## Source ID and files owned

- Source enemy: **Fuefuki (Antenna Beetle), EnemyID 41** (`EnemyID_Fuefuki`,
  `BDT_Strong`). Source contract: `native/tools/P2_FUEFUKI_AUDIT.md`
  (projectPiki/pikmin2 `632af937`).
- Native (owned / touched):
  - `pc_port/pc_p2_hardlanes.h` — new press-receiver hook declaration.
  - `pc_port/pc_p2_hardlanes.cpp` — press latch + `stuckPikmin`/`health`/`bittered`
    engine-fact feed into the FSM tick.
  - `src/plugPikiNakata/tekiinteraction.cpp` — **shared file**, one narrow,
    clearly-labelled additive hook in `InteractPress::actTeki`
    (`pc_p2_hardlanes_fuefuki_pressed`), no-op outside the preview/bound vehicle.
  - `tools/P2_FUEFUKI_COMBAT.md` — receiver/feed contract doc (new).
  - `tools/p2_fuefuki_combat_runtime.cpp` — private real-GL combat fixture (new).
- Root (owned / touched):
  - `experimental/pikmin2_fuefuki_arena.py` — gate refresh (add `press_combat`,
    resolve `brain_fallback`).
  - `tests/test_pikmin2_fuefuki_arena.py` — matching gate assertions.

## Ordered commits (clean)

- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`; head `ddbe3733176893cb3a129325925ba88cd1559e25`, **clean**.
  - `b1d7e283` lane28: Fuefuki natural-combat press receiver + engine-fact feed (#245)
  - `086c360d` lane28: Fuefuki natural-combat runtime fixture and receiver doc (#245)
  - `ddbe3733` lane28: fix press-marker field label (#245)
- Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; head `866e9a6`, **clean**.
  - `866e9a6` lane28: refresh Fuefuki arena gates for natural combat + resolved fallback (#245)

## Interfaces / hooks touched and why

- Source `Fuefuki.cpp:163-185` `pressCallBack`/`hipdropCallBack` both enter
  Struggle when `mCanStruggle` and not bittered. P1 exposes a single
  `InteractPress` and **no hipdrop interaction**, so both source callbacks
  collapse onto the one press receiver (hipdrop = source-backed N/A).
- `InteractPress::actTeki` now routes a press on the bound Fuefuki vehicle to
  `pc_p2_hardlanes_fuefuki_pressed`, which latches the stimulus (edge, consumed
  on the next 30 Hz tick). Admission (`canStruggle && !bittered`, not Dead/
  Struggling) stays in `P2FuefukiFsm` — unchanged and already tested.
- The tick loop now feeds the FSM the two previously-silent engine facts:
  `pressed` (the latch) and `stuckPikmin` (live Piki stuck to the vehicle, walked
  off `Creature::mStickListHead`), which drive the source Struggle "no stuck
  attackers after 3.0 s -> Jump" exit and the fp12/fp13 whistle cadence.
  `bittered` stays false (no P1 EB_Bittered bridge); the bittered-press
  rejection path remains policy-level only.
- The engine's own `InteractAttack -> teki->interact(Attack)` damage path still
  reduces the vehicle's real `mHealth`, which the FSM already reads, so natural
  attack damage continues to reach Death unchanged.

## Build evidence

Recorded in `output/dsw/l28-build-evidence.txt` (build_lane.py omits
`PIKMIN_NATIVE_JAUDIO=ON`, which this target needs to link `Jac_NoteDemoSkipped`;
configured+build via a slot-wrapped manual cmake, MinGW g++ 16.2.0, Ninja,
Release, JAudio ON):

```
native=ddbe3733176893cb3a129325925ba88cd1559e25 dirty=no
build_dir=output/dsw/native-l28-build exe=output/dsw/native-l28-build/bin/nectar.exe
sha256=114d6a4d7abfbaac8a40be3d579d187e7244f27e7eb3e533cf6d6216928a7a83
ninja_n="ninja: no work to do."  (production link 603/603)
```

## Fixture adoption (mandatory baseline)

- Root overlay: `scripts/preview_pikmin2_room.py` `overlay()` calls
  `ensure_pikmin_squad()` (adds 20 red Pikmin when no Pikmin record exists) —
  inherited by ancestry (root head `866e9a6` on `ef1cace`).
- Native window default: `pc_port/pc_main.cpp` sets the experimental preview to
  960×540 windowed and calls `pc_window_center()` — inherited (native head on
  `b805d9c6`).
- The new combat fixture implements the same centred 960×540 startup and live
  starting-squad assumptions (`P2_FUEFUKI_COMBAT_RT_WINDOW`). The fixture source
  is syntax-validated warning-clean against the frozen host tree. Because the
  Fuefuki converted pose/motion bank must be regenerated from the P2 ISO
  (`pikmin2_fuefuki_assets --source ...`) and was not re-extracted this session,
  the combat fixture was **not run**; the real-GL press→Struggle runtime
  acceptance remains UNTESTED.

## Six-gate status (natural vs injected labelled)

| # | Gate | Status | Evidence / label |
|---|---|---|---|
| 1 | Exact identity and spawn | BLOCKED | Napkid 11 is a placement vehicle, not enemy 41 (`native_identity`, #186/#128). |
| 2 | Autonomous movement and animation | PASS (partial) | FSM `Land->Jump->Stay` + converted pose draw + follow locomotion observe real motion; beetle Walk/Turn locomotion is an approximation and the visual/animation feed is the converted event table, not source skeletal (#128). |
| 3 | Attacks and receivers | PASS (policy) / UNTESTED (natural) | Press/hipdrop receiver wired (this slice); Struggle routing PASS in `p2_fuefuki_fsm_test`; a real `InteractPress` on the live vehicle is NOT yet observed (see below). |
| 4 | Death and corpse | PASS (injected) / UNTESTED (natural) | Owner-death Panic release PASS on the real vehicle; death was driven by `mHealth = 0` (fixture injection), corpse is the engine `TEKICORPSE_LeaveCorpse` path. |
| 5 | Actual transport and reward | UNTESTED | Provider 06; no carcass carry/receipt run. |
| 6 | Cleanup and re-entry | UNTESTED | `pc_p2_hardlanes_reset` exists but the preview is single-scene; no generation-change run (provider 07). |

## Tests run

- Native policy fixtures (MinGW g++ 16.2.0, `-Ipc_port`, `-Wall -Wextra -Werror`):
  `interference_policy`, `fsm`, `binding`, `suspend_fallback`, `follow`,
  `follow_binding` — all PASS (no regression from the header changes).
- `-fsyntax-only` on `src/plugPikiNakata/tekiinteraction.cpp` and
  `pc_port/pc_p2_hardlanes.cpp` against the frozen host tree — clean (exit 0).
- Full production build PASS (603/603, JAudio ON); `ninja -n` no work.
- Root Python: `tests/test_pikmin2_fuefuki_{arena,assets,motion,stage,runtime_fixture}.py`
  — 27 passed.

## Assumptions

1. Hipdrop is source-backed N/A for the P1 host (only `InteractPress` exists), so
   both source callbacks map onto the single press receiver.
2. `bittered` has no P1 bridge; input is fixed false and the bittered-press
   rejection remains policy-level coverage.
3. `stuckPikmin` counts living `isPiki()` creatures on the vehicle's sticker list
   (no height/collision refinement).

## Remaining blockers (provider lane)

- `native_identity` (enemy 41) — native actor registration (#186) + source Beetle
  motion/material bank (#128).
- Dedicated P1 follow action — provider 12 (the `mVolatileVelocity` approximation
  remains labelled).
- Corpse/reward transport — provider 06.
- Real-GL natural combat (press→Struggle) — needs a regenerated Fuefuki asset bank
  (`experimental.pikmin2_fuefuki_assets --source <P2 iso>`) + the serialised GL
  slot; not completed this session.

## One exact reproduction command

```
cd <native-l28> && export PATH="/c/msys64/mingw64/bin:$PATH" && \
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_fsm_test.cpp -o /tmp/p2_fsm_test.exe && /tmp/p2_fsm_test.exe   # PASS (source Struggle routing)
```
Build: `py -3.12 slot.py run build l28 -- bash <wave>/l28_build.sh` (configures
Ninja/JAudio ON and builds `pikmin_pc`).
