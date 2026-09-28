# DangoMushi Turn vulnerability window applied + real Rock/Egg births (#174 / #376)

Lane 25 slices following [the hazard runtime slice](PIKMIN2_DANGOMUSHI_HAZARD_RUNTIME.md):
(1) the previously observed-only Turn stickable window is now a real
damage-admission gate, and (2) the Rock/Egg hazard decisions are realized as real
children. Source reference `src/plugProjectNishimuraU/DangoMushiState.cpp:530`
(US GPVE01 rev 0), where the Turn loop-start key clears `EB_Invulnerable` and the
`bod0`/`bod1` parts become stickable until key 3, and
`DangoMushi.cpp:649-776` for the rain.

Implementation owner: Codex via shared account `4laric`. Executing session:
opencode (deepseek), 2026-09-14. Review-fix revision (fix1) applied after review.

- Native branch `deepseek/p2-l25-native`, base
  `codex/p2-main-review-native` @ `b805d9c626e4f4558c95aef7cac311a5d9a2068f`.
- Root branch `deepseek/p2-l25`, base
  `codex/p2-main-review` @ `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`.
- Private build `output/dsw/native-l25-build`,
  `-DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON`; `ninja -n` -> `no work
  to do.`
- Executable SHA-256 (fix1)
  `7bf0c81260fa501f93f37e55af0c7e7f22eaf7bfe7bfc518bba9f0c852b77691` at native
  head `f11cec6c6b832403bfdddac5e06fcb56f23edb7e`.

### Review fixes (fix1)

- The lane-20 static-map trace/RNG/Wait-detection were forked in the original
  slice; they are now extracted to a shared `pc_p2_rock_host.{h,cpp}`
  (`p2rockhost::TraceProxy`/`RockMapBinding`/`ScriptRng`/`detectRock`) consumed by
  both `pc_p2_projectiles.cpp` and `pc_p2_dangomushi.cpp`. Exposed in its own
  commit `lane25: expose rock host binding for consumers (lane 20 primitive)`.
- `tekiinteraction.cpp` hook now lives in its own commit
  `lane25: hook InteractAttack/InteractBomb to pc_p2_dangomushi_invulnerable`.
- `hzo.rockLifetime` (30 s) is now applied: a falling rock that never traces a
  floor is force-killed (`P2RockHazard::forceDeath`, additive primitive
  extension) after its lifetime and its pool slot is released
  (`P2_DANGOMUSHI_ROCK_DESTROY reason=lifetime`).
- A second Egg request no longer `reset()`s a live Egg (it would discard its
  pending break); `spawnRainEgg` skips while one is active.
- `applyRainRockContact` records a contact token only after the source 1 s
  `atari` grace check passes, so a contact ignored during the grace is not
  skipped forever for that rock.
- Stale "future lane-20 birth host" / "future host seam" comments corrected.


## What changed

This is the source host that the [fan-out ledger](PIKMIN2_LANE_COMPLETION.md)
lists as lane 25's missing gate. The maintained line already carried
`pc_p2_dangomushi.cpp` (source FSM) and `pc_p2_dangomushi_hazard.{h,cpp}`
(Turn window + Rock/Egg decisions), but the window was only logged.

- `pc_port/pc_p2_dangomushi_hazard.h`: add the shared pure predicate
  `P2DangoMushiHazardPolicy::attackRejected(bool stickable)` (`!stickable`), so
  the host gate and the engine-free fixture use one definition.
- `pc_port/pc_p2_dangomushi.h/.cpp`: track `stickable` on each registered actor
  (`Dango::stickable`, set from the policy output on every Turn tick and cleared
  on every state transition). Add
  `bool pc_p2_dangomushi_invulnerable(const BTeki*)`: returns false for an
  unregistered actor, otherwise returns `attackRejected(stickable)`. Emits
  `P2_DANGOMUSHI_DAMAGE_REJECTED` on the first rejected attack per window and
  `P2_DANGOMUSHI_DAMAGE_ACCEPTED` when in-window damage is admitted.
- `src/plugPikiNakata/tekiinteraction.cpp`: `InteractAttack::actTeki` and
  `InteractBomb::actTeki` consult the gate and consume the interaction, mirroring
  the existing `pc_p2_hana_rejects_attack` / `pc_p2_kogane_attacked` idiom. Both
  hooks are no-ops for unregistered actors, so P1 controls are untouched.
- `tools/p2_dangomushi_hazard_test.cpp`: assert the shared predicate inside the
  existing window fixture.

## Real Rock/Egg births

