# ch_NARI_03toy P1 runtime acceptance (#746)

Lane `p2-challenge-ch-nari-03toy-p1`, issue #746. Owner: Codex through shared
account `4laric`. Bounded P1 runtime slice for P2 Challenge 06, reusing the
done P0 import base (#540) read-only and the landed #743 gap-stages
extension (read-only) and following the accepted houdai/damagumo/redblue P1
shape. Owns only the reader, its tests, this doc and the guarded fixture.
No engine/family/shared edits, no ADMIT, no ledger writes.

## Stage resolution

`select_stage_extended("ch_NARI_03toy")` through the landed #743 extension
returns provenance `gap`: 2 floors, timers 100.0/150.0, UI 5, table order 2,
100 flower Blue (row 2), bitter 2 / spicy 2, source
`d74b49ac...`. The reader validates every field against the catalogued P0
pin and refuses drift fail-closed. Fresh run layout (stage manifest, input
package with unique generator IDs and recorded positions, ordinary kusachi
control, hashed run plan) is staged, not observed.

## Native position (honest)

The pinned native base names no P2 challenge stage (zero hits for
ch_NARI/kusachi/02tile in `pc_port`). The guarded fixture therefore fails
closed with `BLOCKED ... engine-table-row-pending` (exit 3) until a shared
engine-table row lands (owner #710 mechanics + #186 review), exactly as the
sibling houdai proof on the identical base. Captain safety #632 is adopted
(vendored tested guard, self-test + negative hook); captain parked outside
attack reach; no blanket invincibility.

## Gates

All six UNTESTED unless a headed boot genuinely observes them. No
playability claim.
