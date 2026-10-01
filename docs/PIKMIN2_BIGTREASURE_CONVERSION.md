# Pikmin 2 BigTreasure (Titan Dweevil) Model & Motion Conversion

Lane documentation for the model/motion conversion slice of
[#246](https://github.com/4laric/pikmin-randomizer/issues/246). Scope:
convert/import the BigTreasure boss model and its 29 `.bca` animation clips,
the four weapon pellets plus `loozy`, extract `otakara_*` capture transforms,
record pellet configs in the install profile, and wire the result into the
runtime fixture with captured visual evidence. Out of scope for this slice:
skeletal playback, production wiring, and final visual acceptance.

## Extraction and conversion facts

Extraction runs through `experimental/pikmin2_bigtreasure_assets.py` against
`assets/disc/PIKMIN2 for GAMECUBE.iso`:

```
python -m experimental.pikmin2_bigtreasure_assets --iso "assets/disc/PIKMIN2 for GAMECUBE.iso" \
    --source research --output output/bigtreasure-import-01
```

Executed result (kept in local output, not committed):

- Boss model `BigTreasure`: 34 joints, rigid binding (EVP1 envelope count 0),
  21 draw units. Shape 0 carries TEX1MTXIDX data, so the extractor emits
  explicit per-draw matrices (`rigid_draw_matrices()`) derived from the
  bind pose — required by the restricted converter used by this lane.
- All **29 of 29** `.bca` motion clips converted into baked pose banks
  (**167 poses total**, ~15.3 MB of baked output under
  `output/bigtreasure-import-01/`).
- Weapon pellets **4 of 5** converted: `otakara_elec`, `otakara_fire`,
  `otakara_gas`, `otakara_water`.
- **`loozy` is NOT converted**: its shape 3 uses matrix type 1, which the
  restricted converter does not support. It stays in the fixture as a
  declared debug marker (`pellet_debug=1`); its geometry is not fabricated.
- Capture transforms extracted for `otakara_elec/fire/gas/water/loozy`,
  `kosi`, and the effect joints.
- The 30-slot clip registry registers `wait2.bca` twice with divergent event
  content (slot 25 carries loop markers, slot 29 carries none). This is
  source-legitimate duplication, preserved as-is.
- `dead.bca` carries a `(320, 100)` `KEYEVENT_100` anchor.

## Motion table and vendored retail player

`experimental/pikmin2_bigtreasure_motion.py` emits a
`P2_RETAIL_EVENTS_1` table covering the 29 unique clips (the first
loop-carrying registration of each clip), generated at
`output/bigtreasure-import-01/BigTreasure/p2_bigtreasure_events.txt`.

The native loader (`native/pc_port/pc_p2_bigtreasure_motion.h/.cpp`) requires
exactly 29 clips and rejects malformed rows. The table feeds the **verified
retail event player** via byte-identical vendored headers (sha256 verified
against the engine repo at vendor time):

- `native/pc_port/pc_p2_motion_events.h` — engine commit `66c22b0`.
- `native/pc_port/pc_p2_retail_player.h` — engine commit `3486cc0`.

Related engine work items #257/#259 live on engine branches, not HEAD; the
vendored snapshots are the interface this lane compiles against.

## Pellet configs in the install profile

`experimental/pikmin2_bigtreasure_install.py` now carries the extracted
pellet configs (`PELLET_CONFIGS`):

- `otakara_elec/fire/gas/water`: 30/40 damage-family values, 1000 pokos,
  dictionary entries 197–200, radii 35/35/37/35, heights 50/52/20/51.
- `loozy`: 1/5 values, 10 pokos, dictionary entry 201, radius 12, height 10.
- Finale row: `mPelletDropCode` is null in the story config; loozy spawns via
  `releaseItemLoozy` instead.

## Runtime evidence

- Native visual module `native/pc_port/pc_p2_bigtreasure_visual.h/.cpp`
  (profile `P2_BIGTREASURE_VISUAL_1`) loads the baked pose bank, places the
  four converted pellets at bind-pose joint matrices, dispatches clip events
  through the vendored retail `Player`, and keeps a bounded event log.
- Stage builder `experimental/pikmin2_bigtreasure_stage.py` supports a
  `--clips` subset. Full stage `output/bigtreasure-visual-stage-01`
  (29 clips / 171 modifier shapes) and the reduced runtime stage
  `output/bigtreasure-visual-stage-02` (`wait1`, `dead` = 11 boss poses +
  4 pellets) were both generated.
- Fixture `output/bigtreasure-runtime-fixture-04` built via
  `scripts/build_pikmin2_fixture.py` against native HEAD `4ccb7778`
  (`--expected-native-head 4ccb7778ce1ff1edabf4c143a004d4e0a1f8c3bd`).
- Runtime session `output/bigtreasure-runtime-sessions/bd6b4066a3cb4a459f3a872127f07f7e`
  **PASSED**. Markers:
  - prior probes / elec / water / seam phases all pass (unchanged),
  - `VISUAL_READY clips=2 pellets=4 pellet_debug=1`,
  - `VISUAL_WAIT1_PASS frames=200 events=5 loops=2`,
  - `VISUAL_DEAD_PASS frames=332 events=12 keyevent100=320`.
- Captures `bigtreasure-wait1.ppm` / `bigtreasure-dead.ppm` (with `.png`
  conversions) in the session directory were visually inspected. The wait1
  capture shows the boss partially off-frame at the top-right with the gas
  bomb and elec device pellets visible; the dead capture shows the boss
  large in frame with the Comedy Bomb (green) and Shock Therapist (blue)
  attached. These are a baked-pose debug display, not retail-fidelity
  rendering.
- Fixture note: the load path requires the Groink heap pattern
  (`gsys->setHeap(SYSHEAP_App)` around `loadShape`); without it the host
  PANICs with "no heap specified" (`sysNew.cpp:270`). The full 171-shape
  stage fails to load under the current host heap, so the runtime session
  used the reduced stage.

## Lane fixtures re-run (warning-clean, `-Wall -Wextra -Werror`)

All four standalone fixtures rebuilt and passed after this slice:

- `p2_bigtreasure_test: all fixtures passed`
- `p2_bigtreasure_attacks_test: all fixtures passed`
- `BIGTREASURE_HOST` (all 7 host checks)
- `BIGTREASURE_MOTION` (`motion_load`, `motion_rejected`, `motion_playback`)

`ninja -n pikmin_pc` in `native/build-randomizer` reports no work to do —
the shared randomizer build is untouched.

Python glue tests: `python -m unittest tests.test_pikmin2_bigtreasure_install
tests.test_pikmin2_bigtreasure_assets` → 11 tests OK.

## Honest limitations and open items

- **Baked poses, not skeletal playback**: clips are baked per-frame joint
  matrices; there is no live skinning/IK. Event timing and loop behavior are
  exercised; visual motion is discrete pose flipping.
- **Pellets are static**: placed at bind-pose joint matrices; they do not
  track the boss's animated joints frame-to-frame.
- **Materials are approximate**; lighting/shading is not retail.
- **Boss framing/clipping**: in the wait1 capture the boss is partially
  off-frame; the debug camera is not tuned.
- **Full 171-shape stage blocked**: host heap capacity; only the reduced
  2-clip stage runs in the fixture. Loading the full stage is open.
- **`loozy` model unconverted** (converter matrix-type limitation above).
- **27 of 29 clips converted but not runtime-staged**: only `wait1` and
  `dead` ran in the session.
- **Full visual acceptance against retail remains open**, as does
  root-owned production wiring (slot/carry-route audit, relocation,
  campaign resume) per the root milestone docs.
