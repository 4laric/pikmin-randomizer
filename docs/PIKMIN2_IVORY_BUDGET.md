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

These policy tests do not execute actor allocation, throw controls, discharge
animations or full gameplay. No fresh runtime acceptance is claimed. A fresh
fixture must adopt the current 20-Pikmin overlay, centered 960×540 startup and
captain guard before testing mixed-species conversion in the engine.

Campaign conversion receipts, Ivory-instance persistence, ship compartments,
gas panic/immunity, buried treasure and natural controller/campaign acceptance
remain separate White work. This change does not add AP unlocks or modify cave,
save or storage schemas.
