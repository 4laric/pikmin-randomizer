# Overworld course boot flag #186 request + tooling handoff (#738)

Lane `overworld-boot-flag-review`, issue #738 (OPEN, 4laric-assigned; downstream
#696/#148). Implementation owner: Codex through shared account `4laric`. This is
a **tooling** deliverable: a review adapter, a guarded boot-smoke fixture, focused
tests, and this #186 request. No shared/family/native landing, no gameplay
acceptance, no ADMIT, no ledger writes.

## #186 request (shared-native overworld course boot flag)

The `pc_port` boot dispatch (`pc_port/pc_bbft.cpp:42-53` at native pin
`b805d9c6`) offers only `--experimental-pikmin2-room` and
`--experimental-challenge-level 0-4`. No overworld course boot flag exists, so
tutorial P1 native runtime cannot boot its stage (pre-idle stall, #707 verdict).

Requested (for #186 existing-owner approval; NOT landed here): add to
`pc_port/pc_bbft.cpp` a `static std::string p2OverworldCourse`, an
`OVERWORLD_COURSES[] = {"tutorial"}` table with a `pc_overworld_course_known`
predicate, a `--experimental-p2-overworld-course <name>` branch that validates
non-empty + known + mutual exclusion and emits `P2_OVERWORLD_BOOT course=<name>`,
a `pc_pikipelago_overworld_course()` accessor, and the two one-word guard
extensions so room/challenge branches also refuse an already-selected overworld
course; plus the `pc_pikipelago_overworld_course()` declaration in
`pc_port/pc_bbft.h`. Unknown/empty/mutually-exclusive selections exit 2
fail-closed. The exact proposed diff is produced byte-identically by
`experimental/pikmin2_overworld_boot_flag_review.py --cpp ... --header ... --out ...`
onto private copies; the packet JSON carries both patched hashes and the hook
findings. The single-writer integrator lands it only on #186 approval.

## Owned files (all new)

- `experimental/pikmin2_overworld_boot_flag_review.py`: fail-closed review
  adapter (`apply_proposal`/`verify_proposal`/`request_packet`); refuses drift,
  double-apply, missing anchors, and empty inputs; writes nothing on failure.
- `tests/test_pikmin2_overworld_boot_flag_review.py`: 10 focused tests (clean
  apply + verify, order, existing intact, double-apply/missing-anchor/empty
  refused, no-write on failure, refusals present, packet). All pass.
- `native/tools/p2_overworld_boot_smoke_fixture.cpp`: guarded `RoomApp` boot
  smoke (spliced into `tools/preview_p2_room.cpp`); reports dispatch mode and
  emits `P2_OVERWORLD_BOOT_ABSENT` on the current tree; adopts
  `scripts/p2_fixture_captain_guard.h` (#632) with `CAPTAIN_DOWN` exit 86. No
  `mHealth`/`TransportMode` write.
- This file.

## Build / run provenance

- Lane native pin `codex/overworld-boot-flag-review-native` head `b805d9c6`,
  clean (base `b805d9c6`). Lane root pin `codex/overworld-boot-flag-review`
  head `2e631f74`, clean.
- Adapter + tests are engine-free and fully green (`pytest ... -q` -> 10 passed).
- The smoke fixture is compile-checked (syntax) against the pinned tree; a full
  leased `pikmin_pc` build + headed run is explicitly out of scope for this
  tooling slice and remains with the integrator after #186 approval.

## Six-gate status (tooling; all UNTESTED, no runtime claim)

| Gate | Status | Evidence | Method |
|---|---|---|---|
| 1. identity_spawn | UNTESTED | n/a (tooling) | - |
| 2. movement_animation | UNTESTED | n/a | - |
| 3. attacks_receivers | UNTESTED | n/a | - |
| 4. death_corpse | UNTESTED | n/a | - |
| 5. transport_reward | UNTESTED | n/a | - |
| 6. cleanup_reentry | UNTESTED | n/a | - |

## Captain safety (#632)

`native/tools/p2_overworld_boot_smoke_fixture.cpp` includes and calls
`p2_fixture_require_captain(orimaDead, NaviDead, hp, tick)` before observation
ticks, emitting `P2_FIXTURE_CAPTAIN_DOWN ... outcome=BLOCKED` and exiting 86.
The captain is parked outside attack reach; no blanket invincibility is used.
`fixture_adoption.captain_safety` policy is `unprotected` (boot smoke only).

## Residual / next

- #186 owner approves/amends/declines the proposed diff; the integrator lands it
  (single writer), rebuilds under lease, and the #696 consumer proceeds.
- Day-advance trigger and surface exit/re-entry (the other two ABSENT items)
  remain for future turns.