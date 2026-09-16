# ElecBug28 gate-5 receipt adjudication (#585 vs the admitted #578 standard)

Review-only slice, lane enemy-elecbug28-gate5-adjudication (issue #585).
No runtime run claimed or started, no build, no shared edit, no ADMIT.
The transport_reward gate stays UNTESTED here; the ruling stays with the
integrator (#437). Machine-checked by
experimental/pikmin2_elecbug28_gate5_evidence.py (5 focused tests pass on
the real evidence, read-only).

## Side-by-side: endpoint reality

Both slices deliver through a REAL ordinary Onion endpoint, not a test
hook. #578 Sokkuri79: natural 567.61u haul to the container, then
onion:p2:79 new=1 and duplicate new=0 across restart. #585 ElecBug28:
P2_ELECBUG28_DELIVERED_TO_GOAL moved=557.50 by free Pikmin, then
P2_ORDINARY_P2_RECEIPT id=onion:p2:28:0 new=1 (run1) and new=0 (run2),
same seed and check id, one shared session-ledger row
(onion:p2:28:0 g346002 corpse). Verdict: endpoint parity holds.

## Side-by-side: restart semantics and carry markers

Both prove exactly-once across a process restart sharing one session
ledger (single ledger row; duplicate redelivery consumed as new=0). Both
show natural death (health=0.00 through the real receiver, no health or
state writes) and a real corpse pellet, then a free-Pikmin haul of
comparable distance (567u vs 557u) with no Transport assignment and no
injection markers. Neither log contains staged-state markers; the
natural-carry evidence is engine-emitted in both runs.

## What each withheld, and why

#578 withheld only cleanup_reentry (re-bind is not scene re-entry) and
earned five natural gate PASSes. #585 withholds all six gates because its
course is fixture-staged (replacement main, private course): the harness
cannot support a gameplay PASS claim. Its one extra staged element versus
#578 is the flip stimulus (flip=staged-press: a staged Purple landing,
because the host has no Purple hipdrop state). That stimulus is honestly
labelled, is not an enemy health/state write, and mirrors the class of
staging #578 itself discloses (squad staged in FreeMode, replacement
main). Nothing in either log contradicts the honest labels.

## Recommendation: UPHOLD-STAGED-TOOLING

Uphold the staged transport observation as sufficient for the
tooling-scoped exactly-once claim under the admitted #578 standard:
same ordinary endpoint, same exactly-once restart semantics, same
natural death and haul markers, same honest withholding. This unblocks
the #578 remaining-work note that ElecBug28 was deferred until its
receipt is accepted. transport_reward itself remains UNTESTED; no gate
is flipped here.

## Exact natural experiment if the staged claim cannot stand

If the integrator rejects the flip stimulus, close transport_reward with
one unstaged session: natural flip through a real Purple hipdrop (or an
engine-provided flip path, no staged landing), natural 500 HP drain
through the real receiver to health=0.00, free-Pikmin haul to the room
container, ordinary receipt new=1 then duplicate new=0 across a process
restart sharing one session ledger. Reuse #585 owned files verbatim
(bridge, replacement-main fixture, runner/auditor, ledger format); the
only shared touch is the pre-existing lane-06 ordinary endpoint, which
needs no new review. Standard 960x540 centred-window fixture adoption
with a fresh arena and live starting squad applies.
