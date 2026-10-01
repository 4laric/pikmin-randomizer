# Cave generator consumer landing (#129)

Implementation owner: Codex through shared account `4laric`. Lane
`cave-generator-consumer-landing`, prerequisite for the #635 queue recovery.
This is the actual missing implementation/landing patch identified by the
completed `cave-generator-landing-contract-review` ? not another review.

## Source

Accepted native `e44b5d70` ("wave-native: merge #129 cave generator module +
reviewed pc_p2_cave.cpp hook"): header-inline retail cave-generation policy
(`pc_p2_cave_generate.h`, 250 lines) plus a TU stub whose CMake wiring was
explicitly deferred to a follow-on under #186 review. That follow-on is this
slice.

## Landing (consumer baseline `a95040b6`, branch `codex/prereq-cave-generator-consumer-landing`)

- `native/pc_port/pc_p2_cave_generate.h` ? byte-identical port of the accepted
  header (opt-in `p2-cave-generate.txt` manifest sidecar; flat pool/unit/room/
  door/link/spawn/anchor sections; `P2_CAVE_GENERATE_*` markers;
  `P2_CAVE_GENERATE_REFUSED` on malformed input, changing nothing; absent
  sidecar returns false with zero markers and zero behavior change).
- `native/pc_port/pc_p2_cave_generate.cpp` ? TU wired into `PC_PORT_SOURCES`
  (this was the deferred item); comment updated to record the landing.
- `native/pc_port/pc_p2_cave.cpp` ? identical hook shape to the accepted
  patch: `#include "pc_p2_cave_generate.h"` plus one
  `pc_p2_cave_generate_run();` call after `P2_CAVE_READY` in
  `pc_p2_cave_setup()`. Transfer/restore/checkpoint logic, Beasts paths, nav
  strings and Bulbmin rules untouched.
- `native/CMakeLists.txt` ? one line: `pc_port/pc_p2_cave_generate.cpp`
  appended after `pc_port/pc_p2_cave.cpp` in `PC_PORT_SOURCES`.

Total diff: 3 insertions across the two tracked files, 2 new files. No shared
checkout edits, no maintained export, no behavior change without the opt-in
sidecar.

## Validation

- `tests/test_pikmin2_cave.py`, `test_pikmin2_cave_catalog.py`,
  `test_pikmin2_cave_dependencies.py`: 20 passed, 1 skipped.
- TU standalone syntax check green (stdlib-only includes).
- Private leased build (private dir under the lane `out/`): pinned commit,
  executable SHA-256 and `ninja: no work to do.` dry run recorded in the
  child issue; baseline adoption recorded there as well.

## Consumer update instructions

- **yakushima4 P1** and **tutorial caves**: feed a completed-P0 floor packet
  through the sidecar contract documented in the header
  (`P2_CAVE_GENERATE_1`, pool/units/rooms/doors/links/spawns/anchor in fixed
  order) as `p2-cave-generate.txt` in the run directory. Absent sidecar =
  today's behavior exactly.
- Malformed manifests are refused with a `reason=<code>` marker and change
  nothing; consult the header comment for the refusal codes.
- Do not claim playable floor acceptance from build success; P1/P2 runtime
  acceptance (collisions, routes, actors, receipts, persistence) stays with
  the consumer lanes on their own evidence.

No ADMIT. Issue #129 stays open until the integrator lands this patch.
