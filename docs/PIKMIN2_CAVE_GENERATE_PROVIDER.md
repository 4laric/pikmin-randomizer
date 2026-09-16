# Retail cave generation provider (lane cave-generate-provider, issue #129)

Implementation owner: Codex through shared GitHub account `4laric`.
Executing worker: muse-l60 (approved pool session retained), generation 2.
Implements the generation-review port plan; full level acceptance stays
UNTESTED (generation mechanics proven, not a playable level); no ADMIT.
Issue #129 stays OPEN.

## Design (follow the review plan exactly)

New header-inline policy module `native/pc_port/pc_p2_cave_generate.h`
with a thin TU `native/pc_port/pc_p2_cave_generate.cpp` (wired into
`PC_PORT_SOURCES` under #186 review as the follow-on; until then the
header carries the implementation so no CMakeLists change was needed).
One narrow hook in `native/pc_port/pc_p2_cave.cpp` after `P2_CAVE_READY`
(2 insertions: include + `pc_p2_cave_generate_run();`), arranged for
#186 review before any shared integration. Transfer/restore/checkpoint
logic, Beasts paths, nav marker strings and Bulbmin rules are untouched.

The generator is opt-in via the `p2-cave-generate.txt` sidecar, written
root-side from a completed-P0 packet floor (pool/roster as-is; unit
geometry decoded by the caller with the shared `unit_definition`
parser). Absent sidecar: zero markers, zero behavior change. Any
malformed line: `P2_CAVE_GENERATE_REFUSED reason=<code>`, existing flow
continues (existing `P2_CAVE_READY` still fires; no invalid abort).

## Sidecar contract (normative; mirrored root-side and asserted at runtime)

Flat sections in fixed order: magic `P2_CAVE_GENERATE_1`; `pool`
(name + 1..64 units, ascending idx, positive finite cells);
`rooms` (1..256, valid unit, turn 0..3, finite offsets);
`doors` (0..4096, dir 0..3); `links` (every link resolves to a staged
unit/door, non-negative finite distance; symmetric-pair count reported);
`spawns` (1..256 rows, count >= 1); `anchor hole|geyser`. The transition
anchor is derived: room-0 origin, radius clamped 20..150 over the largest
room diagonal (mirrors `p2_cave_read_anchor` bounds). Rotation matches
`experimental.pikmin2_assembly.transform` (turn t applies t times
(x,z)->(-z,x)); the harness recomputes every room AABB and the anchor
and fails on drift beyond 0.002.

Markers per run: `P2_CAVE_GENERATE_POOL`, one `ROOM` per room (unit,
turn, world AABB), one `SPAWN` per roster-minimum row, `LINKS`
(total/symmetric), `ANCHOR` (derived), `PASS` (counts). Zero-minimum
roster rows are skipped at stage time with the skip count reported.

## What this proves (and does not)

Proven: pool selection, room placement vs pool geometry, roster-minimum
spawn intents vs caveinfo minima, door-link resolvability, anchor
derivation, and unchanged transfer/restore behavior — all observed in a
fresh-arena product run. Not proven: retail `MapRoom::placeObjects`
actor births (spawn intents are data + markers; live Teki birth is the
bounded spawner follow-on), multi-room graph traversal, schedules,
playability, or admission.

## Verification

- `py -3.12 -m pytest tests/test_pikmin2_cave_generate.py -q`
  -> hermetic unit tests for rotation/bounds/anchor/sidecar/verify
  (malformed battery included).
- Fresh-arena harness (`experimental/pikmin2_cave_generate_proving.py`):
  current overlay squad, 960x540 centred window, product binary;
  asserts rooms/spawns/anchor against recomputation plus unchanged
  `P2_CAVE_READY`; negative sidecars assert `REFUSED` with intact
  existing behavior. Run evidence under the lane output dir.
- Private leased build: pinned commits, `ninja -n` clean, exe SHA-256;
  no replacement-main fixture (product-binary runtime, stated plainly).

## Remaining work (bounded follow-ons)

- Spawner follow-on: translate `SPAWN` intents into live Teki births
  (family lanes own vulnerability/behavior).
- Integrator wiring of `pc_p2_cave_generate.cpp` into `PC_PORT_SOURCES`
  under the filed #186 review.
- Schedule parameters and multi-floor descent chains (P1/P2 scope).