# MUKI rows #186 decision packet (issue #777)

Lane `muki-186-decision-packet`, generation 2. Bounded diagnosis for the
blocked producer `muki-stage-table-rows-native` (#748): this packet gives
the #186 shared-review owner the exact serialized wiring decision in
machine-readable form. Diagnosis only: concrete pin/ownership deliverables,
never an engine unblock. No pc_bbft.cpp/CMakeLists.txt edits here, no
engine changes, no ADMIT, no gameplay claim.

## What this delivers

- `experimental/pikmin2_muki_186_decision_packet.py` — builds the packet
  from the pinned #748 native commits (`cae86d4e` + `3c50ca44`, read-only)
  against the destination pins (`#710 db245877` boot-table shape, `#736`
  38305eea CMakeLists policy, read-only): exact unified diff appending the
  two MUKI rows to `kP2ChallengeStages` in `P2ChallengeStageRow` field
  order plus the CMakeLists membership line, file hashes, consumer refs
  #735/#744, and review metadata (`requested-not-granted`).
- `tests/test_pikmin2_muki_186_decision_packet.py` — 14 focused tests:
  packet shape, diff content (both rows, exact fields, membership line),
  fail-closed refusal (malformed pins, wrong count, drift, tampered diff,
  wrong schema/consumers) and JSON serialisability.
- This file.

## The decision being requested

Files (serialized producer scope, NOT owned here): `native/pc_port/pc_bbft.cpp`
(append the two diff rows) and `native/CMakeLists.txt` (add
`pc_port/pc_p2_challenge_muki_stages.cpp` to the owning target). The #186
owner decides; on approval the integrator lands and consumers #735/#744
re-verify against their original failing checks. Until then the rows live
only in the producer module and the boot selects no MUKI stage.

## Validation evidence (this turn, no runtime)

- 14/14 focused tests pass; packet self-validation round-trips.
- `python -m experimental.pikmin2_muki_186_decision_packet packet` emits
  the review artifact; `diff` prints the unified diff alone.

## One exact reproduction command

```
cd <muki-186-decision-root worktree>
py -3.12 -m pytest tests/test_pikmin2_muki_186_decision_packet.py -q   # 14 passed
py -3.12 -m experimental.pikmin2_muki_186_decision_packet packet
```
