# Gatling Groink carcass regeneration and replacement-object revival (lane 21, #198/#209/#210)

Implementation owner: Codex through shared account `4laric`. Executing agent:
opencode (deepseek-v4-pro). This lane resumes the **parked Codex** carcass /
lifetime candidates (see supersession chain below) and adds a typed birth
descriptor + Python twin + tests, for the Gatling Groink (MiniHoudai 78,
roaming) and fixed pedestal variant (FminiHoudai 97).

## Supersession chain

The first lane-21 slice (`88373a12`) reimplemented `pc_p2_groink_carcass.{h,cpp}`
under the same file names with an incompatible free-function/POD API and was
rejected. The native branch was reset to `b805d9c6` and the parked Codex work
resumed by cherry-pick:

- `codex/p2-groink-carcass` @ `8324a5a0` → native `45697128`
  (`pc_port/pc_p2_groink_carcass.{h,cpp}`, `tools/p2_groink_carcass_test.cpp`,
  `tools/P2_GROINK_CARCASS.md`).
- `codex/p2-groink-lifetime` @ `14d9391d` → native `016a3b77`
  (`pc_port/pc_p2_groink_lifetime.h`, `tools/p2_groink_lifetime_test.cpp`,
  `tools/P2_GROINK_LIFETIME.md`).

On top, native `5f5cf5fe` adds the `P2GroinkCarcassBirth` descriptor (host-side
payload for the `RequestBirth` command) and CMake test-target wiring for
`p2_groink_carcass_test` and `p2_groink_lifetime_test`. The parked modules'
class/API, command ordering and semantics are preserved unchanged.

## Source contract

Mirrored from `MiniHoudai::Obj::doBecomeCarcass` / `doUpdateCarcass`
(`src/plugProjectNishimuraU/MiniHoudai.cpp:282-325`):

- `doBecomeCarcass` zeroes `mHealth` and `mHealthGaugeTimer` only; position,
  base matrix, `mExistDuration`, `mInPiklopedia`, `mMaxHealth` survive.
- Each update, while the carcass pellet is alive:
  - `mHealthGaugeTimer` (fp11 `"死亡 ～ ゲージ出現"`, default 30s) elapses first
    with no health change; the life gauge appears when it reaches the parameter
    (`ActivateGauge`).
  - then health regens at `mMaxHealth / mRespawnRate` per second (fp12
    `"ゲージ出現 ～ 復活"`, default 10s), **never clamped**.
  - at `mHealth >= mMaxHealth` the pellet is killed, then a **new** same-type
    object is born from `generalEnemyMgr->birth` at the old position / face-dir
    (`atan2(baseZx, baseZz)`) / existence length / Piklopedia flag; on success
    the old object transits to `MINIHOUDAI_Rebirth`. The pellet is killed
    *before* the birth attempt, so a failed birth leaves the pellet killed and
    the owner released, and no automatic retry occurs.
- A pellet dead before the gauge appears leaves the carcass dead. A pellet dead
  after it resets the gauge timer/health and inactivates the gauge once. Both
  gauge commands are gated on the life-gauge manager existing.

## Native API (kept as parked)

`pc_p2_groink_carcass.h`:
```cpp
struct P2GroinkCarcassConfig { float gaugeDelay, recoverySeconds, maxHealth; };
enum class P2GroinkCarcassCommand { ActivateGauge, KillPellet, RequestBirth, DeactivateGauge };
class P2GroinkCarcass {
  bool become(const P2GroinkCarcassConfig&);
  void reset();
  P2GroinkCarcassStep step(float delta, bool pelletAlive, bool gaugeManager, bool activeTick=true);
  // ready()/timer()/health()
};
```
`step` emits the four commands in the source order; it never self-marks a
terminal, so a failed host birth is expressed by the host reporting
`pelletAlive=false` on the next tick (dead-pellet branch). Health is never
clamped.

`pc_p2_groink_lifetime.h`: `P2GroinkLifetime` host registration guard —
generation-qualified opaque handles, single pending revival ticket via
`beginRevival`/`finishRevival`, fail-closed serial exhaustion, safe
same-address reuse.

Added `P2GroinkCarcassBirth { position; faceDir; existenceLength; inPiklopedia; }`
— the typed host payload matching the source `EnemyBirthArg` fields the Groink
populates at revival.

## Build and test evidence

Native branch `deepseek/p2-l21-native` head `5f5cf5fe` on base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Private lane build dir
(Ninja + MinGW g++, JAUDIO ON, OPTIMIZE OFF).

- `pikmin_pc` builds clean; `ninja -n` reports no work to do; `bin/nectar.exe`
  SHA-256 `9dd6f5d3…` (recorded in the lane 21 build-evidence file; see the lane 21 handoff).
- All ten `p2_groink*` CTests pass, including `p2_groink_carcass_test` and the
  newly wired `p2_groink_lifetime_test`. CTest log: lane 21 evidence dir `ctest-groink-all.log` (see the lane 21 handoff).

## Gate table (six gates, natural vs injected)

1. **Identity and spawn** — source-backed N/A: no new actor registration; the
   policy attaches to the existing MiniHoudai/FminiHoudai identity.
2. **Movement and animation** — UNTESTED: locomotion and Rebirth animation
   (`AnimID 7`) remain on the shared actor hook.
3. **Attacks and receivers** — unchanged: the integrated strike bridge carries
   shell hits to receivers; in-flight natural moving hits remain fixture-pinned.
4. **Death and corpse** — source-backed policy + unit-proven; BLOCKED naturally:
   the full-health step returns `KillPellet` + `RequestBirth` commands, but the
   actual pellet kill / `onKill` drop path needs the live actor.
5. **Transport and reward** — source-backed N/A: no reward changes (lane 06 owns
   drops/cargo).
6. **Cleanup and re-entry** — BLOCKED: `P2GroinkLifetime` provides the guard, but
   real `generalEnemyMgr->birth` + `MINIHOUDAI_Rebirth` transit wiring is the
   pending shared actor hook.

No injected state is promoted to a gameplay PASS.
