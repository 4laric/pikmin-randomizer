# Jigumo63 EAT-receiver review (#689, lane-16 via #167)

Lane `shard-enemies-4-jigumo63-eat-receiver`, generation 2. Owner: Codex
through shared account `4laric`. Consumer: stopped
`shard-enemies-4-jigumo63-observer` (#173-family, gen-2): its pass1 run threw
117 Pikmin (HP 500->380), timed out with 0 DEAD, gates 1-3 natural, gate 5
source N/A, gate 6 UNTESTED. Gate 4 is BLOCKED pending this lane-16
EAT-receiver disposition via #167. The recorded umimushi71 dependency is now
satisfied, so this EAT question is the remaining producer gap; no live lane
owns it. Read-only review: no family/shared edits, no runtime, no ADMIT. All
six gates UNTESTED here.

## 1. EAT path inventoried (source-complete, with citations)

Reference checkout `output/autofill-native-585/pc_port/pc_p2_jigumo.cpp`
(read-only; family-owned, untouched):

- Attack/SAttack drive bite-then-swallow per the source key events (file:5-9,
  file:20-24): bite resolves an explicit capture inside the source attack
  radius, then exactly one InteractKill at the swallow event (exactly-once
  per bite, mirroring the Catfish/Armor ports).
- ATTACK bite at animation key event 2, frame 26: captures the nearest live
  Pikmin inside 200 units (file:489, file:496-499) and emits
  `P2_JIGUMO_BITE` (file:258-261).
- SATTACK activation at frame 13 with the same capture (file:587-590).
- Swallow/kill: `resolveKill` kills the captured Pikmin and emits
  `P2_JIGUMO_EAT` (file:266-273); via dive1 key event 8 / frame 80 in EAT
  (file:553-555) and via sattack1 key event 10 / frame 115 (file:601-603).

## 2. Pass1 evidence: the receiver WORKS (citations)

Run log `.../shard-enemies-4-jigumo63-observer/out/jigumo-run/pass1/
57adf491fd4742baaaf3ee5652505ba7/native.log` (read-only):

- Bind: line 725 `P2_JIGUMO_BIND generator=374003 source_id=63`.
- Bites at the banked frame (9 total): lines 1275, 1337, 1389
  (`P2_JIGUMO_BITE generator=374003 frame=13 ...`).
- Eats (7 total): lines 1325, 1375 (`P2_JIGUMO_EAT generator=374003 ...`).
- HP drain from throw impacts only: line 1232 `hp=500.0` (n=1) to line 1776
  `hp=380.0` (tick 1550); line 1781 throw n=117; timeout tail, 0 DEAD.
- Machine verdict from the reserved checker:
  `receiver-observed death-blocked-throughput` (117 throws, 9 bites, 7 eats,
  0 deaths, HP 380.0 floor, coherent, not injected).

## 3. Disposition: NO missing registration; blocker is damage throughput

- There is NO absent EAT-receiver registration to name (contrast Catfish
  #641, where the corpse marker was missing). Every leg of the receiver
  exists in source AND fired in pass1: stimulus, capture, swallow, kill.
- The precise blocker for gate 4 is damage throughput, not reception: the
  working EAT path eats the squad (7 Pikmin consumed) faster than the 117
  throw impacts damage the 500-HP host (120 HP total, floor 380.0), so no
  natural death is reachable on this stimulus schedule. Thrown-Pikmin impact
  damage alone cannot close gate 4.
- Recommended follow-on (observer lane scope, not this review): a run that
  puts latched (not thrown) attackers inside the 200-unit bite sweep so
  sustained attack damage, rather than throw impacts, drains the host; or an
  additional damage source. No code change is required for the receiver.
- Family-owner (#167) review: NO shared edit is needed or proposed, so no
  shared-file approval is requested. This finding is recorded for the
  consumer lane and the owner; if the owner disagrees and names a required
  registration, that becomes a new bounded scope.

## 4. Reusable checker and tests

- `experimental/pikmin2_jigumo63_eat_receiver_review.py`: `review(text)`
  inventories bind/throw/bite/eat/death/HP and reports `receiver-observed
  death-blocked-throughput` (or unobserved/refused variants). Fail-closed
  on injected markers, captain-down evidence and id mismatches; emits no
  markers.
- `tests/test_pikmin2_jigumo63_eat_receiver_review.py`: 8 focused tests
  (pass1 shape, unobserved receiver, observed death, missing bind, mismatch,
  injected, captain-down, empty). 8/8 pass.
- `gate_claim` is always `"none: review only"`.

## 5. Six-gate evidence (honest, review-only)

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | pass1 bind line 725 (cited, not claimed) | natural (no claim) |
| 2. Autonomous movement and animation | UNTESTED | not in review scope | natural (no claim) |
| 3. Attacks and receivers | UNTESTED | EAT receiver exists in source and fired in pass1 (9 bites, 7 eats); observed, not claimed | natural (no claim) |
| 4. Death and corpse | UNTESTED | no natural death in pass1 (HP floor 380.0); blocked by throughput, not by a missing receiver | natural (no claim) |
| 5. Actual transport and reward | UNTESTED | consumer records source N/A; out of review scope | natural (no claim) |
| 6. Cleanup and re-entry | UNTESTED | not in review scope | natural (no claim) |
