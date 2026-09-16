# Pikmin 2 BombSarai — runtime probe evidence against retail disc assets (#244)

Status: **executed, PASS**. All `P2_BOMBSARAI_*` runtime markers below were
produced by an actual run of the lane fixture against assets extracted from
the retail US Pikmin 2 disc (GPVE01 rev 0). Nothing in this document is
simulated or carried over from synthetic fixtures.

## Environment and build

- Host: Windows, MinGW-w64 g++ 16.2.0 (`C:/msys64/mingw64/bin` on PATH),
  CMake `C:/Program Files/CMake/bin/cmake.exe`, ninja at
  `C:/Users/alari/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0/LocalCache/local-packages/Python312/Scripts/ninja.exe`.
- Native lane branch `codex/p2-bombsarai-policy` (worktree
  `output/native-bombsarai-policy`), private candidate build
  `output/native-bombsarai-policy/build-bombsarai-runtime` configured with
  `-DCMAKE_PROJECT_INCLUDE=C:/Users/alari/pikmin-randomizer/output/bombsarai-runtime-extra.cmake`.
- Fixture binary: `output/p2_bombsarai_runtime.exe`, produced by compiling
  `tools/p2_bombsarai_runtime.cpp` with the exact `pikmin_pc` DEFINES/FLAGS
  from `build.ninja` and linking it with all `pikmin_pc` objects except
  `pc_main.cpp.obj` plus `libpikmin_legacy.a libbbft_transport.a -lws2_32
  libSDL2.dll.a -lopengl32` and the standard Windows system libs (response
  file `output/bombsarai-link.rsp`). The binary is gitignored build output.
- A real GL window was created on the desktop session (`pc_window_init`
  succeeded; first GX draw logged 132 vertices, GL status 0x0000). Audio
  uses the SDL `dummy` driver.

## Disc asset extraction

Source ISO: `assets/disc/PIKMIN2 for GAMECUBE.iso` (a staged copy; the
Downloads original is never touched). Extraction used the shared
`experimental.pikmin2_assets` helpers (`disc_files` / `archive_files` /
`decompress`) read-only, output under `output/pikmin2-extract-bombsarai/`:

- `enemyParms.bin` (+ decompressed) → `parms/` text tables +
  `parsed_parms.json` (BombSarai / bomb / sarai proper, general, collision,
  animmgr, stoneinfo)
- `bombsarai_model.szs.bin`, `bombsarai_anim.szs.bin`, `bomb_model.szs.bin`,
  `bomb_anim.szs.bin` → `bombsarai_enemy.bmd`, `bomb_enemy.bmd`
- `user/Kando/aiConstants.txt` (gravity)

All extracted data stays in gitignored `output/`; no disc data is committed.

## Numeric inputs taken from the retail tables

Bomb (proper): fp01 tekiDamage = **500** (overrides the 250 header default),
fp02 halfHeight = 50, ip01 = 1, ip02 = 15.
Bomb (general): fp00 fuse health = **4.5**, fp22 blast radius = **90**,
fp24 navi/piki damage = **10**.
Bomb fuse animation: `hit_start.bca` = **30 frames** → armLoopTicks = 30;
`hit_loop.bca` = 8 frames.
Bomb collision: root radius 20, child radius 15 → trace radius 15 for the
arena profile (fixture floor/wall probes use radius 5, their own constant).
BombSarai (proper): fp01 flight height = **70** (overrides the 90 header
default), fp03 = 50, fp10 = 2.5, fp11 = 20, fp21 = 1.5, fp22 = 1.0,
fp31 = 0.2, fp32 = 0.8, fp40 = 0.8.
BombSarai (general): health 1500, sight 200, attack radius 50, hit angle 15,
damage 10. Joints (16 total): kamu_jnt1 = index 14, kuti_joint1 = 9,
body_joint1 = 1, balloon1..5 = 4..8.
Gravity: `aiConstants.txt` = **560.0 units/s²** → gravityPerTick = 560/30 =
**18.6667** (30 Hz source tick).

These values populate `tools/p2-bombsarai-arena.txt`:

```
P2_BOMBSARAI_ARENA_1
carrier 0 120 0 0 9001
joint 0 55 0
hover 70 2.5 20 1.5 1.0
bomb 18.666667 4.5 30 15 90 50 500 10
receivers 4
receiver 501 teki 20 15 0 1 0
receiver 502 navi 30 15 0 1 0
receiver 503 piki 0 15 -40 1 0
receiver 504 teki 10 15 0 0 1
```

Receiver 504 is intentionally airborne-immune (grounded=0, immune=1) to
demonstrate the live immunity skip in the blast router.

