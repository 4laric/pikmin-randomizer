# Tutorial crash-fix #186 decision packet (#785)

Lane `tutorial-186-packet`, issue #785 (OPEN, 4laric-assigned; downstream #148).
Implementation owner: Codex through shared account `4laric`. This is a **tooling**
packet for prerequisite recovery request `5aac47ab...`: it packages the exact
pins, shared guard scope, consumer check, requested #186 decision and landing
disposition for the blocked `tutorial-p1-font-settexture-crash-fix` (#750)
slice, consuming that lane read-only without duplicating its scope or touching
shared files. No engine edits, no builds, no runtime runs, no ADMIT. All six
gates UNTESTED.

## Producer pins (read-only refs, verified)

- Root `69b74c1ed5ebd096be1c5c9eb8fcd0a9d4023490`, native
  `0940c1e4c2d47519df3b8f0a44f2e921796b722f` (blocked lane record; clean).
- Shared guard callsite: `native/src/sysCommon/graphics.cpp::Font::setTexture`.
  Build membership: `native/CMakeLists.txt` (verification scope only, no change).
- Consumer: `p2-overworld-tutorial-p1-staged-rerun` re-run expecting no
  `0xC0000005` at `Font::setTexture` (or an exact new blocker); downstream #148.

## Requested #186 decision

Approve/amend/decline the `Font::setTexture` guard with reasons. On approval the
single-writer integrator lands root `69b74c1e` + native `0940c1e4`, rebuilds
under lease, and re-runs the staged boot. No approval is granted by this packet.

## Owned files (all new)

- `experimental/pikmin2_tutorial_crash_fix_186_packet.py` (fail-closed packet
  builder; 7 focused tests green).
- `tests/test_pikmin2_tutorial_crash_fix_186_packet.py`.
- This file.

## Six-gate status (tooling; all UNTESTED, no runtime claim)

| Gate | Status | Evidence | Method |
|---|---|---|---|
| 1-6. all gates | UNTESTED | n/a (packet only) | unobserved |

## Captain safety (#632)

N/A (no runtime run). Any future staged-boot run must adopt
`scripts/p2_fixture_captain_guard.h` with orimaDead/NaviDead/HP<=1 checks,
CAPTAIN_DOWN + BLOCKED exit, and a parked captain.