# Challenge runtime bridge port (#722)

Ports the #710 engine runtime bridge (native commit `db245877`) onto the
integrated tip `be527446` and ADDS the engine call site + CMake membership.
Downstream: `p2-challenge-ch-abem-leafchappy-p1` (#550) challenge markers.
#186 review is required before any shared-line landing; this lane lands
nothing itself (private scoped candidate + single-writer integration).

## Why

#714 landed only a packet; the #710 bridge code (`db245877`) was never landed
and is absent from `be527446`, so challenge boots emit zero markers.

## What (owned files only)

- `native/pc_port/pc_p2_challenge_runtime.{h,cpp}`: ported **byte-verbatim**
  from `db245877` (sha256 `6cefe957...` / `898bdacc...`). The bridge binds the
  selected stage row to StageEntry/HostState, drives
  `p2challenge::wiring::syncTick` from live squad/captain/clock facts, emits
  `P2_CHALLENGE_MODE_BOOT`/_TICK/_DONE, and never aborts the game.
- `native/pc_port/pc_bbft.cpp`: ADDED the #710 call-site glue only —
  `p2_challenge_stage_params()` field copy plus a null-by-default
  `P2ChallengeRuntimeHook` and its guarded invoke in `pc_bbft_update()`. The
  file stays engine-free so the small `pc_bbft_test` target keeps linking and
  runs inert.
- `native/CMakeLists.txt`: added `pc_p2_challenge_runtime.cpp` +
  `pc_p2_challenge_mode.cpp` to `PC_PORT_SOURCES` (feeds `pikmin_pc`); neither
  TU added to `pc_bbft_test`.
- `native/tools/p2_challenge_runtime_bridge_fixture.cpp`: guarded
  replacement-main fixture (ported from the #710 fixture) booting
  `--experimental-pikmin2-room --experimental-challenge-stage
  ch_NARI_01kusachi` with the #632 guard first on every idle.
- `scripts/build_p2_challenge_runtime_bridge.py`: private leased build/run
  helper (default config; runs from a staged asset root so the boot reaches
  idle).
- `experimental/pikmin2_challenge_runtime_bridge_port.py` + `tests/...`:
  fail-closed evidence verifier.
- This doc.

## Compiled evidence

- Default config `pikmin_pc` links (the audio `Jac_NoteDemoSkipped` fix is
  present at this tip); fixture compile/link 0 (183 objects); self-test pass;
  negative exit 86; `ninja -n` 0.
- Headed run from the staged asset root `output/bomb-joint-runs/chappy`
  (needed so the boot reaches idle): `P2_CHALLENGE_MODE_SQUAD_APPLIED` then
  `P2_CHALLENGE_MODE_BOOT`, then **88** `P2CHALLENGE_WIRING_TICK` lines with a
  live squad (`squad_alive=20 squad_reds=20`) and `time_left` counting down
  from 180, no captain-down, exit 0.
- Hashes: executable `9f0fca46...`; marker log `bbb996db...`.

## Captain safety #632

Guard vendored verbatim from `scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`), checked
immediately after engine idle before any observation; self-test 7/7 and
negative path exit 86 verified. The marker run had the guard active with no
captain-down. All six gates UNTESTED; no gameplay acceptance claimed.