## Run procedure (verbatim)

```
python -c "import sys; sys.path.insert(0,'scripts'); from pathlib import Path; \
  from preview_pikmin2_room import prepare; \
  print(prepare(Path('C:/Users/alari/pikmin-local/game/assets'), \
  Path('output/pikmin2-room105').resolve(), Path('output/bombsarai-arena-preview')))"
cp output/native-bombsarai-policy/tools/p2-bombsarai-arena.txt <run>/p2-bombsarai-arena.txt
cd <run>   # output/bombsarai-arena-preview/e2fd1da915be48348f22612438e323f4
PATH="/c/msys64/mingw64/bin:$PATH" \
  C:/Users/alari/pikmin-randomizer/output/p2_bombsarai_runtime.exe \
  --experimental-pikmin2-room > run.log 2>&1
```

The run directory overlays the Pikmin 1 asset tree read-only
(junction/hardlink convention from `scripts/preview_pikmin2_room.py`) and the
previously converted `output/pikmin2-room105` room (`room.mod`, `room.ini`,
`treasure.mod`). Full log: `output/p2_bombsarai_runtime_run.log` (gitignored).

## Probe output (verbatim, exit code 0)

```
P2_BOMBSARAI_ARENA_READY pinned=1 no_ai=1 no_fsm=1 no_visual_assets=1 receivers=4 pool=2
P2_BOMBSARAI_FLOOR_PROBE ground=-0.000000 center=5.000000 floor=1
P2_BOMBSARAI_WALL_PROBE_PASS
P2_BOMBSARAI_MAP_PROBES_PASS
P2_BOMBSARAI_ARENA_DRAW debug_markers_only no_visual_assets=1
P2_BOMBSARAI_SUPPLY source_tick=30
P2_BOMBSARAI_THROW source_tick=60
P2_BOMBSARAI_BLAST ticks=223 traces=19 floors=1 walls=0 hits=3
P2_BOMBSARAI_HIT id=501 kind=0 damage=500.000 self=1 token=0
P2_BOMBSARAI_HIT id=502 kind=1 damage=10.000 self=0 token=9001
P2_BOMBSARAI_HIT id=503 kind=2 damage=10.000 self=0 token=9001
PASS BOMBSARAI_RUNTIME
```

Reading of the evidence:

- `FLOOR_PROBE floor=1`: downward trace through the adapter is classified as
  floor contact against the converted room geometry; resting center = ground +
  probe radius (5.0 on a y=0 floor).
- `WALL_PROBE_PASS`: a real vertical triangle from the room model is found
  and classified as a wall, with the ground sample still valid.
- `SUPPLY source_tick=30` / `THROW source_tick=60`: the retail 30-frame
  `hit_start.bca` arm loop is honored before the throw.
- `BLAST hits=3`: the three vulnerable receivers inside the 90-unit retail
  blast volume are routed — teki 501 takes the retail tekiDamage **500** with
  the self-hit flag, navi 502 and piki 503 take the retail navi/piki damage
  **10** with the carrier token 9001. Airborne-immune receiver 504 is
  correctly skipped.
- Fuse ran 223 ticks from throw to blast under retail gravity (18.6667/tick)
  and 4.5 fuse health.

## Fixture fix uncovered by the first real run

The first execution failed at `FAIL BOMBSARAI_RUNTIME center floor
classification`: the floor probe started 10 units above the surface and
traced exactly 10 units per 30 Hz tick, landing exactly tangent with zero
penetration — P1 registers no collision at zero penetration, so no floor
triangle was recorded. This was a fixture bug, not a runtime defect; the
floor and wall probe velocities were raised from 300 to 600 units/s (change
confined to lane-owned `tools/p2_bombsarai_runtime.cpp`).

## Remaining gaps (as of the harness-event run above)

- No visual assets: carrier/bomb render as debug markers only
  (`no_visual_assets=1`); extracted BMDs are not yet wired in.
- Damage numbers are routed to instrumented receivers, not to real P1
  creatures; integration with live navi/piki/teki damage paths is pending.
- Campaign resume / persistence for BombSarai state remains open.

## Follow-up: FSM-driven run

The "No AI/FSM" gap above is closed by the next slice: the lane-owned
13-state carrier FSM now drives the seam (no harness supply/throw events),
with three executed scenarios — approach (Release lob), Purple-forced Fall
(skyward eject + recovery) and death-drop (zero-velocity drop with
dead-carrier attribution fallback) — all PASS against the same retail
assets. Full design, marker stream and the bomb-trace-radius resolution:
`docs/PIKMIN2_BOMBSARAI_FSM.md`.
