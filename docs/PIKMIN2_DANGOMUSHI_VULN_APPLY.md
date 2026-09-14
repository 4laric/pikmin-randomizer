# DangoMushi Turn vulnerability window applied + real Rock/Egg births (#174 / #376)

Lane 25 slices following [the hazard runtime slice](PIKMIN2_DANGOMUSHI_HAZARD_RUNTIME.md):
(1) the previously observed-only Turn stickable window is now a real
damage-admission gate, and (2) the Rock/Egg hazard decisions are realized as real
children. Source reference `src/plugProjectNishimuraU/DangoMushiState.cpp:530`
(US GPVE01 rev 0), where the Turn loop-start key clears `EB_Invulnerable` and the
`bod0`/`bod1` parts become stickable until key 3, and
`DangoMushi.cpp:649-776` for the rain.

Implementation owner: Codex via shared account `4laric`. Executing session:
opencode (deepseek-v4.1-flash), 2026-09-14.

- Native branch `opencode/p2-crawbster-vuln-native`, base
  `codex/p2-main-review-native` @ `b805d9c626e4f4558c95aef7cac311a5d9a2068f`.
- Root branch `opencode/p2-crawbster-vuln-root`, base
  `origin/codex/p2-main-review` @ `4fccf41f775fc70c907ebce4116637e9abed02ab`.
- Private build `output/native-lane25-vuln-build`, `[603/603]` link, exit 0,
  `-DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON`.
- Executable SHA-256
  `496EBEE70FF4A965B6E5B2F73ED80A25740C809C7150A3BF8DA3BFE24CDEC8F5`;
  `ninja -n` -> `no work to do.`

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

`pc_port/pc_p2_dangomushi.cpp` now hosts the lane-20 **policies** unchanged
(`P2RockHazard`, `P2Egg`; not forked) and realizes the hazard decisions as real
children:

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

This does not fork the lane-20 primitives and does not edit lane-20's module. It
still needs a runtime run to observe the births/strikes; lane 20 remains the
owner of the Rock/Egg policies and the shared `pc_p2_projectiles` host.

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

- Engine-free policy fixture: `PASS DANGOMUSHI_HAZARD` via `ctest -R
  p2_dangomushi_hazard_test` and a direct `g++` build.
- Full production target build: PASS (see pins above), no-work dry run clean.
- Runtime acceptance: PENDING a reserved real-GL run on the private executable.
  The fixture validator now parses the window, birth and strike markers and
  requires `DAMAGE_REJECTED` and a real `ROCK_BIRTH`; `DAMAGE_ACCEPTED`,
  `EGG_BIRTH`, `EGG_ITEM` and `ROCK_STRIKE` are informational because a short
  fixture may not land an in-window attack, break the probabilistic Egg or drop a
  Rock onto a Pikmin.

## Remaining

1. Runtime observation and acceptance of the applied window and the real births
   on a reserved real-GL run (the code paths compile and are validator-covered).
2. True source `InteractPress` roll crush, the `wallCallback` crash trigger and
   the `dangomushi.brk` material loop remain.
3. Death/corpse/cleanup (#397).
