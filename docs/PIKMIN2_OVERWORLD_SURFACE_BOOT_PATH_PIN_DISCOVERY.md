# Overworld surface boot-path pin discovery (lane provider-overworld-surface-boot-path-pin-discovery, #707)

Bounded pin-discovery/ownership for the shared P2 overworld surface runtime
path blocking tutorial #696/#148 and siblings #660/#149, #150, #151.
Root-only tooling: no source/shared/family/native edits, no builds, no
runtime. All six gates UNTESTED; no ADMIT.

## Verdicts (root base c86e4029; native pin b805d9c6)

1. **Course boot / surface entry: ABSENT.** `pc_port` boot-flag dispatch
   (`pc_bbft.cpp:44-51`) offers only `--experimental-pikmin2-room` (room
   preview) and `--experimental-challenge-level 0-4` (P1 challenge). No
   overworld course boot flag exists. #186 request: shared-native overworld
   course boot flag + stage-table registration.
2. **Day-advance / surface-transition trigger: ABSENT.** The only `setTime`
   call in `pc_port` (`pc_p2_cave.cpp:220`) is cave-internal. The integrated
   surface-session contract names the native sunset driver missing
   (`MISSING_INTEGRATION`). #186 request: shared-native day-advance /
   surface-transition trigger mirroring the contract semantics.
3. **Exit / re-entry (stage boundary): ABSENT for surfaces.** The only
   exit/checkpoint path (`pc_p2_cave_request/interact/checkpoint`,
   `pc_p2_cave.cpp:145-154`) is cave-only and does not transfer. #186
   request: shared-native overworld surface exit + re-entry path with
   transition anchor and restore.

The four generic #132 items (sunset driver, save serializer, receipt ledger
endpoint, generator-cache restore) were pinned by #658 and are recorded as
EXCLUDED here, not re-audited.

## Stage-load stall diagnostic plan

- **Stall**: engine boots through window/GL/audio/init, then goes silent
  before the first fixture idle tick (pre-idle legal-data stage load).
- **Observation points**: last log line before silence (post-jaudio without
  room markers = stage-load stall; room markers without heap = map-model
  stall; idle WAIT markers = load OK, hang is later); process liveness + CPU
  (shader-compile spin vs synchronous I/O block); `DVDOpen FAILED` lines
  naming missing CWD-relative `assets/dataDir` files; CWD `assets/dataDir`
  + preview sidecar presence.
- **Data-ready assumption**: a data-ready environment stages CWD-relative
  `assets/dataDir` (legal disc extraction) plus the preview sidecars the boot
  contract requires; without them the stall is a data absence, not an engine
  defect.
- **Smallest instrumentation**: bounded frame budget with WAIT heartbeats in
  fixture idle; preflight imprint of CWD/assets/sidecars before boot; DVDOpen
  failure capture. Owner contract: #186 shared-review track.

## Module, tests, registry

- `experimental/pikmin2_overworld_surface_boot_path_pin_discovery.py`:
  machine-readable registry builder + fail-closed validator (`--check`,
  `--registry-out`).
- `tests/test_pikmin2_overworld_surface_boot_path_pin_discovery.py`: 20
  focused tests (pins, ABSENT verdicts with #186 requests, exclusion
  integrity, downstream/gates, diagnostic plan, refusal battery).
- Registry JSON emitted under the lane output dir (generated, hashed in the
  handoff); downstream consumers #696, #148, #660, #149, #150, #151.

## Captain safety #632

N/A (no runtime run). Any future runtime work must adopt
`scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`) with
orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED exit, and a parked
captain; guard/source hashes recorded at adoption.
