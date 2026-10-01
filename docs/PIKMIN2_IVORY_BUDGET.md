# Ivory same-species capacity (#395)

Implementation owner: Codex through shared account `4laric`. This is a bounded
White acquisition correction; the full White specification remains open.

The former preview callback charged every successful White sprout against the
Ivory's lifetime capacity, including a White thrown back into the same flower.
Retail `Pom::Obj::shotPikmin` decrements `mUsedSlotCount` for same-species inputs
to a non-Queen bud. Source audit: read-only Pikmin 2 revision
`632af93787b9c95b63f0c13be32b161375ce3a96`,
`src/plugProjectNishimuraU/Pom.cpp`, lines 286–306. Intake initially charges a
slot in the same file, lines 157–161; shot refunds that same-species charge.

Native `pc_p2_convert_ivory` now records two totals: successful sprout births
and changed-species lifetime slots. It captures the input's explicit White
identity before allocating a sprout. A same-species conversion still produces
one White sprout, consumes its one input with erase-kill, and does not spend
lifetime capacity. The callback returns charged slots to the existing Pom
`mReleasedSeedCount` adapter, while discharge placement uses the birth count.
This leaves leaf output and total-population behavior intact.

Replacement allocation still precedes input destruction. Failed allocation
returns the input to play and changes neither total. A later callback with zero
or negative remaining capacity releases its inputs instead of manufacturing a
new conversion budget. The change uses the existing native Pom allowance; it
does not establish retail numerical capacity or campaign supply renewal.

## Verification

Native commit `82dafd4bd1ca832bd2baa7abb8eb5962159a4b08` contains the production
callback and its directly used `P2IvoryBudget` policy. The standalone regression
compiles with MinGW GCC 16.2, C++17 and `-Wall -Wextra -Werror`. It covers repeated
White inputs, ordinary inputs, mixed batches, failed-allocation bookkeeping and
an exhausted next callback. Existing White extraction/poison tests are run
separately. Private build evidence is stored under ignored
`output/white-ivory-budget/`; exact build results and hashes are recorded in #395.

Fresh guarded engine acceptance subsequently passed twice in
`output/white-ivory-budget/run-03` and `run-04`, using native fixture commit
`c4c36fac769b8829fa11a70a6fb0f3078d636a9e` and `fixture-03/provenance.json`.
The fixture observes 20 initial Reds and one bound Ivory UID 25 on the P1 practice
map, without enemies. It injects species and capture attachments, then executes
the actual production callback, sprout births and input erase-kills:

- Reserve all 100 real sprout-pool entries; the refused replacement returns
  its living input to play, spends zero slots and preserves 20 bodies.
- One White input creates one genuine White sprout and spends zero slots.
- One ordinary Red input creates one White sprout and spends one slot.
- A mixed batch creates three White sprouts and spends one slot.
- An exhausted callback releases two living inputs; replay changes nothing.

The final population is 15 actors and five White sprouts, still 20 bodies.
Both bounded runs exit 0 in about 4.4 seconds. This establishes native callback,
allocation and population behavior with injected setup; it does not establish
natural capture, plucking or controller conversion.

The observed SDL window is 960×540 at position 373,263 with captain HP 100.
The fixture calls the canonical captain guard immediately after each engine
idle, before movie/pause/observation/PASS handling. A separate forced-down run
of the same executable exits 86 with `P2_FIXTURE_CAPTAIN_DOWN`, without a PASS.
The canonical guard's five policy tests also pass.

Earlier failures remain in `run-01` and `run-02`; their coarse baseline assertion
does not establish which count/binding failed. The diagnostic fixture now prints
actual actor counts, types and UID before asserting. New staging uses the current
native reader's little-endian raw generator identity; the successful runs verify
UID 25 and the exact 20-body baseline. Source-derived White assets were freshly
regenerated from the local disc, with the original audited source hashes.

Campaign conversion receipts, Ivory-instance persistence, ship compartments,
gas panic/immunity, buried treasure and natural controller/campaign acceptance
remain separate White work. This change does not add AP unlocks or modify cave,
save or storage schemas.
