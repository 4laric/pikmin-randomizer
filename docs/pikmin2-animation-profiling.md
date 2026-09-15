# Measuring Snow animation costs (#128)

`experimental.pikmin2_animation_profile` captures an explicitly supplied native
command and analyzes existing port diagnostics. It does not build the game,
change a playtest seed, drive controls or infer FPS from offline extraction time.

Use a freshly prepared isolated preview run. The capture command terminates only
the child it started when the duration expires, so do not point it at a session
whose unsaved progress matters. Set the normal native dependency PATH and, if
desired, `SDL_AUDIODRIVER=dummy`. The harness itself enables
`PIKMIN_PERF_STATS=1` and `PIKMIN_TICK_STATS=1`.

```powershell
py -3.12 -m experimental.pikmin2_animation_profile capture --cwd C:/path/to/private/run --output output/profile/baseline-capture --seconds 90 -- C:/path/to/copied/nectar.exe --experimental-pikmin2-room
py -3.12 -m experimental.pikmin2_animation_profile analyze --log output/profile/baseline-capture/native.log --capture output/profile/baseline-capture/capture.json --bank output/p2-animation128/baseline12 --output output/profile/baseline.json
py -3.12 -m experimental.pikmin2_animation_profile analyze --log output/profile/dense-capture/native.log --capture output/profile/dense-capture/capture.json --bank output/p2-animation128/dense24 --output output/profile/dense.json
py -3.12 -m experimental.pikmin2_animation_profile compare --baseline output/profile/baseline.json --candidate output/profile/dense.json --output output/profile/comparison.json
```

Capture output directories must be new. Analysis accepts logs without any
profiling data and reports missing metrics explicitly. `--warmup-windows 1`
(default) drops the first presentation window. `--start-marker TEXT` ignores
lines before a known fixture marker. A missing marker yields unmeasured results,
not measurements accidentally taken from the title screen.

## What each source measures

- `native/pc_port/gl/pc_gfx.cpp` emits `[PERF]` after 120 presentation intervals.
  Its milliseconds are a mean elapsed frame interval for that window, including
  pacing. Equal-size window means can be averaged; effective FPS is the inverse
  of that combined mean. The tool never reports these as individual-frame p95
  or p99. At two FPS, one window alone takes a minute to appear.
- `native/pc_port/timing/pc_tick_profiler.cpp` reports a rolling buffer of up to
  2,048 CPU ticks. The tool shows only the latest complete report because reports
  overlap. These percentiles describe CPU work, not presentation intervals.
  A short capture's rolling window can still contain startup even after a PERF
  warmup window was discarded. GL/GX count rows remain counts, not milliseconds.
- `[PERF GPU]` contains asynchronous GPU scene/blit timings; missing or pending
  results stay unmeasured.
- `[PC Port] Textures` reports renderer-tracked texture allocations. Its `MB`
  values are actually MiB rounded down by the source's bit shift. They do not
  measure total process RAM, all CPU Shape allocations or VRAM residency.
- `P2_SNOW_BANK` reports native bank loading, payload bytes and explicit texture
  attachment calls. The tool cross-checks pose count and bytes against the
  supplied import. This is not an actor-rendering benchmark.
- `P2_SNOW_DRAW corpse=0/1` confirms that the live/corpse draw path was reached
  at least once. No live marker means the tool flags the FPS result as a room
  workload, without demonstrated Snow rendering.

Missing process RAM and per-frame presentation percentiles are always explicit.
Capture wall time includes startup; extraction duration remains separately
labelled as offline work. Malformed known log records are listed by line number.

## Initial native observations

Two fresh floor-2 previews used the same copied production executable
`output/p2-team-batch1/nectar.exe`, same source room, Purple bank, seven-Snow roster
and a 30-second capture each. They received no controller input. Each report
discards the first 120-frame presentation window.

| Measurement | 12 poses/clip | 24 poses/clip |
| --- | ---: | ---: |
| Native bank load | 0.018 s | 0.034 s |
| Explicit Snow texture attach calls | 1 | 1 |
| Mean presentation interval | 33.33 ms | 33.34 ms |
| Effective presentation FPS | 30.003 | 29.994 |
| Renderer texture total, rounded down | 27 MiB | 27 MiB |

Neither idle camera saw Snow, so neither log contains a live Snow draw marker.
These results establish bounded loading and the room's idle presentation rate;
they do not validate shared materials visually or reproduce the reported
two-FPS condition. Camera, combat and moving-Pikmin workloads need their own
captures. The native close-up fixture's normal 30-frame lifetime is adequate for
a screenshot but too short for even one 120-frame PERF window.

Local evidence lives under `output/p2-animation-profile/`: each named run has
`capture/native.log`, `capture/capture.json` and `report.json`; `comparison.json`
combines them. `run_comparison.py` records the exact private-room preparation
used locally. This is descriptive evidence from one pair, not a performance
regression threshold or statistical attribution to pose density.

## Corrected close-up fixture

The fixture was rebuilt from `native/tools/preview_p2_room.cpp` against the
**current `native/build-randomizer` objects**, native commit `872f0f00`, into
`output/p2-team-batch2/fixture/preview_p2_room.exe`. An initial attempt used stale
`build-stats` objects that only understood v1 banks and aborted during setup;
those `*-render` failure logs are excluded from current validation.

Both current 30-frame fixtures exited zero with `P2_SNOW_DRAW corpse=0` and
`PASS Snow render capture`, but their screenshots were obscured by the landing
sequence. A private output-only fixture copy delays capture to frame 360 and
repeats the existing synthetic nearby placement at frame 330. It changes no
native source or production executable. Both delayed runs exited zero, and
inspected PNGs show the white/blue-spotted Snow model without an obvious material
binding failure. No corpse draw was exercised.

The delayed fixture retains two PERF windows after dropping warmup: baseline
33.335 ms (29.999 FPS), dense 33.340 ms (29.994 FPS). Both show 27 MiB tracked
textures and one explicit Snow attachment call. Native load times were 0.005 s
and 0.008 s in this warmed-cache pair. This is a small synthetic scene with a
visible live Snow actor, not full-game performance acceptance or evidence about
every animation pose. The two-FPS issue was not reproduced.

Evidence: `output/p2-animation-profile/late-render-comparison.json`,
`baseline12-late-snow.png`, `dense24-late-snow.png` and `provenance.json`.
The latter records exact executable SHA-256 hashes and excludes the stale
fixture. The harness now records executable hashes before new captures too.
Current general fixture SHA-256:
`3e369d365f91c493f5fad82948ca54a79c078aed6a50453d60a2af6f6db986cd`.
Private delayed fixture SHA-256:
`bebb6e448835e499e028196f2a1e86900f59d06f0c0d489551f5e4cf2781359b`.

Run the eight focused tests with:

```powershell
py -3.12 -m pytest tests/test_pikmin2_animation_profile.py -q
```