`pc_port/pc_p2_dangomushi.cpp` hosts the lane-20 **policies** (`P2RockHazard`,
`P2Egg`; not forked) and realizes the hazard decisions as real children. The
static-map trace, scripted RNG and Wait detection are the shared
`p2rockhost::*` (pc_p2_rock_host, extracted from lane 20); the only lane-20
primitive edit is the additive `P2RockHazard::forceDeath()` used to cull a rock
that never reaches a floor after its lifetime.

- Rock rain (`hzo.rocksToSpawn`): one `P2RockHazard` per source ring slot is born
  at `P2DangoMushiHazardPolicy::rockOffset(...)` around the active captain,
  `+300` Y, and falls under the source velocity through a real P1 static-map
  trace. Its contacts apply real `InteractPress` (grounded Piki/Navi) and real
  `InteractAttack` (Teki), attributed to the Crawbster actor. Markers:
  `P2_DANGOMUSHI_ROCK_BIRTH`, `_ROCK_PHASE`, `_ROCK_STRIKE`, `_ROCK_DESTROY`.
- Egg (`hzo.eggRequested`): one `P2Egg` is born at the Crawbster home; a
  Navi/Piki touch breaks it and its drop table births real P1 items through
  `pelletMgr->newNumberPellet` / `itemMgr->birth(OBJTYPE_Water)`. Markers:
  `P2_DANGOMUSHI_EGG_BIRTH`, `_EGG_CONTACT`, `_EGG_ITEM`.

Rock fall/scale values are the **documented fixture host parms** already used by
`tools/p2_rock_hazard_test.cpp` (`mSearchDistance`/`Height`/`Angle` stand-ins);
they are host inputs, never source constants. Egg drop chances are the disc proper
parms fp01-fp05 (0.5/0.35/0.05/0.05/0.05) with general fp00=50. The host pool is
16 slots with reuse of dead rocks (the source reserves 30 Rocks / 10 Eggs per
Crawbster); Mitites fall back to nectar because P1 has no Mitite manager.

Lane 20 remains the owner of the Rock/Egg policies and the shared
`pc_p2_projectiles` host; the shared `pc_p2_rock_host` module and the additive
`forceDeath()` extension are labelled `lane25:` commits for integration to review.

## Applied behavior

| Observation | Result |
|---|---|
| Attack/bomb on an unregistered actor | unchanged (gate returns false) |
| Attack/bomb on a registered Crawbster outside the Turn window | rejected; actor health unchanged |
| Attack/bomb on a registered Crawbster inside the Turn `LOOP_START..key-3` window | admitted through the normal damage path |
| Hazard rock decision | real falling `P2RockHazard` children with real press/attack strikes |
| Hazard egg decision | real `P2Egg` whose break births real P1 pellets/nectar |

The window frames are unchanged: opened at the turn loop-start key (32), closed
at key 3 (108).

## Status

- Engine-free policy fixture: `PASS DANGOMUSHI_HAZARD` — stdout saved to
  `output/dsw/l25-out/p2_dangomushi_hazard_test.stdout.txt`.
- Full production target build: PASS (see pins above), no-work dry run clean.
- Runtime acceptance (fix1, real GL, 960x540 centred, live 20-red squad): **PASS
  for the new gates** on run
  `output/dsw/l25-out/runs/9093da5e6b7d45b6b86857f2ca2d4152` (exe
  `7bf0c812…`):
  - `P2_DANGOMUSHI_DAMAGE_REJECTED` (outside window) and
    `P2_DANGOMUSHI_DAMAGE_ACCEPTED ×6` (in-window) — window applied.
  - `P2_DANGOMUSHI_ROCK_BIRTH requested=10 real=10` with a real
    `P2_DANGOMUSHI_ROCK_STRIKE kind=Press damage=10.0` and `_ROCK_DESTROY
    reason=floor` — real Rock births/strikes.
  - `P2_DANGOMUSHI_EGG_BIRTH real=1`, `_EGG_CONTACT health=0`,
    `_EGG_ITEM index=0 kind=2 real=1 item=nectar` — a real Egg birth that broke
    into real nectar.
  The whole-validator `passed` flag is `False` on this run only because the
  pre-existing `wait`/`flick` state-coverage checks are timing/RNG dependent (the
  Crawbster stayed engaged and never idled); every new-gate check passed. The
  Egg decision is probabilistic (`formationPikis/allPikis`, source
  `DangoMushi.cpp:732-748`), so a given run may roll `egg=0`; this run rolled
  `egg=1`.
  Note: `dangomushi-validation.json` reports `exit_code=1 timed_out=true` because
  the fixture is timer-terminated at the requested observation window (pre-existing
  validator counter); it is not an engine failure.

## Remaining

1. True source `InteractPress` roll crush, the `wallCallback` crash trigger and
   the `dangomushi.brk` material loop remain.
2. Death/corpse/cleanup/re-entry (#397, lane 07 lifetime host).
