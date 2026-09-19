# MUKI gen-5 #186 decision-request refresh 2 (#824)

Lane `muki-186-decision-refresh2`, issue #824 (OPEN, assigned 4laric).
Successor to the cycle-75 attempt, which was rejected only for reusing
issue #748 (held by the blocked producer lane). Consumer:
muki-stage-table-rows-native gen 5 (blocked, #748). Diagnosis only.

## Verified facts (read-only)

- Producer pins: root `baf82085`, native base `93603dc2`..head `3c50ca44`
  (delta is exactly the 3 row files, +113/-0, pure additive).
- Destination pins (gen379 lines): wave-root `3a33cbde`, native-wave
  `73891ad5`. All 3 row files ABSENT at the tip: unlanded confirmed.
- The producer delta touches NO shared files; the #186 decision concerns
  the integration-time serialized pc_bbft.cpp/CMakeLists.txt wiring.

## Deliverable

`experimental/pikmin2_muki_186_decision_refresh2.py` re-verifies the above
and emits `decision-packet.json` (pins, unlanded proof, exact decision
requested). Filed as the #186 decision request; never the decision itself.
Unit tests 3/3. No native/shared edits, builds, launches, ADMIT.
Downstream #748.
