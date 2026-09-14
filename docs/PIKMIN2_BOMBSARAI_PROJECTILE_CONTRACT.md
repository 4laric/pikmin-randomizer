# Pikmin 2 Careening Dirigibug bomb projectile lifecycle contract (#244)

Implementation owner: Codex using shared account 4laric. Parent #166, integration contract #186, terrain/clock pattern #169. Source audit: [PIKMIN2_BOMBSARAI_AUDIT.md](PIKMIN2_BOMBSARAI_AUDIT.md). This is an isolated policy milestone, not a playable enemy: no shared hooks, no converter/build changes, no native actor registration.

## Scope

Lane-owned files, native branch `codex/p2-bombsarai-policy` (based on native `b1d0089c`):

- `pc_port/pc_p2_bombsarai_bomb.h` / `.cpp` — isolated bomb-rock projectile lifecycle policy.
- `pc_port/pc_p2_bombsarai_clock.h` — bounded 30 Hz source-clock adapter, lane-owned copy of the #169 Groink pattern (`pc_p2_groink_clock.h`).
- `tools/p2_bombsarai_bomb_test.cpp`, `tools/p2_bombsarai_clock_test.cpp` — standalone fixture executables.

Source reference is projectPiki/pikmin2 revision `632af93787b9c95b63f0c13be32b161375ce3a96` (US GPVE01 rev 0); line numbers below follow the audit.

## Clock contract

The policy samples no wall clock. The host feeds elapsed seconds into `P2BombSaraiSourceClock::step` and runs the source update exactly once per returned tick (`kSourceDelta = 1/30 s`). Inactive, negative, non-finite or ≥0.25 s gaps discard all accumulated debt; a stall caps at four ticks and cannot become a later burst. Explicit throw/death events stay outside the clock so the host can hold a pending event until a source tick consumes it. `P2BombSaraiBomb::update` rejects any delta that is not the source delta — no substituted timesteps.

## Lifecycle state machine

Phases map to the source Bomb FSM (`bombState.cpp`) and the carrier call sites (`BombSarai.cpp`, `BombSaraiState.cpp`):

| Phase | Source equivalent | Behavior |
| --- | --- | --- |
| `Captured` | capture at `kamu_jnt1` (`bomb.cpp:23-44`) | Constrained and invulnerable; the host moves the bomb with the joint; `update` is a no-op. |
| `InFlight` | `BOMB_Wait`, motion stopped, escaped capture | Ballistic flight; host trace per tick; escaped-capture despawn counter runs. |
| `ArmedLoop` | `BOMB_Wait`, hit-loop playing | Entered only on traced floor contact (`isAnimStart` = escaped + floor triangle, `bomb.cpp:468-476`). Fuse health drains 1.0/source-second; transits after the hit-loop animation length. |
| `Burning` | `BOMB_Bomb` | Health keeps draining; at zero, a fixed 10-tick delay precedes detonation. Despawn counter is reset and stopped (source `StateBomb` init). |
| `Despawned` | `kill(nullptr)` | Silent removal without blast (200-tick escaped-capture timeout), or post-detonation. Slot is reusable. |

Contract decisions:

