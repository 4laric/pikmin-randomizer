# Integration sweep #455

Owner: Codex through shared account 4laric. Draft #432 baseline 6b118be / native 3213dd59. Native result fb7fee4673f6929124e2eadf7937e8aa09f586e5.

## Integrated

- Lane 20 root 470c76a, native be8037af (applied e80226a7): opt-in private projectile receiver registry, strike/death diagnostic markers and unit tests. **This is proxy health, not engine Creature health**. Actual damage/emitter/cannon and Egg birth integration remains open.
- Lane 26 root 65fe266: Long Legs FSM suppresses shell requests when host reports ten shells in flight; native fb7fee46. Host must supply occupancy; no ordinary Man-at-Legs actor completion claim.
- Extended reproducible native gate to include projectile receiver and Long Legs FSM (23 probes).
- Lane 15 58631c2: Qurione worker runtime evidence and documented host-AI fix. Resolved doc context using the newer worker report; its native fix is not applied by this documentation import.
- Lane 27 ede4ffc: pinned room-host/BombSarai 3-scenario worker evidence. These are worker runs, not a fresh run on this combined build.
- Lanes 10–12 4fc648c: consolidated patch bundle and review report preserved. **Native series remains unapplied**, aside from previously integrated pure policies.

## Remaining queue

- Shared series 4f7485d5 changes Piki identity, fire/bubble routing, electric/gas adapters, captain/Bulbmin bridges and cave schema 3. Reconcile focused commits against current cave semantics, verify old checkpoint behavior, and run actual provider/consumer acceptance. Worker explicitly reports no live electric/gas emitter or Bulbmin spawn and slot-0-only captain support.
- Waterwraith 3e01ccf visual runtime bundle awaits native-consumer reconciliation; root stager is already present. Broad species/Crawbster host dependencies remain queued.
- Lane 09 fd30e76 prepared bank/native/fixture evidence still names missing #399 room assets; no new specular visual acceptance inferred.
- No new randomizer admissions or natural-combat completion from this sweep. Follow PIKMIN2_NEXT_WAVE.md for next-wave gates and current live-Pikmin/centred-960x540 fixture requirement.

## Validation

Native standalone gate: 23/23 PASS. Receiver and Long Legs probes also pass with -Wall -Wextra -Werror -UNDEBUG. Initial receiver standalone invocation omitted Stone/Rock link modules; corrected command and committed gate include both dependencies.

Production build PASS at fb7fee4673f6929124e2eadf7937e8aa09f586e5; dry run: `ninja: no work to do.` Executable SHA-256 `E8383C24E9EC84A9B7A0018EDBBE416D4110445D15F25B7238625D9D35289C02`. All 1691 exported source files match exactly. Python suite: **2021 passed, 25 skipped, 1088 subtests passed** in 137.57s. Private build output/p2-upstream433-build, Ninja Release, MinGW, JAudio ON, test hooks OFF. No new real-GL acceptance in this sweep.
