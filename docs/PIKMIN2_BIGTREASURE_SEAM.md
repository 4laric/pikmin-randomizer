# Pikmin 2 Titan Dweevil (BigTreasure) host integration seam (#246)

Implementation owner: Codex using shared account 4laric. Integration contract
#186, ownership update per #128 assignment 2026-09-13 and
docs/PIKMIN2_WORKER_HANDOFF.md. Prior slices: [source audit](PIKMIN2_BIGTREASURE_AUDIT.md),
[ownership/teardown contract](PIKMIN2_BIGTREASURE_CONTRACT.md),
[per-element attack policies](PIKMIN2_BIGTREASURE_ATTACKS.md). This slice adds
the lane-owned host binding of the attack-trace interface to the P1 static
map, the opt-in registration/install-profile glue with multi-actor lifetime
wiring, a private isolated native compile against the frozen host, and
runtime flat-floor/wall probes plus elec-bounce/water-arc acceptance.
No shared CMake, hooks, binaries or exports were changed; the shared
`native/build-randomizer` production target reports `ninja: no work to do.`
before and after the fixture build.

## Lane-owned files

Native branch `codex/pikmin2-room-preview`, commit `224b06da`:

- `pc_port/pc_p2_bigtreasure_map_trace.h/.cpp` — host binding of
  `P2BigTreasureTraceFn`/`P2BigTreasureGroundFn` to the P1 static map.
- `pc_port/pc_p2_bigtreasure_host.h/.cpp` — engine-free registration glue:
  opt-in profile parse/install, fixed-placement attack entry, multi-actor
  lifetime wiring at the seam.
- `tools/p2_bigtreasure_host_test.cpp` — standalone engine-free fixture.
- `tools/p2_bigtreasure_runtime.cpp` — private replacement-App runtime
  fixture (isolated fixture build only, never in the game target).
- `tools/p2_bigtreasure_runtime_run.py` — fresh-overlay run/verify helper.

Root repo:

- `experimental/pikmin2_bigtreasure_install.py` — opt-in install profile per
  #186 (hash-bound canonical profile, conflict refusal before mutation, no
  assets; mirrors the #245 Fuefuki lane convention).
- `tests/test_pikmin2_bigtreasure_install.py` — 4 unit tests, pass.

## Map-trace adapter contract

Mirrors the #169 Groink runtime-fixture pattern
(`pc_p2_groink_map_trace.h/.cpp`):

- **Dedicated trace proxy.** `P2BigTreasureTraceProxy` is a standalone
  `Creature` collision recorder, never registered with an actor manager; the
  owner boss's collision fields are never reused for attack-node traces.
  Ground triangle, collision flag, wall flag and platform pointers are
  cleared before every trace; `wallCallback` records wall contact.
- **Center/base conversion.** P1 `MapMgr::traceMove` accepts a sphere base
  (adds the radius before collision, subtracts it after). The P2 policies
  store sphere centers — the elec policy pre-raises its node by +20 (source
  convention) before calling. The adapter traces with `center.y - radius`
  and returns `position.y + radius`.
- **Contact classification + ground sample.** Floor = ground triangle
  present; wall = wall callback fired. On either contact the adapter samples
  `getMinY(x, z, false)`; a contact without a finite terrain sample fails
  the whole trace. The adapter never invents ground.
- **Validation.** Non-finite or out-of-range (±100000) coordinates, any
  delta other than the 30 Hz source delta, any radius other than the elec
  trace radius (20), and a non-finite or non-(0,1] bounce factor fail the
  trace; no trace is performed.
- **Approximation.** P1 `MoveTrace` carries no bounce coefficient; the
  source bounce factor is validated but P1's trace-mutated velocity is what
  the elec policy consumes (floor friction stays policy-side). P1 contact
  classification and restitution are host approximations, not Pikmin 2
  collision parity.

## Registration/install-profile glue and lifetime wiring

Opt-in per #186: `p2_bigtreasure_host_setup` only installs from an explicit
`P2_BIGTREASURE_HOST_1` profile (placement/target/timer/discharge lines,
fail-closed parse, no partial install). Fixed placement comes first per the
boss staged-phases gate — no locomotion, no spawn-table registration. The
seam owns the multi-actor lifetime:

- **Setup** captures the full retail loadout: 4 weapon pellets (elec, fire,
  gas, water) at full 6000 HP plus Louie = 5 captured pellets; pacer reset
  with the profile timer; the elec pool invariant (1 anchor + maxDischarge
  ≤ 17) is enforced at install.
- **Attack entry** derives the source 225-unit XZ target box from the fixed
  placement and routes through the director's pacing limiter (4 + 2 ×
  liveWeapons seconds, strict).
- **Defeat** is deterministic and ordered: pooled attack nodes force-recycle
  first (including in-flight water bubbles, no hit events), then ownership
  releases every still-captured pellet — weapons pop (0,100,0), Louie
  (0,150,0). Drop-event writes cap at the caller's buffer but releases are
  total; the return count reports all releases. Reinstall and reset run the
  same teardown, so no captured pellet or pooled node ever leaks.

## Standalone fixture evidence

MinGW64 GCC, `-std=gnu++17 -Wall -Wextra -Werror`, warning-clean:

```
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_host_test.cpp pc_port/pc_p2_bigtreasure_host.cpp pc_port/pc_p2_bigtreasure.cpp pc_port/pc_p2_bigtreasure_attacks.cpp -o <private-output>/p2_bigtreasure_host_test.exe
```

All six groups pass: valid parse; rejection of null/missing/wrong-magic/
trailing-field/NaN/out-of-range/over-timer/invariant-breaking/truncated
profiles; install loadout (5 captures, elec invariant, reinstall teardown);
bad-profile refusal; fixed-placement attack entry (strict 12 s pacing
boundary, elec first band, one attack at a time, out-of-box target never
attacks); defeat ordering and lifetime (pools drained before releases,
5 events with Louie last at (0,150,0), repeat defeat 0, truncation-total
semantics, reset idempotence). Prior lane suites re-run green:
`p2_bigtreasure_test` (ownership) and `p2_bigtreasure_attacks_test`
(attacks) both pass.

Install-profile unit tests: `python -m unittest
tests.test_pikmin2_bigtreasure_install` — 4 tests pass (install/idempotent
reinstall, conflict refused before mutation, missing run dir refused,
contract tokens).

## Private native compile against the frozen host

Isolated fixture build via root `scripts/build_pikmin2_fixture.py`; the
shared production target is never rebuilt or overwritten:

```
python scripts/build_pikmin2_fixture.py --build native/build-randomizer --source native --fixture native/tools/p2_bigtreasure_runtime.cpp --output output/bigtreasure-runtime-fixture-01 --expected-native-head 224b06da93d9e5e11c6c7cdf346682281b18829f
```

Frozen host configuration (from `native/build-randomizer/CMakeCache.txt`):
Ninja generator, `CMAKE_BUILD_TYPE=Release`, `PIKMIN_NATIVE_JAUDIO=ON`,
`PIKMIN_NATIVE_OPTIMIZE=OFF`, `PIKMIN_RANDOMIZER_TEST_HOOKS=OFF`, MinGW64
g++. Result: `status=built`; provenance
`output/bigtreasure-runtime-fixture-01/provenance.json` (sha256
`7a93c2c2…f96b0`), fixture.exe sha256
`aca2b4b5f07a303b95495b9e974afeccfa735f95f32f2efba9c74bfdc3582ea1`.
`ninja -n pikmin_pc` reports `no work to do` before and after; the fixture
links privately from snapshotted objects into `output/`, outside the native
source and production build.

## Runtime probe evidence (real P1 static map)

Session `output/bigtreasure-runtime-sessions/8d982eb210f54b3db1063768068b4d3e`
(status `passed`, exit 0), run via
`native/tools/p2_bigtreasure_runtime_run.py` against the converted
`output/pikmin2-room105` overlay with staged profile
`output/bigtreasure-host-stage-01/p2-bigtreasure-host.txt`:

| Probe | Marker | Result |
| --- | --- | --- |
| Flat floor | `P2_BIGTREASURE_FLOOR_PROBE ground=-0.000000 center=20.000000 floor=1` | radius-20 center rests exactly at ground+20 with a finite terrain sample |
| Free space | part of `P2_BIGTREASURE_MAP_PROBES_PASS calls=3 floors=1 walls=1` | stationary sphere at ground+100: no floor/wall contact |
| Vertical wall | `P2_BIGTREASURE_WALL_PROBE wall=1 groundY=-0.000000` | real steep map triangle: wall callback fired, terrain sampled |
| Elec bounce | `P2_BIGTREASURE_ELEC_PROBE_PASS bounces=10 traces=3000 floors=2720` | 10 first-contact bounce events; nodes settle on the floor (stored Y = ground within 0.5) |
| Water arc | `P2_BIGTREASURE_WATER_PROBE_PASS ticks=59 hits=1 ground=-0.000000` | gravity −20/update; ground impact via adapter at tick 59; node recycled |
| Host seam | `P2_BIGTREASURE_HOST_SEAM_PASS ticks=361 attacks=1 events=5` | strict 12 s pacing (361 ticks), one elec attack, 5 defeat releases, pools drained |

Final marker `PASS BIGTREASURE_RUNTIME`. These are seam/probe acceptance
results over a stationary harness (no AI, no damage receivers, no models):
they clear the flat-floor/wall gate for later elec-bounce and water-arc
gameplay acceptance, they do not establish it.

## Remaining gaps

- **Models/motions converter handoff stays with the engine lane (#128).**
  `pc_p2_bigtreasure` (ownership), `pc_p2_bigtreasure_attacks`,
  `pc_p2_bigtreasure_host` and `pc_p2_bigtreasure_map_trace` are recorded as
  consumers; the install profile declares `external models_motions:#128`.
- **Pellet configs and `mPelletDropCode` remain disc-data unknowns** (audit
  open questions); declared as `external pellet_configs:disc_data` and
  `external mpellet_drop_code:disc_data` in the install profile.
- **Gameplay acceptance still open:** elec-bounce and water-arc ballistics
  vs retail captures, damage receivers/effects, the 12-state FSM host,
  natural combat, and arena mixed-level staging (gated) are later slices.
- **Root-owned integration:** calling `pc_p2_bigtreasure_host_*` from shared
  game code and adding the lane translation units to the production build
  remains lead-owned merge work; this slice ships lane-owned files only.
