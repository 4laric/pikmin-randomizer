# P2 challenge host-mode engine runtime bridge (lane challenge-hostmode-engine-hook-native, #710)

Bounded shared-file producer for the missing engine runtime hook that blocks
the #550 consumer (`p2-challenge-ch-abem-leafchappy-p1` boots the engine and
emits zero challenge markers). Downstream: #550 challenge markers observed,
then the remaining gates. Shared-line landing requires #186 review; this lane
lands nothing itself (private candidate + single-writer integration).

## Traced gap

`host-mode-runtime-wiring-native` (#702, done+integrated) landed only the
additive `p2challenge::wiring::syncTick` API plus its own fixture; no engine
runtime file calls it. `CMakeLists.txt` compiled `pc_p2_challenge_mode.cpp`
only into the standalone fixture, and `pc_bbft.cpp` never constructed a
`HostState` or called `syncTick`. The #550 consumer verification
(`consumer-verification-abab68ce.md`) proves a plain room boot emits zero
`P2_CHALLENGE_MODE_*` / `P2CHALLENGE_WIRING_*` markers.

## Implementation (owned files only)

- `native/pc_port/pc_p2_challenge_runtime.{h,cpp}` (new): binds the selected
  `P2ChallengeStageRow` to the landed `StageEntry`/`HostState`, owns the
  runtime state, and drives `p2challenge::wiring::syncTick` from live engine
  facts (squad via `pikiMgr`, captain via `naviMgr`+`GameStat::orimaDead`,
  seconds via the frame clock). Emits `P2_CHALLENGE_MODE_BOOT` on bind, then
  the wiring tick stream, then `P2_CHALLENGE_MODE_DONE` once on end. Never
  aborts the game; a dead captain ends the HostState and the bridge goes
  inert. Red composition is untracked (stays 0, constraint documented).
- `native/pc_port/pc_bbft.cpp`: calls the bridge from `pc_bbft_update()`
  through a null-by-default hook plus a plain params copy. Engine-free, so the
  small `pc_bbft_test` target keeps linking and runs inert (hook stays null
  there). The indirection is forced by the dual linkage and documented in the
  header; the engine still drives the bridge every frame in `pikmin_pc`.
- `native/CMakeLists.txt`: adds the runtime module +
  `pc_p2_challenge_mode.cpp` to the `pikmin_pc` target (#186 review). Neither
  new TU is added to `pc_bbft_test`.
- `native/tools/p2_challenge_host_runtime_fixture.cpp`: guarded
  replacement-main fixture booting `--experimental-pikmin2-room
  --experimental-challenge-stage <key>` with the #632 guard first on every
  idle; markers come from the engine bridge, the fixture only guards, bounds
  and reports. Guard vendored verbatim; self-test + negative-test flags.
- `scripts/build_p2_challenge_host_runtime.py`, this doc,
  `experimental/pikmin2_challenge_host_runtime.py` (run-log verifier),
  `tests/test_pikmin2_challenge_host_runtime.py`.

## Activation contract

The bridge is active only when a valid `--experimental-challenge-stage` key
resolves in the decoded table (currently only `ch_NARI_01kusachi`; extending
the table is #675-owner/content-lane scope, not this lane). A plain room boot
without a key stays silent and inert. Movies/pauses skip ticks without ending
the run. No invented stages, no simulated facts.

## Build / run (private, leased)

Build directory `output/challenge-hostmode-engine-hook-build` (exclusive,
lane-private). Lease the heavy-build slot through the canonical registry
before ANY heavy job and respect the live elastic cap; release afterward.
Record the exact source commit, executable SHA-256, and `ninja -n` result.

## Captain safety #632

Mandatory for any observed tick: the fixture checks `orimaDead`, `NaviDead`
and HP<=1 immediately after engine idle, emits `CAPTAIN_DOWN` and exits
BLOCKED (86) with no PASS. Parked captain / no blanket invincibility apply to
runs that test captain hits; this fixture only observes. Guard header
`scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`) recorded.

## Honest status

All six runtime gates stay UNTESTED unless genuinely observed; no playability
claim beyond observed markers; no ADMIT, no ledger writes.
