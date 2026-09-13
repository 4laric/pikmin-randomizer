# Beasts floor 3 donut transport (#361)

Codex owns this bounded experiment using the shared 4laric account. It extends
#360 with an external fixture; no production native source changes are included.

The source-bound donutswhite instance is
`forest_1:floor3:treasure:donutswhite:0`, generator 63001, source treasure row 0,
block-room type-2 slot 2 at (175,20.5,-55). The #357 plan binds the model, floor
package and assembly hashes, value 230, weight 15, slots 25, Pod (-85,0,-280),
and directed source route 6→4→3→0. This route stays inside the block room.
The offline route does not force the native transport AI's route selection.

The fixture restores 20 Red leaf Pikmin and assigns real Transport actions.
It does not teleport carriers/cargo, repair routes, change the source cargo
anchor, or modify geometry. Captain/controller assistance and scripted carrier
assignment are engineering interventions. The captain starts at (0,-100), with
all 20 party grid positions on the lower floor. An earlier (180,-20) start had
only 18 living Pikmin at the fixture check, including a falling survivor; those
failed runs remain preserved. READY reports the generator position; the first
actual cargo trace separately reads (175,20.5,-55).

This uses the actual imported source visual model and source economy settings
on donor pellet physics. Measured donor bottom radius/center size are 20,
cylinder/carry height 14, and config scale 1. Source radius/p_radius 50 and
height 5 are NOT implemented; the visual spans approximately X±54.217 and
Z±56.756. The plan's 50-wide support strip does not cover that authentic source
footprint. A successful haul therefore does not establish authentic donut
collision or clearance.

## Evidence

Private outputs are under `output/donut361` in the owning worktree.
The frozen native source is d69580fa7f5441286e82b065b3e36d2bc5066cf4,
private `native-beasts-floor3-cargo-terminal/build-terminal`. External fixture
linking leaves that source/build unchanged. The ordinary fixture executable
SHA-256 is aa4adaa3833f8ea5127b469e67edc57c81477ab677a4dffc6bd4280e8f75c199.

- `runs/03c13ce157694df7afcbc1ffb27ce1dc`: PASS, 65 actual cargo points,
  peak 20 attached carriers, actual Pod delivery, exact 230-Poko receipt,
  duplicate delivery adds zero, and native economy reopen has one receipt.
  A read-only reviewer independently revalidated log/input hashes and acceptance.
- `runs/c4af59d3eb59477d83c272005d01ebab`: fresh-process replay FAILED at
  the 6000-tick native bound. Cargo remained around (219,ground 0,32), with
  carriers attached, and did not reach the Pod. The copied 230-Poko ledger
  remains evidence; a same-process reader reopen is not fresh-process replay.
- Raised-start failures `20be245a60f24ac5a966f5af3121fc9b` and
  `958d83cc813f45e0b1d09bc832b63de4` remain preserved.

A separate read-only diagnostic fixture logs the actual Stickers leader,
native waypoint buffer, transport state and spline control points. It changes
no AI state. Its single bounded replay is recorded separately below.

Validation: 9 Python tests and 59 subtests passed, including existing green-haul
and cargo-terminal regressions. Strict acceptance checks exact economy bytes,
receipt credit flags, carrier threshold, ordered physical approach markers,
finite donor measurements, input/executable hashes and absence of floor transfer.

This is diagnostic economy only. Campaign rewards, successful descent and full
floor-3 gameplay remain unauthorized. Enemy actors and authentic donut physics
are absent. The optional cargo-terminal marker is not installed.

## Bounded diagnostic outcome

`runs/af2e1685552247068a88c54c4439f382` FAILED at the 150-second host
timeout, with no delivery receipt. The actual leader selected nodes 6,4,3,0;
transport stayed in state 3 / path 0, with spline control points from
(175,20.5,-55) to (150,20.5,0), while 20 attached carriers and cargo
oscillated near the starting platform. The initial connector is therefore a
remaining native transport/terrain interaction blocker even with a valid
directed path. This does not establish a particular collision or AI defect.
No geometry, cargo placement, transport state or route links were changed.

Both failed replay ledgers remain byte-identical to the first delivery ledger:
SHA-256 `54c269c8bfd73e9504893700cc74dfe9b7d71ab982c6ccdbe9eaa2e208647e1d`.
The failed ordinary replay's inputs/log hashes and unchanged ledger were also
independently reviewed. No further attempts were made. First delivery and
same-process duplicate/reopen pass; **fresh-process rehauling remains failed**.
The overall haul/replay milestone is not complete.
