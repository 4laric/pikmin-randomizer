# Bounded Pikmin receiver ownership (#385)

Codex implementation owner using shared account 4laric. The shared engine now
contains the Lesser Jellyfloat receiver core from native `e701e640`, with the
ownership corrections below. Actor/arena registration stays in the #243 family
lane. The core is inactive until `pc_p2_kurage_receiver_setup(owner, mouth)`.

## Engine boundary

- `Piki::doAI` yields only for a live current receiver reservation. Mouth travel
  requires an unattached Pikmin; stomach control requires the exact owner and
  mouth link. A replacement attachment immediately regains ordinary AI, even
  before the receiver's next update.
- `Creature::kill` revokes a Pikmin reservation before stick cleanup/recycling,
  and invalidates an owner before its destruction path. Stage exit resets the
  receiver before managers and stage objects are discarded.
- Mouth travel owns both velocity fields. Arrival, owned release and reset clear
  those fields; receiver cleanup does not overwrite a replacement attachment.
- Reset revokes the old batch before callbacks. A new reservation created by a
  callback is not swept, and an old digestion result cannot kill a Pikmin that
  the callback recaptured or attached elsewhere.
- Stomach digestion retains the imported 16-second countdown and separate
  half-second shrink, with the existing pause rules and captured-scale restore.

Review found that `e701e640` used table membership alone for AI control and did
not reject a replacement attachment during mouth travel. It also advanced the
generation before release, preventing cleanup of an unattached suction passenger.
The new tests reproduce the latter failure on the original receiver and exercise
all three boundaries on the corrected implementation.

## Family adoption

Use the shared `pc_p2_kurage_receiver.{h,cpp}` and digestion header instead of
overwriting them with the earlier private copies. Preserve the additive CMake,
Pikmin-AI, death and stage-exit hooks when rebasing a family candidate. Call reset
before discarding an owner or collision part by any path that bypasses ordinary
Creature death. Actor code still owns update scheduling and owner-health inputs.

This is a single-owner, ten-passenger adapter. It is not a general multi-enemy
capture registry, Greater Jellyfloat captain capture, the retail P2 Pikmin FSM,
or automatic production Jellyfloat activation. Animated mouth placement and the
family's remaining actor work are separate. A Pikmin that changes attachment is
left to its new owner; that owner is responsible for its own scale/motion policy.

## Validation boundaries

`tests/test_pikmin2_receiver_ownership.py` compiles the production receiver against
observable engine doubles. It covers inactive control, suction/reset, owner
invalidation, immediate transfer during both phases, arrival, shrink/release,
Pikmin invalidation and callback recapture. It also compiles the source digestion
policy tests. These are ownership tests, not rendered gameplay or physics proof.

The pre-fix receiver fails the travel-reset velocity assertion; the corrected
receiver passes. The production native build and configured Python suite are
recorded on #385. The #243 worker's five live scenarios remain evidence for its
frozen original candidate, not a claim that this corrected shared build has been
run through that family arena. The family should rerun those scenarios when
adopting the corrected core. Player packages and saves are unchanged.

Shared native commit: `c53ab523`. Production `pikmin_pc` build passed; executable
SHA-256 `3401a22165ffc7347f4e260e0421643bd594b3f228ee8cdd1845cc52afc4e0e7`.
Configured full Python suite: **1,358 passed, 23 skipped, 665 subtests passed**.
Local evidence: root private worktree `output/receiver385-tests.log`; native
private worktree `output/receiver385-build-final.log` and
`output/receiver385-before.log` (expected pre-fix regression failure).
