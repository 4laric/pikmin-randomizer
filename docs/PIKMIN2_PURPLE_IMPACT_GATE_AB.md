# Pikmin 2 Purple impact Gate A/B implementation evidence

Status: opt-in native implementation with standalone runtime fixture acceptance; controller gameplay acceptance pending, 2026-09-13. Tracking: #393, parent #113. Implementation owner: Codex through shared account `4laric`.

## Adapter decisions

- A captain throw is armed in `Navi::throwPiki`, after the real Piki velocity is committed. `PikiFlyingState::init` is not an arming hook because drowning rescue also enters that state. The preview locus is not armed.
- Descending enemy collision and ground/platform bounce call one emitter. A source lifetime and monotonic attack token permit one emission; cleanup forgets transient source state. Collision followed by bounce cannot emit twice.
- The emitter scans the native Teki registry, then filters to explicitly registered P2 Red Dwarf Bulborb actors. This is the documented registered-global-scan approximation to P2 cell enumeration.
- Narrow phase is inclusive XZ distance `60 + BTeki::mCollisionRadius`. Native `BTeki::init` initializes that field from `TPF_CollisionRadius`; visual and shadow radii are not used. Y is deliberately ignored.
- The receiver accepts a living, grounded, nonflying, noninvincible registered Red dwarf in ordinary Chappy states 4–12 or 15, plus repeated impact state 16. Death/pressed/crushed states 0–3 and 13–14 reject. P2 hard-constraint, bitter, no-interrupt, bitter-immunity and DropEarthquake semantics have no audited P1 adapter and remain unsupported rather than inferred.
- `TaiStrategy::transit` runs the current state's finish lifecycle and schedules the new state's start lifecycle. Re-entry into impact state preserves the original return state.

## Receiver ordering

The appended Chappy impact state runs `TaiStopMoveAction`, normal `TaiSimultaneousDamageAction`, `TaiDeadAction`, native Pressed and smashed event actions, then the Purple lifecycle action. By code ordering, queued damage is applied through the native damage function and a lethal result can transition into the existing Chappy death sequence in the same strategy tick. Pressed/smashed transitions finish the impact state and clear its transient receiver state. The standalone fixture observed ordinary nonlethal damage and lethal damage through `InteractAttack`, followed by the normal corpse object. Pressed/smashed interruption still requires runtime observation.

Earthquake sets horizontal velocity to zero and vertical velocity to `200 + 100*roll`. Fit is considered only after more than three receiver updates and a grounded frame. Its roll is consumed only at that decision. A value below 0.3 enters Fit; 0.3 does not. Red Fit exits strictly after ten seconds. A repeated event retains positive Fit elapsed time. The receiver starts the native Wait1 motion so an interrupted attack animation does not keep displaying a bite during stun.

## Opt-in and limits

Existing `P2_PURPLE_1` profiles keep impact disabled. A profile must contain exactly one `impact red_earthquake_v1` line to enable this slice. The normal Purple identity, stats, carry and conversion behavior remains independent.

This is partial P2 behavior and is not yet a complete first-playable or controller signoff claim. Direct collision still follows the native P1 flying collision path after emitting the wave: audited Hipdrop/Press payload ordering, collision-part fallback fidelity, 0.25-second HipDrop entry, homing/descent/spin, 0.3-second landing recovery, impact effects/sound/camera/rumble, DropEarthquake, Snow/Orange and other families remain open. A registered scan can differ from the P2 cell broadphase at cell boundaries.

## Compiled checks

`tools/p2_purple_impact_policy_test.cpp` exercises the portable source and receiver boundaries. `tools/p2_purple_tai_transition_test.cpp` compiles and executes the production `src/plugPikiNakata/tai.cpp` against minimal structural engine stubs. The latter confirms the actual `TaiStrategy::transit` finish/readiness behavior, repeated same-state return preservation, invalid-state rejection and `TaiState::act` action ordering. Its damage/death actions are deliberately minimal harness actions, so it supports the ordering argument but does not prove native `TaiSimultaneousDamageAction`, callbacks, corpse creation or gameplay.

The final production target built successfully from the integrated uncommitted source state. The private fixture builder then compiled and linked `tools/preview_p2_room.cpp`; provenance and the executable are under `output/p2-purple-impact393/fixture-03/` (SHA-256 `5cc9e3f37da8d091a0e109014510336bb0dda55befd9f640edff00b8e9377788`). A diagnostic private derivative parked the ordinary squad and source after the wave, because repeated fixture throws otherwise let normal Pikmin attacks kill the only receiver. It was built with `built` provenance under `fixture-private-02/` (executable SHA-256 `fa09a0de23c3b9a57bc1f17a438da79bb384d1b8a831333ee518e651caa69215`). After the pass, the proven private include was copied byte-for-byte to `tools/preview_p2_purple_impact.inc`; both files have SHA-256 `581d5f0c74852146cc44c4ad98fe1284ea9602172f038ad5d2a899159fbee0c5`, so the successful executable exercises the exact shared fixture body.

The isolated run `output/p2-purple-impact393/run-private-02/` used the real registered Red Dwarf actor/profile and Purple pose assets with explicit `impact red_earthquake_v1`. Its log records an actual `Navi::throwPiki`, accepted ground-bounce quake, state 16 grounded for 90 continuous frames, nonlethal `InteractAttack` reducing health 200 to 195, lethal `InteractAttack`, normal death, and a corpse pellet whose view points to the target. The run exited zero with `PASS p2 Purple impact`. The source Pikmin was fixture-converted and actors were parked by the diagnostic fixture, so this proves the native throw/emitter/receiver/damage/death/corpse chain in a real actor arena but does not prove controller conversion, ordinary play positioning, visual fidelity, or campaign persistence.
