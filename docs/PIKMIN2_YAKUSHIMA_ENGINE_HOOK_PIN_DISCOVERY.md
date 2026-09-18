# Yakushima engine-hook pin-discovery (wired surface session)

Lane `yakushima-engine-hook-pin-discovery`, issue #789 (OPEN), downstream
recovery `bd5aaf22` / `p2-overworld-yakushima-p1-native-runtime` (#150, blocked
gen 18). Owner: Codex through shared account 4laric. Diagnosis only: read-only
audit, no native edits, no builds, no runtime, no ADMIT. All six gates UNTESTED.

## Question

The #150 fixture (`native/tools/p2_yakushima_p1_runtime_fixture.cpp` at native
`d01b89a7`) reports four surface-session boundaries UNSUPPORTED (save+endpoint
proven separately and out of scope here). For each boundary: exact engine hook
point, or verified absence plus nearest foothold, landing owner/files (or
deferral).

## Verdicts (all ABSENT; no hook exists)

1. **boot_yakushima_surface** (`no-overworld-course-boot-in-port`): ABSENT - no
   CourseBoot/overworld/cave-course boot symbol in `pc_port` or `plugPikiColin`.
   Footholds: `pc_pikipelago_room_preview` (`pc_bbft.h`; room boot) and
   `pc_p2_cave_setup/tick/request` (`pc_p2_cave.h:4-6`; cave boot, not
   overworld). Owner: new overworld-boot provider (unowned) + #186 boot-path
   review.
2. **day_transition** (`no-day-advance-api-in-port`): ABSENT as a callable API.
   Port has only `pc_randomizer_next_day` (`pc_randomizer.h:17-18`, diary
   repeat) and `pc_settings_get_day_minutes` (`pc_settings.h:63-64`).
   Footholds: retail day-end flow (`ogResult.cpp:602-638`,
   `RESULT_Active/RESULT_ExitToMapSelect`); day clock exists
   (`pc_photo_mode.h:9`) with no advance entry. Owner: new day-advance
   provider (unowned) + #186.
3. **receipt_replay** (`no-engine-receipt-hooks-in-port-#186-pending`): ABSENT
   engine hook. `P2Economy` ledger exists (`pc_p2_economy.h:5-13`) but only
   `pc_p2_preview.cpp` references it; zero engine session-event callers of
   `credit()`. Footholds: `P2Economy::credit` (needs call sites),
   `pc_p2_cave_receipt_prefix` (`pc_p2_cave.h:9`; cave-scoped). Owner: #186
   shared-hook review for receipt driver call sites + receipt provider.
4. **exit_reentry** (`no-exit-reentry-path-in-port`): ABSENT - no
   exitCourse/goToTitle/returnToTitle in `pc_port` or `plugPikiColin`.
   Foothold: retail `ogResult` exit states (`ogResult.cpp:626-636`,
   `RESULT_ExitToMapSelect/RESULT_ExitToCardSelect`). Owner: new exit/reentry
   provider (unowned) + #186.

## #186 decision request (filed with this packet)

Request to the shared-review owner (`species-integration-owner` via
`workflow.review_decisions`): approve the per-boundary hook approach - (a) new
provider scopes for boot/day/exit (+ receipt call sites on `P2Economy`), (b)
shared call-site review for the `pc_bbft.cpp`/engine seams - against
destination pins root `f2803e42` / native `b944db03`. No bytes proposed here;
this diagnosis is never an engine unblock. The repair is not complete until
the #150 consumer boundaries observe (currently UNSUPPORTED).

## Tooling

`experimental/pikmin2_yakushima_engine_hook_pin_discovery.py` exposes the
machine-readable registry (`pins`) and a fail-closed boundary checker
(`check --boundary`). 5 focused tests green (schema, downstream/destination,
per-boundary ABSENT, unknown-boundary REFUSED, malformed refused).