- **Throw velocities are fixed by source.** Release lob `(50·sin face, 100, 50·cos face)` (`BombSaraiState.cpp:528-531`), Fall skyward throw `(100·sin, 300, 100·cos)` (`:592-595`), death drop `(0,0,0)` (`BombSarai.cpp:57-61`). No homing, no target lead. `throwBomb` is only valid from `Captured`, mirroring the source's unconditional `mHeldBomb` clear that is a no-op on null.
- **Bomb drop on death is unconditional.** The host translates carrier `onKill` into `throwBomb(Death, …)`; the dropped bomb then follows the normal floor-armed fuse. The Fall throw is how a bittered or Purple-dragged carrier ejects its payload mid-crash.
- **Fuse arms on floor contact only.** Wall contact keeps the trace-mutated velocity and stays in flight; the drop-group bounce/collision arming paths (`bomb.cpp:383-408`) do not apply to dirigibug lobs. Landing zeroes velocity and starts the arm loop.
- **Fuse timing is parameter-explicit.** Total fuse = `armLoopTicks` (hit-loop bck length, converter input per #128) + fuse-health drain (bomb general `mHealth` at 1.0/s, host parameter input) + fixed 10-tick detonation delay. The policy refuses invalid configs instead of inventing values; only the source-fixed 200-tick escape timeout and 10-tick delay are hardcoded.
- **Blast is one recorded event, host-routed.** The policy emits exactly one `P2BombSaraiBlastEvent` at detonation: center, `radius` (general attack radius), `halfHeight` (`fp02`, default ±50), `tekiDamage` (`fp01`, default 250), `naviPikiDamage` (general attack damage), knockback weights 100 (Navi) / 200 (Pikmin). Target enumeration, height gating and receiver stimulation are host-owned; the policy never touches creatures.
- **Friendly fire is unconditional per source.** Teki in the volume take 250 via `InteractBomb` with no faction check — including a grounded carrier. Navi/Pikmin damage carries directional knockback computed by the host from the recorded weights (`bombState.cpp:159-190`).

## Stale-mCarrier decision (explicit deviation from source mechanics)

Source attributes Navi/Pikmin blast damage to `Bomb::Obj::mCarrier` when non-null (`bombState.cpp:167-189`). `BombSarai::Obj::throwBomb` never clears that pointer (`BombSarai.cpp:285-294`), so a thrown bomb keeps pointing at a carrier that may die or be reused while the lob is in flight — a use-after-free hazard in any host that reuses creature storage.

This policy never carries object pointers. The host issues a `uint64_t` carrier token at capture time; at blast time the policy resolves liveness through the host `P2BombSaraiCarrierFn` callback:

- **Carrier confirmed live** → `carrierValid = true`, receivers attribute to that token's creature (source-faithful).
- **Carrier unconfirmed (dead, despawned, reused, or no callback)** → `carrierValid = false`; receivers must attribute to the bomb itself, matching the source's `mCarrier == nullptr` fallback (`bombState.cpp:170-172`). This deliberately prefers the source's safe branch over reproducing a stale dereference.

## Pool sizing and exhaustion

`P2BombSaraiBombPool` models supply as a fixed-capacity pool. Default capacity mirrors the BombSarai roster preallocation `mChildNum = 2` (`enemyInfo.cpp:46`); the host configures the real shared Bomb manager limit, which is shared with other carriers (BombOtakara) and remains an open runtime question from the audit. One live bomb per carrier token mirrors the source `!mHeldBomb` guard (`BombSarai.cpp:265`). Exhaustion, duplicate-carrier supply, and invalid input return `nullptr` with no state change, matching the source's silent tolerance of a failed manager or birth; the carrier FSM then runs its Bomb* states harmlessly with a null payload. Detonated/despawned slots are reusable by later supply calls.

## Fixture evidence

Standalone MinGW build, no engine objects (same convention as the Groink lane):

```powershell
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bombsarai_bomb_test.cpp pc_port/pc_p2_bombsarai_bomb.cpp -o <private-test.exe>
g++ -std=gnu++17 -Wall -Wextra -Werror tools/p2_bombsarai_clock_test.cpp -o <private-clock-test.exe>
```

Compiled warning-clean and executed with local MinGW GCC 16.2. The bomb fixture covers: all three source throw velocities (including facing-angle decomposition), capture no-op semantics, throw valid only from capture, fixed-step delta rejection (60 Hz and NaN), untraced ballistic integration with per-tick gravity, wall contact not arming, floor contact arming with velocity zeroing, full fuse through one recorded blast with all event fields, exact arm-loop length and exact 10-tick detonation delay, blast firing exactly once, stale-carrier fallback (`carrierValid=false`, token preserved), death drop arming normally, 200-tick escaped-capture despawn without blast, pool capacity/duplicate-carrier/exhaustion returning `nullptr` without state change, slot reuse after detonation, and invalid-config capture refusal. The clock fixture mirrors the Groink clock cases: 30/60/120 Hz produce exactly 30 source ticks per second, stall capping, gap/pause/invalid-input debt resets.

This is a standalone policy test, not a native arena or gameplay test. Host trace, target enumeration, receiver stimulation, effects, sound, the carrier FSM itself, and save/resume semantics remain unimplemented and are tracked in the issue.

## Open items for later slices

- Host terrain-trace adapter implementation (per #169 pattern): `P2BombSaraiTraceFn` against the P1 static map, with the groundY correction contract.
- `armLoopTicks`, `fuseHealth`, `blastRadius`, `naviPikiDamage`, `gravityPerTick` numeric values from converted Bomb assets/parms (#128 dependency).
- Real shared Bomb manager pool limit under concurrent carriers (audit open question).
- Blast receiver routing (Teki/Navi/Pikmin stimulation) and its separate acceptance evidence; multi-projectile lifetimes under several dirigibugs plus bomb-on-bomb induction (`ip02`) are not modeled in this slice.
- Save/resume and cave/day transition semantics for carried, in-flight and armed bombs (audit persistence caveat).
