# Mamuta source animations: ground strike, move and flick (lane 19, #168 / #221)

Implementation owner: Codex using shared account `4laric`. Executing agent:
opencode (deepseek-v4.1-flash), 2026-09-14. Extends
[PIKMIN2_MAMUTA_POD.md](PIKMIN2_MAMUTA_POD.md).

## Problem

The P1 Miurin proxy observer drew one **frozen** source pose per clip:
`experimental/pikmin2_mamuta_install.py` installed only pose 0 of `wait`, the last
`dead` pose and `attack1` pose 0. The Mamuta had no ground-strike animation (and
no `move`/`flick`), and only three motions were mapped.

## What this adds

- Every P1 Miurin motion (`PaniAnimator.h` TekiMotion) now maps to its P2 Miulin
  clip and loads a time-sampled bank:
  `Wait1/2 -> wait`, `WaitAct1/2 -> waitact`, `Move1/2 -> move`,
  `Attack -> attack1`, `Flick -> flick`, `Type1/2/3 -> attack1`, `Type4 -> attack4`,
  `Type5 -> type5`, `Dead -> dead` (`pc_p2_mamuta_policy.h`).
- `pikmin2_mamuta_install.py` installs all sampled poses of all nine clips
  (`miulin_<clip>_<i>.mod`, three source frames each) plus a bank manifest
  `p2-mamuta-bank.txt` carrying each clip's source length, sampled source frames
  and gameplay event frames.
- `pc_port/pc_p2_mamuta.cpp` reads the manifest and selects the pose from the
  **source-frame timeline** (`phase * (sourceFrames-1)`, nearest sampled frame)
  instead of a uniform pose index, so the sampled event frames land on their
  true pose — in particular `attack1`'s KEYEVENT_2 at source frame 0 (the
  bury/plant) and the frame-4 follow-up. `P2_MAMUTA_DRAW` now logs
  `poses= animated= src_frame= sample= events=`.

## Evidence

Real GL 960x540, native `25f96694` (base draft `5f33a9e6`), exe
`native-mamuta-anim-build/bin/nectar.exe` sha256 `9D84BD14…`, fixture
`mamuta-anim-fixture-natural-02/fixture.exe` sha256 `816A7D28…`:

```
# output/mamuta-anim-run-03 (draw path exercised)
P2_MAMUTA_DRAW generator=221001 anchor=waitact poses=3 animated=1 src_frame=0.0 sample=0 events=2
P2_MAMUTA_DRAW generator=221001 anchor=wait    poses=3 animated=1 src_frame=0.0 sample=0 events=2
P2_MAMUTA_DRAW generator=221001 anchor=move    poses=3 animated=1 src_frame=0.0 sample=0 events=2
P2_MAMUTA_DRAW generator=221001 anchor=attack1 poses=3 animated=1 src_frame=0.0 sample=0 events=2

# output/mamuta-anim-run-04 (full chain)
P2_MAMUTA_DRAW ... anchor=move    poses=3 animated=1 ...
P2_MAMUTA_DRAW ... anchor=attack1 poses=3 animated=1 src_frame=0.0 sample=0 events=2
P2_MAMUTA_DRAW ... anchor=dead    poses=3 animated=1 src_frame=0.0 sample=0 events=1
[Pikipelago] P2_POD_RECEIPT id=corpse:mamuta:221001 value=2 new=1 pokos=2 seeds=0
P2_MAMUTA_POD_RESULT died=1 died_tick=506 corpse=1 carried=1 goal=1 pokos=2 control_alive=1 squad=8
```

Staged `p2-mamuta-bank.txt` (excerpt):

```
clip wait 90 3 2        frames 0 44 89    events 13 72
clip move 77 3 2        frames 0 38 76    events 13 42
clip attack1 38 3 2     frames 0 18 37    events 0 4
clip flick 45 3 2       frames 0 22 44    events 15 25
clip dead 71 3 1        frames 0 35 70    events 27
```

Tests: `tests/test_pikmin2_mamuta_{install,runtime,natural,pod,cargo,assets}.py`
-> 53 passed, 24 subtests.

## Honest limits

- Recorded banks hold **three sampled poses** per clip; playback selects the
  nearest pose (no interpolation) vs the source 38-frame `attack1`.
- The pose timeline is driven by the **P1 Miurin animator** frame count scaled to
  the P2 clip length, a proxy timing, not P2 `miulinState` frame parity.
- `flick` is mapped, installed and in the manifest but was **not observed** in
  these runs (the P1 Flick reserve motion did not trigger); the other banks
  (`wait`/`waitact`/`move`/`attack1`/`dead`) are observed animated.
- Depends on the fixture-builder response-file fix (`fbef363`, cherry-picked
  `9e7a99d`) to build fixtures against the larger draft.

## Provenance

Native candidate `opencode/p2-mamuta-anim` (local-only, not pushed), base
`5f33a9e6e8f618394c5d78cfb1cc1201a754c1b6`, head
`25f96694155fad633787e2766978c376097adb23`; worktree `output/native-mamuta-anim`.
Patches `native-candidates/mamuta-anim/0001-0002`; metadata in
`native-candidates/mamuta-anim/provenance.json`. Root worktree
`opencode/p2-mamuta-anim-root`. Native origin/upstream not pushed. No maintained
checkout or shared build modified.
