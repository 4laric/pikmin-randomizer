# Mamuta ground-strike animation (lane 19, #168 / #221)

Implementation owner: Codex using shared account `4laric`. Executing agent:
opencode (deepseek-v4.1-flash), 2026-09-14. Extends
[PIKMIN2_MAMUTA_POD.md](PIKMIN2_MAMUTA_POD.md).

## Problem

The P1 Miurin proxy observer drew one **frozen** source pose per clip.
`experimental/pikmin2_mamuta_install.py` installed only pose 0 of `wait`, the last
`dead` pose and `attack1` pose 0 (`REQUIRED_CLIPS = {'wait':0,'dead':-1,'attack1':0}`),
so when the Mamuta struck the ground (`attack1`, whose KEYEVENT_2 at frame 0 is the
bury/plant) the actor displayed a single static pose — no strike animation.

## Fix

- `pikmin2_mamuta_install.py` now installs **every** sampled pose of `wait`,
  `dead` and `attack1` as a time-sampled bank (`miulin_<clip>_<i>.mod`). The
  recorded import samples each clip at three source frames (e.g. `attack1` at
  0/18/37). A one-pose import still installs; the bank is just one frame.
- `pc_port/pc_p2_mamuta.cpp` loads `miulin_<clip>_00.mod` .. `_07.mod` as a bank
  and selects the pose from the P1 animator frame
  (`round(counter/(frames-1) * (poses-1))`), falling back to a single
  `miulin_<clip>.mod` legacy install. `P2_MAMUTA_DRAW` now reports
  `poses=<n> animated=<0|1>`.

## Evidence

Real GL 960x540, native `dad4c920` (base draft `5f33a9e6`), exe
`native-mamuta-anim-build/bin/nectar.exe` sha256 `3E9E771A…`, fixture
`mamuta-anim-fixture-natural-01/fixture.exe` sha256 `6DEE805B…`, run
`output/mamuta-anim-run-01/a5e27f7796fc40ccb26e7992efafd2f5`:

```
P2_MAMUTA_READY generator=221001 native_type=24 xyz=-150.000000,30.000000,1850.000000 P1_proxy_source_pose_banks_no_P2_planting
P2_MAMUTA_DRAW generator=221001 anchor=attack1 poses=3 animated=1 P1_gameplay_unchanged
```

Staged room carries `miulin_attack1_00/01/02.mod`, `miulin_dead_00/01/02.mod`,
`miulin_wait_00/01/02.mod`. Tests:
`tests/test_pikmin2_mamuta_install.py`, `test_pikmin2_mamuta_runtime.py`,
`test_pikmin2_mamuta_natural.py`, `test_pikmin2_mamuta_pod.py`,
`test_pikmin2_mamuta_cargo.py` -> 36 passed, 9 subtests.

## Honest limits

- The recorded import holds **three sampled poses** per clip; playback selects
  the nearest pose (no interpolation), so the strike is coarse vs the source
  38-frame `attack1`.
- The pose index is driven by the **P1 Miurin animator** frame count, a proxy
  timing, not P2 `miulinState` frame parity.
- The acceptance run drew the animated `attack1` bank but this particular run
  did not reach a natural kill (run-to-run variance); the animation path is
  observed, not a full strike-to-corpse chain in this log.

## Provenance

Native candidate `opencode/p2-mamuta-anim` (local-only, not pushed), base
`5f33a9e6e8f618394c5d78cfb1cc1201a754c1b6`, head
`dad4c920feea6c9cb0d8323909c5300504210a6a`; worktree `output/native-mamuta-anim`.
Patch `native-candidates/mamuta-anim/0001-*.patch`; metadata in
`native-candidates/mamuta-anim/provenance.json`. Root worktree
`opencode/p2-mamuta-anim-root` (also carries the fixture-builder response-file
fix `9e7a99d`, needed to build fixtures against the larger draft). Native
origin/upstream not pushed. No maintained checkout or shared build modified.
