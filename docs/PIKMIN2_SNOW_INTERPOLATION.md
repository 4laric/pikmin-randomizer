# Snow actor interpolation (#327)

Implementation owner: Codex using shared account 4laric. This is an opt-in
experimental rendering path on the P2 branch, not a release default.

Place `p2-snow-interpolation.txt` containing `P2_SNOW_INTERPOLATION_1` in a
private preview session with a modern `P2_SNOW_2` bank. The complete bank must
pass the bounded baked-pose decoder and share topology and immutable resources.
Legacy banks without explicit source-frame mappings are rejected when enabled.
With the marker absent, existing discrete-pose rendering is retained.

Each Snow actor owns separate position and normal arrays. Source banks and
material/texture resources remain shared and immutable. Positions interpolate
between adjacent source samples; normals interpolate and normalize. Bounds are
rebuilt for the private model. The corpse holds the final death sample.

P1 animation remains the clock and gameplay authority. This changes no attack
events, collision structures or carry attachments, and does not provide P2
skeletal hitbox fidelity. Forget/reset removes the binding; ordinary death and
receipt credit do not imply slot reclamation. Native scene heaps reclaim Shape
storage. Interpolation does not allocate geometry buffers during drawing.

## Validation

Native candidate: `b8fb6df44c46806a035fe1bf0640bbafd2d1ca60`. Production
`pikmin_pc` build passed. The existing Snow lifecycle and shared decoder/blend
tests passed: 17 tests and 45 subtests, including compiled native checks.

The private fixture is built by `experimental.pikmin2_snow_interpolation build`
using an exact native head, and launched with its `run` subcommand. Required
inputs are `--assets`, `--converted`, `--pod`, `--snow`, `--exe`, and a fresh
`--output`. Add `--interpolate` for the new path and `--profile` for the populated
scene. Assets, builds and evidence remain local.

Lifecycle fixture SHA-256:
`93ff8b22da95c7095050fda64ad11f25e45a1d1ca72280e3e5c933060de9aa1d`.
Local accepted run: `output/snow327/lifecycle-final/stage/af8fd89651f04ef8a28405c0cdf2cb57`.
Real combat, death, far corpse transport, native Pod delivery and duplicate
receipt rejection passed. Fifty-one geometry comparisons covered the actual
drawn geometry; explicit forget/reset rejected subsequent queries. Economy
remained exactly 182 Pokos (180 treasure, 2 corpse). The fixture assigns Pikmin
actions and repositions the captain; it does not force enemy health or animation.

## Profiling

The comparison uses one binary, 100 Reds, four Snow actors, two native Spotty
Bulborbs and two native Wollywogs. Populations must remain intact at both ends.
This is a controlled microbenchmark: after each update the fixture restores
Pikmin/enemy placements and clears velocities, keeping the groups apart. Native
AI and drawing still run, but these timings do not represent freely roaming
combat. Free-roaming attempts lost population and are rejected as comparisons.
The profiler discards 120 warm-up callbacks and measures 600 callbacks. Engine
tick timings exclude retrace waiting; separate idle times include it. Windows
working set and private bytes are sampled by the host runner. Performance is
advisory on a shared development machine, not a universal frame-rate guarantee.

The dense24 bank has 120 compatible poses, 1,920,000 source MOD bytes and one
texture attachment; each pose has 226 positions and 164 normals. The decoded
bank and per-actor Shapes add CPU storage even though GPU resources are shared.

Four accepted runs used fixture SHA-256
`0a4be65ceca4eb20959e96e0a0ba705a5f13c5746189d0190bcfb11c21764797`.
Generator, stage settings and Snow manifest hashes match across all four runs.
All preserved 100 Pikmin, four Snow and four ordinary enemies at callbacks 120
and 720. Start/end captures show both groups in view. Their logs, timing CSVs,
JSON results and hashes are indexed locally in `output/snow327/comparison.json`.

| Run | Mean tick ms | Median | p95 | p99 | Worst | Ticks >33.333 ms | Peak WS MiB | Peak private MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| profile-off05 | 20.993 | 20.256 | 23.864 | 29.494 | 317.132 | 4/600 | 1052.6 | 1673.8 |
| profile-on05 | 10.117 | 10.014 | 11.857 | 12.680 | 15.719 | 0/600 | 1058.5 | 1729.7 |
| profile-off06 | 20.435 | 20.856 | 23.938 | 25.381 | 30.589 | 0/600 | 1118.1 | 1783.5 |
| profile-on06 | 18.397 | 18.381 | 22.074 | 23.697 | 25.253 | 0/600 | 1120.8 | 1781.0 |

The JSON `over_33ms` field is a fraction, not a count. Hardware: Core Ultra 9
275HX, 24 cores/threads, approximately 32 GiB RAM; Intel Graphics driver
32.0.101.8724 and RTX 5070 Ti Laptop driver 32.0.15.9201 installed. The active
adapter was not recorded, so do not attribute these results to a particular GPU.
There is substantial run-to-run variation and one large baseline outlier.
These observations establish the bounded comparison, not a causal speedup,
precise incremental memory cost, or sustained 60 FPS gameplay acceptance.

Rejected local attempts are retained: off/off02 staging lost population,
off03 timed out behind the inherited captain-state gate, and off04 lost actors
by the end. The accepted fixture removes that gate only for profiling and
holds placements; the lifecycle fixture keeps its normal progression checks.
