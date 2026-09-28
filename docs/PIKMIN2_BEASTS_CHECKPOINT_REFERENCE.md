# Standalone Beasts checkpoint reference adapter

`experimental/pikmin2_beasts_checkpoint_reference.py` implements the bounded
#154/#132 proposal as pure state transformations. It does not write files or
change the tutorial campaign, SurfaceLedger, SurfaceRunner or native protocol.
It is not a second save system. Production integration must commit its returned
state through the existing authoritative ledger and replay command protocol.

Create `BeastsReferenceAdapter(audit, content_hash, floor_receipts)` using the
source audit from `pikmin2_beasts_lifecycle_reference`. The adapter binds its
identity to that complete audit, imported content identity and per-floor allowed
receipt maps. Floor2 must have an empty allowed map. Existing receipts may be
carried through; conflicting per-instance values in the profile are rejected.
The caller supplies actual staged receipt values, not invented source prices.

`initial(trip, squad, health, receipts)` starts floor1. `token(state)` binds trip,
profile, floor and revision. `apply(state, token, squad, health, receipts,
conversions, destination_context)` returns a new state without mutating input.
An exact old-token replay returns the newest state; changed payload conflicts.
Stale tokens, altered profiles, receipt regression and unsupported new credit
are rejected. Extinction or zero health creates a terminal state with no squad.
Casualties and maturity changes remain legal; unsupported species/population
increases do not.

Floor1 handoff requires explicit floor2 generation context:

```python
{
    'global_plus_cave_purple': 0,
    'spawned_flowers': [
        'forest_1:floor2:BlackPom:0',
        'forest_1:floor2:BlackPom:1',
    ],
}
```

This context is supplied by the future trusted staging adapter and must reflect
actual spawned instances and source population context. At20 or more Purple,
only an empty spawned list is accepted. Counts below the incoming Purple party
are rejected. A permitted bud gets5 net conversion slots. Floor2 generation
context is persisted in the state; it is not recomputed from its later converted
party. A subset of permitted buds can be declared when staging actually omits
an instance.

Conversion witnesses are ordered records with unique `id`, stable `flower` and
`input` species. Non-Purple input consumes one slot and changes one available
Pikmin into Purple. Purple input requires an available Purple and refunds the
slot. The resulting survivors must fit the converted population, allowing
casualties. Per-instance capacity and duplicate identities are checked. The
current native handoff does not emit these witnesses: this is a trusted-native
interface contract, not evidence that a player performed a conversion.

Floor2 handoff takes empty destination context and commits revision2, floor3,
status active. `launch_requirement` rejects floor3 staging explicitly. For
floors1/2 it returns `native_ready=false` and a reason, so no caller should treat
this reference as a production launch permit. There is no synthetic cave exit
at floor2, nor a claim that floor3 or the full cave is implemented.

The schema string `P2_BEASTS_CHECKPOINT_REFERENCE_1` is deliberately separate from
tutorial schema1. Existing tutorial code/save identities remain unchanged.
The profile reference currently requires the observed Beasts first three edges,
no fountain/clog and source5-slot capacity. It does not implement arbitrary cave
graphs, Queen Candypop multiplication, enemies that create Pikmin, mid-floor
saving or global population collection.

Validation:8 adapter tests plus4 subtests cover floor2->3, per-bud limits,
source birth gate, same-color availability/refund, old replay after a later
transition, conflicting payload, stale token/profile, invalid health, terminal
failure, casualties and receipt stability. Combined with source-reference,
tutorial campaign, surface-ledger and runner tests:37 tests and8 subtests pass.
No native launch or shared build was performed.

Issue #274 also validates stored conversion records when loading a checkpoint:
the dictionary key must match the witness identity, the source must be a known
floor2 Violet, and non-Purple inputs must fit its five-slot capacity. History
can first appear after committing the floor2 boundary, including terminal
failure on that floor. Failed-floor history must agree with the retained birth
snapshot. Same-color refunds remain valid.

This is structural validation, not authentication of gameplay. Floor3 does not
retain the previous floor's generation snapshot or original party, so standalone
validation cannot reconstruct those facts. The transition still checks them
against its input checkpoint. Authoritative persistence and native witnesses
remain required before campaign use.

Validation for #274: checkpoint, lifecycle, generation and floor2 runtime suites
passed 24 tests and 58 subtests, including JSON round trips, malformed records,
over-capacity history, premature history and failed-floor replay. Native sources
and shared save semantics are unchanged.
