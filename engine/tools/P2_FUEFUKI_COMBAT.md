# Fuefuki natural-combat receiver and engine-fact feed (#245)

Successor of `P2_FUEFUKI_BINDING.md` / `P2_FUEFUKI_VEHICLE_RUNTIME_EVIDENCE.md`.
Those slices proved the whistle-theft claim/reclaim/follow/death-release chain but
killed the vehicle by zeroing `mHealth` from the fixture. This slice closes the
"natural combat" half of gate 3 (attacks and receivers) and the natural-death
half of gate 4 (death and corpse): the beetle now reacts to a real press
stimulus (Struggle) and the FSM's stuck-attacker cadence and health routing run
from live engine facts.

Source revision: projectPiki/pikmin2 632af93787b9c95b63f0c13be32b161375ce3a96
(US GPVE01 rev 0), read-only under native/pikmin2-research. The state machine
this slices feeds is unchanged and already tested
(`tools/p2_fuefuki_fsm_test.cpp` covers Struggle entry, stuck-empty exit to Jump,
bittered-press rejection and fatal Struggle exit to Dead).

## What changed

- `src/plugPikiNakata/tekiinteraction.cpp` — additive `InteractPress::actTeki`
  hook. A press stimulus on the bound Fuefuki vehicle is routed to
  `pc_p2_hardlanes_fuefuki_pressed` (no-op for any other Teki, so ordinary P1
  play is untouched). Source mapping: `Fuefuki.cpp` `pressCallBack`/
  `hipdropCallBack` (:163-185) both enter Struggle when `mCanStruggle` and not
  bittered; P1 exposes a single `InteractPress` stimulus, and no `hipdrop`
  interaction exists, so both source callbacks collapse onto the one press
  receiver (hipdrop is source-backed N/A for the P1 host).
- `pc_port/pc_p2_hardlanes.h` / `.cpp` — `pc_p2_hardlanes_fuefuki_pressed`
  latches the stimulus (edge, consumed on the next 30 Hz tick);
  `pc_p2_hardlanes_fuefuki_press_count` is fixture introspection. The tick loop
  now feeds the FSM two real engine facts that were previously silent:
  - `pressed`: the latched press/hipdrop stimulus. The FSM admits it only when
    `canStruggle && !bittered` and the beetle is not already Dead/Struggling,
    matching the source's immediate `mCanStruggle` check.
  - `stuckPikmin`: the count of living Piki stuck to the vehicle, walked off the
    engine sticker list (`Creature::mStickListHead -> mNextSticker`). This drives
    the source Struggle exit "no stuck attackers after the hard-coded 3.0 s ->
    Jump" and the source whistle-cadence branch "stuck attackers present -> fp12
    no-squad interval".
  - `bittered` stays false: P1 has no EB_Bittered bridge, so the source
    bittered-press rejection remains exercised by the mock-host fixtures only.
    This is a documented host-admission limitation, not a weakening (a bittered
    beetle in P2 would reject the press; the P1 host simply cannot bitter it).

## Host contract

- `pc_p2_hardlanes_fuefuki_pressed(Teki*, Creature*)` is the lane's single
  combat-ingress point. It returns true (consumed) only when the pressed Teki is
  the currently bound Fuefuki vehicle; admission and the Struggle transit stay
  in `P2FuefukiFsm`. It writes no health, no captain ownership and no collision.
- The engine's own `InteractAttack -> teki->interact(Attack)` damage path still
  reduces the vehicle's real `mHealth`; `pc_p2_hardlanes_update` already reads
  `sFuefukiVehicle->mHealth` into the FSM, so natural attack damage continues to
  reach Death through the FSM's per-state `health <= 0` checks unchanged.

## Fixture evidence

Policy fixtures unchanged and re-run clean (no header/logic regression to the
FSM): `p2_fuefuki_fsm_test`, `p2_fuefuki_binding_test`,
`p2_fuefuki_interference_policy_test`, `p2_fuefuki_suspend_fallback_test`,
`p2_fuefuki_follow_test`, `p2_fuefuki_follow_binding_test`.

New evidence:
- Warning-clean `-fsyntax-only` compile of the touched translation units
  (`src/plugPikiNakata/tekiinteraction.cpp`, `pc_port/pc_p2_hardlanes.cpp`,
  `tools/p2_fuefuki_combat_runtime.cpp`) against the frozen host include tree,
  `PIKI_PC_PORT=1`.
- `tools/p2_fuefuki_combat_runtime.cpp` is compiled as the compile-only CMake
  object target `p2_fuefuki_combat_runtime_compile` (not linked, not run): the natural-combat real-GL acceptance is **UNTESTED**. There
  is no `P2_FUEFUKI_COMBAT_RUNTIME_EVIDENCE.md`; no real `InteractPress` has been
  observed on the bound vehicle, nothing proved the Struggle transit live, and no
  engine attack drove `mHealth <= 0` to Dead. `fuefukiStuckPikmin` and the press
  latch have **zero runtime coverage**. The FSM Struggle routing is source-faithful
  and tested at the policy level (`p2_fuefuki_fsm_test`), which is policy evidence
  only, not a natural gameplay PASS.

## Remaining gaps

- `native_identity` (enemy 41) is unchanged: the vehicle is still Napkid 11
  (placement vehicle), pending native actor registration (#186) and the source
  Beetle motion bank (#128).
- `bittered` has no P1 bridge; the bittered-press rejection path is policy-level
  only.
- Corpse/reward transport remains the engine's normal `TEKICORPSE_LeaveCorpse`
  path for the Napkid, not a sourced Fuefuki carcass reward (provider 06).
