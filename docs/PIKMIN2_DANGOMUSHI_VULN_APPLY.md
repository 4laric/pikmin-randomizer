# DangoMushi Turn vulnerability window applied (#174 / #376)

Lane 25 slice following [the hazard runtime slice](PIKMIN2_DANGOMUSHI_HAZARD_RUNTIME.md):
the previously observed-only Turn stickable window is now a real damage-admission
gate. Source reference `src/plugProjectNishimuraU/DangoMushiState.cpp:530`
(US GPVE01 rev 0), where the Turn loop-start key clears `EB_Invulnerable` and the
`bod0`/`bod1` parts become stickable until key 3.

Implementation owner: Codex via shared account `4laric`. Executing session:
opencode (deepseek-v4.1-flash), 2026-09-14.

- Native branch `opencode/p2-crawbster-vuln-native`, base
  `codex/p2-main-review-native` @ `b805d9c626e4f4558c95aef7cac311a5d9a2068f`.
- Root branch `opencode/p2-crawbster-vuln-root`, base
  `origin/codex/p2-main-review` @ `4fccf41f775fc70c907ebce4116637e9abed02ab`.
- Private build `output/native-lane25-vuln-build`, `[603/603]` link, exit 0,
  `-DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON`.
- Executable SHA-256
  `8B81E4906808A98E86346F11D41D6843C5F403ABA114D57DE353F6D2D41BB3A7`;
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

## Applied behavior

| Observation | Result |
|---|---|
| Attack/bomb on an unregistered actor | unchanged (gate returns false) |
| Attack/bomb on a registered Crawbster outside the Turn window | rejected; actor health unchanged |
| Attack/bomb on a registered Crawbster inside the Turn `LOOP_START..key-3` window | admitted through the normal damage path |

The window frames are unchanged: opened at the turn loop-start key (32), closed
at key 3 (108).

## Status

- Engine-free policy fixture: `PASS DANGOMUSHI_HAZARD` via `ctest -R
  p2_dangomushi_hazard_test` and a direct `g++` build.
- Full production target build: PASS (see pins above), no-work dry run clean.
- Runtime acceptance: PENDING a reserved real-GL run on the private executable.
  The fixture validator now parses the two markers and requires
  `DAMAGE_REJECTED`; `DAMAGE_ACCEPTED` is informational because a short fixture
  may not land an in-window attack. Expected native run: `P2_DANGOMUSHI_DAMAGE_REJECTED`
  while the Crawbster is rolling/invulnerable, and `P2_DANGOMUSHI_DAMAGE_ACCEPTED`
  during the flip.

## Remaining (unchanged)

1. **Real Rock/Egg births.** The hazard output still only decides (`rocks`,
   `egg`); no P2 Rock (19) / Egg (37) Teki child is born. There is no generic
   P2-enemy-id -> `TEKI_*` birth helper in the tree, and no P2 family births a
   Teki child: the lane-20 `P2RockHazard` / `P2Egg` modules are engine-free
   policies, and `pc_p2_projectiles.cpp` hosts exactly one Rock and one Egg from
   `p2-projectiles.txt`. Connecting the Crawbster's rain to real children needs
   an agreed additive request seam with the lane-20 host (or a lane-20 pool).
2. True source `InteractPress` roll crush, the `wallCallback` crash trigger and
   the `dangomushi.brk` material loop remain.
3. Death/corpse/cleanup (#397).
