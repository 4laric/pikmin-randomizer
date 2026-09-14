# Gatling Groink carcass regeneration and replacement-object revival (lane 21, #198/#209)

Implementation owner: Codex using shared account `4laric`. Executing agent:
opencode (deepseek-v4-pro), 2026-09-14. This advances the parked lane-21 Groink
stack one bounded step: a source-faithful carcass / revival state machine for
the Gatling Groink (MiniHoudai 78, roaming) and fixed pedestal variant
(FminiHoudai 97). It closes the "source revival/carcass recovery" half named as
the next-wave follow-on to the already-integrated shell-strike bridge
(`pc_p2_groink_hit` / `pc_p2_groink_strike`).

## Scope and boundary

One source enemy ID (#78 MiniHoudai) plus its fixed variant (#97), one missing
end-to-end slice: **death/corpse recovery** — the carcass pellet's gauge delay,
health regeneration and replacement-object rebirth. This is a pure host policy,
deliberately engine-free: it has no pellet, life-gauge manager, enemy-manager
birth or FSM dependency, so the shared `teki.h` / `tekimgr.cpp` /
`gameCoreSection.cpp` actor hook is not required.

## Source contract

Mirrored from `MiniHoudai::Obj::doBecomeCarcass` / `doUpdateCarcass`
(`src/plugProjectNishimuraU/MiniHoudai.cpp:282-325`):

- `doBecomeCarcass` zeroes `mHealth` and `mHealthGaugeTimer` while the object's
  position / face direction / existence duration / Piklopedia flag survive for
  the eventual replacement birth.
- Each update, while the carcass pellet is alive:
  - `mHealthGaugeTimer` (fp11 `"死亡 ～ ゲージ出現"`, default 30s) elapses first
    with no health change; the life gauge appears when it reaches the parameter.
  - then health regenerates at `mMaxHealth / mRespawnRate` per second (fp12
    `"ゲージ出現 ～ 復活"`, default 10s) until it reaches full health.
  - at full health the pellet is killed and a **new** same-type object is born
    from `generalEnemyMgr->birth` at the old position / face direction (from the
    base matrix `zx/zz`) / existence length / Piklopedia flag; the old object
    transits to `MINIHOUDAI_Rebirth`. Replacement object, not same-object
    resurrection.
- A pellet dead before the gauge appears leaves the carcass dead (no revival, no
  gauge activity). A pellet dead after the gauge has appeared resets the gauge
  timer/health and inactivates the gauge once.

## What it adds

- Native `pc_port/pc_p2_groink_carcass.{h,cpp}`: `P2GroinkCarcass` /
  `P2GroinkCarcassParms` / `P2GroinkCarcassBirth` state and
  `p2_groink_carcass_become` / `p2_groink_carcass_step` mirrors. Events are
  `GaugeActive`, `Revive` (with a `P2GroinkCarcassBirth` descriptor the host
  acts on), and `GaugeInactive`. Invalid parms or non-positive delta reject
  without mutation; a revived carcass is terminal.
- Native CTest `tools/p2_groink_carcass_test.cpp` (registered in CMake next to
  the other Groink tests).
- Root Python twin `experimental/pikmin2_groink_carcass.py` and
  `tests/test_pikmin2_groink_carcass.py` (10 tests) keeping the root suite in
  lock-step with the native contract.

## Build and test evidence

Native branch `deepseek/p2-l21-native` on base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Private build dir
`output/dsw/native-l21-build` (Ninja + MinGW g++, `-DPIKMIN_NATIVE_JAUDIO=ON
-DPIKMIN_NATIVE_OPTIMIZE=OFF`, configured with the Python-bundled
`ninja.exe` as `CMAKE_MAKE_PROGRAM`).

- `pikmin_pc` builds clean; `ninja -n` reports no work to do; `bin/nectar.exe`
  SHA-256 recorded in `output/dsw/l21-build-evidence.txt`.
- CTest `p2_groink_carcass_test` passes; all nine `p2_groink*` CTests pass.
- Root `test_pikmin2_groink_carcass.py` passes (10 tests).

## Gate table (honest)

| Gate | Verdict |
|---|---|
| A. Identity and spawn | source-backed N/A here — no new actor registration; the policy is host-consumed by the existing MiniHoudai/FminiHoudai identity. |
| B. Declared behavior | FAIL (natural) — autonomous carcass regeneration is implemented as pure policy and unit-proven, but no real Groink actor runs it yet. |
| C. Attacks and receivers | not changed — the integrated strike bridge carries shell hits to receivers; in-flight natural moving hits remain fixture-pinned as before. |
| D. Death and corpse | source-backed policy + unit-proven (native + Python), BLOCKED naturally — a real carcass pellet requires the live actor / `onKill` drop path. |
| E. Lifetime | BLOCKED — replacement birth (`generalEnemyMgr->birth`) and `MINIHOUDAI_Rebirth` transition are the pending shared actor hook. |
| F. Persistence | UNTESTED — source has no serialization of carcass/regen state (see cannon/groink audit). |

This is a source-faithful FSM slice, not a gameplay PASS. Natural death/corpse,
revival and re-entry remain blocked on the real MiniHoudai actor registration
over the shared `teki.h` / `tekimgr.cpp` / `gameCoreSection.cpp` hook and lane
06/07 reward/lifetime semantics.
